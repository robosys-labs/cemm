from __future__ import annotations

from dataclasses import fields, replace

from cemm.v350.schema.model import (
    Cardinality,
    ActionSchema,
    EventSchema,
    LocalPortSchema,
    OpenBindingPurpose,
    PortFillerClass,
    ReferentTypeSchema,
    StateDimensionSchema,
    StateValueSchema,
    SchemaLifecycleStatus,
    SchemaParentLink,
    StorageKind,
    UseProfile,
)
from cemm.v350.schema.registry import SchemaRegistry
from cemm.v350.uol.equivalence import compare_uol_graphs, semantically_equivalent
from cemm.v350.uol.model import (
    ApplicationBinding,
    CapabilityDelta,
    CapabilityStatus,
    ChangeOperation,
    ClaimForce,
    ClaimOccurrence,
    EventOccurrence,
    FillerRef,
    IdentityStatus,
    ImpactAssessment,
    ImportanceAssessment,
    ImportanceClass,
    OccurrenceStatus,
    Polarity,
    PortFillerClass as UOLPortFillerClass,
    PropositionReferent,
    Referent,
    Reversibility,
    SemanticApplication,
    SemanticVariable,
    StateDelta,
    UOLGraph,
    Valence,
)
from cemm.v350.uol.validator import UOLValidator


def profile(**values: str) -> UseProfile:
    return UseProfile.from_mapping(values)


def type_schema(
    ref: str, *parents: str, storage_kinds: frozenset[StorageKind] = frozenset({StorageKind.ORDINARY})
) -> ReferentTypeSchema:
    return ReferentTypeSchema(
        schema_ref=ref,
        semantic_key=ref.split(":")[-1],
        parent_links=tuple(SchemaParentLink(item) for item in parents),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(mention="allow", ground="allow", compose="allow", query="allow"),
        storage_kinds=storage_kinds,
    )


