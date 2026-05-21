# Lacunas — LiveDocs OSS-first (CLI livre + Cloud paid)

> Pivô novo: CLI open-source na máquina do dev (free) + SaaS hospedado
> de publicação/MCP (paid). Modelo dbt/Sentry/PostHog.
>
> Preencha em pt-BR. Linhas curtas. Pode pular respondendo `—`.
> Não precisa responder na ordem. Quando terminar, manda
> "lacunas preenchidas" e eu redijo `spec.md` de uma vez.

---

## 0) Confirmação do entendimento (1 frase pra cada)

▸ **CLI**: open-source, instala na máquina do dev, roda graphify +
  orquestra entrevista usando o agente que ele já tem
  (Claude Code / Codex / Hermes / Cursor / Ollama). Saída: `.md` locais.
- [X] confirma
- [ ] ajusta: _______________

▸ **Cloud (paid)**: hospeda os `.md` como helpcenter público (free com
  limites), oferece editor web colaborativo, e expõe MCP server (paid).
- [X] confirma
- [ ] ajusta: _______________

▸ **Cloud (free tier)**: texto + prints + helpcenter público com
  limites de bandwidth/páginas. Sem MCP, sem video, sem custom domain.
- [X] confirma
- [ ] ajusta: _______________

▸ **Privacidade**: código, grafo, embeddings, prompts NUNCA saem da
  máquina do dev. Cloud só recebe `.md` + assets que ele explicitamente
  publicou.
- [X] confirma
- [ ] ajusta: _______________

---

## 1) Decision bundle — CLI

### A — Linguagem/runtime da CLI
- [X] **A1** Python (graphify já é Python — chamada nativa, `pip install livedocs` ou `uvx`).
- [ ] **A2** Node/TS (mesma stack do hosted, npm install -g, mas precisa shellar pro graphify).
- [ ] **A3** Go (single binary `brew install livedocs`, mais rápido pra começar, shella tudo).
- [ ] **A4** Rust (overkill no MVP, melhor cancelar).
- Outra: _______________

### B — Estratégia BYOA (bring your own agent)
- [ ] **B1** Detecta CLIs já instaladas (`claude`, `codex`, `hermes`, `gemini`, `ollama`) — usa qualquer uma via shell out + protocolo de arquivos (input prompt em arquivo, output em outro). Sem adapter customizado.
- [ ] **B2** Suporta as 3 mais usadas no v0 (escolhe quais: ___ ___ ___) com adapter próprio; resto fica pra v1.
- [ ] **B3** Direct API calls (OpenAI/Anthropic) com user dando key — sem CLI agent, mais simples mas dev paga tokens.
- [ ] **B4** Híbrido: B3 como default + B1 como override avançado.
- Outra: Eu gostaria de um protocolo de setup similar ao Hermes agent ou com o Paperclip (orquestrador de agentes), ambos permitem escolher a fonte.

### C — UI da entrevista no v0
- [ ] **C1** TUI puro (uma pergunta por vez, prompt natural, libs estilo `prompts`/`enquirer`/`ink`).
- [ ] **C2** Web UI local (CLI sobe `http://localhost:7777`, abre browser).
- [X] **C3** TUI no v0; Web UI local no v1.
- [ ] **C4** TUI batch (mostra bloco A/B/C inteiro de uma vez, igual `.interview.md` hoje, dev edita no editor preferido).
- Outra: _______________

### D — Onde a CLI guarda os `.md`
- [ ] **D1** Dentro do repo do dev (`<repo>/docs/` ou `<repo>/.livedocs/docs/`). Versionamento = git dele.
- [ ] **D2** Fora do repo, em `~/.livedocs/<project-slug>/docs/`. Sem poluir git do projeto.
- [X] **D3** Configurável: default D1 (`docs/`), flag `--out` muda.
- Outra: _______________

