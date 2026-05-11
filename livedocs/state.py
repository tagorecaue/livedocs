"""Config + State persistence (TOML on disk).

Models live in livedocs/models.py — this module is only IO + path helpers
+ schema migrations.

Layout:
  <repo>/.livedocs/config.toml          — project-level config (committable)
  <repo>/.livedocs/state.toml           — interview state (in .gitignore)
  <repo>/<docs_dir>/[<guides_subdir>/]<domain>/<slug>.md  — generated guides
  <repo>/<docs_dir>/[<guides_subdir>/]<domain>/<slug>.tech.md
  <repo>/<docs_dir>/[<guides_subdir>/]<domain>/_meta/<slug>.interview.md

# Migration history

  v1 (livedocs 0.1.x) → v2 (livedocs 0.2.x):
    - status "completed" → "generated" (already handled in v0.1.1)
    - questions[] → facts[] (this module handles the conversion)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import tomli_w

# Re-export models so existing imports `from livedocs.state import …` keep working.
# Listed in __all__ to mark them as intentional re-exports for linters.
from livedocs.models import (  # noqa: F401
    Evaluation,
    Evidence,
    Fact,
    GlobalState,
    InboxItem,
    InterviewState,
    Issue,
    NextRecommendation,
    ProjectConfig,
)

try:
    import tomllib  # py 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


__all__ = [
    # Re-exported models
    "ProjectConfig",
    "GlobalState",
    "InterviewState",
    "Fact",
    "Evidence",
    "Evaluation",
    "Issue",
    "InboxItem",
    "NextRecommendation",
    "QuestionState",
    # Path helpers
    "LIVEDOCS_DIR_NAME",
    "CONFIG_FILE_NAME",
    "STATE_FILE_NAME",
    "find_repo_root",
    "livedocs_dir",
    "config_path",
    "state_path",
    "guides_root",
    # IO
    "load_config",
    "save_config",
    "load_state",
    "save_state",
    "ensure_gitignore_for_state",
]


# ---------------------------------------------------------------------------
# Backward-compat aliases (callers from v0.1 still import QuestionState)
# ---------------------------------------------------------------------------

# Kept ONLY for legacy callers (the migrator below). Internally everything
# operates on Fact[]. Don't add new uses of this.
from pydantic import BaseModel, Field  # noqa: E402


class QuestionState(BaseModel):
    """Legacy schema — present only so state.toml v1 files keep loading.

    Migrated into Fact during _migrate_state_inplace.
    """

    id: str
    block: str = ""
    block_topic: str = ""
    text: str = ""
    answer: str | None = None
    answered_at: str | None = None
    skipped: bool = False
    covered_by: str | None = None


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

LIVEDOCS_DIR_NAME = ".livedocs"
CONFIG_FILE_NAME = "config.toml"
STATE_FILE_NAME = "state.toml"


def find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` looking for a .git directory or .livedocs config."""
    cur = (start or Path.cwd()).resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists() or (parent / LIVEDOCS_DIR_NAME / CONFIG_FILE_NAME).exists():
            return parent
    return None


def livedocs_dir(repo_root: Path) -> Path:
    return repo_root / LIVEDOCS_DIR_NAME


def config_path(repo_root: Path) -> Path:
    return livedocs_dir(repo_root) / CONFIG_FILE_NAME


def state_path(repo_root: Path) -> Path:
    return livedocs_dir(repo_root) / STATE_FILE_NAME


def guides_root(repo_root: Path, cfg: ProjectConfig) -> Path:
    """Compute the absolute path where domain folders live for this project."""
    base = repo_root / cfg.docs_dir
    return base / cfg.guides_subdir if cfg.guides_subdir else base


# ---------------------------------------------------------------------------
# IO — config
# ---------------------------------------------------------------------------

def load_config(repo_root: Path) -> ProjectConfig | None:
    p = config_path(repo_root)
    if not p.exists():
        return None
    with p.open("rb") as f:
        data = tomllib.load(f)
    return ProjectConfig.model_validate(data)


def save_config(repo_root: Path, cfg: ProjectConfig) -> None:
    p = config_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        tomli_w.dump(cfg.model_dump(mode="json", exclude_none=True), f)


# ---------------------------------------------------------------------------
# IO — state
# ---------------------------------------------------------------------------

def load_state(repo_root: Path) -> GlobalState:
    p = state_path(repo_root)
    if not p.exists():
        return GlobalState()
    with p.open("rb") as f:
        data = tomllib.load(f)
    _migrate_state_inplace(data)
    return GlobalState.model_validate(data)


