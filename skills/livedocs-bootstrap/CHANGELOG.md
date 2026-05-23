# Changelog

All notable changes to the `livedocs-bootstrap` skill are recorded here.
The skill follows [SemVer](https://semver.org/): MAJOR breaks article
format or state schema, MINOR adds a phase or principle, PATCH is
clarifications and pitfall fixes.

Each version's date is when the change landed in the skill's git
history.

## Repo-level changes (not skill version bumps)

- **2026-05-22** — `.claude-plugin/plugin.json` added at the repo
  root so `npx skills@latest add tagorecaue/livedocs` works. New
  companion skill `livedocs-setup` (v1.0.0) checks for `graphify`
  and installs it via `uv` or `pipx` on first run.

## [1.3.1] — 2026-05-23

### Fixed
- **i18n leaks in references.** `phase-2-taxonomy.md` no longer
  hardcodes `introducao` for default intro articles — slug now
  resolves from `{lang}` (`overview`/`introducao`/`descripcion`)
  with `is_intro: true`. `phase-4-pass1-drafts.md` no longer writes
  `docs/<kind>/...`; uses `<capabilities-dir>` / `<journeys-dir>`
  resolved via `references/language-handling.md`. Phase 6 interview
  files renamed from pt-BR-only (`bloco-a-significado-produto.md`)
  to language-neutral (`block-a-product-meaning.md`); contents
  already in `{lang}`, only filenames leaked.
- **Phase 5.5 proposed diffs were silently lost.** Review of the
  diffs is now required before bootstrap completes. User chooses
  `before_phase_6` (recommended) or `during_phase_7`, persisted in
  state as `proposed_diffs_review`. Phase 7 step 1.5 reads that
  field and injects the diff into each affected sub-agent prompt
  when `during_phase_7` was chosen.
- **Phase 6 dropped `open` questions when Phase 5.5 was skipped.**
  Step 1 now branches on whether 5.5 ran: with 5.5, filter
  `needs_human` only; without 5.5, include both `needs_human` and
  `open`. No silent loss either way.
- **Phase 7 only patched one origin guide per question.** Dedup in
  Phase 6 merges questions originating from multiple capabilities;
  field renamed from `canonical_origin` (string) to
  `canonical_origins` (list, union-merged across absorbed
  canonicals). Phase 7 now routes each answer to ALL origin guides.
- **Phase 4 sub-agent return contract.** Sub-agent now self-verifies
  with `wc -c` + `grep slug:` and returns `verification_passed:
  true|false`. Orchestrator checks the flag instead of running a
  separate `stat` after the call (was duplicate work, and could
  diverge from what the sub-agent thought it wrote).
- **Duplicated principle numbering in SKILL.md** (`3` + `3b`). Now
  cleanly numbered 1-13.
- **`state-format.md` missed Phase 5.5** in the example phase
  checklist and the `answered_by_code` counter.

### Changed
- `livedocs-setup`: package name corrected to `graphifyy` (was
  `graphify`) in the `pipx` / `pip3` install commands. The PyPI
  package is `graphifyy` (double-y, naming reclaim); `graphify`
  fails on install.

## [1.3.0] — 2026-05-22

### Added
- **Privacy and context boundaries** (core principle 13 +
  `references/privacy.md`). Orchestrator filters paths against a hard
  denylist (`.env*`, `secrets/`, `*.pem`/`*.key`, `.aws/`, `.ssh/`,
  `.gitignore`d content, `.git/`) BEFORE composing sub-agent prompts.
  Phase 0 includes a one-time privacy heads-up before saving guidance.
- **Output versioning**: every article carries a mandatory
  `skill_version` front-matter field. Bumped on creation (Phase 4),
  stitch (Phase 5), triage patch (Phase 5.5), and global update
  (Phase 7). Enables future maintenance to detect articles written
  by older skill versions.

### Changed
- Examples throughout `references/` rewritten to neutral domains
  (project management, recurring billing, contracts) instead of
  <Client>-specific (REURB, moradores, gestao-projetos). Slug
  examples in `language-handling.md` retain pt-BR variants alongside
  English to illustrate the i18n contract.

## [1.2.0] — 2026-05-22

### Added
- **Language handling reference** (`references/language-handling.md`)
  as single source of truth for the i18n contract. Distinguishes
  skill internals (always English) from run output (`{lang}`).
- **Phase 0 step 1**: detect project language, confirm with user,
  persist `Lang:` in state. Every later phase renders user-visible
  prose in `{lang}`.
- Top-level docs dirs render in `{lang}` (`capabilities/` vs
  `capacidades/` etc).

### Changed
- All references and SKILL.md rewritten in English. Previously some
  parts had pt-BR strings hardcoded; now any non-English string in
  the skill is treated as a bug.
- Core principle 3b (UI language) generalized away from pt-BR-default.
- Quick-reference command card lists multiple language equivalents.

## [1.1.0] — 2026-05-22

### Added
- **Phase 5.5 — Code-first triage + article audit**
  (`references/phase-5.5-triage.md`). Between Phase 5 (stitching) and
  Phase 6 (interview), one sub-agent per capability re-checks pending
  questions against code with literal evidence (file:line + snippet)
  AND patches divergent articles. Reduces human interview burden by
  resolving auto-answerable questions while simultaneously fixing
  the articles that were written without that information.
- **Core principle 11 — commit per batch.** Each Phase 4 batch, each
  Phase 5 capability, each Phase 5.5 capability is an atomic git
  checkpoint. Commits use prefixed messages (`phase-4:`, `phase-5.5:`)
  for selective revert and `git log --grep` audit.
- **Core principle 12 — post-edit verification and anti-loop guard.**
  Sub-agents that write files must verify with `wc -c` > 0 and
  sentinel grep, include `verification_passed: true|false` in the
  JSON return. If the same tool fails 2× with the same error, the
  sub-agent aborts.
- **Batch sizing table** in SKILL.md: Phase 4 = 1 article/sub-agent,
  Phase 5 ≤ 5, Phase 5.5 = 1 capability, Phase 6 dedup ≤ 80 questions,
  Phase 7 = 1 article. Hard ceilings observed in production runs.
- **Heuristic "what NOT to ask"** in `references/pending-questions.md`.
  Guiding principle: pending questions must be about INTENT or
  EXPERIENCE, not EXISTENCE or VALUE. Tables of 🚫 / ✅ patterns.
- **Phase 6 thematic blocks A–F**: refinement interview organized by
  theme (meaning / transitions / invariants / UX+support / edges /
  meta-direction) instead of by capability of origin. Lower fatigue,
  faster pace.
- **Two-pass thematic dedup** in Phase 6: intra-batch parallel
  (≤80 questions/batch) → cross-batch reconcile in a single sub-agent.
  Explicit invariants on the clusters JSON (`canonical_id` never
  appears in its own `merged_ids`).
- **Block F fixed template** ("Right depth?", "Anything I missed?",
  "What guide next?", "Anything I should have asked?"). Always
  present in the interview.
- **Phase 4 prior-interview pass**: if `.livedocs/interview/` already
  has answered files (from a prior run), Phase 4 reads them BEFORE
  drafting. Disagreements with current code generate a single
  category-E pending question citing both sides.
- **Phase 5 cross-flavor rule** spelled out with example. `.tech.md`
  containing a `[TODO:link=<self>]` to its own product sibling: the
  placeholder and surrounding phrase are removed entirely; reported
  in a `cross_flavor_removed` array.

### Changed
- Replaced the single fixed cost estimate ($0.30/article) with
  honest observed ranges per phase, with a note to measure on your
  own project before promising users a budget.

## [1.0.0] — 2026-05-21

### Added
- Initial standalone skill — replaces the previous Python CLI.
- 7 phases: guidance → scan → taxonomy → review → drafts → stitch →
  interview → global update.
- State as readable markdown in `.livedocs/state.md`.
- Article pair convention (`.md` + `.tech.md` per topic, never
  cross-linked).
- Screenshot TODOs as in-line admonitions.
- Pending questions registered during drafts, batched in interview.

## Format notes

`skill_version` in an article's front-matter records the version of
this skill that produced (Phase 4) or last modified (Phase 5/5.5/7)
that article. A version mismatch between articles inside a single
`docs/` tree means a partial regeneration happened; the skill flags
it during the next maintenance pass.
