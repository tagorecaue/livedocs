"""Persistence for the bootstrap pipeline state.

State file lives at `<repo>/.livedocs/bootstrap.toml` (gitignored). Holds:

  - schema_version + status + last_completed_phase (resume marker)
  - guidance text captured in phase 0
  - scan output paths + commit_sha (the capture point for Plan B)
  - approved taxonomy
  - per-guide records (status, costs, pending question ids)
  - the pending-questions queue

Schema is locked at v1. If a future schema_version comes in we refuse to
load — caller must run a migration. (Issue #9 carried over from v0.1.)

A `.bak` copy of the previous state is written before each save so a
crash during write doesn't leave the file truncated.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

import tomli_w
from pydantic import BaseModel, Field

try:
    import tomllib  # py 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


CURRENT_SCHEMA_VERSION = 1
BOOTSTRAP_FILE_NAME = "bootstrap.toml"
LIVEDOCS_DIR_NAME = ".livedocs"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class GuidanceText(BaseModel):
    """Free-form orientation captured from the maintainer in phase 0."""

    text: str = ""
    captured_at: str = ""  # ISO timestamp; empty if not captured yet


class Scan(BaseModel):
    """Outputs of phase 1 (deterministic, IA-free)."""

    graph_path: str = ""
    routes_path: str = ""
    i18n_path: str = ""
    models_path: str = ""
    scanned_at: str = ""
    commit_sha: str | None = None  # Plan B uses this as the capture point.


class Capability(BaseModel):
    slug: str
    title: str
    summary: str = ""
    code_anchors: list[str] = Field(default_factory=list)


class Journey(BaseModel):
    slug: str
    title: str
    summary: str = ""
    capability_refs: list[str] = Field(default_factory=list)


class Taxonomy(BaseModel):
    capabilities: list[Capability] = Field(default_factory=list)
    journeys: list[Journey] = Field(default_factory=list)
    approved_at: str | None = None


class GuideRecord(BaseModel):
    slug: str
    kind: Literal["capability", "journey"]
    status: Literal["pending", "drafting", "drafted", "stitched", "refined"] = "pending"
    draft_cost_usd: float = 0.0
    stitch_cost_usd: float = 0.0
    pending_question_ids: list[str] = Field(default_factory=list)


class PendingQuestion(BaseModel):
    id: str
    guide_slug: str
    question: str
    provisional_answer: str = ""
    confidence: Literal["high", "low"] = "low"
    status: Literal["open", "answered", "dropped", "merged"] = "open"
    merged_into: str | None = None
    answer: str = ""


BootstrapStatus = Literal[
    "scanning",
    "deriving",
    "seeding",
    "drafting",
    "stitching",
    "refining",
    "updating",
    "done",
]


class BootstrapState(BaseModel):
    """Top-level persistence model. Single source of truth between phases."""

    schema_version: int = CURRENT_SCHEMA_VERSION
    status: BootstrapStatus = "scanning"
    last_completed_phase: int = 0
    created_at: str = ""
    updated_at: str = ""

    guidance: GuidanceText = Field(default_factory=GuidanceText)
    scan: Scan = Field(default_factory=Scan)
    taxonomy: Taxonomy | None = None
    guides: list[GuideRecord] = Field(default_factory=list)
    pending_questions: list[PendingQuestion] = Field(default_factory=list)
    total_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def bootstrap_path(repo_root: Path) -> Path:
    return repo_root / LIVEDOCS_DIR_NAME / BOOTSTRAP_FILE_NAME


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def load_bootstrap_state(repo_root: Path) -> BootstrapState | None:
    """Return the persisted state, or None if no bootstrap has started.

    Raises ValueError with a clear message if the file on disk has a
    schema_version newer than what this build understands.
    """
    p = bootstrap_path(repo_root)
    if not p.exists():
        return None
    with p.open("rb") as f:
        data = tomllib.load(f)
    schema_version = int(data.get("schema_version", CURRENT_SCHEMA_VERSION))
    if schema_version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"bootstrap.toml has schema_version={schema_version}, but this "
            f"livedocs build only understands up to v{CURRENT_SCHEMA_VERSION}. "
            "Upgrade livedocs or use an older bootstrap file."
        )
    return BootstrapState.model_validate(data)


def save_bootstrap_state(repo_root: Path, state: BootstrapState) -> None:
    """Persist state to disk. Writes a .bak of the prior file first."""
    p = bootstrap_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)

    if p.exists():
        # Backup before overwriting — protects against crash mid-write.
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))

    state.schema_version = CURRENT_SCHEMA_VERSION
    state.updated_at = datetime.now().isoformat(timespec="seconds")
    if not state.created_at:
        state.created_at = state.updated_at

    with p.open("wb") as f:
        tomli_w.dump(state.model_dump(mode="json", exclude_none=True), f)
