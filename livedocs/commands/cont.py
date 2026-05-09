"""`livedocs continue` — resume an in-progress interview."""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.commands.interview import generate_guides, run_interview_loop
from livedocs.detect import has_claude_code
from livedocs.i18n import t
from livedocs.state import load_config, load_state, save_state


def run_continue(repo_root: Path, slug: str | None = None) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1
    if not has_claude_code():
        ui.error(t("err_no_claude"))
        return 1

    state = load_state(repo_root)
    in_progress = {
        s: iv for s, iv in state.interviews.items() if iv.status == "in_progress"
    }
    if not in_progress:
        ui.info("Nenhuma entrevista em andamento." if cfg.lang == "pt-BR"
                else "No interview in progress.")
        return 0

    if slug is None:
        if state.last_touched_slug and state.last_touched_slug in in_progress:
            slug = state.last_touched_slug
        else:
            choices = [(f"{s} ({iv.domain})", s) for s, iv in in_progress.items()]
            picked = ui.ask_choice(
                "Qual entrevista continuar?" if cfg.lang == "pt-BR" else "Which interview to continue?",
                choices=choices,
            )
            if picked is None:
                return 130
            slug = picked

    if slug not in state.interviews:
        ui.error(f"'{slug}' not found.")
        return 1

    interview = state.interviews[slug]
    completed = run_interview_loop(repo_root, cfg, state, interview)
    if not completed:
        return 0

    ok = generate_guides(repo_root, cfg, interview)
    save_state(repo_root, state)
    return 0 if ok else 1
