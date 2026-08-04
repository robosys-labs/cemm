"""Frozen runtime configuration and ABI registry.

This module owns ``ABIRegistry`` and ``RuntimeConfig`` per the stable interface
map in the master roadmap. The release configuration is frozen and bounded; no
active release test may use skip or xfail markers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ABIRegistry:
    """Active ABI versions for the six-phase semantic kernel."""

    contribution: int = 1
    switch_program: int = 1
    coverage: int = 1
    phase_receipt: int = 1
    gap_receipt: int = 1
    learning_plan: int = 1
    response_meaning: int = 1
    realization_receipt: int = 1


@dataclass(frozen=True)
class RuntimeConfig:
    """Frozen, bounded runtime configuration.

    All integer bounds must be positive. The release configuration is the
    default instance; it is immutable and carries no compatibility branch.
    """

    abis: ABIRegistry = field(default_factory=ABIRegistry)
    max_input_tokens: int = 64
    max_designations_per_span: int = 8
    max_affordances_per_target: int = 4
    max_orientation_alternatives: int = 16
    max_beam_states: int = 32
    max_complete_candidates: int = 48
    max_applications: int = 24
    max_graph_depth: int = 6
    max_inference_rounds: int = 6
    max_inference_facts: int = 256
    max_inference_rules: int = 64
    max_learning_obligations: int = 1
    max_operation_reentry: int = 1

    def __post_init__(self) -> None:
        values = [v for v in vars(self).values() if isinstance(v, int)]
        if any(v <= 0 for v in values):
            raise ValueError("runtime bounds must be positive")

    @classmethod
    def release(cls) -> "RuntimeConfig":
        """Return the frozen release configuration."""
        return cls()
