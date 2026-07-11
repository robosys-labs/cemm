"""Transcript regressions for the Phase 3.2 operational core loop."""

from __future__ import annotations

from cemm.tests.harness import SeededSystem, seed_durable_from_config


def _seeded_system() -> SeededSystem:
    system = SeededSystem()
    seed_durable_from_config(system)
    return system


def test_self_name_query_is_not_hijacked_by_stored_user_name():
    system = _seeded_system()
    runtime = system.pipeline._runtime
    context_id = "phase32-self-name-not-profile"

    runtime.run_text("my name is Chibueze", context_id=context_id)
    result = runtime.run_text("lol so curt ok. What's your own name?", context_id=context_id)

    assert result.obligation_contract is not None
    assert result.obligation_contract.has_query
    assert result.obligation_contract.query_contract.query_kind == "self_identity"
    assert result.obligation_contract.query_contract.relation_key == "answers_identity_as"
    assert result.answer_binding is not None
    assert result.answer_binding.has_answer
    assert all(fill.relation_key == "answers_identity_as" for fill in result.answer_binding.slot_fills)


def test_capability_followup_with_unknown_operator_asks_for_meaning():
    system = _seeded_system()
    runtime = system.pipeline._runtime
    context_id = "phase32-capability-followup"

    runtime.run_text("my name is Chibueze", context_id=context_id)
    runtime.run_text("you can't even handle basic chat, what can you do exactly?", context_id=context_id)
    result = runtime.run_text("lol what else can you do?", context_id=context_id)

    assert result.obligation_contract is not None
    assert result.obligation_contract.obligation_kind == "ask_clarification"
    assert not result.obligation_contract.has_query
    assert any(
        frame.frame_type == "clarification_request"
        and frame.features.get("decode_unknown_content_tokens")
        for frame in result.operational_meaning_frames
    )


def test_bare_unknown_operator_capability_question_asks_for_meaning():
    system = _seeded_system()
    runtime = system.pipeline._runtime

    result = runtime.run_text("what else can you do?", context_id="phase32-bare-else")

    assert result.obligation_contract is not None
    assert result.obligation_contract.obligation_kind == "ask_clarification"
    assert not result.obligation_contract.has_query
    assert any(
        frame.frame_type == "clarification_request"
        and frame.features.get("decode_unknown_content_tokens")
        for frame in result.operational_meaning_frames
    )


def test_direct_capability_query_still_routes_when_decode_is_complete():
    system = _seeded_system()
    runtime = system.pipeline._runtime

    result = runtime.run_text("what can you do?", context_id="phase32-direct-capability")

    assert result.obligation_contract is not None
    assert result.obligation_contract.has_query
    assert result.obligation_contract.query_contract.query_kind == "self_capability"
    assert result.obligation_contract.query_contract.relation_key == "capability"
    assert result.answer_binding is not None
    assert result.answer_binding.has_answer


def test_capability_sufficiency_followup_routes_to_self_capability():
    system = _seeded_system()
    runtime = system.pipeline._runtime
    context_id = "phase32-capability-sufficiency-followup"

    runtime.run_text("what can you do?", context_id=context_id)
    result = runtime.run_text("I mean is that all you can do?", context_id=context_id)

    assert result.obligation_contract is not None
    assert result.obligation_contract.has_query
    assert result.obligation_contract.query_contract.query_kind == "self_capability"
    assert result.answer_binding is not None
    assert result.answer_binding.has_answer
    assert any(
        atom.kind == "intent"
        and atom.key in {"capability_query", "self_capability_query"}
        and atom.group_id in {frame.group_id for frame in result.operational_meaning_frames if frame.frame_type == "self_capability_query"}
        for atom in result.uol_graph.atoms.values()
    )


