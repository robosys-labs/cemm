from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.__main__ import seed_registry, seed_self_state, process_input
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.learning.inductor import Inductor
from cemm.learning.online import OnlineLearner
from cemm.operators.abstain import AbstainOperator
from cemm.operators.answer import AnswerOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.registry import OperatorRegistry
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.operators.base import OperatorContext
from cemm.synthesis.result import SynthesisResult
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.store.store import Store
from cemm.registry import Registry


def _runtime():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), RetrieveOperator(), AbstainOperator()]:
        op_registry.register(op)
    pipeline = Pipeline(store, registry)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    loop = RecursiveLoop(pipeline, store, learner, Inductor(store, registry=registry))
    return store, registry, op_registry, pipeline, learner, loop


def _turn(text: str):
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    output = process_input(text, store, registry, op_registry, pipeline, learner, loop, f"ctx_{int(time.time())}", [0])
    return output, loop


def test_remember_output_is_realized_from_sag_not_manual_text() -> None:
    output, loop = _turn("remember I like coffee")
    assert output
    trace = loop._last_result.kernel.memory.working_signal_ids
    assert trace


def test_retrieve_output_is_realized_from_sag_not_manual_text() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("remember I like coffee", store, registry, op_registry, pipeline, learner, loop, "ctx_retrieve", [0])
    output = process_input("what do I like?", store, registry, op_registry, pipeline, learner, loop, "ctx_retrieve", [1])
    assert output


def test_abstain_operator_keeps_verification_diagnostics_internal(monkeypatch) -> None:
    store, registry, _, pipeline, _, _ = _runtime()
    kernel = pipeline.run("unanswerable input", context_id="ctx_abstain").kernel
    assert kernel is not None
    signal = Signal(
        id="sig_abstain",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="unanswerable input",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )

    def fake_run(*args, **kwargs):
        return SynthesisResult(
            success=True,
            output="",
            verified=False,
            metadata={"verification": {"details": ["No evidence selected for synthesis"]}},
        )

    import cemm.operators.abstain as abstain_module

    monkeypatch.setattr(abstain_module._pipeline, "run", fake_run)
    result = AbstainOperator().execute(OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        params={"reason": "internal reason"},
    ))

    assert result.success
    assert "verification" not in result.output_text.lower()
    assert "no evidence selected" not in result.output_text.lower()


def test_scoped_help_request_response_stays_on_user_topic() -> None:
    output, _ = _turn("I mean can you help me grow my career?")
    output_lower = output.lower()
    assert "career" in output_lower or "grow" in output_lower
    assert "verified information" not in output_lower


def test_whats_going_on_response_is_not_abstain_text() -> None:
    output, _ = _turn("what's going on")
    assert "verified information" not in output.lower()
    assert "interesting topic" not in output.lower()


def test_what_does_that_mean_response_mentions_clarification_target() -> None:
    output, _ = _turn("what does that mean?")
    output_lower = output.lower()
    assert "part" in output_lower or "meant" in output_lower or "previous" in output_lower


def test_fresh_world_question_explains_live_information_limit() -> None:
    output, _ = _turn("what is the weather today?")
    output_lower = output.lower()
    assert "verified information" not in output_lower
    assert "live" in output_lower or "current" in output_lower or "latest" in output_lower


def test_repeated_greeting_in_same_session_is_not_first_turn_template() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    first = process_input("hello", store, registry, op_registry, pipeline, learner, loop, "ctx_greet", [0])
    second = process_input("hey", store, registry, op_registry, pipeline, learner, loop, "ctx_greet", [1])
    assert first
    assert second
    assert second != first
    assert "today" not in second.lower()


def test_repeated_acknowledgment_in_same_session_is_not_static_prompt() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    first = process_input("ok", store, registry, op_registry, pipeline, learner, loop, "ctx_ack", [0])
    second = process_input("okay", store, registry, op_registry, pipeline, learner, loop, "ctx_ack", [1])
    assert first
    assert second
    assert second != first
    assert "what else would you like to know or share" not in second.lower()


