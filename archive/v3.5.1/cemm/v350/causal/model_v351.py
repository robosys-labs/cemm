"""Structural causal model and proof contracts for CEMM v3.5.1 Phase 16."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Iterable, Mapping

from ..csir.model import CSIRGraph, ExactAuthorityPin
from ..schema.model import semantic_fingerprint
from ..state.model_v351 import ParticipantRoleBinding, StateDeltaV351, StateModelError, StateValueV351


class CausalModelError(ValueError):
    pass


class ContextSemantics(str, Enum):
    ACTUAL = "actual"
    HYPOTHETICAL = "hypothetical"
    INTERVENTION = "intervention"
    COUNTERFACTUAL = "counterfactual"
    PLANNING = "planning"


@dataclass(frozen=True, slots=True)
class CausalVariable:
    variable_ref: str
    holder_ref: str
    dimension_pin: ExactAuthorityPin
    context_ref: str
    time_step: int = 0

    def __post_init__(self) -> None:
        if not self.variable_ref or not self.holder_ref or not self.context_ref:
            raise CausalModelError("causal variable requires identity, holder and context")
        if self.time_step < 0:
            raise CausalModelError("causal variable time_step cannot be negative")

    @property
    def key(self):
        return self.holder_ref, self.dimension_pin.key, self.context_ref, self.time_step

    @property
    def structural_key(self):
        """Equation identity replaced by do(...); temporal occurrence identity is separate."""
        return self.holder_ref, self.dimension_pin.key, self.context_ref


@dataclass(frozen=True, slots=True)
class CausalMechanismEdgeV351:
    edge_ref: str
    source_variable_ref: str
    target_variable_ref: str
    mechanism_pin: ExactAuthorityPin
    lag_steps: int = 0
    confidence: float = 1.0
    warrant_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.edge_ref or not self.source_variable_ref or not self.target_variable_ref:
            raise CausalModelError("causal edge requires stable refs")
        if self.source_variable_ref == self.target_variable_ref and self.lag_steps == 0:
            raise CausalModelError("instantaneous causal self-loop requires an explicit solver contract")
        if self.lag_steps < 0:
            raise CausalModelError("causal edge lag cannot be negative")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise CausalModelError("causal edge confidence must be in [0,1]")
        _unique(self.warrant_refs, "causal edge warrants")


@dataclass(frozen=True, slots=True)
class CausalMechanismGraph:
    graph_ref: str
    variables: tuple[CausalVariable, ...]
    edges: tuple[CausalMechanismEdgeV351, ...]
    mechanism_pins: tuple[ExactAuthorityPin, ...]
    authority_generation: int
    authority_fingerprint: str
    context_ref: str
    solver_contract_pin: ExactAuthorityPin | None = None
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.graph_ref or not self.context_ref or not self.authority_fingerprint or self.authority_generation < 1:
            raise CausalModelError("causal graph requires exact authority/context identity")
        by_ref = {item.variable_ref: item for item in self.variables}
        if len(by_ref) != len(self.variables):
            raise CausalModelError("causal variables must be unique")
        if any(item.context_ref != self.context_ref for item in self.variables):
            raise CausalModelError("causal graph variables must belong to the graph context")
        mechanism_keys = {pin.key for pin in self.mechanism_pins}
        for edge in self.edges:
            if edge.source_variable_ref not in by_ref or edge.target_variable_ref not in by_ref:
                raise CausalModelError("causal edge references unknown variable")
            if edge.mechanism_pin.key not in mechanism_keys:
                raise CausalModelError("causal edge mechanism is outside exact graph authority")
            source = by_ref[edge.source_variable_ref]
            target = by_ref[edge.target_variable_ref]
            if target.time_step - source.time_step != edge.lag_steps:
                raise CausalModelError("causal edge lag must equal target/source temporal occurrence distance")
        _unique((item.edge_ref for item in self.edges), "causal edge refs")
        _unique((pin.key for pin in self.mechanism_pins), "causal mechanism pins")
        _unique(self.proof_refs, "causal graph proofs")
        self._validate_cycles(by_ref)

    def _validate_cycles(self, by_ref):
        # Only zero-lag cycles require a simultaneous solver contract. Positive-lag feedback
        # is a temporal recurrence and remains bounded by simulation budgets.
        graph = {ref: [] for ref in by_ref}
        for edge in self.edges:
            if edge.lag_steps == 0:
                graph[edge.source_variable_ref].append(edge.target_variable_ref)
        visiting, done = set(), set()
        def walk(ref):
            if ref in done: return
            if ref in visiting:
                if self.solver_contract_pin is None:
                    raise CausalModelError("instantaneous causal cycle lacks exact solver authority")
                return
            visiting.add(ref)
            for nxt in graph[ref]: walk(nxt)
            visiting.remove(ref); done.add(ref)
        for ref in sorted(graph): walk(ref)


@dataclass(frozen=True, slots=True)
class InterventionAssignmentV351:
    variable: CausalVariable
    value: StateValueV351
    authorization_pins: tuple[ExactAuthorityPin, ...]
    role_bindings: tuple[ParticipantRoleBinding, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.authorization_pins:
            raise CausalModelError("intervention assignment requires exact authorization pins")
        _unique((pin.key for pin in self.authorization_pins), "intervention authorization pins")
        _unique((item.role_pin.key for item in self.role_bindings), "intervention role bindings")
        _unique(self.evidence_refs, "intervention evidence")
        if self.role_bindings and self.variable.holder_ref not in {item.participant_ref for item in self.role_bindings}:
            raise CausalModelError("intervention role bindings must include the target holder")


@dataclass(frozen=True, slots=True)
class InterventionContext:
    context_ref: str
    parent_context_ref: str
    interventions: tuple[InterventionAssignmentV351, ...]
    evidence_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.context_ref or not self.parent_context_ref or self.context_ref == self.parent_context_ref:
            raise CausalModelError("intervention context requires a distinct parent context")
        if not self.interventions:
            raise CausalModelError("intervention context requires at least one explicit do-assignment")
        _unique((item.variable.structural_key for item in self.interventions), "intervention structural targets")
        if any(item.variable.context_ref != self.context_ref for item in self.interventions):
            raise CausalModelError("intervention target variables must belong to intervention context")
        _unique(self.evidence_refs, "intervention evidence")
        _unique(self.proof_refs, "intervention proofs")

    @property
    def cut_target_keys(self) -> frozenset[tuple]:
        # do(X=x) replaces the structural equation for X throughout this isolated context;
        # occurrence time remains proof lineage, not part of the equation identity.
        return frozenset(item.variable.structural_key for item in self.interventions)


@dataclass(frozen=True, slots=True)
class ExogenousAssumptionV351:
    """Typed result of the counterfactual abduction step.

    The assumption is not a free-form label: it pins the exact causal variable and value that
    must be held fixed while the intervention changes structural equations.
    """

    assumption_ref: str
    variable: CausalVariable
    value: StateValueV351
    support: float
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.assumption_ref:
            raise CausalModelError("exogenous assumption requires identity")
        if not isfinite(self.support) or not 0.0 <= self.support <= 1.0:
            raise CausalModelError("exogenous assumption support must be in [0,1]")
        _unique(self.evidence_refs, "exogenous assumption evidence")


@dataclass(frozen=True, slots=True)
class CounterfactualContext:
    context_ref: str
    factual_context_ref: str
    intervention: InterventionContext
    factual_evidence_refs: tuple[str, ...]
    exogenous_assumptions: tuple[ExogenousAssumptionV351, ...]
    target_variable_refs: tuple[str, ...]
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.context_ref or not self.factual_context_ref or self.context_ref == self.factual_context_ref:
            raise CausalModelError("counterfactual context must be isolated from factual context")
        if self.intervention.context_ref != self.context_ref:
            raise CausalModelError("counterfactual intervention must target counterfactual context")
        if not self.factual_evidence_refs:
            raise CausalModelError("counterfactual abduction requires factual evidence lineage")
        if not self.target_variable_refs:
            raise CausalModelError("counterfactual context requires explicit target variables")
        if any(item.variable.context_ref != self.context_ref for item in self.exogenous_assumptions):
            raise CausalModelError("counterfactual exogenous assumptions must belong to counterfactual context")
        _unique(self.factual_evidence_refs, "counterfactual factual evidence")
        _unique((item.assumption_ref for item in self.exogenous_assumptions), "counterfactual exogenous assumptions")
        _unique((item.variable.structural_key for item in self.exogenous_assumptions), "counterfactual exogenous variable assumptions")
        _unique(self.target_variable_refs, "counterfactual target variables")
        _unique(self.proof_refs, "counterfactual proofs")


@dataclass(frozen=True, slots=True)
class CausalProofStepV351:
    step_ref: str
    mechanism_pin: ExactAuthorityPin
    source_variable_refs: tuple[str, ...]
    source_event_refs: tuple[str, ...]
    target_variable_ref: str
    trigger_ref: str
    branch_probability: float
    confidence: float
    warrant_refs: tuple[str, ...]
    role_bindings: tuple[ParticipantRoleBinding, ...] = ()
    delta_ref: str = ""
    prior_value_ref: str = ""
    new_value_ref: str = ""
    secondary_event_ref: str = ""
    suppressed_delta_ref: str = ""
    parent_step_refs: tuple[str, ...] = ()
    intervention_cut: bool = False

    def __post_init__(self) -> None:
        if not self.step_ref or not self.trigger_ref:
            raise CausalModelError("causal proof step requires stable refs")
        effect_count = (
            int(bool(self.delta_ref)) + int(bool(self.secondary_event_ref))
            + int(bool(self.intervention_cut))
        )
        if effect_count != 1:
            raise CausalModelError(
                "causal proof step requires exactly one state-delta, secondary-event, or intervention-cut effect"
            )
        if (self.delta_ref or self.intervention_cut) and not self.target_variable_ref:
            raise CausalModelError("state/cut causal proof step requires target variable")
        if self.delta_ref and not (self.prior_value_ref or self.new_value_ref):
            raise CausalModelError(
                "state-delta causal proof step requires an exact prior or new value identity"
            )
        if self.intervention_cut and not self.suppressed_delta_ref:
            raise CausalModelError("intervention-cut proof step requires suppressed delta identity")
        if self.intervention_cut and (self.delta_ref or self.secondary_event_ref):
            raise CausalModelError("intervention-cut proof step cannot also materialize an effect")
        if not self.delta_ref and (self.prior_value_ref or self.new_value_ref):
            raise CausalModelError("non-state causal proof step cannot carry state value identities")
        if not isfinite(self.branch_probability) or not 0.0 <= self.branch_probability <= 1.0:
            raise CausalModelError("causal proof branch probability must be in [0,1]")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise CausalModelError("causal proof confidence must be in [0,1]")
        _unique(self.source_variable_refs, "causal proof variable sources")
        _unique(self.source_event_refs, "causal proof event sources")
        _unique(self.warrant_refs, "causal proof warrants")
        _unique((item.role_pin.key for item in self.role_bindings), "causal proof role bindings")
        _unique(self.parent_step_refs, "causal proof parents")


@dataclass(frozen=True, slots=True)
class CausalProofV351:
    proof_ref: str
    context_ref: str
    context_semantics: ContextSemantics
    steps: tuple[CausalProofStepV351, ...]
    root_trigger_refs: tuple[str, ...]
    target_variable_refs: tuple[str, ...]
    intervention_ref: str = ""
    exogenous_assumption_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.proof_ref or not self.context_ref:
            raise CausalModelError("causal proof requires identity/context")
        _unique((item.step_ref for item in self.steps), "causal proof steps")
        known = {item.step_ref for item in self.steps}
        by_ref = {item.step_ref: item for item in self.steps}
        for step in self.steps:
            if not set(step.parent_step_refs).issubset(known):
                raise CausalModelError("causal proof step references unknown parent")
        visiting, done = set(), set()
        def visit(ref):
            if ref in done:
                return
            if ref in visiting:
                raise CausalModelError("causal proof parent relation must be acyclic")
            visiting.add(ref)
            for parent in by_ref[ref].parent_step_refs:
                visit(parent)
            visiting.remove(ref); done.add(ref)
        for ref in sorted(by_ref):
            visit(ref)
        for values, label in (
            (self.root_trigger_refs, "causal proof roots"),
            (self.target_variable_refs, "causal proof targets"),
            (self.exogenous_assumption_refs, "causal proof exogenous assumptions"),
            (self.evidence_refs, "causal proof evidence"),
            (self.frontier_refs, "causal proof frontiers"),
        ):
            _unique(values, label)


@dataclass(frozen=True, slots=True)
class CausalExplanationV351:
    explanation_ref: str
    query_ref: str
    target_variable_ref: str
    cause_variable_refs: tuple[str, ...]
    cause_event_refs: tuple[str, ...]
    mechanism_pins: tuple[ExactAuthorityPin, ...]
    proof_ref: str
    step_refs: tuple[str, ...]
    minimal: bool
    confidence: float
    probability: float = 1.0
    cause_graph: CSIRGraph | None = None
    effect_graph: CSIRGraph | None = None
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.explanation_ref or not self.query_ref or not self.target_variable_ref or not self.proof_ref:
            raise CausalModelError("causal explanation requires stable refs")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise CausalModelError("causal explanation confidence must be in [0,1]")
        if not isfinite(self.probability) or not 0.0 <= self.probability <= 1.0:
            raise CausalModelError("causal explanation probability must be in [0,1]")
        _unique(self.cause_variable_refs, "causal explanation variable causes")
        _unique(self.cause_event_refs, "causal explanation event causes")
        _unique((pin.key for pin in self.mechanism_pins), "causal explanation mechanisms")
        _unique(self.step_refs, "causal explanation steps")
        _unique(self.frontier_refs, "causal explanation frontiers")


@dataclass(frozen=True, slots=True)
class SimulationBudgetV351:
    maximum_depth: int = 12
    maximum_time_step: int = 1024
    maximum_events: int = 256
    maximum_deltas: int = 1024
    maximum_branches: int = 64
    maximum_proof_steps: int = 2048
    minimum_branch_probability: float = 1e-6
    minimum_confidence: float = 1e-6

    def __post_init__(self) -> None:
        if min(
            self.maximum_depth, self.maximum_time_step, self.maximum_events, self.maximum_deltas,
            self.maximum_branches, self.maximum_proof_steps,
        ) < 1:
            raise CausalModelError("causal simulation budgets must be positive")
        if not 0.0 <= self.minimum_branch_probability <= 1.0 or not 0.0 <= self.minimum_confidence <= 1.0:
            raise CausalModelError("causal simulation thresholds must be in [0,1]")


@dataclass(frozen=True, slots=True)
class CausalSimulationBranchV351:
    branch_ref: str
    probability: float
    confidence: float
    proof_ref: str
    state_deltas: tuple[StateDeltaV351, ...]
    secondary_event_refs: tuple[str, ...]
    proof_step_refs: tuple[str, ...]
    resolved: bool = True
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.branch_ref or not self.proof_ref:
            raise CausalModelError("causal simulation branch requires identity and exact proof_ref")
        if not isfinite(self.probability) or not 0.0 <= self.probability <= 1.0:
            raise CausalModelError("causal simulation branch probability must be in [0,1]")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise CausalModelError("causal simulation branch confidence must be in [0,1]")
        _unique(self.secondary_event_refs, "simulation branch secondary events")
        _unique(self.proof_step_refs, "simulation branch proof steps")
        _unique(self.frontier_refs, "simulation branch frontiers")


@dataclass(frozen=True, slots=True)
class CausalSimulationResultV351:
    simulation_ref: str
    context_ref: str
    context_semantics: ContextSemantics
    branches: tuple[CausalSimulationBranchV351, ...]
    causal_proofs: tuple[CausalProofV351, ...]
    final_state_refs: tuple[str, ...]
    frontier_refs: tuple[str, ...]
    budget_exhausted: bool = False
    intervention_ref: str = ""
    actual_state_unchanged: bool = True
    unresolved_probability_mass: float = 0.0

    def __post_init__(self) -> None:
        if not self.simulation_ref or not self.context_ref:
            raise CausalModelError("causal simulation result requires refs")
        _unique((item.branch_ref for item in self.branches), "simulation branches")
        _unique((item.proof_ref for item in self.branches), "simulation branch proofs")
        _unique((item.proof_ref for item in self.causal_proofs), "simulation proofs")
        proof_by_ref = {item.proof_ref: item for item in self.causal_proofs}
        for branch in self.branches:
            proof = proof_by_ref.get(branch.proof_ref)
            if proof is None:
                raise CausalModelError("simulation branch references missing causal proof")
            if set(branch.proof_step_refs) != {item.step_ref for item in proof.steps}:
                raise CausalModelError("simulation branch/proof step identity mismatch")
        _unique(self.final_state_refs, "simulation final states")
        _unique(self.frontier_refs, "simulation frontiers")
        if not isfinite(self.unresolved_probability_mass) or not 0.0 <= self.unresolved_probability_mass <= 1.0 + 1e-9:
            raise CausalModelError("simulation unresolved probability mass must be in [0,1]")
        branch_mass = sum(item.probability for item in self.branches)
        resolved_mass = sum(item.probability for item in self.branches if item.resolved)
        if branch_mass > 1.0 + 1e-9:
            raise CausalModelError("simulation branch probability mass exceeds one")
        # Incomplete surviving branches are themselves part of unresolved mass, so total
        # branch_mass + unresolved may exceed one by that overlap. Only genuinely resolved
        # mass must be disjoint from unresolved probability.
        if resolved_mass + self.unresolved_probability_mass > 1.0 + 1e-8:
            raise CausalModelError("resolved plus unresolved probability mass exceeds one")


@dataclass(frozen=True, slots=True)
class CausalLearningEvidenceV351:
    evidence_ref: str
    mechanism_pin: ExactAuthorityPin
    source_variable_refs: tuple[str, ...]
    source_event_refs: tuple[str, ...]
    target_variable_ref: str
    proof_step_refs: tuple[str, ...]
    target_event_ref: str = ""
    intervention_support_refs: tuple[str, ...] = ()
    # Direct mechanistic evidence is distinct from generic proof lineage. A proof that an
    # already-authorized mechanism fired supports that exact mechanism; arbitrary causal-path
    # proof refs do not make a different hypothesis causal.
    mechanism_support_refs: tuple[str, ...] = ()
    counterexample_refs: tuple[str, ...] = ()
    source_lineage_refs: tuple[str, ...] = ()
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.evidence_ref:
            raise CausalModelError("causal learning evidence requires identity")
        if bool(self.target_variable_ref) == bool(self.target_event_ref):
            raise CausalModelError(
                "causal learning evidence requires exactly one target variable or target event"
            )
        if not isfinite(self.weight) or self.weight < 0.0:
            raise CausalModelError("causal learning evidence weight must be finite and non-negative")
        _unique(self.source_variable_refs, "causal learning variable sources")
        _unique(self.source_event_refs, "causal learning event sources")
        _unique(self.proof_step_refs, "causal learning proof steps")
        _unique(self.intervention_support_refs, "causal learning interventions")
        _unique(self.mechanism_support_refs, "causal learning mechanism support")
        _unique(self.counterexample_refs, "causal learning counterexamples")
        _unique(self.source_lineage_refs, "causal learning source lineages")


@dataclass(frozen=True, slots=True)
class CausalQueryRequestV351:
    query_ref: str
    target_variable_ref: str
    query_kind: str  # why | why_not | what_if | cause_of | effect_of
    source_variable_ref: str = ""
    contrast_value_key: str = ""
    intervention: InterventionContext | None = None

    def __post_init__(self) -> None:
        if not self.query_ref or not self.target_variable_ref:
            raise CausalModelError("causal query requires query and target variable refs")
        allowed = {"why", "why_not", "what_if", "cause_of", "effect_of"}
        if self.query_kind not in allowed:
            raise CausalModelError("causal query kind is not recognized")
        if self.query_kind == "effect_of" and not self.source_variable_ref:
            raise CausalModelError("effect_of query requires explicit source variable")
        if self.query_kind in {"what_if", "why_not"} and self.intervention is None:
            raise CausalModelError(f"{self.query_kind} query requires explicit intervention context")
        if self.query_kind == "why_not" and not self.contrast_value_key:
            raise CausalModelError("why_not query requires exact contrast value identity")


@dataclass(frozen=True, slots=True)
class CausalQueryResultV351:
    result_ref: str
    query_ref: str
    answered: bool
    explanation: CausalExplanationV351 | None
    simulation_ref: str = ""
    contrast_simulation_ref: str = ""
    proof_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.result_ref or not self.query_ref:
            raise CausalModelError("causal query result requires stable refs")
        if self.answered and (self.explanation is None or not self.simulation_ref):
            raise CausalModelError("answered causal query requires explanation and simulation identity")
        if not self.answered and self.explanation is not None:
            raise CausalModelError("unanswered causal query cannot carry a definitive explanation")
        _unique(self.proof_refs, "causal query result proofs")
        _unique(self.frontier_refs, "causal query result frontiers")


def _unique(values: Iterable[Any], label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise CausalModelError(f"{label} must be unique")


__all__ = [
    "CausalExplanationV351", "CausalLearningEvidenceV351", "CausalMechanismEdgeV351",
    "CausalMechanismGraph", "CausalModelError", "CausalProofStepV351", "CausalProofV351",
    "CausalQueryRequestV351", "CausalQueryResultV351", "CausalSimulationBranchV351",
    "CausalSimulationResultV351", "CausalVariable", "ContextSemantics", "CounterfactualContext",
    "ExogenousAssumptionV351", "InterventionAssignmentV351", "InterventionContext", "SimulationBudgetV351",
]
