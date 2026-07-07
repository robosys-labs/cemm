from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


GRAPH_PATCH_TARGETS = frozenset({
    "concept_lattice",
    "construction_lattice",
    "predicate_schema",
    "causal_affordance",
    "episodic_trace",
    "source_policy",
    "discard",
})

PATCH_OPERATION_TYPES = frozenset({
    "upsert_relation_candidate",
    "upsert_concept_candidate",
    "upsert_state",
    "observe_port_binding",
    "observe_construction_match",
    "observe_predicate_schema",
    "observe_causal_affordance",
    "update_source_policy",
    "retain_exemplar",
    "discard_trace",
    "merge_concepts",
    "mark_counterexample",
    "update_claim_status",
    "custom",
})


@dataclass
class PatchOperation:
    operation: str
    target_id: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    reason: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        self.operation = self._canonical_operation(self.operation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "target_id": self.target_id,
            "fields": dict(self.fields),
            "confidence": self.confidence,
            "reason": self.reason,
            "schema_version": self.schema_version,
        }

    @staticmethod
    def _canonical_operation(operation: str) -> str:
        clean = (operation or "").strip().lower()
        if clean.startswith("custom:"):
            return clean
        if clean not in PATCH_OPERATION_TYPES:
            raise ValueError(f"unknown graph patch operation: {operation!r}")
        return clean


@dataclass
class GraphPatch:
    id: str = ""
    source_graph_id: str = ""
    target: str = "discard"
    operations: list[PatchOperation] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    permission_refs: list[str] = field(default_factory=list)
    inverse_operations: list[PatchOperation] = field(default_factory=list)
    conflict_set_id: str = ""
    schema_version: int = 1
    confidence: float = 0.5
    reason: str = ""

    def __post_init__(self) -> None:
        self.target = self._canonical_target(self.target)
        if not self.id:
            stem = f"{self.source_graph_id}:{self.target}:{self.reason}:{len(self.operations)}"
            self.id = "patch_" + uuid.uuid5(uuid.NAMESPACE_URL, stem).hex[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_graph_id": self.source_graph_id,
            "target": self.target,
            "operations": [operation.to_dict() for operation in self.operations],
            "source_refs": list(self.source_refs),
            "evidence_refs": list(self.evidence_refs),
            "permission_refs": list(self.permission_refs),
            "inverse_operations": [operation.to_dict() for operation in self.inverse_operations],
            "conflict_set_id": self.conflict_set_id,
            "schema_version": self.schema_version,
            "confidence": self.confidence,
            "reason": self.reason,
        }

    def conflicts_with(self, other: GraphPatch) -> bool:
        if self.conflict_set_id and self.conflict_set_id == other.conflict_set_id:
            return True
        own_targets = {(operation.operation, operation.target_id) for operation in self.operations}
        other_targets = {(operation.operation, operation.target_id) for operation in other.operations}
        return bool(own_targets & other_targets and self.target == other.target)

    def merge_with(self, other: GraphPatch) -> GraphPatch:
        if self.target != other.target:
            raise ValueError("cannot merge graph patches with different targets")
        operations = [*self.operations]
        seen = {(operation.operation, operation.target_id) for operation in operations}
        for operation in other.operations:
            key = (operation.operation, operation.target_id)
            if key not in seen:
                operations.append(operation)
                seen.add(key)
        return GraphPatch(
            source_graph_id=self.source_graph_id or other.source_graph_id,
            target=self.target,
            operations=operations,
            source_refs=sorted({*self.source_refs, *other.source_refs}),
            evidence_refs=sorted({*self.evidence_refs, *other.evidence_refs}),
            permission_refs=sorted({*self.permission_refs, *other.permission_refs}),
            inverse_operations=[*self.inverse_operations, *other.inverse_operations],
            conflict_set_id=self.conflict_set_id or other.conflict_set_id,
            schema_version=max(self.schema_version, other.schema_version),
            confidence=max(self.confidence, other.confidence),
            reason="merged_graph_patch",
        )

    @staticmethod
    def _canonical_target(target: str) -> str:
        clean = (target or "discard").strip().lower()
        if clean not in GRAPH_PATCH_TARGETS:
            raise ValueError(f"unknown graph patch target: {target!r}")
        return clean
