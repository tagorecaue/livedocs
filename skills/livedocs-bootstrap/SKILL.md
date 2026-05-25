---
name: livedocs-bootstrap
description: |
  Bootstrap living documentation for a SaaS codebase via guided conversation. Use when
  the user wants to document an existing system from scratch (or fill gaps) — produces
  paired product + technical guides organized as Categories (capabilities) and Articles,
  with cross-links, pending questions, and screenshot TODOs. Documents the project
  one topic at a time, driven from the chat.
version: 2.0.0
author: Tagore + LiveDocs
---

# LiveDocs Bootstrap — Standalone Skill

You are about to bootstrap **living documentation** for a SaaS project. This skill
replaces the Python CLI: the whole flow runs inside this conversation, with you as
the orchestrator and the user as the maintainer.

**The skill documents the project ONE TOPIC AT A TIME (incremental).** There is no
"document everything at once" mode — that was removed in v2.0 because, in real runs,
it (a) diluted article richness, (b) collapsed per-topic nuance during a global dedup,
and (c) swept in internal-only and deprecated screens that should never become user
docs. Letting the maintainer pick each topic keeps the junk out and the depth in.

The overview the old bulk mode provided still exists: the graph (graphify) plus the
Init/Map phases (scan + taxonomy + review) give you the global picture without having
to draft everything.

The output is a `docs/` directory full of paired markdown files. The
top-level directory names render in `{lang}` (the language chosen in
Phase 0):

```
docs/
├── <capabilities-dir>/         ← e.g. "capabilities/" (en) or "capacidades/" (pt-BR)
│   ├── <capability-slug>/
│   │   ├── <article-slug>.md           ← product flavor (end-user)
│   │   ├── <article-slug>.tech.md      ← technical flavor (devs)
│   │   └── ...
│   └── ...
└── <journeys-dir>/             ← e.g. "journeys/" (en) or "jornadas/" (pt-BR)
    ├── <journey-slug>.md
    ├── <journey-slug>.tech.md
    └── ...
```

See `references/language-handling.md` for the lookup table per `{lang}`.

Plus a state file you maintain to track progress:

```
.livedocs/
└── state.md          ← checklist + pending questions + screenshot TODOs
```

## When to use this skill

- The user asks to "document the project", "create a help center", "use livedocs",
  "bootstrap docs", "generate documentation for this codebase", or similar.
- You're inside a SaaS / web app repo (Vue/React/Next/etc) with code worth documenting.
- The user has `graphify` installed (recommended but not required). Check with
  `which graphify`. If missing, warn and continue without graph signal.

## When NOT to use this skill

- The user wants to read existing docs → just open them.
- Single ad-hoc README → write it directly, no ceremony needed.
- Codebase is tiny (<10 files) → overkill.

---

## The execution model: Init/Map → Topic loop → Sync

The flow has three parts. **Init/Map runs once per project.** Then the **Topic loop**
runs once per topic, as many times as the maintainer wants, picking topics one at a
time. **Sync** is a separate, on-demand command that reconciles everything between
topics (cross-links, glossary, recommendations, stale detection) — it never runs
inside the loop.

### Init / Map — once per project

| # | Phase | What happens | LLM cost |
|---|---|---|---|
| 0 | Guidance | User dumps free-form context about the product | 0 |
| 1 | Scan | Run graphify + extract routes/i18n/models | 0 (graphify uses LLM separately) |
| 2 | Taxonomy | Propose capabilities + journeys from the scan | 1 call |
| 3 | Review | User edits/approves the taxonomy | 0–N (split is N calls) |

The taxonomy produced here is the **map** — it's how the Topic loop knows what
topics exist and what to suggest next. Unlike the old bulk mode, the taxonomy is
**amendable mid-stream**: a topic discovered later can be added without redoing
Init/Map.

### Topic loop — once per topic, repeated

The maintainer picks ONE topic (a capability or a journey) and the skill takes it
end to end, in isolation. Then it returns to the selector and suggests the next one.

| # | Phase | What happens (scoped to THIS topic only) | LLM cost |
|---|---|---|---|
| 4 | Draft | Draft the topic's articles in isolated context | N calls (1 per article) |
| 5.5 | Code-first triage | Re-answer questions from code, patch divergent articles | 1 call per article-pair |
| 6 | Refinement | Coverage-aware interview of the *surviving* questions | interview (mostly text) |
| 7 | Topic update | Rewrite the topic's articles with the answers | M calls (affected only) |

