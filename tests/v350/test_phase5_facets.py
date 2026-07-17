from __future__ import annotations

from dataclasses import replace

from cemm.v350.facets import (
    MappingConditionEvaluator,
    ProjectionStatus,
    ReferentKnowledgeProjector,
    StoreConditionEvaluator,
    TypeClosureCompiler,
)
from cemm.v350.schema.model import (
    ActionSchema,
    EntitlementApplicability,
    EntitlementInheritancePolicy,
    FacetEntitlement,
    FacetSchema,
    ReferentTypeSchema,
    SchemaLifecycleStatus,
    SchemaParentLink,
    StateDimensionSchema,
    StateValueSchema,
    StorageKind,
    UseProfile,
)
from cemm.v350.storage import (
    AssertionStatus,
    AssignmentStatus,
    CapabilityInstance,
    ConditionTruth,
    DefaultRuleRecord,
    EvidenceRecord,
    KnowledgeRecord,
    KnowledgeStatus,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    ReferentTypeAssertion,
    SemanticStore,
    StateAssignment,
    encode_record,
)
from cemm.v350.storage.codec import record_ref, record_revision
from cemm.v350.uol.model import (
    ApplicationBinding,
    CapabilityStatus,
    FillerRef,
    IdentityStatus,
    PropositionReferent,
    Referent,
    SemanticApplication,
)
from cemm.v350.schema.model import (
    Cardinality,
    LocalPortSchema,
    PortFillerClass,
    PropertySchema,
    UseOperation,
)


def profile(**values: str) -> UseProfile:
    return UseProfile.from_mapping(values)


def active_type(schema_ref: str, *parents: str) -> ReferentTypeSchema:
    return ReferentTypeSchema(
        schema_ref=schema_ref,
        semantic_key=schema_ref.rsplit(":", 1)[-1],
        parent_links=tuple(SchemaParentLink(item) for item in parents),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        storage_kinds=frozenset({StorageKind.ORDINARY}),
        use_profile=profile(mention="allow", ground="allow", compose="allow", query="allow"),
    )


def active_entitlement(
    entitlement_ref: str,
    owner: str,
    facet: str,
    applicability: EntitlementApplicability,
    *,
    policy: EntitlementInheritancePolicy = EntitlementInheritancePolicy.INHERIT,
    domains: tuple[str, ...] = (),
    defaults: tuple[str, ...] = (),
    contexts: tuple[str, ...] = (),
    temporal: tuple[str, ...] = (),
) -> FacetEntitlement:
    return FacetEntitlement(
        entitlement_ref=entitlement_ref,
        owner_type_ref=owner,
        facet_ref=facet,
        applicability=applicability,
        inheritance_policy=policy,
        value_domain_refs=domains,
        default_rule_refs=defaults,
        context_constraints=contexts,
        temporal_constraints=temporal,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=profile(ground="allow", compose="allow", query="allow"),
    )


def op(kind: RecordKind, value) -> PatchOperation:
    revision = record_revision(kind, value)
    return PatchOperation(
        operation_ref=f"op:{kind.value}:{record_ref(kind, value)}:{revision}",
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=kind,
        target_ref=record_ref(kind, value),
        record_revision=revision,
        payload=encode_record(kind, value),
    )


def commit(store: SemanticStore, ref: str, *operations: PatchOperation) -> None:
    result = store.apply_patch(GraphPatch(
        patch_ref=ref,
        context_ref="actual",
        scope_ref="global",
        source_ref="test",
        permission_ref="internal",
        operations=operations,
        expected_store_revision=store.revision,
    ))
    assert result.committed, result.errors


