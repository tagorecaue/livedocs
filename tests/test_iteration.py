"""Tests for livedocs.iteration._select_auto_fixable — what gets auto-fixed."""

from __future__ import annotations

from livedocs.iteration import _select_auto_fixable
from livedocs.models import Evaluation, Issue


def _issue(
    *,
    id: str = "I1",
    severity: str = "evidence-based",
    auto_fix_available: bool = True,
    patch: str = "rename X to Y",
    applied: bool = False,
) -> Issue:
    return Issue(
        id=id,
        severity=severity,  # type: ignore[arg-type]
        dimension="product_clarity",
        message="",
        auto_fix_available=auto_fix_available,
        patch=patch,
        applied=applied,
    )


def _eval(*issues: Issue) -> Evaluation:
    return Evaluation(dimension="product_clarity", issues=list(issues))


class TestSelectAutoFixable:
    def test_evidence_based_with_patch_selected(self) -> None:
        out = _select_auto_fixable([_eval(_issue(severity="evidence-based"))])
        assert len(out) == 1

    def test_subjective_with_patch_selected(self) -> None:
        out = _select_auto_fixable([_eval(_issue(severity="subjective"))])
        assert len(out) == 1

    def test_blocker_never_selected(self) -> None:
        # Even with auto_fix_available=true and patch present.
        out = _select_auto_fixable([_eval(_issue(severity="blocker"))])
        assert out == []

    def test_already_applied_not_reselected(self) -> None:
        out = _select_auto_fixable([_eval(_issue(applied=True))])
        assert out == []

    def test_auto_fix_unavailable_skipped(self) -> None:
        out = _select_auto_fixable([_eval(_issue(auto_fix_available=False))])
        assert out == []

    def test_empty_patch_skipped(self) -> None:
        out = _select_auto_fixable([_eval(_issue(patch=""))])
        assert out == []

    def test_whitespace_only_patch_skipped(self) -> None:
        out = _select_auto_fixable([_eval(_issue(patch="   \n\t  "))])
        assert out == []

    def test_mixed_batch(self) -> None:
        ev = _eval(
            _issue(id="I1", severity="evidence-based"),  # ✓ pick
            _issue(id="I2", severity="blocker"),  # ✗ blocker
            _issue(id="I3", severity="subjective"),  # ✓ pick
            _issue(id="I4", severity="subjective", auto_fix_available=False),  # ✗ no auto
            _issue(id="I5", severity="evidence-based", patch=""),  # ✗ no patch
            _issue(id="I6", severity="evidence-based", applied=True),  # ✗ already applied
        )
        picked = _select_auto_fixable([ev])
        ids = {i.id for i in picked}
        assert ids == {"I1", "I3"}

    def test_picks_across_multiple_evaluations(self) -> None:
        evals = [
            _eval(_issue(id="A1")),
            _eval(_issue(id="B1")),
            _eval(_issue(id="C1", severity="blocker")),
        ]
        out = _select_auto_fixable(evals)
        assert {i.id for i in out} == {"A1", "B1"}
