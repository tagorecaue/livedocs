# Topic loop — the heart of the incremental flow

## When this runs

After Init/Map (Phases 0–3) is approved. The taxonomy is the **map**; this loop
walks it one topic at a time. Each pass through the loop takes ONE topic (a
capability or a journey) from `not-started` to `done`, fully isolated from every
other topic.

Load this file once Init/Map is done and stay in it until the user stops.

## The loop, at a glance

```
┌─────────────────────────────────────────────────────────┐
│ 1. SELECTOR — show topic status, suggest the next one    │
│        ↓ user picks ONE topic                            │
│ 2. Phase 4    — draft the topic's articles (isolated)    │
│ 3. Phase 5.5  — code-first triage (this topic only)      │
│ 4. Phase 6    — coverage-aware interview (this topic)    │
│ 5. Phase 7    — rewrite affected articles (this topic)   │
│ 6. CLOSE      — commit topic, nudge sync                 │
│        ↓                                                 │
└────────────── back to selector ─────────────────────────┘
```

All chat strings below are illustrative (English). Render in `{lang}`.

## Step 1 — The selector

Read the "Topics" table from `.livedocs/state.md`. Render it grouped by status,
and ALWAYS surface a suggested next topic at the top.

```
Documentation progress — 3/23 topics done

  ✓ done         project-management, recurring-billing, dunning
  ◐ in progress  (none)
  ○ not started  resident-onboarding, payment-methods, refunds, … (18 more)

Suggested next: resident-onboarding
  → A resident must exist before the first charge, and it shares the
    `Resident` model with recurring-billing (already documented). Natural
    follow-up.

What do you want to do?
  [enter]  document the suggested topic (resident-onboarding)
  [pick]   choose a different topic
  [add]    add a topic not on the map (taxonomy drift)
  [sync]   run sync now (cross-links, glossary, recommendations)
  [stop]   pause — state is saved, resume anytime
```

### How to pick the suggestion (next-topic heuristic)

Suggest, never impose. Rank `not-started` topics by, in order:

1. **Dependency adjacency** — a topic whose models/routes are consumed by, or
   feed, an already-`done` topic. Documenting neighbors while context is warm
   produces better cross-links later.
2. **Shared vocabulary** — topics that share models/enums with done topics
   (the glossary is already partly built).
3. **Journey coverage** — if a journey is `done`, suggest the capabilities it
   crosses that aren't done yet.
4. **Taxonomy order** — fall back to the order from Phase 2.

Always give a ONE-sentence reason for the suggestion, grounded in the scan
(shared model, route adjacency, journey membership). Never invent priority —
if you can't justify it from signal, say "no strong signal; suggesting by
taxonomy order".

### Selector actions

- **document (suggested or picked)** → set the topic's status to `in progress`
  in state, write its detail block, go to Step 2.
- **add** → the user names a screen/area not on the map. Verify where it lives
  in code (`find`/grep its route or component) before adding — this is how
  taxonomy stays honest. Add the capability/journey to `taxonomy.json` and a row
  to the Topics table, then offer to document it. (This is the mid-stream
  amendability the bulk mode lacked.)
- **sync** → load `references/sync-flow.md`, run it, return to the selector.
- **stop** → save state, exit gracefully (in `{lang}`): *"Paused. 3/23 topics
  done. Re-invoke the skill anytime — I'll show this menu again."*

### Internal-only / deprecated screens — the whole point

If the user picks (or you would suggest) something that's an internal admin
screen, a deprecated flow, or a non-user-facing area, **flag it and let the
user decide**:

> `feature-flags-admin` looks like an internal-only screen (route under
> `/admin`, no end-user i18n keys). Document it anyway, or skip?

This is exactly the failure the bulk mode had — it documented everything. Here
the human chooses, so internal/dead screens simply never enter the loop unless
explicitly wanted.

## Step 2 — Phase 4 (draft)

Load `references/phase-4-pass1-drafts.md`. Scope: ONLY this topic's articles.

- One article per sub-agent (core principle 4 + batch sizing).
- Offer one-at-a-time so the user can judge quality before paying for the whole
  topic: *"Draft the overview first so you can check the style, then the rest?"*
- Each draft logs its pending questions into the topic's question list in state.
- Commit after the topic's drafts: `phase-4: draft <topic>`.
- Update the topic status to `drafted`.

## Step 3 — Phase 5.5 (code-first triage)

Load `references/phase-5.5-triage.md`. Scope: ONLY this topic.

- One article-pair per sub-agent.
- Auto-answers questions with literal `file:line` evidence; patches divergent
  articles; leaves intent/UX/experience questions as `needs_human`.
- Commit: `phase-5.5: auto-fix from code (<topic>)`.
- Update topic status to `triaged`.

## Step 4 — Phase 6 (coverage-aware interview)

Load `references/phase-6-refinement.md`. Scope: ONLY this topic's surviving
`needs_human` questions.

This is where the per-topic depth is won: a focused interview about one domain,
opening with a free-form question, with each answer re-checked against every
other open question of the topic. Update topic status to `interviewed`.

## Step 5 — Phase 7 (topic update)

Load `references/phase-7-global-update.md`. Scope: ONLY this topic's articles
affected by the answers.

- One article per sub-agent.
- Substitute provisional answers with confirmed ones; remove 🟡 from tech guides.
- Commit: `phase-7: apply answers (<topic>)`.
- Update topic status to `updated`.

## Step 6 — Close the topic

1. Final commit: `topic: close <topic>`.
2. Set the topic's status to `done` in the Topics table; collapse its
   in-progress detail block (keep the row).
3. Fold answered questions into the article front-matter; the interview
   transcript stays in `.livedocs/interview/<topic>/`.
4. Write a "Next-topic recommendation" into state for when the user returns.
5. **Nudge sync, don't run it** (in `{lang}`):

   > `recurring-billing` is done (3 articles). Cross-links to other topics
   > aren't drawn yet — that's the sync step, which runs over the whole doc set
   > when you want. Run sync now, document another topic, or stop?

6. Return to the selector (Step 1).

## What the loop NEVER does

- **No cross-linking between topics.** That's sync's job. A freshly closed topic
  has no `## Veja também` links to other topics yet — and that's correct.
- **No global dedup.** Questions are scoped to the topic; dedup, if needed at
  all, is a single inline pass over a handful of questions.
- **No auto-advance.** After a topic closes, always return to the selector and
  wait. Documenting the next topic is the user's explicit choice.
- **No drafting of unpicked topics.** Only the selected topic gets touched.

## Resume behavior

On re-invocation with Init/Map done:
1. Read the Topics table + the in-progress detail block.
2. If a topic is mid-loop (status between `drafted` and `updated`), offer to
   resume it exactly where it stopped before showing the full selector.
3. Otherwise show the selector with the saved next-topic recommendation.

## Pitfalls

- **Suggesting a topic with no signal-based reason.** Don't fabricate priority.
  Say so and fall back to taxonomy order.
- **Forgetting to flag internal/deprecated screens.** The loop's value over bulk
  mode is precisely this gate — use it.
- **Letting a topic's pending questions leak into another topic.** Each topic's
  questions are independent. Do not carry them across the loop.
- **Running sync automatically to "be helpful".** It's on-demand by design;
  the user owns when links get reconciled.
- **Drafting all of a topic's articles in one sub-agent to "save a turn".**
  Quality collapses (core principle 4). One article per sub-agent even inside a
  single topic.
