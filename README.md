<div align="center">

<img src="assets/banner.jpg" alt="LiveDocs banner" width="900">

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

</div>

# LiveDocs
Document any SaaS, end-to-end, from its source code plus a guided
interview with the developer. The agent reads the repo, proposes a
taxonomy, drafts every article, then asks you only the questions the
code can't answer.

Two paired outputs per topic: a **product guide** (no jargon, for end
users) and a **technical guide** (with `file:line` references, for
devs). Both live inside the codebase. No cloud, no lock-in.

## How it works, in 5 steps

1. **Read the repo, propose a taxonomy.** Builds a semantic graph,
   derives categories and articles. You approve.
   → [Phase 1](skills/livedocs-bootstrap/references/phase-1-scan.md),
   [2](skills/livedocs-bootstrap/references/phase-2-taxonomy.md),
   [3](skills/livedocs-bootstrap/references/phase-3-review.md)

2. **Write every article in parallel, in two paired versions.**
   Product flavor (no jargon) + technical flavor (`file:line` refs).
   Marks where screenshots are needed. Logs every question the code
   alone can't resolve.
   → [Phase 4](skills/livedocs-bootstrap/references/phase-4-pass1-drafts.md)

3. **Cross-link, deduplicate, and code-first triage** every pending
   question. Only what truly needs a human reaches you.
   → [Phase 5](skills/livedocs-bootstrap/references/phase-5-pass2-stitching.md),
   [5.5](skills/livedocs-bootstrap/references/phase-5.5-triage.md)

4. **Interview you in chat** with whatever survived the triage,
   grouped by theme (meaning / transitions / invariants / UX-support /
   code edges / direction). Each question shows the agent's guess +
   confidence level.
   → [Phase 6](skills/livedocs-bootstrap/references/phase-6-refinement.md)

5. **Rewrite only the affected articles** from your answers.
   → [Phase 7](skills/livedocs-bootstrap/references/phase-7-global-update.md)

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
🇧🇷 **Brazil**, on a real production SaaS. The design choices that
look opinionated came from things going wrong in attended runs, not
from whiteboarding.

Find Tagôre on [LinkedIn](https://www.linkedin.com/in/tagorecaue/)
or [GitHub](https://github.com/tagorecaue). Feedback, bug reports,
and reproduction repos welcome.

## License

AGPL-3.0-or-later. Forks must open. See [`LICENSE`](LICENSE).

For dev guidelines, see [`CLAUDE.md`](CLAUDE.md).

---

<sub>Made in 🇧🇷 Brazil by [Tagôre Cardoso](https://www.linkedin.com/in/tagorecaue/) · [GitHub](https://github.com/tagorecaue)</sub>
