# LiveDocs — Skill Procedure (v0.2 — bootstrap)

This file is loaded as context for the embedded agent system prompt. It captures
the *workflow conventions* that consumers of LiveDocs guides expect.

It's a distillation of `living-docs-from-graph` (the upstream skill) with a key
difference: **the LiveDocs CLI orchestrates the workflow**, not the agent.

## Workflow at a glance

A maintainer drives the whole help center from one command:

```
livedocs init                       # one-time project setup
livedocs bootstrap                  # seven-phase pipeline, full system
livedocs bootstrap --resume         # resume from the last completed phase
livedocs bootstrap --skip-refinement  # skip phase 6 interview (resume later)
livedocs refine                     # run phases 6+7 alone, after --skip-refinement
```

The bootstrap pipeline has seven phases (see `.spec/bootstrap/plano-bootstrap.md`):

  0. Guidance — free-form orientation from the maintainer.
  1. Scan — deterministic code scan (graph + routes + i18n + models).
  2. Taxonomy — capabilities + journeys proposed by Claude.
  3. Review — interactive (or `--accept-taxonomy`) approval.
  4. Pass 1 — isolated drafts (one Claude call per guide).
  5. Pass 2 — cross-guide stitching (links, terminology, contradictions).
  6. Refinement — AI dedup of pending questions + batch interview.
  7. Global update — rewrite the guides whose questions got answered.

The agent never invents content: anything that can't be derived from code is
turned into a *pending question* and answered in phase 6.

---

## Two paired guides per topic

Every topic produces **two** markdown files:

- `<slug>.md` — **product** flavor. Audience: end-users, support, product managers,
  conversational widget RAG. **Zero technical jargon.**
- `<slug>.tech.md` — **technical** flavor. Audience: devs, AI agents (via MCP), code
  review onboarding. **Detailed**, with `file:line` citations and numbered invariants.

The pair lives in the same domain folder. They never link to each other directly —
the relationship is structural (same slug + suffix). Cross-links go to other guides
of the **same flavor** + the glossary.

## Front-matter

Every guide must start with:

```yaml
---
slug: <kebab-case>
domain: <domain-name>
audience: <who reads this>
flavor: produto | tecnico
source_files:
  - path/to/file1.ts
  - path/to/file2.sql
related_guides: [<slugs>]
last_interview: YYYY-MM-DD
status: draft | reviewed | stale
---
```

## Standard sections (produto, in order)

1. Por que isso existe / Why this exists
2. Como o usuário vivencia / How the user experiences it
3. Conceitos-chave / Key concepts
4. Fluxos principais / Main flows (mermaid welcome)
5. Casos do dia a dia / Day-to-day cases
6. Convivência com vizinhos / Interaction with neighboring domains
7. Veja também / See also

The "next guide" recommendation is **metadata, not content**. It lives in
the domain's `_index.md` (the nav file). Never write a "Próximo guia" /
"Next guide" section inside the guide body itself.

## Standard sections (tecnico, in order)

1. Modelo de dados / Data model
2. Pontos de entrada / Entry points (hooks, endpoints, services)
3. Diagrama de transições / Transition diagram
4. Regras invariantes / Invariant rules (numbered: R1, R2, R3 with file:line)
5. UI / cores / selos / UI / colors / badges
6. Pendências e melhorias mapeadas / Known gaps
7. Material de referência / Reference material
8. Veja também / See also

## Interview record format

Each guide also has an interview record at:

```
<docs_dir>/<domain>/_meta/<slug>.interview.md
```

Format:

```markdown
**A1.** Pergunta…

**Resposta:**

(user's answer)

---

**A2.** Próxima pergunta…

**Resposta:**

(user's answer)

---
```

## Hypothesis markers

When inferring something from code without explicit user confirmation, mark
with 🟡 in the draft. Each 🟡 should become an interview question.

## Cross-link sweep

When closing a guide, add a "Veja também" / "See also" section with 3-5 bullets
linking to related guides of the **same flavor**. Each bullet is one sentence
explaining why the reader would visit.

Cross-links should be **bidirectional** — adding A → B means also adding B → A.
