"""Vector-valued causal goal arbitration for Phase 16."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Iterable, Mapping

from ..csir.model import ExactAuthorityPin
from ..response.csir_v351 import ConversationalGoalCandidate, ConversationalGoalDecision, ResponseFamily
from ..runtime_abi import artifact_ref
from ..schema.model import semantic_fingerprint
from .impact_v351 import ImpactVector
from .authority_v351 import require_exact_use
from .model_v351 import CausalQueryResultV351, CausalSimulationResultV351, ContextSemantics


@dataclass(frozen=True, slots=True)
class GoalUtilityComponentV351:
    component_ref: str
    channel_pin: ExactAuthorityPin | None
    weight: float
    source_ref: str
    value: float

    def __post_init__(self) -> None:
        if not self.component_ref or not self.source_ref:
            raise ValueError("goal utility component requires refs")
        if not isfinite(self.weight) or not isfinite(self.value):
            raise ValueError("goal utility values must be finite")


@dataclass(frozen=True, slots=True)
class CausalGoalCandidateV351:
    goal_ref: str
    goal_kind: str
    target_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    utility_components: tuple[GoalUtilityComponentV351, ...]
    hard_constraint_refs: tuple[str, ...] = ()
    risk_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    priority: int = 0
    authorized: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.goal_ref or not self.goal_kind:
            raise ValueError("causal goal candidate requires identity and kind")
        for values, label in (
            (self.target_refs, "targets"), (self.source_refs, "sources"),
            (self.hard_constraint_refs, "hard constraints"), (self.risk_refs, "risks"),
            (self.proof_refs, "proofs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"causal goal {label} must be unique")
        utility = sum(item.weight * item.value for item in self.utility_components)
        if not isfinite(utility):
            raise ValueError("causal goal utility must be finite")

    @property
    def utility(self) -> float:
        return sum(item.weight * item.value for item in self.utility_components)


@dataclass(frozen=True, slots=True)
class CausalGoalDecisionV351:
    decision_ref: str
    candidates: tuple[CausalGoalCandidateV351, ...]
    selected_goal_refs: tuple[str, ...]
    rejected_goal_refs: tuple[str, ...]
    deferred_goal_refs: tuple[str, ...]
    conflict_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str


@dataclass(frozen=True, slots=True)
class GoalArbitrationPolicyV351:
    policy_pin: ExactAuthorityPin
    maximum_selected: int = 1
    risk_penalty_weight: float = 1.0
    unresolved_penalty_weight: float = 1.0
    minimum_utility: float = float("-inf")

    def __post_init__(self) -> None:
        if self.maximum_selected < 1:
            raise ValueError("goal arbitration maximum_selected must be positive")
        if not isfinite(self.risk_penalty_weight) or self.risk_penalty_weight < 0.0:
            raise ValueError("goal risk penalty must be finite and non-negative")
        if not isfinite(self.unresolved_penalty_weight) or self.unresolved_penalty_weight < 0.0:
            raise ValueError("goal unresolved penalty must be finite and non-negative")
        if self.minimum_utility != float("-inf") and not isfinite(self.minimum_utility):
            raise ValueError("goal minimum utility must be finite or negative infinity")


class GoalArbitrator:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "goal_engine"

    def __init__(self, policy: GoalArbitrationPolicyV351 | None = None) -> None:
        self.policy = policy

    def arbitrate(
        self,
        candidates: Iterable[CausalGoalCandidateV351],
        *,
        context_ref: str,
        permission_ref: str,
        authority_snapshot=None,
    ) -> CausalGoalDecisionV351:
        values = tuple(candidates)
        if self.policy is None:
            # Candidate generation is cognition; executable arbitration authority is separate.
            return CausalGoalDecisionV351(
                decision_ref="causal-goal-decision:" + semantic_fingerprint("goal-no-policy", (context_ref, permission_ref), 24),
                candidates=values, selected_goal_refs=(), rejected_goal_refs=(),
                deferred_goal_refs=tuple(item.goal_ref for item in values), conflict_refs=(),
                proof_refs=("frontier:goal:arbitration-policy-required",), context_ref=context_ref, permission_ref=permission_ref,
            )
        try:
            require_exact_use(
                authority_snapshot, self.policy.policy_pin, operation="response_policy",
                context_ref=context_ref, permission_ref=permission_ref,
            )
        except Exception:
            return CausalGoalDecisionV351(
                decision_ref="causal-goal-decision:" + semantic_fingerprint(
                    "goal-policy-use-not-authorized", (self.policy.policy_pin.key, context_ref, permission_ref), 24
                ),
                candidates=values, selected_goal_refs=(), rejected_goal_refs=(),
                deferred_goal_refs=tuple(item.goal_ref for item in values), conflict_refs=(),
                proof_refs=("frontier:goal:exact-arbitration-use-authority-required",),
                context_ref=context_ref, permission_ref=permission_ref,
            )
        scored = []
        rejected, deferred = [], []
        for item in values:
            if not item.authorized:
                deferred.append(item.goal_ref); continue
            if item.hard_constraint_refs:
                rejected.append(item.goal_ref); continue
            score = item.utility - self.policy.risk_penalty_weight * len(item.risk_refs)
            score -= self.policy.unresolved_penalty_weight * len(tuple(item.metadata.get("frontier_refs", ())))
            if score < self.policy.minimum_utility:
                rejected.append(item.goal_ref); continue
            scored.append((score, item.priority, item.goal_ref, item))
        scored.sort(key=lambda row: (-row[0], -row[1], row[2]))
        selected = tuple(row[2] for row in scored[: self.policy.maximum_selected])
        rejected.extend(row[2] for row in scored[self.policy.maximum_selected :])
        return CausalGoalDecisionV351(
            decision_ref="causal-goal-decision:" + semantic_fingerprint(
                "causal-goal-decision-v351", (self.policy.policy_pin.key, context_ref, permission_ref, selected, tuple(sorted(rejected)), tuple(sorted(deferred))), 32,
            ),
            candidates=values, selected_goal_refs=selected, rejected_goal_refs=tuple(sorted(set(rejected))),
            deferred_goal_refs=tuple(sorted(set(deferred))), conflict_refs=(),
            proof_refs=(self.policy.policy_pin.ref,), context_ref=context_ref, permission_ref=permission_ref,
        )

    def run(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, store, effect_store, semantic_capabilities
        # Preserve ordinary Phase-12 response behavior but make causal explanation requests
        # first-class when Stage 10/12 produced a warranted causal query result.
        causal_results = tuple(cycle.artifacts.get("causal_query_results", ()) or ())
        answered = [item for item in causal_results if isinstance(item, CausalQueryResultV351) and item.answered and item.explanation is not None]
        if answered:
            candidates = tuple(
                ConversationalGoalCandidate(
                    goal_ref=artifact_ref("goal:causal-explanation", item.result_ref),
                    family=ResponseFamily.PROVIDE_CAUSAL_EXPLANATION,
                    target_refs=(item.query_ref,), source_refs=(item.explanation.explanation_ref,),
                    reason_refs=(item.explanation.proof_ref,), priority=1200,
                    blocked_by_frontier_refs=item.frontier_refs,
                )
                for item in answered
            )
            selected = tuple(item.goal_ref for item in candidates if not item.blocked_by_frontier_refs)
            return {
                "goal_candidates": candidates,
                "goal_decision": ConversationalGoalDecision(
                    decision_ref=artifact_ref("goal-decision:causal-explanation", tuple(selected)),
                    candidates=candidates, selected_goal_refs=selected[:1],
                    selected_families=((ResponseFamily.PROVIDE_CAUSAL_EXPLANATION,) if selected else (ResponseFamily.QUALIFY_UNCERTAINTY,)),
                    context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                    reason_refs=tuple(item.explanation.proof_ref for item in answered),
                ),
            }
        # Do not duplicate the conversational alpha's policy in this module. Runtime wiring
        # installs a composite adapter that delegates ordinary conversational goals to the
        # existing bridge and uses this arbitrator for causal/planning goals.
        return {"causal_goal_candidates": (), "causal_goal_decision": None}


def goals_from_impact(impacts: Iterable[ImpactVector], *, target_goal_kind: str = "improve_expected_state") -> tuple[CausalGoalCandidateV351, ...]:
    """Aggregate actual-world stochastic impacts into expected goal pressure.

    Probability and epistemic confidence remain distinct: each utility contribution is
    `magnitude × confidence × branch_probability`. Branch-specific ImpactVectors remain
    available for risk/tail evaluators, while ordinary goal arbitration receives one expected
    candidate per affected referent and simulation source instead of treating mutually exclusive
    stochastic branches as independent competing goals.
    """
    grouped = {}
    for impact in impacts:
        if impact.context_semantics is not ContextSemantics.ACTUAL or not impact.resolved:
            # Unresolved actual branches remain available to explicit risk/tail evaluators,
            # but ordinary goal pressure must not turn partial cognition into an obligation.
            continue
        for component in impact.components:
            key = (impact.source_ref, component.affected_ref, target_goal_kind)
            group = grouped.setdefault(key, {
                "components": [], "impact_refs": set(), "proof_refs": set(), "frontiers": set(),
            })
            group["components"].append((impact, component))
            group["impact_refs"].add(impact.impact_ref)
            group["proof_refs"].update(impact.proof_refs)
            group["frontiers"].update(impact.frontier_refs)

    result = []
    for (source_ref, affected_ref, goal_kind), group in sorted(grouped.items(), key=lambda item: item[0]):
        utility_components = tuple(
            GoalUtilityComponentV351(
                component_ref="goal-utility:" + semantic_fingerprint(
                    "goal-utility-component",
                    (impact.impact_ref, index, component.channel_pin.key, affected_ref), 24,
                ),
                channel_pin=component.channel_pin, weight=1.0, source_ref=impact.impact_ref,
                value=(
                    component.signed_magnitude
                    * component.confidence
                    * impact.branch_probability
                ),
            )
            for index, (impact, component) in enumerate(group["components"])
        )
        impact_refs = tuple(sorted(group["impact_refs"]))
        proof_refs = tuple(sorted(group["proof_refs"]))
        frontiers = tuple(sorted(group["frontiers"]))
        result.append(CausalGoalCandidateV351(
            goal_ref="causal-goal:" + semantic_fingerprint(
                "causal-goal-v351", (source_ref, goal_kind, affected_ref, impact_refs), 32
            ),
            goal_kind=goal_kind, target_refs=(affected_ref,), source_refs=impact_refs,
            utility_components=utility_components, proof_refs=proof_refs,
            risk_refs=frontiers, metadata={"frontier_refs": frontiers, "expected_utility": True},
        ))
    return tuple(result)


__all__ = [
    "CausalGoalCandidateV351", "CausalGoalDecisionV351", "GoalArbitrationPolicyV351",
    "GoalArbitrator", "GoalUtilityComponentV351", "goals_from_impact",
]
