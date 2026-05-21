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


def test_migrate_v1_to_v2_adds_intro_article(tmp_repo: Path) -> None:
    """Schema v1 sem articles → carregar gera article 'introducao' por capability."""
    p = bootstrap_path(tmp_repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        tomli_w.dump(
            {
                "schema_version": 1,
                "status": "drafting",
                "last_completed_phase": 3,
                "taxonomy": {
                    "capabilities": [
                        {
                            "slug": "cobranca",
                            "title": "Cobrança",
                            "summary": "Faturas e pagamentos",
                            "code_anchors": ["src/billing/**"],
                        },
                        {
                            "slug": "usuarios",
                            "title": "Usuários",
                            "summary": "",
                            "code_anchors": [],
                        },
                    ],
                    "journeys": [],
                },
            },
            f,
        )
    loaded = load_bootstrap_state(tmp_repo)
    assert loaded is not None
    assert loaded.schema_version == 2
    assert loaded.taxonomy is not None
    cap0 = loaded.taxonomy.capabilities[0]
    assert len(cap0.articles) == 1
    art = cap0.articles[0]
    assert art.slug == "introducao"
    assert art.is_intro is True
    assert art.title == "Cobrança"
    assert art.summary == "Faturas e pagamentos"
    assert art.code_anchors == ["src/billing/**"]
    # Capability sem anchors/summary também ganha intro article.
    cap1 = loaded.taxonomy.capabilities[1]
    assert len(cap1.articles) == 1
    assert cap1.articles[0].slug == "introducao"
    assert cap1.articles[0].is_intro is True
