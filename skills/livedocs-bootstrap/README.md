# livedocs-bootstrap (the skill)

This folder IS the skill. The agent's read-only manual lives in
[`SKILL.md`](SKILL.md); the per-phase and per-format references live
under [`references/`](references/).

For everything else — what the skill does, install instructions, real
run example, costs, concepts, requirements, contributing — see the
**[repository README](../../README.md)** at the root of this repo.

## Quick map

- [`SKILL.md`](SKILL.md) — entry point, 13 core principles, phase
  table, batch sizing
- [`CHANGELOG.md`](CHANGELOG.md) — version history
- [`references/language-handling.md`](references/language-handling.md) — i18n contract (read first if you change anything user-facing)
- [`references/privacy.md`](references/privacy.md) — what enters and what NEVER enters a sub-agent's context
- [`references/pending-questions.md`](references/pending-questions.md) — heuristic for what NOT to ask
- [`references/phase-0-guidance.md`](references/phase-0-guidance.md) through [`phase-7-global-update.md`](references/phase-7-global-update.md) — one per phase
- [`references/phase-5.5-triage.md`](references/phase-5.5-triage.md) — code-first triage + article audit, the most important addition vs naive flows
- [`fixtures/mini-saas/`](fixtures/mini-saas/) — tiny Vue 3 fixture for smoke-testing the skill
