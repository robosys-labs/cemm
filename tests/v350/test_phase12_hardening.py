from dataclasses import replace
from types import SimpleNamespace

from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351, DynamicsParameterArtifact
from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.query.model import QueryResult
from cemm.v350.realization.english_v351 import (
    ApplicationFrameSegmentV351,
    compile_english_application_frame,
    compile_english_lexicalization_binding,
    compile_minimum_english_realization_package,
    extend_english_realization_package,
)
from cemm.v350.realization.proof_v351 import ExactRealizationProofVerifier
from cemm.v350.response import (
    ConversationalGoalBridgeV351,
    ConversationalGoalCandidate,
    ConversationalGoalDecision,
    ResponseCorrectionIntent,
    ResponseCSIRBuilderV351,
    ResponseFamily,
    ResponseReportIntent,
    compile_minimum_response_authority,
)
from cemm.v350.runtime_abi import artifact_ref


def _snapshot():
    response = compile_minimum_response_authority()
    english = compile_minimum_english_realization_package()
    dynamics = DynamicsParameterArtifact(
        ExactAuthorityPin("dynamics", "test", "dynamics:baseline", 1, "sha:dynamics", "global"),
        "deterministic-baseline", (("epsilon", 0.0),), ("e:test",),
    )
    return AuthoritySnapshotV351(
        1, "authority:test",
        semantic_definitions=response.semantic_definitions,
        operational_profiles=response.operational_profiles,
        dynamics_parameters=(dynamics,),
        use_authorizations=(*response.use_authorizations, *english.use_authorizations),
        auxiliary_exact_pins=(*english.exact_pins, *response.competence_case_pins),
    ), response, english


def test_partial_query_frontier_selects_clarification_not_fabricated_uncertainty():
    result = QueryResult(
        "result:partial", "query:partial", (), None, (),
        ("frontier:discourse:partial-meaning:abc",),
    )
    cycle = SimpleNamespace(
        cycle_ref="cycle:partial", context_ref="actual", permission_ref="conversation",
        input_payload=SimpleNamespace(response_requested=True),
        artifacts={"query_results": (result,), "claims": ()},
    )
    outcome = ConversationalGoalBridgeV351().arbitrate(
        cycle=cycle, capability=None, store=None, effect_store=None, semantic_capabilities=None,
    )
    decision = outcome.artifacts["goal_decision"]
    assert decision.selected_families == (ResponseFamily.REQUEST_CLARIFICATION,)
    assert "query_requires_clarification" in decision.reason_refs


def test_typed_report_and_correction_intents_make_required_response_families_reachable():
    report = ResponseReportIntent(
        "intent:state", ResponseFamily.REPORT_STATE, "state:1", ("referent:user",),
        ("proof:state",), ("e:state",), 700,
    )
    correction = ResponseCorrectionIntent(
        "intent:correction", "output:1", "state:2", ("proof:correction",), ("e:correction",), 950,
    )
    base = dict(
        cycle_ref="cycle:intents", context_ref="actual", permission_ref="conversation",
        input_payload=SimpleNamespace(response_requested=True),
    )
    report_cycle = SimpleNamespace(**base, artifacts={
        "query_results": (), "claims": (), "response_report_intents": (report,),
    })
    report_outcome = ConversationalGoalBridgeV351().arbitrate(
        cycle=report_cycle, capability=None, store=None, effect_store=None, semantic_capabilities=None,
    )
    assert report_outcome.artifacts["goal_decision"].selected_families == (ResponseFamily.REPORT_STATE,)

    correction_cycle = SimpleNamespace(**base, artifacts={
        "query_results": (), "claims": (), "response_report_intents": (report,),
        "response_correction_intents": (correction,),
    })
    correction_outcome = ConversationalGoalBridgeV351().arbitrate(
        cycle=correction_cycle, capability=None, store=None, effect_store=None, semantic_capabilities=None,
    )
    assert correction_outcome.artifacts["goal_decision"].selected_families == (ResponseFamily.CORRECT_PRIOR_OUTPUT,)


