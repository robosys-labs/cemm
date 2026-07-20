"""Typed repositories over the layered CEMM v3.5 semantic store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, Iterable, TypeVar

from ..schema.model import (
    FacetEntitlement, MeaningSchema, SchemaClass, SchemaLifecycleStatus, UseOperation,
)
from ..schema.registry import SchemaRegistry
from ..language.model import (
    ConstructionRecord, FormSenseLinkRecord, LanguageFormRecord,
    LanguagePackRecord, LexicalSenseRecord,
)
from ..language.registry import LanguageRegistry
from ..transitions.model import CapabilityDependencyRecord, TransitionContractRecord, TransitionProofRecord
from ..learning.model import (
    CompetenceResultRecord, LearningEvidenceLink, LearningFrontierRecord,
    LearningInvalidationRecord, LearningPackageRecord, PromotionDecisionRecord,
)
from ..significance.model import (
    ImpactProofRecord, ImpactRuleRecord, ImportanceEvidenceRecord, ImportancePolicyRecord,
    SignificanceAssessmentRecord,
)
from ..goals.model import (
    GoalCandidateRecord, GoalConflictRecord, GoalDecisionRecord, ResponsePolicyRuleRecord,
    SemanticObligationRecord,
)
from ..operations.model import OperationAdapterContractRecord, OperationAuthorizationRecord, OperationGateAssessmentRecord, OperationJournalRecord, OperationPlanRecord, OperationReconciliationRecord, OperationResultRecord
from ..response.model import ResponseOmissionRecord, ResponseTransformationProof, ResponseTransformRuleRecord, ResponseUOLRecord
from ..realization.model import ArgumentFrameRecord, DeepClausePlanRecord, LinearizationRuleRecord, MorphologyRuleRecord, RealizationRequestRecord, ReferencePlanRecord, SemanticAnalyzerContractRecord, SemanticRoundTripRecord, SurfaceCandidateRecord
from ..output.model import ChannelAdapterContractRecord, LiteralEmissionPolicyRecord, EmissionGateAssessmentRecord, EmissionAuthorizationRecord, EmissionJournalRecord, EmissionRecord, EmissionAnomalyRecord, SilenceOutcomeRecord, OutputDiscourseActRecord, OutputCommitmentRecord, CommonGroundRecord, OutputReferenceAnchorRecord, OutputCorrectionRecord
from ..migration_records.model import MigrationSourceRecord, MigrationRuleRecord, MigrationTargetMapRecord, MigrationDecisionRecord, MigrationBatchRecord, MigrationQuarantineRecord, MigrationIntentionalChangeRecord, SemanticEquivalenceRecord, MigrationRollbackRecord
from ..uol.model import (
    CapabilityDelta,
    ClaimOccurrence,
    EventOccurrence,
    ImpactAssessment,
    ImportanceAssessment,
    PropositionReferent,
    Referent,
    SemanticApplication,
    StateDelta,
)
from .model import (
    CapabilityInstance,
    ClaimHistoryRecord,
    ClaimRecord,
    DefaultRuleRecord,
    EpistemicAdmissionRecord,
    EvidenceRecord,
    IdentityFacetRecord,
    KnowledgeRecord,
    MaterializedViewRecord,
    RecordKind,
    ReferentTypeAssertion,
    SourceAssessmentRecord,
    StateAssignment,
    StoreSnapshot,
    StoredRecord,
)


T = TypeVar("T")


class TypedRepository(Generic[T]):
    def __init__(self, store, record_kind: RecordKind, expected_type: type[T]):
        self._store = store
        self.record_kind = record_kind
        self.expected_type = expected_type

    def get(
        self,
        record_ref: str,
        revision: int | None = None,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> StoredRecord[T] | None:
        stored = self._store.get_record(
            self.record_kind, record_ref, revision, snapshot=snapshot
        )
        if stored is None:
            return None
        if not isinstance(stored.payload, self.expected_type):
            raise TypeError(
                f"{self.record_kind.value} repository decoded {type(stored.payload).__name__}"
            )
        return stored

    def require(
        self,
        record_ref: str,
        revision: int | None = None,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> StoredRecord[T]:
        stored = self.get(record_ref, revision, snapshot=snapshot)
        if stored is None:
            suffix = "" if revision is None else f"@{revision}"
            raise KeyError(f"{self.record_kind.value}:{record_ref}{suffix}")
        return stored

    def all(
        self,
        *,
        all_revisions: bool = False,
        snapshot: StoreSnapshot | None = None,
        include_invalidated: bool = False,
    ) -> tuple[StoredRecord[T], ...]:
        result = self._store.records(
            self.record_kind,
            all_revisions=all_revisions,
            snapshot=snapshot,
        )
        if not include_invalidated:
            result = tuple(
                item
                for item in result
                if not self._store.is_invalidated(
                    item.record_kind, item.record_ref, item.revision
                )
            )
        for item in result:
            if not isinstance(item.payload, self.expected_type):
                raise TypeError(
                    f"{self.record_kind.value} repository decoded {type(item.payload).__name__}"
                )
        return result  # type: ignore[return-value]


class SchemaRepository(TypedRepository[MeaningSchema]):
    def __init__(self, store):
        super().__init__(store, RecordKind.SCHEMA, MeaningSchema)
        self._registry_cache: dict[tuple[int, str, str], SchemaRegistry] = {}

    def registry(self, *, snapshot: StoreSnapshot | None = None) -> SchemaRegistry:
        if snapshot is None:
            key = (
                self._store.revision,
                self._store.boot_fingerprint,
                self._store.overlay_fingerprint,
            )
        else:
            self._store.assert_snapshot(snapshot)
            key = (
                snapshot.store_revision,
                snapshot.boot_fingerprint,
                snapshot.overlay_fingerprint,
            )
        cached = self._registry_cache.get(key)
        if cached is not None:
            return cached
        schemas = tuple(item.payload for item in self.all(all_revisions=True, snapshot=snapshot))
        entitlements = tuple(
            item.payload
            for item in self._store.records(
                RecordKind.FACET_ENTITLEMENT,
                all_revisions=True,
                snapshot=snapshot,
            )
            if isinstance(item.payload, FacetEntitlement)
        )
        registry = SchemaRegistry(schemas, entitlements)
        # A store revision uniquely pins the overlay; retain only the current
        # snapshot to prevent an unbounded cache in long-running processes.
        self._registry_cache = {key: registry}
        return registry

    def authoritative(
        self, schema_ref: str, *, snapshot: StoreSnapshot | None = None
    ) -> MeaningSchema:
        return self.registry(snapshot=snapshot).authoritative_schema(schema_ref)

    def for_use(
        self,
        schema_ref: str,
        operation: UseOperation | str,
        *,
        provisional: bool = False,
        snapshot: StoreSnapshot | None = None,
    ) -> MeaningSchema:
        return self.registry(snapshot=snapshot).schema_for_use(
            schema_ref, operation, provisional=provisional
        )

    def by_class(
        self,
        schema_class: SchemaClass,
        *,
        active_only: bool = False,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[MeaningSchema, ...]:
        registry = self.registry(snapshot=snapshot)
        if active_only:
            return registry.active_schemas(schema_class)
        return tuple(
            item
            for item in registry.iter_schemas()
            if item.schema_class == schema_class
        )


class EntitlementRepository(TypedRepository[FacetEntitlement]):
    def __init__(self, store):
        super().__init__(store, RecordKind.FACET_ENTITLEMENT, FacetEntitlement)

    def for_type(
        self,
        type_ref: str,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[FacetEntitlement, ...]:
        registry = self._store.repositories.schemas.registry(snapshot=snapshot)
        return registry.entitlements_for_type(type_ref)


class ReferentRepository(TypedRepository[Referent]):
    def __init__(self, store):
        super().__init__(store, RecordKind.REFERENT, Referent)

    def type_assertions(
        self,
        referent_ref: str,
        *,
        context_ref: str | None = None,
        at_time: str | datetime | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[ReferentTypeAssertion, ...]:
        items = []
        for stored in self._store.repositories.type_assertions.all(snapshot=snapshot):
            assertion = stored.payload
            if assertion.referent_ref != referent_ref:
                continue
            if context_ref is not None and assertion.context_ref not in {"global", context_ref}:
                continue
            if not interval_contains(assertion.valid_from, assertion.valid_to, at_time):
                continue
            items.append(assertion)
        return tuple(sorted(items, key=lambda item: (item.type_schema_ref, item.assertion_ref)))

    def identity_facets(
        self,
        referent_ref: str,
        *,
        context_ref: str | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[IdentityFacetRecord, ...]:
        result = []
        for stored in self._store.repositories.identity_facets.all(snapshot=snapshot):
            item = stored.payload
            if item.referent_ref == referent_ref and (
                context_ref is None or item.context_ref in {"global", context_ref}
            ):
                result.append(item)
        return tuple(sorted(result, key=lambda item: item.identity_facet_ref))


class ApplicationRepository(TypedRepository[SemanticApplication]):
    def __init__(self, store):
        super().__init__(store, RecordKind.SEMANTIC_APPLICATION, SemanticApplication)

    def for_schema(
        self,
        schema_ref: str,
        *,
        context_ref: str | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[SemanticApplication, ...]:
        result = []
        for stored in self.all(snapshot=snapshot):
            item = stored.payload
            if item.schema_ref == schema_ref and (
                context_ref is None or item.context_ref == context_ref
            ):
                result.append(item)
        return tuple(sorted(result, key=lambda item: item.application_ref))

    def involving(
        self,
        referent_ref: str,
        *,
        context_ref: str | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[SemanticApplication, ...]:
        result = []
        for stored in self.all(snapshot=snapshot):
            item = stored.payload
            if context_ref is not None and item.context_ref != context_ref:
                continue
            if any(
                getattr(filler, "ref", None) == referent_ref
                for binding in item.bindings
                for filler in binding.fillers
            ):
                result.append(item)
        return tuple(sorted(result, key=lambda item: item.application_ref))


class KnowledgeRepository(TypedRepository[KnowledgeRecord]):
    def __init__(self, store):
        super().__init__(store, RecordKind.KNOWLEDGE, KnowledgeRecord)

    def for_proposition(
        self,
        proposition_ref: str,
        *,
        context_ref: str | None = None,
        at_time: str | datetime | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[KnowledgeRecord, ...]:
        result = []
        for stored in self.all(snapshot=snapshot):
            item = stored.payload
            if item.proposition_ref != proposition_ref:
                continue
            if context_ref is not None and item.context_ref not in {"global", context_ref}:
                continue
            if not interval_contains(item.valid_from, item.valid_to, at_time):
                continue
            if item.superseded_by is None:
                result.append(item)
        return tuple(sorted(result, key=lambda item: item.knowledge_ref))


class EventStateRepository:
    def __init__(self, store):
        self._store = store

    def events(
        self,
        referent_ref: str,
        *,
        context_ref: str | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[EventOccurrence, ...]:
        applications = {
            item.application_ref: item
            for item in self._store.repositories.applications.involving(
                referent_ref, context_ref=context_ref, snapshot=snapshot
            )
        }
        result = []
        for stored in self._store.repositories.event_occurrences.all(snapshot=snapshot):
            event = stored.payload
            if event.participant_application_ref in applications and (
                context_ref is None or event.context_ref == context_ref
            ):
                result.append(event)
        return tuple(sorted(result, key=lambda item: item.event_ref))

    def state_timeline(
        self,
        holder_ref: str,
        dimension_ref: str | None = None,
        *,
        context_ref: str | None = None,
        at_time: str | datetime | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[StateAssignment, ...]:
        result = []
        for stored in self._store.repositories.state_assignments.all(snapshot=snapshot):
            item = stored.payload
            if item.holder_ref != holder_ref:
                continue
            if dimension_ref is not None and item.dimension_ref != dimension_ref:
                continue
            if context_ref is not None and item.context_ref not in {"global", context_ref}:
                continue
            if not interval_contains(item.valid_from, item.valid_to, at_time):
                continue
            result.append(item)
        return tuple(
            sorted(
                result,
                key=lambda item: (
                    item.dimension_ref,
                    item.valid_from or "",
                    item.assignment_ref,
                ),
            )
        )

    def state_deltas(
        self,
        holder_ref: str,
        *,
        context_ref: str | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[StateDelta, ...]:
        result = []
        for stored in self._store.repositories.state_deltas.all(snapshot=snapshot):
            item = stored.payload
            if item.holder_ref == holder_ref and (
                context_ref is None or item.context_ref == context_ref
            ):
                result.append(item)
        return tuple(sorted(result, key=lambda item: item.delta_ref))

    def capabilities(
        self,
        holder_ref: str,
        *,
        context_ref: str | None = None,
        at_time: str | datetime | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[CapabilityInstance, ...]:
        result = []
        for stored in self._store.repositories.capability_instances.all(snapshot=snapshot):
            item = stored.payload
            if item.holder_ref != holder_ref:
                continue
            if context_ref is not None and item.context_ref not in {"global", context_ref}:
                continue
            if not interval_contains(item.valid_from, item.valid_to, at_time):
                continue
            result.append(item)
        return tuple(sorted(result, key=lambda item: (item.action_schema_ref, item.capability_ref)))


class DefaultRuleRepository(TypedRepository[DefaultRuleRecord]):
    def __init__(self, store):
        super().__init__(store, RecordKind.DEFAULT_RULE, DefaultRuleRecord)

    def authoritative(
        self, rule_ref: str, *, snapshot: StoreSnapshot | None = None
    ) -> DefaultRuleRecord:
        revisions = [
            item.payload for item in self.all(all_revisions=True, snapshot=snapshot)
            if item.record_ref == rule_ref
        ]
        if not revisions:
            raise KeyError(rule_ref)
        superseded = {
            item.supersedes_revision for item in revisions
            if item.supersedes_revision is not None
            and item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
        }
        usable = [
            item for item in revisions
            if item.revision not in superseded
            and item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
        ]
        if not usable:
            raise KeyError(f"no usable default-rule revision for {rule_ref}")
        rank = {
            SchemaLifecycleStatus.CANDIDATE: 0,
            SchemaLifecycleStatus.STRUCTURALLY_CLOSED: 1,
            SchemaLifecycleStatus.PROVISIONAL: 2,
            SchemaLifecycleStatus.COMPETENCE_VERIFIED: 3,
            SchemaLifecycleStatus.ACTIVE: 4,
            SchemaLifecycleStatus.SUPERSEDED: -1,
            SchemaLifecycleStatus.REJECTED: -1,
        }
        return max(usable, key=lambda item: (rank[item.lifecycle_status], item.revision))

    def for_facet(
        self,
        facet_ref: str,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[DefaultRuleRecord, ...]:
        refs = {
            item.record_ref for item in self.all(all_revisions=True, snapshot=snapshot)
            if item.payload.target_facet_ref == facet_ref
        }
        result = []
        for ref in sorted(refs):
            try:
                item = self.authoritative(ref, snapshot=snapshot)
            except KeyError:
                continue
            if item.target_facet_ref == facet_ref:
                result.append(item)
        return tuple(sorted(result, key=lambda item: (-item.priority, item.rule_ref)))


class MaterializedViewRepository(TypedRepository[MaterializedViewRecord]):
    def __init__(self, store):
        super().__init__(store, RecordKind.MATERIALIZED_VIEW, MaterializedViewRecord)

    def valid(
        self,
        view_ref: str,
        *,
        snapshot: StoreSnapshot | None = None,
    ) -> MaterializedViewRecord | None:
        return self._store.materialized_view(view_ref, snapshot=snapshot)


class LanguageRepository:
    def __init__(self, store: Any) -> None:
        self._store = store
        self.packs = TypedRepository(store, RecordKind.LANGUAGE_PACK, LanguagePackRecord)
        self.forms = TypedRepository(store, RecordKind.LANGUAGE_FORM, LanguageFormRecord)
        self.senses = TypedRepository(store, RecordKind.LEXICAL_SENSE, LexicalSenseRecord)
        self.links = TypedRepository(store, RecordKind.FORM_SENSE_LINK, FormSenseLinkRecord)
        self.constructions = TypedRepository(store, RecordKind.CONSTRUCTION, ConstructionRecord)
        self._registry_cache: dict[tuple[int, str, str], LanguageRegistry] = {}

    def registry(self, *, snapshot: StoreSnapshot | None = None) -> LanguageRegistry:
        if snapshot is None:
            key = (self._store.revision, self._store.boot_fingerprint, self._store.overlay_fingerprint)
        else:
            self._store.assert_snapshot(snapshot)
            key = (snapshot.store_revision, snapshot.boot_fingerprint, snapshot.overlay_fingerprint)
        cached = self._registry_cache.get(key)
        if cached is not None:
            return cached
        registry = LanguageRegistry(
            (item.payload for item in self.packs.all(snapshot=snapshot, all_revisions=True)),
            (item.payload for item in self.forms.all(snapshot=snapshot, all_revisions=True)),
            (item.payload for item in self.senses.all(snapshot=snapshot, all_revisions=True)),
            (item.payload for item in self.links.all(snapshot=snapshot, all_revisions=True)),
            (item.payload for item in self.constructions.all(snapshot=snapshot, all_revisions=True)),
        )
        self._registry_cache = {key: registry}
        return registry


class RepositorySet:
    """Stable typed repository façade bound to one store instance.

    The façade is intentionally a regular class rather than a slotted frozen
    dataclass: repositories are constructed lazily by :class:`SemanticStore`
    and are fixed by convention after initialization.  Declaring undeclared
    attributes on a slotted dataclass made this composition root invalid.
    """

    def __init__(self, store: Any) -> None:
        self.store = store
        self.schemas = SchemaRepository(store)
        self.entitlements = EntitlementRepository(store)
        self.referents = ReferentRepository(store)
        self.type_assertions = TypedRepository(store, RecordKind.TYPE_ASSERTION, ReferentTypeAssertion)
        self.identity_facets = TypedRepository(store, RecordKind.IDENTITY_FACET, IdentityFacetRecord)
        self.applications = ApplicationRepository(store)
        self.propositions = TypedRepository(store, RecordKind.PROPOSITION, PropositionReferent)
        self.claim_occurrences = TypedRepository(store, RecordKind.CLAIM_OCCURRENCE, ClaimOccurrence)
        self.claim_records = TypedRepository(store, RecordKind.CLAIM_RECORD, ClaimRecord)
        self.claim_history = TypedRepository(store, RecordKind.CLAIM_HISTORY, ClaimHistoryRecord)
        self.epistemic_admissions = TypedRepository(store, RecordKind.EPISTEMIC_ADMISSION, EpistemicAdmissionRecord)
        self.source_assessments = TypedRepository(store, RecordKind.SOURCE_ASSESSMENT, SourceAssessmentRecord)
        self.knowledge = KnowledgeRepository(store)
        self.event_occurrences = TypedRepository(store, RecordKind.EVENT_OCCURRENCE, EventOccurrence)
        self.state_assignments = TypedRepository(store, RecordKind.STATE_ASSIGNMENT, StateAssignment)
        self.state_deltas = TypedRepository(store, RecordKind.STATE_DELTA, StateDelta)
        self.capability_instances = TypedRepository(store, RecordKind.CAPABILITY_INSTANCE, CapabilityInstance)
        self.capability_deltas = TypedRepository(store, RecordKind.CAPABILITY_DELTA, CapabilityDelta)
        self.transition_contracts = TypedRepository(store, RecordKind.TRANSITION_CONTRACT, TransitionContractRecord)
        self.capability_dependencies = TypedRepository(store, RecordKind.CAPABILITY_DEPENDENCY, CapabilityDependencyRecord)
        self.transition_proofs = TypedRepository(store, RecordKind.TRANSITION_PROOF, TransitionProofRecord)
        self.impact_assessments = TypedRepository(store, RecordKind.IMPACT_ASSESSMENT, ImpactAssessment)
        self.importance_assessments = TypedRepository(store, RecordKind.IMPORTANCE_ASSESSMENT, ImportanceAssessment)
        self.impact_rules = TypedRepository(store, RecordKind.IMPACT_RULE, ImpactRuleRecord)
        self.impact_proofs = TypedRepository(store, RecordKind.IMPACT_PROOF, ImpactProofRecord)
        self.importance_evidence = TypedRepository(store, RecordKind.IMPORTANCE_EVIDENCE, ImportanceEvidenceRecord)
        self.importance_policies = TypedRepository(store, RecordKind.IMPORTANCE_POLICY, ImportancePolicyRecord)
        self.significance_assessments = TypedRepository(store, RecordKind.SIGNIFICANCE_ASSESSMENT, SignificanceAssessmentRecord)
        self.response_policy_rules = TypedRepository(store, RecordKind.RESPONSE_POLICY_RULE, ResponsePolicyRuleRecord)
        self.semantic_obligations = TypedRepository(store, RecordKind.SEMANTIC_OBLIGATION, SemanticObligationRecord)
        self.goal_candidates = TypedRepository(store, RecordKind.GOAL_CANDIDATE, GoalCandidateRecord)
        self.goal_conflicts = TypedRepository(store, RecordKind.GOAL_CONFLICT, GoalConflictRecord)
        self.goal_decisions = TypedRepository(store, RecordKind.GOAL_DECISION, GoalDecisionRecord)
        self.operation_adapter_contracts = TypedRepository(store, RecordKind.OPERATION_ADAPTER_CONTRACT, OperationAdapterContractRecord)
        self.operation_gate_assessments = TypedRepository(store, RecordKind.OPERATION_GATE_ASSESSMENT, OperationGateAssessmentRecord)
        self.operation_plans = TypedRepository(store, RecordKind.OPERATION_PLAN, OperationPlanRecord)
        self.operation_authorizations = TypedRepository(store, RecordKind.OPERATION_AUTHORIZATION, OperationAuthorizationRecord)
        self.operation_journals = TypedRepository(store, RecordKind.OPERATION_JOURNAL, OperationJournalRecord)
        self.operation_results = TypedRepository(store, RecordKind.OPERATION_RESULT, OperationResultRecord)
        self.operation_reconciliations = TypedRepository(store, RecordKind.OPERATION_RECONCILIATION, OperationReconciliationRecord)
        self.response_transform_rules = TypedRepository(store, RecordKind.RESPONSE_TRANSFORM_RULE, ResponseTransformRuleRecord)
        self.response_transformation_proofs = TypedRepository(store, RecordKind.RESPONSE_TRANSFORMATION_PROOF, ResponseTransformationProof)
        self.response_omissions = TypedRepository(store, RecordKind.RESPONSE_OMISSION, ResponseOmissionRecord)
        self.response_uol = TypedRepository(store, RecordKind.RESPONSE_UOL, ResponseUOLRecord)
        self.realization_requests = TypedRepository(store, RecordKind.REALIZATION_REQUEST, RealizationRequestRecord)
        self.argument_frames = TypedRepository(store, RecordKind.ARGUMENT_FRAME, ArgumentFrameRecord)
        self.morphology_rules = TypedRepository(store, RecordKind.MORPHOLOGY_RULE, MorphologyRuleRecord)
        self.linearization_rules = TypedRepository(store, RecordKind.LINEARIZATION_RULE, LinearizationRuleRecord)
        self.deep_clause_plans = TypedRepository(store, RecordKind.DEEP_CLAUSE_PLAN, DeepClausePlanRecord)
        self.reference_plans = TypedRepository(store, RecordKind.REFERENCE_PLAN, ReferencePlanRecord)
        self.surface_candidates = TypedRepository(store, RecordKind.SURFACE_CANDIDATE, SurfaceCandidateRecord)
        self.semantic_roundtrips = TypedRepository(store, RecordKind.SEMANTIC_ROUNDTRIP, SemanticRoundTripRecord)
        self.semantic_analyzer_contracts = TypedRepository(store, RecordKind.SEMANTIC_ANALYZER_CONTRACT, SemanticAnalyzerContractRecord)
        self.channel_adapter_contracts = TypedRepository(store, RecordKind.CHANNEL_ADAPTER_CONTRACT, ChannelAdapterContractRecord)
        self.literal_emission_policies = TypedRepository(store, RecordKind.LITERAL_EMISSION_POLICY, LiteralEmissionPolicyRecord)
        self.emission_gate_assessments = TypedRepository(store, RecordKind.EMISSION_GATE_ASSESSMENT, EmissionGateAssessmentRecord)
        self.emission_authorizations = TypedRepository(store, RecordKind.EMISSION_AUTHORIZATION, EmissionAuthorizationRecord)
        self.emission_journals = TypedRepository(store, RecordKind.EMISSION_JOURNAL, EmissionJournalRecord)
        self.emissions = TypedRepository(store, RecordKind.EMISSION, EmissionRecord)
        self.emission_anomalies = TypedRepository(store, RecordKind.EMISSION_ANOMALY, EmissionAnomalyRecord)
        self.silence_outcomes = TypedRepository(store, RecordKind.SILENCE_OUTCOME, SilenceOutcomeRecord)
        self.output_discourse_acts = TypedRepository(store, RecordKind.OUTPUT_DISCOURSE_ACT, OutputDiscourseActRecord)
        self.output_commitments = TypedRepository(store, RecordKind.OUTPUT_COMMITMENT, OutputCommitmentRecord)
        self.common_ground = TypedRepository(store, RecordKind.COMMON_GROUND, CommonGroundRecord)
        self.output_reference_anchors = TypedRepository(store, RecordKind.OUTPUT_REFERENCE_ANCHOR, OutputReferenceAnchorRecord)
        self.output_corrections = TypedRepository(store, RecordKind.OUTPUT_CORRECTION, OutputCorrectionRecord)
        self.migration_sources = TypedRepository(store, RecordKind.MIGRATION_SOURCE, MigrationSourceRecord)
        self.migration_rules = TypedRepository(store, RecordKind.MIGRATION_RULE, MigrationRuleRecord)
        self.migration_target_maps = TypedRepository(store, RecordKind.MIGRATION_TARGET_MAP, MigrationTargetMapRecord)
        self.migration_decisions = TypedRepository(store, RecordKind.MIGRATION_DECISION, MigrationDecisionRecord)
        self.migration_batches = TypedRepository(store, RecordKind.MIGRATION_BATCH, MigrationBatchRecord)
        self.migration_quarantines = TypedRepository(store, RecordKind.MIGRATION_QUARANTINE, MigrationQuarantineRecord)
        self.migration_intentional_changes = TypedRepository(store, RecordKind.MIGRATION_INTENTIONAL_CHANGE, MigrationIntentionalChangeRecord)
        self.semantic_equivalence = TypedRepository(store, RecordKind.SEMANTIC_EQUIVALENCE, SemanticEquivalenceRecord)
        self.migration_rollbacks = TypedRepository(store, RecordKind.MIGRATION_ROLLBACK, MigrationRollbackRecord)
        self.evidence = TypedRepository(store, RecordKind.EVIDENCE, EvidenceRecord)
        self.default_rules = DefaultRuleRepository(store)
        self.language = LanguageRepository(store)
        self.materialized_views = MaterializedViewRepository(store)
        self.learning_packages = TypedRepository(store, RecordKind.LEARNING_PACKAGE, LearningPackageRecord)
        self.learning_frontiers = TypedRepository(store, RecordKind.LEARNING_FRONTIER, LearningFrontierRecord)
        self.learning_evidence_links = TypedRepository(store, RecordKind.LEARNING_EVIDENCE_LINK, LearningEvidenceLink)
        self.competence_results = TypedRepository(store, RecordKind.COMPETENCE_RESULT, CompetenceResultRecord)
        self.promotion_decisions = TypedRepository(store, RecordKind.PROMOTION_DECISION, PromotionDecisionRecord)
        self.learning_invalidations = TypedRepository(store, RecordKind.LEARNING_INVALIDATION, LearningInvalidationRecord)
        self.event_state = EventStateRepository(store)


def interval_contains(
    valid_from: str | None,
    valid_to: str | None,
    at_time: str | datetime | None,
) -> bool:
    if at_time is None:
        point = datetime.now(timezone.utc)
    elif isinstance(at_time, datetime):
        point = at_time if at_time.tzinfo is not None else at_time.replace(tzinfo=timezone.utc)
    else:
        point = _parse_time(at_time)
        if point is None:
            return True
    start = _parse_time(valid_from)
    end = _parse_time(valid_to)
    if start is not None and point < start:
        return False
    if end is not None and point >= end:
        return False
    return True


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
