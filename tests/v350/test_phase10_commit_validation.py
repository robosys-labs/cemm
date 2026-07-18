from __future__ import annotations

from dataclasses import replace

from cemm.v350.schema.model import PortFillerClass, StorageKind
from cemm.v350.storage import (
    AdmissionDecision,
    ClaimRecord,
    CommitValidator,
    EpistemicAdmissionRecord,
    EvidenceRecord,
    KnowledgeRecord,
    KnowledgeStatus,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SourceAssessmentRecord,
    StoredRecord,
)
from cemm.v350.uol.model import (
    FillerRef,
    IdentityStatus,
    PropositionReferent,
    Referent,
)


class _Resolver:
    def __init__(self, *records: StoredRecord):
        self.items = tuple(records)

    def resolve(self, record_kind, record_ref, revision=None):
        matches = [
            item for item in self.items
            if item.record_kind == record_kind and item.record_ref == record_ref
            and (revision is None or item.revision == revision)
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: item.revision)

    def records(self, record_kind):
        return tuple(item for item in self.items if item.record_kind == record_kind)

    def resolve_any(self, record_ref):
        return tuple(item for item in self.items if item.record_ref == record_ref)


def _stored(kind, ref, payload, revision=1):
    return StoredRecord(kind, ref, revision, payload, "content", "record", "test", 1)


def _fixtures():
    proposition_ref = "prop:attributed"
    proposition = PropositionReferent(
        Referent(
            proposition_ref,
            StorageKind.PROPOSITION,
            IdentityStatus.CANDIDATE,
            context_refs=("context:reported",),
            provenance_refs=("evidence:claim",),
        ),
        (FillerRef(PortFillerClass.SEMANTIC_APPLICATION, "application:content"),),
        "context:reported",
        evidence_refs=("evidence:claim",),
    )
    source = Referent(
        "source:a", StorageKind.ORDINARY, IdentityStatus.RESOLVED,
        context_refs=("actual",), provenance_refs=("evidence:source",),
    )
    evidence = EvidenceRecord(
        "evidence:claim", "source:a", 1.0, "lineage:claim", context_ref="context:reported"
    )
    source_assessment = SourceAssessmentRecord(
        "source-assessment:a", "source:a", 0.9, 0.9, 0.9, 0.1,
        "context:reported", ("evidence:claim",),
    )
    admission = EpistemicAdmissionRecord(
        "admission:a", proposition_ref, "context:reported", "actual",
        AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 0.9,
        ("source:a",), ("evidence:claim",), ("proof:admission:a",),
        "policy:test", source_assessment_pins=(("source-assessment:a", 1),),
        authorization_ref="authorization:test",
    )
    knowledge = KnowledgeRecord(
        "knowledge:a", proposition_ref, KnowledgeStatus.SUPPORTED, 0.9, "actual",
        ("source:a",), ("evidence:claim",), support_lineage_refs=("admission:a",),
        metadata={"diagnostic": "must_not_control_admission"},
    )
    records = (
        _stored(RecordKind.PROPOSITION, proposition_ref, proposition),
        _stored(RecordKind.REFERENT, "source:a", source),
        _stored(RecordKind.EVIDENCE, "evidence:claim", evidence),
        _stored(RecordKind.SOURCE_ASSESSMENT, "source-assessment:a", source_assessment),
        _stored(RecordKind.EPISTEMIC_ADMISSION, "admission:a", admission),
    )
    return records, admission, knowledge


def _validate(resolver, kind, ref, record, revision=1):
    operation = PatchOperation(
        "op:test", PatchOperationKind.UPSERT, kind, ref,
        record_revision=revision, payload={"record": "test"},
    )
    return CommitValidator(resolver).validate(((operation, record),))


def test_admission_lineage_can_authorize_explicit_cross_context_knowledge() -> None:
    records, _admission, knowledge = _fixtures()
    assert _validate(_Resolver(*records), RecordKind.KNOWLEDGE, knowledge.knowledge_ref, knowledge) == ()


def test_cross_context_knowledge_without_admission_lineage_is_rejected() -> None:
    records, _admission, knowledge = _fixtures()
    forged = replace(
        knowledge,
        support_lineage_refs=(),
        metadata={},
    )
    errors = _validate(_Resolver(*records), RecordKind.KNOWLEDGE, forged.knowledge_ref, forged)
    assert errors and "without explicit epistemic admission" in errors[0].message


def test_derived_knowledge_cannot_forge_source_or_evidence_lineage() -> None:
    records, _admission, knowledge = _fixtures()
    forged = replace(knowledge, source_refs=("source:other",))
    errors = _validate(_Resolver(*records), RecordKind.KNOWLEDGE, forged.knowledge_ref, forged)
    assert errors and "sources must equal" in errors[0].message


def test_claim_record_superseded_by_cannot_compete_with_append_only_history() -> None:
    claim = ClaimRecord(
        "claim:record", "claim:occurrence", "prop:x", "source:a",
        "actual", "context:reported", 1.0, evidence_refs=("evidence:x",),
        superseded_by="claim:other",
    )
    errors = _validate(_Resolver(), RecordKind.CLAIM_RECORD, claim.claim_record_ref, claim)
    assert errors and "append-only ClaimHistoryRecord" in errors[0].message


def test_admission_revision_cannot_rewrite_decision_or_source_lineage() -> None:
    records, admission, _knowledge = _fixtures()
    revised = replace(
        admission,
        revision=2,
        supersedes_revision=1,
        decision=AdmissionDecision.ADMIT_OPPOSITION,
        truth_status=KnowledgeStatus.OPPOSED,
    )
    errors = _validate(_Resolver(*records), RecordKind.EPISTEMIC_ADMISSION, revised.admission_ref, revised, revision=2)
    assert errors and "may not rewrite proposition, context, decision, or source lineage" in errors[0].message


def test_knowledge_cannot_reuse_an_effectively_retracted_admission() -> None:
    records, admission, knowledge = _fixtures()
    retraction = EpistemicAdmissionRecord(
        "admission:retract:a", admission.proposition_ref, admission.source_context_ref,
        admission.target_context_ref, AdmissionDecision.RETRACT, KnowledgeStatus.UNDETERMINED,
        1.0, ("source:a",), ("evidence:claim",), ("proof:retract:a",),
        "policy:test", authorization_ref="authorization:retract:a",
        retracts_admission_ref=admission.admission_ref,
    )
    resolver = _Resolver(
        *records, _stored(RecordKind.EPISTEMIC_ADMISSION, retraction.admission_ref, retraction)
    )
    errors = _validate(resolver, RecordKind.KNOWLEDGE, knowledge.knowledge_ref, knowledge)
    assert errors and "effectively retracted" in errors[0].message


def test_source_assessment_revision_cannot_rewrite_source_identity() -> None:
    records, admission, _knowledge = _fixtures()
    prior = next(item for item in records if item.record_kind == RecordKind.SOURCE_ASSESSMENT).payload
    revised = replace(prior, revision=2, supersedes_revision=1, source_ref="source:other")
    other_source = Referent(
        "source:other", StorageKind.ORDINARY, IdentityStatus.RESOLVED,
        context_refs=("actual",), provenance_refs=("evidence:source",),
    )
    resolver = _Resolver(*records, _stored(RecordKind.REFERENT, "source:other", other_source))
    errors = _validate(
        resolver, RecordKind.SOURCE_ASSESSMENT, revised.assessment_ref, revised, revision=2
    )
    assert errors and "may not rewrite source identity or context" in errors[0].message
