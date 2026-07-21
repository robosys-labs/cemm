from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from cemm.v350.identity import (
    IdempotencyOutcome,
    classify_persisted_identity,
)
from cemm.v350.runtime_authority import (
    AttestedRuntimeAuthority,
    RuntimeAttestation,
    RuntimeAttestationError,
)
from cemm.v350.storage import EvidenceRecord, RecordKind
from cemm.v350.storage.codec import record_fingerprints
from cemm.v350.storage.model import StoredRecord


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class _Manifest:
    release_version: str = "3.5.0"
    release_commit: str = "a" * 40
    source_manifest_sha256: str = "b" * 64
    boot_database_sha256: str = "c" * 64
    verification_report_sha256: str = "d" * 64
    legacy_denylist_sha256: str = "e" * 64
    canonical_runtime_factory: str = "builtins:dict"
    canonical_orchestrator: str = "cemm.v350.orchestration:CanonicalOrchestrator"
    forbidden_runtime_import_prefixes: tuple[str, ...] = (
        "cemm.v347",
        "cemm.migration",
    )


class _Guard:
    def __init__(self):
        self.manifest = _Manifest()
        self.full_verification_calls = 0
        self.stage_checks = 0

    def require_service_authority(self):
        self.full_verification_calls += 1

    def require_stage_adapter(self, *, stage, adapter_ref, adapter_revision):
        self.stage_checks += 1


def _evidence(value: str = "operational") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_ref="evidence:test",
        source_ref="source:test",
        confidence=1.0,
        lineage_ref="source:test",
        metadata={"value": value},
    )


def test_runtime_attestation_runs_full_guard_once_then_hot_checks_are_o1():
    guard = _Guard()
    authority = AttestedRuntimeAuthority.verify_reload(guard)
    assert guard.full_verification_calls == 1

    for _ in range(100):
        authority.require_service_authority()

    assert guard.full_verification_calls == 1
    assert authority.runtime_epoch.generation == 1
    assert authority.attestation.release_commit == guard.manifest.release_commit


def test_reload_verifies_again_advances_generation_and_invalidates_old_epoch():
    first_guard = _Guard()
    first = AttestedRuntimeAuthority.verify_reload(first_guard)
    second_guard = _Guard()
    second = AttestedRuntimeAuthority.verify_reload(
        second_guard, previous=first
    )

    assert first_guard.full_verification_calls == 1
    assert second_guard.full_verification_calls == 1
    assert second.runtime_epoch.generation == 2
    assert second.runtime_epoch.epoch_ref != first.runtime_epoch.epoch_ref
    with pytest.raises(RuntimeAttestationError):
        first.require_service_authority()


def test_attestation_detects_in_memory_manifest_identity_change():
    guard = _Guard()
    authority = AttestedRuntimeAuthority.verify_reload(guard)
    guard.manifest.release_commit = "f" * 40
    with pytest.raises(RuntimeAttestationError):
        authority.require_service_authority()


def test_canonical_persisted_identity_is_fingerprint_based_not_object_equality():
    record = _evidence()
    content_fp, record_fp = record_fingerprints(RecordKind.EVIDENCE, record)
    stored = StoredRecord(
        record_kind=RecordKind.EVIDENCE,
        record_ref=record.evidence_ref,
        revision=1,
        payload=record,
        content_fingerprint=content_fp,
        record_fingerprint=record_fp,
        layer="overlay",
        store_revision=1,
    )
    equivalent = classify_persisted_identity(
        stored, RecordKind.EVIDENCE, _evidence(), revision=1
    )
    conflict = classify_persisted_identity(
        stored, RecordKind.EVIDENCE, _evidence("degraded"), revision=1
    )
    assert equivalent.outcome is IdempotencyOutcome.EQUIVALENT
    assert conflict.outcome is IdempotencyOutcome.CONFLICT


def test_public_runtime_does_not_run_full_release_guard_per_turn():
    source = (ROOT / "cemm/v350/public_runtime.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    run_text = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Runtime"
        for node in node.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_text"
    )
    calls = [
        node
        for node in ast.walk(run_text)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "require_service_authority"
    ]
    assert not calls


def test_phase0_machine_readable_contracts_exist_and_reference_acceptance():
    registry = ROOT / "docs/implementation/v351_phase0_defect_registry.json"
    matrix = ROOT / "docs/acceptance_matrix.json"
    baseline = ROOT / "docs/baselines/v351_phase0_baseline_spec.json"
    assert registry.is_file()
    assert matrix.is_file()
    assert baseline.is_file()
