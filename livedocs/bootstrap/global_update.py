"""Bootstrap phase 7 — Rodada global de ajuste.

For every guide that had at least one pending question answered during
the refinement phase, ask Claude to rewrite the guide incorporating the
fresh answers. Other guides are left untouched.

Each affected guide costs one Claude call (input is small: just the
guide + its Q&As). The agent is restricted to Read/Write so it can't
touch the user's source code.

Resume-safe: a guide whose status is already `refined` is skipped.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jinja2 import Template

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.bootstrap.state import (
    BootstrapState,
    GuideRecord,
    PendingQuestion,
    save_bootstrap_state,
)
from livedocs.models import ProjectConfig

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "global_update.md"

GuideDoneCallback = Callable[[GuideRecord], None]


def _kind_dir(kind: str) -> str:
    return "capacidades" if kind == "capability" else "jornadas"


def _paths_for(repo_root: Path, docs_dir: str, kind: str, slug: str) -> tuple[Path, Path, str, str]:
    sub = _kind_dir(kind)
    product_rel = f"{docs_dir}/{sub}/{slug}.md"
    tech_rel = f"{docs_dir}/{sub}/{slug}.tech.md"
    return (
        repo_root / product_rel,
        repo_root / tech_rel,
        product_rel,
        tech_rel,
    )


def _answered_for_slug(state: BootstrapState, slug: str) -> list[PendingQuestion]:
    return [
        q
        for q in state.pending_questions
        if q.guide_slug == slug and q.status == "answered"
    ]


def _render_prompt(
    *,
    product_path: str,
    tech_path: str,
    product_content: str,
    tech_content: str,
    qas: list[PendingQuestion],
    guidance_text: str,
) -> str:
    template = Template(
        _PROMPT_PATH.read_text(encoding="utf-8"),
        autoescape=False,
        keep_trailing_newline=True,
    )  # noqa: S701
    return template.render(
        product_path=product_path,
        tech_path=tech_path,
        product_content=product_content,
        tech_content=tech_content,
        qas=[
            {
                "id": q.id,
                "confidence": q.confidence,
                "question": q.question,
                "provisional_answer": q.provisional_answer,
                "answer": q.answer,
            }
            for q in qas
        ],
        guidance_text=guidance_text,
    )


def run_global_update(
    repo_root: Path,
    cfg: ProjectConfig,
    state: BootstrapState,
    on_guide_done: GuideDoneCallback | None = None,
) -> None:
    """Phase 7 entry point: rewrite every guide touched by an answered question."""
    docs_dir = cfg.docs_dir.strip("/") or "docs"
    guidance_text = (state.guidance.text or "").strip()

    answered = [q for q in state.pending_questions if q.status == "answered"]
    affected_slugs: list[str] = []
    seen: set[str] = set()
    for q in answered:
        if q.guide_slug and q.guide_slug not in seen:
            affected_slugs.append(q.guide_slug)
            seen.add(q.guide_slug)

    if not affected_slugs:
        ui.info("[global_update] nenhum guia afetado; nada a fazer")
        return

    agent = ClaudeAgent(repo_root=repo_root, lang=cfg.lang)
    allowed_tools = ["Read", "Write"]

    for slug in affected_slugs:
        rec = next((g for g in state.guides if g.slug == slug), None)
        if rec is None:
            ui.warn(f"[global_update] guia '{slug}' não encontrado no estado; pulando")
            continue
        if rec.status == "refined":
            continue

        prod_path, tech_path, product_rel, tech_rel = _paths_for(
            repo_root, docs_dir, rec.kind, rec.slug
        )
        if not prod_path.exists() or not tech_path.exists():
            ui.warn(f"[global_update] {slug}: arquivos faltando; pulando")
            continue

        try:
            product_content = prod_path.read_text(encoding="utf-8")
            tech_content = tech_path.read_text(encoding="utf-8")
        except OSError as e:
            ui.warn(f"[global_update] {slug}: não consegui ler arquivos ({e}); pulando")
            continue

        qas = _answered_for_slug(state, slug)
        if not qas:
            continue

        prompt = "# Task: global-update\n\n" + _render_prompt(
            product_path=product_rel,
            tech_path=tech_rel,
            product_content=product_content,
            tech_content=tech_content,
            qas=qas,
            guidance_text=guidance_text,
        )

        try:
            result = agent.call(
                prompt,
                expect_json=True,
                timeout=600,
                allowed_tools=allowed_tools,
            )
        except AgentError as e:
            ui.warn(f"[global_update] {slug}: chamada falhou ({e}); mantendo status")
            continue

        if result.is_error or not isinstance(result.json_data, dict):
            ui.warn(
                f"[global_update] {slug}: JSON inválido "
                f"({result.error_message or 'no JSON'}); mantendo status"
            )
            continue

        data: dict[str, Any] = result.json_data
        files_modified = data.get("files_modified") or []
        missing = [rel for rel in files_modified if not (repo_root / rel).exists()]
        if missing:
            ui.warn(
                f"[global_update] {slug}: arquivos alegadamente modificados "
                f"faltando: {missing}; mantendo status"
            )
            continue

        rec.status = "refined"
        state.total_cost_usd += float(result.cost_usd or 0.0)
        save_bootstrap_state(repo_root, state)

        if on_guide_done is not None:
            with contextlib.suppress(Exception):
                on_guide_done(rec)


__all__ = ["run_global_update"]
