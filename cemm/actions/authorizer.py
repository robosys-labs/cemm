"""Internal action authorization for CEMM Phase 8.

Authorization is policy over semantic proposals. It does not execute actions.
"""

from __future__ import annotations

from cemm.response.types import InternalActionProposal, ResponseCandidatePlan, ResponseSituation

from .types import ActionAuthorizationDecision, ActionAuthorizationResult, ActionPolicy


_POLICIES: dict[str, ActionPolicy] = {
    "update_output_state": ActionPolicy("update_output_state", "conversation_state", min_confidence=0.3),
    "set_dialogue_expectation": ActionPolicy("set_dialogue_expectation", "conversation_state", min_confidence=0.5),
    "flag_safety_event": ActionPolicy("flag_safety_event", "safety_state", min_confidence=0.5),
    "mark_previous_response_failed": ActionPolicy("mark_previous_response_failed", "repair_state", min_confidence=0.45),
    "record_write_outcome": ActionPolicy("record_write_outcome", "write_trace", min_confidence=0.5),
    "record_distillation_coverage": ActionPolicy("record_distillation_coverage", "deliberation_trace", min_confidence=0.5),
    "set_locale_hint": ActionPolicy("set_locale_hint", "user_context_hint", min_confidence=0.45, require_source_refs=True, require_reversible=True),
    "set_language_hint": ActionPolicy("set_language_hint", "user_context_hint", min_confidence=0.45, require_source_refs=True, require_reversible=True),
    "set_language_preference": ActionPolicy("set_language_preference", "user_preference", min_confidence=0.8, require_source_refs=True, require_explicit_authority=True),
}

_DENIED_ACTION_TYPES = frozenset({
    "durable_memory_write",
    "commit_patch",
    "send_email",
    "create_calendar_event",
    "external_request",
    "execute_tool",
})


class InternalActionAuthorizer:
    def authorize(
        self,
        proposals: list[InternalActionProposal],
        situation: ResponseSituation,
        selected_plan: ResponseCandidatePlan | None = None,
    ) -> ActionAuthorizationResult:
        decisions: list[ActionAuthorizationDecision] = []
        authorized: list[InternalActionProposal] = []
        rejected: list[InternalActionProposal] = []
        for proposal in proposals:
            decision = self._authorize_one(proposal, situation, selected_plan)
            proposal.authorized = decision.authorized
            decisions.append(decision)
            if decision.authorized:
                authorized.append(proposal)
            else:
                rejected.append(proposal)
        return ActionAuthorizationResult(
            proposed_actions=list(proposals),
            authorized_actions=authorized,
            rejected_actions=rejected,
            decisions=decisions,
        )

    def _authorize_one(
        self,
        proposal: InternalActionProposal,
        situation: ResponseSituation,
        selected_plan: ResponseCandidatePlan | None,
    ) -> ActionAuthorizationDecision:
        if proposal.action_type in _DENIED_ACTION_TYPES:
            return self._decision(proposal, False, "side_effect_action_not_authorized_by_response_layer")
        policy = _POLICIES.get(proposal.action_type)
        if policy is None:
            return self._decision(proposal, False, "unknown_action_type")
        if proposal.confidence < policy.min_confidence:
            return self._decision(proposal, False, "confidence_below_policy_minimum", policy)
        if policy.require_source_refs and not proposal.source_refs:
            return self._decision(proposal, False, "missing_semantic_source_refs", policy)
        if policy.require_reversible and not proposal.reversible:
            return self._decision(proposal, False, "action_must_be_reversible", policy)
        if policy.require_explicit_authority:
            authority = proposal.payload.get("authority", "")
            if authority != "explicit_preference":
                return self._decision(proposal, False, "missing_explicit_semantic_authority", policy)
        if proposal.action_type == "flag_safety_event" and not self._has_safety_frame(situation):
            return self._decision(proposal, False, "safety_action_without_safety_frame", policy)
        if proposal.action_type == "record_write_outcome" and situation.write_outcome is None:
            return self._decision(proposal, False, "write_action_without_write_outcome", policy)
        if proposal.action_type == "mark_previous_response_failed":
            has_repair_move = bool(selected_plan and any(m.move_type == "repair_prior_response" for m in selected_plan.moves))
            has_reaction = situation.reaction_signal is not None or situation.temperature.conversation_repair_debt > 0
            if not (has_repair_move or has_reaction):
                return self._decision(proposal, False, "repair_action_without_repair_semantics", policy)
        return self._decision(proposal, True, "authorized", policy)

    @staticmethod
    def _has_safety_frame(situation: ResponseSituation) -> bool:
        safety = situation.safety_frame
        if safety is None:
            return False
        category = str(getattr(safety, "category", "") or getattr(safety, "risk_type", "") or "").lower()
        return category not in {"", "none", "safe", "low"}

    @staticmethod
    def _decision(
        proposal: InternalActionProposal,
        authorized: bool,
        reason: str,
        policy: ActionPolicy | None = None,
    ) -> ActionAuthorizationDecision:
        return ActionAuthorizationDecision(
            proposal=proposal,
            authorized=authorized,
            reason=reason,
            policy_scope=policy.authority_scope if policy is not None else "none",
        )
