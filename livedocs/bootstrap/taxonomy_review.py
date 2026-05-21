"""Bootstrap phase 3 — interactive taxonomy review.

The user reviews the proposed Taxonomy and can rename, merge, remove, add,
or edit code anchors before approving. Non-interactive callers (CI, piped
stdin) skip the loop and approve as-is.

Returns the (possibly modified) Taxonomy on approval, or None if the user
quit without approving — the orchestrator translates that into exit 130.

# Ações Capability→Article

Antes de aprovar, o usuário pode quebrar capabilities grandes em
sub-artigos. Três ações novas:

  [i] inspecionar capacidade   — zero IA, mostra anchors + rotas/models do cache
  [s] split assistido          — 1 chamada Claude propõe N articles
  [A] gerenciar articles       — sub-menu manual (renomear/+/-/mover)

Capacidade sempre tem ≥ 1 article após aprovação. A migração v1→v2 já
garante isso ao carregar; só removemos no [A] se sobrar pelo menos 1.
"""

from __future__ import annotations

import fnmatch
import glob
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

from livedocs import ui
from livedocs.agent import AgentError, ClaudeAgent
from livedocs.bootstrap.state import (
    LIVEDOCS_DIR_NAME,
    Article,
    Capability,
    Journey,
    Taxonomy,
)
from livedocs.i18n import t

_SPLIT_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "split_capability.md"


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
        n_art = len(c.articles)
        suffix = f"  [muted]({n_art} artigo{'s' if n_art != 1 else ''})[/muted]" if n_art else ""
        ui.console.print(f"  {i:>2}. [accent]{c.slug}[/accent]  \"{c.title}\"{suffix}")
        if c.summary:
            ui.console.print(f"      [muted]{c.summary}[/muted]")
        for a in c.articles:
            marker = " [muted](intro)[/muted]" if a.is_intro else ""
            ui.console.print(f"      └─ [accent]{a.slug}[/accent]  \"{a.title}\"{marker}")
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
        if c.articles:
            lines.append("- artigos:")
            for a in c.articles:
                tag = " (intro)" if a.is_intro else ""
                lines.append(f"  - `{a.slug}` — {a.title}{tag}")
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
# Interactive ops — capability-level
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
    # Merge articles: keep A's, append B's that don't collide on slug.
    existing = {a.slug for a in cap_a.articles}
    for art in cap_b.articles:
        if art.slug not in existing:
            cap_a.articles.append(art)
            existing.add(art.slug)
    # Rewrite journey refs.
    for j in tax.journeys:
        j.capability_refs = [cap_a.slug if r == cap_b.slug else r for r in j.capability_refs]
    tax.capabilities.pop(b)


