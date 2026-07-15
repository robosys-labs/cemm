"""Dialogue-grounded, schema-family-aware recursive learning."""
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
from uuid import uuid4

from ..model.dialogue import (
    DialogueObligation, DialogueTurnResolution,
)
from ..model.identity import Provenance, Scope, ScopeLevel
from ..model.learning import LearningTransaction, SchemaHypothesis
from ..schema.competence import CompetenceAssessment, CompetenceHarness
from ..schema.closure import (
    GroundedDefinitionClosure, SchemaGroundingAssessment,
)
from ..schema.store import SemanticSchemaStore
from ..schema.use_profile import SchemaUseProfile
from .assimilator import StagedContribution
from .grounding_frontier import GroundingFrontierBuilder
from .hypothesis_factory import (
    HypothesisFactory, HypothesisKind,
)
from .replay_queue import ReplayQueue
from .schema_compiler import (
    CompiledLearningArtifact, LearnedSchemaCompiler,
)

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
    structural_assessment: (
        SchemaGroundingAssessment | None
    ) = None
    competence_assessment: (
        CompetenceAssessment | None
    ) = None
    use_profile: SchemaUseProfile | None = None
    admissibility: str = "blocked"
    activated: bool = False
    committed_provisional: bool = False
    limitations: tuple[str, ...] = ()
    rollback_reason: str = ""

