"""StateDeltaCompiler — compile StateDeltaFrames from UOL graph state atoms.

Activates the StateDeltaFrame type (defined in types/state_transmutation.py)
by compiling proposed state changes from the graph's schema_state_delta atoms.

The compiler traverses the graph:
1. Finds all state atoms with source="schema_state_delta"
2. For each, finds the causes edge to get the source action atom
3. For each, finds the has_property edge to get the target entity
4. Creates a StateDeltaFrame with dimension, direction, action context

These delta frames are consumed by the StateTransmutationCompiler to build
StateTransmutationFrames with prior_value (from occupancy) and proposed_value.
"""

from __future__ import annotations

from typing import Any

from ..types.operational_meaning import OperationalMeaningFrame
from ..types.state_transmutation import StateDeltaFrame
from ..types.uol_graph import UOLGraph


class StateDeltaCompiler:
    """Compile StateDeltaFrames from graph schema_state_delta atoms."""

    def compile(
        self,
        graph: UOLGraph,
        frames: list[OperationalMeaningFrame] | None = None,
    ) -> list[StateDeltaFrame]:
        deltas: list[StateDeltaFrame] = []

        # Build a map from group_id to frame_id for source_frame_id lookup
        group_to_frame: dict[str, str] = {}
        if frames is not None:
            for frame in frames:
                if frame.group_id:
                    group_to_frame[frame.group_id] = frame.frame_id

        for atom in graph.atoms.values():
            if atom.kind != "state" or atom.source != "schema_state_delta":
                continue

            dimension = atom.features.get("dimension", "")
            direction = atom.features.get("direction", "unknown")
            target_role = atom.features.get("target_role", "actor")
            action_key = atom.features.get("action_key", "")

            if not dimension:
                continue

            parts = dimension.split(".", 1)
            if len(parts) != 2:
                continue
            state_family, dim_name = parts

            # Find target entity ref via has_property edges
            target_ref = self._find_entity_ref(graph, atom.id)

            # Find source frame_id from group_id
            source_frame_id = group_to_frame.get(atom.group_id, "")

            deltas.append(StateDeltaFrame(
                target_ref=target_ref or f"role:{target_role}",
                state_family=state_family,
                dimension=dim_name,
                direction=direction,
                source_frame_id=source_frame_id,
                confidence=atom.confidence,
                evidence_refs=[atom.id],
                features={
                    "action_key": action_key,
                    "target_role": target_role,
                    "atom_id": atom.id,
                },
            ))

        return deltas

    @staticmethod
    def _find_entity_ref(graph: UOLGraph, state_atom_id: str) -> str:
        """Find the entity reference for a state atom via has_property edges."""
        for edge in graph.incoming(state_atom_id, "has_property"):
            entity = graph.atoms.get(edge.source_id)
            if entity is None:
                continue
            if entity.kind in ("entity", "self"):
                return entity.key
        return ""
