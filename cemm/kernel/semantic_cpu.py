"""Semantic core-loop orchestrator.

This wires the seed lattices into the active kernel perceptor, graph builder,
planner, patch extractor, and consolidator. It is intentionally thin: the goal
is to make the architecture runnable without hiding module boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..learning.concept_consolidator import ConceptConsolidator, ConsolidationResult
from ..learning.graph_patch_extractor import GraphPatchExtractor
from ..memory.concept_lattice import ConceptLattice
from ..memory.construction_lattice import ConstructionLattice
from ..memory.episodic_trace_store import EpisodicTraceStore
from ..types.meaning_percept import MeaningPerceptPacket, RetrievalPlan, SafetyFrame, SituationFrame
from ..types.uol_graph import UOLGraph
from .act_resolution_planner import ActResolutionPlan, ActResolutionPlanner
from .affordance_predictor import AffordancePredictor
from .construction_matcher import ConstructionMatcher
from .meaning_graph_builder import MeaningGraphBuilder
from .meaning_perceptor import MeaningPerceptor
from .port_resolver import LatticePortResolver


@dataclass
class SemanticCycleResult:
    percept: MeaningPerceptPacket
    plan: ActResolutionPlan
    consolidation: ConsolidationResult | None = None
    uol_graph: UOLGraph | None = None


class SemanticCPU:
    def __init__(
        self,
        concept_lattice: ConceptLattice | None = None,
        construction_lattice: ConstructionLattice | None = None,
        episodic_store: EpisodicTraceStore | None = None,
        auto_consolidate: bool = False,
    ) -> None:
        self.concept_lattice = concept_lattice or ConceptLattice()
        self.construction_lattice = construction_lattice or ConstructionLattice()
        self.episodic_store = episodic_store or EpisodicTraceStore()
        self.auto_consolidate = auto_consolidate

        self.graph_builder = MeaningGraphBuilder(
            concept_lattice=self.concept_lattice,
            construction_lattice=self.construction_lattice,
            port_resolver=LatticePortResolver(self.concept_lattice),
            affordance_lattice=AffordancePredictor(),
        )
        self.construction_matcher = ConstructionMatcher(
            construction_lattice=self.construction_lattice,
        )
        self.perceptor = MeaningPerceptor(
            construction_matcher=self.construction_matcher,
        )
        self.perceptor._graph_builder = self.graph_builder
        self.planner = ActResolutionPlanner()
        self.patch_extractor = GraphPatchExtractor()
        self.consolidator = ConceptConsolidator(
            self.concept_lattice,
            construction_lattice=self.construction_lattice,
            episodic_store=self.episodic_store,
        )

    def run_turn(
        self,
        signal: Any,
        kernel: Any,
        *,
        percept: MeaningPerceptPacket | None = None,
        retrieval_plan: RetrievalPlan | None = None,
        safety_frame: SafetyFrame | None = None,
        situation: SituationFrame | None = None,
    ) -> SemanticCycleResult:
        if percept is None:
            percept = self.perceptor.perceive(signal, kernel)
        uol_graph: UOLGraph | None = getattr(percept, "uol_graph", None)
        if uol_graph is None:
            uol_graph = self.graph_builder.build(percept)
        if uol_graph is not None:
            percept.graph_patch_candidates = list(self.patch_extractor.extract(uol_graph))
        plan = self.planner.plan(
            None,
            situation=situation,
            retrieval_plan=retrieval_plan,
            safety_frame=safety_frame,
            meaning_percept=percept,
        )
        consolidation = None
        if self.auto_consolidate and uol_graph is not None:
            consolidation = self.consolidator.consolidate(
                list(percept.graph_patch_candidates),
                source_graph=uol_graph,
            )
        return SemanticCycleResult(
            percept=percept,
            plan=plan,
            consolidation=consolidation,
            uol_graph=uol_graph,
        )

__all__ = ["SemanticCPU", "SemanticCycleResult"]
