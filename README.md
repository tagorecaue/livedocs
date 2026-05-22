<div align="center">

<img src="assets/banner.png" alt="LiveDocs banner" width="100%">

# LiveDocs

**Living documentation for SaaS — interview-driven, agent-powered, always aligned with the code.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

</div>

---

LiveDocs turns the knowledge that lives in your code + in the dev's head into **paired product and technical guides**, kept alive as the system evolves.

The premise: you don't sit down to "write documentation". You answer targeted questions — questions an AI agent asks after reading your code. The answers become `.md` guides in the language of your choice, living **on your machine**, in your repository, under your control.

No mandatory cloud. No code capture. No lock-in.

## How it works

LiveDocs ships as an **agent skill**, not a binary. Point any capable coding agent (Claude Code, Codex, Cursor, Hermes, etc.) at this repository, load the `livedocs-bootstrap` skill, and the agent walks the bootstrap flow itself — scanning the codebase, proposing a taxonomy, drafting guides, running the refinement interview, and stitching cross-links.

This decision was deliberate: an LLM driving the flow directly through a skill produces dramatically better output than a CLI wrapping the same prompts. The skill is the product.

## Status

**v0 / alpha — internal dogfooding.** The public version will land here once the flow is validated in production. If this is interesting to you, open an issue — early feedback is gold.

## Principles

- **AGPL-3.0** — real open source. Forks must open.
- **Local-first** — `.md` and state live on your machine. Cloud is always optional.
- **BYOA (Bring Your Own Agent)** — any capable coding agent works. The skill is portable.
- **Multi-language from day 1** — guides generated in whatever language your product speaks.
- **Paired product + technical guides** — same knowledge, two audiences: end user (help center, widget) vs dev/AI (MCP, onboarding).
- **Human-in-the-loop always** — AI proposes, dev approves. No silent commits.

## The skill

See `skills/livedocs-bootstrap/` for the bootstrap flow the agent follows. Glossary and canonical product language in `CONTEXT.md`. Architecture decisions in `docs/adr/`.

## Roadmap

| v | Content |
|---|---------|
| **v0** (this) | Bootstrap skill — interview + local guide generation, agent-driven |
| v0.5 | Incremental maintenance skill (PR diff → guide updates) |
| v1 | Publication skill (push to Chatwoot / other help centers) |
| v2 | Optional cloud tier — hosted help center + conversational widget |

## Contributing

Not open to external contributions yet — product is still in validation. When it is, this note disappears.

## License

[AGPL-3.0-or-later](LICENSE).
