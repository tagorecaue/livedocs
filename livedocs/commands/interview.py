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
    ProjectConfig,
    QuestionState,
    save_state,
)

SKIP_TOKENS = {"/skip", "/pular", "/pula"}
PAUSE_TOKENS = {"/sair", "/exit", "/quit", "/q"}
EDITOR_TOKENS = {"/editor", "/edit", "/e"}


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
                covered_ids = _check_coverage(agent, q, stripped, other_pending)
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
) -> bool:
    """Send the full interview transcript to the agent and ask it to write the guides."""
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

    if result.is_error:
        ui.error(result.error_message or "Agent error during guide generation.")
        return False

    interview.status = "generated"

    # Best-effort: extract files_written list from result text
    written: list[str] = []
    text = result.text or ""
    # If agent returned JSON wrapper, parse it
    if text.strip().startswith("{"):
        try:
            import json
            data = json.loads(text.strip())
            written = list(data.get("files_written", []))
        except Exception:
            pass

    ui.success(t("interview_complete"))
    if written:
        ui.blank()
        ui.info(t("interview_files_created"))
        for f in written:
            ui.console.print(f"  [accent]{f}[/accent]")
    elif text:
        # Show the summary as-is
        ui.console.print(text[:1500])
    return True
