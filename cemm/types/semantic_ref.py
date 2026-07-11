from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class SemanticRefKind(str, Enum):
    """Canonical kinds of semantic references."""
    SIGNAL = "signal"
    SPAN = "span"
    GROUP = "group"
    BRANCH = "branch"
    ENTITY = "entity"
    CONCEPT = "concept"
    PREDICATE = "predicate"
    OPERATOR = "operator"
    PORT = "port"
    STATE = "state"
    STATE_FAMILY = "state_family"
    STATE_DIMENSION = "state_dimension"
    RELATION = "relation"
    RELATION_FAMILY = "relation_family"
    SOURCE = "source"
    PERMISSION = "permission"
    TIME = "time"
    PLACE = "place"
    MODALITY = "modality"
    GAP = "gap"
    EPISODE = "episode"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    CONTRACT = "contract"
    OBLIGATION = "obligation"
    FRAME = "frame"
    ARTIFACT = "artifact"
    RESPONSE = "response"
    OUTPUT_ACT = "output_act"
    LEARNING_OBSERVATION = "learning_observation"
    ROLE = "role"
    SCOPE = "scope"
    CONTEXT_SIGNATURE = "context_signature"
    PROVENANCE = "provenance"
    ACTION = "action"
    QUERY = "query"
    WRITE = "write"
    PATCH = "patch"
    LEDGER_ENTRY = "ledger_entry"


@dataclass(frozen=True, slots=True)
class SemanticRef:
    """A typed reference to a semantic artifact."""
    kind: SemanticRefKind
    id: str
    label: str = ""

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.id}"

    def __repr__(self) -> str:
        return f"SemanticRef({self.kind.value}, {self.id})"

    @classmethod
    def from_string(cls, ref: str) -> "SemanticRef":
        kind_str, _, id_str = ref.partition(":")
        return cls(kind=SemanticRefKind(kind_str), id=id_str)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "id": self.id, "label": self.label}


@dataclass(frozen=True, slots=True)
class RoleRef:
    """A typed role reference — may be resolved or unresolved."""
    role_kind: str
    resolved_entity: SemanticRef | None = None
    is_placeholder: bool = False
    confidence: float = 0.5
    provenance_ref: SemanticRef | None = None

    def is_resolved(self) -> bool:
        return self.resolved_entity is not None and not self.is_placeholder

    def as_ref(self) -> SemanticRef:
        if self.resolved_entity is not None:
            return self.resolved_entity
        return SemanticRef(kind=SemanticRefKind.ROLE, id=f"placeholder:{self.role_kind}")