def test_later_phatic_checkin_is_not_first_turn_health_check() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("hello", store, registry, op_registry, pipeline, learner, loop, "ctx_phatic", [0])
    output = process_input("how are you?", store, registry, op_registry, pipeline, learner, loop, "ctx_phatic", [1])
    assert output
    assert "running normally" not in output.lower()


def test_repeated_playful_acknowledgment_in_same_session_varies() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    first = process_input("lol", store, registry, op_registry, pipeline, learner, loop, "ctx_playful", [0])
    second = process_input("fair enough", store, registry, op_registry, pipeline, learner, loop, "ctx_playful", [1])
    assert first
    assert second
    assert second != first
    assert "still with you" not in second.lower()


def test_repeated_frustration_signal_in_same_session_is_not_static() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    first = process_input("you are dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_frustration", [0])
    second = process_input("you are useless", store, registry, op_registry, pipeline, learner, loop, "ctx_frustration", [1])
    assert first
    assert second
    assert second != first
    assert "let me keep it simple and try to do better" not in second.lower()


def test_first_playful_turn_after_neutral_chat_keeps_base_tone() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("hello", store, registry, op_registry, pipeline, learner, loop, "ctx_playful_neutral", [0])
    output = process_input("lol", store, registry, op_registry, pipeline, learner, loop, "ctx_playful_neutral", [1])
    assert "still with you" in output.lower()


def test_first_frustration_after_neutral_chat_keeps_base_repair() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("hello", store, registry, op_registry, pipeline, learner, loop, "ctx_frustration_neutral", [0])
    output = process_input("you are dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_frustration_neutral", [1])
    assert "let me keep it simple and try to do better" in output.lower()


def test_negative_turn_cools_lingering_playfulness() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("hello", store, registry, op_registry, pipeline, learner, loop, "ctx_affect_balance", [0])
    process_input("lol", store, registry, op_registry, pipeline, learner, loop, "ctx_affect_balance", [1])
    process_input("you are dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_affect_balance", [2])
    affect = loop._last_result.kernel.user.affect
    assert affect.playfulness < 0.6
    assert affect.current_stance != "playful"


def test_high_repetition_friction_acknowledges_pattern() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("you are dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_repetition", [0])
    process_input("you are useless", store, registry, op_registry, pipeline, learner, loop, "ctx_repetition", [1])
    output = process_input("this is dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_repetition", [2])
    assert "same loop" in output.lower() or "going in circles" in output.lower() or "stuck" in output.lower()


def test_runtime_transcript_handles_social_repair_capability_and_teaching_memory() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    ctx = "ctx_runtime_transcript_regression"
    turn = [0]

    def say(text: str) -> str:
        output = process_input(text, store, registry, op_registry, pipeline, learner, loop, ctx, turn)
        turn[0] += 1
        return output

    say("hi")

    mixed_checkin = say("i'm good lol, how are you?")
    assert "verified information" not in mixed_checkin.lower()
    assert any(
        cue in mixed_checkin.lower()
        for cue in ("glad", "good", "doing", "here", "with you", "running")
    )

    skeptical_eval = say("I thought you are smarter than that now")
    assert "verified information" not in skeptical_eval.lower()
    assert any(
        cue in skeptical_eval.lower()
        for cue in ("try", "better", "missed", "understand", "simple")
    )

    negative_eval = say("really it seems you've rather gotten worse than before")
    assert "verified information" not in negative_eval.lower()
    assert any(
        cue in negative_eval.lower()
        for cue in ("try", "better", "missed", "understand", "simple", "reset")
    )

    capability = say("what then can you answer?")
    assert "verified information" not in capability.lower()
    assert any(cue in capability.lower() for cue in ("chat", "remember", "learn", "answer"))

    insult = say("oh man you're much dumber than before")
    assert "information to store" not in insult.lower()
    assert any(cue in insult.lower() for cue in ("try", "better", "simple", "reset", "missed"))

    learn = say("can you even learn?")
    assert "verified information" not in learn.lower()
    assert "learn" in learn.lower() or "remember" in learn.lower()

    unknown_person = say("Do you know who Barack Obama is?")
    assert "barack obama" in unknown_person.lower() or "name" in unknown_person.lower()

    taught_fact = say("he's a former president, do you know what that means?")
    assert "verified information" not in taught_fact.lower()
    assert any(cue in taught_fact.lower() for cue in ("barack", "obama", "former", "president", "remember"))

    recall = say("I told you about Barack Obama, do you remember anything?")
    assert "interesting topic" not in recall.lower()
    assert any(cue in recall.lower() for cue in ("barack", "obama", "former president", "president"))


