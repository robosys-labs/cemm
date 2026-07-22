"""Bounded session/discourse memory for Phase-11 conversational cognition.

This store is not semantic authority and does not mutate the durable SemanticStore.  It is
session-lifecycle state owned by context+permission, committed only at the Stage-13 commit
boundary.  Durable/world promotion remains a separate authorized persistence concern.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from typing import Any, Mapping

from ..csir.model import CSIRGraph
from ..grounding.model import DiscourseAnchor
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
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"session belief {label} must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("session belief confidence must be within [0,1]")
        if self.revision < 1:
            raise ValueError("session belief revision must be positive")
        for values, label in (
            (self.source_refs, "sources"), (self.evidence_refs, "evidence"), (self.proof_refs, "proofs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"session belief {label} must be unique")


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

    @property
    def active_beliefs(self) -> tuple[SessionBeliefEntry, ...]:
        return tuple(item for item in self.beliefs if item.active)


@dataclass(frozen=True, slots=True)
class SessionMemoryCommit:
    commit_ref: str
    expected_revision: int
    additions: tuple[SessionBeliefEntry, ...] = ()
    retract_claim_refs: tuple[str, ...] = ()
    supersede_claims: tuple[tuple[str, str], ...] = ()
    open_questions: tuple[OpenQuestionMemory, ...] = ()
    clarifications: tuple[ClarificationMemory, ...] = ()
    common_ground: tuple[CommonGroundEntry, ...] = ()
    discourse_anchors: tuple[DiscourseAnchor, ...] = ()
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
    """Small copy-on-write session state; lock is held only across snapshot swap."""

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

    def latest_claim_ref(
        self, context_ref: str, permission_ref: str, *, source_ref: str | None = None
    ) -> str | None:
        snapshot = self.snapshot(context_ref, permission_ref)
        values = [
            item for item in snapshot.active_beliefs
            if source_ref is None or source_ref in item.source_refs
        ]
        return values[-1].claim_ref if values else None

    def grounding_anchors(self, context_ref: str, permission_ref: str) -> tuple[DiscourseAnchor, ...]:
        """Return bounded prior-turn anchors for Stage 3 without exposing mutable state."""
        return tuple(self.snapshot(context_ref, permission_ref).discourse_anchors)

    @staticmethod
    def _dedupe_by_ref(values, attribute: str):
        result = {}
        for value in values:
            result[getattr(value, attribute)] = value
        # Preserve discourse recency/insertion order; replacing an existing ref does not
        # turn lexical ref ordering into temporal ordering.
        return tuple(result.values())

    def commit(
        self,
        context_ref: str,
        permission_ref: str,
        proposal: SessionMemoryCommit,
    ) -> SessionCommitReceipt:
        key = (context_ref, permission_ref)
        with self._lock:
            current = self._states.get(key, SessionMemorySnapshot(context_ref, permission_ref, 0))
            if current.revision != proposal.expected_revision:
                raise SessionMemoryConflict(
                    f"session-memory CAS conflict:{proposal.expected_revision}!={current.revision}"
                )
            beliefs = list(current.beliefs)
            retracts = set(proposal.retract_claim_refs)
            supersede = dict(proposal.supersede_claims)
            updated: list[SessionBeliefEntry] = []
            for item in beliefs:
                if item.claim_ref in retracts and item.active:
                    item = replace(item, active=False, revision=item.revision + 1)
                replacement = supersede.get(item.claim_ref)
                if replacement is not None and item.active:
                    item = replace(
                        item, active=False, superseded_by_ref=replacement,
                        revision=item.revision + 1,
                    )
                updated.append(item)
            existing_refs = {item.belief_ref for item in updated}
            for item in proposal.additions:
                if item.context_ref != context_ref or item.permission_ref != permission_ref:
                    raise ValueError("session-memory commit cannot widen context/permission scope")
                if item.belief_ref not in existing_refs:
                    updated.append(item)
                    existing_refs.add(item.belief_ref)
            # Bound by recency after retaining inactive lineage only while space permits.
            if len(updated) > self.maximum_beliefs:
                active = [item for item in updated if item.active]
                inactive = [item for item in updated if not item.active]
                keep_inactive = max(0, self.maximum_beliefs - len(active))
                updated = (inactive[-keep_inactive:] if keep_inactive else []) + active[-self.maximum_beliefs:]
                updated = updated[-self.maximum_beliefs:]

            open_questions = self._dedupe_by_ref(
                (*current.open_questions, *proposal.open_questions), "question_ref"
            )[-self.maximum_discourse_items:]
            clarifications = self._dedupe_by_ref(
                (*current.clarifications, *proposal.clarifications), "clarification_ref"
            )[-self.maximum_discourse_items:]
            common_ground = self._dedupe_by_ref(
                (*current.common_ground, *proposal.common_ground), "entry_ref"
            )[-self.maximum_discourse_items:]
            discourse_anchors = self._dedupe_by_ref(
                (*current.discourse_anchors, *proposal.discourse_anchors), "anchor_ref"
            )[-self.maximum_discourse_items:]
            after = SessionMemorySnapshot(
                context_ref=context_ref,
                permission_ref=permission_ref,
                revision=current.revision + 1,
                beliefs=tuple(updated),
                open_questions=open_questions,
                clarifications=clarifications,
                common_ground=common_ground,
                discourse_anchors=discourse_anchors,
            )
            self._states[key] = after
        receipt_ref = "session-commit-receipt:" + semantic_fingerprint(
            "session-commit-receipt",
            (proposal.commit_ref, context_ref, permission_ref, current.revision, after.revision),
            32,
        )
        return SessionCommitReceipt(
            receipt_ref=receipt_ref,
            commit_ref=proposal.commit_ref,
            context_ref=context_ref,
            permission_ref=permission_ref,
            revision_before=current.revision,
            revision_after=after.revision,
            applied_belief_refs=tuple(item.belief_ref for item in proposal.additions),
            retracted_claim_refs=tuple(sorted(retracts)),
            superseded_claim_refs=tuple(sorted(supersede)),
        )


__all__ = [
    "ClarificationMemory", "CommonGroundEntry", "OpenQuestionMemory",
    "SessionBeliefEntry", "SessionCommitReceipt", "SessionDiscourseMemory",
    "SessionMemoryCommit", "SessionMemoryConflict", "SessionMemorySnapshot",
]
