"""DEPRECATED: Replaced by cemm.kernel.response.common_ground.CommonGroundManager.

This module is retained for legacy compatibility only. The v3.4 canonical
path uses CommonGroundManager for tracking dispatched communication and
updating discourse state. Do not use for new code — redirect to the v3.4
common ground pipeline.

OutputStateUpdater — updates conversation state after final realization.

Implements P0-3 from cemm_foundational_fixes.md and §18 from architecture.md.

Must run after final output is realized, not inside the pre-output pipeline.
Fixes the bug where:
    AI: How are you doing?
    User: I am fine, you?
    AI: (fails to recognize this as answer to pending question)

The updater sets pending_assistant_question, expected_user_answer_type,
last_assistant_response_mode, and last_assistant_intent from the ACTUAL
assistant output, not the predicted response mode.
"""

from __future__ import annotations

from typing import Any

from ...types.context_kernel import ContextKernel
from ...types.meaning_percept import OutputStateUpdate


def _moves_contain(response_bundle: Any | None, move_type: str) -> bool:
    """Return True if response_bundle contains a move of the given type."""
    if response_bundle is None:
        return False
    for move in getattr(response_bundle, "moves", []) or []:
        if getattr(move, "move_type", "") == move_type:
            return True
    return False


def _detect_question_type(
    response_mode: str,
    response_bundle: Any | None,
    query_contract: Any | None,
) -> tuple[str, str]:
    """Derive pending question type from response metadata, not output text.

    The response_mode, response_bundle moves, and query_contract together
    encode the assistant's output act. Output text is not inspected.
    """
    if response_mode == "clarify":
        query_kind = ""
        if query_contract is not None:
            query_kind = getattr(query_contract, "query_kind", "") or ""
        if query_kind == "clarification":
            return ("idiom_confirmation", "yes_no_or_definition")
        if query_kind == "profile_dimension":
            return ("preference_query", "preference")
        return ("general_question", "free_form")

    if response_mode == "confirm_write":
        return ("yes_no", "yes_no")

    if response_mode == "social" and _moves_contain(response_bundle, "phatic_response"):
        return ("social_checkin", "social_status")

    return ("", "")


class OutputStateUpdater:
    """Updates conversation state after final output is realized."""

    def update(
        self,
        kernel: ContextKernel,
        output_text: str,
        output_signal_id: str = "",
        assistant_intent: str = "",
        response_mode: str = "",
        obligation_contract: Any | None = None,
        response_bundle: Any | None = None,
    ) -> OutputStateUpdate:
        """Produce an OutputStateUpdate from the actual realized output.

        Args:
            kernel: The current context kernel.
            output_text: The actual text the assistant produced. Kept for
                backward compatibility but not used for question detection.
            output_signal_id: ID of the output signal.
            assistant_intent: The intent from the decision packet.
            response_mode: The response mode from the decision packet.
            obligation_contract: The authoritative obligation contract for the
                turn, used to derive query context.
            response_bundle: The realized response bundle, used to derive the
                assistant's actual output act.

        Returns:
            OutputStateUpdate to apply to kernel and session state.
        """
        query_contract = None
        if obligation_contract is not None:
            query_contract = getattr(obligation_contract, "query_contract", None)
        q_type, expected_answer = _detect_question_type(
            response_mode=response_mode,
            response_bundle=response_bundle,
            query_contract=query_contract,
        )

        # If the output is not a question, clear any pending question
        if q_type:
            pending_q = q_type
            expected_type = expected_answer
        else:
            pending_q = None
            expected_type = None

        return OutputStateUpdate(
            last_assistant_output_signal_id=output_signal_id,
            last_assistant_intent=assistant_intent,
            last_assistant_response_mode=response_mode,
            pending_assistant_question=pending_q,
            expected_user_answer_type=expected_type,
        )

    def apply(
        self,
        kernel: ContextKernel,
        update: OutputStateUpdate,
    ) -> None:
        """Apply an OutputStateUpdate to the kernel's conversation state.

        This is a full state transition, not an optional patch. If the latest
        assistant output did not create a pending question, stale pending fields
        must be cleared; otherwise the next user turn can be misinterpreted as
        an answer to an older assistant question.
        """
        if update.last_assistant_response_mode is not None:
            kernel.conversation.last_assistant_response_mode = update.last_assistant_response_mode
        if update.pending_assistant_question is not None:
            kernel.conversation.pending_assistant_question = update.pending_assistant_question
        if update.expected_user_answer_type is not None:
            kernel.conversation.expected_user_answer_type = update.expected_user_answer_type
