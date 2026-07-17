"""Canonical UOL public surface for CEMM v3.4.7.

All records are defined once in :mod:`cemm.v347.model`.  This package contains
only stable imports; it is not a second implementation authority.
"""
from cemm.v347.model import (
    DiscourseRelation,
    EmissionProof,
    GraphPatch,
    MeaningBundle,
    MeaningHypothesis,
    PatchOperation,
    PatchOperationKind,
    PortBinding,
    Predication,
    PropositionPayload,
    Referent,
    ReferentKind,
    ResponseClausePlan,
    UOLGraph,
    UOLResponsePlan,
)

__all__ = [
    "DiscourseRelation", "EmissionProof", "GraphPatch", "MeaningBundle",
    "MeaningHypothesis", "PatchOperation", "PatchOperationKind", "PortBinding",
    "Predication", "PropositionPayload", "Referent", "ReferentKind",
    "ResponseClausePlan", "UOLGraph", "UOLResponsePlan",
]