def base_store(*entitlements: FacetEntitlement) -> SemanticStore:
    store = SemanticStore(":memory:")
    schemas = [
        active_type("type:referent"),
        active_type("type:physical", "type:referent"),
        active_type("type:living", "type:physical"),
        active_type("type:animal", "type:living"),
        active_type("type:agent", "type:referent"),
        active_type("type:fox", "type:animal", "type:agent"),
        active_type("type:proposition", "type:referent"),
        FacetSchema(
            schema_ref="facet:health",
            semantic_key="health",
            facet_family="state",
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(ground="allow", compose="allow", query="allow"),
        ),
        FacetSchema(
            schema_ref="facet:motion",
            semantic_key="motion",
            facet_family="capability",
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(ground="allow", compose="allow", query="allow"),
        ),
        StateDimensionSchema(
            schema_ref="state:health",
            semantic_key="health",
            holder_type_refs=("type:living",),
            value_schema_refs=("state-value:healthy", "state-value:sick"),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(ground="allow", compose="allow", query="allow"),
            metadata={"facet_ref": "facet:health"},
        ),
        StateValueSchema(
            schema_ref="state-value:healthy",
            semantic_key="healthy",
            dimension_ref="state:health",
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(ground="allow", compose="allow", query="allow"),
        ),
        StateValueSchema(
            schema_ref="state-value:sick",
            semantic_key="sick",
            dimension_ref="state:health",
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(ground="allow", compose="allow", query="allow"),
        ),
        ActionSchema(
            schema_ref="action:run",
            semantic_key="run",
            intentional_required=False,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(ground="allow", compose="allow", query="allow"),
        ),
    ]
    fox = Referent(
        "referent:fox",
        identity_status=IdentityStatus.RESOLVED,
        type_refs=("type:fox",),
        context_refs=("actual", "story"),
    )
    proposition = Referent(
        "referent:proposition",
        identity_status=IdentityStatus.RESOLVED,
        type_refs=("type:proposition",),
        context_refs=("actual",),
    )
    commit(
        store,
        "patch:foundation",
        *(op(RecordKind.SCHEMA, item) for item in schemas),
        *(op(RecordKind.FACET_ENTITLEMENT, item) for item in entitlements),
        op(RecordKind.REFERENT, fox),
        op(RecordKind.REFERENT, proposition),
    )
    return store


def test_type_closure_is_deterministic_and_supports_multiple_inheritance() -> None:
    store = base_store()
    try:
        with store.snapshot() as snapshot:
            closure = TypeClosureCompiler(store).compile(
                "referent:fox", context_ref="actual", snapshot=snapshot
            )
        assert closure.type_refs == {
            "type:fox", "type:animal", "type:living", "type:physical",
            "type:agent", "type:referent",
        }
        assert closure.member("type:fox").depth == 0
        assert closure.member("type:referent").depth == 2
        assert closure.members == tuple(sorted(closure.members, key=lambda item: (item.depth, item.type_ref)))
    finally:
        store.close()


def test_opposed_child_type_never_propagates_supported_parent_membership() -> None:
    store = base_store()
    try:
        unknown = Referent(
            "referent:unknown",
            identity_status=IdentityStatus.PROVISIONAL,
            context_refs=("actual",),
        )
        supported = ReferentTypeAssertion(
            "assertion:fox:support", unknown.referent_ref, "type:fox", 1,
            AssertionStatus.SUPPORTED, 0.9, "actual",
        )
        opposed = replace(supported, assertion_ref="assertion:fox:oppose", status=AssertionStatus.OPPOSED)
        commit(store, "patch:type-conflict", op(RecordKind.REFERENT, unknown), op(RecordKind.TYPE_ASSERTION, supported), op(RecordKind.TYPE_ASSERTION, opposed))
        with store.snapshot() as snapshot:
            closure = TypeClosureCompiler(store).compile(
                unknown.referent_ref, context_ref="actual", snapshot=snapshot
            )
        assert "type:fox" in closure.contradicted_type_refs
        assert "type:fox" not in closure.type_refs
        assert "type:animal" not in closure.type_refs
    finally:
        store.close()


