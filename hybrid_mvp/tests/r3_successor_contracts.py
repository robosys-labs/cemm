"""Exact audited assertion routing for R3 predecessor-lineage wrappers.

Only explicitly mapped category/assertion pairs earn successor credit, by
executing their assertion-specific current tests on every call. Unmapped wrapper
claims fail as unproved; test metadata and broad smoke checks are not evidence
of an assertion-specific binding.
"""
from __future__ import annotations


_ASSERTION_RUNNERS = {
    (
        "safety",
        "assertion:safety-and-contracts-no-raw-phrase-equality-dispatch-in-runtime-source",
    ): "test_r1_runtime_has_no_raw_phrase_equality_dispatch",
    (
        "safety",
        "assertion:safety-and-contracts-recursive-graph-cycle-rejected",
    ): "test_r2_semantic_expression_rejects_application_cycle",
    (
        "safety",
        "assertion:safety-and-contracts-safe-artifact-contract-replaces-legacy-checkpoint",
    ): "test_r1_safe_artifact_contract_has_no_legacy_checkpoint_api",
}


def assert_successor_contract(contract: str, assertion_ref: str) -> None:
    """Execute only the exact independently audited assertion runner."""
    if type(assertion_ref) is not str or not assertion_ref.startswith("assertion:"):
        raise TypeError("assertion_ref must be a governed assertion identity")
    runner_name = _ASSERTION_RUNNERS.get((contract, assertion_ref)) if type(contract) is str else None
    if runner_name is None:
        raise AssertionError(
            f"unmapped successor assertion: category={contract!r}, assertion_ref={assertion_ref!r}; "
            "no audited assertion-specific runner"
        )
    from tests import test_r1_r2_safety_successors

    getattr(test_r1_r2_safety_successors, runner_name)()
