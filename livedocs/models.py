"""Data models — Pydantic schemas for state, facts, evaluations, inbox.

These are *pure data structures*. IO (load/save) lives in state.py.
The split lets us write tests and use the models without dragging filesystem
concerns into every module.

# Schema versioning

`GlobalState.schema_version` is bumped whenever the on-disk shape changes:

  - v1 (livedocs 0.1.x): InterviewState.questions[] holding A1/A2/B1 etc.
  - v2 (livedocs 0.2.x): InterviewState.facts[] (fact-driven adaptive interview).

state.py:_migrate_state_inplace handles v1 → v2 transparently so old projects
keep loading without manual intervention.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config (project-level, lives at <repo>/.livedocs/config.toml)
# ---------------------------------------------------------------------------

class ProjectConfig(BaseModel):
    """Stable per-project config, lives at <repo>/.livedocs/config.toml."""

    schema_version: int = 1
    project_slug: str
    lang: Literal["pt-BR", "en"] = "en"
    provider: str = "claude-code"
    docs_dir: str = "docs"
    """Relative path to the docs directory inside the repo."""

    guides_subdir: str = ""
    """Optional subdirectory under docs_dir where guides live (e.g. 'guides').

    When set, full path is `<docs_dir>/<guides_subdir>/<domain>/<slug>.md`.
    Auto-detected during `init` when `<docs_dir>/guides/` already contains .md.
    Empty string means guides live directly under docs_dir.
    """

    use_graphify: bool = False
    """Whether the user opted into graphify integration."""

    style: str = "narrative"
    """Writing style for guides. One of: narrative | reference | tutorial.

    The init wizard copies the chosen template to <repo>/.livedocs/style.md
    where it can be customized freely.
    """

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


# ---------------------------------------------------------------------------
# Fact-driven interview model (v0.2.x)
# ---------------------------------------------------------------------------

EvidenceKind = Literal["code", "answer", "guide", "hypothesis"]
"""
- `code`: ref points to a file:line range in the user's repo.
- `answer`: ref is the id of an interview answer that established the fact.
- `guide`: ref is the slug of another guide that already states the fact.
- `hypothesis`: agent's inference without external grounding (always low-conf).
"""

FactKind = Literal[
    "trigger",       # what fires this behavior?
    "invariant",     # what must never happen / always hold?
    "edge_case",     # rollback, race, timeout, concurrent edit
    "terminology",   # canonical product term + meaning
    "flow",          # narrative of a process or transition
    "value",         # numeric/threshold/limit
    "actor",         # who triggers (operator, customer, system, cron)
    "ui_surface",    # screen / modal / route where it appears
]

FactConfidence = Literal["none", "low", "medium", "high"]

FactPriority = Literal[
    "established",            # evidence is strong, will become an assertion in the guide
    "needs-confirmation",     # evidence exists but ambiguous, needs a user answer
    "hypothesis-with-trace",  # weak evidence, goes to Pendências with 🟡
    "speculation",            # no evidence at all, only fact category where silencing is allowed
]

FactStatus = Literal["open", "hypothesized", "confirmed", "contradicted", "resolved"]


class Evidence(BaseModel):
    """A single piece of evidence backing a fact or refuting it."""

    kind: EvidenceKind
    ref: str
    """For code: 'path:start-end' or 'path:line'. For answer: question/answer id.
    For guide: '<slug>#section' or just '<slug>'. For hypothesis: short note."""
    note: str = ""


class Fact(BaseModel):
    """A single piece of knowledge the guide must establish."""

    id: str
    """Stable id like F1, F2, F3 — assigned by the agent during skeleton build."""
    kind: FactKind
    text: str
    """A claim, in the interview language. Single sentence ideally."""

    confidence: FactConfidence = "none"
    priority: FactPriority = "needs-confirmation"
    status: FactStatus = "open"

    evidence: list[Evidence] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    """Other fact ids this one builds on (chain of reasoning)."""

    answer_text: str | None = None
    """The user's actual answer text if the fact got resolved via interview."""
    resolved_at: str | None = None
    last_touched_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    # Pending-question metadata: when priority is needs-confirmation, the agent
    # phrases the prompt to show the user. Hidden when fact is resolved.
    pending_question: str | None = None


# ---------------------------------------------------------------------------
# Evaluation model (post-generation audits)
# ---------------------------------------------------------------------------

