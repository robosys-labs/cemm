"""Exact Gap Receipt ABI 1 and disabled-later-owner seam tests."""

from __future__ import annotations

from contextlib import contextmanager

import dataclasses
from dataclasses import replace

import pytest

import cemm_authoritative_hybrid.gaps as gaps_module
from cemm_authoritative_hybrid.gaps import (
    GapClassifier,
    GapKind,
    GapReceipt,
    LaterOwnerNotAdmitted,
    MissingOwner,
    ReferenceAmbiguity,
    RepairOwner,
)


def _receipt(**changes: object) -> GapReceipt:
    values: dict[str, object] = {
        "kind": GapKind.IMPLEMENTATION,
        "status": "later_owner_not_admitted",
        "source_refs": ("verified_meaning:one",),
        "blockers": ("later_owner_not_admitted",),
        "missing_contract_refs": ("contract:r3:evaluate",),
        "rejected_candidate_refs": (),
        "recommended_owner": RepairOwner.RUNTIME,
        "safe_response_action": "stop_without_surface",
    }
    values.update(changes)
    return GapReceipt.create(**values)  # type: ignore[arg-type]


def test_gap_receipt_identity_covers_every_semantic_field() -> None:
    original = _receipt()
    changes = (
        ("kind", GapKind.VERIFICATION),
        ("status", "verification_failed"),
        ("source_refs", ("verified_meaning:two",)),
        ("blockers", ("different_blocker",)),
        ("missing_contract_refs", ("contract:r3:alternate",)),
        ("rejected_candidate_refs", ("candidate:one",)),
        ("recommended_owner", RepairOwner.AUTHORITY),
        ("safe_response_action", "reject_candidate"),
    )
    for field, replacement in changes:
        changed = _receipt(**{field: replacement})
        assert changed.gap_ref != original.gap_ref

def test_gap_receipt_round_trip_and_determinism() -> None:
    first = _receipt()
    second = _receipt()
    assert first.gap_ref == second.gap_ref
    assert GapReceipt.from_dict(first.as_dict()) == first


def test_gap_receipt_rejects_stored_and_direct_ref_forgery() -> None:
    receipt = _receipt()
    wire = receipt.as_dict()
    wire["gap_ref"] = "gap:forged"
    with pytest.raises(ValueError, match="gap_ref mismatch"):
        GapReceipt.from_dict(wire)
    with pytest.raises(ValueError, match="gap_ref mismatch"):
        replace(receipt, gap_ref="gap:forged")


