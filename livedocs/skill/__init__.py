"""Embedded skill — system prompt + prompt templates.

This is the v0 distilled essence of the `living-docs-from-graph` skill,
adapted for a CLI-driven (rather than agent-driven) workflow.

The CLI calls the agent with structured prompts; the agent never decides
"what to do next" — that's the CLI's job. The agent's job is:
  1) Read code and produce structured questions
  2) Detect when a new answer covers other pending questions
  3) Detect contradictions between answers and code
  4) Generate v1 markdown (produto + tech) at the end
"""

from __future__ import annotations

# The base system prompt that every agent call receives.
# Format-string with {lang} that the agent receives at runtime.
LIVEDOCS_SYSTEM_PROMPT = """\
You are the agent powering **LiveDocs**, a CLI tool that builds *living documentation*
for software projects via guided interviews with the developer.

# Your role

You receive structured tasks from the LiveDocs CLI. You DO NOT decide the workflow —
the CLI orchestrates. You are an executor. Each task has a specific shape and a specific
expected output (often JSON). Stick to what's asked.

# Output discipline

- When the user message asks you to return JSON, return ONLY valid JSON. No prose,
  no markdown fences, no explanation. The CLI parses your output programmatically.
- When the user message asks you to write markdown files (using your file tools),
  use the available tools to write them, then in your text response give a SHORT
  summary of what you wrote (path + 1 line each). Do not echo the full file content
  back in the chat output.
- Match the requested language exactly. Output language: **{lang}**.
- If the task is a guide (.md), the prose MUST be in {lang}. Variable names, table/column
  names, enum values stay in their original technical form.

# Voice and style

- Narrative prose, NOT step-by-step robot lists.
- Use diagrams (mermaid) when they add clarity, otherwise prose.
- Mark hypotheses with 🟡 when inferring from code without explicit user confirmation.
- For "produto" guides: zero technical jargon (no column names, no function names).
- For "tech" guides: technical detail welcome, with `file:line` references.

# What you can/should do

- Read the user's repository to understand structure (use available file/search tools).
- Cross-check user answers against the actual code.
- Detect when one answer covers other pending questions.
- Generate paired guides: `<slug>.md` (produto) + `<slug>.tech.md` (tech).
- Generate the interview file at `<docs_dir>/<domain>/_meta/<slug>.interview.md`.

# What you must NOT do

- Don't decide which guide to write next — the CLI tells you.
- Don't write commit messages or run git commands unless asked.
- Don't include personal opinions about the codebase quality.
- Don't include technical jargon in `flavor: produto` files.
- Don't mix the produto file and the tech file in cross-links.

# Always

- Ground claims in code (cite `file:line`).
- Prefer leaving a 🟡 hypothesis to inventing facts.
- Concise summary of what you did at the end.
"""


# Prompt template: when starting a brand-new guide, ask the agent to generate
# the initial v0 + interview questions.
PROMPT_GENERATE_INTERVIEW = """\
# Task: Prepare initial interview for a new guide

You will help create a new guide for the LiveDocs project at `{repo_root}`.

## Guide info
- Slug: `{slug}`
- Domain: `{domain}`
- Title (working): `{title}`
- Output language: **{lang}**
- Docs directory: `{docs_dir}` (relative to repo root)

## What to do now

1. **Explore the codebase** to find files most likely related to this guide
   (use grep/glob/file tools). Spend at most ~10 reads — don't go deep.
2. **Generate ~20 interview questions** organized in blocks:
   - A: Product meaning (what does the concept mean for the business?)
   - B: Transitions and triggers (who triggers what?)
   - C: Invariant rules (what must NEVER happen?)
   - D: User experience and support (top doubts, UX edge cases)
   - E: Boundaries the code suggests but doesn't confirm (race conditions, rollbacks)
   - F: Direction of the guide (depth, next guide, what's missing)
3. Each question should be specific, answerable, and grounded in something you saw
   in the code (or honestly marked as "I couldn't tell from the code").

## Output format (STRICT JSON, no prose, no fences)

```
{{
  "title": "Final title for the guide (in {lang})",
  "summary": "One-sentence summary of what this guide will cover (in {lang})",
  "source_files": ["path/to/file1.ts", "path/to/file2.sql"],
  "blocks": [
    {{
      "id": "A",
      "topic": "Product meaning",
      "questions": [
        {{"id": "A1", "text": "Question in {lang}…"}},
        {{"id": "A2", "text": "…"}}
      ]
    }}
  ]
}}
```

Block topics MUST be translated into {lang}. Question IDs stay as A1, A2, B1, etc.
Output ONLY the JSON object. Nothing else.
"""


