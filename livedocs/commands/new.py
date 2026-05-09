"""`livedocs new` — start a new guide interview."""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.commands.interview import (
    generate_guides,
    run_interview_loop,
    start_new_interview,
)
from livedocs.detect import has_claude_code
from livedocs.i18n import t
from livedocs.state import (
    load_config,
    load_state,
    save_state,
)


def run_new(
    repo_root: Path,
    *,
    slug: str | None = None,
    domain: str | None = None,
    title: str | None = None,
) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1

    if not has_claude_code():
        ui.error(t("err_no_claude"))
        return 1

    state = load_state(repo_root)

    # Slug
    if slug is None:
        s = ui.ask_text(t("new_slug_q"))
        if s is None or not s.strip():
            ui.warn(t("abort"))
            return 130
        slug = s.strip()

    if slug in state.interviews:
        ui.warn(f"'{slug}' já existe — use [bold]livedocs continue {slug}[/bold]." if cfg.lang == "pt-BR"
                else f"'{slug}' already exists — use [bold]livedocs continue {slug}[/bold].")
        return 1

    # Domain
    if domain is None:
        existing_domains = sorted({iv.domain for iv in state.interviews.values()})
        if existing_domains:
            choices = [(d, d) for d in existing_domains] + [(t("new_domain_new"), "__new__")]
            picked = ui.ask_choice(t("new_domain_q"), choices=choices, default=existing_domains[0])
            if picked is None:
                ui.warn(t("abort"))
                return 130
            if picked == "__new__":
                d = ui.ask_text(t("new_domain_q"))
                if d is None or not d.strip():
                    ui.warn(t("abort"))
                    return 130
                domain = d.strip()
            else:
                domain = picked
        else:
            d = ui.ask_text(t("new_domain_q"))
            if d is None or not d.strip():
                ui.warn(t("abort"))
                return 130
            domain = d.strip()

    interview = start_new_interview(
        repo_root, cfg, state,
        slug=slug, domain=domain, title=title or slug,
    )
    if interview is None:
        return 1

    completed = run_interview_loop(repo_root, cfg, state, interview)
    if not completed:
        return 0  # paused, success-ish

    # All answered → generate guides
    ok = generate_guides(repo_root, cfg, interview)
    save_state(repo_root, state)
    return 0 if ok else 1
