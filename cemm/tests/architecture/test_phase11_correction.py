"""Phase 11 gate tests: Correction, retraction, and retention.

Gates (from IMPLEMENTATION_PLAN.md Phase 11):
- removed support stops contributing;
- dependent cognition re-evaluates;
- historical meaning remains where policy permits;
- archival cannot masquerade as privacy deletion.

Additional guardrail tests from AGENTS.md §7.8, ACCEPTANCE_TESTS.md §38-40:
- 6 distinct operations: supersession, support_retraction, permission_revocation,
  archival, forgetting, privacy_deletion
- Each targets exact evidence/proposition/sense/schema revisions
- Correction targets exact sense/revision — unrelated senses unaffected
- Old historical proposition meaning preserved
- Archival remains reversible/retrievable under policy
- Privacy deletion removes or cryptographically erases protected content
- Neither is mislabeled as the other
- Provenance history may be retained only where policy permits
- Import boundaries: correction → model only
"""
from __future__ import annotations

import pytest

from cemm.kernel.correction.operations import (
    CorrectionKind, CorrectionReversibility, RetentionPolicy,
    CorrectionOperation, CorrectionResult,
    CorrectionOperationFactory,
)
from cemm.kernel.correction.retraction_engine import (
    RetractionEngine, DependentArtifact,
)
from cemm.kernel.correction.guards import (
    ArchivalPrivacyGuard, CorrectionTargetingGuard, PolicyCheckResult,
)


# ── Helpers ────────────────────────────────────────────────────────


def make_supersession(target: str = "sense:bank:river:v1") -> CorrectionOperation:
    return CorrectionOperationFactory.supersession(target)


def make_support_retraction(target: str = "ev:1") -> CorrectionOperation:
    return CorrectionOperationFactory.support_retraction(target)


def make_permission_revocation(target: str = "schema:1:v2") -> CorrectionOperation:
    return CorrectionOperationFactory.permission_revocation(target)


def make_archival(target: str = "prop:1") -> CorrectionOperation:
    return CorrectionOperationFactory.archival(target)


def make_forgetting(target: str = "prop:1") -> CorrectionOperation:
    return CorrectionOperationFactory.forgetting(target)


def make_privacy_deletion(target: str = "prop:1") -> CorrectionOperation:
    return CorrectionOperationFactory.privacy_deletion(target)


# ── Gate 1: removed support stops contributing ──


def test_removed_support_stops_contributing():
    """Removed support stops contributing."""
    engine = RetractionEngine()

    # Register a dependent on ev:1
    engine.register_dependency(
        artifact_ref="assess:1",
        artifact_kind="assessment",
        depends_on="ev:1",
    )

    # Before retraction, support contributes
    assert engine.support_still_contributes("ev:1", after_retraction=False)

    # Execute support retraction
    result = engine.execute(make_support_retraction("ev:1"))
    assert result.success

    # After retraction, support no longer contributes
    assert not engine.support_still_contributes("ev:1", after_retraction=True)


def test_support_retraction_returns_affected_dependents():
    """Support retraction returns affected dependent artifacts."""
    engine = RetractionEngine()

    engine.register_dependency("assess:1", "assessment", "ev:1")
    engine.register_dependency("inference:1", "inference", "ev:1")
    engine.register_dependency("cached:1", "cached_answer", "ev:1")

    result = engine.execute(make_support_retraction("ev:1"))

    assert "assess:1" in result.affected_refs
    assert "inference:1" in result.affected_refs
    assert "cached:1" in result.affected_refs


def test_support_retraction_exact_target_not_substring():
    """Regression: retracting ev:1 must not affect ev:10 (substring bug)."""
    engine = RetractionEngine()

    # Retract ev:1
    engine.execute(make_support_retraction("ev:1"))

    # ev:10 should still contribute — it was not retracted
    assert engine.support_still_contributes("ev:10", after_retraction=True)
    # ev:1 should not contribute
    assert not engine.support_still_contributes("ev:1", after_retraction=True)


