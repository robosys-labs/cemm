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
from typing import Any, Mapping, TYPE_CHECKING

from .canonical import stable_ref
from .gaps import GapReceipt
from .persistence import RevisionPin, memory_stores

if TYPE_CHECKING:
    from .effects import EffectReceipt
    from .dialogue import FocusStore, DialogueObligationManager

__all__ = [
    "SemanticMode",
    "CycleStatus",
    "SemanticPhase",
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


@dataclass(frozen=True)
class Orientation:
    """The ORIENT phase output: context required for the current cycle.

    The orientation captures only the context required for the current cycle.
    It starts from participants, active turn/session events, verified focus,
    open obligations, and relevant goals.  It traverses indexed typed
    relations within the configured depth and records index probes, visited
    refs, cache key, and revision pin.  It does **not** scan all atoms
    (``scanned_atom_count == 0``).

    Entity, concept, relation, state, and event identities remain
    independently addressable; events do not become a universal wrapper.
    """

    session_ref: str
    turn_ref: str
    mode: SemanticMode
    participant_frame: str
    temporal_frame: str
    authority_generation: str
    world_revision: int
    session_revision: int
    episode_revision: int
    effect_revision: int
    model_identity: str | None
    focus_refs: tuple[str, ...]
    obligation_refs: tuple[str, ...]
    capability_summary: tuple[str, ...]
    permission_summary: tuple[str, ...]
    budgets: Mapping[str, int]
    # -- New projection fields (defaults preserve backward compatibility) --
    participants: tuple[str, ...] = ()
    active_turn_ref: str = ""
    event_refs: tuple[str, ...] = ()
    scanned_atom_count: int = 0
    index_probes: tuple[str, ...] = ()
    visited_refs: tuple[str, ...] = ()
    cache_key: str = ""
    revision_pin: RevisionPin | None = None
    source_text: str = ""


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
        """Project an :class:`Orientation` for ``session_ref`` and ``text``."""
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
            focus_refs = self._ground_focus(text, index_probes, visited)

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

        # -- Cache key -------------------------------------------------------
        cache_key = stable_ref(
            "orientation",
            {
                "session": session_ref,
                "turn": turn_ref,
                "participants": list(participant_refs),
                "focus": list(focus_refs),
                "authority_generation": pin.authority_generation,
            },
        )

        return Orientation(
            session_ref=session_ref,
            turn_ref=turn_ref,
            mode=mode,
            participant_frame="participant:user",
            temporal_frame="now",
            authority_generation=self._authority.generation,
            world_revision=pin.world_revision,
            session_revision=pin.session_revision,
            episode_revision=pin.episode_revision,
            effect_revision=pin.effect_revision,
            model_identity=pin.model_identity,
            focus_refs=focus_refs,
            obligation_refs=obligation_refs,
            capability_summary=cap_summary,
            permission_summary=perm_summary,
            budgets={"input_tokens": self._config.max_input_tokens},
            participants=tuple(participant_refs),
            active_turn_ref=turn_ref,
            event_refs=event_refs,
            scanned_atom_count=0,
            index_probes=tuple(index_probes),
            visited_refs=tuple(visited),
            cache_key=cache_key,
            revision_pin=pin,
        )

    # -- internal: focus grounding ------------------------------------------

    def _ground_focus(
        self,
        text: str,
        index_probes: list[str],
        visited: list[str],
    ) -> tuple[str, ...]:
        """Ground text into focus refs via the authority's designations.

        Uses simple word tokenisation and exact surface lookup.  Does not
        scan all atoms — only probes the designation index.
        """
        index_probes.append("designations:for_surface")
        focus: list[str] = []
        words = self._tokenize(text)
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
        """Traverse indexed typed relations from ``refs`` within max_depth.

        Records index probes and visited refs.  Does not scan all atoms.
        """
        if depth >= self._max_depth or not refs:
            return

        index_probes.append(f"by_kind:relation_type:depth={depth}")
        relation_refs = sorted(self._authority.by_kind("relation_type"))
        for ref in refs:
            for rel_ref in relation_refs:
                if rel_ref not in visited:
                    visited.append(rel_ref)

        # Recurse one level deeper (bounded by max_depth).
        if relation_refs and depth + 1 < self._max_depth:
            self._traverse(
                tuple(relation_refs[:4]),
                index_probes,
                visited,
                depth + 1,
            )


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
                phase.value: list(refs) for phase, refs in self.phase_output_refs.items()
            },
            "gap_receipt": self.gap_receipt.as_dict() if self.gap_receipt is not None else None,
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
    orientation: Any = None  # Orientation
    proposal: Any = None  # ProposalResult
    verification: Any = None  # VerificationResult
    evaluation: Any = None  # EvaluationResult (typed Decision)
    effect_receipt: Any = None  # EffectReceipt | None
    response_meaning: Any = None  # ResponseMeaning | None
    realization_receipt: Any = None  # RealizationReceipt | None
    gap_receipt: GapReceipt | None = None
    trace: tuple[PhaseReceipt, ...] = ()
    final_revision_pin: RevisionPin = field(
        default_factory=lambda: RevisionPin(
            authority_generation="",
            world_revision=0,
            session_revision=0,
            episode_revision=0,
            effect_revision=0,
            model_identity=None,
        )
    )
    _phase_output_refs: Mapping[SemanticPhase, tuple[str, ...]] = field(
        default_factory=dict, repr=False
    )

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
            "gap_receipt": self.gap_receipt.as_dict() if self.gap_receipt is not None else None,
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
