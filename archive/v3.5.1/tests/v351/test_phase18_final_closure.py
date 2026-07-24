from __future__ import annotations

from cemm.v350.finalization.closure_v351 import (
    ClosureGateResultV351, GateStatus, Phase18ClosureLedgerV351, REQUIRED_PHASE18_GATES,
)
from cemm.v350.finalization.shadow_v351 import compare_shadow_capture_v351


def test_missing_gate_is_not_implicitly_passed():
    ledger = Phase18ClosureLedgerV351(
        release_commit="a" * 40,
        authority_payload_sha256="b" * 64,
        boot_database_sha256="c" * 64,
        runtime_source_root_sha256="d" * 64,
        gates=(),
    )
    assert not ledger.complete
    assert set(ledger.missing_or_failed) == set(REQUIRED_PHASE18_GATES)


def test_complete_ledger_requires_every_gate_pass():
    gates = tuple(
        ClosureGateResultV351(gate, GateStatus.PASS, "e" * 64, f"evidence/{gate}.json")
        for gate in REQUIRED_PHASE18_GATES
    )
    ledger = Phase18ClosureLedgerV351("a" * 40, "b" * 64, "c" * 64, "d" * 64, gates)
    assert ledger.complete


def test_shadow_missing_is_not_equal_to_explicit_null():
    base = {
        "grounding": None, "canonical_meaning": {}, "query_bindings": {},
        "epistemic_placement": {}, "durable_deltas": {}, "frontiers": [],
        "response_semantics": {}, "realization": {}, "latency": 1.0, "storage_volume": 1.0,
    }
    new = dict(base)
    del new["grounding"]
    report = compare_shadow_capture_v351(base, new)
    assert report["status"] == "fail"
    assert report["comparisons"]["grounding"]["equal"] is False


def test_shadow_metrics_use_threshold_not_exact_equality():
    base = {
        "grounding": {}, "canonical_meaning": {}, "query_bindings": {},
        "epistemic_placement": {}, "durable_deltas": {}, "frontiers": [],
        "response_semantics": {}, "realization": {}, "latency": 100.0, "storage_volume": 100.0,
    }
    new = dict(base, latency=110.0, storage_volume=110.0)
    report = compare_shadow_capture_v351(base, new)
    assert report["status"] == "pass"
