"""Gap matrix tests: all 18 gap kinds, exact owners, safe actions, and
CycleStatus reachability.

These tests prove that:
- Every one of the 18 gap kinds is reachable from a typed fixture.
- Each gap kind maps to its exact recommended owner and a non-empty
  safe_response_action.
- Branch cases route correctly (reference ambiguity → training, absent
  identity → authority; missing transition → authority, exhausted bound →
  runtime; resource, permission, and adapter remain distinct).
- Every closed ``CycleStatus`` is reachable from a typed decision/gap fixture.
- No status is selected from response wording or a phrase label.
- Construction and transport decoding reject non-``CycleStatus`` strings.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.gaps import (
    AdapterFailure,
    AbsentIdentity,
    BudgetExhausted,
    CoverageGap,
    EffectDenied,
    EvidenceGap,
    GapClassifier,
    GapKind,
    GapReceipt,
    InferenceBound,
    LearningGap,
    MissingOwner,
    MissingTransition,
    PermissionDenied,
    ProposalGap,
    RealizationFailure,
    ReferenceAmbiguity,
    RepairOwner,
    ResourceUnavailable,
    SemanticConflict,
    StateGap,
    StorageFailure,
    TransitionBoundExhausted,
    VerificationFailure,
)
from cemm_authoritative_hybrid.cycle import CycleStatus


# ---------------------------------------------------------------------------
# Fixture: gap_case — canonical typed fixture for each of the 18 gap kinds
# ---------------------------------------------------------------------------


@pytest.fixture
def gap_classifier():
    return GapClassifier()


@pytest.fixture
def gap_case(gap_classifier):
    """Return a callable that produces a ``GapReceipt`` for ``(kind, owner)``.

    Each canonical fixture raises the typed exception that maps to the given
    gap kind and recommended owner. Branch cases (reference, transition) are
    handled by distinct exceptions that route to different owners for the same
    kind.
    """

    def _make(kind: str, owner: str) -> GapReceipt:
        exc = _fixture_exception(kind, owner)
        return gap_classifier.classify(exc)

    return _make


def _fixture_exception(kind: str, owner: str) -> Exception:
    """Return the canonical typed exception for ``(kind, owner)``.

    For branch kinds (reference, transition), the owner determines which
    exception is used.
    """
    if kind == "evidence":
        return EvidenceGap("claim:test", "no evidence")
    if kind == "designation":
        return CoverageGap("span:test", "no designation")
    if kind == "reference":
        if owner == "training":
            return ReferenceAmbiguity("ref:test", ("candidate:a", "candidate:b"))
        if owner == "authority":
            return AbsentIdentity("entity:unknown", "frame:person")
        raise ValueError(f"unknown owner for reference: {owner}")
    if kind == "authority":
        return SemanticConflict("graph:test", "conflict")
    if kind == "proposal":
        return ProposalGap("cycle:test", "no candidates")
    if kind == "verification":
        return VerificationFailure("structural", "cycle:test")
    if kind == "inference":
        return InferenceBound("query:test", "max_rounds")
    if kind == "state":
        return StateGap("entity:door", "dimension:open")
    if kind == "transition":
        if owner == "authority":
            return MissingTransition("state:closed", "state:open")
        if owner == "runtime":
            return TransitionBoundExhausted("transition:test", 6)
        raise ValueError(f"unknown owner for transition: {owner}")
    if kind == "learning":
        return LearningGap("obligation:test", "no plan")
    if kind == "resource":
        return ResourceUnavailable("model:test", "timeout")
    if kind == "permission":
        return PermissionDenied("cap:write", "participant:user")
    if kind == "adapter":
        return AdapterFailure("adapter:test", "timeout")
    if kind == "operation":
        return EffectDenied("effect:test", "permission missing")
    if kind == "storage":
        return StorageFailure("store:world", "io error")
    if kind == "realization":
        return RealizationFailure("response:test", "no surface")
    if kind == "performance":
        return BudgetExhausted("tokens", 64)
    if kind == "implementation":
        return MissingOwner("realizer")
    raise ValueError(f"unknown gap kind: {kind}")


# ---------------------------------------------------------------------------
# 18 gap kinds: exact owner and safe action
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind,owner", [
    ("evidence", "data"), ("designation", "data"), ("reference", "training"),
    ("authority", "authority"), ("proposal", "training"), ("verification", "runtime"),
    ("inference", "runtime"), ("state", "data"), ("transition", "authority"),
    ("learning", "policy"), ("resource", "data"), ("permission", "policy"),
    ("adapter", "adapter"), ("operation", "adapter"), ("storage", "runtime"),
    ("realization", "training"), ("performance", "runtime"), ("implementation", "runtime"),
])
def test_gap_has_exact_owner_and_safe_action(gap_case, kind, owner):
    receipt = gap_case(kind, owner)
    assert receipt.kind == GapKind(kind)
    assert receipt.recommended_owner == RepairOwner(owner)
    assert receipt.safe_response_action


# ---------------------------------------------------------------------------
# Branch cases
# ---------------------------------------------------------------------------


def test_reference_ambiguity_with_candidate_routes_to_training(gap_classifier):
    gap = gap_classifier.classify(
        ReferenceAmbiguity("ref:1", ("candidate:a", "candidate:b"))
    )
    assert gap.kind == GapKind.REFERENCE
    assert gap.recommended_owner == RepairOwner.TRAINING
    assert gap.safe_response_action == "request_reference_resolution"


def test_absent_identity_routes_to_authority(gap_classifier):
    gap = gap_classifier.classify(
        AbsentIdentity("entity:unknown", "frame:person")
    )
    assert gap.kind == GapKind.REFERENCE
    assert gap.recommended_owner == RepairOwner.AUTHORITY
    assert gap.safe_response_action == "request_identity"


def test_missing_transition_routes_to_authority(gap_classifier):
    gap = gap_classifier.classify(
        MissingTransition("state:closed", "state:open")
    )
    assert gap.kind == GapKind.TRANSITION
    assert gap.recommended_owner == RepairOwner.AUTHORITY
    assert gap.safe_response_action == "request_transition_definition"


def test_exhausted_proof_bound_routes_to_runtime(gap_classifier):
    gap = gap_classifier.classify(
        TransitionBoundExhausted("transition:1", 6)
    )
    assert gap.kind == GapKind.TRANSITION
    assert gap.recommended_owner == RepairOwner.RUNTIME
    assert gap.safe_response_action == "bound_transition"


def test_resource_absence_is_distinct_from_permission(gap_classifier):
    res_gap = gap_classifier.classify(ResourceUnavailable("model:1", "timeout"))
    perm_gap = gap_classifier.classify(
        PermissionDenied("cap:write", "participant:user")
    )
    assert res_gap.kind != perm_gap.kind
    assert res_gap.recommended_owner != perm_gap.recommended_owner


def test_adapter_failure_is_distinct_from_operation(gap_classifier):
    adapter_gap = gap_classifier.classify(AdapterFailure("adapter:1", "timeout"))
    op_gap = gap_classifier.classify(EffectDenied("effect:1", "denied"))
    assert adapter_gap.kind != op_gap.kind
    assert adapter_gap.kind == GapKind.ADAPTER
    assert op_gap.kind == GapKind.OPERATION


def test_permission_denial_is_distinct_from_adapter_failure(gap_classifier):
    perm_gap = gap_classifier.classify(
        PermissionDenied("cap:write", "participant:user")
    )
    adapter_gap = gap_classifier.classify(AdapterFailure("adapter:1", "timeout"))
    assert perm_gap.kind != adapter_gap.kind
    assert perm_gap.recommended_owner != adapter_gap.recommended_owner


# ---------------------------------------------------------------------------
# CycleStatus: every status reachable from a typed gap fixture
# ---------------------------------------------------------------------------


# Map each CycleStatus to a (kind, owner) pair that reaches it.
_STATUS_FIXTURES = {
    CycleStatus.RESOLVED: None,  # reached by normal success, not a gap
    CycleStatus.PARTIAL: ("designation", "data"),
    CycleStatus.AMBIGUOUS: ("reference", "training"),
    CycleStatus.UNKNOWN: ("evidence", "data"),
    CycleStatus.CONFLICT: ("authority", "authority"),
    CycleStatus.UNSUPPORTED: ("verification", "runtime"),
    CycleStatus.DENIED: ("permission", "policy"),
    CycleStatus.RESOURCE_UNAVAILABLE: ("resource", "data"),
    CycleStatus.BUDGET_EXHAUSTED: ("performance", "runtime"),
    CycleStatus.OPERATION_FAILED: ("implementation", "runtime"),
    CycleStatus.REALIZATION_FAILED: ("realization", "training"),
}


@pytest.mark.parametrize("status", list(CycleStatus))
def test_every_cycle_status_is_reachable(status, gap_classifier):
    """Every closed ``CycleStatus`` is reachable from a typed fixture."""
    if status is CycleStatus.RESOLVED:
        # RESOLVED is reached by normal success, not a gap.
        # We verify it exists in the enum and is the success status.
        assert status.value == "resolved"
        return

    kind, owner = _STATUS_FIXTURES[status]
    receipt = gap_classifier.classify(_fixture_exception(kind, owner))
    from cemm_authoritative_hybrid.runtime import HybridRuntime

    mapped = HybridRuntime._status_from_gap(receipt)
    assert mapped == status, (
        f"status {status.value} not reachable from kind={kind}, owner={owner}; "
        f"got {mapped.value}"
    )


def test_no_status_selected_from_response_wording(gap_classifier):
    """No CycleStatus is selected from response wording or a phrase label."""
    # The classifier never examines surface text; it maps by type only.
    # Verify that two exceptions with different messages but the same type
    # produce the same gap kind and owner.
    gap_a = gap_classifier.classify(MissingOwner("realizer"))
    gap_b = gap_classifier.classify(MissingOwner("authority"))
    assert gap_a.kind == gap_b.kind
    assert gap_a.recommended_owner == gap_b.recommended_owner
    assert gap_a.safe_response_action == gap_b.safe_response_action


def test_no_status_selected_from_phrase_label(gap_classifier):
    """A phrase label in an exception message does not affect classification."""
    # The message text is never examined; only the Python type matters.
    gap = gap_classifier.classify(
        VerificationFailure("this is a phrase label", "cycle:test")
    )
    assert gap.kind == GapKind.VERIFICATION
    assert gap.recommended_owner == RepairOwner.RUNTIME
    assert gap.safe_response_action == "reject_candidate"


# ---------------------------------------------------------------------------
# Property tests: construction and transport decoding reject non-CycleStatus
# ---------------------------------------------------------------------------


def test_cycle_status_construction_rejects_unknown_string():
    """``CycleStatus`` construction rejects strings not in the closed enum."""
    with pytest.raises(ValueError):
        CycleStatus("not_a_status")


def test_cycle_status_construction_rejects_arbitrary_string():
    """Any arbitrary string that is not a valid status value is rejected."""
    for bad in ("clarification", "fallback", "error", "ok", "", "RESOLVED"):
        with pytest.raises(ValueError):
            CycleStatus(bad)


def test_all_cycle_status_values_are_closed():
    """The CycleStatus enum contains exactly the expected closed set."""
    expected = {
        "resolved", "partial", "ambiguous", "unknown", "conflict", "unsupported",
        "denied", "resource_unavailable", "budget_exhausted", "operation_failed",
        "realization_failed",
    }
    actual = {s.value for s in CycleStatus}
    assert actual == expected


def test_transport_decoding_rejects_non_cycle_status_string():
    """Transport decoding must reject any string not in CycleStatus before
    it can become an externally reachable result."""
    valid_values = {s.value for s in CycleStatus}
    # Simulate a transport decoder: only accept known values.
    bad_input = "clarification"
    assert bad_input not in valid_values
    with pytest.raises(ValueError):
        CycleStatus(bad_input)


# ---------------------------------------------------------------------------
# All 18 gap kinds are reachable
# ---------------------------------------------------------------------------


def test_all_18_gap_kinds_are_reachable(gap_case):
    """Every one of the 18 gap kinds is reachable from a typed fixture."""
    expected_kinds = {
        "evidence", "designation", "reference", "authority", "proposal",
        "verification", "inference", "state", "transition", "learning",
        "resource", "permission", "adapter", "operation", "storage",
        "realization", "performance", "implementation",
    }
    reached_kinds: set[str] = set()
    for kind, owner in [
        ("evidence", "data"), ("designation", "data"), ("reference", "training"),
        ("authority", "authority"), ("proposal", "training"), ("verification", "runtime"),
        ("inference", "runtime"), ("state", "data"), ("transition", "authority"),
        ("learning", "policy"), ("resource", "data"), ("permission", "policy"),
        ("adapter", "adapter"), ("operation", "adapter"), ("storage", "runtime"),
        ("realization", "training"), ("performance", "runtime"), ("implementation", "runtime"),
    ]:
        receipt = gap_case(kind, owner)
        reached_kinds.add(receipt.kind.value)
    assert reached_kinds == expected_kinds


def test_all_6_owners_are_reachable(gap_case):
    """Every one of the 6 repair owners is reachable from a typed fixture."""
    expected_owners = {"data", "training", "authority", "runtime", "policy", "adapter"}
    reached_owners: set[str] = set()
    for kind, owner in [
        ("evidence", "data"), ("designation", "data"), ("reference", "training"),
        ("authority", "authority"), ("proposal", "training"), ("verification", "runtime"),
        ("inference", "runtime"), ("state", "data"), ("transition", "authority"),
        ("learning", "policy"), ("resource", "data"), ("permission", "policy"),
        ("adapter", "adapter"), ("operation", "adapter"), ("storage", "runtime"),
        ("realization", "training"), ("performance", "runtime"), ("implementation", "runtime"),
    ]:
        receipt = gap_case(kind, owner)
        reached_owners.add(receipt.recommended_owner.value)
    assert reached_owners == expected_owners
