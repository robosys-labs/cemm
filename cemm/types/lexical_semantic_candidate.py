"""LexicalSemanticCandidate — candidate meaning from surface evidence.
Must go through predicate/operator activation before becoming authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .semantic_ref import SemanticRef, SemanticRefKind
from .provenance import ProvenanceEnvelope


@dataclass(frozen=True, slots=True)
class LexicalSemanticCandidate:
    """A candidate semantic meaning derived from surface lexical evidence.
    
    This is NOT an activated meaning. It must pass through:
    1. Predicate/operator activation with valid typed ports
    2. Scope validation
    3. Polarity and modality resolution
    
    Until then, it is merely evidence for an interpretation branch.
    """
    candidate_id: str
    surface_form: str
    language_tag: str
    lemma: str = ""
    grammatical_category: str = ""
    
    # What this candidate proposes
    semantic_target_ref: str = ""
    target_kind: str = ""  # entity, concept, operator, state, relation, etc.
    
    # Source evidence
    source_span_ref: str = ""
    span_start: int = 0
    span_end: int = 0
    
    # Multiple possible semantic targets (for ambiguity)
    alternative_targets: tuple[dict[str, Any], ...] = ()
    
    # Confidence and provenance
    confidence: float = 0.5
    provenance: ProvenanceEnvelope | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "surface_form": self.surface_form,
            "language_tag": self.language_tag,
            "lemma": self.lemma,
            "grammatical_category": self.grammatical_category,
            "semantic_target_ref": self.semantic_target_ref,
            "target_kind": self.target_kind,
            "confidence": self.confidence,
        }
