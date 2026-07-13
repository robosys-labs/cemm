"""LearningTransaction, ReplayWorkItem, and DerivedArtifactProvenance.

Import boundary: standard library only → refs, identity, gap.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import AssessmentEnvironmentFingerprint, Scope, Provenance
from .gap import LearningBudget


@dataclass(frozen=True, slots=True)
class SchemaHypothesis:
    """A hypothesis about a schema revision."""
    hypothesis_kind: str  # alias, new_sense, specialization, correction
    target_sense_ref: str = ""
    proposed_revision_ref: str = ""
    differentiator_refs: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class CompetencyResult:
    """Result of running a competency case."""
    case_ref: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Result of a replay work item."""
    work_item_ref: str  # Ref[ReplayWorkItem]
    status: str = "pending"  # pending, succeeded, failed, stale
    evidence_ref: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class LearningTransaction:
    """A learning transaction — recursive schema acquisition lifecycle.

    status: open, probing, staged, provisional, validated, committed, rolled_back
    """
    id: str
    gap_ref: str  # Ref[GapRecord]
    target_sense_ref: str = ""
    target_schema_ref: str = ""
    base_schema_revision: int = 0
    base_store_revision: int = 0
    child_schema_revision: int | None = None
    child_snapshot_fingerprint: AssessmentEnvironmentFingerprint | None = None
    hypotheses: tuple[SchemaHypothesis, ...] = ()
    expected_evidence_schema_ref: str = ""
    acquired_evidence_refs: tuple[str, ...] = ()
    grounding_frontier: tuple[str, ...] = ()
    asked_probe_keys: frozenset[str] = field(default_factory=frozenset)
    replay_checkpoint_ref: str = ""
    replay_work_refs: tuple[str, ...] = ()
    replay_results: tuple[ReplayResult, ...] = ()
    competency_results: tuple[CompetencyResult, ...] = ()
    structural_status: str = "untested"  # untested, partial, structurally_executable
    competence_status: str = "untested"  # untested, self_checked, limited, independently_validated, failed
    admissibility_status: str = "open"  # open, attributed_only, admitted, blocked
    status: str = "open"  # open, probing, staged, provisional, validated, committed, rolled_back
    scope: Scope = field(default_factory=Scope)
    context_refs: tuple[str, ...] = ()
    budget: LearningBudget = field(default_factory=LearningBudget)
    provenance: Provenance = field(
        default_factory=lambda: Provenance(source_id="unknown")
    )


@dataclass(frozen=True, slots=True)
class ReplayWorkItem:
    """A unit of replay work — bounded, idempotent, deduplicated.

    status: queued, running, succeeded, redeferred, cancelled, stale
    """
    id: str
    source_evidence_ref: str  # Ref[EvidenceRecord]
    target_sense_ref: str = ""
    target_schema_revision_ref: str = ""  # Ref[SchemaEnvelope]
    checkpoint_ref: str = ""
    context_refs: tuple[str, ...] = ()
    dependency_fingerprint: str = ""
    idempotency_key: str = ""
    priority: float = 0.0
    status: str = "queued"
    attempt_count: int = 0


@dataclass(frozen=True, slots=True)
class DerivedArtifactProvenance:
    """Provenance for a derived artifact (inference, classification, etc.).

    Every materialized inference, classification, cached answer, plan,
    message item, capability conclusion, and understanding claim carries
    equivalent dependency provenance so downgrade can retract it.
    """
    supporting_schema_revision_refs: tuple[str, ...] = ()
    supporting_assessment_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    environment_fingerprint: AssessmentEnvironmentFingerprint | None = None
