# Phase 0 — Guidance

## Goal
Establish two things before any other work happens:

1. **Language** — what language the entire run will use (skill messages,
   interview, generated docs). See `references/language-handling.md`.
2. **Guidance** — free-form context from the maintainer about the product:
   who they are, what the system does, what it's for, references, hints.
   This text feeds every later LLM call so it MUST be captured carefully.

## What to do

### Step 1 — Decide and confirm the run language

Detect a candidate language by inspecting the codebase. Heuristics
(use as many as available, weight by signal strength):

- **i18n keys** in the codebase — if `t('...')` calls dominantly resolve
  to one language file (e.g. `locales/pt-BR.json` has many keys and is
  the default), use that.
- **Comments and identifiers** — read 5–10 random source files; if
  variable names, comments, and inline strings are in one natural
  language, weight it.
- **README and package metadata** — `README.md` headline + package
  description.
- **Existing docs/** — if any prior documentation exists, look at it.

Pick the strongest candidate. If signals are mixed or absent, default
to **English**.

Ask the user (rendered in **the language you detected** for friendliness;
if you detected English, ask in English; etc.):

> I'll run the bootstrap in {detected-lang}. That means:
> - The questions I'll ask you during the interview will be in {detected-lang}.
> - The generated `.md` and `.tech.md` files will be in {detected-lang}.
> - The state file (`.livedocs/state.md`) will be in {detected-lang}.
>
> Confirm, or tell me which language to use instead (use BCP-47 codes
> like `pt-BR`, `en`, `es-AR`).

Persist the chosen language in `.livedocs/state.md` as the `Lang:` field
(see `references/state-format.md`). From here on, treat this language
as `{lang}` everywhere.

### Step 2 — Ask for product context (guidance)

Render the following prompt in `{lang}` — translate naturally, don't
copy-paste English to a pt-BR user:

> Before we start, tell me a bit about the context:
>
> Who you are, what the system does, what it's for. You can paste
> references, general instructions, or anything that helps the AI
> during documentation.
>
> **How to deliver:**
> - Paste it here in the chat (multi-line is OK), OR
> - Edit `.livedocs/guidance.md` and tell me when you've saved.
>
> Empty text is also acceptable — the run will rely more on code reading.

### Step 3 — Wait for the user's response

Don't proceed without one of:
- Text in the chat (multi-paragraph OK)
- User says they created/saved the guidance file
- User explicitly says "no guidance" / "empty"

### Step 4 — Persist guidance to disk

Before saving, give the user a one-time privacy heads-up (render in
`{lang}`):

> Heads-up: this guidance text will be included in many later LLM
> calls, including to sub-agents. Don't paste secrets, API keys, real
> customer data, or anything you wouldn't want to land in a provider
> log. Want to edit before I save?

If the user wants to edit, let them re-paste or edit `.livedocs/guidance.md`
and signal "saved" again. Otherwise, persist as-is.

Always write `.livedocs/guidance.md` with the captured text (or an
empty-file marker if none). This is the source of truth for later phases.

```bash
mkdir -p .livedocs
cat > .livedocs/guidance.md <<'EOF'
<USER TEXT HERE>
EOF
```

### Step 5 — Initialize state.md if it doesn't exist

Use the template from `references/state-format.md`. Mark phase 0 as
"completed", set "Current phase" to "1 (scan)", record the chosen
`Lang:`.

### Step 6 — Ask consent to advance (render in {lang})

> Guidance captured. Next phase is the code **scan**:
> - Runs `graphify extract` if available (semantic graph, uses LLM)
> - Reads routes, i18n keys, and models from the code
> - Doesn't call the LLM directly (graphify does, but it's its own thing)
>
> Can I proceed?

## Validation

Before leaving phase 0, confirm:
- `Lang:` recorded in `.livedocs/state.md`
- `.livedocs/guidance.md` exists on disk
- `.livedocs/state.md` exists and lists phase 0 as completed
- User explicitly OK'd advancing to phase 1

## Edge cases

- **User pastes a 10k-char manifesto**: accept it; warn that very long
  guidance increases per-call cost. Don't truncate.
- **User can't articulate**: offer to ask 3-4 short questions instead.
- **User says "read my README"**: read it, summarize in 5-10 lines,
  ask them to confirm or amend. The CONFIRMED summary becomes the
  guidance — not the raw README.
- **User wants two languages** (e.g. interview in English but docs in
  pt-BR): NOT supported today. Explain the constraint (single source of
  truth, translation as a later phase). Recommend picking the language
  the final product speaks. See `references/language-handling.md`.
- **Mixed-language codebase** (e.g. backend in English, UI in pt-BR):
  the choice is the language of the **product**, not the code. UI
  language wins because that's what the docs reflect.
