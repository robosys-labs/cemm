"""Reviewed mechanical observation adapters for Phase 17.

Adapters may calibrate, normalize and expose evidence. They may project semantics only through
an exact ObservationModel output_definition_pin in the pinned AuthoritySnapshotV351.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from ..csir.authority_v351 import AuthoritySnapshotV351, ObservationModel
from ..csir.model import ExactAuthorityPin
from ..runtime_abi import artifact_ref
from .model_v351 import (
    CalibratedFeatureV351, ExactReferentBindingV351, ModalityKind, ObservationTrackV351,
    RawObservationV351, StructuredObservationAnalysisV351,
)


def _payload_map(observation: RawObservationV351) -> Mapping[str, Any]:
    if not isinstance(observation.payload, Mapping):
        raise TypeError(f"{observation.modality.value} adapter requires mapping payload")
    return observation.payload


def _confidence(value, fallback: float) -> float:
    # 0.0 is meaningful and must never be replaced by a truthiness default.
    resolved = fallback if value is None else float(value)
    if not 0.0 <= resolved <= 1.0:
        raise ValueError("confidence must be within [0,1]")
    return resolved


def resolve_observation_model(
    snapshot: AuthoritySnapshotV351,
    observation: RawObservationV351,
) -> ObservationModel:
    candidates = tuple(
        item for item in snapshot.observation_models
        if item.modality_ref == observation.modality.value
        and (observation.requested_model_pin is None or item.model_pin.key == observation.requested_model_pin.key)
    )
    if len(candidates) != 1:
        raise ValueError(
            f"exact observation model selection requires one model:{observation.modality.value}:{len(candidates)}"
        )
    model = candidates[0]
    if observation.requested_calibration_pin is not None:
        if model.calibration_pin is None or model.calibration_pin.key != observation.requested_calibration_pin.key:
            raise ValueError("requested calibration pin differs from exact ObservationModel")
    return model


def _projection_pins(model: ObservationModel, payload: Mapping[str, Any]) -> tuple[ExactAuthorityPin, ...]:
    requested = tuple(payload.get("semantic_projection_pins", ()) or ())
    if not requested:
        return ()
    by_key = {pin.key: pin for pin in model.output_definition_pins}
    result = []
    for pin in requested:
        if not isinstance(pin, ExactAuthorityPin):
            raise TypeError("semantic projection must use ExactAuthorityPin")
        if pin.key not in by_key:
            raise ValueError("semantic projection is not licensed by exact ObservationModel")
        result.append(by_key[pin.key])
    return tuple(sorted({pin.key: pin for pin in result}.values(), key=lambda pin: pin.key))


class ReviewedObservationAdapterV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "observation_analyzer"
    SUPPORTED_MODALITIES: frozenset[ModalityKind] = frozenset()

    def supports(self, modality: ModalityKind) -> bool:
        return modality in self.SUPPORTED_MODALITIES

    def _model(self, observation, authority_snapshot_v351):
        if not isinstance(authority_snapshot_v351, AuthoritySnapshotV351):
            raise TypeError("observation adapter requires AuthoritySnapshotV351")
        return resolve_observation_model(authority_snapshot_v351, observation)

    @staticmethod
    def _base_refs(observation: RawObservationV351):
        evidence = tuple(sorted(set(observation.evidence_refs or (observation.observation_ref,))))
        lineage = tuple(sorted(set(observation.lineage_refs or (observation.source_ref,))))
        return evidence, lineage


class SpeechProsodyObservationAdapterV351(ReviewedObservationAdapterV351):
    SUPPORTED_MODALITIES = frozenset({ModalityKind.SPEECH, ModalityKind.PROSODY})

    def analyze(self, observation: RawObservationV351, *, authority_snapshot_v351, **_kwargs):
        if not self.supports(observation.modality):
            raise ValueError("speech/prosody adapter received unsupported modality")
        model = self._model(observation, authority_snapshot_v351)
        payload = _payload_map(observation)
        evidence, lineage = self._base_refs(observation)
        calibration = model.calibration_pin
        if calibration is None:
            raise ValueError("speech/prosody ObservationModel requires calibration")
        features = []
        for name, raw in sorted(dict(payload.get("features", {}) or {}).items()):
            value = raw.get("value") if isinstance(raw, Mapping) else raw
            conf = raw.get("confidence") if isinstance(raw, Mapping) else None
            dep = raw.get("dependence_ref", "") if isinstance(raw, Mapping) else ""
            features.append(CalibratedFeatureV351(
                feature_ref=artifact_ref("calibrated-feature", observation.observation_ref, name),
                feature_name=str(name), value=value,
                confidence=_confidence(conf, _confidence(observation.confidence, 1.0)),
                calibration_pin=calibration, evidence_refs=evidence, lineage_refs=lineage,
                dependence_ref=str(dep or ""),
            ))
        transcript = None
        if observation.modality is ModalityKind.SPEECH and payload.get("transcript") is not None:
            transcript = str(payload["transcript"])
        return StructuredObservationAnalysisV351(
            analysis_ref=artifact_ref("observation-analysis", observation.observation_ref, model.model_pin.key),
            observation_ref=observation.observation_ref, modality=observation.modality,
            observation_model_pin=model.model_pin, calibration_pin=calibration,
            features=tuple(features), semantic_projection_pins=_projection_pins(model, payload),
            transcript=transcript, evidence_refs=evidence, lineage_refs=lineage,
            metadata={"transcript_is_form_evidence": bool(transcript)},
        )


class VisionTrackObservationAdapterV351(ReviewedObservationAdapterV351):
    SUPPORTED_MODALITIES = frozenset({ModalityKind.VISION})

    def analyze(self, observation: RawObservationV351, *, authority_snapshot_v351, **_kwargs):
        model = self._model(observation, authority_snapshot_v351)
        payload = _payload_map(observation)
        evidence, lineage = self._base_refs(observation)
        calibration = model.calibration_pin
        if calibration is None:
            raise ValueError("vision ObservationModel requires calibration")
        tracks = []
        for index, raw in enumerate(tuple(payload.get("tracks", ()) or ())):
            if not isinstance(raw, Mapping):
                raise TypeError("vision track must be a mapping")
            track_ref = str(raw.get("track_ref") or artifact_ref("vision-track", observation.observation_ref, index))
            direct_binding = raw.get("direct_binding")
            if direct_binding is not None and not isinstance(direct_binding, ExactReferentBindingV351):
                raise TypeError("direct vision referent binding requires ExactReferentBindingV351")
            binding_evidence = ()
            if direct_binding is not None:
                authority_snapshot_v351.require_known_pin(direct_binding.binding_authority_pin)
                binding_evidence = tuple(direct_binding.evidence_refs)
            # Provider class labels are features only. They are never converted to type_refs here.
            tracks.append(ObservationTrackV351(
                track_ref=track_ref, modality=ModalityKind.VISION, context_ref=observation.context_ref,
                salience=_confidence(raw.get("salience"), _confidence(observation.confidence, 0.5)),
                evidence_refs=tuple(sorted(set((*evidence, *tuple(raw.get("evidence_refs", ()) or ()), *binding_evidence)))),
                lineage_refs=lineage, type_refs=(), valid_time_ref=raw.get("valid_time_ref"),
                direct_binding=direct_binding,
                metadata={
                    "provider_label": raw.get("label"),
                    "provider_track_metadata": dict(raw.get("metadata", {}) or {}),
                },
            ))
        return StructuredObservationAnalysisV351(
            analysis_ref=artifact_ref("observation-analysis", observation.observation_ref, model.model_pin.key),
            observation_ref=observation.observation_ref, modality=observation.modality,
            observation_model_pin=model.model_pin, calibration_pin=calibration, tracks=tuple(tracks),
            semantic_projection_pins=_projection_pins(model, payload), evidence_refs=evidence,
            lineage_refs=lineage,
        )


class ScalarSensorObservationAdapterV351(ReviewedObservationAdapterV351):
    SUPPORTED_MODALITIES = frozenset({
        ModalityKind.LOCATION, ModalityKind.ENVIRONMENT,
        ModalityKind.RUNTIME_TELEMETRY, ModalityKind.SENSOR,
    })

    def analyze(self, observation: RawObservationV351, *, authority_snapshot_v351, **_kwargs):
        model = self._model(observation, authority_snapshot_v351)
        payload = _payload_map(observation)
        evidence, lineage = self._base_refs(observation)
        calibration = model.calibration_pin
        if calibration is None:
            raise ValueError(f"{observation.modality.value} ObservationModel requires calibration")
        features = tuple(
            CalibratedFeatureV351(
                feature_ref=artifact_ref("calibrated-feature", observation.observation_ref, str(name)),
                feature_name=str(name), value=(raw.get("value") if isinstance(raw, Mapping) else raw),
                confidence=_confidence(
                    raw.get("confidence") if isinstance(raw, Mapping) else None,
                    _confidence(observation.confidence, 1.0),
                ),
                calibration_pin=calibration, evidence_refs=evidence, lineage_refs=lineage,
                dependence_ref=str(raw.get("dependence_ref", "") if isinstance(raw, Mapping) else ""),
            )
            for name, raw in sorted(dict(payload.get("features", payload) or {}).items())
            if name not in {"semantic_projection_pins", "semantic_fragments"}
        )
        fragments = tuple(payload.get("semantic_fragments", ()) or ())
        return StructuredObservationAnalysisV351(
            analysis_ref=artifact_ref("observation-analysis", observation.observation_ref, model.model_pin.key),
            observation_ref=observation.observation_ref, modality=observation.modality,
            observation_model_pin=model.model_pin, calibration_pin=calibration, features=features,
            semantic_projection_pins=_projection_pins(model, payload), semantic_fragments=fragments,
            evidence_refs=evidence, lineage_refs=lineage,
        )


class OperationResultObservationAdapterV351(ReviewedObservationAdapterV351):
    SUPPORTED_MODALITIES = frozenset({ModalityKind.OPERATION_RESULT})

    def analyze(self, observation: RawObservationV351, *, authority_snapshot_v351, **_kwargs):
        model = self._model(observation, authority_snapshot_v351)
        payload = _payload_map(observation)
        evidence, lineage = self._base_refs(observation)
        # Operation-result semantics are a signed contract projection, not sensor calibration.
        return StructuredObservationAnalysisV351(
            analysis_ref=artifact_ref("observation-analysis", observation.observation_ref, model.model_pin.key),
            observation_ref=observation.observation_ref, modality=observation.modality,
            observation_model_pin=model.model_pin, calibration_pin=model.calibration_pin,
            semantic_projection_pins=_projection_pins(model, payload),
            semantic_fragments=tuple(payload.get("semantic_fragments", ()) or ()),
            evidence_refs=evidence, lineage_refs=lineage,
            metadata={"operation_ref": payload.get("operation_ref")},
        )


def canonical_observation_adapters_v351():
    return (
        SpeechProsodyObservationAdapterV351(), VisionTrackObservationAdapterV351(),
        ScalarSensorObservationAdapterV351(), OperationResultObservationAdapterV351(),
    )


__all__ = [
    "OperationResultObservationAdapterV351", "ReviewedObservationAdapterV351",
    "ScalarSensorObservationAdapterV351", "SpeechProsodyObservationAdapterV351",
    "VisionTrackObservationAdapterV351", "canonical_observation_adapters_v351",
    "resolve_observation_model",
]
