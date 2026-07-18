from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.schema.model import (
    ActionSchema, Cardinality, CompetenceHook, EventSchema, LocalPortSchema, ReferentTypeSchema,
    SchemaLifecycleStatus, SchemaProvenance, StateDimensionSchema, StateValueSchema,
    StorageKind, UseOperation, UseProfile,
)
from cemm.v350.schema.registry import SchemaRegistry
from cemm.v350.storage import (
    AdmissionDecision, AdmissionLifecycleStatus, AssignmentStatus, EpistemicAdmissionRecord,
    EvidenceRecord, KnowledgeStatus, RecordKind, SourceAssessmentRecord, StateAssignment,
    StoredRecord,
)
from cemm.v350.storage.sqlite_schema import SCHEMA_VERSION
from cemm.v350.transitions import (
    CapabilityDependencyEngine, CapabilityDependencyRecord, ConditionOperator,
    EventAdmissionGate, StateConditionSpec, StateEffectSpec, StateTimelineProjector,
    TransitionContractCompiler, TransitionContractRecord, TransitionPreviewEngine,
)
from cemm.v350.transitions.compiler import TransitionContractError
from cemm.v350.uol.model import (
    ApplicationBinding, CapabilityStatus, ChangeOperation, EventOccurrence, FillerRef,
    IdentityStatus, OccurrenceStatus, Polarity, PortFillerClass, PropositionReferent,
    Referent, SemanticApplication,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"


def _profile(**values: str) -> UseProfile:
    return UseProfile.from_mapping(values)


def _stored(kind: RecordKind, ref: str, payload, revision: int = 1) -> StoredRecord:
    return StoredRecord(kind, ref, revision, payload, f"content:{ref}:{revision}", f"record:{ref}:{revision}", "test", 1)


class _Resolver:
    def __init__(self, *items: StoredRecord):
        self.items = list(items)

    def add(self, *items: StoredRecord) -> None:
        self.items.extend(items)

    def resolve(self, kind, ref, revision=None):
        matches = [
            item for item in self.items
            if item.record_kind == kind and item.record_ref == ref
            and (revision is None or item.revision == revision)
        ]
        return max(matches, key=lambda item: item.revision) if matches else None

    def records(self, kind):
        return tuple(item for item in self.items if item.record_kind == kind)

    def resolve_any(self, ref):
        return tuple(item for item in self.items if item.record_ref == ref)


def _fixture(*, proposition_polarity: Polarity = Polarity.POSITIVE, event_status: OccurrenceStatus = OccurrenceStatus.ADMITTED):
    type_schema = ReferentTypeSchema(
        schema_ref="type:competence:holder",
        semantic_key="competence_holder",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        storage_kinds=frozenset({StorageKind.ORDINARY}),
        use_profile=_profile(mention="allow", ground="allow", compose="allow", query="allow"),
    )
    contract_ref = "transition-contract:competence:state-change"
    event_schema = EventSchema(
        schema_ref="event:competence:state-change",
        semantic_key="competence_state_change",
        local_ports=(LocalPortSchema(
            "affected",
            accepted_type_refs=(type_schema.schema_ref,),
            cardinality=Cardinality(1, 1),
        ),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        transition_contract_refs=(contract_ref,),
        use_profile=_profile(compose="allow", query="allow", transition="allow"),
        competence_hooks=(CompetenceHook("competence:phase11:synthetic-transition", UseOperation.TRANSITION),),
        provenance=SchemaProvenance(evidence_refs=("evidence:competence:contract",)),
    )
    dimension = StateDimensionSchema(
        schema_ref="state:competence:mode",
        semantic_key="competence_mode",
        holder_type_refs=(type_schema.schema_ref,),
        value_schema_refs=("state-value:competence:mode:a", "state-value:competence:mode:b"),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        transition_contract_refs=(contract_ref,),
        use_profile=_profile(compose="allow", query="allow", transition="allow"),
        competence_hooks=(CompetenceHook("competence:phase11:synthetic-state-transition", UseOperation.TRANSITION),),
        provenance=SchemaProvenance(evidence_refs=("evidence:competence:contract",)),
    )
    value_a = StateValueSchema(
        schema_ref="state-value:competence:mode:a", semantic_key="competence_mode_a",
        dimension_ref=dimension.schema_ref, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=_profile(compose="allow", query="allow"),
    )
    value_b = StateValueSchema(
        schema_ref="state-value:competence:mode:b", semantic_key="competence_mode_b",
        dimension_ref=dimension.schema_ref, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=_profile(compose="allow", query="allow"),
    )
    action_schema = ActionSchema(
        schema_ref="action:competence:placeholder", semantic_key="competence_action",
        local_ports=(LocalPortSchema("actor", accepted_type_refs=(type_schema.schema_ref,), cardinality=Cardinality(1, 1)),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=_profile(compose="allow", query="allow"),
        provenance=SchemaProvenance(evidence_refs=("evidence:competence:dependency",)),
    )
    schemas = SchemaRegistry((type_schema, event_schema, dimension, value_a, value_b, action_schema))
    contract = TransitionContractRecord(
        contract_ref=contract_ref,
        trigger_schema_ref=event_schema.schema_ref,
        trigger_schema_revision=event_schema.revision,
        state_conditions=(StateConditionSpec(
            "condition:competence:from-a", "affected", dimension.schema_ref, dimension.revision,
            ConditionOperator.EQUALS, value_a.schema_ref, value_a.revision,
        ),),
        state_effects=(StateEffectSpec(
            "effect:competence:set-b", "affected", dimension.schema_ref, dimension.revision,
            ChangeOperation.SET, from_value_ref=value_a.schema_ref, from_value_revision=value_a.revision,
            to_value_ref=value_b.schema_ref, to_value_revision=value_b.revision,
        ),),
        evidence_refs=("evidence:competence:contract",),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
    )
    dependency = CapabilityDependencyRecord(
        dependency_ref="capability-dependency:competence:action",
        holder_type_refs=(type_schema.schema_ref,),
        action_schema_ref="action:competence:placeholder",
        action_schema_revision=1,
        state_conditions=(StateConditionSpec(
            "condition:competence:capability-b", "holder", dimension.schema_ref, dimension.revision,
            ConditionOperator.EQUALS, value_b.schema_ref, value_b.revision,
        ),),
        status_if_satisfied=CapabilityStatus.AVAILABLE,
        status_if_unsatisfied=CapabilityStatus.UNAVAILABLE,
        status_if_unknown=CapabilityStatus.UNKNOWN,
        evidence_refs=("evidence:competence:dependency",),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
    )

    subject = Referent(
        "referent:competence:subject", StorageKind.ORDINARY, IdentityStatus.RESOLVED,
        type_refs=(type_schema.schema_ref,), context_refs=("actual",), provenance_refs=("evidence:competence:subject",),
    )
    source_app = SemanticApplication(
        "application:competence:event:source", event_schema.schema_ref, event_schema.revision,
        (ApplicationBinding("affected", (FillerRef(PortFillerClass.REFERENT, subject.referent_ref),)),),
        "context:competence:attributed", use_operation=UseOperation.COMPOSE,
        evidence_refs=("evidence:competence:claim",),
    )
    actual_app = replace(
        source_app,
        application_ref="application:competence:event:actual",
        context_ref="actual",
    )
    proposition_ref = "referent:competence:proposition"
    proposition = PropositionReferent(
        Referent(
            proposition_ref, StorageKind.PROPOSITION, IdentityStatus.CANDIDATE,
            context_refs=("context:competence:attributed",), provenance_refs=("evidence:competence:claim",),
        ),
        (FillerRef(PortFillerClass.SEMANTIC_APPLICATION, source_app.application_ref),),
        "context:competence:attributed", polarity=proposition_polarity,
        evidence_refs=("evidence:competence:claim",),
    )
    admission = EpistemicAdmissionRecord(
        "admission:competence:event", proposition_ref, "context:competence:attributed", "actual",
        AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 0.95,
        ("referent:competence:source",), ("evidence:competence:claim",), ("proof:competence:admission",),
        "policy:competence:admission", source_assessment_pins=(("source-assessment:competence", 1),),
        authorization_ref="authorization:competence:admission",
    )
    event = EventOccurrence(
        Referent(
            "referent:competence:event", StorageKind.EVENT_OCCURRENCE, IdentityStatus.RESOLVED,
            type_refs=(), context_refs=("actual",), provenance_refs=("evidence:competence:event",),
        ),
        event_schema.schema_ref, event_schema.revision, actual_app.application_ref, "actual",
        occurrence_status=event_status, admission_refs=(admission.admission_ref,),
    )
    assignment = StateAssignment(
        "assignment:competence:mode", subject.referent_ref, dimension.schema_ref, dimension.revision,
        value_a.schema_ref, value_a.revision, AssignmentStatus.ACTIVE, "actual", 1.0,
        valid_from="2026-01-01T00:00:00Z", evidence_refs=("evidence:competence:state",),
    )
    evidence = tuple(
        EvidenceRecord(ref, "source:competence", 1.0, f"lineage:{ref}", context_ref="actual")
        for ref in (
            "evidence:competence:contract", "evidence:competence:dependency", "evidence:competence:subject",
            "evidence:competence:claim", "evidence:competence:event", "evidence:competence:state",
        )
    )
    items = [
        _stored(RecordKind.REFERENT, subject.referent_ref, subject),
        _stored(RecordKind.SEMANTIC_APPLICATION, source_app.application_ref, source_app),
        _stored(RecordKind.SEMANTIC_APPLICATION, actual_app.application_ref, actual_app),
        _stored(RecordKind.PROPOSITION, proposition_ref, proposition),
        _stored(RecordKind.EPISTEMIC_ADMISSION, admission.admission_ref, admission),
        _stored(RecordKind.EVENT_OCCURRENCE, event.event_ref, event),
        _stored(RecordKind.STATE_ASSIGNMENT, assignment.assignment_ref, assignment),
        *[_stored(RecordKind.EVIDENCE, item.evidence_ref, item) for item in evidence],
    ]
    return schemas, _Resolver(*items), contract, dependency, event, subject, dimension, value_a, value_b


def test_phase11_scalar_effect_cannot_smuggle_unimplemented_arithmetic() -> None:
    with pytest.raises(ValueError, match="explicit target value"):
        StateEffectSpec(
            "effect:competence:scalar", "affected", "state:competence:scalar", 1,
            ChangeOperation.INCREASE, magnitude_port_ref="amount",
        )


def test_phase11_compiler_has_no_event_specific_mutation_authority() -> None:
    schemas, _resolver, contract, _dependency, _event, *_ = _fixture()
    compiled = TransitionContractCompiler(schemas).compile(contract)
    assert compiled.contract == contract
    assert compiled.trigger_port_refs == frozenset({"affected"})


def test_phase11_admission_bridges_context_by_exact_semantic_application_equivalence() -> None:
    _schemas, resolver, _contract, _dependency, event, *_ = _fixture()
    assessment = EventAdmissionGate(resolver).assess(event)
    assert assessment.admitted is True
    assert assessment.admission_refs == ("admission:competence:event",)


def test_negative_attributed_proposition_cannot_authorize_actual_transition() -> None:
    schemas, resolver, contract, _dependency, event, *_ = _fixture(proposition_polarity=Polarity.NEGATIVE)
    preview = TransitionPreviewEngine(schemas, resolver).preview(
        event, contract, effective_time_ref="2026-07-18T12:00:00Z"
    )
    assert preview.authorized is False
    assert any("negative_proposition_cannot_admit_event" in item for item in preview.blocked_reasons)


@pytest.mark.parametrize("status", [
    OccurrenceStatus.MENTIONED, OccurrenceStatus.CLAIMED, OccurrenceStatus.REPORTED,
    OccurrenceStatus.PLANNED, OccurrenceStatus.HYPOTHETICAL, OccurrenceStatus.COUNTERFACTUAL,
    OccurrenceStatus.FICTIONAL, OccurrenceStatus.NON_OCCURRING, OccurrenceStatus.PREVENTED,
    OccurrenceStatus.FAILED,
])
def test_non_transitioning_event_statuses_never_preview_effects(status: OccurrenceStatus) -> None:
    schemas, resolver, contract, _dependency, event, *_ = _fixture(event_status=status)
    preview = TransitionPreviewEngine(schemas, resolver).preview(
        event, contract, effective_time_ref="2026-07-18T12:00:00Z"
    )
    assert preview.authorized is False
    assert preview.state_deltas == ()


def test_admitted_event_previews_proof_bearing_state_delta_without_mutation() -> None:
    schemas, resolver, contract, _dependency, event, subject, dimension, value_a, value_b = _fixture()
    preview = TransitionPreviewEngine(schemas, resolver).preview(
        event, contract, effective_time_ref="2026-07-18T12:00:00Z"
    )
    assert preview.authorized is True
    assert len(preview.state_deltas) == 1
    delta = preview.state_deltas[0]
    assert delta.holder_ref == subject.referent_ref
    assert delta.dimension_ref == dimension.schema_ref
    assert (delta.from_value_ref, delta.to_value_ref) == (value_a.schema_ref, value_b.schema_ref)
    assert preview.proof is not None and preview.proof.admission_refs == ("admission:competence:event",)
    assert resolver.resolve(RecordKind.STATE_ASSIGNMENT, "assignment:competence:mode").payload.value_ref == value_a.schema_ref


def test_state_timeline_projection_is_immutable_revision_plus_new_assignment() -> None:
    schemas, resolver, contract, _dependency, event, _subject, _dimension, value_a, value_b = _fixture()
    preview = TransitionPreviewEngine(schemas, resolver).preview(event, contract, effective_time_ref="2026-07-18T12:00:00Z")
    projection = StateTimelineProjector(schemas, resolver).project(preview.state_deltas[0])
    assert len(projection.mutations) == 2
    terminated = next(item for item in projection.mutations if item.assignment_ref == "assignment:competence:mode")
    created = next(item for item in projection.mutations if item.assignment_ref != "assignment:competence:mode")
    assert terminated.record_revision == 2 and terminated.projected.status == AssignmentStatus.TERMINATED
    assert created.record_revision == 1 and created.projected.value_ref == value_b.schema_ref
    assert created.projected.proof_refs == (preview.proof.proof_ref,)
    assert resolver.resolve(RecordKind.STATE_ASSIGNMENT, "assignment:competence:mode").payload.value_ref == value_a.schema_ref


def test_unknown_condition_preserves_frontier_instead_of_guessing_effect() -> None:
    schemas, resolver, contract, _dependency, event, *_ = _fixture()
    resolver.items = [item for item in resolver.items if item.record_kind != RecordKind.STATE_ASSIGNMENT]
    preview = TransitionPreviewEngine(schemas, resolver).preview(event, contract, effective_time_ref="2026-07-18T12:00:00Z")
    assert preview.authorized is False
    assert preview.state_deltas == ()
    assert any(item.reason == "transition_condition_unknown" for item in preview.frontiers)


def test_contract_cannot_target_state_dimension_without_explicit_bidirectional_link() -> None:
    schemas, _resolver, contract, *_ = _fixture()
    dimension = schemas.schema("state:competence:mode", 1)
    broken = replace(dimension, transition_contract_refs=())
    registry = SchemaRegistry(tuple(
        broken if item.schema_ref == broken.schema_ref else item
        for item in schemas.iter_schemas(all_revisions=True)
    ))
    with pytest.raises(TransitionContractError, match="does not link transition contract"):
        TransitionContractCompiler(registry).compile(contract)


def test_phase11_storage_schema_version_advances_without_freezing_future_versions() -> None:
    assert SCHEMA_VERSION >= 4


def test_phase11_source_package_still_compiles_with_zero_domain_transition_seed(tmp_path: Path) -> None:
    result = DeterministicSQLiteCompiler().compile(SOURCE, tmp_path / "phase11.sqlite", make_read_only=False)
    assert result.record_count > 0


def test_capability_dependency_reacts_only_to_projected_state_contracts() -> None:
    schemas, resolver, contract, dependency, event, subject, _dimension, _value_a, _value_b = _fixture()
    preview = TransitionPreviewEngine(schemas, resolver).preview(event, contract, effective_time_ref="2026-07-18T12:00:00Z")
    state_projection = StateTimelineProjector(schemas, resolver).project(preview.state_deltas[0])
    projected = CapabilityDependencyEngine(schemas, resolver).evaluate(
        dependency,
        holder_ref=subject.referent_ref,
        context_ref="actual",
        effective_time_ref="2026-07-18T12:00:00Z",
        trigger_ref=event.event_ref,
        proof_refs=(preview.proof.proof_ref,),
        state_projections=(state_projection,),
    )
    assert projected is not None
    assert projected.delta.prior_status == CapabilityStatus.UNKNOWN
    assert projected.delta.new_status == CapabilityStatus.AVAILABLE
    assert projected.projected_instance.dependency_refs == (dependency.dependency_ref,)



def test_phase11_timeline_requires_explicit_concrete_timestamp() -> None:
    schemas, resolver, contract, _dependency, event, *_ = _fixture()
    preview = TransitionPreviewEngine(schemas, resolver).preview(
        event, contract, effective_time_ref="time:unresolved:competence"
    )
    assert preview.authorized
    from cemm.v350.transitions.state import StateTransitionError
    with pytest.raises(StateTransitionError, match="ISO-8601"):
        StateTimelineProjector(schemas, resolver).project(preview.state_deltas[0])

def _patch_op(kind: RecordKind, ref: str, record, revision: int = 1):
    from cemm.v350.storage import PatchOperation, PatchOperationKind, encode_record
    return PatchOperation(
        operation_ref=f"op:phase11:{kind.value}:{ref}:{revision}",
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=kind,
        target_ref=ref,
        record_revision=revision,
        payload=encode_record(kind, record),
    )


def test_end_to_end_atomic_transition_commit_with_capability_reevaluation(tmp_path: Path) -> None:
    from cemm.v350.schema.model import ActionSchema
    from cemm.v350.storage import (
        GraphPatch, PatchCommitStatus, RecordKind, SemanticStore, SourceAssessmentRecord,
    )
    from cemm.v350.transitions import TransitionCoordinator

    boot = DeterministicSQLiteCompiler().compile(SOURCE, tmp_path / "boot.sqlite", make_read_only=False)
    store = SemanticStore(":memory:", boot_path=boot.output_path)
    try:
        contract_ref = "transition-contract:competence:integration"
        evidence_contract = EvidenceRecord(
            "evidence:competence:integration:contract", "source:competence", 1.0,
            "lineage:competence:integration:contract", context_ref="actual",
        )
        evidence_claim = EvidenceRecord(
            "evidence:competence:integration:claim", "referent:self", 1.0,
            "lineage:competence:integration:claim", context_ref="context:competence:integration:attributed",
        )
        evidence_state = EvidenceRecord(
            "evidence:competence:integration:state", "source:competence", 1.0,
            "lineage:competence:integration:state", context_ref="actual",
        )
        event_schema = EventSchema(
            schema_ref="event:competence:integration", semantic_key="competence_integration_event",
            local_ports=(LocalPortSchema("affected", accepted_type_refs=("type:referent",), cardinality=Cardinality(1, 1)),),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            transition_contract_refs=(contract_ref,),
            use_profile=_profile(compose="allow", query="allow", transition="allow"),
            competence_hooks=(CompetenceHook("competence:phase11:integration:event", UseOperation.TRANSITION),),
            provenance=SchemaProvenance(evidence_refs=(evidence_contract.evidence_ref,)),
        )
        dimension = StateDimensionSchema(
            schema_ref="state:competence:integration", semantic_key="competence_integration_state",
            holder_type_refs=("type:referent",),
            value_schema_refs=("state-value:competence:integration:a", "state-value:competence:integration:b"),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            transition_contract_refs=(contract_ref,),
            use_profile=_profile(compose="allow", query="allow", transition="allow"),
            competence_hooks=(CompetenceHook("competence:phase11:integration:state", UseOperation.TRANSITION),),
            provenance=SchemaProvenance(evidence_refs=(evidence_contract.evidence_ref,)),
        )
        value_a = StateValueSchema(
            "state-value:competence:integration:a", "competence_integration_a",
            dimension_ref=dimension.schema_ref, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=_profile(compose="allow", query="allow"),
        )
        value_b = StateValueSchema(
            "state-value:competence:integration:b", "competence_integration_b",
            dimension_ref=dimension.schema_ref, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=_profile(compose="allow", query="allow"),
        )
        contract = TransitionContractRecord(
            contract_ref, event_schema.schema_ref, 1,
            (StateConditionSpec(
                "condition:competence:integration:a", "affected", dimension.schema_ref, 1,
                ConditionOperator.EQUALS, value_a.schema_ref, 1,
            ),),
            (StateEffectSpec(
                "effect:competence:integration:b", "affected", dimension.schema_ref, 1,
                ChangeOperation.SET, from_value_ref=value_a.schema_ref, from_value_revision=1,
                to_value_ref=value_b.schema_ref, to_value_revision=1,
            ),),
            (evidence_contract.evidence_ref,), SchemaLifecycleStatus.ACTIVE,
        )
        dependency = CapabilityDependencyRecord(
            "capability-dependency:competence:integration", ("type:referent",),
            "action:communicate", 1,
            (StateConditionSpec(
                "condition:competence:integration:capability", "holder", dimension.schema_ref, 1,
                ConditionOperator.EQUALS, value_b.schema_ref, 1,
            ),),
            CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE, CapabilityStatus.UNKNOWN,
            (evidence_contract.evidence_ref,), SchemaLifecycleStatus.ACTIVE,
        )
        assignment = StateAssignment(
            "assignment:competence:integration", "referent:self", dimension.schema_ref, 1,
            value_a.schema_ref, 1, AssignmentStatus.ACTIVE, "actual", 1.0,
            valid_from="2026-01-01T00:00:00Z", evidence_refs=(evidence_state.evidence_ref,),
        )
        attributed = "context:competence:integration:attributed"
        source_app = SemanticApplication(
            "application:competence:integration:source", event_schema.schema_ref, 1,
            (ApplicationBinding("affected", (FillerRef(PortFillerClass.REFERENT, "referent:self"),)),),
            attributed, use_operation=UseOperation.COMPOSE, evidence_refs=(evidence_claim.evidence_ref,),
        )
        actual_app = replace(
            source_app, application_ref="application:competence:integration:actual", context_ref="actual"
        )
        proposition_ref = "referent:competence:integration:proposition"
        proposition_referent = Referent(
            proposition_ref, StorageKind.PROPOSITION, IdentityStatus.CANDIDATE,
            type_refs=("type:proposition",), context_refs=(attributed,), provenance_refs=(evidence_claim.evidence_ref,),
        )
        proposition = PropositionReferent(
            proposition_referent,
            (FillerRef(PortFillerClass.SEMANTIC_APPLICATION, source_app.application_ref),),
            attributed, evidence_refs=(evidence_claim.evidence_ref,),
        )
        source_assessment = SourceAssessmentRecord(
            "source-assessment:competence:integration", "referent:self", 1.0, 1.0, 1.0, 0.0,
            attributed, (evidence_claim.evidence_ref,),
        )
        admission = EpistemicAdmissionRecord(
            "admission:competence:integration", proposition_ref, attributed, "actual",
            AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 1.0,
            ("referent:self",), (evidence_claim.evidence_ref,), ("proof:competence:integration:admission",),
            "policy:competence:integration", source_assessment_pins=((source_assessment.assessment_ref, 1),),
            authorization_ref="authorization:competence:integration",
        )
        event_ref = "referent:competence:integration:event"
        event_referent = Referent(
            event_ref, StorageKind.EVENT_OCCURRENCE, IdentityStatus.RESOLVED,
            type_refs=("type:event_occurrence",), context_refs=("actual",), provenance_refs=(evidence_claim.evidence_ref,),
        )
        event = EventOccurrence(
            event_referent, event_schema.schema_ref, 1, actual_app.application_ref, "actual",
            occurrence_status=OccurrenceStatus.ADMITTED, admission_refs=(admission.admission_ref,),
        )

        records = (
            (RecordKind.EVIDENCE, evidence_contract.evidence_ref, evidence_contract),
            (RecordKind.EVIDENCE, evidence_claim.evidence_ref, evidence_claim),
            (RecordKind.EVIDENCE, evidence_state.evidence_ref, evidence_state),
            (RecordKind.SCHEMA, event_schema.schema_ref, event_schema),
            (RecordKind.SCHEMA, dimension.schema_ref, dimension),
            (RecordKind.SCHEMA, value_a.schema_ref, value_a),
            (RecordKind.SCHEMA, value_b.schema_ref, value_b),
            (RecordKind.TRANSITION_CONTRACT, contract.contract_ref, contract),
            (RecordKind.CAPABILITY_DEPENDENCY, dependency.dependency_ref, dependency),
            (RecordKind.STATE_ASSIGNMENT, assignment.assignment_ref, assignment),
            (RecordKind.SEMANTIC_APPLICATION, source_app.application_ref, source_app),
            (RecordKind.SEMANTIC_APPLICATION, actual_app.application_ref, actual_app),
            (RecordKind.REFERENT, proposition_ref, proposition_referent),
            (RecordKind.PROPOSITION, proposition_ref, proposition),
            (RecordKind.SOURCE_ASSESSMENT, source_assessment.assessment_ref, source_assessment),
            (RecordKind.EPISTEMIC_ADMISSION, admission.admission_ref, admission),
            (RecordKind.REFERENT, event_ref, event_referent),
            (RecordKind.EVENT_OCCURRENCE, event_ref, event),
        )
        seed = GraphPatch(
            "patch:competence:phase11:seed", "actual", "competence", "source:competence", "internal",
            tuple(_patch_op(kind, ref, record) for kind, ref, record in records),
            expected_store_revision=0,
            validation_requirements=("phase11_synthetic_fixture",),
        )
        seeded = store.apply_patch(seed)
        assert seeded.committed, seeded.errors

        coordinator = TransitionCoordinator(store)
        stored_event = store.get_record(RecordKind.EVENT_OCCURRENCE, event_ref).payload
        plans = coordinator.plans_for_event(stored_event, effective_time_ref="2026-07-18T12:00:00Z")
        assert len(plans) == 1 and plans[0].preview.authorized
        assert len(plans[0].state_projections) == 1
        assert len(plans[0].capability_projections) == 1

        # Any intervening write invalidates the plan rather than silently recomputing
        # against a different world snapshot.
        unrelated = EvidenceRecord(
            "evidence:competence:integration:intervening", "source:competence", 1.0,
            "lineage:competence:integration:intervening", context_ref="actual",
        )
        intervening = GraphPatch(
            "patch:competence:phase11:intervening", "actual", "competence", "source:competence", "internal",
            (_patch_op(RecordKind.EVIDENCE, unrelated.evidence_ref, unrelated),),
            expected_store_revision=plans[0].store_revision,
        )
        assert store.apply_patch(intervening).committed
        from cemm.v350.transitions import EffectCommitError
        with pytest.raises(EffectCommitError, match="stale"):
            coordinator.build_patch(stored_event, plans[0], source_ref="source:competence", permission_ref="internal")

        plans = coordinator.plans_for_event(stored_event, effective_time_ref="2026-07-18T12:00:00Z")
        patch = coordinator.build_patch(stored_event, plans[0], source_ref="source:competence", permission_ref="internal")

        # A client cannot forge a different effect around a real admitted event/proof.
        from cemm.v350.storage import encode_record
        forged_operations = []
        for operation in patch.operations:
            if operation.record_kind == RecordKind.STATE_DELTA:
                original_delta = plans[0].preview.state_deltas[0]
                forged_delta = replace(
                    original_delta,
                    to_value_ref=value_a.schema_ref,
                    to_value_revision=1,
                )
                forged_operations.append(replace(
                    operation, payload=encode_record(RecordKind.STATE_DELTA, forged_delta)
                ))
            else:
                forged_operations.append(operation)
        forged_patch = replace(
            patch, patch_ref="patch:competence:phase11:forged-effect",
            operations=tuple(forged_operations),
        )
        forged = store.apply_patch(forged_patch)
        assert not forged.committed
        assert any("effect" in error or "delta" in error for error in forged.errors), forged.errors

        committed = store.apply_patch(patch)
        assert committed.status == PatchCommitStatus.COMMITTED, committed.errors

        proof = store.get_record(RecordKind.TRANSITION_PROOF, plans[0].preview.proof.proof_ref)
        assert proof is not None
        assert proof.payload.admission_pins == ((admission.admission_ref, 1),)
        assert proof.payload.input_assignment_pins == ((assignment.assignment_ref, 1),)
        latest_old = store.get_record(RecordKind.STATE_ASSIGNMENT, assignment.assignment_ref)
        assert latest_old is not None and latest_old.revision == 2
        assert latest_old.payload.status == AssignmentStatus.TERMINATED
        active = [
            item.payload for item in store.records(RecordKind.STATE_ASSIGNMENT)
            if item.payload.holder_ref == "referent:self"
            and item.payload.dimension_ref == dimension.schema_ref
            and item.payload.status == AssignmentStatus.ACTIVE
        ]
        assert [item.value_ref for item in active] == [value_b.schema_ref]
        capability_deltas = store.records(RecordKind.CAPABILITY_DELTA)
        assert any(item.payload.action_schema_ref == "action:communicate" and item.payload.new_status == CapabilityStatus.AVAILABLE for item in capability_deltas)
    finally:
        store.close()
