"""Phase-17 typed observation Stage 1-3 bridge.

Kept in a dedicated module so the canonical runtime delegates explicitly rather than growing a
second observation/grounding brain. All semantic work still flows through existing language,
grounding, CSIR and recurrent services.
"""
from __future__ import annotations

from ..conversation import participant_frame_session_anchors
from ..csir.authority_v351 import MissingExactDependency, SemanticAuthorityError
from ..grounding.coordinator import JointGrounder
from ..grounding.participants import participant_frame_anchors
from ..language.analyzer import FormLatticeAnalyzer
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import EvidenceEnvelope, EvidenceLattice, GroundingCandidateSet, RuntimeInput, artifact_ref
from .adapters_v351 import canonical_observation_adapters_v351
from .grounding_v351 import grounding_tracks_from_analyses_v351, prepare_nonlexical_multimodal_grounding_v351
from .model_v351 import ModalityKind, RawObservationV351, StructuredObservationAnalysisV351

def stage_01_observe_multimodal_evidence_v351(coordinator, cycle, capability):
    envelope = cycle.input_payload if isinstance(cycle.input_payload, RuntimeInput) else RuntimeInput(str(cycle.input_payload))
    items = []
    participant_frame = cycle.artifacts.get("participant_frame")
    for evidence_ref in tuple(envelope.participant_evidence_refs):
        participant_ref = getattr(participant_frame, "input_speaker_ref", envelope.speaker_ref)
        source_ref = artifact_ref("source-transport-participant", cycle.context_ref, participant_ref, evidence_ref)
        items.append(EvidenceEnvelope(
            evidence_ref=evidence_ref, source_ref=source_ref, kind="transport_participant_identity",
            payload={"participant_ref": participant_ref, "transport_grounded": True},
            context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            confidence=1.0, lineage_refs=(source_ref,),
        ))
    if envelope.content:
        source_ref = artifact_ref("source-cycle-input", cycle.cycle_ref, envelope.content)
        items.append(EvidenceEnvelope(
            evidence_ref=artifact_ref("evidence-cycle-input", cycle.cycle_ref, source_ref),
            source_ref=source_ref, kind="text", payload=envelope.content,
            context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            evidence_refs=tuple(envelope.participant_evidence_refs), lineage_refs=(source_ref,),
        ))
    for observation in tuple(envelope.observations):
        if not isinstance(observation, RawObservationV351):
            raise TypeError("RuntimeInput.observations accepts RawObservationV351 only")
        if observation.context_ref != cycle.context_ref:
            raise ValueError("observation context differs from cognitive cycle context")
        if observation.permission_ref not in {"public", cycle.permission_ref}:
            raise ValueError("observation permission exceeds cognitive cycle scope")
        items.append(EvidenceEnvelope(
            evidence_ref=artifact_ref("evidence-typed-observation", cycle.cycle_ref, observation.observation_ref),
            source_ref=observation.source_ref, kind=f"raw_observation:{observation.modality.value}",
            payload=observation, context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            confidence=1.0 if observation.confidence is None else float(observation.confidence),
            evidence_refs=tuple(observation.evidence_refs), lineage_refs=tuple(observation.lineage_refs),
        ))
    # Legacy MultimodalTrack remains accepted only as pre-Phase-17 evidence input. It is not
    # promoted to semantic authority and final activation evidence should use typed observations.
    for track in envelope.multimodal_tracks:
        items.append(EvidenceEnvelope(
            evidence_ref=artifact_ref("evidence-multimodal", cycle.cycle_ref, getattr(track, "track_ref", repr(track))),
            source_ref=str(getattr(track, "track_ref", cycle.cycle_ref)),
            kind=str(getattr(track, "kind", "legacy_multimodal_track")), payload=track,
            context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            evidence_refs=tuple(getattr(track, "evidence_refs", ()) or ()),
            lineage_refs=tuple(getattr(track, "evidence_refs", ()) or ()),
        ))
    if not items:
        return StageOutcome(StageExecutionStatus.DEFERRED, frontier_refs=("frontier:observation:no-evidence",))
    return coordinator._performed(evidence_envelopes=tuple(items))

def _observation_analyzer_v351(coordinator, observation):
    injected = tuple(coordinator.services.observation_analyzers.values())
    matches = tuple(item for item in injected if callable(getattr(item, "supports", None)) and item.supports(observation.modality))
    if len(matches) > 1:
        raise ValueError(f"ambiguous injected observation analyzer:{observation.modality.value}:{len(matches)}")
    if matches:
        return matches[0]
    canonical = tuple(item for item in coordinator._canonical_observation_adapters if item.supports(observation.modality))
    if len(canonical) > 1:
        raise ValueError(f"ambiguous canonical observation analyzer:{observation.modality.value}:{len(canonical)}")
    return canonical[0] if canonical else None

