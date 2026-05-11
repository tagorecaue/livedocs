"""Agent wrapper — fala com o Claude Code CLI via subprocess.

Estratégia:
- Cada turno é um `claude --print --output-format=json` com allowlist explícito de tools.
- Adicionamos `--add-dir` pro repo do usuário.
- Passamos o system prompt customizado via `--append-system-prompt`.
- O prompt do user vai como argumento posicional.
- Lemos o JSON envelope, extraímos `result`, parseamos como JSON estruturado
  quando aplicável (tolerante a prose ao redor + code fences).

Segurança (issue #6):
- NÃO usamos `--permission-mode=acceptEdits` (foot-gun: dá Edit livre em todo --add-dir).
- Usamos `--allowedTools` com whitelist mínima: Read, Glob, Grep, Write.
- Edit/Bash/WebFetch ficam de fora — agente não pode modificar fonte do usuário.

Auditoria:
- Cada chamada é loggada em `<repo>/.livedocs/logs/<timestamp>-<purpose>.jsonl`
  contendo system prompt, user prompt, full response, parsed JSON, custo, duração.
- Logs giram automaticamente (mantém últimos N por padrão).

Sem streaming no v0 — usamos spinner do nosso lado e mostramos o output quando terminar.
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from livedocs.skill import LIVEDOCS_SYSTEM_PROMPT


@dataclass
class AgentResult:
    text: str
    json_data: dict | list | None
    cost_usd: float
    duration_ms: int
    is_error: bool
    error_message: str | None = None
    raw_envelope: dict[str, Any] | None = field(default=None, repr=False)


class AgentError(Exception):
    pass


def claude_available() -> bool:
    return shutil.which("claude") is not None


# ---------------------------------------------------------------------------
# JSON extraction — tolerant to prose around + code fences
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def extract_json(text: str) -> dict | list | None:
    """Pull a JSON object/array out of `text`, tolerant to prose around it.

    Order of attempts:
      1. The text already parses as JSON (clean case)
      2. There's a ```json … ``` (or ``` … ```) fence — extract its body
      3. Find first `{` (or `[`), then last matching `}` (or `]`), parse

    Returns None when no JSON-shaped object can be recovered. The caller
    decides what to do.
    """
    if not text:
        return None

    stripped = text.strip()

    # 1. Direct parse
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 2. Code fence
    fence = _JSON_FENCE_RE.search(stripped)
    if fence:
        body = fence.group(1).strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass

    # 3. Bracket scan — extract from first '{' to last '}' (or '[' to ']').
    # This handles prose-before-JSON like:
    #   "I have enough grounding. Producing the JSON skeleton.\n\n{...}"
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = stripped.find(open_ch)
        end = stripped.rfind(close_ch)
        if 0 <= start < end:
            candidate = stripped[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    return None


# ---------------------------------------------------------------------------
# Audit log — every call is persisted for later debugging
# ---------------------------------------------------------------------------

_LOG_RETENTION = 200  # keep last N call logs, oldest get pruned
_PURPOSE_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _purpose_from_prompt(prompt: str) -> str:
    """Infer a short purpose tag from the first line of the prompt.

    The prompts we send all start with `# Task: <purpose>`. Pull that out and
    slugify it. Falls back to 'call' if we can't recognize it.
    """
    first_line = prompt.splitlines()[0] if prompt else ""
    m = re.match(r"#\s*Task:\s*(.+)$", first_line.strip())
    label = m.group(1).strip() if m else "call"
    slug = _PURPOSE_RE.sub("-", label).strip("-").lower()
    return slug[:50] or "call"


def _logs_dir(repo_root: Path) -> Path:
    return repo_root / ".livedocs" / "logs"


def _prune_old_logs(directory: Path, keep: int = _LOG_RETENTION) -> None:
    """Best-effort retention: drop oldest .jsonl files beyond `keep`."""
    if not directory.is_dir():
        return
    files = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    excess = len(files) - keep
    for f in files[:excess] if excess > 0 else []:
        with contextlib.suppress(OSError):
            f.unlink()


def _write_call_log(
    repo_root: Path,
    *,
    purpose: str,
    cmd: list[str],
    system_prompt: str,
    user_prompt: str,
    stdout: str,
    stderr: str,
    returncode: int,
    elapsed_ms: int,
    parsed_envelope: dict[str, Any] | None,
    parsed_json: dict | list | None,
    extra_meta: dict[str, Any] | None = None,
) -> Path | None:
    """Persist one call to `<repo>/.livedocs/logs/<ts>-<purpose>.jsonl`.

    Returns the path that was written (None if writing failed — never raises).
    Each file is a single-line JSONL for tail-ability + grep-ability.
    """
    try:
        directory = _logs_dir(repo_root)
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        path = directory / f"{timestamp}-{purpose}.jsonl"

        # We strip the `claude` binary path so we don't leak full local paths.
        sanitized_cmd = ["claude" if i == 0 else c for i, c in enumerate(cmd)]

        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "purpose": purpose,
            "elapsed_ms": elapsed_ms,
            "returncode": returncode,
            "cmd": sanitized_cmd,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "stdout": stdout,
            "stderr": stderr,
            "parsed_envelope": parsed_envelope,
            "parsed_json": parsed_json,
        }
        if extra_meta:
            record["meta"] = extra_meta

        # Single-line JSON for grepability — but use ensure_ascii=False so
        # accents in prompts stay readable.
        path.write_text(
            json.dumps(record, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        _prune_old_logs(directory)
        return path
    except OSError:
        # Logging must never break the actual flow.
        return None


class ClaudeAgent:
    """Thin wrapper around Claude Code CLI in headless print mode.

    Each call() is independent (no session continuation in v0). The interview
    state on our side is preserved in <repo>/.livedocs/state.toml and we feed
    relevant context into each prompt.
    """

    def __init__(self, repo_root: Path, lang: str = "en", model: str | None = None):
        self.repo_root = repo_root
        self.lang = lang
        self.model = model

    def call(
        self,
        user_prompt: str,
        *,
        expect_json: bool = False,
        timeout: int = 300,
        extra_system: str | None = None,
        json_schema: dict | None = None,
    ) -> AgentResult:
        if not claude_available():
            raise AgentError(
                "Claude Code CLI not found on PATH. Install it from https://claude.com/code"
            )

        # Tool whitelist: Read/Glob/Grep pra explorar código, Write pra criar guides.
        # Edit/Bash/WebFetch fora do allowlist — agente NÃO pode modificar fonte do usuário.
        cmd: list[str] = [
            "claude",
            "--print",
            "--output-format=json",
            "--allowedTools", "Read,Glob,Grep,Write",
            "--add-dir", str(self.repo_root),
        ]

        if self.model:
            cmd.extend(["--model", self.model])

        # System prompt: skill + language pinning.
        # We use simple string replacement instead of `.format()` because the prompts
        # contain plenty of literal `{...}` JSON examples that would trip str.format.
        sys_prompt = LIVEDOCS_SYSTEM_PROMPT.replace("{lang}", self.lang)
        if extra_system:
            sys_prompt = f"{sys_prompt}\n\n---\n\n{extra_system}"
        cmd.extend(["--append-system-prompt", sys_prompt])

        if expect_json and json_schema is not None:
            cmd.extend(["--json-schema", json.dumps(json_schema)])

        cmd.append(user_prompt)

        purpose = _purpose_from_prompt(user_prompt)
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            _write_call_log(
                self.repo_root,
                purpose=purpose,
                cmd=cmd,
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                stdout="",
                stderr=f"timeout after {timeout}s",
                returncode=-1,
                elapsed_ms=elapsed_ms,
                parsed_envelope=None,
                parsed_json=None,
                extra_meta={"timeout_s": timeout},
            )
            raise AgentError(f"Claude Code CLI timed out after {timeout}s") from e

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if proc.returncode != 0 and not proc.stdout:
            _write_call_log(
                self.repo_root,
                purpose=purpose,
                cmd=cmd,
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                elapsed_ms=elapsed_ms,
                parsed_envelope=None,
                parsed_json=None,
            )
            raise AgentError(
                f"Claude Code CLI failed (exit {proc.returncode}): {proc.stderr.strip()[:500]}"
            )

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            _write_call_log(
                self.repo_root,
                purpose=purpose,
                cmd=cmd,
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                elapsed_ms=elapsed_ms,
                parsed_envelope=None,
                parsed_json=None,
                extra_meta={"envelope_parse_error": str(e)},
            )
            raise AgentError(f"Could not parse Claude CLI JSON envelope: {e}") from e

        is_error = bool(envelope.get("is_error"))
        text = envelope.get("result", "")
        cost = float(envelope.get("total_cost_usd", 0.0))
        duration = int(envelope.get("duration_ms", 0))

        json_data: dict | list | None = None
        if expect_json and not is_error and text:
            json_data = extract_json(text)

        _write_call_log(
            self.repo_root,
            purpose=purpose,
            cmd=cmd,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            stdout=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
            elapsed_ms=elapsed_ms,
            parsed_envelope=envelope,
            parsed_json=json_data,
            extra_meta={
                "expect_json": expect_json,
                "json_parsed": json_data is not None,
                "cost_usd": cost,
                "claude_duration_ms": duration,
            },
        )

        return AgentResult(
            text=text,
            json_data=json_data,
            cost_usd=cost,
            duration_ms=duration,
            is_error=is_error,
            error_message=text if is_error else None,
            raw_envelope=envelope,
        )


__all__ = [
    "AgentError",
    "AgentResult",
    "ClaudeAgent",
    "claude_available",
    "extract_json",
]
