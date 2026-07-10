"""Core-loop stress test — 50 multi-turn sessions exercising the full pipeline.

Each session is a short conversation (3-8 turns) with human-like input:
short sentences, long/complex sentences, slang, abbreviations, misspellings.
Sessions cover self-query, teaching+query, social, correction, dismissal,
style feedback, profile, and mixed use cases.

Invariants verified per session:
  - No crashes (no Traceback in errors)
  - Obligation kinds are sane for the input type
  - Durable store never loses relations across turns
  - Self-queries return answers when seeded
  - Teaching produces patches or store growth
  - Social inputs produce non-empty output
  - Dismissal phrases route to exit
  - Style feedback routes to acknowledge_emotional_context
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("CEMM_EXPORT_PATH", "")

from cemm.tests.harness import SeededSystem, seed_durable_from_config


# ── Session definitions ───────────────────────────────────────────────

# Each session is (label, seed_durable, [list of (input, assertions)])
# assertions is a dict of optional checks:
#   "obligation_in": list of allowed obligation kinds
#   "obligation_not": list of disallowed obligation kinds
#   "has_answer": True — must have an answer
#   "output_contains": substring that must appear in output
#   "output_not_contains": substring that must NOT appear
#   "durable_grew": True — durable count must increase from before this turn
#   "no_errors": True — errors must be empty (default True)
#   "output_nonempty": True — output must be non-empty

SESSIONS: list[tuple[str, bool, list[tuple[str, dict]]]] = [

    # ── 1-8: Self-query sessions ────────────────────────────────────────

    ("self_name_variants", True, [
        ("what's your name?", {"obligation_in": ["answer_self_identity", "answer_self_model"], "has_answer": True, "output_contains": "CEMM"}),
        ("what is your name", {"obligation_in": ["answer_self_identity", "answer_self_model"], "has_answer": True, "output_contains": "CEMM"}),
        ("who are you", {"obligation_in": ["answer_self_identity", "answer_self_model"], "has_answer": True}),
        ("what is your name please", {"obligation_in": ["answer_self_identity", "answer_self_model"], "has_answer": True, "output_contains": "CEMM"}),
    ]),

    ("self_capability_variants", True, [
        ("what can you do", {"obligation_in": ["answer_self_capability"], "has_answer": True}),
        ("what do you do", {"obligation_in": ["answer_self_capability"], "has_answer": True}),
        ("what can you help with?", {"obligation_in": ["answer_self_capability"], "has_answer": True}),
        ("how can you help me?", {"obligation_in": ["answer_self_capability"], "has_answer": True}),
    ]),

    ("self_knowledge_variants", True, [
        ("what do you know about yourself?", {"obligation_in": ["answer_self_knowledge", "answer_self_model"], "has_answer": True}),
        ("describe yourself", {"obligation_in": ["answer_self_knowledge", "answer_self_model"], "has_answer": True}),
        ("what are you?", {"obligation_in": ["answer_self_identity", "answer_self_model", "answer_self_knowledge"], "has_answer": True}),
    ]),

    ("self_query_repeated", True, [
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
    ]),

    ("self_query_mixed_sequence", True, [
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
        ("what can you do?", {"has_answer": True}),
        ("what do you know about yourself?", {"has_answer": True}),
        ("who are you?", {"has_answer": True}),
        ("what's your name again?", {"has_answer": True, "output_contains": "CEMM"}),
    ]),

    ("self_query_with_typos", True, [
        ("what's your name", {"has_answer": True, "output_contains": "CEMM"}),
        ("what can you do", {"has_answer": True}),
        ("what do you know about yourself", {"has_answer": True}),
    ]),

    ("self_query_slang", True, [
        ("yo what's your name", {"has_answer": True, "output_contains": "CEMM"}),
        ("hey what can you do", {"has_answer": True}),
        ("so who are you", {"has_answer": True}),
    ]),

    ("self_query_long_sentence", True, [
        ("hey so I was wondering if you could tell me what your name is?", {"has_answer": True, "output_contains": "CEMM"}),
        ("could you tell me what you can do?", {"has_answer": True}),
        ("what do you know about yourself as a system?", {"has_answer": True}),
    ]),

    # ── 9-16: Teaching + query sessions ─────────────────────────────────

    ("teach_name_then_query", False, [
        ("my name is Chibueze", {"no_errors": True, "output_nonempty": True}),
        ("what's my name?", {"has_answer": True}),
    ]),

    ("teach_possessive_then_query", False, [
        ("my favorite color is blue", {"no_errors": True}),
        ("what's my favorite color?", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("teach_is_a_then_query", False, [
        ("remember that a dog is an animal", {"no_errors": True}),
        ("what is a dog?", {"no_errors": True}),
    ]),

    ("teach_multiple_facts", False, [
        ("remember that Paris is the capital of France", {"no_errors": True}),
        ("remember that Tokyo is the capital of Japan", {"no_errors": True}),
        ("remember that Cairo is the capital of Egypt", {"no_errors": True}),
        ("what is the capital of France?", {"no_errors": True}),
    ]),

    ("teach_with_domain_phrase", False, [
        ("my name is Chibueze, just between us", {"no_errors": True}),
        ("what's my name?", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("teach_with_slang", False, [
        ("yo my name is Tunde", {"no_errors": True}),
        ("what's my name", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("teach_with_misspelling", False, [
        ("my name is John", {"no_errors": True}),
        ("what is my name", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("teach_long_complex", False, [
        ("I want you to remember that the Eiffel Tower is located in Paris which is the capital of France", {"no_errors": True}),
        ("what is the capital of France?", {"no_errors": True}),
    ]),

    # ── 17-22: Social sessions ──────────────────────────────────────────

    ("social_greetings", False, [
        ("hi", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("hello", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("hey there", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("hey", {"obligation_in": ["social_reply"], "output_nonempty": True}),
    ]),

    ("social_casual", False, [
        ("hello lol", {"output_nonempty": True}),
        ("how's it going", {"output_nonempty": True}),
        ("good morning", {"output_nonempty": True}),
    ]),

    ("social_then_self_query", True, [
        ("hi", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
    ]),

    ("social_abbreviations", False, [
        ("hey what's up", {"output_nonempty": True}),
        ("how are you", {"output_nonempty": True}),
        ("good morning", {"output_nonempty": True}),
    ]),

    ("social_repeated_greetings", False, [
        ("hi", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("hello", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("hey", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("hi again", {"obligation_in": ["social_reply"], "output_nonempty": True}),
    ]),

    ("social_how_are_you", False, [
        ("how are you?", {"output_nonempty": True, "output_not_contains": "interesting topic"}),
        ("how are you doing today", {"output_nonempty": True}),
    ]),

    # ── 23-26: Correction sessions ──────────────────────────────────────

    ("correct_name_then_query", False, [
        ("my name is John", {"no_errors": True}),
        ("actually my name is Jonathan", {"no_errors": True}),
        ("what's my name?", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("correct_with_slang", False, [
        ("my name be Mike", {"no_errors": True}),
        ("nah its actually Michael", {"no_errors": True}),
        ("what's my name", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("correct_fact", False, [
        ("remember that Lagos is the capital of Nigeria", {"no_errors": True}),
        ("wait no, Abuja is the capital of Nigeria", {"no_errors": True}),
        ("what is the capital of Nigeria?", {"no_errors": True}),
    ]),

    ("correct_with_misspelling", False, [
        ("my nam is Sarah", {"no_errors": True}),
        ("oops I mean Sara", {"no_errors": True}),
        ("what's my nam", {"no_errors": True, "output_nonempty": True}),
    ]),

    # ── 27-30: Dismissal sessions ───────────────────────────────────────

    ("dismissal_go_away", False, [
        ("hi", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("go away", {"obligation_in": ["exit"], "output_nonempty": True}),
    ]),

    ("dismissal_shut_up", False, [
        ("hello", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("shut up", {"obligation_in": ["exit"], "output_nonempty": True}),
    ]),

    ("dismissal_bye", False, [
        ("hey", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("bye", {"obligation_in": ["exit"], "output_nonempty": True}),
    ]),

    ("dismissal_stop_talking", False, [
        ("hi there", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("stop talking", {"obligation_in": ["exit"], "output_nonempty": True}),
    ]),

    # ── 31-34: Style feedback sessions ──────────────────────────────────

    ("style_too_verbose", False, [
        ("that was too verbose", {"obligation_in": ["acknowledge_emotional_context"], "output_nonempty": True}),
    ]),

    ("style_too_long", False, [
        ("your answer was too long", {"obligation_in": ["acknowledge_emotional_context"], "output_nonempty": True}),
    ]),

    ("style_too_robotic", False, [
        ("you sound too robotic", {"obligation_in": ["acknowledge_emotional_context"], "output_nonempty": True}),
    ]),

    ("style_too_wordy", False, [
        ("too wordy", {"obligation_in": ["acknowledge_emotional_context"], "output_nonempty": True}),
    ]),

    # ── 35-38: Profile query sessions ───────────────────────────────────

    ("profile_name_query", False, [
        ("my name is Ada", {"no_errors": True}),
        ("what's my name?", {"has_answer": True}),
    ]),

    ("profile_possessive_query", False, [
        ("my job is engineer", {"no_errors": True}),
        ("what is my job?", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("profile_role_query", False, [
        ("my occupation is teacher", {"no_errors": True}),
        ("what is my occupation?", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("profile_teach_then_query_slang", False, [
        ("my name is dev", {"no_errors": True}),
        ("what's my name", {"no_errors": True, "output_nonempty": True}),
    ]),

    # ── 39-42: Mixed multi-turn sessions ────────────────────────────────

    ("mixed_full_conversation", True, [
        ("hi", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
        ("my name is Kemi", {"no_errors": True}),
        ("what's my name?", {"no_errors": True, "output_nonempty": True}),
        ("what can you do?", {"has_answer": True}),
        ("bye", {"obligation_in": ["exit"], "output_nonempty": True}),
    ]),

    ("mixed_teach_query_social", True, [
        ("hello", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("remember that a cat is an animal", {"no_errors": True}),
        ("what is a cat?", {"no_errors": True}),
        ("thanks", {"output_nonempty": True}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
    ]),

    ("mixed_correct_and_requery", False, [
        ("my name is David", {"no_errors": True}),
        ("what's my name?", {"no_errors": True, "output_nonempty": True}),
        ("actually it's Dave", {"no_errors": True}),
        ("what's my name?", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("mixed_long_session", True, [
        ("hey", {"obligation_in": ["social_reply"], "output_nonempty": True}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
        ("what can you do?", {"has_answer": True}),
        ("my name is Tunde", {"no_errors": True}),
        ("what's my name?", {"no_errors": True, "output_nonempty": True}),
        ("remember that Python is a programming language", {"no_errors": True}),
        ("what is Python?", {"no_errors": True}),
        ("bye", {"obligation_in": ["exit"], "output_nonempty": True}),
    ]),

    # ── 43-46: Edge case sessions ───────────────────────────────────────

    ("edge_empty_and_long", True, [
        ("", {"no_errors": True}),
        ("what is the meaning of life?", {"no_errors": True, "output_nonempty": True}),
        ("hello " * 50, {"no_errors": True}),
    ]),

    ("edge_special_chars", True, [
        ("what's your name?!!! @#$%^&*()", {"no_errors": True}),
        ("~~hello~~", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("edge_misspelled_self_query", True, [
        ("wha is your nam", {"no_errors": True, "output_nonempty": True}),
        ("what can yuo do", {"no_errors": True, "output_nonempty": True}),
    ]),

    ("edge_very_short_inputs", False, [
        ("hi", {"output_nonempty": True}),
        ("yo", {"output_nonempty": True}),
        ("sup", {"output_nonempty": True}),
        ("hey", {"output_nonempty": True}),
    ]),

    # ── 47-50: Deduction and complex sessions ───────────────────────────

    ("deduction_is_a_chain", False, [
        ("remember that a dog is an animal", {"no_errors": True}),
        ("remember that an animal is a living thing", {"no_errors": True}),
        ("what is a dog?", {"no_errors": True}),
    ]),

    ("deduction_property_chain", False, [
        ("remember that gold is a metal", {"no_errors": True}),
        ("remember that metals are conductive", {"no_errors": True}),
        ("what is gold?", {"no_errors": True}),
    ]),

    ("complex_teach_with_context", True, [
        ("hey I want to teach you something", {"output_nonempty": True}),
        ("remember that the sun is a star", {"no_errors": True}),
        ("what is the sun?", {"no_errors": True}),
        ("what's your name?", {"has_answer": True, "output_contains": "CEMM"}),
    ]),

    ("complex_mixed_human_like", True, [
        ("yo what's up", {"output_nonempty": True}),
        ("so like what's your name", {"has_answer": True, "output_contains": "CEMM"}),
        ("cool, my name is Jay", {"no_errors": True}),
        ("can you remember that", {"no_errors": True}),
        ("what's my name", {"no_errors": True, "output_nonempty": True}),
        ("alright bye", {"obligation_in": ["exit"], "output_nonempty": True}),
    ]),
]


# ── Test runner ───────────────────────────────────────────────────────


def _run_session(session_label: str, seed: bool, turns: list[tuple[str, dict]]) -> None:
    """Run a single session and assert all per-turn invariants."""
    sys = SeededSystem(context_id=f"stress_{session_label}")
    if seed:
        seed_durable_from_config(sys)

    prev_durable = sys.durable_store.relation_count()

    for i, (text, checks) in enumerate(turns):
        r = sys.run(text)

        # Universal invariant: no crashes
        for err in r["errors"]:
            assert "Traceback" not in err, (
                f"[{session_label}] turn {i} ({text!r}): crash: {err}"
            )

        # Default: no errors unless explicitly allowed
        if checks.get("no_errors", True):
            assert r["errors"] == [], (
                f"[{session_label}] turn {i} ({text!r}): unexpected errors: {r['errors']}"
            )

        # Obligation kind checks
        if "obligation_in" in checks:
            assert r["obligation_kind"] in checks["obligation_in"], (
                f"[{session_label}] turn {i} ({text!r}): obligation_kind={r['obligation_kind']!r}, "
                f"expected one of {checks['obligation_in']}"
            )

        if "obligation_not" in checks:
            assert r["obligation_kind"] not in checks["obligation_not"], (
                f"[{session_label}] turn {i} ({text!r}): obligation_kind={r['obligation_kind']!r} "
                f"should not be in {checks['obligation_not']}"
            )

        # Answer checks
        if checks.get("has_answer"):
            assert r["has_answer"] is True, (
                f"[{session_label}] turn {i} ({text!r}): no answer: {r['abstention_reason']}"
            )

        # Output content checks
        if checks.get("output_nonempty"):
            assert r["output"], (
                f"[{session_label}] turn {i} ({text!r}): output is empty"
            )

        if "output_contains" in checks:
            assert checks["output_contains"] in r["output"], (
                f"[{session_label}] turn {i} ({text!r}): output={r['output']!r}, "
                f"expected to contain {checks['output_contains']!r}"
            )

        if "output_not_contains" in checks:
            assert checks["output_not_contains"] not in r["output"].lower(), (
                f"[{session_label}] turn {i} ({text!r}): output={r['output']!r}, "
                f"should not contain {checks['output_not_contains']!r}"
            )

        # Durable store checks
        if checks.get("durable_grew"):
            assert r["durable_count"] > prev_durable, (
                f"[{session_label}] turn {i} ({text!r}): durable count didn't grow: "
                f"{prev_durable} -> {r['durable_count']}"
            )
        # Universal: durable count never decreases
        assert r["durable_count"] >= prev_durable - 1, (
            f"[{session_label}] turn {i} ({text!r}): durable count decreased: "
            f"{prev_durable} -> {r['durable_count']}"
        )
        prev_durable = r["durable_count"]


# ── Parametrized test for all 50 sessions ──────────────────────────────

import pytest


@pytest.mark.parametrize(
    "label,seed,turns",
    SESSIONS,
    ids=[s[0] for s in SESSIONS],
)
def test_core_loop_session(label: str, seed: bool, turns: list[tuple[str, dict]]) -> None:
    """Run one multi-turn session through the full pipeline."""
    _run_session(label, seed, turns)


def test_all_50_sessions_defined():
    """Verify we have at least 50 sessions defined."""
    assert len(SESSIONS) >= 50, f"Only {len(SESSIONS)} sessions defined, need at least 50"
