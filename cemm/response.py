"""Target-aware Response CSIR, semantic planning and deterministic pointerization."""
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
            "bindings": [dict(x) for x in self.bindings],
            "qualifiers": dict(self.qualifiers),
            "evidence_literals": list(self.evidence_literals),
            "reason": self.reason,
            "obligation_ref": self.obligation_ref,
        }


class ResponseBuilder:
    """Construct response meaning from the actual target, never a global status."""

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
        facts = []
        bindings = []
        qualifiers = {}
        literals = []
        reason = goal_decision.reason if goal_decision else "no_goal"
        obligation_ref = goal.goal_ref if goal else None

        if goal and goal.kind == "answer_query" and query_result is not None:
            target_ref = None
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
        elif goal and goal.kind == "clarify" and frontiers:
            frontier = frontiers[0]
            action = "request_targeted_clarification"
            target_ref = frontier.target_ref
            literals = tuple(
                str(item.get("surface"))
                for item in frontier.evidence
                if item.get("surface")
            )[:1]
            reason = frontier.kind
        elif goal and goal.kind == "report_self_capability" and capability_assessments:
            preferred = set(goal.payload.get("preferred_capability_refs", ()))
            candidates = [
                item for item in capability_assessments
                if not preferred or item.capability_ref in preferred
            ] or list(capability_assessments)
            # A broad operational answer reports the weakest top-level capability,
            # avoiding a misleading healthy sub-capability when another root is degraded.
            best = min(candidates, key=lambda item: (item.score, item.capability_ref))
            action = "report_capability"
            target_ref = best.capability_ref
            qualifiers = best.as_dict()
        elif goal and goal.kind == "greet":
            action = "greet"
            target_ref = None
        elif goal and goal.kind == "handle_directive":
            if operation_result is not None and operation_result.status == "succeeded":
                action = "report_operation_result"
            else:
                action = "decline_directive"
            target_ref = None
            qualifiers = operation_result.as_dict() if operation_result else {"reason": "no_authorized_operation"}
        elif goal and goal.kind in {"acknowledge_claim", "acknowledge"}:
            action = "acknowledge_claim"
            target_ref = None
            if epistemic_placement is not None:
                qualifiers = epistemic_placement.as_dict()
        elif capability_assessments:
            best = max(capability_assessments, key=lambda item: item.score)
            action = "report_capability"
            target_ref = best.capability_ref
            qualifiers = best.as_dict()

        payload = (action, audience_ref, target_ref, [x.ref for x in facts], bindings, qualifiers, literals, reason, obligation_ref)
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


def pointerize_fact(fact: Fact):
    refs = sorted({value for value in fact.args.values() if isinstance(value, str) and ":" in value})
    placeholders = {ref: f"@A{index}" for index, ref in enumerate(refs)}
    contexts = {}
    for role, value in fact.args.items():
        if value in placeholders:
            contexts.setdefault(value, role)
    parts = ["FACT", fact.stance, fact.operator]
    for role, value in sorted(fact.args.items()):
        parts += [role, placeholders.get(value, canonical(value) if isinstance(value, dict) else str(value))]
    return " ".join(parts), {placeholders[ref]: (ref, contexts.get(ref)) for ref in refs}


def pointerize_plan(plan):
    refs = set()
    if plan.get("value") and isinstance(plan["value"], str):
        refs.add(plan["value"])
    for fact in plan.get("facts", ()):
        refs.update(value for value in fact.args.values() if isinstance(value, str) and ":" in value)
    refs = sorted(refs)
    placeholders = {ref: f"@A{index}" for index, ref in enumerate(refs)}
    contexts = {}
    parts = ["PLAN", plan["goal"]]
    if plan.get("value"):
        value = plan["value"]
        parts += ["VALUE", placeholders.get(value, str(value))]
        if value in placeholders:
            contexts[value] = "response:value"
    for fact in plan.get("facts", ()):
        parts += ["|", "FACT", fact.stance, fact.operator]
        for role, value in sorted(fact.args.items()):
            parts += [role, placeholders.get(value, canonical(value) if isinstance(value, dict) else str(value))]
            if value in placeholders:
                contexts.setdefault(value, role)
    return " ".join(parts), {placeholders[ref]: (ref, contexts.get(ref)) for ref in refs}


def pointerize_response(response: ResponseCSIR):
    atom_refs = set()
    if response.target_ref and ":" in response.target_ref:
        atom_refs.add(response.target_ref)
    for fact in response.facts:
        atom_refs.update(value for value in fact.args.values() if isinstance(value, str) and ":" in value)
    for binding in response.bindings:
        atom_refs.update(value for value in binding.values() if isinstance(value, str) and ":" in value)
    atom_refs = sorted(atom_refs)
    atom_map = {ref: f"@A{index}" for index, ref in enumerate(atom_refs)}
    literal_map = {value: f"@E{index}" for index, value in enumerate(response.evidence_literals)}
    parts = ["RESPONSE", response.action]
    if response.target_ref:
        parts += ["TARGET", atom_map.get(response.target_ref, response.target_ref)]
    for binding in response.bindings:
        parts.append("BINDING")
        for variable, value in sorted(binding.items()):
            parts += [variable, atom_map.get(value, canonical(value) if isinstance(value, dict) else str(value))]
    for fact in response.facts:
        parts.append("|")
        fact_semantic, _ = pointerize_fact(fact)
        for ref, placeholder in atom_map.items():
            fact_semantic = fact_semantic.replace(ref, placeholder)
        parts.append(fact_semantic)
    for literal in response.evidence_literals:
        parts += ["EVIDENCE", literal_map[literal]]
    number_map = {}
    if response.action == "report_capability" and "score" in response.qualifiers:
        value = round(float(response.qualifiers["score"]) * 100)
        number_map[value] = "@N0"
        parts += ["SCORE", "@N0"]
    semantic = " ".join(parts)
    placeholders = {placeholder: {"kind": "atom", "value": ref} for ref, placeholder in atom_map.items()}
    placeholders.update({placeholder: {"kind": "evidence", "value": literal} for literal, placeholder in literal_map.items()})
    placeholders.update({placeholder: {"kind": "number", "value": value} for value, placeholder in number_map.items()})
    return semantic, placeholders
