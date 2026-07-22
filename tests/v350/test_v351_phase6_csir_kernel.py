from __future__ import annotations

from dataclasses import replace

import pytest

from cemm.v350.csir import (
    CURRENT_KERNEL_ABI,
    CSIRCandidateFragment,
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    CanonicalizationBudgetExceeded,
    Coordination,
    ExactAuthorityPin,
    ExactCSIRCompiler,
    KernelOperation,
    PortBinding,
    ProofLink,
    Qualifier,
    QualifierKind,
    ScopeEmbedding,
    SemanticApplication,
    SemanticTerm,
    SemanticVariable,
    TermKind,
    bind,
    canonicalize,
    compare,
    compose,
    exact_fingerprint,
    match,
    normalize,
    project,
    semantic_fingerprint,
    unify,
)


def pin(kind: str, ref: str, rev: int = 1, content: str | None = None):
    return ExactAuthorityPin(kind, "test", ref, rev, content or f"sha:{kind}:{ref}:{rev}")


def relation_graph(*, app_ref="a", left_ref="x", right_ref="y", variable=False):
    predicate = pin("schema", "relation:likes")
    subject = pin("port", "role:subject")
    obj = pin("port", "role:object")
    person = pin("schema", "type:person")
    left = (
        SemanticVariable(left_ref, required_type_pins=(person,), open_purpose="query")
        if variable
        else SemanticTerm(left_ref, TermKind.REFERENT, identity_ref="person:alice", type_pins=(person,))
    )
    right = SemanticTerm(right_ref, TermKind.REFERENT, identity_ref="thing:mango")
    left_kind = CSIRNodeKind.VARIABLE if variable else CSIRNodeKind.TERM
    return CSIRGraph(
        terms=(right,) if variable else (right, left),
        variables=(left,) if variable else (),
        applications=(SemanticApplication(app_ref, predicate),),
        bindings=(
            PortBinding("b-subj", app_ref, subject, (CSIRRef(left_kind, left_ref),)),
            PortBinding("b-obj", app_ref, obj, (CSIRRef(CSIRNodeKind.TERM, right_ref),)),
        ),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, app_ref),),
    )


def test_serialization_round_trip_is_exact():
    graph = relation_graph()
    assert CSIRGraph.from_primitive(graph.to_primitive()) == graph


def test_alpha_renaming_and_insertion_order_do_not_change_semantic_identity():
    left = relation_graph(app_ref="local-a", left_ref="local-x", right_ref="local-y")
    right = relation_graph(app_ref="renamed", left_ref="alice-node", right_ref="mango-node")
    right = replace(
        right,
        terms=tuple(reversed(right.terms)),
        bindings=tuple(reversed(right.bindings)),
    )
    assert semantic_fingerprint(left) == semantic_fingerprint(right)
    assert compare(left, right).equivalent
    assert normalize(left) == normalize(right)


def test_variable_alpha_renaming_is_invariant_but_constraints_are_not():
    a = relation_graph(variable=True, left_ref="who")
    b = relation_graph(variable=True, left_ref="v17")
    assert semantic_fingerprint(a) == semantic_fingerprint(b)
    changed = replace(
        b,
        variables=(replace(b.variables[0], open_purpose="partial"),),
    )
    assert semantic_fingerprint(a) != semantic_fingerprint(changed)


def test_unordered_coordination_order_is_invariant_and_ordered_is_not():
    kind = pin("schema", "coordination:and")
    x = SemanticTerm("x", TermKind.REFERENT, identity_ref="x")
    y = SemanticTerm("y", TermKind.REFERENT, identity_ref="y")
    one = CSIRGraph(
        terms=(x, y),
        coordinations=(Coordination("c", kind, (x.node_ref, y.node_ref), ordered=False),),
        root_refs=(CSIRRef(CSIRNodeKind.COORDINATION, "c"),),
    )
    two = replace(one, coordinations=(replace(one.coordinations[0], members=(y.node_ref, x.node_ref)),))
    assert semantic_fingerprint(one) == semantic_fingerprint(two)
    ordered_one = replace(one, coordinations=(replace(one.coordinations[0], ordered=True),))
    ordered_two = replace(two, coordinations=(replace(two.coordinations[0], ordered=True),))
    assert semantic_fingerprint(ordered_one) != semantic_fingerprint(ordered_two)


def test_qualifier_and_scope_distinctions_are_semantic():
    graph = relation_graph()
    root = graph.root_refs[0]
    actual = replace(
        graph,
        qualifiers=(Qualifier("q", root, QualifierKind.POLARITY, value_atom="positive"),),
    )
    negative = replace(
        graph,
        qualifiers=(Qualifier("q2", root, QualifierKind.POLARITY, value_atom="negative"),),
    )
    assert semantic_fingerprint(actual) != semantic_fingerprint(negative)

    modal = pin("schema", "scope:modal")
    op = SemanticApplication("modal-op", pin("schema", "operator:possible"))
    scoped = CSIRGraph(
        terms=graph.terms,
        applications=(*graph.applications, op),
        bindings=graph.bindings,
        scope_embeddings=(ScopeEmbedding("s", op.node_ref, root, modal, 0),),
        root_refs=graph.root_refs,
    )
    assert semantic_fingerprint(graph) != semantic_fingerprint(scoped)