def test_required_optional_and_prohibited_entitlement_statuses() -> None:
    required = active_entitlement("entitlement:living:health", "type:living", "facet:health", EntitlementApplicability.REQUIRED)
    optional = active_entitlement("entitlement:animal:motion", "type:animal", "facet:motion", EntitlementApplicability.OPTIONAL)
    prohibited = active_entitlement("entitlement:proposition:health", "type:proposition", "facet:health", EntitlementApplicability.PROHIBITED)
    store = base_store(required, optional, prohibited)
    try:
        projector = ReferentKnowledgeProjector(store)
        fox_view = projector.project("referent:fox", context_ref="actual")
        proposition_view = projector.project("referent:proposition", context_ref="actual")
        assert fox_view.entitlement("facet:health").status == ProjectionStatus.UNKNOWN
        assert fox_view.entitlement("facet:motion").status == ProjectionStatus.LATENT
        assert proposition_view.entitlement("facet:health").status == ProjectionStatus.INAPPLICABLE
    finally:
        store.close()


def test_specific_override_defeats_inherited_prohibition() -> None:
    parent = active_entitlement("entitlement:living:health", "type:living", "facet:health", EntitlementApplicability.PROHIBITED)
    child = active_entitlement(
        "entitlement:fox:health", "type:fox", "facet:health",
        EntitlementApplicability.OPTIONAL,
        policy=EntitlementInheritancePolicy.OVERRIDE,
    )
    store = base_store(parent, child)
    try:
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        entitlement = view.entitlement("facet:health")
        assert entitlement.status == ProjectionStatus.LATENT
        assert entitlement.source_entitlement_refs == (child.entitlement_ref,)
    finally:
        store.close()


def test_unoverridden_inherited_prohibition_conflicts_with_license() -> None:
    parent = active_entitlement("entitlement:living:health", "type:living", "facet:health", EntitlementApplicability.PROHIBITED)
    child = active_entitlement("entitlement:fox:health", "type:fox", "facet:health", EntitlementApplicability.OPTIONAL)
    store = base_store(parent, child)
    try:
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        assert view.entitlement("facet:health").status == ProjectionStatus.CONTRADICTED
        assert "facet:facet:health" in view.unresolved_conflicts
    finally:
        store.close()


def test_context_and_temporal_constraints_block_without_mutating_state() -> None:
    entitlement = active_entitlement(
        "entitlement:fox:health", "type:fox", "facet:health",
        EntitlementApplicability.REQUIRED,
        contexts=("actual",), temporal=("condition:season",),
    )
    store = base_store(entitlement)
    try:
        evaluator = MappingConditionEvaluator({"condition:season": ConditionTruth.UNKNOWN})
        projector = ReferentKnowledgeProjector(store, condition_evaluator=evaluator)
        before = store.revision
        actual = projector.project("referent:fox", context_ref="actual")
        story = projector.project("referent:fox", context_ref="story")
        assert actual.entitlement("facet:health").status == ProjectionStatus.BLOCKED
        assert story.entitlement("facet:health").status == ProjectionStatus.INAPPLICABLE
        assert store.revision == before
        assert not store.repositories.state_assignments.all()
    finally:
        store.close()


def test_default_expectation_is_cycle_local_and_never_an_active_assignment() -> None:
    entitlement = active_entitlement(
        "entitlement:living:health", "type:living", "facet:health",
        EntitlementApplicability.REQUIRED, defaults=("default:healthy",),
    )
    store = base_store(entitlement)
    try:
        rule = DefaultRuleRecord(
            rule_ref="default:healthy",
            target_facet_ref="facet:health",
            expected_dimension_ref="state:health",
            expected_dimension_revision=1,
            expected_value_ref="state-value:healthy",
            expected_value_revision=1,
            holder_type_refs=("type:living",),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            confidence=0.7,
            evidence_refs=("foundation:default",),
        )
        commit(store, "patch:default", op(RecordKind.DEFAULT_RULE, rule))
        before = store.revision
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        health = next(item for item in view.state_applicability if item.dimension_ref == "state:health")
        assert health.status == ProjectionStatus.DEFAULT_EXPECTED
        assert health.active_value_refs == ()
        assert view.default_expectations[0].value_ref == "state-value:healthy"
        assert store.revision == before
        assert not store.repositories.state_assignments.all()
    finally:
        store.close()


