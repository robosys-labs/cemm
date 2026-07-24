"""Dependence-aware evidence fusion for CEMM v3.5.1 Phase 17."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, tanh


@dataclass(frozen=True, slots=True)
class EvidenceContributionV351:
    contribution_ref: str
    score: float
    evidence_refs: tuple[str, ...]
    lineage_refs: tuple[str, ...] = ()
    dependence_ref: str = ""

    def __post_init__(self) -> None:
        if not self.contribution_ref:
            raise ValueError("contribution_ref is required")
        value = float(self.score)
        if not isfinite(value) or not -1.0 <= value <= 1.0:
            raise ValueError("evidence contribution score must be within [-1,1]")
        if not self.evidence_refs:
            raise ValueError("evidence contribution requires evidence")


@dataclass(frozen=True, slots=True)
class FusedEvidenceV351:
    fused_score: float
    cluster_scores: tuple[tuple[str, float], ...]
    evidence_refs: tuple[str, ...]
    lineage_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]


class DependenceAwareEvidenceFusionV351:
    """Fuse evidence by dependence quotient classes, never derivation count.

    Without an exact joint model, correlated transforms are intentionally conservative:
    same-sign transforms contribute only the weakest magnitude in their dependence class;
    conflicting signs cancel that class to neutral. Independent observations receive
    independent classes. This prevents duplicated preprocessing from manufacturing support.
    """

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "dependence_aware_evidence_fusion"

    @staticmethod
    def _cluster_score(values: tuple[float, ...]) -> float:
        positives = tuple(value for value in values if value > 0.0)
        negatives = tuple(value for value in values if value < 0.0)
        if positives and negatives:
            return 0.0
        if positives:
            return min(positives)
        if negatives:
            return -min(abs(value) for value in negatives)
        return 0.0

    def fuse(self, contributions) -> FusedEvidenceV351:
        contributions = tuple(contributions)
        clusters: dict[str, list[EvidenceContributionV351]] = {}
        for item in contributions:
            if not isinstance(item, EvidenceContributionV351):
                raise TypeError("fusion accepts EvidenceContributionV351 only")
            key = item.dependence_ref.strip() or f"independent:{item.contribution_ref}"
            clusters.setdefault(key, []).append(item)
        scores = tuple(
            (key, self._cluster_score(tuple(float(item.score) for item in clusters[key])))
            for key in sorted(clusters)
        )
        # Bounded aggregation is across dependence classes, never within duplicated transforms.
        fused = tanh(sum(score for _key, score in scores)) if scores else 0.0
        evidence = tuple(sorted({ref for item in contributions for ref in item.evidence_refs}))
        lineage = tuple(sorted({ref for item in contributions for ref in item.lineage_refs}))
        proof = (
            "proof:dependence-quotient-fusion-v351",
            "proof:correlated-without-joint-model-weakest-magnitude-v351",
        )
        return FusedEvidenceV351(fused, scores, evidence, lineage, proof)


__all__ = ["DependenceAwareEvidenceFusionV351", "EvidenceContributionV351", "FusedEvidenceV351"]
