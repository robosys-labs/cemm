"""Successor credit requires an exact audited assertion-specific runner."""
from __future__ import annotations

import pytest

from tests import r3_successor_contracts as routing
from tests import test_r1_r2_safety_successors as safety
from tests import test_r3_closeout_successors as wrappers

__cemm_test_inventory__ = {
    "tests/test_foundation_successor_routing.py::test_unknown_assertion_is_not_credited_by_category_smoke": {
        "source_ast_sha256": "3f0075767c43217d904aa77be94bd815c25332f6ba96fdec172aa49d7babd0f1",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-unknown-assertion-is-not-credited-by-category-smoke",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_audited_assertion_with_wrong_category_is_rejected": {
        "source_ast_sha256": "90fc13ac30058054f9193cd24de7590b0cb74e9ad746a5cdfc6277ec1251e870",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-audited-assertion-with-wrong-category-is-rejected",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_registered_wrapper_without_audited_runner_remains_unproved": {
        "source_ast_sha256": "01d9ce86219772cb80c6515b38fae10a906ac7924b255242e8fd293240c0263d",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-registered-wrapper-without-audited-runner-remains-unproved",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_exact_runner_is_invoked_each_time_and_failure_is_not_cached[phrase-dispatch]": {
        "source_ast_sha256": "a965bb1f7d51baa67f3ccac47d6bfaaeaea069c3f730fd50526673660396ebbd",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-exact-runner-is-invoked-each-time-and-failure-is-not-cached-phrase-dispatch",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_exact_runner_is_invoked_each_time_and_failure_is_not_cached[application-cycle]": {
        "source_ast_sha256": "a965bb1f7d51baa67f3ccac47d6bfaaeaea069c3f730fd50526673660396ebbd",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-exact-runner-is-invoked-each-time-and-failure-is-not-cached-application-cycle",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_exact_runner_is_invoked_each_time_and_failure_is_not_cached[checkpoint-api]": {
        "source_ast_sha256": "a965bb1f7d51baa67f3ccac47d6bfaaeaea069c3f730fd50526673660396ebbd",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-exact-runner-is-invoked-each-time-and-failure-is-not-cached-checkpoint-api",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_mapped_assertion_executes_its_real_current_runner[phrase-dispatch]": {
        "source_ast_sha256": "f1c01ca6bedd20c56b81177eaeab94169132d37a613e4f0ef05f6adebf837e04",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-mapped-assertion-executes-its-real-current-runner-phrase-dispatch",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_mapped_assertion_executes_its_real_current_runner[application-cycle]": {
        "source_ast_sha256": "f1c01ca6bedd20c56b81177eaeab94169132d37a613e4f0ef05f6adebf837e04",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-mapped-assertion-executes-its-real-current-runner-application-cycle",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    },
    "tests/test_foundation_successor_routing.py::test_mapped_assertion_executes_its_real_current_runner[checkpoint-api]": {
        "source_ast_sha256": "f1c01ca6bedd20c56b81177eaeab94169132d37a613e4f0ef05f6adebf837e04",
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-successor-mapped-assertion-executes-its-real-current-runner-checkpoint-api",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Routing-Repair"
    }
}




def test_unknown_assertion_is_not_credited_by_category_smoke():
    with pytest.raises(AssertionError, match="unmapped successor assertion.*safety.*assertion:never-audited"):
        routing.assert_successor_contract("safety", "assertion:never-audited")


def test_audited_assertion_with_wrong_category_is_rejected():
    with pytest.raises(AssertionError, match="unmapped successor assertion.*focus.*no-raw-phrase"):
        routing.assert_successor_contract(
            "focus", "assertion:safety-and-contracts-no-raw-phrase-equality-dispatch-in-runtime-source",
        )


def test_registered_wrapper_without_audited_runner_remains_unproved():
    with pytest.raises(AssertionError, match="unmapped successor assertion.*focus.*mixed-verified-and-unverified"):
        wrappers.test_r3_successor_03c11585efe153827572()


@pytest.mark.parametrize("assertion_ref,runner_name", [
    ("assertion:safety-and-contracts-no-raw-phrase-equality-dispatch-in-runtime-source", "test_r1_runtime_has_no_raw_phrase_equality_dispatch"),
    ("assertion:safety-and-contracts-recursive-graph-cycle-rejected", "test_r2_semantic_expression_rejects_application_cycle"),
    ("assertion:safety-and-contracts-safe-artifact-contract-replaces-legacy-checkpoint", "test_r1_safe_artifact_contract_has_no_legacy_checkpoint_api"),
], ids=["phrase-dispatch", "application-cycle", "checkpoint-api"])
def test_exact_runner_is_invoked_each_time_and_failure_is_not_cached(monkeypatch, assertion_ref, runner_name):
    calls = []

    def record_call():
        calls.append(runner_name)

    monkeypatch.setattr(safety, runner_name, record_call)
    routing.assert_successor_contract("safety", assertion_ref)
    routing.assert_successor_contract("safety", assertion_ref)
    assert calls == [runner_name, runner_name]

    def failed_runner():
        raise AssertionError("assertion-specific runner failure")

    monkeypatch.setattr(safety, runner_name, failed_runner)
    with pytest.raises(AssertionError, match="assertion-specific runner failure"):
        routing.assert_successor_contract("safety", assertion_ref)


@pytest.mark.parametrize("assertion_ref", [
    "assertion:safety-and-contracts-no-raw-phrase-equality-dispatch-in-runtime-source",
    "assertion:safety-and-contracts-recursive-graph-cycle-rejected",
    "assertion:safety-and-contracts-safe-artifact-contract-replaces-legacy-checkpoint",
], ids=["phrase-dispatch", "application-cycle", "checkpoint-api"])
def test_mapped_assertion_executes_its_real_current_runner(assertion_ref):
    routing.assert_successor_contract("safety", assertion_ref)
