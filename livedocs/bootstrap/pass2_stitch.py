"""Bootstrap phase 5 — Passada 2: cross-guide stitching.

After passada 1 every drafted guide is internally consistent but isolated:
references to other guides are placeholders like `[TODO:link=slug]` and
terminology may diverge. Passada 2 looks at each drafted guide with a
small "index of others" (title + summary + first paragraph, NOT the body)
and asks Claude to:

  - resolve `[TODO:link=...]` placeholders to real Markdown links;
  - flag contradictions across guides as PendingQuestions;
  - harmonize terminology with minimal rewrite.

Guides with status `pending` are skipped (passada 1 failed); already
`stitched`/`refined` ones are skipped (resume-safe).
"""

from __future__ import annotations

import contextlib
import re
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

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "pass2_stitch.md"
_TODO_RE = re.compile(r"\[TODO:link=([a-zA-Z0-9_\-/.]+)\]")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

GuideDoneCallback = Callable[[GuideRecord], None]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kind_dir(kind: str) -> str:
    return "capacidades" if kind == "capability" else "jornadas"


def _paths_for(repo_root: Path, docs_dir: str, kind: str, slug: str) -> tuple[Path, Path, str, str]:
    sub = _kind_dir(kind)
    product_rel = f"{docs_dir}/{sub}/{slug}.md"
    tech_rel = f"{docs_dir}/{sub}/{slug}.tech.md"
    return (
        (repo_root / product_rel),
        (repo_root / tech_rel),
        product_rel,
        tech_rel,
    )


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    fm_block = m.group(1)
    fm: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, content[m.end():]


def _summarize_for_index(content: str) -> tuple[str, str, str]:
    """Return (title, summary, first_paragraph) from a guide .md."""
    fm, body = _parse_frontmatter(content)
    title = fm.get("title", "")
    summary = fm.get("summary", "")
    # First paragraph: skip leading headers and blank lines.
    paragraph = ""
    for chunk in body.split("\n\n"):
        s = chunk.strip()
        if not s or s.startswith("#"):
            continue
        paragraph = s.replace("\n", " ")
        break
    return title, summary, paragraph[:200]


def _build_index_others(
    repo_root: Path, docs_dir: str, state: BootstrapState, current_slug: str
) -> list[dict]:
    out: list[dict] = []
    drafted_or_better = {"drafted", "stitched", "refined"}
    for g in state.guides:
        if g.slug == current_slug:
            continue
        if g.status not in drafted_or_better:
            continue
        prod_path, _tech_path, _prel, _trel = _paths_for(repo_root, docs_dir, g.kind, g.slug)
        if not prod_path.exists():
            continue
        try:
            content = prod_path.read_text(encoding="utf-8")
        except OSError:
            continue
        title, summary, first_para = _summarize_for_index(content)
        out.append({
            "slug": g.slug,
            "title": title or g.slug,
            "summary": summary or "",
            "first_paragraph": first_para or "",
        })
    return out


def _render_prompt(
    *,
    slug: str,
    kind: str,
    product_path: str,
    tech_path: str,
    product_content: str,
    tech_content: str,
    index_others: list[dict],
    todos: list[str],
) -> str:
    template_text = _PROMPT_PATH.read_text(encoding="utf-8")
    template = Template(template_text, autoescape=False, keep_trailing_newline=True)  # noqa: S701
    return template.render(
        slug=slug,
        kind=kind,
        product_path=product_path,
        tech_path=tech_path,
        product_content=product_content,
        tech_content=tech_content,
        index_others=index_others,
        todos=todos,
    )


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

_SKIP_STATUSES = {"stitched", "refined"}