EvaluationDimension = Literal[
    "product_clarity",
    "tech_completeness",
    "base_coherence",
    "shape_and_size",     # phase 2
    "style_consistency",  # phase 2
]

IssueSeverity = Literal[
    "blocker",         # contradiction with code or evidence — must fix
    "evidence-based",  # detected something in code/base needing action (never silently ignored)
    "subjective",      # style/aesthetic without code anchor — silenceable, auto-fix-eligible
]


class Issue(BaseModel):
    """A single finding from a post-generation evaluation."""

    id: str
    """Stable id like I1, I2 — assigned by the evaluator."""
    severity: IssueSeverity
    dimension: EvaluationDimension
    message: str
    location: str = ""
    """E.g. 'pagamento-de-repasses.md:42' or 'tech.md, section R3'."""
    auto_fix_available: bool = False
    patch: str = ""
    """Suggested patch text (when auto_fix_available). Free-form."""

    applied: bool = False
    """Set when auto-fix was applied during internal iteration."""


class Evaluation(BaseModel):
    """A single evaluation pass over a generated guide."""

    dimension: EvaluationDimension
    ran_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Inbox — pending human-facing proposals
# ---------------------------------------------------------------------------

InboxItemType = Literal[
    "apply_cross_link",            # add an entry in another guide's "Veja também"
    "evidence_based_issue",        # an evaluation issue requiring human decision
    "resolve_contradiction",       # phase 2
    "split_suggestion",            # phase 2
    "merge_suggestion",            # phase 2
    "glossary_addition",           # phase 2
    "reconfirm_after_code_change", # phase 3
]

InboxItemStatus = Literal["pending", "accepted", "rejected", "snoozed"]


class InboxItem(BaseModel):
    """A proposal awaiting human decision. Persists across sessions."""

    id: str
    """Stable id like INBOX-001."""
    type: InboxItemType
    guide_slug: str
    """The guide most directly affected (the *target* of the change)."""
    source_slug: str = ""
    """If the proposal comes from another guide's reflection, slug of the source."""
    context: str
    """Short human-readable summary of why this exists."""
    proposed_action: str
    """Concrete description of what will happen if accepted."""
    patch: str = ""
    """The actual change to apply on accept (free-form, type-specific format)."""
    status: InboxItemStatus = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    resolved_at: str | None = None


# ---------------------------------------------------------------------------
# Interview state (v0.2.x — fact-driven)
# ---------------------------------------------------------------------------

InterviewStatus = Literal["draft", "in_progress", "generated", "reviewed", "stale"]


class InterviewState(BaseModel):
    slug: str
    domain: str
    title: str = ""
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_touched_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    status: InterviewStatus = "in_progress"

    # Fact-driven model (v0.2). The old questions[] field is migrated into facts[]
    # by state.py:_migrate_state_inplace.
    facts: list[Fact] = Field(default_factory=list)

    # Source files the agent identified as relevant during skeleton building.
    source_files: list[str] = Field(default_factory=list)

    # User's original free-text intent, if any.
    original_intent: str = ""

    # Post-generation evaluations (last run only, full history is in _meta/ in phase 2).
    evaluations: list[Evaluation] = Field(default_factory=list)

    # Internal iteration count (v1 → v1.1 → v1.2 → human). Capped at 3.
    iteration_count: int = 0

    # Computed at generation time, persisted for `livedocs status` display.
    confidence_score: float = 0.0
    """0.0 to 1.0. Roughly: confirmed_facts / (confirmed + 0.5*open + hypothesized)."""

    notes: str = ""

    # Cost tracking — accumulated across all agent calls for this interview.
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    agent_calls: int = 0

    # ---- Backwards-compat shim (v0.1 callers) ----
    #
    # The v0.1 codebase reads `.questions` heavily. Until those call sites are
    # rewritten in Phase B, expose a read-only projection of `facts` that looks
    # like the old list of QuestionState. Writes to `.facts` are what matters;
    # mutating `.questions` is intentionally not supported.
    @property
    def questions(self) -> list["_LegacyQuestionView"]:  # noqa: UP037
        return [_LegacyQuestionView(f) for f in self.facts]

    # ---- Derived helpers ----

    def pending_facts(self) -> list[Fact]:
        """Facts that still need a user answer (needs-confirmation + not resolved)."""
        return [
            f for f in self.facts
            if f.priority == "needs-confirmation" and f.status not in ("confirmed", "resolved")
        ]

    def confirmed_facts(self) -> list[Fact]:
        return [f for f in self.facts if f.status in ("confirmed", "resolved")]

    def hypothesized_facts(self) -> list[Fact]:
        return [f for f in self.facts if f.status == "hypothesized"]

    def open_facts(self) -> list[Fact]:
        return [f for f in self.facts if f.status == "open"]

    def coverage_ratio(self) -> float:
        """Heuristic for the progress bar shown during the interview.

        Counts facts in the priority categories that *require* action.
        Speculation facts are excluded (they don't block progress).
        """
        actionable = [f for f in self.facts if f.priority != "speculation"]
        if not actionable:
            return 0.0
        resolved = sum(1 for f in actionable if f.status in ("confirmed", "resolved"))
        partial = sum(1 for f in actionable if f.status == "hypothesized")
        return (resolved + 0.5 * partial) / len(actionable)

    def compute_confidence_score(self) -> float:
        """Used at generation time for the front-matter confidence_summary."""
        if not self.facts:
            return 0.0
        confirmed = sum(1 for f in self.facts if f.status in ("confirmed", "resolved"))
        hypothesized = sum(1 for f in self.facts if f.status == "hypothesized")
        open_c = sum(1 for f in self.facts if f.status == "open")
        denom = confirmed + hypothesized + 0.5 * open_c
        return confirmed / denom if denom > 0 else 0.0


