from __future__ import annotations

from types import SimpleNamespace

from cemm.v350.conversation import SessionBeliefEntry, SessionDiscourseMemory, SessionMemoryCommit
from cemm.v350.csir import (
    CSIRGraph, CSIRNodeKind, CSIRRef, ExactAuthorityPin, PortBinding,
    SemanticApplication, SemanticTerm, SemanticVariable, TermKind,
)
from cemm.v350.epistemic import AdmissionClass, EpistemicAdmissionPolicy, EpistemicDecision
from cemm.v350.grounded import AnswerProjection, Claim, Proposition, Query
from cemm.v350.query import GroundedQueryEngineV351
from cemm.v350.storage.model import ClaimRecord
from cemm.v350.grounding.model import ClaimGrounding


PRED = ExactAuthorityPin("semantic_definition", "test", "property:name", 1, "sha:pred")
HOLDER = ExactAuthorityPin("port", "test", "holder", 1, "sha:holder")
VALUE = ExactAuthorityPin("port", "test", "value", 1, "sha:value")


def fact_graph(value: str):
    speaker = SemanticTerm("speaker", TermKind.REFERENT, identity_ref="person:self-user")
    literal = SemanticTerm("value", TermKind.LITERAL, literal_value=value)
    app = SemanticApplication("app", PRED)
    return CSIRGraph(
        terms=(speaker, literal), applications=(app,),
        bindings=(
            PortBinding("b-holder", "app", HOLDER, (speaker.node_ref,)),
            PortBinding("b-value", "app", VALUE, (literal.node_ref,)),
        ),
        root_refs=(app.node_ref,),
    )


def query_graph():
    speaker = SemanticTerm("speaker", TermKind.REFERENT, identity_ref="person:self-user")
    variable = SemanticVariable("answer", allowed_kinds=frozenset({CSIRNodeKind.TERM}), open_purpose="query")
    app = SemanticApplication("app", PRED)
    graph = CSIRGraph(
        terms=(speaker,), variables=(variable,), applications=(app,),
        bindings=(
            PortBinding("b-holder", "app", HOLDER, (speaker.node_ref,)),
            PortBinding("b-value", "app", VALUE, (variable.node_ref,)),
        ),
        root_refs=(app.node_ref,),
    )
    return graph, variable


def test_participant_centered_claim_is_session_scoped_not_global_truth():
    graph = fact_graph("Chibu")
    proposition = Proposition("prop:1", graph, "conversation:1", ("person:self-user",), ("e:1",))
    claim = Claim("claim:1", "prop:1", "person:self-user", ("referent:self",), "conversation:1", "conversation:1", ("e:1",), 1.0)
    klass, decision, _ = EpistemicAdmissionPolicy().classify(
        claim, proposition, permission_ref="conversation"
    )
    assert klass is AdmissionClass.SESSION_PARTICIPANT_FACT
    assert decision is EpistemicDecision.ALLOW


def test_unrelated_third_party_claim_remains_attributed_only():
    graph = fact_graph("Chibu")
    proposition = Proposition("prop:1", graph, "conversation:1", ("person:other",), ("e:1",))
    claim = Claim("claim:1", "prop:1", "person:other", ("referent:self",), "conversation:1", "conversation:1", ("e:1",), 1.0)
    klass, decision, _ = EpistemicAdmissionPolicy().classify(
        claim, proposition, permission_ref="conversation"
    )
    assert klass is AdmissionClass.ATTRIBUTED_ONLY
    assert decision is EpistemicDecision.PRESERVE_ONLY


def _belief(value: str, claim_ref: str):
    graph = fact_graph(value)
    return SessionBeliefEntry(
        belief_ref=f"belief:{claim_ref}", proposition_ref=f"prop:{claim_ref}", claim_ref=claim_ref,
        graph=graph, context_ref="conversation:1", permission_ref="conversation",
        source_refs=("person:self-user",), evidence_refs=(f"e:{claim_ref}",),
        proof_refs=("proof:admission",), confidence=1.0,
    )