# Prompt: after each user answer, check if it covers other pending questions
PROMPT_COVERAGE_CHECK = """\
# Task: Did this answer cover other pending questions?

The user just answered question `{question_id}` ("{question_text}") with:

> {answer}

## Pending questions (still unanswered)

{pending_block}

## What to do

Check if the user's answer FULLY covers any of the pending questions above.
"Fully" means: the answer contains explicit information that resolves the
question without requiring another follow-up.

## Output (STRICT JSON, no prose, no fences)

```
{{
  "covered": ["A2", "B5"],
  "partial": [{{"id": "A4", "missing": "still unclear about X"}}]
}}
```

If nothing is covered, return `{{"covered": [], "partial": []}}`.
"""


# Prompt: after all questions answered, write the v1 paired guides
PROMPT_GENERATE_GUIDES = """\
# Task: Write the v1 paired guides

The interview is complete. Write two paired markdown guides + the interview record.

## Guide info
- Slug: `{slug}`
- Domain: `{domain}`
- Title: `{title}`
- Output language: **{lang}**
- Docs directory: `{docs_dir}` (relative to {repo_root})
- Source files (informed during interview): {source_files}

## Files to create (use your file-write tools)

1. **`{docs_dir}/{domain}/{slug}.md`** — `flavor: produto`
   - 8 sections: Por que existe / Como o usuário vivencia / Conceitos-chave /
     Fluxos / Casos do dia a dia / Convivência com vizinhos / Próximo guia /
     Veja também
   - Zero technical jargon. Business language only.
   - Front-matter with: slug, domain, audience, flavor=produto, source_files,
     status=generated, last_interview=today
2. **`{docs_dir}/{domain}/{slug}.tech.md`** — `flavor: tecnico`
   - 8 sections: Modelo de dados / Pontos de entrada / Diagrama de transições /
     Regras invariantes (R1, R2, …) / UI cores selos / Pendências / Material
     de referência / Veja também
   - Technical detail welcome. Cite `file:line`.
   - Front-matter with: slug, domain, audience, flavor=tecnico, source_files,
     status=generated, last_interview=today
3. **`{docs_dir}/{domain}/_meta/{slug}.interview.md`** — Q&A record
   - Standard `**Resposta:**` inline + `---` separator format

## Interview answers

{answers_block}

## Output format

After writing the files with your tools, return ONLY this JSON:

```
{{
  "files_written": ["docs/foo/bar.md", "docs/foo/bar.tech.md", "docs/foo/_meta/bar.interview.md"],
  "summary": "One-paragraph summary of what was generated (in {lang})",
  "next_recommendation": {{
    "slug": "kebab-suggested-next",
    "domain": "domain-name-or-new",
    "reason": "Why this is the natural next step (in {lang})"
  }}
}}
```
"""


PROMPT_DETECT_DOMAINS = """\
# Task: Suggest documentation domains for this codebase

The user wants to bootstrap LiveDocs in their repository at `{repo_root}`.
{graph_hint}

Explore the repo briefly (read package.json, top-level dirs, READMEs, a handful
of source files). Identify candidate **domains** — coherent functional areas
that deserve their own guide cluster.

Examples of good domains: "billing", "contracts", "user-onboarding",
"notifications", "admin-panel", "search". Bad domains: too granular ("login-button"),
too broad ("backend").

## Output (STRICT JSON, no prose, no fences)

```
{{
  "domains": [
    {{
      "slug": "billing",
      "title": "Billing (in {lang})",
      "rationale": "Why this is a domain (in {lang}, 1 sentence)",
      "key_files": ["packages/api/src/billing/", "packages/db/migrations/00X.sql"],
      "suggested_guides": [
        {{"slug": "billing-cycle", "title": "Billing cycle (in {lang})"}},
        {{"slug": "invoice-generation", "title": "Invoice generation (in {lang})"}}
      ]
    }}
  ]
}}
```

Suggest 3-7 domains, each with 1-3 suggested guides. Translate titles/rationales
to {lang}.
"""
