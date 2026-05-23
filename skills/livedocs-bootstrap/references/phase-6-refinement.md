# Phase 6 — Refinement Interview

## Goal
Get human answers for the questions that survived **Phase 5.5 code-first
triage** — i.e. only questions that genuinely require product intent,
operational reality, or tribal knowledge.

> Prerequisite: Phase 5.5 must have run. Questions reaching Phase 6 have
> `status: needs_human`. Questions with `status: answered_by_code` are
> already resolved with file:line evidence and never reach the user.

## Structure of the interview

The interview is organized in **thematic blocks A–F**, not by capability.
Same theme = same mental mode for the user, lower fatigue, faster pace.

| Block | Theme | Example questions |
|---|---|---|
| **A** | **Product meaning / glossary** | "What does status X mean in business terms?" "Are 'commission' and 'payout' interchangeable in your vocabulary?" |
| **B** | **Transitions and triggers** | "Who fires A → B? Cron? Webhook? Manual?" "What event causes the contract to leave `pending`?" |
| **C** | **Invariants and constraints** | "Can two records of type X exist active at the same time?" "Is there a hard limit on the renegotiation chain?" |
| **D** | **User experience and support** | "Top 3 most common support questions about screen S?" "Does the operator understand this copy?" |
| **E** | **Code-suggested edges** | "Code suggests X but doesn't confirm — is rollback transactional here?" "Race condition between two writers — intentional?" |
| **F** | **Direction of the guide (meta)** | "Right depth?" "Anything obvious I missed?" "What guide next?" |

Block F is **always present**, regardless of content, as the closing
section. It captures user feedback about the guide itself.

---

## What to do

### Step 1 — Load questions

Read `.livedocs/state.md`. Check whether Phase 5.5 ran:
- **Phase 5.5 ran** (state shows `[x] 5.5 — Code-first triage`): filter
  `status == "needs_human"`. If none, skip Phase 6 and tell the user that
  Phase 5.5 resolved everything from code.
- **Phase 5.5 was skipped**: filter `status in ("needs_human", "open")`.
  All unresolved questions go to the interview regardless of status.

Never silently drop `status == "open"` questions when 5.5 was not run.

### Step 2 — Dedup (two-pass when N is large)

**If N ≤ 80 questions:** single dedup call.

**If N > 80:** two-pass thematic dedup.

#### Two-pass dedup algorithm

> When you have hundreds of pending questions across many capabilities,
> a single dedup call times out and quality degrades. Split first by
> theme (intra-batch), then reconcile across batches (cross-batch).

**Pass 1 — intra-batch (parallel, ≤80 questions per sub-agent):**

