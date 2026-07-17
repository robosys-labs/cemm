"""Canonical CEMM v3.4.7 runtime composition root and core loop."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .context import (
    ContextCoordinator,
    DiscoursePatchCompiler,
    ReferentCandidateGenerator,
    WorldObservationCompiler,
)
from .goals import (
    CapabilityCoordinator,
    GoalArbiter,
    GoalGenerator,
    OperationAuthorizer,
    OperationExecutor,
    OperationLedgerCompiler,
    OperationPlanner,
    OutcomeReconciler,
)
from .inference import BoundedInferenceEngine, InferenceBudget
from .knowledge import EpistemicCoordinator, RetrievalResult, build_foundation_patch
from .language import LanguageAnalysisCoordinator, primary_language
from .learning import LearningCoordinator
from .lifecycle import CandidatePromotionCoordinator, SchemaLifecycleCoordinator
from .model import (
    CompetenceResult,
    CycleResult,
    CycleTrace,
    PatchCommitResult,
    SchemaStatus,
    canonical_data,
)
from .observations import ObservationFusionCoordinator
from .truth import TruthMaintenanceCoordinator
from .response import (
    ConversationalTonePlanner,
    EmissionLedgerCompiler,
    RealizationCoordinator,
    ResponseGoalGenerator,
    ResponseRanker,
    UOLResponsePlanner,
)
from .schema import PackageLoader, SemanticSchemaStore
from .storage import SemanticStore
from .understanding import UnderstandingCoordinator
from .version import VERSION


class Runtime:
    VERSION = VERSION

    def __init__(
        self,
        *,
        data_root: Path | None = None,
        database_path: str | Path = ":memory:",
        operation_adapters: Mapping[str, object] | None = None,
        granted_permissions: Iterable[str] = ("conversation", "internal"),
        max_operation_risk: float = 0.25,
    ):
        self._operation_adapters = dict(operation_adapters or {})
        self._granted_permissions = frozenset(granted_permissions)
        self._max_operation_risk = float(max_operation_risk)
        loader = PackageLoader(data_root)
        self.foundation = loader.load_foundation()
        self.language_packs = loader.load_languages()
        self.schema_store = SemanticSchemaStore(self.foundation)
        self.semantic_store = SemanticStore(database_path)
        self._bootstrap()
        self._hydrate_learned_state()

        self.language = LanguageAnalysisCoordinator(self.language_packs)
        self.observations = ObservationFusionCoordinator()
        self.context = ContextCoordinator(self.semantic_store)
        self.referents = ReferentCandidateGenerator(self.semantic_store, self.language_packs)
        self.lifecycle = SchemaLifecycleCoordinator(self.schema_store, self.semantic_store)
        self.promotion = CandidatePromotionCoordinator(self.semantic_store, self.schema_store)
        self.understanding = UnderstandingCoordinator(
            self.schema_store, self.semantic_store, lifecycle=self.lifecycle
        )
        self.epistemics = EpistemicCoordinator(self.semantic_store, self.schema_store)
        self.truth = TruthMaintenanceCoordinator(self.semantic_store)
        self.learning = LearningCoordinator(self.schema_store)
        self.inference = BoundedInferenceEngine(self.semantic_store, self.schema_store)
        self.goal_generator = GoalGenerator()
        self.goal_arbiter = GoalArbiter()
        self.capabilities = CapabilityCoordinator(self.semantic_store, self.schema_store)
        capability_patch = self.capabilities.compile_adapter_observation_patch(
            self._operation_adapters, expected_store_revision=self.semantic_store.revision
        )
        if capability_patch is not None:
            capability_result = self.semantic_store.apply_patch(capability_patch)
            if not capability_result.committed:
                raise RuntimeError("capability bootstrap failed: " + ";".join(capability_result.errors))
        self.operation_planner = OperationPlanner(self.schema_store)
        self.operation_authorizer = OperationAuthorizer(self.schema_store)
        self.operation_executor = OperationExecutor(self._operation_adapters)
        self.outcome_reconciler = OutcomeReconciler()
        self.operation_ledger = OperationLedgerCompiler()
        self.response_goals = ResponseGoalGenerator()
        self.response_ranker = ResponseRanker()
        self.response_planner = UOLResponsePlanner(self.semantic_store, self.schema_store)
        self.tone_planner = ConversationalTonePlanner(self.semantic_store)
        self.realizer = RealizationCoordinator(
            self.semantic_store, self.schema_store, self.language_packs
        )
        self.emission_ledger = EmissionLedgerCompiler()
        self.discourse = DiscoursePatchCompiler()
        self.world_observations = WorldObservationCompiler()

    def _hydrate_learned_state(self) -> None:
        schema_candidates, rule_candidates = self.semantic_store.hydrate_candidates()
        for ref, payload in schema_candidates:
            self.schema_store.add_schema_candidate(ref, payload)
        for ref, payload in rule_candidates:
            self.schema_store.add_rule_candidate(ref, payload)
        latest_schema: dict[str, Mapping[str, Any]] = {}
        for record in self.semantic_store.all_schema_revisions():
            latest_schema[str(record["schema_ref"])] = record
        for ref, record in latest_schema.items():
            self.schema_store.register_schema_revision(ref, record)
        for record in self.semantic_store.latest_rule_revisions():
            self.schema_store.register_rule_revision(str(record["rule_ref"]), record)

    def close(self) -> None:
        self.semantic_store.close()

    def _bootstrap(self) -> None:
        patch = build_foundation_patch(
            self.foundation,
            self.language_packs,
            expected_store_revision=self.semantic_store.revision,
        )
        result = self.semantic_store.apply_patch(patch)
        if not result.committed:
            raise RuntimeError("foundation bootstrap failed: " + ";".join(result.errors))

    def run_text(
        self,
        text: str,
        *,
        context_id: str = "default",
        language_hint: str | None = None,
        target_language: str | None = None,
        channel: str = "text",
        world_observations: Iterable[Mapping[str, Any]] = (),
        tone_constraints: Mapping[str, Any] | None = None,
    ) -> CycleResult:
        cycle_id = f"cycle:{uuid4().hex[:16]}"
        world_observations = tuple(world_observations)
        trace = CycleTrace(cycle_id=cycle_id, context_id=context_id)
        committed_patch_refs: list[str] = []
        commit_results: list[PatchCommitResult] = []

        trace.stage("ORIENT", {
            "version": self.VERSION,
            "foundation_fingerprint": self.foundation.fingerprint,
            "store_revision": self.semantic_store.revision,
            "channel": channel,
        })

        world_patch = self.world_observations.compile(
            context_ref=context_id,
            observations=world_observations,
            expected_store_revision=self.semantic_store.revision,
        )
        if world_patch is not None:
            world_result = self.semantic_store.apply_patch(world_patch)
            commit_results.append(world_result)
            if world_result.committed:
                committed_patch_refs.append(world_patch.patch_id)
            else:
                trace.errors.extend(world_result.errors)
        trace.stage("OBSERVE", {
            "text_length": len(text),
            "world_observation_count": len(world_observations),
        })

        context = self.context.snapshot(context_id)
        lattice = self.language.analyze(text, hint=language_hint)
        observation_lattice = self.observations.observe(
            context_ref=context_id,
            form_lattices=(lattice,),
            observations=world_observations,
        )
        evidence_patch = self.observations.compile_evidence_patch(
            observation_lattice, expected_store_revision=self.semantic_store.revision
        )
        if evidence_patch is not None:
            evidence_result = self.semantic_store.apply_patch(evidence_patch)
            commit_results.append(evidence_result)
            if evidence_result.committed:
                committed_patch_refs.append(evidence_patch.patch_id)
            else:
                trace.errors.extend(evidence_result.errors)
        trace.stage("ANALYZE", {
            "languages": [canonical_data(item) for item in lattice.language_hypotheses],
            "span_count": len(lattice.spans),
            "structure_count": len(lattice.structural_relations),
            "unresolved": lattice.unresolved_span_refs,
            "observation_modalities": observation_lattice.modality_refs,
            "analyzer_fingerprint": observation_lattice.analyzer_fingerprint,
        })

        candidate_map = self.referents.generate(lattice, context)
        trace.stage("GROUND_CANDIDATES", {
            "mention_count": len(candidate_map),
            "candidate_count": sum(len(items) for items in candidate_map.values()),
        })

        understood = self.understanding.understand(
            lattice, candidate_map, context,
            analyzer_fingerprint=observation_lattice.analyzer_fingerprint,
        )
        trace.stage("ACTIVATE_SCHEMAS_AND_PORTS", {
            "activation_refs": tuple(item.activation_id for item in understood.activations),
        })
        trace.stage("COMPOSE_AND_SELECT", {
            "hypothesis_count": len(understood.hypotheses),
            "selected_bundle_ref": understood.bundle.bundle_id if understood.bundle else None,
            "selected_proposition_refs": understood.bundle.proposition_refs if understood.bundle else (),
            "gaps": [canonical_data(item) for item in understood.gaps],
        })

        retrieval = self.epistemics.retrieve(understood.bundle, context_ref=context_id)
        trace.stage("RETRIEVE_AND_ASSESS", canonical_data(retrieval))

        learning_transaction = self.learning.inspect(
            lattice, understood.bundle, understood.gaps, context_ref=context_id
        )
        trace.stage("LEARNING_FRONTIER", canonical_data(learning_transaction) if learning_transaction else None)

        admission_patch = self.epistemics.compile_admission_patch(
            understood.bundle,
            context_ref=context_id,
            source_ref="referent:user",
            expected_store_revision=self.semantic_store.revision,
        )
        if admission_patch is not None:
            result = self.semantic_store.apply_patch(admission_patch)
            commit_results.append(result)
            if result.committed:
                committed_patch_refs.append(admission_patch.patch_id)
            else:
                trace.errors.extend(result.errors)

        learning_patch = self.learning.compile_patch(
            learning_transaction,
            expected_store_revision=self.semantic_store.revision,
        )
        if learning_patch is not None:
            result = self.semantic_store.apply_patch(learning_patch)
            commit_results.append(result)
            if result.committed:
                committed_patch_refs.append(learning_patch.patch_id)
            else:
                trace.errors.extend(result.errors)
        truth_refs = list(understood.bundle.proposition_refs if understood.bundle else ())
        truth_refs.extend(answer.matched_proposition_ref for answer in retrieval.answers)
        truth_assessments = tuple(
            self.truth.assess_proposition(ref, context_ref=context_id)
            for ref in dict.fromkeys(truth_refs)
        )
        truth_patch = self.truth.compile_assessment_patch(
            truth_assessments, context_ref=context_id,
            expected_store_revision=self.semantic_store.revision,
        )
        if truth_patch is not None:
            truth_result = self.semantic_store.apply_patch(truth_patch)
            commit_results.append(truth_result)
            if truth_result.committed:
                committed_patch_refs.append(truth_patch.patch_id)
            else:
                trace.errors.extend(truth_result.errors)
        trace.stage("VALIDATE_AND_COMMIT_PATCHES", {
            "results": [canonical_data(item) for item in commit_results],
            "truth_assessments": [canonical_data(item) for item in truth_assessments],
        })

        inferred = self.inference.infer(
            context_ref=context_id,
            budget=InferenceBudget(wall_clock_ms=50, allow_sensitive=False),
        )
        inference_patch = self.inference.compile_admission_patch(
            inferred, context_ref=context_id,
            expected_store_revision=self.semantic_store.revision,
        )
        if inference_patch is not None:
            inference_result = self.semantic_store.apply_patch(inference_patch)
            commit_results.append(inference_result)
            if inference_result.committed:
                committed_patch_refs.append(inference_patch.patch_id)
            else:
                trace.errors.extend(inference_result.errors)
        trace.stage("INFER", {
            "outcome": canonical_data(inferred.outcome),
            "admission_patch_ref": inference_patch.patch_id if inference_patch else None,
        })

        goals = self.goal_arbiter.select(self.goal_generator.generate(understood.bundle))
        plans = self.operation_planner.plan(goals, understood.bundle)
        capability = self.capabilities.state(
            context_id,
            permissions=self._granted_permissions,
            max_risk=self._max_operation_risk,
        )
        authorized_plans = tuple(
            self.operation_authorizer.authorize(plan, capability) for plan in plans
        )
        outcomes = tuple(self.operation_executor.execute(plan) for plan in authorized_plans)
        reconciliations = tuple(
            self.outcome_reconciler.reconcile(plan, outcome)
            for plan, outcome in zip(authorized_plans, outcomes)
        )
        effect_commit_refs: list[str] = []
        for plan, outcome in zip(authorized_plans, outcomes):
            effect_patch = self.outcome_reconciler.admissible_effect_patch(
                plan, outcome, expected_store_revision=self.semantic_store.revision
            )
            if effect_patch is None:
                continue
            effect_result = self.semantic_store.apply_patch(effect_patch)
            commit_results.append(effect_result)
            if effect_result.committed:
                committed_patch_refs.append(effect_patch.patch_id)
                effect_commit_refs.append(effect_patch.patch_id)
            else:
                trace.errors.extend(effect_result.errors)
        operation_ledger_patch = self.operation_ledger.compile(
            authorized_plans, outcomes, context_ref=context_id,
            expected_store_revision=self.semantic_store.revision,
        )
        if operation_ledger_patch is not None:
            ledger_result = self.semantic_store.apply_patch(operation_ledger_patch)
            commit_results.append(ledger_result)
            if ledger_result.committed:
                committed_patch_refs.append(operation_ledger_patch.patch_id)
            else:
                trace.errors.extend(ledger_result.errors)
        trace.stage("GOALS_AND_OPERATIONS", {
            "goals": [canonical_data(item) for item in goals],
            "plans": [canonical_data(item) for item in authorized_plans],
            "outcomes": [canonical_data(item) for item in outcomes],
            "reconciliations": reconciliations,
            "effect_commit_refs": tuple(effect_commit_refs),
        })

        response_candidates = self.response_goals.generate(
            bundle=understood.bundle,
            retrieval=retrieval,
            gaps=understood.gaps,
            commit_results=commit_results,
            learning=learning_transaction,
            operation_outcomes=outcomes,
            truth_assessments=truth_assessments,
        )
        selected_response_goals = self.response_ranker.select(response_candidates)
        selected_language = self._target_language(
            target_language=target_language,
            language_hint=language_hint,
            lattice_language=primary_language(lattice),
        )
        resolved_tone_constraints = self.tone_planner.derive(
            context_id, explicit=tone_constraints
        )
        response_plan = self.response_planner.plan(
            selected_response_goals,
            target_language=selected_language,
            tone_constraints=resolved_tone_constraints,
        )
        trace.stage("RESPONSE_GOALS_AND_UOL", {
            "candidates": [canonical_data(item) for item in response_candidates],
            "selected": [item.response_goal_id for item in selected_response_goals],
            "plan": canonical_data(response_plan) if response_plan else None,
        })

        realized = self.realizer.realize(response_plan)
        if realized is not None and not realized.proof.authorized:
            trace.errors.extend(realized.proof.reasons)
        emission_patch = self.emission_ledger.compile(
            realized, context_ref=context_id,
            expected_store_revision=self.semantic_store.revision,
        )
        if emission_patch is not None:
            emission_result = self.semantic_store.apply_patch(emission_patch)
            commit_results.append(emission_result)
            if emission_result.committed:
                committed_patch_refs.append(emission_patch.patch_id)
            else:
                trace.errors.extend(emission_result.errors)
        trace.stage("REALIZE_AND_AUTHORIZE", canonical_data(realized) if realized else None)

        discourse_patch = self.discourse.compile(
            cycle_id=cycle_id,
            context=context,
            bundle=understood.bundle,
            language_tag=selected_language,
            speaker_ref="referent:user",
            raw_observation_ref=cycle_id,
            tone_constraints=resolved_tone_constraints,
            expected_store_revision=self.semantic_store.revision,
        )
        if discourse_patch is not None:
            result = self.semantic_store.apply_patch(discourse_patch)
            if result.committed:
                committed_patch_refs.append(discourse_patch.patch_id)
            else:
                trace.errors.extend(result.errors)
            commit_results.append(result)
        trace.stage("OUTPUT_COMMIT_AND_FINALIZE", {
            "dispatched": bool(realized and realized.text and realized.proof.authorized),
            "store_revision": self.semantic_store.revision,
            "committed_patch_refs": tuple(committed_patch_refs),
        })

        return CycleResult(
            cycle_id=cycle_id,
            context_id=context_id,
            output_text=realized.text if realized and realized.proof.authorized else "",
            target_language=selected_language,
            selected_bundle=understood.bundle,
            response_plan=response_plan,
            emission_proof=realized.proof if realized else None,
            gaps=understood.gaps,
            committed_patch_refs=tuple(committed_patch_refs),
            trace=trace,
            observation_lattice=observation_lattice,
            truth_assessments=truth_assessments,
        )

    def promote_schema_candidate(
        self,
        candidate_ref: str,
        *,
        context_id: str = "default",
        competence_results: Iterable[CompetenceResult] = (),
        target_status: SchemaStatus = SchemaStatus.PROVISIONAL,
    ) -> PatchCommitResult | None:
        patch = self.promotion.compile_schema_promotion(
            candidate_ref, context_ref=context_id,
            competence_results=tuple(competence_results),
            expected_store_revision=self.semantic_store.revision,
            target_status=target_status,
        )
        if patch is None:
            return None
        result = self.semantic_store.apply_patch(patch)
        if result.committed:
            schema_ref = next((
                operation.target_ref for operation in patch.operations
                if operation.kind.value == "upsert_schema_revision"
            ), candidate_ref)
            record = self.semantic_store.latest_schema_revision(schema_ref, context_ref=context_id)
            if record is not None:
                self.schema_store.register_schema_revision(schema_ref, record)
            self.lifecycle.invalidate_cache((schema_ref,))
        return result

    def promote_rule_candidate(
        self,
        candidate_ref: str,
        *,
        context_id: str = "default",
        target_status: SchemaStatus = SchemaStatus.PROVISIONAL,
        competence_results: Iterable[CompetenceResult] = (),
    ) -> PatchCommitResult | None:
        patch = self.promotion.compile_rule_promotion(
            candidate_ref, context_ref=context_id,
            expected_store_revision=self.semantic_store.revision,
            target_status=target_status,
            competence_results=tuple(competence_results),
        )
        if patch is None:
            return None
        result = self.semantic_store.apply_patch(patch)
        if result.committed:
            rule_ref = next((
                operation.target_ref for operation in patch.operations
                if operation.kind.value == "upsert_rule_revision"
            ), candidate_ref)
            for record in self.semantic_store.latest_rule_revisions(context_ref=context_id):
                if str(record["rule_ref"]) == rule_ref:
                    self.schema_store.register_rule_revision(rule_ref, record)
            self.lifecycle.invalidate_cache()
        return result

    def run_text_result(self, text: str, **kwargs: Any):
        from ..app.public_result import project_cycle
        return project_cycle(self.run_text(text, **kwargs))

    def _target_language(
        self,
        *,
        target_language: str | None,
        language_hint: str | None,
        lattice_language: str,
    ) -> str:
        for candidate in (target_language, language_hint, lattice_language):
            if not candidate:
                continue
            tag = candidate.split("-", 1)[0].casefold()
            if tag in self.language_packs:
                return tag
        return sorted(self.language_packs)[0]
