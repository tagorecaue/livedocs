"""Bootstrap phase 3 — interactive taxonomy review.

The user reviews the proposed Taxonomy and can rename, merge, remove, add,
or edit code anchors before approving. Non-interactive callers (CI, piped
stdin) skip the loop and approve as-is.

Returns the (possibly modified) Taxonomy on approval, or None if the user
quit without approving — the orchestrator translates that into exit 130.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from livedocs import ui
from livedocs.bootstrap.state import Capability, Journey, Taxonomy
from livedocs.i18n import t

# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _render_tree(tax: Taxonomy) -> None:
    ui.console.print()
    ui.console.print(
        f"[brand]Taxonomia[/brand] — {len(tax.capabilities)} capacidade(s), "
        f"{len(tax.journeys)} jornada(s)"
    )
    ui.console.print()
    ui.console.print("[brand]CAPACIDADES[/brand]")
    for i, c in enumerate(tax.capabilities, 1):
        ui.console.print(f"  {i:>2}. [accent]{c.slug}[/accent]  \"{c.title}\"")
        if c.summary:
            ui.console.print(f"      [muted]{c.summary}[/muted]")
    ui.console.print()
    ui.console.print("[brand]JORNADAS[/brand]")
    if not tax.journeys:
        ui.console.print("  [muted](nenhuma)[/muted]")
    for i, j in enumerate(tax.journeys, 1):
        refs = ", ".join(j.capability_refs) or "(sem refs)"
        ui.console.print(f"  J{i}. [accent]{j.slug}[/accent]  \"{j.title}\"  [muted]→ {refs}[/muted]")
    ui.console.print()


def _write_preview(tax: Taxonomy, repo_root: Path) -> Path:
    """Write a human-readable preview to .livedocs/menu-proposed.md."""
    path = repo_root / ".livedocs" / "menu-proposed.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = ["# Taxonomia proposta", ""]
    lines.append("## Capacidades")
    lines.append("")
    for c in tax.capabilities:
        lines.append(f"### {c.title}")
        lines.append(f"- slug: `{c.slug}`")
        if c.summary:
            lines.append(f"- resumo: {c.summary}")
        if c.code_anchors:
            lines.append("- code_anchors:")
            for a in c.code_anchors:
                lines.append(f"  - `{a}`")
        lines.append("")
    lines.append("## Jornadas")
    lines.append("")
    for j in tax.journeys:
        lines.append(f"### {j.title}")
        lines.append(f"- slug: `{j.slug}`")
        if j.summary:
            lines.append(f"- resumo: {j.summary}")
        if j.capability_refs:
            lines.append("- capacidades: " + ", ".join(f"`{r}`" for r in j.capability_refs))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Interactive ops
# ---------------------------------------------------------------------------

def _pick_capability(tax: Taxonomy, message: str) -> int | None:
    if not tax.capabilities:
        ui.warn("Nenhuma capacidade para escolher.")
        return None
    raw = ui.ask_text(f"{message} (1-{len(tax.capabilities)})")
    if not raw:
        return None
    try:
        idx = int(raw.strip()) - 1
    except ValueError:
        ui.warn("Número inválido.")
        return None
    if not (0 <= idx < len(tax.capabilities)):
        ui.warn("Fora de faixa.")
        return None
    return idx


def _do_rename(tax: Taxonomy) -> None:
    idx = _pick_capability(tax, "Renomear qual capacidade?")
    if idx is None:
        return
    cap = tax.capabilities[idx]
    new_title = ui.ask_text("Novo título", default=cap.title)
    new_slug = ui.ask_text("Novo slug (kebab-case)", default=cap.slug)
    if new_title:
        cap.title = new_title.strip()
    if new_slug:
        cap.slug = new_slug.strip()


def _do_merge(tax: Taxonomy) -> None:
    a = _pick_capability(tax, "Mesclar — capacidade A")
    if a is None:
        return
    b = _pick_capability(tax, "Mesclar — capacidade B (será absorvida)")
    if b is None or a == b:
        ui.warn("Escolha dois itens diferentes.")
        return
    cap_a = tax.capabilities[a]
    cap_b = tax.capabilities[b]
    cap_a.code_anchors = list(dict.fromkeys([*cap_a.code_anchors, *cap_b.code_anchors]))
    if cap_b.summary and not cap_a.summary:
        cap_a.summary = cap_b.summary
    # Rewrite journey refs.
    for j in tax.journeys:
        j.capability_refs = [cap_a.slug if r == cap_b.slug else r for r in j.capability_refs]
    tax.capabilities.pop(b)


def _do_remove(tax: Taxonomy) -> None:
    idx = _pick_capability(tax, "Remover qual capacidade?")
    if idx is None:
        return
    removed = tax.capabilities.pop(idx)
    # Cleanup refs in journeys.
    for j in tax.journeys:
        j.capability_refs = [r for r in j.capability_refs if r != removed.slug]


def _do_add(tax: Taxonomy) -> None:
    slug = ui.ask_text("Slug (kebab-case)")
    if not slug:
        return
    title = ui.ask_text("Título", default=slug.replace("-", " ").title())
    summary = ui.ask_text("Resumo (uma linha)", default="")
    anchors_raw = ui.ask_text("code_anchors separados por vírgula (opcional)", default="")
    anchors = [a.strip() for a in (anchors_raw or "").split(",") if a.strip()]
    tax.capabilities.append(Capability(
        slug=slug.strip(),
        title=(title or slug).strip(),
        summary=(summary or "").strip(),
        code_anchors=anchors,
    ))


def _do_edit_anchors(tax: Taxonomy) -> None:
    idx = _pick_capability(tax, "Editar âncoras de qual capacidade?")
    if idx is None:
        return
    cap = tax.capabilities[idx]
    current = ", ".join(cap.code_anchors)
    raw = ui.ask_text("Novos code_anchors (separados por vírgula)", default=current)
    if raw is None:
        return
    cap.code_anchors = [a.strip() for a in raw.split(",") if a.strip()]


# ---------------------------------------------------------------------------
# Top-level loop
# ---------------------------------------------------------------------------

_ACTIONS: list[tuple[str, str]] = [
    ("[a] aprovar tudo", "approve"),
    ("[r] renomear", "rename"),
    ("[m] mesclar", "merge"),
    ("[x] remover", "remove"),
    ("[+] adicionar", "add"),
    ("[e] editar âncoras", "anchors"),
    ("[p] preview .md", "preview"),
    ("[q] sair", "quit"),
]


def review_taxonomy(
    taxonomy: Taxonomy,
    repo_root: Path,
    non_interactive: bool = False,
    auto_accept: bool = False,
) -> Taxonomy | None:
    """Interactive review of the proposed taxonomy.

    Returns the (possibly mutated) Taxonomy with `approved_at` set on
    success, or None if the user quit without approving.

    With `non_interactive=True` or `auto_accept=True` the function approves
    immediately without prompting (used by CI and pipe-mode).
    """
    if non_interactive or auto_accept:
        taxonomy.approved_at = _now_iso()
        return taxonomy

    while True:
        _render_tree(taxonomy)
        choice = ui.ask_choice(t("bootstrap_review_actions"), _ACTIONS)
        if choice is None or choice == "quit":
            return None
        if choice == "approve":
            taxonomy.approved_at = _now_iso()
            ui.success(t(
                "bootstrap_review_approved",
                caps=len(taxonomy.capabilities),
                jrn=len(taxonomy.journeys),
            ))
            return taxonomy
        if choice == "rename":
            _do_rename(taxonomy)
        elif choice == "merge":
            _do_merge(taxonomy)
        elif choice == "remove":
            _do_remove(taxonomy)
        elif choice == "add":
            _do_add(taxonomy)
        elif choice == "anchors":
            _do_edit_anchors(taxonomy)
        elif choice == "preview":
            path = _write_preview(taxonomy, repo_root)
            ui.info(t("bootstrap_review_preview_written", path=path))


__all__ = ["review_taxonomy"]
# Silence unused-import warnings for re-exports used by tests.
_ = Journey
