"""EvidenceRecord — evidence with lineage and independence tracking.

Import boundary: standard library only → refs, identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .identity import TimeExtent, Provenance, Permission, Scope


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Evidence record with full lineage and independence metadata.

    Evidence independence follows derivation lineage, not record count
    or source labels. Translations, paraphrases, summaries, generated
    examples, and retrieved copies inherit their root lineage unless an
    independent observation or oracle exists.
    """
    id: str
    evidence_kind: str = "observation"
    target_refs: tuple[str, ...] = ()
    stance: str = "supports"  # supports, opposes, observes, defines, corrects, retracts
    source_ref: str | None = None  # Ref[Referent]
    signal_ref: str | None = None  # Ref[SignalEnvelope]
    derivation_parent_refs: tuple[str, ...] = ()
    lineage_root_refs: tuple[str, ...] = ()
    transformation_kind: str | None = None  # translation, paraphrase, summary, generation, retrieval-copy
    independence_cluster: str = ""
    provenance_kind: str = "asserted"  # asserted, observed, entailed, inherited, hypothesized, etc.
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    valid_time: TimeExtent | None = None
    confidence: float = 0.0
    permission: Permission = field(default_factory=Permission.public)
    scope: Scope = field(default_factory=Scope)
    context_refs: tuple[str, ...] = ()
    support_status: str = "active"  # active, retracted, archived, privacy_deleted
