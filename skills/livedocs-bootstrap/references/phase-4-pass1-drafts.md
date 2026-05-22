# Phase 4 — Pass 1: Isolated Drafts

## Goal
For each article + journey in the approved taxonomy, write the FIRST draft of
both `<slug>.md` (product flavor) and `<slug>.tech.md` (technical flavor).
Each draft happens in **isolated context** — the agent only sees: the
guidance, the menu index (titles only, no bodies), the article's code anchors,
and the style.

This is the most expensive phase. Default to **batch-by-capability** to let
the user evaluate quality and budget.

## What to do

> **DELEGATION**: Phase 4 is the BIG ONE for sub-agent usage. Each article
> draft reads code files and produces ~5-20KB of markdown. Doing them in
> your main context kills you by article 5. Rules:
>
> - Spawn ONE sub-agent per article (or in parallel batches if your
>   platform supports concurrent sub-agents).
> - Pass the full prompt template + paths it needs to read.
> - Sub-agent uses Write tool to create the .md files directly.
> - Sub-agent returns ONLY the JSON envelope ({files_written,
>   pending_questions, screenshot_todos}).
> - You (the orchestrator) update state.md based on the JSON — you
>   never read the generated articles.
>
> This is what makes the skill scalable. 67 articles is doable; 67
> articles in your main context is not.

1. **Open the batch selector:**

   ```
   Pass 1 — gerar rascunhos

   Pendentes: 66 artigos (17 capacidades, 5 jornadas)
   Já prontos: 1 artigo

   Opções:
     [1] Gerar tudo o que falta (66 artigos, ~$20)
     [2] Escolher capacidades (multi-seleção)
     [3] Só jornadas (5 artigos)
     [4] Sair e continuar depois

   O que você prefere?
   ```

2. **Wait for the user's choice.** Compute the target list:
   - "tudo" → todos articles + journeys with status≠drafted
   - "escolher" → asks which capability slugs (multi-select)
   - "só jornadas" → only the journeys

3. **For each target article, generate independently.** This is the part that
   benefits from sub-agents / parallel tool calls if your platform supports
   them. If not, sequential is fine — but ALWAYS print progress:

   ```
   [3/12] iniciando: gestao-projetos/criar-projeto…
   ```

   Time-check before the call. Use the prompt template below.

