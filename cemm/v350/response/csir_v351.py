"""Canonical Phase-12 Response CSIR contracts.

Response meaning is exact CSIR.  These records are cycle-local decision artifacts; they
contain no surface strings and never import the legacy UOL response model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Iterable, Mapping

from ..csir.authority import CURRENT_KERNEL_ABI
from ..csir.authority_v351 import AuthoritySnapshotV351, ClosureProof
from ..csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
from ..csir.model import CSIRGraph, ExactAuthorityPin


class ResponseError(ValueError):
    pass


class ResponseFamily(str, Enum):
    ANSWER_QUERY = "answer_query"
    REPORT_STATE = "report_state"
    REPORT_RELATION = "report_relation"
    REPORT_EVENT = "report_event"
    ACKNOWLEDGE_TARGETED_CLAIM = "acknowledge_targeted_claim"
    REQUEST_CLARIFICATION = "request_clarification"
    CORRECT_PRIOR_OUTPUT = "correct_prior_output"
    QUALIFY_UNCERTAINTY = "qualify_uncertainty"
    REPORT_CAPABILITY = "report_capability"
    ASK_LEARNING_QUESTION = "ask_learning_question"
    NO_RESPONSE_REQUIRED = "no_response_required"


@dataclass(frozen=True, slots=True)
class ResponseFamilyAuthority:
    """Exact semantic authority for one response-family construction.

    Port pins are semantic roles.  Their names are never surfaced to the user and no
    universal grammatical meaning is inferred from them.
    """

    family: ResponseFamily
    definition_pin: ExactAuthorityPin
    content_port_pin: ExactAuthorityPin | None = None
    target_port_pin: ExactAuthorityPin | None = None
    source_port_pin: ExactAuthorityPin | None = None
    uncertainty_port_pin: ExactAuthorityPin | None = None
    reason_port_pin: ExactAuthorityPin | None = None

    def exact_pins(self) -> tuple[ExactAuthorityPin, ...]:
        values = (
            self.definition_pin, self.content_port_pin, self.target_port_pin,
            self.source_port_pin, self.uncertainty_port_pin, self.reason_port_pin,
        )
        return tuple(pin for pin in values if pin is not None)


@dataclass(frozen=True, slots=True)
class ResponseAuthorityMapV351:
    authorities: tuple[ResponseFamilyAuthority, ...] = ()

    def __post_init__(self) -> None:
        families = tuple(item.family for item in self.authorities)
        if len(families) != len(set(families)):
            raise ResponseError("response-family authority must be unique")
        definitions = tuple(item.definition_pin.key for item in self.authorities)
        if len(definitions) != len(set(definitions)):
            raise ResponseError("one exact response definition cannot silently mean two families")

    @property
    def by_family(self) -> Mapping[ResponseFamily, ResponseFamilyAuthority]:
        return {item.family: item for item in self.authorities}

    def require(self, family: ResponseFamily) -> ResponseFamilyAuthority:
        try:
            return self.by_family[family]
        except KeyError as exc:
            raise ResponseError(f"missing exact response-family authority:{family.value}") from exc

    def validate_family(self, snapshot: AuthoritySnapshotV351, family: ResponseFamily) -> ResponseFamilyAuthority:
        item = self.require(family)
        definition = snapshot.require_definition(item.definition_pin)
        formal = {port.port_pin.key for port in definition.formal_ports}
        for pin in item.exact_pins()[1:]:
            snapshot.require_known_pin(pin)
            if pin.key not in formal:
                raise ResponseError(
                    f"response authority port is not a formal port of definition:{item.family.value}:{pin.key}"
                )
        return item

    def validate(self, snapshot: AuthoritySnapshotV351) -> None:
        for item in self.authorities:
            self.validate_family(snapshot, item.family)


@dataclass(frozen=True, slots=True)
class ResponseSourceBinding:
    source_ref: str
    semantic_ref: str
    proof_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    semantic_fingerprint: str = ""
    exact_fingerprint: str = ""
    confidence: float = 1.0

    def __post_init__(self) -> None:
        _ref(self.source_ref, "response source_ref")
        _ref(self.semantic_ref, "response semantic_ref")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ResponseError("response source confidence must be finite in [0,1]")
        _unique(self.proof_refs, "response source proofs")
        _unique(self.evidence_refs, "response source evidence")
        if bool(self.semantic_fingerprint) != bool(self.exact_fingerprint):
            raise ResponseError("response source semantic/exact fingerprints must be supplied together")


@dataclass(frozen=True, slots=True)
class ResponseCSIRCandidate:
    candidate_ref: str
    family: ResponseFamily
    graph: CSIRGraph
    semantic_fingerprint: str
    exact_fingerprint: str
    authority_generation: int
    authority_fingerprint: str
    semantic_authority_snapshot_fingerprint: str
    closure_proof: ClosureProof | None
    execution_authority_ref: str
    source_bindings: tuple[ResponseSourceBinding, ...]
    audience_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    obligation_refs: tuple[str, ...] = ()
    target_refs: tuple[str, ...] = ()
    qualification_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()
    score: float = 0.0
    kernel_abi_fingerprint: str = CURRENT_KERNEL_ABI.fingerprint

    def __post_init__(self) -> None:
        _ref(self.candidate_ref, "response candidate_ref")
        _ref(self.context_ref, "response context_ref")
        _ref(self.permission_ref, "response permission_ref")
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise ResponseError("response candidate requires exact AuthorityGeneration")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ResponseError("response candidate kernel ABI mismatch")
        if semantic_fingerprint(self.graph) != self.semantic_fingerprint:
            raise ResponseError("response semantic fingerprint must be kernel-derived")
        if exact_fingerprint(self.graph) != self.exact_fingerprint:
            raise ResponseError("response exact fingerprint must be kernel-derived")
        if not isfinite(self.score):
            raise ResponseError("response candidate score must be finite")
        for values, label in (
            (self.audience_refs, "audiences"), (self.obligation_refs, "obligations"),
            (self.target_refs, "targets"), (self.qualification_refs, "qualifications"),
            (self.frontier_refs, "frontiers"),
        ):
            _unique(values, f"response {label}")
        _unique(tuple(item.source_ref for item in self.source_bindings), "response source binding refs")
        if self.family is ResponseFamily.NO_RESPONSE_REQUIRED and self.graph.root_refs:
            raise ResponseError("NO_RESPONSE_REQUIRED must not smuggle surface-bearing semantic roots")
        if self.family is not ResponseFamily.NO_RESPONSE_REQUIRED and not self.graph.root_refs:
            raise ResponseError("response candidate requires semantic roots")
        if self.graph.applications and self.closure_proof is None:
            raise ResponseError("executable Response CSIR requires typed closure proof")


@dataclass(frozen=True, slots=True)
class ResponseDecision:
    decision_ref: str
    selected_candidate_ref: str
    family: ResponseFamily
    graph: CSIRGraph
    semantic_fingerprint: str
    exact_fingerprint: str
    authority_generation: int
    authority_fingerprint: str
    semantic_authority_snapshot_fingerprint: str
    source_bindings: tuple[ResponseSourceBinding, ...]
    audience_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    target_refs: tuple[str, ...] = ()
    qualification_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()
    no_response_reason_ref: str | None = None
    kernel_abi_fingerprint: str = CURRENT_KERNEL_ABI.fingerprint

    def __post_init__(self) -> None:
        _ref(self.decision_ref, "response decision_ref")
        _ref(self.selected_candidate_ref, "selected response candidate_ref")
        _ref(self.context_ref, "response decision context")
        _ref(self.permission_ref, "response decision permission")
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise ResponseError("response decision requires exact authority")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ResponseError("response decision kernel ABI mismatch")
        if semantic_fingerprint(self.graph) != self.semantic_fingerprint:
            raise ResponseError("response decision semantic fingerprint mismatch")
        if exact_fingerprint(self.graph) != self.exact_fingerprint:
            raise ResponseError("response decision exact fingerprint mismatch")
        for values, label in (
            (self.audience_refs, "audiences"), (self.target_refs, "targets"),
            (self.qualification_refs, "qualifications"), (self.proof_refs, "proofs"),
            (self.frontier_refs, "frontiers"),
        ):
            _unique(values, f"response decision {label}")
        if self.family is ResponseFamily.NO_RESPONSE_REQUIRED:
            if self.no_response_reason_ref is None:
                raise ResponseError("NO_RESPONSE_REQUIRED requires explicit semantic reason")
        elif self.no_response_reason_ref is not None:
            raise ResponseError("ordinary response decision cannot carry no-response reason")

    @property
    def response_ref(self) -> str:
        return self.decision_ref

    def semantic_coverage_refs(self) -> tuple[str, ...]:
        refs: set[str] = set()
        refs.update(item.term_ref for item in self.graph.terms)
        refs.update(item.variable_ref for item in self.graph.variables)
        refs.update(item.application_ref for item in self.graph.applications)
        refs.update(item.binding_ref for item in self.graph.bindings)
        refs.update(item.qualifier_ref for item in self.graph.qualifiers)
        refs.update(item.embedding_ref for item in self.graph.scope_embeddings)
        refs.update(item.coordination_ref for item in self.graph.coordinations)
        refs.update(f"root:{item.kind.value}:{item.ref}" for item in self.graph.root_refs)
        return tuple(sorted(refs))

    def qualification_document(self) -> Mapping[str, Any]:
        return {
            "context_ref": self.context_ref,
            "permission_ref": self.permission_ref,
            "audience_refs": tuple(sorted(self.audience_refs)),
            "qualification_refs": tuple(sorted(self.qualification_refs)),
            "target_refs": tuple(sorted(self.target_refs)),
            "qualifiers": tuple(
                (
                    item.qualifier_ref, item.target.kind.value, item.target.ref,
                    item.qualifier_kind.value,
                    None if item.value_ref is None else (item.value_ref.kind.value, item.value_ref.ref),
                    item.value_atom,
                    None if item.value_pin is None else item.value_pin.key,
                )
                for item in self.graph.qualifiers
            ),
            "scope_embeddings": tuple(
                (
                    item.embedding_ref,
                    (item.operator.kind.value, item.operator.ref),
                    (item.scoped.kind.value, item.scoped.ref),
                    item.scope_kind_pin.key,
                    item.order,
                )
                for item in self.graph.scope_embeddings
            ),
            "source_bindings": tuple(
                (
                    item.source_ref, item.semantic_ref, tuple(sorted(item.proof_refs)),
                    tuple(sorted(item.evidence_refs)), item.semantic_fingerprint,
                    item.exact_fingerprint, item.confidence,
                )
                for item in self.source_bindings
            ),
        }


@dataclass(frozen=True, slots=True)
class ConversationalGoalCandidate:
    goal_ref: str
    family: ResponseFamily
    target_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    reason_refs: tuple[str, ...]
    priority: int
    blocked_by_frontier_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationalGoalDecision:
    decision_ref: str
    candidates: tuple[ConversationalGoalCandidate, ...]
    selected_goal_refs: tuple[str, ...]
    selected_families: tuple[ResponseFamily, ...]
    context_ref: str
    permission_ref: str
    reason_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.decision_ref, "conversational goal decision_ref")
        _ref(self.context_ref, "conversational goal context")
        _ref(self.permission_ref, "conversational goal permission")
        _unique(tuple(item.goal_ref for item in self.candidates), "conversational goal refs")
        _unique(self.selected_goal_refs, "selected conversational goals")
        _unique(self.selected_families, "selected response families")
        _unique(self.reason_refs, "conversational goal reasons")
        known = {item.goal_ref for item in self.candidates}
        if not set(self.selected_goal_refs).issubset(known):
            raise ResponseError("goal decision selects unknown candidate")


@dataclass(frozen=True, slots=True)
class ResponseReportIntent:
    intent_ref: str
    family: ResponseFamily
    semantic_ref: str
    target_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    priority: int = 700

    def __post_init__(self) -> None:
        _ref(self.intent_ref, "response report intent_ref")
        _ref(self.semantic_ref, "response report semantic_ref")
        if self.family not in {
            ResponseFamily.REPORT_STATE, ResponseFamily.REPORT_RELATION,
            ResponseFamily.REPORT_EVENT, ResponseFamily.REPORT_CAPABILITY,
        }:
            raise ResponseError("ResponseReportIntent requires a REPORT_* family")
        _unique(self.target_refs, "response report targets")
        _unique(self.proof_refs, "response report proofs")
        _unique(self.evidence_refs, "response report evidence")


@dataclass(frozen=True, slots=True)
class ResponseCorrectionIntent:
    intent_ref: str
    target_output_ref: str
    replacement_semantic_ref: str
    proof_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    priority: int = 950

    def __post_init__(self) -> None:
        _ref(self.intent_ref, "response correction intent_ref")
        _ref(self.target_output_ref, "response correction target output")
        _ref(self.replacement_semantic_ref, "response correction replacement semantics")
        _unique(self.proof_refs, "response correction proofs")
        _unique(self.evidence_refs, "response correction evidence")


@dataclass(frozen=True, slots=True)
class ResponseBuildFrontier:
    frontier_ref: str
    missing_contract: str
    family: ResponseFamily | None = None
    target_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    effects: tuple[str, ...] = ("blocks_realization", "learning")


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ResponseError(f"{label} must be non-empty")


def _unique(values: Iterable[Any], label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise ResponseError(f"{label} must be unique")


__all__ = [
    "ConversationalGoalCandidate", "ConversationalGoalDecision", "ResponseAuthorityMapV351",
    "ResponseBuildFrontier", "ResponseCSIRCandidate", "ResponseCorrectionIntent",
    "ResponseDecision", "ResponseError", "ResponseFamily", "ResponseFamilyAuthority",
    "ResponseReportIntent", "ResponseSourceBinding",
]
