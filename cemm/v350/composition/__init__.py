"""CEMM v3.5 Phase-9 factor-graph UOL composition."""
from .builder import MeaningFactorGraphBuilder
from .coordinator import MeaningComposer
from .contract import CompositionContract, CompositionPackageAuditor, load_composition_contract
from .materializer import UOLHypothesisMaterializer, UOLMaterializationError
from .model import (
    MeaningBundle,
    MeaningCompositionResult,
    MeaningFactor,
    MeaningFactorGraph,
    MeaningFactorKind,
    MeaningHypothesis,
    MeaningSolveResult,
    MeaningValue,
    MeaningVariable,
    MeaningVariableKind,
    PartialUnderstandingMap,
    PruningTrace,
    SelectionAssessment,
)
from .solver import MeaningFactorSolver

__all__ = [
    "CompositionContract", "CompositionPackageAuditor", "MeaningBundle", "MeaningComposer", "MeaningCompositionResult", "MeaningFactor",
    "MeaningFactorGraph", "MeaningFactorGraphBuilder", "MeaningFactorKind",
    "MeaningFactorSolver", "MeaningHypothesis", "MeaningSolveResult", "MeaningValue",
    "MeaningVariable", "MeaningVariableKind", "PartialUnderstandingMap", "PruningTrace",
    "SelectionAssessment", "UOLHypothesisMaterializer", "UOLMaterializationError",
    "load_composition_contract",
]