def test_proof_lineage_does_not_redefine_semantics_but_exact_identity_tracks_it():
    graph = relation_graph()
    root = graph.root_refs[0]
    one = replace(graph, proof_links=(ProofLink("proof-A", KernelOperation.COMPOSE, (root,), evidence_refs=("e1",)),))
    two = replace(graph, proof_links=(ProofLink("proof-B", KernelOperation.COMPOSE, (root,), evidence_refs=("e2",)),))
    assert semantic_fingerprint(one) == semantic_fingerprint(two)
    assert exact_fingerprint(one) != exact_fingerprint(two)
    # Proof changes cannot renumber semantic nodes in normal form.
    assert replace(normalize(one), proof_links=()) == replace(normalize(two), proof_links=())


def test_exact_authority_revision_or_hash_changes_semantic_identity():
    graph = relation_graph()
    app = graph.applications[0]
    changed_revision = replace(
        graph,
        applications=(replace(app, predicate_pin=replace(app.predicate_pin, revision=2, content_hash="sha:new")),),
    )
    assert semantic_fingerprint(graph) != semantic_fingerprint(changed_revision)


def test_canonicalization_budget_fails_closed_instead_of_using_local_refs():
    terms = tuple(SemanticTerm(f"x{i}", TermKind.LITERAL, literal_value="same") for i in range(4))
    graph = CSIRGraph(terms=terms, root_refs=tuple(x.node_ref for x in terms))
    with pytest.raises(CanonicalizationBudgetExceeded):
        semantic_fingerprint(graph, budget=10)


def test_bind_substitute_unify_and_match_respect_exact_types_and_semantics():
    pattern = relation_graph(variable=True)
    target = relation_graph(variable=False)
    variable = pattern.variables[0]
    alice = next(x for x in target.terms if x.identity_ref == "person:alice")
    # bind() requires the exact filler to exist in the same graph, so compose the
    # grounded target term into the candidate before binding.
    enriched = compose(pattern, CSIRGraph(terms=(alice,)))
    composed_alice = next(x for x in enriched.terms if x.identity_ref == "person:alice")
    bound = bind(enriched, variable.variable_ref, composed_alice.node_ref)
    assert not bound.variables
    result = unify(pattern, pattern.root_refs[0], target, target.root_refs[0])
    assert result.success
    assert result.substitution.get(variable.variable_ref) is not None
    assert match(pattern, target).matched


def test_projection_keeps_semantic_closure_and_drops_unreachable_nodes():
    graph = relation_graph()
    extra = SemanticTerm("unused", TermKind.LITERAL, literal_value="unused")
    expanded = replace(graph, terms=(*graph.terms, extra))
    projected = project(expanded, graph.root_refs)
    assert all(x.term_ref != "unused" for x in projected.terms)
    assert semantic_fingerprint(projected) == semantic_fingerprint(graph)


def test_compiler_rejects_opaque_legacy_input_and_requires_closure_proof_for_application():
    compiler = ExactCSIRCompiler()
    result = compiler.compile_fragments(
        (object(),), authority_generation=1, authority_fingerprint="authority"
    )
    assert not result.candidates
    assert "frontier:csir:opaque-candidate-input" in result.unresolved_refs
    assert "frontier:csir:no-exact-candidate-fragments" in result.unresolved_refs

    result = compiler.compile_fragments(
        (CSIRCandidateFragment("f", relation_graph()),),
        authority_generation=1,
        authority_fingerprint="authority",
    )
    assert not result.candidates
    assert any("missing-exact-definition-closure-proof" in x for x in result.unresolved_refs)


def test_compiler_deduplicates_semantic_classes_and_recomputes_kernel_identity():
    # Deduplication itself is tested without executable applications. Opaque closure-ref
    # strings are no longer authority after Phase 7 and are covered by the rejection test.
    left = CSIRGraph(terms=(SemanticTerm("x", TermKind.LITERAL, literal_value="same"),),
                     root_refs=(CSIRRef(CSIRNodeKind.TERM, "x"),))
    right = CSIRGraph(terms=(SemanticTerm("renamed", TermKind.LITERAL, literal_value="same"),),
                      root_refs=(CSIRRef(CSIRNodeKind.TERM, "renamed"),))
    compiler = ExactCSIRCompiler()
    a = CSIRCandidateFragment("a", left, evidence_refs=("e1",))
    b = CSIRCandidateFragment("b", right, evidence_refs=("e2",))
    result = compiler.compile_fragments((a, b), authority_generation=7, authority_fingerprint="auth7")
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.semantic_fingerprint == semantic_fingerprint(candidate.graph)
    assert candidate.kernel_abi_fingerprint == CURRENT_KERNEL_ABI.fingerprint
    assert candidate.evidence_refs == ("e1", "e2")
    assert candidate.closure_proof_refs == ()
