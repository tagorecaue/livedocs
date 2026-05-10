"""`livedocs` (no subcommand) — Where we left off + smart menu.

This is the most important UX: friendly, knows the state, suggests the right
action. Replaces the cognitive load of remembering subcommands.
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.commands.cont import run_continue
from livedocs.commands.init import run_init
from livedocs.commands.new import run_new
from livedocs.commands.review import run_review
from livedocs.commands.status import run_status
from livedocs.detect import has_claude_code
from livedocs.i18n import set_lang, t
from livedocs.state import load_config, load_state


def run_root(repo_root: Path | None) -> int:
    """No subcommand path. Detects state and offers next step."""
    if repo_root is None:
        ui.splash()
        ui.warn(t("no_project_title"))
        ui.hint(t("no_project_hint"))
        return 0

    cfg = load_config(repo_root)
    if cfg is None:
        ui.splash()
        ui.warn(t("no_project_title"))
        ui.hint(t("no_project_hint"))
        return 0

    set_lang(cfg.lang)
    ui.splash()

    state = load_state(repo_root)

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

    choices.append((
        "Começar guia novo" if cfg.lang == "pt-BR" else "Start a new guide",
        "new",
    ))

    choices.append((
        "Ver estado de todos os guias" if cfg.lang == "pt-BR" else "Show all guides status",
        "status",
    ))

    choices.append((
        "Revisar guias (front-matter, links, …)" if cfg.lang == "pt-BR" else "Review guides (front-matter, links, …)",
        "review",
    ))

    choices.append((t("exit"), "exit"))

    ui.blank()
    if not has_claude_code():
        ui.warn(t("err_no_claude"))
        ui.blank()

    picked = ui.ask_choice(t("what_now"), choices=choices)
    if picked is None or picked == "exit":
        return 0

    if picked == "new":
        return run_new(repo_root)
    if picked == "status":
        return run_status(repo_root)
    if picked == "review":
        return run_review(repo_root)
    if picked.startswith("continue:"):
        slug = picked.split(":", 1)[1]
        return run_continue(repo_root, slug=slug)

    return 0


def run_init_entry(cwd: Path) -> int:
    """Entry point used by `livedocs init`."""
    return run_init(cwd)
