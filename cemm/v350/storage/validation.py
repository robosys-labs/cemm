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
    CapabilityInstance,
    ClaimRecord,
    DefaultRuleRecord,
    KnowledgeRecord,
    PatchOperation,
    RecordDependency,
    RecordKind,
    ReferentTypeAssertion,
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

    def validate(self, operations: Iterable[tuple[PatchOperation, Any | None]]) -> tuple[ValidationError, ...]:
        errors: list[ValidationError] = []
        report = self._registry.validate()
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
        elif kind == RecordKind.DEFAULT_RULE:
            self._validate_default_rule(record)
        elif kind == RecordKind.REFERENT:
            self._validate_referent(record)
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
        occurrence = self._require_record(RecordKind.CLAIM_OCCURRENCE, claim.claim_occurrence_ref).payload
        if occurrence.proposition_ref != claim.proposition_ref:
            raise ValueError("claim record proposition differs from occurrence proposition")
        if occurrence.reported_context_ref != claim.reported_context_ref:
            raise ValueError("claim record reported context mismatch")

    def _validate_knowledge(self, knowledge: KnowledgeRecord) -> None:
        proposition = self._require_record(RecordKind.PROPOSITION, knowledge.proposition_ref).payload
        if proposition.context_ref != knowledge.context_ref:
            raise ValueError("knowledge and proposition contexts differ")
        for evidence_ref in knowledge.evidence_refs:
            self._require_record(RecordKind.EVIDENCE, evidence_ref)

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
        if not self._resolver.resolve_any(delta.dependency_ref):
            raise ValueError("capability delta dependency is unresolved")

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
