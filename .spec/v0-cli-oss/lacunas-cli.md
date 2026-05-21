# Lacunas — LiveDocs CLI v0 (foco: dogfood <Client>)

> Foco exclusivo: **transformar a skill `living-docs-from-graph` num CLI dogfoodável na <Client>**.
> Cloud, MCP hospedado, paid: specs separadas futuras (vide `lacunas.md` macro).
>
> Decisões já confirmadas em `lacunas.md`:
> - A1 Python (uvx)
> - C3 TUI v0 → Web v1
> - D3 default `docs/` configurável
> - E3 state em `~/.livedocs/<slug>/`
> - F1 AGPL-3.0
> - G1 macOS + Linux
>
> Aqui ficam as lacunas QUE FALTAM pra travar spec do CLI v0. Pode pular qualquer
> item respondendo `—`. Notas livres no fim.

---

## 1) Provider system (formaliza o "Hermes/Paperclip-like" do B)

Hermes tem `providers` plugáveis (`anthropic`, `openrouter`, `custom:<name>`). Paperclip orquestra agentes via subprocess. LiveDocs precisa de algo análogo pra escolher QUAL agente faz a entrevista/análise.

### B1 — Modo de comunicação com o agente
A skill atual usa o agente pra (a) ler arquivos do repo, (b) escrever `.md` curado, (c) dialogar pra refinar respostas, (d) detectar contradições no código. Pro v0:
- [ ] **(a) Single round-trip**: livedocs gera prompt em arquivo, agente roda 1x e escreve resposta em outro arquivo. Sem state. Repetir N vezes.
- [ ] **(b) Long session**: livedocs sobe agente como subprocess persistent, conversa via stdin/stdout. Mantém memória da sessão.
- [ ] **(c) Dual-mode**: agentes session-aware (Claude Code, Hermes, Codex) usam (b); APIs simples (Ollama, OpenAI direct) usam (a).
- Outra: _______________

### B2 — Lista de providers no v0 (em ordem de prioridade)
Marca os 3 que MAIS te importam ter no dia 1 (resto fica pra v1):
- [ ] Claude Code (`claude` CLI)
- [ ] Codex CLI (`codex`)
- [ ] Hermes (`hermes`)
- [ ] OpenAI direct (env `OPENAI_API_KEY`)
- [ ] Anthropic direct (env `ANTHROPIC_API_KEY`)
- [ ] Ollama (HTTP local)
- [ ] OpenCode (`opencode`)
- [ ] Cursor agent CLI
- [ ] Gemini CLI (`gemini`)

### B3 — Onde mora o config do provider?
- [ ] **(a) Global**: `~/.livedocs/config.toml` define provider default; pode override por projeto.
- [ ] **(b) Por projeto**: `<repo>/.livedocs/config.toml`; nada global.
- [ ] **(c) Os dois**: global = default; projeto = override.
> _______________

### B4 — Provider configurado não está instalado/acessível
- [ ] **(a)** CLI sai com erro + link pra docs de setup.
- [ ] **(b)** CLI propõe trocar pra outro provider detectado.
- [ ] **(c)** CLI tem fallback built-in (qual? Anthropic via key? OpenAI?).
- Outra: _______________

---

## 2) Estrutura de arquivos no repo (refina D3 / E3)

### B5 — Nome do diretório default no repo
- [ ] **(a)** `docs/` (genérico, igual Mintlify; **colide com `packages/docs/` da <Client> se rodar na raiz**)
- [ ] **(b)** `livedocs/` (não colide, marca presença visual)
- [ ] **(c)** `.livedocs/docs/` (escondido, não polui visual do repo)
- [ ] **(d)** `living-docs/` (auto-explicativo, mais verboso)
- [ ] **(e)** Detecta convenção: usa `docs/` se vazio, senão pergunta no init
> _______________

### B6 — Comportamento se o diretório default já existe (caso real <Client>: `packages/docs/`)
- [ ] **(a)** Aborta e pede `--out` explícito.
- [ ] **(b)** Pergunta no welcome wizard "import existente? merge? renomear?".
- [ ] **(c)** Auto-detecta: se contém `.md` com front-matter livedocs-compatível, vira "import" e usa esses como existing guides; senão aborta.
> _______________

