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
        context_ref: str,
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
        derived_constraints = self._derive_constraints(mentions, lattice, snapshot=snapshot)
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

    def _derive_constraints(
        self, mentions, lattice: FormLattice, *, snapshot: StoreSnapshot | None
    ) -> tuple[GroundingConstraint, ...]:
        """Derive only structural constraints from reviewed evidence/schema contracts.

        Crucially, this method never embeds semantic type names such as ``agent``.
        Construction roles are resolved against the exact output schema revision,
        and candidate compatibility is expressed from that port's data-declared
        accepted types/storage kinds.
        """
        coref = defaultdict(list)
        distinct = defaultdict(list)
        result: list[GroundingConstraint] = []
        candidate_by_ref = {item.candidate_ref: item for item in lattice.construction_candidates}
        schema_registry = self.store.repositories.schemas.registry(snapshot=snapshot)

        for mention in mentions:
            coref_group = mention.metadata.get("coreference_group")
            distinct_group = mention.metadata.get("distinctness_group")
            if coref_group:
                coref[str(coref_group)].append(mention.mention_ref)
            if distinct_group:
                distinct[str(distinct_group)].append(mention.mention_ref)

            port_contracts = []
            role = mention.syntactic_role
            if role:
                for candidate_ref in mention.construction_candidate_refs:
                    construction_candidate = candidate_by_ref.get(candidate_ref)
                    if construction_candidate is None:
                        continue
                    construction = self.analyzer.registry.require_construction(
                        construction_candidate.construction_ref,
                        construction_candidate.construction_revision,
                    )
                    if construction.output_schema_ref is None or construction.output_schema_revision is None:
                        continue
                    schema = schema_registry.schema(
                        construction.output_schema_ref, construction.output_schema_revision
                    )
                    matching_ports = tuple(
                        port for port in schema.local_ports
                        if port.port_ref == role or port.role_family == role
                    )
                    for port in matching_ports:
                        port_contracts.append({
                            "schema_ref": schema.schema_ref,
                            "schema_revision": schema.revision,
                            "port_ref": port.port_ref,
                            "role_family": port.role_family,
                            "accepted_type_refs": tuple(port.accepted_type_refs),
                            "accepted_storage_kinds": tuple(
                                sorted(item.value for item in port.accepted_storage_kinds)
                            ),
                        })
            if port_contracts:
                canonical_contracts = tuple(sorted(
                    port_contracts,
                    key=lambda item: (
                        item["schema_ref"], item["schema_revision"], item["port_ref"]
                    ),
                ))
                result.append(GroundingConstraint(
                    constraint_ref="grounding-constraint:" + semantic_fingerprint(
                        "port-compatibility-constraint",
                        (mention.mention_ref, canonical_contracts),
                        24,
                    ),
                    constraint_kind=GroundingConstraintKind.PORT_COMPATIBLE,
                    mention_refs=(mention.mention_ref,),
                    required=True,
                    evidence_refs=mention.evidence_refs,
                    metadata={"port_contracts": canonical_contracts},
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
