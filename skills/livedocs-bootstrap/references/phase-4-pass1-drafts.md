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
   - When the article mentions a concrete UI route (e.g. `/projects/new`), insert IMMEDIATELY after that paragraph:

     > [!TODO:screenshot]
     > Rota: `/path`
     > Descrição: <what this screen shows>

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