### B7 — Como derivar `<project-slug>` pra `~/.livedocs/<slug>/`?
Identificador estável do projeto (mesmo se dev renomeou diretório, mudou de máquina):
- [ ] **(a)** SHA256(git remote origin url) — falha se sem remote
- [ ] **(b)** Hash do path absoluto do repo — quebra se renomear pasta
- [ ] **(c)** UUID gerado no `init` e guardado em `<repo>/.livedocs/project.toml`
- [ ] **(d)** User escolhe slug no `init` (default = nome do dir)
> _______________

---

## 3) Conceitos de primeira classe na CLI

### B8 — Terminologia: "unidade de trabalho"
Skill atual usa "domínio" (`contratos/`, `projetos/`). Cloud futuro usará "workspace". CLI v0:
- [ ] **(a)** Projeto = repo. Domínio = subdivisão dentro do projeto. **(alinhado com skill)**
- [ ] **(b)** Workspace = projeto inteiro. Categoria = subdivisão. **(alinhado com Cloud futuro)**
- [ ] **(c)** Sem hierarquia: tudo é "guide" e tem `domain` no front-matter. **(simples)**
> _______________

### B9 — Comandos top-level no v0
Marca os que devem existir:
- [ ] `livedocs init` — wizard de setup, config provider, gera `.livedocs/`
- [ ] `livedocs scan` — roda graphify, atualiza grafo
- [ ] `livedocs domains` — lista domínios candidatos extraídos do grafo
- [ ] `livedocs interview <slug>` — inicia/retoma entrevista de um guide
- [ ] `livedocs status` — mostra guides em draft/reviewed/stale
- [ ] `livedocs regen <slug>` — re-roda análise quando código mudou
- [ ] `livedocs diff <slug>` — mostra o que mudou no source_files desde último review
- [ ] `livedocs validate` — verifica links quebrados, front-matter inválido
- [ ] `livedocs config` — mostra/edita config global e por projeto
- [ ] `livedocs import <path>` — importa `packages/docs/` existente
- Outros: _______________

---

## 4) Skill `living-docs-from-graph` — embedded ou Hermes-only?

A skill canônica mora em `~/.hermes/skills/software-development/living-docs-from-graph/` e é versionada em `packages/docs/skills/` da <Client>. CLI precisa do conhecimento dela.

### B10 — Como o conhecimento da skill chega ao CLI?
- [ ] **(a) Embedded**: copia conteúdo da skill como prompts/templates internos do CLI. CLI é self-contained. Funciona com qualquer provider.
- [ ] **(b) Hermes-only**: CLI só funciona com provider Hermes (que carrega skill auto). Outros providers caem fora.
- [ ] **(c) Híbrido**: skill embutida; quando provider é Hermes, **passa nome da skill como param** ao Hermes pra ele usar a versão dele; outros providers recebem conteúdo embedded.
> _______________

### B11 — Quem mantém a skill quando ela é embedded?
- [ ] **(a)** CLI vira fonte canônica (`livedocs/skill_content/`). Hermes/<Client> copiam de lá.
- [ ] **(b)** Skill canônica continua em `packages/docs/skills/` <Client>. CLI tem cópia que precisa sync manual.
- [ ] **(c)** Skill canônica em `~/.hermes/`. Build do CLI roda script de bundle no release.
> _______________

---

## 5) Fluxo `livedocs init` — primeiro contato

### B12 — Welcome wizard: que perguntas fazer? (ordena ou marca)
- [ ] Provider preferido (lista detectada + "outro")
- [ ] Idioma dos `.md` (default pt-BR? configurável?)
- [ ] Diretório de saída (`docs/` ou outro — vide B5)
- [ ] Slug do projeto (sugestão = nome do dir)
- [ ] Roda `scan` (graphify) agora ou depois?
- [ ] Importar `packages/docs/` existente da <Client>? (caso especial)
- Outros: _______________

### B13 — Idioma dos guides (pt-BR vs configurável)
- [ ] **(a) pt-BR fixo no v0** (Tagôre é o usuário, <Client> é cliente, simplifica)
- [ ] **(b) Configurável (`--lang`)** com pt-BR e en disponíveis no v0
- [ ] **(c) Detecta do código** (comentários/docstrings em pt? assume pt; senão en)
> _______________

### B14 — Idioma das mensagens da CLI / TUI
- [ ] pt-BR fixo no v0
- [ ] en fixo no v0 (mira global desde dia 1)
- [ ] Auto-detect locale do SO
> _______________

---

## 6) Migração do `packages/docs/` atual da <Client> (P10 redux)

