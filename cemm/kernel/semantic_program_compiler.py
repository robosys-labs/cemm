"""SemanticProgramCompiler — compile UOLGraph into SemanticProgram.

Turns each UOLMeaningGroup into a SemanticInstruction, classifies the
instruction kind from graph structure (not surface phrases), preserves
discourse hierarchy, and ranks the entry instruction by semantic
obligation force.
"""

from __future__ import annotations

import uuid
from typing import Any

from ..types.meaning_percept import MeaningPerceptPacket
from ..types.semantic_program import SemanticInstruction, SemanticProgram
from ..types.uol_graph import UOLGraph


_OBLIGATION_RANK = {
    "safety": 0,
    "question": 1,
    "correction": 2,
    "repair": 2,
    "teaching": 3,
    "assertion": 4,
    "command": 5,
    "exit": 6,
    "social": 7,
    "creative": 8,
    "unknown": 9,
}


class SemanticProgramCompiler:
    def compile(
        self,
        graph: UOLGraph,
        percept: MeaningPerceptPacket | None = None,
        kernel: Any | None = None,
    ) -> SemanticProgram:
        instructions: list[SemanticInstruction] = []
        for group in graph.groups:
            inst = self._compile_group(graph, group)
            instructions.append(inst)

        for inst in instructions:
            inst.discourse_parent_id = self._find_parent(inst, graph)

        entry_id, ranked_all = self._rank_entry(instructions, graph)
        rejected_candidates = [
            {"id": inst.instruction_id, "kind": inst.instruction_kind, "rank": i}
            for i, inst in enumerate(ranked_all)
            if inst.instruction_id != entry_id
        ]

        return SemanticProgram(
            graph_id=graph.id,
            signal_id=graph.signal_id,
            context_id=graph.context_id,
            instructions=instructions,
            entry_instruction_id=entry_id,
            discourse_edges=[e.id for e in graph.edges],
            candidate_sets=[cs.id for cs in graph.candidate_sets],
            diagnostics={
                "compiler": "semantic_program_compiler_v2",
                "instruction_count": len(instructions),
                "entry_kind": next(
                    (i.instruction_kind for i in instructions if i.instruction_id == entry_id),
                    "unknown",
                ),
                "rejected_candidates": rejected_candidates,
            },
        )

    def _compile_group(self, graph: UOLGraph, group: Any) -> SemanticInstruction:
        atom_ids = list(group.atom_ids)
        edge_ids = list(group.edge_ids)
        candidate_set_ids = [
            cs.id for cs in graph.candidate_sets if cs.group_id == group.id
        ]
        construction_match_ids = [
            cm.id for cm in graph.construction_matches if cm.group_id == group.id
        ]
        kind = self._classify_kind(graph, group, atom_ids)
        input_slots, output_slots = self._extract_slots(graph, group, atom_ids)
        predicate_ids = [
            edge.predicate_id
            for edge in graph.edges
            if edge.group_id == group.id and edge.predicate_id
        ]

        return SemanticInstruction(
            instruction_id=uuid.uuid4().hex[:16],
            group_id=group.id,
            surface=group.surface,
            instruction_kind=kind,
            atom_ids=atom_ids,
            edge_ids=edge_ids,
            candidate_set_ids=candidate_set_ids,
            construction_match_ids=construction_match_ids,
            predicate_ids=predicate_ids,
            input_slots=input_slots,
            output_slots=output_slots,
            discourse_parent_id=group.parent_group_id,
            discourse_relation=group.features.get("discourse_relation", ""),
            confidence=group.confidence,
        )

    _INTENT_KEY_TO_KIND: dict[str, str] = {
        "question": "question",
        "fresh_world_query": "question",
        "capability_query": "question",
        "self_identity_query": "question",
        "self_knowledge_query": "question",
        "teaching": "teaching",
        "repair": "repair",
        "command": "command",
        "greeting": "social",
        "phatic_checkin": "social",
        "reciprocal_phatic": "social",
        "acknowledgment": "social",
        "statement": "assertion",
        "session_exit": "exit",
        "user_state_report": "assertion",
        "self_reflect": "self_reflect",
    }

    def _classify_kind(self, graph: UOLGraph, group: Any, atom_ids: list[str]) -> str:
        kind_scores: dict[str, float] = {}

        for aid in atom_ids:
            atom = graph.atoms.get(aid)
            if atom is None:
                continue
            if atom.kind == "intent":
                mapped = self._INTENT_KEY_TO_KIND.get(atom.key, "")
                if mapped:
                    kind_scores[mapped] = kind_scores.get(mapped, 0.0) + atom.confidence
                elif "correct" in atom.key or "repair" in atom.key:
                    kind_scores["correction"] = kind_scores.get("correction", 0.0) + atom.confidence
                elif "safety" in atom.key or "harm" in atom.key:
                    kind_scores["safety"] = kind_scores.get("safety", 0.0) + atom.confidence
                elif "creative" in atom.key or "story" in atom.key:
                    kind_scores["creative"] = kind_scores.get("creative", 0.0) + atom.confidence
            if atom.kind == "permission" and atom.key in ("deny", "restrict"):
                kind_scores["safety"] = kind_scores.get("safety", 0.0) + atom.confidence

        for edge in graph.edges:
            if edge.group_id == group.id:
                if edge.edge_type == "asks_about":
                    kind_scores["question"] = kind_scores.get("question", 0.0) + edge.confidence
                if edge.edge_type == "teaches":
                    kind_scores["teaching"] = kind_scores.get("teaching", 0.0) + edge.confidence
                if edge.edge_type == "causes":
                    kind_scores["assertion"] = kind_scores.get("assertion", 0.0) + edge.confidence
                if edge.edge_type in ("is_a", "same_as"):
                    kind_scores["assertion"] = kind_scores.get("assertion", 0.0) + edge.confidence

        if kind_scores:
            return max(kind_scores, key=lambda k: kind_scores[k])

        func = getattr(group, "function", "unknown")
        if func in ("question", "teaching", "command", "social", "assertion", "repair"):
            return func

        return "unknown"

    def _extract_slots(
        self, graph: UOLGraph, group: Any, atom_ids: list[str]
    ) -> tuple[dict[str, str], dict[str, str]]:
        input_slots: dict[str, str] = {}
        output_slots: dict[str, str] = {}

        for binding in graph.port_bindings:
            if binding.owner_atom_id in atom_ids:
                port = binding.port_key
                if binding.status == "bound" and binding.filler_atom_id:
                    input_slots[port] = binding.filler_atom_id
                elif binding.status == "placeholder":
                    output_slots[port] = ""

        return input_slots, output_slots

    def _find_parent(self, inst: SemanticInstruction, graph: UOLGraph) -> str:
        for group in graph.groups:
            if group.id == inst.group_id and group.parent_group_id:
                return group.parent_group_id
        return inst.discourse_parent_id

    def _rank_entry(self, instructions: list[SemanticInstruction], graph: UOLGraph) -> tuple[str, list[SemanticInstruction]]:
        if not instructions:
            return "", []

        scored = sorted(
            instructions,
            key=lambda inst: (
                _OBLIGATION_RANK.get(inst.instruction_kind, 8),
                -inst.confidence,
            ),
        )

        return scored[0].instruction_id, scored
