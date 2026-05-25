# Article markdown format

Every article (.md and .tech.md) MUST have this structure.

> All prose section names, headings, and body text rendered to disk are
> in `{lang}` (the language locked in Phase 0). The English names used
> in this reference describe the SEMANTIC sections — the sub-agent
> translates them to `{lang}` when writing the file.

## Front-matter

```yaml
---
slug: <cap-slug>/<article-slug>     # for capability articles
# or
slug: <journey-slug>                 # for journey articles
title: <Human readable title in {lang}>
kind: capability                     # or "journey"
flavor: product                      # or "tech"  (use these English values verbatim)
status: drafted                      # drafted | triaged | interviewed | updated | done | stale
generated_at: "2026-05-21"
skill_version: "1.3.0"               # value from SKILL.md front-matter at generation time
last_interview: ""                   # ISO date of last user answer affecting this guide
source_files:                        # added during Phase 4, optional
  - src/projects/...
  - prisma/schema.prisma
related_guides:                      # added during the Sync command
  - recurring-billing/issue-invoices
---
```

Front-matter KEYS stay in English (skill contract). VALUES like `title`
are in `{lang}`. The `flavor` value is one of the fixed strings
`product` | `tech` — those are enum-like skill tokens, not prose.
`skill_version` is **mandatory** — every article records the version of
this skill that produced or last modified it. Phase 7 and future
maintenance use it to detect "this article was written by an older
skill version, output conventions may differ" and offer a re-pass.

## Sections — product flavor (`.md`)

In this order, no skipping. Section names below are SEMANTIC labels —
the sub-agent renders the actual heading in `{lang}`:

1. **# {title}** (h1)
2. **Why this exists** — why this capability/article matters to the user
3. **How the user experiences it** — user-facing flow, what they see / click / feel
4. **Key concepts** — domain terms with definitions
5. **Main flows** — main flows (mermaid OK if non-trivial)
6. **Day-to-day cases** — Q&A format: "What if I…?"
7. **Living with neighbors** — interactions with other capabilities
8. **See also** — cross-links to 3-5 related guides (the Sync command fills this)

**Zero technical jargon.** No column names, no function names, no
`UPPER_SNAKE_CASE`, no DB enum values, no route paths inline, no
foreign-language terms (anything outside `{lang}`). When a constant
appears in code, find the user-visible label (templates, `:items=`,
`text:`, computed getters, formatters) and use THAT. If the label can't
be found, register a pending question — never leak the raw constant.

Self-check: would a non-technical end user of the product understand
each sentence without opening the codebase? The voice is the one from
`.livedocs/style.md` if it exists; otherwise default to "conversational
tutorial, second person, in `{lang}`".

Tech detail belongs in `.tech.md`, NOT here. That separation is the
whole point of the two flavors.

## Sections — technical flavor (`.tech.md`)

Prose in `{lang}`; identifiers, file:line refs, code blocks unchanged.

1. **# {title} (technical)** (h1) — render the parenthetical in `{lang}` too
2. **Data model** — ORM models touched, key fields
3. **Entry points** — hooks, endpoints, services, routes with file:line
4. **Transition diagram** (if state machines involved) — mermaid
5. **Invariant rules** — numbered (R1, R2, R3) with `file:line`
6. **UI / colors / badges** — only when visual design matters semantically
7. **Pending items and known gaps** — 🟡 hypotheses, missing tests, refactor opportunities
8. **Reference material** — links to repos, docs, ADRs
9. **See also** — cross-links to related tech guides (the Sync command fills this)

Use `file:line` or `file:line-line` citations liberally. Every numbered
invariant rule should cite its source.

## Mermaid usage

Allowed in both flavors but **sparingly**. Rule of thumb: include a
diagram ONLY when prose would take >2 paragraphs to explain what the
diagram shows in one glance.

Common mermaid types used:
- `flowchart` for workflows
- `stateDiagram-v2` for state machines
- `sequenceDiagram` for integrations / API calls
- `erDiagram` for data models (in tech flavor only)

Mermaid labels (node text, edge labels) are user-visible prose — render
in `{lang}`. Node IDs are opaque.

## Pair rules

- `.md` and `.tech.md` MUST share the same slug.
- They live in the same directory.
- They NEVER link directly to each other. Knowledge crosses by
  structure, not by hyperlink.
- Cross-links go to OTHER guides of the SAME flavor.

## Tone

Product flavor:
- Second person (the `{lang}` equivalent of "you").
- Patient teacher tone, no condescension.
- Light humor OK when natural.
- Anticipate confusion: lead with "If you're not sure yet, …"

Tech flavor:
- Third person, direct.
- Tables and bullets liberal.
- Code blocks with language tags.
- Numbered invariants are LAW — they must be backed by code.
