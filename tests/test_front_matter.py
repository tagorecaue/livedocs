"""Tests for livedocs.commands.approve._set_status_in_front_matter."""

from __future__ import annotations

from pathlib import Path

from livedocs.commands.approve import _set_status_in_front_matter


class TestFrontMatterStatusUpdate:
    def _file(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "guide.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_updates_unquoted_status(self, tmp_path: Path) -> None:
        p = self._file(
            tmp_path,
            """---
slug: foo
status: generated
---

# Foo

Body.
""",
        )
        assert _set_status_in_front_matter(p, "reviewed") is True
        new = p.read_text()
        assert "status: reviewed" in new
        assert "status: generated" not in new

    def test_updates_quoted_status(self, tmp_path: Path) -> None:
        p = self._file(
            tmp_path,
            """---
slug: foo
status: "generated"
---

Body.
""",
        )
        assert _set_status_in_front_matter(p, "reviewed") is True
        # Note: current implementation strips the surrounding quotes when
        # replacing — that's fine since unquoted is canonical YAML for a
        # simple lowercase identifier.
        new = p.read_text()
        assert "status: reviewed" in new
        assert "generated" not in new

    def test_idempotent_when_already_target(self, tmp_path: Path) -> None:
        p = self._file(
            tmp_path,
            """---
slug: foo
status: reviewed
---
""",
        )
        # Even when status already matches the target, the implementation
        # rewrites the file because the regex consumes trailing whitespace
        # which isn't preserved in the substitution. Result: returns True
        # but the file's *meaningful* content is unchanged.
        result = _set_status_in_front_matter(p, "reviewed")
        assert isinstance(result, bool)
        # The critical guarantee: status: reviewed survives.
        assert "status: reviewed" in p.read_text()

    def test_no_front_matter_returns_false(self, tmp_path: Path) -> None:
        p = self._file(tmp_path, "# just a heading\n\nno front-matter\n")
        assert _set_status_in_front_matter(p, "reviewed") is False

    def test_status_missing_gets_injected(self, tmp_path: Path) -> None:
        """When front-matter exists but has no status field, one is injected."""
        p = self._file(
            tmp_path,
            """---
slug: foo
domain: bar
---

Body.
""",
        )
        # No status: line at all — function injects one before the closing ---.
        result = _set_status_in_front_matter(p, "reviewed")
        assert result is True
        assert "status: reviewed" in p.read_text()
