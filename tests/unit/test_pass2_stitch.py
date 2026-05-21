"""Tests for pass2_stitch (Fase 5 — costura cross-guides)."""

from __future__ import annotations

from pathlib import Path

from livedocs.bootstrap.pass2_stitch import run_pass2
from livedocs.bootstrap.state import (
    BootstrapState,
    Capability,
    GuideRecord,
    Taxonomy,
)


def _write_md(path: Path, *, title: str, summary: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = f"---\ntitle: {title}\nsummary: {summary}\nstatus: drafted\n---\n\n"
    path.write_text(fm + body, encoding="utf-8")


def _setup(repo: Path) -> BootstrapState:
    state = BootstrapState()
    state.taxonomy = Taxonomy(
        capabilities=[
            Capability(slug="cobranca", title="Cobrança", summary="Faturas"),
            Capability(slug="users", title="Usuários", summary="Contas"),
        ],
    )
    state.guides = [
        GuideRecord(slug="cobranca", kind="capability", status="drafted"),
        GuideRecord(slug="users", kind="capability", status="drafted"),
    ]
    base = repo / "docs" / "capacidades"
    _write_md(base / "cobranca.md", title="Cobrança", summary="Faturas",
              body="Veja [TODO:link=users] para detalhes.")
    _write_md(base / "cobranca.tech.md", title="Cobrança tech", summary="",
              body="Detalhes técnicos.")
    _write_md(base / "users.md", title="Usuários", summary="Contas",
              body="Usuários do sistema.")
    _write_md(base / "users.tech.md", title="Usuários tech", summary="",
              body="Tech.")
    return state


def test_pass2_stitches_two_drafted_guides_with_contradictions(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = _setup(repo)

    mock_agent.set_response(
        "cobranca",
        json_data={
            "files_modified": ["docs/capacidades/cobranca.md",
                               "docs/capacidades/cobranca.tech.md"],
            "links_added": 1,
            "todos_resolved": 1,
            "todos_unresolved": [],
            "contradictions": [
                {"this_guide_says": "fatura mensal",
                 "other_guide": "users",
                 "other_says": "cobrança anual"},
            ],
            "new_pending_questions": [],
        },
        cost_usd=0.02,
    )
    mock_agent.set_response(
        "users",
        json_data={
            "files_modified": ["docs/capacidades/users.md",
                               "docs/capacidades/users.tech.md"],
            "links_added": 0,
            "todos_resolved": 0,
            "todos_unresolved": [],
            "contradictions": [],
            "new_pending_questions": [
                {"question": "É admin único?", "provisional_answer": "sim",
                 "confidence": "low"},
            ],
        },
        cost_usd=0.01,
    )

    run_pass2(repo, cfg, state)

    statuses = {g.slug: g.status for g in state.guides}
    assert statuses == {"cobranca": "stitched", "users": "stitched"}

    # Contradiction → 1 pending; new_pending_questions → 1 more
    questions = state.pending_questions
    assert len(questions) == 2
    assert any("Contradição" in q.question for q in questions)
    assert any("admin único" in q.question for q in questions)


def test_pass2_skips_pending_guides(tmp_project, mock_agent):
    repo, cfg = tmp_project
    state = _setup(repo)
    # users is still pending (passada 1 failed) — should not be stitched.
    state.guides[1].status = "pending"

    mock_agent.set_response(
        "cobranca",
        json_data={
            "files_modified": ["docs/capacidades/cobranca.md",
                               "docs/capacidades/cobranca.tech.md"],
            "contradictions": [],
            "new_pending_questions": [],
        },
    )

    run_pass2(repo, cfg, state)
    statuses = {g.slug: g.status for g in state.guides}
    assert statuses["cobranca"] == "stitched"
    assert statuses["users"] == "pending"
    # Only one agent call (for cobranca).
    assert len(mock_agent.calls) == 1
