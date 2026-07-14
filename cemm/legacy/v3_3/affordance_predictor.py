"""Causal affordance prediction over bound working graphs."""

from __future__ import annotations

from typing import Any

from ...types.causal_affordance import CausalAffordance, PortBindingPattern
from ...types.predicate_schema import GraphPattern, GraphPatchTemplate
from ...types.uol_atom import UOLAtom
from ...types.uol_graph import AffordancePrediction, UOLGraph
from .semantic_schema_kernel import SemanticSchemaKernel, get_kernel


class AffordancePredictor:
    """Pattern matcher for contextual affordance rules.

    Rules are loaded from the Semantic Schema Kernel's AffordanceRegistry.
    The kernel's affordance schemas define trigger patterns, required bindings,
    effect types, predicted patch templates, and confidence scores.
    """

    def __init__(
        self,
        rules: list[CausalAffordance] | None = None,
        schema_kernel: SemanticSchemaKernel | None = None,
    ) -> None:
        self._kernel = schema_kernel or get_kernel()
        self._rules = rules or self._load_rules_from_kernel()

    def _load_rules_from_kernel(self) -> list[CausalAffordance]:
        """Build CausalAffordance rules from the kernel's AffordanceRegistry."""
        rules: list[CausalAffordance] = []
        for schema in self._kernel.affordances.all():
            trigger = schema.trigger_pattern
            atom_patterns = []
            if trigger:
                kind = trigger.get("atom_kind", "")
                key = trigger.get("atom_key", "")
                if kind or key:
                    atom_patterns.append({"kind": kind, "key": key})
            required_bindings = []
            for binding in schema.required_bindings:
                required_bindings.append(PortBindingPattern(port_id=binding, required=True))
            template_ops: list[dict[str, Any]] = []
            patch_template = schema.predicted_patch_template
            if patch_template:
                for k, v in patch_template.items():
                    template_ops.append({"key": k, "value": v})
            rules.append(CausalAffordance(
                affordance_id=schema.affordance_key,
                trigger_pattern=GraphPattern(atom_patterns=atom_patterns),
                required_bindings=required_bindings,
                effect_type=schema.effect_type,
                predicted_effect=GraphPatchTemplate(operations=template_ops) if template_ops else None,
                confidence=schema.confidence,
            ))
        return rules

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
                template = affordance.predicted_effect
                predicted_patch_template = {
                    "target": template.target if template else "causal_affordance",
                    "operation": "observe_causal_affordance",
                }
                if template and template.operations:
                    predicted_patch_template.update({op.get("key", ""): op.get("value", "") for op in template.operations if isinstance(op, dict)})
                predictions.append(AffordancePrediction(
                    id=f"aff_{len(predictions)}_{affordance.affordance_id}",
                    affordance_key=affordance.affordance_id,
                    trigger_atom_ids=[atom.id],
                    required_binding_ids=[b.source_edge_id for b in bindings if b.port_key in required_ports],
                    predicted_patch_template=predicted_patch_template,
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
