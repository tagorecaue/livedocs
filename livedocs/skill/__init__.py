"""LiveDocs skill — embedded prompts that drive the agent (Claude Code).

# Two layers

## 1. System prompt (LIVEDOCS_SYSTEM_PROMPT)

Sent on every call via `--append-system-prompt`. Establishes:
  - Role (executor, not orchestrator)
  - Output discipline (strict JSON when asked)
  - Voice (narrative prose, mark hypotheses with 🟡)
  - Guardrails (no jargon in produto, evidence-based claims)

## 2. Per-task prompts (one per agent-call site in the CLI)

Each prompt is a Python f-string template imported by the call site.
The CLI fills in slug/domain/lang/context and passes the result to ClaudeAgent.

Phase A→B prompt map:

  | CLI step                       | Prompt                          | New in |
  | ------------------------------ | ------------------------------- | ------ |
  | livedocs new (free-text intent)| PROMPT_PARSE_INTENT             | v0.2   |
  | Skeleton build                 | PROMPT_BUILD_SKELETON           | v0.2   |
  | Reflect after each answer      | PROMPT_REFLECT_ON_ANSWER        | v0.2   |
  | Pre-generation self-audit      | PROMPT_PREGEN_SELF_AUDIT        | v0.2   |
  | Generate v1 paired guides      | PROMPT_GENERATE_GUIDES          | rewritten v0.2 |
  | Post-gen eval — clarity        | PROMPT_EVAL_PRODUCT_CLARITY     | v0.2   |
  | Post-gen eval — completeness   | PROMPT_EVAL_TECH_COMPLETENESS   | v0.2   |
  | Post-gen eval — coherence      | PROMPT_EVAL_BASE_COHERENCE      | v0.2   |
  | Reverse-link sweep (cross-base)| PROMPT_REVERSE_LINK_SWEEP       | v0.2   |

The old v0.1 prompts (PROMPT_GENERATE_INTERVIEW, PROMPT_COVERAGE_CHECK) stay
defined for legacy-import compatibility, but the new CLI flow does not use them.
"""

from __future__ import annotations

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

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

# Evidence-first principle

Every claim a guide makes MUST be backed by either:
  - code evidence (`file:line` or `file:start-end`), or
  - user-confirmed answer (interview answer id), or
  - inheritance from another guide of the same flavor (slug)

Claims without grounding go into "Pendências e melhorias mapeadas" of the tech
guide marked with 🟡, NEVER into the product guide as if they were known.

# Fact-driven model

The CLI now maintains a list of `Fact` records — atomic units of knowledge the
guide must establish. Each fact has:

  - `kind`: trigger | invariant | edge_case | terminology | flow | value | actor | ui_surface
  - `confidence`: none | low | medium | high
  - `priority`:
      - established: evidence is strong → will become an assertion automatically
      - needs-confirmation: evidence exists but ambiguous → ASK the user
      - hypothesis-with-trace: weak evidence → goes to Pendências with 🟡
      - speculation: NO evidence, only intuition → only category that can be silenced
  - `status`: open | hypothesized | confirmed | contradicted | resolved
  - `evidence[]`: list of {kind, ref, note}

When you build the skeleton, you classify each fact. The CLI uses the priority
to decide which facts become interview questions and which become assertions.

# What you can/should do

- Read the user's repository (Read, Glob, Grep tools).
- Cross-check user answers against code in real time.
- Generate `Fact` records with explicit evidence.
- Write paired guides: `<slug>.md` (produto) + `<slug>.tech.md` (tech) +
  `_meta/<slug>.interview.md`.

# What you must NOT do

- Don't decide which guide to write next — the CLI tells you.
- Don't run git commands.
- Don't include technical jargon in `flavor: produto` files.
- Don't assert facts without evidence.
- Don't return code-fenced JSON when JSON is requested.
"""


# =============================================================================
# PHASE B — NEW PROMPTS
# =============================================================================

# -----------------------------------------------------------------------------
# PARSE INTENT — free text → {slug, domain, title, is_new_domain}
# -----------------------------------------------------------------------------

PROMPT_PARSE_INTENT = """\
# Task: Parse the user's free-text intent into structured guide metadata

The user typed this description (in {lang}) of what they want to document:

> {intent}

## Existing domains in this project

{existing_domains}

## What to do

