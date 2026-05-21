"""Bootstrap phase 0 — collect free-form orientation from the maintainer.

Strategy: open the user's `$EDITOR` on a draft file inside
`.livedocs/guidance.draft.md`. The user edits in their preferred editor
(vim, nano, vscode --wait, etc.) and SAVES — meaning the text hits disk
the moment they Ctrl-S, well before any later phase can crash. If the
bootstrap is re-run later, we offer to recover from the existing draft.

Fallbacks (in order):
  1. `$EDITOR <path>` on the draft file (preferred — survives crashes).
  2. Inline questionary multiline (memory-only — last resort).
  3. stdin pipe (non-interactive / scripts).

The draft file is deleted once the guidance is successfully persisted
into `bootstrap.toml`. Until then it lingers, which is the point.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import questionary

from livedocs import ui
from livedocs.bootstrap.state import GuidanceText
from livedocs.i18n import t
from livedocs.ui import QUESTIONARY_STYLE

MAX_GUIDANCE_CHARS = 4000
DRAFT_FILENAME = "guidance.draft.md"
DRAFT_HEADER = """<!--
LiveDocs guidance — texto livre que orienta o agente durante o bootstrap.

Conte quem você é, o que o sistema faz, para que serve. Cole referências,
instruções gerais, qualquer coisa que ajude a IA a documentar o sistema.

Linhas começando com `<!--` e terminando com `-->` (HTML comments) são
removidas antes de enviar pro agente. Apague este cabeçalho ou deixe;
tanto faz, ele não vai pro prompt.

Salve o arquivo e feche o editor para continuar. Texto vazio é OK.
-->

"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read_stdin_pipe() -> str:
    try:
        data = sys.stdin.read()
    except (OSError, ValueError):
        return ""
    return (data or "").strip()


def _resolve_editor() -> list[str] | None:
    """Pick an editor command. Honour $VISUAL, then $EDITOR, then sane defaults."""
    for env_var in ("VISUAL", "EDITOR"):
        cmd = os.environ.get(env_var)
        if cmd:
            # Allow values like "code --wait" or "nano".
            return cmd.split()
    for fallback in ("nano", "vim", "vi"):
        if shutil.which(fallback):
            return [fallback]
    return None


def _strip_html_comments(text: str) -> str:
    """Remove <!-- ... --> blocks (single or multi-line) from the draft text."""
    import re

    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def _draft_path(repo_root: Path | None) -> Path | None:
    if repo_root is None:
        return None
    return repo_root / ".livedocs" / DRAFT_FILENAME


def _collect_via_editor(draft: Path) -> str | None:
    """Open the user's editor on the draft file. Returns text or None on failure."""
    editor = _resolve_editor()
    if editor is None:
        return None

    draft.parent.mkdir(parents=True, exist_ok=True)
    if not draft.exists():
        draft.write_text(DRAFT_HEADER, encoding="utf-8")

    ui.hint(f"Abrindo {editor[0]} em {draft.relative_to(draft.parent.parent)} — salve e feche para continuar.")
    try:
        subprocess.run([*editor, str(draft)], check=False)  # noqa: S603 — trusted env
    except (OSError, FileNotFoundError) as e:
        ui.warn(f"Não consegui abrir o editor ({e}); caindo no modo inline.")
        return None

    try:
        raw = draft.read_text(encoding="utf-8")
    except OSError:
        return None
    return _strip_html_comments(raw)


def _collect_via_questionary() -> str:
    try:
        answer = questionary.text(
            "›",
            multiline=True,
            style=QUESTIONARY_STYLE,
            instruction="(Esc-Enter ou Ctrl-D para finalizar)",
        ).ask()
    except (KeyboardInterrupt, EOFError):
        answer = None
    return (answer or "").strip()


def _recover_existing_draft(draft: Path) -> str | None:
    """If a draft exists from a prior crashed run, offer to recover it."""
    if not draft.exists():
        return None
    try:
        raw = draft.read_text(encoding="utf-8")
    except OSError:
        return None
    body = _strip_html_comments(raw)
    if not body:
        return None
    ui.warn(f"Rascunho de guidance anterior encontrado em {draft.name} ({len(body)} chars).")
    try:
        choice = questionary.select(
            "O que fazer?",
            choices=[
                "Recuperar e reaproveitar",
                "Abrir editor com o rascunho pra continuar editando",
                "Descartar e começar do zero",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()
    except (KeyboardInterrupt, EOFError):
        return body  # safest default: recover silently
    if choice and choice.startswith("Recuperar"):
        return body
    if choice and choice.startswith("Descartar"):
        draft.unlink(missing_ok=True)
        return None
    # "Abrir editor" → return None, caller will open editor on the existing file
    return None


def collect_guidance(
    non_interactive: bool = False, repo_root: Path | None = None
) -> GuidanceText:
    """Phase 0: free-form orientation, persisted-to-disk as you type.

    `repo_root` enables the editor-on-file flow. When omitted (older callers),
    falls back to memory-only questionary — present for backwards compatibility
    but users should pass repo_root so their text survives crashes.

    `non_interactive=True` (or stdin not a TTY) reads stdin pipe instead.
    """
    ui.console.print()
    ui.console.print(f"[brand]{t('bootstrap_guidance_intro')}[/brand]")
    ui.console.print()
    ui.console.print(t("bootstrap_guidance_prompt"))
    ui.console.print()

    pipe_mode = non_interactive
    if not pipe_mode:
        try:
            pipe_mode = not sys.stdin.isatty()
        except (AttributeError, ValueError):
            pipe_mode = True

    text = ""
    draft = _draft_path(repo_root)

    if pipe_mode:
        text = _read_stdin_pipe()
    else:
        # Try editor flow first when we have a place to store the draft.
        if draft is not None:
            recovered = _recover_existing_draft(draft)
            if recovered is not None:
                text = recovered
            else:
                via_editor = _collect_via_editor(draft)
                text = via_editor if via_editor is not None else _collect_via_questionary()
        else:
            text = _collect_via_questionary()

    text = text.strip()

    if len(text) > MAX_GUIDANCE_CHARS:
        ui.warn(t("bootstrap_guidance_too_long", n=len(text)))

    return GuidanceText(text=text, captured_at=_now_iso())


def clear_draft(repo_root: Path) -> None:
    """Called by the orchestrator once guidance is safely in bootstrap.toml."""
    draft = _draft_path(repo_root)
    if draft is not None:
        draft.unlink(missing_ok=True)


__all__ = ["collect_guidance", "clear_draft", "MAX_GUIDANCE_CHARS"]
