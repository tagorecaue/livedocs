"""Tests for parsers: envelope, fact_from_raw, apply_reflection."""

from __future__ import annotations

from livedocs.commands.interview import (
    _apply_reflection,
    _fact_from_raw,
    _parse_generate_envelope,
)
from livedocs.models import Fact, InterviewState

# ---------------------------------------------------------------------------
# _parse_generate_envelope: extracts files_written + summary + next_recommendation
# ---------------------------------------------------------------------------

class TestParseGenerateEnvelope:
    def test_clean_json(self) -> None:
        envelope = """{
          "files_written": ["a.md", "b.md"],
          "summary": "Wrote stuff",
          "next_recommendation": {"slug": "next-x", "domain": "d", "reason": "because"}
        }"""
        files, summary, next_rec = _parse_generate_envelope(envelope)
        assert files == ["a.md", "b.md"]
        assert summary == "Wrote stuff"
        assert next_rec == {"slug": "next-x", "domain": "d", "reason": "because"}

    def test_json_inside_code_fence(self) -> None:
        envelope = """```json
{
  "files_written": ["a.md"],
  "summary": "ok",
  "next_recommendation": null
}
```"""
        files, summary, next_rec = _parse_generate_envelope(envelope)
        assert files == ["a.md"]
        assert summary == "ok"
        assert next_rec is None

    def test_json_inside_unlabeled_fence(self) -> None:
        envelope = "```\n{\"files_written\": [\"x.md\"], \"summary\": \"ok\"}\n```"
        files, summary, _ = _parse_generate_envelope(envelope)
        assert files == ["x.md"]
        assert summary == "ok"

    def test_json_with_prose_before(self) -> None:
        envelope = """I wrote three files. Here's the summary:

{
  "files_written": ["a.md", "b.md", "c.md"],
  "summary": "Done",
  "next_recommendation": null
}"""
        files, summary, _ = _parse_generate_envelope(envelope)
        assert files == ["a.md", "b.md", "c.md"]
        assert summary == "Done"

    def test_json_with_prose_around_extracts_first_object(self) -> None:
        # The regex extracts everything between the first { and the last }
        envelope = """Hi.
{
  "files_written": ["a.md"],
  "summary": "ok"
}
Some more text."""
        files, _, _ = _parse_generate_envelope(envelope)
        assert files == ["a.md"]

    def test_empty_input(self) -> None:
        files, summary, next_rec = _parse_generate_envelope("")
        assert files == []
        assert summary == ""
        assert next_rec is None

    def test_completely_malformed(self) -> None:
        files, summary, next_rec = _parse_generate_envelope("not json at all")
        assert files == []
        assert summary == ""
        assert next_rec is None

    def test_invalid_json_returns_empties(self) -> None:
        # Looks like JSON but is broken
        files, summary, _ = _parse_generate_envelope("{broken: no quotes}")
        assert files == []
        assert summary == ""

    def test_non_object_top_level(self) -> None:
        # JSON list at top level - not what we want
        files, _, _ = _parse_generate_envelope("[1, 2, 3]")
        assert files == []

    def test_files_written_filters_non_strings(self) -> None:
        envelope = '{"files_written": ["a.md", 42, null, "b.md"], "summary": "x"}'
        files, _, _ = _parse_generate_envelope(envelope)
        assert files == ["a.md", "b.md"]

    def test_next_recommendation_non_dict_dropped(self) -> None:
        envelope = '{"files_written": [], "summary": "", "next_recommendation": "not a dict"}'
        _, _, next_rec = _parse_generate_envelope(envelope)
        assert next_rec is None


# ---------------------------------------------------------------------------
# _fact_from_raw: coerce loose JSON into a strict Fact
# ---------------------------------------------------------------------------