1. Decide the **slug** (kebab-case, ASCII, ≤40 chars, matches what the guide is about).
2. Decide the **domain** — prefer an existing one when it fits; otherwise propose a new domain slug.
3. Decide the **title** (in {lang}, human-readable, ≤60 chars).
4. Decide whether the domain is new (`is_new_domain: true`) or existing (`false`).
5. If the intent is ambiguous (could mean 2+ different things), provide a one-line
   `clarification_needed` describing what you'd ask. Otherwise leave it empty.

## Output (STRICT JSON, no prose, no fences)

{{
  "slug": "kebab-case-slug",
  "domain": "domain-name",
  "title": "Human title in {lang}",
  "is_new_domain": false,
  "clarification_needed": ""
}}
"""


# -----------------------------------------------------------------------------
# BUILD SKELETON — read code, produce fact skeleton with auto-audit
# -----------------------------------------------------------------------------

PROMPT_BUILD_SKELETON = """\
# Task: Build the fact skeleton for a new guide

You are starting documentation work on this guide:

- Slug: `{slug}`
- Domain: `{domain}`
- Title: `{title}`
- Output language: **{lang}**
- Repo root: `{repo_root}`
- Docs directory: `{docs_dir}` (relative to repo root)
- Existing guides in this project (slug + domain): {existing_guides_compact}

## What to do

### Step 1: Read the code

Use Read/Glob/Grep tools to find files relevant to this topic. Spend 5–15 reads —
enough to ground your skeleton in real code, not so many you drown in detail.

### Step 2: Produce a Fact skeleton (target: 10–30 facts)

For each fact:
  - Assign an id (F1, F2, F3, ...).
  - Choose `kind`: trigger | invariant | edge_case | terminology | flow | value | actor | ui_surface
    | rationale | customer_question | business_rule_unwritten
  - Write a one-sentence `text` claim in **{lang}**.
  - Assess `confidence` based on what the code shows (none/low/medium/high).
  - Pick `priority` per the principle:
      * `established`: evidence in code is unambiguous. Will become an assertion.
      * `needs-confirmation`: evidence exists but ambiguous (e.g., copy that might
        be stale, transition that's done via cron but flag is unclear). ASK the user.
      * `hypothesis-with-trace`: you spotted a possibility but evidence is weak.
        Will go to Pendências with 🟡.
      * `speculation`: NO evidence at all, pure intuition. Only category that can
        be silenced. **Avoid abusing this — if you found anything in the code,
        it is NOT speculation.**
  - Set `status` accordingly:
      * established / high confidence → `confirmed`
      * needs-confirmation → `open`
      * hypothesis-with-trace → `hypothesized`
      * speculation → `open`
  - Populate `evidence[]`:
      * For established: at least one `{{kind: "code", ref: "file:line"}}` entry.
      * For needs-confirmation: code ref + a note explaining why it's ambiguous.
      * For hypothesis-with-trace: best available reference + note.
      * For speculation: empty list.
  - For needs-confirmation facts, write a `pending_question` field — the actual
    question to ask the user in **{lang}**. Phrase it as "I see X in the code,
    is Y still true?" rather than "what is X?".

### Step 2b: Add knowledge categories beyond the code

The agent reading the code can never derive these alone. Always propose at
least a few of each:

  - **`rationale`** (1-3 facts) — for each magic number, hardcoded flag, or
    counter-intuitive behavior you spotted, propose ONE rationale fact asking
    *why* this decision exists. Evidence: the code ref where you spotted it.
    Priority: `needs-confirmation`. Status: `open`. The `pending_question`
    should be: "Vi no código que <X = 24h>. Existe razão de produto pra esse
    valor, ou é arbitrário?".

  - **`customer_question`** (2-3 facts) — propose facts of the form
    *"FAQ candidate: <pergunta provável de cliente/suporte>"*. Use your
    domain knowledge to imagine what end users would ask about this topic.
    Examples: "O que acontece se eu cancelar X enquanto está processando?",
    "Por que minha comissão veio menor que mês passado?". Evidence: empty
    (these are FAQ candidates, not code-derived). Priority:
    `needs-confirmation`. Status: `open`. The `pending_question` should be:
    "Listei 3 dúvidas que clientes finais provavelmente teriam. Quais são
    válidas, quais escapam? Adicione outras se vier à mente."

  - **`business_rule_unwritten`** (0-2 facts) — when you see behavior that
    looks like it should be configurable but isn't (e.g., a discount rule
    that only fires for one specific customer segment, with no flag), propose
    a fact asking if there's an unwritten business rule. Priority:
    `needs-confirmation`. Status: `open`. The `pending_question`: "Essa regra
    é decisão deliberada de produto ou padrão histórico que ninguém revisou?".

