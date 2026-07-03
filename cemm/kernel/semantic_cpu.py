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
from .act_resolution_planner import ActResolutionPlan, ActResolutionPlanner
from .affordance_predictor import AffordancePredictor
from .meaning_graph_builder import MeaningGraphBuilder
from .meaning_perceptor import MeaningPerceptor
from .port_resolver import LatticePortResolver


@dataclass
class SemanticCycleResult:
    percept: MeaningPerceptPacket
    plan: ActResolutionPlan
    consolidation: ConsolidationResult | None = None


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
        self.perceptor = MeaningPerceptor()
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
        retrieval_plan: RetrievalPlan | None = None,
        safety_frame: SafetyFrame | None = None,
        situation: SituationFrame | None = None,
    ) -> SemanticCycleResult:
        percept = self.perceptor.perceive(signal, kernel)
        if percept.uol_graph is not None:
            percept.graph_patch_candidates = self.patch_extractor.extract(percept.uol_graph)
        plan = self.planner.plan(
            None,
            situation=situation,
            retrieval_plan=retrieval_plan,
            safety_frame=safety_frame,
            meaning_percept=percept,
        )
        consolidation = None
        if self.auto_consolidate and percept.uol_graph is not None:
            consolidation = self.consolidator.consolidate(
                list(percept.graph_patch_candidates),
                source_graph=percept.uol_graph,
            )
        return SemanticCycleResult(percept=percept, plan=plan, consolidation=consolidation)

__all__ = ["SemanticCPU", "SemanticCycleResult"]
