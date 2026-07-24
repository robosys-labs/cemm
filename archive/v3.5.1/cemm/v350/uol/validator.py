"""Structural and schema-backed validation for v3.5 UOL graphs.

Validation is deliberately stricter than construction. Candidate graphs may
preserve unresolved dependencies, but they may not silently cross identity,
context, admission, lifecycle, or typed-port boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..schema.model import (
    OpenBindingPurpose,
    PortFillerClass,
    ReferentTypeSchema,
    SchemaClass,
    SchemaLifecycleStatus,
    StateDimensionSchema,
    StateValueSchema,
    UseDecision,
    UseOperation,
    ValidationSeverity,
)
from ..schema.registry import SchemaRegistry
from .model import (
    CapabilityDelta,
    EventOccurrence,
    FillerRef,
    ImpactAssessment,
    ImportanceAssessment,
    OccurrenceStatus,
    PropositionReferent,
    QuotedLiteral,
    StateDelta,
    UOLGraph,
)


@dataclass(frozen=True, slots=True)
class UOLValidationIssue:
    severity: ValidationSeverity
    code: str
    target_ref: str
    message: str
    dependency_ref: str | None = None


@dataclass(frozen=True, slots=True)
class UOLValidationReport:
    issues: tuple[UOLValidationIssue, ...]

    @property
    def errors(self) -> tuple[UOLValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity == ValidationSeverity.ERROR)

    @property
    def warnings(self) -> tuple[UOLValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity == ValidationSeverity.WARNING)

    @property
    def unresolved(self) -> tuple[UOLValidationIssue, ...]:
        return tuple(item for item in self.issues if item.severity == ValidationSeverity.UNRESOLVED)

    @property
    def valid(self) -> bool:
        return not self.errors

    def require_valid(self) -> None:
        if self.errors:
            raise ValueError("; ".join(f"{item.code}:{item.message}" for item in self.errors))


_NON_TRANSITIONING_EVENT_STATUSES = frozenset({
    OccurrenceStatus.MENTIONED,
    OccurrenceStatus.CLAIMED,
    OccurrenceStatus.REPORTED,
    OccurrenceStatus.PLANNED,
    OccurrenceStatus.HYPOTHETICAL,
    OccurrenceStatus.COUNTERFACTUAL,
    OccurrenceStatus.FICTIONAL,
    OccurrenceStatus.NON_OCCURRING,
})
_TERMINAL_SCHEMA_STATUSES = frozenset({
    SchemaLifecycleStatus.SUPERSEDED,
    SchemaLifecycleStatus.REJECTED,
})


class UOLValidator:
    def __init__(self, schemas: SchemaRegistry):
        self._schemas = schemas

    def validate(self, graph: UOLGraph, *, provisional: bool = False) -> UOLValidationReport:
        issues: list[UOLValidationIssue] = []
        self._validate_referents(graph, issues)
        self._validate_referent_specializations(graph, issues)
        self._validate_variables(graph, issues)
        self._validate_coordination(graph, issues)
        self._validate_scopes(graph, issues)

        for application in graph.applications.values():
            self._validate_application(graph, application, issues, provisional=provisional)
        for proposition in graph.propositions.values():
            self._validate_proposition(graph, proposition, issues)
        self._validate_claims(graph, issues)
        self._validate_events(graph, issues)
        self._validate_state_deltas(graph, issues)
        self._validate_capability_deltas(graph, issues)
        self._validate_impacts(graph, issues)
        self._validate_importance(graph, issues)

        for root in graph.root_refs:
            if not self._filler_exists(graph, root):
                issues.append(self._error(
                    "missing_root", graph.graph_ref, "root reference is unresolved", root.ref
                ))

        issues.sort(
            key=lambda item: (
                item.severity.value,
                item.code,
                item.target_ref,
                item.dependency_ref or "",
            )
        )
        return UOLValidationReport(tuple(issues))

    def _validate_referents(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for referent in graph.referents.values():
            for type_ref in referent.type_refs:
                schema = self._schemas.maybe_authoritative_schema(type_ref)
                if schema is None:
                    issues.append(self._unresolved(
                        "missing_referent_type", referent.referent_ref,
                        "referent type is unresolved", type_ref,
                    ))
                    continue
                if not isinstance(schema, ReferentTypeSchema):
                    issues.append(self._error(
                        "referent_type_class", referent.referent_ref,
                        f"{type_ref} is not a referent-type schema", type_ref,
                    ))
                    continue
                if referent.storage_kind not in schema.storage_kinds:
                    issues.append(self._error(
                        "referent_type_storage_mismatch", referent.referent_ref,
                        f"{type_ref} rejects storage kind {referent.storage_kind.value}",
                        type_ref,
                    ))
            if referent.valid_time_ref and not self._any_ref_exists(graph, referent.valid_time_ref):
                issues.append(self._unresolved(
                    "missing_referent_valid_time", referent.referent_ref,
                    "referent valid-time reference is unresolved", referent.valid_time_ref,
                ))

    def _validate_referent_specializations(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for ref, proposition in graph.propositions.items():
            base = graph.referents.get(ref)
            if base is None:
                issues.append(self._error(
                    "proposition_missing_base_referent", ref,
                    "specialized proposition has no base referent",
                ))
            elif proposition.context_ref not in base.context_refs:
                issues.append(self._error(
                    "proposition_base_context_mismatch", ref,
                    "proposition context is absent from its base referent", proposition.context_ref,
                ))
        for ref, event in graph.events.items():
            base = graph.referents.get(ref)
            if base is None:
                issues.append(self._error(
                    "event_missing_base_referent", ref,
                    "specialized event has no base referent",
                ))
            elif event.context_ref not in base.context_refs:
                issues.append(self._error(
                    "event_base_context_mismatch", ref,
                    "event context is absent from its base referent", event.context_ref,
                ))
        for ref, claim in graph.claims.items():
            base = graph.referents.get(ref)
            if base is None:
                issues.append(self._error(
                    "claim_missing_base_referent", ref,
                    "specialized claim has no base referent",
                ))
            elif claim.source_context_ref not in base.context_refs:
                issues.append(self._error(
                    "claim_base_context_mismatch", ref,
                    "claim source context is absent from its base referent",
                    claim.source_context_ref,
                ))

    def _validate_variables(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for variable in graph.variables.values():
            for type_ref in variable.expected_type_refs:
                schema = self._schemas.maybe_authoritative_schema(type_ref)
                if schema is None:
                    issues.append(self._unresolved(
                        "missing_variable_type", variable.variable_ref,
                        "variable expected type is unresolved", type_ref,
                    ))
                elif schema.schema_class != SchemaClass.REFERENT_TYPE:
                    issues.append(self._error(
                        "variable_type_class", variable.variable_ref,
                        "variable expected type is not a referent type", type_ref,
                    ))
            for restriction_ref in variable.restriction_refs:
                if not self._any_ref_exists(graph, restriction_ref):
                    issues.append(self._error(
                        "missing_variable_restriction", variable.variable_ref,
                        "variable restriction is unresolved", restriction_ref,
                    ))
            if variable.projection_ref and not self._any_ref_exists(graph, variable.projection_ref):
                issues.append(self._error(
                    "missing_variable_projection", variable.variable_ref,
                    "variable projection is unresolved", variable.projection_ref,
                ))

    def _validate_coordination(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for group in graph.coordination_groups.values():
            for member in group.members:
                if not self._filler_exists(graph, member):
                    issues.append(self._error(
                        "missing_coordination_member", group.group_ref,
                        "coordination member is unresolved", member.ref,
                    ))

    def _validate_scopes(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for relation in graph.scope_relations:
            operator = graph.applications.get(relation.operator_application_ref)
            if operator is None:
                issues.append(self._error(
                    "missing_scope_operator", relation.scope_relation_ref,
                    "scope operator application is unresolved",
                    relation.operator_application_ref,
                ))
            else:
                schema = self._schemas.maybe_schema(
                    operator.schema_ref, operator.schema_revision
                )
                if schema is not None and schema.schema_class != SchemaClass.OPERATOR:
                    issues.append(self._error(
                        "scope_application_not_operator", relation.scope_relation_ref,
                        "scope relation points to a non-operator schema",
                        operator.application_ref,
                    ))
            if not self._filler_exists(graph, relation.scoped_ref):
                issues.append(self._error(
                    "missing_scoped_content", relation.scope_relation_ref,
                    "scoped content is unresolved", relation.scoped_ref.ref,
                ))

    def _validate_application(
        self, graph: UOLGraph, application: Any, issues: list[UOLValidationIssue],
        *, provisional: bool,
    ) -> None:
        try:
            schema = self._schemas.schema(
                application.schema_ref, application.schema_revision
            )
        except KeyError:
            issues.append(self._error(
                "missing_application_schema", application.application_ref,
                "application schema revision is unresolved", application.schema_ref,
            ))
            return

        if schema.lifecycle_status in {
            SchemaLifecycleStatus.CANDIDATE,
            SchemaLifecycleStatus.STRUCTURALLY_CLOSED,
            *_TERMINAL_SCHEMA_STATUSES,
        }:
            issues.append(self._error(
                "schema_lifecycle_not_usable", application.application_ref,
                f"schema lifecycle is {schema.lifecycle_status.value}", schema.schema_ref,
            ))
        elif schema.lifecycle_status == SchemaLifecycleStatus.PROVISIONAL and not provisional:
            issues.append(self._error(
                "provisional_schema_requires_provisional_graph",
                application.application_ref,
                "provisional schema cannot authorize a non-provisional graph",
                schema.schema_ref,
            ))

        if not schema.use_profile.permits(
            application.use_operation, provisional=provisional
        ):
            issues.append(self._error(
                "schema_use_not_authorized", application.application_ref,
                f"{schema.schema_ref}@{schema.revision} does not authorize "
                f"{application.use_operation.value}", schema.schema_ref,
            ))

        binding_map = {item.port_ref: item for item in application.bindings}
        known_ports = {item.port_ref for item in schema.local_ports}
        for port_ref in binding_map.keys() - known_ports:
            issues.append(self._error(
                "unknown_local_port", application.application_ref,
                f"binding uses unknown port {port_ref}", schema.schema_ref,
            ))
        for port in schema.local_ports:
            binding = binding_map.get(port.port_ref)
            count = len(binding.fillers) if binding else 0
            if not port.cardinality.accepts(count):
                issues.append(self._error(
                    "port_cardinality", application.application_ref,
                    f"port {port.port_ref} count {count} violates "
                    f"{port.cardinality.minimum}..{port.cardinality.maximum}",
                    schema.schema_ref,
                ))
                continue
            if binding is None:
                continue
            if binding.ordered != port.ordered_fillers:
                issues.append(self._error(
                    "port_ordering_mismatch", application.application_ref,
                    f"port {port.port_ref} ordered={port.ordered_fillers} but "
                    f"binding ordered={binding.ordered}", schema.schema_ref,
                ))
            for filler in binding.fillers:
                filler_class = (
                    PortFillerClass.QUOTED_LITERAL
                    if isinstance(filler, QuotedLiteral)
                    else filler.filler_class
                )
                # A semantic variable is an explicitly authorized open binding,
                # not an ordinary closed-world filler class.  LocalPortSchema
                # already models this independently through open_binding_purposes;
                # requiring every schema to duplicate SEMANTIC_VARIABLE in
                # filler_classes would make partial composition data-dependent
                # on a redundant declaration and contradict the metamodel.
                variable_open_binding = (
                    filler_class == PortFillerClass.SEMANTIC_VARIABLE
                    and binding.open_binding_purpose is not None
                    and binding.open_binding_purpose in port.open_binding_purposes
                )
                if filler_class not in port.filler_classes and not variable_open_binding:
                    dependency = (
                        filler.literal_ref if isinstance(filler, QuotedLiteral) else filler.ref
                    )
                    issues.append(self._error(
                        "port_filler_class", application.application_ref,
                        f"port {port.port_ref} rejects {filler_class.value}", dependency,
                    ))
                    continue
                if isinstance(filler, QuotedLiteral):
                    continue
                if not self._filler_exists(graph, filler):
                    issues.append(self._error(
                        "missing_port_filler", application.application_ref,
                        f"port {port.port_ref} filler is unresolved", filler.ref,
                    ))
                    continue
                if filler.filler_class == PortFillerClass.SEMANTIC_VARIABLE:
                    purpose = binding.open_binding_purpose
                    if purpose is None or purpose not in port.open_binding_purposes:
                        shown = purpose.value if purpose is not None else "unspecified"
                        issues.append(self._error(
                            "open_binding_not_authorized", application.application_ref,
                            f"port {port.port_ref} does not allow {shown} variables",
                            filler.ref,
                        ))
                    self._validate_variable_for_port(
                        graph, application.application_ref, port, filler.ref, issues
                    )
                elif filler.filler_class == PortFillerClass.REFERENT:
                    self._validate_referent_filler(
                        graph, application.application_ref, port, filler.ref, issues
                    )
                elif (
                    filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION
                    and port.accepted_schema_classes
                ):
                    nested = graph.applications[filler.ref]
                    nested_schema = self._schemas.maybe_schema(
                        nested.schema_ref, nested.schema_revision
                    )
                    if nested_schema is not None:
                        nested_allowed = nested_schema.schema_class in port.accepted_schema_classes
                        # Operators are recursively compositional structural
                        # nodes.  A port's accepted_schema_classes constrain the
                        # eventual semantic operand leaf; an intermediate
                        # operator may wrap that leaf and is validated through
                        # its own exact operand contract and ScopeRelation.
                        recursive_operator = (
                            schema.schema_class == SchemaClass.OPERATOR
                            and nested_schema.schema_class == SchemaClass.OPERATOR
                        )
                        if not nested_allowed and not recursive_operator:
                            issues.append(self._error(
                                "nested_schema_class", application.application_ref,
                                f"port {port.port_ref} rejects "
                                f"{nested_schema.schema_class.value}", filler.ref,
                            ))

    def _validate_variable_for_port(
        self, graph: UOLGraph, application_ref: str, port: Any,
        variable_ref: str, issues: list[UOLValidationIssue],
    ) -> None:
        variable = graph.variables[variable_ref]
        if port.accepted_schema_classes and variable.expected_schema_classes:
            if not port.accepted_schema_classes.intersection(
                variable.expected_schema_classes
            ):
                issues.append(self._error(
                    "variable_schema_constraint", application_ref,
                    f"port {port.port_ref} and variable {variable_ref} have "
                    "incompatible schema-class constraints", variable_ref,
                ))
        if port.accepted_type_refs and variable.expected_type_refs:
            closure: set[str] = set()
            unresolved = False
            for type_ref in variable.expected_type_refs:
                try:
                    closure.update(self._schemas.type_closure(type_ref))
                except (KeyError, TypeError):
                    unresolved = True
            if not closure.intersection(port.accepted_type_refs):
                issue = self._unresolved if unresolved else self._error
                issues.append(issue(
                    "variable_type_constraint", application_ref,
                    f"port {port.port_ref} accepts {port.accepted_type_refs}, "
                    f"variable expects {variable.expected_type_refs}", variable_ref,
                ))

    def _validate_referent_filler(
        self, graph: UOLGraph, application_ref: str, port: Any,
        referent_ref: str, issues: list[UOLValidationIssue],
    ) -> None:
        referent = graph.referents[referent_ref]
        if (
            port.accepted_storage_kinds
            and referent.storage_kind not in port.accepted_storage_kinds
        ):
            issues.append(self._error(
                "referent_storage_kind", application_ref,
                f"port {port.port_ref} rejects {referent.storage_kind.value}",
                referent_ref,
            ))
        if port.accepted_type_refs:
            closure: set[str] = set()
            unresolved = False
            for type_ref in referent.type_refs:
                try:
                    closure.update(self._schemas.type_closure(type_ref))
                except (KeyError, TypeError):
                    unresolved = True
            if not closure.intersection(port.accepted_type_refs):
                issue = self._unresolved if unresolved else self._error
                issues.append(issue(
                    "referent_type_constraint", application_ref,
                    f"port {port.port_ref} accepts {port.accepted_type_refs}, "
                    f"got {referent.type_refs}", referent_ref,
                ))

    def _validate_proposition(
        self, graph: UOLGraph, proposition: PropositionReferent,
        issues: list[UOLValidationIssue],
    ) -> None:
        for content in proposition.content_refs:
            if not self._filler_exists(graph, content):
                issues.append(self._error(
                    "missing_proposition_content", proposition.proposition_ref,
                    "proposition content is unresolved", content.ref,
                ))
        for modality_ref in proposition.modality_application_refs:
            application = graph.applications.get(modality_ref)
            if application is None:
                issues.append(self._error(
                    "missing_modality_application", proposition.proposition_ref,
                    "modality application is unresolved", modality_ref,
                ))
            else:
                schema = self._schemas.maybe_schema(
                    application.schema_ref, application.schema_revision
                )
                if schema is not None and schema.schema_class != SchemaClass.OPERATOR:
                    issues.append(self._error(
                        "modality_not_operator", proposition.proposition_ref,
                        "modality application does not use an operator schema",
                        modality_ref,
                    ))
        for attribution_ref in proposition.attribution_refs:
            if not self._any_ref_exists(graph, attribution_ref):
                issues.append(self._unresolved(
                    "missing_proposition_attribution", proposition.proposition_ref,
                    "proposition attribution is unresolved", attribution_ref,
                ))

    def _validate_claims(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for claim in graph.claims.values():
            proposition = graph.propositions.get(claim.proposition_ref)
            if proposition is None:
                issues.append(self._error(
                    "claim_missing_proposition", claim.claim_ref,
                    "claim occurrence references no proposition", claim.proposition_ref,
                ))
            elif proposition.context_ref != claim.reported_context_ref:
                issues.append(self._error(
                    "claim_context_mismatch", claim.claim_ref,
                    "claim proposition is not in the attributed reported context",
                    claim.proposition_ref,
                ))
            if claim.claimant_ref not in graph.referents:
                issues.append(self._error(
                    "claim_missing_claimant", claim.claim_ref,
                    "claimant referent is unresolved", claim.claimant_ref,
                ))
            for audience_ref in claim.audience_refs:
                if audience_ref not in graph.referents:
                    issues.append(self._error(
                        "claim_missing_audience", claim.claim_ref,
                        "claim audience referent is unresolved", audience_ref,
                    ))
            if (
                claim.certainty_expression_ref
                and not self._any_ref_exists(graph, claim.certainty_expression_ref)
            ):
                issues.append(self._unresolved(
                    "claim_missing_certainty_expression", claim.claim_ref,
                    "claim certainty expression is unresolved",
                    claim.certainty_expression_ref,
                ))

    def _validate_events(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for event in graph.events.values():
            schema = self._schemas.maybe_schema(
                event.event_schema_ref, event.event_schema_revision
            )
            if schema is None:
                issues.append(self._error(
                    "missing_event_schema", event.event_ref,
                    "event occurrence schema is unresolved", event.event_schema_ref,
                ))
            elif schema.schema_class not in {SchemaClass.EVENT, SchemaClass.ACTION}:
                issues.append(self._error(
                    "event_schema_class_mismatch", event.event_ref,
                    f"{schema.schema_ref} is {schema.schema_class.value}", schema.schema_ref,
                ))
            application = graph.applications.get(event.participant_application_ref)
            if application is None:
                issues.append(self._error(
                    "missing_event_application", event.event_ref,
                    "event occurrence has no participant application",
                    event.participant_application_ref,
                ))
            else:
                if (
                    application.schema_ref != event.event_schema_ref
                    or application.schema_revision != event.event_schema_revision
                ):
                    issues.append(self._error(
                        "event_application_schema_mismatch", event.event_ref,
                        "participant application uses a different schema revision",
                        application.application_ref,
                    ))
                if application.context_ref != event.context_ref:
                    issues.append(self._error(
                        "event_application_context_mismatch", event.event_ref,
                        "event and participant application contexts differ",
                        application.application_ref,
                    ))
            for ref, code, label in (
                (event.time_ref, "event_time", "event time"),
                (event.place_ref, "event_place", "event place"),
            ):
                if ref and not self._any_ref_exists(graph, ref):
                    issues.append(self._unresolved(
                        f"missing_{code}", event.event_ref,
                        f"{label} is unresolved", ref,
                    ))
            for ref in (*event.cause_refs, *event.result_refs):
                if not self._any_ref_exists(graph, ref):
                    issues.append(self._unresolved(
                        "missing_event_related_ref", event.event_ref,
                        "event cause/result is unresolved", ref,
                    ))

    def _validate_state_deltas(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        for delta in graph.state_deltas:
            dimension = self._schemas.maybe_schema(
                delta.dimension_ref, delta.dimension_revision
            )
            if dimension is None:
                issues.append(self._unresolved(
                    "missing_state_delta_dimension", delta.delta_ref,
                    "state delta dimension revision is unresolved",
                    delta.dimension_ref,
                ))
            elif not isinstance(dimension, StateDimensionSchema):
                issues.append(self._error(
                    "state_delta_dimension_class", delta.delta_ref,
                    "state delta dimension is not a state-dimension schema",
                    delta.dimension_ref,
                ))
            for value_ref, revision, role in (
                (delta.from_value_ref, delta.from_value_revision, "from"),
                (delta.to_value_ref, delta.to_value_revision, "to"),
            ):
                if value_ref is None:
                    continue
                value_schema = (
                    self._schemas.maybe_schema(value_ref, revision)
                    if revision is not None
                    else self._schemas.maybe_authoritative_schema(value_ref)
                )
                if value_schema is None:
                    issues.append(self._unresolved(
                        "missing_state_delta_value", delta.delta_ref,
                        f"state delta {role} value is unresolved", value_ref,
                    ))
                elif not isinstance(value_schema, StateValueSchema):
                    issues.append(self._error(
                        "state_delta_value_class", delta.delta_ref,
                        "state delta value is not a state-value schema", value_ref,
                    ))
                elif value_schema.dimension_ref != delta.dimension_ref:
                    issues.append(self._error(
                        "state_delta_value_dimension_mismatch", delta.delta_ref,
                        f"{value_ref} belongs to {value_schema.dimension_ref}", value_ref,
                    ))
            if delta.holder_ref not in graph.referents:
                issues.append(self._error(
                    "state_delta_missing_holder", delta.delta_ref,
                    "state delta holder is unresolved", delta.holder_ref,
                ))
            elif isinstance(dimension, StateDimensionSchema) and dimension.holder_type_refs:
                self._validate_holder_types(
                    graph, delta.delta_ref, delta.holder_ref,
                    dimension.holder_type_refs, "state_delta_holder_type", issues,
                )
            event = graph.events.get(delta.trigger_ref)
            if event is not None:
                self._validate_transition_event(event, delta.delta_ref, delta.context_ref, issues)
            elif not self._any_ref_exists(graph, delta.trigger_ref):
                issues.append(self._error(
                    "state_delta_missing_trigger", delta.delta_ref,
                    "state delta trigger is unresolved", delta.trigger_ref,
                ))

    def _validate_capability_deltas(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        state_by_ref = {item.delta_ref: item for item in graph.state_deltas}
        for delta in graph.capability_deltas:
            action = self._schemas.maybe_schema(
                delta.action_schema_ref, delta.action_schema_revision
            )
            if action is None:
                issues.append(self._unresolved(
                    "missing_capability_action", delta.delta_ref,
                    "capability action schema revision is unresolved",
                    delta.action_schema_ref,
                ))
            elif action.schema_class != SchemaClass.ACTION:
                issues.append(self._error(
                    "capability_action_class", delta.delta_ref,
                    "capability delta action is not an action schema",
                    delta.action_schema_ref,
                ))
            state = state_by_ref.get(delta.trigger_ref)
            event = graph.events.get(delta.trigger_ref)
            if state is not None:
                if state.context_ref != delta.context_ref:
                    issues.append(self._error(
                        "capability_delta_context_leak", delta.delta_ref,
                        "state and capability delta contexts differ", state.delta_ref,
                    ))
            elif event is not None:
                self._validate_transition_event(
                    event, delta.delta_ref, delta.context_ref, issues
                )
            else:
                issues.append(self._error(
                    "capability_delta_missing_trigger", delta.delta_ref,
                    "capability delta trigger is unresolved", delta.trigger_ref,
                ))
            if delta.holder_ref not in graph.referents:
                issues.append(self._error(
                    "capability_delta_missing_holder", delta.delta_ref,
                    "capability delta holder is unresolved", delta.holder_ref,
                ))

    def _validate_transition_event(
        self, event: EventOccurrence, target_ref: str, context_ref: str,
        issues: list[UOLValidationIssue],
    ) -> None:
        schema = self._schemas.maybe_schema(
            event.event_schema_ref, event.event_schema_revision
        )
        if schema is None:
            issues.append(self._unresolved(
                "transition_event_schema_unresolved", target_ref,
                "event transition schema revision is unresolved",
                event.event_schema_ref,
            ))
        elif not schema.use_profile.permits(UseOperation.TRANSITION):
            issues.append(self._error(
                "event_transition_not_authorized", target_ref,
                f"{schema.schema_ref}@{schema.revision} does not authorize transition use",
                schema.schema_ref,
            ))
        if event.occurrence_status in _NON_TRANSITIONING_EVENT_STATUSES:
            issues.append(self._error(
                "unadmitted_event_transition", target_ref,
                f"{event.occurrence_status.value} event cannot produce a delta",
                event.event_ref,
            ))
        if not event.admission_refs:
            issues.append(self._error(
                "event_transition_missing_admission", target_ref,
                "event has no independent epistemic admission proof", event.event_ref,
            ))
        if event.context_ref != context_ref:
            issues.append(self._error(
                "transition_context_leak", target_ref,
                "event and delta contexts differ", event.event_ref,
            ))

    def _validate_holder_types(
        self, graph: UOLGraph, target_ref: str, holder_ref: str,
        accepted_type_refs: tuple[str, ...], code: str,
        issues: list[UOLValidationIssue],
    ) -> None:
        holder = graph.referents[holder_ref]
        closure: set[str] = set()
        unresolved = False
        for type_ref in holder.type_refs:
            try:
                closure.update(self._schemas.type_closure(type_ref))
            except (KeyError, TypeError):
                unresolved = True
        if not closure.intersection(accepted_type_refs):
            issue = self._unresolved if unresolved else self._error
            issues.append(issue(
                code, target_ref,
                f"holder types {holder.type_refs} do not satisfy {accepted_type_refs}",
                holder_ref,
            ))

    def _validate_impacts(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        state_by_ref = {item.delta_ref: item for item in graph.state_deltas}
        capability_by_ref = {item.delta_ref: item for item in graph.capability_deltas}
        importance_by_ref = {
            item.assessment_ref: item for item in graph.importance_assessments
        }
        for impact in graph.impact_assessments:
            source = (
                graph.events.get(impact.source_event_or_state_ref)
                or state_by_ref.get(impact.source_event_or_state_ref)
                or capability_by_ref.get(impact.source_event_or_state_ref)
            )
            if source is None:
                issues.append(self._error(
                    "impact_missing_source", impact.assessment_ref,
                    "impact source is unresolved", impact.source_event_or_state_ref,
                ))
            else:
                source_context = getattr(source, "context_ref", None)
                if source_context != impact.context_ref:
                    issues.append(self._error(
                        "impact_context_leak", impact.assessment_ref,
                        "impact and source contexts differ",
                        impact.source_event_or_state_ref,
                    ))
            for ref in (impact.affected_ref, impact.stakeholder_ref):
                if ref not in graph.referents:
                    issues.append(self._error(
                        "impact_missing_referent", impact.assessment_ref,
                        "impact referent is unresolved", ref,
                    ))
            for facet_ref in impact.affected_facet_refs:
                facet = self._schemas.maybe_authoritative_schema(facet_ref)
                if facet is None:
                    issues.append(self._unresolved(
                        "missing_impact_facet", impact.assessment_ref,
                        "affected facet is unresolved", facet_ref,
                    ))
                elif facet.schema_class != SchemaClass.FACET:
                    issues.append(self._error(
                        "impact_facet_class", impact.assessment_ref,
                        "affected facet reference is not a facet schema", facet_ref,
                    ))
            if impact.importance_ref:
                importance = importance_by_ref.get(impact.importance_ref)
                if importance is None:
                    issues.append(self._error(
                        "impact_missing_importance", impact.assessment_ref,
                        "linked importance assessment is unresolved",
                        impact.importance_ref,
                    ))
                elif importance.context_ref != impact.context_ref:
                    issues.append(self._error(
                        "impact_importance_context_mismatch", impact.assessment_ref,
                        "impact and importance contexts differ", impact.importance_ref,
                    ))

    def _validate_importance(
        self, graph: UOLGraph, issues: list[UOLValidationIssue]
    ) -> None:
        impact_refs = {item.assessment_ref for item in graph.impact_assessments}
        for importance in graph.importance_assessments:
            if (
                not self._any_ref_exists(graph, importance.subject_ref)
                and importance.subject_ref not in impact_refs
            ):
                issues.append(self._error(
                    "importance_missing_subject", importance.assessment_ref,
                    "importance subject is unresolved", importance.subject_ref,
                ))
            if importance.stakeholder_ref not in graph.referents:
                issues.append(self._error(
                    "importance_missing_stakeholder", importance.assessment_ref,
                    "importance stakeholder is unresolved",
                    importance.stakeholder_ref,
                ))

    @staticmethod
    def _filler_exists(graph: UOLGraph, filler: FillerRef) -> bool:
        if filler.filler_class == PortFillerClass.REFERENT:
            return filler.ref in graph.referents
        if filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
            return filler.ref in graph.applications
        if filler.filler_class == PortFillerClass.SEMANTIC_VARIABLE:
            return filler.ref in graph.variables
        if filler.filler_class == PortFillerClass.COORDINATION_GROUP:
            return filler.ref in graph.coordination_groups
        return False

    @staticmethod
    def _any_ref_exists(graph: UOLGraph, ref: str) -> bool:
        return (
            ref in graph.referents
            or ref in graph.applications
            or ref in graph.variables
            or ref in graph.coordination_groups
            or any(item.scope_relation_ref == ref for item in graph.scope_relations)
            or any(item.delta_ref == ref for item in graph.state_deltas)
            or any(item.delta_ref == ref for item in graph.capability_deltas)
            or any(item.assessment_ref == ref for item in graph.impact_assessments)
            or any(item.assessment_ref == ref for item in graph.importance_assessments)
        )

    @staticmethod
    def _error(
        code: str, target: str, message: str, dependency: str | None = None
    ) -> UOLValidationIssue:
        return UOLValidationIssue(
            ValidationSeverity.ERROR, code, target, message, dependency
        )

    @staticmethod
    def _unresolved(
        code: str, target: str, message: str, dependency: str | None = None
    ) -> UOLValidationIssue:
        return UOLValidationIssue(
            ValidationSeverity.UNRESOLVED, code, target, message, dependency
        )
