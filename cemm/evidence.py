"""Cycle-local evidence envelopes; observations are not propositions by default."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping
from cemm.model import now, stable


@dataclass(frozen=True)
class EvidenceEnvelope:
    evidence_ref: str
    modality: str
    source_ref: str
    observed_at: str
    payload: Any
    confidence: float = 1.0
    permission_scope: str | None = None
    lineage: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def text(cls, text: str, source_ref: str, *, language: str, channel: str, permission_scope=None):
        observed_at = now()
        payload = {"text": text, "language": language, "channel": channel}
        return cls(
            stable("evidence", "text", source_ref, observed_at, payload),
            "language",
            source_ref,
            observed_at,
            payload,
            1.0,
            permission_scope,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_ref": self.evidence_ref,
            "modality": self.modality,
            "source_ref": self.source_ref,
            "observed_at": self.observed_at,
            "payload": self.payload,
            "confidence": self.confidence,
            "permission_scope": self.permission_scope,
            "lineage": list(self.lineage),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EvidenceLattice:
    envelopes: tuple[EvidenceEnvelope, ...]
    form_evidence: Mapping[str, Any]
    unknown_evidence: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "envelopes": [x.as_dict() for x in self.envelopes],
            "form_evidence": dict(self.form_evidence),
            "unknown_evidence": list(self.unknown_evidence),
        }
