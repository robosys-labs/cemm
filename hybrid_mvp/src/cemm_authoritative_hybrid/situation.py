"""Situation Context ABI 1.

A situation is the independently verified, revision-pinned context supplied to
EVALUATE alongside one selected :class:`VerifiedMeaning`.  It records the
source-evidence policy, persistent turn/snapshot lineage and the exact
participants that existed in reviewed authority.  It is never reconstructed
from Program identity or raw surface text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import stable_ref
from .cycle import Orientation, SemanticMode
from .forms import EvidencePacket
from .persistence import RevisionPin
from .proposal_context import ProposalContext

SITUATION_CONTEXT_ABI_VERSION = 1
_MAX_REF_CHARS = 512
_MAX_ITEMS = 512
_EVIDENCE_KINDS = frozenset({"text", "sensor", "operation"})

__all__ = [
    "SITUATION_CONTEXT_ABI_VERSION",
    "SituationInputBundle",
    "SituationContext",
    "SituationContextBuilder",
    "SituationContextVerifier",
]


def _text(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > _MAX_REF_CHARS:
        raise ValueError(f"{name} exceeds {_MAX_REF_CHARS} characters")
    return value


def _optional(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _refs(value: object, name: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be exact tuple")
    if len(value) > _MAX_ITEMS:
        raise ValueError(f"{name} exceeds situation bound")
    checked = tuple(_text(item, f"{name} item") for item in value)
    if nonempty and not checked:
        raise ValueError(f"{name} must be nonempty")
    if len(checked) != len(set(checked)):
        raise ValueError(f"{name} must contain unique refs")
    return checked


def _wire_refs(value: object, name: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be exact list")
    return _refs(tuple(value), name, nonempty=nonempty)


def _pin(value: object) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    if RevisionPin.from_dict(value.as_dict()) != value:
        raise ValueError("revision_pin is non-canonical")
    return value


_EPISTEMIC_SCOPE_BY_MODE: Mapping[SemanticMode, str] = {
    SemanticMode.OBSERVE: "epistemic_scope:observed",
    SemanticMode.QUERY: "epistemic_scope:query",
    SemanticMode.REQUEST: "epistemic_scope:requested",
    SemanticMode.SIMULATE: "epistemic_scope:simulated",
}


@dataclass(frozen=True)
class SituationInputBundle:
    """Exact transient inputs used to reconstruct one SituationContext.

    The bundle contains no Program and no raw-text dispatch state.  It binds the
    immutable evidence packet and the persistent snapshots captured during
    ORIENT so EVALUATE can be independently reconstructed.
    """

    situation_input_ref: str
    evidence: EvidencePacket
    turn_index: int
    session_phase_ref: str
    focus_snapshot_ref: str
    focus_refs: tuple[str, ...]
    obligation_snapshot_ref: str
    obligation_refs: tuple[str, ...]
    permission_snapshot_ref: str
    resource_snapshot_ref: str
    resource_refs: tuple[str, ...]
    adapter_snapshot_ref: str
    adapter_refs: tuple[str, ...]
    evidence_policy_refs: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        evidence: EvidencePacket,
        turn_index: int,
        session_phase_ref: str,
        focus_snapshot_ref: str,
        focus_refs: tuple[str, ...],
        obligation_snapshot_ref: str,
        obligation_refs: tuple[str, ...],
        permission_snapshot_ref: str,
        resource_snapshot_ref: str,
        resource_refs: tuple[str, ...],
        adapter_snapshot_ref: str,
        adapter_refs: tuple[str, ...],
        evidence_policy_refs: tuple[str, ...],
    ) -> "SituationInputBundle":
        if type(evidence) is not EvidencePacket:
            raise TypeError("evidence must be exact EvidencePacket")
        if EvidencePacket.from_dict(evidence.as_dict()) != evidence:
            raise ValueError("evidence is non-canonical")
        if type(turn_index) is not int or isinstance(turn_index, bool) or turn_index < 1:
            raise ValueError("turn_index must be a positive exact int")
        values = {
            "evidence": evidence,
            "turn_index": turn_index,
            "session_phase_ref": _text(session_phase_ref, "session_phase_ref"),
            "focus_snapshot_ref": _text(focus_snapshot_ref, "focus_snapshot_ref"),
            "focus_refs": _refs(focus_refs, "focus_refs"),
            "obligation_snapshot_ref": _text(obligation_snapshot_ref, "obligation_snapshot_ref"),
            "obligation_refs": _refs(obligation_refs, "obligation_refs"),
            "permission_snapshot_ref": _text(permission_snapshot_ref, "permission_snapshot_ref"),
            "resource_snapshot_ref": _text(resource_snapshot_ref, "resource_snapshot_ref"),
            "resource_refs": _refs(resource_refs, "resource_refs"),
            "adapter_snapshot_ref": _text(adapter_snapshot_ref, "adapter_snapshot_ref"),
            "adapter_refs": _refs(adapter_refs, "adapter_refs"),
            "evidence_policy_refs": _refs(evidence_policy_refs, "evidence_policy_refs", nonempty=True),
        }
        material = {
            "evidence_packet_ref": evidence.packet_ref,
            "turn_index": turn_index,
            "session_phase_ref": values["session_phase_ref"],
            "focus_snapshot_ref": values["focus_snapshot_ref"],
            "focus_refs": list(values["focus_refs"]),
            "obligation_snapshot_ref": values["obligation_snapshot_ref"],
            "obligation_refs": list(values["obligation_refs"]),
            "permission_snapshot_ref": values["permission_snapshot_ref"],
            "resource_snapshot_ref": values["resource_snapshot_ref"],
            "resource_refs": list(values["resource_refs"]),
            "adapter_snapshot_ref": values["adapter_snapshot_ref"],
            "adapter_refs": list(values["adapter_refs"]),
            "evidence_policy_refs": list(values["evidence_policy_refs"]),
        }
        return cls(stable_ref("situation_input", material), **values)

    def as_kwargs(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence,
            "turn_index": self.turn_index,
            "session_phase_ref": self.session_phase_ref,
            "focus_snapshot_ref": self.focus_snapshot_ref,
            "focus_refs": self.focus_refs,
            "obligation_snapshot_ref": self.obligation_snapshot_ref,
            "obligation_refs": self.obligation_refs,
            "permission_snapshot_ref": self.permission_snapshot_ref,
            "resource_snapshot_ref": self.resource_snapshot_ref,
            "resource_refs": self.resource_refs,
            "adapter_snapshot_ref": self.adapter_snapshot_ref,
            "adapter_refs": self.adapter_refs,
            "evidence_policy_refs": self.evidence_policy_refs,
        }


@dataclass(frozen=True, init=False)
class SituationContext:
    abi_version: int
    situation_ref: str
    orientation_ref: str
    proposal_context_ref: str
    mode: SemanticMode
    session_ref: str
    turn_ref: str
    turn_index: int
    session_phase_ref: str
    participant_refs: tuple[str, ...]
    speaker_ref: str
    addressee_ref: str
    actor_ref: str | None
    temporal_frame_ref: str
    active_event_refs: tuple[str, ...]
    focus_snapshot_ref: str
    focus_refs: tuple[str, ...]
    obligation_snapshot_ref: str
    obligation_refs: tuple[str, ...]
    capability_refs: tuple[str, ...]
    permission_snapshot_ref: str
    permission_refs: tuple[str, ...]
    resource_snapshot_ref: str
    resource_refs: tuple[str, ...]
    adapter_snapshot_ref: str
    adapter_refs: tuple[str, ...]
    evidence_kinds: tuple[str, ...]
    evidence_policy_refs: tuple[str, ...]
    adapter_receipt_refs: tuple[str, ...]
    trusted_observation: bool
    source_refs: tuple[str, ...]
    epistemic_scope_ref: str
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "situation_ref", "orientation_ref", "proposal_context_ref",
        "mode", "session_ref", "turn_ref", "turn_index", "session_phase_ref",
        "participant_refs", "speaker_ref", "addressee_ref", "actor_ref",
        "temporal_frame_ref", "active_event_refs", "focus_snapshot_ref",
        "focus_refs", "obligation_snapshot_ref", "obligation_refs",
        "capability_refs", "permission_snapshot_ref", "permission_refs",
        "resource_snapshot_ref", "resource_refs", "adapter_snapshot_ref",
        "adapter_refs", "evidence_kinds", "evidence_policy_refs",
        "adapter_receipt_refs", "trusted_observation", "source_refs",
        "epistemic_scope_ref", "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use SituationContext.create")

    @staticmethod
    def _material(values: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {"abi_version": SITUATION_CONTEXT_ABI_VERSION}
        for key, item in values.items():
            if isinstance(item, SemanticMode):
                result[key] = item.value
            elif type(item) is tuple:
                result[key] = list(item)
            elif type(item) is RevisionPin:
                result[key] = item.as_dict()
            else:
                result[key] = item
        return result

    @classmethod
    def _from(cls, situation_ref: str, values: Mapping[str, Any]) -> "SituationContext":
        result = object.__new__(cls)
        object.__setattr__(result, "abi_version", SITUATION_CONTEXT_ABI_VERSION)
        object.__setattr__(result, "situation_ref", situation_ref)
        for key, item in values.items():
            object.__setattr__(result, key, item)
        return result

    @classmethod
    def create(
        cls,
        *,
        orientation_ref: str,
        proposal_context_ref: str,
        mode: SemanticMode,
        session_ref: str,
        turn_ref: str,
        turn_index: int,
        session_phase_ref: str,
        participant_refs: tuple[str, ...],
        speaker_ref: str,
        addressee_ref: str,
        actor_ref: str | None,
        temporal_frame_ref: str,
        active_event_refs: tuple[str, ...],
        focus_snapshot_ref: str,
        focus_refs: tuple[str, ...],
        obligation_snapshot_ref: str,
        obligation_refs: tuple[str, ...],
        capability_refs: tuple[str, ...],
        permission_snapshot_ref: str,
        permission_refs: tuple[str, ...],
        resource_snapshot_ref: str,
        resource_refs: tuple[str, ...],
        adapter_snapshot_ref: str,
        adapter_refs: tuple[str, ...],
        evidence_kinds: tuple[str, ...],
        evidence_policy_refs: tuple[str, ...],
        adapter_receipt_refs: tuple[str, ...],
        trusted_observation: bool,
        source_refs: tuple[str, ...],
        epistemic_scope_ref: str,
        revision_pin: RevisionPin,
    ) -> "SituationContext":
        if cls is not SituationContext:
            raise TypeError("SituationContext factories require exact class")
        if type(mode) is not SemanticMode:
            raise TypeError("mode must be exact SemanticMode")
        if type(turn_index) is not int or isinstance(turn_index, bool) or turn_index < 1:
            raise ValueError("turn_index must be a positive exact int")
        if type(trusted_observation) is not bool:
            raise TypeError("trusted_observation must be exact bool")
        evidence = _refs(evidence_kinds, "evidence_kinds", nonempty=True)
        if any(kind not in _EVIDENCE_KINDS for kind in evidence):
            raise ValueError("unsupported situation evidence kind")
        values = {
            "orientation_ref": _text(orientation_ref, "orientation_ref"),
            "proposal_context_ref": _text(proposal_context_ref, "proposal_context_ref"),
            "mode": mode,
            "session_ref": _text(session_ref, "session_ref"),
            "turn_ref": _text(turn_ref, "turn_ref"),
            "turn_index": turn_index,
            "session_phase_ref": _text(session_phase_ref, "session_phase_ref"),
            "participant_refs": _refs(participant_refs, "participant_refs", nonempty=True),
            "speaker_ref": _text(speaker_ref, "speaker_ref"),
            "addressee_ref": _text(addressee_ref, "addressee_ref"),
            "actor_ref": _optional(actor_ref, "actor_ref"),
            "temporal_frame_ref": _text(temporal_frame_ref, "temporal_frame_ref"),
            "active_event_refs": _refs(active_event_refs, "active_event_refs"),
            "focus_snapshot_ref": _text(focus_snapshot_ref, "focus_snapshot_ref"),
            "focus_refs": _refs(focus_refs, "focus_refs"),
            "obligation_snapshot_ref": _text(obligation_snapshot_ref, "obligation_snapshot_ref"),
            "obligation_refs": _refs(obligation_refs, "obligation_refs"),
            "capability_refs": _refs(capability_refs, "capability_refs"),
            "permission_snapshot_ref": _text(permission_snapshot_ref, "permission_snapshot_ref"),
            "permission_refs": _refs(permission_refs, "permission_refs"),
            "resource_snapshot_ref": _text(resource_snapshot_ref, "resource_snapshot_ref"),
            "resource_refs": _refs(resource_refs, "resource_refs"),
            "adapter_snapshot_ref": _text(adapter_snapshot_ref, "adapter_snapshot_ref"),
            "adapter_refs": _refs(adapter_refs, "adapter_refs"),
            "evidence_kinds": evidence,
            "evidence_policy_refs": _refs(evidence_policy_refs, "evidence_policy_refs", nonempty=True),
            "adapter_receipt_refs": _refs(adapter_receipt_refs, "adapter_receipt_refs"),
            "trusted_observation": trusted_observation,
            "source_refs": _refs(source_refs, "source_refs", nonempty=True),
            "epistemic_scope_ref": _text(epistemic_scope_ref, "epistemic_scope_ref"),
            "revision_pin": _pin(revision_pin),
        }
        participants = values["participant_refs"]
        if values["speaker_ref"] not in participants or values["addressee_ref"] not in participants:
            raise ValueError("speaker/addressee must be reviewed participants")
        if values["speaker_ref"] == values["addressee_ref"]:
            raise ValueError("speaker_ref and addressee_ref must differ")
        if values["actor_ref"] is not None and values["actor_ref"] not in participants:
            raise ValueError("actor_ref must be a reviewed participant")
        if values["epistemic_scope_ref"] != _EPISTEMIC_SCOPE_BY_MODE[mode]:
            raise ValueError("epistemic scope does not match mode")
        if trusted_observation:
            if set(evidence).isdisjoint({"sensor", "operation"}):
                raise ValueError("trusted observation requires sensor/operation evidence")
            if not values["adapter_receipt_refs"]:
                raise ValueError("trusted observation requires adapter receipts")
        elif values["adapter_receipt_refs"] and evidence == ("text",):
            raise ValueError("text-only conversation cannot carry trusted adapter receipts")
        material = cls._material(values)
        return cls._from(stable_ref("situation_context", material), values)

    def as_dict(self) -> dict[str, Any]:
        values = {name: getattr(self, name) for name in self._FIELDS - {"abi_version", "situation_ref"}}
        return {"situation_ref": self.situation_ref, **self._material(values)}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SituationContext":
        if type(value) is not dict or frozenset(value) != cls._FIELDS:
            raise ValueError("SituationContext fields mismatch")
        if type(value["abi_version"]) is not int or value["abi_version"] != SITUATION_CONTEXT_ABI_VERSION:
            raise ValueError("unsupported Situation Context ABI")
        if type(value["mode"]) is not str or type(value["revision_pin"]) is not dict:
            raise TypeError("SituationContext nested wire types are invalid")
        rebuilt = cls.create(
            orientation_ref=value["orientation_ref"],
            proposal_context_ref=value["proposal_context_ref"],
            mode=SemanticMode(value["mode"]),
            session_ref=value["session_ref"],
            turn_ref=value["turn_ref"],
            turn_index=value["turn_index"],
            session_phase_ref=value["session_phase_ref"],
            participant_refs=_wire_refs(value["participant_refs"], "participant_refs", nonempty=True),
            speaker_ref=value["speaker_ref"],
            addressee_ref=value["addressee_ref"],
            actor_ref=value["actor_ref"],
            temporal_frame_ref=value["temporal_frame_ref"],
            active_event_refs=_wire_refs(value["active_event_refs"], "active_event_refs"),
            focus_snapshot_ref=value["focus_snapshot_ref"],
            focus_refs=_wire_refs(value["focus_refs"], "focus_refs"),
            obligation_snapshot_ref=value["obligation_snapshot_ref"],
            obligation_refs=_wire_refs(value["obligation_refs"], "obligation_refs"),
            capability_refs=_wire_refs(value["capability_refs"], "capability_refs"),
            permission_snapshot_ref=value["permission_snapshot_ref"],
            permission_refs=_wire_refs(value["permission_refs"], "permission_refs"),
            resource_snapshot_ref=value["resource_snapshot_ref"],
            resource_refs=_wire_refs(value["resource_refs"], "resource_refs"),
            adapter_snapshot_ref=value["adapter_snapshot_ref"],
            adapter_refs=_wire_refs(value["adapter_refs"], "adapter_refs"),
            evidence_kinds=_wire_refs(value["evidence_kinds"], "evidence_kinds", nonempty=True),
            evidence_policy_refs=_wire_refs(value["evidence_policy_refs"], "evidence_policy_refs", nonempty=True),
            adapter_receipt_refs=_wire_refs(value["adapter_receipt_refs"], "adapter_receipt_refs"),
            trusted_observation=value["trusted_observation"],
            source_refs=_wire_refs(value["source_refs"], "source_refs", nonempty=True),
            epistemic_scope_ref=value["epistemic_scope_ref"],
            revision_pin=RevisionPin.from_dict(value["revision_pin"]),
        )
        if rebuilt.situation_ref != value["situation_ref"] or rebuilt.as_dict() != value:
            raise ValueError("non-canonical SituationContext encoding")
        return rebuilt


class SituationContextBuilder:
    """Build one situation from authenticated R2 artifacts and store snapshots."""

    def __init__(self, authority: Any | None = None) -> None:
        self._authority = authority

    def build(
        self,
        orientation: Orientation,
        context: ProposalContext,
        *,
        evidence: EvidencePacket,
        turn_index: int,
        session_phase_ref: str,
        focus_snapshot_ref: str,
        focus_refs: tuple[str, ...],
        obligation_snapshot_ref: str,
        obligation_refs: tuple[str, ...],
        permission_snapshot_ref: str,
        resource_snapshot_ref: str,
        resource_refs: tuple[str, ...],
        adapter_snapshot_ref: str,
        adapter_refs: tuple[str, ...],
        evidence_policy_refs: tuple[str, ...],
    ) -> SituationContext:
        if type(orientation) is not Orientation or type(context) is not ProposalContext:
            raise TypeError("situation builder requires exact R2 artifacts")
        if type(evidence) is not EvidencePacket:
            raise TypeError("evidence must be exact EvidencePacket")
        if context.orientation_ref != orientation.orientation_ref or context.revision_pin != orientation.revision_pin:
            raise ValueError("situation R2 lineage mismatch")
        modes = tuple(dict.fromkeys(row.mode for row in context.mode_slots))
        if len(modes) != 1:
            raise ValueError("situation requires one unambiguous structural mode")
        mode = SemanticMode(modes[0])
        if mode is not orientation.mode:
            raise ValueError("orientation and structural mode disagree")
        participants = tuple(orientation.participants)
        if self._authority is not None:
            atoms = getattr(self._authority, "atoms", {})
            missing = tuple(ref for ref in participants if ref not in atoms)
            if missing:
                raise ValueError(f"situation participant absent from authority: {missing}")
        speaker = orientation.participant_frame
        candidates = tuple(ref for ref in participants if ref != speaker)
        if "participant:system" in candidates:
            addressee = "participant:system"
        elif "participant:user" in candidates:
            addressee = "participant:user"
        elif len(candidates) == 1:
            addressee = candidates[0]
        else:
            raise ValueError("situation lacks one reviewed addressee")
        actor = addressee if mode is SemanticMode.REQUEST else None
        evidence_kinds = tuple(dict.fromkeys(item.source for item in evidence.items))
        adapter_receipts = tuple(
            dict.fromkeys(
                item.adapter_receipt_ref
                for item in evidence.items
                if item.adapter_receipt_ref is not None
            )
        )
        trusted = bool(adapter_receipts) and not set(evidence_kinds).isdisjoint({"sensor", "operation"})
        source_refs = tuple(dict.fromkeys((evidence.packet_ref, *(item.item_ref for item in evidence.items))))
        return SituationContext.create(
            orientation_ref=orientation.orientation_ref,
            proposal_context_ref=context.context_ref,
            mode=mode,
            session_ref=orientation.session_ref,
            turn_ref=orientation.turn_ref,
            turn_index=turn_index,
            session_phase_ref=session_phase_ref,
            participant_refs=participants,
            speaker_ref=speaker,
            addressee_ref=addressee,
            actor_ref=actor,
            temporal_frame_ref=orientation.temporal_frame,
            active_event_refs=tuple(orientation.event_refs),
            focus_snapshot_ref=focus_snapshot_ref,
            focus_refs=focus_refs,
            obligation_snapshot_ref=obligation_snapshot_ref,
            obligation_refs=obligation_refs,
            capability_refs=tuple(orientation.capability_summary),
            permission_snapshot_ref=permission_snapshot_ref,
            permission_refs=tuple(orientation.permission_summary),
            resource_snapshot_ref=resource_snapshot_ref,
            resource_refs=resource_refs,
            adapter_snapshot_ref=adapter_snapshot_ref,
            adapter_refs=adapter_refs,
            evidence_kinds=evidence_kinds,
            evidence_policy_refs=evidence_policy_refs,
            adapter_receipt_refs=adapter_receipts,
            trusted_observation=trusted,
            source_refs=source_refs,
            epistemic_scope_ref=_EPISTEMIC_SCOPE_BY_MODE[mode],
            revision_pin=orientation.revision_pin,
        )


class SituationContextVerifier:
    def __init__(self, authority: Any | None = None) -> None:
        self._authority = authority

    def verify(self, situation: SituationContext, orientation: Orientation, context: ProposalContext, **inputs: Any) -> SituationContext:
        if type(situation) is not SituationContext:
            raise TypeError("situation must be exact SituationContext")
        canonical = SituationContext.from_dict(situation.as_dict())
        rebuilt = SituationContextBuilder(self._authority).build(orientation, context, **inputs)
        if canonical != rebuilt:
            raise ValueError("SituationContext does not match authenticated inputs")
        return canonical
