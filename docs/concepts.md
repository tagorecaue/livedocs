# Concepts

LiveDocs documents a SaaS through a small, opinionated vocabulary.
The choices below all came from one place: trying to keep the doc set
maintainable past ~20 articles, where naive approaches degrade fast.

## What gets its own page — Capability, Journey, Screen

A **capability** is a business area as the user thinks of it
("Recurring billing", "Resident onboarding", "Dunning"). It's the
primary unit — typically 10–25 of them in a mid-sized SaaS, each
becomes a category in the help center.

A **journey** is a cross-cutting flow that touches several
capabilities to deliver an outcome ("From unit registered to first
paid invoice"). Secondary and optional — created only when explaining
the path end-to-end adds more than explaining capability-by-capability
would. Usually 5–15 per SaaS.

A **screen** is a UI route. Crucially, screens are **not** first-class
documentation units — they live as sections or screenshot anchors
inside the article of the capability they serve. Knowledge belongs to
a domain area, not to a button. Promoting screens to standalone
articles fragments the docs into one-page-per-route, which scales
badly and gives users a help center that mirrors your nav rather than
your domain.

(Exception: a screen so conceptually dense that its content doesn't
fit inside the parent capability gets its own page. Rare.)

## Two flavors per topic, never linking to each other

Every article is generated as a pair: `<slug>.md` (product) and
`<slug>.tech.md` (technical). Same domain knowledge, two audiences.

The product flavor uses the language the end user sees in the UI —
no column names, no enum values, no route paths in prose. The
technical flavor is the dev/AI counterpart, with `file:line`
citations, numbered invariants, code anchors.

The two never link to each other. Cross-references go only to other
same-flavor guides. They describe the same thing for different
audiences; linking them creates a loop that adds no value and
confuses readers about which flavor they're in.

## Pending questions, not interruptions

When the agent finds something the code doesn't reveal (intent, UX
rationale, integration behavior under failure), it does NOT pause and
interrupt the user. It registers a **pending question**, writes a
provisional answer into the draft with a confidence flag, and moves on.

Questions accumulate during Phase 4 and Phase 5. Phase 5.5 re-checks
each one against the code, auto-answering the ones with literal
evidence and patching the article that should have had the answer.
Whatever survives reaches Phase 6 — a single batch interview in
thematic blocks (meaning / transitions / invariants / UX-and-support /
code edges / direction).

The cost of context-switching the human ("answer this right now") is
higher than the cost of an extra phase. Batched interviews also
benefit from cross-question dedup — one answer often resolves several.

## Isolated context per draft

Phase 4 generates each article in **isolated context**. The sub-agent
sees: the guidance text, a menu of other articles' titles (no
bodies), the article's own code anchors, the style guide. Nothing else.
No global "all docs in prompt".

Two reasons: **cost** (prompts that grow with N articles get
expensive fast) and **coherence** (an LLM's attention degrades when
keeping all other articles in mind while writing this one).
Cross-linking happens later in Phase 5, where input is a short
markdown index, not raw code.

## Guidance text + code capture point

Some product knowledge isn't in the code: the reasoning behind a
decision, customer profile, integration quirk the maintainer keeps
in their head. Phase 0 collects a free-form **guidance text** that
gets included in every later prompt as instruction, not content to
copy.

The complementary discipline is the **code capture point** — the git
commit SHA at scan time, persisted alongside the taxonomy. It pins
"this documentation was generated from this state of the code". The
SHA becomes important once incremental maintenance lands.
