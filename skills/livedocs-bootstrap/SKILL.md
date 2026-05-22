---
name: livedocs-bootstrap
description: |
  Bootstrap living documentation for a SaaS codebase via guided conversation. Use when
  the user wants to document an existing system from scratch (or fill gaps) — produces
  paired product + technical guides organized as Categories (capabilities) and Articles,
  with cross-links, pending questions, and screenshot TODOs. Drives the whole 7-phase
  flow without leaving the chat.
version: 1.3.0
author: Tagore + LiveDocs
---

# LiveDocs Bootstrap — Standalone Skill

You are about to bootstrap **living documentation** for a SaaS project. This skill
replaces the Python CLI: the entire 7-phase flow runs inside this conversation,
with you as the orchestrator and the user as the maintainer.

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

## The 7+1 phases

You will walk the user through these in order. **One phase at a time.** Don't
skip ahead. After each phase, save state and ask explicit consent to continue.

| # | Phase | What happens | LLM cost |
|---|---|---|---|
| 0 | Guidance | User dumps free-form context about the product | 0 |
| 1 | Scan | Run graphify + extract routes/i18n/models | 0 (graphify uses LLM separately) |
| 2 | Taxonomy | Propose capabilities + journeys from the scan | 1 call |
| 3 | Review | User edits/approves the taxonomy | 0–N (split is N calls) |
| 4 | Pass 1 | Draft each article in isolated context | N calls (1 per article) |
| 5 | Pass 2 | Cross-link articles, harmonize terms | N calls (lighter) |
| **5.5** | **Code-first triage** | **Re-answer questions from code, patch divergent articles** | **K calls (1 per capability)** |
| 6 | Refinement | Batch-ask the *surviving* questions to the user | 1-2 dedup calls + interview |
| 7 | Global update | Rewrite affected articles with answers | M calls (affected only) |

**Phase 5.5 is critical** — it dramatically reduces the human interview
burden by re-checking pending questions against code and patching articles
that were written without the answer. Without it, the user faces a flood
of trivially-answerable questions and the articles stay subtly wrong.

**Always offer to run phase 4 in batches** — by capability — so the user can
evaluate quality before spending the full cost.

---

## Phase-by-phase instructions

Each phase has a detailed reference. Load it when you enter that phase:

- **Phase 0** — `references/phase-0-guidance.md`
- **Phase 1** — `references/phase-1-scan.md`
- **Phase 2** — `references/phase-2-taxonomy.md`
- **Phase 3** — `references/phase-3-review.md`
- **Phase 4** — `references/phase-4-pass1-drafts.md`
- **Phase 5** — `references/phase-5-pass2-stitching.md`
- **Phase 5.5** — `references/phase-5.5-triage.md`
- **Phase 6** — `references/phase-6-refinement.md`
- **Phase 7** — `references/phase-7-global-update.md`

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
   equivalent). If it has content, parse the "Current phase" line and the
   `Lang:` field. Resume from there — announce, rendered in `{lang}`:
   *"Resuming bootstrap from phase N. Continue?"*

2. **If no state yet, greet and confirm intent.** Use the language you
   detect in the codebase (or English as default) for this first message
   — Phase 0 will let the user override. Brief message, equivalent to:

   > *"Hi! I'll guide the bootstrap of this project's documentation. It's
   > 7 phases, takes ~2-4h of work plus LLM call time. Can I start
   > with phase 0?"*

3. **On user OK, load `references/phase-0-guidance.md`** and follow it.
   Phase 0 is where the run language is locked in (`Lang:` in state).

4. **At every save**, write to `.livedocs/state.md`. **At every transition**,
   tell the user what changed (in `{lang}`) and ask consent for next phase.

---

## Core principles (read once, follow always)

1. **DELEGATE the grunt work to sub-agents.** This is critical. Your platform
   likely supports spawning child agents (Task tool, delegate_task, etc.) — USE
   THEM for: graphify execution monitoring, file extraction (routes/i18n/models
   scans), each individual article draft in phase 4, each stitching pass in 5,
   each global update in 7. Keep YOUR main context for orchestration,
   decision-making, and conversation with the user.

   The orchestrator (you) should be the ONE place that knows the full state.
   Sub-agents return summaries — JSON or short text — not full markdown blobs.
   If you let phase 4 drafts pollute your context, by article 10 you'll lose
   track of what's happening.

   Rule of thumb: anything that involves reading >5 code files or producing
   >2KB of output → sub-agent. Anything conversational with the user or
   small (under 500 chars in/out) → handle directly.

