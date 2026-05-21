"""Tests for the PendingQuestion queue helpers."""

from __future__ import annotations

from livedocs.bootstrap.pending import add_pending, find_open, link_question_to_guide
from livedocs.bootstrap.state import (
    BootstrapState,
    load_bootstrap_state,
    save_bootstrap_state,
)


def test_add_pending_sequential_ids():
    state = BootstrapState()
    q1 = add_pending(state, "cobranca", "P1?", "ans1", "low")
    q2 = add_pending(state, "cobranca", "P2?", "", "high")
    q3 = add_pending(state, "users", "P3?", "ans3", "low")
    assert q1 == "Q1"
    assert q2 == "Q2"
    assert q3 == "Q3"
    assert state.pending_questions[0].provisional_answer == "ans1"
    assert state.pending_questions[1].confidence == "high"


def test_ids_survive_reload(tmp_path):
    state = BootstrapState()
    add_pending(state, "a", "x?")
    add_pending(state, "a", "y?")
    save_bootstrap_state(tmp_path, state)
    reloaded = load_bootstrap_state(tmp_path)
    assert reloaded is not None
    assert [q.id for q in reloaded.pending_questions] == ["Q1", "Q2"]
    # next id continues sequentially
    next_id = add_pending(reloaded, "b", "z?")
    assert next_id == "Q3"


def test_find_open_filters_status():
    state = BootstrapState()
    add_pending(state, "a", "q1?")
    qid = add_pending(state, "a", "q2?")
    # mark one answered
    for q in state.pending_questions:
        if q.id == qid:
            q.status = "answered"
    opens = find_open(state)
    assert [q.id for q in opens] == ["Q1"]


def test_link_question_to_guide():
    state = BootstrapState()
    qid = add_pending(state, "", "orphan?")
    assert link_question_to_guide(state, qid, "users") is True
    assert state.pending_questions[0].guide_slug == "users"
    # Unknown id
    assert link_question_to_guide(state, "Q99", "x") is False
