"""Post-generation evaluator — runs the 3 audit dimensions in parallel.

# What it does

After `generate_guides` writes the v1 paired guides, run 3 independent
Claude calls in parallel, each one auditing the guide from a different
persona/dimension:

  - product_clarity     : reads produto.md as an end-user. Flags jargon, missing
                          narrative, broken cross-refs, paragraph-level issues.
  - tech_completeness   : reads tech.md as a new developer. Flags missing
                          invariants, missing diagrams, missing file:line cites.
  - base_coherence      : reads new guide vs sibling guides + glossary. Flags
                          terminology drift, contradiction, missing cross-links,
                          reverse-link opportunities.

Each evaluator returns an `Evaluation` with `Issue[]`. Issues are classified by
severity:

  - blocker      : contradiction with code or evidence — must fix.
  - evidence-based: detectable problem grounded in something explicit.
  - subjective   : style/tone suggestion, no code anchor.

# Concurrency

Uses `concurrent.futures.ThreadPoolExecutor` — each evaluator is one Claude CLI
subprocess so threads work well (no GIL contention on subprocess.run).

# Where it sits in the flow

```
generate_guides → run_evaluations → (Phase D.2: internal iteration)
                                  → (Phase D.3: surface remaining issues to inbox)
```

This module produces the raw evaluations. The orchestrator in D.2 decides what
to auto-fix vs surface.
"""

from __future__ import annotations

import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from livedocs import ui
from livedocs.agent import AgentError, AgentResult, ClaudeAgent
from livedocs.i18n import t
from livedocs.models import Evaluation, EvaluationDimension, InterviewState, Issue
from livedocs.skill import (
    PROMPT_EVAL_BASE_COHERENCE,
    PROMPT_EVAL_PRODUCT_CLARITY,
    PROMPT_EVAL_TECH_COMPLETENESS,
)
from livedocs.skill.styles import load_project_style
from livedocs.state import GlobalState, ProjectConfig, guides_root

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_evaluations(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    interview: InterviewState,
) -> list[Evaluation]:
    """Run the 3 post-generation evaluations in parallel.

    Returns a list of `Evaluation` objects, one per dimension. Errors in
    individual evaluators are surfaced as warnings; the function does not
    raise. Each evaluation's `issues[]` is populated with whatever the agent
    returned (validated and shaped into `Issue` models).

    Side effects:
      - Appends results to `interview.evaluations`
      - Accumulates cost into the interview

    Caller should `save_state(repo_root, state)` after this returns.
    """
    full_dir_path = guides_root(repo_root, cfg) / interview.domain
    full_dir_rel = full_dir_path.relative_to(repo_root)
    produto_path = str(full_dir_rel / f"{interview.slug}.md")
    tech_path = str(full_dir_rel / f"{interview.slug}.tech.md")
    glossary_path = str(Path(cfg.docs_dir) / "_meta" / "glossary.md")

    related_compact = _build_related_compact(repo_root, cfg, state, interview)

    style_content = load_project_style(repo_root)

    tasks: list[tuple[EvaluationDimension, str]] = [
        (
            "product_clarity",
            _build_prompt(
                PROMPT_EVAL_PRODUCT_CLARITY,
                {"produto_path": produto_path},
                style_content,
            ),
        ),
        (
            "tech_completeness",
            _build_prompt(
                PROMPT_EVAL_TECH_COMPLETENESS,
                {"tech_path": tech_path},
                style_content,
            ),
        ),
        (
            "base_coherence",
            _build_prompt(
                PROMPT_EVAL_BASE_COHERENCE,
                {
                    "produto_path": produto_path,
                    "tech_path": tech_path,
                    "related_guides_compact": related_compact,
                    "glossary_path": glossary_path,
                },
                style_content,
            ),
        ),
    ]

    ui.blank()
    ui.section(t("eval_running"))
    ui.hint(t("eval_running_hint"))

    results: list[Evaluation] = []
    # Each subprocess takes ~30-120s; ThreadPoolExecutor saves wall time.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_run_one, repo_root, cfg, dimension, prompt): dimension
            for dimension, prompt in tasks
        }
        for future in as_completed(futures):
            dimension = futures[future]
            try:
                ev, agent_result = future.result()
            except Exception as e:
                ui.warn(t("eval_dim_failed", dim=_dim_label(dimension), err=str(e)[:200]))
                ev = Evaluation(
                    dimension=dimension,
                    issues=[],
                    summary=f"(failed: {e})",
                )
                results.append(ev)
                interview.evaluations.append(ev)
                continue

            # Cost tracking
            interview.total_cost_usd += float(agent_result.cost_usd or 0.0)
            interview.total_duration_ms += int(agent_result.duration_ms or 0)
            interview.agent_calls += 1

            results.append(ev)
            interview.evaluations.append(ev)

    _render_summary(results)
    return results


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _run_one(
    repo_root: Path,
    cfg: ProjectConfig,
    dimension: EvaluationDimension,
    prompt: str,
) -> tuple[Evaluation, AgentResult]:
    """Run one evaluator call and parse its JSON envelope into an Evaluation."""
    agent = ClaudeAgent(repo_root, lang=cfg.lang)
    result = agent.call(prompt, expect_json=True, timeout=300)

    if result.is_error:
        raise AgentError(result.error_message or "evaluator error")

    issues: list[Issue] = []
    summary = ""
    if isinstance(result.json_data, dict):
        summary = str(result.json_data.get("summary", ""))
        raw_issues = result.json_data.get("issues", []) or []
        for i, raw in enumerate(raw_issues, start=1):
            if not isinstance(raw, dict):
                continue
            issue = _issue_from_raw(raw, dimension, i)
            if issue:
                issues.append(issue)

    return (
        Evaluation(dimension=dimension, issues=issues, summary=summary),
        result,
    )


