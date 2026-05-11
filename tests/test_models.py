"""Tests for livedocs.models — validation, derived properties, defaults."""

from __future__ import annotations

from livedocs.models import (
    Evidence,
    Fact,
    GlobalState,
    InboxItem,
    InterviewState,
    Issue,
    ProjectConfig,
)

# ---------------------------------------------------------------------------
# ProjectConfig
# ---------------------------------------------------------------------------

class TestProjectConfig:
    def test_minimal_construction(self) -> None:
        cfg = ProjectConfig(project_slug="x")
        assert cfg.lang == "en"
        assert cfg.provider == "claude-code"
        assert cfg.docs_dir == "docs"
        assert cfg.guides_subdir == ""
        assert cfg.use_graphify is False
        assert cfg.style == "narrative"
        # created_at is auto-populated by default factory
        assert cfg.created_at != ""
        assert "T" in cfg.created_at  # ISO format

    def test_override_fields(self) -> None:
        cfg = ProjectConfig(
            project_slug="rgz",
            lang="pt-BR",
            docs_dir="packages/docs",
            guides_subdir="guides",
            style="reference",
        )
        assert cfg.lang == "pt-BR"
        assert cfg.guides_subdir == "guides"
        assert cfg.style == "reference"


# ---------------------------------------------------------------------------
# Fact + Evidence
# ---------------------------------------------------------------------------

class TestFact:
    def test_required_fields(self) -> None:
        f = Fact(id="F1", kind="trigger", text="something happens")
        assert f.id == "F1"
        assert f.confidence == "none"
        assert f.priority == "needs-confirmation"
        assert f.status == "open"
        assert f.evidence == []
        assert f.derived_from == []
        assert f.answer_text is None
        assert f.pending_question is None

    def test_evidence_attachment(self) -> None:
        f = Fact(
            id="F2",
            kind="invariant",
            text="checked_out is terminal",
            evidence=[
                Evidence(kind="code", ref="cart.py:42-50"),
                Evidence(kind="answer", ref="F2", note="user confirmed"),
            ],
        )
        assert len(f.evidence) == 2
        assert f.evidence[0].kind == "code"
        assert f.evidence[1].note == "user confirmed"


# ---------------------------------------------------------------------------
# InterviewState — derived helpers
# ---------------------------------------------------------------------------

def _make_facts() -> list[Fact]:
    """Build a fixture set of facts spanning every relevant combination."""
    return [
        # established + confirmed
        Fact(id="F1", kind="trigger", text="a", priority="established", status="confirmed"),
        Fact(id="F2", kind="invariant", text="b", priority="established", status="confirmed"),
        # needs-confirmation, still open (pending)
        Fact(id="F3", kind="flow", text="c", priority="needs-confirmation", status="open"),
        Fact(id="F4", kind="edge_case", text="d", priority="needs-confirmation", status="open"),
        # needs-confirmation, already resolved (covered by another answer)
        Fact(id="F5", kind="flow", text="e", priority="needs-confirmation", status="resolved"),
        # hypothesis-with-trace
        Fact(id="F6", kind="value", text="f", priority="hypothesis-with-trace", status="hypothesized"),
        # speculation
        Fact(id="F7", kind="actor", text="g", priority="speculation", status="open"),
    ]


