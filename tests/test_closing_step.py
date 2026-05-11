"""Tests for the closing-step + new Fact kinds added in v0.2.

Covers:
  - The 4 new Fact kinds (rationale, customer_question, business_rule_unwritten,
    closing_note) are accepted by _fact_from_raw, not coerced to 'flow'
  - closing_step() short-answer path (notes-only, no agent call)
  - closing_step() rich-answer path (agent processes, extracts new facts)
  - closing_step() handles agent errors gracefully (notes preserved, no crash)
  - closing_step() skip path (user just presses Enter)
  - _next_fact_id() picks the lowest free F#
  - _bump_fact_id() increments correctly + fallback for malformed
"""

from __future__ import annotations

from pathlib import Path

import pytest

from livedocs.commands.interview import (
    CLOSING_PROCESS_THRESHOLD,
    _bump_fact_id,
    _fact_from_raw,
    _next_fact_id,
    closing_step,
)
from livedocs.models import Fact, InterviewState, ProjectConfig

# ---------------------------------------------------------------------------
# New Fact kinds accepted by _fact_from_raw
# ---------------------------------------------------------------------------

class TestNewFactKinds:
    @pytest.mark.parametrize(
        "kind",
        ["rationale", "customer_question", "business_rule_unwritten", "closing_note"],
    )
    def test_new_kinds_preserved(self, kind: str) -> None:
        """The 4 knowledge-beyond-code kinds shouldn't be coerced to 'flow'."""
        f = _fact_from_raw({"id": "F1", "kind": kind, "text": "x"})
        assert f.kind == kind

    def test_old_kinds_still_preserved(self) -> None:
        for kind in (
            "trigger", "invariant", "edge_case", "terminology",
            "flow", "value", "actor", "ui_surface",
        ):
            f = _fact_from_raw({"id": "F1", "kind": kind, "text": "x"})
            assert f.kind == kind

    def test_truly_unknown_kind_still_falls_back(self) -> None:
        """Sanity: garbage kinds still get coerced to 'flow'."""
        f = _fact_from_raw({"id": "F1", "kind": "totally-made-up", "text": "x"})
        assert f.kind == "flow"


# ---------------------------------------------------------------------------
# _next_fact_id + _bump_fact_id
# ---------------------------------------------------------------------------

class TestFactIdHelpers:
    def test_next_fact_id_with_empty_interview(self) -> None:
        iv = InterviewState(slug="x", domain="d")
        assert _next_fact_id(iv) == "F1"

    def test_next_fact_id_picks_lowest_free(self) -> None:
        iv = InterviewState(
            slug="x", domain="d",
            facts=[
                Fact(id="F1", kind="trigger", text="a"),
                Fact(id="F3", kind="trigger", text="c"),
            ],
        )
        # F2 is the gap
        assert _next_fact_id(iv) == "F2"

    def test_next_fact_id_continues_after_max(self) -> None:
        iv = InterviewState(
            slug="x", domain="d",
            facts=[Fact(id=f"F{n}", kind="trigger", text=str(n)) for n in (1, 2, 3, 4)],
        )
        assert _next_fact_id(iv) == "F5"

    def test_next_fact_id_ignores_malformed_ids(self) -> None:
        iv = InterviewState(
            slug="x", domain="d",
            facts=[
                Fact(id="garbage", kind="trigger", text="x"),
                Fact(id="F2", kind="trigger", text="x"),
            ],
        )
        # Only F2 is recognized → next free is F1 (since F1 isn't used)
        assert _next_fact_id(iv) == "F1"

    def test_bump_fact_id(self) -> None:
        assert _bump_fact_id("F1") == "F2"
        assert _bump_fact_id("F99") == "F100"
        assert _bump_fact_id("F0") == "F1"

    def test_bump_fact_id_fallback(self) -> None:
        assert _bump_fact_id("garbage") == "F1"
        assert _bump_fact_id("") == "F1"
        assert _bump_fact_id("F?") == "F1"


# ---------------------------------------------------------------------------
# closing_step
# ---------------------------------------------------------------------------

def _make_interview(*facts: Fact) -> InterviewState:
    return InterviewState(slug="x", domain="d", title="X", facts=list(facts))