def registry() -> SchemaRegistry:
    referent = type_schema("type:referent")
    animal = type_schema("type:animal", "type:referent")
    person = type_schema("type:person", "type:referent")
    proposition_type = type_schema(
        "type:proposition", "type:referent", storage_kinds=frozenset({StorageKind.PROPOSITION})
    )
    event_occurrence_type = type_schema(
        "type:event-occurrence", "type:referent",
        storage_kinds=frozenset({StorageKind.EVENT_OCCURRENCE}),
    )
    claim_type = type_schema(
        "type:claim", "type:event-occurrence",
        storage_kinds=frozenset({StorageKind.EVENT_OCCURRENCE}),
    )
    die = EventSchema(
        schema_ref="event:die",
        semantic_key="die",
        local_ports=(LocalPortSchema(
            "affected",
            accepted_type_refs=("type:animal",),
            cardinality=Cardinality(1, 1),
        ),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow", transition="allow"),
    )
    named = EventSchema(
        schema_ref="property:named",
        semantic_key="named",
        local_ports=(
            LocalPortSchema("holder", accepted_type_refs=("type:referent",), cardinality=Cardinality(1, 1)),
            LocalPortSchema(
                "value",
                filler_classes=frozenset({PortFillerClass.REFERENT, PortFillerClass.SEMANTIC_VARIABLE}),
                cardinality=Cardinality(1, 1),
                queryable=True,
                open_binding_purposes=frozenset({OpenBindingPurpose.QUERY}),
            ),
        ),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow"),
    )
    life_status = StateDimensionSchema(
        schema_ref="state:life-status",
        semantic_key="life_status",
        holder_type_refs=("type:animal",),
        value_schema_refs=("state-value:dead",),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow", transition="allow"),
    )
    dead = StateValueSchema(
        schema_ref="state-value:dead",
        semantic_key="dead",
        dimension_ref="state:life-status",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow", transition="allow"),
    )
    read = ActionSchema(
        schema_ref="action:read",
        semantic_key="read",
        local_ports=(LocalPortSchema(
            "actor", accepted_type_refs=("type:referent",), cardinality=Cardinality(1, 1)
        ),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(compose="allow", query="allow", transition="allow"),
    )
    return SchemaRegistry([
        referent, animal, person, proposition_type, event_occurrence_type, claim_type,
        die, named, life_status, dead, read,
    ])


def ref(
    ref_id: str, *types: str, storage: StorageKind = StorageKind.ORDINARY,
    context: str = "actual",
) -> Referent:
    return Referent(
        ref_id,
        storage_kind=storage,
        identity_status=IdentityStatus.RESOLVED if storage == StorageKind.ORDINARY else IdentityStatus.PROVISIONAL,
        type_refs=tuple(types),
        context_refs=(context,),
    )


def proposition(ref_id: str, app_ref: str, *, polarity: Polarity = Polarity.POSITIVE, context: str = "actual") -> PropositionReferent:
    base = ref(
        ref_id, "type:proposition", storage=StorageKind.PROPOSITION, context=context
    )
    return PropositionReferent(
        referent=base,
        content_refs=(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, app_ref),),
        context_ref=context,
        polarity=polarity,
    )


def query_graph(*, graph_id: str, app_id: str, variable_id: str, proposition_id: str, reverse_bindings: bool = False) -> UOLGraph:
    user = ref("ref:user", "type:person")
    variable = SemanticVariable(variable_id, expected_type_refs=("type:referent",))
    holder = ApplicationBinding("holder", (FillerRef(PortFillerClass.REFERENT, user.referent_ref),))
    value = ApplicationBinding(
        "value",
        (FillerRef(PortFillerClass.SEMANTIC_VARIABLE, variable_id),),
        open_binding_purpose=OpenBindingPurpose.QUERY,
    )
    bindings = (value, holder) if reverse_bindings else (holder, value)
    application = SemanticApplication(
        app_id,
        "property:named",
        1,
        bindings,
        "actual",
        use_operation=__import__("cemm.v350.schema.model", fromlist=["UseOperation"]).UseOperation.QUERY,
    )
    prop = proposition(proposition_id, app_id)
    return UOLGraph(
        graph_id,
        referents={user.referent_ref: user, prop.proposition_ref: prop.referent},
        applications={app_id: application},
        variables={variable_id: variable},
        propositions={prop.proposition_ref: prop},
        root_refs=(FillerRef(PortFillerClass.REFERENT, prop.proposition_ref),),
    )


def event_graph(status: OccurrenceStatus = OccurrenceStatus.CLAIMED, *, include_delta: bool = False) -> UOLGraph:
    fox = ref("ref:fox", "type:animal")
    app = SemanticApplication(
        "app:die",
        "event:die",
        1,
        (ApplicationBinding("affected", (FillerRef(PortFillerClass.REFERENT, fox.referent_ref),)),),
        "reported:john",
    )
    event_base = ref(
        "event-occurrence:1", "type:event-occurrence",
        storage=StorageKind.EVENT_OCCURRENCE, context="reported:john"
    )
    event = EventOccurrence(
        event_base,
        "event:die",
        1,
        app.application_ref,
        "reported:john",
        occurrence_status=status,
        time_ref="time:t1",
        admission_refs=("admission:knowledge:1",) if status == OccurrenceStatus.ADMITTED else (),
    )
    prop = proposition("proposition:death", app.application_ref, context="reported:john")
    john = ref("ref:john", "type:person")
    self_ref = ref("ref:self", "type:person")
    claim_base = ref(
        "claim:1", "type:claim", storage=StorageKind.EVENT_OCCURRENCE, context="actual"
    )
    claim = ClaimOccurrence(
        claim_base,
        john.referent_ref,
        (self_ref.referent_ref,),
        prop.proposition_ref,
        ClaimForce.ASSERTED,
        "actual",
        "reported:john",
    )
    deltas = ()
    if include_delta:
        deltas = (StateDelta(
            "state-delta:death",
            event.event_ref,
            fox.referent_ref,
            "state:life-status",
            ChangeOperation.SET,
            event.context_ref,
            "time:t1",
            to_value_ref="state-value:dead",
            proof_refs=("proof:transition",),
        ),)
    referents = {
        item.referent_ref: item
        for item in (fox, event.referent, prop.referent, john, self_ref, claim.referent)
    }
    return UOLGraph(
        "graph:event",
        referents=referents,
        applications={app.application_ref: app},
        propositions={prop.proposition_ref: prop},
        claims={claim.claim_ref: claim},
        events={event.event_ref: event},
        state_deltas=deltas,
        root_refs=(FillerRef(PortFillerClass.REFERENT, claim.claim_ref),),
    )


def test_phase3_records_are_referent_backed_not_parallel_identity_families() -> None:
    graph = event_graph()
    event = next(iter(graph.events.values()))
    claim = next(iter(graph.claims.values()))
    proposition_record = next(iter(graph.propositions.values()))
    assert event.referent.storage_kind == StorageKind.EVENT_OCCURRENCE
    assert claim.referent.storage_kind == StorageKind.EVENT_OCCURRENCE
    assert proposition_record.referent.storage_kind == StorageKind.PROPOSITION
    assert set(graph.propositions) <= set(graph.referents)


def test_equivalence_is_binding_order_independent_and_variable_alpha_equivalent() -> None:
    left = query_graph(graph_id="g:left", app_id="a:left", variable_id="v:left", proposition_id="p:left")
    right = query_graph(graph_id="g:right", app_id="a:right", variable_id="v:right", proposition_id="p:right", reverse_bindings=True)
    assessment = compare_uol_graphs(left, right)
    assert assessment.equivalent, assessment


def test_polarity_is_semantic_and_breaks_equivalence() -> None:
    left = query_graph(graph_id="g:left", app_id="a:left", variable_id="v:left", proposition_id="p:left")
    original = next(iter(left.propositions.values()))
    negative = replace(original, polarity=Polarity.NEGATIVE)
    right = replace(
        left,
        graph_ref="g:right",
        propositions={negative.proposition_ref: negative},
    )
    assert not semantically_equivalent(left, right)


def test_claim_is_not_actual_world_admission_or_state_transition() -> None:
    graph = event_graph(OccurrenceStatus.CLAIMED, include_delta=False)
    report = UOLValidator(registry()).validate(graph)
    assert report.valid, report.errors
    claim = next(iter(graph.claims.values()))
    event = next(iter(graph.events.values()))
    assert claim.reported_context_ref == event.context_ref
    assert event.context_ref != "actual"
    assert not graph.state_deltas


def test_unadmitted_event_cannot_produce_state_delta() -> None:
    report = UOLValidator(registry()).validate(event_graph(OccurrenceStatus.CLAIMED, include_delta=True))
    assert any(item.code == "unadmitted_event_transition" for item in report.errors)


def test_admitted_event_delta_is_context_isolated_and_valid() -> None:
    graph = event_graph(OccurrenceStatus.ADMITTED, include_delta=True)
    report = UOLValidator(registry()).validate(graph)
    assert report.valid, report.errors
    assert graph.state_deltas[0].context_ref == graph.events["event-occurrence:1"].context_ref


def test_capability_delta_is_separate_from_state_delta() -> None:
    state = StateDelta(
        "sd:charge",
        "event:dim",
        "ref:lumin",
        "state:charge",
        ChangeOperation.DECREASE,
        "actual",
        "time:t1",
        magnitude_ref="quantity:1",
        proof_refs=("proof:dim",),
    )
    capability = CapabilityDelta(
        "cd:read",
        state.delta_ref,
        "ref:lumin",
        "action:read",
        CapabilityStatus.AVAILABLE,
        CapabilityStatus.BLOCKED,
        "actual",
        "time:t1",
        "dependency:read-charge",
        proof_refs=("proof:dependency",),
    )
    assert state.operation == ChangeOperation.DECREASE
    assert capability.new_status == CapabilityStatus.BLOCKED
    assert capability.trigger_ref == state.delta_ref


def test_impact_is_stakeholder_relative_and_not_a_fact() -> None:
    first = ImpactAssessment(
        "impact:user",
        "event:death",
        "ref:fox",
        "ref:user",
        ("facet:life",),
        ChangeOperation.LOSE,
        Valence.HARMFUL,
        "actual",
        reversibility=Reversibility.IRREVERSIBLE,
        proof_refs=("proof:death",),
    )
    second = replace(first, assessment_ref="impact:farmer", stakeholder_ref="ref:farmer", valence=Valence.MIXED)
    assert first.stakeholder_ref != second.stakeholder_ref
    assert first.valence != second.valence


def test_importance_requires_evidence_and_reason() -> None:
    assessment = ImportanceAssessment(
        "importance:fox:user",
        "ref:fox",
        "ref:user",
        "actual",
        0.8,
        ImportanceClass.HIGH,
        ("evidence:ownership",),
        ("ownership",),
    )
    assert assessment.importance_class == ImportanceClass.HIGH


def test_uol_records_have_no_undifferentiated_negative_field() -> None:
    record_types = [
        SemanticApplication,
        PropositionReferent,
        StateDelta,
        CapabilityDelta,
        ImpactAssessment,
        ImportanceAssessment,
    ]
    assert all("negative" not in {item.name for item in fields(record_type)} for record_type in record_types)


def test_record_fingerprint_preserves_provenance_but_semantic_equivalence_does_not() -> None:
    left = query_graph(graph_id="g:left", app_id="a:left", variable_id="v:left", proposition_id="p:left")
    user = left.referents["ref:user"]
    changed_user = replace(user, provenance_refs=("evidence:other",))
    right = replace(left, graph_ref="g:right", referents={**left.referents, "ref:user": changed_user})
    assert user.record_fingerprint != changed_user.record_fingerprint
    assert semantically_equivalent(left, right)


def test_context_and_schema_revision_are_semantic() -> None:
    left = query_graph(graph_id="g:left", app_id="a:left", variable_id="v:left", proposition_id="p:left")
    app = left.applications["a:left"]
    context_changed = replace(
        left,
        graph_ref="g:context",
        applications={app.application_ref: replace(app, context_ref="hypothetical:1")},
    )
    revision_changed = replace(
        left,
        graph_ref="g:revision",
        applications={app.application_ref: replace(app, schema_revision=2)},
    )
    assert not semantically_equivalent(left, context_changed)
    assert not semantically_equivalent(left, revision_changed)


def _multi_value_graph(*, ordered: bool, reverse: bool, group_kind=None) -> UOLGraph:
    one = ref("ref:one", "type:referent")
    two = ref("ref:two", "type:referent")
    fillers = (
        FillerRef(PortFillerClass.REFERENT, two.referent_ref),
        FillerRef(PortFillerClass.REFERENT, one.referent_ref),
    ) if reverse else (
        FillerRef(PortFillerClass.REFERENT, one.referent_ref),
        FillerRef(PortFillerClass.REFERENT, two.referent_ref),
    )
    if group_kind is not None:
        from cemm.v350.uol.model import CoordinationGroup
        group = CoordinationGroup("group:items", group_kind, fillers)
        return UOLGraph(
            "graph:group",
            referents={one.referent_ref: one, two.referent_ref: two},
            coordination_groups={group.group_ref: group},
            root_refs=(FillerRef(PortFillerClass.COORDINATION_GROUP, group.group_ref),),
        )
    application = SemanticApplication(
        "application:values",
        "relation:values",
        1,
        (ApplicationBinding("items", fillers, ordered=ordered),),
        "actual",
    )
    return UOLGraph(
        "graph:values",
        referents={one.referent_ref: one, two.referent_ref: two},
        applications={application.application_ref: application},
        root_refs=(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, application.application_ref),),
    )


