# LiveDocs v0 — spec final

> Implementação: `~/dev/livedocs/livedocs/`
>
> Objetivo: dogfood Tagôre na <Client>. CLI Python (uvx) que conduz
> entrevistas e gera guias `.md` produto+tech pareados, **com Claude Code
> como agente único no v0**.

## Decisões finais (travadas)

- **A1** Python (uvx)
- **B (custom)** Provider único = Claude Code subprocess. Skill embutida
  no system prompt. Outros providers viram BYOA na v0.5.
- **C3** TUI (Rich + Questionary). Web UI fica fora do v0.
- **D3** `<repo>/docs/` configurável; reaproveita `packages/docs/` se já existir.
- **E (simplificado)** Estado em `<repo>/.livedocs/state.toml` (gitignored
  via `<repo>/.livedocs/.gitignore`). Sem `~/.livedocs/<slug>/` no v0 — fica
  pra v0.5 quando workspace multi-repo entrar.
- **F1** AGPL-3.0
- **G1** macOS + Linux (Windows não testado, deve funcionar em WSL)
- **i18n** pt-BR + en, auto-detecta locale, confirma no init

## Comandos

| Comando | Função |
|---------|--------|
| `livedocs` (sem args) | Splash + "onde paramos?" + menu inteligente |
| `livedocs init` | Wizard de setup (idioma, slug, docs_dir, graphify) |
| `livedocs new [slug]` | Começa entrevista nova (escolhe domínio interativo) |
| `livedocs continue [slug]` | Retoma entrevista em andamento |
| `livedocs status` | Tabela de todos os guias e estado |
| `livedocs review` | Valida front-matter + coerência básica |
| `livedocs version` | Versão |

## Layout no repo do dev

```
<repo>/
  .livedocs/
    config.toml              # idioma, slug, docs_dir, provider
    state.toml               # entrevistas em andamento (gitignored)
    .gitignore               # local: state.toml + .bak
  docs/                      # (ou packages/docs/, configurável)
    <domínio>/
      <slug>.md              # guia produto
      <slug>.tech.md         # guia técnico
      _meta/
        <slug>.interview.md  # registro Q&A
```

## Fluxo de entrevista (UX)

1. `livedocs new pagamento-de-repasses`
2. Pergunta domínio (lista existentes + "novo")
3. Spinner: "agente lendo código e preparando perguntas" (~30s, ~$0.10)
4. Entrevista em loop:
   - Mostra bloco + pergunta + sub-prompt
   - User responde (multiline, Ctrl-D pra finalizar)
   - Tokens: `/sair`, `/skip`, vazio = pular
   - Após resposta: spinner curto pra checar coverage
   - Se cobriu outras → pergunta confirmação inline
   - **State salvo a cada resposta** (Ctrl-C é seguro)
5. Quando todas respondidas: spinner "gerando guia v1"
6. Agente escreve os 3 arquivos via tools
7. Sucesso: lista arquivos criados + cost

## Resumo Custo/Tempo (estimado)

- Init: $0
- Prepare (start_new_interview): ~$0.10, ~30s
- Cada coverage check: ~$0.01-0.02
- Geração final: ~$0.30-0.50
- **Total por guia**: ~$0.50-1.00 + 10-30min de tempo do dev

## Deltas vs lacunas-cli.md (decisões pragmáticas tomadas)

- **B5/B6**: docs_dir default `docs/`, mas se detectar `packages/docs/` ou
  `documentation/` ou `site/docs/` com .md já existentes, oferece
  importar/usar/outro/fresh.
- **B7**: project_slug derivado do nome do dir (sugestão), user pode mudar.
  Sem hash de remote — simples e suficiente no v0.
- **B8**: terminologia = "projeto + domínio + guide" (alinhado skill).
- **P1**: uma pergunta por vez (TUI questionário interativo).
- **P2**: contradição = acumula como pergunta no flow + revalida coverage.
  Análise pós-entrevista de contradição com código fica pra v0.5.
- **P4**: UM ato (entrevista única gera produto + tech).
- **P8**: nada no v0 (git do dev resolve).
- **P9**: sem detecção de staleness no v0.

## Out of scope v0 (próximas versões)

- v0.5: graphify integrado, modo "documentação completa inicial",
  scan/regen para detectar staleness, providers extras (Codex, Hermes).
- v1: Dashboard web local + MCP server local.
- v2: Cloud free tier (helpcenter público).
- v3: Plano pago (custom domain, video, analytics).

## Aceitação Tagôre (dogfood <Client>)

1. `cd ~/dev/<client>/main && uvx livedocs init` detecta `packages/docs/`
   e oferece reaproveitar.
2. `livedocs new <slug-do-próximo>` começa entrevista, gera ~20 perguntas em
   pt-BR, conduz Q&A.
3. Ao final, gera `.md` produto + tech + interview no formato esperado.
4. Resultado é equivalente em qualidade ao guia gerado manualmente via skill.
5. Tempo total ≤ tempo do fluxo manual + 20%.
