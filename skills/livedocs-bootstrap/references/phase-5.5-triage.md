# Phase 5.5 — Code-first triage + article audit

## Goal
Reduce the pending-question backlog by **resolving from code** every
question that doesn't truly need a human, AND simultaneously **patch
the article** that was written without that information.

> Causal insight (don't lose this):
>
> **If the agent ASKED a question instead of READING the code, the
> agent wrote that article WITHOUT that information.** So the
> provisional answer in the draft today may be wrong, vague, or
> missing entirely. The pending question is two symptoms of one gap.
>
> Removing the question without fixing the article leaves the gap
> silent. This phase fixes both ends.

This phase runs **between Phase 5 (stitching) and Phase 6 (interview)**,
**not as a substitute for either**.

---

## Prerequisites (non-negotiable)

This phase has sub-agents writing into existing article files. Without
the safeguards below, a faulty sub-agent can zero a file and report
success.

- **Commit-per-capability discipline** (Core principle #11). One commit
  per capability after this phase processes it. Allows selective revert.
- **Post-edit verification** (Core principle #12). Every write must be
  followed by `wc -c` > 0 + sentinel grep + diff readback. Return
  `verification_passed: true|false` in the sub-agent JSON.
- **Anti-loop guard.** If the same tool fails 2× with the same error,
  abort the sub-agent with `status: "aborted"`.

If any of those are not in place, **do not run this phase**. Tell the
user and proceed to Phase 6 with the unfiltered backlog instead.

---

## What to do

### Step 1 — Group questions by capability

Read pending questions from state. Group by origin capability (use
first segment of `origin` slug, e.g. `gestao-projetos/criar-projeto`
→ capability `gestao-projetos`).

### Step 2 — Spawn one sub-agent per capability

In parallel (respecting `delegate_task` concurrency limits), spawn one
sub-agent per capability with the prompt below. Each sub-agent owns its
capability's questions AND its capability's article files.

#### Sub-agent prompt template

````
# Phase 5.5 — Code-first triage + article audit
# Capability: {capability_slug}

## Your job

For each pending question listed below, you must:

1. Try to answer it from the code with LITERAL EVIDENCE.
2. If you can answer it: check whether the corresponding article(s)
   already reflect that answer. Fix the article if needed.
3. If you cannot: leave the question for the human interview (Phase 6).

## Hard rules

- Literal evidence means `file:path/to/file.ext` PLUS a snippet of 5–10
  lines from that file quoted in your response. Without the snippet,
  the answer is NOT considered evidenced — mark as needs_human.
- "Probably in X" / "maybe Y" / "likely Z" → automatically needs_human.
  Inference is not evidence.
- Do not invent function names, file paths, or schema columns.
  Verify by reading.
- When the same fact appears in both `.md` and `.tech.md`, patch BOTH
  (cross-flavor sync). Report `cross_flavor_synced: true`.
- Direct text patch only when the change is a LITERAL string substitution
  (label of enum, name of column, value of constant). For anything
  conceptual (rewrite a sentence, add a paragraph, change a described
  flow), produce a `proposed_diff` and do NOT apply it.
- After every file write: run `wc -c <file>` (must be > 0) and
  `grep -c "<sentinel>" <file>` to verify content survived. Return
  `verification_passed: true|false`.

## Inputs

- Pending questions: {list of Q objects from state}
- Article files (read AND write):
  - docs/capacidades/{capability_slug}/*.md
  - docs/capacidades/{capability_slug}/*.tech.md
- Codebase: read-only access via grep/read tools.

## Process for each question

1. Read the question, its origin, its provisional answer.
2. Generate a search plan: which files would resolve this?
3. Read those files (up to 2 files). Stop when you have evidence
   or after 2 files exhausted.
4. Decision:
   - **Evidenced answer**:
     a. Read the relevant article(s) — both flavors when applicable.
     b. Classify article state vs your answer:
        - `aligned`: article already says the right thing.
        - `divergent`: article says something different.
        - `missing`: article doesn't address the topic.
     c. Decide article action:
        - `aligned` → no change. Record as positive signal.
        - `divergent` + literal text substitution → apply patch.
        - `divergent` + conceptual → emit `proposed_diff`, do not apply.
        - `missing` + literal addition (term, label, value) → apply add.
        - `missing` + conceptual addition (paragraph, flow) → emit
          `proposed_diff`.
     d. Mark question `status: answered_by_code` with full evidence.
   - **No evidence found** → mark question `status: needs_human`.

## Output (return JSON)

```json
{
  "capability": "{capability_slug}",
  "stats": {
    "questions_input": 47,
    "answered_by_code": 28,
    "needs_human": 19,
    "aborted": 0,
    "articles_patched": 11,
    "articles_proposed_diff": 6,
    "articles_aligned_count": 17
  },
  "questions": [
    {
      "id": "Q42",
      "status": "answered_by_code",
      "evidence": {
        "files": ["packages/web/src/views/Billing/Status.vue"],
        "lines": "L42-L48",
        "snippet": "const invoiceStatusLabel = computed(() => ({\n  DRAFT: 'Em aberto',\n  PAID: 'Paga',\n  ...\n}[invoice.status]))"
      },
      "answer": "The visible labels are 'Em aberto', 'Paga', 'Vencida', 'Cancelada'",
      "article_action": "corrected_text",
      "articles_modified": [
        "docs/capacidades/cobranca/faturas.md"
      ],
      "cross_flavor_synced": false,
      "cross_flavor_reason": "tech.md already uses code-level enum names; product.md needed labels",
      "verification_passed": true
    },
    {
      "id": "Q67",
      "status": "answered_by_code",
      "evidence": { "files": ["src/jobs/dunning.ts"], "lines": "L12-L22", "snippet": "..." },
      "answer": "...",
      "article_action": "aligned",
      "articles_modified": [],
      "cross_flavor_synced": false,
      "verification_passed": null
    },
    {
      "id": "Q89",
      "status": "needs_human",
      "reason": "Question is about UX intent of showing X vs Y — not in code."
    },
    {
      "id": "Q103",
      "status": "answered_by_code",
      "evidence": { "files": ["src/services/contract.ts"], "lines": "L201-L210", "snippet": "..." },
      "answer": "...",
      "article_action": "proposed_diff",
      "proposed_diff": "<unified diff text>",
      "articles_modified": [],
      "cross_flavor_synced": false,
      "verification_passed": null
    }
  ]
}
```

## What to NOT do

- Don't summarize whole files; you only need the relevant lines.
- Don't speculate. If your answer requires a leap, mark needs_human.
- Don't proactively rewrite articles for clarity; this phase is
  ONLY about correctness vs code. Style passes happen elsewhere.
- Don't apply proposed_diff yourself. The human reviews those.

````

### Step 3 — Per-capability commit

After each sub-agent returns:

1. Apply any pending writes the sub-agent emitted (it did this itself —
   verify with `git status`).
2. Read its JSON. Update state with new question statuses.
3. Save proposed diffs to `.livedocs/triage/proposed/{capability_slug}.diff`.
4. Commit:

   ```
   git commit -m "phase-5.5: auto-fix from code (cap=<slug>)" \
     -m "Answered <N> questions from code, patched <M> articles,
         proposed <P> diffs for review.
         Aligned: <A>, divergent fixed: <D>, missing added: <X>."
   ```

   Commit message format matters — `phase-5.5:` prefix allows easy
   `git log --grep="phase-5.5:"` audit and `git revert` of all 5.5
   commits if something is systemically wrong.

### Step 4 — Aggregate report to user

After all sub-agents return, present the user with:

```
Phase 5.5 complete:

  Questions:
    Input:                {N}
    Answered by code:     {A}   ({A/N}%)
    Needs human:          {H}   ({H/N}%) → goes to Phase 6
    Aborted (re-queue):   {Z}

  Article fixes:
    Applied directly:     {M}   (literal text/identifier substitutions)
    Proposed diff:        {P}   (conceptual — review at .livedocs/triage/proposed/)
    Aligned (no change):  {C}   (article was already correct)

  Quality signal:
    Aligned ratio: {C / A * 100}%
    (Higher is better — measures how well Phase 4 wrote the drafts.)

  Next: Phase 6 (refinement interview) with {H} questions, organized
  in blocks A-F. Proceed?
```

### Step 5 — Optional review of proposed diffs

Ask the user:

> Want to review the {P} proposed diffs before Phase 6, or after?
> They're at `.livedocs/triage/proposed/`.

Reviewing before Phase 6 means the human comes to the interview with
articles closer to truth — better questions get better answers. But
it's also extra work. Let the user choose.

---

## When to skip Phase 5.5

- **No pending questions** — nothing to triage. Skip.
- **N < 10 questions total** — overhead of sub-agents exceeds benefit.
  Just go to Phase 6 directly.
- **Prerequisites not in place** — listed above. Falling back to direct
  Phase 6 is safer than running 5.5 without guardrails.

---

## Pitfalls

- **Sub-agent finds answer but applies wrong patch.** Mitigation:
  per-capability commit allows `git revert <sha>` of a single
  capability's worth of changes.
- **Sub-agent hits an environment break (corrupted PATH, missing tool)**
  and loops trying to read files. Mitigation: anti-loop guard aborts
  after 2 same-error retries.
- **Question is half-resolvable**: code reveals X but not why X is X.
  Sub-agent should mark `needs_human` and include a `code_context`
  field in the JSON describing what it DID find, so the human enters
  Phase 6 with that context.
- **Two questions touch the same article line**: sub-agent processes
  questions sequentially within a capability; each `read → patch →
  verify` is atomic. Later question reads the already-patched article.
- **Aligned count looks wrong / suspiciously high.** Sub-agent might be
  rubber-stamping. Sanity check: spot-check a couple of `aligned`
  classifications against the actual article + code. If the aligned
  ratio > 80%, investigate — Phase 4 doesn't usually write that well.
- **Cross-flavor mismatch (only one flavor existed)**: report
  `cross_flavor_synced: false` with `cross_flavor_reason` describing
  why no sync was needed (e.g. the technical fact only belongs in
  tech.md).

---

## Quality metric — aligned ratio

The `aligned` count over total answered-by-code is the best honest
signal of Phase 4 quality. Track it across executions:

- **>50% aligned**: Phase 4 wrote drafts that mostly matched the code.
  The 50% you're filtering out are the genuine corner cases.
- **20-50% aligned**: Phase 4 had real gaps but wasn't fabricating.
- **<20% aligned**: Phase 4 wrote a lot it shouldn't have. Worth
  examining the Phase 4 prompt for "fill the gap" style instructions
  that encourage hallucination.

Persist `aligned_ratio` per capability to state so trends are visible
across reruns / partial regenerations.
