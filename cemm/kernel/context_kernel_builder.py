from __future__ import annotations
import time
import uuid
from ..types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from ..types.signal import Signal
from ..types.permission import Permission


class ContextKernelBuilder:
    def build(
        self,
        world: WorldState | None = None,
        user: UserState | None = None,
        time_state: TimeState | None = None,
        conversation: ConversationState | None = None,
        goal: GoalState | None = None,
        memory: MemoryState | None = None,
        permission: Permission | None = None,
        budget: Budget | None = None,
    ) -> ContextKernel:
        now = time.time()
        if time_state is None:
            time_state = TimeState(now=now, bucket=self._compute_bucket(now))
        if budget is None:
            budget = Budget()
        return ContextKernel(
            id=uuid.uuid4().hex[:16], world=world or WorldState(),
            user=user or UserState(), time=time_state,
            conversation=conversation or ConversationState(),
            goal=goal or GoalState(), memory=memory or MemoryState(),
            permission=permission or Permission.public(), budget=budget,
        )

    @staticmethod
    def from_signal(signal: Signal, turn_index: int = 0) -> ContextKernel:
        now = signal.observed_at
        return ContextKernel(
            id=signal.context_id, world=WorldState(),
            user=UserState(),
            time=TimeState(now=now, bucket=_compute_bucket(now)),
            conversation=ConversationState(
                session_id=signal.context_id, turn_index=turn_index,
                recent_signal_ids=[signal.id],
                first_user_signal_id=signal.id if turn_index == 1 else None,
            ),
            goal=GoalState(), memory=MemoryState(working_signal_ids=[signal.id]),
            permission=signal.permission, budget=Budget(),
            latest_signal=signal,
        )

    @staticmethod
    def _compute_bucket(timestamp: float) -> str:
        import datetime
        hour = datetime.datetime.fromtimestamp(timestamp).hour
        if 5 <= hour < 9: return "early_morning"
        elif 9 <= hour < 12: return "morning"
        elif 12 <= hour < 17: return "afternoon"
        elif 17 <= hour < 22: return "evening"
        elif hour >= 22 or hour < 5: return "night"
        return "unknown"


def _compute_bucket(timestamp: float) -> str:
    return ContextKernelBuilder._compute_bucket(timestamp)
