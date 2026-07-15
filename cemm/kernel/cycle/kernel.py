"""Canonical v3.4.2 cycle with real semantic commit and bounded inference."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

from ..epistemics.evaluator import (
    EvidenceRecord as EpistemicEvidenceRecord,
)
from ..inference.engine import InferenceBudget
from ..model.cycle import (
    CognitiveCycle, CycleTrigger, pin_snapshot,
)
from ..model.trace import CycleTrace

class CognitiveKernel:
    def __init__(
        self, *, schema_store, semantic_memory,
        percept_adapter, semantic_composer,
        grounding_resolver, interpretation_resolver,
        workspace_controller, semantic_retriever,
        epistemic_evaluator, capability_evaluator,
        gap_detector, self_report_builder,
        learning_coordinator, goal_arbiter,
        planner, operation_authorizer,
        operation_executor, outcome_reconciler,
        commit_coordinator, fact_compiler,
        inference_engine, response_planner,
        message_renderer, common_ground_manager,
        **_,
    ):
        self._schema_store = schema_store
        self._memory = semantic_memory
        self._percept = percept_adapter
        self._composer = semantic_composer
        self._grounding = grounding_resolver
        self._interpreter = interpretation_resolver
        self._workspace = workspace_controller
        self._retriever = semantic_retriever
        self._epistemic = epistemic_evaluator
        self._capability = capability_evaluator
        self._gaps = gap_detector
        self._self_report = self_report_builder
        self._learning = learning_coordinator
        self._goal_arbiter = goal_arbiter
        self._planner = planner
        self._authorizer = operation_authorizer
        self._executor = operation_executor
        self._reconciler = outcome_reconciler
        self._commit = commit_coordinator
        self._fact_compiler = fact_compiler
        self._inference = inference_engine
        self._response = response_planner
        self._renderer = message_renderer
        self._common_ground = common_ground_manager

    def run(self, trigger):
        cycle = self._orient(trigger)
        cycle = self._understand(cycle)
        cycle = self._know(cycle)
        cycle = self._trace(cycle, "decide", ())
        cycle = self._trace(cycle, "act", ())
        cycle = self._critical_commit(cycle)
        cycle = self._communicate(cycle)
        cycle = self._output_commit(cycle)
        cycle = self._trace(cycle, "invalidate", ())
        return self._finalize(cycle)

    def _orient(self, trigger):
        cycle_id = f"cycle:{uuid4().hex[:12]}"
        return CognitiveCycle(
            cycle_id=cycle_id,
            trigger=trigger,
            snapshot=pin_snapshot(
                schema_store_revision=(
                    self._schema_store.store_revision
                ),
                semantic_memory_revision=(
                    self._memory.revision
                ),
                kernel_foundation_version=(
                    "v3.4.2-data"
                ),
                grounding_policy_version=(
                    "typed-ports-v3.4.2"
                ),
                competence_suite_hash=(
                    "definition-package-v1"
                ),
                inference_policy_version=(
                    "bounded-rules-v1"
                ),
                adapter_contract_hash=(
                    "language-pack-v1"
                ),
                truth_maintenance_version=(
                    "four-state-v3.4"
                ),
            ),
            trace=CycleTrace(
                cycle_id=cycle_id,
                trigger_kind=trigger.trigger_kind,
                stages=("orient",),
            ),
        )

    def _understand(self, cycle):
        errors = []
        evidence = graphs = groundings = selections = ()
        dialogue = None
        try:
            evidence = tuple(self._percept.perceive(
                input_signals=(
                    cycle.trigger.input_signals
                ),
                signal_ids=cycle.trigger.signal_ids,
                context_id=cycle.trigger.context_id,
            ))
            graphs = tuple(
                self._composer.compose(item)
                for item in evidence
            )
            groundings = tuple(
                self._grounding.ground_graph(
                    graph, item,
                    context_ref=(
                        cycle.trigger.context_id
                    ),
                    environment_fingerprint=(
                        self._fingerprint(cycle)
                    ),
                )
                for graph, item in zip(
                    graphs, evidence
                )
            )
            selected = []
            for index, graph in enumerate(graphs):
                result = self._interpreter.resolve(
                    candidate_graph=graph,
                    grounding_assessments=(
                        [groundings[index]]
                        if index < len(groundings)
                        else []
                    ),
                )
                selected.extend(result.selected)
            selections = tuple(selected)
            dialogue = (
                self._learning.resolve_dialogue_turn(
                    context_ref=(
                        cycle.trigger.context_id
                    ),
                    selected_interpretations=(
                        selections
                    ),
                    surface_evidence=evidence,
                )
            )
        except Exception as exc:
            errors.append(f"understand failed: {exc}")
        cycle = replace(
            cycle,
            surface_evidence=evidence,
            meaning_candidates=graphs,
            grounded_candidates=groundings,
            selected_interpretations=selections,
            dialogue_resolution=dialogue,
            dialogue_obligations=(
                self._learning.pending_obligations(
                    cycle.trigger.context_id
                )
            ),
        )
        return self._trace(
            cycle, "understand", errors
        )

    def _know(self, cycle):
        errors = []
        retrieval = epistemic = knowledge = gaps = ()
        workspace = None
        try:
            open_ports = tuple(
                port
                for graph in cycle.meaning_candidates
                for port in graph.open_ports
            )
            batch = self._retriever.retrieve(
                selected_interpretations=list(
                    cycle.selected_interpretations
                ),
                open_ports=open_ports,
                context_ref=cycle.trigger.context_id,
            )
            retrieval = tuple(batch.results)

            assessments, knowledge_items = [], []
            for interpretation in (
                cycle.selected_interpretations
            ):
                if interpretation.communicative_force not in {
                    "assert", "correct"
                }:
                    continue
                proposition, context = (
                    self._proposition_context(
                        cycle, interpretation
                    )
                )
                grounding = self._predication_grounding(
                    cycle,
                    interpretation.predication_ref,
                )
                if proposition is None or context is None:
                    continue
                evidence = (
                    EpistemicEvidenceRecord(
                        evidence_id=(
                            f"evidence:{cycle.cycle_id}:"
                            f"{proposition.id}"
                        ),
                        proposition_ref=proposition.id,
                        supports=True,
                        source_ref="input:user",
                        confidence=max(
                            0.35,
                            interpretation.confidence,
                        ),
                        is_independent=False,
                        lineage_root=cycle.cycle_id,
                        context_ref=context.id,
                    ),
                )
                assessment = self._epistemic.evaluate(
                    proposition=proposition,
                    context=context,
                    evidence=evidence,
                    schema_use_profile=(
                        grounding.use_profile
                        if grounding else None
                    ),
                    accessible=True,
                    permission_allowed=True,
                    environment_fingerprint=(
                        self._fingerprint(cycle)
                    ),
                )
                assessments.append(assessment)
                knowledge_items.append(
                    self._epistemic.derive_knowledge(
                        proposition=proposition,
                        context=context,
                        assessment=assessment,
                        is_grounded=bool(
                            grounding
                            and grounding
                            .is_structurally_usable
                            and not grounding
                            .unresolved_role_refs
                        ),
                        schema_use_profile=(
                            grounding.use_profile
                            if grounding else None
                        ),
                    )
                )
            epistemic = tuple(assessments)
            knowledge = tuple(knowledge_items)

            all_gaps = []
            suppress = bool(
                cycle.dialogue_resolution
                and getattr(
                    cycle.dialogue_resolution,
                    "suppress_fresh_lexical_gaps",
                    False,
                )
            )
            for index, graph in enumerate(
                cycle.meaning_candidates
            ):
                result = self._gaps.detect(
                    candidate_graph=graph,
                    grounding_assessments=(
                        [cycle.grounded_candidates[index]]
                        if index
                        < len(cycle.grounded_candidates)
                        else []
                    ),
                    epistemic_assessments=list(
                        epistemic
                    ),
                    selected_interpretations=list(
                        cycle.selected_interpretations
                    ),
                    suppress_fresh_lexical_gaps=(
                        suppress
                    ),
                )
                all_gaps.extend(result.gaps)
            gaps = tuple(self._dedupe_gaps(
                all_gaps
            ))
            transactions = []
            for gap in gaps:
                if gap.learnable:
                    transactions.append(
                        self._learning.open_transaction(
                            gap,
                            context_ref=(
                                cycle.trigger.context_id
                            ),
                        )
                    )
            if (
                cycle.dialogue_resolution
                and cycle.dialogue_resolution
                .transaction_ref
            ):
                transaction = (
                    self._learning.get_transaction(
                        cycle.dialogue_resolution
                        .transaction_ref
                    )
                )
                if transaction:
                    transactions.append(transaction)
            transactions = tuple({
                tx.id: tx for tx in transactions
            }.values())
            workspace = self._workspace.focus(
                selected_interpretations=list(
                    cycle.selected_interpretations
                ),
                epistemic_assessments=list(
                    epistemic
                ),
                gaps=list(gaps),
            )
        except Exception as exc:
            errors.append(f"know failed: {exc}")
            transactions = cycle.learning_transactions
        cycle = replace(
            cycle,
            retrieval_results=retrieval,
            epistemic_assessments=epistemic,
            knowledge_assessments=knowledge,
            gaps=gaps,
            learning_transactions=transactions,
            workspace=workspace,
        )
        return self._trace(cycle, "know", errors)

    def _critical_commit(self, cycle):
        errors = []
        mutations = outcome = None
        try:
            compilation = (
                self._fact_compiler.compile(cycle)
            )
            mutations = compilation.mutation_set
            if mutations is not None:
                outcome = self._commit.commit(
                    mutations
                )
                if outcome.required_satisfied:
                    refs = tuple(
                        ref
                        for result in outcome.results
                        for ref in result.record_refs
                    )
                    seed = tuple(
                        self._memory.get(ref)
                        for ref in refs
                        if self._memory.get(ref)
                    )
                    self._inference.infer(
                        seed_facts=seed,
                        rules=(),
                        budget=InferenceBudget(),
                        dependency_fingerprint=self._fingerprint(
                            cycle
                        ),
                    )
        except Exception as exc:
            errors.append(
                f"critical commit failed: {exc}"
            )
        cycle = replace(
            cycle,
            critical_mutations=mutations,
            critical_commit=outcome,
        )
        return self._trace(
            cycle, "critical_commit", errors
        )

    @staticmethod
    def _response_language(cycle):
        if not cycle.surface_evidence:
            return "en"
        tags = {
            evidence.language_tag
            for evidence in cycle.surface_evidence
            if getattr(evidence, "language_tag", None)
        }
        return next(iter(tags), "en")

    @staticmethod
    def _build_response_intents(cycle):
        intents = []
        from ..response.planner import ResponseIntent, ResponseIntentRole
        for interp in getattr(
            cycle, "selected_interpretations", ()
        ):
            roles = tuple(
                ResponseIntentRole(
                    role_key=rb.role_schema_ref.removeprefix("role:"),
                    value_ref=rb.filler_ref,
                    value_kind="referent",
                )
                for rb in getattr(interp, "role_bindings", ())
            )
            intents.append(ResponseIntent(
                intent_id=interp.id,
                predicate_key=getattr(
                    interp, "predicate_semantic_key", ""
                ),
                roles=roles,
                communicative_force=getattr(
                    interp, "communicative_force", "assert"
                ),
                context_ref=getattr(
                    interp, "context_ref", "actual"
                ),
                provenance_refs=(
                    (interp.proposition_ref,)
                    if getattr(interp, "proposition_ref", "")
                    else ()
                ),
            ))
        return tuple(intents)

    def _communicate(self, cycle):
        errors = []
        plan = authorization = payload = None
        try:
            from ..response.planner import (
                ContentSelectionInput,
            )
            response_intents = self._build_response_intents(
                cycle
            )
            selection = ContentSelectionInput(
                response_intents=response_intents,
                requirement_assessments=(),
                commit_outcome=(
                    cycle.critical_commit
                ),
                selected_interpretations=(
                    cycle.selected_interpretations
                ),
                retrieval_results=(
                    cycle.retrieval_results
                ),
                capability_assessments=(
                    cycle.capability_assessments
                ),
                gaps=cycle.gaps,
                learning_transactions=(
                    cycle.learning_transactions
                ),
                language=self._response_language(
                    cycle
                ),
            )
            plan = self._response.plan_response(
                selection
            )
            plan_lang = getattr(
                plan, "language_tag",
                getattr(plan, "language", "en"),
            )
            authorization = self._renderer.authorize(
                plan,
                language=plan_lang,
                environment_fingerprint=(
                    self._fingerprint(cycle)
                ),
            )
            payload = self._renderer.render(
                plan,
                language=plan_lang,
                authorization=authorization,
                environment_fingerprint=(
                    self._fingerprint(cycle)
                ),
            )
            if hasattr(self._renderer, "validate_round_trip") and not self._renderer.validate_round_trip(
                payload
            ):
                raise ValueError(
                    "surface leakage validation failed"
                )
        except Exception as exc:
            errors.append(
                f"communicate failed: {exc}"
            )
        cycle = replace(
            cycle,
            message_plan=plan,
            realization_authorization=(
                authorization
            ),
            surface_payload=payload,
        )
        return self._trace(
            cycle, "communicate", errors
        )

    def _output_commit(self, cycle):
        errors = []
        output_event = None
        try:
            if (
                cycle.message_plan
                and cycle.surface_payload
                and cycle.surface_payload
                .surface_text
            ):
                from ..response.common_ground import (
                    DispatchResult,
                    DispatchStatus,
                    DiscourseStatus,
                )
                dispatched_at = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )
                plan_id = getattr(
                    cycle.message_plan, "plan_id",
                    getattr(cycle.message_plan, "id", ""),
                )
                dispatch = DispatchResult(
                    message_plan_ref=plan_id,
                    status=(
                        DispatchStatus.DISPATCHED
                    ),
                    transport_outcome=(
                        "local_projection"
                    ),
                    dispatched_at=dispatched_at,
                )
                realized = set(
                    cycle.surface_payload
                    .realized_item_refs
                )
                output_event = {
                    "message_plan_ref": plan_id,
                    "realized_item_refs":
                    tuple(realized),
                    "dispatched_at": dispatched_at,
                }
                items = getattr(
                    cycle.message_plan,
                    "content_items",
                    getattr(
                        cycle.message_plan,
                        "clauses", (),
                    ),
                )
                for item in items:
                    sem_ref = getattr(
                        item, "semantic_ref",
                        getattr(item, "clause_id", ""),
                    )
                    if sem_ref not in realized:
                        continue
                    discourse_fn = getattr(
                        item, "discourse_function",
                        getattr(
                            item, "communicative_force",
                            "inform",
                        ),
                    )
                    status = (
                        DiscourseStatus.ASKED
                        if discourse_fn == "query"
                        else DiscourseStatus.ASSERTED
                    )
                    prop_ref = getattr(
                        item, "semantic_ref",
                        getattr(
                            item, "clause_id",
                            sem_ref,
                        ),
                    )
                    self._common_ground.record_dispatch(
                        proposition_ref=prop_ref,
                        participant_ref="self",
                        discourse_status=status,
                        dispatch_result=dispatch,
                    )
                    if (
                        hasattr(item, "content_kind")
                        and item.content_kind
                        == "learning_probe"
                    ):
                        self._learning.register_probe_dispatch(
                            context_ref=(
                                cycle.trigger.context_id
                            ),
                            message_item=item,
                            gaps=cycle.gaps,
                            output_event_ref=(
                                cycle.message_plan.id
                            ),
                        )
                    elif (
                        item.content_kind
                        in {
                            "learning_progress",
                            "dialogue_gap_explanation",
                        }
                        and cycle.dialogue_resolution
                    ):
                        self._learning.register_followup_dispatch(
                            context_ref=(
                                cycle.trigger.context_id
                            ),
                            message_item=item,
                            dialogue_resolution=(
                                cycle.dialogue_resolution
                            ),
                            output_event_ref=(
                                cycle.message_plan.id
                            ),
                        )
        except Exception as exc:
            errors.append(
                f"output commit failed: {exc}"
            )
        cycle = replace(
            cycle,
            output_event=output_event,
            dialogue_obligations=(
                self._learning.pending_obligations(
                    cycle.trigger.context_id
                )
            ),
        )
        return self._trace(
            cycle, "output_commit", errors
        )

    def _finalize(self, cycle):
        trace = cycle.trace
        return replace(
            cycle,
            trace=replace(
                trace,
                stages=(
                    *trace.stages, "finalize"
                ),
                finished_at=datetime.now(
                    timezone.utc
                ),
            ),
        )

    @staticmethod
    def _trace(cycle, stage, errors):
        trace = cycle.trace
        return replace(
            cycle,
            trace=replace(
                trace,
                stages=(*trace.stages, stage),
                errors=(
                    *trace.errors, *tuple(errors)
                ),
            ),
        )

    @staticmethod
    def _fingerprint(cycle):
        return (
            f"schema="
            f"{cycle.snapshot.schema_store_revision};"
            f"memory="
            f"{cycle.snapshot.semantic_memory_revision};"
            f"foundation="
            f"{cycle.snapshot.kernel_foundation_version}"
        )

    @staticmethod
    def _response_language(cycle):
        return next(
            (
                evidence.language_tag
                for evidence
                in cycle.surface_evidence
                if evidence.language_tag
            ),
            "en",
        )

    @staticmethod
    def _proposition_context(
        cycle, interpretation
    ):
        proposition = context = None
        for graph in cycle.meaning_candidates:
            for candidate in (
                graph.candidate_propositions
            ):
                if (
                    candidate.proposition.id
                    == interpretation.proposition_ref
                ):
                    proposition = (
                        candidate.proposition
                    )
            for candidate in (
                graph.candidate_contexts
            ):
                if (
                    candidate.context_frame.id
                    == interpretation.context_ref
                ):
                    context = (
                        candidate.context_frame
                    )
        return proposition, context

    @staticmethod
    def _predication_grounding(
        cycle, predication_ref
    ):
        for grounding in (
            cycle.grounded_candidates
        ):
            found = grounding.for_predication(
                predication_ref
            )
            if found is not None:
                return found
        return None

    @staticmethod
    def _dedupe_gaps(gaps: Iterable):
        result, seen = [], set()
        for gap in gaps:
            key = (
                gap.gap_kind,
                gap.target_artifact_ref,
                tuple(gap.missing_fields),
            )
            if key not in seen:
                seen.add(key)
                result.append(gap)
        return result
