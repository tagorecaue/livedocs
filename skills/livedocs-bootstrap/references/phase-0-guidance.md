# Phase 0 — Guidance

## Goal
Collect free-form context from the maintainer about the product: who they are,
what the system does, what it's for, references, hints. This text feeds every
later LLM call so it MUST be captured carefully.

## What to do

1. **Open the conversation with this exact intro** (or the user's language equivalent):

   > Antes de começar, conta um pouco sobre o contexto:
   >
   > Quem é você, o que o sistema faz, para que serve. Pode colar
   > referências, instruções gerais ou qualquer coisa que ajude a IA
   > durante a documentação.
   >
   > **Como entregar:**
   > - Cole aqui no chat (multi-linha está OK), OU
   > - Edite `.livedocs/guidance.md` e me avise quando salvar.
   >
   > Texto vazio também é aceitável — só vai depender mais do código.

2. **Wait for the user's response.** Don't proceed without one of:
   - Text in the chat (multi-paragraph OK)
   - User says "criei o arquivo" / "salvei em .livedocs/guidance.md"
   - User explicitly says "sem guidance" / "vazio"

3. **Persist the guidance to disk.** Always write `.livedocs/guidance.md`
   with the captured text (or empty file marker if none). This is the source
   of truth for later phases.

   ```bash
   mkdir -p .livedocs
   cat > .livedocs/guidance.md <<'EOF'
   <USER TEXT HERE>
   EOF
   ```

4. **Initialize state.md if it doesn't exist.** Use the template from
   `references/state-format.md`. Mark phase 0 as "completed", set "Current
   phase" to "1 (scan)".

5. **Ask consent to advance:**

   > Guidance capturada. Próxima fase é o **scan** do código:
   > - Roda `graphify extract` se disponível (gera grafo semântico, usa LLM)
   > - Lê rotas, i18n e models do código
   > - Não chama LLM diretamente nesta fase (graphify usa, mas é orquestrado por ele)
   >
   > Posso seguir?

## Validation

Before leaving phase 0, confirm:
- `.livedocs/guidance.md` exists on disk
- `.livedocs/state.md` exists and lists phase 0 as completed
- User explicitly OK'd advancing to phase 1

## Edge cases

- **User pastes a 10k-char manifesto**: accept it, warn that very long
  guidance increases per-call cost. Don't truncate.
- **User can't articulate**: offer prompts: *"Você prefere que eu pergunte
  por partes? Posso fazer 3-4 perguntas curtas."*
- **User says "lê meu README"**: read it, summarize in 5-10 lines, ask
  *"Confirma esse resumo? Quer adicionar algo?"*. The CONFIRMED summary
  becomes the guidance — not the raw README.
