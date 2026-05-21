# LiveDocs — Plano v0.2 (Adaptive Auditor)

> **Onde está este plano:** `~/dev/livedocs/.spec/v0-cli-oss/plano-v02.md`
>
> Arquivos relacionados nesta pasta:
> - `spec.md` — spec original v0 (CLI dogfood)
> - `lacunas.md` — decisões macro (cloud, paid)
> - `lacunas-cli.md` — decisões CLI v0
> - **`plano-v02.md` (este)** — plano da evolução adaptativa
>
> Repo: `~/dev/livedocs/` · Branch: `master` · Versão atual: `0.2.0a1`

---

## Visão

LiveDocs vira um **auditor permanente do conhecimento**. Não é "ferramenta de doc
com entrevista" — é um sistema que **reflete antes, durante, depois, e cruzado**
sobre o que está sendo documentado.

### Princípios não-negociáveis

1. **Evidência detectada no código nunca é ignorada.**
   Fact com evidência → tratamento explícito (auto-resposta, pergunta, ou 🟡 em
   Pendências). Categoria "silenciável" só existe para `speculation` (sem evidência).
2. **IA propõe, humano aprova** — sem commit silencioso.
3. **Iteração interna pré-humano** — você vê o resultado polido, não o rascunho.
4. **UX fluida, sem milhares de parâmetros** — fluxo guia o usuário.
5. **Tokens não restringem; qualidade é o produto.**

### Os 6 momentos de auto-avaliação

```
1. ENTRY            — parse de intent (texto livre → slug/domain/title)
2. PRE-INTERVIEW    — audit do esqueleto (categoria faltando, tamanho)
   ↓
   INTERVIEW LOOP
   3. REFLECT       — cross-check no código a cada resposta
   ↓
4. PRE-GENERATE     — self-audit (evidência de cada afirmação)
   ↓
5. POST-GENERATE    — 5 dimensões em paralelo
   ↓ inbox
6. CROSS-BASE       — reverse-link sweep, contradições, glossário emergente
```

---

## Status — o que existe hoje (v0.2.0a1)

### ✅ Phase A — Fundação (commit `2c95528`)
- `livedocs/models.py` com: `Fact`, `Evidence`, `Issue`, `Evaluation`, `InboxItem`,
  `NextRecommendation`, novo `InterviewState` (facts[]), `GlobalState` (inbox[]).
- `Fact.priority`: `established` / `needs-confirmation` / `hypothesis-with-trace` /
  `speculation` (única silenciável — princípio "evidência nunca ignorada").
- `Issue.severity`: `blocker` / `evidence-based` / `subjective`.
- `ProjectConfig.guides_subdir` (campo existe — não detecta automático ainda).
- Migração v1→v2: `questions[]` → `facts[]` automática, idempotente, preserva
  custos/datas/last_touched.
- Shim `InterviewState.questions` (read-only) projeta `facts[]` no formato v0.1
  pra UI antiga continuar funcionando.

### ✅ Phase B — Prompts novos (commit `05f4e11`)
- `PROMPT_PARSE_INTENT` — texto livre → metadata estruturada
- `PROMPT_BUILD_SKELETON` — agente lê código, monta `Fact[]` com auto-audit
- `PROMPT_REFLECT_ON_ANSWER` — cross-check + cobertura + novos fatos
- `PROMPT_PREGEN_SELF_AUDIT` — lista evidência de cada afirmação
- `PROMPT_GENERATE_GUIDES` — reescrito pra consumir facts
- `PROMPT_EVAL_PRODUCT_CLARITY` / `_TECH_COMPLETENESS` / `_BASE_COHERENCE` (3 dim)
- `PROMPT_REVERSE_LINK_SWEEP`
- System prompt rebrandado: agente é executor, CLI orquestra.

### ✅ Phase C — Fluxo adaptativo E2E (commit `3b0a467`)
- `livedocs new` aceita **texto livre** ("documenta a tela X do menu Y").
- Agente parseia intent → `{slug, domain, title}` com confirma/edita.
- `build_skeleton` lê código, gera 10–30 facts (não 20 fixos), faz auto-audit.
- Loop adaptativo: 1 fact-pergunta por vez, com **barra de cobertura visual**
  + contadores `✓ N  → N  🟡 N`.
- A cada resposta: cross-check no código, propagação de cobertura, novos fatos
  emergentes, detecção de contradição com `file:line`.
