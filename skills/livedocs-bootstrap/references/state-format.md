# State file format

The state file is `.livedocs/state.md`. It's deliberately Markdown (not JSON
or TOML) so the user can READ and EDIT it manually if anything goes wrong.

## Template

```markdown
# LiveDocs — Bootstrap State

**Current phase:** 4 (Pass 1 — drafts)
**Last update:** 2026-05-21T16:42:11
**Commit SHA at scan time:** abc1234
**Total cost so far:** $2.31
**Lang:** pt-BR

## Phase progress

- [x] **0 — Guidance** completed
- [x] **1 — Scan** completed (139 routes, 272 i18n keys, 18 models, graph: 847 nodes)
- [x] **2 — Taxonomy** completed (18 capabilities, 5 journeys)
- [x] **3 — Review** completed (taxonomy approved 2026-05-21T13:22:08)
- [/] **4 — Pass 1** in progress (5/67 articles drafted)
- [ ] 5 — Pass 2
- [ ] 5.5 — Code-first triage
- [ ] 6 — Refinement
- [ ] 7 — Global update

## Articles status

### Capability: project-management
- [x] `project-management/overview`  drafted · $0.49 · 187s
- [x] `project-management/create-project`  drafted · $0.42 · 162s
- [ ] `project-management/configure-financial`  pending
- [ ] `project-management/kanban`  pending

### Capability: recurring-billing
- [ ] `recurring-billing/overview`  pending
- ...

### Journeys
- [ ] `primeira-fatura`  pending
- ...

## Pending questions (open: 7, answered: 0, merged: 0, answered_by_code: 0)

- **Q1** [project-management/create-project] How does X interact with Y when Z?
  - Provisional: "...". Confidence: low.
- **Q2** ...

## Screenshot TODOs (open: 12)

- [open] `project-management/overview.md` — `/projects` — "Kanban view with all stages"
- [open] `project-management/create-project.md` — `/projects/new` — "Wizard step 1"
- ...

## Cost log

| Phase | Item | Cost USD |
|---|---|---|
| 2 | taxonomy-propose | $0.34 |
| 3 | split project-management | $0.05 |
| 4 | draft overview | $0.49 |
| 4 | draft create-project | $0.42 |
```

## Read & write conventions

**On read** (resuming):
1. Parse the "Current phase" line. That tells you which phase to enter.
2. Read the "Articles status" section to determine what's done vs pending
   for Phase 4 — pre-populate the selector.
3. Read "Pending questions" to seed Phase 6 if you're entering it.
4. Read "Cost log" for the running total.

**On write** (incremental):
1. Always rewrite the whole file (it's small, simpler than patching).
2. Update "Last update" timestamp.
3. Bump article statuses incrementally — one at a time, not in batch.

## Backup strategy

Keep `.livedocs/state.md.bak` (one previous version) before any write. If
state gets corrupted, the user can `mv state.md.bak state.md` and continue.

## What NOT to put in state

- Full guide content (lives in docs/)
- Full guidance text (lives in .livedocs/guidance.md)
- Cache files (live in .livedocs/cache/)
- Long JSON blobs

State stays under 50KB for an entire project's worth of bootstrap. If
it's growing past that, you're probably storing the wrong things.
