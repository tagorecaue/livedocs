# Notas operacionais

Coisas que vale saber depois que você decidiu usar a skill. Mantém
carregado durante o primeiro run; depois você não precisa da maior
parte disso.

## Saída

```
docs/
├── <capabilities-dir>/         # capabilities/ (en), capacidades/ (pt-BR), …
│   ├── <capability-slug>/
│   │   ├── <article-slug>.md           ← flavor de produto (usuário final)
│   │   └── <article-slug>.tech.md      ← flavor técnico (devs)
└── <journeys-dir>/             # journeys/ (en), jornadas/ (pt-BR), …
    ├── <journey-slug>.md
    └── <journey-slug>.tech.md
```

Mais state, pending questions e screenshot TODOs em `.livedocs/`.

Cada artigo carrega `skill_version` no front-matter, então um run
futuro de manutenção consegue detectar saída produzida por uma versão
antiga da skill e oferecer um re-pass. Veja o
[CHANGELOG](../../skills/livedocs-bootstrap/CHANGELOG.md).

## Faixas de custo

Direcionado pelo provedor de LLM do seu agente. Observado em runs
reais:

- Phase 4 (draft): **US$ 0,30–1,00 por artigo** (variância de 3× com
  o tamanho da capability)
- Phase 5 (stitch): **US$ 0,50–3,00 por capability**
- Phase 5.5 (triage): **US$ 0,20–1,50 por capability**
- Phase 6 (dedup + entrevista): ~US$ 0,50–2 no dedup; ~US$ 0,05 por
  Q no chat
- Phase 7 (rewrite): **US$ 0,30–0,80 por artigo afetado**

O custo real é gravado em `.livedocs/state.md`. Não prometa um valor
fixo para o usuário — meça com o seu próprio projeto primeiro.

## Idioma

A skill em si é em inglês (é o manual read-only do agente). A SAÍDA —
mensagens de chat, conteúdo da entrevista, guides gerados — roda no
idioma que a Phase 0 fixar. Testado em pt-BR e en.

Regra completa: [`references/language-handling.md`](../../skills/livedocs-bootstrap/references/language-handling.md).

## Privacidade

Uma denylist hard filtra paths antes que qualquer sub-agente leia
código: `.env*`, `secrets/`, `*.pem`/`*.key`, `.aws/`, `.ssh/`,
qualquer coisa em `.gitignore`, qualquer coisa em `.git/`. A Phase 0
avisa o usuário uma vez de que o texto de guidance vai aparecer em
chamadas LLM posteriores, antes de salvar.

Política completa: [`references/privacy.md`](../../skills/livedocs-bootstrap/references/privacy.md).

## Customização

- **Estilo**: jogue um `.livedocs/style.md` no projeto para
  sobrescrever a voz default.
- **Idioma**: a Phase 0 detecta a partir de chaves i18n / comentários /
  README; o usuário confirma ou sobrescreve com um código BCP-47.
- Estilo + guidance + idioma vivem todos em `.livedocs/` — versione
  esses arquivos no seu repo se quer que os runs sejam reproduzíveis.

## Limitações conhecidas

- **Sem publicação** — gera markdown local só. Subir para Chatwoot
  ou outros help centers está planejado, não implementado.
- **Sem manutenção incremental** — o bootstrap é one-shot hoje.
  Re-rodar começa um run novo do zero em vez de fazer diff contra o
  anterior. Modo de manutenção está planejado.
- **Variabilidade de custo entre LLMs** — modelos da classe Sonnet
  e Opus produzem drafts visivelmente melhores que modelos menores;
  a qualidade da skill segue a qualidade do agente.
- **Heurística do `is_intro`** — a Phase 4 às vezes gera um artigo
  de visão geral para capabilities pequenas que não precisam. Você
  pode remover via Phase 3 antes da Phase 4 começar.
