from __future__ import annotations

from dataclasses import replace
import pytest

from cemm.v350.csir import (
    CSIRCandidate,
    CSIRCandidateFragment,
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    ExactAuthorityPin,
    ExactCSIRCompiler,
    PortBinding,
    SemanticApplication,
    SemanticTerm,
    SemanticVariable,
    TermKind,
    unify,
)
from cemm.v350.csir.authority_v351 import (
    AuthoritySnapshotV351,
    CausalMechanism,
    CyclicDefinitionClosure,
    DefinitionClosureResolver,
    DefinitionInvocation,
    DynamicsParameterArtifact,
    FormalPort,
    HardConstraintEvaluation,
    HardConstraintTrace,
    MissingExactDependency,
    OperationalProfile,
    SemanticDefinition,
    UseAuthorization,
    SemanticDefinitionCompiler,
)
from cemm.v350.csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
from cemm.v350.csir.authority import CURRENT_KERNEL_ABI
from cemm.v350.runtime_abi import CSIRCandidateSet


def pin(kind: str, ref: str, rev: int = 1, suffix: str = "a"):
    return ExactAuthorityPin(kind, "test", ref, rev, f"sha:{suffix}:{ref}:{rev}")




def executable_snapshot(generation: int, authority: str, *definitions: SemanticDefinition, auxiliary=()):
    profiles = tuple(
        OperationalProfile(
            pin("operational_profile", f"profile:{definition.definition_pin.ref}"),
            definition.definition_pin,
            "active",
            ("compose",),
            ("public",),
        )
        for definition in definitions
    )
    authorizations = tuple(
        UseAuthorization(
            pin("use_authorization", f"allow:{definition.definition_pin.ref}"),
            definition.definition_pin,
            "compose",
            "allow",
            ("global",),
            ("public",),
        )
        for definition in definitions
    )
    dynamics = (
        DynamicsParameterArtifact(
            pin("dynamics_parameter", "dynamics:baseline"),
            "semantic_recurrence",
            (("decay", 0.1), ("inhibition", 0.2)),
        ),
    )
    return AuthoritySnapshotV351(
        generation, authority, semantic_definitions=definitions,
        operational_profiles=profiles, dynamics_parameters=dynamics,
        use_authorizations=authorizations, auxiliary_exact_pins=tuple(auxiliary),
    )

def primitive_relation_graph(def_pin, left_var="left", right_var="right"):
    left_port = pin("port", "role:left")
    right_port = pin("port", "role:right")
    graph = CSIRGraph(
        variables=(SemanticVariable(left_var), SemanticVariable(right_var)),
        applications=(SemanticApplication("app", def_pin),),
        bindings=(
            PortBinding("bl", "app", left_port, (CSIRRef(CSIRNodeKind.VARIABLE, left_var),)),
            PortBinding("br", "app", right_port, (CSIRRef(CSIRNodeKind.VARIABLE, right_var),)),
        ),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "app"),),
    )
    return graph, left_port, right_port


def test_operational_profile_rotation_does_not_change_semantic_identity():
    predicate = pin("semantic_definition", "relation:likes")
    profile1 = pin("operational_profile", "profile:likes", 1, "p1")
    profile2 = pin("operational_profile", "profile:likes", 2, "p2")
    base = CSIRGraph(
        applications=(SemanticApplication("a", predicate, (profile1,)),),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "a"),),
    )
    rotated = replace(base, applications=(replace(base.applications[0], operational_profile_pins=(profile2,)),))
    assert semantic_fingerprint(base) == semantic_fingerprint(rotated)
    assert exact_fingerprint(base) != exact_fingerprint(rotated)


