"""Session and cycle-local grounding artifacts for CEMM v1.

These objects carry transport/session facts into cognition without turning
language forms into participant identity or persisting transient cycle state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from cemm.model import now, stable


@dataclass(frozen=True)
class ParticipantFrame:
    """Transport-grounded participant roles for one semantic pass."""

    self_ref: str
    speaker_ref: str
    addressee_ref: str
    audience_refs: tuple[str, ...] = ()
    conversation_ref: str = "conversation:default"
    source: str = "chat"
    channel: str = "text"

    def resolve_requirement(self, features: Mapping[str, Any]) -> str | None:
        """Resolve language participant requirements against this frame.

        Language contributes person/role requirements.  It never creates the
        identity of speaker/addressee by itself.
        """
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
    """Stable session/transport bindings; no semantic authority is created here."""

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
    """Cycle-local runtime facts, deliberately not ordinary semantic self-state."""

    self_ref: str
    authority_generation: int
    read_generation: int
    process_available: bool = True


@dataclass
class CycleWorkspace:
    """Transient artifact owner for one cycle/pass."""

    artifacts: dict[str, Any] = field(default_factory=dict)

    def put(self, name: str, value: Any) -> Any:
        self.artifacts[name] = value
        return value

    def get(self, name: str, default: Any = None) -> Any:
        return self.artifacts.get(name, default)


@dataclass
class CycleState:
    cycle_ref: str
    pass_ref: str
    authority_generation: int
    read_generation: int
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
            "read_generation": self.read_generation,
            "participant_frame": self.participant_frame.as_dict(),
        }
