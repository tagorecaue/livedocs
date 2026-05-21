"""Pending-question queue helpers.

Manages the `pending_questions` list inside `BootstrapState`. Each entry
gets a stable `Q{n}` id (sequential, 1-based). Dedup across guides is
intentionally NOT done here — that's commit 4 (Fase 6).

The bootstrap orchestrator and the two passada modules write to the queue
through this thin layer so the id allocation stays centralized.
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
    """Append a new PendingQuestion, return its id."""
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
    """Hint that `qid` also concerns `guide_slug` (best-effort).

    Today we only flip the primary guide_slug if it was empty; full
    cross-guide merging happens in commit 4 via the dedup pass.
    Returns True if the question was found.
    """
    for q in state.pending_questions:
        if q.id == qid:
            if not q.guide_slug:
                q.guide_slug = guide_slug
            return True
    return False


def find_open(state: BootstrapState) -> list[PendingQuestion]:
    return [q for q in state.pending_questions if q.status == "open"]


__all__ = ["add_pending", "find_open", "link_question_to_guide"]
