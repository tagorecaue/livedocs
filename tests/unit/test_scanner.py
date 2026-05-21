"""Phase 1 — deterministic scanner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from livedocs.bootstrap.scanner import run_scan


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
    )


def test_scan_empty_repo(tmp_repo: Path):
    cache = tmp_repo / ".livedocs" / "cache"
    scan = run_scan(tmp_repo, cache)
    assert scan.commit_sha
    assert Path(scan.routes_path).exists()
    assert Path(scan.i18n_path).exists()
    assert Path(scan.models_path).exists()
    assert json.loads(Path(scan.routes_path).read_text()) == []


def test_scan_detects_vue_routes(tmp_path: Path):
    repo = tmp_path / "vrepo"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"name": "v", "dependencies": {"vue": "^3.0.0"}}),
        encoding="utf-8",
    )
    pages = repo / "pages"
    pages.mkdir()
    (pages / "index.vue").write_text("<template/>", encoding="utf-8")
    (pages / "billing.vue").write_text("<template/>", encoding="utf-8")
    sub = pages / "settings"
    sub.mkdir()
    (sub / "profile.vue").write_text("<template/>", encoding="utf-8")
    _git_init(repo)

    scan = run_scan(repo, repo / ".livedocs" / "cache")
    routes = json.loads(Path(scan.routes_path).read_text())
    paths = {r["path"] for r in routes}
    assert "/billing" in paths
    assert "/settings/profile" in paths
    # index → /
    assert "/" in paths or "" in paths or any(p in paths for p in ("/", ""))


def test_scan_detects_i18n_keys(tmp_path: Path):
    repo = tmp_path / "i18nrepo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "app.ts").write_text(
        'const a = t("menu.dashboard"); const b = i18n.t("nav.billing");',
        encoding="utf-8",
    )
    locales = repo / "locales"
    locales.mkdir()
    (locales / "pt-BR.json").write_text(
        json.dumps({"menu": {"dashboard": "Painel"}, "nav": {"billing": "Cobrança"}}),
        encoding="utf-8",
    )
    _git_init(repo)

    scan = run_scan(repo, repo / ".livedocs" / "cache")
    i18n_data = json.loads(Path(scan.i18n_path).read_text())
    keys = {e["key"] for e in i18n_data}
    assert "menu.dashboard" in keys
    assert "nav.billing" in keys


def test_scan_detects_prisma_models(tmp_path: Path):
    repo = tmp_path / "prisma_repo"
    repo.mkdir()
    (repo / "schema.prisma").write_text(
        "model Invoice {\n  id   Int    @id\n  amount Float\n  user User\n}\n\n"
        "model User {\n  id   Int    @id\n  email String\n}\n",
        encoding="utf-8",
    )
    _git_init(repo)

    scan = run_scan(repo, repo / ".livedocs" / "cache")
    models = json.loads(Path(scan.models_path).read_text())
    names = {m["name"] for m in models}
    assert "Invoice" in names
    assert "User" in names


def test_scan_detects_sqlalchemy_models(tmp_path: Path):
    repo = tmp_path / "sa_repo"
    repo.mkdir()
    (repo / "models.py").write_text(
        "from sqlalchemy import Column, Integer, String\n"
        "Base = object\n"
        "class Invoice(Base):\n"
        "    id = Column(Integer, primary_key=True)\n"
        "    amount = Column(Integer)\n",
        encoding="utf-8",
    )
    _git_init(repo)

    scan = run_scan(repo, repo / ".livedocs" / "cache")
    models = json.loads(Path(scan.models_path).read_text())
    names = {m["name"] for m in models}
    assert "Invoice" in names


def test_scan_graphify_missing_is_tolerant(tmp_repo: Path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    scan = run_scan(tmp_repo, tmp_repo / ".livedocs" / "cache")
    assert scan.graph_path == ""
    # Other paths still produced
    assert Path(scan.routes_path).exists()