def stage_02_encode_form_and_sensor_evidence_v351(coordinator, cycle, capability):
    envelopes = tuple(cycle.artifacts["evidence_envelopes"])
    text_items = [item for item in envelopes if item.kind == "text"]
    raw_observations = [item.payload for item in envelopes if item.kind.startswith("raw_observation:")]
    legacy_sensor = tuple(
        item for item in envelopes
        if item.kind not in {"text", "transport_participant_identity"} and not item.kind.startswith("raw_observation:")
    )
    analyses = []
    unresolved = []
    semantic_authority = cycle.artifacts["semantic_authority_snapshot_v351"]
    for observation in raw_observations:
        if observation.temporal_extent is not None and observation.temporal_extent.clock_pin is not None:
            semantic_authority.require_known_pin(observation.temporal_extent.clock_pin)
        if observation.spatial_extent is not None and observation.spatial_extent.frame_authority_pin is not None:
            semantic_authority.require_known_pin(observation.spatial_extent.frame_authority_pin)
        if observation.modality is ModalityKind.TEXT:
            if not text_items:
                source_ref = observation.source_ref
                text_items.append(EvidenceEnvelope(
                    evidence_ref=observation.observation_ref, source_ref=source_ref, kind="text",
                    payload=str(observation.payload), context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref, evidence_refs=observation.evidence_refs,
                    lineage_refs=observation.lineage_refs,
                ))
            continue
        analyzer = _observation_analyzer_v351(coordinator, observation)
        if analyzer is None:
            unresolved.append(f"sensor-model:{observation.observation_ref}:{observation.modality.value}")
            continue
        try:
            analysis = analyzer.analyze(
                observation, authority_snapshot_v351=semantic_authority,
                cycle=cycle, capability=capability,
            )
        except (MissingExactDependency, SemanticAuthorityError):
            # Exact authority failure is never downgraded to an ordinary sensor frontier.
            raise
        except (ValueError, TypeError) as exc:
            unresolved.append(f"sensor-analysis:{observation.observation_ref}:{type(exc).__name__}")
            continue
        if not isinstance(analysis, StructuredObservationAnalysisV351):
            raise TypeError("observation analyzer must return StructuredObservationAnalysisV351")
        if analysis.observation_ref != observation.observation_ref or analysis.modality is not observation.modality:
            raise ValueError("observation analysis identity/modality mismatch")
        models = tuple(item for item in semantic_authority.observation_models if item.model_pin.key == analysis.observation_model_pin.key)
        if len(models) != 1:
            raise ValueError("analysis ObservationModel is absent/ambiguous in exact authority snapshot")
        model = models[0]
        if model.modality_ref != observation.modality.value:
            raise ValueError("analysis ObservationModel modality mismatch")
        if (None if model.calibration_pin is None else model.calibration_pin.key) != (None if analysis.calibration_pin is None else analysis.calibration_pin.key):
            raise ValueError("analysis calibration differs from exact ObservationModel")
        licensed = {pin.key for pin in model.output_definition_pins}
        if any(pin.key not in licensed for pin in analysis.semantic_projection_pins):
            raise ValueError("analysis semantic projection is outside exact ObservationModel outputs")
        analyses.append(analysis)
    # Speech transcript is language/form evidence, not semantic authority. A primary typed/text
    # content channel wins; transcript is promoted to the form lattice only when no such text exists.
    if not text_items:
        for analysis in analyses:
            if analysis.modality is ModalityKind.SPEECH and analysis.transcript:
                text_items.append(EvidenceEnvelope(
                    evidence_ref=artifact_ref("evidence-speech-transcript", analysis.analysis_ref),
                    source_ref=analysis.observation_ref, kind="text", payload=analysis.transcript,
                    context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                    evidence_refs=analysis.evidence_refs, lineage_refs=analysis.lineage_refs,
                ))
    form_lattice = None
    language_evidence = ()
    if text_items:
        cm, snapshot = coordinator._read(capability)
        try:
            registry = coordinator.store.repositories.language.registry(snapshot=snapshot)
            analyzer = FormLatticeAnalyzer(registry, syntax_adapters=coordinator.services.syntax_adapters)
            content = "\n".join(str(item.payload) for item in text_items)
            hints = tuple(getattr(cycle.input_payload, "language_hints", ()) or ())
            form_lattice = analyzer.analyze(content, source_ref=text_items[0].source_ref, language_hints=hints)
            unresolved.extend(f"form-span:{x.start}:{x.end}" for x in form_lattice.unresolved_spans)
            language_evidence = tuple(getattr(form_lattice, "language_evidence", ()) or ())
        finally:
            cm.__exit__(None, None, None)
    lattice = EvidenceLattice(
        lattice_ref=artifact_ref("evidence-lattice", cycle.cycle_ref, tuple(x.evidence_ref for x in envelopes)),
        form_lattice=form_lattice,
        structured_observations=tuple((*analyses, *legacy_sensor)),
        evidence_refs=tuple(x.evidence_ref for x in envelopes), unresolved_refs=tuple(unresolved),
    )
    return StageOutcome(
        StageExecutionStatus.PERFORMED,
        artifacts={
            "evidence_lattice": lattice, "language_decision_evidence": language_evidence,
            "sensor_feature_candidates": tuple(analyses),
            "_structured_observation_analyses": tuple(analyses),
        },
        frontier_refs=tuple(f"frontier:{x}" for x in unresolved),
    )

