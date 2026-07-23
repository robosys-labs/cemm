"""Condition assessment without embedding domain-specific condition logic."""
from __future__ import annotations

from typing import Mapping, Protocol

from ..storage.model import (
    AssertionStatus,
    AssignmentStatus,
    ConditionTruth,
    KnowledgeStatus,
    RecordKind,
    StoreSnapshot,
)
from ..storage.repositories import interval_contains
from ..semantic_records.model import CapabilityStatus, OccurrenceStatus
from .model import ConditionAssessment


class ConditionEvaluator(Protocol):
    def assess(
        self,
        condition_ref: str,
        *,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> ConditionAssessment: ...


class MappingConditionEvaluator:
    """Deterministic evaluator used by tests and policy adapters."""

    def __init__(self, values: Mapping[str, ConditionTruth | str]) -> None:
        self._values = {
            key: value if isinstance(value, ConditionTruth) else ConditionTruth(value)
            for key, value in values.items()
        }

    def assess(self, condition_ref: str, *, context_ref: str, at_time: str | None, snapshot: StoreSnapshot) -> ConditionAssessment:
        truth = self._values.get(condition_ref, ConditionTruth.UNKNOWN)
        return ConditionAssessment(condition_ref, truth, reason="mapping_condition")


class StoreConditionEvaluator:
    """Interpret condition references through canonical stored records.

    This evaluator intentionally does not parse condition names.  A condition
    reference resolves to an admitted typed record, and its typed status decides
    the four-valued result.
    """

    def __init__(self, store) -> None:
        self._store = store

    def assess(self, condition_ref: str, *, context_ref: str, at_time: str | None, snapshot: StoreSnapshot) -> ConditionAssessment:
        candidates = self._store.resolve_any(condition_ref, snapshot=snapshot)
        if not candidates:
            return ConditionAssessment(condition_ref, ConditionTruth.UNKNOWN, reason="condition_unresolved")
        truths: set[ConditionTruth] = set()
        evidence: list[str] = []
        for stored in candidates:
            value = stored.payload
            item_context = getattr(value, "context_ref", context_ref)
            if item_context not in {"global", context_ref}:
                continue
            if not interval_contains(
                getattr(value, "valid_from", None),
                getattr(value, "valid_to", None),
                at_time,
            ):
                continue
            if stored.record_kind == RecordKind.KNOWLEDGE:
                status = value.truth_status
                truths.add({
                    KnowledgeStatus.SUPPORTED: ConditionTruth.SATISFIED,
                    KnowledgeStatus.OPPOSED: ConditionTruth.UNSATISFIED,
                    KnowledgeStatus.BOTH: ConditionTruth.CONTRADICTED,
                    KnowledgeStatus.UNDETERMINED: ConditionTruth.UNKNOWN,
                    KnowledgeStatus.RETRACTED: ConditionTruth.UNKNOWN,
                    KnowledgeStatus.SUPERSEDED: ConditionTruth.UNKNOWN,
                }[status])
                evidence.extend(value.evidence_refs)
            elif stored.record_kind == RecordKind.TYPE_ASSERTION:
                status = value.status
                truths.add({
                    AssertionStatus.SUPPORTED: ConditionTruth.SATISFIED,
                    AssertionStatus.OPPOSED: ConditionTruth.UNSATISFIED,
                    AssertionStatus.DISPUTED: ConditionTruth.CONTRADICTED,
                    AssertionStatus.RETRACTED: ConditionTruth.UNKNOWN,
                    AssertionStatus.SUPERSEDED: ConditionTruth.UNKNOWN,
                }[status])
                evidence.extend(value.evidence_refs)
            elif stored.record_kind == RecordKind.STATE_ASSIGNMENT:
                status = value.status
                truths.add({
                    AssignmentStatus.ACTIVE: ConditionTruth.SATISFIED,
                    AssignmentStatus.OPPOSED: ConditionTruth.UNSATISFIED,
                    AssignmentStatus.CONTRADICTED: ConditionTruth.CONTRADICTED,
                    AssignmentStatus.TERMINATED: ConditionTruth.UNSATISFIED,
                    AssignmentStatus.RETRACTED: ConditionTruth.UNKNOWN,
                    AssignmentStatus.SUPERSEDED: ConditionTruth.UNKNOWN,
                }[status])
                evidence.extend(value.evidence_refs)
            elif stored.record_kind == RecordKind.CAPABILITY_INSTANCE:
                truths.add({
                    CapabilityStatus.AVAILABLE: ConditionTruth.SATISFIED,
                    CapabilityStatus.BLOCKED: ConditionTruth.UNSATISFIED,
                    CapabilityStatus.UNAVAILABLE: ConditionTruth.UNSATISFIED,
                    CapabilityStatus.TERMINATED: ConditionTruth.UNSATISFIED,
                    CapabilityStatus.CONDITIONAL: ConditionTruth.UNKNOWN,
                    CapabilityStatus.DEGRADED: ConditionTruth.UNKNOWN,
                    CapabilityStatus.UNKNOWN: ConditionTruth.UNKNOWN,
                }[value.status])
                evidence.extend(value.evidence_refs)
            elif stored.record_kind == RecordKind.EVENT_OCCURRENCE:
                truths.add({
                    OccurrenceStatus.OBSERVED: ConditionTruth.SATISFIED,
                    OccurrenceStatus.ADMITTED: ConditionTruth.SATISFIED,
                    OccurrenceStatus.ONGOING: ConditionTruth.SATISFIED,
                    OccurrenceStatus.COMPLETED: ConditionTruth.SATISFIED,
                    OccurrenceStatus.ATTEMPTED: ConditionTruth.SATISFIED,
                    OccurrenceStatus.FAILED: ConditionTruth.SATISFIED,
                    OccurrenceStatus.PREVENTED: ConditionTruth.UNSATISFIED,
                    OccurrenceStatus.NON_OCCURRING: ConditionTruth.UNSATISFIED,
                    OccurrenceStatus.MENTIONED: ConditionTruth.UNKNOWN,
                    OccurrenceStatus.CLAIMED: ConditionTruth.UNKNOWN,
                    OccurrenceStatus.REPORTED: ConditionTruth.UNKNOWN,
                    OccurrenceStatus.PLANNED: ConditionTruth.UNKNOWN,
                    OccurrenceStatus.HYPOTHETICAL: ConditionTruth.UNKNOWN,
                    OccurrenceStatus.COUNTERFACTUAL: ConditionTruth.UNKNOWN,
                    OccurrenceStatus.FICTIONAL: ConditionTruth.UNKNOWN,
                }[value.occurrence_status])
                evidence.extend(value.provenance_refs)
            elif stored.record_kind in {
                RecordKind.PROPOSITION,
                RecordKind.CLAIM_OCCURRENCE,
                RecordKind.CLAIM_RECORD,
                RecordKind.SEMANTIC_APPLICATION,
                RecordKind.REFERENT,
                RecordKind.EVIDENCE,
            }:
                # The occurrence/existence of these records is itself a valid
                # condition. Proposition truth remains represented by KnowledgeRecord.
                truths.add(ConditionTruth.SATISFIED)
            else:
                truths.add(ConditionTruth.UNKNOWN)
        if not truths:
            truth = ConditionTruth.UNKNOWN
        elif ConditionTruth.CONTRADICTED in truths or (
            ConditionTruth.SATISFIED in truths and ConditionTruth.UNSATISFIED in truths
        ):
            truth = ConditionTruth.CONTRADICTED
        elif ConditionTruth.SATISFIED in truths:
            truth = ConditionTruth.SATISFIED
        elif ConditionTruth.UNSATISFIED in truths:
            truth = ConditionTruth.UNSATISFIED
        else:
            truth = ConditionTruth.UNKNOWN
        return ConditionAssessment(
            condition_ref,
            truth,
            tuple(dict.fromkeys(evidence)),
            reason="typed_record_condition",
        )
