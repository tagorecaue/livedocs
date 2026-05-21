"""End-to-end bootstrap on the mini-saas fixture.

This test exercises every phase (0-7) of `livedocs bootstrap` with a
mocked Claude agent. The mock routes prompts to canned JSON responses
based on substring matching. We pre-create the .md files the agent
"would write" (so the disk-verification step in pass1/pass2/global_update
passes), and we monkeypatch `ui.ask_text` to return canned answers for
the refinement interview.

Asserts:
  - bootstrap reaches phase 7 / status='done'
  - >=4 docs/ files generated
  - taxonomy has 2 capabilities + 1 journey
  - all guides end up `refined` (had answered questions) or `stitched`
  - pending questions include `answered` items
  - no files outside docs/ were modified vs the initial snapshot
"""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

import pytest

from livedocs.bootstrap.state import load_bootstrap_state
from livedocs.commands.bootstrap import run_bootstrap
from livedocs.models import ProjectConfig
from livedocs.state import (
    ensure_gitignore_for_state,
    save_config,
)

FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "mini-saas"


# ---------------------------------------------------------------------------
# Canned Claude responses (keyed by substring of the prompt)
# ---------------------------------------------------------------------------

_TAXONOMY = {
    "capabilities": [
        {
            "slug": "cobranca",
            "title": "Cobrança",
            "summary": "Faturas e pagamentos.",
            "code_anchors": ["src/models/Invoice.ts", "src/pages/Billing.vue"],
        },
        {
            "slug": "configuracoes",
            "title": "Configurações",
            "summary": "Ajustes da conta.",
            "code_anchors": ["src/pages/Settings.vue", "src/models/User.ts"],
        },
    ],
    "journeys": [
        {
            "slug": "primeira-fatura",
            "title": "Primeira fatura",
            "summary": "Do cadastro até a primeira fatura.",
            "capability_refs": ["cobranca", "configuracoes"],
        },
    ],
}


def _md(repo: Path, kind_dir: str, slug: str, title: str, *, article_slug: str = "introducao") -> tuple[str, str]:
    """Materialize the product + tech files. Returns their repo-relative paths.

    Schema v2 layout: capabilities live at docs/capacidades/<cap>/<article>.md,
    journeys stay flat at docs/jornadas/<slug>.md.
    """
    if kind_dir == "capacidades":
        base = repo / "docs" / kind_dir / slug
        rel_dir = f"docs/{kind_dir}/{slug}"
        fname = article_slug
    else:
        base = repo / "docs" / kind_dir
        rel_dir = f"docs/{kind_dir}"
        fname = slug
    base.mkdir(parents=True, exist_ok=True)
    prod = base / f"{fname}.md"
    tech = base / f"{fname}.tech.md"
    prod.write_text(
        f"---\nslug: {fname}\ntitle: {title}\nstatus: drafted\n---\n\n"
        f"# {title}\n\nDescrição inicial gerada pelo agente.\n",
        encoding="utf-8",
    )
    tech.write_text(
        f"---\nslug: {fname}\ntitle: {title} (técnico)\nstatus: drafted\n---\n\n"
        f"# {title} (técnico)\n\nDetalhes técnicos.\n",
        encoding="utf-8",
    )
    return f"{rel_dir}/{fname}.md", f"{rel_dir}/{fname}.tech.md"


def _copy_fixture(target: Path) -> None:
    shutil.copytree(FIXTURE_ROOT, target)


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
    )


def _outside_docs_files(repo: Path) -> set[str]:
    """List tracked + untracked files outside `.livedocs` and `docs/`."""
    out = subprocess.check_output(
        ["git", "ls-files", "--others", "--cached", "--exclude-standard"],
        cwd=repo,
        text=True,
    )
    return {
        line.strip()
        for line in out.splitlines()
        if line.strip()
        and not line.startswith("docs/")
        and not line.startswith(".livedocs/")
    }


@pytest.fixture
def mini_saas_repo(tmp_path: Path) -> tuple[Path, ProjectConfig]:
    repo = tmp_path / "mini-saas"
    _copy_fixture(repo)
    _git_init(repo)
    cfg = ProjectConfig(
        project_slug="mini-saas",
        lang="pt-BR",
        provider="claude-code",
        docs_dir="docs",
        style="narrative",
    )
    save_config(repo, cfg)
    ensure_gitignore_for_state(repo)
    from livedocs.skill.styles import copy_style_to_project
    copy_style_to_project("narrative", repo / ".livedocs" / "style.md")
    return repo, cfg


