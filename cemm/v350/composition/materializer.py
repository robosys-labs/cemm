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
from ..language.programs import ConstructionSemanticPlan
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

        selected_port_values: dict[tuple[str, ...], object] = {}
        for variable in factor_graph.variables:
            if variable.variable_kind != MeaningVariableKind.PORT_FILLER:
                continue
            chosen = value_by_assignment.get(variable.variable_ref)
            if chosen is None or chosen.value_ref == _INACTIVE:
                continue
            candidate_ref = str(variable.metadata.get("construction_candidate_ref"))
            port_ref = str(variable.metadata.get("port_ref"))
            selected_port_values[(candidate_ref, port_ref)] = (variable, chosen)
            semantic_plan_ref = str(variable.metadata.get("semantic_plan_ref") or "")
            application_symbol_ref = str(variable.metadata.get("application_symbol_ref") or "")
            if semantic_plan_ref and application_symbol_ref:
                selected_port_values[(
                    candidate_ref,
                    semantic_plan_ref,
                    application_symbol_ref,
                    port_ref,
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
        lexical_variable_by_sense: dict[str, str] = {}
        for sense_candidate_ref in sorted(selected_senses):
            source_sense = sense_candidate_by_ref.get(sense_candidate_ref)
            if source_sense is None:
                unresolved.add(sense_candidate_ref)
                continue
            contributions = tuple(getattr(source_sense, "contributions", ()))
            projection_pins = tuple(sorted({
                (item.projection_ref, item.projection_revision) for item in contributions
                if item.contribution_kind.value == "projection" and item.projection_ref and item.projection_revision
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
                projection_revision = contribution.projection_revision
                if projection_ref is None and len(projection_pins) == 1:
                    projection_ref, projection_revision = projection_pins[0]
                variables[variable_ref] = SemanticVariable(
                    variable_ref=variable_ref,
                    expected_schema_classes=frozenset(contribution.expected_schema_classes),
                    expected_type_refs=tuple(contribution.expected_type_refs),
                    restriction_refs=tuple(sorted(set((*restriction_refs, *contribution.restriction_refs)))),
                    projection_ref=projection_ref,
                    projection_revision=projection_revision,
                    projection_candidates=projection_pins if projection_ref is None else (),
                    scope_ref="local",
                    evidence_refs=contribution.evidence_refs or source_sense.evidence_refs,
                    expected_filler_classes=frozenset(contribution.expected_filler_classes),
                    open_binding_purpose=contribution.open_binding_purpose,
                )
                lexical_variable_by_sense[sense_candidate_ref] = variable_ref
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
            selected_construction_value = selected_constructions[candidate_ref]
            semantic_plan_metadata = selected_construction_value.metadata.get(
                "semantic_plan"
            )
            if semantic_plan_metadata:
                semantic_plan = ConstructionSemanticPlan.from_metadata(
                    semantic_plan_metadata
                )
                self._materialize_construction_plan(
                    semantic_plan,
                    candidate=candidate,
                    hypothesis=hypothesis,
                    registry=registry,
                    selected_port_values=selected_port_values,
                    selected_candidate_by_mention=selected_candidate_by_mention,
                    candidate_by_ref=candidate_by_ref,
                    selected_senses=selected_senses,
                    selected_schema_by_sense=selected_schema_by_sense,
                    lattice=lattice,
                    context_ref=context_ref,
                    snapshot=snapshot,
                    referents=referents,
                    applications=applications,
                    variables=variables,
                    events=events,
                    scopes=scopes,
                    roots=roots,
                    unresolved=unresolved,
                    covered_senses=covered_senses,
                    app_ref_by_sense=app_ref_by_sense,
                    lexical_variable_by_sense=lexical_variable_by_sense,
                    sense_candidate_by_ref=sense_candidate_by_ref,
                )
                continue
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
                scope_ports = tuple(
                    port for port in schema.local_ports
                    if PortFillerClass.SEMANTIC_APPLICATION in port.filler_classes
                )
                bound_scope_port = None
                if target_app_ref is not None and len(scope_ports) == 1:
                    bound_scope_port = scope_ports[0]
                    bindings.append(ApplicationBinding(
                        port_ref=bound_scope_port.port_ref,
                        fillers=(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, target_app_ref),),
                        confidence=0.8,
                        evidence_refs=sense_evidence,
                        ordered=bound_scope_port.ordered_fillers,
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
                elif target_app_ref is not None and len(scope_ports) > 1:
                    # Multiple semantically compatible ports require a construction
                    # program or argument contribution. Never guess by port order.
                    unresolved.add(
                        f"{app_ref}:ambiguous-operator-scope-port"
                    )

                for port in schema.local_ports:
                    if bound_scope_port is not None and port.port_ref == bound_scope_port.port_ref:
                        continue
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


    def _materialize_construction_plan(
        self,
        plan: ConstructionSemanticPlan,
        *,
        candidate,
        hypothesis,
        registry,
        selected_port_values,
        selected_candidate_by_mention,
        candidate_by_ref,
        selected_senses,
        selected_schema_by_sense,
        lattice,
        context_ref,
        snapshot,
        referents,
        applications,
        variables,
        events,
        scopes,
        roots,
        unresolved,
        covered_senses,
        app_ref_by_sense,
        lexical_variable_by_sense,
        sense_candidate_by_ref,
    ) -> None:
        aliases = _program_symbol_aliases(plan)
        app_specs_by_symbol = {
            item.symbol_ref: item for item in plan.applications
        }
        variable_specs_by_symbol = {
            item.symbol_ref: item for item in plan.variables
        }
        groups: dict[str, set[str]] = defaultdict(set)
        for symbol in (*app_specs_by_symbol, *variable_specs_by_symbol):
            groups[aliases.get(symbol, symbol)].add(symbol)
    
        # Unification is structural identity. A group may not silently unify an
        # application and a variable, nor two different exact schema pins.
        for canonical, symbols in groups.items():
            app_pins = {
                (
                    app_specs_by_symbol[symbol].schema_ref,
                    app_specs_by_symbol[symbol].schema_revision,
                )
                for symbol in symbols
                if symbol in app_specs_by_symbol
            }
            has_variables = any(
                symbol in variable_specs_by_symbol for symbol in symbols
            )
            if app_pins and has_variables:
                raise UOLMaterializationError(
                    f"construction plan unifies application and variable:{plan.plan_ref}:{canonical}"
                )
            if len(app_pins) > 1:
                raise UOLMaterializationError(
                    f"construction plan unifies incompatible applications:{plan.plan_ref}:{canonical}"
                )
    
        symbol_refs: dict[str, str] = {}
    
        # Applications are allocated before bindings so graph references are
        # order-independent.
        for app_spec in plan.applications:
            canonical = aliases.get(app_spec.symbol_ref, app_spec.symbol_ref)
            symbol_refs[app_spec.symbol_ref] = symbol_refs.setdefault(
                canonical,
                self._application_ref(
                    hypothesis.hypothesis_ref,
                    f"{candidate.candidate_ref}:{plan.plan_ref}:{canonical}",
                ),
            )
    
        # Merge constraints for unified variables instead of dropping either
        # contribution.
        merged_variable_specs = {}
        for variable_spec in plan.variables:
            canonical = aliases.get(
                variable_spec.symbol_ref, variable_spec.symbol_ref
            )
            previous = merged_variable_specs.get(canonical)
            if previous is None:
                merged_variable_specs[canonical] = variable_spec
                continue
            projection_ref = previous.projection_ref or variable_spec.projection_ref
            projection_revision = (
                previous.projection_revision
                or variable_spec.projection_revision
            )
            if (
                previous.projection_ref
                and variable_spec.projection_ref
                and (
                    previous.projection_ref,
                    previous.projection_revision,
                )
                != (
                    variable_spec.projection_ref,
                    variable_spec.projection_revision,
                )
            ):
                unresolved.add(
                    f"construction-plan-projection-conflict:{plan.plan_ref}:{canonical}"
                )
                projection_ref = None
                projection_revision = None
            from dataclasses import replace as _replace
            merged_variable_specs[canonical] = _replace(
                previous,
                expected_filler_classes=tuple(
                    sorted(
                        set(
                            (
                                *previous.expected_filler_classes,
                                *variable_spec.expected_filler_classes,
                            )
                        ),
                        key=lambda item: item.value,
                    )
                ),
                expected_schema_classes=tuple(
                    sorted(
                        set(
                            (
                                *previous.expected_schema_classes,
                                *variable_spec.expected_schema_classes,
                            )
                        ),
                        key=lambda item: item.value,
                    )
                ),
                expected_type_refs=tuple(
                    sorted(
                        set(
                            (
                                *previous.expected_type_refs,
                                *variable_spec.expected_type_refs,
                            )
                        )
                    )
                ),
                restriction_refs=tuple(
                    sorted(
                        set(
                            (
                                *previous.restriction_refs,
                                *variable_spec.restriction_refs,
                            )
                        )
                    )
                ),
                projection_ref=projection_ref,
                projection_revision=projection_revision,
                open_binding_purpose=(
                    previous.open_binding_purpose
                    or variable_spec.open_binding_purpose
                ),
                preserve_gap=(
                    previous.preserve_gap or variable_spec.preserve_gap
                ),
            )
    
        for canonical, variable_spec in merged_variable_specs.items():
            variable_ref = self._gap_variable_ref(
                candidate.candidate_ref,
                f"{plan.plan_ref}:{canonical}",
            )
            symbol_refs[canonical] = variable_ref
            for symbol in groups.get(canonical, (canonical,)):
                symbol_refs[symbol] = variable_ref
            variables[variable_ref] = SemanticVariable(
                variable_ref=variable_ref,
                expected_filler_classes=frozenset(
                    variable_spec.expected_filler_classes
                ),
                expected_schema_classes=frozenset(
                    variable_spec.expected_schema_classes
                ),
                expected_type_refs=variable_spec.expected_type_refs,
                restriction_refs=variable_spec.restriction_refs,
                projection_ref=variable_spec.projection_ref,
                projection_revision=variable_spec.projection_revision,
                open_binding_purpose=variable_spec.open_binding_purpose,
                scope_ref="local",
                evidence_refs=plan.evidence_refs,
            )
            if variable_spec.preserve_gap:
                unresolved.add(variable_ref)
    
        binding_specs_by_application: dict[str, list] = defaultdict(list)
        for binding in plan.bindings:
            binding_specs_by_application[
                binding.application_symbol_ref
            ].append(binding)
    
        application_ref_by_schema_pin = {}
        for app_spec in plan.applications:
            schema = registry.schema(
                app_spec.schema_ref, app_spec.schema_revision
            )
            if not schema.use_profile.permits(
                UseOperation.COMPOSE, provisional=True
            ):
                unresolved.add(
                    f"{candidate.candidate_ref}:{app_spec.schema_ref}@{app_spec.schema_revision}"
                )
                continue
    
            app_ref = symbol_refs[app_spec.symbol_ref]
            bindings = []
            by_port = {
                item.port_ref: item
                for item in binding_specs_by_application.get(
                    app_spec.symbol_ref, ()
                )
            }
            for port in schema.local_ports:
                binding_spec = by_port.get(port.port_ref)
                if binding_spec is None:
                    if port.cardinality.minimum <= 0:
                        continue
                    if (
                        OpenBindingPurpose.PARTIAL_COMPOSITION
                        in port.open_binding_purposes
                    ):
                        variable = self._semantic_gap(
                            hypothesis.hypothesis_ref,
                            app_ref,
                            port,
                            plan.evidence_refs,
                        )
                        variables[variable.variable_ref] = variable
                        bindings.append(
                            ApplicationBinding(
                                port_ref=port.port_ref,
                                fillers=(
                                    FillerRef(
                                        PortFillerClass.SEMANTIC_VARIABLE,
                                        variable.variable_ref,
                                    ),
                                ),
                                confidence=0.35,
                                evidence_refs=plan.evidence_refs,
                                open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
                                ordered=port.ordered_fillers,
                            )
                        )
                        unresolved.add(variable.variable_ref)
                    else:
                        unresolved.add(f"{app_ref}:{port.port_ref}")
                    continue
    
                if binding_spec.source_kind == "symbol":
                    source_symbol = binding_spec.source_ref
                    source_ref = symbol_refs.get(source_symbol)
                    if source_ref is None:
                        unresolved.add(
                            f"{app_ref}:{port.port_ref}:{source_symbol}"
                        )
                        continue
                    if source_symbol in app_specs_by_symbol:
                        filler_class = PortFillerClass.SEMANTIC_APPLICATION
                        purpose = None
                    else:
                        filler_class = PortFillerClass.SEMANTIC_VARIABLE
                        purpose = (
                            variables[source_ref].open_binding_purpose
                            or OpenBindingPurpose.PARTIAL_COMPOSITION
                        )
                    bindings.append(
                        ApplicationBinding(
                            port_ref=port.port_ref,
                            fillers=(FillerRef(filler_class, source_ref),),
                            confidence=0.8,
                            evidence_refs=plan.evidence_refs,
                            open_binding_purpose=purpose,
                            ordered=port.ordered_fillers,
                        )
                    )
                    if filler_class == PortFillerClass.SEMANTIC_VARIABLE:
                        unresolved.add(source_ref)
                    continue
    
                selected = selected_port_values.get(
                    (
                        candidate.candidate_ref,
                        plan.plan_ref,
                        app_spec.symbol_ref,
                        port.port_ref,
                    )
                )
                if selected is None:
                    unresolved.add(f"{app_ref}:{port.port_ref}")
                    continue
                _port_variable, choice = selected
                if choice.value_ref == _OMITTED:
                    continue
                if choice.value_ref == _GAP:
                    slot_refs = tuple(next(
                        (refs for slot_ref, refs in candidate.slot_fillers if slot_ref == binding_spec.source_ref),
                        (),
                    ))
                    slot_sense_refs = set()
                    for slot_ref in slot_refs:
                        if slot_ref in lexical_variable_by_sense:
                            slot_sense_refs.add(slot_ref)
                            continue
                        for selected_sense_ref in selected_senses:
                            selected_source_sense = sense_candidate_by_ref.get(selected_sense_ref)
                            if selected_source_sense is not None and selected_source_sense.form_candidate_ref == slot_ref:
                                slot_sense_refs.add(selected_sense_ref)
                    query_variables = []
                    for selected_sense_ref in sorted(slot_sense_refs):
                        variable_ref = lexical_variable_by_sense.get(selected_sense_ref)
                        if variable_ref is None:
                            continue
                        lexical_variable = variables[variable_ref]
                        if lexical_variable.open_binding_purpose != OpenBindingPurpose.QUERY:
                            continue
                        if lexical_variable.expected_filler_classes and not set(lexical_variable.expected_filler_classes).intersection(port.filler_classes):
                            continue
                        if lexical_variable.expected_schema_classes and port.accepted_schema_classes and not set(lexical_variable.expected_schema_classes).intersection(port.accepted_schema_classes):
                            continue
                        query_variables.append(variable_ref)
                    query_variables = tuple(sorted(set(query_variables)))
                    if OpenBindingPurpose.QUERY in port.open_binding_purposes and len(query_variables) == 1:
                        query_ref = query_variables[0]
                        bindings.append(ApplicationBinding(
                            port_ref=port.port_ref,
                            fillers=(FillerRef(PortFillerClass.SEMANTIC_VARIABLE, query_ref),),
                            confidence=0.8, evidence_refs=choice.evidence_refs,
                            open_binding_purpose=OpenBindingPurpose.QUERY, ordered=port.ordered_fillers,
                        ))
                        unresolved.add(query_ref)
                        continue
                    variable = self._semantic_gap(
                        hypothesis.hypothesis_ref, app_ref, port, choice.evidence_refs
                    )
                    variables[variable.variable_ref] = variable
                    bindings.append(ApplicationBinding(
                        port_ref=port.port_ref,
                        fillers=(FillerRef(PortFillerClass.SEMANTIC_VARIABLE, variable.variable_ref),),
                        confidence=0.45, evidence_refs=choice.evidence_refs,
                        open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION, ordered=port.ordered_fillers,
                    ))
                    unresolved.add(variable.variable_ref)
                    continue
    
                fillers = []
                for selected_candidate_ref in choice.metadata.get(
                    "candidate_refs", ()
                ):
                    selected_candidate = candidate_by_ref.get(
                        str(selected_candidate_ref)
                    )
                    if selected_candidate is None:
                        continue
                    target_ref = selected_candidate.target_ref
                    if target_ref not in referents:
                        referents[target_ref] = self._cycle_referent(
                            selected_candidate, snapshot=snapshot
                        )
                    fillers.append(
                        FillerRef(PortFillerClass.REFERENT, target_ref)
                    )
                if fillers:
                    bindings.append(
                        ApplicationBinding(
                            port_ref=port.port_ref,
                            fillers=tuple(fillers),
                            confidence=min(
                                1.0, max(0.0, candidate.confidence)
                            ),
                            evidence_refs=choice.evidence_refs,
                            ordered=port.ordered_fillers,
                        )
                    )
    
            application = SemanticApplication(
                application_ref=app_ref,
                schema_ref=schema.schema_ref,
                schema_revision=schema.revision,
                bindings=tuple(bindings),
                context_ref=context_ref,
                use_operation=UseOperation.COMPOSE,
                confidence=candidate.confidence,
                evidence_refs=tuple(
                    sorted(
                        set(candidate.evidence_refs)
                        | set(plan.evidence_refs)
                    )
                ),
                metadata={
                    "construction_candidate_ref": candidate.candidate_ref,
                    "construction_semantic_plan_ref": plan.plan_ref,
                    "construction_authority_path": plan.authority_path,
                    "construction_authority_ref": plan.authority_ref,
                    "grammatical_features": tuple(
                        item
                        for item in plan.feature_values
                        if item[0] == app_spec.symbol_ref
                    ),
                    "partial": any(
                        binding.open_binding_purpose is not None
                        for binding in bindings
                    ),
                },
            )
            applications[app_ref] = application
            application_ref_by_schema_pin[
                (schema.schema_ref, schema.revision)
            ] = app_ref
            if schema.schema_class == SchemaClass.EVENT:
                event = self._event_occurrence(
                    hypothesis.hypothesis_ref,
                    application,
                    schema,
                    selected_candidate_by_mention,
                    referents,
                    context_ref,
                    application.evidence_refs,
                    snapshot=snapshot,
                )
                events[event.event_ref] = event
                referents[event.event_ref] = event.referent
    
        for scope_spec in plan.scopes:
            operator_ref = symbol_refs.get(scope_spec.operator_symbol_ref)
            target_ref = symbol_refs.get(scope_spec.target_symbol_ref)
            if operator_ref is None or target_ref is None:
                unresolved.add(
                    f"construction-plan-scope:{plan.plan_ref}:"
                    f"{scope_spec.operator_symbol_ref}:{scope_spec.target_symbol_ref}"
                )
                continue
            target_class = (
                PortFillerClass.SEMANTIC_APPLICATION
                if scope_spec.target_symbol_ref in app_specs_by_symbol
                else PortFillerClass.SEMANTIC_VARIABLE
            )
            scopes.append(
                ScopeRelation(
                    scope_relation_ref="scope-relation:"
                    + semantic_fingerprint(
                        "construction-program-scope",
                        (
                            plan.plan_ref,
                            operator_ref,
                            target_ref,
                            scope_spec.scope_kind,
                        ),
                        24,
                    ),
                    operator_application_ref=operator_ref,
                    scoped_ref=FillerRef(target_class, target_ref),
                    scope_kind=_scope_kind(scope_spec.scope_kind),
                    evidence_refs=plan.evidence_refs,
                )
            )
    
        for root_symbol in plan.root_symbol_refs:
            root_ref = symbol_refs.get(root_symbol)
            if root_ref is None:
                unresolved.add(
                    f"construction-plan-root:{plan.plan_ref}:{root_symbol}"
                )
                continue
            filler_class = (
                PortFillerClass.SEMANTIC_APPLICATION
                if root_symbol in app_specs_by_symbol
                else PortFillerClass.SEMANTIC_VARIABLE
            )
            roots.append(FillerRef(filler_class, root_ref))
    
        # Prevent lexical triggers from generating duplicate applications for the
        # same exact schema occurrence.
        trigger_span = candidate.span
        for sense_ref in selected_senses:
            schema_choice = selected_schema_by_sense.get(sense_ref)
            if schema_choice is None:
                continue
            pin = (
                schema_choice.metadata.get("target_ref"),
                schema_choice.metadata.get("target_revision"),
            )
            app_ref = application_ref_by_schema_pin.get(pin)
            if app_ref is None:
                continue
            source_sense = next(
                (
                    item
                    for item in lattice.sense_candidates
                    if item.candidate_ref == sense_ref
                ),
                None,
            )
            if source_sense is None:
                continue
            form = next(
                (
                    item
                    for item in lattice.form_candidates
                    if item.candidate_ref
                    == source_sense.form_candidate_ref
                ),
                None,
            )
            if form is not None and _span_inside(
                form.span, trigger_span
            ):
                covered_senses.add(sense_ref)
                app_ref_by_sense[sense_ref] = app_ref
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


def _program_symbol_aliases(plan: ConstructionSemanticPlan) -> dict[str, str]:
    symbols = {
        *(item.symbol_ref for item in plan.applications),
        *(item.symbol_ref for item in plan.variables),
        *(value for pair in plan.unifications for value in pair),
    }
    parent = {item: item for item in symbols}

    def find(item):
        parent.setdefault(item, item)
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for left, right in plan.unifications:
        union(left, right)
    return {item: find(item) for item in parent}


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
