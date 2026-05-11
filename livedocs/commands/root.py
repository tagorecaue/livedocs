"""`livedocs` (no subcommand) — Where we left off + smart menu.

This is the most important UX: friendly, knows the state, suggests the right
action. Replaces the cognitive load of remembering subcommands.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from livedocs import ui
from livedocs.commands.approve import run_approve
from livedocs.commands.cont import run_continue
from livedocs.commands.init import run_init
from livedocs.commands.new import run_new
from livedocs.commands.review import run_review
from livedocs.commands.status import run_status
from livedocs.detect import has_claude_code
from livedocs.i18n import set_lang, t
from livedocs.state import load_config, load_state


def run_root(repo_root: Path | None) -> int:
    """No subcommand path. Loops the menu until the user chooses to exit.

    Each menu cycle:
      1. Show the splash + 'where we left off' snapshot
      2. Build a smart menu from current state
      3. Run the chosen action
      4. Loop back unless the user picked 'exit' or hit Ctrl-C
    """
    cwd = Path.cwd()
    if repo_root is None or load_config(repo_root) is None:
        return _offer_init(cwd)

    cfg = load_config(repo_root)
    assert cfg is not None  # narrowed by the check above
    set_lang(cfg.lang)
    ui.splash()

    while True:
        # Reload state on every cycle — actions may have mutated it on disk.
        state = load_state(repo_root)
        try:
            picked = _render_menu_and_pick(repo_root, cfg, state)
        except ui.NonInteractiveError:
            # No TTY → can't loop, just show splash + bail.
            return 0
        if picked is None or picked == "exit":
            return 0
        try:
            _dispatch(repo_root, picked)
        except KeyboardInterrupt:
            # User hit Ctrl-C inside the action — back to menu, not exit.
            ui.blank()
            ui.warn(t("abort"))
            continue


def _render_menu_and_pick(repo_root: Path, cfg, state) -> str | None:
    """Print the 'where we left off' snapshot, build the menu, return the pick."""

    # Compose a "where we left off" snapshot
    in_progress = [iv for iv in state.interviews.values() if iv.status == "in_progress"]
    generated = [iv for iv in state.interviews.values() if iv.status == "generated"]
    reviewed = [iv for iv in state.interviews.values() if iv.status == "reviewed"]
    stale = [iv for iv in state.interviews.values() if iv.status == "stale"]

    ui.section(t("where_we_left"))
    if not state.interviews:
        ui.info("Nenhum guia ainda." if cfg.lang == "pt-BR" else "No guides yet.")
    else:
        ui.console.print(
            f"  [ok]{len(reviewed)}[/ok] {('aprovados' if cfg.lang == 'pt-BR' else 'approved')}"
            + f"   ·   [accent]{len(generated)}[/accent] {('aguardando aprovação' if cfg.lang == 'pt-BR' else 'awaiting approval')}"
            + f"   ·   [warn]{len(in_progress)}[/warn] {('em andamento' if cfg.lang == 'pt-BR' else 'in progress')}"
            + (f"   ·   [err]{len(stale)}[/err] {('defasados' if cfg.lang == 'pt-BR' else 'stale')}" if stale else "")
        )
        if state.last_touched_slug and state.last_touched_slug in state.interviews:
            iv = state.interviews[state.last_touched_slug]
            answered = sum(1 for q in iv.questions if q.answer is not None or q.skipped)
            total = len(iv.questions)
            label = (
                f"  [muted]· último toque:[/muted] [bold]{iv.slug}[/bold] "
                f"[muted]({iv.domain}, {answered}/{total})[/muted]"
                if cfg.lang == "pt-BR"
                else f"  [muted]· last touched:[/muted] [bold]{iv.slug}[/bold] "
                f"[muted]({iv.domain}, {answered}/{total})[/muted]"
            )
            ui.console.print(label)

    # Build smart menu
    choices: list[tuple[str, str]] = []

    if in_progress:
        # Find the freshest in-progress interview
        fresh = max(in_progress, key=lambda iv: iv.last_touched_at)
        label = (
            f"Continuar: {fresh.slug} ({fresh.domain})"
            if cfg.lang == "pt-BR"
            else f"Continue: {fresh.slug} ({fresh.domain})"
        )
        choices.append((label, f"continue:{fresh.slug}"))

    if generated:
        fresh_gen = max(generated, key=lambda iv: iv.last_touched_at)
        label = (
            f"Aprovar guia gerado: {fresh_gen.slug} ({fresh_gen.domain})"
            if cfg.lang == "pt-BR"
            else f"Approve generated guide: {fresh_gen.slug} ({fresh_gen.domain})"
        )
        choices.append((label, f"approve:{fresh_gen.slug}"))

    # Surface the freshest pending agent suggestion (issue #2 — next_recommendation).
    pending_suggestions = [r for r in state.next_recommendations if r.slug not in state.interviews]
    if pending_suggestions:
        suggestion = pending_suggestions[-1]
        label = (
            f"Começar guia sugerido: {suggestion.slug} ({suggestion.domain})"
            if cfg.lang == "pt-BR"
            else f"Start suggested guide: {suggestion.slug} ({suggestion.domain})"
        )
        choices.append((label, f"new_suggested:{suggestion.slug}:{suggestion.domain}"))

    choices.append((
        "Começar guia novo" if cfg.lang == "pt-BR" else "Start a new guide",
        "new",
    ))

    choices.append((
        "Ver estado de todos os guias" if cfg.lang == "pt-BR" else "Show all guides status",
        "status",
    ))

    # `review` (front-matter lint) is still available as `livedocs review`
    # subcommand, but removed from the menu — too technical to surface here.

    choices.append((t("exit"), "exit"))

    ui.blank()
    if not has_claude_code():
        ui.warn(t("err_no_claude"))
        ui.blank()

    picked = ui.ask_choice(t("what_now"), choices=choices)
    return picked


def _dispatch(repo_root: Path, picked: str) -> None:
    """Run the action implied by the menu pick. After it finishes, pause briefly
    so any final error/info message stays visible before the menu re-renders."""
    rc = 0
    if picked == "new":
        rc = run_new(repo_root) or 0
    elif picked == "status":
        rc = run_status(repo_root) or 0
    elif picked == "review":
        rc = run_review(repo_root) or 0
    elif picked.startswith("continue:"):
        slug = picked.split(":", 1)[1]
        rc = run_continue(repo_root, slug=slug) or 0
    elif picked.startswith("approve:"):
        slug = picked.split(":", 1)[1]
        rc = run_approve(repo_root, slug=slug) or 0
    elif picked.startswith("new_suggested:"):
        _, slug, domain = picked.split(":", 2)
        rc = run_new(repo_root, slug=slug, domain=domain) or 0

    # If the action returned non-zero, give the user a chance to read the error
    # before the menu re-renders and clears the scroll context.
    if rc != 0:
        ui.blank()
        ui.warn(
            f"[muted](action exited with code {rc}; press Enter to return to menu)[/muted]"
        )
        with contextlib.suppress(ui.NonInteractiveError):
            ui.ask_text(" ", default="")


def _offer_init(cwd: Path) -> int:
    """When no project is configured here, ask if the user wants to initialize.

    Replaces the previous behavior of just printing an error and exiting.
    Saves the user a step when they run `livedocs` in a fresh repo.
    """
    ui.splash()
    ui.warn(t("no_project_title"))
    try:
        confirmed = ui.ask_confirm(t("no_project_init_q"), default=True)
    except ui.NonInteractiveError:
        # Non-interactive mode: fall back to the old hint and exit cleanly.
        ui.hint(t("no_project_hint"))
        return 0

    if not confirmed:
        ui.hint(t("no_project_hint"))
        return 0

    return run_init(cwd)


def run_init_entry(cwd: Path) -> int:
    """Entry point used by `livedocs init`."""
    return run_init(cwd)
