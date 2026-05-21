# LiveDocs Bootstrap — Skill standalone

Skill plug-and-play que orquestra todo o fluxo de bootstrap de documentação
do LiveDocs **dentro de um chat com qualquer LLM com acesso a ferramentas de
arquivo + terminal** (Claude Code, Codex, Hermes, etc.).

Diferente do CLI Python `livedocs bootstrap`, aqui o agente é o orquestrador.
Sem TOML estruturado, sem binário pra instalar — só uma pasta de markdowns
que descreve cada fase e o agente conduz a conversa.

## Pra que serve

Documentar um SaaS já existente do zero (ou preencher lacunas). Gera:

```
docs/
├── capacidades/
│   ├── <cap-slug>/
│   │   ├── <article-slug>.md       (produto)
│   │   └── <article-slug>.tech.md  (técnico)
└── jornadas/
    ├── <slug>.md
    └── <slug>.tech.md
```

Tudo dirigido por 7 fases conversacionais, com state legível em `.livedocs/state.md`.

## Instalação

Esta pasta é uma skill completa. Pra usar:

### Claude Code

```bash
# se você usa o gerenciador de skills da Anthropic:
mkdir -p ~/.claude/skills
cp -r ./skills/livedocs-bootstrap ~/.claude/skills/

# ou linka:
ln -s "$PWD/skills/livedocs-bootstrap" ~/.claude/skills/livedocs-bootstrap
```

### Hermes (Tagôre)

```bash
mkdir -p ~/.hermes/skills
ln -s "$PWD/skills/livedocs-bootstrap" ~/.hermes/skills/livedocs-bootstrap
```

### Codex / Copilot CLI / OpenCode / etc

Cada uma tem seu próprio diretório de skills. Veja a documentação do agente.
A estrutura é genérica — SKILL.md no nível raiz + `references/*.md`.

## Pra começar

No chat com a LLM, depois de instalar a skill:

```
Quero documentar este projeto. Use a skill livedocs-bootstrap.
```

A skill assume daí. Vai pedir guidance, rodar scan, propor taxonomia, etc.

## Diferenças do CLI Python

| | CLI (`livedocs bootstrap`) | Skill standalone |
|---|---|---|
| Orquestrador | Código Python | Agente LLM |
| State | TOML estruturado (`.livedocs/bootstrap.toml`) | Markdown legível (`.livedocs/state.md`) |
| Sub-agentes | Não usa | **Sim** — delega braçal pra child agents |
| Custo Claude | Centralizado nas calls | Pode variar conforme orquestração do agente |
| Edição manual de state | Frágil (TOML) | Fácil (Markdown) |
| Dependências | Python 3.11+, typer, pydantic, etc | Nenhuma — só LLM com tools |

A skill é especialmente boa quando:
- Você já tem um agente LLM com bom suporte a sub-tasks (Claude Code,
  Codex CLI moderno) e quer aproveitar a paralelização.
- Quer editar state à mão.
- Não quer instalar Python nem dependências.

O CLI é melhor quando:
- Você quer CI / scripts (modo non-interactive).
- Quer custos previsíveis (cada call no CLI tem prompt fixo).
- Quer reproduzibilidade total entre runs.

Ambos produzem o mesmo formato final em `docs/`.

## Estrutura desta skill

```
skills/livedocs-bootstrap/
├── SKILL.md                              # entrada, princípios, fluxo geral
└── references/
    ├── phase-0-guidance.md
    ├── phase-1-scan.md
    ├── phase-2-taxonomy.md
    ├── phase-3-review.md
    ├── phase-4-pass1-drafts.md
    ├── phase-5-pass2-stitching.md
    ├── phase-6-refinement.md
    ├── phase-7-global-update.md
    ├── article-format.md
    ├── state-format.md
    ├── screenshot-todos.md
    └── pending-questions.md
```

12 arquivos. SKILL.md carrega o panorama; cada `phase-N.md` é carregada
quando a fase entra em execução; os 4 arquivos de formato são carregados
conforme necessário durante qualquer fase.

## Customização

- **Style** — coloque `.livedocs/style.md` no projeto pra customizar a
  voz dos guides. Sem ele, o agente usa um default ("tutorial conversacional,
  pt-BR, segunda pessoa"). Exemplos no diretório `livedocs/skill/styles/`
  do repo CLI (narrative, reference, tutorial).
- **Idioma** — a skill detecta pt-BR/en pela guidance. Pra forçar:
  escreva "Use English" / "Use pt-BR" na guidance.

## Limitações conhecidas

- **Não publica no Chatwoot** — geração local apenas. Publicação é Plano B
  do livedocs (futuro).
- **Não detecta mudanças de código** — bootstrap one-shot. Manutenção
  contínua (re-rodar quando código mudar) é Plano B.
- **Custos podem variar muito** entre LLMs — Sonnet caro mas detalhista,
  Haiku barato mas raso. A skill não força modelo; usa o que o agente
  tiver disponível.
