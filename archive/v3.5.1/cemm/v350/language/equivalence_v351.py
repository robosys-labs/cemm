"""Cross-language semantic equivalence gates for CEMM v3.5.1 Phase 17."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..csir.canonical_v351 import semantic_fingerprint
from ..csir.model import CSIRGraph


@dataclass(frozen=True, slots=True)
class LanguageSemanticEquivalenceV351:
    competence_ref: str
    language_tags: tuple[str, ...]
    semantic_fingerprints: tuple[tuple[str, str], ...]
    equivalent: bool
    proof_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.competence_ref or len(self.language_tags) < 2:
            raise ValueError("cross-language equivalence requires a competence ref and >=2 languages")
        if len(self.language_tags) != len(set(self.language_tags)):
            raise ValueError("language tags must be unique")
        if {tag for tag, _ in self.semantic_fingerprints} != set(self.language_tags):
            raise ValueError("equivalence fingerprints must cover each language exactly once")
        if self.equivalent and not self.proof_refs:
            raise ValueError("equivalence pass requires proof lineage")


def compare_shared_competence_v351(
    competence_ref: str,
    graphs_by_language: Mapping[str, CSIRGraph],
    *,
    proof_refs=(),
) -> LanguageSemanticEquivalenceV351:
    if len(graphs_by_language) < 2:
        raise ValueError("shared competence comparison requires at least two languages")
    fingerprints = tuple(sorted(
        (str(tag), semantic_fingerprint(graph)) for tag, graph in graphs_by_language.items()
    ))
    equivalent = len({fingerprint for _tag, fingerprint in fingerprints}) == 1
    proofs = tuple(sorted(set(proof_refs)))
    if equivalent and not proofs:
        proofs = ("proof:canonical-csir-semantic-normal-form-v351",)
    return LanguageSemanticEquivalenceV351(
        competence_ref=competence_ref,
        language_tags=tuple(tag for tag, _ in fingerprints),
        semantic_fingerprints=fingerprints,
        equivalent=equivalent,
        proof_refs=proofs,
    )


def synthetic_renaming_invariance_v351(
    competence_ref: str,
    original: CSIRGraph,
    renamed_language_graph: CSIRGraph,
) -> LanguageSemanticEquivalenceV351:
    """A synthetic renamed language must preserve meaning despite disjoint local forms."""
    return compare_shared_competence_v351(
        competence_ref,
        {"source": original, "synthetic-renamed": renamed_language_graph},
        proof_refs=("proof:synthetic-form-renaming-invariance-v351",),
    )


__all__ = [
    "LanguageSemanticEquivalenceV351", "compare_shared_competence_v351",
    "synthetic_renaming_invariance_v351",
]