def _do_remove(tax: Taxonomy) -> None:
    idx = _pick_capability(tax, "Remover qual capacidade?")
    if idx is None:
        return
    removed = tax.capabilities.pop(idx)
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
    slug_clean = slug.strip()
    title_clean = (title or slug).strip()
    summary_clean = (summary or "").strip()
    tax.capabilities.append(Capability(
        slug=slug_clean,
        title=title_clean,
        summary=summary_clean,
        code_anchors=anchors,
        # Mantém invariante len(articles) >= 1.
        articles=[Article(
            slug="introducao",
            title=title_clean,
            summary=summary_clean,
            is_intro=True,
            code_anchors=anchors,
        )],
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
# [i] Inspect capability — zero IA
# ---------------------------------------------------------------------------

def _load_cache_json(repo_root: Path, name: str) -> list[dict] | dict | None:
    p = repo_root / LIVEDOCS_DIR_NAME / "cache" / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _anchor_matches(file_path: str, anchors: list[str]) -> bool:
    return any(fnmatch.fnmatch(file_path, a) for a in anchors)


def _count_files_for_anchor(repo_root: Path, anchor: str) -> int:
    """Count files under repo_root matching the glob `anchor`. Bounded by 10k."""
    try:
        # Use glob with recursive=True so `**` is honored.
        pattern = str(repo_root / anchor)
        hits = glob.glob(pattern, recursive=True)
        # Filter out directories.
        n = 0
        for h in hits:
            if Path(h).is_file():
                n += 1
                if n >= 10000:
                    break
        return n
    except OSError:
        return 0


def _do_inspect(tax: Taxonomy, repo_root: Path) -> None:
    idx = _pick_capability(tax, "Inspecionar qual capacidade?")
    if idx is None:
        return
    cap = tax.capabilities[idx]

    routes = _load_cache_json(repo_root, "routes.json") or []
    models = _load_cache_json(repo_root, "models.json") or []
    graph = _load_cache_json(repo_root, "graph.json")

    matching_routes = [
        r for r in routes
        if isinstance(r, dict) and _anchor_matches(str(r.get("file", "")), cap.code_anchors)
    ]
    matching_models = [
        m for m in models
        if isinstance(m, dict) and _anchor_matches(str(m.get("file", "")), cap.code_anchors)
    ]

    ui.console.print()
    ui.console.print(f"[brand]{cap.slug}[/brand] — \"{cap.title}\"")
    if cap.summary:
        ui.console.print(f"  [muted]{cap.summary}[/muted]")
    ui.console.print()
    ui.console.print("  code_anchors:")
    if not cap.code_anchors:
        ui.console.print("    [muted](nenhum)[/muted]")
    for a in cap.code_anchors:
        n = _count_files_for_anchor(repo_root, a)
        ui.console.print(f"    - `{a}`  [muted]({n} arquivo{'s' if n != 1 else ''})[/muted]")
    ui.console.print()
    ui.console.print(f"  Rotas casando ({len(matching_routes)}):")
    for r in matching_routes[:20]:
        ui.console.print(f"    - {r.get('path', '')}  [muted]{r.get('file', '')}[/muted]")
    if len(matching_routes) > 20:
        ui.console.print(f"    [muted]… +{len(matching_routes) - 20} mais[/muted]")
    ui.console.print()
    ui.console.print(f"  Models tocados ({len(matching_models)}):")
    names = sorted({m.get("name", "?") for m in matching_models})
    if names:
        ui.console.print("    " + ", ".join(names[:30]))
    else:
        ui.console.print("    [muted](nenhum)[/muted]")
    if isinstance(graph, dict):
        nodes = graph.get("nodes") or []
        ui.console.print()
        ui.console.print(f"  Grafo: {len(nodes)} nó(s) totais (top 5):")
        for n in nodes[:5]:
            if isinstance(n, dict):
                ui.console.print(f"    - {n.get('id', n.get('name', '?'))}")
    ui.console.print()
    ui.console.print(f"  Artigos atuais ({len(cap.articles)}):")
    for a in cap.articles:
        tag = " (intro)" if a.is_intro else ""
        ui.console.print(f"    - `{a.slug}` — {a.title}{tag}")
    ui.console.print()


# ---------------------------------------------------------------------------
# [s] Split assistido — 1 chamada Claude
# ---------------------------------------------------------------------------

def _render_split_prompt(
    *,
    capability: Capability,
    routes: list[dict],
    models: list[dict],
    graph_nodes: list[str],
    guidance_text: str,
    lang: str,
) -> str:
    template_text = _SPLIT_PROMPT_PATH.read_text(encoding="utf-8")
    template = Template(template_text, autoescape=False, keep_trailing_newline=True)  # noqa: S701
    return template.render(
        capability=capability,
        routes=routes,
        models=models,
        graph_nodes=graph_nodes,
        guidance_text=guidance_text,
        lang=lang,
    )


def split_capability(
    capability: Capability,
    repo_root: Path,
    guidance_text: str,
    lang: str = "pt-BR",
    agent: Any | None = None,
) -> list[Article] | None:
    """Ask Claude to propose 2-7 articles for the capability.

    Retorna a lista de articles propostos (sem mutar ainda) ou None se
    a chamada falhar / JSON inválido.
    """
    routes = _load_cache_json(repo_root, "routes.json") or []
    models = _load_cache_json(repo_root, "models.json") or []
    graph = _load_cache_json(repo_root, "graph.json")

    matching_routes = [
        r for r in routes
        if isinstance(r, dict) and _anchor_matches(str(r.get("file", "")), capability.code_anchors)
    ]
    matching_models = [
        m for m in models
        if isinstance(m, dict) and _anchor_matches(str(m.get("file", "")), capability.code_anchors)
    ]
    graph_nodes: list[str] = []
    if isinstance(graph, dict):
        for n in (graph.get("nodes") or [])[:20]:
            if isinstance(n, dict):
                graph_nodes.append(str(n.get("id", n.get("name", ""))))

    if agent is None:
        agent = ClaudeAgent(repo_root=repo_root, lang=lang)

    prompt = "# Task: split-capability\n\n" + _render_split_prompt(
        capability=capability,
        routes=matching_routes,
        models=matching_models,
        graph_nodes=graph_nodes,
        guidance_text=guidance_text,
        lang=lang,
    )

    try:
        result = agent.call(
            prompt,
            expect_json=True,
            timeout=300,
            allowed_tools=["Read"],
        )
    except AgentError as e:
        ui.warn(f"[split] chamada falhou: {e}")
        return None

    if result.is_error or result.json_data is None:
        ui.warn(f"[split] JSON inválido: {result.error_message or 'no JSON'}")
        return None

    data = result.json_data if isinstance(result.json_data, dict) else {}
    raw_articles = data.get("articles") or []
    out: list[Article] = []
    for a in raw_articles:
        if not isinstance(a, dict):
            continue
        slug = (a.get("slug") or "").strip()
        title = (a.get("title") or "").strip()
        if not slug or not title:
            continue
        out.append(Article(
            slug=slug,
            title=title,
            summary=(a.get("summary") or "").strip(),
            is_intro=bool(a.get("is_intro", False)),
            code_anchors=[s for s in (a.get("code_anchors") or []) if isinstance(s, str)],
        ))
    return out or None


def _show_articles_proposal(articles: list[Article]) -> None:
    ui.console.print()
    ui.console.print("[brand]Proposta de articles:[/brand]")
    for i, a in enumerate(articles, 1):
        tag = "  [muted](intro)[/muted]" if a.is_intro else ""
        ui.console.print(f"  {i:>2}. [accent]{a.slug}[/accent] — {a.title}{tag}")
        if a.summary:
            ui.console.print(f"      [muted]{a.summary}[/muted]")
        for anc in a.code_anchors:
            ui.console.print(f"      · `{anc}`")
    ui.console.print()


def _edit_proposal_loop(articles: list[Article]) -> list[Article] | None:
    """Sub-loop: [a]ceitar / [r]enomear N / [+]adicionar / [x]remover N / [c]ancelar."""
    actions = [
        ("[a] aceitar e gravar", "accept"),
        ("[r] renomear N", "rename"),
        ("[+] adicionar", "add"),
        ("[x] remover N", "remove"),
        ("[c] cancelar (descartar proposta)", "cancel"),
    ]
    while True:
        _show_articles_proposal(articles)
        choice = ui.ask_choice("O que fazer com a proposta?", actions)
        if choice is None or choice == "cancel":
            return None
        if choice == "accept":
            if not articles:
                ui.warn("Não há articles para aceitar.")
                continue
            return articles
        if choice == "rename":
            n = _pick_article_index(articles, "Renomear qual article?")
            if n is None:
                continue
            art = articles[n]
            new_slug = ui.ask_text("Novo slug", default=art.slug)
            new_title = ui.ask_text("Novo título", default=art.title)
            if new_slug:
                art.slug = new_slug.strip()
            if new_title:
                art.title = new_title.strip()
        elif choice == "add":
            new = _prompt_new_article()
            if new is not None:
                articles.append(new)
        elif choice == "remove":
            n = _pick_article_index(articles, "Remover qual article?")
            if n is None:
                continue
            articles.pop(n)


# ---------------------------------------------------------------------------
# [A] Manage articles — zero IA
# ---------------------------------------------------------------------------

def _pick_article_index(articles: list[Article], message: str) -> int | None:
    if not articles:
        ui.warn("Sem articles.")
        return None
    raw = ui.ask_text(f"{message} (1-{len(articles)})")
    if not raw:
        return None
    try:
        idx = int(raw.strip()) - 1
    except ValueError:
        ui.warn("Número inválido.")
        return None
    if not (0 <= idx < len(articles)):
        ui.warn("Fora de faixa.")
        return None
    return idx


def _prompt_new_article() -> Article | None:
    slug = ui.ask_text("Slug do novo article (kebab-case)")
    if not slug:
        return None
    title = ui.ask_text("Título", default=slug.replace("-", " ").title())
    summary = ui.ask_text("Resumo (uma linha)", default="")
    anchors_raw = ui.ask_text("code_anchors separados por vírgula (opcional)", default="")
    anchors = [a.strip() for a in (anchors_raw or "").split(",") if a.strip()]
    intro = ui.ask_choice("É o article introdutório (intro)?", [("não", "no"), ("sim", "yes")])
    return Article(
        slug=slug.strip(),
        title=(title or slug).strip(),
        summary=(summary or "").strip(),
        is_intro=(intro == "yes"),
        code_anchors=anchors,
    )


def _list_articles(cap: Capability) -> None:
    ui.console.print()
    ui.console.print(f"[brand]{cap.slug}[/brand] · {len(cap.articles)} article(s):")
    for i, a in enumerate(cap.articles, 1):
        tag = "  [muted](intro)[/muted]" if a.is_intro else ""
        ui.console.print(f"  {i:>2}. [accent]{a.slug}[/accent] — {a.title}{tag}")
        if a.code_anchors:
            ui.console.print(f"      [muted]{', '.join(a.code_anchors)}[/muted]")
    ui.console.print()


def _manage_articles_loop(cap: Capability) -> None:
    actions = [
        ("[l] listar", "list"),
        ("[r] renomear N", "rename"),
        ("[x] remover N", "remove"),
        ("[+] adicionar", "add"),
        ("[m] mover âncora", "move_anchor"),
        ("[i] toggle intro de N", "toggle_intro"),
        ("[v] voltar", "back"),
    ]
    while True:
        _list_articles(cap)
        choice = ui.ask_choice(f"Gerenciando articles de '{cap.slug}'", actions)
        if choice is None or choice == "back":
            return
        if choice == "list":
            continue
        if choice == "rename":
            n = _pick_article_index(cap.articles, "Renomear qual article?")
            if n is None:
                continue
            art = cap.articles[n]
            new_slug = ui.ask_text("Novo slug", default=art.slug)
            new_title = ui.ask_text("Novo título", default=art.title)
            if new_slug:
                art.slug = new_slug.strip()
            if new_title:
                art.title = new_title.strip()
        elif choice == "remove":
            if len(cap.articles) <= 1:
                ui.warn("Capacidade precisa de ≥ 1 article. Não é possível remover o último.")
                continue
            n = _pick_article_index(cap.articles, "Remover qual article?")
            if n is None:
                continue
            cap.articles.pop(n)
        elif choice == "add":
            new = _prompt_new_article()
            if new is None:
                continue
            if any(a.slug == new.slug for a in cap.articles):
                ui.warn(f"Slug `{new.slug}` já existe nesta capacidade.")
                continue
            cap.articles.append(new)
        elif choice == "toggle_intro":
            n = _pick_article_index(cap.articles, "Toggle intro de qual article?")
            if n is None:
                continue
            cap.articles[n].is_intro = not cap.articles[n].is_intro
        elif choice == "move_anchor":
            _move_anchor_flow(cap)


def _move_anchor_flow(cap: Capability) -> None:
    """Pick a source (capability ou outro article) e destino para uma âncora."""
    sources: list[tuple[str, list[str], str]] = []
    if cap.code_anchors:
        sources.append((f"capability `{cap.slug}`", cap.code_anchors, "__capability__"))
    for a in cap.articles:
        if a.code_anchors:
            sources.append((f"article `{a.slug}`", a.code_anchors, a.slug))
    if not sources:
        ui.warn("Nenhuma âncora para mover.")
        return

    src_choice = ui.ask_choice(
        "Mover âncora de onde?",
        [(label, key) for label, _anchors, key in sources],
    )
    if src_choice is None:
        return
    src_anchors = next((anc for _l, anc, k in sources if k == src_choice), [])
    if not src_anchors:
        return

    anchor_choice = ui.ask_choice(
        "Qual âncora?",
        [(a, a) for a in src_anchors],
    )
    if anchor_choice is None:
        return

    # Pick destination article.
    dest_choice = ui.ask_choice(
        "Mover para qual article?",
        [(f"`{a.slug}` — {a.title}", a.slug) for a in cap.articles],
    )
    if dest_choice is None:
        return

    # Remove from source.
    if src_choice == "__capability__":
        cap.code_anchors = [a for a in cap.code_anchors if a != anchor_choice]
    else:
        for art in cap.articles:
            if art.slug == src_choice:
                art.code_anchors = [a for a in art.code_anchors if a != anchor_choice]

    # Append to dest.
    for art in cap.articles:
        if art.slug == dest_choice:
            if anchor_choice not in art.code_anchors:
                art.code_anchors.append(anchor_choice)
            break


def _do_split(tax: Taxonomy, repo_root: Path, guidance_text: str, lang: str) -> None:
    idx = _pick_capability(tax, "Split assistido — qual capacidade?")
    if idx is None:
        return
    cap = tax.capabilities[idx]
    ui.info(f"Chamando IA para propor split de `{cap.slug}`…")
    proposal = split_capability(cap, repo_root, guidance_text, lang=lang)
    if proposal is None:
        ui.warn("Sem proposta utilizável; nada alterado.")
        return
    edited = _edit_proposal_loop(list(proposal))
    if edited is None:
        ui.info("Proposta descartada.")
        return
    cap.articles = edited
    ui.success(f"`{cap.slug}` agora tem {len(edited)} article(s).")


def _do_manage(tax: Taxonomy) -> None:
    idx = _pick_capability(tax, "Gerenciar articles de qual capacidade?")
    if idx is None:
        return
    _manage_articles_loop(tax.capabilities[idx])


# ---------------------------------------------------------------------------
# Top-level loop
# ---------------------------------------------------------------------------

_ACTIONS: list[tuple[str, str]] = [
    ("[i] inspecionar capacidade", "inspect"),
    ("[s] split assistido", "split"),
    ("[A] gerenciar articles", "manage"),
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
    guidance_text: str = "",
    lang: str = "pt-BR",
) -> Taxonomy | None:
    """Interactive review of the proposed taxonomy.

    Returns the (possibly mutated) Taxonomy with `approved_at` set on
    success, or None if the user quit without approving.

    With `non_interactive=True` or `auto_accept=True` the function approves
    immediately without prompting (used by CI and pipe-mode). Ensures every
    capability has ≥ 1 article (auto-creates introducao if missing).
    """
    _ensure_articles_invariant(taxonomy)

    if non_interactive or auto_accept:
        taxonomy.approved_at = _now_iso()
        return taxonomy

    while True:
        _render_tree(taxonomy)
        choice = ui.ask_choice(t("bootstrap_review_actions"), _ACTIONS)
        if choice is None or choice == "quit":
            return None
        if choice == "approve":
            _ensure_articles_invariant(taxonomy)
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
        elif choice == "inspect":
            _do_inspect(taxonomy, repo_root)
        elif choice == "split":
            _do_split(taxonomy, repo_root, guidance_text, lang)
        elif choice == "manage":
            _do_manage(taxonomy)
        elif choice == "preview":
            path = _write_preview(taxonomy, repo_root)
            ui.info(t("bootstrap_review_preview_written", path=path))


def _ensure_articles_invariant(tax: Taxonomy) -> None:
    """Every capability must have ≥ 1 article. Auto-fill if needed."""
    for c in tax.capabilities:
        if not c.articles:
            c.articles = [Article(
                slug="introducao",
                title=c.title,
                summary=c.summary,
                is_intro=True,
                code_anchors=list(c.code_anchors),
            )]


__all__ = ["review_taxonomy", "split_capability"]
# Silence unused-import warnings for re-exports used by tests.
_ = Journey
