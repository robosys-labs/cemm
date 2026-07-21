"""Phase-5 universal semantic query compiler and answer binder.

The binder operates on typed UOL gaps and durable semantic record families.  It
never inspects surface words and never turns defaults into facts. Broad query
projections close only through Stage-4 referent knowledge, not global schema
catalogue enumeration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .discourse import DiscourseClassification
from .facets.model import ReferentKnowledgeView
from .learning.model import PinnedRecord
from .schema.model import OpenBindingPurpose, PortFillerClass, SchemaClass, StorageKind, semantic_fingerprint
from .storage import SemanticStore, StoreSnapshot
from .storage.model import AssignmentStatus, KnowledgeStatus, RecordKind
from .uol.model import FillerRef, IdentityStatus, QuotedLiteral, Referent, SemanticApplication, UOLGraph


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class BoundValueKind(StrEnum):
    REFERENT = "referent"
    SCHEMA_TOPIC = "schema_topic"
    SEMANTIC_APPLICATION = "semantic_application"
    LITERAL = "literal"
    PROPOSITION = "proposition"
    EVENT = "event"


@dataclass(frozen=True, slots=True)
class QueryVariableRequest:
    variable_ref: str
    expected_filler_classes: tuple[PortFillerClass, ...]
    expected_schema_classes: tuple[SchemaClass, ...]
    expected_type_refs: tuple[str, ...]
    restriction_refs: tuple[str, ...]
    projection_ref: str | None
    projection_revision: int | None
    projection_candidates: tuple[tuple[str, int], ...]
    host_application_refs: tuple[str, ...]
    host_port_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.variable_ref.strip():
            raise ValueError("query variable_ref is required")
        if (self.projection_ref is None) != (self.projection_revision is None):
            raise ValueError("query projection ref/revision must be supplied together")
        if self.projection_revision is not None and self.projection_revision < 1:
            raise ValueError("query projection revision must be positive")
        if len(self.projection_candidates) != len(set(self.projection_candidates)):
            raise ValueError("query projection candidates must be unique")
        for ref, revision in self.projection_candidates:
            if not ref.strip() or revision < 1:
                raise ValueError("query projection candidate requires exact schema pin")


@dataclass(frozen=True, slots=True)
class SemanticQueryRequest:
    request_ref: str
    variables: tuple[QueryVariableRequest, ...]
    response_requested: bool
    discourse_act_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    evidence_refs: tuple[str, ...]

    @property
    def has_query(self) -> bool:
        return bool(self.variables)


@dataclass(frozen=True, slots=True)
class BoundSemanticValue:
    value_ref: str
    value_kind: BoundValueKind
    source_pin: PinnedRecord
    filler_class: PortFillerClass
    filler_ref: str
    schema_ref: str | None
    schema_revision: int | None
    projection_ref: str | None
    projection_revision: int | None
    evidence_refs: tuple[str, ...]
    qualification_refs: tuple[str, ...] = ()
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.value_ref.strip() or not self.filler_ref.strip():
            raise ValueError("bound semantic value requires non-empty identity")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("bound semantic value confidence must be within [0,1]")
        if (self.schema_ref is None) != (self.schema_revision is None):
            raise ValueError("bound semantic schema ref/revision must be paired")
        if (self.projection_ref is None) != (self.projection_revision is None):
            raise ValueError("bound semantic projection ref/revision must be paired")
        if self.schema_revision is not None and self.schema_revision < 1:
            raise ValueError("bound semantic schema revision must be positive")
        if self.projection_revision is not None and self.projection_revision < 1:
            raise ValueError("bound semantic projection revision must be positive")


@dataclass(frozen=True, slots=True)
class QueryVariableBinding:
    variable_ref: str
    values: tuple[BoundSemanticValue, ...]
    source_pins: tuple[PinnedRecord, ...]
    unresolved_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticQueryResult:
    result_ref: str
    request: SemanticQueryRequest
    bindings: tuple[QueryVariableBinding, ...]
    source_pins: tuple[PinnedRecord, ...]
    answer_graph: UOLGraph
    unresolved_query_refs: tuple[str, ...]
    qualification_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("semantic-query-result", self, 64)

    @property
    def bound_value_refs(self) -> tuple[str, ...]:
        return tuple(sorted({v.filler_ref for b in self.bindings for v in b.values}))


class SemanticQueryCompiler:
    """Compile information gaps independently of matrix discourse force."""

    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def compile(
        self,
        graph: UOLGraph,
        classification: DiscourseClassification | None,
        *,
        context_ref: str,
        permission_ref: str,
        snapshot: StoreSnapshot,
    ) -> SemanticQueryRequest:
        self.store.assert_snapshot(snapshot)
        hosts: dict[str, list[tuple[str, str]]] = {}
        for app in graph.applications.values():
            for binding in app.bindings:
                for filler in binding.fillers:
                    if isinstance(filler, FillerRef) and filler.filler_class == PortFillerClass.SEMANTIC_VARIABLE:
                        hosts.setdefault(filler.ref, []).append((app.application_ref, binding.port_ref))
        variables = []
        evidence = set(graph.evidence_refs)
        for variable in graph.variables.values():
            if variable.open_binding_purpose != OpenBindingPurpose.QUERY:
                continue
            pairs = tuple(sorted(set(hosts.get(variable.variable_ref, ()))))
            variables.append(QueryVariableRequest(
                variable_ref=variable.variable_ref,
                expected_filler_classes=tuple(sorted(variable.expected_filler_classes, key=lambda x: x.value)),
                expected_schema_classes=tuple(sorted(variable.expected_schema_classes, key=lambda x: x.value)),
                expected_type_refs=tuple(variable.expected_type_refs),
                restriction_refs=tuple(variable.restriction_refs),
                projection_ref=variable.projection_ref,
                projection_revision=variable.projection_revision,
                projection_candidates=tuple(variable.projection_candidates),
                host_application_refs=tuple(x[0] for x in pairs),
                host_port_refs=tuple(x[1] for x in pairs),
                evidence_refs=tuple(variable.evidence_refs),
            ))
            evidence.update(variable.evidence_refs)

        response_requested = False
        discourse_refs: list[str] = []
        if classification is not None:
            registry = self.store.repositories.schemas.registry(snapshot=snapshot)
            for app in classification.discourse_acts:
                discourse_refs.append(app.application_ref)
                try:
                    schema = registry.schema(app.schema_ref, app.schema_revision)
                except KeyError:
                    continue
                # This reviewed schema metadata is discourse-force authority. It is
                # deliberately separate from a query variable's lexical meaning.
                if bool(schema.metadata.get("requests_information")):
                    response_requested = True
        request_ref = "semantic-query-request:" + semantic_fingerprint(
            "semantic-query-request",
            (graph.record_fingerprint, tuple(v.variable_ref for v in variables), response_requested, tuple(sorted(discourse_refs))),
            24,
        )
        return SemanticQueryRequest(
            request_ref=request_ref,
            variables=tuple(sorted(variables, key=lambda x: x.variable_ref)),
            response_requested=response_requested,
            discourse_act_refs=tuple(sorted(discourse_refs)),
            context_ref=context_ref,
            permission_ref=permission_ref,
            evidence_refs=tuple(sorted(evidence)) or (request_ref,),
        )


class UniversalSemanticBinder:
    """Bind typed query gaps across normalized semantic record families."""

    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def bind(
        self,
        graph: UOLGraph,
        *,
        classification: DiscourseClassification | None,
        context_ref: str,
        permission_ref: str,
        referent_projections: Mapping[str, ReferentKnowledgeView] | None = None,
        snapshot: StoreSnapshot | None = None,
    ) -> SemanticQueryResult:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.bind(
                    graph,
                    classification=classification,
                    context_ref=context_ref,
                    permission_ref=permission_ref,
                    referent_projections=referent_projections,
                    snapshot=pinned,
                )
        self.store.assert_snapshot(snapshot)
        views = {} if referent_projections is None else dict(referent_projections)
        request = SemanticQueryCompiler(self.store).compile(
            graph, classification, context_ref=context_ref,
            permission_ref=permission_ref, snapshot=snapshot,
        )
        bindings: list[QueryVariableBinding] = []
        pins: dict[tuple, PinnedRecord] = {}
        unresolved: set[str] = set()
        qualifications: set[str] = set()
        evidence = set(request.evidence_refs)

        for req in request.variables:
            values: list[BoundSemanticValue] = []
            restriction_refs = self._restriction_referents(graph, req)
            host_apps = tuple(graph.applications[r] for r in req.host_application_refs if r in graph.applications)

            # Exact host application query, e.g. property:name(holder=self,value=?x).
            # A reviewed host schema may also declare a structural storage adapter
            # (identity facets, type assertions, states, capabilities, ...).
            registry = self.store.repositories.schemas.registry(snapshot=snapshot)
            for host in host_apps:
                try:
                    host_schema = registry.schema(host.schema_ref, host.schema_revision)
                except KeyError:
                    host_schema = None
                if host_schema is not None and host_schema.metadata.get("query_adapter_kind"):
                    values.extend(self._projected_values(
                        host_schema, restriction_refs, context_ref=context_ref,
                        views=views, snapshot=snapshot,
                    ))
                else:
                    values.extend(self._application_values(
                        host, req, context_ref=context_ref, snapshot=snapshot
                    ))

            # Exact/N-best projection semantics remain explicit exact pins.
            projection_pins = (
                ((req.projection_ref, req.projection_revision),)
                if req.projection_ref is not None
                else tuple(req.projection_candidates)
            )
            if projection_pins:
                registry = self.store.repositories.schemas.registry(snapshot=snapshot)
                for projection_ref, projection_revision in projection_pins:
                    schema = registry.schema(projection_ref, projection_revision)
                    values.extend(self._projected_values(
                        schema, restriction_refs, context_ref=context_ref,
                        views=views, snapshot=snapshot,
                    ))
            else:
                # Broad variables close from grounded Stage-4 knowledge only.
                values.extend(self._view_values(
                    req, restriction_refs, context_ref=context_ref, views=views, snapshot=snapshot
                ))

            values = list(self._dedupe(v for v in values if self._compatible(v, req, snapshot, views, context_ref, permission_ref)))
            local_unresolved = () if values else (req.variable_ref,)
            unresolved.update(local_unresolved)
            local_pins = {v.source_pin.key: v.source_pin for v in values}
            for value in values:
                pins[value.source_pin.key] = value.source_pin
                qualifications.update(value.qualification_refs)
                evidence.update(value.evidence_refs)
            bindings.append(QueryVariableBinding(
                variable_ref=req.variable_ref,
                values=tuple(values),
                source_pins=tuple(sorted(local_pins.values(), key=lambda p: p.key)),
                unresolved_refs=local_unresolved,
                evidence_refs=tuple(sorted(set(req.evidence_refs) | {r for v in values for r in v.evidence_refs})) or req.evidence_refs,
            ))

        answer_graph = self._answer_graph(graph, request, tuple(bindings), context_ref=context_ref, permission_ref=permission_ref, snapshot=snapshot)
        result_ref = "semantic-query-result:" + semantic_fingerprint(
            "semantic-query-result-ref",
            (request.request_ref, tuple((b.variable_ref, tuple(v.value_ref for v in b.values)) for b in bindings), tuple(sorted(unresolved))),
            24,
        )
        return SemanticQueryResult(
            result_ref=result_ref,
            request=request,
            bindings=tuple(bindings),
            source_pins=tuple(sorted(pins.values(), key=lambda p: p.key)),
            answer_graph=answer_graph,
            unresolved_query_refs=tuple(sorted(unresolved)),
            qualification_refs=tuple(sorted(qualifications)),
            evidence_refs=tuple(sorted(evidence)) or (result_ref,),
            context_ref=context_ref,
            permission_ref=permission_ref,
        )

    def _application_values(self, query: SemanticApplication, req: QueryVariableRequest, *, context_ref: str, snapshot: StoreSnapshot):
        variable_ports = {
            b.port_ref for b in query.bindings
            if any(isinstance(f, FillerRef) and f.filler_class == PortFillerClass.SEMANTIC_VARIABLE and f.ref == req.variable_ref for f in b.fillers)
        }
        if not variable_ports:
            return ()
        fixed = {
            b.port_ref: self._filler_keys(b)
            for b in query.bindings if b.port_ref not in variable_ports
        }
        result = []
        for stored in self.store.repositories.applications.all(snapshot=snapshot):
            app = stored.payload
            if app.schema_ref != query.schema_ref or app.schema_revision != query.schema_revision:
                continue
            if app.context_ref not in {context_ref, "global"}:
                continue
            by_port = {b.port_ref: b for b in app.bindings}
            if any(self._filler_keys(by_port.get(port)) != expected for port, expected in fixed.items()):
                continue
            for port in variable_ports:
                binding = by_port.get(port)
                if binding is None:
                    continue
                for filler in binding.fillers:
                    if isinstance(filler, FillerRef):
                        filler_schema_ref = None
                        filler_schema_revision = None
                        if filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                            nested = self.store.get_record(RecordKind.SEMANTIC_APPLICATION, filler.ref, snapshot=snapshot)
                            if nested is not None:
                                filler_schema_ref = nested.payload.schema_ref
                                filler_schema_revision = nested.payload.schema_revision
                        result.append(BoundSemanticValue(
                            value_ref=f"bound:{filler.filler_class.value}:{filler.ref}",
                            value_kind=BoundValueKind.SEMANTIC_APPLICATION if filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION else BoundValueKind.REFERENT,
                            source_pin=self._pin(stored), filler_class=filler.filler_class,
                            filler_ref=filler.ref, schema_ref=filler_schema_ref, schema_revision=filler_schema_revision,
                            projection_ref=query.schema_ref, projection_revision=query.schema_revision,
                            evidence_refs=app.evidence_refs or (stored.record_ref,), confidence=app.confidence,
                        ))
                    elif isinstance(filler, QuotedLiteral):
                        literal_ref="query-literal:" + semantic_fingerprint(
                            "query-application-literal", (stored.record_ref, port, filler.literal_ref), 20
                        )
                        result.append(BoundSemanticValue(
                            value_ref=literal_ref, value_kind=BoundValueKind.LITERAL,
                            source_pin=self._pin(stored), filler_class=PortFillerClass.QUOTED_LITERAL,
                            filler_ref=literal_ref, schema_ref=None, schema_revision=None,
                            projection_ref=query.schema_ref, projection_revision=query.schema_revision,
                            evidence_refs=filler.evidence_refs or app.evidence_refs or (stored.record_ref,),
                            confidence=app.confidence,
                            metadata={"literal_surface": filler.surface, "language_tag": filler.language_tag},
                        ))
        return tuple(result)

    def _projected_values(self, schema, holders, *, context_ref, views, snapshot):
        adapter = str(schema.metadata.get("query_adapter_kind", ""))
        if adapter == "identity_facet":
            # IdentityFacetRecord uses a broad facet schema in the current model.
            # A semantic property may bridge to it only with an explicit reviewed
            # selector; never infer name/identifier from strings.
            selector = str(schema.metadata.get("identity_facet_selector_ref", ""))
            if not selector:
                return ()
            return self._identity_values(holders, context_ref=context_ref, snapshot=snapshot, projection=schema, selector_ref=selector)
        if adapter == "type_assertion":
            return self._type_values(holders, context_ref=context_ref, snapshot=snapshot, projection=schema)
        if adapter == "state_assignment" or schema.schema_class == SchemaClass.STATE_DIMENSION:
            return self._state_values(schema.schema_ref, schema.revision, holders, context_ref=context_ref, views=views, snapshot=snapshot)
        if adapter == "capability_instance":
            return self._capability_values(schema.schema_ref if schema.schema_class == SchemaClass.ACTION else None, schema.revision if schema.schema_class == SchemaClass.ACTION else None, holders, context_ref=context_ref, snapshot=snapshot)
        if adapter == "event_occurrence":
            return self._event_values(schema.schema_ref, schema.revision, context_ref=context_ref, snapshot=snapshot)
        if adapter == "knowledge":
            return self._knowledge_values(context_ref=context_ref, snapshot=snapshot, projection=schema)
        if adapter == "referent":
            return self._referent_values(holders, context_ref=context_ref, snapshot=snapshot, projection=schema)
        # Property/relation/role/function values are normally represented as
        # SemanticApplication bindings and are answered by exact host matching.
        return ()

    def _view_values(self, req, holders, *, context_ref, views, snapshot):
        result = []
        # An open ACTION variable is not automatically a capability query.
        # Capability binding requires an explicit reviewed query adapter/restriction;
        # otherwise "what did X do" and "what can X do" would collapse.
        for holder in holders:
            view = views.get(holder)
            if view is None:
                continue
            if not req.expected_schema_classes or SchemaClass.STATE_DIMENSION in req.expected_schema_classes:
                for state in view.state_applicability:
                    result.extend(self._state_values(
                        state.dimension_ref, state.dimension_revision, (holder,),
                        context_ref=context_ref, views=views, snapshot=snapshot,
                    ))
            for app in (*view.property_applications, *view.relation_applications, *view.role_applications, *view.function_applications, *view.resource_applications):
                try:
                    schema = self.store.repositories.schemas.registry(snapshot=snapshot).schema(app.schema_ref, app.schema_revision)
                except KeyError:
                    continue
                if req.expected_schema_classes and schema.schema_class not in req.expected_schema_classes:
                    continue
                stored = self.store.get_record(RecordKind.SEMANTIC_APPLICATION, app.application_ref, snapshot=snapshot)
                if stored is None:
                    continue
                result.append(BoundSemanticValue(
                    value_ref=f"bound-application:{app.application_ref}", value_kind=BoundValueKind.SEMANTIC_APPLICATION,
                    source_pin=self._pin(stored), filler_class=PortFillerClass.SEMANTIC_APPLICATION,
                    filler_ref=app.application_ref, schema_ref=app.schema_ref, schema_revision=app.schema_revision,
                    projection_ref=app.schema_ref, projection_revision=app.schema_revision,
                    evidence_refs=app.evidence_refs or (app.application_ref,), confidence=app.confidence,
                ))
        return tuple(result)

    def _state_values(self, dimension_ref, dimension_revision, holders, *, context_ref, views, snapshot):
        result = []
        for stored in self.store.repositories.state_assignments.all(snapshot=snapshot):
            state = stored.payload
            if state.dimension_ref != dimension_ref or state.dimension_revision != dimension_revision:
                continue
            if holders and state.holder_ref not in holders:
                continue
            if state.context_ref not in {context_ref, "global"} or state.status != AssignmentStatus.ACTIVE:
                continue
            result.append(self._schema_topic(
                state.value_ref, state.value_revision, stored,
                projection_ref=dimension_ref, projection_revision=dimension_revision,
                qualifications=("active_state",), confidence=state.confidence,
            ))
        if result:
            return tuple(result)
        # Defaults remain explicitly qualified expectations, never facts.
        for holder in holders:
            view = views.get(holder)
            if view is None:
                continue
            match = next((s for s in view.state_applicability if s.dimension_ref == dimension_ref and s.dimension_revision == dimension_revision), None)
            if match is None:
                continue
            for expectation in match.default_expectations:
                if expectation.value_ref is None or expectation.value_revision is None:
                    continue
                stored = self.store.get_record(RecordKind.DEFAULT_RULE, expectation.rule_ref, expectation.rule_revision, snapshot=snapshot)
                if stored is None:
                    continue
                result.append(self._schema_topic(
                    expectation.value_ref, expectation.value_revision, stored,
                    projection_ref=dimension_ref, projection_revision=dimension_revision,
                    qualifications=("default_expected", expectation.expectation_ref), confidence=expectation.confidence,
                ))
        return tuple(result)

    def _capability_values(self, action_ref, action_revision, holders, *, context_ref, snapshot):
        result = []
        for stored in self.store.repositories.capability_instances.all(snapshot=snapshot):
            cap = stored.payload
            if holders and cap.holder_ref not in holders:
                continue
            if action_ref is not None and (cap.action_schema_ref != action_ref or cap.action_schema_revision != action_revision):
                continue
            if cap.context_ref not in {context_ref, "global"}:
                continue
            if cap.status.value in {"unavailable", "terminated", "unknown"}:
                continue
            result.append(self._schema_topic(
                cap.action_schema_ref, cap.action_schema_revision, stored,
                projection_ref=action_ref, projection_revision=action_revision,
                qualifications=(f"capability_status:{cap.status.value}",), confidence=cap.confidence,
            ))
        return tuple(result)

    def _type_values(self, holders, *, context_ref, snapshot, projection=None):
        result = []
        for stored in self.store.repositories.type_assertions.all(snapshot=snapshot):
            item = stored.payload
            if holders and item.referent_ref not in holders:
                continue
            if item.context_ref not in {context_ref, "global"}:
                continue
            if item.status.value not in {"supported", "active"}:
                continue
            result.append(self._schema_topic(
                item.type_schema_ref, item.type_revision, stored,
                projection_ref=None if projection is None else projection.schema_ref,
                projection_revision=None if projection is None else projection.revision,
                qualifications=("type_assertion",), confidence=item.confidence,
            ))
        return tuple(result)

    def _identity_values(self, holders, *, context_ref, snapshot, projection, selector_ref):
        result = []
        for stored in self.store.repositories.identity_facets.all(snapshot=snapshot):
            item = stored.payload
            if holders and item.referent_ref not in holders:
                continue
            if item.context_ref not in {context_ref, "global"}:
                continue
            if item.facet_schema_ref != selector_ref and item.identity_facet_ref != selector_ref:
                continue
            literal_ref = "query-literal:" + semantic_fingerprint(
                "query-identity-literal", (item.identity_facet_ref, item.normalized_value), 20
            )
            result.append(BoundSemanticValue(
                value_ref=literal_ref, value_kind=BoundValueKind.LITERAL,
                source_pin=self._pin(stored), filler_class=PortFillerClass.QUOTED_LITERAL,
                filler_ref=literal_ref, schema_ref=None, schema_revision=None,
                projection_ref=projection.schema_ref, projection_revision=projection.revision,
                evidence_refs=item.evidence_refs or (stored.record_ref,),
                qualification_refs=("identity_facet",), confidence=item.confidence,
                metadata={"literal_surface": item.normalized_value, "language_tag": "und"},
            ))
        return tuple(result)

    def _event_values(self, schema_ref, schema_revision, *, context_ref, snapshot):
        result = []
        for stored in self.store.repositories.event_occurrences.all(snapshot=snapshot):
            item = stored.payload
            if item.event_schema_ref != schema_ref or item.event_schema_revision != schema_revision:
                continue
            if item.context_ref not in {context_ref, "global"}:
                continue
            result.append(BoundSemanticValue(
                value_ref=f"bound-event:{item.event_ref}", value_kind=BoundValueKind.EVENT,
                source_pin=self._pin(stored), filler_class=PortFillerClass.REFERENT,
                filler_ref=item.event_ref, schema_ref=item.event_schema_ref, schema_revision=item.event_schema_revision,
                projection_ref=schema_ref, projection_revision=schema_revision,
                evidence_refs=item.provenance_refs or item.referent.provenance_refs or (stored.record_ref,),
                qualification_refs=(f"occurrence_status:{item.occurrence_status.value}",), confidence=1.0,
            ))
        return tuple(result)

    def _knowledge_values(self, *, context_ref, snapshot, projection):
        result = []
        for stored in self.store.repositories.knowledge.all(snapshot=snapshot):
            item = stored.payload
            if item.context_ref not in {context_ref, "global"}:
                continue
            if item.truth_status not in {KnowledgeStatus.SUPPORTED, KnowledgeStatus.BOTH}:
                continue
            result.append(BoundSemanticValue(
                value_ref=f"bound-proposition:{item.proposition_ref}", value_kind=BoundValueKind.PROPOSITION,
                source_pin=self._pin(stored), filler_class=PortFillerClass.REFERENT,
                filler_ref=item.proposition_ref, schema_ref=None, schema_revision=None,
                projection_ref=projection.schema_ref, projection_revision=projection.revision,
                evidence_refs=item.evidence_refs or (stored.record_ref,),
                qualification_refs=(f"truth_status:{item.truth_status.value}",), confidence=item.confidence,
            ))
        return tuple(result)

    def _referent_values(self, holders, *, context_ref, snapshot, projection):
        result = []
        for stored in self.store.repositories.referents.all(snapshot=snapshot):
            item = stored.payload
            if holders and item.referent_ref not in holders:
                continue
            if item.context_refs and context_ref not in item.context_refs and "global" not in item.context_refs:
                continue
            result.append(BoundSemanticValue(
                value_ref=f"bound-referent:{item.referent_ref}", value_kind=BoundValueKind.REFERENT,
                source_pin=self._pin(stored), filler_class=PortFillerClass.REFERENT,
                filler_ref=item.referent_ref, schema_ref=None, schema_revision=None,
                projection_ref=projection.schema_ref, projection_revision=projection.revision,
                evidence_refs=item.provenance_refs or (stored.record_ref,), confidence=1.0,
            ))
        return tuple(result)

    def _schema_topic(self, schema_ref, schema_revision, stored, *, projection_ref, projection_revision, qualifications, confidence):
        return BoundSemanticValue(
            value_ref="bound-schema:" + semantic_fingerprint("bound-schema", (schema_ref, schema_revision, stored.record_kind.value, stored.record_ref, stored.revision), 20),
            value_kind=BoundValueKind.SCHEMA_TOPIC,
            source_pin=self._pin(stored), filler_class=PortFillerClass.REFERENT,
            filler_ref="schema-topic:" + semantic_fingerprint("schema-topic-referent", (schema_ref, schema_revision), 20),
            schema_ref=schema_ref, schema_revision=schema_revision,
            projection_ref=projection_ref, projection_revision=projection_revision,
            evidence_refs=tuple(getattr(stored.payload, "evidence_refs", ())) or (stored.record_ref,),
            qualification_refs=tuple(qualifications), confidence=confidence,
            metadata={"schema_topic_ref": schema_ref, "schema_topic_revision": schema_revision},
        )

    def _restriction_referents(self, graph, req):
        result = {r for r in req.restriction_refs if r in graph.referents}
        for ref in (*req.restriction_refs, *req.host_application_refs):
            app = graph.applications.get(ref)
            if app is None:
                continue
            for binding in app.bindings:
                for filler in binding.fillers:
                    if isinstance(filler, FillerRef) and filler.filler_class == PortFillerClass.REFERENT:
                        result.add(filler.ref)
        return tuple(sorted(result))

    def _answer_graph(self, source_graph, request, bindings, *, context_ref, permission_ref, snapshot):
        referents: dict[str, Referent] = {}
        applications: dict[str, SemanticApplication] = {}
        variables = {}
        roots: list[FillerRef] = []
        evidence = set(request.evidence_refs)
        unresolved = {r for b in bindings for r in b.unresolved_refs}
        for binding in bindings:
            for value in binding.values:
                evidence.update(value.evidence_refs)
                if value.value_kind == BoundValueKind.SEMANTIC_APPLICATION:
                    stored = self.store.get_record(RecordKind.SEMANTIC_APPLICATION, value.filler_ref, snapshot=snapshot)
                    if stored is not None:
                        applications[value.filler_ref] = stored.payload
                        roots.append(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, value.filler_ref))
                    continue
                if value.value_kind == BoundValueKind.EVENT:
                    event_stored = self.store.get_record(
                        value.source_pin.record_kind, value.source_pin.record_ref,
                        value.source_pin.revision, snapshot=snapshot,
                    )
                    participant_ref = None if event_stored is None else getattr(
                        event_stored.payload, "participant_application_ref", None
                    )
                    app_stored = None if not participant_ref else self.store.get_record(
                        RecordKind.SEMANTIC_APPLICATION, participant_ref, snapshot=snapshot
                    )
                    if app_stored is not None:
                        applications[participant_ref] = app_stored.payload
                        roots.append(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, participant_ref))
                        continue
                stored = self.store.get_record(RecordKind.REFERENT, value.filler_ref, snapshot=snapshot)
                if stored is not None:
                    referent = stored.payload
                else:
                    referent = Referent(
                        referent_ref=value.filler_ref,
                        storage_kind=(
                            StorageKind.SCHEMA_TOPIC if value.value_kind == BoundValueKind.SCHEMA_TOPIC
                            else StorageKind.EVENT_OCCURRENCE if value.value_kind == BoundValueKind.EVENT
                            else StorageKind.PROPOSITION if value.value_kind == BoundValueKind.PROPOSITION
                            else StorageKind.ORDINARY
                        ),
                        identity_status=IdentityStatus.RESOLVED,
                        type_refs=(),
                        scope_ref="query-answer", context_refs=(context_ref,),
                        provenance_refs=value.evidence_refs, permission_ref=permission_ref,
                        metadata={
                            **dict(value.metadata),
                            "query_bound_value_kind": value.value_kind.value,
                            "schema_ref": value.schema_ref,
                            "schema_revision": value.schema_revision,
                            "qualification_refs": value.qualification_refs,
                            "source_record_kind": value.source_pin.record_kind.value,
                            "source_record_ref": value.source_pin.record_ref,
                            "source_revision": value.source_pin.revision,
                            "source_fingerprint": value.source_pin.record_fingerprint,
                        },
                    )
                referents[referent.referent_ref] = referent
                roots.append(FillerRef(PortFillerClass.REFERENT, referent.referent_ref))
        for ref in sorted(unresolved):
            variable = source_graph.variables.get(ref)
            if variable is not None:
                variables[ref] = variable
                roots.append(FillerRef(PortFillerClass.SEMANTIC_VARIABLE, ref))
        unique = {(r.filler_class.value, r.ref): r for r in roots}
        return UOLGraph(
            graph_ref="query-answer-graph:" + semantic_fingerprint("query-answer-graph", (request.request_ref, tuple(sorted(unique)), tuple(sorted(unresolved))), 24),
            referents=referents, applications=applications, variables=variables,
            root_refs=tuple(unique[k] for k in sorted(unique)),
            unresolved_refs=tuple(sorted(unresolved)), evidence_refs=tuple(sorted(evidence)) or (request.request_ref,),
        )

    def _compatible(self, value, req, snapshot, views, context_ref, permission_ref):
        stored = self.store.get_record(
            value.source_pin.record_kind,
            value.source_pin.record_ref,
            value.source_pin.revision,
            snapshot=snapshot,
        )
        if stored is None or stored.record_fingerprint != value.source_pin.record_fingerprint:
            return False
        source_permission = stored.permission_ref or getattr(stored.payload, "permission_ref", None)
        if source_permission not in {None, "public", permission_ref}:
            return False
        if req.expected_filler_classes and value.filler_class not in req.expected_filler_classes:
            # Schema topics and proof-backed literal values are referent-shaped
            # answer nodes in cycle-local Response UOL.
            if not (
                value.value_kind in {BoundValueKind.SCHEMA_TOPIC, BoundValueKind.LITERAL}
                and PortFillerClass.REFERENT in req.expected_filler_classes
            ):
                return False
        if req.expected_schema_classes:
            semantic_ref = value.projection_ref or value.schema_ref
            semantic_revision = value.projection_revision or value.schema_revision
            if semantic_ref and semantic_revision is not None:
                try:
                    schema = self.store.repositories.schemas.registry(snapshot=snapshot).schema(
                        semantic_ref, semantic_revision
                    )
                except KeyError:
                    return False
                if schema.schema_class not in req.expected_schema_classes:
                    return False
        if req.expected_type_refs and value.value_kind == BoundValueKind.REFERENT:
            available = self._referent_type_refs(value.filler_ref, views, context_ref, snapshot)
            if not set(req.expected_type_refs).intersection(available):
                return False
        return True

    def _referent_type_refs(self, referent_ref, views, context_ref, snapshot):
        view = views.get(referent_ref)
        if view is not None:
            return set(view.type_closure.type_refs)
        result = set()
        stored = self.store.get_record(RecordKind.REFERENT, referent_ref, snapshot=snapshot)
        if stored is not None:
            result.update(getattr(stored.payload, "type_refs", ()))
        for assertion in self.store.repositories.type_assertions.all(snapshot=snapshot):
            item = assertion.payload
            if item.referent_ref != referent_ref or item.context_ref not in {context_ref, "global"}:
                continue
            if getattr(item.status, "value", "") in {"supported", "active"}:
                result.add(item.type_schema_ref)
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        closure = set(result)
        for type_ref in tuple(result):
            try:
                closure.update(registry.type_closure(type_ref))
            except (KeyError, TypeError):
                continue
        return closure

    @staticmethod
    def _filler_keys(binding):
        if binding is None:
            return ()
        return tuple(
            (f.filler_class.value, f.ref)
            if isinstance(f, FillerRef)
            else (PortFillerClass.QUOTED_LITERAL.value, f.literal_ref, f.surface, f.language_tag)
            for f in binding.fillers
        )

    @staticmethod
    def _pin(stored):
        return PinnedRecord(stored.record_kind, stored.record_ref, stored.revision, stored.record_fingerprint)

    @staticmethod
    def _dedupe(values: Iterable[BoundSemanticValue]):
        selected = {}
        for value in values:
            key = (value.value_kind.value, value.filler_ref, value.schema_ref, value.schema_revision, value.projection_ref, value.projection_revision, value.qualification_refs)
            previous = selected.get(key)
            if previous is None or value.confidence > previous.confidence:
                selected[key] = value
        return tuple(sorted(selected.values(), key=lambda v: (-v.confidence, v.value_kind.value, v.filler_ref)))
