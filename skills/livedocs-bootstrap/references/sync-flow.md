# Sync — on-demand cross-reference command

## What this is

A **separate, on-demand command** that reconciles everything that spans topics.
It is NOT a phase of the topic loop. The user runs it when they want — typically
after closing one or more topics — by asking to *"sincronizar a documentação" /
"sync docs" / "atualizar os links e referências"*.

Sync is idempotent: running it twice over an unchanged corpus produces no diff.

It is the new home of the old Phase 5 stitching work, plus the cross-corpus
chores that used to be scattered (glossary, next-topic recommendations, stale
detection, taxonomy drift).

## Why it's separate from the loop

The topic loop is **local and deep** (one topic, end to end). Cross-references
are **global and broad** (they only make sense across the whole corpus). Mixing
them forced the old "progressive back-link sweep" where closing topic B made you
edit topic A. Pulling all between-topic work into one command means:

- Closing a topic never forces edits to topics already done.
- The user controls when links get reconciled (memory: the user prefers to
  "close and update links when I want, independently, with a command").
- A freshly closed topic correctly has no cross-links yet — sync adds them.

## What sync owns

1. **Cross-links (bidirectional).** Resolve `[TODO:link={slug}]` placeholders;
   add `## Veja também` links between topics that reference each other; ensure
   every link has a reverse link. Product↔product and tech↔tech only — never
   cross-flavor.
2. **Glossary consolidation.** Collect canonical terms surfaced across topics
   into the shared glossary; flag terminology drift (two terms for one concept).
3. **Next-topic recommendation** in each domain `_index.md` (managed section).
4. **Stale detection.** For each guide, compare its `source_files` against the
   current code; mark `status: stale` when a source changed since it was written.
5. **Taxonomy drift.** Detect topics that emerged (routes/models not on the map)
   and report them so the user can `[add]` them in the loop.

## Inputs

- All `docs/**` guides (product + tech).
- `.livedocs/taxonomy.json` (the map).
- `.livedocs/state.md` (topic statuses, scan SHA).
- The codebase (for stale detection + drift).

## What to do

### Step 0 — Snapshot before touching anything

