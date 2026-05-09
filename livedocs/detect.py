"""Detection helpers — figure out what's already on the user's machine."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def has_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def has_claude_code() -> bool:
    return shutil.which("claude") is not None


def claude_code_version() -> str | None:
    if not has_claude_code():
        return None
    try:
        out = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        return None
    return None


def has_graphify() -> bool:
    """graphify available either as 'graphify' command or as a Python module."""
    if shutil.which("graphify"):
        return True
    try:
        import importlib.util
        return importlib.util.find_spec("graphify") is not None
    except Exception:
        return False


def has_existing_docs(repo_root: Path, candidate_dirs: list[str]) -> tuple[str | None, int]:
    """Return (path, count_of_md) for the first directory that already contains .md files."""
    for d in candidate_dirs:
        full = repo_root / d
        if not full.is_dir():
            continue
        md_files = list(full.rglob("*.md"))
        if md_files:
            return d, len(md_files)
    return None, 0


def project_slug_suggestion(repo_root: Path) -> str:
    """Guess a project slug from the repo dir name. Slugified."""
    name = repo_root.name
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in ("-", "_", " "):
            out.append("-")
    return "".join(out).strip("-") or "project"
