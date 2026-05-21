# Pending questions

## Why
The agent shouldn't invent answers when code doesn't reveal intent or
external integration details. Instead, register a structured PENDING
QUESTION that gets batched and asked to the user in Phase 6.

## Anatomy

```
Q3 — origin: gestao-projetos/criar-projeto — confidence: low
  Question: Quando você cria um projeto e ele entra na fase 'Negociação' do
            Kanban, isso dispara alguma notificação automática?
  Provisional answer: Não há notificação automática — membros vêem ao abrir
                      o quadro.
  Status: open
  Merged into: -
  Answer: -
```

Fields:
- **id** — sequential `Q1`, `Q2`, … unique across the bootstrap
- **origin** — guide slug that triggered the question (or list of guides)
- **confidence** — `low` | `high`. Reflects how sure the agent is about the
  provisional answer. `high` = agent is 80%+ confident; `low` = anyone's guess.
- **question** — clear, single-sentence ask
- **provisional_answer** — agent's best guess, used in the draft until resolved
- **status** — `open` | `answered` | `merged` | `dropped` | `resolved`
- **merged_into** — set when dedup determines this is equivalent to another Q
- **answer** — user's response, set during Phase 6

## Where they're stored

Inside `.livedocs/state.md`, in the "Pending questions" section. Format:

```markdown
## Pending questions (open: 7, answered: 0, merged: 0)

- **Q1** [gestao-projetos/criar-projeto] How does X interact with Y?
  - Provisional: "X always calls Y first". Confidence: high.
- **Q2** [cobranca-recorrente/conciliacao] When the bank ack returns 404, what does the system do?
  - Provisional: "Retries 3 times then alerts admin". Confidence: low.
- **Q3** [merged into Q1] (was: ...)
```

## Rules

1. **Don't invent answers.** If the code doesn't reveal it, register a
   question. Better to have many questions than fabricated content.

2. **One question per atomic ask.** Don't bundle "What about X, and also
   Y, and Z?". Split into 3 questions.

3. **Provisional answers go in the draft** with 🟡 markers (tech guide
   only). When the question is answered in Phase 6, the 🟡 marker is
   removed and the actual answer replaces the provisional content.

4. **Origin matters.** Multiple guides can hit the same question. Origin
   is a list. After dedup in Phase 6, merged questions inherit the
   canonical's origins for tracking.

5. **Confidence guides UX.** During Phase 6 batch interview, `confidence:
   high` questions get prefaced with "Estou bastante seguro disso —
   confirma?" and `confidence: low` with "Não consegui inferir do código:".

## Anti-patterns

DON'T register:
- Questions answered by the code (just read it harder).
- Questions about external systems the agent shouldn't know (e.g. "What's
  the SLA of the payment provider?" — that's product knowledge, not livedocs).
- Vague questions ("How does this work in general?").

DO register:
- UX intent: why was this designed this way?
- External integrations: which webhook events do we listen to?
- Contradictions between guides (auto-generated during Phase 5).
- Hypotheses with low confidence that need a yes/no from the user.
