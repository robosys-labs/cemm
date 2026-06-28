from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class TemporalRelation(str, Enum):
    PRECEDES = "temporally_precedes"
    OVERLAPS = "temporally_overlaps"
    DURING = "temporally_during"
    CONTAINS = "temporally_contains"
    MEETS = "temporally_meets"

@dataclass
class TemporalRelationClaim:
    subject_claim_id: str
    object_claim_id: str
    relation: TemporalRelation
    confidence: float
