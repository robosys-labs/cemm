"""Cycle-local prediction-error and learning-work contracts for Phase 14."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..csir.model import CSIRGraph
from ..language.model import ConstructionKind, ConstructionSlot, SenseTargetKind
from ..schema.model import SchemaClass, UseAuthorization, UseOperation, semantic_fingerprint
from ..storage.model import RecordKind
from .model import LearningFrontierRecord, PinnedRecord
from .package import CandidateProposal


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class PredictionErrorFamily(StrEnum):
    FORM_NORMALIZATION = "form_normalization"
    LEXICALIZATION = "lexicalization"
    SENSE = "sense"
    CONSTRUCTION = "construction"
    IDENTITY_GROUNDING = "identity_grounding"
    SEMANTIC_DEFINITION = "semantic_definition"
    STATE_SCHEMA = "state_schema"
    OBSERVATION_CALIBRATION = "observation_calibration"
    ROLE_TRANSITION = "role_transition"
    CAUSAL_STRUCTURE = "causal_structure"
    CAUSAL_PARAMETER = "causal_parameter"
    CONTEXT_TIME = "context_time"
    CAPABILITY_DEPENDENCY = "capability_dependency"
    DISCOURSE = "discourse"
    IMPACT_GOAL = "impact_goal"
    RESPONSE_REALIZATION = "response_realization"
    DYNAMICS_PARAMETER = "dynamics_parameter"


@dataclass(frozen=True, slots=True)
class SemanticPredictionV351:
    prediction_ref: str
    family: PredictionErrorFamily
    expected_refs: tuple[str, ...]
    source_artifact_refs: tuple[str, ...]
    authority_pins: tuple[PinnedRecord, ...] = ()
    confidence: float = 1.0
    context_ref: str = "actual"
    permission_ref: str = "conversation"

    def __post_init__(self) -> None:
        _ref(self.prediction_ref, "prediction_ref")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("prediction confidence must be finite in [0,1]")
        _unique(self.expected_refs, "prediction expected refs")
        _unique(self.source_artifact_refs, "prediction source refs")
        _unique(tuple(item.key for item in self.authority_pins), "prediction authority pins")


@dataclass(frozen=True, slots=True)
class PredictionErrorV351:
    error_ref: str
    family: PredictionErrorFamily
    predicted_refs: tuple[str, ...]
    observed_refs: tuple[str, ...]
    missing_refs: tuple[str, ...]
    conflicting_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    frontier_ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.error_ref, "prediction error_ref")
        for values, label in (
            (self.predicted_refs, "predicted refs"), (self.observed_refs, "observed refs"),
            (self.missing_refs, "missing refs"), (self.conflicting_refs, "conflicting refs"),
            (self.evidence_refs, "error evidence refs"), (self.source_lineage_refs, "error lineage refs"),
        ):
            _unique(values, label)


@dataclass(frozen=True, slots=True)
class NovelFormSignal:
    signal_ref: str
    observation_ref: str
    pack_pin: PinnedRecord
    language_tag: str
    written_form: str
    normalized_form: str
    script: str
    category: str
    token_count: int
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    permission_ref: str = "conversation"

    def __post_init__(self) -> None:
        _ref(self.signal_ref, "novel form signal_ref")
        _ref(self.observation_ref, "novel form observation_ref")
        if not self.written_form or (not self.normalized_form and self.token_count > 0):
            raise ValueError("novel form signal requires written/normalized form")
        if self.token_count < 1:
            raise ValueError("novel non-zero form token_count must be positive")
        if not self.evidence_refs or not self.source_lineage_refs:
            raise ValueError("novel form induction requires evidence and source lineage")


@dataclass(frozen=True, slots=True)
class LexicalTargetSignal:
    signal_ref: str
    form_signal_ref: str
    pack_pin: PinnedRecord
    target_pin: PinnedRecord
    target_kind: SenseTargetKind
    target_schema_class: SchemaClass | None
    use_operation: UseOperation
    lexical_category: str
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    competence_case_refs: tuple[str, ...]
    requested_uses: tuple[UseAuthorization, ...]
    permission_ref: str = "conversation"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.signal_ref, "lexical target signal_ref")
        _ref(self.form_signal_ref, "lexical target form signal_ref")
        if not self.evidence_refs or not self.source_lineage_refs:
            raise ValueError("lexical target induction requires evidence and lineage")
        if not self.competence_case_refs:
            raise ValueError("lexical target requires explicit competence cases before executable promotion")
        _unique(self.competence_case_refs, "lexical target competence cases")
        _unique(tuple(item.operation for item in self.requested_uses), "lexical target requested uses")


@dataclass(frozen=True, slots=True)
class ConstructionPatternSignal:
    signal_ref: str
    pack_pin: PinnedRecord
    construction_kind: ConstructionKind
    slots: tuple[ConstructionSlot, ...]
    trigger_form_pins: tuple[PinnedRecord, ...]
    trigger_sense_pins: tuple[PinnedRecord, ...]
    output_schema_pin: PinnedRecord | None
    output_schema_class: SchemaClass | None
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    competence_case_refs: tuple[str, ...]
    requested_uses: tuple[UseAuthorization, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.signal_ref, "construction pattern signal_ref")
        if not self.slots:
            raise ValueError("construction pattern requires structural slots")
        if not self.evidence_refs or not self.source_lineage_refs:
            raise ValueError("construction pattern requires evidence and lineage")
        if not self.competence_case_refs:
            raise ValueError("construction candidate requires competence cases")
        _unique(tuple(item.slot_ref for item in self.slots), "construction signal slots")
        _unique(tuple(item.key for item in self.trigger_form_pins), "construction trigger form pins")
        _unique(tuple(item.key for item in self.trigger_sense_pins), "construction trigger sense pins")


@dataclass(frozen=True, slots=True)
class ExactStructuralCandidateSignal:
    """Typed evidence for a candidate whose semantic payload is already structurally derived.

    This is intentionally not a free-form template: the payload must be a canonical record
    object of ``record_kind``, and every semantic/executable dependency is exact-pinned.
    The corresponding inducer still validates family-specific structural invariants.
    """

    signal_ref: str
    family: PredictionErrorFamily
    record_kind: RecordKind
    payload: Any
    dependency_pins: tuple[PinnedRecord, ...]
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    competence_case_refs: tuple[str, ...]
    requested_uses: tuple[UseAuthorization, ...]
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.signal_ref, "structural candidate signal_ref")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("candidate confidence must be finite in [0,1]")
        if not self.evidence_refs or not self.source_lineage_refs:
            raise ValueError("structural candidate requires evidence and independent lineage accounting")
        _unique(tuple(item.key for item in self.dependency_pins), "structural candidate dependency pins")
        _unique(self.competence_case_refs, "structural candidate competence cases")


@dataclass(frozen=True, slots=True)
class ParameterTrainingExample:
    example_ref: str
    feature_values: tuple[tuple[str, float], ...]
    expected_semantic_class_ref: str
    observed_semantic_class_ref: str | None
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.example_ref, "parameter example_ref")
        _ref(self.expected_semantic_class_ref, "expected semantic class")
        _unique(tuple(name for name, _ in self.feature_values), "parameter example features")
        if any(not isfinite(value) for _, value in self.feature_values):
            raise ValueError("parameter training features must be finite")
        if not self.evidence_refs or not self.source_lineage_refs:
            raise ValueError("parameter training requires attributable evidence")


@dataclass(frozen=True, slots=True)
class DynamicsParameterCandidateV351:
    candidate_ref: str
    base_parameter_pins: tuple[Any, ...]
    candidate_artifacts: tuple[Any, ...]
    training_example_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    objective_before: float
    objective_after: float
    calibration_required: bool = True

    def __post_init__(self) -> None:
        _ref(self.candidate_ref, "dynamics parameter candidate_ref")
        if not self.candidate_artifacts:
            raise ValueError("parameter candidate requires immutable candidate artifacts")
        _unique(tuple(getattr(pin, "key", repr(pin)) for pin in self.base_parameter_pins), "base parameter pins")
        _unique(self.training_example_refs, "parameter training examples")
        _unique(self.evidence_refs, "parameter candidate evidence")
        _unique(self.source_lineage_refs, "parameter candidate lineages")
        if not isfinite(self.objective_before) or not isfinite(self.objective_after):
            raise ValueError("parameter objectives must be finite")
        if self.objective_after > self.objective_before:
            raise ValueError("parameter candidate may not claim an objective regression as training improvement")


@dataclass(frozen=True, slots=True)
class LearningCandidateWorkItemV351:
    work_ref: str
    frontier: LearningFrontierRecord
    proposals: tuple[CandidateProposal, ...]
    source_lineage_refs: tuple[str, ...]
    requested_uses: tuple[UseAuthorization, ...]
    competence_case_refs: tuple[str, ...]
    review_refs: tuple[str, ...] = ()
    authorization_refs: tuple[str, ...] = ()
    risk_refs: tuple[str, ...] = ()
    promotion_policy_ref: str = "policy:v351:reviewed-learning-promotion"
    deferred_reason_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.work_ref, "learning work_ref")
        _unique(tuple((item.record_kind.value, repr(item.payload)) for item in self.proposals), "learning proposals")
        _unique(self.source_lineage_refs, "learning work source lineages")
        _unique(tuple(item.operation for item in self.requested_uses), "learning work requested uses")
        _unique(self.competence_case_refs, "learning work competence cases")
        _unique(self.review_refs, "learning work reviews")
        _unique(self.authorization_refs, "learning work authorizations")
        _unique(self.risk_refs, "learning work risks")
        _unique(self.deferred_reason_refs, "learning work deferred reasons")


@dataclass(frozen=True, slots=True)
class LearningAdvanceBatchV351:
    batch_ref: str
    prediction_errors: tuple[PredictionErrorV351, ...]
    frontiers: tuple[LearningFrontierRecord, ...]
    candidate_work: tuple[LearningCandidateWorkItemV351, ...]
    parameter_candidates: tuple[DynamicsParameterCandidateV351, ...]
    learning_question_candidates: tuple[str, ...]
    source_artifact_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str

    def __post_init__(self) -> None:
        _ref(self.batch_ref, "learning batch_ref")
        _unique(tuple(item.error_ref for item in self.prediction_errors), "prediction errors")
        _unique(tuple(item.frontier_ref for item in self.frontiers), "learning frontiers")
        _unique(tuple(item.work_ref for item in self.candidate_work), "learning candidate work")
        _unique(tuple(item.candidate_ref for item in self.parameter_candidates), "parameter candidates")
        _unique(self.learning_question_candidates, "learning questions")
        _unique(self.source_artifact_refs, "learning source artifacts")


@dataclass(frozen=True, slots=True)
class PromotionEventV351:
    event_ref: str
    package_refs: tuple[str, ...]
    trigger_record_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.event_ref, "promotion event_ref")
        if not self.package_refs:
            raise ValueError("promotion event must target explicit packages")
        _unique(self.package_refs, "promotion event packages")
        _unique(self.trigger_record_refs, "promotion event triggers")
        _unique(self.reason_refs, "promotion event reasons")


@dataclass(frozen=True, slots=True)
class PromotionMaintenanceResultV351:
    result_ref: str
    promoted_package_refs: tuple[str, ...]
    decision_refs: tuple[str, ...]
    authority_generation_before: int
    authority_generation_after: int
    restart_required: bool
    replay_requirement_refs: tuple[str, ...]
    blocked_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TeachingProjectionEvidenceV351:
    """Generic construction-authorized teaching projection; never phrase-specific.

    A reviewed construction/adapter emits this only when its exact metadata states that
    one surface observation denotes an exact semantic target under the construction's
    semantic projection.  Phase 14 consumes the projection; it never infers it from word
    order, grammatical subject/object labels, or English strings.
    """
    projection_ref: str
    form_signal_ref: str
    target_pin: PinnedRecord
    target_kind: SenseTargetKind
    target_schema_class: SchemaClass | None
    use_operation: UseOperation
    construction_pin: PinnedRecord
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    competence_case_refs: tuple[str, ...]
    requested_uses: tuple[UseAuthorization, ...]
    lexical_category: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.projection_ref, "teaching projection_ref")
        _ref(self.form_signal_ref, "teaching form signal_ref")
        if not self.evidence_refs or not self.source_lineage_refs:
            raise ValueError("teaching projection requires evidence and independent lineage")
        if not self.competence_case_refs:
            raise ValueError("teaching projection requires competence cases before executable promotion")
        _unique(self.evidence_refs, "teaching projection evidence")
        _unique(self.source_lineage_refs, "teaching projection lineages")
        _unique(self.competence_case_refs, "teaching projection competence cases")
        _unique(tuple(item.operation for item in self.requested_uses), "teaching projection requested uses")


@dataclass(frozen=True, slots=True)
class DefinitionTeachingProjectionV351:
    """Reviewed construction evidence that introduces a genuinely new semantic subtype.

    The form is only an identity/linguistic anchor.  Semantic content comes from the exact
    parent schema and the reviewed construction relation; raw wording is never interpreted
    by the learning kernel.  Phase 14 currently activates this direct construction-derived
    path only for referent-type subtype introduction. Other schema families still enter via
    ``ExactStructuralCandidateSignal`` and ``SemanticDefinitionInducer``.
    """
    projection_ref: str
    form_signal_ref: str
    parent_schema_pin: PinnedRecord
    parent_schema_class: SchemaClass
    construction_pin: PinnedRecord
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    competence_case_refs: tuple[str, ...]
    requested_uses: tuple[UseAuthorization, ...]
    lexical_category: str = ""
    definition_relation: str = "subtype"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.projection_ref, "definition teaching projection_ref")
        _ref(self.form_signal_ref, "definition teaching form signal_ref")
        if self.parent_schema_pin.record_kind is not RecordKind.SCHEMA:
            raise ValueError("definition teaching parent must be an exact schema pin")
        if self.definition_relation != "subtype":
            raise ValueError("direct definition teaching currently supports only the structural subtype relation")
        if not self.evidence_refs or not self.source_lineage_refs:
            raise ValueError("definition teaching requires evidence and independent lineage")
        if not self.competence_case_refs:
            raise ValueError("definition teaching requires competence cases before executable promotion")
        _unique(self.evidence_refs, "definition teaching evidence")
        _unique(self.source_lineage_refs, "definition teaching lineages")
        _unique(self.competence_case_refs, "definition teaching competence cases")
        _unique(tuple(item.operation for item in self.requested_uses), "definition teaching requested uses")


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty")


def _unique(values, label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


__all__ = [name for name in globals() if name.endswith("V351") or name in {
    "PredictionErrorFamily", "NovelFormSignal", "LexicalTargetSignal",
    "ConstructionPatternSignal", "ExactStructuralCandidateSignal", "ParameterTrainingExample",
}]
