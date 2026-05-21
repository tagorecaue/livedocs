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


def _make_md_files(repo: Path, kind_dir: str, cap_slug: str, article_slug: str) -> tuple[str, str]:
    base = repo / "docs" / kind_dir / cap_slug
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"{article_slug}.md"
    t = base / f"{article_slug}.tech.md"
    p.write_text(f"---\ntitle: T\nslug: {article_slug}\n---\n\nBody.", encoding="utf-8")
    t.write_text("---\ntitle: Tt\n---\n\nTech.", encoding="utf-8")
    return f"docs/{kind_dir}/{cap_slug}/{article_slug}.md", f"docs/{kind_dir}/{cap_slug}/{article_slug}.tech.md"


def test_bootstrap_phases_0_to_5_e2e(tmp_project, mock_agent, monkeypatch):
    repo_root, _cfg = tmp_project
    monkeypatch.setattr("sys.stdin", io.StringIO("SaaS de billing.\n"))
    monkeypatch.setattr("livedocs.ui.is_non_interactive", lambda: True)
    monkeypatch.setattr("livedocs.bootstrap.scanner.shutil.which", lambda _cmd: None)

    mock_agent.set_response("propor-taxonomia", _CANNED_TAXONOMY)

    # With the schema-v2 migration, each capability gets a default
    # `articles=[Article(slug="introducao", is_intro=True)]`. Pass1 iterates
    # articles, so we expect 2 capabilities * 1 article = 2 draft calls,
    # writing to docs/capacidades/<cap-slug>/<article-slug>.md.
    cob = _make_md_files(repo_root, "capacidades", "cobranca", "introducao")
    usr = _make_md_files(repo_root, "capacidades", "usuarios", "introducao")

    mock_agent.set_response("passada-1-draft", json_data={
        "files_written": list(cob), "pending_questions": [],
    }, cost_usd=0.05)
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
    assert state.last_completed_phase == 7
    assert state.status == "done"
    assert len(state.guides) == 2
    assert all(g.status == "stitched" for g in state.guides), (
        f"guide statuses: {[(g.slug, g.status) for g in state.guides]}"
    )
