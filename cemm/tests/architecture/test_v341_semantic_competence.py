"""v3.4.1 cutover, learning-dialogue, and NLG exit gates."""
from __future__ import annotations

from pathlib import Path

import pytest


def test_public_entrypoints_have_no_legacy_imports():
    for path in (Path("cemm/__main__.py"), Path("cemm/web_demo.py")):
        source = path.read_text(encoding="utf-8")
        assert "legacy.v3_3" not in source
        assert "from cemm.legacy" not in source
        assert "from .legacy" not in source


def test_input_signal_separates_identity_from_content():
    from cemm.kernel.model.signal import InputSignal
    from cemm.kernel.model.cycle import CycleTrigger

    signal = InputSignal(id="signal:1", content="hello", context_id="session:1")
    trigger = CycleTrigger(
        trigger_kind="user_utterance",
        signal_ids=(signal.id,),
        input_signals=(signal,),
        context_id="session:1",
    )
    assert trigger.signal_ids == ("signal:1",)
    assert trigger.input_signals[0].content == "hello"


def test_tokenizer_does_not_declare_semantic_unknownness():
    from cemm.language.en.tokenizer import tokenize

    stream = tokenize("president")
    assert stream.tokens[0].raw_form == "president"
    assert stream.tokens[0].is_unknown is False


def test_opaque_identity_is_stable():
    from cemm.kernel.schema.store import SemanticSchemaStore
    from cemm.kernel.boot.v341 import register_v341_foundations
    from cemm.language.en.adapter import EnglishLanguageAdapter
    from cemm.kernel.understanding.composer import SemanticComposer

    store = SemanticSchemaStore()
    register_v341_foundations(store)
    adapter = EnglishLanguageAdapter(store)
    composer = SemanticComposer(store)
    first = composer.compose(adapter.perceive("president", "en"))
    second = composer.compose(adapter.perceive("president", "en"))
    assert first.opaque_lexeme_refs == second.opaque_lexeme_refs
    assert first.opaque_lexeme_refs == ("opaque:en:president",)


def test_elongated_greeting_is_lexical_candidate_not_phrase_route():
    from cemm.kernel.schema.store import SemanticSchemaStore
    from cemm.kernel.boot.v341 import register_v341_foundations
    from cemm.language.en.adapter import EnglishLanguageAdapter

    store = SemanticSchemaStore()
    register_v341_foundations(store)
    evidence = EnglishLanguageAdapter(store).perceive("hiii", "en")
    keys = {candidate.semantic_key for candidate in evidence.lexical_sense_candidates}
    assert "greet" in keys
    assert any(cue.cue_kind == "greeting" for cue in evidence.pragmatic_cues)


def test_english_constructions_do_not_own_semantic_predicates():
    source = Path("cemm/language/en/constructions.py").read_text(encoding="utf-8")
    forbidden = {
        "has_condition",
        "subkind_of",
        "instance_of",
        "query_content",
        "query_truth",
        "capable_of",
        'predicate_schema_ref="',
    }
    for marker in forbidden:
        assert marker not in source


def test_gap_detector_does_not_own_query_predicate_roles():
    source = Path("cemm/kernel/understanding/gap_detector.py").read_text(encoding="utf-8")
    forbidden = {
        "has_condition",
        "query_content",
        "query_truth",
        "role:condition",
        "role:requested_content",
        "role:truth_status",
    }
    for marker in forbidden:
        assert marker not in source


def test_response_planner_does_not_key_self_status_on_input_predicate_names():
    source = Path("cemm/kernel/response/planner.py").read_text(encoding="utf-8")
    forbidden = {
        'predicate_semantic_key", "") != "has_condition"',
        'operation_schema_ref", "") == "op:answer"',
    }
    for marker in forbidden:
        assert marker not in source


def test_learning_dialogue_does_not_match_raw_english_phrase_lists():
    source = Path("cemm/kernel/learning/coordinator.py").read_text(encoding="utf-8")
    forbidden = {
        "which part",
        "what part",
        "the role",
        "the person",
        "both of them",
        "role and person",
    }
    for marker in forbidden:
        assert marker not in source


