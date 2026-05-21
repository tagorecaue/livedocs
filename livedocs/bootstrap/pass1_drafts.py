"""Bootstrap phase 4 — Passada 1: rascunhos isolados (drafts).

For each approved capability + journey, call Claude once with an ISOLATED
context (no other guides' bodies, only the menu index + this guide's code
anchors + the maintainer's guidance + style). The agent writes two files
per guide: `{docs}/{kind}/{slug}.md` (product) and `{docs}/{kind}/{slug}.tech.md`
(tech), and returns a JSON envelope listing pending questions.

Failures of a single guide are isolated: the GuideRecord is marked
`pending`, a warning is logged, and the loop continues. State is saved
after each guide so `--resume` is granular at the guide level.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jinja2 import Template

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.bootstrap.pending import add_pending
from livedocs.bootstrap.state import (
    BootstrapState,
    GuideRecord,
    save_bootstrap_state,
)
from livedocs.models import ProjectConfig

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "pass1_draft.md"

GuideDoneCallback = Callable[[GuideRecord], None]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_style(repo_root: Path) -> str:
    style_path = repo_root / ".livedocs" / "style.md"
    if style_path.exists():
        try:
            return style_path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def _kind_dir(kind: str) -> str:
    return "capacidades" if kind == "capability" else "jornadas"


def _build_menu_index(state: BootstrapState) -> list[dict]:
    out: list[dict] = []
    if state.taxonomy is None:
        return out
    for c in state.taxonomy.capabilities:
        out.append({
            "slug": c.slug,
            "title": c.title,
            "kind": "capability",
            "summary": c.summary or "",
        })
    for j in state.taxonomy.journeys:
        out.append({
            "slug": j.slug,
            "title": j.title,
            "kind": "journey",
            "summary": j.summary or "",
        })
    return out


def _get_or_create_record(state: BootstrapState, slug: str, kind: str) -> GuideRecord:
    for g in state.guides:
        if g.slug == slug:
            return g
    rec = GuideRecord(slug=slug, kind=kind, status="pending")  # type: ignore[arg-type]
    state.guides.append(rec)
    return rec


def _render_prompt(
    *,
    slug: str,
    title: str,
    kind: str,
    summary: str,
    code_anchors: list[str],
    guidance_text: str,
    style: str,
    menu_index: list[dict],
    product_path: str,
    tech_path: str,
    lang: str,
) -> str:
    template_text = _PROMPT_PATH.read_text(encoding="utf-8")
    template = Template(template_text, autoescape=False, keep_trailing_newline=True)  # noqa: S701
    return template.render(
        slug=slug,
        title=title,
        kind=kind,
        summary=summary,
        code_anchors=code_anchors,
        guidance_text=guidance_text,
        style=style,
        menu_index=menu_index,
        product_path=product_path,
        tech_path=tech_path,
        lang=lang,
    )


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

_SKIP_STATUSES = {"drafted", "stitched", "refined"}


def run_pass1(
    repo_root: Path,
    cfg: ProjectConfig,
    state: BootstrapState,
    on_guide_done: GuideDoneCallback | None = None,
) -> None:
    """Run passada 1 over every capability+journey in the approved taxonomy."""
    if state.taxonomy is None:
        return

    style = _read_style(repo_root)
    guidance_text = (state.guidance.text or "").strip()
    menu_index = _build_menu_index(state)
    docs_dir = cfg.docs_dir.strip("/") or "docs"

    items: list[tuple[str, Any]] = []
    for c in state.taxonomy.capabilities:
        items.append(("capability", c))
    for j in state.taxonomy.journeys:
        items.append(("journey", j))

    agent = ClaudeAgent(repo_root=repo_root, lang=cfg.lang)
    allowed_tools = ["Read", "Glob", "Grep", "Write"]

    for kind, item in items:
        rec = _get_or_create_record(state, item.slug, kind)
        if rec.status in _SKIP_STATUSES:
            continue

        rec.status = "drafting"
        save_bootstrap_state(repo_root, state)

        kind_subdir = _kind_dir(kind)
        product_rel = f"{docs_dir}/{kind_subdir}/{item.slug}.md"
        tech_rel = f"{docs_dir}/{kind_subdir}/{item.slug}.tech.md"

        code_anchors = list(getattr(item, "code_anchors", []) or [])

        prompt = "# Task: passada-1-draft\n\n" + _render_prompt(
            slug=item.slug,
            title=item.title,
            kind=kind,
            summary=item.summary or "",
            code_anchors=code_anchors,
            guidance_text=guidance_text,
            style=style,
            menu_index=menu_index,
            product_path=product_rel,
            tech_path=tech_rel,
            lang=cfg.lang,
        )

        try:
            result = agent.call(
                prompt,
                expect_json=True,
                timeout=900,
                allowed_tools=allowed_tools,
            )
        except AgentError as e:
            ui.warn(f"[pass1] {item.slug}: chamada falhou ({e}); marcando pending")
            rec.status = "pending"
            save_bootstrap_state(repo_root, state)
            continue

        if result.is_error or result.json_data is None:
            ui.warn(
                f"[pass1] {item.slug}: agente sem JSON válido"
                f" ({result.error_message or 'no JSON'}); marcando pending"
            )
            rec.status = "pending"
            save_bootstrap_state(repo_root, state)
            continue

        data: dict[str, Any] = result.json_data if isinstance(result.json_data, dict) else {}
        files_written = data.get("files_written") or []
        pending_qs = data.get("pending_questions") or []

        # Validate files exist on disk (issue #10).
        missing: list[str] = []
        for rel in files_written:
            abs_path = (repo_root / rel).resolve()
            if not abs_path.exists():
                missing.append(rel)

        if missing or not files_written:
            ui.warn(
                f"[pass1] {item.slug}: agente alegou {len(files_written)} arquivos "
                f"mas {len(missing) or 'nenhum'} no disco (faltando: {missing}); marcando pending"
            )
            rec.status = "pending"
            rec.draft_cost_usd += float(result.cost_usd or 0.0)
            state.total_cost_usd += float(result.cost_usd or 0.0)
            save_bootstrap_state(repo_root, state)
            continue

        # Persist pending questions.
        for pq in pending_qs:
            if not isinstance(pq, dict):
                continue
            q_text = (pq.get("question") or "").strip()
            if not q_text:
                continue
            conf_raw = pq.get("confidence") or "low"
            confidence = "high" if conf_raw == "high" else "low"
            qid = add_pending(
                state,
                item.slug,
                q_text,
                provisional_answer=(pq.get("provisional_answer") or "").strip(),
                confidence=confidence,
            )
            rec.pending_question_ids.append(qid)

        rec.status = "drafted"
        rec.draft_cost_usd += float(result.cost_usd or 0.0)
        state.total_cost_usd += float(result.cost_usd or 0.0)
        save_bootstrap_state(repo_root, state)

        if on_guide_done is not None:
            with contextlib.suppress(Exception):  # UI callback must not crash pipeline
                on_guide_done(rec)


__all__ = ["run_pass1"]
