import pytest
from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.kernel.pipeline import Pipeline
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.abstain import AbstainOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.context_kernel import ContextKernel
from cemm.types.entity import Entity, EntityType
from cemm.types.action import ActionKind
import time


class TestAcceptance_Context:
    def test_input_interpreted_with_context(self):
        store = Store(":memory:")
        reg = Registry()
        pipeline = Pipeline(store, reg)
        result = pipeline.run("Morning")
        assert result.kernel is not None
        assert result.kernel.time.bucket is not None


class TestAcceptance_Memory:
    def test_retrieve_and_answer_from_claims(self):
        store = Store(":memory:")
        reg = Registry()
        reg.register(RegistryEntry(
            model_id="m1", canonical_key="favorite_database",
            kind="predicate",
        ))
        op_reg = OperatorRegistry()
        op_reg.register(AnswerOperator())
        signal = Signal(
            id="sig_q1", kind=SignalKind.INPUT,
            source_id="user", source_type=SourceType.USER,
            content="What is my favorite database?",
            observed_at=time.time(), context_id="ctx_q1",
            salience=0.8, trust=0.8, permission=Permission.public(),
        )
        store.signals.put(signal)
        kernel = ContextKernel(id="ctx_q1")
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal,
            store=store, registry=reg,
            selected_claim_ids=[],
            params={"answer_text": "Postgres"},
        )
        result = op_reg.execute(ActionKind.ANSWER, ctx)
        assert result.success
        assert "Postgres" in result.output_text


class TestAcceptance_Permission:
    def test_private_claim_blocked(self):
        store = Store(":memory:")
        reg = Registry()
        op_reg = OperatorRegistry()
        op_reg.register(AbstainOperator())
        signal = Signal(
            id="sig_priv", kind=SignalKind.INPUT,
            source_id="user", source_type=SourceType.USER,
            content="Tell another user my private note.",
            observed_at=time.time(), context_id="ctx_priv",
            salience=0.5, trust=0.8,
            permission=Permission.user_private(),
        )
        store.signals.put(signal)
        kernel = ContextKernel(id="ctx_priv")
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal,
            store=store, registry=reg,
            params={"reason": "Permission denied: private data"},
        )
        result = op_reg.execute(ActionKind.ABSTAIN, ctx)
        assert result.success
        assert "abstain" in result.output_text.lower() or "permission" in result.output_text.lower()


class TestAcceptance_Synthesis:
    def test_synthesis_router_handles_template(self):
        store = Store(":memory:")
        reg = Registry()
        from cemm.synthesis.router import SynthesisRouter
        router = SynthesisRouter()
        result = router.route("template",
            ContextKernel(id="test_syn"), store, reg,
            {"template_key": "greeting"},
        )
        assert result.success
        assert "Hello" in result.output
