"""App runtime — dependency construction and public entry point.

Per completion-plan.md Stage 1:
- Move dependency construction to app/runtime.py
- Public app entry returns CognitiveCycle / public result projection
- RuntimeCycleResult no longer drives the canonical path

This module constructs all v3.4 canonical components, wires the
CognitiveKernel, and provides a public run() entry point.
"""
from __future__ import annotations

from typing import Any

from ..kernel.cycle.kernel import CognitiveKernel
from ..kernel.model.cycle import CycleTrigger
from ..kernel.schema.store import SemanticSchemaStore
from ..kernel.understanding.composer import SemanticComposer
from ..kernel.understanding.grounding import GroundingResolver
from ..kernel.understanding.interpreter import InterpretationResolver
from ..kernel.understanding.gap_detector import GapDetector
from ..kernel.understanding.workspace import WorkspaceController
from ..kernel.epistemics.evaluator import EpistemicEvaluator
from ..kernel.epistemics.retriever import SemanticRetriever
from ..kernel.epistemics.truth_maintenance import TruthMaintenance
from ..kernel.epistemics.invalidation_engine import CrossSchemaLaunderingGuard
from ..kernel.self_model.capability_evaluator import CapabilityEvaluator
from ..kernel.self_model.self_report import SelfReportBuilder
from ..kernel.learning.coordinator import LearningCoordinator
from ..kernel.execution.goal_arbiter import GoalArbiter
from ..kernel.execution.planner import Planner
from ..kernel.execution.executor import OperationExecutor
from ..kernel.execution.authorizer import OperationAuthorizer
from ..kernel.execution.reconciliation import OutcomeReconciler
from ..kernel.execution.commit import CommitCoordinator
from ..kernel.response.planner import ResponsePlanner
from ..kernel.response.common_ground import CommonGroundManager
from ..kernel.retirement.cutover import AuthoritativeCutoverVerifier


