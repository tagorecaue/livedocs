# Phase 3 — Taxonomy Review

## Goal
Let the user edit the proposed taxonomy until they're happy with it. This is
conversational — you propose, they react, you patch the JSON.

## What to do

1. **Show the current state** of `.livedocs/taxonomy.json` as a menu:

   ```
   Taxonomia atual — 18 capacidades, 5 jornadas

   CAPACIDADES
     1. cobranca-recorrente   (1 artigo)
     2. onboarding-morador    (1 artigo)
     ...

   JORNADAS
     J1. primeira-fatura
     ...

   Ações disponíveis:
     [i] inspecionar capacidade N — mostra rotas, models, arquivos da capacidade
     [s] split capacidade N — IA propõe N artigos (custo ~$0.05)
     [A] gerenciar artigos da capacidade N — editar manualmente
     [r] renomear capacidade N
     [m] mesclar capacidades N+M
     [x] remover capacidade N
     [+] adicionar capacidade
     [J] gerenciar jornadas (analogamente)
     [a] aprovar e avançar pra Phase 4
     [q] sair (salva estado)

   O que você quer fazer?
   ```

2. **Wait for user choice.** Execute the action and re-render the menu.
   Loop until user picks `[a]` or `[q]`.

### Action: inspect (`[i]`)

Filter routes/models from the cache by the capability's `code_anchors`:

```
gestao-projetos — "Gestão de Projetos de REURB"
  code_anchors:
    - src/projects/** (87 arquivos)
    - src/views/Projects/** (23 arquivos)
  Rotas dentro:
    /projects                    (lista/kanban)
    /projects/new
    /projects/:id
    /projects/:id/financial
    /projects/:id/team
  Models tocados: Project, ProjectMember, ProjectConfig, ProjectStage
```

Zero LLM. Pure filtering.

### Action: split (`[s]`)

This IS an LLM call. Estimate cost: ~$0.05 per split. Confirm before running.

Prompt:
> Para a capacidade "gestao-projetos" cujos anchors são `src/projects/**`,
> proponha 2-7 articles que representem sub-áreas/sub-fluxos dentro dela.
>
> Rotas dentro: <filtered routes>
> Models tocados: <filtered models>
> Guidance: <user guidance>
>
> Cada article: slug kebab-case, title, summary (1 linha), is_intro
> (exatamente 0 ou 1 com true). code_anchors do artigo devem ser refinamento
> dos anchors da capability pai.
>
> Output JSON estrito: {"articles": [{...}]}

Show the proposal, sub-menu:
```
[a]ceitar  [r]enomear N  [+]adicionar  [x]remover N  [c]ancelar
```

If accepted, replace `capability.articles` with the new list. Save.

### Action: manage articles (`[A]`)

Sub-loop. Zero LLM. Renomear / remover (manter ≥1) / adicionar / mover âncoras / toggle is_intro / voltar.

### Action: rename / merge / remove / add

Straightforward edits to `.livedocs/taxonomy.json`. After each edit, re-render
the top menu.

When merging A into B:
- Concatenate code_anchors (dedup)
- Concatenate articles (rename conflicts: `<slug>-from-B`)
- Update journey refs that mentioned A → now mention B

### Action: approve (`[a]`)

Set `approved_at` to current ISO timestamp in `.livedocs/taxonomy.json`.
Update state.md to mark phase 3 done.

Show summary:
```
✓ Taxonomia aprovada: 22 capacidades, 5 jornadas
Total de artigos a gerar na Phase 4: 67

Custo estimado da Phase 4 (passada 1):
  - ~$0.30 por artigo × 67 = $20 (variação ~$10-30)
  - Pode rodar em lotes — veja menu da Phase 4
```

Ask consent to advance to Phase 4.

## Pitfalls

- **User goes back and forth a lot**: that's fine. Just keep saving after each
  edit. Don't pressure them.
- **User splits 18 capabilities to 60+ articles**: warn about cost.
- **User wants to delete a journey referenced by capabilities**: just remove,
  capabilities don't reference journeys.
- **Slug collisions**: when adding/renaming, check for duplicates within the
  same capability. Reject with helpful message.
