from __future__ import annotations
from ..types.claim import Claim, ClaimStatus
from ..types.context_kernel import ContextKernel
from ..store.claim_store import ClaimStore


class FrameEngine:
    def __init__(self, claim_store: ClaimStore) -> None:
        self._claim_store = claim_store

    def apply_frame_rules(self, kernel: ContextKernel) -> list[str]:
        invalidated: list[str] = []
        active_claims = kernel.world.active_claim_ids
        now = kernel.time.now
        for claim_id in active_claims:
            claim = self._claim_store.get(claim_id)
            if claim is None:
                continue
            if claim.status != ClaimStatus.ACTIVE:
                invalidated.append(claim_id)
                continue
            if claim.valid_from is not None and now < claim.valid_from:
                invalidated.append(claim_id)
                continue
            if claim.valid_until is not None and now > claim.valid_until:
                invalidated.append(claim_id)
                continue
        for cid in invalidated:
            if cid in kernel.world.active_claim_ids:
                kernel.world.active_claim_ids.remove(cid)
            if cid in kernel.conversation.active_claim_ids:
                kernel.conversation.active_claim_ids.remove(cid)
            if cid in kernel.memory.working_claim_ids:
                kernel.memory.working_claim_ids.remove(cid)
        return invalidated

    def is_valid(self, claim: Claim, kernel: ContextKernel) -> bool:
        """Return True if the claim is valid under the current kernel frame/time."""
        now = kernel.time.now
        if claim.status != ClaimStatus.ACTIVE:
            return False
        if claim.valid_from is not None and now < claim.valid_from:
            return False
        if claim.valid_until is not None and now > claim.valid_until:
            return False
        return True

    def filter_valid(self, claims: list[Claim], kernel: ContextKernel) -> list[Claim]:
        return [c for c in claims if self.is_valid(c, kernel)]

    def check_supersession(self, new_claim: Claim, kernel: ContextKernel) -> list[Claim]:
        existing = self._claim_store.find_contradictions(
            new_claim.subject_entity_id, new_claim.predicate
        )
        superseded: list[Claim] = []
        for e in existing:
            if e.id == new_claim.id:
                continue
            if e.object_value == new_claim.object_value and e.object_entity_id == new_claim.object_entity_id:
                continue
            superseded.append(e)
        return superseded
