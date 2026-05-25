# livedocs-bootstrap (the skill)

This folder IS the skill. The agent's read-only manual lives in
[`SKILL.md`](SKILL.md); the per-phase and per-format references live
under [`references/`](references/).

For everything else — what the skill does, install instructions, real
run example, costs, concepts, requirements, contributing — see the
**[repository README](../../README.md)** at the root of this repo.

## Quick map

- [`SKILL.md`](SKILL.md) — entry point, 13 core principles, the
  Init/Map → Topic loop → Sync model, batch sizing
- [`CHANGELOG.md`](CHANGELOG.md) — version history
- [`references/language-handling.md`](references/language-handling.md) — i18n contract (read first if you change anything user-facing)
- [`references/privacy.md`](references/privacy.md) — what enters and what NEVER enters a sub-agent's context
- [`references/pending-questions.md`](references/pending-questions.md) — heuristic for what NOT to ask
- [`references/phase-0-guidance.md`](references/phase-0-guidance.md) through [`phase-3-review.md`](references/phase-3-review.md) — the one-time Init/Map (setup)
- [`references/topic-loop.md`](references/topic-loop.md) — the per-topic loop: selector + next-topic suggestion, drives Phase 4 → 5.5 → 6 → 7
- [`references/phase-5.5-triage.md`](references/phase-5.5-triage.md) — code-first triage + article audit, the most important addition vs naive flows
- [`references/phase-6-refinement.md`](references/phase-6-refinement.md) — coverage-aware per-topic interview
- [`references/sync-flow.md`](references/sync-flow.md) — on-demand command for cross-links, glossary, recommendations, stale detection
- [`fixtures/mini-saas/`](fixtures/mini-saas/) — tiny Vue 3 fixture for smoke-testing the skill
