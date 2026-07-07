"""Select semantic read units for anytime distillation."""

from __future__ import annotations

from .types import DeliberationPlan, DocumentMap, ReadUnit

_CORE_SECTION_ROLES = {"abstract", "toc", "intro", "conclusion", "executive_summary"}
_ARTIFACT_PRIORITY = {"table": 1, "figure": 2, "equation": 3, "code_block": 3, "citation": 6}


class ReadUnitSelector:
    def select(self, document_maps: list[DocumentMap], plan: DeliberationPlan, *, budget_ms: float = 0.0) -> list[ReadUnit]:
        if plan.distillation_policy == "none" or not document_maps:
            return []
        units: list[ReadUnit] = []
        for doc in document_maps:
            units.extend(self._metadata_units(doc))
            if plan.strategy == "rapid_skim":
                units.extend(self._rapid_skim_units(doc))
            elif plan.strategy == "recursive_distill":
                units.extend(self._recursive_units(doc, plan.max_recursive_steps))
            elif plan.strategy == "deep_synthesis":
                units.extend(self._deep_units(doc))
            elif plan.strategy == "partial_with_limits":
                units.extend(self._rapid_skim_units(doc, minimal=True))
        units = self._dedupe(units)
        units.sort(key=lambda u: (u.priority, u.cost_ms, u.unit_id))
        return self._fit_budget(units, budget_ms)

    @staticmethod
    def _metadata_units(doc: DocumentMap) -> list[ReadUnit]:
        return [ReadUnit(
            unit_id=f"{doc.source_id}:metadata",
            source_id=doc.source_id,
            unit_type="metadata",
            priority=0,
            cost_ms=30.0,
            coverage_weight=1.0,
            required=True,
            reason="source_map",
            source_refs=tuple(doc.metadata_refs),
        )]

    def _rapid_skim_units(self, doc: DocumentMap, minimal: bool = False) -> list[ReadUnit]:
        units: list[ReadUnit] = []
        core = [s for s in doc.sections if s.role in _CORE_SECTION_ROLES]
        body = [s for s in doc.sections if s.role not in _CORE_SECTION_ROLES]
        for section in sorted(core, key=lambda s: (s.index, -s.salience)):
            units.append(self._section_unit(doc.source_id, section, "section_full", priority=1, cost=160.0, weight=1.2, reason="core_section"))
        if not minimal:
            salient_body = sorted(body, key=lambda s: (-s.salience, s.index))[: max(3, min(12, len(body)))]
        else:
            salient_body = sorted(body, key=lambda s: (-s.salience, s.index))[: min(4, len(body))]
        for section in salient_body:
            units.append(self._section_unit(doc.source_id, section, "section_boundary", priority=3, cost=80.0, weight=0.55, reason="boundary_sample"))
        artifact_cap = 3 if minimal else 10
        for artifact in sorted(doc.artifacts, key=lambda a: (_ARTIFACT_PRIORITY.get(a.artifact_type, 5), -a.salience, a.artifact_id))[:artifact_cap]:
            units.append(ReadUnit(
                unit_id=f"{doc.source_id}:artifact:{artifact.artifact_id}",
                source_id=doc.source_id,
                unit_type="artifact",
                target_id=artifact.artifact_id,
                priority=_ARTIFACT_PRIORITY.get(artifact.artifact_type, 5),
                cost_ms=120.0,
                coverage_weight=0.8,
                reason=f"artifact:{artifact.artifact_type}",
                source_refs=tuple(artifact.source_refs),
            ))
        return units

    def _recursive_units(self, doc: DocumentMap, recursive_steps: int) -> list[ReadUnit]:
        units = self._rapid_skim_units(doc)
        cap = max(8, min(32, 8 + recursive_steps * 8))
        body = sorted(doc.sections, key=lambda s: (-s.salience, s.depth, s.index))[:cap]
        for section in body:
            units.append(self._section_unit(doc.source_id, section, "section_full", priority=4, cost=220.0, weight=1.0, reason="recursive_section"))
        return units

    def _deep_units(self, doc: DocumentMap) -> list[ReadUnit]:
        units = self._rapid_skim_units(doc)
        for section in sorted(doc.sections, key=lambda s: (s.depth, s.index)):
            units.append(self._section_unit(doc.source_id, section, "section_full", priority=5, cost=240.0, weight=1.0, reason="deep_section"))
        for artifact in doc.artifacts:
            units.append(ReadUnit(
                unit_id=f"{doc.source_id}:artifact:{artifact.artifact_id}",
                source_id=doc.source_id,
                unit_type="artifact",
                target_id=artifact.artifact_id,
                priority=5,
                cost_ms=140.0,
                coverage_weight=0.8,
                reason="deep_artifact",
                source_refs=tuple(artifact.source_refs),
            ))
        return units

    @staticmethod
    def _section_unit(source_id: str, section, unit_type: str, priority: int, cost: float, weight: float, reason: str) -> ReadUnit:
        return ReadUnit(
            unit_id=f"{source_id}:{unit_type}:{section.section_id}",
            source_id=source_id,
            unit_type=unit_type,
            target_id=section.section_id,
            priority=priority,
            cost_ms=cost,
            coverage_weight=weight,
            required=section.role in _CORE_SECTION_ROLES,
            reason=reason,
            source_refs=tuple(section.source_refs),
        )

    @staticmethod
    def _dedupe(units: list[ReadUnit]) -> list[ReadUnit]:
        best: dict[str, ReadUnit] = {}
        for unit in units:
            existing = best.get(unit.unit_id)
            if existing is None or (unit.priority, unit.cost_ms) < (existing.priority, existing.cost_ms):
                best[unit.unit_id] = unit
        return list(best.values())

    @staticmethod
    def _fit_budget(units: list[ReadUnit], budget_ms: float) -> list[ReadUnit]:
        if budget_ms <= 0:
            return units
        selected: list[ReadUnit] = []
        spent = 0.0
        for unit in units:
            if unit.required or spent + unit.cost_ms <= budget_ms:
                selected.append(unit)
                spent += unit.cost_ms
        return selected
