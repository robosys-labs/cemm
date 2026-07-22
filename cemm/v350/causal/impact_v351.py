"""Causal impact vectors with strict physical/affective/report/stance separation."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Iterable, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import semantic_fingerprint
from ..state.model_v351 import StateDeltaV351
from .model_v351 import CausalSimulationResultV351, ContextSemantics


@dataclass(frozen=True, slots=True)
class ImpactComponentV351:
    channel_pin: ExactAuthorityPin
    stakeholder_ref: str
    affected_ref: str
    signed_magnitude: float
    confidence: float
    source_delta_refs: tuple[str, ...]
    causal_proof_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stakeholder_ref or not self.affected_ref:
            raise ValueError("impact component requires stakeholder and affected refs")
        if not isfinite(self.signed_magnitude):
            raise ValueError("impact magnitude must be finite")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("impact confidence must be in [0,1]")


@dataclass(frozen=True, slots=True)
class ImpactVector:
    impact_ref: str
    source_ref: str
    components: tuple[ImpactComponentV351, ...]
    context_ref: str
    context_semantics: ContextSemantics
    branch_probability: float
    resolved: bool
    physical_state_delta_refs: tuple[str, ...]
    affective_state_delta_refs: tuple[str, ...] = ()
    reported_affect_refs: tuple[str, ...] = ()
    response_stance_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.impact_ref or not self.source_ref or not self.context_ref:
            raise ValueError("impact vector requires refs")
        if not isfinite(self.branch_probability) or not 0.0 <= self.branch_probability <= 1.0:
            raise ValueError("impact branch probability must be in [0,1]")
        physical = set(self.physical_state_delta_refs)
        affective = set(self.affective_state_delta_refs)
        reports = set(self.reported_affect_refs)
        stance = set(self.response_stance_refs)
        if physical & affective or physical & reports or physical & stance or affective & reports or affective & stance or reports & stance:
            raise ValueError("physical state, affective consequence, reported affect and response stance must remain distinct")


@dataclass(frozen=True, slots=True)
class ImpactProjectionRuleV351:
    rule_ref: str
    source_dimension_pin: ExactAuthorityPin
    channel_pin: ExactAuthorityPin
    stakeholder_role_pin: ExactAuthorityPin
    affected_role_pin: ExactAuthorityPin
    scale: float = 1.0
    revision: int = 1
    lifecycle_status: str = "candidate"
    competence_case_pins: tuple[ExactAuthorityPin, ...] = ()


    def __post_init__(self) -> None:
        if not self.rule_ref:
            raise ValueError("impact projection rule requires identity")
        if self.revision < 1:
            raise ValueError("impact projection rule revision must be positive")
        if not isfinite(self.scale):
            raise ValueError("impact projection rule scale must be finite")

    @property
    def authority_pin(self) -> ExactAuthorityPin:
        payload = (
            self.rule_ref, self.source_dimension_pin.key, self.channel_pin.key,
            self.stakeholder_role_pin.key, self.affected_role_pin.key, float(self.scale), self.revision,
        )
        return ExactAuthorityPin(
            "impact_projection_rule", "cemm:v351:causal:impact", self.rule_ref, self.revision,
            semantic_fingerprint("impact-projection-rule-v351", payload, 64), "global",
        )

    @property
    def executable(self) -> bool:
        return self.lifecycle_status == "active" and bool(self.competence_case_pins)


class CausalImpactEngineV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "causal_impact_engine_v351"

    def __init__(self, rules: Iterable[ImpactProjectionRuleV351] = ()) -> None:
        self.rules = tuple(rules)

    def derive(
        self,
        simulation: CausalSimulationResultV351,
        *,
        role_bindings: Mapping[tuple, str] | None = None,
        affective_dimension_pins: tuple[ExactAuthorityPin, ...] = (),
    ) -> tuple[ImpactVector, ...]:
        role_bindings = dict(role_bindings or {})
        affective = {pin.key for pin in affective_dimension_pins}
        results = []
        proof_by_step = {
            step.step_ref: step
            for proof in simulation.causal_proofs
            for step in proof.steps
        }
        for branch in simulation.branches:
            components = []
            step_by_delta = {
                proof_by_step[ref].delta_ref: proof_by_step[ref]
                for ref in branch.proof_step_refs
                if ref in proof_by_step and proof_by_step[ref].delta_ref
            }
            physical_refs, affective_refs = [], []
            for delta in branch.state_deltas:
                if delta.dimension_pin.key in affective: affective_refs.append(delta.delta_ref)
                else: physical_refs.append(delta.delta_ref)
                for rule in self.rules:
                    if not rule.executable or rule.source_dimension_pin.key != delta.dimension_pin.key:
                        continue
                    step = step_by_delta.get(delta.delta_ref)
                    exact_roles = (
                        {item.role_pin.key: item.participant_ref for item in step.role_bindings}
                        if step is not None else {}
                    )
                    stakeholder = exact_roles.get(
                        rule.stakeholder_role_pin.key, role_bindings.get(rule.stakeholder_role_pin.key)
                    )
                    affected = exact_roles.get(
                        rule.affected_role_pin.key, role_bindings.get(rule.affected_role_pin.key)
                    )
                    if not stakeholder or not affected:
                        continue
                    magnitude = _delta_magnitude(delta) * rule.scale
                    components.append(ImpactComponentV351(
                        channel_pin=rule.channel_pin, stakeholder_ref=stakeholder, affected_ref=affected,
                        signed_magnitude=magnitude, confidence=delta.confidence,
                        source_delta_refs=(delta.delta_ref,), causal_proof_refs=delta.proof_refs,
                    ))
            if not components and not branch.state_deltas:
                continue
            results.append(ImpactVector(
                impact_ref="impact-vector:" + semantic_fingerprint(
                    "impact-vector-v351", (simulation.simulation_ref, branch.branch_ref, tuple((x.channel_pin.key, x.signed_magnitude) for x in components)), 32,
                ),
                source_ref=simulation.simulation_ref, components=tuple(components), context_ref=simulation.context_ref,
                context_semantics=simulation.context_semantics, branch_probability=branch.probability,
                resolved=branch.resolved,
                physical_state_delta_refs=tuple(physical_refs), affective_state_delta_refs=tuple(affective_refs),
                proof_refs=tuple(branch.proof_step_refs), frontier_refs=tuple(branch.frontier_refs),
            ))
        return tuple(results)


def _delta_magnitude(delta: StateDeltaV351) -> float:
    before, after = delta.prior_value, delta.new_value
    if before is not None and after is not None:
        if before.scalar_value is not None and after.scalar_value is not None:
            return float(after.scalar_value - before.scalar_value)
        if before.vector_value and after.vector_value and len(before.vector_value) == len(after.vector_value):
            return sum((b - a) ** 2 for a, b in zip(before.vector_value, after.vector_value)) ** 0.5
        if before.set_members or after.set_members:
            return float(len(set(after.set_members) - set(before.set_members)) - len(set(before.set_members) - set(after.set_members)))
        return 0.0 if before.value_ref == after.value_ref else 1.0
    return 1.0 if after is not None else -1.0


__all__ = ["CausalImpactEngineV351", "ImpactComponentV351", "ImpactProjectionRuleV351", "ImpactVector"]
