"""MemoryPatchCompiler — Store buffer that packages raw claim intent into GraphPatches.

Before any claim reaches durable storage, it must be compiled into a
GraphPatch with proper source, evidence, permission, and operation metadata.
This is the "store buffer" step before the MMU (PatchValidator) gate.
"""

from __future__ import annotations
from typing import Any

from ..types.claim import Claim
from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.context_kernel import ContextKernel


class MemoryPatchCompiler:
    """Packages raw claim intent into a structured GraphPatch for validation."""

    def compile(
        self,
        subject_entity_id: str,
        predicate: str,
        object_value: str | None = None,
        object_entity_id: str | None = None,
        domain: str = "general",
        qualifiers: dict[str, Any] | None = None,
        evidence_signal_ids: list[str] | None = None,
        source_id: str = "",
        permission: Any | None = None,
        confidence: float = 0.7,
        trust: float = 0.7,
        kernel: ContextKernel | None = None,
    ) -> GraphPatch:
        """Compile raw claim intent into a GraphPatch for the validation barrier.

        All metadata (source, evidence, permission, operations) is assembled
        here so the PatchValidator has a complete picture before any store write.
        """
        fields: dict[str, Any] = {
            "subject_entity_id": subject_entity_id,
            "predicate": predicate,
            "object_value": str(object_value) if object_value is not None else "",
            "object_entity_id": object_entity_id or "",
            "domain": domain,
            "qualifiers": qualifiers or {},
            "trust": trust,
        }
        op = PatchOperation(
            operation="custom:upsert_claim",
            target_id=f"{subject_entity_id}:{predicate}",
            fields=fields,
            confidence=confidence,
            reason=f"compile_claim:{predicate}",
        )
        source_refs: list[str] = [source_id] if source_id else []
        if kernel is not None and kernel.id:
            source_refs.append(f"kernel:{kernel.id}")

        return GraphPatch(
            target="episodic_trace",
            operations=[op],
            source_refs=source_refs,
            evidence_refs=list(evidence_signal_ids) if evidence_signal_ids else [],
            confidence=confidence,
            reason=f"compile:{subject_entity_id}:{predicate}",
        )

    def compile_from_claim(
        self,
        claim: Claim,
        kernel: ContextKernel | None = None,
    ) -> GraphPatch:
        """Compile an already-constructed Claim back into a GraphPatch."""
        op = PatchOperation(
            operation="custom:upsert_claim",
            target_id=claim.id,
            fields={
                "claim_id": claim.id,
                "subject_entity_id": claim.subject_entity_id,
                "predicate": claim.predicate,
                "object_value": str(claim.object_value) if claim.object_value is not None else "",
                "object_entity_id": claim.object_entity_id or "",
                "domain": claim.domain,
                "confidence": claim.confidence,
                "trust": claim.trust,
                "source_id": claim.source_id,
            },
            confidence=claim.confidence,
            reason=f"compile_from_claim:{claim.predicate}",
        )
        source_refs: list[str] = [claim.source_id] if claim.source_id else []
        if kernel is not None and kernel.id:
            source_refs.append(f"kernel:{kernel.id}")

        return GraphPatch(
            target="episodic_trace",
            operations=[op],
            source_refs=source_refs,
            evidence_refs=list(claim.evidence_signal_ids or []),
            confidence=claim.confidence,
            reason=f"compile_from_claim:{claim.subject_entity_id}:{claim.predicate}",
        )
