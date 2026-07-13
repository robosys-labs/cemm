"""Knowledge derivation — distinguishes stored/remembers/has_access/knows/understands/believes.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §10):
- The following are NEVER interchangeable:
    stored(p)       — a persistent record exists
    remembers(self, p) — a relevant stored trace was successfully retrieved
    has_access_to(self, p) — current retrieval, permission, and resources allow access
    knows(self, p)  — epistemic criteria are satisfied
    knows_about(self, topic) — has knowledge about a topic
    understands(self, schema_or_structure) — executable schemas can operate over x
    believes(self, p) — proposition is held in a belief context
- knows(self, p) requires ALL 7 conditions
- "What do you not know?" returns only bounded active gaps, unresolved
  requested content, contradictions, inaccessible records, unsupported
  propositions, and known limitations
- An unbacked epistemic clause is a realization error
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.epistemic import EpistemicAssessment
from ..model.proposition import Proposition
from ..model.context_frame import ContextFrame
from ..schema.use_profile import SchemaUseProfile, UseProfileLevel
from .evaluator import (
    EpistemicEvaluator, KnowledgeAssessment, SupportState, AdmissibilityLevel,
)


@dataclass(frozen=True, slots=True)
class UnderstandingAssessment:
    """Assessment of whether self understands a schema or structure.

    understands(self, schema_or_structure) is operation-relative.
    It states exact supported competencies and limitations.

    A known lexeme or schema ref does not imply understanding.
    """
    schema_record_ref: str
    is_understood: bool = False
    supported_operations: tuple[str, ...] = ()
    unsupported_operations: tuple[str, ...] = ()
    competence_level: str = "none"  # none, opaque, partial, active, causal
    exact_competencies: tuple[str, ...] = ()
    exact_limitations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def describe(self) -> str:
        """Human-readable description of understanding state."""
        if not self.is_understood:
            return f"I do not currently understand {self.schema_record_ref}"
        parts = [f"I can operate on {self.schema_record_ref} at {self.competence_level} level."]
        if self.exact_competencies:
            parts.append("Supported: " + ", ".join(self.exact_competencies))
        if self.exact_limitations:
            parts.append("Limitations: " + ", ".join(self.exact_limitations))
        return " ".join(parts)


@dataclass(frozen=True, slots=True)
class BeliefAssessment:
    """Assessment of whether self believes proposition p.

    believes(self, p) holds a proposition in a belief context.
    This is distinct from knows(self, p) — belief does not require
    the full 7 epistemic conditions.
    """
    proposition_ref: str
    is_believed: bool = False
    belief_context_ref: str = ""
    confidence: float = 0.0
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelfReport:
    """Evidence-bound self-report.

    Self-report queries use ordinary semantic retrieval over:
    - remembered proposition
    - schema grounding assessment
    - competence results
    - admissibility assessment
    - current blockers
    - capability/component evidence

    An unbacked epistemic clause is a realization error.
    """
    report_kind: str  # "knows", "understands", "remembers", "believes", "can_do"
    proposition_ref: str = ""
    schema_ref: str = ""
    is_true: bool = False
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    is_backed: bool = False  # Must be True — unbacked is a realization error

    def assert_backed(self) -> None:
        """Assert that this self-report is evidence-bound.

        An unbacked epistemic clause is a realization error.
        """
        if not self.is_backed:
            raise AssertionError(
                f"Unbacked epistemic clause for {self.report_kind} — "
                "self-report must be evidence-bound"
            )


class KnowledgeDeriver:
    """Derives knowledge, understanding, and belief assessments.

    Distinguishes:
    - stored(p): a persistent record exists (checked externally)
    - remembers(self, p): a relevant stored trace was successfully retrieved
    - has_access_to(self, p): current retrieval, permission, and resources allow access
    - knows(self, p): epistemic criteria are satisfied (7 conditions)
    - knows_about(self, topic): has knowledge about a topic
    - understands(self, schema_or_structure): executable schemas can operate over x
    - believes(self, p): proposition is held in a belief context

    None of these are interchangeable.
    """

    def __init__(self, evaluator: EpistemicEvaluator | None = None) -> None:
        self._evaluator = evaluator or EpistemicEvaluator()

    def derive_understanding(
        self,
        schema_record_ref: str,
        use_profile: SchemaUseProfile | None = None,
        competence_results: tuple[str, ...] = (),
        blocker_reasons: tuple[str, ...] = (),
    ) -> UnderstandingAssessment:
        """Derive whether self understands a schema or structure.

        understands is operation-relative — states exact supported
        competencies and limitations.
        """
        if use_profile is None:
            return UnderstandingAssessment(
                schema_record_ref=schema_record_ref,
                is_understood=False,
                competence_level="none",
                exact_limitations=("No use profile available",),
            )

        level = use_profile.level.value
        supported = tuple(
            op for op in use_profile.permitted_semantic_operations
        )
        # Unsupported = all operations not in permitted
        from ..schema.use_profile import SemanticOperation
        all_ops = {op.value for op in SemanticOperation}
        unsupported = tuple(
            op for op in all_ops if op not in use_profile.permitted_semantic_operations
        )

        is_understood = use_profile.level in (
            UseProfileLevel.PARTIAL, UseProfileLevel.ACTIVE, UseProfileLevel.CAUSAL
        )

        # Exact competencies from use profile level
        competencies: list[str] = []
        if use_profile.level == UseProfileLevel.ACTIVE:
            competencies.extend(["recognize", "classify", "answer defining queries", "licensed inference"])
        elif use_profile.level == UseProfileLevel.CAUSAL:
            competencies.extend(["recognize", "classify", "answer defining queries",
                                "licensed inference", "predict", "simulate", "propose"])
        elif use_profile.level == UseProfileLevel.PARTIAL:
            competencies.extend(["typed reference", "compose under qualification",
                                "query supplied theory", "contrast provisionally"])

        # Limitations from blockers
        limitations: list[str] = list(blocker_reasons)
        if use_profile.level == UseProfileLevel.OPAQUE:
            limitations.append("schema is opaque — can only quote/preserve/search/probe")
        elif use_profile.level == UseProfileLevel.PARTIAL:
            limitations.append("partial understanding — cannot classify or perform licensed inference")
        if not use_profile.permits_execute():
            limitations.append("execute requires live authorization")

        return UnderstandingAssessment(
            schema_record_ref=schema_record_ref,
            is_understood=is_understood,
            supported_operations=supported,
            unsupported_operations=unsupported,
            competence_level=level,
            exact_competencies=tuple(competencies),
            exact_limitations=tuple(limitations),
        )

    def derive_belief(
        self,
        proposition: Proposition,
        context: ContextFrame,
        assessment: EpistemicAssessment,
    ) -> BeliefAssessment:
        """Derive whether self believes proposition p.

        believes(self, p) holds a proposition in a belief context.
        This is distinct from knows — belief does not require all 7 conditions.
        """
        # Belief requires a belief context and some support
        is_believed = (
            context.context_kind in ("believed", "reported", "hypothetical")
            and assessment.support_state in (
                SupportState.SUPPORTED.value, SupportState.BOTH.value
            )
        )

        return BeliefAssessment(
            proposition_ref=proposition.id,
            is_believed=is_believed,
            belief_context_ref=context.id,
            confidence=assessment.confidence,
            evidence_refs=assessment.explanation_refs,
        )

    def create_self_report(
        self,
        report_kind: str,
        is_true: bool,
        evidence_refs: tuple[str, ...] = (),
        proposition_ref: str = "",
        schema_ref: str = "",
        limitations: tuple[str, ...] = (),
    ) -> SelfReport:
        """Create an evidence-bound self-report.

        An unbacked epistemic clause is a realization error.
        Self-report must be backed by evidence.
        """
        is_backed = len(evidence_refs) > 0

        report = SelfReport(
            report_kind=report_kind,
            proposition_ref=proposition_ref,
            schema_ref=schema_ref,
            is_true=is_true,
            evidence_refs=evidence_refs,
            limitations=limitations,
            is_backed=is_backed,
        )

        # Assert backed — unbacked is a realization error
        report.assert_backed()

        return report
