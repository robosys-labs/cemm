"""Language-agnostic invariants for operational decode gating."""

from __future__ import annotations

import inspect
from pathlib import Path

from cemm.kernel import operational_meaning_compiler


def test_operational_decode_gate_has_no_local_language_word_table():
    source = inspect.getsource(operational_meaning_compiler.OperationalMeaningCompiler)

    assert "_FUNCTION_WORDS" not in source
    assert "_is_question_like_surface" not in source


def test_operational_decode_gate_does_not_special_case_unknown_operator_surface():
    source = inspect.getsource(operational_meaning_compiler.OperationalMeaningCompiler)

    assert '"else"' not in source
    assert "'else'" not in source
    assert "what else can you do" not in source


def test_operational_compiler_does_not_classify_from_surface_text():
    source = inspect.getsource(operational_meaning_compiler.OperationalMeaningCompiler)

    forbidden_fragments = [
        "_looks_like_",
        "_infer_profile_dimension",
        "_infer_affect",
        "_infer_style_dimension",
        "_is_assistant_directed_criticism",
        "group.surface",
        "re.findall",
        "re.search",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_fallback_obligation_scheduler_does_not_route_from_surface_text():
    source = Path("cemm/kernel/semantic_obligation_scheduler.py").read_text(encoding="utf-8")

    forbidden_fragments = [
        "_STYLE_FEEDBACK_SURFACES",
        "profile_keywords",
        "surface_lower",
        "entry.surface.lower",
        "marker in surface",
        "kw in surface",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_legacy_query_builder_does_not_switch_profile_relation_from_surface_keywords():
    source = Path("cemm/kernel/semantic_query_engine.py").read_text(encoding="utf-8")

    forbidden_fragments = [
        "surface_lower",
        '"job" in',
        '"occupation" in',
        '"work" in',
        '"title" in',
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_runtime_does_not_fallback_to_legacy_obligation_scheduler():
    source = Path("cemm/kernel/semantic_kernel_runtime.py").read_text(encoding="utf-8")

    assert "_obligation_scheduler.schedule" not in source
    assert "schedule obligation fallback" not in source


def test_query_engine_does_not_match_queries_from_surface_tokens():
    source = Path("cemm/kernel/semantic_query_engine.py").read_text(encoding="utf-8")

    forbidden_fragments = [
        "_match_frames_by_surface",
        "_select_best_frame",
        "question_surface",
        "entry_surface",
        "token_re",
        "Surface-based fallback",
        "surface token",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_runtime_safety_detection_does_not_use_raw_input_text():
    source = Path("cemm/kernel/semantic_kernel_runtime.py").read_text(encoding="utf-8")
    detector_source = Path("cemm/kernel/safety_frame_detector.py").read_text(encoding="utf-8")

    assert "input_text=getattr(signal, 'content', '')" not in source
    assert "input_text" not in detector_source


def test_32_runtime_does_not_import_legacy_surface_classifiers():
    runtime_source = Path("cemm/kernel/semantic_kernel_runtime.py").read_text(encoding="utf-8")
    cpu_source = Path("cemm/kernel/semantic_cpu.py").read_text(encoding="utf-8")
    combined = runtime_source + "\n" + cpu_source

    forbidden_fragments = [
        "conversation_act_classifier",
        "ConversationActClassifier",
        "capability_classifier",
        "CapabilityClassifier",
        "teaching_interpreter",
        "TeachingInterpreter",
        "EntityFactExtractor",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in combined
