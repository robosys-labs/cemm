from __future__ import annotations

import uuid
from typing import Any

from ..memory.durable_semantic_store import CommitResult, DurableSemanticStore
from ..types.graph_patch import GraphPatch


class PatchCommitter:
    def __init__(self, durable_store: DurableSemanticStore | None = None) -> None:
        self._store = durable_store or DurableSemanticStore()

    @property
    def store(self) -> DurableSemanticStore:
        return self._store

    def commit(self, patch: GraphPatch, validation: Any) -> CommitResult:
        if not validation.accepted:
            status = validation.status if validation.status in {"rejected", "needs_confirmation"} else "quarantined"
            return CommitResult(
                commit_id=uuid.uuid4().hex[:16],
                status=status,
                rejected_operation_target_ids=[
                    str(item).split(":", 1)[0]
                    for item in getattr(validation, "rejected_operations", []) or []
                    if item
                ],
            )
        return self._store.apply_validated_patch(patch, validation)

    def commit_batch(self, patches: list[GraphPatch], validations: list[Any]) -> list[CommitResult]:
        results: list[CommitResult] = []
        for index, patch in enumerate(patches):
            validation = validations[index] if index < len(validations) else None
            if validation is None:
                results.append(CommitResult(
                    commit_id=uuid.uuid4().hex[:16],
                    status="rejected",
                    rejected_operation_target_ids=[op.target_id for op in patch.operations if op.target_id],
                ))
                continue
            try:
                results.append(self.commit(patch, validation))
            except Exception as exc:  # fail closed; caller receives a rejected result
                results.append(CommitResult(
                    commit_id=uuid.uuid4().hex[:16],
                    status="rejected",
                    rejected_operation_target_ids=[op.target_id for op in patch.operations if op.target_id],
                    errors=[f"{type(exc).__name__}: {exc}"],
                ))
        return results

    def get_stored_relation_frames(
        self,
        relation_key: str = "",
        subject_concept_id: str = "",
        subject_entity_id: str = "",
        object_concept_id: str = "",
        object_entity_id: str = "",
        dimension: str = "",
    ) -> list[Any]:
        return self._store.query_relations(
            relation_key=relation_key,
            subject_concept_id=subject_concept_id,
            subject_entity_id=subject_entity_id,
            object_concept_id=object_concept_id,
            object_entity_id=object_entity_id,
            dimension=dimension,
            active_only=True,
        )
