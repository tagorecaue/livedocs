"""Pending-question queue helpers.

Manages the `pending_questions` list inside `BootstrapState`. Each entry
gets a stable `Q{n}` id (sequential, 1-based).

Phase 4-5 only add questions. Phase 6 (refinement) is the place that:
- merges equivalent questions via `merge_questions(...)` (AI dedup output),
- propagates a maintainer answer from canonical to every merged sibling
  via `propagate_answer(...)`.
"""

from __future__ import annotations

import re
from typing import Literal

from livedocs.bootstrap.state import BootstrapState, PendingQuestion

_QID_RE = re.compile(r"^Q(\d+)$")


def _next_id(state: BootstrapState) -> str:
    used: list[int] = []
    for q in state.pending_questions:
        m = _QID_RE.match(q.id or "")
        if m:
            used.append(int(m.group(1)))
    n = (max(used) if used else 0) + 1
    return f"Q{n}"


def add_pending(
    state: BootstrapState,
    guide_slug: str,
    question: str,
    provisional_answer: str = "",
    confidence: Literal["high", "low"] = "low",
) -> str:
    qid = _next_id(state)
    state.pending_questions.append(
        PendingQuestion(
            id=qid,
            guide_slug=guide_slug,
            question=question,
            provisional_answer=provisional_answer or "",
            confidence=confidence,
            status="open",
        )
    )
    return qid


def link_question_to_guide(
    state: BootstrapState, qid: str, guide_slug: str
) -> bool:
    for q in state.pending_questions:
        if q.id == qid:
            if not q.guide_slug:
                q.guide_slug = guide_slug
            return True
    return False


def find_open(state: BootstrapState) -> list[PendingQuestion]:
    return [q for q in state.pending_questions if q.status == "open"]


def _find(state: BootstrapState, qid: str) -> PendingQuestion | None:
    for q in state.pending_questions:
        if q.id == qid:
            return q
    return None


def merge_questions(
    state: BootstrapState,
    canonical_id: str,
    merged_ids: list[str],
    canonical_question: str | None = None,
) -> list[PendingQuestion]:
    """Group equivalent questions: keep `canonical_id` open, mark others as merged.

    Returns the list of `PendingQuestion`s that were actually touched
    (canonical first if updated, then each merged sibling). Unknown ids
    are silently ignored.
    """
    touched: list[PendingQuestion] = []
    canonical = _find(state, canonical_id)
    if canonical is None:
        return touched
    if canonical_question and canonical_question.strip():
        new_q = canonical_question.strip()
        if new_q != canonical.question:
            canonical.question = new_q
            touched.append(canonical)
    for mid in merged_ids:
        if mid == canonical_id:
            continue
        q = _find(state, mid)
        if q is None:
            continue
        q.status = "merged"
        q.merged_into = canonical_id
        touched.append(q)
    return touched


def propagate_answer(
    state: BootstrapState, canonical_id: str, answer: str
) -> list[PendingQuestion]:
    """Mark canonical as answered and propagate the answer to merged siblings.

    Returns the list of updated questions (canonical first).
    """
    touched: list[PendingQuestion] = []
    canonical = _find(state, canonical_id)
    if canonical is None:
        return touched
    canonical.answer = answer
    canonical.status = "answered"
    touched.append(canonical)
    for q in state.pending_questions:
        if q.id == canonical_id:
            continue
        if q.merged_into == canonical_id and q.status == "merged":
            q.answer = answer
            q.status = "answered"
            touched.append(q)
    return touched


__all__ = [
    "add_pending",
    "find_open",
    "link_question_to_guide",
    "merge_questions",
    "propagate_answer",
]
