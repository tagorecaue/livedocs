"""Style template management.

Three built-in styles + read of user-customized `<repo>/.livedocs/style.md`.

# Behavior

- During `livedocs init`, the user picks one of the 3 built-in templates
  (narrative / reference / tutorial). The chosen template is copied verbatim
  to `<repo>/.livedocs/style.md`.
- The user can edit `style.md` freely afterwards — livedocs respects it.
- When generating or evaluating guides, the CLI loads `style.md` (if present)
  and injects it into the agent prompt as style context.
- If `style.md` is missing (legacy projects, edge cases), the `narrative`
  template is used as fallback.

# Why 3, not more

Decision paralysis. 3 covers >95% of the target ICP without overwhelming
the init wizard. The 3 chosen are:

  - narrative: SaaS B2B operational/financial, end-user humans
  - reference: APIs/SDKs/devtools, end-user devs
  - tutorial : B2C or onboarding, conversational tone

Custom-from-scratch is intentionally not offered — the user can always delete
and rewrite style.md after init.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Literal

StyleId = Literal["narrative", "reference", "tutorial"]

DEFAULT_STYLE: StyleId = "narrative"

STYLE_LABELS_PT_BR: dict[StyleId, str] = {
    "narrative": "Narrativo de produto — prosa fluida, explica o porquê (Stripe, Linear)",
    "reference": "Técnico de referência — seco, citações de código (Stripe API, AWS, Hono)",
    "tutorial":  "Tutorial conversacional — didático, segunda pessoa (Notion help, Tailwind)",
}

STYLE_LABELS_EN: dict[StyleId, str] = {
    "narrative": "Narrative product — fluid prose, explains the why (Stripe, Linear)",
    "reference": "Technical reference — dry, code citations (Stripe API, AWS, Hono)",
    "tutorial":  "Conversational tutorial — didactic, second person (Notion help, Tailwind)",
}


def all_styles() -> list[StyleId]:
    """Return the canonical list of built-in style ids."""
    return ["narrative", "reference", "tutorial"]


def style_label(style: StyleId, lang: str) -> str:
    table = STYLE_LABELS_PT_BR if lang == "pt-BR" else STYLE_LABELS_EN
    return table.get(style, style)


def builtin_style_content(style: StyleId) -> str:
    """Return the raw text of a built-in style template."""
    # Access the bundled file via importlib.resources so it works after pip install too.
    files = resources.files("livedocs.skill.styles")
    return (files / f"{style}.md").read_text(encoding="utf-8")


def copy_style_to_project(style: StyleId, target: Path) -> Path:
    """Copy a built-in template into <repo>/.livedocs/style.md.

    Idempotent: if `target` already exists, leave it alone (the user's
    customizations stay intact).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(builtin_style_content(style), encoding="utf-8")
    return target


def load_project_style(repo_root: Path) -> str:
    """Return the style content for the current project.

    Loads `<repo>/.livedocs/style.md` when present; otherwise falls back to
    the default built-in. The returned string is meant to be appended to the
    `PROMPT_GENERATE_GUIDES` and the post-gen evaluators.
    """
    candidate = repo_root / ".livedocs" / "style.md"
    if candidate.exists():
        try:
            return candidate.read_text(encoding="utf-8")
        except OSError:
            pass
    return builtin_style_content(DEFAULT_STYLE)
