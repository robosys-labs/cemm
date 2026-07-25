"""Configurable thresholds for CEMM v1."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    settler_posterior_threshold: float = 0.48
    settler_margin_threshold: float = 0.06
    settler_rounds: int = 4
    settler_top_k: int = 10
    rule_evidence_threshold: int = 2
    salience_decay: float = 0.55
    workspace_top_k: int = 24
    inference_max_rounds: int = 8
    inference_max_facts: int = 200
    inference_timeout_seconds: float = 30.0
    state_support_threshold: float = 0.67
    state_projection_cache_limit: int = 256
    query_min_answer_coverage: float = 1.0
    epistemic_default_claim_confidence: float = 0.95
    model_cache_limit: int = 8
    structured_net_seed: int = 41
    rule_net_seed: int = 73
    classifier_seed: int = 11
    # Explicit reviewed acquisition workflow only; parsing remains pure.
    autonomous_acquisition: bool = True
