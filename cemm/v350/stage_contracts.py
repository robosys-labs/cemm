"""Canonical v3.5.1 Stage-0..22 ABI and persistence/effect contracts.

This is the machine-readable bridge between CORE_LOOP.md and RUNTIME_PLAN.md.
It intentionally contains no UOL-era aliases.  A stage contract describes logical
cognitive ownership; it is not a database-transaction plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .runtime_generations import GenerationDomain
from .schema.model import semantic_fingerprint


class CoreStage(int, Enum):
    ORIENT_AND_PIN_SEMANTIC_BRAIN = 0
    OBSERVE_MULTIMODAL_EVIDENCE = 1
    ENCODE_FORM_AND_SENSOR_EVIDENCE = 2
    ACTIVATE_AND_GROUND_REFERENTS = 3
    PROJECT_ENTITLED_STATE_SPACES = 4
    COMPILE_CANDIDATES_TO_CSIR = 5
    RUN_RECURRENT_MEANING_DYNAMICS = 6
    STABILIZE_SEMANTIC_ATTRACTORS = 7
    BUILD_DISCOURSE_PROPOSITION_EVENT_AND_QUERY_STRUCTURES = 8
    PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORLD_BELIEF = 9
    QUERY_AND_EXPLAIN_FROM_GROUNDED_WORLD_MODEL = 10
    CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING = 11
    SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS = 12
    COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS = 13
    PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE = 14
    DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS = 15
    PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE = 16
    ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR = 17
    CONSTRUCT_RESPONSE_CSIR = 18
    REALIZE_TARGET_LANGUAGE_OR_MODALITY = 19
    VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION = 20
    COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND = 21
    CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE = 22

    def __str__(self) -> str:
        return self.name


class PersistenceClass(str, Enum):
    NONE = "none"
    WORKSPACE = "workspace"
    DURABLE_COMMIT = "durable_commit"
    EFFECT_JOURNAL = "effect_journal"
    OUTPUT_DISCOURSE = "output_discourse"
    CONSOLIDATION = "consolidation"
    OPTIONAL_AUDIT = "optional_audit"


class EffectKind(str, Enum):
    DURABLE_PERSISTENCE = "durable_persistence"
    EXTERNAL_OPERATION = "external_operation"
    PROTECTED_DISCLOSURE = "protected_disclosure"
    EXTERNAL_EMISSION = "external_emission"


@dataclass(frozen=True, slots=True)
class StageContract:
    stage: CoreStage
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    produced_outputs: tuple[str, ...]
    required_outputs_on_performed: tuple[str, ...]
    persistence: PersistenceClass
    allowed_generation_changes: frozenset[GenerationDomain]
    allowed_effects: frozenset[EffectKind]
    frontier_classes: tuple[str, ...]
    budget_keys: tuple[str, ...]
    proof_requirements: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, values in (
            ("required_inputs", self.required_inputs),
            ("optional_inputs", self.optional_inputs),
            ("produced_outputs", self.produced_outputs),
            ("required_outputs_on_performed", self.required_outputs_on_performed),
            ("frontier_classes", self.frontier_classes),
            ("budget_keys", self.budget_keys),
            ("proof_requirements", self.proof_requirements),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} in {self.stage.name}")
        if not set(self.required_outputs_on_performed).issubset(self.produced_outputs):
            raise ValueError(f"required outputs not declared by {self.stage.name}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            "stage-contract-v351",
            (
                int(self.stage), self.stage.name, self.required_inputs, self.optional_inputs,
                self.produced_outputs, self.required_outputs_on_performed, self.persistence.value,
                tuple(sorted(x.value for x in self.allowed_generation_changes)),
                tuple(sorted(x.value for x in self.allowed_effects)),
                self.frontier_classes, self.budget_keys, self.proof_requirements,
            ),
            64,
        )


def _c(
    stage: CoreStage,
    inputs: Iterable[str],
    outputs: Iterable[str],
    *,
    optional: Iterable[str] = (),
    required: Iterable[str] | None = None,
    persistence: PersistenceClass = PersistenceClass.WORKSPACE,
    generations: Iterable[GenerationDomain] = (),
    effects: Iterable[EffectKind] = (),
    frontiers: Iterable[str] = (),
    budgets: Iterable[str] = (),
    proofs: Iterable[str] = (),
) -> StageContract:
    outputs = tuple(outputs)
    return StageContract(
        stage=stage,
        required_inputs=tuple(inputs),
        optional_inputs=tuple(optional),
        produced_outputs=outputs,
        required_outputs_on_performed=tuple(outputs if required is None else required),
        persistence=persistence,
        allowed_generation_changes=frozenset(generations),
        allowed_effects=frozenset(effects),
        frontier_classes=tuple(frontiers),
        budget_keys=tuple(budgets),
        proof_requirements=tuple(proofs),
    )


_CONTRACTS = (
    _c(CoreStage.ORIENT_AND_PIN_SEMANTIC_BRAIN, (),
       ("authority_snapshot", "semantic_authority_snapshot_v351", "read_generation", "kernel_semantic_abi", "participant_frame", "context_stack", "runtime_budgets"),
       persistence=PersistenceClass.NONE, frontiers=("runtime_capability", "reference_ambiguity"), proofs=("runtime_attestation",)),
    _c(CoreStage.OBSERVE_MULTIMODAL_EVIDENCE, ("participant_frame",),
       ("evidence_envelopes",), persistence=PersistenceClass.WORKSPACE, frontiers=("observation_gap",)),
    _c(CoreStage.ENCODE_FORM_AND_SENSOR_EVIDENCE, ("evidence_envelopes",),
       ("evidence_lattice", "language_decision_evidence", "sensor_feature_candidates"),
       persistence=PersistenceClass.WORKSPACE, frontiers=("form_gap", "sensor_gap"), budgets=("inference_steps",)),
    _c(CoreStage.ACTIVATE_AND_GROUND_REFERENTS, ("evidence_lattice", "participant_frame"),
       ("grounding_candidates", "identity_coreference_trace"), persistence=PersistenceClass.WORKSPACE,
       frontiers=("grounding_ambiguity", "reference_ambiguity"), budgets=("inference_steps",), proofs=("grounding_evidence_lineage",)),
    _c(CoreStage.PROJECT_ENTITLED_STATE_SPACES, ("grounding_candidates", "read_generation"),
       ("referent_projections", "state_space_projections", "semantic_closure_candidates"),
       persistence=PersistenceClass.WORKSPACE, frontiers=("type_closure_gap", "state_projection_gap"), proofs=("exact_type_closure",)),
    _c(CoreStage.COMPILE_CANDIDATES_TO_CSIR, ("evidence_lattice", "grounding_candidates", "referent_projections", "authority_snapshot", "semantic_authority_snapshot_v351", "kernel_semantic_abi"),
       ("csir_candidates", "closure_proofs", "hard_constraint_trace"), persistence=PersistenceClass.WORKSPACE,
       frontiers=("semantic_learning", "runtime_capability"), budgets=("inference_steps",), proofs=("kernel_semantic_abi", "canonical_normal_form", "exact_definition_closure", "hard_constraint_trace")),
    _c(CoreStage.RUN_RECURRENT_MEANING_DYNAMICS, ("csir_candidates", "authority_snapshot", "semantic_authority_snapshot_v351"),
       ("activation_graph", "activation_trace"), persistence=PersistenceClass.WORKSPACE,
       frontiers=("non_convergence", "runtime_capability"), budgets=("inference_steps",), proofs=("hard_semantic_mask",)),
    _c(CoreStage.STABILIZE_SEMANTIC_ATTRACTORS, ("activation_graph", "activation_trace", "semantic_authority_snapshot_v351"),
       ("semantic_attractors", "partial_meaning", "open_variables", "convergence_assessment"),
       persistence=PersistenceClass.WORKSPACE, frontiers=("non_convergence", "semantic_ambiguity"), budgets=("inference_steps",), proofs=("canonical_semantic_equivalence",)),
    _c(CoreStage.BUILD_DISCOURSE_PROPOSITION_EVENT_AND_QUERY_STRUCTURES, ("semantic_attractors", "participant_frame", "grounding_candidates", "evidence_envelopes", "semantic_authority_snapshot_v351"),
       ("discourse_structures", "propositions", "claims", "events", "queries", "corrections", "commitments"),
       persistence=PersistenceClass.WORKSPACE, frontiers=("discourse_gap",), proofs=("selected_attractor_lineage",)),
    _c(CoreStage.PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORLD_BELIEF, ("claims", "events", "propositions", "corrections", "evidence_envelopes"),
       ("epistemic_placement", "working_belief_delta", "admission_decisions"), persistence=PersistenceClass.WORKSPACE,
       frontiers=("epistemic_gap", "policy_block"), proofs=("source_context_permission_lineage",)),
    _c(CoreStage.QUERY_AND_EXPLAIN_FROM_GROUNDED_WORLD_MODEL, ("queries", "epistemic_placement", "working_belief_delta"),
       ("query_results", "explanation_proofs"), persistence=PersistenceClass.WORKSPACE,
       frontiers=("query_gap", "reference_ambiguity"), proofs=("proof_path_retrieval",)),
    _c(CoreStage.CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING, ("semantic_attractors",),
       ("prediction_errors", "learning_frontiers", "learning_candidate_work", "learning_question_candidates"),
       persistence=PersistenceClass.WORKSPACE, frontiers=("semantic_learning",), budgets=("learning_frontiers",), proofs=("evidence_dependence_lineage",)),
    _c(CoreStage.SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS, ("events", "epistemic_placement"),
       ("transition_previews", "counterfactual_branches", "causal_proofs"), persistence=PersistenceClass.WORKSPACE,
       frontiers=("causal_gap",), budgets=("transition_plans",), proofs=("mechanism_pins",)),
    _c(CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS,
       ("admission_decisions", "working_belief_delta"),
       ("commit_receipts", "committed_read_generation"), optional=("learning_candidate_work", "learning_frontiers", "discourse_structures", "query_results"), persistence=PersistenceClass.DURABLE_COMMIT,
       generations=(GenerationDomain.WORLD, GenerationDomain.DISCOURSE, GenerationDomain.AUDIT),
       effects=(EffectKind.DURABLE_PERSISTENCE,), frontiers=("commit_conflict", "permission_block"), proofs=("effect_authorization", "cas_preconditions")),
    _c(CoreStage.PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE, ("commit_receipts",),
       ("capability_deltas", "impact_assessments", "affect_estimates", "significance_assessments"),
       persistence=PersistenceClass.OPTIONAL_AUDIT, generations=(GenerationDomain.AUDIT,), effects=(EffectKind.DURABLE_PERSISTENCE,), frontiers=("impact_gap",), proofs=("impact_mechanism_lineage",)),
    _c(CoreStage.DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS,
       (), ("goal_candidates", "goal_decision"), optional=("query_results", "learning_frontiers", "significance_assessments", "epistemic_placement"), persistence=PersistenceClass.OPTIONAL_AUDIT,
       generations=(GenerationDomain.AUDIT,), effects=(EffectKind.DURABLE_PERSISTENCE,), frontiers=("goal_conflict", "policy_block"), proofs=("authorization_before_utility",)),
    _c(CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE, ("goal_decision",),
       ("plans", "effect_authorizations", "operation_journals", "operation_observations"),
       persistence=PersistenceClass.EFFECT_JOURNAL, generations=(GenerationDomain.EFFECT_JOURNAL, GenerationDomain.AUDIT),
       effects=(EffectKind.DURABLE_PERSISTENCE, EffectKind.EXTERNAL_OPERATION,), frontiers=("permission_block", "operation_outcome_unknown"), budgets=("external_operations",), proofs=("effect_authorization", "idempotency_identity")),
    _c(CoreStage.ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR, ("operation_observations",),
       ("outcome_reconciliations", "operation_prediction_errors"), persistence=PersistenceClass.EFFECT_JOURNAL,
       generations=(GenerationDomain.EFFECT_JOURNAL, GenerationDomain.AUDIT), effects=(EffectKind.DURABLE_PERSISTENCE,), frontiers=("operation_outcome_unknown", "temporal_replay"), proofs=("operation_observation_lineage",)),
    _c(CoreStage.CONSTRUCT_RESPONSE_CSIR, ("goal_decision",),
       ("response_csir_candidates", "response_decision"), optional=("query_results", "epistemic_placement", "learning_frontiers"), persistence=PersistenceClass.OPTIONAL_AUDIT,
       generations=(GenerationDomain.AUDIT,), effects=(EffectKind.DURABLE_PERSISTENCE,), frontiers=("response_gap",), proofs=("all_and_only_authorized_meaning",)),
    _c(CoreStage.REALIZE_TARGET_LANGUAGE_OR_MODALITY, ("response_decision", "authority_snapshot"),
       ("realization_plan", "surface_candidates", "realization_proofs"), persistence=PersistenceClass.OPTIONAL_AUDIT,
       generations=(GenerationDomain.AUDIT,), effects=(EffectKind.DURABLE_PERSISTENCE,), frontiers=("realization_gap",), budgets=("realization_candidates",), proofs=("proof_carrying_realization",)),
    _c(CoreStage.VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION,
       ("response_decision", "surface_candidates", "realization_proofs"),
       ("semantic_preservation_assessments", "emission_authorization", "emission_observation"),
       required=("semantic_preservation_assessments", "emission_authorization"),
       persistence=PersistenceClass.EFFECT_JOURNAL, generations=(GenerationDomain.EFFECT_JOURNAL, GenerationDomain.AUDIT),
       effects=(EffectKind.DURABLE_PERSISTENCE, EffectKind.PROTECTED_DISCLOSURE, EffectKind.EXTERNAL_EMISSION), frontiers=("realization_gap", "permission_block"),
       proofs=("semantic_preservation_proof", "effect_authorization")),
    _c(CoreStage.COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND, ("emission_observation",),
       ("output_discourse_commit", "common_ground_proposal"), persistence=PersistenceClass.OUTPUT_DISCOURSE,
       generations=(GenerationDomain.DISCOURSE, GenerationDomain.AUDIT), effects=(EffectKind.DURABLE_PERSISTENCE,), frontiers=("common_ground_gap",), proofs=("observed_emission",)),
    _c(CoreStage.CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE, (),
       ("cycle_completion_status", "invalidation_set", "replay_requirements", "consolidation_results", "final_cycle_summary"),
       persistence=PersistenceClass.CONSOLIDATION,
       generations=(GenerationDomain.WORLD, GenerationDomain.DISCOURSE, GenerationDomain.AUDIT),
       effects=(EffectKind.DURABLE_PERSISTENCE,),
       frontiers=("temporal_replay", "budget_incomplete"), proofs=("whole_cycle_lineage", "effect_authorization")),
)


CONTRACT_BY_STAGE: Mapping[CoreStage, StageContract] = {c.stage: c for c in _CONTRACTS}


def canonical_stage_contracts() -> tuple[StageContract, ...]:
    validate_stage_contracts(_CONTRACTS)
    return _CONTRACTS


def stage_contract(stage: CoreStage | int) -> StageContract:
    return CONTRACT_BY_STAGE[stage if isinstance(stage, CoreStage) else CoreStage(stage)]


def validate_stage_contracts(contracts: Iterable[StageContract]) -> None:
    items = tuple(contracts)
    if tuple(c.stage for c in items) != tuple(CoreStage):
        raise ValueError("stage contracts must match CORE_LOOP Stage 0..22 exactly")
    old_tokens = ("UOL", "FACTOR_GRAPH", "MEANING_BUNDLE")
    for c in items:
        public_text = " ".join((c.stage.name, *c.required_inputs, *c.optional_inputs, *c.produced_outputs))
        if c.stage in {
            CoreStage.COMPILE_CANDIDATES_TO_CSIR,
            CoreStage.RUN_RECURRENT_MEANING_DYNAMICS,
            CoreStage.STABILIZE_SEMANTIC_ATTRACTORS,
            CoreStage.CONSTRUCT_RESPONSE_CSIR,
        } and any(token in public_text for token in old_tokens):
            raise ValueError(f"legacy UOL ABI leaked into {c.stage.name}")


__all__ = [
    "CONTRACT_BY_STAGE", "CoreStage", "EffectKind", "PersistenceClass",
    "StageContract", "canonical_stage_contracts", "stage_contract",
    "validate_stage_contracts",
]
