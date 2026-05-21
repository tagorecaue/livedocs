"""E2E partial: run bootstrap phases 0-5 end-to-end with mocked agent."""

from __future__ import annotations

import io
from pathlib import Path

from livedocs.bootstrap.state import load_bootstrap_state
from livedocs.commands.bootstrap import run_bootstrap

_CANNED_TAXONOMY = {
    "capabilities": [
        {"slug": "cobranca", "title": "Cobrança", "summary": "Faturas",
         "code_anchors": ["src/billing/**"]},
        {"slug": "usuarios", "title": "Usuários", "summary": "Contas",
         "code_anchors": ["src/users/**"]},
    ],
    "journeys": [],
}


def _make_md_files(repo: Path, kind_dir: str, slug: str) -> tuple[str, str]:
    base = repo / "docs" / kind_dir
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"{slug}.md"
    t = base / f"{slug}.tech.md"
    p.write_text("---\ntitle: T\nslug: " + slug + "\n---\n\nBody.", encoding="utf-8")
    t.write_text("---\ntitle: Tt\n---\n\nTech.", encoding="utf-8")
    return f"docs/{kind_dir}/{slug}.md", f"docs/{kind_dir}/{slug}.tech.md"


def test_bootstrap_phases_0_to_5_e2e(tmp_project, mock_agent, monkeypatch):
    repo_root, _cfg = tmp_project
    monkeypatch.setattr("sys.stdin", io.StringIO("SaaS de billing.\n"))
    monkeypatch.setattr("livedocs.ui.is_non_interactive", lambda: True)

    mock_agent.set_response("propor-taxonomia", _CANNED_TAXONOMY)

    # Pre-write the files for the agent to claim.
    cob = _make_md_files(repo_root, "capacidades", "cobranca")
    usr = _make_md_files(repo_root, "capacidades", "usuarios")

    mock_agent.set_response("passada-1-draft", json_data={
        "files_written": list(cob), "pending_questions": [],
    }, cost_usd=0.05)
    # The second pass1 call (for usuarios) gets the same matcher; queue 2nd
    mock_agent.set_response("passada-1-draft", json_data={
        "files_written": list(usr), "pending_questions": [],
    }, cost_usd=0.05)

    mock_agent.set_response("passada-2-stitch", json_data={
        "files_modified": list(cob),
        "contradictions": [],
        "new_pending_questions": [],
    }, cost_usd=0.01)
    mock_agent.set_response("passada-2-stitch", json_data={
        "files_modified": list(usr),
        "contradictions": [],
        "new_pending_questions": [],
    }, cost_usd=0.01)

    rc = run_bootstrap(repo_root, accept_taxonomy=True)
    assert rc == 0

    state = load_bootstrap_state(repo_root)
    assert state is not None
    # With no pending questions, phase 6 (dedup) is a no-op and phase 7
    # (global update) has no affected guides → bootstrap finishes clean.
    assert state.last_completed_phase == 7
    assert state.status == "done"
    assert all(g.status == "stitched" for g in state.guides)
    assert len(state.guides) == 2
