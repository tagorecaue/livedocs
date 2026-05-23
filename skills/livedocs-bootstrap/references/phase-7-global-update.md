# Phase 7 — Global Update

## Goal
Take the answers gathered in Phase 6 and apply them to the affected guides.
Each affected article gets rewritten to incorporate the new information,
removing provisional answers and updating sections that depended on them.

## What to do

> **DELEGATION**: each affected guide is a sub-task. Sub-agent receives
> current content + relevant Q&A, rewrites via Write, returns only the
> JSON summary. You (orchestrator) update state.md.

1. **Identify affected guides:** group answered questions by their
   `canonical_origins` list (each canonical may have multiple origin guides
   after Phase 6 dedup merged questions from different capabilities). Result:
   a set of `(guide_slug, list_of_qa_pairs)`.

1.5. **Check for pending proposed diffs:** read state field
   `proposed_diffs_review`. If `"during_phase_7"`, read
   `.livedocs/triage/proposed/` and merge any diff for a capability into
   that capability's sub-agent prompt (see Step 2). If `"before_phase_6"`
   (user already reviewed them manually), skip this step. If the field is
   absent (Phase 5.5 did not run or produced no diffs), skip.

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
   If a `.livedocs/triage/proposed/{capability_slug}.diff` exists for this
   guide's capability, read it and apply the changes alongside the Q&A
   answers. Treat it as a confirmed correction (it was evidenced from code
   in Phase 5.5). If absent or empty, skip this section.

   ## Rules

   1. Replace provisional / inferred content with the confirmed answer.
   2. Remove 🟡 markers and "Pending items and known gaps" entries
      that now have answers.
   3. Don't change unrelated content. Don't re-stitch links (that's
      Phase 5's job).
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

4. **After all affected guides updated:**
   - mark them `status="refined"` in state
   - bump each guide's `skill_version` front-matter to the current
     SKILL.md version
   - mark answered questions `status="resolved"`
   - update state.md with the final summary

5. **Final celebration message** (render in `{lang}`; English skeleton):
   ```
   ✓ Bootstrap complete!

   Summary:
     - 67 articles generated in docs/
     - 18 capabilities + 5 journeys
     - 47 pending questions (18 answered, 5 left open, 24 deduped)
     - 9 articles refined after answers
     - 23 screenshot TODOs registered — open `.livedocs/screenshots.md`
       to see the list and capture them manually
     - Total cost: $23.40

   Suggested next steps:
     - Review the articles in `docs/` in your editor
     - Capture the screenshots (list at `.livedocs/screenshots.md`)
     - Publish to the help center (future skill feature)
     - To update when the code changes: re-invoke this skill — it'll
       detect changes and propose adjustments (future skill feature)
   ```

## Pitfalls

- **Guide doesn't actually exist when phase 7 runs**: it was marked
  `pending` in phase 4. Skip; don't refine a non-existent guide.
- **Multiple answers contradict each other for the same guide**: that
  shouldn't happen post-dedup, but if it does, escalate to user with
  the conflict.
- **Update introduces NEW 🟡 hypotheses**: agent drifted. Re-prompt with
  emphasis on "remove or resolve hypotheses, never add new ones".
- **Cost spike**: if user answered very long, some guides might need
  rewriting >50%. That's OK and expected.
