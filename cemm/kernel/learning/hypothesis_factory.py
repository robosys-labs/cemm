"""HypothesisFactory — generates competing schema hypotheses.

Import boundary: model + schema submodules only. No engine, commit, or persistence imports.

Architectural guardrails (AGENTS.md §7.2, LEARNING_PIPELINE.md §1-2, §15):
- The learning transaction receives grounded propositions and evidence
  records, never copied free-text fields as semantic authority.
- Not every teaching-looking utterance defines a concept.
- Hypothesis kinds: alias, new_sense, specialization, correction
- New incompatible evidence creates a candidate sense or ambiguity set
  unless correction is explicit.
- Alias/synonym/translation hypotheses compete with new-schema and
  specialization hypotheses.
- No hypothesis is silently rewritten as user teaching.
- Induced patterns alone never activate a definition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.learning import SchemaHypothesis
from ..model.gap import GapRecord
from ..schema.provenance import ProvenanceKind, ContributionRecord


class HypothesisKind(str, Enum):
    """Kinds of schema hypotheses that compete."""
    ALIAS = "alias"                # existing sense, new lexical form
    NEW_SENSE = "new_sense"        # new sense for known lexical form
    SPECIALIZATION = "specialization"  # refinement/subtype of existing schema
    CORRECTION = "correction"      # explicit correction of existing schema
    NONE = "none"                  # instance fact or relation — no hypothesis needed


@dataclass(frozen=True, slots=True)
class EvidenceForHypothesis:
    """Evidence supporting a hypothesis."""
    evidence_ref: str
    proposition_ref: str
    supports_hypothesis_kind: HypothesisKind
    confidence: float = 0.0
    is_independent: bool = False
    provenance_kind: ProvenanceKind = ProvenanceKind.HYPOTHESIZED
    context_ref: str = ""


@dataclass(frozen=True, slots=True)
class CompetingHypotheses:
    """A set of competing hypotheses for a target sense/schema.

    Alias/synonym/translation hypotheses compete with new-schema and
    specialization hypotheses. Correction is separate — it requires
    explicit evidence of error.
    """
    target_sense_ref: str
    target_schema_ref: str
    hypotheses: tuple[SchemaHypothesis, ...] = ()
    evidence: tuple[EvidenceForHypothesis, ...] = ()
    is_correction_explicit: bool = False

    def competing_kinds(self) -> frozenset[str]:
        """Get the set of competing hypothesis kinds."""
        return frozenset(h.hypothesis_kind for h in self.hypotheses)

    def has_competition(self) -> bool:
        """Check if multiple hypotheses compete."""
        return len(self.hypotheses) > 1

    def correction_hypotheses(self) -> tuple[SchemaHypothesis, ...]:
        """Get only correction hypotheses."""
        return tuple(h for h in self.hypotheses if h.hypothesis_kind == "correction")

    def non_correction_hypotheses(self) -> tuple[SchemaHypothesis, ...]:
        """Get non-correction hypotheses (alias, new_sense, specialization)."""
        return tuple(h for h in self.hypotheses if h.hypothesis_kind != "correction")


class HypothesisFactory:
    """Generates competing schema hypotheses from evidence.

    The factory receives grounded propositions and evidence records,
    never copied free-text fields as semantic authority.

    Not every teaching-looking utterance defines a concept. The factory
    classifies what kind of learning evidence supports:
    - instance fact (no hypothesis needed)
    - relation between existing schemas (no hypothesis needed)
    - lexeme-to-schema binding → alias hypothesis
    - partial definition → specialization hypothesis
    - complete compositional definition → new_sense hypothesis
    - correction or counterexample → correction hypothesis
    - source retraction → correction (retraction)
    - permission change → no hypothesis
    """

    def generate(
        self,
        gap: GapRecord,
        evidence: tuple[EvidenceForHypothesis, ...] = (),
        is_correction_explicit: bool = False,
    ) -> CompetingHypotheses:
        """Generate competing hypotheses from evidence for a gap.

        Alias/synonym/translation hypotheses compete with new-schema
        and specialization hypotheses.
        """
        hypotheses: list[SchemaHypothesis] = []

        # Group evidence by hypothesis kind
        kind_evidence: dict[HypothesisKind, list[EvidenceForHypothesis]] = {}
        for ev in evidence:
            kind = ev.supports_hypothesis_kind
            kind_evidence.setdefault(kind, []).append(ev)

        # If correction is explicit, generate correction hypothesis
        if is_correction_explicit:
            corr_ev = kind_evidence.get(HypothesisKind.CORRECTION, [])
            if corr_ev:
                confidence = max(ev.confidence for ev in corr_ev)
                hypotheses.append(SchemaHypothesis(
                    hypothesis_kind=HypothesisKind.CORRECTION.value,
                    target_sense_ref=gap.target_artifact_ref,
                    proposed_revision_ref="",
                    confidence=confidence,
                ))
            return CompetingHypotheses(
                target_sense_ref=gap.target_artifact_ref,
                target_schema_ref=gap.target_artifact_ref,
                hypotheses=tuple(hypotheses),
                evidence=evidence,
                is_correction_explicit=True,
            )

        # Non-correction hypotheses compete
        for kind, evs in kind_evidence.items():
            if kind == HypothesisKind.CORRECTION:
                continue  # Only explicit correction
            if kind == HypothesisKind.NONE:
                continue  # Instance facts don't generate hypotheses

            confidence = max(ev.confidence for ev in evs) if evs else 0.0
            hypotheses.append(SchemaHypothesis(
                hypothesis_kind=kind.value,
                target_sense_ref=gap.target_artifact_ref,
                proposed_revision_ref="",
                confidence=confidence,
            ))

        return CompetingHypotheses(
            target_sense_ref=gap.target_artifact_ref,
            target_schema_ref=gap.target_artifact_ref,
            hypotheses=tuple(hypotheses),
            evidence=evidence,
            is_correction_explicit=False,
        )

    def classify_evidence(
        self,
        proposition_ref: str,
        evidence_ref: str,
        is_new_lexical_binding: bool = False,
        is_new_sense_evidence: bool = False,
        is_specialization: bool = False,
        is_correction: bool = False,
        confidence: float = 0.0,
        is_independent: bool = False,
        context_ref: str = "",
    ) -> EvidenceForHypothesis:
        """Classify what kind of hypothesis evidence supports.

        Not every teaching-looking utterance defines a concept.
        This method determines which hypothesis kind the evidence supports.
        """
        if is_correction:
            kind = HypothesisKind.CORRECTION
            provenance = ProvenanceKind.ASSERTED
        elif is_new_lexical_binding:
            kind = HypothesisKind.ALIAS
            provenance = ProvenanceKind.OBSERVED
        elif is_new_sense_evidence:
            kind = HypothesisKind.NEW_SENSE
            provenance = ProvenanceKind.INDUCED
        elif is_specialization:
            kind = HypothesisKind.SPECIALIZATION
            provenance = ProvenanceKind.INDUCED
        else:
            # Instance fact or relation — no hypothesis needed
            kind = HypothesisKind.NONE
            provenance = ProvenanceKind.OBSERVED

        return EvidenceForHypothesis(
            evidence_ref=evidence_ref,
            proposition_ref=proposition_ref,
            supports_hypothesis_kind=kind,
            confidence=confidence,
            is_independent=is_independent,
            provenance_kind=provenance,
            context_ref=context_ref,
        )
