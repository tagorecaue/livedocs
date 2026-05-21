"""Phase 3 — taxonomy review (non-interactive paths)."""

from __future__ import annotations

from pathlib import Path

from livedocs.bootstrap.state import Capability, Journey, Taxonomy
from livedocs.bootstrap.taxonomy_review import review_taxonomy


def _sample_tax() -> Taxonomy:
    return Taxonomy(
        capabilities=[
            Capability(slug="cobranca", title="Cobrança", summary="x", code_anchors=["src/**"]),
            Capability(slug="usuarios", title="Usuários", summary="y", code_anchors=[]),
        ],
        journeys=[Journey(slug="prim", title="Primeira", capability_refs=["cobranca"])],
    )


def test_review_non_interactive_approves(tmp_path: Path):
    tax = _sample_tax()
    out = review_taxonomy(tax, tmp_path, non_interactive=True)
    assert out is not None
    assert out.approved_at is not None
    assert len(out.capabilities) == 2


def test_review_auto_accept_approves(tmp_path: Path):
    tax = _sample_tax()
    out = review_taxonomy(tax, tmp_path, auto_accept=True)
    assert out is not None
    assert out.approved_at is not None
