"""Tests for `livedocs refine`.

Covers:
  - _apply_changes happy path (single + multi-change)
  - Anchor not found → RefineError, no writes
  - Anchor matches multiple times → RefineError
  - File not in repo → RefineError
  - File doesn't exist → RefineError
  - Trying to refine _index.md → RefineError
  - Chained edits in same file (second edit matches content created by first)
  - run_refine end-to-end with mock agent: status flips reviewed→generated
  - run_refine end-to-end: status generated stays generated
  - run_refine respects refine_status_blocked for non-eligible status
  - Empty changes list → no writes, no status flip
"""

from __future__ import annotations

from pathlib import Path

import pytest

from livedocs.commands.refine import RefineError, _apply_changes, run_refine
from livedocs.models import (
    Fact,
    GlobalState,
    InterviewState,
    ProjectConfig,
)
from livedocs.state import save_state

# ---------------------------------------------------------------------------
# _apply_changes — pure validation + application
# ---------------------------------------------------------------------------

class TestApplyChangesHappyPath:
    def test_single_change_in_one_file(self, tmp_path: Path) -> None:
        f = tmp_path / "guide.md"
        f.write_text("hello world\nfoo bar\n", encoding="utf-8")

        applied = _apply_changes(
            tmp_path,
            [{"file": "guide.md", "old": "foo bar", "new": "FOO BAR"}],
        )
        assert applied == [f]
        assert f.read_text() == "hello world\nFOO BAR\n"

    def test_multi_change_same_file(self, tmp_path: Path) -> None:
        f = tmp_path / "guide.md"
        f.write_text("A\nB\nC\n", encoding="utf-8")

        applied = _apply_changes(
            tmp_path,
            [
                {"file": "guide.md", "old": "A\n", "new": "A1\n"},
                {"file": "guide.md", "old": "C\n", "new": "C1\n"},
            ],
        )
        assert applied == [f]
        assert f.read_text() == "A1\nB\nC1\n"

    def test_changes_across_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "produto.md"
        f1.write_text("alpha\n", encoding="utf-8")
        f2 = tmp_path / "tech.md"
        f2.write_text("beta\n", encoding="utf-8")

        applied = _apply_changes(
            tmp_path,
            [
                {"file": "produto.md", "old": "alpha", "new": "ALPHA"},
                {"file": "tech.md", "old": "beta", "new": "BETA"},
            ],
        )
        assert set(applied) == {f1, f2}
        assert f1.read_text() == "ALPHA\n"
        assert f2.read_text() == "BETA\n"

    def test_chained_edits(self, tmp_path: Path) -> None:
        """Second change can match content created by the first."""
        f = tmp_path / "g.md"
        f.write_text("start\n", encoding="utf-8")

        _apply_changes(
            tmp_path,
            [
                {"file": "g.md", "old": "start", "new": "middle"},
                {"file": "g.md", "old": "middle", "new": "end"},
            ],
        )
        assert f.read_text() == "end\n"