class LearningCoordinator:
    def __init__(
        self,
        store: SemanticSchemaStore,
        evaluator=None,
        schema_compiler=None,
        hypothesis_factory=None,
        frontier_builder=None,
        replay_queue=None,
        closure=None,
        competence_harness=None,
        **_,
    ):
        self._store = store
        self._evaluator = evaluator
        self._compiler = (
            schema_compiler or LearnedSchemaCompiler()
        )
        self._hypotheses = (
            hypothesis_factory or HypothesisFactory()
        )
        self._frontier = (
            frontier_builder or GroundingFrontierBuilder()
        )
        self._replay = replay_queue or ReplayQueue()
        self._closure = (
            closure or GroundedDefinitionClosure()
        )
        self._competence = (
            competence_harness or CompetenceHarness()
        )
        self._transactions = {}
        self._keys = {}
        self._obligations = {}
        self._artifacts: dict[
            str, CompiledLearningArtifact
        ] = {}

    def open_transaction(
        self, gap, *, context_ref="default"
    ):
        key = (
            context_ref,
            gap.target_artifact_ref,
            gap.gap_kind,
        )
        existing_id = self._keys.get(key)
        if existing_id:
            existing = self._transactions[existing_id]
            if existing.status not in {
                "committed", "rolled_back"
            }:
                return existing
        tx = LearningTransaction(
            id=f"tx:{uuid4().hex[:12]}",
            gap_ref=gap.id,
            target_sense_ref=gap.target_artifact_ref,
            target_schema_ref=gap.target_artifact_ref,
            base_store_revision=self._store.store_revision,
            expected_evidence_schema_ref=(
                gap.expected_evidence_schema_ref
                or f"evidence:{gap.gap_kind}"
            ),
            grounding_frontier=tuple(
                gap.missing_fields
                or self._default_frontier(
                    gap.gap_kind
                )
            ),
            status="open",
            scope=Scope(
                level=ScopeLevel.SESSION,
                session_id=context_ref,
            ),
            context_refs=(context_ref,),
            budget=gap.budget,
            provenance=Provenance(
                source_id=gap.id,
                source_kind="semantic_gap",
            ),
        )
        self._transactions[tx.id] = tx
        self._keys[key] = tx.id
        return tx

    def get_transaction(self, tx_id):
        return self._transactions.get(tx_id)

    def get_pending_transactions(
        self, context_ref=None
    ):
        return tuple(
            tx for tx in self._transactions.values()
            if tx.status in {
                "open", "probing", "staged",
                "provisional",
            }
            and (
                context_ref is None
                or context_ref in tx.context_refs
            )
        )

    def get_active_transactions(self):
        return self.get_pending_transactions()

    def pending_obligations(self, context_ref):
        return tuple(
            obligation
            for obligation in self._obligations.values()
            if (
                obligation.context_ref == context_ref
                and obligation.status == "pending"
            )
        )

    def register_probe_dispatch(
        self, *, context_ref, message_item,
        gaps, output_event_ref="",
    ):
        if message_item.content_kind != "learning_probe":
            return None
        gap_role = message_item.role("gap_ref")
        gap_ref = (
            gap_role.semantic_ref if gap_role else ""
        )
        gap = next(
            (item for item in gaps if item.id == gap_ref),
            None,
        )
        if gap is None:
            return None
        tx = self.open_transaction(
            gap, context_ref=context_ref
        )
        unresolved = tuple(
            gap.missing_fields
            or self._default_frontier(
                gap.gap_kind
            )
        )
        obligation = DialogueObligation(
            obligation_id=(
                f"dialogue:{uuid4().hex[:12]}"
            ),
            context_ref=context_ref,
            transaction_ref=tx.id,
            question_semantic_ref=(
                message_item.semantic_ref
            ),
            target_artifact_ref=(
                gap.target_artifact_ref
            ),
            expected_evidence_schema_refs=(
                tx.expected_evidence_schema_ref,
            ),
            unresolved_field_refs=unresolved,
            asked_probe_key=(
                f"probe:{tx.id}:{unresolved[0]}"
            ),
            output_event_ref=output_event_ref,
        )
        self._supersede_pending(tx.id)
        self._obligations[
            obligation.obligation_id
        ] = obligation
        self._transactions[tx.id] = replace(
            tx,
            status="probing",
            asked_probe_keys=frozenset((
                *tx.asked_probe_keys,
                obligation.asked_probe_key,
            )),
        )
        return obligation

    def register_followup_dispatch(
        self, *, context_ref, message_item,
        dialogue_resolution, output_event_ref="",
    ):
        tx = self._transactions.get(
            dialogue_resolution.transaction_ref
        )
        if (
            tx is None
            or not dialogue_resolution.remaining_field_refs
        ):
            return None
        obligation = DialogueObligation(
            obligation_id=(
                f"dialogue:{uuid4().hex[:12]}"
            ),
            context_ref=context_ref,
            transaction_ref=tx.id,
            question_semantic_ref=(
                message_item.semantic_ref
            ),
            target_artifact_ref=(
                dialogue_resolution.target_artifact_ref
            ),
            expected_evidence_schema_refs=(
                "evidence:"
                + dialogue_resolution.remaining_field_refs[0],
            ),
            unresolved_field_refs=(
                dialogue_resolution.remaining_field_refs
            ),
            accepted_contribution_refs=(
                dialogue_resolution
                .accepted_contribution_refs
            ),
            asked_probe_key=(
                f"probe:{tx.id}:"
                f"{dialogue_resolution.remaining_field_refs[0]}"
            ),
            output_event_ref=output_event_ref,
        )
        self._supersede_pending(tx.id)
        self._obligations[
            obligation.obligation_id
        ] = obligation
        return obligation

    def resolve_dialogue_turn(
        self, *, context_ref,
        selected_interpretations,
        surface_evidence,
    ):
        obligations = self.pending_obligations(
            context_ref
        )
        if not obligations:
            return DialogueTurnResolution(
                context_ref=context_ref
            )
        obligation = obligations[-1]
        tx = self._transactions.get(
            obligation.transaction_ref
        )
        if tx is None:
            return DialogueTurnResolution(
                context_ref=context_ref
            )

        if self._is_meta_question(
            selected_interpretations,
            surface_evidence,
        ):
            return DialogueTurnResolution(
                context_ref=context_ref,
                resolution_kind="meta_question",
                obligation_ref=(
                    obligation.obligation_id
                ),
                transaction_ref=tx.id,
                target_artifact_ref=(
                    obligation.target_artifact_ref
                ),
                remaining_field_refs=(
                    obligation.unresolved_field_refs
                ),
                explanation_key=(
                    "explain_pending_learning_frontier"
                ),
                evidence_refs=(
                    obligation.question_semantic_ref,
                ),
                suppress_fresh_lexical_gaps=True,
            )

        assertions = tuple(
            item
            for item in selected_interpretations
            if item.communicative_force
            in {"assert", "correct"}
        )
        rule_candidates = tuple(
            candidate
            for evidence in surface_evidence
            for candidate in getattr(
                evidence, "rule_candidates", ()
            )
        )
        if not assertions and not rule_candidates:
            return DialogueTurnResolution(
                context_ref=context_ref
            )

        contributions = self._typed_contributions(
            assertions, surface_evidence
        )
        evidence_refs = tuple(
            f"learning_evidence:{item.proposition_ref}"
            for item in assertions
        ) or tuple(
            "learning_rule_evidence:"
            + candidate.construction_key
            for candidate in rule_candidates
        )
        tx = replace(
            tx,
            status="probing",
            hypotheses=(SchemaHypothesis(
                hypothesis_kind=(
                    HypothesisKind.NEW_SENSE.value
                ),
                target_sense_ref=(
                    tx.target_sense_ref
                ),
                confidence=max(
                    (
                        item.confidence
                        for item in assertions
                    ),
                    default=0.55,
                ),
            ),),
            acquired_evidence_refs=tuple(
                dict.fromkeys((
                    *tx.acquired_evidence_refs,
                    *evidence_refs,
                ))
            ),
        )
        self._transactions[tx.id] = tx

        artifact = self._compiler.compile(
            target_semantic_key=self._stable_key(
                tx.target_sense_ref
            ),
            target_surface=self._surface(
                tx.target_sense_ref
            ),
            language_tag=(
                surface_evidence[0].language_tag
                if surface_evidence else "und"
            ),
            scope=tx.scope,
            contributions=contributions,
            rule_candidates=rule_candidates,
            source_ref=tx.id,
            version=(tx.child_schema_revision or 0) + 1,
        )
        self._install_artifact(artifact)
        self._artifacts[tx.id] = artifact
        status = (
            "provisional"
            if self._has_minimum_structure(
                artifact
            )
            else "staged"
        )
        if status == "provisional":
            self._transition_provisional(
                artifact
            )
        remaining = tuple(dict.fromkeys((
            *artifact.unresolved_fields,
            "independent_competence",
        )))
        tx = replace(
            tx,
            status=status,
            target_schema_ref=(
                artifact.primary_envelope.record_id
            ),
            child_schema_revision=(
                artifact.primary_envelope.version
            ),
            grounding_frontier=remaining,
            structural_status=(
                "partial"
                if remaining
                else "structurally_executable"
            ),
            competence_status="limited",
            admissibility_status=(
                "attributed_only"
            ),
        )
        self._transactions[tx.id] = tx
        self._obligations[
            obligation.obligation_id
        ] = replace(
            obligation,
            status="answered",
            accepted_contribution_refs=(
                evidence_refs
            ),
            unresolved_field_refs=remaining,
        )
        return DialogueTurnResolution(
            context_ref=context_ref,
            resolution_kind="evidence",
            obligation_ref=(
                obligation.obligation_id
            ),
            transaction_ref=tx.id,
            target_artifact_ref=(
                obligation.target_artifact_ref
            ),
            accepted_contribution_refs=(
                evidence_refs
            ),
            accepted_surface_forms=(
                self._accepted_surfaces(
                    surface_evidence
                )
            ),
            remaining_field_refs=remaining,
            explanation_key=(
                "report_accepted_and_remaining"
            ),
            evidence_refs=evidence_refs,
            suppress_fresh_lexical_gaps=True,
        )

    def consume_pending_evidence(
        self, selected_interpretations=None,
        *, context_ref="default",
        surface_evidence=(),
    ):
        resolution = self.resolve_dialogue_turn(
            context_ref=context_ref,
            selected_interpretations=(
                selected_interpretations or ()
            ),
            surface_evidence=surface_evidence,
        )
        tx = self._transactions.get(
            resolution.transaction_ref
        )
        return (tx,) if tx else ()

    def check_completion_gate(self, tx, attempt):
        failures = []
        artifact = self._artifacts.get(tx.id)
        if artifact is None:
            failures.append(
                "compiled artifact missing"
            )
        elif self._store.get(
            artifact.primary_envelope.record_id
        ) is None:
            failures.append(
                "artifact absent from schema store"
            )
        if tx.status != "committed":
            failures.append(
                "competence/replay/activation incomplete"
            )
        return not failures, tuple(failures)

    def _install_artifact(self, artifact):
        for envelope in (
            artifact.primary_envelope,
            *artifact.auxiliary_envelopes,
        ):
            if self._store.get(
                envelope.record_id
            ) is None:
                self._store.register(
                    envelope,
                    dependencies=(
                        artifact.dependencies
                        if envelope.record_id
                        == artifact
                        .primary_envelope.record_id
                        else ()
                    ),
                )
                for lexical_form in getattr(
                    envelope.payload,
                    "lexical_form_refs",
                    (),
                ):
                    self._store.index_lexical_form(
                        lexical_form.normalised,
                        lexical_form.language_tag,
                        getattr(
                            envelope.payload,
                            "semantic_key",
                            envelope.semantic_key,
                        ),
                    )

    def _transition_provisional(
        self, artifact
    ):
        for envelope in (
            artifact.primary_envelope,
            *artifact.auxiliary_envelopes,
        ):
            revision = self._store.get_revision(
                envelope.record_id
            )
            if revision is not None:
                self._store.transition_to_provisional(
                    envelope.record_id,
                    revision,
                )

    def _typed_contributions(
        self, interpretations, evidence
    ):
        result = []
        evidence_ref = (
            "learning_evidence:"
            + interpretations[0].proposition_ref
            if interpretations else ""
        )
        for interpretation in interpretations:
            predicate = (
                interpretation
                .predicate_semantic_key
            )
            if predicate == "subkind_of":
                result.append(
                    StagedContribution(
                        field_name="semantic_family",
                        field_value="entity_kind",
                        provenance_kind="asserted",
                        evidence_ref=evidence_ref,
                        source_ref=(
                            interpretation
                            .proposition_ref
                        ),
                    )
                )
                parent = next(
                    (
                        binding.filler_ref
                        for binding in
                        interpretation.role_bindings
                        if binding.role_schema_ref
                        == "role:parent_kind"
                    ),
                    "",
                )
                if parent:
                    result.append(
                        StagedContribution(
                            field_name=(
                                "parent_kind_ref"
                            ),
                            field_value=parent,
                            provenance_kind=(
                                "asserted"
                            ),
                            evidence_ref=evidence_ref,
                            source_ref=(
                                interpretation
                                .predication_ref
                            ),
                        )
                    )
            elif predicate == "means":
                result.append(
                    StagedContribution(
                        field_name=(
                            "semantic_family"
                        ),
                        field_value=(
                            "lexeme_sense"
                        ),
                        provenance_kind="asserted",
                        evidence_ref=evidence_ref,
                        source_ref=(
                            interpretation
                            .proposition_ref
                        ),
                    )
                )
            for binding in (
                interpretation.role_bindings
            ):
                result.append(
                    StagedContribution(
                        field_name="role_ref",
                        field_value=(
                            binding.role_schema_ref
                        ),
                        provenance_kind="observed",
                        evidence_ref=evidence_ref,
                        source_ref=(
                            interpretation
                            .predication_ref
                        ),
                    )
                )
        for surface in self._accepted_surfaces(
            evidence
        ):
            result.append(
                StagedContribution(
                    field_name=(
                        "related_surface_form"
                    ),
                    field_value=surface,
                    provenance_kind="observed",
                    evidence_ref=evidence_ref,
                    source_ref=evidence_ref,
                )
            )
        unique = {}
        for item in result:
            unique[
                (
                    item.field_name,
                    repr(item.field_value),
                )
            ] = item
        return tuple(unique.values())

    @staticmethod
    def _accepted_surfaces(evidence):
        values = []
        for item in evidence:
            for candidate in (
                item.lexical_sense_candidates
            ):
                if candidate.semantic_key.startswith((
                    "grammar:", "pronoun:",
                    "wh:", "aux:", "polarity:",
                )):
                    continue
                values.append(
                    candidate.lexical_form_ref
                    .surface.casefold()
                )
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _is_meta_question(
        interpretations, evidence
    ):
        return any(
            cue.cue_kind
            == "elliptical_clarification_query"
            for item in evidence
            for cue in item.pragmatic_cues
        )

    def _supersede_pending(self, tx_id):
        for key, obligation in tuple(
            self._obligations.items()
        ):
            if (
                obligation.transaction_ref == tx_id
                and obligation.status == "pending"
            ):
                self._obligations[key] = replace(
                    obligation,
                    status="superseded",
                )

    @staticmethod
    def _has_minimum_structure(
        artifact
    ):
        return (
            artifact.primary_envelope.schema_kind
            != "lexeme_sense"
            and "semantic_family"
            not in artifact.unresolved_fields
        )

    @staticmethod
    def _stable_key(target):
        return (
            target
            if target.startswith("opaque:")
            else f"learned:{target}"
        )

    @staticmethod
    def _surface(target):
        if target.startswith("opaque:"):
            return target.split(
                ":", 2
            )[-1].replace("_", " ")
        return target.rsplit(":", 1)[-1]

    @staticmethod
    def _default_frontier(kind):
        if kind in {
            "missing_semantic_family",
            "sense_individuation_pending",
        }:
            return (
                "semantic_family",
                "constitutive_structure",
            )
        if kind == "missing_required_role":
            return ("required_role",)
        return ("missing_definition_field",)