Split questions into thematic batches by **origin capability** (or by
emerging topic when capabilities don't cluster cleanly). Each batch
goes to one sub-agent.

Prompt template per sub-agent:

> Below are N pending questions from a single thematic group during
> documentation generation. Group equivalent or near-equivalent questions
> into clusters. For each cluster, pick a canonical question (rewrite
> if a better phrasing helps) and list the IDs being merged.
>
> Output JSON:
> ```json
> {
>   "clusters": [
>     {
>       "canonical_id": "Q3",
>       "canonical_question": "...",
>       "canonical_origins": ["billing/invoices", "project-management/create-project"],
>       "canonical_confidence": "low|high",
>       "canonical_provisional_answer": "...",
>       "merged_ids": ["Q7", "Q11"]
>     }
>   ]
> }
> ```
>
> **Critical rule:** `canonical_id` MUST NOT appear inside its own
> `merged_ids`. Singletons (no duplicates) have `merged_ids: []`.

Example correct output (mix of singleton and real cluster):

```json
{
  "clusters": [
    // Singleton — Q5 has no duplicates
    {
      "canonical_id": "Q5",
      "canonical_question": "...",
      "merged_ids": []
    },
    // Real cluster — Q3 absorbs Q7 and Q11; Q3 does NOT appear in merged_ids
    {
      "canonical_id": "Q3",
      "canonical_question": "...",
      "merged_ids": ["Q7", "Q11"]
    }
  ]
}
```

Example INCORRECT output (do not produce):

```json
{
  "canonical_id": "Q3",
  "merged_ids": ["Q3", "Q7", "Q11"]  // ❌ canonical can't merge into itself
}
```

**Pass 2 — cross-batch (single sub-agent):**

Take all canonicals from Pass 1 (drop merged IDs) and feed to one
sub-agent that finds cross-batch duplicates. Same JSON shape.

**Reconciliation:**

The orchestrator (you) combines Pass 1 and Pass 2 results via
`execute_code` (a small Python script). Algorithm:

1. Start with Pass 1 clusters.
2. For each Pass 2 cluster that merges canonicals from different
   Pass 1 batches: absorb those canonicals into the new canonical.
3. **Union `canonical_origins`**: for every absorbed canonical, union its
   `canonical_origins` list into the surviving canonical's list. Deduplicate.
   This ensures Phase 7 routes the answer to ALL origin guides, not just
   the canonical's original guide.
4. Sanitize: remove any `canonical_id` that appears inside its own
   `merged_ids` (defensive guard against the bug above).
5. Validate invariant: each original Q appears in exactly one cluster.
6. Sort clusters by `len(merged_ids) DESC`, then `canonical_id ASC`.

Save the result to `.livedocs/cache/questions/clusters-final.json`.

### Step 3 — Classify into blocks A–F

After dedup, classify each canonical cluster into one of the six blocks.
Either:
- single LLM call with all canonicals, returning `{canonical_id: "A"|...|"F"}`, OR
- per-cluster classification inline if N is small (<30).

Save classification back into state and into `clusters-final.json` (add
`"block": "A"|...|"F"` per cluster).

### Step 4 — Export interview files (recommended for N > 50)

Write one markdown file per block to `.livedocs/interview/`:

```
.livedocs/interview/
├── block-a-product-meaning.md
├── block-b-transitions-triggers.md
├── block-c-invariants.md
├── block-d-ux-support.md
├── block-e-code-edges.md
└── block-f-guide-direction.md
```

Each file has the same skeleton (see template below). User can answer
inline in any editor and signal "done with block X". Agent reads the
file back to ingest answers.

For N ≤ 50, inline chat interview is fine; skip the file export.

#### Interview file template (per block)

> The block file is rendered in `{lang}`. The skeleton below is shown in
> English for illustration — translate every prose line, including the
> "Resposta:" / "Answer:" marker word, while keeping the structure intact.

````markdown
# Interview — Block {LETTER} — {BLOCK NAME in {lang}}

**Date:** YYYY-MM-DD
**Interviewee:** {user name from state}
**Interviewer:** livedocs-bootstrap agent

## How to answer

Answer below each question in the **{Answer:}** field. You can answer
in prose, bullets, transcribed audio — whatever is practical. Skip
with `/skip`, pause with `/pause`. Where I guessed, I marked 🟡 with
what I assumed — just confirm or correct.

---

## {Block name in {lang}}

### {Q#} — origin: {capability/slug} — confidence: {high|low}

{Question text in {lang}}

🟡 **My provisional answer:** {provisional_answer in {lang}}

**{Answer:}**



---

### {Q#} — ...
````

The literal word `Answer:` above is the **answer marker** the agent
greps for when reading the file back. Translate it for the user but
keep it consistent within a run (e.g. `Resposta:` in pt-BR — always the
same word, never mixed). Record the chosen marker in state under
`answer_marker:` so the import step in Step 7 knows what to grep.

### Step 5 — Always include Block F

Block F is a fixed template appended after content blocks A–E
(render in `{lang}`):

````markdown
# Block F — Direction of the guide (meta)

These are about the guide, not about the system.

**F1. Right depth?** Are the drafts too shallow, too deep, or right for
this domain? Should we split into product + tech more aggressively?

**{Answer:}**

---

**F2. Anything obvious I missed?** Is there something a maintainer of
this product would consider essential that none of the drafts touch?

**{Answer:}**

---

**F3. Next guide?** Now that this bootstrap is done, what should be the
first guide we revisit or expand in maintenance mode?

**{Answer:}**

---

**F4. Anything I should have asked but didn't?** Open mic.

**{Answer:}**
````

### Step 6 — Conduct the interview

**Inline mode (chat, N ≤ 50):**

For each canonical, in block order (A → F), render the turn in `{lang}`.
The skeleton below is shown in English for illustration:

```
Question 5/23 — Block B (Transitions) — origin: project-management/create-project

The agent asks:
  "When you create a project and it enters the 'Negotiation' Kanban
   stage, does that trigger any automatic notification?"

🟡 Provisional answer (confidence: low):
  "No automatic notification — members see it when opening the Kanban."

Other questions this one also answers:
  - Q12 (billing/invoice-issuance): "Do stage changes trigger alerts?"

Your answer (or /skip / /quit):
>
```

**File mode (N > 50):**

Tell the user the files were created. Wait for them to say "done with
block A" (or similar). Read the file, parse each answer marker section
(`Resposta:` / `Answer:` / whatever is recorded in state under
`answer_marker:`), save to state. Repeat for each block.

### Step 7 — When user answers

- Save to canonical: `status="answered"`, `answer="..."` (verbatim text
  preserved, including language — see `language-handling.md`).
- Propagate to merged questions: `status="answered"`, same answer.
- **Re-evaluate other open questions**: an answer often resolves
  others. After each answer, scan remaining canonicals. If any is
  clearly now resolved by the new answer, ask (in `{lang}`, semantic
  equivalent of):
  > "Your answer also seems to resolve Q12 ('Does stage change emit an
  > alert?'). OK to mark Q12 as answered with the same answer?"

### Step 8 — Pause / resume

Slash commands stay as-is regardless of `{lang}` — they're parser tokens.
The agent's surrounding chat lines render in `{lang}`.

- `/skip` → leave question open, continue.
- `/quit` or `/pause` → save state, exit gracefully (message in `{lang}`):
  > "Pausing refinement. You answered 8/23 questions. To continue,
  > re-invoke the skill — I'll resume from here."
- `/abort` → save state with a `paused_at` timestamp, mark
  `interview_status: paused`. On resume, skip already-answered questions.

### Step 9 — End of interview

Save state, summarize (render in `{lang}`; English skeleton shown):

```
✓ Refinement complete — 18/23 answered, 5 skipped.

  By block:
    A (meaning):    4/4
    B (transitions): 5/6
    C (invariants): 3/4
    D (UX/support): 2/4
    E (edges):      2/3
    F (direction):  2/2

Next phase: Global Update — affected articles will be reopened and the
answers incorporated. Estimate: ~M affected articles, cost ~$X.

Proceed?
```

---

## Pitfalls

- **User answers vague (equivalent of "I don't know" / "depends")**:
  that's a real answer. Save it; Phase 7 will write it as a documented
  uncertainty in the guide.
- **User answers a 5-paragraph essay**: accept all. Save full text. Phase
  7 will distill what's relevant per affected article.
- **Question has no clear origin guide**: dedup might lose it. Fallback:
  treat as standalone and use during Phase 7's global update against
  all guides.
- **Sub-agent reformulates questions excessively**: the dedup prompt has
  a "rewrite if a better phrasing helps" clause but isn't an
  instruction to rewrite all. Keep original where it's already clear.
- **User pauses and resumes much later**: pending questions older than
  ~2 weeks may be stale (code may have changed). When resuming, warn
  the user and offer to re-run Phase 5.5 to see if any are now
  answer-able from current code.
- **Block classification drifts**: if you get questions with no clear
  block fit, default to **E (code-suggested edges)** — almost any
  ambiguity-from-code question fits there.
- **Cross-batch dedup forgets to merge**: cross-batch sub-agent receives
  only canonicals (no merged IDs from Pass 1). When it creates a new
  cluster spanning Pass 1 batches, the reconciliation step (Step 2,
  algorithm point 2) must absorb both Pass 1 canonicals into the new one.
