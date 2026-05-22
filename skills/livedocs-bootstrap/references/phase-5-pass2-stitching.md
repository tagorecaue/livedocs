# Phase 5 — Pass 2: Cross-link Stitching

## Goal
Walk each drafted article and:
1. Resolve `[TODO:link={slug}]` placeholders into real markdown links
2. Add cross-links to OTHER guides that should reference this one
3. Harmonize terminology (if guide A says "fatura" and B says "cobrança",
   pick the dominant term across the help center)
4. Flag direct contradictions between guides

Smaller per-call cost than Phase 4 because input is markdown (not code) and
output is patches, not full rewrites.

## What to do

> **DELEGATION**: Each stitching call needs to read 2 markdown files
> (.md and .tech.md of the article) and produces patches via Write.
> Spawne sub-agent por artigo, mesmo padrão da Phase 4. Você recebe só
> o JSON de retorno (links_added, contradictions, etc.).

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
        - This guide's path: `docs/<kind>/<cap-slug>/<article-slug>.md` (or `docs/jornadas/<slug>.md`)
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

   6. NEVER reorder or rewrite conceptual content. Mudanças mínimas: links,
      term tweaks, contradiction markers. Keep the body intact.

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
     "terms_harmonized": [{"from": "fatura", "to": "cobrança"}],
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

4. **For each contradiction returned**, generate a pending question:
   *"Contradição detectada: este guia diz X, guia <slug> diz not-X. Qual é
   o correto?"*. Add to state.

5. **Update state.md** — mark each stitched article, log links_added /
   contradictions counts.

6. **At the end:**
   ```
   ✓ Pass 2 concluída — 4 artigos stitchados
     - 12 links resolvidos
     - 3 links unresolved (slugs ainda não criados)
     - 2 contradições viraram pending questions
     - 1 termo harmonizado: "fatura" → "cobrança"

   Próximo passo: Phase 6 (refinement) — vou consolidar e te perguntar as
   pending questions. Opções:
     [1] Avançar pra Phase 6
     [2] Pular Phase 6 (mantém pending questions abertas, roda Phase 7 vazia)
     [3] Voltar pra Phase 4 (gerar mais artigos antes de stitchar)
   ```

## Pitfalls

- **Broken Markdown links**: relative path calculation is error-prone. If a
  sub-agent's output produces obviously wrong paths, retry with explicit
  paths in the prompt.
- **Over-linking**: agent might convert every domain term to a link, making
  text noisy. Re-prompt with "máximo 1 link por conceito por parágrafo".
- **Tech ↔ product contamination**: agent might link product.md to tech.md.
  Reject and flag, never store these.
- **Recursive contradictions**: A vs B vs C all say different things. Don't
  try to resolve here — pile them all into pending questions.
- **"unresolved" because slug exists but in another batch**: if user
  stitched only batch 1 articles, links to batch 2 articles will be
  unresolved. Normal — they'll resolve when batch 2 is stitched.
