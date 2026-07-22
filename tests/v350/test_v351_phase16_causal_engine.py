from __future__ import annotations

import pytest

from cemm.v350.csir.model import CSIRGraph, ExactAuthorityPin, SemanticTerm, TermKind
from cemm.v350.schema.model import UseOperation
from cemm.v350.causal import (
    CausalPropagationEngine, CausalVariable, ContextSemantics, CounterfactualContext,
    ExogenousAssumptionV351, InterventionAssignmentV351, InterventionContext,
)
from cemm.v350.state import (
    CausalEventV351, ConditionOperatorV351, MechanismTriggerKind, OperandKind, ParticipantRoleBinding,
    RoleStateTransformV351, StateDomainContractV351, StateDomainKind, StateKeyV351,
    StateOperandV351, StateSnapshotV351, StateTransformExpression, StateTransformOperator,
    StateDeltaV351, StateValueV351, TransitionMechanismV351,
)


def pin(kind, ref): return ExactAuthorityPin(kind, "test", ref, 1, f"sha:{kind}:{ref}", "global")


def substrate():
    role = pin("semantic_port", "affected")
    d1, d2 = pin("state_dimension", "x"), pin("state_dimension", "y")
    trigger = pin("semantic_definition", "trigger")
    competence = pin("competence_case", "m")
    m1 = TransitionMechanismV351(
        "mechanism:direct", 1, MechanismTriggerKind.EVENT, trigger, (role,),
        deterministic_transforms=(RoleStateTransformV351(
            "t:x", role, d1, StateTransformExpression(
                StateTransformOperator.ADD, (StateOperandV351(OperandKind.CONSTANT, constant=1.0),)
            ),
        ),), competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    )
    m2 = TransitionMechanismV351(
        "mechanism:secondary", 1, MechanismTriggerKind.STATE_CHANGE, None, (role,),
        source_dimension_pins=(d1,), deterministic_transforms=(RoleStateTransformV351(
            "t:y", role, d2, StateTransformExpression(
                StateTransformOperator.ADD, (StateOperandV351(OperandKind.CONSTANT, constant=10.0),)
            ),
        ),), competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    )
    snapshot = StateSnapshotV351(
        (
            (StateKeyV351("r:1", d1, "actual"), StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=0)),
            (StateKeyV351("r:1", d2, "actual"), StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=0)),
        ),
        ((d1.key, StateDomainContractV351("x",1,StateDomainKind.CONTINUOUS)), (d2.key, StateDomainContractV351("y",1,StateDomainKind.CONTINUOUS))),
    )
    event = CausalEventV351(
        "event:root", trigger, (ParticipantRoleBinding(role,"r:1","app:1"),), "actual", "t:0"
    )
    return (m1,m2), snapshot, event, d1, d2


def test_cross_dimensional_consequence_reuses_same_bounded_causal_proof_graph():
    mechanisms, snapshot, event, d1, d2 = substrate()
    result = CausalPropagationEngine(mechanisms=mechanisms).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.ACTUAL,
    )
    assert len(result.branches) == 1
    assert [d.new_value.scalar_value for d in result.branches[0].state_deltas] == [1, 10]
    proof = result.causal_proofs[0]
    assert len(proof.steps) == 2
    assert proof.steps[1].parent_step_refs == (proof.steps[0].step_ref,)
    learning = CausalPropagationEngine.learning_evidence(result)
    assert {item.mechanism_pin.ref for item in learning} == {"mechanism:direct", "mechanism:secondary"}


def test_do_intervention_cuts_incoming_effect_and_never_mutates_actual_snapshot():
    mechanisms, snapshot, event, d1, _d2 = substrate()
    variable = CausalVariable("var:x", "r:1", d1, "cf", 1)
    intervention = InterventionContext(
        "cf", "actual",
        (InterventionAssignmentV351(
            variable, StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=99),
            (pin("intervention_authorization", "do-x"),),
            (ParticipantRoleBinding(pin("semantic_port", "affected"), "r:1", "intervention:1"),),
        ),),
    )
    result = CausalPropagationEngine(mechanisms=mechanisms).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.INTERVENTION,
        intervention=intervention,
    )
    assert result.actual_state_unchanged
    assert not any("intervention-cut" in ref for ref in result.frontier_refs)
    cut_steps = [
        step for proof in result.causal_proofs for step in proof.steps if step.intervention_cut
    ]
    assert cut_steps and all(step.suppressed_delta_ref for step in cut_steps)
    # do(X=99) is itself reified as a state-change root, so downstream X->Y mechanics still fire.
    assert any(
        delta.dimension_pin.ref == "y" and delta.new_value.scalar_value == 10
        for branch in result.branches for delta in branch.state_deltas
    )
    # A structural edge cut is explanatory proof, not positive evidence that the cut mechanism failed.
    assert all(
        item.mechanism_pin.key != cut_steps[0].mechanism_pin.key
        for item in CausalPropagationEngine.learning_evidence(result)
    )
    assert snapshot.value("r:1", d1, "actual").scalar_value == 0


