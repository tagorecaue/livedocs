"""Import existing markdown guides into livedocs state (D.5).

When `livedocs init` detects an existing `<docs_dir>` with markdown guides,
this module scans them and registers them in `state.toml` so they show up in
`livedocs status` and the menu suggestions.

# What gets imported

Per guide pair (`<slug>.md` + optional `<slug>.tech.md`):
  - slug (from front-matter; falls back to filename stem)
  - domain (from front-matter; falls back to parent directory name)
  - title (from the first `# Heading` line; falls back to slug)
  - status (from front-matter; defaults to "reviewed" — humans wrote them)
  - source_files (from front-matter)
  - last_interview (from front-matter)

# What does NOT get imported (intentionally)

  - The `<slug>.interview.md` Q&A record is left on disk as historical
    artifact. We do NOT try to parse it back into Fact[] (the format is
    designed for humans, not round-tripping; v0.5 may add a re-parse command).
  - `_index.md` files are read for next-recommendation hints but NOT turned
    into interview state (they're nav metadata).
  - `_meta/glossary.md` is ignored (it's project-wide, not per-guide).
  - `articles/` and other non-canonical directories are ignored.

# Idempotency

Re-running `scan_existing_guides` on a project that's already imported is
a no-op: existing entries are detected by slug and skipped (rather than
overwritten — preserves any cost tracking, facts that were added by other
runs, etc).

# Detection heuristic for guides_subdir

If the user's docs_dir already follows the <Client> layout
(`packages/docs/guides/<domain>/<slug>.md`), set `guides_subdir = "guides"`
automatically. Otherwise leave it as empty (flat layout under docs_dir).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import yaml

from livedocs.models import InterviewState, ProjectConfig

# Files that look like a guide but aren't (meta/nav/glossary).
_RESERVED_STEMS = frozenset({"_index", "README", "readme", "index"})

# Front-matter line scanner — we don't depend on python-frontmatter, just regex + yaml.
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_guides_subdir(repo_root: Path, docs_dir: str) -> str:
    """Detect whether the project follows the `<docs_dir>/guides/<domain>/...` layout.

    Returns `"guides"` if there's at least one `<docs_dir>/guides/<dir>/<file>.md`,
    otherwise empty string (flat layout under docs_dir).
    """
    base = repo_root / docs_dir / "guides"
    if not base.is_dir():
        return ""
    # Look for any nested .md under guides/ → strong signal
    for child in base.iterdir():
        if not child.is_dir():
            continue
        for md in child.glob("*.md"):
            if md.stem.lower() in _RESERVED_STEMS:
                continue
            if not md.stem.endswith(".tech"):
                return "guides"
    return ""


def scan_existing_guides(
    repo_root: Path,
    cfg: ProjectConfig,
    state,  # GlobalState — avoids circular type import
) -> int:
    """Walk `<docs_dir>/<guides_subdir>/<domain>/*.md` and register guides in state.

    Returns the count of NEW guides imported (existing slugs are skipped).
    Mutates `state` in place; caller is responsible for `save_state`.
    """
    guides_base = _guides_base(repo_root, cfg)
    if not guides_base.is_dir():
        return 0

    imported = 0
    for domain_dir in sorted(guides_base.iterdir()):
        if not domain_dir.is_dir():
            continue
        if domain_dir.name.startswith("_") or domain_dir.name.startswith("."):
            continue  # skip _meta, _index dirs etc.

        for md_path in sorted(domain_dir.glob("*.md")):
            if not _is_product_guide(md_path):
                continue

            fm, title = _read_front_matter_and_title(md_path)

            slug = (fm.get("slug") if isinstance(fm.get("slug"), str) else None) or md_path.stem
            domain = (
                fm.get("domain") if isinstance(fm.get("domain"), str) else None
            ) or domain_dir.name

            if slug in state.interviews:
                # Idempotent: don't overwrite existing entries.
                continue

            iv = _build_interview_state(slug, domain, title, fm)
            state.interviews[slug] = iv
            imported += 1

        # Phase D.6 — pull "next recommendation" out of any existing _index.md
        # so the menu can surface it. Best-effort: silently ignore parse failures.
        _import_next_recommendation_from_index(domain_dir, state)

    return imported


def _import_next_recommendation_from_index(domain_dir: Path, state) -> None:
    """If `<domain_dir>/_index.md` contains a Próxima recomendação section,
    register it in state.next_recommendations. Idempotent."""
    from livedocs.index_md import parse_next_recommendation
    from livedocs.models import NextRecommendation

    index_path = domain_dir / "_index.md"
    parsed = parse_next_recommendation(index_path)
    if not parsed:
        return

    slug = str(parsed.get("slug") or "").strip()
    if not slug:
        return

    # Skip duplicates (same slug already tracked).
    if any(r.slug == slug for r in state.next_recommendations):
        return

    state.next_recommendations.append(
        NextRecommendation(
            slug=slug,
            domain=domain_dir.name,
            reason=str(parsed.get("reason") or "").strip(),
            suggested_by="(imported from _index.md)",
        )
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _guides_base(repo_root: Path, cfg: ProjectConfig) -> Path:
    base = repo_root / cfg.docs_dir
    return base / cfg.guides_subdir if cfg.guides_subdir else base


def _is_product_guide(path: Path) -> bool:
    """A 'product guide' is `<slug>.md` (not `.tech.md`, not `_index.md`)."""
    if path.suffix != ".md":
        return False
    if path.stem.endswith(".tech"):
        return False
    return path.stem.lower() not in _RESERVED_STEMS


def _read_front_matter_and_title(path: Path) -> tuple[dict, str]:
    """Parse YAML front-matter and grab the first `# Heading`. Best-effort.

    Returns (front_matter_dict, title_str). Empty dict / empty string on failure
    — never raises (we want import to keep going across messy files).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, ""

    fm: dict = {}
    body = text
    m = _FRONT_MATTER_RE.match(text)
    if m:
        try:
            parsed = yaml.safe_load(m.group(1))
            if isinstance(parsed, dict):
                fm = parsed
        except yaml.YAMLError:
            fm = {}
        body = text[m.end():]

    title_match = _TITLE_RE.search(body)
    title = title_match.group(1).strip() if title_match else ""
    return fm, title


