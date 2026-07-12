"""Single authority for cross-turn session, teaching, and learning state."""

from __future__ import annotations

import copy
from typing import Any


class SessionStore:
    def __init__(self) -> None:
        self._state: dict[str, dict[str, Any]] = {}
        self._turn_counts: dict[str, int] = {}

    def get_turn_count(self, context_id: str) -> int:
        return self._turn_counts.get(context_id, 0)

    def next_turn_index(self, context_id: str) -> int:
        index = self._turn_counts.get(context_id, 0) + 1
        self._turn_counts[context_id] = index
        return index

    def restore(self, kernel: Any, signal: Any) -> None:
        prior = self._state.get(signal.context_id)
        if prior is None:
            return
        conv = getattr(kernel, "conversation", None)
        if conv is not None:
            conv.dynamics = copy.deepcopy(prior.get("conversation_dynamics", conv.dynamics))
            conv.active_repetition_group_ids = list(prior.get("active_repetition_group_ids", conv.active_repetition_group_ids))
            conv.recent_signal_ids = list(prior.get("recent_signal_ids", [])) + [signal.id]
            conv.first_user_signal_id = prior.get("first_user_signal_id", conv.first_user_signal_id)
            conv.pending_assistant_question = prior.get("pending_assistant_question", "")
            conv.expected_user_answer_type = prior.get("expected_user_answer_type", "")
            conv.last_assistant_response_mode = prior.get("last_assistant_response_mode", "")
            prior_discourse = prior.get("discourse_stack")
            if prior_discourse:
                conv.discourse_stack = copy.deepcopy(prior_discourse)
            conv.repair_target_turn_id = prior.get("repair_target_turn_id", "")
            conv.active_teaching_target = prior.get("active_teaching_target", "")
            conv.active_unknown_concept = prior.get("active_unknown_concept", "")
            conv.entity_salience = dict(prior.get("entity_salience", {}))
        user = getattr(kernel, "user", None)
        if user is not None and hasattr(user, "affect"):
            user.affect = copy.deepcopy(prior.get("user_affect", user.affect))
        topic = getattr(kernel, "topic", None)
        if topic is not None:
            prior_topic = prior.get("topic_state") or {}
            for key in (
                "active_topic_entity_id", "active_topic_surface", "active_topic_type",
                "last_taught_entity_id", "last_taught_entity_surface", "last_questioned_attribute",
            ):
                if hasattr(topic, key):
                    setattr(topic, key, prior_topic.get(key, getattr(topic, key)))
        last_user_at = prior.get("last_user_at")
        time_state = getattr(kernel, "time", None)
        if last_user_at is not None and time_state is not None:
            time_state.time_since_last_user_signal_ms = max(
                0.0, (signal.observed_at - float(last_user_at)) * 1000.0
            )

    def persist(self, kernel: Any, signal: Any) -> None:
        context_id = signal.context_id
        prior = self._state.get(context_id, {})
        conv = getattr(kernel, "conversation", None)
        topic = getattr(kernel, "topic", None)
        user = getattr(kernel, "user", None)
        self._state[context_id] = {
            **{key: copy.deepcopy(value) for key, value in prior.items() if key in {"teaching_frame", "learning_state"}},
            "user_affect": copy.deepcopy(user.affect) if user is not None and hasattr(user, "affect") else {},
            "conversation_dynamics": copy.deepcopy(conv.dynamics) if conv is not None and hasattr(conv, "dynamics") else {},
            "active_repetition_group_ids": list(conv.active_repetition_group_ids) if conv is not None else [],
            "recent_signal_ids": list(conv.recent_signal_ids) if conv is not None else [],
            "first_user_signal_id": conv.first_user_signal_id if conv is not None else None,
            "last_user_at": signal.observed_at,
            "pending_assistant_question": conv.pending_assistant_question if conv is not None else "",
            "expected_user_answer_type": conv.expected_user_answer_type if conv is not None else "",
            "last_assistant_response_mode": conv.last_assistant_response_mode if conv is not None else "",
            "topic_state": {
                key: getattr(topic, key, "")
                for key in (
                    "active_topic_entity_id", "active_topic_surface", "active_topic_type",
                    "last_taught_entity_id", "last_taught_entity_surface", "last_questioned_attribute",
                )
            } if topic is not None else {},
            "discourse_stack": copy.deepcopy(conv.discourse_stack) if conv is not None else None,
            "repair_target_turn_id": conv.repair_target_turn_id if conv is not None else "",
            "active_teaching_target": conv.active_teaching_target if conv is not None else "",
            "active_unknown_concept": conv.active_unknown_concept if conv is not None else "",
            "entity_salience": dict(conv.entity_salience) if conv is not None and hasattr(conv, "entity_salience") else {},
        }

    def save_teaching_frame(self, context_id: str, frame_data: dict | None) -> None:
        self._state.setdefault(context_id, {})["teaching_frame"] = copy.deepcopy(frame_data)

    def load_teaching_frame(self, context_id: str) -> dict | None:
        return copy.deepcopy((self._state.get(context_id) or {}).get("teaching_frame"))

    def save_learning_state(self, context_id: str, state: dict[str, Any] | None) -> None:
        self._state.setdefault(context_id, {})["learning_state"] = copy.deepcopy(state or {})

    def load_learning_state(self, context_id: str) -> dict[str, Any] | None:
        state = (self._state.get(context_id) or {}).get("learning_state")
        return copy.deepcopy(state) if isinstance(state, dict) else None

    def has_context(self, context_id: str) -> bool:
        return context_id in self._state

    def get_state(self, context_id: str) -> dict | None:
        state = self._state.get(context_id)
        return copy.deepcopy(state) if state is not None else None
