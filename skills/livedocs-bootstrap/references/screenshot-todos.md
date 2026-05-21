# Screenshot TODOs

## Why
The agent can't take screenshots. But it CAN identify the moments where a
screenshot would help the reader, and structure the TODO so a human can
quickly capture them later.

## Format inside the .md (product flavor only)

Inserted immediately AFTER the paragraph mentioning the screen, in an
admonition block:

```markdown
Para começar, acesse o **Pipeline de pré-projetos** (`/pre-projects`).
Ali você consegue ver todos os projetos em andamento, organizados em
colunas como "Negociação", "Aprovado", "Em implantação".

> [!TODO:screenshot]
> Rota: `/pre-projects`
> Descrição: Vista do quadro Kanban completo, com pelo menos 3 colunas
> e 5+ cards distribuídos para ilustrar o uso normal.
```

## Format in state.md

Each TODO is also registered in state for programmatic listing:

```markdown
## Screenshot TODOs (open: 12)

- [open] `gestao-projetos/visao-geral.md` — `/projects` — "Kanban view"
- [open] `gestao-projetos/criar-projeto.md` — `/projects/new` — "Wizard step 1"
```

## Rules

1. **One screenshot, one TODO.** If a paragraph references 3 screens, write
   3 TODOs. Don't bundle.

2. **Concrete routes only.** If the agent doesn't have a concrete path
   (e.g., "vá em configurações"), DON'T write a TODO. The route field
   would be hand-wavy and useless.

3. **`.md` only, never `.tech.md`.** Product guides need screenshots;
   tech guides have file:line references instead.

4. **Description guides the capturer.** Don't write "tela do dashboard" —
   write "Dashboard logo após login, com pelo menos 1 projeto cadastrado
   e 3 tarefas pendentes". The more context, the better the screenshot.

5. **Status field stays simple:** `open` (default) | `captured` | `dropped`.
   Captured = human attached image. Dropped = route no longer relevant.

## When the user captures (future)

The user has two options to mark a TODO as captured:

a) Edit `.livedocs/state.md` directly, change `[open]` to `[captured]`.
b) Save the image at `.livedocs/screenshots/<cap-slug>/<article-slug>__<num>.png`
   and re-invoke the skill — it scans the dir, matches by article, marks
   captured automatically.

(Option b not implemented in v1 — manual marking only.)

## Anti-pattern

DON'T write:
```markdown
> [!TODO:screenshot]
> Rota: (a página de configuração)
> Descrição: (uma tela bonita do produto)
```

That's noise. Either you have a concrete route → write it precisely; OR
you don't → omit the TODO entirely.
