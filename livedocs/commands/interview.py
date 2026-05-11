"""Interview orchestrator — fact-driven adaptive flow (v0.2).

The CLI drives, the agent executes. Each turn:

  1. Show user the fact that needs confirmation (pending question rendered in {lang})
  2. Get user's answer (or skip / pause)
  3. Send to agent for reflection: cross-check with code, detect coverage of
     other facts, propose new facts that emerged
  4. Update Fact records; persist state.toml after every meaningful change

When all facts critical/high are resolved, run pre-generation self-audit, then
the generate-guides prompt. The CLI keeps the loop tight — no batched questions,
no rigid 20-question script.

State invariants:
  - state.toml rewritten after every meaningful change
  - Skips never lose info — they go into the interview record with their status
  - Speculation facts are silently dropped at generation time
  - Hypothesis-with-trace facts go to Pendências in the .tech.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from livedocs import ui
from livedocs.agent import AgentError, AgentResult, ClaudeAgent
from livedocs.i18n import t
from livedocs.skill import (
    PROMPT_BUILD_SKELETON,
    PROMPT_GENERATE_GUIDES,
    PROMPT_PARSE_INTENT,
    PROMPT_PREGEN_SELF_AUDIT,
    PROMPT_REFLECT_ON_ANSWER,
)
from livedocs.state import (
    Evidence,
    Fact,
    GlobalState,
    InterviewState,
    NextRecommendation,
    ProjectConfig,
    guides_root,
    save_state,
)

# ---------------------------------------------------------------------------
# Constants — interactive sentinel tokens
# ---------------------------------------------------------------------------

PAUSE_TOKENS = {"/sair", "/exit", "/quit", "/q", "/pause", "/pausar"}
SKIP_TOKENS = {"/skip", "/pular", "/pula"}


# ---------------------------------------------------------------------------
# Prompt rendering — we use a tiny safe-substitution helper instead of
# str.format() because the prompts contain literal `{...}` JSON examples
# that str.format would interpret as fields and crash with KeyError.
# ---------------------------------------------------------------------------

def _render_prompt(template: str, **kwargs: object) -> str:
    """Replace ${name} or {name} placeholders with provided kwargs.

    Only substitutes the keys explicitly passed; any leftover `{foo}` in the
    template stays as-is (which is what we want for embedded JSON examples).
    """
    out = template
    for key, value in kwargs.items():
        out = out.replace("{" + key + "}", str(value))
    return out


# ---------------------------------------------------------------------------
# Cost tracking helper
# ---------------------------------------------------------------------------

def _track_cost(interview: InterviewState, result: AgentResult) -> None:
    """Accumulate cost/duration/call-count from any AgentResult."""
    interview.total_cost_usd += float(result.cost_usd or 0.0)
    interview.total_duration_ms += int(result.duration_ms or 0)
    interview.agent_calls += 1


# ---------------------------------------------------------------------------
# Phase C1 — Parse user's free-text intent into structured metadata
# ---------------------------------------------------------------------------

def parse_intent(
    repo_root: Path,
    cfg: ProjectConfig,
    intent_text: str,
    existing_domains: list[str],
) -> dict[str, Any] | None:
    """Ask the agent to extract {slug, domain, title, is_new_domain} from free text.

    Returns the parsed dict, or None on failure (UI already reported).
    """
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    domains_block = (
        "\n".join(f"- {d}" for d in existing_domains)
        if existing_domains
        else "(none yet — the project has no documented domains)"
    )
    prompt = _render_prompt(PROMPT_PARSE_INTENT,
        intent=intent_text.strip(),
        existing_domains=domains_block,
        lang=cfg.lang,
    )

    try:
        with ui.spinner(t("intent_parsing")):
            result = agent.call(prompt, expect_json=True, timeout=60)
    except AgentError as e:
        ui.error(str(e))
        return None

    if result.is_error or not isinstance(result.json_data, dict):
        ui.error(t("intent_parse_failed"))
        if result.text:
            ui.hint(result.text[:300])
        return None

    data = result.json_data
    # Basic shape validation
    required = ("slug", "domain", "title")
    if not all(k in data and data[k] for k in required):
        ui.error(t("intent_parse_failed"))
        return None
    return data


# ---------------------------------------------------------------------------
# Phase C2 — Build the fact skeleton (replaces start_new_interview)
# ---------------------------------------------------------------------------

def build_skeleton(
    repo_root: Path,
    cfg: ProjectConfig,
    global_state: GlobalState,
    *,
    slug: str,
    domain: str,
    title: str,
    intent_text: str = "",
) -> InterviewState | None:
    """Build the initial Fact skeleton for a brand-new interview."""
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    existing_compact = "\n".join(
        f"- {s} ({iv.domain}) [{iv.status}]"
        for s, iv in sorted(global_state.interviews.items())
    ) or "(none)"

    prompt = _render_prompt(PROMPT_BUILD_SKELETON,
        slug=slug,
        domain=domain,
        title=title,
        lang=cfg.lang,
        repo_root=str(repo_root),
        docs_dir=cfg.docs_dir,
        existing_guides_compact=existing_compact,
    )

    ui.blank()
    ui.info(t("skeleton_building", slug=slug))

    try:
        with ui.spinner(t("skeleton_thinking")):
            result = agent.call(prompt, expect_json=True, timeout=480)
    except AgentError as e:
        ui.error(str(e))
        return None

    if result.is_error or not isinstance(result.json_data, dict):
        ui.error(t("skeleton_failed"))
        if result.text:
            ui.hint(result.text[:500])
        return None

    data = result.json_data
    raw_facts = data.get("facts") or []
    if not isinstance(raw_facts, list) or not raw_facts:
        ui.error(t("skeleton_failed"))
        return None

    facts: list[Fact] = []
    for raw in raw_facts:
        try:
            facts.append(_fact_from_raw(raw))
        except Exception as e:  # pragma: no cover (defensive)
            ui.warn(f"Ignoring malformed fact: {e}")
            continue

    if not facts:
        ui.error(t("skeleton_failed"))
        return None

    interview = InterviewState(
        slug=slug,
        domain=domain,
        title=data.get("title", title),
        facts=facts,
        source_files=[s for s in (data.get("source_files") or []) if isinstance(s, str)],
        original_intent=intent_text,
        total_cost_usd=float(result.cost_usd or 0.0),
        total_duration_ms=int(result.duration_ms or 0),
        agent_calls=1,
    )
    global_state.interviews[slug] = interview
    global_state.last_touched_slug = slug
    save_state(repo_root, global_state)

    # Handle should_split suggestion
    should_split = data.get("should_split")
    if isinstance(should_split, dict) and should_split.get("suggested_slugs"):
        ui.blank()
        ui.warn(t("skeleton_split_suggested"))
        ui.console.print(f"  [muted]{should_split.get('reason', '')}[/muted]")
        ui.console.print(f"  [muted]Sugestões: {', '.join(should_split['suggested_slugs'])}[/muted]")
        ui.hint(t("skeleton_split_hint"))

    # Quick summary
    summary = _facts_summary(facts)
    ui.success(
        t(
            "skeleton_ready",
            total=summary["total"],
            confirmed=summary["confirmed"],
            pending=summary["pending"],
            hypothesized=summary["hypothesized"],
        )
    )
    return interview


def _fact_from_raw(raw: dict) -> Fact:
    """Coerce loose JSON from the agent into a strict Fact model."""
    evidence_raw = raw.get("evidence") or []
    evidence: list[Evidence] = []
    for e in evidence_raw:
        if not isinstance(e, dict):
            continue
        ek = e.get("kind", "hypothesis")
        if ek not in ("code", "answer", "guide", "hypothesis"):
            ek = "hypothesis"
        evidence.append(Evidence(kind=ek, ref=str(e.get("ref", "")), note=str(e.get("note", ""))))

    kind = raw.get("kind", "flow")
    valid_kinds = {"trigger", "invariant", "edge_case", "terminology", "flow", "value", "actor", "ui_surface"}
    if kind not in valid_kinds:
        kind = "flow"

    confidence = raw.get("confidence", "none")
    if confidence not in ("none", "low", "medium", "high"):
        confidence = "none"

    priority = raw.get("priority", "needs-confirmation")
    if priority not in ("established", "needs-confirmation", "hypothesis-with-trace", "speculation"):
        priority = "needs-confirmation"

    status = raw.get("status", "open")
    if status not in ("open", "hypothesized", "confirmed", "contradicted", "resolved"):
        status = "open"

    pending_q = raw.get("pending_question")
    if pending_q == "" or pending_q is None:
        pending_q = None

    return Fact(
        id=str(raw.get("id") or "F?"),
        kind=kind,
        text=str(raw.get("text", "")),
        confidence=confidence,
        priority=priority,
        status=status,
        evidence=evidence,
        derived_from=[str(x) for x in (raw.get("derived_from") or []) if isinstance(x, str)],
        pending_question=pending_q,
    )


def _facts_summary(facts: list[Fact]) -> dict[str, int]:
    return {
        "total": len(facts),
        "confirmed": sum(1 for f in facts if f.status in ("confirmed", "resolved")),
        "pending": sum(
            1 for f in facts
            if f.priority == "needs-confirmation" and f.status not in ("confirmed", "resolved")
        ),
        "hypothesized": sum(1 for f in facts if f.status == "hypothesized"),
        "open": sum(1 for f in facts if f.status == "open"),
    }


# ---------------------------------------------------------------------------
# Phase C3 — Adaptive interview loop
# ---------------------------------------------------------------------------

def run_adaptive_loop(
    repo_root: Path,
    cfg: ProjectConfig,
    global_state: GlobalState,
    interview: InterviewState,
) -> bool:
    """Drive the fact-by-fact loop. Return True when all pending facts handled.

    Returns False if user paused mid-loop.
    """
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    while True:
        pending = interview.pending_facts()
        if not pending:
            return True

        fact = pending[0]
        _render_progress(interview, fact)

        try:
            answer = ui.ask_text(t("interview_answer_q"), multiline=True)
        except ui.NonInteractiveError as e:
            ui.error(str(e))
            interview.last_touched_at = _now()
            save_state(repo_root, global_state)
            return False

        if answer is None:
            ui.warn(t("interview_paused"))
            interview.last_touched_at = _now()
            save_state(repo_root, global_state)
            return False

        stripped = answer.strip()

        if stripped.lower() in PAUSE_TOKENS:
            ui.info(t("interview_paused"))
            interview.last_touched_at = _now()
            save_state(repo_root, global_state)
            return False

        if stripped == "" or stripped.lower() in SKIP_TOKENS:
            # Skipping a needs-confirmation fact → demote to hypothesis-with-trace
            # so it surfaces in Pendências instead of becoming an assertion.
            fact.priority = "hypothesis-with-trace"
            fact.status = "hypothesized"
            fact.resolved_at = _now()
            fact.last_touched_at = fact.resolved_at
            save_state(repo_root, global_state)
            continue

        # Real answer — reflect with agent
        fact.answer_text = stripped
        fact.resolved_at = _now()
        fact.last_touched_at = fact.resolved_at
        global_state.last_touched_slug = interview.slug
        interview.last_touched_at = fact.resolved_at
        save_state(repo_root, global_state)

        # Cross-check with agent
        other_pending = [f for f in interview.pending_facts() if f.id != fact.id]
        try:
            reflection = _reflect_on_answer(agent, interview, fact, stripped, other_pending)
        except AgentError as e:
            ui.warn(f"{t('reflect_skipped')}: {e}")
            # Default classification: trust the user
            fact.status = "confirmed"
            fact.evidence.append(Evidence(kind="answer", ref=fact.id, note="(reflection skipped)"))
            save_state(repo_root, global_state)
            continue

        _apply_reflection(interview, fact, stripped, reflection)
        save_state(repo_root, global_state)


def _reflect_on_answer(
    agent: ClaudeAgent,
    interview: InterviewState,
    fact: Fact,
    answer: str,
    other_pending: list[Fact],
) -> dict[str, Any]:
    """Call the agent to reflect on the user's answer."""
    other_block = (
        "\n".join(f"- **{f.id}** ({f.kind}): {f.pending_question or f.text}" for f in other_pending)
        if other_pending
        else "(none)"
    )
    prompt = _render_prompt(PROMPT_REFLECT_ON_ANSWER,
        fact_id=fact.id,
        fact_text=fact.text,
        pending_question=fact.pending_question or fact.text,
        answer=answer[:2000].replace("\n", " "),
        other_facts_compact=other_block,
    )
    with ui.spinner(t("reflect_thinking")):
        result = agent.call(prompt, expect_json=True, timeout=120)
    _track_cost(interview, result)

    if result.is_error or not isinstance(result.json_data, dict):
        # Don't blow up — return a minimal "confirmed" outcome to keep flow alive.
        return {"outcome": "confirmed", "covers_other_facts": [], "new_facts": []}
    return result.json_data


