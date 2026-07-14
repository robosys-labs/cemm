"""WriteContractBuilder — build write contracts from writable meaning frames.

Only writable OperationalMeaningFrames may produce write contracts.
This ensures feedback, dismissal, social acts, and queries never
produce durable patch candidates.
"""

from __future__ import annotations

from typing import Any

from ...types.obligation_contract import WriteContract
from ...types.operational_meaning import (
    OperationalMeaningFrame,
    is_writable_frame,
)


class WriteContractBuilder:
    """Build WriteContract only from writable operational meaning frames."""

    def build(
        self,
        frame: OperationalMeaningFrame,
        graph: Any | None = None,
    ) -> WriteContract | None:
        if not is_writable_frame(frame):
            return None

        write_kind_map = {
            "profile_assertion": "profile_upsert",
            "concept_definition_teaching": "relation_upsert",
            "world_fact_claim": "relation_upsert",
            "correction": "correction_apply",
            "memory_command": "memory_command",
        }
        write_kind = write_kind_map.get(frame.frame_type, "relation_upsert")

        required_features: list[str] = []
        if frame.dimension:
            required_features.append(frame.dimension)
        prop_dim = frame.features.get("property_dimension", "")
        if prop_dim and prop_dim not in required_features:
            required_features.append(prop_dim)

        allowed_targets = self._allowed_patch_targets(frame)

        return WriteContract(
            write_kind=write_kind,
            target=frame.target_scope,
            persistence_policy=frame.persistence_policy,
            allowed_patch_targets=allowed_targets,
            required_features=required_features,
            required_evidence_refs=list(frame.evidence_refs),
            permission_scope=frame.target_scope,
            commit_policy="commit_if_valid",
            features=dict(frame.features),
        )

    @staticmethod
    def _allowed_patch_targets(frame: OperationalMeaningFrame) -> list[str]:
        if frame.frame_type in ("profile_assertion", "concept_definition_teaching", "world_fact_claim", "memory_command", "command"):
            return ["concept_lattice"]
        if frame.frame_type == "correction":
            return ["concept_lattice"]
        return []
