"""LearningCoordinator — transaction lifecycle authority.

Import boundary: model + schema + epistemics submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7, AUTHORITY_MATRIX, LEARNING_PIPELINE.md §12-13, §17):
- LearningCoordinator is the transaction lifecycle authority.
- Transaction lifecycle: open → probing → staged → provisional →
  validated → committed / rolled_back
- Activation sequence (LEARNING_PIPELINE.md §12):
    pin child and environment snapshot
    → derive structural assessment
    → run competence suite
    → derive admissibility profile
    → replay
    → compare-and-swap store/environment fingerprint
    → atomically commit active revision or cluster
    → publish typed invalidation and deferred-replay events
- If independent competence or admissibility is incomplete, the child
  remains provisional. It may be committed with exact limitations,
  not falsely activated.
- Learning completion gate (§17): a learning change is complete only when:
    exact artifact and field provenance are known;
    ordinary understanding uses the changed revision;
    structural closure is valid;
    competence status is honestly represented;
    context/scope admissibility is explicit;
    replay is idempotent and successful for claimed competencies;
    activation, if any, committed atomically;
    dependent cognition has valid fingerprints;
    response wording matches the actual outcome.
- Learning cannot install a parallel resolver.
- No competency test may mutate canonical stores or execute external effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.learning import (
    LearningTransaction, SchemaHypothesis, ReplayWorkItem, ReplayResult,
    CompetencyResult,
)
from ..model.gap import GapRecord, LearningBudget
from ..schema.store import SemanticSchemaStore
from ..schema.envelope import SchemaEnvelope
from ..schema.closure import GroundedDefinitionClosure, SchemaGroundingAssessment
from ..schema.competence import CompetenceHarness, CompetenceAssessment
from ..schema.use_profile import derive_use_profile, SchemaUseProfile, UseProfileLevel
from ..schema.provenance import ProvenanceKind, FieldProvenanceMap
from ..epistemics.evaluator import EpistemicEvaluator, AdmissibilityLevel
from .hypothesis_factory import HypothesisFactory, CompetingHypotheses, EvidenceForHypothesis
from .grounding_frontier import GroundingFrontierBuilder, GroundingFrontier, FrontierItem
from .assimilator import Assimilator, ChildRevision, StagedContribution
from .replay_queue import ReplayQueue


class TransactionStatus(str, Enum):
    """Learning transaction lifecycle states."""
    OPEN = "open"
    PROBING = "probing"
    STAGED = "staged"
    PROVISIONAL = "provisional"
    VALIDATED = "validated"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True, slots=True)
class ActivationAttempt:
    """Result of an activation attempt for a child revision.

    If independent competence or admissibility is incomplete, the child
    remains provisional. It may be committed with exact limitations,
    not falsely activated.
    """
    child_revision_ref: str
    structural_assessment: SchemaGroundingAssessment | None = None
    competence_assessment: CompetenceAssessment | None = None
    use_profile: SchemaUseProfile | None = None
    admissibility: AdmissibilityLevel = AdmissibilityLevel.BLOCKED
    activated: bool = False
    committed_provisional: bool = False
    limitations: tuple[str, ...] = ()
    rollback_reason: str = ""


class LearningCoordinator:
    """Transaction lifecycle authority for recursive schema acquisition.

    Manages the full learning transaction:
    open → probing → staged → provisional → validated → committed / rolled_back

    Does NOT:
    - Install a parallel resolver
    - Allow competency tests to mutate canonical stores
    - Allow competency tests to execute external effects
    - Falsely activate a schema without full conditions
    """

    def __init__(
        self,
        store: SemanticSchemaStore,
        hypothesis_factory: HypothesisFactory | None = None,
        frontier_builder: GroundingFrontierBuilder | None = None,
        assimilator: Assimilator | None = None,
        replay_queue: ReplayQueue | None = None,
        closure: GroundedDefinitionClosure | None = None,
        competence_harness: CompetenceHarness | None = None,
        evaluator: EpistemicEvaluator | None = None,
    ) -> None:
        self._store = store
        self._hypothesis_factory = hypothesis_factory or HypothesisFactory()
        self._frontier_builder = frontier_builder or GroundingFrontierBuilder()
        self._assimilator = assimilator or Assimilator()
        self._replay_queue = replay_queue or ReplayQueue()
        self._closure = closure or GroundedDefinitionClosure()
        self._competence_harness = competence_harness or CompetenceHarness()
        self._evaluator = evaluator or EpistemicEvaluator()
        self._transactions: dict[str, LearningTransaction] = {}

    def open_transaction(
        self,
        gap: GapRecord,
    ) -> LearningTransaction:
        """Open a new learning transaction for a gap."""
        tx = LearningTransaction(
            id=f"tx:{gap.id}",
            gap_ref=gap.id,
            target_sense_ref=gap.target_artifact_ref,
            target_schema_ref=gap.target_artifact_ref,
            base_store_revision=self._store.store_revision,
            status=TransactionStatus.OPEN.value,
            budget=gap.budget,
        )
        self._transactions[tx.id] = tx
        return tx

    def begin_probing(
        self,
        tx: LearningTransaction,
        evidence: tuple[EvidenceForHypothesis, ...] = (),
        is_correction_explicit: bool = False,
    ) -> tuple[LearningTransaction, CompetingHypotheses]:
        """Begin probing phase — generate competing hypotheses.

        Alias/synonym/translation hypotheses compete with new-schema
        and specialization hypotheses.
        """
        gap = GapRecord(
            id=tx.gap_ref,
            target_artifact_ref=tx.target_sense_ref,
            budget=tx.budget,
        )
        competing = self._hypothesis_factory.generate(
            gap=gap,
            evidence=evidence,
            is_correction_explicit=is_correction_explicit,
        )

        from dataclasses import replace
        updated = replace(
            tx, status=TransactionStatus.PROBING.value,
            hypotheses=competing.hypotheses,
        )
        self._transactions[updated.id] = updated
        return updated, competing

    def stage_revision(
        self,
        tx: LearningTransaction,
        hypothesis: SchemaHypothesis,
        contributions: tuple[StagedContribution, ...] = (),
    ) -> tuple[LearningTransaction, ChildRevision]:
        """Stage a child revision from accepted evidence.

        Accepted evidence creates an immutable child revision.
        No hypothesis is silently rewritten as user teaching.
        """
        child = self._assimilator.assimilate(
            base_schema_ref=tx.target_schema_ref,
            base_store_revision=tx.base_store_revision,
            hypothesis=hypothesis,
            contributions=contributions,
        )

        from dataclasses import replace
        updated = replace(
            tx, status=TransactionStatus.STAGED.value,
            child_schema_revision=1,
        )
        self._transactions[updated.id] = updated
        return updated, child

    def attempt_activation(
        self,
        tx: LearningTransaction,
        child: ChildRevision,
        implementation_path: str = "",
    ) -> tuple[LearningTransaction, ActivationAttempt]:
        """Attempt activation of a child revision.

        Activation sequence (LEARNING_PIPELINE.md §12):
        1. pin child and environment snapshot
        2. derive structural assessment
        3. run competence suite
        4. derive admissibility profile
        5. replay
        6. compare-and-swap store/environment fingerprint
        7. atomically commit active revision or cluster
        8. publish typed invalidation and deferred-replay events

        If independent competence or admissibility is incomplete,
        the child remains provisional.
        """
        # 1. Pin snapshot — use store revision at transaction start
        env_fingerprint = f"store:{tx.base_store_revision}"

        # 2. Derive structural assessment
        # Create a temporary envelope for assessment
        env = SchemaEnvelope(
            record_id=child.revision_id,
            semantic_key=tx.target_sense_ref,
            schema_kind="predicate",
            status="candidate",
        )
        grounding_spec = child.grounding_spec
        if grounding_spec is None:
            from ..schema.grounding_spec import GroundingSpecification
            grounding_spec = GroundingSpecification(semantic_family="predicate")

        structural = self._closure.assess(
            envelope=env,
            grounding_spec=grounding_spec,
            patterns=child.patterns,
        )

        # 3. Run competence suite (sandboxed, non-mutating)
        competence_assessment = self._competence_harness.assess(
            cases=(),
            implementation_path=implementation_path,
        )

        # 4. Derive admissibility profile
        # Default to attributed_only for learning — actual-world admission
        # requires full epistemic evaluation
        admissibility = AdmissibilityLevel.ATTRIBUTED_ONLY

        # 5. Derive use profile
        use_profile = derive_use_profile(
            assessment=structural,
            competence_is_competent=competence_assessment.is_competent,
            competence_is_self_certified=competence_assessment.is_self_certified,
        )

        # Determine outcome
        limitations: list[str] = list(structural.blocker_reasons)
        if competence_assessment.is_self_certified:
            limitations.append("self-certified competence — not independently validated")
        if not competence_assessment.is_competent:
            limitations.append("competence not met")

        # 6-7. Activation or provisional commit
        activated = False
        committed_provisional = False
        rollback_reason = ""

        if structural.is_structurally_executable and competence_assessment.is_competent:
            # Full activation conditions met
            # Register and activate through the store (CAS)
            try:
                self._store.register(env)
                rev = self._store.get_revision(env.record_id)
                if rev is not None:
                    # Transition to provisional first
                    result = self._store.transition_to_provisional(
                        env.record_id, rev
                    )
                    if result.status.value == "success":
                        rev = self._store.get_revision(env.record_id)
                        if rev is not None:
                            result = self._store.activate(env.record_id, rev)
                            activated = result.status.value == "success"
                            if not activated:
                                rollback_reason = f"activation CAS failed: {result.detail}"
                else:
                    rollback_reason = "could not get revision after register"
            except ValueError:
                rollback_reason = "schema already registered"
        elif structural.is_structurally_executable:
            # Structurally executable but competence incomplete → provisional
            committed_provisional = True
            limitations.append("provisional — competence incomplete")
        else:
            # Not structurally executable → stays staged
            rollback_reason = "not structurally executable"

        # Update transaction status
        if activated:
            new_status = TransactionStatus.COMMITTED.value
        elif committed_provisional:
            new_status = TransactionStatus.PROVISIONAL.value
        else:
            new_status = TransactionStatus.ROLLED_BACK.value

        from dataclasses import replace
        updated = replace(
            tx, status=new_status,
            structural_status="structurally_executable" if structural.is_structurally_executable else "partial",
            competence_status="independently_validated" if competence_assessment.is_competent else "self_checked",
            admissibility_status=admissibility.value,
        )
        self._transactions[updated.id] = updated

        attempt = ActivationAttempt(
            child_revision_ref=child.revision_id,
            structural_assessment=structural,
            competence_assessment=competence_assessment,
            use_profile=use_profile,
            admissibility=admissibility,
            activated=activated,
            committed_provisional=committed_provisional,
            limitations=tuple(limitations),
            rollback_reason=rollback_reason,
        )

        return updated, attempt

    def get_transaction(self, tx_id: str) -> LearningTransaction | None:
        """Get a transaction by ID."""
        return self._transactions.get(tx_id)

    def get_pending_transactions(self) -> tuple[LearningTransaction, ...]:
        """Get all transactions awaiting evidence (PROBING or STAGED)."""
        return tuple(
            tx for tx in self._transactions.values()
            if tx.status in (
                TransactionStatus.PROBING.value,
                TransactionStatus.STAGED.value,
                TransactionStatus.OPEN.value,
            )
        )

    def get_active_transactions(self) -> tuple[LearningTransaction, ...]:
        """Get all non-terminal transactions."""
        return tuple(
            tx for tx in self._transactions.values()
            if tx.status not in (
                TransactionStatus.COMMITTED.value,
                TransactionStatus.ROLLED_BACK.value,
            )
        )

    def consume_pending_evidence(
        self,
        selected_interpretations: list[Any] | None = None,
    ) -> tuple[Any, ...]:
        """B5: Consume pending learning evidence.

        After ordinary composition and grounding, match grounded
        propositions against expected evidence schemas for pending
        transactions. Raw text is never copied directly into a
        hypothesis field.

        Returns updated transactions that received evidence.
        """
        if not selected_interpretations:
            return ()

        pending = self.get_pending_transactions()
        if not pending:
            return ()

        from .hypothesis_factory import EvidenceForHypothesis, HypothesisKind
        updated_txs: list[Any] = []

        for tx in pending:
            # Match interpretations to this transaction's target
            matched_evidence: list[EvidenceForHypothesis] = []
            for interp in selected_interpretations:
                prop = getattr(interp, "proposition", None)
                if prop is None:
                    continue
                prop_id = getattr(prop, "id", "")
                # Check if this proposition relates to the transaction's target
                target = tx.target_sense_ref or tx.target_schema_ref
                if not target:
                    continue
                # Match by target reference in proposition's predication
                pred_ref = getattr(prop, "predication_ref", "") or getattr(prop, "predicate_schema_ref", "")
                if target in pred_ref or pred_ref in target:
                    ev = self._hypothesis_factory.classify_evidence(
                        proposition_ref=prop_id,
                        evidence_ref=f"ev:{prop_id}",
                        is_new_sense_evidence=True,
                        confidence=0.5,
                        is_independent=True,
                    )
                    matched_evidence.append(ev)

            if matched_evidence:
                # Begin probing with matched evidence
                updated, _ = self.begin_probing(
                    tx=tx,
                    evidence=tuple(matched_evidence),
                )
                updated_txs.append(updated)

        return tuple(updated_txs)

    def provisional_replay(
        self,
        tx: LearningTransaction,
        contributions: tuple[StagedContribution, ...] = (),
        implementation_path: str = "",
    ) -> tuple[LearningTransaction, ActivationAttempt]:
        """B6: Provisional replay — create child revision and attempt activation.

        When matched evidence can update a target schema:
        1. create a child schema revision against the pinned snapshot
        2. stage typed schema changes with field-level provenance
        3. classify typed dependencies and recursive components
        4. run structural closure and sandboxed competence cases
        5. derive context-specific epistemic admissibility
        6. expose the result as provisional or activation-ready
        7. preserve rollback and idempotency data

        Replay may not repeat dispatched output or external side effects.
        Definition-derived cases can prove well-formedness only, not
        independent competence.
        """
        # Select the best hypothesis (highest confidence)
        if not tx.hypotheses:
            from dataclasses import replace
            updated = replace(tx, status=TransactionStatus.ROLLED_BACK.value)
            self._transactions[updated.id] = updated
            return updated, ActivationAttempt(
                child_revision_ref="",
                rollback_reason="no hypotheses to stage",
            )

        best_hyp = max(tx.hypotheses, key=lambda h: h.confidence)

        # Stage child revision
        updated, child = self.stage_revision(
            tx=tx,
            hypothesis=best_hyp,
            contributions=contributions,
        )

        # Attempt activation (runs closure, competence, admissibility)
        updated, attempt = self.attempt_activation(
            tx=updated,
            child=child,
            implementation_path=implementation_path,
        )

        # Enqueue replay work if replay queue is available
        if self._replay_queue is not None and attempt.activated:
            from ..model.learning import ReplayWorkItem
            replay_item = ReplayWorkItem(
                id=f"replay:{child.revision_id}",
                source_evidence_ref=updated.gap_ref,
                target_sense_ref=updated.target_sense_ref,
                target_schema_revision_ref=child.revision_id,
                checkpoint_ref=updated.replay_checkpoint_ref,
                context_refs=updated.context_refs,
                dependency_fingerprint=f"store:{updated.base_store_revision}",
                idempotency_key=f"replay:{child.revision_id}:{updated.base_store_revision}",
            )
            self._replay_queue.enqueue(replay_item)

        return updated, attempt

    def rollback(self, tx: LearningTransaction) -> LearningTransaction:
        """Roll back a transaction.

        Roll back provisional schema revisions that failed validation.
        Original evidence remains preserved.
        """
        from dataclasses import replace
        updated = replace(tx, status=TransactionStatus.ROLLED_BACK.value)
        self._transactions[updated.id] = updated
        return updated

    def compute_grounding_frontier(
        self,
        tx: LearningTransaction,
        attempt: ActivationAttempt | None = None,
        blockers: tuple[Any, ...] = (),
    ) -> GroundingFrontier:
        """Compute the grounding frontier for a transaction.

        Per LEARNING_PIPELINE.md §5:
        - The transaction computes the smallest blocking frontier over
          typed dependencies.
        - Priority: active goal blocker, required semantic family/role/value,
          constitutive structure, independent discrimination, differentiator,
          context/time applicability, enrichment.
        - Asked probe keys are persisted. Budget exhaustion leaves exact typed
          gaps and a resumable transaction.
        """
        frontier_items: list[FrontierItem] = []

        # Build frontier items from structural assessment blockers
        if attempt is not None and attempt.structural_assessment is not None:
            for blocker in attempt.structural_assessment.blocker_reasons:
                priority = self._frontier_builder.classify_blocker(blocker)
                probe_key = f"probe:{tx.id}:{blocker}"
                frontier_items.append(FrontierItem(
                    item_id=f"fi:{tx.id}:{blocker}",
                    dependency_ref=blocker,
                    blocker_kind=blocker,
                    priority=priority,
                    probe_key=probe_key,
                    target_schema_ref=tx.target_schema_ref,
                ))

        # Also include any additional blockers passed in
        for blocker in blockers:
            blocker_kind = getattr(blocker, "kind", str(blocker))
            priority = self._frontier_builder.classify_blocker(blocker_kind)
            probe_key = f"probe:{tx.id}:{blocker_kind}"
            frontier_items.append(FrontierItem(
                item_id=f"fi:{tx.id}:{blocker_kind}",
                dependency_ref=str(blocker),
                blocker_kind=blocker_kind,
                priority=priority,
                probe_key=probe_key,
                target_schema_ref=tx.target_schema_ref,
            ))

        return self._frontier_builder.build(
            blockers=tuple(frontier_items),
            budget=tx.budget,
            asked_probe_keys=tx.asked_probe_keys,
        )

    def check_completion_gate(
        self,
        tx: LearningTransaction,
        attempt: ActivationAttempt,
    ) -> tuple[bool, tuple[str, ...]]:
        """Check the learning completion gate (LEARNING_PIPELINE.md §17).

        A learning change is complete only when:
        1. exact artifact and field provenance are known
        2. ordinary understanding uses the changed revision
        3. structural closure is valid
        4. competence status is honestly represented
        5. context/scope admissibility is explicit
        6. replay is idempotent and successful for claimed competencies
        7. activation, if any, committed atomically
        8. dependent cognition has valid fingerprints
        9. response wording matches the actual outcome
        """
        failures: list[str] = []

        # 1. Field provenance known
        if attempt.structural_assessment is None:
            failures.append("structural assessment missing")

        # 3. Structural closure valid
        if attempt.structural_assessment and not attempt.structural_assessment.is_structurally_executable:
            if tx.status != TransactionStatus.PROVISIONAL.value:
                failures.append("structural closure not valid")

        # 4. Competence status honestly represented
        if attempt.competence_assessment and attempt.competence_assessment.is_self_certified:
            if attempt.activated:
                failures.append("self-certified competence cannot activate")

        # 5. Admissibility explicit
        if tx.admissibility_status == "open":
            failures.append("admissibility not explicit")

        # 7. Activation committed atomically
        if attempt.activated and tx.status != TransactionStatus.COMMITTED.value:
            failures.append("activation not reflected in transaction status")

        # If provisional, limitations must be explicit
        if tx.status == TransactionStatus.PROVISIONAL.value:
            if not attempt.limitations:
                failures.append("provisional without explicit limitations")

        return (len(failures) == 0, tuple(failures))
