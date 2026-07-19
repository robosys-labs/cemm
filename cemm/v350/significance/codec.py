"""Deterministic codecs for Phase-14 significance records."""
from __future__ import annotations

from typing import Any, Mapping

from ..learning.codec import _pin
from ..schema.model import SchemaLifecycleStatus, UseDecision, UseOperation, canonical_data
from ..storage.model import RecordKind
from ..uol.codec import impact_from_document, importance_from_document
from ..uol.model import ChangeOperation, Reversibility, Valence
from .model import (
    ImpactProofRecord,
    ImpactRuleRecord,
    ImportanceEvidencePolarity,
    ImportanceEvidenceRecord,
    ImportancePolicyRecord,
    SignificanceAssessmentRecord,
)


def significance_record_to_document(record: Any) -> dict[str, Any]:
    return dict(canonical_data(record))


def impact_rule_from_document(value: Mapping[str, Any]) -> ImpactRuleRecord:
    d = dict(value)
    return ImpactRuleRecord(
        rule_ref=str(d["rule_ref"]),
        source_record_kinds=tuple(RecordKind(str(x)) for x in d.get("source_record_kinds", ())),
        source_schema_pins=tuple((str(x[0]), int(x[1])) for x in d.get("source_schema_pins", ())),
        stakeholder_port_refs=tuple(map(str, d.get("stakeholder_port_refs", ()))),
        affected_port_refs=tuple(map(str, d.get("affected_port_refs", ()))),
        fixed_stakeholder_refs=tuple(map(str, d.get("fixed_stakeholder_refs", ()))),
        fixed_affected_refs=tuple(map(str, d.get("fixed_affected_refs", ()))),
        affected_facet_refs=tuple(map(str, d.get("affected_facet_refs", ()))),
        direction=ChangeOperation(str(d.get("direction", ChangeOperation.ACTIVATE.value))),
        valence=Valence(str(d.get("valence", Valence.NEUTRAL.value))),
        reversibility=Reversibility(str(d.get("reversibility", Reversibility.UNKNOWN.value))),
        magnitude_ref=None if d.get("magnitude_ref") is None else str(d["magnitude_ref"]),
        duration_ref=None if d.get("duration_ref") is None else str(d["duration_ref"]),
        confidence=float(d.get("confidence", 1.0)),
        priority=int(d.get("priority", 0)),
        context_constraints=tuple(map(str, d.get("context_constraints", ()))),
        prerequisite_proof_kinds=tuple(RecordKind(str(x)) for x in d.get("prerequisite_proof_kinds", ())),
        use_operation=UseOperation(str(d.get("use_operation", UseOperation.IMPACT.value))),
        lifecycle_status=SchemaLifecycleStatus(str(d.get("lifecycle_status", SchemaLifecycleStatus.CANDIDATE.value))),
        use_decision=UseDecision(str(d.get("use_decision", UseDecision.DENY.value))),
        permission_ref=str(d.get("permission_ref", "public")),
        revision=int(d.get("revision", 1)),
        supersedes_revision=None if d.get("supersedes_revision") is None else int(d["supersedes_revision"]),
        metadata=dict(d.get("metadata", {})),
    )


def impact_proof_from_document(value: Mapping[str, Any]) -> ImpactProofRecord:
    d = dict(value)
    return ImpactProofRecord(
        proof_ref=str(d["proof_ref"]), source_pin=_pin(dict(d["source_pin"])), rule_pin=_pin(dict(d["rule_pin"])),
        stakeholder_ref=str(d["stakeholder_ref"]), affected_ref=str(d["affected_ref"]), context_ref=str(d["context_ref"]),
        permission_ref=str(d["permission_ref"]), binding_evidence_refs=tuple(map(str, d.get("binding_evidence_refs", ()))),
        prerequisite_proof_refs=tuple(map(str, d.get("prerequisite_proof_refs", ()))), confidence=float(d.get("confidence", 1.0)),
        revision=int(d.get("revision", 1)), metadata=dict(d.get("metadata", {})),
    )


def importance_evidence_from_document(value: Mapping[str, Any]) -> ImportanceEvidenceRecord:
    d = dict(value)
    return ImportanceEvidenceRecord(
        evidence_ref=str(d["evidence_ref"]), subject_ref=str(d["subject_ref"]), stakeholder_ref=str(d["stakeholder_ref"]),
        channel_schema_ref=str(d["channel_schema_ref"]), channel_schema_revision=int(d["channel_schema_revision"]),
        source_pin=_pin(dict(d["source_pin"])), polarity=ImportanceEvidencePolarity(str(d["polarity"])), weight=float(d["weight"]),
        context_ref=str(d["context_ref"]), permission_ref=str(d["permission_ref"]), reason_refs=tuple(map(str, d.get("reason_refs", ()))),
        proof_refs=tuple(map(str, d.get("proof_refs", ()))), valid_time_ref=None if d.get("valid_time_ref") is None else str(d["valid_time_ref"]),
        revision=int(d.get("revision", 1)), metadata=dict(d.get("metadata", {})),
    )


def importance_policy_from_document(value: Mapping[str, Any]) -> ImportancePolicyRecord:
    d = dict(value)
    return ImportancePolicyRecord(
        policy_ref=str(d["policy_ref"]), channel_weights=tuple((str(x[0]), int(x[1]), float(x[2])) for x in d.get("channel_weights", ())),
        low_threshold=float(d["low_threshold"]), high_threshold=float(d["high_threshold"]),
        lifecycle_status=SchemaLifecycleStatus(str(d.get("lifecycle_status", SchemaLifecycleStatus.CANDIDATE.value))),
        use_operation=UseOperation(str(d.get("use_operation", UseOperation.IMPACT.value))), use_decision=UseDecision(str(d.get("use_decision", UseDecision.DENY.value))),
        permission_ref=str(d.get("permission_ref", "public")), revision=int(d.get("revision", 1)),
        supersedes_revision=None if d.get("supersedes_revision") is None else int(d["supersedes_revision"]), metadata=dict(d.get("metadata", {})),
    )


def significance_assessment_from_document(value: Mapping[str, Any]) -> SignificanceAssessmentRecord:
    d = dict(value)
    return SignificanceAssessmentRecord(
        assessment_ref=str(d["assessment_ref"]), source_pin=_pin(dict(d["source_pin"])), rule_pin=_pin(dict(d["rule_pin"])),
        proof_ref=str(d["proof_ref"]), impact=impact_from_document(dict(d["impact"])),
        importance=None if d.get("importance") is None else importance_from_document(dict(d["importance"])),
        importance_evidence_refs=tuple(map(str, d.get("importance_evidence_refs", ()))),
        importance_policy_pin=None if d.get("importance_policy_pin") is None else _pin(dict(d["importance_policy_pin"])),
        frontier_refs=tuple(map(str, d.get("frontier_refs", ()))), context_ref=str(d["context_ref"]), permission_ref=str(d["permission_ref"]),
        revision=int(d.get("revision", 1)), supersedes_revision=None if d.get("supersedes_revision") is None else int(d["supersedes_revision"]),
        metadata=dict(d.get("metadata", {})),
    )
