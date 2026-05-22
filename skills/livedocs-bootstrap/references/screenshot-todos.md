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

2. **Be GENEROUS.** Product guides should have many screenshots — every UI
   surface mentioned in prose is a candidate. The rule of thumb is
   "1 screenshot every 2-4 paragraphs" in the operational sections.
   When in doubt, write the TODO. A reviewer can drop it later; a missing
   one is invisible.

   Specifically, ALWAYS write a TODO when the prose mentions:
   - a concrete route (`/path`)
   - a sidebar, panel, drawer, modal, dialog, or tab
   - a button or action with a name (e.g. "botão Salvar splits")
   - a list, grid, kanban column, or chart
   - an empty state, success state, or error state worth showing
   - a step inside a wizard or multi-step flow
   - a settings section reachable from a named menu item

3. **Identify the surface as precisely as you can.** A route is best, but a
   named surface inside a route is also fine. Use the `Local:` field for
   non-route surfaces:

   ```markdown
   > [!TODO:screenshot]
   > Local: barra lateral do projeto → seção "Parceiros e splits"
   > Rota base: `/project/:project`
   > Descrição: <what this surface shows>
   ```

   Only OMIT the TODO when you genuinely don't know where the surface lives
   (e.g. "em algum lugar das configurações" with no anchor at all). In that
   case, register a pending question instead asking the user where it is.

4. **`.md` only, never `.tech.md`.** Product guides need screenshots;
   tech guides have file:line references instead.

5. **Description guides the capturer.** Don't write "tela do dashboard" —
   write "Dashboard logo após login, com pelo menos 1 projeto cadastrado
   e 3 tarefas pendentes". The more context, the better the screenshot.

6. **Status field stays simple:** `open` (default) | `captured` | `dropped`.
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
