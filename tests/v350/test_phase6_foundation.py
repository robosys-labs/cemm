from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from cemm.v350.data import DeterministicSQLiteCompiler, SourcePackageLoader
from cemm.v350.facets import ProjectionStatus, ReferentKnowledgeProjector
from cemm.v350.foundation import (
    FoundationCompetenceRunner,
    FoundationPackageAuditor,
    load_foundation_competence,
    load_foundation_contract,
)
from cemm.v350.schema.model import (
    ActionSchema,
    DiscourseActSchema,
    EventSchema,
    FacetSchema,
    PortFillerClass,
    ReferentTypeSchema,
    ResponsePolicySchema,
    SchemaClass,
    SchemaLifecycleStatus,
    StateDimensionSchema,
    StateValueSchema,
    StorageKind,
    UseOperation,
)
from cemm.v350.storage import AssignmentStatus, RecordKind, SemanticStore
from cemm.v350.uol.model import (
    ApplicationBinding,
    CapabilityStatus,
    ChangeOperation,
    EventOccurrence,
    FillerRef,
    ImpactAssessment,
    IdentityStatus,
    OccurrenceStatus,
    Referent,
    SemanticApplication,
    StateDelta,
    UOLGraph,
    Valence,
)
from cemm.v350.uol.validator import UOLValidator


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"


@pytest.fixture(scope="module")
def contract():
    return load_foundation_contract(SOURCE / "foundation_contract.json")


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    directory = tmp_path_factory.mktemp("phase6")
    first = DeterministicSQLiteCompiler().compile(
        SOURCE, directory / "foundation-a.sqlite", make_read_only=False
    )
    second = DeterministicSQLiteCompiler().compile(
        SOURCE, directory / "foundation-b.sqlite", make_read_only=False
    )
    assert first.output_path.read_bytes() == second.output_path.read_bytes()
    assert first.boot_fingerprint == second.boot_fingerprint
    assert first.record_set_fingerprint == second.record_set_fingerprint
    return first


@pytest.fixture(scope="module")
def store(compiled):
    value = SemanticStore(":memory:", boot_path=compiled.output_path)
    yield value
    value.close()


@pytest.fixture(scope="module")
def self_view(store):
    return ReferentKnowledgeProjector(store).project("referent:self", context_ref="actual")


@pytest.fixture(scope="module")
def proposition_view(store):
    return ReferentKnowledgeProjector(store).project(
        "referent:foundation:proposition-example",
        context_ref="competence:foundation",
    )


def test_foundation_contract_audit_is_clean(contract) -> None:
    report = FoundationPackageAuditor(contract).audit(SOURCE)
    assert report.valid, report.issues
    assert report.counts_by_kind == contract.expected_record_counts
    assert report.record_count == sum(contract.expected_record_counts.values())


def test_foundation_compilation_is_byte_deterministic(compiled, contract) -> None:
    manifest = SourcePackageLoader(SOURCE).manifest
    foundation_modules = {item.module_ref for item in manifest.modules if item.phase <= 6}
    assert sum(
        count for module_ref, count in compiled.module_counts.items()
        if module_ref in foundation_modules
    ) == sum(contract.expected_record_counts.values())
    assert compiled.record_count >= sum(contract.expected_record_counts.values())
    assert compiled.byte_size > 0
    assert compiled.boot_fingerprint.startswith("boot-database:")
    assert compiled.record_set_fingerprint.startswith("compiled-record-set:")


def test_manifest_is_reviewed_language_neutral_and_domain_light() -> None:
    manifest = SourcePackageLoader(SOURCE).manifest
    assert {
        "authority": manifest.metadata["authority"],
        "domain_light": manifest.metadata["domain_light"],
        "language_neutral": manifest.metadata["language_neutral"],
        "phase": manifest.metadata["phase"],
        "foundation_phase": manifest.metadata["foundation_phase"],
    } == {
        "authority": "reviewed_source",
        "domain_light": True,
        "language_neutral": True,
        "phase": "8",
        "foundation_phase": "6",
    }
    assert manifest.metadata["foundation_contract_ref"] == "contract:cemm:v350:foundation"
    assert len(manifest.metadata["foundation_contract_sha256"]) == 64
    assert len(manifest.metadata["foundation_competence_sha256"]) == 64
    assert all((SOURCE / item.path).is_file() for item in manifest.modules)


