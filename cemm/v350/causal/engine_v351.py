"""Bounded structural causal propagation, intervention and counterfactual simulation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from ..schema.model import semantic_fingerprint
from ..state.model_v351 import OperandKind, ParticipantRoleBinding, StateDeltaV351, TransitionMechanismV351
from ..state.transition_v351 import CausalEventV351, StateKeyV351, StateSnapshotV351, TransitionPreviewEngineV351
from .model_v351 import (
    CausalLearningEvidenceV351, CausalModelError, CausalProofStepV351, CausalProofV351,
    CausalSimulationBranchV351, CausalSimulationResultV351, CausalVariable, ContextSemantics,
    CounterfactualContext, InterventionContext, SimulationBudgetV351,
)


@dataclass(frozen=True, slots=True)
class MechanismCatalogV351:
    mechanisms: tuple[TransitionMechanismV351, ...]

    def event_mechanisms(self, predicate_pin):
        return tuple(
            item for item in self.mechanisms
            if item.executable and item.trigger_definition_pin is not None
            and item.trigger_definition_pin.key == predicate_pin.key
        )

    def state_mechanisms(self, dimension_pin):
        return tuple(
            item for item in self.mechanisms
            if item.executable and dimension_pin.key in {pin.key for pin in item.source_dimension_pins}
        )


@dataclass
class _BranchWork:
    branch_ref: str
    probability: float
    confidence: float
    snapshot: StateSnapshotV351
    queue: list[CausalEventV351]
    deltas: list[StateDeltaV351]
    secondary_refs: list[str]
    proof_steps: list[CausalProofStepV351]
    frontiers: list[str]
    seen: set[tuple]
    depth: int = 0
    resolved: bool = True


class CausalPropagationEngine:
    """One causal engine for prediction, explanation, learning and planning.

    It performs no durable writes.  Stage 13 is the only commit boundary.  Interventions
    cut incoming mechanisms to their target variables; observations never do.
    """

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "causal_propagation_engine_v351"

    def __init__(
        self, *, mechanisms: Iterable[TransitionMechanismV351] = (),
        budget: SimulationBudgetV351 | None = None,
        transition_preview_engine: TransitionPreviewEngineV351 | None = None,
        aggregation_selection_evaluators: Mapping[str, object] | None = None,
    ):
        self.catalog = MechanismCatalogV351(tuple(mechanisms))
        self.budget = budget or SimulationBudgetV351()
        self.preview = transition_preview_engine or TransitionPreviewEngineV351()
        self.aggregation_selection_evaluators = dict(aggregation_selection_evaluators or {})

    def simulate(
        self,
        *,
        initial_state: StateSnapshotV351,
        root_events: tuple[CausalEventV351, ...],
        context_semantics: ContextSemantics,
        intervention: InterventionContext | None = None,
        counterfactual: CounterfactualContext | None = None,
        budget: SimulationBudgetV351 | None = None,
    ) -> CausalSimulationResultV351:
        budget = budget or self.budget
        if counterfactual is not None:
            if context_semantics != ContextSemantics.COUNTERFACTUAL:
                raise CausalModelError("CounterfactualContext requires counterfactual semantics")
            if not counterfactual.exogenous_assumptions and not counterfactual.proof_refs:
                # Do not pretend the abduction step succeeded when latent/exogenous state is
                # not identifiable from the evidence and an inverse model was not supplied.
                return CausalSimulationResultV351(
                    simulation_ref="causal-simulation:" + semantic_fingerprint(
                        "counterfactual-unresolved-abduction", (counterfactual.context_ref, counterfactual.factual_evidence_refs), 32,
                    ),
                    context_ref=counterfactual.context_ref,
                    context_semantics=context_semantics,
                    branches=(), causal_proofs=(), final_state_refs=(),
                    frontier_refs=("frontier:causal:counterfactual-abduction-unresolved",),
                    intervention_ref=counterfactual.intervention.context_ref,
                    actual_state_unchanged=True,
                )
            intervention = counterfactual.intervention

        isolation_context = (
            intervention.context_ref if intervention is not None
            else (
                root_events[0].context_ref
                if root_events and context_semantics is not ContextSemantics.ACTUAL
                else None
            )
        )
        source_context = (
            counterfactual.factual_context_ref
            if counterfactual is not None
            else intervention.parent_context_ref if intervention is not None
            else isolation_context
        )
        state = self._isolate_context(
            initial_state, isolation_context, source_context_ref=source_context
        )
        if counterfactual is not None:
            # Abduction result: hold inferred exogenous/background values fixed in the
            # isolated counterfactual world before replacing targeted structural equations.
            for assumption in counterfactual.exogenous_assumptions:
                domain = state.domain(assumption.variable.dimension_pin)
                self.preview.algebra.validate_value(domain, assumption.value)
                state = state.with_value(
                    assumption.variable.holder_ref,
                    assumption.variable.dimension_pin,
                    counterfactual.context_ref,
                    assumption.value,
                )
        cut_keys = frozenset()
        intervention_ref = ""
        intervention_events = ()
        if intervention is not None:
            intervention_ref = intervention.context_ref
            cut_keys = intervention.cut_target_keys
            state, intervention_events = self._apply_interventions(state, intervention)

        simulation_context_ref = (
            intervention.context_ref
            if intervention is not None
            else (root_events[0].context_ref if root_events else "actual")
        )
        contextual_root_events = tuple(
            replace(
                event, context_ref=simulation_context_ref,
                occurrence_kind=(
                    "counterfactual" if context_semantics is ContextSemantics.COUNTERFACTUAL
                    else "interventional" if context_semantics is ContextSemantics.INTERVENTION
                    else "planned" if context_semantics is ContextSemantics.PLANNING
                    else event.occurrence_kind
                ),
            )
            for event in root_events
        )
        seed = _BranchWork(
            branch_ref="causal-branch:root",
            probability=1.0, confidence=1.0, snapshot=state,
            queue=list((*intervention_events, *contextual_root_events)), deltas=[], secondary_refs=[], proof_steps=[], frontiers=[], seen=set(), depth=0,
        )
        active = [seed]
        completed: list[_BranchWork] = []
        exhausted = False
        event_count = 0
        delta_count = 0
        simulation_frontiers: set[str] = set()

        while active:
            work = active.pop(0)
            if not work.queue:
                completed.append(work)
                continue
            next_event = work.queue[0]
            if next_event.causal_depth >= budget.maximum_depth:
                work.frontiers.append("frontier:causal:maximum-depth")
                work.resolved = False
                completed.append(work); exhausted = True; continue
            if next_event.time_step > budget.maximum_time_step:
                work.frontiers.append("frontier:causal:maximum-time-horizon")
                work.resolved = False
                completed.append(work); exhausted = True; continue
            if len(work.proof_steps) >= budget.maximum_proof_steps:
                work.frontiers.append("frontier:causal:proof-step-budget-exhausted")
                work.resolved = False
                completed.append(work); exhausted = True; continue
            if event_count >= budget.maximum_events or delta_count >= budget.maximum_deltas:
                work.frontiers.append("frontier:causal:budget-exhausted")
                work.resolved = False
                completed.append(work); exhausted = True; continue
            event = work.queue.pop(0); event_count += 1
            cycle_key = (
                event.occurrence_kind,
                event.predicate_pin.key,
                None if event.source_delta is None else event.source_delta.delta_ref,
                tuple((r.role_pin.key, r.participant_ref) for r in event.role_bindings),
                event.context_ref,
                event.time_step,
            )
            if cycle_key in work.seen:
                # Skip only the repeated causal event. Other independent queued effects on the
                # same branch remain eligible; cycle detection is not a branch-wide abort.
                work.frontiers.append("frontier:causal:cycle-detected")
                work.resolved = False
                work.depth += 1
                active.append(work)
                continue
            work.seen.add(cycle_key)

            if event.source_delta is not None:
                preview = self.preview.preview_state_change(
                    source_delta=event.source_delta,
                    role_bindings=event.role_bindings,
                    mechanisms=self.catalog.state_mechanisms(event.source_delta.dimension_pin),
                    snapshot=work.snapshot,
                    time_step=event.time_step,
                )
            else:
                preview = self.preview.preview_event(event, self.catalog.mechanisms, work.snapshot)
            work.frontiers.extend(preview.frontier_refs)
            if preview.frontier_refs:
                work.resolved = False
            if not preview.distributions:
                work.depth += 1
                active.append(work)
                continue

            expanded, unresolved = self._expand_distributions(
                work, event, preview.distributions, cut_keys, budget
            )
            simulation_frontiers.update(unresolved)
            delta_count += sum(len(item.deltas) - len(work.deltas) for item in expanded)
            active.extend(expanded)
            if len(active) + len(completed) > budget.maximum_branches:
                remaining = max(0, budget.maximum_branches - len(completed))
                ranked = sorted(
                    active, key=lambda item: item.probability * item.confidence, reverse=True
                )
                discarded = ranked[remaining:]
                active = ranked[:remaining]
                if discarded:
                    simulation_frontiers.add("frontier:causal:branch-budget-pruned")
                    for item in active:
                        item.frontiers.append("frontier:causal:branch-budget-pruned")
                exhausted = True

        branches = []
        proofs = []
        final_refs = set()
        all_frontiers = set(simulation_frontiers)
        for work in completed:
            proof = CausalProofV351(
                proof_ref="causal-proof:" + semantic_fingerprint(
                    "causal-proof-v351", (work.branch_ref, tuple(step.step_ref for step in work.proof_steps), context_semantics.value, intervention_ref), 40,
                ),
                context_ref=(intervention.context_ref if intervention else (root_events[0].context_ref if root_events else "actual")),
                context_semantics=context_semantics,
                steps=tuple(work.proof_steps),
                root_trigger_refs=tuple(item.event_ref for item in (*intervention_events, *contextual_root_events)),
                target_variable_refs=tuple(sorted({step.target_variable_ref for step in work.proof_steps if step.target_variable_ref})),
                intervention_ref=intervention_ref,
                exogenous_assumption_refs=(() if counterfactual is None else tuple(item.assumption_ref for item in counterfactual.exogenous_assumptions)),
                evidence_refs=tuple(sorted({
                    ref for event in (*intervention_events, *contextual_root_events)
                    for ref in event.evidence_refs
                })),
                frontier_refs=tuple(sorted(set(work.frontiers))),
            )
            proofs.append(proof)
            for key, value in work.snapshot.values:
                final_refs.add(value.value_ref)
            all_frontiers.update(work.frontiers)
            branches.append(CausalSimulationBranchV351(
                branch_ref=work.branch_ref,
                probability=work.probability,
                confidence=work.confidence,
                proof_ref=proof.proof_ref,
                state_deltas=tuple(work.deltas),
                secondary_event_refs=tuple(work.secondary_refs),
                proof_step_refs=tuple(step.step_ref for step in work.proof_steps),
                resolved=work.resolved,
                frontier_refs=tuple(sorted(set(work.frontiers))),
            ))
        return CausalSimulationResultV351(
            simulation_ref="causal-simulation:" + semantic_fingerprint(
                "causal-simulation-v351",
                (context_semantics.value, tuple(item.event_ref for item in root_events), intervention_ref,
                 tuple((b.branch_ref, b.probability, b.proof_step_refs) for b in branches)), 40,
            ),
            context_ref=(intervention.context_ref if intervention else (root_events[0].context_ref if root_events else "actual")),
            context_semantics=context_semantics,
            branches=tuple(branches), causal_proofs=tuple(proofs),
            final_state_refs=tuple(sorted(final_refs)), frontier_refs=tuple(sorted(all_frontiers)),
            budget_exhausted=exhausted, intervention_ref=intervention_ref, actual_state_unchanged=True,
            unresolved_probability_mass=max(0.0, min(1.0, 1.0 - sum(
                item.probability for item in branches if item.resolved
            ))),
        )

    def _expand_distributions(self, work, event, distributions, cut_keys, budget):
        # Competing mechanisms that write the same target variable in one causal step are not
        # silently overwritten. They require an explicit shared aggregation contract.
        targets = {}
        for dist in distributions:
            mechanism = next((m for m in self.catalog.mechanisms if m.authority_pin.key == dist.mechanism_pin.key), None)
            for _, _, deltas, _, _ in dist.branches:
                for delta in deltas:
                    target = (delta.holder_ref, delta.dimension_pin.key, delta.context_ref)
                    targets.setdefault(target, []).append(mechanism)
        conflicts = [items for items in targets.values() if len({m.authority_pin.key for m in items if m}) > 1]
        if conflicts:
            contract_pins = {
                m.aggregation_contract_pin.key: m.aggregation_contract_pin
                for items in conflicts for m in items
                if m is not None and m.aggregation_contract_pin is not None
            }
            conflict_mechanisms = {
                m.authority_pin.key for items in conflicts for m in items if m is not None
            }
            if len(contract_pins) != 1 or any(
                m is None or m.aggregation_contract_pin is None
                for items in conflicts for m in items
            ):
                work.frontiers.append("frontier:causal:competing-mechanisms-require-exact-aggregation-contract")
                work.resolved = False
                return [work], (work.frontiers[-1],)
            contract_pin = next(iter(contract_pins.values()))
            evaluator = self.aggregation_selection_evaluators.get(contract_pin.key)
            if not callable(evaluator):
                work.frontiers.append(
                    "frontier:causal:aggregation-evaluator-required:" + contract_pin.ref
                )
                work.resolved = False
                return [work], (work.frontiers[-1],)
            selected_refs = tuple(evaluator(
                aggregation_contract_pin=contract_pin, event=event, snapshot=work.snapshot,
                distributions=tuple(distributions), conflict_mechanism_keys=tuple(sorted(conflict_mechanisms)),
            ) or ())
            if not selected_refs or len(selected_refs) != len(set(selected_refs)):
                work.frontiers.append("frontier:causal:aggregation-selection-invalid")
                work.resolved = False
                return [work], (work.frontiers[-1],)
            by_ref = {item.distribution_ref: item for item in distributions}
            if any(ref not in by_ref for ref in selected_refs):
                work.frontiers.append("frontier:causal:aggregation-selection-outside-authorized-distributions")
                work.resolved = False
                return [work], (work.frontiers[-1],)
            distributions = tuple(by_ref[ref] for ref in selected_refs)
            # Bind the exact aggregation-policy authority into every selected transition proof
            # without turning it into a frontier. Downstream causal proof steps inherit these
            # proof/evidence warrants, so selection authority remains auditable.
            distributions = tuple(
                replace(
                    dist,
                    branches=tuple(
                        (branch_ref, probability, deltas, secondary, replace(
                            proof, evidence_refs=tuple(sorted(set((
                                *proof.evidence_refs, _authority_ref(contract_pin),
                            )))),
                        ))
                        for branch_ref, probability, deltas, secondary, proof in dist.branches
                    ),
                )
                for dist in distributions
            )
            # Selection may only choose already proof-bearing distributions. Verify the exact
            # conflict is actually gone; a callback cannot smuggle an implicit overwrite policy.
            selected_targets = {}
            for dist in distributions:
                for _, _, deltas, _, _ in dist.branches:
                    for delta in deltas:
                        target = (delta.holder_ref, delta.dimension_pin.key, delta.context_ref)
                        selected_targets.setdefault(target, set()).add(dist.mechanism_pin.key)
            if any(len(keys) > 1 for keys in selected_targets.values()):
                work.frontiers.append("frontier:causal:aggregation-selection-still-conflicting")
                work.resolved = False
                return [work], (work.frontiers[-1],)

        stochastic = [
            (dist, next((m for m in self.catalog.mechanisms if m.authority_pin.key == dist.mechanism_pin.key), None))
            for dist in distributions if len(dist.branches) > 1
        ]
        if len(stochastic) > 1:
            independence = [
                None if mechanism is None else mechanism.stochastic_independence_pin
                for _dist, mechanism in stochastic
            ]
            keys = {None if pin is None else pin.key for pin in independence}
            if None in keys or len(keys) != 1:
                work.frontiers.append(
                    "frontier:causal:joint-stochastic-composition-requires-exact-independence-contract"
                )
                work.resolved = False
                return [work], ("frontier:causal:joint-stochastic-composition-requires-exact-independence-contract",)

        combinations = [work]
        unresolved_frontiers = []
        for dist in distributions:
            next_comb = []
            for base in combinations:
                created = []
                pruned_frontiers = []
                for branch_ref, probability, deltas, secondary, proof in dist.branches:
                    p = base.probability * probability
                    if p < budget.minimum_branch_probability:
                        pruned_frontiers.append(
                            "frontier:causal:minimum-branch-probability-pruned:" + branch_ref
                        )
                        continue
                    clone = _clone(base, suffix=branch_ref, probability=p)
                    parent_steps = tuple(step.step_ref for step in clone.proof_steps)
                    for delta in deltas:
                        if len(clone.proof_steps) >= budget.maximum_proof_steps:
                            clone.frontiers.append("frontier:causal:proof-step-budget-exhausted")
                            clone.resolved = False
                            continue
                        target_key = (delta.holder_ref, delta.dimension_pin.key, delta.context_ref)
                        if target_key in cut_keys:
                            variable_ref = _variable_ref(
                                delta.holder_ref, delta.dimension_pin, delta.context_ref, delta.time_step
                            )
                            mechanism = next(
                                (m for m in self.catalog.mechanisms if m.authority_pin.key == dist.mechanism_pin.key),
                                None,
                            )
                            source_vars = self._mechanism_source_variables(
                                mechanism, event, context_ref=delta.context_ref
                            )
                            cut_step = CausalProofStepV351(
                                step_ref="causal-proof-step:" + semantic_fingerprint(
                                    "causal-intervention-cut-step-v351",
                                    (proof.proof_ref, delta.delta_ref, variable_ref, tuple(sorted(cut_keys))), 32,
                                ),
                                mechanism_pin=dist.mechanism_pin,
                                source_variable_refs=source_vars,
                                source_event_refs=(event.event_ref,),
                                target_variable_ref=variable_ref,
                                trigger_ref=event.event_ref,
                                branch_probability=p,
                                confidence=delta.confidence,
                                warrant_refs=(proof.proof_ref, *proof.evidence_refs),
                                role_bindings=proof.role_bindings,
                                suppressed_delta_ref=delta.delta_ref,
                                parent_step_refs=event.causal_parent_step_refs,
                                intervention_cut=True,
                            )
                            clone.proof_steps.append(cut_step)
                            continue
                        current = clone.snapshot.value(delta.holder_ref, delta.dimension_pin, delta.context_ref)
                        # A preview is valid only against the branch pre-state it was derived from.
                        if (None if current is None else current.value_ref) != (None if delta.prior_value is None else delta.prior_value.value_ref):
                            clone.frontiers.append(f"frontier:causal:prestate-drift:{delta.delta_ref}")
                            clone.resolved = False
                            continue
                        delta = replace(delta, branch_probability=p)
                        clone.snapshot = clone.snapshot.with_value(delta.holder_ref, delta.dimension_pin, delta.context_ref, delta.new_value)
                        clone.deltas.append(delta)
                        clone.confidence = min(clone.confidence, delta.confidence)
                        variable_ref = _variable_ref(
                            delta.holder_ref, delta.dimension_pin, delta.context_ref, delta.time_step
                        )
                        mechanism = next(
                            (m for m in self.catalog.mechanisms if m.authority_pin.key == dist.mechanism_pin.key),
                            None,
                        )
                        source_vars = self._mechanism_source_variables(
                            mechanism, event, context_ref=delta.context_ref
                        )
                        step = CausalProofStepV351(
                            step_ref="causal-proof-step:" + semantic_fingerprint(
                                "causal-proof-step-v351", (proof.proof_ref, delta.delta_ref, variable_ref), 32,
                            ),
                            mechanism_pin=dist.mechanism_pin,
                            source_variable_refs=source_vars,
                            source_event_refs=(event.event_ref,),
                            target_variable_ref=variable_ref,
                            trigger_ref=event.event_ref,
                            branch_probability=p,
                            confidence=delta.confidence,
                            warrant_refs=(proof.proof_ref, *proof.evidence_refs),
                            role_bindings=proof.role_bindings,
                            delta_ref=delta.delta_ref,
                            prior_value_ref=("" if delta.prior_value is None else delta.prior_value.value_ref),
                            new_value_ref=("" if delta.new_value is None else delta.new_value.value_ref),
                            parent_step_refs=event.causal_parent_step_refs,
                        )
                        clone.proof_steps.append(step)
                        # Reify the derived state change into the causal queue. This preserves
                        # stochastic branching/probability mass and gives state-triggered
                        # mechanisms the same budgets, cycle checks, interventions and proofs
                        # as event-triggered mechanisms.
                        if self.catalog.state_mechanisms(delta.dimension_pin):
                            clone.queue.append(CausalEventV351(
                                event_ref="causal-state-event:" + semantic_fingerprint(
                                    "causal-state-event-v351",
                                    (delta.delta_ref, event.event_ref, event.time_step + 1),
                                    32,
                                ),
                                predicate_pin=delta.mechanism_pin,
                                role_bindings=event.role_bindings,
                                context_ref=delta.context_ref,
                                effective_time_ref=delta.effective_time_ref,
                                time_step=event.time_step + 1,
                                causal_depth=event.causal_depth + 1,
                                proof_refs=tuple(sorted(set((proof.proof_ref, *delta.proof_refs)))),
                                occurrence_kind="derived_state_change",
                                source_delta=delta,
                                causal_parent_step_refs=(step.step_ref,),
                            ))
                    for se in secondary:
                        if len(clone.proof_steps) >= budget.maximum_proof_steps:
                            clone.frontiers.append("frontier:causal:proof-step-budget-exhausted")
                            clone.resolved = False
                            continue
                        mechanism = next(
                            (m for m in self.catalog.mechanisms if m.authority_pin.key == dist.mechanism_pin.key),
                            None,
                        )
                        secondary_step = CausalProofStepV351(
                            step_ref="causal-proof-step:" + semantic_fingerprint(
                                "causal-secondary-event-step-v351",
                                (proof.proof_ref, se.event_ref, event.event_ref),
                                32,
                            ),
                            mechanism_pin=dist.mechanism_pin,
                            source_variable_refs=self._mechanism_source_variables(
                                mechanism, event, context_ref=se.context_ref
                            ),
                            source_event_refs=(event.event_ref,),
                            target_variable_ref="",
                            trigger_ref=event.event_ref,
                            branch_probability=p,
                            confidence=clone.confidence,
                            warrant_refs=(proof.proof_ref, *proof.evidence_refs),
                            role_bindings=se.role_bindings,
                            secondary_event_ref=se.event_ref,
                            parent_step_refs=event.causal_parent_step_refs,
                        )
                        clone.proof_steps.append(secondary_step)
                        clone.queue.append(CausalEventV351(
                            event_ref=se.event_ref, predicate_pin=se.event_definition_pin,
                            role_bindings=se.role_bindings, context_ref=se.context_ref,
                            effective_time_ref=event.effective_time_ref, time_step=se.time_step,
                            causal_depth=event.causal_depth + 1,
                            proof_refs=se.proof_refs, occurrence_kind="secondary",
                            causal_parent_step_refs=(secondary_step.step_ref,),
                        ))
                        clone.secondary_refs.append(se.event_ref)
                    clone.depth = max(clone.depth, event.causal_depth + 1)
                    if clone.confidence < budget.minimum_confidence:
                        pruned_frontiers.append(
                            "frontier:causal:minimum-confidence-pruned:" + branch_ref
                        )
                        continue
                    created.append(clone)
                if pruned_frontiers:
                    unresolved_frontiers.extend(pruned_frontiers)
                    for clone in created:
                        clone.frontiers.extend(pruned_frontiers)
                next_comb.extend(created)
            combinations = next_comb
        return combinations, tuple(sorted(set(unresolved_frontiers)))

    @staticmethod
    def _mechanism_source_variables(
        mechanism: TransitionMechanismV351 | None,
        event: CausalEventV351,
        *,
        context_ref: str,
    ) -> tuple[str, ...]:
        """Return only state variables structurally read by the exact mechanism.

        Event occurrence itself is preserved separately in `source_event_refs`; participant
        identity must never be reinterpreted as a change in the target state dimension.
        """
        refs = set()
        role_map = {binding.role_pin.key: binding.participant_ref for binding in event.role_bindings}
        if event.source_delta is not None:
            refs.add(_variable_ref(
                event.source_delta.holder_ref,
                event.source_delta.dimension_pin,
                event.source_delta.context_ref,
                max(0, event.source_delta.time_step - 1),
            ))
        if mechanism is not None:
            for condition in mechanism.preconditions:
                holder = role_map.get(condition.holder_role_pin.key)
                if holder:
                    refs.add(_variable_ref(holder, condition.dimension_pin, context_ref, event.time_step))
            transforms = [
                *mechanism.deterministic_transforms,
                *(transform for branch in mechanism.branches for transform in branch.transforms),
            ]
            for transform in transforms:
                for operand in transform.expression.operands:
                    if operand.kind is not OperandKind.ROLE_STATE:
                        continue
                    holder = role_map.get(operand.role_pin.key if operand.role_pin is not None else ())
                    if holder and operand.dimension_pin is not None:
                        refs.add(_variable_ref(holder, operand.dimension_pin, context_ref, event.time_step))
        return tuple(sorted(refs))

    @staticmethod
    def _isolate_context(
        snapshot: StateSnapshotV351,
        context_ref: str | None,
        *,
        source_context_ref: str | None = None,
    ) -> StateSnapshotV351:
        if context_ref is None:
            return snapshot
        # Clone only the declared parent/factual context plus global fallback. Values from
        # unrelated hypothetical/session contexts must never leak into a new causal world.
        source_context_ref = source_context_ref or context_ref
        chosen = {}
        for key, value in snapshot.values:
            if key.context_ref not in {"global", source_context_ref}:
                continue
            structural = (key.holder_ref, key.dimension_pin.key)
            rank = 1 if key.context_ref == source_context_ref else 0
            current = chosen.get(structural)
            if current is None or rank > current[0]:
                chosen[structural] = (rank, key.dimension_pin, value)
        values = tuple(
            (StateKeyV351(holder, pin, context_ref), value)
            for (holder, _dimension_key), (_rank, pin, value) in sorted(
                chosen.items(), key=lambda item: str(item[0])
            )
        )
        return StateSnapshotV351(values, snapshot.domains, snapshot.proof_refs)

    def _apply_interventions(
        self, snapshot: StateSnapshotV351, intervention: InterventionContext
    ) -> tuple[StateSnapshotV351, tuple[CausalEventV351, ...]]:
        result = snapshot
        events = []
        for item in intervention.interventions:
            domain = result.domain(item.variable.dimension_pin)
            self.preview.algebra.validate_value(domain, item.value)
            prior = result.value(
                item.variable.holder_ref, item.variable.dimension_pin, intervention.context_ref
            )
            result = result.with_value(
                item.variable.holder_ref,
                item.variable.dimension_pin,
                intervention.context_ref,
                item.value,
            )
            # The imposed `do` value is a structural root change, not a learned causal
            # mechanism. Reify it only so downstream state-trigger mechanisms evaluate the
            # mutilated model. Exact intervention authorization remains separately pinned.
            source_pin = item.authorization_pins[0]
            delta = StateDeltaV351(
                delta_ref="intervention-delta:" + semantic_fingerprint(
                    "intervention-delta-v351",
                    (intervention.context_ref, item.variable.key, item.value.value_ref,
                     tuple(pin.key for pin in item.authorization_pins)),
                    32,
                ),
                holder_ref=item.variable.holder_ref,
                dimension_pin=item.variable.dimension_pin,
                prior_value=prior, new_value=item.value,
                transform_ref="structural-do-assignment", mechanism_pin=source_pin,
                context_ref=intervention.context_ref,
                effective_time_ref=f"intervention:{intervention.context_ref}:{item.variable.time_step}",
                confidence=1.0, time_step=item.variable.time_step, branch_probability=1.0,
                proof_refs=tuple(pin.ref for pin in item.authorization_pins),
                evidence_refs=item.evidence_refs,
            )
            events.append(CausalEventV351(
                event_ref="causal-intervention-state-event:" + semantic_fingerprint(
                    "causal-intervention-state-event-v351", delta.delta_ref, 32
                ),
                predicate_pin=source_pin, role_bindings=item.role_bindings,
                context_ref=intervention.context_ref,
                effective_time_ref=delta.effective_time_ref, time_step=item.variable.time_step,
                evidence_refs=item.evidence_refs,
                proof_refs=tuple(pin.ref for pin in item.authorization_pins),
                occurrence_kind="intervention_assignment", source_delta=delta,
            ))
        return result, tuple(events)

    @staticmethod
    def learning_evidence(result: CausalSimulationResultV351) -> tuple[CausalLearningEvidenceV351, ...]:
        evidence = []
        for proof in result.causal_proofs:
            for step in proof.steps:
                if step.intervention_cut:
                    continue
                evidence.append(CausalLearningEvidenceV351(
                    evidence_ref="causal-learning-evidence:" + semantic_fingerprint(
                        "causal-learning-evidence-v351", (proof.proof_ref, step.step_ref), 32,
                    ),
                    mechanism_pin=step.mechanism_pin,
                    source_variable_refs=step.source_variable_refs,
                    source_event_refs=step.source_event_refs,
                    target_variable_ref=step.target_variable_ref,
                    target_event_ref=step.secondary_event_ref,
                    proof_step_refs=(step.step_ref,),
                    intervention_support_refs=((result.intervention_ref,) if result.intervention_ref else ()),
                    mechanism_support_refs=(step.mechanism_pin.ref,),
                    source_lineage_refs=(proof.proof_ref,),
                    weight=step.confidence * step.branch_probability,
                ))
        return tuple(evidence)


def _authority_ref(pin) -> str:
    return (
        f"authority:{pin.kind}:{pin.namespace}:{pin.ref}@{pin.revision}:"
        f"{pin.content_hash}:{pin.scope_ref}"
    )


def _clone(work: _BranchWork, *, suffix: str, probability: float) -> _BranchWork:
    return _BranchWork(
        branch_ref=work.branch_ref + "/" + suffix,
        probability=probability, confidence=work.confidence, snapshot=work.snapshot,
        queue=list(work.queue), deltas=list(work.deltas), secondary_refs=list(work.secondary_refs),
        proof_steps=list(work.proof_steps), frontiers=list(work.frontiers), seen=set(work.seen),
        depth=work.depth, resolved=work.resolved,
    )


def _variable_ref(holder_ref, dimension_pin, context_ref, time_step):
    return "causal-variable:" + semantic_fingerprint(
        "causal-variable-v351", (holder_ref, dimension_pin.key, context_ref, time_step), 32,
    )


__all__ = ["CausalPropagationEngine", "MechanismCatalogV351"]