def _apply_reflection(
    interview: InterviewState,
    fact: Fact,
    answer: str,
    reflection: dict[str, Any],
) -> None:
    """Mutate the interview based on what the agent found."""
    outcome = str(reflection.get("outcome", "confirmed"))
    now = _now()

    if outcome == "contradicted":
        fact.status = "contradicted"
        note = str(reflection.get("contradiction_note", ""))
        code_ref = str(reflection.get("code_ref", ""))
        if code_ref:
            fact.evidence.append(Evidence(kind="code", ref=code_ref, note=f"Contradiction: {note}"))
        fact.evidence.append(Evidence(kind="answer", ref=fact.id, note="User answer (contradicts code)"))
        ui.blank()
        ui.warn(t("reflect_contradiction"))
        if note:
            ui.console.print(f"  [muted]{note}[/muted]")
        if code_ref:
            ui.console.print(f"  [muted]→ {code_ref}[/muted]")
        ui.hint(t("reflect_contradiction_hint"))

    elif outcome == "confirmed_with_correction":
        fact.status = "confirmed"
        note = str(reflection.get("correction_note", ""))
        code_ref = str(reflection.get("code_ref", ""))
        if code_ref:
            fact.evidence.append(Evidence(kind="code", ref=code_ref, note=note))
        fact.evidence.append(Evidence(kind="answer", ref=fact.id))
        if note:
            ui.blank()
            ui.info(t("reflect_corrected"))
            ui.console.print(f"  [muted]{note}[/muted]")

    elif outcome == "needs_more":
        fact.status = "open"
        follow_up = str(reflection.get("follow_up_question", "")).strip()
        if follow_up:
            fact.pending_question = follow_up
        else:
            fact.status = "confirmed"
            fact.evidence.append(Evidence(kind="answer", ref=fact.id))

    else:  # confirmed
        fact.status = "confirmed"
        fact.evidence.append(Evidence(kind="answer", ref=fact.id))

    # Coverage propagation
    covered_ids = reflection.get("covers_other_facts", []) or []
    if isinstance(covered_ids, list) and covered_ids:
        by_id = {f.id: f for f in interview.facts}
        labels = []
        for cid in covered_ids:
            f = by_id.get(str(cid))
            if f and f.status not in ("confirmed", "resolved") and f.id != fact.id:
                f.status = "resolved"
                f.priority = "established"
                f.resolved_at = now
                f.last_touched_at = now
                f.evidence.append(
                    Evidence(kind="answer", ref=fact.id, note=f"Covered by answer to {fact.id}")
                )
                labels.append(f.id)
        if labels:
            ui.blank()
            ui.info(t("reflect_covered_others", ids=", ".join(labels)))

    # New facts that emerged
    new_facts = reflection.get("new_facts", []) or []
    if isinstance(new_facts, list) and new_facts:
        for raw in new_facts:
            try:
                nf = _fact_from_raw(raw)
            except Exception:
                continue
            # Avoid id collision
            if any(f.id == nf.id for f in interview.facts):
                next_n = 1 + max(
                    (int(f.id[1:]) for f in interview.facts if f.id.startswith("F") and f.id[1:].isdigit()),
                    default=0,
                )
                nf.id = f"F{next_n}"
            interview.facts.append(nf)
        ui.info(t("reflect_new_facts", n=len(new_facts)))


