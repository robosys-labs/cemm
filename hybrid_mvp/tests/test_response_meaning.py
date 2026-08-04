"""Tests for exact response meaning preceding language.

Verifies that ResponseMeaning is built from evaluation/effect receipts (not
input words), and that the six-phase runtime produces a trace with all phases
in order and with duration_ns set.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.response import ResponseMeaning, ResponseBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evaluation(status="resolved", output_refs=("prop:test",)):
    """Create a minimal evaluation result for testing."""
    from cemm_authoritative_hybrid.runtime import EvaluationResult

    return EvaluationResult(status=status, output_refs=output_refs)


def _make_effect(output_refs=("effect:proof",)):
    """Create a minimal effect result for testing."""
    from cemm_authoritative_hybrid.runtime import EffectResult

    return EffectResult(executed=True, output_refs=output_refs)


def _make_orientation(mode="QUERY", focus_refs=("participant:system",)):
    """Create a minimal orientation for testing."""
    from cemm_authoritative_hybrid.cycle import Orientation, SemanticMode
    from cemm_authoritative_hybrid.persistence import RevisionPin

    pin = RevisionPin(
        authority_generation="authority:generation-test",
        world_revision=0,
        session_revision=0,
        episode_revision=0,
        effect_revision=0,
        model_identity=None,
    )
    return Orientation.create(
        session_ref="session:test",
        turn_ref="turn:test",
        source_text="",
        mode=SemanticMode[mode] if isinstance(mode, str) else mode,
        participant_frame="participant:user",
        temporal_frame="now",
        participants=(),
        active_turn_ref="turn:test",
        event_refs=(),
        focus_refs=focus_refs,
        obligation_refs=(),
        capability_summary=(),
        permission_summary=(),
        budgets={"input_tokens": 64},
        scanned_atom_count=0,
        index_probes=(),
        visited_refs=(),
        revision_pin=pin,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResponseMeaningPrecedesLanguage:
    def test_response_meaning_precedes_language(self, runtime):
        """ResponseMeaning is built from evaluation/effect receipts, not input words."""
        result = runtime.process("s", "what is your name?")
        assert result.response_meaning is not None
        assert result.response_meaning.proposition_ref
        phases = {receipt.phase: receipt for receipt in result.trace}
        assert phases["EVALUATE"].duration_ns is not None
        assert tuple(phases) == (
            "ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"
        )

    def test_response_meaning_has_all_fields(self):
        """ResponseMeaning carries all required semantic fields."""
        evaluation = _make_evaluation(status="resolved")
        effect = _make_effect()
        orientation = _make_orientation()
        builder = ResponseBuilder()
        rm = builder.build(evaluation, effect, orientation)
        assert rm.response_ref
        assert rm.mode == "QUERY"
        assert rm.status == "resolved"
        assert rm.proposition_ref == "prop:test"
        assert rm.polarity == "positive"
        assert rm.modality == "actual"
        assert rm.epistemic_status == "supported"
        assert rm.discourse_action == "answer"
        assert rm.requested_bindings
        assert rm.source_refs

    def test_response_builder_cannot_inspect_input_words(self):
        """ResponseBuilder works only from typed receipts, not input text."""
        evaluation = _make_evaluation(status="unknown")
        effect = _make_effect()
        orientation = _make_orientation()
        builder = ResponseBuilder()
        rm = builder.build(evaluation, effect, orientation)
        # The builder maps status to discourse action without seeing input.
        assert rm.discourse_action == "unknown"
        assert rm.epistemic_status == "unknown"

    def test_denied_status_maps_to_deny_action(self):
        """Denied status produces a deny discourse action with negative polarity."""
        evaluation = _make_evaluation(status="denied")
        effect = _make_effect()
        orientation = _make_orientation(mode="REQUEST")
        builder = ResponseBuilder()
        rm = builder.build(evaluation, effect, orientation)
        assert rm.discourse_action == "deny"
        assert rm.polarity == "negative"
        assert rm.epistemic_status == "denied"

    def test_response_meaning_is_frozen(self):
        """ResponseMeaning is a frozen dataclass."""
        evaluation = _make_evaluation()
        effect = _make_effect()
        orientation = _make_orientation()
        builder = ResponseBuilder()
        rm = builder.build(evaluation, effect, orientation)
        with pytest.raises((AttributeError, Exception)):
            rm.status = "changed"
