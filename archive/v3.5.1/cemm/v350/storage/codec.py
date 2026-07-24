"""Typed record codec registry used by the compiler and overlay store."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from ..schema.codec import record_from_document as schema_record_from_document
from ..schema.codec import record_to_document as schema_record_to_document
from ..schema.model import FacetEntitlement, MeaningSchema, canonical_data, semantic_fingerprint
from ..language.codec import (
    construction_program_from_document,
    construction_from_document,
    form_lexeme_link_from_document,
    form_sense_link_from_document,
    language_form_from_document,
    language_pack_from_document,
    language_record_to_document,
    lexeme_from_document,
    lexeme_sense_link_from_document,
    lexical_sense_from_document,
    morphology_analysis_rule_from_document,
    semantic_contribution_spec_from_document,
)
from ..language.model import (
    ConstructionProgramRecord,
    ConstructionRecord,
    FormLexemeLinkRecord,
    FormSenseLinkRecord,
    LanguageFormRecord,
    LanguagePackRecord,
    LexemeRecord,
    LexemeSenseLinkRecord,
    LexicalSenseRecord,
    MorphologyAnalysisRuleRecord,
    SemanticContributionSpecRecord,
)
from ..transitions.codec import (
    capability_dependency_from_document,
    transition_contract_from_document,
    transition_proof_from_document,
)
from ..transitions.model import (
    CapabilityDependencyRecord,
    TransitionContractRecord,
    TransitionProofRecord,
)
from ..state.codec_v351 import (
    capability_dependency_graph_from_document, capability_dependency_graph_to_document,
    transition_mechanism_from_document, transition_mechanism_to_document,
)
from ..state.model_v351 import TransitionMechanismV351
from ..state.capability_v351 import CapabilityDependencyGraph
from ..causal.codec_v351 import causal_proof_from_document, causal_proof_to_document
from ..causal.model_v351 import CausalProofV351
from ..learning.codec import (
    competence_result_from_document,
    learning_evidence_link_from_document,
    learning_frontier_from_document,
    learning_invalidation_from_document,
    learning_package_from_document,
    promotion_decision_from_document,
)
from ..learning.model import (
    CompetenceResultRecord, LearningEvidenceLink, LearningFrontierRecord,
    LearningInvalidationRecord, LearningPackageRecord, PromotionDecisionRecord,
)
from ..significance.codec import (
    impact_proof_from_document, impact_rule_from_document, importance_evidence_from_document,
    importance_policy_from_document, significance_assessment_from_document,
)
from ..significance.model import (
    ImpactProofRecord, ImpactRuleRecord, ImportanceEvidenceRecord, ImportancePolicyRecord,
    SignificanceAssessmentRecord,
)
from ..goals.codec import (
    goal_candidate_from_document, goal_conflict_from_document, goal_decision_from_document,
    response_policy_rule_from_document, semantic_obligation_from_document,
)
from ..goals.model import (
    GoalCandidateRecord, GoalConflictRecord, GoalDecisionRecord, ResponsePolicyRuleRecord,
    SemanticObligationRecord,
)
from ..operations.codec import (adapter_contract_from_document, operation_authorization_from_document, operation_gate_assessment_from_document, operation_journal_from_document, operation_plan_from_document, operation_reconciliation_from_document, operation_result_from_document)
from ..operations.model import (OperationAdapterContractRecord, OperationAuthorizationRecord, OperationGateAssessmentRecord, OperationJournalRecord, OperationPlanRecord, OperationReconciliationRecord, OperationResultRecord)
from ..realization.codec import (argument_frame_from_document, deep_clause_plan_from_document, linearization_rule_from_document, morphology_rule_from_document, realization_request_from_document, reference_plan_from_document, semantic_analyzer_contract_from_document, semantic_roundtrip_from_document, surface_candidate_from_document)
from ..realization.model import (ArgumentFrameRecord, DeepClausePlanRecord, LinearizationRuleRecord, MorphologyRuleRecord, RealizationRequestRecord, ReferencePlanRecord, SemanticAnalyzerContractRecord, SemanticRoundTripRecord, SurfaceCandidateRecord)
from ..output.codec import (channel_adapter_contract_from_document, literal_emission_policy_from_document, emission_gate_assessment_from_document, emission_authorization_from_document, emission_journal_from_document, emission_from_document, emission_anomaly_from_document, silence_outcome_from_document, output_discourse_act_from_document, output_commitment_from_document, common_ground_from_document, output_reference_anchor_from_document, output_correction_from_document)
from ..output.model import (ChannelAdapterContractRecord, LiteralEmissionPolicyRecord, EmissionGateAssessmentRecord, EmissionAuthorizationRecord, EmissionJournalRecord, EmissionRecord, EmissionAnomalyRecord, SilenceOutcomeRecord, OutputDiscourseActRecord, OutputCommitmentRecord, CommonGroundRecord, OutputReferenceAnchorRecord, OutputCorrectionRecord)
from ..migration_records.codec import (migration_source_from_document, migration_rule_from_document, migration_target_map_from_document, migration_decision_from_document, migration_batch_from_document, migration_quarantine_from_document, migration_intentional_change_from_document, semantic_equivalence_from_document, migration_rollback_from_document)
from ..migration_records.model import (MigrationSourceRecord, MigrationRuleRecord, MigrationTargetMapRecord, MigrationDecisionRecord, MigrationBatchRecord, MigrationQuarantineRecord, MigrationIntentionalChangeRecord, SemanticEquivalenceRecord, MigrationRollbackRecord)
from ..semantic_records.codec import (
    application_from_document,
    capability_delta_from_document,
    claim_from_document,
    event_from_document,
    impact_from_document,
    importance_from_document,
    proposition_from_document,
    referent_from_document,
    state_delta_from_document,
    semantic_record_to_document,
)
from ..semantic_records.model import (
    CapabilityDelta,
    ClaimOccurrence,
    EventOccurrence,
    ImpactAssessment,
    ImportanceAssessment,
    PropositionReferent,
    Referent,
    SemanticApplication,
    StateDelta,
)
from .model import (
    AssertionStatus,
    AssignmentStatus,
    AdmissionDecision,
    AdmissionLifecycleStatus,
    CapabilityInstance,
    ClaimHistoryAction,
    ClaimHistoryRecord,
    ClaimRecord,
    ConditionTruth,
    DefaultRuleRecord,
    DependencyEdge,
    EpistemicAdmissionRecord,
    EvidenceRecord,
    IdentityFacetRecord,
    KnowledgeRecord,
    KnowledgeStatus,
    MaterializedViewRecord,
    RecordKind,
    ReferentTypeAssertion,
    SourceAssessmentRecord,
    StateAssignment,
)


class RecordDecodeError(ValueError):
    pass


Decoder = Callable[[Mapping[str, Any]], Any]
Encoder = Callable[[Any], Mapping[str, Any]]


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise RecordDecodeError("expected an array, not one string")
    return tuple(str(item) for item in value)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RecordDecodeError(f"{label} must be an object")
    return value


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _dataclass_document(value: Any) -> Mapping[str, Any]:
    if not is_dataclass(value):
        raise TypeError(f"record is not a dataclass: {type(value)!r}")
    return canonical_data(value)


def _evidence(value: Mapping[str, Any]) -> EvidenceRecord:
    data = dict(value)
    try:
        return EvidenceRecord(
            evidence_ref=str(data["evidence_ref"]),
            source_ref=str(data["source_ref"]),
            confidence=float(data["confidence"]),
            lineage_ref=str(data["lineage_ref"]),
            context_ref=str(data.get("context_ref", "actual")),
            observed_at=None if data.get("observed_at") is None else str(data["observed_at"]),
            span_start=None if data.get("span_start") is None else int(data["span_start"]),
            span_end=None if data.get("span_end") is None else int(data["span_end"]),
            permission_ref=str(data.get("permission_ref", "conversation")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _type_assertion(value: Mapping[str, Any]) -> ReferentTypeAssertion:
    data = dict(value)
    try:
        return ReferentTypeAssertion(
            assertion_ref=str(data["assertion_ref"]),
            referent_ref=str(data["referent_ref"]),
            type_schema_ref=str(data["type_schema_ref"]),
            type_revision=int(data["type_revision"]),
            status=AssertionStatus(data["status"]),
            confidence=float(data["confidence"]),
            context_ref=str(data["context_ref"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            source_refs=_tuple_str(data.get("source_refs")),
            proof_refs=_tuple_str(data.get("proof_refs")),
            permission_ref=str(data.get("permission_ref", "conversation")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _identity_facet(value: Mapping[str, Any]) -> IdentityFacetRecord:
    data = dict(value)
    try:
        return IdentityFacetRecord(
            identity_facet_ref=str(data["identity_facet_ref"]),
            referent_ref=str(data["referent_ref"]),
            facet_schema_ref=str(data["facet_schema_ref"]),
            normalized_value=str(data["normalized_value"]),
            anchor_ref=None if data.get("anchor_ref") is None else str(data["anchor_ref"]),
            confidence=float(data.get("confidence", 1.0)),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            context_ref=str(data.get("context_ref", "actual")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _source_assessment(value: Mapping[str, Any]) -> SourceAssessmentRecord:
    data = dict(value)
    try:
        return SourceAssessmentRecord(
            assessment_ref=str(data["assessment_ref"]),
            source_ref=str(data["source_ref"]),
            authority=float(data["authority"]),
            reliability=float(data["reliability"]),
            access_quality=float(data["access_quality"]),
            bias_risk=float(data["bias_risk"]),
            context_ref=str(data["context_ref"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            permission_ref=str(data.get("permission_ref", "conversation")),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _claim_record(value: Mapping[str, Any]) -> ClaimRecord:
    data = dict(value)
    try:
        return ClaimRecord(
            claim_record_ref=str(data["claim_record_ref"]),
            claim_occurrence_ref=str(data["claim_occurrence_ref"]),
            proposition_ref=str(data["proposition_ref"]),
            source_ref=str(data["source_ref"]),
            source_context_ref=str(data["source_context_ref"]),
            reported_context_ref=str(data["reported_context_ref"]),
            commitment_strength=float(data["commitment_strength"]),
            permission_ref=str(data.get("permission_ref", "conversation")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            superseded_by=None if data.get("superseded_by") is None else str(data["superseded_by"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _claim_history(value: Mapping[str, Any]) -> ClaimHistoryRecord:
    data = dict(value)
    try:
        return ClaimHistoryRecord(
            history_ref=str(data["history_ref"]),
            claim_record_ref=str(data["claim_record_ref"]),
            action=ClaimHistoryAction(data["action"]),
            source_ref=str(data["source_ref"]),
            context_ref=str(data["context_ref"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            target_claim_record_ref=None if data.get("target_claim_record_ref") is None else str(data["target_claim_record_ref"]),
            occurred_at=None if data.get("occurred_at") is None else str(data["occurred_at"]),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _epistemic_admission(value: Mapping[str, Any]) -> EpistemicAdmissionRecord:
    data = dict(value)
    try:
        return EpistemicAdmissionRecord(
            admission_ref=str(data["admission_ref"]),
            proposition_ref=str(data["proposition_ref"]),
            source_context_ref=str(data["source_context_ref"]),
            target_context_ref=str(data["target_context_ref"]),
            decision=AdmissionDecision(data["decision"]),
            truth_status=KnowledgeStatus(data["truth_status"]),
            confidence=float(data["confidence"]),
            source_refs=_tuple_str(data.get("source_refs")),
            source_assessment_pins=tuple((str(item[0]), int(item[1])) for item in data.get("source_assessment_pins", ())),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            proof_refs=_tuple_str(data.get("proof_refs")),
            policy_ref=str(data["policy_ref"]),
            authorization_ref=None if data.get("authorization_ref") is None else str(data["authorization_ref"]),
            permission_ref=str(data.get("permission_ref", "conversation")),
            sensitivity=str(data.get("sensitivity", "normal")),
            lifecycle_status=AdmissionLifecycleStatus(data.get("lifecycle_status", AdmissionLifecycleStatus.ACTIVE.value)),
            valid_time_ref=None if data.get("valid_time_ref") is None else str(data["valid_time_ref"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            retracts_admission_ref=None if data.get("retracts_admission_ref") is None else str(data["retracts_admission_ref"]),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _knowledge(value: Mapping[str, Any]) -> KnowledgeRecord:
    data = dict(value)
    try:
        return KnowledgeRecord(
            knowledge_ref=str(data["knowledge_ref"]),
            proposition_ref=str(data["proposition_ref"]),
            truth_status=KnowledgeStatus(data["truth_status"]),
            confidence=float(data["confidence"]),
            context_ref=str(data["context_ref"]),
            source_refs=_tuple_str(data.get("source_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            permission_ref=str(data.get("permission_ref", "conversation")),
            sensitivity=str(data.get("sensitivity", "normal")),
            valid_time_ref=None if data.get("valid_time_ref") is None else str(data["valid_time_ref"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            support_lineage_refs=_tuple_str(data.get("support_lineage_refs")),
            derivation_refs=_tuple_str(data.get("derivation_refs")),
            superseded_by=None if data.get("superseded_by") is None else str(data["superseded_by"]),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _state_assignment(value: Mapping[str, Any]) -> StateAssignment:
    data = dict(value)
    try:
        return StateAssignment(
            assignment_ref=str(data["assignment_ref"]),
            holder_ref=str(data["holder_ref"]),
            dimension_ref=str(data["dimension_ref"]),
            dimension_revision=int(data["dimension_revision"]),
            value_ref=str(data["value_ref"]),
            value_revision=int(data["value_revision"]),
            status=AssignmentStatus(data["status"]),
            context_ref=str(data["context_ref"]),
            confidence=float(data["confidence"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            proof_refs=_tuple_str(data.get("proof_refs")),
            source_refs=_tuple_str(data.get("source_refs")),
            value_document=dict(data.get("value_document", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _capability(value: Mapping[str, Any]) -> CapabilityInstance:
    from .model import CapabilityStatus

    data = dict(value)
    try:
        return CapabilityInstance(
            capability_ref=str(data["capability_ref"]),
            holder_ref=str(data["holder_ref"]),
            action_schema_ref=str(data["action_schema_ref"]),
            action_schema_revision=int(data["action_schema_revision"]),
            status=CapabilityStatus(data["status"]),
            confidence=float(data["confidence"]),
            context_ref=str(data["context_ref"]),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            valid_from=None if data.get("valid_from") is None else str(data["valid_from"]),
            valid_to=None if data.get("valid_to") is None else str(data["valid_to"]),
            dependency_refs=_tuple_str(data.get("dependency_refs")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
            proof_refs=_tuple_str(data.get("proof_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _default_rule(value: Mapping[str, Any]) -> DefaultRuleRecord:
    from ..schema.model import SchemaLifecycleStatus

    data = dict(value)
    try:
        return DefaultRuleRecord(
            rule_ref=str(data["rule_ref"]),
            target_facet_ref=str(data["target_facet_ref"]),
            expected_dimension_ref=None if data.get("expected_dimension_ref") is None else str(data["expected_dimension_ref"]),
            expected_dimension_revision=None if data.get("expected_dimension_revision") is None else int(data["expected_dimension_revision"]),
            expected_value_ref=None if data.get("expected_value_ref") is None else str(data["expected_value_ref"]),
            expected_value_revision=None if data.get("expected_value_revision") is None else int(data["expected_value_revision"]),
            holder_type_refs=_tuple_str(data.get("holder_type_refs")),
            condition_refs=_tuple_str(data.get("condition_refs")),
            defeater_refs=_tuple_str(data.get("defeater_refs")),
            context_constraints=_tuple_str(data.get("context_constraints")),
            temporal_constraints=_tuple_str(data.get("temporal_constraints")),
            priority=int(data.get("priority", 0)),
            confidence=float(data.get("confidence", 0.5)),
            lifecycle_status=SchemaLifecycleStatus(data.get("lifecycle_status", SchemaLifecycleStatus.CANDIDATE.value)),
            revision=int(data.get("revision", 1)),
            supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
            scope_ref=str(data.get("scope_ref", "global")),
            permission_ref=str(data.get("permission_ref", "public")),
            evidence_refs=_tuple_str(data.get("evidence_refs")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _dependency(value: Mapping[str, Any]) -> DependencyEdge:
    data = dict(value)
    try:
        prerequisite_kind = data.get("prerequisite_kind")
        return DependencyEdge(
            dependency_ref=str(data["dependency_ref"]),
            dependent_kind=RecordKind(data["dependent_kind"]),
            dependent_ref=str(data["dependent_ref"]),
            dependent_revision=int(data["dependent_revision"]),
            prerequisite_kind=None if prerequisite_kind is None else RecordKind(prerequisite_kind),
            prerequisite_ref=str(data["prerequisite_ref"]),
            prerequisite_revision=None if data.get("prerequisite_revision") is None else int(data["prerequisite_revision"]),
            prerequisite_fingerprint=None if data.get("prerequisite_fingerprint") is None else str(data["prerequisite_fingerprint"]),
            dependency_kind=str(data.get("dependency_kind", "semantic")),
            active=bool(data.get("active", True)),
            metadata=dict(data.get("metadata", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _view(value: Mapping[str, Any]) -> MaterializedViewRecord:
    data = dict(value)
    try:
        return MaterializedViewRecord(
            view_ref=str(data["view_ref"]),
            view_kind=str(data["view_kind"]),
            subject_ref=str(data["subject_ref"]),
            context_ref=str(data["context_ref"]),
            payload=dict(data.get("payload", {})),
            dependency_refs=_tuple_str(data.get("dependency_refs")),
            dependency_fingerprint=str(data["dependency_fingerprint"]),
            snapshot_revision=int(data["snapshot_revision"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordDecodeError(str(exc)) from exc


def _lazy_response_transform_rule_from_document(v):
    from ..response.records_codec_v351 import response_transform_rule_from_document
    return response_transform_rule_from_document(v)

def _lazy_response_transformation_proof_from_document(v):
    from ..response.records_codec_v351 import response_transformation_proof_from_document
    return response_transformation_proof_from_document(v)

def _lazy_response_omission_from_document(v):
    from ..response.records_codec_v351 import response_omission_from_document
    return response_omission_from_document(v)


_DECODERS: Mapping[RecordKind, Decoder] = {
    RecordKind.SCHEMA: schema_record_from_document,
    RecordKind.FACET_ENTITLEMENT: schema_record_from_document,
    RecordKind.REFERENT: referent_from_document,
    RecordKind.TYPE_ASSERTION: _type_assertion,
    RecordKind.IDENTITY_FACET: _identity_facet,
    RecordKind.SEMANTIC_APPLICATION: application_from_document,
    RecordKind.PROPOSITION: proposition_from_document,
    RecordKind.CLAIM_OCCURRENCE: claim_from_document,
    RecordKind.CLAIM_RECORD: _claim_record,
    RecordKind.CLAIM_HISTORY: _claim_history,
    RecordKind.EPISTEMIC_ADMISSION: _epistemic_admission,
    RecordKind.EVENT_OCCURRENCE: event_from_document,
    RecordKind.STATE_ASSIGNMENT: _state_assignment,
    RecordKind.STATE_DELTA: state_delta_from_document,
    RecordKind.CAPABILITY_INSTANCE: _capability,
    RecordKind.CAPABILITY_DELTA: capability_delta_from_document,
    RecordKind.TRANSITION_CONTRACT: lambda value: (
        transition_mechanism_from_document(value)
        if str(value.get("model_version", "")) == "v351"
        else transition_contract_from_document(value)
    ),
    RecordKind.CAPABILITY_DEPENDENCY: lambda value: (
        capability_dependency_graph_from_document(value)
        if str(value.get("model_version", "")) == "capability-dependency-v351"
        else capability_dependency_from_document(value)
    ),
    RecordKind.TRANSITION_PROOF: lambda value: (
        causal_proof_from_document(value)
        if str(value.get("model_version", "")) == "causal-proof-v351"
        else transition_proof_from_document(value)
    ),
    RecordKind.KNOWLEDGE: _knowledge,
    RecordKind.EVIDENCE: _evidence,
    RecordKind.SOURCE_ASSESSMENT: _source_assessment,
    RecordKind.IMPACT_ASSESSMENT: impact_from_document,
    RecordKind.IMPORTANCE_ASSESSMENT: importance_from_document,
    RecordKind.IMPACT_RULE: impact_rule_from_document,
    RecordKind.IMPACT_PROOF: impact_proof_from_document,
    RecordKind.IMPORTANCE_EVIDENCE: importance_evidence_from_document,
    RecordKind.IMPORTANCE_POLICY: importance_policy_from_document,
    RecordKind.SIGNIFICANCE_ASSESSMENT: significance_assessment_from_document,
    RecordKind.RESPONSE_POLICY_RULE: response_policy_rule_from_document,
    RecordKind.SEMANTIC_OBLIGATION: semantic_obligation_from_document,
    RecordKind.GOAL_CANDIDATE: goal_candidate_from_document,
    RecordKind.GOAL_CONFLICT: goal_conflict_from_document,
    RecordKind.GOAL_DECISION: goal_decision_from_document,
    RecordKind.OPERATION_ADAPTER_CONTRACT: adapter_contract_from_document,
    RecordKind.OPERATION_GATE_ASSESSMENT: operation_gate_assessment_from_document,
    RecordKind.OPERATION_PLAN: operation_plan_from_document,
    RecordKind.OPERATION_AUTHORIZATION: operation_authorization_from_document,
    RecordKind.OPERATION_JOURNAL: operation_journal_from_document,
    RecordKind.OPERATION_RESULT: operation_result_from_document,
    RecordKind.OPERATION_RECONCILIATION: operation_reconciliation_from_document,
    RecordKind.RESPONSE_TRANSFORM_RULE: _lazy_response_transform_rule_from_document,
    RecordKind.RESPONSE_TRANSFORMATION_PROOF: _lazy_response_transformation_proof_from_document,
    RecordKind.RESPONSE_OMISSION: _lazy_response_omission_from_document,
    RecordKind.REALIZATION_REQUEST: realization_request_from_document,
    RecordKind.ARGUMENT_FRAME: argument_frame_from_document,
    RecordKind.MORPHOLOGY_RULE: morphology_rule_from_document,
    RecordKind.LINEARIZATION_RULE: linearization_rule_from_document,
    RecordKind.DEEP_CLAUSE_PLAN: deep_clause_plan_from_document,
    RecordKind.REFERENCE_PLAN: reference_plan_from_document,
    RecordKind.SURFACE_CANDIDATE: surface_candidate_from_document,
    RecordKind.SEMANTIC_ROUNDTRIP: semantic_roundtrip_from_document,
    RecordKind.SEMANTIC_ANALYZER_CONTRACT: semantic_analyzer_contract_from_document,
    RecordKind.CHANNEL_ADAPTER_CONTRACT: channel_adapter_contract_from_document,
    RecordKind.LITERAL_EMISSION_POLICY: literal_emission_policy_from_document,
    RecordKind.EMISSION_GATE_ASSESSMENT: emission_gate_assessment_from_document,
    RecordKind.EMISSION_AUTHORIZATION: emission_authorization_from_document,
    RecordKind.EMISSION_JOURNAL: emission_journal_from_document,
    RecordKind.EMISSION: emission_from_document,
    RecordKind.EMISSION_ANOMALY: emission_anomaly_from_document,
    RecordKind.SILENCE_OUTCOME: silence_outcome_from_document,
    RecordKind.OUTPUT_DISCOURSE_ACT: output_discourse_act_from_document,
    RecordKind.OUTPUT_COMMITMENT: output_commitment_from_document,
    RecordKind.COMMON_GROUND: common_ground_from_document,
    RecordKind.OUTPUT_REFERENCE_ANCHOR: output_reference_anchor_from_document,
    RecordKind.OUTPUT_CORRECTION: output_correction_from_document,
    RecordKind.MIGRATION_SOURCE: migration_source_from_document,
    RecordKind.MIGRATION_RULE: migration_rule_from_document,
    RecordKind.MIGRATION_TARGET_MAP: migration_target_map_from_document,
    RecordKind.MIGRATION_DECISION: migration_decision_from_document,
    RecordKind.MIGRATION_BATCH: migration_batch_from_document,
    RecordKind.MIGRATION_QUARANTINE: migration_quarantine_from_document,
    RecordKind.MIGRATION_INTENTIONAL_CHANGE: migration_intentional_change_from_document,
    RecordKind.SEMANTIC_EQUIVALENCE: semantic_equivalence_from_document,
    RecordKind.MIGRATION_ROLLBACK: migration_rollback_from_document,
    RecordKind.DEFAULT_RULE: _default_rule,
    RecordKind.DEPENDENCY: _dependency,
    RecordKind.LANGUAGE_PACK: language_pack_from_document,
    RecordKind.LANGUAGE_FORM: language_form_from_document,
    RecordKind.LEXEME: lexeme_from_document,
    RecordKind.FORM_LEXEME_LINK: form_lexeme_link_from_document,
    RecordKind.LEXICAL_SENSE: lexical_sense_from_document,
    RecordKind.LEXEME_SENSE_LINK: lexeme_sense_link_from_document,
    RecordKind.FORM_SENSE_LINK: form_sense_link_from_document,
    RecordKind.SEMANTIC_CONTRIBUTION_SPEC: semantic_contribution_spec_from_document,
    RecordKind.MORPHOLOGY_ANALYSIS_RULE: morphology_analysis_rule_from_document,
    RecordKind.CONSTRUCTION: construction_from_document,
    RecordKind.CONSTRUCTION_PROGRAM: construction_program_from_document,
    RecordKind.MATERIALIZED_VIEW: _view,
    RecordKind.LEARNING_PACKAGE: learning_package_from_document,
    RecordKind.LEARNING_FRONTIER: learning_frontier_from_document,
    RecordKind.LEARNING_EVIDENCE_LINK: learning_evidence_link_from_document,
    RecordKind.COMPETENCE_RESULT: competence_result_from_document,
    RecordKind.PROMOTION_DECISION: promotion_decision_from_document,
    RecordKind.LEARNING_INVALIDATION: learning_invalidation_from_document,
}


def decode_record(record_kind: RecordKind | str, value: Mapping[str, Any]) -> Any:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    try:
        decoder = _DECODERS[resolved]
        record = decoder(value)
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, RecordDecodeError):
            raise
        raise RecordDecodeError(f"{resolved.value}: {exc}") from exc
    validate_record_kind(resolved, record)
    return record


def encode_record(record_kind: RecordKind | str, record: Any) -> dict[str, Any]:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    validate_record_kind(resolved, record)
    if resolved in {RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT}:
        document = schema_record_to_document(record)
    elif resolved in {
        RecordKind.LANGUAGE_PACK,
        RecordKind.LANGUAGE_FORM,
        RecordKind.LEXEME,
        RecordKind.FORM_LEXEME_LINK,
        RecordKind.LEXICAL_SENSE,
        RecordKind.LEXEME_SENSE_LINK,
        RecordKind.FORM_SENSE_LINK,
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC,
        RecordKind.MORPHOLOGY_ANALYSIS_RULE,
        RecordKind.CONSTRUCTION,
        RecordKind.CONSTRUCTION_PROGRAM,
    }:
        document = language_record_to_document(record)
    elif resolved == RecordKind.TRANSITION_CONTRACT and isinstance(record, TransitionMechanismV351):
        document = transition_mechanism_to_document(record)
    elif resolved == RecordKind.CAPABILITY_DEPENDENCY and isinstance(record, CapabilityDependencyGraph):
        document = capability_dependency_graph_to_document(record)
    elif resolved == RecordKind.TRANSITION_PROOF and isinstance(record, CausalProofV351):
        document = causal_proof_to_document(record)
    elif resolved in {
        RecordKind.REFERENT,
        RecordKind.SEMANTIC_APPLICATION,
        RecordKind.PROPOSITION,
        RecordKind.CLAIM_OCCURRENCE,
        RecordKind.EVENT_OCCURRENCE,
        RecordKind.STATE_DELTA,
        RecordKind.CAPABILITY_DELTA,
        RecordKind.IMPACT_ASSESSMENT,
        RecordKind.IMPORTANCE_ASSESSMENT,
    }:
        document = semantic_record_to_document(record)
    else:
        document = dict(_dataclass_document(record))
    if resolved == RecordKind.CAPABILITY_INSTANCE:
        if document.get("revision") == 1:
            document.pop("revision", None)
        if document.get("supersedes_revision") is None:
            document.pop("supersedes_revision", None)
    return dict(document)


def validate_record_kind(record_kind: RecordKind, record: Any) -> None:
    if record_kind == RecordKind.RESPONSE_UOL:
        raise TypeError("response_uol is migration-only and unavailable to canonical runtime storage")
    from ..response.records_model_v351 import ResponseOmissionRecord, ResponseTransformationProof, ResponseTransformRuleRecord
    expected: Mapping[RecordKind, tuple[type[Any], ...]] = {
        RecordKind.SCHEMA: (MeaningSchema,),
        RecordKind.FACET_ENTITLEMENT: (FacetEntitlement,),
        RecordKind.REFERENT: (Referent,),
        RecordKind.TYPE_ASSERTION: (ReferentTypeAssertion,),
        RecordKind.IDENTITY_FACET: (IdentityFacetRecord,),
        RecordKind.SEMANTIC_APPLICATION: (SemanticApplication,),
        RecordKind.PROPOSITION: (PropositionReferent,),
        RecordKind.CLAIM_OCCURRENCE: (ClaimOccurrence,),
        RecordKind.CLAIM_RECORD: (ClaimRecord,),
        RecordKind.CLAIM_HISTORY: (ClaimHistoryRecord,),
        RecordKind.EPISTEMIC_ADMISSION: (EpistemicAdmissionRecord,),
        RecordKind.EVENT_OCCURRENCE: (EventOccurrence,),
        RecordKind.STATE_ASSIGNMENT: (StateAssignment,),
        RecordKind.STATE_DELTA: (StateDelta,),
        RecordKind.CAPABILITY_INSTANCE: (CapabilityInstance,),
        RecordKind.CAPABILITY_DELTA: (CapabilityDelta,),
        RecordKind.TRANSITION_CONTRACT: (TransitionContractRecord, TransitionMechanismV351),
        RecordKind.CAPABILITY_DEPENDENCY: (CapabilityDependencyRecord, CapabilityDependencyGraph),
        RecordKind.TRANSITION_PROOF: (TransitionProofRecord, CausalProofV351),
        RecordKind.KNOWLEDGE: (KnowledgeRecord,),
        RecordKind.EVIDENCE: (EvidenceRecord,),
        RecordKind.SOURCE_ASSESSMENT: (SourceAssessmentRecord,),
        RecordKind.IMPACT_ASSESSMENT: (ImpactAssessment,),
        RecordKind.IMPORTANCE_ASSESSMENT: (ImportanceAssessment,),
        RecordKind.IMPACT_RULE: (ImpactRuleRecord,),
        RecordKind.IMPACT_PROOF: (ImpactProofRecord,),
        RecordKind.IMPORTANCE_EVIDENCE: (ImportanceEvidenceRecord,),
        RecordKind.IMPORTANCE_POLICY: (ImportancePolicyRecord,),
        RecordKind.SIGNIFICANCE_ASSESSMENT: (SignificanceAssessmentRecord,),
        RecordKind.RESPONSE_POLICY_RULE: (ResponsePolicyRuleRecord,),
        RecordKind.SEMANTIC_OBLIGATION: (SemanticObligationRecord,),
        RecordKind.GOAL_CANDIDATE: (GoalCandidateRecord,),
        RecordKind.GOAL_CONFLICT: (GoalConflictRecord,),
        RecordKind.GOAL_DECISION: (GoalDecisionRecord,),
        RecordKind.OPERATION_ADAPTER_CONTRACT: (OperationAdapterContractRecord,),
        RecordKind.OPERATION_GATE_ASSESSMENT: (OperationGateAssessmentRecord,),
        RecordKind.OPERATION_PLAN: (OperationPlanRecord,),
        RecordKind.OPERATION_AUTHORIZATION: (OperationAuthorizationRecord,),
        RecordKind.OPERATION_JOURNAL: (OperationJournalRecord,),
        RecordKind.OPERATION_RESULT: (OperationResultRecord,),
        RecordKind.OPERATION_RECONCILIATION: (OperationReconciliationRecord,),
        RecordKind.RESPONSE_TRANSFORM_RULE: (ResponseTransformRuleRecord,),
        RecordKind.RESPONSE_TRANSFORMATION_PROOF: (ResponseTransformationProof,),
        RecordKind.RESPONSE_OMISSION: (ResponseOmissionRecord,),
        RecordKind.REALIZATION_REQUEST: (RealizationRequestRecord,),
        RecordKind.ARGUMENT_FRAME: (ArgumentFrameRecord,),
        RecordKind.MORPHOLOGY_RULE: (MorphologyRuleRecord,),
        RecordKind.LINEARIZATION_RULE: (LinearizationRuleRecord,),
        RecordKind.DEEP_CLAUSE_PLAN: (DeepClausePlanRecord,),
        RecordKind.REFERENCE_PLAN: (ReferencePlanRecord,),
        RecordKind.SURFACE_CANDIDATE: (SurfaceCandidateRecord,),
        RecordKind.SEMANTIC_ROUNDTRIP: (SemanticRoundTripRecord,),
        RecordKind.SEMANTIC_ANALYZER_CONTRACT: (SemanticAnalyzerContractRecord,),
        RecordKind.CHANNEL_ADAPTER_CONTRACT: (ChannelAdapterContractRecord,),
        RecordKind.LITERAL_EMISSION_POLICY: (LiteralEmissionPolicyRecord,),
        RecordKind.EMISSION_GATE_ASSESSMENT: (EmissionGateAssessmentRecord,),
        RecordKind.EMISSION_AUTHORIZATION: (EmissionAuthorizationRecord,),
        RecordKind.EMISSION_JOURNAL: (EmissionJournalRecord,),
        RecordKind.EMISSION: (EmissionRecord,),
        RecordKind.EMISSION_ANOMALY: (EmissionAnomalyRecord,),
        RecordKind.SILENCE_OUTCOME: (SilenceOutcomeRecord,),
        RecordKind.OUTPUT_DISCOURSE_ACT: (OutputDiscourseActRecord,),
        RecordKind.OUTPUT_COMMITMENT: (OutputCommitmentRecord,),
        RecordKind.COMMON_GROUND: (CommonGroundRecord,),
        RecordKind.OUTPUT_REFERENCE_ANCHOR: (OutputReferenceAnchorRecord,),
        RecordKind.OUTPUT_CORRECTION: (OutputCorrectionRecord,),
        RecordKind.MIGRATION_SOURCE: (MigrationSourceRecord,),
        RecordKind.MIGRATION_RULE: (MigrationRuleRecord,),
        RecordKind.MIGRATION_TARGET_MAP: (MigrationTargetMapRecord,),
        RecordKind.MIGRATION_DECISION: (MigrationDecisionRecord,),
        RecordKind.MIGRATION_BATCH: (MigrationBatchRecord,),
        RecordKind.MIGRATION_QUARANTINE: (MigrationQuarantineRecord,),
        RecordKind.MIGRATION_INTENTIONAL_CHANGE: (MigrationIntentionalChangeRecord,),
        RecordKind.SEMANTIC_EQUIVALENCE: (SemanticEquivalenceRecord,),
        RecordKind.MIGRATION_ROLLBACK: (MigrationRollbackRecord,),
        RecordKind.DEFAULT_RULE: (DefaultRuleRecord,),
        RecordKind.DEPENDENCY: (DependencyEdge,),
        RecordKind.LANGUAGE_PACK: (LanguagePackRecord,),
        RecordKind.LANGUAGE_FORM: (LanguageFormRecord,),
        RecordKind.LEXEME: (LexemeRecord,),
        RecordKind.FORM_LEXEME_LINK: (FormLexemeLinkRecord,),
        RecordKind.LEXICAL_SENSE: (LexicalSenseRecord,),
        RecordKind.LEXEME_SENSE_LINK: (LexemeSenseLinkRecord,),
        RecordKind.FORM_SENSE_LINK: (FormSenseLinkRecord,),
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC: (SemanticContributionSpecRecord,),
        RecordKind.MORPHOLOGY_ANALYSIS_RULE: (MorphologyAnalysisRuleRecord,),
        RecordKind.CONSTRUCTION: (ConstructionRecord,),
        RecordKind.CONSTRUCTION_PROGRAM: (ConstructionProgramRecord,),
        RecordKind.MATERIALIZED_VIEW: (MaterializedViewRecord,),
        RecordKind.LEARNING_PACKAGE: (LearningPackageRecord,),
        RecordKind.LEARNING_FRONTIER: (LearningFrontierRecord,),
        RecordKind.LEARNING_EVIDENCE_LINK: (LearningEvidenceLink,),
        RecordKind.COMPETENCE_RESULT: (CompetenceResultRecord,),
        RecordKind.PROMOTION_DECISION: (PromotionDecisionRecord,),
        RecordKind.LEARNING_INVALIDATION: (LearningInvalidationRecord,),
    }
    if not isinstance(record, expected[record_kind]):
        names = ", ".join(item.__name__ for item in expected[record_kind])
        raise TypeError(f"{record_kind.value} requires {names}, got {type(record).__name__}")
    if record_kind == RecordKind.SCHEMA and isinstance(record, FacetEntitlement):
        raise TypeError("facet entitlement must use facet_entitlement record kind")


def record_ref(record_kind: RecordKind | str, record: Any) -> str:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    validate_record_kind(resolved, record)
    attributes: Mapping[RecordKind, str] = {
        RecordKind.SCHEMA: "schema_ref",
        RecordKind.FACET_ENTITLEMENT: "entitlement_ref",
        RecordKind.REFERENT: "referent_ref",
        RecordKind.TYPE_ASSERTION: "assertion_ref",
        RecordKind.IDENTITY_FACET: "identity_facet_ref",
        RecordKind.SEMANTIC_APPLICATION: "application_ref",
        RecordKind.PROPOSITION: "proposition_ref",
        RecordKind.CLAIM_OCCURRENCE: "claim_ref",
        RecordKind.CLAIM_RECORD: "claim_record_ref",
        RecordKind.CLAIM_HISTORY: "history_ref",
        RecordKind.EPISTEMIC_ADMISSION: "admission_ref",
        RecordKind.SOURCE_ASSESSMENT: "assessment_ref",
        RecordKind.EVENT_OCCURRENCE: "event_ref",
        RecordKind.STATE_ASSIGNMENT: "assignment_ref",
        RecordKind.STATE_DELTA: "delta_ref",
        RecordKind.CAPABILITY_INSTANCE: "capability_ref",
        RecordKind.CAPABILITY_DELTA: "delta_ref",
        RecordKind.TRANSITION_CONTRACT: "contract_ref",
        RecordKind.CAPABILITY_DEPENDENCY: "dependency_ref",
        RecordKind.TRANSITION_PROOF: "proof_ref",
        RecordKind.KNOWLEDGE: "knowledge_ref",
        RecordKind.EVIDENCE: "evidence_ref",
        RecordKind.IMPACT_ASSESSMENT: "assessment_ref",
        RecordKind.IMPORTANCE_ASSESSMENT: "assessment_ref",
        RecordKind.IMPACT_RULE: "rule_ref",
        RecordKind.IMPACT_PROOF: "proof_ref",
        RecordKind.IMPORTANCE_EVIDENCE: "evidence_ref",
        RecordKind.IMPORTANCE_POLICY: "policy_ref",
        RecordKind.SIGNIFICANCE_ASSESSMENT: "assessment_ref",
        RecordKind.RESPONSE_POLICY_RULE: "rule_ref",
        RecordKind.SEMANTIC_OBLIGATION: "obligation_ref",
        RecordKind.GOAL_CANDIDATE: "goal_ref",
        RecordKind.GOAL_CONFLICT: "conflict_ref",
        RecordKind.GOAL_DECISION: "decision_ref",
        RecordKind.OPERATION_ADAPTER_CONTRACT: "contract_ref",
        RecordKind.OPERATION_GATE_ASSESSMENT: "assessment_ref",
        RecordKind.OPERATION_PLAN: "plan_ref",
        RecordKind.OPERATION_AUTHORIZATION: "authorization_ref",
        RecordKind.OPERATION_JOURNAL: "journal_ref",
        RecordKind.OPERATION_RESULT: "result_ref",
        RecordKind.OPERATION_RECONCILIATION: "reconciliation_ref",
        RecordKind.RESPONSE_TRANSFORM_RULE: "rule_ref",
        RecordKind.RESPONSE_TRANSFORMATION_PROOF: "proof_ref",
        RecordKind.RESPONSE_OMISSION: "omission_ref",
        RecordKind.RESPONSE_UOL: "response_ref",
        RecordKind.REALIZATION_REQUEST: "request_ref",
        RecordKind.ARGUMENT_FRAME: "frame_ref",
        RecordKind.MORPHOLOGY_RULE: "rule_ref",
        RecordKind.LINEARIZATION_RULE: "rule_ref",
        RecordKind.DEEP_CLAUSE_PLAN: "clause_ref",
        RecordKind.REFERENCE_PLAN: "reference_ref",
        RecordKind.SURFACE_CANDIDATE: "candidate_ref",
        RecordKind.SEMANTIC_ROUNDTRIP: "roundtrip_ref",
        RecordKind.SEMANTIC_ANALYZER_CONTRACT: "contract_ref",
        RecordKind.CHANNEL_ADAPTER_CONTRACT: "contract_ref",
        RecordKind.LITERAL_EMISSION_POLICY: "policy_ref",
        RecordKind.EMISSION_GATE_ASSESSMENT: "assessment_ref",
        RecordKind.EMISSION_AUTHORIZATION: "authorization_ref",
        RecordKind.EMISSION_JOURNAL: "journal_ref",
        RecordKind.EMISSION: "emission_ref",
        RecordKind.EMISSION_ANOMALY: "anomaly_ref",
        RecordKind.SILENCE_OUTCOME: "silence_ref",
        RecordKind.OUTPUT_DISCOURSE_ACT: "discourse_ref",
        RecordKind.OUTPUT_COMMITMENT: "commitment_ref",
        RecordKind.COMMON_GROUND: "ground_ref",
        RecordKind.OUTPUT_REFERENCE_ANCHOR: "anchor_ref",
        RecordKind.OUTPUT_CORRECTION: "correction_ref",
        RecordKind.MIGRATION_SOURCE: "source_ref",
        RecordKind.MIGRATION_RULE: "rule_ref",
        RecordKind.MIGRATION_TARGET_MAP: "map_ref",
        RecordKind.MIGRATION_DECISION: "decision_ref",
        RecordKind.MIGRATION_BATCH: "batch_ref",
        RecordKind.MIGRATION_QUARANTINE: "quarantine_ref",
        RecordKind.MIGRATION_INTENTIONAL_CHANGE: "change_ref",
        RecordKind.SEMANTIC_EQUIVALENCE: "equivalence_ref",
        RecordKind.MIGRATION_ROLLBACK: "rollback_ref",
        RecordKind.DEFAULT_RULE: "rule_ref",
        RecordKind.DEPENDENCY: "dependency_ref",
        RecordKind.LANGUAGE_PACK: "pack_ref",
        RecordKind.LANGUAGE_FORM: "form_ref",
        RecordKind.LEXEME: "lexeme_ref",
        RecordKind.FORM_LEXEME_LINK: "link_ref",
        RecordKind.LEXICAL_SENSE: "sense_ref",
        RecordKind.LEXEME_SENSE_LINK: "link_ref",
        RecordKind.FORM_SENSE_LINK: "link_ref",
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC: "spec_ref",
        RecordKind.MORPHOLOGY_ANALYSIS_RULE: "rule_ref",
        RecordKind.CONSTRUCTION: "construction_ref",
        RecordKind.CONSTRUCTION_PROGRAM: "program_ref",
        RecordKind.MATERIALIZED_VIEW: "view_ref",
        RecordKind.LEARNING_PACKAGE: "package_ref",
        RecordKind.LEARNING_FRONTIER: "frontier_ref",
        RecordKind.LEARNING_EVIDENCE_LINK: "link_ref",
        RecordKind.COMPETENCE_RESULT: "result_ref",
        RecordKind.PROMOTION_DECISION: "decision_ref",
        RecordKind.LEARNING_INVALIDATION: "invalidation_ref",
    }
    return str(getattr(record, attributes[resolved]))


def record_revision(record_kind: RecordKind | str, record: Any, fallback: int = 1) -> int:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    validate_record_kind(resolved, record)
    if resolved in {
        RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT,
        RecordKind.REFERENT, RecordKind.DEFAULT_RULE, RecordKind.CAPABILITY_INSTANCE,
        RecordKind.LANGUAGE_PACK, RecordKind.LANGUAGE_FORM, RecordKind.LEXEME,
        RecordKind.FORM_LEXEME_LINK, RecordKind.LEXICAL_SENSE,
        RecordKind.LEXEME_SENSE_LINK, RecordKind.FORM_SENSE_LINK,
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC,
        RecordKind.MORPHOLOGY_ANALYSIS_RULE, RecordKind.CONSTRUCTION,
        RecordKind.CONSTRUCTION_PROGRAM, RecordKind.CLAIM_HISTORY, RecordKind.EPISTEMIC_ADMISSION, RecordKind.SOURCE_ASSESSMENT,
        RecordKind.TRANSITION_CONTRACT, RecordKind.CAPABILITY_DEPENDENCY,
        RecordKind.LEARNING_PACKAGE, RecordKind.LEARNING_FRONTIER,
        RecordKind.LEARNING_EVIDENCE_LINK, RecordKind.COMPETENCE_RESULT,
        RecordKind.PROMOTION_DECISION, RecordKind.LEARNING_INVALIDATION,
        RecordKind.IMPACT_RULE, RecordKind.IMPACT_PROOF, RecordKind.IMPORTANCE_EVIDENCE,
        RecordKind.IMPORTANCE_POLICY, RecordKind.SIGNIFICANCE_ASSESSMENT,
        RecordKind.RESPONSE_POLICY_RULE, RecordKind.SEMANTIC_OBLIGATION,
        RecordKind.GOAL_CANDIDATE, RecordKind.GOAL_CONFLICT, RecordKind.GOAL_DECISION,
        RecordKind.OPERATION_ADAPTER_CONTRACT, RecordKind.OPERATION_GATE_ASSESSMENT, RecordKind.OPERATION_PLAN, RecordKind.OPERATION_AUTHORIZATION,
        RecordKind.OPERATION_JOURNAL, RecordKind.OPERATION_RESULT, RecordKind.OPERATION_RECONCILIATION,
        RecordKind.RESPONSE_TRANSFORM_RULE, RecordKind.RESPONSE_TRANSFORMATION_PROOF, RecordKind.RESPONSE_OMISSION, RecordKind.RESPONSE_UOL,
        RecordKind.REALIZATION_REQUEST, RecordKind.ARGUMENT_FRAME, RecordKind.MORPHOLOGY_RULE, RecordKind.LINEARIZATION_RULE,
        RecordKind.DEEP_CLAUSE_PLAN, RecordKind.REFERENCE_PLAN, RecordKind.SURFACE_CANDIDATE, RecordKind.SEMANTIC_ROUNDTRIP, RecordKind.SEMANTIC_ANALYZER_CONTRACT,
        RecordKind.CHANNEL_ADAPTER_CONTRACT, RecordKind.LITERAL_EMISSION_POLICY, RecordKind.EMISSION_GATE_ASSESSMENT, RecordKind.EMISSION_AUTHORIZATION,
        RecordKind.EMISSION_JOURNAL, RecordKind.EMISSION, RecordKind.EMISSION_ANOMALY, RecordKind.SILENCE_OUTCOME, RecordKind.OUTPUT_DISCOURSE_ACT, RecordKind.OUTPUT_COMMITMENT,
        RecordKind.COMMON_GROUND, RecordKind.OUTPUT_REFERENCE_ANCHOR, RecordKind.OUTPUT_CORRECTION, RecordKind.MIGRATION_SOURCE, RecordKind.MIGRATION_RULE,
        RecordKind.MIGRATION_TARGET_MAP, RecordKind.MIGRATION_DECISION, RecordKind.MIGRATION_BATCH, RecordKind.MIGRATION_QUARANTINE,
        RecordKind.MIGRATION_INTENTIONAL_CHANGE, RecordKind.SEMANTIC_EQUIVALENCE, RecordKind.MIGRATION_ROLLBACK,
    }:
        return int(getattr(record, "revision"))
    if resolved == RecordKind.PROPOSITION:
        return int(record.referent.revision)
    if resolved in {RecordKind.CLAIM_OCCURRENCE, RecordKind.EVENT_OCCURRENCE}:
        return int(record.referent.revision)
    return int(fallback)


def record_context(record_kind: RecordKind | str, record: Any) -> str | None:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    if hasattr(record, "context_ref"):
        return str(getattr(record, "context_ref"))
    if resolved == RecordKind.REFERENT:
        return str(record.context_refs[0]) if record.context_refs else None
    if resolved == RecordKind.PROPOSITION:
        return str(record.context_ref)
    if resolved == RecordKind.CLAIM_OCCURRENCE:
        return str(record.source_context_ref)
    if resolved == RecordKind.CLAIM_HISTORY:
        return str(record.context_ref)
    if resolved == RecordKind.EPISTEMIC_ADMISSION:
        return str(record.target_context_ref)
    return None


def record_lifecycle(record_kind: RecordKind | str, record: Any) -> str | None:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    if resolved == RecordKind.LEARNING_FRONTIER:
        return str(record.resolution_status.value)
    if resolved == RecordKind.COMPETENCE_RESULT:
        return str(record.outcome.value)
    if resolved == RecordKind.PROMOTION_DECISION:
        return str(record.decision.value)
    if resolved == RecordKind.LEARNING_INVALIDATION:
        return str(record.status.value)
    if resolved in {RecordKind.SEMANTIC_ANALYZER_CONTRACT, RecordKind.CHANNEL_ADAPTER_CONTRACT, RecordKind.LITERAL_EMISSION_POLICY}:
        return "active" if bool(getattr(record, "active", False)) else "inactive"
    if resolved in {
        RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT, RecordKind.DEFAULT_RULE,
        RecordKind.LANGUAGE_PACK, RecordKind.LANGUAGE_FORM, RecordKind.LEXEME,
        RecordKind.FORM_LEXEME_LINK, RecordKind.LEXICAL_SENSE,
        RecordKind.LEXEME_SENSE_LINK, RecordKind.FORM_SENSE_LINK,
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC, RecordKind.MORPHOLOGY_ANALYSIS_RULE,
        RecordKind.CONSTRUCTION, RecordKind.CONSTRUCTION_PROGRAM, RecordKind.EPISTEMIC_ADMISSION,
        RecordKind.TRANSITION_CONTRACT, RecordKind.CAPABILITY_DEPENDENCY,
        RecordKind.LEARNING_PACKAGE, RecordKind.IMPACT_RULE, RecordKind.IMPORTANCE_POLICY,
        RecordKind.RESPONSE_POLICY_RULE, RecordKind.RESPONSE_TRANSFORM_RULE,
        RecordKind.ARGUMENT_FRAME, RecordKind.MORPHOLOGY_RULE, RecordKind.LINEARIZATION_RULE, RecordKind.MIGRATION_RULE,
    }:
        return str(getattr(record.lifecycle_status, "value", record.lifecycle_status))
    if hasattr(record, "status"):
        return str(_enum_value(getattr(record, "status")))
    if resolved == RecordKind.EVENT_OCCURRENCE:
        return str(record.occurrence_status.value)
    return None


def record_permission(record_kind: RecordKind | str, record: Any) -> str | None:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    if hasattr(record, "permission_ref"):
        return str(getattr(record, "permission_ref"))
    if resolved == RecordKind.PROPOSITION:
        return str(record.referent.permission_ref)
    if resolved in {RecordKind.CLAIM_OCCURRENCE, RecordKind.EVENT_OCCURRENCE}:
        return str(record.referent.permission_ref)
    return None


def record_interval(record_kind: RecordKind | str, record: Any) -> tuple[str | None, str | None]:
    del record_kind
    return getattr(record, "valid_from", None), getattr(record, "valid_to", None)


def record_fingerprints(record_kind: RecordKind | str, record: Any) -> tuple[str, str]:
    resolved = record_kind if isinstance(record_kind, RecordKind) else RecordKind(record_kind)
    document = encode_record(resolved, record)
    if resolved in {RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT}:
        return record.content_fingerprint, record.record_fingerprint
    content_document = dict(document)
    for key in (
        "evidence_refs", "proof_refs", "provenance_refs", "source_refs", "source_assessment_pins",
        "authorization_ref", "metadata",
        "confidence", "revision", "superseded_by",
    ):
        content_document.pop(key, None)
    return (
        semantic_fingerprint(f"{resolved.value}-content", content_document, 64),
        semantic_fingerprint(f"{resolved.value}-record", document, 64),
    )
