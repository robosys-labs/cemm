"""DEPRECATED: Replaced by cemm.kernel.execution.goal_arbiter.GoalArbiter + cemm.kernel.model.goal.GoalRecord.

This module is retained for legacy compatibility only. The v3.4 canonical
path uses GoalArbiter for goal derivation and arbitration. Do not use for
new code — redirect to the v3.4 goal/plan pipeline.

ObligationFrame — the output of the SemanticObligationScheduler.

An ObligationFrame is the authoritative scheduling decision for one turn.
It specifies what the runtime must do (obligation_kind), how to respond
(response_mode), what evidence is needed (evidence_policy), what memory
writes are allowed (write_policy), and which slots must be filled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


OBLIGATION_KINDS = frozenset({
    "answer_concept",
    "answer_relation",
    "answer_self_model",
    "answer_user_profile",
    "continue_teaching",
    "store_patch",
    "ask_clarification",
    "abstain_policy",
    "repair",
    "social_reply",
    "acknowledge_emotional_context",
    "exit",
    "safety_refusal",
})


@dataclass
class ObligationFrame:
    primary_instruction_id: str
    obligation_kind: str
    response_mode: str
    evidence_policy: str = "none"
    write_policy: str = "none"
    required_slots: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    child_obligations: list[str] = field(default_factory=list)
    suppressed_obligations: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    context: dict[str, Any] = field(default_factory=dict)
