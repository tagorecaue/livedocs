# Article markdown format

Every article (.md and .tech.md) MUST have this structure.

## Front-matter

```yaml
---
slug: <cap-slug>/<article-slug>     # for capability articles
# or
slug: <journey-slug>                 # for journey articles
title: <Human readable title>
kind: capability                     # or "journey"
flavor: produto                      # or "tecnico"
status: drafted                      # drafted | stitched | refined
generated_at: "2026-05-21"
last_interview: ""                   # ISO date of last user answer affecting this guide
source_files:                        # added during phase 4, optional
  - src/projects/...
  - prisma/schema.prisma
related_guides:                      # added during phase 5
  - cobranca-recorrente/emissao-boletos
---
```

## Sections — product flavor (`.md`)

In this order, no skipping:

1. **# {title}** (h1)
2. **Por que isso existe** — why this capability/article matters to the user
3. **Como o usuário vivencia** — user-facing flow, what they see/click/feel
4. **Conceitos-chave** — domain terms with definitions
5. **Fluxos principais** — main flows (mermaid OK if non-trivial)
6. **Casos do dia a dia** — Q&A format: "E se eu...?"
7. **Convivência com vizinhos** — interactions with other capabilities
8. **Veja também** — cross-links to 3-5 related guides (PHASE 5 fills this)

**Zero technical jargon.** No column names, no function names, no
`UPPER_SNAKE_CASE`, no DB enum values (`before_tax`, `REURB_S`, etc.), no
route paths inline, no English terms when the product UI is in another
language. When a constant appears in code, find the user-visible label
(templates, `:items=`, `text:`, computed getters, formatters) and use THAT.
If the label can't be found, register a pending question — never leak the
raw constant. Self-check: would a non-technical user (gestor, operador,
morador) understand each sentence without opening the codebase? The voice
is the one from `.livedocs/style.md` (or default: "tutorial conversacional,
pt-BR, segunda pessoa").

Tech detail belongs in `.tech.md`, NOT here. That separation is the whole
point of the two flavors.

## Sections — technical flavor (`.tech.md`)

1. **# {title} (técnico)** (h1)
2. **Modelo de dados** — ORM models touched, key fields
3. **Pontos de entrada** — hooks, endpoints, services, routes with file:line
4. **Diagrama de transições** (if state machines involved) — mermaid
5. **Regras invariantes** — numbered (R1, R2, R3) with `file:line`
6. **UI / cores / selos** — only when visual design matters semantically
7. **Pendências e melhorias mapeadas** — 🟡 hypotheses, missing tests, refactor opportunities
8. **Material de referência** — links to repos, docs, ADRs
9. **Veja também** — cross-links to related tech guides (PHASE 5 fills this)

Use `file:line` or `file:line-line` citations liberally. Every numbered
invariant rule should cite its source.

## Mermaid usage

Allowed in both flavors but **sparingly**. Rule of thumb: include a diagram
ONLY when prose would take >2 paragraphs to explain what the diagram shows
in one glance.

Common mermaid types used:
- `flowchart` for workflows
- `stateDiagram-v2` for state machines
- `sequenceDiagram` for integrations / API calls
- `erDiagram` for data models (in tech flavor only)

## Pair rules

- `.md` and `.tech.md` MUST share the same slug.
- They live in the same directory.
- They NEVER link directly to each other. Knowledge crosses by structure,
  not by hyperlink.
- Cross-links go to OTHER guides of the SAME flavor.

## Tone

Product flavor:
- Second person ("você", "you").
- Patient teacher tone, no condescension.
- Light humor OK when natural.
- Anticipate confusion: "Se você ainda não tem certeza..."

Tech flavor:
- Third person, direct.
- Tables and bullets liberal.
- Code blocks with language tags.
- Numbered invariants are LAW — they must be backed by code.