3. **Evidence-first.** Every claim in a guide MUST be backed by either:
   (a) `file:line` code reference, (b) user-confirmed answer, or
   (c) inheritance from another guide. No invention. Mark 🟡 hypotheses
   in tech guides; never in product guides.

3b. **UI language in product guides = the language the user actually sees.**
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
   Always (rendered in `{lang}` from state.md):
   *"Batch done. Move to Pass 2 or generate more articles first?"*

10. **State is sacred.** Persist after every phase, every batch, every save.
    If the conversation crashes, the user re-invokes the skill and you read
    state to continue exactly where you stopped.

11. **Commit per batch.** Treat each Phase 4 batch (per capability), each
    Phase 5 capability, and each Phase 5.5 capability as an atomic git
    checkpoint. Commit AFTER every successful batch BEFORE starting the
    next. Recovery from sub-agent corruption or environment failure
    depends on this discipline. Use a prefix in the commit message
    (e.g. `phase-4: draft <capability>`, `phase-5.5: auto-fix from code
    (<capability>)`) so `git log --grep` and selective revert work.

12. **Post-edit verification — sub-agents never report success blindly.**
    Any sub-agent that writes to files (Phases 4, 5, 5.5, 7) MUST verify
    its own work before returning:

    - `wc -c <file>` — file must NOT be 0 bytes.
    - `grep -c "<sentinel>" <file>` — for stitching/triage, the expected
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

For each LLM call in phases 2/4/5/5.5/7, mentally estimate cost based on
prompt size + expected output. Tell the user before expensive calls:

> *"I'm going to run Pass 2 on 4 articles. Each call reads the article
> content plus the index of the others — typical usage ~$0.05 per article.
> Estimated cost: $0.20. OK?"* (render in `{lang}`)

In phase 4 (the expensive one), ALWAYS offer batch-by-capability instead of
all-at-once.

**Honest cost ranges** (observed across real runs — calibrate against your
own project, do not promise these to the user as fixed estimates):

- Phase 4 (draft per article): **$0.30 – $1.00 per article.** Varies 3× with
  how much code each capability touches. Big-capability projects can hit $1+.
- Phase 5 (stitching per capability): **$0.50 – $3.00 per capability.**
- Phase 5.5 (code-first triage per capability): **$0.20 – $1.50 per capability**
  depending on questions × code-reading depth.
- Phase 6 (dedup + interview): **dedup ~$0.50 – $2 per pass** (two-pass when
  >80 questions); interview itself is mostly text, ~$0.05 per Q.
- Phase 7 (global update): **$0.30 – $0.80 per affected article.**

Record actual cost per batch in `.livedocs/state.md` so the user (and you)
have empirical data for the next execution.

---

## Batch sizing — hard limits that prevent timeouts

Observed in real runs: exceeding these limits caused sub-agent timeouts
and corrupted state. Treat as ceilings, not targets.

| Operation | Limit per sub-agent call |
|---|---|
| Phase 4 draft | **1 article** per sub-agent |
| Phase 5 stitch | **up to 5 articles** per sub-agent (group by capability) |
| Phase 5.5 triage | **1 capability** per sub-agent |
| Phase 6 dedup (intra-batch) | **up to 80 questions** per sub-agent |
| Phase 6 dedup (cross-batch) | 1 sub-agent reconciling canonicals across batches |
| Phase 7 rewrite | **1 article** per sub-agent |

If a unit exceeds the limit (e.g. a capability with 7 articles for Phase 5),
split into thematic sub-batches BEFORE calling the sub-agent. Better to
make 2 calls than to time out and re-run.

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
| "continue" / "resume" / "continuar" | Read state, resume from current phase |
| "what's the next phase?" | Tell user, don't auto-advance |
| "go back to phase X" | Confirm, mark X as current in state, re-execute |
| "status" | Summarize state.md in 5 lines |
| "what's the cost so far?" | Sum the cost annotations from state.md |

Now load `references/phase-0-guidance.md` when the user is ready to begin.
