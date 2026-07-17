"""Four-state truth maintenance, temporal admissibility and contradiction proof."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .model import (
    GraphPatch,
    KnowledgeRecord,
    PatchOperation,
    PatchOperationKind,
    Polarity,
    TruthAssessment,
    TruthStatus,
    semantic_hash,
)
from .storage import SemanticStore


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class TruthMaintenanceCoordinator:
    """Assess support and opposition without collapsing open-world states."""

    def __init__(self, store: SemanticStore):
        self._store = store

    def proposition_signature(self, proposition_ref: str) -> str | None:
        proposition = self._store.get_referent(proposition_ref)
        if proposition is None:
            return None
        payload = proposition.payload or {}
        predication_refs = tuple(map(str, payload.get("predication_refs", ())))
        predications: list[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]]] = []
        for predication_ref in predication_refs:
            predication = self._store.get_predication(predication_ref)
            if predication is None:
                return None
            predications.append((
                predication.predicate_schema_ref,
                tuple(sorted(
                    (binding.port_id, tuple(binding.referent_refs))
                    for binding in predication.bindings
                    if binding.referent_refs
                )),
            ))
        return semantic_hash("proposition_signature", tuple(sorted(predications)))

    def assess_proposition(
        self,
        proposition_ref: str,
        *,
        context_ref: str,
        at_time: str | None = None,
        scope_refs: Iterable[str] = (),
    ) -> TruthAssessment:
        signature = self.proposition_signature(proposition_ref)
        if signature is None:
            return TruthAssessment(
                assessment_id=semantic_hash("truth_assessment", (proposition_ref, "missing")),
                proposition_signature=proposition_ref,
                context_ref=context_ref,
                truth_status=TruthStatus.UNDETERMINED,
                support_knowledge_refs=(),
                opposition_knowledge_refs=(),
                confidence=0.0,
                store_revision=self._store.revision,
            )
        proposition = self._store.get_referent(proposition_ref)
        requested_polarity = str((proposition.payload or {}).get("polarity", Polarity.POSITIVE.value))
        supports: list[KnowledgeRecord] = []
        oppositions: list[KnowledgeRecord] = []
        for knowledge in self._store.active_knowledge(context_ref=context_ref, scope_refs=scope_refs):
            if not self._temporally_valid(knowledge, at_time):
                continue
            candidate_signature = self.proposition_signature(knowledge.proposition_ref)
            if candidate_signature != signature:
                continue
            stored = self._store.get_referent(knowledge.proposition_ref)
            stored_polarity = str((stored.payload or {}).get("polarity", Polarity.POSITIVE.value)) if stored else ""
            target = supports if stored_polarity == requested_polarity else oppositions
            target.append(knowledge)
        status = self._status(supports, oppositions)
        confidence = self._confidence(supports, oppositions, status)
        return TruthAssessment(
            assessment_id=semantic_hash("truth_assessment", (
                signature, context_ref, requested_polarity,
                tuple(item.knowledge_id for item in supports),
                tuple(item.knowledge_id for item in oppositions), at_time,
            )),
            proposition_signature=signature,
            context_ref=context_ref,
            truth_status=status,
            support_knowledge_refs=tuple(item.knowledge_id for item in supports),
            opposition_knowledge_refs=tuple(item.knowledge_id for item in oppositions),
            confidence=confidence,
            valid_time_ref=at_time,
            evidence_refs=tuple(dict.fromkeys(
                ref for item in (*supports, *oppositions) for ref in item.evidence_refs
            )),
            store_revision=self._store.revision,
        )

    def assess_signature(
        self,
        predicate_ref: str,
        fixed_ports: Mapping[str, str],
        *,
        context_ref: str,
        at_time: str | None = None,
        scope_refs: Iterable[str] = (),
    ) -> TruthAssessment:
        candidates = self._store.knowledge_for_predicate(
            predicate_ref, context_ref=context_ref, scope_refs=scope_refs
        )
        supports: list[KnowledgeRecord] = []
        oppositions: list[KnowledgeRecord] = []
        signature_data = (predicate_ref, tuple(sorted(fixed_ports.items())))
        for knowledge, predication, proposition in candidates:
            if not self._temporally_valid(knowledge, at_time):
                continue
            bound = {
                binding.port_id: binding.referent_refs[0]
                for binding in predication.bindings if len(binding.referent_refs) == 1
            }
            if not all(bound.get(port) == ref for port, ref in fixed_ports.items()):
                continue
            polarity = str((proposition.payload or {}).get("polarity", Polarity.POSITIVE.value))
            (supports if polarity == Polarity.POSITIVE.value else oppositions).append(knowledge)
        status = self._status(supports, oppositions)
        return TruthAssessment(
            assessment_id=semantic_hash("truth_assessment", (
                signature_data, context_ref, at_time,
                tuple(item.knowledge_id for item in supports),
                tuple(item.knowledge_id for item in oppositions),
            )),
            proposition_signature=semantic_hash("proposition_signature", signature_data),
            context_ref=context_ref,
            truth_status=status,
            support_knowledge_refs=tuple(item.knowledge_id for item in supports),
            opposition_knowledge_refs=tuple(item.knowledge_id for item in oppositions),
            confidence=self._confidence(supports, oppositions, status),
            valid_time_ref=at_time,
            evidence_refs=tuple(dict.fromkeys(
                ref for item in (*supports, *oppositions) for ref in item.evidence_refs
            )),
            store_revision=self._store.revision,
        )

    def compile_assessment_patch(
        self,
        assessments: Iterable[TruthAssessment],
        *,
        context_ref: str,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        assessments = tuple(assessments)
        if not assessments:
            return None
        operations = tuple(
            PatchOperation(
                operation_id=f"op:{item.assessment_id}",
                kind=PatchOperationKind.UPSERT_TRUTH_ASSESSMENT,
                target_ref=item.assessment_id,
                payload={
                    "proposition_signature": item.proposition_signature,
                    "context_ref": item.context_ref,
                    "truth_status": item.truth_status.value,
                    "support_knowledge_refs": item.support_knowledge_refs,
                    "opposition_knowledge_refs": item.opposition_knowledge_refs,
                    "confidence": item.confidence,
                    "valid_time_ref": item.valid_time_ref,
                    "evidence_refs": item.evidence_refs,
                    "store_revision": item.store_revision,
                },
            ) for item in assessments
        )
        return GraphPatch(
            patch_id=semantic_hash("patch:truth_assessments", tuple(item.assessment_id for item in assessments)),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:truth_maintenance",
            evidence_refs=tuple(dict.fromkeys(
                ref for item in assessments for ref in item.evidence_refs
            )),
            operations=operations,
            expected_store_revision=expected_store_revision,
            permission_ref="internal",
        )

    @staticmethod
    def _status(
        supports: Iterable[KnowledgeRecord], oppositions: Iterable[KnowledgeRecord]
    ) -> TruthStatus:
        has_support = any(item.truth_status in {TruthStatus.SUPPORTED, TruthStatus.BOTH} for item in supports)
        has_opposition = any(item.truth_status in {TruthStatus.SUPPORTED, TruthStatus.BOTH} for item in oppositions)
        if has_support and has_opposition:
            return TruthStatus.BOTH
        if has_support:
            return TruthStatus.SUPPORTED
        if has_opposition:
            return TruthStatus.OPPOSED
        return TruthStatus.UNDETERMINED

    @staticmethod
    def _confidence(
        supports: Iterable[KnowledgeRecord],
        oppositions: Iterable[KnowledgeRecord],
        status: TruthStatus,
    ) -> float:
        support = max((item.confidence for item in supports), default=0.0)
        opposition = max((item.confidence for item in oppositions), default=0.0)
        if status == TruthStatus.BOTH:
            return min(support, opposition)
        return max(support, opposition)

    def _temporally_valid(self, knowledge: KnowledgeRecord, at_time: str | None) -> bool:
        if at_time is None:
            at = datetime.now(timezone.utc)
        else:
            at = _parse_time(at_time)
            if at is None:
                return True
        start = _parse_time(knowledge.valid_from)
        end = _parse_time(knowledge.valid_to)
        if start and at < start:
            return False
        if end and at >= end:
            return False
        if knowledge.valid_time_ref:
            referent = self._store.get_referent(knowledge.valid_time_ref)
            payload: Mapping[str, Any] = referent.payload if referent and isinstance(referent.payload, Mapping) else {}
            ref_start = _parse_time(str(payload.get("start_iso") or ""))
            ref_end = _parse_time(str(payload.get("end_iso") or ""))
            if ref_start and at < ref_start:
                return False
            if ref_end and at >= ref_end:
                return False
        return True
