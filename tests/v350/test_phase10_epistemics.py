from __future__ import annotations

from pathlib import Path
import sqlite3
from dataclasses import replace

import pytest

from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.epistemics import (
    AdmissionPolicy,
    AdmissionRequest,
    AdmissionThresholds,
    ClaimCompilationError,
    ClaimHistoryProjector,
    ClaimOccurrenceCompiler,
    EpistemicAdmissionEngine,
    EpistemicPatchPlanner,
    FourStateTruthProjector,
    SourceAssessment,
)
from cemm.v350.schema.model import EventSchema, PortFillerClass, StorageKind, UseOperation
from cemm.v350.storage import (
    AdmissionDecision,
    AdmissionLifecycleStatus,
    ClaimHistoryAction,
    ClaimHistoryRecord,
    ClaimRecord,
    EpistemicAdmissionRecord,
    KnowledgeStatus,
    RecordKind,
    SourceAssessmentRecord,
    SemanticStore,
    decode_record,
    encode_record,
)
from cemm.v350.storage.sqlite_schema import SCHEMA_VERSION, configure_connection, initialize_schema, require_schema_compatible
from cemm.v350.storage.persistence import write_record
from cemm.v350.uol.model import (
    ApplicationBinding,
    ClaimForce,
    EventOccurrence,
    FillerRef,
    IdentityStatus,
    OccurrenceStatus,
    PropositionReferent,
    Referent,
    SemanticApplication,
    UOLGraph,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    path = tmp_path_factory.mktemp("phase10") / "boot.sqlite"
    result = DeterministicSQLiteCompiler().compile(SOURCE, path, make_read_only=False)
    value = SemanticStore(":memory:", boot_path=result.output_path)
    yield value
    value.close()


def _claim_graph(store: SemanticStore, *, same_context: bool = False):
    registry = store.repositories.schemas.registry()
    candidates = []
    for item in registry.iter_schemas():
        if not isinstance(item, EventSchema) or not item.use_profile.permits(UseOperation.COMPOSE):
            continue
        proposition_ports = tuple(
            port for port in item.local_ports if StorageKind.PROPOSITION in port.accepted_storage_kinds
        )
        source_ports = tuple(
            port for port in item.local_ports
            if port.identity_contribution and port.cardinality.minimum > 0
            and PortFillerClass.REFERENT in port.filler_classes
            and port not in proposition_ports
        )
        if len(proposition_ports) == 1 and len(source_ports) == 1:
            candidates.append((item, source_ports[0], proposition_ports[0]))
    assert len(candidates) == 1
    schema, source_port, proposition_port = candidates[0]
    audience_ports = [item for item in schema.local_ports if item.port_ref not in {source_port.port_ref, proposition_port.port_ref}]
    claimant = store.repositories.referents.require("referent:self").payload
    audience = claimant
    attributed = "actual" if same_context else "context:attributed:test"
    content_app = SemanticApplication(
        application_ref="application:test:content",
        schema_ref=schema.schema_ref,
        schema_revision=schema.revision,
        use_operation=UseOperation.COMPOSE,
        bindings=(),
        context_ref=attributed,
        evidence_refs=("evidence:test:content",),
    )
    proposition_ref = "referent:test:proposition"
    proposition_referent = Referent(
        referent_ref=proposition_ref,
        storage_kind=StorageKind.PROPOSITION,
        identity_status=IdentityStatus.CANDIDATE,
        context_refs=(attributed,),
        provenance_refs=("evidence:test:proposition",),
    )
    proposition = PropositionReferent(
        referent=proposition_referent,
        content_refs=(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, content_app.application_ref),),
        context_ref=attributed,
        evidence_refs=("evidence:test:proposition",),
    )
    bindings = [
        ApplicationBinding(source_port.port_ref, (FillerRef(PortFillerClass.REFERENT, claimant.referent_ref),), evidence_refs=("evidence:test:claim",)),
        ApplicationBinding(proposition_port.port_ref, (FillerRef(PortFillerClass.REFERENT, proposition_ref),), evidence_refs=("evidence:test:claim",)),
    ]
    for port in audience_ports:
        bindings.append(ApplicationBinding(port.port_ref, (FillerRef(PortFillerClass.REFERENT, audience.referent_ref),), evidence_refs=("evidence:test:claim",)))
    claim_app = SemanticApplication(
        application_ref="application:test:claim",
        schema_ref=schema.schema_ref,
        schema_revision=schema.revision,
        use_operation=UseOperation.COMPOSE,
        bindings=tuple(bindings),
        context_ref="actual",
        evidence_refs=("evidence:test:claim",),
    )
    event_ref = "referent:test:claim-event"
    event_referent = Referent(
        referent_ref=event_ref,
        storage_kind=StorageKind.EVENT_OCCURRENCE,
        identity_status=IdentityStatus.CANDIDATE,
        context_refs=("actual",),
        provenance_refs=("evidence:test:claim",),
    )
    event = EventOccurrence(
        referent=event_referent,
        event_schema_ref=schema.schema_ref,
        event_schema_revision=schema.revision,
        participant_application_ref=claim_app.application_ref,
        context_ref="actual",
        occurrence_status=OccurrenceStatus.MENTIONED,
        provenance_refs=("evidence:test:claim",),
        admission_refs=(),
    )
    graph = UOLGraph(
        graph_ref="uol:test:claim",
        referents={claimant.referent_ref: claimant, proposition_ref: proposition_referent, event_ref: event_referent},
        applications={content_app.application_ref: content_app, claim_app.application_ref: claim_app},
        propositions={proposition_ref: proposition},
        events={event_ref: event},
        evidence_refs=("evidence:test:claim",),
        root_refs=(claim_app.application_ref,),
    )
    return graph, claim_app.application_ref


