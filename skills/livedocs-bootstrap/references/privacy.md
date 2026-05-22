# Privacy and context boundaries

> What enters and what does NEVER enter the context of any sub-agent
> spawned during this bootstrap.

## Why this matters

This skill spawns many sub-agents and reads many files. With careless
defaults, secrets, customer data, or audit-sensitive content can end
up in LLM prompts and provider logs. Even with privacy-respecting
providers, leaking secrets into a transcript is a one-way action — you
can't un-leak.

This is an open-source skill running on user-owned repositories. We
assume some users will run it against codebases with real production
keys checked in by mistake, `.env` files committed years ago, or
fixtures with real PII. The skill must default to the safe side.

## Hard denylist — never reach a sub-agent

The following paths are NEVER included in any sub-agent's reading scope,
regardless of phase, regardless of whether they would help. The
orchestrator filters them out before composing prompts:

- Any path matching `.env`, `.env.*` (e.g. `.env.local`, `.env.production`)
- Any path under `secrets/`, `secret/`, `credentials/`, `keys/`
- Any file named `*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`,
  `*.keystore`, `id_rsa`, `id_ed25519`, `*.kdbx`, `*.gpg`, `*.asc`
- Any path matching `.aws/`, `.gcloud/`, `.kube/config`, `.ssh/`
- Anything ignored by `.gitignore` (treat as "the project chose to
  hide it; respect that")
- Anything under `.git/` (objects, hooks, packed refs)
- Anything under `node_modules/`, `vendor/`, `.venv/`, `dist/`,
  `build/`, `__pycache__/`, `target/`, `.next/`, `.nuxt/`

If a sub-agent asks for a denied file via tool calls, the orchestrator
denies the read and tells the sub-agent: `"Path <X> is in the privacy
denylist. If you need information from there, mark as needs_human."`

## Soft denylist — agent should avoid unless asked

Possible high-noise / high-risk paths that often contain raw data, not
code:

- `fixtures/`, `seeds/`, `test-data/`, `mocks/`, `samples/`
- `migrations/seeds/` (DB seed scripts can contain real-looking records)
- `*.sql` dumps named like `*-dump.sql`, `*-prod.sql`
- `logs/`, `*.log`
- Anything > 1 MB single-file (likely data, not code)

Sub-agents reading these must justify the read (e.g. "checking the
schema of a fixture to understand the data model"). If purely
incidental, skip.

## What the user pastes IS the user's call

Free-form user inputs (Phase 0 guidance, interview answers in Phase 6,
prior `.interview.md` files in Phase 4) are user-authored and may
contain whatever the user chose to share. The skill does not filter
those — censoring user-typed content silently is a worse failure than
including it.

But: in **Phase 0**, after collecting guidance, the agent SHOULD say
(render in `{lang}`):

> Heads-up: this guidance text will be included in many later LLM
> calls, including to sub-agents. Don't paste secrets, API keys, real
> customer data, or anything you wouldn't want to land in a provider
> log. Want to edit before I save?

This is a one-time warning. The user is in charge after that.

## Sub-agent reading scope — explicit, not "read whatever"

A sub-agent's prompt must include an explicit reading scope, not
"read what you need". The orchestrator decides the scope from:

- Phase 4 / 5 / 7 article work: `code_anchors` of the target article
  PLUS the article's own draft files PLUS — only when needed — files
  the article cross-references. Sub-agent stays within these.
- Phase 5.5 triage: the capability's articles + the project codebase
  (read-only) MINUS the denylists above. The sub-agent has search
  tools (grep) so it can find what it needs without an unbounded read.
- Phase 1 scan: globs are explicit (`pages/**/*.vue`, `prisma/schema.prisma`).
  Sub-agent reports what it found; doesn't read outside the glob.

The orchestrator NEVER tells a sub-agent "you have full repo access".
Even when it's true at the tool-permission level, narrow scope keeps
the sub-agent focused and the LLM bill smaller.

## What about the LLM provider?

Out of scope for this skill. The user chose their provider when they
chose their agent platform (Claude Code, Codex, Cursor, etc.). Privacy
posture of that provider is their concern. This skill's job is to
avoid making things WORSE by leaking content that the user wouldn't
have shared otherwise.

## Recommended user-side checks

The skill can suggest (render in `{lang}`, during Phase 0):

> A few quick checks before we start:
> - `git ls-files | grep -E '\\.env(\\.|$)'` — any committed `.env`? Move to `.env.example`.
> - Any committed `*.pem`, `*.key` files? Rotate and remove before running.
> - Any `fixtures/` with real-looking PII? Consider scrubbing first.
>
> Not blocking; just a suggestion. Continue?

This is optional and may be skipped — but it costs nothing and prevents
the most common embarrassments.

## When in doubt

If a path is ambiguous (the user has a `secrets-config.ts` file that
ISN'T secrets, it's config FOR managing secrets), the agent reads its
NAME pattern, sees risk, and asks the user inline:

> The file `secrets-config.ts` matches the privacy denylist pattern.
> Is it safe to include in context, or should I skip it?

One question, one answer, recorded in state under
`privacy_overrides:` so subsequent phases inherit the decision.

## Migration note

This is a **principle**, not a runtime enforcement. The orchestrator
must apply it actively — there is no plugin scanning the LLM context.
A sub-agent receives only what the orchestrator decides to send. So
the discipline is in the prompt-composition step, not in some
imagined sandbox.