def _query():
    graph, variable = query_graph()
    return Query(
        "query:1", graph, ("gap:1",), AnswerProjection("projection:1", variable.node_ref),
        "person:self-user", ("referent:self",), "conversation:1", ("e:q",),
    )


def test_query_returns_semantic_value_and_correction_supersedes_prior_value():
    memory = SessionDiscourseMemory()
    first = _belief("Chibu", "claim:old")
    memory.commit(
        "conversation:1", "conversation",
        SessionMemoryCommit("commit:1", 0, additions=(first,)),
    )
    second = _belief("Chibueze", "claim:new")
    memory.commit(
        "conversation:1", "conversation",
        SessionMemoryCommit(
            "commit:2", 1, additions=(second,),
            supersede_claims=(("claim:old", "claim:new"),),
        ),
    )
    cycle = SimpleNamespace(
        context_ref="conversation:1", permission_ref="conversation",
        artifacts={"queries": (_query(),), "working_belief_delta": None},
    )
    outcome = GroundedQueryEngineV351(memory).query(
        cycle=cycle, capability=SimpleNamespace(), store=None, effect_store=None,
        semantic_capabilities=None,
    )
    result = outcome.artifacts["query_results"][0]
    assert result.answered
    assert len(result.bindings) == 1
    assert result.bindings[0].value_atom == "Chibueze"
    assert result.bindings[0].value_identity_ref is None
    assert result.bindings[0].claim_ref == "claim:new"


def test_same_source_and_reported_context_preserves_attribution_without_forcing_difference():
    record = ClaimRecord(
        "record:1", "occurrence:1", "prop:1", "person:self-user",
        "conversation:1", "conversation:1", 1.0, evidence_refs=("e:1",),
    )
    assert record.source_context_ref == record.reported_context_ref
    grounding = ClaimGrounding(
        "grounding:1", "mention:1", "prop:1", "person:self-user", (),
        "conversation:1", "conversation:1", ("e:1",), 1.0,
    )
    assert grounding.source_context_ref == grounding.reported_context_ref


def test_latest_claim_uses_recency_not_lexical_reference_order():
    memory = SessionDiscourseMemory()
    memory.commit(
        "conversation:1", "conversation",
        SessionMemoryCommit("commit:z", 0, additions=(_belief("first", "claim:z"),)),
    )
    memory.commit(
        "conversation:1", "conversation",
        SessionMemoryCommit("commit:a", 1, additions=(_belief("second", "claim:a"),)),
    )
    assert memory.latest_claim_ref(
        "conversation:1", "conversation", source_ref="person:self-user"
    ) == "claim:a"


def test_unmatched_yes_no_query_is_unknown_not_false_under_open_world_semantics():
    memory = SessionDiscourseMemory()
    restriction = fact_graph("Chibu")
    truth = SemanticVariable(
        "truth", allowed_kinds=frozenset({CSIRNodeKind.TERM}), open_purpose="query"
    )
    graph = CSIRGraph(
        terms=restriction.terms,
        applications=restriction.applications,
        bindings=restriction.bindings,
        variables=(truth,),
        root_refs=(*restriction.root_refs, truth.node_ref),
    )
    query = Query(
        "query:truth", graph, ("gap:truth",),
        AnswerProjection("projection:truth", truth.node_ref),
        "person:self-user", ("referent:self",), "conversation:1", ("e:q",),
    )
    cycle = SimpleNamespace(
        context_ref="conversation:1", permission_ref="conversation",
        artifacts={"queries": (query,), "working_belief_delta": None},
    )
    outcome = GroundedQueryEngineV351(memory).query(
        cycle=cycle, capability=SimpleNamespace(), store=None, effect_store=None,
        semantic_capabilities=None,
    )
    result = outcome.artifacts["query_results"][0]
    assert result.truth_value is None
    assert not result.answered
    assert result.frontier_refs
