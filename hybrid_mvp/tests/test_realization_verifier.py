"""Tests for the independent realization equivalence verifier.

Verifies that the RealizationVerifier:
- Rejects flipped polarity with mismatch_codes == ("polarity",)
- Accepts correct surfaces
- Rejects internal semantic refs in surface
- Rejects empty output for authorized response actions
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.cycle import CycleStatus, SemanticMode
from cemm_authoritative_hybrid.expressions import (
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r3_response import ResponseMeaning
from cemm_authoritative_hybrid.realization import (
    EquivalenceReceipt,
    RealizationVerifier,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response_meaning(
    *,
    discourse_action="answer",
    polarity_ref="polarity:positive",
    modality_ref="modality:actual",
    epistemic_status_ref="epistemic_status:supported",
    cycle_status=CycleStatus.RESOLVED,
    mode=SemanticMode.QUERY,
) -> ResponseMeaning:
    """Create the canonical Response Meaning ABI 2 value used by REALIZE."""
    application = SemanticApplication(
        "application:realization-test",
        "op:designation",
        "entity:cemm",
        (RoleBinding("role:target", GroundedReference("entity:cemm")),),
    )
    expression = SemanticExpression.create(
        applications=(application,), root_refs=(application.application_ref,)
    )
    return ResponseMeaning.create(
        decision_ref="decision:realization-test",
        verified_meaning_ref="meaning:realization-test",
        source_expression_ref=expression.expression_ref,
        response_expression=expression,
        situation_ref="situation:realization-test",
        effect_outcome_ref="no_effect:realization-test",
        learning_plan_ref=None,
        obligation_ref=None,
        mode=mode,
        cycle_status=cycle_status,
        discourse_action=discourse_action,
        bindings=(("participant:system", "entity:cemm"),),
        polarity_ref=polarity_ref,
        modality_ref=modality_ref,
        epistemic_status_ref=epistemic_status_ref,
        source_refs=("participant:system",),
        proof_refs=("effect:proof",),
        blocker_refs=(),
        policy_refs=("policy:realization-test",),
        permitted_omissions=(),
        revision_pin=RevisionPin(
            "authority:test", 0, 0, 0, 0, "model:test"
        ),
    )


class _DuckResponseMeaning:
    def __init__(self, value: ResponseMeaning) -> None:
        self._value = value

    def __getattr__(self, name: str):
        return getattr(self._value, name)


def _forged_response_meaning(value: ResponseMeaning) -> ResponseMeaning:
    forged = object.__new__(ResponseMeaning)
    for name, item in value.__dict__.items():
        object.__setattr__(forged, name, item)
    object.__setattr__(forged, "response_meaning_ref", "response_meaning:forged")
    return forged


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def realization_verifier():
    """A RealizationVerifier for testing."""
    return RealizationVerifier()


@pytest.fixture
def supported_answer():
    """A ResponseMeaning for a supported positive answer."""
    return _make_response_meaning(
        discourse_action="answer",
        polarity_ref="polarity:positive",
        epistemic_status_ref="epistemic_status:supported",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanonicalRealizationVerifier:
    def test_duck_typed_response_meaning_is_rejected(
        self, realization_verifier, supported_answer
    ):
        with pytest.raises(TypeError, match="exact canonical ResponseMeaning"):
            realization_verifier.verify(
                _DuckResponseMeaning(supported_answer), "My name is CEMM."
            )

    def test_forged_exact_type_response_meaning_is_rejected(
        self, realization_verifier, supported_answer
    ):
        with pytest.raises(ValueError, match="canonical ResponseMeaning"):
            realization_verifier.verify(
                _forged_response_meaning(supported_answer), "My name is CEMM."
            )

    def test_flipped_polarity_is_rejected(self, realization_verifier, supported_answer):
        """A negative surface for a positive response contract is rejected."""
        result = realization_verifier.verify(
            supported_answer, "No, that is not supported."
        )
        assert not result.equivalent
        assert result.mismatch_codes == ("polarity",)

    def test_correct_positive_answer_is_accepted(self, realization_verifier, supported_answer):
        """A correct positive surface passes verification."""
        result = realization_verifier.verify(supported_answer, "My name is CEMM.")
        assert result.equivalent
        assert result.mismatch_codes == ()

    def test_internal_refs_are_rejected(self, realization_verifier, supported_answer):
        """Internal semantic refs in surface are rejected."""
        result = realization_verifier.verify(
            supported_answer, "My name is concept:system."
        )
        assert not result.equivalent
        assert "internal_refs" in result.mismatch_codes

    def test_empty_output_is_rejected_for_answer(self, realization_verifier, supported_answer):
        """Empty output is rejected for authorized response actions."""
        result = realization_verifier.verify(supported_answer, "")
        assert not result.equivalent
        assert "empty_output" in result.mismatch_codes

    def test_negative_answer_is_accepted(self, realization_verifier):
        """A negative surface for a negative response contract is accepted."""
        rm = _make_response_meaning(
            discourse_action="answer",
            polarity_ref="polarity:negative",
            epistemic_status_ref="epistemic_status:supported",
        )
        result = realization_verifier.verify(rm, "No, that is not supported.")
        assert result.equivalent

    def test_unknown_discourse_action_matches(self, realization_verifier):
        """Unknown discourse action requires unknown surface markers."""
        rm = _make_response_meaning(
            discourse_action="unknown",
            epistemic_status_ref="epistemic_status:unknown",
            cycle_status=CycleStatus.UNKNOWN,
        )
        result = realization_verifier.verify(rm, "I do not know.")
        assert result.equivalent

    def test_deny_discourse_action_matches(self, realization_verifier):
        """Deny discourse action requires denial surface markers."""
        rm = _make_response_meaning(
            discourse_action="deny",
            polarity_ref="polarity:negative",
            epistemic_status_ref="epistemic_status:denied",
            cycle_status=CycleStatus.DENIED,
            mode=SemanticMode.REQUEST,
        )
        result = realization_verifier.verify(rm, "That is not permitted.")
        assert result.equivalent

    def test_equivalence_receipt_is_frozen(self):
        """EquivalenceReceipt is a frozen dataclass."""
        receipt = EquivalenceReceipt(equivalent=True, mismatch_codes=())
        with pytest.raises((AttributeError, Exception)):
            receipt.equivalent = False


__cemm_test_inventory__ = {
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_duck_typed_response_meaning_is_rejected": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "e8aca89bd52512b9f8a7e9b7f092cca9272ba14807ec075bd4376c23937e561a",
        "assertion_ref": "assertion:r4-sr3-realization-verifier-rejects-duck-response-meaning",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_forged_exact_type_response_meaning_is_rejected": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "07f4447d85b1f6fd3a99f3177a8a0f902beb1f808b5497252d7ada5f954ec57b",
        "assertion_ref": "assertion:r4-sr3-realization-verifier-rejects-forged-response-meaning",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_flipped_polarity_is_rejected": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "953c8fa6beaaf26e88e799cd306adc2515d5951ccaf1ded81ef0b319f2b0de22",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-flipped-polarity-is-rejected",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_flipped_polarity_is_rejected",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_correct_positive_answer_is_accepted": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "99782131fd093fe289d756940be9b854c2c7d989f659516b6001d1e2a2c1d0dc",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-correct-positive-answer-is-accepted",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_correct_positive_answer_is_accepted",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_internal_refs_are_rejected": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "2a544e852a3e491f420e6cb90cbcd50046ff88e8875dc1b2022b0b3acab96e1a",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-internal-refs-are-rejected",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_internal_refs_are_rejected",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_empty_output_is_rejected_for_answer": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "854f98dcc297d76beb1d9fed9153fcd5b4eff4ca1b33a9cd38198eea681d9e40",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-empty-output-is-rejected-for-answer",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_empty_output_is_rejected_for_answer",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_negative_answer_is_accepted": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "0dd1e836608730469ad1c8847534f4c34219993a0a47f175e63d4a3abb326f1c",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-negative-answer-is-accepted",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_negative_answer_is_accepted",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_unknown_discourse_action_matches": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "5e1c7edb9e77b5f0246e25db1fa55ed3decc0d4f3034cd508c8c7a452909e998",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-unknown-discourse-action-matches",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_unknown_discourse_action_matches",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_deny_discourse_action_matches": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "1da11574f47c9c91ccbdff8eb1776e25c35c109c61b4d72c3de2c889a39799a8",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-deny-discourse-action-matches",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_deny_discourse_action_matches",
    },
    "tests/test_realization_verifier.py::TestCanonicalRealizationVerifier::test_equivalence_receipt_is_frozen": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "233b826cf766c611e92a40e1d21c315f83f6c42fd5e4f1c5aeb3084e46df87a8",
        "assertion_ref": "assertion:realization-verifier-test-realization-verifier-equivalence-receipt-is-frozen",
        "supersedes_node_id": "tests/test_realization_verifier.py::TestRealizationVerifier::test_equivalence_receipt_is_frozen",
    },
}
