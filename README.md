<div align="center">

<img src="assets/banner.jpg" alt="LiveDocs banner" width="900">

</div>

<p align="center">
  🇺🇸 <a href="README.md">English</a> | 🇧🇷 <a href="docs/translations/README.pt-BR.md">Português</a>
</p>

<p align="center">
  <a href="https://www.gnu.org/licenses/agpl-3.0"><img src="https://img.shields.io/badge/License-AGPL_v3-blue.svg" alt="License: AGPL v3"/></a>
  <a href="#"><img src="https://img.shields.io/badge/status-alpha-orange.svg" alt="Status: alpha"/></a>
  <a href="https://github.com/safishamsi/graphify"><img src="https://img.shields.io/github/stars/safishamsi/graphify?style=flat&label=graphify%20%E2%AD%90&color=yellow" alt="graphify stars"/></a>
  <a href="https://www.linkedin.com/in/tagorecaue/"><img src="https://img.shields.io/badge/LinkedIn-Tag%C3%B4re%20Cardoso-0077B5?logo=linkedin" alt="LinkedIn"/></a>
  <a href="https://github.com/tagorecaue"><img src="https://img.shields.io/badge/GitHub-tagorecaue-181717?logo=github" alt="GitHub"/></a>
</p>

# LiveDocs
Document any SaaS, end-to-end, from its source code plus a guided
interview with the developer. The agent reads the repo, proposes a
taxonomy, drafts every article, then asks you only the questions the
code can't answer.

Two paired outputs per topic: a **product guide** (no jargon, for end
users) and a **technical guide** (with `file:line` references, for
devs). Both live inside the codebase. No cloud, no lock-in.

## How it works

LiveDocs documents your project **one topic at a time** — never all at once.
First a one-time setup, then a loop you drive: you pick a topic, the agent takes
it end to end, then suggests the next one.

