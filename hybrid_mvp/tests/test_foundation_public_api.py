"""Exactly one root-installed CycleResult and one public FoundationRuntime."""
from cemm_authoritative_hybrid import (
    CycleFinalizer,
    CycleResult,
    FoundationRuntime,
    FoundationTurn,
    load_foundation,
)
from cemm_authoritative_hybrid.r3_cycle import (
    CycleFinalizer as ExactFinalizer,
    CycleResult as ExactResult,
)
from cemm_authoritative_hybrid.foundation import (
    FoundationRuntime as ExactFoundationRuntime,
    FoundationTurn as ExactFoundationTurn,
    load_foundation as exact_loader,
)


def test_canonical_public_abi_is_the_executable_r3_successor():
    assert CycleResult is ExactResult
    assert CycleFinalizer is ExactFinalizer
    assert FoundationRuntime is ExactFoundationRuntime
    assert FoundationTurn is ExactFoundationTurn
    assert load_foundation is exact_loader