def test_bootstrap_e2e_mini_saas(mini_saas_repo, mock_agent, monkeypatch):
    repo, _cfg = mini_saas_repo

    # No TTY → guidance reads stdin, refinement is gated.
    monkeypatch.setattr("sys.stdin", io.StringIO("SaaS de cobrança e contas.\n"))
    # We still want the refinement interview to RUN, so flip non-interactive
    # off but stub `ui.ask_text` to feed canned answers.
    monkeypatch.setattr("livedocs.ui.is_non_interactive", lambda: False)
    # Skip the interactive pass1 selector — generate all pending in one go.
    monkeypatch.setattr(
        "livedocs.bootstrap.pass1_selector.select_pass1_scope",
        lambda state: (
            {c.slug for c in (state.taxonomy.capabilities if state.taxonomy else [])},
            True,
            "all",
        ),
    )
    # Disable real graphify CLI invocation in scan phase.
    monkeypatch.setattr("livedocs.bootstrap.scanner.shutil.which", lambda _cmd: None)

    answers = iter(
        [
            "O ciclo é mensal e cobramos no dia 5.",
            "Sim, suportamos cartão e Pix.",
            "Cancelamento é via formulário em /settings.",
        ]
        * 5  # plenty of canned answers in case dedup is light
    )

    def _fake_ask_text(message, **kwargs):
        try:
            return next(answers)
        except StopIteration:
            return "/skip"

    monkeypatch.setattr("livedocs.ui.ask_text", _fake_ask_text)
    monkeypatch.setattr("livedocs.bootstrap.refinement.ui.ask_text", _fake_ask_text)

    # ---- Snapshot non-docs files BEFORE bootstrap ----
    snapshot_before = {
        str(p.relative_to(repo)): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file()
        and ".livedocs" not in p.parts
        and "docs" not in p.parts
        and ".git" not in p.parts
    }

    # ---- Wire canned responses ----
    mock_agent.set_response("propor-taxonomia", _TAXONOMY)

    # Pre-create the four files the pass1 agent claims to write.
    cob = _md(repo, "capacidades", "cobranca", "Cobrança")
    cfg_paths = _md(repo, "capacidades", "configuracoes", "Configurações")
    pf = _md(repo, "jornadas", "primeira-fatura", "Primeira fatura")

    mock_agent.set_response(
        "passada-1-draft",
        json_data={
            "files_written": list(cob),
            "pending_questions": [
                {
                    "question": "Qual o ciclo de cobrança padrão?",
                    "provisional_answer": "Mensal.",
                    "confidence": "low",
                },
            ],
        },
        cost_usd=0.05,
    )
    mock_agent.set_response(
        "passada-1-draft",
        json_data={
            "files_written": list(cfg_paths),
            "pending_questions": [
                {
                    "question": "Como funciona o cancelamento de conta?",
                    "provisional_answer": "Auto-serviço.",
                    "confidence": "low",
                },
            ],
        },
        cost_usd=0.05,
    )
    mock_agent.set_response(
        "passada-1-draft",
        json_data={
            "files_written": list(pf),
            "pending_questions": [
                {
                    "question": "Quais métodos de pagamento aceitamos?",
                    "provisional_answer": "Cartão.",
                    "confidence": "low",
                },
            ],
        },
        cost_usd=0.05,
    )

    # Pass 2 (one per drafted guide).
    for paths in (cob, cfg_paths, pf):
        mock_agent.set_response(
            "passada-2-stitch",
            json_data={
                "files_modified": list(paths),
                "contradictions": [],
                "new_pending_questions": [],
            },
            cost_usd=0.01,
        )

    # Refinement dedup: keep all questions unique (no merge).
    mock_agent.set_response(
        "refinement-dedup",
        json_data={
            "clusters": [],
            "unique_ids": ["Q1", "Q2", "Q3"],
        },
        cost_usd=0.005,
    )

    # Global update — once per affected guide.
    for paths in (cob, cfg_paths, pf):
        mock_agent.set_response(
            "global-update",
            json_data={
                "files_modified": list(paths),
                "changes_summary": "Resposta do mantenedor incorporada.",
            },
            cost_usd=0.02,
        )

    rc = run_bootstrap(repo, accept_taxonomy=True, skip_refinement=False)
    assert rc == 0

    state = load_bootstrap_state(repo)
    assert state is not None
    assert state.status == "done"
    assert state.last_completed_phase == 7

    # Taxonomy and guides
    assert state.taxonomy is not None
    assert len(state.taxonomy.capabilities) == 2
    assert len(state.taxonomy.journeys) == 1
    assert len(state.guides) == 3

    # Every guide answered → refined. With schema v2, capability guides
    # are slugged as `<cap-slug>/<article-slug>`; default migration creates
    # an "introducao" article per capability.
    statuses = {g.slug: g.status for g in state.guides}
    for slug in ("cobranca/introducao", "configuracoes/introducao", "primeira-fatura"):
        assert statuses[slug] == "refined", statuses

    # Pending questions exist + at least 3 are answered.
    assert len(state.pending_questions) >= 3
    answered = [q for q in state.pending_questions if q.status == "answered"]
    assert len(answered) >= 3

    # >=4 .md files in docs/
    md_files = list((repo / "docs").rglob("*.md"))
    assert len(md_files) >= 4

    # No files outside docs/ + .livedocs/ were touched.
    snapshot_after = {
        str(p.relative_to(repo)): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file()
        and ".livedocs" not in p.parts
        and "docs" not in p.parts
        and ".git" not in p.parts
    }
    assert snapshot_after == snapshot_before

    # Sanity: outside-docs git-tracked files unchanged.
    assert _outside_docs_files(repo) == {
        "README.md",
        "locales/pt-BR.json",
        "package.json",
        "src/models/Invoice.ts",
        "src/models/User.ts",
        "src/pages/Billing.vue",
        "src/pages/Home.vue",
        "src/pages/Settings.vue",
    }
