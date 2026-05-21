"""Agent wrapper — fala com o Claude Code CLI via subprocess.

Estratégia:
- Cada turno é um `claude --print --output-format=stream-json --verbose` com
  allowlist explícito de tools. Streaming permite mostrar progresso (qual
  arquivo o agente está lendo, qual padrão está buscando) enquanto ele trabalha.
- `--add-dir` pro repo do usuário.
- System prompt customizado via `--append-system-prompt`.
- User prompt como argumento posicional.
- Eventos do stream agregam o text final + alimentam um callback opcional
  pra UI mostrar "Lendo X.vue", "Buscando Y", etc.

Segurança:
- NÃO usamos `--permission-mode=acceptEdits`.
- `--allowedTools Read,Glob,Grep,Write` — agente não pode modificar fonte do usuário.

Auditoria:
- Cada chamada é loggada em `<repo>/.livedocs/logs/<timestamp>-<purpose>.jsonl`
  contendo system prompt, user prompt, full response, parsed JSON, custo, duração.
- Logs giram automaticamente (mantém últimos N por padrão).
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
import subprocess
import time
from collections.abc import Callable
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


# Callback invoked on each progress event. Receives a short human-readable
# string like "Reading packages/api/foo.ts" or "Searching 'split_partner'".
# Production wires this to a Rich live spinner; tests can capture into a list.
ProgressCallback = Callable[[str], None]


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
    """
    if not text:
        return None
    stripped = text.strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fence = _JSON_FENCE_RE.search(stripped)
    if fence:
        body = fence.group(1).strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass

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
# Stream event → progress label
# ---------------------------------------------------------------------------

def event_to_progress(event: dict, repo_root: Path | None = None) -> str | None:
    """Translate one stream-json event into a short progress line.

    Returns None for events that don't deserve a UI update (init, results,
    rate-limit chatter, etc).
    """
    if not isinstance(event, dict):
        return None

    etype = event.get("type")
    if etype != "assistant":
        return None

    msg = event.get("message") or {}
    contents = msg.get("content") or []
    if not isinstance(contents, list):
        return None

    for c in contents:
        if not isinstance(c, dict):
            continue
        ctype = c.get("type")

        if ctype == "tool_use":
            return _format_tool_use(c, repo_root)
        if ctype == "thinking":
            # Don't emit on every thinking chunk — the spinner already implies that.
            # We'll only return a label if there's nothing else more useful.
            return None
    return None


def _format_tool_use(c: dict, repo_root: Path | None) -> str | None:
    name = c.get("name", "")
    inp = c.get("input") or {}

    if name == "Read":
        path = str(inp.get("file_path", ""))
        return f"Lendo {_relativize(path, repo_root)}"
    if name == "Glob":
        pattern = str(inp.get("pattern", ""))
        return f"Buscando arquivos: {pattern}"
    if name == "Grep":
        pattern = str(inp.get("pattern", ""))
        path = str(inp.get("path", ""))
        suffix = f" em {_relativize(path, repo_root)}" if path else ""
        return f"Procurando \"{pattern}\"{suffix}"
    if name == "Write":
        path = str(inp.get("file_path", ""))
        return f"Escrevendo {_relativize(path, repo_root)}"
    return None


def _relativize(path: str, repo_root: Path | None) -> str:
    if not repo_root or not path:
        return path
    try:
        return str(Path(path).resolve().relative_to(repo_root.resolve()))
    except (ValueError, OSError):
        return path


# ---------------------------------------------------------------------------
# Audit log — every call is persisted for later debugging
# ---------------------------------------------------------------------------

_LOG_RETENTION = 200
_PURPOSE_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _purpose_from_prompt(prompt: str) -> str:
    first_line = prompt.splitlines()[0] if prompt else ""
    m = re.match(r"#\s*Task:\s*(.+)$", first_line.strip())
    label = m.group(1).strip() if m else "call"
    slug = _PURPOSE_RE.sub("-", label).strip("-").lower()
    return slug[:50] or "call"


def _logs_dir(repo_root: Path) -> Path:
    return repo_root / ".livedocs" / "logs"