class TestFactFromRaw:
    def test_minimal_well_formed(self) -> None:
        f = _fact_from_raw(
            {
                "id": "F1",
                "kind": "trigger",
                "text": "X happens when Y",
                "confidence": "high",
                "priority": "established",
                "status": "confirmed",
                "evidence": [],
            }
        )
        assert f.id == "F1"
        assert f.kind == "trigger"
        assert f.confidence == "high"
        assert f.priority == "established"
        assert f.status == "confirmed"

    def test_invalid_kind_falls_back_to_flow(self) -> None:
        f = _fact_from_raw({"id": "F1", "kind": "garbage", "text": "x"})
        assert f.kind == "flow"

    def test_invalid_confidence_falls_back_to_none(self) -> None:
        f = _fact_from_raw({"id": "F1", "kind": "trigger", "text": "x", "confidence": "ultra-mega"})
        assert f.confidence == "none"

    def test_invalid_priority_falls_back_to_needs_confirmation(self) -> None:
        f = _fact_from_raw(
            {"id": "F1", "kind": "trigger", "text": "x", "priority": "very-important"}
        )
        assert f.priority == "needs-confirmation"

    def test_invalid_status_falls_back_to_open(self) -> None:
        f = _fact_from_raw({"id": "F1", "kind": "trigger", "text": "x", "status": "weird"})
        assert f.status == "open"

    def test_missing_id_gets_placeholder(self) -> None:
        f = _fact_from_raw({"kind": "trigger", "text": "x"})
        # Falls back to "F?" — caller may renumber, but parsing doesn't crash
        assert f.id == "F?"

    def test_evidence_coerced_to_evidence_models(self) -> None:
        f = _fact_from_raw(
            {
                "id": "F1",
                "kind": "trigger",
                "text": "x",
                "evidence": [
                    {"kind": "code", "ref": "cart.py:10", "note": "good"},
                    {"kind": "invalid-kind", "ref": "x"},  # bad kind → hypothesis
                    "not a dict",  # silently dropped
                    {"kind": "answer", "ref": "F1"},
                ],
            }
        )
        # Three valid pieces (dict items), the bare string dropped
        assert len(f.evidence) == 3
        assert f.evidence[0].kind == "code"
        assert f.evidence[1].kind == "hypothesis"  # coerced
        assert f.evidence[2].kind == "answer"

    def test_pending_question_empty_string_becomes_none(self) -> None:
        f = _fact_from_raw({"id": "F1", "kind": "trigger", "text": "x", "pending_question": ""})
        assert f.pending_question is None

    def test_derived_from_filters_non_strings(self) -> None:
        f = _fact_from_raw(
            {
                "id": "F2",
                "kind": "trigger",
                "text": "x",
                "derived_from": ["F1", 42, None, "F3"],
            }
        )
        assert f.derived_from == ["F1", "F3"]


# ---------------------------------------------------------------------------
# _apply_reflection: mutate facts based on agent's verdict
# ---------------------------------------------------------------------------

def _make_iv(*facts: Fact) -> InterviewState:
    return InterviewState(slug="x", domain="d", facts=list(facts))


class TestApplyReflectionConfirmed:
    def test_marks_fact_confirmed_and_adds_answer_evidence(self) -> None:
        f = Fact(id="F1", kind="trigger", text="x", status="open")
        iv = _make_iv(f)
        _apply_reflection(iv, f, "answer text", {"outcome": "confirmed"})
        assert f.status == "confirmed"
        assert any(e.kind == "answer" and e.ref == "F1" for e in f.evidence)


class TestApplyReflectionContradicted:
    def test_marks_contradicted_with_evidence(self) -> None:
        f = Fact(id="F1", kind="trigger", text="x", status="open")
        iv = _make_iv(f)
        _apply_reflection(
            iv,
            f,
            "answer",
            {
                "outcome": "contradicted",
                "contradiction_note": "code says X, not Y",
                "code_ref": "cart.py:42",
            },
        )
        assert f.status == "contradicted"
        # Has both code evidence (the contradiction) and answer evidence
        kinds = [e.kind for e in f.evidence]
        assert "code" in kinds
        assert "answer" in kinds


class TestApplyReflectionCorrected:
    def test_confirmed_with_correction_adds_code_evidence(self) -> None:
        f = Fact(id="F1", kind="trigger", text="x", status="open")
        iv = _make_iv(f)
        _apply_reflection(
            iv,
            f,
            "answer",
            {
                "outcome": "confirmed_with_correction",
                "correction_note": "minor nuance",
                "code_ref": "cart.py:1",
            },
        )
        assert f.status == "confirmed"
        assert any(e.kind == "code" for e in f.evidence)
        assert any(e.kind == "answer" for e in f.evidence)


