"""Canonical runtime adapters for Phase-15/16 state, causality, impact, goals and planning."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from dataclasses import replace as dc_replace
from typing import Mapping

from ..csir.model import CSIRNodeKind, SemanticTerm, TermKind
from ..orchestration import StageExecutionStatus, StageOutcome
from ..response.goal_bridge_v351 import ConversationalGoalBridgeV351
from ..schema.model import StateDimensionSchema, semantic_fingerprint
from ..storage.model import AssignmentStatus, RecordKind, StateAssignment
from ..state.algebra_v351 import StateAlgebraV351, StateDomainCompilerV351
from ..state.capability_v351 import CapabilityDependencyRuntimeV351
from ..state.entitlement_v351 import state_value_from_document
from ..state.model_v351 import EntitledStateVariableV351, ParticipantRoleBinding, TransitionMechanismV351
from ..state.transition_v351 import CausalEventV351, StateKeyV351, StateSnapshotV351
from .engine_v351 import CausalPropagationEngine
from .explanation_v351 import ExplanationExtractor
from .goals_v351 import GoalArbitrator, goals_from_impact
from .impact_v351 import CausalImpactEngineV351
from .model_v351 import CausalQueryRequestV351, ContextSemantics, CounterfactualContext, InterventionContext
from .planning_v351 import CausalPlanner
from .authority_v351 import require_authorization_pins, require_exact_use


class Phase15CausalSimulatorV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "causal_simulator"

    def __init__(
        self, *, parameter_lookup=None, manifold_transform_resolver=None,
        set_member_type_resolver=None, simulation_budget=None,
        aggregation_selection_evaluators=None,
    ) -> None:
        self.algebra = StateAlgebraV351(
            manifold_transform_resolver=manifold_transform_resolver,
            set_member_type_resolver=set_member_type_resolver,
        )
        from ..state.transition_v351 import TransitionPreviewEngineV351
        self.preview = TransitionPreviewEngineV351(
            parameter_lookup=parameter_lookup, algebra=self.algebra,
        )
        self.simulation_budget = simulation_budget
        self.aggregation_selection_evaluators = dict(aggregation_selection_evaluators or {})

    def simulate(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del effect_store, semantic_capabilities
        authority_snapshot = cycle.artifacts.get("semantic_authority_snapshot_v351")
        # Resolve one highest non-invalidated executable revision per mechanism identity first.
        # Context and per-use authority are applied separately for each simulated world below.
        candidate_mechanisms = {}
        for item in store.records(RecordKind.TRANSITION_CONTRACT, all_revisions=True):
            payload = item.payload
            if not isinstance(payload, TransitionMechanismV351) or not payload.executable:
                continue
            if store.is_invalidated(RecordKind.TRANSITION_CONTRACT, item.record_ref, item.revision):
                continue
            if payload.permission_ref not in {"public", cycle.permission_ref}:
                continue
            current = candidate_mechanisms.get(payload.mechanism_ref)
            if current is None or payload.revision > current.revision:
                candidate_mechanisms[payload.mechanism_ref] = payload

        mechanism_authority_frontiers = []
        def mechanisms_for(context_ref):
            selected = []
            for payload in candidate_mechanisms.values():
                if payload.context_scopes and context_ref not in payload.context_scopes and "global" not in payload.context_scopes:
                    continue
                try:
                    require_exact_use(
                        authority_snapshot, payload.authority_pin, operation="transition",
                        context_ref=context_ref, permission_ref=cycle.permission_ref,
                    )
                except Exception:
                    mechanism_authority_frontiers.append(
                        "frontier:causal:mechanism-exact-transition-use-authority-required:"
                        + payload.mechanism_ref + ":" + context_ref
                    )
                    continue
                selected.append(payload)
            return tuple(sorted(selected, key=lambda item: item.authority_pin.key))

        intervention_contexts = tuple(
            item for item in tuple(cycle.artifacts.get("intervention_contexts", ()) or ())
            if isinstance(item, InterventionContext)
        )
        counterfactual_contexts = tuple(
            item for item in tuple(cycle.artifacts.get("counterfactual_contexts", ()) or ())
            if isinstance(item, CounterfactualContext)
        )
        actual_mechanisms = mechanisms_for(cycle.context_ref)
        mechanisms_by_context = {cycle.context_ref: actual_mechanisms}
        for context in intervention_contexts:
            mechanisms_by_context.setdefault(context.context_ref, mechanisms_for(context.context_ref))
        for context in counterfactual_contexts:
            mechanisms_by_context.setdefault(context.context_ref, mechanisms_for(context.context_ref))
        union_by_pin = {
            mechanism.authority_pin.key: mechanism
            for values in mechanisms_by_context.values() for mechanism in values
        }
        all_visible_mechanisms = tuple(union_by_pin[key] for key in sorted(union_by_pin))

        root_events, event_frontiers, causal_semantic_graphs = self._events_from_semantics(
            cycle, all_visible_mechanisms
        )
        # Trusted internal observation/runtime services may provide typed exogenous occurrences.
        # Raw payload text is never interpreted here; every occurrence must be a CausalEventV351,
        # explicitly marked exogenous and carry attributable evidence/proof lineage.
        exogenous_frontiers = []
        for event in tuple(cycle.artifacts.get("causal_exogenous_events", ()) or ()):
            if not isinstance(event, CausalEventV351) or event.occurrence_kind != "exogenous":
                exogenous_frontiers.append("frontier:causal:invalid-exogenous-event-artifact")
                continue
            if event.context_ref != cycle.context_ref:
                exogenous_frontiers.append(
                    "frontier:causal:exogenous-event-context-mismatch:" + event.event_ref
                )
                continue
            if not (event.evidence_refs or event.proof_refs):
                exogenous_frontiers.append(
                    "frontier:causal:exogenous-event-evidence-required:" + event.event_ref
                )
                continue
            root_events = (*root_events, event)

        if not all_visible_mechanisms:
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={
                    "transition_previews": (), "causal_simulation_results": (), "causal_proofs": (),
                    "causal_learning_evidence": (), "causal_query_results": (),
                },
                frontier_refs=tuple(sorted(set((
                    *mechanism_authority_frontiers,
                    "frontier:causal:no-active-transition-mechanism-authority",
                )))),
            )
        if not root_events and not intervention_contexts and not counterfactual_contexts:
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={
                    "transition_previews": (), "causal_simulation_results": (), "causal_proofs": (),
                    "causal_learning_evidence": (), "causal_query_results": (),
                }, frontier_refs=tuple(sorted(set((*event_frontiers, *exogenous_frontiers, *mechanism_authority_frontiers)))),
            )
        snapshot, state_frontiers = self._state_snapshot(
            cycle, store, all_visible_mechanisms, root_events=tuple(root_events), algebra=self.algebra,
        )
        def engine_for(context_ref):
            return CausalPropagationEngine(
                mechanisms=mechanisms_by_context.get(context_ref, ()), budget=self.simulation_budget,
                transition_preview_engine=self.preview,
                aggregation_selection_evaluators=self.aggregation_selection_evaluators,
            )

        simulations = []
        intervention_authority_frontiers = []
        if root_events and actual_mechanisms:
            simulations.append(engine_for(cycle.context_ref).simulate(
                initial_state=snapshot, root_events=tuple(root_events), context_semantics=ContextSemantics.ACTUAL,
            ))
        for intervention in intervention_contexts:
            try:
                for assignment in intervention.interventions:
                    require_authorization_pins(
                        authority_snapshot, assignment.authorization_pins,
                        allowed_operations=("infer", "transition"),
                        context_ref=intervention.context_ref, permission_ref=cycle.permission_ref,
                    )
            except Exception:
                intervention_authority_frontiers.append(
                    "frontier:causal:intervention-exact-use-authorization-required:" + intervention.context_ref
                )
                continue
            context_mechanisms = mechanisms_by_context.get(intervention.context_ref, ())
            if not context_mechanisms:
                intervention_authority_frontiers.append(
                    "frontier:causal:no-authorized-mechanisms-for-intervention-context:" + intervention.context_ref
                )
                continue
            simulations.append(engine_for(intervention.context_ref).simulate(
                initial_state=snapshot, root_events=tuple(root_events), context_semantics=ContextSemantics.INTERVENTION,
                intervention=intervention,
            ))
        for counterfactual in counterfactual_contexts:
            try:
                for assignment in counterfactual.intervention.interventions:
                    require_authorization_pins(
                        authority_snapshot, assignment.authorization_pins,
                        allowed_operations=("infer", "transition"),
                        context_ref=counterfactual.context_ref, permission_ref=cycle.permission_ref,
                    )
            except Exception:
                intervention_authority_frontiers.append(
                    "frontier:causal:counterfactual-exact-use-authorization-required:" + counterfactual.context_ref
                )
                continue
            context_mechanisms = mechanisms_by_context.get(counterfactual.context_ref, ())
            if not context_mechanisms:
                intervention_authority_frontiers.append(
                    "frontier:causal:no-authorized-mechanisms-for-counterfactual-context:" + counterfactual.context_ref
                )
                continue
            simulations.append(engine_for(counterfactual.context_ref).simulate(
                initial_state=snapshot, root_events=tuple(root_events), context_semantics=ContextSemantics.COUNTERFACTUAL,
                counterfactual=counterfactual,
            ))
        proofs = tuple(proof for result in simulations for proof in result.causal_proofs)
        learning = tuple(
            item for result in simulations
            for item in engine_for(result.context_ref).learning_evidence(result)
        )
        extractor = ExplanationExtractor()
        causal_queries = []
        for request in tuple(cycle.artifacts.get("causal_query_requests", ()) or ()):
            if not isinstance(request, CausalQueryRequestV351): continue
            candidates = [
                item for item in simulations
                if request.target_variable_ref in {target for proof in item.causal_proofs for target in proof.target_variable_refs}
                or (request.query_kind == "effect_of" and any(
                    request.source_variable_ref in step.source_variable_refs
                    for proof in item.causal_proofs for step in proof.steps if not step.intervention_cut
                ))
            ]
            simulation = None
            semantic_maps = dict(causal_semantic_graphs)
            semantic_maps.update(dict(cycle.artifacts.get("causal_semantic_graphs", {}) or {}))
            if request.query_kind == "why_not":
                factual = tuple(
                    item for item in candidates
                    if item.context_semantics is ContextSemantics.ACTUAL
                )
                contrasts = tuple(
                    item for item in candidates
                    if item.context_semantics in {ContextSemantics.COUNTERFACTUAL, ContextSemantics.INTERVENTION}
                    and (
                        request.intervention is None
                        or item.intervention_ref == request.intervention.context_ref
                    )
                )
                if request.intervention is None:
                    from .model_v351 import CausalQueryResultV351
                    causal_queries.append(CausalQueryResultV351(
                        result_ref="causal-query-result:" + semantic_fingerprint(
                            "causal-query-why-not-explicit-contrast-required", request.query_ref, 24,
                        ),
                        query_ref=request.query_ref, answered=False, explanation=None,
                        frontier_refs=("frontier:causal:why-not-requires-explicit-intervention-context",),
                    ))
                    continue
                if len(factual) == 1 and len(contrasts) == 1:
                    causal_queries.append(extractor.answer_why_not(
                        request, factual[0], contrasts[0], semantic_graphs=semantic_maps
                    ))
                    continue
                if len(factual) > 1 or len(contrasts) > 1:
                    from .model_v351 import CausalQueryResultV351
                    causal_queries.append(CausalQueryResultV351(
                        result_ref="causal-query-result:" + semantic_fingerprint(
                            "causal-query-why-not-context-ambiguous",
                            (request.query_ref, tuple(x.simulation_ref for x in factual),
                             tuple(x.simulation_ref for x in contrasts)), 24,
                        ),
                        query_ref=request.query_ref, answered=False, explanation=None,
                        frontier_refs=("frontier:causal:why-not-simulation-context-ambiguous",),
                    ))
                    continue
            elif request.intervention is not None:
                matches = tuple(
                    item for item in candidates
                    if item.intervention_ref == request.intervention.context_ref
                )
                simulation = matches[0] if len(matches) == 1 else None
                if len(matches) > 1:
                    from .model_v351 import CausalQueryResultV351
                    causal_queries.append(CausalQueryResultV351(
                        result_ref="causal-query-result:" + semantic_fingerprint(
                            "causal-query-intervention-context-ambiguous",
                            (request.query_ref, tuple(x.simulation_ref for x in matches)), 24,
                        ),
                        query_ref=request.query_ref, answered=False, explanation=None,
                        frontier_refs=("frontier:causal:matching-intervention-simulation-ambiguous",),
                    ))
                    continue
            else:
                matches = tuple(
                    item for item in candidates
                    if item.context_semantics is ContextSemantics.ACTUAL
                )
                simulation = matches[0] if len(matches) == 1 else None
                if len(matches) > 1:
                    from .model_v351 import CausalQueryResultV351
                    causal_queries.append(CausalQueryResultV351(
                        result_ref="causal-query-result:" + semantic_fingerprint(
                            "causal-query-actual-context-ambiguous",
                            (request.query_ref, tuple(x.simulation_ref for x in matches)), 24,
                        ),
                        query_ref=request.query_ref, answered=False, explanation=None,
                        frontier_refs=("frontier:causal:actual-simulation-context-ambiguous",),
                    ))
                    continue
            if simulation is not None:
                causal_queries.append(
                    extractor.answer(request, simulation, semantic_graphs=semantic_maps)
                )
            else:
                from .model_v351 import CausalQueryResultV351
                causal_queries.append(CausalQueryResultV351(
                    result_ref="causal-query-result:" + semantic_fingerprint(
                        "causal-query-no-matching-context",
                        (request.query_ref, request.query_kind, request.target_variable_ref), 24,
                    ),
                    query_ref=request.query_ref, answered=False, explanation=None,
                    frontier_refs=("frontier:causal:no-matching-simulation-context",),
                ))
        root_role_bindings, root_role_frontiers = self._unique_root_role_bindings(tuple(root_events))
        frontiers = tuple(sorted(set((
            *event_frontiers, *exogenous_frontiers, *state_frontiers, *root_role_frontiers,
            *mechanism_authority_frontiers, *intervention_authority_frontiers,
            *(ref for result in simulations for ref in result.frontier_refs),
        ))))
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "transition_previews": tuple(simulations),
                "causal_simulation_results": tuple(simulations),
                "causal_proofs": proofs,
                "causal_learning_evidence": learning,
                "causal_query_results": tuple(causal_queries),
                "causal_initial_state_snapshot": snapshot,
                "active_transition_mechanisms": actual_mechanisms,
                "causal_root_events": tuple(root_events),
                "causal_root_role_bindings": root_role_bindings,
                "causal_semantic_graphs": {
                    **causal_semantic_graphs,
                    **dict(cycle.artifacts.get("causal_semantic_graphs", {}) or {}),
                },
            }, frontier_refs=frontiers,
        )

    @staticmethod
    def _events_from_semantics(cycle, mechanisms):
        trigger_keys = {m.trigger_definition_pin.key for m in mechanisms if m.trigger_definition_pin is not None}
        role_requirements = {}
        for mechanism in mechanisms:
            if mechanism.trigger_definition_pin is not None:
                role_requirements.setdefault(mechanism.trigger_definition_pin.key, set()).update(pin.key for pin in mechanism.participant_role_pins)
        attractors = cycle.artifacts.get("semantic_attractors")
        values = tuple(getattr(attractors, "attractors", ()) or ())
        result, frontiers, semantic_graphs = [], [], {}
        for attractor in values:
            graph = attractor.graph
            for app in graph.applications:
                if app.predicate_pin.key not in trigger_keys: continue
                bindings = []
                for binding in graph.bindings_for(app.application_ref):
                    if binding.port_pin.key not in role_requirements.get(app.predicate_pin.key, set()): continue
                    if len(binding.fillers) != 1:
                        frontiers.append(f"frontier:causal:role-cardinality:{binding.binding_ref}"); continue
                    node = graph.node(binding.fillers[0])
                    if not isinstance(node, SemanticTerm) or node.term_kind is not TermKind.REFERENT or not node.identity_ref:
                        frontiers.append(f"frontier:causal:role-not-grounded-referent:{binding.binding_ref}"); continue
                    bindings.append(ParticipantRoleBinding(
                        role_pin=binding.port_pin, participant_ref=node.identity_ref,
                        source_application_ref=app.application_ref, participant_type_pins=tuple(node.type_pins),
                        evidence_refs=tuple(ref for proof in graph.proof_links for ref in proof.evidence_refs),
                        proof_refs=tuple(proof.proof_ref for proof in graph.proof_links),
                    ))
                event_ref = "causal-event:" + semantic_fingerprint(
                    "causal-event-from-csir-v351",
                    (
                        app.application_ref,
                        app.predicate_pin.key,
                        tuple((x.role_pin.key, x.participant_ref) for x in bindings),
                        cycle.context_ref,
                    ),
                    32,
                )
                pins = cycle.artifacts.get("_cycle_pins")
                effective_time = str(getattr(pins, "cycle_time", "") or cycle.cycle_ref)
                result.append(CausalEventV351(
                    event_ref=event_ref,
                    predicate_pin=app.predicate_pin,
                    role_bindings=tuple(bindings),
                    context_ref=cycle.context_ref,
                    effective_time_ref=effective_time,
                    evidence_refs=tuple(ref for proof in graph.proof_links for ref in proof.evidence_refs),
                    proof_refs=tuple(proof.proof_ref for proof in graph.proof_links),
                    occurrence_kind="actual",
                ))
                # Preserve the original CSIR occurrence as the semantic cause surface/proof
                # source, with this application as the sole root. No new causal wording or
                # semantic paraphrase is invented here.
                semantic_graphs[event_ref] = dc_replace(graph, root_refs=(app.node_ref,))
        return tuple(result), tuple(frontiers), semantic_graphs

    @staticmethod
    def _unique_root_role_bindings(root_events):
        """Return only unambiguous exact role→participant bindings for impact projection.

        Multiple root events may bind the same semantic role to different participants. That
        ambiguity must not be collapsed by dictionary overwrite; the affected impact rule simply
        remains unresolved until a more specific exact projection is supplied.
        """
        by_role = {}
        ambiguous = set()
        for event in root_events:
            for binding in event.role_bindings:
                key = binding.role_pin.key
                prior = by_role.get(key)
                if prior is None:
                    by_role[key] = binding.participant_ref
                elif prior != binding.participant_ref:
                    ambiguous.add(key)
        mapping = {key: value for key, value in by_role.items() if key not in ambiguous}
        frontiers = tuple("frontier:impact:ambiguous-root-role:" + str(key) for key in sorted(ambiguous))
        return mapping, frontiers

    @staticmethod
    def _state_snapshot(cycle, store, mechanisms, *, root_events=(), algebra=None):
        algebra = algebra or StateAlgebraV351()
        holders = {
            binding.participant_ref
            for event in root_events
            for binding in event.role_bindings
        }
        # Explicit intervention targets may introduce holders not present in a triggering event.
        for context in tuple(cycle.artifacts.get("intervention_contexts", ()) or ()):
            if isinstance(context, InterventionContext):
                holders.update(item.variable.holder_ref for item in context.interventions)
        for context in tuple(cycle.artifacts.get("counterfactual_contexts", ()) or ()):
            if isinstance(context, CounterfactualContext):
                holders.update(item.variable.holder_ref for item in context.intervention.interventions)
        dimension_pins = {}
        for m in mechanisms:
            for pin in m.source_dimension_pins: dimension_pins[pin.key]=pin
            for cond in m.preconditions: dimension_pins[cond.dimension_pin.key]=cond.dimension_pin
            for transform in (*m.deterministic_transforms, *(t for b in m.branches for t in b.transforms)):
                dimension_pins[transform.dimension_pin.key]=transform.dimension_pin
        domains=[]; values=[]; frontiers=[]
        for pin in dimension_pins.values():
            stored=store.get_record(RecordKind.SCHEMA,pin.ref,pin.revision)
            if stored is None or not isinstance(stored.payload,StateDimensionSchema):
                frontiers.append(f"frontier:state:dimension-authority-missing:{pin.ref}@{pin.revision}"); continue
            dimension=stored.payload
            domain=StateDomainCompilerV351.compile(dimension)
            domains.append((pin.key,domain))
            for holder in holders:
                candidates=[item.payload for item in store.records(RecordKind.STATE_ASSIGNMENT) if isinstance(item.payload,StateAssignment) and item.payload.holder_ref==holder and item.payload.dimension_ref==pin.ref and item.payload.dimension_revision==pin.revision and item.payload.context_ref in {"global",cycle.context_ref} and item.payload.status==AssignmentStatus.ACTIVE]
                exact=[item for item in candidates if item.context_ref==cycle.context_ref]
                fallback=[item for item in candidates if item.context_ref=="global"]
                selected=exact if exact else fallback
                if len(selected)>1:
                    # Multi-valued rich domains are represented inside one typed value. Never
                    # choose a current assignment by repository ordering.
                    frontiers.append(f"frontier:state:multiple-active-assignments:{holder}:{pin.ref}"); continue
                if selected:
                    assignment=selected[0]
                    try:
                        if getattr(assignment,"value_document",{}): value=state_value_from_document(assignment.value_document)
                        else:
                            from ..state.entitlement_v351 import EntitledStateSpaceCompilerV351
                            value=EntitledStateSpaceCompilerV351.assignment_value(assignment,dimension,store=store)
                        algebra.validate_value(domain, value)
                        values.append((StateKeyV351(holder,pin,cycle.context_ref),value))
                    except Exception as exc:
                        frontiers.append(f"frontier:state:value-decode:{holder}:{pin.ref}:{type(exc).__name__}")
        return StateSnapshotV351(tuple(values),tuple(domains)),tuple(frontiers)


class Phase16ImpactRuntimeV351:
    RUNTIME_ABI="v351"; SERVICE_KIND="impact_engine"
    def __init__(
        self, rules=(), *, capability_leaf_resolver=None,
        manifold_transform_resolver=None, set_member_type_resolver=None,
    ):
        self.engine=CausalImpactEngineV351(rules)
        algebra=StateAlgebraV351(
            manifold_transform_resolver=manifold_transform_resolver,
            set_member_type_resolver=set_member_type_resolver,
        )
        self.capabilities=CapabilityDependencyRuntimeV351(
            external_leaf_resolver=capability_leaf_resolver, algebra=algebra,
        )

    def propagate(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability,effect_store,semantic_capabilities
        from .model_v351 import ContextSemantics
        authority_snapshot = cycle.artifacts.get("semantic_authority_snapshot_v351")
        authorized_rules = []
        impact_frontiers = []
        for rule in self.engine.rules:
            if not rule.executable:
                continue
            try:
                require_exact_use(
                    authority_snapshot, rule.authority_pin, operation="impact",
                    context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                )
            except Exception:
                impact_frontiers.append("frontier:impact:exact-use-authority-required:" + rule.rule_ref)
                continue
            authorized_rules.append(rule)
        impact_engine = CausalImpactEngineV351(tuple(authorized_rules))
        all_impacts=tuple(
            x for simulation in tuple(cycle.artifacts.get("causal_simulation_results",()) or ())
            for x in impact_engine.derive(
                simulation, role_bindings=dict(cycle.artifacts.get("causal_root_role_bindings", {}) or {})
            )
        )
        actual=tuple(item for item in all_impacts if item.context_semantics is ContextSemantics.ACTUAL)
        simulated=tuple(item for item in all_impacts if item.context_semantics is not ContextSemantics.ACTUAL)
        capability_assessments, capability_deltas, capability_frontiers = self.capabilities.evaluate(
            store, context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            authority_snapshot=authority_snapshot,
        )
        return {
            "impact_vectors":actual,
            "impact_assessments":actual,
            "causal_simulated_impact_vectors":simulated,
            "capability_assessments_v351":capability_assessments,
            "capability_deltas":capability_deltas,
            "affect_estimates":(),"significance_assessments":(),
            "frontier_refs":tuple(sorted(set((*capability_frontiers, *impact_frontiers)))),
        }


class CompositeGoalArbitratorV351:
    RUNTIME_ABI="v351"; SERVICE_KIND="goal_engine"
    def __init__(self, *, policy=None):
        self.causal=GoalArbitrator(policy); self.conversational=ConversationalGoalBridgeV351()
    def arbitrate(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        causal_response=self.causal.run(
            cycle=cycle, capability=capability, store=store, effect_store=effect_store,
            semantic_capabilities=semantic_capabilities,
        )
        impact_goals=goals_from_impact(tuple(cycle.artifacts.get("impact_vectors",()) or ()))
        causal_decision=self.causal.arbitrate(
            impact_goals, context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            authority_snapshot=cycle.artifacts.get("semantic_authority_snapshot_v351"),
        ) if impact_goals else None
        if causal_response.get("goal_decision") is not None:
            causal_response=dict(causal_response)
            causal_response["causal_goal_candidates"]=impact_goals
            causal_response["causal_goal_decision"]=causal_decision
            return causal_response
        ordinary=self.conversational.arbitrate(
            cycle=cycle, capability=capability, store=store, effect_store=effect_store,
            semantic_capabilities=semantic_capabilities,
        )
        if hasattr(ordinary, "artifacts"):
            ordinary = dict(ordinary.artifacts)
        else:
            ordinary = dict(ordinary)
        ordinary["causal_goal_candidates"]=impact_goals
        ordinary["causal_goal_decision"]=causal_decision
        return ordinary


class CausalPlanningOperationEngineV351:
    """Stage-16 causal planner adapter. Planning never implies operation authorization."""
    RUNTIME_ABI="v351"; SERVICE_KIND="operation_engine"
    def __init__(
        self, *, utility_evaluator=None, utility_policy_pin=None, parameter_lookup=None,
        manifold_transform_resolver=None, set_member_type_resolver=None, simulation_budget=None,
        aggregation_selection_evaluators=None,
    ):
        self.utility_evaluator=utility_evaluator
        self.utility_policy_pin=utility_policy_pin
        self.algebra=StateAlgebraV351(
            manifold_transform_resolver=manifold_transform_resolver,
            set_member_type_resolver=set_member_type_resolver,
        )
        from ..state.transition_v351 import TransitionPreviewEngineV351
        self.preview=TransitionPreviewEngineV351(
            parameter_lookup=parameter_lookup, algebra=self.algebra,
        )
        self.simulation_budget=simulation_budget
        self.aggregation_selection_evaluators=dict(aggregation_selection_evaluators or {})
    def prepare(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability,effect_store,semantic_capabilities
        precomputed=tuple(cycle.artifacts.get("causal_plan_candidates",()) or ())
        if precomputed:
            return {"plans":precomputed,"effect_authorizations":(),"operation_journals":(),"authorized_operations":(),"frontier_refs":()}
        goal_decision=cycle.artifacts.get("causal_goal_decision")
        actions=tuple(cycle.artifacts.get("action_candidates",()) or ())
        initial_state=cycle.artifacts.get("causal_initial_state_snapshot")
        mechanisms=tuple(cycle.artifacts.get("active_transition_mechanisms",()) or ())
        if goal_decision is None or not getattr(goal_decision,"selected_goal_refs",()):
            return {"plans":(),"effect_authorizations":(),"operation_journals":(),"authorized_operations":(),"frontier_refs":("frontier:planning:no-selected-causal-goal",)}
        action_frontiers=[]
        authorized_actions=[]
        authority_snapshot=cycle.artifacts.get("semantic_authority_snapshot_v351")
        for action in actions:
            try:
                require_exact_use(
                    authority_snapshot, action.action_schema_pin, operation="plan",
                    context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                )
            except Exception:
                action_frontiers.append(
                    "frontier:planning:action-exact-plan-use-authority-required:" + action.action_ref
                )
                continue
            authorized_actions.append(action)
        actions=tuple(authorized_actions)
        if not actions or initial_state is None or not mechanisms:
            return {
                "plans":(),"effect_authorizations":(),"operation_journals":(),"authorized_operations":(),
                "frontier_refs":tuple(sorted(set((
                    *action_frontiers,
                    "frontier:planning:action-state-or-mechanism-substrate-missing",
                )))),
            }
        if not callable(self.utility_evaluator) or self.utility_policy_pin is None:
            return {"plans":(),"effect_authorizations":(),"operation_journals":(),"authorized_operations":(),"frontier_refs":("frontier:planning:exact-utility-evaluator-and-policy-required",)}
        try:
            require_exact_use(
                cycle.artifacts.get("semantic_authority_snapshot_v351"), self.utility_policy_pin,
                operation="plan", context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            )
        except Exception:
            return {"plans":(),"effect_authorizations":(),"operation_journals":(),"authorized_operations":(),"frontier_refs":("frontier:planning:exact-utility-policy-use-authority-required",)}
        planner=CausalPlanner(CausalPropagationEngine(
            mechanisms=mechanisms, budget=self.simulation_budget,
            transition_preview_engine=self.preview,
            aggregation_selection_evaluators=self.aggregation_selection_evaluators,
        ))
        decision=planner.plan(
            goal_decision=goal_decision, action_candidates=actions, initial_state=initial_state,
            utility_evaluator=self.utility_evaluator, context_ref=cycle.context_ref,
        )
        plans=decision.candidates
        # Even an executable causal plan is only semantically eligible. The existing Stage-16
        # effect gate still requires exact adapter/policy/journal authorization before I/O.
        return {
            "plans":plans,"causal_plan_decision":decision,"effect_authorizations":(),
            "operation_journals":(),"authorized_operations":(),
            "frontier_refs":tuple(sorted(set((*decision.frontier_refs, *action_frontiers)))),
        }
    def execute(self, *, cycle, capability, store, effect_store, prepared, operation_effect_receipts):
        del cycle,capability,store,effect_store,operation_effect_receipts
        return {"operation_journals":tuple(prepared.get("operation_journals",()) or ()),"operation_observations":(),"frontier_refs":tuple(prepared.get("frontier_refs",()) or ())}


__all__=["CausalPlanningOperationEngineV351","CompositeGoalArbitratorV351","Phase15CausalSimulatorV351","Phase16ImpactRuntimeV351"]
