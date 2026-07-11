from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from .provenance import ProvenanceScope
from .knowledge_strength import PromotionState


@dataclass(frozen=True, slots=True)
class LearningContract:
    """The sole authority for creating provisional bindings, evidence events,
    revision operations, and durable learning patches.
    
    No learning promotion occurs without an authorized LearningContract.
    """
    contract_id: str
    episode_id: str = ""
    target_hypothesis_ids: tuple[str, ...] = ()
    
    # What operations this contract permits
    permitted_operations: tuple[str, ...] = (
        "propose_binding",
        "record_evidence",
        "activate_provisional",
        "promote",
        "restrict",
        "supersede",
        "retire",
    )
    
    # Scope constraints
    activation_scope: str = "session"
    promotion_ceiling: PromotionState = PromotionState.SESSION_PROVISIONAL
    
    # Evidence requirements
    required_evidence: tuple[str, ...] = ()
    minimum_confidence: float = 0.3
    
    # Security constraints
    prohibited_authorities: tuple[str, ...] = (
        "tool_execution",
        "safety_exception",
        "global_permission",
        "kernel_primitive_creation",
    )
    
    # Provenance
    source_refs: tuple[str, ...] = ()
    provenance_ref: str = ""
    created_at: float = 0.0
    
    @property
    def can_promote_to_durable(self) -> bool:
        return PromotionState(self.promotion_ceiling) in {
            PromotionState.USER_SCOPED_ACTIVE,
            PromotionState.DOMAIN_SCOPED_ACTIVE,
            PromotionState.LANGUAGE_SCOPED_ACTIVE,
            PromotionState.STABLE,
        }
    
    def permits_operation(self, operation: str) -> bool:
        return operation in self.permitted_operations
    
    def prohibits_authority(self, authority: str) -> bool:
        return authority in self.prohibited_authorities
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "episode_id": self.episode_id,
            "target_hypothesis_ids": list(self.target_hypothesis_ids),
            "permitted_operations": list(self.permitted_operations),
            "activation_scope": self.activation_scope,
            "promotion_ceiling": self.promotion_ceiling.value,
            "required_evidence": list(self.required_evidence),
            "minimum_confidence": self.minimum_confidence,
            "prohibited_authorities": list(self.prohibited_authorities),
        }
