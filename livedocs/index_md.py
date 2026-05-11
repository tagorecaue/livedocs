"""Manage `_index.md` files per domain (D.6).

Each domain folder gets an `_index.md` that:
  1. Names the domain
  2. Lists every guide pair in the domain (produto + tech links)
  3. Captures the "next recommendation" — what to document next

# Why this matters

The recommendation is **metadata**. It never belongs inside an individual
guide (produto.md / tech.md) because:
  - Guides are content readers consume; recommendations are author-state
  - Recommendations change frequently; guide bodies should be stable
  - A guide may serve multiple navigation paths

`_index.md` is the canonical place for nav metadata.

# Update strategy

livedocs is **conservative** with `_index.md`:
  - We own and rewrite the **`## Guias deste domínio`** section (the
    auto-generated catalog of produto+tech pairs)
  - We own and rewrite the **`## Próxima recomendação para este domínio`**
    section (the next-step pointer)
  - We **preserve everything else** the human wrote: opening paragraph,
    `## Guias planejados`, `## Vocabulário`, `## Material de apoio`, etc.

If `_index.md` doesn't exist yet, we create one from a minimal template.

# Idempotency

Re-running the update with the same state should produce byte-identical
output. We achieve this by:
  - Sorting guide entries deterministically (by slug)
  - Using stable section markers (### per guide)
  - Stripping trailing whitespace consistently
"""

from __future__ import annotations

import re
from pathlib import Path

from livedocs.models import InterviewState, ProjectConfig
from livedocs.state import guides_root

# Section anchors we own. Everything else in the file is preserved verbatim.
GUIDES_SECTION_TITLE_PT = "## Guias deste domínio"
GUIDES_SECTION_TITLE_EN = "## Guides in this domain"
NEXT_SECTION_TITLE_PT = "## Próxima recomendação para este domínio"
NEXT_SECTION_TITLE_EN = "## Next recommendation for this domain"


# ---------------------------------------------------------------------------
# Section detection (anchored to either pt-BR or en titles)
# ---------------------------------------------------------------------------

