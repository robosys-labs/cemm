from __future__ import annotations
from ..types.claim import Claim
from ..types.temporal_relation import TemporalRelation, TemporalRelationClaim
from ..store.store import Store
import time

def derive_temporal_relations(claim: Claim, store: Store) -> list[TemporalRelationClaim]:
    if claim.valid_from is None and claim.valid_until is None:
        return []
    recent = store.claims.find_active(5)
    relations: list[TemporalRelationClaim] = []
    now = time.time()
    cf = claim.valid_from or now
    cu = claim.valid_until or now
    for other in recent:
        if other.id == claim.id:
            continue
        of = other.valid_from or now
        ou = other.valid_until or now
        if cu <= of:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id, object_claim_id=other.id,
                relation=TemporalRelation.PRECEDES, confidence=0.9,
            ))
        elif cf >= ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id, object_claim_id=other.id,
                relation=TemporalRelation.PRECEDES, confidence=0.9,
            ))
        elif cf >= of and cu <= ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id, object_claim_id=other.id,
                relation=TemporalRelation.DURING, confidence=0.8,
            ))
        elif cf <= of and cu >= ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id, object_claim_id=other.id,
                relation=TemporalRelation.CONTAINS, confidence=0.8,
            ))
        elif cf < ou and cu > of:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id, object_claim_id=other.id,
                relation=TemporalRelation.OVERLAPS, confidence=0.7,
            ))
        elif cu == of or cf == ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id, object_claim_id=other.id,
                relation=TemporalRelation.MEETS, confidence=0.9,
            ))
    return relations
