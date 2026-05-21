"""`livedocs bootstrap` — orchestrator.

The actual seven-phase pipeline lives in `livedocs.bootstrap.*`. This module
just wires the entry point together. In this commit it is a placeholder that
prints a TODO and exits 0; phases will be wired in in the next commits.
"""

from __future__ import annotations

from pathlib import Path

from livedocs import ui


def run_bootstrap(
    repo_root: Path,
    *,
    resume: bool = False,
    re_tax: bool = False,
) -> int:
    """Run (or resume) the bootstrap pipeline.

    Currently a stub: prints TODO and returns 0. The flags are accepted
    so the CLI surface is stable while phases are implemented.
    """
    _ = repo_root, resume, re_tax  # silence unused-arg warnings for now
    ui.info("TODO: implementação nas fases seguintes")
    return 0
