"""SchemaEnvelope, SchemaContribution, SchemaDependency — schema record wrappers.

Import boundary: standard library only → model.refs, model.identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from ..model.refs import Ref
from ..model.identity import Scope, TimeExtent, Provenance, Permission


S = TypeVar("S")


@dataclass(frozen=True, slots=True)
class SchemaContribution:
    """Field-level contribution to a schema with provenance.

    provenance_kind: asserted, observed, entailed, inherited, hypothesized,
                     defaulted, induced, adapter_supplied, boot_supplied
    """
    field_path: str
    value_or_pattern_ref: str
    provenance_kind: str = "asserted"
    evidence_refs: tuple[str, ...] = ()
    derivation_refs: tuple[str, ...] = ()
    scope: Scope = field(default_factory=Scope)
    context_refs: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class SchemaDependency:
    """Typed dependency from one schema to another.

    dependency_kind: definition, inheritance, selectional, competence,
                     evidence, adapter, policy, realization, effect
    """
    dependency_kind: str
    target_schema_ref: str  # Ref[SchemaEnvelope]
    polarity: str = "positive"  # positive | negative
    monotonicity: str = "monotone"  # monotone, defeasible, non_monotone
    required_for_operations: frozenset[str] = field(default_factory=frozenset)
    invalidation_policy: str = "invalidate_dependents"


@dataclass(frozen=True, slots=True)
class SchemaEnvelope(Generic[S]):
    """Versioned wrapper around a schema payload.

    status: candidate, provisional, active, rejected, superseded

    Lifecycle is strict:
    - candidate: identity exists but not structurally usable
    - provisional: some structure executable in declared context
    - active: passed structural closure, competence, policy, atomic activation
    - superseded/rejected: not selected for new interpretation
    """
    record_id: str
    semantic_key: str
    schema_kind: str
    status: str = "candidate"
    scope: Scope = field(default_factory=Scope)
    applicability_context_refs: tuple[str, ...] = ()
    valid_time: TimeExtent | None = None
    version: int = 1
    payload: S | None = None
    grounding_spec_ref: str = ""
    contribution_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()
    support_refs: tuple[str, ...] = ()
    counterevidence_refs: tuple[str, ...] = ()
    confidence: float = 0.0
    permission: Permission = field(default_factory=Permission.public)
    provenance: Provenance = field(
        default_factory=lambda: Provenance(source_id="unknown")
    )
    supersedes_refs: tuple[str, ...] = ()
    # Assessment/admissibility refs — required for active records (Stage 3 exit gate)
    grounding_assessment_ref: str = ""  # Ref[SchemaGroundingAssessment]
    epistemic_admissibility_ref: str = ""  # Ref[EpistemicAssessment]
    competence_assessment_ref: str = ""  # Ref[CompetenceAssessment]
    activation_environment_fingerprint: str = ""  # pinned snapshot fingerprint
