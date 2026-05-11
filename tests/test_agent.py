"""Tests for livedocs.agent — extract_json tolerance + audit log writer."""

from __future__ import annotations

import json
from pathlib import Path

from livedocs.agent import (
    _LOG_RETENTION,
    _logs_dir,
    _purpose_from_prompt,
    _write_call_log,
    extract_json,
)

# ---------------------------------------------------------------------------
# extract_json — tolerant JSON extraction
# ---------------------------------------------------------------------------

class TestExtractJsonClean:
    def test_pure_object(self) -> None:
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_pure_array(self) -> None:
        assert extract_json('[1, 2, 3]') == [1, 2, 3]

    def test_with_whitespace(self) -> None:
        assert extract_json('  \n {"x": "y"}  \n') == {"x": "y"}


class TestExtractJsonCodeFence:
    def test_json_fence(self) -> None:
        text = '```json\n{"slug": "foo"}\n```'
        assert extract_json(text) == {"slug": "foo"}

    def test_plain_fence(self) -> None:
        text = '```\n{"slug": "bar"}\n```'
        assert extract_json(text) == {"slug": "bar"}

    def test_fence_with_prose_around(self) -> None:
        text = "Here's the result:\n\n```json\n{\"x\": 42}\n```\n\nDone."
        assert extract_json(text) == {"x": 42}


class TestExtractJsonProseBefore:
    """The exact case that hit Tagôre on pagamento-de-repasses."""

    def test_chatty_prefix(self) -> None:
        text = (
            "I have enough grounding. Producing the JSON skeleton.\n\n"
            '{"title": "X", "facts": []}'
        )
        result = extract_json(text)
        assert result == {"title": "X", "facts": []}

    def test_chatty_suffix(self) -> None:
        text = '{"slug": "a"}\n\nLet me know if you want refinements.'
        assert extract_json(text) == {"slug": "a"}

    def test_chatty_both_sides(self) -> None:
        text = (
            "Sure! Here it is:\n\n"
            '{"slug": "b", "domain": "c"}\n\n'
            "Hope this helps."
        )
        assert extract_json(text) == {"slug": "b", "domain": "c"}

    def test_array_with_prose(self) -> None:
        text = "Items: [1, 2, 3] — that's all."
        assert extract_json(text) == [1, 2, 3]


class TestExtractJsonFailureModes:
    def test_empty_returns_none(self) -> None:
        assert extract_json("") is None
        assert extract_json("   \n  ") is None

    def test_no_json_returns_none(self) -> None:
        assert extract_json("Just regular prose, no JSON anywhere.") is None

    def test_malformed_returns_none(self) -> None:
        # Looks like JSON but is broken — no recoverable substring
        assert extract_json("{broken: no quotes}") is None

    def test_truncated_json_returns_none(self) -> None:
        # The famous pagamento-de-repasses cut: opens but never closes
        truncated = (
            '{"title": "X", "source_files": ['
            '"a.ts", "b.ts", "packages/web/src/pages/Finance/ExpensesC'
        )
        assert extract_json(truncated) is None


class TestExtractJsonNestedAndEdges:
    def test_nested_objects(self) -> None:
        text = "Result:\n\n" + json.dumps({
            "outer": {"inner": {"deep": [1, {"k": "v"}]}}
        })
        result = extract_json(text)
        assert result["outer"]["inner"]["deep"][1]["k"] == "v"

    def test_braces_inside_strings_handled(self) -> None:
        text = '{"template": "Hello {name}!"}'
        assert extract_json(text) == {"template": "Hello {name}!"}

    def test_multiple_top_level_picks_outermost(self) -> None:
        # When there are 2 objects, bracket scan grabs first { to last } —
        # which won't parse as valid JSON. Falls back to None.
        # (We deliberately don't try to be clever here.)
        text = '{"a": 1} and then {"b": 2}'
        # The clean parse fails, the bracket scan extracts
        # '{"a": 1} and then {"b": 2}' which isn't valid JSON, returns None.
        assert extract_json(text) is None


# ---------------------------------------------------------------------------
# _purpose_from_prompt — derive log file name from prompt header
# ---------------------------------------------------------------------------

class TestPurposeFromPrompt:
    def test_task_header_extracted(self) -> None:
        prompt = "# Task: Build the fact skeleton for a new guide\n\nMore text..."
        assert _purpose_from_prompt(prompt) == "build-the-fact-skeleton-for-a-new-guide"

    def test_no_task_header_falls_back(self) -> None:
        assert _purpose_from_prompt("Random prompt without header") == "call"

    def test_empty_falls_back(self) -> None:
        assert _purpose_from_prompt("") == "call"

    def test_unicode_chars_stripped(self) -> None:
        prompt = "# Task: Avaliar coerência (português)"
        result = _purpose_from_prompt(prompt)
        # Slugified: lowercase, hyphens-only
        assert "avaliar" in result
        assert " " not in result
        assert "(" not in result

    def test_long_purpose_truncated_to_50(self) -> None:
        prompt = "# Task: " + "x" * 200
        result = _purpose_from_prompt(prompt)
        assert len(result) <= 50


