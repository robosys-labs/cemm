"""Canonical CEMM v3.4.1 application runtime.

Public text entrypoints use this runtime exclusively.  Legacy v3.3 may be
imported only by explicit migration tooling, never by this assembly.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from .public_result import PublicCycleResult, project_cycle
from ..kernel.boot.v341 import register_v341_foundations
from ..kernel.boot.v341_validation import (
    validate_registered_v341, validate_v341_spec,
)
from ..kernel.cycle.kernel import CognitiveKernel
from ..kernel.model.cycle import CycleTrigger
from ..kernel.model.signal import InputSignal
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
from ..kernel.response.renderer import MessageRenderer
from ..kernel.response.common_ground import CommonGroundManager
from ..kernel.retirement.cutover import AuthoritativeCutoverVerifier


class Runtime:
    """Construct the single authoritative native runtime."""

    def __init__(
        self,
        *,
        predicate_schema_store: Any | None = None,
        load_boot: bool = True,
    ) -> None:
        if predicate_schema_store is not None:
            raise ValueError(
                "parallel predicate schema stores are forbidden; use SemanticSchemaStore"
            )

        self._schema_store = SemanticSchemaStore()
        self._boot_report: Any | None = None
        self._boot_unresolved_deps: tuple[str, ...] = ()
        if load_boot:
            from ..kernel.boot.validation import BootValidator, BootStatus
            from ..kernel.boot.manifest import build_boot_manifest

            validator = BootValidator()
            manifest = build_boot_manifest()
            self._boot_report = validator.validate_boot(self._schema_store, manifest)
            status = getattr(self._boot_report.status, "value", self._boot_report.status)
            if status == getattr(BootStatus.HALTED, "value", "halted"):
                raise RuntimeError(
                    f"Boot validation halted: {self._boot_report.halted_reasons}"
                )
            validator.register_boot_schemas(
                self._schema_store, manifest, self._boot_report
            )
            unresolved, _ = validator.verify_dependencies(
                self._schema_store, manifest
            )
            self._boot_unresolved_deps = unresolved
            validate_v341_spec().require_ok()
            register_v341_foundations(self._schema_store)
            validate_registered_v341(self._schema_store).require_ok()

        from ..language.en.adapter import EnglishLanguageAdapter
        self._percept_adapter = _NativePerceptAdapter(
            EnglishLanguageAdapter(self._schema_store)
        )
        self._semantic_composer = SemanticComposer(self._schema_store)
        self._grounding_resolver = GroundingResolver(self._schema_store)
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
        self._operation_authorizer = OperationAuthorizer()
        self._operation_executor = OperationExecutor()
        self._outcome_reconciler = OutcomeReconciler()
        self._commit_coordinator = CommitCoordinator()
        self._response_planner = ResponsePlanner()
        self._message_renderer = MessageRenderer(self._schema_store)
        self._common_ground_manager = CommonGroundManager()

        from ..kernel.epistemics.artifact_index import DerivedArtifactIndex
        from ..kernel.epistemics.invalidation_engine import InvalidationEngine
        from ..kernel.epistemics.invalidation_events import InvalidationEventBus
        from ..kernel.epistemics.replay_safety import ReplaySafetyManager
        from ..kernel.correction.retraction_engine import RetractionEngine
        from ..kernel.learning.replay_queue import ReplayQueue

        self._artifact_index = DerivedArtifactIndex()
        self._invalidation_event_bus = InvalidationEventBus()
        self._invalidation_engine = InvalidationEngine(
            index=self._artifact_index,
            truth_maintenance=self._truth_maintenance,
            event_bus=self._invalidation_event_bus,
        )
        self._retraction_engine = RetractionEngine()
        self._replay_queue = ReplayQueue()
        self._replay_safety_manager = ReplaySafetyManager(self._replay_queue)

        self._cutover_verifier = AuthoritativeCutoverVerifier()
        authorities = {
            "surface_analysis": "PerceptAdapter",
            "semantic_composition": "SemanticComposer",
            "referent_sense_role_grounding": "GroundingResolver",
            "schema_identity_version_resolution": "SemanticSchemaStore",
            "structural_grounding_assessment": "GroundingResolver",
            "competence_execution": "CapabilityEvaluator",
            "schema_lifecycle_activation": "SemanticSchemaStore",
            "recursive_cluster_classification": "SemanticSchemaStore",
            "interpretation_selection": "InterpretationResolver",
            "context_isolation": "EpistemicEvaluator",
            "semantic_retrieval": "SemanticRetriever",
            "truth_and_context_admissibility": "EpistemicEvaluator",
            "current_schema_use": "GroundingResolver",
            "derived_cognition_retraction": "InvalidationEngine",
            "current_capability": "CapabilityEvaluator",
            "gap_creation": "GapDetector",
            "learning_lifecycle": "LearningCoordinator",
            "replay_scheduling_idempotence": "ReplaySafetyManager",
            "active_goals": "GoalArbiter",
            "plan_selection": "Planner",
            "operation_authorization": "OperationAuthorizer",
            "execution": "OperationExecutor",
            "outcome_reconciliation": "OutcomeReconciler",
            "persistent_mutation": "CommitCoordinator",
            "common_ground": "CommonGroundManager",
            "response_content": "ResponsePlanner",
            "surface_realization": "MessageRenderer",
            "cycle_scheduling": "CognitiveKernel",
        }
        for key, owner in authorities.items():
            self._cutover_verifier.register(key, owner)

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
        return self._kernel

    @property
    def schema_store(self) -> SemanticSchemaStore:
        return self._schema_store

    @property
    def boot_report(self) -> Any | None:
        return self._boot_report

    @property
    def diagnostic_safe(self) -> bool:
        if self._boot_report is None:
            return False
        return getattr(self._boot_report.status, "value", self._boot_report.status) == "diagnostic_safe"

    @property
    def learning_coordinator(self) -> LearningCoordinator:
        return self._learning_coordinator

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
        return self._kernel.run(trigger)

    def run_text(
        self,
        text: str,
        *,
        context_id: str = "default",
        language_hint: str = "en",
        channel: str = "text",
    ) -> Any:
        signal = InputSignal(
            id=f"signal:{uuid4().hex[:12]}",
            content=text,
            context_id=context_id,
            source_ref="user",
            language_hint=language_hint,
            channel=channel,
        )
        return self._kernel.run(CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=(signal.id,),
            input_signals=(signal,),
            context_id=context_id,
        ))

    def run_text_result(
        self,
        text: str,
        *,
        context_id: str = "default",
        language_hint: str = "en",
        channel: str = "text",
    ) -> PublicCycleResult:
        return project_cycle(self.run_text(
            text,
            context_id=context_id,
            language_hint=language_hint,
            channel=channel,
        ))

    @staticmethod
    def project(cycle: Any) -> PublicCycleResult:
        return project_cycle(cycle)


class _NativePerceptAdapter:
    def __init__(self, language_adapter: Any) -> None:
        self._adapter = language_adapter

    def perceive(
        self,
        *,
        input_signals: tuple[InputSignal, ...] = (),
        signal_ids: tuple[str, ...] = (),
        context_id: str = "default",
        **_: Any,
    ) -> tuple[Any, ...]:
        # signal_ids are identity only. Legacy callers that supply raw text via
        # signal_ids receive no surface evidence rather than a silent contract
        # violation.
        results = []
        for signal in input_signals:
            if not signal.content:
                continue
            language = signal.language_hint or "en"
            results.append(self._adapter.perceive(signal.content, language))
        return tuple(results)
