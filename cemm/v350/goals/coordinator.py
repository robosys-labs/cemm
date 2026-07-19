"""Atomic Phase-15 decision coordinator."""
from __future__ import annotations

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record, record_fingerprints, record_ref, record_revision
from ..storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordDependency, RecordKind
from .model import GoalCandidateRecord, GoalConflictRecord, GoalDecisionRecord, SemanticObligationRecord


class GoalDecisionCoordinator:
    def __init__(self, store) -> None:
        self.store = store

    def commit(
        self,
        *,
        obligations: tuple[SemanticObligationRecord, ...],
        candidates: tuple[GoalCandidateRecord, ...],
        conflicts: tuple[GoalConflictRecord, ...],
        selected_goal_refs: tuple[str, ...],
        rejected_goal_refs: tuple[str, ...],
        deferred_goal_refs: tuple[str, ...],
        arbitration_policy_ref: str,
        context_ref: str,
        permission_ref: str,
    ):
        candidate_map = {item.goal_ref: item for item in candidates}
        unknown = set((*selected_goal_refs, *rejected_goal_refs, *deferred_goal_refs)) - set(candidate_map)
        if unknown:
            raise ValueError(f"goal decision references unknown candidates: {sorted(unknown)}")
        if any(not candidate_map[ref].authorized for ref in selected_goal_refs):
            raise ValueError("unauthorized candidate cannot be committed as selected")
        with self.store.snapshot() as snapshot:
            operations = []
            obligation_fps = {}
            for obligation in obligations:
                deps = [
                    RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "obligation_source")
                    for pin in obligation.source_pins
                ]
                deps.append(RecordDependency(
                    RecordKind.RESPONSE_POLICY_RULE, obligation.policy_rule_pin.record_ref, obligation.policy_rule_pin.revision,
                    obligation.policy_rule_pin.record_fingerprint, "response_policy_rule",
                ))
                op = self._upsert(RecordKind.SEMANTIC_OBLIGATION, obligation, tuple(deps), "persist target-bearing semantic obligation")
                operations.append(op)
                obligation_fps[obligation.obligation_ref] = record_fingerprints(RecordKind.SEMANTIC_OBLIGATION, obligation)[1]
            candidate_fps = {}
            for candidate in candidates:
                deps = [
                    RecordDependency(RecordKind.SEMANTIC_OBLIGATION, ref, 1, obligation_fps[ref], "goal_obligation")
                    for ref in candidate.obligation_refs
                ]
                deps.extend(
                    RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "goal_policy_or_source")
                    for pin in (*candidate.policy_rule_pins, *candidate.source_pins)
                )
                op = self._upsert(RecordKind.GOAL_CANDIDATE, candidate, tuple(deps), "persist authorized/rejected goal candidate")
                operations.append(op)
                candidate_fps[candidate.goal_ref] = record_fingerprints(RecordKind.GOAL_CANDIDATE, candidate)[1]
            for conflict in conflicts:
                deps = tuple(
                    RecordDependency(RecordKind.GOAL_CANDIDATE, ref, 1, candidate_fps[ref], "goal_conflict_candidate")
                    for ref in conflict.competing_goal_refs
                )
                operations.append(self._upsert(RecordKind.GOAL_CONFLICT, conflict, deps, "persist explicit unresolved goal conflict"))
            candidate_pins = tuple(
                PinnedRecord(RecordKind.GOAL_CANDIDATE, item.goal_ref, 1, candidate_fps[item.goal_ref]) for item in candidates
            )
            decision_ref = "goal-decision:" + semantic_fingerprint(
                "goal-decision-ref", (snapshot.fingerprint, selected_goal_refs, rejected_goal_refs, deferred_goal_refs, arbitration_policy_ref), 24
            )
            decision = GoalDecisionRecord(
                decision_ref=decision_ref, candidate_pins=candidate_pins, selected_goal_refs=selected_goal_refs,
                rejected_goal_refs=rejected_goal_refs, deferred_goal_refs=deferred_goal_refs,
                conflict_refs=tuple(sorted(item.conflict_ref for item in conflicts)), arbitration_policy_ref=arbitration_policy_ref,
                authorization_refs=tuple(sorted({ref for c in candidates for ref in c.authorization_refs})),
                reason_refs=tuple(sorted({reason for c in candidates for reason in (*c.reason_refs, *c.denial_reasons)})),
                snapshot_revision=snapshot.store_revision, snapshot_fingerprint=snapshot.fingerprint,
                boot_fingerprint=snapshot.boot_fingerprint, overlay_fingerprint=snapshot.overlay_fingerprint,
                context_ref=context_ref, permission_ref=permission_ref,
            )
            decision_deps = tuple(
                RecordDependency(RecordKind.GOAL_CANDIDATE, pin.record_ref, pin.revision, pin.record_fingerprint, "goal_decision_candidate")
                for pin in candidate_pins
            )
            operations.append(self._upsert(RecordKind.GOAL_DECISION, decision, decision_deps, "persist exact-snapshot goal arbitration result"))
            patch = GraphPatch(
                patch_ref="graph-patch:phase15:" + semantic_fingerprint("phase15-patch", (decision_ref, snapshot.fingerprint), 24),
                context_ref=context_ref, scope_ref="phase15:goals", source_ref="source:phase15:goal-coordinator",
                permission_ref=permission_ref, operations=tuple(operations), expected_store_revision=snapshot.store_revision,
                validation_requirements=("phase15_target_bearing", "phase15_authorization_before_utility", "phase15_exact_snapshot"),
                metadata={"phase": 15, "decision_ref": decision_ref},
            )
        return self.store.apply_patch(patch), decision

    @staticmethod
    def _upsert(kind: RecordKind, record, deps: tuple[RecordDependency, ...], reason: str) -> PatchOperation:
        return PatchOperation(
            operation_ref="patch-operation:phase15:" + semantic_fingerprint(
                "phase15-op", (kind.value, record_ref(kind, record), record_revision(kind, record), reason), 20
            ),
            operation_kind=PatchOperationKind.UPSERT, record_kind=kind, target_ref=record_ref(kind, record),
            record_revision=record_revision(kind, record), payload=encode_record(kind, record), dependencies=deps, reason=reason,
        )