def test_realization_package_identity_changes_when_exact_vocabulary_or_frame_changes():
    package = compile_minimum_english_realization_package()
    semantic_pin = ExactAuthorityPin("semantic_value", "test", "value:blue", 1, "sha:blue", "global")
    lexical = compile_english_lexicalization_binding(semantic_pin, "blue", lexical_category="adjective")
    extended = extend_english_realization_package(package, lexicalizations=(lexical,))
    assert extended.package_pin.content_hash != package.package_pin.content_hash
    assert extended.package_pin.revision == package.package_pin.revision + 1
    assert lexical.lexical_pin in extended.exact_pins

    definition_pin = ExactAuthorityPin("semantic_definition", "test", "relation:likes", 1, "sha:likes", "global")
    subject_port = ExactAuthorityPin("semantic_port", "test", "relation:likes:port:left", 1, "sha:left", "global")
    object_port = ExactAuthorityPin("semantic_port", "test", "relation:likes:port:right", 1, "sha:right", "global")
    frame = compile_english_application_frame(definition_pin, (
        ApplicationFrameSegmentV351("port", subject_port),
        ApplicationFrameSegmentV351("predicate"),
        ApplicationFrameSegmentV351("port", object_port),
    ))
    extended_again = extend_english_realization_package(extended, application_frames=(frame,))
    assert extended_again.package_pin.content_hash != extended.package_pin.content_hash
    assert extended_again.package_pin.revision == extended.package_pin.revision + 1
    assert frame.frame_pin in extended_again.exact_pins


def test_realization_proof_is_bound_to_stage0_authority_generation():
    # Reuse the smallest query-answer path to produce a genuine proof.
    from cemm.v350.query.model import QueryBinding
    from cemm.v350.realization.english_v351 import EnglishCSIRRealizerV351

    snapshot, response, english = _snapshot()
    variable = SimpleNamespace(ref="who", kind=SimpleNamespace(value="variable"))
    binding = QueryBinding(
        "binding:authority", variable, value_atom="Chibu",
        proposition_ref="prop:1", claim_ref="claim:1", confidence=1.0,
    )
    result = QueryResult("result:authority", "query:1", (binding,), None, ("proof:q",))
    goal_candidate = ConversationalGoalCandidate(
        "goal:authority", ResponseFamily.ANSWER_QUERY, ("query:1",), ("result:authority",), ("answer",), 900,
    )
    goal = ConversationalGoalDecision(
        "goal-decision:authority", (goal_candidate,), (goal_candidate.goal_ref,),
        (ResponseFamily.ANSWER_QUERY,), "actual", "conversation", ("answer",),
    )
    cycle = SimpleNamespace(
        cycle_ref="cycle:authority", context_ref="actual", permission_ref="conversation",
        audience_refs=("referent:user",), target_language="en", channel_ref="text",
        input_payload=SimpleNamespace(response_requested=True),
        artifacts={"semantic_authority_snapshot_v351": snapshot, "goal_decision": goal, "query_results": (result,)},
    )
    capability = SimpleNamespace(authority_generation=1, authority_fingerprint="authority:test")
    decision = ResponseCSIRBuilderV351(authority_map=response.authority_map).build(
        cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None,
    ).artifacts["response_decision"]
    cycle.artifacts["response_decision"] = decision
    realized = EnglishCSIRRealizerV351(
        package=english, response_authority_map=response.authority_map, session_memory=None,
    ).realize(cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None)
    candidate = realized["surface_candidates"][0]
    proof = realized["realization_proofs"][0]

    stale_snapshot = AuthoritySnapshotV351(
        2, "authority:next",
        semantic_definitions=snapshot.semantic_definitions,
        operational_profiles=snapshot.operational_profiles,
        dynamics_parameters=snapshot.dynamics_parameters,
        use_authorizations=snapshot.use_authorizations,
        auxiliary_exact_pins=snapshot.auxiliary_exact_pins,
    )
    assessment = ExactRealizationProofVerifier().verify(
        semantic_input=decision, surface=candidate.surface, proof=proof, authority_snapshot=stale_snapshot,
    )
    assert not assessment.passed
    assert "realization_proof_authority_generation_mismatch" in assessment.reason_refs