These facts have `evidence[]` either empty (for customer_question) or pointing
to code where you spotted the convention (for rationale / business_rule_unwritten).
They will become Q&A entries in the interview, and the answers will enrich the
guide with product/business context the code alone cannot provide.

### Step 3: Auto-audit the skeleton

Look at the skeleton you produced. Check:
  - Coverage: do you have facts about the *outcome*, the *trigger*, *invariants*,
    *edge cases*, *user vivência*? If a category is missing, ADD facts.
  - Tema size: if the topic is huge (would need >40 facts), propose `should_split`
    with 2-3 sub-slug suggestions.

## Output (STRICT JSON, no prose, no fences)

{{
  "title": "Final title in {lang} (may refine the working title)",
  "summary": "One-sentence summary in {lang}",
  "source_files": [
    "packages/api/src/billing/foo.ts",
    "packages/db/migrations/000123.sql"
  ],
  "facts": [
    {{
      "id": "F1",
      "kind": "trigger",
      "text": "Claim in {lang}",
      "confidence": "high",
      "priority": "established",
      "status": "confirmed",
      "evidence": [{{"kind": "code", "ref": "packages/api/src/foo.ts:42-58", "note": ""}}],
      "pending_question": null
    }},
    {{
      "id": "F2",
      "kind": "invariant",
      "text": "Claim in {lang}",
      "confidence": "low",
      "priority": "needs-confirmation",
      "status": "open",
      "evidence": [{{"kind": "code", "ref": "packages/api/src/bar.ts:120", "note": "Code suggests X but not enforced"}}],
      "pending_question": "Question in {lang}, framed as a confirmation"
    }}
  ],
  "should_split": null
}}

`should_split`, when not null:
  {{
    "reason": "Why this topic is too big (in {lang})",
    "suggested_slugs": ["sub-slug-1", "sub-slug-2"]
  }}

Output ONLY the JSON object.
"""


# -----------------------------------------------------------------------------
# REFLECT ON ANSWER — cross-check, update facts, surface contradictions
# -----------------------------------------------------------------------------

PROMPT_REFLECT_ON_ANSWER = """\
# Task: Reflect on the user's latest answer

The user just answered the pending question for fact `{fact_id}`:

**Fact text:** {fact_text}
**Pending question:** {pending_question}
**User answer:** {answer}

## Current state of other facts (compact)

{other_facts_compact}

## What to do

### Step 1: Cross-check with the code

Use Read/Glob/Grep to verify the user's answer against what the code actually does.
Look at the evidence already attached to this fact, expand if needed.

### Step 2: Classify the outcome

Pick ONE outcome:
  - `confirmed`: user's answer matches code and is consistent. Fact is now resolved.
  - `confirmed_with_correction`: user's answer is *mostly* right but you found a
    nuance worth recording (e.g., they said "uses payment_date" but code shows
    `due_date`). Include `correction_note` explaining the nuance, do NOT contradict
    the user openly — frame as enrichment.
  - `contradicted`: user's answer DIRECTLY conflicts with code. Surface this to the
    user with the code reference. Include `contradiction_note` and `code_ref`.
  - `needs_more`: answer is partial. Include `follow_up_question` in {lang}.

### Step 3: Detect coverage of other facts

Does this answer ALSO resolve other facts in the pending list (by topic, not just
literal coincidence)? List their ids in `covers_other_facts`.

### Step 4: Detect new facts that emerged

Did the answer reveal a fact you didn't have in the skeleton? List them as
`new_facts` with the same shape as in PROMPT_BUILD_SKELETON.

## Output (STRICT JSON, no prose, no fences)

{{
  "outcome": "confirmed",
  "correction_note": "",
  "contradiction_note": "",
  "code_ref": "",
  "follow_up_question": "",
  "covers_other_facts": ["F4", "F7"],
  "new_facts": []
}}