def test_satisfied_defeater_suppresses_default() -> None:
    entitlement = active_entitlement(
        "entitlement:living:health", "type:living", "facet:health",
        EntitlementApplicability.REQUIRED, defaults=("default:healthy",),
    )
    store = base_store(entitlement)
    try:
        rule = DefaultRuleRecord(
            rule_ref="default:healthy",
            target_facet_ref="facet:health",
            expected_dimension_ref="state:health",
            expected_dimension_revision=1,
            expected_value_ref="state-value:healthy",
            expected_value_revision=1,
            holder_type_refs=("type:living",),
            defeater_refs=("condition:illness-evidence",),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        )
        commit(store, "patch:default", op(RecordKind.DEFAULT_RULE, rule))
        evaluator = MappingConditionEvaluator({"condition:illness-evidence": ConditionTruth.SATISFIED})
        view = ReferentKnowledgeProjector(store, condition_evaluator=evaluator).project(
            "referent:fox", context_ref="actual"
        )
        assert view.default_expectations == ()
        health = next(item for item in view.state_applicability if item.dimension_ref == "state:health")
        assert health.status == ProjectionStatus.UNKNOWN
    finally:
        store.close()


def test_active_and_exclusive_conflicting_state_assignments_project_correctly() -> None:
    entitlement = active_entitlement("entitlement:living:health", "type:living", "facet:health", EntitlementApplicability.REQUIRED)
    store = base_store(entitlement)
    try:
        healthy = StateAssignment(
            "assignment:healthy", "referent:fox", "state:health", 1,
            "state-value:healthy", 1, AssignmentStatus.ACTIVE, "actual", 0.9,
            evidence_refs=("evidence:healthy",),
        )
        commit(store, "patch:healthy", op(RecordKind.STATE_ASSIGNMENT, healthy))
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        health = next(item for item in view.state_applicability if item.dimension_ref == "state:health")
        assert health.status == ProjectionStatus.ACTIVE
        assert health.active_value_refs == ("state-value:healthy",)

        sick = replace(
            healthy,
            assignment_ref="assignment:sick",
            value_ref="state-value:sick",
            evidence_refs=("evidence:sick",),
        )
        commit(store, "patch:sick", op(RecordKind.STATE_ASSIGNMENT, sick))
        conflict = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        health = next(item for item in conflict.state_applicability if item.dimension_ref == "state:health")
        assert health.status == ProjectionStatus.CONTRADICTED
        assert health.active_value_refs == ("state-value:healthy", "state-value:sick")
    finally:
        store.close()


def test_terminated_state_is_historical_not_unknown() -> None:
    entitlement = active_entitlement("entitlement:living:health", "type:living", "facet:health", EntitlementApplicability.REQUIRED)
    store = base_store(entitlement)
    try:
        ended = StateAssignment(
            "assignment:ended", "referent:fox", "state:health", 1,
            "state-value:healthy", 1, AssignmentStatus.TERMINATED, "actual", 0.9,
            proof_refs=("proof:termination",),
        )
        commit(store, "patch:ended", op(RecordKind.STATE_ASSIGNMENT, ended))
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        health = next(item for item in view.state_applicability if item.dimension_ref == "state:health")
        assert health.status == ProjectionStatus.TERMINATED
        assert health.terminated_value_refs == ("state-value:healthy",)
    finally:
        store.close()


def test_capability_projection_distinguishes_blocked_and_contradicted() -> None:
    store = base_store()
    try:
        blocked = CapabilityInstance(
            "capability:fox:run:blocked", "referent:fox", "action:run", 1,
            CapabilityStatus.BLOCKED, 0.9, "actual",
            evidence_refs=("evidence:block",),
        )
        commit(store, "patch:blocked", op(RecordKind.CAPABILITY_INSTANCE, blocked))
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        assert view.live_capabilities[0].status == ProjectionStatus.BLOCKED

        available = replace(
            blocked,
            capability_ref="capability:fox:run:available",
            status=CapabilityStatus.AVAILABLE,
            evidence_refs=("evidence:adapter",),
        )
        commit(store, "patch:available", op(RecordKind.CAPABILITY_INSTANCE, available))
        conflict = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        assert conflict.live_capabilities[0].status == ProjectionStatus.CONTRADICTED
    finally:
        store.close()


