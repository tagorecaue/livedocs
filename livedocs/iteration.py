"""Iteration loop — apply auto-fixes and rerun evals until convergence.

After `generate_guides` produces v1 and `run_evaluations` audits it, this
module iterates:

  1. Apply auto-fixable issues (severity = subjective OR evidence-based with
     a viable `patch`) directly to the .md files.
  2. Re-run the same evaluators.
  3. If no new auto-fixes were applied OR we hit the max ciclos cap → stop.

Issues that survive iteration (blockers + evidence-based without patch) are
NOT silently dropped — they go to the inbox so the human decides.

# Why ciclos cap?

3 was chosen because:
  - Tokens are not the constraint (Tagôre's call), but UX is: too many
    cycles = the user stares at spinners forever.
  - In practice, after 3 cycles either we converge or we hit issues the agent
    can't auto-fix anyway.
  - Keeps total per-guide cost bounded (~$1-2 worst case).

# Auto-fix strategy

The auto-fix is intentionally simple in Phase D: we ask the agent to apply
its own proposed `patch` via its Write tool. We do NOT do textual surgery
in Python — too error-prone. The agent reads the file, applies the patch
(usually a one-line replacement or paragraph rewrite), and writes back.

Each cycle gets its own Claude call. Cost is logged.
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.evaluator import run_evaluations
from livedocs.i18n import t
from livedocs.models import Evaluation, InterviewState, Issue
from livedocs.state import GlobalState, ProjectConfig, guides_root

MAX_CYCLES = 3


def iterate_until_clean(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    interview: InterviewState,
    initial_evaluations: list[Evaluation],
) -> list[Issue]:
    """Apply auto-fixes and re-evaluate until convergence (max 3 cycles).

    Returns the list of issues that remain unresolved after iteration.
    These will be surfaced to the human via the inbox.
    """
    current_evals = initial_evaluations
    cycles_run = 0

    for cycle in range(1, MAX_CYCLES + 1):
        auto_fixable = _select_auto_fixable(current_evals)
        if not auto_fixable:
            break

        ui.blank()
        ui.info(t("iter_cycle", n=cycle, total=MAX_CYCLES, fixes=len(auto_fixable)))

        applied = _apply_fixes(repo_root, cfg, interview, auto_fixable)
        if not applied:
            # Agent could not apply anything — give up to avoid infinite loop
            ui.warn(t("iter_no_progress"))
            break

        # Mark issues as applied so they don't get auto-fixed again
        for issue in applied:
            issue.applied = True

        # Re-evaluate
        current_evals = run_evaluations(repo_root, cfg, state, interview)
        cycles_run = cycle

    if cycles_run > 0:
        ui.success(t("iter_polished", n=cycles_run))

    # Collect surviving issues (anything not applied + non-auto-fixable)
    remaining: list[Issue] = []
    for ev in current_evals:
        for issue in ev.issues:
            if issue.applied:
                continue
            remaining.append(issue)
    return remaining


# ---------------------------------------------------------------------------
# Selection + application
# ---------------------------------------------------------------------------

def _select_auto_fixable(evaluations: list[Evaluation]) -> list[Issue]:
    """Pick issues we can apply automatically this cycle.

    Rules:
      - subjective + auto_fix_available=true + patch present → auto
      - evidence-based + auto_fix_available=true + patch present → auto
      - blocker → NEVER auto. Always goes to inbox.
      - subjective without patch → drop silently (style-only, no fix proposed)
      - evidence-based without patch → goes to inbox (human decides)
    """
    out: list[Issue] = []
    for ev in evaluations:
        for issue in ev.issues:
            if issue.applied:
                continue
            if issue.severity == "blocker":
                continue
            if not issue.auto_fix_available:
                continue
            if not issue.patch.strip():
                continue
            out.append(issue)
    return out


def _apply_fixes(
    repo_root: Path,
    cfg: ProjectConfig,
    interview: InterviewState,
    issues: list[Issue],
) -> list[Issue]:
    """Ask the agent to apply each issue's patch. Returns list actually applied.

    We batch all fixes into one Claude call to keep latency down. The agent
    reads each file, applies its proposed patches, writes back, and returns
    a summary of what was applied.
    """
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    full_dir = (guides_root(repo_root, cfg) / interview.domain).relative_to(repo_root)

    # Group issues by location (path) so the agent reads each file once.
    by_path: dict[str, list[Issue]] = {}
    for issue in issues:
        # Heuristic: location like "path:line" → use the path part.
        # If location is empty, default to produto.md (most evals run there).
        loc = issue.location or f"{full_dir}/{interview.slug}.md"
        path = loc.split(":", 1)[0]
        by_path.setdefault(path, []).append(issue)

    fixes_block = []
    for path, group in by_path.items():
        fixes_block.append(f"## File: `{path}`\n")
        for issue in group:
            fixes_block.append(f"- **{issue.id}** [{issue.severity}]: {issue.message}")
            if issue.location and ":" in issue.location:
                fixes_block.append(f"  - Location: {issue.location}")
            fixes_block.append(f"  - Proposed patch: {issue.patch}")
            fixes_block.append("")

    prompt = f"""\
# Task: Apply small fixes to the generated guides

You previously audited these guides and produced issues with proposed patches.
Now apply them. Read each file, apply each patch, write back.

## Files and proposed patches

{chr(10).join(fixes_block)}

## Rules

- Apply ONLY the proposed patch for each issue. Don't make additional changes.
- Preserve front-matter, section structure, and all other content.
- If a patch is ambiguous, skip it and report in the output.
- Don't add new commentary; the docs stay clean.

## Output (STRICT JSON, no prose, no fences)

```json
{{
  "applied": ["{interview.slug}/I1", "{interview.slug}/I3"],
  "skipped": [{{"id": "I2", "reason": "patch ambiguous"}}]
}}
```

Output ONLY the JSON object.
"""

    try:
        with ui.progress_spinner(t("iter_applying", n=len(issues))) as update:
            result = agent.call(prompt, expect_json=True, timeout=300, on_progress=update)
    except AgentError as e:
        ui.warn(f"Auto-fix call failed: {e}")
        return []

    # Cost
    interview.total_cost_usd += float(result.cost_usd or 0.0)
    interview.total_duration_ms += int(result.duration_ms or 0)
    interview.agent_calls += 1

    if result.is_error or not isinstance(result.json_data, dict):
        return []

    applied_ids = result.json_data.get("applied", []) or []
    applied_set = {str(x).split("/")[-1] for x in applied_ids if isinstance(x, str)}

    applied_issues = [i for i in issues if i.id in applied_set]
    return applied_issues


__all__ = ["iterate_until_clean", "MAX_CYCLES"]
