from __future__ import annotations
import json
import time
import uuid
from pathlib import Path

from .base import BaseOperator, OperatorContext, OperatorResult
from .claim_writer import ClaimWriter
from ..types.action import ActionKind
from ..types.graph_patch import GraphPatch
from ..types.signal import Signal, SignalKind, SourceType
from ..types.entity import Entity, EntityType
from ..types.trace import Trace
from types import SimpleNamespace
from ..synthesis.realizer import RealizationPipeline
from ..synthesis.template import TemplateStrategy
from ..kernel.memory_update_planner import MemoryUpdateBatch, MemoryUpdateTask
from ..learning.memory_patch_compiler import MemoryPatchCompiler
from ..learning.patch_validator import PatchValidator


_OPERATOR_MESSAGES_PATH = Path(__file__).parents[1] / "data" / "operator_messages.json"


def _load_operator_messages(language: str = "en") -> dict:
    if not _OPERATOR_MESSAGES_PATH.exists():
        return {}
    data = json.loads(_OPERATOR_MESSAGES_PATH.read_text(encoding="utf-8"))
    return data.get(language, data.get("en", {}))


class RememberOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.REMEMBER

    def _message(self, message_id: str, variables: dict | None = None) -> str:
        ctx = self._ctx
        locale = getattr(ctx.kernel.user, "locale", None) if ctx.kernel.user else None
        language = (locale or {}).get("language", "en")
        messages = _load_operator_messages(language).get("remember", {})
        return messages.get(message_id, message_id).format(**(variables or {}))

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        self._ctx = ctx
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text=self._message("permission_denied_execute"))
        if not ctx.kernel.permission.may_store:
            return OperatorResult(success=False, output_text=self._message("permission_denied_storage"))

        # v3.3: Batch memory update path
        batch = ctx.params.get("batch_tasks")
        if batch is not None:
            return self._execute_batch(ctx, batch)

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
                output_text=self._message("insufficient_information"),
            )
        if raw_text.endswith("?"):
            return OperatorResult(
                success=False,
                output_text=self._message("question_not_stored"),
            )
        if not predicate:
            return OperatorResult(
                success=False,
                output_text=self._message("predicate_missing"),
            )

        compiler = MemoryPatchCompiler()
        validator = PatchValidator(store=ctx.store)
        candidate = compiler.compile(
            subject_entity_id=subject_id,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=object_entity_id,
            domain=domain,
            qualifiers=qualifiers,
            evidence_signal_ids=[ctx.input_signal.id],
            source_id=ctx.input_signal.source_id,
            permission=ctx.kernel.permission,
            confidence=0.7,
            trust=0.7,
            kernel=ctx.kernel,
        )
        validation = validator.validate(candidate, ctx.kernel)
        if not validation.accepted:
            return OperatorResult(
                success=False,
                output_text=f"Cannot store: {'; '.join(validation.reasons)}",
            )

        patches: list[GraphPatch] = []
        writer = ClaimWriter(ctx.store)

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
            claim, patch = writer.write_profile(
                slot=slot,
                value=raw_text,
                source_id=ctx.input_signal.source_id,
                permission=ctx.kernel.permission,
                trust=0.7,
            )
            patches.append(patch)
        else:
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
            claim, patch = writer.write_claim(
                subject_entity_id=subject_id,
                predicate=predicate,
                object_value=object_value,
                object_entity_id=object_entity_id,
                domain=domain,
                qualifiers=qualifiers,
                evidence_signal_ids=[ctx.input_signal.id],
                source_id=ctx.input_signal.source_id,
                permission=ctx.kernel.permission,
                confidence=0.7,
                trust=0.7,
            )
            patches.append(patch)

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
            content=self._message("stored_claim", {"subject_id": subject_id, "predicate": predicate}),
            observed_at=now,
            context_id=ctx.kernel.id,
            salience=0.5,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)
        contract = SimpleNamespace(
            id=uuid.uuid4().hex[:16],
            intent="remember",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_claim_ids=[claim.id],
            selected_model_ids=[],
            entity_refs=[],
            confidence=0.7,
            uncertainty_reasons=[],
            permission_scope="public",
            verification=SimpleNamespace(
                supported=False,
                verification_type="none",
                confidence=0.0,
                unsupported_spans=[],
                uncertainty_reason="",
            ),
        )
        result = RealizationPipeline().run(contract, ctx.kernel, ctx.store, ctx.registry)
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
            semantic_answer_graph_id=contract.id,
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
            semantic_answer_graph=None,
            graph_patches=patches,
        )

    def _execute_batch(
        self,
        ctx: OperatorContext,
        batch: MemoryUpdateBatch | list[MemoryUpdateTask],
    ) -> OperatorResult:
        """Execute a batch of memory update tasks atomically.

        v3.3: Processes all valid tasks from a MemoryUpdateBatch or list of
        MemoryUpdateTask items. Each task produces a claim. Returns a combined
        result with all new claim IDs.
        """
        tasks = batch.tasks if isinstance(batch, MemoryUpdateBatch) else batch
        valid_tasks = [t for t in tasks if t.is_valid()]
        if not valid_tasks:
            return OperatorResult(
                success=False,
                output_text=self._message("insufficient_information"),
            )

        now = time.time()
        patches: list[GraphPatch] = []
        writer = ClaimWriter(ctx.store)

        filtered_tasks: list[MemoryUpdateTask] = []
        for task in valid_tasks:
            raw_text = str(task.object_value or "").strip()
            if not raw_text or len(raw_text) < 2:
                continue
            if raw_text.endswith("?"):
                continue

            entity = ctx.store.entities.get(task.subject_entity_id)
            if entity is None:
                entity = Entity(
                    id=task.subject_entity_id,
                    type=EntityType.PERSON,
                    name=task.subject_entity_id,
                    aliases=[],
                    confidence=0.7,
                    created_from_signal_id=ctx.input_signal.id,
                    created_at=now,
                    updated_at=now,
                )
                ctx.store.entities.put(entity)

            filtered_tasks.append(task)

        if not filtered_tasks:
            return OperatorResult(
                success=False,
                output_text=self._message("insufficient_information"),
            )

        # Validation gate: compile and validate every task before writing
        compiler = MemoryPatchCompiler()
        validator = PatchValidator(store=ctx.store)
        validation_errors: list[str] = []
        for task in filtered_tasks:
            candidate = compiler.compile(
                subject_entity_id=task.subject_entity_id,
                predicate=task.predicate,
                object_value=task.object_value,
                object_entity_id=task.object_entity_id,
                domain=task.domain,
                qualifiers=task.qualifiers,
                evidence_signal_ids=[ctx.input_signal.id],
                source_id=ctx.input_signal.source_id,
                permission=ctx.kernel.permission,
                confidence=task.confidence,
                trust=task.trust,
                kernel=ctx.kernel,
            )
            validation = validator.validate(candidate, ctx.kernel)
            if not validation.accepted:
                validation_errors.append(
                    f"task '{task.predicate}={task.object_value}': {'; '.join(validation.reasons)}"
                )
        if validation_errors:
            return OperatorResult(
                success=False,
                output_text=f"Cannot store batch: {' | '.join(validation_errors)}",
            )

        claims, batch_patches = writer.write_batch(
            tasks=filtered_tasks,
            input_signal_id=ctx.input_signal.id,
            source_id=ctx.input_signal.source_id,
            permission=ctx.kernel.permission,
        )
        patches.extend(batch_patches)
        new_claim_ids = [c.id for c in claims]
        stored_count = len(claims)

        if not new_claim_ids:
            return OperatorResult(
                success=False,
                output_text=self._message("insufficient_information"),
            )

        self_state = ctx.store.self_store.latest()
        if self_state:
            self_state.meta_memory.recently_written_claim_ids.extend(new_claim_ids)
            if len(self_state.meta_memory.recently_written_claim_ids) > 100:
                self_state.meta_memory.recently_written_claim_ids = (
                    self_state.meta_memory.recently_written_claim_ids[-100:]
                )
            self_state.updated_at = time.time()
            ctx.store.self_store.put(self_state)

        result_signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.MEMORY_UPDATE,
            source_id="remember_operator",
            source_type=SourceType.ASSISTANT,
            content=f"Stored {stored_count} fact(s).",
            observed_at=now,
            context_id=ctx.kernel.id,
            salience=0.5,
            trust=0.9,
            permission=ctx.kernel.permission,
        )
        ctx.store.signals.put(result_signal)

        contract = SimpleNamespace(
            id=uuid.uuid4().hex[:16],
            intent="remember",
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_claim_ids=new_claim_ids,
            selected_model_ids=[],
            entity_refs=[],
            confidence=0.7,
            uncertainty_reasons=[],
            permission_scope="public",
            verification=SimpleNamespace(
                supported=False,
                verification_type="none",
                confidence=0.0,
                unsupported_spans=[],
                uncertainty_reason="",
            ),
        )
        result = RealizationPipeline().run(contract, ctx.kernel, ctx.store, ctx.registry)
        language = TemplateStrategy._detect_language(ctx.kernel)
        fallback_template = TemplateStrategy._load_template("remember_confirm", language)
        fallback_output = TemplateStrategy._apply(fallback_template, {})
        output = result.output if result.success and result.verified else fallback_output
        cost_ms = (time.time() - ctx.kernel.time.now) * 1000.0 if ctx.kernel.time.now > 0 else 1.0
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_claim_ids=new_claim_ids,
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
            semantic_answer_graph_id=contract.id,
            realization_strategy=result.strategy,
            realization_verified=result.verified,
            realization_details={
                "source_answer_graph_id": result.metadata.get("source_answer_graph_id"),
                "strategy": result.strategy,
                "batch_count": stored_count,
            },
            verification_details=result.metadata.get("verification", {}),
        )
        return OperatorResult(
            success=True,
            output_text=output,
            trace=trace,
            result_signal=result_signal,
            new_claim_ids=new_claim_ids,
            cost_ms=cost_ms,
            semantic_answer_graph=None,
            graph_patches=patches,
        )
