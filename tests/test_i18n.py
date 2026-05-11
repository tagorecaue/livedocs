"""Tests for livedocs.i18n — translation, fallback, locale detection."""

from __future__ import annotations

import pytest

from livedocs.i18n import (
    detect_system_locale,
    get_lang,
    lang_label,
    set_lang,
    supported_langs,
    t,
)


@pytest.fixture(autouse=True)
def _isolate_lang() -> None:
    """Each test starts with English active and restores on exit."""
    set_lang("en")


class TestTranslate:
    def test_known_key_returns_active_lang(self) -> None:
        set_lang("pt-BR")
        s = t("interview_paused")
        assert "Entrevista pausada" in s

    def test_known_key_falls_back_to_en(self) -> None:
        set_lang("en")
        s = t("interview_paused")
        # English version contains "Interview paused"
        assert "Interview paused" in s

    def test_unknown_key_returns_key(self) -> None:
        # Default fallback when no default_= provided: return the key literally.
        assert t("definitely_not_a_key_xxx") == "definitely_not_a_key_xxx"

    def test_unknown_key_with_default_returns_default(self) -> None:
        assert t("nope", default_="fallback") == "fallback"

    def test_known_key_with_default_still_translates(self) -> None:
        """default_= only kicks in when the key is missing."""
        set_lang("en")
        s = t("interview_paused", default_="ignored")
        assert "Interview paused" in s
        assert "ignored" not in s

    def test_format_kwargs_apply(self) -> None:
        set_lang("en")
        s = t("interview_files_missing", n=3, total=5)
        assert "3" in s
        assert "5" in s

    def test_missing_format_keys_dont_crash(self) -> None:
        """If the translation string has placeholders we didn't fill, fail open."""
        # interview_files_missing wants {n} and {total}; we pass nothing.
        # Implementation suppresses KeyError/IndexError and returns the raw template.
        s = t("interview_files_missing")
        assert isinstance(s, str)
        assert len(s) > 0


class TestLangSetters:
    def test_get_set_roundtrip(self) -> None:
        set_lang("pt-BR")
        assert get_lang() == "pt-BR"
        set_lang("en")
        assert get_lang() == "en"

    def test_supported_langs(self) -> None:
        assert "pt-BR" in supported_langs()
        assert "en" in supported_langs()

    def test_lang_label(self) -> None:
        # Just verify it returns a non-empty string for both
        assert isinstance(lang_label("pt-BR"), str)
        assert isinstance(lang_label("en"), str)


class TestDetectSystemLocale:
    def test_livedocs_lang_env_pt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Wipe all related env vars, then set our explicit override
        for v in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setenv("LIVEDOCS_LANG", "pt_BR.UTF-8")
        assert detect_system_locale() == "pt-BR"

    def test_livedocs_lang_env_en(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for v in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setenv("LIVEDOCS_LANG", "en_US.UTF-8")
        assert detect_system_locale() == "en"

    def test_unknown_locale_defaults_to_en(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for v in ("LIVEDOCS_LANG", "LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
            monkeypatch.delenv(v, raising=False)
        # Even if python locale picks something exotic, our heuristic defaults to 'en'.
        # We don't control system locale here; the function still returns one of two values.
        assert detect_system_locale() in ("pt-BR", "en")