class _LegacyQuestionView:
    """Adapter that makes a Fact look like the v0.1 QuestionState shape.

    Read-only. Used so Phase A can ship without breaking the v0.1 CLI commands
    that still iterate over `.questions`. Phase B replaces them with native
    fact-driven flow and this class can be deleted.
    """

    __slots__ = ("_fact",)

    def __init__(self, fact: Fact):
        self._fact = fact

    @property
    def id(self) -> str:
        return self._fact.id

    @property
    def block(self) -> str:
        # Synthesize a single-letter "block" so legacy UI grouping still shows something.
        return self._fact.id[:1].upper() if self._fact.id else "?"

    @property
    def block_topic(self) -> str:
        # Use the fact kind capitalized — close enough for legacy status display.
        return self._fact.kind.replace("_", " ").title()

    @property
    def text(self) -> str:
        return self._fact.pending_question or self._fact.text

    @property
    def answer(self) -> str | None:
        return self._fact.answer_text

    @property
    def answered_at(self) -> str | None:
        return self._fact.resolved_at

    @property
    def skipped(self) -> bool:
        # In v0.1 semantics, "skipped" means the user explicitly bypassed it.
        # In v0.2 the closest match is speculation+open (legacy migration path).
        return self._fact.priority == "speculation" and self._fact.status == "open"

    @property
    def covered_by(self) -> str | None:
        # No exact analog in v0.2; legacy callers only use this for display.
        return None


# ---------------------------------------------------------------------------
# Next-guide recommendations (carried from v0.1 — kept compatible)
# ---------------------------------------------------------------------------

class NextRecommendation(BaseModel):
    """A guide the agent suggested as the natural next step."""

    slug: str
    domain: str
    reason: str = ""
    suggested_by: str
    """Slug of the interview whose generation produced this recommendation."""
    suggested_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

class GlobalState(BaseModel):
    """All known interviews + inbox + cross-cutting metadata."""

    schema_version: int = 2
    """Bumped from 1 → 2 when facts[] replaced questions[]."""

    interviews: dict[str, InterviewState] = Field(default_factory=dict)
    """Keyed by slug."""

    last_touched_slug: str | None = None

    next_recommendations: list[NextRecommendation] = Field(default_factory=list)
    """Pending guide suggestions captured during generate_guides()."""

    inbox: list[InboxItem] = Field(default_factory=list)
    """Pending proposals awaiting human review."""

    # ---- Helpers ----

    def pending_inbox(self) -> list[InboxItem]:
        return [i for i in self.inbox if i.status == "pending"]

    def next_inbox_id(self) -> str:
        existing_ns = []
        for item in self.inbox:
            if item.id.startswith("INBOX-"):
                with contextlib.suppress(ValueError):
                    existing_ns.append(int(item.id.split("-", 1)[1]))
        n = max(existing_ns, default=0) + 1
        return f"INBOX-{n:03d}"