def test_foundational_type_graph_is_complete_and_multiply_inherited(store, contract) -> None:
    registry = store.repositories.schemas.registry()
    for ref, parents in contract.expected_type_parents.items():
        schema = registry.authoritative_schema(ref)
        assert isinstance(schema, ReferentTypeSchema)
        assert tuple(sorted(link.parent_ref for link in schema.parent_links)) == tuple(sorted(parents))
        assert "type:referent" in registry.type_closure(ref, schema.revision)
    software = registry.type_closure("type:software_agent", 1)
    assert {"type:software_agent", "type:agent", "type:digital_entity", "type:concrete", "type:referent"} <= software
    hybrid = registry.type_closure("type:hybrid_entity", 1)
    assert {"type:physical_entity", "type:digital_entity", "type:concrete"} <= hybrid


def test_root_type_covers_only_stable_storage_shapes(store) -> None:
    root = store.repositories.schemas.authoritative("type:referent")
    assert isinstance(root, ReferentTypeSchema)
    assert root.storage_kinds == frozenset(StorageKind)


def test_domain_concepts_remain_unseeded(store, contract) -> None:
    forbidden = {item.casefold() for item in contract.forbidden_domain_semantic_keys}
    schemas = store.repositories.schemas.registry().iter_schemas()
    assert not [item.schema_ref for item in schemas if item.semantic_key.casefold() in forbidden]


def test_universal_facets_are_active_and_entitlement_backed(store, contract) -> None:
    registry = store.repositories.schemas.registry()
    facets = tuple(item for item in registry.iter_schemas() if isinstance(item, FacetSchema))
    assert len(facets) == 20
    assert all(item.lifecycle_status == SchemaLifecycleStatus.ACTIVE for item in facets)
    for ref in contract.required_entitlement_refs:
        item = registry.authoritative_entitlement(ref)
        assert item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
        assert isinstance(registry.authoritative_schema(item.owner_type_ref), ReferentTypeSchema)
        assert isinstance(registry.authoritative_schema(item.facet_ref), FacetSchema)


def test_state_dimensions_and_values_are_bidirectionally_closed(store) -> None:
    registry = store.repositories.schemas.registry()
    dimensions = {
        item.schema_ref: item for item in registry.iter_schemas()
        if isinstance(item, StateDimensionSchema)
    }
    values = {
        item.schema_ref: item for item in registry.iter_schemas()
        if isinstance(item, StateValueSchema)
    }
    assert len(dimensions) == 17
    assert len(values) == 93
    for dimension in dimensions.values():
        assert dimension.holder_type_refs
        assert dimension.value_schema_refs
        for ref in dimension.value_schema_refs:
            assert values[ref].dimension_ref == dimension.schema_ref
    for value in values.values():
        assert value.schema_ref in dimensions[value.dimension_ref].value_schema_refs


def test_self_identity_and_type_are_truthful(store, self_view) -> None:
    self_record = store.repositories.referents.require("referent:self").payload
    assert self_record.identity_status == IdentityStatus.RESOLVED
    assert self_record.type_refs == ("type:software_agent",)
    assert {"type:software_agent", "type:agent", "type:digital_entity", "type:concrete", "type:referent"} <= self_view.type_closure.type_refs
    assert {"identity:self:name", "identity:self:identifier"} <= set(self_view.identity_facet_refs)


def test_action_affordances_are_derived_from_entitlements(self_view) -> None:
    assert {
        "action:communicate",
        "action:observe",
        "action:learn",
        "action:read_semantic_store",
        "action:compile_foundation",
        "action:project_referent_knowledge",
        "action:realize_language",
    } <= set(self_view.afforded_action_refs)


def test_self_function_and_live_capability_remain_distinct(self_view) -> None:
    functions = {item.schema_ref for item in self_view.function_applications}
    assert {
        "function:preserve_semantic_structure",
        "function:compile_reviewed_foundation",
        "function:project_referent_knowledge",
        "function:communicate_meaning",
    } <= functions
    capabilities = {item.action_schema_ref: item.status for item in self_view.live_capabilities}
    assert capabilities["action:read_semantic_store"] == ProjectionStatus.ACTIVE
    assert capabilities["action:compile_foundation"] == ProjectionStatus.ACTIVE
    assert capabilities["action:project_referent_knowledge"] == ProjectionStatus.ACTIVE
    assert capabilities["action:realize_language"] == ProjectionStatus.BLOCKED