def test_prefaced_user_name_query_selects_profile_query_over_discourse_filler():
    system = _seeded_system()
    runtime = system.pipeline._runtime
    context_id = "phase32-prefaced-profile-query"

    runtime.run_text("My name is Chibueze, I'm a programmer, can you remember that?", context_id=context_id)
    result = runtime.run_text("OK so what's my name?", context_id=context_id)

    assert result.obligation_contract is not None
    assert result.obligation_contract.has_query
    assert result.obligation_contract.query_contract.query_kind == "profile_dimension"
    assert result.obligation_contract.query_contract.dimension == "name"
    assert result.answer_binding is not None
    assert result.answer_binding.has_answer
    assert any(fill.surface.lower() == "chibueze" for fill in result.answer_binding.slot_fills)


def test_assistant_criticism_is_feedback_not_durable_world_fact():
    system = _seeded_system()
    runtime = system.pipeline._runtime

    result = runtime.run_text(
        "Wow you're just a dumb pattern matcher, I thought you understand meanings",
        context_id="phase32-assistant-criticism",
    )

    assert result.obligation_contract is not None
    assert not result.obligation_contract.has_write
    assert all(frame.frame_type != "world_fact_claim" for frame in result.operational_meaning_frames)
    assert any(frame.frame_type in ("response_feedback", "style_feedback", "social_act") for frame in result.operational_meaning_frames)
    assert any(
        atom.kind == "intent"
        and atom.key in {"frustration_signal", "user_complaint", "assistant_evaluation"}
        for atom in result.uol_graph.atoms.values()
    )


def test_criticism_with_memory_words_is_not_memory_command():
    system = _seeded_system()
    runtime = system.pipeline._runtime

    result = runtime.run_text(
        "you don't know what a programmer is either, do you? you just remember without understanding",
        context_id="phase32-memory-word-criticism",
    )

    assert result.obligation_contract is not None
    assert not result.obligation_contract.has_write
    assert all(frame.frame_type != "memory_command" for frame in result.operational_meaning_frames)


def test_unknown_heavy_profile_shaped_question_does_not_route_to_profile_memory():
    system = _seeded_system()
    runtime = system.pipeline._runtime
    context_id = "phase32-low-decode-profile"

    runtime.run_text("my name is Chibueze", context_id=context_id)
    result = runtime.run_text("flarn name my zibble?", context_id=context_id)

    assert result.obligation_contract is not None
    assert result.obligation_contract.obligation_kind == "ask_clarification"
    assert not result.obligation_contract.has_query
    assert not (result.answer_binding and result.answer_binding.has_answer)


def test_world_question_never_uses_dimensionless_profile_fallback():
    system = _seeded_system()
    runtime = system.pipeline._runtime
    context_id = "phase32-world-question-not-profile"

    runtime.run_text("my name is Chibueze", context_id=context_id)
    result = runtime.run_text("who is the president of United States?", context_id=context_id)

    assert result.obligation_contract is not None
    assert result.obligation_contract.has_query
    assert result.obligation_contract.query_contract.query_kind == "concept_definition"
    assert result.obligation_contract.query_contract.target_scope == "concept_lattice"
    assert result.obligation_contract.query_contract.subject_concept_id == "concept:president_united_states"
    if result.answer_binding is not None:
        assert not result.answer_binding.has_answer


def test_insult_tainted_teaching_is_still_world_fact_and_answerable_later():
    system = _seeded_system()
    runtime = system.pipeline._runtime
    context_id = "phase32-insult-tainted-teaching"

    teach = runtime.run_text(
        "The president of United States is Trump you buffoon",
        context_id=context_id,
    )

    assert any(frame.frame_type == "world_fact_claim" for frame in teach.operational_meaning_frames)
    assert teach.obligation_contract is not None
    assert teach.obligation_contract.has_write

    query = runtime.run_text("who is the president of the united states?", context_id=context_id)

    assert query.obligation_contract is not None
    assert query.obligation_contract.has_query
    assert query.obligation_contract.query_contract.query_kind == "concept_definition"
    assert query.answer_binding is not None
    assert query.answer_binding.has_answer
    surfaces = [fill.surface.lower() for fill in query.answer_binding.slot_fills]
    assert any("trump" in s for s in surfaces)
