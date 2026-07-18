"""Typed learning frontier collection and evidence aggregation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from ..schema.model import SchemaClass, semantic_fingerprint
from ..storage.model import RecordKind
from .model import (
    EvidencePolarity,
    FrontierResolutionStatus,
    LearningBudget,
    LearningEvidenceLink,
    LearningFrontierRecord,
)


@dataclass(frozen=True, slots=True)
class FrontierObservation:
    missing_contract: str
    expected_record_kinds: tuple[RecordKind, ...]
    expected_schema_classes: tuple[SchemaClass, ...]
    accepted_anchor_types: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    candidate_refs: tuple[str, ...] = ()
    target_ref: str | None = None
    dependency_depth: int = 0
    sensitivity: str = "normal"
    best_question_uol_ref: str | None = None
    context_ref: str = "actual"
    permission_ref: str = "conversation"


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    support_link_refs: tuple[str, ...]
    counterexample_link_refs: tuple[str, ...]
    correction_link_refs: tuple[str, ...]
    retraction_link_refs: tuple[str, ...]
    independent_support_lineages: tuple[str, ...]
    independent_counterexample_lineages: tuple[str, ...]
    support_weight: float
    counterexample_weight: float

    @property
    def contradicted(self) -> bool:
        return bool(self.counterexample_link_refs or self.correction_link_refs or self.retraction_link_refs)


class FrontierCollector:
    """Deduplicate unresolved needs by structure, never by surface wording."""

    def __init__(self, budget: LearningBudget | None = None) -> None:
        self.budget = budget or LearningBudget()

    def collect(
        self,
        observations: Iterable[FrontierObservation],
        existing: Iterable[LearningFrontierRecord] = (),
    ) -> tuple[LearningFrontierRecord, ...]:
        by_key = {item.structural_key: item for item in existing if item.resolution_status != FrontierResolutionStatus.SUPERSEDED}
        produced: list[LearningFrontierRecord] = []
        for observation in observations:
            if observation.dependency_depth > self.budget.maximum_dependency_depth:
                continue
            probe = LearningFrontierRecord(
                frontier_ref="frontier:probe",
                missing_contract=observation.missing_contract,
                expected_record_kinds=tuple(sorted(set(observation.expected_record_kinds), key=lambda item: item.value)),
                expected_schema_classes=tuple(sorted(set(observation.expected_schema_classes), key=lambda item: item.value)),
                accepted_anchor_types=tuple(sorted(set(observation.accepted_anchor_types))),
                evidence_refs=tuple(sorted(set(observation.evidence_refs))),
                candidate_refs=tuple(sorted(set(observation.candidate_refs))),
                target_ref=observation.target_ref,
                dependency_depth=observation.dependency_depth,
                sensitivity=observation.sensitivity,
                best_question_uol_ref=observation.best_question_uol_ref,
                context_ref=observation.context_ref,
                permission_ref=observation.permission_ref,
            )
            current = by_key.get(probe.structural_key)
            if current is None:
                frontier_ref = "learning-frontier:" + semantic_fingerprint("learning-frontier-ref", probe.structural_key, 24)
                item = replace(probe, frontier_ref=frontier_ref)
            else:
                item = replace(
                    current,
                    revision=current.revision + 1,
                    supersedes_revision=current.revision,
                    evidence_refs=tuple(sorted(set((*current.evidence_refs, *observation.evidence_refs)))),
                    candidate_refs=tuple(sorted(set((*current.candidate_refs, *observation.candidate_refs)))),
                    dependency_depth=min(current.dependency_depth, observation.dependency_depth),
                    best_question_uol_ref=observation.best_question_uol_ref or current.best_question_uol_ref,
                    resolution_status=FrontierResolutionStatus.OPEN,
                )
            by_key[item.structural_key] = item
            produced.append(item)
            if len(by_key) >= self.budget.maximum_frontiers:
                break
        return tuple(sorted(produced, key=lambda item: (item.frontier_ref, item.revision)))


class EvidenceAggregator:
    """Aggregate attributable evidence without converting frequency into authority."""

    @staticmethod
    def summarize(links: Iterable[LearningEvidenceLink]) -> EvidenceSummary:
        support = []
        counter = []
        correction = []
        retraction = []
        support_lineages: set[str] = set()
        counter_lineages: set[str] = set()
        support_weight = 0.0
        counter_weight = 0.0
        for item in links:
            if item.polarity == EvidencePolarity.SUPPORT:
                support.append(item.link_ref)
                support_lineages.update(item.source_lineage_refs)
                support_weight += item.weight
            elif item.polarity == EvidencePolarity.COUNTEREXAMPLE:
                counter.append(item.link_ref)
                counter_lineages.update(item.source_lineage_refs)
                counter_weight += item.weight
            elif item.polarity == EvidencePolarity.CORRECTION:
                correction.append(item.link_ref)
                counter_lineages.update(item.source_lineage_refs)
                counter_weight += item.weight
            elif item.polarity == EvidencePolarity.RETRACTION:
                retraction.append(item.link_ref)
                counter_lineages.update(item.source_lineage_refs)
                counter_weight += item.weight
        return EvidenceSummary(
            tuple(sorted(support)), tuple(sorted(counter)), tuple(sorted(correction)), tuple(sorted(retraction)),
            tuple(sorted(support_lineages)), tuple(sorted(counter_lineages)), support_weight, counter_weight,
        )
