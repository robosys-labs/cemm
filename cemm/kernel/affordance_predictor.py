"""Causal affordance prediction over bound working graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..types.uol_graph import AffordancePrediction, UOLGraph


@dataclass
class AffordanceRule:
    key: str
    trigger_kind: str = ""
    trigger_key: str = ""
    required_port_keys: set[str] = field(default_factory=set)
    effect_type: str = "state_change"
    predicted_operation: str = "observe_causal_affordance"
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5


class AffordancePredictor:
    """Pattern matcher for contextual affordance rules."""

    def __init__(self, rules: list[AffordanceRule] | None = None) -> None:
        self._rules = rules or self._seed_rules()

    def predict(self, graph: UOLGraph) -> list[AffordancePrediction]:
        predictions: list[AffordancePrediction] = []
        for atom in graph.atoms.values():
            for rule in self._rules:
                if rule.trigger_kind and atom.kind != rule.trigger_kind:
                    continue
                if rule.trigger_key and rule.trigger_key not in {atom.key, atom.surface}:
                    continue
                bindings = graph.bindings_for_owner(atom.id)
                binding_keys = {binding.port_key for binding in bindings if binding.status == "bound"}
                if not rule.required_port_keys <= binding_keys:
                    continue
                predictions.append(AffordancePrediction(
                    id=f"aff_{len(predictions)}_{rule.key}",
                    affordance_key=rule.key,
                    trigger_atom_ids=[atom.id],
                    required_binding_ids=[binding.source_edge_id for binding in bindings if binding.port_key in rule.required_port_keys],
                    predicted_patch_template={
                        "target": "causal_affordance",
                        "operation": rule.predicted_operation,
                        **dict(rule.payload),
                    },
                    effect_type=rule.effect_type,
                    confidence=min(1.0, max(atom.confidence, rule.confidence)),
                    reason="affordance_rule_match",
                ))
        return predictions

    @staticmethod
    def _seed_rules() -> list[AffordanceRule]:
        return [
            AffordanceRule(
                key="fresh_source_requirement",
                trigger_kind="evidence",
                trigger_key="fresh_external_evidence_required",
                effect_type="action_enablement",
                payload={"policy": "require_fresh_source"},
                confidence=0.7,
            ),
            AffordanceRule(
                key="clarity_need",
                trigger_kind="intent",
                trigger_key="repair",
                effect_type="need_activation",
                payload={"need_key": "clarity"},
                confidence=0.65,
            ),
            AffordanceRule(
                key="cold_context_comfort_relevance",
                trigger_kind="state",
                trigger_key="cold",
                required_port_keys={"holder"},
                effect_type="need_activation",
                payload={"need_key": "comfort_or_warmth_may_be_relevant"},
                confidence=0.58,
            ),
        ]