def stage_03_activate_and_ground_referents_v351(coordinator, cycle, capability):
    lattice: EvidenceLattice = cycle.artifacts["evidence_lattice"]
    envelope = cycle.input_payload if isinstance(cycle.input_payload, RuntimeInput) else RuntimeInput(str(cycle.input_payload))
    analyses = tuple(cycle.artifacts.get("_structured_observation_analyses", ()) or ())
    cm, snapshot = coordinator._read(capability)
    try:
        frame = cycle.artifacts["participant_frame"]
        participant_anchors = participant_frame_anchors(frame, store=coordinator.store, snapshot=snapshot)
        session_snapshot = coordinator.session_memory.snapshot(cycle.context_ref, cycle.permission_ref)
        cycle_participant_anchors = participant_frame_session_anchors(frame, turn_index=session_snapshot.revision + 1)
        anchors = {
            item.anchor_ref: item for item in (
                *tuple(getattr(envelope, "discourse_anchors", ()) or ()),
                *coordinator.session_memory.grounding_anchors(cycle.context_ref, cycle.permission_ref),
                *participant_anchors, *cycle_participant_anchors,
            )
        }
        system_outputs = (
            *tuple(getattr(envelope, "system_output_anchors", ()) or ()),
            *coordinator.session_memory.system_output_anchors(cycle.context_ref, cycle.permission_ref),
        )
        constraints = tuple(getattr(envelope, "grounding_constraints", ()) or ())
        if lattice.form_lattice is None:
            prepared, result = prepare_nonlexical_multimodal_grounding_v351(
                coordinator.store, analyses, context_ref=cycle.context_ref,
                discourse_anchors=tuple(anchors[key] for key in sorted(anchors)),
                system_outputs=system_outputs, constraints=constraints, snapshot=snapshot,
            )
            if prepared is None or result is None:
                return coordinator._gap(capability.stage, "multimodal_grounder")
        else:
            analyzer = FormLatticeAnalyzer(coordinator.store.repositories.language.registry(snapshot=snapshot), syntax_adapters=coordinator.services.syntax_adapters)
            grounder = JointGrounder(coordinator.store, analyzer)
            typed_tracks = grounding_tracks_from_analyses_v351(analyses)
            prepared = grounder.prepare_lattice(
                lattice.form_lattice, context_ref=cycle.context_ref,
                discourse_anchors=tuple(anchors[key] for key in sorted(anchors)),
                multimodal_tracks=tuple((*typed_tracks, *tuple(getattr(envelope, "multimodal_tracks", ()) or ()))),
                system_outputs=system_outputs, constraints=constraints, snapshot=snapshot,
            )
            result = grounder.solve_prepared(prepared)
    finally:
        cm.__exit__(None, None, None)
    artifact = GroundingCandidateSet(
        candidate_set_ref=artifact_ref("grounding-candidates", cycle.cycle_ref, tuple(x.candidate_ref for x in prepared.candidates)),
        preparation=prepared, result=result, evidence_refs=tuple(result.evidence_refs),
        unresolved_refs=tuple(result.frontier_refs),
    )
    return StageOutcome(
        StageExecutionStatus.PERFORMED,
        artifacts={"grounding_candidates": artifact, "identity_coreference_trace": tuple(result.evidence_refs)},
        frontier_refs=tuple(result.frontier_refs),
    )



__all__ = [
    "stage_01_observe_multimodal_evidence_v351",
    "stage_02_encode_form_and_sensor_evidence_v351",
    "stage_03_activate_and_ground_referents_v351",
]
