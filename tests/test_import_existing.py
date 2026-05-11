"""Tests for D.5 — import_existing.

Covers detect_guides_subdir + scan_existing_guides idempotency, front-matter
parsing edge cases, and the full <Client>-style nested layout.
"""

from __future__ import annotations

from pathlib import Path

from livedocs.import_existing import (
    _build_interview_state,
    _is_product_guide,
    _read_front_matter_and_title,
    detect_guides_subdir,
    scan_existing_guides,
)
from livedocs.models import GlobalState, ProjectConfig


# ---------------------------------------------------------------------------
# detect_guides_subdir
# ---------------------------------------------------------------------------

class TestDetectGuidesSubdir:
    def test_returns_empty_when_no_docs(self, tmp_path: Path) -> None:
        assert detect_guides_subdir(tmp_path, "docs") == ""

    def test_returns_empty_when_flat_layout(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "domain1").mkdir()
        (tmp_path / "docs" / "domain1" / "thing.md").write_text("# Thing")
        # No 'guides' subdir — flat layout
        assert detect_guides_subdir(tmp_path, "docs") == ""

    def test_detects_guides_subdir(self, tmp_path: Path) -> None:
        """When `<docs>/guides/<domain>/<slug>.md` exists, return 'guides'."""
        d = tmp_path / "packages" / "docs" / "guides" / "contratos"
        d.mkdir(parents=True)
        (d / "ciclo-de-vida.md").write_text("# Ciclo")
        assert detect_guides_subdir(tmp_path, "packages/docs") == "guides"

    def test_ignores_tech_only_files(self, tmp_path: Path) -> None:
        """Only `.tech.md` files should NOT trigger detection — needs a product guide."""
        d = tmp_path / "docs" / "guides" / "x"
        d.mkdir(parents=True)
        (d / "thing.tech.md").write_text("# tech only")
        assert detect_guides_subdir(tmp_path, "docs") == ""

    def test_ignores_reserved_filenames(self, tmp_path: Path) -> None:
        """`_index.md` and `README.md` alone shouldn't trigger detection."""
        d = tmp_path / "docs" / "guides" / "x"
        d.mkdir(parents=True)
        (d / "_index.md").write_text("# Index")
        (d / "README.md").write_text("# Readme")
        assert detect_guides_subdir(tmp_path, "docs") == ""


# ---------------------------------------------------------------------------
# _is_product_guide
# ---------------------------------------------------------------------------

class TestIsProductGuide:
    def test_plain_md_is_guide(self, tmp_path: Path) -> None:
        p = tmp_path / "checkout.md"
        p.touch()
        assert _is_product_guide(p) is True

    def test_tech_md_is_not(self, tmp_path: Path) -> None:
        p = tmp_path / "checkout.tech.md"
        p.touch()
        assert _is_product_guide(p) is False

    def test_index_is_not(self, tmp_path: Path) -> None:
        p = tmp_path / "_index.md"
        p.touch()
        assert _is_product_guide(p) is False

    def test_readme_is_not(self, tmp_path: Path) -> None:
        for name in ("README.md", "readme.md"):
            assert _is_product_guide(tmp_path / name) is False

    def test_non_md_is_not(self, tmp_path: Path) -> None:
        assert _is_product_guide(tmp_path / "thing.txt") is False


# ---------------------------------------------------------------------------
# _read_front_matter_and_title
# ---------------------------------------------------------------------------

class TestReadFrontMatterAndTitle:
    def test_full_front_matter_and_title(self, tmp_path: Path) -> None:
        p = tmp_path / "g.md"
        p.write_text(
            """---
slug: foo
domain: bar
status: reviewed
source_files:
  - cart.py
  - api.py
last_interview: 2026-05-10
---

# Foo's Title

Body here.
""",
            encoding="utf-8",
        )
        fm, title = _read_front_matter_and_title(p)
        assert fm["slug"] == "foo"
        assert fm["domain"] == "bar"
        assert fm["source_files"] == ["cart.py", "api.py"]
        assert title == "Foo's Title"

    def test_no_front_matter_just_title(self, tmp_path: Path) -> None:
        p = tmp_path / "g.md"
        p.write_text("# Just a Heading\n\nBody.\n", encoding="utf-8")
        fm, title = _read_front_matter_and_title(p)
        assert fm == {}
        assert title == "Just a Heading"

    def test_front_matter_no_title(self, tmp_path: Path) -> None:
        p = tmp_path / "g.md"
        p.write_text(
            """---
slug: foo
---

No heading body.
""",
            encoding="utf-8",
        )
        fm, title = _read_front_matter_and_title(p)
        assert fm["slug"] == "foo"
        assert title == ""

    def test_malformed_yaml_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "g.md"
        p.write_text(
            """---
slug: foo
this: : : : nope
---

# Title
""",
            encoding="utf-8",
        )
        fm, title = _read_front_matter_and_title(p)
        # YAML failed → empty dict but title still extracted from body
        assert fm == {}
        assert title == "Title"

    def test_unreadable_file_returns_empty(self, tmp_path: Path) -> None:
        # Point at a non-existent file
        fm, title = _read_front_matter_and_title(tmp_path / "ghost.md")
        assert fm == {}
        assert title == ""