def _source(ref="referent:self", *, reliability=0.95, authority=0.95, access=0.95, bias=0.05):
    return SourceAssessment(ref, authority, reliability, access, bias, (f"evidence:{ref}:assessment",))


def _request(*, status=KnowledgeStatus.SUPPORTED, auth="authorization:test", source="referent:self", evidence=0.95, policy="policy:test"):
    return AdmissionRequest(
        request_ref=f"request:{status.value}:{source}",
        proposition_ref="referent:test:proposition",
        source_context_ref="context:attributed:test",
        target_context_ref="actual",
        requested_truth_status=status,
        source_refs=(source,),
        evidence_confidences=((f"evidence:{source}:claim", evidence),),
        proof_refs=(f"proof:{source}:admission",),
        source_assessments=(_source(source),),
        policy_ref=policy,
        authorization_ref=auth,
    )


def _policy():
    return AdmissionPolicy(
        "policy:test",
        AdmissionThresholds(0.5, 0.5, 0.5, 0.5, 0.5, 1),
    )


def test_claim_compiler_uses_schema_ports_and_preserves_attribution(store) -> None:
    graph, app_ref = _claim_graph(store)
    compiled = ClaimOccurrenceCompiler(store).compile(
        graph, app_ref, claim_force=ClaimForce.ASSERTED,
        commitment_strength=0.9, evidence_refs=("evidence:test:claim",),
    )
    assert compiled.claim_occurrence.proposition_ref == "referent:test:proposition"
    assert compiled.claim_occurrence.source_context_ref == "actual"
    assert compiled.claim_occurrence.reported_context_ref == "context:attributed:test"
    assert compiled.claim_occurrence.claimant_ref == "referent:self"
    assert compiled.history_record.action == ClaimHistoryAction.ASSERT
    assert compiled.claim_record.reported_context_ref != compiled.claim_record.source_context_ref


def test_claim_compiler_rejects_unattributed_same_context(store) -> None:
    graph, app_ref = _claim_graph(store, same_context=True)
    with pytest.raises(ClaimCompilationError):
        ClaimOccurrenceCompiler(store).compile(
            graph, app_ref, claim_force=ClaimForce.ASSERTED,
            commitment_strength=0.9, evidence_refs=("evidence:test:claim",),
        )


def test_grammar_and_claim_structure_never_auto_admit() -> None:
    engine = EpistemicAdmissionEngine()
    request = _request(auth=None)
    assessment = engine.assess(request, _policy())
    record = engine.record(request, assessment)
    assert assessment.decision == AdmissionDecision.PRESERVE_ATTRIBUTED
    assert assessment.truth_status == KnowledgeStatus.UNDETERMINED
    assert record.truth_status == KnowledgeStatus.UNDETERMINED
    assert record.proof_refs == ()


