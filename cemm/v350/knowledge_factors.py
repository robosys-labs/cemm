"""Bind Stage-4 referent knowledge to Stage-5 semantic ports and plans.

The bridge is graph/port based. Surface span equality is never semantic authority.
Candidate generation comes from Stage-4 SemanticClosureCandidate records; this
binder enforces that selected port fillers remain compatible with the grounded
referent knowledge view.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from .composition.model import (
    MeaningFactor,
    MeaningFactorGraph,
    MeaningFactorKind,
    MeaningVariableKind,
)
from .facets.closure import SemanticClosureCandidate
from .facets.model import ProjectionStatus, ReferentKnowledgeView
from .schema.model import PropertySchema, StateDimensionSchema, semantic_fingerprint


class ReferentKnowledgeFactorBinder:
    def __init__(self, store) -> None:
        self.store = store

    def bind(
        self,
        graph: MeaningFactorGraph,
        *,
        grounding,
        projections: Mapping[str, ReferentKnowledgeView],
        closure_candidates: tuple[SemanticClosureCandidate, ...],
        snapshot,
    ) -> MeaningFactorGraph:
        if not projections:
            return replace(
                graph,
                metadata={
                    **dict(graph.metadata),
                    "stage4_projection_binding": "no_durable_projection",
                },
            )

        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        candidate_by_ref = {
            item.candidate_ref: item for item in grounding.candidates
        }
        closure_pins = {
            (item.referent_ref, item.schema_ref, item.schema_revision)
            for item in closure_candidates
            if item.usable_for_composition
        }
        extra: list[MeaningFactor] = []
        unresolved = set(graph.unresolved_refs)
        projection_fps = {
            view.dependency_fingerprint
            for view in projections.values()
            if view.dependency_fingerprint
        }

        for port_var in (
            item
            for item in graph.variables
            if item.variable_kind == MeaningVariableKind.PORT_FILLER
        ):
            schema_ref = str(port_var.metadata.get("schema_ref") or "")
            schema_revision = port_var.metadata.get("schema_revision")
            if not schema_ref or schema_revision is None:
                continue
            try:
                schema = registry.schema(schema_ref, int(schema_revision))
            except Exception:
                unresolved.add(f"stage4-schema:{schema_ref}@{schema_revision}")
                continue

            allowed: list[tuple[str]] = []
            constrained = False
            for value in port_var.values:
                if value.metadata.get("inactive") or value.value_ref in {
                    "choice:inactive",
                    "choice:gap",
                    "choice:omitted",
                }:
                    allowed.append((value.value_ref,))
                    continue
                candidate_refs = tuple(
                    map(str, value.metadata.get("candidate_refs", ()))
                )
                if not candidate_refs:
                    allowed.append((value.value_ref,))
                    continue

                compatible = True
                for candidate_ref in candidate_refs:
                    candidate = candidate_by_ref.get(candidate_ref)
                    if candidate is None:
                        compatible = False
                        break
                    view = projections.get(candidate.target_ref)
                    if view is None:
                        # Provisional/non-durable referents remain possible.
                        continue
                    constrained = True
                    if not self._compatible_schema(schema, view):
                        compatible = False
                        break
                    if closure_candidates and (
                        view.referent_ref,
                        schema.schema_ref,
                        schema.revision,
                    ) not in closure_pins:
                        active_schema_refs = {
                            item.schema_ref
                            for item in (
                                *view.property_applications,
                                *view.relation_applications,
                                *view.role_applications,
                                *view.function_applications,
                            )
                        }
                        if schema.schema_ref not in active_schema_refs:
                            compatible = False
                            break
                if compatible:
                    allowed.append((value.value_ref,))

            if not constrained:
                continue
            if not allowed:
                unresolved.add(
                    f"stage4-port-compatibility:{port_var.variable_ref}"
                )
                continue

            extra.append(
                MeaningFactor(
                    factor_ref="factor:stage4-port-knowledge:"
                    + semantic_fingerprint(
                        "stage4-port-knowledge",
                        (
                            graph.graph_ref,
                            port_var.variable_ref,
                            schema.schema_ref,
                            schema.revision,
                            tuple(allowed),
                        ),
                        24,
                    ),
                    factor_kind=MeaningFactorKind.TYPE_ENTITLEMENT,
                    variable_refs=(port_var.variable_ref,),
                    hard=True,
                    allowed_value_tuples=tuple(sorted(set(allowed))),
                    evidence_refs=tuple(
                        sorted({*graph.evidence_refs, *projection_fps})
                    ),
                    reason=(
                        "Stage-4 referent knowledge constrains exact semantic "
                        "port fillers"
                    ),
                    metadata={
                        "authority": "referent_knowledge_projection",
                        "schema_ref": schema.schema_ref,
                        "schema_revision": schema.revision,
                        "projection_dependency_fingerprints": tuple(
                            sorted(projection_fps)
                        ),
                    },
                )
            )

        return replace(
            graph,
            factors=tuple((*graph.factors, *extra)),
            unresolved_refs=tuple(sorted(unresolved)),
            metadata={
                **dict(graph.metadata),
                "stage4_projection_binding": "graph_port_based",
                "stage4_projection_count": len(projections),
                "stage4_closure_candidate_count": len(closure_candidates),
                "stage4_projection_dependency_fingerprints": tuple(
                    sorted(projection_fps)
                ),
                "stage4_factor_count": len(extra),
                "surface_span_semantic_authority": False,
            },
        )

    @staticmethod
    def _compatible_schema(schema, view: ReferentKnowledgeView) -> bool:
        holder_types = tuple(getattr(schema, "holder_type_refs", ()) or ())
        if holder_types and not set(holder_types).intersection(
            view.type_closure.type_refs
        ):
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
            if (
                state is not None
                and state.status == ProjectionStatus.INAPPLICABLE
            ):
                return False

        if isinstance(schema, PropertySchema):
            facet_ref = str(
                schema.metadata.get("facet_ref") or schema.schema_ref
            )
            entitlement = view.entitlement(facet_ref)
            if (
                entitlement is not None
                and entitlement.status == ProjectionStatus.INAPPLICABLE
            ):
                return False

        return True
