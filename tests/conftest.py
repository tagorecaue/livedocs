"""Shared fixtures across all livedocs tests.

# Key fixtures

  tmp_repo
    Minimal git-initialized repo with a single source file. Returns Path.

  tmp_project
    Like tmp_repo plus a complete ProjectConfig persisted to .livedocs/config.toml,
    a fresh state.toml, and .livedocs/style.md. Returns (Path, ProjectConfig).

  mock_agent
    Stub for livedocs.agent.ClaudeAgent. Tests configure canned responses
    per-prompt via `mock_agent.set_response(matcher, AgentResult-like)`.
    See tests/_helpers.py for AgentResult shaping.

# Why fixtures and not testcase classes

Mixing pytest fixtures with class-based tests in a Pydantic-heavy codebase tends
to create import-order headaches. Function-based tests + fixtures keep things
linear and easy to grep.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from livedocs.models import ProjectConfig
from livedocs.state import (
    ensure_gitignore_for_state,
    save_config,
)

# ---------------------------------------------------------------------------
# Repo / project fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A minimal git-initialized repo with one Python source file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "cart.py").write_text(
        '"""Tiny cart module for tests."""\n\n'
        'def can_checkout(cart):\n'
        '    """Return True iff cart is open with items."""\n'
        '    return cart.status == "open" and len(cart.items) > 0\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
    )
    return repo


@pytest.fixture
def tmp_project(tmp_repo: Path) -> tuple[Path, ProjectConfig]:
    """tmp_repo + persisted config + .gitignore + style.md."""
    cfg = ProjectConfig(
        project_slug="test-project",
        lang="en",
        provider="claude-code",
        docs_dir="docs",
        style="narrative",
    )
    save_config(tmp_repo, cfg)
    ensure_gitignore_for_state(tmp_repo)
    # Style file
    from livedocs.skill.styles import copy_style_to_project
    copy_style_to_project("narrative", tmp_repo / ".livedocs" / "style.md")
    return tmp_repo, cfg


# ---------------------------------------------------------------------------
# Agent mock
# ---------------------------------------------------------------------------

class _AgentResultStub:
    """A stand-in for livedocs.agent.AgentResult.

    We don't import AgentResult directly here to keep tests decoupled from
    its constructor signature; only fields actually read by callers matter.
    """
    def __init__(
        self,
        *,
        text: str = "",
        json_data: Any = None,
        is_error: bool = False,
        error_message: str | None = None,
        cost_usd: float = 0.0,
        duration_ms: int = 0,
    ):
        self.text = text
        self.json_data = json_data
        self.is_error = is_error
        self.error_message = error_message
        self.cost_usd = cost_usd
        self.duration_ms = duration_ms


class MockAgent:
    """Stand-in for ClaudeAgent injected into modules under test.

    Usage:
        mock_agent.set_response("PARSE_INTENT", {"slug": "x", ...})
        mock_agent.set_response("BUILD_SKELETON", {"facts": [...]})
        # Multiple responses to the same matcher get returned in order.

    Match is substring-based against the prompt text.
    Falls back to a default error result if no matcher hits — test should fail
    loudly when the system tries to call an unexpected prompt.
    """

    def __init__(self, repo_root: Path | None = None, lang: str = "en", **kwargs: Any):
        self.repo_root = repo_root
        self.lang = lang
        self._matchers: list[tuple[Callable[[str], bool], list[_AgentResultStub]]] = []
        self.calls: list[dict[str, Any]] = []

    # ---- Test API ----

    def set_response(
        self,
        matcher: str | Callable[[str], bool],
        json_data: Any = None,
        *,
        text: str = "",
        is_error: bool = False,
        error_message: str | None = None,
        cost_usd: float = 0.001,
        duration_ms: int = 50,
    ) -> None:
        """Queue a canned response for any prompt matching `matcher`.

        - matcher str: substring check (case-insensitive).
        - matcher callable: arbitrary predicate over the prompt text.

        If queued multiple times to the same matcher, they're consumed FIFO.
        """
        if isinstance(matcher, str):
            needle = matcher.lower()

            def pred(prompt: str, _n: str = needle) -> bool:
                return _n in prompt.lower()
        else:
            pred = matcher
        result = _AgentResultStub(
            text=text,
            json_data=json_data,
            is_error=is_error,
            error_message=error_message,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        )
        # Try to find an existing matcher we can extend; otherwise add new.
        for existing_pred, results in self._matchers:
            if existing_pred is pred:
                results.append(result)
                return
        self._matchers.append((pred, [result]))

    # ---- Production API surface (matches ClaudeAgent.call) ----

    def call(
        self,
        prompt: str,
        *,
        expect_json: bool = False,
        timeout: int = 60,
        extra_system: str | None = None,
        json_schema: dict | None = None,
        on_progress=None,
        allowed_tools: list[str] | None = None,
    ) -> _AgentResultStub:
        self.calls.append(
            {
                "prompt": prompt,
                "expect_json": expect_json,
                "timeout": timeout,
                "extra_system": extra_system,
                "on_progress": on_progress,
                "allowed_tools": allowed_tools,
            }
        )
        for pred, results in self._matchers:
            if pred(prompt) and results:
                return results.pop(0)
        return _AgentResultStub(
            is_error=True,
            error_message=f"MockAgent: no canned response for prompt (first 80 chars): {prompt[:80]}",
        )


@pytest.fixture
def mock_agent(monkeypatch: pytest.MonkeyPatch) -> MockAgent:
    """Patches `livedocs.agent.ClaudeAgent` with a MockAgent for the test.

    Returns the singleton instance the production code will receive when
    it constructs `ClaudeAgent(...)`. Tests configure canned responses
    BEFORE invoking the system-under-test.

    Note on patching strategy: many modules do `from livedocs.agent import ClaudeAgent`
    at import-time, which means we have to monkey-patch *each* module's reference,
    not just livedocs.agent.ClaudeAgent. We patch all known call sites.
    """
    instance = MockAgent()

    def _ctor(*args: Any, **kwargs: Any) -> MockAgent:
        # Re-use the same instance so tests can inspect a single .calls list.
        instance.repo_root = kwargs.get("repo_root") or (args[0] if args else None)
        instance.lang = kwargs.get("lang", "en")
        return instance

    # Patch every module that imported ClaudeAgent at top-level.
    modules = [
        "livedocs.agent",
        "livedocs.bootstrap.taxonomy",
        "livedocs.bootstrap.pass1_drafts",
        "livedocs.bootstrap.pass2_stitch",
        "livedocs.bootstrap.refinement",
        "livedocs.bootstrap.global_update",
    ]
    for modname in modules:
        try:
            __import__(modname)
            import sys
            mod = sys.modules[modname]
            if hasattr(mod, "ClaudeAgent"):
                monkeypatch.setattr(f"{modname}.ClaudeAgent", _ctor)
        except (ImportError, AttributeError):
            pass

    return instance


# ---------------------------------------------------------------------------
# UI silence — keep test output readable
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _silence_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out the Rich console so tests don't pollute pytest output.

    Per-test, this replaces ui.console with a non-printing dummy. Tests that
    need to assert on UI output should re-monkeypatch with their own capture.

    The console exposes a bunch of methods (print, rule, status, etc) — we
    return a no-op for any attribute access so production code never crashes
    against a missing method on the stub.
    """
    from livedocs import ui

    class _NullConsole:
        def __getattr__(self, name: str):
            # Any attribute lookup returns a no-op callable.
            return lambda *a, **kw: None

    monkeypatch.setattr(ui, "console", _NullConsole())

    # `ui.spinner` returns a context manager — stub it out cheaply.
    from contextlib import contextmanager

    @contextmanager
    def _null_spinner(*args: Any, **kwargs: Any):
        yield

    @contextmanager
    def _null_progress_spinner(*args: Any, **kwargs: Any):
        # progress_spinner yields a callable (the update fn). Tests don't care
        # what we pass to it — just need something that's safe to invoke.
        def update(_label: str) -> None:
            return

        yield update

    monkeypatch.setattr(ui, "spinner", _null_spinner)
    monkeypatch.setattr(ui, "progress_spinner", _null_progress_spinner)
