"""`livedocs init` — first-run wizard.

Detects:
- git repo
- system locale → confirms with user
- Claude Code CLI
- graphify presence
- existing `docs/` or `packages/docs/` (<Client>)
- project slug suggestion

Writes:
- <repo>/.livedocs/config.toml
- <repo>/.livedocs/.gitignore (state.toml is local-only)
"""

from __future__ import annotations

from pathlib import Path

from livedocs import detect, ui
from livedocs.i18n import (
    detect_system_locale,
    lang_label,
    set_lang,
    supported_langs,
    t,
)
from livedocs.state import (
    ProjectConfig,
    config_path,
    ensure_gitignore_for_state,
    save_config,
)

CANDIDATE_DOCS_DIRS = ["docs", "packages/docs", "documentation", "site/docs"]


def run_init(cwd: Path) -> int:
    ui.splash()

    # 1. Confirm we have a sane place to live (a git repo)
    if not detect.has_git_repo(cwd):
        ui.error(t("err_not_a_repo"))
        return 1

    # 2. Detect system locale, confirm preferred language for the *guides*
    detected_lang = detect_system_locale()
    set_lang(detected_lang)  # default our own UI to that for now

    ui.section(t("init_welcome"))
    ui.hint(t("init_lang_detected", lang=lang_label(detected_lang)))

    chosen = ui.ask_choice(
        t("init_lang_q"),
        choices=[(lang_label(lng), lng) for lng in supported_langs()],
        default=detected_lang,
    )
    if chosen is None:
        ui.warn(t("abort"))
        return 130
    set_lang(chosen)

    # 3. Project slug
    suggested_slug = detect.project_slug_suggestion(cwd)
    slug = ui.ask_text(t("init_project_name_q"), default=suggested_slug)
    if slug is None:
        ui.warn(t("abort"))
        return 130
    slug = slug.strip() or suggested_slug

    # 4. Provider — only claude-code in v0
    ui.blank()
    if detect.has_claude_code():
        version = detect.claude_code_version() or ""
        ui.success(t("init_provider_detected", provider=f"Claude Code {version}".strip()))
    else:
        ui.warn(t("init_provider_not_found"))

    # 5. Existing docs detection
    ui.blank()
    found_dir, found_count = detect.has_existing_docs(cwd, CANDIDATE_DOCS_DIRS)

    docs_dir: str
    if found_dir:
        ui.info(t("init_docs_dir_existing", path=found_dir, count=found_count))
        action = ui.ask_choice(
            t("init_docs_dir_action_q"),
            choices=[
                (t("init_docs_dir_use"), "use"),
                (t("init_docs_dir_other"), "other"),
                (t("init_docs_dir_fresh"), "fresh"),
            ],
            default="use",
        )
        if action is None:
            ui.warn(t("abort"))
            return 130

        if action == "use":
            docs_dir = found_dir
        else:
            picked = ui.ask_text(t("init_docs_dir_q"), default="docs")
            if picked is None:
                ui.warn(t("abort"))
                return 130
            docs_dir = picked.strip() or "docs"
    else:
        picked = ui.ask_text(t("init_docs_dir_q"), default="docs")
        if picked is None:
            ui.warn(t("abort"))
            return 130
        docs_dir = picked.strip() or "docs"

    # 6. Graphify — COMMENTED OUT pending real integration (would be misleading
    # to ask: cfg.use_graphify is detected but never consumed downstream).
    # Re-enable when `livedocs scan` exists and the prompt actually uses the graph.
    use_graphify = False
    # if detect.has_graphify():
    #     ui.blank()
    #     ui.info(t("init_graphify_detected"))
    #     ans = ui.ask_confirm(t("init_graphify_q"), default=False)
    #     use_graphify = bool(ans)

    # 6.5. Style (new in v0.2 D.0)
    from livedocs.skill.styles import (
        all_styles,
        copy_style_to_project,
        style_label,
    )
    ui.blank()
    ui.section(t("init_style_q"))
    ui.hint(t("init_style_hint"))
    style_choice = ui.ask_choice(
        t("init_style_q"),
        choices=[(style_label(s, chosen), s) for s in all_styles()],
        default="narrative",
    )
    if style_choice is None:
        ui.warn(t("abort"))
        return 130

    # 6.6. `guides_subdir` is now decided by the bootstrap pipeline (it picks
    # `<docs_dir>/guides/` by default). We leave it empty at init time.
    guides_subdir = ""

    # 7. Persist
    cfg = ProjectConfig(
        project_slug=slug,
        lang=chosen,
        provider="claude-code",
        docs_dir=docs_dir,
        guides_subdir=guides_subdir,
        use_graphify=use_graphify,
        style=style_choice,
    )
    save_config(cwd, cfg)
    ensure_gitignore_for_state(cwd)

    # Copy the chosen style template to <repo>/.livedocs/style.md
    style_target = cwd / ".livedocs" / "style.md"
    copy_style_to_project(style_choice, style_target)

    # Make sure docs_dir exists (we may want to write to it later)
    (cwd / docs_dir).mkdir(parents=True, exist_ok=True)

    ui.blank()
    ui.success(t("init_done", path=str(config_path(cwd).relative_to(cwd))))
    ui.hint(t("init_style_customize", path=".livedocs/style.md"))
    ui.blank()
    ui.info("Próximo passo: livedocs bootstrap")
    return 0
