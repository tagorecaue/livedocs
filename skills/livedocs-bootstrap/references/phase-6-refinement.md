# Phase 6 — Coverage-aware refinement interview (per topic)

## Goal

Get human answers for the questions that survived **Phase 5.5 code-first
triage** — only questions that genuinely require product intent, operational
reality, or tribal knowledge — for **the current topic only**.

> Scope: ONE topic. This runs inside the topic loop (`references/topic-loop.md`).
> The questions here belong to the topic being documented, nothing else. There
> is no project-wide dedup, no two-pass reconciliation. A topic has a handful of
> surviving questions, not hundreds.

> Prerequisite: Phase 5.5 ran for this topic. Questions reaching Phase 6 have
> `status: needs_human`. Questions with `status: answered_by_code` are already
> resolved with file:line evidence and never reach the user.

## Why coverage-aware

The user often finds it easier to give one big answer than to answer many small
questions — and a single rich answer frequently resolves several pending
questions at once. The risk: if the agent marks questions "answered" by loose
association, a **nuance gets lost** and an important question is never asked.

The antidote: **coverage is never binary.** After every answer, each still-open
question is re-checked and classified into THREE buckets — fully, partially, or
not covered — with evidence. Partial coverage is always followed up; high-stakes
questions always get explicit confirmation. This is the mechanism that lets the
user "dump" a big answer without silently dropping anything.

## Structure of the interview

Organized in **thematic blocks A–F**, not by article. Same theme = same mental
mode for the user, lower fatigue.

| Block | Theme | Example questions |
|---|---|---|
| **A** | **Product meaning / glossary** | "What does status X mean in business terms?" |
| **B** | **Transitions and triggers** | "Who fires A → B? Cron? Webhook? Manual?" |
| **C** | **Invariants and constraints** | "Can two records of type X be active at once?" |
| **D** | **User experience and support** | "Top 3 support questions about screen S?" |
| **E** | **Code-suggested edges** | "Code suggests X but doesn't confirm — is rollback transactional?" |
| **F** | **Direction of the guide (meta)** | "Right depth? Anything obvious I missed?" |

Block F is **always present** as the closing section.

---

## What to do

### Step 1 — Load this topic's questions