def _prune_old_logs(directory: Path, keep: int = _LOG_RETENTION) -> None:
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
    try:
        directory = _logs_dir(repo_root)
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        path = directory / f"{timestamp}-{purpose}.jsonl"
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
        path.write_text(
            json.dumps(record, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        _prune_old_logs(directory)
        return path
    except OSError:
        return None


class ClaudeAgent:
    """Thin wrapper around Claude Code CLI in stream-json mode."""

    def __init__(self, repo_root: Path, lang: str = "en", model: str | None = None):
        self.repo_root = repo_root
        self.lang = lang
        self.model = model

    DEFAULT_ALLOWED_TOOLS: tuple[str, ...] = ("Read", "Glob", "Grep", "Write")
    DEFAULT_DISALLOWED_TOOLS: tuple[str, ...] = ("Edit", "Bash", "WebFetch")

    def call(
        self,
        user_prompt: str,
        *,
        expect_json: bool = False,
        timeout: int = 300,
        extra_system: str | None = None,
        json_schema: dict | None = None,
        on_progress: ProgressCallback | None = None,
        allowed_tools: list[str] | None = None,
    ) -> AgentResult:
        """Run one Claude turn.

        on_progress (optional): callable invoked with short progress strings
        ("Lendo X.vue", "Procurando 'foo'") as the agent works through
        tool calls. Errors in the callback are swallowed — UI bugs must
        never break the actual agent run.
        """
        if not claude_available():
            raise AgentError(
                "Claude Code CLI not found on PATH. Install it from https://claude.com/code"
            )

        # stream-json requires --verbose. We capture stdout line-by-line.
        cmd: list[str] = [
            "claude",
            "--print",
            "--output-format=stream-json",
            "--verbose",
            "--allowedTools", ",".join(allowed_tools or self.DEFAULT_ALLOWED_TOOLS),
            "--disallowedTools", ",".join(self.DEFAULT_DISALLOWED_TOOLS),
            "--add-dir", str(self.repo_root),
        ]

        if self.model:
            cmd.extend(["--model", self.model])

        sys_prompt = LIVEDOCS_SYSTEM_PROMPT.replace("{lang}", self.lang)
        if extra_system:
            sys_prompt = f"{sys_prompt}\n\n---\n\n{extra_system}"
        cmd.extend(["--append-system-prompt", sys_prompt])

        if expect_json and json_schema is not None:
            cmd.extend(["--json-schema", json.dumps(json_schema)])

        cmd.append(user_prompt)

        purpose = _purpose_from_prompt(user_prompt)
        t0 = time.monotonic()

        # Stream Popen so we can read events as they arrive.
        try:
            proc = subprocess.Popen(  # noqa: S603 — trusted CLI
                cmd,
                cwd=self.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # line-buffered
            )
        except OSError as e:
            raise AgentError(f"Failed to spawn claude: {e}") from e

        stdout_lines: list[str] = []
        events: list[dict] = []
        final_envelope: dict[str, Any] | None = None

        def emit_progress(label: str) -> None:
            if on_progress is None:
                return
            with contextlib.suppress(Exception):
                on_progress(label)

        deadline = t0 + timeout
        try:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                if time.monotonic() > deadline:
                    proc.kill()
                    raise AgentError(f"Claude Code CLI timed out after {timeout}s")

                line = raw_line.rstrip("\n")
                if not line:
                    continue
                stdout_lines.append(line)

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                events.append(event)

                # The final 'result' event holds the full envelope (text result,
                # cost, duration, etc) — same shape as --output-format=json.
                if event.get("type") == "result":
                    final_envelope = event

                # UI progress
                label = event_to_progress(event, self.repo_root)
                if label:
                    emit_progress(label)

            proc.wait(timeout=max(1.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            proc.kill()
            raise AgentError(f"Claude Code CLI timed out after {timeout}s") from None
        except AgentError:
            raise
        finally:
            stderr_text = proc.stderr.read() if proc.stderr else ""

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        stdout_text = "\n".join(stdout_lines)
        returncode = proc.returncode if proc.returncode is not None else -1

        if returncode != 0 and final_envelope is None:
            _write_call_log(
                self.repo_root,
                purpose=purpose,
                cmd=cmd,
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                stdout=stdout_text,
                stderr=stderr_text,
                returncode=returncode,
                elapsed_ms=elapsed_ms,
                parsed_envelope=None,
                parsed_json=None,
                extra_meta={"events_count": len(events)},
            )
            raise AgentError(
                f"Claude Code CLI failed (exit {returncode}): {stderr_text.strip()[:500]}"
            )

        if final_envelope is None:
            _write_call_log(
                self.repo_root,
                purpose=purpose,
                cmd=cmd,
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                stdout=stdout_text,
                stderr=stderr_text,
                returncode=returncode,
                elapsed_ms=elapsed_ms,
                parsed_envelope=None,
                parsed_json=None,
                extra_meta={"events_count": len(events), "missing_result_event": True},
            )
            raise AgentError("Claude stream ended without a 'result' event")

        is_error = bool(final_envelope.get("is_error"))
        text = final_envelope.get("result", "")
        cost = float(final_envelope.get("total_cost_usd", 0.0))
        duration = int(final_envelope.get("duration_ms", 0))

        json_data: dict | list | None = None
        if expect_json and not is_error and text:
            json_data = extract_json(text)

        _write_call_log(
            self.repo_root,
            purpose=purpose,
            cmd=cmd,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            stdout=stdout_text,
            stderr=stderr_text,
            returncode=returncode,
            elapsed_ms=elapsed_ms,
            parsed_envelope=final_envelope,
            parsed_json=json_data,
            extra_meta={
                "expect_json": expect_json,
                "json_parsed": json_data is not None,
                "cost_usd": cost,
                "claude_duration_ms": duration,
                "events_count": len(events),
            },
        )

        return AgentResult(
            text=text,
            json_data=json_data,
            cost_usd=cost,
            duration_ms=duration,
            is_error=is_error,
            error_message=text if is_error else None,
            raw_envelope=final_envelope,
        )


__all__ = [
    "AgentError",
    "AgentResult",
    "ClaudeAgent",
    "ProgressCallback",
    "claude_available",
    "event_to_progress",
    "extract_json",
]
