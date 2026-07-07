"""Coverage estimation for deliberation/distillation."""

from __future__ import annotations

from .types import DistilledUnit, DocumentMap, ReadUnit


class CoverageEstimator:
    def estimate_plan(self, document_maps: list[DocumentMap], read_units: list[ReadUnit]) -> float:
        denom = sum(max(1, m.coverage_denominator or len(m.sections) + len(m.artifacts) + 1) for m in document_maps)
        if denom <= 0:
            return 0.0
        covered = sum(max(0.0, unit.coverage_weight) for unit in read_units)
        return max(0.0, min(1.0, covered / float(denom)))

    def estimate_result(self, document_maps: list[DocumentMap], units: list[DistilledUnit]) -> float:
        denom = sum(max(1, m.coverage_denominator or len(m.sections) + len(m.artifacts) + 1) for m in document_maps)
        if denom <= 0:
            return 0.0
        covered = sum(max(0.0, unit.coverage_weight) for unit in units)
        return max(0.0, min(1.0, covered / float(denom)))