def test_composer_does_not_invent_embedded_complement_predicates():
    source = Path("cemm/kernel/understanding/composer.py").read_text(encoding="utf-8")
    forbidden = {
        '"subkind_of"',
        '"knows"',
        '"predicate:knows"',
        '"boot:predicate:knows:v1"',
    }
    for marker in forbidden:
        assert marker not in source


def test_missing_epistemic_assessment_never_becomes_assertion():
    from cemm.kernel.response.planner import ContentSelectionInput, ResponsePlanner

    plan = ResponsePlanner().plan_response(ContentSelectionInput(
        proposition_refs=("prop:unassessed",),
        assessments=(),
    ))
    assert all(item.semantic_ref != "prop:unassessed" for item in plan.content_items)
    assert any(item.content_kind == "honest_abstention" for item in plan.content_items)


def test_lexical_gate_allows_mention_but_blocks_unregistered_assertion():
    from cemm.kernel.boot.v341 import register_v341_foundations
    from cemm.kernel.model.message import LexicalRequirement, MessageContentItem
    from cemm.kernel.response.lexical_use import LexicalUseGate, LexicalUseStatus
    from cemm.kernel.schema.store import SemanticSchemaStore

    store = SemanticSchemaStore()
    register_v341_foundations(store)
    gate = LexicalUseGate(store)
    item = MessageContentItem(
        semantic_ref="item:1",
        provenance_refs=("evidence:1",),
        lexical_requirements=(
            LexicalRequirement(
                semantic_key="lexical_mention",
                use_mode="mention",
                surface_hint="president",
            ),
            LexicalRequirement(
                semantic_key="unregistered_action",
                use_mode="assert",
            ),
        ),
    )
    result = gate.authorize_item(item, language="en")
    statuses = [assessment.status for assessment in result.assessments]
    assert LexicalUseStatus.MENTION_ONLY in statuses
    assert LexicalUseStatus.BLOCKED in statuses
    assert not result.authorized


def test_renderer_does_not_have_generic_id_or_got_it_fallback():
    source = Path("cemm/kernel/response/renderer.py").read_text(encoding="utf-8")
    assert "Got it" not in source
    assert "regarding {semantic_ref}" not in source
    assert "understood regarding" not in source


def test_learning_probe_registers_only_after_dispatch():
    from cemm.kernel.boot.v341 import register_v341_foundations
    from cemm.kernel.learning.coordinator import LearningCoordinator
    from cemm.kernel.model.gap import GapRecord, ProbePlan
    from cemm.kernel.model.message import MessageContentItem, MessageRoleValue
    from cemm.kernel.schema.store import SemanticSchemaStore

    store = SemanticSchemaStore()
    register_v341_foundations(store)
    coordinator = LearningCoordinator(store)
    gap = GapRecord(
        id="gap:president",
        gap_kind="missing_semantic_family",
        target_artifact_ref="opaque:en:president",
        missing_fields=("semantic_family",),
        blocked_stage="ground",
        learnable=True,
        probe_options=(ProbePlan(
            probe_kind="ask_user",
            target_ref="opaque:en:president",
            expected_evidence_kind="semantic_family",
            idempotency_key="probe:president:family",
        ),),
    )
    coordinator.open_transaction(gap, context_ref="session:1")
    assert coordinator.pending_obligations("session:1") == ()
    item = MessageContentItem(
        semantic_ref="learning_probe:gap:president",
        content_kind="learning_probe",
        provenance_refs=(gap.id,),
        role_values=(
            MessageRoleValue("gap_ref", semantic_ref=gap.id),
            MessageRoleValue("probe_key", surface_hint="probe:president:family"),
        ),
    )
    obligation = coordinator.register_probe_dispatch(
        context_ref="session:1",
        message_item=item,
        gaps=(gap,),
        output_event_ref="message:1",
    )
    assert obligation is not None
    assert coordinator.pending_obligations("session:1") == (obligation,)


