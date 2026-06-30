from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .permission import Permission


class ClaimStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    RETRACTED = "retracted"


@dataclass
class Claim:
    id: str
    subject_entity_id: str
    predicate: str
    predicate_model_id: str | None = None
    object_entity_id: str | None = None
    object_value: str | int | float | bool | None = None
    qualifiers: dict[str, str | int | float | bool | None] = field(default_factory=dict)
    evidence_signal_ids: list[str] = field(default_factory=list)
    source_id: str = ""
    domain: str = ""
    confidence: float = 0.5
    confidence_log_odds: float = 0.0
    trust: float = 0.5
    salience: float = 0.3
    status: ClaimStatus = ClaimStatus.ACTIVE
    supersedes_claim_id: str | None = None
    frame_id: str | None = None
    valid_from: float | None = None
    valid_until: float | None = None
    observed_at: float = 0.0
    updated_at: float = 0.0
    permission: Permission | None = None
    version: str = "cemm.claim.v1"
