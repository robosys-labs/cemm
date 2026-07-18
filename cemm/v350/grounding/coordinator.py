"""Composition root for Phase-7 evidence and Phase-8 joint grounding."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from ..language import FormLattice, FormLatticeAnalyzer
from ..schema.model import semantic_fingerprint
from ..storage import SemanticStore, StoreSnapshot
from .candidates import GroundingCandidateProvider
from .mentions import MentionCompiler
from .model import (
    DiscourseAnchor,
    GroundingConstraint,
    GroundingConstraintKind,
    GroundingResult,
    MultimodalTrack,
    SystemOutputAnchor,
)
from .solver import JointGroundingSolver


class JointGrounder:
    def __init__(
        self,
        store: SemanticStore,
        analyzer: FormLatticeAnalyzer,
        *,
        solver: JointGroundingSolver | None = None,
    ) -> None:
        self.store = store
        self.analyzer = analyzer
        self.mentions = MentionCompiler(analyzer.registry)
        self.candidates = GroundingCandidateProvider(store)
        self.solver = solver or JointGroundingSolver()

    def ground_text(
        self,
        content: str,
        *,
        source_ref: str,
        context_ref: str = "actual",
        language_hints: tuple[str, ...] = (),
        discourse_anchors: Iterable[DiscourseAnchor] = (),
        multimodal_tracks: Iterable[MultimodalTrack] = (),
        system_outputs: Iterable[SystemOutputAnchor] = (),
        constraints: Iterable[GroundingConstraint] = (),
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[FormLattice, GroundingResult]:
        lattice = self.analyzer.analyze(
            content, source_ref=source_ref, language_hints=language_hints
        )
        mentions = self.mentions.compile(lattice, context_ref=context_ref)
        derived_constraints = self._derive_constraints(mentions)
        candidates = self.candidates.generate(
            mentions,
            discourse_anchors=discourse_anchors,
            multimodal_tracks=multimodal_tracks,
            system_outputs=system_outputs,
            snapshot=snapshot,
        )
        result = self.solver.solve(
            mentions,
            candidates,
            constraints=(*tuple(constraints), *derived_constraints),
            evidence_refs=(lattice.lattice_ref,),
        )
        return lattice, result

    @staticmethod
    def _derive_constraints(mentions) -> tuple[GroundingConstraint, ...]:
        coref = defaultdict(list)
        distinct = defaultdict(list)
        result = []
        for mention in mentions:
            coref_group = mention.metadata.get("coreference_group")
            distinct_group = mention.metadata.get("distinctness_group")
            if coref_group:
                coref[str(coref_group)].append(mention.mention_ref)
            if distinct_group:
                distinct[str(distinct_group)].append(mention.mention_ref)
            if mention.target_class.value == "claim_source":
                result.append(GroundingConstraint(
                    constraint_ref="grounding-constraint:" + semantic_fingerprint(
                        "claim-source-constraint", mention.mention_ref, 24
                    ),
                    constraint_kind=GroundingConstraintKind.CLAIM_SOURCE,
                    mention_refs=(mention.mention_ref,),
                    required=True,
                    evidence_refs=mention.evidence_refs,
                ))
            if mention.target_class.value == "audience":
                result.append(GroundingConstraint(
                    constraint_ref="grounding-constraint:" + semantic_fingerprint(
                        "claim-audience-constraint", mention.mention_ref, 24
                    ),
                    constraint_kind=GroundingConstraintKind.CLAIM_AUDIENCE,
                    mention_refs=(mention.mention_ref,),
                    required=True,
                    evidence_refs=mention.evidence_refs,
                ))
        for group, refs in sorted(coref.items()):
            if len(refs) > 1:
                result.append(GroundingConstraint(
                    constraint_ref=f"grounding-constraint:corefer:{group}",
                    constraint_kind=GroundingConstraintKind.COREFER,
                    mention_refs=tuple(sorted(refs)),
                    required=True,
                    evidence_refs=tuple(sorted({
                        evidence_ref
                        for mention in mentions if mention.mention_ref in refs
                        for evidence_ref in mention.evidence_refs
                    })),
                ))
        for group, refs in sorted(distinct.items()):
            if len(refs) > 1:
                result.append(GroundingConstraint(
                    constraint_ref=f"grounding-constraint:distinct:{group}",
                    constraint_kind=GroundingConstraintKind.DISTINCT,
                    mention_refs=tuple(sorted(refs)),
                    required=True,
                    evidence_refs=tuple(sorted({
                        evidence_ref
                        for mention in mentions if mention.mention_ref in refs
                        for evidence_ref in mention.evidence_refs
                    })),
                ))
        return tuple(result)