# ---------------------------------------------------------------------------
# Phase C4 — Pre-generation self-audit
# ---------------------------------------------------------------------------

def pregen_self_audit(
    repo_root: Path,
    cfg: ProjectConfig,
    interview: InterviewState,
) -> tuple[bool, dict[str, Any]]:
    """Returns (ready_to_generate, audit_dict)."""
    agent = ClaudeAgent(repo_root, lang=cfg.lang)
    facts_compact = "\n".join(
        f"- **{f.id}** ({f.kind}, priority={f.priority}, status={f.status}, "
        f"conf={f.confidence}): {f.text[:120]}"
        for f in interview.facts
    )

    prompt = _render_prompt(PROMPT_PREGEN_SELF_AUDIT,
        slug=interview.slug,
        domain=interview.domain,
        lang=cfg.lang,
        facts_compact=facts_compact,
    )

    try:
        with ui.spinner(t("pregen_audit")):
            result = agent.call(prompt, expect_json=True, timeout=120)
    except AgentError as e:
        ui.warn(f"Self-audit skipped: {e}")
        return True, {}

    _track_cost(interview, result)

    if result.is_error or not isinstance(result.json_data, dict):
        return True, {}

    data = result.json_data
    ready = bool(data.get("ready_to_generate", True))
    return ready, data