Read the in-progress topic's pending questions from `.livedocs/state.md`.
Filter `status == "needs_human"`. If Phase 5.5 was skipped (it shouldn't be),
include `status == "open"` too — never silently drop open questions.

If there are none, tell the user Phase 5.5 resolved everything from code for
this topic and skip to Phase 7.

### Step 2 — Classify into blocks A–F

For a topic's handful of questions, classify inline (no sub-agent needed):
assign each question a block letter A–F. Save the block on each question in
state. If a question has no clear block, default to **E**.

### Step 3 — Open each block with a free-form question FIRST

This is the heart of the coverage-aware design. Before asking the block's
specific questions one by one, **invite a free-form dump**:

```
Block B — Transitions & triggers (recurring-billing)

I have 4 questions here, but answer however is easiest — you can describe
the whole billing lifecycle in one go and I'll map your answer to the
questions, or take them one at a time. Your call.

(If you'd rather just see the questions: say "list".)
```

The free-form answer is the input to the coverage pass (Step 4). If the user
prefers, they answer questions individually — then the coverage pass still runs
after each individual answer, because one answer can resolve siblings too.

### Step 4 — Coverage pass after EVERY answer

After each user answer (free-form or targeted), run ONE coverage check over all
**still-open questions of this topic**. For each open question, classify into
exactly one of THREE buckets — never two:

- **`fully-covered`** — the answer resolves the question completely.
- **`partially-covered`** — the answer touches it but leaves a gap.
- **`untouched`** — the answer doesn't address it.

**Evidence requirement (non-negotiable):** for `fully` or `partially`, you MUST
extract the **specific span** of the user's answer that covers it AND write the
**explicit inferred answer**. If you can't quote a span, it is NOT covered —
classify as `untouched`. No "seems related".

**Conservative asymmetry:** when torn between `fully` and `partially`, choose
`partially`. A silent gap (false "answered") is worse than re-asking (mild
annoyance).

### Step 5 — Act on each bucket (high/low confidence)

Apply the confidence rule. Confidence is YOUR assessment of how certain the
inferred answer is, given the span.

- **`fully-covered` + high confidence** → confirm in a BATCH, showing the
  inferred answer per question so the user can catch a misread:

  ```
  From your answer, I've recorded:
    • Q3 (who triggers retries): "The dunning cron retries 3× over 5 days."
    • Q7 (manual vs auto): "Charges are automatic; only refunds are manual."
  Correct anything, or say "ok" to confirm both.
  ```

- **`fully-covered` + low confidence** → ALWAYS ask explicitly, even though it
  looks covered. Show your inference and ask for confirmation as a real question,
  not a batch line.

- **`partially-covered`** → NEVER skip. Re-ask, reframed to show what you have
  and what's missing:

  ```
  Q5 — I got that charges retry 3×, but not what happens after the 3rd
  failure. Does the contract suspend, or does it stay active with a flag?
  ```

- **`untouched`** → ask normally when its block comes up.

### Step 6 — High-stakes override

Some questions demand explicit confirmation **even when coverage looks full and
confidence is high**. Never fold these into the silent batch-confirm. They are:

- **Invariants / constraints** (Block C) — "X can never happen".
- **Integration failure modes** (Block E) — webhook retries, timeouts, partner
  error behavior.
- **Product intent** that changes the narrative — "why it was designed this
  way".

For these, always surface the inferred answer as a direct question and get a
clear yes/correction. Getting an invariant subtly wrong propagates into the
tech guide as a false "the system prevents…".

### Step 7 — Record with an audit trail

When a question is closed via propagation (covered by another answer rather than
asked directly), record on the question:

```
status: answered
answered_via: propagation-from-Q3
inferred_answer: "<the explicit answer you inferred>"
user_confirmed: true        # always true — batch-confirm or explicit ask
covering_span: "<the quoted span from the user's answer>"
```

Directly-asked questions record `answered_via: direct`. Phase 7 uses
`inferred_answer` / the direct answer as the source of truth, and the audit
trail lets a later reader see which answers were inferred vs stated.

Verbatim preservation: store the user's actual answer text as written,
including language (see `language-handling.md`). The `inferred_answer` is your
distillation; the raw answer is kept too.

### Step 8 — Interview file (optional, for a question-heavy topic)

A single topic rarely needs file export. If a topic is unusually large (say
>15 surviving questions), you may export a per-block file to
`.livedocs/interview/<topic>/block-X.md` using the template below; otherwise the
inline chat interview is better — the coverage pass is most natural in chat.

````markdown
# Interview — {topic} — Block {LETTER} — {BLOCK NAME in {lang}}

**Date:** YYYY-MM-DD
**Interviewee:** {user name from state}

## How to answer

Answer below each question in the **{Answer:}** field, or write one big
answer at the top — I'll map it to the questions. Skip with `/skip`,
pause with `/pause`. Where I guessed, I marked 🟡.

---

## Free-form (answer everything here if you prefer)

**{Answer:}**


---

### {Q#} — origin: {topic/article} — confidence: {high|low}

{Question text in {lang}}

🟡 **My provisional answer:** {provisional_answer in {lang}}

**{Answer:}**


---
````

The literal word `Answer:` is the **answer marker** the agent greps for.
Translate it for the user but keep it consistent within a run (record it in
state under `answer_marker:`).

### Step 9 — Always include Block F

Appended after A–E (render in `{lang}`):

````markdown
# Block F — Direction of the guide (meta)

**F1. Right depth?** Too shallow, too deep, or right for this topic?

**{Answer:}**

---

**F2. Anything obvious I missed?** Something a maintainer would consider
essential that the drafts don't touch?

**{Answer:}**

---

**F3. Anything I should have asked but didn't?** Open mic.

**{Answer:}**
````

(Note: "what topic next?" is NOT asked here — the topic loop's selector owns the
next-topic suggestion. Block F is about THIS guide's quality.)

### Step 10 — Pause / resume

Slash commands stay as-is regardless of `{lang}` — parser tokens.

- `/skip` → leave question open, continue.
- `/list` → show the block's specific questions instead of free-form.
- `/quit` or `/pause` → save state, exit (in `{lang}`): *"Pausing. You answered
  N of M for this topic. Re-invoke to resume from here."*

### Step 11 — End of interview

Save state, set the topic status to `interviewed`, summarize (in `{lang}`):

```
✓ Interview done for recurring-billing — 6/7 answered, 1 skipped.
  A: 2/2  B: 2/2  C: 1/1  D: 1/1  E: 0/1 (skipped)  F: meta captured
  3 answered directly, 3 by propagation (all confirmed).

Next: rewrite the affected articles (Phase 7) with these answers. Proceed?
```

---

## Pitfalls

- **Treating coverage as binary.** The whole point is three buckets. A question
  that's "sort of covered" is `partially` → always followed up.
- **Marking covered without quoting a span.** If you can't quote the user's
  words that answer it, it's `untouched`. No vibes.
- **Folding an invariant or integration-failure question into silent
  batch-confirm.** High-stakes questions always get explicit confirmation
  (Step 6), even when coverage looks complete.
- **Carrying questions across topics.** Phase 6 is scoped to the current topic.
  Another topic's questions are not in play here.
- **Re-introducing global dedup.** There is none. A topic's question set is
  small; if two are near-duplicates, merge inline and move on.
- **User answers vague ("depends" / "I don't know").** That's a real answer —
  save it; Phase 7 writes it as a documented uncertainty.
- **User writes a 5-paragraph essay.** Accept all, store verbatim, let the
  coverage pass map it to questions. This is the intended easy path.
