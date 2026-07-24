"""CEMM v3.5 Phase-10 attributed claims and epistemic admission."""
from .admission import EpistemicAdmissionEngine
from .claims import ClaimCompilationError, ClaimOccurrenceCompiler
from .history import ClaimHistoryProjector
from .model import (
    AdmissionAssessment, AdmissionPolicy, AdmissionRequest, AdmissionThresholds,
    CompiledClaim, EpistemicProjection, FourStateTruthAssessment, SourceAssessment,
)
from .patches import EpistemicPatchPlanner
from .truth import FourStateTruthProjector

__all__ = [
    "AdmissionAssessment", "AdmissionPolicy", "AdmissionRequest", "AdmissionThresholds",
    "ClaimCompilationError", "ClaimHistoryProjector", "ClaimOccurrenceCompiler", "CompiledClaim",
    "EpistemicAdmissionEngine", "EpistemicPatchPlanner", "EpistemicProjection",
    "FourStateTruthAssessment", "FourStateTruthProjector", "SourceAssessment",
]
