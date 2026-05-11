"""Tier 2 — Integration tests for the fact-driven interview flow.

These tests cover the full flow from parse_intent through generate_guides
using a mocked agent (no Claude Code subprocess, no tokens, no rede).

Tests verify:
  - parse_intent returns structured metadata (success path) + falha graciosa
  - build_skeleton coerces JSON facts into Fact[], persists state, surfaces split
  - pregen_self_audit returns (ready, audit_dict) shape
  - generate_guides parses envelope, validates files, accumulates cost,
    triggers post-gen audit pipeline
"""

from __future__ import annotations

from pathlib import Path

import pytest

from livedocs.commands.interview import (
    build_skeleton,
    generate_guides,
    parse_intent,
    pregen_self_audit,
)
from livedocs.models import ProjectConfig
from livedocs.state import load_state

# ---------------------------------------------------------------------------
# parse_intent
# ---------------------------------------------------------------------------

class TestParseIntent:
    def test_happy_path(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        mock_agent.set_response(
            "Parse the user's free-text intent",
            {
                "slug": "shopping-cart-lifecycle",
                "domain": "shopping-cart",
                "title": "Shopping Cart Lifecycle",
                "is_new_domain": True,
                "clarification_needed": "",
            },
        )
        result = parse_intent(repo, cfg, "document the cart lifecycle", [])
        assert result is not None
        assert result["slug"] == "shopping-cart-lifecycle"
        assert result["domain"] == "shopping-cart"
        assert result["is_new_domain"] is True

    def test_missing_required_field_fails(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        # Missing 'title'
        mock_agent.set_response(
            "Parse the user's free-text intent",
            {"slug": "x", "domain": "d"},
        )
        result = parse_intent(repo, cfg, "intent text", [])
        # parse_intent considers slug/domain/title all required.
        assert result is None

    def test_agent_error_returns_none(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        # No mock set → MockAgent returns is_error=True by default
        result = parse_intent(repo, cfg, "x", [])
        assert result is None

    def test_existing_domains_passed_to_prompt(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        mock_agent.set_response(
            "Parse the user's free-text intent",
            {"slug": "x", "domain": "contracts", "title": "X", "is_new_domain": False},
        )
        parse_intent(repo, cfg, "doc x", ["contracts", "payments"])
        # The prompt sent to the agent should contain both domain names
        last_call = mock_agent.calls[-1]
        assert "contracts" in last_call["prompt"]
        assert "payments" in last_call["prompt"]


# ---------------------------------------------------------------------------
# build_skeleton
# ---------------------------------------------------------------------------

class TestBuildSkeleton:
    def test_creates_interview_with_facts(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        state = load_state(repo)
        mock_agent.set_response(
            "Build the fact skeleton",
            {
                "title": "Cart Lifecycle",
                "summary": "Cart states and transitions",
                "source_files": ["cart.py"],
                "facts": [
                    {
                        "id": "F1",
                        "kind": "trigger",
                        "text": "Checkout fires when items present",
                        "confidence": "high",
                        "priority": "established",
                        "status": "confirmed",
                        "evidence": [{"kind": "code", "ref": "cart.py:10-15"}],
                    },
                    {
                        "id": "F2",
                        "kind": "invariant",
                        "text": "Checked-out is terminal",
                        "confidence": "medium",
                        "priority": "needs-confirmation",
                        "status": "open",
                        "pending_question": "Is it really terminal?",
                    },
                ],
                "should_split": None,
            },
        )

        iv = build_skeleton(
            repo,
            cfg,
            state,
            slug="cart-lifecycle",
            domain="cart",
            title="Cart Lifecycle (working)",
            intent_text="cart lifecycle",
        )
        assert iv is not None
        assert iv.slug == "cart-lifecycle"
        assert iv.title == "Cart Lifecycle"  # uses agent's refined title
        assert len(iv.facts) == 2
        assert iv.facts[0].id == "F1"
        assert iv.facts[0].priority == "established"
        assert iv.facts[1].priority == "needs-confirmation"
        assert iv.source_files == ["cart.py"]
        assert iv.original_intent == "cart lifecycle"
        # state was persisted with this interview
        assert "cart-lifecycle" in state.interviews
        assert state.last_touched_slug == "cart-lifecycle"
        # Cost accumulated
        assert iv.agent_calls == 1

    def test_empty_facts_returns_none(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        state = load_state(repo)
        mock_agent.set_response(
            "Build the fact skeleton",
            {"title": "X", "summary": "", "source_files": [], "facts": []},
        )
        iv = build_skeleton(repo, cfg, state, slug="x", domain="d", title="X")
        assert iv is None

    def test_malformed_facts_partially_recover(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        """If some facts are dicts and one is junk, the good ones survive."""
        repo, cfg = tmp_project
        state = load_state(repo)
        mock_agent.set_response(
            "Build the fact skeleton",
            {
                "title": "X",
                "facts": [
                    {"id": "F1", "kind": "trigger", "text": "ok"},
                    "totally invalid",
                    {"id": "F3", "kind": "flow", "text": "also ok"},
                ],
            },
        )
        # _fact_from_raw can handle dicts; non-dicts raise inside the loop and
        # are caught + warned. So we end up with 2 facts (F1, F3).
        iv = build_skeleton(repo, cfg, state, slug="x", domain="d", title="X")
        assert iv is not None
        assert len(iv.facts) == 2

    def test_split_suggestion_does_not_abort(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        """should_split is a warning, not a hard stop — the skeleton still builds."""
        repo, cfg = tmp_project
        state = load_state(repo)
        mock_agent.set_response(
            "Build the fact skeleton",
            {
                "title": "Huge topic",
                "facts": [{"id": "F1", "kind": "trigger", "text": "x"}],
                "should_split": {
                    "reason": "30+ facts likely",
                    "suggested_slugs": ["part-a", "part-b"],
                },
            },
        )
        iv = build_skeleton(repo, cfg, state, slug="big", domain="d", title="Big")
        assert iv is not None
        # The skeleton still came back; the warning is non-fatal.
        assert len(iv.facts) == 1


# ---------------------------------------------------------------------------
# pregen_self_audit
# ---------------------------------------------------------------------------

class TestPregenSelfAudit:
    def test_ready_to_generate_true(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        from livedocs.models import Fact, InterviewState

        iv = InterviewState(
            slug="x", domain="d",
            facts=[Fact(id="F1", kind="trigger", text="x", status="confirmed", priority="established")],
        )
        mock_agent.set_response(
            "Self-audit before generating",
            {
                "ready_to_generate": True,
                "assertions": [{"fact_id": "F1", "kind": "trigger", "summary": "X", "evidence_summary": "code"}],
                "pendencias": [],
                "still_open_critical": [],
                "dropped_speculation": [],
            },
        )
        ready, audit = pregen_self_audit(repo, cfg, iv)
        assert ready is True
        assert audit["ready_to_generate"] is True
        assert iv.agent_calls == 1

    def test_blocked_when_critical_open(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        repo, cfg = tmp_project
        from livedocs.models import Fact, InterviewState

        iv = InterviewState(
            slug="x", domain="d",
            facts=[Fact(id="F1", kind="invariant", text="x", status="open", priority="needs-confirmation")],
        )
        mock_agent.set_response(
            "Self-audit before generating",
            {
                "ready_to_generate": False,
                "block_reason": "F1 is critical and unanswered",
                "still_open_critical": ["F1"],
            },
        )
        ready, audit = pregen_self_audit(repo, cfg, iv)
        assert ready is False
        assert "block_reason" in audit

    def test_agent_failure_defaults_to_ready(
        self, tmp_project: tuple[Path, ProjectConfig], mock_agent
    ) -> None:
        """If the audit call fails, we default to ready=True (skip the gate)
        rather than blocking the user. The empty dict signals we skipped."""
        repo, cfg = tmp_project
        from livedocs.models import InterviewState

        iv = InterviewState(slug="x", domain="d")
        # No matcher set → MockAgent returns is_error
        ready, audit = pregen_self_audit(repo, cfg, iv)
        assert ready is True
        assert audit == {}


# ---------------------------------------------------------------------------
# generate_guides — most complex flow, with file verification
# ---------------------------------------------------------------------------

class TestGenerateGuides:
    def _make_interview(self):
        from livedocs.models import Fact, InterviewState

        return InterviewState(
            slug="cart",
            domain="shopping",
            title="Cart",
            facts=[
                Fact(
                    id="F1",
                    kind="trigger",
                    text="checkout fires when items present",
                    status="confirmed",
                    priority="established",
                ),
            ],
        )

    def test_writes_files_and_marks_generated(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo, cfg = tmp_project
        state = load_state(repo)

        # The agent claims to write 3 files — we need them to actually exist
        # on disk for verification to pass. Create them ourselves.
        produto = repo / "docs" / "shopping" / "cart.md"
        tech = repo / "docs" / "shopping" / "cart.tech.md"
        interview_rec = repo / "docs" / "shopping" / "_meta" / "cart.interview.md"
        for f in (produto, tech, interview_rec):
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("placeholder\n", encoding="utf-8")

        # Plain-text envelope (expect_json=False on generate)
        envelope = """{
  "files_written": [
    "docs/shopping/cart.md",
    "docs/shopping/cart.tech.md",
    "docs/shopping/_meta/cart.interview.md"
  ],
  "summary": "Wrote three files",
  "next_recommendation": {"slug": "checkout", "domain": "shopping", "reason": "natural next"}
}"""
        mock_agent.set_response(
            "Write the v1 paired guides",
            text=envelope,
            cost_usd=0.5,
            duration_ms=42_000,
        )

        # Disable the post-gen audit pipeline for this test — we just want
        # to assert the core flow. (The post-gen path is tested in test_evaluator.)
        # Stub out the post-gen pipeline so it doesn't call the agent again.
        import livedocs.evaluator
        import livedocs.iteration
        from livedocs.commands import interview as itv_mod  # noqa: F401

        monkeypatch.setattr(livedocs.evaluator, "run_evaluations", lambda *a, **kw: [])
        monkeypatch.setattr(
            livedocs.iteration, "iterate_until_clean", lambda *a, **kw: []
        )

        iv = self._make_interview()
        state.interviews[iv.slug] = iv
        ok = generate_guides(repo, cfg, iv, global_state=state)
        assert ok is True
        assert iv.status == "generated"
        # Cost was tracked
        assert iv.total_cost_usd == 0.5
        assert iv.agent_calls == 1
        # next_recommendation registered
        slugs = [r.slug for r in state.next_recommendations]
        assert "checkout" in slugs

    def test_missing_files_aborts(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Agent claims files but didn't create them — we must refuse."""
        repo, cfg = tmp_project
        state = load_state(repo)

        envelope = """{
  "files_written": ["docs/shopping/cart.md"],
  "summary": "claimed",
  "next_recommendation": null
}"""
        mock_agent.set_response("Write the v1 paired guides", text=envelope)

        import livedocs.evaluator
        import livedocs.iteration
        monkeypatch.setattr(livedocs.evaluator, "run_evaluations", lambda *a, **kw: [])
        monkeypatch.setattr(livedocs.iteration, "iterate_until_clean", lambda *a, **kw: [])

        iv = self._make_interview()
        state.interviews[iv.slug] = iv
        ok = generate_guides(repo, cfg, iv, global_state=state)
        # Files don't exist on disk → must fail loudly
        assert ok is False
        # Status NOT bumped to generated
        assert iv.status != "generated"

    def test_recovery_when_envelope_silent_but_files_exist(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Agent writes the files but forgets to list them — recover via disk check."""
        repo, cfg = tmp_project
        state = load_state(repo)

        # Files exist on disk
        produto = repo / "docs" / "shopping" / "cart.md"
        tech = repo / "docs" / "shopping" / "cart.tech.md"
        for f in (produto, tech):
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("ok\n", encoding="utf-8")

        # But envelope has empty files_written
        envelope = '{"files_written": [], "summary": "I forgot to list", "next_recommendation": null}'
        mock_agent.set_response("Write the v1 paired guides", text=envelope)

        import livedocs.evaluator
        import livedocs.iteration
        monkeypatch.setattr(livedocs.evaluator, "run_evaluations", lambda *a, **kw: [])
        monkeypatch.setattr(livedocs.iteration, "iterate_until_clean", lambda *a, **kw: [])

        iv = self._make_interview()
        state.interviews[iv.slug] = iv
        ok = generate_guides(repo, cfg, iv, global_state=state)
        # Recovery: files exist on the canonical paths, accept the guide
        assert ok is True
        assert iv.status == "generated"
