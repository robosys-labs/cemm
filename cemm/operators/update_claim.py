from __future__ import annotations
from types import SimpleNamespace
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.claim import Claim, ClaimStatus
from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.signal import Signal, SignalKind, SourceType
from ..types.trace import Trace
import time, uuid


class UpdateClaimOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.UPDATE_CLAIM

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        claim_id = ctx.params.get("claim_id", "")
        new_status_str = ctx.params.get("status", "superseded")
        new_status = ClaimStatus(new_status_str)
        now = time.time()

        existing = ctx.store.claims.get(claim_id)
        if existing is None:
            return OperatorResult(
                success=False,
                output_text=f"Claim {claim_id} not found",
            )
        existing.status = new_status
        existing.updated_at = now
        # Status updates route through GraphPatch pipeline — no direct store write.

        patch_op = PatchOperation(
            operation="update_claim_status",
            target_id=claim_id,
            fields={"claim_id": claim_id, "status": new_status_str, "updated_at": now},
            confidence=0.9,
            reason=f"status:{claim_id}:{new_status_str}",
        )
        patch = GraphPatch(
            target="episodic_trace",
            operations=[patch_op],
            source_refs=[ctx.input_signal.id],
            evidence_refs=[],
            confidence=0.9,
            reason=f"update_claim:{claim_id}",
        )

        if new_status in (ClaimStatus.DISPUTED, ClaimStatus.RETRACTED):
            self_state = ctx.store.self_store.latest()
            if self_state:
                if claim_id not in self_state.epistemic.open_contradiction_claim_ids:
                    self_state.epistemic.open_contradiction_claim_ids.append(claim_id)
                self_state.updated_at = time.time()
                ctx.store.self_store.put(self_state)

        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.MEMORY_UPDATE,
            source_id="update_claim_operator",
            source_type=SourceType.ASSISTANT,
            content=f"Updated claim {claim_id} to {new_status_str}",
            observed_at=now,
            context_id=ctx.kernel.id,
            salience=0.4,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        answer_graph = SimpleNamespace(
            id=uuid.uuid4().hex[:16],
            intent="update_claim",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_claim_ids=[claim_id],
        )
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_claim_ids=[claim_id],
            action_id="",
            operator_model_id="update_claim_operator",
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
            output_text=f"Claim {claim_id} marked as {new_status_str}",
            trace=trace,
            result_signal=result_signal,
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
            graph_patches=[patch],
        )
