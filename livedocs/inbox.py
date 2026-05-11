"""Inbox helpers — push surviving issues + cross-base proposals into the queue.

These functions are called by:
  - `generate_guides` after iteration (to push remaining issues)
  - `approve` after the human reviews a guide (to push reverse-link proposals)

The actual UI for browsing inbox lives in `commands/inbox.py`.
"""

from __future__ import annotations

from livedocs.models import GlobalState, InboxItem, Issue


def issue_to_inbox(issue: Issue, guide_slug: str) -> InboxItem:
    """Convert an unresolved evaluation issue into an InboxItem."""
    if issue.severity == "blocker":
        type_ = "evidence_based_issue"  # blockers route through same UI
        action = f"Resolve blocker before publish: {issue.message[:120]}"
    elif issue.severity == "evidence-based":
        type_ = "evidence_based_issue"
        action = issue.patch or issue.message
    else:  # subjective without auto-fix
        type_ = "evidence_based_issue"
        action = issue.patch or issue.message

    return InboxItem(
        id="placeholder",  # caller fills via GlobalState.next_inbox_id()
        type=type_,
        guide_slug=guide_slug,
        context=(
            f"[{issue.severity}] {issue.dimension}: {issue.message}"
            + (f" ({issue.location})" if issue.location else "")
        ),
        proposed_action=action,
        patch=issue.patch,
    )


def push_issues_to_inbox(
    state: GlobalState,
    guide_slug: str,
    issues: list[Issue],
) -> int:
    """Push surviving issues into the inbox. Returns count actually added."""
    added = 0
    for issue in issues:
        item = issue_to_inbox(issue, guide_slug)
        item.id = state.next_inbox_id()
        state.inbox.append(item)
        added += 1
    return added


def push_cross_link_proposal(
    state: GlobalState,
    *,
    target_slug: str,
    target_path: str,
    source_slug: str,
    bullet: str,
) -> InboxItem:
    """Create an InboxItem for a reverse-cross-link proposal."""
    item = InboxItem(
        id=state.next_inbox_id(),
        type="apply_cross_link",
        guide_slug=target_slug,
        source_slug=source_slug,
        context=f"Reverse link from {source_slug} → {target_slug}",
        proposed_action=f"Add bullet to '## Veja também' in `{target_path}`",
        patch=bullet,
    )
    state.inbox.append(item)
    return item


__all__ = ["issue_to_inbox", "push_issues_to_inbox", "push_cross_link_proposal"]
