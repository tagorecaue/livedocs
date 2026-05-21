"""Bootstrap phase 4 — Passada 1: rascunhos isolados (drafts).

For each approved capability+article + journey, call Claude once with an
ISOLATED context (no other guides' bodies, only the menu index + this
guide's code anchors + the maintainer's guidance + style). The agent
writes two files per article/journey: `{docs}/{kind}/.../{slug}.md`
(product) and `.tech.md` (tech), and returns a JSON envelope listing
pending questions.

Articles ficam em subpastas dentro da capacidade:
`docs/capacidades/<cap-slug>/<article-slug>.md`. GuideRecord identifica
articles pelo slug composto `<cap-slug>/<article-slug>` para evitar
colisão entre articles homônimos de capabilities diferentes (ex.: vários
"introducao").

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
    Article,
    BootstrapState,
    Capability,
    GuideRecord,
    Journey,
    ScreenshotTodo,
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
    """Two-level menu: each capability lists its articles by slug+title."""
    out: list[dict] = []
    if state.taxonomy is None:
        return out
    for c in state.taxonomy.capabilities:
        out.append({
            "slug": c.slug,
            "title": c.title,
            "kind": "capability",
            "summary": c.summary or "",
            "articles": [
                {"slug": a.slug, "title": a.title, "is_intro": a.is_intro}
                for a in c.articles
            ],
        })
    for j in state.taxonomy.journeys:
        out.append({
            "slug": j.slug,
            "title": j.title,
            "kind": "journey",
            "summary": j.summary or "",
            "articles": [],
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
    capability_title: str | None = None,
    siblings: list[dict] | None = None,
    is_intro: bool = False,
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
        capability_title=capability_title,
        siblings=siblings or [],
        is_intro=is_intro,
    )


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

_SKIP_STATUSES = {"drafted", "stitched", "refined"}


def _iter_targets(state: BootstrapState) -> list[tuple[str, Any, Capability | None]]:
    """Flatten taxonomy into (kind, item, parent_cap_or_None) draft targets."""
    out: list[tuple[str, Any, Capability | None]] = []
    if state.taxonomy is None:
        return out
    for c in state.taxonomy.capabilities:
        for a in c.articles:
            out.append(("capability", a, c))
    for j in state.taxonomy.journeys:
        out.append(("journey", j, None))
    return out


def run_pass1(
    repo_root: Path,
    cfg: ProjectConfig,
    state: BootstrapState,
    on_guide_done: GuideDoneCallback | None = None,
) -> None:
    """Run passada 1 over every article+journey in the approved taxonomy."""
    if state.taxonomy is None:
        return

    style = _read_style(repo_root)
    guidance_text = (state.guidance.text or "").strip()
    menu_index = _build_menu_index(state)
    docs_dir = cfg.docs_dir.strip("/") or "docs"

    targets = _iter_targets(state)

    agent = ClaudeAgent(repo_root=repo_root, lang=cfg.lang)
    allowed_tools = ["Read", "Glob", "Grep", "Write"]

    for kind, item, parent in targets:
        if kind == "capability":
            assert isinstance(item, Article) and isinstance(parent, Capability)
            record_slug = f"{parent.slug}/{item.slug}"
            rel_dir = parent.slug
            file_name = item.slug
            capability_title = parent.title
            siblings = [
                {"slug": s.slug, "title": s.title}
                for s in parent.articles
                if s.slug != item.slug
            ]
            is_intro = bool(item.is_intro)
        else:
            assert isinstance(item, Journey)
            record_slug = item.slug
            rel_dir = ""
            file_name = item.slug
            capability_title = None
            siblings = []
            is_intro = False

        rec = _get_or_create_record(state, record_slug, kind)
        if rec.status in _SKIP_STATUSES:
            continue

        rec.status = "drafting"
        save_bootstrap_state(repo_root, state)

        kind_subdir = _kind_dir(kind)
        if rel_dir:
            product_rel = f"{docs_dir}/{kind_subdir}/{rel_dir}/{file_name}.md"
            tech_rel = f"{docs_dir}/{kind_subdir}/{rel_dir}/{file_name}.tech.md"
        else:
            product_rel = f"{docs_dir}/{kind_subdir}/{file_name}.md"
            tech_rel = f"{docs_dir}/{kind_subdir}/{file_name}.tech.md"

        code_anchors = list(getattr(item, "code_anchors", []) or [])

        prompt = "# Task: passada-1-draft\n\n" + _render_prompt(
            slug=record_slug,
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
            capability_title=capability_title,
            siblings=siblings,
            is_intro=is_intro,
        )

        try:
            result = agent.call(
                prompt,
                expect_json=True,
                timeout=900,
                allowed_tools=allowed_tools,
            )
        except AgentError as e:
            ui.warn(f"[pass1] {record_slug}: chamada falhou ({e}); marcando pending")
            rec.status = "pending"
            save_bootstrap_state(repo_root, state)
            continue

        if result.is_error or result.json_data is None:
            ui.warn(
                f"[pass1] {record_slug}: agente sem JSON válido"
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
                f"[pass1] {record_slug}: agente alegou {len(files_written)} arquivos "
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
                record_slug,
                q_text,
                provisional_answer=(pq.get("provisional_answer") or "").strip(),
                confidence=confidence,
            )
            rec.pending_question_ids.append(qid)

        # Persist screenshot TODOs (mirror what the agent embedded in the .md).
        shots = data.get("screenshot_todos") or []
        for sh in shots:
            if not isinstance(sh, dict):
                continue
            route = (sh.get("route") or "").strip()
            desc = (sh.get("description") or "").strip()
            if not route:
                continue
            state.screenshot_todos.append(
                ScreenshotTodo(
                    guide_slug=record_slug,
                    guide_path=product_rel,
                    route=route,
                    description=desc,
                )
            )

        rec.status = "drafted"
        rec.draft_cost_usd += float(result.cost_usd or 0.0)
        state.total_cost_usd += float(result.cost_usd or 0.0)
        save_bootstrap_state(repo_root, state)

        if on_guide_done is not None:
            with contextlib.suppress(Exception):  # UI callback must not crash pipeline
                on_guide_done(rec)


__all__ = ["run_pass1"]