def test_no_response_required_is_not_blocked_by_unrelated_response_authority():
    response = compile_minimum_response_authority()
    snapshot = AuthoritySnapshotV351(1, "authority:silence")
    goal_candidate = ConversationalGoalCandidate(
        "goal:silence", ResponseFamily.NO_RESPONSE_REQUIRED, (), ("cycle:silence",),
        ("response_not_requested",), 1000,
    )
    goal = ConversationalGoalDecision(
        "goal-decision:silence", (goal_candidate,), (goal_candidate.goal_ref,),
        (ResponseFamily.NO_RESPONSE_REQUIRED,), "actual", "conversation", ("response_not_requested",),
    )
    cycle = SimpleNamespace(
        cycle_ref="cycle:silence", context_ref="actual", permission_ref="conversation",
        audience_refs=("referent:user",),
        artifacts={"semantic_authority_snapshot_v351": snapshot, "goal_decision": goal},
    )
    capability = SimpleNamespace(authority_generation=1, authority_fingerprint="authority:silence")
    outcome = ResponseCSIRBuilderV351(authority_map=response.authority_map).build(
        cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None,
    )
    decision = outcome.artifacts["response_decision"]
    assert decision.family is ResponseFamily.NO_RESPONSE_REQUIRED
    assert not decision.graph.root_refs


def test_selected_answer_family_is_not_blocked_by_inactive_unrelated_response_families():
    response = compile_minimum_response_authority()
    selected = response.authority_map.require(ResponseFamily.ANSWER_QUERY)
    definition = next(item for item in response.semantic_definitions if item.definition_pin.key == selected.definition_pin.key)
    profile = next(item for item in response.operational_profiles if item.definition_pin.key == selected.definition_pin.key)
    authorizations = tuple(item for item in response.use_authorizations if item.target_pin.key == selected.definition_pin.key)
    dynamics = DynamicsParameterArtifact(
        ExactAuthorityPin("dynamics", "test", "dynamics:answer-only", 1, "sha:dynamics:answer", "global"),
        "deterministic-baseline", (("epsilon", 0.0),), ("e:test",),
    )
    snapshot = AuthoritySnapshotV351(
        1, "authority:answer-only", semantic_definitions=(definition,), operational_profiles=(profile,),
        dynamics_parameters=(dynamics,), use_authorizations=authorizations,
        auxiliary_exact_pins=response.competence_case_pins,
    )
    from cemm.v350.query.model import QueryBinding
    binding = QueryBinding(
        "binding:answer-only", SimpleNamespace(ref="x", kind=SimpleNamespace(value="variable")),
        value_atom="known", proposition_ref="p:1", claim_ref="c:1", confidence=1.0,
    )
    result = QueryResult("result:answer-only", "query:1", (binding,), None, ("proof:q",))
    candidate = ConversationalGoalCandidate(
        "goal:answer-only", ResponseFamily.ANSWER_QUERY, ("query:1",), (result.result_ref,), ("answer",), 900,
    )
    goal = ConversationalGoalDecision(
        "goal-decision:answer-only", (candidate,), (candidate.goal_ref,), (ResponseFamily.ANSWER_QUERY,),
        "actual", "conversation", ("answer",),
    )
    cycle = SimpleNamespace(
        cycle_ref="cycle:answer-only", context_ref="actual", permission_ref="conversation",
        audience_refs=("referent:user",),
        artifacts={"semantic_authority_snapshot_v351": snapshot, "goal_decision": goal, "query_results": (result,)},
    )
    capability = SimpleNamespace(authority_generation=1, authority_fingerprint="authority:answer-only")
    outcome = ResponseCSIRBuilderV351(authority_map=response.authority_map).build(
        cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None,
    )
    assert outcome.artifacts["response_decision"].family is ResponseFamily.ANSWER_QUERY


