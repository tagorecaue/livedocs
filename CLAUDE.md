# CLAUDE.md — Development guide for LiveDocs

> Instructions for any agent (Claude Code, Codex, Hermes, etc.) or human
> contributor working **on this repo itself** — not for users running the
> skill on their own project.
>
> If you're a user looking to document a SaaS, see
> `skills/livedocs-bootstrap/README.md` instead.

## What this repo is

LiveDocs is a **skill-only project**. There is no binary, no CLI, no
runtime. The product is a folder of markdown files an agent reads and
follows. Everything that matters lives under:

```
skills/livedocs-bootstrap/
├── SKILL.md                 # entry point + core principles
├── README.md                # public-facing intro
├── CHANGELOG.md             # version history
├── fixtures/mini-saas/      # smoke-test fixture
└── references/              # per-phase + per-format reference files
```

Repo root has:
- `README.md` — public entry point. Carries product framing and the
  "Concepts" rationale section. This is where the canonical
  vocabulary lives now (previously in `CONTEXT.md`, since absorbed).
- `.claude-plugin/plugin.json` — manifest that makes the repo
  installable via `npx skills@latest add tagorecaue/livedocs`. Lists
  the skills under `skills/` that get exposed. **Update this when
  adding a new top-level skill.**
- `docs/` — long-form material referenced from README but kept out of
  it to control length (today: `case-study.md` with the real-run
  per-phase breakdown). Add a file here when a section grows past
  ~50 lines and starts overweighting the README.
- `.spec/` — implementation plans for the skill itself (not for user-
  documented systems).

