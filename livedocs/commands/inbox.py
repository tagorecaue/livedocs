"""`livedocs inbox` — browse and resolve pending agent proposals.

UI behavior:
  - Lists pending items with severity + context
  - For each item: accept / reject / snooze / view details
  - Accept applies the patch (varies by type) and marks resolved
  - Reject just marks rejected (drops the proposal)
  - Snooze keeps it visible but moves to bottom of the list

Item types and their accept behavior:
  - evidence_based_issue: agent edits the affected file applying the patch
  - apply_cross_link:     livedocs appends bullet to target's "Veja também"
  - others (phase 2+):    not implemented in D.3
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.i18n import t
from livedocs.models import GlobalState, InboxItem
from livedocs.state import (
    ProjectConfig,
    guides_root,
    load_config,
    load_state,
    save_state,
)


def run_inbox(repo_root: Path) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1

    state = load_state(repo_root)
    pending = state.pending_inbox()
    if not pending:
        ui.info(t("inbox_empty"))
        return 0

    ui.section(t("inbox_title", n=len(pending)))

    # Simple loop: present items one by one with an action prompt.
    # For Phase D.3 we avoid arrow-key navigation to keep dependencies light;
    # questionary's choice picker is enough.
    for item in pending:
        rc = _present_item(repo_root, cfg, state, item)
        if rc == "quit":
            break

    save_state(repo_root, state)

    remaining = len(state.pending_inbox())
    if remaining:
        ui.blank()
        ui.info(t("inbox_remaining", n=remaining))
    else:
        ui.blank()
        ui.success(t("inbox_cleared"))
    return 0


def _present_item(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    item: InboxItem,
) -> str:
    """Show one item, ask for action. Return 'quit' to exit the loop early."""
    ui.blank()
    ui.console.print(f"[brand]· {item.id}[/brand]  [muted]({item.type})[/muted]")
    ui.console.print(f"  Guia: [bold]{item.guide_slug}[/bold]")
    ui.console.print(f"  Contexto: {item.context}")
    ui.console.print(f"  Ação: {item.proposed_action}")
    if item.patch and len(item.patch) < 200:
        ui.console.print(f"  [muted]Patch:[/muted] {item.patch}")

    action = ui.ask_choice(
        t("inbox_action_q"),
        choices=[
            (t("inbox_accept"), "accept"),
            (t("inbox_reject"), "reject"),
            (t("inbox_snooze"), "snooze"),
            (t("inbox_view"), "view"),
            (t("inbox_quit"), "quit"),
        ],
        default="accept",
    )

    if action is None or action == "quit":
        return "quit"

    now = datetime.now().isoformat(timespec="seconds")

    if action == "view":
        # Just print full details, keep item pending
        ui.console.print("  [muted]Full patch:[/muted]")
        ui.console.print(item.patch or "(no patch)")
        return "stay"

    if action == "reject":
        item.status = "rejected"
        item.resolved_at = now
        ui.info(t("inbox_rejected"))
        return "stay"

    if action == "snooze":
        item.status = "snoozed"
        ui.info(t("inbox_snoozed"))
        return "stay"

    # accept
    ok = _apply_inbox_item(repo_root, cfg, state, item)
    if ok:
        item.status = "accepted"
        item.resolved_at = now
        ui.success(t("inbox_accepted", id=item.id))
    else:
        ui.error(t("inbox_apply_failed", id=item.id))
    return "stay"


def _apply_inbox_item(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    item: InboxItem,
) -> bool:
    if item.type == "apply_cross_link":
        return _apply_cross_link(repo_root, cfg, item)
    if item.type == "evidence_based_issue":
        return _apply_issue_via_agent(repo_root, cfg, state, item)
    ui.warn(f"Type '{item.type}' not yet supported for auto-apply.")
    return False


def _apply_cross_link(repo_root: Path, cfg: ProjectConfig, item: InboxItem) -> bool:
    """Append `item.patch` (a bullet line) to the target file's 'Veja também' section."""
    # Resolve target path. We try multiple conventions.
    full_dir = guides_root(repo_root, cfg)
    candidates = [
        full_dir / f"{item.guide_slug}.md",
        full_dir / f"{item.guide_slug}.tech.md",
    ]
    # Also try domain-organized layout (most common).
    for domain_dir in full_dir.iterdir() if full_dir.exists() else []:
        if not domain_dir.is_dir():
            continue
        candidates.append(domain_dir / f"{item.guide_slug}.md")
        candidates.append(domain_dir / f"{item.guide_slug}.tech.md")

    target = next((c for c in candidates if c.exists()), None)
    if target is None:
        ui.warn(f"Target file not found for {item.guide_slug}.")
        return False

    text = target.read_text(encoding="utf-8")
    bullet = item.patch.strip()
    if not bullet:
        return False
    if not bullet.startswith("-"):
        bullet = f"- {bullet}"

    # Try to find an existing "## Veja também" section; otherwise append one.
    pattern = re.compile(r"(##\s+Veja também\s*\n)", re.IGNORECASE)
    if pattern.search(text):
        # Insert bullet right after the section header (idempotent: skip if same line exists).
        if bullet in text:
            ui.hint("(bullet already present, no-op)")
            return True
        new_text = pattern.sub(lambda m: m.group(1) + bullet + "\n", text, count=1)
    else:
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + "\n## Veja também\n\n" + bullet + "\n"

    target.write_text(new_text, encoding="utf-8")
    return True


def _apply_issue_via_agent(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    item: InboxItem,
) -> bool:
    """Ask the agent to apply the issue's patch to the underlying file."""
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    full_dir = guides_root(repo_root, cfg)
    # We don't know exact file without context heuristics; pass slug + patch.
    prompt = f"""\
# Task: Apply this fix to a guide

Find the guide file for slug `{item.guide_slug}` under `{full_dir.relative_to(repo_root)}`.
Apply this fix and write back the file.

## Issue context

{item.context}

## Patch to apply

{item.patch}

## Output (STRICT JSON)

```json
{{"applied": true}}
```
or
```json
{{"applied": false, "reason": "why"}}
```

Output ONLY the JSON.
"""
    try:
        with ui.spinner(t("inbox_applying")):
            result = agent.call(prompt, expect_json=True, timeout=180)
    except AgentError as e:
        ui.warn(str(e))
        return False

    # cost tracking on the global state is per-interview; inbox actions are
    # cross-cutting so we don't have an interview to charge to. Skip for D.3.

    if result.is_error or not isinstance(result.json_data, dict):
        return False
    return bool(result.json_data.get("applied"))


__all__ = ["run_inbox"]
