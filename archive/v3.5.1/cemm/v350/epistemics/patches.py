"""Atomic GraphPatch planners for claims and independently admitted knowledge."""
from __future__ import annotations

from ..schema.model import semantic_fingerprint
from ..storage import (
    AdmissionDecision, EpistemicAdmissionRecord, GraphPatch, KnowledgeRecord,
    PatchOperation, PatchOperationKind, RecordKind, SourceAssessmentRecord, encode_record,
)
from .model import CompiledClaim


class EpistemicPatchPlanner:
    def claim_patch(self, compiled: CompiledClaim, *, expected_store_revision: int | None = None) -> GraphPatch:
        items = (
            (RecordKind.REFERENT, compiled.claim_occurrence.referent),
            (RecordKind.CLAIM_OCCURRENCE, compiled.claim_occurrence),
            (RecordKind.CLAIM_RECORD, compiled.claim_record),
            (RecordKind.CLAIM_HISTORY, compiled.history_record),
        )
        operations = tuple(
            PatchOperation(
                operation_ref="patch-operation:" + semantic_fingerprint("claim-patch-operation", (kind.value, index, target_ref(kind, record)), 24),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=kind,
                target_ref=target_ref(kind, record),
                record_revision=record_revision(kind, record),
                payload=encode_record(kind, record),
                reason="persist attributed claim structure without epistemic admission",
            )
            for index, (kind, record) in enumerate(items)
        )
        return GraphPatch(
            patch_ref="graph-patch:claim:" + semantic_fingerprint("claim-patch-ref", tuple(item.operation_ref for item in operations), 24),
            context_ref=compiled.claim_occurrence.source_context_ref,
            scope_ref=compiled.claim_occurrence.referent.scope_ref,
            source_ref=compiled.claim_occurrence.claimant_ref,
            permission_ref=compiled.claim_occurrence.referent.permission_ref,
            operations=operations,
            expected_store_revision=expected_store_revision,
            evidence_refs=compiled.evidence_refs,
            validation_requirements=("claim_is_attributed_not_admitted", "append_only_claim_history"),
            metadata={"actual_world_admission": False, "state_transition": False},
        )

    def admission_patch(
        self,
        admission: EpistemicAdmissionRecord,
        knowledge: KnowledgeRecord | None = None,
        source_assessments: tuple[SourceAssessmentRecord, ...] = (),
        *,
        expected_store_revision: int | None = None,
    ) -> GraphPatch:
        direct = admission.decision in {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION}
        expected_assessment_refs = set(admission.source_assessment_pins)
        provided_assessment_refs = {(item.assessment_ref, item.revision) for item in source_assessments}
        if direct and provided_assessment_refs != expected_assessment_refs:
            raise ValueError("direct admission patch must atomically persist the exact durable source assessments")
        if not direct and source_assessments:
            raise ValueError("non-admission decisions must not smuggle source-assessment authority into the patch")
        for item in source_assessments:
            if item.source_ref not in admission.source_refs:
                raise ValueError("source assessment does not belong to an admitted source")
            if item.context_ref != admission.source_context_ref:
                raise ValueError("source assessment context differs from the admission source context")
        if knowledge is not None:
            lineage = set(knowledge.support_lineage_refs)
            if admission.admission_ref not in lineage:
                raise ValueError("knowledge projection must retain the authorizing admission ref")
            if not direct:
                raise ValueError("non-admission decisions cannot authorize a knowledge record")
            if knowledge.proposition_ref != admission.proposition_ref:
                raise ValueError("knowledge projection targets a different proposition")
            if knowledge.context_ref != admission.target_context_ref:
                raise ValueError("knowledge projection targets a different admitted context")
            if not set(admission.source_refs).issubset(knowledge.source_refs):
                raise ValueError("knowledge projection must retain admitted source lineage")
            if not set(admission.evidence_refs).issubset(knowledge.evidence_refs):
                raise ValueError("knowledge projection must retain admitted evidence lineage")
        items = [(RecordKind.SOURCE_ASSESSMENT, item) for item in source_assessments]
        items.append((RecordKind.EPISTEMIC_ADMISSION, admission))
        if knowledge is not None:
            items.append((RecordKind.KNOWLEDGE, knowledge))
        operations = tuple(
            PatchOperation(
                operation_ref="patch-operation:" + semantic_fingerprint("admission-patch-operation", (kind.value, index, target_ref(kind, record)), 24),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=kind,
                target_ref=target_ref(kind, record),
                record_revision=record_revision(kind, record),
                payload=encode_record(kind, record),
                reason="persist explicit epistemic decision and separately projected knowledge",
            )
            for index, (kind, record) in enumerate(items)
        )
        return GraphPatch(
            patch_ref="graph-patch:admission:" + semantic_fingerprint("admission-patch-ref", tuple(item.operation_ref for item in operations), 24),
            context_ref=admission.target_context_ref,
            scope_ref="epistemic",
            source_ref=admission.source_refs[0] if admission.source_refs else admission.policy_ref,
            permission_ref=admission.permission_ref,
            operations=operations,
            expected_store_revision=expected_store_revision,
            evidence_refs=admission.evidence_refs,
            validation_requirements=("explicit_admission_proof", "no_state_effects"),
            metadata={"state_transition": False, "claim_grammar_authority": False},
        )


def target_ref(kind: RecordKind, record) -> str:
    from ..storage import record_ref
    return record_ref(kind, record)


def record_revision(kind: RecordKind, record) -> int:
    from ..storage import record_revision as resolve_revision
    return resolve_revision(kind, record)
