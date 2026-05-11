"""`livedocs approve` follow-up: reverse-cross-link sweep.

After the human approves a guide, ask the agent to propose entries in other
guides' "Veja também" sections so the base becomes bidirectionally navigable.

Each proposal goes to the inbox as type `apply_cross_link`. The human reviews
via `livedocs inbox`.
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.i18n import t
from livedocs.inbox import push_cross_link_proposal
from livedocs.models import GlobalState, InterviewState, ProjectConfig
from livedocs.skill import PROMPT_REVERSE_LINK_SWEEP
from livedocs.state import guides_root


def run_reverse_link_sweep(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    interview: InterviewState,
) -> int:
    """Run reverse-link sweep against the freshly approved guide. Returns count pushed."""
    full_dir = (guides_root(repo_root, cfg) / interview.domain).relative_to(repo_root)
    produto_path = str(full_dir / f"{interview.slug}.md")
    tech_path = str(full_dir / f"{interview.slug}.tech.md")

    agent = ClaudeAgent(repo_root, lang=cfg.lang)
    prompt = (
        PROMPT_REVERSE_LINK_SWEEP
        .replace("{slug}", interview.slug)
        .replace("{domain}", interview.domain)
        .replace("{produto_path}", produto_path)
        .replace("{tech_path}", tech_path)
    )

    try:
        with ui.spinner(t("reverse_link_sweeping")):
            result = agent.call(prompt, expect_json=True, timeout=240)
    except AgentError as e:
        ui.warn(f"Reverse-link sweep failed: {e}")
        return 0

    # Cost tracking
    interview.total_cost_usd += float(result.cost_usd or 0.0)
    interview.total_duration_ms += int(result.duration_ms or 0)
    interview.agent_calls += 1

    if result.is_error or not isinstance(result.json_data, dict):
        return 0

    proposals = result.json_data.get("proposals", []) or []
    added = 0
    for raw in proposals:
        if not isinstance(raw, dict):
            continue
        target_slug = str(raw.get("target_slug", "")).strip()
        target_path = str(raw.get("target_path", "")).strip()
        bullet = str(raw.get("bullet", "")).strip()
        if not target_slug or not bullet:
            continue
        push_cross_link_proposal(
            state,
            target_slug=target_slug,
            target_path=target_path,
            source_slug=interview.slug,
            bullet=bullet,
        )
        added += 1
    return added


__all__ = ["run_reverse_link_sweep"]
