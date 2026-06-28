from __future__ import annotations
from ..types.context_kernel import ContextKernel
from ..types.context_inference import ContextInference
from ..types.signal import Signal
from ..store.store import Store
from ..registry import Registry
import uuid, time

class ContextInferenceEngine:
    def __init__(self, store: Store, registry: Registry) -> None:
        self._store = store
        self._registry = registry

    def infer(self, signal: Signal, kernel: ContextKernel) -> ContextInference:
        inference = ContextInference(
            id=uuid.uuid4().hex[:16],
            source_signal_id=signal.id,
        )
        turn_index = kernel.conversation.turn_index if kernel.conversation else 0

        if turn_index == 1:
            content_lower = signal.content.lower().strip()
            if len(content_lower.split()) <= 3 and content_lower in ("morning", "good morning", "hello", "hi", "hey"):
                inference.confidence = 0.7
                inference.frame_id = "session_opening"
            elif len(content_lower) < 15 and "?" not in content_lower:
                inference.confidence = 0.3
                inference.frame_id = "urgent_request"

        if "weather" in signal.content.lower():
            if not kernel.user.locale:
                inference.confidence = 0.4

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
