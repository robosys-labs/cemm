"""CEMM v3.4.2 runtime with data-defined foundations and semantic memory."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from uuid import uuid4

from .public_result import project_cycle
from ..kernel.cycle.kernel import CognitiveKernel
from ..kernel.data.loader import (
    DefinitionPackageLoader, default_data_root,
)
from ..kernel.epistemics.evaluator import EpistemicEvaluator
from ..kernel.epistemics.invalidation_engine import (
    CrossSchemaLaunderingGuard,
)
from ..kernel.epistemics.retriever import SemanticRetriever
from ..kernel.epistemics.truth_maintenance import TruthMaintenance
from ..kernel.execution.authorizer import OperationAuthorizer
from ..kernel.execution.commit import CommitCoordinator
from ..kernel.execution.executor import OperationExecutor
from ..kernel.execution.goal_arbiter import GoalArbiter
from ..kernel.execution.planner import Planner
from ..kernel.execution.reconciliation import OutcomeReconciler
from ..kernel.inference.engine import BoundedInferenceEngine
from ..kernel.learning.coordinator import LearningCoordinator
from ..kernel.learning.schema_compiler import LearnedSchemaCompiler
from ..kernel.memory.compiler import FactMutationCompiler
from ..kernel.memory.semantic import (
    FactRole, MutationPayloadRegistry,
    SemanticFact, SemanticMemoryStore,
)
from ..kernel.model.cycle import CycleTrigger
from ..kernel.model.signal import InputSignal
from ..kernel.response.common_ground import CommonGroundManager
from ..kernel.response.planner import ResponsePlanner
from ..kernel.response.renderer import MessageRenderer
from ..kernel.schema.rule import RuleSchema
from ..kernel.schema.store import SemanticSchemaStore
from ..kernel.self_model.capability_evaluator import CapabilityEvaluator
from ..kernel.self_model.self_report import SelfReportBuilder
from ..kernel.understanding.composer import SemanticComposer
from ..kernel.understanding.gap_detector import GapDetector
from ..kernel.understanding.grounding import GroundingResolver
from ..kernel.understanding.interpreter import InterpretationResolver
from ..kernel.understanding.workspace import WorkspaceController
from ..language.en.adapter import EnglishLanguageAdapter
from ..language.fr.adapter import FrenchLanguageAdapter
from ..language.pack import LanguagePackRegistry

class Runtime:
    def __init__(
        self, *, data_root: Path | None = None,
        predicate_schema_store: Any | None = None,
    ):
        if predicate_schema_store is not None:
            raise ValueError(
                "parallel predicate schema stores are forbidden"
            )
        self._data_root = data_root or default_data_root()
        self._schema_store = SemanticSchemaStore()
        self._language_registry = LanguagePackRegistry()
        self._language_registry.load_directory(
            self._data_root / "languages"
        )
        self._definition_loader = DefinitionPackageLoader(
            self._data_root
        )
        self._definition_report = (
            self._definition_loader.validate(
                self._language_registry
            )
        )
        self._definition_report.require_ok()
        self._definition_loader.install(
            self._schema_store,
            self._language_registry,
        )

        self._semantic_memory = SemanticMemoryStore()
        self._payload_registry = MutationPayloadRegistry()
        self._truth = TruthMaintenance()
        self._guard = CrossSchemaLaunderingGuard()
        self._epistemic = EpistemicEvaluator(
            truth_maintenance=self._truth,
            cross_schema_guard=self._guard,
        )
        self._fact_compiler = FactMutationCompiler(
            self._payload_registry
        )
        self._commit = CommitCoordinator(
            self._semantic_memory,
            self._payload_registry,
        )
        self._inference = BoundedInferenceEngine()

        adapters = {
            "en": EnglishLanguageAdapter(
                self._schema_store,
                self._language_registry,
            ),
            "fr": FrenchLanguageAdapter(
                self._schema_store,
                self._language_registry,
            ),
        }
        percept = _NativePerceptAdapter(adapters)
        retriever = SemanticRetriever(
            store=self._semantic_memory,
            schema_store=self._schema_store,
            truth_maintenance=self._truth,
        )
        learning = LearningCoordinator(
            store=self._schema_store,
            evaluator=self._epistemic,
            schema_compiler=LearnedSchemaCompiler(),
        )
        self._kernel = CognitiveKernel(
            schema_store=self._schema_store,
            semantic_memory=self._semantic_memory,
            percept_adapter=percept,
            semantic_composer=SemanticComposer(
                self._schema_store
            ),
            grounding_resolver=GroundingResolver(
                self._schema_store
            ),
            interpretation_resolver=InterpretationResolver(),
            workspace_controller=WorkspaceController(),
            semantic_retriever=retriever,
            epistemic_evaluator=self._epistemic,
            capability_evaluator=CapabilityEvaluator(),
            gap_detector=GapDetector(),
            self_report_builder=SelfReportBuilder(),
            learning_coordinator=learning,
            goal_arbiter=GoalArbiter(),
            planner=Planner(
                schema_store=self._schema_store
            ),
            operation_authorizer=OperationAuthorizer(),
            operation_executor=OperationExecutor(),
            outcome_reconciler=OutcomeReconciler(),
            commit_coordinator=self._commit,
            fact_compiler=self._fact_compiler,
            inference_engine=self._inference,
            response_planner=ResponsePlanner(),
            message_renderer=MessageRenderer.load_default(
                self._data_root
            ),
            common_ground_manager=CommonGroundManager(),
        )
        self._learning_coordinator = learning
        self._seed_live_self_observations()

    @property
    def kernel(self):
        return self._kernel

    @property
    def schema_store(self):
        return self._schema_store

    @property
    def semantic_memory(self):
        return self._semantic_memory

    @property
    def learning_coordinator(self):
        return self._learning_coordinator

    @property
    def language_registry(self):
        return self._language_registry

    @property
    def definition_report(self):
        return self._definition_report

    def run(self, trigger):
        return self._kernel.run(trigger)

    def run_text(
        self, text, *, context_id="default",
        language_hint="en", channel="text",
    ):
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

    def run_text_result(self, text, **kwargs):
        return project_cycle(
            self.run_text(text, **kwargs)
        )

    @staticmethod
    def project(cycle):
        return project_cycle(cycle)

    def _seed_live_self_observations(self):
        self._semantic_memory.add(SemanticFact(
            fact_id="observation:self:name",
            predicate_key="named",
            roles=(
                FactRole("holder", "self"),
                FactRole(
                    "name", "value:text:CEMM",
                    "text", surface="CEMM",
                ),
            ),
            context_ref="actual",
            confidence=1.0,
            evidence_refs=(
                "runtime_observation:self_identity",
            ),
            source_ref="runtime:self_observer",
        ))
        self._semantic_memory.add(SemanticFact(
            fact_id=(
                "observation:self:operational_status"
            ),
            predicate_key="has_state",
            roles=(
                FactRole("holder", "self"),
                FactRole(
                    "dimension",
                    "operational_status",
                    "state_dimension",
                    "operational_status",
                ),
                FactRole(
                    "value", "available",
                    "enum", "availability",
                    "available",
                ),
            ),
            context_ref="actual",
            confidence=1.0,
            evidence_refs=(
                "runtime_observation:process_running",
            ),
            source_ref="runtime:health_observer",
        ))
        self._semantic_memory.add(SemanticFact(
            fact_id=(
                "observation:self:software_system"
            ),
            predicate_key="instance_of",
            roles=(
                FactRole("entity", "self"),
                FactRole(
                    "kind", "software_system",
                    "schema", "software_system",
                ),
            ),
            context_ref="actual",
            confidence=1.0,
            evidence_refs=(
                "runtime_observation:"
                "implementation_identity",
            ),
            source_ref="runtime:self_observer",
        ))

class _NativePerceptAdapter:
    def __init__(self, adapters):
        self._adapters = adapters

    def perceive(
        self, *, input_signals=(),
        signal_ids=(), context_id="default",
        **_,
    ):
        result = []
        for signal in input_signals:
            language = (
                signal.language_hint or "en"
            ).split("-", 1)[0]
            adapter = self._adapters.get(language)
            if adapter is not None:
                result.append(adapter.perceive(
                    signal.content,
                    signal.language_hint,
                ))
        return tuple(result)
