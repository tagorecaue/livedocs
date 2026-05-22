# LiveDocs Bootstrap — Plano de melhoria para Open Source

Documento gerado após uma sessão real de bootstrap completo no monorepo <Client>
(24 capacidades, 76 artigos, 6 jornadas — Fases 0 a 6 parcialmente).

Status atual: skill funcional e usável, mas tem conteúdo específico do domínio
<Client> (REURB, terminologia pt-BR hardcoded, exemplos do app) e algumas
fragilidades técnicas que apareceram em uso real. Este plano lista o que precisa
mudar antes de publicar como open-source genérico.

Convenção: itens marcados **[BLOCKER]** são pré-requisito pra release; **[NEXT]**
melhora a próxima iteração; **[NICE]** é nice-to-have.

---

## Parte 1 — Generalização de domínio

### 1.1 [BLOCKER] Strings pt-BR hardcoded no SKILL.md

Locais com mensagens em pt-BR no fluxo (entrada da skill, transições, prompts
de consentimento):

- `"Retomando bootstrap da fase N. Continue?"`
- `"Olá! Vou guiar o bootstrap da documentação deste projeto..."`
- `"Lote concluído. Avançar pra Pass 2 ou gerar mais artigos primeiro?"`
- `"Vou rodar a Pass 2 em 4 artigos..."`

Opções:
- (A) Traduzir tudo pra inglês e adicionar nota: "ajuste para o idioma do projeto".
- (B) Adicionar passo na Fase 0 que pergunta o idioma do projeto e usa daí em diante.

**Recomendação:** B. A skill já tem `Lang:` no state file, mas não usa para
modular as mensagens. Aproveitar.

### 1.2 [BLOCKER] Exemplos do domínio REURB espalhados pelas references

Termos a remover/substituir:
- `REURB_S`, `VIA_RESIDENT` (enum values de REURB)
- `before_tax`, `auto_split` (constants do negócio <Client>)
- `project_stage_type`, `started_at`, `split_distribution` (colunas)
- `gestor`, `operador comercial`, `morador` (personas do app)
- Slugs de exemplo: `gestao-projetos/criar-projeto`,
  `cobranca-recorrente/emissao-boletos`, `splits-bancarios/acompanhar-repasses`

Substituir por:
- Placeholders genéricos: `<enum_value>`, `<database_constant>`, `<persona>`
- OU um app fictício recorrente e simples (ex: SaaS de gestão de inquilinos)
  que seja usado em TODOS os exemplos pra dar coesão sem viés de domínio

### 1.3 [BLOCKER] Regra "UI language" (seção 3b do SKILL.md) tem viés pt-BR

A regra é universal e ótima ("não vazar identifiers de código pra prosa de produto")
mas está escrita assumindo pt-BR:

> "NEVER write a foreign-language word in prose when the product UI is in
> another language (e.g. an English term in a pt-BR product)."

Generalizar:
- Princípio: "use a língua que o produto efetivamente exibe ao usuário"
- Lista de proibições universal (enums, route paths, function names, DB columns,
  technical identifiers) — manter como está
- Tirar a parte sobre `localStorage`, `jsonb`, `enum` específica e usar
  exemplos neutros

---

## Parte 2 — Fragilidades técnicas observadas em uso

### 2.1 [BLOCKER] Sizing de batches está ausente em Phase 5 e Phase 6

**Sintoma observado:** 3 timeouts em uma sessão:
- Sub-agent stitchando 6 jornadas de uma vez (timeout 600s)
- Sub-agent dedupando 314 questões de uma vez (timeout 600s)
- Sub-agent processando capacidades grandes em paralelo (env corrompido)

**Causa:** SKILL.md menciona "batches" em Phase 4, mas Phase 5 (stitching) e
Phase 6 (dedup) não estabelecem limites.

**Correção:** adicionar ao SKILL.md uma tabela de sizing recomendado:

| Operação | Limite por chamada |
|---|---|
| Phase 4 draft | 1 artigo / sub-agent |
| Phase 5 stitch | até 5 artigos / sub-agent |
| Phase 6 dedup | até 80 questões / sub-agent (thematic batches) |
| Phase 7 rewrite | 1 artigo / sub-agent |

E nota: "se ultrapassar, divida em batches temáticos (por capacidade, por tema)
antes de chamar o sub-agent."

### 2.2 [BLOCKER] Esquema JSON ambíguo para clusters de dedup

**Sintoma observado:** 1 dos 4 sub-agents de dedup (batch 1) listou
`canonical_id` dentro de `merged_ids`. Os outros 3 não fizeram. Precisei
limpar programaticamente após.

**Correção:** em `references/phase-6-refinement.md`, mostrar exemplo
explícito **com singleton** e **com cluster real**:

```json
{
  "clusters": [
    // Singleton — Q5 não tem duplicatas
    {
      "canonical_id": "Q5",
      "canonical_question": "...",
      "merged_ids": []
    },
    // Cluster real — Q3 absorve Q7 e Q11; Q3 NÃO aparece em merged_ids
    {
      "canonical_id": "Q3",
      "canonical_question": "...",
      "merged_ids": ["Q7", "Q11"]
    }
  ]
}
```

Reforçar com regra explícita: "`canonical_id` JAMAIS deve aparecer em `merged_ids`."

### 2.3 [BLOCKER] Cross-flavor rule precisa estar no template do sub-agent, não só no SKILL.md

**Sintoma observado:** Phase 5 sub-agent de `contratos` deixou 1 TODO unresolved
porque um `.tech.md` apontava pro próprio `.md` sibling (cross-flavor). A regra
está no SKILL.md mas o sub-agent só recebeu o template do `phase-5-pass2-stitching.md`.

**Correção:** atualizar `references/phase-5-pass2-stitching.md`, regra 7,
adicionar explicitamente:

> 7. **CROSS-FLAVOR PROHIBITED.** `.md` links only to `.md`. `.tech.md` links only to `.tech.md`.
>    - If a `.tech.md` contains `[TODO:link=<same-slug>]` pointing to its OWN product
>      sibling (e.g. `contratos/gerar-assinar-contrato.tech.md` has
>      `[TODO:link=contratos/gerar-assinar-contrato]`), REMOVE the placeholder
>      and its surrounding phrase entirely — do NOT leave as unresolved, do NOT
>      add a cross-flavor link. Report in `cross_flavor_removed` array.

### 2.4 [BLOCKER] Falta recomendação de checkpoint git por batch

**Sintoma observado:** durante uma falha de ambiente, um sub-agent zerou um arquivo
(`docs/.../introducao.md` ficou com 0 bytes). Recuperei via `git checkout HEAD --`,
mas só porque tinha commits intermediários.

**Correção:** adicionar princípio core ao SKILL.md (na seção Core principles):

> 11. **Commit per batch.** Treat each Phase 4 batch and each Phase 5 capability
>     as an atomic git checkpoint. Commit after every successful batch BEFORE
>     starting the next. Recovery from sub-agent corruption or env failure depends
>     on this discipline.

Adicionar exemplo no Phase 4 e Phase 5 references.

### 2.5 [BLOCKER] Mandatory post-edit verification em sub-agents

**Sintoma observado:** o sub-agent que zerou o arquivo **reportou sucesso no JSON**.
Falsos positivos quebram a confiança na pipeline.

**Correção:** em todos os prompts de sub-agent de Phase 4/5/7, adicionar:

> After editing each file, RUN a verification:
> - `wc -c <file>` — confirm file is not zero bytes
> - `grep -c "<sentinel>" <file>` — for Phase 5, confirm `[TODO:link=` count is zero
>   on resolved articles, OR report remaining count
> Include verification results in the returned JSON as `verification_passed: true|false`.
> If verification fails, set the article's `files_modified` to [] and report
> the failure in `errors` array — never report success without verification.