- Pre-gen audit: bloqueia geração se fato crítico sem resposta.
- Front-matter ganha `confidence_summary` + `quality_score`.
- Interview record em formato canônico `**{Fact_ID}.**` + `**Resposta:**` + `---`.

### Smoke E2E validado
- repo `/tmp/ld-e2e` com `cart.py` simples
- intent: "document the shopping cart lifecycle"
- Resultado: 18 facts (10 estabelecidos do código + 4 needs-confirmation + 4
  hipóteses), 3 agent calls, $0.58, 95s, confidence 77.78%
- 3 arquivos gerados com qualidade verificada manualmente
- Status flow `in_progress → generated` correto (não pula `approve`)

### Não tem ainda (vem nas próximas fases)
- Inbox + comando `livedocs inbox`
- 3 dimensões de avaliação pós-geração (prompts prontos, fluxo não)
- Iteração interna pré-humano (até 3 ciclos com auto-fix)
- Cross-base reflection (reverse-link sweep)
- Import de `packages/docs/` legado
- Auto-detect `guides_subdir`
- Atualização automática de `_index.md` por domínio
- **Style guide configurável** (3 templates no init + `.livedocs/style.md` customizável)

---

## Style guide configurável (Phase D)

**Decisão:** ao invés de embutir estilo fixo no `PROMPT_GENERATE_GUIDES`,
oferecer 3 templates no `livedocs init`. Cada template vira `<repo>/.livedocs/style.md`
que pode ser editado livremente. O `PROMPT_GENERATE_GUIDES` carrega esse arquivo
quando existe.

### Os 3 templates

**1. Narrative de produto (default)** — `livedocs/skill/styles/narrative.md`
- ICP: SaaS B2B operacional/financeiro. Cliente final = humano não-técnico.
- Voz: 3ª pessoa do usuário, prosa contínua, explica porquê antes do como.
- Característica única: seção "Casos do dia a dia" em 1ª pessoa entre aspas.
- Referência: `~/dev/nexa/docs/captura/gravar-tela-com-extensao.md`, guides
  da <Client>, Stripe (parte de produto), Linear changelog.

**2. Técnico de referência** — `livedocs/skill/styles/reference.md`
- ICP: API, SDK, devtool, infra. Cliente final = dev.
- Voz: 2ª pessoa diretiva, frases curtas, code blocks frequentes.
- Característica única: pré-requisitos listados antes de qualquer instrução,
  sem narrativa de "porquê" (assume conhecimento).
- Referência: Stripe API docs, AWS docs, DataDog, Hono.dev.

**3. Tutorial conversacional** — `livedocs/skill/styles/tutorial.md`
- ICP: B2C ou B2B simples, onboarding, help center pra usuário não-técnico.
- Voz: 2ª pessoa amigável, didática, professor paciente. Permite humor leve.
- Característica única: sessões progressivas ("primeiro… depois… agora…"),
  acolhedor sem ser paternalista.
- Referência: Notion help, Tailwind docs (tutoriais), Mintlify quickstarts.

### Implementação

- Embed em `livedocs/skill/styles/` 3 arquivos de ~30-60 linhas cada com:
  regras de voz, exemplo de abertura, exemplo de "casos do dia a dia",
  vocabulário negativo (o que evitar).
- `livedocs init` ganha pergunta: "Que estilo de escrita?" com opções +
  link "Pode personalizar depois em `.livedocs/style.md`".
- `init` copia o escolhido pra `<repo>/.livedocs/style.md`.
- `PROMPT_GENERATE_GUIDES` lê `style.md` se existir e injeta no prompt como
  contexto de estilo.
- `PROMPT_EVAL_PRODUCT_CLARITY` e `_TECH_COMPLETENESS` também recebem o
  style.md (avaliação respeita o estilo escolhido).
- Sem opção "custom em branco" no init (pula essa fricção; usuário pode
  sempre apagar e reescrever depois).

---

## Ajustes detectados pelo Tagôre no primeiro teste

> Tagôre testou rápido e disse "funcionou, com pequenos ajustes — é normal".
> Detalhes específicos a coletar na próxima sessão.

**Placeholder para anotar quando voltarmos:**
- [ ] (ajuste 1)
- [ ] (ajuste 2)
- [ ] (ajuste 3)

---

## Próxima sessão — Phase D (Avaliações + Inbox + Cross-base + Style)

