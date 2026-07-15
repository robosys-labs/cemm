"""LearningCoordinator — dialogue-grounded schema acquisition authority.

v3.4.1 replacement.  Learning remains inside SemanticSchemaStore: an opaque
surface receives a stable session-scoped candidate revision; user evidence is
stored as typed field contributions; provisional status is not reported unless
the child record was committed and is visible to the ordinary resolver.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
from typing import Any, Iterable
from uuid import uuid4

from ..model.dialogue import DialogueObligation, DialogueTurnResolution
from ..model.gap import GapRecord
from ..model.identity import (
    Permission, PermissionScope, Provenance, RetentionPolicy, Scope, ScopeLevel,
)
from ..model.learning import LearningTransaction, SchemaHypothesis
from ..schema.competence import CompetenceAssessment, CompetenceCase, CompetenceHarness
from ..schema.closure import GroundedDefinitionClosure, SchemaGroundingAssessment
from ..schema.envelope import SchemaEnvelope
from ..schema.grounding_spec import GroundingSpecification
from ..schema.lexeme import LexemeSenseSchema
from ..schema.provenance import ProvenanceKind
from ..schema.store import SemanticSchemaStore
from ..schema.use_profile import SchemaUseProfile, UseProfileLevel, derive_use_profile
from .assimilator import Assimilator, ChildRevision, StagedContribution
from .grounding_frontier import GroundingFrontier, GroundingFrontierBuilder, FrontierItem
from .hypothesis_factory import (
    CompetingHypotheses,
    EvidenceForHypothesis,
    HypothesisFactory,
    HypothesisKind,
)
from .replay_queue import ReplayQueue


class TransactionStatus(str, Enum):
    OPEN = "open"
    PROBING = "probing"
    STAGED = "staged"
    PROVISIONAL = "provisional"
    VALIDATED = "validated"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True, slots=True)
class ActivationAttempt:
    child_revision_ref: str
    structural_assessment: SchemaGroundingAssessment | None = None
    competence_assessment: CompetenceAssessment | None = None
    use_profile: SchemaUseProfile | None = None
    admissibility: str = "blocked"
    activated: bool = False
    committed_provisional: bool = False
    limitations: tuple[str, ...] = ()
    rollback_reason: str = ""


@dataclass(frozen=True, slots=True)
class LearnedSchemaDraft:
    """Declarative payload for a partially grounded learned sense."""

    semantic_key: str
    target_surface: str = ""
    semantic_family: str = ""
    role_refs: tuple[str, ...] = ()
    constitutive_predicate_refs: tuple[str, ...] = ()
    related_surface_forms: tuple[str, ...] = ()
    unresolved_field_refs: tuple[str, ...] = ()


class LearningCoordinator:
    """Own the complete learning transaction and pending dialogue lifecycle."""

    def __init__(
        self,
        store: SemanticSchemaStore,
        hypothesis_factory: HypothesisFactory | None = None,
        frontier_builder: GroundingFrontierBuilder | None = None,
        assimilator: Assimilator | None = None,
        replay_queue: ReplayQueue | None = None,
        closure: GroundedDefinitionClosure | None = None,
        competence_harness: CompetenceHarness | None = None,
        evaluator: Any | None = None,
    ) -> None:
        self._store = store
        self._hypothesis_factory = hypothesis_factory or HypothesisFactory()
        self._frontier_builder = frontier_builder or GroundingFrontierBuilder()
        self._assimilator = assimilator or Assimilator()
        self._replay_queue = replay_queue or ReplayQueue()
        self._closure = closure or GroundedDefinitionClosure()
        self._competence_harness = competence_harness or CompetenceHarness()
        self._evaluator = evaluator
        self._transactions: dict[str, LearningTransaction] = {}
        self._transaction_keys: dict[tuple[str, str, str], str] = {}
        self._obligations: dict[str, DialogueObligation] = {}
        self._children: dict[str, ChildRevision] = {}

    # ------------------------------------------------------------------
    # Transaction identity and lifecycle
    # ------------------------------------------------------------------

    def open_transaction(
        self,
        gap: GapRecord,
        *,
        context_ref: str = "default",
    ) -> LearningTransaction:
        target = gap.target_artifact_ref
        key = (context_ref, target, gap.gap_kind)
        existing_id = self._transaction_keys.get(key)
        if existing_id:
            existing = self._transactions.get(existing_id)
            if existing and existing.status not in {
                TransactionStatus.COMMITTED.value,
                TransactionStatus.ROLLED_BACK.value,
            }:
                return existing

        tx = LearningTransaction(
            id=f"tx:{uuid4().hex[:12]}",
            gap_ref=gap.id,
            target_sense_ref=target,
            target_schema_ref=target,
            base_store_revision=self._store.store_revision,
            expected_evidence_schema_ref=(
                gap.expected_evidence_schema_ref
                or self._expected_evidence_key(gap)
            ),
            grounding_frontier=tuple(gap.missing_fields),
            status=TransactionStatus.OPEN.value,
            scope=Scope(level=ScopeLevel.SESSION, session_id=context_ref),
            context_refs=(context_ref,),
            budget=gap.budget,
            provenance=Provenance(
                source_id=gap.id,
                source_kind="semantic_gap",
            ),
        )
        self._transactions[tx.id] = tx
        self._transaction_keys[key] = tx.id
        return tx

    def get_transaction(self, tx_id: str) -> LearningTransaction | None:
        return self._transactions.get(tx_id)

    def get_pending_transactions(
        self,
        context_ref: str | None = None,
    ) -> tuple[LearningTransaction, ...]:
        result = []
        for tx in self._transactions.values():
            if tx.status not in {
                TransactionStatus.OPEN.value,
                TransactionStatus.PROBING.value,
                TransactionStatus.STAGED.value,
                TransactionStatus.PROVISIONAL.value,
            }:
                continue
            if context_ref is not None and context_ref not in tx.context_refs:
                continue
            result.append(tx)
        return tuple(result)

    def get_active_transactions(self) -> tuple[LearningTransaction, ...]:
        return tuple(
            tx for tx in self._transactions.values()
            if tx.status not in {
                TransactionStatus.COMMITTED.value,
                TransactionStatus.ROLLED_BACK.value,
            }
        )

    def begin_probing(
        self,
        tx: LearningTransaction,
        evidence: tuple[EvidenceForHypothesis, ...] = (),
        is_correction_explicit: bool = False,
    ) -> tuple[LearningTransaction, CompetingHypotheses]:
        gap = GapRecord(
            id=tx.gap_ref,
            target_artifact_ref=tx.target_sense_ref,
            expected_evidence_schema_ref=tx.expected_evidence_schema_ref or None,
            budget=tx.budget,
            learnable=True,
        )
        competing = self._hypothesis_factory.generate(
            gap=gap,
            evidence=evidence,
            is_correction_explicit=is_correction_explicit,
        )
        # A structural gap with accepted evidence must always retain at least
        # one explicit hypothesis.  This is not a claim that it is correct.
        hypotheses = competing.hypotheses
        if not hypotheses and evidence:
            hypotheses = (
                SchemaHypothesis(
                    hypothesis_kind=(
                        HypothesisKind.CORRECTION.value
                        if is_correction_explicit
                        else HypothesisKind.NEW_SENSE.value
                    ),
                    target_sense_ref=tx.target_sense_ref,
                    confidence=max((ev.confidence for ev in evidence), default=0.4),
                ),
            )
            competing = replace(competing, hypotheses=hypotheses)

        updated = replace(
            tx,
            status=TransactionStatus.PROBING.value,
            hypotheses=hypotheses,
            acquired_evidence_refs=tuple(dict.fromkeys(
                (*tx.acquired_evidence_refs, *(ev.evidence_ref for ev in evidence))
            )),
        )
        self._transactions[updated.id] = updated
        return updated, competing

    # ------------------------------------------------------------------
    # Dialogue obligations — registered only after dispatch
    # ------------------------------------------------------------------

    def pending_obligations(
        self,
        context_ref: str,
    ) -> tuple[DialogueObligation, ...]:
        return tuple(
            obligation for obligation in self._obligations.values()
            if obligation.context_ref == context_ref
            and obligation.status == "pending"
        )

    def register_probe_dispatch(
        self,
        *,
        context_ref: str,
        message_item: Any,
        gaps: tuple[Any, ...] | list[Any],
        output_event_ref: str = "",
    ) -> DialogueObligation | None:
        if getattr(message_item, "content_kind", "") != "learning_probe":
            return None
        gap_role = message_item.role("gap_ref") if hasattr(message_item, "role") else None
        gap_ref = getattr(gap_role, "semantic_ref", "") if gap_role else ""
        gap = next((g for g in gaps if getattr(g, "id", "") == gap_ref), None)
        if gap is None:
            return None
        tx = self.open_transaction(gap, context_ref=context_ref)
        tx = replace(
            tx,
            status=TransactionStatus.PROBING.value,
            asked_probe_keys=frozenset((*tx.asked_probe_keys, self._probe_key(message_item, gap))),
        )
        self._transactions[tx.id] = tx

        unresolved = tuple(getattr(gap, "missing_fields", ()) or ())
        if not unresolved:
            unresolved = self._default_frontier(gap.gap_kind)
        obligation = DialogueObligation(
            obligation_id=f"dialogue:{uuid4().hex[:12]}",
            context_ref=context_ref,
            transaction_ref=tx.id,
            question_semantic_ref=getattr(message_item, "semantic_ref", ""),
            target_artifact_ref=gap.target_artifact_ref,
            expected_evidence_schema_refs=(
                tx.expected_evidence_schema_ref,
            ) if tx.expected_evidence_schema_ref else (),
            unresolved_field_refs=unresolved,
            asked_probe_key=self._probe_key(message_item, gap),
            output_event_ref=output_event_ref,
        )
        # Supersede older question for the same transaction; preserve history.
        for oid, old in tuple(self._obligations.items()):
            if old.transaction_ref == tx.id and old.status == "pending":
                self._obligations[oid] = replace(old, status="superseded")
        self._obligations[obligation.obligation_id] = obligation
        return obligation


    def register_followup_dispatch(
        self,
        *,
        context_ref: str,
        message_item: Any,
        dialogue_resolution: DialogueTurnResolution,
        output_event_ref: str = "",
    ) -> DialogueObligation | None:
        """Register a follow-up frontier question that was actually emitted."""
        if getattr(message_item, "content_kind", "") not in {
            "learning_progress", "dialogue_gap_explanation"
        }:
            return None
        tx = self._transactions.get(dialogue_resolution.transaction_ref)
        if tx is None:
            return None
        unresolved = tuple(dialogue_resolution.remaining_field_refs)
        if not unresolved:
            return None
        for oid, old in tuple(self._obligations.items()):
            if old.transaction_ref == tx.id and old.status == "pending":
                self._obligations[oid] = replace(old, status="superseded")
        obligation = DialogueObligation(
            obligation_id=f"dialogue:{uuid4().hex[:12]}",
            context_ref=context_ref,
            transaction_ref=tx.id,
            question_semantic_ref=getattr(message_item, "semantic_ref", ""),
            target_artifact_ref=dialogue_resolution.target_artifact_ref,
            expected_evidence_schema_refs=("evidence:denotation_choice",),
            unresolved_field_refs=unresolved,
            accepted_contribution_refs=dialogue_resolution.accepted_contribution_refs,
            asked_probe_key=f"probe:{tx.id}:{unresolved[0]}",
            output_event_ref=output_event_ref,
        )
        self._obligations[obligation.obligation_id] = obligation
        self._transactions[tx.id] = replace(
            tx,
            status=TransactionStatus.PROBING.value,
            asked_probe_keys=frozenset((*tx.asked_probe_keys, obligation.asked_probe_key)),
            grounding_frontier=unresolved,
        )
        return obligation

    def resolve_dialogue_turn(
        self,
        *,
        context_ref: str,
        selected_interpretations: list[Any] | tuple[Any, ...],
        surface_evidence: tuple[Any, ...] | list[Any],
    ) -> DialogueTurnResolution:
        pending = self.pending_obligations(context_ref)
        if not pending:
            return DialogueTurnResolution(context_ref=context_ref)
        obligation = pending[-1]
        tx = self._transactions.get(obligation.transaction_ref)
        if tx is None:
            return DialogueTurnResolution(context_ref=context_ref)

        if self._is_meta_question(selected_interpretations, surface_evidence):
            return DialogueTurnResolution(
                context_ref=context_ref,
                resolution_kind="meta_question",
                obligation_ref=obligation.obligation_id,
                transaction_ref=tx.id,
                target_artifact_ref=obligation.target_artifact_ref,
                remaining_field_refs=obligation.unresolved_field_refs,
                explanation_key="explain_pending_learning_frontier",
                evidence_refs=(obligation.question_semantic_ref,),
                suppress_fresh_lexical_gaps=True,
            )

        evidence_interps = tuple(
            interp for interp in selected_interpretations
            if getattr(interp, "communicative_force", "") in {"assert", "correct"}
        )
        choice = self._choice_answer(surface_evidence)
        if not evidence_interps and choice:
            evidence_ref = f"learning_evidence:choice:{uuid4().hex[:10]}"
            evidence = (
                self._hypothesis_factory.classify_evidence(
                    proposition_ref=evidence_ref,
                    evidence_ref=evidence_ref,
                    is_new_sense_evidence=True,
                    confidence=0.85,
                    is_independent=False,
                    context_ref=context_ref,
                ),
            )
            updated, competing = self.begin_probing(tx, evidence=evidence)
            contributions = (
                StagedContribution(
                    field_name="denotation_role_or_holder",
                    field_value=choice,
                    provenance_kind=ProvenanceKind.ASSERTED,
                    evidence_ref=evidence_ref,
                    source_ref="user:dialogue_answer",
                    is_independent=False,
                ),
            )
            best = max(
                competing.hypotheses,
                key=lambda hypothesis: hypothesis.confidence,
                default=SchemaHypothesis(
                    hypothesis_kind=HypothesisKind.NEW_SENSE.value,
                    target_sense_ref=updated.target_sense_ref,
                    confidence=0.6,
                ),
            )
            updated, child = self.stage_revision(updated, best, contributions)
            updated, _ = self.attempt_activation(updated, child)
            remaining = tuple(
                field for field in obligation.unresolved_field_refs
                if field != "denotation_role_or_holder"
            )
            remaining = tuple(dict.fromkeys((*remaining, "example", "non_example", "differentiator")))
            accepted_refs = tuple(dict.fromkeys(
                (*obligation.accepted_contribution_refs, evidence_ref)
            ))
            self._obligations[obligation.obligation_id] = replace(
                obligation,
                status="answered",
                accepted_contribution_refs=accepted_refs,
                unresolved_field_refs=remaining,
            )
            self._transactions[updated.id] = replace(
                updated,
                grounding_frontier=remaining,
            )
            return DialogueTurnResolution(
                context_ref=context_ref,
                resolution_kind="evidence",
                obligation_ref=obligation.obligation_id,
                transaction_ref=updated.id,
                target_artifact_ref=obligation.target_artifact_ref,
                accepted_contribution_refs=accepted_refs,
                accepted_surface_forms=(choice,),
                remaining_field_refs=remaining,
                explanation_key="report_denotation_and_request_contrast",
                evidence_refs=(evidence_ref,),
                suppress_fresh_lexical_gaps=True,
            )
        if not evidence_interps:
            return DialogueTurnResolution(context_ref=context_ref)

        is_correction = any(
            getattr(interp, "communicative_force", "") == "correct"
            for interp in evidence_interps
        )
        evidence = tuple(
            self._hypothesis_factory.classify_evidence(
                proposition_ref=getattr(interp, "proposition_ref", ""),
                evidence_ref=f"learning_evidence:{getattr(interp, 'proposition_ref', uuid4().hex)}",
                is_new_sense_evidence=not is_correction,
                is_correction=is_correction,
                confidence=max(0.35, float(getattr(interp, "confidence", 0.0))),
                # The user utterance is independent of CEMM's hypothesis, but
                # repeated paraphrases retain the same source lineage.  We do
                # not count it as an independent competence oracle.
                is_independent=False,
                context_ref=getattr(interp, "context_ref", context_ref),
            )
            for interp in evidence_interps
            if getattr(interp, "proposition_ref", "")
        )
        updated, competing = self.begin_probing(
            tx,
            evidence=evidence,
            is_correction_explicit=is_correction,
        )
        accepted_surfaces = self._accepted_surfaces(
            surface_evidence,
            obligation.target_artifact_ref,
        )
        contributions = self._typed_contributions(
            evidence_interps,
            accepted_surfaces,
            evidence,
        )
        best = max(
            competing.hypotheses,
            key=lambda hypothesis: hypothesis.confidence,
            default=SchemaHypothesis(
                hypothesis_kind=HypothesisKind.NEW_SENSE.value,
                target_sense_ref=updated.target_sense_ref,
                confidence=0.4,
            ),
        )
        updated, child = self.stage_revision(updated, best, contributions)
        updated, attempt = self.attempt_activation(updated, child)

        accepted_refs = tuple(
            dict.fromkeys(
                (*obligation.accepted_contribution_refs,
                 *(contribution.evidence_ref for contribution in contributions if contribution.evidence_ref))
            )
        )
        remaining = self._remaining_frontier(
            obligation.unresolved_field_refs,
            contributions,
        )
        # A single analogy/subkind assertion does not establish role-vs-holder
        # denotation or independent contrast competence.
        if "denotation_role_or_holder" not in remaining:
            remaining = (*remaining, "denotation_role_or_holder")
        remaining = tuple(dict.fromkeys(remaining))
        self._obligations[obligation.obligation_id] = replace(
            obligation,
            status="answered",
            accepted_contribution_refs=accepted_refs,
            unresolved_field_refs=remaining,
        )
        self._transactions[updated.id] = replace(
            updated,
            grounding_frontier=remaining,
        )
        return DialogueTurnResolution(
            context_ref=context_ref,
            resolution_kind="correction" if is_correction else "evidence",
            obligation_ref=obligation.obligation_id,
            transaction_ref=updated.id,
            target_artifact_ref=obligation.target_artifact_ref,
            accepted_contribution_refs=accepted_refs,
            accepted_surface_forms=accepted_surfaces,
            remaining_field_refs=remaining,
            explanation_key="report_accepted_and_remaining",
            evidence_refs=tuple(ev.evidence_ref for ev in evidence),
            suppress_fresh_lexical_gaps=True,
        )

    # Compatibility API: called after ordinary interpretation resolution.
    def consume_pending_evidence(
        self,
        selected_interpretations: list[Any] | None = None,
        *,
        context_ref: str = "default",
        surface_evidence: tuple[Any, ...] = (),
    ) -> tuple[Any, ...]:
        resolution = self.resolve_dialogue_turn(
            context_ref=context_ref,
            selected_interpretations=selected_interpretations or [],
            surface_evidence=surface_evidence,
        )
        if resolution.transaction_ref:
            tx = self._transactions.get(resolution.transaction_ref)
            return (tx,) if tx else ()
        return ()

    # ------------------------------------------------------------------
    # Child revisions and activation
    # ------------------------------------------------------------------

    def stage_revision(
        self,
        tx: LearningTransaction,
        hypothesis: SchemaHypothesis,
        contributions: tuple[StagedContribution, ...] = (),
    ) -> tuple[LearningTransaction, ChildRevision]:
        prior_child = self._children.get(tx.target_schema_ref)
        combined_contributions = tuple(dict.fromkeys(
            (*(prior_child.contributions if prior_child else ()), *contributions)
        ))
        semantic_key = self._stable_semantic_key(tx.target_sense_ref)
        existing_versions = [
            getattr(candidate, "version", 0)
            for candidate in self._store.find_candidates(semantic_key)
        ]
        version = max(existing_versions, default=0) + 1
        digest = hashlib.sha1(semantic_key.encode("utf-8")).hexdigest()[:12]
        child = self._assimilator.assimilate(
            base_schema_ref=tx.target_schema_ref,
            base_store_revision=self._store.store_revision,
            hypothesis=hypothesis,
            contributions=combined_contributions,
            grounding_spec=GroundingSpecification(
                semantic_family="lexeme_sense",
                required_definition_fields=("semantic_family",),
                allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
                minimum_independent_oracle_classes=frozenset({"invariant"}),
            ),
        )
        child = replace(child, revision_id=f"learned:lexeme:{digest}:v{version}")
        surface = self._target_surface(tx.target_sense_ref)
        draft = LearnedSchemaDraft(
            semantic_key=semantic_key,
            target_surface=surface,
            semantic_family=self._field(contributions, "semantic_family"),
            role_refs=tuple(self._field_values(contributions, "role_ref")),
            constitutive_predicate_refs=tuple(
                self._field_values(contributions, "constitutive_predicate_ref")
            ),
            related_surface_forms=tuple(
                self._field_values(contributions, "related_surface_form")
            ),
            unresolved_field_refs=tuple(tx.grounding_frontier),
        )
        record_id = child.revision_id
        scope = tx.scope if tx.scope.level == ScopeLevel.SESSION else Scope(
            level=ScopeLevel.SESSION,
            session_id=(tx.context_refs[0] if tx.context_refs else "default"),
        )
        envelope = SchemaEnvelope(
            record_id=record_id,
            semantic_key=semantic_key,
            schema_kind="lexeme_sense",
            status="candidate",
            scope=scope,
            version=version,
            payload=LexemeSenseSchema(
                semantic_key=semantic_key,
                lexical_form_refs=(),
                predicate_schema_ref="",
                part_of_speech="",
                sense_disambiguators=draft.related_surface_forms,
            ),
            confidence=max(0.2, hypothesis.confidence),
            permission=Permission(
                scope=PermissionScope.SESSION_PRIVATE,
                may_store=True,
                may_retrieve=True,
                may_use=True,
                may_share=False,
                may_execute=False,
                retention=RetentionPolicy.SESSION,
            ),
            provenance=Provenance(
                source_id=tx.id,
                source_kind="user_teaching",
                language_tag="en",
            ),
            support_refs=tuple(
                contribution.evidence_ref
                for contribution in contributions
                if contribution.evidence_ref
            ),
        )
        if self._store.get(record_id) is None:
            with self._store.transaction():
                self._store.register(envelope)
                if surface:
                    self._store.index_lexical_form(surface.lower(), "en", semantic_key)
        self._children[record_id] = child
        updated = replace(
            tx,
            status=TransactionStatus.STAGED.value,
            child_schema_revision=version,
            target_schema_ref=record_id,
        )
        self._transactions[updated.id] = updated
        return updated, child

    def attempt_activation(
        self,
        tx: LearningTransaction,
        child: ChildRevision,
        implementation_path: str = "",
        competence_cases: tuple[CompetenceCase, ...] = (),
    ) -> tuple[LearningTransaction, ActivationAttempt]:
        envelope = self._store.get(child.revision_id)
        if envelope is None:
            updated = replace(tx, status=TransactionStatus.ROLLED_BACK.value)
            self._transactions[updated.id] = updated
            return updated, ActivationAttempt(
                child_revision_ref=child.revision_id,
                rollback_reason="child schema was not committed to SemanticSchemaStore",
            )

        grounding_spec = child.grounding_spec or GroundingSpecification(
            semantic_family=envelope.schema_kind,
            required_definition_fields=(),
        )
        structural = self._closure.assess(
            envelope=envelope,
            grounding_spec=grounding_spec,
            patterns=child.patterns,
            provenance_map=child.field_provenance_map,
            environment_fingerprint=f"store:{tx.base_store_revision}",
        )
        competence = self._competence_harness.assess(
            cases=competence_cases,
            implementation_path=implementation_path,
        )
        use_profile = derive_use_profile(
            structural,
            context_ref=(tx.context_refs[0] if tx.context_refs else ""),
            competence_is_competent=competence.is_competent,
            competence_is_self_certified=competence.is_self_certified,
            # User teaching remains attributed until independently admitted.
            epistemic_admissible=True,
            scope_accessible=True,
        )
        limitations = list(structural.blocker_reasons)
        if not competence_cases:
            limitations.append("no independent competence cases supplied")
        if not competence.is_competent:
            limitations.append("independent competence not established")

        activated = False
        committed_provisional = False
        rollback_reason = ""
        current_revision = self._store.get_revision(child.revision_id)
        if current_revision is None:
            rollback_reason = "child revision is not visible"
        elif structural.is_structurally_executable and competence.is_competent:
            result = self._store.activate_with_assessment(
                child.revision_id,
                current_revision,
                grounding_assessment_ref=f"grounding:{child.revision_id}",
                competence_assessment_ref=f"competence:{child.revision_id}",
                epistemic_admissibility_ref=f"admissibility:{child.revision_id}:attributed",
                environment_fingerprint=f"store:{tx.base_store_revision}",
                grounding_assessment=structural,
                competence_assessment=competence,
            )
            activated = getattr(result.status, "value", result.status) == "success"
            if not activated:
                rollback_reason = getattr(result, "detail", "activation failed")
        else:
            # Commit a real provisional revision only when some declarative
            # contribution exists.  It remains limited to attributed/qualified
            # use and cannot become actual-world knowledge or authorize effects.
            has_minimum_session_structure = any(
                contribution.field_name == "semantic_family"
                and bool(contribution.field_value)
                for contribution in child.contributions
            )
            if has_minimum_session_structure:
                result = self._store.transition_to_provisional(
                    child.revision_id,
                    current_revision,
                )
                committed_provisional = (
                    getattr(result.status, "value", result.status) == "success"
                )
                if not committed_provisional:
                    rollback_reason = getattr(result, "detail", "provisional commit failed")
            else:
                rollback_reason = "semantic family is still unresolved"

        if activated:
            status = TransactionStatus.COMMITTED.value
        elif committed_provisional:
            status = TransactionStatus.PROVISIONAL.value
        elif envelope.status == "candidate":
            # Keep the transaction staged rather than falsely reporting rollback
            # when further user evidence can still make progress.
            status = TransactionStatus.STAGED.value
        else:
            status = TransactionStatus.ROLLED_BACK.value
        updated = replace(
            tx,
            status=status,
            structural_status=(
                "structurally_executable"
                if structural.is_structurally_executable
                else "partial"
            ),
            competence_status=(
                "independently_validated"
                if competence.is_competent
                else "limited"
            ),
            admissibility_status="attributed_only",
        )
        self._transactions[updated.id] = updated
        return updated, ActivationAttempt(
            child_revision_ref=child.revision_id,
            structural_assessment=structural,
            competence_assessment=competence,
            use_profile=use_profile,
            admissibility="attributed_only",
            activated=activated,
            committed_provisional=committed_provisional,
            limitations=tuple(dict.fromkeys(limitations)),
            rollback_reason=rollback_reason,
        )

    def provisional_replay(
        self,
        tx: LearningTransaction,
        contributions: tuple[StagedContribution, ...] = (),
        implementation_path: str = "",
    ) -> tuple[LearningTransaction, ActivationAttempt]:
        if not tx.hypotheses:
            return tx, ActivationAttempt(
                child_revision_ref="",
                rollback_reason="no hypothesis is available for replay",
            )
        best = max(tx.hypotheses, key=lambda hypothesis: hypothesis.confidence)
        updated, child = self.stage_revision(tx, best, contributions)
        return self.attempt_activation(updated, child, implementation_path)

    def rollback(self, tx: LearningTransaction) -> LearningTransaction:
        updated = replace(tx, status=TransactionStatus.ROLLED_BACK.value)
        self._transactions[updated.id] = updated
        return updated

    # ------------------------------------------------------------------
    # Frontier and completion
    # ------------------------------------------------------------------

    def compute_grounding_frontier(
        self,
        tx: LearningTransaction,
        attempt: ActivationAttempt | None = None,
        blockers: tuple[Any, ...] = (),
    ) -> GroundingFrontier:
        items: list[FrontierItem] = []
        blocker_values: list[str] = list(tx.grounding_frontier)
        if attempt and attempt.structural_assessment:
            blocker_values.extend(attempt.structural_assessment.blocker_reasons)
        blocker_values.extend(str(getattr(value, "kind", value)) for value in blockers)
        for blocker in dict.fromkeys(value for value in blocker_values if value):
            probe_key = f"probe:{tx.id}:{blocker}"
            items.append(FrontierItem(
                item_id=f"fi:{uuid4().hex[:10]}",
                dependency_ref=blocker,
                blocker_kind=blocker,
                priority=self._frontier_builder.classify_blocker(blocker),
                probe_key=probe_key,
                target_schema_ref=tx.target_schema_ref,
            ))
        return self._frontier_builder.build(
            blockers=tuple(items),
            budget=tx.budget,
            asked_probe_keys=tx.asked_probe_keys,
        )

    def check_completion_gate(
        self,
        tx: LearningTransaction,
        attempt: ActivationAttempt,
    ) -> tuple[bool, tuple[str, ...]]:
        failures: list[str] = []
        if self._store.get(attempt.child_revision_ref) is None:
            failures.append("child revision is absent from SemanticSchemaStore")
        if attempt.structural_assessment is None:
            failures.append("structural assessment missing")
        if attempt.activated and tx.status != TransactionStatus.COMMITTED.value:
            failures.append("activation is not reflected in transaction status")
        if tx.status == TransactionStatus.PROVISIONAL.value:
            if not attempt.committed_provisional:
                failures.append("provisional transaction lacks a committed provisional revision")
            if not attempt.limitations:
                failures.append("provisional limitations are absent")
        if not attempt.activated:
            failures.append("ordinary use has not passed independent competence and activation")
        return not failures, tuple(failures)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _expected_evidence_key(gap: GapRecord) -> str:
        if gap.gap_kind == "missing_semantic_family":
            return "evidence:semantic_family"
        if gap.gap_kind == "missing_required_role":
            return "evidence:role_filler"
        if gap.gap_kind in {"missing_differentiator", "sense_individuation_pending"}:
            return "evidence:differentiator"
        return "evidence:partial_definition"

    @staticmethod
    def _default_frontier(gap_kind: str) -> tuple[str, ...]:
        if gap_kind in {"missing_semantic_family", "sense_individuation_pending"}:
            return ("semantic_family", "denotation_role_or_holder")
        if gap_kind == "missing_required_role":
            return ("required_role",)
        return ("missing_definition_field",)

    @staticmethod
    def _probe_key(message_item: Any, gap: Any) -> str:
        role = message_item.role("probe_key") if hasattr(message_item, "role") else None
        value = getattr(role, "surface_hint", "") if role else ""
        return value or f"probe:{getattr(gap, 'id', '')}:{getattr(gap, 'gap_kind', '')}"

    @staticmethod
    def _is_meta_question(
        selected_interpretations: Iterable[Any],
        surface_evidence: Iterable[Any],
    ) -> bool:
        for evidence in surface_evidence:
            for cue in getattr(evidence, "pragmatic_cues", ()):
                if getattr(cue, "cue_kind", "") == "elliptical_clarification_query":
                    return True
        asks = [
            interp for interp in selected_interpretations
            if getattr(interp, "communicative_force", "") == "ask"
        ]
        return bool(asks and all(
            getattr(interp, "open_role_refs", ())
            or getattr(interp, "query_role_refs", ())
            for interp in asks
        ))

    @staticmethod
    def _choice_answer(surface_evidence: Iterable[Any]) -> str:
        semantic_keys: set[str] = set()
        for evidence in surface_evidence:
            semantic_keys.update(
                getattr(candidate, "semantic_key", "")
                for candidate in getattr(evidence, "lexical_sense_candidates", ())
                if getattr(candidate, "semantic_key", "")
            )
        if "grammar:quantifier_both" in semantic_keys or {"role", "person"} <= semantic_keys:
            return "both"
        if "role" in semantic_keys:
            return "role"
        if "person" in semantic_keys:
            return "person"
        return ""

    @staticmethod
    def _accepted_surfaces(
        surface_evidence: Iterable[Any],
        target_ref: str,
    ) -> tuple[str, ...]:
        target = LearningCoordinator._target_surface(target_ref).lower()
        blocked = {
            "a", "an", "the", "is", "are", "am", "was", "were",
            "like", "of", "to", "and", "or", "what", "which", "do",
            "does", "did", "i", "you", "it", "that", "this", "my",
            "your", "well", "mean",
        }
        values: list[str] = []
        for evidence in surface_evidence:
            stream = getattr(evidence, "token_stream", None)
            for token in getattr(stream, "tokens", ()):
                raw = getattr(token, "raw_form", "").strip()
                lemma = (
                    getattr(token, "lemma_candidates", ()) or
                    (getattr(token, "normalized_form", ""),)
                )[0].lower()
                if not raw or lemma in blocked or lemma == target or len(lemma) < 2:
                    continue
                # Preserve open-class evidence only.  This remains an observed
                # lexical mention, not a silently accepted definition field.
                values.append(raw.lower())
        return tuple(dict.fromkeys(values))

    def _typed_contributions(
        self,
        interpretations: Iterable[Any],
        accepted_surfaces: tuple[str, ...],
        evidence: tuple[EvidenceForHypothesis, ...],
    ) -> tuple[StagedContribution, ...]:
        contributions: list[StagedContribution] = []
        ev_refs = [ev.evidence_ref for ev in evidence]
        first_ev = ev_refs[0] if ev_refs else ""
        for interp in interpretations:
            predicate = getattr(interp, "predicate_semantic_key", "")
            if self._supports_family_contribution(predicate):
                contributions.append(StagedContribution(
                    field_name="semantic_family",
                    field_value="entity_kind_or_role",
                    provenance_kind=ProvenanceKind.ASSERTED,
                    evidence_ref=first_ev,
                    source_ref=getattr(interp, "proposition_ref", ""),
                    is_independent=False,
                ))
                contributions.append(StagedContribution(
                    field_name="constitutive_predicate_ref",
                    field_value=predicate,
                    provenance_kind=ProvenanceKind.ASSERTED,
                    evidence_ref=first_ev,
                    source_ref=getattr(interp, "predication_ref", ""),
                    is_independent=False,
                ))
            for binding in getattr(interp, "role_bindings", ()):
                contributions.append(StagedContribution(
                    field_name="role_ref",
                    field_value=getattr(binding, "role_schema_ref", ""),
                    provenance_kind=ProvenanceKind.OBSERVED,
                    evidence_ref=first_ev,
                    source_ref=getattr(interp, "predication_ref", ""),
                    is_independent=False,
                ))
        for surface in accepted_surfaces:
            contributions.append(StagedContribution(
                field_name="related_surface_form",
                field_value=surface,
                provenance_kind=ProvenanceKind.OBSERVED,
                evidence_ref=first_ev,
                source_ref=first_ev,
                is_independent=False,
            ))
        # Deduplicate exact field/value pairs.
        unique: dict[tuple[str, str], StagedContribution] = {}
        for contribution in contributions:
            unique[(contribution.field_name, repr(contribution.field_value))] = contribution
        return tuple(unique.values())

    def _supports_family_contribution(self, predicate_key: str) -> bool:
        active = self._store.find_active(predicate_key)
        payload = getattr(active, "payload", None) if active is not None else None
        role_refs = set(getattr(payload, "role_refs", ()) or ())
        classifying_shapes = (
            {"role:child_kind", "role:parent_kind"},
            {"role:entity", "role:kind"},
            {"role:subject", "role:complement"},
        )
        return any(shape <= role_refs for shape in classifying_shapes)

    @staticmethod
    def _remaining_frontier(
        old: tuple[str, ...],
        contributions: tuple[StagedContribution, ...],
    ) -> tuple[str, ...]:
        supplied = {contribution.field_name for contribution in contributions}
        remaining = [field for field in old if field not in supplied]
        if "semantic_family" not in supplied and "semantic_family" not in remaining:
            remaining.insert(0, "semantic_family")
        if "differentiator" not in remaining:
            remaining.append("differentiator")
        return tuple(dict.fromkeys(remaining))

    @staticmethod
    def _stable_semantic_key(target_ref: str) -> str:
        if target_ref.startswith("opaque:"):
            return target_ref
        return f"learned:{target_ref}"

    @staticmethod
    def _target_surface(target_ref: str) -> str:
        if target_ref.startswith("opaque:"):
            parts = target_ref.split(":")
            return parts[-1] if parts else ""
        if target_ref.startswith("ref:unknown:"):
            return target_ref[len("ref:unknown:"):]
        return target_ref.rsplit(":", 1)[-1] if target_ref else ""

    @staticmethod
    def _field(contributions: tuple[StagedContribution, ...], name: str) -> str:
        for contribution in contributions:
            if contribution.field_name == name:
                return str(contribution.field_value)
        return ""

    @staticmethod
    def _field_values(
        contributions: tuple[StagedContribution, ...], name: str,
    ) -> tuple[str, ...]:
        return tuple(
            str(contribution.field_value)
            for contribution in contributions
            if contribution.field_name == name and contribution.field_value
        )
