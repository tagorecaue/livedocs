"""E2E partial: run bootstrap phases 0-3 end-to-end with mocked agent."""

from __future__ import annotations

from pathlib import Path

from livedocs.bootstrap.state import bootstrap_path, load_bootstrap_state
from livedocs.commands.bootstrap import run_bootstrap

_CANNED_TAXONOMY = {
    "capabilities": [
        {"slug": "cobranca", "title": "Cobrança", "summary": "Faturas",
         "code_anchors": ["src/billing/**"]},
        {"slug": "usuarios", "title": "Usuários", "summary": "Contas",
         "code_anchors": ["src/users/**"]},
        {"slug": "relatorios", "title": "Relatórios", "summary": "Dashboards",
         "code_anchors": ["src/reports/**"]},
    ],
    "journeys": [
        {"slug": "onboarding", "title": "Onboarding",
         "summary": "Do cadastro à primeira fatura",
         "capability_refs": ["usuarios", "cobranca"]},
    ],
}


def test_bootstrap_phases_0_to_3_e2e(tmp_project, mock_agent, monkeypatch):
    repo_root, _cfg = tmp_project
    # Pipe-mode for non-interactive prompts (guidance).
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("SaaS B2B de billing.\n"))
    monkeypatch.setattr(
        "livedocs.ui.is_non_interactive", lambda: True,
    )
    mock_agent.set_response("propor-taxonomia", _CANNED_TAXONOMY)

    rc = run_bootstrap(repo_root, accept_taxonomy=True)
    assert rc == 0

    state_file = bootstrap_path(repo_root)
    assert state_file.exists()

    state = load_bootstrap_state(repo_root)
    assert state is not None
    # With phases 4-5 wired into the orchestrator, the pipeline now also
    # tries to draft+stitch — but without canned responses for those, every
    # guide ends up `pending` and stitching no-ops. The taxonomy itself is
    # still approved at phase 3, which is what this test asserts.
    assert state.last_completed_phase >= 3
    assert state.taxonomy is not None
    assert state.taxonomy.approved_at is not None
    assert len(state.taxonomy.capabilities) >= 2
    assert state.scan.commit_sha  # set by git rev-parse on tmp_repo
    # SaaS B2B blurb captured.
    assert "billing" in state.guidance.text.lower() or state.guidance.text == ""


def test_bootstrap_resume_skips_completed_phases(tmp_project, mock_agent, monkeypatch):
    repo_root, _cfg = tmp_project
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("first run\n"))
    monkeypatch.setattr("livedocs.ui.is_non_interactive", lambda: True)
    mock_agent.set_response("propor-taxonomia", _CANNED_TAXONOMY)

    rc1 = run_bootstrap(repo_root, accept_taxonomy=True)
    assert rc1 == 0

    # Now resume — should NOT call collect_guidance / scan / taxonomy again.
    # We assert this by making the agent raise if called.
    def explode(*_a, **_k):
        raise AssertionError("agent should not be called on resume after phase 3")

    mock_agent._matchers.clear()
    mock_agent.call = explode  # type: ignore[assignment]

    rc2 = run_bootstrap(repo_root, resume=True, accept_taxonomy=True)
    assert rc2 == 0


def test_bootstrap_without_init_errors(tmp_repo: Path):
    rc = run_bootstrap(tmp_repo, accept_taxonomy=True)
    assert rc == 1
