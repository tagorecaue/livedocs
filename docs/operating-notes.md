# Operating notes

Stuff worth knowing once you've decided to use the skill. Keep it
loaded for the first run; you won't need most of it after that.

## Output

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

Each article carries `skill_version` in front-matter, so a future
maintenance pass can detect output produced by an older version of
the skill and offer a re-pass. See the
[CHANGELOG](../skills/livedocs-bootstrap/CHANGELOG.md).

## Cost ranges

Driven by the agent's LLM provider. Observed across real runs. Because the
skill documents one topic at a time, cost is spread across sessions, not
front-loaded:

- Phase 4 (draft): **$0.30–$1.00 per article** (3× variance with topic size)
- Phase 5.5 (triage): **$0.20–$1.50 per article-pair**
- Phase 6 (interview): ~$0.05 per question in chat; intra-topic dedup, if any, is one inline call
- Phase 7 (topic update): **$0.30–$0.80 per affected article**
- Sync (on-demand cross-corpus): scales with corpus size; run occasionally

Real cost gets recorded in `.livedocs/state.md`. Don't promise users
a fixed estimate — measure with your own project first.

## Language

The skill itself is in English (it's the agent's read-only manual).
The OUTPUT — chat messages, interview content, generated guides —
runs in whatever language Phase 0 locks in. Tested in pt-BR and en.

Full rule: [`references/language-handling.md`](../skills/livedocs-bootstrap/references/language-handling.md).

## Privacy

A hard denylist filters paths before any sub-agent reads code:
`.env*`, `secrets/`, `*.pem`/`*.key`, `.aws/`, `.ssh/`, anything in
`.gitignore`, anything in `.git/`. Phase 0 warns the user once that
guidance text will appear in later LLM calls, before saving.

Full policy: [`references/privacy.md`](../skills/livedocs-bootstrap/references/privacy.md).

## Customization

- **Style**: drop a `.livedocs/style.md` in the project to override
  the default voice.
- **Language**: Phase 0 detects from i18n keys / comments / README;
  user confirms or overrides with a BCP-47 code.
- Style + guidance + language all live in `.livedocs/` — version
  them in your repo if you want runs to be reproducible.

## Known limitations

- **No publication** — generates local markdown only. Pushing to
  Chatwoot / other help centers is planned, not built.
- **Sync is manual** — cross-links, glossary, and "next" recommendations are
  reconciled by an on-demand `sync` command, not automatically after each
  topic. This is by design (you control when links get drawn), but it means a
  freshly documented topic has no cross-links until you run sync.
- **Stale detection flags, doesn't fix** — sync marks guides whose source
  changed as `stale`; re-documenting them is a manual topic-loop decision.
  Full incremental maintenance (diffing against the previous run) is planned.
- **Cost variability across LLMs** — Sonnet-class and Opus-class
  models produce noticeably better drafts than smaller ones; the
  skill's quality follows the agent's quality.
- **`is_intro` heuristic** — Phase 4 sometimes generates an overview
  article for small topics that don't need one. Remove via Phase 3
  before documenting the topic.