class TestApplyChangesValidation:
    def test_anchor_not_found_aborts(self, tmp_path: Path) -> None:
        f = tmp_path / "g.md"
        original = "hello world\n"
        f.write_text(original, encoding="utf-8")

        with pytest.raises(RefineError, match="anchor not found"):
            _apply_changes(
                tmp_path,
                [{"file": "g.md", "old": "nonexistent string", "new": "X"}],
            )
        # File untouched
        assert f.read_text() == original

    def test_anchor_ambiguous_aborts(self, tmp_path: Path) -> None:
        f = tmp_path / "g.md"
        original = "foo\nfoo\nfoo\n"
        f.write_text(original, encoding="utf-8")

        with pytest.raises(RefineError, match="matches 3 places"):
            _apply_changes(
                tmp_path,
                [{"file": "g.md", "old": "foo", "new": "bar"}],
            )
        assert f.read_text() == original

    def test_one_bad_change_rolls_back_entire_batch(self, tmp_path: Path) -> None:
        """If ANY change fails validation, NOTHING gets written."""
        f1 = tmp_path / "ok.md"
        f1.write_text("alpha\n", encoding="utf-8")
        f2 = tmp_path / "bad.md"
        f2.write_text("beta\n", encoding="utf-8")

        with pytest.raises(RefineError):
            _apply_changes(
                tmp_path,
                [
                    {"file": "ok.md", "old": "alpha", "new": "ALPHA"},
                    {"file": "bad.md", "old": "nonexistent", "new": "X"},
                ],
            )
        # Both files are untouched
        assert f1.read_text() == "alpha\n"
        assert f2.read_text() == "beta\n"

    def test_file_outside_repo_aborts(self, tmp_path: Path) -> None:
        with pytest.raises(RefineError, match="outside the repo"):
            _apply_changes(
                tmp_path,
                [{"file": "../../../etc/passwd", "old": "x", "new": "y"}],
            )

    def test_file_does_not_exist_aborts(self, tmp_path: Path) -> None:
        with pytest.raises(RefineError, match="does not exist"):
            _apply_changes(
                tmp_path,
                [{"file": "no-such.md", "old": "x", "new": "y"}],
            )

    def test_refuses_index_md(self, tmp_path: Path) -> None:
        (tmp_path / "_index.md").write_text("x\n", encoding="utf-8")
        with pytest.raises(RefineError, match="_index.md"):
            _apply_changes(
                tmp_path,
                [{"file": "_index.md", "old": "x", "new": "y"}],
            )

    def test_missing_file_field_aborts(self, tmp_path: Path) -> None:
        with pytest.raises(RefineError, match="missing 'file'"):
            _apply_changes(
                tmp_path,
                [{"old": "x", "new": "y"}],
            )

    def test_missing_old_aborts(self, tmp_path: Path) -> None:
        (tmp_path / "g.md").write_text("x\n", encoding="utf-8")
        with pytest.raises(RefineError, match="empty 'old'"):
            _apply_changes(
                tmp_path,
                [{"file": "g.md", "new": "y"}],
            )

    def test_non_dict_change_aborts(self, tmp_path: Path) -> None:
        with pytest.raises(RefineError, match="not an object"):
            _apply_changes(tmp_path, ["not a dict"])


# ---------------------------------------------------------------------------
# run_refine — end-to-end (with mock agent)
# ---------------------------------------------------------------------------

def _setup_guide(
    repo: Path,
    cfg: ProjectConfig,
    slug: str,
    status: str = "reviewed",
) -> tuple[InterviewState, Path, Path]:
    """Create a domain/slug + produto.md + tech.md + a saved InterviewState."""
    from livedocs.state import guides_root

    domain = "demo"
    iv = InterviewState(
        slug=slug,
        domain=domain,
        title=slug.replace("-", " ").title(),
        status=status,
        facts=[Fact(id="F1", kind="trigger", text="initial fact")],
    )

    state = GlobalState(interviews={slug: iv})
    save_state(repo, state)

    domain_dir = guides_root(repo, cfg) / domain
    domain_dir.mkdir(parents=True, exist_ok=True)

    produto = domain_dir / f"{slug}.md"
    produto.write_text(
        "---\nslug: " + slug + "\nstatus: " + status + "\n---\n\n## Intro\n\nfoo bar baz\n",
        encoding="utf-8",
    )
    tech = domain_dir / f"{slug}.tech.md"
    tech.write_text(
        "---\nslug: " + slug + "\n---\n\n## R1\n\nclaim about code\n",
        encoding="utf-8",
    )
    return iv, produto, tech


