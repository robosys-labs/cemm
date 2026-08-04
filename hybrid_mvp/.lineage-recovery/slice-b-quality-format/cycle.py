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

from dataclasses import dataclass, field
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
from .gaps import GapReceipt
from .persistence import RevisionPin, memory_stores

if TYPE_CHECKING:
    from .effects import EffectReceipt
    from .dialogue import FocusStore, DialogueObligationManager

__all__ = [
    "SemanticMode",
    "CycleStatus",
    "SemanticPhase",
    "ORIENTATION_ABI_VERSION",
    "Orientation",
    "OrientationProjector",
    "PhaseReceipt",
    "KernelCycleResult",
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

    _FIELDS = frozenset(
        {
            "abi_version",
            "orientation_ref",
            "session_ref",
            "turn_ref",
            "source_text",
            "mode",
            "participant_frame",
            "temporal_frame",
            "participants",
            "active_turn_ref",
            "event_refs",
            "focus_refs",
            "obligation_refs",
            "capability_summary",
            "permission_summary",
            "budgets",
            "scanned_atom_count",
            "index_probes",
            "visited_refs",
            "revision_pin",
        }
    )
    _TUPLE_FIELDS = (
        "participants",
        "event_refs",
        "focus_refs",
        "obligation_refs",
        "capability_summary",
        "permission_summary",
        "index_probes",
        "visited_refs",
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
            session_ref=self.session_ref,
            turn_ref=self.turn_ref,
            source_text=self.source_text,
            mode=self.mode,
            participant_frame=self.participant_frame,
            temporal_frame=self.temporal_frame,
            participants=self.participants,
            active_turn_ref=self.active_turn_ref,
            event_refs=self.event_refs,
            focus_refs=self.focus_refs,
            obligation_refs=self.obligation_refs,
            capability_summary=self.capability_summary,
            permission_summary=self.permission_summary,
            budgets=self.budgets,
            scanned_atom_count=self.scanned_atom_count,
            index_probes=self.index_probes,
            visited_refs=self.visited_refs,
            revision_pin=self.revision_pin,
        )
        object.__setattr__(self, "budgets", frozen_budgets)
        if self.orientation_ref != stable_ref("orientation", material):
            raise ValueError("Orientation ref mismatch")

    @classmethod
    def create(
        cls,
        *,
        session_ref: str,
        turn_ref: str,
        source_text: str,
        mode: SemanticMode,
        participant_frame: str,
        temporal_frame: str,
        participants: tuple[str, ...],
        active_turn_ref: str,
        event_refs: tuple[str, ...],
        focus_refs: tuple[str, ...],
        obligation_refs: tuple[str, ...],
        capability_summary: tuple[str, ...],
        permission_summary: tuple[str, ...],
        budgets: Mapping[str, int],
        scanned_atom_count: int,
        index_probes: tuple[str, ...],
        visited_refs: tuple[str, ...],
        revision_pin: RevisionPin,
        cache_key: str | None = None,
    ) -> "Orientation":
        if cls is not Orientation:
            raise TypeError("Orientation factories require exact Orientation")
        if cache_key is not None:
            _orientation_text(cache_key, "cache_key")
        material, frozen_budgets = cls._material(
            session_ref=session_ref,
            turn_ref=turn_ref,
            source_text=source_text,
            mode=mode,
            participant_frame=participant_frame,
            temporal_frame=temporal_frame,
            participants=participants,
            active_turn_ref=active_turn_ref,
            event_refs=event_refs,
            focus_refs=focus_refs,
            obligation_refs=obligation_refs,
            capability_summary=capability_summary,
            permission_summary=permission_summary,
            budgets=budgets,
            scanned_atom_count=scanned_atom_count,
            index_probes=index_probes,
            visited_refs=visited_refs,
            revision_pin=revision_pin,
        )
        value = object.__new__(cls)
        values = {
            "abi_version": ORIENTATION_ABI_VERSION,
            "orientation_ref": stable_ref("orientation", material),
            "session_ref": session_ref,
            "turn_ref": turn_ref,
            "source_text": source_text,
            "mode": mode,
            "participant_frame": participant_frame,
            "temporal_frame": temporal_frame,
            "participants": participants,
            "active_turn_ref": active_turn_ref,
            "event_refs": event_refs,
            "focus_refs": focus_refs,
            "obligation_refs": obligation_refs,
            "capability_summary": capability_summary,
            "permission_summary": permission_summary,
            "budgets": frozen_budgets,
            "scanned_atom_count": scanned_atom_count,
            "index_probes": index_probes,
            "visited_refs": visited_refs,
            "revision_pin": revision_pin,
            "cache_key": cache_key,
        }
        for name, item in values.items():
            object.__setattr__(value, name, item)
        return value

    @staticmethod
    def _material(
        *,
        session_ref: str,
        turn_ref: str,
        source_text: str,
        mode: SemanticMode,
        participant_frame: str,
        temporal_frame: str,
        participants: tuple[str, ...],
        active_turn_ref: str,
        event_refs: tuple[str, ...],
        focus_refs: tuple[str, ...],
        obligation_refs: tuple[str, ...],
        capability_summary: tuple[str, ...],
        permission_summary: tuple[str, ...],
        budgets: Mapping[str, int],
        scanned_atom_count: int,
        index_probes: tuple[str, ...],
        visited_refs: tuple[str, ...],
        revision_pin: RevisionPin,
    ) -> tuple[dict[str, Any], Mapping[str, int]]:
        for name, value in (
            ("session_ref", session_ref),
            ("turn_ref", turn_ref),
            ("participant_frame", participant_frame),
            ("temporal_frame", temporal_frame),
            ("active_turn_ref", active_turn_ref),
        ):
            _orientation_text(value, name)
        _orientation_text(source_text, "source_text", allow_empty=True)
        if type(mode) is not SemanticMode:
            raise TypeError("mode must be SemanticMode")
        for name, value in (
            ("participants", participants),
            ("event_refs", event_refs),
            ("focus_refs", focus_refs),
            ("obligation_refs", obligation_refs),
            ("capability_summary", capability_summary),
            ("permission_summary", permission_summary),
            ("index_probes", index_probes),
            ("visited_refs", visited_refs),
        ):
            _orientation_tuple(value, name)
        frozen_budgets = _orientation_budgets(budgets)
        if type(scanned_atom_count) is not int:
            raise TypeError("scanned_atom_count must be exact int")
        if not 0 <= scanned_atom_count <= _ORIENTATION_MAX_SCANNED_ATOMS:
            raise ValueError("scanned_atom_count exceeds configured bound")
        if type(revision_pin) is not RevisionPin:
            raise TypeError("revision_pin must be RevisionPin")
        material = {
            "abi_version": ORIENTATION_ABI_VERSION,
            "session_ref": session_ref,
            "turn_ref": turn_ref,
            "source_text": source_text,
            "mode": mode.value,
            "participant_frame": participant_frame,
            "temporal_frame": temporal_frame,
            "participants": list(participants),
            "active_turn_ref": active_turn_ref,
            "event_refs": list(event_refs),
            "focus_refs": list(focus_refs),
            "obligation_refs": list(obligation_refs),
            "capability_summary": list(capability_summary),
            "permission_summary": list(permission_summary),
            "budgets": dict(frozen_budgets),
            "scanned_atom_count": scanned_atom_count,
            "index_probes": list(index_probes),
            "visited_refs": list(visited_refs),
            "revision_pin": revision_pin.as_dict(),
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
            session_ref=data["session_ref"],
            turn_ref=data["turn_ref"],
            source_text=data["source_text"],
            mode=mode,
            participant_frame=data["participant_frame"],
            temporal_frame=data["temporal_frame"],
            participants=tuples["participants"],
            active_turn_ref=data["active_turn_ref"],
            event_refs=tuples["event_refs"],
            focus_refs=tuples["focus_refs"],
            obligation_refs=tuples["obligation_refs"],
            capability_summary=tuples["capability_summary"],
            permission_summary=tuples["permission_summary"],
            budgets=data["budgets"],
            scanned_atom_count=data["scanned_atom_count"],
            index_probes=tuples["index_probes"],
            visited_refs=tuples["visited_refs"],
            revision_pin=RevisionPin.from_dict(data["revision_pin"]),
            cache_key=None,
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
        participant_refs = sorted(self._authority.by_kind("participant"))
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
        cap_summary = tuple(self._authority.capabilities.get("participant:system", []))
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

        return [w.lower() for w in re.findall(r"[A-Za-z]+", text)]

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
# Phase receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhaseReceipt:
    """A receipt for one completed phase of the six-phase kernel.

    The cycle always transfers phase artifacts but stores serialized
    ``PhaseReceipt`` rows only for ``trace=True``, evaluation capture, or a
    durable effect.
    """

    cycle_ref: str
    phase: str
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    revision_pin: RevisionPin
    budget_use: Mapping[str, int]
    status: str
    rejection_codes: tuple[str, ...] = ()
    duration_ns: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "cycle_ref": self.cycle_ref,
            "phase": self.phase,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "revision_pin": self.revision_pin.as_dict(),
            "budget_use": dict(self.budget_use),
            "status": self.status,
            "rejection_codes": list(self.rejection_codes),
            "duration_ns": self.duration_ns,
        }


# ---------------------------------------------------------------------------
# Kernel cycle result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KernelCycleResult:
    """The kernel-level result of one six-phase cycle.

    ``phase_output_refs`` maps each :class:`SemanticPhase` to the artifact refs
    produced by that phase. ``trace`` holds serialized ``PhaseReceipt`` rows
    only when trace collection was enabled; it is empty otherwise.
    ``effect_receipt`` carries the idempotent receipt from the EFFECT phase's
    :class:`EffectGateway` when one proof-bearing gateway owns all effectful
    commits.
    """

    cycle_ref: str
    status: CycleStatus
    phase_output_refs: Mapping[SemanticPhase, tuple[str, ...]]
    gap_receipt: GapReceipt | None
    trace: tuple[PhaseReceipt, ...]
    final_revision_pin: RevisionPin
    effect_receipt: "EffectReceipt | None" = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "cycle_ref": self.cycle_ref,
            "status": self.status.value,
            "phase_output_refs": {
                phase.value: list(refs)
                for phase, refs in self.phase_output_refs.items()
            },
            "gap_receipt": self.gap_receipt.as_dict()
            if self.gap_receipt is not None
            else None,
            "trace": [receipt.as_dict() for receipt in self.trace],
            "final_revision_pin": self.final_revision_pin.as_dict(),
            "effect_receipt": _effect_receipt_as_dict(self.effect_receipt),
        }


