"""Effect / No-Effect Receipt ABI 1 and the sole mutation gateway.

External operations use a durable finite-state journal.  A journal entry reaches
``invocation_started`` before the adapter is called.  Recovery of that state
uses ``reconcile`` and never blindly invokes the operation again.  Only an
adapter observation that exactly matches the reviewed expected transition may
become world state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .decision import DecisionAction, DecisionStatus
from .expressions import VerifiedMeaning
from .persistence import Fact, RevisionPin, SemanticStores
from .r3_artifacts import EvaluationBundle, StateDelta
from .r3_codec import exact_fields, exact_pin, exact_refs, exact_text, wire_refs
from .r3_learning import DialogueObligation, LearningPlan
from .r3_persistence import (
    EffectJournalState,
    StoredEffectJournal,
    commit_learning_outcome,
    effect_journal_begin,
    effect_journal_commit,
    effect_journal_get,
    effect_journal_transition,
)
from .situation import SituationContext

EFFECT_RECEIPT_ABI_VERSION = 1
ADAPTER_RESULT_ABI_VERSION = 1
EFFECT_REQUEST_ABI_VERSION = 1

__all__ = [
    "EFFECT_RECEIPT_ABI_VERSION",
    "EffectStatus",
    "NoEffectReason",
    "AdapterStatus",
    "ObservedDelta",
    "EffectRequest",
    "AdapterResult",
    "EffectAdapter",
    "AdapterRegistry",
    "EffectReceipt",
    "NoEffectReceipt",
    "R3EffectGateway",
]


def _text(value: object, name: str) -> str:
    return exact_text(value, name)


def _optional(value: object, name: str) -> str | None:
    return None if value is None else _text(value, name)


def _pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple or len(value) > 128:
        raise TypeError(f"{name} must be a bounded exact tuple")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not tuple or len(row) != 2:
            raise TypeError(f"{name} rows must be exact pairs")
        rows.append((_text(row[0], f"{name} key"), _text(row[1], f"{name} value")))
    if len(rows) != len({row[0] for row in rows}):
        raise ValueError(f"{name} keys must be unique")
    return tuple(rows)


def _wire_pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not list or len(row) != 2:
            raise TypeError(f"{name} wire rows must be two-item lists")
        rows.append((row[0], row[1]))
    return _pairs(tuple(rows), name)


def _predicted_pin(
    pin: RevisionPin, *, world: int = 0, session: int = 0, effects: int = 0
) -> RevisionPin:
    return RevisionPin(
        pin.authority_generation,
        pin.world_revision + world,
        pin.session_revision + session,
        pin.episode_revision,
        pin.effect_revision + effects,
        pin.model_identity,
    )


class EffectStatus(Enum):
    COMMITTED = "committed"
    DENIED = "denied"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    ADAPTER_MISSING = "adapter_missing"
    PENDING = "pending"
    FAILED = "failed"
    STALE_REVISION = "stale_revision"


class NoEffectReason(Enum):
    READ_ONLY = "read_only"
    SIMULATION = "simulation"
    ATTRIBUTED_ONLY = "attributed_only"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    NO_REQUESTED_EFFECT = "no_requested_effect"
    LEARNING_OBLIGATION_ONLY = "learning_obligation_only"


class AdapterStatus(Enum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, init=False)
class ObservedDelta:
    abi_version: int
    observed_delta_ref: str
    operator_ref: str
    predicate_ref: str
    role_values: tuple[tuple[str, str], ...]
    stance: str
    evidence_refs: tuple[str, ...]

    _FIELDS = frozenset({
        "abi_version", "observed_delta_ref", "operator_ref", "predicate_ref",
        "role_values", "stance", "evidence_refs",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ObservedDelta.create")

    @classmethod
    def create(
        cls,
        *,
        operator_ref: str,
        predicate_ref: str,
        role_values: tuple[tuple[str, str], ...],
        stance: str,
        evidence_refs: tuple[str, ...],
    ) -> "ObservedDelta":
        if stance not in {"support", "deny"}:
            raise ValueError("observed stance must be support or deny")
        roles = _pairs(role_values, "role_values")
        values = {
            "operator_ref": _text(operator_ref, "operator_ref"),
            "predicate_ref": _text(predicate_ref, "predicate_ref"),
            "role_values": roles,
            "stance": stance,
            "evidence_refs": exact_refs(evidence_refs, "evidence_refs", nonempty=True),
        }
        material = {
            "abi_version": ADAPTER_RESULT_ABI_VERSION,
            "operator_ref": values["operator_ref"],
            "predicate_ref": values["predicate_ref"],
            "role_values": [list(row) for row in roles],
            "stance": stance,
            "evidence_refs": list(values["evidence_refs"]),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", ADAPTER_RESULT_ABI_VERSION)
        object.__setattr__(obj, "observed_delta_ref", stable_ref("observed_delta", material))
        for name, item in values.items():
            object.__setattr__(obj, name, item)
        return obj

    @classmethod
    def from_state_delta(
        cls, delta: StateDelta, *, evidence_refs: tuple[str, ...]
    ) -> "ObservedDelta":
        if type(delta) is not StateDelta:
            raise TypeError("delta must be exact StateDelta")
        return cls.create(
            operator_ref=delta.operator_ref,
            predicate_ref=delta.predicate_ref,
            role_values=delta.role_values,
            stance=delta.stance,
            evidence_refs=evidence_refs,
        )

    @property
    def semantic_signature(self) -> tuple[str, str, tuple[tuple[str, str], ...], str]:
        return self.operator_ref, self.predicate_ref, self.role_values, self.stance

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "observed_delta_ref": self.observed_delta_ref,
            "operator_ref": self.operator_ref,
            "predicate_ref": self.predicate_ref,
            "role_values": [list(row) for row in self.role_values],
            "stance": self.stance,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservedDelta":
        row = exact_fields(value, cls._FIELDS, "ObservedDelta")
        if type(row["abi_version"]) is not int or row["abi_version"] != ADAPTER_RESULT_ABI_VERSION:
            raise ValueError("unsupported Observed Delta ABI")
        rebuilt = cls.create(
            operator_ref=row["operator_ref"],
            predicate_ref=row["predicate_ref"],
            role_values=_wire_pairs(row["role_values"], "role_values"),
            stance=row["stance"],
            evidence_refs=wire_refs(row["evidence_refs"], "evidence_refs", nonempty=True),
        )
        if row["observed_delta_ref"] != rebuilt.observed_delta_ref or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ObservedDelta encoding")
        return rebuilt


@dataclass(frozen=True, init=False)
class EffectRequest:
    abi_version: int
    request_ref: str
    idempotency_key: str
    journal_origin_ref: str
    decision_ref: str
    verified_meaning_ref: str
    expression_ref: str
    situation_ref: str
    program_ref: str
    effect_intent_ref: str
    actor_ref: str
    event_type_ref: str
    target_ref: str | None
    transition_ref: str | None
    adapter_ref: str
    expected_deltas: tuple[ObservedDelta, ...]
    input_revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "request_ref", "idempotency_key", "journal_origin_ref",
        "decision_ref", "verified_meaning_ref", "expression_ref", "situation_ref",
        "program_ref", "effect_intent_ref", "actor_ref", "event_type_ref",
        "target_ref", "transition_ref", "adapter_ref", "expected_deltas",
        "input_revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use EffectRequest.create")

    @classmethod
    def create(
        cls,
        *,
        idempotency_key: str,
        decision_ref: str,
        verified_meaning_ref: str,
        expression_ref: str,
        situation_ref: str,
        program_ref: str,
        effect_intent_ref: str,
        actor_ref: str,
        event_type_ref: str,
        target_ref: str | None,
        transition_ref: str | None,
        adapter_ref: str,
        expected_deltas: tuple[ObservedDelta, ...],
        input_revision_pin: RevisionPin,
    ) -> "EffectRequest":
        if type(expected_deltas) is not tuple or not expected_deltas or any(type(row) is not ObservedDelta for row in expected_deltas):
            raise TypeError("expected_deltas must be a non-empty exact ObservedDelta tuple")
        values = {
            "idempotency_key": _text(idempotency_key, "idempotency_key"),
            "decision_ref": _text(decision_ref, "decision_ref"),
            "verified_meaning_ref": _text(verified_meaning_ref, "verified_meaning_ref"),
            "expression_ref": _text(expression_ref, "expression_ref"),
            "situation_ref": _text(situation_ref, "situation_ref"),
            "program_ref": _text(program_ref, "program_ref"),
            "effect_intent_ref": _text(effect_intent_ref, "effect_intent_ref"),
            "actor_ref": _text(actor_ref, "actor_ref"),
            "event_type_ref": _text(event_type_ref, "event_type_ref"),
            "target_ref": _optional(target_ref, "target_ref"),
            "transition_ref": _optional(transition_ref, "transition_ref"),
            "adapter_ref": _text(adapter_ref, "adapter_ref"),
            "expected_deltas": expected_deltas,
            "input_revision_pin": exact_pin(input_revision_pin),
        }
        material = {
            "abi_version": EFFECT_REQUEST_ABI_VERSION,
            **{
                key: [row.as_dict() for row in item]
                if key == "expected_deltas"
                else item.as_dict()
                if type(item) is RevisionPin
                else item
                for key, item in values.items()
            },
        }
        origin_ref = stable_ref("effect_journal_origin", material)
        material["journal_origin_ref"] = origin_ref
        request_ref = stable_ref("effect_request", material)
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", EFFECT_REQUEST_ABI_VERSION)
        object.__setattr__(obj, "request_ref", request_ref)
        object.__setattr__(obj, "journal_origin_ref", origin_ref)
        for name, item in values.items():
            object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "request_ref": self.request_ref,
            "idempotency_key": self.idempotency_key,
            "journal_origin_ref": self.journal_origin_ref,
            "decision_ref": self.decision_ref,
            "verified_meaning_ref": self.verified_meaning_ref,
            "expression_ref": self.expression_ref,
            "situation_ref": self.situation_ref,
            "program_ref": self.program_ref,
            "effect_intent_ref": self.effect_intent_ref,
            "actor_ref": self.actor_ref,
            "event_type_ref": self.event_type_ref,
            "target_ref": self.target_ref,
            "transition_ref": self.transition_ref,
            "adapter_ref": self.adapter_ref,
            "expected_deltas": [row.as_dict() for row in self.expected_deltas],
            "input_revision_pin": self.input_revision_pin.as_dict(),
        }


@dataclass(frozen=True, init=False)
class AdapterResult:
    abi_version: int
    result_ref: str
    adapter_ref: str
    status: AdapterStatus
    idempotency_key: str
    request_ref: str
    event_type_ref: str
    target_ref: str | None
    transition_ref: str | None
    observed_deltas: tuple[ObservedDelta, ...]
    blocker_refs: tuple[str, ...]
    operation_receipt_ref: str | None

    _FIELDS = frozenset({
        "abi_version", "result_ref", "adapter_ref", "status",
        "idempotency_key", "request_ref", "event_type_ref", "target_ref",
        "transition_ref", "observed_deltas", "blocker_refs",
        "operation_receipt_ref",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use AdapterResult.create")

    @classmethod
    def create(
        cls,
        *,
        adapter_ref: str,
        status: AdapterStatus,
        idempotency_key: str,
        request_ref: str,
        event_type_ref: str,
        target_ref: str | None,
        transition_ref: str | None,
        observed_deltas: tuple[ObservedDelta, ...],
        blocker_refs: tuple[str, ...],
        operation_receipt_ref: str | None,
    ) -> "AdapterResult":
        if type(status) is not AdapterStatus:
            raise TypeError("status must be exact AdapterStatus")
        if type(observed_deltas) is not tuple or any(type(row) is not ObservedDelta for row in observed_deltas):
            raise TypeError("observed_deltas must be exact ObservedDelta tuple")
        operation = _optional(operation_receipt_ref, "operation_receipt_ref")
        blockers = exact_refs(blocker_refs, "blocker_refs")
        if status is AdapterStatus.SUCCEEDED:
            if not observed_deltas or operation is None or blockers:
                raise ValueError("successful adapter result requires observations and operation receipt only")
        else:
            if observed_deltas:
                raise ValueError("non-success adapter result cannot carry observations")
            if not blockers:
                raise ValueError("non-success adapter result requires blockers")
        values = {
            "adapter_ref": _text(adapter_ref, "adapter_ref"),
            "status": status,
            "idempotency_key": _text(idempotency_key, "idempotency_key"),
            "request_ref": _text(request_ref, "request_ref"),
            "event_type_ref": _text(event_type_ref, "event_type_ref"),
            "target_ref": _optional(target_ref, "target_ref"),
            "transition_ref": _optional(transition_ref, "transition_ref"),
            "observed_deltas": observed_deltas,
            "blocker_refs": blockers,
            "operation_receipt_ref": operation,
        }
        material = {
            "abi_version": ADAPTER_RESULT_ABI_VERSION,
            "adapter_ref": values["adapter_ref"],
            "status": status.value,
            "idempotency_key": values["idempotency_key"],
            "request_ref": values["request_ref"],
            "event_type_ref": values["event_type_ref"],
            "target_ref": values["target_ref"],
            "transition_ref": values["transition_ref"],
            "observed_deltas": [row.as_dict() for row in observed_deltas],
            "blocker_refs": list(blockers),
            "operation_receipt_ref": operation,
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", ADAPTER_RESULT_ABI_VERSION)
        object.__setattr__(obj, "result_ref", stable_ref("adapter_result", material))
        for name, item in values.items():
            object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "result_ref": self.result_ref,
            "adapter_ref": self.adapter_ref,
            "status": self.status.value,
            "idempotency_key": self.idempotency_key,
            "request_ref": self.request_ref,
            "event_type_ref": self.event_type_ref,
            "target_ref": self.target_ref,
            "transition_ref": self.transition_ref,
            "observed_deltas": [row.as_dict() for row in self.observed_deltas],
            "blocker_refs": list(self.blocker_refs),
            "operation_receipt_ref": self.operation_receipt_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AdapterResult":
        row = exact_fields(value, cls._FIELDS, "AdapterResult")
        if type(row["abi_version"]) is not int or row["abi_version"] != ADAPTER_RESULT_ABI_VERSION:
            raise ValueError("unsupported Adapter Result ABI")
        if type(row["observed_deltas"]) is not list:
            raise TypeError("observed_deltas must be an exact list")
        rebuilt = cls.create(
            adapter_ref=row["adapter_ref"],
            status=AdapterStatus(row["status"]),
            idempotency_key=row["idempotency_key"],
            request_ref=row["request_ref"],
            event_type_ref=row["event_type_ref"],
            target_ref=row["target_ref"],
            transition_ref=row["transition_ref"],
            observed_deltas=tuple(ObservedDelta.from_dict(item) for item in row["observed_deltas"]),
            blocker_refs=wire_refs(row["blocker_refs"], "blocker_refs"),
            operation_receipt_ref=row["operation_receipt_ref"],
        )
        if row["result_ref"] != rebuilt.result_ref or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical AdapterResult encoding")
        return rebuilt


@runtime_checkable
class EffectAdapter(Protocol):
    def invoke(self, request: EffectRequest) -> AdapterResult: ...
    def reconcile(self, request: EffectRequest) -> AdapterResult: ...


class AdapterRegistry:
    def __init__(self, adapters: Mapping[str, EffectAdapter] | None = None) -> None:
        if adapters is not None and not isinstance(adapters, Mapping):
            raise TypeError("adapters must be a mapping")
        self._adapters = dict(adapters or {})
        for ref, adapter in self._adapters.items():
            _text(ref, "adapter_ref")
            if not isinstance(adapter, EffectAdapter):
                raise TypeError(f"adapter {ref} violates EffectAdapter")

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def get(self, adapter_ref: str) -> EffectAdapter | None:
        return self._adapters.get(adapter_ref)


@dataclass(frozen=True, init=False)
class EffectReceipt:
    abi_version: int
    receipt_ref: str
    status: EffectStatus
    idempotency_key: str
    journal_origin_ref: str
    journal_preterminal_ref: str
    reconciliation_required: bool
    decision_ref: str
    verified_meaning_ref: str
    expression_ref: str
    situation_ref: str
    program_ref: str
    effect_intent_ref: str | None
    actor_ref: str
    event_type_ref: str
    transition_ref: str | None
    adapter_ref: str | None
    adapter_result_ref: str | None
    operation_receipt_ref: str | None
    observed_delta_refs: tuple[str, ...]
    committed_fact_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    input_revision_pin: RevisionPin
    output_revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "receipt_ref", "status", "idempotency_key",
        "journal_origin_ref", "journal_preterminal_ref",
        "reconciliation_required", "decision_ref", "verified_meaning_ref",
        "expression_ref", "situation_ref", "program_ref", "effect_intent_ref",
        "actor_ref", "event_type_ref", "transition_ref", "adapter_ref",
        "adapter_result_ref", "operation_receipt_ref", "observed_delta_refs",
        "committed_fact_refs", "proof_refs", "blocker_refs",
        "input_revision_pin", "output_revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use EffectReceipt.create")

    @classmethod
    def create(cls, **raw: Any) -> "EffectReceipt":
        status = raw.pop("status")
        if type(status) is not EffectStatus:
            raise TypeError("status must be exact EffectStatus")
        reconciliation = raw.pop("reconciliation_required")
        if type(reconciliation) is not bool:
            raise TypeError("reconciliation_required must be exact bool")
        input_pin = exact_pin(raw.pop("input_revision_pin"))
        output_pin = exact_pin(raw.pop("output_revision_pin"))
        values = {
            "status": status,
            "idempotency_key": _text(raw.pop("idempotency_key"), "idempotency_key"),
            "journal_origin_ref": _text(raw.pop("journal_origin_ref"), "journal_origin_ref"),
            "journal_preterminal_ref": _text(raw.pop("journal_preterminal_ref"), "journal_preterminal_ref"),
            "reconciliation_required": reconciliation,
            "decision_ref": _text(raw.pop("decision_ref"), "decision_ref"),
            "verified_meaning_ref": _text(raw.pop("verified_meaning_ref"), "verified_meaning_ref"),
            "expression_ref": _text(raw.pop("expression_ref"), "expression_ref"),
            "situation_ref": _text(raw.pop("situation_ref"), "situation_ref"),
            "program_ref": _text(raw.pop("program_ref"), "program_ref"),
            "effect_intent_ref": _optional(raw.pop("effect_intent_ref"), "effect_intent_ref"),
            "actor_ref": _text(raw.pop("actor_ref"), "actor_ref"),
            "event_type_ref": _text(raw.pop("event_type_ref"), "event_type_ref"),
            "transition_ref": _optional(raw.pop("transition_ref"), "transition_ref"),
            "adapter_ref": _optional(raw.pop("adapter_ref"), "adapter_ref"),
            "adapter_result_ref": _optional(raw.pop("adapter_result_ref"), "adapter_result_ref"),
            "operation_receipt_ref": _optional(raw.pop("operation_receipt_ref"), "operation_receipt_ref"),
            "observed_delta_refs": exact_refs(raw.pop("observed_delta_refs"), "observed_delta_refs"),
            "committed_fact_refs": exact_refs(raw.pop("committed_fact_refs"), "committed_fact_refs"),
            "proof_refs": exact_refs(raw.pop("proof_refs"), "proof_refs"),
            "blocker_refs": exact_refs(raw.pop("blocker_refs"), "blocker_refs"),
            "input_revision_pin": input_pin,
            "output_revision_pin": output_pin,
        }
        if raw:
            raise TypeError(f"unknown EffectReceipt fields: {sorted(raw)}")
        if output_pin.authority_generation != input_pin.authority_generation or output_pin.model_identity != input_pin.model_identity:
            raise ValueError("effect receipt changed fixed revision dimensions")
        if output_pin.world_revision < input_pin.world_revision or output_pin.effect_revision <= input_pin.effect_revision:
            raise ValueError("effect receipt output revisions are not monotonic")
        if status is EffectStatus.COMMITTED:
            if not values["observed_delta_refs"] or not values["committed_fact_refs"]:
                raise ValueError("committed effect requires observations and facts")
            if reconciliation or values["blocker_refs"]:
                raise ValueError("committed effect cannot require reconciliation or blockers")
            if output_pin.world_revision <= input_pin.world_revision:
                raise ValueError("committed effect must advance world revision")
        elif status is EffectStatus.PENDING:
            if not reconciliation or values["committed_fact_refs"] or values["observed_delta_refs"]:
                raise ValueError("pending effect has invalid reconciliation/fact semantics")
            if not values["blocker_refs"]:
                raise ValueError("pending effect requires blockers")
        else:
            if reconciliation or values["committed_fact_refs"] or values["observed_delta_refs"]:
                raise ValueError("terminal noncommit effect has invalid fields")
            if not values["blocker_refs"]:
                raise ValueError("terminal noncommit effect requires blockers")
        material = {
            "abi_version": EFFECT_RECEIPT_ABI_VERSION,
            **{
                key: item.value
                if isinstance(item, Enum)
                else list(item)
                if type(item) is tuple
                else item.as_dict()
                if type(item) is RevisionPin
                else item
                for key, item in values.items()
            },
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", EFFECT_RECEIPT_ABI_VERSION)
        object.__setattr__(obj, "receipt_ref", stable_ref("effect_receipt", material))
        for name, item in values.items():
            object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "receipt_ref": self.receipt_ref,
            "status": self.status.value,
            "idempotency_key": self.idempotency_key,
            "journal_origin_ref": self.journal_origin_ref,
            "journal_preterminal_ref": self.journal_preterminal_ref,
            "reconciliation_required": self.reconciliation_required,
            "decision_ref": self.decision_ref,
            "verified_meaning_ref": self.verified_meaning_ref,
            "expression_ref": self.expression_ref,
            "situation_ref": self.situation_ref,
            "program_ref": self.program_ref,
            "effect_intent_ref": self.effect_intent_ref,
            "actor_ref": self.actor_ref,
            "event_type_ref": self.event_type_ref,
            "transition_ref": self.transition_ref,
            "adapter_ref": self.adapter_ref,
            "adapter_result_ref": self.adapter_result_ref,
            "operation_receipt_ref": self.operation_receipt_ref,
            "observed_delta_refs": list(self.observed_delta_refs),
            "committed_fact_refs": list(self.committed_fact_refs),
            "proof_refs": list(self.proof_refs),
            "blocker_refs": list(self.blocker_refs),
            "input_revision_pin": self.input_revision_pin.as_dict(),
            "output_revision_pin": self.output_revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EffectReceipt":
        row = exact_fields(value, cls._FIELDS, "EffectReceipt")
        if type(row["abi_version"]) is not int or row["abi_version"] != EFFECT_RECEIPT_ABI_VERSION:
            raise ValueError("unsupported Effect Receipt ABI")
        kwargs = dict(row)
        receipt_ref = kwargs.pop("receipt_ref")
        kwargs.pop("abi_version")
        kwargs["status"] = EffectStatus(kwargs["status"])
        for name in ("observed_delta_refs", "committed_fact_refs", "proof_refs", "blocker_refs"):
            kwargs[name] = wire_refs(kwargs[name], name)
        kwargs["input_revision_pin"] = RevisionPin.from_dict(kwargs["input_revision_pin"])
        kwargs["output_revision_pin"] = RevisionPin.from_dict(kwargs["output_revision_pin"])
        rebuilt = cls.create(**kwargs)
        if receipt_ref != rebuilt.receipt_ref or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical EffectReceipt encoding")
        return rebuilt


@dataclass(frozen=True, init=False)
class NoEffectReceipt:
    abi_version: int
    receipt_ref: str
    reason: NoEffectReason
    idempotency_key: str
    journal_origin_ref: str
    journal_preterminal_ref: str
    decision_ref: str
    verified_meaning_ref: str
    expression_ref: str
    situation_ref: str
    program_ref: str
    learning_plan_ref: str | None
    obligation_ref: str | None
    proof_refs: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    input_revision_pin: RevisionPin
    output_revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "receipt_ref", "reason", "idempotency_key",
        "journal_origin_ref", "journal_preterminal_ref", "decision_ref",
        "verified_meaning_ref", "expression_ref", "situation_ref", "program_ref",
        "learning_plan_ref", "obligation_ref", "proof_refs", "blocker_refs",
        "input_revision_pin", "output_revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use NoEffectReceipt.create")

    @classmethod
    def create(
        cls,
        *,
        reason: NoEffectReason,
        idempotency_key: str,
        journal_origin_ref: str,
        journal_preterminal_ref: str,
        decision_ref: str,
        verified_meaning_ref: str,
        expression_ref: str,
        situation_ref: str,
        program_ref: str,
        learning_plan_ref: str | None,
        obligation_ref: str | None,
        proof_refs: tuple[str, ...],
        blocker_refs: tuple[str, ...],
        input_revision_pin: RevisionPin,
        output_revision_pin: RevisionPin,
    ) -> "NoEffectReceipt":
        if type(reason) is not NoEffectReason:
            raise TypeError("reason must be exact NoEffectReason")
        input_pin = exact_pin(input_revision_pin)
        output_pin = exact_pin(output_revision_pin)
        if output_pin.authority_generation != input_pin.authority_generation or output_pin.model_identity != input_pin.model_identity:
            raise ValueError("no-effect receipt changed fixed revision dimensions")
        if output_pin.effect_revision <= input_pin.effect_revision:
            raise ValueError("persisted no-effect receipt must advance effect revision")
        plan = _optional(learning_plan_ref, "learning_plan_ref")
        obligation = _optional(obligation_ref, "obligation_ref")
        if reason is NoEffectReason.LEARNING_OBLIGATION_ONLY:
            if plan is None or obligation is None or output_pin.session_revision <= input_pin.session_revision:
                raise ValueError("learning no-effect requires plan, obligation, and session revision")
        elif plan is not None or obligation is not None:
            raise ValueError("only learning no-effect may bind learning artifacts")
        values = {
            "reason": reason,
            "idempotency_key": _text(idempotency_key, "idempotency_key"),
            "journal_origin_ref": _text(journal_origin_ref, "journal_origin_ref"),
            "journal_preterminal_ref": _text(journal_preterminal_ref, "journal_preterminal_ref"),
            "decision_ref": _text(decision_ref, "decision_ref"),
            "verified_meaning_ref": _text(verified_meaning_ref, "verified_meaning_ref"),
            "expression_ref": _text(expression_ref, "expression_ref"),
            "situation_ref": _text(situation_ref, "situation_ref"),
            "program_ref": _text(program_ref, "program_ref"),
            "learning_plan_ref": plan,
            "obligation_ref": obligation,
            "proof_refs": exact_refs(proof_refs, "proof_refs"),
            "blocker_refs": exact_refs(blocker_refs, "blocker_refs"),
            "input_revision_pin": input_pin,
            "output_revision_pin": output_pin,
        }
        material = {
            "abi_version": EFFECT_RECEIPT_ABI_VERSION,
            **{
                key: item.value
                if isinstance(item, Enum)
                else list(item)
                if type(item) is tuple
                else item.as_dict()
                if type(item) is RevisionPin
                else item
                for key, item in values.items()
            },
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", EFFECT_RECEIPT_ABI_VERSION)
        object.__setattr__(obj, "receipt_ref", stable_ref("no_effect_receipt", material))
        for name, item in values.items():
            object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "receipt_ref": self.receipt_ref,
            "reason": self.reason.value,
            "idempotency_key": self.idempotency_key,
            "journal_origin_ref": self.journal_origin_ref,
            "journal_preterminal_ref": self.journal_preterminal_ref,
            "decision_ref": self.decision_ref,
            "verified_meaning_ref": self.verified_meaning_ref,
            "expression_ref": self.expression_ref,
            "situation_ref": self.situation_ref,
            "program_ref": self.program_ref,
            "learning_plan_ref": self.learning_plan_ref,
            "obligation_ref": self.obligation_ref,
            "proof_refs": list(self.proof_refs),
            "blocker_refs": list(self.blocker_refs),
            "input_revision_pin": self.input_revision_pin.as_dict(),
            "output_revision_pin": self.output_revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NoEffectReceipt":
        row = exact_fields(value, cls._FIELDS, "NoEffectReceipt")
        if type(row["abi_version"]) is not int or row["abi_version"] != EFFECT_RECEIPT_ABI_VERSION:
            raise ValueError("unsupported No-Effect Receipt ABI")
        rebuilt = cls.create(
            reason=NoEffectReason(row["reason"]),
            idempotency_key=row["idempotency_key"],
            journal_origin_ref=row["journal_origin_ref"],
            journal_preterminal_ref=row["journal_preterminal_ref"],
            decision_ref=row["decision_ref"],
            verified_meaning_ref=row["verified_meaning_ref"],
            expression_ref=row["expression_ref"],
            situation_ref=row["situation_ref"],
            program_ref=row["program_ref"],
            learning_plan_ref=row["learning_plan_ref"],
            obligation_ref=row["obligation_ref"],
            proof_refs=wire_refs(row["proof_refs"], "proof_refs"),
            blocker_refs=wire_refs(row["blocker_refs"], "blocker_refs"),
            input_revision_pin=RevisionPin.from_dict(row["input_revision_pin"]),
            output_revision_pin=RevisionPin.from_dict(row["output_revision_pin"]),
        )
        if row["receipt_ref"] != rebuilt.receipt_ref or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical NoEffectReceipt encoding")
        return rebuilt


class R3EffectGateway:
    """The sole owner of world mutation, adapter invocation, and effect journals."""

    def __init__(self, stores: SemanticStores, adapters: AdapterRegistry) -> None:
        if type(stores) is not SemanticStores:
            raise TypeError("stores must be exact SemanticStores")
        if type(adapters) is not AdapterRegistry:
            raise TypeError("adapters must be exact AdapterRegistry")
        self._stores = stores
        self._adapters = adapters

    @staticmethod
    def _effect_key(decision_ref: str, intent_ref: str | None, kind: str) -> str:
        return stable_ref(
            "r3_effect_key",
            {"decision_ref": decision_ref, "intent_ref": intent_ref, "kind": kind},
        )

    @staticmethod
    def _turn_payload(situation: SituationContext) -> dict[str, Any]:
        return {
            "session_ref": situation.session_ref,
            "turn_ref": situation.turn_ref,
            "turn_index": situation.turn_index,
            "session_phase_ref": situation.session_phase_ref,
        }

    @classmethod
    def _request_payload(
        cls, request: EffectRequest, situation: SituationContext
    ) -> dict[str, Any]:
        return {**request.as_dict(), **cls._turn_payload(situation)}

    @staticmethod
    def _fact(delta: ObservedDelta, *, decision_ref: str, operation_receipt_ref: str) -> Fact:
        material = {
            "operator": delta.operator_ref,
            "predicate": delta.predicate_ref,
            "roles": [list(row) for row in delta.role_values],
            "stance": delta.stance,
            "decision_ref": decision_ref,
            "operation_receipt_ref": operation_receipt_ref,
            "evidence_refs": list(delta.evidence_refs),
        }
        return Fact(
            fact_ref=stable_ref("fact", material),
            operator=delta.operator_ref,
            args={**dict(delta.role_values), "predicate_ref": delta.predicate_ref},
            stance=delta.stance,
            confidence=1.0,
            derived=False,
            proof={
                "source": operation_receipt_ref,
                "decision_ref": decision_ref,
                "evidence_refs": list(delta.evidence_refs),
            },
        )

    @staticmethod
    def _terminal_receipt(stored: StoredEffectJournal) -> EffectReceipt | NoEffectReceipt:
        payload = stored.receipt_payload
        if payload is None:
            raise ValueError("terminal journal lacks a receipt payload")
        if "status" in payload:
            receipt = EffectReceipt.from_dict(payload)
        elif "reason" in payload:
            receipt = NoEffectReceipt.from_dict(payload)
        else:
            raise ValueError("unknown terminal effect receipt payload")
        if receipt.receipt_ref != stored.entry.outcome_ref:
            raise ValueError("journal outcome and receipt identity disagree")
        return receipt

    def execute(
        self,
        evaluation: EvaluationBundle,
        meaning: VerifiedMeaning,
        situation: SituationContext,
        *,
        learning_plan: LearningPlan | None = None,
        obligation: DialogueObligation | None = None,
    ) -> EffectReceipt | NoEffectReceipt:
        if type(evaluation) is not EvaluationBundle or type(meaning) is not VerifiedMeaning or type(situation) is not SituationContext:
            raise TypeError("effect gateway requires exact R3 artifacts")
        if evaluation.decision.verified_meaning_ref != meaning.verified_meaning_ref:
            raise ValueError("effect gateway meaning lineage mismatch")
        if evaluation.decision.situation.situation_ref != situation.situation_ref:
            raise ValueError("effect gateway situation lineage mismatch")
        action = evaluation.decision.action
        if action is DecisionAction.ADMIT_CLAIM:
            if not situation.trusted_observation:
                raise ValueError("untrusted conversation cannot enter ADMIT_CLAIM")
            return self._commit_semantic(evaluation, meaning, situation)
        if action is DecisionAction.REQUEST_EFFECT:
            return self._execute_external(evaluation, meaning, situation)
        if action is DecisionAction.CREATE_LEARNING_OBLIGATION:
            if learning_plan is None or obligation is None:
                raise ValueError("learning decision requires exact plan and obligation")
            return self._commit_learning(evaluation, meaning, situation, learning_plan, obligation)
        reason = {
            DecisionAction.PREVIEW_TRANSITION: NoEffectReason.SIMULATION,
            DecisionAction.RETAIN_ATTRIBUTION: NoEffectReason.ATTRIBUTED_ONLY,
            DecisionAction.ACKNOWLEDGE: NoEffectReason.ATTRIBUTED_ONLY,
        }.get(action)
        if reason is None:
            reason = {
                DecisionStatus.CONFLICT: NoEffectReason.CONFLICT,
                DecisionStatus.UNKNOWN: NoEffectReason.UNKNOWN,
                DecisionStatus.BUDGET_EXHAUSTED: NoEffectReason.UNKNOWN,
            }.get(evaluation.decision.status, NoEffectReason.READ_ONLY)
        return self._persist_no_effect(evaluation, meaning, situation, reason)

    def _begin(
        self, *, key: str, intent_ref: str, decision_ref: str,
        request_payload: Mapping[str, Any]
    ) -> StoredEffectJournal:
        existing = effect_journal_get(self._stores, key)
        if existing is not None:
            return existing
        pin = self._stores.revision_pin()
        return effect_journal_begin(
            self._stores,
            idempotency_key=key,
            intent_ref=intent_ref,
            decision_ref=decision_ref,
            request_payload=request_payload,
            expected_effect_revision=pin.effect_revision,
        )

    def _persist_no_effect(
        self,
        evaluation: EvaluationBundle,
        meaning: VerifiedMeaning,
        situation: SituationContext,
        reason: NoEffectReason,
    ) -> NoEffectReceipt:
        decision = evaluation.decision
        key = self._effect_key(decision.decision_ref, None, f"no_effect:{reason.value}")
        origin = stable_ref("effect_journal_origin", {
            "decision_ref": decision.decision_ref,
            "kind": f"no_effect:{reason.value}",
        })
        stored = self._begin(
            key=key,
            intent_ref=origin,
            decision_ref=decision.decision_ref,
            request_payload={
                "journal_origin_ref": origin,
                "kind": "no_effect",
                "reason": reason.value,
                "decision_ref": decision.decision_ref,
                **self._turn_payload(situation),
            },
        )
        if stored.entry.state.terminal:
            receipt = self._terminal_receipt(stored)
            if type(receipt) is not NoEffectReceipt:
                raise ValueError("no-effect key resolved to EffectReceipt")
            return receipt
        if stored.entry.state is not EffectJournalState.PLANNED:
            raise ValueError("no-effect journal is in an invalid nonterminal state")
        current = self._stores.revision_pin()
        output = _predicted_pin(current, session=1, effects=1)
        receipt = NoEffectReceipt.create(
            reason=reason,
            idempotency_key=key,
            journal_origin_ref=origin,
            journal_preterminal_ref=stored.entry.journal_ref,
            decision_ref=decision.decision_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            program_ref=meaning.program_ref,
            learning_plan_ref=None,
            obligation_ref=None,
            proof_refs=decision.proof_refs,
            blocker_refs=decision.blocker_refs,
            input_revision_pin=situation.revision_pin,
            output_revision_pin=output,
        )
        terminal = effect_journal_transition(
            self._stores,
            idempotency_key=key,
            expected_state=EffectJournalState.PLANNED,
            next_state=EffectJournalState.NO_EFFECT,
            observation_payload=None,
            outcome_ref=receipt.receipt_ref,
            receipt_payload=receipt.as_dict(),
            blocker_refs=decision.blocker_refs,
            expected_effect_revision=current.effect_revision,
        )
        if terminal.entry.state is not EffectJournalState.NO_EFFECT:
            raise RuntimeError("no-effect journal did not terminate")
        if self._stores.revision_pin() != receipt.output_revision_pin:
            raise RuntimeError("no-effect persistence revision mismatch")
        return receipt

    def _commit_learning(
        self,
        evaluation: EvaluationBundle,
        meaning: VerifiedMeaning,
        situation: SituationContext,
        plan: LearningPlan,
        obligation: DialogueObligation,
    ) -> NoEffectReceipt:
        decision = evaluation.decision
        if plan.decision_ref != decision.decision_ref or obligation.plan_ref != plan.plan_ref:
            raise ValueError("learning artifacts do not bind the Decision")
        key = self._effect_key(decision.decision_ref, plan.plan_ref, "learning_obligation")
        origin = stable_ref("effect_journal_origin", {
            "decision_ref": decision.decision_ref,
            "plan_ref": plan.plan_ref,
            "kind": "learning_obligation",
        })
        stored = self._begin(
            key=key,
            intent_ref=plan.plan_ref,
            decision_ref=decision.decision_ref,
            request_payload={
                "journal_origin_ref": origin,
                "kind": "learning_obligation",
                "plan_ref": plan.plan_ref,
                "obligation_ref": obligation.obligation_ref,
                **self._turn_payload(situation),
            },
        )
        if stored.entry.state.terminal:
            receipt = self._terminal_receipt(stored)
            if type(receipt) is not NoEffectReceipt:
                raise ValueError("learning key resolved to EffectReceipt")
            return receipt
        if stored.entry.state is not EffectJournalState.PLANNED:
            raise ValueError("learning journal is in an invalid state")
        current = self._stores.revision_pin()
        output = _predicted_pin(current, session=1, effects=1)
        receipt = NoEffectReceipt.create(
            reason=NoEffectReason.LEARNING_OBLIGATION_ONLY,
            idempotency_key=key,
            journal_origin_ref=origin,
            journal_preterminal_ref=stored.entry.journal_ref,
            decision_ref=decision.decision_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            program_ref=meaning.program_ref,
            learning_plan_ref=plan.plan_ref,
            obligation_ref=obligation.obligation_ref,
            proof_refs=decision.proof_refs,
            blocker_refs=(),
            input_revision_pin=situation.revision_pin,
            output_revision_pin=output,
        )
        terminal, actual = commit_learning_outcome(
            self._stores,
            session_ref=situation.session_ref,
            obligation_ref=obligation.obligation_ref,
            obligation_payload=obligation.as_dict(),
            idempotency_key=key,
            intent_ref=plan.plan_ref,
            decision_ref=decision.decision_ref,
            receipt_payload=receipt.as_dict(),
            expected_revision_pin=current,
        )
        if actual != output or terminal.entry.outcome_ref != receipt.receipt_ref:
            raise RuntimeError("learning outcome revision or receipt mismatch")
        return receipt

    def _commit_semantic(
        self,
        evaluation: EvaluationBundle,
        meaning: VerifiedMeaning,
        situation: SituationContext,
    ) -> EffectReceipt:
        decision = evaluation.decision
        if not evaluation.state_deltas:
            raise ValueError("ADMIT_CLAIM requires state deltas")
        key = self._effect_key(decision.decision_ref, None, "trusted_semantic_admission")
        origin = stable_ref("effect_journal_origin", {
            "decision_ref": decision.decision_ref,
            "kind": "trusted_semantic_admission",
        })
        expected = tuple(
            ObservedDelta.from_state_delta(delta, evidence_refs=situation.source_refs)
            for delta in evaluation.state_deltas
        )
        stored = self._begin(
            key=key,
            intent_ref=origin,
            decision_ref=decision.decision_ref,
            request_payload={
                "journal_origin_ref": origin,
                "kind": "trusted_semantic_admission",
                "expected_deltas": [row.as_dict() for row in expected],
                **self._turn_payload(situation),
            },
        )
        if stored.entry.state.terminal:
            receipt = self._terminal_receipt(stored)
            if type(receipt) is not EffectReceipt:
                raise ValueError("semantic admission key resolved to NoEffectReceipt")
            return receipt
        current = self._stores.revision_pin()
        if stored.entry.state is EffectJournalState.PLANNED:
            stored = effect_journal_transition(
                self._stores, idempotency_key=key,
                expected_state=EffectJournalState.PLANNED,
                next_state=EffectJournalState.AUTHORIZED,
                observation_payload=None, outcome_ref=None, receipt_payload=None,
                blocker_refs=(), expected_effect_revision=current.effect_revision,
            )
            current = self._stores.revision_pin()
        if stored.entry.state is EffectJournalState.AUTHORIZED:
            observation = {
                "source_kind": "trusted_evidence",
                "observed_deltas": [row.as_dict() for row in expected],
                "evidence_refs": list(situation.source_refs),
            }
            stored = effect_journal_transition(
                self._stores, idempotency_key=key,
                expected_state=EffectJournalState.AUTHORIZED,
                next_state=EffectJournalState.OBSERVED,
                observation_payload=observation, outcome_ref=None,
                receipt_payload=None, blocker_refs=(),
                expected_effect_revision=current.effect_revision,
            )
        if stored.entry.state is not EffectJournalState.OBSERVED:
            raise ValueError("semantic admission journal could not reach observed")
        return self._commit_observation(
            evaluation=evaluation,
            meaning=meaning,
            situation=situation,
            key=key,
            origin_ref=origin,
            preterminal=stored,
            observed=expected,
            adapter_ref=None,
            adapter_result=None,
            operation_receipt_ref=stable_ref("trusted_evidence_receipt", {
                "situation_ref": situation.situation_ref,
                "source_refs": list(situation.source_refs),
            }),
            effect_intent_ref=None,
            actor_ref=situation.speaker_ref,
            event_type_ref="event:semantic_admission",
            transition_ref=None,
        )

    def _request(self, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
                 situation: SituationContext) -> tuple[Any, EffectRequest]:
        decision = evaluation.decision
        intents = tuple(row for row in evaluation.effect_intents if row.effect_intent_ref == decision.effect_intent_ref)
        if len(intents) != 1:
            raise ValueError("Decision effect_intent_ref is not uniquely present")
        intent = intents[0]
        if intent.adapter_ref is None:
            raise ValueError("external effect intent requires adapter_ref")
        expected = tuple(
            ObservedDelta.from_state_delta(delta, evidence_refs=(intent.effect_intent_ref,))
            for delta in intent.proposed_deltas
        )
        key = self._effect_key(decision.decision_ref, intent.effect_intent_ref, "external")
        request = EffectRequest.create(
            idempotency_key=key,
            decision_ref=decision.decision_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            program_ref=meaning.program_ref,
            effect_intent_ref=intent.effect_intent_ref,
            actor_ref=intent.actor_ref,
            event_type_ref=intent.event_type_ref,
            target_ref=intent.target_ref,
            transition_ref=intent.transition_ref,
            adapter_ref=intent.adapter_ref,
            expected_deltas=expected,
            input_revision_pin=situation.revision_pin,
        )
        return intent, request

    @staticmethod
    def _validate_adapter_result(result: AdapterResult, request: EffectRequest) -> None:
        if type(result) is not AdapterResult:
            raise TypeError("adapter returned non-canonical AdapterResult")
        if AdapterResult.from_dict(result.as_dict()) != result:
            raise ValueError("adapter returned non-canonical result")
        if (
            result.adapter_ref != request.adapter_ref
            or result.idempotency_key != request.idempotency_key
            or result.request_ref != request.request_ref
            or result.event_type_ref != request.event_type_ref
            or result.target_ref != request.target_ref
            or result.transition_ref != request.transition_ref
        ):
            raise ValueError("adapter result lineage does not match EffectRequest")
        if result.status is AdapterStatus.SUCCEEDED:
            expected = sorted(row.semantic_signature for row in request.expected_deltas)
            observed = sorted(row.semantic_signature for row in result.observed_deltas)
            if observed != expected:
                raise ValueError("adapter observation contradicts expected transition")

    def _pending(
        self, *, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
        situation: SituationContext, request: EffectRequest,
        stored: StoredEffectJournal, blocker_refs: tuple[str, ...],
        adapter_result_ref: str | None,
    ) -> EffectReceipt:
        return EffectReceipt.create(
            status=EffectStatus.PENDING,
            idempotency_key=request.idempotency_key,
            journal_origin_ref=request.journal_origin_ref,
            journal_preterminal_ref=stored.entry.journal_ref,
            reconciliation_required=True,
            decision_ref=evaluation.decision.decision_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            program_ref=meaning.program_ref,
            effect_intent_ref=request.effect_intent_ref,
            actor_ref=request.actor_ref,
            event_type_ref=request.event_type_ref,
            transition_ref=request.transition_ref,
            adapter_ref=request.adapter_ref,
            adapter_result_ref=adapter_result_ref,
            operation_receipt_ref=None,
            observed_delta_refs=(),
            committed_fact_refs=(),
            proof_refs=evaluation.decision.proof_refs,
            blocker_refs=blocker_refs,
            input_revision_pin=situation.revision_pin,
            output_revision_pin=self._stores.revision_pin(),
        )

    def _terminal_failure(
        self, *, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
        situation: SituationContext, request: EffectRequest,
        stored: StoredEffectJournal, result: AdapterResult | None,
        status: EffectStatus, blockers: tuple[str, ...],
    ) -> EffectReceipt:
        current = self._stores.revision_pin()
        output = _predicted_pin(current, session=1, effects=1)
        receipt = EffectReceipt.create(
            status=status,
            idempotency_key=request.idempotency_key,
            journal_origin_ref=request.journal_origin_ref,
            journal_preterminal_ref=stored.entry.journal_ref,
            reconciliation_required=False,
            decision_ref=evaluation.decision.decision_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            program_ref=meaning.program_ref,
            effect_intent_ref=request.effect_intent_ref,
            actor_ref=request.actor_ref,
            event_type_ref=request.event_type_ref,
            transition_ref=request.transition_ref,
            adapter_ref=request.adapter_ref,
            adapter_result_ref=None if result is None else result.result_ref,
            operation_receipt_ref=None if result is None else result.operation_receipt_ref,
            observed_delta_refs=(),
            committed_fact_refs=(),
            proof_refs=evaluation.decision.proof_refs,
            blocker_refs=blockers,
            input_revision_pin=situation.revision_pin,
            output_revision_pin=output,
        )
        terminal = effect_journal_transition(
            self._stores,
            idempotency_key=request.idempotency_key,
            expected_state=stored.entry.state,
            next_state=EffectJournalState.FAILED,
            observation_payload=None,
            outcome_ref=receipt.receipt_ref,
            receipt_payload=receipt.as_dict(),
            blocker_refs=blockers,
            expected_effect_revision=current.effect_revision,
        )
        if terminal.entry.outcome_ref != receipt.receipt_ref:
            raise RuntimeError("failed effect journal did not bind receipt")
        if self._stores.revision_pin() != receipt.output_revision_pin:
            raise RuntimeError("failed effect persistence revision mismatch")
        return receipt

    def _execute_external(
        self, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
        situation: SituationContext,
    ) -> EffectReceipt:
        intent, request = self._request(evaluation, meaning, situation)
        adapter = self._adapters.get(request.adapter_ref)
        if adapter is None:
            stored = self._begin(
                key=request.idempotency_key,
                intent_ref=request.effect_intent_ref,
                decision_ref=request.decision_ref,
                request_payload=self._request_payload(request, situation),
            )
            if stored.entry.state.terminal:
                receipt = self._terminal_receipt(stored)
                if type(receipt) is not EffectReceipt:
                    raise ValueError("external effect key resolved to NoEffectReceipt")
                return receipt
            return self._terminal_failure(
                evaluation=evaluation, meaning=meaning, situation=situation,
                request=request, stored=stored, result=None,
                status=EffectStatus.ADAPTER_MISSING,
                blockers=("adapter_missing", request.adapter_ref),
            )

        stored = self._begin(
            key=request.idempotency_key,
            intent_ref=request.effect_intent_ref,
            decision_ref=request.decision_ref,
            request_payload=self._request_payload(request, situation),
        )
        if stored.entry.state.terminal:
            receipt = self._terminal_receipt(stored)
            if type(receipt) is not EffectReceipt:
                raise ValueError("external effect key resolved to NoEffectReceipt")
            return receipt

        current = self._stores.revision_pin()
        if stored.entry.state is EffectJournalState.PLANNED:
            stored = effect_journal_transition(
                self._stores, idempotency_key=request.idempotency_key,
                expected_state=EffectJournalState.PLANNED,
                next_state=EffectJournalState.AUTHORIZED,
                observation_payload=None, outcome_ref=None, receipt_payload=None,
                blocker_refs=(), expected_effect_revision=current.effect_revision,
            )
            current = self._stores.revision_pin()
        if stored.entry.state is EffectJournalState.AUTHORIZED:
            stored = effect_journal_transition(
                self._stores, idempotency_key=request.idempotency_key,
                expected_state=EffectJournalState.AUTHORIZED,
                next_state=EffectJournalState.INVOCATION_STARTED,
                observation_payload=None, outcome_ref=None, receipt_payload=None,
                blocker_refs=(), expected_effect_revision=current.effect_revision,
            )
            invoke = True
        elif stored.entry.state in {
            EffectJournalState.INVOCATION_STARTED,
            EffectJournalState.PENDING_RECONCILIATION,
        }:
            invoke = False
        elif stored.entry.state is EffectJournalState.OBSERVED:
            return self._commit_observed_request(
                evaluation, meaning, situation, request, stored
            )
        else:
            raise ValueError("external effect journal is in an invalid state")

        try:
            result = adapter.invoke(request) if invoke else adapter.reconcile(request)
            self._validate_adapter_result(result, request)
        except Exception as exc:
            blockers = (
                "adapter_invocation_outcome_unknown" if invoke else "adapter_reconciliation_failed",
                stable_ref("adapter_exception", {"type": type(exc).__name__, "request_ref": request.request_ref}),
            )
            current = self._stores.revision_pin()
            pending = effect_journal_transition(
                self._stores,
                idempotency_key=request.idempotency_key,
                expected_state=stored.entry.state,
                next_state=EffectJournalState.PENDING_RECONCILIATION,
                observation_payload=None,
                outcome_ref=None,
                receipt_payload=None,
                blocker_refs=blockers,
                expected_effect_revision=current.effect_revision,
            )
            return self._pending(
                evaluation=evaluation, meaning=meaning, situation=situation,
                request=request, stored=pending, blocker_refs=blockers,
                adapter_result_ref=None,
            )

        if result.status is AdapterStatus.SUCCEEDED:
            current = self._stores.revision_pin()
            observed = effect_journal_transition(
                self._stores,
                idempotency_key=request.idempotency_key,
                expected_state=stored.entry.state,
                next_state=EffectJournalState.OBSERVED,
                observation_payload=result.as_dict(),
                outcome_ref=None,
                receipt_payload=None,
                blocker_refs=(),
                expected_effect_revision=current.effect_revision,
            )
            return self._commit_observation(
                evaluation=evaluation,
                meaning=meaning,
                situation=situation,
                key=request.idempotency_key,
                origin_ref=request.journal_origin_ref,
                preterminal=observed,
                observed=result.observed_deltas,
                adapter_ref=request.adapter_ref,
                adapter_result=result,
                operation_receipt_ref=result.operation_receipt_ref or result.result_ref,
                effect_intent_ref=request.effect_intent_ref,
                actor_ref=request.actor_ref,
                event_type_ref=request.event_type_ref,
                transition_ref=request.transition_ref,
            )

        if result.status in {AdapterStatus.PENDING, AdapterStatus.NOT_FOUND}:
            blockers = result.blocker_refs
            if result.status is AdapterStatus.NOT_FOUND:
                blockers = tuple(dict.fromkeys((*blockers, "adapter_reconciliation_not_found")))
            current = self._stores.revision_pin()
            pending = effect_journal_transition(
                self._stores,
                idempotency_key=request.idempotency_key,
                expected_state=stored.entry.state,
                next_state=EffectJournalState.PENDING_RECONCILIATION,
                observation_payload=None,
                outcome_ref=None,
                receipt_payload=None,
                blocker_refs=blockers,
                expected_effect_revision=current.effect_revision,
            )
            return self._pending(
                evaluation=evaluation, meaning=meaning, situation=situation,
                request=request, stored=pending, blocker_refs=blockers,
                adapter_result_ref=result.result_ref,
            )

        return self._terminal_failure(
            evaluation=evaluation, meaning=meaning, situation=situation,
            request=request, stored=stored, result=result,
            status=EffectStatus.FAILED, blockers=result.blocker_refs,
        )

    def _commit_observed_request(
        self, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
        situation: SituationContext, request: EffectRequest,
        stored: StoredEffectJournal,
    ) -> EffectReceipt:
        payload = stored.entry.observation_payload
        if payload is None:
            raise ValueError("observed journal lacks adapter observation")
        result = AdapterResult.from_dict(payload)
        self._validate_adapter_result(result, request)
        return self._commit_observation(
            evaluation=evaluation,
            meaning=meaning,
            situation=situation,
            key=request.idempotency_key,
            origin_ref=request.journal_origin_ref,
            preterminal=stored,
            observed=result.observed_deltas,
            adapter_ref=request.adapter_ref,
            adapter_result=result,
            operation_receipt_ref=result.operation_receipt_ref or result.result_ref,
            effect_intent_ref=request.effect_intent_ref,
            actor_ref=request.actor_ref,
            event_type_ref=request.event_type_ref,
            transition_ref=request.transition_ref,
        )

    def _commit_observation(
        self, *, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
        situation: SituationContext, key: str, origin_ref: str,
        preterminal: StoredEffectJournal, observed: tuple[ObservedDelta, ...],
        adapter_ref: str | None, adapter_result: AdapterResult | None,
        operation_receipt_ref: str, effect_intent_ref: str | None,
        actor_ref: str, event_type_ref: str, transition_ref: str | None,
    ) -> EffectReceipt:
        if preterminal.entry.state is not EffectJournalState.OBSERVED:
            raise ValueError("commit requires observed journal state")
        facts = tuple(
            self._fact(delta, decision_ref=evaluation.decision.decision_ref,
                       operation_receipt_ref=operation_receipt_ref)
            for delta in observed
        )
        current = self._stores.revision_pin()
        output = _predicted_pin(current, world=1, session=1, effects=1)
        receipt = EffectReceipt.create(
            status=EffectStatus.COMMITTED,
            idempotency_key=key,
            journal_origin_ref=origin_ref,
            journal_preterminal_ref=preterminal.entry.journal_ref,
            reconciliation_required=False,
            decision_ref=evaluation.decision.decision_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            program_ref=meaning.program_ref,
            effect_intent_ref=effect_intent_ref,
            actor_ref=actor_ref,
            event_type_ref=event_type_ref,
            transition_ref=transition_ref,
            adapter_ref=adapter_ref,
            adapter_result_ref=None if adapter_result is None else adapter_result.result_ref,
            operation_receipt_ref=operation_receipt_ref,
            observed_delta_refs=tuple(row.observed_delta_ref for row in observed),
            committed_fact_refs=tuple(row.fact_ref for row in facts),
            proof_refs=evaluation.decision.proof_refs,
            blocker_refs=(),
            input_revision_pin=situation.revision_pin,
            output_revision_pin=output,
        )
        journal, actual = effect_journal_commit(
            self._stores,
            idempotency_key=key,
            observation_payload={
                "observed_deltas": [row.as_dict() for row in observed],
                "operation_receipt_ref": operation_receipt_ref,
            },
            outcome_ref=receipt.receipt_ref,
            receipt_payload=receipt.as_dict(),
            facts=facts,
            expected_revision_pin=current,
        )
        if actual != output or journal.entry.outcome_ref != receipt.receipt_ref:
            raise RuntimeError("atomic effect commit revision or identity mismatch")
        return receipt