# ---------------------------------------------------------------------------
# _build_interview_state
# ---------------------------------------------------------------------------

class TestBuildInterviewState:
    def test_minimal_defaults(self) -> None:
        iv = _build_interview_state("foo", "bar", "Foo Title", {})
        assert iv.slug == "foo"
        assert iv.domain == "bar"
        assert iv.title == "Foo Title"
        assert iv.status == "reviewed"
        assert iv.facts == []
        assert iv.original_intent == "(imported from disk)"
        # Default confidence when not in fm: 1.0
        assert iv.confidence_score == 1.0

    def test_title_falls_back_to_slug_when_empty(self) -> None:
        iv = _build_interview_state("my-slug", "d", "", {})
        assert iv.title == "my-slug"

    def test_status_from_front_matter(self) -> None:
        iv = _build_interview_state("s", "d", "T", {"status": "stale"})
        assert iv.status == "stale"

    def test_invalid_status_coerced_to_reviewed(self) -> None:
        iv = _build_interview_state("s", "d", "T", {"status": "bogus"})
        assert iv.status == "reviewed"

    def test_source_files_extracted(self) -> None:
        iv = _build_interview_state("s", "d", "T", {"source_files": ["a.py", "b.py", 42, None]})
        # Non-strings filtered out
        assert iv.source_files == ["a.py", "b.py"]

    def test_quality_score_used_as_confidence(self) -> None:
        iv = _build_interview_state("s", "d", "T", {"quality_score": 0.78})
        assert iv.confidence_score == 0.78

    def test_last_interview_preserved(self) -> None:
        iv = _build_interview_state("s", "d", "T", {"last_interview": "2026-05-10"})
        assert iv.last_touched_at == "2026-05-10"


# ---------------------------------------------------------------------------
# scan_existing_guides — full filesystem walk
# ---------------------------------------------------------------------------

def _write_guide(path: Path, slug: str, domain: str, title: str, **fm_extras) -> None:
    """Helper to drop a well-formed guide on disk."""
    fm_lines = [f"slug: {slug}", f"domain: {domain}", "status: reviewed"]
    for k, v in fm_extras.items():
        fm_lines.append(f"{k}: {v}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + "\n".join(fm_lines) + "\n---\n\n" + f"# {title}\n\nBody.\n",
        encoding="utf-8",
    )


