"""SemanticGraph — aggregate view of canonical semantic graph records.

Import boundary: standard library only → refs, referent, value, predication,
proposition, context_frame, evidence, structural_link.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .referent import Referent
from .value import Value
from .predication import Predication
from .proposition import Proposition
from .context_frame import ContextFrame
from .evidence import EvidenceRecord
from .structural_link import StructuralLink


@dataclass(frozen=True, slots=True)
class SemanticGraph:
    """Immutable snapshot of canonical semantic graph records.

    This is a read-only aggregate view — it does not create a second
    ontology or store. Engines consume snapshots for read access.
    """
    referents: tuple[Referent, ...] = ()
    values: tuple[Value, ...] = ()
    predications: tuple[Predication, ...] = ()
    propositions: tuple[Proposition, ...] = ()
    context_frames: tuple[ContextFrame, ...] = ()
    evidence_records: tuple[EvidenceRecord, ...] = ()
    structural_links: tuple[StructuralLink, ...] = ()