# ---------------------------------------------------------------------------
# _write_call_log — audit log writer
# ---------------------------------------------------------------------------

class TestWriteCallLog:
    def _setup_repo(self, tmp_path: Path) -> Path:
        (tmp_path / ".livedocs").mkdir()
        return tmp_path

    def test_writes_jsonl_file(self, tmp_path: Path) -> None:
        repo = self._setup_repo(tmp_path)
        path = _write_call_log(
            repo,
            purpose="test-call",
            cmd=["claude", "--print", "user prompt here"],
            system_prompt="You are X.",
            user_prompt="Hello!",
            stdout='{"result": "ok", "total_cost_usd": 0.05}',
            stderr="",
            returncode=0,
            elapsed_ms=1234,
            parsed_envelope={"result": "ok"},
            parsed_json={"ok": True},
        )
        assert path is not None
        assert path.exists()
        assert path.parent == _logs_dir(repo)
        assert path.name.endswith("-test-call.jsonl")

        # Each log is a single-line JSONL we can parse
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["purpose"] == "test-call"
        assert data["elapsed_ms"] == 1234
        assert data["returncode"] == 0
        assert data["user_prompt"] == "Hello!"
        assert data["parsed_json"] == {"ok": True}

    def test_records_extra_meta(self, tmp_path: Path) -> None:
        repo = self._setup_repo(tmp_path)
        path = _write_call_log(
            repo,
            purpose="meta-test",
            cmd=["claude"],
            system_prompt="",
            user_prompt="",
            stdout="",
            stderr="",
            returncode=0,
            elapsed_ms=10,
            parsed_envelope=None,
            parsed_json=None,
            extra_meta={"cost_usd": 0.12, "json_parsed": True},
        )
        assert path is not None
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["meta"]["cost_usd"] == 0.12
        assert data["meta"]["json_parsed"] is True

    def test_preserves_accents_in_prompts(self, tmp_path: Path) -> None:
        repo = self._setup_repo(tmp_path)
        path = _write_call_log(
            repo,
            purpose="i18n",
            cmd=["claude"],
            system_prompt="",
            user_prompt="Documentar configurações financeiras com ç e ã",
            stdout="",
            stderr="",
            returncode=0,
            elapsed_ms=0,
            parsed_envelope=None,
            parsed_json=None,
        )
        text = path.read_text(encoding="utf-8")
        # Accented characters preserved verbatim, not \uXXXX-escaped
        assert "configurações" in text
        assert "ç" in text

    def test_log_dir_created_lazily(self, tmp_path: Path) -> None:
        # No .livedocs/logs yet
        path = _write_call_log(
            tmp_path,
            purpose="lazy",
            cmd=["claude"],
            system_prompt="",
            user_prompt="",
            stdout="",
            stderr="",
            returncode=0,
            elapsed_ms=0,
            parsed_envelope=None,
            parsed_json=None,
        )
        assert path is not None
        assert path.parent.is_dir()

    def test_retention_prunes_oldest(self, tmp_path: Path) -> None:
        """When over retention threshold, oldest files get removed."""
        repo = self._setup_repo(tmp_path)
        logs = _logs_dir(repo)
        logs.mkdir(parents=True, exist_ok=True)

        # Fake retention-cap files with stale mtimes — create _LOG_RETENTION + 5
        import os
        for i in range(_LOG_RETENTION + 5):
            f = logs / f"old-{i:04d}.jsonl"
            f.write_text("{}")
            # Make older files have older mtimes
            os.utime(f, (1000.0 + i, 1000.0 + i))

        # Now write a new one — retention should kick in
        _write_call_log(
            repo,
            purpose="new-one",
            cmd=["claude"],
            system_prompt="",
            user_prompt="",
            stdout="",
            stderr="",
            returncode=0,
            elapsed_ms=0,
            parsed_envelope=None,
            parsed_json=None,
        )

        remaining = list(logs.glob("*.jsonl"))
        # Should be at most _LOG_RETENTION files
        assert len(remaining) <= _LOG_RETENTION


# ---------------------------------------------------------------------------
# Logs directory is included in .gitignore
# ---------------------------------------------------------------------------

class TestGitignoreCoversLogs:
    def test_ensure_gitignore_includes_logs_pattern(self, tmp_path: Path) -> None:
        from livedocs.state import ensure_gitignore_for_state

        ensure_gitignore_for_state(tmp_path)
        gi = tmp_path / ".livedocs" / ".gitignore"
        contents = gi.read_text()
        assert "logs/" in contents
