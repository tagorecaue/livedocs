"""`livedocs status` — show overview of all guides and their state."""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.i18n import t
from livedocs.state import load_config, load_state


def run_status(repo_root: Path) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1

    state = load_state(repo_root)
    if not state.interviews:
        ui.info(t("status_no_guides"))
        return 0

    ui.section(t("status_title"))

    table = ui.make_table(
        "slug", "domain", "status",
        "Q ✓/total" if cfg.lang != "pt-BR" else "Q ✓/total",
    )
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
        table.add_row(
            slug, iv.domain, label,
            f"{answered + skipped}/{total}",
        )
    ui.console.print(table)
    ui.blank()
    ui.info(t("status_total", n=len(state.interviews)))
    return 0
