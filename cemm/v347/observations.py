"""Multimodal observation contracts and evidence fusion.

Analyzers are deliberately non-authoritative. They emit reversible observations
and evidence; they never create durable knowledge, select identity, or activate a
schema. Text analysis is represented by a FormLattice and other modalities use
AnalyzerObservation records in the same ObservationLattice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Protocol

from .model import (
    AnalyzerObservation,
    EvidenceRef,
    FormLattice,
    ObservationKind,
    ObservationLattice,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    semantic_hash,
)


class ObservationAnalyzer(Protocol):
    analyzer_ref: str
    version: str

    def analyze(
        self,
        payload: Mapping[str, Any],
        *,
        context_ref: str,
        observation_index: int,
    ) -> tuple[AnalyzerObservation, ...]: ...


class StructuredObservationAnalyzer:
    analyzer_ref = "analyzer:structured_world"
    version = "3.4.7.2"

    def analyze(
        self,
        payload: Mapping[str, Any],
        *,
        context_ref: str,
        observation_index: int,
    ) -> tuple[AnalyzerObservation, ...]:
        referent_ref = str(payload.get("referent_ref", "")).strip()
        state = payload.get("state", {})
        if not referent_ref or not isinstance(state, Mapping):
            return ()
        modality = str(payload.get("modality", "structured")).casefold()
        try:
            kind = ObservationKind(modality)
        except ValueError:
            kind = ObservationKind.STRUCTURED
        observed_at = str(payload.get("observed_at") or datetime.now(timezone.utc).isoformat())
        confidence = max(0.0, min(1.0, float(payload.get("confidence", 0.5))))
        result: list[AnalyzerObservation] = []
        # One atom per observed state key keeps evidence independently addressable.
        for key, value in sorted(state.items(), key=lambda item: str(item[0])):
            observation_id = semantic_hash("observation", (
                context_ref, referent_ref, modality, str(key), value, observed_at, observation_index
            ))
            evidence_ref = f"evidence:{observation_id}"
            result.append(AnalyzerObservation(
                observation_id=observation_id,
                observation_kind=kind,
                source_ref=str(payload.get("source_ref", self.analyzer_ref)),
                context_ref=context_ref,
                confidence=confidence,
                payload={
                    "referent_ref": referent_ref,
                    "state_key": str(key),
                    "state_value": value,
                    "track_id": str(payload.get("track_id", "")),
                    "raw_modality": modality,
                },
                evidence_refs=(evidence_ref,),
                observed_at=observed_at,
                analyzer_ref=self.analyzer_ref,
                analyzer_version=self.version,
            ))
        return tuple(result)


class ObservationFusionCoordinator:
    """Fuse analyzer records while preserving disagreement and lineage."""

    def __init__(self, analyzers: Iterable[ObservationAnalyzer] = ()):
        analyzers = tuple(analyzers)
        self._analyzers = analyzers or (StructuredObservationAnalyzer(),)

    def observe(
        self,
        *,
        context_ref: str,
        form_lattices: Iterable[FormLattice] = (),
        observations: Iterable[Mapping[str, Any]] = (),
    ) -> ObservationLattice:
        forms = tuple(form_lattices)
        records: list[AnalyzerObservation] = []
        unresolved: list[str] = []
        for index, payload in enumerate(observations):
            matched = False
            for analyzer in self._analyzers:
                produced = analyzer.analyze(
                    payload,
                    context_ref=context_ref,
                    observation_index=index,
                )
                if produced:
                    matched = True
                    records.extend(produced)
            if not matched:
                unresolved.append(semantic_hash("observation:unresolved", (context_ref, index, payload)))

        # Keep the strongest duplicate but retain contradictory values as distinct
        # observations because fusion is not truth selection.
        deduped: dict[tuple[str, str, str, str], AnalyzerObservation] = {}
        for record in records:
            payload = record.payload
            key = (
                record.observation_kind.value,
                str(payload.get("referent_ref", "")),
                str(payload.get("state_key", "")),
                repr(payload.get("state_value")),
            )
            current = deduped.get(key)
            if current is None or record.confidence > current.confidence:
                deduped[key] = record
        records = sorted(deduped.values(), key=lambda item: item.observation_id)

        evidence: list[EvidenceRef] = []
        for form in forms:
            evidence.extend(form.evidence)
        for record in records:
            for evidence_ref in record.evidence_refs:
                evidence.append(EvidenceRef(
                    evidence_id=evidence_ref,
                    source_ref=record.source_ref,
                    confidence=record.confidence,
                    lineage_ref=f"{record.analyzer_ref}:{record.analyzer_version}",
                    metadata={
                        "observation_kind": record.observation_kind.value,
                        "observation_ref": record.observation_id,
                    },
                ))
        analyzer_fingerprint = semantic_hash("analyzer_fingerprint", (
            tuple((item.analyzer_ref, item.version) for item in self._analyzers),
            tuple(sorted(form.analyzer_versions.items()) for form in forms),
        ), 64)
        return ObservationLattice(
            lattice_id=semantic_hash("observation_lattice", (
                context_ref,
                tuple(form.lattice_id for form in forms),
                tuple(item.observation_id for item in records),
            )),
            context_ref=context_ref,
            form_lattices=forms,
            observations=tuple(records),
            fused_evidence=tuple(evidence),
            modality_refs=tuple(dict.fromkeys(
                [ObservationKind.TEXT.value] * len(forms)
                + [item.observation_kind.value for item in records]
            )),
            analyzer_fingerprint=analyzer_fingerprint,
            unresolved_observation_refs=tuple(unresolved),
        )

    def compile_evidence_patch(
        self,
        lattice: ObservationLattice,
        *,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        """Persist analyzer evidence without promoting observations to knowledge.

        The patch contains only EvidenceRef records.  World tracks and semantic
        propositions are compiled by their own coordinators so the fusion layer
        cannot silently become an admission authority.
        """
        if not lattice.fused_evidence:
            return None
        operations = tuple(
            PatchOperation(
                operation_id=f"op:{item.evidence_id}",
                kind=PatchOperationKind.UPSERT_EVIDENCE,
                target_ref=item.evidence_id,
                payload={
                    "source_ref": item.source_ref,
                    "confidence": item.confidence,
                    "lineage_ref": item.lineage_ref,
                    "span_start": item.span_start,
                    "span_end": item.span_end,
                    "metadata": dict(item.metadata),
                },
            )
            for item in lattice.fused_evidence
        )
        return GraphPatch(
            patch_id=semantic_hash("patch:observation_evidence", lattice.lattice_id),
            context_ref=lattice.context_ref,
            scope_ref=lattice.context_ref,
            source_ref="runtime:observation_fusion",
            evidence_refs=tuple(item.evidence_id for item in lattice.fused_evidence),
            operations=operations,
            expected_store_revision=expected_store_revision,
            permission_ref="internal",
            metadata={
                "analyzer_fingerprint": lattice.analyzer_fingerprint,
                "modalities": lattice.modality_refs,
            },
        )
