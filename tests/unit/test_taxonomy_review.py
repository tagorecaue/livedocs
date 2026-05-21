"""Phase 3 — taxonomy review (non-interactive paths + new article actions)."""

from __future__ import annotations

import json
from pathlib import Path

from livedocs.bootstrap.state import Article, Capability, Journey, Taxonomy
from livedocs.bootstrap.taxonomy_review import (
    _do_inspect,
    _do_manage,
    _do_split,
    review_taxonomy,
)


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
    # Invariante: toda capability tem ≥ 1 article.
    for c in out.capabilities:
        assert len(c.articles) >= 1
        assert c.articles[0].is_intro is True


def test_review_auto_accept_approves(tmp_path: Path):
    tax = _sample_tax()
    out = review_taxonomy(tax, tmp_path, auto_accept=True)
    assert out is not None
    assert out.approved_at is not None


# ---------------------------------------------------------------------------
# [i] inspect
# ---------------------------------------------------------------------------

def _seed_cache(repo: Path) -> None:
    cache = repo / ".livedocs" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "routes.json").write_text(json.dumps([
        {"path": "/billing", "file": "src/billing/Index.vue"},
        {"path": "/users", "file": "src/users/List.vue"},
    ]))
    (cache / "models.json").write_text(json.dumps([
        {"name": "Invoice", "file": "src/billing/Invoice.ts"},
        {"name": "User", "file": "src/users/User.ts"},
    ]))


def test_inspect_renders_no_ia(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_cache(repo)
    # Make a couple of source files so glob counts > 0.
    (repo / "src" / "billing").mkdir(parents=True)
    (repo / "src" / "billing" / "Index.vue").write_text("x")
    (repo / "src" / "billing" / "Invoice.ts").write_text("x")

    tax = Taxonomy(capabilities=[
        Capability(slug="billing", title="Billing", summary="",
                   code_anchors=["src/billing/**"],
                   articles=[Article(slug="introducao", title="Billing", is_intro=True)]),
    ])

    monkeypatch.setattr("livedocs.bootstrap.taxonomy_review.ui.ask_text", lambda *a, **k: "1")
    # Should not raise; also no agent call expected.
    _do_inspect(tax, repo)


# ---------------------------------------------------------------------------
# [s] split assistido
# ---------------------------------------------------------------------------

def test_split_assistido_replaces_articles(tmp_path: Path, monkeypatch, mock_agent):
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_cache(repo)

    tax = Taxonomy(capabilities=[
        Capability(slug="billing", title="Billing", summary="Cobrança",
                   code_anchors=["src/billing/**"],
                   articles=[Article(slug="introducao", title="Billing", is_intro=True)]),
    ])

    # Mock IA returning a 3-article proposal.
    mock_agent.set_response("split-capability", json_data={
        "articles": [
            {"slug": "introducao", "title": "Visão geral", "summary": "",
             "is_intro": True, "code_anchors": ["src/billing/**"]},
            {"slug": "boletos", "title": "Emissão de boletos", "summary": "",
             "is_intro": False, "code_anchors": ["src/billing/boletos/**"]},
            {"slug": "conciliacao", "title": "Conciliação", "summary": "",
             "is_intro": False, "code_anchors": ["src/billing/recon/**"]},
        ],
    })

    # User picks capability 1, then accepts.
    ask_text_calls = iter(["1"])
    monkeypatch.setattr(
        "livedocs.bootstrap.taxonomy_review.ui.ask_text",
        lambda *a, **k: next(ask_text_calls, ""),
    )

    choice_calls = iter(["accept"])
    monkeypatch.setattr(
        "livedocs.bootstrap.taxonomy_review.ui.ask_choice",
        lambda *a, **k: next(choice_calls, None),
    )

    _do_split(tax, repo, guidance_text="", lang="pt-BR")

    cap = tax.capabilities[0]
    assert len(cap.articles) == 3
    slugs = [a.slug for a in cap.articles]
    assert slugs == ["introducao", "boletos", "conciliacao"]
    assert cap.articles[0].is_intro is True


# ---------------------------------------------------------------------------
# [A] manage articles
# ---------------------------------------------------------------------------

def test_manage_articles_add_then_remove(tmp_path: Path, monkeypatch):
    tax = Taxonomy(capabilities=[
        Capability(slug="billing", title="Billing", summary="",
                   articles=[
                       Article(slug="introducao", title="Intro", is_intro=True),
                   ]),
    ])

    # ask_text feeds: capability index, then add prompts (slug, title, summary, anchors),
    # then for remove: which-article index.
    text_inputs = iter([
        "1",            # pick capability
        "boletos",      # new article slug
        "Boletos",      # title
        "",             # summary
        "",             # anchors
        "2",            # remove which N (we'll add → list has 2 → remove #2)
    ])
    monkeypatch.setattr(
        "livedocs.bootstrap.taxonomy_review.ui.ask_text",
        lambda *a, **k: next(text_inputs, ""),
    )

    choice_inputs = iter([
        "add",      # action: add
        "no",       # intro? no
        "remove",   # action: remove
        "back",     # quit loop
    ])
    monkeypatch.setattr(
        "livedocs.bootstrap.taxonomy_review.ui.ask_choice",
        lambda *a, **k: next(choice_inputs, None),
    )

    _do_manage(tax)

    cap = tax.capabilities[0]
    # Started with 1, added 1 (=2), removed 1 → 1 article remaining.
    assert len(cap.articles) == 1
    assert cap.articles[0].slug == "introducao"


def test_manage_articles_cannot_remove_last(tmp_path: Path, monkeypatch):
    tax = Taxonomy(capabilities=[
        Capability(slug="billing", title="Billing", summary="",
                   articles=[Article(slug="introducao", title="Intro", is_intro=True)]),
    ])

    text_inputs = iter(["1"])
    monkeypatch.setattr(
        "livedocs.bootstrap.taxonomy_review.ui.ask_text",
        lambda *a, **k: next(text_inputs, ""),
    )

    choice_inputs = iter(["remove", "back"])
    monkeypatch.setattr(
        "livedocs.bootstrap.taxonomy_review.ui.ask_choice",
        lambda *a, **k: next(choice_inputs, None),
    )

    _do_manage(tax)
    # Last article was protected.
    assert len(tax.capabilities[0].articles) == 1
