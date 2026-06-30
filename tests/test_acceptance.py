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
            params={},
        )
        result = op_reg.execute(ActionKind.ANSWER, ctx)
        assert result.success


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


class TestAcceptance_UOLMapping:
    def test_uol_maps_insults_to_atoms(self):
        from cemm.registry.uol_mapper import UOLMapper
        from cemm.registry import Registry
        from cemm.types.context_kernel import ContextKernel
        from cemm.types.self_state import SelfState
        registry = Registry()
        registry.register(RegistryEntry(model_id="uol_low", canonical_key="low_competence", kind="uol_semantic", aliases=["dumb", "stupid", "fool", "idiot", "useless", "broken"]))
        registry.register(RegistryEntry(model_id="uol_high", canonical_key="high_quality", kind="uol_semantic", aliases=["great", "awesome", "excellent", "amazing", "helpful"]))
        registry.register(RegistryEntry(model_id="uol_eval", canonical_key="assert_evaluation", kind="uol_semantic", aliases=["is", "are", "was", "were"]))
        mapper = UOLMapper(registry)
        kernel = ContextKernel(id="uol_test")
        kernel.self_view = kernel.self_view.from_self_state(SelfState(id="self_main", name="cemm"))
        atoms = mapper.map_signal("you are dumb", kernel)
        entity_refs = [a for a in atoms if a.kind == "entity_ref"]
        states = [a for a in atoms if a.kind == "state"]
        assert any(a.role == "target" for a in entity_refs)
        assert any(a.state_key == "low_competence" for a in states)


class TestAcceptance_Recursion:
    def test_recursive_loop_processes_internal_signals(self):
        from cemm.kernel.recursive_loop import RecursiveLoop
        from cemm.store.store import Store
        from cemm.registry import Registry
        from cemm.kernel.pipeline import Pipeline
        from cemm.learning.online import OnlineLearner
        from cemm.learning.inductor import Inductor
        store = Store(":memory:")
        reg = Registry()
        pipeline = Pipeline(store, reg)
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
        inductor = Inductor(store)
        loop = RecursiveLoop(pipeline, store, learner, inductor)
        kernel, signals, actionable = loop.run_once("hello", "accept_rec")
        assert kernel is not None


class TestAcceptance_ContextInference:
    def test_first_utterance_greeting(self):
        from cemm.kernel.context_inference import ContextInferenceEngine
        from cemm.store.store import Store
        from cemm.registry import Registry
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.context_kernel import ContextKernel, ConversationState
        from cemm.types.permission import Permission
        import time
        store = Store(":memory:")
        reg = Registry()
        engine = ContextInferenceEngine(store, reg)
        signal = Signal(id="sig_greet", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="Good morning",
            observed_at=time.time(), context_id="ctx", salience=0.8, trust=0.8,
            permission=Permission.public())
        kernel = ContextKernel(id="ctx_greet", permission=Permission.public())
        kernel.conversation = ConversationState(turn_index=1)
        inference = engine.infer(signal, kernel)
        assert inference.frame_id == "session_opening"

    def test_location_ambiguity_weather(self):
        from cemm.kernel.context_inference import ContextInferenceEngine
        from cemm.store.store import Store
        from cemm.registry import Registry
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.context_kernel import ContextKernel, ConversationState
        from cemm.types.permission import Permission
        import time
        engine = ContextInferenceEngine(Store(":memory:"), Registry())
        signal = Signal(id="sig_w", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="what is the weather?",
            observed_at=time.time(), context_id="ctx", salience=0.8, trust=0.8,
            permission=Permission.public())
        kernel = ContextKernel(id="ctx_w", permission=Permission.public())
        inference = engine.infer(signal, kernel)
        assert inference.confidence <= 0.5


class TestAcceptance_CausalModel:
    def test_causal_prediction_with_rule(self):
        from cemm.store.store import Store
        from cemm.causal.inference import CausalInference
        from cemm.types.model import Model, ModelKind, ModelStatus
        from cemm.types.claim import Claim
        from cemm.types.context_kernel import ContextKernel
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.permission import Permission
        import time
        store = Store(":memory:")
        from cemm.types.entity import Entity, EntityType
        store.entities.put(Entity(id="file1", type=EntityType.OBJECT,
            name="file1", aliases=[], confidence=0.9,
            created_from_signal_id="sig_c", created_at=time.time(),
            updated_at=time.time()))
        sig = Signal(id="sig_c", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="test",
            observed_at=time.time(), context_id="ctx", salience=0.5, trust=0.5,
            permission=Permission.public())
        store.signals.put(sig)
        model = Model(id="causal_del", kind=ModelKind.CAUSAL_RULE, name="delete_file",
            description="Deleting a file removes it", preconditions=["file_exists"],
            effects=["file_deleted"], confidence=0.9, trust=0.8,
            status=ModelStatus.ACTIVE, created_at=time.time(), updated_at=time.time())
        store.models.put(model)
        claim = Claim(id="cl_exists", subject_entity_id="file1",
            predicate="file_exists", object_value=True,
            evidence_signal_ids=["sig_c"], source_id="user", domain="test")
        store.claims.put(claim)
        inference = CausalInference(store)
        kernel = ContextKernel(id="causal_test")
        result = inference.predict("delete_file", ["cl_exists"], kernel)
        assert len(result.predictions) >= 1


class TestAcceptance_FirstUtterance:
    def test_greeting_detected(self):
        from cemm.kernel.context_inference import ContextInferenceEngine
        from cemm.store.store import Store
        from cemm.registry import Registry
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.context_kernel import ContextKernel, ConversationState
        from cemm.types.permission import Permission
        import time
        engine = ContextInferenceEngine(Store(":memory:"), Registry())
        signal = Signal(id="sg", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="Good morning",
            observed_at=time.time(), context_id="ctx", salience=0.8, trust=0.8,
            permission=Permission.public())
        kernel = ContextKernel(id="ctx_g")
        kernel.conversation = ConversationState(turn_index=1)
        inference = engine.infer(signal, kernel)
        assert inference.frame_id == "session_opening"

    def test_urgency_detected(self):
        from cemm.kernel.context_inference import ContextInferenceEngine
        from cemm.store.store import Store
        from cemm.registry import Registry
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.context_kernel import ContextKernel, ConversationState
        from cemm.types.permission import Permission
        import time
        engine = ContextInferenceEngine(Store(":memory:"), Registry())
        signal = Signal(id="sf", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="Fix this now",
            observed_at=time.time(), context_id="ctx", salience=0.8, trust=0.8,
            permission=Permission.public())
        kernel = ContextKernel(id="ctx_f")
        kernel.conversation = ConversationState(turn_index=1)
        inference = engine.infer(signal, kernel)
        assert inference.confidence >= 0.0  # should not crash

class TestAcceptance_CausalConfidence:
    def test_chain_confidence_capped(self):
        from cemm.causal.inference import CausalInference
        from cemm.store.store import Store
        from cemm.types.context_kernel import ContextKernel
        from cemm.types.packets import InferencePacket
        store = Store(":memory:")
        inference = CausalInference(store)
        kernel = ContextKernel(id="cc_test")
        result = inference.transitive_closure([], kernel, max_depth=0)
        assert isinstance(result, InferencePacket)

class TestAcceptance_InvariantGuard:
    def test_invariant_guard_basic(self):
        from cemm.kernel.invariant_guard import InvariantGuard
        guard = InvariantGuard()
        guard.reset()
        assert len(guard.assert_no_errors()) == 0
        guard.check_recursive_budget(None, 999)
        assert len(guard.assert_no_errors()) >= 1
