from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .semantic_ref import SemanticRef


class ProvenanceScope(str, Enum):
    SESSION = "session"
    USER = "user"
    DOMAIN = "domain"
    LANGUAGE = "language"
    DIALECT = "dialect"
    GLOBAL = "global"


@dataclass(frozen=True, slots=True)
class ProvenanceEnvelope:
    source_id: str
    source_trust: float = 0.5
    confidence: float = 0.5
    observed_at: float = 0.0
    language_tag: str = "und"
    scope: str = "session"
    signal_id: str = ""
    context_id: str = ""
    turn_index: int = 0
    independence_key: str = ""
    refs: tuple[SemanticRef, ...] = ()

    def merge(self, other: ProvenanceEnvelope) -> ProvenanceEnvelope:
        if self.source_trust >= other.source_trust:
            return self
        return other

    def with_refs(self, *refs: SemanticRef) -> ProvenanceEnvelope:
        return ProvenanceEnvelope(
            source_id=self.source_id,
            source_trust=self.source_trust,
            confidence=self.confidence,
            observed_at=self.observed_at,
            language_tag=self.language_tag,
            scope=self.scope,
            signal_id=self.signal_id,
            context_id=self.context_id,
            turn_index=self.turn_index,
            independence_key=self.independence_key,
            refs=refs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_trust": self.source_trust,
            "confidence": self.confidence,
            "observed_at": self.observed_at,
            "language_tag": self.language_tag,
            "scope": self.scope,
            "signal_id": self.signal_id,
            "context_id": self.context_id,
            "turn_index": self.turn_index,
            "independence_key": self.independence_key,
        }
