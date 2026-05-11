"""Tests for D.6 — index_md (parse + update + scaffold + integration with import)."""

from __future__ import annotations

from pathlib import Path

from livedocs.import_existing import scan_existing_guides
from livedocs.index_md import (
    parse_next_recommendation,
    update_domain_index,
)
from livedocs.models import GlobalState, InterviewState, ProjectConfig

# ---------------------------------------------------------------------------
# parse_next_recommendation
# ---------------------------------------------------------------------------

class TestParseNextRecommendation:
    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        assert parse_next_recommendation(tmp_path / "nope.md") is None

    def test_returns_none_when_section_missing(self, tmp_path: Path) -> None:
        p = tmp_path / "_index.md"
        p.write_text("# Domínio: x\n\nQualquer texto.\n", encoding="utf-8")
        assert parse_next_recommendation(p) is None

    def test_parses_markdown_link_target(self, tmp_path: Path) -> None:
        p = tmp_path / "_index.md"
        p.write_text(
            """# Domínio: contratos

## Próxima recomendação para este domínio

> Recomendado seguir para [Configurações financeiras do projeto](../projetos/configuracoes-financeiras.md). Razão: várias regras citadas vivem nesse painel.
""",
            encoding="utf-8",
        )
        rec = parse_next_recommendation(p)
        assert rec is not None
        assert rec["slug"] == "configuracoes-financeiras"
        assert "regras citadas" in rec["reason"]

    def test_parses_relative_same_dir_link(self, tmp_path: Path) -> None:
        p = tmp_path / "_index.md"
        p.write_text(
            """# Domínio: x

## Próxima recomendação para este domínio

> Próximo: [Algo](./outro-slug.md).
""",
            encoding="utf-8",
        )
        rec = parse_next_recommendation(p)
        assert rec is not None
        assert rec["slug"] == "outro-slug"

    def test_parses_inline_code_fallback(self, tmp_path: Path) -> None:
        p = tmp_path / "_index.md"
        p.write_text(
            """# Domínio: x

## Próxima recomendação para este domínio

> Próximo guia: `cadastramento-de-lotes`. Razão: vinculado ao financeiro.
""",
            encoding="utf-8",
        )
        rec = parse_next_recommendation(p)
        assert rec is not None
        assert rec["slug"] == "cadastramento-de-lotes"

    def test_strips_tech_suffix_from_target(self, tmp_path: Path) -> None:
        """If the link points to <slug>.tech.md, we still resolve to <slug>."""
        p = tmp_path / "_index.md"
        p.write_text(
            """# Domínio: x

## Próxima recomendação para este domínio

> [Referência técnica](./foo.tech.md).
""",
            encoding="utf-8",
        )
        rec = parse_next_recommendation(p)
        assert rec is not None
        assert rec["slug"] == "foo"

    def test_works_with_english_section_title(self, tmp_path: Path) -> None:
        p = tmp_path / "_index.md"
        p.write_text(
            """# Domain: x

## Next recommendation for this domain

> Next: [Onboarding](./onboarding.md).
""",
            encoding="utf-8",
        )
        rec = parse_next_recommendation(p)
        assert rec is not None
        assert rec["slug"] == "onboarding"


# ---------------------------------------------------------------------------
# update_domain_index
# ---------------------------------------------------------------------------

def _make_iv(slug: str, domain: str, title: str = "", status: str = "reviewed") -> InterviewState:
    return InterviewState(slug=slug, domain=domain, title=title or slug, status=status)


class TestUpdateDomainIndexFresh:
    """When _index.md doesn't exist yet."""

    def test_creates_file_with_scaffold_and_guides(
        self, tmp_project: tuple[Path, ProjectConfig]
    ) -> None:
        repo, cfg = tmp_project
        interviews = {
            "ciclo-de-vida": _make_iv("ciclo-de-vida", "contratos", "Ciclo de vida"),
            "renovacao": _make_iv("renovacao", "contratos", "Renovação"),
        }
        path = update_domain_index(repo, cfg, "contratos", interviews)
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        # The scaffold header should be there
        assert "Domain: contratos" in text or "Domínio: contratos" in text
        # Both guides catalogued
        assert "ciclo-de-vida.md" in text
        assert "renovacao.md" in text
        # Tech links also present
        assert "ciclo-de-vida.tech.md" in text
        assert "renovacao.tech.md" in text

    def test_no_guides_emits_placeholder_section(
        self, tmp_project: tuple[Path, ProjectConfig]
    ) -> None:
        repo, cfg = tmp_project
        path = update_domain_index(repo, cfg, "empty-domain", interviews={})
        text = path.read_text(encoding="utf-8")
        # Guides section present but empty
        assert "Guides in this domain" in text or "Guias deste domínio" in text
        assert "No guides" in text or "Nenhum guia" in text

    def test_writes_next_recommendation_when_provided(
        self, tmp_project: tuple[Path, ProjectConfig]
    ) -> None:
        repo, cfg = tmp_project
        interviews = {"a": _make_iv("a", "x")}
        rec = {"slug": "b-next", "domain": "x", "reason": "natural follow-up"}
        path = update_domain_index(repo, cfg, "x", interviews, next_recommendation=rec)
        text = path.read_text(encoding="utf-8")
        assert "b-next" in text
        assert "natural follow-up" in text


