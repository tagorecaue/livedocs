# Phase 7 — Global Update

## Goal
Take the answers gathered in Phase 6 and apply them to the affected guides.
Each affected article gets rewritten to incorporate the new information,
removing provisional answers and updating sections that depended on them.

## What to do

> **DELEGATION**: cada guia afetado vira uma sub-task. Sub-agent recebe o
> conteúdo atual + Q&A relevantes, reescreve via Write, retorna só o JSON
> summary. Você (orquestrador) atualiza state.md.

1. **Identify affected guides:** group answered questions by their origin
   guide (or guides — some questions originated from multiple). Result:
   a set of `(guide_slug, list_of_qa_pairs)`.

2. **For each affected guide, spawn a sub-agent:**

   ```
   # Task: incorporate maintainer answers into this guide

   ## Current guide content (product)
   ---
   <content of guide.md>
   ---

   ## Current guide content (technical)
   ---
   <content of guide.tech.md>
   ---

   ## Maintainer answers to incorporate
   <list of Q&A pairs relevant to this guide>

   Q5. "Quando você cria um projeto e ele entra na fase 'Negociação', isso
        dispara alguma notificação automática?"
   A5. "Não. A notificação automática só dispara quando o stage muda PARA
        'Em Atendimento'. Negociação é só observado no Kanban."

   ## Rules

   1. Replace provisional/inferred content with the confirmed answer.
   2. Remove 🟡 markers and "Pendências e melhorias mapeadas" entries that
      now have answers.
   3. Don't change unrelated content. Don't re-stitch links (that's Phase 5's job).
   4. Update both `.md` (product flavor) and `.tech.md` (with code refs if relevant).
   5. If an answer REVEALS new code references (e.g., user mentions a job
      class name), add them to the tech guide's "Modelo de dados" /
      "Pontos de entrada" section.
   6. If an answer CONTRADICTS what the guide says, rewrite the contradicted
      passage, do NOT just delete it.

   ## Output

   Use the Write tool on each modified file. Then return ONLY JSON:

   ```json
   {
     "files_modified": ["docs/.../slug.md", "docs/.../slug.tech.md"],
     "changes_summary": "Substituiu hipótese sobre notificação por mecânica real do stage 'Em Atendimento'. Adicionou referência ao job NotifyStageChange em :42."
   }
   ```
   ```

3. **For each affected guide, run the call.** Print progress:
   ```
   [3/9] atualizando: gestao-projetos/criar-projeto…
   [3/9] gestao-projetos/criar-projeto: ✓ 22s · $0.04 (Substituiu hipótese de notificação por mecânica real)
   ```

4. **After all affected guides updated:**
   - mark them `status="refined"` in state
   - mark answered questions `status="resolved"`
   - update state.md with the final summary

5. **Final celebration message:**
   ```
   ✓ Bootstrap completo!

   Resumo:
     - 67 artigos gerados em docs/
     - 18 capacidades + 5 jornadas
     - 47 perguntas pendentes (18 respondidas, 5 abertas, 24 dedup'd)
     - 9 artigos refinados após respostas
     - 23 screenshot TODOs registrados — abra .livedocs/screenshots.md
       pra ver a lista e capturar manualmente
     - Custo total: $23.40

   Próximos passos sugeridos:
     - Revisar os artigos em docs/ no seu editor
     - Tirar os screenshots (lista em .livedocs/screenshots.md)
     - Publicar no help center (próxima feature da skill)
     - Pra atualizar quando o código mudar: re-invoque esta skill,
       vai detectar mudanças e propor ajustes
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
