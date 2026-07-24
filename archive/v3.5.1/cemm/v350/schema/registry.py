"""Revisioned in-memory Phase-2 schema authority and structural validator.

Phase 4 will provide normalized SQLite repositories. This registry defines the
selection and validation semantics those repositories must preserve.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from .model import (
    ActionSchema,
    DiscourseActSchema,
    DiscourseRelationSchema,
    EntitlementApplicability,
    EventSchema,
    FacetEntitlement,
    FacetSchema,
    FunctionSchema,
    MeaningSchema,
    MeasureDimensionSchema,
    OperatorSchema,
    ParentRevisionPolicy,
    PropertySchema,
    ReferentTypeSchema,
    RelationSchema,
    ResponsePolicySchema,
    RoleSchema,
    SchemaClass,
    SchemaDependency,
    SchemaLifecycleStatus,
    SchemaParentLink,
    StateDimensionSchema,
    StateValueSchema,
    UnitSchema,
    UseDecision,
    UseOperation,
    ValidationSeverity,
    schema_authorizes_use,
    semantic_fingerprint,
)


class SchemaRegistryError(ValueError):
    pass


class DuplicateRevisionError(SchemaRegistryError):
    pass


class InheritanceCycleError(SchemaRegistryError):
    def __init__(self, cycle: tuple[str, ...]):
        self.cycle = cycle
        super().__init__(f"schema inheritance cycle: {' -> '.join(cycle)}")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: ValidationSeverity
    code: str
    target_ref: str
    message: str
    dependency_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity == ValidationSeverity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity == ValidationSeverity.WARNING)

    @property
    def unresolved(self) -> tuple[ValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity == ValidationSeverity.UNRESOLVED)

    @property
    def valid(self) -> bool:
        return not self.errors

    def require_valid(self) -> None:
        if self.errors:
            raise SchemaRegistryError("; ".join(f"{item.code}:{item.message}" for item in self.errors))


_LIFECYCLE_RANK = {
    SchemaLifecycleStatus.CANDIDATE: 0,
    SchemaLifecycleStatus.STRUCTURALLY_CLOSED: 1,
    SchemaLifecycleStatus.PROVISIONAL: 2,
    SchemaLifecycleStatus.COMPETENCE_VERIFIED: 3,
    SchemaLifecycleStatus.ACTIVE: 4,
}
_TERMINAL = {SchemaLifecycleStatus.SUPERSEDED, SchemaLifecycleStatus.REJECTED}
_AUTHORITY_LIFECYCLES = {SchemaLifecycleStatus.ACTIVE}
_SUPERSESSION_AUTHORITY = {SchemaLifecycleStatus.ACTIVE}
_CLOSED = {
    SchemaLifecycleStatus.STRUCTURALLY_CLOSED,
    SchemaLifecycleStatus.PROVISIONAL,
    SchemaLifecycleStatus.COMPETENCE_VERIFIED,
    SchemaLifecycleStatus.ACTIVE,
}

_ALLOWED_PARENT_CLASSES = {
    SchemaClass.MEANING: frozenset({SchemaClass.MEANING}),
    SchemaClass.REFERENT_TYPE: frozenset({SchemaClass.REFERENT_TYPE}),
    SchemaClass.FACET: frozenset({SchemaClass.FACET}),
    SchemaClass.PROPERTY: frozenset({SchemaClass.PROPERTY}),
    SchemaClass.STATE_DIMENSION: frozenset({SchemaClass.STATE_DIMENSION}),
    SchemaClass.STATE_VALUE: frozenset({SchemaClass.STATE_VALUE}),
    SchemaClass.RELATION: frozenset({SchemaClass.RELATION}),
    SchemaClass.ROLE: frozenset({SchemaClass.ROLE}),
    SchemaClass.FUNCTION: frozenset({SchemaClass.FUNCTION}),
    SchemaClass.ACTION: frozenset({SchemaClass.ACTION, SchemaClass.EVENT}),
    SchemaClass.EVENT: frozenset({SchemaClass.EVENT}),
    SchemaClass.UNIT: frozenset({SchemaClass.UNIT}),
    SchemaClass.MEASURE_DIMENSION: frozenset({SchemaClass.MEASURE_DIMENSION}),
    SchemaClass.OPERATOR: frozenset({SchemaClass.OPERATOR}),
    SchemaClass.DISCOURSE_ACT: frozenset({SchemaClass.DISCOURSE_ACT}),
    SchemaClass.DISCOURSE_RELATION: frozenset({SchemaClass.DISCOURSE_RELATION}),
    SchemaClass.RESPONSE_POLICY: frozenset({SchemaClass.RESPONSE_POLICY}),
}


class SchemaRegistry:
    def __init__(
        self,
        schemas: Iterable[MeaningSchema] = (),
        entitlements: Iterable[FacetEntitlement] = (),
    ) -> None:
        self._schemas: dict[str, dict[int, MeaningSchema]] = {}
        self._entitlements: dict[str, dict[int, FacetEntitlement]] = {}
        self._type_closure_cache: dict[tuple[str, int], frozenset[str]] = {}
        for schema in schemas:
            self.add_schema(schema)
        for entitlement in entitlements:
            self.add_entitlement(entitlement)

    def add_schema(self, schema: MeaningSchema, *, replace: bool = False) -> None:
        revisions = self._schemas.setdefault(schema.schema_ref, {})
        if schema.revision in revisions and not replace:
            raise DuplicateRevisionError(f"duplicate schema revision {schema.schema_ref}@{schema.revision}")
        revisions[schema.revision] = schema
        self._type_closure_cache.clear()

    def add_entitlement(self, entitlement: FacetEntitlement, *, replace: bool = False) -> None:
        revisions = self._entitlements.setdefault(entitlement.entitlement_ref, {})
        if entitlement.revision in revisions and not replace:
            raise DuplicateRevisionError(
                f"duplicate entitlement revision {entitlement.entitlement_ref}@{entitlement.revision}"
            )
        revisions[entitlement.revision] = entitlement

    def schema(self, schema_ref: str, revision: int | None = None) -> MeaningSchema:
        revisions = self._schemas.get(schema_ref)
        if not revisions:
            raise KeyError(schema_ref)
        selected = max(revisions) if revision is None else revision
        try:
            return revisions[selected]
        except KeyError as exc:
            raise KeyError(f"unknown schema revision {schema_ref}@{selected}") from exc

    def maybe_schema(self, schema_ref: str, revision: int | None = None) -> MeaningSchema | None:
        try:
            return self.schema(schema_ref, revision)
        except KeyError:
            return None

    def maybe_authoritative_schema(self, schema_ref: str) -> MeaningSchema | None:
        try:
            return self.authoritative_schema(schema_ref)
        except KeyError:
            return None

    def entitlement(self, entitlement_ref: str, revision: int | None = None) -> FacetEntitlement:
        revisions = self._entitlements.get(entitlement_ref)
        if not revisions:
            raise KeyError(entitlement_ref)
        selected = max(revisions) if revision is None else revision
        try:
            return revisions[selected]
        except KeyError as exc:
            raise KeyError(f"unknown entitlement revision {entitlement_ref}@{selected}") from exc

    @staticmethod
    def _effective_revisions(revisions):
        """Return immutable revisions not superseded by a usable later record.

        Boot records are read-only, so a writable overlay cannot rewrite an old
        active row merely to mark it superseded.  Supersession is therefore an
        effective lifecycle relation derived from the newer revision's explicit
        ``supersedes_revision`` pin.
        """
        superseded = {
            item.supersedes_revision
            for item in revisions.values()
            if item.lifecycle_status in _SUPERSESSION_AUTHORITY
            and item.supersedes_revision is not None
        }
        return tuple(
            item for item in revisions.values()
            if item.lifecycle_status not in _TERMINAL and item.revision not in superseded
        )

    def authoritative_schema(self, schema_ref: str) -> MeaningSchema:
        revisions = self._schemas.get(schema_ref)
        if not revisions:
            raise KeyError(schema_ref)
        usable = tuple(
            item for item in self._effective_revisions(revisions)
            if item.lifecycle_status in _AUTHORITY_LIFECYCLES
        )
        if not usable:
            raise KeyError(f"no authoritative schema revision for {schema_ref}")
        return max(usable, key=lambda item: (_LIFECYCLE_RANK[item.lifecycle_status], item.revision))

    def authoritative_entitlement(self, entitlement_ref: str) -> FacetEntitlement:
        revisions = self._entitlements.get(entitlement_ref)
        if not revisions:
            raise KeyError(entitlement_ref)
        usable = tuple(
            item for item in self._effective_revisions(revisions)
            if item.lifecycle_status in _AUTHORITY_LIFECYCLES
        )
        if not usable:
            raise KeyError(f"no authoritative entitlement revision for {entitlement_ref}")
        return max(usable, key=lambda item: (_LIFECYCLE_RANK[item.lifecycle_status], item.revision))

    def schema_for_use(
        self,
        schema_ref: str,
        operation: UseOperation | str,
        *,
        provisional: bool = False,
    ) -> MeaningSchema:
        resolved = operation if isinstance(operation, UseOperation) else UseOperation(operation)
        revisions = self._schemas.get(schema_ref)
        if not revisions:
            raise KeyError(schema_ref)
        candidates = [
            item for item in self._effective_revisions(revisions)
            if schema_authorizes_use(item, resolved, provisional=provisional)
        ]
        if not candidates:
            raise KeyError(f"no revision of {schema_ref} authorizes {resolved.value}")
        return max(candidates, key=lambda item: (_LIFECYCLE_RANK[item.lifecycle_status], item.revision))

    def iter_schemas(self, *, all_revisions: bool = False) -> Iterator[MeaningSchema]:
        for ref in sorted(self._schemas):
            revisions = self._schemas[ref]
            if all_revisions:
                for revision in sorted(revisions):
                    yield revisions[revision]
            else:
                try:
                    yield self.authoritative_schema(ref)
                except KeyError:
                    continue

    def iter_entitlements(self, *, all_revisions: bool = False) -> Iterator[FacetEntitlement]:
        for ref in sorted(self._entitlements):
            revisions = self._entitlements[ref]
            if all_revisions:
                for revision in sorted(revisions):
                    yield revisions[revision]
            else:
                try:
                    yield self.authoritative_entitlement(ref)
                except KeyError:
                    continue

    def active_schemas(self, schema_class: SchemaClass | None = None) -> tuple[MeaningSchema, ...]:
        result: list[MeaningSchema] = []
        for ref in sorted(self._schemas):
            active = [
                item for item in self._schemas[ref].values()
                if item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
                and (schema_class is None or item.schema_class == schema_class)
            ]
            if active:
                result.append(max(active, key=lambda item: item.revision))
        return tuple(result)

    def resolve_parent(self, link: SchemaParentLink) -> MeaningSchema:
        if link.revision_policy == ParentRevisionPolicy.AUTHORITATIVE:
            return self.authoritative_schema(link.parent_ref)
        if link.revision_policy == ParentRevisionPolicy.EXACT:
            assert link.revision is not None
            return self.schema(link.parent_ref, link.revision)
        assert link.revision is not None
        revisions = self._schemas.get(link.parent_ref, {})
        candidates = [
            item for revision, item in revisions.items()
            if revision >= link.revision and item.lifecycle_status not in _TERMINAL
        ]
        if not candidates:
            raise KeyError(f"no revision of {link.parent_ref} satisfies minimum {link.revision}")
        return max(candidates, key=lambda item: (_LIFECYCLE_RANK[item.lifecycle_status], item.revision))

    def type_closure(self, type_ref: str, revision: int | None = None) -> frozenset[str]:
        root = self.schema(type_ref, revision) if revision is not None else self.authoritative_schema(type_ref)
        if not isinstance(root, ReferentTypeSchema):
            raise TypeError(f"{type_ref} is not a referent type schema")
        key = (root.schema_ref, root.revision)
        cached = self._type_closure_cache.get(key)
        if cached is not None:
            return cached
        complete: set[str] = set()
        visiting: list[str] = []

        def visit(schema: ReferentTypeSchema) -> None:
            if schema.schema_ref in complete:
                return
            if schema.schema_ref in visiting:
                index = visiting.index(schema.schema_ref)
                raise InheritanceCycleError(tuple(visiting[index:] + [schema.schema_ref]))
            visiting.append(schema.schema_ref)
            for link in sorted(schema.parent_links, key=lambda item: (-item.priority, item.parent_ref)):
                parent = self.resolve_parent(link)
                if not isinstance(parent, ReferentTypeSchema):
                    raise TypeError(f"referent type {schema.schema_ref} inherits non-type {parent.schema_ref}")
                visit(parent)
            visiting.pop()
            complete.add(schema.schema_ref)

        visit(root)
        result = frozenset(complete)
        self._type_closure_cache[key] = result
        return result

    def direct_entitlements_for_type(self, type_ref: str) -> tuple[FacetEntitlement, ...]:
        result = []
        for ref in sorted(self._entitlements):
            try:
                item = self.authoritative_entitlement(ref)
            except KeyError:
                continue
            if item.owner_type_ref == type_ref:
                result.append(item)
        return tuple(result)

    def validate(self) -> ValidationReport:
        issues: list[ValidationIssue] = []
        for schema in self.iter_schemas(all_revisions=True):
            self._validate_schema(schema, issues)
        for entitlement in self.iter_entitlements(all_revisions=True):
            self._validate_entitlement(entitlement, issues)
        self._validate_revision_sets(issues)
        self._validate_entitlement_revision_sets(issues)
        self._validate_type_cycles(issues)
        issues.sort(key=lambda item: (item.severity.value, item.code, item.target_ref, item.dependency_ref or ""))
        return ValidationReport(tuple(issues))

    def snapshot_fingerprint(self) -> str:
        records = [item.record_fingerprint for item in self.iter_schemas(all_revisions=True)]
        records.extend(item.record_fingerprint for item in self.iter_entitlements(all_revisions=True))
        return semantic_fingerprint("schema-snapshot", tuple(sorted(records)), 64)

    def _validate_revision_sets(self, issues: list[ValidationIssue]) -> None:
        for ref, revisions in self._schemas.items():
            active = [
                item for item in self._effective_revisions(revisions)
                if item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
            ]
            if len(active) > 1:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR, "multiple_active_revisions", ref,
                    f"multiple active revisions: {sorted(item.revision for item in active)}",
                ))
            for item in revisions.values():
                if item.supersedes_revision is not None and item.supersedes_revision not in revisions:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, "missing_superseded_revision", ref,
                        f"revision {item.revision} supersedes missing revision {item.supersedes_revision}",
                    ))

    def _validate_schema(self, schema: MeaningSchema, issues: list[ValidationIssue]) -> None:
        if schema.schema_class == SchemaClass.MEANING and schema.lifecycle_status in {
            SchemaLifecycleStatus.COMPETENCE_VERIFIED, SchemaLifecycleStatus.ACTIVE
        }:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "generic_schema_executable", schema.schema_ref,
                "generic MeaningSchema cannot become executable; use a typed schema family",
            ))

        for link in schema.parent_links:
            try:
                parent = self.resolve_parent(link)
            except KeyError:
                self._missing(schema.lifecycle_status, issues, "missing_parent", schema.schema_ref, link.parent_ref, "parent schema is unresolved")
                continue
            allowed_parent_classes = _ALLOWED_PARENT_CLASSES[schema.schema_class]
            if parent.schema_class not in allowed_parent_classes:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR, "parent_class_mismatch", schema.schema_ref,
                    f"{schema.schema_class.value} inherits incompatible {parent.schema_class.value}",
                    parent.schema_ref,
                ))
            if (
                schema.lifecycle_status in {SchemaLifecycleStatus.COMPETENCE_VERIFIED, SchemaLifecycleStatus.ACTIVE}
                and parent.lifecycle_status in {SchemaLifecycleStatus.CANDIDATE, SchemaLifecycleStatus.STRUCTURALLY_CLOSED}
            ):
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR, "parent_lifecycle_not_usable", schema.schema_ref,
                    f"parent {parent.schema_ref}@{parent.revision} is {parent.lifecycle_status.value}",
                    parent.schema_ref,
                ))

        for port in schema.local_ports:
            for accepted_type_ref in port.accepted_type_refs:
                target = self.maybe_authoritative_schema(accepted_type_ref)
                if target is None:
                    self._missing(schema.lifecycle_status, issues, "missing_port_type", schema.schema_ref, accepted_type_ref, f"port {port.port_ref} type is unresolved")
                elif not isinstance(target, ReferentTypeSchema):
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, "port_type_class_mismatch", schema.schema_ref,
                        f"port {port.port_ref} accepts non-type schema {accepted_type_ref}", accepted_type_ref,
                    ))

        for dependency in schema.dependencies:
            self._validate_dependency(
                schema.schema_ref, schema.lifecycle_status, schema.use_profile, dependency, issues
            )

        self._validate_use_profile(
            schema.schema_ref, schema.lifecycle_status, schema.use_profile, schema.competence_hooks, issues
        )
        self._validate_specialized_references(schema, issues)

        if isinstance(schema, StateValueSchema):
            dimension = self.maybe_authoritative_schema(schema.dimension_ref)
            if dimension is None:
                self._missing(schema.lifecycle_status, issues, "missing_state_dimension", schema.schema_ref, schema.dimension_ref, "state value dimension is unresolved")
            elif not isinstance(dimension, StateDimensionSchema):
                issues.append(ValidationIssue(ValidationSeverity.ERROR, "state_dimension_class_mismatch", schema.schema_ref, f"{schema.dimension_ref} is not a state dimension", schema.dimension_ref))

        if isinstance(schema, StateDimensionSchema):
            for value_ref in schema.value_schema_refs:
                value = self.maybe_authoritative_schema(value_ref)
                if value is None:
                    self._missing(schema.lifecycle_status, issues, "missing_state_value", schema.schema_ref, value_ref, "state dimension value is unresolved")
                elif not isinstance(value, StateValueSchema):
                    issues.append(ValidationIssue(ValidationSeverity.ERROR, "state_value_class_mismatch", schema.schema_ref, f"{value_ref} is not a state value", value_ref))
                elif value.dimension_ref != schema.schema_ref:
                    issues.append(ValidationIssue(ValidationSeverity.ERROR, "state_value_backref_mismatch", schema.schema_ref, f"{value_ref} points to {value.dimension_ref}", value_ref))

        if isinstance(schema, UnitSchema):
            target = self.maybe_authoritative_schema(schema.measure_dimension_ref)
            if target is None:
                self._missing(schema.lifecycle_status, issues, "missing_measure_dimension", schema.schema_ref, schema.measure_dimension_ref, "unit measure dimension is unresolved")
            elif not isinstance(target, MeasureDimensionSchema):
                issues.append(ValidationIssue(ValidationSeverity.ERROR, "measure_dimension_class_mismatch", schema.schema_ref, f"{schema.measure_dimension_ref} is not a measure dimension", schema.measure_dimension_ref))

        if isinstance(schema, ActionSchema) and schema.controlling_port_ref is None and schema.intentional_required:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR if schema.lifecycle_status in _CLOSED else ValidationSeverity.UNRESOLVED,
                "missing_controlling_port", schema.schema_ref,
                "intentional action has no controlling participant port",
            ))

        if isinstance(schema, PropertySchema) and schema.lifecycle_status in _CLOSED:
            if not schema.holder_type_refs and not schema.local_ports:
                issues.append(ValidationIssue(ValidationSeverity.ERROR, "untyped_property_holder", schema.schema_ref, "closed property has no holder type or typed holder port"))

    def _validate_use_profile(
        self,
        record_ref: str,
        lifecycle: SchemaLifecycleStatus,
        use_profile,
        competence_hooks,
        issues: list[ValidationIssue],
    ) -> None:
        decisions = {item.operation: item.decision for item in use_profile.authorizations}
        # Candidate use profiles are proposals, not authority. They may name the
        # use axes they seek to prove, while schema_authorizes_use/schema_for_use
        # keep executable ALLOW unavailable until active promotion.
        if lifecycle in {SchemaLifecycleStatus.COMPETENCE_VERIFIED, SchemaLifecycleStatus.ACTIVE}:
            required_hooks = {
                (item.operation, item.case_ref) for item in competence_hooks if item.required
            }
            for operation, decision in decisions.items():
                if decision == UseDecision.ALLOW and operation in {
                    UseOperation.INFER, UseOperation.TRANSITION, UseOperation.IMPACT,
                    UseOperation.PLAN, UseOperation.EXECUTE, UseOperation.REALIZE,
                } and not any(op == operation for op, _ in required_hooks):
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, "missing_competence_hook", record_ref,
                        f"{lifecycle.value} {operation.value} authorization has no required competence hook",
                    ))

    def _validate_dependency(
        self,
        owner_ref: str,
        lifecycle: SchemaLifecycleStatus,
        use_profile,
        dependency: SchemaDependency,
        issues: list[ValidationIssue],
    ) -> None:
        relevant = not dependency.required_for or any(
            use_profile.decision_for(operation) in {UseDecision.PROVISIONAL, UseDecision.ALLOW}
            for operation in dependency.required_for
        )
        if not relevant:
            return

        target = self._resolve_dependency(dependency)
        if target is None:
            if dependency.required:
                self._missing(
                    lifecycle, issues, "missing_required_dependency", owner_ref,
                    dependency.dependency_ref, dependency.reason or "required dependency is unresolved",
                )
            return
        if dependency.minimum_revision is not None and target.revision < dependency.minimum_revision:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "dependency_revision_too_old", owner_ref,
                f"{dependency.dependency_ref}@{target.revision} is below {dependency.minimum_revision}",
                dependency.dependency_ref,
            ))
        if (
            dependency.required
            and lifecycle in {SchemaLifecycleStatus.COMPETENCE_VERIFIED, SchemaLifecycleStatus.ACTIVE}
            and target.lifecycle_status in {
                SchemaLifecycleStatus.CANDIDATE,
                SchemaLifecycleStatus.STRUCTURALLY_CLOSED,
                SchemaLifecycleStatus.PROVISIONAL,
                SchemaLifecycleStatus.REJECTED,
            }
        ):
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "dependency_lifecycle_not_usable", owner_ref,
                f"required dependency {dependency.dependency_ref}@{target.revision} is "
                f"{target.lifecycle_status.value}",
                dependency.dependency_ref,
            ))

    def _resolve_dependency(self, dependency: SchemaDependency):
        if dependency.exact_revision is not None:
            return (
                self.maybe_schema(dependency.dependency_ref, dependency.exact_revision)
                or self._maybe_entitlement(dependency.dependency_ref, dependency.exact_revision)
            )

        schema_revisions = self._schemas.get(dependency.dependency_ref, {})
        entitlement_revisions = self._entitlements.get(dependency.dependency_ref, {})
        candidates = [
            item
            for revision, item in (*schema_revisions.items(), *entitlement_revisions.items())
            if (dependency.minimum_revision is None or revision >= dependency.minimum_revision)
            and item.lifecycle_status not in _TERMINAL
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: (_LIFECYCLE_RANK[item.lifecycle_status], item.revision),
        )

    def _maybe_entitlement(
        self, entitlement_ref: str, revision: int | None = None
    ) -> FacetEntitlement | None:
        try:
            return self.entitlement(entitlement_ref, revision)
        except KeyError:
            return None

    def _validate_entitlement(self, entitlement: FacetEntitlement, issues: list[ValidationIssue]) -> None:
        owner = self.maybe_authoritative_schema(entitlement.owner_type_ref)
        facet = self.maybe_authoritative_schema(entitlement.facet_ref)
        if owner is None:
            self._missing(entitlement.lifecycle_status, issues, "missing_entitlement_owner", entitlement.entitlement_ref, entitlement.owner_type_ref, "entitlement owner is unresolved")
        elif not isinstance(owner, ReferentTypeSchema):
            issues.append(ValidationIssue(ValidationSeverity.ERROR, "entitlement_owner_class_mismatch", entitlement.entitlement_ref, f"{entitlement.owner_type_ref} is not a referent type", entitlement.owner_type_ref))
        if facet is None:
            self._missing(entitlement.lifecycle_status, issues, "missing_entitlement_facet", entitlement.entitlement_ref, entitlement.facet_ref, "entitlement facet is unresolved")
        elif not isinstance(facet, FacetSchema):
            issues.append(ValidationIssue(ValidationSeverity.ERROR, "entitlement_facet_class_mismatch", entitlement.entitlement_ref, f"{entitlement.facet_ref} is not a facet", entitlement.facet_ref))
        for dependency in entitlement.dependencies:
            self._validate_dependency(
                entitlement.entitlement_ref, entitlement.lifecycle_status,
                entitlement.use_profile, dependency, issues,
            )
        self._validate_use_profile(
            entitlement.entitlement_ref, entitlement.lifecycle_status,
            entitlement.use_profile, entitlement.competence_hooks, issues,
        )
        for value_domain_ref in entitlement.value_domain_refs:
            if self.maybe_authoritative_schema(value_domain_ref) is None:
                self._missing(
                    entitlement.lifecycle_status, issues, "missing_entitlement_value_domain",
                    entitlement.entitlement_ref, value_domain_ref,
                    "entitlement value domain is unresolved",
                )
        if entitlement.applicability == EntitlementApplicability.PROHIBITED and entitlement.default_rule_refs:
            issues.append(ValidationIssue(ValidationSeverity.ERROR, "prohibited_entitlement_has_default", entitlement.entitlement_ref, "prohibited facet cannot define default expectations"))
        if isinstance(owner, ReferentTypeSchema) and owner.facet_entitlement_refs and entitlement.entitlement_ref not in owner.facet_entitlement_refs:
            issues.append(ValidationIssue(ValidationSeverity.WARNING, "entitlement_not_indexed_by_owner", entitlement.entitlement_ref, "owner type does not list this entitlement", owner.schema_ref))

    def _validate_entitlement_revision_sets(
        self, issues: list[ValidationIssue]
    ) -> None:
        for ref, revisions in self._entitlements.items():
            active = [
                item for item in self._effective_revisions(revisions)
                if item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
            ]
            if len(active) > 1:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR, "multiple_active_entitlement_revisions", ref,
                    f"multiple active revisions: {sorted(item.revision for item in active)}",
                ))
            for item in revisions.values():
                if item.supersedes_revision is not None and item.supersedes_revision not in revisions:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, "missing_superseded_entitlement_revision", ref,
                        f"revision {item.revision} supersedes missing revision "
                        f"{item.supersedes_revision}",
                    ))

    def _validate_specialized_references(
        self, schema: MeaningSchema, issues: list[ValidationIssue]
    ) -> None:
        def refs(
            values, expected_classes: frozenset[SchemaClass] | None, code: str, label: str
        ) -> None:
            for target_ref in values:
                target = self.maybe_authoritative_schema(target_ref)
                if target is None:
                    self._missing(
                        schema.lifecycle_status, issues, f"missing_{code}", schema.schema_ref,
                        target_ref, f"{label} is unresolved",
                    )
                elif expected_classes is not None and target.schema_class not in expected_classes:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, f"{code}_class_mismatch", schema.schema_ref,
                        f"{target_ref} is {target.schema_class.value}, expected "
                        f"{sorted(item.value for item in expected_classes)}",
                        target_ref,
                    ))

        if isinstance(schema, ReferentTypeSchema):
            for entitlement_ref in schema.facet_entitlement_refs:
                entitlement = self._maybe_entitlement(entitlement_ref)
                if entitlement is None:
                    self._missing(
                        schema.lifecycle_status, issues, "missing_type_entitlement",
                        schema.schema_ref, entitlement_ref,
                        "referent type entitlement is unresolved",
                    )
                elif entitlement.owner_type_ref != schema.schema_ref:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, "type_entitlement_owner_mismatch",
                        schema.schema_ref,
                        f"{entitlement_ref} belongs to {entitlement.owner_type_ref}",
                        entitlement_ref,
                    ))
        if isinstance(schema, PropertySchema):
            refs(schema.holder_type_refs, frozenset({SchemaClass.REFERENT_TYPE}), "property_holder_type", "property holder type")
            refs(schema.value_type_refs, frozenset({SchemaClass.REFERENT_TYPE}), "property_value_type", "property value type")
            refs(schema.value_schema_refs, None, "property_value_schema", "property value schema")
        if isinstance(schema, StateDimensionSchema):
            refs(schema.holder_type_refs, frozenset({SchemaClass.REFERENT_TYPE}), "state_holder_type", "state holder type")
        if isinstance(schema, RoleSchema):
            refs(schema.holder_type_refs, frozenset({SchemaClass.REFERENT_TYPE}), "role_holder_type", "role holder type")
            refs(schema.context_type_refs, frozenset({SchemaClass.REFERENT_TYPE}), "role_context_type", "role context type")
        if isinstance(schema, FunctionSchema):
            refs(schema.holder_type_refs, frozenset({SchemaClass.REFERENT_TYPE}), "function_holder_type", "function holder type")
            refs(schema.contribution_schema_refs, None, "function_contribution", "function contribution")
            refs(schema.realization_action_refs, frozenset({SchemaClass.ACTION}), "function_action", "function action")
        if isinstance(schema, RelationSchema) and schema.inverse_relation_ref:
            refs((schema.inverse_relation_ref,), frozenset({SchemaClass.RELATION}), "inverse_relation", "inverse relation")
        if isinstance(schema, MeasureDimensionSchema):
            refs(schema.quantity_type_refs, frozenset({SchemaClass.REFERENT_TYPE}), "quantity_type", "quantity type")
            if schema.canonical_unit_ref:
                refs((schema.canonical_unit_ref,), frozenset({SchemaClass.UNIT}), "canonical_unit", "canonical unit")
        if isinstance(schema, DiscourseActSchema):
            # Port existence is enforced by the dataclass; obligation schemas are
            # intentionally deferred to the response-goal architecture.
            pass
        if isinstance(schema, (EventSchema, OperatorSchema, DiscourseRelationSchema, ResponsePolicySchema)):
            # Their non-parent contract references belong to later typed stores.
            pass

    def _validate_type_cycles(self, issues: list[ValidationIssue]) -> None:
        checked: set[tuple[str, int]] = set()
        for schema in self.iter_schemas(all_revisions=True):
            if not isinstance(schema, ReferentTypeSchema) or (schema.schema_ref, schema.revision) in checked:
                continue
            checked.add((schema.schema_ref, schema.revision))
            try:
                self.type_closure(schema.schema_ref, schema.revision)
            except InheritanceCycleError as exc:
                issues.append(ValidationIssue(ValidationSeverity.ERROR, "type_inheritance_cycle", schema.schema_ref, str(exc)))
            except (KeyError, TypeError):
                pass

    @staticmethod
    def _missing(
        lifecycle: SchemaLifecycleStatus,
        issues: list[ValidationIssue],
        code: str,
        target_ref: str,
        dependency_ref: str,
        message: str,
    ) -> None:
        severity = ValidationSeverity.ERROR if lifecycle in {
            SchemaLifecycleStatus.COMPETENCE_VERIFIED,
            SchemaLifecycleStatus.ACTIVE,
        } else ValidationSeverity.UNRESOLVED
        issues.append(ValidationIssue(severity, code, target_ref, message, dependency_ref))
