"""Tests for livedocs.inbox helpers — issue→item, push_to_inbox, cross-link."""

from __future__ import annotations

from livedocs.inbox import (
    issue_to_inbox,
    push_cross_link_proposal,
    push_issues_to_inbox,
)
from livedocs.models import GlobalState, Issue


def _issue(severity: str = "evidence-based", **kwargs) -> Issue:
    defaults = {
        "id": "I1",
        "severity": severity,
        "dimension": "product_clarity",
        "message": "something is off",
        "location": "guide.md:42",
        "auto_fix_available": False,
        "patch": "",
    }
    defaults.update(kwargs)
    return Issue(**defaults)  # type: ignore[arg-type]


class TestIssueToInbox:
    def test_evidence_based_routes_to_evidence_inbox_type(self) -> None:
        item = issue_to_inbox(_issue(severity="evidence-based"), "g1")
        assert item.type == "evidence_based_issue"
        assert item.guide_slug == "g1"
        # Context captures severity + dimension + message + location
        assert "evidence-based" in item.context
        assert "product_clarity" in item.context
        assert "something is off" in item.context
        assert "guide.md:42" in item.context

    def test_blocker_routes_via_evidence_inbox(self) -> None:
        item = issue_to_inbox(_issue(severity="blocker"), "g1")
        assert item.type == "evidence_based_issue"
        # Blocker action gets a special "Resolve blocker..." prefix
        assert "blocker" in item.proposed_action.lower()

    def test_subjective_routes_via_evidence_inbox(self) -> None:
        item = issue_to_inbox(_issue(severity="subjective"), "g1")
        assert item.type == "evidence_based_issue"

    def test_patch_when_present_becomes_action(self) -> None:
        item = issue_to_inbox(
            _issue(severity="evidence-based", patch="replace X with Y"),
            "g1",
        )
        assert item.proposed_action == "replace X with Y"

    def test_falls_back_to_message_without_patch(self) -> None:
        item = issue_to_inbox(_issue(severity="evidence-based", patch=""), "g1")
        assert item.proposed_action == "something is off"


class TestPushIssuesToInbox:
    def test_appends_unique_ids(self) -> None:
        gs = GlobalState()
        added = push_issues_to_inbox(
            gs,
            "g1",
            [_issue(id="I1"), _issue(id="I2"), _issue(id="I3")],
        )
        assert added == 3
        assert len(gs.inbox) == 3
        # IDs are unique and sequential
        ids = [item.id for item in gs.inbox]
        assert ids == ["INBOX-001", "INBOX-002", "INBOX-003"]

    def test_continues_existing_numbering(self) -> None:
        gs = GlobalState()
        push_issues_to_inbox(gs, "g1", [_issue(id="I1")])
        push_issues_to_inbox(gs, "g2", [_issue(id="I2")])
        push_issues_to_inbox(gs, "g3", [_issue(id="I3")])
        ids = [item.id for item in gs.inbox]
        assert ids == ["INBOX-001", "INBOX-002", "INBOX-003"]

    def test_empty_list_no_op(self) -> None:
        gs = GlobalState()
        added = push_issues_to_inbox(gs, "g", [])
        assert added == 0
        assert gs.inbox == []


class TestPushCrossLinkProposal:
    def test_creates_apply_cross_link_item(self) -> None:
        gs = GlobalState()
        item = push_cross_link_proposal(
            gs,
            target_slug="parceiros-do-projeto",
            target_path="docs/projetos/parceiros-do-projeto.md",
            source_slug="pagamento-de-repasses",
            bullet="- [Pagamento de Repasses](../financeiro/...) — porque ...",
        )
        assert item.type == "apply_cross_link"
        assert item.guide_slug == "parceiros-do-projeto"
        assert item.source_slug == "pagamento-de-repasses"
        assert "pagamento-de-repasses" in item.context
        assert item.patch.startswith("- ")
        # And it's now in the global state's inbox
        assert gs.inbox == [item]

    def test_ids_increment_with_other_items(self) -> None:
        gs = GlobalState()
        push_issues_to_inbox(gs, "g1", [_issue(id="I1")])  # INBOX-001
        item = push_cross_link_proposal(
            gs,
            target_slug="t",
            target_path="p",
            source_slug="s",
            bullet="- x",
        )
        # Cross-link gets INBOX-002 because INBOX-001 already exists
        assert item.id == "INBOX-002"
