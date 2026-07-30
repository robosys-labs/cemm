"""Gap receipt tests: typed gap classification and receipt structure.

These tests assert the Gap Receipt ABI. They verify that ``GapClassifier``
maps typed exceptions to exact gap kinds, recommended owners and safe response
actions — never examining surface text. Unknown exceptions become
``implementation`` gaps rather than reaching users as generic clarification.
"""

from __future__ import annotations

import dataclasses

from cemm_authoritative_hybrid.gaps import (
    BudgetExhausted,
    CoverageGap,
    EffectDenied,
    GapClassifier,
    GapKind,
    GapReceipt,
    MissingOwner,
    PermissionDenied,
    RealizationFailure,
    RepairOwner,
    ResourceUnavailable,
    SemanticConflict,
    VerificationFailure,
    EvidenceGap,
    ReferenceAmbiguity,
    AbsentIdentity,
    ProposalGap,
    InferenceBound,
    StateGap,
    MissingTransition,
    TransitionBoundExhausted,
    LearningGap,
    AdapterFailure,
    StorageFailure,
)


# ---------------------------------------------------------------------------
# Closed gap kinds (18) and repair owners (6)
# ---------------------------------------------------------------------------


def test_gap_kind_enum_is_closed():
    assert tuple(kind.value for kind in GapKind) == (
        "evidence", "designation", "reference", "authority", "proposal",
        "verification", "inference", "state", "transition", "learning",
        "resource", "permission", "adapter", "operation", "storage",
        "realization", "performance", "implementation",
    )


def test_repair_owner_enum_is_closed():
    assert tuple(owner.value for owner in RepairOwner) == (
        "data", "training", "authority", "runtime", "policy", "adapter",
    )


# ---------------------------------------------------------------------------
# Typed exception classification
# ---------------------------------------------------------------------------


def test_missing_owner_is_implementation_gap(gap_classifier):
    gap = gap_classifier.classify(MissingOwner("realizer"))
    assert gap.kind == GapKind.IMPLEMENTATION
    assert gap.recommended_owner == RepairOwner.RUNTIME
    assert gap.safe_response_action == "activation_failure"


def test_verification_failure_is_verification_gap(gap_classifier):
    gap = gap_classifier.classify(VerificationFailure("structural", "cycle:test"))
    assert gap.kind == GapKind.VERIFICATION
    assert gap.recommended_owner == RepairOwner.RUNTIME


def test_coverage_gap_is_designation_gap(gap_classifier):
    gap = gap_classifier.classify(CoverageGap("span:1", "no designation"))
    assert gap.kind == GapKind.DESIGNATION
    assert gap.recommended_owner == RepairOwner.DATA


def test_effect_denied_is_operation_gap(gap_classifier):
    gap = gap_classifier.classify(EffectDenied("effect:1", "permission missing"))
    assert gap.kind == GapKind.OPERATION
    assert gap.recommended_owner == RepairOwner.ADAPTER


def test_realization_failure_is_realization_gap(gap_classifier):
    gap = gap_classifier.classify(RealizationFailure("response:1", "no surface"))
    assert gap.kind == GapKind.REALIZATION
    assert gap.recommended_owner == RepairOwner.TRAINING


def test_budget_exhausted_is_performance_gap(gap_classifier):
    gap = gap_classifier.classify(BudgetExhausted("tokens", 64))
    assert gap.kind == GapKind.PERFORMANCE
    assert gap.recommended_owner == RepairOwner.RUNTIME


def test_resource_unavailable_is_resource_gap(gap_classifier):
    gap = gap_classifier.classify(ResourceUnavailable("model:1", "timeout"))
    assert gap.kind == GapKind.RESOURCE
    assert gap.recommended_owner == RepairOwner.DATA


def test_permission_denied_is_permission_gap(gap_classifier):
    gap = gap_classifier.classify(PermissionDenied("cap:write", "participant:user"))
    assert gap.kind == GapKind.PERMISSION
    assert gap.recommended_owner == RepairOwner.POLICY


def test_semantic_conflict_is_authority_gap(gap_classifier):
    gap = gap_classifier.classify(SemanticConflict("graph:1", "ambiguous designation"))
    assert gap.kind == GapKind.AUTHORITY
    assert gap.recommended_owner == RepairOwner.AUTHORITY


def test_unknown_exception_is_implementation_gap(gap_classifier):
    gap = gap_classifier.classify(RuntimeError("something unexpected"))
    assert gap.kind == GapKind.IMPLEMENTATION
    assert gap.recommended_owner == RepairOwner.RUNTIME
    assert gap.safe_response_action == "activation_failure"