def test_explicit_policy_proof_and_source_dimensions_can_admit_support() -> None:
    engine = EpistemicAdmissionEngine()
    request = _request()
    assessment = engine.assess(request, _policy())
    record = engine.record(request, assessment)
    assert assessment.decision == AdmissionDecision.ADMIT_SUPPORT
    assert record.truth_status == KnowledgeStatus.SUPPORTED
    assert record.proof_refs
    assert 0 < record.confidence <= 1


def test_source_dimensions_are_independent_gates_not_one_fused_score() -> None:
    engine = EpistemicAdmissionEngine()
    request = _request()
    request = replace(
        request,
        source_assessments=(_source(reliability=0.1, authority=1.0, access=1.0, bias=0.0),),
    )
    assessment = engine.assess(request, _policy())
    assert assessment.decision == AdmissionDecision.DEFER
    assert "source_dimensions" in assessment.failed_requirements


def test_four_state_truth_support_opposition_and_both() -> None:
    engine = EpistemicAdmissionEngine()
    support_req = _request(status=KnowledgeStatus.SUPPORTED, source="source:a")
    oppose_req = _request(status=KnowledgeStatus.OPPOSED, source="source:b")
    support = engine.record(support_req, engine.assess(support_req, _policy()))
    oppose = engine.record(oppose_req, engine.assess(oppose_req, _policy()))
    projector = FourStateTruthProjector()
    assert projector.assess(support.proposition_ref, "actual", (support,)).truth_status == KnowledgeStatus.SUPPORTED
    assert projector.assess(oppose.proposition_ref, "actual", (oppose,)).truth_status == KnowledgeStatus.OPPOSED
    both = projector.assess(support.proposition_ref, "actual", (support, oppose))
    assert both.truth_status == KnowledgeStatus.BOTH
    assert both.support_admission_refs and both.opposition_admission_refs


def test_retraction_removes_only_targeted_admission_lineage() -> None:
    engine = EpistemicAdmissionEngine()
    req_a = _request(source="source:a")
    req_b = _request(source="source:b")
    a = engine.record(req_a, engine.assess(req_a, _policy()))
    b = engine.record(req_b, engine.assess(req_b, _policy()))
    retract = EpistemicAdmissionRecord(
        admission_ref="admission:retract:a",
        proposition_ref=a.proposition_ref,
        source_context_ref=a.source_context_ref,
        target_context_ref=a.target_context_ref,
        decision=AdmissionDecision.RETRACT,
        truth_status=KnowledgeStatus.UNDETERMINED,
        confidence=1.0,
        source_refs=("source:a",),
        evidence_refs=("evidence:retract:a",),
        proof_refs=("proof:retract:a",),
        policy_ref="policy:test",
        authorization_ref="authorization:retract:a",
        retracts_admission_ref=a.admission_ref,
    )
    assessment = FourStateTruthProjector().assess(a.proposition_ref, "actual", (a, b, retract))
    assert assessment.truth_status == KnowledgeStatus.SUPPORTED
    assert assessment.support_admission_refs == (b.admission_ref,)



def test_in_memory_cross_source_retraction_cannot_remove_another_source() -> None:
    engine = EpistemicAdmissionEngine()
    req_a = _request(source="source:a")
    admission = engine.record(req_a, engine.assess(req_a, _policy()))
    malicious = EpistemicAdmissionRecord(
        admission_ref="admission:retract:other-source",
        proposition_ref=admission.proposition_ref,
        source_context_ref=admission.source_context_ref,
        target_context_ref=admission.target_context_ref,
        decision=AdmissionDecision.RETRACT,
        truth_status=KnowledgeStatus.UNDETERMINED,
        confidence=1.0,
        source_refs=("source:b",),
        evidence_refs=("evidence:retract:b",),
        proof_refs=("proof:retract:b",),
        policy_ref="policy:test",
        authorization_ref="authorization:retract:b",
        retracts_admission_ref=admission.admission_ref,
    )
    assessment = FourStateTruthProjector().assess(
        admission.proposition_ref, "actual", (admission, malicious)
    )
    assert assessment.truth_status == KnowledgeStatus.SUPPORTED
    assert assessment.support_admission_refs == (admission.admission_ref,)


