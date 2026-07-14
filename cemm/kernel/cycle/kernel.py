"""CognitiveKernel — canonical v3.4 cycle orchestrator.

Per CORE_LOOP.md §4-§5 and AUTHORITY_MATRIX.md:
- CognitiveKernel.run(trigger) owns the full cycle:
  ORIENT → UNDERSTAND → KNOW → DECIDE → ACT → CRITICAL_COMMIT →
  COMMUNICATE → OUTPUT_COMMIT → CONSOLIDATE/SCHEDULE
- Stages return new CognitiveCycle revisions; no hidden mutation.
- Each stage has exactly one sole authority.
- No canonical component reads hidden mutable legacy kernel state.

Import boundary: model + canonical kernel subpackages only.
No imports from root kernel/*.py legacy modules.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..model.cycle import (
    CognitiveCycle,
    CycleTrigger,
    KernelSnapshot,
    pin_snapshot,
)
from ..model.trace import CycleTrace


class CognitiveKernel:
    """Canonical v3.4 cognitive cycle orchestrator.

    Owns the macro state machine. Each stage delegates to its sole
    authority component. The cycle produces an immutable
    CognitiveCycle artifact.

    Dependencies are injected — construction lives in app/runtime.py.
    """

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
        """Run one complete cognitive cycle.

        Returns an immutable CognitiveCycle with all stage outputs.
        """
        cycle = self._orient(trigger)
        cycle = self._understand(cycle)
        cycle = self._know(cycle)
        cycle = self._decide(cycle)
        cycle = self._act_and_reconcile(cycle)
        cycle = self._critical_commit(cycle)
        cycle = self._communicate(cycle)
        cycle = self._output_commit_and_consolidate(cycle)
        cycle = self._invalidate_and_repair(cycle)
        cycle = self._finalize(cycle)
        return cycle

    # ── A. ORIENT ──

    def _orient(self, trigger: CycleTrigger) -> CognitiveCycle:
        """Pin KernelSnapshot and initialize the cycle."""
        snapshot = self._pin_snapshot()
        cycle_id = f"cycle:{uuid4().hex[:12]}"
        cycle = CognitiveCycle(
            cycle_id=cycle_id,
            trigger=trigger,
            snapshot=snapshot,
        )
        if self._cutover_verifier:
            self._cutover_verifier.reset_turn_writers()
        return cycle

    def _pin_snapshot(self) -> KernelSnapshot:
        """Pin current store revisions into an immutable snapshot."""
        schema_rev = getattr(self._schema_store, "revision", 0)
        fp = f"fp:v3.4:schema={schema_rev}"
        return pin_snapshot(
            schema_store_revision=schema_rev,
            kernel_foundation_version="v3.4",
            adapter_contract_hash=fp,
        )

    def _current_fingerprint(self) -> str:
        """Get current environment fingerprint for invalidation checks."""
        schema_rev = getattr(self._schema_store, "revision", 0)
        return f"fp:v3.4:schema={schema_rev}"

    # ── B. UNDERSTAND ──

    def _understand(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """B1-B8: Observe, Perceive, Compose, Ground, Resolve, Integrate."""
        errors: list[str] = []

        # B1-B2. Observe + Perceive via legacy boundary adapter
        surface_evidence = ()
        try:
            raw_signals = cycle.trigger.signal_ids
            evidence = self._percept_adapter.perceive(raw_signals)
            surface_evidence = tuple(evidence) if evidence else ()
        except Exception as e:
            errors.append(f"perceive failed: {e}")

        cycle = replace(cycle, surface_evidence=surface_evidence)
        if self._cutover_verifier:
            self._cutover_verifier.assert_single_writer(
                "surface_evidence", "PerceptAdapter"
            )

        # B3. Compose
        meaning_candidates = ()
        try:
            if surface_evidence:
                graphs = []
                for ev in surface_evidence:
                    graph = self._semantic_composer.compose(ev)
                    graphs.append(graph)
                meaning_candidates = tuple(graphs)
        except Exception as e:
            errors.append(f"compose failed: {e}")

        cycle = replace(cycle, meaning_candidates=meaning_candidates)
        if self._cutover_verifier:
            self._cutover_verifier.assert_single_writer(
                "meaning_candidates", "SemanticComposer"
            )

        # B4. Ground
        grounded_candidates = ()
        try:
            if meaning_candidates:
                grounded = []
                for graph in meaning_candidates:
                    assessments = self._grounding_resolver.ground_referent(
                        surface=str(getattr(graph, "source_surface", "")),
                    )
                    grounded.append(assessments)
                grounded_candidates = tuple(grounded)
        except Exception as e:
            errors.append(f"ground failed: {e}")

        cycle = replace(cycle, grounded_candidates=grounded_candidates)
        if self._cutover_verifier:
            self._cutover_verifier.assert_single_writer(
                "grounded_candidates", "GroundingResolver"
            )

        # B5. Consume pending learning evidence
        learning_transactions = ()
        try:
            updated_txs = self._learning_coordinator.consume_pending_evidence(
                selected_interpretations=list(cycle.selected_interpretations),
            )
            if updated_txs:
                learning_transactions = tuple(updated_txs)
        except Exception as e:
            errors.append(f"learning evidence consumption failed: {e}")

        # B6. Provisional replay — for transactions with matched evidence,
        # create child revisions and attempt activation
        if learning_transactions:
            try:
                replayed = []
                for tx in learning_transactions:
                    if hasattr(tx, "hypotheses") and tx.hypotheses:
                        updated_tx, attempt = (
                            self._learning_coordinator.provisional_replay(tx)
                        )
                        replayed.append(updated_tx)
                if replayed:
                    learning_transactions = tuple(replayed)
            except Exception as e:
                errors.append(f"provisional replay failed: {e}")

        cycle = replace(cycle, learning_transactions=learning_transactions)

        # B7. Resolve
        selected_interpretations = ()
        try:
            if meaning_candidates:
                selected = []
                for graph in meaning_candidates:
                    result = self._interpretation_resolver.resolve(
                        candidate_graph=graph,
                        grounding_assessments=list(grounded_candidates),
                    )
                    if hasattr(result, "selected"):
                        selected.extend(result.selected)
                selected_interpretations = tuple(selected)
        except Exception as e:
            errors.append(f"resolve failed: {e}")

        cycle = replace(
            cycle,
            selected_interpretations=selected_interpretations,
        )
        if self._cutover_verifier:
            self._cutover_verifier.assert_single_writer(
                "selected_interpretations", "InterpretationResolver"
            )

        if errors:
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=("orient", "understand"),
                errors=tuple(errors),
            ))

        return cycle

    # ── C. KNOW ──

    def _know(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """C1-C5: Retrieve, Evaluate Epistemics, Introspect, Detect Gaps, Focus."""
        errors: list[str] = []

        # C1. Retrieve
        retrieval_results = ()
        try:
            batch = self._semantic_retriever.retrieve(
                selected_interpretations=list(cycle.selected_interpretations),
            )
            retrieval_results = tuple(batch.results) if hasattr(batch, "results") else ()
        except Exception as e:
            errors.append(f"retrieve failed: {e}")

        cycle = replace(cycle, retrieval_results=retrieval_results)

        # C2. Evaluate Epistemics
        epistemic_assessments = ()
        knowledge_assessments = ()
        self_reports = ()
        try:
            # Collect evidence refs from retrieval results
            evidence_by_prop: dict[str, list[str]] = {}
            for rr in retrieval_results:
                refs = getattr(rr, "evidence_refs", ())
                prop_ref = getattr(rr, "query_pattern_ref", "")
                if refs:
                    evidence_by_prop.setdefault(prop_ref, []).extend(refs)

            assessments = []
            knowledge_list = []
            reports = []
            for interp in cycle.selected_interpretations:
                prop = getattr(interp, "proposition", None)
                ctx = getattr(interp, "context_frame", None)
                if prop is not None and ctx is not None:
                    result = self._epistemic_evaluator.evaluate(
                        proposition=prop,
                        context=ctx,
                    )
                    assessments.append(result)

                    # Derive knowledge assessment (knows(self, p))
                    knowledge = None
                    if hasattr(self._epistemic_evaluator, "derive_knowledge"):
                        knowledge = self._epistemic_evaluator.derive_knowledge(
                            proposition=prop,
                            context=ctx,
                            assessment=result,
                        )
                        knowledge_list.append(knowledge)

                    # Build self-report
                    if self._self_report_builder is not None and knowledge is not None:
                        if hasattr(self._self_report_builder, "report_knows"):
                            report = self._self_report_builder.report_knows(
                                proposition_ref=prop.id,
                                knowledge=knowledge,
                            )
                            reports.append(report)
            epistemic_assessments = tuple(assessments)
            knowledge_assessments = tuple(knowledge_list)
            self_reports = tuple(reports)

            # Register assessments in artifact index for invalidation tracking
            if self._invalidation_engine is not None:
                from ..model.learning import DerivedArtifactProvenance
                from ..epistemics.artifact_index import (
                    IndexedArtifact, ArtifactKind,
                )
                for a in assessments:
                    prop_id = getattr(a, "proposition_ref", "")
                    if prop_id:
                        art = IndexedArtifact(
                            artifact_id=f"assess:{prop_id}",
                            artifact_kind=ArtifactKind.INFERENCE,
                            provenance=DerivedArtifactProvenance(
                                supporting_assessment_refs=(prop_id,),
                                environment_fingerprint=None,
                            ),
                        )
                        self._invalidation_engine.index.register(art)
        except Exception as e:
            errors.append(f"epistemics failed: {e}")

        cycle = replace(
            cycle,
            epistemic_assessments=epistemic_assessments,
            knowledge_assessments=knowledge_assessments,
            self_reports=self_reports,
        )

        # C3. Introspect — capability assessment
        capability_assessments = ()
        try:
            caps = []
            for interp in cycle.selected_interpretations:
                op_ref = getattr(interp, "operation_schema_ref", "")
                if op_ref:
                    cap = self._capability_evaluator.evaluate(
                        subject_ref="self",
                        operation_schema_ref=op_ref,
                    )
                    caps.append(cap)
            capability_assessments = tuple(caps)
        except Exception as e:
            errors.append(f"capability failed: {e}")

        cycle = replace(cycle, capability_assessments=capability_assessments)

        # C4. Detect Gaps
        gaps = ()
        try:
            gap_result = self._gap_detector.detect(
                candidate_graph=cycle.meaning_candidates[0]
                if cycle.meaning_candidates else None,
                grounding_assessments=list(cycle.grounded_candidates),
                epistemic_assessments=list(cycle.epistemic_assessments),
            )
            gaps = tuple(gap_result.gaps) if hasattr(gap_result, "gaps") else ()
        except Exception as e:
            errors.append(f"gap detection failed: {e}")

        cycle = replace(cycle, gaps=gaps)

        # C4b. Open learning transactions for detected gaps
        new_learning_txs = list(cycle.learning_transactions)
        try:
            for gap in gaps:
                tx = self._learning_coordinator.open_transaction(gap)
                new_learning_txs.append(tx)
        except Exception as e:
            errors.append(f"learning transaction open failed: {e}")

        cycle = replace(cycle, learning_transactions=tuple(new_learning_txs))

        # C5. Focus — workspace
        workspace = None
        try:
            workspace = self._workspace_controller.focus(
                selected_interpretations=list(cycle.selected_interpretations),
                epistemic_assessments=list(cycle.epistemic_assessments),
                gaps=list(cycle.gaps),
            )
        except Exception as e:
            errors.append(f"focus failed: {e}")

        cycle = replace(cycle, workspace=workspace)

        if errors:
            existing = cycle.trace
            new_errors = (existing.errors if existing else ()) + tuple(errors)
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=(existing.stages if existing else ()) + ("know",),
                errors=new_errors,
            ))

        return cycle

    # ── D. DECIDE ──

    def _decide(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """D1-D4: Derive Goals, Plan, Authorize."""
        errors: list[str] = []

        # D1-D2. Derive and arbitrate goals
        goals = ()
        try:
            goal_result = self._goal_arbiter.derive_and_arbitrate(
                selected_interpretations=list(cycle.selected_interpretations),
                gaps=list(cycle.gaps),
                capability_assessment=cycle.capability_assessments[0]
                if cycle.capability_assessments else None,
            )
            goals = tuple(goal_result.active_goals) if hasattr(goal_result, "active_goals") else ()
        except Exception as e:
            errors.append(f"goal arbitration failed: {e}")

        cycle = replace(cycle, goals=goals)

        # D3. Plan
        plans = ()
        plan_batch = None
        try:
            plan_batch = self._planner.plan(
                goals=goals,
                capability_assessment=cycle.capability_assessments[0]
                if cycle.capability_assessments else None,
            )
            plans = tuple(plan_batch.plans) if hasattr(plan_batch, "plans") else ()
        except Exception as e:
            errors.append(f"planning failed: {e}")

        cycle = replace(cycle, plans=plans)

        # D4. Authorize — consume live typed conditions
        authorization = None
        try:
            if plan_batch and hasattr(plan_batch, "selected") and plan_batch.selected:
                from ..execution.authorizer import (
                    AuthorizationConditions,
                    AuthorizationBatch,
                )
                # Derive live conditions from capability and epistemic assessments
                cap_available = True
                if cycle.capability_assessments:
                    cap = cycle.capability_assessments[0]
                    cap_available = getattr(cap, "is_capable", True)

                # Check epistemic admissibility for schema-use validity
                schema_use_valid = True
                if cycle.epistemic_assessments:
                    for assessment in cycle.epistemic_assessments:
                        admissibility = getattr(assessment, "admissibility", "admitted")
                        if admissibility in ("blocked", "inadmissible"):
                            schema_use_valid = False
                            break

                # Build environment fingerprint from snapshot
                env_fp = f"store:{cycle.snapshot.schema_store_revision}"

                auth_by_op = {}
                for op in plan_batch.selected.operations:
                    auth_result = self._operation_authorizer.authorize(
                        operation=op,
                        conditions=AuthorizationConditions(
                            capability_available=cap_available,
                            permission_allowed=True,
                            safety_passed=True,
                            privacy_passed=True,
                            resources_available=True,
                            context_valid=True,
                            schema_use_valid=schema_use_valid,
                            risk_level="low",
                            environment_fingerprint=env_fp,
                        ),
                    )
                    auth_by_op[op.id] = auth_result
                authorization = AuthorizationBatch(by_operation_ref=auth_by_op)
        except Exception as e:
            errors.append(f"authorization failed: {e}")

        cycle = replace(cycle, authorization=authorization)

        if errors:
            existing = cycle.trace
            new_errors = (existing.errors if existing else ()) + tuple(errors)
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=(existing.stages if existing else ()) + ("decide",),
                errors=new_errors,
            ))

        return cycle

    # ── E. ACT AND RECONCILE ──

    def _act_and_reconcile(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """E1-E3: Execute, Observe, Reconcile."""
        errors: list[str] = []

        # E1. Execute
        execution_ledger = None
        try:
            if cycle.plans and cycle.authorization:
                selected_plan = cycle.plans[0]
                exec_result = self._operation_executor.execute(
                    plan=selected_plan,
                    authorization=cycle.authorization,
                )
                execution_ledger = exec_result.ledger if exec_result else None

                # Register in-flight effects for reauthorization at commit
                if execution_ledger and self._replay_safety_manager is not None:
                    for outcome in execution_ledger.outcomes:
                        if outcome.status == "succeeded":
                            op_id = outcome.operation_ref
                            idem_key = getattr(outcome, "idempotency_key", op_id)
                            auth_fp = ""
                            if hasattr(cycle.authorization, "by_operation_ref"):
                                auth_result = cycle.authorization.by_operation_ref.get(op_id)
                                if auth_result:
                                    auth_fp = getattr(auth_result, "authorization_fingerprint", "")
                            self._replay_safety_manager.register_in_flight_effect(
                                effect_id=f"effect:{op_id}",
                                operation_id=op_id,
                                idempotency_key=idem_key,
                                authorization_fingerprint=auth_fp,
                                predicted_effects=tuple(outcome.output_refs),
                            )
        except Exception as e:
            errors.append(f"execution failed: {e}")

        cycle = replace(cycle, execution_ledger=execution_ledger)

        # E3. Reconcile — compare predicted and observed effects
        try:
            if execution_ledger and cycle.plans:
                selected_plan = cycle.plans[0]
                reconcile_result = self._outcome_reconciler.reconcile(
                    plan=selected_plan,
                    ledger=execution_ledger,
                )
                cycle = replace(cycle, reconciliation_result=reconcile_result)
                if reconcile_result and reconcile_result.prediction_errors:
                    existing = cycle.trace
                    new_errors = (existing.errors if existing else ()) + tuple(
                        f"prediction error: {pe.error_kind} for {pe.operation_ref}"
                        for pe in reconcile_result.prediction_errors
                    )
                    cycle = replace(cycle, trace=CycleTrace(
                        cycle_id=cycle.cycle_id,
                        trigger_kind=cycle.trigger.trigger_kind,
                        stages=(existing.stages if existing else ()) + ("reconcile",),
                        errors=new_errors,
                    ))
        except Exception as e:
            errors.append(f"reconciliation failed: {e}")
        if errors:
            existing = cycle.trace
            new_errors = (existing.errors if existing else ()) + tuple(errors)
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=(existing.stages if existing else ()) + ("act",),
                errors=new_errors,
            ))

        return cycle

    # ── F. CRITICAL COMMIT ──

    def _critical_commit(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """F1-F6: Build MutationSet, validate, commit atomically.

        Per CORE_LOOP.md §F and Stage 6:
        - Revalidate authorization before critical commit.
        - Build exact MutationSet from execution outcomes.
        - Commit atomically. Roll back on failure.
        """
        errors: list[str] = []

        critical_commit = None
        try:
            if cycle.execution_ledger:
                from ..model.mutation import MutationSet, MutationOperation
                from uuid import uuid4 as _uuid4

                # F0. Revalidate authorization before critical commit
                if cycle.authorization:
                    from ..execution.authorizer import AuthorizationBatch, AuthorizationConditions
                    auth_batch = cycle.authorization
                    if isinstance(auth_batch, AuthorizationBatch):
                        for op_id, auth_result in auth_batch.by_operation_ref.items():
                            if auth_result.revalidation_required:
                                # Check if environment changed
                                current_fp = f"store:{cycle.snapshot.schema_store_revision}"
                                if auth_result.authorization_fingerprint and \
                                   auth_result.authorization_fingerprint != current_fp:
                                    errors.append(
                                        f"authorization stale for {op_id}: "
                                        f"environment changed"
                                    )
                                    continue

                # F0b. Reauthorize in-flight effects via ReplaySafetyManager
                if self._replay_safety_manager is not None:
                    current_fp = f"store:{cycle.snapshot.schema_store_revision}"
                    for effect in self._replay_safety_manager.get_in_flight_effects():
                        reauth = self._replay_safety_manager.reauthorize(
                            effect_id=effect.effect_id,
                            current_fingerprint=current_fp,
                        )
                        if not reauth.is_authorized:
                            errors.append(
                                f"effect reauthorization denied for {effect.effect_id}: "
                                f"{reauth.reason}"
                            )
                        else:
                            self._replay_safety_manager.commit_effect(effect.effect_id)

                ops = []
                for outcome in cycle.execution_ledger.outcomes:
                    if outcome.status == "succeeded":
                        ops.append(MutationOperation(
                            id=f"mut:{_uuid4().hex[:8]}",
                            action="create",
                            payload_ref=outcome.operation_ref,
                            evidence_refs=outcome.output_refs,
                            required=True,
                        ))

                if ops and not any("authorization stale" in e for e in errors):
                    mutation_set = MutationSet(
                        id=f"ms:{_uuid4().hex[:8]}",
                        phase="critical",
                        operations=tuple(ops),
                    )
                    critical_commit = self._commit_coordinator.commit(mutation_set)
        except Exception as e:
            errors.append(f"critical commit failed: {e}")

        cycle = replace(cycle, critical_commit=critical_commit)

        if errors:
            existing = cycle.trace
            new_errors = (existing.errors if existing else ()) + tuple(errors)
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=(existing.stages if existing else ()) + ("commit",),
                errors=new_errors,
            ))

        return cycle

    # ── G. COMMUNICATE ──

    def _communicate(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """G1-G4: Select content, build message plan, realize, dispatch."""
        errors: list[str] = []

        # G1-G2. Select content and build message plan
        message_plan = None
        try:
            from ..response.planner import ContentSelectionInput
            from ..model.epistemic import EpistemicAssessment

            prop_refs = tuple(
                getattr(s, "proposition_ref", "")
                for s in cycle.selected_interpretations
            )
            assessments_tuple = tuple(
                a for a in cycle.epistemic_assessments
                if isinstance(a, EpistemicAssessment)
            )
            selection = ContentSelectionInput(
                proposition_refs=prop_refs,
                assessments=assessments_tuple,
                commit_outcome=cycle.critical_commit,
                execution_ledger=cycle.execution_ledger,
                goal_refs=tuple(g.id for g in cycle.goals if hasattr(g, "id")),
            )
            message_plan = self._response_planner.plan_response(selection)

            # Validate plan — every clause maps to content/provenance
            if message_plan and not self._response_planner.validate_plan(message_plan):
                errors.append("message plan validation failed: content/provenance mismatch")
                message_plan = None

            # Register message items in artifact index for repair obligation tracking
            if message_plan and self._invalidation_engine is not None:
                from ..model.learning import DerivedArtifactProvenance
                from ..epistemics.artifact_index import (
                    IndexedArtifact, ArtifactKind,
                )
                for item in message_plan.content_items:
                    art = IndexedArtifact(
                        artifact_id=f"msg:{item.semantic_ref}",
                        artifact_kind=ArtifactKind.MESSAGE_ITEM,
                        provenance=DerivedArtifactProvenance(
                            supporting_assessment_refs=item.provenance_refs,
                            evidence_refs=item.provenance_refs,
                        ),
                    )
                    self._invalidation_engine.index.register(art)
        except Exception as e:
            errors.append(f"communicate failed: {e}")

        cycle = replace(cycle, message_plan=message_plan)

        # G3. Realize — language renderer produces surface text
        surface_payload = None
        try:
            if message_plan:
                surface_payload = self._message_renderer.render(
                    plan=message_plan,
                    language=message_plan.language or "en",
                )
        except Exception as e:
            errors.append(f"realization failed: {e}")

        cycle = replace(cycle, surface_payload=surface_payload)

        # G4. Dispatch — record transport outcome
        # (In a full implementation, this would dispatch through an
        # authorized channel. For now, we mark as dispatched.)
        if errors:
            existing = cycle.trace
            new_errors = (existing.errors if existing else ()) + tuple(errors)
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=(existing.stages if existing else ()) + ("communicate",),
                errors=new_errors,
            ))

        return cycle

    # ── H. OUTPUT COMMIT AND CONSOLIDATE ──

    def _output_commit_and_consolidate(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """H1-H7: Commit output, update common ground, schedule."""
        errors: list[str] = []

        # Record dispatched content in common ground
        # Commit common ground only after dispatch
        try:
            if cycle.message_plan and cycle.surface_payload:
                from ..response.common_ground import (
                    DispatchResult,
                    DispatchStatus,
                    DiscourseStatus,
                )
                from datetime import datetime, timezone

                # Only record if surface payload has content (was dispatched)
                if cycle.surface_payload.surface_text:
                    dispatch_result = DispatchResult(
                        message_plan_ref=cycle.message_plan.id,
                        status=DispatchStatus.DISPATCHED,
                        dispatched_at=datetime.now(timezone.utc).isoformat(),
                    )

                    # Map discourse function to discourse status
                    status_map = {
                        "inform": DiscourseStatus.ASSERTED,
                        "query": DiscourseStatus.ASKED,
                        "acknowledge": DiscourseStatus.ACCEPTED,
                        "correct": DiscourseStatus.CORRECTED,
                        "refuse": DiscourseStatus.REJECTED,
                        "repair": DiscourseStatus.CORRECTED,
                        "promise": DiscourseStatus.PROMISED,
                        "request": DiscourseStatus.UNRESOLVED,
                    }

                    for item in cycle.message_plan.content_items:
                        if item.semantic_ref:
                            disc_status = status_map.get(
                                item.discourse_function,
                                DiscourseStatus.ASSERTED,
                            )
                            self._common_ground_manager.record_dispatch(
                                proposition_ref=item.semantic_ref,
                                participant_ref="self",
                                discourse_status=disc_status,
                                dispatch_result=dispatch_result,
                            )
        except Exception as e:
            errors.append(f"common ground update failed: {e}")

        if errors:
            existing = cycle.trace
            new_errors = (existing.errors if existing else ()) + tuple(errors)
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=(existing.stages if existing else ()) + ("output_commit",),
                errors=new_errors,
            ))

        return cycle

    # ── Invalidation and repair ──

    def execute_correction(self, operation: Any) -> Any:
        """Execute a correction/retention operation.

        Per AGENTS.md §7.8, each operation targets exact evidence,
        proposition, sense, or schema revisions and triggers
        appropriate dependency reassessment.

        Returns CorrectionResult or None if retraction_engine not wired.
        """
        if self._retraction_engine is None:
            return None
        result = self._retraction_engine.execute(operation)

        # If the correction invalidates a schema, trigger invalidation cascade
        if self._invalidation_engine is not None and result.success:
            target = operation.target_ref
            if operation.kind.value == "supersession":
                self._invalidation_engine.on_schema_supersession(
                    old_schema_ref=target,
                    new_schema_ref="",
                )
            elif operation.kind.value == "support_retraction":
                self._invalidation_engine.on_evidence_retraction(target)
            elif operation.kind.value == "permission_revocation":
                self._invalidation_engine.on_schema_downgrade(
                    schema_revision_ref=target,
                )

        return result

    def _invalidate_and_repair(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """Process invalidation events and generate repair obligations.

        Per AGENTS.md §7.5, §7.8, LEARNING_PIPELINE.md §13-14:
        - Parent downgrade cascades to dependent artifacts
        - Historical output generates repair obligation
        - Evidence remains preserved
        - Stale effects must be re-authorized
        """
        errors: list[str] = []
        invalidation_result = None
        repair_obligations: tuple[Any, ...] = ()

        try:
            if self._invalidation_engine is not None:
                # Check for environment fingerprint changes
                current_fp = self._current_fingerprint()
                if cycle.snapshot and hasattr(cycle.snapshot, 'adapter_contract_hash'):
                    old_fp = cycle.snapshot.adapter_contract_hash
                    if old_fp and old_fp != current_fp:
                        inv_result = self._invalidation_engine.on_environment_change(
                            old_fingerprint=old_fp,
                            new_fingerprint=current_fp,
                        )
                        invalidation_result = inv_result

                # Collect repair obligations from invalidated dispatched messages
                if invalidation_result and invalidation_result.repair_obligation_ids:
                    repair_obligations = tuple(invalidation_result.repair_obligation_ids)

        except Exception as e:
            errors.append(f"invalidation failed: {e}")

        cycle = replace(
            cycle,
            invalidation_result=invalidation_result,
            repair_obligations=repair_obligations,
        )

        if errors:
            existing = cycle.trace
            new_errors = (existing.errors if existing else ()) + tuple(errors)
            cycle = replace(cycle, trace=CycleTrace(
                cycle_id=cycle.cycle_id,
                trigger_kind=cycle.trigger.trigger_kind,
                stages=(existing.stages if existing else ()) + ("invalidate",),
                errors=new_errors,
            ))

        return cycle

    # ── Finalize ──

    def _finalize(self, cycle: CognitiveCycle) -> CognitiveCycle:
        """Finalize trace with completion timestamp."""
        existing = cycle.trace
        stages = (existing.stages if existing else ()) + ("finalize",)
        errors = existing.errors if existing else ()

        cycle = replace(cycle, trace=CycleTrace(
            cycle_id=cycle.cycle_id,
            trigger_kind=cycle.trigger.trigger_kind,
            stages=stages,
            errors=errors,
            finished_at=datetime.now(timezone.utc),
        ))
        return cycle
