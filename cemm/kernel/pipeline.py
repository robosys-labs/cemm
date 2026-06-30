from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from ..types.signal import Signal, SignalKind, SourceType
from ..types.action import Action, ActionKind, ActionStatus
from ..types.trace import Trace
from ..types.context_kernel import ContextKernel
from ..types.semantic_event_graph import SemanticEventGraph
from ..types.packets import GroundedGraph, MemoryPacket, RankingTraceEntry
from ..types.self_view import SelfView
from ..types.permission import Permission
from ..store.store import Store
from ..store.artifact_store import ArtifactStore
from ..registry import Registry
from ..confidence.scoring import score_action
from .context_kernel_builder import ContextKernelBuilder
from .normalizer import Normalizer
from .entity_resolver import EntityResolver
from .frame_engine import FrameEngine
from .pragmatic_interpreter import interpret_signal, update_user_affect, update_conversation_dynamics
from ..registry.uol_mapper import UOLMapper
from .context_inference import ContextInferenceEngine
from .semantic_interpreter import SemanticInterpreter
from .grounding import GroundingPipeline
from ..retrieval.structural import StructuralRetriever
from ..retrieval.ranker import Ranker


@dataclass
class PipelineResult:
    output_text: str = ""
    actions: list[Action] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    kernel: ContextKernel | None = None
    confidence: float = 0.0
    cost_ms: float = 0.0
    abstained: bool = False
    ranked_claim_ids: list[str] = field(default_factory=list)
    ranked_model_ids: list[str] = field(default_factory=list)
    semantic_event_graph: SemanticEventGraph | None = None
    grounded_graph: GroundedGraph | None = None
    memory_packet: MemoryPacket | None = None


