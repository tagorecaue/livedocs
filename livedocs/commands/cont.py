"""`livedocs continue` — resume an in-progress adaptive interview."""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.commands.interview import (
    closing_step,
    generate_guides,
    pregen_self_audit,
    run_adaptive_loop,
)
from livedocs.detect import has_claude_code
from livedocs.i18n import t
from livedocs.state import load_config, load_state, save_state


def run_continue(
    repo_root: Path,
    slug: str | None = None,
    *,
    answers_file: Path | None = None,
) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1
    if not has_claude_code():
        ui.error(t("err_no_claude"))
        return 1

    if answers_file is not None:
        ui.warn(
            "--answers-file ainda não foi reescrito para o fluxo fact-driven da v0.2."
            if cfg.lang == "pt-BR"
            else "--answers-file has not been rewritten for the v0.2 fact-driven flow."
        )
        return 2

    state = load_state(repo_root)
    in_progress = {s: iv for s, iv in state.interviews.items() if iv.status == "in_progress"}
    if not in_progress:
        ui.info(
            "Nenhuma entrevista em andamento." if cfg.lang == "pt-BR" else "No interview in progress."
        )
        return 0

    if slug is None:
        if state.last_touched_slug and state.last_touched_slug in in_progress:
            slug = state.last_touched_slug
        else:
            try:
                choices = [(f"{s} ({iv.domain})", s) for s, iv in in_progress.items()]
                picked = ui.ask_choice(
                    "Qual entrevista continuar?"
                    if cfg.lang == "pt-BR"
                    else "Which interview to continue?",
                    choices=choices,
                )
            except ui.NonInteractiveError as e:
                ui.error(str(e))
                return 2
            if picked is None:
                return 130
            slug = picked

    if slug not in state.interviews:
        ui.error(t("err_slug_not_found", slug=slug))
        return 1

    interview = state.interviews[slug]
    completed = run_adaptive_loop(repo_root, cfg, state, interview)
    if not completed:
        return 0  # paused, success-ish

    # Closing step — "anything to add?" valve. Runs BEFORE the pregen audit.
    closing_step(repo_root, cfg, interview)
    save_state(repo_root, state)

    # Pre-generation self-audit
    ready, audit = pregen_self_audit(repo_root, cfg, interview)
    if not ready:
        ui.warn(
            (audit.get("block_reason") if isinstance(audit, dict) else None)
            or (
                "Audit indicou que faltam respostas críticas."
                if cfg.lang == "pt-BR"
                else "Audit reports critical answers still missing."
            )
        )
        save_state(repo_root, state)
        return 0

    ok = generate_guides(repo_root, cfg, interview, global_state=state)
    save_state(repo_root, state)
    return 0 if ok else 1
