"""Causal affordance prediction over bound working graphs."""

from __future__ import annotations

from typing import Any

from ..types.causal_affordance import CausalAffordance, PortBindingPattern
from ..types.predicate_schema import GraphPattern
from ..types.uol_atom import UOLAtom
from ..types.uol_graph import AffordancePrediction, UOLGraph


class AffordancePredictor:
    """Pattern matcher for contextual affordance rules."""

    def __init__(self, rules: list[CausalAffordance] | None = None) -> None:
        self._rules = rules or self._seed_rules()

    def predict(self, graph: UOLGraph) -> list[AffordancePrediction]:
        predictions: list[AffordancePrediction] = []
        for atom in graph.atoms.values():
            for affordance in self._rules:
                pattern = affordance.trigger_pattern
                if pattern is not None and pattern.atom_patterns:
                    if not self._atom_matches_patterns(atom, pattern.atom_patterns):
                        continue
                elif pattern is not None:
                    continue
                bindings = graph.bindings_for_owner(atom.id)
                binding_keys = {b.port_key for b in bindings if b.status == "bound"}
                required_ports = {bp.port_id for bp in affordance.required_bindings if bp.required}
                if required_ports and not required_ports.issubset(binding_keys):
                    continue
                predictions.append(AffordancePrediction(
                    id=f"aff_{len(predictions)}_{affordance.affordance_id}",
                    affordance_key=affordance.affordance_id,
                    trigger_atom_ids=[atom.id],
                    required_binding_ids=[b.source_edge_id for b in bindings if b.port_key in required_ports],
                    predicted_patch_template={
                        "target": "causal_affordance",
                        "operation": "observe_causal_affordance",
                    },
                    effect_type=affordance.effect_type,
                    confidence=min(1.0, max(atom.confidence, affordance.confidence)),
                    reason="affordance_rule_match",
                ))
        return predictions

    @staticmethod
    def _atom_matches_patterns(atom: UOLAtom, patterns: list[dict[str, Any]]) -> bool:
        for pattern in patterns:
            kind_match = not pattern.get("kind") or atom.kind == pattern["kind"]
            key_match = not pattern.get("key") or atom.key == pattern["key"]
            surface_match = not pattern.get("surface") or atom.surface == pattern["surface"]
            if kind_match and key_match and surface_match:
                return True
        return False

    @staticmethod
    def _seed_rules() -> list[CausalAffordance]:
        return [
            CausalAffordance(
                affordance_id="fresh_source_requirement",
                trigger_pattern=GraphPattern(atom_patterns=[
                    {"kind": "evidence", "key": "fresh_external_evidence_required"},
                ]),
                effect_type="action_enablement",
                confidence=0.7,
            ),
            CausalAffordance(
                affordance_id="clarity_need",
                trigger_pattern=GraphPattern(atom_patterns=[
                    {"kind": "intent", "key": "repair"},
                ]),
                effect_type="need_activation",
                confidence=0.65,
            ),
            CausalAffordance(
                affordance_id="cold_context_comfort_relevance",
                trigger_pattern=GraphPattern(atom_patterns=[
                    {"kind": "state", "key": "cold"},
                ]),
                required_bindings=[
                    PortBindingPattern(port_id="holder", required=True),
                ],
                effect_type="need_activation",
                confidence=0.58,
            ),
        ]
