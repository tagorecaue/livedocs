# Plano A — `livedocs bootstrap` end-to-end

> Origem: sessão grill-with-docs 2026-05-21. Glossário em `CONTEXT.md`,
> decisão de plataforma em `docs/adr/0001-chatwoot-as-help-center.md`.
> Escopo deste plano: bootstrap de um SaaS do zero, sem Chatwoot
> (Plano B trata publicação e manutenção).

## Princípios

- Bootstrap é um comando único: `livedocs bootstrap`.
- Sete fases em sequência, com `--resume` retomando da última concluída.
- Nenhuma fase carrega "todos os guias" no prompt; contexto sempre bounded.
- Texto de orientação livre é colhido por input rico no início, nunca por flag.
- Quebra com v0.1: removemos `new`, `cont`, `interview`, `iteration`,
  `evaluator`. Eles deixam de existir.

## Comando-alvo

```
$ livedocs bootstrap [--resume] [--re-tax]
```

`--resume` retoma da última fase com marker em `bootstrap.toml`.
`--re-tax` força refazer a fase 2 (taxonomia) mantendo o scan.

## Estado persistido

Arquivo novo: `<repo>/.livedocs/bootstrap.toml` (gitignored). Modelo:

```toml
schema_version = 1
status = "drafting"           # scanning|deriving|seeding|drafting|stitching|refining|updating|done
last_completed_phase = 3
created_at = "2026-05-21T..."
updated_at = "..."

guidance_text = """..."""     # input livre coletado na fase 0

[scan]
graph_path = ".livedocs/cache/graph.json"
routes_path = ".livedocs/cache/routes.json"
i18n_path = ".livedocs/cache/i18n.json"
models_path = ".livedocs/cache/models.json"
scanned_at = "..."
commit_sha = "abc123..."        # ponto de captura — pré-requisito do Plano B

[taxonomy]
approved_at = "..."
capabilities = [
  { slug = "cobranca-recorrente", title = "Cobrança recorrente",
    code_anchors = ["src/billing/**", "src/jobs/charge.ts"] },
  ...
]
journeys = [
  { slug = "primeira-fatura", title = "Do cadastro até a primeira fatura",
    capability_refs = ["cobranca-recorrente", "onboarding-morador"] },
  ...
]

[[guides]]
slug = "cobranca-recorrente"
kind = "capability"
status = "drafted"            # pending|drafting|drafted|stitched|refined
draft_cost_usd = 0.12
stitch_cost_usd = 0.01
pending_questions = ["Q3", "Q7"]

[[pending_questions]]
id = "Q3"
guide_slug = "cobranca-recorrente"
question = "..."
provisional_answer = "..."
confidence = "low"
status = "open"               # open|merged_into:Qx|answered|dropped
answer = ""
```

## Modelos de dados (Pydantic em `livedocs/models.py`)

```python
class GuidanceText(BaseModel):
    text: str = ""
    captured_at: datetime

class CodeAnchor(BaseModel):
    glob: str

class Capability(BaseModel):
    slug: str
    title: str
    summary: str = ""
    code_anchors: list[str] = []

class Journey(BaseModel):
    slug: str
    title: str
    summary: str = ""
    capability_refs: list[str] = []

class Taxonomy(BaseModel):
    capabilities: list[Capability]
    journeys: list[Journey]
    approved_at: datetime | None = None

class PendingQuestion(BaseModel):
    id: str
    guide_slug: str
    question: str
    provisional_answer: str
    confidence: Literal["high", "low"]
    status: Literal["open", "answered", "dropped", "merged"] = "open"
    merged_into: str | None = None
    answer: str = ""

class GuideRecord(BaseModel):
    slug: str
    kind: Literal["capability", "journey"]
    status: Literal["pending", "drafting", "drafted", "stitched", "refined"]
    draft_cost_usd: float = 0.0
    stitch_cost_usd: float = 0.0
    pending_question_ids: list[str] = []

class BootstrapState(BaseModel):
    schema_version: int = 1
    status: Literal["scanning","deriving","seeding","drafting",
                    "stitching","refining","updating","done"]
    last_completed_phase: int = 0
    guidance: GuidanceText
    scan_paths: dict[str, str] = {}
    taxonomy: Taxonomy | None = None
    guides: list[GuideRecord] = []
    pending_questions: list[PendingQuestion] = []
    total_cost_usd: float = 0.0
```

