"""Commit-boundary validation for normalized v3.5 durable records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from ..schema.model import (
    ActionSchema,
    EventSchema,
    FacetEntitlement,
    FacetSchema,
    MeaningSchema,
    PortFillerClass,
    ReferentTypeSchema,
    SchemaLifecycleStatus,
    StateDimensionSchema,
    StateValueSchema,
)
from ..schema.registry import SchemaRegistry
from ..language.model import (
    ConstructionRecord, FormSenseLinkRecord, LanguageFormRecord,
    LanguagePackRecord, LexicalSenseRecord, SenseTargetKind,
)
from ..language.registry import LanguageRegistry, LanguageRegistryError
from ..transitions.admission import EventAdmissionGate
from ..transitions.compiler import TransitionContractCompiler, TransitionContractError
from ..transitions.state import require_concrete_timeline_timestamp
from ..transitions.model import (
    CapabilityDependencyRecord,
    ConditionOperator,
    TransitionContractRecord,
    TransitionProofRecord,
)
from ..uol.model import (
    CapabilityDelta,
    ClaimOccurrence,
    EventOccurrence,
    FillerRef,
    PropositionReferent,
    QuotedLiteral,
    Referent,
    SemanticApplication,
    StateDelta,
)
from .model import (
    AdmissionDecision,
    AdmissionLifecycleStatus,
    AssignmentStatus,
    CapabilityInstance,
    ClaimHistoryRecord,
    ClaimRecord,
    DefaultRuleRecord,
    EpistemicAdmissionRecord,
    KnowledgeRecord,
    KnowledgeStatus,
    PatchOperation,
    RecordDependency,
    RecordKind,
    ReferentTypeAssertion,
    SourceAssessmentRecord,
    StateAssignment,
    StoredRecord,
)


class RecordResolver(Protocol):
    def resolve(
        self, record_kind: RecordKind, record_ref: str, revision: int | None = None
    ) -> StoredRecord[Any] | None: ...

    def records(self, record_kind: RecordKind) -> tuple[StoredRecord[Any], ...]: ...

    def resolve_any(self, record_ref: str) -> tuple[StoredRecord[Any], ...]: ...


@dataclass(frozen=True, slots=True)
class ValidationError:
    code: str
    target_ref: str
    message: str


class CommitValidationError(ValueError):
    def __init__(self, errors: Iterable[ValidationError]):
        self.errors = tuple(errors)
        super().__init__("; ".join(f"{item.code}:{item.target_ref}:{item.message}" for item in self.errors))


class CommitValidator:
    def __init__(self, resolver: RecordResolver):
        self._resolver = resolver
        self._registry = self._schema_registry()
        self._language_registry = self._build_language_registry()

    def validate(self, operations: Iterable[tuple[PatchOperation, Any | None]]) -> tuple[ValidationError, ...]:
        errors: list[ValidationError] = []
        report = self._registry.validate()
        try:
            self._language_registry.snapshot()
        except LanguageRegistryError as exc:
            errors.append(ValidationError("language_registry", "language", str(exc)))
        errors.extend(
            ValidationError(item.code, item.target_ref, item.message)
            for item in report.errors
        )
        errors.extend(self._validate_default_rule_revisions())
        for operation, record in operations:
            if record is None:
                continue
            try:
                self._validate_record(operation.record_kind, record, operation.record_revision)
                self._validate_dependencies(operation.target_ref, operation.dependencies)
            except ValueError as exc:
                errors.append(ValidationError("record_contract", operation.target_ref, str(exc)))
        return tuple(errors)

    def require_valid(self, operations: Iterable[tuple[PatchOperation, Any | None]]) -> None:
        errors = self.validate(operations)
        if errors:
            raise CommitValidationError(errors)


    def _validate_default_rule_revisions(self) -> tuple[ValidationError, ...]:
        by_ref: dict[str, dict[int, DefaultRuleRecord]] = {}
        for stored in self._resolver.records(RecordKind.DEFAULT_RULE):
            item = stored.payload
            if isinstance(item, DefaultRuleRecord):
                by_ref.setdefault(item.rule_ref, {})[item.revision] = item
        errors: list[ValidationError] = []
        for rule_ref, revisions in sorted(by_ref.items()):
            for item in revisions.values():
                if item.supersedes_revision is not None and item.supersedes_revision not in revisions:
                    errors.append(ValidationError(
                        "missing_superseded_default_rule_revision", rule_ref,
                        f"revision {item.revision} supersedes missing revision {item.supersedes_revision}",
                    ))
            superseded = {
                item.supersedes_revision for item in revisions.values()
                if item.supersedes_revision is not None
                and item.lifecycle_status not in {
                    SchemaLifecycleStatus.CANDIDATE, SchemaLifecycleStatus.REJECTED,
                }
            }
            active = [
                item for item in revisions.values()
                if item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
                and item.revision not in superseded
            ]
            if len(active) > 1:
                errors.append(ValidationError(
                    "multiple_active_default_rule_revisions", rule_ref,
                    f"multiple active revisions: {sorted(item.revision for item in active)}",
                ))
        return tuple(errors)

    def _build_language_registry(self) -> LanguageRegistry:
        def records(kind: RecordKind, expected: type[Any]):
            return tuple(
                item.payload for item in self._resolver.records(kind)
                if isinstance(item.payload, expected)
            )
        return LanguageRegistry(
            records(RecordKind.LANGUAGE_PACK, LanguagePackRecord),
            records(RecordKind.LANGUAGE_FORM, LanguageFormRecord),
            records(RecordKind.LEXICAL_SENSE, LexicalSenseRecord),
            records(RecordKind.FORM_SENSE_LINK, FormSenseLinkRecord),
            records(RecordKind.CONSTRUCTION, ConstructionRecord),
        )

    def _schema_registry(self) -> SchemaRegistry:
        schemas = tuple(item.payload for item in self._resolver.records(RecordKind.SCHEMA))
        entitlements = tuple(item.payload for item in self._resolver.records(RecordKind.FACET_ENTITLEMENT))
        return SchemaRegistry(
            (item for item in schemas if isinstance(item, MeaningSchema)),
            (item for item in entitlements if isinstance(item, FacetEntitlement)),
        )

    def _validate_record(self, kind: RecordKind, record: Any, revision: int) -> None:
        if kind == RecordKind.TYPE_ASSERTION:
            self._validate_type_assertion(record)
        elif kind == RecordKind.SEMANTIC_APPLICATION:
            self._validate_application(record)
        elif kind == RecordKind.PROPOSITION:
            self._validate_proposition(record)
        elif kind == RecordKind.CLAIM_OCCURRENCE:
            self._validate_claim(record)
        elif kind == RecordKind.CLAIM_RECORD:
            self._validate_claim_record(record)
        elif kind == RecordKind.CLAIM_HISTORY:
            self._validate_claim_history(record)
        elif kind == RecordKind.SOURCE_ASSESSMENT:
            self._validate_source_assessment(record)
        elif kind == RecordKind.EPISTEMIC_ADMISSION:
            self._validate_epistemic_admission(record)
        elif kind == RecordKind.KNOWLEDGE:
            self._validate_knowledge(record)
        elif kind == RecordKind.EVENT_OCCURRENCE:
            self._validate_event(record)
        elif kind == RecordKind.STATE_ASSIGNMENT:
            self._validate_state_assignment(record)
        elif kind == RecordKind.STATE_DELTA:
            self._validate_state_delta(record)
        elif kind == RecordKind.CAPABILITY_INSTANCE:
            self._validate_capability(record)
        elif kind == RecordKind.CAPABILITY_DELTA:
            self._validate_capability_delta(record)
        elif kind == RecordKind.TRANSITION_CONTRACT:
            self._validate_transition_contract(record)
        elif kind == RecordKind.CAPABILITY_DEPENDENCY:
            self._validate_capability_dependency(record)
        elif kind == RecordKind.TRANSITION_PROOF:
            self._validate_transition_proof(record)
        elif kind == RecordKind.DEFAULT_RULE:
            self._validate_default_rule(record)
        elif kind == RecordKind.REFERENT:
            self._validate_referent(record)
        elif kind == RecordKind.LEXICAL_SENSE:
            self._validate_lexical_sense(record)
        elif kind == RecordKind.CONSTRUCTION:
            self._validate_construction(record)
        del revision

    def _validate_referent(self, referent: Referent) -> None:
        for type_ref in referent.type_refs:
            schema = self._registry.maybe_authoritative_schema(type_ref)
            if schema is None:
                raise ValueError(f"referent type is unresolved: {type_ref}")
            if not isinstance(schema, ReferentTypeSchema):
                raise ValueError(f"referent type is not a ReferentTypeSchema: {type_ref}")
            if referent.storage_kind not in schema.storage_kinds:
                raise ValueError(
                    f"storage kind {referent.storage_kind.value} is not licensed by {type_ref}"
                )

    def _validate_type_assertion(self, assertion: ReferentTypeAssertion) -> None:
        self._require_record(RecordKind.REFERENT, assertion.referent_ref)
        schema = self._require_schema(assertion.type_schema_ref, assertion.type_revision)
        if not isinstance(schema, ReferentTypeSchema):
            raise ValueError("type assertion must pin a ReferentTypeSchema")

    def _validate_application(self, application: SemanticApplication) -> None:
        schema = self._require_schema(application.schema_ref, application.schema_revision)
        if not schema.use_profile.permits(application.use_operation, provisional=True):
            raise ValueError(
                f"schema {schema.schema_ref}@{schema.revision} does not authorize "
                f"{application.use_operation.value}"
            )
        bindings = {item.port_ref: item for item in application.bindings}
        known_ports = {item.port_ref for item in schema.local_ports}
        unknown = sorted(set(bindings).difference(known_ports))
        if unknown:
            raise ValueError(f"application has unknown local ports: {unknown}")
        for port in schema.local_ports:
            binding = bindings.get(port.port_ref)
            count = 0 if binding is None else len(binding.fillers)
            if not port.cardinality.accepts(count):
                raise ValueError(
                    f"port {port.port_ref} cardinality rejects {count}; expected "
                    f"{port.cardinality.minimum}..{port.cardinality.maximum}"
                )
            if binding is None:
                continue
            if binding.ordered != port.ordered_fillers and len(binding.fillers) > 1:
                raise ValueError(f"port {port.port_ref} ordering does not match its schema")
            if binding.open_binding_purpose is not None and binding.open_binding_purpose not in port.open_binding_purposes:
                raise ValueError(
                    f"port {port.port_ref} does not authorize open purpose "
                    f"{binding.open_binding_purpose.value}"
                )
            for filler in binding.fillers:
                filler_class = (
                    PortFillerClass.QUOTED_LITERAL
                    if isinstance(filler, QuotedLiteral)
                    else filler.filler_class
                )
                if filler_class not in port.filler_classes:
                    raise ValueError(
                        f"port {port.port_ref} rejects filler class {filler_class.value}"
                    )
                if isinstance(filler, FillerRef):
                    self._validate_filler(port, filler)

    def _validate_filler(self, port, filler: FillerRef) -> None:
        kind_map = {
            PortFillerClass.REFERENT: RecordKind.REFERENT,
            PortFillerClass.SEMANTIC_APPLICATION: RecordKind.SEMANTIC_APPLICATION,
        }
        record_kind = kind_map.get(filler.filler_class)
        if record_kind is None:
            return
        stored = self._require_record(record_kind, filler.ref)
        if filler.filler_class == PortFillerClass.REFERENT:
            referent = stored.payload
            if port.accepted_storage_kinds and referent.storage_kind not in port.accepted_storage_kinds:
                raise ValueError(
                    f"port {port.port_ref} rejects storage kind {referent.storage_kind.value}"
                )
            if port.accepted_type_refs:
                closure = self._referent_type_closure(referent.referent_ref, referent)
                if not closure.intersection(port.accepted_type_refs):
                    raise ValueError(
                        f"port {port.port_ref} requires one of {sorted(port.accepted_type_refs)}"
                    )
        elif filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION and port.accepted_schema_classes:
            application = stored.payload
            schema = self._require_schema(application.schema_ref, application.schema_revision)
            if schema.schema_class not in port.accepted_schema_classes:
                raise ValueError(
                    f"port {port.port_ref} rejects schema class {schema.schema_class.value}"
                )

    def _validate_proposition(self, proposition: PropositionReferent) -> None:
        self._require_record(RecordKind.REFERENT, proposition.proposition_ref)
        for content in proposition.content_refs:
            kind = (
                RecordKind.SEMANTIC_APPLICATION
                if content.filler_class == PortFillerClass.SEMANTIC_APPLICATION
                else None
            )
            if kind is not None:
                application = self._require_record(kind, content.ref).payload
                if application.context_ref != proposition.context_ref:
                    raise ValueError("proposition content context differs from proposition context")

    def _validate_claim(self, claim: ClaimOccurrence) -> None:
        self._require_record(RecordKind.REFERENT, claim.claim_ref)
        proposition = self._require_record(RecordKind.PROPOSITION, claim.proposition_ref).payload
        if proposition.context_ref != claim.reported_context_ref:
            raise ValueError("claim reported context must match proposition context")
        self._require_record(RecordKind.REFERENT, claim.claimant_ref)

    def _validate_claim_record(self, claim: ClaimRecord) -> None:
        if claim.superseded_by is not None:
            raise ValueError("claim supersession/correction authority belongs to append-only ClaimHistoryRecord, not ClaimRecord.superseded_by")
        occurrence = self._require_record(RecordKind.CLAIM_OCCURRENCE, claim.claim_occurrence_ref).payload
        if occurrence.proposition_ref != claim.proposition_ref:
            raise ValueError("claim record proposition differs from occurrence proposition")
        if occurrence.reported_context_ref != claim.reported_context_ref:
            raise ValueError("claim record reported context mismatch")

    def _validate_claim_history(self, history: ClaimHistoryRecord) -> None:
        claim = self._require_record(RecordKind.CLAIM_RECORD, history.claim_record_ref).payload
        if claim.source_ref != history.source_ref:
            raise ValueError("claim history source must match the claim source")
        if history.target_claim_record_ref is not None:
            target = self._require_record(RecordKind.CLAIM_RECORD, history.target_claim_record_ref).payload
            if target.source_ref != history.source_ref:
                raise ValueError("claim correction/retraction may not rewrite another source's history")
        if history.supersedes_revision is not None:
            stored_prior = self._resolver.resolve(
                RecordKind.CLAIM_HISTORY, history.history_ref, history.supersedes_revision
            )
            if stored_prior is None:
                raise ValueError("claim history supersedes a missing exact revision")
            prior = stored_prior.payload
            stable = (
                prior.claim_record_ref, prior.action, prior.source_ref, prior.context_ref,
                prior.target_claim_record_ref,
            )
            current = (
                history.claim_record_ref, history.action, history.source_ref, history.context_ref,
                history.target_claim_record_ref,
            )
            if current != stable:
                raise ValueError("claim history revision may not rewrite event identity or source lineage")
        for evidence_ref in history.evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)


    def _validate_source_assessment(self, assessment: SourceAssessmentRecord) -> None:
        if not self._resolver.resolve_any(assessment.source_ref):
            raise ValueError(f"source assessment source is unresolved: {assessment.source_ref}")
        for evidence_ref in assessment.evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)
        if assessment.supersedes_revision is not None:
            stored_prior = self._resolver.resolve(
                RecordKind.SOURCE_ASSESSMENT, assessment.assessment_ref, assessment.supersedes_revision
            )
            if stored_prior is None:
                raise ValueError("source assessment supersedes a missing exact revision")
            prior = stored_prior.payload
            if (prior.source_ref, prior.context_ref) != (assessment.source_ref, assessment.context_ref):
                raise ValueError("source assessment revision may not rewrite source identity or context")

    def _validate_epistemic_admission(self, admission: EpistemicAdmissionRecord) -> None:
        self._require_record(RecordKind.PROPOSITION, admission.proposition_ref)
        for evidence_ref in admission.evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)
        for source_ref in admission.source_refs:
            if not self._resolver.resolve_any(source_ref):
                raise ValueError(f"epistemic admission source is unresolved: {source_ref}")
        assessments = []
        for assessment_ref, assessment_revision in admission.source_assessment_pins:
            stored_assessment = self._resolver.resolve(
                RecordKind.SOURCE_ASSESSMENT, assessment_ref, assessment_revision
            )
            if stored_assessment is None:
                raise ValueError(
                    f"epistemic admission source assessment pin is unresolved: "
                    f"{assessment_ref}@{assessment_revision}"
                )
            assessments.append(stored_assessment.payload)
        if admission.decision in {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION}:
            if len(assessments) != len(admission.source_refs):
                raise ValueError("direct admission requires exactly one durable source assessment per source")
            if {item.source_ref for item in assessments} != set(admission.source_refs):
                raise ValueError("admission source assessments must cover exactly the admitted sources")
            if any(item.context_ref != admission.source_context_ref for item in assessments):
                raise ValueError("admission source assessments must be pinned to the source context")
        if admission.supersedes_revision is not None:
            stored_prior = self._resolver.resolve(
                RecordKind.EPISTEMIC_ADMISSION, admission.admission_ref, admission.supersedes_revision
            )
            if stored_prior is None:
                raise ValueError("epistemic admission supersedes a missing exact revision")
            prior = stored_prior.payload
            stable = (
                prior.proposition_ref, prior.source_context_ref, prior.target_context_ref,
                prior.decision, prior.source_refs, prior.policy_ref, prior.retracts_admission_ref,
            )
            current = (
                admission.proposition_ref, admission.source_context_ref, admission.target_context_ref,
                admission.decision, admission.source_refs, admission.policy_ref, admission.retracts_admission_ref,
            )
            if current != stable:
                raise ValueError("epistemic admission revision may not rewrite proposition, context, decision, or source lineage")
        if admission.retracts_admission_ref is not None:
            target = self._require_record(RecordKind.EPISTEMIC_ADMISSION, admission.retracts_admission_ref).payload
            if target.proposition_ref != admission.proposition_ref or target.target_context_ref != admission.target_context_ref:
                raise ValueError("admission retraction must target the same proposition and context")
            if not set(admission.source_refs).intersection(target.source_refs):
                raise ValueError("admission retraction must preserve source lineage")

    def _validate_knowledge(self, knowledge: KnowledgeRecord) -> None:
        proposition = self._require_record(RecordKind.PROPOSITION, knowledge.proposition_ref).payload
        for evidence_ref in knowledge.evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)

        admissions: list[EpistemicAdmissionRecord] = []
        non_admission_lineage: list[str] = []
        for lineage_ref in knowledge.support_lineage_refs:
            stored = self._resolver.resolve(RecordKind.EPISTEMIC_ADMISSION, lineage_ref)
            if stored is None or not isinstance(stored.payload, EpistemicAdmissionRecord):
                non_admission_lineage.append(lineage_ref)
            else:
                admissions.append(stored.payload)

        if proposition.context_ref != knowledge.context_ref and not admissions:
            raise ValueError("knowledge and proposition contexts differ without explicit epistemic admission")
        if admissions:
            if non_admission_lineage:
                raise ValueError("epistemic knowledge support lineage must contain only explicit admission records")
            if not knowledge.support_lineage_refs:
                raise ValueError("derived epistemic knowledge requires admission lineage")
            for admission in admissions:
                if admission.proposition_ref != knowledge.proposition_ref:
                    raise ValueError("knowledge admission lineage targets a different proposition")
                if admission.source_context_ref != proposition.context_ref:
                    raise ValueError("knowledge admission lineage starts from a different proposition context")
                if admission.target_context_ref != knowledge.context_ref:
                    raise ValueError("knowledge admission lineage targets a different context")
                if admission.lifecycle_status != AdmissionLifecycleStatus.ACTIVE:
                    raise ValueError("knowledge cannot derive from an inactive epistemic admission")
                if self._admission_effectively_retracted(admission):
                    raise ValueError("knowledge cannot derive from an effectively retracted epistemic admission")
                if admission.decision not in {
                    AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION,
                }:
                    raise ValueError("knowledge can derive only from explicit support/opposition admissions")
            has_support = any(item.truth_status == KnowledgeStatus.SUPPORTED for item in admissions)
            has_opposition = any(item.truth_status == KnowledgeStatus.OPPOSED for item in admissions)
            derived_status = (
                KnowledgeStatus.BOTH if has_support and has_opposition
                else KnowledgeStatus.SUPPORTED if has_support
                else KnowledgeStatus.OPPOSED if has_opposition
                else KnowledgeStatus.UNDETERMINED
            )
            if knowledge.truth_status != derived_status:
                raise ValueError("knowledge truth status disagrees with admission lineage")
            source_refs = {ref for item in admissions for ref in item.source_refs}
            evidence_refs = {ref for item in admissions for ref in item.evidence_refs}
            if set(knowledge.source_refs) != source_refs:
                raise ValueError("knowledge sources must equal active admission source lineage")
            if set(knowledge.evidence_refs) != evidence_refs:
                raise ValueError("knowledge evidence must equal active admission evidence lineage")
        elif proposition.context_ref != knowledge.context_ref:
            raise ValueError("knowledge and proposition contexts differ without explicit epistemic admission")

    def _admission_effectively_retracted(self, admission: EpistemicAdmissionRecord) -> bool:
        latest: dict[str, EpistemicAdmissionRecord] = {}
        for stored in self._resolver.records(RecordKind.EPISTEMIC_ADMISSION):
            item = stored.payload
            if not isinstance(item, EpistemicAdmissionRecord):
                continue
            prior = latest.get(item.admission_ref)
            if prior is None or item.revision > prior.revision:
                latest[item.admission_ref] = item
        for item in latest.values():
            if (
                item.decision == AdmissionDecision.RETRACT
                and item.lifecycle_status == AdmissionLifecycleStatus.ACTIVE
                and item.retracts_admission_ref == admission.admission_ref
                and item.proposition_ref == admission.proposition_ref
                and item.target_context_ref == admission.target_context_ref
                and set(item.source_refs).intersection(admission.source_refs)
            ):
                return True
        return False

    def _validate_event(self, event: EventOccurrence) -> None:
        self._require_record(RecordKind.REFERENT, event.event_ref)
        schema = self._require_schema(event.event_schema_ref, event.event_schema_revision)
        if not isinstance(schema, EventSchema):
            raise ValueError("event occurrence must pin an EventSchema")
        application = self._require_record(
            RecordKind.SEMANTIC_APPLICATION, event.participant_application_ref
        ).payload
        if application.schema_ref != event.event_schema_ref or application.schema_revision != event.event_schema_revision:
            raise ValueError("event participant application must pin the same event schema revision")
        if application.context_ref != event.context_ref:
            raise ValueError("event participant application context mismatch")
        for admission_ref in event.admission_refs:
            if not self._resolver.resolve_any(admission_ref):
                raise ValueError(f"event admission reference is unresolved: {admission_ref}")

    def _validate_state_assignment(self, assignment: StateAssignment) -> None:
        self._require_record(RecordKind.REFERENT, assignment.holder_ref)
        dimension = self._require_schema(assignment.dimension_ref, assignment.dimension_revision)
        value = self._require_schema(assignment.value_ref, assignment.value_revision)
        if not isinstance(dimension, StateDimensionSchema) or not isinstance(value, StateValueSchema):
            raise ValueError("state assignment must pin a state dimension and state value")
        if value.dimension_ref != dimension.schema_ref:
            raise ValueError("state value does not belong to the pinned dimension")
        self._require_holder_type(assignment.holder_ref, dimension.holder_type_refs)

    def _validate_state_delta(self, delta: StateDelta) -> None:
        self._require_record(RecordKind.REFERENT, delta.holder_ref)
        dimension = self._require_schema(delta.dimension_ref, delta.dimension_revision)
        if not isinstance(dimension, StateDimensionSchema):
            raise ValueError("state delta must pin a StateDimensionSchema")
        self._require_holder_type(delta.holder_ref, dimension.holder_type_refs)
        for value_ref, value_revision in (
            (delta.from_value_ref, delta.from_value_revision),
            (delta.to_value_ref, delta.to_value_revision),
        ):
            if value_ref is None:
                continue
            value = self._require_schema(value_ref, value_revision or 0)
            if not isinstance(value, StateValueSchema) or value.dimension_ref != dimension.schema_ref:
                raise ValueError("state delta value does not belong to the pinned dimension")
        if not self._resolver.resolve_any(delta.trigger_ref):
            raise ValueError("state delta trigger is unresolved")
        trigger_event = self._resolver.resolve(RecordKind.EVENT_OCCURRENCE, delta.trigger_ref)
        if trigger_event is not None:
            proofs = [
                self._resolver.resolve(RecordKind.TRANSITION_PROOF, proof_ref)
                for proof_ref in delta.proof_refs
            ]
            if not any(item is not None for item in proofs):
                raise ValueError("event-triggered state delta requires durable transition proof lineage")

    def _validate_capability(self, capability: CapabilityInstance) -> None:
        self._require_record(RecordKind.REFERENT, capability.holder_ref)
        action = self._require_schema(
            capability.action_schema_ref, capability.action_schema_revision
        )
        if not isinstance(action, ActionSchema):
            raise ValueError("capability must pin an ActionSchema")

    def _validate_capability_delta(self, delta: CapabilityDelta) -> None:
        self._require_record(RecordKind.REFERENT, delta.holder_ref)
        action = self._require_schema(delta.action_schema_ref, delta.action_schema_revision)
        if not isinstance(action, ActionSchema):
            raise ValueError("capability delta must pin an ActionSchema")
        if not self._resolver.resolve_any(delta.trigger_ref):
            raise ValueError("capability delta trigger is unresolved")
        dependency = self._resolver.resolve(RecordKind.CAPABILITY_DEPENDENCY, delta.dependency_ref)
        if dependency is None or not isinstance(dependency.payload, CapabilityDependencyRecord):
            raise ValueError("capability delta dependency must resolve to a capability dependency record")
        if dependency.payload.action_schema_ref != delta.action_schema_ref:
            raise ValueError("capability delta dependency targets a different action schema")
        if not any(
            self._resolver.resolve(RecordKind.TRANSITION_PROOF, proof_ref) is not None
            for proof_ref in delta.proof_refs
        ):
            raise ValueError("Phase-11 capability delta requires durable transition proof lineage")

    def _validate_transition_contract(self, contract: TransitionContractRecord) -> None:
        try:
            TransitionContractCompiler(self._registry).compile(contract)
        except TransitionContractError as exc:
            raise ValueError(str(exc)) from exc
        for evidence_ref in contract.evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)
        if contract.supersedes_revision is not None:
            prior = self._resolver.resolve(RecordKind.TRANSITION_CONTRACT, contract.contract_ref, contract.supersedes_revision)
            if prior is None or not isinstance(prior.payload, TransitionContractRecord):
                raise ValueError("transition contract supersedes a missing exact revision")
            if (prior.payload.trigger_schema_ref, prior.payload.trigger_schema_revision) != (
                contract.trigger_schema_ref, contract.trigger_schema_revision
            ):
                raise ValueError("transition contract revision may not retarget its trigger schema")

    def _validate_capability_dependency(self, dependency: CapabilityDependencyRecord) -> None:
        try:
            TransitionContractCompiler(self._registry).validate_capability_dependency(dependency)
        except TransitionContractError as exc:
            raise ValueError(str(exc)) from exc
        for evidence_ref in dependency.evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)
        if dependency.supersedes_revision is not None:
            prior = self._resolver.resolve(RecordKind.CAPABILITY_DEPENDENCY, dependency.dependency_ref, dependency.supersedes_revision)
            if prior is None or not isinstance(prior.payload, CapabilityDependencyRecord):
                raise ValueError("capability dependency supersedes a missing exact revision")
            if prior.payload.action_schema_ref != dependency.action_schema_ref:
                raise ValueError("capability dependency revision may not retarget its action schema")

    def _validate_transition_proof(self, proof: TransitionProofRecord) -> None:
        event = self._require_record(RecordKind.EVENT_OCCURRENCE, proof.event_ref).payload
        if event.context_ref != proof.context_ref:
            raise ValueError("transition proof context differs from event context")
        require_concrete_timeline_timestamp(proof.effective_time_ref)
        contract_stored = self._resolver.resolve(
            RecordKind.TRANSITION_CONTRACT, proof.transition_contract_ref, proof.transition_contract_revision
        )
        if contract_stored is None or not isinstance(contract_stored.payload, TransitionContractRecord):
            raise ValueError("transition proof contract revision is unresolved")
        contract = contract_stored.payload
        if (contract.trigger_schema_ref, contract.trigger_schema_revision) != (
            event.event_schema_ref, event.event_schema_revision
        ):
            raise ValueError("transition proof contract does not match event schema revision")
        try:
            TransitionContractCompiler(self._registry).compile(contract)
        except TransitionContractError as exc:
            raise ValueError(f"transition proof contract is not executable: {exc}") from exc

        admission_assessment = EventAdmissionGate(self._resolver).assess(event)
        if not admission_assessment.admitted:
            raise ValueError("transition proof event is not independently admitted")
        if tuple(sorted(proof.admission_pins)) != tuple(sorted(admission_assessment.admission_pins)):
            raise ValueError("transition proof admission pins differ from the event's active admission lineage")

        for admission_ref, admission_revision in proof.admission_pins:
            stored = self._resolver.resolve(RecordKind.EPISTEMIC_ADMISSION, admission_ref, admission_revision)
            if stored is None:
                raise ValueError("transition proof admission pin is unresolved")
            admission = stored.payload
            if (
                admission.lifecycle_status != AdmissionLifecycleStatus.ACTIVE
                or admission.decision != AdmissionDecision.ADMIT_SUPPORT
                or admission.target_context_ref != proof.context_ref
                or self._admission_effectively_retracted(admission)
            ):
                raise ValueError("transition proof admission lineage is not active admitted support")
        for evidence_ref in proof.evidence_refs + proof.condition_evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)

        application = self._require_record(
            RecordKind.SEMANTIC_APPLICATION, event.participant_application_ref
        ).payload
        binding_map = {item.port_ref: item for item in application.bindings}
        expected_assignment_pins: set[tuple[str, int]] = set()
        expected_condition_evidence: set[str] = set()
        for condition in contract.state_conditions:
            binding = binding_map.get(condition.holder_port_ref)
            if binding is None or len(binding.fillers) != 1 or not isinstance(binding.fillers[0], FillerRef):
                raise ValueError("transition proof condition holder binding is unresolved")
            holder_ref = binding.fillers[0].ref
            active = self._pre_transition_active_assignments(
                proof, holder_ref, condition.dimension_ref, proof.context_ref
            )
            expected_assignment_pins.update((item.record_ref, item.revision) for item in active)
            expected_condition_evidence.update(
                ref for item in active for ref in item.payload.evidence_refs
            )
            values = {item.payload.value_ref for item in active}
            if condition.operator == ConditionOperator.KNOWN:
                satisfied = bool(values)
            elif condition.operator == ConditionOperator.UNKNOWN:
                satisfied = not values
            elif condition.operator == ConditionOperator.EQUALS:
                satisfied = bool(values) and condition.value_ref in values
            elif condition.operator == ConditionOperator.NOT_EQUALS:
                satisfied = bool(values) and condition.value_ref not in values
            else:  # pragma: no cover - enum exhaustiveness
                satisfied = False
            if not satisfied:
                raise ValueError(f"transition proof condition is not satisfied: {condition.condition_ref}")

        if tuple(sorted(proof.input_assignment_pins)) != tuple(sorted(expected_assignment_pins)):
            raise ValueError("transition proof input assignment pins do not match the pre-transition condition state")
        if tuple(sorted(proof.condition_evidence_refs)) != tuple(sorted(expected_condition_evidence)):
            raise ValueError("transition proof condition evidence does not match pinned pre-transition state")

        for assignment_ref, assignment_revision in proof.input_assignment_pins:
            if self._resolver.resolve(RecordKind.STATE_ASSIGNMENT, assignment_ref, assignment_revision) is None:
                raise ValueError("transition proof input assignment pin is unresolved")

        deltas = []
        for delta_ref in proof.derived_state_delta_refs:
            stored = self._require_record(RecordKind.STATE_DELTA, delta_ref)
            delta = stored.payload
            if delta.trigger_ref != proof.event_ref or proof.proof_ref not in delta.proof_refs:
                raise ValueError("transition proof delta lineage is inconsistent")
            deltas.append(delta)
        if len(deltas) != len(contract.state_effects):
            raise ValueError("transition proof delta count differs from reviewed transition contract")
        unmatched = list(deltas)
        for effect in contract.state_effects:
            binding = binding_map.get(effect.holder_port_ref)
            if binding is None or len(binding.fillers) != 1 or not isinstance(binding.fillers[0], FillerRef):
                raise ValueError("transition proof effect holder binding is unresolved")
            holder_ref = binding.fillers[0].ref
            magnitude_ref = None
            if effect.magnitude_port_ref is not None:
                magnitude_binding = binding_map.get(effect.magnitude_port_ref)
                if magnitude_binding is None or len(magnitude_binding.fillers) != 1 or not isinstance(magnitude_binding.fillers[0], FillerRef):
                    raise ValueError("transition proof magnitude binding is unresolved")
                magnitude_ref = magnitude_binding.fillers[0].ref
            match = next((delta for delta in unmatched if (
                delta.holder_ref == holder_ref
                and delta.dimension_ref == effect.dimension_ref
                and delta.dimension_revision == effect.dimension_revision
                and delta.operation == effect.operation
                and delta.from_value_ref == effect.from_value_ref
                and delta.from_value_revision == effect.from_value_revision
                and delta.to_value_ref == effect.to_value_ref
                and delta.to_value_revision == effect.to_value_revision
                and delta.magnitude_ref == magnitude_ref
                and delta.context_ref == proof.context_ref
                and delta.effective_time_ref == proof.effective_time_ref
            )), None)
            if match is None:
                raise ValueError(f"transition proof delta does not match reviewed effect: {effect.effect_ref}")
            unmatched.remove(match)
        if unmatched:
            raise ValueError("transition proof contains unreviewed extra state effects")

    def _pre_transition_active_assignments(
        self, proof: TransitionProofRecord, holder_ref: str, dimension_ref: str, context_ref: str
    ) -> tuple[StoredRecord[Any], ...]:
        by_ref: dict[str, list[StoredRecord[Any]]] = {}
        for stored in self._resolver.records(RecordKind.STATE_ASSIGNMENT):
            item = stored.payload
            if not isinstance(item, StateAssignment):
                continue
            if item.holder_ref != holder_ref or item.dimension_ref != dimension_ref:
                continue
            if item.context_ref not in {"global", context_ref}:
                continue
            # A staged assignment revision carrying this proof is the proposed post-state,
            # not evidence for the condition that authorized the same proof.
            if stored.layer == "staged" and proof.proof_ref in item.proof_refs:
                continue
            by_ref.setdefault(item.assignment_ref, []).append(stored)
        active: list[StoredRecord[Any]] = []
        for revisions in by_ref.values():
            latest = max(revisions, key=lambda item: item.revision)
            if latest.payload.status == AssignmentStatus.ACTIVE and latest.payload.valid_to is None:
                active.append(latest)
        return tuple(sorted(active, key=lambda item: (item.record_ref, item.revision)))

    def _validate_default_rule(self, rule: DefaultRuleRecord) -> None:
        facet = self._registry.maybe_authoritative_schema(rule.target_facet_ref)
        if facet is None or not isinstance(facet, FacetSchema):
            raise ValueError("default rule target must be an active facet schema")
        for type_ref in rule.holder_type_refs:
            schema = self._registry.maybe_authoritative_schema(type_ref)
            if schema is None or not isinstance(schema, ReferentTypeSchema):
                raise ValueError(f"default rule holder type is unresolved: {type_ref}")
        if rule.expected_dimension_ref is not None:
            dimension = self._require_schema(
                rule.expected_dimension_ref, rule.expected_dimension_revision or 0
            )
            if not isinstance(dimension, StateDimensionSchema):
                raise ValueError("default rule expected dimension is not a state dimension")
            if rule.expected_value_ref is not None:
                value = self._require_schema(
                    rule.expected_value_ref, rule.expected_value_revision or 0
                )
                if not isinstance(value, StateValueSchema) or value.dimension_ref != dimension.schema_ref:
                    raise ValueError("default rule value does not belong to its dimension")

    def _validate_lexical_sense(self, sense: LexicalSenseRecord) -> None:
        if sense.target_kind in {
            SenseTargetKind.SCHEMA, SenseTargetKind.REFERENT_TYPE,
            SenseTargetKind.OPERATOR, SenseTargetKind.DISCOURSE,
        }:
            schema = self._require_schema(sense.target_ref, sense.target_revision or 0)
            if sense.target_schema_class is not None and schema.schema_class != sense.target_schema_class:
                raise ValueError(
                    f"lexical sense target class mismatch: {sense.sense_ref} expects "
                    f"{sense.target_schema_class.value}, got {schema.schema_class.value}"
                )
            if not schema.use_profile.permits(sense.use_operation, provisional=True):
                raise ValueError(
                    f"lexical sense target does not authorize {sense.use_operation.value}: "
                    f"{sense.target_ref}@{sense.target_revision}"
                )
            if sense.target_kind == SenseTargetKind.REFERENT_TYPE and not isinstance(schema, ReferentTypeSchema):
                raise ValueError("referent-type lexical sense must target ReferentTypeSchema")
        for type_ref in sense.expected_type_refs:
            schema = self._registry.maybe_authoritative_schema(type_ref)
            if schema is None or not isinstance(schema, ReferentTypeSchema):
                raise ValueError(f"lexical sense expected type is unresolved: {type_ref}")

    def _validate_construction(self, construction: ConstructionRecord) -> None:
        if construction.output_schema_ref is None:
            return
        schema = self._require_schema(
            construction.output_schema_ref, construction.output_schema_revision or 0
        )
        if construction.output_schema_class is not None and schema.schema_class != construction.output_schema_class:
            raise ValueError(
                f"construction output class mismatch: {construction.construction_ref}"
            )
        if not schema.use_profile.permits("compose", provisional=True):
            raise ValueError(
                f"construction output schema does not authorize composition: {schema.schema_ref}"
            )
        schema_ports = {item.port_ref for item in schema.local_ports}
        for slot in construction.slots:
            if slot.semantic_port_ref and slot.semantic_port_ref not in schema_ports:
                raise ValueError(
                    f"construction slot maps to unknown semantic port {slot.semantic_port_ref}: "
                    f"{construction.construction_ref}"
                )

    def _validate_dependencies(self, target_ref: str, dependencies: Iterable[RecordDependency]) -> None:
        for dependency in dependencies:
            candidates = (
                self._resolver.resolve_any(dependency.record_ref)
                if dependency.record_kind is None
                else tuple(filter(None, (self._resolver.resolve(
                    dependency.record_kind, dependency.record_ref, dependency.revision
                ),)))
            )
            if not candidates:
                raise ValueError(
                    f"dependency of {target_ref} is unresolved: {dependency.record_ref}"
                )
            if dependency.fingerprint is not None and not any(
                item.record_fingerprint == dependency.fingerprint
                or item.content_fingerprint == dependency.fingerprint
                for item in candidates
            ):
                raise ValueError(
                    f"dependency fingerprint is stale: {dependency.record_ref}"
                )

    def _require_schema(self, schema_ref: str, revision: int) -> MeaningSchema:
        stored = self._resolver.resolve(RecordKind.SCHEMA, schema_ref, revision)
        if stored is None or not isinstance(stored.payload, MeaningSchema):
            raise ValueError(f"schema revision is unresolved: {schema_ref}@{revision}")
        schema = stored.payload
        if schema.lifecycle_status in {
            SchemaLifecycleStatus.REJECTED,
            SchemaLifecycleStatus.SUPERSEDED,
        }:
            raise ValueError(f"schema revision is not usable: {schema_ref}@{revision}")
        return schema

    def _require_record(self, kind: RecordKind, record_ref: str) -> StoredRecord[Any]:
        stored = self._resolver.resolve(kind, record_ref)
        if stored is None:
            raise ValueError(f"{kind.value} is unresolved: {record_ref}")
        return stored

    def _referent_type_closure(self, referent_ref: str, referent: Referent | None = None) -> frozenset[str]:
        direct = set(referent.type_refs if referent is not None else ())
        for stored in self._resolver.records(RecordKind.TYPE_ASSERTION):
            assertion = stored.payload
            if (
                assertion.referent_ref == referent_ref
                and assertion.status.value == "supported"
            ):
                direct.add(assertion.type_schema_ref)
        closure: set[str] = set()
        for type_ref in sorted(direct):
            schema = self._registry.maybe_authoritative_schema(type_ref)
            if isinstance(schema, ReferentTypeSchema):
                closure.update(self._registry.type_closure(schema.schema_ref, schema.revision))
        return frozenset(closure)

    def _require_holder_type(self, holder_ref: str, accepted_type_refs: Iterable[str]) -> None:
        accepted = frozenset(accepted_type_refs)
        if not accepted:
            return
        referent = self._require_record(RecordKind.REFERENT, holder_ref).payload
        closure = self._referent_type_closure(holder_ref, referent)
        if not closure.intersection(accepted):
            raise ValueError(
                f"holder {holder_ref} does not satisfy type constraints {sorted(accepted)}"
            )