@dataclass(frozen=True)
class CycleResult:
    """The finalized user-facing cycle result.

    Carries all six phase artifacts forward as immutable fields:
    orientation, proposal, verification, evaluation, effect receipt,
    response meaning, and realization receipt. ``KernelCycleResult``
    remains an internal typed-fixture test artifact and is not exported
    by the release runtime.

    Fields default to ``None``/empty so that early-exit paths (e.g. a
    verification failure that stops before EVALUATE) can still construct
    a valid ``CycleResult``.
    """

    cycle_ref: str
    status: CycleStatus
    final_revision_pin: RevisionPin
    orientation: Any = None  # Orientation
    proposal: Any = None  # ProposalResult
    verification: Any = None  # VerificationResult
    evaluation: Any = None  # EvaluationResult (typed Decision)
    effect_receipt: Any = None  # EffectReceipt | None
    response_meaning: Any = None  # ResponseMeaning | None
    realization_receipt: Any = None  # RealizationReceipt | None
    gap_receipt: GapReceipt | None = None
    trace: tuple[PhaseReceipt, ...] = ()

    _phase_output_refs: Mapping[SemanticPhase, tuple[str, ...]] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        if type(self.final_revision_pin) is not RevisionPin:
            raise TypeError("final_revision_pin must be RevisionPin")

    @property
    def kernel(self) -> KernelCycleResult:
        """Construct an internal ``KernelCycleResult`` view (backward compat)."""
        return KernelCycleResult(
            cycle_ref=self.cycle_ref,
            status=self.status,
            phase_output_refs=dict(self._phase_output_refs),
            gap_receipt=self.gap_receipt,
            trace=self.trace,
            final_revision_pin=self.final_revision_pin,
            effect_receipt=self.effect_receipt,
        )

    @property
    def phase_output_refs(self) -> Mapping[SemanticPhase, tuple[str, ...]]:
        return self._phase_output_refs

    def as_dict(self) -> dict[str, Any]:
        return {
            "cycle_ref": self.cycle_ref,
            "status": self.status.value,
            "phase_output_refs": {
                phase.value: list(refs)
                for phase, refs in self._phase_output_refs.items()
            },
            "gap_receipt": self.gap_receipt.as_dict()
            if self.gap_receipt is not None
            else None,
            "trace": [receipt.as_dict() for receipt in self.trace],
            "final_revision_pin": self.final_revision_pin.as_dict(),
            "effect_receipt": _effect_receipt_as_dict(self.effect_receipt),
        }


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _effect_receipt_as_dict(receipt: "EffectReceipt | None") -> dict[str, Any] | None:
    if receipt is None:
        return None
    return {
        "effect_ref": receipt.effect_ref,
        "status": receipt.status,
        "world_revision": receipt.world_revision,
        "proof_refs": list(receipt.proof_refs),
        "adapter_receipt_ref": receipt.adapter_receipt_ref,
    }


