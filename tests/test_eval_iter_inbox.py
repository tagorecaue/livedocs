"""Tier 2 — Tests for the evaluator + iteration loop."""

from __future__ import annotations

from pathlib import Path

from livedocs.evaluator import run_evaluations
from livedocs.iteration import iterate_until_clean
from livedocs.models import (
    Evaluation,
    GlobalState,
    InterviewState,
    Issue,
    ProjectConfig,
)


def _make_interview() -> InterviewState:
    return InterviewState(
        slug="cart",
        domain="shopping",
        title="Cart",
        facts=[],
    )


# ---------------------------------------------------------------------------
# run_evaluations — 3 dimensions in parallel
# ---------------------------------------------------------------------------

class TestRunEvaluations:
    def test_three_dimensions_run_and_return(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = _make_interview()

        mock_agent.set_response(
            "product-flavored guide for clarity",
            {
                "summary": "ok",
                "issues": [
                    {
                        "id": "PC-01",
                        "severity": "evidence-based",
                        "message": "jargon",
                        "location": "x.md:42",
                        "auto_fix_available": True,
                        "patch": "rename",
                    }
                ],
            },
        )
        mock_agent.set_response(
            "tech-flavored guide for completeness",
            {
                "summary": "ok",
                "issues": [
                    {
                        "id": "TC-01",
                        "severity": "subjective",
                        "message": "more cites",
                        "auto_fix_available": True,
                        "patch": "add cite",
                    }
                ],
            },
        )
        mock_agent.set_response(
            "consistent with what is already documented",
            {"summary": "ok", "issues": []},
        )

        results = run_evaluations(repo, cfg, state, iv)
        assert len(results) == 3
        dims = {r.dimension for r in results}
        assert dims == {"product_clarity", "tech_completeness", "base_coherence"}
        # Cost was accumulated for each call
        assert iv.agent_calls == 3
        # Issues populated where mock returned them
        by_dim = {r.dimension: r for r in results}
        assert len(by_dim["product_clarity"].issues) == 1
        assert by_dim["product_clarity"].issues[0].id == "PC-01"
        assert len(by_dim["tech_completeness"].issues) == 1
        assert len(by_dim["base_coherence"].issues) == 0

    def test_invalid_severity_falls_back_to_subjective(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = _make_interview()

        mock_agent.set_response(
            "product-flavored guide for clarity",
            {
                "issues": [
                    {"severity": "critical-mega", "message": "x"},  # invalid → subjective
                ],
            },
        )
        mock_agent.set_response("tech-flavored", {"issues": []})
        mock_agent.set_response("consistent with", {"issues": []})

        results = run_evaluations(repo, cfg, state, iv)
        pc = next(r for r in results if r.dimension == "product_clarity")
        assert len(pc.issues) == 1
        assert pc.issues[0].severity == "subjective"

    def test_issue_with_no_message_dropped(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = _make_interview()
        mock_agent.set_response(
            "product-flavored",
            {
                "issues": [
                    {"id": "X1", "severity": "subjective"},  # no message
                    {"id": "X2", "severity": "subjective", "message": "  "},  # blank message
                ],
            },
        )
        mock_agent.set_response("tech-flavored", {"issues": []})
        mock_agent.set_response("consistent with", {"issues": []})

        results = run_evaluations(repo, cfg, state, iv)
        pc = next(r for r in results if r.dimension == "product_clarity")
        # Both dropped (empty message)
        assert pc.issues == []

    def test_individual_failure_does_not_break_others(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = _make_interview()
        # product_clarity has no mock → will fail
        mock_agent.set_response("tech-flavored", {"issues": [{"id": "X", "severity": "subjective", "message": "ok"}]})
        mock_agent.set_response("consistent with", {"issues": []})

        results = run_evaluations(repo, cfg, state, iv)
        # Still 3 evaluations come back, the failed one with empty issues + (failed: ...) summary
        assert len(results) == 3
        pc = next(r for r in results if r.dimension == "product_clarity")
        assert pc.issues == []
        assert "failed" in pc.summary
        # The other two succeeded
        tc = next(r for r in results if r.dimension == "tech_completeness")
        assert len(tc.issues) == 1


# ---------------------------------------------------------------------------
# iterate_until_clean — auto-fix loop
# ---------------------------------------------------------------------------

class TestIterateUntilClean:
    def _make_eval(self, issues: list[Issue]) -> Evaluation:
        return Evaluation(dimension="product_clarity", issues=issues)

    def _make_issue(
        self,
        id: str = "I1",
        severity: str = "evidence-based",
        auto: bool = True,
        patch: str = "rename X to Y",
    ) -> Issue:
        return Issue(
            id=id,
            severity=severity,  # type: ignore[arg-type]
            dimension="product_clarity",
            message="msg",
            location="g.md:42",
            auto_fix_available=auto,
            patch=patch,
        )

    def test_zero_cycles_when_nothing_auto_fixable(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = _make_interview()
        # Only blockers (never auto)
        evals = [self._make_eval([self._make_issue(severity="blocker")])]
        remaining = iterate_until_clean(repo, cfg, state, iv, evals)
        # The blocker survives (not applied)
        assert len(remaining) == 1
        assert remaining[0].severity == "blocker"
        # No agent calls made (no fixes attempted)
        assert iv.agent_calls == 0

    def test_one_cycle_applies_then_converges(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = _make_interview()
        issue = self._make_issue(id="I1")
        evals = [self._make_eval([issue])]

        # Apply call: agent says it applied I1
        # The actual prompt header is "Apply small fixes to the generated guides".
        mock_agent.set_response(
            "Apply small fixes",
            {"applied": ["cart/I1"], "skipped": []},
        )
        # Re-eval after apply: all clean
        for matcher in (
            "product-flavored",
            "tech-flavored",
            "consistent with",
        ):
            mock_agent.set_response(matcher, {"issues": []})

        remaining = iterate_until_clean(repo, cfg, state, iv, evals)
        # The fix was applied; nothing survived to the inbox
        assert remaining == []
        # Marked applied on the original issue
        assert issue.applied is True

    def test_stops_at_max_cycles(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        """If the agent claims to apply but new issues keep appearing, we cap at 3 cycles."""
        repo, cfg = tmp_project
        state = GlobalState()
        iv = _make_interview()

        # Initial: one fixable issue
        evals = [self._make_eval([self._make_issue(id="I1")])]

        # Apply call always succeeds (agent applies I1 in cycle 1, I2 in cycle 2, etc.)
        # We don't care about specifics; just keep approving everything.
        for _ in range(3):
            mock_agent.set_response(
                "Apply small fixes",
                {"applied": ["cart/I1", "cart/I2", "cart/I3"], "skipped": []},
            )

        # Each re-evaluation produces a NEW fixable issue with a different id.
        # Cycle 1's re-eval introduces I2; cycle 2's intro I3; cycle 3's intro I4.
        for issue_id in ("I2", "I3", "I4"):
            for matcher in ("product-flavored", "tech-flavored", "consistent with"):
                if matcher == "product-flavored":
                    mock_agent.set_response(
                        matcher,
                        {"issues": [{"id": issue_id, "severity": "subjective",
                                     "message": "z", "auto_fix_available": True, "patch": "p"}]},
                    )
                else:
                    mock_agent.set_response(matcher, {"issues": []})

        iterate_until_clean(repo, cfg, state, iv, evals)
        # After MAX_CYCLES=3, whatever issue was uncovered is in remaining
        # (or empty if the last cycle happened to converge — but in this setup, won't)
        # Either way, the loop is bounded.
        assert iv.agent_calls <= 12  # 3 cycles × (1 apply + 3 evals) max
        # We don't assert exact count of remaining — the loop's stopping
        # condition is the cap, and `remaining` reflects whatever the last eval saw.


# ---------------------------------------------------------------------------
# reverse_link sweep
# ---------------------------------------------------------------------------

class TestReverseLinkSweep:
    def test_proposals_added_to_inbox(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = InterviewState(slug="cart", domain="shopping", title="Cart")

        mock_agent.set_response(
            "Propose reverse cross-links",
            {
                "proposals": [
                    {
                        "target_slug": "checkout",
                        "target_path": "docs/shopping/checkout.md",
                        "bullet": "- [Cart](../shopping/cart.md) — explica o estado de origem.",
                    },
                    {
                        "target_slug": "payments",
                        "target_path": "docs/shopping/payments.md",
                        "bullet": "- [Cart](../shopping/cart.md) — onde o pagamento começa.",
                    },
                ]
            },
        )
        from livedocs.commands.reverse_link import run_reverse_link_sweep

        n = run_reverse_link_sweep(repo, cfg, state, iv)
        assert n == 2
        assert len(state.inbox) == 2
        types = {i.type for i in state.inbox}
        assert types == {"apply_cross_link"}
        # Each item has source_slug set to the new guide
        for item in state.inbox:
            assert item.source_slug == "cart"

    def test_drops_invalid_proposals(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
    ) -> None:
        repo, cfg = tmp_project
        state = GlobalState()
        iv = InterviewState(slug="cart", domain="shopping", title="Cart")

        mock_agent.set_response(
            "Propose reverse cross-links",
            {
                "proposals": [
                    {"target_slug": "", "bullet": "no slug"},  # missing slug
                    {"target_slug": "checkout", "bullet": ""},  # missing bullet
                    {"target_slug": "valid", "target_path": "x.md", "bullet": "- ok"},
                    "totally not a dict",
                ]
            },
        )
        from livedocs.commands.reverse_link import run_reverse_link_sweep

        n = run_reverse_link_sweep(repo, cfg, state, iv)
        # Only the one well-formed proposal survives
        assert n == 1


# ---------------------------------------------------------------------------
# inbox UI: _apply_cross_link (filesystem behavior, no agent)
# ---------------------------------------------------------------------------

class TestApplyCrossLinkAction:
    def test_appends_to_existing_section(
        self,
        tmp_project: tuple[Path, ProjectConfig],
    ) -> None:
        from livedocs.commands.inbox import _apply_cross_link
        from livedocs.models import InboxItem

        repo, cfg = tmp_project
        # Create a guide with existing Veja também
        target = repo / "docs" / "shopping" / "checkout.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            """---
slug: checkout
---

# Checkout

## Veja também

- [Existing](./existing.md)
""",
            encoding="utf-8",
        )
        item = InboxItem(
            id="INBOX-001",
            type="apply_cross_link",
            guide_slug="checkout",
            context="x",
            proposed_action="y",
            patch="- [Cart](../shopping/cart.md) — origem",
        )
        ok = _apply_cross_link(repo, cfg, item)
        assert ok is True
        new = target.read_text()
        # Both bullets present
        assert "[Existing]" in new
        assert "[Cart]" in new

    def test_creates_section_when_missing(
        self,
        tmp_project: tuple[Path, ProjectConfig],
    ) -> None:
        from livedocs.commands.inbox import _apply_cross_link
        from livedocs.models import InboxItem

        repo, cfg = tmp_project
        target = repo / "docs" / "shopping" / "checkout.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            """---
slug: checkout
---

# Checkout

Some body.
""",
            encoding="utf-8",
        )
        item = InboxItem(
            id="INBOX-001",
            type="apply_cross_link",
            guide_slug="checkout",
            context="x",
            proposed_action="y",
            patch="- [Cart](../shopping/cart.md)",
        )
        ok = _apply_cross_link(repo, cfg, item)
        assert ok is True
        new = target.read_text()
        # New section was added
        assert "## Veja também" in new
        assert "[Cart]" in new

    def test_idempotent_skips_duplicate_bullet(
        self,
        tmp_project: tuple[Path, ProjectConfig],
    ) -> None:
        from livedocs.commands.inbox import _apply_cross_link
        from livedocs.models import InboxItem

        repo, cfg = tmp_project
        target = repo / "docs" / "shopping" / "checkout.md"
        target.parent.mkdir(parents=True)
        bullet = "- [Cart](../shopping/cart.md)"
        target.write_text(
            f"""---
slug: checkout
---

# Checkout

## Veja também

{bullet}
""",
            encoding="utf-8",
        )
        item = InboxItem(
            id="INBOX-001",
            type="apply_cross_link",
            guide_slug="checkout",
            context="x",
            proposed_action="y",
            patch=bullet,  # exact same bullet
        )
        ok = _apply_cross_link(repo, cfg, item)
        # Idempotent: returns True but doesn't duplicate
        assert ok is True
        new = target.read_text()
        # Bullet still present exactly once
        assert new.count(bullet) == 1

    def test_returns_false_when_target_missing(
        self,
        tmp_project: tuple[Path, ProjectConfig],
    ) -> None:
        from livedocs.commands.inbox import _apply_cross_link
        from livedocs.models import InboxItem

        repo, cfg = tmp_project
        # No file created for "nonexistent"
        item = InboxItem(
            id="INBOX-001",
            type="apply_cross_link",
            guide_slug="nonexistent",
            context="x",
            proposed_action="y",
            patch="- something",
        )
        assert _apply_cross_link(repo, cfg, item) is False
