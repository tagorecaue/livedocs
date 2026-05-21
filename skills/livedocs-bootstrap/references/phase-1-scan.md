# Phase 1 — Scan

## Goal
Produce a structured map of the codebase using deterministic extractors. No
LLM calls from us — `graphify` may invoke an LLM internally but that's its
business.

## Inputs
- `.livedocs/guidance.md` (already saved in phase 0)

## Outputs
Files in `.livedocs/cache/`:
- `commit_sha.txt` — `git rev-parse HEAD` at scan time (anchor for future maintenance)
- `routes.json` — discovered frontend routes
- `i18n.json` — i18n keys + values
- `models.json` — domain models (Prisma/SQLAlchemy/TypeORM/Sequelize/Mongoose)
- `graphify-out/graph.json` — produced by graphify (if installed)

## What to do

> **DELEGATION**: each sub-step here (graphify extract, route extraction,
> i18n extraction, model extraction) é trabalho braçal de I/O e parsing.
> Spawne UM sub-agente por sub-step. O orquestrador (você) recebe APENAS o
> resumo de cada (contagens, paths, samples) — NUNCA o conteúdo bruto dos
> arquivos. Sub-agentes leem >50 arquivos cada; isso poluiria seu contexto.

1. **Capture commit SHA:**
   ```bash
   mkdir -p .livedocs/cache
   git rev-parse HEAD > .livedocs/cache/commit_sha.txt 2>/dev/null || echo "no-git" > .livedocs/cache/commit_sha.txt
   ```

2. **Detect graphify:**
   ```bash
   which graphify
   ```

   - If found AND `graphify-out/graph.json` does NOT exist: run extraction.
     ```bash
     graphify extract . --backend claude-cli --no-viz
     ```
     This takes 5-30 min on a medium repo, uses the user's Claude subscription.
     **Tell the user before running** — it's the most expensive step here.

   - If found AND `graphify-out/graph.json` already exists: refresh incrementally.
     ```bash
     graphify update . --force
     ```

   - If NOT found: warn the user with:
     > Graphify não está instalado. Vou continuar sem o sinal de grafo —
     > a taxonomia ainda funciona com rotas, i18n e models. Pra instalar:
     > `uv tool install graphifyy`

3. **Extract routes.** Detect frontend framework from `package.json`:
   - **Vue/Nuxt**: glob `pages/**/*.vue` and `**/router.{ts,js}`. For Vue Router config files, regex `path: ['"]([^'"]+)['"]`. For pages/-based, derive route from file path.
   - **React/Next**: glob `app/**/page.{tsx,jsx,ts,js}` (App Router) or `pages/**/*.{tsx,jsx,ts,js}` (Pages Router). Derive route from path.
   - **Generic fallback**: regex `path:\s*['"]([^'"]+)['"]` in `*.routes.*` files.

   Write `.livedocs/cache/routes.json`:
   ```json
   [
     {"path": "/projects", "file": "src/pages/Projects/Index.vue", "name": "ProjectsList"},
     ...
   ]
   ```

4. **Extract i18n keys.** Regex `t\(["']([^"']+)["']\)` and `\$t\(["']([^"']+)` across `*.{ts,tsx,js,jsx,vue}`. Read JSON files in `locales/`, `i18n/`, `lang/` if they exist. Write:
   ```json
   [
     {"key": "menu.dashboard", "values_by_lang": {"pt-BR": "Painel", "en": "Dashboard"}, "files_using": ["src/components/Nav.vue"]},
     ...
   ]
   ```

5. **Extract models.** Detect ORM(s):
   - **Prisma**: parse `schema.prisma`. Regex `model\s+(\w+)\s*\{([^}]+)\}`
   - **SQLAlchemy**: classes extending `Base`, `db.Model`, `Model` with `Column(...)` fields
   - **TypeORM**: classes decorated with `@Entity()`, fields with `@Column()`
   - **Sequelize**: `sequelize.define(...)` calls, or classes extending `Model`
   - **Mongoose**: `new Schema({...})` or `mongoose.model(...)`

   Write:
   ```json
   [
     {"name": "Project", "fields": ["id", "name", "stageId", "..."], "file": "prisma/schema.prisma"},
     ...
   ]
   ```

6. **Summarize for the user:**
   > Scan completo:
   > - Commit SHA: `abc1234`
   > - 139 rotas extraídas
   > - 272 chaves i18n
   > - 18 models
   > - Grafo: <X nós, Y arestas> ou "não disponível"
   >
   > Atualizar state.md e avançar pra Phase 2 (taxonomia)?

7. **Update `.livedocs/state.md`:** mark phase 1 done, save the counts in the
   state summary block.

## Pitfalls

- **`node_modules/` slows globs**: always exclude `node_modules`, `.git`,
  `dist`, `build`, `.venv`, `vendor`.
- **Graphify takes a long time**: tell the user it's working, don't poll
  unnecessarily. Check return code at the end.
- **Empty extractions are OK**: if a repo has no i18n, save an empty
  `i18n.json` `[]` — don't error.
- **Mixed frameworks**: a monorepo might have both Vue and a Node backend
  with no frontend routes. Save only what you find.
