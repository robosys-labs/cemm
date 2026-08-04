"""Six-phase semantic kernel cycle, receipts and closed enums.

This module owns the Phase Receipt ABI and the closed semantic-mode,
cycle-outcome and semantic-phase enums. The six phases are mathematical
ownership boundaries:

    ORIENT -> PROPOSE -> VERIFY -> EVALUATE -> EFFECT -> REALIZE

``SemanticMode`` constrains evaluation/effect legality after composition; it is
not a phrase intent and cannot be selected by a raw-surface branch.
``CycleStatus`` is the closed externally reachable outcome enum.

Trace collection is opt-in and observational: identical input, revision and
model with trace on/off yields identical semantic result and store revisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, TYPE_CHECKING

from .canonical import stable_ref
from .config import RuntimeConfig
from .forms import (
    EVIDENCE_MAX_INTEGER,
    EVIDENCE_MAX_KEY_CHARS,
    EVIDENCE_MAX_REF_CHARS,
    EVIDENCE_MAX_SOURCE_CHARS,
)
from .gaps import GapKind, GapReceipt, RepairOwner
from .persistence import RevisionPin

if TYPE_CHECKING:
    from .dialogue import FocusStore, DialogueObligationManager
    from .proposal import ProposalResult
    from .verifier import VerificationBatch

__all__ = [
    "SemanticMode",
    "CycleStatus",
    "SemanticPhase",
    "PhaseDisposition",
    "ORIENTATION_ABI_VERSION",
    "PHASE_RECEIPT_ABI_VERSION",
    "CYCLE_RESULT_ABI_VERSION",
    "Orientation",
    "OrientationProjector",
    "PhaseReceipt",
    "CycleFinalizer",
    "CycleResult",
]


# ---------------------------------------------------------------------------
# Closed enums
# ---------------------------------------------------------------------------


class SemanticMode(Enum):
    """Closed cycle-mode enum.

    Modes constrain evaluation/effect legality after composition. They are
    not phrase intents and cannot be selected by a raw-surface branch.
    """

    OBSERVE = "OBSERVE"
    QUERY = "QUERY"
    REQUEST = "REQUEST"
    SIMULATE = "SIMULATE"


class CycleStatus(Enum):
    """Closed externally reachable outcome enum."""

    RESOLVED = "resolved"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    UNSUPPORTED = "unsupported"
    DENIED = "denied"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    BUDGET_EXHAUSTED = "budget_exhausted"
    OPERATION_FAILED = "operation_failed"
    REALIZATION_FAILED = "realization_failed"


class SemanticPhase(Enum):
    """The six semantic kernel phases (mathematical ownership boundaries)."""

    ORIENT = "ORIENT"
    PROPOSE = "PROPOSE"
    VERIFY = "VERIFY"
    EVALUATE = "EVALUATE"
    EFFECT = "EFFECT"
    REALIZE = "REALIZE"


# ---------------------------------------------------------------------------
# Orientation (ORIENT phase output)
# ---------------------------------------------------------------------------


ORIENTATION_ABI_VERSION = 1
_ORIENTATION_CONFIG = RuntimeConfig.release()
_ORIENTATION_MAX_ITEMS = (
    _ORIENTATION_CONFIG.max_input_tokens
    * _ORIENTATION_CONFIG.max_orientation_alternatives
)
_ORIENTATION_MAX_BUDGETS = _ORIENTATION_CONFIG.max_input_tokens
_ORIENTATION_MAX_SCANNED_ATOMS = _ORIENTATION_CONFIG.max_inference_facts


def _orientation_text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value and not allow_empty:
        raise ValueError(f"{name} must be nonempty")
    if name == "source_text":
        maximum = EVIDENCE_MAX_SOURCE_CHARS
    elif name == "session_ref":
        maximum = EVIDENCE_MAX_KEY_CHARS
    else:
        maximum = EVIDENCE_MAX_REF_CHARS
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    return value


def _orientation_tuple(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if len(value) > _ORIENTATION_MAX_ITEMS:
        raise ValueError(f"{name} exceeds orientation item bound")
    for item in value:
        _orientation_text(item, f"{name} item")
    return value


def _orientation_budgets(value: object) -> Mapping[str, int]:
    if not isinstance(value, Mapping):
        raise TypeError("budgets must be a mapping")
    if len(value) > _ORIENTATION_MAX_BUDGETS:
        raise ValueError("budgets exceeds orientation budget-count bound")
    copied: dict[str, int] = {}
    for key, amount in value.items():
        if type(key) is not str:
            raise TypeError("budget keys must be exact str")
        if not key:
            raise ValueError("budget keys must be nonempty")
        if len(key) > EVIDENCE_MAX_KEY_CHARS:
            raise ValueError("budget key exceeds evidence key bound")
        if type(amount) is not int:
            raise TypeError("budget values must be exact int")
        if amount < 0 or amount > EVIDENCE_MAX_INTEGER:
            raise ValueError("budget values must be bounded nonnegative integers")
        copied[key] = amount
    return MappingProxyType(copied)


@dataclass(frozen=True)
class Orientation:
    """Canonical content-addressed ORIENT output (Orientation ABI 1)."""

    abi_version: int
    orientation_ref: str
    session_ref: str
    turn_ref: str
    source_text: str
    mode: SemanticMode
    participant_frame: str
    temporal_frame: str
    participants: tuple[str, ...]
    active_turn_ref: str
    event_refs: tuple[str, ...]
    focus_refs: tuple[str, ...]
    obligation_refs: tuple[str, ...]
    capability_summary: tuple[str, ...]
    permission_summary: tuple[str, ...]
    budgets: Mapping[str, int]
    scanned_atom_count: int
    index_probes: tuple[str, ...]
    visited_refs: tuple[str, ...]
    revision_pin: RevisionPin
    cache_key: str | None = None

    _FIELDS = frozenset({
        "abi_version", "orientation_ref", "session_ref", "turn_ref",
        "source_text", "mode", "participant_frame", "temporal_frame",
        "participants", "active_turn_ref", "event_refs", "focus_refs",
        "obligation_refs", "capability_summary", "permission_summary",
        "budgets", "scanned_atom_count", "index_probes", "visited_refs",
        "revision_pin",
    })
    _TUPLE_FIELDS = (
        "participants", "event_refs", "focus_refs", "obligation_refs",
        "capability_summary", "permission_summary", "index_probes", "visited_refs",
    )

    def __post_init__(self) -> None:
        if type(self.abi_version) is not int:
            raise TypeError("abi_version must be exact int")
        if self.abi_version != ORIENTATION_ABI_VERSION:
            raise ValueError("unsupported Orientation ABI version")
        _orientation_text(self.orientation_ref, "orientation_ref")
        if self.cache_key is not None:
            _orientation_text(self.cache_key, "cache_key")
        material, frozen_budgets = self._material(
            session_ref=self.session_ref, turn_ref=self.turn_ref,
            source_text=self.source_text, mode=self.mode,
            participant_frame=self.participant_frame,
            temporal_frame=self.temporal_frame, participants=self.participants,
            active_turn_ref=self.active_turn_ref, event_refs=self.event_refs,
            focus_refs=self.focus_refs, obligation_refs=self.obligation_refs,
            capability_summary=self.capability_summary,
            permission_summary=self.permission_summary, budgets=self.budgets,
            scanned_atom_count=self.scanned_atom_count,
            index_probes=self.index_probes, visited_refs=self.visited_refs,
            revision_pin=self.revision_pin,
        )
        object.__setattr__(self, "budgets", frozen_budgets)
        if self.orientation_ref != stable_ref("orientation", material):
            raise ValueError("Orientation ref mismatch")

    @classmethod
    def create(
        cls, *, session_ref: str, turn_ref: str, source_text: str,
        mode: SemanticMode, participant_frame: str, temporal_frame: str,
        participants: tuple[str, ...], active_turn_ref: str,
        event_refs: tuple[str, ...], focus_refs: tuple[str, ...],
        obligation_refs: tuple[str, ...], capability_summary: tuple[str, ...],
        permission_summary: tuple[str, ...], budgets: Mapping[str, int],
        scanned_atom_count: int, index_probes: tuple[str, ...],
        visited_refs: tuple[str, ...], revision_pin: RevisionPin,
        cache_key: str | None = None,
    ) -> "Orientation":
        if cls is not Orientation:
            raise TypeError("Orientation factories require exact Orientation")
        if cache_key is not None:
            _orientation_text(cache_key, "cache_key")
        material, frozen_budgets = cls._material(
            session_ref=session_ref, turn_ref=turn_ref, source_text=source_text,
            mode=mode, participant_frame=participant_frame,
            temporal_frame=temporal_frame, participants=participants,
            active_turn_ref=active_turn_ref, event_refs=event_refs,
            focus_refs=focus_refs, obligation_refs=obligation_refs,
            capability_summary=capability_summary,
            permission_summary=permission_summary, budgets=budgets,
            scanned_atom_count=scanned_atom_count, index_probes=index_probes,
            visited_refs=visited_refs, revision_pin=revision_pin,
        )
        value = object.__new__(cls)
        values = {
            "abi_version": ORIENTATION_ABI_VERSION,
            "orientation_ref": stable_ref("orientation", material),
            "session_ref": session_ref, "turn_ref": turn_ref,
            "source_text": source_text, "mode": mode,
            "participant_frame": participant_frame,
            "temporal_frame": temporal_frame,
            "participants": participants, "active_turn_ref": active_turn_ref,
            "event_refs": event_refs, "focus_refs": focus_refs,
            "obligation_refs": obligation_refs,
            "capability_summary": capability_summary,
            "permission_summary": permission_summary,
            "budgets": frozen_budgets,
            "scanned_atom_count": scanned_atom_count,
            "index_probes": index_probes, "visited_refs": visited_refs,
            "revision_pin": revision_pin, "cache_key": cache_key,
        }
        for name, item in values.items():
            object.__setattr__(value, name, item)
        return value

    @staticmethod
    def _material(
        *, session_ref: str, turn_ref: str, source_text: str,
        mode: SemanticMode, participant_frame: str, temporal_frame: str,
        participants: tuple[str, ...], active_turn_ref: str,
        event_refs: tuple[str, ...], focus_refs: tuple[str, ...],
        obligation_refs: tuple[str, ...], capability_summary: tuple[str, ...],
        permission_summary: tuple[str, ...], budgets: Mapping[str, int],
        scanned_atom_count: int, index_probes: tuple[str, ...],
        visited_refs: tuple[str, ...], revision_pin: RevisionPin,
    ) -> tuple[dict[str, Any], Mapping[str, int]]:
        for name, value in (
            ("session_ref", session_ref), ("turn_ref", turn_ref),
            ("participant_frame", participant_frame),
            ("temporal_frame", temporal_frame),
            ("active_turn_ref", active_turn_ref),
        ):
            _orientation_text(value, name)
        _orientation_text(source_text, "source_text", allow_empty=True)
        if type(mode) is not SemanticMode:
            raise TypeError("mode must be SemanticMode")
        for name, value in (
            ("participants", participants), ("event_refs", event_refs),
            ("focus_refs", focus_refs), ("obligation_refs", obligation_refs),
            ("capability_summary", capability_summary),
            ("permission_summary", permission_summary),
            ("index_probes", index_probes), ("visited_refs", visited_refs),
        ):
            _orientation_tuple(value, name)
        frozen_budgets = _orientation_budgets(budgets)
        if type(scanned_atom_count) is not int:
            raise TypeError("scanned_atom_count must be exact int")
        if not 0 <= scanned_atom_count <= _ORIENTATION_MAX_SCANNED_ATOMS:
            raise ValueError("scanned_atom_count exceeds configured bound")
        if type(revision_pin) is not RevisionPin:
            raise TypeError("revision_pin must be exact RevisionPin")
        try:
            revision_pin_material = RevisionPin.as_dict(revision_pin)
            canonical_pin = RevisionPin.from_dict(revision_pin_material)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("revision_pin must be canonical RevisionPin") from exc
        if canonical_pin != revision_pin:
            raise ValueError("revision_pin must be canonical RevisionPin")
        material = {
            "abi_version": ORIENTATION_ABI_VERSION,
            "session_ref": session_ref, "turn_ref": turn_ref,
            "source_text": source_text, "mode": mode.value,
            "participant_frame": participant_frame,
            "temporal_frame": temporal_frame,
            "participants": list(participants),
            "active_turn_ref": active_turn_ref,
            "event_refs": list(event_refs), "focus_refs": list(focus_refs),
            "obligation_refs": list(obligation_refs),
            "capability_summary": list(capability_summary),
            "permission_summary": list(permission_summary),
            "budgets": dict(frozen_budgets),
            "scanned_atom_count": scanned_atom_count,
            "index_probes": list(index_probes),
            "visited_refs": list(visited_refs),
            "revision_pin": revision_pin_material,
        }
        return material, frozen_budgets

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "orientation_ref": self.orientation_ref,
            "session_ref": self.session_ref,
            "turn_ref": self.turn_ref,
            "source_text": self.source_text,
            "mode": self.mode.value,
            "participant_frame": self.participant_frame,
            "temporal_frame": self.temporal_frame,
            "participants": list(self.participants),
            "active_turn_ref": self.active_turn_ref,
            "event_refs": list(self.event_refs),
            "focus_refs": list(self.focus_refs),
            "obligation_refs": list(self.obligation_refs),
            "capability_summary": list(self.capability_summary),
            "permission_summary": list(self.permission_summary),
            "budgets": dict(self.budgets),
            "scanned_atom_count": self.scanned_atom_count,
            "index_probes": list(self.index_probes),
            "visited_refs": list(self.visited_refs),
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Orientation":
        if cls is not Orientation:
            raise TypeError("Orientation factories require exact Orientation")
        if type(data) is not dict:
            raise TypeError("Orientation payload must be an exact dict")
        if len(data) != len(cls._FIELDS):
            raise ValueError("Orientation payload has wrong field count")
        if any(type(key) is not str for key in data):
            raise TypeError("Orientation field names must be exact str")
        if frozenset(data) != cls._FIELDS:
            raise ValueError("Orientation payload fields mismatch")
        if type(data["abi_version"]) is not int:
            raise TypeError("abi_version wire value must be exact int")
        _orientation_text(data["orientation_ref"], "orientation_ref")
        if type(data["mode"]) is not str:
            raise TypeError("mode wire value must be exact str")
        try:
            mode = SemanticMode(data["mode"])
        except ValueError as exc:
            raise ValueError("unsupported Orientation mode") from exc
        tuples: dict[str, tuple[str, ...]] = {}
        for name in cls._TUPLE_FIELDS:
            value = data[name]
            if type(value) is not list:
                raise TypeError(f"{name} wire value must be an exact list")
            if len(value) > _ORIENTATION_MAX_ITEMS:
                raise ValueError(f"{name} exceeds orientation item bound")
            for item in value:
                _orientation_text(item, f"{name} item")
            tuples[name] = tuple(value)
        if type(data["budgets"]) is not dict:
            raise TypeError("budgets wire value must be an exact dict")
        if type(data["revision_pin"]) is not dict:
            raise TypeError("revision_pin wire value must be an exact dict")
        rebuilt = cls.create(
            session_ref=data["session_ref"], turn_ref=data["turn_ref"],
            source_text=data["source_text"], mode=mode,
            participant_frame=data["participant_frame"],
            temporal_frame=data["temporal_frame"],
            participants=tuples["participants"],
            active_turn_ref=data["active_turn_ref"], event_refs=tuples["event_refs"],
            focus_refs=tuples["focus_refs"], obligation_refs=tuples["obligation_refs"],
            capability_summary=tuples["capability_summary"],
            permission_summary=tuples["permission_summary"], budgets=data["budgets"],
            scanned_atom_count=data["scanned_atom_count"],
            index_probes=tuples["index_probes"], visited_refs=tuples["visited_refs"],
            revision_pin=RevisionPin.from_dict(data["revision_pin"]), cache_key=None,
        )
        if data["abi_version"] != ORIENTATION_ABI_VERSION:
            raise ValueError("unsupported Orientation ABI version")
        if data["orientation_ref"] != rebuilt.orientation_ref:
            raise ValueError("Orientation ref mismatch")
        if rebuilt.as_dict() != data:
            raise ValueError("non-canonical Orientation encoding")
        return rebuilt

# ---------------------------------------------------------------------------
# OrientationProjector — bounded ORIENT projection
# ---------------------------------------------------------------------------


class OrientationProjector:
    """Builds an :class:`Orientation` from stores, authority and evidence.

    Projection starts from participants, active turn/session events, verified
    focus, open obligations, and relevant goals.  It traverses indexed typed
    relations within the configured depth and records index probes, visited
    refs, cache key, and revision pin.  It does **not** scan all atoms
    (``scanned_atom_count == 0``).

    Entity, concept, relation, state, and event identities remain
    independently addressable; events do not become a universal wrapper.
    """

    def __init__(
        self,
        authority: Any,
        stores: Any,
        config: Any,
        *,
        focus_store: "FocusStore | None" = None,
        obligation_manager: "DialogueObligationManager | None" = None,
    ) -> None:
        self._authority = authority
        self._stores = stores
        self._config = config
        self._max_depth = getattr(config, "max_graph_depth", 6)
        self._focus_store = focus_store
        self._obligation_manager = obligation_manager

    def project(
        self,
        session_ref: str,
        text: str,
        *,
        mode: SemanticMode = SemanticMode.OBSERVE,
    ) -> Orientation:
        """Project one bounded exact-content orientation without graph scans."""
        _orientation_text(session_ref, "session_ref")
        _orientation_text(text, "source_text", allow_empty=True)
        if type(mode) is not SemanticMode:
            raise TypeError("mode must be SemanticMode")
        words = self._tokenize(text)
        if len(words) > self._config.max_input_tokens:
            raise ValueError("projector token bound violated")
        pin = self._stores.revision_pin()
        index_probes: list[str] = []
        visited: list[str] = []

        # -- Participants (from authority, sorted) --------------------------
        participant_refs = sorted(
            self._authority.by_kind("participant")
        )
        index_probes.append("by_kind:participant")
        visited.extend(participant_refs)

        # -- Active turn / session events -----------------------------------
        turn_ref = f"turn:{session_ref}"
        session_event_ref = f"event:session:{session_ref}"
        event_refs = (session_event_ref, turn_ref)
        visited.extend(event_refs)

        # -- Focus refs -----------------------------------------------------
        # When a FocusStore is provided, use verified focus refs; otherwise
        # ground the text via the authority's designation index.
        if self._focus_store is not None:
            index_probes.append("focus_store:refs")
            focus_refs = tuple(sorted(self._focus_store.refs))
            visited.extend(focus_refs)
        else:
            focus_refs = self._ground_focus(words, index_probes, visited)

        # -- Traverse relations from focus within max_depth -----------------
        self._traverse(focus_refs, index_probes, visited, depth=0)

        # -- Obligations ----------------------------------------------------
        # When a DialogueObligationManager is provided, use pending refs;
        # otherwise obligations remain empty.
        obligation_refs: tuple[str, ...] = ()
        if self._obligation_manager is not None:
            index_probes.append("obligations:pending")
            obligation_refs = tuple(
                ob.obligation_ref for ob in self._obligation_manager.pending()
            )
            visited.extend(obligation_refs)
        else:
            index_probes.append("obligations:get_open")

        # -- Capabilities and permissions -----------------------------------
        cap_summary = tuple(
            self._authority.capabilities.get("participant:system", [])
        )
        perm_summary = tuple(
            f"{p[0]}:{p[1]}:{p[2]}" for p in self._authority.permissions
        )
        index_probes.append("capabilities:participant:system")
        index_probes.append("permissions:all")

        orientation = Orientation.create(
            session_ref=session_ref,
            turn_ref=turn_ref,
            source_text=text,
            mode=mode,
            participant_frame="participant:user",
            temporal_frame="now",
            participants=tuple(participant_refs),
            active_turn_ref=turn_ref,
            event_refs=event_refs,
            focus_refs=focus_refs,
            obligation_refs=obligation_refs,
            capability_summary=cap_summary,
            permission_summary=perm_summary,
            budgets={"input_tokens": self._config.max_input_tokens},
            scanned_atom_count=0,
            index_probes=tuple(index_probes),
            visited_refs=tuple(visited),
            revision_pin=pin,
            cache_key=None,
        )
        object.__setattr__(orientation, "cache_key", orientation.orientation_ref)
        return orientation

    # -- internal: focus grounding ------------------------------------------

    def _ground_focus(
        self,
        words: list[str],
        index_probes: list[str],
        visited: list[str],
    ) -> tuple[str, ...]:
        """Ground one already-bounded token sequence through exact lookup."""
        index_probes.append("designations:for_surface")
        focus: list[str] = []
        for word in words:
            targets = self._authority.designations.for_surface(word, "en")
            for target in targets:
                if target not in focus:
                    focus.append(target)
                    visited.append(target)
        return tuple(focus)
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Split text into lowercase word tokens (stripping punctuation)."""
        import re

        return [
            w.lower()
            for w in re.findall(r"[A-Za-z]+", text)
        ]

    # -- internal: relation traversal ---------------------------------------

    def _traverse(
        self,
        refs: tuple[str, ...],
        index_probes: list[str],
        visited: list[str],
        depth: int,
    ) -> None:
        """Expose the disabled adjacency seam without enumerating authority."""
        if "relation_adjacency:unavailable" not in index_probes:
            index_probes.append("relation_adjacency:unavailable")

