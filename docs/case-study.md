# Case study — a real bootstrap, end-to-end

Concrete example so you know what to expect from `livedocs-bootstrap`.
This is what happened on a real Brazilian SaaS the author dogfooded
the skill on — a mid-sized production codebase (~38k semantic nodes
per `graphify`), full backend + Vue 3 frontend, ~3 years of code,
multi-tenant.

The agent was [Hermes](https://github.com/NousResearch/hermes) running
on Anthropic's Opus 4.7. Total wall-clock: roughly a working week,
mostly attended; the long parts were dinner-and-come-back ones.

## Per-phase breakdown

| Phase | What the agent did | Numbers from this run |
|---|---|---|
| 0 — Guidance | Asked the maintainer to dump context, detected pt-BR | ~10 min, $0 |
| 1 — Scan | Ran `graphify extract`, parsed routes/i18n/models | graphify run ~25 min; 139 routes, 272 i18n keys, 18 models; graph 38k nodes |
| 2 — Taxonomy | Proposed 22 capabilities + 6 journeys from the signals | 1 LLM call, ~$0.40 |
| 3 — Review | Maintainer split / merged / renamed via interactive menu | ~30 min of human time, a handful of split calls |
| 4 — Drafts | 1 sub-agent per article, all in parallel batches | 76 articles × 2 flavors = 152 files; ~$74 total |
| 5 — Stitch | Cross-links resolved, terminology harmonized | ~$20; flagged a few contradictions as pending questions |
| **5.5 — Triage** | **Re-checked 314 pending questions against the code** | **120-ish auto-answered with file:line evidence; ~28 articles auto-patched; ~150 questions reached the human** |
| 6 — Interview | Maintainer answered the 150 in thematic blocks (A–F) | ~3 hours of human time, two sittings; vague answers welcomed and saved |
| 7 — Global update | Affected articles re-opened and rewritten with the answers | ~$15; ~30 articles touched |

## Totals

- **~$110** in LLM spend
- **~4 hours** of attended human time (mostly the interview)
- **152 markdown files** produced (76 articles × product + tech flavors)
- **6 journeys** documenting cross-cutting flows
- One working week wall-clock, mostly hands-off

End state: a `docs/capacidades/` and `docs/jornadas/` tree the
maintainer reviews, edits, and publishes — paired product + technical
files for every capability, with `skill_version` stamped on each
article so future maintenance knows what generated them.

## Lessons that became durable rules

Things that surfaced in this run and got encoded back into the skill,
so the next run doesn't repeat the mistakes:

### The maintainer reading 300+ raw pending questions was the pain point

Before Phase 5.5 existed, every code-answerable question (label of
an enum, value of a column, name of a cron job) reached the human
through the interview. The user spent more time filtering noise than
giving real product input. **Phase 5.5 came from that** and now
removes most of them before the interview even starts. The questions
that survive are genuinely about intent, UX, or operational reality.

### Context-switching per question kills the interview

Asking the user "is this label `'Pending'` or `'Em aberto'`?" right
after "what's the SLA expectation on the dunning webhook?" forces a
mental mode change every turn. Cumulative cost: high.

**Thematic interview blocks** were the fix:

- A: meaning / glossary
- B: transitions and triggers
- C: invariants and constraints
- D: UX and support
- E: code-suggested edges
- F: meta-direction of the guide

Each block keeps the human in one mental mode at a time. Same
questions, half the fatigue.

### Sub-agents reporting success blindly is the worst failure mode

One sub-agent in Phase 5 wrote an empty file, returned `{"status":
"ok", "files_modified": [...]}`, and the orchestrator advanced. The
article looked fine in state but was empty on disk. Only caught by
chance during review.

After that incident, **post-edit verification is a core principle**:
every sub-agent that writes a file must `wc -c` to check size > 0,
grep for an expected sentinel, and return
`verification_passed: true|false` in its JSON. The orchestrator never
trusts a self-report without verification.

The matching anti-loop guard came from the same run: a sub-agent
that's hit the same tool error twice in a row aborts with
`status: "aborted"` instead of retrying silently and burning context.

## What this run did NOT exercise

Honest about coverage:

- **Multi-language** — this was a pt-BR-only run. The English path is
  in place but less battle-tested.
- **Incremental maintenance** — bootstrap was one-shot. Re-running
  the skill against the same project after code changes is planned
  for v2.0.
- **Publication** — the maintainer published to Chatwoot manually
  from the local `docs/` tree. Automated publication is planned for
  v2.0.
- **Cross-team interview** — single maintainer answered everything.
  Splitting the interview across multiple subject-matter experts
  isn't supported yet.

If you run the skill and hit a case the above doesn't cover, that's
useful feedback — open an issue with the project.
