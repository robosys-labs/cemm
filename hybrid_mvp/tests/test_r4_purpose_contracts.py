from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cemm_authoritative_hybrid.r4_purpose import (
    MAX_DENOMINATOR_MINIMA,
    ChallengeHoldout,
    DenominatorMinimum,
    DuplicateRiskGroup,
    PurposeContract,
    PurposeMembership,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/r4_purpose_contract.schema.json"
REVIEW_REF = "source_review:0123456789abcdef01234567"
CASE_REFS = tuple(
    f"expanded_case_v2:{index:024x}" for index in range(1, 6)
)


def _memberships() -> tuple[PurposeMembership, ...]:
    return (
        PurposeMembership.create(
            source_case_ref=CASE_REFS[0],
            classification="semantic_supervision",
            purpose="train",
            duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        ),
        PurposeMembership.create(
            source_case_ref=CASE_REFS[1],
            classification="semantic_supervision",
            purpose="train",
            duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        ),
        PurposeMembership.create(
            source_case_ref=CASE_REFS[2],
            classification="typed_abstention",
            purpose="selection",
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        ),
        PurposeMembership.create(
            source_case_ref=CASE_REFS[3],
            classification="semantic_supervision",
            purpose="calibration",
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        ),
        PurposeMembership.create(
            source_case_ref=CASE_REFS[4],
            classification="semantic_supervision",
            purpose="frozen_test",
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        ),
    )


def _minima() -> tuple[DenominatorMinimum, ...]:
    return tuple(
        DenominatorMinimum.create(
            denominator_ref=f"denominator:semantic-expression-{purpose}",
            denominator_family="semantic_expression",
            purpose=purpose,
            minimum=1,
            review_refs=(REVIEW_REF,),
        )
        for purpose in ("train", "selection", "calibration", "frozen_test")
    )


def _contract() -> PurposeContract:
    return PurposeContract.create(
        source_set_ref="r4_source_set_v1:0123456789abcdef01234567",
        memberships=_memberships(),
        duplicate_risk_groups=(
            DuplicateRiskGroup.create(
                group_ref="duplicate_risk_group:family-a",
                namespace="paraphrase_family",
                member_case_refs=CASE_REFS[:2],
                reason_ref="duplicate_reason:reviewed-paraphrase",
                review_refs=(REVIEW_REF,),
            ),
        ),
        challenge_holdouts=(
            ChallengeHoldout.create(
                holdout_ref="challenge_holdout:selection-gap",
                identity_namespace="semantic_identity",
                identity_ref="gap_kind:unresolved_designation",
                purpose="selection",
                member_case_refs=(CASE_REFS[2],),
                reason_ref="holdout_reason:unseen-gap",
                review_refs=(REVIEW_REF,),
            ),
        ),
        denominator_minima=_minima(),
        review_refs=(REVIEW_REF,),
        solver_output_is_authority=False,
    )


@pytest.mark.parametrize(
    "value",
    (
        _memberships()[0],
        DuplicateRiskGroup.create(
            group_ref="duplicate_risk_group:family-a",
            namespace="paraphrase_family",
            member_case_refs=CASE_REFS[:2],
            reason_ref="duplicate_reason:reviewed-paraphrase",
            review_refs=(REVIEW_REF,),
        ),
        ChallengeHoldout.create(
            holdout_ref="challenge_holdout:selection-gap",
            identity_namespace="semantic_identity",
            identity_ref="gap_kind:unresolved_designation",
            purpose="selection",
            member_case_refs=(CASE_REFS[2],),
            reason_ref="holdout_reason:unseen-gap",
            review_refs=(REVIEW_REF,),
        ),
        _minima()[0],
        _contract(),
    ),
    ids=["value0", "value1", "value2", "value3", "value4"],
)
def test_purpose_values_are_factory_only_frozen_and_canonical(value) -> None:
    with pytest.raises(TypeError, match="use .*create"):
        type(value)()
    with pytest.raises(FrozenInstanceError):
        value.abi_version = 99
    if type(value) is PurposeContract:
        assert PurposeContract.from_json_bytes(value.to_json_bytes()) == value
    else:
        assert type(value).from_dict(value.as_dict()) == value


def test_membership_classification_is_total_and_diagnostic_rows_never_enter_a_purpose() -> None:
    with pytest.raises(ValueError, match="diagnostic-only"):
        PurposeMembership.create(
            source_case_ref=CASE_REFS[0],
            classification="diagnostic_only",
            purpose="train",
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref="diagnostic_reason:comparison-only",
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="diagnostic reason"):
        PurposeMembership.create(
            source_case_ref=CASE_REFS[0],
            classification="diagnostic_only",
            purpose=None,
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="supervised"):
        PurposeMembership.create(
            source_case_ref=CASE_REFS[0],
            classification="semantic_supervision",
            purpose=None,
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        )


def test_duplicate_groups_are_explicit_reviewed_lineage_not_semantic_union_keys() -> None:
    for forbidden in (
        "operator",
        "role",
        "mode",
        "semantic_target",
        "topology",
        "response_action",
    ):
        with pytest.raises(ValueError, match="duplicate-risk namespace"):
            DuplicateRiskGroup.create(
                group_ref="duplicate_risk_group:bad",
                namespace=forbidden,
                member_case_refs=CASE_REFS[:2],
                reason_ref="duplicate_reason:bad",
                review_refs=(REVIEW_REF,),
            )

    with pytest.raises(ValueError, match="unique refs"):
        DuplicateRiskGroup.create(
            group_ref="duplicate_risk_group:duplicate",
            namespace="mutation_lineage",
            member_case_refs=(CASE_REFS[0], CASE_REFS[0]),
            reason_ref="duplicate_reason:mutation",
            review_refs=(REVIEW_REF,),
        )


def test_purpose_contract_rejects_duplicate_unknown_and_cross_purpose_group_members() -> None:
    contract = _contract()
    with pytest.raises(ValueError, match="duplicate source case"):
        PurposeContract.create(
            source_set_ref=contract.source_set_ref,
            memberships=contract.memberships + (contract.memberships[0],),
            duplicate_risk_groups=contract.duplicate_risk_groups,
            challenge_holdouts=contract.challenge_holdouts,
            denominator_minima=contract.denominator_minima,
            review_refs=contract.review_refs,
            solver_output_is_authority=False,
        )

    changed = list(contract.memberships)
    changed[1] = PurposeMembership.create(
        source_case_ref=CASE_REFS[1],
        classification="semantic_supervision",
        purpose="selection",
        duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
        diagnostic_reason_ref=None,
        review_refs=(REVIEW_REF,),
    )
    with pytest.raises(ValueError, match="one purpose"):
        PurposeContract.create(
            source_set_ref=contract.source_set_ref,
            memberships=tuple(changed),
            duplicate_risk_groups=contract.duplicate_risk_groups,
            challenge_holdouts=contract.challenge_holdouts,
            denominator_minima=contract.denominator_minima,
            review_refs=contract.review_refs,
            solver_output_is_authority=False,
        )

    bad_group = DuplicateRiskGroup.create(
        group_ref="duplicate_risk_group:unknown-case",
        namespace="source_case_lineage",
        member_case_refs=(CASE_REFS[0], "expanded_case_v2:ffffffffffffffffffffffff"),
        reason_ref="duplicate_reason:lineage",
        review_refs=(REVIEW_REF,),
    )
    with pytest.raises(ValueError, match="unknown source case"):
        PurposeContract.create(
            source_set_ref=contract.source_set_ref,
            memberships=contract.memberships,
            duplicate_risk_groups=(bad_group,),
            challenge_holdouts=contract.challenge_holdouts,
            denominator_minima=contract.denominator_minima,
            review_refs=contract.review_refs,
            solver_output_is_authority=False,
        )


def test_challenge_holdouts_are_separate_reviewed_identity_contracts() -> None:
    with pytest.raises(ValueError, match="challenge identity namespace"):
        ChallengeHoldout.create(
            holdout_ref="challenge_holdout:raw",
            identity_namespace="raw_surface",
            identity_ref="surface:lamp",
            purpose="selection",
            member_case_refs=(CASE_REFS[2],),
            reason_ref="holdout_reason:bad",
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="challenge identity namespace"):
        ChallengeHoldout.create(
            holdout_ref="challenge_holdout:spelling",
            identity_namespace="internal_ref_spelling",
            identity_ref="operator:spelling",
            purpose="selection",
            member_case_refs=(CASE_REFS[2],),
            reason_ref="holdout_reason:bad",
            review_refs=(REVIEW_REF,),
        )


def test_denominator_minima_are_fixed_positive_finite_and_bounded() -> None:
    with pytest.raises((TypeError, ValueError), match="minimum"):
        DenominatorMinimum.create(
            denominator_ref="denominator:bad-zero",
            denominator_family="semantic_expression",
            purpose="train",
            minimum=0,
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises((TypeError, ValueError), match="minimum"):
        DenominatorMinimum.create(
            denominator_ref="denominator:bad-nan",
            denominator_family="semantic_expression",
            purpose="train",
            minimum=float("nan"),
            review_refs=(REVIEW_REF,),
        )

    minimum = _minima()[0]
    with pytest.raises(ValueError, match="denominator bound"):
        PurposeContract.create(
            source_set_ref="r4_source_set_v1:0123456789abcdef01234567",
            memberships=_memberships(),
            duplicate_risk_groups=_contract().duplicate_risk_groups,
            challenge_holdouts=_contract().challenge_holdouts,
            denominator_minima=tuple(minimum for _ in range(MAX_DENOMINATOR_MINIMA + 1)),
            review_refs=(REVIEW_REF,),
            solver_output_is_authority=False,
        )


def test_purpose_contract_rejects_solver_authority_unknown_missing_abi_and_noncanonical_json() -> None:
    contract = _contract()
    value = contract.as_dict()

    with pytest.raises(ValueError, match="solver output"):
        PurposeContract.create(
            source_set_ref=contract.source_set_ref,
            memberships=contract.memberships,
            duplicate_risk_groups=contract.duplicate_risk_groups,
            challenge_holdouts=contract.challenge_holdouts,
            denominator_minima=contract.denominator_minima,
            review_refs=contract.review_refs,
            solver_output_is_authority=True,
        )

    for corrupt in (
        {**deepcopy(value), "abi_version": 2},
        {key: item for key, item in deepcopy(value).items() if key != "review_refs"},
        {**deepcopy(value), "solver_receipt_ref": "solver:forbidden"},
    ):
        with pytest.raises((TypeError, ValueError)):
            PurposeContract.from_dict(corrupt)

    raw = contract.to_json_bytes()
    duplicate = raw.replace(b'{"abi_version":1,', b'{"abi_version":1,"abi_version":1,', 1)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        PurposeContract.from_json_bytes(duplicate)
    pretty = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    with pytest.raises(ValueError, match="not canonical"):
        PurposeContract.from_json_bytes(pretty)


def test_purpose_schema_is_strict_draft_2020_12_and_matches_decoder() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    def assert_strict_objects(value: object) -> None:
        if type(value) is dict:
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
            for child in value.values():
                assert_strict_objects(child)
        elif type(value) is list:
            for child in value:
                assert_strict_objects(child)

    assert_strict_objects(schema)
    validator = Draft202012Validator(schema)
    contract = _contract()
    wire = contract.as_dict()
    assert validator.is_valid(wire)
    assert PurposeContract.from_dict(deepcopy(wire)) == contract

    for corrupt in (
        {**deepcopy(wire), "abi_version": 9},
        {key: item for key, item in deepcopy(wire).items() if key != "memberships"},
        {**deepcopy(wire), "unknown": []},
    ):
        assert not validator.is_valid(corrupt)
        with pytest.raises((TypeError, ValueError)):
            PurposeContract.from_dict(corrupt)


__cemm_test_inventory__ = {'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value0]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': '51d31b8ffb10c3233f81f685500854db4b920912161ff957d41b609cb52381f0'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value1]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': '51d31b8ffb10c3233f81f685500854db4b920912161ff957d41b609cb52381f0'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value2]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': '51d31b8ffb10c3233f81f685500854db4b920912161ff957d41b609cb52381f0'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value3]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': '51d31b8ffb10c3233f81f685500854db4b920912161ff957d41b609cb52381f0'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value4]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': '51d31b8ffb10c3233f81f685500854db4b920912161ff957d41b609cb52381f0'},
 'tests/test_r4_purpose_contracts.py::test_membership_classification_is_total_and_diagnostic_rows_never_enter_a_purpose': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:r4-purpose-membership-total-diagnostic-isolated',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                                           'source_ast_sha256': '8c5465694f4861d27e48dfe93d4b0b92604fa2d12ddefd773a1070d5521999d0'},
 'tests/test_r4_purpose_contracts.py::test_duplicate_groups_are_explicit_reviewed_lineage_not_semantic_union_keys': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:r4-duplicate-groups-reviewed-lineage-not-semantic-union',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                     'owner_ref': 'mutation-partition',
                                                                                                                     'source_ast_sha256': '7f797f45e898e9b273ae56293ba4a06fa5a739080a1c8345200b57095732d188'},
 'tests/test_r4_purpose_contracts.py::test_purpose_contract_rejects_duplicate_unknown_and_cross_purpose_group_members': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-purpose-contract-rejects-duplicate-unknown-cross-purpose',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                                         'source_ast_sha256': '882b042fb8e3ec453430335d3cbb42293385c54030f1aae83abeab4f56fadb36'},
 'tests/test_r4_purpose_contracts.py::test_challenge_holdouts_are_separate_reviewed_identity_contracts': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-challenge-holdouts-separate-reviewed-identity',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                          'owner_ref': 'mutation-partition',
                                                                                                          'source_ast_sha256': '13a7e9a3b600807ae2f269b5dd8f3e19330a9c25f19d093e28fd0a60ce23747e'},
 'tests/test_r4_purpose_contracts.py::test_denominator_minima_are_fixed_positive_finite_and_bounded': {'activation_phase': 'R4',
                                                                                                       'assertion_ref': 'assertion:r4-denominator-minima-fixed-positive-finite-bounded',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                       'owner_ref': 'mutation-partition',
                                                                                                       'source_ast_sha256': 'b741c0b46aaaa468bb4104bd2d0b8b8dc29473e6d84b308eb107e320eb490a11'},
 'tests/test_r4_purpose_contracts.py::test_purpose_contract_rejects_solver_authority_unknown_missing_abi_and_noncanonical_json': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:r4-purpose-contract-rejects-solver-unknown-missing-noncanonical',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                                                  'source_ast_sha256': '3ee9cd1ca4796d53cdfd64c8cc9458fa56198843556d37f0f7a0740559310ef4'},
 'tests/test_r4_purpose_contracts.py::test_purpose_schema_is_strict_draft_2020_12_and_matches_decoder': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-purpose-schema-draft-2020-12-decoder-parity',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                         'source_ast_sha256': 'c9c016d103e08046754b4e2e343f4ece1d0a9bae9b9c1ec8f802ff833e6a8e07'}}