def test_closure_resolver_fails_closed_on_missing_exact_dependency():
    root_pin = pin("semantic_definition", "root")
    missing_pin = pin("semantic_definition", "missing")
    root = SemanticDefinition(
        root_pin,
        CSIRGraph(),
        semantic_dependency_pins=(missing_pin,),
        invocations=(DefinitionInvocation("invoke", missing_pin),),
        expected_semantic_fingerprint="deadbeef",
    )
    snapshot = AuthoritySnapshotV351(1, "authority", semantic_definitions=(root,))
    with pytest.raises(MissingExactDependency):
        DefinitionClosureResolver(snapshot).resolve(root_pin)


def test_exact_compiler_rejects_spoofed_string_closure_proof_and_duck_typed_legacy():
    predicate = pin("semantic_definition", "relation:likes")
    graph, _, _ = primitive_relation_graph(predicate)
    compiler = ExactCSIRCompiler()
    result = compiler.compile_fragments(
        (CSIRCandidateFragment("f", graph, closure_proof_refs=("closure:fake",)),),
        authority_generation=1,
        authority_fingerprint="authority",
    )
    assert not result.candidates
    assert any("missing-exact-definition-closure-proof" in x for x in result.unresolved_refs)

    class LegacyWrapper:
        def to_csir_fragment(self):
            return CSIRCandidateFragment("smuggled", graph)

    result = compiler.compile_fragments(
        (LegacyWrapper(),), authority_generation=1, authority_fingerprint="authority"
    )
    assert not result.candidates
    assert "frontier:csir:opaque-candidate-input" in result.unresolved_refs


def test_definition_compiler_emits_typed_closure_proof_for_primitive_definition():
    predicate = pin("semantic_definition", "relation:likes")
    graph, left_port, right_port = primitive_relation_graph(predicate)
    # Primitive definition has no higher-order deps, so expected fingerprint can be absent.
    definition = SemanticDefinition(
        predicate,
        graph,
        formal_ports=(FormalPort(left_port, "left"), FormalPort(right_port, "right")),
    )
    snapshot = executable_snapshot(7, "auth7", definition)
    alice = SemanticTerm("alice", TermKind.REFERENT, identity_ref="person:alice")
    mango = SemanticTerm("mango", TermKind.REFERENT, identity_ref="thing:mango")
    external = CSIRGraph(
        terms=(alice, mango),
        root_refs=(alice.node_ref, mango.node_ref),
    )
    compiled = SemanticDefinitionCompiler(snapshot).compile(
        predicate,
        external_graph=external,
        arguments={left_port: alice.node_ref, right_port: mango.node_ref},
    )
    compiled.closure_proof.verify(
        compiled.graph, authority_generation=7, authority_fingerprint="auth7",
        authority_snapshot=snapshot,
    )
    fragment = CSIRCandidateFragment(
        "compiled",
        compiled.graph,
        closure_proofs=(compiled.closure_proof,),
    )
    result = ExactCSIRCompiler().compile_fragments(
        (fragment,), authority_generation=7, authority_fingerprint="auth7",
        semantic_authority_snapshot=snapshot,
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].closure_proof_refs == (compiled.closure_proof.proof_ref,)
    assert result.candidates[0].execution_authority_ref
    assert result.candidates[0].dynamics_parameter_pins
    assert result.candidates[0].use_authorization_pins