# ---------------------------------------------------------------------------
# Test-only fixture cycle runner
# ---------------------------------------------------------------------------


class _FixtureCycleRunner:
    """A minimal cycle runner for tests.

    Produces a deterministic :class:`KernelCycleResult` with all six named
    phases in the trace (when ``trace=True``), status ``resolved`` and a valid
    ``RevisionPin`` sourced from an in-memory store. This is a test fixture
    only; it does not run the full semantic runtime.
    """

    _PHASES = tuple(SemanticPhase)

    def run(self, *, trace: bool = False) -> KernelCycleResult:
        stores = memory_stores(authority_generation="authority:generation-test")
        try:
            pin = stores.revision_pin()
            cycle_ref = "cycle:fixture"
            phase_output_refs: dict[SemanticPhase, tuple[str, ...]] = {}
            trace_rows: tuple[PhaseReceipt, ...] = ()
            if trace:
                rows: list[PhaseReceipt] = []
                for phase in self._PHASES:
                    output_ref = f"artifact:{phase.value.lower()}"
                    phase_output_refs[phase] = (output_ref,)
                    rows.append(
                        PhaseReceipt(
                            cycle_ref=cycle_ref,
                            phase=phase.value,
                            input_refs=(),
                            output_refs=(output_ref,),
                            revision_pin=pin,
                            budget_use={"tokens": 1},
                            status="ok",
                        )
                    )
                trace_rows = tuple(rows)
            else:
                for phase in self._PHASES:
                    phase_output_refs[phase] = (f"artifact:{phase.value.lower()}",)
            return KernelCycleResult(
                cycle_ref=cycle_ref,
                status=CycleStatus.RESOLVED,
                phase_output_refs=phase_output_refs,
                gap_receipt=None,
                trace=trace_rows,
                final_revision_pin=pin,
            )
        finally:
            stores.close()
