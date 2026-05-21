"""Tests for pass1_drafts (Fase 4 — rascunhos isolados).

Após schema v2 a iteração é por *article* dentro de capability. Slug do
GuideRecord é composto: `<cap-slug>/<article-slug>`. Capabilities com
um único article (migração default) geram um único draft equivalente
ao comportamento velho.
"""

from __future__ import annotations

from pathlib import Path

from livedocs.bootstrap.pass1_drafts import run_pass1
from livedocs.bootstrap.state import (
    Article,
    BootstrapState,
    Capability,
    Journey,
    Taxonomy,
)


def _seed_taxonomy(state: BootstrapState) -> None:
    state.taxonomy = Taxonomy(
        capabilities=[
            Capability(
                slug="cobranca", title="Cobrança", summary="Faturas",
                code_anchors=["src/billing/**"],
                articles=[
                    Article(slug="introducao", title="Cobrança", summary="Faturas",
                            is_intro=True, code_anchors=["src/billing/**"]),
                ],
            ),
        ],
        journeys=[
            Journey(slug="onboarding", title="Onboarding",
                    summary="Cadastro", capability_refs=["cobranca"]),
        ],
    )


def _make_md_files(repo: Path, rel_dir: str, slug: str) -> tuple[str, str]:
    """Create the two .md files the agent is supposed to have written."""
    base = repo / "docs" / rel_dir
    base.mkdir(parents=True, exist_ok=True)
    product = base / f"{slug}.md"
    tech = base / f"{slug}.tech.md"
    product.write_text(
        "---\ntitle: T\nslug: " + slug + "\nstatus: drafted\n---\n\nLorem.",
        encoding="utf-8",
    )
    tech.write_text("---\ntitle: T tech\n---\n\nTech.", encoding="utf-8")
    return (f"docs/{rel_dir}/{slug}.md", f"docs/{rel_dir}/{slug}.tech.md")


def test_pass1_drafts_two_files_and_pending_questions(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = BootstrapState()
    _seed_taxonomy(state)

    # Article "introducao" of capability "cobranca" lives under capacidades/cobranca/.
    cob_prod, cob_tech = _make_md_files(repo, "capacidades/cobranca", "introducao")
    onb_prod, onb_tech = _make_md_files(repo, "jornadas", "onboarding")

    mock_agent.set_response(
        "cobranca/introducao",
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
    assert statuses == {"cobranca/introducao": "drafted", "onboarding": "drafted"}
    assert len(state.pending_questions) == 1
    assert state.pending_questions[0].guide_slug == "cobranca/introducao"
    assert state.pending_questions[0].id == "Q1"
    assert state.total_cost_usd >= 0.08 - 1e-9


def test_pass1_missing_files_marks_pending(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = BootstrapState()
    _seed_taxonomy(state)

    # Agent returns files that DON'T exist on disk.
    mock_agent.set_response(
        "cobranca/introducao",
        json_data={
            "files_written": ["docs/capacidades/cobranca/introducao.md",
                              "docs/capacidades/cobranca/introducao.tech.md"],
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
    assert statuses["cobranca/introducao"] == "pending"
    assert statuses["onboarding"] == "drafted"


def test_pass1_resume_skips_drafted(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = BootstrapState()
    _seed_taxonomy(state)

    cob_prod, cob_tech = _make_md_files(repo, "capacidades/cobranca", "introducao")
    onb_prod, onb_tech = _make_md_files(repo, "jornadas", "onboarding")

    mock_agent.set_response("cobranca/introducao", json_data={
        "files_written": [cob_prod, cob_tech], "pending_questions": [],
    })
    mock_agent.set_response("onboarding", json_data={
        "files_written": [onb_prod, onb_tech], "pending_questions": [],
    })

    run_pass1(repo, cfg, state)
    n_calls_first = len(mock_agent.calls)
    assert n_calls_first == 2


def test_pass1_screenshot_todos_captured(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = BootstrapState()
    _seed_taxonomy(state)

    cob_prod, cob_tech = _make_md_files(repo, "capacidades/cobranca", "introducao")
    onb_prod, onb_tech = _make_md_files(repo, "jornadas", "onboarding")

    mock_agent.set_response("cobranca/introducao", json_data={
        "files_written": [cob_prod, cob_tech],
        "pending_questions": [],
        "screenshot_todos": [
            {"route": "/billing", "description": "Lista de faturas"},
            {"route": "/billing/new", "description": "Wizard de nova fatura"},
        ],
    })
    mock_agent.set_response("onboarding", json_data={
        "files_written": [onb_prod, onb_tech],
        "pending_questions": [],
        "screenshot_todos": [{"route": "", "description": "ignorada"}],  # vazio → ignorado
    })

    run_pass1(repo, cfg, state)

    assert len(state.screenshot_todos) == 2
    todo = state.screenshot_todos[0]
    assert todo.guide_slug == "cobranca/introducao"
    assert todo.guide_path == cob_prod
    assert todo.route == "/billing"
    assert todo.status == "open"
    assert state.screenshot_todos[1].route == "/billing/new"

    # Second run: agent should NOT be called for the already-drafted ones.
    run_pass1(repo, cfg, state)
    assert len(mock_agent.calls) == 2  # no new calls


def test_pass1_multi_article_capability(tmp_project, mock_agent):
    """Capability com 2 articles → 2 chamadas, 4 arquivos."""
    repo, cfg = tmp_project
    state = BootstrapState()
    state.taxonomy = Taxonomy(
        capabilities=[
            Capability(
                slug="cobranca", title="Cobrança", summary="Faturas",
                code_anchors=["src/billing/**"],
                articles=[
                    Article(slug="introducao", title="Visão geral",
                            is_intro=True, code_anchors=["src/billing/**"]),
                    Article(slug="emissao-boletos", title="Emissão de boletos",
                            is_intro=False, code_anchors=["src/billing/boletos/**"]),
                ],
            ),
        ],
    )

    p1, t1 = _make_md_files(repo, "capacidades/cobranca", "introducao")
    p2, t2 = _make_md_files(repo, "capacidades/cobranca", "emissao-boletos")

    mock_agent.set_response("cobranca/introducao", json_data={
        "files_written": [p1, t1], "pending_questions": [],
    })
    mock_agent.set_response("cobranca/emissao-boletos", json_data={
        "files_written": [p2, t2], "pending_questions": [],
    })

    run_pass1(repo, cfg, state)

    # Both should be drafted.
    statuses = {g.slug: g.status for g in state.guides}
    assert statuses == {
        "cobranca/introducao": "drafted",
        "cobranca/emissao-boletos": "drafted",
    }
    # Two agent calls, four files on disk.
    assert len(mock_agent.calls) == 2
    for rel in (p1, t1, p2, t2):
        assert (repo / rel).exists()
