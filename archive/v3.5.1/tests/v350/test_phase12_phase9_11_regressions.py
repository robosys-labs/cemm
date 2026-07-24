from types import SimpleNamespace

from cemm.v350.conversation.session_memory import SessionBeliefEntry, SessionDiscourseMemory
from cemm.v350.csir.model import CSIRGraph, CSIRNodeKind, CSIRRef, Qualifier, QualifierKind, SemanticTerm, TermKind
from cemm.v350.discourse.context_v351 import semantic_contexts_for_graph
from cemm.v350.epistemic.admission_v351 import EpistemicAdmissionPolicy
from cemm.v350.grounded.model import Claim, Proposition


def test_hypothetical_context_is_not_collapsed_to_actual_before_admission():
    term = SemanticTerm("x", TermKind.REFERENT, identity_ref="r:x")
    graph = CSIRGraph(
        terms=(term,), qualifiers=(Qualifier("q:ctx", term.node_ref, QualifierKind.CONTEXT, value_atom="hypothetical"),),
        root_refs=(term.node_ref,),
    )
    contexts, selected, kind = semantic_contexts_for_graph(
        graph, cycle_context_ref="actual", permission_ref="conversation", evidence_refs=("e:1",),
    )
    assert kind == "hypothetical" and selected != "actual"
    proposition = Proposition("p:1", graph, selected, ("speaker:1",), ("e:1",))
    claim = Claim("c:1", "p:1", "speaker:1", (), "actual", selected, ("e:1",), 1.0)
    klass, decision, _ = EpistemicAdmissionPolicy().classify(
        claim, proposition, permission_ref="conversation", reported_context_kind=kind,
    )
    assert klass.value == "HYPOTHETICAL_ONLY"
    assert decision.value == "preserve_only"


def test_session_belief_recency_is_insertion_order_not_lexical_ref_order():
    memory = SessionDiscourseMemory()
    older = SessionBeliefEntry(
        "belief:z", "p:z", "claim:z", CSIRGraph(), "actual", "conversation",
        ("speaker",), ("e:1",), ("proof:1",), 1.0,
    )
    newer = SessionBeliefEntry(
        "belief:a", "p:a", "claim:a", CSIRGraph(), "actual", "conversation",
        ("speaker",), ("e:2",), ("proof:2",), 1.0,
    )
    from cemm.v350.conversation.session_memory import SessionMemoryCommit
    memory.commit("actual", "conversation", SessionMemoryCommit("commit:1", 0, additions=(older, newer)))
    assert memory.latest_claim_ref("actual", "conversation") == "claim:a"


def test_prior_system_output_is_queryable_without_becoming_world_belief():
    from cemm.v350.conversation.session_memory import OutputMemoryEntry, SessionMemoryCommit
    from cemm.v350.csir.model import (
        ExactAuthorityPin, PortBinding, SemanticApplication, SemanticVariable,
    )
    from cemm.v350.grounded.model import AnswerProjection, Query
    from cemm.v350.query.engine_v351 import GroundedQueryEngineV351

    memory = SessionDiscourseMemory()
    predicate = ExactAuthorityPin("semantic_definition", "test", "meaning:said", 1, "sha:said", "global")
    port = ExactAuthorityPin("semantic_port", "test", "meaning:said:content", 1, "sha:content", "global")
    value = SemanticTerm("value:prior", TermKind.LITERAL, literal_value="previous meaning")
    app = SemanticApplication("app:prior", predicate)
    output_graph = CSIRGraph(
        terms=(value,), applications=(app,),
        bindings=(PortBinding("bind:prior", app.application_ref, port, (value.node_ref,)),),
        root_refs=(app.node_ref,),
    )
    output = OutputMemoryEntry(
        "output:prior", "response:prior", output_graph, "surface:prior",
        "actual", "conversation", ("referent:user",), ("e:out",), 1,
    )
    memory.commit(
        "actual", "conversation",
        SessionMemoryCommit("commit:output", 0, prior_outputs=(output,), evidence_refs=("e:out",)),
    )
    variable = SemanticVariable("answer", open_purpose="query")
    query_app = SemanticApplication("app:query", predicate)
    query_graph = CSIRGraph(
        variables=(variable,), applications=(query_app,),
        bindings=(PortBinding("bind:query", query_app.application_ref, port, (variable.node_ref,)),),
        root_refs=(query_app.node_ref,),
    )
    query = Query(
        "query:prior-output", query_graph, ("gap:prior",),
        AnswerProjection("projection:prior", variable.node_ref),
        "referent:user", ("referent:self",), "actual", ("e:q",),
    )
    cycle = SimpleNamespace(
        context_ref="actual", permission_ref="conversation",
        artifacts={"queries": (query,), "working_belief_delta": None},
    )
    outcome = GroundedQueryEngineV351(memory).query(
        cycle=cycle, capability=None, store=None, effect_store=None, semantic_capabilities=None,
    )
    result = outcome.artifacts["query_results"][0]
    assert result.bindings and result.bindings[0].value_atom == "previous meaning"
    proofs = outcome.artifacts["explanation_proofs"]
    assert any("not-world-belief" in proof.operation_refs for proof in proofs)
    assert not memory.snapshot("actual", "conversation").active_beliefs


