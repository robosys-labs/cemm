"""Anytime distillation loop for structured sources.

This class consumes a DistillationPlan and a content provider. It never parses
natural-language deadlines or user commands; it only executes already-selected
semantic read units until its budget or stop conditions are met.
"""

from __future__ import annotations

from typing import Any

from .coverage_estimator import CoverageEstimator
from .read_unit_selector import ReadUnitSelector
from .source_mapper import SourceMapper
from .types import (
    ContentProvider,
    DeliberationPlan,
    DistillationPlan,
    DistillationResult,
    DistilledUnit,
    DocumentMap,
    ReadUnit,
)


class AnytimeDistiller:
    def __init__(self) -> None:
        self._source_mapper = SourceMapper()
        self._selector = ReadUnitSelector()
        self._coverage = CoverageEstimator()

    def build_plan(
        self,
        sources: list[Any],
        deliberation_plan: DeliberationPlan,
        *,
        budget_ms: float = 0.0,
    ) -> tuple[DistillationPlan, list[DocumentMap]]:
        maps = [self._source_mapper.map_document(source) for source in sources]
        read_units = self._selector.select(maps, deliberation_plan, budget_ms=budget_ms)
        coverage = self._coverage.estimate_plan(maps, read_units)
        blind_spots = self._blind_spots(maps, read_units, coverage, deliberation_plan)
        distill = DistillationPlan(
            strategy=deliberation_plan.distillation_policy,
            source_ids=[m.source_id for m in maps],
            read_units=read_units,
            recursive_passes=deliberation_plan.max_recursive_steps,
            sampling_policy=deliberation_plan.depth,
            coverage_estimate=coverage,
            expected_blind_spots=blind_spots,
            diagnostics={
                "document_count": len(maps),
                "read_unit_count": len(read_units),
                "strategy": deliberation_plan.strategy,
            },
        )
        return distill, maps

    def distill(
        self,
        sources: list[Any],
        deliberation_plan: DeliberationPlan,
        *,
        content_provider: ContentProvider | None = None,
        budget_ms: float = 0.0,
    ) -> DistillationResult:
        plan, maps = self.build_plan(sources, deliberation_plan, budget_ms=budget_ms)
        if plan.strategy == "none" or not plan.read_units:
            return DistillationResult(strategy=plan.strategy, partial=False, diagnostics={"reason": "no_distillation"})
        provider = content_provider or self._default_provider
        distilled: list[DistilledUnit] = []
        spent = 0.0
        for unit in plan.read_units:
            if budget_ms > 0 and not unit.required and spent + unit.cost_ms > budget_ms:
                break
            payload = provider(unit)
            distilled.append(self._distill_unit(unit, payload))
            spent += unit.cost_ms
            if self._should_stop(deliberation_plan, maps, distilled):
                break
        coverage = self._coverage.estimate_result(maps, distilled)
        evidence_refs = self._dedupe([ref for unit in distilled for ref in unit.evidence_refs])
        confidence = self._confidence(deliberation_plan, coverage, distilled)
        return DistillationResult(
            strategy=plan.strategy,
            units=distilled,
            merged_atoms=[atom for unit in distilled for atom in unit.summary_atoms],
            evidence_refs=evidence_refs,
            coverage_estimate=coverage,
            confidence=confidence,
            blind_spots=self._blind_spots(maps, plan.read_units, coverage, deliberation_plan),
            partial=coverage < deliberation_plan.coverage_target,
            diagnostics={
                "planned_unit_count": len(plan.read_units),
                "read_unit_count": len(distilled),
                "spent_ms_estimate": spent,
                "coverage_target": deliberation_plan.coverage_target,
                "confidence_target": deliberation_plan.confidence_target,
            },
        )

    @staticmethod
    def _default_provider(unit: ReadUnit) -> Any:
        return {"unit_id": unit.unit_id, "source_refs": list(unit.source_refs), "semantic_payload_available": False}

    @staticmethod
    def _distill_unit(unit: ReadUnit, payload: Any) -> DistilledUnit:
        atoms: list[Any] = []
        evidence_refs: list[str] = list(unit.source_refs)
        confidence = 0.5
        if isinstance(payload, dict):
            atoms = list(payload.get("summary_atoms", []) or payload.get("atoms", []) or [])
            evidence_refs.extend(str(ref) for ref in payload.get("evidence_refs", []) or [] if ref)
            confidence = float(payload.get("confidence", confidence) or confidence)
        else:
            atoms = list(getattr(payload, "summary_atoms", []) or getattr(payload, "atoms", []) or [])
            evidence_refs.extend(str(ref) for ref in getattr(payload, "evidence_refs", []) or [] if ref)
            confidence = float(getattr(payload, "confidence", confidence) or confidence)
        return DistilledUnit(
            unit_id=unit.unit_id,
            source_id=unit.source_id,
            unit_type=unit.unit_type,
            payload=payload,
            summary_atoms=atoms,
            evidence_refs=AnytimeDistiller._dedupe(evidence_refs),
            confidence=confidence,
            coverage_weight=unit.coverage_weight,
            diagnostics={"reason": unit.reason, "cost_ms": unit.cost_ms},
        )

    @staticmethod
    def _should_stop(plan: DeliberationPlan, maps: list[DocumentMap], units: list[DistilledUnit]) -> bool:
        coverage = CoverageEstimator().estimate_result(maps, units)
        confidence = AnytimeDistiller._confidence(plan, coverage, units)
        return coverage >= plan.coverage_target and confidence >= plan.confidence_target

    @staticmethod
    def _confidence(plan: DeliberationPlan, coverage: float, units: list[DistilledUnit]) -> float:
        if not units:
            return 0.0
        avg = sum(u.confidence for u in units) / len(units)
        # Coverage constrains confidence; partial reading should not pretend full confidence.
        return max(0.0, min(1.0, (avg * 0.65) + (coverage * 0.35)))

    @staticmethod
    def _blind_spots(
        maps: list[DocumentMap],
        read_units: list[ReadUnit],
        coverage: float,
        plan: DeliberationPlan,
    ) -> list[str]:
        blind: list[str] = []
        if coverage < plan.coverage_target:
            blind.append("coverage_below_target")
        selected_targets = {u.target_id for u in read_units if u.target_id}
        for doc in maps:
            unread_sections = [s.section_id for s in doc.sections if s.section_id not in selected_targets]
            unread_artifacts = [a.artifact_id for a in doc.artifacts if a.artifact_id not in selected_targets]
            if unread_sections:
                blind.append(f"unread_sections:{doc.source_id}:{len(unread_sections)}")
            if unread_artifacts:
                blind.append(f"unread_artifacts:{doc.source_id}:{len(unread_artifacts)}")
        return blind

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        out: list[str] = []
        for value in values:
            if value and value not in out:
                out.append(value)
        return out