Output ONLY the JSON.
"""


# -----------------------------------------------------------------------------
# PROCESS CLOSING ANSWER — extract structure from the free-form catch-all
# -----------------------------------------------------------------------------

PROMPT_PROCESS_CLOSING_ANSWER = """\
# Task: Process the user's closing free-form answer

At the end of the interview for `{slug}` (domain: `{domain}`), the user was
asked: *"Algo que você gostaria de registrar e que ninguém perguntou ainda?
(pode falar livre, eu organizo)"*.

Their answer:

---
{closing_answer}
---

Your job: turn this into structured material for the guide.

## Rules

1. If the answer is short (a one-line note or trivial) → return empty `new_facts`
   and put the answer in `appendix_notes` verbatim. Don't invent facts.

2. If the answer is rich (mentions concrete behaviors, rules, edge cases,
   product decisions, FAQ hints): extract those as new Fact entries with the
   same shape used everywhere else (id starts at the next free F#, you can
   use `F?` and the CLI will renumber; pick `kind` from the standard list
   including `rationale`, `customer_question`, `business_rule_unwritten`,
   `closing_note`).

3. NEVER fabricate evidence. For facts derived from the user's verbal
   statement, use `evidence: [{{kind: "answer", ref: "closing", note: "..."}}]`.

4. Use `closing_note` kind when the content is meaningful but doesn't fit
   any other category (general guidance, gotcha, future intention).

5. Set `priority: "established"` and `status: "confirmed"` for everything you
   extract — the user already told you this. We're not asking again.

## Output (STRICT JSON)

{{
  "new_facts": [
    {{
      "id": "F?",
      "kind": "rationale" | "customer_question" | "business_rule_unwritten"
              | "closing_note" | "edge_case" | "invariant" | ...,
      "text": "Statement in {lang}",
      "confidence": "high",
      "priority": "established",
      "status": "confirmed",
      "evidence": [{{"kind": "answer", "ref": "closing", "note": "User stated X verbatim"}}]
    }}
  ],
  "appendix_notes": "Optional verbatim or summarized text to append to the guide's notes (in {lang})"
}}

If the answer was effectively empty (just "no", "nada", "ok", ""):

{{
  "new_facts": [],
  "appendix_notes": ""
}}

Output ONLY the JSON.
"""


# -----------------------------------------------------------------------------
# PRE-GENERATION SELF-AUDIT — every claim has evidence?
# -----------------------------------------------------------------------------

PROMPT_PREGEN_SELF_AUDIT = """\
# Task: Self-audit before generating the guides

You are about to write the v1 paired guides for `{slug}` (domain: `{domain}`).
Before generating, list each claim you intend to put in the guides and identify
those that lack solid evidence.

## Facts at hand

{facts_compact}

## What to do

For each fact:
  - If `priority = established` and `status = confirmed` with code evidence: OK.
  - If `priority = needs-confirmation` and `status = confirmed` (user answered): OK.
  - If `priority = hypothesis-with-trace`: it must go to "Pendências" with 🟡, NOT
    as an assertion. List it.
  - If `priority = speculation` (no evidence): drop silently, not even in Pendências.
  - If status is `contradicted`: skip it OR resolve it. Flag if unresolved.

Also identify:
  - Critical facts still `open` (priority = needs-confirmation, status = open) →
    these should have been answered. List them under `still_open_critical`.

## Output (STRICT JSON, no prose, no fences)

{{
  "ready_to_generate": true,
  "assertions": [
    {{"fact_id": "F1", "kind": "trigger", "summary": "...in {lang}", "evidence_summary": "..."}},
    ...
  ],
  "pendencias": [
    {{"fact_id": "F8", "summary": "...in {lang}", "reason": "weak evidence"}},
    ...
  ],
  "still_open_critical": [],
  "dropped_speculation": ["F12", "F13"]
}}

If `still_open_critical` is non-empty, set `ready_to_generate: false` and explain
in `block_reason` what's missing.

Output ONLY the JSON.
"""


# -----------------------------------------------------------------------------
# GENERATE GUIDES — produce the v1 .md files (REWRITTEN for facts)
# -----------------------------------------------------------------------------

PROMPT_GENERATE_GUIDES = """\
# Task: Write the v1 paired guides + interview record

You have a confirmed set of facts about `{slug}` (domain: `{domain}`). Write
three markdown files using your Write tool.

