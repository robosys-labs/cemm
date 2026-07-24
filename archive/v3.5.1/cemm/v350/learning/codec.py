"""Deterministic codecs for durable Phase-13 learning records."""
from __future__ import annotations

from typing import Any, Mapping

from ..schema.model import SchemaClass, UseAuthorization, UseDecision, UseOperation, canonical_data
from ..storage.model import RecordKind
from .model import (
    CompetenceOutcome,
    CompetenceResultRecord,
    EvidencePolarity,
    FrontierResolutionStatus,
    InvalidationStatus,
    LearningEvidenceLink,
    LearningFrontierRecord,
    LearningInvalidationRecord,
    LearningPackageRecord,
    LearningPackageStatus,
    PinnedRecord,
    PromotionDecisionKind,
    PromotionDecisionRecord,
    PromotionUseGrant,
)


def learning_record_to_document(record: Any) -> dict[str, Any]:
    return dict(canonical_data(record))


def _pin(value: Mapping[str, Any]) -> PinnedRecord:
    return PinnedRecord(
        RecordKind(str(value["record_kind"])),
        str(value["record_ref"]),
        int(value["revision"]),
        str(value["record_fingerprint"]),
    )


def _pins(values: Any) -> tuple[PinnedRecord, ...]:
    return tuple(_pin(dict(item)) for item in (values or ()))


def _use_authorizations(values: Any) -> tuple[UseAuthorization, ...]:
    return tuple(
        UseAuthorization(
            UseOperation(str(item["operation"])),
            UseDecision(str(item["decision"])),
            tuple(str(value) for value in item.get("evidence_refs", ())),
            str(item.get("reason", "")),
        )
        for item in (values or ())
    )


def _grant(value: Mapping[str, Any]) -> PromotionUseGrant:
    return PromotionUseGrant(
        candidate_pin=_pin(dict(value["candidate_pin"])),
        operation=UseOperation(str(value["operation"])),
        decision=UseDecision(str(value["decision"])),
        competence_result_refs=tuple(str(item) for item in value.get("competence_result_refs", ())),
        evidence_refs=tuple(str(item) for item in value.get("evidence_refs", ())),
        reason=str(value.get("reason", "")),
    )


def learning_package_from_document(value: Mapping[str, Any]) -> LearningPackageRecord:
    data = dict(value)
    return LearningPackageRecord(
        package_ref=str(data["package_ref"]),
        package_family=str(data["package_family"]),
        candidate_pins=_pins(data.get("candidate_pins")),
        dependency_pins=_pins(data.get("dependency_pins")),
        frontier_refs=tuple(str(item) for item in data.get("frontier_refs", ())),
        evidence_link_refs=tuple(str(item) for item in data.get("evidence_link_refs", ())),
        counterexample_link_refs=tuple(str(item) for item in data.get("counterexample_link_refs", ())),
        competence_case_refs=tuple(str(item) for item in data.get("competence_case_refs", ())),
        requested_use_authorizations=_use_authorizations(data.get("requested_use_authorizations")),
        promotion_policy_ref=str(data["promotion_policy_ref"]),
        review_refs=tuple(str(item) for item in data.get("review_refs", ())),
        provenance_refs=tuple(str(item) for item in data.get("provenance_refs", ())),
        source_lineage_refs=tuple(str(item) for item in data.get("source_lineage_refs", ())),
        scope_ref=str(data.get("scope_ref", "global")),
        permission_ref=str(data.get("permission_ref", "conversation")),
        sensitivity=str(data.get("sensitivity", "normal")),
        lifecycle_status=LearningPackageStatus(str(data.get("lifecycle_status", "candidate"))),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        metadata=dict(data.get("metadata", {})),
    )


def learning_frontier_from_document(value: Mapping[str, Any]) -> LearningFrontierRecord:
    data = dict(value)
    return LearningFrontierRecord(
        frontier_ref=str(data["frontier_ref"]),
        missing_contract=str(data["missing_contract"]),
        expected_record_kinds=tuple(RecordKind(str(item)) for item in data.get("expected_record_kinds", ())),
        expected_schema_classes=tuple(SchemaClass(str(item)) for item in data.get("expected_schema_classes", ())),
        accepted_anchor_types=tuple(str(item) for item in data.get("accepted_anchor_types", ())),
        evidence_refs=tuple(str(item) for item in data.get("evidence_refs", ())),
        candidate_refs=tuple(str(item) for item in data.get("candidate_refs", ())),
        target_ref=None if data.get("target_ref") is None else str(data["target_ref"]),
        dependency_depth=int(data.get("dependency_depth", 0)),
        sensitivity=str(data.get("sensitivity", "normal")),
        best_question_uol_ref=None if data.get("best_question_uol_ref") is None else str(data["best_question_uol_ref"]),
        resolution_status=FrontierResolutionStatus(str(data.get("resolution_status", "open"))),
        context_ref=str(data.get("context_ref", "actual")),
        permission_ref=str(data.get("permission_ref", "conversation")),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        metadata=dict(data.get("metadata", {})),
    )


