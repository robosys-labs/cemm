# CEMM-ARCH: Refer to cemm_architecture_gap_trace.md and AGENTS.md before modifying.
# Fix 1: Model-driven inference. Loads context_rule models from ModelStore
# and scores them against signal content before falling back to hardcoded rules.

from __future__ import annotations
from ..types.context_kernel import ContextKernel
from ..types.context_inference import ContextInference
from ..types.signal import Signal
from ..types.model import ModelKind, ModelStatus
from ..store.store import Store
from ..registry import Registry
from ..retrieval.ranker import Ranker
from ..confidence.scoring import score_model
import uuid, time


_INFERENCE_CONFIDENCE_THRESHOLD = 0.6


class ContextInferenceEngine:
    def __init__(self, store: Store, registry: Registry) -> None:
        self._store = store
        self._registry = registry
        self._ranker = Ranker()

    def infer(self, signal: Signal, kernel: ContextKernel) -> ContextInference:
        inference = ContextInference(
            id=uuid.uuid4().hex[:16],
            source_signal_id=signal.id,
        )
        content_lower = signal.content.lower().strip()
        turn_index = kernel.conversation.turn_index if kernel.conversation else 0

        # Phase 1: Model-driven inference — load active context_rule models
        model_rules = self._store.models.find_by_kind(
            ModelKind.CONTEXT_RULE.value,
            ModelStatus.ACTIVE.value,
        )
        scored_rules = self._ranker.rank_models(model_rules, kernel)
        for model, score in scored_rules:
            if score < _INFERENCE_CONFIDENCE_THRESHOLD:
                break
            # Check if model's preconditions match the signal content
            matched = True
            for prec in model.preconditions:
                prec_lower = prec.lower()
                if prec_lower.startswith("keyword:"):
                    keyword = prec_lower[len("keyword:"):]
                    if keyword not in content_lower:
                        matched = False
                        break
                elif prec_lower.startswith("regex:"):
                    import re
                    pattern = prec_lower[len("regex:"):]
                    if not re.search(pattern, content_lower):
                        matched = False
                        break
                elif prec_lower.startswith("turn:"):
                    turn_condition = prec_lower[len("turn:"):]
                    if turn_condition == "first" and turn_index != 1:
                        matched = False
                        break
            if matched:
                inference.confidence = max(inference.confidence, model.confidence)
                if model.registry_key:
                    inference.frame_id = model.registry_key
                inference.applied_context_rule_model_ids.append(model.id)

        # Phase 2: Fallback — hardcoded rules (only if no model exceeded threshold)
        if not inference.applied_context_rule_model_ids:
            greeting_words = {"hello", "hi", "hey", "howdy", "greetings", "sup", "morning", "afternoon", "evening"}
            acknowledgment_words = {"ok", "sure", "yeah", "cool", "right", "understood", "noted", "great", "nice"}
            clarification_words = {"what", "huh", "confused", "lost", "why", "how"}
            exit_words = {"exit", "quit", "bye", "goodbye", "stop", "done"}
            words_set = set(content_lower.replace("?", "").split())

            if words_set & exit_words:
                inference.confidence = max(inference.confidence, 0.7)
                inference.frame_id = "session_exit"
            elif turn_index == 1 and (words_set & greeting_words):
                inference.confidence = max(inference.confidence, 0.7)
                inference.frame_id = "session_opening"
            elif words_set & greeting_words:
                inference.confidence = max(inference.confidence, 0.5)
                inference.frame_id = "greeting"
            elif words_set & acknowledgment_words:
                inference.confidence = max(inference.confidence, 0.5)
                inference.frame_id = "acknowledgment"
            elif words_set & clarification_words:
                inference.confidence = max(inference.confidence, 0.5)
                inference.frame_id = "clarification"
            elif turn_index == 1 and len(content_lower.split()) <= 3 and "?" not in content_lower:
                inference.confidence = max(inference.confidence, 0.3)
                inference.frame_id = "session_opening"

            if "weather" in content_lower:
                if not kernel.user.locale:
                    inference.confidence = max(inference.confidence, 0.4)

            context_rules = self._registry.all_by_kind("context_rule")
            for rule in context_rules:
                if rule.canonical_key == "greeting_detection" and turn_index == 1:
                    inference.applied_context_rule_model_ids.append(rule.model_id)

        return inference

    def apply_to_kernel(self, inference: ContextInference, kernel: ContextKernel) -> None:
        if not kernel.conversation:
            return
        kernel.conversation.inferred_context_claim_ids = inference.inferred_claim_ids
        if inference.frame_id:
            if kernel.memory and inference.frame_id not in kernel.memory.active_frame_ids:
                kernel.memory.active_frame_ids.append(inference.frame_id)
