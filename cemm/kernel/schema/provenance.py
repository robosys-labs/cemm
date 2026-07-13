"""Field-level provenance — ContributionRecord tracking per-field provenance kind.

Import boundary: model submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7.3):
- Every learned schema field or pattern records whether it was:
    asserted, observed, entailed, inherited, hypothesized, defaulted,
    induced, adapter-supplied, boot-supplied
- Hypothesized/defaulted content may guide candidate ranking and probing.
  It may not be presented as user-taught or observed truth.
- Competence cases derived from the definition may test well-formedness
  only. They cannot independently certify discrimination, truth, or
  promotion.
- Evidence independence follows derivation lineage, not record count or
  source labels. Translations, paraphrases, summaries, generated examples,
  and retrieved copies inherit their root lineage unless an independent
  observation or oracle exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone


class ProvenanceKind(str, Enum):
    """How a schema field or pattern was derived.

    Ordered from most authoritative to least:
    - ASSERTED: explicitly stated by a source
    - OBSERVED: independently observed
    - ENTAILED: logically derived from other grounded fields
    - INHERITED: derived from a parent schema
    - INDUCED: induced from multiple examples
    - ADAPTER_SUPPLIED: provided by a language adapter (candidate only)
    - BOOT_SUPPLIED: provided by boot schemas
    - HYPOTHESIZED: hypothesized from partial evidence
    - DEFAULTED: filled with a default value
    """
    ASSERTED = "asserted"
    OBSERVED = "observed"
    ENTAILED = "entailed"
    INHERITED = "inherited"
    INDUCED = "induced"
    ADAPTER_SUPPLIED = "adapter-supplied"
    BOOT_SUPPLIED = "boot-supplied"
    HYPOTHESIZED = "hypothesized"
    DEFAULTED = "defaulted"


# Fields that can guide ranking/probing but cannot be presented as truth
WEAK_PROVENANCE = frozenset({
    ProvenanceKind.HYPOTHESIZED,
    ProvenanceKind.DEFAULTED,
})

# Fields that come from adapters — candidate evidence only
ADAPTER_PROVENANCE = frozenset({
    ProvenanceKind.ADAPTER_SUPPLIED,
})

# Fields that are independently grounded
INDEPENDENT_PROVENANCE = frozenset({
    ProvenanceKind.ASSERTED,
    ProvenanceKind.OBSERVED,
})

# Fields derived from other grounded fields
DERIVED_PROVENANCE = frozenset({
    ProvenanceKind.ENTAILED,
    ProvenanceKind.INHERITED,
    ProvenanceKind.INDUCED,
    ProvenanceKind.BOOT_SUPPLIED,
})


@dataclass(frozen=True, slots=True)
class ContributionRecord:
    """A field-level contribution with provenance.

    Every learned schema field or pattern records its provenance kind,
    source reference, confidence, and whether it counts as independent
    evidence.

    Hypothesized/defaulted content may guide candidate ranking and
    probing. It may not be presented as user-taught or observed truth.
    """
    field_name: str
    provenance_kind: ProvenanceKind
    source_ref: str = ""  # Ref[Referent | EvidenceRecord | SchemaEnvelope]
    confidence: float = 0.0
    is_independent: bool = False
    derivation_lineage: tuple[str, ...] = ()  # chain of source_refs
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def is_weak(self) -> bool:
        """Whether this contribution is weak (hypothesized/defaulted).

        Weak contributions can guide ranking but cannot be presented
        as user-taught or observed truth.
        """
        return self.provenance_kind in WEAK_PROVENANCE

    @property
    def is_adapter_supplied(self) -> bool:
        """Whether this contribution comes from a language adapter."""
        return self.provenance_kind in ADAPTER_PROVENANCE

    @property
    def can_certify_truth(self) -> bool:
        """Whether this contribution can certify truth or discrimination.

        Only independently observed or asserted contributions can
        certify truth. Derived contributions (entailed, inherited,
        induced) follow their source lineage. Weak contributions
        (hypothesized, defaulted) cannot certify anything.
        """
        return self.provenance_kind in INDEPENDENT_PROVENANCE and self.is_independent

    @property
    def lineage_root(self) -> str:
        """The root source of this contribution's lineage.

        If derivation_lineage is non-empty, the root is the first entry.
        Otherwise, it's the source_ref.
        """
        if self.derivation_lineage:
            return self.derivation_lineage[0]
        return self.source_ref


@dataclass(frozen=True, slots=True)
class FieldProvenanceMap:
    """A collection of contribution records for a schema.

    Maps field names to their contribution records. A field may have
    multiple contributions from different sources.
    """
    contributions: tuple[ContributionRecord, ...] = ()

    def contributions_for(self, field_name: str) -> tuple[ContributionRecord, ...]:
        """Get all contributions for a specific field."""
        return tuple(c for c in self.contributions if c.field_name == field_name)

    def field_names(self) -> frozenset[str]:
        """Get all field names that have contributions."""
        return frozenset(c.field_name for c in self.contributions)

    def has_independent_evidence(self, field_name: str) -> bool:
        """Check if a field has at least one independent contribution."""
        return any(
            c.is_independent and c.provenance_kind in INDEPENDENT_PROVENANCE
            for c in self.contributions_for(field_name)
        )

    def has_weak_only(self, field_name: str) -> bool:
        """Check if a field has only weak (hypothesized/defaulted) contributions."""
        contribs = self.contributions_for(field_name)
        if not contribs:
            return True
        return all(c.is_weak for c in contribs)

    def independent_lineage_roots(self) -> frozenset[str]:
        """Get the set of independent lineage roots across all contributions."""
        return frozenset(
            c.lineage_root for c in self.contributions
            if c.is_independent and c.provenance_kind in INDEPENDENT_PROVENANCE
        )

    def can_self_certify(self, field_name: str, implementation_path: str) -> bool:
        """Check if a field's contributions would constitute self-certification.

        The same implementation path cannot generate input meaning,
        expected graph, and pass judgment without an independent
        invariant. If all contributions for a field share the same
        source as the implementation path, it's self-certification.
        """
        contribs = self.contributions_for(field_name)
        if not contribs:
            return False
        # If all contributions come from the same source as the implementation path
        independent = [
            c for c in contribs
            if c.is_independent and c.lineage_root != implementation_path
        ]
        return len(independent) == 0