### E — Estado da CLI (grafo, embeddings, histórico)
- [ ] **E1** Tudo em `<repo>/.livedocs/` (gitignore'd) — versão pareada com `docs/`.
- [ ] **E2** Tudo em `~/.livedocs/<project-slug>/state/` — separado completamente do repo.
- [X] **E3** Misto: `docs/` no repo (D1), `state/` em `~/.livedocs/` (E2).
- Outra: _______________

### F — Licença
- [X] **F1** AGPL-3.0 (force qualquer fork/SaaS hospedado em cima a abrir código).
- [ ] **F2** MIT (máxima adoção, mas perde leverage — AWS pode forkar).
- [ ] **F3** Apache 2.0 (meio termo, com NOTICE de attribution).
- [ ] **F4** BSL/Elastic License (não-pode-revender, vira open-core de verdade).
- Outra: _______________

### G — OS suportados no v0
- [X] **G1** macOS + Linux apenas. Windows = WSL, sem suporte oficial.
- [ ] **G2** macOS + Linux + Windows nativo.
- [ ] **G3** Linux only no v0 (você dogfooda em Linux).
- Outra: _______________

---

## 2) Decision bundle — Cloud hospedado

### H — Repo strategy
- [X] **H1** 1 repo OSS (`livedocs-cli`) público + 1 repo privado (`livedocs-cloud`). Trabalhar nos dois separadamente.
- [ ] **H2** Monorepo único, parte pública via GitHub workflow `package extract`, parte privada em branch separada (frágil).
- [ ] **H3** 2 repos OSS (`livedocs-cli` + `livedocs-cloud`) ambos públicos, mas cloud com BSL (não-revender).
- Outra: _______________

### I — O que vai no plano FREE do hospedado
Marca todos que devem ser free:
- [X] **I1** Helpcenter público em subdomínio `<ws>.livedocs.app` com texto + prints
- [X] **I2** Editor web (TipTap-like) dos `.md` publicados
- [X] **I3** Limite de N docs publicados (define N: 50)
- [X] **I4** Limite de M GB/mês de bandwidth (define M: 1)
- [X] **I5** Branding "Powered by LiveDocs" no helpcenter
- [ ] **I6** Sem analytics
- [ ] **I7** Custom domain
- Outra: _______________

### J — O que vai no plano PAID
Marca todos que devem ser paid:
- [X] **J1** MCP server hospedado (cliente final usa)
- [X] **J2** Custom domain
- [X] **J3** Remover branding "Powered by LiveDocs"
- [X] **J4** Upload/streaming de vídeo (tutorial em tela)
- [X] **J5** Analytics do widget (quais perguntas viraram lead)
- [X] **J6** Edição colaborativa multi-user com lock/conflito
- [X] **J7** Bandwidth aumentado / docs ilimitados
- [ ] **J8** Self-hosted enterprise (instala teu cloud no AWS/GCP deles)
- Outra: _______________

### K — Pricing inicial (chute educado)
- Free: __________
- Starter (paid básico): $99/mês com ___
- Pro: $199/mês com ___
- Enterprise: custom

### L — Login do hospedado
- [ ] **L1** Google OAuth apenas.
- [ ] **L2** GitHub OAuth (mais alinhado com público dev).
- [X] **L3** Os dois.
- Outra: _______________

### M — Sync CLI → Cloud
- [X] **M1** Push manual: `livedocs publish` empacota e sobe.
- [ ] **M2** GitHub App: dev autoriza, push no repo dele aciona sync automático no Cloud.
- [ ] **M3** Os dois (manual no v0, GitHub App no v1).
- Outra: _______________

---

## 3) Tensões binárias

### T1 — MCP local (free) vs MCP hospedado (paid)
- [ ] **(a)** MCP **local** (rodando junto da CLI free) é grátis — qualquer dev usa Claude Code/Cursor com docs locais.
- [ ] **(b)** MCP **hospedado** (HTTPS público, multi-user, com auth) é paid.
- [ ] **Ambos como acima** (a free + b paid). É a direção mais óbvia, mas confirme.
- Outra: _______________

### T2 — Multi-codebase por workspace
- [ ] **MVP suporta 1 repo por workspace** (cliente com backend + UI separados precisa criar 2 workspaces).
- [ ] **MVP suporta N repos** (config aponta vários paths).
- Outra: _______________

### T3 — Hosting de prints/imagens
- [ ] **(a)** Imagens ficam **no repo do dev** (`<repo>/docs/assets/<slug>.png`). CLI publica = upload pro Cloud.
- [ ] **(b)** Imagens ficam **só no Cloud** após publicar (upload via UI de edição web).
- [ ] **(c)** Os dois — repo é canônico, Cloud espelha.
- Outra: _______________

### T4 — Edição: CLI vs Cloud editor
Cliente edita `.md` via:
- [ ] **(a)** Apenas pelo editor preferido dele (VS Code etc.) + git push do repo dele.
- [ ] **(b)** Apenas pelo editor web do Cloud (paid feature).
- [ ] **(c)** Ambos — Cloud editor abre PR no repo dele (GitHub App), ou puxa diff manual.
- Outra: _______________

### T5 — Re-scan / detecção de mudança no código
- [ ] **(a)** CLI roda `livedocs scan` quando dev quiser.
- [ ] **(b)** Hook de git (post-commit) na CLI.
- [ ] **(c)** GitHub App (Cloud detecta push, dispara webhook na CLI do dev — complicado).
- [ ] **(d)** (a) + (b) — manual + hook opcional.
- Outra: _______________

---

## 4) Perguntas P1-P10 (atualizadas pro novo modelo)

### P1 — Forma da entrevista
Modelo padrão: blocos A/B/C/D no terminal, dev responde 1 pergunta por vez OU bloco inteiro?
- [ ] uma por vez (TUI questionário interativo)
- [ ] bloco inteiro (gera `.interview.md`, dev edita no editor preferido, CLI lê)
- [ ] dev escolhe (`--mode interactive | batch`)
- Outra: _______________

### P2 — Reconciliação contradição/erro
Quando agente detecta contradição:
- [ ] (a) interrompe entrevista e mostra inline
- [ ] (b) acumula em fila, mostra no final
- [ ] (c) ambos (configurável)
> _______________

### P3 — Primeira sugestão de fluxo após scan
Agente propõe N domínios. Dev pode:
- [ ] adicionar domínio que agente não sugeriu
- [ ] descartar/ignorar sugestão
- [ ] reordenar prioridade
- [ ] tudo isso
- Outra: _______________

### P4 — Dois flavors em UM ato ou DOIS atos?
- [ ] (a) UM ato: entrevista única gera `.md` produto + `.tech.md` (mantém comportamento atual da skill).
- [ ] (b) DOIS atos: entrevista 1 = produto, entrevista 2 = tech. Mais lento mas separa cabeça.
> _______________

### P5 — i18n do hospedado
- [ ] pt-BR + en no MVP
- [ ] pt-BR apenas (en vira backlog)
- [ ] en apenas (mira ICP global, não Brasil)
> _______________

### P6 — Auth do MCP local
Cliente conecta Cursor/Claude Code no MCP local da CLI:
- [ ] (a) sem auth — `localhost` confia no SO
- [ ] (b) token gerado pela CLI no setup
> _______________

### P7 — Auth do MCP hospedado (paid)
- [ ] (a) API key por workspace
- [ ] (b) Device flow OAuth
- [ ] (c) self-hosted (cliente instala MCP server na infra dele)
- [ ] (d) (a) + (c) opcional para enterprise
> _______________

### P8 — Versionamento dos `.md` na CLI
- [ ] (a) nada — git do dev resolve
- [ ] (b) snapshot em `<repo>/.livedocs/snapshots/` antes de cada save (paranoia)
- [ ] (c) histórico de chamadas do agente em `<repo>/.livedocs/history/` (não diff de `.md`, mas log de "agente disse X em Y data")
- [ ] (d) (a) + (c)
> _______________

### P9 — Print de tela: como detectar staleness?
- [ ] (a) Manual — dev marca print como "precisa atualizar"
- [ ] (b) IA infere: rota X / componente Y mudou no código → marca todos os prints com tag X
- [ ] (c) Hash da imagem + comparação visual (overkill v0)
- [ ] (d) (a) + (b)
> _______________

### P10 — Dogfood na <Client>
- [ ] (a) `~/dev/<client>/main` é o primeiro repo conectado, `<repo>/docs/` recebe os `.md` (substituindo `packages/docs/` atual após migração).
- [ ] (b) Fica em paralelo: `packages/docs/` legado vivo + `~/.livedocs/<client>/` novo, comparar.
- [ ] (c) Migrar `packages/docs/` atual pra dentro do novo CLI rodando — usar como teste de import.
> _______________

---

## 5) Estratégia de lançamento e marketing

### Q1 — Quando lançar OSS no GitHub?
- [ ] (a) Dia 1 — repo público desde o primeiro commit
- [ ] (b) Após dogfood completo da <Client> (~4 semanas)
- [ ] (c) Após hosted starter funcionar (~10 semanas)
> _______________

### Q2 — Primeiro post de divulgação
- [ ] HackerNews
- [ ] X / Twitter dev community
- [ ] LinkedIn
- [ ] Show HN + dev.to + r/programming combo
- [ ] Nada — viral via GitHub stars naturais
> _______________

### Q3 — Métricas de tração que justificam construir o paid (gating de quando começar Cloud)
- ___ GitHub stars
- ___ npm/pip downloads/mês
- ___ devs com projeto ativo (heurística)
- ___ pedidos de "como hospedar?" no issues

---

## 6) Notas livres / mudanças de decisão / coisas que esqueci de perguntar

> _______________
