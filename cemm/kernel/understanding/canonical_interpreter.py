"""Interpretation resolver that carries grounded fillers and context kind."""
from __future__ import annotations

from dataclasses import dataclass, fields

from .interpreter import InterpretationResolver, SelectedInterpretation
from ..model.role_binding import RoleBinding


@dataclass(frozen=True, slots=True)
class CanonicalSelectedInterpretation:
    id: str
    predication_ref: str = ""
    proposition_ref: str = ""
    predicate_schema_ref: str = ""
    predicate_semantic_key: str = ""
    role_bindings: tuple[RoleBinding, ...] = ()
    role_groundings: tuple[object, ...] = ()
    context_ref: str = ""
    communicative_force: str = ""
    confidence: float = 0.0
    selected_evidence_refs: tuple[str, ...] = ()
    rejected_alternative_refs: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    is_opaque: bool = False
    is_provisional: bool = False
    requested_semantic_operation: str = ""
    grounding_ref: str = ""
    context_kind: str = ""


class CanonicalInterpretationResolver(InterpretationResolver):
    def _make_interpretation(self, candidate, force, graph, grounding):
        selected, reason = super()._make_interpretation(
            candidate,
            force,
            graph,
            grounding,
        )
        if selected is None or reason:
            return selected, reason

        pg = (
            grounding.for_predication(selected.predication_ref)
            if grounding is not None
            else None
        )
        grounded_bindings = selected.role_bindings
        if pg is not None:
            grounded_bindings = tuple(
                RoleBinding(
                    role_schema_ref=item.role_schema_ref,
                    filler_ref=item.grounded_filler_ref,
                    confidence=item.confidence,
                    evidence_refs=(
                        item.grounding.referent_ref,
                    ) if item.grounding is not None else (),
                )
                for item in pg.role_bindings
            )

        context_kind = next(
            (
                item.context_frame.context_kind
                for item in graph.candidate_contexts
                if item.context_frame.id == selected.context_ref
            ),
            "",
        )
        base_values = {
            item.name: getattr(selected, item.name)
            for item in fields(SelectedInterpretation)
        }
        base_values["role_bindings"] = grounded_bindings
        return CanonicalSelectedInterpretation(
            **base_values,
            context_kind=context_kind,
        ), ""
