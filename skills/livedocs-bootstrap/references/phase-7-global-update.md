# Phase 7 — Topic update

## Goal
Take the answers gathered in Phase 6 for the **current topic** and apply them to
that topic's affected guides. Each affected article gets rewritten to incorporate
the new information, removing provisional answers and updating sections that
depended on them. Scope: ONLY this topic's articles.

## What to do

> **DELEGATION**: each affected guide is a sub-task. Sub-agent receives
> current content + relevant Q&A, rewrites via Write, returns only the
> JSON summary. You (orchestrator) update state.md.

1. **Identify affected guides** within this topic: group the topic's answered
   questions by their origin article. Each answered question carries its
   `answered_via` (`direct` or `propagation-from-Qx`) and `inferred_answer` /
   raw answer from the coverage-aware interview (see `phase-6-refinement.md`).
   Result: a set of `(guide_slug, list_of_qa_pairs)` for this topic only.

1.5. **Check for pending proposed diffs:** read state field
   `proposed_diffs_review`. If `"during_phase_7"`, read
   `.livedocs/triage/proposed/{topic_slug}.diff` and merge it into the relevant
   sub-agent prompt (see Step 2). If `"before_phase_6"` (user already reviewed
   them), skip. If absent (Phase 5.5 produced no diffs), skip.

2. **For each affected guide, spawn a sub-agent:**

   ```
   # Task: incorporate maintainer answers into this guide

   ## Run language
   `{lang}` (from state.md). All user-visible prose you write or rewrite
   stays in `{lang}`. The Q&A pairs below are in `{lang}` (the user
   answered in it) — preserve their wording where natural.

   ## Current guide content (product)
   ---
   <content of guide.md>
   ---

   ## Current guide content (technical)
   ---
   <content of guide.tech.md>
   ---

   ## Maintainer answers to incorporate
   <list of Q&A pairs relevant to this guide, in `{lang}`>

   ## Proposed diff to apply (if present)
   If a `.livedocs/triage/proposed/{topic_slug}.diff` exists for this topic,
   read it and apply the changes alongside the Q&A answers. Treat it as a
   confirmed correction (it was evidenced from code in Phase 5.5). If absent
   or empty, skip this section.

   ## Rules

   1. Replace provisional / inferred content with the confirmed answer.
   2. Remove 🟡 markers and "Pending items and known gaps" entries
      that now have answers.
   3. Don't change unrelated content. Don't add cross-links between topics
      (that's the on-demand Sync command's job).
   4. Update both `.md` (product flavor) and `.tech.md` (with code
      refs if relevant).
   5. If an answer REVEALS new code references (e.g. user mentions a
      job class name), add them to the tech guide's "Data model" /
      "Entry points" section.
   6. If an answer CONTRADICTS what the guide says, rewrite the
      contradicted passage; do NOT just delete it.
   7. Verification: after writing each file, run `wc -c` (must be > 0)
      and grep for a sentinel to confirm the content survived. Set
      `verification_passed: true|false` in the JSON return. See core
      principle 12.

   ## Output

   Use the Write tool on each modified file. Then return ONLY JSON:

   ```json
   {
     "files_modified": ["docs/<...>/slug.md", "docs/<...>/slug.tech.md"],
     "changes_summary": "<one-paragraph summary in {lang} of what changed and why>",
     "verification_passed": true
   }
   ```
   ```

3. **For each affected guide, run the call.** Print progress in `{lang}`:
   ```
   [3/9] updating: project-management/create-project…
   [3/9] project-management/create-project: ✓ 22s · $0.04 (<summary>)
   ```

4. **After all of the topic's affected guides are updated:**
   - mark them `status="updated"` in state
   - bump each guide's `skill_version` front-matter to the current
     SKILL.md version
   - mark answered questions `status="resolved"`
   - update state.md and set the topic's status to `updated`

5. **Topic-complete message** (render in `{lang}`; English skeleton). This
   closes ONE topic, not the whole project — control returns to the topic loop:
   ```
   ✓ Topic complete: recurring-billing

   Summary:
     - 3 articles finalized in docs/
     - 7 pending questions (6 answered, 1 left open)
     - 3 articles updated after answers
     - 4 screenshot TODOs registered — see `.livedocs/screenshots.md`
     - Topic cost: $3.10

   Cross-links to other topics aren't drawn yet — that's the Sync step,
   which runs over the whole doc set on demand.

   What's next?
     - Run Sync now (cross-links, glossary, recommendations)
     - Document another topic (I'll suggest one)
     - Stop — state is saved
   ```

   Then hand back to `references/topic-loop.md` Step 6 (close) → selector.

## Pitfalls

- **Guide doesn't actually exist when Phase 7 runs**: it was left `pending`
  in Phase 4. Skip; don't refine a non-existent guide.
- **Multiple answers contradict each other for the same guide**: rare within a
  single topic, but if it happens, escalate to the user with the conflict.
- **Update introduces NEW 🟡 hypotheses**: agent drifted. Re-prompt with
  emphasis on "remove or resolve hypotheses, never add new ones".
- **Cost spike**: if the user answered very long, some guides might need
  rewriting >50%. That's OK and expected.
- **Applying an inferred (propagation) answer as if stated verbatim**: the
  coverage-aware interview already had the user confirm propagated answers
  (`user_confirmed: true`). Use `inferred_answer`, but if a passage is sensitive
  (an invariant), prefer the user's raw words.
