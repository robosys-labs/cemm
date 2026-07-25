"""Runtime limits and immutable policy thresholds for CEMM v1."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Semantic settling.
    settler_posterior_threshold: float = 0.48
    settler_margin_threshold: float = 0.06
    settler_rounds: int = 4
    settler_top_k: int = 10

    # Reviewed rule induction.
    rule_evidence_threshold: int = 2

    # Sparse retrieval and inference.
    retrieval_max_seed_facts: int = 96
    retrieval_max_rules: int = 48
    retrieval_max_depth: int = 4
    inference_max_rounds: int = 8
    inference_max_facts: int = 256
    inference_timeout_seconds: float = 5.0
    query_min_answer_coverage: float = 1.0

    # Recursive state/capability projection.
    state_support_threshold: float = 0.67
    state_projection_cache_limit: int = 256
    capability_dependency_max_depth: int = 12
    capability_unknown_score: float = 0.0

    # Active workspace and bounded re-entry.
    workspace_top_k: int = 32
    workspace_max_required: int = 48
    salience_decay: float = 0.55
    max_operation_reentry: int = 1

    # Admission/commit policy.
    epistemic_default_claim_confidence: float = 0.95
    commit_cas_required: bool = True
    persist_normal_frontiers: bool = True
    persist_common_ground: bool = True

    # Models/artifacts.
    model_cache_limit: int = 8
    structured_net_seed: int = 41
    rule_net_seed: int = 73
    classifier_seed: int = 11

    # Explicit reviewed acquisition only. Unknown ordinary text never mints atoms.
    reviewed_acquisition_enabled: bool = True
