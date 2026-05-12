"""`livedocs refine` — apply a free-form instruction to an existing guide.

The user gives a natural-language instruction; the agent decides how to
interpret it (rewrite a section, add a use case, re-check code, etc.) and
returns surgical edits as a JSON list of substring replacements. The CLI
validates each edit (unique anchor, file exists) and applies them
transactionally — all or nothing.

# Why structured edits, not Edit/Write tools

  - Allowlist stays restricted (Read/Glob/Grep/Write only — Edit is too
    permissive on --add-dir; see issue #6).
  - Full audit lives in .livedocs/logs/ (old/new visible per change).
  - Local validation catches agent hallucinations (anchor doesn't exist,
    matches multiple times) BEFORE touching disk.
  - Transactional: a single bad change rolls back the whole refine.

# Status semantics

  - `reviewed` → `generated` (refining content invalidates the prior review)
  - `generated` → stays `generated`
  - `in_progress` / `draft` / `stale` → refine is a no-op (errors out;
    those need `new`/`continue`, not `refine`)
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.commands.interview import _render_prompt
from livedocs.detect import has_claude_code
from livedocs.i18n import t
from livedocs.models import InterviewState
from livedocs.skill import PROMPT_REFINE_GUIDE
from livedocs.skill.styles import load_project_style
from livedocs.state import guides_root, load_config, load_state, save_state

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_refine(
    repo_root: Path,
    slug: str | None = None,
    *,
    instruction: str | None = None,
) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1
    if not has_claude_code():
        ui.error(t("err_no_claude"))
        return 1

    state = load_state(repo_root)

    # Pick the guide (CLI arg → last_touched → interactive picker)
    if slug is None:
        slug = _pick_slug(state, cfg)
        if slug is None:
            return 130

    iv = state.interviews.get(slug)
    if iv is None:
        ui.error(t("err_slug_not_found", slug=slug))
        return 1

    if iv.status not in ("reviewed", "generated"):
        ui.error(t("refine_status_blocked", slug=slug, status=iv.status))
        return 1

    # Resolve guide paths + read content
    domain_dir = guides_root(repo_root, cfg) / iv.domain
    produto_path = domain_dir / f"{slug}.md"
    tech_path = domain_dir / f"{slug}.tech.md"

    if not produto_path.exists():
        ui.error(t("refine_file_missing", path=str(produto_path.relative_to(repo_root))))
        return 1

    produto_content = produto_path.read_text(encoding="utf-8")
    tech_content = tech_path.read_text(encoding="utf-8") if tech_path.exists() else ""

    # Ask the user for the instruction (unless passed as arg)
    if not instruction:
        try:
            ui.blank()
            ui.section(t("refine_title", slug=slug))
            ui.hint(t("refine_hint"))
            instruction = ui.ask_text(t("refine_prompt"), multiline=True)
        except ui.NonInteractiveError as e:
            ui.error(str(e))
            return 2

    if not instruction or not instruction.strip():
        ui.warn(t("abort"))
        return 130
    instruction = instruction.strip()

    # Build prompt + call agent
    style_md = load_project_style(repo_root)
    facts_compact = _facts_compact(iv)

    prompt = _render_prompt(
        PROMPT_REFINE_GUIDE,
        slug=slug,
        domain=iv.domain,
        lang=cfg.lang,
        repo_root=str(repo_root),
        style_md=style_md,
        produto_path=str(produto_path.relative_to(repo_root)),
        produto_content=produto_content,
        tech_path=str(tech_path.relative_to(repo_root)) if tech_path.exists() else "(no tech.md)",
        tech_content=tech_content if tech_content else "(no tech.md content)",
        facts_compact=facts_compact,
        user_instruction=instruction,
    )

    agent = ClaudeAgent(repo_root, lang=cfg.lang)
    try:
        with ui.progress_spinner(t("refine_thinking")) as update:
            result = agent.call(prompt, expect_json=True, timeout=300, on_progress=update)
    except AgentError as e:
        ui.error(str(e))
        return 1

    # Track cost on the interview
    iv.total_cost_usd = (iv.total_cost_usd or 0.0) + float(result.cost_usd or 0.0)
    iv.total_duration_ms = (iv.total_duration_ms or 0) + int(result.duration_ms or 0)
    iv.agent_calls = (iv.agent_calls or 0) + 1

    if result.is_error or not isinstance(result.json_data, dict):
        ui.error(t("refine_failed"))
        if result.text:
            ui.hint(result.text[:500])
        save_state(repo_root, state)
        return 1

    data = result.json_data
    summary = str(data.get("summary") or "").strip()
    raw_changes = data.get("changes") or []

    if not isinstance(raw_changes, list) or not raw_changes:
        ui.blank()
        ui.info(t("refine_no_changes"))
        if summary:
            ui.console.print(f"  [muted]{summary}[/muted]")
        save_state(repo_root, state)
        return 0

    # Validate + apply transactionally
    try:
        applied_files = _apply_changes(repo_root, raw_changes)
    except RefineError as e:
        ui.error(str(e))
        save_state(repo_root, state)
        return 1

    # Status flip if needed
    previous_status = iv.status
    if iv.status == "reviewed":
        iv.status = "generated"

    save_state(repo_root, state)

    # Summary
    ui.blank()
    ui.success(t("refine_done", n=len(raw_changes), files=len(applied_files)))
    if summary:
        ui.console.print(f"  [muted]{summary}[/muted]")
    for f in applied_files:
        ui.console.print(f"    [muted]· {f.relative_to(repo_root)}[/muted]")

    if previous_status == "reviewed":
        ui.blank()
        ui.hint(t("refine_status_flipped"))

    # Surface any code checks the agent says it did
    checks = data.get("code_checks_performed")
    if isinstance(checks, list) and checks:
        ui.blank()
        ui.console.print(f"[muted]{t('refine_code_checks')}[/muted]")
        for c in checks:
            if not isinstance(c, dict):
                continue
            what = str(c.get("what", "")).strip()
            where = str(c.get("where", "")).strip()
            outcome = str(c.get("outcome", "")).strip()
            if what:
                line = f"  · {what}"
                if where:
                    line += f"  [muted]{where}[/muted]"
                if outcome:
                    line += f"  [muted]({outcome})[/muted]"
                ui.console.print(line)

    return 0


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

class RefineError(Exception):
    """One of the proposed changes failed validation."""


def _apply_changes(repo_root: Path, raw_changes: list) -> list[Path]:
    """Validate every change, then apply them all. Transactional.

    Strategy:
      - First pass: build a dict[Path -> list[(old, new)]], reading each file once
      - For each change: verify `file` is under the repo, `old` exists exactly once
        in the file's CURRENT content (i.e., before any other change applied)
      - We apply changes one-at-a-time per file in order; a later change can
        match content that previous changes created (intentional — chained edits)
      - On any validation failure → raise RefineError, NO files written
      - On success → write each modified file

    Returns the list of paths that were actually changed.
    """
    # Group by file path so we read each only once at validation time.
    by_file: dict[Path, list[tuple[str, str, str]]] = {}
    for idx, c in enumerate(raw_changes):
        if not isinstance(c, dict):
            raise RefineError(f"Change #{idx + 1}: not an object")
        file_rel = str(c.get("file") or "").strip()
        old = c.get("old")
        new = c.get("new")
        reason = str(c.get("reason") or "").strip()

        if not file_rel:
            raise RefineError(f"Change #{idx + 1}: missing 'file'")
        if not isinstance(old, str) or not old:
            raise RefineError(f"Change #{idx + 1}: missing or empty 'old'")
        if not isinstance(new, str):
            raise RefineError(f"Change #{idx + 1}: missing 'new'")

        # Resolve path safely under repo
        try:
            resolved = (repo_root / file_rel).resolve()
            resolved.relative_to(repo_root.resolve())
        except (ValueError, OSError) as e:
            raise RefineError(f"Change #{idx + 1}: path '{file_rel}' is outside the repo") from e

        if not resolved.exists():
            raise RefineError(f"Change #{idx + 1}: file does not exist: {file_rel}")

        if resolved.name == "_index.md":
            raise RefineError(
                f"Change #{idx + 1}: refusing to refine `_index.md` (the CLI manages it)"
            )

        by_file.setdefault(resolved, []).append((old, new, reason))

    # Compute new contents per file (in-memory), validating each anchor.
    new_contents: dict[Path, str] = {}
    for path, changes in by_file.items():
        text = path.read_text(encoding="utf-8")
        for n, (old, new, _reason) in enumerate(changes, start=1):
            count = text.count(old)
            if count == 0:
                raise RefineError(
                    f"In {path.name}, change #{n}: 'old' anchor not found "
                    f"({old[:60]!r}…)"
                )
            if count > 1:
                raise RefineError(
                    f"In {path.name}, change #{n}: 'old' anchor matches "
                    f"{count} places (must be unique). Widen the anchor."
                )
            text = text.replace(old, new, 1)
        new_contents[path] = text

    # All validated — write atomically (per-file; if a write fails mid-batch
    # the earlier ones stay applied. Acceptable: git makes this recoverable.).
    written: list[Path] = []
    for path, text in new_contents.items():
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def _facts_compact(iv: InterviewState) -> str:
    if not iv.facts:
        return "(no facts on record)"
    lines = []
    for f in iv.facts[:30]:  # cap to avoid bloating prompt
        lines.append(
            f"- **{f.id}** ({f.kind}, {f.status}): {f.text[:140]}"
        )
    return "\n".join(lines)


def _pick_slug(state, cfg) -> str | None:
    """Interactive picker — only show refine-eligible guides (reviewed / generated)."""
    eligible = [
        (s, iv) for s, iv in sorted(state.interviews.items())
        if iv.status in ("reviewed", "generated")
    ]
    if not eligible:
        ui.error(t("refine_no_eligible"))
        return None

    # If exactly one + last_touched matches, use it directly.
    if state.last_touched_slug and any(s == state.last_touched_slug for s, _ in eligible):
        # Still let the user confirm via picker so they don't accidentally refine
        # the wrong one — but pre-select last_touched.
        pass

    choices: list[tuple[str, str]] = [
        (f"{s}  [{iv.domain}]  ({iv.status})", s) for s, iv in eligible
    ]
    choices.append((t("cancel"), "__cancel__"))

    try:
        picked = ui.ask_choice(
            t("refine_pick_guide"),
            choices=choices,
            default=state.last_touched_slug if state.last_touched_slug else None,
        )
    except ui.NonInteractiveError as e:
        ui.error(str(e))
        return None

    if picked is None or picked == "__cancel__":
        return None
    return picked


__all__ = ["run_refine", "RefineError"]
