"""CognitiveKernel — canonical v3.4.1 cycle orchestrator.

The replacement repairs the v3.4 object/ref mismatch, grounds candidate graphs
instead of empty strings, consumes learning evidence only after interpretation,
and records only actually dispatched realization items in common ground.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from ..model.cycle import CognitiveCycle, CycleTrigger, KernelSnapshot, pin_snapshot
from ..model.trace import CycleTrace
from ..epistemics.evaluator import EvidenceRecord as EpistemicEvidenceRecord


class CognitiveKernel:
    def __init__(
        self,
        *,
        schema_store: Any,
        percept_adapter: Any,
        semantic_composer: Any,
        grounding_resolver: Any,
        interpretation_resolver: Any,
        workspace_controller: Any,
        semantic_retriever: Any,
        epistemic_evaluator: Any,
        capability_evaluator: Any,
        gap_detector: Any,
        self_report_builder: Any,
        learning_coordinator: Any,
        goal_arbiter: Any,
        planner: Any,
        operation_authorizer: Any,
        operation_executor: Any,
        outcome_reconciler: Any,
        commit_coordinator: Any,
        response_planner: Any,
        message_renderer: Any,
        common_ground_manager: Any,
        invalidation_engine: Any | None = None,
        retraction_engine: Any | None = None,
        replay_safety_manager: Any | None = None,
        cross_schema_guard: Any | None = None,
        cutover_verifier: Any | None = None,
    ) -> None:
        self._schema_store = schema_store
        self._percept_adapter = percept_adapter
        self._semantic_composer = semantic_composer
        self._grounding_resolver = grounding_resolver
        self._interpretation_resolver = interpretation_resolver
        self._workspace_controller = workspace_controller
        self._semantic_retriever = semantic_retriever
        self._epistemic_evaluator = epistemic_evaluator
        self._capability_evaluator = capability_evaluator
        self._gap_detector = gap_detector
        self._self_report_builder = self_report_builder
        self._learning_coordinator = learning_coordinator
        self._goal_arbiter = goal_arbiter
        self._planner = planner
        self._operation_authorizer = operation_authorizer
        self._operation_executor = operation_executor
        self._outcome_reconciler = outcome_reconciler
        self._commit_coordinator = commit_coordinator
        self._response_planner = response_planner
        self._message_renderer = message_renderer
        self._common_ground_manager = common_ground_manager
        self._invalidation_engine = invalidation_engine
        self._retraction_engine = retraction_engine
        self._replay_safety_manager = replay_safety_manager
        self._cross_schema_guard = cross_schema_guard
        self._cutover_verifier = cutover_verifier

    def run(self, trigger: CycleTrigger) -> CognitiveCycle:
        cycle = self._orient(trigger)
        cycle = self._understand(cycle)
        cycle = self._know(cycle)
        cycle = self._decide(cycle)
        cycle = self._act_and_reconcile(cycle)
        cycle = self._critical_commit(cycle)
        cycle = self._communicate(cycle)
        cycle = self._output_commit_and_consolidate(cycle)
        cycle = self._invalidate_and_repair(cycle)
        return self._finalize(cycle)

    # ------------------------------------------------------------------
    # A. ORIENT
    # ------------------------------------------------------------------

    def _orient(self, trigger: CycleTrigger) -> CognitiveCycle:
        cycle_id = f"cycle:{uuid4().hex[:12]}"
        snapshot = pin_snapshot(
            schema_store_revision=getattr(self._schema_store, "store_revision", 0),
            kernel_foundation_version="v3.4.1",
            grounding_policy_version="graph-grounding-v2",
            competence_suite_hash="competence-v3.4.1",
            type_registry_version="semantic-model-v3.4",
            inference_policy_version="open-world-v3.4",
            truth_maintenance_version="four-state-v3.4",
            adapter_contract_hash="native-language-adapter-v3.4.1",
            context_scope_policy_version="scope-v3.4",
        )
        if self._cutover_verifier is not None:
            self._cutover_verifier.reset_turn_writers()
        return CognitiveCycle(
            cycle_id=cycle_id,
            trigger=trigger,
            snapshot=snapshot,
            trace=CycleTrace(
                cycle_id=cycle_id,
                trigger_kind=trigger.trigger_kind,
                stages=("orient",),
            ),
        )

    # ------------------------------------------------------------------
    # B. UNDERSTAND
    # ------------------------------------------------------------------

    def _understand(self, cycle: CognitiveCycle) -> CognitiveCycle:
        errors: list[str] = []
        surface_evidence: tuple[Any, ...] = ()
        meaning_candidates: tuple[Any, ...] = ()
        grounded_candidates: tuple[Any, ...] = ()
        selected_interpretations: tuple[Any, ...] = ()
        dialogue_resolution = None
        learning_transactions: tuple[Any, ...] = cycle.learning_transactions

        try:
            surface_evidence = tuple(self._percept_adapter.perceive(
                input_signals=cycle.trigger.input_signals,
                signal_ids=cycle.trigger.signal_ids,
                context_id=cycle.trigger.context_id,
            ))
        except Exception as exc:
            errors.append(f"perceive failed: {exc}")

        try:
            meaning_candidates = tuple(
                self._semantic_composer.compose(evidence)
                for evidence in surface_evidence
            )
        except Exception as exc:
            errors.append(f"compose failed: {exc}")

        try:
            grounded_candidates = tuple(
                self._grounding_resolver.ground_graph(
                    graph,
                    evidence,
                    context_ref=cycle.trigger.context_id,
                    environment_fingerprint=self._environment_fingerprint(cycle),
                )
                for graph, evidence in zip(meaning_candidates, surface_evidence)
            )
        except Exception as exc:
            errors.append(f"ground failed: {exc}")

        # Interpretation precedes learning-evidence consumption. A learning
        # answer is ordinary semantic evidence first, never copied raw text.
        try:
            selected: list[Any] = []
            for index, graph in enumerate(meaning_candidates):
                grounding = (
                    [grounded_candidates[index]]
                    if index < len(grounded_candidates) else []
                )
                result = self._interpretation_resolver.resolve(
                    candidate_graph=graph,
                    grounding_assessments=grounding,
                )
                selected.extend(getattr(result, "selected", ()) or ())
            selected_interpretations = tuple(selected)
        except Exception as exc:
            errors.append(f"resolve failed: {exc}")

        try:
            dialogue_resolution = self._learning_coordinator.resolve_dialogue_turn(
                context_ref=cycle.trigger.context_id,
                selected_interpretations=selected_interpretations,
                surface_evidence=surface_evidence,
            )
            if getattr(dialogue_resolution, "transaction_ref", ""):
                transaction = self._learning_coordinator.get_transaction(
                    dialogue_resolution.transaction_ref
                )
                if transaction is not None:
                    learning_transactions = (transaction,)
        except Exception as exc:
            errors.append(f"learning evidence consumption failed: {exc}")

        cycle = replace(
            cycle,
            surface_evidence=surface_evidence,
            meaning_candidates=meaning_candidates,
            grounded_candidates=grounded_candidates,
            selected_interpretations=selected_interpretations,
            dialogue_resolution=dialogue_resolution,
            dialogue_obligations=self._learning_coordinator.pending_obligations(
                cycle.trigger.context_id
            ),
            learning_transactions=learning_transactions,
        )
        return self._trace(cycle, "understand", errors)

    # ------------------------------------------------------------------
    # C. KNOW
    # ------------------------------------------------------------------

    def _know(self, cycle: CognitiveCycle) -> CognitiveCycle:
        errors: list[str] = []
        retrieval_results: tuple[Any, ...] = ()
        epistemic_assessments: tuple[Any, ...] = ()
        knowledge_assessments: tuple[Any, ...] = ()
        capability_assessments: tuple[Any, ...] = ()
        self_reports: tuple[Any, ...] = ()
        gaps: tuple[Any, ...] = ()
        workspace = None

        try:
            open_ports = tuple(
                port
                for graph in cycle.meaning_candidates
                for port in getattr(graph, "open_ports", ())
            )
            batch = self._semantic_retriever.retrieve(
                selected_interpretations=list(cycle.selected_interpretations),
                open_ports=open_ports,
                context_ref=cycle.trigger.context_id,
            )
            retrieval_results = tuple(getattr(batch, "results", ()) or ())
        except Exception as exc:
            errors.append(f"retrieve failed: {exc}")

        try:
            assessments: list[Any] = []
            knowledge: list[Any] = []
            reports: list[Any] = []
            for interpretation in cycle.selected_interpretations:
                # A question is not a factual assertion to admit or refute.
                if getattr(interpretation, "communicative_force", "") not in {
                    "assert", "correct"
                }:
                    continue
                proposition, context = self._resolve_proposition_context(
                    cycle, interpretation
                )
                if proposition is None or context is None:
                    continue
                predication_grounding = self._resolve_predication_grounding(
                    cycle, interpretation.predication_ref
                )
                evidence = (
                    EpistemicEvidenceRecord(
                        evidence_id=f"evidence:{proposition.id}",
                        proposition_ref=proposition.id,
                        supports=True,
                        source_ref=proposition.attribution_ref or "input:user",
                        confidence=max(0.3, interpretation.confidence),
                        is_independent=False,
                        lineage_root=proposition.attribution_ref or cycle.cycle_id,
                        context_ref=context.id,
                    ),
                )
                assessment = self._epistemic_evaluator.evaluate(
                    proposition=proposition,
                    context=context,
                    evidence=evidence,
                    schema_use_profile=(
                        predication_grounding.use_profile
                        if predication_grounding is not None else None
                    ),
                    accessible=True,
                    permission_allowed=True,
                    environment_fingerprint=self._environment_fingerprint(cycle),
                )
                assessments.append(assessment)
                known = self._epistemic_evaluator.derive_knowledge(
                    proposition=proposition,
                    context=context,
                    assessment=assessment,
                    is_grounded=bool(
                        predication_grounding
                        and predication_grounding.is_structurally_usable
                        and not predication_grounding.opaque_role_refs
                        and not predication_grounding.unresolved_role_refs
                    ),
                    schema_use_profile=(
                        predication_grounding.use_profile
                        if predication_grounding is not None else None
                    ),
                )
                knowledge.append(known)
                if (
                    self._self_report_builder is not None
                    and hasattr(self._self_report_builder, "report_knows")
                ):
                    reports.append(self._self_report_builder.report_knows(
                        proposition_ref=proposition.id,
                        knowledge=known,
                    ))
            epistemic_assessments = tuple(assessments)
            knowledge_assessments = tuple(knowledge)
            self_reports = tuple(reports)
        except Exception as exc:
            errors.append(f"epistemics failed: {exc}")

        try:
            from ..self_model.capability_evaluator import (
                ChannelRecord,
                CompetenceRecord,
                ComponentHealthRecord,
                ContextualPrecondition,
                ImplementationRecord,
                PermissionRecord,
                ResourceRecord,
            )

            if self._needs_answer_capability(cycle):
                operation_ref = self._operation_ref("op:answer")
                if operation_ref:
                    capability_assessments = (
                        self._capability_evaluator.evaluate(
                            subject_ref="self",
                            operation_schema_ref=operation_ref,
                            competence=CompetenceRecord(
                                schema_ref=operation_ref,
                                is_competent=True,
                                competence_score=0.9,
                                detail="boot communication competence available",
                            ),
                            implementation=ImplementationRecord(
                                operation_ref=operation_ref,
                                implementation_id="component:response_planner",
                                is_registered=True,
                            ),
                            component_health=ComponentHealthRecord(
                                component_id="component:canonical_runtime",
                                health="healthy",
                            ),
                            input_channel=ChannelRecord(
                                channel_kind="input",
                                channel_id=cycle.trigger.context_id,
                                is_available=True,
                                detail="current user utterance channel",
                            ),
                            output_channel=ChannelRecord(
                                channel_kind="output",
                                channel_id="text",
                                is_available=True,
                                detail="local text projection channel",
                            ),
                            resources=(
                                ResourceRecord(
                                    resource_kind="cycle_budget",
                                    status="available",
                                    available_amount=1.0,
                                    required_amount=1.0,
                                ),
                            ),
                            permission=PermissionRecord(
                                operation_ref=operation_ref,
                                is_allowed=True,
                                policy_ref="policy:execution_policy",
                                detail="local text answer permitted",
                            ),
                            preconditions=(
                                ContextualPrecondition(
                                    precondition_id="context:has_current_turn",
                                    description="current cycle has a user utterance",
                                    is_satisfied=bool(cycle.surface_evidence),
                                ),
                            ),
                            observed_reliability=1.0,
                        ),
                    )
        except Exception as exc:
            errors.append(f"capability evaluation failed: {exc}")

        try:
            all_gaps: list[Any] = []
            suppress = bool(
                cycle.dialogue_resolution
                and getattr(
                    cycle.dialogue_resolution,
                    "suppress_fresh_lexical_gaps",
                    False,
                )
            )
            for index, graph in enumerate(cycle.meaning_candidates):
                graph_grounding = (
                    [cycle.grounded_candidates[index]]
                    if index < len(cycle.grounded_candidates) else []
                )
                graph_selected = [
                    interpretation
                    for interpretation in cycle.selected_interpretations
                    if self._interpretation_in_graph(interpretation, graph)
                ]
                result = self._gap_detector.detect(
                    candidate_graph=graph,
                    grounding_assessments=graph_grounding,
                    epistemic_assessments=list(epistemic_assessments),
                    selected_interpretations=graph_selected,
                    suppress_fresh_lexical_gaps=suppress,
                )
                all_gaps.extend(getattr(result, "gaps", ()) or ())
            gaps = tuple(self._dedupe_gaps(all_gaps))
        except Exception as exc:
            errors.append(f"gap detection failed: {exc}")

        learning_transactions = list(cycle.learning_transactions)
        try:
            for gap in gaps:
                if not getattr(gap, "learnable", False):
                    continue
                transaction = self._learning_coordinator.open_transaction(
                    gap,
                    context_ref=cycle.trigger.context_id,
                )
                if all(
                    getattr(existing, "id", "") != transaction.id
                    for existing in learning_transactions
                ):
                    learning_transactions.append(transaction)
        except Exception as exc:
            errors.append(f"learning transaction open failed: {exc}")

        try:
            workspace = self._workspace_controller.focus(
                selected_interpretations=list(cycle.selected_interpretations),
                epistemic_assessments=list(epistemic_assessments),
                gaps=list(gaps),
            )
        except Exception as exc:
            errors.append(f"workspace focus failed: {exc}")

        cycle = replace(
            cycle,
            retrieval_results=retrieval_results,
            epistemic_assessments=epistemic_assessments,
            knowledge_assessments=knowledge_assessments,
            capability_assessments=capability_assessments,
            self_reports=self_reports,
            gaps=gaps,
            learning_transactions=tuple(learning_transactions),
            workspace=workspace,
        )
        return self._trace(cycle, "know", errors)

    # ------------------------------------------------------------------
    # D-F. DECIDE / ACT / CRITICAL COMMIT
    # ------------------------------------------------------------------

    def _decide(self, cycle: CognitiveCycle) -> CognitiveCycle:
        errors: list[str] = []
        goals: tuple[Any, ...] = ()
        plans: tuple[Any, ...] = ()
        authorization = None
        try:
            forces = tuple(
                force
                for graph in cycle.meaning_candidates
                for force in getattr(graph, "candidate_communicative_forces", ())
            )
            result = self._goal_arbiter.derive_and_arbitrate(
                selected_interpretations=list(cycle.selected_interpretations),
                communicative_forces=forces,
                gaps=list(cycle.gaps),
            )
            goals = tuple(getattr(result, "active_goals", ()) or ())

            # Information and discourse goals are handled by the response and
            # learning authorities. They are not executed as fake cognitive
            # operations merely to manufacture a success ledger.
            executable_goals = tuple(
                goal for goal in goals
                if getattr(goal, "goal_kind", "") == "world_state"
            )
            if executable_goals:
                plan_batch = self._planner.plan(goals=executable_goals)
                plans = tuple(getattr(plan_batch, "plans", ()) or ())
                selected_plan = getattr(plan_batch, "selected", None)
                if selected_plan is not None:
                    from ..execution.authorizer import (
                        AuthorizationBatch,
                        AuthorizationConditions,
                    )
                    decisions = {}
                    for operation in selected_plan.operations:
                        # No live policy/capability/resource records were
                        # supplied to this cycle. Unknown gates defer safely.
                        decisions[operation.id] = self._operation_authorizer.authorize(
                            operation,
                            AuthorizationConditions(
                                environment_fingerprint=self._environment_fingerprint(cycle),
                            ),
                        )
                    authorization = AuthorizationBatch(by_operation_ref=decisions)
        except Exception as exc:
            errors.append(f"decision failed: {exc}")
        cycle = replace(cycle, goals=goals, plans=plans, authorization=authorization)
        return self._trace(cycle, "decide", errors)

    def _act_and_reconcile(self, cycle: CognitiveCycle) -> CognitiveCycle:
        errors: list[str] = []
        ledger = None
        reconciliation = None
        try:
            if cycle.plans and cycle.authorization:
                result = self._operation_executor.execute(
                    plan=cycle.plans[0],
                    authorization=cycle.authorization,
                )
                ledger = getattr(result, "ledger", None)
                if ledger is not None:
                    reconciliation = self._outcome_reconciler.reconcile(
                        plan=cycle.plans[0],
                        ledger=ledger,
                    )
        except Exception as exc:
            errors.append(f"execution/reconciliation failed: {exc}")
        cycle = replace(
            cycle,
            execution_ledger=ledger,
            reconciliation_result=reconciliation,
        )
        return self._trace(cycle, "act", errors)

    def _critical_commit(self, cycle: CognitiveCycle) -> CognitiveCycle:
        # Execution output refs are not canonical semantic mutation payloads.
        # Do not convert operation IDs/results into fake persistent mutations.
        return self._trace(cycle, "critical_commit", [])

    # ------------------------------------------------------------------
    # G-H. COMMUNICATE / OUTPUT COMMIT
    # ------------------------------------------------------------------

    def _communicate(self, cycle: CognitiveCycle) -> CognitiveCycle:
        errors: list[str] = []
        message_plan = None
        realization_authorization = None
        surface_payload = None
        try:
            from ..response.planner import ContentSelectionInput

            selection = ContentSelectionInput(
                proposition_refs=tuple(
                    getattr(item, "proposition_ref", "")
                    for item in cycle.selected_interpretations
                    if getattr(item, "proposition_ref", "")
                ),
                assessments=tuple(cycle.epistemic_assessments),
                commit_outcome=cycle.critical_commit,
                execution_ledger=cycle.execution_ledger,
                goal_refs=tuple(
                    getattr(goal, "id", "") for goal in cycle.goals
                    if getattr(goal, "id", "")
                ),
                repair_obligation_refs=tuple(cycle.repair_obligations),
                language=self._response_language(cycle),
                channel="text",
                selected_interpretations=cycle.selected_interpretations,
                grounding_assessments=cycle.grounded_candidates,
                retrieval_results=cycle.retrieval_results,
                knowledge_assessments=cycle.knowledge_assessments,
                capability_assessments=cycle.capability_assessments,
                gaps=cycle.gaps,
                learning_transactions=cycle.learning_transactions,
                dialogue_resolution=cycle.dialogue_resolution,
                dialogue_obligations=cycle.dialogue_obligations,
                surface_evidence=cycle.surface_evidence,
            )
            message_plan = self._response_planner.plan_response(selection)
            if not self._response_planner.validate_plan(message_plan):
                raise ValueError("message plan failed semantic/provenance validation")
            realization_authorization = self._message_renderer.authorize(
                message_plan,
                language=message_plan.language or "en",
                environment_fingerprint=self._environment_fingerprint(cycle),
            )
            surface_payload = self._message_renderer.render(
                message_plan,
                language=message_plan.language or "en",
                authorization=realization_authorization,
                environment_fingerprint=self._environment_fingerprint(cycle),
            )
            if not self._message_renderer.validate_round_trip(surface_payload):
                raise ValueError("surface payload failed structural leakage validation")
        except Exception as exc:
            errors.append(f"communication failed: {exc}")
        cycle = replace(
            cycle,
            message_plan=message_plan,
            realization_authorization=realization_authorization,
            surface_payload=surface_payload,
        )
        return self._trace(cycle, "communicate", errors)

    def _output_commit_and_consolidate(self, cycle: CognitiveCycle) -> CognitiveCycle:
        errors: list[str] = []
        output_event = None
        try:
            if (
                cycle.message_plan is not None
                and cycle.surface_payload is not None
                and cycle.surface_payload.surface_text
            ):
                from ..response.common_ground import (
                    DispatchResult,
                    DispatchStatus,
                    DiscourseStatus,
                )
                dispatched_at = datetime.now(timezone.utc).isoformat()
                dispatch = DispatchResult(
                    message_plan_ref=cycle.message_plan.id,
                    status=DispatchStatus.DISPATCHED,
                    transport_outcome="local_projection",
                    dispatched_at=dispatched_at,
                )
                realized = set(cycle.surface_payload.realized_item_refs)
                output_event = {
                    "message_plan_ref": cycle.message_plan.id,
                    "realized_item_refs": tuple(realized),
                    "dispatched_at": dispatched_at,
                }
                status_map = {
                    "inform": DiscourseStatus.ASSERTED,
                    "query": DiscourseStatus.ASKED,
                    "correct": DiscourseStatus.CORRECTED,
                    "repair": DiscourseStatus.CORRECTED,
                    "request": DiscourseStatus.UNRESOLVED,
                    "refuse": DiscourseStatus.REJECTED,
                    "promise": DiscourseStatus.PROMISED,
                    "acknowledge": DiscourseStatus.ACCEPTED,
                }
                for item in cycle.message_plan.content_items:
                    if item.semantic_ref not in realized:
                        continue
                    self._common_ground_manager.record_dispatch(
                        proposition_ref=item.semantic_ref,
                        participant_ref="self",
                        discourse_status=status_map.get(
                            item.discourse_function,
                            DiscourseStatus.ASSERTED,
                        ),
                        dispatch_result=dispatch,
                    )
                    if item.content_kind == "learning_probe":
                        self._learning_coordinator.register_probe_dispatch(
                            context_ref=cycle.trigger.context_id,
                            message_item=item,
                            gaps=cycle.gaps,
                            output_event_ref=cycle.message_plan.id,
                        )
                    elif item.content_kind in {"learning_progress", "dialogue_gap_explanation"} and cycle.dialogue_resolution is not None:
                        self._learning_coordinator.register_followup_dispatch(
                            context_ref=cycle.trigger.context_id,
                            message_item=item,
                            dialogue_resolution=cycle.dialogue_resolution,
                            output_event_ref=cycle.message_plan.id,
                        )
        except Exception as exc:
            errors.append(f"output commit failed: {exc}")
        cycle = replace(
            cycle,
            output_event=output_event,
            dialogue_obligations=self._learning_coordinator.pending_obligations(
                cycle.trigger.context_id
            ),
        )
        return self._trace(cycle, "output_commit", errors)

    # ------------------------------------------------------------------
    # Invalidation/finalization and compatibility correction entry
    # ------------------------------------------------------------------

    def execute_correction(self, operation: Any) -> Any:
        if self._retraction_engine is None:
            return None
        return self._retraction_engine.execute(operation)

    def _invalidate_and_repair(self, cycle: CognitiveCycle) -> CognitiveCycle:
        # Invalidation events are processed by their owning components when
        # revisions change. This cycle does not invent an environment change by
        # comparing unlike fingerprint formats.
        return self._trace(cycle, "invalidate", [])

    def _finalize(self, cycle: CognitiveCycle) -> CognitiveCycle:
        trace = cycle.trace or CycleTrace(cycle_id=cycle.cycle_id)
        trace = replace(
            trace,
            finished_at=datetime.now(timezone.utc),
            stages=(*trace.stages, "finalize"),
        )
        return replace(cycle, trace=trace)

    # ------------------------------------------------------------------
    # Lookup and trace helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _trace(cycle: CognitiveCycle, stage: str, errors: list[str]) -> CognitiveCycle:
        current = cycle.trace or CycleTrace(cycle_id=cycle.cycle_id)
        return replace(cycle, trace=replace(
            current,
            stages=(*current.stages, stage),
            errors=(*current.errors, *tuple(errors)),
        ))

    @staticmethod
    def _environment_fingerprint(cycle: CognitiveCycle) -> str:
        return (
            f"schema={cycle.snapshot.schema_store_revision};"
            f"foundation={cycle.snapshot.kernel_foundation_version};"
            f"adapter={cycle.snapshot.adapter_contract_hash}"
        )

    @staticmethod
    def _response_language(cycle: CognitiveCycle) -> str:
        for evidence in cycle.surface_evidence:
            language = getattr(evidence, "language_tag", "")
            if language:
                return language
        return "en"

    @staticmethod
    def _needs_answer_capability(cycle: CognitiveCycle) -> bool:
        return any(
            getattr(interpretation, "communicative_force", "") == "ask"
            for interpretation in cycle.selected_interpretations
        )

    def _operation_ref(self, semantic_key: str) -> str:
        active = self._schema_store.find_active(semantic_key)
        if active is not None:
            return getattr(active, "semantic_key", "") or semantic_key
        return ""

    @staticmethod
    def _interpretation_in_graph(interpretation: Any, graph: Any) -> bool:
        prop_ref = getattr(interpretation, "proposition_ref", "")
        return any(
            candidate.proposition.id == prop_ref
            for candidate in getattr(graph, "candidate_propositions", ())
        )

    @staticmethod
    def _resolve_proposition_context(
        cycle: CognitiveCycle,
        interpretation: Any,
    ) -> tuple[Any | None, Any | None]:
        prop_ref = getattr(interpretation, "proposition_ref", "")
        context_ref = getattr(interpretation, "context_ref", "")
        proposition = None
        context = None
        for graph in cycle.meaning_candidates:
            for candidate in getattr(graph, "candidate_propositions", ()):
                if candidate.proposition.id == prop_ref:
                    proposition = candidate.proposition
                    context_ref = context_ref or proposition.context_ref
                    break
            for candidate in getattr(graph, "candidate_contexts", ()):
                if candidate.context_frame.id == context_ref:
                    context = candidate.context_frame
                    break
            if proposition is not None and context is not None:
                break
        return proposition, context

    @staticmethod
    def _resolve_predication_grounding(
        cycle: CognitiveCycle,
        predication_ref: str,
    ) -> Any | None:
        for grounding in cycle.grounded_candidates:
            if hasattr(grounding, "for_predication"):
                found = grounding.for_predication(predication_ref)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _dedupe_gaps(gaps: Iterable[Any]) -> list[Any]:
        result: list[Any] = []
        seen: set[tuple[str, str, tuple[str, ...]]] = set()
        for gap in gaps:
            key = (
                getattr(gap, "gap_kind", ""),
                getattr(gap, "target_artifact_ref", ""),
                tuple(getattr(gap, "missing_fields", ()) or ()),
            )
            if key not in seen:
                seen.add(key)
                result.append(gap)
        return result
