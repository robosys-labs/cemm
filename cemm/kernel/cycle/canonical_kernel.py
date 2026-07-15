"""Canonical v3.4.3 cycle with real DECIDE/ACT and emission closure."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from .kernel import CognitiveKernel


class CanonicalCognitiveKernel(CognitiveKernel):
    def __init__(
        self,
        *,
        response_decider,
        emission_environment_builder,
        foundation_fingerprint: str,
        active_schema_refs: frozenset[str],
        passed_competence_case_refs: frozenset[str],
        passed_round_trip_case_refs: frozenset[str],
        non_persistent_predicates: frozenset[str] = frozenset(),
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._response_decider = response_decider
        self._emission_environment_builder = emission_environment_builder
        self._foundation_fingerprint = foundation_fingerprint
        self._active_schema_refs = active_schema_refs
        self._passed_competence_case_refs = passed_competence_case_refs
        self._passed_round_trip_case_refs = passed_round_trip_case_refs
        self._non_persistent_predicates = non_persistent_predicates

    def run(self, trigger):
        cycle = self._orient(trigger)
        cycle = self._understand(cycle)
        cycle = self._know(cycle)
        cycle = self._decide(cycle)
        cycle = self._act(cycle)
        cycle = self._critical_commit(cycle)
        cycle = self._communicate(cycle)
        cycle = self._output_commit(cycle)
        cycle = self._trace(cycle, "invalidate", ())
        return self._finalize(cycle)

    def _orient(self, trigger):
        cycle = super()._orient(trigger)
        return replace(
            cycle,
            snapshot=replace(
                cycle.snapshot,
                kernel_foundation_version="v3.4.3-runtime",
                grounding_policy_version="typed-query-ports-v3.4.3",
                competence_suite_hash=self._foundation_fingerprint,
                adapter_contract_hash="semantic-language-pack-v3.4.3",
            ),
        )

    def _decide(self, cycle):
        errors = []
        goals = ()
        response_intents = ()
        try:
            forces = tuple(
                force
                for graph in cycle.meaning_candidates
                for force in graph.candidate_communicative_forces
            )
            arbitration = self._goal_arbiter.derive_and_arbitrate(
                selected_interpretations=list(
                    cycle.selected_interpretations
                ),
                communicative_forces=forces,
                gaps=list(cycle.gaps),
            )
            goals = arbitration.active_goals
            response_intents = self._response_decider.decide(cycle)
        except Exception as exc:
            errors.append(f"decide failed: {exc}")
        cycle = replace(
            cycle,
            goals=goals,
            response_intents=response_intents,
        )
        return self._trace(cycle, "decide", errors)

    def _act(self, cycle):
        errors = []
        plans = ()
        try:
            batch = self._planner.plan(
                goals=cycle.goals,
                workspace_snapshot=cycle.workspace,
            )
            plans = batch.plans
        except Exception as exc:
            errors.append(f"act failed: {exc}")
        cycle = replace(cycle, plans=plans)
        return self._trace(cycle, "act", errors)

    def _critical_commit(self, cycle):
        if not self._non_persistent_predicates:
            return super()._critical_commit(cycle)
        filtered = tuple(
            interpretation
            for interpretation in cycle.selected_interpretations
            if interpretation.predicate_semantic_key
            not in self._non_persistent_predicates
        )
        committed = super()._critical_commit(replace(
            cycle,
            selected_interpretations=filtered,
        ))
        return replace(
            committed,
            selected_interpretations=cycle.selected_interpretations,
        )

    def _communicate(self, cycle):
        errors = []
        plan = authorization = payload = None
        try:
            from ..response.planner import ContentSelectionInput

            selection = ContentSelectionInput(
                response_intents=cycle.response_intents,
                requirement_assessments=tuple(
                    getattr(cycle, "requirement_assessments", ()) or ()
                ),
                commit_outcome=cycle.critical_commit,
                selected_interpretations=cycle.selected_interpretations,
                retrieval_results=cycle.retrieval_results,
                capability_assessments=cycle.capability_assessments,
                gaps=cycle.gaps,
                learning_transactions=cycle.learning_transactions,
                language=self._response_language(cycle),
            )
            plan = self._response.plan_response(selection)
            environment = self._emission_environment_builder.build(
                cycle,
                foundation_fingerprint=self._foundation_fingerprint,
                active_schema_refs=self._active_schema_refs,
                passed_competence_case_refs=(
                    self._passed_competence_case_refs
                ),
                passed_round_trip_case_refs=(
                    self._passed_round_trip_case_refs
                ),
            )
            authorization = self._renderer.authorize(
                plan,
                language=plan.language_tag,
                environment=environment,
            )
            payload = self._renderer.render(
                plan,
                language=plan.language_tag,
                environment=environment,
                authorization=authorization,
            )
        except Exception as exc:
            errors.append(f"communicate failed: {exc}")
        cycle = replace(
            cycle,
            message_plan=plan,
            realization_authorization=authorization,
            surface_payload=payload,
        )
        return self._trace(cycle, "communicate", errors)

    def _output_commit(self, cycle):
        errors = []
        output_event = None
        try:
            if (
                cycle.message_plan
                and cycle.surface_payload
                and cycle.surface_payload.surface_text
            ):
                from ..response.common_ground import (
                    DispatchResult,
                    DispatchStatus,
                    DiscourseStatus,
                )

                dispatched_at = datetime.now(timezone.utc).isoformat()
                plan = cycle.message_plan
                dispatch = DispatchResult(
                    message_plan_ref=plan.plan_id,
                    status=DispatchStatus.DISPATCHED,
                    transport_outcome="local_projection",
                    dispatched_at=dispatched_at,
                )
                realized = set(cycle.surface_payload.realized_item_refs)
                output_event = {
                    "message_plan_ref": plan.plan_id,
                    "realized_item_refs": tuple(realized),
                    "dispatched_at": dispatched_at,
                }
                for clause in plan.clauses:
                    if clause.clause_id not in realized:
                        continue
                    status = (
                        DiscourseStatus.ASKED
                        if clause.communicative_force
                        in {"ask", "query", "request"}
                        else DiscourseStatus.ASSERTED
                    )
                    self._common_ground.record_dispatch(
                        proposition_ref=clause.clause_id,
                        participant_ref="self",
                        discourse_status=status,
                        dispatch_result=dispatch,
                    )
        except Exception as exc:
            errors.append(f"output commit failed: {exc}")
        cycle = replace(
            cycle,
            output_event=output_event,
            dialogue_obligations=self._learning.pending_obligations(
                cycle.trigger.context_id
            ),
        )
        return self._trace(cycle, "output_commit", errors)