class TestUpdateDomainIndexPreservesContent:
    """The killer feature: keep human-written sections intact."""

    def test_preserves_intro_paragraph_and_planned_guides(
        self, tmp_project: tuple[Path, ProjectConfig]
    ) -> None:
        repo, cfg = tmp_project
        # Manually create a rich _index.md, then update it.
        existing_dir = repo / "docs" / "contratos"
        existing_dir.mkdir(parents=True)
        existing = existing_dir / "_index.md"
        existing.write_text(
            """# Domínio: contratos

O contrato é a entidade central. Aqui orbitam parcelas, pagamentos, etc.

## Guides in this domain

(stale catalog written by hand)

## Guias planejados

- **Renovação detalhada** — fluxos de UI e regras de desconto.
- **Negociações ativas** — boletos de quitação.

## Vocabulário do domínio

Ver [`/_meta/glossary.md`](../../_meta/glossary.md).

## Next recommendation for this domain

> stale recommendation
""",
            encoding="utf-8",
        )

        interviews = {
            "ciclo-de-vida": _make_iv("ciclo-de-vida", "contratos", "Ciclo de vida"),
        }
        update_domain_index(
            repo,
            cfg,
            "contratos",
            interviews,
            next_recommendation={"slug": "renovacao", "domain": "contratos", "reason": "fresh"},
        )
        text = existing.read_text(encoding="utf-8")

        # Lead paragraph preserved
        assert "entidade central" in text
        # Human-written planned-guides section preserved
        assert "## Guias planejados" in text
        assert "Renovação detalhada" in text
        # Vocabulário preserved
        assert "Vocabulário do domínio" in text
        assert "glossary.md" in text
        # Stale catalog REPLACED with current
        assert "ciclo-de-vida.md" in text
        assert "(stale catalog written by hand)" not in text
        # Stale recommendation REPLACED with current
        assert "renovacao" in text
        assert "stale recommendation" not in text

    def test_idempotent_repeated_calls_converge(
        self, tmp_project: tuple[Path, ProjectConfig]
    ) -> None:
        repo, cfg = tmp_project
        interviews = {"a": _make_iv("a", "x"), "b": _make_iv("b", "x")}
        rec = {"slug": "c", "domain": "x", "reason": "..."}
        path = update_domain_index(repo, cfg, "x", interviews, next_recommendation=rec)
        first = path.read_text(encoding="utf-8")
        # Run again with identical inputs
        update_domain_index(repo, cfg, "x", interviews, next_recommendation=rec)
        second = path.read_text(encoding="utf-8")
        assert first == second

    def test_appends_managed_sections_to_existing_file_without_them(
        self, tmp_project: tuple[Path, ProjectConfig]
    ) -> None:
        repo, cfg = tmp_project
        existing_dir = repo / "docs" / "x"
        existing_dir.mkdir(parents=True)
        existing = existing_dir / "_index.md"
        existing.write_text(
            "# Domain: x\n\nWritten by hand, no catalog yet.\n",
            encoding="utf-8",
        )
        interviews = {"a": _make_iv("a", "x")}
        update_domain_index(
            repo, cfg, "x", interviews,
            next_recommendation={"slug": "next", "reason": "go here"},
        )
        text = existing.read_text(encoding="utf-8")
        # Original line preserved
        assert "Written by hand" in text
        # Both managed sections appended
        assert "a.md" in text  # guides section
        assert "next" in text  # recommendation section


# ---------------------------------------------------------------------------
# Round-trip with import_existing — D.5 + D.6 integration
# ---------------------------------------------------------------------------

class TestImportRoundtrip:
    def test_import_picks_up_next_recommendation_from_index(
        self, tmp_path: Path
    ) -> None:
        """When init scans a project with an existing _index.md that has a
        recommendation, it should land in state.next_recommendations."""
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="")
        d = tmp_path / "docs" / "financeiro"
        d.mkdir(parents=True)
        (d / "pagamento.md").write_text(
            "---\nslug: pagamento\ndomain: financeiro\nstatus: reviewed\n---\n\n# Pagamento\n",
            encoding="utf-8",
        )
        (d / "_index.md").write_text(
            """# Domínio: financeiro

## Próxima recomendação para este domínio

> Próximo: [Cadastramento de lotes](./cadastramento-de-lotes.md). Razão: comissões dependem de configuração de lote.
""",
            encoding="utf-8",
        )
        state = GlobalState()
        scan_existing_guides(tmp_path, cfg, state)

        # Guide imported normally
        assert "pagamento" in state.interviews
        # Recommendation extracted
        assert len(state.next_recommendations) == 1
        rec = state.next_recommendations[0]
        assert rec.slug == "cadastramento-de-lotes"
        assert rec.domain == "financeiro"
        assert "comissões" in rec.reason
        assert rec.suggested_by == "(imported from _index.md)"

    def test_idempotent_does_not_duplicate_recommendations(
        self, tmp_path: Path
    ) -> None:
        cfg = ProjectConfig(project_slug="x", docs_dir="docs", guides_subdir="")
        d = tmp_path / "docs" / "x"
        d.mkdir(parents=True)
        (d / "_index.md").write_text(
            "# Domínio: x\n\n## Próxima recomendação para este domínio\n\n> [Foo](./foo.md)\n",
            encoding="utf-8",
        )
        state = GlobalState()
        scan_existing_guides(tmp_path, cfg, state)
        n_before = len(state.next_recommendations)
        scan_existing_guides(tmp_path, cfg, state)
        # No duplicate added on re-scan
        assert len(state.next_recommendations) == n_before
