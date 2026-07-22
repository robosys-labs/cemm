"""Bounded session/discourse memory for v3.5.1 conversational cognition.

This store is not semantic authority and does not mutate the durable SemanticStore.  It is
session-lifecycle state owned by context+permission.  Belief admission occurs at Stage 13;
observed system output/common-ground proposal occurs separately at Stage 21.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from threading import RLock
from typing import Any

from ..csir.model import CSIRGraph
from ..grounding.model import DiscourseAnchor, SystemOutputAnchor
from ..schema.model import semantic_fingerprint


@dataclass(frozen=True, slots=True)
class SessionBeliefEntry:
    belief_ref: str
    proposition_ref: str
    claim_ref: str
    graph: CSIRGraph
    context_ref: str
    permission_ref: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    confidence: float
    truth_status: str = "supported"
    active: bool = True
    superseded_by_ref: str | None = None
    revision: int = 1

    def __post_init__(self) -> None:
        for value, label in (
            (self.belief_ref, "belief_ref"), (self.proposition_ref, "proposition_ref"),
            (self.claim_ref, "claim_ref"), (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"), (self.truth_status, "truth_status"),
        ):
            _ref(value, f"session belief {label}")
        if not 0.0 <= self.confidence <= 1.0 or self.revision < 1:
            raise ValueError("invalid session belief confidence/revision")
        for values, label in (
            (self.source_refs, "sources"), (self.evidence_refs, "evidence"), (self.proof_refs, "proofs"),
        ):
            _unique(values, f"session belief {label}")


@dataclass(frozen=True, slots=True)
class ReferenceSurfaceEntry:
    reference_ref: str
    referent_ref: str
    surface: str
    normalized_key: str
    language_tag: str
    context_ref: str
    evidence_refs: tuple[str, ...]
    turn_index: int
    safe_for_realization: bool = True

    def __post_init__(self) -> None:
        for value, label in (
            (self.reference_ref, "reference_ref"), (self.referent_ref, "referent_ref"),
            (self.surface, "surface"), (self.normalized_key, "normalized_key"),
            (self.language_tag, "language_tag"), (self.context_ref, "context_ref"),
        ):
            _ref(value, label)
        if self.turn_index < 0:
            raise ValueError("reference surface turn index cannot be negative")
        _unique(self.evidence_refs, "reference surface evidence")


@dataclass(frozen=True, slots=True)
class OutputMemoryEntry:
    output_ref: str
    response_ref: str
    graph: CSIRGraph
    surface_candidate_ref: str
    context_ref: str
    permission_ref: str
    audience_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    turn_index: int
    target_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.output_ref, "output_ref"), (self.response_ref, "response_ref"),
            (self.surface_candidate_ref, "surface_candidate_ref"), (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.turn_index < 0:
            raise ValueError("output memory turn index cannot be negative")
        _unique(self.audience_refs, "output memory audiences")
        _unique(self.evidence_refs, "output memory evidence")
        _unique(self.target_refs, "output memory targets")


@dataclass(frozen=True, slots=True)
class SessionEventEntry:
    event_ref: str
    graph: CSIRGraph
    context_ref: str
    permission_ref: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    support: float
    turn_index: int

    def __post_init__(self) -> None:
        for value, label in ((self.event_ref, "event_ref"), (self.context_ref, "context_ref"), (self.permission_ref, "permission_ref")):
            _ref(value, f"session event {label}")
        if not 0.0 <= self.support <= 1.0 or self.turn_index < 0:
            raise ValueError("invalid session event support/turn")
        _unique(self.source_refs, "session event sources")
        _unique(self.evidence_refs, "session event evidence")
        _unique(self.proof_refs, "session event proofs")


@dataclass(frozen=True, slots=True)
class OpenQuestionMemory:
    question_ref: str
    query_ref: str
    context_ref: str
    speaker_ref: str
    target_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    answered: bool = False


@dataclass(frozen=True, slots=True)
class ClarificationMemory:
    clarification_ref: str
    target_ref: str
    reason_ref: str
    context_ref: str
    evidence_refs: tuple[str, ...] = ()
    resolved: bool = False


@dataclass(frozen=True, slots=True)
class CommonGroundEntry:
    entry_ref: str
    proposition_ref: str
    participant_refs: tuple[str, ...]
    context_ref: str
    evidence_refs: tuple[str, ...]
    grounded_by_emission: bool = False
    accepted_by_participants: bool = False


@dataclass(frozen=True, slots=True)
class SessionMemorySnapshot:
    context_ref: str
    permission_ref: str
    revision: int
    beliefs: tuple[SessionBeliefEntry, ...] = ()
    open_questions: tuple[OpenQuestionMemory, ...] = ()
    clarifications: tuple[ClarificationMemory, ...] = ()
    common_ground: tuple[CommonGroundEntry, ...] = ()
    discourse_anchors: tuple[DiscourseAnchor, ...] = ()
    reference_surfaces: tuple[ReferenceSurfaceEntry, ...] = ()
    prior_outputs: tuple[OutputMemoryEntry, ...] = ()
    events: tuple[SessionEventEntry, ...] = ()

    @property
    def active_beliefs(self) -> tuple[SessionBeliefEntry, ...]:
        return tuple(item for item in self.beliefs if item.active)

    @property
    def unanswered_questions(self) -> tuple[OpenQuestionMemory, ...]:
        return tuple(item for item in self.open_questions if not item.answered)


@dataclass(frozen=True, slots=True)
class SessionMemoryCommit:
    commit_ref: str
    expected_revision: int
    additions: tuple[SessionBeliefEntry, ...] = ()
    retract_claim_refs: tuple[str, ...] = ()
    supersede_claims: tuple[tuple[str, str], ...] = ()
    open_questions: tuple[OpenQuestionMemory, ...] = ()
    answered_query_refs: tuple[str, ...] = ()
    clarifications: tuple[ClarificationMemory, ...] = ()
    resolved_clarification_refs: tuple[str, ...] = ()
    common_ground: tuple[CommonGroundEntry, ...] = ()
    discourse_anchors: tuple[DiscourseAnchor, ...] = ()
    reference_surfaces: tuple[ReferenceSurfaceEntry, ...] = ()
    prior_outputs: tuple[OutputMemoryEntry, ...] = ()
    events: tuple[SessionEventEntry, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SessionCommitReceipt:
    receipt_ref: str
    commit_ref: str
    context_ref: str
    permission_ref: str
    revision_before: int
    revision_after: int
    applied_belief_refs: tuple[str, ...]
    retracted_claim_refs: tuple[str, ...]
    superseded_claim_refs: tuple[str, ...]


class SessionMemoryConflict(RuntimeError):
    pass


class SessionDiscourseMemory:
    """Small copy-on-write session state; lock spans only the bounded snapshot swap."""

    def __init__(self, *, maximum_beliefs: int = 512, maximum_discourse_items: int = 128) -> None:
        if maximum_beliefs < 1 or maximum_discourse_items < 1:
            raise ValueError("session-memory bounds must be positive")
        self.maximum_beliefs = maximum_beliefs
        self.maximum_discourse_items = maximum_discourse_items
        self._lock = RLock()
        self._states: dict[tuple[str, str], SessionMemorySnapshot] = {}

    def snapshot(self, context_ref: str, permission_ref: str) -> SessionMemorySnapshot:
        key = (context_ref, permission_ref)
        with self._lock:
            return self._states.get(key, SessionMemorySnapshot(context_ref, permission_ref, 0))

    def latest_claim_ref(self, context_ref: str, permission_ref: str, *, source_ref: str | None = None) -> str | None:
        values = [
            item for item in self.snapshot(context_ref, permission_ref).active_beliefs
            if source_ref is None or source_ref in item.source_refs
        ]
        return values[-1].claim_ref if values else None

    def grounding_anchors(self, context_ref: str, permission_ref: str) -> tuple[DiscourseAnchor, ...]:
        snapshot = self.snapshot(context_ref, permission_ref)
        keys_by_referent: dict[str, set[str]] = {}
        for surface in snapshot.reference_surfaces:
            if surface.safe_for_realization:
                keys_by_referent.setdefault(surface.referent_ref, set()).add(surface.normalized_key)
        return tuple(
            replace(
                anchor,
                normalized_surface_keys=tuple(sorted(keys_by_referent.get(anchor.referent_ref, ()))),
            )
            for anchor in snapshot.discourse_anchors
        )

    def system_output_anchors(self, context_ref: str, permission_ref: str) -> tuple[SystemOutputAnchor, ...]:
        result = []
        for item in self.snapshot(context_ref, permission_ref).prior_outputs:
            identities = tuple(sorted({term.identity_ref for term in item.graph.terms if term.identity_ref}))
            targets = tuple(item.target_refs)
            if identities or targets:
                result.append(SystemOutputAnchor(
                    output_ref=item.output_ref, context_ref=item.context_ref,
                    content_referent_refs=identities, target_refs=targets,
                    turn_index=item.turn_index, evidence_refs=item.evidence_refs,
                ))
        return tuple(result)

    def reference_surface_entry(
        self, context_ref: str, permission_ref: str, referent_ref: str, *, language_tag: str = "en",
    ) -> ReferenceSurfaceEntry | None:
        values = [
            item for item in self.snapshot(context_ref, permission_ref).reference_surfaces
            if item.referent_ref == referent_ref and item.language_tag == language_tag and item.safe_for_realization
        ]
        return values[-1] if values else None

    def reference_surface(self, context_ref: str, permission_ref: str, referent_ref: str, *, language_tag: str = "en") -> str | None:
        entry = self.reference_surface_entry(
            context_ref, permission_ref, referent_ref, language_tag=language_tag,
        )
        return None if entry is None else entry.surface

    def semantic_graph(self, context_ref: str, permission_ref: str, semantic_ref: str) -> CSIRGraph | None:
        """Resolve a scoped semantic occurrence for realization/follow-up, never as authority."""
        snapshot = self.snapshot(context_ref, permission_ref)
        matches = []
        for belief in snapshot.active_beliefs:
            if semantic_ref in {belief.belief_ref, belief.proposition_ref, belief.claim_ref}:
                matches.append(belief.graph)
        for event in snapshot.events:
            if semantic_ref == event.event_ref:
                matches.append(event.graph)
        for output in snapshot.prior_outputs:
            if semantic_ref in {output.output_ref, output.response_ref}:
                matches.append(output.graph)
        # A semantic reference must resolve singularly inside one context/permission scope.
        unique = {semantic_fingerprint("session-semantic-graph", graph, 64): graph for graph in matches}
        return next(iter(unique.values())) if len(unique) == 1 else None

    @staticmethod
    def _dedupe_by_ref(values, attribute: str):
        result = {}
        for value in values:
            key = getattr(value, attribute)
            if key in result:
                # A newer occurrence/revision of the same identity is newest for discourse
                # recency purposes. Delete before reinsertion so order reflects observation
                # order rather than first-seen position or lexical ref ordering.
                del result[key]
            result[key] = value
        return tuple(result.values())

    def commit(self, context_ref: str, permission_ref: str, proposal: SessionMemoryCommit) -> SessionCommitReceipt:
        key = (context_ref, permission_ref)
        with self._lock:
            current = self._states.get(key, SessionMemorySnapshot(context_ref, permission_ref, 0))
            if current.revision != proposal.expected_revision:
                raise SessionMemoryConflict(f"session-memory CAS conflict:{proposal.expected_revision}!={current.revision}")
            beliefs = list(current.beliefs)
            retracts = set(proposal.retract_claim_refs)
            supersede = dict(proposal.supersede_claims)
            updated: list[SessionBeliefEntry] = []
            for item in beliefs:
                if item.claim_ref in retracts and item.active:
                    item = replace(item, active=False, revision=item.revision + 1)
                replacement = supersede.get(item.claim_ref)
                if replacement is not None and item.active:
                    item = replace(item, active=False, superseded_by_ref=replacement, revision=item.revision + 1)
                updated.append(item)
            existing_refs = {item.belief_ref for item in updated}
            for item in proposal.additions:
                if item.context_ref != context_ref or item.permission_ref != permission_ref:
                    raise ValueError("session-memory commit cannot widen context/permission scope")
                if item.belief_ref not in existing_refs:
                    updated.append(item)
                    existing_refs.add(item.belief_ref)
            if len(updated) > self.maximum_beliefs:
                active = [item for item in updated if item.active]
                inactive = [item for item in updated if not item.active]
                keep_inactive = max(0, self.maximum_beliefs - len(active))
                updated = (inactive[-keep_inactive:] if keep_inactive else []) + active[-self.maximum_beliefs:]
                updated = updated[-self.maximum_beliefs:]

            answered = set(proposal.answered_query_refs)
            open_questions = [
                replace(item, answered=True) if item.query_ref in answered and not item.answered else item
                for item in current.open_questions
            ]
            open_questions = self._dedupe_by_ref((*open_questions, *proposal.open_questions), "question_ref")[-self.maximum_discourse_items:]
            resolved_clarifications = set(proposal.resolved_clarification_refs)
            clarifications = [
                replace(item, resolved=True) if item.clarification_ref in resolved_clarifications and not item.resolved else item
                for item in current.clarifications
            ]
            clarifications = self._dedupe_by_ref((*clarifications, *proposal.clarifications), "clarification_ref")[-self.maximum_discourse_items:]
            common_ground = self._dedupe_by_ref((*current.common_ground, *proposal.common_ground), "entry_ref")[-self.maximum_discourse_items:]
            discourse_anchors = self._dedupe_by_ref((*current.discourse_anchors, *proposal.discourse_anchors), "anchor_ref")[-self.maximum_discourse_items:]
            reference_surfaces = self._dedupe_by_ref((*current.reference_surfaces, *proposal.reference_surfaces), "reference_ref")[-self.maximum_discourse_items:]
            prior_outputs = self._dedupe_by_ref((*current.prior_outputs, *proposal.prior_outputs), "output_ref")[-self.maximum_discourse_items:]
            events = self._dedupe_by_ref((*current.events, *proposal.events), "event_ref")[-self.maximum_discourse_items:]
            after = SessionMemorySnapshot(
                context_ref=context_ref, permission_ref=permission_ref, revision=current.revision + 1,
                beliefs=tuple(updated), open_questions=open_questions, clarifications=clarifications,
                common_ground=common_ground, discourse_anchors=discourse_anchors,
                reference_surfaces=reference_surfaces, prior_outputs=prior_outputs, events=events,
            )
            self._states[key] = after
        receipt_ref = "session-commit-receipt:" + semantic_fingerprint(
            "session-commit-receipt",
            (proposal.commit_ref, context_ref, permission_ref, current.revision, after.revision), 32,
        )
        return SessionCommitReceipt(
            receipt_ref=receipt_ref, commit_ref=proposal.commit_ref,
            context_ref=context_ref, permission_ref=permission_ref,
            revision_before=current.revision, revision_after=after.revision,
            applied_belief_refs=tuple(item.belief_ref for item in proposal.additions),
            retracted_claim_refs=tuple(sorted(retracts)),
            superseded_claim_refs=tuple(sorted(supersede)),
        )

    def commit_output(
        self, context_ref: str, permission_ref: str, *, output: OutputMemoryEntry,
        common_ground: CommonGroundEntry,
    ) -> SessionCommitReceipt:
        current = self.snapshot(context_ref, permission_ref)
        proposal = SessionMemoryCommit(
            commit_ref="session-output-commit:" + semantic_fingerprint(
                "session-output-commit", (output.output_ref, common_ground.entry_ref, current.revision), 24,
            ),
            expected_revision=current.revision,
            common_ground=(common_ground,), prior_outputs=(output,), evidence_refs=output.evidence_refs,
        )
        return self.commit(context_ref, permission_ref, proposal)


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty")


def _unique(values: tuple[Any, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


__all__ = [
    "ClarificationMemory", "CommonGroundEntry", "OpenQuestionMemory", "OutputMemoryEntry",
    "ReferenceSurfaceEntry", "SessionBeliefEntry", "SessionEventEntry", "SessionCommitReceipt", "SessionDiscourseMemory",
    "SessionMemoryCommit", "SessionMemoryConflict", "SessionMemorySnapshot",
]