`git status` must be clean (or the user OK's running over dirty tree). Sync
writes to many files; a clean checkpoint makes `git revert` trivial if a pass
goes wrong.

### Step 1 — Build the indexes

Produce two "index of others" menus — one per flavor — where each entry is
`{slug, title, summary, first_paragraph}` (~200 chars). The product index lists
only `.md`; the tech index only `.tech.md`. These are the menus each stitch
sub-agent uses as context (markdown, never raw code).

### Step 2 — Cross-link stitch (sub-agent per article-pair, ≤5 articles each)

> **DELEGATION**: one sub-agent reads an article's `.md` + `.tech.md` and emits
> patches via Write. You receive only the JSON return. Group up to 5 articles
> per sub-agent by capability (batch sizing).

Sub-agent prompt (per guide):

````
# Task: stitch this guide into the doc set

## This guide (full content)
---
<content of <guide>.md>
---

## Tech guide (full content)
---
<content of <guide>.tech.md>
---

## Index of OTHER guides, same flavor (titles + summaries + first paragraph)
<product index for the .md ; tech index for the .tech.md>

## Placeholders found in this guide
- [TODO:link=recurring-billing/issue-invoices]
- ...

## Rules

1. Each [TODO:link={slug}] becomes a real Markdown link IF the slug exists in
   the index. Link text = the target's title. Format:
   `[<title>](path/relative/to/this/file)`. Compute the relative path with
   forward slashes from this guide's path to the target's path.

2. If [TODO:link=X] points to a slug NOT in the index, leave as-is and add to
   `unresolved_links`.

3. Add inline links where a paragraph clearly discusses something another guide
   covers, even without a TODO. One link per concept; don't over-link. Count in
   `links_added`.

4. Harmonize terminology: if this guide uses term X but the index shows term Y
   is dominant for the same concept, change to Y. Note in `terms_harmonized`.

5. Flag contradictions: if this guide says X about feature F and another guide's
   first paragraph says not-X, register in `contradictions`.

6. NEVER reorder or rewrite conceptual content. Minimum changes only: links,
   term tweaks, contradiction markers. Body stays intact.

7. CROSS-FLAVOR PROHIBITED. `.md` links ONLY to other `.md`; `.tech.md` ONLY to
   other `.tech.md`. If a `.tech.md` has `[TODO:link=<its-own-product-sibling>]`,
   REMOVE the placeholder and its surrounding phrase entirely — do NOT leave
   unresolved, do NOT add a cross-flavor link. Report in `cross_flavor_removed`.

8. After every write: `wc -c <file>` (>0) and `grep -c "<sentinel>" <file>`.
   Return `verification_passed`. Anti-loop: same error 2× → abort.

9. Output ONLY JSON:
   {
     "files_modified": [...],
     "links_added": 4,
     "todos_resolved": 3,
     "unresolved_links": ["mystery-slug"],
     "terms_harmonized": [{"from": "...", "to": "..."}],
     "contradictions": [{"this_guide_says":"...","other_guide":"slug","other_says":"..."}],
     "cross_flavor_removed": ["contracts/issue-and-sign"],
     "verification_passed": true
   }
````

### Step 3 — Reverse-link pass

Cross-links are only useful bidirectionally. For each link A→B added in Step 2,
ensure B→A exists. A second hash-gated pass (only over guides that gained a new
inbound reference) adds the reverse `## Veja também` entry. If B already links
to A, no-op (idempotency).

### Step 4 — Contradictions → pending questions

Each contradiction returned becomes a pending question (in `{lang}`): *"This
guide says X, guide `<slug>` says not-X. Which is correct?"*. These are
cross-topic, so they live in a `sync-pending` list in state, surfaced to the
user at the end of sync — not folded into any single topic's interview.

### Step 5 — Glossary consolidation

Collect canonical terms each topic surfaced (from tech-guide invariants and
product-guide "key concepts"). Merge into `docs/_meta/glossary.md` (or the
project's glossary path). Report new terms and any drift (two spellings/words
for one concept) for the user to resolve.

### Step 6 — Next-topic recommendation per domain `_index.md`

Rewrite ONLY the managed sections of each domain's `_index.md`:
- `## Guias deste domínio` — auto-generated catalog of the topic's article pairs.
- `## Próxima recomendação para este domínio` — pointer to the next guide.

Preserve everything else (lead paragraph, planned-guides roadmap, vocabulary,
support material). This must be **idempotent byte-for-byte** — running sync
twice produces no diff. Test: rewrite, capture, rewrite again, assert equal.

### Step 7 — Stale detection

For each guide, read its `source_files` front-matter. Compare each file's
current state against the scan SHA (or last sync SHA) via `git diff --name-only
<sha>..HEAD`. If any `source_file` changed, set the guide's `status: stale` and
list it in the sync report. (Driving the re-documentation of stale guides is a
future incremental-maintenance feature; sync only flags them today.)

### Step 8 — Taxonomy drift

Cross-check routes/models from a fresh light scan against `taxonomy.json`. Report
routes/areas not represented by any topic — candidates the user may want to
`[add]` in the loop. Don't add them automatically.

### Step 9 — Commit + report

Commit: `sync: cross-links + glossary + recommendations`. Report (in `{lang}`):

```
✓ Sync done over 12 topics / 38 articles
  - 27 cross-links resolved, 4 still unresolved (slugs not created yet)
  - 9 reverse links added
  - glossary: +6 terms, 1 drift to resolve ("renegociação" vs "renovação")
  - 3 contradictions → pending (need your call)
  - 2 guides marked stale (source changed: billing/charge.ts, …)
  - taxonomy drift: /admin/exports has no topic — add it?
```

## Pitfalls

- **Broken relative paths.** Path math is error-prone; if a sub-agent emits an
  obviously wrong path, retry with explicit paths in the prompt.
- **Over-linking.** Cap at 1 link per concept per paragraph.
- **Cross-flavor contamination.** Never let `.md` link to `.tech.md`. Reject and
  flag (see core principle 6 / regra 8b).
- **Non-idempotent `_index.md` rewrite.** A trailing-newline mismatch makes
  sync produce a diff on every run. Normalize (`text.rstrip() + "\n"`) and test
  idempotency explicitly.
- **Unresolved because the target topic isn't documented yet.** Normal — the
  link resolves on a later sync once that topic is done. Not an error.
- **Running stale/drift as if it were a rewrite.** Sync only FLAGS stale guides
  and drift; it doesn't re-document them. That's the user's next loop decision.
