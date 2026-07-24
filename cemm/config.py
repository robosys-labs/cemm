"""Configurable thresholds for CEMM v1.

All thresholds that were hardcoded magic numbers in v4 are centralized here.
This fixes weakness #4 (hardcoded thresholds).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Semantic settler
    settler_posterior_threshold: float = 0.48
    settler_margin_threshold: float = 0.06
    settler_rounds: int = 4
    settler_top_k: int = 10

    # Rule learning
    rule_evidence_threshold: int = 2

    # Salience / discourse
    salience_decay: float = 0.55

    # Workspace
    workspace_top_k: int = 24

    # Inference (weakness #6 fix: timeout)
    inference_max_rounds: int = 8
    inference_max_facts: int = 200
    inference_timeout_seconds: float = 30.0

    # Model cache (weakness #10 fix: bounded cache)
    model_cache_limit: int = 8

    # Neural seeds
    structured_net_seed: int = 41
    rule_net_seed: int = 73
    classifier_seed: int = 11

    # Autonomous acquisition (weakness #11 fix)
    autonomous_acquisition: bool = True
