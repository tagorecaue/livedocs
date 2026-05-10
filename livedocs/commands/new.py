"""`livedocs new` — start a new guide interview."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from livedocs import ui
from livedocs.commands.interview import (
    apply_answers_file,
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
    answers_file: Path | None = None,
) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1

    if not has_claude_code():
        ui.error(t("err_no_claude"))
        return 1

    # Non-interactive guard (#1): refuse early without an answers file so we
    # don't waste a Claude call on interview prep just to fail at the Q&A loop.
    if answers_file is None and ui.is_non_interactive():
        ui.error(t("err_non_interactive_needs_answers"))
        return 2

    state = load_state(repo_root)

    # Slug
    if slug is None:
        try:
            s = ui.ask_text(t("new_slug_q"))
        except ui.NonInteractiveError as e:
            ui.error(str(e))
            return 2
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
        try:
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
        except ui.NonInteractiveError as e:
            ui.error(str(e))
            return 2

    interview = start_new_interview(
        repo_root, cfg, state,
        slug=slug, domain=domain, title=title or slug,
    )
    if interview is None:
        return 1

    # Non-interactive path (#1): bypass the Q&A loop entirely.
    if answers_file is not None:
        try:
            n_ans, n_skip, unknown = apply_answers_file(repo_root, state, interview, answers_file)
        except (FileNotFoundError, ValueError) as e:
            ui.error(str(e))
            return 1
        ui.success(t("answers_file_applied", answered=n_ans, skipped=n_skip, total=len(interview.questions)))
        if unknown:
            ui.warn(t("answers_file_unknown_ids", ids=", ".join(unknown)))
        # Mark any leftover (no answer, not skipped) as skipped — we promised batch mode.
        now = datetime.now().isoformat(timespec="seconds")
        for q in interview.questions:
            if q.answer is None and not q.skipped:
                q.skipped = True
                q.answered_at = now
        save_state(repo_root, state)
        ok = generate_guides(repo_root, cfg, interview, global_state=state)
        save_state(repo_root, state)
        return 0 if ok else 1

    completed = run_interview_loop(repo_root, cfg, state, interview)
    if not completed:
        return 0  # paused, success-ish

    # All answered → generate guides
    ok = generate_guides(repo_root, cfg, interview, global_state=state)
    save_state(repo_root, state)
    return 0 if ok else 1