4. **Prompt template** for each article draft:

   ```
   # Task: draft this article

   ## About this article
   - capability: <capability slug + title>  (or "journey" if it's a journey)
   - article slug: <slug>
   - article title: <title>
   - article summary: <summary>
   - is_intro: <true|false>
   - code_anchors (read these files): <list>

   ## Sibling articles in the same capability (just slugs+titles, no bodies)
   <siblings list>

   ## Maintainer guidance
   <full guidance.md content>

   ## Style (target voice)
   <contents of .livedocs/style.md if it exists, else: "tutorial conversacional, pt-BR, sem jargão técnico no .md de produto">

   ## Rules

   - You are in ISOLATED context. You don't see other articles' bodies, only titles.
   - When you want to reference another guide, write `[TODO:link={slug}]`. Phase 5 resolves.
   - When the code doesn't reveal intent/UX/integration, register a pending question — don't invent.
   - Each pending question: { question, provisional_answer (your best guess from code), confidence (low/high) }.

   ### Pending questions — bar for registering

   **Guiding principle: a pending question is about INTENT or EXPERIENCE,
   not about EXISTENCE or VALUE.**

   - Existence and value live in code. Read it harder.
   - Intent ("why was this designed this way?") and experience
     ("what do support tickets ask about this screen?") live in the
     user's head. Those are the questions worth asking.

   🚫 Do NOT register questions like (these are auto-answerable):
   - "What's the label for enum X?" → read the template / i18n / formatter
   - "What are the valid values of enum X?" → read the migration / schema
   - "Where is cron job Y?" → grep `src/cron/`
   - "Does ADR-NNNN exist?" → `ls docs/adr/` or grep
   - "Is column Z nullable?" → read the schema/migration
   - "What's the shape of jsonb J?" → read the TS interface / Zod schema
   - "Does function W exist?" → grep
   - "What endpoint does button B hit?" → read its click handler
   - "What's the exact toast text?" → grep the codebase

   ✅ DO register questions like:
   - "Why was this designed to do A instead of B?"
   - "Top 3 dúvidas support actually gets about this screen?"
   - "Is feature F still used or dead code nobody removed?"
   - "When entity A is transferred, what happens to scheduled job J?"
   - "Race condition between two writers — intentional or risk?"
   - "External API returns 429 — what should the UX do?"

   See `references/pending-questions.md` for the full heuristic.
   Phase 5.5 will filter out 🚫-pattern questions and patch the article
   if the answer is in the code — but it's cheaper to never write them.

   ### UI language (HARD RULE — applies to the product `.md` only)

   - Write in the SAME language the product UI uses. Default for this repo: pt-BR.
   - NEVER paste a foreign-language word, a DB enum value, a code constant, a
     field/column name, a function name, or a route inline in product prose.
     Forbidden examples: `before_tax`, `auto_split`, `REURB_S`, `started_at`,
     `split_distribution`, `localStorage`, `endpoint`, `mutation`, `enum`.
   - When a constant appears in code, HUNT for the user-visible label that
     represents it. Where to look (in this order): Vue/React templates near
     the field, `:items=` arrays in selects, `t()` / `$t()` i18n keys (note:
     this codebase has decaying i18n, prefer the inline templates), `text:` /
     `label:` props, `computed` getters that translate enum → display text,
     `<option>` children, formatter functions.
   - Use the visible label in the `.md`. If you can't find it, register a
     pending question (`"Qual é o texto exibido para X?"`) and put a
     descriptive placeholder in pt-BR, never the raw constant.
   - Self-check before writing each paragraph: would a non-technical user
     understand this sentence without opening the codebase? If no, rewrite.
   - Tech detail (constants, enum values, columns, file:line, routes) goes in
     `.tech.md` — that's where it belongs.

   ### Screenshot TODOs (BE GENEROUS in the product `.md`)

   - Target: roughly 1 screenshot every 2-4 paragraphs in operational
     sections. When in doubt, write the TODO — a reviewer can drop it.
   - Trigger a TODO whenever prose mentions any of:
     * a concrete route (`/path`)
     * a sidebar / panel / drawer / modal / dialog / tab
     * a named button or action
     * a list, grid, kanban column, chart
     * an empty / success / error state
     * a step inside a wizard or multi-step flow
     * a settings section reachable from a named menu item
   - Insert the admonition IMMEDIATELY after the paragraph that mentions the
     surface. Use `Local:` for non-route surfaces:

     ```markdown
     > [!TODO:screenshot]
     > Local: barra lateral do projeto → seção "Parceiros e splits"
     > Rota base: `/project/:project`
     > Descrição: <o que essa superfície mostra, com contexto suficiente>
     ```

     For pure-route surfaces:

     ```markdown
     > [!TODO:screenshot]
     > Rota: `/pre-projects`
     > Descrição: <o que essa tela mostra>
     ```

   - One screenshot, one TODO. Don't bundle multiple screens in one block.

   - Generate TWO files using the Write tool:
     * `docs/<kind>/<cap-slug>/<article-slug>.md` (product flavor, idioma pt-BR)
     * `docs/<kind>/<cap-slug>/<article-slug>.tech.md` (technical flavor, same lang)
     * For journeys: `docs/jornadas/<slug>.md` and `.tech.md` (flat, no subdir)
   - Front-matter on both:
     ```yaml
     ---
     slug: <cap-slug>/<article-slug>     # or just <slug> for journeys
     title: <title>
     kind: capability                     # or "journey"
     status: drafted
     generated_at: "<ISO date>"
     ---
     ```

   ## If this article is is_intro=true

   This is the OVERVIEW article of its capability. Special rules:
   - Resumo do domínio inteiro da capacidade.
   - Linka os irmãos com `[TODO:link=<cap>/<sibling-slug>]`.
   - NÃO entre no detalhe operacional dos irmãos — cada um tem artigo próprio.

   ## Prior interview pass (when previous answered interviews exist)

   Before drafting, scan `.livedocs/interview/` and `.livedocs/answered/`
   for any prior `.interview.md` files relevant to this article's
   capability or topic. If you find prior answers:

   1. Read them. They are HIGHER PRIORITY than your own inference.
   2. Compare the prior human answers with what the code shows NOW.
   3. If they AGREE → use the human's wording in the draft (.md), the
      code's facts in .tech.md.
   4. If they DISAGREE → generate ONE pending question of `category: E`
      (code-suggested edges) with `confidence: high`, of the form:
      `"O draft anterior diz X, mas o código no arquivo Y:linha Z mostra
      W. Qual versão é a correta hoje?"`. Cite both sides literally.
   5. DO NOT generate a pending question for facts the human already
      answered in a prior interview, unless the code now contradicts
      the answer.

   This is the path to living docs: each new pass refines, never reinvents.

   ## Output

   Return ONLY JSON (no prose):

   ```json
   {
     "files_written": [
       "docs/.../slug.md",
       "docs/.../slug.tech.md"
     ],
     "pending_questions": [
       {"question": "...", "provisional_answer": "...", "confidence": "low"}
     ],
     "screenshot_todos": [
       {"route": "/path", "description": "..."}
     ]
   }
   ```
   ```

5. **After each call**, verify the files exist on disk. If missing, mark
   this article as `pending` in state, warn user, continue with the next.

6. **Update state.md** after each article (incremental — survives crash):
   - bump `drafted` count
   - append pending questions to the state's pending list
   - append screenshot TODOs to the state's screenshot list
   - record cost (extract from your platform if possible, else estimate)

7. **At the end of the batch:**
   ```
   ✓ Lote concluído — 4 artigos gerados (custo total ~$1.40)
   Ainda faltam 62 artigos. Próximo passo:
     - Rodar outro lote da Phase 4
     - Avançar pra Phase 5 (vai stitchar SÓ os 4 atuais)
     - Sair

   O que prefere?
   ```

## Pitfalls

- **Article writes nothing on disk**: agent claimed `files_written` but they're
  not there. Mark `pending`, warn, continue.
- **Article gets HUGE**: if a tech.md goes >50KB, it's probably padded. Note
  it for phase 5 review.
- **Cost runs away**: total > 2x estimate → pause, summarize for user, ask
  to continue or stop.
- **User abandons mid-batch**: state.md must be up-to-date. Re-invocation
  resumes correctly.
- **Sibling articles get cross-referenced**: that's why we use TODO:link
  placeholders. Don't try to write real links here — phase 5's job.
- **is_intro article doesn't link to siblings**: re-prompt or patch. Intro
  articles MUST have outbound TODO:link to all siblings.
