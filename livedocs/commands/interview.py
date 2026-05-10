"""Interview orchestrator — drives the question/answer loop.

Each turn:
  1. Show the next pending question
  2. Get user's answer (or skip / pause / open-editor)
  3. Send to agent for coverage check (does this answer also cover others?)
  4. Update state on disk after every answer (so Ctrl-C is safe)
  5. When all questions answered/skipped → trigger generate-guides

State invariants:
  - state.toml is rewritten after every meaningful change
  - We never commit anything; the user owns git ops
  - Skips are NOT failures — they go in the interview record as "skipped"
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.i18n import t
from livedocs.skill import (
    PROMPT_COVERAGE_CHECK,
    PROMPT_GENERATE_GUIDES,
    PROMPT_GENERATE_INTERVIEW,
)
from livedocs.state import (
    GlobalState,
    InterviewState,
    NextRecommendation,
    ProjectConfig,
    QuestionState,
    save_state,
)

SKIP_TOKENS = {"/skip", "/pular", "/pula"}
PAUSE_TOKENS = {"/sair", "/exit", "/quit", "/q"}
EDITOR_TOKENS = {"/editor", "/edit", "/e"}


def _track_cost(interview: InterviewState, result) -> None:
    """Accumulate cost/duration/call-count from an AgentResult into the interview.

    Centralized so cost tracking stays consistent across start_new_interview,
    _check_coverage, generate_guides and any future call site.
    """
    interview.total_cost_usd += float(result.cost_usd or 0.0)
    interview.total_duration_ms += int(result.duration_ms or 0)
    interview.agent_calls += 1


def start_new_interview(
    repo_root: Path,
    cfg: ProjectConfig,
    global_state: GlobalState,
    *,
    slug: str,
    domain: str,
    title: str,
) -> InterviewState | None:
    """Ask the agent to prepare ~20 questions; persist as InterviewState."""
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    ui.blank()
    ui.info(t("interview_starting", slug=slug))

    prompt = PROMPT_GENERATE_INTERVIEW.format(
        repo_root=str(repo_root),
        slug=slug,
        domain=domain,
        title=title or slug,
        lang=cfg.lang,
        docs_dir=cfg.docs_dir,
    )

    try:
        with ui.spinner(t("interview_thinking")):
            result = agent.call(prompt, expect_json=True, timeout=420)
    except AgentError as e:
        ui.error(str(e))
        return None

    if result.is_error or not result.json_data:
        ui.error("Agent did not return valid JSON for the interview prep.")
        if result.text:
            ui.hint(result.text[:500])
        return None

    data = result.json_data
    if not isinstance(data, dict) or "blocks" not in data:
        ui.error("Agent response shape unexpected (missing 'blocks').")
        return None

    questions: list[QuestionState] = []
    for block in data.get("blocks", []):
        block_id = block.get("id", "?")
        block_topic = block.get("topic", "")
        for q in block.get("questions", []):
            questions.append(
                QuestionState(
                    id=q.get("id", f"{block_id}?"),
                    block=block_id,
                    block_topic=block_topic,
                    text=q.get("text", ""),
                )
            )

    interview = InterviewState(
        slug=slug,
        domain=domain,
        title=data.get("title", title or slug),
        questions=questions,
        # Cost from the very first call (interview prep) accounted for here (#3).
        total_cost_usd=float(result.cost_usd or 0.0),
        total_duration_ms=int(result.duration_ms or 0),
        agent_calls=1,
    )
    global_state.interviews[slug] = interview
    global_state.last_touched_slug = slug
    save_state(repo_root, global_state)

    ui.success(f"{len(questions)} {('perguntas preparadas' if cfg.lang == 'pt-BR' else 'questions ready')}")
    return interview


def run_interview_loop(
    repo_root: Path,
    cfg: ProjectConfig,
    global_state: GlobalState,
    interview: InterviewState,
) -> bool:
    """Drive Q&A until all questions are handled or user pauses.

    Returns True if all questions are processed (ready to generate guides),
    False if user paused.
    """
    agent = ClaudeAgent(repo_root, lang=cfg.lang)
    total = len(interview.questions)

    while True:
        # Find the next not-yet-handled question
        pending = [q for q in interview.questions if q.answer is None and not q.skipped]
        if not pending:
            return True

        q = pending[0]
        already_done = total - len(pending)

        # Show context
        ui.blank()
        ui.section(
            t("interview_block", block=q.block, topic=q.block_topic),
            hint=t("interview_question_n", n=already_done + 1, total=total),
        )
        ui.console.print(f"  [bold]{q.id}.[/bold] {q.text}")
        ui.blank()
        ui.hint(t("interview_skip_hint"))

        answer = ui.ask_text(t("interview_answer_q"), multiline=True)
        if answer is None:
            ui.warn(t("interview_paused"))
            interview.last_touched_at = datetime.now().isoformat(timespec="seconds")
            save_state(repo_root, global_state)
            return False

        stripped = answer.strip()

        # User commands
        if stripped.lower() in PAUSE_TOKENS:
            ui.info(t("interview_paused"))
            interview.last_touched_at = datetime.now().isoformat(timespec="seconds")
            save_state(repo_root, global_state)
            return False

        if stripped == "" or stripped.lower() in SKIP_TOKENS:
            q.skipped = True
            q.answered_at = datetime.now().isoformat(timespec="seconds")
            save_state(repo_root, global_state)
            continue

        # Real answer
        q.answer = stripped
        q.answered_at = datetime.now().isoformat(timespec="seconds")
        global_state.last_touched_slug = interview.slug
        interview.last_touched_at = q.answered_at
        save_state(repo_root, global_state)

        # Coverage check — does this answer cover other pending questions?
        other_pending = [other for other in interview.questions
                         if other.answer is None and not other.skipped and other.id != q.id]
        if other_pending:
            try:
                covered_ids = _check_coverage(agent, interview, q, stripped, other_pending)
            except AgentError as e:
                ui.warn(f"Coverage check skipped: {e}")
                covered_ids = []
            if covered_ids:
                _apply_coverage(interview, q, covered_ids, stripped)
                save_state(repo_root, global_state)

    # unreachable
    return True


def _check_coverage(
    agent: ClaudeAgent,
    interview: InterviewState,
    answered: QuestionState,
    answer: str,
    pending: list[QuestionState],
) -> list[str]:
    pending_block = "\n".join(f"- **{q.id}** ({q.block}): {q.text}" for q in pending)
    prompt = PROMPT_COVERAGE_CHECK.format(
        question_id=answered.id,
        question_text=answered.text.replace('"', "'"),
        answer=answer.replace("\n", " ").strip()[:2000],
        pending_block=pending_block,
    )
    with ui.spinner("…"):
        result = agent.call(prompt, expect_json=True, timeout=90)
    _track_cost(interview, result)
    if result.is_error or not result.json_data:
        return []
    data = result.json_data
    if not isinstance(data, dict):
        return []
    raw = data.get("covered", [])
    return [str(x) for x in raw if isinstance(x, str)]


def _apply_coverage(
    interview: InterviewState,
    by: QuestionState,
    covered_ids: list[str],
    answer: str,
) -> None:
    actually_covered = [q for q in interview.questions if q.id in covered_ids and q.answer is None and not q.skipped]
    if not actually_covered:
        return

    labels = ", ".join(q.id for q in actually_covered)
    ui.info(t("interview_covered_others", questions=labels))
    confirm = ui.ask_confirm(t("interview_covered_q"), default=True)
    if not confirm:
        return

    now = datetime.now().isoformat(timespec="seconds")
    for q in actually_covered:
        q.covered_by = by.id
        q.answer = f"(coberta por {by.id}: {answer.strip()[:500]})"
        q.answered_at = now


def generate_guides(
    repo_root: Path,
    cfg: ProjectConfig,
    interview: InterviewState,
    global_state: GlobalState | None = None,
) -> bool:
    """Send the full interview transcript to the agent and ask it to write the guides.

    When `global_state` is provided, agent's `next_recommendation` is persisted into
    `global_state.next_recommendations` for the smart menu to surface later.
    """
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    answers_block_lines = []
    for q in interview.questions:
        answers_block_lines.append(f"### {q.id} ({q.block} — {q.block_topic})")
        answers_block_lines.append(f"**Q:** {q.text}")
        if q.skipped:
            answers_block_lines.append("**A:** _(pulada)_")
        elif q.covered_by:
            answers_block_lines.append(f"**A:** _(coberta por {q.covered_by})_")
        else:
            answers_block_lines.append(f"**A:** {q.answer or '(sem resposta)'}")
        answers_block_lines.append("")

    answers_block = "\n".join(answers_block_lines)

    prompt = PROMPT_GENERATE_GUIDES.format(
        slug=interview.slug,
        domain=interview.domain,
        title=interview.title,
        lang=cfg.lang,
        docs_dir=cfg.docs_dir,
        repo_root=str(repo_root),
        source_files="(see during exploration)",
        answers_block=answers_block,
    )

    ui.blank()
    try:
        with ui.spinner(t("interview_generating")):
            result = agent.call(prompt, expect_json=False, timeout=600)
    except AgentError as e:
        ui.error(str(e))
        return False

    # Track cost even on error so the user sees what they paid for the failed run.
    _track_cost(interview, result)

    if result.is_error:
        ui.error(result.error_message or "Agent error during guide generation.")
        return False

    # Parse the agent's JSON envelope: {files_written, summary, next_recommendation}.
    # If parsing fails (model went off-script), we still record the raw text so
    # the user sees something useful.
    written, summary, next_rec = _parse_generate_envelope(result.text or "")

    # Verify the agent actually wrote what it claimed (issue #10 — guard against
    # silent failure / hallucinated paths). If anything is missing, do NOT mark
    # the interview as 'generated' — keep it 'in_progress' so the user can rerun.
    missing = [f for f in written if not (repo_root / f).exists()]
    if written and missing:
        ui.error(t("interview_files_missing", n=len(missing), total=len(written)))
        for f in missing:
            ui.console.print(f"  [err]✗[/err] {f}")
        ui.hint(t("interview_files_missing_hint"))
        return False

    if not written:
        # Agent did not return a parseable list. Cross-check against expected paths.
        expected = [
            f"{cfg.docs_dir}/{interview.domain}/{interview.slug}.md",
            f"{cfg.docs_dir}/{interview.domain}/{interview.slug}.tech.md",
        ]
        actually_present = [p for p in expected if (repo_root / p).exists()]
        if not actually_present:
            ui.error(t("interview_no_files_written"))
            ui.hint(t("interview_files_missing_hint"))
            return False
        # Recover: agent wrote files but didn't tell us — use the cross-check.
        written = actually_present
        ui.warn(t("interview_files_recovered", n=len(written)))

    interview.status = "generated"

    # Persist next_recommendation in the GlobalState so `livedocs` (no args) can offer it.
    if next_rec is not None and global_state is not None:
        nr = NextRecommendation(
            slug=next_rec.get("slug", "").strip(),
            domain=next_rec.get("domain", interview.domain).strip(),
            reason=next_rec.get("reason", "").strip(),
            suggested_by=interview.slug,
        )
        if nr.slug:
            # Replace any previous suggestion with the same slug (idempotent re-runs).
            global_state.next_recommendations = [
                r for r in global_state.next_recommendations if r.slug != nr.slug
            ]
            global_state.next_recommendations.append(nr)

    ui.success(t("interview_complete"))
    if interview.total_cost_usd > 0 or interview.agent_calls > 0:
        ui.console.print(
            f"  [muted]· "
            f"{t('cost_summary', calls=interview.agent_calls, cost=interview.total_cost_usd, secs=interview.total_duration_ms / 1000)}"
            f"[/muted]"
        )
    if written:
        ui.blank()
        ui.info(t("interview_files_created"))
        for f in written:
            ui.console.print(f"  [accent]{f}[/accent]")
    if summary:
        ui.blank()
        ui.console.print(f"[muted]{summary}[/muted]")
    if next_rec is not None and next_rec.get("slug"):
        ui.blank()
        ui.console.print(
            f"[brand]💡 {t('interview_next_suggested')}[/brand] "
            f"[bold]{next_rec.get('slug')}[/bold] "
            f"[muted]({next_rec.get('domain', interview.domain)})[/muted]"
        )
        if next_rec.get("reason"):
            ui.console.print(f"   [muted]{next_rec.get('reason')}[/muted]")
        ui.blank()
        ui.hint(t("interview_next_command", slug=next_rec.get("slug"), domain=next_rec.get("domain", interview.domain)))
    elif not written and not summary and result.text:
        # Fallback when the agent did not return JSON: show raw text.
        ui.console.print(result.text[:1500])
    return True


def _parse_generate_envelope(text: str) -> tuple[list[str], str, dict | None]:
    """Extract (files_written, summary, next_recommendation) from the agent reply.

    Tolerates code fences and surrounding prose. Returns ([], "", None) on failure
    (no exception): callers fall back to mark `generated` regardless.
    """
    import json
    import re

    if not text:
        return [], "", None

    candidate = text.strip()
    # Strip code fences if present.
    if candidate.startswith("```"):
        # crude fence stripper — first line and last line if they are fences
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    # If still not pure JSON, try to find the largest {...} block.
    if not candidate.startswith("{"):
        m = re.search(r"\{.*\}", candidate, re.DOTALL)
        candidate = m.group(0) if m else ""

    if not candidate:
        return [], "", None

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return [], "", None

    if not isinstance(data, dict):
        return [], "", None

    written = [str(f) for f in data.get("files_written", []) if isinstance(f, str)]
    summary = str(data.get("summary", "") or "")
    next_rec = data.get("next_recommendation")
    if not isinstance(next_rec, dict):
        next_rec = None
    return written, summary, next_rec
