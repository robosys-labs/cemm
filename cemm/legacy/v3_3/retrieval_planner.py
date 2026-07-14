"""RetrievalPlanner — explicit retrieval plan from SituationFrame + ConversationAct.

Implements §14 from architecture.md and §8.7 from cemm_foundational_fixes.md.

Do not let ConversationAct.requires_evidence directly control retrieval.
Create an explicit retrieval plan that considers the situation frame, safety
frame, and conversation act type.

Examples:
    "hiii" -> mode=none
    "I am fine, you?" -> mode=none
    "what can you do?" -> mode=self_knowledge
    "who is Obama?" -> mode=world_memory, freshness_required
    "Obidike is looking for my trouble" -> mode=lexeme_memory
    "what's my name?" -> mode=profile
"""

from __future__ import annotations

from typing import Any

from ...types.meaning_percept import RetrievalPlan, SituationFrame, SafetyFrame
from ...types.conversation_act import ConversationActPacket


class RetrievalPlanner:
    """Plans retrieval based on situation and conversation act, not just requires_evidence."""

    def plan(
        self,
        conversation_act: ConversationActPacket | None = None,
        situation: SituationFrame | None = None,
        safety_frame: SafetyFrame | None = None,
        has_unknown_lexemes: bool = False,
        has_idiom_candidates: bool = False,
        act_resolution_plan: Any = None,
    ) -> RetrievalPlan:
        """Build a retrieval plan from the current turn's analysis.

        When act_resolution_plan is provided, use its retrieval_mode and
        requires_retrieval as the primary signal instead of re-deriving
        from conversation_act.act_type.
        """
        # ── ConversationAct social/creative/repair always wins ──
        # Check BEFORE the plan's retrieval_mode: secondary evidence_query
        # from the classifier should not override a primary social act.
        under_social_turn = conversation_act and (
            conversation_act.is_social
            or conversation_act.is_creative
            or conversation_act.is_repair
        )

        # Safety frames: no retrieval except safety policy
        if safety_frame and safety_frame.category != "none":
            return RetrievalPlan(
                mode="none",
                reason=f"safety_frame={safety_frame.category} — no retrieval needed",
            )

        # Social/exit/repair/creative turns: no retrieval
        if under_social_turn:
            return RetrievalPlan(
                mode="none",
                reason=f"act_type={conversation_act.act_type} — social/creative/repair, no retrieval",
            )

        # ── ActResolutionPlan takes priority for non-social turns ──
        if act_resolution_plan is not None:
            # Safety tasks always mean no retrieval
            if act_resolution_plan.safety_tasks:
                return RetrievalPlan(
                    mode="none",
                    reason="act_resolution_plan: safety_task present — no retrieval",
                )
            # If the plan already determined retrieval mode, use it
            if act_resolution_plan.retrieval_mode and act_resolution_plan.retrieval_mode != "none":
                return RetrievalPlan(
                    mode=act_resolution_plan.retrieval_mode,
                    reason=f"act_resolution_plan: retrieval_mode={act_resolution_plan.retrieval_mode}",
                )
            # Memory-only turns: no retrieval needed
            if act_resolution_plan.memory_updates and not act_resolution_plan.answer_tasks:
                return RetrievalPlan(
                    mode="none",
                    reason="act_resolution_plan: memory_updates only — no retrieval",
                )

        act_type = conversation_act.act_type if conversation_act else "unknown"

        # Exit: no retrieval
        if act_type == "exit":
            return RetrievalPlan(
                mode="none",
                reason="exit — no retrieval",
            )

        # Unknown lexemes or idiom candidates: lexeme memory
        if has_unknown_lexemes or has_idiom_candidates:
            return RetrievalPlan(
                mode="lexeme_memory",
                reason="unknown lexemes or idiom candidates — check lexeme memory",
            )

        # Self-related queries
        if act_type in ("self_identity_query", "self_knowledge_query", "self_capability_query"):
            return RetrievalPlan(
                mode="self_knowledge",
                reason=f"act_type={act_type} — self knowledge retrieval",
            )

        # User profile queries
        if act_type in ("user_identity_query", "user_name_query"):
            return RetrievalPlan(
                mode="profile",
                reason=f"act_type={act_type} — profile retrieval",
            )

        # Open-domain entity queries
        if act_type == "open_domain_entity_query":
            return RetrievalPlan(
                mode="world_memory",
                freshness_required=True,
                reason="open_domain_entity_query — world memory with freshness check",
            )

        # Evidence queries
        if act_type in ("evidence_query", "memory_query"):
            return RetrievalPlan(
                mode="world_memory",
                reason=f"act_type={act_type} — world memory retrieval",
            )

        # Teaching: no retrieval needed
        if act_type in ("teaching_offer", "definition_teaching", "command_alias_teaching"):
            return RetrievalPlan(
                mode="none",
                reason=f"act_type={act_type} — teaching, no retrieval",
            )

        # Default: no retrieval for unknown acts
        if act_type == "unknown":
            return RetrievalPlan(
                mode="none",
                reason="unknown act — no retrieval by default",
            )

        # Fallback: check if evidence is required
        if conversation_act and conversation_act.requires_evidence:
            return RetrievalPlan(
                mode="world_memory",
                reason=f"act_type={act_type} requires evidence",
            )

        return RetrievalPlan(
            mode="none",
            reason=f"act_type={act_type} — no retrieval needed",
        )
