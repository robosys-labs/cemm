"""OutputStateUpdater — updates conversation state after final realization.

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

import re

from ..types.context_kernel import ContextKernel
from ..types.meaning_percept import OutputStateUpdate


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


# Patterns that indicate the assistant asked a question
_QUESTION_PATTERNS = {
    "social_checkin": [
        r"how are you",
        r"how are you doing",
        r"how are things",
        r"how's it going",
        r"how do you do",
        r"what's up",
        r"how are you today",
    ],
    "idiom_confirmation": [
        r"do you mean",
        r"does .+ mean",
        r"is .+ bothering",
        r"is .+ provoking",
    ],
    "yes_no": [
        r"^do you",
        r"^are you",
        r"^is it",
        r"^can you",
        r"^would you",
        r"^should i",
    ],
    "preference": [
        r"what are you (in the mood for|leaning toward)",
        r"what do you (prefer|want|think)",
    ],
}


def _detect_question_type(output_text: str) -> tuple[str, str]:
    """Detect what kind of question the assistant asked.

    Returns (question_type, expected_answer_type).
    """
    text_lower = output_text.lower().strip()
    tokens = _tokenize(text_lower)

    # Check if it ends with a question mark or has question structure
    is_question = text_lower.endswith("?") or (
        bool(tokens) and tokens[0] in ("do", "are", "is", "can", "would", "should", "how", "what", "why", "could")
    ) or any(
        re.search(pattern, text_lower)
        for pattern in [
            r"i'?d like to know",
            r"i want to know",
            r"tell me (about|what|how|why|when|where)",
            r"could you (tell|explain|describe)",
            r"can you (tell|explain|describe)",
            r"what(?:'s| is| are) your",
        ]
    )
    if not is_question:
        return ("", "")

    for q_type, patterns in _QUESTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                if q_type == "social_checkin":
                    return ("social_checkin", "social_status")
                elif q_type == "idiom_confirmation":
                    return ("idiom_confirmation", "yes_no_or_definition")
                elif q_type == "yes_no":
                    return ("yes_no", "yes_no")
                elif q_type == "preference":
                    return ("preference_query", "preference")
    return ("general_question", "free_form")


class OutputStateUpdater:
    """Updates conversation state after final output is realized."""

    def update(
        self,
        kernel: ContextKernel,
        output_text: str,
        output_signal_id: str = "",
        assistant_intent: str = "",
        response_mode: str = "",
    ) -> OutputStateUpdate:
        """Produce an OutputStateUpdate from the actual realized output.

        Args:
            kernel: The current context kernel.
            output_text: The actual text the assistant produced.
            output_signal_id: ID of the output signal.
            assistant_intent: The intent from the decision packet.
            response_mode: The response mode from the decision packet.

        Returns:
            OutputStateUpdate to apply to kernel and session state.
        """
        q_type, expected_answer = _detect_question_type(output_text)

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