class TestRunRefineEndToEnd:
    def test_reviewed_flips_to_generated(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        iv, produto, _tech = _setup_guide(repo, cfg, "demo-guide", status="reviewed")

        mock_agent.set_response(
            "Refine an existing guide",
            {
                "summary": "Replaced foo with FOO",
                "changes": [
                    {
                        "file": str(produto.relative_to(repo)),
                        "old": "foo bar baz",
                        "new": "FOO bar baz",
                        "reason": "stylistic",
                    }
                ],
                "code_checks_performed": [],
            },
        )

        rc = run_refine(repo, slug="demo-guide", instruction="uppercase foo")
        assert rc == 0
        assert "FOO bar baz" in produto.read_text()

        # Status got flipped reviewed → generated
        from livedocs.state import load_state
        state2 = load_state(repo)
        assert state2.interviews["demo-guide"].status == "generated"

    def test_generated_stays_generated(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        _iv, produto, _tech = _setup_guide(repo, cfg, "demo-guide", status="generated")

        mock_agent.set_response(
            "Refine an existing guide",
            {
                "summary": "Replaced foo with FOO",
                "changes": [
                    {
                        "file": str(produto.relative_to(repo)),
                        "old": "foo bar baz",
                        "new": "FOO bar baz",
                        "reason": "stylistic",
                    }
                ],
                "code_checks_performed": [],
            },
        )

        rc = run_refine(repo, slug="demo-guide", instruction="uppercase foo")
        assert rc == 0

        from livedocs.state import load_state
        state2 = load_state(repo)
        assert state2.interviews["demo-guide"].status == "generated"  # unchanged

    def test_status_blocked_for_in_progress(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        _setup_guide(repo, cfg, "demo-guide", status="in_progress")

        rc = run_refine(repo, slug="demo-guide", instruction="x")
        assert rc == 1
        # No agent calls — bailed before invoking
        assert mock_agent.calls == []

    def test_unknown_slug_errors_out(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, _cfg = tmp_project
        rc = run_refine(repo, slug="does-not-exist", instruction="x")
        assert rc == 1
        assert mock_agent.calls == []

    def test_empty_changes_no_status_change_no_writes(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        _iv, produto, _tech = _setup_guide(repo, cfg, "demo-guide", status="reviewed")
        original = produto.read_text()

        mock_agent.set_response(
            "Refine an existing guide",
            {
                "summary": "Instruction unclear, no changes made",
                "changes": [],
                "code_checks_performed": [],
            },
        )

        rc = run_refine(repo, slug="demo-guide", instruction="vague")
        assert rc == 0
        # File untouched
        assert produto.read_text() == original
        # Status NOT flipped
        from livedocs.state import load_state
        state2 = load_state(repo)
        assert state2.interviews["demo-guide"].status == "reviewed"

    def test_bad_anchor_no_writes_no_status_change(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        """Agent returns a bad anchor → CLI rejects, file untouched, status preserved."""
        repo, cfg = tmp_project
        _iv, produto, _tech = _setup_guide(repo, cfg, "demo-guide", status="reviewed")
        original = produto.read_text()

        mock_agent.set_response(
            "Refine an existing guide",
            {
                "summary": "Bad change",
                "changes": [
                    {
                        "file": str(produto.relative_to(repo)),
                        "old": "this string is not in the file",
                        "new": "X",
                    }
                ],
                "code_checks_performed": [],
            },
        )

        rc = run_refine(repo, slug="demo-guide", instruction="bad")
        assert rc == 1
        # File untouched
        assert produto.read_text() == original
        # Status preserved
        from livedocs.state import load_state
        state2 = load_state(repo)
        assert state2.interviews["demo-guide"].status == "reviewed"

    def test_cost_tracked_on_interview(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        _iv, produto, _tech = _setup_guide(repo, cfg, "demo-guide", status="reviewed")

        from livedocs.state import load_state
        baseline = load_state(repo).interviews["demo-guide"]
        before_calls = baseline.agent_calls

        mock_agent.set_response(
            "Refine an existing guide",
            {
                "summary": "x",
                "changes": [
                    {"file": str(produto.relative_to(repo)), "old": "foo bar baz", "new": "x"}
                ],
                "code_checks_performed": [],
            },
        )

        run_refine(repo, slug="demo-guide", instruction="x")

        state2 = load_state(repo)
        assert state2.interviews["demo-guide"].agent_calls == before_calls + 1
