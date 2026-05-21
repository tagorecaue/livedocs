# Phase 6 — Refinement Interview

## Goal
Resolve pending questions accumulated during Phases 4 and 5. This is a
**conversation with the user**, in batches, asking the questions the agent
couldn't answer from code alone.

## What to do

1. **Read pending questions from state.** Filter `status == "open"`.

2. **Dedup via LLM call** (1 single call):

   > Below are N pending questions accumulated during documentation. Many
   > are likely equivalent. Group them into clusters; for each cluster pick
   > a canonical version (rewrite the question if a better phrasing helps)
   > and mark the others as `merged_into=<canonical_id>`.
   >
   > Output JSON:
   > ```json
   > {
   >   "clusters": [
   >     {"canonical_id": "Q3", "canonical_question": "...", "merged_ids": ["Q7", "Q11"]},
   >     ...
   >   ],
   >   "unique_ids": ["Q1", "Q2", "Q5"]
   > }
   > ```

   Apply the dedup: questions marked merged_into get `status="merged"` and
   inherit the canonical's answer when it's answered.

3. **Tell the user** the count after dedup:
   > De 47 perguntas pendentes, consolidei em 23 únicas após deduplicação.
   > Vou te perguntar uma de cada vez. Você pode responder, digitar `/skip`
   > para pular, ou `/sair` para pausar.
   >
   > Pronto pra começar?

4. **Loop**: for each canonical question (those still `status="open"`):

   ```
   Pergunta 5/23 (origem: gestao-projetos/criar-projeto)

   O agente perguntou:
     "Quando você cria um projeto e ele entra na fase 'Negociação' do
      Kanban, isso dispara alguma notificação automática pros membros do
      time, ou eles precisam ver no quadro?"

   Suposição provisória no rascunho (confiança: baixa):
     "Não há notificação automática — membros vêem ao abrir o Kanban."

   Outras perguntas que esta também responde:
     - Q12 (cobranca-recorrente/emissao-boletos): "Mudanças de stage geram alerta?"

   Sua resposta (ou /skip / /sair):
   >
   ```

5. **When user answers:**
   - Save the answer to the canonical question (status="answered", answer="...")
   - Propagate to merged questions (status="answered", answer=<same>)
   - **Re-evaluate other open questions** — sometimes one answer makes another
     obsolete. After the answer, scan remaining canonical questions: if any
     CLEARLY are now resolved (the answer covers them), tell the user:
     > Sua resposta também parece responder Q12 ("Existe alerta de mudança
     > de stage?"). OK marcar Q12 como respondida com a mesma resposta?

6. **When user types `/skip`**: leave the question open. Continue.

7. **When user types `/sair`**: save state (answered questions persist),
   exit gracefully:
   > Pausando refinamento. Você respondeu 8/23 perguntas. Pra continuar,
   > re-invoque a skill — vou retomar daqui.

8. **At end of loop**, save state, summarize:
   > ✓ Refinamento concluído — 18/23 perguntas respondidas, 5 ficaram abertas
   > (você optou por pular).
   >
   > Próxima fase: Global Update — vou reabrir os artigos afetados pelas
   > respostas e incorporar as informações. Estimativa: ~M artigos afetados,
   > custo ~$X.
   >
   > Avançar?

## Pitfalls

- **User answers vague ("não sei", "depende")**: that's a real answer.
  Save it; phase 7 will write it as a documented uncertainty in the guide.
- **User answers a 5-paragraph essay**: accept all. Save full text.
- **Question has no clear origin guide**: dedup might lose this. Fallback:
  treat as standalone and use it during phase 7's global update considering
  all guides.
- **Agent gets stuck reformulating questions**: just use the original
  question text — don't over-engineer the dedup.
- **User pauses and resumes much later**: pending questions older than a
  week might be obsolete (code may have changed). Warn user; offer to
  drop them.
