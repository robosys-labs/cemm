from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..retrieval.structural import StructuralRetriever, RetrievalQuery
from ..retrieval.ranker import Ranker
from ..synthesis.realizer import RealizationPipeline
import time, uuid


class RetrieveOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.RETRIEVE

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        if not ctx.kernel.permission.may_retrieve:
            return OperatorResult(success=False, output_text="Permission denied: retrieval not allowed")
        query = RetrievalQuery(
            subject_entity_id=ctx.params.get("subject_entity_id"),
            predicate=ctx.params.get("predicate"),
            object_entity_id=ctx.params.get("object_entity_id"),
            domain=ctx.params.get("domain"),
            source_id=ctx.params.get("source_id"),
            limit=ctx.params.get("limit", 64),
        )
        retriever = StructuralRetriever(ctx.store)
        result = retriever.retrieve(query, ctx.kernel)
        ranker = Ranker()
        ranked = ranker.rank_claims(result.claims, ctx.kernel)
        selected_ids = [c.id for c, _ in ranked[:10]]
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="answer" if selected_ids else "retrieve",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_claim_ids=selected_ids[:5],
            confidence=0.7 if selected_ids else 0.3,
        )
        realization = RealizationPipeline().run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
        output = realization.output if realization.success and realization.verified else "I did not find matching stored evidence."
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_claim_ids=selected_ids,
            action_id="",
            operator_model_id="retrieve_operator",
            synthesis_verified=realization.verified,
            synthesis_verification_type="hard",
            permission="allowed",
            confidence=0.7,
            cost_ms=cost_ms,
            grounded_graph_id=ctx.grounded_graph_id,
            memory_packet_id=ctx.memory_packet_id,
            inference_packet_id=ctx.inference_packet_id,
            semantic_event_graph_id=ctx.semantic_event_graph_id,
            semantic_answer_graph_id=answer_graph.id,
            realization_strategy=realization.strategy,
            realization_verified=realization.verified,
            realization_details={
                "source_answer_graph_id": realization.metadata.get("source_answer_graph_id"),
                "strategy": realization.strategy,
            },
            verification_details=realization.metadata.get("verification", {}),
        )
        return OperatorResult(
            success=True,
            output_text=output,
            trace=trace,
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