def test_intervention_requires_exact_authorization_before_do_assignment_exists():
    _mechanisms, _snapshot, _event, d1, _d2 = substrate()
    variable = CausalVariable("var:x:unauthorized", "r:1", d1, "cf:unauthorized", 1)
    with pytest.raises(ValueError, match="authorization"):
        InterventionAssignmentV351(
            variable, StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=4), ()
        )


def test_counterfactual_requires_abduction_or_explicit_exogenous_assumptions():
    mechanisms, snapshot, event, d1, _ = substrate()
    variable = CausalVariable("var:x", "r:1", d1, "cf", 1)
    intervention = InterventionContext(
        "cf", "actual",
        (InterventionAssignmentV351(
            variable, StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=5),
            (pin("intervention_authorization", "do-x"),),
            (ParticipantRoleBinding(pin("semantic_port", "affected"), "r:1", "intervention:2"),),
        ),),
    )
    unresolved = CounterfactualContext("cf", "actual", intervention, ("e:factual",), (), (variable.variable_ref,))
    r1 = CausalPropagationEngine(mechanisms=mechanisms).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.COUNTERFACTUAL,
        counterfactual=unresolved,
    )
    assert r1.branches == ()
    assert "frontier:causal:counterfactual-abduction-unresolved" in r1.frontier_refs
    resolved = CounterfactualContext(
        "cf", "actual", intervention, ("e:factual",),
        (ExogenousAssumptionV351("u:x", variable, StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=0), 1.0),),
        (variable.variable_ref,),
    )
    r2 = CausalPropagationEngine(mechanisms=mechanisms).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.COUNTERFACTUAL,
        counterfactual=resolved,
    )
    assert r2.context_semantics is ContextSemantics.COUNTERFACTUAL


def test_pruned_stochastic_mass_remains_unresolved_not_renormalized():
    from cemm.v350.causal import SimulationBudgetV351
    from cemm.v350.state import MechanismBranchV351

    role = pin("semantic_port", "affected:stochastic")
    dimension = pin("state_dimension", "stochastic-x")
    trigger = pin("semantic_definition", "stochastic-trigger")
    competence = pin("competence_case", "stochastic")
    def transform(ref, amount):
        return RoleStateTransformV351(
            ref, role, dimension,
            StateTransformExpression(
                StateTransformOperator.ADD,
                (StateOperandV351(OperandKind.CONSTANT, constant=amount),),
            ),
        )
    mechanism = TransitionMechanismV351(
        "mechanism:stochastic", 1, MechanismTriggerKind.EVENT, trigger, (role,),
        branches=(
            MechanismBranchV351("likely", .9, (transform("t:likely", 1.0),)),
            MechanismBranchV351("rare", .1, (transform("t:rare", 100.0),)),
        ),
        competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    )
    snapshot = StateSnapshotV351(
        ((StateKeyV351("r:s", dimension, "actual"), StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=0)),),
        ((dimension.key, StateDomainContractV351("stochastic-x", 1, StateDomainKind.CONTINUOUS)),),
    )
    event = CausalEventV351(
        "event:stochastic", trigger,
        (ParticipantRoleBinding(role, "r:s", "app:stochastic"),), "actual", "t:0",
    )
    result = CausalPropagationEngine(
        mechanisms=(mechanism,),
        budget=SimulationBudgetV351(minimum_branch_probability=.2),
    ).simulate(initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.ACTUAL)
    assert len(result.branches) == 1
    assert result.branches[0].probability == .9
    assert abs(result.unresolved_probability_mass - .1) < 1e-9
    assert any("minimum-branch-probability-pruned" in ref for ref in result.frontier_refs)


def test_causal_proof_codec_roundtrip_preserves_exact_state_and_mechanism_lineage():
    from cemm.v350.causal.codec_v351 import causal_proof_from_document, causal_proof_to_document

    mechanisms, snapshot, event, _d1, _d2 = substrate()
    result = CausalPropagationEngine(mechanisms=mechanisms).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.ACTUAL,
    )
    proof = result.causal_proofs[0]
    restored = causal_proof_from_document(causal_proof_to_document(proof))
    assert restored == proof
    assert all(step.new_value_ref for step in restored.steps if step.delta_ref)


