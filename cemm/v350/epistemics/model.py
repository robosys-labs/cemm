"""Phase-10 epistemic contracts.

These records model assessment policy and cycle-local results. Durable claim,
history, admission, evidence, and knowledge records live in the normalized
storage model so they share the same CAS/GraphPatch authority as the rest of
CEMM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping

from ..storage import AdmissionDecision, EpistemicAdmissionRecord, KnowledgeStatus
from ..uol.model import ClaimOccurrence
from ..storage.model import ClaimHistoryRecord, ClaimRecord, KnowledgeRecord


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")


def _probability(value: float, label: str) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be within [0, 1]")


def _unique(values, label: str) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"duplicate {label}")


@dataclass(frozen=True, slots=True)
class SourceAssessment:
    source_ref: str
    authority: float
    reliability: float
    access_quality: float
    bias_risk: float
    evidence_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.source_ref, "source assessment source_ref")
        if not self.evidence_refs:
            raise ValueError("source assessment requires evidence")
        _unique(self.evidence_refs, "source-assessment evidence")
        for value, label in (
            (self.authority, "source authority"),
            (self.reliability, "source reliability"),
            (self.access_quality, "source access quality"),
            (self.bias_risk, "source bias risk"),
        ):
            _probability(value, label)


@dataclass(frozen=True, slots=True)
class AdmissionThresholds:
    minimum_authority: float = 0.0
    minimum_reliability: float = 0.0
    minimum_access_quality: float = 0.0
    maximum_bias_risk: float = 1.0
    minimum_evidence_confidence: float = 0.0
    minimum_independent_sources: int = 1

    def __post_init__(self) -> None:
        for value in (
            self.minimum_authority, self.minimum_reliability,
            self.minimum_access_quality, self.maximum_bias_risk,
            self.minimum_evidence_confidence,
        ):
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("admission thresholds must be within [0, 1]")
        if self.minimum_independent_sources < 1:
            raise ValueError("minimum independent sources must be positive")


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    policy_ref: str
    default_thresholds: AdmissionThresholds = field(default_factory=AdmissionThresholds)
    thresholds_by_sensitivity: Mapping[str, AdmissionThresholds] = field(default_factory=dict)
    require_explicit_authorization: bool = True
    permission_ref: str = "conversation"

    def __post_init__(self) -> None:
        _ref(self.policy_ref, "admission policy_ref")
        _ref(self.permission_ref, "admission policy permission_ref")
        for sensitivity, thresholds in self.thresholds_by_sensitivity.items():
            _ref(str(sensitivity), "admission sensitivity key")
            if not isinstance(thresholds, AdmissionThresholds):
                raise ValueError("sensitivity thresholds must be AdmissionThresholds")

    def thresholds_for(self, sensitivity: str) -> AdmissionThresholds:
        return self.thresholds_by_sensitivity.get(sensitivity, self.default_thresholds)


@dataclass(frozen=True, slots=True)
class AdmissionRequest:
    request_ref: str
    proposition_ref: str
    source_context_ref: str
    target_context_ref: str
    requested_truth_status: KnowledgeStatus
    source_refs: tuple[str, ...]
    evidence_confidences: tuple[tuple[str, float], ...]
    proof_refs: tuple[str, ...]
    source_assessments: tuple[SourceAssessment, ...]
    policy_ref: str
    authorization_ref: str | None = None
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    valid_time_ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.request_ref, "admission request_ref"),
            (self.proposition_ref, "admission proposition_ref"),
            (self.source_context_ref, "admission source_context_ref"),
            (self.target_context_ref, "admission target_context_ref"),
            (self.policy_ref, "admission policy_ref"),
            (self.permission_ref, "admission permission_ref"),
            (self.sensitivity, "admission sensitivity"),
        ):
            _ref(value, label)
        if self.requested_truth_status not in {KnowledgeStatus.SUPPORTED, KnowledgeStatus.OPPOSED}:
            raise ValueError("an admission request may request only support or opposition")
        _unique(self.source_refs, "admission sources")
        _unique(self.proof_refs, "admission proofs")
        evidence_refs = tuple(ref for ref, _ in self.evidence_confidences)
        if len(evidence_refs) != len(set(evidence_refs)):
            raise ValueError("duplicate admission evidence")
        for evidence_ref, confidence in self.evidence_confidences:
            if not isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise ValueError("evidence confidence must be within [0, 1]")
        _unique(tuple(item.source_ref for item in self.source_assessments), "source assessments")
        assessed_sources = {item.source_ref for item in self.source_assessments}
        if not set(self.source_refs).issubset(assessed_sources):
            raise ValueError("every admission source requires an independent source assessment")
        if self.authorization_ref is not None and not self.authorization_ref.strip():
            raise ValueError("authorization_ref cannot be blank")


@dataclass(frozen=True, slots=True)
class AdmissionAssessment:
    request_ref: str
    decision: AdmissionDecision
    truth_status: KnowledgeStatus
    confidence: float
    satisfied_requirements: tuple[str, ...]
    failed_requirements: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.request_ref, "admission assessment request_ref")
        _probability(self.confidence, "admission assessment confidence")
        _unique(self.satisfied_requirements, "satisfied admission requirements")
        _unique(self.failed_requirements, "failed admission requirements")
        _unique(self.evidence_refs, "admission assessment evidence")
        if set(self.satisfied_requirements).intersection(self.failed_requirements):
            raise ValueError("admission requirement cannot be both satisfied and failed")
        admitted = {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION}
        if self.decision in admitted and self.failed_requirements:
            raise ValueError("an admitted assessment cannot retain failed requirements")
        if self.decision not in admitted and self.truth_status != KnowledgeStatus.UNDETERMINED:
            raise ValueError("non-admission assessment cannot assert truth support")


@dataclass(frozen=True, slots=True)
class FourStateTruthAssessment:
    proposition_ref: str
    context_ref: str
    truth_status: KnowledgeStatus
    support_admission_refs: tuple[str, ...]
    opposition_admission_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence: float
    conflicts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.proposition_ref, "truth assessment proposition_ref")
        _ref(self.context_ref, "truth assessment context_ref")
        for values, label in (
            (self.support_admission_refs, "support admissions"),
            (self.opposition_admission_refs, "opposition admissions"),
            (self.source_refs, "truth assessment sources"),
            (self.evidence_refs, "truth assessment evidence"),
            (self.conflicts, "truth assessment conflicts"),
        ):
            _unique(values, label)
        if set(self.support_admission_refs).intersection(self.opposition_admission_refs):
            raise ValueError("one admission cannot be both support and opposition")
        _probability(self.confidence, "truth assessment confidence")
        expected = (
            KnowledgeStatus.BOTH if self.support_admission_refs and self.opposition_admission_refs
            else KnowledgeStatus.SUPPORTED if self.support_admission_refs
            else KnowledgeStatus.OPPOSED if self.opposition_admission_refs
            else KnowledgeStatus.UNDETERMINED
        )
        if self.truth_status != expected:
            raise ValueError("four-state truth status disagrees with admission sets")


@dataclass(frozen=True, slots=True)
class CompiledClaim:
    claim_occurrence: ClaimOccurrence
    claim_record: ClaimRecord
    history_record: ClaimHistoryRecord
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.claim_record.claim_occurrence_ref != self.claim_occurrence.claim_ref:
            raise ValueError("compiled claim record/occurrence identity mismatch")
        if self.history_record.claim_record_ref != self.claim_record.claim_record_ref:
            raise ValueError("compiled claim history does not target compiled claim record")
        if self.history_record.source_ref != self.claim_record.source_ref:
            raise ValueError("compiled claim history/source lineage mismatch")
        _unique(self.evidence_refs, "compiled-claim evidence")
        if not self.evidence_refs:
            raise ValueError("compiled claim requires evidence")


@dataclass(frozen=True, slots=True)
class EpistemicProjection:
    assessment: FourStateTruthAssessment
    knowledge_record: KnowledgeRecord | None
    admission_records: tuple[EpistemicAdmissionRecord, ...]

    def __post_init__(self) -> None:
        refs = {item.admission_ref for item in self.admission_records}
        required = set(self.assessment.support_admission_refs) | set(self.assessment.opposition_admission_refs)
        if refs != required:
            raise ValueError("epistemic projection admission records must exactly match truth lineage")
        if self.knowledge_record is None and self.assessment.truth_status != KnowledgeStatus.UNDETERMINED:
            raise ValueError("determinate epistemic projection requires a knowledge record")
        if self.knowledge_record is not None:
            if self.knowledge_record.proposition_ref != self.assessment.proposition_ref:
                raise ValueError("epistemic projection knowledge proposition mismatch")
            if self.knowledge_record.context_ref != self.assessment.context_ref:
                raise ValueError("epistemic projection knowledge context mismatch")