class TestApplyReflectionNeedsMore:
    def test_with_follow_up_sets_open_and_updates_question(self) -> None:
        f = Fact(id="F1", kind="trigger", text="x", status="open", pending_question="Q1?")
        iv = _make_iv(f)
        _apply_reflection(
            iv,
            f,
            "answer",
            {"outcome": "needs_more", "follow_up_question": "Tell me about X then?"},
        )
        assert f.status == "open"
        assert f.pending_question == "Tell me about X then?"

    def test_without_follow_up_falls_through_to_confirmed(self) -> None:
        f = Fact(id="F1", kind="trigger", text="x", status="open")
        iv = _make_iv(f)
        _apply_reflection(iv, f, "answer", {"outcome": "needs_more", "follow_up_question": ""})
        # When follow-up is empty, we accept the answer as confirmed
        assert f.status == "confirmed"


class TestApplyReflectionCoversOthers:
    def test_resolves_other_pending_facts(self) -> None:
        f1 = Fact(id="F1", kind="trigger", text="x", priority="needs-confirmation", status="open")
        f2 = Fact(id="F2", kind="invariant", text="y", priority="needs-confirmation", status="open")
        f3 = Fact(id="F3", kind="flow", text="z", priority="established", status="confirmed")
        iv = _make_iv(f1, f2, f3)

        _apply_reflection(
            iv,
            f1,
            "ans",
            {"outcome": "confirmed", "covers_other_facts": ["F2", "F3"]},
        )
        # F2 became resolved + established
        assert f2.status == "resolved"
        assert f2.priority == "established"
        # F3 was already confirmed — we don't touch it
        assert f3.status == "confirmed"
        # F1 (the answered fact) stays as confirmed
        assert f1.status == "confirmed"

    def test_ignores_unknown_covered_ids(self) -> None:
        f1 = Fact(id="F1", kind="trigger", text="x", status="open")
        iv = _make_iv(f1)
        # Reference F99 which doesn't exist
        _apply_reflection(
            iv,
            f1,
            "ans",
            {"outcome": "confirmed", "covers_other_facts": ["F99"]},
        )
        # No crash, F1 still gets confirmed
        assert f1.status == "confirmed"


class TestApplyReflectionNewFacts:
    def test_appends_new_facts(self) -> None:
        f1 = Fact(id="F1", kind="trigger", text="x", status="open")
        iv = _make_iv(f1)
        _apply_reflection(
            iv,
            f1,
            "ans",
            {
                "outcome": "confirmed",
                "new_facts": [
                    {
                        "id": "F2",
                        "kind": "invariant",
                        "text": "emerged from F1 answer",
                        "priority": "established",
                        "status": "confirmed",
                    }
                ],
            },
        )
        assert len(iv.facts) == 2
        assert iv.facts[1].text == "emerged from F1 answer"

    def test_id_collision_gets_renamed(self) -> None:
        f1 = Fact(id="F1", kind="trigger", text="x", status="open")
        f2 = Fact(id="F2", kind="trigger", text="y", status="confirmed")
        iv = _make_iv(f1, f2)
        _apply_reflection(
            iv,
            f1,
            "ans",
            {
                "outcome": "confirmed",
                "new_facts": [
                    {
                        "id": "F1",  # collision with existing F1
                        "kind": "invariant",
                        "text": "new fact",
                    }
                ],
            },
        )
        assert len(iv.facts) == 3
        # New fact got renumbered to F3 (next available after F1, F2)
        new_fact = iv.facts[2]
        assert new_fact.id == "F3"
        assert new_fact.text == "new fact"

    def test_malformed_new_fact_dropped_silently(self) -> None:
        f1 = Fact(id="F1", kind="trigger", text="x", status="open")
        iv = _make_iv(f1)
        _apply_reflection(
            iv,
            f1,
            "ans",
            {
                "outcome": "confirmed",
                # Wrong shape; _fact_from_raw should swallow the exception in caller
                "new_facts": ["just a string, not a dict"],
            },
        )
        # No crash; no new fact added
        assert len(iv.facts) == 1