**One-time setup — build the map**
1. **Read the repo, propose a taxonomy.** Builds a semantic graph
   of the codebase (using
   [graphify](https://github.com/safishamsi/graphify) — the
   widely-used MIT-licensed knowledge-graph tool by Safi Shamsi),
   derives categories and articles, you approve. The taxonomy is the map;
   it stays editable as you go.
   → [Phase 1](skills/livedocs-bootstrap/references/phase-1-scan.md),
   [2](skills/livedocs-bootstrap/references/phase-2-taxonomy.md),
   [3](skills/livedocs-bootstrap/references/phase-3-review.md)

**Topic loop — repeat per topic, you choose each one**
2. **Pick a topic; the agent drafts its articles** in two paired versions —
   product flavor (no jargon) + technical flavor (`file:line` refs). Internal or
   deprecated screens simply never get picked, so they never pollute the docs.
   → [Topic loop](skills/livedocs-bootstrap/references/topic-loop.md),
   [Phase 4](skills/livedocs-bootstrap/references/phase-4-pass1-drafts.md)

3. **Code-first triage** of every pending question for that topic. Only what
   truly needs a human survives.
   → [Phase 5.5](skills/livedocs-bootstrap/references/phase-5.5-triage.md)

4. **A focused, coverage-aware interview** about that one topic. Answer in one
   big dump if you like — after each answer the agent re-checks every open
   question for what you already covered (fully / partially / not), confirms the
   sure ones in a batch, and always re-asks the partial ones. Nothing important
   is silently skipped.
   → [Phase 6](skills/livedocs-bootstrap/references/phase-6-refinement.md)

5. **Rewrite that topic's affected articles** from your answers, commit, and
   return to the selector for the next topic.
   → [Phase 7](skills/livedocs-bootstrap/references/phase-7-global-update.md)

**On demand — sync the whole doc set**
6. **Sync** reconciles everything that spans topics — cross-links, glossary,
   "what to read next", stale detection — over the entire corpus, whenever you
   ask. It never runs inside the loop, so closing one topic never forces edits
   to topics already done.
   → [Sync](skills/livedocs-bootstrap/references/sync-flow.md)

Real run: 76 articles + 6 journeys, ~$110 in LLM spend, ~4h human
time. Full breakdown in the [case study](docs/case-study.md).

## Install

```bash
npx skills@latest add tagorecaue/livedocs
```

This walks you through which coding agent(s) to install the skill on
(Claude Code, Codex, Cursor, OpenCode, etc.) and symlinks the skill
into each agent's skills directory.

Then, in your agent, run the one-time environment setup:

```
/setup-livedocs
```

It checks for `graphify` and installs it if missing
(via `uv` or `pipx`).

<details>
<summary>Manual install (no npm)</summary>

Clone or fork this repo, then symlink the skill into your agent's
skills dir:

```bash
# Claude Code
ln -s "$PWD/skills/livedocs-bootstrap" ~/.claude/skills/livedocs-bootstrap

# Hermes
ln -s "$PWD/skills/livedocs-bootstrap" ~/.hermes/skills/livedocs-bootstrap
```

Then install `graphify` manually:

```bash
uv tool install graphifyy
```

</details>

## Quickstart

In the chat with your agent:

```
Use the livedocs-bootstrap skill to document this project.
```

The agent takes over. State persists in `.livedocs/state.md` — you
can interrupt and resume any time.

## Requirements

- A coding agent with sub-agent / Task primitives, file write, and
  shell. Verified: Claude Code (Sonnet 4 / Opus), Hermes (Opus 4.7),
  Codex CLI. Smaller models drop Phase 4 quality noticeably.
- [`graphify`](https://github.com/safishamsi/graphify) — installed
  automatically by `/setup-livedocs`. Without it Phase 2's taxonomy
  is weaker, but the rest still works.
- A git repo (Phase 1 records the scan SHA; later phases
  commit-per-batch).
- `node` / `npx` if you use the one-line install above. Skip if you
  do the manual install.

## When to use it / when not to

Use it when the user asks for documentation, a help center, onboarding
docs, etc., AND the codebase is large enough that hand-writing
would take weeks. Skip when there's already docs to read, when a
single ad-hoc README is enough, or when the repo is tiny.

## Going deeper

- [**Concepts**](docs/concepts.md) — Why capability/journey/screen,
  why two flavors, why pending questions, why isolated context, what
  the guidance text is for.
- [**Operating notes**](docs/operating-notes.md) — Output format, cost
  ranges, language, privacy, customization, known limitations.
- [**Case study**](docs/case-study.md) — Real per-phase breakdown
  from a production SaaS run.
- [`SKILL.md`](skills/livedocs-bootstrap/SKILL.md) — The agent's
  manual: 13 core principles, phase table, batch sizing.
- [`CHANGELOG.md`](skills/livedocs-bootstrap/CHANGELOG.md) — Version
  history.

## Author

Built by **Tagôre Cardoso** — designed and dogfooded in
🇧🇷 **Brazil**, on a real production SaaS with paying customers
and 2+ years in production. That run generated **156 articles**
and **30,000+ lines** of high-quality documentation. The design
choices that look opinionated came from things going wrong in
attended runs, not from whiteboarding.

Feedback, bug reports, and reproduction repos welcome.

## Contributors

<p>
  <a href="https://github.com/tagorecaue" title="Tagôre Cardoso — creator &amp; maintainer">
    <img src="https://images.weserv.nl/?url=github.com/tagorecaue.png&w=120&h=120&fit=cover&mask=circle" width="60" height="60" alt="Tagôre Cardoso"/>
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/FredySchaible" title="Fredy Schaible — contributor">
    <img src="https://images.weserv.nl/?url=github.com/FredySchaible.png&w=120&h=120&fit=cover&mask=circle" width="60" height="60" alt="Fredy Schaible"/>
  </a>
</p>

Want to be here? See [`CLAUDE.md`](CLAUDE.md) for dev guidelines, then open a PR.

## License

AGPL-3.0-or-later. Forks must open. See [`LICENSE`](LICENSE).

For dev guidelines, see [`CLAUDE.md`](CLAUDE.md).

---

<sub>Made in 🇧🇷 Brazil by [Tagôre Cardoso](https://www.linkedin.com/in/tagorecaue/) · [GitHub](https://github.com/tagorecaue)</sub>
