"""Typed CEMM v3.5.1 multimodal observation contracts.

Observations remain evidence. Provider labels, detector classes and sensor field names never
become semantic identity without an exact ObservationModel projection in the pinned authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..csir.model import CSIRCandidateFragment, ExactAuthorityPin


class ModalityKind(str, Enum):
    TEXT = "text"
    SPEECH = "speech"
    PROSODY = "prosody"
    VISION = "vision"
    LOCATION = "location"
    ENVIRONMENT = "environment"
    RUNTIME_TELEMETRY = "runtime_telemetry"
    OPERATION_RESULT = "operation_result"
    SENSOR = "sensor"


_CALIBRATED_MODALITIES = frozenset({
    ModalityKind.SPEECH,
    ModalityKind.PROSODY,
    ModalityKind.VISION,
    ModalityKind.LOCATION,
    ModalityKind.ENVIRONMENT,
    ModalityKind.RUNTIME_TELEMETRY,
    ModalityKind.SENSOR,
})


def _nonempty(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty")


def _unique(values, label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


@dataclass(frozen=True, slots=True)
class TemporalExtentV351:
    start_time: str
    end_time: str | None = None
    clock_pin: ExactAuthorityPin | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.start_time, "temporal start_time")
        if self.end_time is not None:
            _nonempty(self.end_time, "temporal end_time")
        _unique(self.evidence_refs, "temporal evidence refs")


@dataclass(frozen=True, slots=True)
class SpatialExtentV351:
    frame_ref: str
    coordinates: tuple[float, ...] = ()
    frame_authority_pin: ExactAuthorityPin | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.frame_ref, "spatial frame_ref")
        if any(not isfinite(float(value)) for value in self.coordinates):
            raise ValueError("spatial coordinates must be finite")
        _unique(self.evidence_refs, "spatial evidence refs")


@dataclass(frozen=True, slots=True)
class ExactReferentBindingV351:
    """A provider may name a durable referent only with exact binding authority + evidence."""

    referent_ref: str
    binding_authority_pin: ExactAuthorityPin
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonempty(self.referent_ref, "referent_ref")
        if not self.evidence_refs:
            raise ValueError("direct referent binding requires evidence")
        _unique(self.evidence_refs, "referent binding evidence")


@dataclass(frozen=True, slots=True)
class RawObservationV351:
    observation_ref: str
    modality: ModalityKind
    source_ref: str
    payload: Any
    context_ref: str
    permission_ref: str
    observed_at: str | None = None
    temporal_extent: TemporalExtentV351 | None = None
    spatial_extent: SpatialExtentV351 | None = None
    confidence: float | None = 1.0
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    requested_model_pin: ExactAuthorityPin | None = None
    requested_calibration_pin: ExactAuthorityPin | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.observation_ref, "observation_ref"),
            (self.source_ref, "source_ref"),
            (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _nonempty(value, label)
        if not isinstance(self.modality, ModalityKind):
            raise TypeError("modality must be ModalityKind")
        if self.confidence is not None:
            value = float(self.confidence)
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("observation confidence must be within [0,1]")
        _unique(self.evidence_refs, "observation evidence refs")
        _unique(self.lineage_refs, "observation lineage refs")


@dataclass(frozen=True, slots=True)
class CalibratedFeatureV351:
    feature_ref: str
    feature_name: str
    value: Any
    confidence: float
    calibration_pin: ExactAuthorityPin
    evidence_refs: tuple[str, ...]
    lineage_refs: tuple[str, ...] = ()
    dependence_ref: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.feature_ref, "feature_ref")
        _nonempty(self.feature_name, "feature_name")
        confidence = float(self.confidence)
        if not isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("feature confidence must be within [0,1]")
        if not self.evidence_refs:
            raise ValueError("calibrated feature requires evidence")
        _unique(self.evidence_refs, "feature evidence refs")
        _unique(self.lineage_refs, "feature lineage refs")


@dataclass(frozen=True, slots=True)
class ObservationTrackV351:
    track_ref: str
    modality: ModalityKind
    context_ref: str
    salience: float
    evidence_refs: tuple[str, ...]
    lineage_refs: tuple[str, ...] = ()
    type_refs: tuple[str, ...] = ()
    valid_time_ref: str | None = None
    direct_binding: ExactReferentBindingV351 | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.track_ref, "track_ref")
        _nonempty(self.context_ref, "context_ref")
        value = float(self.salience)
        if not isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("track salience must be within [0,1]")
        if not self.evidence_refs:
            raise ValueError("track requires evidence")
        _unique(self.evidence_refs, "track evidence refs")
        _unique(self.lineage_refs, "track lineage refs")
        _unique(self.type_refs, "track type refs")


@dataclass(frozen=True, slots=True)
class StructuredObservationAnalysisV351:
    analysis_ref: str
    observation_ref: str
    modality: ModalityKind
    observation_model_pin: ExactAuthorityPin
    calibration_pin: ExactAuthorityPin | None
    features: tuple[CalibratedFeatureV351, ...] = ()
    tracks: tuple[ObservationTrackV351, ...] = ()
    semantic_projection_pins: tuple[ExactAuthorityPin, ...] = ()
    semantic_fragments: tuple[CSIRCandidateFragment, ...] = ()
    transcript: str | None = None
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.analysis_ref, "analysis_ref")
        _nonempty(self.observation_ref, "observation_ref")
        if not isinstance(self.modality, ModalityKind):
            raise TypeError("analysis modality must be ModalityKind")
        if self.modality in _CALIBRATED_MODALITIES and self.calibration_pin is None:
            raise ValueError(f"{self.modality.value} analysis requires exact calibration authority")
        _unique((item.key for item in self.semantic_projection_pins), "semantic projection pins")
        _unique((item.feature_ref for item in self.features), "feature refs")
        _unique((item.track_ref for item in self.tracks), "track refs")
        _unique(self.evidence_refs, "analysis evidence refs")
        _unique(self.lineage_refs, "analysis lineage refs")
        if self.transcript is not None and self.modality is not ModalityKind.SPEECH:
            raise ValueError("only speech analysis may expose a transcript")


__all__ = [
    "CalibratedFeatureV351", "ExactReferentBindingV351", "ModalityKind",
    "ObservationTrackV351", "RawObservationV351", "SpatialExtentV351",
    "StructuredObservationAnalysisV351", "TemporalExtentV351",
]
