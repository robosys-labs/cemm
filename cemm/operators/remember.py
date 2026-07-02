from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..types.claim import Claim, ClaimStatus
from ..types.signal import Signal, SignalKind, SourceType
from ..types.entity import Entity, EntityType
from ..types.trace import Trace
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..synthesis.realizer import RealizationPipeline
from ..synthesis.template import TemplateStrategy
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
        if (not subject_id or not predicate or not object_value) and ctx.params.get("text"):
            words = str(ctx.params["text"]).strip().split()
            if len(words) >= 3:
                subject_id = subject_id or words[0].lower()
                predicate = predicate or words[1].lower()
                object_value = object_value or " ".join(words[2:])

        # Memory write gates: do not store questions, raw commands, or empty facts.
        # Command words are resolved via registry, not hardcoded.
        raw_text = str(object_value or "").strip()
        if not raw_text or len(raw_text) < 2:
            return OperatorResult(
                success=False,
                output_text="I don't have enough information to store.",
            )
        if raw_text.endswith("?"):
            return OperatorResult(
                success=False,
                output_text="Questions are not stored as claims.",
            )
        if not predicate:
            return OperatorResult(
                success=False,
                output_text="I couldn't determine a predicate for this fact.",
            )

        # Profile lane: facts about the user are stored with subject "user" and a
        # predicate in the user namespace (e.g., user.name, user.alias). This is a
        # structural signal, not an English string match.
        is_profile_fact = subject_id == "user" or predicate.startswith("user.")
        if is_profile_fact:
            slot = predicate.removeprefix("user.") if predicate.startswith("user.") else predicate
            entity = ctx.store.entities.get("user")
            if entity is None:
                entity = Entity(
                    id="user",
                    type=EntityType.PERSON,
                    name="user",
                    aliases=[],
                    confidence=0.7,
                    created_from_signal_id=ctx.input_signal.id,
                    created_at=now,
                    updated_at=now,
                )
                ctx.store.entities.put(entity)
            claim = ctx.store.profile.put(
                slot=slot,
                value=raw_text,
                source_id=ctx.input_signal.source_id,
                permission=ctx.kernel.permission,
                trust=0.7,
            )
        else:
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
            confidence=0.7,
        )
        result = RealizationPipeline().run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
        language = TemplateStrategy._detect_language(ctx.kernel)
        fallback_template = TemplateStrategy._load_template("remember_confirm", language)
        fallback_output = TemplateStrategy._apply(fallback_template, {})
        output = result.output if result.success and result.verified else fallback_output
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_claim_ids=[claim.id],
            action_id="",
            operator_model_id="remember_operator",
            synthesis_verified=result.verified,
            synthesis_verification_type="hard",
            permission="allowed",
            confidence=0.7,
            cost_ms=cost_ms,
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
            output_text=output,
            trace=trace,
            result_signal=result_signal,
            new_claim_ids=[claim.id],
            cost_ms=cost_ms,
            semantic_answer_graph=answer_graph,
        )
