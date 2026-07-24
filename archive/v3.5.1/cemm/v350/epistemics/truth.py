"""Four-state truth aggregation over independent epistemic admissions."""
from __future__ import annotations

from math import prod

from ..schema.model import semantic_fingerprint
from ..storage import (
    AdmissionDecision, AdmissionLifecycleStatus, EpistemicAdmissionRecord,
    KnowledgeRecord, KnowledgeStatus,
)
from .model import EpistemicProjection, FourStateTruthAssessment


class FourStateTruthProjector:
    @staticmethod
    def _latest(
        admissions: tuple[EpistemicAdmissionRecord, ...],
    ) -> dict[str, EpistemicAdmissionRecord]:
        latest: dict[str, EpistemicAdmissionRecord] = {}
        for item in sorted(admissions, key=lambda value: (value.admission_ref, value.revision)):
            current = latest.get(item.admission_ref)
            if current is None or item.revision > current.revision:
                latest[item.admission_ref] = item
        return latest

    def _active_admissions(
        self,
        proposition_ref: str,
        context_ref: str,
        admissions: tuple[EpistemicAdmissionRecord, ...],
    ) -> tuple[EpistemicAdmissionRecord, ...]:
        relevant = tuple(
            item for item in admissions
            if item.proposition_ref == proposition_ref and item.target_context_ref == context_ref
        )
        latest = self._latest(relevant)
        retracted: set[str] = set()
        for retraction in latest.values():
            if (
                retraction.decision != AdmissionDecision.RETRACT
                or retraction.lifecycle_status != AdmissionLifecycleStatus.ACTIVE
                or not retraction.retracts_admission_ref
            ):
                continue
            target = latest.get(retraction.retracts_admission_ref)
            if target is None:
                continue
            # A retraction is source-local even before durable commit validation.
            # This keeps pure projection safe when handed uncommitted candidates.
            if not set(retraction.source_refs).intersection(target.source_refs):
                continue
            retracted.add(target.admission_ref)
        return tuple(sorted((
            item for item in latest.values()
            if item.admission_ref not in retracted
            and item.lifecycle_status == AdmissionLifecycleStatus.ACTIVE
            and item.decision in {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION}
        ), key=lambda item: (item.admission_ref, item.revision)))

    def assess(
        self,
        proposition_ref: str,
        context_ref: str,
        admissions: tuple[EpistemicAdmissionRecord, ...],
    ) -> FourStateTruthAssessment:
        active = self._active_admissions(proposition_ref, context_ref, admissions)
        supports = tuple(sorted(item.admission_ref for item in active if item.truth_status == KnowledgeStatus.SUPPORTED))
        oppositions = tuple(sorted(item.admission_ref for item in active if item.truth_status == KnowledgeStatus.OPPOSED))
        if supports and oppositions:
            status = KnowledgeStatus.BOTH
        elif supports:
            status = KnowledgeStatus.SUPPORTED
        elif oppositions:
            status = KnowledgeStatus.OPPOSED
        else:
            status = KnowledgeStatus.UNDETERMINED
        support_conf = 1.0 - prod(1.0 - item.confidence for item in active if item.truth_status == KnowledgeStatus.SUPPORTED)
        oppose_conf = 1.0 - prod(1.0 - item.confidence for item in active if item.truth_status == KnowledgeStatus.OPPOSED)
        confidence = min(support_conf, oppose_conf) if status == KnowledgeStatus.BOTH else max(support_conf, oppose_conf)
        return FourStateTruthAssessment(
            proposition_ref=proposition_ref,
            context_ref=context_ref,
            truth_status=status,
            support_admission_refs=supports,
            opposition_admission_refs=oppositions,
            source_refs=tuple(sorted({ref for item in active for ref in item.source_refs})),
            evidence_refs=tuple(sorted({ref for item in active for ref in item.evidence_refs})),
            confidence=confidence,
            conflicts=("independent_support_and_opposition",) if status == KnowledgeStatus.BOTH else (),
        )

    def project_knowledge(
        self,
        assessment: FourStateTruthAssessment,
        admissions: tuple[EpistemicAdmissionRecord, ...],
        *,
        permission_ref: str = "conversation",
        sensitivity: str = "normal",
    ) -> EpistemicProjection:
        active_refs = set(assessment.support_admission_refs) | set(assessment.opposition_admission_refs)
        active = tuple(
            item for item in self._active_admissions(
                assessment.proposition_ref, assessment.context_ref, admissions
            )
            if item.admission_ref in active_refs
        )
        knowledge = None
        if assessment.truth_status != KnowledgeStatus.UNDETERMINED and active:
            knowledge = KnowledgeRecord(
                knowledge_ref="knowledge:epistemic:" + semantic_fingerprint(
                    "epistemic-knowledge-ref",
                    (assessment.proposition_ref, assessment.context_ref, tuple(sorted(active_refs))),
                    32,
                ),
                proposition_ref=assessment.proposition_ref,
                truth_status=assessment.truth_status,
                confidence=assessment.confidence,
                context_ref=assessment.context_ref,
                source_refs=assessment.source_refs,
                evidence_refs=assessment.evidence_refs,
                permission_ref=permission_ref,
                sensitivity=sensitivity,
                support_lineage_refs=tuple(sorted(active_refs)),
            )
        return EpistemicProjection(assessment, knowledge, active)