class TestInterviewState:
    def test_pending_facts_excludes_resolved_and_non_needs_conf(self) -> None:
        iv = InterviewState(slug="x", domain="d", facts=_make_facts())
        pending = iv.pending_facts()
        ids = {f.id for f in pending}
        # Only F3 and F4 are needs-confirmation + status not in (confirmed, resolved)
        assert ids == {"F3", "F4"}

    def test_confirmed_facts_includes_resolved(self) -> None:
        iv = InterviewState(slug="x", domain="d", facts=_make_facts())
        confirmed = iv.confirmed_facts()
        ids = {f.id for f in confirmed}
        # F1 (confirmed), F2 (confirmed), F5 (resolved)
        assert ids == {"F1", "F2", "F5"}

    def test_hypothesized_facts(self) -> None:
        iv = InterviewState(slug="x", domain="d", facts=_make_facts())
        assert [f.id for f in iv.hypothesized_facts()] == ["F6"]

    def test_open_facts(self) -> None:
        iv = InterviewState(slug="x", domain="d", facts=_make_facts())
        # status == "open": F3, F4 (needs-conf open), F7 (speculation open)
        assert {f.id for f in iv.open_facts()} == {"F3", "F4", "F7"}

    def test_coverage_ratio_excludes_speculation(self) -> None:
        iv = InterviewState(slug="x", domain="d", facts=_make_facts())
        # Actionable (non-speculation): F1..F6 = 6 facts
        # Resolved/confirmed: F1, F2, F5 = 3
        # Hypothesized (partial weight 0.5): F6 = 1 -> 0.5
        # Open (needs-conf): F3, F4 = 2 -> count 0
        # ratio = (3 + 0.5*1) / 6 = 3.5 / 6
        assert iv.coverage_ratio() == 3.5 / 6

    def test_coverage_ratio_empty(self) -> None:
        iv = InterviewState(slug="x", domain="d", facts=[])
        assert iv.coverage_ratio() == 0.0

    def test_coverage_ratio_only_speculation(self) -> None:
        iv = InterviewState(
            slug="x",
            domain="d",
            facts=[Fact(id="F1", kind="actor", text="", priority="speculation", status="open")],
        )
        # No actionable facts -> 0
        assert iv.coverage_ratio() == 0.0

    def test_compute_confidence_score_full_house(self) -> None:
        iv = InterviewState(slug="x", domain="d", facts=_make_facts())
        # confirmed (status in confirmed/resolved): F1, F2, F5 = 3
        # hypothesized: F6 = 1
        # open (status == open): F3, F4, F7 = 3
        # denom = 3 + 1 + 0.5*3 = 5.5
        # score = 3 / 5.5
        assert abs(iv.compute_confidence_score() - 3 / 5.5) < 1e-9

    def test_compute_confidence_score_empty(self) -> None:
        iv = InterviewState(slug="x", domain="d")
        assert iv.compute_confidence_score() == 0.0

    def test_questions_shim_projects_facts(self) -> None:
        """Legacy .questions read-only shim used by v0.1 CLI surfaces."""
        iv = InterviewState(slug="x", domain="d", facts=_make_facts())
        qs = iv.questions
        assert len(qs) == 7
        # First fact F1 was confirmed via established — answer_text is None
        # but the projection maps id/text correctly
        assert qs[0].id == "F1"
        assert qs[0].block == "F"  # synthesized from id letter
        # F7 is speculation+open -> skipped True in legacy semantics
        assert qs[6].skipped is True
        # Answered facts should report answer == answer_text (None here since
        # _make_facts doesn't populate answer_text)
        assert qs[0].answer is None


# ---------------------------------------------------------------------------
# GlobalState — inbox helpers
# ---------------------------------------------------------------------------

def _make_inbox_items() -> list[InboxItem]:
    return [
        InboxItem(
            id="INBOX-001",
            type="apply_cross_link",
            guide_slug="g1",
            context="x",
            proposed_action="y",
            status="pending",
        ),
        InboxItem(
            id="INBOX-002",
            type="evidence_based_issue",
            guide_slug="g2",
            context="x",
            proposed_action="y",
            status="accepted",
        ),
        InboxItem(
            id="INBOX-003",
            type="apply_cross_link",
            guide_slug="g3",
            context="x",
            proposed_action="y",
            status="snoozed",
        ),
        InboxItem(
            id="INBOX-005",
            type="apply_cross_link",
            guide_slug="g5",
            context="x",
            proposed_action="y",
            status="pending",
        ),
    ]


class TestGlobalState:
    def test_pending_inbox_filters_status(self) -> None:
        gs = GlobalState(inbox=_make_inbox_items())
        pending = gs.pending_inbox()
        # Only INBOX-001 and INBOX-005 are 'pending'
        # (snoozed is not pending, per the model spec used in commands/inbox.py)
        ids = {i.id for i in pending}
        assert ids == {"INBOX-001", "INBOX-005"}

    def test_next_inbox_id_increments_max(self) -> None:
        gs = GlobalState(inbox=_make_inbox_items())
        # Highest existing is 005 -> next is 006
        assert gs.next_inbox_id() == "INBOX-006"

    def test_next_inbox_id_starts_at_001(self) -> None:
        gs = GlobalState()
        assert gs.next_inbox_id() == "INBOX-001"

    def test_next_inbox_id_skips_malformed(self) -> None:
        # If something garbled is in the inbox, we still produce a valid next id
        gs = GlobalState(
            inbox=[
                InboxItem(
                    id="weird-thing-no-suffix",
                    type="apply_cross_link",
                    guide_slug="g",
                    context="x",
                    proposed_action="y",
                ),
                InboxItem(
                    id="INBOX-042",
                    type="apply_cross_link",
                    guide_slug="g",
                    context="x",
                    proposed_action="y",
                ),
            ]
        )
        assert gs.next_inbox_id() == "INBOX-043"


# ---------------------------------------------------------------------------
# Issue / Evaluation defaults
# ---------------------------------------------------------------------------

class TestIssue:
    def test_minimal_construction(self) -> None:
        i = Issue(id="I1", severity="subjective", dimension="product_clarity", message="foo")
        assert i.location == ""
        assert i.auto_fix_available is False
        assert i.patch == ""
        assert i.applied is False