def test_higher_order_conservativity_is_template_level_not_grounded_instance_level():
    child_pin = pin("semantic_definition", "relation:likes")
    child_graph, child_left, child_right = primitive_relation_graph(child_pin, "cl", "cr")
    child = SemanticDefinition(
        child_pin,
        child_graph,
        formal_ports=(FormalPort(child_left, "cl"), FormalPort(child_right, "cr")),
    )

    root_pin = pin("semantic_definition", "operator:not-likes")
    root_left = pin("port", "role:left")
    root_right = pin("port", "role:right")
    root_graph = CSIRGraph(
        variables=(SemanticVariable("rl"), SemanticVariable("rr")),
        applications=(SemanticApplication("root-app", root_pin),),
        bindings=(
            PortBinding("rbl", "root-app", root_left, (CSIRRef(CSIRNodeKind.VARIABLE, "rl"),)),
            PortBinding("rbr", "root-app", root_right, (CSIRRef(CSIRNodeKind.VARIABLE, "rr"),)),
        ),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "root-app"),),
    )
    provisional_root = SemanticDefinition(
        root_pin,
        root_graph,
        formal_ports=(FormalPort(root_left, "rl"), FormalPort(root_right, "rr")),
        semantic_dependency_pins=(child_pin,),
        invocations=(
            DefinitionInvocation(
                "invoke:likes",
                child_pin,
                (
                    (child_left, CSIRRef(CSIRNodeKind.VARIABLE, "rl")),
                    (child_right, CSIRRef(CSIRNodeKind.VARIABLE, "rr")),
                ),
            ),
        ),
        executable=False,
    )
    provisional_snapshot = AuthoritySnapshotV351(
        9, "auth9", semantic_definitions=(child, provisional_root)
    )
    expected_template_fp = semantic_fingerprint(
        SemanticDefinitionCompiler(provisional_snapshot).expanded_template(root_pin)
    )
    root = replace(
        provisional_root,
        executable=True,
        expected_semantic_fingerprint=expected_template_fp,
    )
    snapshot = AuthoritySnapshotV351(9, "auth9", semantic_definitions=(child, root))

    alice = SemanticTerm("alice-ground", TermKind.REFERENT, identity_ref="person:alice")
    mango = SemanticTerm("mango-ground", TermKind.REFERENT, identity_ref="thing:mango")
    compiled = SemanticDefinitionCompiler(snapshot).compile(
        root_pin,
        external_graph=CSIRGraph(terms=(alice, mango)),
        arguments={root_left: alice.node_ref, root_right: mango.node_ref},
    )
    # Grounded occurrence identity necessarily changes the concrete candidate fingerprint,
    # but it must not invalidate definition-level conservativity.
    assert compiled.closure_proof.expanded_template_semantic_fingerprint == expected_template_fp
    assert compiled.closure_proof.conservative


def test_semantic_definition_rejects_bundled_operational_profile_authority():
    predicate = pin("semantic_definition", "relation:profile-bundled")
    profile = pin("operational_profile", "profile:bad")
    graph = CSIRGraph(
        applications=(SemanticApplication("a", predicate, (profile,)),),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "a"),),
    )
    with pytest.raises(ValueError):
        SemanticDefinition(predicate, graph)


def test_exact_constraint_closure_requires_typed_satisfied_trace():
    predicate = pin("semantic_definition", "relation:constrained")
    constraint = pin("constraint", "constraint:holder-compatible")
    graph, left_port, right_port = primitive_relation_graph(predicate)
    definition = SemanticDefinition(
        predicate,
        graph,
        formal_ports=(FormalPort(left_port, "left"), FormalPort(right_port, "right")),
        constraint_pins=(constraint,),
    )
    snapshot = executable_snapshot(11, "auth11", definition, auxiliary=(constraint,))
    alice = SemanticTerm("alice-c", TermKind.REFERENT, identity_ref="person:alice")
    mango = SemanticTerm("mango-c", TermKind.REFERENT, identity_ref="thing:mango")
    compiled = SemanticDefinitionCompiler(snapshot).compile(
        predicate,
        external_graph=CSIRGraph(terms=(alice, mango)),
        arguments={left_port: alice.node_ref, right_port: mango.node_ref},
    )
    fragment_without_trace = CSIRCandidateFragment(
        "constrained", compiled.graph, closure_proofs=(compiled.closure_proof,)
    )
    blocked = ExactCSIRCompiler().compile_fragments(
        (fragment_without_trace,),
        authority_generation=11,
        authority_fingerprint="auth11",
        semantic_authority_snapshot=snapshot,
    )
    assert not blocked.candidates
    assert any("missing-hard-constraint-trace" in ref for ref in blocked.unresolved_refs)

    trace = HardConstraintTrace(
        authority_generation=11,
        authority_fingerprint="auth11",
        semantic_authority_snapshot_fingerprint=snapshot.snapshot_fingerprint,
        graph_structural_exact_fingerprint=compiled.closure_proof.compiled_structural_exact_fingerprint,
        evaluations=(HardConstraintEvaluation(constraint, True, ("evidence:constraint",)),),
    )
    accepted = ExactCSIRCompiler().compile_fragments(
        (
            CSIRCandidateFragment(
                "constrained",
                compiled.graph,
                closure_proofs=(compiled.closure_proof,),
                hard_constraint_traces=(trace,),
            ),
        ),
        authority_generation=11,
        authority_fingerprint="auth11",
        semantic_authority_snapshot=snapshot,
    )
    assert len(accepted.candidates) == 1
    assert accepted.candidates[0].hard_constraint_trace_refs == (trace.trace_ref,)


