"""CausalWarrantGrades — causal warrant classification and enforcement.

Import boundary: model + schema + epistemics submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7.7, SEMANTIC_FOUNDATIONS.md §10,
ACCEPTANCE_TESTS.md §35-37, ADR-20):
- Schema grounding may permit interpretation, prediction, simulation, or
  proposal of effects. It never grants persistent authority to execute or
  commit an effect.
- Foundational causal predicates define representation and query semantics.
  Claims using them carry a separate warrant grade:
    reported_claim
    contextual_rule
    predictive_association
    mechanism_supported
    intervention_supported
- Actual intervention or irreversible planning requires the appropriate
  grade plus live authorization.
- Teaching a causal/effect schema fires no effect.
- Teaching alone never fires shutdown (or any other effect).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CausalWarrantGrade(str, Enum):
    """Causal warrant grades from SEMANTIC_FOUNDATIONS.md §10.

    Ordered from weakest to strongest:
    1. reported_claim — someone said this causal relationship exists
    2. contextual_rule — rule applies in this context but not verified
    3. predictive_association — observed correlation, no mechanism
    4. mechanism_supported — mechanism understood and verified
    5. intervention_supported — intervention tested and verified
    """
    REPORTED_CLAIM = "reported_claim"
    CONTEXTUAL_RULE = "contextual_rule"
    PREDICTIVE_ASSOCIATION = "predictive_association"
    MECHANISM_SUPPORTED = "mechanism_supported"
    INTERVENTION_SUPPORTED = "intervention_supported"

    @property
    def strength(self) -> int:
        """Numeric strength for comparison (higher = stronger)."""
        order = {
            CausalWarrantGrade.REPORTED_CLAIM: 0,
            CausalWarrantGrade.CONTEXTUAL_RULE: 1,
            CausalWarrantGrade.PREDICTIVE_ASSOCIATION: 2,
            CausalWarrantGrade.MECHANISM_SUPPORTED: 3,
            CausalWarrantGrade.INTERVENTION_SUPPORTED: 4,
        }
        return order[self]

    def is_sufficient_for(self, required: CausalWarrantGrade) -> bool:
        """Check if this grade is sufficient for a required grade."""
        return self.strength >= required.strength


class EffectCapability(str, Enum):
    """What a schema can do with effects (AGENTS.md §7.7).

    Schema grounding may permit:
    - interpretation: understand what an effect means
    - prediction: predict what would happen
    - simulation: simulate the effect
    - proposal: propose the effect

    It NEVER grants:
    - authorization: authorize execution
    - execution: execute the effect
    - commit: commit the effect persistently
    """
    INTERPRET = "interpret"
    PREDICT = "predict"
    SIMULATE = "simulate"
    PROPOSE = "propose"
    # The following are NOT schema-level capabilities:
    AUTHORIZE = "authorize"  # OperationAuthorizer only
    EXECUTE = "execute"      # OperationExecutor only
    COMMIT = "commit"        # CommitCoordinator only


# Schema-level capabilities (what grounding can permit)
SCHEMA_LEVEL_CAPABILITIES: frozenset[EffectCapability] = frozenset({
    EffectCapability.INTERPRET,
    EffectCapability.PREDICT,
    EffectCapability.SIMULATE,
    EffectCapability.PROPOSE,
})

# Non-schema capabilities (what requires live authority)
LIVE_AUTHORITY_CAPABILITIES: frozenset[EffectCapability] = frozenset({
    EffectCapability.AUTHORIZE,
    EffectCapability.EXECUTE,
    EffectCapability.COMMIT,
})


@dataclass(frozen=True, slots=True)
class CausalWarrantAssessment:
    """Assessment of causal warrant for a proposition.

    Teaching a causal/effect schema fires no effect.
    The warrant grade is recorded but does not grant execution authority.
    """
    proposition_ref: str
    grade: CausalWarrantGrade
    is_schema_level_only: bool = True  # Teaching never grants live authority
    intervention_blocked: bool = True  # Blocked until required grade + live auth
    required_grade_for_intervention: CausalWarrantGrade = CausalWarrantGrade.INTERVENTION_SUPPORTED
    evidence_refs: tuple[str, ...] = ()
    policy_allows_intervention: bool = False


class CausalWarrantEvaluator:
    """Evaluates causal warrant grades and enforces live-effect-authority law.

    Schema grounding may permit interpretation, prediction, simulation, or
    proposal of effects. It never grants persistent authority to execute or
    commit an effect.

    Teaching a causal/effect schema fires no effect.
    """

    def assess_warrant(
        self,
        proposition_ref: str,
        grade: CausalWarrantGrade = CausalWarrantGrade.REPORTED_CLAIM,
        evidence_refs: tuple[str, ...] = (),
        is_taught: bool = False,
    ) -> CausalWarrantAssessment:
        """Assess causal warrant for a proposition.

        Teaching alone never fires an effect — the assessment is always
        schema-level only, and intervention is always blocked until the
        required grade plus live authorization.
        """
        # Teaching always results in schema-level-only authority
        is_schema_level = True
        intervention_blocked = True

        # Even if the grade is high, teaching doesn't grant intervention
        # Live authorization is always required separately
        if is_taught:
            is_schema_level = True
            intervention_blocked = True

        return CausalWarrantAssessment(
            proposition_ref=proposition_ref,
            grade=grade,
            is_schema_level_only=is_schema_level,
            intervention_blocked=intervention_blocked,
            required_grade_for_intervention=CausalWarrantGrade.INTERVENTION_SUPPORTED,
            evidence_refs=evidence_refs,
            policy_allows_intervention=False,  # Always False from schema alone
        )

    def can_interpret(self, assessment: CausalWarrantAssessment) -> bool:
        """Check if the warrant allows interpretation.

        Schema grounding may permit interpretation of effects.
        """
        return True  # Interpretation is always allowed from schema

    def can_predict(self, assessment: CausalWarrantAssessment) -> bool:
        """Check if the warrant allows prediction.

        Schema grounding may permit prediction of effects.
        """
        return True  # Prediction is always allowed from schema

    def can_simulate(self, assessment: CausalWarrantAssessment) -> bool:
        """Check if the warrant allows simulation.

        Schema grounding may permit simulation of effects.
        """
        return True  # Simulation is always allowed from schema

    def can_propose(self, assessment: CausalWarrantAssessment) -> bool:
        """Check if the warrant allows proposal.

        Schema grounding may permit proposal of effects.
        """
        return True  # Proposal is always allowed from schema

    def can_authorize(
        self,
        assessment: CausalWarrantAssessment,
        live_authorization: bool = False,
    ) -> bool:
        """Check if the warrant allows authorization.

        Schema grounding NEVER grants authorization authority.
        Authorization requires live OperationAuthorizer.
        """
        # Schema alone never authorizes
        if assessment.is_schema_level_only and not live_authorization:
            return False
        # Even with live authorization, the required grade must be met
        if not live_authorization:
            return False
        return not assessment.intervention_blocked

    def can_execute(
        self,
        assessment: CausalWarrantAssessment,
        live_authorization: bool = False,
    ) -> bool:
        """Check if the warrant allows execution.

        Schema grounding NEVER grants execution authority.
        Execution requires live OperationExecutor with authorization.
        """
        # Schema alone never executes
        if not live_authorization:
            return False
        # Intervention must be unblocked
        if assessment.intervention_blocked:
            return False
        # Required grade must be met
        return assessment.grade.is_sufficient_for(
            assessment.required_grade_for_intervention
        )

    def check_intervention_readiness(
        self,
        assessment: CausalWarrantAssessment,
        live_authorization: bool = False,
        policy_allows: bool = False,
    ) -> tuple[bool, str]:
        """Check if intervention is ready (grade + live auth + policy).

        Actual intervention or irreversible planning requires the
        appropriate grade plus live authorization.

        Returns (is_ready, reason).
        """
        if assessment.intervention_blocked and not live_authorization:
            return (False, "intervention blocked — requires live authorization")

        if not assessment.grade.is_sufficient_for(
            assessment.required_grade_for_intervention
        ):
            return (
                False,
                f"warrant grade {assessment.grade.value} insufficient — "
                f"requires {assessment.required_grade_for_intervention.value}",
            )

        if not live_authorization:
            return (False, "live authorization not granted")

        if not policy_allows:
            return (False, "policy does not allow intervention")

        return (True, "")
