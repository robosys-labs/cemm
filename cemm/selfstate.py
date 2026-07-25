"""Deprecated compatibility facade for the former global SessionSelf.

Cognitive interpretation, scoped epistemics and learning frontiers now live in
CycleWorkspace artifacts.  This class intentionally emits no semantic facts and
must not be used to turn one unresolved utterance into a global self condition.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateTransition:
    dimension: str
    before: str | None
    after: str
    cause: str
    turn: int


class SessionSelf:
    """Compatibility-only runtime trace; not semantic self/world state."""

    def __init__(self, _store):
        self.turn = 0
        self.state: dict[str, str] = {}
        self.transitions: list[StateTransition] = []

    def set(self, dimension, value, cause):
        self.turn += 1
        before = self.state.get(str(dimension))
        if before != value:
            self.state[str(dimension)] = str(value)
            self.transitions.append(StateTransition(str(dimension), before, str(value), str(cause), self.turn))

    def slots(self):
        # Runtime/cognitive bookkeeping is not injected as op:state(self, ...).
        return []
