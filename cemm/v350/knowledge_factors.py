"""Bridge Stage-4 referent knowledge projections into the Stage-5 factor graph.

The base Phase-9 builder already enforces lexical/schema/port/grounding constraints.
This binder adds the missing cross-stage applicability constraint without teaching
the kernel domain names: it uses only exact schema holder constraints, facet refs,
and projected entitlement/state applicability.
"""
from __future__ import annotations

from dataclasses import replace
from itertools import product
from typing import Mapping

from .composition.model import (
    MeaningFactor,
    MeaningFactorGraph,
    MeaningFactorKind,
    MeaningVariableKind,
)
from .facets.model import ProjectionStatus, ReferentKnowledgeView
from .schema.model import (
    PropertySchema,
    StateDimensionSchema,
    semantic_fingerprint,
)


class ReferentKnowledgeFactorBinder:
    def __init__(self, store) -> None:
        self.store = store

    def bind(
        self,
        graph: MeaningFactorGraph,
        *,
        lattice,
        projections: Mapping[str, ReferentKnowledgeView],
        snapshot,
    ) -> MeaningFactorGraph:
        if not projections:
            return replace(
                graph,
                metadata={**dict(graph.metadata), "stage4_projection_binding": "no_durable_projection"},
            )

        forms = {item.candidate_ref: item for item in lattice.form_candidates}
        variables = {item.variable_ref: item for item in graph.variables}
        referent_vars = tuple(
            item for item in graph.variables if item.variable_kind == MeaningVariableKind.REFERENT
        )
        schema_vars = tuple(
            item for item in graph.variables if item.variable_kind == MeaningVariableKind.SCHEMA
        )
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        extra: list[MeaningFactor] = []
        projection_fps: set[str] = set()

        for schema_var in schema_vars:
            form_ref = str(schema_var.metadata.get("form_candidate_ref", ""))
            form = forms.get(form_ref)
            if form is None:
                continue
            for referent_var in referent_vars:
                span = tuple(referent_var.metadata.get("span", ()))
                if span != (form.span.start, form.span.end):
                    continue

                allowed: list[tuple[str, str]] = []
                all_pairs = 0
                used_projection = False
                for schema_value, referent_value in product(schema_var.values, referent_var.values):
                    all_pairs += 1
                    target_ref = str(referent_value.metadata.get("target_ref", ""))
                    view = projections.get(target_ref)
                    if view is None:
                        # Provisional/non-durable referents remain possible. Missing
                        # projection is uncertainty, never proof of incompatibility.
                        allowed.append((schema_value.value_ref, referent_value.value_ref))
                        continue
                    used_projection = True
                    projection_fps.add(view.dependency_fingerprint)
                    if self._compatible(schema_value.metadata, view, registry):
                        allowed.append((schema_value.value_ref, referent_value.value_ref))

                if not used_projection or len(allowed) == all_pairs:
                    continue
                if not allowed:
                    # An impossible cross product should not create an invalid empty
                    # hard factor; retain the original graph and expose the conflict
                    # as unresolved so the solver cannot fabricate compatibility.
                    unresolved = tuple(
                        sorted(
                            set(graph.unresolved_refs)
                            | {f"stage4-compatibility:{schema_var.variable_ref}:{referent_var.variable_ref}"}
                        )
                    )
                    graph = replace(graph, unresolved_refs=unresolved)
                    continue

                factor_ref = "factor:stage4-knowledge:" + semantic_fingerprint(
                    "stage4-knowledge-factor",
                    (
                        graph.graph_ref,
                        schema_var.variable_ref,
                        referent_var.variable_ref,
                        tuple(sorted(allowed)),
                    ),
                    24,
                )
                extra.append(
                    MeaningFactor(
                        factor_ref=factor_ref,
                        factor_kind=MeaningFactorKind.TYPE_ENTITLEMENT,
                        variable_refs=(schema_var.variable_ref, referent_var.variable_ref),
                        hard=True,
                        allowed_value_tuples=tuple(sorted(allowed)),
                        evidence_refs=graph.evidence_refs,
                        reason=(
                            "Stage-4 referent type/facet applicability constrains "
                            "Stage-5 schema/referent compatibility"
                        ),
                        metadata={
                            "authority": "referent_knowledge_projection",
                            "projection_dependency_fingerprints": tuple(sorted(projection_fps)),
                        },
                    )
                )

        return replace(
            graph,
            factors=tuple((*graph.factors, *extra)),
            metadata={
                **dict(graph.metadata),
                "stage4_projection_binding": "applied",
                "stage4_projection_count": len(projections),
                "stage4_projection_dependency_fingerprints": tuple(sorted(projection_fps)),
                "stage4_factor_count": len(extra),
            },
        )

    @staticmethod
    def _compatible(schema_metadata, view: ReferentKnowledgeView, registry) -> bool:
        schema_ref = schema_metadata.get("schema_ref")
        revision = schema_metadata.get("target_revision") or schema_metadata.get("schema_revision")
        if not schema_ref or not revision:
            return True
        try:
            schema = registry.schema(str(schema_ref), int(revision))
        except (KeyError, TypeError, ValueError):
            return False

        holder_types = tuple(getattr(schema, "holder_type_refs", ()) or ())
        if holder_types and not set(holder_types).intersection(view.type_closure.type_refs):
            return False

        if isinstance(schema, StateDimensionSchema):
            state = next(
                (
                    item
                    for item in view.state_applicability
                    if item.dimension_ref == schema.schema_ref
                    and item.dimension_revision == schema.revision
                ),
                None,
            )
            if state is not None and state.status == ProjectionStatus.INAPPLICABLE:
                return False

        if isinstance(schema, PropertySchema):
            facet_ref = str(schema.metadata.get("facet_ref") or schema.schema_ref)
            entitlement = view.entitlement(facet_ref)
            if entitlement is not None and entitlement.status == ProjectionStatus.INAPPLICABLE:
                return False

        return True
