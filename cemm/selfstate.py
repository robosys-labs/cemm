"""Session self-state and state transitions for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 504-516).

The SessionSelf tracks the agent's internal state across three dimensions
(response, interpretation, epistemic) and emits those states as derived
semantic facts so the workspace and response planner can reason about them.
"""
from __future__ import annotations

from dataclasses import dataclass

from cemm.store import Store
from cemm.model import Fact, stable, canonical, now


@dataclass
class StateTransition:
    dimension: str
    before: str | None
    after: str
    cause: str
    turn: int


class SessionSelf:
    def __init__(self, s: Store):
        self.s = s
        self.turn = 0
        self.state = {
            s.symbol("self.response_state_dimension"): s.symbol("self.ready"),
            s.symbol("self.interpretation_state_dimension"): s.symbol("self.resolved"),
            s.symbol("self.epistemic_state_dimension"): s.symbol("self.sufficient"),
        }
        self.transitions: list[StateTransition] = []

    def set(self, dimension, value, cause):
        before = self.state.get(dimension)
        self.turn += 1
        if before != value:
            self.state[dimension] = value
            self.transitions.append(
                StateTransition(dimension, before, value, cause, self.turn)
            )

    def slots(self):
        selfref = self.s.symbol("self.ref")
        op = self.s.symbol("operator.state")
        return [
            Fact(
                stable("selfslot", d, v),
                op,
                {"role:subject": selfref, "role:dimension": d, "role:value": v},
                "support",
                1,
                True,
                {"session_state": True},
            )
            for d, v in self.state.items()
        ]
