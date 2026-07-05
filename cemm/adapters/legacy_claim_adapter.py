"""LegacyClaimAdapter — materialize accepted semantic operations into claim store rows.

Claims become a derived view of semantic memory, not the source of truth.
The adapter reads accepted graph patch operations and produces legacy Claim
objects for backward compatibility.
"""

from __future__ import annotations
from typing import Any
from ..types.claim import Claim, ClaimStatus
from ..types.graph_patch import GraphPatch, PatchOperation
from ..learning.patch_validator import PatchValidationResult


class LegacyClaimAdapter:
    """Materializes accepted semantic operations into legacy Claim store rows.

    This is the ONLY code path that should produce claims from semantic memory.
    Direct claim writes from operators bypassing this adapter are architecture
    violations.
    """

    def __init__(self, store: Any | None = None) -> None:
        self._store = store
        self._claim_count = 0

    def materialize(
        self,
        patch: GraphPatch,
        validation: PatchValidationResult,
    ) -> list[Claim]:
        """Convert accepted patch operations into Claim objects.

        Only operations with status "accepted" are materialized.
        Returns list of Claim objects for optional legacy store write.
        """
        if validation.status != "accepted":
            return []

        claims: list[Claim] = []
        for op in patch.operations:
            if self._should_materialize(op):
                claim = self._operation_to_claim(op, patch)
                if claim is not None:
                    claims.append(claim)

        return claims

    def _should_materialize(self, op: PatchOperation) -> bool:
        """Check if an operation should produce a legacy claim."""
        materializable = {
            "upsert_relation_candidate",
            "upsert_concept_candidate",
            "observe_predicate_schema",
        }
        return op.operation in materializable and bool(op.fields)

    def _operation_to_claim(
        self,
        op: PatchOperation,
        patch: GraphPatch,
    ) -> Claim | None:
        """Convert a single accepted operation to a Claim."""
        import time
        import uuid

        fields = op.fields or {}
        subject = fields.get("subject", "") or fields.get("subject_entity_id", "")
        predicate = fields.get("predicate", "")
        object_value = fields.get("object_value", "")
        object_entity_id = fields.get("object_entity_id", "")
        domain = fields.get("domain", "general")
        confidence = op.confidence or patch.confidence

        if not subject or not predicate:
            return None

        now = time.time()
        claim = Claim(
            id=uuid.uuid4().hex[:16],
            subject_entity_id=subject,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=object_entity_id,
            evidence_signal_ids=list(patch.evidence_refs),
            source_id=fields.get("source_id", ""),
            domain=domain,
            confidence=confidence,
            trust=op.confidence or 0.5,
            salience=0.5,
            status=ClaimStatus.ACTIVE,
            observed_at=now,
            updated_at=now,
        )
        return claim

    def materialize_and_store(
        self,
        patch: GraphPatch,
        validation: PatchValidationResult,
    ) -> list[Claim]:
        """Materialize and write to legacy claim store (if store available)."""
        claims = self.materialize(patch, validation)
        if self._store is not None and claims:
            for claim in claims:
                self._store.claims.put(claim)
                self._claim_count += 1
        return claims

    @property
    def total_materialized(self) -> int:
        return self._claim_count
