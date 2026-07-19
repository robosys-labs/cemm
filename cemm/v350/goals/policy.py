"""Structural Phase-15 obligation derivation, authorization and arbitration."""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ..learning.model import FrontierResolutionStatus, LearningFrontierRecord, PinnedRecord
from ..schema.model import UseOperation, semantic_fingerprint
from ..significance.model import SignificanceAssessmentRecord
from ..storage.model import KnowledgeStatus, RecordKind
from ..uol.model import CapabilityStatus
from ..uol.model import ClaimOccurrence, EventOccurrence, FillerRef, SemanticApplication
from .model import (
    GoalCandidateRecord, GoalConflictRecord, ResponsePolicyRuleRecord, SemanticObligationRecord,
    TargetSelectorMode,
)


class ResponsePolicyRegistry:
    def __init__(self, rules: Iterable[ResponsePolicyRuleRecord]) -> None:
        self._rules = tuple(r for r in rules if r.executable)

    def candidates(self, source_kind: RecordKind, source_payload: object) -> tuple[ResponsePolicyRuleRecord, ...]:
        schema_pin = _schema_pin(source_payload)
        result = []
        for rule in self._rules:
            if source_kind not in rule.trigger_record_kinds:
                continue
            if rule.trigger_schema_pins and schema_pin not in rule.trigger_schema_pins:
                continue
            result.append(rule)
        return tuple(sorted(result, key=lambda r: (-r.priority, r.rule_ref, r.revision)))


class ObligationDeriver:
    def __init__(self, store) -> None:
        self.store = store

    def derive(self, source_pin: PinnedRecord, rule: ResponsePolicyRuleRecord, rule_pin: PinnedRecord) -> SemanticObligationRecord | None:
        stored = self.store.get_record(source_pin.record_kind, source_pin.record_ref, source_pin.revision)
        if stored is None or stored.record_fingerprint != source_pin.record_fingerprint:
            raise ValueError("stale source pin during obligation derivation")
        if not rule.executable:
            raise ValueError("candidate/provisional response policy cannot execute")
        targets = self._targets(stored.payload, rule)
        if rule.prohibition:
            return None
        if not targets:
            return None
        frontier_refs = ()
        if isinstance(stored.payload, LearningFrontierRecord) and stored.payload.resolution_status == FrontierResolutionStatus.OPEN:
            frontier_refs = (stored.payload.frontier_ref,)
        obligation_ref = "obligation:" + semantic_fingerprint(
            "semantic-obligation-ref", (source_pin.key, rule_pin.key, targets, rule.goal_schema_ref, rule.goal_operation.value), 24
        )
        return SemanticObligationRecord(
            obligation_ref=obligation_ref, policy_rule_pin=rule_pin, source_pins=(source_pin,), target_refs=targets,
            goal_schema_ref=rule.goal_schema_ref, goal_schema_revision=rule.goal_schema_revision, required_operation=rule.goal_operation,
            priority=rule.priority, permission_ref=stored.permission_ref or getattr(stored.payload, "permission_ref", "conversation"),
            prerequisite_frontier_refs=frontier_refs, reason_refs=(rule.rule_ref,),
        )

    def _targets(self, source: object, rule: ResponsePolicyRuleRecord) -> tuple[str, ...]:
        result: list[str] = []
        for selector in rule.target_selectors:
            if selector.mode == TargetSelectorMode.SOURCE:
                result.append(_primary_ref(source))
            elif selector.mode == TargetSelectorMode.SOURCE_PROPOSITION:
                value = getattr(source, "proposition_ref", None)
                if value:
                    result.append(str(value))
            elif selector.mode == TargetSelectorMode.FRONTIER_TARGET and isinstance(source, LearningFrontierRecord):
                if source.target_ref:
                    result.append(source.target_ref)
            elif selector.mode == TargetSelectorMode.SIGNIFICANCE_STAKEHOLDER and isinstance(source, SignificanceAssessmentRecord):
                result.append(source.impact.stakeholder_ref)
            elif selector.mode == TargetSelectorMode.SIGNIFICANCE_AFFECTED and isinstance(source, SignificanceAssessmentRecord):
                result.append(source.impact.affected_ref)
            elif selector.mode == TargetSelectorMode.APPLICATION_PORT:
                app = _application(source, self.store)
                if app is not None:
                    for binding in app.bindings:
                        if binding.port_ref == selector.port_ref:
                            result.extend(f.ref for f in binding.fillers if isinstance(f, FillerRef))
            elif selector.mode == TargetSelectorMode.FIXED and selector.fixed_ref:
                result.append(selector.fixed_ref)
        return tuple(sorted(set(filter(None, result))))


