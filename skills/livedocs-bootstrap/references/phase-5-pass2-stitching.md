# Phase 5 — Pass 2: Cross-link Stitching

## Goal
Walk each drafted article and:
1. Resolve `[TODO:link={slug}]` placeholders into real markdown links
2. Add cross-links to OTHER guides that should reference this one
3. Harmonize terminology (if guide A says term X and B says term Y for
   the same concept, pick the dominant one across the help center)
4. Flag direct contradictions between guides

Smaller per-call cost than Phase 4 because input is markdown (not code) and
output is patches, not full rewrites.

## What to do

> **DELEGATION**: Each stitching call needs to read 2 markdown files
> (.md and .tech.md of the article) and produces patches via Write.
> Spawn one sub-agent per article, same pattern as Phase 4. You receive
> only the JSON return (links_added, contradictions, etc.).

1. **List drafted articles + journeys.** Skip anything still in `pending`
   or already `stitched`. If the user just finished a Phase 4 batch with
   N articles, Pass 2 only touches those N.

2. **Build the "index of others":** for every drafted guide produce
   `{slug, title, summary, first_paragraph}` (~200 chars each). This is
   the MENU that each stitch call uses as context.

3. **For each guide to stitch, spawn a sub-agent** with this prompt:

   ```
   # Task: stitch this guide to the help center

   ## This guide (full content)
   ---
   <content of <guide>.md>
   ---

   ## Tech guide (full content)
   ---
   <content of <guide>.tech.md>
   ---

   ## Index of other guides (titles + summaries + first paragraph)
   <index of others>

   ## Placeholders found in this guide
   - [TODO:link=cobranca-recorrente/emissao-boletos]
   - [TODO:link=primeira-fatura]
   - ...

   ## Rules

   1. Each [TODO:link={slug}] must become a real Markdown link IF the slug
      exists in the index. Use the title from the index as link text. Format:
      `[<title>](path/relative/to/this/file)`.

      Path computation (use forward slashes):
        - This guide's path: `docs/<kind-dir>/<cap-slug>/<article-slug>.md` (or `docs/<journeys-dir>/<slug>.md`)
        - Target's path: same logic
        - Compute the relative path between them.

   2. If [TODO:link=X] points to a slug NOT in the index, leave as-is but
      add to the response's `unresolved_links` array.

   3. Look for paragraphs that CLEARLY discuss something that another guide
      covers, even without TODO:link. Add inline links where natural —
      one per concept, don't over-link. Note count in `links_added`.

   4. Harmonize terminology: if you notice this guide uses term X but the
      index suggests term Y is dominant elsewhere, change to Y. Note in
      `terms_harmonized` array (from, to).

   5. Flag contradictions: if this guide says X about feature F and another
      guide's first paragraph says NOT-X about F, register in
      `contradictions`: { this_guide_says, other_guide_slug, other_says }.

   6. NEVER reorder or rewrite conceptual content. Minimum changes only:
      links, term tweaks, contradiction markers. Keep the body intact.

   7. **CROSS-FLAVOR PROHIBITED.** `.md` links ONLY to other `.md`.
      `.tech.md` links ONLY to other `.tech.md`. The .tech.md version
      stitches under the SAME rules but with the tech-flavor index.

      Special case — `.tech.md` containing `[TODO:link=<same-slug>]`
      pointing to its OWN product sibling (e.g.
      `contratos/gerar-assinar-contrato.tech.md` has
      `[TODO:link=contratos/gerar-assinar-contrato]`):
      **REMOVE the placeholder and its surrounding phrase entirely** —
      do NOT leave as unresolved, do NOT add a cross-flavor link.
      Report the slug in a `cross_flavor_removed` array of the response.

      This rule exists because the .tech.md and .md of the same article
      describe the same thing for different audiences — linking between
      them creates a loop that adds no value.

   8. Output ONLY JSON, no prose:

   ```json
   {
     "files_modified": ["docs/.../slug.md", "docs/.../slug.tech.md"],
     "links_added": 4,
     "todos_resolved": 3,
     "todos_unresolved": ["mystery-slug"],
     "terms_harmonized": [{"from": "<source term>", "to": "<canonical term>"}],
     "contradictions": [
       {"this_guide_says": "...", "other_guide": "slug", "other_says": "..."}
     ],
     "cross_flavor_removed": ["contratos/gerar-assinar-contrato"],
     "new_pending_questions": [
       {"question": "...", "provisional_answer": "...", "confidence": "low"}
     ],
     "verification_passed": true
   }
   ```
   ```

4. **For each contradiction returned**, generate a pending question
   (text in `{lang}`, semantic equivalent of):
   *"Contradiction detected: this guide says X, guide `<slug>` says
   not-X. Which is correct?"*. Add to state.

5. **Update state.md** — mark each stitched article, log links_added /
   contradictions counts.

6. **At the end** (render in `{lang}`):
   ```
   ✓ Pass 2 done — 4 articles stitched
     - 12 links resolved
     - 3 links unresolved (slugs not created yet)
     - 2 contradictions became pending questions
     - 1 term harmonized: "<from>" → "<to>"

   Next step: Phase 5.5 (code-first triage) — re-checks pending
   questions against code and patches articles that need it.
   Options:
     [1] Advance to Phase 5.5
     [2] Skip 5.5, go straight to Phase 6 (not recommended)
     [3] Back to Phase 4 (generate more articles before stitching)
   ```

## Pitfalls

- **Broken Markdown links**: relative path calculation is error-prone. If a
  sub-agent's output produces obviously wrong paths, retry with explicit
  paths in the prompt.
- **Over-linking**: agent might convert every domain term to a link, making
  text noisy. Re-prompt with "max 1 link per concept per paragraph".
- **Tech ↔ product contamination**: agent might link product.md to tech.md.
  Reject and flag, never store these.
- **Recursive contradictions**: A vs B vs C all say different things. Don't
  try to resolve here — pile them all into pending questions.
- **"unresolved" because slug exists but in another batch**: if user
  stitched only batch 1 articles, links to batch 2 articles will be
  unresolved. Normal — they'll resolve when batch 2 is stitched.