def test_report_realization_fails_closed_when_frozen_session_source_changes():
    from cemm.v350.conversation.session_memory import (
        SessionBeliefEntry, SessionDiscourseMemory, SessionMemoryCommit,
    )
    from cemm.v350.csir.model import CSIRGraph, SemanticTerm, TermKind
    from cemm.v350.realization.english_v351 import EnglishCSIRRealizerV351

    snapshot, response, english = _snapshot()
    memory = SessionDiscourseMemory()
    first_term = SemanticTerm("value:1", TermKind.LITERAL, literal_value="blue")
    first_graph = CSIRGraph(terms=(first_term,), root_refs=(first_term.node_ref,))
    first = SessionBeliefEntry(
        "belief:state:1", "state:1", "claim:state:1", first_graph,
        "actual", "conversation", ("speaker",), ("e:1",), ("proof:1",), 1.0,
    )
    memory.commit("actual", "conversation", SessionMemoryCommit("commit:source:1", 0, additions=(first,)))

    report = ResponseReportIntent(
        "intent:report:source", ResponseFamily.REPORT_STATE, "state:1",
        ("referent:user",), ("proof:1",), ("e:1",), 700,
    )
    goal_candidate = ConversationalGoalCandidate(
        "goal:report:source", ResponseFamily.REPORT_STATE, report.target_refs,
        (report.semantic_ref,), ("semantic_report_intent",), 700,
    )
    goal = ConversationalGoalDecision(
        "goal-decision:report:source", (goal_candidate,), (goal_candidate.goal_ref,),
        (ResponseFamily.REPORT_STATE,), "actual", "conversation", ("semantic_report_intent",),
    )
    cycle = SimpleNamespace(
        cycle_ref="cycle:report-source", context_ref="actual", permission_ref="conversation",
        audience_refs=("referent:user",), target_language="en", channel_ref="text",
        input_payload=SimpleNamespace(response_requested=True),
        artifacts={"semantic_authority_snapshot_v351": snapshot, "goal_decision": goal},
    )
    capability = SimpleNamespace(authority_generation=1, authority_fingerprint="authority:test")
    decision = ResponseCSIRBuilderV351(
        authority_map=response.authority_map, session_memory=memory,
    ).build(cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None).artifacts["response_decision"]
    cycle.artifacts["response_decision"] = decision

    second_term = SemanticTerm("value:2", TermKind.LITERAL, literal_value="red")
    second_graph = CSIRGraph(terms=(second_term,), root_refs=(second_term.node_ref,))
    second = SessionBeliefEntry(
        "belief:state:2", "state:1", "claim:state:2", second_graph,
        "actual", "conversation", ("speaker",), ("e:2",), ("proof:2",), 1.0,
    )
    memory.commit("actual", "conversation", SessionMemoryCommit("commit:source:2", 1, additions=(second,)))

    realized = EnglishCSIRRealizerV351(
        package=english, response_authority_map=response.authority_map, session_memory=memory,
    ).realize(cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None)
    assert not realized["surface_candidates"]
    assert "frontier:realization:reference-or-lexicalization-gap" in realized["frontier_refs"]


def test_observed_semantic_silence_does_not_create_output_or_common_ground_memory():
    from cemm.v350.conversation.session_memory import SessionDiscourseMemory
    from cemm.v350.csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
    from cemm.v350.csir.model import CSIRGraph
    from cemm.v350.output.runtime_v351 import OutputDiscourseCommitterV351
    from cemm.v350.response import ResponseDecision, ResponseSourceBinding
    from cemm.v350.runtime_abi import EmissionObservationArtifact

    memory = SessionDiscourseMemory()
    graph = CSIRGraph()
    decision = ResponseDecision(
        "decision:silence", "candidate:silence", ResponseFamily.NO_RESPONSE_REQUIRED,
        graph, semantic_fingerprint(graph), exact_fingerprint(graph), 1, "authority:silence",
        "semantic-snapshot:silence", (ResponseSourceBinding("cycle:silence", "cycle:silence"),),
        ("referent:user",), "actual", "conversation",
        no_response_reason_ref="no_semantic_response_obligation",
    )
    observation = EmissionObservationArtifact(
        "observation:silence", "no-response:candidate:silence", "",
        ("no_semantic_response_obligation",), "text",
    )
    cycle = SimpleNamespace(
        artifacts={"emission_observation": observation, "response_decision": decision},
        context_ref="actual", permission_ref="conversation", audience_refs=("referent:user",),
    )
    outcome = OutputDiscourseCommitterV351(memory).commit(
        cycle=cycle, capability=None, store=None, effect_store=None, semantic_capabilities=None,
    )
    assert outcome.artifacts["output_discourse_commit"] == ()
    assert outcome.artifacts["common_ground_proposal"] == ()
    snapshot = memory.snapshot("actual", "conversation")
    assert not snapshot.prior_outputs and not snapshot.common_ground


