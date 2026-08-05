"""Canonical R3 evaluation artifacts.

These records are the proof-bearing products consumed by Decision, EFFECT,
learning, response construction and R4 episode generation. They contain no
surface dispatch state and preserve complete content identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .cycle import SemanticMode
from .decision import Decision, DecisionContribution
from .expressions import SemanticExpression
from .persistence import RevisionPin
from .situation import SituationContext

R3_ARTIFACT_ABI_VERSION = 2
_MAX_TEXT = 512
_MAX_ROWS = 512
_MAX_PAYLOAD_DEPTH = 8
_MAX_PAYLOAD_NODES = 4096

__all__ = [
    "R3_ARTIFACT_ABI_VERSION",
    "ProofNode",
    "ProofGraph",
    "QueryStatus",
    "QueryResult",
    "PlacementMode",
    "ClaimOccurrence",
    "AdmissionStatus",
    "AdmissionDecision",
    "StateDelta",
    "StateQueryResult",
    "TransitionStatus",
    "TransitionEvaluation",
    "CapabilityStatus",
    "CapabilityEvaluation",
    "EffectIntent",
    "LearningDraft",
    "ModeEvaluation",
    "EvaluationBundle",
]


def _text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value and not allow_empty:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > _MAX_TEXT:
        raise ValueError(f"{name} exceeds {_MAX_TEXT} characters")
    return value


def _optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _refs(value: object, name: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be exact tuple")
    if len(value) > _MAX_ROWS:
        raise ValueError(f"{name} exceeds row bound")
    if nonempty and not value:
        raise ValueError(f"{name} must be nonempty")
    for item in value:
        _text(item, f"{name} item")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must contain unique refs")
    return value


def _pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be exact tuple")
    if len(value) > _MAX_ROWS:
        raise ValueError(f"{name} exceeds row bound")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not tuple or len(row) != 2:
            raise TypeError(f"{name} rows must be exact pairs")
        rows.append((_text(row[0], f"{name} key"), _text(row[1], f"{name} value")))
    if len(rows) != len({row[0] for row in rows}):
        raise ValueError(f"{name} keys must be unique")
    return tuple(rows)


def _pin(value: object) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    if RevisionPin.from_dict(value.as_dict()) != value:
        raise ValueError("revision_pin is non-canonical")
    return value


def _freeze_json(value: object, *, depth: int = 0, budget: list[int] | None = None) -> object:
    if budget is None:
        budget = [0]
    budget[0] += 1
    if budget[0] > _MAX_PAYLOAD_NODES:
        raise ValueError("artifact payload exceeds node bound")
    if depth > _MAX_PAYLOAD_DEPTH:
        raise ValueError("artifact payload exceeds depth bound")
    if value is None or type(value) in {bool, int, float}:
        if type(value) is float and (value != value or value in {float("inf"), float("-inf")}):
            raise ValueError("artifact payload floats must be finite")
        return value
    if type(value) is str:
        _text(value, "payload string", allow_empty=True)
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_ROWS:
            raise ValueError("artifact payload mapping exceeds bound")
        frozen: dict[str, object] = {}
        for key, item in value.items():
            _text(key, "payload key")
            frozen[key] = _freeze_json(item, depth=depth + 1, budget=budget)
        return MappingProxyType(frozen)
    if type(value) in {tuple, list}:
        if len(value) > _MAX_ROWS:
            raise ValueError("artifact payload sequence exceeds bound")
        return tuple(_freeze_json(item, depth=depth + 1, budget=budget) for item in value)
    raise TypeError("artifact payload must contain bounded JSON values")


def _wire_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _wire_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_wire_json(item) for item in value]
    return value


def _exact(data: object, fields: frozenset[str], name: str) -> dict[str, Any]:
    if type(data) is not dict:
        raise TypeError(f"{name} payload must be exact dict")
    if frozenset(data) != fields:
        raise ValueError(f"{name} fields mismatch")
    return data


def _wire_refs(value: object, name: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} must be exact list")
    return _refs(tuple(value), name, nonempty=nonempty)


def _wire_pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if type(value) is not list:
        raise TypeError(f"{name} must be exact list")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not list or len(row) != 2:
            raise TypeError(f"{name} rows must be two-item lists")
        rows.append((row[0], row[1]))
    return _pairs(tuple(rows), name)


@dataclass(frozen=True, init=False)
class ProofNode:
    abi_version: int
    proof_node_ref: str
    conclusion_ref: str
    source_fact_refs: tuple[str, ...]
    rule_ref: str | None
    premise_node_refs: tuple[str, ...]
    substitutions: tuple[tuple[str, str], ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "proof_node_ref", "conclusion_ref", "source_fact_refs",
        "rule_ref", "premise_node_refs", "substitutions", "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ProofNode.create")

    @classmethod
    def create(cls, *, conclusion_ref: str, source_fact_refs: tuple[str, ...],
               rule_ref: str | None, premise_node_refs: tuple[str, ...],
               substitutions: tuple[tuple[str, str], ...],
               revision_pin: RevisionPin) -> "ProofNode":
        values = {
            "conclusion_ref": _text(conclusion_ref, "conclusion_ref"),
            "source_fact_refs": _refs(source_fact_refs, "source_fact_refs"),
            "rule_ref": _optional_text(rule_ref, "rule_ref"),
            "premise_node_refs": _refs(premise_node_refs, "premise_node_refs"),
            "substitutions": _pairs(substitutions, "substitutions"),
            "revision_pin": _pin(revision_pin),
        }
        if bool(values["source_fact_refs"]) == bool(values["premise_node_refs"]):
            raise ValueError("proof node must be either fact-backed or premise-backed")
        material = {
            "abi_version": R3_ARTIFACT_ABI_VERSION,
            "conclusion_ref": values["conclusion_ref"],
            "source_fact_refs": list(values["source_fact_refs"]),
            "rule_ref": values["rule_ref"],
            "premise_node_refs": list(values["premise_node_refs"]),
            "substitutions": [list(row) for row in values["substitutions"]],
            "revision_pin": values["revision_pin"].as_dict(),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", R3_ARTIFACT_ABI_VERSION)
        object.__setattr__(obj, "proof_node_ref", stable_ref("r3_proof_node", material))
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "proof_node_ref": self.proof_node_ref,
            "conclusion_ref": self.conclusion_ref,
            "source_fact_refs": list(self.source_fact_refs), "rule_ref": self.rule_ref,
            "premise_node_refs": list(self.premise_node_refs),
            "substitutions": [list(row) for row in self.substitutions],
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProofNode":
        row = _exact(data, cls._FIELDS, "ProofNode")
        rebuilt = cls.create(
            conclusion_ref=row["conclusion_ref"],
            source_fact_refs=_wire_refs(row["source_fact_refs"], "source_fact_refs"),
            rule_ref=row["rule_ref"],
            premise_node_refs=_wire_refs(row["premise_node_refs"], "premise_node_refs"),
            substitutions=_wire_pairs(row["substitutions"], "substitutions"),
            revision_pin=RevisionPin.from_dict(row["revision_pin"]),
        )
        if row["proof_node_ref"] != rebuilt.proof_node_ref or rebuilt.as_dict() != row:
            raise ValueError("non-canonical ProofNode")
        return rebuilt


@dataclass(frozen=True, init=False)
class ProofGraph:
    abi_version: int
    proof_ref: str
    root_node_refs: tuple[str, ...]
    nodes: tuple[ProofNode, ...]
    semantic_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    rule_refs: tuple[str, ...]
    transient_witness_refs: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "proof_ref", "root_node_refs", "nodes", "semantic_refs",
        "source_refs", "rule_refs", "transient_witness_refs", "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ProofGraph.create")

    @classmethod
    def create(cls, *, root_node_refs: tuple[str, ...], nodes: tuple[ProofNode, ...],
               semantic_refs: tuple[str, ...], source_refs: tuple[str, ...],
               rule_refs: tuple[str, ...], transient_witness_refs: tuple[str, ...],
               revision_pin: RevisionPin) -> "ProofGraph":
        roots = _refs(root_node_refs, "root_node_refs", nonempty=True)
        if type(nodes) is not tuple or not nodes or len(nodes) > _MAX_ROWS:
            raise ValueError("nodes must be a bounded nonempty tuple")
        if any(type(node) is not ProofNode for node in nodes):
            raise TypeError("nodes must contain exact ProofNode")
        refs = tuple(node.proof_node_ref for node in nodes)
        if len(refs) != len(set(refs)):
            raise ValueError("proof nodes must be unique")
        by_ref = {node.proof_node_ref: node for node in nodes}
        if set(roots) - set(by_ref):
            raise ValueError("proof roots contain unknown nodes")
        for node in nodes:
            if node.revision_pin != revision_pin:
                raise ValueError("proof node revision pin mismatch")
            if set(node.premise_node_refs) - set(by_ref):
                raise ValueError("proof node references unknown premise")
        visiting: set[str] = set(); visited: set[str] = set()
        def visit(ref: str) -> None:
            if ref in visiting: raise ValueError("proof graph contains a cycle")
            if ref in visited: return
            visiting.add(ref)
            for child in by_ref[ref].premise_node_refs: visit(child)
            visiting.remove(ref); visited.add(ref)
        for ref in roots: visit(ref)
        if visited != set(by_ref):
            raise ValueError("proof graph contains unreachable nodes")
        values = {
            "root_node_refs": roots, "nodes": nodes,
            "semantic_refs": _refs(semantic_refs, "semantic_refs"),
            "source_refs": _refs(source_refs, "source_refs"),
            "rule_refs": _refs(rule_refs, "rule_refs"),
            "transient_witness_refs": _refs(transient_witness_refs, "transient_witness_refs"),
            "revision_pin": _pin(revision_pin),
        }
        material = {
            "abi_version": R3_ARTIFACT_ABI_VERSION,
            "root_node_refs": list(roots), "nodes": [node.as_dict() for node in nodes],
            "semantic_refs": list(values["semantic_refs"]),
            "source_refs": list(values["source_refs"]), "rule_refs": list(values["rule_refs"]),
            "transient_witness_refs": list(values["transient_witness_refs"]),
            "revision_pin": revision_pin.as_dict(),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", R3_ARTIFACT_ABI_VERSION)
        object.__setattr__(obj, "proof_ref", stable_ref("r3_proof_graph", material))
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "proof_ref": self.proof_ref,
            "root_node_refs": list(self.root_node_refs),
            "nodes": [node.as_dict() for node in self.nodes],
            "semantic_refs": list(self.semantic_refs), "source_refs": list(self.source_refs),
            "rule_refs": list(self.rule_refs),
            "transient_witness_refs": list(self.transient_witness_refs),
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProofGraph":
        row = _exact(data, cls._FIELDS, "ProofGraph")
        if type(row["nodes"]) is not list: raise TypeError("nodes must be exact list")
        rebuilt = cls.create(
            root_node_refs=_wire_refs(row["root_node_refs"], "root_node_refs", nonempty=True),
            nodes=tuple(ProofNode.from_dict(item) for item in row["nodes"]),
            semantic_refs=_wire_refs(row["semantic_refs"], "semantic_refs"),
            source_refs=_wire_refs(row["source_refs"], "source_refs"),
            rule_refs=_wire_refs(row["rule_refs"], "rule_refs"),
            transient_witness_refs=_wire_refs(row["transient_witness_refs"], "transient_witness_refs"),
            revision_pin=RevisionPin.from_dict(row["revision_pin"]),
        )
        if row["proof_ref"] != rebuilt.proof_ref or rebuilt.as_dict() != row:
            raise ValueError("non-canonical ProofGraph")
        return rebuilt


class QueryStatus(Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"
    PARTIAL = "partial"
    BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True, init=False)
class QueryResult:
    abi_version: int
    query_result_ref: str
    expression_ref: str
    status: QueryStatus
    bindings: tuple[tuple[str, str], ...]
    proof: ProofGraph | None
    retrieval_refs: tuple[str, ...]
    rounds: int
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "query_result_ref", "expression_ref", "status", "bindings",
        "proof", "retrieval_refs", "rounds", "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: raise TypeError("use QueryResult.create")

    @classmethod
    def create(cls, *, expression_ref: str, status: QueryStatus,
               bindings: tuple[tuple[str, str], ...], proof: ProofGraph | None,
               retrieval_refs: tuple[str, ...], rounds: int,
               revision_pin: RevisionPin) -> "QueryResult":
        if type(status) is not QueryStatus: raise TypeError("status must be QueryStatus")
        if type(rounds) is not int or not 0 <= rounds <= 1024: raise ValueError("rounds out of bound")
        if proof is not None and type(proof) is not ProofGraph: raise TypeError("proof must be ProofGraph or None")
        if status in {QueryStatus.SUPPORTED, QueryStatus.CONTRADICTED, QueryStatus.CONFLICT} and proof is None:
            raise ValueError("decisive query statuses require proof")
        if status in {QueryStatus.UNKNOWN, QueryStatus.BUDGET_EXHAUSTED} and bindings:
            raise ValueError("unknown/budget-exhausted query cannot carry bindings")
        if proof is not None and proof.revision_pin != revision_pin: raise ValueError("proof pin mismatch")
        values = {
            "expression_ref": _text(expression_ref, "expression_ref"), "status": status,
            "bindings": _pairs(bindings, "bindings"), "proof": proof,
            "retrieval_refs": _refs(retrieval_refs, "retrieval_refs"), "rounds": rounds,
            "revision_pin": _pin(revision_pin),
        }
        material = {
            "abi_version": R3_ARTIFACT_ABI_VERSION, "expression_ref": values["expression_ref"],
            "status": status.value, "bindings": [list(row) for row in values["bindings"]],
            "proof": proof.as_dict() if proof else None,
            "retrieval_refs": list(values["retrieval_refs"]), "rounds": rounds,
            "revision_pin": revision_pin.as_dict(),
        }
        obj = object.__new__(cls); object.__setattr__(obj, "abi_version", R3_ARTIFACT_ABI_VERSION)
        object.__setattr__(obj, "query_result_ref", stable_ref("r3_query_result", material))
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "query_result_ref": self.query_result_ref,
            "expression_ref": self.expression_ref, "status": self.status.value,
            "bindings": [list(row) for row in self.bindings],
            "proof": self.proof.as_dict() if self.proof else None,
            "retrieval_refs": list(self.retrieval_refs), "rounds": self.rounds,
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "QueryResult":
        row = _exact(data, cls._FIELDS, "QueryResult")
        rebuilt = cls.create(
            expression_ref=row["expression_ref"], status=QueryStatus(row["status"]),
            bindings=_wire_pairs(row["bindings"], "bindings"),
            proof=None if row["proof"] is None else ProofGraph.from_dict(row["proof"]),
            retrieval_refs=_wire_refs(row["retrieval_refs"], "retrieval_refs"),
            rounds=row["rounds"], revision_pin=RevisionPin.from_dict(row["revision_pin"]),
        )
        if row["query_result_ref"] != rebuilt.query_result_ref or rebuilt.as_dict() != row:
            raise ValueError("non-canonical QueryResult")
        return rebuilt


class PlacementMode(Enum):
    OBSERVED = "observed"
    REPORTED = "reported"
    BELIEVED = "believed"
    DESIRED = "desired"
    PREDICTED = "predicted"
    QUOTED = "quoted"
    SIMULATED = "simulated"
    CORRECTED = "corrected"


@dataclass(frozen=True, init=False)
class ClaimOccurrence:
    abi_version: int
    occurrence_ref: str
    expression_ref: str
    root_ref: str
    source_ref: str
    evidence_refs: tuple[str, ...]
    interval_ref: str
    confidence_q: int
    modality_ref: str
    scope_ref: str
    placement: PlacementMode
    situation_ref: str
    supersedes_ref: str | None
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "occurrence_ref", "expression_ref", "root_ref", "source_ref",
        "evidence_refs", "interval_ref", "confidence_q", "modality_ref", "scope_ref",
        "placement", "situation_ref", "supersedes_ref", "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: raise TypeError("use ClaimOccurrence.create")

    @classmethod
    def create(cls, *, expression_ref: str, root_ref: str, source_ref: str,
               evidence_refs: tuple[str, ...], interval_ref: str, confidence_q: int,
               modality_ref: str, scope_ref: str, placement: PlacementMode,
               situation_ref: str, supersedes_ref: str | None,
               revision_pin: RevisionPin) -> "ClaimOccurrence":
        if type(placement) is not PlacementMode: raise TypeError("placement must be PlacementMode")
        if type(confidence_q) is not int or not 0 <= confidence_q <= 1_000_000:
            raise ValueError("confidence_q out of range")
        values = {
            "expression_ref": _text(expression_ref, "expression_ref"), "root_ref": _text(root_ref, "root_ref"),
            "source_ref": _text(source_ref, "source_ref"), "evidence_refs": _refs(evidence_refs, "evidence_refs"),
            "interval_ref": _text(interval_ref, "interval_ref"), "confidence_q": confidence_q,
            "modality_ref": _text(modality_ref, "modality_ref"), "scope_ref": _text(scope_ref, "scope_ref"),
            "placement": placement, "situation_ref": _text(situation_ref, "situation_ref"),
            "supersedes_ref": _optional_text(supersedes_ref, "supersedes_ref"), "revision_pin": _pin(revision_pin),
        }
        material = {"abi_version": R3_ARTIFACT_ABI_VERSION, **{
            k: (v.value if isinstance(v, Enum) else list(v) if type(v) is tuple else v.as_dict() if type(v) is RevisionPin else v)
            for k, v in values.items()
        }}
        obj = object.__new__(cls); object.__setattr__(obj, "abi_version", R3_ARTIFACT_ABI_VERSION)
        object.__setattr__(obj, "occurrence_ref", stable_ref("r3_claim_occurrence", material))
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "occurrence_ref": self.occurrence_ref,
                "expression_ref": self.expression_ref, "root_ref": self.root_ref,
                "source_ref": self.source_ref, "evidence_refs": list(self.evidence_refs),
                "interval_ref": self.interval_ref, "confidence_q": self.confidence_q,
                "modality_ref": self.modality_ref, "scope_ref": self.scope_ref,
                "placement": self.placement.value, "situation_ref": self.situation_ref,
                "supersedes_ref": self.supersedes_ref, "revision_pin": self.revision_pin.as_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ClaimOccurrence":
        row = _exact(data, cls._FIELDS, "ClaimOccurrence")
        rebuilt = cls.create(expression_ref=row["expression_ref"], root_ref=row["root_ref"], source_ref=row["source_ref"],
            evidence_refs=_wire_refs(row["evidence_refs"], "evidence_refs"), interval_ref=row["interval_ref"],
            confidence_q=row["confidence_q"], modality_ref=row["modality_ref"], scope_ref=row["scope_ref"],
            placement=PlacementMode(row["placement"]), situation_ref=row["situation_ref"],
            supersedes_ref=row["supersedes_ref"], revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["occurrence_ref"] != rebuilt.occurrence_ref or rebuilt.as_dict() != row: raise ValueError("non-canonical ClaimOccurrence")
        return rebuilt


class AdmissionStatus(Enum):
    ADMITTED = "admitted"
    ATTRIBUTED = "attributed"
    CONTESTED = "contested"
    CORRECTED = "corrected"
    REJECTED = "rejected"


@dataclass(frozen=True, init=False)
class AdmissionDecision:
    abi_version: int
    admission_ref: str
    occurrence_ref: str
    status: AdmissionStatus
    policy_ref: str
    proof_refs: tuple[str, ...]
    proposed_fact_refs: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({"abi_version", "admission_ref", "occurrence_ref", "status", "policy_ref", "proof_refs", "proposed_fact_refs", "revision_pin"})

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: raise TypeError("use AdmissionDecision.create")

    @classmethod
    def create(cls, *, occurrence_ref: str, status: AdmissionStatus, policy_ref: str,
               proof_refs: tuple[str, ...], proposed_fact_refs: tuple[str, ...], revision_pin: RevisionPin) -> "AdmissionDecision":
        if type(status) is not AdmissionStatus: raise TypeError("status must be AdmissionStatus")
        values = {"occurrence_ref": _text(occurrence_ref, "occurrence_ref"), "status": status,
                  "policy_ref": _text(policy_ref, "policy_ref"), "proof_refs": _refs(proof_refs, "proof_refs"),
                  "proposed_fact_refs": _refs(proposed_fact_refs, "proposed_fact_refs"), "revision_pin": _pin(revision_pin)}
        if status is AdmissionStatus.ADMITTED and not proposed_fact_refs:
            raise ValueError("admitted occurrence requires proposed facts")
        if status is not AdmissionStatus.ADMITTED and proposed_fact_refs:
            raise ValueError("only admitted occurrences may propose world facts")
        if status is AdmissionStatus.ADMITTED and not proof_refs:
            raise ValueError("admitted occurrence requires proof")
        material = {"abi_version": R3_ARTIFACT_ABI_VERSION, "occurrence_ref": values["occurrence_ref"], "status": status.value,
                    "policy_ref": values["policy_ref"], "proof_refs": list(values["proof_refs"]),
                    "proposed_fact_refs": list(values["proposed_fact_refs"]), "revision_pin": revision_pin.as_dict()}
        obj = object.__new__(cls); object.__setattr__(obj, "abi_version", R3_ARTIFACT_ABI_VERSION)
        object.__setattr__(obj, "admission_ref", stable_ref("r3_admission", material))
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "admission_ref": self.admission_ref,
                "occurrence_ref": self.occurrence_ref, "status": self.status.value,
                "policy_ref": self.policy_ref, "proof_refs": list(self.proof_refs),
                "proposed_fact_refs": list(self.proposed_fact_refs), "revision_pin": self.revision_pin.as_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdmissionDecision":
        row = _exact(data, cls._FIELDS, "AdmissionDecision")
        rebuilt = cls.create(occurrence_ref=row["occurrence_ref"], status=AdmissionStatus(row["status"]), policy_ref=row["policy_ref"],
                             proof_refs=_wire_refs(row["proof_refs"], "proof_refs"), proposed_fact_refs=_wire_refs(row["proposed_fact_refs"], "proposed_fact_refs"),
                             revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["admission_ref"] != rebuilt.admission_ref or rebuilt.as_dict() != row: raise ValueError("non-canonical AdmissionDecision")
        return rebuilt


@dataclass(frozen=True, init=False)
class StateDelta:
    abi_version: int
    state_delta_ref: str
    fact_ref: str
    operator_ref: str
    predicate_ref: str
    role_values: tuple[tuple[str, str], ...]
    stance: str
    occurrence_ref: str
    proof_refs: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({"abi_version", "state_delta_ref", "fact_ref", "operator_ref", "predicate_ref", "role_values", "stance", "occurrence_ref", "proof_refs", "revision_pin"})

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: raise TypeError("use StateDelta.create")

    @classmethod
    def create(cls, *, operator_ref: str, predicate_ref: str, role_values: tuple[tuple[str, str], ...],
               stance: str, occurrence_ref: str, proof_refs: tuple[str, ...], revision_pin: RevisionPin) -> "StateDelta":
        roles = _pairs(role_values, "role_values")
        if operator_ref != "op:state":
            raise ValueError("StateDelta requires op:state")
        required_roles = {"role:subject", "role:value"}
        if not required_roles <= {role for role, _ in roles}:
            raise ValueError("StateDelta requires subject and value roles")
        if not proof_refs:
            raise ValueError("StateDelta requires proof refs")
        material_core = {"operator_ref": _text(operator_ref, "operator_ref"), "predicate_ref": _text(predicate_ref, "predicate_ref"),
                         "role_values": [list(row) for row in roles], "stance": _text(stance, "stance"),
                         "occurrence_ref": _text(occurrence_ref, "occurrence_ref"), "proof_refs": list(_refs(proof_refs, "proof_refs")),
                         "revision_pin": _pin(revision_pin).as_dict()}
        fact_ref = stable_ref("r3_fact", material_core)
        material = {"abi_version": R3_ARTIFACT_ABI_VERSION, "fact_ref": fact_ref, **material_core}
        obj = object.__new__(cls); object.__setattr__(obj, "abi_version", R3_ARTIFACT_ABI_VERSION)
        object.__setattr__(obj, "state_delta_ref", stable_ref("r3_state_delta", material)); object.__setattr__(obj, "fact_ref", fact_ref)
        object.__setattr__(obj, "operator_ref", material_core["operator_ref"]); object.__setattr__(obj, "predicate_ref", material_core["predicate_ref"])
        object.__setattr__(obj, "role_values", roles); object.__setattr__(obj, "stance", material_core["stance"])
        object.__setattr__(obj, "occurrence_ref", material_core["occurrence_ref"]); object.__setattr__(obj, "proof_refs", tuple(material_core["proof_refs"]))
        object.__setattr__(obj, "revision_pin", revision_pin)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "state_delta_ref": self.state_delta_ref, "fact_ref": self.fact_ref,
                "operator_ref": self.operator_ref, "predicate_ref": self.predicate_ref,
                "role_values": [list(row) for row in self.role_values], "stance": self.stance,
                "occurrence_ref": self.occurrence_ref, "proof_refs": list(self.proof_refs), "revision_pin": self.revision_pin.as_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StateDelta":
        row = _exact(data, cls._FIELDS, "StateDelta")
        rebuilt = cls.create(operator_ref=row["operator_ref"], predicate_ref=row["predicate_ref"], role_values=_wire_pairs(row["role_values"], "role_values"),
                             stance=row["stance"], occurrence_ref=row["occurrence_ref"], proof_refs=_wire_refs(row["proof_refs"], "proof_refs"),
                             revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["state_delta_ref"] != rebuilt.state_delta_ref or row["fact_ref"] != rebuilt.fact_ref or rebuilt.as_dict() != row: raise ValueError("non-canonical StateDelta")
        return rebuilt


@dataclass(frozen=True, init=False)
class StateQueryResult:
    abi_version: int
    state_query_ref: str
    status: QueryStatus
    entity_ref: str
    dimension_ref: str
    value_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({"abi_version", "state_query_ref", "status", "entity_ref", "dimension_ref", "value_refs", "source_refs", "proof_refs", "revision_pin"})

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: raise TypeError("use StateQueryResult.create")

    @classmethod
    def create(cls, *, status: QueryStatus, entity_ref: str, dimension_ref: str, value_refs: tuple[str, ...], source_refs: tuple[str, ...], proof_refs: tuple[str, ...], revision_pin: RevisionPin) -> "StateQueryResult":
        if type(status) is not QueryStatus: raise TypeError("status must be QueryStatus")
        values = {"status": status, "entity_ref": _text(entity_ref, "entity_ref"), "dimension_ref": _text(dimension_ref, "dimension_ref"),
                  "value_refs": _refs(value_refs, "value_refs"), "source_refs": _refs(source_refs, "source_refs"),
                  "proof_refs": _refs(proof_refs, "proof_refs"), "revision_pin": _pin(revision_pin)}
        if status is QueryStatus.SUPPORTED and len(value_refs) != 1:
            raise ValueError("supported state query requires one value")
        if status is QueryStatus.CONFLICT and len(value_refs) < 2:
            raise ValueError("conflict requires multiple values")
        if status in {QueryStatus.UNKNOWN, QueryStatus.BUDGET_EXHAUSTED} and value_refs:
            raise ValueError("unknown state query cannot carry values")
        if status in {QueryStatus.SUPPORTED, QueryStatus.CONFLICT, QueryStatus.CONTRADICTED} and not proof_refs:
            raise ValueError("decisive state query requires proof refs")
        material = {"abi_version": R3_ARTIFACT_ABI_VERSION, "status": status.value, "entity_ref": values["entity_ref"], "dimension_ref": values["dimension_ref"],
                    "value_refs": list(values["value_refs"]), "source_refs": list(values["source_refs"]), "proof_refs": list(values["proof_refs"]), "revision_pin": revision_pin.as_dict()}
        obj=object.__new__(cls); object.__setattr__(obj,"abi_version",R3_ARTIFACT_ABI_VERSION); object.__setattr__(obj,"state_query_ref",stable_ref("r3_state_query",material))
        for name,item in values.items(): object.__setattr__(obj,name,item)
        return obj

    def as_dict(self)->dict[str,Any]:
        return {"abi_version":self.abi_version,"state_query_ref":self.state_query_ref,"status":self.status.value,"entity_ref":self.entity_ref,"dimension_ref":self.dimension_ref,"value_refs":list(self.value_refs),"source_refs":list(self.source_refs),"proof_refs":list(self.proof_refs),"revision_pin":self.revision_pin.as_dict()}

    @classmethod
    def from_dict(cls,data:Mapping[str,Any])->"StateQueryResult":
        row=_exact(data,cls._FIELDS,"StateQueryResult"); rebuilt=cls.create(status=QueryStatus(row["status"]),entity_ref=row["entity_ref"],dimension_ref=row["dimension_ref"],value_refs=_wire_refs(row["value_refs"],"value_refs"),source_refs=_wire_refs(row["source_refs"],"source_refs"),proof_refs=_wire_refs(row["proof_refs"],"proof_refs"),revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["state_query_ref"]!=rebuilt.state_query_ref or rebuilt.as_dict()!=row: raise ValueError("non-canonical StateQueryResult")
        return rebuilt


class TransitionStatus(Enum):
    READY = "ready"
    SIMULATED = "simulated"
    PRECONDITION_FAILED = "precondition_failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, init=False)
class TransitionEvaluation:
    abi_version:int; transition_evaluation_ref:str; expression_ref:str; event_type_ref:str; transition_ref:str|None; status:TransitionStatus; source_application_ref:str; actor_ref:str|None; target_ref:str|None; predicted_deltas:tuple[StateDelta,...]; proof_refs:tuple[str,...]; blocker_refs:tuple[str,...]; revision_pin:RevisionPin
    _FIELDS=frozenset({"abi_version","transition_evaluation_ref","expression_ref","event_type_ref","transition_ref","status","source_application_ref","actor_ref","target_ref","predicted_deltas","proof_refs","blocker_refs","revision_pin"})
    def __init__(self,*_args:Any,**_kwargs:Any)->None: raise TypeError("use TransitionEvaluation.create")
    @classmethod
    def create(cls,*,expression_ref:str,event_type_ref:str,transition_ref:str|None,status:TransitionStatus,source_application_ref:str,actor_ref:str|None,target_ref:str|None,predicted_deltas:tuple[StateDelta,...],proof_refs:tuple[str,...],blocker_refs:tuple[str,...],revision_pin:RevisionPin)->"TransitionEvaluation":
        if type(status) is not TransitionStatus: raise TypeError("status must be TransitionStatus")
        if type(predicted_deltas) is not tuple or len(predicted_deltas)>_MAX_ROWS or any(type(row) is not StateDelta for row in predicted_deltas): raise TypeError("predicted_deltas must be bounded StateDelta tuple")
        if any(row.revision_pin != revision_pin for row in predicted_deltas):
            raise ValueError("predicted delta pin mismatch")
        if status in {TransitionStatus.READY, TransitionStatus.SIMULATED} and not predicted_deltas:
            raise ValueError("ready/simulated transition requires predicted deltas")
        if status in {TransitionStatus.PRECONDITION_FAILED, TransitionStatus.UNKNOWN} and not blocker_refs:
            raise ValueError("failed/unknown transition requires blockers")
        if status in {TransitionStatus.READY, TransitionStatus.SIMULATED} and not proof_refs:
            raise ValueError("ready/simulated transition requires proof refs")
        values={"expression_ref":_text(expression_ref,"expression_ref"),"event_type_ref":_text(event_type_ref,"event_type_ref"),"transition_ref":_optional_text(transition_ref,"transition_ref"),"status":status,"source_application_ref":_text(source_application_ref,"source_application_ref"),"actor_ref":_optional_text(actor_ref,"actor_ref"),"target_ref":_optional_text(target_ref,"target_ref"),"predicted_deltas":predicted_deltas,"proof_refs":_refs(proof_refs,"proof_refs"),"blocker_refs":_refs(blocker_refs,"blocker_refs"),"revision_pin":_pin(revision_pin)}
        material={"abi_version":R3_ARTIFACT_ABI_VERSION,"expression_ref":values["expression_ref"],"event_type_ref":values["event_type_ref"],"transition_ref":values["transition_ref"],"status":status.value,"source_application_ref":values["source_application_ref"],"actor_ref":values["actor_ref"],"target_ref":values["target_ref"],"predicted_deltas":[row.as_dict() for row in predicted_deltas],"proof_refs":list(values["proof_refs"]),"blocker_refs":list(values["blocker_refs"]),"revision_pin":revision_pin.as_dict()}
        obj=object.__new__(cls); object.__setattr__(obj,"abi_version",R3_ARTIFACT_ABI_VERSION); object.__setattr__(obj,"transition_evaluation_ref",stable_ref("r3_transition_evaluation",material)); [object.__setattr__(obj,k,v) for k,v in values.items()]; return obj
    def as_dict(self)->dict[str,Any]: return {"abi_version":self.abi_version,"transition_evaluation_ref":self.transition_evaluation_ref,"expression_ref":self.expression_ref,"event_type_ref":self.event_type_ref,"transition_ref":self.transition_ref,"status":self.status.value,"source_application_ref":self.source_application_ref,"actor_ref":self.actor_ref,"target_ref":self.target_ref,"predicted_deltas":[row.as_dict() for row in self.predicted_deltas],"proof_refs":list(self.proof_refs),"blocker_refs":list(self.blocker_refs),"revision_pin":self.revision_pin.as_dict()}
    @classmethod
    def from_dict(cls,data:Mapping[str,Any])->"TransitionEvaluation":
        row=_exact(data,cls._FIELDS,"TransitionEvaluation"); rebuilt=cls.create(expression_ref=row["expression_ref"],event_type_ref=row["event_type_ref"],transition_ref=row["transition_ref"],status=TransitionStatus(row["status"]),source_application_ref=row["source_application_ref"],actor_ref=row["actor_ref"],target_ref=row["target_ref"],predicted_deltas=tuple(StateDelta.from_dict(x) for x in row["predicted_deltas"]),proof_refs=_wire_refs(row["proof_refs"],"proof_refs"),blocker_refs=_wire_refs(row["blocker_refs"],"blocker_refs"),revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["transition_evaluation_ref"]!=rebuilt.transition_evaluation_ref or rebuilt.as_dict()!=row: raise ValueError("non-canonical TransitionEvaluation")
        return rebuilt


class CapabilityStatus(Enum):
    AVAILABLE="available"; UNKNOWN="unknown"; RESOURCE_UNAVAILABLE="resource_unavailable"; DENIED="denied"; ADAPTER_MISSING="adapter_missing"


@dataclass(frozen=True,init=False)
class CapabilityEvaluation:
    abi_version:int; capability_evaluation_ref:str; actor_ref:str; event_type_ref:str; status:CapabilityStatus; capability_refs:tuple[str,...]; permission_refs:tuple[str,...]; resource_refs:tuple[str,...]; adapter_ref:str|None; proof_refs:tuple[str,...]; blocker_refs:tuple[str,...]; revision_pin:RevisionPin
    _FIELDS=frozenset({"abi_version","capability_evaluation_ref","actor_ref","event_type_ref","status","capability_refs","permission_refs","resource_refs","adapter_ref","proof_refs","blocker_refs","revision_pin"})
    def __init__(self,*_args:Any,**_kwargs:Any)->None: raise TypeError("use CapabilityEvaluation.create")
    @classmethod
    def create(cls,*,actor_ref:str,event_type_ref:str,status:CapabilityStatus,capability_refs:tuple[str,...],permission_refs:tuple[str,...],resource_refs:tuple[str,...],adapter_ref:str|None,proof_refs:tuple[str,...],blocker_refs:tuple[str,...],revision_pin:RevisionPin)->"CapabilityEvaluation":
        if type(status) is not CapabilityStatus: raise TypeError("status must be CapabilityStatus")
        if status is CapabilityStatus.AVAILABLE and blocker_refs:
            raise ValueError("available capability cannot carry blockers")
        if status is not CapabilityStatus.AVAILABLE and not blocker_refs:
            raise ValueError("unavailable capability requires blockers")
        if status is CapabilityStatus.AVAILABLE and not proof_refs:
            raise ValueError("available capability requires proof refs")
        values={"actor_ref":_text(actor_ref,"actor_ref"),"event_type_ref":_text(event_type_ref,"event_type_ref"),"status":status,"capability_refs":_refs(capability_refs,"capability_refs"),"permission_refs":_refs(permission_refs,"permission_refs"),"resource_refs":_refs(resource_refs,"resource_refs"),"adapter_ref":_optional_text(adapter_ref,"adapter_ref"),"proof_refs":_refs(proof_refs,"proof_refs"),"blocker_refs":_refs(blocker_refs,"blocker_refs"),"revision_pin":_pin(revision_pin)}
        material={"abi_version":R3_ARTIFACT_ABI_VERSION,"actor_ref":values["actor_ref"],"event_type_ref":values["event_type_ref"],"status":status.value,"capability_refs":list(values["capability_refs"]),"permission_refs":list(values["permission_refs"]),"resource_refs":list(values["resource_refs"]),"adapter_ref":values["adapter_ref"],"proof_refs":list(values["proof_refs"]),"blocker_refs":list(values["blocker_refs"]),"revision_pin":revision_pin.as_dict()}
        obj=object.__new__(cls); object.__setattr__(obj,"abi_version",R3_ARTIFACT_ABI_VERSION); object.__setattr__(obj,"capability_evaluation_ref",stable_ref("r3_capability_evaluation",material)); [object.__setattr__(obj,k,v) for k,v in values.items()]; return obj
    def as_dict(self)->dict[str,Any]: return {"abi_version":self.abi_version,"capability_evaluation_ref":self.capability_evaluation_ref,"actor_ref":self.actor_ref,"event_type_ref":self.event_type_ref,"status":self.status.value,"capability_refs":list(self.capability_refs),"permission_refs":list(self.permission_refs),"resource_refs":list(self.resource_refs),"adapter_ref":self.adapter_ref,"proof_refs":list(self.proof_refs),"blocker_refs":list(self.blocker_refs),"revision_pin":self.revision_pin.as_dict()}
    @classmethod
    def from_dict(cls,data:Mapping[str,Any])->"CapabilityEvaluation":
        row=_exact(data,cls._FIELDS,"CapabilityEvaluation"); rebuilt=cls.create(actor_ref=row["actor_ref"],event_type_ref=row["event_type_ref"],status=CapabilityStatus(row["status"]),capability_refs=_wire_refs(row["capability_refs"],"capability_refs"),permission_refs=_wire_refs(row["permission_refs"],"permission_refs"),resource_refs=_wire_refs(row["resource_refs"],"resource_refs"),adapter_ref=row["adapter_ref"],proof_refs=_wire_refs(row["proof_refs"],"proof_refs"),blocker_refs=_wire_refs(row["blocker_refs"],"blocker_refs"),revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["capability_evaluation_ref"]!=rebuilt.capability_evaluation_ref or rebuilt.as_dict()!=row: raise ValueError("non-canonical CapabilityEvaluation")
        return rebuilt


@dataclass(frozen=True,init=False)
class EffectIntent:
    abi_version:int; effect_intent_ref:str; event_type_ref:str; transition_ref:str|None; actor_ref:str; target_ref:str|None; adapter_ref:str|None; capability_evaluation_ref:str; proposed_deltas:tuple[StateDelta,...]; requirement_proof_refs:tuple[str,...]; revision_pin:RevisionPin
    _FIELDS=frozenset({"abi_version","effect_intent_ref","event_type_ref","transition_ref","actor_ref","target_ref","adapter_ref","capability_evaluation_ref","proposed_deltas","requirement_proof_refs","revision_pin"})
    def __init__(self,*_args:Any,**_kwargs:Any)->None: raise TypeError("use EffectIntent.create")
    @classmethod
    def create(cls,*,event_type_ref:str,transition_ref:str|None,actor_ref:str,target_ref:str|None,adapter_ref:str|None,capability_evaluation_ref:str,proposed_deltas:tuple[StateDelta,...],requirement_proof_refs:tuple[str,...],revision_pin:RevisionPin)->"EffectIntent":
        if type(proposed_deltas) is not tuple or len(proposed_deltas) > _MAX_ROWS or any(type(x) is not StateDelta for x in proposed_deltas):
            raise TypeError("proposed_deltas must be StateDelta tuple")
        if not proposed_deltas:
            raise ValueError("EffectIntent requires proposed deltas")
        if any(row.revision_pin != revision_pin for row in proposed_deltas):
            raise ValueError("EffectIntent delta pin mismatch")
        if not requirement_proof_refs:
            raise ValueError("EffectIntent requires requirement proof refs")
        values={"event_type_ref":_text(event_type_ref,"event_type_ref"),"transition_ref":_optional_text(transition_ref,"transition_ref"),"actor_ref":_text(actor_ref,"actor_ref"),"target_ref":_optional_text(target_ref,"target_ref"),"adapter_ref":_optional_text(adapter_ref,"adapter_ref"),"capability_evaluation_ref":_text(capability_evaluation_ref,"capability_evaluation_ref"),"proposed_deltas":proposed_deltas,"requirement_proof_refs":_refs(requirement_proof_refs,"requirement_proof_refs"),"revision_pin":_pin(revision_pin)}
        material={"abi_version":R3_ARTIFACT_ABI_VERSION,"event_type_ref":values["event_type_ref"],"transition_ref":values["transition_ref"],"actor_ref":values["actor_ref"],"target_ref":values["target_ref"],"adapter_ref":values["adapter_ref"],"capability_evaluation_ref":values["capability_evaluation_ref"],"proposed_deltas":[x.as_dict() for x in proposed_deltas],"requirement_proof_refs":list(values["requirement_proof_refs"]),"revision_pin":revision_pin.as_dict()}
        obj=object.__new__(cls); object.__setattr__(obj,"abi_version",R3_ARTIFACT_ABI_VERSION); object.__setattr__(obj,"effect_intent_ref",stable_ref("r3_effect_intent",material)); [object.__setattr__(obj,k,v) for k,v in values.items()]; return obj
    def as_dict(self)->dict[str,Any]: return {"abi_version":self.abi_version,"effect_intent_ref":self.effect_intent_ref,"event_type_ref":self.event_type_ref,"transition_ref":self.transition_ref,"actor_ref":self.actor_ref,"target_ref":self.target_ref,"adapter_ref":self.adapter_ref,"capability_evaluation_ref":self.capability_evaluation_ref,"proposed_deltas":[x.as_dict() for x in self.proposed_deltas],"requirement_proof_refs":list(self.requirement_proof_refs),"revision_pin":self.revision_pin.as_dict()}
    @classmethod
    def from_dict(cls,data:Mapping[str,Any])->"EffectIntent":
        row=_exact(data,cls._FIELDS,"EffectIntent"); rebuilt=cls.create(event_type_ref=row["event_type_ref"],transition_ref=row["transition_ref"],actor_ref=row["actor_ref"],target_ref=row["target_ref"],adapter_ref=row["adapter_ref"],capability_evaluation_ref=row["capability_evaluation_ref"],proposed_deltas=tuple(StateDelta.from_dict(x) for x in row["proposed_deltas"]),requirement_proof_refs=_wire_refs(row["requirement_proof_refs"],"requirement_proof_refs"),revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["effect_intent_ref"]!=rebuilt.effect_intent_ref or rebuilt.as_dict()!=row: raise ValueError("non-canonical EffectIntent")
        return rebuilt


@dataclass(frozen=True,init=False)
class LearningDraft:
    abi_version:int; learning_draft_ref:str; kind:str; surface_literal:str; target_ref:str|None; expected_target_kinds:tuple[str,...]; source_query_ref:str|None; answer_contract_ref:str; proof_refs:tuple[str,...]; revision_pin:RevisionPin
    _FIELDS=frozenset({"abi_version","learning_draft_ref","kind","surface_literal","target_ref","expected_target_kinds","source_query_ref","answer_contract_ref","proof_refs","revision_pin"})
    def __init__(self,*_args:Any,**_kwargs:Any)->None: raise TypeError("use LearningDraft.create")
    @classmethod
    def create(cls,*,kind:str,surface_literal:str,target_ref:str|None,expected_target_kinds:tuple[str,...],source_query_ref:str|None,answer_contract_ref:str,proof_refs:tuple[str,...],revision_pin:RevisionPin)->"LearningDraft":
        if kind not in {"lookup","teaching","directive","learning_event"}: raise ValueError("unknown learning distinction")
        values={"kind":kind,"surface_literal":_text(surface_literal,"surface_literal"),"target_ref":_optional_text(target_ref,"target_ref"),"expected_target_kinds":_refs(expected_target_kinds,"expected_target_kinds"),"source_query_ref":_optional_text(source_query_ref,"source_query_ref"),"answer_contract_ref":_text(answer_contract_ref,"answer_contract_ref"),"proof_refs":_refs(proof_refs,"proof_refs"),"revision_pin":_pin(revision_pin)}
        material={"abi_version":R3_ARTIFACT_ABI_VERSION,**{k:(list(v) if type(v) is tuple else v.as_dict() if type(v) is RevisionPin else v) for k,v in values.items()}}
        obj=object.__new__(cls); object.__setattr__(obj,"abi_version",R3_ARTIFACT_ABI_VERSION); object.__setattr__(obj,"learning_draft_ref",stable_ref("r3_learning_draft",material)); [object.__setattr__(obj,k,v) for k,v in values.items()]; return obj
    def as_dict(self)->dict[str,Any]: return {"abi_version":self.abi_version,"learning_draft_ref":self.learning_draft_ref,"kind":self.kind,"surface_literal":self.surface_literal,"target_ref":self.target_ref,"expected_target_kinds":list(self.expected_target_kinds),"source_query_ref":self.source_query_ref,"answer_contract_ref":self.answer_contract_ref,"proof_refs":list(self.proof_refs),"revision_pin":self.revision_pin.as_dict()}
    @classmethod
    def from_dict(cls,data:Mapping[str,Any])->"LearningDraft":
        row=_exact(data,cls._FIELDS,"LearningDraft"); rebuilt=cls.create(kind=row["kind"],surface_literal=row["surface_literal"],target_ref=row["target_ref"],expected_target_kinds=_wire_refs(row["expected_target_kinds"],"expected_target_kinds"),source_query_ref=row["source_query_ref"],answer_contract_ref=row["answer_contract_ref"],proof_refs=_wire_refs(row["proof_refs"],"proof_refs"),revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["learning_draft_ref"]!=rebuilt.learning_draft_ref or rebuilt.as_dict()!=row: raise ValueError("non-canonical LearningDraft")
        return rebuilt


@dataclass(frozen=True)
class ModeEvaluation:
    contribution: DecisionContribution
    query_results: tuple[QueryResult,...]=()
    claim_occurrences: tuple[ClaimOccurrence,...]=()
    admission_decisions: tuple[AdmissionDecision,...]=()
    state_deltas: tuple[StateDelta,...]=()
    state_query_results: tuple[StateQueryResult,...]=()
    transition_evaluations: tuple[TransitionEvaluation,...]=()
    capability_evaluations: tuple[CapabilityEvaluation,...]=()
    effect_intents: tuple[EffectIntent,...]=()
    learning_drafts: tuple[LearningDraft,...]=()

    def __post_init__(self)->None:
        if type(self.contribution) is not DecisionContribution: raise TypeError("contribution must be DecisionContribution")
        specs=(("query_results",QueryResult),("claim_occurrences",ClaimOccurrence),("admission_decisions",AdmissionDecision),("state_deltas",StateDelta),("state_query_results",StateQueryResult),("transition_evaluations",TransitionEvaluation),("capability_evaluations",CapabilityEvaluation),("effect_intents",EffectIntent),("learning_drafts",LearningDraft))
        for name,owner in specs:
            value=getattr(self,name)
            if type(value) is not tuple or len(value)>_MAX_ROWS or any(type(row) is not owner for row in value): raise TypeError(f"{name} must be a bounded exact {owner.__name__} tuple")


@dataclass(frozen=True,init=False)
class EvaluationBundle:
    abi_version:int; evaluation_ref:str; decision:Decision; expression:SemanticExpression; situation:SituationContext; query_results:tuple[QueryResult,...]; claim_occurrences:tuple[ClaimOccurrence,...]; admission_decisions:tuple[AdmissionDecision,...]; state_deltas:tuple[StateDelta,...]; state_query_results:tuple[StateQueryResult,...]; transition_evaluations:tuple[TransitionEvaluation,...]; capability_evaluations:tuple[CapabilityEvaluation,...]; effect_intents:tuple[EffectIntent,...]; learning_drafts:tuple[LearningDraft,...]; revision_pin:RevisionPin
    _FIELDS=frozenset({"abi_version","evaluation_ref","decision","expression","situation","query_results","claim_occurrences","admission_decisions","state_deltas","state_query_results","transition_evaluations","capability_evaluations","effect_intents","learning_drafts","revision_pin"})
    def __init__(self,*_args:Any,**_kwargs:Any)->None: raise TypeError("use EvaluationBundle.create")
    @classmethod
    def create(cls,*,decision:Decision,expression:SemanticExpression,situation:SituationContext,mode_evaluation:ModeEvaluation,revision_pin:RevisionPin)->"EvaluationBundle":
        if type(decision) is not Decision or type(expression) is not SemanticExpression or type(situation) is not SituationContext or type(mode_evaluation) is not ModeEvaluation: raise TypeError("invalid EvaluationBundle input")
        if decision.expression_ref!=expression.expression_ref or decision.situation.situation_ref!=situation.situation_ref: raise ValueError("EvaluationBundle lineage mismatch")
        if decision.revision_pin!=revision_pin or situation.revision_pin!=revision_pin: raise ValueError("EvaluationBundle revision mismatch")
        values={"decision":decision,"expression":expression,"situation":situation,"query_results":mode_evaluation.query_results,"claim_occurrences":mode_evaluation.claim_occurrences,"admission_decisions":mode_evaluation.admission_decisions,"state_deltas":mode_evaluation.state_deltas,"state_query_results":mode_evaluation.state_query_results,"transition_evaluations":mode_evaluation.transition_evaluations,"capability_evaluations":mode_evaluation.capability_evaluations,"effect_intents":mode_evaluation.effect_intents,"learning_drafts":mode_evaluation.learning_drafts,"revision_pin":_pin(revision_pin)}
        material={"abi_version":R3_ARTIFACT_ABI_VERSION,"decision":decision.as_dict(),"expression":expression.as_dict(),"situation":situation.as_dict(),"query_results":[x.as_dict() for x in values["query_results"]],"claim_occurrences":[x.as_dict() for x in values["claim_occurrences"]],"admission_decisions":[x.as_dict() for x in values["admission_decisions"]],"state_deltas":[x.as_dict() for x in values["state_deltas"]],"state_query_results":[x.as_dict() for x in values["state_query_results"]],"transition_evaluations":[x.as_dict() for x in values["transition_evaluations"]],"capability_evaluations":[x.as_dict() for x in values["capability_evaluations"]],"effect_intents":[x.as_dict() for x in values["effect_intents"]],"learning_drafts":[x.as_dict() for x in values["learning_drafts"]],"revision_pin":revision_pin.as_dict()}
        obj=object.__new__(cls); object.__setattr__(obj,"abi_version",R3_ARTIFACT_ABI_VERSION); object.__setattr__(obj,"evaluation_ref",stable_ref("r3_evaluation",material)); [object.__setattr__(obj,k,v) for k,v in values.items()]; return obj
    def as_dict(self)->dict[str,Any]: return {"abi_version":self.abi_version,"evaluation_ref":self.evaluation_ref,"decision":self.decision.as_dict(),"expression":self.expression.as_dict(),"situation":self.situation.as_dict(),"query_results":[x.as_dict() for x in self.query_results],"claim_occurrences":[x.as_dict() for x in self.claim_occurrences],"admission_decisions":[x.as_dict() for x in self.admission_decisions],"state_deltas":[x.as_dict() for x in self.state_deltas],"state_query_results":[x.as_dict() for x in self.state_query_results],"transition_evaluations":[x.as_dict() for x in self.transition_evaluations],"capability_evaluations":[x.as_dict() for x in self.capability_evaluations],"effect_intents":[x.as_dict() for x in self.effect_intents],"learning_drafts":[x.as_dict() for x in self.learning_drafts],"revision_pin":self.revision_pin.as_dict()}
    @classmethod
    def from_dict(cls,data:Mapping[str,Any])->"EvaluationBundle":
        row=_exact(data,cls._FIELDS,"EvaluationBundle")
        mode=ModeEvaluation(contribution=DecisionContribution(status=__import__("cemm_authoritative_hybrid.decision",fromlist=["DecisionStatus"]).DecisionStatus(row["decision"]["status"]),action=__import__("cemm_authoritative_hybrid.decision",fromlist=["DecisionAction"]).DecisionAction(row["decision"]["action"]),answer_expression_ref=row["decision"]["answer_expression_ref"],bindings=_wire_pairs(row["decision"]["bindings"],"bindings"),claim_occurrence_refs=_wire_refs(row["decision"]["claim_occurrence_refs"],"claim_occurrence_refs"),admission_decision_refs=_wire_refs(row["decision"]["admission_decision_refs"],"admission_decision_refs"),query_result_refs=_wire_refs(row["decision"]["query_result_refs"],"query_result_refs"),transition_preview_refs=_wire_refs(row["decision"]["transition_preview_refs"],"transition_preview_refs"),effect_intent_ref=row["decision"]["effect_intent_ref"],learning_draft_refs=_wire_refs(row["decision"]["learning_draft_refs"],"learning_draft_refs"),proof_refs=_wire_refs(row["decision"]["proof_refs"],"proof_refs"),source_refs=_wire_refs(row["decision"]["source_refs"],"source_refs"),blocker_refs=_wire_refs(row["decision"]["blocker_refs"],"blocker_refs"),policy_refs=_wire_refs(row["decision"]["policy_refs"],"policy_refs")),query_results=tuple(QueryResult.from_dict(x) for x in row["query_results"]),claim_occurrences=tuple(ClaimOccurrence.from_dict(x) for x in row["claim_occurrences"]),admission_decisions=tuple(AdmissionDecision.from_dict(x) for x in row["admission_decisions"]),state_deltas=tuple(StateDelta.from_dict(x) for x in row["state_deltas"]),state_query_results=tuple(StateQueryResult.from_dict(x) for x in row["state_query_results"]),transition_evaluations=tuple(TransitionEvaluation.from_dict(x) for x in row["transition_evaluations"]),capability_evaluations=tuple(CapabilityEvaluation.from_dict(x) for x in row["capability_evaluations"]),effect_intents=tuple(EffectIntent.from_dict(x) for x in row["effect_intents"]),learning_drafts=tuple(LearningDraft.from_dict(x) for x in row["learning_drafts"]))
        rebuilt=cls.create(decision=Decision.from_dict(row["decision"]),expression=SemanticExpression.from_dict(row["expression"]),situation=SituationContext.from_dict(row["situation"]),mode_evaluation=mode,revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if row["evaluation_ref"]!=rebuilt.evaluation_ref or rebuilt.as_dict()!=row: raise ValueError("non-canonical EvaluationBundle")
        return rebuilt
