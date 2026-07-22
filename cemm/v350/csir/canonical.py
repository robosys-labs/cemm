"""Exact canonical labeling, normalization and equivalence for CSIR v2.

Local refs and insertion order are occurrence mechanics, never semantic identity.
Canonicalization therefore operates over an attributed directed relational graph and
finds a ref-independent normal form.  Ambiguous automorphism classes are enumerated
only within an explicit budget; budget exhaustion is a typed failure, never a fallback
to local refs.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import permutations, product
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

from .authority import CURRENT_KERNEL_ABI
from .model import (
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    Coordination,
    PortBinding,
    ProofLink,
    Qualifier,
    ScopeEmbedding,
    SemanticApplication,
    SemanticTerm,
    SemanticVariable,
)


class CanonicalizationError(ValueError):
    pass


class CanonicalizationBudgetExceeded(CanonicalizationError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalizationResult:
    semantic_code: str
    semantic_fingerprint: str
    exact_code: str
    exact_fingerprint: str
    normalized_graph: CSIRGraph
    semantic_node_map: Mapping[tuple[str, str], str]
    proof_ref_map: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ComparisonAssessment:
    equivalent: bool
    left_fingerprint: str
    right_fingerprint: str
    reasons: tuple[str, ...] = ()


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pin(pin: Any) -> tuple[Any, ...]:
    return tuple(pin.key)


def _atom(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("non-finite numeric semantic atom")
        # JSON has unstable -0.0 semantics across producers; canonicalize it.
        if value == 0.0:
            return 0.0
    return value


def _vkey(kind: str, ref: str) -> tuple[str, str]:
    return kind, ref


def _semantic_ref_key(ref: CSIRRef) -> tuple[str, str]:
    return ref.kind.value, ref.ref


def _build_relational_graph(
    graph: CSIRGraph,
    *,
    include_proofs: bool,
) -> tuple[dict[tuple[str, str], Any], list[tuple[tuple[str, str], str, tuple[str, str]]]]:
    attrs: dict[tuple[str, str], Any] = {}
    edges: list[tuple[tuple[str, str], str, tuple[str, str]]] = []
    root_set = {_semantic_ref_key(ref) for ref in graph.root_refs}

    for item in graph.terms:
        key = _vkey("term", item.term_ref)
        attrs[key] = (
            "term",
            item.term_kind.value,
            item.identity_ref,
            _atom(item.literal_value),
            item.datatype_ref,
            tuple(sorted(_pin(p) for p in item.type_pins)),
            tuple(sorted(_pin(p) for p in item.authority_pins)),
            tuple(sorted(item.features)),
            key in root_set,
        )
    for item in graph.variables:
        key = _vkey("variable", item.variable_ref)
        attrs[key] = (
            "variable",
            tuple(sorted(k.value for k in item.allowed_kinds)),
            tuple(sorted(_pin(p) for p in item.required_type_pins)),
            item.scope_ref,
            item.open_purpose,
            key in root_set,
        )
    for item in graph.applications:
        key = _vkey("application", item.application_ref)
        attrs[key] = (
            "application",
            _pin(item.predicate_pin),
            tuple(sorted(_pin(p) for p in item.operational_profile_pins)),
            key in root_set,
        )
    for item in graph.coordinations:
        key = _vkey("coordination", item.coordination_ref)
        attrs[key] = (
            "coordination",
            _pin(item.coordination_kind_pin),
            item.ordered,
            key in root_set,
        )
        for index, member in enumerate(item.members):
            label = f"member:{index}" if item.ordered else "member"
            edges.append((key, label, _semantic_ref_key(member)))

    for item in graph.bindings:
        key = _vkey("binding", item.binding_ref)
        attrs[key] = ("binding", _pin(item.port_pin), item.ordered)
        edges.append((_vkey("application", item.application_ref), "has_binding", key))
        for index, filler in enumerate(item.fillers):
            label = f"filler:{index}" if item.ordered else "filler"
            edges.append((key, label, _semantic_ref_key(filler)))

    for item in graph.qualifiers:
        key = _vkey("qualifier", item.qualifier_ref)
        attrs[key] = (
            "qualifier",
            item.qualifier_kind.value,
            _atom(item.value_atom),
            None if item.value_pin is None else _pin(item.value_pin),
        )
        edges.append((key, "target", _semantic_ref_key(item.target)))
        if item.value_ref is not None:
            edges.append((key, "value_ref", _semantic_ref_key(item.value_ref)))

    for item in graph.scope_embeddings:
        key = _vkey("scope", item.embedding_ref)
        attrs[key] = ("scope", _pin(item.scope_kind_pin), item.order)
        edges.append((key, "operator", _semantic_ref_key(item.operator)))
        edges.append((key, "scoped", _semantic_ref_key(item.scoped)))

    if include_proofs:
        for item in graph.proof_links:
            key = _vkey("proof", item.proof_ref)
            attrs[key] = (
                "proof",
                item.operation.value,
                tuple(sorted(_pin(p) for p in item.authority_pins)),
                tuple(sorted(item.evidence_refs)),
                tuple(sorted(item.reason_refs)),
            )
            for subject in item.subject_refs:
                edges.append((key, "subject", _semantic_ref_key(subject)))
            for parent in item.parent_proof_refs:
                edges.append((key, "parent_proof", _vkey("proof", parent)))

    missing = {
        endpoint
        for source, _label, target in edges
        for endpoint in (source, target)
        if endpoint not in attrs
    }
    if missing:
        raise CanonicalizationError(f"relational graph contains dangling vertices:{sorted(missing)}")
    return attrs, edges


def _initial_colors(attrs: Mapping[tuple[str, str], Any]) -> dict[tuple[str, str], str]:
    return {key: _sha(_json(value)) for key, value in attrs.items()}


def _refine(
    attrs: Mapping[tuple[str, str], Any],
    edges: Iterable[tuple[tuple[str, str], str, tuple[str, str]]],
) -> dict[tuple[str, str], str]:
    colors = _initial_colors(attrs)
    outgoing: dict[tuple[str, str], list[tuple[str, tuple[str, str]]]] = {key: [] for key in attrs}
    incoming: dict[tuple[str, str], list[tuple[str, tuple[str, str]]]] = {key: [] for key in attrs}
    for source, label, target in edges:
        outgoing[source].append((label, target))
        incoming[target].append((label, source))
    for _iteration in range(max(2, len(attrs) + 1)):
        next_colors = {}
        for key in attrs:
            signature = (
                colors[key],
                tuple(sorted((label, colors[target]) for label, target in outgoing[key])),
                tuple(sorted((label, colors[source]) for label, source in incoming[key])),
            )
            next_colors[key] = _sha(_json(signature))
        if next_colors == colors:
            break
        colors = next_colors
    return colors


def _candidate_orders(
    attrs: Mapping[tuple[str, str], Any],
    edges: list[tuple[tuple[str, str], str, tuple[str, str]]],
    *,
    budget: int,
) -> Iterable[tuple[tuple[str, str], ...]]:
    colors = _refine(attrs, edges)
    groups: dict[str, list[tuple[str, str]]] = {}
    for key, color in colors.items():
        groups.setdefault(color, []).append(key)
    ordered_groups = [groups[color] for color in sorted(groups)]

    # Ambiguous cells are exactly where graph automorphism/local-ref ambiguity remains.
    # Never use local refs to break them. Enumerate all labelings under an explicit bound.
    count = 1
    variants: list[tuple[tuple[tuple[str, str], ...], ...]] = []
    for group in ordered_groups:
        if len(group) == 1:
            variants.append(((group[0],),))
            continue
        factor = math.factorial(len(group))
        count *= factor
        if count > budget:
            raise CanonicalizationBudgetExceeded(
                "canonical labeling automorphism budget exceeded: "
                f"needed>{budget}; ambiguous class size={len(group)}"
            )
        variants.append(tuple(permutations(tuple(group))))

    for selected in product(*variants):
        yield tuple(node for group in selected for node in group)


def _code_for_order(
    attrs: Mapping[tuple[str, str], Any],
    edges: Iterable[tuple[tuple[str, str], str, tuple[str, str]]],
    order: tuple[tuple[str, str], ...],
    *,
    include_unresolved: tuple[str, ...] = (),
) -> str:
    index = {key: i for i, key in enumerate(order)}
    vertices = tuple(attrs[key] for key in order)
    edge_code = tuple(sorted((index[s], label, index[t]) for s, label, t in edges))
    return _json(
        {
            "kernel_abi": CURRENT_KERNEL_ABI.fingerprint,
            "vertices": vertices,
            "edges": edge_code,
            "unresolved_refs": tuple(sorted(include_unresolved)),
        }
    )


def _best_order(
    graph: CSIRGraph,
    *,
    include_proofs: bool,
    budget: int,
    include_unresolved: bool,
) -> tuple[str, tuple[tuple[str, str], ...]]:
    attrs, edges = _build_relational_graph(graph, include_proofs=include_proofs)
    if not attrs:
        code = _json(
            {
                "kernel_abi": CURRENT_KERNEL_ABI.fingerprint,
                "vertices": (),
                "edges": (),
                "unresolved_refs": tuple(sorted(graph.unresolved_refs)) if include_unresolved else (),
            }
        )
        return code, ()
    best_code: str | None = None
    best_order: tuple[tuple[str, str], ...] | None = None
    for order in _candidate_orders(attrs, edges, budget=budget):
        code = _code_for_order(
            attrs,
            edges,
            order,
            include_unresolved=(graph.unresolved_refs if include_unresolved else ()),
        )
        if best_code is None or code < best_code:
            best_code, best_order = code, order
    assert best_code is not None and best_order is not None
    return best_code, best_order


def canonical_semantic_code(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    code, _ = _best_order(
        graph,
        include_proofs=False,
        budget=budget,
        include_unresolved=False,
    )
    return code


def canonical_exact_code(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    code, _ = _best_order(
        graph,
        include_proofs=True,
        budget=budget,
        include_unresolved=True,
    )
    return code


def semantic_fingerprint(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    return _sha(canonical_semantic_code(graph, budget=budget))


def exact_fingerprint(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    return _sha(canonical_exact_code(graph, budget=budget))


def normalize(graph: CSIRGraph, *, budget: int = 100_000) -> CSIRGraph:
    # Semantic local labels must not change when proof/audit lineage changes. Derive all
    # semantic/structural constructor names from the proof-free normal form, then derive
    # proof-link names independently from the exact graph.
    _semantic_code, semantic_order = _best_order(
        graph,
        include_proofs=False,
        budget=budget,
        include_unresolved=False,
    )
    _exact_code, exact_order = _best_order(
        graph,
        include_proofs=True,
        budget=budget,
        include_unresolved=True,
    )
    proof_order = tuple(key for key in exact_order if key[0] == "proof")
    order = (*semantic_order, *proof_order)
    counters: dict[str, int] = {}
    mapping: dict[tuple[str, str], str] = {}
    prefixes = {
        "term": "t",
        "variable": "v",
        "application": "a",
        "coordination": "c",
        "binding": "b",
        "qualifier": "q",
        "scope": "s",
        "proof": "p",
    }
    for key in order:
        kind = key[0]
        prefix = prefixes[kind]
        index = counters.get(kind, 0)
        counters[kind] = index + 1
        mapping[key] = f"{prefix}{index}"

    def ref(value: CSIRRef) -> CSIRRef:
        return CSIRRef(value.kind, mapping[(value.kind.value, value.ref)])

    terms = tuple(
        replace(x, term_ref=mapping[("term", x.term_ref)])
        for x in sorted(graph.terms, key=lambda x: mapping[("term", x.term_ref)])
    )
    variables = tuple(
        replace(x, variable_ref=mapping[("variable", x.variable_ref)])
        for x in sorted(graph.variables, key=lambda x: mapping[("variable", x.variable_ref)])
    )
    applications = tuple(
        replace(x, application_ref=mapping[("application", x.application_ref)])
        for x in sorted(graph.applications, key=lambda x: mapping[("application", x.application_ref)])
    )
    bindings = tuple(
        replace(
            x,
            binding_ref=mapping[("binding", x.binding_ref)],
            application_ref=mapping[("application", x.application_ref)],
            fillers=tuple(ref(r) for r in x.fillers),
        )
        for x in sorted(graph.bindings, key=lambda x: mapping[("binding", x.binding_ref)])
    )
    qualifiers = tuple(
        replace(
            x,
            qualifier_ref=mapping[("qualifier", x.qualifier_ref)],
            target=ref(x.target),
            value_ref=None if x.value_ref is None else ref(x.value_ref),
        )
        for x in sorted(graph.qualifiers, key=lambda x: mapping[("qualifier", x.qualifier_ref)])
    )
    scopes = tuple(
        replace(
            x,
            embedding_ref=mapping[("scope", x.embedding_ref)],
            operator=ref(x.operator),
            scoped=ref(x.scoped),
        )
        for x in sorted(graph.scope_embeddings, key=lambda x: mapping[("scope", x.embedding_ref)])
    )
    coordinations = tuple(
        replace(
            x,
            coordination_ref=mapping[("coordination", x.coordination_ref)],
            members=tuple(ref(r) for r in x.members),
        )
        for x in sorted(graph.coordinations, key=lambda x: mapping[("coordination", x.coordination_ref)])
    )
    proof_links = tuple(
        replace(
            x,
            proof_ref=mapping[("proof", x.proof_ref)],
            subject_refs=tuple(ref(r) for r in x.subject_refs),
            parent_proof_refs=tuple(mapping[("proof", p)] for p in x.parent_proof_refs),
        )
        for x in sorted(graph.proof_links, key=lambda x: mapping[("proof", x.proof_ref)])
    )
    return CSIRGraph(
        terms=terms,
        variables=variables,
        applications=applications,
        bindings=bindings,
        qualifiers=qualifiers,
        scope_embeddings=scopes,
        coordinations=coordinations,
        proof_links=proof_links,
        root_refs=tuple(sorted((ref(r) for r in graph.root_refs), key=lambda r: (r.kind.value, r.ref))),
        unresolved_refs=tuple(sorted(graph.unresolved_refs)),
    )


def canonicalize(graph: CSIRGraph, *, budget: int = 100_000) -> CanonicalizationResult:
    normalized = normalize(graph, budget=budget)
    semantic_code = canonical_semantic_code(normalized, budget=budget)
    exact_code = canonical_exact_code(normalized, budget=budget)
    _code, semantic_order = _best_order(
        graph, include_proofs=False, budget=budget, include_unresolved=False
    )
    _ecode, exact_order = _best_order(
        graph, include_proofs=True, budget=budget, include_unresolved=True
    )
    counters: dict[str, int] = {}
    prefixes = {
        "term": "t", "variable": "v", "application": "a", "coordination": "c",
        "binding": "b", "qualifier": "q", "scope": "s",
    }
    semantic_map: dict[tuple[str, str], str] = {}
    for key in semantic_order:
        prefix = prefixes[key[0]]; index = counters.get(key[0], 0); counters[key[0]] = index + 1
        semantic_map[key] = f"{prefix}{index}"
    proof_order = tuple(key for key in exact_order if key[0] == "proof")
    proof_map = {key[1]: f"p{index}" for index, key in enumerate(proof_order)}
    return CanonicalizationResult(
        semantic_code=semantic_code,
        semantic_fingerprint=_sha(semantic_code),
        exact_code=exact_code,
        exact_fingerprint=_sha(exact_code),
        normalized_graph=normalized,
        semantic_node_map=semantic_map,
        proof_ref_map=proof_map,
    )


def equivalent(left: CSIRGraph, right: CSIRGraph, *, budget: int = 100_000) -> bool:
    return semantic_fingerprint(left, budget=budget) == semantic_fingerprint(right, budget=budget)


def compare(left: CSIRGraph, right: CSIRGraph, *, budget: int = 100_000) -> ComparisonAssessment:
    left_fp = semantic_fingerprint(left, budget=budget)
    right_fp = semantic_fingerprint(right, budget=budget)
    return ComparisonAssessment(
        equivalent=left_fp == right_fp,
        left_fingerprint=left_fp,
        right_fingerprint=right_fp,
        reasons=() if left_fp == right_fp else ("canonical_semantic_normal_forms_differ",),
    )


__all__ = [
    "CanonicalizationBudgetExceeded",
    "CanonicalizationError",
    "CanonicalizationResult",
    "ComparisonAssessment",
    "canonical_exact_code",
    "canonical_semantic_code",
    "canonicalize",
    "compare",
    "equivalent",
    "exact_fingerprint",
    "normalize",
    "semantic_fingerprint",
]
