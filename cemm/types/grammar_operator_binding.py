"""GrammarOperatorBinding — maps closed-class items to semantic features.
Articles, determiners, prepositions, case markers, auxiliaries, inflections,
particles, and conjunctions are not disposable stop words.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class GrammarFeatureKind(str, Enum):
    """Language-neutral semantic features that grammar items can encode."""
    DEFINITENESS = "definiteness"
    SPECIFICITY = "specificity"
    QUANTITY = "quantity"
    TIME = "time"
    ASPECT = "aspect"
    COMPLETION = "completion"
    SOURCE = "source"
    GOAL = "goal"
    PATH = "path"
    CONTAINMENT = "containment"
    INSTRUMENT = "instrument"
    POSSESSION = "possession"
    ACCOMPANIMENT = "accompaniment"
    DOMAIN = "domain"
    MODALITY = "modality"
    NEGATION = "negation"
    EVIDENTIALITY = "evidentiality"
    CAUSAL = "causal"
    CONDITIONAL = "conditional"
    CONTRASTIVE = "contrastive"
    TEMPORAL_DISCOURSE = "temporal_discourse"
    INFORMATION_STRUCTURE = "information_structure"
    REFERENCE_ACCESSIBILITY = "reference_accessibility"
    NOUN_CLASS = "noun_class"


@dataclass(frozen=True, slots=True)
class GrammarOperatorBinding:
    """Binds a surface form/morpheme/position to semantic features or graph operations.
    
    Language-specific rules remain in language packs. This binding type
    maps them to language-neutral semantic features.
    """
    binding_id: str
    language_tag: str
    surface_form: str
    grammatical_category: str
    # article, determiner, preposition, postposition, case_marker,
    # auxiliary, inflection, particle, conjunction, clitic
    
    feature_kind: GrammarFeatureKind
    feature_value: str = ""
    
    # Graph rewrite: what UOL changes this grammar item produces
    graph_rewrite: dict[str, Any] = field(default_factory=dict)
    
    scope: str = "language"
    confidence: float = 0.5
    source: str = "language_pack"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "language_tag": self.language_tag,
            "surface_form": self.surface_form,
            "grammatical_category": self.grammatical_category,
            "feature_kind": self.feature_kind.value,
            "feature_value": self.feature_value,
            "scope": self.scope,
            "confidence": self.confidence,
        }