## Estrutura de arquivos nova

```
livedocs/
├── commands/
│   ├── bootstrap.py          (NOVO — orquestrador)
│   └── root.py               (REVISTO — só oferece bootstrap)
├── bootstrap/
│   ├── __init__.py
│   ├── state.py              (load/save bootstrap.toml + markers)
│   ├── guidance.py           (Fase 0 — input rico multi-linha)
│   ├── scanner.py            (Fase 1 — graphify + rotas + i18n + models)
│   ├── taxonomy.py           (Fase 2 — propõe capacidades/jornadas)
│   ├── taxonomy_review.py    (Fase 3 — UI interativa de aprovação)
│   ├── pass1_drafts.py       (Fase 4 — rascunhos isolados)
│   ├── pass2_stitch.py       (Fase 5 — costura cross-guides)
│   ├── pending.py            (dedupe + persistência da fila)
│   ├── refinement.py         (Fase 6 — entrevista em lote)
│   └── global_update.py      (Fase 7 — rodada de ajuste)
├── prompts/                  (NOVO — templates de prompt extraídos)
│   ├── taxonomy_propose.md
│   ├── pass1_draft.md
│   ├── pass2_stitch.md
│   └── global_update.md
└── ... (mantidos: agent.py, state.py, ui.py, i18n.py, skill/)

REMOVIDOS:
- livedocs/commands/new.py
- livedocs/commands/cont.py
- livedocs/commands/interview.py
- livedocs/commands/approve.py        (será reintroduzido no Plano B)
- livedocs/commands/inbox.py          (substituído por refinement.py)
- livedocs/commands/refine.py
- livedocs/commands/reverse_link.py
- livedocs/iteration.py
- livedocs/evaluator.py
- livedocs/inbox.py
- livedocs/import_existing.py         (não há mais "guias importáveis"; é bootstrap)
- livedocs/index_md.py                (revisitar; provavelmente vira parte do scanner)
```

---

# Fases

## Fase 0 — Input de orientação (guidance)

**Arquivo**: `livedocs/bootstrap/guidance.py`

**Comportamento**: Antes da fase 1, exibe um painel com a copy:

```
LiveDocs vai documentar seu sistema. Antes de começar, conta um
pouco sobre o contexto:

  Me conta aqui quem você é, o que o sistema faz, para que serve.
  Você pode colar referências, instruções gerais ou qualquer coisa
  que ajude a IA durante o processo de documentação.

  (Vazio é ok — pressione Enter sem digitar.)

  [editor multi-linha; Ctrl-D ou Esc-Enter pra finalizar]
```

Usa `questionary.text(multiline=True)` OU `prompt_toolkit` direto com
keybindings claros. Detecta non-tty e aceita stdin pipe.

**Output**: `GuidanceText` salvo em `bootstrap.toml`. Vai como `system`
ou bloco `## Orientação do mantenedor` em todos os prompts subsequentes.

**Edge cases**:
- Texto vazio → guidance.text == "", prompts omitem o bloco.
- Texto > 4000 chars → aceita, mas alerta ("muito longo pode encher contexto").

---

## Fase 1 — Scan

**Arquivo**: `livedocs/bootstrap/scanner.py`

**Sub-passos**:

1. **Graphify** — `subprocess.run(["graphify", "scan", "--out", cache/graph.json, repo_root])`.
   Detecta ausência → instala via `pip install graphify` ou erra com instrução.
2. **Rotas frontend** — heurística por framework detectado (`package.json`):
   - Vue/Nuxt: parser de `pages/` ou `router.ts`.
   - React/Next: parser de `app/` ou `pages/`.
   - Genérico: regex de `path:` em arquivos `*.routes.*`.
   Output: `routes.json` = `[{path, file, name}, ...]`.