def test_available_self_capabilities_have_plan_execute_competence(store) -> None:
    for stored in store.repositories.capability_instances.all():
        capability = stored.payload
        action = store.repositories.schemas.registry().schema(
            capability.action_schema_ref, capability.action_schema_revision
        )
        assert isinstance(action, ActionSchema)
        if capability.status == CapabilityStatus.AVAILABLE:
            assert action.use_profile.permits(UseOperation.PLAN)
            assert action.use_profile.permits(UseOperation.EXECUTE)
            required = {hook.operation for hook in action.competence_hooks if hook.required}
            assert {UseOperation.PLAN, UseOperation.EXECUTE} <= required
            assert capability.evidence_refs
            from cemm.v350.foundation import resolve_runtime_component
            component_ref = str(action.metadata.get("runtime_component") or "")
            assert component_ref
            assert resolve_runtime_component(component_ref) is not None
        elif capability.action_schema_ref == "action:realize_language":
            assert capability.status == CapabilityStatus.UNAVAILABLE
            assert not action.use_profile.permits(UseOperation.EXECUTE)


def test_proposition_affective_and_capability_facets_are_inapplicable(proposition_view) -> None:
    assert proposition_view.entitlement("facet:affective").status == ProjectionStatus.INAPPLICABLE
    assert proposition_view.entitlement("facet:capability").status == ProjectionStatus.INAPPLICABLE
    assert proposition_view.entitlement("facet:epistemic").status in {
        ProjectionStatus.LATENT, ProjectionStatus.UNKNOWN
    }


def test_truth_support_and_epistemic_basis_are_orthogonal(store) -> None:
    registry = store.repositories.schemas.registry()
    truth = registry.authoritative_schema("state:truth_status")
    basis = registry.authoritative_schema("state:epistemic_basis")
    assert truth.exclusive
    assert truth.value_cardinality.maximum == 1
    assert {registry.authoritative_schema(ref).semantic_key for ref in truth.value_schema_refs} == {
        "supported", "opposed", "both", "undetermined"
    }
    assert not basis.exclusive
    assert {registry.authoritative_schema(ref).semantic_key for ref in basis.value_schema_refs} == {
        "observed", "reported", "inferred", "default_expected", "assumed"
    }
    assert set(truth.value_schema_refs).isdisjoint(basis.value_schema_refs)
    assert registry.authoritative_schema("operator:truth_status:opposed").operator_family == "truth_status"
    assert registry.authoritative_schema("operator:epistemic_basis:reported").operator_family == "epistemic_basis"


def test_movement_action_modes_are_distinct_from_event_occurrence(store) -> None:
    registry = store.repositories.schemas.registry()
    abstract = registry.authoritative_schema("action:move")
    external = registry.authoritative_schema("action:externally_caused_move")
    self_move = registry.authoritative_schema("action:self_initiated_move")
    event = registry.authoritative_schema("event:move")
    assert abstract.schema_class == external.schema_class == self_move.schema_class == SchemaClass.ACTION
    assert event.schema_class == SchemaClass.EVENT
    assert external.controlling_port_ref == "affected"
    assert not external.intentional_required
    assert external.port("affected").accepted_type_refs == ("type:physical_entity",)
    assert self_move.controlling_port_ref == "actor"
    assert self_move.intentional_required
    assert self_move.port("actor").accepted_type_refs == ("type:biological_agent",)
    assert not event.use_profile.permits(UseOperation.TRANSITION)


def test_truth_default_is_expected_but_never_materialized(store, proposition_view) -> None:
    truth = next(item for item in proposition_view.state_applicability if item.dimension_ref == "state:truth_status")
    assert truth.status == ProjectionStatus.DEFAULT_EXPECTED
    assert truth.active_value_refs == ()
    assert truth.default_expectations[0].value_ref == "state-value:truth_status:undetermined"
    assert not [
        item for item in store.repositories.state_assignments.all()
        if item.payload.holder_ref == proposition_view.referent_ref
        and item.payload.dimension_ref == "state:truth_status"
        and item.payload.status == AssignmentStatus.ACTIVE
    ]


