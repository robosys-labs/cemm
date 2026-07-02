from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.trace import Trace
from ..types.signal import Signal, SignalKind, SourceType
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..synthesis.realizer import RealizationPipeline
from ..latent.encoder import LatentEncoder
import time, uuid

_pipeline = RealizationPipeline()
_latent_encoder = LatentEncoder()


class AnswerOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.ANSWER

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        intent = ctx.params.get("intent", "")
        selected_claims = ctx.selected_claim_ids or []
        decision_reason = ctx.params.get("decision_reason", "")
        reason_lower = decision_reason.lower()
        # If decision router detected greeting/acknowledgment, set intent accordingly
        if "greeting" in reason_lower and not selected_claims:
            intent = "greeting"
        elif "acknowledgment" in reason_lower and not selected_claims:
            intent = "acknowledgment"
        elif "unknown term" in reason_lower or "ask meaning" in reason_lower:
            intent = "ask_meaning"
            term = "that"
            if "unknown term" in reason_lower:
                parts = decision_reason.split("'", 2)
                if len(parts) > 2:
                    term = parts[1]
            unknown_term = term
        else:
            unknown_term = ""
        # Propagate confidence from kernel self-view uncertainty to SAG
        seg_confidence = ctx.params.get("seg_confidence", 0.0)
        sag_confidence = max(seg_confidence, 1.0 - ctx.kernel.self_view.uncertainty) if seg_confidence > 0 else max(0.5, 1.0 - ctx.kernel.self_view.uncertainty)
        answer_latent = _latent_encoder.encode_answer(
            intent=intent or ("abstain" if not selected_claims else "answer"),
            selected_claim_ids=selected_claims,
            selected_model_ids=ctx.selected_model_ids or [],
        )
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent=intent or ("abstain" if not selected_claims else "answer"),
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_claim_ids=selected_claims,
            selected_model_ids=ctx.selected_model_ids or [],
            confidence=sag_confidence,
            answer_latent=answer_latent,
        )
        if unknown_term:
            answer_graph.entity_refs.append({
                "kind": "clarification",
                "question": f"What do you mean by '{unknown_term}'?",
                "term": unknown_term,
                "role": "unknown_lexeme",
            })
        simulation_claims = ctx.params.get("simulation_claims")
        if simulation_claims:
            answer_graph.entity_refs.append({
                "kind": "simulation",
                "predictions": simulation_claims,
                "confidence": ctx.params.get("simulation_confidence", 0.5),
            })
        result = _pipeline.run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
        if not result.success:
            abstain_latent = _latent_encoder.encode_answer(
                intent="abstain", selected_claim_ids=[], selected_model_ids=[],
            )
            result = _pipeline.run(
                SemanticAnswerGraph(
                    id=uuid.uuid4().hex[:16],
                    intent="abstain",
                    source_signal_ids=[ctx.input_signal.id],
                    context_id=ctx.kernel.id,
                    confidence=sag_confidence,
                    answer_latent=abstain_latent,
                ),
                ctx.kernel, ctx.store, ctx.registry,
            )
        output = result.output
        # Unified verification is already done inside RealizationPipeline.run()
        # Check the result's verified flag
        if not result.verified:
            verification_meta = result.metadata.get("verification", {})
            issues = verification_meta.get("details", ["unverified output"])
            return OperatorResult(
                success=False,
                output_text="Answer blocked by realization verification: " + "; ".join(issues),
            )
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
            selected_claim_ids=selected_claims,
            selected_model_ids=ctx.selected_model_ids or [],
            action_id="",
            operator_model_id="answer_operator",
            causal_inference_used=bool(ctx.params.get("causal_inference_used")),
            frame_rules_applied=True,
            synthesis_verified=result.verified,
            synthesis_verification_type="hard" if result.strategy in ("template", "extractive") else "soft",
            permission="allowed",
            confidence=max(0.0, min(1.0, sag_confidence)),
            cost_ms=cost_ms,
            fallback_used=False,
            grounded_graph_id=ctx.grounded_graph_id,
            memory_packet_id=ctx.memory_packet_id,
            inference_packet_id=ctx.inference_packet_id,
            semantic_event_graph_id=ctx.semantic_event_graph_id,
            semantic_answer_graph_id=answer_graph.id,
            realization_strategy=result.strategy,
            realization_verified=result.verified,
            realization_details={
                "source_answer_graph_id": result.metadata.get("source_answer_graph_id"),
                "strategy": result.strategy,
            },
            verification_details=result.metadata.get("verification", {}),
        )
        return OperatorResult(
            success=True,
            output_text=result_signal.content,
            trace=trace,
            result_signal=result_signal,
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
