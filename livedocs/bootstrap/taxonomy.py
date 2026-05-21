"""Bootstrap phase 2 — propose taxonomy (capabilities + journeys) via Claude.

Reads the compacted scan signals (routes, i18n, models, optional graph) plus
the maintainer's guidance, renders a Jinja prompt, asks Claude for strict
JSON, validates it into a `Taxonomy`.

This is the single most expensive AI call of the whole pipeline ($0.30–$1).
Phases 4+ rely on the taxonomy as a stable skeleton, so callers are
encouraged to gate this behind phase 3 (interactive review).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Template
from pydantic import ValidationError

from livedocs.agent import AgentError, ClaudeAgent
from livedocs.bootstrap.state import GuidanceText, Scan, Taxonomy

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "taxonomy_propose.md"


# ---------------------------------------------------------------------------
# Signal compaction
# ---------------------------------------------------------------------------

_NAV_KEY_PREFIXES = ("menu.", "nav.", "navigation.", "sidebar.", "routes.", "router.")


def _load_json_or_default(path_str: str, default: Any) -> Any:
    if not path_str:
        return default
    p = Path(path_str)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _compact_routes(routes: list[dict]) -> list[dict]:
    # Trim to 100, keep only path/file/name.
    out = []
    for r in routes[:100]:
        out.append({
            "path": r.get("path", ""),
            "file": r.get("file", ""),
            "name": r.get("name", ""),
        })
    return out


def _compact_i18n(i18n: list[dict]) -> list[dict]:
    if len(i18n) < 50:
        filtered = i18n
    else:
        filtered = [k for k in i18n if any(k.get("key", "").startswith(p) for p in _NAV_KEY_PREFIXES)]
        if not filtered:
            filtered = i18n[:50]
    out = []
    for entry in filtered[:200]:
        out.append({
            "key": entry.get("key", ""),
            "values_by_lang": entry.get("values_by_lang", {}),
        })
    return out


def _compact_models(models: list[dict]) -> list[dict]:
    out = []
    for m in models[:100]:
        out.append({
            "name": m.get("name", ""),
            "kind": m.get("kind", "model"),
            "fields": (m.get("fields") or [])[:5],
        })
    return out


def _summarize_graph(graph: Any) -> str:
    """Best-effort top-level summary. Tolerant to unknown shapes."""
    if not isinstance(graph, dict):
        return ""
    # graphify-ish shape: { "nodes": [...], "edges": [...] }
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        return ""
    clusters: dict[str, int] = {}
    for n in nodes:
        if not isinstance(n, dict):
            continue
        path = n.get("file") or n.get("path") or ""
        if not isinstance(path, str) or "/" not in path:
            continue
        top = path.split("/", 2)[0]
        clusters[top] = clusters.get(top, 0) + 1
    if not clusters:
        return ""
    parts = [f"- {k}: {v} arquivo(s)" for k, v in sorted(clusters.items(), key=lambda x: -x[1])[:15]]
    return "\n".join(parts)


def _render_prompt(
    *,
    guidance_text: str,
    routes: list[dict],
    i18n: list[dict],
    models: list[dict],
    graph_summary: str,
    lang: str,
) -> str:
    template_text = _PROMPT_PATH.read_text(encoding="utf-8")
    template = Template(template_text, autoescape=False, keep_trailing_newline=True)  # noqa: S701 — markdown, not HTML
    return template.render(
        guidance_text=guidance_text,
        routes=routes,
        i18n=i18n,
        models=models,
        graph_summary=graph_summary,
        lang=lang,
    )


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def propose_taxonomy(
    scan: Scan,
    guidance: GuidanceText,
    repo_root: Path,
    lang: str = "pt-BR",
) -> Taxonomy:
    """Phase 2: call Claude with compacted scan signals and parse the result.

    Raises AgentError / ValidationError on failure; the orchestrator decides
    how to surface that to the user.
    """
    routes_raw = _load_json_or_default(scan.routes_path, [])
    i18n_raw = _load_json_or_default(scan.i18n_path, [])
    models_raw = _load_json_or_default(scan.models_path, [])
    graph_raw = _load_json_or_default(scan.graph_path, {})

    routes = _compact_routes(routes_raw if isinstance(routes_raw, list) else [])
    i18n_keys = _compact_i18n(i18n_raw if isinstance(i18n_raw, list) else [])
    models = _compact_models(models_raw if isinstance(models_raw, list) else [])
    graph_summary = _summarize_graph(graph_raw)

    prompt = "# Task: propor-taxonomia\n\n" + _render_prompt(
        guidance_text=(guidance.text or "").strip(),
        routes=routes,
        i18n=i18n_keys,
        models=models,
        graph_summary=graph_summary,
        lang=lang,
    )

    agent = ClaudeAgent(repo_root=repo_root, lang=lang)
    result = agent.call(prompt, expect_json=True, timeout=600)

    if result.is_error or result.json_data is None:
        raise AgentError(
            f"Taxonomy proposal failed: {result.error_message or 'no JSON returned'}"
        )

    try:
        taxonomy = Taxonomy.model_validate(result.json_data)
    except ValidationError as e:
        raise AgentError(f"Taxonomy JSON did not validate: {e}") from e

    return taxonomy


__all__ = ["propose_taxonomy"]
