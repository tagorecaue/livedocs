"""Bootstrap phase 0 — collect free-form orientation from the maintainer.

Shows a panel explaining what the maintainer should type, then opens a
multi-line text prompt (questionary). When stdin is not a TTY or the caller
asked for non-interactive mode, reads whatever is piped on stdin (which may
be empty) and returns immediately.

Output: a `GuidanceText` with the text + ISO capture timestamp. Persisted
inside `BootstrapState.guidance` by the orchestrator.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

import questionary

from livedocs import ui
from livedocs.bootstrap.state import GuidanceText
from livedocs.i18n import t
from livedocs.ui import QUESTIONARY_STYLE

MAX_GUIDANCE_CHARS = 4000


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read_stdin_pipe() -> str:
    """Read all stdin until EOF. Returns empty string if nothing piped."""
    try:
        data = sys.stdin.read()
    except (OSError, ValueError):
        return ""
    return (data or "").strip()


def collect_guidance(non_interactive: bool = False) -> GuidanceText:
    """Phase 0: free-form orientation panel + multi-line text capture.

    `non_interactive=True` (or stdin not a TTY) reads stdin pipe instead of
    prompting; empty pipe → empty guidance, which is valid.
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

    if pipe_mode:
        text = _read_stdin_pipe()
    else:
        try:
            answer = questionary.text(
                "›",
                multiline=True,
                style=QUESTIONARY_STYLE,
                instruction="(Esc-Enter ou Ctrl-D para finalizar)",
            ).ask()
        except (KeyboardInterrupt, EOFError):
            answer = None
        text = (answer or "").strip()

    if len(text) > MAX_GUIDANCE_CHARS:
        ui.warn(t("bootstrap_guidance_too_long", n=len(text)))

    return GuidanceText(text=text, captured_at=_now_iso())


__all__ = ["collect_guidance", "MAX_GUIDANCE_CHARS"]