def test_stage3_local_grounding_preference_is_not_promoted_to_resolved_identity():
    from cemm.v350.discourse.builder_v351 import DiscourseStructureBuilderV351
    from cemm.v350.grounded.model import IdentityCandidateStatus

    factor = SimpleNamespace(evidence_refs=("e:g",), factor_ref="factor:g", hard=False)
    candidate_a = SimpleNamespace(
        mention_ref="mention:1", target_ref="referent:a", candidate_ref="candidate:a",
        local_score=10.0, provisional=False, factors=(factor,),
    )
    candidate_b = SimpleNamespace(
        mention_ref="mention:1", target_ref="referent:b", candidate_ref="candidate:b",
        local_score=9.0, provisional=False, factors=(factor,),
    )
    mention = SimpleNamespace(
        mention_ref="mention:1", source_ref="source:1", span=SimpleNamespace(start=0, end=3),
        evidence_refs=("e:g",),
    )
    assignment = SimpleNamespace(
        assignment_ref="assignment:local-prior", mention_to_target=(("mention:1", "referent:a"),),
    )
    result = SimpleNamespace(
        ambiguous_mention_refs=(), selected_assignment_ref=assignment.assignment_ref,
        assignments=(assignment,), candidates=(candidate_a, candidate_b), mentions=(mention,),
    )
    grounding = SimpleNamespace(result=result)
    frame = SimpleNamespace(
        system_ref="referent:self", input_speaker_ref="referent:user",
        input_addressee_refs=("referent:self",), response_audience_refs=("referent:user",),
        identity_evidence_refs=("e:participant",), frame_ref="frame:1",
    )
    cycle = SimpleNamespace(
        cycle_ref="cycle:grounding-prior", context_ref="actual", permission_ref="conversation",
        artifacts={"participant_frame": frame, "grounding_candidates": grounding},
    )
    store = SimpleNamespace(get_record=lambda *args, **kwargs: None)
    _contexts, _referents, _mentions, identities, chains, _roles = DiscourseStructureBuilderV351._referent_substrate(cycle, store)
    status = {item.referent_ref: item.status for item in identities}
    assert status["referent:a"] is IdentityCandidateStatus.PROVISIONAL
    assert status["referent:b"] is IdentityCandidateStatus.CANDIDATE
    assert chains[0].resolved_referent_ref is None


def test_unknown_explicit_context_qualifier_fails_closed_as_non_actual():
    term = SemanticTerm("x:unknown-context", TermKind.REFERENT, identity_ref="r:x")
    graph = CSIRGraph(
        terms=(term,), qualifiers=(Qualifier(
            "q:ctx:unknown", term.node_ref, QualifierKind.CONTEXT,
            value_atom="context:external-branch-42",
        ),), root_refs=(term.node_ref,),
    )
    _contexts, selected, kind = semantic_contexts_for_graph(
        graph, cycle_context_ref="actual", permission_ref="conversation", evidence_refs=("e:ctx",),
    )
    assert selected != "actual" and kind == "qualified"
    proposition = Proposition("p:unknown-context", graph, selected, ("speaker:1",), ("e:ctx",))
    claim = Claim("c:unknown-context", proposition.proposition_ref, "speaker:1", (), "actual", selected, ("e:ctx",), 1.0)
    klass, decision, _ = EpistemicAdmissionPolicy().classify(
        claim, proposition, permission_ref="conversation", reported_context_kind=kind,
    )
    assert klass.value == "HYPOTHETICAL_ONLY"
    assert decision.value == "preserve_only"


def test_replacing_existing_reference_identity_advances_recency():
    from cemm.v350.conversation.session_memory import ReferenceSurfaceEntry, SessionMemoryCommit

    memory = SessionDiscourseMemory()
    first = ReferenceSurfaceEntry(
        "ref:name", "referent:user", "Chibu", "chibu", "en", "actual", ("e:1",), 1,
    )
    other = ReferenceSurfaceEntry(
        "ref:other", "referent:other", "Other", "other", "en", "actual", ("e:2",), 2,
    )
    memory.commit("actual", "conversation", SessionMemoryCommit(
        "commit:refs:1", 0, reference_surfaces=(first, other),
    ))
    updated = ReferenceSurfaceEntry(
        "ref:name", "referent:user", "Chibueze", "chibueze", "en", "actual", ("e:3",), 3,
    )
    memory.commit("actual", "conversation", SessionMemoryCommit(
        "commit:refs:2", 1, reference_surfaces=(updated,),
    ))
    snapshot = memory.snapshot("actual", "conversation")
    assert snapshot.reference_surfaces[-1].reference_ref == "ref:name"
    assert memory.reference_surface("actual", "conversation", "referent:user") == "Chibueze"


