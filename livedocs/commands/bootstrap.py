"""`livedocs bootstrap` — orchestrator.

The actual phase logic lives in `livedocs.bootstrap.*`. This module just
wires them together with phase guards + state persistence, so each phase
can be re-run independently via `--resume` and `--re-tax`.

Implemented now: phases 0–3 (guidance, scan, taxonomy, review).
Phases 4–7 follow in the next commit and will hang off the same loop.
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.agent import AgentError
from livedocs.bootstrap.guidance import collect_guidance
from livedocs.bootstrap.pass1_drafts import run_pass1
from livedocs.bootstrap.pass2_stitch import run_pass2
from livedocs.bootstrap.scanner import run_scan
from livedocs.bootstrap.state import (
    BootstrapState,
    load_bootstrap_state,
    save_bootstrap_state,
)
from livedocs.bootstrap.taxonomy import propose_taxonomy
from livedocs.bootstrap.taxonomy_review import review_taxonomy
from livedocs.i18n import t
from livedocs.state import load_config


def run_bootstrap(
    repo_root: Path,
    *,
    resume: bool = False,
    re_tax: bool = False,
    accept_taxonomy: bool = False,
) -> int:
    """Drive the seven-phase bootstrap pipeline.

    Returns the exit code: 0 on success, 1 on config error, 130 on
    user-aborted taxonomy review.
    """
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("bootstrap_need_init"))
        return 1

    state = load_bootstrap_state(repo_root) if resume else None
    if state is None:
        state = BootstrapState(status="scanning", last_completed_phase=-1)

    # --- Phase 0 --- Guidance ----------------------------------------------
    if state.last_completed_phase < 0:
        ui.section(t("bootstrap_phase_guidance"))
        guidance = collect_guidance(non_interactive=ui.is_non_interactive())
        state.guidance = guidance
        state.status = "scanning"
        state.last_completed_phase = 0
        save_bootstrap_state(repo_root, state)

    # --- Phase 1 --- Scan --------------------------------------------------
    if state.last_completed_phase < 1:
        ui.section(t("bootstrap_phase_scan"))
        cache_dir = repo_root / ".livedocs" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        scan = run_scan(repo_root, cache_dir)
        state.scan = scan
        state.status = "deriving"
        state.last_completed_phase = 1
        save_bootstrap_state(repo_root, state)

    # --- Phase 2 --- Taxonomy ----------------------------------------------
    if state.last_completed_phase < 2 or re_tax:
        ui.section(t("bootstrap_phase_taxonomy"))
        try:
            with ui.progress_spinner(t("bootstrap_taxonomy_deriving")):
                taxonomy = propose_taxonomy(
                    state.scan,
                    state.guidance,
                    repo_root,
                    lang=cfg.lang,
                )
        except AgentError as e:
            ui.error(f"{t('bootstrap_taxonomy_bad_json')} ({e})")
            return 2
        state.taxonomy = taxonomy
        state.status = "seeding"
        state.last_completed_phase = 2
        save_bootstrap_state(repo_root, state)

    # --- Phase 3 --- Taxonomy review ---------------------------------------
    if state.last_completed_phase < 3:
        ui.section(t("bootstrap_phase_taxonomy_review"))
        assert state.taxonomy is not None  # phase 2 wrote it
        reviewed = review_taxonomy(
            state.taxonomy,
            repo_root,
            non_interactive=ui.is_non_interactive(),
            auto_accept=accept_taxonomy,
        )
        if reviewed is None:
            ui.warn(t("bootstrap_review_aborted"))
            return 130
        state.taxonomy = reviewed
        state.status = "drafting"
        state.last_completed_phase = 3
        save_bootstrap_state(repo_root, state)

    # --- Phase 4 --- Passada 1: rascunhos isolados -------------------------
    if state.last_completed_phase < 4:
        ui.section(t("bootstrap_phase_pass1"))
        assert state.taxonomy is not None
        total = len(state.taxonomy.capabilities) + len(state.taxonomy.journeys)
        counter = {"n": 0}

        def _on_draft_done(rec, _total=total, _counter=counter):
            _counter["n"] += 1
            ui.info(
                f"[{_counter['n']}/{_total}] {rec.slug} → {rec.status} "
                f"(US${rec.draft_cost_usd:.4f})"
            )

        run_pass1(repo_root, cfg, state, on_guide_done=_on_draft_done)
        state.status = "stitching"
        state.last_completed_phase = 4
        save_bootstrap_state(repo_root, state)

    # --- Phase 5 --- Passada 2: costura ------------------------------------
    if state.last_completed_phase < 5:
        ui.section(t("bootstrap_phase_pass2"))
        drafted = [g for g in state.guides if g.status in ("drafted", "stitched", "refined")]
        total = len(drafted)
        counter = {"n": 0}

        def _on_stitch_done(rec, _total=total, _counter=counter):
            _counter["n"] += 1
            ui.info(
                f"[{_counter['n']}/{_total}] {rec.slug} → {rec.status} "
                f"(US${rec.stitch_cost_usd:.4f})"
            )

        run_pass2(repo_root, cfg, state, on_guide_done=_on_stitch_done)
        state.status = "refining"
        state.last_completed_phase = 5
        save_bootstrap_state(repo_root, state)

    # --- Phases 6-7 (next commit) ------------------------------------------
    ui.info(t("bootstrap_phases_6_7_todo"))
    return 0
