"""Cycle-pinned referent knowledge projection and optional cache materialization."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from ..schema.model import (
    ActionSchema,
    FunctionSchema,
    PropertySchema,
    RelationSchema,
    RoleSchema,
    SchemaClass,
    StateDimensionSchema,
    canonical_data,
    semantic_fingerprint,
)
from ..storage.codec import encode_record
from ..storage.model import (
    GraphPatch,
    MaterializedViewRecord,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
    StoreSnapshot,
)
from ..uol.model import CapabilityStatus, SemanticApplication
from .conditions import ConditionEvaluator
from .engine import (
    DefaultExpectationProjector,
    FacetEntitlementProjector,
    StateApplicabilityAssessor,
    TypeClosureCompiler,
)
from .model import (
    CapabilityProjection,
    ProjectionStatus,
    ReferentKnowledgeView,
)


class ReferentKnowledgeProjector:
    """Build the universal referent envelope from canonical records.

    The projector is read-only.  Call :meth:`materialization_patch` explicitly
    when a caller wants to cache a view through the ordinary GraphPatch commit
    boundary.
    """

    def __init__(self, store, *, condition_evaluator: ConditionEvaluator | None = None) -> None:
        self._store = store
        self.type_closure = TypeClosureCompiler(store)
        self.entitlements = FacetEntitlementProjector(
            store, condition_evaluator=condition_evaluator
        )
        self.defaults = DefaultExpectationProjector(
            store, condition_evaluator=condition_evaluator
        )
        self.state_applicability = StateApplicabilityAssessor(store)

    def project(
        self,
        referent_ref: str,
        *,
        context_ref: str,
        at_time: str | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> ReferentKnowledgeView:
        if snapshot is None:
            with self._store.snapshot() as pinned:
                return self._project(
                    referent_ref,
                    context_ref=context_ref,
                    at_time=at_time,
                    snapshot=pinned,
                )
        self._store.assert_snapshot(snapshot)
        return self._project(
            referent_ref,
            context_ref=context_ref,
            at_time=at_time,
            snapshot=snapshot,
        )

    def _project(
        self,
        referent_ref: str,
        *,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> ReferentKnowledgeView:
        stored_referent = self._store.repositories.referents.get(
            referent_ref, snapshot=snapshot
        )
        if stored_referent is None:
            raise KeyError(referent_ref)
        referent = stored_referent.payload
        closure = self.type_closure.compile(
            referent_ref,
            context_ref=context_ref,
            at_time=at_time,
            snapshot=snapshot,
        )
        entitlements = self.entitlements.project(
            closure,
            context_ref=context_ref,
            at_time=at_time,
            snapshot=snapshot,
        )
        defaults = self.defaults.project(
            referent_ref,
            closure,
            entitlements,
            context_ref=context_ref,
            at_time=at_time,
            snapshot=snapshot,
        )

        registry = self._store.repositories.schemas.registry(snapshot=snapshot)
        applications = self._store.repositories.applications.involving(
            referent_ref,
            context_ref=context_ref,
            snapshot=snapshot,
        )
        by_class: dict[SchemaClass, list[SemanticApplication]] = defaultdict(list)
        unresolved_application_refs: list[str] = []
        for application in applications:
            try:
                schema = registry.schema(application.schema_ref, application.schema_revision)
            except KeyError:
                unresolved_application_refs.append(application.application_ref)
                continue
            by_class[schema.schema_class].append(application)

        dimensions: dict[tuple[str, int], StateDimensionSchema] = {}
        for item in registry.iter_schemas():
            if isinstance(item, StateDimensionSchema):
                facet_ref = str(item.metadata.get("facet_ref") or item.schema_ref)
                if item.holder_type_refs and not closure.type_refs.intersection(item.holder_type_refs):
                    continue
                if any(ent.facet_ref in {facet_ref, item.schema_ref} for ent in entitlements):
                    dimensions[(item.schema_ref, item.revision)] = item
        for stored_assignment in self._store.repositories.state_assignments.all(snapshot=snapshot):
            assignment = stored_assignment.payload
            if assignment.holder_ref == referent_ref and assignment.context_ref in {"global", context_ref}:
                try:
                    schema = registry.schema(assignment.dimension_ref, assignment.dimension_revision)
                except KeyError:
                    continue
                if isinstance(schema, StateDimensionSchema):
                    dimensions[(schema.schema_ref, schema.revision)] = schema
        for expectation in defaults:
            if expectation.dimension_ref is None or expectation.dimension_revision is None:
                continue
            try:
                schema = registry.schema(expectation.dimension_ref, expectation.dimension_revision)
            except KeyError:
                continue
            if isinstance(schema, StateDimensionSchema):
                dimensions[(schema.schema_ref, schema.revision)] = schema

        state_results = tuple(
            self.state_applicability.assess(
                referent_ref,
                dimension.schema_ref,
                dimension.revision,
                closure,
                entitlements,
                defaults,
                context_ref=context_ref,
                at_time=at_time,
                snapshot=snapshot,
            )
            for _, dimension in sorted(dimensions.items())
        )
        state_timelines = {
            item.dimension_ref: item.assignment_refs for item in state_results
        }

        capabilities = self._capability_projections(
            referent_ref,
            context_ref=context_ref,
            at_time=at_time,
            snapshot=snapshot,
        )
        events = self._store.repositories.event_state.events(
            referent_ref, context_ref=context_ref, snapshot=snapshot
        )
        identity_facets = self._store.repositories.referents.identity_facets(
            referent_ref, context_ref=context_ref, snapshot=snapshot
        )
        impacts = tuple(
            stored.payload
            for stored in self._store.repositories.impact_assessments.all(snapshot=snapshot)
            if stored.payload.context_ref == context_ref
            and referent_ref in {
                stored.payload.affected_ref,
                stored.payload.stakeholder_ref,
                stored.payload.source_event_or_state_ref,
            }
        )
        importance = tuple(
            stored.payload
            for stored in self._store.repositories.importance_assessments.all(snapshot=snapshot)
            if stored.payload.context_ref == context_ref
            and referent_ref in {stored.payload.subject_ref, stored.payload.stakeholder_ref}
        )
        application_refs = {item.application_ref for item in applications}
        propositions = tuple(
            stored.payload
            for stored in self._store.repositories.propositions.all(snapshot=snapshot)
            if stored.payload.context_ref in {"global", context_ref}
            and any(
                getattr(content, "ref", None) in application_refs
                for content in stored.payload.content_refs
            )
        )
        proposition_refs = {item.proposition_ref for item in propositions}
        knowledge = tuple(
            stored.payload
            for stored in self._store.repositories.knowledge.all(snapshot=snapshot)
            if stored.payload.context_ref in {"global", context_ref}
            and stored.payload.proposition_ref in proposition_refs
        )
        claim_records = tuple(
            stored.payload
            for stored in self._store.repositories.claim_records.all(snapshot=snapshot)
            if stored.payload.proposition_ref in proposition_refs
            and stored.payload.source_context_ref in {"global", context_ref}
        )

        conflicts: list[str] = []
        conflicts.extend(f"type:{ref}" for ref in closure.contradicted_type_refs)
        conflicts.extend(
            f"facet:{item.facet_ref}"
            for item in entitlements
            if item.status == ProjectionStatus.CONTRADICTED
        )
        conflicts.extend(
            f"state:{item.dimension_ref}"
            for item in state_results
            if item.status == ProjectionStatus.CONTRADICTED
        )
        conflicts.extend(f"application:{ref}" for ref in unresolved_application_refs)

        dependencies = {
            referent_ref,
            *closure.dependency_refs,
            *(ref for item in entitlements for ref in item.dependency_refs),
            *(item.rule_ref for item in defaults),
            *(ref for item in state_results for ref in item.dependency_refs),
            *(item.capability_ref for group in capabilities for item in self._capability_instances(group, referent_ref, context_ref, at_time, snapshot)),
            *(item.application_ref for item in applications),
            *(item.event_ref for item in events),
            *(item.identity_facet_ref for item in identity_facets),
            *(item.assessment_ref for item in impacts),
            *(item.assessment_ref for item in importance),
            *(item.proposition_ref for item in propositions),
            *(item.knowledge_ref for item in knowledge),
            *(item.claim_record_ref for item in claim_records),
        }
        dependencies.discard("")

        return ReferentKnowledgeView(
            referent_ref=referent_ref,
            referent_revision=referent.revision,
            context_ref=context_ref,
            at_time=at_time,
            snapshot_revision=snapshot.store_revision,
            type_closure=closure,
            identity_facet_refs=tuple(sorted(item.identity_facet_ref for item in identity_facets)),
            facet_entitlements=entitlements,
            property_applications=tuple(sorted(by_class[SchemaClass.PROPERTY], key=lambda item: item.application_ref)),
            state_timelines=state_timelines,
            state_applicability=state_results,
            relation_applications=tuple(sorted(by_class[SchemaClass.RELATION], key=lambda item: item.application_ref)),
            role_applications=tuple(sorted(by_class[SchemaClass.ROLE], key=lambda item: item.application_ref)),
            event_refs=tuple(sorted(item.event_ref for item in events)),
            afforded_action_refs=tuple(sorted({
                application.schema_ref for application in by_class[SchemaClass.ACTION]
            })),
            live_capabilities=capabilities,
            function_applications=tuple(sorted(by_class[SchemaClass.FUNCTION], key=lambda item: item.application_ref)),
            resource_applications=tuple(sorted(
                (
                    application for application in applications
                    if str(application.metadata.get("facet_family", "")) == "resource"
                ),
                key=lambda item: item.application_ref,
            )),
            significance_assessment_refs=tuple(sorted({
                *(item.assessment_ref for item in impacts),
                *(item.assessment_ref for item in importance),
            })),
            epistemic_record_refs=tuple(sorted({
                *(item.knowledge_ref for item in knowledge),
                *(item.claim_record_ref for item in claim_records),
            })),
            default_expectations=defaults,
            unresolved_conflicts=tuple(sorted(set(conflicts))),
            dependency_refs=tuple(sorted(dependencies)),
            dependency_fingerprint=self._store.dependency_fingerprint(dependencies, snapshot=snapshot),
            metadata={
                "boot_fingerprint": snapshot.boot_fingerprint,
                "overlay_fingerprint": snapshot.overlay_fingerprint,
            },
        )

    def materialization_patch(
        self,
        view: ReferentKnowledgeView,
        *,
        source_ref: str = "runtime:referent_knowledge_projector",
        permission_ref: str = "internal",
    ) -> GraphPatch:
        view_ref = semantic_fingerprint(
            "referent-knowledge-view-ref",
            (view.referent_ref, view.context_ref, view.at_time),
            48,
        )
        current = self._store.get_record(RecordKind.MATERIALIZED_VIEW, view_ref)
        revision = 1 if current is None else current.revision + 1
        record = MaterializedViewRecord(
            view_ref=view_ref,
            view_kind="referent_knowledge_view",
            subject_ref=view.referent_ref,
            context_ref=view.context_ref,
            payload=canonical_data(view),
            dependency_refs=view.dependency_refs,
            dependency_fingerprint=view.dependency_fingerprint,
            snapshot_revision=view.snapshot_revision,
        )
        dependencies = tuple(
            RecordDependency(None, ref, dependency_kind="referent_knowledge_projection")
            for ref in view.dependency_refs
        )
        operation = PatchOperation(
            operation_ref=f"operation:materialize:{view_ref}:{revision}",
            operation_kind=PatchOperationKind.MATERIALIZE,
            record_kind=RecordKind.MATERIALIZED_VIEW,
            target_ref=view_ref,
            record_revision=revision,
            payload=encode_record(RecordKind.MATERIALIZED_VIEW, record),
            expected_record_revision=None if current is None else current.revision,
            expected_record_fingerprint=None if current is None else current.record_fingerprint,
            dependencies=dependencies,
            reason="cache cycle-pinned referent knowledge projection",
        )
        return GraphPatch(
            patch_ref=f"patch:materialize:{view_ref}:{revision}",
            context_ref=view.context_ref,
            scope_ref=view.context_ref,
            source_ref=source_ref,
            permission_ref=permission_ref,
            operations=(operation,),
            expected_store_revision=self._store.revision,
            validation_requirements=("dependency_fingerprint_current", "view_is_derived_only"),
            rollback_hint="invalidate the materialized view",
        )

    def _capability_projections(
        self,
        referent_ref: str,
        *,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> tuple[CapabilityProjection, ...]:
        grouped: dict[tuple[str, int], list] = defaultdict(list)
        for item in self._store.repositories.event_state.capabilities(
            referent_ref, context_ref=context_ref, at_time=at_time, snapshot=snapshot
        ):
            grouped[(item.action_schema_ref, item.action_schema_revision)].append(item)
        result = []
        for (action_ref, revision), items in sorted(grouped.items()):
            statuses = {item.status for item in items}
            if CapabilityStatus.AVAILABLE in statuses:
                status = ProjectionStatus.ACTIVE
            elif CapabilityStatus.BLOCKED in statuses or CapabilityStatus.UNAVAILABLE in statuses:
                status = ProjectionStatus.BLOCKED
            elif CapabilityStatus.TERMINATED in statuses:
                status = ProjectionStatus.TERMINATED
            elif CapabilityStatus.CONDITIONAL in statuses or CapabilityStatus.DEGRADED in statuses:
                status = ProjectionStatus.LATENT
            else:
                status = ProjectionStatus.UNKNOWN
            if (
                CapabilityStatus.AVAILABLE in statuses
                and statuses.intersection({CapabilityStatus.BLOCKED, CapabilityStatus.UNAVAILABLE})
            ):
                status = ProjectionStatus.CONTRADICTED
            dependencies = {
                action_ref,
                *(item.capability_ref for item in items),
                *(ref for item in items for ref in item.dependency_refs),
            }
            result.append(CapabilityProjection(
                action_schema_ref=action_ref,
                action_schema_revision=revision,
                status=status,
                capability_statuses=tuple(sorted(statuses, key=lambda value: value.value)),
                capability_refs=tuple(sorted(item.capability_ref for item in items)),
                dependency_refs=tuple(sorted(dependencies)),
                confidence=min(item.confidence for item in items),
                reasons=("conflicting_capability_observations",) if status == ProjectionStatus.CONTRADICTED else (),
            ))
        return tuple(result)

    def _capability_instances(
        self,
        projection: CapabilityProjection,
        referent_ref: str,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ):
        refs = set(projection.capability_refs)
        return tuple(
            item for item in self._store.repositories.event_state.capabilities(
                referent_ref, context_ref=context_ref, at_time=at_time, snapshot=snapshot
            )
            if item.capability_ref in refs
        )