Restante da **Fase 1 do plano macro** (já aprovada):

### D.0 — Style guide configurável (NOVO — pré-requisito de D.1)
- Embed 3 templates em `livedocs/skill/styles/{narrative,reference,tutorial}.md`.
- `livedocs init` oferece escolha; copia escolhido pra `<repo>/.livedocs/style.md`.
- `PROMPT_GENERATE_GUIDES` + os 3 evaluators carregam `style.md` quando existe.

### D.1 — Evaluator paralelo
Novo módulo `livedocs/evaluator.py`:
- Roda 3 chamadas Claude em paralelo após geração:
  - `PROMPT_EVAL_PRODUCT_CLARITY` lendo `produto.md`
  - `PROMPT_EVAL_TECH_COMPLETENESS` lendo `tech.md`
  - `PROMPT_EVAL_BASE_COHERENCE` cruzando com guides irmãos + glossário
- Acumula `Issue[]` em `interview.evaluations[]`.

### D.2 — Iteração interna pré-humano (até 3 ciclos)
- Issues `severity = subjective` com `auto_fix_available = true` → aplicar patch
  automaticamente.
- Issues `severity = evidence-based` com patch viável → aplicar e mostrar nota.
- Re-rodar evaluations rapidamente; sai do loop quando convergir ou hit max 3
  ciclos. Tela final mostra "Polido em N ciclos" sem ruído.

### D.3 — Inbox
- Modelos já existem (`InboxItem`, `GlobalState.inbox[]`).
- Issues blocker/evidence-based que sobraram após iteração → vão pra inbox.
- Novo comando `livedocs inbox`:
  - Lista pendentes com tipo + contexto curto + ação proposta
  - Navega com setas; teclas: `a` aceita (aplica patch), `r` rejeita, `s` adia,
    `v` ver detalhes, `q` sair.
- Menu default (`livedocs`) mostra "📥 N itens pendentes na inbox" quando aplica.

### D.4 — Cross-base — reverse-link sweep
- Após `livedocs approve`, dispara `PROMPT_REVERSE_LINK_SWEEP`.
- Cada proposta vira `InboxItem` tipo `apply_cross_link`.
- Aceitar = patch no `## Veja também` do guide alvo.

### D.5 — Import existente
- `livedocs init` detecta `<docs_dir>/guides/` populado → grava `guides_subdir`.
- Varre `<docs_dir>/<guides_subdir>/<domain>/<slug>.md`, lê front-matter,
  popula `state.toml` como `status: reviewed`, `facts: []`.
- `_index.md` parseado em busca do bloco "Próxima recomendação" → popula
  `state.next_recommendations`.

### D.6 — Atualização de `_index.md`
- `generate_guides` passa a atualizar/criar `_index.md` do domínio (adiciona
  guide na lista, reescreve bloco "Próxima recomendação" com a sugestão do agente).
- Quando agente cria domínio novo, escreve `_index.md` template.

### Estimativa: ~2–3 dias de trabalho compactado.

---

## Roadmap pós-Fase 1

### Fase 2 (depois de Fase 1)
- 2 dimensões adicionais de avaliação: `shape_and_size` (sugere split) + `style_consistency`.
- Inbox com snooze, filtro por severity, persistência avançada.
- Contradição cross-guides (compara facts confirmados entre guides).
- Glossário emergente (propõe termos novos pro `_meta/glossary.md`).
- Sugestão de guide-mãe (cluster de 3+ guides do mesmo domínio).
- Herança de facts (não pergunta o que já está em outro guide do domínio).

### Fase 3 (futuro)
- `livedocs reflect` — re-audit toda a base, popula inbox.
- Stale detection via git diff (`source_files` modificados) — ver seção "Refresh via git SHA" abaixo para o desenho detalhado.
- `livedocs regen <slug>` com diff incremental.
- Modo dream — cron noturno acumula propostas.
- Graphify integrado (sugere domínios não-documentados).
- Reverse-narrate (simula perguntas de cliente, detecta gaps).
- Comparação versionada (diff conceitual entre versões do guide).
- Histórico de evals em `_meta/<slug>.eval-<timestamp>.md`.
- Persona-toggle (`livedocs evaluate --as=customer-final`).

---

## Refresh via git SHA — manutenção contínua (proposto pelo Tagôre, mai/2026)

