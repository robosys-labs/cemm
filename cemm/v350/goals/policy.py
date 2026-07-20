"""Structural Phase-15 obligation derivation, authorization and arbitration."""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ..learning.model import FrontierResolutionStatus, LearningFrontierRecord, PinnedRecord
from ..schema.model import ActionSchema, UseOperation, schema_authorizes_use, semantic_fingerprint
from ..significance.model import SignificanceAssessmentRecord
from ..storage.model import KnowledgeStatus, RecordKind
from ..uol.model import CapabilityStatus
from ..uol.model import ClaimOccurrence, EventOccurrence, FillerRef, SemanticApplication
from .model import (
    GoalCandidateRecord, GoalConflictRecord, ResponsePolicyRuleRecord, SemanticObligationRecord,
    GoalTargetBinding, TargetSelectorMode,
)


class ResponsePolicyRegistry:
    def __init__(self, rules: Iterable[ResponsePolicyRuleRecord]) -> None:
        by_ref = {}
        for rule in rules:
            if rule.executable:
                by_ref.setdefault(rule.rule_ref, []).append(rule)
        effective = []
        for rule_ref in sorted(by_ref):
            revisions = by_ref[rule_ref]
            superseded = {r.supersedes_revision for r in revisions if r.supersedes_revision is not None}
            effective.extend(r for r in revisions if r.revision not in superseded)
        self._rules = tuple(sorted(effective, key=lambda r: (r.rule_ref, r.revision)))

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

    def derive(self, source_pin: PinnedRecord, rule: ResponsePolicyRuleRecord, rule_pin: PinnedRecord, *, supporting_pins: tuple[PinnedRecord, ...] = ()) -> SemanticObligationRecord | None:
        stored = self.store.get_record(source_pin.record_kind, source_pin.record_ref, source_pin.revision)
        if stored is None or stored.record_fingerprint != source_pin.record_fingerprint:
            raise ValueError("stale source pin during obligation derivation")
        if not rule.executable:
            raise ValueError("candidate/provisional response policy cannot execute")
        for pin in supporting_pins:
            support = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if support is None or support.record_fingerprint != pin.record_fingerprint:
                raise ValueError("stale supporting pin during obligation derivation")
        target_bindings = self._target_bindings(stored.payload, rule, supporting_pins)
        targets = tuple(sorted({item.target_ref for item in target_bindings}))
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
            obligation_ref=obligation_ref, policy_rule_pin=rule_pin, source_pins=(source_pin, *supporting_pins), target_refs=targets,
            goal_schema_ref=rule.goal_schema_ref, goal_schema_revision=rule.goal_schema_revision, required_operation=rule.goal_operation,
            priority=rule.priority, permission_ref=stored.permission_ref or getattr(stored.payload, "permission_ref", "conversation"),
            prerequisite_frontier_refs=frontier_refs, reason_refs=(rule.rule_ref,),
            metadata={"context_ref": stored.context_ref or getattr(stored.payload, "context_ref", "actual"), "conflict_key_refs": rule.conflict_key_refs},
            target_bindings=target_bindings,
        )

    def _targets(self, source: object, rule: ResponsePolicyRuleRecord, supporting_pins: tuple[PinnedRecord, ...] = ()) -> tuple[str, ...]:
        return tuple(sorted({item.target_ref for item in self._target_bindings(source, rule, supporting_pins)}))

    def _target_bindings(self, source: object, rule: ResponsePolicyRuleRecord, supporting_pins: tuple[PinnedRecord, ...] = ()) -> tuple[GoalTargetBinding, ...]:
        result: list[str] = []
        bindings: list[GoalTargetBinding] = []
        for selector in rule.target_selectors:
            role_ref = selector.port_ref or selector.mode.value
            if selector.mode == TargetSelectorMode.SOURCE:
                result.append(_primary_ref(source)); bindings.append(GoalTargetBinding(role_ref, result[-1]))
            elif selector.mode == TargetSelectorMode.SOURCE_PROPOSITION:
                value = getattr(source, "proposition_ref", None)
                if value:
                    result.append(str(value)); bindings.append(GoalTargetBinding(role_ref, str(value)))
            elif selector.mode == TargetSelectorMode.FRONTIER_TARGET and isinstance(source, LearningFrontierRecord):
                if source.target_ref:
                    result.append(source.target_ref); bindings.append(GoalTargetBinding(role_ref, source.target_ref))
            elif selector.mode == TargetSelectorMode.SIGNIFICANCE_STAKEHOLDER and isinstance(source, SignificanceAssessmentRecord):
                result.append(source.impact.stakeholder_ref); bindings.append(GoalTargetBinding(role_ref, source.impact.stakeholder_ref))
            elif selector.mode == TargetSelectorMode.SIGNIFICANCE_AFFECTED and isinstance(source, SignificanceAssessmentRecord):
                result.append(source.impact.affected_ref); bindings.append(GoalTargetBinding(role_ref, source.impact.affected_ref))
            elif selector.mode == TargetSelectorMode.APPLICATION_PORT:
                app = _application(source, self.store, supporting_pins)
                if app is not None:
                    for binding in app.bindings:
                        if binding.port_ref == selector.port_ref:
                            for filler in binding.fillers:
                                if isinstance(filler, FillerRef):
                                    result.append(filler.ref); bindings.append(GoalTargetBinding(role_ref, filler.ref))
            elif selector.mode == TargetSelectorMode.FIXED and selector.fixed_ref:
                result.append(selector.fixed_ref); bindings.append(GoalTargetBinding(role_ref, selector.fixed_ref))
        unique = {
            (item.role_ref, item.target_ref): item
            for item in bindings
            if item.target_ref
        }
        return tuple(unique[key] for key in sorted(unique))


