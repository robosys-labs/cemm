"""Typed Stage 0-22 trace and side-effect ownership."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any
from cemm.model import now, stable


class Stage(IntEnum):
    ORIENT = 0
    OBSERVE = 1
    ENCODE = 2
    GROUND = 3
    PROJECT_STATE = 4
    COMPILE = 5
    RECURRENT_DYNAMICS = 6
    STABILIZE = 7
    BUILD_STRUCTURES = 8
    EPISTEMIC_PLACEMENT = 9
    QUERY_EXPLAIN = 10
    PREDICTION_ERROR = 11
    TRANSITION_SIMULATION = 12
    COMMIT = 13
    CAPABILITY_IMPACT = 14
    GOAL_ARBITRATION = 15
    PLAN_EXECUTE = 16
    ASSIMILATE_OPERATION = 17
    RESPONSE_CSIR = 18
    REALIZE = 19
    VERIFY = 20
    COMMON_GROUND = 21
    FINALIZE = 22


@dataclass(frozen=True)
class BudgetSet:
    max_facts: int
    max_rules: int
    max_depth: int
    max_reentry: int


@dataclass(frozen=True)
class StageRecord:
    stage: int
    name: str
    artifact_counts: dict[str, int]
    refs: tuple[str, ...] = ()
    durable_write: bool = False
    note: str | None = None
    recorded_at: str = field(default_factory=now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "name": self.name,
            "artifact_counts": dict(self.artifact_counts),
            "refs": list(self.refs),
            "durable_write": self.durable_write,
            "note": self.note,
            "recorded_at": self.recorded_at,
        }


@dataclass
class StageTrace:
    cycle_ref: str
    records: list[StageRecord] = field(default_factory=list)

    def add(self, stage: Stage, *, counts=None, refs=(), durable_write=False, note=None) -> StageRecord:
        if self.records and int(stage) <= self.records[-1].stage:
            raise ValueError(f"stage order regression: {stage} after {self.records[-1].stage}")
        if durable_write and int(stage) not in {13, 16, 17, 21}:
            raise ValueError(f"stage {stage} does not own durable effects")
        record = StageRecord(
            int(stage),
            stage.name,
            dict(counts or {}),
            tuple(refs),
            durable_write,
            note,
        )
        self.records.append(record)
        return record

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_ref": stable("stage-trace", self.cycle_ref, [x.as_dict() for x in self.records]),
            "cycle_ref": self.cycle_ref,
            "records": [x.as_dict() for x in self.records],
        }
