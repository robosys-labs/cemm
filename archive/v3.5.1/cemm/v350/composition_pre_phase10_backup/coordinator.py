"""Phase-9 UOL factor-graph composition root."""
from __future__ import annotations

from ..grounding.model import GroundingResult
from ..language.model import FormLattice
from ..schema.model import semantic_fingerprint
from ..storage import SemanticStore, StoreSnapshot
from .builder import MeaningFactorGraphBuilder
from .materializer import UOLHypothesisMaterializer, UOLMaterializationError
from .model import (
    MeaningBundle,
    MeaningCompositionResult,
    MeaningFactorGraph,
    MeaningSolveResult,
    PartialUnderstandingMap,
    SelectionAssessment,
)
from .solver import MeaningFactorSolver
from ..uol.equivalence import semantic_graph_fingerprint


class MeaningComposer:
    """Compose a selected, partial-safe UOL bundle from Phase-7/8 evidence.

    The public stage methods intentionally split Core Loop Stages 5, 6 and 7.
    ``compose`` remains a compatibility convenience but canonical runtime wiring
    must call ``build_factor_graph`` -> ``solve_factor_graph`` -> ``select_bundle``.
    Selection has no dependency on target-language realization.
    """

    def __init__(
        self,
        store: SemanticStore,
        *,
        builder: MeaningFactorGraphBuilder | None = None,
        solver: MeaningFactorSolver | None = None,
        materializer: UOLHypothesisMaterializer | None = None,
        decisiveness_margin: float = 0.75,
        close_alternative_margin: float = 1.0,
    ) -> None:
        if decisiveness_margin < 0 or close_alternative_margin < 0:
            raise ValueError("meaning selection margins cannot be negative")
        self.store = store
        self.builder = builder or MeaningFactorGraphBuilder(store)
        self.solver = solver or MeaningFactorSolver()
        self.materializer = materializer or UOLHypothesisMaterializer(store)
        self.decisiveness_margin = decisiveness_margin
        self.close_alternative_margin = close_alternative_margin

    def build_factor_graph(
        self,
        lattice: FormLattice,
        grounding: GroundingResult,
        *,
        context_ref: str,
        referent_projections=None,
        closure_candidates=(),
        snapshot: StoreSnapshot | None = None,
    ) -> MeaningFactorGraph:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.build_factor_graph(
                    lattice, grounding, context_ref=context_ref,
                    referent_projections=referent_projections,
                    closure_candidates=closure_candidates,
                    snapshot=pinned,
                )
        self.store.assert_snapshot(snapshot)
        graph = self.builder.build(
            lattice, grounding, context_ref=context_ref,
            closure_candidates=closure_candidates,
            snapshot=snapshot,
        )
        if referent_projections:
            from ..knowledge_factors import ReferentKnowledgeFactorBinder
            graph = ReferentKnowledgeFactorBinder(self.store).bind(
                graph,
                grounding=grounding,
                projections=referent_projections,
                closure_candidates=tuple(closure_candidates),
                snapshot=snapshot,
            )
        return graph

    def solve_factor_graph(self, factor_graph: MeaningFactorGraph) -> MeaningSolveResult:
        return self.solver.solve(factor_graph)

    def select_bundle(
        self,
        factor_graph: MeaningFactorGraph,
        solved: MeaningSolveResult,
        lattice: FormLattice,
        grounding: GroundingResult,
        *,
        context_ref: str,
        snapshot: StoreSnapshot | None = None,
    ) -> MeaningCompositionResult:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.select_bundle(
                    factor_graph,
                    solved,
                    lattice,
                    grounding,
                    context_ref=context_ref,
                    snapshot=pinned,
                )
        self.store.assert_snapshot(snapshot)
        if solved.factor_graph_ref != factor_graph.graph_ref:
            raise ValueError("meaning solve result does not belong to factor graph")
        if factor_graph.snapshot_fingerprint != snapshot.fingerprint:
            raise ValueError("meaning factor graph snapshot is stale at selection")

        materialized = []
        failures = []
        for hypothesis in solved.hypotheses:
            try:
                uol, report = self.materializer.materialize(
                    factor_graph,
                    hypothesis,
                    lattice,
                    grounding,
                    context_ref=context_ref,
                    snapshot=snapshot,
                )
            except UOLMaterializationError as exc:
                failures.append((hypothesis.hypothesis_ref, (str(exc),)))
                continue
            materialized.append((hypothesis, uol, report))

        semantic_clusters = {}
        for hypothesis, uol, report in materialized:
            semantic_clusters.setdefault(
                semantic_graph_fingerprint(uol), []
            ).append((hypothesis, uol, report))
        ranked_clusters = sorted(
            semantic_clusters.values(),
            key=lambda cluster: (
                -max(item[0].score for item in cluster),
                cluster[0][0].hypothesis_ref,
            ),
        )
        selected_cluster = ranked_clusters[0] if ranked_clusters else ()
        selected_hypothesis = selected_cluster[0][0] if selected_cluster else None
        selected_uol = selected_cluster[0][1] if selected_cluster else None
        selected_report = selected_cluster[0][2] if selected_cluster else None
        intentional_query_refs: set[str] = set()
        if selected_hypothesis is None:
            margin = 0.0
            close = ()
            uncertainty = ("no materializable meaning hypothesis",)
        else:
            next_score = (
                max(item[0].score for item in ranked_clusters[1])
                if len(ranked_clusters) > 1 else None
            )
            margin = (
                selected_hypothesis.score - next_score
                if next_score is not None
                else float("inf")
            )
            close = tuple(
                cluster[0][0].hypothesis_ref
                for cluster in ranked_clusters[1:]
                if selected_hypothesis.score
                - max(item[0].score for item in cluster)
                <= self.close_alternative_margin
            )
            uncertainty_list = []
            intentional_query_refs = {
                ref
                for ref, variable in (
                    selected_uol.variables.items()
                    if selected_uol is not None else ()
                )
                if getattr(
                    variable.open_binding_purpose, "value", None
                ) == "query"
            }
            semantic_unresolved = set(
                selected_hypothesis.unresolved_refs
            ) | (
                set(selected_uol.unresolved_refs)
                if selected_uol is not None else set()
            )
            semantic_unresolved.difference_update(intentional_query_refs)
            if semantic_unresolved:
                uncertainty_list.append(
                    "selected meaning retains unresolved semantic frontiers"
                )
            if close:
                uncertainty_list.append("close compatible alternatives are preserved")
            if solved.exhausted:
                uncertainty_list.append(
                    "bounded search budget exhausted before full enumeration"
                )
            if selected_report and selected_report.unresolved:
                uncertainty_list.append(
                    "UOL validation retains unresolved dependencies"
                )
            uncertainty = tuple(uncertainty_list)

        decisive = bool(
            selected_hypothesis is not None
            and margin >= self.decisiveness_margin
            and not uncertainty
        )
        selection = SelectionAssessment(
            selected_hypothesis_ref=(
                None
                if selected_hypothesis is None
                else selected_hypothesis.hypothesis_ref
            ),
            decisive=decisive,
            margin=margin,
            close_alternative_refs=close,
            uncertainty_reasons=uncertainty,
            evidence_refs=factor_graph.evidence_refs,
        )
        understood = ()
        selected_unresolved = tuple(factor_graph.unresolved_refs)
        if selected_uol is not None:
            understood = tuple(
                sorted(
                    set(selected_uol.referents)
                    | set(selected_uol.applications)
                    | set(selected_uol.coordination_groups)
                    | set(selected_uol.propositions)
                    | set(selected_uol.events)
                    | set(selected_uol.claims)
                )
            )
            selected_unresolved = tuple(
                sorted(set(selected_unresolved) | set(selected_uol.unresolved_refs))
            )
        partial = PartialUnderstandingMap(
            understood_refs=understood,
            unresolved_refs=selected_unresolved,
            frontier_refs=tuple(
                sorted(
                    set(grounding.frontier_refs)
                    | set(grounding.unresolved_mention_refs)
                )
            ),
            evidence_refs=factor_graph.evidence_refs,
        )
        alternatives = tuple(
            hypothesis
            for hypothesis, _uol, _report in materialized
            if selected_hypothesis is None
            or hypothesis.hypothesis_ref != selected_hypothesis.hypothesis_ref
        )
        bundle = MeaningBundle(
            bundle_ref="meaning-bundle:"
            + semantic_fingerprint(
                "meaning-bundle-ref",
                (
                    factor_graph.graph_ref,
                    None
                    if selected_hypothesis is None
                    else selected_hypothesis.hypothesis_ref,
                    tuple(item.hypothesis_ref for item in alternatives),
                ),
                24,
            ),
            factor_graph_ref=factor_graph.graph_ref,
            selected_hypothesis_ref=(
                None
                if selected_hypothesis is None
                else selected_hypothesis.hypothesis_ref
            ),
            uol_graph=selected_uol,
            alternatives=alternatives,
            selection=selection,
            partial_understanding=partial,
            evidence_refs=factor_graph.evidence_refs,
            metadata={
                "bounded": True,
                "beam_width": solved.metadata.get("beam_width"),
                "expansions": solved.expansions,
                "search_exhausted": solved.exhausted,
                "realization_influenced_selection": False,
                "actual_world_admission": False,
                "transition_commit": False,
                "selection_authority": (
                    "no_materializable_meaning"
                    if selected_hypothesis is None
                    else "ambiguous_semantic_clusters"
                    if close
                    else "semantically_equivalent_alternatives"
                    if len(selected_cluster) > 1
                    else "single_semantic_cluster"
                ),
                "equivalent_alternative_refs": tuple(
                    item[0].hypothesis_ref for item in selected_cluster[1:]
                ),
                "intentional_query_gap_refs": tuple(
                    sorted(intentional_query_refs)
                ),
            },
        )
        return MeaningCompositionResult(
            factor_graph=factor_graph,
            solve_result=solved,
            bundle=bundle,
            materialization_issue_codes=tuple(failures),
        )

    def compose(
        self,
        lattice: FormLattice,
        grounding: GroundingResult,
        *,
        context_ref: str,
        snapshot: StoreSnapshot | None = None,
    ) -> MeaningCompositionResult:
        """Compatibility one-shot composition outside canonical stage tracing."""

        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.compose(
                    lattice, grounding, context_ref=context_ref, snapshot=pinned
                )
        self.store.assert_snapshot(snapshot)
        graph = self.build_factor_graph(
            lattice, grounding, context_ref=context_ref, snapshot=snapshot
        )
        solved = self.solve_factor_graph(graph)
        return self.select_bundle(
            graph,
            solved,
            lattice,
            grounding,
            context_ref=context_ref,
            snapshot=snapshot,
        )