def test_view_materialization_is_explicit_and_dependency_invalidated() -> None:
    entitlement = active_entitlement("entitlement:living:health", "type:living", "facet:health", EntitlementApplicability.REQUIRED)
    store = base_store(entitlement)
    try:
        projector = ReferentKnowledgeProjector(store)
        view = projector.project("referent:fox", context_ref="actual")
        assert store.repositories.materialized_views.all() == ()
        materialize = projector.materialization_patch(view)
        result = store.apply_patch(materialize)
        assert result.committed, result.errors
        view_ref = materialize.operations[0].target_ref
        assert store.repositories.materialized_views.valid(view_ref) is not None

        fox = store.repositories.referents.get("referent:fox").payload
        revised = replace(fox, revision=2, metadata={"observed": True})
        commit(store, "patch:fox-v2", op(RecordKind.REFERENT, revised))
        assert store.repositories.materialized_views.valid(view_ref) is None
    finally:
        store.close()


def test_projection_fingerprint_is_context_sensitive_and_stable() -> None:
    entitlement = active_entitlement("entitlement:living:health", "type:living", "facet:health", EntitlementApplicability.REQUIRED)
    store = base_store(entitlement)
    try:
        projector = ReferentKnowledgeProjector(store)
        first = projector.project("referent:fox", context_ref="actual")
        second = projector.project("referent:fox", context_ref="actual")
        story = projector.project("referent:fox", context_ref="story")
        assert first.fingerprint == second.fingerprint
        assert first.dependency_fingerprint == second.dependency_fingerprint
        assert first.fingerprint != story.fingerprint
    finally:
        store.close()


def test_direct_declared_type_opposition_is_not_silently_ignored() -> None:
    store = base_store()
    try:
        opposed = ReferentTypeAssertion(
            "assertion:declared-fox:oppose", "referent:fox", "type:fox", 1,
            AssertionStatus.OPPOSED, 0.9, "actual",
        )
        commit(store, "patch:oppose-declared", op(RecordKind.TYPE_ASSERTION, opposed))
        with store.snapshot() as snapshot:
            closure = TypeClosureCompiler(store).compile(
                "referent:fox", context_ref="actual", snapshot=snapshot
            )
        assert "type:fox" in closure.contradicted_type_refs
        assert "type:fox" not in closure.type_refs
        assert "type:animal" not in closure.type_refs
    finally:
        store.close()


def test_specific_prohibition_blocks_less_specific_license() -> None:
    parent = active_entitlement(
        "entitlement:living:health", "type:living", "facet:health",
        EntitlementApplicability.OPTIONAL,
    )
    child = active_entitlement(
        "entitlement:fox:health", "type:fox", "facet:health",
        EntitlementApplicability.PROHIBITED,
    )
    store = base_store(parent, child)
    try:
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        entitlement = view.entitlement("facet:health")
        assert entitlement.status == ProjectionStatus.INAPPLICABLE
        assert entitlement.source_entitlement_refs == (child.entitlement_ref,)
    finally:
        store.close()


def test_domain_narrowing_is_deterministic() -> None:
    parent = active_entitlement(
        "entitlement:living:health", "type:living", "facet:health",
        EntitlementApplicability.OPTIONAL,
        domains=("state-value:healthy", "state-value:sick"),
    )
    child = active_entitlement(
        "entitlement:fox:health", "type:fox", "facet:health",
        EntitlementApplicability.OPTIONAL,
        policy=EntitlementInheritancePolicy.NARROW_DOMAIN,
        domains=("state-value:healthy",),
    )
    store = base_store(parent, child)
    try:
        entitlement = ReferentKnowledgeProjector(store).project(
            "referent:fox", context_ref="actual"
        ).entitlement("facet:health")
        assert entitlement.value_domain_refs == ("state-value:healthy",)
    finally:
        store.close()


