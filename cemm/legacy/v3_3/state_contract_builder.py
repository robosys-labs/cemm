"""StateContractBuilder — builds StateContract from state transmutation frames.

Only authorized state transmutations may alter state occupancy.
The StateContract validates state family, dimension, holder kind,
value/polarity/intensity/scale/units, temporal persistence, and
transmutation authority before allowing application.
"""

from __future__ import annotations

from typing import Any

from ...types.obligation_contract import StateContract
from ...types.state_transmutation import StateTransmutationFrame


class StateContractBuilder:
    """Builds StateContract from state transmutation frames.

    Produces exactly one StateContract per turn when state changes
    are detected. The contract carries full provenance and authorization
    metadata.
    """

    def build(
        self,
        transmutation_frames: list[StateTransmutationFrame],
    ) -> StateContract | None:
        if not transmutation_frames:
            return None

        primary = transmutation_frames[0]
        source_ids = [t.source_frame_id for t in transmutation_frames if hasattr(t, "source_frame_id") and t.source_frame_id]

        return StateContract(
            state_family=getattr(primary, "state_family", ""),
            dimension=getattr(primary, "dimension", ""),
            holder_entity_ref=getattr(primary, "target_ref", ""),
            value=getattr(primary, "proposed_value", None),
            direction=getattr(primary, "direction", "set"),
            modality=getattr(primary, "transmutation_kind", "observed"),
            transmutation_id=getattr(primary, "transmutation_id", ""),
            source_frame_id=source_ids[0] if source_ids else "",
            requires_authorization=True,
            is_applied=False,
            persistence_policy=getattr(primary, "persistence_policy", "session_state"),
            confidence=getattr(primary, "confidence", 0.5),
        )