# ── Gate 2: dependent cognition re-evaluates ──


def test_dependent_cognition_re_evaluates():
    """Dependent cognition re-evaluates after correction."""
    engine = RetractionEngine()

    # Register multiple dependent artifacts
    engine.register_dependency("assess:1", "assessment", "schema:1:v1")
    engine.register_dependency("plan:1", "plan", "schema:1:v1")
    engine.register_dependency("msg:1", "undispatched_message", "schema:1:v1")

    # Execute supersession
    result = engine.execute(make_supersession("schema:1:v1"))

    # All dependents are affected — they need re-evaluation
    assert len(result.affected_refs) == 3
    assert "assess:1" in result.affected_refs
    assert "plan:1" in result.affected_refs
    assert "msg:1" in result.affected_refs


def test_correction_triggers_reassessment():
    """All correction operations trigger dependency reassessment."""
    for factory_fn in [
        CorrectionOperationFactory.supersession,
        CorrectionOperationFactory.support_retraction,
        CorrectionOperationFactory.permission_revocation,
        CorrectionOperationFactory.archival,
        CorrectionOperationFactory.forgetting,
        CorrectionOperationFactory.privacy_deletion,
    ]:
        op = factory_fn("target:1")
        assert op.triggers_reassessment, f"{op.kind.value} must trigger reassessment"


# ── Gate 3: historical meaning remains where policy permits ──


def test_historical_meaning_remains_for_supersession():
    """Historical meaning remains for supersession where policy permits."""
    engine = RetractionEngine()

    result = engine.execute(make_supersession("schema:1:v1"))
    assert result.retained_history


def test_historical_meaning_remains_for_support_retraction():
    """Provenance history remains for support retraction where permitted."""
    engine = RetractionEngine()

    result = engine.execute(make_support_retraction("ev:1"))
    assert result.retained_history


def test_historical_meaning_remains_for_archival():
    """Historical meaning remains for archival."""
    engine = RetractionEngine()

    result = engine.execute(make_archival("prop:1"))
    assert result.retained_history


def test_historical_meaning_removed_for_privacy_deletion():
    """Privacy deletion removes/crypto-erases provenance history."""
    engine = RetractionEngine()

    result = engine.execute(make_privacy_deletion("prop:1"))
    assert not result.retained_history


def test_historical_meaning_removed_for_forgetting():
    """Forgetting removes content but may retain provenance."""
    engine = RetractionEngine()

    result = engine.execute(make_forgetting("prop:1"))
    # Forgetting retains provenance history by default
    assert result.retained_history


# ── Gate 4: archival cannot masquerade as privacy deletion ──


def test_archival_is_reversible():
    """Archival remains reversible/retrievable under policy."""
    guard = ArchivalPrivacyGuard()
    op = make_archival("prop:1")

    assert guard.can_reverse(op)
    assert guard.can_retrieve(op)


def test_privacy_deletion_is_irreversible():
    """Privacy deletion is irreversible and not retrievable."""
    guard = ArchivalPrivacyGuard()
    op = make_privacy_deletion("prop:1")

    assert not guard.can_reverse(op)
    assert not guard.can_retrieve(op)


def test_archival_not_mislabeled_as_privacy():
    """Archival cannot masquerade as privacy deletion."""
    guard = ArchivalPrivacyGuard()

    # Archival with privacy in ID is caught
    bad_archival = CorrectionOperation(
        operation_id="privacy_delete:prop:1",  # Mislabeled!
        kind=CorrectionKind.ARCHIVAL,
        target_ref="prop:1",
        target_kind="proposition",
        reversibility=CorrectionReversibility.REVERSIBLE,  # Valid for archival
        retention_policy=RetentionPolicy.RETAIN,  # Valid for archival
    )

    result = guard.check_operation(bad_archival)
    assert not result.is_valid
    assert "mislabeled" in result.violation


