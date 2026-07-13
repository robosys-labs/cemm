"""DerivedArtifactIndex — index every derived artifact by supporting schema
revisions and environment fingerprint.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7.5, ADR-21, SEMANTIC_DATA_MODEL.md §4.9):
- Every materialized inference, classification, cached answer, plan,
  message item, capability conclusion, and understanding claim carries
  equivalent dependency provenance so downgrade can retract it.
- A dependency or environment change invalidates all dependent derived
  cognition, including assessments, inherited constraints, classifications,
  inferred propositions, cached answers, plans, undispatched messages,
  effect proposals, capability/understanding conclusions, and
  learning-success claims.
- Original evidence and already dispatched historical output remain preserved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.learning import DerivedArtifactProvenance


class ArtifactKind(str, Enum):
    """Kinds of derived artifacts that can be invalidated."""
    INFERENCE = "inference"
    CLASSIFICATION = "classification"
    CACHED_ANSWER = "cached_answer"
    PLAN = "plan"
    MESSAGE_ITEM = "message_item"
    EFFECT_PROPOSAL = "effect_proposal"
    CAPABILITY_CONCLUSION = "capability_conclusion"
    UNDERSTANDING_CONCLUSION = "understanding_conclusion"
    LEARNING_SUCCESS_CLAIM = "learning_success_claim"
    INHERITED_CONSTRAINT = "inherited_constraint"


class ArtifactStatus(str, Enum):
    """Status of a derived artifact."""
    ACTIVE = "active"
    STALE = "stale"
    RETRACTED = "retracted"


@dataclass(frozen=True, slots=True)
class IndexedArtifact:
    """A derived artifact indexed by its supporting schema revisions and
    environment fingerprint.

    Every materialized inference, classification, cached answer, plan,
    message item, capability conclusion, and understanding claim carries
    equivalent dependency provenance so downgrade can retract it.
    """
    artifact_id: str
    artifact_kind: ArtifactKind
    provenance: DerivedArtifactProvenance
    status: ArtifactStatus = ArtifactStatus.ACTIVE
    created_at: str = ""  # ISO timestamp


class DerivedArtifactIndex:
    """Index of derived artifacts by supporting schema revisions and
    environment fingerprint.

    Enables efficient lookup of all artifacts that depend on a given
    schema revision or environment fingerprint, so that a dependency
    change can retract or mark stale all dependent derived artifacts.

    Does NOT:
    - Mutate canonical stores
    - Decide truth (that's EpistemicEvaluator's job)
    - Dispatch or produce responses
    """

    def __init__(self) -> None:
        self._artifacts: dict[str, IndexedArtifact] = {}
        # Index by schema revision ref → artifact IDs
        self._by_schema: dict[str, set[str]] = {}
        # Index by assessment ref → artifact IDs
        self._by_assessment: dict[str, set[str]] = {}
        # Index by evidence ref → artifact IDs
        self._by_evidence: dict[str, set[str]] = {}
        # Index by environment fingerprint → artifact IDs
        self._by_fingerprint: dict[str, set[str]] = {}

    def register(self, artifact: IndexedArtifact) -> None:
        """Register a derived artifact with its provenance."""
        self._artifacts[artifact.artifact_id] = artifact

        # Index by schema revisions
        for schema_ref in artifact.provenance.supporting_schema_revision_refs:
            self._by_schema.setdefault(schema_ref, set()).add(artifact.artifact_id)

        # Index by assessment refs
        for assessment_ref in artifact.provenance.supporting_assessment_refs:
            self._by_assessment.setdefault(assessment_ref, set()).add(artifact.artifact_id)

        # Index by evidence refs
        for evidence_ref in artifact.provenance.evidence_refs:
            self._by_evidence.setdefault(evidence_ref, set()).add(artifact.artifact_id)

        # Index by environment fingerprint
        if artifact.provenance.environment_fingerprint is not None:
            fp = str(artifact.provenance.environment_fingerprint)
            self._by_fingerprint.setdefault(fp, set()).add(artifact.artifact_id)

    def get(self, artifact_id: str) -> IndexedArtifact | None:
        """Get an artifact by ID."""
        return self._artifacts.get(artifact_id)

    def find_by_schema(self, schema_revision_ref: str) -> tuple[IndexedArtifact, ...]:
        """Find all artifacts that depend on a given schema revision."""
        ids = self._by_schema.get(schema_revision_ref, set())
        return tuple(self._artifacts[aid] for aid in ids if aid in self._artifacts)

    def find_by_assessment(self, assessment_ref: str) -> tuple[IndexedArtifact, ...]:
        """Find all artifacts that depend on a given assessment."""
        ids = self._by_assessment.get(assessment_ref, set())
        return tuple(self._artifacts[aid] for aid in ids if aid in self._artifacts)

    def find_by_evidence(self, evidence_ref: str) -> tuple[IndexedArtifact, ...]:
        """Find all artifacts that depend on given evidence."""
        ids = self._by_evidence.get(evidence_ref, set())
        return tuple(self._artifacts[aid] for aid in ids if aid in self._artifacts)

    def find_by_fingerprint(self, fingerprint: str) -> tuple[IndexedArtifact, ...]:
        """Find all artifacts that depend on a given environment fingerprint."""
        ids = self._by_fingerprint.get(fingerprint, set())
        return tuple(self._artifacts[aid] for aid in ids if aid in self._artifacts)

    def find_all_dependents(
        self,
        schema_revision_refs: tuple[str, ...] = (),
        assessment_refs: tuple[str, ...] = (),
        evidence_refs: tuple[str, ...] = (),
        environment_fingerprint: str | None = None,
    ) -> tuple[IndexedArtifact, ...]:
        """Find all artifacts that depend on any of the given inputs.

        This is the primary query for invalidation — given a set of
        changed schema revisions, assessments, evidence, or fingerprint,
        find all derived artifacts that need to be retracted or marked stale.
        """
        dependent_ids: set[str] = set()

        for schema_ref in schema_revision_refs:
            dependent_ids.update(self._by_schema.get(schema_ref, set()))

        for assessment_ref in assessment_refs:
            dependent_ids.update(self._by_assessment.get(assessment_ref, set()))

        for evidence_ref in evidence_refs:
            dependent_ids.update(self._by_evidence.get(evidence_ref, set()))

        if environment_fingerprint is not None:
            dependent_ids.update(self._by_fingerprint.get(environment_fingerprint, set()))

        return tuple(self._artifacts[aid] for aid in dependent_ids if aid in self._artifacts)

    def update_status(
        self,
        artifact_id: str,
        new_status: ArtifactStatus,
    ) -> IndexedArtifact | None:
        """Update the status of an artifact (e.g., mark stale or retracted).

        Returns the updated artifact, or None if not found.
        """
        from dataclasses import replace
        old = self._artifacts.get(artifact_id)
        if old is None:
            return None
        updated = replace(old, status=new_status)
        self._artifacts[artifact_id] = updated
        return updated

    def active_artifacts(self) -> tuple[IndexedArtifact, ...]:
        """Get all active artifacts."""
        return tuple(
            a for a in self._artifacts.values()
            if a.status == ArtifactStatus.ACTIVE
        )

    def stale_artifacts(self) -> tuple[IndexedArtifact, ...]:
        """Get all stale artifacts."""
        return tuple(
            a for a in self._artifacts.values()
            if a.status == ArtifactStatus.STALE
        )

    def retracted_artifacts(self) -> tuple[IndexedArtifact, ...]:
        """Get all retracted artifacts."""
        return tuple(
            a for a in self._artifacts.values()
            if a.status == ArtifactStatus.RETRACTED
        )
