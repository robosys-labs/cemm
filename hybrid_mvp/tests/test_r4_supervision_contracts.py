from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cemm_authoritative_hybrid.r4_supervision import (
    MAX_BLUEPRINT_ACTIONS,
    MAX_DERIVATIONS_PER_CASE,
    BlueprintAction,
    DerivationBlueprint,
    DerivationSelector,
    LiteralAlignment,
    MutationContract,
    ProposalTarget,
    R4ReviewManifest,
    RealizationRow,
    RealizationSlot,
    ReferenceFormChoice,
    ReviewSourceFile,
    TypedAbstention,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
CASE_REF = "expanded_case_v2:0123456789abcdef01234567"
REVIEW_REF = "source_review:0123456789abcdef01234567"


def _selector(kind: str, value_ref: str) -> DerivationSelector:
    return DerivationSelector.create(selector_kind=kind, value_ref=value_ref)


def _blueprint() -> DerivationBlueprint:
    return DerivationBlueprint.create(
        actions=(
            BlueprintAction.create(
                action_index=0,
                action_type="select_context",
                selectors=(_selector("context_slot", "proposal_context:case-1"),),
            ),
            BlueprintAction.create(
                action_index=1,
                action_type="select_mode",
                selectors=(_selector("mode_slot", "mode_slot:observe"),),
            ),
            BlueprintAction.create(
                action_index=2,
                action_type="instantiate_operator",
                selectors=(
                    _selector("local_node", "application:0"),
                    _selector("frame_slot", "application_frame_slot:event"),
                ),
            ),
            BlueprintAction.create(
                action_index=3,
                action_type="complete_program",
                selectors=(),
            ),
        ),
        root_local_refs=("application:0",),
    )


def _derive_target() -> ProposalTarget:
    return ProposalTarget.create(
        source_case_ref=CASE_REF,
        target_kind="derive",
        expected_expression_refs=("expression:0123456789abcdef01234567",),
        expression_relation="exact",
        derivations=(_blueprint(),),
        abstention=None,
        review_refs=(REVIEW_REF,),
    )


def _abstain_target() -> ProposalTarget:
    return ProposalTarget.create(
        source_case_ref="expanded_case_v2:1123456789abcdef01234567",
        target_kind="abstain",
        expected_expression_refs=(),
        expression_relation="exact",
        derivations=(),
        abstention=TypedAbstention.create(
            gap_kind_ref="gap_kind:unresolved_designation",
            critical=True,
            earliest_owner="orient",
            safe_disposition="frontier",
        ),
        review_refs=(REVIEW_REF,),
    )


def _realization() -> RealizationRow:
    return RealizationRow.create(
        source_case_ref=CASE_REF,
        response_signature_ref="response_signature:0123456789abcdef01234567",
        expression_refs=("expression:0123456789abcdef01234567",),
        discourse_action_ref="response_action:answer_state",
        polarity_ref="polarity:positive",
        modality_ref="modality:actual",
        epistemic_status_ref="epistemic_status:known",
        output_speaker_ref="participant:system",
        output_addressee_ref="participant:user",
        authorized_surface="The lamp is on.",
        language="en",
        semantic_slots=(
            RealizationSlot.create(
                slot_ref="response_slot:subject",
                semantic_ref="entity:lamp",
                required=True,
            ),
        ),
        reference_forms=(
            ReferenceFormChoice.create(
                participant_ref="participant:system",
                surface_form="I",
            ),
        ),
        literal_alignments=(
            LiteralAlignment.create(
                slot_ref="response_slot:subject",
                copy_source_kind="reviewed_literal",
                copy_source_ref="reviewed_literal:lamp",
                source_literal="lamp",
                source_start=0,
                source_end=4,
                surface_start=4,
                surface_end=8,
            ),
        ),
        review_refs=(REVIEW_REF,),
    )


def _mutation() -> MutationContract:
    return MutationContract.create(
        mutation_family_ref="mutation_family:polarity",
        source_case_ref=CASE_REF,
        changed_dimension_ref="dimension:polarity",
        expected_earliest_owner="verify",
        disposition="reject",
        effect_kind="no_effect",
        expected_effect_ref=None,
        review_refs=(REVIEW_REF,),
    )


def _manifest() -> R4ReviewManifest:
    rows = tuple(
        ReviewSourceFile.create(
            source_ref=f"reviewed_source:{index:024x}",
            path=path,
            sha256=(str(index) * 64),
            record_count=1,
            review_refs=(REVIEW_REF,),
        )
        for index, path in enumerate(
            (
                "data/review/r4_1/mutation_contracts.jsonl",
                "data/review/r4_1/proposal_supervision.jsonl",
                "data/review/r4_1/purpose_contract.json",
                "data/review/r4_1/realization_supervision.jsonl",
            ),
            start=1,
        )
    )
    return R4ReviewManifest.create(
        review_policy_ref="review_policy:r4_1",
        reviewer_refs=("reviewer:human-1",),
        reviewed_base_revision="a" * 40,
        authority_generation="authority-v1-2026-07-29",
        source_bundle_ref="r4_review_bundle_v1:0123456789abcdef01234567",
        scenario_source_sha256="f" * 64,
        sources=rows,
        approval_state="approved",
        supersedes_refs=("r4_build_v4:0123456789abcdef01234567",),
        runtime_observations_are_source_authority=False,
        bootstrap_outputs_are_source_authority=False,
    )


@pytest.mark.parametrize(
    "factory",
    (_manifest, _derive_target, _abstain_target, _realization, _mutation),
    ids=["_manifest", "_derive_target", "_abstain_target", "_realization", "_mutation"],
)
def test_supervision_contracts_are_factory_only_frozen_and_canonical(factory) -> None:
    value = factory()
    with pytest.raises(TypeError, match="use .*create"):
        type(value)()
    with pytest.raises(FrozenInstanceError):
        value.abi_version = 99
    assert type(value).from_json_bytes(value.to_json_bytes()) == value


def test_review_manifest_is_content_addressed_complete_and_never_self_authored() -> None:
    manifest = _manifest()
    assert manifest.abi_version == 1
    assert len(manifest.sources) == 4
    assert manifest.runtime_observations_are_source_authority is False
    assert manifest.bootstrap_outputs_are_source_authority is False

    tampered = deepcopy(manifest.as_dict())
    tampered["manifest_ref"] = "r4_review_manifest_v1:forged"
    with pytest.raises(ValueError, match="manifest ref"):
        R4ReviewManifest.from_dict(tampered)

    with pytest.raises(ValueError, match="reviewed source"):
        ReviewSourceFile.create(
            source_ref="runtime_observation:forbidden",
            path=manifest.sources[0].path,
            sha256=manifest.sources[0].sha256,
            record_count=manifest.sources[0].record_count,
            review_refs=manifest.sources[0].review_refs,
        )
    with pytest.raises(ValueError, match="content ref"):
        ReviewSourceFile.create(
            source_ref="reviewed_source:not-content-addressed",
            path=manifest.sources[0].path,
            sha256=manifest.sources[0].sha256,
            record_count=manifest.sources[0].record_count,
            review_refs=manifest.sources[0].review_refs,
        )


def test_proposal_targets_separate_derivation_from_meaning_and_require_typed_abstention() -> None:
    target = _derive_target()
    assert target.target_kind == "derive"
    assert target.expected_expression_refs == ("expression:0123456789abcdef01234567",)
    assert all("expression" not in action.as_dict() for action in target.derivations[0].actions)

    with pytest.raises(ValueError, match="derive target"):
        ProposalTarget.create(
            source_case_ref=CASE_REF,
            target_kind="derive",
            expected_expression_refs=target.expected_expression_refs,
            expression_relation="exact",
            derivations=(),
            abstention=None,
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="abstain target"):
        ProposalTarget.create(
            source_case_ref=CASE_REF,
            target_kind="abstain",
            expected_expression_refs=(),
            expression_relation="exact",
            derivations=(),
            abstention=None,
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="content ref"):
        ProposalTarget.create(
            source_case_ref=CASE_REF,
            target_kind="derive",
            expected_expression_refs=("expression:not-content-addressed",),
            expression_relation="exact",
            derivations=target.derivations,
            abstention=None,
            review_refs=(REVIEW_REF,),
        )


def test_derivation_blueprints_reject_unsafe_selectors_and_unbounded_lists() -> None:
    with pytest.raises(ValueError, match="unsafe selector"):
        DerivationSelector.create(selector_kind="raw_phrase", value_ref="literal:lamp")
    with pytest.raises(ValueError, match="unsafe selector"):
        DerivationSelector.create(selector_kind="regex", value_ref="literal:.*")
    with pytest.raises(ValueError, match="unsafe selector"):
        DerivationSelector.create(selector_kind="internal_ref_spelling", value_ref="literal:op-event")
    with pytest.raises(ValueError, match="source-local selector"):
        DerivationSelector.create(
            selector_kind="context_slot",
            value_ref="runtime_observation:forbidden",
        )

    action = BlueprintAction.create(
        action_index=0,
        action_type="select_context",
        selectors=(_selector("context_slot", "proposal_context:case-1"),),
    )
    with pytest.raises(ValueError, match="action bound"):
        DerivationBlueprint.create(
            actions=tuple(action for _ in range(MAX_BLUEPRINT_ACTIONS + 1)),
            root_local_refs=(),
        )
    target = _derive_target()
    with pytest.raises(ValueError, match="derivation bound"):
        ProposalTarget.create(
            source_case_ref=CASE_REF,
            target_kind="derive",
            expected_expression_refs=target.expected_expression_refs,
            expression_relation="exact",
            derivations=tuple(target.derivations[0] for _ in range(MAX_DERIVATIONS_PER_CASE + 1)),
            abstention=None,
            review_refs=(REVIEW_REF,),
        )


def test_realization_alignment_is_exact_bounded_and_never_input_as_output_gold() -> None:
    row = _realization()
    assert row.authorized_surface[4:8] == "lamp"

    invalid = deepcopy(row.as_dict())
    invalid["literal_alignments"][0]["surface_end"] = 9
    with pytest.raises(ValueError, match="alignment"):
        RealizationRow.from_dict(invalid)

    with pytest.raises(ValueError, match="input surface"):
        LiteralAlignment.create(
            slot_ref="response_slot:subject",
            copy_source_kind="input_surface",
            copy_source_ref="input_surface:case-1",
            source_literal="lamp",
            source_start=0,
            source_end=4,
            surface_start=4,
            surface_end=8,
        )

    with pytest.raises((TypeError, ValueError), match="integer|span"):
        LiteralAlignment.create(
            slot_ref="response_slot:subject",
            copy_source_kind="reviewed_literal",
            copy_source_ref="reviewed_literal:lamp",
            source_literal="lamp",
            source_start=float("nan"),
            source_end=4,
            surface_start=4,
            surface_end=8,
        )


def test_mutation_contract_is_reviewed_truth_not_an_observation_echo() -> None:
    contract = _mutation()
    assert contract.effect_kind == "no_effect"
    assert not any("observed" in key for key in contract.as_dict())
    with pytest.raises(ValueError, match="effect ref"):
        MutationContract.create(
            mutation_family_ref=contract.mutation_family_ref,
            source_case_ref=contract.source_case_ref,
            changed_dimension_ref=contract.changed_dimension_ref,
            expected_earliest_owner=contract.expected_earliest_owner,
            disposition="accept",
            effect_kind="effect",
            expected_effect_ref=None,
            review_refs=contract.review_refs,
        )


def test_supervision_decoders_reject_unknown_missing_abi_duplicate_and_noncanonical_json() -> None:
    target = _derive_target()
    value = target.as_dict()

    unknown = deepcopy(value)
    unknown["observed_program_ref"] = "program:forbidden"
    with pytest.raises(ValueError, match="fields mismatch"):
        ProposalTarget.from_dict(unknown)

    missing = deepcopy(value)
    missing.pop("review_refs")
    with pytest.raises(ValueError, match="fields mismatch"):
        ProposalTarget.from_dict(missing)

    unsupported = deepcopy(value)
    unsupported["abi_version"] = 2
    with pytest.raises(ValueError, match="unsupported Proposal Supervision ABI"):
        ProposalTarget.from_dict(unsupported)

    raw = target.to_json_bytes()
    duplicate = raw.replace(b'{"abi_version":1,', b'{"abi_version":1,"abi_version":1,', 1)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        ProposalTarget.from_json_bytes(duplicate)

    pretty = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    with pytest.raises(ValueError, match="not canonical"):
        ProposalTarget.from_json_bytes(pretty)

    nonfinite = raw.replace(b'"abi_version":1', b'"abi_version":NaN', 1)
    with pytest.raises(ValueError, match="non-finite JSON"):
        ProposalTarget.from_json_bytes(nonfinite)


def test_supervision_schemas_are_strict_draft_2020_12_and_match_decoders() -> None:
    instances = {
        "r4_review_manifest.schema.json": (_manifest(), R4ReviewManifest),
        "r4_proposal_supervision.schema.json": (_derive_target(), ProposalTarget),
        "r4_realization_supervision.schema.json": (_realization(), RealizationRow),
        "r4_mutation_contract.schema.json": (_mutation(), MutationContract),
    }

    def assert_strict_objects(value: object) -> None:
        if type(value) is dict:
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
            for child in value.values():
                assert_strict_objects(child)
        elif type(value) is list:
            for child in value:
                assert_strict_objects(child)

    missing_field = {"r4_review_manifest.schema.json": "reviewer_refs"}
    for filename, (instance, decoder) in instances.items():
        schema = json.loads((SCHEMAS / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert_strict_objects(schema)
        validator = Draft202012Validator(schema)
        wire = instance.as_dict()
        assert validator.is_valid(wire)
        assert decoder.from_dict(deepcopy(wire)) == instance

        for corrupt in (
            {**deepcopy(wire), "abi_version": 99},
            {key: item for key, item in deepcopy(wire).items() if key != missing_field.get(filename, "review_refs")},
            {**deepcopy(wire), "unexpected": True},
        ):
            assert not validator.is_valid(corrupt)
            with pytest.raises((TypeError, ValueError)):
                decoder.from_dict(corrupt)


__cemm_test_inventory__ = {'tests/test_r4_supervision_contracts.py::test_supervision_contracts_are_factory_only_frozen_and_canonical[_manifest]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-supervision-contracts-factory-only-frozen-canonical',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                                         'source_ast_sha256': '6c6f289bd99a7291eb62916a0082bf40e3d87d25e04d8fe0c6ba77fcfedfdd97'},
 'tests/test_r4_supervision_contracts.py::test_supervision_contracts_are_factory_only_frozen_and_canonical[_derive_target]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:r4-supervision-contracts-factory-only-frozen-canonical',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                              'owner_ref': 'mutation-partition',
                                                                                                                              'source_ast_sha256': '6c6f289bd99a7291eb62916a0082bf40e3d87d25e04d8fe0c6ba77fcfedfdd97'},
 'tests/test_r4_supervision_contracts.py::test_supervision_contracts_are_factory_only_frozen_and_canonical[_abstain_target]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:r4-supervision-contracts-factory-only-frozen-canonical',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                               'owner_ref': 'mutation-partition',
                                                                                                                               'source_ast_sha256': '6c6f289bd99a7291eb62916a0082bf40e3d87d25e04d8fe0c6ba77fcfedfdd97'},
 'tests/test_r4_supervision_contracts.py::test_supervision_contracts_are_factory_only_frozen_and_canonical[_realization]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:r4-supervision-contracts-factory-only-frozen-canonical',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                            'owner_ref': 'mutation-partition',
                                                                                                                            'source_ast_sha256': '6c6f289bd99a7291eb62916a0082bf40e3d87d25e04d8fe0c6ba77fcfedfdd97'},
 'tests/test_r4_supervision_contracts.py::test_supervision_contracts_are_factory_only_frozen_and_canonical[_mutation]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-supervision-contracts-factory-only-frozen-canonical',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                                         'source_ast_sha256': '6c6f289bd99a7291eb62916a0082bf40e3d87d25e04d8fe0c6ba77fcfedfdd97'},
 'tests/test_r4_supervision_contracts.py::test_review_manifest_is_content_addressed_complete_and_never_self_authored': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:r4-review-manifest-content-addressed-no-self-gold',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                        'owner_ref': 'mutation-partition',
                                                                                                                        'source_ast_sha256': '2bdfafe2b2a0408be036609855e0a45129d9c50e950387fda413b1e764418533'},
 'tests/test_r4_supervision_contracts.py::test_proposal_targets_separate_derivation_from_meaning_and_require_typed_abstention': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:r4-proposal-targets-separate-derivation-meaning-abstention',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                                 'owner_ref': 'mutation-partition',
                                                                                                                                 'source_ast_sha256': '06b9f4c27877704cf2cdd4cb7e3578e5d5cbb211d7ac68328a5e7e20d44718c3'},
 'tests/test_r4_supervision_contracts.py::test_derivation_blueprints_reject_unsafe_selectors_and_unbounded_lists': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-derivation-blueprints-reject-unsafe-unbounded',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                    'owner_ref': 'mutation-partition',
                                                                                                                    'source_ast_sha256': '1adb769a0d940595736fb9b72b86549fa0619a99821e372335b051b051a61c06'},
 'tests/test_r4_supervision_contracts.py::test_realization_alignment_is_exact_bounded_and_never_input_as_output_gold': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:r4-realization-alignment-exact-bounded-no-input-gold',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                        'owner_ref': 'mutation-partition',
                                                                                                                        'source_ast_sha256': '4c893cbc6bc869a4ef01f11ab0a70fc92f106f1b999cb4128f987b994e12bb6a'},
 'tests/test_r4_supervision_contracts.py::test_mutation_contract_is_reviewed_truth_not_an_observation_echo': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:r4-mutation-contract-reviewed-truth-not-observation-echo',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                              'owner_ref': 'mutation-partition',
                                                                                                              'source_ast_sha256': '531be0e9d564302433d9e4a0ea117e03e752537989f322e5dd3e3097c4356938'},
 'tests/test_r4_supervision_contracts.py::test_supervision_decoders_reject_unknown_missing_abi_duplicate_and_noncanonical_json': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:r4-supervision-decoders-strict-canonical-json',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                                                  'source_ast_sha256': '299f6a73beefbc0b7d3d37951924c1cc86d382aba2573780d0d7302281878571'},
 'tests/test_r4_supervision_contracts.py::test_supervision_schemas_are_strict_draft_2020_12_and_match_decoders': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:r4-supervision-schemas-draft-2020-12-decoder-parity',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                                  'source_ast_sha256': '91bf681cdbfb2478e2aa09b7bb975f6d63fdb8b8c1514c20bca482b826f92f87'}}
