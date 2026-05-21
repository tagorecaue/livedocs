"""Persistence for the bootstrap pipeline state.

State file lives at `<repo>/.livedocs/bootstrap.toml` (gitignored). Holds:

  - schema_version + status + last_completed_phase (resume marker)
  - guidance text captured in phase 0
  - scan output paths + commit_sha (the capture point for Plan B)
  - approved taxonomy
  - per-guide records (status, costs, pending question ids)
  - the pending-questions queue

Schema v2 added the `Article` model: a Capability is now a *container*
(equivalente a Categoria do Chatwoot) e cada `Article` é a unidade de
página/artigo. Capacidade tem ≥ 1 artigo. Bumps de schema futuros
seguem o mesmo padrão de migração silenciosa abaixo.

A `.bak` copy of the previous state is written before each save so a
crash during write doesn't leave the file truncated.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import tomli_w
from pydantic import BaseModel, Field

try:
    import tomllib  # py 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


CURRENT_SCHEMA_VERSION = 2
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


class Article(BaseModel):
    """Uma unidade de página/artigo dentro de uma capacidade.

    Mapeia naturalmente em Artigo do Chatwoot. Capacidade vira a
    categoria-contêiner; cada artigo é uma página independente. Slugs
    são únicos *dentro* da capacidade (kebab-case).

    `is_intro=True` marca o artigo introdutório/overview da categoria:
    resume o domínio inteiro e linka os irmãos. No máximo um intro por
    capacidade.
    """

    slug: str
    title: str
    summary: str = ""
    is_intro: bool = False
    code_anchors: list[str] = Field(default_factory=list)


class Capability(BaseModel):
    slug: str
    title: str
    summary: str = ""
    code_anchors: list[str] = Field(default_factory=list)
    articles: list[Article] = Field(default_factory=list)


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


class ScreenshotTodo(BaseModel):
    """A screenshot the agent flagged for human capture during pass1.

    Inserted as `> [!TODO:screenshot]` admonition inside the article markdown
    AND mirrored here for programmatic listing/management. Status flips to
    `captured` once a human attaches the image (future `livedocs screenshots`
    command), or `dropped` if the route is no longer relevant.
    """

    guide_slug: str           # the article that mentions this screen
    guide_path: str           # the .md file path (product, not tech)
    route: str
    description: str
    status: Literal["open", "captured", "dropped"] = "open"


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
    screenshot_todos: list[ScreenshotTodo] = Field(default_factory=list)
    total_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def bootstrap_path(repo_root: Path) -> Path:
    return repo_root / LIVEDOCS_DIR_NAME / BOOTSTRAP_FILE_NAME


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Add a default introdutory Article to every capability.

    Antes do v2 a Capability era diretamente a unidade de página. Agora
    o artigo é a unidade. Toda capability existente sem articles ganha
    um `introducao` com `is_intro=True` derivado do título/summary/anchors
    da própria capability — equivalência funcional 1-pra-1 com o
    comportamento velho.
    """
    tax = data.get("taxonomy")
    if isinstance(tax, dict):
        caps = tax.get("capabilities") or []
        for cap in caps:
            if not isinstance(cap, dict):
                continue
            if not cap.get("articles"):
                cap["articles"] = [
                    {
                        "slug": "introducao",
                        "title": cap.get("title", cap.get("slug", "")),
                        "summary": cap.get("summary", ""),
                        "is_intro": True,
                        "code_anchors": list(cap.get("code_anchors", []) or []),
                    }
                ]
    data["schema_version"] = 2
    return data


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def load_bootstrap_state(repo_root: Path) -> BootstrapState | None:
    """Return the persisted state, or None if no bootstrap has started.

    Raises ValueError with a clear message if the file on disk has a
    schema_version newer than what this build understands.

    v1 → v2 é migrado silenciosamente em memória; só persiste no próximo
    save_bootstrap_state.
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
    if schema_version < 2:
        data = _migrate_v1_to_v2(data)
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
