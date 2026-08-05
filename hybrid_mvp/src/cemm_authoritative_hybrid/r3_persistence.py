"""Public crash-safe persistence port for R3.

The canonical :class:`SemanticStores` owner is extended transactionally by the
bundle installer.  R3 owners use only the methods declared by ``R3StorePort``;
they never reach through ``SemanticStores._backend`` and never issue SQL.

The effect journal is a durable state machine.  ``invocation_started`` is
committed before an external adapter call.  A recovered nonterminal entry can
only be reconciled; it is never blindly invoked a second time.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .persistence import Fact, RevisionPin, SemanticStores
from .r3_codec import (
    exact_fields,
    exact_int,
    exact_pin,
    exact_refs,
    exact_text,
    freeze_json,
    thaw_json,
    wire_refs,
)

EFFECT_JOURNAL_ABI_VERSION = 1

__all__ = [
    "EFFECT_JOURNAL_ABI_VERSION",
    "EffectJournalState",
    "EffectJournalEntry",
    "StoredEffectJournal",
    "R3StorePort",
    "require_r3_store_port",
    "world_snapshot",
    "begin_turn",
    "session_snapshot",
    "focus_snapshot",
    "obligation_snapshot",
    "effect_journal_get",
    "effect_journal_begin",
    "effect_journal_transition",
    "effect_journal_commit",
    "commit_learning_outcome",
    "commit_effect_transaction",
    "predicted_effect_pin",
]


class EffectJournalState(Enum):
    PLANNED = "planned"
    AUTHORIZED = "authorized"
    INVOCATION_STARTED = "invocation_started"
    PENDING_RECONCILIATION = "pending_reconciliation"
    OBSERVED = "observed"
    COMMITTED = "committed"
    DENIED = "denied"
    NO_EFFECT = "no_effect"
    FAILED = "failed"
    STALE = "stale"

    @property
    def terminal(self) -> bool:
        return self in {
            EffectJournalState.COMMITTED,
            EffectJournalState.DENIED,
            EffectJournalState.NO_EFFECT,
            EffectJournalState.FAILED,
            EffectJournalState.STALE,
        }


_ALLOWED_TRANSITIONS: Mapping[EffectJournalState, frozenset[EffectJournalState]] = {
    EffectJournalState.PLANNED: frozenset(
        {
            EffectJournalState.AUTHORIZED,
            EffectJournalState.DENIED,
            EffectJournalState.NO_EFFECT,
            EffectJournalState.FAILED,
            EffectJournalState.STALE,
        }
    ),
    EffectJournalState.AUTHORIZED: frozenset(
        {
            EffectJournalState.INVOCATION_STARTED,
            EffectJournalState.OBSERVED,
            EffectJournalState.DENIED,
            EffectJournalState.NO_EFFECT,
            EffectJournalState.FAILED,
            EffectJournalState.STALE,
        }
    ),
    EffectJournalState.INVOCATION_STARTED: frozenset(
        {
            EffectJournalState.PENDING_RECONCILIATION,
            EffectJournalState.OBSERVED,
            EffectJournalState.FAILED,
        }
    ),
    EffectJournalState.PENDING_RECONCILIATION: frozenset(
        {
            EffectJournalState.PENDING_RECONCILIATION,
            EffectJournalState.OBSERVED,
            EffectJournalState.FAILED,
        }
    ),
    EffectJournalState.OBSERVED: frozenset(
        {EffectJournalState.COMMITTED, EffectJournalState.FAILED}
    ),
    EffectJournalState.COMMITTED: frozenset(),
    EffectJournalState.DENIED: frozenset(),
    EffectJournalState.NO_EFFECT: frozenset(),
    EffectJournalState.FAILED: frozenset(),
    EffectJournalState.STALE: frozenset(),
}


def validate_journal_transition(
    source: EffectJournalState, target: EffectJournalState
) -> None:
    if type(source) is not EffectJournalState or type(target) is not EffectJournalState:
        raise TypeError("journal transitions require exact states")
    if target not in _ALLOWED_TRANSITIONS[source]:
        raise ValueError(
            f"illegal effect journal transition: {source.value}->{target.value}"
        )


@dataclass(frozen=True, init=False)
class EffectJournalEntry:
    abi_version: int
    journal_ref: str
    idempotency_key: str
    state: EffectJournalState
    attempt_index: int
    intent_ref: str
    decision_ref: str
    request_payload: Mapping[str, Any]
    observation_payload: Mapping[str, Any] | None
    outcome_ref: str | None
    blocker_refs: tuple[str, ...]
    parent_journal_ref: str | None
    effect_revision: int

    _FIELDS = frozenset(
        {
            "abi_version",
            "journal_ref",
            "idempotency_key",
            "state",
            "attempt_index",
            "intent_ref",
            "decision_ref",
            "request_payload",
            "observation_payload",
            "outcome_ref",
            "blocker_refs",
            "parent_journal_ref",
            "effect_revision",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use EffectJournalEntry.create")

    @classmethod
    def create(
        cls,
        *,
        idempotency_key: str,
        state: EffectJournalState,
        attempt_index: int,
        intent_ref: str,
        decision_ref: str,
        request_payload: Mapping[str, Any],
        observation_payload: Mapping[str, Any] | None,
        outcome_ref: str | None,
        blocker_refs: tuple[str, ...],
        parent_journal_ref: str | None,
        effect_revision: int,
    ) -> "EffectJournalEntry":
        if type(state) is not EffectJournalState:
            raise TypeError("state must be exact EffectJournalState")
        request = freeze_json(request_payload)
        if not isinstance(request, Mapping) or not request:
            raise ValueError("request_payload must be a nonempty mapping")
        observation = (
            None
            if observation_payload is None
            else freeze_json(observation_payload)
        )
        if observation is not None and not isinstance(observation, Mapping):
            raise TypeError("observation_payload must be a mapping or None")
        outcome = None if outcome_ref is None else exact_text(outcome_ref, "outcome_ref")
        parent = (
            None
            if parent_journal_ref is None
            else exact_text(parent_journal_ref, "parent_journal_ref")
        )
        blockers = exact_refs(blocker_refs, "blocker_refs")
        if state in {EffectJournalState.OBSERVED, EffectJournalState.COMMITTED}:
            if observation is None:
                raise ValueError("observed/committed state requires observation")
        if state is EffectJournalState.NO_EFFECT and observation is not None:
            raise ValueError("no-effect state cannot carry observation")
        if state.terminal != (outcome is not None):
            raise ValueError("terminal state and outcome_ref presence disagree")
        values = {
            "idempotency_key": exact_text(idempotency_key, "idempotency_key"),
            "state": state,
            "attempt_index": exact_int(
                attempt_index, "attempt_index", maximum=1_000_000
            ),
            "intent_ref": exact_text(intent_ref, "intent_ref"),
            "decision_ref": exact_text(decision_ref, "decision_ref"),
            "request_payload": request,
            "observation_payload": observation,
            "outcome_ref": outcome,
            "blocker_refs": blockers,
            "parent_journal_ref": parent,
            "effect_revision": exact_int(effect_revision, "effect_revision"),
        }
        material = {
            "abi_version": EFFECT_JOURNAL_ABI_VERSION,
            "idempotency_key": values["idempotency_key"],
            "state": state.value,
            "attempt_index": values["attempt_index"],
            "intent_ref": values["intent_ref"],
            "decision_ref": values["decision_ref"],
            "request_payload": thaw_json(request),
            "observation_payload": thaw_json(observation),
            "outcome_ref": outcome,
            "blocker_refs": list(blockers),
            "parent_journal_ref": parent,
            "effect_revision": values["effect_revision"],
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", EFFECT_JOURNAL_ABI_VERSION)
        object.__setattr__(obj, "journal_ref", stable_ref("effect_journal", material))
        for name, item in values.items():
            object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "journal_ref": self.journal_ref,
            "idempotency_key": self.idempotency_key,
            "state": self.state.value,
            "attempt_index": self.attempt_index,
            "intent_ref": self.intent_ref,
            "decision_ref": self.decision_ref,
            "request_payload": thaw_json(self.request_payload),
            "observation_payload": thaw_json(self.observation_payload),
            "outcome_ref": self.outcome_ref,
            "blocker_refs": list(self.blocker_refs),
            "parent_journal_ref": self.parent_journal_ref,
            "effect_revision": self.effect_revision,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EffectJournalEntry":
        row = exact_fields(value, cls._FIELDS, "EffectJournalEntry")
        if (
            type(row["abi_version"]) is not int
            or row["abi_version"] != EFFECT_JOURNAL_ABI_VERSION
        ):
            raise ValueError("unsupported Effect Journal ABI")
        rebuilt = cls.create(
            idempotency_key=row["idempotency_key"],
            state=EffectJournalState(row["state"]),
            attempt_index=row["attempt_index"],
            intent_ref=row["intent_ref"],
            decision_ref=row["decision_ref"],
            request_payload=row["request_payload"],
            observation_payload=row["observation_payload"],
            outcome_ref=row["outcome_ref"],
            blocker_refs=wire_refs(row["blocker_refs"], "blocker_refs"),
            parent_journal_ref=row["parent_journal_ref"],
            effect_revision=row["effect_revision"],
        )
        if row["journal_ref"] != rebuilt.journal_ref or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical EffectJournalEntry encoding")
        return rebuilt


@dataclass(frozen=True)
class StoredEffectJournal:
    entry: EffectJournalEntry
    receipt_payload: Mapping[str, Any] | None

    def __post_init__(self) -> None:
        if type(self.entry) is not EffectJournalEntry:
            raise TypeError("entry must be exact EffectJournalEntry")
        payload = (
            None if self.receipt_payload is None else freeze_json(self.receipt_payload)
        )
        if payload is not None and not isinstance(payload, Mapping):
            raise TypeError("receipt_payload must be a mapping or None")
        if self.entry.state.terminal != (payload is not None):
            raise ValueError("terminal journal and receipt presence disagree")
        if payload is not None and payload.get("receipt_ref") != self.entry.outcome_ref:
            raise ValueError("terminal journal does not bind receipt identity")
        object.__setattr__(self, "receipt_payload", payload)

    def as_dict(self) -> dict[str, Any]:
        return {
            "entry": self.entry.as_dict(),
            "receipt": thaw_json(self.receipt_payload),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StoredEffectJournal":
        row = exact_fields(
            value, frozenset({"entry", "receipt"}), "StoredEffectJournal"
        )
        if type(row["entry"]) is not dict:
            raise TypeError("StoredEffectJournal entry must be exact dict")
        if row["receipt"] is not None and type(row["receipt"]) is not dict:
            raise TypeError("StoredEffectJournal receipt must be exact dict or None")
        return cls(EffectJournalEntry.from_dict(row["entry"]), row["receipt"])


@runtime_checkable
class R3StorePort(Protocol):
    def r3_world_snapshot(self, *, maximum: int) -> tuple[Fact, ...]: ...
    def r3_session_snapshot(self, session_ref: str) -> Mapping[str, Any]: ...
    def r3_begin_turn(self, session_ref: str) -> Mapping[str, Any]: ...
    def r3_focus_snapshot(
        self, session_ref: str, *, maximum: int
    ) -> Mapping[str, Any]: ...
    def r3_obligation_snapshot(
        self, session_ref: str, *, maximum: int
    ) -> Mapping[str, Any]: ...
    def r3_effect_journal_get(
        self, idempotency_key: str
    ) -> Mapping[str, Any] | None: ...
    def r3_effect_journal_begin(
        self,
        *,
        idempotency_key: str,
        intent_ref: str,
        decision_ref: str,
        request_payload: Mapping[str, Any],
        expected_effect_revision: int,
    ) -> Mapping[str, Any]: ...
    def r3_effect_journal_transition(
        self,
        *,
        idempotency_key: str,
        expected_state: str,
        next_state: str,
        observation_payload: Mapping[str, Any] | None,
        outcome_ref: str | None,
        receipt_payload: Mapping[str, Any] | None,
        blocker_refs: tuple[str, ...],
        expected_effect_revision: int,
    ) -> Mapping[str, Any]: ...
    def r3_effect_journal_commit(
        self,
        *,
        idempotency_key: str,
        expected_state: str,
        observation_payload: Mapping[str, Any],
        outcome_ref: str,
        receipt_payload: Mapping[str, Any],
        facts: tuple[Fact, ...],
        expected_revision_pin: RevisionPin,
    ) -> Mapping[str, Any]: ...
    def r3_commit_learning_outcome(
        self,
        *,
        session_ref: str,
        obligation_ref: str,
        obligation_payload: Mapping[str, Any],
        idempotency_key: str,
        intent_ref: str,
        decision_ref: str,
        receipt_payload: Mapping[str, Any],
        expected_revision_pin: RevisionPin,
    ) -> Mapping[str, Any]: ...


_REQUIRED_PORT_METHODS = (
    "r3_world_snapshot",
    "r3_session_snapshot",
    "r3_begin_turn",
    "r3_focus_snapshot",
    "r3_obligation_snapshot",
    "r3_effect_journal_get",
    "r3_effect_journal_begin",
    "r3_effect_journal_transition",
    "r3_effect_journal_commit",
    "r3_commit_learning_outcome",
)


def require_r3_store_port(stores: SemanticStores) -> R3StorePort:
    if type(stores) is not SemanticStores:
        raise TypeError("stores must be exact SemanticStores")
    missing = tuple(
        name for name in _REQUIRED_PORT_METHODS if not callable(getattr(stores, name, None))
    )
    if missing:
        raise TypeError(f"SemanticStores lacks the canonical R3 port: {missing}")
    return stores  # type: ignore[return-value]


def world_snapshot(stores: SemanticStores, *, maximum: int) -> tuple[Fact, ...]:
    maximum = exact_int(maximum, "maximum", minimum=1, maximum=100_000)
    rows = require_r3_store_port(stores).r3_world_snapshot(maximum=maximum)
    if type(rows) is not tuple or any(type(row) is not Fact for row in rows):
        raise TypeError("r3_world_snapshot returned invalid facts")
    if len(rows) > maximum:
        raise ValueError("r3_world_snapshot exceeded its bound")
    refs = tuple(row.fact_ref for row in rows)
    if len(refs) != len(set(refs)):
        raise ValueError("r3_world_snapshot returned duplicate facts")
    return rows


def _snapshot(value: Mapping[str, Any], *, kind: str) -> Mapping[str, Any]:
    frozen = freeze_json(value)
    if not isinstance(frozen, Mapping):
        raise TypeError(f"{kind} snapshot must be a mapping")
    expected_ref = frozen.get("snapshot_ref")
    if type(expected_ref) is not str or not expected_ref:
        raise ValueError(f"{kind} snapshot lacks snapshot_ref")
    return frozen


def begin_turn(stores: SemanticStores, session_ref: str) -> Mapping[str, Any]:
    return _snapshot(
        require_r3_store_port(stores).r3_begin_turn(
            exact_text(session_ref, "session_ref")
        ),
        kind="turn",
    )


def session_snapshot(stores: SemanticStores, session_ref: str) -> Mapping[str, Any]:
    return _snapshot(
        require_r3_store_port(stores).r3_session_snapshot(
            exact_text(session_ref, "session_ref")
        ),
        kind="session",
    )


def focus_snapshot(
    stores: SemanticStores, session_ref: str, *, maximum: int
) -> Mapping[str, Any]:
    maximum = exact_int(maximum, "maximum", minimum=1, maximum=10_000)
    return _snapshot(
        require_r3_store_port(stores).r3_focus_snapshot(
            exact_text(session_ref, "session_ref"), maximum=maximum
        ),
        kind="focus",
    )


def obligation_snapshot(
    stores: SemanticStores, session_ref: str, *, maximum: int
) -> Mapping[str, Any]:
    maximum = exact_int(maximum, "maximum", minimum=1, maximum=10_000)
    return _snapshot(
        require_r3_store_port(stores).r3_obligation_snapshot(
            exact_text(session_ref, "session_ref"), maximum=maximum
        ),
        kind="obligation",
    )


def _stored(value: object, context: str) -> StoredEffectJournal:
    if type(value) is not dict:
        raise TypeError(f"{context} returned a non-dict row")
    return StoredEffectJournal.from_dict(value)


def effect_journal_get(
    stores: SemanticStores, idempotency_key: str
) -> StoredEffectJournal | None:
    row = require_r3_store_port(stores).r3_effect_journal_get(
        exact_text(idempotency_key, "idempotency_key")
    )
    return None if row is None else _stored(row, "r3_effect_journal_get")


def effect_journal_begin(
    stores: SemanticStores,
    *,
    idempotency_key: str,
    intent_ref: str,
    decision_ref: str,
    request_payload: Mapping[str, Any],
    expected_effect_revision: int,
) -> StoredEffectJournal:
    row = require_r3_store_port(stores).r3_effect_journal_begin(
        idempotency_key=exact_text(idempotency_key, "idempotency_key"),
        intent_ref=exact_text(intent_ref, "intent_ref"),
        decision_ref=exact_text(decision_ref, "decision_ref"),
        request_payload=thaw_json(freeze_json(request_payload)),
        expected_effect_revision=exact_int(
            expected_effect_revision, "expected_effect_revision"
        ),
    )
    return _stored(row, "r3_effect_journal_begin")


def effect_journal_transition(
    stores: SemanticStores,
    *,
    idempotency_key: str,
    expected_state: EffectJournalState,
    next_state: EffectJournalState,
    observation_payload: Mapping[str, Any] | None,
    outcome_ref: str | None,
    receipt_payload: Mapping[str, Any] | None,
    blocker_refs: tuple[str, ...],
    expected_effect_revision: int,
) -> StoredEffectJournal:
    validate_journal_transition(expected_state, next_state)
    if (outcome_ref is None) != (receipt_payload is None):
        raise ValueError("outcome_ref and receipt_payload must be present together")
    row = require_r3_store_port(stores).r3_effect_journal_transition(
        idempotency_key=exact_text(idempotency_key, "idempotency_key"),
        expected_state=expected_state.value,
        next_state=next_state.value,
        observation_payload=(
            None
            if observation_payload is None
            else thaw_json(freeze_json(observation_payload))
        ),
        outcome_ref=(
            None if outcome_ref is None else exact_text(outcome_ref, "outcome_ref")
        ),
        receipt_payload=(
            None
            if receipt_payload is None
            else thaw_json(freeze_json(receipt_payload))
        ),
        blocker_refs=exact_refs(blocker_refs, "blocker_refs"),
        expected_effect_revision=exact_int(
            expected_effect_revision, "expected_effect_revision"
        ),
    )
    return _stored(row, "r3_effect_journal_transition")


def effect_journal_commit(
    stores: SemanticStores,
    *,
    idempotency_key: str,
    observation_payload: Mapping[str, Any],
    outcome_ref: str,
    receipt_payload: Mapping[str, Any],
    facts: tuple[Fact, ...],
    expected_revision_pin: RevisionPin,
) -> tuple[StoredEffectJournal, RevisionPin]:
    if type(facts) is not tuple or any(type(row) is not Fact for row in facts):
        raise TypeError("facts must be an exact Fact tuple")
    row = require_r3_store_port(stores).r3_effect_journal_commit(
        idempotency_key=exact_text(idempotency_key, "idempotency_key"),
        expected_state=EffectJournalState.OBSERVED.value,
        observation_payload=thaw_json(freeze_json(observation_payload)),
        outcome_ref=exact_text(outcome_ref, "outcome_ref"),
        receipt_payload=thaw_json(freeze_json(receipt_payload)),
        facts=facts,
        expected_revision_pin=exact_pin(expected_revision_pin),
    )
    if type(row) is not dict or set(row) != {"journal", "revision_pin"}:
        raise TypeError("r3_effect_journal_commit returned invalid material")
    journal = StoredEffectJournal.from_dict(row["journal"])
    pin = RevisionPin.from_dict(row["revision_pin"])
    if journal.entry.state is not EffectJournalState.COMMITTED:
        raise ValueError("atomic effect commit did not produce committed state")
    return journal, pin


def commit_learning_outcome(
    stores: SemanticStores,
    *,
    session_ref: str,
    obligation_ref: str,
    obligation_payload: Mapping[str, Any],
    idempotency_key: str,
    intent_ref: str,
    decision_ref: str,
    receipt_payload: Mapping[str, Any],
    expected_revision_pin: RevisionPin,
) -> tuple[StoredEffectJournal, RevisionPin]:
    row = require_r3_store_port(stores).r3_commit_learning_outcome(
        session_ref=exact_text(session_ref, "session_ref"),
        obligation_ref=exact_text(obligation_ref, "obligation_ref"),
        obligation_payload=thaw_json(freeze_json(obligation_payload)),
        idempotency_key=exact_text(idempotency_key, "idempotency_key"),
        intent_ref=exact_text(intent_ref, "intent_ref"),
        decision_ref=exact_text(decision_ref, "decision_ref"),
        receipt_payload=thaw_json(freeze_json(receipt_payload)),
        expected_revision_pin=exact_pin(expected_revision_pin),
    )
    if type(row) is not dict or set(row) != {"journal", "revision_pin"}:
        raise TypeError("r3_commit_learning_outcome returned invalid material")
    journal = StoredEffectJournal.from_dict(row["journal"])
    pin = RevisionPin.from_dict(row["revision_pin"])
    if journal.entry.state is not EffectJournalState.NO_EFFECT:
        raise ValueError("learning outcome must produce no-effect journal state")
    return journal, pin


def commit_effect_transaction(
    stores: SemanticStores,
    *,
    expected_pin: RevisionPin,
    facts: tuple[Fact, ...],
    effect_key: str,
    effect_payload: Mapping[str, Any],
) -> RevisionPin:
    """Atomically commit world facts and an effect entry in one transaction.

    This is the simple atomic write port for tests and owners that need to
    persist a committed effect with world deltas without going through the
    full effect-journal FSM.  The revision pin is validated, world facts are
    inserted, the effect store is advanced, and a predicted effect pin is
    returned.
    """
    require_r3_store_port(stores)
    expected_pin = exact_pin(expected_pin)
    if type(facts) is not tuple or any(type(row) is not Fact for row in facts):
        raise TypeError("facts must be an exact Fact tuple")
    if type(effect_key) is not str or not effect_key:
        raise TypeError("effect_key must be a non-empty str")
    if not isinstance(effect_payload, Mapping):
        raise TypeError("effect_payload must be a Mapping")
    if expected_pin != stores.revision_pin():
        from .persistence import StaleRevisionError
        raise StaleRevisionError("commit_effect_transaction revision pin is stale")
    stores.world.commit(facts, expected_revision=stores.world.revision)
    stores.effects.commit({"effect_key": effect_key, "payload": dict(effect_payload)})
    return predicted_effect_pin(expected_pin, has_world_delta=bool(facts))


def predicted_effect_pin(
    pin: RevisionPin,
    *,
    has_world_delta: bool,
    effect_steps: int = 1,
    session_steps: int = 0,
) -> RevisionPin:
    pin = exact_pin(pin)
    if type(has_world_delta) is not bool:
        raise TypeError("has_world_delta must be exact bool")
    effect_steps = exact_int(effect_steps, "effect_steps", minimum=1)
    session_steps = exact_int(session_steps, "session_steps")
    return RevisionPin(
        pin.authority_generation,
        pin.world_revision + (1 if has_world_delta else 0),
        pin.session_revision + session_steps,
        pin.episode_revision,
        pin.effect_revision + effect_steps,
        pin.model_identity,
    )
