"""`livedocs new` — start a new guide.

v0.2 flow:
  1. Free-text intent (or --slug/--domain/--title shortcut)
  2. Parse intent into structured metadata, user confirms/edits
  3. Build fact skeleton (agent reads code)
  4. Adaptive interview loop
  5. Pre-generation self-audit
  6. Generate paired guides + interview record
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui
from livedocs.commands.interview import (
    build_skeleton,
    generate_guides,
    parse_intent,
    pregen_self_audit,
    run_adaptive_loop,
)
from livedocs.detect import has_claude_code
from livedocs.i18n import t
from livedocs.state import (
    GlobalState,
    InterviewState,
    ProjectConfig,
    load_config,
    load_state,
    save_state,
)


def run_new(
    repo_root: Path,
    *,
    slug: str | None = None,
    domain: str | None = None,
    title: str | None = None,
    answers_file: Path | None = None,  # legacy, kept for CLI signature compat
) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1
    if not has_claude_code():
        ui.error(t("err_no_claude"))
        return 1

    if answers_file is not None:
        ui.warn(
            "--answers-file ainda não foi reescrito para o fluxo fact-driven da v0.2."
            if cfg.lang == "pt-BR"
            else "--answers-file has not been rewritten for the v0.2 fact-driven flow."
        )
        return 2

    state = load_state(repo_root)

    # Path 1: shortcut — user passed --slug, skip intent parsing.
    if slug:
        if slug in state.interviews:
            ui.warn(
                f"'{slug}' já existe — use [bold]livedocs continue {slug}[/bold]."
                if cfg.lang == "pt-BR"
                else f"'{slug}' already exists — use [bold]livedocs continue {slug}[/bold]."
            )
            return 1
        if not domain:
            domain = _prompt_domain(cfg, state)
            if domain is None:
                return 130
        return _run_skeleton_and_loop(
            repo_root, cfg, state,
            slug=slug, domain=domain, title=title or slug, intent_text="",
        )

    # Path 2: free-text intent
    return _run_free_text_intent(repo_root, cfg, state)


# ---------------------------------------------------------------------------
# Free-text intent path
# ---------------------------------------------------------------------------

def _run_free_text_intent(repo_root: Path, cfg: ProjectConfig, state: GlobalState) -> int:
    ui.blank()
    ui.section(t("intent_q"))
    ui.hint(t("intent_hint"))
    try:
        intent_text = ui.ask_text(t("intent_q"), multiline=False)
    except ui.NonInteractiveError as e:
        ui.error(str(e))
        return 2

    if intent_text is None or not intent_text.strip():
        ui.warn(t("abort"))
        return 130
    intent_text = intent_text.strip()

    existing_domains = sorted({iv.domain for iv in state.interviews.values()})
    parsed = parse_intent(repo_root, cfg, intent_text, existing_domains)
    if parsed is None:
        return 1

    slug = str(parsed["slug"]).strip()
    domain = str(parsed["domain"]).strip()
    title = str(parsed["title"]).strip()
    is_new_domain = bool(parsed.get("is_new_domain"))
    clarification = str(parsed.get("clarification_needed", "")).strip()

    if clarification:
        ui.blank()
        ui.warn(t("intent_clarification", q=clarification))

    ui.blank()
    if is_new_domain:
        ui.console.print(f"  · {t('intent_new_domain')}")
    ui.console.print(
        f"  · {t('intent_review_q', title=title, slug=slug, domain=domain)}"
    )

    choice = ui.ask_choice(
        " ",
        choices=[
            ("Confirmar e seguir" if cfg.lang == "pt-BR" else "Confirm and proceed", "confirm"),
            ("Editar slug/domínio/título" if cfg.lang == "pt-BR" else "Edit slug/domain/title", "edit"),
            (t("cancel"), "cancel"),
        ],
        default="confirm",
    )
    if choice is None or choice == "cancel":
        ui.warn(t("abort"))
        return 130

    if choice == "edit":
        new_slug = ui.ask_text(t("intent_edit_slug_q"), default=slug)
        if not new_slug:
            return 130
        slug = new_slug.strip()

        new_domain = ui.ask_text(t("intent_edit_domain_q"), default=domain)
        if not new_domain:
            return 130
        domain = new_domain.strip()

        new_title = ui.ask_text(t("intent_edit_title_q"), default=title)
        if new_title:
            title = new_title.strip()

    if slug in state.interviews:
        ui.warn(
            f"'{slug}' já existe — use [bold]livedocs continue {slug}[/bold]."
            if cfg.lang == "pt-BR"
            else f"'{slug}' already exists — use [bold]livedocs continue {slug}[/bold]."
        )
        return 1

    return _run_skeleton_and_loop(
        repo_root, cfg, state,
        slug=slug, domain=domain, title=title, intent_text=intent_text,
    )


# ---------------------------------------------------------------------------
# Skeleton + adaptive loop + self-audit + generate
# ---------------------------------------------------------------------------

def _run_skeleton_and_loop(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    *,
    slug: str,
    domain: str,
    title: str,
    intent_text: str,
) -> int:
    interview = build_skeleton(
        repo_root, cfg, state,
        slug=slug, domain=domain, title=title, intent_text=intent_text,
    )
    if interview is None:
        return 1

    completed = run_adaptive_loop(repo_root, cfg, state, interview)
    if not completed:
        return 0  # paused

    return _finish_and_generate(repo_root, cfg, state, interview)


def _finish_and_generate(
    repo_root: Path,
    cfg: ProjectConfig,
    state: GlobalState,
    interview: InterviewState,
) -> int:
    # Pre-generation self-audit
    ready, audit = pregen_self_audit(repo_root, cfg, interview)
    if not ready:
        ui.warn(
            (audit.get("block_reason") if isinstance(audit, dict) else None)
            or ("Audit indicou que faltam respostas críticas." if cfg.lang == "pt-BR"
                else "Audit reports critical answers still missing.")
        )
        # Best UX: leave interview in_progress so user can continue
        save_state(repo_root, state)
        return 0

    ok = generate_guides(repo_root, cfg, interview, global_state=state)
    save_state(repo_root, state)
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prompt_domain(cfg: ProjectConfig, state: GlobalState) -> str | None:
    existing_domains = sorted({iv.domain for iv in state.interviews.values()})
    if existing_domains:
        choices = [(d, d) for d in existing_domains] + [
            (t("new_domain_new") if "new_domain_new" in dir() else "+ Novo domínio…", "__new__"),
        ]
        picked = ui.ask_choice(
            t("new_domain_q") if "new_domain_q" in dir() else (
                "Em qual domínio?" if cfg.lang == "pt-BR" else "Which domain?"
            ),
            choices=choices,
            default=existing_domains[0],
        )
        if picked is None:
            return None
        if picked == "__new__":
            d = ui.ask_text("Novo domínio" if cfg.lang == "pt-BR" else "New domain")
            if not d or not d.strip():
                return None
            return d.strip()
        return picked
    d = ui.ask_text("Domínio" if cfg.lang == "pt-BR" else "Domain")
    return d.strip() if d and d.strip() else None
