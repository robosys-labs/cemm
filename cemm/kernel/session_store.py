"""SessionStore — single authority for cross-turn session state.

Encapsulates restore/persist of all conversation-level state that must
survive across turns within a context.  Replaces the duplicated and
divergent _session_state dictionaries that previously lived in both
Pipeline and SemanticKernelRuntime.

Key invariants:
  - One implementation, used by run_turn() at entry and exit.
  - recent_signal_ids are *accumulated* (prior + current signal id).
  - last_user_at uses signal.observed_at (not time.time()).
  - TeachingFrame state is serialized and restored (not just the target string).
  - Turn counts are tracked per context_id.
"""

from __future__ import annotations

import copy
from typing import Any


class SessionStore:
    """Single authority for cross-turn session state."""

    def __init__(self) -> None:
        self._state: dict[str, dict] = {}
        self._turn_counts: dict[str, int] = {}

    # ── Turn counts ───────────────────────────────────────────────

    def get_turn_count(self, context_id: str) -> int:
        return self._turn_counts.get(context_id, 0)

    def next_turn_index(self, context_id: str) -> int:
        idx = self._turn_counts.get(context_id, 0) + 1
        self._turn_counts[context_id] = idx
        return idx

    # ── Restore ───────────────────────────────────────────────────

    def restore(self, kernel: Any, signal: Any) -> None:
        """Hydrate kernel from prior session state for this context.

        Called at the top of run_turn(), before any processing.
        Appends the current signal id to recent_signal_ids.
        """
        context_id = signal.context_id
        prior = self._state.get(context_id)
        if prior is None:
            return

        conv = getattr(kernel, "conversation", None)
        if conv is not None:
            conv.dynamics = copy.deepcopy(
                prior.get("conversation_dynamics", conv.dynamics)
            )
            conv.active_repetition_group_ids = list(
                prior.get("active_repetition_group_ids", conv.active_repetition_group_ids)
            )
            previous_recent = list(prior.get("recent_signal_ids", []))
            conv.recent_signal_ids = previous_recent + [signal.id]
            conv.first_user_signal_id = prior.get(
                "first_user_signal_id", conv.first_user_signal_id
            )
            conv.pending_assistant_question = prior.get(
                "pending_assistant_question", ""
            )
            conv.expected_user_answer_type = prior.get(
                "expected_user_answer_type", ""
            )
            conv.last_assistant_response_mode = prior.get(
                "last_assistant_response_mode", ""
            )
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
            prior_topic = prior.get("topic_state")
            if prior_topic:
                topic.active_topic_entity_id = prior_topic.get("active_topic_entity_id", "")
                topic.active_topic_surface = prior_topic.get("active_topic_surface", "")
                topic.active_topic_type = prior_topic.get("active_topic_type", "")
                topic.last_taught_entity_id = prior_topic.get("last_taught_entity_id", "")
                topic.last_taught_entity_surface = prior_topic.get("last_taught_entity_surface", "")
                topic.last_questioned_attribute = prior_topic.get("last_questioned_attribute", "")

        last_user_at = prior.get("last_user_at")
        if last_user_at is not None:
            tm = getattr(kernel, "time", None)
            if tm is not None:
                tm.time_since_last_user_signal_ms = max(
                    0.0, (signal.observed_at - float(last_user_at)) * 1000.0,
                )

    # ── Persist ───────────────────────────────────────────────────

    def persist(self, kernel: Any, signal: Any) -> None:
        """Snapshot kernel state into session store for this context.

        Called at the end of run_turn(), after all processing and
        output state updates are complete.
        """
        context_id = signal.context_id
        conv = getattr(kernel, "conversation", None)
        topic = getattr(kernel, "topic", None)
        user = getattr(kernel, "user", None)

        self._state[context_id] = {
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
                "active_topic_entity_id": topic.active_topic_entity_id if topic is not None else "",
                "active_topic_surface": topic.active_topic_surface if topic is not None else "",
                "active_topic_type": topic.active_topic_type if topic is not None else "",
                "last_taught_entity_id": topic.last_taught_entity_id if topic is not None else "",
                "last_taught_entity_surface": topic.last_taught_entity_surface if topic is not None else "",
                "last_questioned_attribute": topic.last_questioned_attribute if topic is not None else "",
            } if topic is not None else {},
            "discourse_stack": copy.deepcopy(conv.discourse_stack) if conv is not None else None,
            "repair_target_turn_id": conv.repair_target_turn_id if conv is not None else "",
            "active_teaching_target": conv.active_teaching_target if conv is not None else "",
            "active_unknown_concept": conv.active_unknown_concept if conv is not None else "",
            "entity_salience": dict(conv.entity_salience) if conv is not None and hasattr(conv, "entity_salience") else {},
        }

    # ── Teaching frame serialization ──────────────────────────────

    def save_teaching_frame(self, context_id: str, frame_data: dict | None) -> None:
        """Persist teaching frame data for a context."""
        state = self._state.setdefault(context_id, {})
        state["teaching_frame"] = frame_data

    def load_teaching_frame(self, context_id: str) -> dict | None:
        """Retrieve teaching frame data for a context."""
        state = self._state.get(context_id)
        if state is None:
            return None
        return state.get("teaching_frame")

    # ── Introspection (for tests) ─────────────────────────────────

    def has_context(self, context_id: str) -> bool:
        return context_id in self._state

    def get_state(self, context_id: str) -> dict | None:
        return self._state.get(context_id)
