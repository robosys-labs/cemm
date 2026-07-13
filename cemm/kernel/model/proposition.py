"""Proposition and ModalQualifier — truth-bearing semantic content.

Import boundary: standard library only → refs, identity, predication.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import TimeExtent, AssessmentEnvironmentFingerprint


@dataclass(frozen=True, slots=True)
class ModalQualifier:
    """Modal qualifier independent from polarity and context.

    modal_kind: possible, necessary, permitted, prohibited, obligated, capable
    """
    modal_kind: str
    holder_ref: str | None = None  # Ref[Referent] as opaque string
    degree: float | None = None
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Proposition:
    """Truth-bearing semantic content.

    A Proposition wraps a Predication with context, polarity, modality,
    attribution, valid time, and derivation metadata.

    The following are independent axes and must never be collapsed into
    one ``proposition_mode`` enum:
    - communicative force (assert, ask, request, etc.)
    - polarity (positive / negative)
    - context (actual, reported, believed, hypothetical, etc.)
    - modality (possible, necessary, permitted, etc.)
    - temporal scope and aspect
    """
    id: str
    predication_ref: str  # Ref[Predication] as opaque string
    context_ref: str  # Ref[ContextFrame] as opaque string
    polarity: str = "positive"  # positive | negative
    modal_qualifiers: tuple[ModalQualifier, ...] = ()
    attribution_ref: str | None = None  # Ref[Referent | EvidenceRecord]
    valid_time: TimeExtent | None = None
    evidence_refs: tuple[str, ...] = ()
    derivation_kind: str = "observed"  # observed, attributed, inferred, replayed
    derivation_parent_refs: tuple[str, ...] = ()
    interpreted_under: tuple[str, ...] = ()  # Ref[SchemaEnvelope] refs
    assessment_environment_fingerprint: str = ""