def _issue_from_raw(raw: dict, dimension: EvaluationDimension, n: int) -> Issue | None:
    severity = raw.get("severity", "subjective")
    if severity not in ("blocker", "evidence-based", "subjective"):
        severity = "subjective"

    message = str(raw.get("message", "")).strip()
    if not message:
        return None

    issue_id = str(raw.get("id") or f"{_dim_short(dimension)}-{n:02d}")

    return Issue(
        id=issue_id,
        severity=severity,
        dimension=dimension,
        message=message,
        location=str(raw.get("location", "")),
        auto_fix_available=bool(raw.get("auto_fix_available", False)),
        patch=str(raw.get("patch", "")),
        applied=False,
    )


def _build_prompt(template: str, fields: dict[str, str], style: str) -> str:
    """Render a prompt template and append the project's style guide."""
    out = template
    for key, value in fields.items():
        out = out.replace("{" + key + "}", str(value))
    return (
        out
        + "\n\n---\n\n# Writing style guide (project-specific)\n\n"
        + "When deciding what is 'good' for this guide, defer to this style. "
        + "Things flagged 'evidence-based' should be detectable regardless of style; "
        + "things flagged 'subjective' must align with the style below.\n\n"
        + style
    )


def _build_related_compact(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    interview: InterviewState,
) -> str:
    """Build a compact list of related guides for the base_coherence evaluator.

    Strategy: list ≤8 sibling guides (same domain first, then other domains),
    annotated with status. The evaluator agent reads them with its own tools
    as needed.
    """
    same_domain: list[str] = []
    other: list[str] = []
    for slug, iv in sorted(state.interviews.items()):
        if slug == interview.slug:
            continue
        line = f"- {slug} ({iv.domain}) [{iv.status}]"
        if iv.domain == interview.domain:
            same_domain.append(line)
        else:
            other.append(line)
    items = same_domain[:5] + other[: max(0, 8 - len(same_domain[:5]))]
    return "\n".join(items) or "(none — this is the first guide in the project)"


def _render_summary(results: list[Evaluation]) -> None:
    ui.blank()
    for ev in results:
        n = len(ev.issues)
        blockers = sum(1 for i in ev.issues if i.severity == "blocker")
        evidence = sum(1 for i in ev.issues if i.severity == "evidence-based")
        subjective = sum(1 for i in ev.issues if i.severity == "subjective")
        label = _dim_label(ev.dimension)
        if n == 0:
            ui.console.print(f"  [ok]✓[/ok] {label}: 0 issues")
        else:
            ui.console.print(
                f"  [warn]·[/warn] {label}: {n} issue(s)  "
                f"[err]{blockers} blocker[/err]  "
                f"[warn]{evidence} evidence-based[/warn]  "
                f"[muted]{subjective} subjective[/muted]"
            )


def _dim_label(dim: EvaluationDimension) -> str:
    return t(f"eval_dim_{dim}", default_=dim.replace("_", " "))


def _dim_short(dim: EvaluationDimension) -> str:
    return {
        "product_clarity": "PC",
        "tech_completeness": "TC",
        "base_coherence": "BC",
        "shape_and_size": "SS",
        "style_consistency": "SC",
    }.get(dim, dim[:2].upper())


__all__ = ["run_evaluations"]


# Sentinel — for forward-compat when D.2 needs more helpers from here
_ = uuid, re, json