Anything else (Python code, CLI utilities, glossaries, ADRs for
features that don't exist yet, etc.) **does not belong here** and has
been deliberately removed. When the skill grows toward v2.0 features
(publication, incremental maintenance), `docs/adr/` comes back — but
we write decisions as they're made, not before.

## How to contribute changes

This repo is in **validation through dogfooding**. External PRs aren't
accepted yet, but if you're forking or running it through your own
agent and want to improve the skill, the workflow is:

### 1. Don't bypass the skill itself

If you discover an issue while running the skill, **patch the skill**
(`SKILL.md` or a reference file), don't work around it in your
project's `.livedocs/`. The point of the skill is to encode lessons;
silent workarounds defeat the purpose.

### 2. Bump `version` in SKILL.md when you change semantics

`skills/livedocs-bootstrap/SKILL.md` has a YAML frontmatter with
`version: X.Y.Z`. Follow SemVer:

- **MAJOR** — breaks article format, state schema, or sub-agent JSON
  contracts. Existing `.livedocs/state.md` from older runs may not
  resume.
- **MINOR** — adds a phase, a core principle, a reference file. Old
  runs still work.
- **PATCH** — clarifications, examples, pitfall notes. Pure docs.

When you bump, also add an entry to `CHANGELOG.md` with a date, a
brief rationale, and which files moved.

### 3. Always English in the skill itself

Skill internals (SKILL.md, all references, sub-agent prompts you
compose) are always English. The OUTPUT language is whatever Phase 0
locks in via `{lang}`. If you find a non-English string hardcoded in
the skill, it's a bug — patch it.

See `skills/livedocs-bootstrap/references/language-handling.md` for the
full contract. **Read it before changing anything that produces user-
visible text.**

### 4. Commit per logical change

The skill itself follows the same discipline it imposes on user
projects: one logical change per commit, clear prefix.

Suggested prefixes:

- `skill(SKILL.md): <what>` — top-level skill changes
- `skill(phase-N): <what>` — phase reference changes
- `skill(<format>): <what>` — language-handling / privacy / pending-
  questions / etc
- `skill(fixture): <what>` — fixture changes
- `docs(plan): <what>` — `.spec/` plan changes
- `chore: <what>` — repo hygiene

### 5. Test your change against the fixture

Before declaring a change done, run the skill on
`skills/livedocs-bootstrap/fixtures/mini-saas/`:

```bash
cp -r skills/livedocs-bootstrap/fixtures/mini-saas /tmp/livedocs-smoke
cd /tmp/livedocs-smoke
# open your agent here and invoke the skill
```

The fixture's README documents expected outcomes per phase. If your
change regresses any of them, fix before committing.

For changes that only affect Phase 4+ (drafts onward), running just
Phase 0–3 in the fixture is enough to catch basic regressions.

### 6. Update README "Concepts" section only with intent

The README's "Concepts" section is the product's canonical
vocabulary — capability, journey, screen, two flavors, pending
questions, isolated context, guidance text, code capture point. Don't
edit it just to align with code. Edit it when a **product** decision
changes — the distinction between "capability" and "journey" is
product-level; how those concepts get serialized to disk is
implementation-level. If you catch yourself updating Concepts to
match an implementation artifact, you're probably doing it backwards.

## Working on this repo with a coding agent

### As a fork maintainer

If you forked this repo to add features, follow the agent workflow
below. Keep your fork's `livedocs-bootstrap` branch in sync with
upstream so it's easy to PR back once contributions open.

### Branch model

Main branch: `livedocs-bootstrap` (this is the dev branch and what
external clones see; `main` was retired when the project went
skill-only).

### Recommended agent setup

The skill is best maintained by an agent with:

- Sub-agent / Task primitives (so reviewing changes across many
  reference files in one session is feasible).
- File write access.
- Shell access (for git, smoke tests).

Tested combinations: Claude Code (Sonnet 4 / Opus class), Hermes
(Opus 4.7), Codex CLI. Smaller models drop quality.

### Conventions the agent should follow when editing the skill

1. **Read `SKILL.md` first**, every session, even if you wrote it last
   week. Its core principles (1–13) are the contract for everything
   else.

2. **Read `language-handling.md`** before touching any reference file
   that produces user-visible text. The two-layer rule (English skill,
   `{lang}` output) is easy to violate accidentally.

3. **Read `privacy.md`** before touching anything that decides what a
   sub-agent reads. The denylist is the contract.

4. **Read `pending-questions.md`** before changing how Phase 4 / 5 /
   5.5 / 6 deal with questions. The INTENT-or-EXPERIENCE principle is
   the discriminator that prevents the whole flow from degenerating
   into "ask the human everything".

5. **No new dependencies**. The skill is markdown only. If you find
   yourself wanting to add a Python script, a npm package, or a Docker
   image — stop. Push the logic into the skill as agent instructions
   (the agent can run `execute_code` or shell commands inline).

6. **Examples in references stay generic**. Use neutral domains
   (recurring billing, project management, contracts). Don't introduce
   examples from real client systems — those leak product context the
   skill can't validate.

## Roadmap (very rough)

Not committed dates, just intent:

- **v1.4** — incremental maintenance mode (re-run skill on a project
  that already has `docs/`, detect code changes via git diff, update
  only affected articles).
- **v1.5** — state migration to JSON with a published schema (current
  state is markdown for human-edit ergonomics; JSON helps tooling).
- **v2.0** — Chatwoot / generic help-center publication phase.
  Currently the skill produces local `docs/` only.

See `.spec/skill-oss-prep/plano-skill-oss-prep.md` for the current
in-flight plan and what's blocking each item.

## Project image (banner / social card)

The repo doesn't ship with an image yet. If you're regenerating one,
the prompt that fits the project's voice is:

```
A minimalist horizontal banner (1280×640 for GitHub social card, or
1920×480 for repo header). Centered: a stack of three or four
overlapping markdown documents drawn in clean line-art, slightly
askew, with subtle highlight on a few inline text blocks to suggest
content. To the left or above, a small node-graph fragment (5-7
circles connected by lines) — a hint at the underlying code graph
the skill uses. Color palette: deep slate / charcoal background,
warm off-white documents, single accent color (a muted terracotta
or amber) for the highlighted text blocks and graph edges. No
gradients, no glow, no 3D depth — flat, technical, calm. Typography
optional: "LiveDocs" in a quiet sans-serif (Inter, IBM Plex) at the
top-left, very small. No tagline, no logo, no people, no screen
mockups. The feeling should be "engineering notebook", not "SaaS
landing page".
```

Tools you can use to generate it:

- **GPT-4o / Imagen 3 / Midjourney** via your usual UI.
- **ComfyUI / SDXL** locally with a flat-design LoRA if you have one.
- **An illustrator** (the prompt above translates well to a brief).

Save the result at `assets/banner.png` (1280×640 for the social card
slot; GitHub repo settings → Social preview → Upload). Don't commit
larger than 1 MB; use a PNG with reasonable compression or convert to
WebP if the tool supports it.

If you're using a generation tool and the output looks like
SaaS-landing-page slop (gradients, glow, 3D documents floating in
space, abstract people), reject and re-prompt with stronger emphasis
on "flat, technical, calm, engineering notebook".

## License

AGPL-3.0-or-later. Forks must open. See `LICENSE`.
