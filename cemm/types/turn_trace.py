"""Per-turn debug trace for the CEMM pipeline.

Captures the full decision chain for a single turn:
raw_input → normalized_forms → matched_aliases → uol_frames →
conversation_act_packet → claim_candidates → retrieval_allowed →
selected_claim_ids → decision_action → response_mode → operator →
template_key → memory_write_attempt.

This is distinct from the operator-scoped Trace (which audits action
execution). TurnTrace is a diagnostic tool for understanding why the
pipeline classified and routed a turn the way it did.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnTrace:
    """Granular per-turn debug trace for pipeline diagnostics."""
    # ── Input ─────────────────────────────────────────────────────
    raw_input: str = ""
    normalized_forms: list[str] = field(default_factory=list)
    turn_index: int = 0
    context_id: str = ""

    # ── Semantic interpretation ───────────────────────────────────
    matched_aliases: list[str] = field(default_factory=list)
    uol_frame_keys: list[str] = field(default_factory=list)
    uol_atom_count: int = 0
    semantic_cluster_key: str = ""
    observation_speech_act: str = ""

    # ── Conversation act packet ───────────────────────────────────
    primary_act_type: str = ""
    secondary_act_types: list[str] = field(default_factory=list)
    discourse_relation: str = "none"
    pending_question_resolved: str = ""
    compositional_intent: dict[str, Any] = field(default_factory=dict)

    # ── Retrieval ─────────────────────────────────────────────────
    retrieval_allowed: bool = False
    claim_candidates: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)

    # ── Decision ──────────────────────────────────────────────────
    decision_action_kind: str = ""
    response_mode: str = ""
    decision_reason: str = ""
    decision_confidence: float = 0.0

    # ── Memory ────────────────────────────────────────────────────
    memory_write_attempted: bool = False
    memory_write_allowed: bool = False

    # ── Timing ────────────────────────────────────────────────────
    cost_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a flat dict for logging/JSON export."""
        return {
            "raw_input": self.raw_input,
            "normalized_forms": self.normalized_forms,
            "turn_index": self.turn_index,
            "context_id": self.context_id,
            "matched_aliases": self.matched_aliases,
            "uol_frame_keys": self.uol_frame_keys,
            "uol_atom_count": self.uol_atom_count,
            "semantic_cluster_key": self.semantic_cluster_key,
            "observation_speech_act": self.observation_speech_act,
            "primary_act_type": self.primary_act_type,
            "secondary_act_types": self.secondary_act_types,
            "discourse_relation": self.discourse_relation,
            "pending_question_resolved": self.pending_question_resolved,
            "compositional_intent": self.compositional_intent,
            "retrieval_allowed": self.retrieval_allowed,
            "claim_candidates": self.claim_candidates,
            "selected_claim_ids": self.selected_claim_ids,
            "selected_model_ids": self.selected_model_ids,
            "decision_action_kind": self.decision_action_kind,
            "response_mode": self.response_mode,
            "decision_reason": self.decision_reason,
            "decision_confidence": self.decision_confidence,
            "memory_write_attempted": self.memory_write_attempted,
            "memory_write_allowed": self.memory_write_allowed,
            "cost_ms": self.cost_ms,
        }
