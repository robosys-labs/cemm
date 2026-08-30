from __future__ import annotations

from copy import deepcopy

import pytest

from cemm_authoritative_hybrid.r4_review_context import ReviewContextMaterial


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
