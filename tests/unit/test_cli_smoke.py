"""Smoke tests for the typer CLI surface after the bootstrap scaffold."""

from __future__ import annotations

from typer.testing import CliRunner

from livedocs.cli import app

runner = CliRunner()


def test_help_lists_bootstrap() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "bootstrap" in result.stdout.lower()


def test_version_runs() -> None:
    # The autouse _silence_ui fixture stubs ui.console, so we only assert
    # the command exits cleanly (output goes through ui.console.print).
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0


def test_bootstrap_help() -> None:
    result = runner.invoke(app, ["bootstrap", "--help"])
    assert result.exit_code == 0
    assert "bootstrap" in result.stdout.lower()
