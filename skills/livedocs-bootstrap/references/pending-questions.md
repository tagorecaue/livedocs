# Pending questions

## Why
Pending questions are how the agent acknowledges what it doesn't know
without inventing answers. They get batched and asked to the user in
Phase 6 — but **only after Phase 5.5 (code-first triage) filters out
the ones the agent could have answered by reading the code harder.**

## Guiding principle

> **A pending question must be about INTENT or EXPERIENCE,
> not about EXISTENCE or VALUE.**
>
> Existence and value live in the code — go read it.
> Intent ("why was this designed this way?") and experience
> ("what support questions does the team actually receive?") only live
> in the user's head. Those are the questions worth asking.

If you find yourself about to ask "what is the value of X?" or
"does Y exist?", stop and look at the code.

## What NOT to register 🚫

These are auto-answerable. Registering them wastes the user's time
and Phase 5.5 will catch and remove them anyway — better to never
write them.

| Bad question pattern | Where the answer actually lives |
|---|---|
| "What's the label for enum value X?" | Vue/React `<template>`, `:items=` arrays, `t()` / `$t()` calls, computed `XxxLabel`, formatters, `<option>` children |
| "What are the valid values of structural enum X?" | SQL migration that defined it; `CREATE TYPE` |
| "Where is the cron that does Y scheduled?" | `src/cron/*`, scheduler config files, `CLAUDE.md` of the integration |
| "Does ADR-NNNN exist?" | `grep -r "ADR-NNNN"` or list `docs/adr/` |
| "Is column X nullable / unique?" | Migration file or `\d table` equivalent |
| "Does function/constant Z exist?" | `grep`, code search |
| "What's the shape of jsonb column J?" | TypeScript interface, Zod schema, fixture data |
| "Which file contains hook useX?" | Project file index |
| "Is this column audited?" | Schema definition |
| "What endpoint does button Y hit?" | The button's click handler |
| "What's the exact text of toast Z?" | i18n file or inline string |

The unifying property: **the answer is a fact present in the repository.**
Reading the code with a clear question is faster than the round-trip to
the human.

> Note for the agent: if you genuinely tried and couldn't find the
> answer (the file is huge, the indirection is deep), that's still not
> grounds to register the question — it's grounds to look harder or
> ask another sub-agent to grep for you. The pending question backlog
> is not a "todo: read code later" list.

## What TO register ✅

These genuinely require the human. Register confidently.

| Good question pattern | Why only the human knows |
|---|---|
| "Why was the system designed to do A instead of B?" | Intent — product decision |
| "Which path through this flow is more common in practice — X or Y?" | Operational reality |
| "When operators ask support about screen S, what are the top 3 most common questions?" | Tribal support knowledge |
| "Is feature F still used, or is it dead code that nobody removed?" | Roadmap / usage knowledge |
| "Two parallel cron jobs touch the same table — is the lack of locking intentional or accidental?" | Risk tolerance / product call |
| "External API X returns code 429 — what's the desired UX?" | Product decision on failure modes |
| "When entity A is transferred to a new owner, what should happen to messages already scheduled for the old owner?" | Cross-cutting flow intent |
| "The draft says X, but the code shows Y at file:line. Which is correct?" | Reconciling drift between narrative and reality |
| "Top complaints about screen S?" | Support history |
| "Is the race condition between concurrent writers OK, or do we want a UI lock?" | Risk acceptance |
| "Field F exists in DB but isn't on the UI — legacy, future, or wrong?" | Provenance / roadmap |

The unifying property: **the answer requires product intent,
operational reality, or the human's history with the system.**

## Anatomy of a pending question

```
Q3 — origin: gestao-projetos/criar-projeto — confidence: low — category: B
  Question: When entity A moves to stage 'Negotiation', does it trigger any
            automatic notification to team members?
  Provisional answer: No automatic notification — members see it on opening the board.
  Status: open
  Merged into: -
  Answer: -
```

Fields:
- **id** — sequential `Q1`, `Q2`, … unique across the bootstrap
- **origin** — guide slug that triggered the question (or list of guides)
- **confidence** — `low` | `high`. Reflects how sure the agent is about the
  provisional answer. `high` = agent is 80%+ confident; `low` = anyone's guess.
- **category** — `A`-`F` (assigned during Phase 6 grouping; see
  `phase-6-refinement.md`). Optional in Phase 4, mandatory by Phase 6.
- **question** — clear, single-sentence ask
- **provisional_answer** — agent's best guess, used in the draft until resolved
- **status** — `open` | `answered` | `merged` | `dropped` | `answered_by_code` | `resolved`
- **merged_into** — set when dedup determines this is equivalent to another Q
- **answer** — user's response, set during Phase 6 (or sub-agent during 5.5)

`status: answered_by_code` is set by Phase 5.5 when a sub-agent finds the
answer in the code with literal evidence (file:line + snippet). Those
never reach the human.

## Where they're stored

Inside `.livedocs/state.md`, in the "Pending questions" section. Format:

```markdown
## Pending questions (open: 7, answered: 0, merged: 0, answered_by_code: 0)

- **Q1** [gestao-projetos/criar-projeto] [conf: high] How does X interact with Y?
  - Provisional: "X always calls Y first".
- **Q2** [cobranca/conciliacao] [conf: low] When bank ack returns 404, what does the system do?
  - Provisional: "Retries 3 times then alerts admin".
- **Q3** [merged into Q1] (was: ...)
```

## Rules for the agent

1. **Apply the heuristic above BEFORE registering.** If the question
   matches a 🚫 pattern, do not register it. Go find the answer in
   the code and put it in the draft.

2. **Don't invent answers.** When the answer truly requires the human
   (✅ patterns), the provisional answer in the draft is a labeled
   guess (🟡 in tech guides), not a fabrication.

3. **One question per atomic ask.** Don't bundle "What about X, and
   also Y, and Z?". Split into separate questions.

4. **Provisional answers go in the draft** with 🟡 markers (tech guide
   only). When the question is answered, the 🟡 marker is removed
   and the actual answer replaces the provisional content.

5. **Origin matters.** Multiple guides can hit the same question. Origin
   is a list. After dedup in Phase 6, merged questions inherit the
   canonical's origins for tracking.

6. **Confidence guides UX.** During Phase 6 interview, `confidence:
   high` questions get prefaced with "I'm fairly sure of this — confirm?"
   and `confidence: low` with "Couldn't infer from code:".

7. **Stay aware of Phase 5.5.** Sub-agents in 5.5 will filter your
   questions. If you systematically generate 🚫-pattern questions, the
   filter ratio will be high — that's a signal that Phase 4 sub-agents
   are skipping code reading. Treat it as a calibration issue, not as
   normal.
