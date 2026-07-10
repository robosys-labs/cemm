"""Compile StateTransmutationFrames from operational meaning frames.

State transmutations are runtime authority units. They describe state changes
without adding new UOL atom kinds or edge types.

Extended in the meaning-based safety refactor to compile transmutations from
StateDeltaFrames (proposed changes from graph schema_state_delta atoms) with
prior_value populated from StateOccupancyFrames (current entity states).
"""

from __future__ import annotations

import uuid
from typing import Any

from ..types.operational_meaning import OperationalMeaningFrame
from ..types.state_transmutation import (
    StateDeltaFrame,
    StateOccupancyFrame,
    StateTransmutationFrame,
)


class StateTransmutationCompiler:
    """Compile state transitions implied by selected operational meanings."""

    def compile(
        self,
        graph: Any,
        frames: list[OperationalMeaningFrame],
        delta_frames: list[StateDeltaFrame] | None = None,
        occupancy_frames: list[StateOccupancyFrame] | None = None,
    ) -> list[StateTransmutationFrame]:
        transmutations: list[StateTransmutationFrame] = []

        # Path 1: Compile from operational meaning frame types (existing)
        for frame in frames:
            transmutation = self._compile_frame(graph, frame)
            if transmutation is not None:
                transmutations.append(transmutation)
                frame.state_transmutations.append(transmutation)

        # Path 2: Compile from StateDeltaFrames (new — meaning-based)
        if delta_frames:
            occupancy_index = self._index_occupancy(occupancy_frames or [])
            frame_index = {f.frame_id: f for f in frames}
            for delta in delta_frames:
                transmutation = self._compile_from_delta(
                    delta, occupancy_index, frame_index,
                )
                if transmutation is not None:
                    transmutations.append(transmutation)
                    source_frame = frame_index.get(delta.source_frame_id)
                    if source_frame is not None:
                        source_frame.state_transmutations.append(transmutation)

        return transmutations

    def _compile_from_delta(
        self,
        delta: StateDeltaFrame,
        occupancy_index: dict[str, StateOccupancyFrame],
        frame_index: dict[str, OperationalMeaningFrame],
    ) -> StateTransmutationFrame | None:
        """Compile a StateDeltaFrame into a StateTransmutationFrame.

        Uses prior_value from the corresponding StateOccupancyFrame if available.
        Determines transmutation_kind and authority from the source frame type.
        """
        # Look up prior state from occupancy
        occ_key = f"{delta.target_ref}:{delta.state_family}.{delta.dimension}"
        prior = occupancy_index.get(occ_key)
        prior_value = prior.current_value if prior else None

        # Determine transmutation_kind and authority from source frame
        source_frame = frame_index.get(delta.source_frame_id)
        transmutation_kind = "observed"
        authority = "user_asserted"
        persistence_policy = "session_state"
        temporal_scope = "current_turn"

        if source_frame is not None:
            ftype = source_frame.frame_type
            if ftype == "command":
                transmutation_kind = "commanded"
                authority = "user_asserted"
                persistence_policy = "session_state"
                temporal_scope = "session"
            elif ftype == "safety_candidate":
                transmutation_kind = "inferred"
                authority = "policy_authorized"
                persistence_policy = "quarantine"
                temporal_scope = "ephemeral"
            elif ftype == "user_state_report":
                transmutation_kind = "reported"
                authority = "user_asserted"
                persistence_policy = "session_state"
                temporal_scope = "session"
            elif ftype == "world_fact_claim":
                transmutation_kind = "reported"
                authority = "user_asserted"
                persistence_policy = "graph_patch_candidate"
                temporal_scope = "persistent"

        # Build features with action context for safety detection
        features: dict[str, Any] = {}
        if source_frame is not None:
            features.update(source_frame.features)
        features.update(delta.features)
        features["compiled_from"] = "state_delta"

        return StateTransmutationFrame(
            transmutation_id=f"stm_{uuid.uuid4().hex[:12]}",
            source_frame_id=delta.source_frame_id,
            target_ref=delta.target_ref,
            state_family=delta.state_family,
            dimension=delta.dimension,
            prior_value=prior_value,
            proposed_value=None,
            direction=delta.direction,
            transmutation_kind=transmutation_kind,
            authority=authority,
            persistence_policy=persistence_policy,
            temporal_scope=temporal_scope,
            source_refs=[],
            evidence_refs=list(delta.evidence_refs),
            confidence=delta.confidence,
            features=features,
        )

    @staticmethod
    def _index_occupancy(
        occupancy_frames: list[StateOccupancyFrame],
    ) -> dict[str, StateOccupancyFrame]:
        """Index occupancy frames by target_ref:state_family.dimension."""
        index: dict[str, StateOccupancyFrame] = {}
        for occ in occupancy_frames:
            key = f"{occ.target_ref}:{occ.state_family}.{occ.dimension}"
            index[key] = occ
        return index

    def _compile_frame(
        self,
        graph: Any,
        frame: OperationalMeaningFrame,
    ) -> StateTransmutationFrame | None:
        if frame.frame_type == "profile_assertion":
            dimension = frame.dimension or frame.features.get("property_dimension", "")
            if not dimension:
                return None
            return self._frame(
                frame,
                target_ref="entity:user",
                state_family="identity" if dimension == "name" else "contextual",
                dimension=dimension,
                proposed_value=self._object_surface(graph, frame),
                persistence_policy="graph_patch_candidate",
                temporal_scope="persistent",
            )

        if frame.frame_type in ("style_feedback", "response_feedback"):
            dimension = frame.dimension or frame.features.get("dimension", "response_detail")
            return self._frame(
                frame,
                target_ref="conversation:style",
                state_family="operational",
                dimension=dimension,
                direction="decrease" if dimension in {"verbosity", "response_detail", "detail"} else "set",
                transmutation_kind="reported",
                persistence_policy="session_state",
                temporal_scope="session",
            )

        if frame.frame_type == "session_exit":
            return self._frame(
                frame,
                target_ref=f"conversation:{getattr(graph, 'context_id', '') or frame.graph_id}",
                state_family="temporal",
                dimension="status",
                proposed_value="closing",
                transmutation_kind="commanded",
                persistence_policy="session_state",
                temporal_scope="session",
            )

        if frame.frame_type == "user_state_report":
            return self._frame(
                frame,
                target_ref="entity:user",
                state_family="affective",
                dimension=frame.dimension or frame.features.get("dimension", "mood"),
                proposed_value=frame.features.get("affect", "") or self._object_surface(graph, frame),
                transmutation_kind="reported",
                persistence_policy="session_state",
                temporal_scope="session",
            )

        if frame.frame_type == "safety_candidate":
            return self._frame(
                frame,
                target_ref="conversation:safety",
                state_family="risk",
                dimension="safety",
                proposed_value="candidate",
                transmutation_kind="inferred",
                authority="policy_authorized",
                persistence_policy="ephemeral",
            )

        return None

    @staticmethod
    def _frame(
        source: OperationalMeaningFrame,
        *,
        target_ref: str,
        state_family: str,
        dimension: str,
        prior_value: Any | None = None,
        proposed_value: Any | None = None,
        direction: str = "set",
        transmutation_kind: str = "observed",
        authority: str = "user_asserted",
        persistence_policy: str = "session_state",
        temporal_scope: str = "current_turn",
    ) -> StateTransmutationFrame:
        return StateTransmutationFrame(
            transmutation_id=f"stm_{uuid.uuid4().hex[:12]}",
            source_frame_id=source.frame_id,
            target_ref=target_ref,
            state_family=state_family,
            dimension=dimension,
            prior_value=prior_value,
            proposed_value=proposed_value,
            direction=direction,
            transmutation_kind=transmutation_kind,
            authority=authority,
            persistence_policy=persistence_policy,
            temporal_scope=temporal_scope,
            source_refs=list(source.source_refs),
            evidence_refs=list(source.evidence_refs),
            confidence=source.confidence,
            features=dict(source.features),
        )

    @staticmethod
    def _object_surface(graph: Any, frame: OperationalMeaningFrame) -> str:
        atom = getattr(graph, "atoms", {}).get(frame.object_atom_id)
        return getattr(atom, "surface", "") or getattr(atom, "key", "") if atom is not None else ""
