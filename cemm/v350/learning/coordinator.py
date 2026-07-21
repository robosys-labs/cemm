"""Shadow Stage-11 learning coordinator.

This coordinator collects frontiers and candidate evidence. It deliberately
contains no automatic promotion path; promotion requires durable competence,
review, authorization, and the PromotionCoordinator CAS boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record, record_ref, record_revision
from ..storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordKind
from .frontier import FrontierCollector, FrontierObservation
from .model import LearningBudget, LearningFrontierRecord


@dataclass(frozen=True, slots=True)
class LearningCycleTrace:
    trace_ref: str
    snapshot_revision: int
    frontier_refs: tuple[str, ...]
    persisted: bool
    promotion_attempted: bool = False


class LearningCoordinator:
    def __init__(self, store, budget: LearningBudget | None = None) -> None:
        self.store = store
        self.budget = budget or LearningBudget()
        self.frontiers = FrontierCollector(self.budget)

    def collect_frontiers(
        self,
        observations: Iterable[FrontierObservation],
        *,
        persist: bool = False,
        source_ref: str = "source:phase13:runtime-frontier",
    ) -> LearningCycleTrace:
        with self.store.snapshot() as snapshot:
            existing = tuple(
                item.payload for item in self.store.repositories.learning_frontiers.all(all_revisions=True)
                if isinstance(item.payload, LearningFrontierRecord)
            ) if hasattr(self.store.repositories, "learning_frontiers") else ()
            produced = self.frontiers.collect(observations, existing)
            patches = []
            if persist and produced:
                grouped = {}
                for item in produced:
                    grouped.setdefault(
                        (item.context_ref, item.permission_ref), []
                    ).append(item)
                for (context_ref, permission_ref), group in sorted(grouped.items()):
                    operations = tuple(PatchOperation(
                    operation_ref="patch-operation:learning-frontier:" + semantic_fingerprint(
                        "learning-frontier-operation", (item.frontier_ref, item.revision), 20
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.LEARNING_FRONTIER,
                    target_ref=record_ref(RecordKind.LEARNING_FRONTIER, item),
                    record_revision=record_revision(RecordKind.LEARNING_FRONTIER, item),
                    payload=encode_record(RecordKind.LEARNING_FRONTIER, item),
                    reason="persist typed unresolved learning frontier without granting authority",
                    ) for item in group)
                    patches.append(GraphPatch(
                    patch_ref="graph-patch:learning-frontiers:" + semantic_fingerprint(
                        "learning-frontiers-patch", (snapshot.fingerprint, context_ref, permission_ref, tuple((item.frontier_ref, item.revision) for item in group)), 24
                    ),
                    context_ref=context_ref,
                    scope_ref="phase13:learning-shadow",
                    source_ref=source_ref,
                    permission_ref=permission_ref,
                    operations=operations,
                    expected_store_revision=snapshot.store_revision,
                    validation_requirements=("phase13_frontiers_are_not_authority",),
                    metadata={"phase": 13, "runtime_cutover": False, "automatic_promotion": False},
                    ))
            trace_ref = "learning-trace:" + semantic_fingerprint(
                "learning-cycle-trace", (snapshot.fingerprint, tuple((item.frontier_ref, item.revision) for item in produced), persist), 24
            )
            trace = LearningCycleTrace(trace_ref, snapshot.store_revision, tuple(item.frontier_ref for item in produced), persist)
        for index, patch in enumerate(patches):
            if index:
                with self.store.snapshot() as refreshed:
                    from dataclasses import replace
                    patch = replace(
                        patch,
                        expected_store_revision=refreshed.store_revision,
                    )
            result = self.store.apply_patch(patch)
            if not result.committed:
                raise ValueError("frontier persistence failed: " + "; ".join(result.errors))
        return trace