def test_effect_of_query_traverses_proof_forward_not_as_a_reverse_why_query():
    from cemm.v350.causal import CausalQueryRequestV351, ExplanationExtractor

    mechanisms, snapshot, event, _d1, _d2 = substrate()
    simulation = CausalPropagationEngine(mechanisms=mechanisms).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.ACTUAL,
    )
    proof = simulation.causal_proofs[0]
    source = proof.steps[1].source_variable_refs[0]
    expected_effect = proof.steps[1].target_variable_ref
    request = CausalQueryRequestV351(
        "query:effect-of", source, "effect_of", source_variable_ref=source,
    )
    # Causal proof alone is not sufficient for a user-facing semantic answer. The exact
    # source/effect semantic projection must also exist; internal causal refs never leak.
    unresolved = ExplanationExtractor().answer(request, simulation)
    assert not unresolved.answered
    assert "frontier:causal:explanation-semantic-surface-projection" in unresolved.frontier_refs

    def graph(label):
        term = SemanticTerm(
            term_ref="term:" + label.replace(":", "-"),
            term_kind=TermKind.LITERAL,
            literal_value=label,
        )
        return CSIRGraph(terms=(term,), root_refs=(term.node_ref,))

    result = ExplanationExtractor().answer(
        request, simulation, semantic_graphs={source: graph("cause"), expected_effect: graph("effect")},
    )
    assert result.answered
    assert not result.frontier_refs
    assert result.explanation.target_variable_ref == expected_effect
    assert result.explanation.cause_variable_refs == (source,)


def test_stage13_materializes_only_final_delta_per_exact_state_variable():
    from cemm.v350.causal.commit_v351 import CausalStateCommitterV351

    dimension = pin("state_dimension", "collapse")
    mechanism_pin = pin("causal_mechanism", "collapse")
    def delta(ref, value, step):
        return StateDeltaV351(
            delta_ref=ref, holder_ref="r:collapse", dimension_pin=dimension,
            prior_value=StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=value - 1),
            new_value=StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=value),
            transform_ref="t:collapse", mechanism_pin=mechanism_pin, context_ref="actual",
            effective_time_ref=f"t:{step}", confidence=1.0, time_step=step,
        )
    first = delta("delta:first", 1, 1)
    second = delta("delta:second", 2, 2)
    same_step_later = delta("delta:same-step-later", 3, 2)
    selected = CausalStateCommitterV351.final_state_deltas((first, second, same_step_later))
    assert selected == (same_step_later,)


def test_nonactual_impacts_do_not_become_actual_goal_pressure():
    from cemm.v350.causal import CausalImpactEngineV351, ContextSemantics, goals_from_impact

    mechanisms, snapshot, event, _d1, _d2 = substrate()
    simulation = CausalPropagationEngine(mechanisms=mechanisms).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.PLANNING,
    )
    impacts = CausalImpactEngineV351().derive(simulation)
    assert impacts
    assert all(item.context_semantics is ContextSemantics.PLANNING for item in impacts)
    assert goals_from_impact(impacts) == ()


def test_long_delay_is_time_horizon_not_causal_depth():
    from cemm.v350.causal import SimulationBudgetV351
    from cemm.v350.state import SecondaryEventTemplateV351

    role = pin("semantic_port", "delay-role")
    trigger = pin("semantic_definition", "delay-trigger")
    secondary = pin("semantic_definition", "delay-secondary")
    competence = pin("competence_case", "delay-case")
    mechanism = TransitionMechanismV351(
        "mechanism:delay", 1, MechanismTriggerKind.EVENT, trigger, (role,),
        deterministic_secondary_events=(SecondaryEventTemplateV351(
            "secondary:delay", secondary, ((role, role),), delay_steps=100,
        ),),
        competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    )
    event = CausalEventV351(
        "event:delay", trigger, (ParticipantRoleBinding(role, "r:delay", "app:delay"),),
        "actual", "t:0",
    )
    result = CausalPropagationEngine(
        mechanisms=(mechanism,),
        budget=SimulationBudgetV351(maximum_depth=2, maximum_time_step=200),
    ).simulate(
        initial_state=StateSnapshotV351((), ()), root_events=(event,),
        context_semantics=ContextSemantics.ACTUAL,
    )
    assert "frontier:causal:maximum-depth" not in result.frontier_refs