class Pipeline:
    def __init__(
        self,
        store: Store,
        registry: Registry,
    ) -> None:
        self._store = store
        self._registry = registry
        self._builder = ContextKernelBuilder()
        self._normalizer = Normalizer(registry)
        self._resolver = EntityResolver(store.entities)
        self._frames = FrameEngine(store.claims)
        self._uol_mapper = UOLMapper(registry)
        self._artifact_store = ArtifactStore(store)
        self._semantic_interpreter = SemanticInterpreter(
            self._uol_mapper, artifact_store=self._artifact_store,
        )
        self._grounding_pipeline = GroundingPipeline(self._resolver, self._frames)
        self._context_inference_engine = ContextInferenceEngine(store, registry)
        self._retriever = StructuralRetriever(store)
        self._ranker = Ranker()
        self._turn_count: int = 0

    def run(
        self,
        input_text: str,
        context_id: str | None = None,
        budget_override: dict | None = None,
        source_id: str = "user",
    ) -> PipelineResult:
        start = time.time()
        signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.INPUT,
            source_id=source_id,
            source_type=SourceType.USER,
            content=input_text,
            observed_at=start,
            context_id=context_id or uuid.uuid4().hex[:16],
            salience=0.8,
            trust=0.8,
            permission=Permission.public(),
        )
        self._store.signals.put(signal)

        self._turn_count += 1
        kernel = self._builder.from_signal(signal, turn_index=self._turn_count)

        # Normalize (local var only, keep raw signal content stable)
        normalized_content = self._normalizer.normalize_predicate(signal.content)

        if budget_override:
            for k, v in budget_override.items():
                if hasattr(kernel.budget, k):
                    setattr(kernel.budget, k, v)

        self_state = self._store.self_store.latest()
        if self_state:
            kernel.self_view = SelfView.from_self_state(self_state, kernel.memory.working_claim_ids)
        else:
            kernel.self_view = SelfView()

        # Interpret: SemanticEventGraph + UOL atoms
        semantic_event_graph = self._semantic_interpreter.run(signal, kernel)
        semantics = interpret_signal(signal, kernel, self._store)
        if semantics is not None:
            uol_atoms = self._uol_mapper.map_signal(signal.content, kernel)
            semantics.uol_atoms = uol_atoms
            quality_keys, process_keys = self._uol_mapper.compile_to_pragmatic_keys(uol_atoms)
            kernel.user.affect.active_quality_atom_keys = quality_keys
            if kernel.conversation.dynamics:
                kernel.conversation.dynamics.active_process_atom_keys = process_keys
            signal.observation_semantics = semantics
            if semantics.semantic_cluster_key:
                kernel.user.affect = update_user_affect(kernel.user.affect, semantics, kernel, signal.id)
                kernel.conversation.dynamics = update_conversation_dynamics(
                    kernel.conversation.dynamics, semantics, kernel, signal.id
                )

        # Infer context from signal + graph + kernel (not raw text alone)
        context_inference = self._context_inference_engine.infer(signal, kernel)
        self._context_inference_engine.apply_to_kernel(context_inference, kernel)

        # Ground entities, time, frame, permission
        grounded_graph = self._grounding_pipeline.run(semantic_event_graph, kernel)

        # Seed entity IDs from graph for graph-grounded retrieval
        for ref in semantic_event_graph.entity_refs:
            eid = ref.get("entity_id", "")
            if eid and eid not in kernel.memory.working_entity_ids:
                kernel.memory.working_entity_ids.append(eid)

        # Retrieve claims and models
        retrieval_result = self._retriever.retrieve_for_kernel(kernel)

        # Graph-grounded retrieval enrichment
        graph_result = self._retriever.retrieve_for_graph(semantic_event_graph, kernel)

        # Merge: deduplicate by claim ID, prefer graph results
        seen_ids = {c.id for c in retrieval_result.claims}
        for c in graph_result.claims:
            if c.id not in seen_ids:
                retrieval_result.claims.append(c)
                seen_ids.add(c.id)

        # Rank claims and models with graph context
        ranked_claims = self._ranker.rank_claims(retrieval_result.claims, kernel, graph=semantic_event_graph)
        ranked_models = self._ranker.rank_models(retrieval_result.models, kernel)
        kernel.memory.working_claim_ids = [c.id for c, _ in ranked_claims[:kernel.budget.max_ranked]]
        kernel.world.active_claim_ids = kernel.memory.working_claim_ids
        kernel.memory.candidate_model_ids = [m.id for m, _ in ranked_models[:kernel.budget.max_ranked]]

        memory_packet = MemoryPacket(
            selected_signal_ids=[signal.id],
            selected_claim_ids=list(kernel.memory.working_claim_ids),
            selected_model_ids=list(kernel.memory.candidate_model_ids),
            ranking_trace=[
                RankingTraceEntry(
                    candidate_id=c.id,
                    score=s,
                    reason=f"ranked {s:.3f}",
                )
                for c, s in (ranked_claims if isinstance(ranked_claims, list) else [])
            ] if ranked_claims else [],
            confidence=sum(s for _, s in ranked_claims[:5]) / max(len(ranked_claims[:5]), 1) if ranked_claims else 0.5,
        )

        self._check_budget(kernel, start)

        result = PipelineResult(
            kernel=kernel,
            ranked_claim_ids=kernel.memory.working_claim_ids,
            ranked_model_ids=[m.id for m in retrieval_result.models],
            semantic_event_graph=semantic_event_graph,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
        )
        result.signals.append(signal)
        result.cost_ms = (time.time() - start) * 1000.0
        return result

    def _check_budget(self, kernel: ContextKernel, start: float) -> None:
        elapsed = (time.time() - start) * 1000.0
        if elapsed > kernel.budget.latency_target_ms:
            working_ids = kernel.memory.working_signal_ids
            if len(working_ids) > kernel.budget.max_entities:
                kernel.memory.working_signal_ids = working_ids[-kernel.budget.max_entities:]
            if len(kernel.world.active_claim_ids) > kernel.budget.max_claims:
                kernel.world.active_claim_ids = kernel.world.active_claim_ids[-kernel.budget.max_claims:]
