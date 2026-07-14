"""Build only the base ObligationContract envelope.

Specialized Query/Write/Reaction/State/Learning builders are invoked exclusively
by OperationalContractCompiler. This builder must not duplicate their work.
"""

from __future__ import annotations

import uuid
from typing import Any

from ...types.obligation_contract import ObligationContract, SafetyContract
from ...types.operational_meaning import OperationalMeaningFrame, MeaningArbitrationResult

_FRAME_TO_OBLIGATION = {
    "profile_assertion": "store_profile",
    "concept_definition_teaching": "store_teaching",
    "world_fact_claim": "store_teaching",
    "correction": "store_correction",
    "memory_command": "memory_command",
    "command": "memory_command",
    "concept_definition_query": "answer_concept_definition",
    "self_identity_query": "answer_self_identity",
    "self_capability_query": "answer_self_capability",
    "self_knowledge_query": "answer_self_knowledge",
    "user_profile_query": "answer_user_profile",
    "clarification_request": "ask_clarification",
    "style_feedback": "apply_style_feedback",
    "response_feedback": "apply_response_feedback",
    "session_exit": "exit",
    "user_state_report": "acknowledge_emotional_context",
    "social_act": "social_reply",
    "phatic_act": "social_reply",
    "safety_candidate": "safety_refusal",
}

_FRAME_TO_MODE = {
    "profile_assertion": "confirm_write",
    "concept_definition_teaching": "confirm_write",
    "world_fact_claim": "confirm_write",
    "correction": "confirm_write",
    "memory_command": "confirm_write",
    "command": "acknowledge",
    "concept_definition_query": "answer",
    "self_identity_query": "answer",
    "self_capability_query": "answer",
    "self_knowledge_query": "answer",
    "user_profile_query": "answer",
    "clarification_request": "clarify",
    "style_feedback": "acknowledge",
    "response_feedback": "acknowledge",
    "session_exit": "exit",
    "user_state_report": "acknowledge",
    "social_act": "social",
    "phatic_act": "social",
    "safety_candidate": "refuse",
}


class ObligationContractBuilder:
    def build(
        self,
        frames: list[OperationalMeaningFrame],
        arbitration: MeaningArbitrationResult,
        effects: list[Any] | None = None,
        safety_frame: Any | None = None,
        budget_decision: Any | None = None,
    ) -> ObligationContract:
        if not frames:
            return self._empty_contract()
        primary_id = arbitration.selected_frame_ids[0] if arbitration.selected_frame_ids else frames[0].frame_id
        primary = next((frame for frame in frames if frame.frame_id == primary_id), frames[0])
        children = arbitration.child_frame_ids or [frame.frame_id for frame in frames if frame.frame_id != primary.frame_id]
        safety = self._safety_contract(primary, safety_frame)
        blocked_by: list[str] = []
        obligation_kind = _FRAME_TO_OBLIGATION.get(primary.frame_type, "social_reply")
        response_mode = _FRAME_TO_MODE.get(primary.frame_type, "social")
        if safety is not None and safety.safety_kind != "none" and primary.frame_type != "safety_candidate":
            blocked_by.append("safety_preemption")
            obligation_kind = "safety_refusal"
            response_mode = "refuse"
        return ObligationContract(
            contract_id=f"oc_{uuid.uuid4().hex[:12]}",
            primary_meaning_frame_id=primary.frame_id,
            child_meaning_frame_ids=children,
            obligation_kind=obligation_kind,
            response_mode=response_mode,
            safety_policy=safety.safety_kind if safety else "none",
            safety_contract=safety,
            blocked_by=blocked_by,
            confidence=primary.confidence,
            diagnostics={
                "primary_frame_type": primary.frame_type,
                "target_scope": primary.target_scope,
                "persistence_policy": primary.persistence_policy,
                "arbitration_reason": arbitration.arbitration_reason,
                "contract_authority": "operational_contract_compiler",
            },
        )

    @staticmethod
    def _safety_contract(frame: OperationalMeaningFrame, safety_frame: Any | None) -> SafetyContract | None:
        if frame.frame_type == "safety_candidate":
            return SafetyContract(
                safety_kind="refusal",
                refusal_reason="safety_candidate_detected",
                risk_level=frame.confidence,
                source_refs=list(frame.source_refs),
            )
        if safety_frame is None:
            return None
        category = str(getattr(safety_frame, "category", "") or getattr(safety_frame, "risk_type", "") or "").lower()
        severity = str(getattr(safety_frame, "severity", "") or getattr(safety_frame, "risk_level", "") or "").lower()
        if not category or category in {"none", "safe", "low"}:
            return None
        try:
            risk_level = float(getattr(safety_frame, "risk_level", 0.5) or 0.5)
        except (TypeError, ValueError):
            risk_level = 0.5
        return SafetyContract(
            safety_kind="refusal",
            refusal_reason=f"safety:{category}",
            risk_level=risk_level,
            requires_human_confirmation=severity in {"high", "critical"},
            source_refs=list(frame.source_refs),
        )

    @staticmethod
    def _empty_contract() -> ObligationContract:
        return ObligationContract(
            contract_id=f"oc_{uuid.uuid4().hex[:12]}",
            primary_meaning_frame_id="",
            obligation_kind="abstain",
            response_mode="abstain",
            confidence=0.3,
            diagnostics={"reason": "no_meaning_frames"},
        )