def test_classifier_never_examines_surface_text(gap_classifier):
    """A typed exception must classify by type, not by its message text."""
    gap_a = gap_classifier.classify(MissingOwner("realizer"))
    gap_b = gap_classifier.classify(MissingOwner("authority"))
    assert gap_a.kind == gap_b.kind == GapKind.IMPLEMENTATION
    assert gap_a.recommended_owner == gap_b.recommended_owner == RepairOwner.RUNTIME


# -- New gap kind classification -------------------------------------------


def test_evidence_gap_is_evidence_kind(gap_classifier):
    gap = gap_classifier.classify(EvidenceGap("claim:1", "no evidence"))
    assert gap.kind == GapKind.EVIDENCE
    assert gap.recommended_owner == RepairOwner.DATA


def test_reference_ambiguity_routes_to_training(gap_classifier):
    gap = gap_classifier.classify(
        ReferenceAmbiguity("ref:1", ("candidate:a", "candidate:b"))
    )
    assert gap.kind == GapKind.REFERENCE
    assert gap.recommended_owner == RepairOwner.TRAINING


def test_absent_identity_routes_to_authority(gap_classifier):
    gap = gap_classifier.classify(
        AbsentIdentity("entity:unknown", "frame:person")
    )
    assert gap.kind == GapKind.REFERENCE
    assert gap.recommended_owner == RepairOwner.AUTHORITY


def test_proposal_gap_is_proposal_kind(gap_classifier):
    gap = gap_classifier.classify(ProposalGap("cycle:1", "no candidates"))
    assert gap.kind == GapKind.PROPOSAL
    assert gap.recommended_owner == RepairOwner.TRAINING


def test_inference_bound_is_inference_kind(gap_classifier):
    gap = gap_classifier.classify(InferenceBound("query:1", "max_rounds"))
    assert gap.kind == GapKind.INFERENCE
    assert gap.recommended_owner == RepairOwner.RUNTIME


def test_state_gap_is_state_kind(gap_classifier):
    gap = gap_classifier.classify(StateGap("entity:door", "dimension:open"))
    assert gap.kind == GapKind.STATE
    assert gap.recommended_owner == RepairOwner.DATA


def test_missing_transition_routes_to_authority(gap_classifier):
    gap = gap_classifier.classify(
        MissingTransition("state:closed", "state:open")
    )
    assert gap.kind == GapKind.TRANSITION
    assert gap.recommended_owner == RepairOwner.AUTHORITY


def test_transition_bound_exhausted_routes_to_runtime(gap_classifier):
    gap = gap_classifier.classify(
        TransitionBoundExhausted("transition:1", 6)
    )
    assert gap.kind == GapKind.TRANSITION
    assert gap.recommended_owner == RepairOwner.RUNTIME


def test_learning_gap_is_learning_kind(gap_classifier):
    gap = gap_classifier.classify(LearningGap("obligation:1", "no plan"))
    assert gap.kind == GapKind.LEARNING
    assert gap.recommended_owner == RepairOwner.POLICY


def test_adapter_failure_is_adapter_kind(gap_classifier):
    gap = gap_classifier.classify(AdapterFailure("adapter:1", "timeout"))
    assert gap.kind == GapKind.ADAPTER
    assert gap.recommended_owner == RepairOwner.ADAPTER


def test_storage_failure_is_storage_kind(gap_classifier):
    gap = gap_classifier.classify(StorageFailure("store:world", "io error"))
    assert gap.kind == GapKind.STORAGE
    assert gap.recommended_owner == RepairOwner.RUNTIME


# ---------------------------------------------------------------------------
# Gap receipt structure
# ---------------------------------------------------------------------------


def test_gap_receipt_is_frozen_dataclass():
    receipt = GapReceipt(
        gap_ref="gap:test",
        kind=GapKind.IMPLEMENTATION,
        status="activation_failure",
        source_refs=("cycle:test",),
        blockers=("missing owner: realizer",),
        missing_contract_refs=(),
        rejected_candidate_refs=(),
        recommended_owner=RepairOwner.RUNTIME,
        safe_response_action="activation_failure",
    )
    assert dataclasses.is_dataclass(receipt)
    try:
        receipt.kind = GapKind.EVIDENCE  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("GapReceipt must be frozen")


def test_gap_receipt_has_stable_ref(gap_classifier):
    gap = gap_classifier.classify(MissingOwner("realizer"))
    assert gap.gap_ref.startswith("gap:")
    # same input yields same ref (deterministic)
    gap2 = gap_classifier.classify(MissingOwner("realizer"))
    assert gap.gap_ref == gap2.gap_ref
