"""StateOccupancyCompiler — compile StateOccupancyFrames from graph + kernel.

Activates the StateOccupancyFrame type (defined in types/state_transmutation.py)
by collecting current entity state values from two sources:

1. ContextKernel.entity_states — the cross-turn entity state registry
2. UOLGraph state atoms — reported states from the current turn

The compiler produces a list of StateOccupancyFrame objects that represent
the *current* state of entities before any proposed state changes are applied.
These are consumed by the StateTransmutationCompiler to populate prior_value
on StateTransmutationFrames, and by the SafetyFrameDetector to assess
severity based on magnitude of change from prior state.
"""

from __future__ import annotations

from typing import Any

from ...types.context_kernel import ContextKernel
from ...types.state_transmutation import StateOccupancyFrame
from ...types.uol_graph import UOLGraph


class StateOccupancyCompiler:
    """Compile StateOccupancyFrames from kernel entity states and graph state atoms."""

    def compile(
        self,
        graph: UOLGraph,
        kernel: ContextKernel | None = None,
    ) -> list[StateOccupancyFrame]:
        frames: list[StateOccupancyFrame] = []
        seen_keys: set[str] = set()

        # Source 1: Kernel entity state registry (cross-turn persisted states)
        if kernel is not None:
            for entry in kernel.entity_states.values():
                key = f"{entry.entity_ref}:{entry.state_family}.{entry.dimension}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                frames.append(StateOccupancyFrame(
                    target_ref=entry.entity_ref,
                    state_family=entry.state_family,
                    dimension=entry.dimension,
                    current_value=entry.current_value,
                    confidence=entry.confidence,
                    temporal_scope="session",
                    features={
                        "source": "kernel_registry",
                        "last_updated_signal_id": entry.last_updated_signal_id,
                    },
                ))

        # Source 2: Graph state atoms (reported states from current turn)
        for atom in graph.atoms.values():
            if atom.kind != "state":
                continue
            # Skip schema_state_delta atoms — those are proposed changes, not current state
            if atom.source == "schema_state_delta":
                continue

            dimension = atom.features.get("dimension", "")
            if not dimension:
                continue

            parts = dimension.split(".", 1)
            if len(parts) != 2:
                continue
            state_family, dim_name = parts

            # Find the entity that holds this state via has_property edges
            target_ref = self._find_entity_ref(graph, atom.id)
            if not target_ref:
                continue

            key = f"{target_ref}:{state_family}.{dim_name}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            frames.append(StateOccupancyFrame(
                target_ref=target_ref,
                state_family=state_family,
                dimension=dim_name,
                current_value=atom.value if atom.value is not None else atom.features.get("value"),
                confidence=atom.confidence,
                temporal_scope="current_turn",
                source_refs=[atom.id],
                features={
                    "source": "graph_state_atom",
                    "atom_source": atom.source,
                },
            ))

        return frames

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
