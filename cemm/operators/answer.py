from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.trace import Trace
from ..types.signal import Signal, SignalKind, SourceType
from ..synthesis.verifier import SynthesisVerifier
import time, uuid

_verifier = SynthesisVerifier()


class AnswerOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.ANSWER

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        output = ctx.params.get("answer_text", "")
        if not output and ctx.selected_claim_ids:
            claims = [ctx.store.claims.get(cid) for cid in ctx.selected_claim_ids]
            valid_claims = [c for c in claims if c]
            verified, issues = _verifier.verify(
                output or "synthesized",
                ctx.selected_claim_ids,
                ctx.selected_model_ids,
                ctx.kernel,
                valid_claims,
            )
            if not verified:
                return OperatorResult(
                    success=False,
                    output_text="Answer blocked by synthesis verification: " + "; ".join(issues),
                )
            parts = [
                f"{c.subject_entity_id} {c.predicate} {c.object_value or c.object_entity_id or ''}"
                for c in valid_claims
            ]
            output = "; ".join(parts) if parts else ""
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.TRACE,
            source_id="answer_operator",
            source_type=SourceType.ASSISTANT,
            content=output or "I don't have enough information to answer.",
            observed_at=time.time(),
            context_id=ctx.kernel.id,
            salience=0.5,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_claim_ids=ctx.selected_claim_ids,
            selected_model_ids=ctx.selected_model_ids,
            action_id="",
            operator_model_id="answer_operator",
            causal_inference_used=bool(ctx.params.get("causal_inference_used")),
            frame_rules_applied=True,
            synthesis_verified=True,
            synthesis_verification_type="hard",
            permission="allowed",
            confidence=ctx.kernel.self_view.confidence if hasattr(ctx.kernel.self_view, 'confidence') else 0.9,
            cost_ms=cost_ms,
            fallback_used=False,
        )
        return OperatorResult(
            success=True,
            output_text=result_signal.content,
            trace=trace,
            result_signal=result_signal,
            cost_ms=cost_ms,
        )