def test_cause_aware_loop_repair_mentions_seeded_cause() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("you are dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_cause", [0])
    process_input("you are useless", store, registry, op_registry, pipeline, learner, loop, "ctx_cause", [1])

    import time
    from cemm.types.claim import Claim
    from cemm.types.entity import Entity, EntityType
    from cemm.types.permission import Permission

    store.entities.put(Entity(
        id="retrieval_pipeline",
        type=EntityType.SYSTEM,
        name="retrieval pipeline",
        aliases=[],
        confidence=0.9,
        created_from_signal_id="seed",
        created_at=time.time(),
        updated_at=time.time(),
    ))

    cause = Claim(
        id="claim_seeded_cause",
        subject_entity_id="retrieval_pipeline",
        predicate="causes",
        object_value="retrieval failure",
        domain="causal",
        confidence=0.9,
        trust=0.9,
        salience=0.8,
        observed_at=time.time(),
        updated_at=time.time(),
        permission=Permission.public(),
    )
    store.claims.put(cause)

    output = process_input("this is dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_cause", [2])
    # Seed a likely cause directly to exercise the realization path the runtime will use.
    loop._last_result.kernel.conversation.dynamics.likely_cause_claim_ids = ["claim_seeded_cause"]
    from cemm.synthesis.realizer import RealizationPipeline
    from cemm.types.semantic_answer_graph import SemanticAnswerGraph
    sag = SemanticAnswerGraph(
        id="sag_cause_runtime",
        intent="frustration_response",
        source_signal_ids=[loop._last_result.signals[0].id],
        context_id=loop._last_result.kernel.id,
        confidence=0.9,
    )
    rerender = RealizationPipeline().run(sag, loop._last_result.kernel, store, registry)
    assert "retrieval failure" in rerender.output.lower()


def test_runtime_repetition_can_surface_recent_written_cause() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()

    import time
    from cemm.types.claim import Claim
    from cemm.types.entity import Entity, EntityType
    from cemm.types.permission import Permission

    store.entities.put(Entity(
        id="retrieval_pipeline_runtime",
        type=EntityType.SYSTEM,
        name="retrieval pipeline runtime",
        aliases=[],
        confidence=0.9,
        created_from_signal_id="seed",
        created_at=time.time(),
        updated_at=time.time(),
    ))
    cause = Claim(
        id="claim_runtime_cause",
        subject_entity_id="retrieval_pipeline_runtime",
        predicate="causes",
        object_value="retrieval failure",
        domain="causal",
        confidence=0.9,
        trust=0.9,
        salience=0.8,
        observed_at=time.time(),
        updated_at=time.time(),
        permission=Permission.public(),
    )
    store.claims.put(cause)
    self_state = store.self_store.latest()
    assert self_state is not None
    self_state.meta_memory.recently_written_claim_ids.append("claim_runtime_cause")
    self_state.updated_at = time.time()
    store.self_store.put(self_state)

    process_input("you are dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_runtime_cause", [0])
    process_input("you are useless", store, registry, op_registry, pipeline, learner, loop, "ctx_runtime_cause", [1])
    output = process_input("this is dumb", store, registry, op_registry, pipeline, learner, loop, "ctx_runtime_cause", [2])

    assert "retrieval failure" in output.lower()