def test_privacy_deletion_not_mislabeled_as_archival():
    """Privacy deletion cannot masquerade as archival."""
    guard = ArchivalPrivacyGuard()

    bad_privacy = CorrectionOperation(
        operation_id="archive:prop:1",  # Mislabeled!
        kind=CorrectionKind.PRIVACY_DELETION,
        target_ref="prop:1",
        target_kind="proposition",
        reversibility=CorrectionReversibility.IRREVERSIBLE,
        retention_policy=RetentionPolicy.CRYPTO_ERASE,
    )

    result = guard.check_operation(bad_privacy)
    assert not result.is_valid
    assert "mislabeled" in result.violation


def test_archival_must_be_reversible():
    """Archival with wrong reversibility is caught."""
    guard = ArchivalPrivacyGuard()

    bad_archival = CorrectionOperation(
        operation_id="archive:prop:1",
        kind=CorrectionKind.ARCHIVAL,
        target_ref="prop:1",
        target_kind="proposition",
        reversibility=CorrectionReversibility.IRREVERSIBLE,  # Wrong!
    )

    result = guard.check_operation(bad_archival)
    assert not result.is_valid
    assert "reversible" in result.violation


def test_privacy_deletion_must_crypto_erase():
    """Privacy deletion without crypto-erase is caught."""
    guard = ArchivalPrivacyGuard()

    bad_privacy = CorrectionOperation(
        operation_id="privacy_delete:prop:1",
        kind=CorrectionKind.PRIVACY_DELETION,
        target_ref="prop:1",
        target_kind="proposition",
        reversibility=CorrectionReversibility.IRREVERSIBLE,
        retention_policy=RetentionPolicy.RETAIN,  # Wrong! Must crypto-erase
    )

    result = guard.check_operation(bad_privacy)
    assert not result.is_valid
    assert "crypto-erase" in result.violation


def test_archival_cannot_crypto_erase():
    """Archival must not crypto-erase provenance."""
    guard = ArchivalPrivacyGuard()

    bad_archival = CorrectionOperation(
        operation_id="archive:prop:1",
        kind=CorrectionKind.ARCHIVAL,
        target_ref="prop:1",
        target_kind="proposition",
        reversibility=CorrectionReversibility.REVERSIBLE,
        retention_policy=RetentionPolicy.CRYPTO_ERASE,  # Wrong!
    )

    result = guard.check_operation(bad_archival)
    assert not result.is_valid
    assert "crypto-erase" in result.violation


def test_valid_archival_passes_guard():
    """Valid archival passes the guard."""
    guard = ArchivalPrivacyGuard()
    result = guard.check_operation(make_archival("prop:1"))
    assert result.is_valid


def test_valid_privacy_deletion_passes_guard():
    """Valid privacy deletion passes the guard."""
    guard = ArchivalPrivacyGuard()
    result = guard.check_operation(make_privacy_deletion("prop:1"))
    assert result.is_valid


# ── Correction targeting tests ──


def test_correction_targets_exact_sense():
    """Correction targets exact sense/revision."""
    guard = CorrectionTargetingGuard()

    op = make_supersession("sense:bank:river:v1")
    known = ("sense:bank:river:v1", "sense:bank:financial:v1")

    result = guard.check_target_precision(op, known)
    assert result.is_valid


def test_correction_unknown_target_detected():
    """Correction with unknown target is detected."""
    guard = CorrectionTargetingGuard()

    op = make_supersession("sense:unknown:v1")
    known = ("sense:bank:river:v1", "sense:bank:financial:v1")

    result = guard.check_target_precision(op, known)
    assert not result.is_valid


def test_unrelated_senses_unaffected():
    """Unrelated senses are unaffected by correction."""
    guard = CorrectionTargetingGuard()

    op = make_supersession("sense:bank:river:v1")
    related = ("sense:bank:river:v1", "sense:bank:financial:v1")
    affected = ("sense:bank:river:v1",)  # Only the target is affected

    result = guard.check_unaffected_senses(op, related, affected)
    assert result.is_valid


