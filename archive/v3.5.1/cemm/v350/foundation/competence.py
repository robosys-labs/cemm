"""Executable Phase-6 competence over a compiled immutable boot database."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..facets import ProjectionStatus, ReferentKnowledgeProjector, TypeClosureCompiler
from ..schema.model import (
    ActionSchema,
    DiscourseActSchema,
    EventSchema,
    FunctionSchema,
    MeasureDimensionSchema,
    RelationSchema,
    ResponsePolicySchema,
    RoleSchema,
    StateDimensionSchema,
    UnitSchema,
    UseOperation,
)
from ..storage import RecordKind, SemanticStore
from .runtime import resolve_runtime_component
from .model import (
    FoundationCompetenceCase,
    FoundationCompetenceReport,
    FoundationCompetenceResult,
)


def load_foundation_competence(path: str | Path) -> tuple[FoundationCompetenceCase, ...]:
    result: list[FoundationCompetenceCase] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        value = json.loads(raw)
        case = FoundationCompetenceCase(
            case_ref=str(value["case_ref"]),
            operation=str(value["operation"]),
            context_ref=str(value.get("context_ref", "actual")),
            expected=dict(value.get("expected", {})),
            subject_ref=None if value.get("subject_ref") is None else str(value["subject_ref"]),
            query=dict(value.get("query", {})),
            metadata=dict(value.get("metadata", {})),
        )
        if case.case_ref in seen:
            raise ValueError(f"duplicate competence case {case.case_ref}")
        seen.add(case.case_ref)
        result.append(case)
    return tuple(result)


class FoundationCompetenceRunner:
    def __init__(self, store: SemanticStore):
        self.store = store
        self.projector = ReferentKnowledgeProjector(store)
        self._view_cache: dict[tuple[str, str], Any] = {}

    def _view(self, subject_ref: str, context_ref: str):
        key = (subject_ref, context_ref)
        view = self._view_cache.get(key)
        if view is None:
            view = self.projector.project(subject_ref, context_ref=context_ref)
            self._view_cache[key] = view
        return view

    def run(self, cases: tuple[FoundationCompetenceCase, ...]) -> FoundationCompetenceReport:
        return FoundationCompetenceReport(tuple(self.run_case(item) for item in cases))

    def run_case(self, case: FoundationCompetenceCase) -> FoundationCompetenceResult:
        try:
            observed = self._observe(case)
            errors = tuple(_compare(case.expected, observed))
            return FoundationCompetenceResult(
                case.case_ref,
                case.operation,
                not errors,
                case.expected,
                observed,
                errors,
            )
        except Exception as exc:
            return FoundationCompetenceResult(
                case.case_ref,
                case.operation,
                False,
                case.expected,
                {},
                (f"{type(exc).__name__}:{exc}",),
            )

    def _observe(self, case: FoundationCompetenceCase) -> Mapping[str, Any]:
        operation = case.operation
        if operation == "type_closure":
            subject = _required(case.subject_ref, "subject_ref")
            with self.store.snapshot() as snapshot:
                closure = TypeClosureCompiler(self.store).compile(
                    subject,
                    context_ref=case.context_ref,
                    snapshot=snapshot,
                )
            return {"contains": sorted(closure.type_refs)}

        if operation == "state_projection":
            view = self._view(
                _required(case.subject_ref, "subject_ref"), case.context_ref
            )
            dimension_ref = str(case.query["dimension_ref"])
            revision = int(case.query.get("dimension_revision", 1))
            state = next(
                item for item in view.state_applicability
                if item.dimension_ref == dimension_ref and item.dimension_revision == revision
            )
            return {"status": state.status.value, "active_values": list(state.active_value_refs)}

        if operation == "entitlement_projection":
            view = self._view(
                _required(case.subject_ref, "subject_ref"), case.context_ref
            )
            entitlement = view.entitlement(str(case.query["facet_ref"]))
            return {"status": None if entitlement is None else entitlement.status.value}

        if operation == "default_non_materialization":
            subject = _required(case.subject_ref, "subject_ref")
            view = self._view(subject, case.context_ref)
            dimension_ref = str(case.query["dimension_ref"])
            revision = int(case.query.get("dimension_revision", 1))
            state = next(
                item for item in view.state_applicability
                if item.dimension_ref == dimension_ref and item.dimension_revision == revision
            )
            assignments = tuple(
                stored.payload
                for stored in self.store.repositories.state_assignments.all()
                if stored.payload.holder_ref == subject
                and stored.payload.dimension_ref == dimension_ref
                and stored.payload.context_ref in {"global", case.context_ref}
            )
            expected_value = state.default_expectations[0].value_ref if state.default_expectations else None
            return {
                "status": state.status.value,
                "active_assignment_count": len(assignments),
                "default_value_ref": expected_value,
            }

        if operation == "function_capability_distinction":
            view = self._view(
                _required(case.subject_ref, "subject_ref"), case.context_ref
            )
            function_ref = str(case.query["function_schema_ref"])
            action_ref = str(case.query["action_schema_ref"])
            function_present = any(item.schema_ref == function_ref for item in view.function_applications)
            capability = next(item for item in view.live_capabilities if item.action_schema_ref == action_ref)
            return {"function_present": function_present, "capability_status": capability.status.value}

        if operation == "record_absence":
            kind = RecordKind(str(case.query["record_kind"]))
            ref = str(case.query["record_ref"])
            return {"absent": self.store.get_record(kind, ref) is None}

        if operation == "schema_orthogonality":
            registry = self.store.repositories.schemas.registry()
            loss = registry.authoritative_schema(str(case.query["loss_event_ref"]))
            decrease = registry.authoritative_schema(str(case.query["decrease_event_ref"]))
            valence = registry.authoritative_schema(str(case.query["valence_dimension_ref"]))
            distinct = (
                loss.schema_ref != decrease.schema_ref
                and loss.schema_class.value == "event"
                and decrease.schema_class.value == "event"
                and valence.schema_class.value == "state_dimension"
                and loss.semantic_key == "lose"
                and decrease.semantic_key == "decrease"
                and valence.semantic_key == "valence"
            )
            return {"distinct": distinct}

        if operation == "schema_type_closure":
            registry = self.store.repositories.schemas.registry()
            closure = registry.type_closure(
                str(case.query["type_ref"]), int(case.query.get("revision", 1))
            )
            return {"contains": sorted(closure)}


        if operation == "schema_parent_closure":
            registry = self.store.repositories.schemas.registry()
            root = registry.schema(
                str(case.query["schema_ref"]), int(case.query.get("revision", 1))
            )
            complete: set[str] = set()
            stack = [root]
            while stack:
                schema = stack.pop()
                if schema.schema_ref in complete:
                    continue
                complete.add(schema.schema_ref)
                stack.extend(registry.resolve_parent(link) for link in schema.parent_links)
            return {"contains": sorted(complete)}

        if operation == "referent_view_field":
            view = self._view(
                _required(case.subject_ref, "subject_ref"), case.context_ref
            )
            field = str(case.query["field"])
            if field not in {
                "afforded_action_refs", "identity_facet_refs", "event_refs",
                "significance_assessment_refs", "epistemic_record_refs",
            }:
                raise ValueError(f"unsupported referent view competence field {field}")
            return {"contains": list(getattr(view, field))}

        if operation == "operator_families":
            registry = self.store.repositories.schemas.registry()
            families = {}
            for ref in map(str, case.query.get("schema_refs", ())):
                schema = registry.authoritative_schema(ref)
                families[ref] = str(getattr(schema, "operator_family", ""))
            return {"families": families}

        if operation == "entitlement_domain":
            view = self._view(
                _required(case.subject_ref, "subject_ref"), case.context_ref
            )
            entitlement = view.entitlement(str(case.query["facet_ref"]))
            return {
                "status": None if entitlement is None else entitlement.status.value,
                "contains": [] if entitlement is None else sorted(entitlement.value_domain_refs),
            }

        if operation == "state_dimension_contract":
            registry = self.store.repositories.schemas.registry()
            dimension = registry.authoritative_schema(str(case.query["dimension_ref"]))
            if not isinstance(dimension, StateDimensionSchema):
                raise TypeError(f"{dimension.schema_ref} is not a state dimension")
            value_keys = [
                registry.authoritative_schema(ref).semantic_key
                for ref in dimension.value_schema_refs
            ]
            return {
                "holder_types": sorted(dimension.holder_type_refs),
                "value_keys": sorted(value_keys),
                "exclusive": dimension.exclusive,
                "minimum": dimension.value_cardinality.minimum,
                "maximum": dimension.value_cardinality.maximum,
            }

        if operation == "measure_dimension_contract":
            registry = self.store.repositories.schemas.registry()
            measure = registry.authoritative_schema(str(case.query["measure_ref"]))
            if not isinstance(measure, MeasureDimensionSchema):
                raise TypeError(f"{measure.schema_ref} is not a measure dimension")
            unit = registry.authoritative_schema(str(measure.canonical_unit_ref))
            if not isinstance(unit, UnitSchema):
                raise TypeError(f"{unit.schema_ref} is not a unit")
            return {
                "quantity_types": sorted(measure.quantity_type_refs),
                "canonical_unit_ref": measure.canonical_unit_ref,
                "unit_measure_ref": unit.measure_dimension_ref,
                "ordered": measure.ordered,
            }

        if operation == "relation_inverse_contract":
            registry = self.store.repositories.schemas.registry()
            relation = registry.authoritative_schema(str(case.query["relation_ref"]))
            if not isinstance(relation, RelationSchema):
                raise TypeError(f"{relation.schema_ref} is not a relation")
            inverse = registry.authoritative_schema(str(relation.inverse_relation_ref))
            if not isinstance(inverse, RelationSchema):
                raise TypeError(f"{inverse.schema_ref} is not a relation")
            return {
                "inverse_ref": relation.inverse_relation_ref,
                "inverse_round_trip_ref": inverse.inverse_relation_ref,
                "relation_class": relation.schema_class.value,
            }

        if operation == "role_contract":
            registry = self.store.repositories.schemas.registry()
            role = registry.authoritative_schema(str(case.query["role_ref"]))
            if not isinstance(role, RoleSchema):
                raise TypeError(f"{role.schema_ref} is not a role")
            return {
                "holder_types": sorted(role.holder_type_refs),
                "context_types": sorted(role.context_type_refs),
                "minimum": role.occupancy_cardinality.minimum,
                "maximum": role.occupancy_cardinality.maximum,
                "occupancy_policy": role.occupancy_policy,
            }

        if operation == "discourse_response_contract":
            registry = self.store.repositories.schemas.registry()
            act = registry.authoritative_schema(str(case.query["discourse_act_ref"]))
            if not isinstance(act, DiscourseActSchema):
                raise TypeError(f"{act.schema_ref} is not a discourse act")
            content = act.port(str(act.content_port_ref))
            policies = [
                schema for schema in registry.iter_schemas()
                if isinstance(schema, ResponsePolicySchema)
                and schema.metadata.get("foundation_layer") == "phase6"
            ]
            return {
                "content_port_ref": act.content_port_ref,
                "content_minimum": content.cardinality.minimum,
                "policy_refs": sorted(item.schema_ref for item in policies),
                "literal_policy_refs": sorted(
                    item.schema_ref for item in policies if item.literal_realization_refs
                ),
            }

        if operation == "runtime_contract":
            action_ref = str(case.query["action_schema_ref"])
            capability_ref = str(case.query["capability_ref"])
            action = self.store.repositories.schemas.authoritative(action_ref)
            capability = self.store.repositories.capability_instances.require(capability_ref).payload
            component_ref = str(action.metadata.get("runtime_component") or "")
            component_resolves = False
            if component_ref:
                resolve_runtime_component(component_ref)
                component_resolves = True
            return {
                "action_execute_authorized": action.use_profile.permits(UseOperation.EXECUTE),
                "capability_status": capability.status.value,
                "runtime_component_resolves": component_resolves,
            }

        if operation == "movement_distinction":
            registry = self.store.repositories.schemas.registry()
            abstract = registry.authoritative_schema(str(case.query["abstract_action_ref"]))
            external = registry.authoritative_schema(str(case.query["external_action_ref"]))
            self_action = registry.authoritative_schema(str(case.query["self_action_ref"]))
            event = registry.authoritative_schema(str(case.query["event_ref"]))
            if not isinstance(abstract, ActionSchema):
                raise TypeError(f"{abstract.schema_ref} is not an action")
            if not isinstance(external, ActionSchema):
                raise TypeError(f"{external.schema_ref} is not an action")
            if not isinstance(self_action, ActionSchema):
                raise TypeError(f"{self_action.schema_ref} is not an action")
            if not isinstance(event, EventSchema):
                raise TypeError(f"{event.schema_ref} is not an event")
            external_port = external.port(str(external.controlling_port_ref))
            self_port = self_action.port(str(self_action.controlling_port_ref))
            return {
                "abstract_action_class": abstract.schema_class.value,
                "external_action_class": external.schema_class.value,
                "external_controlling_port": external.controlling_port_ref,
                "external_intentional_required": external.intentional_required,
                "external_holder_types": sorted(external_port.accepted_type_refs),
                "self_action_class": self_action.schema_class.value,
                "self_controlling_port": self_action.controlling_port_ref,
                "self_intentional_required": self_action.intentional_required,
                "self_holder_types": sorted(self_port.accepted_type_refs),
                "event_class": event.schema_class.value,
                "event_transition_authorized": event.use_profile.permits(UseOperation.TRANSITION),
                "all_distinct": len({
                    abstract.schema_ref, external.schema_ref, self_action.schema_ref, event.schema_ref
                }) == 4,
            }

        raise ValueError(f"unknown foundation competence operation {operation}")


def _compare(expected: Any, observed: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(expected, Mapping):
        if not isinstance(observed, Mapping):
            return [f"{path}:expected_mapping"]
        for key, value in expected.items():
            if key not in observed:
                errors.append(f"{path}.{key}:missing")
            else:
                errors.extend(_compare(value, observed[key], f"{path}.{key}"))
        return errors
    if isinstance(expected, list):
        if not isinstance(observed, (list, tuple)):
            return [f"{path}:expected_list"]
        actual = list(observed)
        if path.endswith(".contains"):
            missing = [item for item in expected if item not in actual]
            return [] if not missing else [f"{path}:missing={missing!r}:observed={actual!r}"]
        if expected != actual:
            return [f"{path}:expected={expected!r}:observed={actual!r}"]
        return errors
    if expected != observed:
        errors.append(f"{path}:expected={expected!r}:observed={observed!r}")
    return errors


def _required(value: str | None, label: str) -> str:
    if value is None:
        raise ValueError(f"{label} is required")
    return value