def test_gap_receipt_rejects_hostile_wire_before_hashing(monkeypatch) -> None:
    wire = _receipt().as_dict()
    wire["source_refs"] = ["source:x"] * 65

    def forbidden_hash(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("hostile GapReceipt wire reached stable_ref")

    monkeypatch.setattr(gaps_module, "stable_ref", forbidden_hash)
    with pytest.raises(ValueError, match="source_refs exceeds"):
        GapReceipt.from_dict(wire)


def test_gap_receipt_create_rejects_noncanonical_python_types() -> None:
    invalid_values = (
        ("source_refs", ["verified_meaning:one"]),
        ("blockers", ["later_owner_not_admitted"]),
        ("missing_contract_refs", ["contract:r3:evaluate"]),
        ("rejected_candidate_refs", ["candidate:one"]),
        ("kind", "implementation"),
        ("recommended_owner", "runtime"),
    )
    for field, value in invalid_values:
        with pytest.raises(TypeError):
            _receipt(**{field: value})

def test_gap_receipt_rejects_duplicate_ordered_codes_and_refs() -> None:
    for field in (
        "source_refs",
        "blockers",
        "missing_contract_refs",
        "rejected_candidate_refs",
    ):
        with pytest.raises(ValueError, match="duplicates"):
            _receipt(**{field: ("duplicate:x", "duplicate:x")})


def test_later_owner_not_admitted_has_exact_verified_meaning_lineage() -> None:
    exc = LaterOwnerNotAdmitted(
        verified_meaning_ref="verified_meaning:one",
        contract_ref="contract:r3:evaluate",
    )
    receipt = GapClassifier().classify(exc)
    assert receipt.kind is GapKind.IMPLEMENTATION
    assert receipt.status == "later_owner_not_admitted"
    assert receipt.source_refs == ("verified_meaning:one",)
    assert receipt.blockers == ("later_owner_not_admitted",)
    assert receipt.missing_contract_refs == ("contract:r3:evaluate",)
    assert receipt.rejected_candidate_refs == ()
    assert receipt.recommended_owner is RepairOwner.RUNTIME
    assert receipt.safe_response_action == "stop_without_surface"


def test_later_owner_gap_is_deterministic_and_contract_sensitive() -> None:
    classifier = GapClassifier()
    first = classifier.classify(
        LaterOwnerNotAdmitted("verified_meaning:one", "contract:r3:evaluate")
    )
    repeated = classifier.classify(
        LaterOwnerNotAdmitted("verified_meaning:one", "contract:r3:evaluate")
    )
    other_contract = classifier.classify(
        LaterOwnerNotAdmitted("verified_meaning:one", "contract:r5:realize")
    )
    assert first.gap_ref == repeated.gap_ref
    assert first.gap_ref != other_contract.gap_ref


def test_typed_gap_exception_propagates_through_context_manager() -> None:
    @contextmanager
    def boundary():
        yield

    with pytest.raises(MissingOwner, match="proposal"):
        with boundary():
            raise MissingOwner("proposal")

def test_reference_ambiguity_preserves_ordered_candidate_refs() -> None:
    candidates = ("candidate:first", "candidate:second")
    receipt = GapClassifier().classify(
        ReferenceAmbiguity("reference:one", candidates)
    )
    reversed_receipt = GapClassifier().classify(
        ReferenceAmbiguity("reference:one", tuple(reversed(candidates)))
    )
    assert receipt.rejected_candidate_refs == candidates
    assert receipt.gap_ref != reversed_receipt.gap_ref

def test_gap_receipt_abi1_successor_is_frozen_dataclass() -> None:
    receipt = GapReceipt.create(
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
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.kind = GapKind.EVIDENCE  # type: ignore[misc]

__cemm_test_inventory__ = {'tests/test_gap_receipt_abi1.py::test_gap_receipt_abi1_successor_is_frozen_dataclass': {'activation_phase': 'R1',
                                                                                         'assertion_ref': 'assertion:gap-receipts-gap-receipt-is-frozen-dataclass',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R1-Slice-C1',
                                                                                         'owner_ref': 'cycle-result',
                                                                                         'source_ast_sha256': '4f47f5a54623adf1957805b44c09d3ff920345055a648f892fa3884bb73a50dc',
                                                                                         'supersedes_node_id': 'tests/test_gap_receipts.py::test_gap_receipt_is_frozen_dataclass'},
 'tests/test_gap_receipt_abi1.py::test_gap_receipt_create_rejects_noncanonical_python_types': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-gap-create-exact-types',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Slice-C1',
                                                                                               'owner_ref': 'cycle-result',
                                                                                               'source_ast_sha256': '7add87b4b6aa20d44a785f107e17540c2dd81b359f7f9a106072cec554186060'},
 'tests/test_gap_receipt_abi1.py::test_gap_receipt_identity_covers_every_semantic_field': {'activation_phase': 'R1',
                                                                                           'assertion_ref': 'assertion:r1-gap-full-content-identity',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R1-Slice-C1',
                                                                                           'owner_ref': 'cycle-result',
                                                                                           'source_ast_sha256': '6128d548e9b77990d3912e356c94c8d88e0760d3291986cb25dcc4501402a73d'},
 'tests/test_gap_receipt_abi1.py::test_gap_receipt_rejects_duplicate_ordered_codes_and_refs': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-gap-rejects-duplicate-rows',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Slice-C1',
                                                                                               'owner_ref': 'cycle-result',
                                                                                               'source_ast_sha256': '0b592922a568af83d2c95163f81f1c29fc2e2d1ea7221a102c46122123d9cdcd'},
 'tests/test_gap_receipt_abi1.py::test_gap_receipt_rejects_hostile_wire_before_hashing': {'activation_phase': 'R1',
                                                                                          'assertion_ref': 'assertion:r1-gap-prehash-wire-bound',
                                                                                          'diagnostic_role': 'owner',
                                                                                          'introduced_by_task': 'R1-Slice-C1',
                                                                                          'owner_ref': 'cycle-result',
                                                                                          'source_ast_sha256': 'b696764847bd9b83808abf9c73261ac37d7f27092bda9fe776e4cd6501f37b90'},
 'tests/test_gap_receipt_abi1.py::test_gap_receipt_rejects_stored_and_direct_ref_forgery': {'activation_phase': 'R1',
                                                                                            'assertion_ref': 'assertion:r1-gap-rejects-ref-forgery',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R1-Slice-C1',
                                                                                            'owner_ref': 'cycle-result',
                                                                                            'source_ast_sha256': '072f529cc0a6390098f9ace30042de2fdbeff4397b0f53df13e891e8b8ae173f'},
 'tests/test_gap_receipt_abi1.py::test_gap_receipt_round_trip_and_determinism': {'activation_phase': 'R1',
                                                                                 'assertion_ref': 'assertion:r1-gap-roundtrip-deterministic',
                                                                                 'diagnostic_role': 'owner',
                                                                                 'introduced_by_task': 'R1-Slice-C1',
                                                                                 'owner_ref': 'cycle-result',
                                                                                 'source_ast_sha256': '6f15de8930b633f08d5fb07b375c1868650d73e5256a4e6cc21675a8426be7f3'},
 'tests/test_gap_receipt_abi1.py::test_later_owner_gap_is_deterministic_and_contract_sensitive': {'activation_phase': 'R1',
                                                                                                  'assertion_ref': 'assertion:r1-later-owner-contract-sensitive',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R1-Slice-C1',
                                                                                                  'owner_ref': 'cycle-result',
                                                                                                  'source_ast_sha256': '1bfbb2e104587ac5417c62ec4ed1063d100450b8cb29a337a6d269656b7ac0ac'},
 'tests/test_gap_receipt_abi1.py::test_later_owner_not_admitted_has_exact_verified_meaning_lineage': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-later-owner-exact-lineage',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Slice-C1',
                                                                                                      'owner_ref': 'cycle-result',
                                                                                                      'source_ast_sha256': 'd25897867ee032df6ed0a757c2f579ebd8205633ccce23a946d22d9064d17581'},
 'tests/test_gap_receipt_abi1.py::test_reference_ambiguity_preserves_ordered_candidate_refs': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-gap-reference-candidate-lineage',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Slice-C1',
                                                                                               'owner_ref': 'cycle-result',
                                                                                               'source_ast_sha256': '9433615decd35e6c97da475107d2d71208864a8d3ff4eb63ebd26798c3268190'},
 'tests/test_gap_receipt_abi1.py::test_typed_gap_exception_propagates_through_context_manager': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-gap-exception-standard-propagation',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-9',
                                                                                                 'owner_ref': 'cycle-result',
                                                                                                 'source_ast_sha256': '5d3cdb62890afb8f7ce08cd47f026b88fa6a01fb4f02bc479194fe3e64f36673'}}