def save_state(repo_root: Path, state: GlobalState) -> None:
    p = state_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Make sure we serialize the current schema version.
    state.schema_version = 2
    with p.open("wb") as f:
        tomli_w.dump(state.model_dump(mode="json", exclude_none=True), f)


def ensure_gitignore_for_state(repo_root: Path) -> None:
    """Make sure <repo>/.livedocs/state.toml is git-ignored.

    We use a localized .gitignore inside .livedocs/ so we don't touch the user's root .gitignore.
    """
    ld = livedocs_dir(repo_root)
    ld.mkdir(parents=True, exist_ok=True)
    gi = ld / ".gitignore"
    contents = "state.toml\n*.bak\nlogs/\n"
    if not gi.exists() or gi.read_text() != contents:
        gi.write_text(contents)


# ---------------------------------------------------------------------------
# Migration v1 → v2
# ---------------------------------------------------------------------------

def _migrate_state_inplace(data: dict) -> None:
    """Light forward migrations for state.toml.

    v0.1.0 → v0.1.1: status "completed" → "generated" (already shipped).
    v0.1.x → v0.2.0: questions[] → facts[] in every interview.

    Idempotent: re-running on an already-migrated state is a no-op.
    """
    schema_version = data.get("schema_version", 1)

    interviews = data.get("interviews") or {}
    for _slug, iv in interviews.items():
        # v0.1.0 → v0.1.1
        if iv.get("status") == "completed":
            iv["status"] = "generated"

        # v0.1.x → v0.2.x: questions → facts
        old_questions = iv.get("questions")
        if old_questions and "facts" not in iv:
            iv["facts"] = _convert_questions_to_facts(old_questions)
            iv.pop("questions", None)

        # Always ensure new fields exist with defaults so model_validate is happy.
        iv.setdefault("facts", [])
        iv.setdefault("source_files", [])
        iv.setdefault("original_intent", "")
        iv.setdefault("evaluations", [])
        iv.setdefault("iteration_count", 0)
        iv.setdefault("confidence_score", 0.0)

    # Top-level new fields
    data.setdefault("inbox", [])
    data["schema_version"] = 2

    # Surface that schema was bumped (caller doesn't need to do anything special;
    # save_state will write the new version next time).
    _ = schema_version  # silence unused


def _convert_questions_to_facts(questions: list[dict]) -> list[dict]:
    """Convert v0.1 questions[] into v0.2 facts[].

    Heuristic mapping (best effort, no data loss):
      - Each question becomes one Fact with kind based on block letter:
          A → terminology    (product meaning)
          B → trigger
          C → invariant
          D → edge_case
          E → flow
          F → flow            (any remaining direction question)
      - id remains the same (A1, A2, B1…) so cross-refs survive.
      - Answered questions become priority=established, status=confirmed.
      - Skipped questions become priority=speculation, status=open.
      - Unanswered/unskipped become priority=needs-confirmation, status=open.
      - The question text becomes the Fact's pending_question.
      - The original answer text is preserved in answer_text.
    """
    block_to_kind = {
        "A": "terminology",
        "B": "trigger",
        "C": "invariant",
        "D": "edge_case",
        "E": "flow",
        "F": "flow",
    }
    out: list[dict] = []
    for i, q in enumerate(questions, start=1):
        qid = q.get("id") or f"F{i}"
        block = (q.get("block") or qid[:1]).upper()
        kind = block_to_kind.get(block, "flow")

        answer = q.get("answer")
        skipped = bool(q.get("skipped"))

        if answer:
            priority = "established"
            status = "confirmed"
            evidence = [
                {
                    "kind": "answer",
                    "ref": f"legacy:{qid}",
                    "note": "migrated from v0.1 questions",
                }
            ]
        elif skipped:
            priority = "speculation"
            status = "open"
            evidence = []
        else:
            priority = "needs-confirmation"
            status = "open"
            evidence = []

        out.append(
            {
                "id": qid,
                "kind": kind,
                "text": (q.get("text") or "").strip() or "(migrated from legacy question without text)",
                "confidence": "high" if answer else "low",
                "priority": priority,
                "status": status,
                "evidence": evidence,
                "derived_from": [],
                "answer_text": answer,
                "resolved_at": q.get("answered_at"),
                "last_touched_at": q.get("answered_at") or datetime.now().isoformat(timespec="seconds"),
                "pending_question": q.get("text") or None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Backward-compat unused field reference (silence linters)
# ---------------------------------------------------------------------------

# pydantic Field is imported above only because QuestionState (legacy) used it.
_ = Field
