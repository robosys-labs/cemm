from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from .semantic_ref import SemanticRef, SemanticRefKind
from .provenance import ProvenanceEnvelope


class GapKind(str, Enum):
    """Typed semantic gap kinds.

    Each gap kind represents a specific missing meaning dimension.
    """
    LEXEME_SENSE = "lexeme_sense"
    MORPHOLOGY = "morphology"
    GRAMMATICAL_FUNCTION = "grammatical_function"
    CONSTRUCTION = "construction"
    ENTITY_KIND = "entity_kind"
    ENTITY_IDENTITY = "entity_identity"
    RELATION_IDENTITY = "relation_identity"
    RELATION_ORIENTATION = "relation_orientation"
    OPERATOR_IDENTITY = "operator_identity"
    REQUIRED_PORT = "required_port"
    STATE_FAMILY = "state_family"
    STATE_DIMENSION = "state_dimension"
    STATE_VALUE_OR_SCALE = "state_value_or_scale"
    TEMPORAL_ANCHOR = "temporal_anchor"
    GEOSPATIAL_ANCHOR = "geospatial_anchor"
    MODALITY_OR_POLARITY = "modality_or_polarity"
    CAUSAL_EFFECT = "causal_effect"
    REALIZATION_FORM = "realization_form"


@dataclass(frozen=True, slots=True)
class SemanticGap:
    """A typed representation of unknown or uncertain meaning.

    A gap records exactly what meaning dimension is missing, with
    provenance, confidence, and candidate hypotheses for resolution.
    """
    gap_id: str
    branch_id: str
    group_id: str
    span_ref: SemanticRef
    language_tag: str
    gap_kind: GapKind

    # What this gap blocks (artifact IDs that depend on resolution)
    blocking_artifact_ids: tuple[str, ...] = ()

    # Fields that have been filled vs still missing
    required_fields: tuple[str, ...] = ()
    resolved_fields: dict[str, Any] = field(default_factory=dict)

    # Candidate hypotheses for resolution
    candidate_hypothesis_ids: tuple[str, ...] = ()

    # Uncertainty and provenance
    entropy: float = 1.0
    confidence: float = 0.0
    provenance: ProvenanceEnvelope | None = None

    # Surface form that triggered the gap (if applicable)
    surface_form: str = ""

    @property
    def is_blocking(self) -> bool:
        """A gap is blocking when unresolved meaning is required for
        a selected obligation, safety decision, query target, write target,
        or state transition."""
        return len(self.blocking_artifact_ids) > 0

    @property
    def is_fully_resolved(self) -> bool:
        return all(f in self.resolved_fields for f in self.required_fields)

    def with_resolved_field(self, field: str, value: Any) -> "SemanticGap":
        new_resolved = dict(self.resolved_fields)
        new_resolved[field] = value
        return SemanticGap(
            gap_id=self.gap_id,
            branch_id=self.branch_id,
            group_id=self.group_id,
            span_ref=self.span_ref,
            language_tag=self.language_tag,
            gap_kind=self.gap_kind,
            blocking_artifact_ids=self.blocking_artifact_ids,
            required_fields=self.required_fields,
            resolved_fields=new_resolved,
            candidate_hypothesis_ids=self.candidate_hypothesis_ids,
            entropy=self.entropy,
            confidence=self.confidence,
            provenance=self.provenance,
            surface_form=self.surface_form,
        )
