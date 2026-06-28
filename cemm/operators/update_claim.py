from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.claim import Claim, ClaimStatus
from ..types.signal import Signal, SignalKind, SourceType
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
        ctx.store.claims.put(existing)

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
        return OperatorResult(
            success=True,
            output_text=f"Claim {claim_id} marked as {new_status_str}",
            result_signal=result_signal,
        )