class TestClosingStepShortAnswer:
    """Below the threshold: notes-only, NO agent call."""

    def test_short_answer_saved_to_notes(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo, cfg = tmp_project
        iv = _make_interview()

        # Simulate user typing a short answer.
        short_answer = "Nada de importante além do que já falei."
        assert len(short_answer) < CLOSING_PROCESS_THRESHOLD

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: short_answer)

        added = closing_step(repo, cfg, iv)
        assert added == 0
        assert iv.notes == short_answer
        # Agent should NEVER have been called (short answer = notes-only path)
        assert mock_agent.calls == []
        # No new facts added
        assert iv.facts == []

    def test_blank_answer_skips_entirely(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo, cfg = tmp_project
        iv = _make_interview()

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: "")

        added = closing_step(repo, cfg, iv)
        assert added == 0
        assert iv.notes == ""
        assert mock_agent.calls == []

    def test_none_answer_skips(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When ask_text returns None (Ctrl-C / EOF), skip cleanly."""
        repo, cfg = tmp_project
        iv = _make_interview()

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: None)

        added = closing_step(repo, cfg, iv)
        assert added == 0
        assert mock_agent.calls == []


class TestClosingStepRichAnswer:
    """Above the threshold: agent processes, extracts facts."""

    def _long_answer(self) -> str:
        # > CLOSING_PROCESS_THRESHOLD (80)
        return (
            "Tem uma regra importante que esquecemos: quando o cliente pede "
            "estorno, a comissão do parceiro também precisa ser estornada "
            "no próximo ciclo. Isso não está documentado em lugar nenhum mas "
            "todo mundo sabe que tem que fazer."
        )

    def test_rich_answer_extracts_new_facts(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo, cfg = tmp_project
        iv = _make_interview()

        long_answer = self._long_answer()
        assert len(long_answer) >= CLOSING_PROCESS_THRESHOLD

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: long_answer)

        mock_agent.set_response(
            "Process the user's closing free-form answer",
            {
                "new_facts": [
                    {
                        "id": "F?",
                        "kind": "business_rule_unwritten",
                        "text": "Estorno de cliente dispara estorno da comissão do parceiro no próximo ciclo",
                        "confidence": "high",
                        "priority": "established",
                        "status": "confirmed",
                        "evidence": [{"kind": "answer", "ref": "closing", "note": "User stated verbatim"}],
                    },
                    {
                        "id": "F?",
                        "kind": "closing_note",
                        "text": "Regra cultural não documentada formalmente",
                        "confidence": "medium",
                        "priority": "established",
                        "status": "confirmed",
                        "evidence": [{"kind": "answer", "ref": "closing"}],
                    },
                ],
                "appendix_notes": "",
            },
        )

        added = closing_step(repo, cfg, iv)
        assert added == 2
        assert len(iv.facts) == 2
        # IDs got assigned (F1 and F2 since interview was empty)
        ids = {f.id for f in iv.facts}
        assert ids == {"F1", "F2"}
        # Kinds preserved
        kinds = {f.kind for f in iv.facts}
        assert "business_rule_unwritten" in kinds
        assert "closing_note" in kinds
        # User's verbatim answer is in notes
        assert long_answer in iv.notes

    def test_id_collisions_get_renumbered(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If agent returns F1 but interview already has F1, give the new one F#next."""
        repo, cfg = tmp_project
        iv = _make_interview(
            Fact(id="F1", kind="trigger", text="existing"),
            Fact(id="F2", kind="invariant", text="existing"),
        )

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: self._long_answer())

        mock_agent.set_response(
            "Process the user's closing free-form answer",
            {
                "new_facts": [
                    {"id": "F1", "kind": "closing_note", "text": "should be renamed"},
                ],
                "appendix_notes": "",
            },
        )

        added = closing_step(repo, cfg, iv)
        assert added == 1
        # Original F1 untouched
        assert iv.facts[0].text == "existing"
        # New fact got F3 (F1 and F2 already taken)
        assert iv.facts[2].id == "F3"
        assert iv.facts[2].text == "should be renamed"

    def test_appendix_notes_appended(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo, cfg = tmp_project
        iv = _make_interview()

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: self._long_answer())

        mock_agent.set_response(
            "Process the user's closing free-form answer",
            {
                "new_facts": [],
                "appendix_notes": "Resumo: regra de estorno cruzada parceiro/cliente.",
            },
        )

        closing_step(repo, cfg, iv)
        # Both raw answer AND agent's summary are in notes
        assert self._long_answer() in iv.notes
        assert "Resumo:" in iv.notes

    def test_agent_error_preserves_notes_no_crash(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the agent call fails, the user's answer is still preserved."""
        repo, cfg = tmp_project
        iv = _make_interview()

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: self._long_answer())

        # No mock response set → MockAgent returns is_error=True

        added = closing_step(repo, cfg, iv)
        # Failed gracefully — answer still preserved as notes, no new facts
        assert added == 0
        assert self._long_answer() in iv.notes
        # No facts added (the structuring failed)
        assert iv.facts == []

    def test_malformed_new_facts_filtered(
        self,
        tmp_project: tuple[Path, ProjectConfig],
        mock_agent,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo, cfg = tmp_project
        iv = _make_interview()

        from livedocs import ui as ui_module
        monkeypatch.setattr(ui_module, "ask_text", lambda *a, **kw: self._long_answer())

        mock_agent.set_response(
            "Process the user's closing free-form answer",
            {
                "new_facts": [
                    "not a dict",
                    {"id": "F?", "kind": "closing_note", "text": "this one is fine"},
                    None,
                ],
                "appendix_notes": "",
            },
        )

        added = closing_step(repo, cfg, iv)
        assert added == 1
        assert len(iv.facts) == 1
        assert iv.facts[0].text == "this one is fine"