> **Posição:** Esta feature pertence à Fase 3 e só faz sentido quando o
> projeto entrou em "modo manutenção" (base coberta, maioria dos guides
> `reviewed`, foco passa a ser manter, não criar).

### Intuição central (Tagôre)

> "Marcar o commit do projeto, e quando rodar `livedocs update` (ou
> `refresh`), perguntar se desejo escanear todas as mudanças do repo desde
> a última atualização pra propor revisões nos guides afetados. Depois de
> ter isso manual, fica fácil promover pra rotina automática."

Os dois ganhos:
1. **Liga a doc viva ao código mecanicamente.** Cada commit que toca
   `source_files` de um guide vira um sinal "este guide pode estar stale".
2. **Manual antes de automático.** Validamos UX no fluxo humano antes de
   plugar em hook/cron. Mesma trilha de dbt, Sentry, PostHog.

### Por que NÃO é uma feature do MVP

- Pressupõe base ≥80% coberta. Sem isso, vira ruído: arquivos mudam mas
  nenhum guide mapeia eles, e o comando fica perguntando "documentar?"
  pra coisas que nem deveriam ter doc ainda.
- O comando precisa de granularidade per-guide do marker — implica
  mudar `InterviewState` adicionando `last_refresh_sha`.
- Edge cases: rebase, squash, force-push em master, merge commits sem
  diff próprio. Validar UX no manual é mais barato que descobrir em
  produção.

### Design proposto

**Marker per-guide:**
```toml
[interviews.pagamento-de-repasses]
slug = "pagamento-de-repasses"
# ...
last_refresh_sha = "a4f9b2c"     # commit em que source_files foram
                                  # vistos pela última vez sem diff
```

Workspace-level também pode existir (`state.last_refresh_sha`), mas a
granularidade per-guide é o que destrava UX rica como
`livedocs status` mostrando `🟡 stale (3 source files mudaram desde
a4f9b2c)`.

**Comando: `livedocs refresh`**

Preferência por "refresh" sobre "update" — "update" colide semanticamente
com `git update` / `npm update` (atualizar dependências).

Fluxo:

```
$ livedocs refresh

→ Detectando mudanças desde a4f9b2c (último refresh — 12 dias atrás)...
→ 47 arquivos mudaram. 8 deles tocam 3 guides existentes:

  🟡 pagamento-de-repasses (financeiro)
     expensePayoutService.ts (35 linhas alteradas)
     CommissionPaymentModal.vue (deletado!)
     + 1 outro

  🟡 parceiros-do-projeto (projetos)
     contractService.ts (62 linhas alteradas)

  ✓ ciclo-de-vida-do-contrato (contratos) — source_files intactos

→ 12 arquivos novos em packages/api/src/billing/ não tocam guide nenhum.
  Quer mapear pra um guide novo ou ignorar?

O que fazer?
  [1] Marcar todos os 🟡 como stale (pra livedocs status mostrar)
  [2] Regenerar pagamento-de-repasses (entrevista incremental — só F's afetados)
  [3] Ver o diff em detalhes
  [4] Apenas atualizar o marker (eu reviso por fora)
  [5] Sair
```

**Heurísticas de "afetou":**
- **mudou parcialmente** → marca `status: stale`, flag pra revisão
- **deletado** → blocker; o guide afirma algo sobre função/rota que
  sumiu, vai pra inbox como item crítico
- **arquivo novo** em pasta com source_files conhecidos → sugere adicionar
  ao guide do domínio correspondente

**Versão automática (depois do manual):**
- Cron noturno `livedocs refresh --quiet` popula inbox
- Git hook `post-merge` (opt-in via `livedocs hooks install`)
- Modo dream cobre o mesmo terreno com mais autonomia

### Perguntas em aberto

- **Granularidade do marker** — workspace + per-guide combinados, ou só per-guide? *Inclinação: per-guide, com derivação automática do workspace-level pra UI.*
- **Arquivos NOVOS não-mapeados** — ignorar silenciosamente ou perguntar? *Inclinação: perguntar apenas quando estão em pasta que já tem source_files de algum guide.*
- **Como o livedocs detecta "está em manutenção"?** — Possível: % domains não-documentados < 20% + maioria reviewed há mais de N dias. Mostrar em `livedocs status` como "Fase: construção / manutenção".
- **Escopo do diff** — repo inteiro ou só dirs que já têm source_files conhecidos? Importante em monorepo grande.

### Conexão com outras fases