3. **i18n / labels de menu** — grep por `t("...")`/`i18n.t(...)` e leitura
   dos JSON de tradução em pastas comuns (`locales/`, `i18n/`, `lang/`).
   Output: `i18n.json` = `[{key, values_by_lang, files_using}, ...]`.
4. **Modelos de domínio** — detecta ORMs (Prisma schema, SQLAlchemy
   models, Sequelize models, TypeORM entities, Mongoose schemas).
   Output: `models.json` = `[{name, fields, file}, ...]`.

**Falhas tolerantes**: cada sub-passo pode falhar independentemente
(repo sem i18n, sem ORM, etc). O scanner reporta o que conseguiu;
fases seguintes lidam com sinais faltantes.

**Cache**: tudo em `.livedocs/cache/`. `--resume` reusa; sem isso,
recomputa.

**Custo**: zero IA. Tudo determinístico.

---

## Fase 2 — Taxonomia proposta

**Arquivo**: `livedocs/bootstrap/taxonomy.py`

**Prompt** (`prompts/taxonomy_propose.md`):

```
# Tarefa
Proponha uma taxonomia de guias de help center para este SaaS,
baseada nos sinais de código fornecidos.

# Orientação do mantenedor
{guidance.text if not empty else "(nenhuma)"}

# Sinais
## Rotas
{routes.json compactado}
## Labels de menu / i18n
{i18n.json filtrado por chaves de navegação}
## Modelos de domínio
{models.json}
## Grafo (resumo top-level)
{graph.json — clusters por pasta com contagens}

# O que entregar
JSON estrito:
{
  "capabilities": [
    {"slug": "...", "title": "...", "summary": "uma linha",
     "code_anchors": ["src/billing/**", ...]}
  ],
  "journeys": [
    {"slug": "...", "title": "...", "summary": "uma linha",
     "capability_refs": ["slug1", "slug2"]}
  ]
}

# Regras
- Capacidades: 10-25 itens. Cada uma = unidade de negócio reconhecível.
- Jornadas: 3-10 itens. Só crie se cross-cutting agregar valor.
- NÃO crie um guia por rota; rotas viram seções dentro de capacidades.
- Slugs em kebab-case, em pt-BR ou idioma configurado.
- Use o ORIENTAÇÃO DO MANTENEDOR pra desempatar nomes.
```

**Custo**: 1 chamada Claude. ~$0.30-1.00 dependendo do tamanho.

**Output**: `Taxonomy` salvo em `bootstrap.toml`.

---

## Fase 3 — Entrevista de seeding (revisão da taxonomia)

**Arquivo**: `livedocs/bootstrap/taxonomy_review.py`

**UI**:

```
Taxonomia proposta (18 capacidades, 4 jornadas):

CAPACIDADES
  1. cobranca-recorrente      "Cobrança recorrente"
  2. onboarding-morador       "Onboarding de morador"
  ...

JORNADAS
  J1. primeira-fatura         "Do cadastro até a primeira fatura"
  ...

Ações: [a]provar tudo  [r]enomear N  [m]esclar N+M  [x]remover N
       [+]adicionar    [e]ditar âncoras de N  [p]review .md  [q]sair
>
```

`[p]review` escreve `.livedocs/menu-proposed.md` com árvore + summaries +
âncoras de código pra o humano abrir no editor.

Ao aprovar (`a`), `taxonomy.approved_at` é setado. Marker da fase 3
escrito.

**Não-interativo**: `--accept-taxonomy` pula a UI. Útil pra CI.

---

## Fase 4 — Passada 1: rascunhos isolados

**Arquivo**: `livedocs/bootstrap/pass1_drafts.py`

**Loop**: pra cada capability + journey aprovada, em ordem (capabilities
primeiro, depois journeys que dependem delas):

