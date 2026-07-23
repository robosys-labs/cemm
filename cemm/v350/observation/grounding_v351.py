"""Nonlexical multimodal grounding through the canonical grounding candidate/solver path."""
from __future__ import annotations

from ..grounding.candidates import GroundingCandidateProvider
from ..grounding.coordinator import GroundingPreparation
from ..grounding.model import MentionHypothesis, MentionTargetClass, MultimodalTrack
from ..grounding.solver import JointGroundingSolver
from ..language.model import Span
from ..runtime_abi import artifact_ref
from .model_v351 import StructuredObservationAnalysisV351


def _track_to_grounding_track(track):
    direct = track.direct_binding
    return MultimodalTrack(
        track_ref=track.track_ref,
        modality=track.modality.value,
        context_ref=track.context_ref,
        referent_ref=None if direct is None else direct.referent_ref,
        type_refs=tuple(track.type_refs),
        valid_time_ref=track.valid_time_ref,
        salience=float(track.salience),
        evidence_refs=tuple(track.evidence_refs),
        metadata={
            **dict(track.metadata),
            "direct_binding_authority_pin": None if direct is None else direct.binding_authority_pin,
        },
    )



def grounding_tracks_from_analyses_v351(analyses):
    return tuple(_track_to_grounding_track(track) for item in tuple(analyses) for track in item.tracks)


def prepare_nonlexical_multimodal_grounding_v351(
    store,
    analyses,
    *,
    context_ref: str,
    discourse_anchors=(),
    system_outputs=(),
    constraints=(),
    snapshot=None,
):
    """Create evidence-only mention hypotheses for tracks; no language lattice is fabricated."""
    analyses = tuple(analyses)
    tracks = list(grounding_tracks_from_analyses_v351(analyses))
    represented = {track.track_ref for track in tracks}
    for analysis in analyses:
        if analysis.tracks or not (analysis.semantic_projection_pins or analysis.semantic_fragments):
            continue
        tracks.append(MultimodalTrack(
            track_ref=artifact_ref("observation-evidence-track", analysis.observation_ref),
            modality=analysis.modality.value, context_ref=context_ref, referent_ref=None,
            type_refs=(), salience=0.5, evidence_refs=tuple(analysis.evidence_refs),
            metadata={"analysis_ref": analysis.analysis_ref, "semantic_projection_only": True},
        ))
    tracks = tuple(tracks)
    mentions = []
    for track in tracks:
        synthetic = f"⟦track:{track.track_ref}⟧"
        mentions.append(MentionHypothesis(
            mention_ref=artifact_ref("multimodal-mention", track.track_ref),
            source_ref=track.track_ref,
            span=Span(0, len(synthetic)),
            surface=synthetic,
            normalized_surface=synthetic,
            target_class=MentionTargetClass.MULTIMODAL_TRACK,
            context_ref=context_ref,
            salience=track.salience,
            evidence_refs=tuple(track.evidence_refs),
            metadata={
                "grounding_channels": ("multimodal",),
                "source_track_ref": track.track_ref,
                "nonlexical_observation": True,
            },
        ))
    if not mentions:
        return None, None
    provider = GroundingCandidateProvider(store)
    candidates = provider.generate(
        tuple(mentions), discourse_anchors=tuple(discourse_anchors),
        multimodal_tracks=tracks, system_outputs=tuple(system_outputs), snapshot=snapshot,
    )
    evidence_refs = tuple(sorted({
        *(ref for item in analyses for ref in item.evidence_refs),
        *(ref for candidate in candidates for factor in candidate.factors for ref in factor.evidence_refs),
    }))
    prepared = GroundingPreparation(
        lattice_ref=artifact_ref("nonlexical-multimodal-lattice", tuple(item.analysis_ref for item in analyses)),
        mentions=tuple(mentions), candidates=tuple(candidates), constraints=tuple(constraints),
        evidence_refs=evidence_refs,
    )
    result = JointGroundingSolver().solve(
        prepared.mentions, prepared.candidates, constraints=prepared.constraints,
        evidence_refs=prepared.evidence_refs,
    )
    return prepared, result


__all__ = ["grounding_tracks_from_analyses_v351", "prepare_nonlexical_multimodal_grounding_v351"]
