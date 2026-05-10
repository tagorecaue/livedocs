"""Agent wrapper — fala com o Claude Code CLI via subprocess.

Estratégia:
- Cada turno é um `claude --print --output-format=json` com allowlist explícito de tools.
- Adicionamos `--add-dir` pro repo do usuário (Claude já tá no cwd, mas explicitar).
- Passamos o system prompt customizado via `--append-system-prompt`.
- O prompt do user vai como argumento posicional.
- Lemos o JSON, extraímos `result`, parseamos como JSON estruturado quando aplicável.

Segurança (issue #6):
- NÃO usamos `--permission-mode=acceptEdits` (foot-gun: dá Edit livre em todo --add-dir).
- Usamos `--allowedTools` com whitelist mínima: Read, Glob, Grep, Write.
- Edit/Bash/WebFetch ficam de fora — agente não pode modificar fonte do usuário.

Sem streaming no v0 — usamos spinner do nosso lado e mostramos o output quando terminar.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from livedocs.skill import LIVEDOCS_SYSTEM_PROMPT


@dataclass
class AgentResult:
    text: str
    json_data: dict | list | None
    cost_usd: float
    duration_ms: int
    is_error: bool
    error_message: str | None = None


class AgentError(Exception):
    pass


def claude_available() -> bool:
    return shutil.which("claude") is not None


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
        # Isso troca `--permission-mode=acceptEdits` (que liberava Edit em --add-dir).
        cmd: list[str] = [
            "claude",
            "--print",
            "--output-format=json",
            "--allowedTools", "Read,Glob,Grep,Write",
            "--add-dir", str(self.repo_root),
        ]

        if self.model:
            cmd.extend(["--model", self.model])

        # System prompt: skill + language pinning
        sys_prompt = LIVEDOCS_SYSTEM_PROMPT.format(lang=self.lang)
        if extra_system:
            sys_prompt = f"{sys_prompt}\n\n---\n\n{extra_system}"
        cmd.extend(["--append-system-prompt", sys_prompt])

        if expect_json and json_schema is not None:
            cmd.extend(["--json-schema", json.dumps(json_schema)])

        cmd.append(user_prompt)

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
            raise AgentError(f"Claude Code CLI timed out after {timeout}s") from e

        if proc.returncode != 0 and not proc.stdout:
            raise AgentError(
                f"Claude Code CLI failed (exit {proc.returncode}): {proc.stderr.strip()[:500]}"
            )

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise AgentError(f"Could not parse Claude CLI JSON envelope: {e}") from e

        is_error = bool(envelope.get("is_error"))
        text = envelope.get("result", "")
        cost = float(envelope.get("total_cost_usd", 0.0))
        duration = int(envelope.get("duration_ms", 0))

        json_data: dict | list | None = None
        if expect_json and not is_error and text:
            text_stripped = text.strip()
            # Remove possible code fence
            if text_stripped.startswith("```"):
                lines = text_stripped.splitlines()
                # drop first/last fence lines
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text_stripped = "\n".join(lines).strip()
            try:
                json_data = json.loads(text_stripped)
            except json.JSONDecodeError:
                json_data = None  # caller decides what to do

        return AgentResult(
            text=text,
            json_data=json_data,
            cost_usd=cost,
            duration_ms=duration,
            is_error=is_error,
            error_message=text if is_error else None,
        )