def test_channel_contract_cannot_double_as_disclosure_authority():
    from cemm.v350.learning.model import PinnedRecord
    from cemm.v350.output.runtime_v351 import InProcessTextEmissionEngineV351
    from cemm.v350.storage.model import RecordKind

    channel_pin = PinnedRecord(RecordKind.CHANNEL_ADAPTER_CONTRACT, "channel:text", 1, "fp:channel")
    engine = InProcessTextEmissionEngineV351(channel_contract_pin=channel_pin)
    authorization = engine.authorize(
        cycle=SimpleNamespace(channel_ref="text", input_payload=SimpleNamespace()),
        capability=None, store=SimpleNamespace(), semantic_capabilities=None,
        selected_candidate=SimpleNamespace(surface="hello", language_tag="en", candidate_ref="surface:1"),
        realization_proof=SimpleNamespace(proof_ref="proof:1"),
        semantic_preservation=SimpleNamespace(passed=True, assessment_ref="assessment:1"),
        verification_policy=None, independent_roundtrip=None,
    )
    assert authorization["emission_gate_decision"] == "defer"
    assert "frontier:emission:exact-disclosure-authorization-required" in authorization["frontier_refs"]


def test_typed_disclosure_grant_is_pinned_scoped_and_backed_by_durable_substrate():
    from cemm.v350.learning.model import PinnedRecord
    from cemm.v350.output.authorization_v351 import (
        DisclosureAudienceMode, DisclosureDecision, build_disclosure_authorization_grant_pin,
    )
    from cemm.v350.output.runtime_v351 import InProcessTextEmissionEngineV351
    from cemm.v350.output.model import ChannelAdapterContractRecord
    from cemm.v350.storage.model import RecordKind

    channel_payload = ChannelAdapterContractRecord(
        contract_ref="channel:text", channel_ref="text", adapter_ref="adapter:in-process",
        adapter_revision=1, max_payload_bytes=4096, allowed_language_tags=("en",), active=True,
    )
    channel_pin = PinnedRecord(
        RecordKind.CHANNEL_ADAPTER_CONTRACT, "channel:text", 1, "fp:channel:text"
    )
    policy_pin = PinnedRecord(RecordKind.KNOWLEDGE, "policy:disclosure:conversation", 1, "fp:policy")
    grant = build_disclosure_authorization_grant_pin(
        ref="disclosure:conversation:text", revision=1, namespace="test", scope_ref="global",
        decision=DisclosureDecision.ALLOW, channel_refs=("text",),
        permission_refs=("conversation",), context_refs=("actual",),
        audience_mode=DisclosureAudienceMode.RESPONSE_AUDIENCE,
        language_tags=("en",), substrate_pins=(policy_pin,),
        evidence_refs=("competence:disclosure:text",), active=True,
    )
    snapshot = AuthoritySnapshotV351(
        1, "authority:disclosure", auxiliary_exact_pins=(grant.grant_pin,)
    )

    stored = {
        channel_pin.key: SimpleNamespace(record_fingerprint=channel_pin.record_fingerprint, payload=channel_payload),
        policy_pin.key: SimpleNamespace(record_fingerprint=policy_pin.record_fingerprint, payload=SimpleNamespace()),
    }

    class Store:
        def get_record(self, kind, ref, revision):
            return stored.get((kind.value, ref, revision))

    cycle = SimpleNamespace(
        cycle_ref="cycle:disclosure", channel_ref="text", context_ref="actual",
        permission_ref="conversation", audience_refs=("referent:user",),
        input_payload=SimpleNamespace(),
        artifacts={
            "semantic_authority_snapshot_v351": snapshot,
            "participant_frame": SimpleNamespace(response_audience_refs=("referent:user",)),
        },
    )
    engine = InProcessTextEmissionEngineV351(
        channel_contract_pin=channel_pin, disclosure_authorization_grants=(grant,),
    )
    authorization = engine.authorize(
        cycle=cycle, capability=None, store=Store(), semantic_capabilities=None,
        selected_candidate=SimpleNamespace(surface="hello", language_tag="en", candidate_ref="surface:1"),
        realization_proof=SimpleNamespace(proof_ref="proof:1"),
        semantic_preservation=SimpleNamespace(passed=True, assessment_ref="assessment:1"),
        verification_policy=None, independent_roundtrip=None,
    )
    assert authorization["emission_gate_decision"] == "allow"
    assert authorization["disclosure_gate_passed"] is True
    assert authorization["disclosure_authorization_ref"] == grant.grant_pin.ref
    assert {pin.record_ref for pin in authorization["authorization_pins"]} == {
        channel_pin.record_ref, policy_pin.record_ref,
    }