def test_semantic_unification_ignores_operational_profile_rotation():
    predicate = pin("semantic_definition", "relation:likes-unify")
    profile1 = pin("operational_profile", "profile:likes-unify", 1, "p1")
    profile2 = pin("operational_profile", "profile:likes-unify", 2, "p2")
    left = CSIRGraph(
        applications=(SemanticApplication("left", predicate, (profile1,)),),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "left"),),
    )
    right = CSIRGraph(
        applications=(SemanticApplication("right", predicate, (profile2,)),),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "right"),),
    )
    assert semantic_fingerprint(left) == semantic_fingerprint(right)
    assert unify(left, left.root_refs[0], right, right.root_refs[0]).success


def test_candidate_set_rejects_forged_exact_graph_fingerprint():
    graph = CSIRGraph(
        terms=(SemanticTerm("t", TermKind.LITERAL, literal_value="x"),),
        root_refs=(CSIRRef(CSIRNodeKind.TERM, "t"),),
    )
    candidate = CSIRCandidate(
        "candidate:forged", graph, semantic_fingerprint(graph), "forged",
        1, "authority", CURRENT_KERNEL_ABI.fingerprint,
    )
    with pytest.raises(ValueError, match="exact fingerprint"):
        CSIRCandidateSet(
            "set:forged", (candidate,), 1, "authority", CURRENT_KERNEL_ABI.fingerprint, (), ()
        )


def test_execution_authority_auto_pins_profile_policy_and_matching_causal_mechanism():
    predicate = pin("semantic_definition", "event:generic")
    graph, left_port, right_port = primitive_relation_graph(predicate)
    definition = SemanticDefinition(
        predicate, graph,
        formal_ports=(FormalPort(left_port, "left"), FormalPort(right_port, "right")),
    )
    policy = pin("policy", "policy:generic")
    profile = OperationalProfile(
        pin("operational_profile", "profile:event-generic"), predicate, "active",
        ("compose",), ("public",), policy_pins=(policy,),
    )
    authorization = UseAuthorization(
        pin("use_authorization", "allow:event-generic"), predicate, "compose", "allow",
        ("global",), ("public",),
    )
    dynamics = DynamicsParameterArtifact(
        pin("dynamics_parameter", "dyn:event"), "semantic_recurrence", (("decay", 0.1),)
    )
    mechanism = CausalMechanism(pin("causal_mechanism", "causal:event-generic"), predicate)
    snapshot = AuthoritySnapshotV351(
        12, "auth12", (definition,), (profile,), (dynamics,), (), (mechanism,),
        (authorization,), (policy,),
    )
    bound, envelope = snapshot.bind_execution_authority(
        graph, operation="compose", context_ref="global", permission_ref="public"
    )
    assert bound.applications[0].operational_profile_pins == (profile.profile_pin,)
    assert envelope.policy_adapter_pins == (policy,)
    assert envelope.causal_mechanism_pins == (mechanism.mechanism_pin,)
    envelope.verify(bound, snapshot)