- **Stale detection (Fase 3, já no roadmap)** — é o core mecânico deste fluxo. O `refresh` é a UI humana do mesmo motor.
- **`livedocs regen <slug>` com diff incremental (Fase 3)** — uma das opções no menu de `refresh` (item [2] no fluxo acima).
- **Modo dream (Fase 3)** — automatiza `refresh` em cron noturno.
- **Inbox (já implementada, Fase 1 D.3)** — `refresh` automático popula a inbox; o humano resolve quando quiser.

### Implementação estimada (quando virar prioridade)

- Adicionar `last_refresh_sha: str | None` em `InterviewState` (migração leve, default None)
- Novo módulo `livedocs/refresh.py` com `compute_diff_since(repo, sha) → list[(file, kind)]`
- `livedocs/commands/refresh.py` com a UX descrita
- Mapping `file → affected_guides` via `source_files`
- Testes unitários (parser do `git diff --name-status`) + integration (fluxo completo com mock)
- ~3-5 dias de trabalho

---



## Decisões já travadas

| Tópico | Decisão |
|---|---|
| Linguagem CLI | Python (uvx) |
| Provider v0 | Claude Code via subprocess (BYOA é v0.5) |
| UI | TUI Rich + Questionary; web local fica pra v1+ |
| Storage `.md` | `<repo>/<docs_dir>/`, configurável; default `docs/` |
| Estado | `<repo>/.livedocs/state.toml` (gitignored) |
| Idioma | pt-BR + en, auto-detect locale, init confirma |
| Licença | AGPL-3.0 |
| Inbox | comando separado + atalho no menu default |
| Pergunta | 1 por vez (não batch) |
| Iteração interna | até 3 ciclos antes de apresentar ao humano |
| Confidence | visível no front-matter + `livedocs status` |
| Vídeos | **fora do escopo até v3+** |
| Daemon | **fora do MVP** (modo manual on-demand) |
| Hooks git/Claude Code | **fora do MVP** (vem na Fase 3) |
| MCP local | **fora do MVP** (vem em v1) |
| Cloud | spec separada, não nesta fase |

---

## Como retomar a sessão

Se você (Tagôre) ou outro agente abrir este plano:

1. Ler **"Status — o que existe hoje"** (Phases A/B/C).
2. Ler **"Ajustes detectados pelo Tagôre"** se preenchido.
3. Próximo trabalho começa em **"Próxima sessão — Phase D"**.
4. Para detalhes do código atual: olhe `livedocs/commands/interview.py` e
   `livedocs/models.py`.
5. Histórico de commits: `git log --oneline` no repo.

---

## Histórico de commits desta fase

```
badcb44 feat(v0.2): post-gen audit + iteration + inbox + reverse-link (D.1-D.4)
acf8a3a feat(styles): 3 templates + style.md injetado em generate_guides (D.0)
eacbde1 chore: bump to 0.2.0a1 — adaptive fact-driven interview
3b0a467 feat(v0.2): adaptive fact-driven interview flow end-to-end (Phase C)
05f4e11 feat(skill): rewrite prompts for fact-driven flow + 5 new prompts (Phase B)
2c95528 feat(models): fact-driven schema (v2) + migration from v0.1 questions (Phase A)
```

## Status — atualizado após Phase D parcial (D.0-D.4 done) + Testes

✅ **D.0** — 3 style templates + .livedocs/style.md customizável
✅ **D.1** — Evaluator paralelo (3 dimensões em ThreadPool)
✅ **D.2** — Iteração interna pré-humano (até 3 ciclos com auto-fix)
✅ **D.3** — Inbox + comando `livedocs inbox` (accept/reject/snooze/view/quit)
✅ **D.4** — Reverse-link sweep após `livedocs approve`
✅ **Tier 1** — 116 unit tests (models, state, migration, parsers, helpers)
✅ **Tier 2** — 27 integration tests (interview flow, evaluator, iteration, inbox, reverse-link)
✅ **D.5** — Import de packages/docs/ legado (detect_guides_subdir + scan_existing_guides + init integrado, 30 testes)
✅ **D.6** — `_index.md` updates automáticos (geração + import + preservação de seções humanas, 15 testes)
⏸ **Tier 3** — E2E real com Claude Code (opcional pré-release)

Total: **143 tests, 0.6s suite, 52% coverage** (core modules 90-100%).
Comandos disponíveis: init / new / continue / status / review / approve / inbox / version.

