"""ErrorAttributionEngine — convert user reactions into labelled error data.

Runs after realization. Uses ReactionSignal (from pre-classification),
ConversationActPacket, DiscourseStateStack, DecisionPacket, SemanticAnswerGraph,
and realization metadata to attribute a specific error type to the previous turn.

The result is used to:
1. Mark the previous DiscourseEntry as failed
2. Update SelfView.recent_error_rate (EMA)
3. Export correction labels for training
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..kernel.reaction_detector import ReactionSignal
from ..types.context_kernel import DiscourseStateStack, DiscourseEntry
from ..types.conversation_act import ConversationActPacket
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..types.self_view import SelfView


@dataclass
class ErrorAttributionResult:
    """Result of attributing an error to a previous turn."""

    source_turn_id: str
    error_type: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)
    correct_act_type: str = ""
    previous_intent: str = ""
    previous_response_mode: str = ""
    previous_user_text: str = ""
    previous_assistant_response: str = ""


# Error type constants
INTENT_MISCLASSIFIED = "intent_misclassified"
RESPONSE_TOO_GENERIC = "response_too_generic"
RETRIEVAL_WRONG = "retrieval_wrong"
MEMORY_WRITE_FAILED = "memory_write_failed"
TEACHING_NOT_UNDERSTOOD = "teaching_not_understood"
CAPABILITY_MISREPRESENTED = "capability_misrepresented"
UNKNOWN_CONCEPT_NOT_DECLARED = "unknown_concept_not_declared"
SAFETY_MISSED = "safety_missed"

# Maps reaction_kind → default error type
_REACTION_KIND_TO_ERROR: dict[str, str] = {
    "confusion": RESPONSE_TOO_GENERIC,
    "frustration": INTENT_MISCLASSIFIED,
    "correction": INTENT_MISCLASSIFIED,
    "meta_critique": RESPONSE_TOO_GENERIC,
}

# Previous response modes that are considered "generic"
_GENERIC_MODES = {"general_conversation", "unknown_entity_response"}


class ErrorAttributionEngine:
    """Attribution engine that converts reactions into structured error labels."""

    def evaluate(
        self,
        reaction_signal: ReactionSignal | None,
        conversation_act: ConversationActPacket | None,
        discourse_stack: DiscourseStateStack | None,
        decision_packet: Any | None = None,
        sag: SemanticAnswerGraph | None = None,
        realization_metadata: dict[str, Any] | None = None,
    ) -> ErrorAttributionResult | None:
        """Evaluate whether the current turn is a reaction indicating a previous error.

        Returns ErrorAttributionResult if an error is attributed, None otherwise.
        """
        if not reaction_signal or not reaction_signal.is_reaction:
            return None

        if not discourse_stack or not discourse_stack.entries:
            return None

        # The target is the previous turn (the one the user is reacting to)
        target_entry = None
        for entry in reversed(discourse_stack.entries):
            if entry.turn_id == reaction_signal.target_turn_id:
                target_entry = entry
                break

        if not target_entry:
            # Fall back to last entry
            target_entry = discourse_stack.last_entry
            if not target_entry:
                return None

        # Start with the reaction detector's likely error type
        error_type = reaction_signal.likely_error_type or _REACTION_KIND_TO_ERROR.get(
            reaction_signal.reaction_kind, RESPONSE_TOO_GENERIC
        )

        evidence: dict[str, Any] = dict(reaction_signal.evidence)
        evidence["reaction_kind"] = reaction_signal.reaction_kind
        evidence["reaction_confidence"] = reaction_signal.confidence

        prev_mode = target_entry.assistant_response_mode or "general_conversation"
        prev_intent = target_entry.assistant_intent
        correct_act_type = ""

        # Refine error type based on previous turn context

        # 1. If previous intent was general_conversation and reaction is confusion
        #    → intent_misclassified (the input was likely something specific)
        if (
            prev_intent in ("general_conversation", "")
            and reaction_signal.reaction_kind == "confusion"
        ):
            error_type = INTENT_MISCLASSIFIED
            # Try to infer the correct act type from current conversation act
            if conversation_act and conversation_act.act_types:
                for act_type in conversation_act.act_types:
                    if act_type not in ("general_conversation", "unknown", "evidence_query"):
                        correct_act_type = act_type
                        break

        # 2. If previous intent was correct but template was generic
        #    → response_too_generic
        elif prev_mode in _GENERIC_MODES and prev_intent not in ("general_conversation", ""):
            error_type = RESPONSE_TOO_GENERIC

        # 3. If previous was remember but no claim was stored
        #    → memory_write_failed
        elif prev_intent == "remember" and not target_entry.selected_claim_ids:
            error_type = MEMORY_WRITE_FAILED
            evidence["no_claims_stored"] = True

        # 4. If previous was evidence_answer but reaction is confusion
        #    → retrieval_wrong (irrelevant evidence)
        elif prev_mode == "evidence_answer" and reaction_signal.reaction_kind == "confusion":
            error_type = RETRIEVAL_WRONG

        # 5. If previous was teaching_prompt and user seems confused
        #    → teaching_not_understood
        elif prev_mode == "teaching_prompt" and reaction_signal.reaction_kind in ("confusion", "frustration"):
            error_type = TEACHING_NOT_UNDERSTOOD

        # 6. If previous was capability_summary and reaction is correction
        #    → capability_misrepresented
        elif prev_mode == "capability_summary" and reaction_signal.reaction_kind == "correction":
            error_type = CAPABILITY_MISREPRESENTED

        # 7. If previous was unknown_entity_response but user indicates
        #    the system should have known
        elif prev_mode == "unknown_entity_response" and reaction_signal.reaction_kind == "correction":
            error_type = UNKNOWN_CONCEPT_NOT_DECLARED

        # 8. If safety was missed (current act is safety but previous wasn't safety)
        if (
            conversation_act
            and "safety_response" in conversation_act.act_types
            and prev_mode != "safety_response"
        ):
            error_type = SAFETY_MISSED
            correct_act_type = "safety_response"

        # Use SAG verification metadata if available
        if realization_metadata:
            verification = realization_metadata.get("verification", {})
            if verification and not verification.get("verified", True):
                evidence["verification_failed"] = True
                evidence["verification_details"] = verification.get("details", [])

        return ErrorAttributionResult(
            source_turn_id=target_entry.turn_id,
            error_type=error_type,
            confidence=reaction_signal.confidence,
            evidence=evidence,
            correct_act_type=correct_act_type,
            previous_intent=prev_intent,
            previous_response_mode=prev_mode,
            previous_user_text=target_entry.user_text,
            previous_assistant_response=target_entry.assistant_text,
        )

    def apply(
        self,
        result: ErrorAttributionResult,
        discourse_stack: DiscourseStateStack,
        self_view: SelfView,
        semantic_model_store: Any = None,
    ) -> None:
        """Apply the attribution result: mark discourse entry, update error rate, correct bindings.

        Args:
            result: The error attribution result.
            discourse_stack: The discourse state stack to update.
            self_view: The self view to update error rate on.
            semantic_model_store: Optional store to correct surface→act_type bindings.
        """
        # 1. Mark previous DiscourseEntry as failed
        for entry in discourse_stack.entries:
            if entry.turn_id == result.source_turn_id:
                entry.status = "failed"
                entry.error_type = result.error_type
                break

        # 2. Update SelfView.recent_error_rate (EMA over last N turns)
        # EMA: recent_error_rate = 0.7 * recent_error_rate + 0.3 * (1 if failed else 0)
        current_error = 1.0
        self_view.recent_error_rate = min(
            1.0,
            0.7 * self_view.recent_error_rate + 0.3 * current_error,
        )

        # 3. Track error history (last 20 error types)
        self_view.error_history.append(result.error_type)
        if len(self_view.error_history) > 20:
            self_view.error_history = self_view.error_history[-20:]

        # 4. Correct SemanticModelStore binding for intent_misclassified errors
        # When an intent was misclassified, the previous user surface should be
        # corrected to map to the correct act_type/frame_key.
        if semantic_model_store and result.error_type in (
            INTENT_MISCLASSIFIED, UNKNOWN_CONCEPT_NOT_DECLARED, SAFETY_MISSED
        ) and result.correct_act_type:
            # Find existing binding for the previous user surface
            prev_surface = result.previous_user_text
            existing_bindings = semantic_model_store.lookup_surface(prev_surface)
            if existing_bindings:
                # Correct the first (highest confidence) binding
                corrected_mapping = {
                    "act_type": result.correct_act_type,
                    "frame_key": result.correct_act_type,
                }
                semantic_model_store.correct(
                    existing_bindings[0].id,
                    corrected_mapping,
                    signal_id=result.source_turn_id,
                )
            else:
                # Create a new candidate binding with the correct mapping
                from ..registry.semantic_model_store import SurfaceBinding
                binding = SurfaceBinding(
                    id="",
                    surface=prev_surface,
                    language="en",
                    normalized_surface=prev_surface.lower().strip(),
                    maps_to_act_type=result.correct_act_type,
                    maps_to_frame_key=result.correct_act_type,
                    source="corrected",
                )
                semantic_model_store.observe_candidate(binding, signal_id=result.source_turn_id)

    def record_success(self, self_view: Any) -> None:
        """Decay EMA error rate on a successful (non-error) turn."""
        self_view.recent_error_rate = max(
            0.0,
            0.7 * self_view.recent_error_rate + 0.3 * 0.0,
        )

    def decay_error_rate(self, self_view: Any) -> None:
        self.record_success(self_view)

    def export_correction_label(
        self,
        result: ErrorAttributionResult,
        current_input: str,
    ) -> dict[str, Any]:
        """Export a correction label for training.

        Args:
            result: The error attribution result.
            current_input: The current user input that triggered the reaction.

        Returns:
            A correction label dict suitable for training export.
        """
        return {
            "task_type": "correction_label",
            "input": current_input,
            "context": {
                "previous_user_text": result.previous_user_text,
                "previous_assistant_response": result.previous_assistant_response,
                "previous_intent": result.previous_intent,
                "previous_response_mode": result.previous_response_mode,
            },
            "target": {
                "act_type": "retrospective_repair",
                "error_type": result.error_type,
                "correct_act_type": result.correct_act_type,
                "source_turn_id": result.source_turn_id,
            },
            "confidence": result.confidence,
            "evidence": result.evidence,
        }