def test_ambiguous_local_grounding_preference_cannot_become_reusable_reference_surface():
    from cemm.v350.conversation.commit_v351 import SessionMemoryCommitCoordinatorV351

    # Use the actual enum identity to exercise the safety check.
    from cemm.v350.grounding.model import GroundingFactorKind, CandidateOrigin
    factor = SimpleNamespace(factor_kind=GroundingFactorKind.IDENTITY, evidence_refs=("e:id",))
    candidates = (
        SimpleNamespace(mention_ref="mention:amb", target_ref="referent:a", origin=CandidateOrigin.STORE, provisional=False, factors=(factor,)),
        SimpleNamespace(mention_ref="mention:amb", target_ref="referent:b", origin=CandidateOrigin.STORE, provisional=False, factors=(factor,)),
    )
    assignment = SimpleNamespace(
        assignment_ref="assignment:amb", mention_to_target=(("mention:amb", "referent:a"),),
    )
    result = SimpleNamespace(
        selected_assignment_ref=assignment.assignment_ref, assignments=(assignment,), candidates=candidates,
        mentions=(SimpleNamespace(mention_ref="mention:amb", surface="Alex", evidence_refs=("e:id",)),),
    )
    discourse = SimpleNamespace(substrate=SimpleNamespace(mention_chains=(
        SimpleNamespace(mention_refs=("mention:amb",), resolved_referent_ref=None),
    )))
    cycle = SimpleNamespace(
        target_language="en", context_ref="actual",
        artifacts={"grounding_candidates": SimpleNamespace(result=result), "discourse_structures": discourse},
    )
    assert SessionMemoryCommitCoordinatorV351._reference_surfaces(cycle, 1) == ()


def test_partial_meaning_equal_to_existing_attractor_is_not_promoted_to_claim():
    from cemm.v350.conversation.session_memory import SessionDiscourseMemory
    from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351
    from cemm.v350.csir.canonical_v351 import semantic_fingerprint as csir_semantic_fingerprint
    from cemm.v350.discourse.builder_v351 import DiscourseStructureBuilderV351
    from cemm.v350.runtime_abi import ConvergenceAssessment, SemanticAttractor, SemanticAttractorSet

    term = SemanticTerm("partial:value", TermKind.LITERAL, literal_value="known-fragment")
    graph = CSIRGraph(terms=(term,), root_refs=(term.node_ref,), unresolved_refs=("frontier:unknown",))
    fp = csir_semantic_fingerprint(graph)
    attractor = SemanticAttractor("attractor:partial", graph, fp, 1.0, derivation_refs=("d:1",))
    attractors = SemanticAttractorSet(
        "attractors:partial", (attractor,), graph, (),
        ConvergenceAssessment(False, True, 0.0, 0.0, ("partial_unresolved_evidence",)),
        1, "authority:partial", semantic_authority_snapshot_fingerprint="snapshot:partial",
    )
    frame = SimpleNamespace(
        system_ref="referent:self", input_speaker_ref="referent:user",
        input_addressee_refs=("referent:self",), response_audience_refs=("referent:user",),
        identity_evidence_refs=("e:participant",), frame_ref="frame:partial",
    )
    cycle = SimpleNamespace(
        cycle_ref="cycle:partial-attractor", context_ref="actual", permission_ref="conversation",
        artifacts={
            "semantic_attractors": attractors, "semantic_authority_snapshot_v351": AuthoritySnapshotV351(1, "authority:partial"),
            "participant_frame": frame, "evidence_envelopes": (),
        },
    )
    store = SimpleNamespace(get_record=lambda *args, **kwargs: None)
    outcome = DiscourseStructureBuilderV351(SessionDiscourseMemory()).build(
        cycle=cycle, capability=None, store=store, effect_store=None, semantic_capabilities=None,
    )
    assert outcome.artifacts["claims"] == ()
    assert outcome.artifacts["discourse_structures"].clarification_targets


def test_persisted_system_output_anchor_preserves_semantic_response_targets_not_local_root_ids():
    from cemm.v350.conversation.session_memory import OutputMemoryEntry, SessionMemoryCommit

    memory = SessionDiscourseMemory()
    term = SemanticTerm("out:term", TermKind.REFERENT, identity_ref="referent:thing")
    graph = CSIRGraph(terms=(term,), root_refs=(term.node_ref,))
    output = OutputMemoryEntry(
        "output:targeted", "response:targeted", graph, "surface:targeted",
        "actual", "conversation", ("referent:user",), ("e:out",), 1,
        target_refs=("event:target",),
    )
    memory.commit("actual", "conversation", SessionMemoryCommit(
        "commit:targeted-output", 0, prior_outputs=(output,),
    ))
    anchor = memory.system_output_anchors("actual", "conversation")[0]
    assert anchor.target_refs == ("event:target",)
    assert "out:term" not in anchor.target_refs