def test_disclosure_grant_cannot_authorize_audience_outside_response_participants():
    from cemm.v350.learning.model import PinnedRecord
    from cemm.v350.output.authorization_v351 import DisclosureDecision, build_disclosure_authorization_grant_pin
    from cemm.v350.output.runtime_v351 import InProcessTextEmissionEngineV351
    from cemm.v350.output.model import ChannelAdapterContractRecord
    from cemm.v350.storage.model import RecordKind

    channel_payload = ChannelAdapterContractRecord(
        contract_ref="channel:text", channel_ref="text", adapter_ref="adapter:in-process",
        adapter_revision=1, max_payload_bytes=4096, allowed_language_tags=("en",), active=True,
    )
    channel_pin = PinnedRecord(RecordKind.CHANNEL_ADAPTER_CONTRACT, "channel:text", 1, "fp:channel:text")
    policy_pin = PinnedRecord(RecordKind.KNOWLEDGE, "policy:disclosure:conversation", 1, "fp:policy")
    grant = build_disclosure_authorization_grant_pin(
        ref="disclosure:conversation:text", revision=1, namespace="test", scope_ref="global",
        decision=DisclosureDecision.ALLOW, channel_refs=("text",), permission_refs=("conversation",),
        substrate_pins=(policy_pin,), evidence_refs=("competence:disclosure:text",), active=True,
    )
    snapshot = AuthoritySnapshotV351(1, "authority:disclosure", auxiliary_exact_pins=(grant.grant_pin,))
    stored = {
        channel_pin.key: SimpleNamespace(record_fingerprint=channel_pin.record_fingerprint, payload=channel_payload),
        policy_pin.key: SimpleNamespace(record_fingerprint=policy_pin.record_fingerprint, payload=SimpleNamespace()),
    }

    class Store:
        def get_record(self, kind, ref, revision):
            return stored.get((kind.value, ref, revision))

    cycle = SimpleNamespace(
        cycle_ref="cycle:disclosure", channel_ref="text", context_ref="actual",
        permission_ref="conversation", audience_refs=("referent:outsider",), input_payload=SimpleNamespace(),
        artifacts={
            "semantic_authority_snapshot_v351": snapshot,
            "participant_frame": SimpleNamespace(response_audience_refs=("referent:user",)),
        },
    )
    engine = InProcessTextEmissionEngineV351(
        channel_contract_pin=channel_pin, disclosure_authorization_grants=(grant,),
    )
    authorization = engine.authorize(
        cycle=cycle, capability=None, store=Store(), semantic_capabilities=None,
        selected_candidate=SimpleNamespace(surface="hello", language_tag="en", candidate_ref="surface:1"),
        realization_proof=SimpleNamespace(proof_ref="proof:1"),
        semantic_preservation=SimpleNamespace(passed=True, assessment_ref="assessment:1"),
        verification_policy=None, independent_roundtrip=None,
    )
    assert authorization["emission_gate_decision"] == "deny"
    assert "frontier:emission:no-disclosure-authorization-matches-scope" in authorization["frontier_refs"]
