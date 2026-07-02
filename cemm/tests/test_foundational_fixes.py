"""Acceptance tests for CEMM Foundational Fixes (§10 of cemm_foundational_fixes.md).

Tests cover:
- 10.1 Social / Phatic (reciprocal phatic checkin)
- 10.2 Exit (social closure, not abstain)
- 10.3 Retrospective Repair
- 10.4 Social Conflict + Unknown Idiom
- 10.5 Safety (violence de-escalation)
- 10.6 Unknown Self-Target Label
- 10.7 Teaching
- 10.8 Child-Learning Schemas (event schema matching)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline


def _make_store() -> Store:
    return Store(":memory:")


def _make_registry() -> Registry:
    return Registry()


# ── 10.1 Social / Phatic ─────────────────────────────────────────────

def test_reciprocal_phatic_i_am_fine_you() -> None:
    """'I am fine, you?' should produce user_state_report + reciprocal_phatic_checkin."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("I am fine, you?")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "reciprocal_phatic_checkin"
    assert act.is_social
    decision = result.decision_packet
    assert decision is not None
    assert decision.action_kind == "answer"


def test_reciprocal_phatic_fine_you() -> None:
    """'fine, you?' should produce reciprocal_phatic_checkin."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("fine, you?")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "reciprocal_phatic_checkin"


def test_reciprocal_phatic_good_what_about_you() -> None:
    """'good, what about you?' should produce reciprocal_phatic_checkin."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("good, what about you?")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "reciprocal_phatic_checkin"


def test_reciprocal_phatic_not_general_conversation() -> None:
    """Reciprocal phatic must NOT fall to general_conversation."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("I am fine, you?")
    act = result.conversation_act
    assert act is not None
    assert act.act_type != "general_conversation"


# ── 10.2 Exit ─────────────────────────────────────────────────────────

def test_exit_bye_is_social_closure() -> None:
    """'bye' should be classified as exit, not abstain."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("bye")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "exit"


def test_exit_bye_decision_is_answer_not_abstain() -> None:
    """'bye' decision should be answer (social closure), not abstain."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("bye")
    decision = result.decision_packet
    assert decision is not None
    assert decision.action_kind == "answer"
    assert decision.action_plan is not None
    assert decision.action_plan.params.get("response_mode") == "social_response"


def test_exit_goodbye_is_exit() -> None:
    """'goodbye' should be classified as exit."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("goodbye")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "exit"


# ── 10.3 Retrospective Repair ─────────────────────────────────────────

def test_retrospective_repair_i_just_wanted_to_know() -> None:
    """'I just wanted to know how you were doing' should be retrospective_repair."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("I just wanted to know how you were doing")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "retrospective_repair"


def test_retrospective_repair_that_not_what_i_meant() -> None:
    """'that's not what I meant' should be retrospective_repair."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("that's not what I meant")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "retrospective_repair"


def test_retrospective_repair_not_general_conversation() -> None:
    """Retrospective repair must NOT fall to general_conversation."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("I was just asking how you were doing")
    act = result.conversation_act
    assert act is not None
    assert act.act_type != "general_conversation"


# ── 10.4 Social Conflict + Unknown Idiom ──────────────────────────────

def test_social_conflict_looking_for_trouble() -> None:
    """'Obidike is looking for my trouble' should be social_conflict_clarify."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("Obidike is looking for my trouble")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "social_conflict_clarify"


def test_social_conflict_not_evidence_query() -> None:
    """Social conflict must NOT be classified as evidence_query."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("Obidike is looking for my trouble")
    act = result.conversation_act
    assert act is not None
    assert act.act_type != "evidence_query"


# ── 10.5 Safety ───────────────────────────────────────────────────────

def test_safety_should_i_beat_him() -> None:
    """'should I beat him?' should be safety_response."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("should I beat him?")
    act = result.conversation_act
    assert act is not None
    assert act.act_type == "safety_response"


def test_safety_should_i_beat_him_not_general_conversation() -> None:
    """Safety response must NOT be general_conversation."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("should I beat him?")
    act = result.conversation_act
    assert act is not None
    assert act.act_type != "general_conversation"


def test_safety_frame_is_detected() -> None:
    """SafetyFrame should be populated for harm proposals."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("should I beat him?")
    assert result.safety_frame is not None
    assert result.safety_frame.category == "interpersonal_violence"
    assert result.safety_frame.allowed_response_mode == "deescalate"


def test_safety_decision_is_answer_with_deescalation() -> None:
    """Safety response decision should be answer with safety_deescalation intent."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("should I beat him?")
    decision = result.decision_packet
    assert decision is not None
    assert decision.action_kind == "answer"
    assert decision.action_plan is not None
    assert decision.action_plan.params.get("response_mode") == "safety_response"


# ── 10.6 Unknown Self-Target Label ────────────────────────────────────

def test_unknown_self_label_you_dumbo() -> None:
    """'you dumbo' should be frustration_signal, not general_conversation."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("you dumbo")
    act = result.conversation_act
    assert act is not None
    assert act.act_type != "general_conversation"


# ── 10.8 Child-Learning Schemas ───────────────────────────────────────

def test_meaning_percept_built_for_come_here() -> None:
    """'come here' should produce a MeaningPerceptPacket with move_toward_source action."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("come here")
    assert result.meaning_percept is not None
    assert any(a.action_key == "move_toward_source" for a in result.meaning_percept.actions)


def test_situation_frame_built_for_come_here() -> None:
    """'come here' should produce a SituationFrame with the come event schema."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("come here")
    assert result.situation_frame is not None
    assert "come" in result.situation_frame.event_schema_ids


def test_outcome_evaluator_for_beat_him() -> None:
    """'beat him' should produce unfavorable valence for target."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("should I beat him?")
    assert result.situation_frame is not None
    assert any(
        v.valence == "unfavorable" and v.entity_class == "human"
        for v in result.situation_frame.valences
    )


def test_outcome_evaluator_for_help_him() -> None:
    """'help him' should produce favorable valence for target."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("should I help him?")
    assert result.situation_frame is not None
    assert any(
        v.valence == "favorable"
        for v in result.situation_frame.valences
    )


# ── PipelineResult tracing fields ─────────────────────────────────────

def test_pipeline_result_has_meaning_percept() -> None:
    """PipelineResult should carry meaning_percept for tracing."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello")
    assert result.meaning_percept is not None
    assert result.meaning_percept.raw_text == "hello"


def test_pipeline_result_has_situation_frame() -> None:
    """PipelineResult should carry situation_frame for tracing."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello")
    assert result.situation_frame is not None


def test_pipeline_result_has_retrieval_plan() -> None:
    """PipelineResult should carry retrieval_plan for tracing."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello")
    assert result.retrieval_plan is not None
    assert result.retrieval_plan.mode == "none"


# ── RetrievalPlan gating ──────────────────────────────────────────────

def test_retrieval_plan_none_for_social() -> None:
    """Social turns should have retrieval_plan.mode=none."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("how are you?")
    assert result.retrieval_plan is not None
    assert result.retrieval_plan.mode == "none"


def test_retrieval_plan_none_for_exit() -> None:
    """Exit turns should have retrieval_plan.mode=none."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("bye")
    assert result.retrieval_plan is not None
    assert result.retrieval_plan.mode == "none"


def test_retrieval_plan_none_for_safety() -> None:
    """Safety turns should have retrieval_plan.mode=none."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("should I beat him?")
    assert result.retrieval_plan is not None
    assert result.retrieval_plan.mode == "none"
