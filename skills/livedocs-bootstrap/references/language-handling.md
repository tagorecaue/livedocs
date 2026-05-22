# Language handling

> **Single source of truth for the language convention used by this skill.**

## The two layers

There are two distinct layers, and they live in different languages:

| Layer | Language | Examples |
|---|---|---|
| **Skill internals** (read by the agent) | **Always English** | SKILL.md, all `references/*.md`, sub-agent prompts you compose, JSON keys, Q IDs, code identifiers, file paths |
| **Run output** (read by the user / produced for them) | `{lang}` from Phase 0 | Chat messages, generated `.md` + `.tech.md`, interview file content, the VALUES inside JSON fields, slugs |

The skill itself is the agent's manual. Like a cookbook written in
English instructing the chef to greet guests in French — the recipe
text is English, the greeting is French.

## The rule, restated

This skill runs in ONE output language per bootstrap run, chosen by the
user in Phase 0. That language is used for:

1. **Skill messages to the user** — chat prompts, transitions, consent
   asks, summaries, error messages.
2. **The refinement interview** — block files, questions (the text, not
   the IDs), headers, meta-prompts.
3. **The generated documentation** — both `.md` (product) and `.tech.md`
   (technical) flavors. Identifiers, file:line refs, JSON keys stay
   as-is.

We deliberately do NOT support multi-language mixing within a single
run. Translation is a downstream operation, not a runtime concern.

## How the language is decided

In Phase 0, the agent:

1. **Detects** a candidate by looking at i18n keys, comments density,
   README, package metadata. Suggests the candidate.
2. **Asks** the user to confirm or override.
3. **Persists** in `.livedocs/state.md` as `**Lang:** <code>` (BCP-47
   form: `pt-BR`, `en`, `es-AR`, etc.).

After Phase 0, no later phase ever asks again. If the user wants to
change language mid-run, they edit `state.md` manually and re-invoke
the skill — but that's effectively a re-bootstrap.

## How sub-agents use the language

Every sub-agent prompt MUST receive `{lang}` as an explicit variable and
include this instruction:

> All user-visible prose you produce — drafts, summaries, interview
> questions, JSON `canonical_question` values, screenshot descriptions —
> MUST be in {lang}. Code identifiers, file paths, JSON keys (not values),
> and technical constants stay as-is.

The prompt template ITSELF stays in English. Only what the user
eventually reads is in `{lang}`.

## Detail: JSON keys vs values

Sub-agents return JSON like this:

```json
{
  "canonical_question": "Quem dispara a transição de active → finished?",
  "canonical_origin": "contratos/ciclo-de-vida",
  "merged_ids": ["Q7", "Q11"]
}
```

- Keys (`canonical_question`, `merged_ids`) — English. They are skill
  contracts.
- The VALUE of `canonical_question` — `{lang}`. It's what the user
  will read in the interview.
- `canonical_origin` — slug, language of the slug (see below).
- `merged_ids` — opaque IDs, unchanged.

## What "user-visible prose" means in each phase

| Phase | User-visible prose (in `{lang}`) | Stays as-is (English / opaque) |
|---|---|---|
| 0 | Greeting, language confirmation, guidance prompt | — |
| 2 | Capability/article titles, summaries, **slugs** | Internal IDs |
| 3 | Confirmation messages, split prompts | Slugs |
| 4 | Article body (both flavors), pending question text | file:line refs, code identifiers, JSON keys |
| 5 | Stitching summary, contradiction reports | TODO link markers, JSON keys |
| 5.5 | Triage report to user, proposed_diff descriptions | Code snippets in evidence |
| 6 | Interview file headers, block titles, question text, instructions | Q IDs, JSON keys |
| 7 | Rewrite summary | — |

## Top-level docs directories

The two top-level directories under `docs/` are named in `{lang}`:

| `{lang}` | capabilities dir | journeys dir |
|---|---|---|
| en | `capabilities/` | `journeys/` |
| pt-BR | `capacidades/` | `jornadas/` |
| es-* | `capacidades/` | `recorridos/` |
| fr-* | `capacites/` | `parcours/` |

When references talk about `docs/<capabilities-dir>/...` or
`docs/<journeys-dir>/...`, the sub-agent resolves the placeholder
from `{lang}`. The full path lives in state so later phases can rely
on it.

Slugs INSIDE those dirs are also in `{lang}` (see slug rules above).

## Slugs are special

Slugs (article paths like `gestao-projetos/criar-projeto`) are
**chosen in `{lang}` during Phase 2**, then stay as-is for the
lifetime of the project. They appear in URLs, file paths, and
cross-references — translating them later would break links.

The taxonomy sub-agent receives `{lang}` and is instructed to produce
slugs in that language, using kebab-case + ASCII fold:

- pt-BR: `cobrança-recorrente` → `cobranca-recorrente`
- es-AR: `gestión-de-proyectos` → `gestion-de-proyectos`
- en: `recurring-billing` → `recurring-billing`

## User answers — preserved verbatim

When the user answers an interview question, the response is stored
**exactly as written**, including language. If the user answers in
`{lang}` (the normal case), great. If they answer in a different
language for some reason — accept it, store it, don't translate.

If a future run resumes with a different `Lang:` (rare; counts as
re-bootstrap), prior answers stay in their original language. The
skill does not retroactively translate. Coherent with the principle
that translation is a separate downstream operation.

## Migration note

Earlier versions of this skill had pt-BR strings hardcoded in
`SKILL.md` and reference files. v1.1+ replaces all of those with
English instructions + `{lang}` placeholders. If you see a hardcoded
non-English phrase in a reference file or in the skill itself, it is
a bug — patch it.

## Future: translation pass

NOT in scope today. When/if implemented, it will live as a separate
post-bootstrap phase that takes finished `docs/` + `state.md` and
produces a parallel `docs-{target-lang}/` tree. Single source of truth
stays in `{lang}`.
