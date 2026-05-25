# State file format

The state file is `.livedocs/state.md`. It's deliberately Markdown (not JSON
or TOML) so the user can READ and EDIT it manually if anything goes wrong.

The model is **incremental**: a one-time Init/Map (phases 0–3) followed by a
**per-topic loop**. The state therefore tracks two things: whether Init/Map is
done, and the status of each topic independently. There is no single global
"current phase" once the loop starts — topics advance on their own.

## Template

```markdown
# LiveDocs — State

**Last update:** 2026-05-21T16:42:11
**Commit SHA at scan time:** abc1234
**Total cost so far:** $4.10
**Lang:** pt-BR
**Answer marker:** Resposta:

## Init / Map (one-time)

- [x] **0 — Guidance** completed
- [x] **1 — Scan** completed (139 routes, 272 i18n keys, 18 models, graph: 847 nodes)
- [x] **2 — Taxonomy** completed (18 capabilities, 5 journeys)
- [x] **3 — Review** completed (taxonomy approved 2026-05-21T13:22:08)

> Init/Map done → topic loop active.

## Topics

Per-topic status. One row per capability/journey. Status values:
`not-started → drafted → triaged → interviewed → updated → done`.

| Topic | Kind | Status | Articles | Cost | Last touched |
|---|---|---|---|---|---|
| project-management | capability | done | 2/2 | $1.40 | 2026-05-21T14:10 |
| recurring-billing | capability | drafted | 3/3 | $1.55 | 2026-05-21T16:40 |
| resident-onboarding | capability | not-started | 0/? | — | — |
| first-invoice | journey | not-started | 0/? | — | — |

### In-progress topic detail (only the one being worked on)

**recurring-billing** — status: drafted
- [x] `recurring-billing/overview`  drafted · $0.49
- [x] `recurring-billing/issue-charges`  drafted · $0.61
- [x] `recurring-billing/dunning`  drafted · $0.45
- next step: code-first triage (Phase 5.5)

## Next-topic recommendation

> **Suggested next:** `resident-onboarding` — it feeds `recurring-billing`
> (a resident must exist before the first charge), and the scan shows it
> shares the `Resident` model. Confirmed as logical follow-up.

## Pending questions — current topic only

Questions live with the topic they belong to. Only the in-progress topic keeps
an open list here; closed topics fold their answered questions into the article
front-matter and the interview transcript.

- **Q1** [recurring-billing/dunning] needs_human — Why retry 3× before marking failed?
  - Provisional: "...". Confidence: low.
- **Q2** [recurring-billing/issue-charges] answered_by_code — evidence: src/billing/charge.ts:88

## Screenshot TODOs (open: 4)

- [open] `recurring-billing/overview.md` — `/billing` — "Dashboard with all charges"
- ...

## Cost log

| When | Topic | Item | Cost USD |
|---|---|---|---|
| — | (init) | taxonomy-propose | $0.34 |
| — | project-management | draft + triage + update | $1.40 |
| — | recurring-billing | draft (3 articles) | $1.55 |

## Sync log

Records each on-demand sync run (cross-links, glossary, stale, drift).

| When | What ran | Result |
|---|---|---|
| 2026-05-21T14:15 | cross-links + glossary | 12 links added, glossary +4 terms |
```

## Read & write conventions

**On read** (resuming):
1. Check the "Init / Map" section. If any of 0–3 is unchecked, resume that
   phase. If all four are done, enter the **topic loop**.
2. In the loop, read the "Topics" table to know what's done vs pending and to
   seed the selector. Read "In-progress topic detail" to resume a half-done
   topic exactly where it stopped.
3. Read "Next-topic recommendation" to pre-fill the selector's suggestion.
4. Read "Pending questions — current topic" only when re-entering Phase 6 for
   the in-progress topic.
5. Read "Cost log" for the running total.

**On write** (incremental):
1. Always rewrite the whole file (it's small, simpler than patching).
2. Update "Last update" timestamp.
3. Bump the in-progress topic's row and detail as each phase completes; when a
   topic reaches `done`, collapse its detail block (keep the table row).
4. After Sync, append a row to "Sync log".

## Backup strategy

Keep `.livedocs/state.md.bak` (one previous version) before any write. If
state gets corrupted, the user can `mv state.md.bak state.md` and continue.

## What NOT to put in state

- Full guide content (lives in docs/)
- Full guidance text (lives in .livedocs/guidance.md)
- Cache files (live in .livedocs/cache/)
- Long JSON blobs
- Pending questions for topics other than the one in progress (closed topics'
  questions live in article front-matter + the interview transcript)

State stays small. If it's growing past ~50KB, you're probably keeping
per-topic detail for topics that already closed — collapse them.
