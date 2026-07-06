"""SemanticProgram — executable IR view of one turn's UOL graph.

SemanticProgram is the instruction stream compiled from UOLGraph. It groups
meaning groups into typed semantic instructions with discourse hierarchy
and an entry instruction determined by semantic obligation ranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


INSTRUCTION_KINDS = frozenset({
    "exit",
    "social",
    "question",
    "teaching",
    "assertion",
    "correction",
    "command",
    "repair",
    "safety",
    "creative",
    "unknown",
})


@dataclass
class SemanticInstruction:
    instruction_id: str
    group_id: str
    surface: str
    instruction_kind: str
    atom_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    candidate_set_ids: list[str] = field(default_factory=list)
    construction_match_ids: list[str] = field(default_factory=list)
    predicate_ids: list[str] = field(default_factory=list)
    input_slots: dict[str, str] = field(default_factory=dict)
    output_slots: dict[str, str] = field(default_factory=dict)
    discourse_parent_id: str = ""
    discourse_relation: str = ""
    confidence: float = 0.5


@dataclass
class SemanticProgram:
    graph_id: str
    signal_id: str
    context_id: str
    instructions: list[SemanticInstruction] = field(default_factory=list)
    entry_instruction_id: str = ""
    discourse_edges: list[str] = field(default_factory=list)
    candidate_sets: list[str] = field(default_factory=list)
    suppressed_instruction_ids: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5

    @property
    def entry_instruction(self) -> SemanticInstruction | None:
        for inst in self.instructions:
            if inst.instruction_id == self.entry_instruction_id:
                return inst
        return None

    @property
    def instruction_by_id(self) -> dict[str, SemanticInstruction]:
        return {inst.instruction_id: inst for inst in self.instructions}
