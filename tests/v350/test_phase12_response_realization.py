from types import SimpleNamespace

from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351, DynamicsParameterArtifact
from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.query.model import QueryBinding, QueryResult
from cemm.v350.response import (
    ConversationalGoalCandidate, ConversationalGoalDecision, ResponseCSIRBuilderV351,
    ResponseFamily, compile_minimum_response_authority,
)
from cemm.v350.realization.english_v351 import EnglishCSIRRealizerV351, compile_minimum_english_realization_package
from cemm.v350.realization.proof_v351 import ExactRealizationProofVerifier


def _snapshot():
    response = compile_minimum_response_authority()
    english = compile_minimum_english_realization_package()
    dynamics = DynamicsParameterArtifact(
        ExactAuthorityPin("dynamics", "test", "dynamics:baseline", 1, "sha:dynamics", "global"),
        "deterministic-baseline", (("epsilon", 0.0),), ("e:test",),
    )
    snapshot = AuthoritySnapshotV351(
        1, "authority:test",
        semantic_definitions=response.semantic_definitions,
        operational_profiles=response.operational_profiles,
        dynamics_parameters=(dynamics,),
        use_authorizations=(*response.use_authorizations, *english.use_authorizations),
        auxiliary_exact_pins=(*english.exact_pins, *response.competence_case_pins),
    )
    return snapshot, response, english


def _cycle(snapshot, goal, result):
    return SimpleNamespace(
        cycle_ref="cycle:1", context_ref="actual", permission_ref="conversation",
        audience_refs=("referent:user",), target_language="en", channel_ref="text",
        input_payload=SimpleNamespace(response_requested=True),
        artifacts={
            "semantic_authority_snapshot_v351": snapshot,
            "goal_decision": goal,
            "query_results": (result,),
        },
    )


def test_answer_query_builds_response_csir_before_surface_and_proves_realization():
    snapshot, response, english = _snapshot()
    binding = QueryBinding(
        "binding:1", SimpleNamespace(ref="who", kind=SimpleNamespace(value="variable")),
        value_atom="Chibu", proposition_ref="prop:1", claim_ref="claim:1", confidence=0.99,
    )
    result = QueryResult("result:1", "query:1", (binding,), None, ("proof:query:1",))
    goal_candidate = ConversationalGoalCandidate(
        "goal:1", ResponseFamily.ANSWER_QUERY, ("query:1",), ("result:1",), ("answer",), 900,
    )
    goal = ConversationalGoalDecision(
        "goal-decision:1", (goal_candidate,), ("goal:1",), (ResponseFamily.ANSWER_QUERY,),
        "actual", "conversation", ("answer",),
    )
    cycle = _cycle(snapshot, goal, result)
    capability = SimpleNamespace(authority_generation=1, authority_fingerprint="authority:test")
    outcome = ResponseCSIRBuilderV351(authority_map=response.authority_map).build(
        cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None,
    )
    decision = outcome.artifacts["response_decision"]
    assert decision.family is ResponseFamily.ANSWER_QUERY
    assert "Chibu" not in decision.decision_ref  # content is semantic, not encoded as a canned response id
    cycle.artifacts["response_decision"] = decision
    realizer = EnglishCSIRRealizerV351(
        package=english, response_authority_map=response.authority_map, session_memory=None,
    )
    realized = realizer.realize(
        cycle=cycle, capability=capability, store=None, effect_store=None, semantic_capabilities=None,
    )
    candidate = realized["surface_candidates"][0]
    proof = realized["realization_proofs"][0]
    # M2 acceptance asserts semantic response/proof, not brittle exact wording.
    assert candidate.surface
    assert any(term.literal_value == "Chibu" for term in decision.graph.terms)
    assessment = ExactRealizationProofVerifier().verify(
        semantic_input=decision, surface=candidate.surface, proof=proof, authority_snapshot=snapshot,
    )
    assert assessment.passed


def test_realization_fails_closed_when_exact_rule_pins_not_in_pinned_generation():
    snapshot, response, english = _snapshot()
    stripped = AuthoritySnapshotV351(
        snapshot.generation, snapshot.authority_fingerprint,
        semantic_definitions=snapshot.semantic_definitions,
        operational_profiles=snapshot.operational_profiles,
        dynamics_parameters=snapshot.dynamics_parameters,
        use_authorizations=response.use_authorizations,
        auxiliary_exact_pins=response.competence_case_pins,
    )
    try:
        english.validate(stripped)
    except Exception:
        pass
    else:
        raise AssertionError("English realization package must not float outside exact authority")


def test_all_required_phase12_response_families_are_explicit():
    assert {item.value for item in ResponseFamily} == {
        "answer_query", "report_state", "report_relation", "report_event",
        "acknowledge_targeted_claim", "request_clarification", "correct_prior_output",
        "qualify_uncertainty", "report_capability", "ask_learning_question",
        "no_response_required",
    }