def test_branch_budget_never_returns_more_completed_branches_than_limit():
    from cemm.v350.causal import SimulationBudgetV351
    from cemm.v350.state import MechanismBranchV351

    role = pin("semantic_port", "branch-role")
    dimension = pin("state_dimension", "branch-state")
    trigger = pin("semantic_definition", "branch-trigger")
    competence = pin("competence_case", "branch-case")
    branches = tuple(
        MechanismBranchV351(
            f"branch:{i}", 0.25,
            (RoleStateTransformV351(
                f"transform:{i}", role, dimension,
                StateTransformExpression(
                    StateTransformOperator.ASSIGN,
                    (StateOperandV351(
                        OperandKind.CONSTANT,
                        constant=StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=float(i)),
                    ),),
                ),
            ),),
        )
        for i in range(4)
    )
    mechanism = TransitionMechanismV351(
        "mechanism:branch-budget", 1, MechanismTriggerKind.EVENT, trigger, (role,),
        branches=branches, competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    )
    snapshot = StateSnapshotV351(
        (), ((dimension.key, StateDomainContractV351("branch-state", 1, StateDomainKind.CONTINUOUS)),),
    )
    event = CausalEventV351(
        "event:branch-budget", trigger,
        (ParticipantRoleBinding(role, "r:branch", "app:branch"),), "actual", "t:0",
    )
    result = CausalPropagationEngine(
        mechanisms=(mechanism,), budget=SimulationBudgetV351(maximum_branches=2),
    ).simulate(initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.ACTUAL)
    assert len(result.branches) <= 2
    assert result.unresolved_probability_mass >= 0.5 - 1e-9
    assert "frontier:causal:branch-budget-pruned" in result.frontier_refs


def test_surviving_incomplete_branch_probability_is_counted_as_unresolved_mass():
    from cemm.v350.state import MechanismPrecondition, UnknownConditionPolicyV351
    role = pin("semantic_port", "partial-role")
    dimension = pin("state_dimension", "partial-state")
    trigger = pin("semantic_definition", "partial-trigger")
    competence = pin("competence_case", "partial-case")
    mechanism = TransitionMechanismV351(
        "mechanism:partial", 1, MechanismTriggerKind.EVENT, trigger, (role,),
        preconditions=(MechanismPrecondition(
            "condition:unknown", role, dimension, ConditionOperatorV351.KNOWN,
            unknown_policy=UnknownConditionPolicyV351.PRESERVE_FRONTIER,
        ),),
        deterministic_transforms=(RoleStateTransformV351(
            "transform:partial", role, dimension,
            StateTransformExpression(
                StateTransformOperator.ASSIGN,
                (StateOperandV351(OperandKind.CONSTANT, constant=StateValueV351(
                    StateDomainKind.CONTINUOUS, scalar_value=1.0
                )),),
            ),
        ),),
        competence_case_pins=(competence,), lifecycle_status="active", evidence_refs=("e:reviewed",),
        authorized_use_operations=(UseOperation.TRANSITION,), use_authority_explicit=True,
    )
    snapshot = StateSnapshotV351(
        (), ((dimension.key, StateDomainContractV351("partial-state", 1, StateDomainKind.CONTINUOUS)),),
    )
    event = CausalEventV351(
        "event:partial", trigger, (ParticipantRoleBinding(role, "r:partial", "app:partial"),),
        "actual", "t:0",
    )
    result = CausalPropagationEngine(mechanisms=(mechanism,)).simulate(
        initial_state=snapshot, root_events=(event,), context_semantics=ContextSemantics.ACTUAL,
    )
    assert len(result.branches) == 1
    assert not result.branches[0].resolved
    assert result.branches[0].probability == 1.0
    assert result.unresolved_probability_mass == 1.0


def test_goal_pressure_weights_stochastic_impact_by_branch_probability_without_conflating_confidence():
    from cemm.v350.causal import ImpactComponentV351, ImpactVector, goals_from_impact
    channel = pin("impact_channel", "wellbeing")
    component = ImpactComponentV351(
        channel, "r:stakeholder", "r:affected", 100.0, 0.5, ("d:1",), ("p:1",)
    )
    impact = ImpactVector(
        "impact:rare", "simulation:1", (component,), "actual", ContextSemantics.ACTUAL,
        0.1, True, ("d:1",), proof_refs=("p:1",),
    )
    goals = goals_from_impact((impact,))
    assert len(goals) == 1
    assert goals[0].utility == 5.0
