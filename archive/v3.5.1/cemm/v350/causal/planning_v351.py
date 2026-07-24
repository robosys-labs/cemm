"""Bounded causal planning by intervention simulation; never an execution shortcut."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Iterable, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import semantic_fingerprint
from ..state.transition_v351 import CausalEventV351, StateSnapshotV351
from .engine_v351 import CausalPropagationEngine
from .goals_v351 import CausalGoalDecisionV351
from .model_v351 import ContextSemantics, InterventionContext


@dataclass(frozen=True, slots=True)
class ActionCandidateV351:
    action_ref: str
    action_schema_pin: ExactAuthorityPin
    event: CausalEventV351
    capability_proof_refs: tuple[str, ...]
    authorization_refs: tuple[str, ...]
    resource_refs: tuple[str, ...] = ()
    adapter_contract_refs: tuple[str, ...] = ()
    risk_refs: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_ref:
            raise ValueError("action candidate requires action_ref")
        if not self.capability_proof_refs:
            raise ValueError("action candidate requires live capability proof")
        if not self.authorization_refs:
            raise ValueError("action candidate requires explicit planning authorization inputs")


@dataclass(frozen=True, slots=True)
class CausalPlanCandidateV351:
    plan_ref: str
    action_refs: tuple[str, ...]
    simulation_ref: str
    expected_utility: float
    goal_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    risk_refs: tuple[str, ...]
    executable: bool
    frontier_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CausalPlanDecisionV351:
    decision_ref: str
    candidates: tuple[CausalPlanCandidateV351, ...]
    selected_plan_ref: str
    frontier_refs: tuple[str, ...]


class CausalPlanner:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "causal_planner_v351"

    def __init__(self, engine: CausalPropagationEngine, *, maximum_candidates: int = 64) -> None:
        if maximum_candidates < 1:
            raise ValueError("maximum_candidates must be positive")
        self.engine = engine
        self.maximum_candidates = maximum_candidates

    def plan(
        self,
        *,
        goal_decision: CausalGoalDecisionV351,
        action_candidates: Iterable[ActionCandidateV351],
        initial_state: StateSnapshotV351,
        utility_evaluator,
        context_ref: str,
    ) -> CausalPlanDecisionV351:
        selected_goals = set(goal_decision.selected_goal_refs)
        candidates = []
        for action in tuple(action_candidates)[: self.maximum_candidates]:
            planning_context = f"planning:{context_ref}:{semantic_fingerprint('plan-context', action.action_ref, 12)}"
            event = CausalEventV351(
                event_ref=action.event.event_ref,
                predicate_pin=action.event.predicate_pin,
                role_bindings=action.event.role_bindings,
                context_ref=planning_context,
                effective_time_ref=action.event.effective_time_ref,
                time_step=0,
                evidence_refs=action.event.evidence_refs,
                proof_refs=action.event.proof_refs,
                occurrence_kind="planned",
            )
            simulation = self.engine.simulate(
                initial_state=initial_state,
                root_events=(event,),
                context_semantics=ContextSemantics.PLANNING,
            )
            utility = float(utility_evaluator(simulation, selected_goals))
            if not isfinite(utility):
                raise ValueError("causal plan utility evaluator must return a finite value")
            frontier_refs = tuple(sorted(set((*simulation.frontier_refs, *action.risk_refs))))
            executable = bool(action.adapter_contract_refs) and not simulation.budget_exhausted and not frontier_refs
            candidates.append(CausalPlanCandidateV351(
                plan_ref="causal-plan:" + semantic_fingerprint(
                    "causal-plan-v351", (action.action_ref, simulation.simulation_ref, tuple(sorted(selected_goals))), 32,
                ),
                action_refs=(action.action_ref,), simulation_ref=simulation.simulation_ref,
                expected_utility=utility, goal_refs=tuple(sorted(selected_goals)),
                proof_refs=tuple(proof.proof_ref for proof in simulation.causal_proofs),
                risk_refs=action.risk_refs, executable=executable, frontier_refs=frontier_refs,
            ))
        ranked = sorted(candidates, key=lambda item: (-item.expected_utility, item.plan_ref))
        selected = next((item.plan_ref for item in ranked if item.executable), "")
        frontiers = () if selected else ("frontier:planning:no-authorized-executable-plan",)
        return CausalPlanDecisionV351(
            decision_ref="causal-plan-decision:" + semantic_fingerprint(
                "causal-plan-decision-v351", (goal_decision.decision_ref, tuple(item.plan_ref for item in ranked), selected), 32,
            ),
            candidates=tuple(ranked), selected_plan_ref=selected, frontier_refs=frontiers,
        )


__all__ = ["ActionCandidateV351", "CausalPlanCandidateV351", "CausalPlanDecisionV351", "CausalPlanner"]
