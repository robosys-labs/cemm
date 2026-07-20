"""Materialize a solved Phase-9 hypothesis into cycle-local UOL.

Materialization is deliberately non-durable.  It may create provisional
cycle-local referents and semantic variables, but never KnowledgeRecord,
StateDelta, CapabilityDelta, transition proof, or actual-world admission.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Mapping

from ..grounding.model import GroundingCandidate, GroundingResult
from ..language.model import ConstructionKind, FormLattice, SenseTargetKind
from ..schema.model import (
    OpenBindingPurpose,
    PortFillerClass,
    SchemaClass,
    StorageKind,
    UseOperation,
    semantic_fingerprint,
)
from ..storage import SemanticStore, StoreSnapshot
from ..uol.model import (
    ApplicationBinding,
    CoordinationGroup,
    CoordinationKind,
    EventOccurrence,
    FillerRef,
    IdentityStatus,
    OccurrenceStatus,
    Referent,
    ScopeKind,
    ScopeRelation,
    SemanticApplication,
    SemanticVariable,
    UOLGraph,
)
from ..uol.validator import UOLValidationReport, UOLValidator
from .model import MeaningFactorGraph, MeaningHypothesis, MeaningVariableKind

_INACTIVE = "choice:inactive"
_UNRESOLVED = "choice:unresolved"
_OMITTED = "choice:omitted"
_GAP = "choice:gap"


class UOLMaterializationError(ValueError):
    pass


class UOLHypothesisMaterializer:
    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def materialize(
        self,
        factor_graph: MeaningFactorGraph,
        hypothesis: MeaningHypothesis,
        lattice: FormLattice,
        grounding: GroundingResult,
        *,
        context_ref: str,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[UOLGraph, UOLValidationReport]:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.materialize(
                    factor_graph, hypothesis, lattice, grounding,
                    context_ref=context_ref, snapshot=pinned,
                )
        self.store.assert_snapshot(snapshot)
        if factor_graph.snapshot_fingerprint != snapshot.fingerprint:
            raise UOLMaterializationError("factor graph snapshot is stale")
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        language = self.store.repositories.language.registry(snapshot=snapshot)
        assignments = hypothesis.assignment_map
        variable_by_ref = {item.variable_ref: item for item in factor_graph.variables}
        value_by_assignment = {
            var_ref: next(
                value for value in variable_by_ref[var_ref].values
                if value.value_ref == value_ref
            )
            for var_ref, value_ref in assignments.items()
        }
        candidate_by_ref = {item.candidate_ref: item for item in grounding.candidates}

        referents: dict[str, Referent] = {}
        selected_candidate_by_mention: dict[str, GroundingCandidate] = {}
        for variable in factor_graph.variables:
            if variable.variable_kind != MeaningVariableKind.REFERENT:
                continue
            chosen = value_by_assignment.get(variable.variable_ref)
            if chosen is None:
                continue
            candidate = candidate_by_ref.get(chosen.value_ref)
            if candidate is None:
                continue
            selected_candidate_by_mention[candidate.mention_ref] = candidate
            referent = self._cycle_referent(candidate, snapshot=snapshot)
            referents.setdefault(referent.referent_ref, referent)

        selected_senses = {}
        for variable in factor_graph.variables:
            if variable.variable_kind != MeaningVariableKind.SENSE:
                continue
            chosen = value_by_assignment.get(variable.variable_ref)
            if chosen is not None:
                selected_senses[chosen.value_ref] = chosen

        selected_schema_by_sense = {}
        for variable in factor_graph.variables:
            if variable.variable_kind != MeaningVariableKind.SCHEMA:
                continue
            chosen = value_by_assignment.get(variable.variable_ref)
            if chosen is None:
                continue
            sense_candidate_ref = str(chosen.metadata.get("sense_candidate_ref") or "")
            if sense_candidate_ref:
                selected_schema_by_sense[sense_candidate_ref] = chosen

        selected_constructions = {}
        for variable in factor_graph.variables:
            if variable.variable_kind != MeaningVariableKind.CONSTRUCTION:
                continue
            chosen = value_by_assignment.get(variable.variable_ref)
            if chosen is not None and chosen.value_ref != _INACTIVE:
                candidate_ref = str(variable.metadata.get("construction_candidate_ref"))
                selected_constructions[candidate_ref] = chosen

        selected_port_values: dict[tuple[str, str], object] = {}
        for variable in factor_graph.variables:
            if variable.variable_kind != MeaningVariableKind.PORT_FILLER:
                continue
            chosen = value_by_assignment.get(variable.variable_ref)
            if chosen is None or chosen.value_ref == _INACTIVE:
                continue
            selected_port_values[(
                str(variable.metadata.get("construction_candidate_ref")),
                str(variable.metadata.get("port_ref")),
            )] = (variable, chosen)

        applications: dict[str, SemanticApplication] = {}
        variables: dict[str, SemanticVariable] = {}
        events: dict[str, EventOccurrence] = {}
        coordination: dict[str, CoordinationGroup] = {}
        scopes: list[ScopeRelation] = []
        roots: list[FillerRef] = []
        unresolved = set(hypothesis.unresolved_refs)
        evidence = set(factor_graph.evidence_refs)
        app_ref_by_sense: dict[str, str] = {}
        covered_senses: set[str] = set()

        # Preserve targetless/partial lexical meaning as typed UOL variables.
        # Contributions are semantic constraints, not hidden intent labels.
        sense_candidate_by_ref = {item.candidate_ref: item for item in lattice.sense_candidates}
        for sense_candidate_ref in sorted(selected_senses):
            source_sense = sense_candidate_by_ref.get(sense_candidate_ref)
            if source_sense is None:
                unresolved.add(sense_candidate_ref)
                continue
            contributions = tuple(getattr(source_sense, "contributions", ()))
            projection_refs = tuple(sorted({
                item.projection_ref for item in contributions
                if item.contribution_kind.value == "projection" and item.projection_ref
            }))
            restriction_refs = tuple(sorted({
                ref for item in contributions for ref in item.restriction_refs
            }))
            for contribution in contributions:
                if contribution.contribution_kind.value != "variable":
                    continue
                variable_ref = "semantic-variable:" + semantic_fingerprint(
                    "lexical-contribution-variable",
                    (hypothesis.hypothesis_ref, contribution.contribution_ref),
                    24,
                )
                projection_ref = contribution.projection_ref
                if projection_ref is None and len(projection_refs) == 1:
                    projection_ref = projection_refs[0]
                if projection_ref is None and len(projection_refs) > 1:
                    unresolved.update(projection_refs)
                variables[variable_ref] = SemanticVariable(
                    variable_ref=variable_ref,
                    expected_schema_classes=frozenset(contribution.expected_schema_classes),
                    expected_type_refs=tuple(contribution.expected_type_refs),
                    restriction_refs=tuple(sorted(set((*restriction_refs, *contribution.restriction_refs)))),
                    projection_ref=projection_ref,
                    scope_ref="local",
                    evidence_refs=contribution.evidence_refs or source_sense.evidence_refs,
                    expected_filler_classes=frozenset(contribution.expected_filler_classes),
                    open_binding_purpose=contribution.open_binding_purpose,
                )
                unresolved.add(variable_ref)

        # Active reviewed constructions with semantic output become the primary
        # clause applications.  Their exact ports are filled from the joint
        # referent choices; gaps remain explicit SemanticVariables.
        construction_candidates = {
            item.candidate_ref: item for item in lattice.construction_candidates
        }
        for candidate_ref in sorted(selected_constructions):
            candidate = construction_candidates.get(candidate_ref)
            if candidate is None:
                unresolved.add(candidate_ref)
                continue
            construction_record = language.require_construction(
                candidate.construction_ref, candidate.construction_revision
            )
            evidence.update(candidate.evidence_refs)
            if construction_record.output_schema_ref is None:
                if construction_record.construction_kind == ConstructionKind.COORDINATION:
                    group = self._coordination_group(
                        candidate, construction_record, grounding,
                        selected_candidate_by_mention, lattice,
                    )
                    if group is not None:
                        coordination[group.group_ref] = group
                        roots.append(FillerRef(PortFillerClass.COORDINATION_GROUP, group.group_ref))
                    else:
                        unresolved.add(candidate.candidate_ref)
                elif construction_record.construction_kind == ConstructionKind.ELLIPSIS:
                    gap_ref = self._gap_variable_ref(candidate.candidate_ref, "ellipsis")
                    variables[gap_ref] = SemanticVariable(
                        variable_ref=gap_ref,
                        scope_ref="local",
                        evidence_refs=candidate.evidence_refs,
                    )
                    unresolved.add(gap_ref)
                else:
                    # A syntactic construction without semantic output remains
                    # preserved as evidence; it cannot invent an application.
                    unresolved.add(candidate.candidate_ref)
                continue

            schema = registry.schema(
                construction_record.output_schema_ref,
                construction_record.output_schema_revision,
            )
            if not schema.use_profile.permits(UseOperation.COMPOSE, provisional=True):
                unresolved.add(candidate.candidate_ref)
                continue
            app_ref = self._application_ref(hypothesis.hypothesis_ref, candidate.candidate_ref)
            bindings = []
            for port in schema.local_ports:
                selected = selected_port_values.get((candidate.candidate_ref, port.port_ref))
                if selected is None:
                    if port.cardinality.minimum > 0:
                        if OpenBindingPurpose.PARTIAL_COMPOSITION in port.open_binding_purposes:
                            variable = self._semantic_gap(
                                hypothesis.hypothesis_ref, app_ref, port, candidate.evidence_refs
                            )
                            variables[variable.variable_ref] = variable
                            bindings.append(ApplicationBinding(
                                port_ref=port.port_ref,
                                fillers=(FillerRef(PortFillerClass.SEMANTIC_VARIABLE, variable.variable_ref),),
                                confidence=0.45,
                                evidence_refs=candidate.evidence_refs,
                                open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
                                ordered=port.ordered_fillers,
                            ))
                            unresolved.add(variable.variable_ref)
                        else:
                            unresolved.add(f"{app_ref}:{port.port_ref}")
                    continue
                _port_variable, choice = selected
                if choice.value_ref == _OMITTED:
                    continue
                if choice.value_ref == _GAP:
                    variable = self._semantic_gap(
                        hypothesis.hypothesis_ref, app_ref, port, choice.evidence_refs
                    )
                    variables[variable.variable_ref] = variable
                    bindings.append(ApplicationBinding(
                        port_ref=port.port_ref,
                        fillers=(FillerRef(PortFillerClass.SEMANTIC_VARIABLE, variable.variable_ref),),
                        confidence=0.45,
                        evidence_refs=choice.evidence_refs,
                        open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
                        ordered=port.ordered_fillers,
                    ))
                    unresolved.add(variable.variable_ref)
                    continue
                fillers = []
                for selected_candidate_ref in choice.metadata.get("candidate_refs", ()):
                    selected_candidate = candidate_by_ref.get(str(selected_candidate_ref))
                    if selected_candidate is None:
                        continue
                    target_ref = selected_candidate.target_ref
                    if target_ref not in referents:
                        referents[target_ref] = self._cycle_referent(
                            selected_candidate, snapshot=snapshot
                        )
                    fillers.append(FillerRef(PortFillerClass.REFERENT, target_ref))
                if fillers:
                    bindings.append(ApplicationBinding(
                        port_ref=port.port_ref,
                        fillers=tuple(fillers),
                        confidence=min(1.0, max(0.0, candidate.confidence)),
                        evidence_refs=choice.evidence_refs,
                        ordered=port.ordered_fillers,
                    ))

            application = SemanticApplication(
                application_ref=app_ref,
                schema_ref=schema.schema_ref,
                schema_revision=schema.revision,
                bindings=tuple(bindings),
                context_ref=context_ref,
                use_operation=UseOperation.COMPOSE,
                confidence=candidate.confidence,
                evidence_refs=candidate.evidence_refs,
                metadata={
                    "construction_candidate_ref": candidate.candidate_ref,
                    "partial": any(
                        binding.open_binding_purpose == OpenBindingPurpose.PARTIAL_COMPOSITION
                        for binding in bindings
                    ),
                },
            )
            applications[app_ref] = application
            if schema.schema_class == SchemaClass.EVENT:
                event = self._event_occurrence(
                    hypothesis.hypothesis_ref, application, schema,
                    selected_candidate_by_mention, referents, context_ref,
                    candidate.evidence_refs, snapshot=snapshot,
                )
                events[event.event_ref] = event
                referents[event.event_ref] = event.referent
            roots.append(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, app_ref))

            # Prevent a lexical trigger from generating a duplicate application
            # for the same exact schema occurrence.
            trigger_span = candidate.span
            for sense_ref, selected_value in selected_senses.items():
                schema_choice = selected_schema_by_sense.get(sense_ref)
                if schema_choice is None or schema_choice.metadata.get("target_ref") != schema.schema_ref:
                    continue
                if schema_choice.metadata.get("target_revision") != schema.revision:
                    continue
                source_sense = next(
                    (item for item in lattice.sense_candidates if item.candidate_ref == sense_ref), None
                )
                if source_sense is None:
                    continue
                form = next(
                    (item for item in lattice.form_candidates if item.candidate_ref == source_sense.form_candidate_ref), None
                )
                if form is not None and _span_inside(form.span, trigger_span):
                    covered_senses.add(sense_ref)
                    app_ref_by_sense[sense_ref] = app_ref

        # Pre-allocate lexical application refs so nested operators may point to
        # one another without order-dependent construction.
        selected_schema_senses = []
        for sense_candidate_ref, selected_value in sorted(selected_senses.items()):
            if sense_candidate_ref in covered_senses:
                continue
            schema_choice = selected_schema_by_sense.get(sense_candidate_ref)
            if schema_choice is None:
                continue
            if schema_choice.metadata.get("structural"):
                continue
            target_ref = schema_choice.metadata.get("target_ref")
            revision = schema_choice.metadata.get("target_revision")
            if not target_ref or revision is None:
                unresolved.add(sense_candidate_ref)
                continue
            try:
                schema = registry.schema(str(target_ref), int(revision))
            except Exception:
                unresolved.add(sense_candidate_ref)
                continue
            if not schema.use_profile.permits(UseOperation.COMPOSE, provisional=True):
                unresolved.add(sense_candidate_ref)
                continue
            app_ref = self._application_ref(hypothesis.hypothesis_ref, sense_candidate_ref)
            app_ref_by_sense[sense_candidate_ref] = app_ref
            selected_schema_senses.append((sense_candidate_ref, selected_value, schema, app_ref))

        scope_choice_by_operator = {}
        for variable in factor_graph.variables:
            if variable.variable_kind != MeaningVariableKind.SCOPE:
                continue
            chosen = value_by_assignment.get(variable.variable_ref)
            operator_ref = str(variable.metadata.get("operator_sense_candidate_ref") or "")
            if chosen is not None and operator_ref:
                scope_choice_by_operator[operator_ref] = chosen

        for sense_candidate_ref, selected_value, schema, app_ref in selected_schema_senses:
            source_sense = next(
                (item for item in lattice.sense_candidates if item.candidate_ref == sense_candidate_ref), None
            )
            sense_evidence = tuple(selected_value.evidence_refs)
            bindings = []
            if schema.schema_class == SchemaClass.OPERATOR:
                scope_choice = scope_choice_by_operator.get(sense_candidate_ref)
                target_app_ref = None
                if scope_choice is not None and scope_choice.value_ref != _UNRESOLVED:
                    target_sense_ref = scope_choice.metadata.get("target_sense_candidate_ref")
                    if target_sense_ref:
                        target_app_ref = app_ref_by_sense.get(str(target_sense_ref))
                operand_port = schema.local_ports[0] if len(schema.local_ports) == 1 else None
                if operand_port is not None and target_app_ref is not None:
                    bindings.append(ApplicationBinding(
                        port_ref=operand_port.port_ref,
                        fillers=(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, target_app_ref),),
                        confidence=0.8,
                        evidence_refs=sense_evidence,
                        ordered=operand_port.ordered_fillers,
                    ))
                    scope_kind = _scope_kind(
                        str(scope_choice.metadata.get("scope_behavior") or selected_value.metadata.get("scope_behavior") or "")
                    )
                    scopes.append(ScopeRelation(
                        scope_relation_ref="scope-relation:" + semantic_fingerprint(
                            "scope-relation-ref", (app_ref, target_app_ref, scope_kind.value), 24
                        ),
                        operator_application_ref=app_ref,
                        scoped_ref=FillerRef(PortFillerClass.SEMANTIC_APPLICATION, target_app_ref),
                        scope_kind=scope_kind,
                        evidence_refs=tuple(sorted(set(sense_evidence) | set(scope_choice.evidence_refs))),
                    ))
                elif operand_port is not None:
                    variable = self._semantic_gap(
                        hypothesis.hypothesis_ref, app_ref, operand_port, sense_evidence
                    )
                    variables[variable.variable_ref] = variable
                    bindings.append(ApplicationBinding(
                        port_ref=operand_port.port_ref,
                        fillers=(FillerRef(PortFillerClass.SEMANTIC_VARIABLE, variable.variable_ref),),
                        confidence=0.35,
                        evidence_refs=sense_evidence,
                        open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
                        ordered=operand_port.ordered_fillers,
                    ))
                    unresolved.add(variable.variable_ref)
            else:
                for port in schema.local_ports:
                    # Lexical schemas without a selected argument construction
                    # remain honestly partial; no surface-position guessing fills
                    # semantic ports.
                    if port.cardinality.minimum <= 0:
                        continue
                    if OpenBindingPurpose.PARTIAL_COMPOSITION not in port.open_binding_purposes:
                        unresolved.add(f"{app_ref}:{port.port_ref}")
                        continue
                    variable = self._semantic_gap(
                        hypothesis.hypothesis_ref, app_ref, port, sense_evidence
                    )
                    variables[variable.variable_ref] = variable
                    bindings.append(ApplicationBinding(
                        port_ref=port.port_ref,
                        fillers=(FillerRef(PortFillerClass.SEMANTIC_VARIABLE, variable.variable_ref),),
                        confidence=0.35,
                        evidence_refs=sense_evidence,
                        open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
                        ordered=port.ordered_fillers,
                    ))
                    unresolved.add(variable.variable_ref)

            application = SemanticApplication(
                application_ref=app_ref,
                schema_ref=schema.schema_ref,
                schema_revision=schema.revision,
                bindings=tuple(bindings),
                context_ref=context_ref,
                use_operation=UseOperation.COMPOSE,
                confidence=float(getattr(source_sense, "confidence", 0.5)),
                evidence_refs=sense_evidence,
                metadata={
                    "sense_candidate_ref": sense_candidate_ref,
                    "authority_path": getattr(source_sense, "authority_path", ""),
                    "semantic_contribution_refs": tuple(
                        item.contribution_ref for item in getattr(source_sense, "contributions", ())
                    ),
                    "partial": bool(unresolved.intersection(
                        binding.fillers[0].ref for binding in bindings
                        if binding.fillers and isinstance(binding.fillers[0], FillerRef)
                        and binding.fillers[0].filler_class == PortFillerClass.SEMANTIC_VARIABLE
                    )),
                },
            )
            applications[app_ref] = application
            if schema.schema_class == SchemaClass.EVENT:
                event = self._event_occurrence(
                    hypothesis.hypothesis_ref, application, schema,
                    selected_candidate_by_mention, referents, context_ref,
                    sense_evidence, snapshot=snapshot,
                )
                events[event.event_ref] = event
                referents[event.event_ref] = event.referent

        # Root selection is semantic and graph-structural: anything scoped by an
        # operator is not also emitted as an independent root.  No realization
        # concern participates in this decision.
        scoped_application_refs = {
            item.scoped_ref.ref for item in scopes
            if item.scoped_ref.filler_class == PortFillerClass.SEMANTIC_APPLICATION
        }
        operator_app_refs = {item.operator_application_ref for item in scopes}
        existing_root_refs = {item.ref for item in roots}
        for app_ref in sorted(applications):
            if app_ref in scoped_application_refs:
                continue
            if app_ref not in existing_root_refs:
                roots.append(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, app_ref))
        # If an inner operator is scoped by another operator it is naturally
        # removed as a root by the same rule above.

        graph = UOLGraph(
            graph_ref="uol-graph:" + semantic_fingerprint(
                "phase9-uol-graph-ref", (factor_graph.graph_ref, hypothesis.hypothesis_ref), 24
            ),
            referents=dict(sorted(referents.items())),
            applications=dict(sorted(applications.items())),
            variables=dict(sorted(variables.items())),
            coordination_groups=dict(sorted(coordination.items())),
            propositions={},
            claims={},
            events=dict(sorted(events.items())),
            scope_relations=tuple(sorted(scopes, key=lambda item: item.scope_relation_ref)),
            state_deltas=(),
            capability_deltas=(),
            impact_assessments=(),
            importance_assessments=(),
            root_refs=tuple(_dedupe_fillers(roots)),
            unresolved_refs=tuple(sorted(unresolved)),
            assumptions=(),
            evidence_refs=tuple(sorted(evidence)),
        )
        report = UOLValidator(registry).validate(graph, provisional=True)
        if report.errors:
            raise UOLMaterializationError(
                "; ".join(f"{item.code}:{item.target_ref}:{item.message}" for item in report.errors)
            )
        return graph, report

    def _cycle_referent(
        self, candidate: GroundingCandidate, *, snapshot: StoreSnapshot
    ) -> Referent:
        stored = self.store.repositories.referents.get(candidate.target_ref, snapshot=snapshot)
        if stored is not None:
            return stored.payload
        return Referent(
            referent_ref=candidate.target_ref,
            storage_kind=candidate.storage_kind,
            identity_status=IdentityStatus.PROVISIONAL if candidate.provisional else IdentityStatus.CANDIDATE,
            type_refs=tuple(candidate.type_refs),
            context_refs=tuple(candidate.context_refs),
            valid_time_ref=candidate.valid_time_ref,
            provenance_refs=tuple(sorted({ref for factor in candidate.factors for ref in factor.evidence_refs})),
            metadata={"cycle_local": True, "candidate_origin": candidate.origin.value},
        )

    def _event_occurrence(
        self,
        hypothesis_ref,
        application,
        schema,
        selected_candidate_by_mention,
        referents,
        context_ref,
        evidence_refs,
        *,
        snapshot,
    ) -> EventOccurrence:
        matching = []
        for candidate in selected_candidate_by_mention.values():
            if candidate.storage_kind != StorageKind.EVENT_OCCURRENCE:
                continue
            pins = tuple(candidate.metadata.get("introduced_by_schema_pins", ()))
            if (schema.schema_ref, schema.revision) in {
                (str(ref), int(revision)) for ref, revision in pins
            }:
                matching.append(candidate)
        matching.sort(key=lambda item: (-item.local_score, item.candidate_ref))
        if matching:
            referent = self._cycle_referent(matching[0], snapshot=snapshot)
        else:
            event_ref = "referent:cycle-event:" + semantic_fingerprint(
                "cycle-event-ref", (hypothesis_ref, application.application_ref), 24
            )
            referent = Referent(
                referent_ref=event_ref,
                storage_kind=StorageKind.EVENT_OCCURRENCE,
                identity_status=IdentityStatus.PROVISIONAL,
                context_refs=(context_ref,),
                provenance_refs=tuple(evidence_refs),
                metadata={"cycle_local": True, "introduced_by_application_ref": application.application_ref},
            )
        referents[referent.referent_ref] = referent
        return EventOccurrence(
            referent=referent,
            event_schema_ref=schema.schema_ref,
            event_schema_revision=schema.revision,
            participant_application_ref=application.application_ref,
            context_ref=context_ref,
            occurrence_status=OccurrenceStatus.MENTIONED,
            provenance_refs=tuple(evidence_refs),
            admission_refs=(),
        )

    @staticmethod
    def _semantic_gap(hypothesis_ref, app_ref, port, evidence_refs):
        variable_ref = "semantic-variable:" + semantic_fingerprint(
            "phase9-semantic-gap-ref", (hypothesis_ref, app_ref, port.port_ref), 24
        )
        return SemanticVariable(
            variable_ref=variable_ref,
            expected_schema_classes=frozenset(port.accepted_schema_classes),
            expected_type_refs=tuple(port.accepted_type_refs),
            expected_filler_classes=frozenset(port.filler_classes),
            scope_ref="local",
            evidence_refs=tuple(evidence_refs),
            open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
        )

    @staticmethod
    def _gap_variable_ref(candidate_ref, slot_ref):
        return "semantic-variable:" + semantic_fingerprint(
            "phase9-construction-gap-ref", (candidate_ref, slot_ref), 24
        )

    @staticmethod
    def _application_ref(hypothesis_ref, source_ref):
        return "semantic-application:" + semantic_fingerprint(
            "phase9-application-ref", (hypothesis_ref, source_ref), 24
        )

    @staticmethod
    def _coordination_group(candidate, record, grounding, selected_by_mention, lattice):
        # Coordination membership is recovered only from construction slot
        # evidence and the already selected referent identities.
        members = []
        for slot_ref, filler_refs in candidate.slot_fillers:
            for mention in grounding.mentions:
                if candidate.candidate_ref not in mention.construction_candidate_refs:
                    continue
                if mention.syntactic_role != slot_ref:
                    continue
                selected = selected_by_mention.get(mention.mention_ref)
                if selected is not None:
                    members.append(FillerRef(PortFillerClass.REFERENT, selected.target_ref))
        members = _dedupe_fillers(members)
        if len(members) < 2:
            return None
        raw_kind = str(record.metadata.get("coordination_kind") or "list")
        try:
            kind = CoordinationKind(raw_kind)
        except ValueError:
            kind = CoordinationKind.LIST
        return CoordinationGroup(
            group_ref="coordination-group:" + semantic_fingerprint(
                "phase9-coordination-ref", (candidate.candidate_ref, tuple((m.filler_class.value, m.ref) for m in members)), 24
            ),
            coordination_kind=kind,
            members=tuple(members),
            scope_ref="local",
            evidence_refs=candidate.evidence_refs,
        )


def _scope_kind(value: str) -> ScopeKind:
    # These are structural scope-family labels, not ontology concepts.
    return {
        "modal": ScopeKind.MODAL,
        "negation": ScopeKind.NEGATION,
        "temporal": ScopeKind.TEMPORAL,
        "quantifier": ScopeKind.QUANTIFIER,
        "discourse": ScopeKind.DISCOURSE,
        "logical": ScopeKind.LOGICAL,
    }.get(value, ScopeKind.LOGICAL)


def _span_inside(inner, outer) -> bool:
    return inner.start >= outer.start and inner.end <= outer.end


def _dedupe_fillers(values):
    seen = set()
    result = []
    for item in values:
        key = (item.filler_class, item.ref)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return tuple(result)
