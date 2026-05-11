"""Tests for livedocs.skill.styles — built-in templates + style.md handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from livedocs.skill.styles import (
    DEFAULT_STYLE,
    all_styles,
    builtin_style_content,
    copy_style_to_project,
    load_project_style,
    style_label,
)


class TestStyleRegistry:
    def test_all_styles_has_three(self) -> None:
        styles = all_styles()
        assert set(styles) == {"narrative", "reference", "tutorial"}

    def test_default_style_is_narrative(self) -> None:
        assert DEFAULT_STYLE == "narrative"

    def test_style_label_pt_br(self) -> None:
        label = style_label("narrative", "pt-BR")
        assert "Narrativo" in label or "narrativo" in label.lower()

    def test_style_label_en(self) -> None:
        label = style_label("reference", "en")
        assert "reference" in label.lower()


class TestBuiltinContent:
    def test_each_style_has_content(self) -> None:
        for s in all_styles():
            content = builtin_style_content(s)
            assert len(content) > 200, f"{s} is suspiciously short"
            # Each style file is markdown with a top-level heading
            assert content.startswith("# ")


class TestCopyStyleToProject:
    def test_creates_file_when_missing(self, tmp_path: Path) -> None:
        target = tmp_path / ".livedocs" / "style.md"
        copy_style_to_project("narrative", target)
        assert target.exists()
        # File matches the built-in
        assert target.read_text(encoding="utf-8") == builtin_style_content("narrative")

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "deep" / "style.md"
        copy_style_to_project("tutorial", target)
        assert target.exists()

    def test_idempotent_preserves_user_edits(self, tmp_path: Path) -> None:
        """If style.md already exists (user customized), don't overwrite."""
        target = tmp_path / ".livedocs" / "style.md"
        target.parent.mkdir(parents=True)
        target.write_text("# my custom style\n", encoding="utf-8")

        copy_style_to_project("narrative", target)
        # User's content survives
        assert target.read_text(encoding="utf-8") == "# my custom style\n"


class TestLoadProjectStyle:
    def test_uses_repo_style_md_when_present(self, tmp_path: Path) -> None:
        (tmp_path / ".livedocs").mkdir()
        custom = "# custom style for this repo\n\nLorem ipsum etc."
        (tmp_path / ".livedocs" / "style.md").write_text(custom, encoding="utf-8")
        loaded = load_project_style(tmp_path)
        assert loaded == custom

    def test_falls_back_to_narrative_when_missing(self, tmp_path: Path) -> None:
        # No .livedocs/style.md present
        loaded = load_project_style(tmp_path)
        assert loaded == builtin_style_content("narrative")

    def test_falls_back_when_file_unreadable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / ".livedocs" / "style.md"
        target.parent.mkdir()
        target.write_text("ok", encoding="utf-8")

        # Patch read_text only on the specific Path we're testing.
        # Patching globally would also break the fallback path inside load_project_style.
        original_read = Path.read_text

        def _selective_read(self, *args, **kwargs):  # noqa: ARG001
            if self == target:
                raise OSError("simulated unreadable file")
            return original_read(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", _selective_read)
        loaded = load_project_style(tmp_path)
        # Falls back to the built-in default (narrative)
        assert "Narrativo" in loaded or "Narrative" in loaded
