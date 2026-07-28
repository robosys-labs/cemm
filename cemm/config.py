"""Runtime limits and immutable policy thresholds for CEMM."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    settler_posterior_threshold: float = 0.48
    settler_margin_threshold: float = 0.06
    # Composition scores aggregate bounded, independently reviewed evidence.
    # Calibrate them before posterior normalisation, while retaining a raw
    # evidence-gap gate so calibration cannot turn near-tied polysemy into a
    # settled meaning.
    settler_score_temperature: float = 0.4
    settler_score_margin_threshold: float = 0.25
    settler_rounds: int = 4
    settler_top_k: int = 10
    rule_evidence_threshold: int = 2
    retrieval_max_seed_facts: int = 96
    retrieval_max_rules: int = 48
    retrieval_max_depth: int = 4
    inference_max_rounds: int = 8
    inference_max_facts: int = 256
    inference_timeout_seconds: float = 5.0
    query_min_answer_coverage: float = 1.0
    state_support_threshold: float = 0.67
    state_projection_cache_limit: int = 256
    capability_dependency_max_depth: int = 12
    form_max_input_chars: int = 8192
    form_max_normalizations: int = 8
    form_max_grounding_hypotheses: int = 16
    form_max_span_candidates: int = 128
    form_max_construction_matches: int = 32
    form_max_semantic_hypotheses: int = 8
    form_max_semantic_candidates: int = 48

    # Bounded recursive atomic composition.
    composition_max_scope_units: int = 16
    composition_max_scopes_per_hypothesis: int = 96
    composition_max_graphlets_per_cell: int = 8
    composition_max_total_graphlets: int = 48
    composition_max_depth: int = 6
    composition_state_budget: int = 12000
    composition_max_partial_gaps: int = 24

    # Exact semantic description and proof traversal.
    description_max_depth: int = 3
    description_max_facts: int = 48
    description_max_designations: int = 8
    description_max_frames: int = 8
    proof_max_nodes: int = 96
    proof_max_sources: int = 16
    dialogue_max_verified_focus: int = 8

    workspace_top_k: int = 32
    workspace_max_required: int = 48
    salience_decay: float = 0.55
    max_operation_reentry: int = 1
    epistemic_default_claim_confidence: float = 0.95
    commit_cas_required: bool = True
    persist_normal_frontiers: bool = True
    persist_common_ground: bool = True
    model_cache_limit: int = 8
    structured_net_seed: int = 41
    rule_net_seed: int = 73
    classifier_seed: int = 11
    reviewed_acquisition_enabled: bool = True

    def __post_init__(self) -> None:
        bounded_positive = {
            "composition_max_scope_units": self.composition_max_scope_units,
            "composition_max_scopes_per_hypothesis": self.composition_max_scopes_per_hypothesis,
            "composition_max_graphlets_per_cell": self.composition_max_graphlets_per_cell,
            "composition_max_total_graphlets": self.composition_max_total_graphlets,
            "composition_max_depth": self.composition_max_depth,
            "composition_state_budget": self.composition_state_budget,
            "composition_max_partial_gaps": self.composition_max_partial_gaps,
            "description_max_depth": self.description_max_depth,
            "description_max_facts": self.description_max_facts,
            "description_max_designations": self.description_max_designations,
            "description_max_frames": self.description_max_frames,
            "proof_max_nodes": self.proof_max_nodes,
            "proof_max_sources": self.proof_max_sources,
            "dialogue_max_verified_focus": self.dialogue_max_verified_focus,
        }
        invalid = [name for name, value in bounded_positive.items() if not isinstance(value, int) or value <= 0]
        if invalid:
            raise ValueError("invalid bounded runtime configuration: " + ",".join(sorted(invalid)))
        if (
            not isinstance(self.settler_score_temperature, (int, float))
            or self.settler_score_temperature <= 0
            or not isinstance(self.settler_score_margin_threshold, (int, float))
            or self.settler_score_margin_threshold <= 0
        ):
            raise ValueError("invalid semantic-settler score calibration")
        if self.composition_max_depth > 6:
            raise ValueError("composition depth exceeds PropositionGraph ABI")
        if self.composition_max_total_graphlets > self.composition_state_budget:
            raise ValueError("graphlet bound exceeds composition state budget")
        if self.description_max_facts > self.inference_max_facts:
            raise ValueError("description fact bound exceeds inference bound")