def test_direct_actual_world_admission_requires_durable_authorization() -> None:
    with pytest.raises(ValueError, match="explicit authorization"):
        EpistemicAdmissionRecord(
            "admission:no-auth", "prop:test", "reported", "actual",
            AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 1.0,
            ("source:a",), ("evidence:a",), ("proof:a",), "policy:test",
        )


def test_actual_world_retraction_requires_durable_authorization_and_proof() -> None:
    with pytest.raises(ValueError, match="explicit authorization"):
        EpistemicAdmissionRecord(
            "admission:retract:no-auth", "prop:test", "reported", "actual",
            AdmissionDecision.RETRACT, KnowledgeStatus.UNDETERMINED, 1.0,
            ("source:a",), ("evidence:a",), ("proof:a",), "policy:test",
            retracts_admission_ref="admission:target",
        )

def test_knowledge_projection_requires_actual_active_admissions() -> None:
    engine = EpistemicAdmissionEngine()
    req = _request()
    admission = engine.record(req, engine.assess(req, _policy()))
    projector = FourStateTruthProjector()
    assessment = projector.assess(admission.proposition_ref, "actual", (admission,))
    projection = projector.project_knowledge(assessment, (admission,))
    assert projection.knowledge_record is not None
    assert admission.admission_ref in projection.knowledge_record.support_lineage_refs
    unknown = projector.assess(admission.proposition_ref, "actual", ())
    assert projector.project_knowledge(unknown, ()).knowledge_record is None


def test_claim_history_correction_and_retraction_are_append_only_and_source_local() -> None:
    a1 = ClaimRecord("claim:a1", "occ:a1", "prop:1", "source:a", "actual", "reported:a", 1.0, evidence_refs=("e:a1",))
    a2 = ClaimRecord("claim:a2", "occ:a2", "prop:2", "source:a", "actual", "reported:a2", 1.0, evidence_refs=("e:a2",))
    b1 = ClaimRecord("claim:b1", "occ:b1", "prop:1", "source:b", "actual", "reported:b", 1.0, evidence_refs=("e:b1",))
    history = (
        ClaimHistoryRecord("hist:a1", "claim:a1", ClaimHistoryAction.ASSERT, "source:a", "actual", ("e:a1",)),
        ClaimHistoryRecord("hist:a2", "claim:a2", ClaimHistoryAction.CORRECT, "source:a", "actual", ("e:a2",), target_claim_record_ref="claim:a1"),
    )
    effective = ClaimHistoryProjector().effective_claims((a1, a2, b1), history)
    assert {item.claim_record_ref for item in effective} == {"claim:a2", "claim:b1"}


def test_direct_admission_persists_exact_durable_source_assessments_atomically() -> None:
    engine = EpistemicAdmissionEngine()
    request = _request()
    assessment = engine.assess(request, _policy())
    admission = engine.record(request, assessment)
    source_records = engine.source_assessment_records(request)
    assert set(admission.source_assessment_pins) == {(item.assessment_ref, item.revision) for item in source_records}
    patch = EpistemicPatchPlanner().admission_patch(
        admission, source_assessments=source_records
    )
    kinds = tuple(item.record_kind for item in patch.operations)
    assert kinds.count(RecordKind.SOURCE_ASSESSMENT) == len(request.source_refs)
    assert kinds[-1] == RecordKind.EPISTEMIC_ADMISSION


def test_epistemic_patch_planner_never_contains_state_or_capability_effects(store) -> None:
    graph, app_ref = _claim_graph(store)
    compiled = ClaimOccurrenceCompiler(store).compile(
        graph, app_ref, claim_force=ClaimForce.ASSERTED,
        commitment_strength=0.9, evidence_refs=("evidence:test:claim",),
    )
    patch = EpistemicPatchPlanner().claim_patch(compiled)
    assert {item.record_kind for item in patch.operations} == {
        RecordKind.REFERENT, RecordKind.CLAIM_OCCURRENCE, RecordKind.CLAIM_RECORD, RecordKind.CLAIM_HISTORY
    }
    assert RecordKind.STATE_DELTA not in {item.record_kind for item in patch.operations}
    assert RecordKind.CAPABILITY_DELTA not in {item.record_kind for item in patch.operations}



