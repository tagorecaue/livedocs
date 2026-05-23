# Phase 2 — Taxonomy proposal

## Goal
Propose a list of **capabilities** (= help-center categories) and **journeys**
(cross-cutting flows) that organize what the codebase does, from the user's
perspective. This is the structure of the help center menu.

## Inputs
- `.livedocs/guidance.md`
- `.livedocs/cache/routes.json`, `i18n.json`, `models.json`
- `.livedocs/cache/graphify-out/graph.json` (if available)

## Output
`.livedocs/taxonomy.json` — proposed structure (titles, summaries, and
slugs are in `{lang}`; keys stay English):

```json
{
  "capabilities": [
    {
      "slug": "recurring-billing",
      "title": "<title in {lang}>",
      "summary": "<one-sentence summary in {lang}>",
      "code_anchors": ["src/billing/**", "src/jobs/charge.ts"],
      "articles": [
        {"slug": "overview", "title": "<title in {lang}>", "is_intro": true, "summary": "...", "code_anchors": ["src/billing/**"]}
      ]
    }
  ],
  "journeys": [
    {"slug": "first-invoice", "title": "<title in {lang}>", "summary": "...", "capability_refs": ["recurring-billing", "resident-onboarding"]}
  ]
}
```

The example slugs above are English illustrations. In an actual pt-BR
run, slugs would be `cobranca-recorrente`, `primeira-fatura`, etc. —
the sub-agent picks slug language based on `{lang}` from state.

## What to do

1. **Compact the scan signals** so they fit the context window:
   - Routes: cap at 100 entries, prefer ones whose file path looks "feature-y"
   - i18n: filter keys matching `menu.*`, `nav.*`, `sidebar.*`, `routes.*` (navigation labels). If fewer than 50 such keys, include all.
   - Models: name + first 5 fields each, max 50 models
   - Graph: top-level cluster summary only (folder → node count), not full nodes

2. **Generate the proposal.** Use this prompt to yourself / to a sub-agent:

   > Analyze the codebase signals below. Propose a help-center taxonomy with:
   > - 10–25 capabilities (= categories users can recognize as separate areas of the product)
   > - 3–10 journeys (= cross-cutting flows worth a guide of their own, end-to-end)
   >
   > The user's language is `{lang}` (from state.md `Lang:`).
   >
   > Rules:
   > - Capability slugs: kebab-case, ASCII-fold of words IN `{lang}` (e.g.
   >   `cobranca-recorrente` for pt-BR, `recurring-billing` for en).
   > - Capability/article titles and summaries: in `{lang}`.
   > - Each capability starts with 1 article whose slug is the `{lang}`
   >   equivalent of "overview" or "introduction" (e.g. `introducao` in
   >   pt-BR, `overview` in en), with `is_intro=true`. You can propose
   >   more articles per capability if the area is rich (max 7 articles
   >   per capability).
   > - Don't make a capability per route — group related routes into capabilities.
   > - Use the user's guidance to disambiguate names (e.g. if they use a
   >   specific term for an actor or domain object, prefer that).
   > - Don't invent functionality not in the signals.
   > - Output ONLY the JSON, no prose.

3. **Save** the resulting JSON to `.livedocs/taxonomy.json`.

4. **Render a human-readable preview** for the user (render headers and
   summary text in `{lang}` — example below shown in English):

   ```
   Proposed taxonomy — 18 capabilities, 5 journeys

   CAPABILITIES
     1. recurring-billing   "<title>"
        <one-line summary>...
        ▸ 1 article: overview
     2. ...

   JOURNEYS
     J1. first-invoice      "<title>"
         → recurring-billing, resident-onboarding
     ...
   ```

   Save to `.livedocs/taxonomy-preview.md` for the user to read.

5. **Update state.md**, ask (render in `{lang}`):

   > Taxonomy proposal saved at `.livedocs/taxonomy-preview.md`. Next
   > phase (3) is review — you can rename, merge, remove, inspect
   > capabilities, or ask me to SPLIT one into more articles (1 extra
   > LLM call per split, ~$0.05).
   >
   > Open the preview, or go straight to the review menu?

## Pitfalls

- **Too many capabilities** (>30): the agent over-fragmented. Suggest to user
  to mesclar some, or re-prompt with stricter rules.
- **Too few** (<8): under-fragmented. Probably a small repo OR the agent was
  too conservative. Show to user and offer to "split-all" via phase 3 actions.
- **Capability with 0 articles**: shouldn't happen, but if it does, add a
  default intro article using the `{lang}`-equivalent slug for "overview" or
  "introduction" (e.g. `overview` in en, `introducao` in pt-BR, `descripcion`
  in es) with `is_intro: true`, matching the capability's slug/title.
- **Jornadas referencing slugs that don't exist**: validate refs, drop broken ones.
