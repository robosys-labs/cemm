"""Build structured source/document maps from semantic source descriptors."""

from __future__ import annotations

from typing import Any

from .types import DocumentArtifact, DocumentMap, DocumentSection, SourceDescriptor


class SourceMapper:
    """Normalize upstream source metadata without parsing human language."""

    def describe(self, source: Any) -> SourceDescriptor:
        if isinstance(source, SourceDescriptor):
            return source
        metadata = dict(getattr(source, "metadata", {}) or {})
        source_id = str(getattr(source, "source_id", "") or metadata.get("source_id", "source"))
        sections = list(getattr(source, "sections", []) or metadata.get("sections", []) or [])
        artifacts = list(getattr(source, "artifacts", []) or metadata.get("artifacts", []) or [])
        return SourceDescriptor(
            source_id=source_id,
            source_type=str(getattr(source, "source_type", "") or metadata.get("source_type", "unknown")),
            unit_count=int(getattr(source, "unit_count", 0) or metadata.get("unit_count", 0) or len(sections) + len(artifacts)),
            token_count=int(getattr(source, "token_count", 0) or metadata.get("token_count", 0) or 0),
            section_count=int(getattr(source, "section_count", 0) or metadata.get("section_count", 0) or len(sections)),
            artifact_count=int(getattr(source, "artifact_count", 0) or metadata.get("artifact_count", 0) or len(artifacts)),
            confidence=float(getattr(source, "confidence", 0.5) or metadata.get("confidence", 0.5) or 0.5),
            metadata=metadata,
            risk_tags=set(getattr(source, "risk_tags", set()) or metadata.get("risk_tags", set()) or set()),
        )

    def map_document(self, source: Any) -> DocumentMap:
        descriptor = self.describe(source)
        sections = [self._section(s, idx, descriptor.source_id) for idx, s in enumerate(self._raw_sections(source))]
        artifacts = [self._artifact(a, idx, descriptor.source_id) for idx, a in enumerate(self._raw_artifacts(source))]
        denominator = max(1, len(sections) + len(artifacts) + 1)
        return DocumentMap(
            source_id=descriptor.source_id,
            title_ref=str(descriptor.metadata.get("title_ref", "")),
            page_count=int(descriptor.metadata.get("page_count", 0) or getattr(source, "page_count", 0) or 0),
            token_estimate=descriptor.token_count,
            sections=sections,
            artifacts=artifacts,
            metadata_refs=list(descriptor.metadata.get("metadata_refs", []) or []),
            confidence=descriptor.confidence,
            coverage_denominator=denominator,
            diagnostics={
                "source_type": descriptor.source_type,
                "unit_count": descriptor.unit_count,
                "section_count": len(sections),
                "artifact_count": len(artifacts),
            },
        )

    @staticmethod
    def _raw_sections(source: Any) -> list[Any]:
        metadata = dict(getattr(source, "metadata", {}) or {})
        return list(getattr(source, "sections", []) or metadata.get("sections", []) or [])

    @staticmethod
    def _raw_artifacts(source: Any) -> list[Any]:
        metadata = dict(getattr(source, "metadata", {}) or {})
        return list(getattr(source, "artifacts", []) or metadata.get("artifacts", []) or [])

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _section(self, raw: Any, idx: int, source_id: str) -> DocumentSection:
        sid = str(self._get(raw, "section_id", "") or self._get(raw, "id", "") or f"{source_id}:section:{idx}")
        return DocumentSection(
            section_id=sid,
            index=int(self._get(raw, "index", idx) or idx),
            depth=int(self._get(raw, "depth", 1) or 1),
            role=str(self._get(raw, "role", "body") or "body"),
            parent_id=str(self._get(raw, "parent_id", "") or ""),
            page_start=int(self._get(raw, "page_start", 0) or 0),
            page_end=int(self._get(raw, "page_end", 0) or 0),
            token_estimate=int(self._get(raw, "token_estimate", 0) or 0),
            line_count=int(self._get(raw, "line_count", 0) or 0),
            salience=float(self._get(raw, "salience", 0.5) or 0.5),
            title_atom_id=str(self._get(raw, "title_atom_id", "") or ""),
            source_refs=list(self._get(raw, "source_refs", []) or []),
            metadata=dict(self._get(raw, "metadata", {}) or {}),
        )

    def _artifact(self, raw: Any, idx: int, source_id: str) -> DocumentArtifact:
        aid = str(self._get(raw, "artifact_id", "") or self._get(raw, "id", "") or f"{source_id}:artifact:{idx}")
        return DocumentArtifact(
            artifact_id=aid,
            artifact_type=str(self._get(raw, "artifact_type", "") or self._get(raw, "type", "unknown") or "unknown"),
            section_id=str(self._get(raw, "section_id", "") or ""),
            page=int(self._get(raw, "page", 0) or 0),
            salience=float(self._get(raw, "salience", 0.5) or 0.5),
            source_refs=list(self._get(raw, "source_refs", []) or []),
            metadata=dict(self._get(raw, "metadata", {}) or {}),
        )