class GoalAuthorizationGate:
    def __init__(self, store) -> None:
        self.store = store

    def authorize(self, candidate: GoalCandidateRecord, rule: ResponsePolicyRuleRecord) -> GoalCandidateRecord:
        denial: list[str] = []
        auth_refs: list[str] = []
        if rule.require_permission:
            for pin in candidate.source_pins:
                stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
                if stored is None or stored.record_fingerprint != pin.record_fingerprint:
                    denial.append("stale_source")
                    continue
                permission = stored.permission_ref or getattr(stored.payload, "permission_ref", "conversation")
                if permission not in {"public", candidate.permission_ref}:
                    denial.append("permission_scope_mismatch")
        if rule.block_on_open_frontier and candidate.prerequisite_frontier_refs:
            denial.append("open_prerequisite_frontier")
        if rule.require_epistemic_support:
            for target in candidate.target_refs:
                matches = [
                    item.payload for item in self.store.records(RecordKind.KNOWLEDGE)
                    if getattr(item.payload, "proposition_ref", None) == target
                    and getattr(item.payload, "status", None) == KnowledgeStatus.SUPPORTED
                    and (item.permission_ref in {None, "public", candidate.permission_ref})
                ]
                if not matches:
                    denial.append(f"no_epistemic_support:{target}")
                else:
                    auth_refs.extend(getattr(item, "knowledge_ref", "") for item in matches)
        if rule.require_capability:
            app_targets = []
            for target in candidate.target_refs:
                stored = self.store.get_record(RecordKind.SEMANTIC_APPLICATION, target)
                if stored is not None and isinstance(stored.payload, SemanticApplication):
                    app_targets.append(stored.payload)
            if not app_targets:
                denial.append("execute_goal_missing_action_application")
            for app in app_targets:
                holders = {
                    filler.ref for binding in app.bindings for filler in binding.fillers if isinstance(filler, FillerRef)
                }
                capabilities = [
                    item.payload for item in self.store.records(RecordKind.CAPABILITY_INSTANCE)
                    if getattr(item.payload, "action_schema_ref", None) == app.schema_ref
                    and getattr(item.payload, "action_schema_revision", None) == app.schema_revision
                    and getattr(item.payload, "status", None) == CapabilityStatus.AVAILABLE
                    and getattr(item.payload, "holder_ref", None) in holders
                ]
                if not capabilities:
                    denial.append(f"no_live_capability_for_target:{app.application_ref}")
                else:
                    auth_refs.extend(getattr(item, "capability_ref", "") for item in capabilities)
        denial = sorted(set(denial))
        return replace(
            candidate,
            authorized=not denial,
            authorization_refs=tuple(sorted(set(filter(None, (*candidate.authorization_refs, *auth_refs))))),
            denial_reasons=tuple(denial),
        )