def test_meta_question_resolves_pending_obligation_not_word_part_gap():
    from cemm.kernel.boot.v341 import register_v341_foundations
    from cemm.kernel.learning.coordinator import LearningCoordinator
    from cemm.kernel.model.gap import GapRecord
    from cemm.kernel.model.message import MessageContentItem, MessageRoleValue
    from cemm.kernel.schema.store import SemanticSchemaStore
    from cemm.language.en.adapter import EnglishLanguageAdapter

    store = SemanticSchemaStore()
    register_v341_foundations(store)
    coordinator = LearningCoordinator(store)
    gap = GapRecord(
        id="gap:president",
        gap_kind="missing_semantic_family",
        target_artifact_ref="opaque:en:president",
        missing_fields=("denotation_role_or_holder",),
        blocked_stage="ground",
        learnable=True,
    )
    coordinator.open_transaction(gap, context_ref="session:1")
    coordinator.register_probe_dispatch(
        context_ref="session:1",
        message_item=MessageContentItem(
            semantic_ref="learning_probe:gap:president",
            content_kind="learning_probe",
            provenance_refs=(gap.id,),
            role_values=(MessageRoleValue("gap_ref", semantic_ref=gap.id),),
        ),
        gaps=(gap,),
        output_event_ref="message:1",
    )
    evidence = EnglishLanguageAdapter(store).perceive("which part?", "en")
    resolution = coordinator.resolve_dialogue_turn(
        context_ref="session:1",
        selected_interpretations=(),
        surface_evidence=(evidence,),
    )
    assert resolution.resolution_kind == "meta_question"
    assert resolution.target_artifact_ref == "opaque:en:president"
    assert resolution.suppress_fresh_lexical_gaps


def test_end_to_end_public_runtime_is_canonical():
    from cemm.app.runtime import Runtime

    runtime = Runtime()
    result = runtime.run_text_result("hiii", context_id="session:test")
    assert result.output_text
    assert "finalize" in result.trace_stages
    assert "Got it" not in result.output_text


def test_social_status_question_does_not_open_learning_gap():
    from cemm.app.runtime import Runtime

    runtime = Runtime()
    cycle = runtime.run_text("how are you?", context_id="session:social")
    result = runtime.project(cycle)
    assert result.output_text
    assert result.realized_item_refs == ("self:capability_status",)
    assert result.blocked_item_refs == ()
    assert cycle.gaps == ()
    assert cycle.learning_transactions == ()
    assert cycle.capability_assessments
    assert cycle.selected_interpretations
    assert {
        item.predicate_semantic_key for item in cycle.selected_interpretations
    } == {"has_condition"}


def test_learning_progress_realizes_and_preserves_followup_obligation():
    from cemm.app.runtime import Runtime

    runtime = Runtime()
    runtime.run_text(
        "lol, well you're a glorp what did I expect lol",
        context_id="session:learn-machine",
    )
    cycle = runtime.run_text(
        "A glorp is something mechanical or digital like you",
        context_id="session:learn-machine",
    )
    result = runtime.project(cycle)
    assert result.output_text
    assert result.realized_item_refs == (
        "learning_progress:" + cycle.dialogue_resolution.transaction_ref,
    )
    assert result.blocked_item_refs == ()
    obligations = runtime.learning_coordinator.pending_obligations(
        "session:learn-machine"
    )
    assert obligations
    assert obligations[-1].unresolved_field_refs


def test_machine_is_seeded_as_ordinary_foundation_schema():
    from cemm.app.runtime import Runtime

    runtime = Runtime()
    assert runtime.schema_store.find_active("machine") is not None
    cycle = runtime.run_text(
        "lol, well you're a machine what did I expect lol",
        context_id="session:machine-seed",
    )
    assert cycle.gaps == ()
    definition = runtime.run_text(
        "A machine is something mechanical or digital like you",
        context_id="session:machine-seed",
    )
    assert definition.gaps == ()
    assert runtime.project(definition).realized_item_refs != (
        "response:no_admissible_content",
    )


