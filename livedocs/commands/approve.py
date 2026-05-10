"""`livedocs approve <slug>` — mark a generated guide as reviewed by a human.

Status flow:
    in_progress → generated → reviewed → stale

`generated` means: agent finished writing the .md files.
`reviewed` means: human read them and confirms they're accurate.

This command:
1. Validates the interview is in `generated` state (refuses other states with hint).
2. Updates the in-memory state.toml.
3. Rewrites the `status:` front-matter field in both .md files (produto + tech).
"""

from __future__ import annotations

import re
from pathlib import Path

from livedocs import ui
from livedocs.i18n import t
from livedocs.state import load_config, load_state, save_state


def run_approve(repo_root: Path, slug: str | None = None) -> int:
    cfg = load_config(repo_root)
    if cfg is None:
        ui.error(t("err_no_project"))
        return 1

    state = load_state(repo_root)

    if slug is None:
        # Pick the freshest guide that is in `generated` state
        candidates = {s: iv for s, iv in state.interviews.items() if iv.status == "generated"}
        if not candidates:
            ui.info(t("approve_none_pending"))
            return 0
        if len(candidates) == 1:
            slug = next(iter(candidates))
        else:
            choices = [(f"{s} ({iv.domain})", s) for s, iv in candidates.items()]
            picked = ui.ask_choice(t("approve_pick_q"), choices=choices)
            if picked is None:
                ui.warn(t("abort"))
                return 130
            slug = picked

    if slug not in state.interviews:
        ui.error(t("err_slug_not_found", slug=slug))
        return 1

    iv = state.interviews[slug]
    if iv.status != "generated":
        ui.warn(t("approve_wrong_status", slug=slug, status=iv.status))
        return 1

    # Update front-matter on both guide files (best-effort).
    docs_dir = repo_root / cfg.docs_dir / iv.domain
    candidates = [docs_dir / f"{slug}.md", docs_dir / f"{slug}.tech.md"]
    updated_files: list[str] = []
    for path in candidates:
        if not path.exists():
            ui.warn(f"[muted]· {path.relative_to(repo_root)} not found, skipping front-matter update[/muted]")
            continue
        if _set_status_in_front_matter(path, "reviewed"):
            updated_files.append(str(path.relative_to(repo_root)))

    iv.status = "reviewed"
    save_state(repo_root, state)

    ui.success(t("approve_done", slug=slug))
    if updated_files:
        for f in updated_files:
            ui.console.print(f"  [muted]· front-matter atualizado:[/muted] [accent]{f}[/accent]")
    return 0


_FRONT_MATTER_STATUS_RE = re.compile(
    r"^(status\s*:\s*)([\"']?)([a-z_]+)\2\s*$",
    re.MULTILINE,
)


def _set_status_in_front_matter(path: Path, new_status: str) -> bool:
    """Rewrite the `status:` line inside the YAML front-matter. Idempotent.

    Returns True when the file was updated, False otherwise.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    fm, body = parts[1], parts[2]
    new_fm, count = _FRONT_MATTER_STATUS_RE.subn(rf"\1{new_status}", fm, count=1)
    if count == 0:
        # No status line — inject one before the closing ---.
        new_fm = fm.rstrip() + f"\nstatus: {new_status}\n"
    if new_fm == fm:
        return False
    path.write_text(f"---{new_fm}---{body}", encoding="utf-8")
    return True
