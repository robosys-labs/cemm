"""Deterministic codecs for Phase-15 goal/policy records."""
from __future__ import annotations

from typing import Any, Mapping

from ..learning.codec import _pin
from ..schema.model import SchemaLifecycleStatus, UseDecision, UseOperation, canonical_data
from ..storage.model import RecordKind
from .model import (
    GoalCandidateRecord, GoalConflictRecord, GoalDecisionRecord, ResponsePolicyRuleRecord,
    SemanticObligationRecord, TargetSelector, TargetSelectorMode,
)


def goal_record_to_document(record: Any) -> dict[str, Any]:
    return dict(canonical_data(record))


def _selector(value: Mapping[str, Any]) -> TargetSelector:
    d = dict(value)
    return TargetSelector(TargetSelectorMode(str(d["mode"])), d.get("port_ref"), d.get("fixed_ref"))


def response_policy_rule_from_document(value: Mapping[str, Any]) -> ResponsePolicyRuleRecord:
    d = dict(value)
    return ResponsePolicyRuleRecord(
        rule_ref=str(d["rule_ref"]), trigger_record_kinds=tuple(RecordKind(str(x)) for x in d.get("trigger_record_kinds", ())),
        trigger_schema_pins=tuple((str(x[0]), int(x[1])) for x in d.get("trigger_schema_pins", ())),
        goal_schema_ref=str(d["goal_schema_ref"]), goal_schema_revision=int(d["goal_schema_revision"]),
        goal_operation=UseOperation(str(d["goal_operation"])), target_selectors=tuple(_selector(x) for x in d.get("target_selectors", ())),
        priority=int(d.get("priority", 0)), require_permission=bool(d.get("require_permission", True)),
        require_epistemic_support=bool(d.get("require_epistemic_support", False)), require_capability=bool(d.get("require_capability", False)),
        block_on_open_frontier=bool(d.get("block_on_open_frontier", False)), conflict_key_refs=tuple(map(str, d.get("conflict_key_refs", ()))),
        prohibition=bool(d.get("prohibition", False)), lifecycle_status=SchemaLifecycleStatus(str(d.get("lifecycle_status", SchemaLifecycleStatus.CANDIDATE.value))),
        use_operation=UseOperation(str(d.get("use_operation", UseOperation.RESPONSE_POLICY.value))), use_decision=UseDecision(str(d.get("use_decision", UseDecision.DENY.value))),
        permission_ref=str(d.get("permission_ref", "public")), revision=int(d.get("revision", 1)),
        supersedes_revision=None if d.get("supersedes_revision") is None else int(d["supersedes_revision"]), metadata=dict(d.get("metadata", {})),
    )


def semantic_obligation_from_document(value: Mapping[str, Any]) -> SemanticObligationRecord:
    d = dict(value)
    return SemanticObligationRecord(
        obligation_ref=str(d["obligation_ref"]), policy_rule_pin=_pin(dict(d["policy_rule_pin"])),
        source_pins=tuple(_pin(dict(x)) for x in d.get("source_pins", ())), target_refs=tuple(map(str, d.get("target_refs", ()))),
        goal_schema_ref=str(d["goal_schema_ref"]), goal_schema_revision=int(d["goal_schema_revision"]), required_operation=UseOperation(str(d["required_operation"])),
        priority=int(d["priority"]), permission_ref=str(d["permission_ref"]), sensitivity=str(d.get("sensitivity", "normal")),
        prerequisite_frontier_refs=tuple(map(str, d.get("prerequisite_frontier_refs", ()))), impact_refs=tuple(map(str, d.get("impact_refs", ()))),
        importance_refs=tuple(map(str, d.get("importance_refs", ()))), reason_refs=tuple(map(str, d.get("reason_refs", ()))),
        proof_refs=tuple(map(str, d.get("proof_refs", ()))), revision=int(d.get("revision", 1)), metadata=dict(d.get("metadata", {})),
    )


def goal_candidate_from_document(value: Mapping[str, Any]) -> GoalCandidateRecord:
    d = dict(value)
    return GoalCandidateRecord(
        goal_ref=str(d["goal_ref"]), goal_schema_ref=str(d["goal_schema_ref"]), goal_schema_revision=int(d["goal_schema_revision"]), operation=UseOperation(str(d["operation"])),
        target_refs=tuple(map(str, d.get("target_refs", ()))), obligation_refs=tuple(map(str, d.get("obligation_refs", ()))),
        policy_rule_pins=tuple(_pin(dict(x)) for x in d.get("policy_rule_pins", ())), source_pins=tuple(_pin(dict(x)) for x in d.get("source_pins", ())),
        authorization_refs=tuple(map(str, d.get("authorization_refs", ()))), prerequisite_frontier_refs=tuple(map(str, d.get("prerequisite_frontier_refs", ()))),
        impact_refs=tuple(map(str, d.get("impact_refs", ()))), importance_refs=tuple(map(str, d.get("importance_refs", ()))), risk_refs=tuple(map(str, d.get("risk_refs", ()))),
        reason_refs=tuple(map(str, d.get("reason_refs", ()))), proof_refs=tuple(map(str, d.get("proof_refs", ()))), permission_ref=str(d.get("permission_ref", "conversation")),
        sensitivity=str(d.get("sensitivity", "normal")), authorized=bool(d.get("authorized", False)), denial_reasons=tuple(map(str, d.get("denial_reasons", ()))),
        priority=int(d.get("priority", 0)), utility_score=float(d.get("utility_score", 0.0)), revision=int(d.get("revision", 1)), metadata=dict(d.get("metadata", {})),
    )


def goal_conflict_from_document(value: Mapping[str, Any]) -> GoalConflictRecord:
    d = dict(value)
    return GoalConflictRecord(str(d["conflict_ref"]), tuple(map(str, d.get("competing_goal_refs", ()))), tuple(map(str, d.get("target_refs", ()))), tuple(map(str, d.get("conflict_key_refs", ()))), tuple(map(str, d.get("reason_refs", ()))), tuple(map(str, d.get("unresolved_frontier_refs", ()))), int(d.get("revision", 1)))


def goal_decision_from_document(value: Mapping[str, Any]) -> GoalDecisionRecord:
    d = dict(value)
    return GoalDecisionRecord(
        decision_ref=str(d["decision_ref"]), candidate_pins=tuple(_pin(dict(x)) for x in d.get("candidate_pins", ())),
        selected_goal_refs=tuple(map(str, d.get("selected_goal_refs", ()))), rejected_goal_refs=tuple(map(str, d.get("rejected_goal_refs", ()))),
        deferred_goal_refs=tuple(map(str, d.get("deferred_goal_refs", ()))), conflict_refs=tuple(map(str, d.get("conflict_refs", ()))),
        arbitration_policy_ref=str(d["arbitration_policy_ref"]), authorization_refs=tuple(map(str, d.get("authorization_refs", ()))), reason_refs=tuple(map(str, d.get("reason_refs", ()))),
        snapshot_revision=int(d["snapshot_revision"]), snapshot_fingerprint=str(d["snapshot_fingerprint"]), boot_fingerprint=str(d.get("boot_fingerprint", "")),
        overlay_fingerprint=str(d.get("overlay_fingerprint", "")), context_ref=str(d["context_ref"]), permission_ref=str(d["permission_ref"]),
        revision=int(d.get("revision", 1)), supersedes_revision=None if d.get("supersedes_revision") is None else int(d["supersedes_revision"]), metadata=dict(d.get("metadata", {})),
    )