def learning_evidence_link_from_document(value: Mapping[str, Any]) -> LearningEvidenceLink:
    data = dict(value)
    return LearningEvidenceLink(
        link_ref=str(data["link_ref"]),
        package_ref=str(data["package_ref"]),
        package_revision=int(data["package_revision"]),
        polarity=EvidencePolarity(str(data["polarity"])),
        evidence_refs=tuple(str(item) for item in data.get("evidence_refs", ())),
        source_lineage_refs=tuple(str(item) for item in data.get("source_lineage_refs", ())),
        candidate_pin=None if data.get("candidate_pin") is None else _pin(dict(data["candidate_pin"])),
        context_ref=str(data.get("context_ref", "actual")),
        time_ref=None if data.get("time_ref") is None else str(data["time_ref"]),
        weight=float(data.get("weight", 1.0)),
        permission_ref=str(data.get("permission_ref", "conversation")),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        metadata=dict(data.get("metadata", {})),
    )


def competence_result_from_document(value: Mapping[str, Any]) -> CompetenceResultRecord:
    data = dict(value)
    return CompetenceResultRecord(
        result_ref=str(data["result_ref"]),
        package_ref=str(data["package_ref"]),
        package_revision=int(data["package_revision"]),
        use_operation=UseOperation(str(data["use_operation"])),
        candidate_pins=_pins(data.get("candidate_pins")),
        dependency_pins=_pins(data.get("dependency_pins")),
        case_refs=tuple(str(item) for item in data.get("case_refs", ())),
        outcome=CompetenceOutcome(str(data["outcome"])),
        passed_case_refs=tuple(str(item) for item in data.get("passed_case_refs", ())),
        failed_case_refs=tuple(str(item) for item in data.get("failed_case_refs", ())),
        counterexample_refs=tuple(str(item) for item in data.get("counterexample_refs", ())),
        proof_refs=tuple(str(item) for item in data.get("proof_refs", ())),
        failure_frontier_refs=tuple(str(item) for item in data.get("failure_frontier_refs", ())),
        snapshot_revision=int(data["snapshot_revision"]),
        boot_fingerprint=str(data["boot_fingerprint"]),
        overlay_fingerprint=str(data["overlay_fingerprint"]),
        runner_ref=str(data["runner_ref"]),
        runner_revision=str(data["runner_revision"]),
        independent_lineage_refs=tuple(str(item) for item in data.get("independent_lineage_refs", ())),
        environment_refs=tuple(str(item) for item in data.get("environment_refs", ())),
        performance_ms=tuple((str(item[0]), float(item[1])) for item in data.get("performance_ms", ())),
        permission_ref=str(data.get("permission_ref", "internal")),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        metadata=dict(data.get("metadata", {})),
    )


def promotion_decision_from_document(value: Mapping[str, Any]) -> PromotionDecisionRecord:
    data = dict(value)
    return PromotionDecisionRecord(
        decision_ref=str(data["decision_ref"]),
        package_ref=str(data["package_ref"]),
        package_revision=int(data["package_revision"]),
        decision=PromotionDecisionKind(str(data["decision"])),
        candidate_pins=_pins(data.get("candidate_pins")),
        use_grants=tuple(_grant(dict(item)) for item in data.get("use_grants", ())),
        policy_ref=str(data["policy_ref"]),
        review_refs=tuple(str(item) for item in data.get("review_refs", ())),
        authorization_refs=tuple(str(item) for item in data.get("authorization_refs", ())),
        risk_refs=tuple(str(item) for item in data.get("risk_refs", ())),
        reason_refs=tuple(str(item) for item in data.get("reason_refs", ())),
        scope_ref=str(data.get("scope_ref", "global")),
        permission_ref=str(data.get("permission_ref", "internal")),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        metadata=dict(data.get("metadata", {})),
    )


def learning_invalidation_from_document(value: Mapping[str, Any]) -> LearningInvalidationRecord:
    data = dict(value)
    return LearningInvalidationRecord(
        invalidation_ref=str(data["invalidation_ref"]),
        trigger_pins=_pins(data.get("trigger_pins")),
        affected_pins=_pins(data.get("affected_pins")),
        package_refs=tuple(str(item) for item in data.get("package_refs", ())),
        invalidated_decision_refs=tuple(str(item) for item in data.get("invalidated_decision_refs", ())),
        recomputation_frontier_refs=tuple(str(item) for item in data.get("recomputation_frontier_refs", ())),
        replay_required_refs=tuple(str(item) for item in data.get("replay_required_refs", ())),
        reason=str(data["reason"]),
        status=InvalidationStatus(str(data["status"])),
        evidence_refs=tuple(str(item) for item in data.get("evidence_refs", ())),
        proof_refs=tuple(str(item) for item in data.get("proof_refs", ())),
        context_ref=str(data.get("context_ref", "actual")),
        permission_ref=str(data.get("permission_ref", "internal")),
        revision=int(data.get("revision", 1)),
        supersedes_revision=None if data.get("supersedes_revision") is None else int(data["supersedes_revision"]),
        metadata=dict(data.get("metadata", {})),
    )
