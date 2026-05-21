"""Bootstrap phase 1 — deterministic code scan (no AI).

Sub-passos (all best-effort, tolerant to failure):
  1. commit_sha  — `git rev-parse HEAD` (the Plan B capture point)
  2. graphify    — optional binary; produces a code graph in cache/graph.json
  3. routes      — Vue/Nuxt, React/Next, or generic regex on `*.routes.*`
  4. i18n        — t(...) / i18n.t(...) calls + JSON/YAML translations
  5. models      — Prisma, SQLAlchemy, TypeORM, Sequelize, Mongoose

Each sub-step writes its raw output to `<cache_dir>/<name>.json`. Failures
are logged via `ui.warn` and the corresponding path is left empty in the
returned `Scan` model. Phase 2 deals with missing signals.

No new third-party deps — stdlib + pathlib only.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from livedocs import ui
from livedocs.bootstrap.state import Scan
from livedocs.i18n import t

# Directories we never want to walk into when scanning user code.
_IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".nuxt", "out",
    "coverage", "__pycache__", ".venv", "venv", "env", ".tox", ".mypy_cache",
    ".pytest_cache", ".livedocs", ".idea", ".vscode", "target", ".cache",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """Like rglob but prunes _IGNORE_DIRS while walking. Returns up to ~5000 hits."""
    out: list[Path] = []
    limit = 5000
    stack: list[Path] = [root]
    while stack and len(out) < limit:
        cur = stack.pop()
        try:
            for entry in cur.iterdir():
                if entry.is_dir():
                    if entry.name in _IGNORE_DIRS or entry.name.startswith("."):
                        continue
                    stack.append(entry)
                elif entry.is_file() and entry.suffix.lower() in suffixes:
                    out.append(entry)
                    if len(out) >= limit:
                        break
        except (OSError, PermissionError):
            continue
    return out


def _read_text_safe(p: Path, max_bytes: int = 500_000) -> str:
    try:
        size = p.stat().st_size
        if size > max_bytes:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. commit_sha
# ---------------------------------------------------------------------------

def _detect_commit_sha(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(  # noqa: S603,S607 — trusted
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            return sha or None
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


# ---------------------------------------------------------------------------
# 2. graphify
#
# graphify creates the initial graph in two ways:
#   (a) via an LLM-driven SKILL inside Claude Code / Codex / etc (`/graphify`)
#   (b) via the headless `graphify extract <path> --backend <X>` CLI command
#
# livedocs uses (b) with `--backend claude-cli` so it reuses the same Claude
# subscription the agent already authenticates with — no extra API key.
#
# Idempotency: if `<repo>/graphify-out/graph.json` already exists we either
# refresh it via `graphify update` or skip the LLM extraction entirely. The
# scan phase is rerunnable cheaply.
# ---------------------------------------------------------------------------

GRAPHIFY_EXTRACT_TIMEOUT = 1800  # 30 min for medium repos


def _locate_graphify_output(repo_root: Path) -> Path | None:
    candidate = repo_root / "graphify-out" / "graph.json"
    if candidate.is_file():
        return candidate
    return None


def _extract_graph_via_cli(repo_root: Path, backend: str = "claude-cli") -> Path | None:
    """Headless graph extraction via `graphify extract --backend <X>`.

    Runs from the repo root so graphify writes to `<repo>/graphify-out/`.
    Returns the path to the produced graph.json on success, None on failure.
    """
    ui.info(
        f"Extraindo grafo do código com graphify (backend={backend}). "
        "Isso pode levar alguns minutos em repos grandes…"
    )
    try:
        result = subprocess.run(  # noqa: S603,S607 — trusted
            ["graphify", "extract", ".", "--backend", backend, "--no-viz"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=GRAPHIFY_EXTRACT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        ui.warn(f"graphify extract falhou ({e}); seguindo sem grafo.")
        return None

    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip()[-400:]
        ui.warn(
            f"graphify extract retornou {result.returncode}; seguindo sem grafo. "
            f"stderr: {stderr_tail}"
        )
        return None

    produced = _locate_graphify_output(repo_root)
    if produced is None:
        ui.warn("graphify extract terminou mas graphify-out/graph.json não apareceu; seguindo sem grafo.")
    return produced


def _refresh_existing_graph(repo_root: Path) -> None:
    """Best-effort `graphify update --force` on an existing graph. Non-fatal."""
    try:
        subprocess.run(  # noqa: S603,S607
            ["graphify", "update", ".", "--force"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        ui.warn(f"graphify update falhou (mantendo grafo existente): {e}")


def _run_graphify(repo_root: Path, out_path: Path) -> Path | None:
    """Produce or refresh a graphify graph for the repo.

    Strategy:
      1. If `<repo>/graphify-out/graph.json` exists → refresh with `update`
         (best-effort) and return.
      2. Otherwise, run `graphify extract . --backend claude-cli` to build
         the graph from scratch using the Claude Code CLI subscription.
      3. If graphify is not installed → emit hint and return None.
    """
    if shutil.which("graphify") is None:
        ui.warn(t("bootstrap_graphify_missing"))
        return None

    existing = _locate_graphify_output(repo_root)
    if existing is None:
        produced = _extract_graph_via_cli(repo_root, backend="claude-cli")
        if produced is None:
            return None
        existing = produced
    else:
        ui.info("Grafo do graphify encontrado; rodando update incremental…")
        _refresh_existing_graph(repo_root)

    # Mirror into our cache dir so callers always read from a stable path.
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(existing.read_bytes())
        return out_path
    except OSError as e:
        ui.warn(f"não consegui copiar saída do graphify ({e}); usando caminho original")
        return existing


# ---------------------------------------------------------------------------
# 3. routes
# ---------------------------------------------------------------------------

def _read_package_json(repo_root: Path) -> dict:
    pkg = repo_root / "package.json"
    if not pkg.exists():
        # Try common monorepo locations
        for sub in ("packages", "apps"):
            for p in (repo_root / sub).glob("*/package.json") if (repo_root / sub).exists() else []:
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
        return {}
    try:
        return json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _all_deps(pkg: dict) -> dict:
    out = {}
    for k in ("dependencies", "devDependencies", "peerDependencies"):
        d = pkg.get(k)
        if isinstance(d, dict):
            out.update(d)
    return out


_ROUTE_PATH_RE = re.compile(r"""path\s*:\s*['"`]([^'"`]+)['"`]""")


def _route_from_filepath(file: Path, base: Path, ext_strip: tuple[str, ...]) -> str:
    rel = file.relative_to(base).as_posix()
    for ext in ext_strip:
        if rel.endswith(ext):
            rel = rel[: -len(ext)]
            break
    # Drop "index"
    if rel.endswith("/index"):
        rel = rel[: -len("/index")]
    elif rel == "index":
        rel = ""
    # Bracket params [id] → :id
    rel = re.sub(r"\[(\.\.\.)?([^/\]]+)\]", r":\2", rel)
    return "/" + rel if not rel.startswith("/") else rel


def _scan_routes(repo_root: Path) -> list[dict]:
    pkg = _read_package_json(repo_root)
    deps = _all_deps(pkg)
    out: list[dict] = []

    # Vue/Nuxt — look for pages/**/*.vue
    if "vue" in deps or "nuxt" in deps:
        for base_name in ("pages", "src/pages", "app/pages"):
            base = repo_root / base_name
            if not base.is_dir():
                continue
            for f in _iter_files(base, (".vue",)):
                path = _route_from_filepath(f, base, (".vue",))
                out.append({
                    "path": path,
                    "file": str(f.relative_to(repo_root)),
                    "name": f.stem,
                })

    # React/Next — pages/**/*.{tsx,jsx,ts,js} or app/**
    if "react" in deps or "next" in deps:
        for base_name in ("pages", "src/pages", "app", "src/app"):
            base = repo_root / base_name
            if not base.is_dir():
                continue
            for f in _iter_files(base, (".tsx", ".jsx", ".ts", ".js")):
                # Skip api routes & special files for cleanliness
                name = f.name
                if name.startswith("_") or name in {"layout.tsx", "layout.jsx", "layout.ts", "layout.js"}:
                    continue
                if base_name.endswith("app") and name not in {"page.tsx", "page.jsx", "page.ts", "page.js"}:
                    continue
                path = _route_from_filepath(f, base, (".tsx", ".jsx", ".ts", ".js"))
                out.append({
                    "path": path,
                    "file": str(f.relative_to(repo_root)),
                    "name": f.stem,
                })

    # Generic regex fallback: anything matching *.routes.* (vue-router, angular, etc).
    seen_paths = {(r["path"], r["file"]) for r in out}
    for f in _iter_files(repo_root, (".ts", ".js", ".tsx", ".jsx", ".vue")):
        if ".routes." not in f.name and not f.name.endswith(("router.ts", "router.js", "routes.ts", "routes.js")):
            continue
        text = _read_text_safe(f)
        if not text:
            continue
        for m in _ROUTE_PATH_RE.finditer(text):
            path = m.group(1)
            if not path or path.startswith("http"):
                continue
            file_rel = str(f.relative_to(repo_root))
            if (path, file_rel) in seen_paths:
                continue
            seen_paths.add((path, file_rel))
            out.append({"path": path, "file": file_rel, "name": path.strip("/").replace("/", "-") or "root"})

    return out


# ---------------------------------------------------------------------------
# 4. i18n
# ---------------------------------------------------------------------------

_I18N_CALL_RE = re.compile(r"""(?:^|[^A-Za-z0-9_])(?:i18n\.t|\$?t)\(\s*['"`]([A-Za-z0-9_.\-]+)['"`]""")


def _scan_i18n(repo_root: Path) -> list[dict]:
    # 1) grep calls
    keys: dict[str, dict] = {}  # key -> {"files_using": set, "values_by_lang": {}}
    for f in _iter_files(repo_root, (".ts", ".tsx", ".js", ".jsx", ".vue")):
        text = _read_text_safe(f)
        if not text or "t(" not in text and "i18n" not in text:
            continue
        for m in _I18N_CALL_RE.finditer(text):
            k = m.group(1)
            entry = keys.setdefault(k, {"files_using": set(), "values_by_lang": {}})
            entry["files_using"].add(str(f.relative_to(repo_root)))

    # 2) read translations from common dirs
    locale_roots = []
    for name in ("locales", "i18n", "lang", "locale", "translations"):
        for cand in (repo_root / name, repo_root / "src" / name, repo_root / "public" / name):
            if cand.is_dir():
                locale_roots.append(cand)

    def _flatten(prefix: str, obj: Any, out: dict) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_p = f"{prefix}.{k}" if prefix else k
                _flatten(new_p, v, out)
        elif isinstance(obj, str):
            out[prefix] = obj

    for root in locale_roots:
        for f in _iter_files(root, (".json",)):
            # lang inferred from filename stem or parent dir
            lang = f.stem
            if len(lang) > 6 and "-" not in lang:
                lang = f.parent.name
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            flat: dict[str, str] = {}
            _flatten("", data, flat)
            for k, v in flat.items():
                entry = keys.setdefault(k, {"files_using": set(), "values_by_lang": {}})
                entry["values_by_lang"].setdefault(lang, v)

    out_list = []
    for k, v in keys.items():
        out_list.append({
            "key": k,
            "values_by_lang": v["values_by_lang"],
            "files_using": sorted(v["files_using"])[:5],
        })
    out_list.sort(key=lambda x: x["key"])
    return out_list


# ---------------------------------------------------------------------------
# 5. models
# ---------------------------------------------------------------------------

_PRISMA_MODEL_RE = re.compile(r"model\s+(\w+)\s*\{([^}]+)\}", re.MULTILINE)
_PRISMA_FIELD_RE = re.compile(r"^\s*(\w+)\s+\S+", re.MULTILINE)
_SQLA_CLASS_RE = re.compile(
    r"class\s+(\w+)\s*\([^)]*(?:Base|db\.Model|Model)[^)]*\)\s*:",
)
_TYPEORM_CLASS_RE = re.compile(r"@Entity\([^)]*\)\s*(?:export\s+)?class\s+(\w+)")
_SEQ_DEFINE_RE = re.compile(r"""sequelize\.define\(\s*['"`](\w+)['"`]""")
_MONGOOSE_RE = re.compile(r"""(?:new\s+(?:mongoose\.)?Schema|(?:mongoose\.)?model)\s*\(\s*['"`]?(\w+)?""")


def _scan_models(repo_root: Path) -> list[dict]:
    models: list[dict] = []

    # Prisma
    for f in _iter_files(repo_root, (".prisma",)):
        text = _read_text_safe(f)
        for m in _PRISMA_MODEL_RE.finditer(text):
            name = m.group(1)
            body = m.group(2)
            fields = [fm.group(1) for fm in _PRISMA_FIELD_RE.finditer(body) if fm.group(1) not in {"@id", "@@", "//"}]
            models.append({
                "name": name,
                "fields": fields[:20],
                "file": str(f.relative_to(repo_root)),
                "kind": "prisma",
            })

    # Python — SQLAlchemy
    for f in _iter_files(repo_root, (".py",)):
        text = _read_text_safe(f)
        if not text or ("Base" not in text and "db.Model" not in text and "Model" not in text):
            continue
        for cm in _SQLA_CLASS_RE.finditer(text):
            name = cm.group(1)
            # Pull columns: lines like `foo = Column(...)`
            field_re = re.compile(r"^\s+(\w+)\s*=\s*(?:Column|relationship|mapped_column)\(", re.MULTILINE)
            fields = [m.group(1) for m in field_re.finditer(text)]
            models.append({
                "name": name,
                "fields": fields[:20],
                "file": str(f.relative_to(repo_root)),
                "kind": "sqlalchemy",
            })

    # TS/JS — TypeORM, Sequelize, Mongoose
    for f in _iter_files(repo_root, (".ts", ".tsx", ".js")):
        text = _read_text_safe(f)
        if not text:
            continue
        for cm in _TYPEORM_CLASS_RE.finditer(text):
            name = cm.group(1)
            # @Column() prop: type;
            field_re = re.compile(r"@Column\([^)]*\)\s*([A-Za-z_]\w*)", re.MULTILINE)
            fields = [m.group(1) for m in field_re.finditer(text)]
            models.append({
                "name": name,
                "fields": fields[:20],
                "file": str(f.relative_to(repo_root)),
                "kind": "typeorm",
            })
        for cm in _SEQ_DEFINE_RE.finditer(text):
            name = cm.group(1)
            models.append({
                "name": name,
                "fields": [],
                "file": str(f.relative_to(repo_root)),
                "kind": "sequelize",
            })
        if "mongoose" in text.lower() and "Schema" in text:
            for cm in _MONGOOSE_RE.finditer(text):
                name = cm.group(1) or f.stem
                if name and name not in {"Schema", "model"}:
                    # Pull field names from object literal
                    field_re = re.compile(r"^\s*(\w+)\s*:\s*\{", re.MULTILINE)
                    fields = [m.group(1) for m in field_re.finditer(text)]
                    models.append({
                        "name": name,
                        "fields": fields[:20],
                        "file": str(f.relative_to(repo_root)),
                        "kind": "mongoose",
                    })

    # Dedupe by (name, file)
    seen = set()
    deduped = []
    for m in models:
        key = (m["name"], m["file"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(m)
    return deduped


# ---------------------------------------------------------------------------
# Top-level entry
# ---------------------------------------------------------------------------

def run_scan(repo_root: Path, cache_dir: Path) -> Scan:
    """Run all five scan sub-steps. Returns a `Scan` with paths to cached JSONs."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    scan = Scan(scanned_at=_now_iso())

    # 1. commit_sha
    sha = _detect_commit_sha(repo_root)
    scan.commit_sha = sha

    # 2. graphify
    graph_out = cache_dir / "graph.json"
    g = _run_graphify(repo_root, graph_out)
    scan.graph_path = str(g) if g else ""

    # 3. routes
    try:
        routes = _scan_routes(repo_root)
    except Exception as e:  # noqa: BLE001 — tolerant scan
        ui.warn(f"route scan failed: {e}")
        routes = []
    routes_out = cache_dir / "routes.json"
    _write_json(routes_out, routes)
    scan.routes_path = str(routes_out)

    # 4. i18n
    try:
        i18n = _scan_i18n(repo_root)
    except Exception as e:  # noqa: BLE001
        ui.warn(f"i18n scan failed: {e}")
        i18n = []
    i18n_out = cache_dir / "i18n.json"
    _write_json(i18n_out, i18n)
    scan.i18n_path = str(i18n_out)

    # 5. models
    try:
        models = _scan_models(repo_root)
    except Exception as e:  # noqa: BLE001
        ui.warn(f"model scan failed: {e}")
        models = []
    models_out = cache_dir / "models.json"
    _write_json(models_out, models)
    scan.models_path = str(models_out)

    ui.info(t("bootstrap_scan_done", routes=len(routes), i18n=len(i18n), models=len(models)))
    return scan


__all__ = ["run_scan"]
