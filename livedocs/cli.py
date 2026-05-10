"""LiveDocs CLI entry point — Typer app."""

from __future__ import annotations

from pathlib import Path

import typer

from livedocs import ui
from livedocs.commands.approve import run_approve
from livedocs.commands.cont import run_continue
from livedocs.commands.init import run_init
from livedocs.commands.new import run_new
from livedocs.commands.review import run_review
from livedocs.commands.root import run_root
from livedocs.commands.status import run_status
from livedocs.i18n import detect_system_locale, set_lang, t
from livedocs.state import find_repo_root, load_config

app = typer.Typer(
    name="livedocs",
    help="Living documentation for SaaS — interview-driven, code-aware.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


def _bootstrap_lang(repo_root: Path | None) -> None:
    """Set the active i18n lang from project config if present, else from system locale."""
    if repo_root:
        cfg = load_config(repo_root)
        if cfg:
            set_lang(cfg.lang)
            return
    set_lang(detect_system_locale())


@app.callback()
def main_callback(ctx: typer.Context) -> None:
    """Default action when no subcommand is given: smart 'where we left off' menu."""
    if ctx.invoked_subcommand is not None:
        return

    cwd = Path.cwd()
    repo_root = find_repo_root(cwd) or cwd
    _bootstrap_lang(repo_root if (repo_root / ".livedocs" / "config.toml").exists() else None)
    rc = run_root(repo_root if (repo_root / ".livedocs" / "config.toml").exists() else None)
    raise typer.Exit(code=rc)


@app.command("init", help="Configure LiveDocs in this repository.")
def cmd_init() -> None:
    cwd = Path.cwd()
    _bootstrap_lang(None)  # use system locale; init confirms
    rc = run_init(cwd)
    raise typer.Exit(code=rc)


@app.command("new", help="Start a new guide interview.")
def cmd_new(
    slug: str = typer.Argument(None, help="Slug for the new guide (kebab-case)."),
    domain: str = typer.Option(None, "--domain", "-d", help="Domain folder for this guide."),
    title: str = typer.Option(None, "--title", "-t", help="Working title."),
) -> None:
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)
    if repo_root is None:
        ui.error(t("err_no_project"))
        raise typer.Exit(code=1)
    _bootstrap_lang(repo_root)
    rc = run_new(repo_root, slug=slug, domain=domain, title=title)
    raise typer.Exit(code=rc)


@app.command("continue", help="Resume an in-progress interview.")
def cmd_continue(
    slug: str = typer.Argument(None, help="Slug to resume (defaults to last touched)."),
) -> None:
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)
    if repo_root is None:
        ui.error(t("err_no_project"))
        raise typer.Exit(code=1)
    _bootstrap_lang(repo_root)
    rc = run_continue(repo_root, slug=slug)
    raise typer.Exit(code=rc)


@app.command("status", help="Show all guides and their status.")
def cmd_status() -> None:
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)
    if repo_root is None:
        ui.error(t("err_no_project"))
        raise typer.Exit(code=1)
    _bootstrap_lang(repo_root)
    rc = run_status(repo_root)
    raise typer.Exit(code=rc)


@app.command("review", help="Run quick coherence checks on existing guides.")
def cmd_review() -> None:
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)
    if repo_root is None:
        ui.error(t("err_no_project"))
        raise typer.Exit(code=1)
    _bootstrap_lang(repo_root)
    rc = run_review(repo_root)
    raise typer.Exit(code=rc)


@app.command("approve", help="Mark a generated guide as reviewed by a human.")
def cmd_approve(
    slug: str = typer.Argument(None, help="Slug to approve (defaults to single pending or interactive pick)."),
) -> None:
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)
    if repo_root is None:
        ui.error(t("err_no_project"))
        raise typer.Exit(code=1)
    _bootstrap_lang(repo_root)
    rc = run_approve(repo_root, slug=slug)
    raise typer.Exit(code=rc)


@app.command("version", help="Show LiveDocs version.")
def cmd_version() -> None:
    from livedocs import __version__
    ui.console.print(f"livedocs [accent]{__version__}[/accent]")


if __name__ == "__main__":
    app()
