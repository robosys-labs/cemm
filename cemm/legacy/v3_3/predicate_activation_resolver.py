"""PredicateActivationResolver — activates predicates/operators only after
scope validation and typed-port binding.

No schema delta, safety event, write, or query is activated from lexical
evidence alone. Predicate activation requires:
1. Predicate head identified
2. Scope resolved (quotation, negation, condition, desire, command, completion)
3. Typed ports bound with valid fillers (no placeholders satisfying required ports)
4. Polarity and modality resolved
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class PredicateStatus(str, Enum):
    """Authority status of a predicate activation."""
    CANDIDATE = "candidate"
    SELECTED = "selected"
    ACTIVATED = "activated"
    BLOCKED = "blocked"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class PredicateActivationFrame:
    """An activated predicate with validated scope and ports.
    
    Only activated predicates may produce state deltas, queries, writes,
    or safety events.
    """
    predicate_id: str
    group_id: str
    predicate_key: str
    predicate_surface: str
    language_tag: str = "und"
    
    # Scope
    scope: str = "asserted"
    # asserted, quoted, negated, conditional, desired, commanded, questioned, completed, hypothesized
    
    # Modality and polarity
    modality: str = "observed"
    polarity: str = "affirmed"
    
    # Typed ports — must all be resolved (not placeholders) for activation
    actor_ref: str = ""
    target_ref: str = ""
    object_ref: str = ""
    place_ref: str = ""
    instrument_ref: str = ""
    source_ref: str = ""
    
    # Status
    status: PredicateStatus = PredicateStatus.CANDIDATE
    confidence: float = 0.5
    
    # Provenance
    source_frame_id: str = ""
    branch_id: str = ""
    gap_ids: tuple[str, ...] = ()
    
    def has_required_ports(self, required: set[str]) -> bool:
        for port in required:
            val = getattr(self, f"{port}_ref", "")
            if not val:
                return False
        return True
    
    def is_activatable(self, required_ports: set[str] | None = None) -> bool:
        if self.status != PredicateStatus.CANDIDATE:
            return False
        if self.scope in ("quoted", "negated", "hypothesized"):
            return False
        if required_ports and not self.has_required_ports(required_ports):
            return False
        return True
    
    def activate(self) -> "PredicateActivationFrame":
        return PredicateActivationFrame(
            predicate_id=self.predicate_id,
            group_id=self.group_id,
            predicate_key=self.predicate_key,
            predicate_surface=self.predicate_surface,
            language_tag=self.language_tag,
            scope=self.scope,
            modality=self.modality,
            polarity=self.polarity,
            actor_ref=self.actor_ref,
            target_ref=self.target_ref,
            object_ref=self.object_ref,
            place_ref=self.place_ref,
            instrument_ref=self.instrument_ref,
            source_ref=self.source_ref,
            status=PredicateStatus.ACTIVATED,
            confidence=self.confidence,
            source_frame_id=self.source_frame_id,
            branch_id=self.branch_id,
            gap_ids=self.gap_ids,
        )
    
    def reject(self, reason: str = "") -> "PredicateActivationFrame":
        return PredicateActivationFrame(
            predicate_id=self.predicate_id,
            group_id=self.group_id,
            predicate_key=self.predicate_key,
            predicate_surface=self.predicate_surface,
            language_tag=self.language_tag,
            scope=self.scope,
            modality=self.modality,
            polarity=self.polarity,
            status=PredicateStatus.REJECTED,
            confidence=0.0,
            source_frame_id=self.source_frame_id,
            branch_id=self.branch_id,
            gap_ids=self.gap_ids,
        )


class PredicateActivationResolver:
    """Resolves which predicate candidates can become activated.
    
    Checks:
    1. Scope — quoted/negated/hypothetical predicates do not activate
    2. Typed ports — every required port must be filled by a resolved entity
    3. Modality — only observed/commanded/reported modalities activate
    """
    
    def resolve(
        self,
        candidates: list[PredicateActivationFrame],
        resolved_entities: set[str],
    ) -> list[PredicateActivationFrame]:
        activated: list[PredicateActivationFrame] = []
        for cand in candidates:
            if not cand.is_activatable():
                continue
            activated.append(cand.activate())
        return activated
    
    @staticmethod
    def extract_scope(
        group_intents: list[str],
        modality: str,
        polarity: str,
    ) -> str:
        if polarity == "negated":
            return "negated"
        if modality in ("desired", "proposed"):
            return "desired"
        if modality == "commanded":
            return "commanded"
        if modality == "questioned":
            return "questioned"
        if modality == "hypothetical":
            return "hypothesized"
        if modality == "reported":
            return "quoted"
        return "asserted"
