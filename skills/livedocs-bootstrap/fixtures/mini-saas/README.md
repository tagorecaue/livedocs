# mini-saas — smoke-test fixture for livedocs-bootstrap

Tiny Vue 3 SaaS used as a smoke test for the skill. Two capabilities
roughly emerge from the code:

- **Billing** — `Billing.vue` + `models/billing.ts` (Subscription,
  Invoice, PaymentMethod).
- **Projects** — `Projects.vue` + `models/projects.ts` (Project, Task).
- **Settings** — `Settings.vue` (touches PaymentMethod).

## How to use as smoke test

1. Symlink or copy this directory somewhere outside the skill repo:

   ```bash
   cp -r skills/livedocs-bootstrap/fixtures/mini-saas /tmp/livedocs-smoke
   cd /tmp/livedocs-smoke
   ```

2. Open your agent in that directory, invoke the skill:

   ```
   Use the livedocs-bootstrap skill to document this project.
   ```

3. Expected outcomes (smoke checks, not strict acceptance):

   - **Phase 0**: detects English from the codebase. User confirms or
     overrides.
   - **Phase 1**: extracts ~3 routes (`/billing`, `/projects`,
     `/settings`), 0 i18n keys (fixture has none), 5 models, no
     graphify required.
   - **Phase 2**: proposes ~2-3 capabilities. Sane shapes are
     `billing`, `project-management`, optionally `account-settings`.
   - **Phase 3**: trivial — accept proposed taxonomy.
   - **Phase 4**: ≤ 5 articles drafted. Each has both `.md` and
     `.tech.md`. Each carries `skill_version` in front-matter.
   - **Phase 5**: TODO:link placeholders resolve, no contradictions.
   - **Phase 5.5**: low pending-question count expected (fixture is
     small); aligned ratio should be high.
   - **Phase 6**: ≤ 5 questions reach the human (or zero — fixture is
     intentionally unambiguous).
   - **Phase 7**: trivial — minimal rewrites.

4. Inspect `docs/` and `.livedocs/state.md`. The state file should
   show all 8 phases marked complete and a total cost under $5 on
   most providers.

## What this DOESN'T test

- Multi-language runs (fixture is English-only).
- Large codebases (fixture is ~6 files).
- Long pending-question backlogs (fixture is too simple).
- Two-pass dedup (won't trigger; ≤ 80 questions).

For those, use a real-sized codebase. The fixture is for catching
regressions in the basic happy path.