def _build_interview_state(
    slug: str,
    domain: str,
    title: str,
    fm: dict,
) -> InterviewState:
    """Create an InterviewState entry for an imported guide.

    Status defaults to "reviewed" because: humans wrote these by hand or
    through prior livedocs runs that they already approved. If front-matter
    explicitly says otherwise we honor it.

    facts[] is left empty: the .interview.md companion file isn't parsed
    back into structured Fact records (see module docstring rationale).
    """
    status = fm.get("status", "reviewed")
    if status not in ("draft", "in_progress", "generated", "reviewed", "stale"):
        status = "reviewed"

    source_files: list[str] = []
    raw_sf = fm.get("source_files")
    if isinstance(raw_sf, list):
        source_files = [str(s) for s in raw_sf if isinstance(s, str)]

    last_interview = fm.get("last_interview")
    if isinstance(last_interview, (datetime, date)):
        last_touched_at = last_interview.isoformat()
    elif isinstance(last_interview, str) and last_interview:
        last_touched_at = last_interview
    else:
        last_touched_at = _today_iso()

    confidence = 1.0  # human-reviewed = fully confident by default
    if isinstance(fm.get("quality_score"), (int, float)):
        confidence = float(fm["quality_score"])

    return InterviewState(
        slug=slug,
        domain=domain,
        title=title or slug,
        status=status,
        facts=[],
        source_files=source_files,
        original_intent="(imported from disk)",
        confidence_score=confidence,
        notes="",
        last_touched_at=last_touched_at,
    )


def _today_iso() -> str:
    return datetime.now().date().isoformat()


__all__ = [
    "detect_guides_subdir",
    "scan_existing_guides",
]