### 2.5b [BLOCKER] Qualidade das pending questions — heurísticas de "o que NÃO perguntar"

**Sintoma observado:** comparando as perguntas que esta skill gerou (314)
com perguntas de uma versão artesanal anterior do livedocs (vide
`packages/docs/guides/*/_meta/*.interview.md` no monorepo <Client>),
ficou claro que a skill atual:

1. Gera muita pergunta que o agente poderia ter respondido lendo até 2 arquivos
   do código (labels de enum visíveis na UI, valores válidos de enums estruturais,
   schedules de cron com nome óbvio, existência de ADRs com path conhecido).
2. Gera perguntas mecânicas sobre estrutura de schema ("X não herda structure.audited
   — intencional?") que são dívida técnica anotável, não pergunta de usuário.
3. Trata cada pergunta como isolada, sem agrupamento temático.

**Exemplos reais que NÃO deveriam ter chegado ao usuário:**
- Q1: "Qual o label do enum invoiceStatusLabel?" — resolvido em 3min lendo BillingDashboard.vue
- Q23: "Quais valores válidos para o enum structure.inbox_conversation_status?" — migration SQL responde
- Q49: "Como visit_result.fields (jsonb) é editado em produção?" — componente revela
- Q58: "ADR-0009 referenciado em código mas arquivo não existe?" — grep responde antes

**Correção:** atualizar `references/pending-questions.md` com tabela explícita:

#### 🚫 NÃO REGISTRAR como pending question:
- Labels de enum visíveis na UI → procurar no `<template>`, arrays `:items=`,
  `t()`/`$t()`, computeds `XxxLabel`, formatters
- Valores possíveis de enums estruturais → existe migration SQL; faça grep
- Comportamento documentado em código com nome óbvio (controller, service, hook)
- Schemas/colunas sem auditoria — anotar como dívida técnica no `.tech.md`,
  não levar ao usuário
- Cron schedules e job names — código revela; só anotar
- Existência de ADRs com path conhecido — `grep` ANTES de perguntar
- "Tabela X tem coluna Y nullable, intencional?" — anotar como pendência
  no tech.md, não perguntar
- "Constante Z existe?" — `grep` resolve

#### ✅ REGISTRAR como pending question:
- **Integrações externas:** webhooks, sequência de chamadas, comportamento
  sob falha do parceiro (ex: Asaas timeout, ZapSign signature_status)
- **Regras de negócio ambíguas:** quando dois caminhos parecem equivalentes
  mas levam a estados diferentes (ex: `auto_canceled` vs `terminated`)
- **Intenção de produto:** *por que* foi feito assim, *quem* configura,
  *quando* é usado
- **Fluxos cruzados:** "quando X muda, o que acontece com Y agendado
  anteriormente?" (mensagem da régua quando contrato é transferido)
- **Confronto código vs narrativa anterior:** "o código sugere X, mas o
  draft diz Y — quem está certo?"
- **Top dúvidas reais de suporte/sucesso** — só o humano tem isso
- **Race conditions / concorrência** — produto decide, código só sugere
- **Bordas que o código não confirma:** rollback transacional, dead-letter
  queues, behavior em conflicting writes

**Princípio guia:** uma pergunta deve ser sobre *INTENÇÃO* ou *EXPERIÊNCIA*,
não sobre *EXISTÊNCIA* ou *VALOR* (que o código tem).

### 2.5c [BLOCKER] Code-first triage + article audit antes de Phase 6

**Observação:** das 314 questões geradas, estimo que ~40-50% podem ser
respondidas lendo até 2 arquivos do código. Mas há um insight maior:

> Se o agente PERGUNTOU em vez de LER o código, significa que escreveu o
> artigo SEM essa informação. Portanto a resposta provisória que está no
> draft hoje pode estar **errada** ou **ausente**. Ruído nas perguntas é
> também ruído nos artigos.

A correção é **dupla**: tirar a pergunta do humano E corrigir o artigo
para refletir a realidade do código.

**Correção:** entre Phase 5 (stitching) e Phase 6 (entrevista humana),
adicionar uma **Phase 5.5 — Code-first triage + article audit**:

```
Para cada capacidade (1 sub-agent por capacidade):
  Inputs:
    - Pending questions dessa capacidade
    - Artigos da capacidade (.md + .tech.md de cada)
    - Acesso ao repositório

  Para cada question:
    1. Tenta resolver via código (até 2 arquivos)

    2. Se RESOLVE:
       a. Lê o que o artigo diz hoje sobre o tema
       b. Classifica: aligned | divergent | missing
       c. Se divergent ou missing:
          - Patcha o artigo (ambos os flavors quando relevante)
          - Registra diff no retorno
       d. Marca question como `status: "answered_by_code"`,
          inclui `evidence_files: [path:line]` e
          `article_action: aligned|corrected|added`

    3. Se NÃO RESOLVE (precisa intenção/UX/produto):
       - Marca como `status: "needs_human"`
       - Mantém aberta para Phase 6

  Retorna JSON consolidado por capacidade
```

**Regras críticas:**
- Sub-agent só responde via código com EVIDÊNCIA EXPLÍCITA (file:line).
  Se exige inferência → marca como needs_human.
- Para correções de artigo:
  - **Aplica diretamente** mudanças ortográficas (label exato de enum,
    valor de constante, nome de tabela/coluna).
  - **Propõe diff sem aplicar** quando a mudança é conceitual (regra de
    negócio que parece errada, fluxo distorcido). Usuário revisa em batch.
- Sempre commit por capacidade, com message diferenciando "phase-5.5
  auto-fix from code" → permite revisão e revert seletivo.

**Resultado esperado:**
- 40-60% das questões removidas da entrevista humana
- Artigos corrigidos para refletir o código real
- Histórico claro do que foi auto-corrigido vs respondido pelo humano
- Phase 6 fica focada em questões de produto puras (intenção, UX, integrações)

**Verification pós-Phase 5.5:** após cada capacidade auto-corrigida,
o sub-agent OU um audit script deve confirmar:
- Nenhum artigo zerado
- Diff faz sentido (não removeu conteúdo legítimo, só corrigiu)
- pending_questions atualizadas no metadado do artigo

### 2.5d [BLOCKER] Estrutura das perguntas por bloco temático (Phase 6)

**Observação:** perguntas isoladas por origem cansam o usuário e perdem
sinergia. Versão artesanal usa blocos temáticos (A-F) que dão "modo mental"
ao entrevistado.

**Correção:** em `references/phase-6-refinement.md`, depois do dedup,
agrupar canonicals em blocos:

- **A — Significado de produto / glossário:** o que esse termo, status,
  campo significa no negócio?
- **B — Transições e gatilhos:** quem dispara X → Y? cron? webhook? manual?
- **C — Regras invariantes / constraints:** o que NUNCA pode acontecer?
- **D — Vivência do usuário e suporte:** top dúvidas, copy, fluxos reais
- **E — Bordas do código (hipóteses do agente):** o código sugere X,
  mas não confirma
- **F — Direção do guia (meta):** profundidade certa? faltou algo? próximo guia?

Sub-agent extra após dedup: "classifica cada cluster em A/B/C/D/E/F".
Entrevista percorre blocos na ordem (A→F), não capacidades.

Bônus: a entrevista pode ser salva como markdown render por bloco
(`.livedocs/interview/bloco-A.md`, etc.) que o usuário responde inline.

### 2.5e [BLOCKER] Confronto código vs narrativa anterior

**Observação:** na v1 artesanal, o agente comparou o que o usuário falou
em entrevistas ANTERIORES com o que viu no código DEPOIS, e usou as
divergências como gatilho de pergunta ("você disse X, código mostra Y").
Isso gera perguntas de altíssima qualidade.

**Correção:** se já existem entrevistas respondidas em
`.livedocs/interview/*` ou `.livedocs/answered/*.md`, sub-agent que gera
perguntas para um novo guia DEVE:
1. Ler transcrições anteriores relevantes pro tema do novo guia
2. Comparar com código atual
3. Se houver discrepância clara, gera UMA pergunta de confronto
   (com `confidence: high`, citando ambos os lados)
4. Não gera perguntas redundantes com o que já foi respondido

Este é o caminho pra docs vivos: cada nova rodada refina, não reinventa.

### 2.6 [NEXT] Phase 6 escala mal — sugerir thematic batching como técnica oficial

**Observação:** 314 perguntas precisaram ser quebradas em 4 batches temáticos
(por capacidade) pra evitar timeout. A cross-batch pass depois pegou mais 13
duplicatas. Isto deveria ser documentado.

**Correção:** em `references/phase-6-refinement.md`, adicionar seção
"Scaling dedup":

> If you have more than ~80 pending questions, do a two-pass dedup:
>
> 1. **Intra-batch pass:** split questions into thematic batches (by capability
>    or by topic) of ~60-80 questions each. Run one sub-agent per batch in
>    parallel. Each returns batch-local clusters.
> 2. **Cross-batch pass:** pass the canonical questions from all batches
>    (without merged duplicates) to a single new sub-agent that finds
>    cross-batch duplicates. Output the same `clusters` format.
> 3. Apply both pass results to reconcile into a single clusters file.

Incluir script de reconciliação (ver Parte 3.1 abaixo).

### 2.7 [NEXT] Anti-loop guard pra sub-agents

**Sintoma observado:** quando o ambiente da shell quebrou (PATH corrompido,
`cat`/`grep` indisponíveis), 1 sub-agent ficou 463s e fez 90+ tool calls
em loop tentando ler arquivos que falhavam sempre com a mesma mensagem.

**Correção:** em **todos** os prompts de sub-agent, adicionar:

> If the same tool fails 2× in a row with the same error message, ABORT the task.
> Do NOT retry. Return a JSON with `status: "aborted"` and `error: "<message>"`.
> Manual intervention will be needed — silent retry burns context for nothing.

### 2.8 [NICE] State file não tem schema validável

Hoje o state.md é markdown livre. Erros silenciosos de formatação podem
quebrar a retomada.

**Correção:** publicar `references/state-schema.json` (JSON Schema) e/ou
mover state pra `.livedocs/state.json` em vez de `.livedocs/state.md`.
Manter `.livedocs/state.md` opcional como vista humana renderizada do JSON.

### 2.9 [NICE] Calibrar estimativas de custo com dados reais

A skill estima ~$0.30/artigo na Phase 4. Na minha sessão, o custo real foi
~$0.90/artigo na Phase 4 (3× a estimativa). Phase 5 variou $0.50–$3 por
capacidade.

**Correção:**
- Atualizar números no SKILL.md baseados em pelo menos 2 execuções reais (este
  projeto + um piloto público).
- Adicionar instrução: skill deve logar `cost_actual_usd` no state file ao final
  de cada batch. Próxima iteração pode usar média histórica.

### 2.10 [NICE] Interview UX (Phase 6) não escala em chat único

288 perguntas 1-a-1 no chat são cansativas. Considerar:

(a) Exportar perguntas em batches numerados pra arquivos `.livedocs/interview/batch-NN.md`
    com placeholders pra respostas inline.
(b) Permitir que o usuário responda múltiplas perguntas em um editor offline,
    depois importe.
(c) Manter o modo 1-a-1 como fallback.

---

## Parte 3 — Ferramentas/scripts auxiliares pra publicar junto

### 3.1 [BLOCKER] Script de reconciliação cross-batch (Phase 6)

Após dedup em batches, é preciso unir os resultados. Hoje fiz inline no execute_code.
Publicar como script standalone:

```
scripts/reconcile-dedup.py <batch-1.json> <batch-2.json> ... <cross-batch.json>
  → produz clusters-final.json
```

Algoritmo:
1. Carregar todos os batches.
2. Limpar canonical_id duplicado dentro de merged_ids (bug 2.2 acima).
3. Aplicar merges cross-batch: absorber canonicals listados em outras canonicals.
4. Validar invariantes: cada Q aparece em exatamente um cluster.
5. Ordenar por size DESC, canonical_id ASC.

### 3.2 [BLOCKER] Script de auditoria pós-Phase 5

Verifica que:
- Nenhum `[TODO:link=` sobrou em nenhum arquivo (exceto se reportado como `unresolved`).
- Todos os links markdown apontam pra arquivos que existem.
- Nenhum `.md` cita um `.tech.md` (cross-flavor) e vice-versa.

```
scripts/audit-stitching.py docs/
```

### 3.3 [NICE] Script de validação do state

```
scripts/validate-state.py .livedocs/state.md
```

Verifica que cada capacidade declarada na state realmente tem arquivos
correspondentes em `docs/capacidades/`.

---

## Parte 4 — Documentação / branding

### 4.1 [BLOCKER] README do skill

Hoje só tem o SKILL.md. Pra publicação separar:
- **README.md** público: o que é, como instalar (assumir Claude Code / similar),
  exemplo de uso (1 prompt), 1-2 screenshots dos artefatos gerados.
- **SKILL.md**: continua sendo o "manual interno" pro agente.

### 4.2 [BLOCKER] Demo / quickstart

Criar um repo público minúsculo de exemplo (50–100 arquivos, framework conhecido
tipo Next.js todo list app) com docs/ gerado pela skill commitada. Serve como
exemplo concreto de output esperado.

### 4.3 [NEXT] CHANGELOG e versionamento

Hoje SKILL.md tem `version: 1.0.0` mas sem CHANGELOG.md. Adicionar antes
da primeira release pública.

---

## Ordem sugerida de execução

1. **Sprint 1 — Generalização (Parte 1)**: 1.1, 1.2, 1.3. Saída: skill rodável
   em qualquer projeto sem viés <Client>.
2. **Sprint 2 — Integridade (Parte 2 blockers)**: 2.1, 2.2, 2.3, 2.4, 2.5.
   Saída: skill confiável em batches grandes, com recovery.
3. **Sprint 3 — Ferramentas (Parte 3 blockers)**: 3.1, 3.2. Saída: scripts
   pra auditoria/reconciliação publicáveis junto.
4. **Sprint 4 — Publicação (Parte 4 blockers)**: 4.1, 4.2. Saída: pronto pra
   open source.
5. **Iteração 2 (pós-release)**: items NEXT (2.6, 2.7, 2.9, 2.10, 4.3, 3.3).
6. **Iteração 3**: items NICE.

---

## Snapshot da sessão que originou este plano

- Projeto: <Client> monorepo (SaaS REURB, ~38k nós no graphify scan)
- Output: 164 arquivos markdown (82 product + 82 tech) através de 24 capacidades
  + 6 jornadas
- Phase 4 cost real: ~$74 (vs estimado $0.30/artigo × 76 = $22.80 — 3.2× off)
- Phase 5 cost real: ~$20 acumulado (24 capacidades + 6 jornadas)
- Phase 6 dedup: 314 → 288 clusters únicos (8.3% colapso, conservador)
- Total wall-clock: ~3h fases 5+6 (com timeouts e retries)
- 1 incidente de zeragem de arquivo (recuperado via git)
- 3 timeouts de sub-agent (jornadas all-in-one; dedup 314-de-uma-vez; lote
  inicial de capacidades grandes em paralelo)