Hoje a <Client> tem 4 guides funcionais:
- `contratos/ciclo-de-vida.md` + `.tech.md`
- `projetos/configuracoes-financeiras.md` + `.tech.md`
- `projetos/parceiros-do-projeto.md` + `.tech.md`
- `articles/cadastro-cliente/index.md` (formato antigo, não pareado)

### B15 — Como o livedocs lida com esse acervo no init da <Client>?
- [ ] **(a) Importa direto**: lê front-matter, valida shape, marca como `status: reviewed`. Continua trabalho onde parou.
- [ ] **(b) Reseta**: descarta acervo, começa do zero. **Ruim** — perde contexto e horas de entrevista.
- [ ] **(c) Coexistência**: livedocs roda em `docs/` novo; `packages/docs/` legado fica intacto até validação.
- [ ] **(d) Migração assistida**: comando `livedocs import packages/docs/` move + valida + relata gaps.
> _______________

### B16 — `articles/cadastro-cliente/` (formato antigo, não pareado)
- [ ] **(a)** Ignora — formato diferente, fica fora.
- [ ] **(b)** Migra pra novo formato (gera `produto+tech` pareados na importação).
- [ ] **(c)** Trata como categoria especial "tutoriais" no v0.
> _______________

---

## 7) P1-P10 do arquivo original (CLI-relevantes que faltam)

### P1 — Forma da entrevista no TUI
- [ ] **(a)** uma por vez (questionário interativo TUI)
- [ ] **(b)** bloco inteiro (gera `.interview.md`, dev edita no editor preferido, CLI lê)
- [ ] **(c)** dev escolhe (`--mode interactive | batch`)
> _______________

### P2 — Contradição/erro detectada pelo agente durante a entrevista
- [ ] (a) interrompe entrevista e mostra inline
- [ ] (b) acumula em fila, mostra no final (passo 4c da skill — análise pós-entrevista)
- [ ] (c) ambos (configurável)
> _______________

### P3 — Sugestão de domínios após scan
Dev pode:
- [ ] adicionar domínio que agente não sugeriu
- [ ] descartar/ignorar sugestão
- [ ] reordenar prioridade
- [ ] tudo isso
> _______________

### P4 — Dois flavors em UM ato ou DOIS atos?
- [ ] **(a)** UM ato: entrevista única gera `produto.md` + `.tech.md` (mantém skill atual).
- [ ] **(b)** DOIS atos: entrevista 1 = produto, entrevista 2 = tech. Mais lento mas separa cabeça.
> _______________

### P8 — Versionamento dos `.md` na CLI
- [ ] (a) nada — git do dev resolve
- [ ] (b) snapshot em `<repo>/.livedocs/snapshots/` antes de cada save (paranoia)
- [ ] (c) histórico de chamadas do agente em `<repo>/.livedocs/history/` (log de "agente disse X em Y data")
- [ ] (d) (a) + (c)
> _______________

### P9 — Print de tela no v0 (sem cloud)
v0 = `.png` mora em `<repo>/docs/<dominio>/assets/`. Como tratar staleness?
- [ ] **(a) Manual** — dev marca print como "precisa atualizar" via `livedocs mark-stale <slug> <asset>`
- [ ] **(b) IA infere** via mudança no `source_files` vinculado ao guide
- [ ] **(c) Ignorar staleness no v0** — print é só arquivo, dev resolve quando notar
> _______________

### T2 — Multi-codebase no v0
<Client> é monorepo (1 path). Mas alguns clientes têm backend + UI separados.
- [ ] **(a) MVP só 1 repo por config** (multi-repo cria projetos separados via cd em cada um)
- [ ] **(b) MVP suporta config aponta vários paths** (`paths = ["~/dev/foo/api", "~/dev/foo/web"]`)
> _______________

### T5 — Re-scan / detecção de mudança no código no v0
- [ ] **(a)** CLI roda `livedocs scan` quando dev quiser (manual)
- [ ] **(b)** Hook git post-commit (CLI instala se dev autoriza)
- [ ] **(c)** Watcher daemon (`livedocs watch`)
- [ ] **(d)** (a) + (b) opcional
> _______________

---

## 8) Estratégia de release v0 (mini)

### Q1 — Quando o repo OSS vira público?
- [ ] **(a)** Dia 1 — repo público desde primeiro commit (sem barulho, mas indexável)
- [ ] **(b)** Após dogfood completo da <Client> (4-6 semanas, lança com 5 guides já gerados pelo CLI)
- [ ] **(c)** Após v1 (helpcenter público funcional)
> _______________

---

## 9) Notas livres / mudanças de decisão / coisas que esqueci

> _______________
