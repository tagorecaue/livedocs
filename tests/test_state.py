"""Tests for livedocs.state — IO, paths, migration v1→v2."""

from __future__ import annotations

from pathlib import Path

from livedocs.models import GlobalState, InterviewState, ProjectConfig
from livedocs.state import (
    _migrate_state_inplace,
    config_path,
    ensure_gitignore_for_state,
    find_repo_root,
    guides_root,
    load_config,
    load_state,
    save_config,
    save_state,
    state_path,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

class TestPathHelpers:
    def test_find_repo_root_in_dotgit(self, tmp_path: Path) -> None:
        repo = tmp_path / "r"
        repo.mkdir()
        (repo / ".git").mkdir()
        # Walking up from a nested folder still finds the root
        nested = repo / "a" / "b"
        nested.mkdir(parents=True)
        assert find_repo_root(nested) == repo.resolve()

    def test_find_repo_root_in_livedocs_dir(self, tmp_path: Path) -> None:
        repo = tmp_path / "r"
        repo.mkdir()
        (repo / ".livedocs").mkdir()
        (repo / ".livedocs" / "config.toml").write_text("project_slug='x'\n", encoding="utf-8")
        assert find_repo_root(repo) == repo.resolve()

    def test_find_repo_root_returns_none_in_random_dir(self, tmp_path: Path) -> None:
        # tmp_path is just a folder, no .git, no .livedocs config
        assert find_repo_root(tmp_path) is None

    def test_guides_root_without_subdir(self, tmp_path: Path) -> None:
        cfg = ProjectConfig(project_slug="x", docs_dir="docs")
        assert guides_root(tmp_path, cfg) == tmp_path / "docs"

    def test_guides_root_with_subdir(self, tmp_path: Path) -> None:
        cfg = ProjectConfig(project_slug="x", docs_dir="packages/docs", guides_subdir="guides")
        assert guides_root(tmp_path, cfg) == tmp_path / "packages/docs/guides"


# ---------------------------------------------------------------------------
# Config IO
# ---------------------------------------------------------------------------

class TestConfigIO:
    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        assert load_config(tmp_path) is None

    def test_save_then_load_roundtrip(self, tmp_path: Path) -> None:
        cfg = ProjectConfig(
            project_slug="<client>",
            lang="pt-BR",
            docs_dir="packages/docs",
            guides_subdir="guides",
            style="reference",
            use_graphify=True,
        )
        save_config(tmp_path, cfg)
        # File was created at the expected path
        assert config_path(tmp_path).exists()
        # Round-trip preserves all fields
        loaded = load_config(tmp_path)
        assert loaded is not None
        assert loaded.project_slug == "<client>"
        assert loaded.lang == "pt-BR"
        assert loaded.docs_dir == "packages/docs"
        assert loaded.guides_subdir == "guides"
        assert loaded.style == "reference"
        assert loaded.use_graphify is True


# ---------------------------------------------------------------------------
# State IO
# ---------------------------------------------------------------------------

class TestStateIO:
    def test_load_missing_returns_empty_state(self, tmp_path: Path) -> None:
        st = load_state(tmp_path)
        assert isinstance(st, GlobalState)
        assert st.interviews == {}
        assert st.inbox == []
        # schema_version always >= 2 after _migrate_state_inplace
        assert st.schema_version == 2

    def test_save_then_load_roundtrip(self, tmp_path: Path) -> None:
        st = GlobalState()
        iv = InterviewState(slug="checkout", domain="payments", title="Checkout")
        iv.agent_calls = 5
        iv.total_cost_usd = 1.234
        st.interviews["checkout"] = iv
        st.last_touched_slug = "checkout"
        save_state(tmp_path, st)
        assert state_path(tmp_path).exists()

        loaded = load_state(tmp_path)
        assert "checkout" in loaded.interviews
        assert loaded.interviews["checkout"].agent_calls == 5
        assert loaded.interviews["checkout"].total_cost_usd == 1.234
        assert loaded.last_touched_slug == "checkout"
        assert loaded.schema_version == 2

    def test_save_writes_v2_schema(self, tmp_path: Path) -> None:
        st = GlobalState(schema_version=1)  # try to write a stale version
        save_state(tmp_path, st)
        # The save bumps schema_version to 2 regardless of what we passed in
        loaded = load_state(tmp_path)
        assert loaded.schema_version == 2

    def test_ensure_gitignore_writes_state_toml_pattern(self, tmp_path: Path) -> None:
        ensure_gitignore_for_state(tmp_path)
        gi = tmp_path / ".livedocs" / ".gitignore"
        assert gi.exists()
        contents = gi.read_text()
        assert "state.toml" in contents


# ---------------------------------------------------------------------------
# Migration v1 → v2
# ---------------------------------------------------------------------------

class TestMigration:
    def test_status_completed_becomes_generated(self) -> None:
        """v0.1.0 used 'completed'; v0.1.1+ uses 'generated' before approve."""
        data: dict = {
            "interviews": {
                "x": {
                    "slug": "x",
                    "domain": "d",
                    "status": "completed",
                    "questions": [],
                }
            }
        }
        _migrate_state_inplace(data)
        assert data["interviews"]["x"]["status"] == "generated"

    def test_v1_questions_convert_to_v2_facts(self) -> None:
        data: dict = {
            "interviews": {
                "x": {
                    "slug": "x",
                    "domain": "d",
                    "status": "generated",
                    "questions": [
                        {
                            "id": "A1",
                            "block": "A",
                            "text": "What is X?",
                            "answer": "X is a thing",
                            "answered_at": "2026-01-01T00:00:00",
                            "skipped": False,
                        },
                        {
                            "id": "B1",
                            "block": "B",
                            "text": "How is X triggered?",
                            "answer": None,
                            "skipped": False,
                        },
                        {
                            "id": "C1",
                            "block": "C",
                            "text": "Is X reversible?",
                            "answer": None,
                            "skipped": True,
                        },
                    ],
                }
            }
        }
        _migrate_state_inplace(data)
        iv = data["interviews"]["x"]
        # questions[] is gone, facts[] is there
        assert "questions" not in iv
        facts = iv["facts"]
        assert len(facts) == 3

        # Answered question → established/confirmed with evidence
        f1 = facts[0]
        assert f1["id"] == "A1"
        assert f1["priority"] == "established"
        assert f1["status"] == "confirmed"
        assert f1["answer_text"] == "X is a thing"
        assert f1["confidence"] == "high"
        assert len(f1["evidence"]) == 1
        assert f1["evidence"][0]["kind"] == "answer"
        # block letter A maps to terminology kind
        assert f1["kind"] == "terminology"

        # Unanswered, unskipped → needs-confirmation/open
        f2 = facts[1]
        assert f2["priority"] == "needs-confirmation"
        assert f2["status"] == "open"
        assert f2["answer_text"] is None
        # block B maps to trigger
        assert f2["kind"] == "trigger"

        # Skipped → speculation/open, no evidence
        f3 = facts[2]
        assert f3["priority"] == "speculation"
        assert f3["status"] == "open"
        assert f3["evidence"] == []
        # block C maps to invariant
        assert f3["kind"] == "invariant"

    def test_idempotent_on_v2_state(self) -> None:
        """Running migration twice on v2 state is a no-op."""
        data: dict = {
            "schema_version": 2,
            "interviews": {
                "x": {
                    "slug": "x",
                    "domain": "d",
                    "status": "generated",
                    "facts": [
                        {
                            "id": "F1",
                            "kind": "trigger",
                            "text": "foo",
                            "priority": "established",
                            "status": "confirmed",
                        }
                    ],
                }
            },
        }
        # Re-running migration on an already-v2 state is a no-op.
        _migrate_state_inplace(data)
        # Migration should add default empty lists but not corrupt anything
        assert data["interviews"]["x"]["facts"][0]["id"] == "F1"
        assert data["interviews"]["x"]["facts"][0]["text"] == "foo"
        # schema_version stays/becomes 2
        assert data["schema_version"] == 2

    def test_top_level_defaults_added(self) -> None:
        """Old states without inbox or next_recommendations get defaults."""
        data: dict = {"interviews": {}}
        _migrate_state_inplace(data)
        assert data["inbox"] == []
        assert data["schema_version"] == 2

    def test_unknown_block_letter_defaults_to_flow(self) -> None:
        """v1 questions sometimes had block letters we don't know — fallback to flow."""
        data: dict = {
            "interviews": {
                "x": {
                    "slug": "x",
                    "domain": "d",
                    "status": "generated",
                    "questions": [
                        {
                            "id": "Z1",
                            "block": "Z",
                            "text": "alien block",
                            "answer": "yes",
                        },
                    ],
                }
            }
        }
        _migrate_state_inplace(data)
        f = data["interviews"]["x"]["facts"][0]
        assert f["kind"] == "flow"

    def test_question_with_blank_text_keeps_placeholder(self) -> None:
        """We don't drop questions just because text is empty — a placeholder helps spot bugs."""
        data: dict = {
            "interviews": {
                "x": {
                    "slug": "x",
                    "domain": "d",
                    "status": "generated",
                    "questions": [
                        {"id": "A1", "block": "A", "text": "  ", "answer": None},
                    ],
                }
            }
        }
        _migrate_state_inplace(data)
        f = data["interviews"]["x"]["facts"][0]
        assert "(migrated from legacy" in f["text"]

    def test_real_v1_state_loads_cleanly(self, tmp_path: Path) -> None:
        """End-to-end: write a v1 state.toml, load_state migrates and validates."""
        (tmp_path / ".livedocs").mkdir()
        (tmp_path / ".livedocs" / "state.toml").write_text(
            """schema_version = 1
last_touched_slug = "ciclo-de-vida"

[interviews.ciclo-de-vida]
slug = "ciclo-de-vida"
domain = "contratos"
title = "Ciclo"
status = "completed"
total_cost_usd = 0.5
total_duration_ms = 12000
agent_calls = 8

[[interviews.ciclo-de-vida.questions]]
id = "A1"
block = "A"
text = "O que é um contrato?"
answer = "Vínculo formal..."
answered_at = "2026-01-01T00:00:00"

[[interviews.ciclo-de-vida.questions]]
id = "B1"
block = "B"
text = "Como ativa?"
""",
            encoding="utf-8",
        )

        st = load_state(tmp_path)
        assert st.schema_version == 2
        iv = st.interviews["ciclo-de-vida"]
        # status migrated
        assert iv.status == "generated"
        # costs preserved
        assert iv.total_cost_usd == 0.5
        assert iv.agent_calls == 8
        # facts migrated, count matches questions count
        assert len(iv.facts) == 2
        assert iv.facts[0].priority == "established"
        assert iv.facts[0].status == "confirmed"
        assert iv.facts[1].priority == "needs-confirmation"
        assert iv.facts[1].status == "open"


# ---------------------------------------------------------------------------
# Roundtrip after migration
# ---------------------------------------------------------------------------

class TestRoundtripAfterMigration:
    def test_save_after_migration_persists_v2(self, tmp_path: Path) -> None:
        """Load v1 → save → reload returns the migrated v2 shape."""
        (tmp_path / ".livedocs").mkdir()
        (tmp_path / ".livedocs" / "state.toml").write_text(
            """schema_version = 1

[interviews.x]
slug = "x"
domain = "d"
status = "generated"

[[interviews.x.questions]]
id = "A1"
block = "A"
text = "Q?"
answer = "A"
""",
            encoding="utf-8",
        )
        st = load_state(tmp_path)
        save_state(tmp_path, st)

        # File should now have facts (not questions) and schema_version 2
        reloaded = load_state(tmp_path)
        assert reloaded.schema_version == 2
        assert len(reloaded.interviews["x"].facts) == 1
        # Re-reading raw bytes shouldn't contain "questions ="
        raw = (tmp_path / ".livedocs" / "state.toml").read_text()
        assert "[interviews.x.questions]" not in raw
