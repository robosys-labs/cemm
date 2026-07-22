from __future__ import annotations

import pytest

from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.causal import (
    ActionCandidateV351, CausalLearningEvidenceV351,
    CausalStructureResearcherV351, MechanismHypothesisV351,
)
from cemm.v350.causal.query_v351 import CausalQueryProjectionContractV351
from cemm.v350.learning.inducers_v351 import TransitionCausalInducer
from cemm.v350.learning.phase14_model_v351 import ExactStructuralCandidateSignal, PredictionErrorFamily
from cemm.v350.learning.model import PinnedRecord
from cemm.v350.schema.model import UseAuthorization, UseDecision, UseOperation
from cemm.v350.state import (
    CausalEventV351, MechanismTriggerKind, OperandKind, ParticipantRoleBinding,
    CapabilityDependencyGraph, CapabilityDependencyNodeV351, CapabilityNodeKind,
    CapabilityStateRequirementV351, ConditionOperatorV351, RoleStateTransformV351,
    StateOperandV351, StateTransformExpression, StateTransformOperator,
    TransitionMechanismV351,
)
from cemm.v350.storage.model import RecordKind


def pin(kind, ref): return ExactAuthorityPin(kind, "test", ref, 1, f"sha:{kind}:{ref}", "global")


def mechanism():
    role, dim = pin("semantic_port","affected"), pin("state_dimension","x")
    trigger = pin("semantic_definition","event")
    return TransitionMechanismV351(
        "m:hypothesis", 1, MechanismTriggerKind.EVENT, trigger, (role,),
        deterministic_transforms=(RoleStateTransformV351(
            "t:1", role, dim,
            StateTransformExpression(StateTransformOperator.ADD, (StateOperandV351(OperandKind.CONSTANT, constant=1.0),)),
        ),), competence_case_pins=(pin("competence_case","causal"),), lifecycle_status="candidate",
    ), role, trigger


def test_causal_query_contract_is_exact_semantic_projection_not_question_words():
    contract = CausalQueryProjectionContractV351(pin("query_contract","why"), pin("projection","cause"), "why")
    assert contract.query_kind == "why"
    assert not hasattr(contract, "surface")


def test_causal_research_requires_intervention_support_before_phase14_candidate_signal():
    m, _role, _trigger = mechanism()
    hypothesis = MechanismHypothesisV351(
        "hypothesis:1", m,
        (PinnedRecord(RecordKind.SCHEMA, "schema:dep", 1, "fp:dep"),),
        ("closure:1",), ("lineage:hypothesis",), .1,
    )
    evidence = CausalLearningEvidenceV351(
        "e:1", m.authority_pin, ("var:a",), ("event:a",), "var:b", ("proof-step:1",),
        source_lineage_refs=("lineage:observation",), weight=1.0,
    )
    researcher = CausalStructureResearcherV351(minimum_log_score=-10)
    score = researcher.score(hypothesis, (evidence,), likelihood_ratio=lambda _m,_e: 10.0)
    assert not score.accepted_for_candidate  # association/support without intervention is insufficient
    intervention_evidence = CausalLearningEvidenceV351(
        "e:2", m.authority_pin, ("var:a",), ("event:a",), "var:b", ("proof-step:2",),
        intervention_support_refs=("intervention:1",), source_lineage_refs=("lineage:intervention",), weight=1.0,
    )
    score2 = researcher.score(hypothesis, (intervention_evidence,), likelihood_ratio=lambda _m,_e: 10.0)
    signal = researcher.candidate_signal(
        hypothesis, score2, evidence_refs=("e:2",), competence_case_refs=("case:causal:1",),
        requested_uses=(UseAuthorization(UseOperation.TRANSITION, UseDecision.ALLOW, reason="reviewed causal use"),),
    )
    proposals = TransitionCausalInducer().induce(signal)
    assert len(proposals) == 1
    assert proposals[0].record_kind is RecordKind.TRANSITION_CONTRACT
    assert proposals[0].payload is m


def test_action_candidate_requires_capability_and_planning_authorization_before_causal_planning():
    _m, role, trigger = mechanism()
    event = CausalEventV351(
        "event:plan", trigger, (ParticipantRoleBinding(role,"r:1","app:1"),), "planning:1", "t:0"
    )
    with pytest.raises(ValueError, match="capability proof"):
        ActionCandidateV351(
            "action:1", pin("action","a"), event, capability_proof_refs=(), authorization_refs=("auth:1",)
        )
    with pytest.raises(ValueError, match="planning authorization"):
        ActionCandidateV351(
            "action:1", pin("action","a"), event, capability_proof_refs=("cap:proof",), authorization_refs=()
        )


def test_phase14_accepts_exact_capability_dependency_graph_candidate_not_untyped_payload():
    action = pin("action", "operate")
    holder_type = pin("referent_type", "machine")
    dimension = pin("state_dimension", "ready")
    requirement = CapabilityStateRequirementV351(
        "requirement:ready", dimension, ConditionOperatorV351.KNOWN,
    )
    node = CapabilityDependencyNodeV351(
        "node:ready", CapabilityNodeKind.STATE, state_requirement=requirement,
    )
    graph = CapabilityDependencyGraph(
        "capability-graph:operate", action, (holder_type,), node.node_ref, (node,),
        lifecycle_status="candidate",
        competence_case_pins=(pin("competence_case", "capability-operate"),),
    )
    signal = ExactStructuralCandidateSignal(
        signal_ref="signal:capability-dependency",
        family=PredictionErrorFamily.CAPABILITY_DEPENDENCY,
        record_kind=RecordKind.CAPABILITY_DEPENDENCY,
        payload=graph,
        dependency_pins=(PinnedRecord(RecordKind.SCHEMA, "schema:dep", 1, "fp:dep"),),
        evidence_refs=("e:capability",),
        source_lineage_refs=("lineage:capability",),
        competence_case_refs=("case:capability",),
        requested_uses=(UseAuthorization(UseOperation.TRANSITION, UseDecision.ALLOW),),
        metadata={"intervention_or_mechanism_evidence": True},
    )
    proposals = TransitionCausalInducer().induce(signal)
    assert len(proposals) == 1
    assert proposals[0].record_kind is RecordKind.CAPABILITY_DEPENDENCY
    assert proposals[0].payload is graph