def test_ended_active_interval_projects_terminated_history() -> None:
    entitlement = active_entitlement(
        "entitlement:living:health", "type:living", "facet:health",
        EntitlementApplicability.REQUIRED,
    )
    store = base_store(entitlement)
    try:
        historical = StateAssignment(
            "assignment:historical", "referent:fox", "state:health", 1,
            "state-value:healthy", 1, AssignmentStatus.ACTIVE, "actual", 0.9,
            valid_from="2025-01-01T00:00:00+00:00",
            valid_to="2025-02-01T00:00:00+00:00",
            evidence_refs=("evidence:historical",),
        )
        commit(store, "patch:historical", op(RecordKind.STATE_ASSIGNMENT, historical))
        view = ReferentKnowledgeProjector(store).project(
            "referent:fox", context_ref="actual", at_time="2026-01-01T00:00:00+00:00"
        )
        health = next(item for item in view.state_applicability if item.dimension_ref == "state:health")
        assert health.status == ProjectionStatus.TERMINATED
        assert health.terminated_value_refs == ("state-value:healthy",)
    finally:
        store.close()


def test_new_active_default_revision_supersedes_immutable_prior_revision() -> None:
    entitlement = active_entitlement(
        "entitlement:living:health", "type:living", "facet:health",
        EntitlementApplicability.REQUIRED, defaults=("default:healthy",),
    )
    store = base_store(entitlement)
    try:
        first = DefaultRuleRecord(
            rule_ref="default:healthy",
            target_facet_ref="facet:health",
            expected_dimension_ref="state:health",
            expected_dimension_revision=1,
            expected_value_ref="state-value:healthy",
            expected_value_revision=1,
            holder_type_refs=("type:living",),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            revision=1,
        )
        commit(store, "patch:default-v1", op(RecordKind.DEFAULT_RULE, first))
        second = replace(
            first,
            revision=2,
            supersedes_revision=1,
            expected_value_ref="state-value:sick",
        )
        commit(store, "patch:default-v2", op(RecordKind.DEFAULT_RULE, second))
        assert store.repositories.default_rules.authoritative("default:healthy").revision == 2
        view = ReferentKnowledgeProjector(store).project("referent:fox", context_ref="actual")
        assert view.default_expectations[0].rule_revision == 2
        assert view.default_expectations[0].value_ref == "state-value:sick"
        assert len(store.repositories.default_rules.all(all_revisions=True)) == 2
    finally:
        store.close()


def test_store_condition_evaluator_respects_validity_time() -> None:
    entitlement = active_entitlement(
        "entitlement:living:health", "type:living", "facet:health",
        EntitlementApplicability.REQUIRED,
    )
    store = base_store(entitlement)
    try:
        assignment = StateAssignment(
            "assignment:time-bounded", "referent:fox", "state:health", 1,
            "state-value:healthy", 1, AssignmentStatus.ACTIVE, "actual", 0.9,
            valid_from="2026-01-01T00:00:00+00:00",
            valid_to="2026-02-01T00:00:00+00:00",
            evidence_refs=("evidence:time-bounded",),
        )
        commit(store, "patch:time-bounded", op(RecordKind.STATE_ASSIGNMENT, assignment))
        evaluator = StoreConditionEvaluator(store)
        with store.snapshot() as snapshot:
            active = evaluator.assess(
                assignment.assignment_ref,
                context_ref="actual",
                at_time="2026-01-15T00:00:00+00:00",
                snapshot=snapshot,
            )
            expired = evaluator.assess(
                assignment.assignment_ref,
                context_ref="actual",
                at_time="2026-03-01T00:00:00+00:00",
                snapshot=snapshot,
            )
        assert active.truth == ConditionTruth.SATISFIED
        assert expired.truth == ConditionTruth.UNKNOWN
    finally:
        store.close()


