from __future__ import annotations

from typing import Any

from ..types.semantic_focus import SemanticFocus
from ..types.uol_graph import UOLGraph, UOLAtom, PortBinding, CandidateSet, ConceptResolution, AffordancePrediction
from ..types.context_kernel import ContextKernel, Budget
from .semantic_working_set import SemanticWorkingSet

SAFETY_RISK_KEYS = frozenset({"deny", "restricted", "quarantine"})


class SemanticAttentionController:
    """Instruction scheduler — decides what the runtime should focus on."""

    def attend(
        self,
        graph: UOLGraph,
        kernel: ContextKernel,
        budget: Budget | None = None,
    ) -> SemanticWorkingSet:
        effective_budget = budget if budget is not None else kernel.budget

        focus_items: list[SemanticFocus] = []
        risk_flags: list[str] = []
        unresolved_ports: list[dict[str, Any]] = []
        evidence_requirements: list[dict[str, Any]] = []
        seen_atom_ids: set[str] = set()

        # Tier 1: Safety/risk atoms (priority = 1)
        for atom in graph.atoms.values():
            if atom.kind == "permission" and atom.key in SAFETY_RISK_KEYS:
                focus_items.append(SemanticFocus(
                    atom_id=atom.id,
                    reason=f"safety_risk:{atom.key}",
                    priority=1,
                    confidence=atom.confidence,
                ))
                risk_flags.append(f"permission:{atom.key}")
                seen_atom_ids.add(atom.id)

        # Tier 2: Unresolved required ports (priority = 2)
        for binding in graph.port_bindings:
            if binding.status == "placeholder" and binding.required:
                focus_items.append(SemanticFocus(
                    atom_id=binding.owner_atom_id,
                    reason=f"unresolved_required_port:{binding.port_key}",
                    priority=2,
                    confidence=binding.score,
                ))
                unresolved_ports.append({
                    "port_key": binding.port_key,
                    "owner_atom_id": binding.owner_atom_id,
                    "required": binding.required,
                })
                seen_atom_ids.add(binding.owner_atom_id)

        # Tier 3: Fresh evidence requirements (priority = 3)
        for cr in graph.concept_resolutions:
            if cr.atom_id not in seen_atom_ids and (cr.state == "unresolved" or cr.confidence < 0.3):
                focus_items.append(SemanticFocus(
                    atom_id=cr.atom_id,
                    reason=f"evidence_needed:{cr.state}",
                    priority=3,
                    confidence=cr.confidence,
                ))
                evidence_requirements.append({
                    "atom_id": cr.atom_id,
                    "reason": cr.reason or cr.state,
                    "confidence": cr.confidence,
                })
                seen_atom_ids.add(cr.atom_id)

        # Tier 4: Ambiguous candidate sets (priority = 4)
        for cs in graph.candidate_sets:
            if not cs.resolved:
                atom_id = cs.selected_atom_id or cs.target_span_id
                if atom_id not in seen_atom_ids:
                    focus_items.append(SemanticFocus(
                        atom_id=atom_id,
                        reason=f"ambiguous_candidates:{cs.id}",
                        priority=4,
                        confidence=cs.confidence,
                    ))
                    if atom_id:
                        seen_atom_ids.add(atom_id)

        # Tier 5: Anaphora/deixis unresolved — not yet implemented
        # Tier 6: Contradiction markers — not yet implemented

        # Tier 7: Active intent atoms (priority = 7)
        for atom in graph.atoms.values():
            if atom.kind == "intent" and atom.id not in seen_atom_ids:
                focus_items.append(SemanticFocus(
                    atom_id=atom.id,
                    reason="active_intent",
                    priority=7,
                    confidence=atom.confidence,
                ))
                seen_atom_ids.add(atom.id)

        # Tier 8: Self/action affordance requirements (priority = 8)
        for atom in graph.atoms.values():
            if atom.kind in ("self", "action") and atom.id not in seen_atom_ids:
                focus_items.append(SemanticFocus(
                    atom_id=atom.id,
                    reason=f"affordance:{atom.kind}",
                    priority=8,
                    confidence=atom.confidence,
                ))
                seen_atom_ids.add(atom.id)

        # Tier 8b: Affordance prediction triggers (priority = 8)
        for pred in graph.affordance_predictions:
            for atom_id in pred.trigger_atom_ids:
                if atom_id not in seen_atom_ids:
                    focus_items.append(SemanticFocus(
                        atom_id=atom_id,
                        reason=f"affordance_prediction:{pred.affordance_key}",
                        priority=8,
                        confidence=pred.confidence,
                    ))
                    seen_atom_ids.add(atom_id)

        # Tier 9: Low-confidence predicate bindings (priority = 9)
        for cr in graph.concept_resolutions:
            if cr.atom_id not in seen_atom_ids and cr.confidence < 0.5:
                focus_items.append(SemanticFocus(
                    atom_id=cr.atom_id,
                    reason="low_confidence_predicate",
                    priority=9,
                    confidence=cr.confidence,
                ))

        focus_items.sort(key=lambda f: f.priority)

        selected_paths: list[str] = [
            cs.selected_atom_id
            for cs in graph.candidate_sets
            if cs.selected_atom_id
        ]

        rejected_paths: list[str] = [
            cid
            for cs in graph.candidate_sets
            for cid in cs.rejected_candidate_ids
        ]

        return SemanticWorkingSet(
            focus_items=focus_items,
            selected_paths=selected_paths,
            rejected_paths=rejected_paths,
            unresolved_ports=unresolved_ports,
            evidence_requirements=evidence_requirements,
            risk_flags=risk_flags,
        )
