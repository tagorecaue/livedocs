"""Tests for pass1_drafts (Fase 4 — rascunhos isolados)."""

from __future__ import annotations

from pathlib import Path

from livedocs.bootstrap.pass1_drafts import run_pass1
from livedocs.bootstrap.state import (
    BootstrapState,
    Capability,
    Journey,
    Taxonomy,
)


def _seed_taxonomy(state: BootstrapState) -> None:
    state.taxonomy = Taxonomy(
        capabilities=[
            Capability(slug="cobranca", title="Cobrança", summary="Faturas",
                       code_anchors=["src/billing/**"]),
        ],
        journeys=[
            Journey(slug="onboarding", title="Onboarding",
                    summary="Cadastro", capability_refs=["cobranca"]),
        ],
    )


def _make_md_files(repo: Path, kind_dir: str, slug: str) -> tuple[str, str]:
    """Create the two .md files the agent is supposed to have written."""
    base = repo / "docs" / kind_dir
    base.mkdir(parents=True, exist_ok=True)
    product = base / f"{slug}.md"
    tech = base / f"{slug}.tech.md"
    product.write_text(
        "---\ntitle: T\nslug: " + slug + "\nstatus: drafted\n---\n\nLorem.",
        encoding="utf-8",
    )
    tech.write_text("---\ntitle: T tech\n---\n\nTech.", encoding="utf-8")
    return (f"docs/{kind_dir}/{slug}.md", f"docs/{kind_dir}/{slug}.tech.md")


def test_pass1_drafts_two_files_and_pending_questions(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = BootstrapState()
    _seed_taxonomy(state)

    # Pre-create the files the agent will claim to have written.
    cob_prod, cob_tech = _make_md_files(repo, "capacidades", "cobranca")
    onb_prod, onb_tech = _make_md_files(repo, "jornadas", "onboarding")

    mock_agent.set_response(
        "cobranca",
        json_data={
            "files_written": [cob_prod, cob_tech],
            "pending_questions": [
                {"question": "Como cobrar?", "provisional_answer": "Boleto",
                 "confidence": "low"},
            ],
        },
        cost_usd=0.05,
    )
    mock_agent.set_response(
        "onboarding",
        json_data={
            "files_written": [onb_prod, onb_tech],
            "pending_questions": [],
        },
        cost_usd=0.03,
    )

    run_pass1(repo, cfg, state)

    statuses = {g.slug: g.status for g in state.guides}
    assert statuses == {"cobranca": "drafted", "onboarding": "drafted"}
    assert len(state.pending_questions) == 1
    assert state.pending_questions[0].guide_slug == "cobranca"
    assert state.pending_questions[0].id == "Q1"
    assert state.total_cost_usd >= 0.08 - 1e-9


def test_pass1_missing_files_marks_pending(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = BootstrapState()
    _seed_taxonomy(state)

    # Agent returns files that DON'T exist on disk.
    mock_agent.set_response(
        "cobranca",
        json_data={
            "files_written": ["docs/capacidades/cobranca.md",
                              "docs/capacidades/cobranca.tech.md"],
            "pending_questions": [],
        },
    )
    onb_prod, onb_tech = _make_md_files(repo, "jornadas", "onboarding")
    mock_agent.set_response(
        "onboarding",
        json_data={"files_written": [onb_prod, onb_tech], "pending_questions": []},
    )

    run_pass1(repo, cfg, state)
    statuses = {g.slug: g.status for g in state.guides}
    assert statuses["cobranca"] == "pending"
    assert statuses["onboarding"] == "drafted"


def test_pass1_resume_skips_drafted(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = BootstrapState()
    _seed_taxonomy(state)

    cob_prod, cob_tech = _make_md_files(repo, "capacidades", "cobranca")
    onb_prod, onb_tech = _make_md_files(repo, "jornadas", "onboarding")

    mock_agent.set_response("cobranca", json_data={
        "files_written": [cob_prod, cob_tech], "pending_questions": [],
    })
    mock_agent.set_response("onboarding", json_data={
        "files_written": [onb_prod, onb_tech], "pending_questions": [],
    })

    run_pass1(repo, cfg, state)
    n_calls_first = len(mock_agent.calls)
    assert n_calls_first == 2

    # Second run: agent should NOT be called for the already-drafted ones.
    run_pass1(repo, cfg, state)
    assert len(mock_agent.calls) == n_calls_first  # no new calls