def test_boot_has_no_assumed_live_state_or_world_knowledge(store) -> None:
    assert store.repositories.state_assignments.all() == ()
    assert store.repositories.knowledge.all() == ()


def test_core_event_schemas_do_not_claim_phase11_authority(store) -> None:
    registry = store.repositories.schemas.registry()
    events = tuple(item for item in registry.iter_schemas() if isinstance(item, EventSchema))
    assert len(events) == 24
    correct = registry.authoritative_schema("event:correct")
    assert {link.parent_ref for link in correct.parent_links} == {
        "event:communicative", "event:epistemic_change"
    }
    for event in events:
        assert event.transition_contract_refs == ()
        assert event.result_contract_refs == ()
        assert event.causal_contract_refs == ()
        assert event.impact_rule_refs == ()
        assert not event.use_profile.permits(UseOperation.TRANSITION)


def test_loss_decrease_valence_and_polarity_are_orthogonal(store) -> None:
    registry = store.repositories.schemas.registry()
    loss = registry.authoritative_schema("event:lose")
    decrease = registry.authoritative_schema("event:decrease")
    valence = registry.authoritative_schema("state:valence")
    negative_polarity = registry.authoritative_schema("operator:polarity:negative")
    assert loss.schema_ref != decrease.schema_ref
    assert loss.schema_class == decrease.schema_class == SchemaClass.EVENT
    assert valence.schema_class == SchemaClass.STATE_DIMENSION
    assert negative_polarity.schema_class == SchemaClass.OPERATOR
    assert len({loss.semantic_key, decrease.semantic_key, valence.semantic_key, negative_polarity.semantic_key}) == 4


def test_claim_and_response_foundations_preserve_target_and_uncertainty(store) -> None:
    registry = store.repositories.schemas.registry()
    claim = registry.authoritative_schema("event:claim")
    assert isinstance(claim, EventSchema)
    assert claim.metadata["admission_policy"] == "independent_epistemic_admission"
    acknowledge = registry.authoritative_schema("discourse-act:acknowledge")
    assert isinstance(acknowledge, DiscourseActSchema)
    assert acknowledge.content_port_ref
    assert acknowledge.port(acknowledge.content_port_ref).cardinality.minimum == 1
    policies = tuple(item for item in registry.iter_schemas() if isinstance(item, ResponsePolicySchema))
    assert policies
    assert all(not item.literal_realization_refs for item in policies)


def test_all_declared_foundation_competence_cases_pass(store, contract) -> None:
    cases = load_foundation_competence(SOURCE / "competence" / "foundation.jsonl")
    assert set(contract.required_competence_case_refs) <= {item.case_ref for item in cases}
    report = FoundationCompetenceRunner(store).run(cases)
    assert report.passed, report.failed




def _reported_fictional_move_graph(store) -> UOLGraph:
    mover = Referent(
        "referent:fixture:mover",
        storage_kind=StorageKind.ORDINARY,
        identity_status=IdentityStatus.RESOLVED,
        type_refs=("type:physical_entity",),
        context_refs=("fictional",),
    )
    stakeholder_a = Referent(
        "referent:fixture:stakeholder-a",
        identity_status=IdentityStatus.RESOLVED,
        type_refs=("type:agent",),
        context_refs=("fictional",),
    )
    stakeholder_b = Referent(
        "referent:fixture:stakeholder-b",
        identity_status=IdentityStatus.RESOLVED,
        type_refs=("type:agent",),
        context_refs=("fictional",),
    )
    application = SemanticApplication(
        "application:fixture:move",
        "event:move",
        1,
        (ApplicationBinding(
            "mover",
            (FillerRef(PortFillerClass.REFERENT, mover.referent_ref),),
        ),),
        "fictional",
        use_operation=UseOperation.COMPOSE,
    )
    event_referent = Referent(
        "event:fixture:move",
        storage_kind=StorageKind.EVENT_OCCURRENCE,
        identity_status=IdentityStatus.RESOLVED,
        type_refs=("type:event_occurrence",),
        context_refs=("fictional",),
    )
    event = EventOccurrence(
        event_referent,
        "event:move",
        1,
        application.application_ref,
        "fictional",
        occurrence_status=OccurrenceStatus.REPORTED,
    )
    return UOLGraph(
        "graph:fixture:reported-fictional-move",
        referents={item.referent_ref: item for item in (
            mover, stakeholder_a, stakeholder_b, event_referent
        )},
        applications={application.application_ref: application},
        events={event.event_ref: event},
        root_refs=(FillerRef(PortFillerClass.REFERENT, event.event_ref),),
    )