def run_pass2(
    repo_root: Path,
    cfg: ProjectConfig,
    state: BootstrapState,
    on_guide_done: GuideDoneCallback | None = None,
) -> None:
    """Run passada 2 over every guide currently in status `drafted`."""
    docs_dir = cfg.docs_dir.strip("/") or "docs"
    agent = ClaudeAgent(repo_root=repo_root, lang=cfg.lang)
    allowed_tools = ["Read", "Write"]

    for rec in state.guides:
        if rec.status in _SKIP_STATUSES:
            continue
        if rec.status != "drafted":
            # pending / drafting → skip
            continue

        prod_path, tech_path, product_rel, tech_rel = _paths_for(
            repo_root, docs_dir, rec.kind, rec.slug
        )

        if not prod_path.exists() or not tech_path.exists():
            ui.warn(f"[pass2] {rec.slug}: arquivos do rascunho não estão no disco; pulando")
            continue

        try:
            product_content = prod_path.read_text(encoding="utf-8")
            tech_content = tech_path.read_text(encoding="utf-8")
        except OSError as e:
            ui.warn(f"[pass2] {rec.slug}: não consegui ler arquivos ({e}); pulando")
            continue

        todos = sorted(set(_TODO_RE.findall(product_content) + _TODO_RE.findall(tech_content)))
        index_others = _build_index_others(repo_root, docs_dir, state, rec.slug)

        prompt = "# Task: passada-2-stitch\n\n" + _render_prompt(
            slug=rec.slug,
            kind=rec.kind,
            product_path=product_rel,
            tech_path=tech_rel,
            product_content=product_content,
            tech_content=tech_content,
            index_others=index_others,
            todos=todos,
        )

        try:
            result = agent.call(
                prompt,
                expect_json=True,
                timeout=600,
                allowed_tools=allowed_tools,
            )
        except AgentError as e:
            ui.warn(f"[pass2] {rec.slug}: chamada falhou ({e}); mantendo drafted")
            continue

        if result.is_error or result.json_data is None:
            ui.warn(
                f"[pass2] {rec.slug}: JSON inválido "
                f"({result.error_message or 'no JSON'}); mantendo drafted"
            )
            continue

        data: dict[str, Any] = result.json_data if isinstance(result.json_data, dict) else {}
        files_modified = data.get("files_modified") or []
        missing = [
            rel for rel in files_modified if not (repo_root / rel).resolve().exists()
        ]
        if missing:
            ui.warn(
                f"[pass2] {rec.slug}: agente alegou modificar arquivos faltando: {missing}; "
                "mantendo drafted"
            )
            continue

        # Persist contradictions as low-confidence pending questions.
        for c in data.get("contradictions") or []:
            if not isinstance(c, dict):
                continue
            this_says = (c.get("this_guide_says") or "").strip()
            other = (c.get("other_guide") or "").strip()
            other_says = (c.get("other_says") or "").strip()
            q = (
                f"Contradição detectada: este guia diz \"{this_says}\"; "
                f"o guia `{other}` diz \"{other_says}\". Qual é o correto?"
            )
            qid = add_pending(state, rec.slug, q, provisional_answer="", confidence="low")
            rec.pending_question_ids.append(qid)

        # New pending questions surfaced during stitch.
        for pq in data.get("new_pending_questions") or []:
            if not isinstance(pq, dict):
                continue
            q_text = (pq.get("question") or "").strip()
            if not q_text:
                continue
            conf_raw = pq.get("confidence") or "low"
            confidence = "high" if conf_raw == "high" else "low"
            qid = add_pending(
                state,
                rec.slug,
                q_text,
                provisional_answer=(pq.get("provisional_answer") or "").strip(),
                confidence=confidence,
            )
            rec.pending_question_ids.append(qid)

        rec.status = "stitched"
        rec.stitch_cost_usd += float(result.cost_usd or 0.0)
        state.total_cost_usd += float(result.cost_usd or 0.0)
        save_bootstrap_state(repo_root, state)

        if on_guide_done is not None:
            with contextlib.suppress(Exception):
                on_guide_done(rec)


__all__ = ["run_pass2"]