# ---------------------------------------------------------------------------
# Phase C5 — Generate the v1 paired guides
# ---------------------------------------------------------------------------

def generate_guides(
    repo_root: Path,
    cfg: ProjectConfig,
    interview: InterviewState,
    global_state: GlobalState | None = None,
) -> bool:
    """Ask the agent to write produto + tech + interview .md files."""
    agent = ClaudeAgent(repo_root, lang=cfg.lang)

    # Compute confidence score before sending it to the agent
    interview.confidence_score = interview.compute_confidence_score()

    facts_payload = []
    for f in interview.facts:
        # Drop pure speculation; agent should never see them.
        if f.priority == "speculation":
            continue
        facts_payload.append(
            {
                "id": f.id,
                "kind": f.kind,
                "text": f.text,
                "confidence": f.confidence,
                "priority": f.priority,
                "status": f.status,
                "evidence": [{"kind": e.kind, "ref": e.ref, "note": e.note} for e in f.evidence],
                "answer_text": f.answer_text,
                "pending_question": f.pending_question,
            }
        )

    full_dir_path = guides_root(repo_root, cfg) / interview.domain
    full_dir_rel = full_dir_path.relative_to(repo_root)

    # Load the project's style guide so the agent writes in the user's chosen voice.
    from livedocs.skill.styles import load_project_style
    style_content = load_project_style(repo_root)

    prompt = _render_prompt(PROMPT_GENERATE_GUIDES,
        slug=interview.slug,
        domain=interview.domain,
        title=interview.title or interview.slug,
        lang=cfg.lang,
        repo_root=str(repo_root),
        docs_dir=cfg.docs_dir,
        guides_subdir=cfg.guides_subdir,
        full_dir=str(full_dir_rel),
        today=datetime.now().date().isoformat(),
        facts_full=json.dumps(facts_payload, ensure_ascii=False, indent=2),
        quality_score=f"{interview.confidence_score:.2f}",
    )

    # Append the style guide so the agent writes in the project's voice.
    # Done as a suffix instead of a template placeholder to keep the prompt
    # template stable across style customizations.
    prompt = (
        prompt
        + "\n\n---\n\n# Writing style guide (project-specific)\n\n"
        + "The guide MUST follow these style rules. If the rules below conflict "
        + "with anything earlier in this prompt, the style guide wins for voice "
        + "and tone (the earlier rules win for structure and front-matter).\n\n"
        + style_content
    )

    ui.blank()
    try:
        with ui.spinner(t("interview_generating")):
            result = agent.call(prompt, expect_json=False, timeout=600)
    except AgentError as e:
        ui.error(str(e))
        return False

    _track_cost(interview, result)

    if result.is_error:
        ui.error(result.error_message or "Agent error during guide generation.")
        return False

    written, summary, next_rec = _parse_generate_envelope(result.text or "")

    # Verify the agent actually wrote what it claimed (carried from v0.1.x)
    missing = [f for f in written if not (repo_root / f).exists()]
    if written and missing:
        ui.error(t("interview_files_missing", n=len(missing), total=len(written)))
        for f in missing:
            ui.console.print(f"  [err]✗[/err] {f}")
        ui.hint(t("interview_files_missing_hint"))
        return False

    if not written:
        # Cross-check expected paths
        expected = [
            f"{full_dir_rel}/{interview.slug}.md",
            f"{full_dir_rel}/{interview.slug}.tech.md",
        ]
        present = [p for p in expected if (repo_root / p).exists()]
        if not present:
            ui.error(t("interview_no_files_written"))
            ui.hint(t("interview_files_missing_hint"))
            return False
        written = present
        ui.warn(t("interview_files_recovered", n=len(written)))

    interview.status = "generated"

    if next_rec is not None and global_state is not None and next_rec.get("slug"):
        nr = NextRecommendation(
            slug=str(next_rec["slug"]).strip(),
            domain=str(next_rec.get("domain", interview.domain)).strip(),
            reason=str(next_rec.get("reason", "")).strip(),
            suggested_by=interview.slug,
        )
        # Idempotent: replace any previous same-slug suggestion.
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
        ui.console.print(result.text[:1500])

    return True


