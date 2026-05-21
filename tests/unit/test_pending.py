"""Tests for the PendingQuestion queue helpers."""

from __future__ import annotations

from livedocs.bootstrap.pending import (
    add_pending,
    find_open,
    link_question_to_guide,
    merge_questions,
    propagate_answer,
)
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


def test_merge_questions_marks_siblings():
    state = BootstrapState()
    add_pending(state, "a", "Quanto desconto?")
    add_pending(state, "a", "Desconto antecipado?")
    add_pending(state, "b", "Pode antecipar pagando menos?")
    touched = merge_questions(
        state, "Q1", ["Q2", "Q3"], canonical_question="Existe desconto por antecipação?"
    )
    assert state.pending_questions[0].question == "Existe desconto por antecipação?"
    assert state.pending_questions[1].status == "merged"
    assert state.pending_questions[1].merged_into == "Q1"
    assert state.pending_questions[2].status == "merged"
    assert state.pending_questions[2].merged_into == "Q1"
    # Canonical is in touched (because question changed) plus the two merged.
    assert len(touched) == 3


def test_merge_questions_unknown_canonical_is_noop():
    state = BootstrapState()
    add_pending(state, "a", "x?")
    touched = merge_questions(state, "Q99", ["Q1"])
    assert touched == []
    assert state.pending_questions[0].status == "open"


def test_propagate_answer_to_merged_siblings():
    state = BootstrapState()
    add_pending(state, "a", "q1?")
    add_pending(state, "b", "q2?")
    merge_questions(state, "Q1", ["Q2"])
    updated = propagate_answer(state, "Q1", "Sim, com 5% off.")
    ids = [u.id for u in updated]
    assert ids == ["Q1", "Q2"]
    assert state.pending_questions[0].status == "answered"
    assert state.pending_questions[0].answer == "Sim, com 5% off."
    assert state.pending_questions[1].status == "answered"
    assert state.pending_questions[1].answer == "Sim, com 5% off."


def test_propagate_answer_does_not_touch_unrelated_open():
    state = BootstrapState()
    add_pending(state, "a", "q1?")
    add_pending(state, "b", "q2?")
    # Q2 is unrelated/open
    propagate_answer(state, "Q1", "yes")
    assert state.pending_questions[1].status == "open"
    assert state.pending_questions[1].answer == ""