def test_reported_fictional_event_is_representable_but_cannot_transition(store) -> None:
    graph = _reported_fictional_move_graph(store)
    validator = UOLValidator(store.repositories.schemas.registry())
    report = validator.validate(graph)
    assert report.valid, report.errors
    event = graph.events["event:fixture:move"]
    delta = StateDelta(
        "delta:fixture:location",
        event.event_ref,
        "referent:fixture:mover",
        "state:location_status",
        ChangeOperation.SET,
        "fictional",
        "time:fixture",
        to_value_ref="state-value:location_status:known",
        to_value_revision=1,
        proof_refs=("proof:fixture",),
    )
    invalid = UOLGraph(
        graph.graph_ref,
        referents=graph.referents,
        applications=graph.applications,
        events=graph.events,
        state_deltas=(delta,),
        root_refs=graph.root_refs,
    )
    errors = {item.code for item in validator.validate(invalid).errors}
    assert "event_transition_not_authorized" in errors
    assert "unadmitted_event_transition" in errors
    assert "event_transition_missing_admission" in errors


def test_impact_valence_can_differ_by_stakeholder_in_same_context(store) -> None:
    graph = _reported_fictional_move_graph(store)
    event = graph.events["event:fixture:move"]
    impacts = (
        ImpactAssessment(
            "impact:fixture:a",
            event.event_ref,
            "referent:fixture:mover",
            "referent:fixture:stakeholder-a",
            ("facet:localization",),
            ChangeOperation.SET,
            Valence.BENEFICIAL,
            "fictional",
            proof_refs=("proof:impact:a",),
        ),
        ImpactAssessment(
            "impact:fixture:b",
            event.event_ref,
            "referent:fixture:mover",
            "referent:fixture:stakeholder-b",
            ("facet:localization",),
            ChangeOperation.SET,
            Valence.HARMFUL,
            "fictional",
            proof_refs=("proof:impact:b",),
        ),
    )
    assessed = UOLGraph(
        graph.graph_ref,
        referents=graph.referents,
        applications=graph.applications,
        events=graph.events,
        impact_assessments=impacts,
        root_refs=graph.root_refs,
    )
    report = UOLValidator(store.repositories.schemas.registry()).validate(assessed)
    assert report.valid, report.errors
    assert {item.valence for item in assessed.impact_assessments} == {
        Valence.BENEFICIAL, Valence.HARMFUL
    }


def test_jsonl_sources_are_canonical_and_have_unique_record_identities() -> None:
    records = SourcePackageLoader(SOURCE).load()
    identities = {(item.record_kind, item.record_ref, item.revision) for item in records}
    assert len(identities) == len(records)
    for path in SOURCE.rglob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            value = json.loads(raw)
            assert raw == json.dumps(value, sort_keys=True, separators=(",", ":"))


def test_foundation_audit_detects_competence_tampering(tmp_path, contract) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    competence = copied / "competence" / "foundation.jsonl"
    competence.write_text(competence.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report = FoundationPackageAuditor(contract).audit(copied)
    assert not report.valid
    assert "manifest_hash_mismatch" in {item.code for item in report.errors}


def test_foundation_audit_detects_unreviewed_source_change(tmp_path, contract) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    evidence = copied / "foundation" / "evidence.jsonl"
    extra = {
        "confidence": 1.0,
        "context_ref": "actual",
        "evidence_ref": "evidence:fixture:unreviewed",
        "lineage_ref": "lineage:fixture:unreviewed",
        "metadata": {"fixture": True},
        "observed_at": "2026-07-17T00:00:00Z",
        "permission_ref": "internal",
        "source_ref": "source:fixture:unreviewed",
    }
    evidence.write_text(
        evidence.read_text(encoding="utf-8")
        + json.dumps(extra, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    report = FoundationPackageAuditor(contract).audit(copied)
    codes = {item.code for item in report.errors}
    assert "record_count_mismatch" in codes
    assert "source_fingerprint_mismatch" in codes