def test_ordered_fillers_and_list_coordination_preserve_order() -> None:
    from cemm.v350.uol.model import CoordinationKind

    assert semantically_equivalent(
        _multi_value_graph(ordered=False, reverse=False),
        _multi_value_graph(ordered=False, reverse=True),
    )
    assert not semantically_equivalent(
        _multi_value_graph(ordered=True, reverse=False),
        _multi_value_graph(ordered=True, reverse=True),
    )
    assert semantically_equivalent(
        _multi_value_graph(ordered=False, reverse=False, group_kind=CoordinationKind.AND),
        _multi_value_graph(ordered=False, reverse=True, group_kind=CoordinationKind.AND),
    )
    assert not semantically_equivalent(
        _multi_value_graph(ordered=False, reverse=False, group_kind=CoordinationKind.LIST),
        _multi_value_graph(ordered=False, reverse=True, group_kind=CoordinationKind.LIST),
    )


def test_admission_proof_identity_is_provenance_but_admission_presence_is_semantic() -> None:
    left = event_graph(OccurrenceStatus.ADMITTED, include_delta=False)
    event = left.events["event-occurrence:1"]
    other_proof = replace(
        left,
        graph_ref="graph:other-proof",
        events={event.event_ref: replace(event, admission_refs=("admission:other",))},
    )
    absent = replace(
        left,
        graph_ref="graph:no-admission",
        events={event.event_ref: replace(event, admission_refs=())},
    )
    assert semantically_equivalent(left, other_proof)
    assert not semantically_equivalent(left, absent)


