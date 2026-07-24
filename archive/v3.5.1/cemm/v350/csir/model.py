"""Exact CSIR v2 kernel data model.

CSIR is the sole canonical semantic substrate.  The constructors here are intentionally
small and domain-agnostic: TERM, VARIABLE, APPLICATION, BINDING, QUALIFIER,
SCOPE_EMBEDDING, COORDINATION and PROOF_LINK.

Local graph refs are occurrence labels only and never semantic identity.  Exact
semantic identity is computed by :mod:`cemm.v350.csir.canonical` after canonical
labelling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Iterable, Mapping


class CSIRValidationError(ValueError):
    pass


class CSIRNodeKind(str, Enum):
    TERM = "term"
    VARIABLE = "variable"
    APPLICATION = "application"
    BINDING = "binding"
    QUALIFIER = "qualifier"
    SCOPE_EMBEDDING = "scope_embedding"
    COORDINATION = "coordination"
    PROOF_LINK = "proof_link"


class TermKind(str, Enum):
    """Stable denotation shapes, never learned ontology classes."""

    REFERENT = "referent"
    LITERAL = "literal"
    TIME = "time"
    CONTEXT = "context"
    QUANTITY = "quantity"
    UNIT = "unit"
    OTHER = "other"


class QualifierKind(str, Enum):
    CONTEXT = "context"
    TIME = "time"
    POLARITY = "polarity"
    MODALITY = "modality"
    SOURCE = "source"
    PERMISSION = "permission"
    EVIDENCE = "evidence"


class KernelOperation(str, Enum):
    INSTANTIATE = "instantiate"
    BIND = "bind"
    UNIFY = "unify"
    COMPOSE = "compose"
    QUALIFY = "qualify"
    EMBED = "embed"
    PROJECT = "project"
    MATCH = "match"
    COMPARE = "compare"
    NORMALIZE = "normalize"
    PROPAGATE = "propagate"
    INTEGRATE = "integrate"
    SIMULATE = "simulate"
    REWRITE = "rewrite"
    COMMIT = "commit"
    INVALIDATE = "invalidate"
    CONSOLIDATE = "consolidate"


@dataclass(frozen=True, slots=True, order=True)
class ExactAuthorityPin:
    """Exact executable authority identity.

    ``content_hash`` is intentionally opaque to the kernel but must be stable and
    non-empty.  The authority layer decides whether it is a SHA-256, canonical record
    fingerprint, or another signed exact content identifier.
    """

    kind: str
    namespace: str
    ref: str
    revision: int
    content_hash: str
    scope_ref: str = "global"

    def __post_init__(self) -> None:
        for value, label in (
            (self.kind, "kind"),
            (self.namespace, "namespace"),
            (self.ref, "ref"),
            (self.content_hash, "content_hash"),
            (self.scope_ref, "scope_ref"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CSIRValidationError(f"authority pin {label} must be non-empty")
        if self.revision < 1:
            raise CSIRValidationError("authority pin revision must be positive")

    @property
    def key(self) -> tuple[str, str, str, int, str, str]:
        return (
            self.kind,
            self.namespace,
            self.ref,
            self.revision,
            self.content_hash,
            self.scope_ref,
        )

    @classmethod
    def from_record_pin(
        cls,
        pin: Any,
        *,
        namespace: str = "cemm",
        scope_ref: str = "global",
    ) -> "ExactAuthorityPin":
        kind = getattr(getattr(pin, "record_kind", None), "value", None)
        if kind is None:
            kind = str(getattr(pin, "record_kind", ""))
        return cls(
            kind=str(kind),
            namespace=namespace,
            ref=str(getattr(pin, "record_ref")),
            revision=int(getattr(pin, "revision")),
            content_hash=str(getattr(pin, "record_fingerprint")),
            scope_ref=scope_ref,
        )


@dataclass(frozen=True, slots=True, order=True)
class CSIRRef:
    kind: CSIRNodeKind
    ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.ref, str) or not self.ref.strip():
            raise CSIRValidationError("CSIR ref must be non-empty")
        if self.kind is CSIRNodeKind.PROOF_LINK:
            raise CSIRValidationError("proof links cannot be semantic fillers/targets")


@dataclass(frozen=True, slots=True)
class SemanticTerm:
    term_ref: str
    term_kind: TermKind
    identity_ref: str | None = None
    literal_value: str | int | float | bool | None = None
    datatype_ref: str | None = None
    type_pins: tuple[ExactAuthorityPin, ...] = ()
    authority_pins: tuple[ExactAuthorityPin, ...] = ()
    features: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _ref(self.term_ref, "term_ref")
        if self.term_kind is TermKind.REFERENT and not self.identity_ref:
            raise CSIRValidationError("referent term requires identity_ref")
        if self.term_kind is TermKind.LITERAL and self.literal_value is None:
            raise CSIRValidationError("literal term requires literal_value")
        if isinstance(self.literal_value, float) and not math.isfinite(self.literal_value):
            raise CSIRValidationError("literal float must be finite")
        _unique(self.type_pins, "term type pins")
        _unique(self.authority_pins, "term authority pins")
        _unique((key for key, _ in self.features), "term feature keys")

    @property
    def node_ref(self) -> CSIRRef:
        return CSIRRef(CSIRNodeKind.TERM, self.term_ref)


@dataclass(frozen=True, slots=True)
class SemanticVariable:
    variable_ref: str
    allowed_kinds: frozenset[CSIRNodeKind] = frozenset(
        {CSIRNodeKind.TERM, CSIRNodeKind.APPLICATION, CSIRNodeKind.COORDINATION}
    )
    required_type_pins: tuple[ExactAuthorityPin, ...] = ()
    scope_ref: str = "global"
    open_purpose: str = "partial"

    def __post_init__(self) -> None:
        _ref(self.variable_ref, "variable_ref")
        _ref(self.scope_ref, "variable scope_ref")
        _ref(self.open_purpose, "variable open_purpose")
        if not self.allowed_kinds:
            raise CSIRValidationError("variable must allow at least one semantic node kind")
        if CSIRNodeKind.VARIABLE in self.allowed_kinds or CSIRNodeKind.PROOF_LINK in self.allowed_kinds:
            raise CSIRValidationError("variable allowed_kinds cannot contain VARIABLE/PROOF_LINK")
        _unique(self.required_type_pins, "variable type pins")

    @property
    def node_ref(self) -> CSIRRef:
        return CSIRRef(CSIRNodeKind.VARIABLE, self.variable_ref)


@dataclass(frozen=True, slots=True)
class SemanticApplication:
    application_ref: str
    predicate_pin: ExactAuthorityPin
    operational_profile_pins: tuple[ExactAuthorityPin, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.application_ref, "application_ref")
        _unique(self.operational_profile_pins, "operational profile pins")

    @property
    def node_ref(self) -> CSIRRef:
        return CSIRRef(CSIRNodeKind.APPLICATION, self.application_ref)


@dataclass(frozen=True, slots=True)
class PortBinding:
    binding_ref: str
    application_ref: str
    port_pin: ExactAuthorityPin
    fillers: tuple[CSIRRef, ...]
    ordered: bool = False

    def __post_init__(self) -> None:
        _ref(self.binding_ref, "binding_ref")
        _ref(self.application_ref, "binding application_ref")
        if not self.fillers:
            raise CSIRValidationError("binding requires at least one filler")
        if not self.ordered:
            _unique(self.fillers, "unordered binding fillers")


@dataclass(frozen=True, slots=True)
class Qualifier:
    qualifier_ref: str
    target: CSIRRef
    qualifier_kind: QualifierKind
    value_ref: CSIRRef | None = None
    value_atom: str | int | float | bool | None = None
    value_pin: ExactAuthorityPin | None = None

    def __post_init__(self) -> None:
        _ref(self.qualifier_ref, "qualifier_ref")
        choices = sum(
            value is not None
            for value in (self.value_ref, self.value_atom, self.value_pin)
        )
        if choices != 1:
            raise CSIRValidationError(
                "qualifier requires exactly one of value_ref/value_atom/value_pin"
            )
        if isinstance(self.value_atom, float) and not math.isfinite(self.value_atom):
            raise CSIRValidationError("qualifier float must be finite")


@dataclass(frozen=True, slots=True)
class ScopeEmbedding:
    embedding_ref: str
    operator: CSIRRef
    scoped: CSIRRef
    scope_kind_pin: ExactAuthorityPin
    order: int = 0

    def __post_init__(self) -> None:
        _ref(self.embedding_ref, "embedding_ref")
        if self.operator.kind is not CSIRNodeKind.APPLICATION:
            raise CSIRValidationError("scope operator must be an application")
        if self.order < 0:
            raise CSIRValidationError("scope order must be non-negative")


@dataclass(frozen=True, slots=True)
class Coordination:
    coordination_ref: str
    coordination_kind_pin: ExactAuthorityPin
    members: tuple[CSIRRef, ...]
    ordered: bool = False

    def __post_init__(self) -> None:
        _ref(self.coordination_ref, "coordination_ref")
        if len(self.members) < 2:
            raise CSIRValidationError("coordination requires at least two members")
        if not self.ordered:
            _unique(self.members, "unordered coordination members")

    @property
    def node_ref(self) -> CSIRRef:
        return CSIRRef(CSIRNodeKind.COORDINATION, self.coordination_ref)


@dataclass(frozen=True, slots=True)
class ProofLink:
    proof_ref: str
    operation: KernelOperation
    subject_refs: tuple[CSIRRef, ...]
    authority_pins: tuple[ExactAuthorityPin, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    parent_proof_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.proof_ref, "proof_ref")
        if not self.subject_refs:
            raise CSIRValidationError("proof link requires at least one semantic subject")
        _unique(self.subject_refs, "proof subjects")
        _unique(self.authority_pins, "proof authority pins")
        _unique(self.evidence_refs, "proof evidence refs")
        _unique(self.parent_proof_refs, "parent proof refs")
        _unique(self.reason_refs, "proof reason refs")


@dataclass(frozen=True, slots=True)
class CSIRGraph:
    terms: tuple[SemanticTerm, ...] = ()
    variables: tuple[SemanticVariable, ...] = ()
    applications: tuple[SemanticApplication, ...] = ()
    bindings: tuple[PortBinding, ...] = ()
    qualifiers: tuple[Qualifier, ...] = ()
    scope_embeddings: tuple[ScopeEmbedding, ...] = ()
    coordinations: tuple[Coordination, ...] = ()
    proof_links: tuple[ProofLink, ...] = ()
    root_refs: tuple[CSIRRef, ...] = ()
    unresolved_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        node_refs: dict[CSIRRef, Any] = {}
        local_refs: set[str] = set()
        collections = (
            (CSIRNodeKind.TERM, self.terms, "term_ref"),
            (CSIRNodeKind.VARIABLE, self.variables, "variable_ref"),
            (CSIRNodeKind.APPLICATION, self.applications, "application_ref"),
            (CSIRNodeKind.COORDINATION, self.coordinations, "coordination_ref"),
        )
        for kind, values, attribute in collections:
            for value in values:
                local = str(getattr(value, attribute))
                if local in local_refs:
                    raise CSIRValidationError(f"local node ref reused across kinds:{local}")
                local_refs.add(local)
                ref = CSIRRef(kind, local)
                node_refs[ref] = value

        _unique((item.binding_ref for item in self.bindings), "binding refs")
        _unique((item.qualifier_ref for item in self.qualifiers), "qualifier refs")
        _unique((item.embedding_ref for item in self.scope_embeddings), "scope embedding refs")
        _unique((item.proof_ref for item in self.proof_links), "proof refs")
        _unique(self.root_refs, "root refs")
        _unique(self.unresolved_refs, "unresolved refs")

        for root in self.root_refs:
            if root not in node_refs:
                raise CSIRValidationError(f"dangling root ref:{root}")

        apps = {item.application_ref: item for item in self.applications}
        bound_ports: set[tuple[str, tuple[str, str, str, int, str, str]]] = set()
        for binding in self.bindings:
            if binding.application_ref not in apps:
                raise CSIRValidationError(
                    f"binding references missing application:{binding.application_ref}"
                )
            key = (binding.application_ref, binding.port_pin.key)
            if key in bound_ports:
                raise CSIRValidationError(
                    f"application has duplicate exact port binding:{binding.application_ref}:{binding.port_pin.ref}"
                )
            bound_ports.add(key)
            for filler in binding.fillers:
                if filler not in node_refs:
                    raise CSIRValidationError(f"dangling binding filler:{filler}")

        for qualifier in self.qualifiers:
            if qualifier.target not in node_refs:
                raise CSIRValidationError(f"dangling qualifier target:{qualifier.target}")
            if qualifier.value_ref is not None and qualifier.value_ref not in node_refs:
                raise CSIRValidationError(f"dangling qualifier value ref:{qualifier.value_ref}")

        scope_edges: dict[CSIRRef, set[CSIRRef]] = {}
        scope_orders: set[tuple[CSIRRef, int]] = set()
        for embedding in self.scope_embeddings:
            if embedding.operator not in node_refs or embedding.scoped not in node_refs:
                raise CSIRValidationError("scope embedding contains dangling node")
            order_key = (embedding.scoped, embedding.order)
            if order_key in scope_orders:
                raise CSIRValidationError(
                    f"ambiguous scope order for {embedding.scoped.ref}@{embedding.order}"
                )
            scope_orders.add(order_key)
            scope_edges.setdefault(embedding.operator, set()).add(embedding.scoped)
        _require_acyclic(scope_edges, "scope embedding")

        coord_edges: dict[CSIRRef, set[CSIRRef]] = {}
        for coordination in self.coordinations:
            coord_ref = coordination.node_ref
            for member in coordination.members:
                if member not in node_refs:
                    raise CSIRValidationError(f"dangling coordination member:{member}")
                coord_edges.setdefault(coord_ref, set()).add(member)
        _require_acyclic(coord_edges, "coordination")

        proof_refs = {item.proof_ref for item in self.proof_links}
        proof_edges: dict[str, set[str]] = {}
        for proof in self.proof_links:
            for subject in proof.subject_refs:
                if subject not in node_refs:
                    raise CSIRValidationError(f"proof references missing subject:{subject}")
            missing_parents = set(proof.parent_proof_refs).difference(proof_refs)
            if missing_parents:
                raise CSIRValidationError(
                    f"proof references missing parents:{sorted(missing_parents)}"
                )
            proof_edges.setdefault(proof.proof_ref, set()).update(proof.parent_proof_refs)
        _require_acyclic(proof_edges, "proof lineage")

    def node(self, ref: CSIRRef) -> Any:
        if ref.kind is CSIRNodeKind.TERM:
            return next((item for item in self.terms if item.term_ref == ref.ref), None)
        if ref.kind is CSIRNodeKind.VARIABLE:
            return next((item for item in self.variables if item.variable_ref == ref.ref), None)
        if ref.kind is CSIRNodeKind.APPLICATION:
            return next((item for item in self.applications if item.application_ref == ref.ref), None)
        if ref.kind is CSIRNodeKind.COORDINATION:
            return next((item for item in self.coordinations if item.coordination_ref == ref.ref), None)
        return None

    def bindings_for(self, application_ref: str) -> tuple[PortBinding, ...]:
        return tuple(item for item in self.bindings if item.application_ref == application_ref)

    def qualifiers_for(self, target: CSIRRef) -> tuple[Qualifier, ...]:
        return tuple(item for item in self.qualifiers if item.target == target)

    def to_primitive(self) -> Mapping[str, Any]:
        return _graph_to_primitive(self)

    @classmethod
    def from_primitive(cls, value: Mapping[str, Any]) -> "CSIRGraph":
        return _graph_from_primitive(value)


@dataclass(frozen=True, slots=True)
class CSIRCandidate:
    candidate_ref: str
    graph: CSIRGraph
    semantic_fingerprint: str
    exact_fingerprint: str
    authority_generation: int
    authority_fingerprint: str
    kernel_abi_fingerprint: str
    evidence_refs: tuple[str, ...] = ()
    closure_proof_refs: tuple[str, ...] = ()
    hard_constraint_trace_refs: tuple[str, ...] = ()
    execution_authority_ref: str = ""
    semantic_authority_snapshot_fingerprint: str = ""
    dynamics_parameter_pins: tuple[ExactAuthorityPin, ...] = ()
    use_authorization_pins: tuple[ExactAuthorityPin, ...] = ()
    projection_authority_pins: tuple[ExactAuthorityPin, ...] = ()
    causal_mechanism_pins: tuple[ExactAuthorityPin, ...] = ()
    policy_adapter_pins: tuple[ExactAuthorityPin, ...] = ()
    projection_authority_required: bool = False
    prior_score: float = 0.0

    def __post_init__(self) -> None:
        _ref(self.candidate_ref, "candidate_ref")
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise CSIRValidationError("candidate requires exact authority generation")
        for value, label in (
            (self.semantic_fingerprint, "semantic_fingerprint"),
            (self.exact_fingerprint, "exact_fingerprint"),
            (self.kernel_abi_fingerprint, "kernel_abi_fingerprint"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CSIRValidationError(f"candidate {label} must be non-empty")
        if not math.isfinite(self.prior_score):
            raise CSIRValidationError("candidate prior score must be finite")
        _unique(self.evidence_refs, "candidate evidence refs")
        _unique(self.closure_proof_refs, "candidate closure proof refs")
        _unique(self.hard_constraint_trace_refs, "candidate hard constraint refs")
        for label, pins in (
            ("dynamics", self.dynamics_parameter_pins),
            ("use authorization", self.use_authorization_pins),
            ("projection authority", self.projection_authority_pins),
            ("causal mechanism", self.causal_mechanism_pins),
            ("policy/adapter", self.policy_adapter_pins),
        ):
            _unique((pin.key for pin in pins), f"candidate {label} pins")


@dataclass(frozen=True, slots=True)
class CSIRCandidateFragment:
    fragment_ref: str
    graph: CSIRGraph
    evidence_refs: tuple[str, ...] = ()
    # Opaque refs are retained only as historical/audit metadata. Stage 5 authority
    # requires the typed payloads below and validates them against the normalized graph.
    closure_proof_refs: tuple[str, ...] = ()
    closure_proofs: tuple[Any, ...] = ()
    hard_constraint_trace_refs: tuple[str, ...] = ()
    hard_constraint_traces: tuple[Any, ...] = ()
    projection_authority_pins: tuple[ExactAuthorityPin, ...] = ()
    causal_mechanism_pins: tuple[ExactAuthorityPin, ...] = ()
    policy_adapter_pins: tuple[ExactAuthorityPin, ...] = ()
    requires_projection_authority: bool = False
    prior_score: float = 0.0

    def __post_init__(self) -> None:
        _ref(self.fragment_ref, "fragment_ref")
        if not math.isfinite(self.prior_score):
            raise CSIRValidationError("fragment prior score must be finite")
        _unique(self.evidence_refs, "fragment evidence refs")
        _unique(self.closure_proof_refs, "fragment closure proof refs")
        proof_refs = tuple(getattr(item, "proof_ref", "") for item in self.closure_proofs)
        if any(not ref for ref in proof_refs):
            raise CSIRValidationError("typed closure proof payloads require stable proof_ref")
        _unique(proof_refs, "fragment typed closure proofs")
        _unique(self.hard_constraint_trace_refs, "fragment hard constraint refs")
        trace_refs = tuple(getattr(item, "trace_ref", "") for item in self.hard_constraint_traces)
        if any(not ref for ref in trace_refs):
            raise CSIRValidationError("typed hard constraint traces require stable trace_ref")
        _unique(trace_refs, "fragment typed hard constraint traces")
        _unique((pin.key for pin in self.projection_authority_pins), "fragment projection authority pins")
        _unique((pin.key for pin in self.causal_mechanism_pins), "fragment causal mechanism pins")
        _unique((pin.key for pin in self.policy_adapter_pins), "fragment policy/adapter pins")


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CSIRValidationError(f"{label} must be non-empty")


def _unique(values: Iterable[Any], label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise CSIRValidationError(f"{label} must be unique")


def _require_acyclic(edges: Mapping[CSIRRef, set[CSIRRef]], label: str) -> None:
    visiting: set[CSIRRef] = set()
    visited: set[CSIRRef] = set()

    def visit(node: CSIRRef) -> None:
        if node in visited:
            return
        if node in visiting:
            raise CSIRValidationError(f"cyclic {label}")
        visiting.add(node)
        for child in edges.get(node, set()):
            if child in edges:
                visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in tuple(edges):
        visit(node)


def _pin_to_primitive(pin: ExactAuthorityPin) -> dict[str, Any]:
    return {
        "kind": pin.kind,
        "namespace": pin.namespace,
        "ref": pin.ref,
        "revision": pin.revision,
        "content_hash": pin.content_hash,
        "scope_ref": pin.scope_ref,
    }


def _pin_from_primitive(value: Mapping[str, Any]) -> ExactAuthorityPin:
    return ExactAuthorityPin(
        kind=str(value["kind"]),
        namespace=str(value["namespace"]),
        ref=str(value["ref"]),
        revision=int(value["revision"]),
        content_hash=str(value["content_hash"]),
        scope_ref=str(value.get("scope_ref", "global")),
    )


def _ref_to_primitive(ref: CSIRRef) -> dict[str, str]:
    return {"kind": ref.kind.value, "ref": ref.ref}


def _ref_from_primitive(value: Mapping[str, Any]) -> CSIRRef:
    return CSIRRef(CSIRNodeKind(str(value["kind"])), str(value["ref"]))


def _graph_to_primitive(graph: CSIRGraph) -> Mapping[str, Any]:
    return {
        "terms": [
            {
                "term_ref": x.term_ref,
                "term_kind": x.term_kind.value,
                "identity_ref": x.identity_ref,
                "literal_value": x.literal_value,
                "datatype_ref": x.datatype_ref,
                "type_pins": [_pin_to_primitive(p) for p in x.type_pins],
                "authority_pins": [_pin_to_primitive(p) for p in x.authority_pins],
                "features": [list(item) for item in x.features],
            }
            for x in graph.terms
        ],
        "variables": [
            {
                "variable_ref": x.variable_ref,
                "allowed_kinds": sorted(k.value for k in x.allowed_kinds),
                "required_type_pins": [_pin_to_primitive(p) for p in x.required_type_pins],
                "scope_ref": x.scope_ref,
                "open_purpose": x.open_purpose,
            }
            for x in graph.variables
        ],
        "applications": [
            {
                "application_ref": x.application_ref,
                "predicate_pin": _pin_to_primitive(x.predicate_pin),
                "operational_profile_pins": [_pin_to_primitive(p) for p in x.operational_profile_pins],
            }
            for x in graph.applications
        ],
        "bindings": [
            {
                "binding_ref": x.binding_ref,
                "application_ref": x.application_ref,
                "port_pin": _pin_to_primitive(x.port_pin),
                "fillers": [_ref_to_primitive(r) for r in x.fillers],
                "ordered": x.ordered,
            }
            for x in graph.bindings
        ],
        "qualifiers": [
            {
                "qualifier_ref": x.qualifier_ref,
                "target": _ref_to_primitive(x.target),
                "qualifier_kind": x.qualifier_kind.value,
                "value_ref": None if x.value_ref is None else _ref_to_primitive(x.value_ref),
                "value_atom": x.value_atom,
                "value_pin": None if x.value_pin is None else _pin_to_primitive(x.value_pin),
            }
            for x in graph.qualifiers
        ],
        "scope_embeddings": [
            {
                "embedding_ref": x.embedding_ref,
                "operator": _ref_to_primitive(x.operator),
                "scoped": _ref_to_primitive(x.scoped),
                "scope_kind_pin": _pin_to_primitive(x.scope_kind_pin),
                "order": x.order,
            }
            for x in graph.scope_embeddings
        ],
        "coordinations": [
            {
                "coordination_ref": x.coordination_ref,
                "coordination_kind_pin": _pin_to_primitive(x.coordination_kind_pin),
                "members": [_ref_to_primitive(r) for r in x.members],
                "ordered": x.ordered,
            }
            for x in graph.coordinations
        ],
        "proof_links": [
            {
                "proof_ref": x.proof_ref,
                "operation": x.operation.value,
                "subject_refs": [_ref_to_primitive(r) for r in x.subject_refs],
                "authority_pins": [_pin_to_primitive(p) for p in x.authority_pins],
                "evidence_refs": list(x.evidence_refs),
                "parent_proof_refs": list(x.parent_proof_refs),
                "reason_refs": list(x.reason_refs),
            }
            for x in graph.proof_links
        ],
        "root_refs": [_ref_to_primitive(r) for r in graph.root_refs],
        "unresolved_refs": list(graph.unresolved_refs),
    }


def _graph_from_primitive(value: Mapping[str, Any]) -> CSIRGraph:
    return CSIRGraph(
        terms=tuple(
            SemanticTerm(
                term_ref=str(x["term_ref"]),
                term_kind=TermKind(str(x["term_kind"])),
                identity_ref=None if x.get("identity_ref") is None else str(x.get("identity_ref")),
                literal_value=x.get("literal_value"),
                datatype_ref=None if x.get("datatype_ref") is None else str(x.get("datatype_ref")),
                type_pins=tuple(_pin_from_primitive(p) for p in x.get("type_pins", ())),
                authority_pins=tuple(_pin_from_primitive(p) for p in x.get("authority_pins", ())),
                features=tuple((str(k), str(v)) for k, v in x.get("features", ())),
            )
            for x in value.get("terms", ())
        ),
        variables=tuple(
            SemanticVariable(
                variable_ref=str(x["variable_ref"]),
                allowed_kinds=frozenset(CSIRNodeKind(str(k)) for k in x.get("allowed_kinds", ())),
                required_type_pins=tuple(_pin_from_primitive(p) for p in x.get("required_type_pins", ())),
                scope_ref=str(x.get("scope_ref", "global")),
                open_purpose=str(x.get("open_purpose", "partial")),
            )
            for x in value.get("variables", ())
        ),
        applications=tuple(
            SemanticApplication(
                application_ref=str(x["application_ref"]),
                predicate_pin=_pin_from_primitive(x["predicate_pin"]),
                operational_profile_pins=tuple(_pin_from_primitive(p) for p in x.get("operational_profile_pins", ())),
            )
            for x in value.get("applications", ())
        ),
        bindings=tuple(
            PortBinding(
                binding_ref=str(x["binding_ref"]),
                application_ref=str(x["application_ref"]),
                port_pin=_pin_from_primitive(x["port_pin"]),
                fillers=tuple(_ref_from_primitive(r) for r in x.get("fillers", ())),
                ordered=bool(x.get("ordered", False)),
            )
            for x in value.get("bindings", ())
        ),
        qualifiers=tuple(
            Qualifier(
                qualifier_ref=str(x["qualifier_ref"]),
                target=_ref_from_primitive(x["target"]),
                qualifier_kind=QualifierKind(str(x["qualifier_kind"])),
                value_ref=None if x.get("value_ref") is None else _ref_from_primitive(x["value_ref"]),
                value_atom=x.get("value_atom"),
                value_pin=None if x.get("value_pin") is None else _pin_from_primitive(x["value_pin"]),
            )
            for x in value.get("qualifiers", ())
        ),
        scope_embeddings=tuple(
            ScopeEmbedding(
                embedding_ref=str(x["embedding_ref"]),
                operator=_ref_from_primitive(x["operator"]),
                scoped=_ref_from_primitive(x["scoped"]),
                scope_kind_pin=_pin_from_primitive(x["scope_kind_pin"]),
                order=int(x.get("order", 0)),
            )
            for x in value.get("scope_embeddings", ())
        ),
        coordinations=tuple(
            Coordination(
                coordination_ref=str(x["coordination_ref"]),
                coordination_kind_pin=_pin_from_primitive(x["coordination_kind_pin"]),
                members=tuple(_ref_from_primitive(r) for r in x.get("members", ())),
                ordered=bool(x.get("ordered", False)),
            )
            for x in value.get("coordinations", ())
        ),
        proof_links=tuple(
            ProofLink(
                proof_ref=str(x["proof_ref"]),
                operation=KernelOperation(str(x["operation"])),
                subject_refs=tuple(_ref_from_primitive(r) for r in x.get("subject_refs", ())),
                authority_pins=tuple(_pin_from_primitive(p) for p in x.get("authority_pins", ())),
                evidence_refs=tuple(map(str, x.get("evidence_refs", ()))),
                parent_proof_refs=tuple(map(str, x.get("parent_proof_refs", ()))),
                reason_refs=tuple(map(str, x.get("reason_refs", ()))),
            )
            for x in value.get("proof_links", ())
        ),
        root_refs=tuple(_ref_from_primitive(r) for r in value.get("root_refs", ())),
        unresolved_refs=tuple(map(str, value.get("unresolved_refs", ()))),
    )


__all__ = [
    "CSIRCandidate",
    "CSIRCandidateFragment",
    "CSIRGraph",
    "CSIRNodeKind",
    "CSIRRef",
    "CSIRValidationError",
    "Coordination",
    "ExactAuthorityPin",
    "KernelOperation",
    "PortBinding",
    "ProofLink",
    "Qualifier",
    "QualifierKind",
    "ScopeEmbedding",
    "SemanticApplication",
    "SemanticTerm",
    "SemanticVariable",
    "TermKind",
]