# ---------------------------------------------------------------------------
# Canonical Phase Receipt ABI 2 and Cycle Result ABI 2
# ---------------------------------------------------------------------------


PHASE_RECEIPT_ABI_VERSION = 2
CYCLE_RESULT_ABI_VERSION = 2
_PHASE_MAX_REFS = RuntimeConfig.release().max_input_tokens
_PHASE_MAX_BUDGETS = RuntimeConfig.release().max_input_tokens
_CYCLE_MAX_PHASES = len(SemanticPhase)


class PhaseDisposition(Enum):
    COMPLETED = "completed"
    ABSTAINED = "abstained"
    REJECTED = "rejected"
    GAP = "gap"
    COMMITTED = "committed"
    NO_EFFECT = "no_effect"
    FAILED = "failed"


def _cycle_text(value: object, name: str, maximum: int = EVIDENCE_MAX_REF_CHARS) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    return value


def _cycle_tuple(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if len(value) > _PHASE_MAX_REFS:
        raise ValueError(f"{name} exceeds phase ref bound")
    for item in value:
        _cycle_text(item, f"{name} item")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must contain unique refs")
    return value


def _cycle_pin(value: object, name: str) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError(f"{name} must be exact RevisionPin")
    try:
        rebuilt = RevisionPin.from_dict(value.as_dict())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not canonical") from exc
    if rebuilt != value:
        raise ValueError(f"{name} is not canonical")
    return value


def _cycle_budget(value: object) -> Mapping[str, int]:
    if not isinstance(value, Mapping):
        raise TypeError("budget_use must be a mapping")
    if len(value) > _PHASE_MAX_BUDGETS:
        raise ValueError("budget_use exceeds phase budget bound")
    copied: dict[str, int] = {}
    for key, amount in value.items():
        _cycle_text(key, "budget key", EVIDENCE_MAX_KEY_CHARS)
        if type(amount) is not int:
            raise TypeError("budget values must be exact int")
        if not 0 <= amount <= EVIDENCE_MAX_INTEGER:
            raise ValueError("budget values must be bounded nonnegative integers")
        copied[key] = amount
    return MappingProxyType(copied)


def _cycle_duration(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int:
        raise TypeError("duration_ns must be exact int or None")
    if not 0 <= value <= EVIDENCE_MAX_INTEGER:
        raise ValueError("duration_ns must be a bounded nonnegative integer")
    return value


def _exact_wire_dict(value: object, fields: frozenset[str], name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{name} payload must be an exact dict")
    if len(value) != len(fields):
        raise ValueError(f"{name} payload has the wrong field count")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{name} field names must be exact str")
    if frozenset(value) != fields:
        raise ValueError(f"{name} payload fields mismatch")
    return value


def _wire_ref_list(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    if len(value) > _PHASE_MAX_REFS:
        raise ValueError(f"{name} exceeds phase ref bound")
    return _cycle_tuple(tuple(value), name)


@dataclass(frozen=True)
class _PhaseMaterial:
    phase: SemanticPhase
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    input_revision_pin: RevisionPin
    output_revision_pin: RevisionPin
    disposition: PhaseDisposition
    rejection_codes: tuple[str, ...]
    budget_use: Mapping[str, int]

    _FIELDS = frozenset({
        "phase", "input_refs", "output_refs", "input_revision_pin",
        "output_revision_pin", "disposition", "rejection_codes", "budget_use",
    })

    def __post_init__(self) -> None:
        if type(self) is not _PhaseMaterial:
            raise TypeError("_PhaseMaterial requires exact class")
        if type(self.phase) is not SemanticPhase:
            raise TypeError("phase must be SemanticPhase")
        _cycle_tuple(self.input_refs, "input_refs")
        _cycle_tuple(self.output_refs, "output_refs")
        _cycle_pin(self.input_revision_pin, "input_revision_pin")
        _cycle_pin(self.output_revision_pin, "output_revision_pin")
        if type(self.disposition) is not PhaseDisposition:
            raise TypeError("disposition must be PhaseDisposition")
        _cycle_tuple(self.rejection_codes, "rejection_codes")
        object.__setattr__(self, "budget_use", _cycle_budget(self.budget_use))
        if self.input_revision_pin != self.output_revision_pin and self.phase is not SemanticPhase.EFFECT:
            raise ValueError("only EFFECT may change the revision pin")
        if self.disposition in {PhaseDisposition.COMMITTED, PhaseDisposition.NO_EFFECT} and self.phase is not SemanticPhase.EFFECT:
            raise ValueError("committed/no_effect dispositions belong only to EFFECT")
        successful = {
            PhaseDisposition.COMPLETED,
            PhaseDisposition.COMMITTED,
            PhaseDisposition.NO_EFFECT,
        }
        if self.disposition in successful and self.rejection_codes:
            raise ValueError("successful dispositions require empty rejection_codes")
        if self.disposition not in successful and not self.rejection_codes:
            raise ValueError("terminal dispositions require nonempty rejection_codes")
        if self.phase is SemanticPhase.EFFECT:
            source = self.input_revision_pin
            target = self.output_revision_pin
            fixed_dimensions = (
                ("authority_generation", source.authority_generation, target.authority_generation),
                ("session_revision", source.session_revision, target.session_revision),
                ("episode_revision", source.episode_revision, target.episode_revision),
                ("model_identity", source.model_identity, target.model_identity),
            )
            if any(before != after for _, before, after in fixed_dimensions):
                raise ValueError("EFFECT revision change altered a fixed dimension")
            if (
                target.world_revision < source.world_revision
                or target.effect_revision < source.effect_revision
            ):
                raise ValueError("EFFECT revision changes must be monotonic")
            if (
                target != source
                and self.disposition is not PhaseDisposition.COMMITTED
            ):
                raise ValueError("only EFFECT with COMMITTED may change a revision pin")
            if self.disposition is PhaseDisposition.COMMITTED and target == source:
                raise ValueError("EFFECT with COMMITTED must advance the revision pin")

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "input_revision_pin": self.input_revision_pin.as_dict(),
            "output_revision_pin": self.output_revision_pin.as_dict(),
            "disposition": self.disposition.value,
            "rejection_codes": list(self.rejection_codes),
            "budget_use": dict(self.budget_use),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "_PhaseMaterial":
        if cls is not _PhaseMaterial:
            raise TypeError("_PhaseMaterial codec requires exact class")
        data = _exact_wire_dict(value, cls._FIELDS, "_PhaseMaterial")
        if type(data["phase"]) is not str or type(data["disposition"]) is not str:
            raise TypeError("phase/disposition wire values must be exact str")
        if type(data["input_revision_pin"]) is not dict or type(data["output_revision_pin"]) is not dict:
            raise TypeError("revision pins must be exact dicts")
        if type(data["budget_use"]) is not dict:
            raise TypeError("budget_use wire value must be an exact dict")
        return cls(
            SemanticPhase(data["phase"]),
            _wire_ref_list(data["input_refs"], "input_refs"),
            _wire_ref_list(data["output_refs"], "output_refs"),
            RevisionPin.from_dict(data["input_revision_pin"]),
            RevisionPin.from_dict(data["output_revision_pin"]),
            PhaseDisposition(data["disposition"]),
            _wire_ref_list(data["rejection_codes"], "rejection_codes"),
            data["budget_use"],
        )


def _phase_receipt_identity(cycle_ref: str, material: _PhaseMaterial) -> dict[str, Any]:
    return {
        "abi_version": PHASE_RECEIPT_ABI_VERSION,
        "cycle_ref": cycle_ref,
        "material": material.as_dict(),
    }


@dataclass(frozen=True)
class PhaseReceipt:
    abi_version: int
    receipt_ref: str
    cycle_ref: str
    phase: SemanticPhase
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    input_revision_pin: RevisionPin
    output_revision_pin: RevisionPin
    disposition: PhaseDisposition
    rejection_codes: tuple[str, ...]
    budget_use: Mapping[str, int]
    duration_ns: int | None

    _FIELDS = frozenset({
        "abi_version", "receipt_ref", "cycle_ref", "phase", "input_refs",
        "output_refs", "input_revision_pin", "output_revision_pin",
        "disposition", "rejection_codes", "budget_use", "duration_ns",
    })

    def __post_init__(self) -> None:
        if type(self) is not PhaseReceipt:
            raise TypeError("PhaseReceipt requires exact class")
        if type(self.abi_version) is not int or self.abi_version != PHASE_RECEIPT_ABI_VERSION:
            raise ValueError("unsupported Phase Receipt ABI")
        _cycle_text(self.receipt_ref, "receipt_ref")
        _cycle_text(self.cycle_ref, "cycle_ref")
        material = _PhaseMaterial(
            self.phase, self.input_refs, self.output_refs,
            self.input_revision_pin, self.output_revision_pin,
            self.disposition, self.rejection_codes, self.budget_use,
        )
        object.__setattr__(self, "budget_use", material.budget_use)
        _cycle_duration(self.duration_ns)
        if self.receipt_ref != stable_ref("phase_receipt", _phase_receipt_identity(self.cycle_ref, material)):
            raise ValueError("PhaseReceipt ref mismatch")

    @classmethod
    def create(cls, *, cycle_ref: str, material: _PhaseMaterial, duration_ns: int | None) -> "PhaseReceipt":
        if cls is not PhaseReceipt:
            raise TypeError("PhaseReceipt factories require exact PhaseReceipt")
        _cycle_text(cycle_ref, "cycle_ref")
        if type(material) is not _PhaseMaterial:
            raise TypeError("material must be exact _PhaseMaterial")
        canonical = _PhaseMaterial.from_dict(material.as_dict())
        duration = _cycle_duration(duration_ns)
        value = object.__new__(cls)
        values = {
            "abi_version": PHASE_RECEIPT_ABI_VERSION,
            "receipt_ref": stable_ref("phase_receipt", _phase_receipt_identity(cycle_ref, canonical)),
            "cycle_ref": cycle_ref,
            "phase": canonical.phase, "input_refs": canonical.input_refs,
            "output_refs": canonical.output_refs,
            "input_revision_pin": canonical.input_revision_pin,
            "output_revision_pin": canonical.output_revision_pin,
            "disposition": canonical.disposition,
            "rejection_codes": canonical.rejection_codes,
            "budget_use": canonical.budget_use, "duration_ns": duration,
        }
        for name, item in values.items():
            object.__setattr__(value, name, item)
        return value

    @property
    def material(self) -> _PhaseMaterial:
        return _PhaseMaterial(
            self.phase, self.input_refs, self.output_refs,
            self.input_revision_pin, self.output_revision_pin,
            self.disposition, self.rejection_codes, self.budget_use,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "receipt_ref": self.receipt_ref,
            "cycle_ref": self.cycle_ref, **self.material.as_dict(),
            "duration_ns": self.duration_ns,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PhaseReceipt":
        if cls is not PhaseReceipt:
            raise TypeError("PhaseReceipt codec requires exact class")
        data = _exact_wire_dict(value, cls._FIELDS, "PhaseReceipt")
        material = _PhaseMaterial.from_dict({key: data[key] for key in _PhaseMaterial._FIELDS})
        rebuilt = cls(
            data["abi_version"], data["receipt_ref"], data["cycle_ref"],
            material.phase, material.input_refs, material.output_refs,
            material.input_revision_pin, material.output_revision_pin,
            material.disposition, material.rejection_codes,
            material.budget_use, data["duration_ns"],
        )
        if rebuilt.as_dict() != data:
            raise ValueError("non-canonical PhaseReceipt encoding")
        return rebuilt

def _artifact_refs(
    *, orientation: Orientation | None, proposal: "ProposalResult | None", verification: "VerificationBatch | None",
    evaluation: None, effect_receipt: None, response_meaning: None,
    realization_receipt: None, gap_receipt: GapReceipt | None,
) -> dict[str, str | None]:
    orientation_ref = proposal_ref = verification_ref = gap_ref = None
    if orientation is not None:
        if type(orientation) is not Orientation:
            raise TypeError("orientation must be exact Orientation or None")
        if Orientation.from_dict(orientation.as_dict()) != orientation:
            raise ValueError("orientation is not canonical")
        orientation_ref = orientation.orientation_ref
    if proposal is not None:
        from .proposal import ProposalResult
        if type(proposal) is not ProposalResult:
            raise TypeError("proposal must be exact ProposalResult or None")
        if ProposalResult.from_dict(proposal.as_dict()) != proposal:
            raise ValueError("proposal is not canonical")
        proposal_ref = proposal.proposal_ref
    if verification is not None:
        from .verifier import VerificationBatch
        if type(verification) is not VerificationBatch:
            raise TypeError("verification must be exact VerificationBatch or None")
        if VerificationBatch.from_dict(verification.as_dict()) != verification:
            raise ValueError("verification is not canonical")
        verification_ref = verification.batch_ref
    for name, artifact in (
        ("evaluation", evaluation), ("effect_receipt", effect_receipt),
        ("response_meaning", response_meaning),
        ("realization_receipt", realization_receipt),
    ):
        if artifact is not None:
            raise TypeError(f"{name} owner is not admitted for Cycle Result ABI 2")
    if gap_receipt is not None:
        if type(gap_receipt) is not GapReceipt:
            raise TypeError("gap_receipt must be exact GapReceipt or None")
        try:
            canonical_gap = GapReceipt.from_dict(gap_receipt.as_dict())
        except (TypeError, ValueError) as exc:
            raise ValueError("gap_receipt is not canonical") from exc
        if canonical_gap != gap_receipt:
            raise ValueError("gap_receipt is not canonical")
        gap_ref = gap_receipt.gap_ref
    return {
        "orientation_ref": orientation_ref, "proposal_ref": proposal_ref,
        "verification_ref": verification_ref, "evaluation_ref": None,
        "effect_receipt_ref": None, "response_meaning_ref": None,
        "realization_receipt_ref": None, "gap_ref": gap_ref,
    }


def _validate_cycle_state(
    *, input_ref: str, status: CycleStatus,
    orientation: Orientation | None, proposal: "ProposalResult | None", verification: "VerificationBatch | None",
    evaluation: None, effect_receipt: None, response_meaning: None,
    realization_receipt: None, gap_receipt: GapReceipt | None,
    phase_material: tuple[_PhaseMaterial, ...],
    final_revision_pin: RevisionPin,
) -> dict[str, str | None]:
    _cycle_text(input_ref, "input_ref")
    if type(status) is not CycleStatus:
        raise TypeError("status must be CycleStatus")
    if type(phase_material) is not tuple:
        raise TypeError("phase_material must be an exact tuple")
    if not phase_material or len(phase_material) > _CYCLE_MAX_PHASES:
        raise ValueError("phase_material exceeds cycle phase bound or is empty")
    if any(type(row) is not _PhaseMaterial for row in phase_material):
        raise TypeError("phase_material rows must be exact _PhaseMaterial")
    for row in phase_material:
        try:
            rebuilt_row = _PhaseMaterial.from_dict(row.as_dict())
        except (TypeError, ValueError) as exc:
            raise ValueError("phase_material contains a non-canonical row") from exc
        if rebuilt_row != row:
            raise ValueError("phase_material contains a non-canonical row")
    actual = tuple(row.phase for row in phase_material)
    if actual != tuple(SemanticPhase)[:len(phase_material)]:
        raise ValueError("phase_material order must be a unique phase prefix")
    terminal = {
        PhaseDisposition.ABSTAINED,
        PhaseDisposition.REJECTED,
        PhaseDisposition.GAP,
        PhaseDisposition.FAILED,
    }
    if any(row.disposition in terminal for row in phase_material[:-1]):
        raise ValueError("terminal phase disposition cannot precede a later phase")
    if input_ref not in phase_material[0].input_refs:
        raise ValueError("ORIENT material must bind the exact input_ref")
    for previous, current in zip(phase_material, phase_material[1:]):
        if previous.output_revision_pin != current.input_revision_pin:
            raise ValueError("phase revision pin chain is broken")
        if not set(previous.output_refs).issubset(current.input_refs):
            raise ValueError("prior phase output refs must feed the next phase inputs")
    _cycle_pin(final_revision_pin, "final_revision_pin")
    if final_revision_pin != phase_material[-1].output_revision_pin:
        raise ValueError("final_revision_pin must equal the last phase output pin")
    refs = _artifact_refs(
        orientation=orientation, proposal=proposal, verification=verification,
        evaluation=evaluation, effect_receipt=effect_receipt,
        response_meaning=response_meaning,
        realization_receipt=realization_receipt, gap_receipt=gap_receipt,
    )
    requirements = (
        (SemanticPhase.ORIENT, orientation, refs["orientation_ref"]),
        (SemanticPhase.PROPOSE, proposal, refs["proposal_ref"]),
        (SemanticPhase.VERIFY, verification, refs["verification_ref"]),
    )
    for phase, artifact, artifact_ref in requirements:
        index = tuple(SemanticPhase).index(phase)
        if index < len(phase_material):
            if artifact is None or artifact_ref not in phase_material[index].output_refs:
                raise ValueError(f"{phase.value} material lacks its exact artifact")
        elif artifact is not None:
            raise ValueError(f"{phase.value} artifact exists without phase material")
    if proposal is not None and proposal.orientation_ref != orientation.orientation_ref:
        raise ValueError("proposal does not bind the exact orientation")
    if verification is not None and verification.proposal_ref != proposal.proposal_ref:
        raise ValueError("verification does not bind the exact proposal")
    if (
        verification is not None
        and verification.proposal_context_ref != proposal.proposal_context_ref
    ):
        raise ValueError("verification does not bind the exact proposal context")
    if verification is not None:
        verify_row = phase_material[tuple(SemanticPhase).index(SemanticPhase.VERIFY)]
        expected_dispositions = {
            "selected": PhaseDisposition.COMPLETED,
            "abstained": PhaseDisposition.ABSTAINED,
            "rejected": PhaseDisposition.REJECTED,
            "ambiguous": PhaseDisposition.GAP,
        }
        if verify_row.disposition is not expected_dispositions[verification.status]:
            raise ValueError("VERIFY disposition does not match VerificationBatch status")
        expected_proposal_status = (
            "abstained" if verification.status == "abstained" else "candidates"
        )
        if proposal.status != expected_proposal_status:
            raise ValueError("proposal status does not match VerificationBatch status")
        expected_rejection_codes = {
            "selected": (),
            "abstained": (proposal.abstention_code,),
            "rejected": ("verification:rejected",),
            "ambiguous": ("verification:ambiguous",),
        }
        if verify_row.rejection_codes != expected_rejection_codes[verification.status]:
            raise ValueError("VERIFY rejection_codes do not match canonical outcome")
        if verification.status == "ambiguous" and status is not CycleStatus.AMBIGUOUS:
            raise ValueError("ambiguous verification requires ambiguous cycle status")
        if verification.status in {"abstained", "rejected"} and status is not CycleStatus.UNSUPPORTED:
            raise ValueError("non-selected verification requires unsupported cycle status")
        if verification.status == "selected" and status is not CycleStatus.PARTIAL:
            raise ValueError("selected R1 verification requires partial cycle status")
    if status is CycleStatus.RESOLVED:
        raise ValueError("resolved cycles require later ABI-2 owners not yet admitted")
    if gap_receipt is None:
        raise ValueError("non-resolved CycleResult requires a canonical gap receipt")
    if verification is not None and verification.status == "selected":
        meaning = verification.selected_meaning
        if meaning is None:
            raise ValueError("selected verification lacks selected meaning")
        exact_later_gap = (
            gap_receipt.kind is GapKind.IMPLEMENTATION
            and gap_receipt.status == "later_owner_not_admitted"
            and gap_receipt.source_refs == (meaning.verified_meaning_ref,)
            and gap_receipt.blockers == ("later_owner_not_admitted",)
            and gap_receipt.missing_contract_refs == ("contract:r3:evaluate",)
            and gap_receipt.rejected_candidate_refs == ()
            and gap_receipt.recommended_owner is RepairOwner.RUNTIME
            and gap_receipt.safe_response_action == "stop_without_surface"
        )
        if not exact_later_gap:
            raise ValueError("selected verification requires exact LaterOwnerNotAdmitted gap")
    elif gap_receipt.status == "later_owner_not_admitted":
        raise ValueError("LaterOwnerNotAdmitted gap requires selected verification")
    if len(phase_material) > 3:
        raise ValueError("later phase material is disabled until C2 owner admission")
    return refs


def _cycle_identity_material(
    *, input_ref: str, status: CycleStatus,
    refs: Mapping[str, str | None],
    phase_material: tuple[_PhaseMaterial, ...],
    final_revision_pin: RevisionPin,
) -> dict[str, Any]:
    return {
        "abi_version": CYCLE_RESULT_ABI_VERSION, "input_ref": input_ref,
        "orientation_ref": refs["orientation_ref"], "status": status.value,
        "phase_material": [row.as_dict() for row in phase_material],
        "proposal_ref": refs["proposal_ref"],
        "verification_ref": refs["verification_ref"],
        "evaluation_ref": refs["evaluation_ref"],
        "effect_receipt_ref": refs["effect_receipt_ref"],
        "response_meaning_ref": refs["response_meaning_ref"],
        "realization_receipt_ref": refs["realization_receipt_ref"],
        "gap_ref": refs["gap_ref"],
        "final_revision_pin": final_revision_pin.as_dict(),
    }


def _validate_trace(
    trace: tuple[PhaseReceipt, ...],
    phase_material: tuple[_PhaseMaterial, ...],
    cycle_ref: str,
) -> None:
    if type(trace) is not tuple:
        raise TypeError("trace must be an exact tuple")
    if len(trace) > _CYCLE_MAX_PHASES:
        raise ValueError("trace exceeds cycle phase bound")
    if not trace:
        return
    if len(trace) != len(phase_material):
        raise ValueError("trace must cover every serialized phase material")
    for receipt, material in zip(trace, phase_material):
        if type(receipt) is not PhaseReceipt:
            raise TypeError("trace rows must be exact PhaseReceipt")
        try:
            rebuilt_receipt = PhaseReceipt.from_dict(receipt.as_dict())
        except (TypeError, ValueError) as exc:
            raise ValueError("trace contains a non-canonical PhaseReceipt") from exc
        if rebuilt_receipt != receipt:
            raise ValueError("trace contains a non-canonical PhaseReceipt")
        if receipt.cycle_ref != cycle_ref or receipt.material != material:
            raise ValueError("trace does not bind exact cycle semantic material")


@dataclass(frozen=True)
class CycleResult:
    abi_version: int
    cycle_ref: str
    input_ref: str
    status: CycleStatus
    orientation: Orientation | None
    proposal: "ProposalResult | None"
    verification: "VerificationBatch | None"
    evaluation: None
    effect_receipt: None
    response_meaning: None
    realization_receipt: None
    gap_receipt: GapReceipt | None
    phase_material: tuple[_PhaseMaterial, ...]
    trace: tuple[PhaseReceipt, ...]
    final_revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "cycle_ref", "input_ref", "status", "orientation",
        "proposal", "verification", "evaluation", "effect_receipt",
        "response_meaning", "realization_receipt", "gap_receipt",
        "phase_material", "trace", "final_revision_pin",
    })

    def __post_init__(self) -> None:
        if type(self) is not CycleResult:
            raise TypeError("CycleResult requires exact class")
        if type(self.abi_version) is not int or self.abi_version != CYCLE_RESULT_ABI_VERSION:
            raise ValueError("unsupported Cycle Result ABI")
        _cycle_text(self.cycle_ref, "cycle_ref")
        refs = _validate_cycle_state(
            input_ref=self.input_ref, status=self.status,
            orientation=self.orientation, proposal=self.proposal,
            verification=self.verification, evaluation=self.evaluation,
            effect_receipt=self.effect_receipt,
            response_meaning=self.response_meaning,
            realization_receipt=self.realization_receipt,
            gap_receipt=self.gap_receipt,
            phase_material=self.phase_material,
            final_revision_pin=self.final_revision_pin,
        )
        expected = stable_ref(
            "cycle", _cycle_identity_material(
                input_ref=self.input_ref, status=self.status, refs=refs,
                phase_material=self.phase_material,
                final_revision_pin=self.final_revision_pin,
            ),
        )
        if self.cycle_ref != expected:
            raise ValueError("CycleResult cycle ref mismatch")
        _validate_trace(self.trace, self.phase_material, self.cycle_ref)


    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "cycle_ref": self.cycle_ref,
            "input_ref": self.input_ref, "status": self.status.value,
            "orientation": self.orientation.as_dict() if self.orientation is not None else None,
            "proposal": self.proposal.as_dict() if self.proposal is not None else None,
            "verification": self.verification.as_dict() if self.verification is not None else None,
            "evaluation": None, "effect_receipt": None,
            "response_meaning": None, "realization_receipt": None,
            "gap_receipt": self.gap_receipt.as_dict() if self.gap_receipt is not None else None,
            "phase_material": [row.as_dict() for row in self.phase_material],
            "trace": [row.as_dict() for row in self.trace],
            "final_revision_pin": self.final_revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CycleResult":
        if cls is not CycleResult:
            raise TypeError("CycleResult codec requires exact class")
        data = _exact_wire_dict(value, cls._FIELDS, "CycleResult")
        if type(data["abi_version"]) is not int or data["abi_version"] != CYCLE_RESULT_ABI_VERSION:
            raise ValueError("unsupported Cycle Result ABI")
        if type(data["status"]) is not str:
            raise TypeError("status wire value must be exact str")
        for name in ("phase_material", "trace"):
            if type(data[name]) is not list:
                raise TypeError(f"{name} wire value must be an exact list")
            if len(data[name]) > _CYCLE_MAX_PHASES:
                raise ValueError(f"{name} exceeds cycle phase bound")
        from .proposal import ProposalResult
        from .verifier import VerificationBatch
        orientation = None if data["orientation"] is None else Orientation.from_dict(data["orientation"])
        proposal = None if data["proposal"] is None else ProposalResult.from_dict(data["proposal"])
        verification = None if data["verification"] is None else VerificationBatch.from_dict(data["verification"])
        for name in ("evaluation", "effect_receipt", "response_meaning", "realization_receipt"):
            if data[name] is not None:
                raise TypeError(f"{name} owner is not admitted for Cycle Result ABI 2")
        gap = None if data["gap_receipt"] is None else GapReceipt.from_dict(data["gap_receipt"])
        if type(data["final_revision_pin"]) is not dict:
            raise TypeError("final_revision_pin must be an exact dict")
        rebuilt = cls(
            data["abi_version"], data["cycle_ref"], data["input_ref"],
            CycleStatus(data["status"]), orientation, proposal, verification,
            None, None, None, None, gap,
            tuple(_PhaseMaterial.from_dict(row) for row in data["phase_material"]),
            tuple(PhaseReceipt.from_dict(row) for row in data["trace"]),
            RevisionPin.from_dict(data["final_revision_pin"]),
        )
        if rebuilt.as_dict() != data:
            raise ValueError("non-canonical CycleResult encoding")
        return rebuilt

class CycleFinalizer:
    @classmethod
    def finalize(
        cls, *, input_ref: str, status: CycleStatus,
        orientation: Orientation | None, proposal: "ProposalResult | None", verification: "VerificationBatch | None",
        evaluation: None, effect_receipt: None, response_meaning: None,
        realization_receipt: None, gap_receipt: GapReceipt | None,
        phase_material: tuple[_PhaseMaterial, ...],
        final_revision_pin: RevisionPin, capture_trace: bool,
        durations_ns: tuple[int | None, ...],
    ) -> CycleResult:
        if cls is not CycleFinalizer:
            raise TypeError("CycleFinalizer requires exact canonical owner")
        if type(capture_trace) is not bool:
            raise TypeError("capture_trace must be exact bool")
        if type(durations_ns) is not tuple:
            raise TypeError("durations_ns must be an exact tuple")
        if len(durations_ns) > _CYCLE_MAX_PHASES:
            raise ValueError("durations_ns exceeds cycle phase bound")
        if len(durations_ns) != len(phase_material):
            raise ValueError("durations_ns must align with phase_material")
        durations = tuple(_cycle_duration(row) for row in durations_ns)
        refs = _validate_cycle_state(
            input_ref=input_ref, status=status, orientation=orientation,
            proposal=proposal, verification=verification,
            evaluation=evaluation, effect_receipt=effect_receipt,
            response_meaning=response_meaning,
            realization_receipt=realization_receipt,
            gap_receipt=gap_receipt, phase_material=phase_material,
            final_revision_pin=final_revision_pin,
        )
        cycle_ref = stable_ref(
            "cycle", _cycle_identity_material(
                input_ref=input_ref, status=status, refs=refs,
                phase_material=phase_material,
                final_revision_pin=final_revision_pin,
            ),
        )
        trace = (
            tuple(
                PhaseReceipt.create(
                    cycle_ref=cycle_ref, material=material, duration_ns=duration
                )
                for material, duration in zip(phase_material, durations)
            )
            if capture_trace else ()
        )
        return CycleResult(
            CYCLE_RESULT_ABI_VERSION,
            cycle_ref,
            input_ref,
            status,
            orientation,
            proposal,
            verification,
            evaluation,
            effect_receipt,
            response_meaning,
            realization_receipt,
            gap_receipt,
            phase_material,
            trace,
            final_revision_pin,
        )
