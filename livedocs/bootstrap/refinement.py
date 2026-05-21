"""Bootstrap phase 6 — Entrevista de refinamento.

Two sub-steps:

  1. AI dedup. The whole list of `open` pending questions is sent to
     Claude in one call. The model groups equivalent ones, picks a
     canonical id per cluster, suggests a cleaned-up canonical question,
     and lists the remaining unique ids. We apply the merge via
     `pending.merge_questions`.

  2. Interactive batch interview. For each canonical question still
     `open`, ask the maintainer a single answer; on submission, we
     propagate the answer to every merged sibling via
     `pending.propagate_answer`. State is saved after each answer so a
     mid-interview interrupt can be resumed.

Non-interactive mode (`ui.is_non_interactive()` true) skips the
interactive step entirely — questions stay open. Useful for CI and
behind `--skip-refinement` in the orchestrator.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jinja2 import Template

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.bootstrap.pending import (
    find_open,
    merge_questions,
    propagate_answer,
)
from livedocs.bootstrap.state import (
    BootstrapState,
    PendingQuestion,
    save_bootstrap_state,
)
from livedocs.models import ProjectConfig

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "refinement_dedup.md"

ProgressCallback = Callable[[str], None]


def _render_dedup_prompt(questions: list[PendingQuestion], guidance_text: str) -> str:
    template = Template(
        _PROMPT_PATH.read_text(encoding="utf-8"),
        autoescape=False,
        keep_trailing_newline=True,
    )  # noqa: S701
    return template.render(
        questions=[
            {
                "id": q.id,
                "guide_slug": q.guide_slug,
                "confidence": q.confidence,
                "question": q.question,
                "provisional_answer": q.provisional_answer,
            }
            for q in questions
        ],
        guidance_text=guidance_text,
    )


def _run_dedup(
    repo_root: Path,
    cfg: ProjectConfig,
    state: BootstrapState,
) -> None:
    """One Claude call to cluster equivalent questions."""
    opens = find_open(state)
    if len(opens) < 2:
        return  # nothing to dedup

    agent = ClaudeAgent(repo_root=repo_root, lang=cfg.lang)
    guidance_text = (state.guidance.text or "").strip()
    prompt = "# Task: refinement-dedup\n\n" + _render_dedup_prompt(opens, guidance_text)

    try:
        result = agent.call(
            prompt,
            expect_json=True,
            timeout=300,
            allowed_tools=[],
        )
    except AgentError as e:
        ui.warn(f"[refinement] dedup falhou ({e}); seguindo sem agrupar")
        return

    if result.is_error or not isinstance(result.json_data, dict):
        ui.warn("[refinement] dedup: JSON inválido; seguindo sem agrupar")
        return

    data: dict[str, Any] = result.json_data
    clusters = data.get("clusters") or []
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        canonical_id = (cluster.get("canonical_id") or "").strip()
        if not canonical_id:
            continue
        merged_ids = [
            str(m).strip() for m in (cluster.get("merged_ids") or []) if str(m).strip()
        ]
        canonical_question = (cluster.get("canonical_question") or "").strip() or None
        merge_questions(state, canonical_id, merged_ids, canonical_question)

    state.total_cost_usd += float(result.cost_usd or 0.0)
    save_bootstrap_state(repo_root, state)


# ---------------------------------------------------------------------------
# Interactive interview
# ---------------------------------------------------------------------------

def _siblings_for(
    state: BootstrapState, canonical_id: str
) -> list[PendingQuestion]:
    return [
        q for q in state.pending_questions
        if q.merged_into == canonical_id and q.status == "merged"
    ]


def _render_question(
    rec: PendingQuestion,
    siblings: list[PendingQuestion],
    n: int,
    total: int,
) -> None:
    ui.section(f"Pergunta {n}/{total} (origem: guia '{rec.guide_slug}')")
    ui.console.print()
    ui.console.print("O agente perguntou:")
    ui.console.print(f"  {rec.question}")
    ui.console.print()
    conf_label = "alta" if rec.confidence == "high" else "baixa"
    ui.console.print(
        f"Suposição provisória no rascunho (confiança: {conf_label}):"
    )
    ui.console.print(f"  {rec.provisional_answer or '(nenhuma)'}")
    if siblings:
        ui.console.print()
        ui.console.print("Outras perguntas que esta também responde:")
        for s in siblings:
            ui.console.print(f"  - {s.id} ({s.guide_slug}): {s.question}")
    ui.console.print()


def run_refinement(
    repo_root: Path,
    cfg: ProjectConfig,
    state: BootstrapState,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Phase 6 entry point: dedup + batch interview."""
    opens = find_open(state)
    if not opens:
        ui.info("[refinement] sem perguntas pendentes; nada a fazer")
        return

    # 1. dedup
    _run_dedup(repo_root, cfg, state)

    # 2. interview
    if ui.is_non_interactive():
        ui.warn(
            "[refinement] modo não-interativo: entrevista pulada. "
            "Rode `livedocs refine` mais tarde."
        )
        return

    canonicals = [q for q in state.pending_questions if q.status == "open"]
    total = len(canonicals)
    for i, canonical in enumerate(canonicals, start=1):
        siblings = _siblings_for(state, canonical.id)
        _render_question(canonical, siblings, i, total)
        try:
            answer = ui.ask_text(
                "Resposta (vazio ou /skip para pular)",
                multiline=True,
            )
        except ui.NonInteractiveError:
            ui.warn("[refinement] perdi o TTY no meio da entrevista; abortando")
            return

        if answer is None:
            ui.warn("[refinement] entrevista interrompida pelo usuário")
            return

        ans = answer.strip()
        if not ans or ans == "/skip":
            ui.hint("(pulado)")
            continue

        propagate_answer(state, canonical.id, ans)
        save_bootstrap_state(repo_root, state)
        if on_progress is not None:
            with contextlib.suppress(Exception):
                on_progress(f"{canonical.id} respondida")


__all__ = ["run_refinement"]
