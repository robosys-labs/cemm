"""Gap owner evaluation tests (M4 Task 4).

Verifies that every gap kind's recommended repair owner is correct —
i.e. the :class:`GapClassifier` maps each typed exception to the right
:class:`RepairOwner`. No owner is inferred from response-string equality.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.gaps import (
    AdapterFailure,
    BudgetExhausted,
    CoverageGap,
    EffectDenied,
    EvidenceGap,
    GapClassifier,
    GapKind,
    LearningGap,
    MissingOwner,
    MissingTransition,
    PermissionDenied,
    ProposalGap,
    RealizationFailure,
    ReferenceAmbiguity,
    AbsentIdentity,
    RepairOwner,
    ResourceUnavailable,
    SemanticConflict,
    StateGap,
    StorageFailure,
    TransitionBoundExhausted,
    VerificationFailure,
    InferenceBound,
)


# ---------------------------------------------------------------------------
# Expected (gap_kind, repair_owner) pairs for every typed exception
# ---------------------------------------------------------------------------


EXPECTED_OWNERS = [
    # (exception_factory, expected_gap_kind, expected_repair_owner)
    (lambda: MissingOwner("proposal"), GapKind.IMPLEMENTATION, RepairOwner.RUNTIME),
    (lambda: VerificationFailure("bad", "cycle:1"), GapKind.VERIFICATION, RepairOwner.RUNTIME),
    (lambda: CoverageGap("span:1", "no designation"), GapKind.DESIGNATION, RepairOwner.DATA),
    (lambda: EffectDenied("effect:1", "no permission"), GapKind.OPERATION, RepairOwner.ADAPTER),
    (lambda: RealizationFailure("resp:1", "failed"), GapKind.REALIZATION, RepairOwner.TRAINING),
    (lambda: BudgetExhausted("beam", 32), GapKind.PERFORMANCE, RepairOwner.RUNTIME),
    (lambda: ResourceUnavailable("model:1", "unavailable"), GapKind.RESOURCE, RepairOwner.DATA),
    (lambda: PermissionDenied("cap:1", "participant:user"), GapKind.PERMISSION, RepairOwner.POLICY),
    (lambda: SemanticConflict("graph:1", "conflict"), GapKind.AUTHORITY, RepairOwner.AUTHORITY),
    (lambda: EvidenceGap("claim:1", "missing"), GapKind.EVIDENCE, RepairOwner.DATA),
    (lambda: ReferenceAmbiguity("ref:1", ("cand:1", "cand:2")), GapKind.REFERENCE, RepairOwner.TRAINING),
    (lambda: AbsentIdentity("id:1", "frame:1"), GapKind.REFERENCE, RepairOwner.AUTHORITY),
    (lambda: ProposalGap("cycle:1", "gap"), GapKind.PROPOSAL, RepairOwner.TRAINING),
    (lambda: InferenceBound("query:1", "depth"), GapKind.INFERENCE, RepairOwner.RUNTIME),
    (lambda: StateGap("entity:1", "dim:1"), GapKind.STATE, RepairOwner.DATA),
    (lambda: MissingTransition("s1", "s2"), GapKind.TRANSITION, RepairOwner.AUTHORITY),
    (lambda: TransitionBoundExhausted("trans:1", 6), GapKind.TRANSITION, RepairOwner.RUNTIME),
    (lambda: LearningGap("obligation:1", "pending"), GapKind.LEARNING, RepairOwner.POLICY),
    (lambda: AdapterFailure("adapter:1", "failed"), GapKind.ADAPTER, RepairOwner.ADAPTER),
    (lambda: StorageFailure("store:1", "corrupt"), GapKind.STORAGE, RepairOwner.RUNTIME),
]


@pytest.fixture
def classifier():
    return GapClassifier()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc_factory,expected_kind,expected_owner",
    EXPECTED_OWNERS,
    ids=[f"{ek.value}-{eo.value}" for _, ek, eo in EXPECTED_OWNERS],
)
def test_gap_owner_is_correct(classifier, exc_factory, expected_kind, expected_owner):
    """Every typed exception maps to the correct gap kind and repair owner."""
    receipt = classifier.classify(exc_factory())
    assert receipt.kind == expected_kind, (
        f"Expected kind {expected_kind.value}, got {receipt.kind.value}"
    )
    assert receipt.recommended_owner == expected_owner, (
        f"Expected owner {expected_owner.value}, got {receipt.recommended_owner.value}"
    )


def test_every_gap_kind_has_an_owner(classifier):
    """All 18 gap kinds are covered by the classifier with a valid owner."""
    seen_kinds: set[GapKind] = set()
    for exc_factory, expected_kind, _ in EXPECTED_OWNERS:
        receipt = classifier.classify(exc_factory())
        seen_kinds.add(receipt.kind)
    # All 18 gap kinds must be reachable.
    for kind in GapKind:
        assert kind in seen_kinds, f"GapKind.{kind.value} has no test coverage"


def test_gap_owner_evaluation_in_report():
    """The evaluation report's per-gap-kind metrics confirm correct owners."""
    from cemm_authoritative_hybrid.evaluation import EvaluationReport
    from pathlib import Path

    report_path = Path(__file__).resolve().parents[1] / "artifacts" / "evaluation" / "CEMM_EVALUATION.json"
    if not report_path.exists():
        pytest.fail(
            f"CEMM_EVALUATION.json not found at {report_path}. "
            "Run: python scripts/evaluate_cemm.py"
        )
    report = EvaluationReport.from_json(report_path.read_text(encoding="utf-8"))
    # Every gap kind in the report has owner_correct == True.
    for kind, metrics in report.per_gap_kind_metrics.items():
        assert metrics.get("owner_correct", False), (
            f"Gap kind {kind} has incorrect owner"
        )
