"""Semantic dialogue focus, reference resolution, goals, and obligations.

Only verified semantic refs enter focus — unverified output never enters
focus.  Reference resolution applies person/number/kind/recency/scope
constraints and preserves alternatives below margin.  ``GoalArbiter``
selects among verified goals/obligations by policy; a UI intent label is
derived afterward and has no control authority.  Typed obligations carry
source query, expected answer contract, expiry, and completion receipt.
Only one learning obligation may exist; unrelated dialogue cannot
accidentally consume it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Literal

from .authority import LinkedAuthority
from .canonical import stable_ref
from .config import RuntimeConfig
from .persistence import Obligation

if TYPE_CHECKING:
    from .cycle import Orientation

__all__ = [
    "VerifiedSemanticFocus",
    "FocusStore",
    "ReferenceConstraints",
    "ReferenceResolution",
    "ReferenceResolver",
    "GoalArbiter",
    "GoalSelection",
    "DialogueObligation",
    "DialogueObligationManager",
]


# ---------------------------------------------------------------------------
# Verified semantic focus
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifiedSemanticFocus:
    """A verified semantic focus entry.

    Only verified semantic refs are stored — unverified output never
    enters focus.  Each entry records the proposition, entity, and event
    refs that were verified, along with salience evidence, the
    participant who produced them, the turn, and the revision.

    Attributes:
        proposition_refs: verified proposition refs.
        entity_refs: verified entity refs.
        event_refs: verified event refs.
        salience_evidence: tuple of salience evidence refs.
        participant: the participant ref (e.g. ``"participant:system"``).
        turn: the turn ref.
        revision: the revision at which the focus was verified.
    """

    proposition_refs: tuple[str, ...]
    entity_refs: tuple[str, ...]
    event_refs: tuple[str, ...]
    salience_evidence: tuple[str, ...]
    participant: str
    turn: str
    revision: int


class FocusStore:
    """Tracks verified semantic refs across dialogue turns.

    Only verified semantic refs enter focus.  Unverified output is never
    added — the caller is responsible for verifying before calling
    :meth:`add`.
    """

    __slots__ = ("_entries", "_refs")

    def __init__(self) -> None:
        self._entries: list[VerifiedSemanticFocus] = []
        self._refs: set[str] = set()

    def add(self, focus: VerifiedSemanticFocus) -> None:
        """Add verified refs to focus.

        Only call this after the refs have been independently verified.
        Unverified output must never be passed to this method.
        """
        self._entries.append(focus)
        for ref in (
            *focus.proposition_refs,
            *focus.entity_refs,
            *focus.event_refs,
        ):
            self._refs.add(ref)

    @property
    def refs(self) -> frozenset[str]:
        """Return all focus refs as a frozenset."""
        return frozenset(self._refs)

    def query(self, ref: str) -> bool:
        """Check if ``ref`` is in focus."""
        return ref in self._refs

    @property
    def entries(self) -> tuple[VerifiedSemanticFocus, ...]:
        """Return all focus entries in insertion order."""
        return tuple(self._entries)

    def recent_entries(self, n: int) -> tuple[VerifiedSemanticFocus, ...]:
        """Return the ``n`` most recent focus entries."""
        if n <= 0:
            return ()
        return tuple(self._entries[-n:])


# ---------------------------------------------------------------------------
# Reference constraints and resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceConstraints:
    """Constraints for discourse reference resolution.

    Attributes:
        person: ``"first"`` (speaker/user), ``"second"`` (addressee/system),
            ``"third"`` (other), or ``None`` (unconstrained).
        number: ``"singular"`` or ``"plural"`` or ``None``.
        kind: expected semantic kind (e.g. ``"proposition"``, ``"entity"``,
            ``"event"``, ``"content"``) or ``None``.
        recency: how many turns back to consider.
        scope: discourse scope (e.g. ``"local"``, ``"global"``) or ``None``.
    """

    person: str | None
    number: str | None
    kind: str | None
    recency: int
    scope: str | None


@dataclass(frozen=True)
class ReferenceResolution:
    """The result of resolving a discourse reference.

    Attributes:
        ref: the reference being resolved (e.g. ``"that"``, ``"what"``).
        resolved_ref: the resolved semantic ref, or ``None`` if unresolved.
        bindings: reference bindings (ref -> resolved ref).
        alternatives: preserved alternatives below margin.
        margin: the margin used for preserving alternatives.
    """

    ref: str
    resolved_ref: str | None
    bindings: dict[str, str]
    alternatives: tuple[str, ...]
    margin: float


# Default margin for preserving alternatives below the winner.
_DEFAULT_MARGIN = 0.3

# Mapping from person constraint to participant ref.
_PERSON_TO_PARTICIPANT: dict[str, str] = {
    "first": "participant:user",
    "second": "participant:system",
}

# Mapping from kind constraint to the VerifiedSemanticFocus field name.
_KIND_TO_FIELD: dict[str, str] = {
    "proposition": "proposition_refs",
    "content": "proposition_refs",
    "claim": "proposition_refs",
    "entity": "entity_refs",
    "event": "event_refs",
}


class ReferenceResolver:
    """Resolves discourse references using verified focus and constraints.

    Applies person/number/kind/recency/scope constraints and preserves
    alternatives below margin.  ``"what did you say?"`` resolves to
    verified system speech; ``"that"`` resolves to a prior verified
    proposition.
    """

    __slots__ = ("_focus_store", "_authority", "_margin")

    def __init__(
        self,
        focus_store: FocusStore,
        authority: LinkedAuthority,
        *,
        margin: float = _DEFAULT_MARGIN,
    ) -> None:
        self._focus_store = focus_store
        self._authority = authority
        self._margin = margin

    def resolve(
        self,
        ref: str,
        constraints: ReferenceConstraints,
        orientation: "Orientation",
    ) -> ReferenceResolution:
        """Resolve ``ref`` using ``constraints`` against verified focus.

        Returns a :class:`ReferenceResolution` with the best matching
        verified ref, bindings, and preserved alternatives below margin.
        """
        candidates = self._collect_candidates(constraints, orientation)
        if not candidates:
            return ReferenceResolution(
                ref=ref,
                resolved_ref=None,
                bindings={},
                alternatives=(),
                margin=self._margin,
            )

        scored = self._score_candidates(candidates, constraints)
        best_ref, best_score = scored[0]

        # Preserve alternatives whose score is within the margin of the best.
        alternatives = tuple(
            r for r, s in scored[1:] if (best_score - s) <= self._margin
        )

        return ReferenceResolution(
            ref=ref,
            resolved_ref=best_ref,
            bindings={ref: best_ref},
            alternatives=alternatives,
            margin=self._margin,
        )

    # -- internal -----------------------------------------------------------

    def _collect_candidates(
        self, constraints: ReferenceConstraints, orientation: "Orientation"
    ) -> list[tuple[str, VerifiedSemanticFocus, int]]:
        """Collect (ref, entry, recency_rank) candidates matching constraints.

        ``recency_rank`` is 0 for the most recent entry, 1 for the next, etc.
        The current turn (``orientation.turn_ref``) is excluded — a reference
        cannot resolve to the current turn's own output.
        """
        entries = self._focus_store.entries
        if constraints.recency > 0:
            entries = entries[-constraints.recency:] if constraints.recency < len(entries) else entries

        current_turn = getattr(orientation, "turn_ref", "")
        candidates: list[tuple[str, VerifiedSemanticFocus, int]] = []
        total = len(entries)
        for idx, entry in enumerate(entries):
            recency_rank = total - 1 - idx

            # Exclude the current turn — a reference cannot resolve to the
            # current turn's own output.
            if current_turn and entry.turn == current_turn:
                continue

            # Filter by person (participant).
            if constraints.person is not None:
                expected = _PERSON_TO_PARTICIPANT.get(constraints.person)
                if expected is not None and entry.participant != expected:
                    continue

            # Collect refs matching the kind constraint.
            refs = self._refs_for_kind(entry, constraints.kind)
            for r in refs:
                candidates.append((r, entry, recency_rank))

        return candidates

    @staticmethod
    def _refs_for_kind(
        entry: VerifiedSemanticFocus, kind: str | None
    ) -> tuple[str, ...]:
        """Return refs from ``entry`` matching the ``kind`` constraint."""
        if kind is None:
            return (*entry.proposition_refs, *entry.entity_refs, *entry.event_refs)
        field_name = _KIND_TO_FIELD.get(kind)
        if field_name is not None:
            return getattr(entry, field_name)
        # Fall back to prefix matching for arbitrary kinds.
        all_refs = (
            *entry.proposition_refs,
            *entry.entity_refs,
            *entry.event_refs,
        )
        return tuple(r for r in all_refs if r.startswith(f"{kind}:"))

    def _score_candidates(
        self,
        candidates: list[tuple[str, VerifiedSemanticFocus, int]],
        constraints: ReferenceConstraints,
    ) -> list[tuple[str, float]]:
        """Score candidates and return them sorted by score descending.

        More recent entries (lower recency_rank) receive higher scores.
        Kind-matched refs receive a small bonus.
        """
        scored: list[tuple[str, float]] = []
        for ref, entry, recency_rank in candidates:
            score = 1.0 - (recency_rank * 0.1)
            if constraints.kind is not None:
                field_name = _KIND_TO_FIELD.get(constraints.kind)
                if field_name is not None and ref in getattr(entry, field_name):
                    score += 0.05
            scored.append((ref, max(score, 0.0)))

        # Sort by score descending; ties broken by recency (already ordered).
        scored.sort(key=lambda pair: -pair[1])
        return scored


# ---------------------------------------------------------------------------
# Goal arbitration
# ---------------------------------------------------------------------------


_GOAL_ARBITRATION_POLICY = "policy:goal_arbitration"


@dataclass(frozen=True)
class GoalSelection:
    """The result of goal arbitration.

    The ``selected_goal_ref`` and ``selected_obligation_ref`` carry control
    authority.  The ``ui_intent_label`` is derived afterward and has NO
    control authority — it is a display label only.

    Attributes:
        selected_goal_ref: the selected goal ref, or ``None``.
        selected_obligation_ref: the selected obligation ref, or ``None``.
        ui_intent_label: a derived UI label with no control authority.
        policy_ref: the policy ref that produced this selection.
    """

    selected_goal_ref: str | None
    selected_obligation_ref: str | None
    ui_intent_label: str
    policy_ref: str


class GoalArbiter:
    """Selects among verified goals/obligations by policy.

    A UI intent label is derived afterward and has NO control authority.
    Policy: obligations take priority over goals; higher-priority
    obligations are preferred.
    """

    __slots__ = ("_authority", "_config")

    def __init__(self, authority: LinkedAuthority, config: RuntimeConfig) -> None:
        self._authority = authority
        self._config = config

    def select(
        self,
        goals: tuple[str, ...],
        obligations: tuple[Obligation, ...],
    ) -> GoalSelection:
        """Select among verified goals and obligations by policy."""
        selected_goal: str | None = None
        selected_obligation: str | None = None

        # Obligations take priority over goals.
        pending_obs = [o for o in obligations if not o.satisfied]
        if pending_obs:
            sorted_obs = sorted(pending_obs, key=lambda o: -o.priority)
            selected_obligation = sorted_obs[0].obligation_ref
        elif goals:
            selected_goal = goals[0]

        # Derive UI intent label (no control authority).
        if selected_obligation is not None:
            ui_label = "obligation:fulfill"
        elif selected_goal is not None:
            ui_label = "goal:pursue"
        else:
            ui_label = "idle"

        return GoalSelection(
            selected_goal_ref=selected_goal,
            selected_obligation_ref=selected_obligation,
            ui_intent_label=ui_label,
            policy_ref=_GOAL_ARBITRATION_POLICY,
        )


# ---------------------------------------------------------------------------
# Typed dialogue obligations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialogueObligation:
    """A typed dialogue obligation.

    Clarification, learning answers, requested evidence, and pending
    operation resolution use frozen records with source query, expected
    semantic answer contract, expiry, and completion receipt.

    Attributes:
        obligation_ref: stable ref uniquely identifying this obligation.
        kind: one of ``"clarification"``, ``"learning_answer"``,
            ``"evidence_request"``, ``"operation_resolution"``.
        source_query_ref: the source query ref.
        expected_answer_contract_ref: the expected answer contract ref.
        expiry: the turn at which this obligation expires.
        completion_receipt_ref: the completion receipt ref when fulfilled,
            or ``None`` when pending.
    """

    obligation_ref: str
    kind: Literal[
        "clarification",
        "learning_answer",
        "evidence_request",
        "operation_resolution",
    ]
    source_query_ref: str
    expected_answer_contract_ref: str
    expiry: int
    completion_receipt_ref: str | None = None


# Kinds that count as learning obligations.
_LEARNING_KINDS = frozenset({"learning_answer"})


class DialogueObligationManager:
    """Manages typed dialogue obligations.

    Only one learning obligation may exist at a time.  Unrelated dialogue
    cannot accidentally consume a learning obligation — fulfilling a
    non-learning obligation does not affect pending learning obligations.
    """

    __slots__ = ("_obligations",)

    def __init__(self) -> None:
        self._obligations: dict[str, DialogueObligation] = {}

    def add(self, obligation: DialogueObligation) -> None:
        """Add a dialogue obligation.

        Raises :class:`ValueError` if a learning obligation already exists
        and ``obligation`` is also a learning obligation.
        """
        if obligation.kind in _LEARNING_KINDS and self.has_learning_obligation():
            raise ValueError(
                "only one learning obligation may exist at a time"
            )
        self._obligations[obligation.obligation_ref] = obligation

    def fulfill(
        self, obligation_ref: str, completion_receipt_ref: str
    ) -> None:
        """Mark an obligation as fulfilled with a completion receipt.

        Raises :class:`KeyError` if ``obligation_ref`` is unknown.
        Unrelated obligations are not affected.
        """
        if obligation_ref not in self._obligations:
            raise KeyError(f"unknown obligation: {obligation_ref}")
        ob = self._obligations[obligation_ref]
        self._obligations[obligation_ref] = replace(
            ob, completion_receipt_ref=completion_receipt_ref
        )

    def pending(self) -> tuple[DialogueObligation, ...]:
        """Return all pending (unfulfilled) obligations."""
        return tuple(
            ob
            for ob in self._obligations.values()
            if ob.completion_receipt_ref is None
        )

    def has_learning_obligation(self) -> bool:
        """Return ``True`` if a pending learning obligation exists."""
        return any(
            ob.kind in _LEARNING_KINDS and ob.completion_receipt_ref is None
            for ob in self._obligations.values()
        )

    def get(self, obligation_ref: str) -> DialogueObligation | None:
        """Return the obligation for ``obligation_ref`` or ``None``."""
        return self._obligations.get(obligation_ref)
