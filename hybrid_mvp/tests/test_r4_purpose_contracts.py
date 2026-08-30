from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
import cemm_authoritative_hybrid.r4_purpose as purpose_module

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
            purpose=None,
            duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        ),
        PurposeMembership.create(
            source_case_ref=CASE_REFS[1],
            classification="semantic_supervision",
            purpose=None,
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
            denominator_ref="denominator:semantic-expression",
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
                purpose="train",
                member_case_refs=CASE_REFS[:2],
                reason_ref="duplicate_reason:reviewed-paraphrase",
                review_refs=(REVIEW_REF,),
            ),
        ),
        challenge_holdouts=(
            ChallengeHoldout.create(
                holdout_ref="challenge_holdout:selection-gap",
                identity_namespace="semantic_identity",
                identity_ref="concept:unresolved-designation",
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


def _recreate_contract(contract: PurposeContract, **changes) -> PurposeContract:
    values = {
        "source_set_ref": contract.source_set_ref,
        "memberships": contract.memberships,
        "duplicate_risk_groups": contract.duplicate_risk_groups,
        "challenge_holdouts": contract.challenge_holdouts,
        "denominator_minima": contract.denominator_minima,
        "review_refs": contract.review_refs,
        "solver_output_is_authority": contract.solver_output_is_authority,
    }
    values.update(changes)
    return PurposeContract.create(**values)


@pytest.mark.parametrize(
    "value",
    (
        _memberships()[0],
        DuplicateRiskGroup.create(
            group_ref="duplicate_risk_group:family-a",
            namespace="paraphrase_family",
            purpose="train",
            member_case_refs=CASE_REFS[:2],
            reason_ref="duplicate_reason:reviewed-paraphrase",
            review_refs=(REVIEW_REF,),
        ),
        ChallengeHoldout.create(
            holdout_ref="challenge_holdout:selection-gap",
            identity_namespace="semantic_identity",
            identity_ref="concept:unresolved-designation",
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
    with pytest.raises(ValueError, match="diagnostic-only.*group"):
        PurposeMembership.create(
            source_case_ref=CASE_REFS[0],
            classification="diagnostic_only",
            purpose=None,
            duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
            diagnostic_reason_ref="diagnostic_reason:comparison-only",
            review_refs=(REVIEW_REF,),
        )


def test_duplicate_groups_are_explicit_reviewed_lineage_not_semantic_union_keys() -> None:
    for forbidden in (
        "operator",
        "role",
        "mode",
        "semantic_target",
        "conflict_set",
        "topology",
        "response_action",
    ):
        with pytest.raises(ValueError, match="duplicate-risk namespace"):
            DuplicateRiskGroup.create(
                group_ref="duplicate_risk_group:bad",
                namespace=forbidden,
                purpose="train",
                member_case_refs=CASE_REFS[:2],
                reason_ref="duplicate_reason:bad",
                review_refs=(REVIEW_REF,),
            )

    with pytest.raises(ValueError, match="unique refs"):
        DuplicateRiskGroup.create(
            group_ref="duplicate_risk_group:duplicate",
            namespace="mutation_lineage",
            purpose="train",
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
        purpose=None,
        duplicate_risk_group_refs=(
            "duplicate_risk_group:family-a",
            "duplicate_risk_group:family-b",
        ),
        diagnostic_reason_ref=None,
        review_refs=(REVIEW_REF,),
    )
    changed[2] = PurposeMembership.create(
        source_case_ref=CASE_REFS[2],
        classification="typed_abstention",
        purpose=None,
        duplicate_risk_group_refs=("duplicate_risk_group:family-b",),
        diagnostic_reason_ref=None,
        review_refs=(REVIEW_REF,),
    )
    cross_purpose_group = DuplicateRiskGroup.create(
        group_ref="duplicate_risk_group:family-b",
        namespace="normalization_family",
        purpose="selection",
        member_case_refs=CASE_REFS[1:3],
        reason_ref="duplicate_reason:normalization",
        review_refs=(REVIEW_REF,),
    )
    with pytest.raises(ValueError, match="component.*one purpose"):
        PurposeContract.create(
            source_set_ref=contract.source_set_ref,
            memberships=tuple(changed),
            duplicate_risk_groups=contract.duplicate_risk_groups
            + (cross_purpose_group,),
            challenge_holdouts=contract.challenge_holdouts,
            denominator_minima=contract.denominator_minima,
            review_refs=contract.review_refs,
            solver_output_is_authority=False,
        )

    bad_group = DuplicateRiskGroup.create(
        group_ref="duplicate_risk_group:unknown-case",
        namespace="source_case_lineage",
        purpose="train",
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


def test_purpose_abi_fields_reject_booleans_at_top_and_nested_boundaries() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    contract = _contract()
    paths = []

    def collect_paths(node, path=()):
        if type(node) is dict:
            if "abi_version" in node:
                paths.append(path + ("abi_version",))
            for key, child in node.items():
                collect_paths(child, path + (key,))
        elif type(node) is list:
            for index, child in enumerate(node):
                collect_paths(child, path + (index,))

    collect_paths(contract.as_dict())
    for path in paths:
        wire = deepcopy(contract.as_dict())
        cursor = wire
        for part in path[:-1]:
            cursor = cursor[part]
        cursor[path[-1]] = True
        assert not Draft202012Validator(schema).is_valid(wire), path
        with pytest.raises((TypeError, ValueError), match="ABI|abi_version"):
            PurposeContract.from_dict(wire)

    raw = contract.to_json_bytes().replace(b'"abi_version":1', b'"abi_version":true', 1)
    with pytest.raises((TypeError, ValueError), match="ABI|abi_version"):
        PurposeContract.from_json_bytes(raw)
    nested_raw = contract.to_json_bytes().replace(
        b'"memberships":[{"abi_version":1',
        b'"memberships":[{"abi_version":true',
        1,
    )
    with pytest.raises((TypeError, ValueError), match="ABI|abi_version"):
        PurposeContract.from_json_bytes(nested_raw)


def test_purpose_standalone_case_refs_and_challenge_identity_tags_are_exact() -> None:
    with pytest.raises(ValueError, match="content ref"):
        DuplicateRiskGroup.create(
            group_ref="duplicate_risk_group:bad-case",
            namespace="source_case_lineage",
            purpose="train",
            member_case_refs=(CASE_REFS[1], "expanded_case_v2:not-a-hash"),
            reason_ref="duplicate_reason:bad-case",
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="content ref"):
        ChallengeHoldout.create(
            holdout_ref="challenge_holdout:bad-case",
            identity_namespace="semantic_identity",
            identity_ref="concept:gap",
            purpose="selection",
            member_case_refs=("expanded_case_v2:not-a-hash",),
            reason_ref="holdout_reason:bad-case",
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="identity.*namespace|namespace.*identity"):
        ChallengeHoldout.create(
            holdout_ref="challenge_holdout:tag-confusion",
            identity_namespace="operator",
            identity_ref="participant:user",
            purpose="selection",
            member_case_refs=(CASE_REFS[2],),
            reason_ref="holdout_reason:tag-confusion",
            review_refs=(REVIEW_REF,),
        )

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    contract = _contract()
    for index, (identity_namespace, identity_ref) in enumerate(
        (
            ("semantic_identity", "event:turn"),
            ("semantic_identity", "concept:person"),
            ("semantic_identity", "entity:lamp"),
            ("semantic_identity", "rel:likes"),
            ("semantic_identity", "dim:availability"),
            ("semantic_identity", "value:online"),
            ("semantic_identity", "label:name"),
            ("semantic_identity", "cap:query"),
            ("operator", "op:relation"),
        ),
        start=1,
    ):
        holdout = ChallengeHoldout.create(
            holdout_ref=f"challenge_holdout:authority-{index}",
            identity_namespace=identity_namespace,
            identity_ref=identity_ref,
            purpose="selection",
            member_case_refs=(CASE_REFS[2],),
            reason_ref="holdout_reason:authority-identity",
            review_refs=(REVIEW_REF,),
        )
        valid = _recreate_contract(contract, challenge_holdouts=(holdout,))
        assert validator.is_valid(valid.as_dict()), identity_ref
        assert PurposeContract.from_dict(valid.as_dict()) == valid

    for invented_ref in (
        "relation:likes",
        "state_dimension:availability",
        "label_type:name",
    ):
        with pytest.raises(ValueError, match="identity.*namespace|namespace.*identity"):
            ChallengeHoldout.create(
                holdout_ref="challenge_holdout:invented-prefix",
                identity_namespace="semantic_identity",
                identity_ref=invented_ref,
                purpose="selection",
                member_case_refs=(CASE_REFS[2],),
                reason_ref="holdout_reason:invented-prefix",
                review_refs=(REVIEW_REF,),
            )
        corrupt = contract.as_dict()
        corrupt["challenge_holdouts"][0]["identity_ref"] = invented_ref
        assert not validator.is_valid(corrupt), invented_ref
    with pytest.raises(ValueError, match="identity.*namespace|namespace.*identity"):
        ChallengeHoldout.create(
            holdout_ref="challenge_holdout:non-kernel-operator",
            identity_namespace="operator",
            identity_ref="op:learn",
            purpose="selection",
            member_case_refs=(CASE_REFS[2],),
            reason_ref="holdout_reason:non-kernel-operator",
            review_refs=(REVIEW_REF,),
        )


def test_purpose_rejects_asymmetric_group_membership_and_duplicate_holdout_identity() -> None:
    contract = _contract()
    changed = list(contract.memberships)
    changed[2] = PurposeMembership.create(
        source_case_ref=CASE_REFS[2],
        classification="typed_abstention",
        purpose=None,
        duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
        diagnostic_reason_ref=None,
        review_refs=(REVIEW_REF,),
    )
    with pytest.raises(ValueError, match="both ways|not contain|asymmetric"):
        _recreate_contract(contract, memberships=tuple(changed))

    original = contract.challenge_holdouts[0]
    duplicate = ChallengeHoldout.create(
        holdout_ref="challenge_holdout:different-ref",
        identity_namespace=original.identity_namespace,
        identity_ref=original.identity_ref,
        purpose=original.purpose,
        member_case_refs=original.member_case_refs,
        reason_ref=original.reason_ref,
        review_refs=original.review_refs,
    )
    with pytest.raises(ValueError, match="duplicate holdout identity"):
        _recreate_contract(
            contract,
            challenge_holdouts=tuple(
                sorted((original, duplicate), key=lambda item: item.holdout_ref)
            ),
        )


def test_purpose_parent_factory_rejects_forged_nested_values(monkeypatch) -> None:
    contract = _contract()
    valid = contract.memberships[0]
    forged = object.__new__(PurposeMembership)
    for name, value in valid.__dict__.items():
        object.__setattr__(forged, name, value)
    object.__setattr__(forged, "membership_ref", "purpose_membership_v1:" + "f" * 24)
    with pytest.raises(ValueError, match="canonical|membership"):
        _recreate_contract(contract, memberships=(forged,) + contract.memberships[1:])

    monkeypatch.setattr(purpose_module, "MAX_AGGREGATE_MEMBERSHIP_LINKS", 4)
    with pytest.raises(ValueError, match="aggregate membership"):
        _recreate_contract(contract)


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

    def assert_ref_string_bounds(value: object) -> None:
        if type(value) is dict:
            pattern = value.get("pattern")
            if type(pattern) is str and ":" in pattern:
                assert value.get("maxLength") == 512
            for child in value.values():
                assert_ref_string_bounds(child)
        elif type(value) is list:
            for child in value:
                assert_ref_string_bounds(child)

    assert_ref_string_bounds(schema)
    for field in (
        "memberships",
        "duplicate_risk_groups",
        "challenge_holdouts",
        "denominator_minima",
    ):
        assert "uniqueItems" not in schema["properties"][field]
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

    adversarial = []
    corrupt = deepcopy(wire)
    corrupt["memberships"][0]["review_refs"] = ["runtime_review:forbidden"]
    adversarial.append(corrupt)
    corrupt = deepcopy(wire)
    corrupt["challenge_holdouts"][0]["identity_namespace"] = "operator"
    corrupt["challenge_holdouts"][0]["identity_ref"] = "participant:user"
    adversarial.append(corrupt)
    corrupt = deepcopy(wire)
    corrupt["duplicate_risk_groups"][0]["member_case_refs"][0] = "expanded_case_v2:not-a-hash"
    adversarial.append(corrupt)
    for corrupt in adversarial:
        assert not validator.is_valid(corrupt)
        with pytest.raises((TypeError, ValueError)):
            PurposeContract.from_dict(corrupt)

    # Cross-row bidirectionality, uniqueness and aggregate link accounting are
    # semantic decoder postconditions that Draft 2020-12 cannot express.
    corrupt = deepcopy(wire)
    corrupt["purpose_contract_ref"] = "purpose_contract_v1:" + "f" * 24
    assert validator.is_valid(corrupt)
    assert "semantic postconditions" in schema["$comment"]
    with pytest.raises(ValueError, match="canonical"):
        PurposeContract.from_dict(corrupt)

    duplicate = deepcopy(wire)
    duplicate["memberships"].append(deepcopy(duplicate["memberships"][0]))
    assert validator.is_valid(duplicate)
    with pytest.raises(ValueError, match="duplicate source case membership"):
        PurposeContract.from_dict(duplicate)


def _sr4_cartesian_minima(
    denominator_ref: str = "denominator:semantic-expression",
    denominator_family: str = "semantic_expression",
) -> tuple[DenominatorMinimum, ...]:
    return tuple(
        DenominatorMinimum.create(
            denominator_ref=denominator_ref,
            denominator_family=denominator_family,
            purpose=purpose,
            minimum=1,
            review_refs=(REVIEW_REF,),
        )
        for purpose in ("train", "selection", "calibration", "frozen_test")
    )


def _sr4_component_contract(
    *, second_group_purpose: str = "train", holdout_purpose: str = "train"
) -> PurposeContract:
    group_refs_by_case = (
        ("duplicate_risk_group:family-a",),
        ("duplicate_risk_group:family-a", "duplicate_risk_group:family-b"),
        ("duplicate_risk_group:family-b",),
    )
    memberships = tuple(
        PurposeMembership.create(
            source_case_ref=case_ref,
            classification="semantic_supervision",
            purpose=None,
            duplicate_risk_group_refs=group_refs,
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        )
        for case_ref, group_refs in zip(CASE_REFS[:3], group_refs_by_case)
    )
    groups = (
        DuplicateRiskGroup.create(
            group_ref="duplicate_risk_group:family-a",
            namespace="paraphrase_family",
            purpose="train",
            member_case_refs=CASE_REFS[:2],
            reason_ref="duplicate_reason:reviewed-paraphrase-a",
            review_refs=(REVIEW_REF,),
        ),
        DuplicateRiskGroup.create(
            group_ref="duplicate_risk_group:family-b",
            namespace="normalization_family",
            purpose=second_group_purpose,
            member_case_refs=CASE_REFS[1:3],
            reason_ref="duplicate_reason:reviewed-paraphrase-b",
            review_refs=(REVIEW_REF,),
        ),
    )
    holdout = ChallengeHoldout.create(
        holdout_ref="challenge_holdout:inherited-purpose",
        identity_namespace="semantic_identity",
        identity_ref="concept:grouped-case",
        purpose=holdout_purpose,
        member_case_refs=(CASE_REFS[2],),
        reason_ref="holdout_reason:inherited-purpose",
        review_refs=(REVIEW_REF,),
    )
    return PurposeContract.create(
        source_set_ref="r4_source_set_v1:0123456789abcdef01234567",
        memberships=memberships,
        duplicate_risk_groups=groups,
        challenge_holdouts=(holdout,),
        denominator_minima=_sr4_cartesian_minima(),
        review_refs=(REVIEW_REF,),
        solver_output_is_authority=False,
    )


def test_sr4_group_owns_purpose_and_membership_is_exact_tagged_union() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_validator = Draft202012Validator(schema)
    base_wire = _sr4_component_contract().as_dict()

    def schema_accepts_membership(wire: dict) -> bool:
        candidate = deepcopy(base_wire)
        candidate["memberships"][0] = deepcopy(wire)
        return schema_validator.is_valid(candidate)

    positive_memberships = []
    for classification in (
        "semantic_supervision",
        "typed_abstention",
        "verification_rejection",
    ):
        grouped = PurposeMembership.create(
            source_case_ref=CASE_REFS[0],
            classification=classification,
            purpose=None,
            duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        )
        assert grouped.purpose is None
        positive_memberships.append(grouped)
        with pytest.raises(ValueError, match="grouped.*purpose"):
            PurposeMembership.create(
                source_case_ref=CASE_REFS[0],
                classification=classification,
                purpose="train",
                duplicate_risk_group_refs=("duplicate_risk_group:family-a",),
                diagnostic_reason_ref=None,
                review_refs=(REVIEW_REF,),
            )

    direct = PurposeMembership.create(
        source_case_ref=CASE_REFS[0],
        classification="verification_rejection",
        purpose="selection",
        duplicate_risk_group_refs=(),
        diagnostic_reason_ref=None,
        review_refs=(REVIEW_REF,),
    )
    assert direct.purpose == "selection"
    positive_memberships.append(direct)
    with pytest.raises(ValueError, match="ungrouped.*purpose"):
        PurposeMembership.create(
            source_case_ref=CASE_REFS[0],
            classification="semantic_supervision",
            purpose=None,
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        )

    diagnostic = PurposeMembership.create(
        source_case_ref=CASE_REFS[1],
        classification="diagnostic_only",
        purpose=None,
        duplicate_risk_group_refs=(),
        diagnostic_reason_ref="diagnostic_reason:restart-review",
        review_refs=(REVIEW_REF,),
    )
    positive_memberships.append(diagnostic)
    for membership in positive_memberships:
        wire = membership.as_dict()
        assert schema_accepts_membership(wire)
        assert PurposeMembership.from_dict(deepcopy(wire)) == membership

    invalid_memberships = []
    grouped_with_purpose = deepcopy(positive_memberships[0].as_dict())
    grouped_with_purpose["purpose"] = "train"
    invalid_memberships.append(grouped_with_purpose)
    direct_without_purpose = deepcopy(direct.as_dict())
    direct_without_purpose["purpose"] = None
    invalid_memberships.append(direct_without_purpose)
    diagnostic_with_group = deepcopy(diagnostic.as_dict())
    diagnostic_with_group["duplicate_risk_group_refs"] = [
        "duplicate_risk_group:family-a"
    ]
    invalid_memberships.append(diagnostic_with_group)
    for wire in invalid_memberships:
        assert not schema_accepts_membership(wire)
        with pytest.raises((TypeError, ValueError)):
            PurposeMembership.from_dict(wire)

    group = DuplicateRiskGroup.create(
        group_ref="duplicate_risk_group:family-a",
        namespace="paraphrase_family",
        purpose="train",
        member_case_refs=CASE_REFS[:2],
        reason_ref="duplicate_reason:reviewed-paraphrase",
        review_refs=(REVIEW_REF,),
    )
    assert group.purpose == "train"
    assert "purpose" in schema["$defs"]["group"]["required"]
    assert "verification_rejection" in schema["$defs"]["membership"][
        "properties"
    ]["classification"]["enum"]
    missing_group_purpose = _sr4_component_contract().as_dict()
    del missing_group_purpose["duplicate_risk_groups"][0]["purpose"]
    assert not Draft202012Validator(schema).is_valid(missing_group_purpose)
    with pytest.raises((TypeError, ValueError), match="fields|purpose"):
        PurposeContract.from_dict(missing_group_purpose)


def test_sr4_overlapping_groups_resolve_one_inherited_purpose_for_holdouts() -> None:
    contract = _sr4_component_contract()
    assert contract.challenge_holdouts[0].purpose == "train"
    with pytest.raises(ValueError, match="component.*one purpose"):
        _sr4_component_contract(second_group_purpose="selection")
    with pytest.raises(ValueError, match="holdout.*purpose"):
        _sr4_component_contract(holdout_purpose="selection")


def test_sr4_denominator_ref_requires_exact_four_purpose_cartesian_family() -> None:
    contract = _sr4_component_contract()
    with pytest.raises(ValueError, match="each denominator.*four purposes"):
        _recreate_contract(contract, denominator_minima=contract.denominator_minima[:-1])

    drifted = list(contract.denominator_minima)
    drifted[1] = DenominatorMinimum.create(
        denominator_ref=drifted[1].denominator_ref,
        denominator_family="operator",
        purpose=drifted[1].purpose,
        minimum=drifted[1].minimum,
        review_refs=drifted[1].review_refs,
    )
    with pytest.raises(ValueError, match="denominator.*one family"):
        _recreate_contract(contract, denominator_minima=tuple(drifted))

    distributed = tuple(
        DenominatorMinimum.create(
            denominator_ref=f"denominator:distributed-{purpose}",
            denominator_family="semantic_expression",
            purpose=purpose,
            minimum=1,
            review_refs=(REVIEW_REF,),
        )
        for purpose in ("train", "selection", "calibration", "frozen_test")
    )
    with pytest.raises(ValueError, match="each denominator.*four purposes"):
        _recreate_contract(contract, denominator_minima=distributed)


def _sr4_overlapping_chain_contract(size: int) -> PurposeContract:
    case_refs = tuple(
        f"expanded_case_v2:{index:024x}" for index in range(1, size + 1)
    )
    group_refs = tuple(
        f"duplicate_risk_group:chain-{index:04d}" for index in range(size - 1)
    )
    memberships = []
    for index, case_ref in enumerate(case_refs):
        member_groups = tuple(
            group_refs[group_index]
            for group_index in (index - 1, index)
            if 0 <= group_index < len(group_refs)
        )
        memberships.append(
            PurposeMembership.create(
                source_case_ref=case_ref,
                classification="semantic_supervision",
                purpose=None,
                duplicate_risk_group_refs=member_groups,
                diagnostic_reason_ref=None,
                review_refs=(REVIEW_REF,),
            )
        )
    groups = tuple(
        DuplicateRiskGroup.create(
            group_ref=group_ref,
            namespace="source_case_lineage",
            purpose="train",
            member_case_refs=case_refs[index : index + 2],
            reason_ref="duplicate_reason:reviewed-chain",
            review_refs=(REVIEW_REF,),
        )
        for index, group_ref in enumerate(group_refs)
    )
    return PurposeContract.create(
        source_set_ref="r4_source_set_v1:0123456789abcdef01234567",
        memberships=tuple(memberships),
        duplicate_risk_groups=groups,
        challenge_holdouts=(),
        denominator_minima=_sr4_cartesian_minima(),
        review_refs=(REVIEW_REF,),
        solver_output_is_authority=False,
    )


def test_sr4_indexed_component_validation_has_deterministic_linear_operation_count() -> None:
    small = _sr4_overlapping_chain_contract(16)
    large = _sr4_overlapping_chain_contract(32)
    small_count = purpose_module._validation_operation_count_for_test(small)
    large_count = purpose_module._validation_operation_count_for_test(large)
    small_size = len(small.memberships) + sum(
        len(row.duplicate_risk_group_refs) for row in small.memberships
    ) + sum(len(group.member_case_refs) for group in small.duplicate_risk_groups)
    large_size = len(large.memberships) + sum(
        len(row.duplicate_risk_group_refs) for row in large.memberships
    ) + sum(len(group.member_case_refs) for group in large.duplicate_risk_groups)
    assert small_count <= 8 * small_size
    assert large_count <= 8 * large_size
    assert large_count <= 2 * small_count + 32


__cemm_test_inventory__ = {'tests/test_r4_purpose_contracts.py::test_sr4_denominator_ref_requires_exact_four_purpose_cartesian_family': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:r4-sr4-denominator-cartesian-four-purpose-family',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R4.1-SR4',
                                                                                                               'owner_ref': 'mutation-partition',
                                                                                                               'source_ast_sha256': '7d5c4f1ffe8bd49b3a318e0499787254336dc923ad7165661cb4fa96d583ae41'},
 'tests/test_r4_purpose_contracts.py::test_sr4_group_owns_purpose_and_membership_is_exact_tagged_union': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-sr4-group-purpose-membership-tagged-union',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4.1-SR4',
                                                                                                          'owner_ref': 'mutation-partition',
                                                                                                          'source_ast_sha256': 'b36c207dbb1d9dc11e4e762509c926cb8ed3bf63f0253369ae251d1c40d4e595'},
 'tests/test_r4_purpose_contracts.py::test_sr4_indexed_component_validation_has_deterministic_linear_operation_count': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:r4-sr4-purpose-component-linear-operations',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R4.1-SR4',
                                                                                                                        'owner_ref': 'mutation-partition',
                                                                                                                        'source_ast_sha256': '01d34dac4e5503f2986b5ff3d729d292c3928f0116a869305fbaf6ef8e05aef2'},
 'tests/test_r4_purpose_contracts.py::test_sr4_overlapping_groups_resolve_one_inherited_purpose_for_holdouts': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:r4-sr4-overlapping-groups-inherited-purpose',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R4.1-SR4',
                                                                                                                'owner_ref': 'mutation-partition',
                                                                                                                'source_ast_sha256': '5ea11e60659ac9c9add2ade3cf972c9dd15357ccdcaab67f526159b61477140b'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value0]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': 'a43a0ca034ab9bfa2522085925d6340175f08f85f0748db48ce2cb47b63bbffa'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value1]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': 'a43a0ca034ab9bfa2522085925d6340175f08f85f0748db48ce2cb47b63bbffa'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value2]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': 'a43a0ca034ab9bfa2522085925d6340175f08f85f0748db48ce2cb47b63bbffa'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value3]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': 'a43a0ca034ab9bfa2522085925d6340175f08f85f0748db48ce2cb47b63bbffa'},
 'tests/test_r4_purpose_contracts.py::test_purpose_values_are_factory_only_frozen_and_canonical[value4]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-purpose-values-factory-only-frozen-canonical',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': 'a43a0ca034ab9bfa2522085925d6340175f08f85f0748db48ce2cb47b63bbffa'},
 'tests/test_r4_purpose_contracts.py::test_membership_classification_is_total_and_diagnostic_rows_never_enter_a_purpose': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:r4-purpose-membership-total-diagnostic-isolated',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                                           'source_ast_sha256': 'b2e14e858bdc3df5a225c7b594b501c6a826e631ee168efec7f5f09870dda3d9'},
 'tests/test_r4_purpose_contracts.py::test_duplicate_groups_are_explicit_reviewed_lineage_not_semantic_union_keys': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:r4-duplicate-groups-reviewed-lineage-not-semantic-union',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                     'owner_ref': 'mutation-partition',
                                                                                                                     'source_ast_sha256': '04155e8d17f21efc70cc0fc93318b65d5e935dcbce4784d132831970fa576e99'},
 'tests/test_r4_purpose_contracts.py::test_purpose_contract_rejects_duplicate_unknown_and_cross_purpose_group_members': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-purpose-contract-rejects-duplicate-unknown-cross-purpose',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                                         'source_ast_sha256': '89a28331a0b16807777fe174f88359ebe000d0eb37eae9dd3bba7190b4b5edec'},
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
 'tests/test_r4_purpose_contracts.py::test_purpose_abi_fields_reject_booleans_at_top_and_nested_boundaries': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:r4-purpose-abi-exact-int-not-bool',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                              'owner_ref': 'mutation-partition',
                                                                                                              'source_ast_sha256': 'fa0332a6e08db35f8d6f0217befbc0d5309042915b0b1adfae24c9c728a3c1c8'},
 'tests/test_r4_purpose_contracts.py::test_purpose_standalone_case_refs_and_challenge_identity_tags_are_exact': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:r4-purpose-case-and-identity-tags-exact',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                 'owner_ref': 'mutation-partition',
                                                                                                                 'source_ast_sha256': 'f49706bbba46d38cbd7539310ede70aeaf83bdaf6ff5171e8a6d0b480cdfd025'},
 'tests/test_r4_purpose_contracts.py::test_purpose_rejects_asymmetric_group_membership_and_duplicate_holdout_identity': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-purpose-group-bidirectional-holdout-identity-unique',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                                         'source_ast_sha256': '90003e8ebc05fddacb3d308e39b405d9555160b015983f6930dd674ebbdb0f8d'},
 'tests/test_r4_purpose_contracts.py::test_purpose_parent_factory_rejects_forged_nested_values': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:r4-purpose-parent-rejects-forged-nested-and-aggregate-bound',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                  'source_ast_sha256': '1a849abd5e3d6c80d7f104869321328186a4bbd8ebfd505743e3e39ac00d3b55'},
 'tests/test_r4_purpose_contracts.py::test_purpose_schema_is_strict_draft_2020_12_and_matches_decoder': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-purpose-schema-draft-2020-12-decoder-parity',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                         'source_ast_sha256': '3f46ff05483a245631753b61429e98e9e5fb0ace6369c285e1d85a9549abcd9c'}}
