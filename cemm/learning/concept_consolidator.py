"""GraphPatch validation and consolidation with v4.2 lifecycle management.

Consolidation is the ONLY learning mechanism in CEMM v4.2. Every incoming
GraphPatch passes through compression-gain scoring, state-lifecycle advancement,
staleness/decay tracking, counterexample monitoring, and fingerprint-based
nearest-neighbor matching to avoid duplicate concepts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from ..memory.concept_lattice import ConceptLattice
from ..memory.construction_lattice import ConstructionLattice
from ..memory.episodic_trace_store import EpisodicTraceStore
from ..types.graph_patch import GraphPatch
from ..types.uol_graph import UOLGraph


CONCEPT_STATES = ["candidate_atom", "typed_candidate", "operational_atom", "consolidated_atom"]

_STATE_ORDER = {state: i for i, state in enumerate(CONCEPT_STATES)}


@dataclass
class ConsolidationResult:
    accepted_patch_ids: list[str] = field(default_factory=list)
    rejected_patch_ids: list[str] = field(default_factory=list)
    applied_targets: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    concept_state_changes: dict[str, str] = field(default_factory=dict)
    gain_scores: dict[str, float] = field(default_factory=dict)
    evicted_concept_ids: list[str] = field(default_factory=list)


class ConceptConsolidator:
    """Validate, score, and apply graph patches to seed stores with lifecycle management."""

    def __init__(
        self,
        concept_lattice: ConceptLattice,
        construction_lattice: ConstructionLattice | None = None,
        episodic_store: EpisodicTraceStore | None = None,
        confidence_threshold: float = 0.35,
        persistent_store: object = None,
        *,
        gain_threshold: float = 0.15,
        similarity_threshold: float = 0.85,
        staleness_days: int = 30,
        max_counterexamples: int = 3,
        router: Any = None,
    ) -> None:
        self._concept_lattice = concept_lattice
        self._construction_lattice = construction_lattice
        self._episodic_store = episodic_store
        self._confidence_threshold = confidence_threshold
        self._persistent_store = persistent_store
        self._router = router
        self._gain_threshold = gain_threshold
        self._similarity_threshold = similarity_threshold
        self._staleness_days = staleness_days
        self._max_counterexamples = max_counterexamples

        self._concept_states: dict[str, str] = {}
        self._concept_fingerprints: dict[str, set[str]] = {}
        self._staleness_tracker: dict[str, datetime] = {}
        self._counterexample_tracker: dict[str, int] = {}

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
            gain = self._compute_gain_score(patch, source_graph)
            result.gain_scores[patch.id] = gain
            if gain < self._gain_threshold:
                result.rejected_patch_ids.append(patch.id)
                result.reasons[patch.id] = f"gain_below_threshold_{gain:.3f}"
                self._journal(patch, accepted=False)
                continue
            concept_ids = self._resolve_concept_ids_from_patch(patch)
            has_duplicate = False
            for cid in concept_ids:
                existing = self._find_nearest_match(
                    self._compute_fingerprint(cid, "", set()),
                    self._concept_fingerprints,
                )
                if existing is not None and existing != cid:
                    result.reasons[patch.id] = f"merged_into_existing_{existing}"
                    self._track_counterexample(patch, cid)
                    has_duplicate = True
            if has_duplicate:
                result.rejected_patch_ids.append(patch.id)
                self._journal(patch, accepted=False)
                continue
            applied = self._apply(patch, source_graph)
            if applied:
                result.accepted_patch_ids.append(patch.id)
                result.applied_targets.extend(applied)
                self._journal(patch, accepted=True)
                for cid in concept_ids:
                    old_state = self._concept_states.get(cid, CONCEPT_STATES[0])
                    if cid in self._concept_states:
                        new_state = self._advance_state(cid, CONCEPT_STATES[min(
                            _STATE_ORDER.get(old_state, 0) + 1,
                            len(CONCEPT_STATES) - 1,
                        )])
                    else:
                        new_state = self._advance_state(cid, CONCEPT_STATES[1])
                    if new_state != old_state:
                        result.concept_state_changes[cid] = new_state
                    self._staleness_tracker[cid] = datetime.now(timezone.utc)
                    key = cid.replace("concept:", "")
                    surface = ""
                    for op in patch.operations:
                        sf = op.fields.get("surface", "")
                        if sf:
                            surface = sf
                            break
                    self._concept_fingerprints[cid] = self._compute_fingerprint(key, surface, set())
            else:
                result.rejected_patch_ids.append(patch.id)
                result.reasons[patch.id] = "no_matching_store_or_operation"
                self._journal(patch, accepted=False)
        stale_ids = self._check_staleness()
        if stale_ids:
            result.evicted_concept_ids = stale_ids
            for cid in stale_ids:
                self._concept_states.pop(cid, None)
                self._concept_fingerprints.pop(cid, None)
                self._staleness_tracker.pop(cid, None)
                self._counterexample_tracker.pop(cid, None)
        return result

    def _compute_gain_score(self, patch: GraphPatch, source_graph: UOLGraph | None) -> float:
        traces_explained = len(patch.operations) * 0.1
        prediction_gain = patch.confidence * 0.2
        repair_reduction = 0.0
        complexity_cost = len(patch.operations) * 0.05
        contradiction_count = 0
        for op in patch.operations:
            cc = op.fields.get("contradiction_count", None)
            if cc is not None:
                contradiction_count += int(cc)
        contradiction_cost = contradiction_count * 0.3
        return traces_explained + prediction_gain + repair_reduction - complexity_cost - contradiction_cost

    def _resolve_concept_ids_from_patch(self, patch: GraphPatch) -> list[str]:
        ids: dict[str, bool] = {}
        for op in patch.operations:
            target_id = op.target_id
            if target_id and target_id.startswith("concept:"):
                ids[target_id] = True
            key = op.fields.get("key", "")
            if key:
                ids[f"concept:{key}"] = True
        return list(ids)

    def _advance_state(self, concept_id: str, target_state: str) -> str:
        current = self._concept_states.get(concept_id, CONCEPT_STATES[0])
        target_idx = _STATE_ORDER.get(target_state, len(CONCEPT_STATES) - 1)
        current_idx = _STATE_ORDER.get(current, 0)
        new_state = CONCEPT_STATES[max(current_idx, target_idx)]
        self._concept_states[concept_id] = new_state
        return new_state

    def _demote_state(self, concept_id: str) -> str | None:
        current = self._concept_states.get(concept_id)
        if current is None:
            return None
        current_idx = _STATE_ORDER.get(current, 0)
        if current_idx <= 0:
            return current
        new_state = CONCEPT_STATES[current_idx - 1]
        self._concept_states[concept_id] = new_state
        return new_state

    def _check_staleness(self) -> list[str]:
        stale: list[str] = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self._staleness_days)
        for cid, last_seen in self._staleness_tracker.items():
            if last_seen < cutoff:
                stale.append(cid)
        return stale

    def _track_counterexample(self, patch: GraphPatch, concept_id: str) -> None:
        count = self._counterexample_tracker.get(concept_id, 0)
        for op in patch.operations:
            if op.operation == "mark_counterexample":
                count += 1
        self._counterexample_tracker[concept_id] = count
        if count >= self._max_counterexamples:
            self._demote_state(concept_id)

    def _compute_fingerprint(self, key: str, surface: str, roles: set[str]) -> set[str]:
        tokens: set[str] = set()
        for s in [key, surface]:
            for part in s.lower().replace(":", "_").split("_"):
                tokens.update(part.split())
        tokens.update(roles)
        return tokens

    @staticmethod
    def _fingerprint_similarity(fp1: set[str], fp2: set[str]) -> float:
        if not fp1 or not fp2:
            return 0.0
        intersection = fp1 & fp2
        union = fp1 | fp2
        return len(intersection) / len(union)

    def _find_nearest_match(
        self,
        fingerprint: set[str],
        existing_fingerprints: dict[str, set[str]],
    ) -> str | None:
        best_id: str | None = None
        best_score = 0.0
        for cid, fp in existing_fingerprints.items():
            score = self._fingerprint_similarity(fingerprint, fp)
            if score > best_score:
                best_score = score
                best_id = cid
        if best_score >= self._similarity_threshold:
            return best_id
        return None

    def _apply(self, patch: GraphPatch, source_graph: UOLGraph | None) -> list[str]:
        if self._router is not None:
            return self._router.route(patch, source_graph)
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
        if hasattr(self, '_persistent_store') and self._persistent_store is not None:
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
            "concept_states": dict(self._concept_states),
            "concept_fingerprints": {
                cid: sorted(fp) for cid, fp in self._concept_fingerprints.items()
            },
            "staleness_tracker": {
                cid: ts.isoformat() for cid, ts in self._staleness_tracker.items()
            },
            "counterexample_tracker": dict(self._counterexample_tracker),
            "config": {
                "gain_threshold": self._gain_threshold,
                "similarity_threshold": self._similarity_threshold,
                "staleness_days": self._staleness_days,
                "max_counterexamples": self._max_counterexamples,
            },
        }
