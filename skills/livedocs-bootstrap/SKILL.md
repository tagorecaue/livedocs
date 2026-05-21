     1|---
     2|name: livedocs-bootstrap
     3|description: |
     4|  Bootstrap living documentation for a SaaS codebase via guided conversation. Use when
     5|  the user wants to document an existing system from scratch (or fill gaps) — produces
     6|  paired product + technical guides organized as Categories (capabilities) and Articles,
     7|  with cross-links, pending questions, and screenshot TODOs. Drives the whole 7-phase
     8|  flow without leaving the chat.
     9|version: 1.0.0
    10|author: Tagore + LiveDocs
    11|---
    12|
    13|# LiveDocs Bootstrap — Standalone Skill
    14|
    15|You are about to bootstrap **living documentation** for a SaaS project. This skill
    16|replaces the Python CLI: the entire 7-phase flow runs inside this conversation,
    17|with you as the orchestrator and the user as the maintainer.
    18|
    19|The output is a `docs/` directory full of paired markdown files:
    20|
    21|```
    22|docs/
    23|├── capacidades/
    24|│   ├── <capability-slug>/
    25|│   │   ├── <article-slug>.md           ← product flavor (end-user)
    26|│   │   ├── <article-slug>.tech.md      ← technical flavor (devs)
    27|│   │   └── ...
    28|│   └── ...
    29|└── jornadas/
    30|    ├── <journey-slug>.md
    31|    ├── <journey-slug>.tech.md
    32|    └── ...
    33|```
    34|
    35|Plus a state file you maintain to track progress:
    36|
    37|```
    38|.livedocs/
    39|└── state.md          ← checklist + pending questions + screenshot TODOs
    40|```
    41|
    42|## When to use this skill
    43|
    44|- The user asks to "document the project", "create a help center", "use livedocs",
    45|  "bootstrap docs", "generate documentation for this codebase", or similar.
    46|- You're inside a SaaS / web app repo (Vue/React/Next/etc) with code worth documenting.
    47|- The user has `graphify` installed (recommended but not required). Check with
    48|  `which graphify`. If missing, warn and continue without graph signal.
    49|
    50|## When NOT to use this skill
    51|
    52|- The user wants to read existing docs → just open them.
    53|- Single ad-hoc README → write it directly, no ceremony needed.
    54|- Codebase is tiny (<10 files) → overkill.
    55|
    56|---
    57|
    58|## The 7 phases
    59|
    60|You will walk the user through these in order. **One phase at a time.** Don't
    61|skip ahead. After each phase, save state and ask explicit consent to continue.
    62|
    63|| # | Phase | What happens | LLM cost |
    64||---|---|---|---|
    65|| 0 | Guidance | User dumps free-form context about the product | 0 |
    66|| 1 | Scan | Run graphify + extract routes/i18n/models | 0 (graphify uses LLM separately) |
    67|| 2 | Taxonomy | Propose capabilities + journeys from the scan | 1 call |
    68|| 3 | Review | User edits/approves the taxonomy | 0–N (split is N calls) |
    69|| 4 | Pass 1 | Draft each article in isolated context | N calls (1 per article) |
    70|| 5 | Pass 2 | Cross-link articles, harmonize terms | N calls (lighter) |
    71|| 6 | Refinement | Batch-ask pending questions to user | 1 dedup call + interview |
    72|| 7 | Global update | Rewrite affected articles with answers | M calls (affected only) |
    73|
    74|**Always offer to run phase 4 in batches** — by capability — so the user can
    75|evaluate quality before spending the full cost.
    76|
    77|---
    78|
    79|## Phase-by-phase instructions
    80|
    81|Each phase has a detailed reference. Load it when you enter that phase:
    82|
    83|- **Phase 0** — `references/phase-0-guidance.md`
    84|- **Phase 1** — `references/phase-1-scan.md`
    85|- **Phase 2** — `references/phase-2-taxonomy.md`
    86|- **Phase 3** — `references/phase-3-review.md`
    87|- **Phase 4** — `references/phase-4-pass1-drafts.md`
    88|- **Phase 5** — `references/phase-5-pass2-stitching.md`
    89|- **Phase 6** — `references/phase-6-refinement.md`
    90|- **Phase 7** — `references/phase-7-global-update.md`
    91|
    92|Shared formats and conventions:
    93|
    94|- **Article markdown structure** — `references/article-format.md`
    95|- **State file format** — `references/state-format.md`
    96|- **Screenshot TODOs** — `references/screenshot-todos.md`
    97|- **Pending questions** — `references/pending-questions.md`
    98|
    99|---
   100|
   101|## Starting the bootstrap
   102|
   103|When invoked, do these in order **without asking permission** — this is the
   104|canonical entry sequence:
   105|
   106|1. **Read state if exists.** Run `cat .livedocs/state.md 2>/dev/null` (or
   107|   equivalent). If it has content, parse the "Current phase" line and
   108|   resume from there — announce: *"Retomando bootstrap da fase N. Continue?"*
   109|
   110|2. **If no state yet, greet and confirm intent.** Brief message:
   111|   > *"Olá! Vou guiar o bootstrap da documentação deste projeto. São 7 fases,
   112|   > leva cerca de 2-4h de trabalho (mais o tempo das chamadas LLM). Posso
   113|   > começar pela fase 0?"*
   114|
   115|3. **On user OK, load `references/phase-0-guidance.md`** and follow it.
   116|
   117|4. **At every save**, write to `.livedocs/state.md`. **At every transition**,
   118|   tell the user what changed and ask consent for next phase.
   119|
   120|---
   121|
   122|## Core principles (read once, follow always)
   123|
   124|1. **DELEGATE braçal work to sub-agents.** This is critical. Your platform
   125|   likely supports spawning child agents (Task tool, delegate_task, etc.) — USE
   126|   THEM for: graphify execution monitoring, file extraction (routes/i18n/models
   127|   scans), each individual article draft in phase 4, each stitching pass in 5,
   128|   each global update in 7. Keep YOUR main context for orchestration,
   129|   decision-making, and conversation with the user.
   130|
   131|   The orchestrator (you) should be the ONE place that knows the full state.
   132|   Sub-agents return summaries — JSON or short text — not full markdown blobs.
   133|   If you let phase 4 drafts pollute your context, by article 10 you'll lose
   134|   track of what's happening.
   135|
   136|   Rule of thumb: anything that involves reading >5 code files or producing
   137|   >2KB of output → sub-agent. Anything conversational with the user or
   138|   small (under 500 chars in/out) → handle directly.
   139|
