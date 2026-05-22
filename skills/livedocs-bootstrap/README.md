# livedocs-bootstrap

Generate **living documentation** for an existing SaaS codebase, driven
end-to-end by a capable coding agent (Claude Code, Codex CLI, Cursor,
Hermes, etc.). No binary, no Python runtime — just a folder of markdown
files the agent reads and follows.

The output is a `docs/` directory with paired guides:

```
docs/
├── <capabilities-dir>/         # capabilities/ (en), capacidades/ (pt-BR), …
│   ├── <capability-slug>/
│   │   ├── <article-slug>.md           ← product flavor (end-user)
│   │   └── <article-slug>.tech.md      ← technical flavor (devs)
└── <journeys-dir>/             # journeys/ (en), jornadas/ (pt-BR), …
    ├── <journey-slug>.md
    └── <journey-slug>.tech.md
```

Plus state, pending questions, and screenshot TODOs in `.livedocs/`.

## What makes it different

- **Two flavors per topic**: same domain knowledge, two audiences — end
  users (product `.md`) and devs/AI (`.tech.md`). They never link to
  each other; cross-links go to other same-flavor guides.
- **Agent-driven**: the skill is the agent's read-only manual. No CLI,
  no separate Python process. State lives in plain markdown the user
  can read and edit.
- **Pending-question discipline**: questions about INTENT or
  EXPERIENCE (the only kind a human can answer) get batched for a
  single interview at the end. Questions about EXISTENCE or VALUE go
  back to the code where they belong.
- **Code-first triage (Phase 5.5)**: a dedicated pass re-checks every
  pending question against the codebase. The ones the agent can
  resolve with literal evidence get answered automatically AND the
  affected article gets patched, so the human only sees what genuinely
  needs them.
- **Single source of truth, one language per run**: language locked in
  Phase 0, used everywhere downstream. Translation is a separate
  downstream operation, not a runtime concern.

## When to use it

- The user asks you to "document this project", "create a help
  center", "bootstrap docs", "generate documentation for this
  codebase", or similar.
- You're in a real SaaS / web app repo (Vue / React / Next / etc.)
  with code worth documenting.
- The user has `graphify` installed (recommended, not required —
  routes/i18n/models extractors still produce a usable taxonomy
  signal).

## When NOT to use it

- The user wants to read existing docs → just open them.
- Single ad-hoc README → write it directly, no ceremony needed.
- Codebase is tiny (<10 files) → overkill.

## Install

This folder is a complete skill. Drop it where your agent looks for
skills:

