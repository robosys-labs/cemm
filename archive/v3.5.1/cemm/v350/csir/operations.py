"""Bounded exact CSIR kernel operations.

These operations manipulate only CSIR constructors and exact authority pins. They do
not branch on language words, domain concept names, storage record kinds, or legacy
UOL structures.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from .canonical_v351 import ComparisonAssessment, compare as compare_graphs, normalize
from .model import (
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    Coordination,
    ExactAuthorityPin,
    KernelOperation,
    PortBinding,
    ProofLink,
    Qualifier,
    QualifierKind,
    ScopeEmbedding,
    SemanticApplication,
    SemanticTerm,
    SemanticVariable,
)


class KernelOperationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Substitution:
    bindings: tuple[tuple[str, CSIRRef], ...] = ()

    def __post_init__(self) -> None:
        keys = [key for key, _ in self.bindings]
        if len(keys) != len(set(keys)):
            raise KernelOperationError("substitution binds a variable more than once")

    def get(self, variable_ref: str) -> CSIRRef | None:
        return next((value for key, value in self.bindings if key == variable_ref), None)

    def extend(self, variable_ref: str, value: CSIRRef) -> "Substitution":
        existing = self.get(variable_ref)
        if existing is not None and existing != value:
            raise KernelOperationError(f"conflicting substitution for {variable_ref}")
        if existing is not None:
            return self
        return Substitution(tuple(sorted((*self.bindings, (variable_ref, value)), key=lambda x: x[0])))


@dataclass(frozen=True, slots=True)
class UnificationResult:
    success: bool
    substitution: Substitution
    reason_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MatchResult:
    matched: bool
    substitution: Substitution
    matched_root_pairs: tuple[tuple[CSIRRef, CSIRRef], ...] = ()
    reason_refs: tuple[str, ...] = ()


def _variable_map(graph: CSIRGraph) -> dict[str, SemanticVariable]:
    return {item.variable_ref: item for item in graph.variables}


def _term_map(graph: CSIRGraph) -> dict[str, SemanticTerm]:
    return {item.term_ref: item for item in graph.terms}


def _app_map(graph: CSIRGraph) -> dict[str, SemanticApplication]:
    return {item.application_ref: item for item in graph.applications}


def _coord_map(graph: CSIRGraph) -> dict[str, Coordination]:
    return {item.coordination_ref: item for item in graph.coordinations}


def _binding_map(graph: CSIRGraph) -> dict[str, tuple[PortBinding, ...]]:
    result: dict[str, list[PortBinding]] = {}
    for binding in graph.bindings:
        result.setdefault(binding.application_ref, []).append(binding)
    return {key: tuple(sorted(value, key=lambda x: x.port_pin.key)) for key, value in result.items()}


def _node_type_pins(graph: CSIRGraph, ref: CSIRRef) -> frozenset[ExactAuthorityPin]:
    if ref.kind is CSIRNodeKind.TERM:
        term = _term_map(graph).get(ref.ref)
        return frozenset(() if term is None else term.type_pins)
    return frozenset()


def _check_variable_accepts(graph: CSIRGraph, variable: SemanticVariable, filler: CSIRRef) -> None:
    if filler.kind not in variable.allowed_kinds:
        raise KernelOperationError(
            f"variable {variable.variable_ref} rejects filler kind {filler.kind.value}"
        )
    if variable.required_type_pins:
        observed = _node_type_pins(graph, filler)
        if not set(variable.required_type_pins).issubset(observed):
            raise KernelOperationError(
                f"variable {variable.variable_ref} required type pins are not satisfied"
            )


def substitute(graph: CSIRGraph, substitution: Substitution) -> CSIRGraph:
    variables = _variable_map(graph)
    for variable_ref, filler in substitution.bindings:
        variable = variables.get(variable_ref)
        if variable is None:
            raise KernelOperationError(f"unknown substitution variable:{variable_ref}")
        if filler.kind is CSIRNodeKind.VARIABLE:
            target = variables.get(filler.ref)
            if target is None:
                raise KernelOperationError(f"substitution targets unknown variable:{filler.ref}")
            # Variable-to-variable substitution must narrow, never widen, constraints.
            if not target.allowed_kinds.issubset(variable.allowed_kinds):
                raise KernelOperationError("variable substitution widens allowed node kinds")
            if not set(variable.required_type_pins).issubset(set(target.required_type_pins)):
                raise KernelOperationError("variable substitution drops required type constraints")
        else:
            _check_variable_accepts(graph, variable, filler)

    def ref(value: CSIRRef) -> CSIRRef:
        seen: set[str] = set()
        current = value
        while current.kind is CSIRNodeKind.VARIABLE:
            if current.ref in seen:
                raise KernelOperationError("cyclic variable substitution")
            seen.add(current.ref)
            replacement = substitution.get(current.ref)
            if replacement is None:
                break
            current = replacement
        return current

    bound = {key for key, value in substitution.bindings if value.kind is not CSIRNodeKind.VARIABLE or value.ref != key}
    result = CSIRGraph(
        terms=graph.terms,
        variables=tuple(item for item in graph.variables if item.variable_ref not in bound),
        applications=graph.applications,
        bindings=tuple(replace(item, fillers=tuple(ref(x) for x in item.fillers)) for item in graph.bindings),
        qualifiers=tuple(
            replace(
                item,
                target=ref(item.target),
                value_ref=None if item.value_ref is None else ref(item.value_ref),
            )
            for item in graph.qualifiers
        ),
        scope_embeddings=tuple(
            replace(item, operator=ref(item.operator), scoped=ref(item.scoped))
            for item in graph.scope_embeddings
        ),
        coordinations=tuple(replace(item, members=tuple(ref(x) for x in item.members)) for item in graph.coordinations),
        proof_links=tuple(replace(item, subject_refs=tuple(ref(x) for x in item.subject_refs)) for item in graph.proof_links),
        root_refs=tuple(ref(x) for x in graph.root_refs),
        unresolved_refs=graph.unresolved_refs,
    )
    return result


def bind(graph: CSIRGraph, variable_ref: str, filler: CSIRRef) -> CSIRGraph:
    return substitute(graph, Substitution(((variable_ref, filler),)))


def instantiate(graph: CSIRGraph, *, namespace: str) -> CSIRGraph:
    if not namespace.strip():
        raise KernelOperationError("instantiate requires a non-empty namespace")
    prefix = "inst_" + "".join(ch if ch.isalnum() else "_" for ch in namespace) + "_"
    return _rename_graph(graph, prefix)


def compose(*graphs: CSIRGraph, substitutions: Mapping[int, Substitution] | None = None) -> CSIRGraph:
    if not graphs:
        return CSIRGraph()
    substitutions = substitutions or {}
    renamed: list[CSIRGraph] = []
    used: set[tuple[str, str]] = set()
    for index, original in enumerate(graphs):
        graph = substitute(original, substitutions[index]) if index in substitutions else original
        keys = _all_local_keys(graph)
        if used.intersection(keys):
            graph = _rename_graph(graph, f"g{index}_")
            keys = _all_local_keys(graph)
            if used.intersection(keys):
                raise KernelOperationError("compose could not isolate local ref collision")
        used.update(keys)
        renamed.append(graph)
    return CSIRGraph(
        terms=tuple(x for g in renamed for x in g.terms),
        variables=tuple(x for g in renamed for x in g.variables),
        applications=tuple(x for g in renamed for x in g.applications),
        bindings=tuple(x for g in renamed for x in g.bindings),
        qualifiers=tuple(x for g in renamed for x in g.qualifiers),
        scope_embeddings=tuple(x for g in renamed for x in g.scope_embeddings),
        coordinations=tuple(x for g in renamed for x in g.coordinations),
        proof_links=tuple(x for g in renamed for x in g.proof_links),
        root_refs=tuple(x for g in renamed for x in g.root_refs),
        unresolved_refs=tuple(sorted({x for g in renamed for x in g.unresolved_refs})),
    )


def qualify(
    graph: CSIRGraph,
    *,
    qualifier_ref: str,
    target: CSIRRef,
    qualifier_kind: QualifierKind,
    value_ref: CSIRRef | None = None,
    value_atom=None,
    value_pin: ExactAuthorityPin | None = None,
) -> CSIRGraph:
    qualifier = Qualifier(
        qualifier_ref=qualifier_ref,
        target=target,
        qualifier_kind=qualifier_kind,
        value_ref=value_ref,
        value_atom=value_atom,
        value_pin=value_pin,
    )
    return replace(graph, qualifiers=(*graph.qualifiers, qualifier))


def embed(
    graph: CSIRGraph,
    *,
    embedding_ref: str,
    operator: CSIRRef,
    scoped: CSIRRef,
    scope_kind_pin: ExactAuthorityPin,
    order: int = 0,
) -> CSIRGraph:
    item = ScopeEmbedding(embedding_ref, operator, scoped, scope_kind_pin, order)
    return replace(graph, scope_embeddings=(*graph.scope_embeddings, item))


def project(graph: CSIRGraph, roots: Iterable[CSIRRef]) -> CSIRGraph:
    wanted = set(roots)
    if not wanted:
        return CSIRGraph(unresolved_refs=graph.unresolved_refs)
    binding_by_app = _binding_map(graph)
    coord_by_ref = _coord_map(graph)
    scopes_by_target: dict[CSIRRef, list[ScopeEmbedding]] = {}
    for item in graph.scope_embeddings:
        scopes_by_target.setdefault(item.scoped, []).append(item)
    qualifiers_by_target: dict[CSIRRef, list[Qualifier]] = {}
    for item in graph.qualifiers:
        qualifiers_by_target.setdefault(item.target, []).append(item)

    queue = list(wanted)
    semantic: set[CSIRRef] = set()
    while queue:
        ref = queue.pop()
        if ref in semantic:
            continue
        if graph.node(ref) is None:
            raise KernelOperationError(f"project root/closure contains unknown node:{ref}")
        semantic.add(ref)
        if ref.kind is CSIRNodeKind.APPLICATION:
            for binding in binding_by_app.get(ref.ref, ()):
                queue.extend(binding.fillers)
        elif ref.kind is CSIRNodeKind.COORDINATION:
            queue.extend(coord_by_ref[ref.ref].members)
        for qualifier in qualifiers_by_target.get(ref, ()):
            if qualifier.value_ref is not None:
                queue.append(qualifier.value_ref)
        for scope in scopes_by_target.get(ref, ()):
            queue.append(scope.operator)

    def keep(ref: CSIRRef) -> bool:
        return ref in semantic

    kept_bindings = tuple(
        b for b in graph.bindings
        if keep(CSIRRef(CSIRNodeKind.APPLICATION, b.application_ref))
        and all(keep(f) for f in b.fillers)
    )
    kept_qualifiers = tuple(
        q for q in graph.qualifiers
        if keep(q.target) and (q.value_ref is None or keep(q.value_ref))
    )
    kept_scopes = tuple(s for s in graph.scope_embeddings if keep(s.operator) and keep(s.scoped))
    kept_proofs = tuple(p for p in graph.proof_links if all(keep(s) for s in p.subject_refs))
    kept_proof_refs = {p.proof_ref for p in kept_proofs}
    kept_proofs = tuple(
        replace(p, parent_proof_refs=tuple(x for x in p.parent_proof_refs if x in kept_proof_refs))
        for p in kept_proofs
    )
    return CSIRGraph(
        terms=tuple(x for x in graph.terms if keep(x.node_ref)),
        variables=tuple(x for x in graph.variables if keep(x.node_ref)),
        applications=tuple(x for x in graph.applications if keep(x.node_ref)),
        bindings=kept_bindings,
        qualifiers=kept_qualifiers,
        scope_embeddings=kept_scopes,
        coordinations=tuple(x for x in graph.coordinations if keep(x.node_ref)),
        proof_links=kept_proofs,
        root_refs=tuple(x for x in roots if keep(x)),
        unresolved_refs=graph.unresolved_refs,
    )


def _qualifiers_for(graph: CSIRGraph, target: CSIRRef) -> tuple[Qualifier, ...]:
    return tuple(x for x in graph.qualifiers if x.target == target)


def _scopes_for(graph: CSIRGraph, scoped: CSIRRef) -> tuple[ScopeEmbedding, ...]:
    return tuple(sorted((x for x in graph.scope_embeddings if x.scoped == scoped), key=lambda x: (x.order, x.scope_kind_pin.key)))


def _unify_annotations(
    left_graph: CSIRGraph, left: CSIRRef, right_graph: CSIRGraph, right: CSIRRef,
    substitution: Substitution, seen: set[tuple[CSIRRef, CSIRRef]],
) -> Substitution:
    left_q = _qualifiers_for(left_graph, left); right_q = _qualifiers_for(right_graph, right)
    if len(left_q) != len(right_q):
        raise KernelOperationError("qualifier cardinality differs")
    remaining = list(right_q); current = substitution
    for lq in left_q:
        candidates = [rq for rq in remaining if (rq.qualifier_kind, rq.value_atom, rq.value_pin) == (lq.qualifier_kind, lq.value_atom, lq.value_pin)]
        matched = None
        for rq in candidates:
            try:
                trial = current
                if (lq.value_ref is None) != (rq.value_ref is None):
                    continue
                if lq.value_ref is not None:
                    trial = _unify_ref(left_graph, lq.value_ref, right_graph, rq.value_ref, trial, set(seen))
                matched = (rq, trial); break
            except KernelOperationError:
                continue
        if matched is None:
            raise KernelOperationError("qualifier semantics differ")
        remaining.remove(matched[0]); current = matched[1]

    left_s = _scopes_for(left_graph, left); right_s = _scopes_for(right_graph, right)
    if len(left_s) != len(right_s):
        raise KernelOperationError("scope embedding cardinality differs")
    for ls, rs in zip(left_s, right_s):
        if (ls.order, ls.scope_kind_pin) != (rs.order, rs.scope_kind_pin):
            raise KernelOperationError("scope kind/order differs")
        current = _unify_ref(left_graph, ls.operator, right_graph, rs.operator, current, seen)
    return current


def _unify_ref(
    left_graph: CSIRGraph,
    left: CSIRRef,
    right_graph: CSIRGraph,
    right: CSIRRef,
    substitution: Substitution,
    seen: set[tuple[CSIRRef, CSIRRef]],
) -> Substitution:
    pair = (left, right)
    if pair in seen:
        return substitution
    seen.add(pair)
    if left.kind is CSIRNodeKind.VARIABLE:
        variable = _variable_map(left_graph).get(left.ref)
        if variable is None:
            raise KernelOperationError(f"missing variable:{left.ref}")
        _check_variable_accepts(right_graph, variable, right)
        current = substitution.extend(left.ref, right)
        return _unify_annotations(left_graph, left, right_graph, right, current, seen)
    if right.kind is CSIRNodeKind.VARIABLE:
        # Right-side variables are not stored in the left substitution namespace.
        # Exact symmetric unification requires callers to alpha-rename one graph first.
        raise KernelOperationError("right-side open variable requires prior alpha-renaming/instantiation")
    if left.kind != right.kind:
        raise KernelOperationError("node kinds differ")
    if left.kind is CSIRNodeKind.TERM:
        l = _term_map(left_graph)[left.ref]
        r = _term_map(right_graph)[right.ref]
        if replace(l, term_ref="_") != replace(r, term_ref="_"):
            raise KernelOperationError("term identities/features differ")
        return _unify_annotations(left_graph, left, right_graph, right, substitution, seen)
    if left.kind is CSIRNodeKind.APPLICATION:
        l = _app_map(left_graph)[left.ref]
        r = _app_map(right_graph)[right.ref]
        # Operational profiles authorize/use an application but do not alter denotation.
        # Semantic unification therefore compares the exact predicate definition only;
        # executable-profile compatibility is enforced by the execution-authority envelope.
        if l.predicate_pin != r.predicate_pin:
            raise KernelOperationError("application semantic predicate authority differs")
        lb = _binding_map(left_graph).get(left.ref, ())
        rb = _binding_map(right_graph).get(right.ref, ())
        lmap = {x.port_pin: x for x in lb}; rmap = {x.port_pin: x for x in rb}
        if set(lmap) != set(rmap):
            raise KernelOperationError("application port sets differ")
        current = substitution
        for port in sorted(lmap, key=lambda p: p.key):
            a, b = lmap[port], rmap[port]
            if a.ordered != b.ordered or len(a.fillers) != len(b.fillers):
                raise KernelOperationError("binding cardinality/order differs")
            if a.ordered:
                pairs = zip(a.fillers, b.fillers)
            else:
                # Exact unordered filler matching: bounded brute force by local binding cardinality.
                if len(a.fillers) > 8:
                    raise KernelOperationError("unordered unification budget exceeded")
                matched = None
                from itertools import permutations
                for perm in permutations(b.fillers):
                    try:
                        trial = current
                        trial_seen = set(seen)
                        for lf, rf in zip(a.fillers, perm):
                            trial = _unify_ref(left_graph, lf, right_graph, rf, trial, trial_seen)
                        matched = trial
                        break
                    except KernelOperationError:
                        continue
                if matched is None:
                    raise KernelOperationError("unordered fillers do not unify")
                current = matched
                continue
            for lf, rf in pairs:
                current = _unify_ref(left_graph, lf, right_graph, rf, current, seen)
        return _unify_annotations(left_graph, left, right_graph, right, current, seen)
    if left.kind is CSIRNodeKind.COORDINATION:
        l = _coord_map(left_graph)[left.ref]; r = _coord_map(right_graph)[right.ref]
        if l.coordination_kind_pin != r.coordination_kind_pin or l.ordered != r.ordered or len(l.members) != len(r.members):
            raise KernelOperationError("coordination structure differs")
        current = substitution
        if l.ordered:
            for lf, rf in zip(l.members, r.members):
                current = _unify_ref(left_graph, lf, right_graph, rf, current, seen)
            return _unify_annotations(left_graph, left, right_graph, right, current, seen)
        if len(l.members) > 8:
            raise KernelOperationError("coordination unification budget exceeded")
        from itertools import permutations
        for perm in permutations(r.members):
            try:
                trial = current; trial_seen = set(seen)
                for lf, rf in zip(l.members, perm):
                    trial = _unify_ref(left_graph, lf, right_graph, rf, trial, trial_seen)
                return _unify_annotations(left_graph, left, right_graph, right, trial, trial_seen)
            except KernelOperationError:
                continue
        raise KernelOperationError("coordination members do not unify")
    raise KernelOperationError(f"unsupported unification node kind:{left.kind.value}")


def unify(
    left_graph: CSIRGraph,
    left: CSIRRef,
    right_graph: CSIRGraph,
    right: CSIRRef,
    *,
    initial: Substitution | None = None,
) -> UnificationResult:
    try:
        result = _unify_ref(left_graph, left, right_graph, right, initial or Substitution(), set())
        return UnificationResult(True, result)
    except KernelOperationError as exc:
        return UnificationResult(False, initial or Substitution(), (str(exc),))


def match(pattern: CSIRGraph, target: CSIRGraph) -> MatchResult:
    if len(pattern.root_refs) > len(target.root_refs):
        return MatchResult(False, Substitution(), reason_refs=("target_has_too_few_roots",))
    if len(pattern.root_refs) > 8 or len(target.root_refs) > 10:
        return MatchResult(False, Substitution(), reason_refs=("root_match_budget_exceeded",))
    from itertools import permutations
    for chosen in permutations(target.root_refs, len(pattern.root_refs)):
        substitution = Substitution(); pairs = []
        ok = True
        for left, right in zip(pattern.root_refs, chosen):
            result = unify(pattern, left, target, right, initial=substitution)
            if not result.success:
                ok = False; break
            substitution = result.substitution; pairs.append((left, right))
        if ok:
            return MatchResult(True, substitution, tuple(pairs))
    return MatchResult(False, Substitution(), reason_refs=("no_root_assignment_unifies",))


def compare(left: CSIRGraph, right: CSIRGraph) -> ComparisonAssessment:
    return compare_graphs(left, right)


def _all_local_keys(graph: CSIRGraph) -> set[tuple[str, str]]:
    result = set()
    # Semantic node refs share one local namespace by CSIRGraph invariant.
    for values, attr in (
        (graph.terms, "term_ref"),
        (graph.variables, "variable_ref"),
        (graph.applications, "application_ref"),
        (graph.coordinations, "coordination_ref"),
    ):
        result.update(("semantic", getattr(x, attr)) for x in values)
    for kind, values, attr in (
        ("binding", graph.bindings, "binding_ref"),
        ("qualifier", graph.qualifiers, "qualifier_ref"),
        ("scope", graph.scope_embeddings, "embedding_ref"),
        ("proof", graph.proof_links, "proof_ref"),
    ):
        result.update((kind, getattr(x, attr)) for x in values)
    return result


def _rename_graph(graph: CSIRGraph, prefix: str) -> CSIRGraph:
    semantic_mapping = {}
    for kind, values, attr in (
        (CSIRNodeKind.TERM, graph.terms, "term_ref"),
        (CSIRNodeKind.VARIABLE, graph.variables, "variable_ref"),
        (CSIRNodeKind.APPLICATION, graph.applications, "application_ref"),
        (CSIRNodeKind.COORDINATION, graph.coordinations, "coordination_ref"),
    ):
        for item in values:
            old = getattr(item, attr); semantic_mapping[(kind, old)] = prefix + old
    proof_map = {x.proof_ref: prefix + x.proof_ref for x in graph.proof_links}
    def ref(x: CSIRRef) -> CSIRRef:
        return CSIRRef(x.kind, semantic_mapping[(x.kind, x.ref)])
    return CSIRGraph(
        terms=tuple(replace(x, term_ref=prefix + x.term_ref) for x in graph.terms),
        variables=tuple(replace(x, variable_ref=prefix + x.variable_ref) for x in graph.variables),
        applications=tuple(replace(x, application_ref=prefix + x.application_ref) for x in graph.applications),
        bindings=tuple(replace(x, binding_ref=prefix+x.binding_ref, application_ref=prefix+x.application_ref, fillers=tuple(ref(r) for r in x.fillers)) for x in graph.bindings),
        qualifiers=tuple(replace(x, qualifier_ref=prefix+x.qualifier_ref, target=ref(x.target), value_ref=None if x.value_ref is None else ref(x.value_ref)) for x in graph.qualifiers),
        scope_embeddings=tuple(replace(x, embedding_ref=prefix+x.embedding_ref, operator=ref(x.operator), scoped=ref(x.scoped)) for x in graph.scope_embeddings),
        coordinations=tuple(replace(x, coordination_ref=prefix+x.coordination_ref, members=tuple(ref(r) for r in x.members)) for x in graph.coordinations),
        proof_links=tuple(replace(x, proof_ref=proof_map[x.proof_ref], subject_refs=tuple(ref(r) for r in x.subject_refs), parent_proof_refs=tuple(proof_map[p] for p in x.parent_proof_refs)) for x in graph.proof_links),
        root_refs=tuple(ref(r) for r in graph.root_refs),
        unresolved_refs=graph.unresolved_refs,
    )


__all__ = [
    "KernelOperationError",
    "MatchResult",
    "Substitution",
    "UnificationResult",
    "bind",
    "compare",
    "compose",
    "embed",
    "instantiate",
    "match",
    "normalize",
    "project",
    "qualify",
    "substitute",
    "unify",
]