class TestScanExistingGuides:
    def test_scans_<client>_layout(self, tmp_path: Path) -> None:
        """Mimics the actual <Client> layout: packages/docs/guides/<dom>/<slug>.md."""
        cfg = ProjectConfig(
            project_slug="rgz",
            docs_dir="packages/docs",
            guides_subdir="guides",
        )
        guides = tmp_path / "packages" / "docs" / "guides"
        _write_guide(guides / "contratos" / "ciclo-de-vida.md", "ciclo-de-vida", "contratos", "Ciclo")
        _write_guide(guides / "contratos" / "ciclo-de-vida.tech.md", "ciclo-de-vida-tech", "contratos", "Ciclo Tech")
        _write_guide(guides / "financeiro" / "repasses.md", "repasses", "financeiro", "Repasses")
        # _index files should be skipped
        (guides / "contratos" / "_index.md").write_text("# Index")

        state = GlobalState()
        n = scan_existing_guides(tmp_path, cfg, state)
        # Imported: ciclo-de-vida + repasses. Skipped: .tech.md companion + _index.
        assert n == 2
        assert "ciclo-de-vida" in state.interviews
        assert "repasses" in state.interviews
        # Tech companion file should not have produced its own entry
        assert "ciclo-de-vida-tech" not in state.interviews

    def test_flat_layout_without_guides_subdir(self, tmp_path: Path) -> None:
        """docs_dir = 'docs' with no guides/ subdir → scan happens directly under docs/<dom>/."""
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="")
        d = tmp_path / "docs"
        _write_guide(d / "domain1" / "thing.md", "thing", "domain1", "Thing")

        state = GlobalState()
        n = scan_existing_guides(tmp_path, cfg, state)
        assert n == 1
        assert "thing" in state.interviews

    def test_idempotent_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        """Running scan twice doesn't replace existing in-state entries."""
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="")
        d = tmp_path / "docs"
        _write_guide(d / "dom" / "thing.md", "thing", "dom", "Thing")

        state = GlobalState()
        # Mark thing with custom data the user already has
        from livedocs.models import InterviewState
        state.interviews["thing"] = InterviewState(
            slug="thing",
            domain="dom",
            title="Original",
            agent_calls=42,  # this should survive
        )
        n = scan_existing_guides(tmp_path, cfg, state)
        # Already present → not re-imported
        assert n == 0
        # Original entry untouched
        assert state.interviews["thing"].title == "Original"
        assert state.interviews["thing"].agent_calls == 42

    def test_slug_falls_back_to_filename(self, tmp_path: Path) -> None:
        """No slug in front-matter → use file stem."""
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="")
        d = tmp_path / "docs" / "dom"
        d.mkdir(parents=True)
        # Guide with no front-matter slug
        (d / "no-fm-slug.md").write_text("---\ndomain: dom\n---\n\n# Title\n", encoding="utf-8")

        state = GlobalState()
        n = scan_existing_guides(tmp_path, cfg, state)
        assert n == 1
        # Slug came from the filename stem
        assert "no-fm-slug" in state.interviews

    def test_domain_falls_back_to_dirname(self, tmp_path: Path) -> None:
        """No domain in front-matter → use parent directory name."""
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="")
        d = tmp_path / "docs" / "inferred-domain"
        d.mkdir(parents=True)
        (d / "g.md").write_text("---\nslug: g\n---\n\n# T\n", encoding="utf-8")

        state = GlobalState()
        scan_existing_guides(tmp_path, cfg, state)
        assert state.interviews["g"].domain == "inferred-domain"

    def test_meta_dirs_skipped(self, tmp_path: Path) -> None:
        """`_meta`, `.hidden`, etc. shouldn't be scanned as domain dirs."""
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="")
        # `_meta` dir contains things like glossary.md — we don't want them.
        _write_guide(tmp_path / "docs" / "_meta" / "glossary.md", "glossary", "meta", "Glossary")
        # Hidden dirs also skipped
        _write_guide(tmp_path / "docs" / ".hidden" / "secret.md", "secret", "h", "S")
        # Normal one for sanity
        _write_guide(tmp_path / "docs" / "real" / "x.md", "x", "real", "X")

        state = GlobalState()
        n = scan_existing_guides(tmp_path, cfg, state)
        assert n == 1
        assert "x" in state.interviews
        assert "glossary" not in state.interviews
        assert "secret" not in state.interviews

    def test_missing_guides_base_returns_zero(self, tmp_path: Path) -> None:
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="guides")
        state = GlobalState()
        # No docs/ dir at all
        n = scan_existing_guides(tmp_path, cfg, state)
        assert n == 0

    def test_real_<client>_format(self, tmp_path: Path) -> None:
        """Replays the actual <Client> front-matter shape."""
        cfg = ProjectConfig(
            project_slug="rgz",
            docs_dir="packages/docs",
            guides_subdir="guides",
        )
        p = tmp_path / "packages" / "docs" / "guides" / "contratos" / "ciclo-de-vida.md"
        p.parent.mkdir(parents=True)
        p.write_text(
            """---
slug: ciclo-de-vida-do-contrato
domain: contratos
audience: end-user, support, product
flavor: produto
source_files:
  - packages/api/src/billing/contractService.ts
  - packages/db/migrations/000178.sql
related_guides: []
last_interview: 2026-05-08
status: reviewed
---

# Status e situações de um contrato

Aqui começa o guia.
""",
            encoding="utf-8",
        )

        state = GlobalState()
        n = scan_existing_guides(tmp_path, cfg, state)
        assert n == 1
        iv = state.interviews["ciclo-de-vida-do-contrato"]
        assert iv.domain == "contratos"
        assert iv.status == "reviewed"
        assert iv.title == "Status e situações de um contrato"
        assert "packages/api/src/billing/contractService.ts" in iv.source_files
        assert iv.last_touched_at == "2026-05-08"