class GoalConflictDetector:
    def detect(self, candidates: Iterable[GoalCandidateRecord]) -> tuple[GoalConflictRecord, ...]:
        items = tuple(candidates)
        result = []
        for i, left in enumerate(items):
            left_keys = set(left.metadata.get("conflict_key_refs", ()))
            for right in items[i + 1:]:
                if not set(left.target_refs).intersection(right.target_refs):
                    continue
                right_keys = set(right.metadata.get("conflict_key_refs", ()))
                if left.operation == right.operation and not left_keys.intersection(right_keys):
                    continue
                ref = "goal-conflict:" + semantic_fingerprint(
                    "goal-conflict-ref", (left.goal_ref, right.goal_ref, tuple(sorted(set(left.target_refs) & set(right.target_refs)))), 24
                )
                result.append(GoalConflictRecord(
                    conflict_ref=ref, competing_goal_refs=tuple(sorted((left.goal_ref, right.goal_ref))),
                    target_refs=tuple(sorted(set(left.target_refs).intersection(right.target_refs))),
                    conflict_key_refs=tuple(sorted(left_keys.union(right_keys))), reason_refs=("structural_goal_conflict",),
                ))
        return tuple(result)


class GoalArbitrator:
    """Authorization first; utility never grants authority."""

    def select(self, candidates: Iterable[GoalCandidateRecord], conflicts: Iterable[GoalConflictRecord]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        items = tuple(candidates)
        unauthorized = {item.goal_ref for item in items if not item.authorized}
        blocked_by_conflict: set[str] = set()
        conflict_map = {ref for c in conflicts for ref in c.competing_goal_refs}
        eligible = [item for item in items if item.authorized]
        eligible.sort(key=lambda item: (-item.priority, -item.utility_score, item.goal_ref))
        selected: list[str] = []
        selected_targets: set[str] = set()
        for item in eligible:
            if item.goal_ref in conflict_map and selected_targets.intersection(item.target_refs):
                blocked_by_conflict.add(item.goal_ref)
                continue
            selected.append(item.goal_ref)
            selected_targets.update(item.target_refs)
        rejected = tuple(sorted(unauthorized | blocked_by_conflict))
        deferred = tuple(sorted(item.goal_ref for item in items if item.goal_ref not in set(selected) | set(rejected)))
        return tuple(selected), rejected, deferred


def build_candidate(obligation: SemanticObligationRecord, *, utility_score: float = 0.0, metadata=None) -> GoalCandidateRecord:
    ref = "goal:" + semantic_fingerprint(
        "goal-candidate-ref", (obligation.obligation_ref, obligation.target_refs, obligation.goal_schema_ref, obligation.required_operation.value), 24
    )
    return GoalCandidateRecord(
        goal_ref=ref, goal_schema_ref=obligation.goal_schema_ref, goal_schema_revision=obligation.goal_schema_revision,
        operation=obligation.required_operation, target_refs=obligation.target_refs, obligation_refs=(obligation.obligation_ref,),
        policy_rule_pins=(obligation.policy_rule_pin,), source_pins=obligation.source_pins, authorization_refs=(),
        prerequisite_frontier_refs=obligation.prerequisite_frontier_refs, impact_refs=obligation.impact_refs,
        importance_refs=obligation.importance_refs, reason_refs=obligation.reason_refs, proof_refs=obligation.proof_refs,
        permission_ref=obligation.permission_ref, sensitivity=obligation.sensitivity, priority=obligation.priority,
        utility_score=utility_score, metadata=dict(metadata or {}),
    )


def _schema_pin(payload: object):
    if isinstance(payload, SemanticApplication):
        return payload.schema_ref, payload.schema_revision
    return None


def _application(payload: object, store):
    if isinstance(payload, SemanticApplication):
        return payload
    if isinstance(payload, EventOccurrence):
        stored = store.get_record(RecordKind.SEMANTIC_APPLICATION, payload.participant_application_ref)
        return None if stored is None else stored.payload
    return None


def _primary_ref(payload: object) -> str:
    for name in (
        "application_ref", "proposition_ref", "claim_ref", "claim_record_ref", "event_ref", "frontier_ref",
        "assessment_ref", "knowledge_ref", "assignment_ref", "delta_ref", "capability_ref",
    ):
        value = getattr(payload, name, None)
        if value:
            return str(value)
    raise ValueError(f"source payload has no stable semantic reference: {type(payload).__name__}")
