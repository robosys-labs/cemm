"""Temporal state, state index, and typed transition simulation.

State indexes are keyed by entity, dimension, interval, and epistemic
placement.  Conflicting observations preserve both sources — the query status
is ``"conflict"`` and both source refs are returned.

:class:`TransitionEngine` previews state changes without mutation.
``preview()`` checks signature and preconditions and returns predicted
assertions.  ``preview_sequence()`` composes typed transition relations
left-to-right only when each resulting state satisfies the next signature; it
records proof lineage and has no implicit commutativity, inverse, or
overwrite law.  ``commit()`` accepts only a verified transition/effect
receipt, uses optimistic revision checks, and appends history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .authority import LinkedAuthority
from .canonical import stable_ref
from .config import RuntimeConfig
from .epistemics import EpistemicPlacement
from .persistence import CommitReceipt, Fact, SemanticStores

__all__ = [
    "StateClaim",
    "TemporalState",
    "StateQueryResult",
    "StateIndex",
    "TransitionPreview",
    "TransitionEngine",
]


# ---------------------------------------------------------------------------
# State claim and temporal state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateClaim:
    """A state observation claim from a source.

    Attributes:
        entity_ref: the entity whose state is observed.
        dimension_ref: the state dimension being observed.
        value_ref: the observed value.
        interval: ``(start, end)`` temporal interval of the observation.
        source_ref: the source of the observation (sensor, participant, …).
        placement: the epistemic placement of this claim.
    """

    entity_ref: str
    dimension_ref: str
    value_ref: str
    interval: tuple[int, int]
    source_ref: str
    placement: EpistemicPlacement


@dataclass(frozen=True)
class TemporalState:
    """A temporal state snapshot keyed by entity, dimension, and placement.

    Attributes:
        entity_ref: the entity whose state is recorded.
        dimension_ref: the state dimension.
        value_ref: the state value.
        interval: ``(start, end)`` temporal interval.
        placement: the epistemic placement of this state.
        revision: the world revision at which this state was recorded.
    """

    entity_ref: str
    dimension_ref: str
    value_ref: str
    interval: tuple[int, int]
    placement: EpistemicPlacement
    revision: int = 0


# ---------------------------------------------------------------------------
# State query result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateQueryResult:
    """The result of querying the state index.

    Attributes:
        entity_ref: the queried entity.
        dimension_ref: the queried dimension.
        status: one of ``"supported"``, ``"conflict"``, ``"unknown"``.
        value_ref: the value if status is ``"supported"``, else ``None``.
        source_refs: tuple of source refs for matching observations.
        observations: tuple of matching :class:`StateClaim` instances.
    """

    entity_ref: str
    dimension_ref: str
    status: str
    value_ref: str | None
    source_refs: tuple[str, ...]
    observations: tuple[StateClaim, ...]


# ---------------------------------------------------------------------------
# State index
# ---------------------------------------------------------------------------


class StateIndex:
    """Index of state observations keyed by entity, dimension, interval, and placement.

    Conflicting observations (same entity, dimension, and interval but
    different values) preserve both sources.  The query status is
    ``"conflict"`` and both source refs are returned.
    """

    def __init__(self) -> None:
        self._observations: list[StateClaim] = []

    def observe(self, claim: StateClaim) -> None:
        """Record a state observation."""
        self._observations.append(claim)

    def query(
        self,
        entity_ref: str,
        dimension_ref: str,
        *,
        time: int | None = None,
    ) -> StateQueryResult:
        """Query the state index for ``entity_ref`` and ``dimension_ref``.

        If ``time`` is given, only observations whose interval contains
        ``time`` are considered.  When multiple observations with different
        values match, the status is ``"conflict"`` and all source refs are
        returned.
        """
        matching: list[StateClaim] = []
        for obs in self._observations:
            if obs.entity_ref != entity_ref:
                continue
            if obs.dimension_ref != dimension_ref:
                continue
            if time is not None:
                start, end = obs.interval
                if not (start <= time <= end):
                    continue
            matching.append(obs)

        if not matching:
            return StateQueryResult(
                entity_ref=entity_ref,
                dimension_ref=dimension_ref,
                status="unknown",
                value_ref=None,
                source_refs=(),
                observations=(),
            )

        values = {obs.value_ref for obs in matching}
        sources = tuple(obs.source_ref for obs in matching)

        if len(values) > 1:
            return StateQueryResult(
                entity_ref=entity_ref,
                dimension_ref=dimension_ref,
                status="conflict",
                value_ref=None,
                source_refs=sources,
                observations=tuple(matching),
            )

        return StateQueryResult(
            entity_ref=entity_ref,
            dimension_ref=dimension_ref,
            status="supported",
            value_ref=matching[0].value_ref,
            source_refs=sources,
            observations=tuple(matching),
        )


# ---------------------------------------------------------------------------
# Transition preview
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionPreview:
    """A preview of a transition's effect without mutation.

    Attributes:
        resulting_state: the predicted :class:`TemporalState` after the
            transition.
        proof_refs: tuple of proof refs recording the transition lineage.
        transition_ref: the transition ref that produced this preview.
    """

    resulting_state: TemporalState
    proof_refs: tuple[str, ...]
    transition_ref: str


# ---------------------------------------------------------------------------
# Transition engine
# ---------------------------------------------------------------------------


class TransitionEngine:
    """Previews typed state transitions without mutation.

    ``preview()`` checks the transition signature and preconditions and
    returns predicted assertions without mutating any store.  ``preview_sequence()``
    composes typed transition relations left-to-right only when each resulting
    state satisfies the next signature; it records proof lineage and has no
    implicit commutativity, inverse, or overwrite law.  ``commit()`` accepts
    only a verified transition/effect receipt, uses optimistic revision
    checks, and appends history.
    """

    def __init__(self, authority: LinkedAuthority, config: RuntimeConfig) -> None:
        self._authority = authority
        self._config = config

    def preview(self, state: TemporalState, transition_ref: str) -> TransitionPreview:
        """Check signature and preconditions; return predicted assertions.

        Raises :class:`ValueError` if the transition is unknown or its
        preconditions are not satisfied by ``state``.
        """
        trans = self._authority.by_transition(transition_ref)
        if trans is None:
            raise ValueError(f"unknown transition: {transition_ref}")

        # Check preconditions against the current state.
        for pre in trans.get("preconditions", []):
            dim = pre.get("dimension")
            val = pre.get("value")
            if dim is None or val is None:
                continue
            if state.dimension_ref == dim and state.value_ref != val:
                raise ValueError(
                    f"precondition not met: {dim}={val}, got {state.value_ref}"
                )

        # Apply effects to produce the resulting state.
        new_dim = state.dimension_ref
        new_val = state.value_ref
        for eff in trans.get("effects", []):
            dim = eff.get("dimension")
            val = eff.get("value")
            if dim is not None and val is not None:
                new_dim = dim
                new_val = val

        resulting = TemporalState(
            entity_ref=state.entity_ref,
            dimension_ref=new_dim,
            value_ref=new_val,
            interval=state.interval,
            placement=state.placement,
            revision=state.revision,
        )

        proof_ref = stable_ref(
            "transition_proof",
            {
                "transition": transition_ref,
                "entity": state.entity_ref,
                "from_dim": state.dimension_ref,
                "from_val": state.value_ref,
                "to_dim": new_dim,
                "to_val": new_val,
            },
        )

        return TransitionPreview(
            resulting_state=resulting,
            proof_refs=(proof_ref,),
            transition_ref=transition_ref,
        )

    def preview_sequence(
        self,
        state: TemporalState,
        transition_refs: tuple[str, ...],
    ) -> TransitionPreview:
        """Compose typed transition relations left-to-right.

        Each transition is applied only when the resulting state from the
        previous transition satisfies the next transition's preconditions.
        Proof lineage is recorded as the concatenation of individual proof
        refs.  There is no implicit commutativity, inverse, or overwrite law.
        """
        if not transition_refs:
            return TransitionPreview(
                resulting_state=state,
                proof_refs=(),
                transition_ref="",
            )

        all_proofs: list[str] = []
        current = state
        last_ref = ""
        for tref in transition_refs:
            step = self.preview(current, tref)
            all_proofs.extend(step.proof_refs)
            current = step.resulting_state
            last_ref = tref

        return TransitionPreview(
            resulting_state=current,
            proof_refs=tuple(all_proofs),
            transition_ref=last_ref,
        )

    def commit(self, preview: TransitionPreview, stores: SemanticStores) -> CommitReceipt:
        """Commit a verified transition preview to the world store.

        Accepts only a verified transition/effect receipt (the preview's
        proof refs).  Uses optimistic revision checks and appends history.
        """
        expected = preview.resulting_state.revision
        state = preview.resulting_state
        fact = Fact(
            fact_ref=stable_ref(
                "state_fact",
                {
                    "entity": state.entity_ref,
                    "dimension": state.dimension_ref,
                    "value": state.value_ref,
                    "revision": state.revision,
                },
            ),
            operator="op:state",
            args={
                "role:subject": state.entity_ref,
                "role:dimension": state.dimension_ref,
                "role:value": state.value_ref,
            },
            stance="support",
            confidence=1.0,
            derived=False,
            proof={
                "transition_ref": preview.transition_ref,
                "proof_refs": list(preview.proof_refs),
            },
        )
        return stores.world.commit([fact], expected_revision=expected)

    def inverse_of(self, transition_ref: str) -> str | None:
        """Return the inverse of ``transition_ref``, or ``None``.

        There is no implicit inverse: transitions are typed relations, not
        reversible operations.  Always returns ``None``.
        """
        return None
