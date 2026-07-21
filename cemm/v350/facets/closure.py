"""Compile Stage-4 referent knowledge into explicit semantic-closure candidates.

The closure compiler is read-only. It exposes which reviewed schemas are
structurally applicable to a referent so Stage 5 can build a bounded candidate
domain from type/facet/state/capability knowledge rather than surface-span
coincidence. Defaults remain expectations, never facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..schema.model import SchemaClass, UseOperation, semantic_fingerprint
from .model import ProjectionStatus, ReferentKnowledgeView


@dataclass(frozen=True, slots=True)
class SemanticClosureCandidate:
    candidate_ref: str
    referent_ref: str
    schema_ref: str
    schema_revision: int
    schema_class: SchemaClass
    projection_status: ProjectionStatus
    source_kind: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence: float = 1.0

    @property
    def usable_for_composition(self) -> bool:
        return self.projection_status not in {
            ProjectionStatus.INAPPLICABLE,
            ProjectionStatus.BLOCKED,
            ProjectionStatus.CONTRADICTED,
            ProjectionStatus.TERMINATED,
        }


class ReferentKnowledgeClosureCompiler:
    def __init__(self, store) -> None:
        self.store = store

    def compile(
        self,
        projections: Mapping[str, ReferentKnowledgeView],
        *,
        snapshot,
    ) -> tuple[SemanticClosureCandidate, ...]:
        self.store.assert_snapshot(snapshot)
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        result: dict[tuple[str, str, int, str], SemanticClosureCandidate] = {}

        def add(
            view,
            schema_ref,
            revision,
            status,
            source_kind,
            source_refs,
            confidence=1.0,
        ):
            try:
                schema = registry.schema(schema_ref, revision)
            except Exception:
                return
            if not schema.use_profile.permits(
                UseOperation.COMPOSE, provisional=True
            ):
                return
            key = (
                view.referent_ref,
                schema.schema_ref,
                schema.revision,
                source_kind,
            )
            evidence = tuple(sorted(set((*view.dependency_refs, *source_refs))))
            result[key] = SemanticClosureCandidate(
                candidate_ref="semantic-closure:"
                + semantic_fingerprint(
                    "semantic-closure",
                    (
                        view.referent_ref,
                        schema.schema_ref,
                        schema.revision,
                        status.value,
                        source_kind,
                        tuple(source_refs),
                    ),
                    24,
                ),
                referent_ref=view.referent_ref,
                schema_ref=schema.schema_ref,
                schema_revision=schema.revision,
                schema_class=schema.schema_class,
                projection_status=status,
                source_kind=source_kind,
                source_refs=tuple(source_refs),
                evidence_refs=evidence or (view.dependency_fingerprint,),
                confidence=confidence,
            )

        for view in projections.values():
            # Structural property applicability is referent-driven, not a global
            # answer catalogue. A PropertySchema's holder-type contract licenses a
            # latent composition candidate; it does not assert that the referent
            # currently has a value for that property.
            type_refs = set(view.type_closure.type_refs)
            for schema in registry.active_schemas(SchemaClass.PROPERTY):
                holder_types = set(getattr(schema, "holder_type_refs", ()))
                if holder_types and not holder_types.intersection(type_refs):
                    continue
                add(
                    view,
                    schema.schema_ref,
                    schema.revision,
                    ProjectionStatus.LATENT,
                    "property_applicability",
                    (
                        schema.schema_ref,
                        *tuple(sorted(holder_types.intersection(type_refs))),
                    ),
                )
            for application in (
                *view.property_applications,
                *view.relation_applications,
                *view.role_applications,
                *view.function_applications,
            ):
                add(
                    view,
                    application.schema_ref,
                    application.schema_revision,
                    ProjectionStatus.ACTIVE,
                    "active_application",
                    (application.application_ref,),
                    application.confidence,
                )

            for state in view.state_applicability:
                try:
                    dimension = registry.schema(state.dimension_ref, state.dimension_revision)
                except KeyError:
                    continue
                if bool(dimension.metadata.get("requires_applicability_evidence")) and not state.assignment_refs and not state.active_value_refs:
                    continue
                add(
                    view, state.dimension_ref, state.dimension_revision, state.status,
                    "state_applicability", (*state.assignment_refs, *state.dependency_refs),
                )

            for action_ref in view.afforded_action_refs:
                schema = registry.maybe_authoritative_schema(action_ref)
                if schema is not None:
                    add(
                        view,
                        schema.schema_ref,
                        schema.revision,
                        ProjectionStatus.LATENT,
                        "action_affordance",
                        (action_ref,),
                    )

            for capability in view.live_capabilities:
                add(
                    view,
                    capability.action_schema_ref,
                    capability.action_schema_revision,
                    capability.status,
                    "live_capability",
                    (*capability.capability_refs, *capability.dependency_refs),
                    capability.confidence,
                )

            for entitlement in view.facet_entitlements:
                if entitlement.status in {
                    ProjectionStatus.INAPPLICABLE,
                    ProjectionStatus.BLOCKED,
                    ProjectionStatus.CONTRADICTED,
                }:
                    continue
                for value_ref in entitlement.value_domain_refs:
                    schema = registry.maybe_authoritative_schema(value_ref)
                    if schema is None:
                        continue
                    add(
                        view,
                        schema.schema_ref,
                        schema.revision,
                        ProjectionStatus.LATENT,
                        "facet_entitlement",
                        (
                            *entitlement.source_entitlement_refs,
                            *entitlement.dependency_refs,
                        ),
                        entitlement.confidence,
                    )

        return tuple(
            sorted(
                result.values(),
                key=lambda item: (
                    item.referent_ref,
                    item.schema_class.value,
                    item.schema_ref,
                    item.schema_revision,
                    item.source_kind,
                ),
            )
        )
