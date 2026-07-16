"""Contextual N-best interpretation resolver for semantic forests."""
from __future__ import annotations

from dataclasses import replace

from .canonical_interpreter import CanonicalInterpretationResolver
from .interpreter import InterpretationResult, SelectedInterpretation


class ContextualInterpretationResolver(CanonicalInterpretationResolver):
    resolver_version = "contextual-nbest-v3.4.6"

    def resolve(
        self,
        candidate_graph,
        grounding_assessments=None,
        epistemic_assessments=None,
        *,
        context_snapshot=None,
    ):
        grounding = self._graph_grounding(grounding_assessments)
        epistemic = epistemic_assessments or []
        selected = []
        rejected = []
        alternatives = []
        used = set()
        forces = candidate_graph.candidate_communicative_forces or ()

        predication_sources = {
            item.predication.id: (
                set(item.source_token_indices), item.candidate_source
            )
            for item in candidate_graph.candidate_predications
        }
        for force in forces:
            force_source = set(
                tuple(getattr(force, "source_token_indices", ()) or ())
            )
            candidates = []
            for proposition in candidate_graph.candidate_propositions:
                source, candidate_source = predication_sources.get(
                    proposition.proposition.predication_ref, (set(), "")
                )
                if candidate_source == "rule_component":
                    continue
                if force_source:
                    if source and source == force_source:
                        candidates.append(proposition)
                elif (
                    not force.target_proposition_ref
                    or proposition.proposition.id == force.target_proposition_ref
                ):
                    candidates.append(proposition)
            accepted = []
            for candidate in candidates:
                interpretation, reason = self._make_interpretation(
                    candidate,
                    force.force,
                    candidate_graph,
                    grounding,
                )
                if reason or interpretation is None:
                    rejected.append(SelectedInterpretation(
                        id=f"interp_rej:{candidate.proposition.id}",
                        proposition_ref=candidate.proposition.id,
                        confidence=candidate.confidence,
                        rejection_reasons=(reason or "unusable candidate",),
                    ))
                    continue
                score, breakdown, coverage, unresolved = self._contextual_score(
                    candidate,
                    force.force,
                    candidate_graph,
                    grounding,
                    epistemic,
                    context_snapshot,
                )
                accepted.append(replace(
                    interpretation,
                    confidence=max(0.0, min(1.0, score)),
                    score_breakdown=breakdown,
                    coverage_ratio=coverage,
                    unresolved_fragment_refs=unresolved,
                ))
            accepted.sort(
                key=lambda item: (
                    item.confidence,
                    -len(item.unresolved_fragment_refs),
                    item.proposition_ref,
                ),
                reverse=True,
            )
            if accepted:
                if accepted[0].proposition_ref not in used:
                    selected.append(accepted[0])
                    used.add(accepted[0].proposition_ref)
                alternatives.extend(
                    item for item in accepted[1:]
                    if item.proposition_ref not in used
                )

        if not forces:
            predication_sources = {
                item.predication.id: item.candidate_source
                for item in candidate_graph.candidate_predications
            }
            accepted = []
            for candidate in candidate_graph.candidate_propositions:
                if predication_sources.get(
                    candidate.proposition.predication_ref
                ) == "rule_component":
                    continue
                interpretation, reason = self._make_interpretation(
                    candidate,
                    "assert",
                    candidate_graph,
                    grounding,
                )
                if reason or interpretation is None:
                    rejected.append(SelectedInterpretation(
                        id=f"interp_rej:{candidate.proposition.id}",
                        proposition_ref=candidate.proposition.id,
                        confidence=candidate.confidence,
                        rejection_reasons=(reason or "unusable candidate",),
                    ))
                    continue
                score, breakdown, coverage, unresolved = self._contextual_score(
                    candidate,
                    "assert",
                    candidate_graph,
                    grounding,
                    epistemic,
                    context_snapshot,
                )
                accepted.append(replace(
                    interpretation,
                    confidence=max(0.0, min(1.0, score)),
                    score_breakdown=breakdown,
                    coverage_ratio=coverage,
                    unresolved_fragment_refs=unresolved,
                ))
            accepted.sort(key=lambda item: item.confidence, reverse=True)
            if accepted:
                selected.append(accepted[0])
                alternatives.extend(accepted[1:])

        primary = max(selected, key=lambda item: item.confidence) if selected else None
        return InterpretationResult(
            selected=tuple(selected),
            rejected=tuple(rejected),
            alternatives=tuple(alternatives),
            primary=primary,
            has_selection=bool(selected),
        )

    def _contextual_score(
        self,
        candidate,
        force,
        graph,
        grounding,
        epistemic,
        context_snapshot,
    ):
        base = super()._score(
            candidate, force, graph, grounding, epistemic
        )
        breakdown = [("base_semantic", base)]
        predication_ref = candidate.proposition.predication_ref
        predication = next(
            (
                item for item in graph.candidate_predications
                if item.predication.id == predication_ref
            ),
            None,
        )
        coverage = dict(
            tuple(getattr(graph, "coverage_by_predication", ()) or ())
        ).get(predication_ref, 0.0)
        breakdown.append(("surface_coverage", coverage * 0.16))

        unresolved_items = tuple(
            getattr(graph, "unresolved_fragments", ()) or ()
        )
        source_indices = set(
            tuple(getattr(predication, "source_token_indices", ()) or ())
        )
        unresolved = tuple(
            str(getattr(item, "span_ref", ""))
            for item in unresolved_items
            if not source_indices.intersection(
                tuple(getattr(item, "token_indices", ()) or ())
            )
        )
        if unresolved:
            breakdown.append(("unresolved_residue", -min(0.22, len(unresolved) * 0.045)))

        pg = grounding.for_predication(predication_ref) if grounding else None
        predicate_key = (
            pg.predicate_semantic_key if pg is not None
            else getattr(predication.predication, "predicate_schema_ref", "")
            if predication is not None else ""
        )
        if context_snapshot is not None:
            topic = float(context_snapshot.predicate_weight(predicate_key))
            if topic:
                breakdown.append(("topic_continuity", min(0.12, topic * 0.12)))
            if pg is not None:
                salience = max(
                    (
                        float(context_snapshot.referent_weight(
                            binding.grounded_filler_ref
                        ))
                        for binding in pg.role_bindings
                    ),
                    default=0.0,
                )
                if salience:
                    breakdown.append(("referent_salience", min(0.12, salience * 0.12)))
                semantic_activation = max(
                    (
                        float(context_snapshot.semantic_weight(key))
                        for binding in pg.role_bindings
                        for key in tuple(
                            getattr(binding.grounding, "semantic_keys", ()) or ()
                        )
                    ),
                    default=0.0,
                )
                if semantic_activation:
                    breakdown.append((
                        "semantic_frequency",
                        min(0.10, semantic_activation * 0.10),
                    ))
                if any(
                    getattr(binding.grounding, "referent_kind", "") == "proposition"
                    for binding in pg.role_bindings
                ):
                    breakdown.append(("anaphora_resolution", 0.16))

        if candidate.proposition.valid_time is not None:
            breakdown.append(("temporal_grounding", 0.10))
        if any(
            relation.source_ref == candidate.proposition.id
            and relation.relation_kind in {"correction", "contrast", "answer"}
            for relation in graph.discourse_relations
        ):
            breakdown.append(("discourse_coherence", 0.12))

        # Base score already lies near [0, 1]. Keep contextual contributions
        # bounded and normalize after summation.
        contextual = sum(value for name, value in breakdown if name != "base_semantic")
        score = base * 0.72 + 0.14 + contextual
        return score, tuple(breakdown), coverage, unresolved
