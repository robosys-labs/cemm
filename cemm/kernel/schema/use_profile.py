"""SchemaUseProfile — derived per-snapshot usability for a schema in a context.

Import boundary: standard library only → model.refs, model.identity, schema.closure.

These are derived control records. They do not create another schema
store or ontology. Neither SchemaGroundingAssessment nor SchemaUseProfile
is an activation authority.

Architectural guardrails (AGENTS.md §7.1, UNDERSTANDING_PIPELINE.md §4.4):
- The resolver derives a use profile by intersecting structural,
  competence, admissibility, scope/access, and requested-operation results.
- A schema may be:
    opaque: quote, preserve attributed assertion, search, probe
    partial/provisional: typed reference, compose under qualification,
      query the supplied theory, contrast provisionally, explain blockers
    active/admitted: recognize, classify, answer defining queries,
      perform licensed inference in admitted contexts
    causal/effect interpretable: predict/simulate/propose only;
      never execute without live authorization
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.identity import AssessmentEnvironmentFingerprint
from .closure import SchemaGroundingAssessment, CompetenceProfile


class UseProfileLevel(str, Enum):
    """Level of usability for a schema revision."""
    OPAQUE = "opaque"
    PARTIAL = "partial"
    ACTIVE = "active"
    CAUSAL = "causal"
    INADMISSIBLE = "inadmissible"


class SemanticOperation(str, Enum):
    """Operations that may be requested on a schema."""
    QUOTE = "quote"
    PRESERVE = "preserve"
    SEARCH = "search"
    PROBE = "probe"
    TYPED_REFERENCE = "typed_reference"
    COMPOSE_QUALIFIED = "compose_qualified"
    QUERY_THEORY = "query_theory"
    CONTRAST_PROVISIONAL = "contrast_provisional"
    EXPLAIN_BLOCKERS = "explain_blockers"
    RECOGNIZE = "recognize"
    CLASSIFY = "classify"
    ANSWER_DEFINING_QUERY = "answer_defining_query"
    LICENSED_INFERENCE = "licensed_inference"
    PREDICT = "predict"
    SIMULATE = "simulate"
    PROPOSE = "propose"
    EXECUTE = "execute"


# Operations permitted at each level
OPAQUE_OPERATIONS = frozenset({
    SemanticOperation.QUOTE,
    SemanticOperation.PRESERVE,
    SemanticOperation.SEARCH,
    SemanticOperation.PROBE,
})

PARTIAL_OPERATIONS = OPAQUE_OPERATIONS | frozenset({
    SemanticOperation.TYPED_REFERENCE,
    SemanticOperation.COMPOSE_QUALIFIED,
    SemanticOperation.QUERY_THEORY,
    SemanticOperation.CONTRAST_PROVISIONAL,
    SemanticOperation.EXPLAIN_BLOCKERS,
})

ACTIVE_OPERATIONS = PARTIAL_OPERATIONS | frozenset({
    SemanticOperation.RECOGNIZE,
    SemanticOperation.CLASSIFY,
    SemanticOperation.ANSWER_DEFINING_QUERY,
    SemanticOperation.LICENSED_INFERENCE,
})

CAUSAL_OPERATIONS = ACTIVE_OPERATIONS | frozenset({
    SemanticOperation.PREDICT,
    SemanticOperation.SIMULATE,
    SemanticOperation.PROPOSE,
})

# EXECUTE is never in any level — it requires live authorization


@dataclass(frozen=True, slots=True)
class SchemaUseProfile:
    """Derived per-snapshot usability profile for a schema in a context.

    A revision may support quotation, preservation, or attributed reasoning
    while remaining opaque or provisional. It may support actual-world
    classification or inference only when the current SchemaUseProfile
    permits those operations.

    EXECUTE is never permitted by profile alone — it requires live
    authorization.
    """
    schema_record_ref: str  # Ref[SchemaEnvelope]
    context_ref: str  # Ref[ContextFrame]
    level: UseProfileLevel = UseProfileLevel.OPAQUE
    requested_operation: str = ""
    structural_status: str = "opaque"
    competence_status: str = "untested"
    epistemic_admissibility: str = "blocked"
    permitted_semantic_operations: frozenset[str] = field(default_factory=frozenset)
    limitations: tuple[str, ...] = ()
    grounding_assessment_ref: str = ""  # Ref[SchemaGroundingAssessment]
    epistemic_assessment_refs: tuple[str, ...] = ()
    environment_fingerprint: AssessmentEnvironmentFingerprint | None = None

    def permits(self, operation: SemanticOperation) -> bool:
        """Check if a specific operation is permitted."""
        return operation.value in self.permitted_semantic_operations

    def permits_execute(self) -> bool:
        """EXECUTE is never permitted by profile alone — requires live authorization."""
        return False


def derive_use_profile(
    assessment: SchemaGroundingAssessment,
    context_ref: str = "",
    competence_is_competent: bool = False,
    competence_is_self_certified: bool = False,
    epistemic_admissible: bool = True,
    scope_accessible: bool = True,
) -> SchemaUseProfile:
    """Derive a SchemaUseProfile from assessment results.

    Intersects structural executability, competence, epistemic
    admissibility, and scope/access to determine the use level.

    Neither this function nor the GroundingResolver may activate a revision.
    """
    blockers: list[str] = []

    # If not structurally executable → opaque
    if not assessment.is_structurally_executable:
        blockers.extend(assessment.blocker_reasons)
        return SchemaUseProfile(
            schema_record_ref=assessment.record_id,
            context_ref=context_ref,
            level=UseProfileLevel.OPAQUE,
            structural_status="opaque",
            permitted_semantic_operations=frozenset(op.value for op in OPAQUE_OPERATIONS),
            limitations=tuple(blockers),
            environment_fingerprint=assessment.environment_fingerprint or None,
        )

    # If not epistemically admissible → opaque
    if not epistemic_admissible:
        blockers.append("Epistemic admissibility blocked")
        return SchemaUseProfile(
            schema_record_ref=assessment.record_id,
            context_ref=context_ref,
            level=UseProfileLevel.OPAQUE,
            structural_status="structurally_executable",
            epistemic_admissibility="blocked",
            permitted_semantic_operations=frozenset(op.value for op in OPAQUE_OPERATIONS),
            limitations=tuple(blockers),
            environment_fingerprint=assessment.environment_fingerprint or None,
        )

    # If not scope accessible → inadmissible
    if not scope_accessible:
        blockers.append("Scope access blocked")
        return SchemaUseProfile(
            schema_record_ref=assessment.record_id,
            context_ref=context_ref,
            level=UseProfileLevel.INADMISSIBLE,
            structural_status="structurally_executable",
            epistemic_admissibility="admitted",
            permitted_semantic_operations=frozenset(),
            limitations=tuple(blockers),
            environment_fingerprint=assessment.environment_fingerprint or None,
        )

    # If competence not met → partial/provisional
    if not competence_is_competent:
        if competence_is_self_certified:
            blockers.append("Competence self-certified — invalid")
        else:
            blockers.append("Competence requirements not met")

        return SchemaUseProfile(
            schema_record_ref=assessment.record_id,
            context_ref=context_ref,
            level=UseProfileLevel.PARTIAL,
            structural_status="structurally_executable",
            competence_status="failed" if competence_is_self_certified else "limited",
            epistemic_admissibility="admitted",
            permitted_semantic_operations=frozenset(op.value for op in PARTIAL_OPERATIONS),
            limitations=tuple(blockers),
            environment_fingerprint=assessment.environment_fingerprint or None,
        )

    # Check if causal patterns exist → causal level
    has_causal = False
    if assessment.pattern_assessment is not None:
        from .pattern_assessment import PatternFunction
        for p in assessment.pattern_assessment.all_patterns:
            try:
                if PatternFunction(p.function) == PatternFunction.CAUSAL:
                    has_causal = True
                    break
            except ValueError:
                continue

    if has_causal:
        return SchemaUseProfile(
            schema_record_ref=assessment.record_id,
            context_ref=context_ref,
            level=UseProfileLevel.CAUSAL,
            structural_status="structurally_executable",
            competence_status="independently_validated",
            epistemic_admissibility="admitted",
            permitted_semantic_operations=frozenset(op.value for op in CAUSAL_OPERATIONS),
            environment_fingerprint=assessment.environment_fingerprint or None,
        )

    # Default: active/admitted
    return SchemaUseProfile(
        schema_record_ref=assessment.record_id,
        context_ref=context_ref,
        level=UseProfileLevel.ACTIVE,
        structural_status="structurally_executable",
        competence_status="independently_validated",
        epistemic_admissibility="admitted",
        permitted_semantic_operations=frozenset(op.value for op in ACTIVE_OPERATIONS),
        environment_fingerprint=assessment.environment_fingerprint or None,
    )