**There is no per-topic cross-linking.** Dedup, when needed, is intra-topic — small
enough to run inline, never the old two-pass global dedup.

**Phase 5.5 is critical** — it re-checks pending questions against code and patches
articles written without the answer, dramatically reducing the human interview burden.

**Always offer to run Phase 4 in one batch per article** so the user can evaluate
quality before spending the full cost of the topic.

After a topic closes (committed), the loop **nudges** the user: *"Topic done. Want
to run sync to refresh cross-links and the glossary?"* — it does not run sync itself.

### Sync — separate, on-demand command

Triggered when the user asks to *"sincronizar a documentação" / "sync docs" /
"sincronizar links e referências"*. Runs over the whole corpus, idempotent. Owns
everything that spans topics:

- cross-links bidirectional (product↔product, tech↔tech; never cross-flavor)
- glossary consolidation
- "next recommendation" in each domain `_index.md`
- `stale` detection (a guide whose `source_files` changed since scan)
- taxonomy drift (topics that emerged and aren't on the map)

Sync is the new home of the old Phase 5 stitching work. See
`references/sync-flow.md`.

---

## Phase-by-phase instructions

Each phase has a detailed reference. Load it when you enter that phase:

- **Phase 0** — `references/phase-0-guidance.md`
- **Phase 1** — `references/phase-1-scan.md`
- **Phase 2** — `references/phase-2-taxonomy.md`
- **Phase 3** — `references/phase-3-review.md`
- **Topic loop** — `references/topic-loop.md` (selector + next-topic suggestion)
- **Phase 4** — `references/phase-4-pass1-drafts.md`
- **Phase 5.5** — `references/phase-5.5-triage.md`
- **Phase 6** — `references/phase-6-refinement.md`
- **Phase 7** — `references/phase-7-global-update.md`
- **Sync** — `references/sync-flow.md` (on-demand cross-reference command)

Shared formats and conventions:

- **Language handling (READ FIRST)** — `references/language-handling.md`
- **Privacy and context boundaries** — `references/privacy.md`
- **Article markdown structure** — `references/article-format.md`
- **State file format** — `references/state-format.md`
- **Screenshot TODOs** — `references/screenshot-todos.md`
- **Pending questions** — `references/pending-questions.md`

---

## Starting the bootstrap

When invoked, do these in order **without asking permission** — this is the
canonical entry sequence:

1. **Read state if exists.** Run `cat .livedocs/state.md 2>/dev/null` (or
   equivalent). If it has content, parse the `Lang:` field and where the run
   stopped. Two resume shapes:
   - **Init/Map not finished** (phase 0–3 incomplete): resume that phase.
     Announce in `{lang}`: *"Resuming setup from phase N. Continue?"*
   - **Init/Map done** (taxonomy approved): enter the **Topic loop**. Read the
     per-topic statuses, announce in `{lang}` what's done and what's pending,
     then show the topic selector with a suggested next topic.

2. **If no state yet, greet and confirm intent.** Use the language you
   detect in the codebase (or English as default) for this first message
   — Phase 0 will let the user override. Brief message, equivalent to:

   > *"Hi! I'll help you document this project. First a one-time setup
   > (guidance, code scan, taxonomy), then we document one topic at a time —
   > you pick each topic, I take it end to end. Can I start with the setup?"*

3. **On user OK, load `references/phase-0-guidance.md`** and follow it.
   Phase 0 is where the run language is locked in (`Lang:` in state).

4. **After Init/Map (phase 3 approved), load `references/topic-loop.md`** and
   drive the loop: select a topic → Phase 4 → 5.5 → 6 → 7 → commit → nudge sync
   → back to selector.

5. **At every save**, write to `.livedocs/state.md`. **At every transition**,
   tell the user what changed (in `{lang}`) and ask consent to continue.

---

## Core principles (read once, follow always)

1. **DELEGATE the grunt work to sub-agents.** This is critical. Your platform
   likely supports spawning child agents (Task tool, delegate_task, etc.) — USE
   THEM for: graphify execution monitoring, file extraction (routes/i18n/models
   scans), each individual article draft in Phase 4, each Phase 5.5 triage, each
   Phase 7 topic update, and the per-corpus passes during Sync. Keep YOUR main
   context for orchestration, decision-making, and conversation with the user.

   The orchestrator (you) should be the ONE place that knows the full state.
   Sub-agents return summaries — JSON or short text — not full markdown blobs.
   If you let phase 4 drafts pollute your context, by article 10 you'll lose
   track of what's happening.

   Rule of thumb: anything that involves reading >5 code files or producing
   >2KB of output → sub-agent. Anything conversational with the user or
   small (under 500 chars in/out) → handle directly.

2. **Evidence-first.** Every claim in a guide MUST be backed by either:
   (a) `file:line` code reference, (b) user-confirmed answer, or
   (c) inheritance from another guide. No invention. Mark 🟡 hypotheses
   in tech guides; never in product guides.

3. **UI language in product guides = the language the user actually sees.**
    Hard rules for the `.md` (product flavor):

    - NEVER write a foreign-language word in prose when the product UI is in
      another language. The product `.md` is written entirely in `{lang}`
      (the language locked in Phase 0 and stored in `state.md` under `Lang:`).
    - NEVER leak DB enum values, code constants, technical identifiers,
      column names, function names, or route paths into product prose.
      Anything that looks like a snake_case or camelCase token, an SQL enum
      value, a path with slashes, or a function name — all forbidden in
      product prose.
    - When the code uses a constant (e.g. an enum value) to drive a UI
      control, the sub-agent MUST hunt for the human-visible label. Where
      to look: Vue/React templates near the field, `:items=` arrays in
      selects, `t()` / `$t()` i18n keys, `text:` / `label:` props,
      `computed` getters that translate enum → display text, formatters,
      `<option>` children.
    - Use the visible label in the `.md`. If you can't locate it, register
      a pending question (in `{lang}`: "What label appears in the UI for X?")
      and put a descriptive placeholder in `{lang}`, never the raw constant.
    - When in doubt: would a non-technical end user of the product
      understand this sentence WITHOUT opening the codebase? If no,
      rewrite.

    Tech guides (`.tech.md`) are where constants, enum values, column
    names, file paths and routes belong. That's their whole job — don't
    dilute them by spilling tech detail into the product flavor. Tech
    guides ALSO render their prose in `{lang}` (the user reading them
    is the dev of the same product), but they keep code identifiers
    untranslated.

4. **Isolated context per draft.** In Phase 4, each article gets its OWN focused
   sub-task. Even within a single topic, don't draft all its articles in one shot
   — quality collapses. Use separate tool calls / sub-agents when your platform
   supports it.

5. **Capability = Category, Article = Page.** Maximum 2 levels of hierarchy.
   This maps directly to Chatwoot (the target help-center). No grandchildren.

6. **Two flavors, same domain.** Each article has `.md` (product, zero jargon)
   and `.tech.md` (technical, with code refs). They never cross-link to each
   other; cross-links go to OTHER same-flavor guides.

7. **Pending questions, not invented answers.** When code doesn't reveal
   intent / UX rationale / external integration details, write a pending
   question. Phase 6 asks them, scoped to the current topic.

8. **Screenshot TODOs are structured.** When mentioning a concrete UI route,
   insert the admonition (see `references/screenshot-todos.md`) AND register
   in state. Both happen together, always.

9. **User approves transitions.** Never silently advance. Inside the topic loop,
   after drafting ask (rendered in `{lang}`): *"Drafts done for this topic. Move
   to code-first triage, or generate more first?"* And after a topic closes,
   return to the selector — never auto-start the next topic.

10. **State is sacred.** Persist after every phase, every batch, every save.
    If the conversation crashes, the user re-invokes the skill and you read
    state to continue exactly where you stopped.

11. **Commit per topic step.** Treat each Phase 4 batch, each Phase 5.5 triage,
    and each Phase 7 update as an atomic git checkpoint, and commit the whole
    topic when it closes. Commit AFTER every successful step BEFORE starting the
    next. Recovery from sub-agent corruption or environment failure depends on
    this discipline. Use a prefix in the commit message (e.g. `phase-4: draft
    <topic>`, `phase-5.5: auto-fix from code (<topic>)`, `topic: close <topic>`,
    `sync: cross-links`) so `git log --grep` and selective revert work.

12. **Post-edit verification — sub-agents never report success blindly.**
    Any sub-agent that writes to files (Phase 4, 5.5, 7, and Sync) MUST verify
    its own work before returning:

    - `wc -c <file>` — file must NOT be 0 bytes.
    - `grep -c "<sentinel>" <file>` — for triage/sync, the expected
      content must be present (or expected `[TODO:link=` count must be 0
      on resolved articles, or report remaining count).
    - Include `verification_passed: true|false` in the returned JSON.
    - If verification fails: set `files_modified: []`, add the failure
      to `errors[]`, and never claim success.

    Also: **anti-loop guard** — if the same tool call fails 2× with the
    same error message, the sub-agent ABORTS with `status: "aborted"`
    and the error. Do not retry silently — burns context for nothing.

13. **Privacy first — bounded sub-agent reading scope.** Never send
    secrets, credentials, or `.gitignore`d content into a sub-agent's
    context, even if the user's tool permissions would technically allow
    it. The orchestrator filters paths against the denylist BEFORE
    composing prompts. See `references/privacy.md` for the full rule:
    `.env*`, `secrets/`, `*.pem`/`*.key`, `.aws/`, `.ssh/`, anything in
    `.gitignore` or `.git/`, plus the heavy-noise dirs (`node_modules/`,
    `vendor/`, `.venv/`). The user gets a one-time warning in Phase 0
    that guidance text WILL appear in later LLM calls so they can
    self-redact before saving.

---

## Cost discipline

For each LLM call in Phase 2/4/5.5/7 and during Sync, mentally estimate cost
based on prompt size + expected output. Tell the user before expensive calls:

> *"I'm going to draft the 3 articles in this topic. Each call reads the topic's
> code anchors plus the style guide — typical usage ~$0.50 per article.
> Estimated cost: $1.50. OK?"* (render in `{lang}`)

In Phase 4 (the expensive one), ALWAYS offer one article at a time so the user
can evaluate quality before committing to the whole topic.

**Honest cost ranges** (observed across real runs — calibrate against your
own project, do not promise these to the user as fixed estimates):

- Phase 4 (draft per article): **$0.30 – $1.00 per article.** Varies 3× with
  how much code each topic touches.
- Phase 5.5 (code-first triage per article-pair): **$0.20 – $1.50** depending
  on questions × code-reading depth.
- Phase 6 (interview): mostly text, ~$0.05 per question; intra-topic dedup, when
  needed, is a single inline call.
- Phase 7 (topic update): **$0.30 – $0.80 per affected article.**
- Sync (cross-corpus): scales with corpus size; run it occasionally, not after
  every topic.

Because the work is per-topic, cost is **spread across sessions** rather than
front-loaded. Record actual cost per topic in `.livedocs/state.md` so the user
(and you) have empirical data for the next topic.

---

## Batch sizing — hard limits that prevent timeouts

Observed in real runs: exceeding these limits caused sub-agent timeouts
and corrupted state. Treat as ceilings, not targets.

| Operation | Limit per sub-agent call |
|---|---|
| Phase 4 draft | **1 article** per sub-agent |
| Phase 5.5 triage | **1 article-pair** (`.md` + `.tech.md`) per sub-agent |
| Phase 7 rewrite | **1 article** per sub-agent |
| Sync stitch | **up to 5 articles** per sub-agent (group by capability) |

Because every step is scoped to one topic, the old global-scale problems
(stitching 6 journeys at once, deduping 314 questions at once) no longer arise.
Intra-topic dedup is small enough to run inline. If a single topic is unusually
large (e.g. a capability with 7 articles), still split Phase 4 / 5.5 one
article at a time — never batch them to "save time".

---

## Failure modes — what to do

- **Graphify missing**: warn, continue without graph signal. Other scan
  sources (routes/i18n/models) still drive taxonomy.
- **Conversation context fills up**: tell the user, offer to compact the
  state file (drop completed phase details) and restart fresh.
- **User abandons mid-phase**: save partial state, exit gracefully. They
  resume by re-invoking the skill.
- **You wrote a wrong article**: don't silently fix. Tell the user, propose
  what to change, get OK, then patch.
- **You drift from the skill**: re-read this SKILL.md. Common drift =
  inventing content, skipping evidence, abandoning state tracking.

---

## Quick reference card

| User intent (any language equivalent) | What you do |
|---|---|
| "start" / "begin" / "iniciar" / "começar" | Phase 0 → ask for guidance text via editor |
| "continue" / "resume" / "continuar" | Read state; resume Init/Map or re-enter the topic loop |
| "document X" / "next topic" / "próximo tópico" | Topic loop: select/suggest a topic, run 4→5.5→6→7 |
| "sync docs" / "sincronizar a documentação" / "atualizar links" | Run Sync (`references/sync-flow.md`) |
| "what's next?" | Suggest the next topic, don't auto-start |
| "status" | Summarize state.md in 5 lines (Init/Map done? topics done vs pending) |
| "what's the cost so far?" | Sum the cost annotations from state.md |

Now load `references/phase-0-guidance.md` when the user is ready to begin.
Once Init/Map is approved, load `references/topic-loop.md` to drive the loop.