class GoalAuthorizationGate:
    def __init__(self, store) -> None:
        self.store = store

    def authorize(self, candidate: GoalCandidateRecord, rule: ResponsePolicyRuleRecord) -> GoalCandidateRecord:
        denial: list[str] = []
        auth_refs: list[str] = []
        auth_pins: list[PinnedRecord] = []
        source_contexts: set[str] = set()
        if candidate.operation == UseOperation.EXECUTE and not rule.require_capability:
            denial.append("execute_policy_missing_capability_gate")
        for pin in candidate.source_pins:
            stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if stored is None or stored.record_fingerprint != pin.record_fingerprint:
                denial.append("stale_source")
                continue
            source_contexts.add(str(stored.context_ref or getattr(stored.payload, "context_ref", "actual")))
            if rule.require_permission:
                permission = stored.permission_ref or getattr(stored.payload, "permission_ref", "conversation")
                if permission not in {"public", candidate.permission_ref}: denial.append("permission_scope_mismatch")
        if len(source_contexts) > 1: denial.append("mixed_source_contexts")
        context_ref = next(iter(source_contexts), str(candidate.metadata.get("context_ref", "actual")))
        if rule.block_on_open_frontier and candidate.prerequisite_frontier_refs: denial.append("open_prerequisite_frontier")
        if rule.require_epistemic_support:
            for target in candidate.target_refs:
                matches = [item for item in self.store.records(RecordKind.KNOWLEDGE)
                    if getattr(item.payload, "proposition_ref", None) == target
                    and getattr(item.payload, "status", None) == KnowledgeStatus.SUPPORTED
                    and getattr(item.payload, "context_ref", None) in {"global", context_ref}
                    and item.permission_ref in {None, "public", candidate.permission_ref}]
                if len(matches) != 1:
                    denial.append(f"epistemic_support_cardinality:{target}:{len(matches)}")
                else:
                    item = matches[0]; auth_refs.append(item.record_ref); auth_pins.append(PinnedRecord(item.record_kind,item.record_ref,item.revision,item.record_fingerprint))
        if rule.require_capability:
            for target in candidate.target_refs:
                stored = self.store.get_record(RecordKind.SEMANTIC_APPLICATION, target)
                if stored is None or not isinstance(stored.payload, SemanticApplication):
                    denial.append(f"missing_action_application:{target}"); continue
                target_pin = PinnedRecord(stored.record_kind, stored.record_ref, stored.revision, stored.record_fingerprint)
                auth_pins.append(target_pin)
                app = stored.payload
                schema_stored = self.store.get_record(RecordKind.SCHEMA, app.schema_ref, app.schema_revision)
                if schema_stored is None or not isinstance(schema_stored.payload, ActionSchema) or schema_stored.payload.controlling_port_ref is None:
                    denial.append(f"action_missing_controlling_port:{target}"); continue
                if not schema_authorizes_use(schema_stored.payload, UseOperation.EXECUTE):
                    denial.append(f"action_not_execute_authorized:{target}"); continue
                try:
                    effective_action = self.store.repositories.schemas.for_use(app.schema_ref, UseOperation.EXECUTE)
                except KeyError:
                    denial.append(f"action_not_effective_execute_authority:{target}"); continue
                if effective_action.revision != app.schema_revision:
                    denial.append(f"stale_action_schema_revision:{target}"); continue
                auth_pins.append(PinnedRecord(schema_stored.record_kind, schema_stored.record_ref, schema_stored.revision, schema_stored.record_fingerprint))
                control = app.binding(schema_stored.payload.controlling_port_ref)
                holders = tuple(f.ref for f in (() if control is None else control.fillers) if isinstance(f,FillerRef))
                if len(holders) != 1:
                    denial.append(f"ambiguous_controlling_holder:{target}"); continue
                capabilities = [item for item in self.store.records(RecordKind.CAPABILITY_INSTANCE)
                    if getattr(item.payload,"action_schema_ref",None)==app.schema_ref
                    and getattr(item.payload,"action_schema_revision",None)==app.schema_revision
                    and getattr(item.payload,"status",None)==CapabilityStatus.AVAILABLE
                    and getattr(item.payload,"holder_ref",None)==holders[0]
                    and getattr(item.payload,"context_ref",None) in {"global",app.context_ref}]
                if len(capabilities) != 1:
                    denial.append(f"live_capability_cardinality:{target}:{len(capabilities)}")
                else:
                    item=capabilities[0];auth_refs.append(item.record_ref);auth_pins.append(PinnedRecord(item.record_kind,item.record_ref,item.revision,item.record_fingerprint))
        denial = sorted(set(denial)); auth_pins=sorted({p.key+(p.record_fingerprint,):p for p in auth_pins}.values(),key=lambda p:p.key)
        new_ref = "goal:" + semantic_fingerprint("authorized-goal-candidate", (candidate.goal_ref, tuple(p.key+(p.record_fingerprint,) for p in auth_pins), tuple(denial), context_ref), 24)
        return replace(candidate, goal_ref=new_ref, authorized=not denial, authorization_refs=tuple(sorted(set(filter(None, (*candidate.authorization_refs,*auth_refs))))),
                       authorization_pins=tuple(auth_pins), denial_reasons=tuple(denial), metadata={**dict(candidate.metadata),"context_ref":context_ref,"authorization_scope":"goal_eligibility_only"})


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
        conflict_pairs = {frozenset(c.competing_goal_refs) for c in conflicts}
        eligible = sorted((item for item in items if item.authorized), key=lambda item: (-item.priority, -item.utility_score, item.goal_ref))
        selected: list[str] = []; rejected_conflict: set[str] = set()
        for item in eligible:
            if any(frozenset((item.goal_ref, chosen)) in conflict_pairs for chosen in selected):
                rejected_conflict.add(item.goal_ref); continue
            # Exact duplicate semantic goals are deferred rather than emitted twice.
            duplicate = next((x for x in eligible if x.goal_ref in selected and x.operation==item.operation and x.target_refs==item.target_refs and x.goal_schema_ref==item.goal_schema_ref), None)
            if duplicate is not None: continue
            selected.append(item.goal_ref)
        rejected = tuple(sorted(unauthorized | rejected_conflict))
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
        utility_score=utility_score, metadata={**dict(obligation.metadata), **dict(metadata or {})},
        target_bindings=obligation.target_bindings,
    )


def _schema_pin(payload: object):
    if isinstance(payload, SemanticApplication):
        return payload.schema_ref, payload.schema_revision
    if isinstance(payload, EventOccurrence):
        return payload.event_schema_ref, payload.event_schema_revision
    return None


def _application(payload: object, store, supporting_pins: tuple[PinnedRecord, ...] = ()):
    if isinstance(payload, SemanticApplication):
        return payload
    if isinstance(payload, EventOccurrence):
        matches = [pin for pin in supporting_pins if pin.record_kind == RecordKind.SEMANTIC_APPLICATION and pin.record_ref == payload.participant_application_ref]
        if len(matches) != 1:
            raise ValueError("event APPLICATION_PORT target selection requires one exact participant application support pin")
        pin = matches[0]
        stored = store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        if stored is None or stored.record_fingerprint != pin.record_fingerprint or not isinstance(stored.payload, SemanticApplication):
            raise ValueError("stale event participant application support pin")
        return stored.payload
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