1. Preparar contexto isolado:
   - guidance.text
   - registro daquele guia (slug, title, summary, code_anchors)
   - menu inteiro como ÍNDICE (só títulos + slugs, sem corpo)
   - extrato de código: arquivos casando com `code_anchors` (Read tool
     com whitelist — herda fix do issue #6)
   - estilo (`.livedocs/style.md`)

2. Prompt (`prompts/pass1_draft.md`):

```
# Tarefa
Escreva o RASCUNHO INICIAL do guia "{title}" ({kind}).

# Orientação do mantenedor
{guidance.text or "(nenhuma)"}

# Estilo
{style.md content}

# Menu completo do help center (índice apenas, sem corpo)
{menu_index}

# Código relevante para este guia
Leia os arquivos que casam com:
{code_anchors}

# Regras
- Você está num CONTEXTO ISOLADO. NÃO assume que outros guias
  existem com conteúdo X — só sabe os títulos do menu.
- Se você quiser referenciar outro guia, escreva
  `[TODO:link={slug}]` no lugar do link real. A passada 2 resolve.
- Se você encontrar algo que o código não revela (intenção de UX,
  porquê de uma regra de negócio, integração externa, conexão
  implícita), NÃO invente. Registre como pergunta pendente.
- Gere DOIS arquivos por guia:
    docs/{kind}/{slug}.md         (guia de produto, pt-BR)
    docs/{kind}/{slug}.tech.md    (guia técnico, mesmo idioma)
- Front-matter obrigatório nos dois (slug, title, kind, status="drafted",
  generated_at).

# Output (JSON estrito)
{
  "files_written": ["docs/.../slug.md", "docs/.../slug.tech.md"],
  "pending_questions": [
    {"question": "...", "provisional_answer": "...", "confidence": "low|high"}
  ]
}
```

3. Pós-call:
   - Verificar arquivos no disco (herda fix do issue #10).
   - Inserir perguntas pendentes via `pending.add(guide_slug, q, prov, conf)`,
     com IDs estáveis `Q{n}`.
   - Atualizar `GuideRecord.status = "drafted"`.
   - Marker incremental por guia (pra `--resume` granular).

**Custo**: 1 chamada por guia. ~22 chamadas num SaaS médio. ~$3-8 total.

**Falha de um guia**: marca `status = "pending"`, registra erro, continua
o loop. No fim, reporta os que falharam pra retry manual.

---

## Fase 5 — Passada 2: costura

**Arquivo**: `livedocs/bootstrap/pass2_stitch.py`

**Loop**: pra cada guia com `status = "drafted"`:

1. Contexto isolado, MUITO menor que passada 1:
   - O próprio guia (produto + técnico)
   - Índice dos outros guias = `[{slug, title, summary, first_paragraph}]`
     (NÃO o corpo inteiro)
   - Lista de placeholders `[TODO:link=...]` encontrados neste guia

2. Prompt (`prompts/pass2_stitch.md`):

```
# Tarefa
Costure este guia ao restante do help center.

# Este guia
{conteúdo md atual}

# Índice dos demais (título + resumo + primeiro parágrafo)
{index_others}

# O que fazer
1. Para cada `[TODO:link={slug}]`, substitua pelo link Markdown real
   se o slug existe no índice. Se não existe, transforme em pergunta
   pendente "Quis linkar X mas não achei guia correspondente".
2. Onde o texto menciona algo que CLARAMENTE corresponde a outro
   guia (mesmo sem TODO), proponha link inline.
3. Harmonize terminologia: se este guia usa "fatura" e o glossário
   inferido dos outros usa "cobrança", ajuste para o termo dominante
   no menu.
4. Sinalize contradições: se este guia afirma X mas outro guia
   afirma not-X, anote como pergunta pendente.
5. NÃO reescreva conteúdo conceitual. Mude o mínimo: links,
   termos, marcadores de contradição.

# Output (JSON estrito)
{
  "files_modified": [...],
  "links_added": N,
  "todos_resolved": N,
  "todos_unresolved": [...],
  "contradictions": [
    {"this_guide_says": "...", "other_guide": "slug", "other_says": "..."}
  ],
  "new_pending_questions": [...]
}
```

3. Pós-call:
   - Verificar arquivos.
   - Persistir contradições como `PendingQuestion` (categoria
     `contradiction`).
   - `GuideRecord.status = "stitched"`.

**Custo**: 1 chamada por guia, mas input pequeno (~$0.03-0.10 cada).

---

## Fase 6 — Entrevista de refinamento

**Arquivo**: `livedocs/bootstrap/refinement.py`

**Sub-passos**:

1. **Dedup IA** (uma chamada): manda toda a fila de `pending_questions`
   abertas pra Claude, pede pra agrupar perguntas equivalentes e
   reescrever versões canônicas.

   Prompt resumido:
   ```
   Você tem N perguntas pendentes. Para cada cluster equivalente,
   produza UMA pergunta canônica e marque as outras como
   merged_into=<canonical_id>. Retorne JSON com canonical_ids e
   mapeamento.
   ```

   Atualiza `pending_questions` com `status="merged"` e `merged_into`.

2. **UI interativa** (uma canonical por vez):

   ```
   Pergunta 3/14 (origem: guia "cobranca-recorrente")

   O agente perguntou:
     "Quando a fatura é gerada com 30 dias de antecedência, o cliente
      pode antecipar o pagamento e pegar desconto?"

   Suposição provisória no rascunho (confiança: baixa):
     "O cliente pode antecipar com 5% de desconto se pagar 10+ dias
      antes do vencimento."

   Outras perguntas que esta também responde:
     - Q7 (jornada primeira-fatura): "Existe desconto por pagamento
       antecipado?"

   Resposta: [editor multi-linha; Enter envia, Ctrl-C pula, /skip ignora]
   >
   ```

3. Após cada resposta:
   - Marca canonical como `answered`.
   - Marca merged_intos como `answered` (resposta propaga).
   - Re-roda dedup leve: a nova resposta torna outras perguntas
     obsoletas? Se sim, mostra "esta resposta também sana Q11 (...). OK?".

4. No fim, marker da fase 6 escrito.

**Pular fase**: `--skip-refinement` aceita rascunhos como estão.
Perguntas ficam abertas pra rodar depois com `livedocs refine`
(comando utilitário, fora do `bootstrap`).

---

## Fase 7 — Rodada global de ajuste

**Arquivo**: `livedocs/bootstrap/global_update.py`

**Sub-passos**:

1. Mapear quais guias têm perguntas respondidas: `affected_slugs`.
2. Pra cada guia afetado, contexto isolado:
   - O guia atual
   - Lista de Q&A relevantes (só as `answered` ligadas a este guia)
3. Prompt (`prompts/global_update.md`):
   ```
   Você escreveu este guia antes. Agora o mantenedor respondeu N
   perguntas pendentes. Atualize o guia incorporando as respostas.
   - Substitua suposições provisórias pelas respostas reais.
   - Remova [TODO:pergunta=...] que foram respondidos.
   - Se a resposta invalida um trecho, reescreva o trecho.
   - NÃO mude links e termos já harmonizados na passada 2 sem motivo.
   Retorne JSON com files_modified e changes_summary.
   ```
4. `GuideRecord.status = "refined"`.

**Custo**: 1 chamada por guia afetado (geralmente <50% dos guias).

**Marker final**: `status = "done"`. `livedocs bootstrap` daqui em
diante avisa "já rodou; use `livedocs maintain` (Plano B) ou
`livedocs regenerate <slug>` pra forçar".

---

# Testes

Estrutura mínima em `tests/`:

```
tests/
├── conftest.py                       (fixture tmp_repo com git init + arquivos fake)
├── fixtures/
│   ├── mini-saas/                    (repo fake: 5 rotas, 3 models, i18n simples)
│   ├── graph-sample.json
│   ├── routes-sample.json
│   └── claude-responses/             (mocks de AgentResult por fase)
│       ├── taxonomy.json
│       ├── pass1-cobranca.json
│       ├── pass2-cobranca.json
│       └── ...
├── unit/
│   ├── test_guidance.py
│   ├── test_scanner_routes.py
│   ├── test_scanner_i18n.py
│   ├── test_scanner_models.py
│   ├── test_taxonomy_prompt.py       (snapshot do prompt renderizado)
│   ├── test_taxonomy_review_actions.py
│   ├── test_pending_dedup.py
│   └── test_state_resume.py          (marker → carregar → continuar)
└── e2e/
    └── test_bootstrap_mini_saas.py   (mocka ClaudeAgent, roda 7 fases end-to-end)
```

Cobrir explicitamente:
- `--resume` retoma de cada uma das 7 fases corretamente
- guidance.text vazio não quebra prompts
- pergunta pendente respondida propaga pros `merged_into`
- arquivo não escrito por agente → guia marcado `pending`, não `drafted`
- whitelist de tools impede edição fora de `docs/`

---

# Ordem de implementação (sub-PRs, um plano = uma branch)

Por default, **1 PR único** com toda a fase. Mas o tamanho favorece
quebrar em 4 commits internos lógicos pra revisão. Decisão final do
usuário.

```
Commit 1 — Limpeza + scaffold
  - Remove new/cont/interview/iteration/evaluator/inbox/refine/
    reverse_link/approve/import_existing/index_md.
  - Adiciona livedocs/bootstrap/ com __init__ e state.py.
  - Adiciona livedocs/prompts/ vazio.
  - Atualiza commands/root.py pra só oferecer bootstrap.
  - Atualiza cli.py.
  - Atualiza ISSUES.md marcando #1, #2, #5, #7, #11 como obsoletos
    (substituídos pelo novo fluxo).
  - Testes: conftest + smoke do CLI.

Commit 2 — Fases 0-3 (input até taxonomia aprovada)
  - guidance.py, scanner.py, taxonomy.py, taxonomy_review.py.
  - prompts/taxonomy_propose.md.
  - Testes unitários de scanner + taxonomy_review.
  - E2E parcial: bootstrap até "Confirmar?" e --accept-taxonomy.

Commit 3 — Fases 4-5 (rascunhos + costura)
  - pass1_drafts.py, pass2_stitch.py, pending.py.
  - prompts/pass1_draft.md, pass2_stitch.md.
  - Whitelist de tools (Read/Glob/Grep/Write), git diff guard pós-call.
  - Testes: pass1 com mock gera 2 .md + perguntas pendentes;
            pass2 resolve TODOs.

Commit 4 — Fases 6-7 (refinamento + global)
  - refinement.py, global_update.py.
  - prompts/global_update.md.
  - UI da entrevista em lote.
  - Testes: dedup, propagação de resposta, status=done.
  - E2E completo no fixture mini-saas.
```

---

# Critério de aceite do plano (definition of done)

- `livedocs bootstrap` no fixture `tests/fixtures/mini-saas/` roda as
  7 fases com mocks e termina com `bootstrap.toml.status = "done"`.
- Dogfood real: rodar em `~/dev/<client>/main`, gerar a taxonomia,
  aprovar manualmente, deixar passar as 2 passadas, responder
  refinamento. Validar que os `.md` em `docs/` cobrem >80% das
  capacidades reconhecíveis do produto.
- Custo total no dogfood ≤ $15.
- `--resume` interrompendo no meio de qualquer fase retoma sem
  reprocessar trabalho.
- Nenhum arquivo fora de `docs/` modificado pelo agente.

---

# Riscos identificados e mitigações

| Risco | Mitigação |
|-------|-----------|
| Taxonomia ruim → todo o resto sofre | Fase 3 obrigatória + `--re-tax` |
| Stack frontend não detectada → routes vazio | Scanner reporta sinais ausentes; taxonomia ainda funciona com grafo+models |
| Custo explode em SaaS grande (>50 capacidades) | Limite duro: warning > 30 capacidades, exige confirmação |
| Pergunta pendente vira ruído | Dedup IA + categorização (`contradiction`, `intent`, `integration`) na UI |
| `bootstrap.toml` corrompido | Backup `.bak` antes de cada save; schema_version validado |
| Provider único (Claude) cai no meio | `--resume` granular por guia já cobre |

---

# Fora de escopo (vai pro Plano B)

- Publicar no Chatwoot
- Sincronizar do Chatwoot pra detectar edições humanas
- `livedocs maintain` baseado em diff de PR
- Diff de manutenção pro humano aprovar
