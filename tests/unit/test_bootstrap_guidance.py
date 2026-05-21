"""Phase 0 — guidance capture."""

from __future__ import annotations

import io

from livedocs.bootstrap.guidance import MAX_GUIDANCE_CHARS, collect_guidance


def test_collect_guidance_non_interactive_empty(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    g = collect_guidance(non_interactive=True)
    assert g.text == ""
    assert g.captured_at  # ISO timestamp set


def test_collect_guidance_non_interactive_pipe(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("Sou maintainer do projeto X.\nSaaS B2B de billing."))
    g = collect_guidance(non_interactive=True)
    assert "billing" in g.text
    assert g.captured_at


def test_collect_guidance_long_text_warning(monkeypatch, capsys):
    long_text = "x" * (MAX_GUIDANCE_CHARS + 100)
    monkeypatch.setattr("sys.stdin", io.StringIO(long_text))
    g = collect_guidance(non_interactive=True)
    # Text is accepted as-is.
    assert len(g.text) > MAX_GUIDANCE_CHARS
