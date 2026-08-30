"""Bounded worksheet-local R4 authoring records."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cemm_authoritative_hybrid.r4_authoring import (
    AuthoringCandidate,
    AuthoringRecipe,
    validate_authoring_recipes,
)

CASE_A = "expanded_case_v2:0123456789abcdef01234567"
CASE_B = "expanded_case_v2:1123456789abcdef01234567"
REVIEW = "source_review:0123456789abcdef01234567"
CONTEXT = "review_context_v1:0123456789abcdef01234567"


def _recipe(**overrides) -> AuthoringRecipe:
    values = {
        "recipe_kind": "proposal",
        "purpose": "train",
        "normalized_family_key": ("single", "mode:observe", {"op": "op:event"}),
        "member_case_refs": (CASE_A,),
        "ancestry_refs": (),
        "reviewed_parameters": {"target_kind": "derive"},
        "review_refs": (REVIEW,),
    }
    values.update(overrides)
    return AuthoringRecipe.create(**values)


def test_candidate_envelope_is_inert_complete_and_content_addressed() -> None:
    recipe = _recipe()
    candidate = AuthoringCandidate.create(
        candidate_kind="proposal",
        source_case_ref=CASE_A,
        purpose="train",
        recipe_ref=recipe.recipe_ref,
        input_refs=("r4_input_set_v1:0123456789abcdef01234567",),
        evidence_refs=(),
        generator_source_ref="generator_source:0123456789abcdef01234567",
        provenance_refs=(CONTEXT,),
        verification_receipt_ref="authoring_verification:0123456789abcdef01234567",
        selectable=False,
        exception_codes=("awaiting_review",),
        proposed_row=None,
    )
    assert candidate.selectable is False
    assert candidate.proposed_row is None
    changed = AuthoringCandidate.create(
        candidate_kind=candidate.candidate_kind,
        source_case_ref=candidate.source_case_ref,
        purpose=candidate.purpose,
        recipe_ref=candidate.recipe_ref,
        input_refs=candidate.input_refs,
        evidence_refs=("evidence_snapshot_v1:0123456789abcdef01234567",),
        generator_source_ref=candidate.generator_source_ref,
        provenance_refs=candidate.provenance_refs,
        verification_receipt_ref=candidate.verification_receipt_ref,
        selectable=candidate.selectable,
        exception_codes=candidate.exception_codes,
        proposed_row=candidate.proposed_row,
    )
    assert changed.candidate_ref != candidate.candidate_ref


def test_recipe_records_are_frozen_closed_and_normalized() -> None:
    recipe = _recipe()
    with pytest.raises(FrozenInstanceError):
        recipe.purpose = "selection"
    with pytest.raises(TypeError, match="use AuthoringRecipe.create"):
        AuthoringRecipe()
    with pytest.raises(ValueError, match="recipe kind"):
        _recipe(recipe_kind="runtime_branch")
    with pytest.raises(ValueError, match="purpose"):
        _recipe(purpose="unknown")
    with pytest.raises(ValueError, match="member_case_refs"):
        _recipe(member_case_refs=(CASE_A, CASE_A))


def test_recipe_inventory_rejects_family_collisions_and_cross_purpose_membership() -> None:
    base = _recipe()
    collision = _recipe(
        member_case_refs=(CASE_B,),
        reviewed_parameters={"target_kind": "abstain"},
    )
    with pytest.raises(ValueError, match="family-key collision"):
        validate_authoring_recipes((base, collision))

    frozen = _recipe(
        purpose="frozen_test",
        normalized_family_key=("frozen",),
    )
    with pytest.raises(ValueError, match="case ownership crosses purposes"):
        validate_authoring_recipes((base, frozen))


def test_recipe_family_and_instance_bounds_are_per_kind_and_purpose() -> None:
    rows = tuple(
        _recipe(
            normalized_family_key=("family", index),
            member_case_refs=(f"expanded_case_v2:{index + 1:024x}",),
        )
        for index in range(129)
    )
    with pytest.raises(ValueError, match="128 recipe families"):
        validate_authoring_recipes(rows)

    purposes = ("train", "selection", "calibration", "frozen_test")
    too_many = tuple(
        _recipe(
            purpose=purposes[index % len(purposes)],
            normalized_family_key=("instance", index),
            member_case_refs=(f"expanded_case_v2:{index + 1:024x}",),
        )
        for index in range(513)
    )
    with pytest.raises(ValueError, match="512 purpose-scoped"):
        validate_authoring_recipes(too_many)


def test_selectable_candidate_requires_verified_concrete_row() -> None:
    recipe = _recipe()
    common = {
        "candidate_kind": "proposal",
        "source_case_ref": CASE_A,
        "purpose": "train",
        "recipe_ref": recipe.recipe_ref,
        "input_refs": ("r4_input_set_v1:0123456789abcdef01234567",),
        "evidence_refs": (),
        "generator_source_ref": "generator_source:0123456789abcdef01234567",
        "provenance_refs": (CONTEXT,),
        "verification_receipt_ref": "authoring_verification:0123456789abcdef01234567",
    }
    with pytest.raises(ValueError, match="selectable"):
        AuthoringCandidate.create(
            **common,
            selectable=True,
            exception_codes=(),
            proposed_row=None,
        )
    with pytest.raises(ValueError, match="exception"):
        AuthoringCandidate.create(
            **common,
            selectable=True,
            exception_codes=("awaiting_review",),
            proposed_row={"target_kind": "derive"},
        )
