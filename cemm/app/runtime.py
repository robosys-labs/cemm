"""CEMM canonical v3.4.3 runtime.

The runtime has one semantic language-pack authority for understanding and
realization.  DECIDE emits explicit response intents; the renderer only emits
proof-carrying clauses licensed by the same audited package.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .public_result import project_cycle
from ..kernel.boot.v343_runtime import (
    collect_runtime_emission_evidence,
    load_runtime_policies,
    load_v343_runtime_package,
)
from ..kernel.cycle.canonical_kernel import CanonicalCognitiveKernel
from ..kernel.data.loader import DefinitionPackageLoader, default_data_root
from ..kernel.epistemics.canonical_retriever import CanonicalSemanticRetriever
from ..kernel.epistemics.evaluator import EpistemicEvaluator
from ..kernel.epistemics.invalidation_engine import CrossSchemaLaunderingGuard
from ..kernel.epistemics.truth_maintenance import TruthMaintenance
from ..kernel.execution.authorizer import OperationAuthorizer
from ..kernel.execution.commit import CommitCoordinator
from ..kernel.execution.executor import OperationExecutor
from ..kernel.execution.goal_arbiter import GoalArbiter
from ..kernel.execution.planner import Planner
from ..kernel.execution.reconciliation import OutcomeReconciler
from ..kernel.inference.catalog import SemanticRuleCatalog
from ..kernel.inference.committer import InferenceFactCommitter
from ..kernel.inference.agenda_engine import AgendaInferenceEngine
from ..kernel.inference.engine import BoundedInferenceEngine
from ..kernel.learning.coordinator import LearningCoordinator
from ..kernel.learning.anchored_schema_compiler import AnchoredLearnedSchemaCompiler
from ..kernel.learning.grounded_definition_learner import GroundedDefinitionLearner
from ..kernel.learning.grounded_rule_learner import GroundedRuleLearner
from ..kernel.learning.schema_compiler import LearnedSchemaCompiler
from ..kernel.memory.compiler import FactMutationCompiler
from ..kernel.memory.semantic import (
    FactRole,
    MutationPayloadRegistry,
    SemanticFact,
    SemanticMemoryStore,
)
from ..kernel.model.cycle import CycleTrigger
from ..kernel.model.signal import InputSignal
from ..kernel.response.common_ground import CommonGroundManager
from ..kernel.response.cycle_environment import (
    CanonicalCycleEmissionEnvironmentBuilder,
)
from ..kernel.response.decider import ResponseDecider
from ..kernel.response.ranker import ResponseCandidateRanker
from ..kernel.response.emission_closure import SemanticEmissionGate
from ..kernel.response.planner import ResponsePlanner
from ..kernel.response.renderer import MessageRenderer
from ..kernel.schema.store import SemanticSchemaStore
from ..kernel.self_model.capability_evaluator import CapabilityEvaluator
from ..kernel.self_model.runtime_capabilities import RuntimeCapabilityProvider
from ..kernel.self_model.self_report import SelfReportBuilder
from ..kernel.understanding.context_snapshot import DialogueSemanticLedger
from ..kernel.understanding.contextual_grounding import ContextualGroundingResolver
from ..kernel.understanding.contextual_interpreter import ContextualInterpretationResolver
from ..kernel.understanding.forest_composer import SemanticForestComposer
from ..kernel.understanding.canonical_grounding import CanonicalGroundingResolver
from ..kernel.understanding.canonical_interpreter import (
    CanonicalInterpretationResolver,
)
from ..kernel.understanding.canonical_gap_detector import CanonicalGapDetector
from ..kernel.understanding.workspace import WorkspaceController
from ..language.semantic_adapter import SemanticLanguageAdapter


class Runtime:
    def __init__(
        self,
        *,
        data_root: Path | None = None,
        predicate_schema_store: Any | None = None,
    ):
        if predicate_schema_store is not None:
            raise ValueError("parallel predicate schema stores are forbidden")

        self._data_root = data_root or default_data_root()
        self._schema_store = SemanticSchemaStore()
        self._definition_loader = DefinitionPackageLoader(self._data_root)
        empty_registry = _EmptyLanguageRegistry()
        self._definition_report = self._definition_loader.validate(empty_registry)
        self._definition_report.require_ok()
        self._definition_loader.install(self._schema_store, empty_registry)

        self._boot_package = load_v343_runtime_package(self._data_root)
        self._language_registry = _SemanticLanguageRegistry(
            self._boot_package.language_packs
        )
        emission_evidence = collect_runtime_emission_evidence(
            self._data_root,
            self._boot_package,
        )
        runtime_policies = load_runtime_policies(self._data_root)

        self._semantic_memory = SemanticMemoryStore()
        self._payload_registry = MutationPayloadRegistry()
        self._truth = TruthMaintenance()
        self._guard = CrossSchemaLaunderingGuard()
        self._epistemic = EpistemicEvaluator(
            truth_maintenance=self._truth,
            cross_schema_guard=self._guard,
        )
        self._fact_compiler = FactMutationCompiler(
            self._payload_registry, self._semantic_memory
        )
        self._commit = CommitCoordinator(
            self._semantic_memory,
            self._payload_registry,
        )
        self._inference = AgendaInferenceEngine()
        rule_catalog = SemanticRuleCatalog(self._schema_store)
        inference_committer = InferenceFactCommitter(
            self._payload_registry,
            self._commit,
        )

        adapters = {
            tag: SemanticLanguageAdapter(
                pack,
                passed_competence_case_refs=(
                    emission_evidence.competence_case_refs
                ),
                schema_store=self._schema_store,
            )
            for tag, pack in self._boot_package.language_packs.items()
        }
        percept = _NativePerceptAdapter(adapters)
        dialogue_ledger = DialogueSemanticLedger()
        composer = SemanticForestComposer(self._schema_store)
        grounding = ContextualGroundingResolver(self._schema_store)
        interpreter = ContextualInterpretationResolver()
        workspace = WorkspaceController()
        retriever = CanonicalSemanticRetriever(
            store=self._semantic_memory,
            schema_store=self._schema_store,
            truth_maintenance=self._truth,
        )
        learning = LearningCoordinator(
            store=self._schema_store,
            evaluator=self._epistemic,
            schema_compiler=AnchoredLearnedSchemaCompiler(
                self._schema_store
            ),
        )
        rule_learner = GroundedRuleLearner(
            self._schema_store, self._semantic_memory
        )
        definition_learner = GroundedDefinitionLearner(
            self._schema_store, self._semantic_memory
        )
        response_planner = ResponsePlanner()
        response_decider = ResponseDecider(
            tuple(runtime_policies.get("dialogue_policies", ())),
            ranker=ResponseCandidateRanker(),
            semantic_memory=self._semantic_memory,
        )
        renderer = MessageRenderer(
            emission_gate=SemanticEmissionGate(
                self._boot_package.foundations,
                self._boot_package.self_claim_authorizer,
            ),
            language_packs={
                tag: pack.realization
                for tag, pack in self._boot_package.language_packs.items()
            },
        )
        common_ground = CommonGroundManager()
        capability_evaluator = CapabilityEvaluator()
        capability_provider = RuntimeCapabilityProvider(
            evaluator=capability_evaluator,
            schema_store=self._schema_store,
            operation_specs=tuple(self._definition_loader.operations),
            components={
                "op:perceive": percept.perceive,
                "op:interpret": interpreter.resolve,
                "op:ground": grounding.ground_graph,
                "op:retrieve": retriever.retrieve,
                "op:infer": self._inference.infer,
                "op:learn": learning.open_transaction,
                "op:store_fact": self._commit.commit,
                "op:answer": response_decider.decide,
                "op:realize": renderer.render,
                # Dispatch is intentionally omitted: recording common ground is
                # not equivalent to proving that a transport is available.
            },
        )

        self._kernel = CanonicalCognitiveKernel(
            schema_store=self._schema_store,
            semantic_memory=self._semantic_memory,
            percept_adapter=percept,
            semantic_composer=composer,
            grounding_resolver=grounding,
            interpretation_resolver=interpreter,
            workspace_controller=workspace,
            semantic_retriever=retriever,
            epistemic_evaluator=self._epistemic,
            capability_evaluator=capability_evaluator,
            gap_detector=CanonicalGapDetector(),
            self_report_builder=SelfReportBuilder(),
            learning_coordinator=learning,
            goal_arbiter=GoalArbiter(),
            planner=Planner(schema_store=self._schema_store),
            operation_authorizer=OperationAuthorizer(),
            operation_executor=OperationExecutor(),
            outcome_reconciler=OutcomeReconciler(),
            commit_coordinator=self._commit,
            fact_compiler=self._fact_compiler,
            inference_engine=self._inference,
            response_planner=response_planner,
            message_renderer=renderer,
            common_ground_manager=common_ground,
            response_decider=response_decider,
            emission_environment_builder=(
                CanonicalCycleEmissionEnvironmentBuilder()
            ),
            capability_provider=capability_provider,
            rule_catalog=rule_catalog,
            inference_committer=inference_committer,
            rule_learner=rule_learner,
            definition_learner=definition_learner,
            dialogue_ledger=dialogue_ledger,
            foundation_fingerprint=self._boot_package.fingerprint,
            active_schema_refs=emission_evidence.active_schema_refs,
            passed_competence_case_refs=(
                emission_evidence.competence_case_refs
            ),
            passed_round_trip_case_refs=(
                emission_evidence.round_trip_case_refs
            ),
            non_persistent_predicates=frozenset(
                runtime_policies.get("non_persistent_predicates", ())
            ),
        )
        self._learning_coordinator = learning
        self._seed_live_self_observations()
        self._seed_foundational_relations()
        self._close_seed_knowledge(rule_catalog, inference_committer)

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
        self,
        text,
        *,
        context_id="default",
        language_hint="en",
        channel="text",
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
        return project_cycle(self.run_text(text, **kwargs))

    @staticmethod
    def project(cycle):
        return project_cycle(cycle)

    def _seed_foundational_relations(self):
        self._semantic_memory.add(SemanticFact(
            fact_id="observation:user:agent",
            predicate_key="instance_of",
            roles=(
                FactRole("entity", "user"),
                FactRole("kind", "agent", "referent", "agent"),
            ),
            context_ref="actual",
            confidence=1.0,
            evidence_refs=("runtime_observation:dialogue_participant",),
            source_ref="runtime:participant_observer",
        ))
        for item in self._definition_loader.entity_kinds:
            child = str(item.get("semantic_key", ""))
            for parent in item.get("parent_kind_refs", ()):
                self._semantic_memory.add(SemanticFact(
                    fact_id=f"foundation:subkind:{child}:{parent}",
                    predicate_key="subkind_of",
                    roles=(
                        FactRole("child_kind", child, "referent", child),
                        FactRole("parent_kind", str(parent), "referent", str(parent)),
                    ),
                    context_ref="actual",
                    confidence=1.0,
                    evidence_refs=("foundation:entity_kind_hierarchy",),
                    source_ref="foundation:definitions",
                ))

    def _close_seed_knowledge(self, rule_catalog, inference_committer):
        rules = rule_catalog.active_rules()
        if not rules:
            return
        from ..kernel.inference.rule_model import InferenceBudget
        outcome = self._inference.infer(
            seed_facts=self._semantic_memory.all_facts(),
            rules=rules,
            budget=InferenceBudget(wall_clock_ms=50, allow_sensitive=False),
            dependency_fingerprint=self._boot_package.fingerprint,
        )
        inference_committer.commit(outcome, context_id="boot")

    def _seed_live_self_observations(self):
        self._semantic_memory.add(SemanticFact(
            fact_id="observation:self:name",
            predicate_key="named",
            roles=(
                FactRole("holder", "self"),
                FactRole(
                    "name",
                    "value:text:CEMM",
                    "value",
                    surface="CEMM",
                ),
            ),
            context_ref="actual",
            confidence=1.0,
            evidence_refs=("runtime_observation:self_identity",),
            source_ref="runtime:self_observer",
        ))
        self._semantic_memory.add(SemanticFact(
            fact_id="observation:self:operational_status",
            predicate_key="has_state",
            roles=(
                FactRole("holder", "self"),
                FactRole(
                    "dimension",
                    "operational_status",
                    "referent",
                    "operational_status",
                    "operational status",
                ),
                FactRole(
                    "value",
                    "available",
                    "value",
                    "state:available",
                    "available",
                ),
            ),
            context_ref="actual",
            confidence=1.0,
            evidence_refs=("runtime_observation:process_running",),
            source_ref="runtime:health_observer",
        ))
        self._semantic_memory.add(SemanticFact(
            fact_id="observation:self:software_system",
            predicate_key="instance_of",
            roles=(
                FactRole("entity", "self"),
                FactRole(
                    "kind",
                    "software_system",
                    "referent",
                    "software_system",
                ),
            ),
            context_ref="actual",
            confidence=1.0,
            evidence_refs=(
                "runtime_observation:implementation_identity",
            ),
            source_ref="runtime:self_observer",
        ))


class _NativePerceptAdapter:
    def __init__(self, adapters):
        self._adapters = adapters

    def perceive(
        self,
        *,
        input_signals=(),
        signal_ids=(),
        context_id="default",
        **_,
    ):
        result = []
        for signal in input_signals:
            language = (signal.language_hint or "en").split("-", 1)[0]
            adapter = self._adapters.get(language)
            if adapter is not None:
                result.append(adapter.perceive(
                    signal.content,
                    signal.language_hint,
                ))
        return tuple(result)


class _EmptyLanguageRegistry:
    language_tags: tuple[str, ...] = ()

    @staticmethod
    def require(tag: str):
        raise KeyError(tag)


class _SemanticLanguageRegistry:
    def __init__(self, packs):
        self._packs = dict(packs)
        self.language_tags = tuple(sorted(self._packs))

    def require(self, tag: str):
        return self._packs[tag]