### Claude Code

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/skills/livedocs-bootstrap" ~/.claude/skills/livedocs-bootstrap
```

### Hermes

```bash
mkdir -p ~/.hermes/skills
ln -s "$PWD/skills/livedocs-bootstrap" ~/.hermes/skills/livedocs-bootstrap
```

### Codex CLI / Copilot CLI / OpenCode / etc.

Each has its own skills directory — check that agent's docs. The
structure is generic: `SKILL.md` at the top, `references/*.md` next to
it. Any agent that can read SKILL.md frontmatter and load referenced
files works.

## Quickstart

In the chat with your agent, after the skill is installed:

```
I want to document this project. Use the livedocs-bootstrap skill.
```

The agent takes over. It will:

1. **Phase 0** — detect the project's language, confirm with you, ask
   for free-form guidance about the product.
2. **Phase 1** — scan the codebase: routes, i18n keys, models, plus
   `graphify` if installed.
3. **Phase 2** — propose a help-center taxonomy (capabilities + journeys).
4. **Phase 3** — let you review, rename, merge, split.
5. **Phase 4** — draft each article in isolated context (1 sub-agent
   per article, parallelized).
6. **Phase 5** — stitch cross-links, harmonize terms, flag contradictions.
7. **Phase 5.5** — re-check pending questions against code, patch
   articles that were written without the answer, filter the
   interview to only what genuinely needs you.
8. **Phase 6** — refinement interview in thematic blocks (A: meaning,
   B: transitions, C: invariants, D: UX/support, E: code edges, F:
   meta-direction).
9. **Phase 7** — rewrite the affected articles with your answers.

Each phase pauses for your consent before advancing. State persists in
`.livedocs/state.md`; you can interrupt and resume any time.

## Cost expectations

Driven by the agent's LLM provider. Observed in real runs (large
~38k-node codebase, 80+ articles):

- Phase 4 draft: **$0.30–$1.00 per article** (3× variance with
  capability size).
- Phase 5 stitch: **$0.50–$3.00 per capability**.
- Phase 5.5 triage: **$0.20–$1.50 per capability**.
- Phase 6 dedup + interview: **$0.50–$2 dedup, ~$0.05 per Q in chat**.
- Phase 7 rewrite: **$0.30–$0.80 per affected article**.

Real cost gets recorded in `.livedocs/state.md` as you go. Don't
promise users a fixed estimate — measure with your own project first.

## Languages

The skill itself is in English (it's the agent's read-only manual).
The OUTPUT — chat messages, interview content, generated guides —
runs in whatever language Phase 0 locks in. Tested in pt-BR and en.
Adding new languages is a matter of letting Phase 0 detect/confirm
them — no skill changes needed.

See [`references/language-handling.md`](references/language-handling.md)
for the full rule.

## Privacy

The skill applies a hard denylist before sending any code to a
sub-agent: `.env*`, `secrets/`, `*.pem`/`*.key`, `.aws/`, `.ssh/`,
anything in `.gitignore`, anything in `.git/`. Phase 0 includes a
one-time heads-up that guidance text WILL appear in later LLM calls
so the user can self-redact before saving.

Full policy: [`references/privacy.md`](references/privacy.md).

## Structure of this skill

```
skills/livedocs-bootstrap/
├── SKILL.md                              # entry point, core principles
├── README.md                             # this file
├── CHANGELOG.md                          # version history
└── references/
    ├── language-handling.md              # i18n contract — READ FIRST
    ├── privacy.md                        # context boundaries
    ├── article-format.md                 # markdown structure (front-matter, sections, tone)
    ├── state-format.md                   # what .livedocs/state.md looks like
    ├── pending-questions.md              # heuristic for what NOT to ask
    ├── screenshot-todos.md               # admonition format + rules
    ├── phase-0-guidance.md
    ├── phase-1-scan.md
    ├── phase-2-taxonomy.md
    ├── phase-3-review.md
    ├── phase-4-pass1-drafts.md
    ├── phase-5-pass2-stitching.md
    ├── phase-5.5-triage.md
    ├── phase-6-refinement.md
    └── phase-7-global-update.md
```

SKILL.md is always loaded. Phase references are loaded on entry to
each phase. Format references (language-handling, privacy, article,
state, pending, screenshot) are loaded on demand from any phase.

## Customization

- **Style**: drop a `.livedocs/style.md` in the project to override
  the default voice ("conversational tutorial, second person, in
  `{lang}`, no jargon in product `.md`").
- **Language**: detected from i18n keys / comments / README in Phase
  0; user confirms or overrides with a BCP-47 code (`pt-BR`, `en`,
  `es-AR`, etc.).
- **Style + guidance + language all live in `.livedocs/`** — version
  them in your repo if you want runs to be reproducible.

## Known limitations

- **No publication** — generates local markdown only. Pushing to
  Chatwoot / other help centers is a follow-up skill, not yet built.
- **No incremental maintenance** — bootstrap is one-shot. Re-running
  the skill on the same project starts a new full run rather than
  diffing against the last one. Maintenance mode is planned.
- **Cost variability across LLMs** — the skill doesn't pin a model.
  Sonnet-class models produce noticeably better drafts than smaller
  ones; the skill's quality follows the agent's quality.
- **`is_intro` heuristic** — Phase 4 decides whether a capability
  needs an overview article. On small capabilities it sometimes still
  generates one; you can remove via Phase 3 before Phase 4 starts.

## Versioning

Each article carries a `skill_version` in its front-matter. When the
skill bumps, future maintenance can detect "this article was generated
by an older skill, conventions may have changed" and offer a re-pass.
See [`CHANGELOG.md`](CHANGELOG.md).

## License

AGPL-3.0-or-later (matches the parent LiveDocs project).

## Contributing

Not open to external contributions yet — the skill is in validation
through dogfooding in real projects. When ready, this note disappears.
File issues with reproductions; PRs may be accepted later.