def test_admitted_event_without_independent_admission_cannot_transition() -> None:
    graph = event_graph(OccurrenceStatus.ADMITTED, include_delta=True)
    event = graph.events["event-occurrence:1"]
    invalid = replace(graph, events={event.event_ref: replace(event, admission_refs=())})
    report = UOLValidator(registry()).validate(invalid)
    assert any(item.code == "event_transition_missing_admission" for item in report.errors)


def test_transition_context_leak_is_rejected() -> None:
    graph = event_graph(OccurrenceStatus.ADMITTED, include_delta=True)
    delta = graph.state_deltas[0]
    invalid = replace(graph, state_deltas=(replace(delta, context_ref="actual"),))
    report = UOLValidator(registry()).validate(invalid)
    assert any(item.code == "transition_context_leak" for item in report.errors)


def test_state_delta_holder_must_satisfy_dimension_type() -> None:
    graph = event_graph(OccurrenceStatus.ADMITTED, include_delta=True)
    fox = graph.referents["ref:fox"]
    invalid = replace(
        graph,
        referents={**graph.referents, fox.referent_ref: replace(fox, type_refs=("type:person",))},
    )
    report = UOLValidator(registry()).validate(invalid)
    assert any(item.code == "state_delta_holder_type" for item in report.errors)