def test_phase10_schema_version_is_bumped_and_old_v2_shape_is_rejected() -> None:
    assert SCHEMA_VERSION == 3
    connection = sqlite3.connect(":memory:")
    try:
        configure_connection(connection, deterministic_build=True)
        initialize_schema(connection)
        require_schema_compatible(connection)
        connection.execute("PRAGMA user_version=2")
        with pytest.raises(RuntimeError, match="unsupported CEMM database schema version"):
            require_schema_compatible(connection)
    finally:
        connection.close()


def test_source_assessment_persists_in_normalized_table() -> None:
    record = SourceAssessmentRecord(
        "source-assessment:persist", "source:persist", 0.8, 0.7, 0.9, 0.1,
        "context:persist", ("evidence:persist",), metadata={"audited": True},
    )
    connection = sqlite3.connect(":memory:")
    try:
        configure_connection(connection, deterministic_build=True)
        initialize_schema(connection)
        write_record(connection, RecordKind.SOURCE_ASSESSMENT, record, revision=1, store_revision=1)
        row = connection.execute(
            "SELECT source_ref, authority, reliability, access_quality, bias_risk "
            "FROM source_assessment_records WHERE assessment_ref=? AND revision=1",
            (record.assessment_ref,),
        ).fetchone()
        assert row == ("source:persist", 0.8, 0.7, 0.9, 0.1)
        admission = EpistemicAdmissionRecord(
            "admission:persist", "prop:persist", "context:persist", "actual",
            AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 0.8,
            ("source:persist",), ("evidence:persist",), ("proof:persist",),
            "policy:persist", source_assessment_pins=((record.assessment_ref, record.revision),),
            authorization_ref="authorization:persist",
        )
        write_record(connection, RecordKind.EPISTEMIC_ADMISSION, admission, revision=1, store_revision=1)
        admission_row = connection.execute(
            "SELECT source_assessment_pins_json FROM epistemic_admissions WHERE admission_ref=?",
            (admission.admission_ref,),
        ).fetchone()
        assert admission_row == ('[["source-assessment:persist",1]]',)
    finally:
        connection.close()


def test_phase10_records_round_trip_through_typed_codec() -> None:
    history = ClaimHistoryRecord(
        "hist:codec", "claim:codec", ClaimHistoryAction.ASSERT,
        "source:codec", "context:codec", ("evidence:codec",), revision=2,
        supersedes_revision=1, metadata={"lineage": "append-only"},
    )
    decoded_history = decode_record(RecordKind.CLAIM_HISTORY, encode_record(RecordKind.CLAIM_HISTORY, history))
    assert decoded_history == history

    source_assessment = SourceAssessmentRecord(
        "source-assessment:codec", "source:codec", 0.9, 0.8, 0.7, 0.2,
        "reported:codec", ("evidence:codec",), revision=2, supersedes_revision=1,
        metadata={"lineage": "source-quality"},
    )
    decoded_source_assessment = decode_record(
        RecordKind.SOURCE_ASSESSMENT,
        encode_record(RecordKind.SOURCE_ASSESSMENT, source_assessment),
    )
    assert decoded_source_assessment == source_assessment

    admission = EpistemicAdmissionRecord(
        "admission:codec", "prop:codec", "reported:codec", "actual:codec",
        AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 0.8,
        ("source:codec",), ("evidence:codec",), ("proof:codec",),
        "policy:codec", source_assessment_pins=(("source-assessment:codec", 2),),
        authorization_ref="authorization:codec",
        revision=2, supersedes_revision=1, metadata={"lineage": "explicit"},
    )
    decoded_admission = decode_record(
        RecordKind.EPISTEMIC_ADMISSION,
        encode_record(RecordKind.EPISTEMIC_ADMISSION, admission),
    )
    assert decoded_admission == admission

def test_one_admission_record_cannot_encode_both_truth_states() -> None:
    with pytest.raises(ValueError):
        EpistemicAdmissionRecord(
            "admission:bad", "prop:bad", "reported", "actual",
            AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.BOTH, 1.0,
            ("source:a",), ("e:a",), ("proof:a",), "policy:test",
            source_assessment_pins=(("source-assessment:a", 1),),
        )
