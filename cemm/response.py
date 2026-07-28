"""Obligation-bound Response CSIR and deterministic semantic pointerization.

Response construction consumes an exact discourse goal and its source artifact.
It never substitutes a supporting fact for a failed response operation and never
reconstructs query kind from proof shape or variable spelling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping

from cemm.model import Fact, canonical, stable
from cemm.learning_plans import LearningPlan

_SEMANTIC_REF = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class ResponseCSIR:
    response_ref: str
    action: str
    audience_ref: str
    target_ref: str | None = None
    facts: tuple[Fact, ...] = ()
    bindings: tuple[Mapping[str, Any], ...] = ()
    qualifiers: Mapping[str, Any] = field(default_factory=dict)
    evidence_literals: tuple[str, ...] = ()
    reason: str | None = None
    obligation_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.response_ref or not self.action or not self.audience_ref:
            raise ValueError("Response CSIR requires ref, action and audience")
        if self.action != "remain_silent" and not self.obligation_ref:
            raise ValueError(f"response action {self.action} requires discourse obligation")
        query_actions = {
            "answer_bindings",
            "report_multiple_bindings",
            "confirm",
            "deny",
            "report_conflict",
            "report_target_uncertainty",
            "report_operational_condition",
            "describe_semantic_target",
            "explain_evidence_provenance",
        }
        if self.action in query_actions:
            if not self.qualifiers.get("query_ref") or not self.qualifiers.get("query_kind"):
                raise ValueError(f"query response {self.action} requires immutable query metadata")
        if self.action == "report_operational_condition" and not self.target_ref:
            raise ValueError("operational response requires exact target")
        if self.action == "explain_surface_choice":
            required = {"surface_decision_ref", "surface_choice_a", "surface_choice_b"}
            if required - set(self.qualifiers):
                raise ValueError("surface-choice explanation lacks prior decision provenance")
        if self.action == "acknowledge_attributed_claim":
            required = {"subject_ref", "predicate_surface", "claim_kind"}
            if required - set(self.qualifiers):
                raise ValueError("attributed-claim acknowledgment lacks preserved partial meaning")

    def as_dict(self):
        return {
            "response_ref": self.response_ref,
            "action": self.action,
            "audience_ref": self.audience_ref,
            "target_ref": self.target_ref,
            "facts": [
                {
                    "ref": fact.ref,
                    "operator": fact.operator,
                    "args": fact.args,
                    "stance": fact.stance,
                    "confidence": fact.confidence,
                }
                for fact in self.facts
            ],
            "bindings": [dict(item) for item in self.bindings],
            "qualifiers": dict(self.qualifiers),
            "evidence_literals": list(self.evidence_literals),
            "reason": self.reason,
            "obligation_ref": self.obligation_ref,
        }

    def semantic_signature(self) -> str:
        return canonical(
            {
                "action": self.action,
                "audience_ref": self.audience_ref,
                "target_ref": self.target_ref,
                "facts": [
                    {"ref": x.ref, "operator": x.operator, "args": x.args, "stance": x.stance}
                    for x in self.facts
                ],
                "bindings": [dict(x) for x in self.bindings],
                "qualifiers": dict(self.qualifiers),
                "evidence_literals": list(self.evidence_literals),
                "reason": self.reason,
                "obligation_ref": self.obligation_ref,
            }
        )


class ResponseBuilder:
    """Construct exactly one response operation for the selected goal."""

    @staticmethod
    def _frontier_priority(frontier) -> tuple[float, int, str]:
        evidence = tuple(frontier.evidence)
        priority = max((float(item.get("priority", 0.0)) for item in evidence), default=0.0)
        grounded = max((len(item.get("known_bindings", ())) for item in evidence), default=0)
        return priority, grounded, frontier.frontier_ref

    @staticmethod
    def _canonical_bindings(bindings) -> tuple[dict[str, Any], ...]:
        unique: dict[str, dict[str, Any]] = {}
        for binding in bindings:
            values = dict(binding.values if hasattr(binding, "values") else binding)
            unique.setdefault(canonical(values), values)
        return tuple(unique[key] for key in sorted(unique))

    @staticmethod
    def _proof_facts(bindings, facts_by_ref) -> tuple[Fact, ...]:
        refs = {
            ref
            for binding in bindings
            for ref in tuple(getattr(binding, "proof_refs", ()))
        }
        return tuple(facts_by_ref[ref] for ref in sorted(refs) if ref in facts_by_ref)

    @staticmethod
    def _answer_metadata(bindings, frontiers, query_qualifiers):
        qualifiers = dict(query_qualifiers or {})
        literals: list[str] = []
        for frontier in frontiers:
            for item in frontier.evidence:
                if item.get("learning_plan_ref"):
                    qualifiers.setdefault("learning_plan_ref", item["learning_plan_ref"])
                    if item.get("surface"):
                        literals.append(str(item["surface"]))
        if not literals:
            for binding in bindings:
                for value in dict(binding).values():
                    if isinstance(value, dict) and "literal" in value:
                        raw = value["literal"].get("value")
                        if isinstance(raw, str):
                            literals.append(raw)
        object_surface = qualifiers.get("object_surface")
        if isinstance(object_surface, dict) and "literal" in object_surface:
            qualifiers["object_surface"] = object_surface["literal"].get("value")
        return qualifiers, tuple(dict.fromkeys(literals))

    @staticmethod
    def _decision_from_context(dialogue_context, expected_ref):
        decision = dict((dialogue_context or {}).get("last_surface_decision", {}) or {})
        if not decision or decision.get("decision_ref") != expected_ref:
            raise ValueError("surface-choice explanation cannot resolve exact prior decision")
        if not decision.get("response_equivalence", {}).get("equivalent"):
            raise ValueError("prior surface decision lacks semantic-equivalence proof")
        return decision

    def build(
        self,
        *,
        audience_ref,
        goal_decision,
        query_result=None,
        facts_by_ref=None,
        frontiers=(),
        capability_assessments=(),
        operation_result=None,
        epistemic_placement=None,
        operational_snapshot=None,
        discourse_act=None,
        dialogue_context=None,
    ):
        goal = goal_decision.selected if goal_decision else None
        facts_by_ref = facts_by_ref or {}
        action = "remain_silent"
        target_ref = None
        facts: tuple[Fact, ...] = ()
        bindings: tuple[dict[str, Any], ...] = ()
        qualifiers: dict[str, Any] = {}
        literals: tuple[str, ...] = ()
        reason = goal_decision.reason if goal_decision else "no_goal"
        obligation_ref = goal.goal_ref if goal else None
        precomputed_response_ref = None

        if goal and goal.kind == "request_learning_evidence":
            if query_result is None or goal.source_ref != query_result.query_ref:
                raise ValueError("learning request goal is not bound to its exact QueryResult")
            if query_result.bindings or query_result.status not in {"unknown", "partial"}:
                raise ValueError("learning request requires an unanswered exact query")
            payload = dict(goal.payload or {})
            if payload.get("query_ref") != query_result.query_ref:
                raise ValueError("learning request payload lost exact query provenance")
            raw_plan = payload.get("learning_plan")
            if not isinstance(raw_plan, Mapping):
                raise ValueError("learning request requires typed learning plan")
            plan = LearningPlan.from_dict(raw_plan)
            surface = str(payload.get("surface") or "").strip()
            query_kind = str(dict(query_result.qualifiers or {}).get("query_kind") or "")
            if not surface or not query_kind:
                raise ValueError("learning request requires surface and query kind")
            if plan.source_query_ref != query_result.query_ref:
                raise ValueError("learning plan is not bound to executed query")
            if plan.source_query_kind != query_kind:
                raise ValueError("learning plan query kind differs from QueryResult")
            probe_query = payload.get("probe_query")
            if not isinstance(probe_query, Mapping):
                raise ValueError("learning request lacks exact probe query")
            if canonical(plan.source_query) != canonical(dict(probe_query)):
                raise ValueError("learning plan source query differs from goal probe query")
            if plan.surface_literal != surface:
                raise ValueError("learning plan surface differs from probe")
            action = "request_learning_evidence"
            target_ref = plan.target_ref
            literals = (surface,)
            qualifiers = {
                "query_ref": query_result.query_ref,
                "query_kind": query_kind,
                "learning_query": payload.get("probe_query"),
                "expected_semantic_kinds": list(plan.expected_target_kinds),
                "known_bindings": dict(plan.known_bindings),
                "expected_answer_shape": {
                    "answer_contract_ref": plan.answer_contract_ref,
                    "surface_cardinality": "one",
                },
                "original_candidate_ref": plan.original_candidate_ref,
                "unresolved_span_ref": plan.unresolved_span_ref,
            }
            precomputed_response_ref = stable("response-csir", (
                action, audience_ref, target_ref, [], (), qualifiers,
                literals, "unanswered_learning_query", obligation_ref,
            ))
            plan = plan.bind_response(
                response_ref=precomputed_response_ref,
                goal_ref=obligation_ref,
            )
            qualifiers["learning_plan"] = plan.as_dict()
            qualifiers["learning_plan_ref"] = plan.plan_ref
            qualifiers["learning_contract_ref"] = plan.contract_ref
            reason = "unanswered_learning_query"

        elif goal and goal.kind == "answer_query":
            if query_result is None or goal.source_ref != query_result.query_ref:
                raise ValueError("answer goal is not bound to its exact QueryResult")
            query_qualifiers = dict(query_result.qualifiers or {})
            if not query_qualifiers.get("query_kind"):
                raise ValueError("QueryResult lost immutable query_kind qualifier")
            common = {
                **query_qualifiers,
                "query_status": query_result.status,
                "coverage": query_result.coverage,
                "unresolved_variables": list(query_result.unresolved_variables),
                "query_ref": query_result.query_ref,
            }
            if query_qualifiers.get("query_kind") == "capability_inventory_query":
                target_ref = query_qualifiers.get("target_ref")
            if query_qualifiers.get("query_kind") == "semantic_description":
                result = dict(query_qualifiers.get("description_result", {}) or {})
                action = "describe_semantic_target"
                target_ref = result.get("target_ref") or query_qualifiers.get("target_ref")
                facts = tuple(
                    facts_by_ref[ref]
                    for ref in sorted({item.get("ref") for item in result.get("facts", ()) if item.get("ref")})
                    if ref in facts_by_ref
                )
                facet_names = [key for key, refs in dict(result.get("fact_facets", {})).items() if refs]
                qualifiers = {
                    **common,
                    "description_result_ref": result.get("result_ref"),
                    "description_completeness": result.get("completeness"),
                    "target_kind": result.get("target_kind"),
                    "preferred_surface": result.get("preferred_surface"),
                    "description_summary": ", ".join(facet_names),
                    "description_fact_refs": [item.get("ref") for item in result.get("facts", ()) if item.get("ref")],
                    "description_source_refs": list(result.get("source_refs", ())),
                    "missing_facets": list(result.get("missing_facets", ())),
                }
                reason = "semantic_target_description"
            elif query_qualifiers.get("query_kind") == "epistemic_provenance":
                proof = dict(query_qualifiers.get("proof_bundle", {}) or {})
                action = "explain_evidence_provenance"
                target_ref = None
                sources = list(proof.get("source_refs", ()))
                authority = list(dict(proof.get("provenance", {})).get("authority_statuses", ()))
                if audience_ref in sources:
                    basis = "user_report"
                elif proof.get("operational_snapshot_refs"):
                    basis = "operational_observation"
                elif proof.get("inference_receipt_refs"):
                    basis = "inference"
                elif "reviewed" in authority or "promoted" in authority or "seed" in sources:
                    basis = "reviewed_authority"
                elif proof.get("fact_refs") or proof.get("claim_refs"):
                    basis = "stored_evidence"
                else:
                    basis = "unsupported"
                qualifiers = {
                    **common,
                    "proof_ref": proof.get("proof_ref"),
                    "proof_basis": basis,
                    "proof_completeness": proof.get("completeness"),
                    "proof_fact_refs": list(proof.get("fact_refs", ())),
                    "proof_claim_refs": list(proof.get("claim_refs", ())),
                    "proof_source_refs": sources,
                    "proof_inference_refs": list(proof.get("inference_receipt_refs", ())),
                    "proof_snapshot_refs": list(proof.get("operational_snapshot_refs", ())),
                }
                reason = "epistemic_provenance_explanation"
            elif query_qualifiers.get("query_kind") == "operational_condition_query":
                if operational_snapshot is None:
                    raise ValueError("operational query requires current OperationalSnapshot")
                assessment = operational_snapshot.assess()
                action = "report_operational_condition"
                target_ref = operational_snapshot.self_ref
                qualifiers = {
                    **common,
                    "assessment_status": assessment.status,
                    "assessment_score": assessment.score,
                    "snapshot_ref": assessment.snapshot_ref,
                    "assessment_ref": assessment.assessment_ref,
                    "critical_blockers": list(assessment.critical_blockers),
                    "degraded_resources": list(assessment.degraded_resources),
                    "unknown_resources": list(assessment.unknown_resources),
                }
            else:
                bindings = self._canonical_bindings(query_result.bindings)
                facts = self._proof_facts(query_result.bindings, facts_by_ref)
                boolean_answer = query_qualifiers.get("answer_mode") == "boolean"
                if query_result.status == "conflict":
                    action = "report_conflict"
                elif boolean_answer and query_result.status in {"answered", "supported"}:
                    action = "confirm"
                elif boolean_answer and query_result.status == "contradicted":
                    action = "deny"
                elif bindings and query_result.status in {"answered", "partial"}:
                    requested_cardinality = query_qualifiers.get("answer_cardinality")
                    action = (
                        "report_multiple_bindings"
                        if len(bindings) > 1 and requested_cardinality != "many"
                        else "answer_bindings"
                    )
                elif query_result.status == "supported":
                    action = "confirm"
                elif query_result.status == "contradicted":
                    action = "deny"
                else:
                    action = "report_target_uncertainty"
                metadata, literals = self._answer_metadata(bindings, frontiers, query_qualifiers)
                qualifiers = {**common, **metadata, "binding_count": len(bindings)}

        elif goal and goal.kind == "clarify":
            if not frontiers:
                raise ValueError("clarification goal requires a frontier")
            frontier = max(frontiers, key=self._frontier_priority)
            if frontier.frontier_ref != goal.source_ref:
                frontier = next((x for x in frontiers if x.frontier_ref == goal.source_ref), None)
                if frontier is None:
                    raise ValueError("clarification goal is not bound to an exact frontier")
            evidence = max(
                frontier.evidence,
                key=lambda item: (
                    float(item.get("priority", 0.0)),
                    len(str(item.get("surface", ""))),
                    canonical(item),
                ),
                default={},
            )
            raw_learning_plan = evidence.get("learning_plan")
            surface = evidence.get("surface") or evidence.get("normalized")
            if isinstance(raw_learning_plan, Mapping):
                action = "request_learning_evidence"
            elif evidence.get("composition_gap"):
                action = "report_structural_composition_gap"
            elif surface or frontier.target_ref:
                action = "request_targeted_clarification"
            else:
                action = "request_generic_clarification"
            target_ref = frontier.target_ref
            literals = (str(surface),) if surface else ()
            qualifiers = {
                "frontier_ref": frontier.frontier_ref,
                "composition_gap": dict(evidence.get("composition_gap", {}) or {}),
                "gap_kind": dict(evidence.get("composition_gap", {}) or {}).get("gap_kind"),
                "frontier_kind": frontier.kind,
                "expected_semantic_kinds": list(evidence.get("semantic_kind_candidates", ())),
                "original_candidate_ref": evidence.get("candidate_ref"),
                "unresolved_span_ref": evidence.get("span_ref"),
            }
            if isinstance(raw_learning_plan, Mapping):
                plan = LearningPlan.from_dict(raw_learning_plan)
                qualifiers.update(
                    {
                        "learning_plan": plan.as_dict(),
                        "learning_plan_ref": plan.plan_ref,
                        "learning_contract_ref": plan.contract_ref,
                        "query_ref": plan.source_query_ref,
                        "query_kind": plan.source_query_kind,
                        "learning_query": evidence.get("probe_query"),
                        "known_bindings": dict(plan.known_bindings),
                        "expected_answer_shape": {
                            "answer_contract_ref": plan.answer_contract_ref,
                            "surface_cardinality": "one",
                        },
                    }
                )
            reason = frontier.kind

        elif goal and goal.kind == "explain_surface_choice":
            decision_ref = goal.payload.get("surface_decision_ref")
            decision = self._decision_from_context(dialogue_context, decision_ref)
            action = "explain_surface_choice"
            target_ref = decision.get("reference_plan", {}).get("speaker_ref")
            qualifiers = {
                "surface_decision_ref": decision_ref,
                "prior_response_ref": decision.get("response_ref"),
                "prior_response_action": decision.get("response_action"),
                "prior_surface": decision.get("chosen_surface"),
                "prior_reference_plan": decision.get("reference_plan"),
                "surface_choice_a": goal.payload.get("surface_choice_a"),
                "surface_choice_b": goal.payload.get("surface_choice_b"),
                "explanation_kind": "speaker_perspective_reference_choice",
            }

        elif goal and goal.kind == "acknowledge_attributed_claim":
            action = "acknowledge_attributed_claim"
            target_ref = goal.payload.get("subject_ref")
            predicate_surface = goal.payload.get("predicate_surface")
            if isinstance(predicate_surface, dict) and "literal" in predicate_surface:
                predicate_surface = predicate_surface["literal"].get("value")
            qualifiers = {
                "claim_kind": "attributed_open_predication",
                "subject_ref": goal.payload.get("subject_ref"),
                "predicate_surface": predicate_surface,
                "epistemic_stance": goal.payload.get("epistemic_stance"),
                "act_ref": goal.payload.get("act_ref"),
            }

        elif goal and goal.kind == "report_self_capability":
            preferred = set(goal.payload.get("preferred_capability_refs", ()))
            candidates = [
                item for item in capability_assessments
                if not preferred or item.capability_ref in preferred
            ]
            if not candidates:
                raise ValueError("capability report goal has no matching assessment")
            if preferred and {x.capability_ref for x in candidates} != preferred:
                raise ValueError("capability report lacks requested assessment")
            candidates.sort(key=lambda x: x.capability_ref)
            best = candidates[0]
            action = "report_capability"
            target_ref = best.capability_ref
            qualifiers = best.as_dict()

        elif goal and goal.kind == "greet":
            action = "greet"
        elif goal and goal.kind == "handle_directive":
            action = "report_operation_result" if operation_result is not None and operation_result.status == "succeeded" else "decline_directive"
            qualifiers = operation_result.as_dict() if operation_result else {"reason": "no_authorized_operation"}
        elif goal and goal.kind in {"acknowledge_claim", "acknowledge"}:
            action = "acknowledge_claim"
            if epistemic_placement is not None:
                qualifiers = epistemic_placement.as_dict()

        payload = (
            action,
            audience_ref,
            target_ref,
            [item.ref for item in facts],
            bindings,
            qualifiers,
            literals,
            reason,
            obligation_ref,
        )
        return ResponseCSIR(
            precomputed_response_ref or stable("response-csir", payload),
            action,
            audience_ref,
            target_ref,
            facts,
            bindings,
            qualifiers,
            literals,
            reason,
            obligation_ref,
        )


class _PointerTable:
    def __init__(self):
        self.atom_by_value: dict[str, str] = {}
        self.literal_by_key: dict[str, str] = {}
        self.number_by_key: dict[str, str] = {}
        self.info: dict[str, dict[str, Any]] = {}

    def atom(self, value: str, context: str | None = None) -> str:
        if value not in self.atom_by_value:
            placeholder = f"@A{len(self.atom_by_value)}"
            self.atom_by_value[value] = placeholder
            self.info[placeholder] = {"kind": "atom", "value": value, "context": context}
        elif context and not self.info[self.atom_by_value[value]].get("context"):
            self.info[self.atom_by_value[value]]["context"] = context
        return self.atom_by_value[value]

    def literal(self, value: Mapping[str, Any], context: str | None = None) -> str:
        literal = dict(value["literal"])
        typ = str(literal.get("type", "text"))
        raw = literal.get("value")
        table = self.number_by_key if typ in {"int", "float", "number"} else self.literal_by_key
        prefix = "@N" if table is self.number_by_key else "@E"
        key = canonical((context, typ, raw))
        if key not in table:
            placeholder = f"{prefix}{len(table)}"
            table[key] = placeholder
            self.info[placeholder] = {
                "kind": "number" if prefix == "@N" else "evidence",
                "value": raw,
                "literal_type": typ,
                "context": context,
            }
        return table[key]

    def encode(self, value: Any, context: str | None = None) -> str:
        if isinstance(value, str) and _SEMANTIC_REF.fullmatch(value) and not value.startswith("?"):
            return self.atom(value, context)
        if isinstance(value, dict) and "literal" in value:
            return self.literal(value, context)
        return canonical(value) if isinstance(value, (dict, list)) else str(value)


def pointerize_fact(fact: Fact):
    table = _PointerTable()
    parts = ["FACT", fact.stance, fact.operator]
    for role, value in sorted(fact.args.items()):
        parts += [role, table.encode(value, role)]
    return " ".join(parts), table.info


def pointerize_plan(plan):
    table = _PointerTable()
    parts = ["PLAN", plan["goal"]]
    if plan.get("value") is not None:
        parts += ["VALUE", table.encode(plan["value"], "response:value")]
    for fact in plan.get("facts", ()):
        parts += ["|", "FACT", fact.stance, fact.operator]
        for role, value in sorted(fact.args.items()):
            parts += [role, table.encode(value, role)]
    return " ".join(parts), table.info


def pointerize_response(response: ResponseCSIR):
    table = _PointerTable()
    parts = ["RESPONSE", response.action]
    if response.target_ref:
        parts += ["TARGET", table.encode(response.target_ref, "response:target")]
    for key, label in (
        ("query_kind", "QUERY_KIND"),
        ("property_ref", "PROPERTY"),
        ("relation_ref", "RELATION"),
        ("subject_ref", "SUBJECT"),
        ("surface_decision_ref", "SURFACE_DECISION"),
    ):
        value = response.qualifiers.get(key)
        if value is not None:
            parts += [label, table.encode(value, f"response:{key}")]
    learning_plan_ref = response.qualifiers.get("learning_plan_ref")
    if learning_plan_ref:
        parts += [
            "LEARNING_PLAN",
            table.literal(
                {"literal": {"type": "text", "value": str(learning_plan_ref)}},
                "response:learning_plan_ref",
            ),
        ]
    for key, label in (
        ("object_surface", "OBJECT_SURFACE"),
        ("predicate_surface", "PREDICATE_SURFACE"),
        ("surface_choice_a", "CHOICE_A"),
        ("surface_choice_b", "CHOICE_B"),
        ("prior_surface", "PRIOR_SURFACE"),
    ):
        value = response.qualifiers.get(key)
        if isinstance(value, dict) and "literal" in value:
            value = value["literal"].get("value")
        if value is not None:
            parts += [label, table.literal({"literal": {"type": "text", "value": str(value)}}, f"response:{key}")]
    for binding in response.bindings:
        parts.append("BINDING")
        for variable, value in sorted(binding.items()):
            parts += [variable, table.encode(value, f"binding:{variable}")]
    if response.action not in {"answer_bindings", "report_multiple_bindings"}:
        for fact in response.facts:
            parts.append("|")
            semantic, mapping = pointerize_fact(fact)
            for placeholder in sorted(mapping, key=lambda item: (-len(item), item)):
                info = mapping[placeholder]
                replacement = table.encode(info["value"], info.get("context"))
                semantic = re.sub(
                    rf"(?<![A-Za-z0-9_]){re.escape(placeholder)}(?!\d)",
                    lambda _match, value=replacement: value,
                    semantic,
                )
            parts.append(semantic)
    for literal in response.evidence_literals:
        parts += [
            "EVIDENCE",
            table.literal({"literal": {"type": "text", "value": literal}}, "response:evidence"),
        ]
    capability_score = response.qualifiers.get("score")
    if response.action == "report_capability" and capability_score is not None:
        value = round(float(capability_score) * 100)
        parts += [
            "SCORE",
            table.literal({"literal": {"type": "int", "value": value}}, "response:score"),
        ]
    return " ".join(parts), table.info
