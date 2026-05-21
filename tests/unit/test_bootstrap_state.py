"""Tests for the BootstrapState persistence layer."""

from __future__ import annotations

from pathlib import Path

import pytest
import tomli_w

from livedocs.bootstrap.state import (
    CURRENT_SCHEMA_VERSION,
    BootstrapState,
    GuidanceText,
    bootstrap_path,
    load_bootstrap_state,
    save_bootstrap_state,
)


def test_default_state_is_phase_zero() -> None:
    s = BootstrapState()
    assert s.schema_version == CURRENT_SCHEMA_VERSION
    assert s.status == "scanning"
    assert s.last_completed_phase == 0
    assert s.guides == []
    assert s.pending_questions == []
    assert s.scan.commit_sha is None


def test_load_returns_none_when_missing(tmp_repo: Path) -> None:
    assert load_bootstrap_state(tmp_repo) is None


def test_save_then_load_roundtrip(tmp_repo: Path) -> None:
    s = BootstrapState(
        status="drafting",
        last_completed_phase=3,
        guidance=GuidanceText(text="hello", captured_at="2026-01-01T00:00:00"),
    )
    save_bootstrap_state(tmp_repo, s)
    p = bootstrap_path(tmp_repo)
    assert p.exists()

    loaded = load_bootstrap_state(tmp_repo)
    assert loaded is not None
    assert loaded.status == "drafting"
    assert loaded.last_completed_phase == 3
    assert loaded.guidance.text == "hello"
    # created_at/updated_at are auto-stamped on save
    assert loaded.created_at != ""
    assert loaded.updated_at != ""


def test_save_creates_bak_of_prior_file(tmp_repo: Path) -> None:
    s = BootstrapState()
    save_bootstrap_state(tmp_repo, s)
    s.status = "deriving"
    save_bootstrap_state(tmp_repo, s)
    bak = bootstrap_path(tmp_repo).with_suffix(".toml.bak")
    assert bak.exists(), "expected .bak backup after second save (issue #9)"


def test_future_schema_version_raises_clearly(tmp_repo: Path) -> None:
    p = bootstrap_path(tmp_repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        tomli_w.dump(
            {
                "schema_version": CURRENT_SCHEMA_VERSION + 1,
                "status": "scanning",
                "last_completed_phase": 0,
            },
            f,
        )
    with pytest.raises(ValueError, match="schema_version"):
        load_bootstrap_state(tmp_repo)
