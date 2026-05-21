"""`livedocs` (no subcommand) — smart entry point.

After the v0.2 pivot to `livedocs bootstrap` (see .spec/bootstrap/), the
root menu is intentionally minimal: it points the user at the right next
command instead of trying to be a fully-featured menu.

Three states:
  1. No `.livedocs/config.toml` → offer to run `livedocs init`.
  2. Configured but no `.livedocs/bootstrap.toml` → suggest `livedocs bootstrap`.
  3. Bootstrap started → suggest `livedocs bootstrap --resume`.
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.bootstrap.state import bootstrap_path, load_bootstrap_state
from livedocs.commands.init import run_init
from livedocs.i18n import set_lang, t
from livedocs.state import load_config


def run_root(repo_root: Path | None) -> int:
    """Print a one-shot orientation; do not loop a menu in this scaffold commit."""
    cwd = Path.cwd()
    if repo_root is None or load_config(repo_root) is None:
        return _offer_init(cwd)

    cfg = load_config(repo_root)
    assert cfg is not None
    set_lang(cfg.lang)
    ui.splash()

    if not bootstrap_path(repo_root).exists():
        ui.section("Próximo passo")
        ui.info("Rode: livedocs bootstrap")
        return 0

    state = load_bootstrap_state(repo_root)
    if state and state.status != "done":
        ui.section("Bootstrap em andamento")
        ui.info(
            f"status={state.status} · última fase concluída: {state.last_completed_phase}"
        )
        ui.hint("Retome com: livedocs bootstrap --resume")
        return 0

    ui.success("Bootstrap concluído. (Plano B cobrirá publicação e manutenção.)")
    return 0


def _offer_init(cwd: Path) -> int:
    """When no project is configured here, ask if the user wants to initialize."""
    ui.splash()
    ui.warn(t("no_project_title"))
    try:
        confirmed = ui.ask_confirm(t("no_project_init_q"), default=True)
    except ui.NonInteractiveError:
        ui.hint(t("no_project_hint"))
        return 0

    if not confirmed:
        ui.hint(t("no_project_hint"))
        return 0

    return run_init(cwd)


def run_init_entry(cwd: Path) -> int:
    """Entry point used by `livedocs init`."""
    return run_init(cwd)
