"""Tests for the SafeRealizer safety channel.

Verifies that SafeRealizer:
- Realizes ONLY reviewed failure meanings (unknown, ambiguous, denied,
  operation_failed, realization_failed)
- Raises UnsafeFallbackError for normal answer meanings
- Produces "safe" status receipts
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
    NeuralConstrainedRealizer,
    RealizationReceipt,
    RealizationVerifier,
    SafeRealizer,
    UnsafeFallbackError,
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
        "application:safe-realizer-test",
        "op:designation",
        "entity:cemm",
        (RoleBinding("role:target", GroundedReference("entity:cemm")),),
    )
    expression = SemanticExpression.create(
        applications=(application,), root_refs=(application.application_ref,)
    )
    return ResponseMeaning.create(
        decision_ref="decision:safe-realizer-test",
        verified_meaning_ref="meaning:safe-realizer-test",
        source_expression_ref=expression.expression_ref,
        response_expression=expression,
        situation_ref="situation:safe-realizer-test",
        effect_outcome_ref="no_effect:safe-realizer-test",
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
        policy_refs=("policy:safe-realizer-test",),
        permitted_omissions=(),
        revision_pin=RevisionPin(
            "authority:test", 0, 0, 0, 0, "model:test"
        ),
    )


def failure_meaning(status: str) -> ResponseMeaning:
    """Create a failure ResponseMeaning for the given status."""
    polarity_ref = "polarity:negative" if status in ("denied", "operation_failed", "realization_failed") else "polarity:positive"
    epistemic_status_ref = "epistemic_status:denied" if status == "denied" else "epistemic_status:unknown"
    mode = SemanticMode.REQUEST if status in ("denied", "operation_failed") else SemanticMode.QUERY
    cycle_status = {
        "unknown": CycleStatus.UNKNOWN,
        "ambiguous": CycleStatus.AMBIGUOUS,
        "denied": CycleStatus.DENIED,
        "operation_failed": CycleStatus.OPERATION_FAILED,
        "realization_failed": CycleStatus.REALIZATION_FAILED,
    }[status]
    return _make_response_meaning(
        discourse_action=status,
        polarity_ref=polarity_ref,
        epistemic_status_ref=epistemic_status_ref,
        cycle_status=cycle_status,
        mode=mode,
    )


def normal_answer_meaning() -> ResponseMeaning:
    """Create a normal answer ResponseMeaning."""
    return _make_response_meaning(
        discourse_action="answer",
        polarity_ref="polarity:positive",
        epistemic_status_ref="epistemic_status:supported",
        cycle_status=CycleStatus.RESOLVED,
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
def safe_realizer():
    """A SafeRealizer for testing."""
    return SafeRealizer(RealizationVerifier())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanonicalSafeRealizer:
    def test_safe_realizer_rejects_duck_typed_response_meaning(self, safe_realizer):
        with pytest.raises(TypeError, match="exact canonical ResponseMeaning"):
            safe_realizer.realize(_DuckResponseMeaning(failure_meaning("unknown")))

    def test_safe_realizer_rejects_forged_exact_type_response_meaning(
        self, safe_realizer
    ):
        with pytest.raises(ValueError, match="canonical ResponseMeaning"):
            safe_realizer.realize(_forged_response_meaning(failure_meaning("unknown")))

    def test_neural_realizer_rejects_duck_typed_response_meaning(self):
        realizer = NeuralConstrainedRealizer(
            network=object(),
            metadata=object(),
            verifier=RealizationVerifier(),
        )
        with pytest.raises(TypeError, match="exact canonical ResponseMeaning"):
            realizer.realize(_DuckResponseMeaning(normal_answer_meaning()))

    def test_neural_realizer_rejects_forged_exact_type_response_meaning(self):
        realizer = NeuralConstrainedRealizer(
            network=object(),
            metadata=object(),
            verifier=RealizationVerifier(),
        )
        with pytest.raises(ValueError, match="canonical ResponseMeaning"):
            realizer.realize(_forged_response_meaning(normal_answer_meaning()))

    @pytest.mark.parametrize(
        "status",
        ["unknown", "ambiguous", "denied", "operation_failed", "realization_failed"],
        ids=["unknown", "ambiguous", "denied", "operation_failed", "realization_failed"],
    )
    def test_safe_realizer_is_limited_to_failure_actions(
        self, safe_realizer, status
    ):
        """SafeRealizer realizes failure meanings with status 'safe'."""
        receipt = safe_realizer.realize(failure_meaning(status))
        assert receipt.status == "safe"
        assert receipt.surface is not None
        assert receipt.model_identity is None

    def test_safe_realizer_rejects_normal_answer(self, safe_realizer):
        """SafeRealizer raises UnsafeFallbackError for normal answers."""
        with pytest.raises(UnsafeFallbackError):
            safe_realizer.realize(normal_answer_meaning())

    def test_safe_realizer_rejects_acknowledge(self, safe_realizer):
        """SafeRealizer raises UnsafeFallbackError for acknowledge actions."""
        rm = _make_response_meaning(discourse_action="acknowledge")
        with pytest.raises(UnsafeFallbackError):
            safe_realizer.realize(rm)

    def test_safe_realizer_receipt_is_frozen(self, safe_realizer):
        """SafeRealizer receipts are frozen."""
        receipt = safe_realizer.realize(failure_meaning("unknown"))
        with pytest.raises((AttributeError, Exception)):
            receipt.status = "realized"

    def test_safe_realizer_has_equivalence_receipt(self, safe_realizer):
        """SafeRealizer receipts carry equivalence receipts."""
        receipt = safe_realizer.realize(failure_meaning("unknown"))
        assert receipt.equivalence_receipt is not None
        assert receipt.equivalence_receipt.equivalent


__cemm_test_inventory__ = {
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_rejects_duck_typed_response_meaning": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "a38783bcff14abd037707ca11aeef1e60306ea69432bcff24a99e635b271202d",
        "assertion_ref": "assertion:r4-sr3-safe-realizer-rejects-duck-response-meaning",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_rejects_forged_exact_type_response_meaning": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "f8793838521fb2809e2ef2ea9c1d82d702bdf12f672c831e06fe62b3749e908a",
        "assertion_ref": "assertion:r4-sr3-safe-realizer-rejects-forged-response-meaning",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_neural_realizer_rejects_duck_typed_response_meaning": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "c89d9ee7c46b45a4813fe7d21386fecf23d89cf1f1bd2768e94bc5534ebe7b15",
        "assertion_ref": "assertion:r4-sr3-neural-realizer-rejects-duck-response-meaning",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_neural_realizer_rejects_forged_exact_type_response_meaning": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "1e6f498c803cee10fd4727332bf164de630b5cbf0c4ed1db2b59690911b804e9",
        "assertion_ref": "assertion:r4-sr3-neural-realizer-rejects-forged-response-meaning",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[unknown]": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "3335b2e349800a2c2a72e502c91e8c4403dba198f45e56a982a3a30d5b9363ba",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-is-limited-to-failure-actions",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[unknown]",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[ambiguous]": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "3335b2e349800a2c2a72e502c91e8c4403dba198f45e56a982a3a30d5b9363ba",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-is-limited-to-failure-actions",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[ambiguous]",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[denied]": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "3335b2e349800a2c2a72e502c91e8c4403dba198f45e56a982a3a30d5b9363ba",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-is-limited-to-failure-actions",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[denied]",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[operation_failed]": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "3335b2e349800a2c2a72e502c91e8c4403dba198f45e56a982a3a30d5b9363ba",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-is-limited-to-failure-actions",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[operation_failed]",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[realization_failed]": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "3335b2e349800a2c2a72e502c91e8c4403dba198f45e56a982a3a30d5b9363ba",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-is-limited-to-failure-actions",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_is_limited_to_failure_actions[realization_failed]",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_rejects_normal_answer": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "3185a5276264939b4466c61510c1f31440ad1f100db4e7429eb4125bf35b6c2f",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-rejects-normal-answer",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_rejects_normal_answer",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_rejects_acknowledge": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "c97ff3fc13fa2fa2b08d69cc5cc841d4841165cf49080db6eb8ec9be199d8d2e",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-rejects-acknowledge",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_rejects_acknowledge",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_receipt_is_frozen": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "2bfc53f6038cb7be243fdf1a25122342f8fdbe57849a91c6624015d5a75fb2de",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-receipt-is-frozen",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_receipt_is_frozen",
    },
    "tests/test_safe_realizer.py::TestCanonicalSafeRealizer::test_safe_realizer_has_equivalence_receipt": {
        "activation_phase": "R3", "diagnostic_role": "owner", "introduced_by_task": "R4.1-Source-Readiness-SR3", "owner_ref": "learning-response", "source_ast_sha256": "122a03ddb67e4c5ded21889300902893efe976a9fafe31d509631ccd9e396d81",
        "assertion_ref": "assertion:safe-realizer-test-safe-realizer-safe-realizer-has-equivalence-receipt",
        "supersedes_node_id": "tests/test_safe_realizer.py::TestSafeRealizer::test_safe_realizer_has_equivalence_receipt",
    },
}
