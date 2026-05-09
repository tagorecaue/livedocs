"""`livedocs review` — quick coherence/link/front-matter check.

v0 implementation: very lightweight. Parses front-matter via yaml, reports issues.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from livedocs import ui
from livedocs.i18n import t
from livedocs.state import load_config


def run_review(repo_root: Path) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1

    docs = repo_root / cfg.docs_dir
    if not docs.exists():
        ui.warn(f"{docs} {'não existe' if cfg.lang == 'pt-BR' else 'does not exist'}")
        return 0

    files = list(docs.rglob("*.md"))
    if not files:
        ui.info("Sem guias ainda." if cfg.lang == "pt-BR" else "No guides yet.")
        return 0

    issues: list[tuple[Path, str]] = []
    for f in files:
        if "_meta/" in str(f):
            continue
        text = f.read_text(encoding="utf-8")
        fm, body = _split_front_matter(text)
        if fm is None:
            issues.append((f, "missing front-matter"))
            continue
        try:
            data = yaml.safe_load(fm) or {}
        except yaml.YAMLError as e:
            issues.append((f, f"invalid YAML front-matter: {e}"))
            continue
        for required in ("slug", "domain", "flavor", "status"):
            if required not in data:
                issues.append((f, f"front-matter missing '{required}'"))
        flavor = data.get("flavor")
        if flavor not in (None, "produto", "tecnico"):
            issues.append((f, f"unknown flavor '{flavor}'"))
        if not body.strip():
            issues.append((f, "empty body"))

    if not issues:
        ui.success(f"{len(files)} {'arquivo(s) revisado(s), tudo certo' if cfg.lang == 'pt-BR' else 'file(s) reviewed, all good'}")
        return 0

    ui.warn(f"{len(issues)} {'problema(s) encontrado(s)' if cfg.lang == 'pt-BR' else 'issue(s) found'}")
    for path, msg in issues:
        try:
            rel = path.relative_to(repo_root)
        except ValueError:
            rel = path
        ui.console.print(f"  [muted]{rel}[/muted] — {msg}")
    return 1


def _split_front_matter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    return parts[1], parts[2]
