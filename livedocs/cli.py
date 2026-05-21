"""LiveDocs CLI entry point — Typer app."""

from __future__ import annotations

from pathlib import Path

import typer

from livedocs import ui
from livedocs.commands.bootstrap import run_bootstrap
from livedocs.commands.init import run_init
from livedocs.commands.refine import run_refine
from livedocs.commands.root import run_root
from livedocs.i18n import detect_system_locale, set_lang, t
from livedocs.state import find_repo_root, load_config

app = typer.Typer(
    name="livedocs",
    help="Living documentation for SaaS — bootstrap your help center from code.",
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
def main_callback(
    ctx: typer.Context,
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        "-y",
        help="Refuse prompts and fail fast instead of looping (for scripts/CI).",
    ),
) -> None:
    """Default action when no subcommand is given: smart 'where we left off' menu."""
    # Pin the non-interactive flag for the whole process (issue #1).
    ui.set_non_interactive(non_interactive)

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


@app.command(
    "bootstrap",
    help="Bootstrap a help center for this SaaS from code (seven-phase pipeline).",
)
def cmd_bootstrap(
    resume: bool = typer.Option(
        False, "--resume", help="Resume from the last completed phase recorded in bootstrap.toml."
    ),
    re_tax: bool = typer.Option(
        False, "--re-tax", help="Re-run the taxonomy phase while keeping the scan cache."
    ),
    accept_taxonomy: bool = typer.Option(
        False,
        "--accept-taxonomy",
        help="Skip the interactive taxonomy review and approve as-is (useful for CI).",
    ),
    skip_refinement: bool = typer.Option(
        False,
        "--skip-refinement",
        help="Skip phase 6 (refinement interview). Pending questions stay open; run `livedocs refine` later.",
    ),
) -> None:
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)
    if repo_root is None:
        ui.error(t("err_no_project"))
        raise typer.Exit(code=1)
    _bootstrap_lang(repo_root)
    rc = run_bootstrap(
        repo_root,
        resume=resume,
        re_tax=re_tax,
        accept_taxonomy=accept_taxonomy,
        skip_refinement=skip_refinement,
    )
    raise typer.Exit(code=rc)


@app.command(
    "refine",
    help="Run only the refinement interview + global update (phases 6-7). Use after --skip-refinement.",
)
def cmd_refine() -> None:
    cwd = Path.cwd()
    repo_root = find_repo_root(cwd)
    if repo_root is None:
        ui.error(t("err_no_project"))
        raise typer.Exit(code=1)
    _bootstrap_lang(repo_root)
    rc = run_refine(repo_root)
    raise typer.Exit(code=rc)


@app.command("version", help="Show LiveDocs version.")
def cmd_version() -> None:
    from livedocs import __version__
    ui.console.print(f"livedocs [accent]{__version__}[/accent]")


if __name__ == "__main__":
    app()
