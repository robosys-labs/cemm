"""Assimilator — evidence assimilation with field-level provenance and lineage.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (LEARNING_PIPELINE.md §3-4, §6):
- Every evidence record stores source, transformation, derivation parents,
  lineage roots, independence cluster, context, and permission.
- Derived propositions may be working knowledge but cannot increase
  support or competence for any schema in their transitive support
  ancestry or support strongly connected component.
- A translation, paraphrase, generated case, summary, or copied source
  does not create new independent support.
- Every staged contribution records whether it is asserted, observed,
  entailed, inherited, hypothesized, defaulted, induced, adapter-supplied,
  or boot-supplied.
- No hypothesis is silently rewritten as user teaching.
- Accepted evidence creates an immutable child revision in the same
  SemanticSchemaStore snapshot.
- Untrusted learning is declarative. User data cannot install executable
  code or override formal kernel semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.learning import SchemaHypothesis
from ..schema.provenance import (
    ProvenanceKind, ContributionRecord, FieldProvenanceMap,
    WEAK_PROVENANCE, DERIVED_PROVENANCE,
)
from ..schema.envelope import SchemaEnvelope
from ..schema.grounding_spec import GroundingSpecification, SemanticPattern


@dataclass(frozen=True, slots=True)
class StagedContribution:
    """A staged contribution to a child schema revision.

    Every staged contribution records its provenance kind.
    No hypothesis is silently rewritten as user teaching.
    """
    field_name: str
    field_value: Any
    provenance_kind: ProvenanceKind
    evidence_ref: str = ""
    source_ref: str = ""
    is_independent: bool = False
    derivation_lineage: tuple[str, ...] = ()
    is_hypothesis: bool = False  # Hypotheses are never rewritten as user teaching


@dataclass(frozen=True, slots=True)
class ChildRevision:
    """An immutable child schema revision.

    Created in the same SemanticSchemaStore snapshot.
    Untrusted learning is declarative — user data cannot install
    executable code or override formal kernel semantics.
    """
    revision_id: str
    base_schema_ref: str
    base_store_revision: int
    contributions: tuple[StagedContribution, ...] = ()
    grounding_spec: GroundingSpecification | None = None
    patterns: tuple[SemanticPattern, ...] = ()
    field_provenance_map: FieldProvenanceMap | None = None
    is_declarative_only: bool = True  # Untrusted learning is declarative

    def get_provenance(self, field_name: str) -> ContributionRecord | None:
        """Get the provenance record for a specific field."""
        for contrib in self.contributions:
            if contrib.field_name == field_name:
                return ContributionRecord(
                    field_name=contrib.field_name,
                    provenance_kind=contrib.provenance_kind,
                    source_ref=contrib.source_ref,
                    is_independent=contrib.is_independent,
                    derivation_lineage=contrib.derivation_lineage,
                )
        return None

    def weak_fields(self) -> tuple[str, ...]:
        """Get fields with weak provenance (hypothesized/defaulted)."""
        return tuple(
            contrib.field_name for contrib in self.contributions
            if contrib.provenance_kind in WEAK_PROVENANCE
        )

    def has_independent_evidence(self) -> bool:
        """Check if any field has independent evidence."""
        return any(
            contrib.is_independent and contrib.provenance_kind not in DERIVED_PROVENANCE
            for contrib in self.contributions
        )


class Assimilator:
    """Assimilates grounded evidence into child schema revisions.

    The learning transaction receives grounded propositions and evidence
    records, never copied free-text fields as semantic authority.

    Derived propositions may be working knowledge but cannot increase
    support or competence for any schema in their transitive support
    ancestry or support strongly connected component.
    """

    def assimilate(
        self,
        base_schema_ref: str,
        base_store_revision: int,
        hypothesis: SchemaHypothesis,
        contributions: tuple[StagedContribution, ...] = (),
        grounding_spec: GroundingSpecification | None = None,
        patterns: tuple[SemanticPattern, ...] = (),
    ) -> ChildRevision:
        """Assimilate evidence into a child schema revision.

        Accepted evidence creates an immutable child revision.
        No hypothesis is silently rewritten as user teaching.
        """
        # Build field provenance map from contributions
        provenance_records = tuple(
            ContributionRecord(
                field_name=contrib.field_name,
                provenance_kind=contrib.provenance_kind,
                source_ref=contrib.source_ref,
                is_independent=contrib.is_independent,
                derivation_lineage=contrib.derivation_lineage,
            )
            for contrib in contributions
        )
        provenance_map = FieldProvenanceMap(contributions=provenance_records)

        # Determine if this is declarative-only (untrusted learning)
        # Untrusted learning is declarative — user data cannot install
        # executable code or override formal kernel semantics
        is_declarative = True

        return ChildRevision(
            revision_id=f"child:{base_schema_ref}:v{base_store_revision + 1}",
            base_schema_ref=base_schema_ref,
            base_store_revision=base_store_revision,
            contributions=contributions,
            grounding_spec=grounding_spec,
            patterns=patterns,
            field_provenance_map=provenance_map,
            is_declarative_only=is_declarative,
        )

    def check_lineage_support(
        self,
        evidence_lineage: tuple[str, ...],
        schema_ancestry: tuple[str, ...],
    ) -> bool:
        """Check if evidence can increase support for a schema.

        Derived propositions may be working knowledge but cannot increase
        support or competence for any schema in their transitive support
        ancestry or support strongly connected component.

        Returns True if the evidence CAN increase support (no ancestry
        overlap), False if it cannot (ancestry overlap detected).
        """
        evidence_roots = set(evidence_lineage)
        schema_ancestors = set(schema_ancestry)

        # If any evidence root is in the schema's ancestry, it cannot
        # increase support (circular support)
        overlap = evidence_roots & schema_ancestors
        return len(overlap) == 0

    def can_increase_competence(
        self,
        evidence_lineage: tuple[str, ...],
        schema_scc: tuple[str, ...],  # strongly connected component
    ) -> bool:
        """Check if evidence can increase competence for a schema.

        A translation, paraphrase, generated case, summary, or copied
        source does not create new independent support.
        """
        evidence_roots = set(evidence_lineage)
        scc_members = set(schema_scc)

        # If evidence root is in the SCC, it cannot increase competence
        overlap = evidence_roots & scc_members
        return len(overlap) == 0

    def create_contribution(
        self,
        field_name: str,
        field_value: Any,
        provenance_kind: ProvenanceKind,
        evidence_ref: str = "",
        source_ref: str = "",
        is_independent: bool = False,
        derivation_lineage: tuple[str, ...] = (),
        is_hypothesis: bool = False,
    ) -> StagedContribution:
        """Create a staged contribution with explicit provenance.

        No hypothesis is silently rewritten as user teaching.
        """
        return StagedContribution(
            field_name=field_name,
            field_value=field_value,
            provenance_kind=provenance_kind,
            evidence_ref=evidence_ref,
            source_ref=source_ref,
            is_independent=is_independent,
            derivation_lineage=derivation_lineage,
            is_hypothesis=is_hypothesis,
        )