def _section_re(title_pt: str, title_en: str) -> re.Pattern[str]:
    """Match a managed section from its title up to the next `## ` or EOF."""
    escaped = re.escape(title_pt) + "|" + re.escape(title_en)
    # (?:...) non-capturing group; (?ms) multiline+dotall.
    return re.compile(
        rf"(?ms)^(?:{escaped})\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )


_GUIDES_RE = _section_re(GUIDES_SECTION_TITLE_PT, GUIDES_SECTION_TITLE_EN)
_NEXT_RE = _section_re(NEXT_SECTION_TITLE_PT, NEXT_SECTION_TITLE_EN)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def update_domain_index(
    repo_root: Path,
    cfg: ProjectConfig,
    domain: str,
    interviews: dict[str, InterviewState],
    next_recommendation: dict | None = None,
    *,
    lang: str | None = None,
) -> Path:
    """Create or update `<docs>/<guides_subdir>/<domain>/_index.md` for a domain.

    Strategy: load existing file, replace ONLY the two sections we own
    (Guias deste domínio + Próxima recomendação), preserve everything else.
    If the file doesn't exist, write a minimal scaffold and inject our sections.

    Returns the path to the (now updated) _index.md.
    """
    domain_dir = guides_root(repo_root, cfg) / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    index_path = domain_dir / "_index.md"

    effective_lang = lang or cfg.lang
    domain_guides = sorted(
        (iv for iv in interviews.values() if iv.domain == domain),
        key=lambda i: i.slug,
    )

    if index_path.exists():
        existing = index_path.read_text(encoding="utf-8")
    else:
        existing = _scaffold(domain, effective_lang)

    new_text = _replace_managed_sections(
        existing,
        domain_guides,
        next_recommendation,
        lang=effective_lang,
    )
    index_path.write_text(new_text, encoding="utf-8")
    return index_path


def parse_next_recommendation(index_path: Path) -> dict | None:
    """Read an existing `_index.md` and extract its next-recommendation, if any.

    Used during D.5 import: pull the human-written recommendation back into
    `GlobalState.next_recommendations` so the menu can offer it.

    Returns:
        {"slug": "...", "reason": "..."} if a slug can be inferred,
        or None when the section is absent / unparseable.
    """
    if not index_path.exists():
        return None
    text = index_path.read_text(encoding="utf-8")
    section = _NEXT_RE.search(text)
    if not section:
        return None
    body = section.group(1).strip()
    if not body:
        return None

    # Try to find a markdown link or filename reference inside the section.
    # Patterns we accept:
    #   [text](./other-slug.md)
    #   [text](../other-domain/other-slug.md)
    #   `other-slug.md`
    #   **other-slug** (last-resort heuristic)
    link = re.search(r"\[([^\]]+)\]\(([^)]+\.md)\)", body)
    if link:
        target = link.group(2)
        slug = Path(target).stem.replace(".tech", "")
        return {"slug": slug, "reason": body[:500].strip()}

    inline_code = re.search(r"`([a-z0-9][\w-]+?)(?:\.md)?`", body)
    if inline_code:
        return {"slug": inline_code.group(1), "reason": body[:500].strip()}

    return None


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _replace_managed_sections(
    existing: str,
    guides: list[InterviewState],
    next_rec: dict | None,
    *,
    lang: str,
) -> str:
    """Replace the two managed sections, preserve everything else.

    If a managed section is absent, append it to the end of the file.
    Final newline normalized.
    """
    guides_block = _render_guides_section(guides, lang=lang)
    text = existing

    # Always end the replacement with a blank-line separator so subsequent
    # sections are visually separated. This also makes the function idempotent
    # (re-running on already-formatted output produces the same bytes).
    if _GUIDES_RE.search(text):
        text = _GUIDES_RE.sub(guides_block + "\n\n", text, count=1)
    else:
        text = _ensure_trailing_newlines(text) + guides_block + "\n\n"

    next_block = _render_next_section(next_rec, lang=lang)
    if next_block:
        if _NEXT_RE.search(text):
            text = _NEXT_RE.sub(next_block + "\n\n", text, count=1)
        else:
            text = _ensure_trailing_newlines(text) + next_block + "\n\n"

    # Normalize trailing whitespace: end with exactly one newline.
    return text.rstrip() + "\n"


def _render_guides_section(guides: list[InterviewState], *, lang: str) -> str:
    title = GUIDES_SECTION_TITLE_PT if lang == "pt-BR" else GUIDES_SECTION_TITLE_EN

    if not guides:
        # Empty domain — still emit the section so the file has a stable shape.
        intro = (
            "_(Nenhum guia ainda neste domínio.)_"
            if lang == "pt-BR"
            else "_(No guides in this domain yet.)_"
        )
        return f"{title}\n\n{intro}\n"

    intro = (
        "Cada tema tem **dois guias**: um para usuários do SaaS "
        "(linguagem de produto) e outro para devs/IA (com referências de código)."
        if lang == "pt-BR"
        else "Each topic ships as **two guides**: one for SaaS users "
        "(product language) and one for devs/AI (with code references)."
    )

    lines = [title, "", intro, ""]
    for iv in guides:
        heading = iv.title or iv.slug
        lines.append(f"### {heading}")
        lines.append("")
        if lang == "pt-BR":
            lines.append(
                f"- [Para usuários — linguagem de produto](./{iv.slug}.md)"
            )
            lines.append(
                f"- [Para devs e IA — referência técnica](./{iv.slug}.tech.md)"
            )
        else:
            lines.append(f"- [For users — product language](./{iv.slug}.md)")
            lines.append(f"- [For devs and AI — technical reference](./{iv.slug}.tech.md)")
        lines.append("")
    # Trim trailing blank line so the section ends clean.
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _render_next_section(next_rec: dict | None, *, lang: str) -> str:
    if not next_rec:
        return ""
    title = NEXT_SECTION_TITLE_PT if lang == "pt-BR" else NEXT_SECTION_TITLE_EN
    slug = str(next_rec.get("slug") or "").strip()
    domain = str(next_rec.get("domain") or "").strip()
    reason = str(next_rec.get("reason") or "").strip()
    if not slug:
        return ""

    if lang == "pt-BR":
        link_label = "Próximo guia recomendado"
        body_pieces = [f"> **{link_label}:** `{slug}`"]
        if domain:
            body_pieces[0] += f" (domínio `{domain}`)"
        body_pieces[0] += "."
        if reason:
            body_pieces.append("")
            body_pieces.append(f"> {reason}")
    else:
        link_label = "Recommended next guide"
        body_pieces = [f"> **{link_label}:** `{slug}`"]
        if domain:
            body_pieces[0] += f" (domain `{domain}`)"
        body_pieces[0] += "."
        if reason:
            body_pieces.append("")
            body_pieces.append(f"> {reason}")

    return f"{title}\n\n" + "\n".join(body_pieces)


def _scaffold(domain: str, lang: str) -> str:
    """Minimal _index.md template when none exists."""
    if lang == "pt-BR":
        return f"# Domínio: {domain}\n\n_(Adicione aqui um parágrafo introdutório do domínio.)_\n"
    return f"# Domain: {domain}\n\n_(Add an introductory paragraph for this domain here.)_\n"


def _ensure_trailing_newlines(text: str) -> str:
    if not text.endswith("\n\n"):
        text = text.rstrip("\n") + "\n\n"
    return text


__all__ = [
    "GUIDES_SECTION_TITLE_PT",
    "GUIDES_SECTION_TITLE_EN",
    "NEXT_SECTION_TITLE_PT",
    "NEXT_SECTION_TITLE_EN",
    "update_domain_index",
    "parse_next_recommendation",
]