def test_open_variable_purpose_must_be_licensed_by_local_port() -> None:
    graph = query_graph(graph_id="g", app_id="a", variable_id="v", proposition_id="p")
    app = graph.applications["a"]
    value = app.binding("value")
    assert value is not None
    invalid_value = replace(value, open_binding_purpose=OpenBindingPurpose.LEARNING)
    invalid_app = replace(app, bindings=tuple(
        invalid_value if item.port_ref == "value" else item for item in app.bindings
    ))
    report = UOLValidator(registry()).validate(
        replace(graph, applications={invalid_app.application_ref: invalid_app})
    )
    assert any(item.code == "open_binding_not_authorized" for item in report.errors)


def test_impact_cannot_cross_context_boundary() -> None:
    graph = event_graph(OccurrenceStatus.ADMITTED, include_delta=True)
    impact = ImpactAssessment(
        "impact:death",
        graph.state_deltas[0].delta_ref,
        "ref:fox",
        "ref:john",
        ("facet:life",),
        ChangeOperation.LOSE,
        Valence.HARMFUL,
        "actual",
        proof_refs=("proof:impact",),
    )
    report = UOLValidator(registry()).validate(replace(graph, impact_assessments=(impact,)))
    assert any(item.code == "impact_context_leak" for item in report.errors)


def test_loss_is_not_a_state_dimension_operation() -> None:
    import pytest

    with pytest.raises(ValueError, match="not a state-dimension operation"):
        StateDelta(
            "delta:loss",
            "event:loss",
            "ref:fox",
            "state:life-status",
            ChangeOperation.LOSE,
            "actual",
            "time:t1",
            proof_refs=("proof:loss",),
        )