def test_prepinned_profile_cannot_bypass_unique_exact_profile_selection():
    predicate = pin("semantic_definition", "relation:profile-selection")
    graph, left_port, right_port = primitive_relation_graph(predicate)
    definition = SemanticDefinition(
        predicate, graph,
        formal_ports=(FormalPort(left_port, "left"), FormalPort(right_port, "right")),
    )
    p1 = OperationalProfile(
        pin("operational_profile", "profile:one"), predicate, "active", ("compose",), ("public",)
    )
    p2 = OperationalProfile(
        pin("operational_profile", "profile:two"), predicate, "active", ("compose",), ("public",)
    )
    auth = UseAuthorization(
        pin("use_authorization", "allow:profile-selection"), predicate,
        "compose", "allow", ("global",), ("public",),
    )
    dynamics = DynamicsParameterArtifact(
        pin("dynamics_parameter", "dyn:profile-selection"),
        "semantic_recurrence", (("decay", 0.1),),
    )
    snapshot = AuthoritySnapshotV351(
        13, "auth13", (definition,), (p1, p2), (dynamics,), (), (), (auth,), ()
    )
    pinned_graph = replace(
        graph,
        applications=(replace(graph.applications[0], operational_profile_pins=(p1.profile_pin,)),),
    )
    with pytest.raises(ValueError, match="requires one active profile"):
        snapshot.bind_execution_authority(
            pinned_graph, operation="compose", context_ref="global", permission_ref="public"
        )


def test_stage5_projection_authority_requirement_is_owned_by_compiler_boundary():
    predicate = pin("semantic_definition", "relation:projection-required")
    graph, left_port, right_port = primitive_relation_graph(predicate)
    definition = SemanticDefinition(
        predicate, graph,
        formal_ports=(
            FormalPort(left_port, "left", minimum=0),
            FormalPort(right_port, "right", minimum=0),
        ),
    )
    projection = pin("language_package", "language-pack:en")
    snapshot = executable_snapshot(14, "auth14", definition, auxiliary=(projection,))
    compiled = SemanticDefinitionCompiler(snapshot).compile(predicate)

    missing = ExactCSIRCompiler().compile_fragments(
        (CSIRCandidateFragment("missing-projection", compiled.graph,
                               closure_proofs=(compiled.closure_proof,)),),
        authority_generation=14,
        authority_fingerprint="auth14",
        semantic_authority_snapshot=snapshot,
        require_projection_authority=True,
    )
    assert not missing.candidates
    assert any("invalid-execution-authority" in ref for ref in missing.unresolved_refs)

    accepted = ExactCSIRCompiler().compile_fragments(
        (CSIRCandidateFragment(
            "with-projection", compiled.graph,
            closure_proofs=(compiled.closure_proof,),
            projection_authority_pins=(projection,),
        ),),
        authority_generation=14,
        authority_fingerprint="auth14",
        semantic_authority_snapshot=snapshot,
        require_projection_authority=True,
    )
    assert len(accepted.candidates) == 1
    assert accepted.candidates[0].projection_authority_required
    assert accepted.candidates[0].projection_authority_pins == (projection,)


def test_exact_non_definition_semantic_dependency_is_closure_leaf_not_recursive_definition():
    predicate = pin("semantic_definition", "property:color")
    value_type = pin("referent_type", "type:color-value")
    graph = CSIRGraph(
        applications=(SemanticApplication("a", predicate),),
        root_refs=(CSIRRef(CSIRNodeKind.APPLICATION, "a"),),
    )
    definition = SemanticDefinition(
        predicate,
        graph,
        semantic_dependency_pins=(value_type,),
    )
    snapshot = AuthoritySnapshotV351(
        15, "auth15", semantic_definitions=(definition,), auxiliary_exact_pins=(value_type,)
    )
    closure = DefinitionClosureResolver(snapshot).resolve(predicate)
    assert closure.pins == (value_type, predicate)
    assert closure.dependency_edges == ((predicate, value_type),)
