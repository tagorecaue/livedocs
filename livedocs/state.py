"""Config + State persistence.

Config = stable choices made during init (lang, provider, docs_dir, slug).
State = per-guide progress (interview cursor, answered questions, etc).

Both stored as TOML in plain text — easy for the user to peek/edit.

Layout:
  <repo>/.livedocs/config.toml          — project-level config (committable)
  <repo>/.livedocs/state.toml           — interview state (in .gitignore)
  <repo>/<docs_dir>/<domain>/<slug>.md  — generated guides
  <repo>/<docs_dir>/<domain>/<slug>.tech.md
  <repo>/<docs_dir>/<domain>/_meta/<slug>.interview.md
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

import tomli_w
from pydantic import BaseModel, Field

try:
    import tomllib  # py 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ProjectConfig(BaseModel):
    """Stable per-project config, lives at <repo>/.livedocs/config.toml."""

    schema_version: int = 1
    project_slug: str
    lang: Literal["pt-BR", "en"] = "en"
    provider: str = "claude-code"
    docs_dir: str = "docs"
    """Relative path to the docs directory inside the repo."""

    use_graphify: bool = False
    """Whether the user opted into graphify integration."""

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class QuestionState(BaseModel):
    id: str
    """Stable id like A1, A2, B1, etc."""
    block: str
    """Block letter (A, B, C, …)."""
    block_topic: str = ""
    text: str
    answer: str | None = None
    answered_at: str | None = None
    skipped: bool = False
    covered_by: str | None = None
    """Id of another question whose answer also covers this one."""


class InterviewState(BaseModel):
    slug: str
    domain: str
    title: str = ""
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_touched_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    status: Literal["draft", "in_progress", "generated", "reviewed", "stale"] = "in_progress"
    cursor: int = 0
    """Index of the next question to ask."""
    questions: list[QuestionState] = Field(default_factory=list)
    notes: str = ""

    def remaining(self) -> list[QuestionState]:
        return [q for q in self.questions if q.answer is None and not q.skipped]

    def answered(self) -> list[QuestionState]:
        return [q for q in self.questions if q.answer is not None]


class NextRecommendation(BaseModel):
    """A guide the agent suggested as the natural next step.

    Captured from the JSON envelope returned by `generate_guides` so the
    user sees it in `livedocs` (no args) without having to remember to
    re-read the agent's reply text.
    """

    slug: str
    domain: str
    reason: str = ""
    suggested_by: str
    """Slug of the interview whose generation produced this recommendation."""
    suggested_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class GlobalState(BaseModel):
    """All known interviews + last-touched cursor for the project."""

    schema_version: int = 1
    interviews: dict[str, InterviewState] = Field(default_factory=dict)
    """Keyed by slug."""

    last_touched_slug: str | None = None

    next_recommendations: list[NextRecommendation] = Field(default_factory=list)
    """Pending guide suggestions captured during generate_guides()."""


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


# ---------------------------------------------------------------------------
# IO
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


def load_state(repo_root: Path) -> GlobalState:
    p = state_path(repo_root)
    if not p.exists():
        return GlobalState()
    with p.open("rb") as f:
        data = tomllib.load(f)
    _migrate_state_inplace(data)
    return GlobalState.model_validate(data)


def _migrate_state_inplace(data: dict) -> None:
    """Light forward migrations for state.toml.

    v0.1.0 → v0.1.1: status "completed" was renamed to "generated" (issue #5)
    so we can distinguish between "agent finished writing" and "human reviewed".
    Old state files keep loading instead of crashing on the new Literal.
    """
    interviews = data.get("interviews") or {}
    for iv in interviews.values():
        if iv.get("status") == "completed":
            iv["status"] = "generated"


def save_state(repo_root: Path, state: GlobalState) -> None:
    p = state_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        tomli_w.dump(state.model_dump(mode="json", exclude_none=True), f)


def ensure_gitignore_for_state(repo_root: Path) -> None:
    """Make sure <repo>/.livedocs/state.toml is git-ignored.

    We use a localized .gitignore inside .livedocs/ so we don't touch the user's root .gitignore.
    """
    ld = livedocs_dir(repo_root)
    ld.mkdir(parents=True, exist_ok=True)
    gi = ld / ".gitignore"
    contents = "state.toml\n*.bak\n"
    if not gi.exists() or gi.read_text() != contents:
        gi.write_text(contents)
