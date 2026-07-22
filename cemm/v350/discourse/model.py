"""Phase-11 discourse/common-ground ownership contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..csir.authority_v351 import AuthoritySnapshotV351
from ..csir.model import ExactAuthorityPin
from ..grounded.model import GroundedSemanticSubstrate
from ..conversation.session_memory import ClarificationMemory, CommonGroundEntry, OpenQuestionMemory


class DiscourseActKind(str, Enum):
    ASSERTION = "assertion"
    QUERY = "query"
    CORRECTION = "correction"
    RETRACTION = "retraction"
    DEFINITION = "definition"
    GREETING = "greeting"
    REQUEST = "request"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class DiscourseActAuthority:
    definition_pin: ExactAuthorityPin
    act_kind: DiscourseActKind
    content_port_pin: ExactAuthorityPin | None = None
    target_port_pin: ExactAuthorityPin | None = None
    replacement_port_pin: ExactAuthorityPin | None = None


@dataclass(frozen=True, slots=True)
class DiscourseAuthorityMap:
    authorities: tuple[DiscourseActAuthority, ...] = ()

    def __post_init__(self) -> None:
        keys = tuple(item.definition_pin.key for item in self.authorities)
        if len(keys) != len(set(keys)):
            raise ValueError("discourse authority definitions must be unique")

    @property
    def by_definition(self):
        return {item.definition_pin.key: item for item in self.authorities}

    def validate(self, snapshot: AuthoritySnapshotV351) -> None:
        for item in self.authorities:
            snapshot.require_definition(item.definition_pin)
            for pin in (item.content_port_pin, item.target_port_pin, item.replacement_port_pin):
                if pin is not None:
                    snapshot.require_known_pin(pin)


@dataclass(frozen=True, slots=True)
class DiscourseAct:
    act_ref: str
    act_kind: DiscourseActKind
    semantic_ref: str
    speaker_ref: str
    audience_refs: tuple[str, ...]
    context_ref: str
    evidence_refs: tuple[str, ...]
    authority_pin: ExactAuthorityPin | None = None
    target_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscourseStructureBatch:
    batch_ref: str
    substrate: GroundedSemanticSubstrate
    acts: tuple[DiscourseAct, ...]
    open_questions: tuple[OpenQuestionMemory, ...] = ()
    clarification_targets: tuple[ClarificationMemory, ...] = ()
    common_ground_proposals: tuple[CommonGroundEntry, ...] = ()
    frontier_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


__all__ = [
    "DiscourseAct", "DiscourseActAuthority", "DiscourseActKind",
    "DiscourseAuthorityMap", "DiscourseStructureBatch",
]
