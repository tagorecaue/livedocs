"""`livedocs status` — show overview of all guides and their state.

After printing the table, offers a picker so the user can act on any guide
without having to type its slug. Actions depend on the guide's status:
  draft       → start
  in_progress → continue
  generated   → approve
  reviewed    → (no action yet — Phase 3 may add regenerate)
  stale       → (Phase 3)
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from livedocs import ui
from livedocs.i18n import t
from livedocs.state import load_config, load_state


def run_status(repo_root: Path, with_cost: bool = False) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1

    state = load_state(repo_root)
    if not state.interviews:
        ui.info(t("status_no_guides"))
        return 0

    ui.section(t("status_title"))

    columns = ["slug", "domain", "status", "Q ✓/total"]
    if with_cost:
        columns.extend(["calls", "US$"])

    table = ui.make_table(*columns)
    total_cost = 0.0
    total_calls = 0
    for slug, iv in sorted(state.interviews.items()):
        answered = sum(1 for q in iv.questions if q.answer is not None)
        skipped = sum(1 for q in iv.questions if q.skipped)
        total = len(iv.questions)
        if iv.status == "in_progress":
            label = f"[warn]{t('status_in_progress')}[/warn]"
        elif iv.status == "generated":
            label = f"[accent]{t('status_generated')}[/accent]"
        elif iv.status == "reviewed":
            label = f"[ok]{t('status_reviewed')}[/ok]"
        elif iv.status == "stale":
            label = f"[err]{t('status_stale')}[/err]"
        else:
            label = t("status_draft")
        row = [slug, iv.domain, label, f"{answered + skipped}/{total}"]
        if with_cost:
            row.extend([str(iv.agent_calls), f"{iv.total_cost_usd:.4f}"])
            total_cost += iv.total_cost_usd
            total_calls += iv.agent_calls
        table.add_row(*row)
    ui.console.print(table)
    ui.blank()
    ui.info(t("status_total", n=len(state.interviews)))
    if with_cost:
        ui.info(t("status_total_cost", calls=total_calls, cost=total_cost))

    # ---- Picker: act on a guide directly from status ----
    actionable = [iv for iv in state.interviews.values() if _has_action(iv)]
    if not actionable:
        # Nothing actionable (everything reviewed and no stale). Just return.
        return 0

    with contextlib.suppress(ui.NonInteractiveError):
        # Non-TTY (CI, pipes): the status print was the whole job — skip picker.
        _offer_actions(repo_root, state)

    return 0


def _has_action(iv) -> bool:
    """Whether this guide has at least one available action right now."""
    return iv.status in ("draft", "in_progress", "generated")


def _offer_actions(repo_root: Path, state) -> None:
    """Mini-menu inside status: pick a guide → pick an action.

    Returns to caller without exit so run_root's main loop continues.
    """
    cfg = load_config(repo_root)
    assert cfg is not None  # caller verified

    # Build the per-guide choices list. We show available actions inline so the
    # user doesn't need to interpret status. Some guides have multiple actions
    # (e.g. 'generated' can be approved OR refined).
    choices: list[tuple[str, str]] = []
    for slug, iv in sorted(state.interviews.items()):
        for action, verb in _actions_for(iv, cfg.lang):
            label = f"{slug}  [{iv.domain}]  — {verb}"
            choices.append((label, f"{action}:{slug}"))

    if not choices:
        return

    back_label = "← Voltar" if cfg.lang == "pt-BR" else "← Back"
    choices.append((back_label, "__back__"))

    ui.blank()
    pick_q = (
        "Quer agir em algum guia?"
        if cfg.lang == "pt-BR"
        else "Want to act on any guide?"
    )
    picked = ui.ask_choice(pick_q, choices=choices)
    if picked is None or picked == "__back__":
        return

    action, slug = picked.split(":", 1)
    iv = state.interviews[slug]
    _execute_action(repo_root, iv, action)


def _actions_for(iv, lang: str) -> list[tuple[str, str]]:
    """Return list of (action_id, human_verb) tuples for this guide.

    A guide can have 0, 1, or 2 actions:
      - draft → start
      - in_progress → continue
      - generated → approve  +  refine
      - reviewed → refine
      - other → nothing
    """
    pt = lang == "pt-BR"
    out: list[tuple[str, str]] = []
    if iv.status == "draft":
        out.append(("start", "começar" if pt else "start"))
    elif iv.status == "in_progress":
        out.append(("continue", "continuar" if pt else "continue"))
    elif iv.status == "generated":
        out.append(("approve", "aprovar" if pt else "approve"))
        out.append(("refine", "refinar" if pt else "refine"))
    elif iv.status == "reviewed":
        out.append(("refine", "refinar" if pt else "refine"))
    return out


def _execute_action(repo_root: Path, iv, action: str) -> None:
    """Dispatch the chosen action for this guide."""
    # Local imports avoid circular import at module load time.
    from livedocs.commands.approve import run_approve
    from livedocs.commands.cont import run_continue
    from livedocs.commands.new import run_new
    from livedocs.commands.refine import run_refine

    if action == "continue":
        run_continue(repo_root, slug=iv.slug)
    elif action == "approve":
        run_approve(repo_root, slug=iv.slug)
    elif action == "start":
        run_new(repo_root, slug=iv.slug, domain=iv.domain)
    elif action == "refine":
        run_refine(repo_root, slug=iv.slug)
