"""Session and cycle-local grounding artifacts for CEMM v1.

Transport/session facts orient cognition without becoming lexical identity or
ordinary semantic self/world state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from cemm.model import now, stable


@dataclass(frozen=True)
class ParticipantFrame:
    self_ref: str
    speaker_ref: str
    addressee_ref: str
    audience_refs: tuple[str, ...] = ()
    conversation_ref: str = "conversation:default"
    source: str = "chat"
    channel: str = "text"

    def resolve_requirement(self, features: Mapping[str, Any]) -> str | None:
        role = features.get("participant_role")
        person = features.get("person")
        if role == "speaker" or (not role and person == "first"):
            return self.speaker_ref
        if role == "addressee" or (not role and person == "second"):
            return self.addressee_ref
        if role == "self":
            return self.self_ref
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "self_ref": self.self_ref,
            "speaker_ref": self.speaker_ref,
            "addressee_ref": self.addressee_ref,
            "audience_refs": list(self.audience_refs),
            "conversation_ref": self.conversation_ref,
            "source": self.source,
            "channel": self.channel,
        }


@dataclass(frozen=True)
class SessionContext:
    session_ref: str
    conversation_ref: str
    self_ref: str
    default_input_speaker_ref: str
    default_input_addressee_ref: str
    audience_refs: tuple[str, ...] = ()
    permission_scope: str | None = None

    @classmethod
    def default(cls, self_ref: str, user_ref: str = "participant:user") -> "SessionContext":
        return cls(
            session_ref=stable("session", self_ref, user_ref, "default"),
            conversation_ref=stable("conversation", self_ref, user_ref, "default"),
            self_ref=self_ref,
            default_input_speaker_ref=user_ref,
            default_input_addressee_ref=self_ref,
        )

    def input_frame(
        self,
        *,
        speaker_ref: str | None = None,
        addressee_ref: str | None = None,
        audience_refs: tuple[str, ...] | None = None,
        source: str = "user",
        channel: str = "text",
    ) -> ParticipantFrame:
        return ParticipantFrame(
            self_ref=self.self_ref,
            speaker_ref=speaker_ref or self.default_input_speaker_ref,
            addressee_ref=addressee_ref or self.default_input_addressee_ref,
            audience_refs=self.audience_refs if audience_refs is None else audience_refs,
            conversation_ref=self.conversation_ref,
            source=source,
            channel=channel,
        )

    def output_frame(
        self,
        *,
        addressee_ref: str | None = None,
        audience_refs: tuple[str, ...] | None = None,
        source: str = "system",
        channel: str = "text",
    ) -> ParticipantFrame:
        return ParticipantFrame(
            self_ref=self.self_ref,
            speaker_ref=self.self_ref,
            addressee_ref=addressee_ref or self.default_input_speaker_ref,
            audience_refs=self.audience_refs if audience_refs is None else audience_refs,
            conversation_ref=self.conversation_ref,
            source=source,
            channel=channel,
        )


@dataclass(frozen=True)
class ContextStack:
    refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemporalFrame:
    observed_at: str = field(default_factory=now)
    reference_time: str | None = None


@dataclass(frozen=True)
class SelfRuntimeView:
    """Cycle-local provider evidence, not a vocabulary-dependent self label."""

    self_ref: str
    authority_generation: int
    world_revision: int
    discourse_revision: int
    observation_revision: int
    process_available: bool = True
    language_realizer_support: float = 1.0
    semantic_runtime_support: float = 1.0
    critical_blockers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "self_ref": self.self_ref,
            "authority_generation": self.authority_generation,
            "world_revision": self.world_revision,
            "discourse_revision": self.discourse_revision,
            "observation_revision": self.observation_revision,
            "process_available": self.process_available,
            "language_realizer_support": self.language_realizer_support,
            "semantic_runtime_support": self.semantic_runtime_support,
            "critical_blockers": list(self.critical_blockers),
        }


@dataclass
class CycleWorkspace:
    artifacts: dict[str, Any] = field(default_factory=dict)

    def put(self, name: str, value: Any) -> Any:
        self.artifacts[name] = value
        return value

    def append(self, name: str, value: Any) -> Any:
        self.artifacts.setdefault(name, []).append(value)
        return value

    def get(self, name: str, default: Any = None) -> Any:
        return self.artifacts.get(name, default)


@dataclass
class CycleState:
    cycle_ref: str
    pass_ref: str
    authority_generation: int
    world_revision: int
    discourse_revision: int
    observation_revision: int
    participant_frame: ParticipantFrame
    context_stack: ContextStack
    temporal_frame: TemporalFrame
    self_runtime_view: SelfRuntimeView
    workspace: CycleWorkspace = field(default_factory=CycleWorkspace)

    def trace(self) -> dict[str, Any]:
        return {
            "cycle_ref": self.cycle_ref,
            "pass_ref": self.pass_ref,
            "authority_generation": self.authority_generation,
            "world_revision": self.world_revision,
            "discourse_revision": self.discourse_revision,
            "observation_revision": self.observation_revision,
            "participant_frame": self.participant_frame.as_dict(),
            "self_runtime_view": self.self_runtime_view.as_dict(),
        }