- Output language: **{lang}**
- Repo root: `{repo_root}`
- Docs directory: `{docs_dir}` (relative to repo root)
- Guides subdir: `{guides_subdir}` (when non-empty, paths become `{docs_dir}/{guides_subdir}/{domain}/...`)
- Slug: `{slug}`
- Title: `{title}`

## Files to create

1. **`{full_dir}/{slug}.md`** — `flavor: produto`
   - Audience: end-user, support, product. NO technical jargon.
   - 7 sections in order:
     1. Por que isso existe (Why this exists)
     2. Como o usuário vivencia (User experience)
     3. Conceitos-chave (Key concepts)
     4. Fluxos principais (Main flows — mermaid welcome)
     5. Casos do dia a dia (Day-to-day cases)
     6. Convivência com vizinhos (Neighbors interaction — when applicable)
     7. Veja também (See also)
   - DO NOT write a "next guide" / "próximo guia" section in the body.
     The next-step recommendation is metadata — it lives in the domain's
     `_index.md` and in the JSON output below, never in the guide itself.
   - Front-matter:
     ```yaml
     ---
     slug: {slug}
     domain: {domain}
     audience: ...
     flavor: produto
     source_files:
       - ...
     related_guides: []
     last_interview: {today}
     status: generated
     confidence_summary: "X facts confirmed, Y hypothesis"
     quality_score: 0.XX
     ---
     ```

2. **`{full_dir}/{slug}.tech.md`** — `flavor: tecnico`
   - Audience: dev, AI agent. Technical detail welcome.
   - 8 sections:
     1. Modelo de dados (Data model)
     2. Pontos de entrada (Entry points)
     3. Diagrama de transições (Transition diagram)
     4. Regras invariantes (R1, R2, ... numbered, with `file:line`)
     5. UI / cores / selos (UI / colors / badges)
     6. Pendências e melhorias mapeadas (Known gaps — includes 🟡 hypotheses)
     7. Material de referência (Reference material)
     8. Veja também (See also — other tech.md only)
   - Front-matter: same shape but `flavor: tecnico`.

3. **`{full_dir}/_meta/{slug}.interview.md`** — Q&A record
   - For each fact with `pending_question`, write:
     ```markdown
     **{{fact_id}}.** {{pending_question}}

     **Resposta:**

     {{answer}}

     ---
     ```

## Facts (with evidence)

{facts_full}

## Rules

- Every assertion in either guide must be traceable to a fact in the list above.
- Facts with `priority: hypothesis-with-trace` go to Pendências section (tech),
  prefixed with 🟡.
