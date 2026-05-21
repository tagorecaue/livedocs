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
`.livedocs/taxonomy.json` — proposed structure:

```json
{
  "capabilities": [
    {
      "slug": "cobranca-recorrente",
      "title": "Cobrança recorrente",
      "summary": "Cobrança automatizada de mensalidades com régua de inadimplência.",
      "code_anchors": ["src/billing/**", "src/jobs/charge.ts"],
      "articles": [
        {"slug": "introducao", "title": "Visão geral de cobrança", "is_intro": true, "summary": "...", "code_anchors": ["src/billing/**"]}
      ]
    }
  ],
  "journeys": [
    {"slug": "primeira-fatura", "title": "Da unidade cadastrada à primeira fatura paga", "summary": "...", "capability_refs": ["cobranca-recorrente", "onboarding-morador"]}
  ]
}
```

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
   > Rules:
   > - Capability slugs: kebab-case in the user's language (pt-BR or en)
   > - Each capability starts with 1 article (`introducao`, is_intro=true). You can propose more articles per capability if the area is rich (max 7 articles per capability).
   > - Don't make a capability per route — group related routes into capabilities.
   > - Use the user's guidance to disambiguate names (e.g. if they say "moradores" not "users", use moradores).
   > - Don't invent functionality not in the signals.
   > - Output ONLY the JSON, no prose.

3. **Save** the resulting JSON to `.livedocs/taxonomy.json`.

4. **Render a human-readable preview** for the user:

   ```
   Taxonomia proposta — 18 capacidades, 5 jornadas

   CAPACIDADES
     1. cobranca-recorrente   "Cobrança recorrente"
        Cobrança automatizada de mensalidades...
        ▸ 1 artigo: introducao
     2. ...

   JORNADAS
     J1. primeira-fatura      "Da unidade cadastrada à primeira fatura paga"
         → cobranca-recorrente, onboarding-morador
     ...
   ```

   Save to `.livedocs/taxonomy-preview.md` for the user to read.

5. **Update state.md**, ask:

   > Taxonomia proposta salva em `.livedocs/taxonomy-preview.md`. Próxima fase
   > (3) é a revisão — você pode renomear, mesclar, remover, inspecionar
   > capacidades, ou pedir pra eu SPLITTAR uma em mais artigos (1 chamada LLM
   > a mais por split, ~$0.05).
   >
   > Quer abrir o preview ou já entrar no menu de revisão?

## Pitfalls

- **Too many capabilities** (>30): the agent over-fragmented. Suggest to user
  to mesclar some, or re-prompt with stricter rules.
- **Too few** (<8): under-fragmented. Probably a small repo OR the agent was
  too conservative. Show to user and offer to "split-all" via phase 3 actions.
- **Capability with 0 articles**: shouldn't happen, but if it does, add a
  default introducao article matching the capability's slug/title.
- **Jornadas referencing slugs that don't exist**: validate refs, drop broken ones.
