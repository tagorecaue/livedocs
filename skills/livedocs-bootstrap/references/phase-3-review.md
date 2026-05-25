# Phase 3 — Taxonomy Review

## Goal
Let the user edit the proposed taxonomy until they're happy with it. This is
conversational — you propose, they react, you patch the JSON.

All chat strings shown below are illustrative (in English). Render them
in `{lang}` when speaking to the user.

## What to do

1. **Show the current state** of `.livedocs/taxonomy.json` as a menu
   (illustrative; render in `{lang}`):

   ```
   Current taxonomy — 18 capabilities, 5 journeys

   CAPABILITIES
     1. recurring-billing   (1 article)
     2. resident-onboarding (1 article)
     ...

   JOURNEYS
     J1. first-invoice
     ...

   Available actions:
     [i] inspect capability N — show routes, models, files in scope
     [s] split capability N — AI proposes N articles (cost ~$0.05)
     [A] manage articles of capability N — edit manually
     [r] rename capability N
     [m] merge capabilities N+M
     [x] remove capability N
     [+] add capability
     [J] manage journeys (analogous)
     [a] approve and advance to Phase 4
     [q] quit (saves state)

   What do you want to do?
   ```

   When rendering the labels, translate to `{lang}` but **keep the
   bracketed letter shortcuts** (`[i]`, `[s]`, `[a]`, etc.) — those
   are the input contract, not prose.

2. **Wait for user choice.** Execute the action and re-render the menu.
   Loop until user picks `[a]` or `[q]`.

### Action: inspect (`[i]`)

Filter routes/models from the cache by the capability's `code_anchors`.
Output illustrative; render in `{lang}`:

```
project-management — "<title>"
  code_anchors:
    - src/projects/** (87 files)
    - src/views/Projects/** (23 files)
  Routes inside:
    /projects                    (list/kanban)
    /projects/new
    /projects/:id
    /projects/:id/financial
    /projects/:id/team
  Models touched: Project, ProjectMember, ProjectConfig, ProjectStage
```

Zero LLM. Pure filtering.

### Action: split (`[s]`)

This IS an LLM call. Estimate cost: ~$0.05 per split. Confirm before running.

Prompt to the sub-agent:

> For the capability `{capability_slug}` whose anchors are `{anchors}`,
> propose 2–7 articles representing sub-areas / sub-flows.
>
> Routes inside: <filtered routes>
> Models touched: <filtered models>
> User guidance: <user guidance>
> Output language: `{lang}` (titles, summaries; slugs in kebab-case
> ASCII fold of `{lang}` words).
>
> Each article: slug (kebab-case), title, summary (1 line), is_intro
> (exactly 0 or 1 set to true). code_anchors of the article must be a
> refinement of the parent capability's anchors.
>
> Output strict JSON: {"articles": [{...}]}

Show the proposal, sub-menu (illustrative; in `{lang}`):
```
[a]ccept  [r]ename N  [+]add  [x]remove N  [c]ancel
```

If accepted, replace `capability.articles` with the new list. Save.

### Action: manage articles (`[A]`)

Sub-loop. Zero LLM. Rename / remove (keep ≥1) / add / move anchors /
toggle `is_intro` / back.

### Action: rename / merge / remove / add

Straightforward edits to `.livedocs/taxonomy.json`. After each edit,
re-render the top menu.

When merging A into B:
- Concatenate code_anchors (dedup)
- Concatenate articles (rename conflicts: `<slug>-from-B`)
- Update journey refs that mentioned A → now mention B

### Action: approve (`[a]`)

Set `approved_at` to current ISO timestamp in `.livedocs/taxonomy.json`.
Update state.md to mark Init/Map done (phase 3 complete).

Show summary (illustrative; render in `{lang}`):
```
✓ Taxonomy approved: 22 capabilities, 5 journeys (27 topics)

This is the MAP. We don't document everything now — we go one topic at a
time, you pick each one. Per-topic cost is roughly:
  - $0.30–$1.00 per article to draft, + light triage/interview/update
  - You'll see an estimate before each topic, and pay only for what you pick

The taxonomy stays editable: you can add a topic later if we discover one
that's missing.
```

Then load `references/topic-loop.md` and open the topic selector — it will
suggest a first topic. Don't auto-draft anything; the user picks.

## Pitfalls

- **User goes back and forth a lot**: that's fine. Just keep saving after each
  edit. Don't pressure them.
- **User splits 18 capabilities to 60+ articles**: warn about cost.
- **User wants to delete a journey referenced by capabilities**: just remove,
  capabilities don't reference journeys.
- **Slug collisions**: when adding/renaming, check for duplicates within the
  same capability. Reject with helpful message.
