"""Target-aware Response CSIR and deterministic semantic pointerization."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from cemm.model import Fact, canonical, stable


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


class ResponseBuilder:
    """Construct response meaning from exact results and scoped blockers."""

    @staticmethod
    def _frontier_priority(frontier) -> tuple[float, int, str]:
        evidence = tuple(frontier.evidence)
        priority = max((float(item.get("priority", 0.0)) for item in evidence), default=0.0)
        grounded = max((len(item.get("known_bindings", ())) for item in evidence), default=0)
        return priority, grounded, frontier.frontier_ref

    @staticmethod
    def _designation_answer_metadata(facts, bindings, frontiers):
        qualifiers: dict[str, Any] = {}
        literals: list[str] = []
        for frontier in frontiers:
            for item in frontier.evidence:
                if item.get("learning_operation"):
                    qualifiers["query_kind"] = (
                        (item.get("probe_query") or {}).get("qualifiers", {}).get("query_kind")
                        or "designation_learning"
                    )
                    qualifiers["learning_operation"] = item["learning_operation"]
                    if item.get("surface"):
                        literals.append(str(item["surface"]))
        designation = next((fact for fact in facts if fact.operator == "op:designation"), None)
        if designation:
            label_type = designation.args.get("role:label_type")
            if isinstance(label_type, str):
                qualifiers.setdefault("property_ref", label_type)
            qualifiers.setdefault("query_kind", "designation_property")
        if not literals:
            for binding in bindings:
                for value in binding.values():
                    if isinstance(value, dict) and "literal" in value:
                        raw = value["literal"].get("value")
                        if isinstance(raw, str):
                            literals.append(raw)
        return qualifiers, tuple(dict.fromkeys(literals))

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
    ):
        goal = goal_decision.selected if goal_decision else None
        facts_by_ref = facts_by_ref or {}
        action = "remain_silent"
        target_ref = None
        facts: list[Fact] = []
        bindings: list[dict[str, Any]] = []
        qualifiers: dict[str, Any] = {}
        literals: tuple[str, ...] = ()
        reason = goal_decision.reason if goal_decision else "no_goal"
        obligation_ref = goal.goal_ref if goal else None

        if goal and goal.kind == "answer_query" and query_result is not None:
            bindings = [dict(item.values) for item in query_result.bindings]
            proof_refs = {ref for item in query_result.bindings for ref in item.proof_refs}
            facts = [facts_by_ref[ref] for ref in sorted(proof_refs) if ref in facts_by_ref]
            action = (
                "report_conflict"
                if query_result.status == "conflict"
                else "answer_bindings"
                if query_result.bindings
                else "confirm"
                if query_result.status == "supported"
                else "deny"
                if query_result.status == "contradicted"
                else "report_target_uncertainty"
            )
            qualifiers = {
                "query_status": query_result.status,
                "coverage": query_result.coverage,
                "unresolved_variables": list(query_result.unresolved_variables),
            }
            metadata, literals = self._designation_answer_metadata(
                facts, bindings, frontiers
            )
            qualifiers.update(metadata)
        elif goal and goal.kind == "clarify" and frontiers:
            frontier = max(frontiers, key=self._frontier_priority)
            evidence = max(
                frontier.evidence,
                key=lambda item: (
                    float(item.get("priority", 0.0)),
                    len(str(item.get("surface", ""))),
                ),
                default={},
            )
            learning_operation = evidence.get("learning_operation")
            action = (
                "request_learning_evidence"
                if learning_operation
                else "request_targeted_clarification"
            )
            target_ref = frontier.target_ref
            if evidence.get("surface"):
                literals = (str(evidence["surface"]),)
            qualifiers = {
                "frontier_kind": frontier.kind,
                "expected_semantic_kinds": list(
                    evidence.get("semantic_kind_candidates", ())
                ),
            }
            if learning_operation:
                qualifiers.update(
                    {
                        "learning_operation": str(learning_operation),
                        "learning_query": evidence.get("probe_query"),
                        "known_bindings": dict(evidence.get("known_bindings", {})),
                    }
                )
            reason = frontier.kind
        elif goal and goal.kind == "report_self_capability" and capability_assessments:
            preferred = set(goal.payload.get("preferred_capability_refs", ()))
            candidates = [
                item
                for item in capability_assessments
                if not preferred or item.capability_ref in preferred
            ] or list(capability_assessments)
            best = min(candidates, key=lambda item: (item.score, item.capability_ref))
            action = "report_capability"
            target_ref = best.capability_ref
            qualifiers = best.as_dict()
        elif goal and goal.kind == "greet":
            action = "greet"
        elif goal and goal.kind == "handle_directive":
            action = (
                "report_operation_result"
                if operation_result is not None and operation_result.status == "succeeded"
                else "decline_directive"
            )
            qualifiers = (
                operation_result.as_dict()
                if operation_result
                else {"reason": "no_authorized_operation"}
            )
        elif goal and goal.kind in {"acknowledge_claim", "acknowledge"}:
            action = "acknowledge_claim"
            if epistemic_placement is not None:
                qualifiers = epistemic_placement.as_dict()
        elif capability_assessments:
            best = max(capability_assessments, key=lambda item: item.score)
            action = "report_capability"
            target_ref = best.capability_ref
            qualifiers = best.as_dict()

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
            stable("response-csir", payload),
            action,
            audience_ref,
            target_ref,
            tuple(facts),
            tuple(bindings),
            qualifiers,
            tuple(literals),
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
            self.info[placeholder] = {
                "kind": "atom",
                "value": value,
                "context": context,
            }
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
        if isinstance(value, str) and ":" in value and not value.startswith("?"):
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
    query_kind = response.qualifiers.get("query_kind")
    if query_kind:
        parts += ["QUERY_KIND", str(query_kind)]
    property_ref = response.qualifiers.get("property_ref")
    if isinstance(property_ref, str):
        parts += ["PROPERTY", table.encode(property_ref, "response:property")]
    learning_operation = response.qualifiers.get("learning_operation")
    if learning_operation:
        parts += ["LEARNING", str(learning_operation)]
    for binding in response.bindings:
        parts.append("BINDING")
        for variable, value in sorted(binding.items()):
            parts += [variable, table.encode(value, f"binding:{variable}")]
    # Facts remain proof-bearing ResponseCSIR members. Binding responses use the
    # compact query target above so learned realization does not depend on every
    # optional proof role being present.
    if response.action != "answer_bindings":
        for fact in response.facts:
            parts.append("|")
            semantic, mapping = pointerize_fact(fact)
            for placeholder, info in mapping.items():
                replacement = table.encode(info["value"], info.get("context"))
                semantic = semantic.replace(placeholder, replacement)
            parts.append(semantic)
    # For designation_property binding answers, the binding value is the
    # evidence; the reviewed transform carries it via BINDING ?q0 @E0 and does
    # not include a separate EVIDENCE slot.  Adding one would break the
    # authorized-transform match and force a fallback realization.
    query_kind = response.qualifiers.get("query_kind")
    suppress_evidence = (
        response.action == "answer_bindings"
        and query_kind == "designation_property"
        and response.bindings
    )
    if not suppress_evidence:
        for literal in response.evidence_literals:
            parts += [
                "EVIDENCE",
                table.literal(
                    {"literal": {"type": "text", "value": literal}},
                    "response:evidence",
                ),
            ]
    if response.action == "report_capability" and "score" in response.qualifiers:
        value = round(float(response.qualifiers["score"]) * 100)
        parts += [
            "SCORE",
            table.literal(
                {"literal": {"type": "int", "value": value}},
                "response:score",
            ),
        ]
    return " ".join(parts), table.info