def test_unrelated_senses_violation_detected():
    """Violation detected when unrelated sense is affected."""
    guard = CorrectionTargetingGuard()

    op = make_supersession("sense:bank:river:v1")
    related = ("sense:bank:river:v1", "sense:bank:financial:v1")
    affected = ("sense:bank:river:v1", "sense:bank:financial:v1")  # Both affected!

    result = guard.check_unaffected_senses(op, related, affected)
    assert not result.is_valid
    assert "sense:bank:financial:v1" in result.violation


def test_history_preserved_for_non_deletion():
    """Historical meaning preserved for non-deletion operations."""
    guard = CorrectionTargetingGuard()

    op = make_supersession("schema:1:v1")
    result = guard.check_history_preserved(op, history_available=True)
    assert result.is_valid


def test_history_not_preserved_detected():
    """Missing history detected for non-deletion operations."""
    guard = CorrectionTargetingGuard()

    op = make_supersession("schema:1:v1")
    result = guard.check_history_preserved(op, history_available=False)
    assert not result.is_valid


def test_history_not_required_for_privacy_deletion():
    """History not required for privacy deletion."""
    guard = CorrectionTargetingGuard()

    op = make_privacy_deletion("prop:1")
    result = guard.check_history_preserved(op, history_available=False)
    assert result.is_valid


# ── 6 distinct operations tests ──


def test_six_distinct_correction_kinds():
    """The kernel distinguishes exactly 6 correction/retention operations."""
    kinds = set(CorrectionKind)
    assert len(kinds) == 6
    assert CorrectionKind.SUPERSESSION in kinds
    assert CorrectionKind.SUPPORT_RETRACTION in kinds
    assert CorrectionKind.PERMISSION_REVOCATION in kinds
    assert CorrectionKind.ARCHIVAL in kinds
    assert CorrectionKind.FORGETTING in kinds
    assert CorrectionKind.PRIVACY_DELETION in kinds


def test_each_kind_has_distinct_factory():
    """Each correction kind has a distinct factory method."""
    ops = [
        CorrectionOperationFactory.supersession("t:1"),
        CorrectionOperationFactory.support_retraction("t:1"),
        CorrectionOperationFactory.permission_revocation("t:1"),
        CorrectionOperationFactory.archival("t:1"),
        CorrectionOperationFactory.forgetting("t:1"),
        CorrectionOperationFactory.privacy_deletion("t:1"),
    ]
    kinds = [op.kind for op in ops]
    assert len(set(kinds)) == 6  # All distinct


def test_supersession_retains_history():
    """Supersession retains provenance history."""
    op = make_supersession()
    assert op.retention_policy == RetentionPolicy.RETAIN


def test_privacy_deletion_crypto_erases():
    """Privacy deletion crypto-erases."""
    op = make_privacy_deletion()
    assert op.retention_policy == RetentionPolicy.CRYPTO_ERASE


def test_archival_is_reversible_by_design():
    """Archival is reversible by design."""
    op = make_archival()
    assert op.reversibility == CorrectionReversibility.REVERSIBLE


def test_privacy_deletion_is_irreversible_by_design():
    """Privacy deletion is irreversible by design."""
    op = make_privacy_deletion()
    assert op.reversibility == CorrectionReversibility.IRREVERSIBLE


# ── Import boundary tests ──


def test_phase11_imports_no_engine():
    """Phase 11 correction modules must not import any engine module."""
    import cemm.kernel.correction.operations as ops_mod
    import cemm.kernel.correction.retraction_engine as re_mod
    import cemm.kernel.correction.guards as gu_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    for mod in [ops_mod, re_mod, gu_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__file__} imports forbidden module {f}"


def test_correction_does_not_import_schema():
    """Correction modules must not import schema submodules."""
    import cemm.kernel.correction.operations as ops_mod
    import cemm.kernel.correction.retraction_engine as re_mod
    import cemm.kernel.correction.guards as gu_mod

    forbidden_schema = [
        "from ..schema.",
        "from cemm.kernel.schema.",
    ]
    for mod in [ops_mod, re_mod, gu_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden_schema:
            assert f not in source, f"{mod.__file__} imports forbidden schema module {f}"
