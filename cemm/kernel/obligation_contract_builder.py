"""ObligationContractBuilder — build ObligationContract from meaning frames.

Consumes selected OperationalMeaningFrames, OperationalEffects,
StateTransmutationFrames, safety frame, and budget decision to produce
an ObligationContract.

This replaces the broad instruction-kind routing in SemanticObligationScheduler
with explicit per-meaning contract compilation.
"""

from __future__ import annotations

import uuid
from typing import Any

from ..types.obligation_contract import (
    ObligationContract,
    QueryContract,
    WriteContract,
    ReactionContract,
    SafetyContract,
)
from ..types.operational_meaning import (
    OperationalMeaningFrame,
    OperationalEffect,
    MeaningArbitrationResult,
    is_writable_frame,
)


_FRAME_TYPE_TO_OBLIGATION: dict[str, str] = {
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

_FRAME_TYPE_TO_RESPONSE_MODE: dict[str, str] = {
    "profile_assertion": "confirm_write",
    "concept_definition_teaching": "confirm_write",
    "world_fact_claim": "confirm_write",
    "correction": "confirm_write",
    "memory_command": "confirm_write",
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
    "command": "acknowledge",
    "safety_candidate": "refuse",
}


class ObligationContractBuilder:
    """Build ObligationContract from selected meaning frames and effects."""

    def build(
        self,
        frames: list[OperationalMeaningFrame],
        arbitration: MeaningArbitrationResult,
        effects: list[OperationalEffect] | None = None,
        safety_frame: Any | None = None,
        budget_decision: Any | None = None,
    ) -> ObligationContract:
        if not frames:
            return self._empty_contract()

        primary_id = arbitration.selected_frame_ids[0] if arbitration.selected_frame_ids else frames[0].frame_id
        primary = next((f for f in frames if f.frame_id == primary_id), frames[0])
        child_ids = arbitration.child_frame_ids or [f.frame_id for f in frames if f.frame_id != primary.frame_id]

        obligation_kind = _FRAME_TYPE_TO_OBLIGATION.get(primary.frame_type, "social_reply")
        response_mode = _FRAME_TYPE_TO_RESPONSE_MODE.get(primary.frame_type, "social")

        query_contract = self._build_query_contract(primary)
        write_contract = self._build_write_contract(primary)
        reaction_contract = self._build_reaction_contract(primary, effects)
        safety_contract = self._build_safety_contract(primary, safety_frame)

        blocked_by: list[str] = []
        if safety_contract is not None and safety_contract.safety_kind != "none":
            if primary.frame_type != "safety_candidate":
                blocked_by.append("safety_preemption")
                obligation_kind = "safety_refusal"
                response_mode = "refuse"

        return ObligationContract(
            contract_id=f"oc_{uuid.uuid4().hex[:12]}",
            primary_meaning_frame_id=primary.frame_id,
            child_meaning_frame_ids=child_ids,
            obligation_kind=obligation_kind,
            response_mode=response_mode,
            query_policy=primary.query_policy if query_contract else "none",
            write_policy="patch_only" if write_contract and write_contract.is_writable else "none",
            reaction_policy=reaction_contract.reaction_kind if reaction_contract else "none",
            safety_policy=safety_contract.safety_kind if safety_contract else "none",
            query_contract=query_contract,
            write_contract=write_contract,
            reaction_contract=reaction_contract,
            safety_contract=safety_contract,
            blocked_by=blocked_by,
            confidence=primary.confidence,
            diagnostics={
                "primary_frame_type": primary.frame_type,
                "target_scope": primary.target_scope,
                "persistence_policy": primary.persistence_policy,
                "arbitration_reason": arbitration.arbitration_reason,
            },
        )

    def _build_query_contract(self, frame: OperationalMeaningFrame) -> QueryContract | None:
        if not frame.is_query:
            return None

        query_kind_map = {
            "concept_definition_query": "concept_definition",
            "self_identity_query": "self_identity",
            "self_capability_query": "self_capability",
            "self_knowledge_query": "self_knowledge",
            "user_profile_query": "profile_dimension",
        }
        query_kind = query_kind_map.get(frame.frame_type, "relation_lookup")
        subject_concept_id = frame.features.get("subject_concept_id", "")
        object_concept_id = frame.features.get("object_concept_id", "")
        subject_entity_id = frame.features.get("subject_entity_id", "")
        if frame.frame_type == "concept_definition_query":
            subject_concept_id = object_concept_id or subject_concept_id
            object_concept_id = ""
        if frame.frame_type == "user_profile_query":
            subject_entity_id = subject_entity_id or "user"

        return QueryContract(
            query_kind=query_kind,
            target_scope=frame.target_scope,
            subject_concept_id=subject_concept_id,
            subject_entity_id=subject_entity_id,
            relation_key=self._contract_relation_key(frame),
            relation_family=frame.relation_family,
            dimension=frame.dimension,
            object_concept_id=object_concept_id,
            object_entity_id=frame.features.get("object_entity_id", ""),
            evidence_policy="required",
            ambiguity_policy="abstain",
            features=dict(frame.features),
        )

    @staticmethod
    def _contract_relation_key(frame: OperationalMeaningFrame) -> str:
        if frame.frame_type == "concept_definition_query" and frame.relation_key in ("", "asks_about"):
            return "is_a"
        if frame.frame_type == "user_profile_query" and frame.relation_key in ("", "asks_about"):
            return "has_property"
        if frame.frame_type == "self_identity_query":
            return "answers_identity_as"
        if frame.frame_type == "self_capability_query":
            return "capability"
        if frame.frame_type == "self_knowledge_query":
            return "knows_about"
        return frame.relation_key

    def _build_write_contract(self, frame: OperationalMeaningFrame) -> WriteContract | None:
        if not is_writable_frame(frame):
            return None

        write_kind_map = {
            "profile_assertion": "profile_upsert",
            "concept_definition_teaching": "relation_upsert",
            "world_fact_claim": "relation_upsert",
            "correction": "correction_apply",
            "memory_command": "memory_command",
            "command": "memory_command",
        }
        write_kind = write_kind_map.get(frame.frame_type, "relation_upsert")

        required_features = []
        if frame.dimension:
            required_features.append(frame.dimension)
        if frame.features.get("property_dimension"):
            required_features.append(frame.features["property_dimension"])

        return WriteContract(
            write_kind=write_kind,
            target=frame.target_scope,
            persistence_policy=frame.persistence_policy,
            allowed_patch_targets=["concept_lattice"],
            required_features=required_features,
            required_evidence_refs=list(frame.evidence_refs),
            permission_scope=frame.target_scope,
            commit_policy="commit_if_valid",
            features=dict(frame.features),
        )

    def _build_reaction_contract(
        self,
        frame: OperationalMeaningFrame,
        effects: list[OperationalEffect] | None,
    ) -> ReactionContract | None:
        if frame.frame_type not in ("style_feedback", "response_feedback", "user_state_report"):
            return None

        style_delta: dict[str, float] = {}
        if frame.frame_type in ("style_feedback", "response_feedback"):
            dimension = frame.dimension or frame.features.get("dimension", "")
            if dimension in ("verbosity", "response_detail", "detail"):
                style_delta["detail"] = -0.15
                style_delta["terseness"] = 0.1
            elif dimension in ("naturalness", "warmth"):
                style_delta["warmth"] = 0.1
                style_delta["formality"] = -0.1
            elif dimension in ("directness",):
                style_delta["directness"] = 0.1

        repair_debt = 0.0
        if effects:
            for effect in effects:
                if effect.effect_type == "increase_repair_debt":
                    repair_debt += effect.strength
                elif effect.effect_type == "decrease_response_detail":
                    style_delta["detail"] = min(style_delta.get("detail", 0.0) - effect.strength, 0.0)

        reaction_kind = "style_adjust" if style_delta else "repair_debt_update"
        if frame.frame_type == "user_state_report":
            reaction_kind = "style_adjust"
            affect = frame.features.get("affect", "")
            if affect in ("positive", "great", "good"):
                style_delta["warmth"] = 0.05

        return ReactionContract(
            reaction_kind=reaction_kind,
            target=frame.target_scope,
            style_delta=style_delta,
            repair_debt_delta=repair_debt,
            persistence_policy="session_state",
            source_refs=list(frame.source_refs),
        )

    def _build_safety_contract(
        self,
        frame: OperationalMeaningFrame,
        safety_frame: Any | None,
    ) -> SafetyContract | None:
        if frame.frame_type == "safety_candidate":
            return SafetyContract(
                safety_kind="refusal",
                refusal_reason="safety_candidate_detected",
                risk_level=frame.confidence,
                source_refs=list(frame.source_refs),
            )
        if safety_frame is not None:
            category = (getattr(safety_frame, "category", "") or getattr(safety_frame, "risk_type", "") or "").lower()
            severity = (getattr(safety_frame, "severity", "") or getattr(safety_frame, "risk_level", "") or "").lower()
            if category and category not in {"none", "safe", "low"}:
                return SafetyContract(
                    safety_kind="refusal",
                    refusal_reason=f"safety:{category}",
                    risk_level=float(getattr(safety_frame, "risk_level", 0.5) or 0.5),
                    requires_human_confirmation=severity in {"high", "critical"},
                    source_refs=list(frame.source_refs),
                )
        return None

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
