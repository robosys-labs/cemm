from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.claim import Claim, ClaimStatus
from ..types.signal import Signal, SignalKind, SourceType
from ..types.entity import Entity, EntityType
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
import time, uuid


class RememberOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.REMEMBER

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        if not ctx.kernel.permission.may_store:
            return OperatorResult(success=False, output_text="Permission denied: storage not allowed")
        now = time.time()
        subject_id = ctx.params.get("subject_entity_id", "")
        predicate = ctx.params.get("predicate", "")
        object_value = ctx.params.get("object_value")
        object_entity_id = ctx.params.get("object_entity_id")
        domain = ctx.params.get("domain", "general")
        qualifiers = ctx.params.get("qualifiers", {})

        claim = Claim(
            id=uuid.uuid4().hex[:16],
            subject_entity_id=subject_id,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=object_entity_id,
            qualifiers=qualifiers,
            evidence_signal_ids=[ctx.input_signal.id],
            source_id=ctx.input_signal.source_id,
            domain=domain,
            confidence=0.7,
            trust=0.7,
            salience=0.5,
            status=ClaimStatus.ACTIVE,
            observed_at=now,
            updated_at=now,
            permission=ctx.kernel.permission,
        )
        entity = ctx.store.entities.get(subject_id)
        if entity is None:
            entity = Entity(
                id=subject_id,
                type=EntityType.PERSON,
                name=subject_id,
                aliases=[],
                confidence=0.7,
                created_from_signal_id=ctx.input_signal.id,
                created_at=now,
                updated_at=now,
            )
            ctx.store.entities.put(entity)
        ctx.store.claims.put(claim)

        self_state = ctx.store.self_store.latest()
        if self_state:
            self_state.meta_memory.recently_written_claim_ids.append(claim.id)
            if len(self_state.meta_memory.recently_written_claim_ids) > 100:
                self_state.meta_memory.recently_written_claim_ids = self_state.meta_memory.recently_written_claim_ids[-100:]
            self_state.updated_at = time.time()
            ctx.store.self_store.put(self_state)

        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.MEMORY_UPDATE,
            source_id="remember_operator",
            source_type=SourceType.ASSISTANT,
            content=f"Stored claim: {subject_id} {predicate}",
            observed_at=now,
            context_id=ctx.kernel.id,
            salience=0.5,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="remember",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_claim_ids=[claim.id],
        )
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_claim_ids=[claim.id],
            action_id="",
            operator_model_id="remember_operator",
            permission="allowed",
            confidence=0.7,
            cost_ms=cost_ms,
            grounded_graph_id=ctx.grounded_graph_id,
            memory_packet_id=ctx.memory_packet_id,
            inference_packet_id=ctx.inference_packet_id,
            semantic_event_graph_id=ctx.semantic_event_graph_id,
            semantic_answer_graph_id=answer_graph.id,
        )
        return OperatorResult(
            success=True,
            output_text=f"Remembered: {subject_id} {predicate}",
            trace=trace,
            result_signal=result_signal,
            new_claim_ids=[claim.id],
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
