"""Structural regression tests for CEMM 3.3 forbidden surface-text patterns.

These tests verify that AGENTS.md §5 forbidden patterns (raw-text string
matching, regex, surface-text routing in operational meaning, contracts,
query, safety, patch, response planning) are not present in the designated
kernel components.

For each component, the test asserts the absence of specific known violation
patterns. As fixes are applied, this file should be updated to assert the new
authoritative behavior.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from types import SimpleNamespace

from cemm.kernel import meaning_perceptor
from cemm.kernel import uol_metadata
from cemm.kernel.output_state_updater import _detect_question_type, OutputStateUpdater


class TestMeaningPerceptorAuthority:
    """MeaningPerceptor must not contain hardcoded English intent cue sets."""

    def test_no_hardcoded_answer_token_set(self):
        source = inspect.getsource(meaning_perceptor)
        assert 'token_set <= {"yes", "yeah", "yup", "no", "nah", "ok", "okay", "sure", "right"}' not in source
        assert "_ANSWER_TOKENS" not in source or "_ANSWER_TOKENS" not in source

    def test_no_dead_hardcoded_query_methods(self):
        source = inspect.getsource(meaning_perceptor)
        assert "def _is_capability_query" not in source
        assert "def _is_self_identity_query" not in source
        assert "def _is_self_knowledge_query" not in source

    def test_teaching_group_uses_data_driven_cue_set(self):
        source = inspect.getsource(meaning_perceptor.MeaningPerceptor._is_teaching_group)
        assert "_TEACHING_CUES" in source
        assert '{"means", "called", "refers", "equals"}' not in source

    def test_repair_group_uses_data_driven_cue_set(self):
        source = inspect.getsource(meaning_perceptor.MeaningPerceptor._is_repair_group)
        assert "cue_set(\"repair\")" in source
        assert '{"mean", "that"}' not in source
        assert '{"what", "mean"}' not in source

    def test_reflect_fallback_uses_frame_alias(self):
        source = inspect.getsource(meaning_perceptor.MeaningPerceptor._intent_key_for_group)
        assert 'frame_alias_set("command_reflect")' in source
        assert '{"reflect", "reflect_on", "introspect", "self_reflect"}' not in source


class TestUOLMetadataAcknowledgment:
    """uol_metadata must expose acknowledgment tokens from JSON, not hardcoded."""

    def test_pure_acknowledgment_set_is_data_driven(self):
        acks = uol_metadata.pure_acknowledgment_set()
        assert "ok" in acks
        assert "okay" in acks
        assert "yes" in acks
        assert "yeah" in acks

    def test_answer_tokens_include_negative_acknowledgments(self):
        acks = meaning_perceptor._ACK_TOKENS
        assert "ok" in acks
        assert "yes" in acks
        assert "no" in acks or "nope" in acks or "nah" in acks

    def test_teaching_cue_contains_teach(self):
        cues = uol_metadata.cue_set("teaching_cue")
        assert "teach" in cues
        assert "means" in cues
        assert "called" in cues


class TestOutputStateUpdaterAuthority:
    """OutputStateUpdater must not regex-parse generated English output text."""

    def test_no_regex_question_patterns(self):
        source = Path("cemm/kernel/output_state_updater.py").read_text(encoding="utf-8")
        assert "_QUESTION_PATTERNS" not in source
        assert "re.findall" not in source
        assert "re.search" not in source

    def test_detect_question_from_response_mode_and_moves(self):
        # Social phatic check-in (e.g. "How are you doing?")
        bundle = SimpleNamespace(moves=[SimpleNamespace(move_type="phatic_response")])
        assert _detect_question_type("social", bundle, None) == ("social_checkin", "social_status")

        # Clarification question
        qc = SimpleNamespace(query_kind="clarification")
        assert _detect_question_type("clarify", None, qc) == ("idiom_confirmation", "yes_no_or_definition")

        # Preference question
        qc = SimpleNamespace(query_kind="profile_dimension")
        assert _detect_question_type("clarify", None, qc) == ("preference_query", "preference")

        # General clarification
        assert _detect_question_type("clarify", None, None) == ("general_question", "free_form")

        # Confirmation write
        assert _detect_question_type("confirm_write", None, None) == ("yes_no", "yes_no")

        # Non-question outputs
        assert _detect_question_type("answer", None, None) == ("", "")
        assert _detect_question_type("acknowledge", None, None) == ("", "")

    def test_update_uses_semantic_contracts(self):
        updater = OutputStateUpdater()
        kernel = SimpleNamespace()
        bundle = SimpleNamespace(moves=[SimpleNamespace(move_type="phatic_response")])
        contract = SimpleNamespace(query_contract=SimpleNamespace(query_kind="clarification"))
        update = updater.update(
            kernel,
            output_text="How are you doing?",
            response_mode="social",
            obligation_contract=contract,
            response_bundle=bundle,
        )
        assert update.pending_assistant_question == "social_checkin"
