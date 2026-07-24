"""Discourse, common-ground and event re-abstraction contracts for v3.5.1."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..csir.authority_v351 import AuthoritySnapshotV351
from ..csir.model import CSIRGraph, ExactAuthorityPin
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
class EventAuthority:
    definition_pin: ExactAuthorityPin
    participant_port_pins: tuple[ExactAuthorityPin, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscourseAuthorityMap:
    authorities: tuple[DiscourseActAuthority, ...] = ()
    event_authorities: tuple[EventAuthority, ...] = ()

    def __post_init__(self) -> None:
        keys = tuple(item.definition_pin.key for item in self.authorities)
        if len(keys) != len(set(keys)):
            raise ValueError("discourse authority definitions must be unique")
        event_keys = tuple(item.definition_pin.key for item in self.event_authorities)
        if len(event_keys) != len(set(event_keys)):
            raise ValueError("event authority definitions must be unique")

    @property
    def by_definition(self):
        return {item.definition_pin.key: item for item in self.authorities}

    @property
    def events_by_definition(self):
        return {item.definition_pin.key: item for item in self.event_authorities}

    def validate(self, snapshot: AuthoritySnapshotV351) -> None:
        for item in self.authorities:
            definition = snapshot.require_definition(item.definition_pin)
            formal = {port.port_pin.key for port in definition.formal_ports}
            for pin in (item.content_port_pin, item.target_port_pin, item.replacement_port_pin):
                if pin is not None:
                    snapshot.require_known_pin(pin)
                    if pin.key not in formal:
                        raise ValueError("discourse authority port is not formal to its exact definition")
        for item in self.event_authorities:
            definition = snapshot.require_definition(item.definition_pin)
            formal = {port.port_pin.key for port in definition.formal_ports}
            for pin in item.participant_port_pins:
                snapshot.require_known_pin(pin)
                if pin.key not in formal:
                    raise ValueError("event participant port is not formal to its exact definition")


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
class EventOccurrenceV351:
    event_ref: str
    graph: CSIRGraph
    definition_pin: ExactAuthorityPin
    context_ref: str
    participant_refs: tuple[tuple[ExactAuthorityPin, str], ...]
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    support: float

    def __post_init__(self) -> None:
        if not self.event_ref or not self.context_ref:
            raise ValueError("event occurrence requires identity and context")
        if not 0.0 <= self.support <= 1.0:
            raise ValueError("event occurrence support must be in [0,1]")
        ports = tuple(pin.key for pin, _ in self.participant_refs)
        if len(ports) != len(set(ports)):
            raise ValueError("event occurrence participant ports must be unique")


@dataclass(frozen=True, slots=True)
class DiscourseStructureBatch:
    batch_ref: str
    substrate: GroundedSemanticSubstrate
    acts: tuple[DiscourseAct, ...]
    events: tuple[EventOccurrenceV351, ...] = ()
    open_questions: tuple[OpenQuestionMemory, ...] = ()
    clarification_targets: tuple[ClarificationMemory, ...] = ()
    common_ground_proposals: tuple[CommonGroundEntry, ...] = ()
    frontier_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


__all__ = [
    "DiscourseAct", "DiscourseActAuthority", "DiscourseActKind", "DiscourseAuthorityMap",
    "DiscourseStructureBatch", "EventAuthority", "EventOccurrenceV351",
]
