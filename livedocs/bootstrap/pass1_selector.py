"""Interactive selector for incremental pass1 batches.

Before running passada 1, lets the user pick WHICH capabilities (or journeys)
to generate this round. Capabilities already fully `drafted` show as ✓ and are
skipped; partial ones show a counter (e.g. "2/4 prontos"). The user can:

  - Tudo o que falta — generate every pending article in one shot
  - Escolher capacidades — multi-select from the list
  - Só jornadas — skip caps, do journeys only
  - Sair sem gerar

When all capabilities + journeys are done, the selector short-circuits
and returns (set(), False, "all_done"): the orchestrator then knows to
mark phase 4 complete and move on.

Returns (capability_slugs, include_journeys, mode):
  - capability_slugs: set of capability slugs to process this round
                     (empty set + include_journeys=True means journeys-only)
  - include_journeys: whether to generate journeys this round
  - mode: "selected" | "all" | "journeys_only" | "all_done" | "abort"
"""

from __future__ import annotations

from typing import Literal

import questionary

from livedocs import ui
from livedocs.bootstrap.state import BootstrapState
from livedocs.ui import QUESTIONARY_STYLE

_DONE = {"drafted", "stitched", "refined"}

Mode = Literal["selected", "all", "journeys_only", "all_done", "abort"]


def _cap_progress(state: BootstrapState, cap_slug: str) -> tuple[int, int]:
    cap = next(
        (c for c in (state.taxonomy.capabilities if state.taxonomy else []) if c.slug == cap_slug),
        None,
    )
    if cap is None:
        return (0, 0)
    total = len(cap.articles)
    done = 0
    for a in cap.articles:
        rec_slug = f"{cap.slug}/{a.slug}"
        rec = next((g for g in state.guides if g.slug == rec_slug), None)
        if rec is not None and rec.status in _DONE:
            done += 1
    return (done, total)


def _journey_pending_count(state: BootstrapState) -> tuple[int, int]:
    if state.taxonomy is None:
        return (0, 0)
    total = len(state.taxonomy.journeys)
    done = 0
    for j in state.taxonomy.journeys:
        rec = next((g for g in state.guides if g.slug == j.slug), None)
        if rec is not None and rec.status in _DONE:
            done += 1
    return (done, total)


def select_pass1_scope(
    state: BootstrapState,
) -> tuple[set[str], bool, Mode]:
    """Show the selector menu. Returns (cap_slugs, include_journeys, mode)."""
    if state.taxonomy is None:
        return (set(), False, "abort")

    # Compute pending stats.
    pending_caps = []
    for c in state.taxonomy.capabilities:
        done, total = _cap_progress(state, c.slug)
        if done < total:
            pending_caps.append((c.slug, c.title, done, total))

    j_done, j_total = _journey_pending_count(state)
    journeys_pending = j_total - j_done

    if not pending_caps and journeys_pending == 0:
        return (set(), False, "all_done")

    # Non-interactive (CI / pipe): skip the menu, do everything.
    if ui.is_non_interactive():
        return ({c[0] for c in pending_caps}, journeys_pending > 0, "all")

    # Top-level choice.
    ui.console.print()
    ui.console.print("[brand]Passada 1 — gerar rascunhos[/brand]")
    pending_total = sum(t - d for (_, _, d, t) in pending_caps) + journeys_pending
    ui.console.print(
        f"  Pendentes: {pending_total} artigo(s) "
        f"({len(pending_caps)} capacidade(s), {journeys_pending} jornada(s))"
    )
    ui.console.print()

    choices = [
        f"Gerar tudo o que falta ({pending_total} artigos)",
        "Escolher capacidades (multi-seleção)",
    ]
    if journeys_pending:
        choices.append(f"Só jornadas ({journeys_pending})")
    choices.append("Sair sem gerar")

    try:
        choice = questionary.select(
            "O que gerar agora?",
            choices=choices,
            style=QUESTIONARY_STYLE,
        ).ask()
    except (KeyboardInterrupt, EOFError):
        return (set(), False, "abort")

    if choice is None or choice.startswith("Sair"):
        return (set(), False, "abort")

    if choice.startswith("Gerar tudo"):
        return ({c[0] for c in pending_caps}, True, "all")

    if choice.startswith("Só jornadas"):
        return (set(), True, "journeys_only")

    # Multi-select capabilities.
    cap_choices = [
        questionary.Choice(
            title=f"{slug}  ·  {title}  [{done}/{total}]",
            value=slug,
            checked=False,
        )
        for (slug, title, done, total) in pending_caps
    ]
    try:
        selected = questionary.checkbox(
            "Selecione capacidades (espaço marca, enter confirma)",
            choices=cap_choices,
            style=QUESTIONARY_STYLE,
        ).ask()
    except (KeyboardInterrupt, EOFError):
        return (set(), False, "abort")

    if not selected:
        return (set(), False, "abort")

    # Also offer journeys as a yes/no.
    inc_j = False
    if journeys_pending:
        try:
            inc_j = bool(
                questionary.confirm(
                    f"Incluir também as {journeys_pending} jornada(s) pendentes?",
                    default=False,
                    style=QUESTIONARY_STYLE,
                ).ask()
            )
        except (KeyboardInterrupt, EOFError):
            inc_j = False

    return (set(selected), inc_j, "selected")


__all__ = ["select_pass1_scope", "Mode"]
