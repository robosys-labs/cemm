"""MemoryUpdateTask and MemoryUpdateBatch — v3.3 batch memory write planning.

The ActResolutionPlanner produces MemoryUpdateTask items from EntityFactCandidates.
These are collected into a MemoryUpdateBatch and executed atomically by the
RememberOperator, replacing the single-claim-at-a-time approach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryUpdateTask:
    """A single memory write operation planned from a fact candidate."""
    subject_entity_id: str = ""
    predicate: str = ""
    object_value: str | int | float | bool | None = None
    object_entity_id: str | None = None
    qualifiers: dict[str, Any] = field(default_factory=dict)
    domain: str = "general"
    confidence: float = 0.5
    trust: float = 0.5
    evidence_span: str = ""
    source: str = "act_resolution_planner"
    reason: str = ""

    def is_valid(self) -> bool:
        """Check if this task has enough information to produce a claim."""
        return bool(
            self.subject_entity_id
            and self.predicate
            and self.object_value is not None
            and str(self.object_value).strip()
        )


@dataclass
class MemoryUpdateBatch:
    """A batch of memory update tasks to be executed atomically."""
    tasks: list[MemoryUpdateTask] = field(default_factory=list)
    source_signal_id: str = ""
    context_id: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.valid_tasks

    @property
    def valid_tasks(self) -> list[MemoryUpdateTask]:
        return [t for t in self.tasks if t.is_valid()]

    def add(self, task: MemoryUpdateTask) -> None:
        self.tasks.append(task)

    def add_from_candidate(
        self,
        subject_entity_id: str,
        predicate: str,
        object_value: str | int | float | bool | None,
        object_entity_id: str | None = None,
        qualifiers: dict[str, Any] | None = None,
        domain: str = "general",
        confidence: float = 0.5,
        trust: float = 0.5,
        evidence_span: str = "",
        reason: str = "",
    ) -> None:
        self.tasks.append(MemoryUpdateTask(
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=object_entity_id,
            qualifiers=qualifiers or {},
            domain=domain,
            confidence=confidence,
            trust=trust,
            evidence_span=evidence_span,
            reason=reason,
        ))
