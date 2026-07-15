"""InterpretationResolver — grounding-aware candidate selection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .candidate_graph import CandidateGraph, CandidateProposition
from .grounding import GraphGrounding, PredicationGrounding
from ..model.role_binding import RoleBinding
from ..schema.use_profile import SemanticOperation, UseProfileLevel


@dataclass(frozen=True, slots=True)
class SelectedInterpretation:
    id: str
    predication_ref: str = ""
    proposition_ref: str = ""
    predicate_schema_ref: str = ""
    predicate_semantic_key: str = ""
    role_bindings: tuple[RoleBinding, ...] = ()
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


@dataclass(frozen=True, slots=True)
class InterpretationResult:
    selected: tuple[SelectedInterpretation, ...] = ()
    rejected: tuple[SelectedInterpretation, ...] = ()
    primary: SelectedInterpretation | None = None
    has_selection: bool = False

    @property
    def selected_count(self) -> int:
        return len(self.selected)


class InterpretationResolver:
    """Select branches using structural grounding and operation-specific use."""

    def resolve(
        self,
        candidate_graph: CandidateGraph,
        grounding_assessments: list[Any] | None = None,
        epistemic_assessments: list[Any] | None = None,
    ) -> InterpretationResult:
        graph_grounding = self._graph_grounding(grounding_assessments)
        selected: list[SelectedInterpretation] = []
        rejected: list[SelectedInterpretation] = []
        used: set[str] = set()

        forces = candidate_graph.candidate_communicative_forces or ()
        if not forces and candidate_graph.candidate_propositions:
            # Composition normally supplies a force; preserve an explicit
            # neutral fallback rather than guessing a conversation act.
            forces = ()

        for force in forces:
            candidates = [
                proposition for proposition in candidate_graph.candidate_propositions
                if not force.target_proposition_ref
                or proposition.proposition.id == force.target_proposition_ref
            ]
            ranked = sorted(
                candidates,
                key=lambda item: self._score(
                    item, force.force, candidate_graph, graph_grounding,
                    epistemic_assessments or [],
                ),
                reverse=True,
            )
            accepted = None
            for candidate in ranked:
                interpretation, reason = self._make_interpretation(
                    candidate,
                    force.force,
                    candidate_graph,
                    graph_grounding,
                )
                if reason:
                    rejected.append(
                        SelectedInterpretation(
                            id=f"interp_rej:{uuid4().hex[:12]}",
                            proposition_ref=candidate.proposition.id,
                            confidence=candidate.confidence,
                            rejection_reasons=(reason,),
                        )
                    )
                    continue
                accepted = interpretation
                break
            if accepted is not None:
                selected.append(accepted)
                used.add(accepted.proposition_ref)

        # Do not reinterpret embedded or supporting candidates from a question
        # as independent assertions.  Multi-clause composition must attach its
        # own communicative force to each asserted proposition.
        if not forces:
            for candidate in candidate_graph.candidate_propositions:
                if candidate.proposition.id in used:
                    continue
                interpretation, reason = self._make_interpretation(
                    candidate,
                    "assert",
                    candidate_graph,
                    graph_grounding,
                )
                if reason:
                    rejected.append(
                        SelectedInterpretation(
                            id=f"interp_rej:{uuid4().hex[:12]}",
                            proposition_ref=candidate.proposition.id,
                            confidence=candidate.confidence,
                            rejection_reasons=(reason,),
                        )
                    )
                elif interpretation is not None:
                    selected.append(interpretation)

        primary = max(selected, key=lambda item: item.confidence) if selected else None
        return InterpretationResult(
            selected=tuple(selected),
            rejected=tuple(rejected),
            primary=primary,
            has_selection=bool(selected),
        )

    def _make_interpretation(
        self,
        candidate: CandidateProposition,
        force: str,
        graph: CandidateGraph,
        grounding: GraphGrounding | None,
    ) -> tuple[SelectedInterpretation | None, str]:
        predication_candidate = next(
            (
                item for item in graph.candidate_predications
                if item.predication.id == candidate.proposition.predication_ref
            ),
            None,
        )
        if predication_candidate is None:
            return None, "proposition predication missing"

        predication = predication_candidate.predication
        pg = grounding.for_predication(predication.id) if grounding else None
        operation = self._requested_operation(force, pg)
        is_opaque = self._is_opaque(pg)
        is_provisional = is_opaque or bool(
            pg and pg.use_profile and pg.use_profile.level == UseProfileLevel.PARTIAL
        )

        # Opaque meaning may be selected for questions, quotation, correction,
        # and learning evidence. It may not support unqualified actual-world
        # inference or effects.
        if pg is None:
            if force not in {"ask", "assert", "correct"}:
                return None, "missing grounding for operational use"
        elif pg.use_profile is not None:
            if operation == SemanticOperation.CLASSIFY:
                if is_opaque:
                    # User assertions remain preservable as attributed learning
                    # evidence, never as admitted classification.
                    is_provisional = True
                elif not pg.use_profile.permits(operation):
                    return None, "schema use profile blocks classification"
            elif not pg.use_profile.permits(operation):
                return None, f"schema use profile blocks {operation.value}"

        confidence = candidate.confidence
        if pg is not None:
            if pg.is_structurally_usable:
                confidence += 0.1
            confidence -= 0.08 * len(pg.unresolved_role_refs)
            confidence -= 0.05 * len(pg.opaque_role_refs)
        confidence = max(0.0, min(1.0, confidence))

        return SelectedInterpretation(
            id=f"interp:{uuid4().hex[:12]}",
            predication_ref=predication.id,
            proposition_ref=candidate.proposition.id,
            predicate_schema_ref=predication.predicate_schema_ref,
            predicate_semantic_key=(
                pg.predicate_semantic_key if pg is not None
                else predication.predicate_schema_ref
            ),
            role_bindings=predication.bindings,
            context_ref=candidate.proposition.context_ref,
            communicative_force=force,
            confidence=confidence,
            selected_evidence_refs=candidate.source_evidence_refs,
            is_opaque=is_opaque,
            is_provisional=is_provisional,
            requested_semantic_operation=operation.value,
            grounding_ref=pg.predication_ref if pg is not None else "",
        ), ""

    @staticmethod
    def _requested_operation(
        force: str, grounding: PredicationGrounding | None,
    ) -> SemanticOperation:
        opaque = InterpretationResolver._is_opaque(grounding)
        if force == "ask":
            return SemanticOperation.PROBE if opaque else SemanticOperation.QUERY_THEORY
        if force in {"correct", "acknowledge"}:
            return SemanticOperation.COMPOSE_QUALIFIED
        return SemanticOperation.COMPOSE_QUALIFIED if opaque else SemanticOperation.CLASSIFY

    @staticmethod
    def _is_opaque(grounding: PredicationGrounding | None) -> bool:
        if grounding is None or grounding.use_profile is None:
            return True
        return bool(
            grounding.use_profile.level == UseProfileLevel.OPAQUE
            or grounding.opaque_role_refs
            or grounding.unresolved_role_refs
        )

    @staticmethod
    def _graph_grounding(values: list[Any] | None) -> GraphGrounding | None:
        if not values:
            return None
        for value in values:
            if isinstance(value, GraphGrounding):
                return value
        return None

    def _score(
        self,
        candidate: CandidateProposition,
        force: str,
        graph: CandidateGraph,
        grounding: GraphGrounding | None,
        epistemic_assessments: list[Any],
    ) -> float:
        score = candidate.confidence
        predication_ref = candidate.proposition.predication_ref
        pg = grounding.for_predication(predication_ref) if grounding else None
        if pg is not None and pg.is_structurally_usable:
            score += 0.15
        if pg is not None and pg.use_profile is not None:
            operation = self._requested_operation(force, pg)
            if pg.use_profile.permits(operation):
                score += 0.15
        assessment = next(
            (
                item for item in epistemic_assessments
                if getattr(item, "proposition_ref", "") == candidate.proposition.id
            ),
            None,
        )
        if assessment is not None:
            if getattr(assessment, "admissibility", "") in {"admitted", "attributed_only"}:
                score += 0.1
            elif getattr(assessment, "admissibility", "") == "blocked":
                score -= 0.2
        return score
