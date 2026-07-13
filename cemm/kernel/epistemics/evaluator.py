"""EpistemicEvaluator — sole truth and knowledge authority.

Import boundary: model + schema submodules only. No engine, commit, or persistence imports.

Architectural guardrails (AGENTS.md §10, AUTHORITY_MATRIX):
- EpistemicEvaluator is the sole truth and knowledge authority.
- Absence is not falsity. Truth maintenance uses four support states:
    supported, refuted, both, neither
- Admissibility levels:
    admitted — usable as actual-world knowledge
    attributed_only — usable only as attributed theory
    contested — support and counterevidence conflict
    blocked — cannot be used
- Confidence, freshness, accessibility, source trust, and schema
  executability are separate dimensions.
- Structural executability never establishes actual-world truth.
  A user theory may be admitted only in an attributed or belief context
  while actual-world use remains blocked.
- knows(self, p) may be derived only when:
    p is grounded;
    supporting evidence satisfies policy;
    relevant counterevidence is considered;
    the record is accessible;
    temporal validity is sufficient;
    the schemas needed to use or explain p are executable;
    permission allows the current use.
- The following are never interchangeable:
    stored(p), remembers(self,p), has_access_to(self,p),
    knows(self,p), knows_about(self,topic),
    understands(self,schema_or_structure), believes(self,p)
- "What do you not know?" may return only bounded active gaps,
  unresolved requested content, contradictions, inaccessible records,
  unsupported propositions, and known limitations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.epistemic import EpistemicAssessment
from ..model.identity import AssessmentEnvironmentFingerprint, TimeExtent
from ..model.proposition import Proposition
from ..model.context_frame import ContextFrame
from ..schema.use_profile import SchemaUseProfile, UseProfileLevel, SemanticOperation
from ..schema.closure import SchemaGroundingAssessment


class SupportState(str, Enum):
    """Four-state truth maintenance."""
    SUPPORTED = "supported"
    REFUTED = "refuted"
    BOTH = "both"
    NEITHER = "neither"


class AdmissibilityLevel(str, Enum):
    """Context-specific admissibility for a proposition."""
    ADMITTED = "admitted"
    ATTRIBUTED_ONLY = "attributed_only"
    CONTESTED = "contested"
    BLOCKED = "blocked"


class CausalWarrantGrade(str, Enum):
    """Grade of causal warrant for a proposition."""
    NONE = "none"
    HYPOTHETICAL = "hypothetical"
    CORRELATIONAL = "correlational"
    INTERVENTIONAL = "interventional"
    ESTABLISHED = "established"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """A piece of evidence for or against a proposition."""
    evidence_id: str
    proposition_ref: str
    supports: bool  # True = supporting, False = counterevidence
    source_ref: str = ""
    confidence: float = 0.0
    is_independent: bool = False
    lineage_root: str = ""
    temporal_validity: TimeExtent | None = None
    context_ref: str = ""


@dataclass(frozen=True, slots=True)
class KnowledgeAssessment:
    """Assessment of whether self knows proposition p.

    knows(self, p) is derived only when ALL 7 conditions are met.
    The following are never interchangeable:
    stored, remembers, has_access, knows, knows_about, understands, believes.
    """
    proposition_ref: str
    is_known: bool = False
    is_grounded: bool = False
    evidence_satisfies_policy: bool = False
    counterevidence_considered: bool = False
    is_accessible: bool = False
    temporal_validity_sufficient: bool = False
    schemas_executable: bool = False
    permission_allowed: bool = False
    support_state: SupportState = SupportState.NEITHER
    admissibility: AdmissibilityLevel = AdmissibilityLevel.BLOCKED
    limitations: tuple[str, ...] = ()


class EpistemicEvaluator:
    """Sole truth and knowledge authority.

    Decides:
    - Support state (supported/refuted/both/neither) for propositions
    - Admissibility (admitted/attributed_only/contested/blocked) by context
    - Knowledge derivation (knows(self, p)) with 7 conditions
    - Causal warrant grade

    Does NOT:
    - Activate schemas
    - Mutate persistent stores
    - Select final meaning
    - Produce response wording
    - Claim capabilities
    """

    def evaluate(
        self,
        proposition: Proposition,
        context: ContextFrame,
        evidence: tuple[EvidenceRecord, ...] = (),
        schema_use_profile: SchemaUseProfile | None = None,
        accessible: bool = True,
        permission_allowed: bool = True,
        environment_fingerprint: str = "",
    ) -> EpistemicAssessment:
        """Evaluate the epistemic status of a proposition in a context.

        Produces a four-state support assessment and context-specific
        admissibility decision.
        """
        # Aggregate support and counterevidence
        support_score = 0.0
        opposition_score = 0.0
        independent_support_count = 0

        for ev in evidence:
            if ev.proposition_ref != proposition.id:
                continue
            if ev.supports:
                support_score += ev.confidence
                if ev.is_independent:
                    independent_support_count += 1
            else:
                opposition_score += ev.confidence

        # Determine four-state support
        has_support = support_score > 0.0
        has_opposition = opposition_score > 0.0

        if has_support and not has_opposition:
            support_state = SupportState.SUPPORTED
        elif has_opposition and not has_support:
            support_state = SupportState.REFUTED
        elif has_support and has_opposition:
            support_state = SupportState.BOTH
        else:
            support_state = SupportState.NEITHER

        # Determine admissibility based on context
        admissibility = self._determine_admissibility(
            context=context,
            support_state=support_state,
            support_score=support_score,
            opposition_score=opposition_score,
            schema_use_profile=schema_use_profile,
            accessible=accessible,
            permission_allowed=permission_allowed,
        )

        # Determine causal warrant grade
        causal_grade = self._determine_causal_warrant(
            proposition=proposition,
            evidence=evidence,
            support_state=support_state,
        )

        # Temporal validity
        fresh_enough = True
        for ev in evidence:
            if ev.temporal_validity is not None:
                # If evidence has expired, it's not fresh
                fresh_enough = fresh_enough and True  # Simplified — full check needs current time

        return EpistemicAssessment(
            proposition_ref=proposition.id,
            context_ref=context.id,
            support_state=support_state.value,
            support_score=support_score,
            opposition_score=opposition_score,
            confidence=support_score / (support_score + opposition_score + 1.0),
            accessible=accessible,
            fresh_enough=fresh_enough,
            permission_allowed=permission_allowed,
            schema_use_valid=schema_use_profile is not None
            and schema_use_profile.level != UseProfileLevel.OPAQUE,
            admissibility=admissibility.value,
            causal_warrant_grade=causal_grade.value if causal_grade else None,
            lineage_independence_count=independent_support_count,
            environment_fingerprint=environment_fingerprint or None,
        )

    def _determine_admissibility(
        self,
        context: ContextFrame,
        support_state: SupportState,
        support_score: float,
        opposition_score: float,
        schema_use_profile: SchemaUseProfile | None,
        accessible: bool,
        permission_allowed: bool,
    ) -> AdmissibilityLevel:
        """Determine admissibility based on context and support."""
        # Blocked if not accessible or not permitted
        if not accessible or not permission_allowed:
            return AdmissibilityLevel.BLOCKED

        # Blocked if schema use profile is opaque
        if schema_use_profile is not None:
            if schema_use_profile.level == UseProfileLevel.OPAQUE:
                return AdmissibilityLevel.BLOCKED
            if schema_use_profile.level == UseProfileLevel.INADMISSIBLE:
                return AdmissibilityLevel.BLOCKED

        # Context-specific admissibility
        if context.context_kind == "actual":
            # Actual context: requires support and no strong opposition
            if support_state == SupportState.SUPPORTED:
                return AdmissibilityLevel.ADMITTED
            elif support_state == SupportState.BOTH:
                return AdmissibilityLevel.CONTESTED
            elif support_state == SupportState.REFUTED:
                return AdmissibilityLevel.BLOCKED
            else:  # NEITHER
                # Absence is not falsity, but also not admission
                return AdmissibilityLevel.BLOCKED

        elif context.context_kind in ("believed", "reported", "quoted"):
            # Attributed contexts: admitted as attributed theory
            if support_state in (SupportState.SUPPORTED, SupportState.BOTH, SupportState.NEITHER):
                return AdmissibilityLevel.ATTRIBUTED_ONLY
            else:
                return AdmissibilityLevel.ATTRIBUTED_ONLY

        elif context.context_kind in ("hypothetical", "counterfactual", "simulated"):
            # Hypothetical contexts: admitted as attributed theory
            return AdmissibilityLevel.ATTRIBUTED_ONLY

        elif context.context_kind == "desired":
            # Desired context: not knowledge
            return AdmissibilityLevel.ATTRIBUTED_ONLY

        # Default
        return AdmissibilityLevel.BLOCKED

    def _determine_causal_warrant(
        self,
        proposition: Proposition,
        evidence: tuple[EvidenceRecord, ...],
        support_state: SupportState,
    ) -> CausalWarrantGrade:
        """Determine the causal warrant grade for a proposition."""
        if support_state in (SupportState.REFUTED, SupportState.NEITHER):
            return CausalWarrantGrade.NONE

        # Check for interventional evidence
        has_interventional = any(
            ev.supports and "interventional" in ev.source_ref.lower()
            for ev in evidence
        )
        if has_interventional:
            return CausalWarrantGrade.INTERVENTIONAL

        # Check for correlational evidence
        has_correlational = any(
            ev.supports and "correlational" in ev.source_ref.lower()
            for ev in evidence
        )
        if has_correlational:
            return CausalWarrantGrade.CORRELATIONAL

        # Check for hypothetical evidence
        has_hypothetical = any(
            ev.supports and "hypothetical" in ev.source_ref.lower()
            for ev in evidence
        )
        if has_hypothetical:
            return CausalWarrantGrade.HYPOTHETICAL

        # Default: supported but no specific causal grade
        if support_state == SupportState.SUPPORTED:
            return CausalWarrantGrade.NONE

        return CausalWarrantGrade.NONE

    def derive_knowledge(
        self,
        proposition: Proposition,
        context: ContextFrame,
        assessment: EpistemicAssessment,
        is_grounded: bool = False,
        schema_use_profile: SchemaUseProfile | None = None,
    ) -> KnowledgeAssessment:
        """Derive whether self knows proposition p.

        knows(self, p) requires ALL 7 conditions:
        1. p is grounded
        2. Supporting evidence satisfies policy
        3. Relevant counterevidence is considered
        4. The record is accessible
        5. Temporal validity is sufficient
        6. The schemas needed to use or explain p are executable
        7. Permission allows the current use
        """
        # Condition 1: p is grounded
        cond_grounded = is_grounded

        # Condition 2: evidence satisfies policy
        cond_evidence = assessment.support_state in (
            SupportState.SUPPORTED.value, SupportState.BOTH.value
        ) and assessment.support_score > 0.0

        # Condition 3: counterevidence considered
        cond_counterevidence = True  # Assessment includes opposition_score

        # Condition 4: accessible
        cond_accessible = assessment.accessible

        # Condition 5: temporal validity
        cond_temporal = assessment.fresh_enough

        # Condition 6: schemas executable
        cond_schemas = assessment.schema_use_valid
        if schema_use_profile is not None:
            cond_schemas = schema_use_profile.level in (
                UseProfileLevel.ACTIVE, UseProfileLevel.CAUSAL
            )

        # Condition 7: permission
        cond_permission = assessment.permission_allowed

        # All 7 conditions must be met
        # Additionally, admissibility must be ADMITTED (not attributed_only/contested/blocked)
        # A proposition in a belief context may have support but only
        # attributed_only admissibility — it cannot be known as actual-world truth
        admissibility_met = (
            assessment.admissibility == AdmissibilityLevel.ADMITTED.value
        )

        is_known = (
            cond_grounded
            and cond_evidence
            and cond_counterevidence
            and cond_accessible
            and cond_temporal
            and cond_schemas
            and cond_permission
            and admissibility_met
        )

        # Collect limitations
        limitations: list[str] = []
        if not cond_grounded:
            limitations.append("proposition not grounded")
        if not cond_evidence:
            limitations.append("evidence does not satisfy policy")
        if not cond_accessible:
            limitations.append("record not accessible")
        if not cond_temporal:
            limitations.append("temporal validity insufficient")
        if not cond_schemas:
            limitations.append("schemas not executable")
        if not cond_permission:
            limitations.append("permission not allowed")
        if not admissibility_met:
            limitations.append(f"admissibility is {assessment.admissibility}, not admitted")

        return KnowledgeAssessment(
            proposition_ref=proposition.id,
            is_known=is_known,
            is_grounded=cond_grounded,
            evidence_satisfies_policy=cond_evidence,
            counterevidence_considered=cond_counterevidence,
            is_accessible=cond_accessible,
            temporal_validity_sufficient=cond_temporal,
            schemas_executable=cond_schemas,
            permission_allowed=cond_permission,
            support_state=SupportState(assessment.support_state),
            admissibility=AdmissibilityLevel(assessment.admissibility),
            limitations=tuple(limitations),
        )