class Runtime:
    """Canonical v3.4 runtime assembly.

    Constructs all canonical components, wires the CognitiveKernel,
    and provides a public run() entry that returns CognitiveCycle.
    """

    def __init__(
        self,
        *,
        legacy_perceptor: Any | None = None,
        legacy_percept_bridge: Any | None = None,
        predicate_schema_store: Any | None = None,
        load_boot: bool = True,
    ) -> None:
        # Construct canonical v3.4 components
        self._schema_store = SemanticSchemaStore()

        # Load and validate boot schemas
        self._boot_report: Any | None = None
        self._boot_unresolved_deps: tuple[str, ...] = ()
        if load_boot:
            from ..kernel.boot.validation import BootValidator
            from ..kernel.boot.manifest import build_boot_manifest
            validator = BootValidator()
            manifest = build_boot_manifest()
            self._boot_report = validator.validate_boot(self._schema_store, manifest)
            if self._boot_report.status == "halted":
                raise RuntimeError(
                    f"Boot validation halted: {self._boot_report.halted_reasons}"
                )
            validator.register_boot_schemas(
                self._schema_store, manifest, self._boot_report
            )
            # Verify all dependencies resolve after registration
            unresolved, _ = validator.verify_dependencies(
                self._schema_store, manifest
            )
            if unresolved:
                # Log but don't halt — unresolved deps downgrade dependents
                self._boot_unresolved_deps = unresolved

        self._semantic_composer = SemanticComposer(store=self._schema_store)
        self._grounding_resolver = GroundingResolver(store=self._schema_store)
        self._interpretation_resolver = InterpretationResolver()
        self._gap_detector = GapDetector()
        self._workspace_controller = WorkspaceController()
        self._truth_maintenance = TruthMaintenance()
        self._cross_schema_guard = CrossSchemaLaunderingGuard()
        self._epistemic_evaluator = EpistemicEvaluator(
            truth_maintenance=self._truth_maintenance,
            cross_schema_guard=self._cross_schema_guard,
        )
        self._semantic_retriever = SemanticRetriever(
            schema_store=self._schema_store,
            truth_maintenance=self._truth_maintenance,
        )
        self._capability_evaluator = CapabilityEvaluator()
        self._self_report_builder = SelfReportBuilder()
        self._learning_coordinator = LearningCoordinator(
            store=self._schema_store,
            evaluator=self._epistemic_evaluator,
        )
        self._goal_arbiter = GoalArbiter()
        self._planner = Planner(schema_store=self._schema_store)
        self._operation_executor = OperationExecutor()
        self._operation_authorizer = OperationAuthorizer()
        self._outcome_reconciler = OutcomeReconciler()
        self._commit_coordinator = CommitCoordinator()
        self._response_planner = ResponsePlanner()
        from ..kernel.response.renderer import MessageRenderer
        self._message_renderer = MessageRenderer()
        self._common_ground_manager = CommonGroundManager()

        # Stage 8: Invalidation, correction, retention
        from ..kernel.epistemics.artifact_index import DerivedArtifactIndex
        from ..kernel.epistemics.invalidation_engine import InvalidationEngine
        from ..kernel.epistemics.invalidation_events import InvalidationEventBus
        from ..kernel.epistemics.replay_safety import ReplaySafetyManager
        from ..kernel.correction.retraction_engine import RetractionEngine
        from ..kernel.learning.replay_queue import ReplayQueue

        # Reuse the truth_maintenance instance already created above
        self._artifact_index = DerivedArtifactIndex()
        self._invalidation_event_bus = InvalidationEventBus()
        self._invalidation_engine = InvalidationEngine(
            index=self._artifact_index,
            truth_maintenance=self._truth_maintenance,
            event_bus=self._invalidation_event_bus,
        )
        self._retraction_engine = RetractionEngine()
        self._replay_queue = ReplayQueue()
        self._replay_safety_manager = ReplaySafetyManager(
            replay_queue=self._replay_queue,
        )

        # Language adapter — native v3.4 or legacy boundary
        if legacy_perceptor is not None:
            # Legacy path: use boundary adapter wrapping MeaningPerceptor
            from ..legacy.v3_3.percept_adapter import LegacyV33PerceptAdapter
            self._percept_adapter = LegacyV33PerceptAdapter(
                perceptor=legacy_perceptor,
                percept_bridge=legacy_percept_bridge,
            )
        else:
            # Native path: use English language adapter directly
            from ..language.en.adapter import EnglishLanguageAdapter
            self._percept_adapter = _NativePerceptAdapter(
                language_adapter=EnglishLanguageAdapter(),
            )

        # Cutover verifier — register all authorities
        self._cutover_verifier = AuthoritativeCutoverVerifier()
        self._cutover_verifier.register("surface_analysis", "PerceptAdapter")
        self._cutover_verifier.register("semantic_composition", "SemanticComposer")
        self._cutover_verifier.register(
            "referent_sense_role_grounding", "GroundingResolver"
        )
        self._cutover_verifier.register(
            "schema_identity_version_resolution", "SemanticSchemaStore"
        )
        self._cutover_verifier.register(
            "structural_grounding_assessment", "GroundingResolver"
        )
        self._cutover_verifier.register("competence_execution", "CapabilityEvaluator")
        self._cutover_verifier.register(
            "schema_lifecycle_activation", "SemanticSchemaStore"
        )
        self._cutover_verifier.register(
            "recursive_cluster_classification", "SemanticSchemaStore"
        )
        self._cutover_verifier.register(
            "interpretation_selection", "InterpretationResolver"
        )
        self._cutover_verifier.register("context_isolation", "EpistemicEvaluator")
        self._cutover_verifier.register("semantic_retrieval", "SemanticRetriever")
        self._cutover_verifier.register(
            "truth_and_context_admissibility", "EpistemicEvaluator"
        )
        self._cutover_verifier.register("current_schema_use", "GroundingResolver")
        self._cutover_verifier.register(
            "derived_cognition_retraction", "InvalidationEngine"
        )
        self._cutover_verifier.register("current_capability", "CapabilityEvaluator")
        self._cutover_verifier.register("gap_creation", "GapDetector")
        self._cutover_verifier.register("learning_lifecycle", "LearningCoordinator")
        self._cutover_verifier.register(
            "replay_scheduling_idempotence", "ReplaySafetyManager"
        )
        self._cutover_verifier.register("active_goals", "GoalArbiter")
        self._cutover_verifier.register("plan_selection", "Planner")
        self._cutover_verifier.register(
            "operation_authorization", "OperationAuthorizer"
        )
        self._cutover_verifier.register("execution", "OperationExecutor")
        self._cutover_verifier.register(
            "outcome_reconciliation", "OutcomeReconciler"
        )
        self._cutover_verifier.register("persistent_mutation", "CommitCoordinator")
        self._cutover_verifier.register("common_ground", "CommonGroundManager")
        self._cutover_verifier.register("response_content", "ResponsePlanner")
        self._cutover_verifier.register(
            "surface_realization", "MessageRenderer"
        )
        self._cutover_verifier.register("cycle_scheduling", "CognitiveKernel")

        # Wire the kernel
        self._kernel = CognitiveKernel(
            schema_store=self._schema_store,
            percept_adapter=self._percept_adapter,
            semantic_composer=self._semantic_composer,
            grounding_resolver=self._grounding_resolver,
            interpretation_resolver=self._interpretation_resolver,
            workspace_controller=self._workspace_controller,
            semantic_retriever=self._semantic_retriever,
            epistemic_evaluator=self._epistemic_evaluator,
            capability_evaluator=self._capability_evaluator,
            gap_detector=self._gap_detector,
            self_report_builder=self._self_report_builder,
            learning_coordinator=self._learning_coordinator,
            goal_arbiter=self._goal_arbiter,
            planner=self._planner,
            operation_authorizer=self._operation_authorizer,
            operation_executor=self._operation_executor,
            outcome_reconciler=self._outcome_reconciler,
            commit_coordinator=self._commit_coordinator,
            response_planner=self._response_planner,
            message_renderer=self._message_renderer,
            common_ground_manager=self._common_ground_manager,
            invalidation_engine=self._invalidation_engine,
            retraction_engine=self._retraction_engine,
            replay_safety_manager=self._replay_safety_manager,
            cross_schema_guard=self._cross_schema_guard,
            cutover_verifier=self._cutover_verifier,
        )

    @property
    def kernel(self) -> CognitiveKernel:
        """The canonical CognitiveKernel instance."""
        return self._kernel

    @property
    def boot_report(self) -> Any | None:
        """Boot validation report, or None if boot loading was skipped."""
        return self._boot_report

    @property
    def diagnostic_safe(self) -> bool:
        """Whether the runtime is in diagnostic-safe mode."""
        return (
            self._boot_report is not None
            and self._boot_report.status == "diagnostic_safe"
        )

    @property
    def schema_store(self) -> SemanticSchemaStore:
        """The canonical schema store."""
        return self._schema_store

    @property
    def invalidation_engine(self) -> Any:
        return self._invalidation_engine

    @property
    def retraction_engine(self) -> Any:
        return self._retraction_engine

    @property
    def replay_safety_manager(self) -> Any:
        return self._replay_safety_manager

    @property
    def cross_schema_guard(self) -> Any:
        return self._cross_schema_guard

    @property
    def artifact_index(self) -> Any:
        return self._artifact_index

    def run(self, trigger: CycleTrigger) -> Any:
        """Run one cognitive cycle.

        Returns an immutable CognitiveCycle.
        This is the public app entry point.
        """
        return self._kernel.run(trigger)

    def run_text(
        self,
        text: str,
        *,
        context_id: str = "default",
    ) -> Any:
        """Convenience: run a cycle from raw text input."""
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=(text,),
        )
        return self._kernel.run(trigger)


class _NativePerceptAdapter:
    """Wraps a native v3.4 LanguageAdapter for the CognitiveKernel.

    The CognitiveKernel calls perceive(signal_ids) expecting a tuple
    of SurfaceEvidence. This adapter bridges the LanguageAdapter protocol
    (perceive(raw_text, language_tag) -> SurfaceEvidence) to that interface.
    """

    def __init__(self, language_adapter: Any) -> None:
        self._adapter = language_adapter

    def perceive(
        self,
        signal_ids: tuple[str, ...] = (),
        raw_text: str = "",
        signal: Any | None = None,
        kernel: Any | None = None,
    ) -> tuple[Any, ...]:
        """Produce SurfaceEvidence from native language adapter."""
        results = []
        texts = [raw_text] if raw_text else list(signal_ids)
        for text in texts:
            if text:
                evidence = self._adapter.perceive(text, "en")
                results.append(evidence)
        return tuple(results)