- Facts with `priority: speculation` are SILENTLY DROPPED. They do not appear anywhere.
- `confidence_summary` in front-matter: count facts by status (e.g., "18 facts
  confirmed, 2 hypothesis, 1 open").
- `quality_score`: precomputed value — use `{quality_score}`.

## Output

After writing the 3 files with your tools, return ONLY this JSON:

{{
  "files_written": [
    "{full_dir}/{slug}.md",
    "{full_dir}/{slug}.tech.md",
    "{full_dir}/_meta/{slug}.interview.md"
  ],
  "summary": "One-paragraph summary in {lang}",
  "next_recommendation": {{
    "slug": "natural-next-slug",
    "domain": "{domain}",
    "reason": "Why this is the natural next step (in {lang})"
  }}
}}

Output ONLY the JSON.
"""


# -----------------------------------------------------------------------------
# POST-GENERATION EVALUATIONS (3 dimensions in Phase 1)
# -----------------------------------------------------------------------------

PROMPT_EVAL_PRODUCT_CLARITY = """\
# Task: Evaluate the product-flavored guide for clarity

You are reading **as an end-user of the SaaS** (or support agent, or product
manager). You are NOT a developer.

## File to evaluate

Read `{produto_path}` carefully. Use your Read tool.

## What to check

For each issue you find, classify severity:

- **blocker**: guide states something that contradicts the source code evidence
  (you may need to spot-check). Must fix before publishing.
- **evidence-based**: detectable problem grounded in something explicit:
  jargon vazado from code, mention of a column/enum/function name, broken
  cross-reference, missing front-matter field, narrative jump.
- **subjective**: stylistic suggestion (tone too formal, paragraph too long,
  better word choice). These are auto-fixable.

## Output (STRICT JSON, no prose, no fences)

{{
  "summary": "One-line in {lang}",
  "issues": [
    {{
      "id": "I1",
      "severity": "evidence-based",
      "message": "Guide cites 'commission_rate' (technical jargon). End-user wouldn't know that.",
      "location": "{produto_path}:42",
      "auto_fix_available": true,
      "patch": "Substituir 'commission_rate' por 'taxa de comissão'."
    }}
  ]
}}

Output ONLY the JSON. Empty issues array if all clean.
"""


PROMPT_EVAL_TECH_COMPLETENESS = """\
# Task: Evaluate the tech-flavored guide for completeness

You are reading **as a developer new to this codebase**, who needs the guide
to onboard them.

## File to evaluate

Read `{tech_path}`. Use your Read tool.

## What to check

- Invariants numbered (R1, R2, ...) — each with `file:line`?
- Edge cases mentioned (rollback, race, timeout, concurrent edit)?
- Diagram present where it'd help?
- `source_files` in front-matter complete (10+ entries for non-trivial topics)?
- Pendências section captures known gaps (🟡)?

Same severity scheme as product evaluation.

## Output (STRICT JSON, no prose, no fences)

Same shape as PROMPT_EVAL_PRODUCT_CLARITY.

Output ONLY the JSON. Empty issues array if all clean.
"""


PROMPT_EVAL_BASE_COHERENCE = """\
# Task: Evaluate the new guide against the existing knowledge base

You are checking whether this guide is consistent with what is already documented
in the project.

## Files to read

- **New guide (produto)**: `{produto_path}`
- **New guide (tech)**: `{tech_path}`
- **Existing guides in the same flavor that may relate**:

{related_guides_compact}

- **Glossary** (if present): `{glossary_path}`

## What to check

- Terms diverging from the glossary (or worth adding to it)?
- Affirmations that contradict an existing guide?
- "Veja também" sections — does the new guide link to obvious related guides?
- Reverse-link: would another guide benefit from citing this new one?

Output same shape as the other evaluators. For reverse-link findings, use
`type: "reverse_link_suggestion"` in the issue message — phase-1 CLI will
funnel these to the inbox separately.

Output ONLY the JSON.
"""


# -----------------------------------------------------------------------------
# REVERSE-LINK SWEEP — after human approves, propose entries in other guides
# -----------------------------------------------------------------------------

PROMPT_REFINE_GUIDE = """\
# Task: Refine an existing guide based on a free-form instruction

The user has an existing pair of guides (`produto.md` + `tech.md`) and wants
to apply a refinement. They wrote the instruction in their own words; you
need to interpret it, decide what to do (rewrite a section, add a use case,
re-check code, simplify tone, etc.), and produce surgical edits.

## Inputs

- Guide slug: `{slug}`
- Domain: `{domain}`
- Output language: **{lang}**
- Repo root: `{repo_root}`
- Style guide for produto-flavored content:

---
{style_md}
---

## Current state of the guides

### produto.md  (path: `{produto_path}`)

```markdown
{produto_content}
```

### tech.md  (path: `{tech_path}`)

```markdown
{tech_content}
```

## Compact fact context

{facts_compact}

## User instruction

---
{user_instruction}
---

## What to do

1. Parse the instruction. It can be:
   - Add content (new section/case/example/diagram)
   - Reformulate content (change tone, fix wording, simplify)
   - Remove content (drop a confusing reference, prune a section)
   - Cross-check code (use Read/Glob/Grep — confirm or correct claims)
   - Mixed combinations of the above

2. Decide if you need to read code. If the instruction asks you to verify
   or update technical claims, USE THE TOOLS. If it's purely a wording/tone/
   structure change, you don't need to.

3. Produce SURGICAL EDITS as a list of `changes`. Each change is one
   exact substring replacement in one file. Rules:
   - `old` must appear EXACTLY ONCE in the target file (verbatim, including
     whitespace, headings, blank lines). If you can't find a unique anchor,
     widen the `old` to include surrounding lines until it's unique.
   - `new` is what replaces it.
   - To add content: include the line before AND after the insertion point in
     `old`, with `new` containing the same surrounding lines + your insertion.
   - To remove content: `old` is the text to remove (with anchoring context),
     `new` is what remains.
   - One file per change. Multiple changes in the same file are fine — they
     apply in order.

4. NEVER touch:
   - YAML front-matter (slug, domain, status, source_files, etc.). The CLI
     manages these. Don't include them in `old` or `new`.
   - `_index.md` files. The CLI rewrites them automatically.

5. Prefer the produto.md style guide above when refining the product guide.
   Stay technical and code-anchored on tech.md.

## Output (STRICT JSON)

{{
  "summary": "One-paragraph in {lang} explaining what you did and why",
  "changes": [
    {{
      "file": "packages/docs/guides/<domain>/<slug>.md",
      "old": "exact substring (unique in file)",
      "new": "replacement",
      "reason": "why this change in {lang}"
    }}
  ],
  "code_checks_performed": [
    {{
      "what": "Verified that the auto-cancellation rule still uses 24h",
      "where": "packages/api/src/services/contracts/autoTerminationService.ts:42",
      "outcome": "confirmed / corrected"
    }}
  ]
}}

If the instruction is impossible (e.g., refers to content that doesn't exist
in the guide and can't be added meaningfully), return:

{{
  "summary": "Brief explanation in {lang} of why no changes were made",
  "changes": [],
  "code_checks_performed": []
}}

Output ONLY the JSON object.
"""


# -----------------------------------------------------------------------------
# REVERSE-LINK SWEEP — after human approves, propose entries in other guides
# -----------------------------------------------------------------------------

PROMPT_REVERSE_LINK_SWEEP = """\
# Task: Propose reverse cross-links

The user just approved a new guide. Now you propose reverse links — entries
to add in OTHER guides' "Veja também" sections so the base becomes
bidirectionally navigable.

## New guide

- Slug: `{slug}`
- Domain: `{domain}`
- File (produto): `{produto_path}`
- File (tech): `{tech_path}`

## What to do

Read the new guide's "Veja também" section. For each guide it cites:
  - Read that target guide.
  - Check whether the target already cites the new guide back.
  - If not, propose a one-bullet entry to add to that target's "Veja também"
    section, explaining (1 sentence) why the reader would visit the new guide.

Only propose for guides of the **same flavor** (produto → produto, tech → tech).

## Output (STRICT JSON, no prose, no fences)

{{
  "proposals": [
    {{
      "target_path": "guides/projetos/parceiros-do-projeto.md",
      "target_slug": "parceiros-do-projeto",
      "bullet": "- [Pagamento de Repasses](../financeiro/pagamento-de-repasses.md) — explica como as comissões definidas aqui são executadas no fluxo financeiro."
    }}
  ]
}}

Output ONLY the JSON. Empty proposals array if all reverse-links already exist.
"""


# =============================================================================
# LEGACY (v0.1) PROMPTS — kept for backwards-compatible import only
# =============================================================================
#
# The v0.1 CLI flow (interview.py) imports PROMPT_GENERATE_INTERVIEW and
# PROMPT_COVERAGE_CHECK from this module. Phase B keeps them present so the
# old code path still imports without breaking. Phase C removes the
# legacy CLI flow and these can be deleted.

PROMPT_GENERATE_INTERVIEW = """\
# Task: Prepare initial interview for a new guide

You will help create a new guide for the LiveDocs project at `{repo_root}`.

## Guide info
- Slug: `{slug}`
- Domain: `{domain}`
- Title (working): `{title}`
- Output language: **{lang}**
- Docs directory: `{docs_dir}`

This prompt is DEPRECATED — use PROMPT_BUILD_SKELETON instead.

## Output format

{{
  "title": "...",
  "summary": "...",
  "source_files": [],
  "blocks": [
    {{"id": "A", "topic": "...", "questions": [{{"id": "A1", "text": "..."}}]}}
  ]
}}
"""


PROMPT_COVERAGE_CHECK = """\
# Task: Did this answer cover other pending questions?

DEPRECATED — use PROMPT_REFLECT_ON_ANSWER instead.

The user just answered question `{question_id}` ("{question_text}") with:

> {answer}

## Pending questions

{pending_block}

## Output (STRICT JSON, no prose, no fences)

{{"covered": [], "partial": []}}
"""


PROMPT_DETECT_DOMAINS = """\
# Task: Suggest documentation domains for this codebase

DEPRECATED — use PROMPT_PARSE_INTENT with the user's free-text and existing
domains list to drive guide selection now.

Output (STRICT JSON):

{{"domains": []}}
"""
