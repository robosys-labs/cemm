"""GraphPatch validation and consolidation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..memory.concept_lattice import ConceptLattice
from ..memory.construction_lattice import ConstructionLattice
from ..memory.episodic_trace_store import EpisodicTraceStore
from ..types.graph_patch import GraphPatch
from ..types.uol_graph import UOLGraph


@dataclass
class ConsolidationResult:
    accepted_patch_ids: list[str] = field(default_factory=list)
    rejected_patch_ids: list[str] = field(default_factory=list)
    applied_targets: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)


class ConceptConsolidator:
    """Validate and apply graph patches to seed stores."""

    def __init__(
        self,
        concept_lattice: ConceptLattice,
        construction_lattice: ConstructionLattice | None = None,
        episodic_store: EpisodicTraceStore | None = None,
        confidence_threshold: float = 0.35,
        persistent_store: object = None,
    ) -> None:
        self._concept_lattice = concept_lattice
        self._construction_lattice = construction_lattice
        self._episodic_store = episodic_store
        self._confidence_threshold = confidence_threshold
        self._persistent_store = persistent_store

    def consolidate(
        self,
        patches: list[GraphPatch],
        *,
        source_graph: UOLGraph | None = None,
    ) -> ConsolidationResult:
        result = ConsolidationResult()
        merged = self._merge_compatible_patches(patches)
        for patch in merged:
            if not self._is_acceptable(patch):
                result.rejected_patch_ids.append(patch.id)
                result.reasons[patch.id] = "below_confidence_or_missing_operations"
                self._journal(patch, accepted=False)
                continue
            applied = self._apply(patch, source_graph)
            if applied:
                result.accepted_patch_ids.append(patch.id)
                result.applied_targets.extend(applied)
                self._journal(patch, accepted=True)
            else:
                result.rejected_patch_ids.append(patch.id)
                result.reasons[patch.id] = "no_matching_store_or_operation"
                self._journal(patch, accepted=False)
        return result

    def _apply(self, patch: GraphPatch, source_graph: UOLGraph | None) -> list[str]:
        if patch.target == "concept_lattice":
            return self._concept_lattice.apply_patch(patch)
        if patch.target == "construction_lattice" and self._construction_lattice is not None:
            return self._construction_lattice.apply_patch(patch)
        if patch.target == "episodic_trace" and self._episodic_store is not None and source_graph is not None:
            trace = self._episodic_store.retain_graph(source_graph, reason=patch.reason, score=patch.confidence)
            return [trace.trace_id]
        return []

    def _is_acceptable(self, patch: GraphPatch) -> bool:
        return bool(patch.operations) and patch.confidence >= self._confidence_threshold

    def _journal(self, patch: GraphPatch, accepted: bool) -> None:
        if self._persistent_store is not None:
            self._persistent_store.journal_patch(patch, accepted=accepted)

    @staticmethod
    def _merge_compatible_patches(patches: list[GraphPatch]) -> list[GraphPatch]:
        merged: list[GraphPatch] = []
        for patch in patches:
            for index, existing in enumerate(merged):
                if existing.target == patch.target and not existing.conflicts_with(patch):
                    merged[index] = existing.merge_with(patch)
                    break
            else:
                merged.append(patch)
        return merged

    def snapshot(self) -> dict[str, Any]:
        return {
            "concept_lattice": self._concept_lattice.snapshot(),
            "construction_lattice": self._construction_lattice.snapshot() if self._construction_lattice else {},
        }