# ---------------------------------------------------------------------------
# UI helpers (visual progress, fact list)
# ---------------------------------------------------------------------------

def _render_progress(interview: InterviewState, current_fact: Fact) -> None:
    """Show 'where we are' header before the next question."""
    coverage = interview.coverage_ratio()
    bar_width = 20
    filled = int(round(coverage * bar_width))
    bar = "█" * filled + "░" * (bar_width - filled)
    pct = int(round(coverage * 100))

    pending = interview.pending_facts()
    confirmed = interview.confirmed_facts()
    hypothesized = interview.hypothesized_facts()

    ui.blank()
    ui.section(interview.title or interview.slug, hint=f"({interview.domain})")
    ui.console.print(
        f"  [brand]{bar}[/brand]  [accent]{pct}%[/accent]   "
        f"[ok]✓ {len(confirmed)}[/ok]  [warn]→ {len(pending)}[/warn]"
        + (f"  [muted]🟡 {len(hypothesized)}[/muted]" if hypothesized else "")
    )
    ui.blank()
    ui.console.print(
        f"  [bold]{current_fact.id}[/bold] "
        f"[muted]({_kind_label(current_fact.kind, interview)})[/muted]"
    )
    ui.console.print(f"  {current_fact.pending_question or current_fact.text}")
    ui.blank()
    ui.hint(t("interview_skip_hint"))


def _kind_label(kind: str, interview: InterviewState) -> str:
    """Translate the technical kind into a human label in interview language."""
    # interview lang is held in state via i18n; we don't have per-interview lang yet,
    # so we use the active language.
    return t(f"fact_kind_{kind}", default_=kind)


# ---------------------------------------------------------------------------
# JSON envelope parser (carried over from v0.1, robust to off-script replies)
# ---------------------------------------------------------------------------

def _parse_generate_envelope(text: str) -> tuple[list[str], str, dict | None]:
    import re

    if not text:
        return [], "", None

    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

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

    written = [str(f) for f in (data.get("files_written") or []) if isinstance(f, str)]
    summary = str(data.get("summary", "") or "")
    next_rec = data.get("next_recommendation")
    if not isinstance(next_rec, dict):
        next_rec = None
    return written, summary, next_rec


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "parse_intent",
    "build_skeleton",
    "run_adaptive_loop",
    "pregen_self_audit",
    "generate_guides",
]