def test_attributed_assertion_receives_qualified_receipt_not_abstention():
    from cemm.app.runtime import Runtime

    result = Runtime().run_text_result(
        "you are a machine",
        context_id="session:attributed-assertion",
    )
    assert result.output_text
    assert result.realized_item_refs != ("response:no_admissible_content",)
    assert result.output_text == "I received that information."


def test_name_offer_question_selects_interpretation():
    from cemm.app.runtime import Runtime

    cycle = Runtime().run_text(
        "anyway dont you want to know my name?",
        context_id="session:name-offer",
    )
    assert cycle.selected_interpretations
    assert cycle.gaps == ()
    assert Runtime().run_text_result(
        "anyway dont you want to know my name?",
        context_id="session:name-offer-output",
    ).output_text == "What is your name?"


def test_answer_capability_assessment_is_request_scoped():
    from cemm.app.runtime import Runtime

    runtime = Runtime()
    cycle = runtime.run_text("hiii", context_id="session:greeting-only")
    assert cycle.capability_assessments == ()


@pytest.mark.parametrize(
    "text,forbidden",
    [
        ("Do you know what a president is?", ("I know", "Got it")),
        ("arrghhh", ("Got it",)),
    ],
)
def test_critical_transcript_never_uses_unlicensed_acknowledgment(text, forbidden):
    from cemm.app.runtime import Runtime

    result = Runtime().run_text_result(text, context_id="session:critical")
    for phrase in forbidden:
        assert phrase not in result.output_text


def test_open_class_realizations_reference_active_semantic_schemas():
    from cemm.kernel.boot.v341 import register_v341_foundations
    from cemm.kernel.boot.v341_validation import validate_registered_v341, validate_v341_spec
    from cemm.kernel.schema.realization import RealizationSchema
    from cemm.kernel.schema.store import SemanticSchemaStore

    store = SemanticSchemaStore()
    validate_v341_spec().require_ok()
    register_v341_foundations(store)
    validate_registered_v341(store).require_ok()
    for envelope in store.records_by_kind("realization"):
        schema = envelope.payload
        if not isinstance(schema, RealizationSchema) or schema.closed_class:
            continue
        assert schema.semantic_schema_ref
        semantic = store.get(schema.semantic_schema_ref)
        assert semantic is not None
        assert semantic.status == "active"
        assert semantic.grounding_assessment_ref
        assert semantic.competence_assessment_ref


def test_learning_probe_contains_explicit_truth_bearing_clauses():
    from cemm.kernel.model.gap import GapRecord
    from cemm.kernel.response.planner import ContentSelectionInput, ResponsePlanner

    gap = GapRecord(
        id="gap:president",
        gap_kind="missing_semantic_family",
        target_artifact_ref="opaque:en:president",
        missing_fields=("semantic_family", "denotation_role_or_holder"),
        blocked_stage="ground",
        learnable=True,
    )
    plan = ResponsePlanner().plan_response(ContentSelectionInput(gaps=(gap,)))
    item = next(value for value in plan.content_items if value.content_kind == "learning_probe")
    clauses = {clause.predicate_key: clause for clause in item.clauses}
    assert set(clauses) == {"recognizes_form", "has_usable_definition", "means"}
    assert clauses["has_usable_definition"].polarity == "negative"
    assert clauses["means"].communicative_force == "ask"
    assert {role.role_key for role in clauses["recognizes_form"].role_values} == {
        "recognizer", "lexical_form"
    }


def test_critical_self_state_predicates_remain_distinct():
    from cemm.kernel.boot.v341 import semantic_specs

    predicates, _ = semantic_specs()
    keys = {
        "recognizes_form", "knows", "has_usable_definition", "stores",
        "has_access_to", "receives", "completes", "requires_information",
    }
    assert keys.issubset(predicates)
    assert len({predicates[key].semantic_key for key in keys}) == len(keys)
