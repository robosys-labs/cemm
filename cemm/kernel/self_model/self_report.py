"""Self-report and operation-relative understands.

Import boundary: model + schema + epistemics submodules only. No engine imports.

Architectural guardrails (AGENTS.md §10-11, UNDERSTANDING_PIPELINE.md §12):
- Self-report queries use ordinary semantic retrieval over:
    remembered proposition
    schema grounding assessment
    competence results
    admissibility assessment
    current blockers
    capability/component evidence
- Truthful outputs distinguish:
    I remember your statement.
    I can use your definition provisionally in this conversation.
    I can recognize/query these cases.
    I have not independently validated it.
    I do not currently have enough structure to understand it.
- An unbacked epistemic clause is a realization error.
- understands is operation-relative — states exact supported competencies
  and limitations.
- Static schema declarations cannot advertise capabilities.
- Self-description must query current assessments and ordinary semantic
  records, then pass through the normal response planner and NLG pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.epistemic import EpistemicAssessment
from ..model.capability import CapabilityAssessment
from ..schema.use_profile import SchemaUseProfile, UseProfileLevel, SemanticOperation
from ..schema.closure import SchemaGroundingAssessment
from ..epistemics.evaluator import (
    EpistemicEvaluator, KnowledgeAssessment, SupportState, AdmissibilityLevel,
)
from ..epistemics.knowledge_derivation import (
    KnowledgeDeriver, UnderstandingAssessment, BeliefAssessment, SelfReport,
)
from .capability_evaluator import CapabilityEvaluator


@dataclass(frozen=True, slots=True)
class OperationRelativeUnderstanding:
    """Operation-relative understanding assessment.

    understands(self, schema_or_structure) is not a boolean — it depends
    on what operation is being requested. This record states exact
    supported competencies and limitations for a specific operation.
    """
    schema_record_ref: str
    requested_operation: str
    can_perform: bool = False
    competence_level: str = "none"
    exact_competencies: tuple[str, ...] = ()
    exact_limitations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def describe(self) -> str:
        """Human-readable description."""
        if self.can_perform:
            return (
                f"I can {self.requested_operation} on {self.schema_record_ref} "
                f"at {self.competence_level} level."
            )
        return (
            f"I cannot {self.requested_operation} on {self.schema_record_ref}. "
            f"Limitations: {', '.join(self.exact_limitations) or 'unspecified'}"
        )


class SelfReportBuilder:
    """Builds evidence-bound self-reports.

    Self-report must be evidence-bound. An unbacked epistemic clause
    is a realization error.

    Self-description must query current assessments and ordinary semantic
    records. Static schema declarations cannot advertise capabilities.
    """

    def __init__(
        self,
        evaluator: EpistemicEvaluator | None = None,
        deriver: KnowledgeDeriver | None = None,
        capability_evaluator: CapabilityEvaluator | None = None,
    ) -> None:
        self._evaluator = evaluator or EpistemicEvaluator()
        self._deriver = deriver or KnowledgeDeriver(self._evaluator)
        self._capability_evaluator = capability_evaluator or CapabilityEvaluator()

    def report_knows(
        self,
        proposition_ref: str,
        knowledge: KnowledgeAssessment,
    ) -> SelfReport:
        """Report whether self knows proposition p.

        Truthful outputs distinguish:
        - I remember your statement.
        - I can use your definition provisionally in this conversation.
        - I can recognize/query these cases.
        - I have not independently validated it.
        - I do not currently have enough structure to understand it.
        """
        if knowledge.is_known:
            return SelfReport(
                report_kind="knows",
                proposition_ref=proposition_ref,
                is_true=True,
                evidence_refs=(proposition_ref,),
                is_backed=True,
            )
        else:
            # Report specific limitations
            return SelfReport(
                report_kind="knows",
                proposition_ref=proposition_ref,
                is_true=False,
                evidence_refs=(proposition_ref,),
                limitations=knowledge.limitations,
                is_backed=True,
            )

    def report_understands(
        self,
        schema_ref: str,
        understanding: UnderstandingAssessment,
        requested_operation: str = "",
    ) -> SelfReport:
        """Report whether self understands a schema or structure.

        understands is operation-relative — states exact supported
        competencies and limitations.
        """
        if requested_operation:
            # Operation-relative understanding
            can_perform = requested_operation in understanding.supported_operations
            return SelfReport(
                report_kind="understands",
                schema_ref=schema_ref,
                is_true=can_perform,
                evidence_refs=(schema_ref,),
                limitations=understanding.exact_limitations if not can_perform else (),
                is_backed=True,
            )

        return SelfReport(
            report_kind="understands",
            schema_ref=schema_ref,
            is_true=understanding.is_understood,
            evidence_refs=(schema_ref,),
            limitations=understanding.exact_limitations,
            is_backed=True,
        )

    def report_capability(
        self,
        operation_ref: str,
        capability: CapabilityAssessment,
    ) -> SelfReport:
        """Report whether self has a current capability.

        Static schema declarations cannot advertise capabilities.
        Capability must be based on live evidence.
        """
        return SelfReport(
            report_kind="can_do",
            schema_ref=operation_ref,
            is_true=capability.status == "capable",
            evidence_refs=capability.evidence_refs,
            limitations=capability.limitations,
            is_backed=True,
        )

    def report_remembers(
        self,
        proposition_ref: str,
        was_retrieved: bool,
    ) -> SelfReport:
        """Report whether self remembers a proposition.

        remembers(self, p) — a relevant stored trace was successfully
        retrieved. This is distinct from knows(self, p).
        """
        return SelfReport(
            report_kind="remembers",
            proposition_ref=proposition_ref,
            is_true=was_retrieved,
            evidence_refs=(proposition_ref,) if was_retrieved else (),
            is_backed=True,
        )

    def report_believes(
        self,
        proposition_ref: str,
        belief: BeliefAssessment,
    ) -> SelfReport:
        """Report whether self believes proposition p.

        believes(self, p) is distinct from knows(self, p).
        """
        return SelfReport(
            report_kind="believes",
            proposition_ref=proposition_ref,
            is_true=belief.is_believed,
            evidence_refs=belief.evidence_refs,
            is_backed=True,
        )

    def derive_operation_relative_understanding(
        self,
        schema_record_ref: str,
        use_profile: SchemaUseProfile,
        requested_operation: SemanticOperation,
        blocker_reasons: tuple[str, ...] = (),
    ) -> OperationRelativeUnderstanding:
        """Derive operation-relative understanding.

        understands is not a boolean — it depends on the requested operation.
        States exact supported competencies and limitations.
        """
        understanding = self._deriver.derive_understanding(
            schema_record_ref=schema_record_ref,
            use_profile=use_profile,
            blocker_reasons=blocker_reasons,
        )

        can_perform = use_profile.permits(requested_operation)

        return OperationRelativeUnderstanding(
            schema_record_ref=schema_record_ref,
            requested_operation=requested_operation.value,
            can_perform=can_perform,
            competence_level=understanding.competence_level,
            exact_competencies=understanding.exact_competencies,
            exact_limitations=understanding.exact_limitations,
            evidence_refs=understanding.evidence_refs,
        )
