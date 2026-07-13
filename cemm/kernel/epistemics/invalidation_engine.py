"""InvalidationEngine — processes invalidation events, retracts dependent artifacts.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7.5, LEARNING_PIPELINE.md §13,
CORE_LOOP.md §9, ADR-21):
- Parent downgrade retracts classifications, inferences, answers, plans,
  messages, and effect proposals.
- Evidence remains — original evidence is preserved.
- Historical output remains an event and may generate a repair obligation.
- Effects and irreversible operations revalidate at authorization and
  critical commit.
- Cross-schema inference laundering does not increase support.
- A dependency or environment change invalidates all dependent derived
  cognition, including assessments, inherited constraints, classifications,
  inferred propositions, cached answers, plans, undispatched messages,
  effect proposals, capability/understanding conclusions, and
  learning-success claims.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.learning import DerivedArtifactProvenance
from .artifact_index import (
    DerivedArtifactIndex, IndexedArtifact, ArtifactKind, ArtifactStatus,
)
from .invalidation_events import (
    TypedInvalidationEvent, InvalidationSource, InvalidationAction,
    InvalidationEventBus,
)
from .truth_maintenance import TruthMaintenance, LineageGraph, LineageNode


@dataclass(frozen=True, slots=True)
class InvalidationResult:
    """Result of processing an invalidation event."""
    event_id: str
    retracted_artifact_ids: tuple[str, ...] = ()
    staled_artifact_ids: tuple[str, ...] = ()
    reauthorized_artifact_ids: tuple[str, ...] = ()
    evidence_preserved: bool = True
    repair_obligation_ids: tuple[str, ...] = ()


class InvalidationEngine:
    """Processes invalidation events and retracts/stales dependent artifacts.

    Parent downgrade retracts classifications, inferences, answers, plans,
    messages, and effect proposals. Evidence remains.

    Cross-schema inference laundering does not increase support —
    the engine detects and blocks support-cycle laundering.

    Does NOT:
    - Delete original evidence
    - Mutate canonical stores
    - Dispatch responses
    """

    def __init__(
        self,
        index: DerivedArtifactIndex | None = None,
        truth_maintenance: TruthMaintenance | None = None,
        event_bus: InvalidationEventBus | None = None,
    ) -> None:
        self._index = index or DerivedArtifactIndex()
        self._tm = truth_maintenance or TruthMaintenance()
        self._bus = event_bus or InvalidationEventBus()
        self._repair_obligations: list[str] = []

    @property
    def index(self) -> DerivedArtifactIndex:
        return self._index

    @property
    def event_bus(self) -> InvalidationEventBus:
        return self._bus

    def process(self, event: TypedInvalidationEvent) -> InvalidationResult:
        """Process an invalidation event.

        Finds all dependent artifacts and retracts or marks them stale
        based on the event action. Evidence is always preserved.
        """
        # Find all dependent artifacts
        dependents = self._index.find_all_dependents(
            schema_revision_refs=event.changed_schema_revision_refs,
            assessment_refs=event.changed_assessment_refs,
            evidence_refs=event.changed_evidence_refs,
            environment_fingerprint=event.old_fingerprint if event.old_fingerprint else None,
        )

        retracted: list[str] = []
        staled: list[str] = []
        reauthorized: list[str] = []

        for artifact in dependents:
            if artifact.status != ArtifactStatus.ACTIVE:
                continue  # Already processed

            if event.action == InvalidationAction.RETRACT:
                self._index.update_status(artifact.artifact_id, ArtifactStatus.RETRACTED)
                retracted.append(artifact.artifact_id)

                # Mark proposition as invalidated in truth maintenance
                self._tm.invalidate(artifact.artifact_id)

                # Historical output generates repair obligation
                if artifact.artifact_kind == ArtifactKind.MESSAGE_ITEM:
                    self._repair_obligations.append(artifact.artifact_id)

            elif event.action == InvalidationAction.MARK_STALE:
                self._index.update_status(artifact.artifact_id, ArtifactStatus.STALE)
                staled.append(artifact.artifact_id)
                self._tm.invalidate(artifact.artifact_id)

            elif event.action == InvalidationAction.REAUTHORIZE:
                # Effects and irreversible operations revalidate at
                # authorization and critical commit
                reauthorized.append(artifact.artifact_id)
                self._tm.invalidate(artifact.artifact_id)

        # Publish the event
        self._bus.publish(event)

        return InvalidationResult(
            event_id=event.event_id,
            retracted_artifact_ids=tuple(retracted),
            staled_artifact_ids=tuple(staled),
            reauthorized_artifact_ids=tuple(reauthorized),
            evidence_preserved=True,  # Evidence always remains
            repair_obligation_ids=tuple(self._repair_obligations),
        )

    def on_schema_downgrade(
        self,
        schema_revision_ref: str,
        old_fingerprint: str = "",
        new_fingerprint: str = "",
    ) -> InvalidationResult:
        """Handle a schema downgrade (e.g., active → provisional).

        Parent downgrade retracts classifications, inferences, answers,
        plans, messages, and effect proposals.
        """
        event = TypedInvalidationEvent.create(
            source=InvalidationSource.SCHEMA_DOWNGRADE,
            action=InvalidationAction.RETRACT,
            changed_schema_revision_refs=(schema_revision_ref,),
            old_fingerprint=old_fingerprint,
            new_fingerprint=new_fingerprint,
        )
        return self.process(event)

    def on_schema_supersession(
        self,
        old_schema_ref: str,
        new_schema_ref: str,
    ) -> InvalidationResult:
        """Handle schema supersession — old revision replaced by new.

        Dependent artifacts are marked stale (not retracted) since the
        new revision may support them.
        """
        event = TypedInvalidationEvent.create(
            source=InvalidationSource.SCHEMA_SUPERSESSION,
            action=InvalidationAction.MARK_STALE,
            changed_schema_revision_refs=(old_schema_ref,),
        )
        return self.process(event)

    def on_evidence_retraction(
        self,
        evidence_ref: str,
    ) -> InvalidationResult:
        """Handle evidence retraction.

        Evidence retraction retracts dependent artifacts but the original
        evidence record itself remains preserved (as a historical event).
        """
        event = TypedInvalidationEvent.create(
            source=InvalidationSource.EVIDENCE_RETRACTION,
            action=InvalidationAction.RETRACT,
            changed_evidence_refs=(evidence_ref,),
        )
        return self.process(event)

    def on_environment_change(
        self,
        old_fingerprint: str,
        new_fingerprint: str,
    ) -> InvalidationResult:
        """Handle environment fingerprint change.

        A dependency or environment change invalidates all dependent
        derived cognition.
        """
        event = TypedInvalidationEvent.create(
            source=InvalidationSource.ENVIRONMENT_FINGERPRINT_CHANGE,
            action=InvalidationAction.MARK_STALE,
            old_fingerprint=old_fingerprint,
            new_fingerprint=new_fingerprint,
        )
        return self.process(event)

    def on_in_flight_effect(
        self,
        schema_revision_ref: str,
        old_fingerprint: str = "",
        new_fingerprint: str = "",
    ) -> InvalidationResult:
        """Handle in-flight effects that need reauthorization.

        Effects and irreversible operations revalidate at authorization
        and critical commit.
        """
        event = TypedInvalidationEvent.create(
            source=InvalidationSource.SCHEMA_DOWNGRADE,
            action=InvalidationAction.REAUTHORIZE,
            changed_schema_revision_refs=(schema_revision_ref,),
            old_fingerprint=old_fingerprint,
            new_fingerprint=new_fingerprint,
        )
        return self.process(event)

    def get_repair_obligations(self) -> tuple[str, ...]:
        """Get repair obligations from retracted historical output.

        Historical output remains an event and may generate a repair
        obligation.
        """
        return tuple(self._repair_obligations)


class CrossSchemaLaunderingGuard:
    """Guards against cross-schema inference laundering.

    Cross-schema inference laundering does not increase support.
    A derived proposition may be working knowledge but cannot increase
    support or competence for any schema in its transitive support
    ancestry or support strongly connected component.

    A translation, paraphrase, generated case, summary, or copied source
    does not create new independent support.
    """

    def __init__(self) -> None:
        self._support_ancestry: dict[str, set[str]] = {}
        self._support_sccs: dict[str, set[str]] = {}

    def register_support_ancestry(
        self,
        schema_ref: str,
        ancestry: tuple[str, ...],
    ) -> None:
        """Register the support ancestry for a schema.

        The ancestry is the set of schemas that this schema's support
        depends on transitively.
        """
        self._support_ancestry[schema_ref] = set(ancestry)

    def register_support_scc(
        self,
        schema_ref: str,
        scc_members: tuple[str, ...],
    ) -> None:
        """Register the strongly connected component for a schema.

        The SCC is the set of schemas that mutually support each other.
        """
        scc_set = set(scc_members)
        for member in scc_members:
            self._support_sccs[member] = scc_set

    def can_increase_support(
        self,
        evidence_schema_ref: str,
        target_schema_ref: str,
        evidence_lineage: tuple[str, ...] = (),
    ) -> bool:
        """Check if evidence from one schema can increase support for another.

        Cross-schema inference laundering does not increase support.
        Returns True if the evidence CAN increase support (no laundering
        detected), False if it cannot.
        """
        # Check ancestry: if target is in evidence schema's ancestry,
        # the evidence cannot increase support (circular support)
        ancestry = self._support_ancestry.get(evidence_schema_ref, set())
        if target_schema_ref in ancestry:
            return False

        # Check SCC: if both are in the same SCC, evidence cannot
        # increase support (mutual support laundering)
        evidence_scc = self._support_sccs.get(evidence_schema_ref, set())
        target_scc = self._support_sccs.get(target_schema_ref, set())
        if evidence_scc and target_scc and evidence_scc & target_scc:
            return False

        # Check lineage: if evidence lineage overlaps with target's ancestry
        target_ancestry = self._support_ancestry.get(target_schema_ref, set())
        evidence_roots = set(evidence_lineage)
        if evidence_roots & target_ancestry:
            return False

        return True

    def detect_laundering(
        self,
        evidence_schema_ref: str,
        target_schema_ref: str,
        evidence_lineage: tuple[str, ...] = (),
    ) -> str | None:
        """Detect and describe cross-schema inference laundering.

        Returns a description of the laundering detected, or None if
        no laundering is detected.
        """
        ancestry = self._support_ancestry.get(evidence_schema_ref, set())
        if target_schema_ref in ancestry:
            return (
                f"cross-schema laundering: {evidence_schema_ref} has "
                f"{target_schema_ref} in its support ancestry — "
                f"circular support detected"
            )

        evidence_scc = self._support_sccs.get(evidence_schema_ref, set())
        target_scc = self._support_sccs.get(target_schema_ref, set())
        if evidence_scc and target_scc and evidence_scc & target_scc:
            return (
                f"cross-schema laundering: {evidence_schema_ref} and "
                f"{target_schema_ref} are in the same support SCC — "
                f"mutual support laundering detected"
            )

        target_ancestry = self._support_ancestry.get(target_schema_ref, set())
        evidence_roots = set(evidence_lineage)
        if evidence_roots & target_ancestry:
            overlap = evidence_roots & target_ancestry
            return (
                f"cross-schema laundering: evidence lineage {overlap} "
                f"overlaps with target ancestry — "
                f"derived evidence cannot increase support"
            )

        return None
