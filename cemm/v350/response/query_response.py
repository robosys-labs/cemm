"""Generic Phase-7 Response UOL planning for Stage-10 query artifacts."""
from __future__ import annotations

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.model import RecordKind
from .model import ResponseTransformKind, ResponseTransformationProof, ResponseUOLRecord


class BoundQueryResponsePlanner:
    def __init__(self, store, rules) -> None:
        self.store = store
        self.rules = tuple(r for r in rules if r.executable)

    def plan(self, decision_pin: PinnedRecord, query_result, *, audience_refs, perspective_ref):
        decision_stored = self._exact(decision_pin)
        decision = decision_stored.payload
        selected = []
        for pin in decision.candidate_pins:
            if pin.record_ref not in decision.selected_goal_refs:
                continue
            stored = self._exact(pin)
            selected.append((pin, stored.payload))
        matching = [
            item for item in selected
            if item[1].metadata.get("query_result_ref") == query_result.result_ref
            and item[1].metadata.get("query_result_fingerprint") == query_result.fingerprint
        ]
        if not matching:
            raise ValueError("selected goal does not pin current query result")
        if len(matching) != 1:
            raise ValueError("query response goal must be singular")
        goal_pin, goal = matching[0]
        artifact_kind = str(goal.metadata.get("query_artifact_kind", ""))
        if artifact_kind != "bound_query":
            raise ValueError(
                "partial query requires independently reviewed clarification UOL"
            )
        transform_kind = ResponseTransformKind.BOUND_QUERY_GRAPH
        rules = [
            r for r in self.rules
            if r.transform_kind == transform_kind
            and (goal.goal_schema_ref, goal.goal_schema_revision) in r.goal_schema_pins
        ]
        rules.sort(key=lambda r: (-r.priority, r.rule_ref, r.revision))
        if len(rules) != 1:
            raise ValueError(f"query response transform authority cardinality:{len(rules)}")
        rule = rules[0]
        rule_stored = self.store.get_record(RecordKind.RESPONSE_TRANSFORM_RULE, rule.rule_ref, rule.revision)
        if rule_stored is None:
            raise ValueError("missing exact query response transform rule")
        rule_pin = PinnedRecord(rule_stored.record_kind, rule_stored.record_ref, rule_stored.revision, rule_stored.record_fingerprint)

        input_pins = tuple(query_result.source_pins) or tuple(goal.source_pins)
        if not input_pins:
            raise ValueError("query response requires durable source lineage")
        graph = query_result.answer_graph
        mandatory = set(rule.mandatory_qualification_refs)
        if not mandatory.issubset(set(query_result.qualification_refs)):
            raise ValueError("query response missing mandatory qualification")

        proof_ref = "response-proof:query:" + semantic_fingerprint(
            "query-response-proof",
            (goal_pin.key, rule_pin.key, tuple(p.key for p in input_pins), graph.record_fingerprint, query_result.fingerprint),
            24,
        )
        proof = ResponseTransformationProof(
            proof_ref=proof_ref,
            goal_candidate_pin=goal_pin,
            rule_pin=rule_pin,
            input_pins=input_pins,
            output_refs=tuple(root.ref for root in graph.root_refs) or tuple(query_result.unresolved_query_refs),
            authorization_pins=tuple(goal.authorization_pins),
            reason_refs=(transform_kind.value, query_result.result_ref),
        )
        unresolved_frontiers = ()
        frontiers = ()
        with self.store.snapshot() as snapshot:
            response = ResponseUOLRecord(
                response_ref="response-uol:query:" + semantic_fingerprint(
                    "query-response-uol",
                    (decision_pin.key, goal_pin.key, rule_pin.key, query_result.fingerprint, graph.record_fingerprint),
                    24,
                ),
                goal_decision_pin=decision_pin,
                selected_goal_pins=(goal_pin,),
                source_pins=input_pins,
                transformation_proof_refs=(proof_ref,),
                omission_refs=(),
                graph=graph,
                unresolved_frontier_refs=unresolved_frontiers,
                audience_refs=tuple(audience_refs),
                perspective_ref=perspective_ref,
                context_ref=query_result.context_ref,
                permission_ref=query_result.permission_ref,
                snapshot_revision=snapshot.store_revision,
                snapshot_fingerprint=snapshot.fingerprint,
                metadata={
                    "query_result_ref": query_result.result_ref,
                    "query_result_fingerprint": query_result.fingerprint,
                    "query_artifact_kind": artifact_kind,
                    "qualification_refs": query_result.qualification_refs,
                },
            )
        return response, (proof,), frontiers

    def _exact(self, pin):
        stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        if stored is None or stored.record_fingerprint != pin.record_fingerprint:
            raise ValueError(f"stale exact pin:{pin.key}")
        return stored