def test_referent_knowledge_view_excludes_unrelated_contextual_knowledge() -> None:
    store = base_store()
    try:
        property_schema = PropertySchema(
            schema_ref="property:tagged",
            semantic_key="tagged",
            local_ports=(
                LocalPortSchema(
                    "holder",
                    accepted_type_refs=("type:referent",),
                    cardinality=Cardinality(1, 1),
                ),
            ),
            holder_type_refs=("type:referent",),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(compose="allow", query="allow", ground="allow"),
        )
        proposition_type = ReferentTypeSchema(
            schema_ref="type:proposition-record",
            semantic_key="proposition-record",
            parent_links=(SchemaParentLink("type:referent"),),
            storage_kinds=frozenset({StorageKind.PROPOSITION}),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(mention="allow", ground="allow", compose="allow", query="allow"),
        )
        other = Referent(
            "referent:other",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:referent",),
            context_refs=("actual",),
        )
        relevant_application = SemanticApplication(
            "application:fox-tagged", property_schema.schema_ref, 1,
            (ApplicationBinding(
                "holder",
                (FillerRef(PortFillerClass.REFERENT, "referent:fox"),),
            ),),
            "actual",
            use_operation=UseOperation.COMPOSE,
        )
        unrelated_application = SemanticApplication(
            "application:other-tagged", property_schema.schema_ref, 1,
            (ApplicationBinding(
                "holder",
                (FillerRef(PortFillerClass.REFERENT, other.referent_ref),),
            ),),
            "actual",
            use_operation=UseOperation.COMPOSE,
        )
        relevant_proposition = PropositionReferent(
            Referent(
                "proposition:fox-tagged",
                storage_kind=StorageKind.PROPOSITION,
                identity_status=IdentityStatus.RESOLVED,
                type_refs=(proposition_type.schema_ref,),
                context_refs=("actual",),
            ),
            (FillerRef(PortFillerClass.SEMANTIC_APPLICATION, relevant_application.application_ref),),
            "actual",
        )
        unrelated_proposition = PropositionReferent(
            Referent(
                "proposition:other-tagged",
                storage_kind=StorageKind.PROPOSITION,
                identity_status=IdentityStatus.RESOLVED,
                type_refs=(proposition_type.schema_ref,),
                context_refs=("actual",),
            ),
            (FillerRef(PortFillerClass.SEMANTIC_APPLICATION, unrelated_application.application_ref),),
            "actual",
        )
        evidence = EvidenceRecord(
            "evidence:knowledge", "source:test", 1.0, "lineage:test",
            context_ref="actual",
        )
        relevant_knowledge = KnowledgeRecord(
            "knowledge:fox-tagged", relevant_proposition.proposition_ref,
            KnowledgeStatus.SUPPORTED, 0.9, "actual", ("source:test",),
            (evidence.evidence_ref,),
        )
        unrelated_knowledge = KnowledgeRecord(
            "knowledge:other-tagged", unrelated_proposition.proposition_ref,
            KnowledgeStatus.SUPPORTED, 0.9, "actual", ("source:test",),
            (evidence.evidence_ref,),
        )
        commit(
            store,
            "patch:knowledge-relevance",
            op(RecordKind.SCHEMA, property_schema),
            op(RecordKind.SCHEMA, proposition_type),
            op(RecordKind.REFERENT, other),
            op(RecordKind.SEMANTIC_APPLICATION, relevant_application),
            op(RecordKind.SEMANTIC_APPLICATION, unrelated_application),
            op(RecordKind.REFERENT, relevant_proposition.referent),
            op(RecordKind.REFERENT, unrelated_proposition.referent),
            op(RecordKind.PROPOSITION, relevant_proposition),
            op(RecordKind.PROPOSITION, unrelated_proposition),
            op(RecordKind.EVIDENCE, evidence),
            op(RecordKind.KNOWLEDGE, relevant_knowledge),
            op(RecordKind.KNOWLEDGE, unrelated_knowledge),
        )
        view = ReferentKnowledgeProjector(store).project(
            "referent:fox", context_ref="actual"
        )
        assert "knowledge:fox-tagged" in view.epistemic_record_refs
        assert "knowledge:other-tagged" not in view.epistemic_record_refs
        assert "knowledge:other-tagged" not in view.dependency_refs
    finally:
        store.close()
