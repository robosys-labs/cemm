from __future__ import annotations

from copy import deepcopy

import pytest

from cemm_authoritative_hybrid.r4_review_context import ReviewContextMaterial

__cemm_test_inventory__ = {'tests/test_r4_review_context.py::test_review_context_excludes_output_identities': {'activation_phase': 'R4',
                                                                                     'assertion_ref': 'assertion:r4-closure-test-authority-review-context-excludes-output-identities',
                                                                                     'diagnostic_role': 'admission_only',
                                                                                     'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                     'source_ast_sha256': '526d9fc79c925dd4b7c1ec028dafdd5c88f1be9a45776dfc9504acdbd408d3b5'},
 'tests/test_r4_review_context.py::test_every_review_context_input_changes_identity[policy-ref]': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:r4-closure-test-authority-every-review-context-input-changes-identity-policy-ref',
                                                                                                   'diagnostic_role': 'admission_only',
                                                                                                   'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                   'source_ast_sha256': 'd59e507f774f529e59f4d47df09b44be28763d42f604dd089a6256e0ffbe68bb'},
 'tests/test_r4_review_context.py::test_every_review_context_input_changes_identity[policy-hash]': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:r4-closure-test-authority-every-review-context-input-changes-identity-policy-hash',
                                                                                                    'diagnostic_role': 'admission_only',
                                                                                                    'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                    'source_ast_sha256': 'd59e507f774f529e59f4d47df09b44be28763d42f604dd089a6256e0ffbe68bb'},
 'tests/test_r4_review_context.py::test_every_review_context_input_changes_identity[reviewers]': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:r4-closure-test-authority-every-review-context-input-changes-identity-reviewers',
                                                                                                  'diagnostic_role': 'admission_only',
                                                                                                  'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                  'source_ast_sha256': 'd59e507f774f529e59f4d47df09b44be28763d42f604dd089a6256e0ffbe68bb'},
 'tests/test_r4_review_context.py::test_every_review_context_input_changes_identity[base-revision]': {'activation_phase': 'R4',
                                                                                                      'assertion_ref': 'assertion:r4-closure-test-authority-every-review-context-input-changes-identity-base-revision',
                                                                                                      'diagnostic_role': 'admission_only',
                                                                                                      'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                      'source_ast_sha256': 'd59e507f774f529e59f4d47df09b44be28763d42f604dd089a6256e0ffbe68bb'},
 'tests/test_r4_review_context.py::test_every_review_context_input_changes_identity[authority-generation]': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:r4-closure-test-authority-every-review-context-input-changes-identity-authority-generation',
                                                                                                             'diagnostic_role': 'admission_only',
                                                                                                             'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                             'source_ast_sha256': 'd59e507f774f529e59f4d47df09b44be28763d42f604dd089a6256e0ffbe68bb'},
 'tests/test_r4_review_context.py::test_every_review_context_input_changes_identity[form-pack-hash]': {'activation_phase': 'R4',
                                                                                                       'assertion_ref': 'assertion:r4-closure-test-authority-every-review-context-input-changes-identity-form-pack-hash',
                                                                                                       'diagnostic_role': 'admission_only',
                                                                                                       'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                       'source_ast_sha256': 'd59e507f774f529e59f4d47df09b44be28763d42f604dd089a6256e0ffbe68bb'},
 'tests/test_r4_review_context.py::test_every_review_context_input_changes_identity[input-set]': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:r4-closure-test-authority-every-review-context-input-changes-identity-input-set',
                                                                                                  'diagnostic_role': 'admission_only',
                                                                                                  'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                  'source_ast_sha256': 'd59e507f774f529e59f4d47df09b44be28763d42f604dd089a6256e0ffbe68bb'},
 'tests/test_r4_review_context.py::test_review_context_rejects_output_identity_fields': {'activation_phase': 'R4',
                                                                                         'assertion_ref': 'assertion:r4-closure-test-authority-review-context-rejects-output-identity-fields',
                                                                                         'diagnostic_role': 'admission_only',
                                                                                         'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                         'source_ast_sha256': 'b722665d190ddecb96fed996bc375877b598a4c9943dd4847e3e1d6938fa83c7'}}



def _material() -> ReviewContextMaterial:
    return ReviewContextMaterial.create(
        review_policy_ref="review_policy:r4_1_single_accountable_reviewer",
        review_policy_sha256="11" * 32,
        reviewer_refs=("reviewer:son",),
        reviewed_base_revision="22" * 20,
        authority_generation="authority-v1-2026-07-29",
        form_abi_version=7,
        form_pack_sha256="33" * 32,
        input_set_ref="worksheet_input_set:0123456789abcdef01234567",
    )


def test_review_context_excludes_output_identities() -> None:
    row = _material().as_dict()
    assert set(row) == {
        "review_scope",
        "review_policy_ref",
        "review_policy_sha256",
        "reviewer_refs",
        "reviewed_base_revision",
        "authority_generation",
        "form_abi_version",
        "form_pack_sha256",
        "input_set_ref",
        "review_context_ref",
    }
    forbidden = {"worksheet_ref", "row_ref", "manifest_ref", "source_bundle_ref"}
    assert forbidden.isdisjoint(row)
    assert ReviewContextMaterial.from_dict(deepcopy(row)) == _material()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("review_policy_ref", "review_policy:other"),
        ("review_policy_sha256", "44" * 32),
        ("reviewer_refs", ["reviewer:other"]),
        ("reviewed_base_revision", "55" * 20),
        ("authority_generation", "authority-v1-other"),
        ("form_pack_sha256", "66" * 32),
        ("input_set_ref", "worksheet_input_set:ffffffffffffffffffffffff"),
    ],
    ids=(
        "policy-ref",
        "policy-hash",
        "reviewers",
        "base-revision",
        "authority-generation",
        "form-pack-hash",
        "input-set",
    ),
)
def test_every_review_context_input_changes_identity(field: str, value: object) -> None:
    row = _material().as_dict()
    row[field] = value
    row.pop("review_context_ref")
    changed = ReviewContextMaterial.create(
        review_policy_ref=row["review_policy_ref"],
        review_policy_sha256=row["review_policy_sha256"],
        reviewer_refs=tuple(row["reviewer_refs"]),
        reviewed_base_revision=row["reviewed_base_revision"],
        authority_generation=row["authority_generation"],
        form_abi_version=row["form_abi_version"],
        form_pack_sha256=row["form_pack_sha256"],
        input_set_ref=row["input_set_ref"],
    )
    assert changed.review_context_ref != _material().review_context_ref


def test_review_context_rejects_output_identity_fields() -> None:
    row = _material().as_dict()
    row["manifest_ref"] = "r4_review_manifest_v1:0123456789abcdef01234567"
    with pytest.raises((TypeError, ValueError), match="fields mismatch"):
        ReviewContextMaterial.from_dict(row)
