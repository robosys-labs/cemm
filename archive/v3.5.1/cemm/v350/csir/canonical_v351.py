"""v3.5.1 semantic/executable canonicalization boundary.

The Phase-6 canonicalizer treated ``SemanticApplication.operational_profile_pins`` as
meaning-bearing attributes.  That violates the v3.5.1 authority split: an operational
profile controls lifecycle/validation/use behavior and may change without changing what
an application means.

This module preserves the Phase-6 graph-isomorphism implementation while separating:

* semantic identity -- CSIR meaning only; operational profiles and proof lineage excluded;
* executable/exact identity -- semantic structure plus exact profiles, proof lineage and
  unresolved execution metadata.

Semantic node labels are derived from the profile-free graph so profile rotation cannot
renumber semantic nodes and poison caches or equality.
"""
from __future__ import annotations

from dataclasses import replace
from . import canonical as _v2
from .model import CSIRGraph


ComparisonAssessment = _v2.ComparisonAssessment
CanonicalizationBudgetExceeded = _v2.CanonicalizationBudgetExceeded
CanonicalizationError = _v2.CanonicalizationError


def _semantic_view(graph: CSIRGraph) -> CSIRGraph:
    """Return the meaning-only view used for semantic identity.

    Operational profile pins remain part of exact executable identity but never alter
    denotation.  Proof links are left in place here because the underlying semantic
    canonicalizer already excludes them; retaining them allows one normalization pass to
    preserve proof lineage.
    """
    return replace(
        graph,
        applications=tuple(
            replace(application, operational_profile_pins=())
            for application in graph.applications
        ),
    )


def canonical_semantic_code(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    return _v2.canonical_semantic_code(_semantic_view(graph), budget=budget)


def semantic_fingerprint(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    return _v2.semantic_fingerprint(_semantic_view(graph), budget=budget)


def _normalized_with_base(graph: CSIRGraph, *, budget: int):
    view = _semantic_view(graph)
    base = _v2.canonicalize(view, budget=budget)
    profiles_by_normalized_ref = {
        base.semantic_node_map[("application", application.application_ref)]:
            application.operational_profile_pins
        for application in graph.applications
    }
    applications = tuple(
        replace(
            application,
            operational_profile_pins=profiles_by_normalized_ref.get(
                application.application_ref, ()
            ),
        )
        for application in base.normalized_graph.applications
    )
    return replace(base.normalized_graph, applications=applications), base


def normalize(graph: CSIRGraph, *, budget: int = 100_000) -> CSIRGraph:
    """Normalize using meaning-only labels, then reattach exact operational profiles."""
    normalized, _base = _normalized_with_base(graph, budget=budget)
    return normalized

def canonical_exact_code(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    # Normalize semantic labels independently from operational-profile/proof changes, then
    # let the Phase-6 exact encoder include the exact executable attributes.
    return _v2.canonical_exact_code(normalize(graph, budget=budget), budget=budget)


def exact_fingerprint(graph: CSIRGraph, *, budget: int = 100_000) -> str:
    import hashlib

    return hashlib.sha256(canonical_exact_code(graph, budget=budget).encode("utf-8")).hexdigest()


def canonicalize(graph: CSIRGraph, *, budget: int = 100_000):
    normalized, base = _normalized_with_base(graph, budget=budget)
    exact_code = _v2.canonical_exact_code(normalized, budget=budget)
    import hashlib

    return _v2.CanonicalizationResult(
        semantic_code=base.semantic_code,
        semantic_fingerprint=base.semantic_fingerprint,
        exact_code=exact_code,
        exact_fingerprint=hashlib.sha256(exact_code.encode("utf-8")).hexdigest(),
        normalized_graph=normalized,
        semantic_node_map=base.semantic_node_map,
        proof_ref_map=base.proof_ref_map,
    )

def equivalent(left: CSIRGraph, right: CSIRGraph, *, budget: int = 100_000) -> bool:
    return semantic_fingerprint(left, budget=budget) == semantic_fingerprint(right, budget=budget)


def compare(left: CSIRGraph, right: CSIRGraph, *, budget: int = 100_000) -> ComparisonAssessment:
    left_fp = semantic_fingerprint(left, budget=budget)
    right_fp = semantic_fingerprint(right, budget=budget)
    return ComparisonAssessment(
        equivalent=left_fp == right_fp,
        left_fingerprint=left_fp,
        right_fingerprint=right_fp,
        reasons=() if left_fp == right_fp else ("canonical_semantic_normal_forms_differ",),
    )


__all__ = [
    "CanonicalizationBudgetExceeded",
    "CanonicalizationError",
    "ComparisonAssessment",
    "canonical_exact_code",
    "canonical_semantic_code",
    "canonicalize",
    "compare",
    "equivalent",
    "exact_fingerprint",
    "normalize",
    "semantic_fingerprint",
]
