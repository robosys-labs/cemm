"""Phase-7 generic response-goal derivation for Stage-10 query artifacts."""
from __future__ import annotations

from dataclasses import replace

from ..learning.model import PinnedRecord
from ..schema.model import UseOperation, semantic_fingerprint
from ..storage.model import RecordKind
from .model import GoalTargetBinding, ResponseTriggerArtifactKind, SemanticObligationRecord
from .policy import GoalAuthorizationGate, build_candidate


class QueryResponseGoalDeriver:
    """Derive answer/clarification goals by artifact family, not predicate name."""

    def __init__(self, store, policy_registry) -> None:
        self.store = store
        self.registry = policy_registry

    def derive(self, query_result, *, frontier_pins: tuple[PinnedRecord, ...] = ()):
        if query_result is None or not query_result.request.response_requested:
            return (), ()
        bound = bool(query_result.bindings) and not query_result.unresolved_query_refs
        if not bound:
            # Missing bindings remain typed learning frontiers. A clarification is
            # communicative content and requires an independently reviewed question
            # UOL/realization authority; the runtime must not invent one from a gap.
            return (), ()
        artifact_kind = ResponseTriggerArtifactKind.BOUND_QUERY
        rules = self.registry.artifact_candidates(artifact_kind)
        if not rules:
            return (), ()

        source_pins = tuple(query_result.source_pins)
        if not source_pins:
            # No durable content lineage means no response authority. A typed
            # frontier is safer than inventing a clarification utterance.
            return (), ()

        targets = query_result.bound_value_refs
        if not targets:
            return (), ()

        obligations = []
        candidates = []
        for rule in rules:
            stored_rule = self.store.get_record(RecordKind.RESPONSE_POLICY_RULE, rule.rule_ref, rule.revision)
            if stored_rule is None or stored_rule.record_fingerprint == "":
                continue
            rule_pin = PinnedRecord(stored_rule.record_kind, stored_rule.record_ref, stored_rule.revision, stored_rule.record_fingerprint)
            target_bindings = tuple(GoalTargetBinding("query_value", ref) for ref in sorted(set(targets)))
            obligation_ref = "obligation:query:" + semantic_fingerprint(
                "query-response-obligation",
                (query_result.result_ref, query_result.fingerprint, artifact_kind.value, rule_pin.key, targets),
                24,
            )
            obligation = SemanticObligationRecord(
                obligation_ref=obligation_ref,
                policy_rule_pin=rule_pin,
                source_pins=source_pins,
                target_refs=tuple(sorted(set(targets))),
                goal_schema_ref=rule.goal_schema_ref,
                goal_schema_revision=rule.goal_schema_revision,
                required_operation=rule.goal_operation,
                priority=rule.priority,
                permission_ref=query_result.permission_ref,
                prerequisite_frontier_refs=tuple(query_result.unresolved_query_refs),
                reason_refs=(rule.rule_ref, artifact_kind.value),
                target_bindings=target_bindings,
                metadata={
                    "context_ref": query_result.context_ref,
                    "query_result_ref": query_result.result_ref,
                    "query_result_fingerprint": query_result.fingerprint,
                    "query_artifact_kind": artifact_kind.value,
                    "qualification_refs": query_result.qualification_refs,
                    "conflict_key_refs": rule.conflict_key_refs,
                },
            )
            candidate = build_candidate(obligation, metadata={
                "query_result_ref": query_result.result_ref,
                "query_result_fingerprint": query_result.fingerprint,
                "query_artifact_kind": artifact_kind.value,
                "qualification_refs": query_result.qualification_refs,
            })
            candidate = GoalAuthorizationGate(self.store).authorize(candidate, rule)
            obligations.append(obligation)
            candidates.append(candidate)
        return tuple(obligations), tuple(candidates)
