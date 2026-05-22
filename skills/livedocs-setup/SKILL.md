---
name: livedocs-setup
description: |
  Pre-flight setup for LiveDocs. Run once per machine after installing the
  livedocs skills. Checks that `graphify` is installed and on PATH (offers
  to install it via uv or pipx if missing), and verifies the user has a
  capable coding agent environment. Use when the user says "set up
  livedocs", "/setup-livedocs", "prepare livedocs", or right after they
  install the skill for the first time.
version: 1.0.0
author: Tagôre Cardoso + LiveDocs
---

# LiveDocs setup

You are doing a one-time pre-flight check for the LiveDocs project.
Goal: leave the user's machine ready to run `livedocs-bootstrap` on
any of their projects.

Do not run the actual bootstrap from here. That's a separate skill,
invoked per-project. Your job is environment only.

## What to do, in order

### Step 1 — Greet and explain (render in the user's language)

> I'll set up LiveDocs on this machine. Quick environment check —
> mainly verifying that `graphify` (the code-graph tool we use in
> Phase 1) is installed. If it's missing, I'll offer to install it.
> Nothing destructive; I'll confirm before running anything. OK?

Wait for confirmation.

### Step 2 — Detect operating system

```bash
uname -s
```

Branches:

- `Linux` → Linux path below
- `Darwin` → macOS path below
- `MINGW*` / `MSYS*` / `CYGWIN*` → tell the user to use WSL2:
  > LiveDocs needs a Unix-like environment for `graphify` and the
  > skill's shell calls. On Windows, run this inside WSL2 (Ubuntu
  > recommended). Re-invoke me from there.
  > Exit gracefully.

### Step 3 — Check if `graphify` is already installed

```bash
which graphify 2>/dev/null && graphify --version 2>/dev/null
```

Three outcomes:

1. **Installed AND version prints** → tell the user:
   > Found `graphify <VERSION>` at `<PATH>`. You're good to go.
   > Skip to Step 6.

2. **`which` returns nothing** → not installed. Go to Step 4.

3. **`which` returns a path but `--version` fails** → broken install.
   Tell the user:
   > Found `graphify` at `<PATH>` but `--version` failed. Likely a
   > broken install. Want me to reinstall it (Step 4)?
   > On confirmation, proceed to Step 4.

### Step 4 — Choose an install method

Probe for installers in this order:

```bash
which uv && uv --version
which pipx && pipx --version
which pip3 && pip3 --version
```

Pick the first one available and prefer them in this order:

| Tool | Command |
|---|---|
| `uv` | `uv tool install graphifyy` |
| `pipx` | `pipx install graphify` |
| `pip3` | `pip3 install --user graphify` (last resort — pollutes user site-packages) |

If NONE are installed, tell the user:

> You don't have `uv`, `pipx`, or `pip3` on this machine. The
> recommended installer is `uv`. Install it with:
>
>   curl -LsSf https://astral.sh/uv/install.sh | sh
>
> Then re-invoke me. Or, if you prefer, install `graphify` yourself
> by another means and re-run setup.

Exit gracefully.

### Step 5 — Confirm and install

Tell the user EXACTLY what you're about to run:

> I'll run: `uv tool install graphifyy`
> This installs the `graphify` CLI tool from PyPI into a uv-managed
> environment. About 30-60 seconds. OK to proceed?

On confirmation, run it. After completion:

```bash
graphify --version
```

If it prints a version: success. Tell the user:
> ✓ Installed `graphify <VERSION>`. PATH is set up correctly.

If `graphify` still isn't found, common causes:

- **`uv`**: the user's shell needs to source `~/.local/bin` (uv tools
  default there). Suggest: `export PATH="$HOME/.local/bin:$PATH"`
  and add to `~/.bashrc` / `~/.zshrc`.
- **`pipx`**: same — `pipx ensurepath` then restart the shell.
- **`pip3 --user`**: depends on the platform. Suggest the user check
  `python3 -m site --user-base`/bin.

Resolve PATH issue with the user before continuing.

### Step 6 — Quick sanity check on the coding agent

You (the agent running this skill) ARE the agent that will run the
bootstrap. Sanity check yourself:

- Can you spawn sub-agents (Task tool, delegate_task, equivalent)?
- Can you run shell commands?
- Can you write files?

Report your findings honestly:

> LiveDocs needs an agent that can:
> - spawn sub-agents (Task / delegate)
> - run shell commands
> - write files
>
> I'm running on <AGENT NAME> and I support all three.  ✓
>
> (or, if any are missing:)
>
> I don't support <missing capability>. LiveDocs Phase 4 in particular
> needs sub-agent spawning to draft articles in parallel — without it,
> Phase 4 still works sequentially but will be slow on large
> projects. You can either continue and accept the limitation, or run
> LiveDocs from a different agent (Claude Code, Hermes Opus, Codex CLI
> are verified to work).

### Step 7 — Confirm done and point to next step

Render in the user's language:

> Setup complete. To document a project:
>
>   1. `cd` into the project's repo.
>   2. Tell me: "Use the livedocs-bootstrap skill to document this project."
>
> I'll walk you through 8 phases of bootstrap. State persists in
> `.livedocs/state.md` — you can interrupt and resume any time.
>
> First-run reading (optional):
>   - Concepts:        docs/concepts.md
>   - Operating notes: docs/operating-notes.md
>   - Real case study: docs/case-study.md

End the skill here. Do NOT auto-invoke the bootstrap.

## Failure modes — what to do

- **User refuses graphify install**: it's a soft dependency. Bootstrap
  Phase 1 detects its absence and warns gracefully — extractors for
  routes/i18n/models still produce a usable taxonomy signal. Tell
  the user this, then exit.

- **User on Windows without WSL**: graphify works in native Windows
  but several shell calls inside the skill assume POSIX. Strongly
  recommend WSL2. If they insist on native Windows, warn and proceed —
  expect Phase 1 / Phase 5.5 to fail on shell commands.

- **Slow network or PyPI timeout**: `uv tool install` can hang on
  bad networks. Tell the user to retry; offer to use a mirror if
  they're in a region where PyPI is slow.

- **Conflicting `graphify` on PATH**: there's a hypothetical name
  conflict (some other tool called `graphify`). If `graphify --help`
  output looks nothing like a code-graph tool, alert the user and
  ask which one they want.

## What you DO NOT do here

- Don't create `.livedocs/` in any project directory.
- Don't read or scan project code.
- Don't ask the user about their codebase.
- Don't start Phase 0 of the bootstrap.

This skill is one-shot environment prep. The bootstrap is its own
skill, invoked per-project, with its own consent flow.