3. **Evidence-first.** Every claim in a guide MUST be backed by either:
   (a) `file:line` code reference, (b) user-confirmed answer, or
   (c) inheritance from another guide. No invention. Mark 🟡 hypotheses
   in tech guides; never in product guides.

4. **Isolated context per draft.** In phase 4, each article gets its OWN focused
   sub-task. Don't try to draft 20 articles in one shot — quality collapses.
   Use separate tool calls / sub-agents when your platform supports it.

5. **Capability = Category, Article = Page.** Maximum 2 levels of hierarchy.
   This maps directly to Chatwoot (the target help-center). No grandchildren.

6. **Two flavors, same domain.** Each article has `.md` (product, zero jargon)
   and `.tech.md` (technical, with code refs). They never cross-link to each
   other; cross-links go to OTHER same-flavor guides.

7. **Pending questions, not invented answers.** When code doesn't reveal
   intent / UX rationale / external integration details, write a pending
   question. Phase 6 batches them.

8. **Screenshot TODOs are structured.** When mentioning a concrete UI route,
   insert the admonition (see `references/screenshot-todos.md`) AND register
   in state. Both happen together, always.

9. **User approves transitions.** Never silently jump from phase 4 to 5.
   Always: *"Lote concluído. Avançar pra Pass 2 ou gerar mais artigos primeiro?"*

10. **State is sacred.** Persist after every phase, every batch, every save.
    If the conversation crashes, the user re-invokes the skill and you read
    state to continue exactly where you stopped.
   186|
   187|---
   188|
   189|## Cost discipline
   190|
   191|For each LLM call in phases 2/4/5/7, mentally estimate cost based on prompt
   192|size + expected output. Tell the user before expensive calls:
   193|
   194|> *"Vou rodar a Pass 2 em 4 artigos. Cada chamada lê o conteúdo dos artigos
   195|> e o índice dos demais — uso típico ~$0.05 por artigo. Custo estimado: $0.20.
   196|> OK?"*
   197|
   198|In phase 4 (the expensive one), ALWAYS offer batch-by-capability instead of
   199|all-at-once. A 60-article system at $0.30 each is $18 — the user might want
   200|to do 2 capabilities ($2-3), evaluate quality, then continue.
   201|
   202|---
   203|
   204|## Failure modes — what to do
   205|
   206|- **Graphify missing**: warn, continue without graph signal. Other scan
   207|  sources (routes/i18n/models) still drive taxonomy.
   208|- **Conversation context fills up**: tell the user, offer to compact the
   209|  state file (drop completed phase details) and restart fresh.
   210|- **User abandons mid-phase**: save partial state, exit gracefully. They
   211|  resume by re-invoking the skill.
   212|- **You wrote a wrong article**: don't silently fix. Tell the user, propose
   213|  what to change, get OK, then patch.
   214|- **You drift from the skill**: re-read this SKILL.md. Common drift =
   215|  inventing content, skipping evidence, abandoning state tracking.
   216|
   217|---
   218|
   219|## Quick reference card
   220|
   221|| Command (mental) | What you do |
   222||---|---|
   223|| "começar" / "iniciar" | Phase 0 → ask for guidance text via editor |
   224|| "continuar" | Read state, resume from current phase |
   225|| "qual a próxima fase?" | Tell user, don't auto-advance |
   226|| "voltar fase X" | Confirm, mark X as current in state, re-execute |
   227|| "status" | Summarize state.md in 5 lines |
   228|| "qual o custo até agora?" | Sum the cost annotations from state.md |
   229|
   230|Now load `references/phase-0-guidance.md` when the user is ready to begin.
   231|