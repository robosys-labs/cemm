from __future__ import annotations
import time
import uuid

from ..store.store import Store
from ..types.claim import Claim, ClaimStatus
from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.permission import Permission
from ..kernel.memory_update_planner import MemoryUpdateTask


class ClaimWriter:
    def __init__(self, store: Store) -> None:
        self._store = store

    def write_claim(
        self,
        subject_entity_id: str,
        predicate: str,
        object_value: str | None = None,
        object_entity_id: str | None = None,
        domain: str = "general",
        qualifiers: dict | None = None,
        evidence_signal_ids: list[str] | None = None,
        source_id: str = "",
        permission: Permission | None = None,
        confidence: float = 0.7,
        trust: float = 0.7,
    ) -> tuple[Claim, GraphPatch]:
        now = time.time()
        claim = Claim(
            id=uuid.uuid4().hex[:16],
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=object_entity_id,
            qualifiers=qualifiers or {},
            evidence_signal_ids=evidence_signal_ids or [],
            source_id=source_id,
            domain=domain,
            confidence=confidence,
            trust=trust,
            salience=0.5,
            status=ClaimStatus.ACTIVE,
            observed_at=now,
            updated_at=now,
            permission=permission,
        )
        self._store.claims.put(claim)
        patch = self._build_patch(claim)
        return claim, patch

    def write_batch(
        self,
        tasks: list[MemoryUpdateTask],
        input_signal_id: str,
        source_id: str,
        permission: Permission,
    ) -> tuple[list[Claim], list[GraphPatch]]:
        now = time.time()
        claims: list[Claim] = []
        patches: list[GraphPatch] = []
        for task in tasks:
            if not task.is_valid():
                continue
            claim = Claim(
                id=uuid.uuid4().hex[:16],
                subject_entity_id=task.subject_entity_id,
                predicate=task.predicate,
                object_value=task.object_value,
                object_entity_id=task.object_entity_id,
                qualifiers=task.qualifiers,
                evidence_signal_ids=[input_signal_id],
                source_id=source_id,
                domain=task.domain,
                confidence=task.confidence,
                trust=task.trust,
                salience=0.5,
                status=ClaimStatus.ACTIVE,
                observed_at=now,
                updated_at=now,
                permission=permission,
            )
            self._store.claims.put(claim)
            claims.append(claim)
            patches.append(self._build_patch(claim))
        return claims, patches

    def write_profile(
        self,
        slot: str,
        value: str,
        source_id: str,
        permission: Permission | None = None,
        trust: float = 0.7,
    ) -> tuple[Claim, GraphPatch]:
        claim = self._store.profile.put(
            slot=slot,
            value=value,
            source_id=source_id,
            permission=permission,
            trust=trust,
        )
        patch = self._build_patch(claim)
        return claim, patch

    def _build_patch(
        self,
        claim: Claim,
        operation: str = "custom:upsert_claim",
    ) -> GraphPatch:
        fields = {
            "claim_id": claim.id,
            "subject_entity_id": claim.subject_entity_id,
            "predicate": claim.predicate,
            "object_value": str(claim.object_value) if claim.object_value is not None else "",
            "object_entity_id": claim.object_entity_id or "",
            "domain": claim.domain,
            "confidence": claim.confidence,
            "trust": claim.trust,
            "source_id": claim.source_id,
        }
        op = PatchOperation(
            operation=operation,
            target_id=claim.id,
            fields=fields,
            confidence=claim.confidence,
            reason=f"claim_write:{claim.predicate}",
        )
        return GraphPatch(
            target="episodic_trace",
            operations=[op],
            source_refs=[claim.source_id] if claim.source_id else [],
            evidence_refs=list(claim.evidence_signal_ids),
            confidence=claim.confidence,
            reason=f"claim_write:{claim.subject_entity_id}:{claim.predicate}",
        )
