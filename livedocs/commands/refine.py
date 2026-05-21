"""`livedocs refine` — utility command.

This is NOT the legacy v0.1 `refine` (which has been removed). It exists
to handle the case where `livedocs bootstrap --skip-refinement` was used:
the maintainer can come back later, answer the pending questions in
batch, and re-run global_update — without redoing phases 0-5.

Behavior:
- Loads `bootstrap.toml`. If absent → error.
- Always runs refinement (phase 6) + global_update (phase 7) again
  against the current state. Both are idempotent for already-answered/refined
  items.
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.bootstrap.global_update import run_global_update
from livedocs.bootstrap.pending import find_open
from livedocs.bootstrap.refinement import run_refinement
from livedocs.bootstrap.state import (
    load_bootstrap_state,
    save_bootstrap_state,
)
from livedocs.state import load_config


def run_refine(repo_root: Path) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error("Nenhum projeto LiveDocs aqui. Rode `livedocs init` primeiro.")
        return 1

    state = load_bootstrap_state(repo_root)
    if state is None:
        ui.error(
            "Nenhum bootstrap encontrado. Rode `livedocs bootstrap` antes de `livedocs refine`."
        )
        return 1

    opens = find_open(state)
    ui.section(f"Refine — {len(opens)} pergunta(s) pendente(s) aberta(s)")
    if opens:
        for q in opens:
            ui.info(f"{q.id} ({q.guide_slug}): {q.question}")

    run_refinement(repo_root, cfg, state)
    # Phase 7 over only the now-answered guides.
    run_global_update(repo_root, cfg, state)

    # Bump the state to done if everything has been refined and there are no
    # more open questions. Otherwise leave whatever last_completed_phase was.
    remaining = find_open(state)
    if not remaining and all(g.status == "refined" or g.status == "stitched" for g in state.guides):
        state.status = "done"
        state.last_completed_phase = max(state.last_completed_phase, 7)
        save_bootstrap_state(repo_root, state)

    ui.success("Refine concluído.")
    return 0


__all__ = ["run_refine"]
