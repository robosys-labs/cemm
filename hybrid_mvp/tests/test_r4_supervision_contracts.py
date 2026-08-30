from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import errno
import hashlib
import json
import os
from pathlib import Path
from types import MappingProxyType

import pytest
from jsonschema import Draft202012Validator
import cemm_authoritative_hybrid.r4_supervision as supervision_module

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.r4_purpose import (
    DenominatorMinimum,
    PurposeContract,
    PurposeMembership,
)

from cemm_authoritative_hybrid.r4_supervision import (
    MAX_BLUEPRINT_ACTIONS,
    MAX_DERIVATIONS_PER_CASE,
    MAX_REALIZATION_VARIANTS_PER_CASE,
    BlueprintAction,
    DesignationAlignment,
    DerivationBlueprint,
    ExpressionSetResponseSubject,
    LiteralAlignment,
    MorphologyAlignment,
    MutationContract,
    OmissionAlignment,
    ProposalTarget,
    R4ReviewManifest,
    RealizationRow,
    RealizationBinding,
    RealizationSlot,
    ReferenceAlignment,
    ReviewSourceFile,
    TypedAbstention,
    TypedGapResponseSubject,
    VerificationRejection,
    VerifierRejectionResponseSubject,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
CASE_REF = "expanded_case_v2:0123456789abcdef01234567"
REVIEW_REF = "source_review:0123456789abcdef01234567"


def _blueprint() -> DerivationBlueprint:
    return _sr2_blueprint("expression:0123456789abcdef01234567")


def _derive_target() -> ProposalTarget:
    return _sr2_derive_target(
        ("expression:0123456789abcdef01234567",),
        (_blueprint(),),
    )


def _abstain_target() -> ProposalTarget:
    return ProposalTarget.create(
        source_case_ref="expanded_case_v2:1123456789abcdef01234567",
        target_kind="abstain",
        expected_expression_refs=(),
        match_policy="exact",
        expected_expression_relation="none",
        derivations=(),
        abstention=TypedAbstention.create(
            gap_kind_ref="gap_kind:unresolved_designation",
            critical=True,
            earliest_owner="orient",
            safe_disposition="frontier",
        ),
        verification_rejection=None,
        review_refs=(REVIEW_REF,),
    )


def _sr2_blueprint(
    expected_expression_ref: str,
    *,
    local_suffix: str = "0",
    roots: tuple[str, ...] | None = None,
    source_assignment_blueprint=None,
):
    surface_ref = "reviewed_surface:0123456789abcdef01234567"
    selected_roots = roots or (f"application:{local_suffix}",)
    bindings = [
        supervision_module.StructuralSelectorBinding.create(
            selector_handle=0,
            selector_kind="context_slot",
            value_ref="proposal_context:case-1",
        ),
        supervision_module.StructuralSelectorBinding.create(
            selector_handle=1,
            selector_kind="mode_slot",
            value_ref="mode_slot:observe",
        ),
    ]
    actions = [
        supervision_module.BlueprintAction.create(
            action_index=0,
            action_type="select_context",
            selector_handles=(0,),
        ),
        supervision_module.BlueprintAction.create(
            action_index=1,
            action_type="select_mode",
            selector_handles=(1,),
        ),
    ]
    for root in selected_roots:
        local_handle = len(bindings)
        bindings.append(
            supervision_module.StructuralSelectorBinding.create(
                selector_handle=local_handle,
                selector_kind="local_node",
                value_ref=root,
            )
        )
        frame_handle = len(bindings)
        bindings.append(
            supervision_module.GroundedSelectorBinding.create(
                selector_handle=frame_handle,
                selector_kind="frame_slot",
                source_case_ref=CASE_REF,
                surface_ref=surface_ref,
                graph_component_ref=f"application_frame_slot:event-{frame_handle}",
                semantic_kind_ref="semantic_kind:event_type",
                spans=(
                    supervision_module.SourceSpan.create(
                        surface_ref=surface_ref,
                        start=0,
                        end=4,
                    ),
                ),
                source_selector_kind="contribution",
                source_selector_ref=f"contribution_slot:predicate-{frame_handle}",
            )
        )
        actions.append(
            supervision_module.BlueprintAction.create(
                action_index=len(actions),
                action_type="instantiate_operator",
                selector_handles=(local_handle, frame_handle),
            )
        )
    actions.append(
        supervision_module.BlueprintAction.create(
            action_index=len(actions),
            action_type="complete_program",
            selector_handles=(),
        )
    )
    if source_assignment_blueprint is None:
        source_assignment_blueprint = supervision_module.SourceAssignmentBlueprint.create(
            observed_source_unit_refs=("unit:0",),
            assignments=(
                supervision_module.SourceAssignmentEntry.create(
                    source_unit_ref="unit:0",
                    contribution_slot_ref="contribution_slot:predicate-3",
                    contribution_kind="predicate",
                    assignment_kind="predicate",
                    target_action_index=2,
                    target_role_ref=None,
                    residual_kind=None,
                    critical=False,
                ),
            ),
        )
    return supervision_module.DerivationBlueprint.create(
        selector_bindings=tuple(bindings),
        actions=tuple(actions),
        root_local_refs=selected_roots,
        expected_expression_ref=expected_expression_ref,
        source_assignment_blueprint=source_assignment_blueprint,
    )


def _sr2_derive_target(expected_expression_refs, derivations):
    return supervision_module.ProposalTarget.create(
        source_case_ref=CASE_REF,
        target_kind="derive",
        expected_expression_refs=tuple(expected_expression_refs),
        match_policy="exact",
        expected_expression_relation=(
            "single" if len(expected_expression_refs) == 1 else "conflict"
        ),
        derivations=tuple(sorted(derivations, key=lambda row: row.blueprint_ref)),
        abstention=None,
        verification_rejection=None,
        review_refs=(REVIEW_REF,),
    )


def _realization() -> RealizationRow:
    return RealizationRow.create(
        source_case_ref=CASE_REF,
        response_subject=ExpressionSetResponseSubject.create(
            expected_expression_relation="single",
            expression_refs=("expression:0123456789abcdef01234567",),
        ),
        bindings=(
            RealizationBinding.create(
                binding_key_ref="binding_key:subject",
                semantic_ref="entity:lamp",
            ),
        ),
        discourse_action_ref="response_action:answer_state",
        polarity_ref="polarity:positive",
        modality_ref="modality:actual",
        epistemic_status_ref="epistemic_status:supported",
        output_speaker_ref="participant:system",
        output_addressee_ref="participant:user",
        authorized_surface="The lamp is on.",
        language="en",
        semantic_slots=(
            RealizationSlot.create(
                slot_ref="response_slot:subject",
                semantic_ref="entity:lamp",
                required=True,
                qualifier_refs=("qualifier:definite",),
            ),
        ),
        alignments=(
            DesignationAlignment.create(
                slot_ref="response_slot:subject",
                designation_fact_ref="designation:0123456789abcdef01234567",
                surface_start=4,
                surface_end=8,
            ),
        ),
        review_refs=(REVIEW_REF,),
    )


def _recreate_realization(row: RealizationRow, **changes) -> RealizationRow:
    values = {
        "source_case_ref": row.source_case_ref,
        "response_subject": row.response_subject,
        "bindings": row.bindings,
        "discourse_action_ref": row.discourse_action_ref,
        "polarity_ref": row.polarity_ref,
        "modality_ref": row.modality_ref,
        "epistemic_status_ref": row.epistemic_status_ref,
        "output_speaker_ref": row.output_speaker_ref,
        "output_addressee_ref": row.output_addressee_ref,
        "authorized_surface": row.authorized_surface,
        "language": row.language,
        "semantic_slots": row.semantic_slots,
        "alignments": row.alignments,
        "review_refs": row.review_refs,
    }
    values.update(changes)
    return RealizationRow.create(**values)


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
            match_policy="exact",
            expected_expression_relation="single",
            derivations=(),
            abstention=None,
            verification_rejection=None,
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="abstain target"):
        ProposalTarget.create(
            source_case_ref=CASE_REF,
            target_kind="abstain",
            expected_expression_refs=(),
            match_policy="exact",
            expected_expression_relation="none",
            derivations=(),
            abstention=None,
            verification_rejection=None,
            review_refs=(REVIEW_REF,),
        )
    with pytest.raises(ValueError, match="content ref"):
        ProposalTarget.create(
            source_case_ref=CASE_REF,
            target_kind="derive",
            expected_expression_refs=("expression:not-content-addressed",),
            match_policy="exact",
            expected_expression_relation="single",
            derivations=target.derivations,
            abstention=None,
            verification_rejection=None,
            review_refs=(REVIEW_REF,),
        )


def test_derivation_blueprints_reject_unsafe_selectors_and_unbounded_lists() -> None:
    for kind, value in (
        ("raw_phrase", "literal:lamp"),
        ("regex", "literal:.*"),
        ("internal_ref_spelling", "literal:op-event"),
        ("context_slot", "runtime_observation:forbidden"),
    ):
        with pytest.raises(ValueError, match="structural selector|forbidden"):
            supervision_module.StructuralSelectorBinding.create(
                selector_handle=0,
                selector_kind=kind,
                value_ref=value,
            )

    target = _derive_target()
    with pytest.raises(ValueError, match="action bound"):
        DerivationBlueprint.create(
            selector_bindings=target.derivations[0].selector_bindings,
            actions=tuple(target.derivations[0].actions[0] for _ in range(MAX_BLUEPRINT_ACTIONS + 1)),
            root_local_refs=target.derivations[0].root_local_refs,
            expected_expression_ref=target.derivations[0].expected_expression_ref,
            source_assignment_blueprint=target.derivations[0].source_assignment_blueprint,
        )
    with pytest.raises(ValueError, match="derivation bound"):
        ProposalTarget.create(
            source_case_ref=CASE_REF,
            target_kind="derive",
            expected_expression_refs=target.expected_expression_refs,
            match_policy="exact",
            expected_expression_relation="single",
            derivations=tuple(target.derivations[0] for _ in range(MAX_DERIVATIONS_PER_CASE + 1)),
            abstention=None,
            verification_rejection=None,
            review_refs=(REVIEW_REF,),
        )


def test_realization_alignment_is_exact_bounded_and_never_input_as_output_gold() -> None:
    row = _realization()
    assert row.authorized_surface[4:8] == "lamp"

    invalid = deepcopy(row.as_dict())
    invalid["alignments"][0]["surface_end"] = 9
    with pytest.raises(ValueError, match="alignment|canonical"):
        RealizationRow.from_dict(invalid)

    with pytest.raises(ValueError, match="literal authority"):
        LiteralAlignment.create(
            slot_ref="response_slot:subject",
            literal_source_ref="input_surface:case-1",
            surface_start=4,
            surface_end=8,
        )

    with pytest.raises((TypeError, ValueError), match="integer|span"):
        LiteralAlignment.create(
            slot_ref="response_slot:subject",
            literal_source_ref="reviewed_literal:0123456789abcdef01234567",
            surface_start=float("nan"),
            surface_end=8,
        )


def test_realization_response_subject_is_closed_complete_and_safe_for_r5_boundaries() -> None:
    row = _realization()
    conflict = ExpressionSetResponseSubject.create(
        expected_expression_relation="conflict",
        expression_refs=(
            "expression:0123456789abcdef01234567",
            "expression:1123456789abcdef01234567",
        ),
    )
    conflict_row = _recreate_realization(row, response_subject=conflict)
    assert conflict_row.response_signature_ref != row.response_signature_ref

    gap = TypedGapResponseSubject.create(
        typed_gap=TypedAbstention.create(
            gap_kind_ref="gap_kind:unresolved_designation",
            critical=True,
            earliest_owner="orient",
            safe_disposition="frontier",
        )
    )
    gap_surface = "I need a reviewed designation before I can answer."
    gap_slot = RealizationSlot.create(
        slot_ref="response_slot:gap",
        semantic_ref=gap.typed_gap.abstention_ref,
        required=True,
        qualifier_refs=(),
    )
    gap_row = _recreate_realization(
        row,
        response_subject=gap,
        bindings=(),
        discourse_action_ref="response_action:report_gap",
        authorized_surface=gap_surface,
        epistemic_status_ref="epistemic_status:unknown",
        semantic_slots=(gap_slot,),
        alignments=(
            LiteralAlignment.create(
                slot_ref=gap_slot.slot_ref,
                literal_source_ref=stable_ref(
                    "reviewed_literal",
                    {
                        "literal": gap_surface,
                        "language": "en",
                        "review_refs": [REVIEW_REF],
                    },
                ),
                surface_start=0,
                surface_end=len(gap_surface),
            ),
        ),
    )
    rejection = VerifierRejectionResponseSubject.create(
        verifier_rejection=VerificationRejection.create(
            input_kind="mutation_payload",
            adversarial_blueprint_ref=None,
            mutation_payload_ref="mutation_payload:0123456789abcdef01234567",
            expected_owner="verify",
            verification_error_code="verification_error:role_kind_mismatch",
            rejection_disposition="reject",
            critical=True,
        )
    )
    rejection_surface = "I rejected that candidate because its roles are invalid."
    rejection_slot = RealizationSlot.create(
        slot_ref="response_slot:verifier_rejection",
        semantic_ref=rejection.verifier_rejection.verification_rejection_ref,
        required=True,
        qualifier_refs=(),
    )
    rejection_row = _recreate_realization(
        row,
        response_subject=rejection,
        bindings=(),
        discourse_action_ref="response_action:reject_candidate",
        authorized_surface=rejection_surface,
        epistemic_status_ref="epistemic_status:unknown",
        semantic_slots=(rejection_slot,),
        alignments=(
            LiteralAlignment.create(
                slot_ref=rejection_slot.slot_ref,
                literal_source_ref=stable_ref(
                    "reviewed_literal",
                    {
                        "literal": rejection_surface,
                        "language": "en",
                        "review_refs": [REVIEW_REF],
                    },
                ),
                surface_start=0,
                surface_end=len(rejection_surface),
            ),
        ),
    )
    assert gap_row.authorized_surface.strip()
    assert rejection_row.authorized_surface.strip()
    assert gap_row.authorized_surface != row.authorized_surface
    assert rejection_row.authorized_surface != row.authorized_surface
    assert RealizationRow.from_json_bytes(gap_row.to_json_bytes()).response_subject == gap
    assert (
        RealizationRow.from_json_bytes(rejection_row.to_json_bytes()).response_subject
        == rejection
    )
    for placeholder in (" ", "[no authorized surface]", "[NO SURFACE]"):
        with pytest.raises(ValueError, match="nonblank reviewed surface"):
            _recreate_realization(row, authorized_surface=placeholder)

    mixed = deepcopy(gap_row.as_dict())
    mixed["response_subject"]["expression_refs"] = [
        "expression:0123456789abcdef01234567"
    ]
    schema = json.loads(
        (SCHEMAS / "r4_realization_supervision.schema.json").read_text(encoding="utf-8")
    )
    assert not Draft202012Validator(schema).is_valid(mixed)
    with pytest.raises(ValueError, match="fields mismatch"):
        RealizationRow.from_dict(mixed)
    with pytest.raises(ValueError, match="epistemic"):
        _recreate_realization(row, epistemic_status_ref="epistemic_status:invented")
    with pytest.raises(ValueError, match="noncanonical response contract"):
        _recreate_realization(gap_row, discourse_action_ref="response_action:answer")
    with pytest.raises(ValueError, match="exact semantic slot"):
        _recreate_realization(
            rejection_row,
            semantic_slots=(row.semantic_slots[0],),
            alignments=(row.alignments[0],),
        )
    with pytest.raises(ValueError, match="reviewed output projection"):
        _recreate_realization(
            gap_row,
            alignments=(
                LiteralAlignment.create(
                    slot_ref=gap_slot.slot_ref,
                    literal_source_ref="reviewed_literal:ffffffffffffffffffffffff",
                    surface_start=0,
                    surface_end=len(gap_surface),
                ),
            ),
        )


def test_realization_file_decoder_rejects_duplicate_identity_and_fifth_variant() -> None:
    rows = tuple(
        _recreate_realization(
            _realization(),
            authorized_surface=f"The lamp is on, variant {index}.",
        )
        for index in range(MAX_REALIZATION_VARIANTS_PER_CASE)
    )
    path = "data/review/r4_1/realization_supervision.jsonl"
    assert supervision_module._record_count_from_authenticated_bytes(
        path, b"".join(row.to_json_bytes() for row in rows)
    ) == MAX_REALIZATION_VARIANTS_PER_CASE
    with pytest.raises(ValueError, match="duplicate row identity"):
        supervision_module._record_count_from_authenticated_bytes(
            path, rows[0].to_json_bytes() + rows[0].to_json_bytes()
        )
    fifth = _recreate_realization(
        _realization(), authorized_surface="The lamp is on, variant five."
    )
    with pytest.raises(ValueError, match="exceeds four variants"):
        supervision_module._record_count_from_authenticated_bytes(
            path, b"".join(row.to_json_bytes() for row in (*rows, fifth))
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

    bounded_deep = b'{"x":' + b"[" * 80 + b"0" + b"]" * 80 + b"}\n"
    with pytest.raises(ValueError, match="nesting"):
        ProposalTarget.from_json_bytes(bounded_deep)
    parser_deep = b'{"x":' + b"[" * 1_500 + b"0" + b"]" * 1_500 + b"}\n"
    with pytest.raises(ValueError, match="JSON|nesting"):
        ProposalTarget.from_json_bytes(parser_deep)

    surrogate = _abstain_target().to_json_bytes().replace(
        b'"gap_kind_ref":"gap_kind:unresolved_designation"',
        b'"gap_kind_ref":"gap_kind:\\ud800"',
        1,
    )
    with pytest.raises(ValueError, match="Unicode|surrogate"):
        ProposalTarget.from_json_bytes(surrogate)

    unicode_row = _recreate_realization(
        _realization(), authorized_surface="The lamp is ön."
    )
    assert RealizationRow.from_json_bytes(unicode_row.to_json_bytes()) == unicode_row


def test_supervision_abi_fields_reject_booleans_at_top_and_nested_boundaries() -> None:
    for filename, value, decoder in (
        ("r4_proposal_supervision.schema.json", _derive_target(), ProposalTarget),
        ("r4_realization_supervision.schema.json", _realization(), RealizationRow),
        ("r4_mutation_contract.schema.json", _mutation(), MutationContract),
        ("r4_review_manifest.schema.json", _manifest(), R4ReviewManifest),
    ):
        schema = json.loads((SCHEMAS / filename).read_text(encoding="utf-8"))
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

        collect_paths(value.as_dict())
        for path in paths:
            wire = deepcopy(value.as_dict())
            cursor = wire
            for part in path[:-1]:
                cursor = cursor[part]
            cursor[path[-1]] = True
            assert not Draft202012Validator(schema).is_valid(wire), (filename, path)
            with pytest.raises((TypeError, ValueError), match="ABI|abi_version"):
                decoder.from_dict(wire)

    manifest = _manifest().as_dict()
    manifest["abi_versions"]["proposal_supervision"] = True
    manifest_schema = json.loads(
        (SCHEMAS / "r4_review_manifest.schema.json").read_text(encoding="utf-8")
    )
    assert not Draft202012Validator(manifest_schema).is_valid(manifest)
    with pytest.raises((TypeError, ValueError), match="ABI|abi_version"):
        R4ReviewManifest.from_dict(manifest)

    raw = _derive_target().to_json_bytes().replace(b'"abi_version":1', b'"abi_version":true', 1)
    with pytest.raises((TypeError, ValueError), match="ABI|abi_version"):
        ProposalTarget.from_json_bytes(raw)
    nested_raw = _derive_target().to_json_bytes().replace(
        b'"selector_bindings":[{"abi_version":1',
        b'"selector_bindings":[{"abi_version":true',
        1,
    )
    with pytest.raises((TypeError, ValueError), match="ABI|abi_version"):
        ProposalTarget.from_json_bytes(nested_raw)


def test_review_provenance_uses_closed_typed_namespaces() -> None:
    target = _derive_target()
    for bad_ref in (
        "runtime_review:0123456789abcdef01234567",
        "unreviewed:0123456789abcdef01234567",
        "runtime_observation:0123456789abcdef01234567",
    ):
        with pytest.raises(ValueError, match="review provenance"):
            ProposalTarget.create(
                source_case_ref=target.source_case_ref,
                target_kind=target.target_kind,
                expected_expression_refs=target.expected_expression_refs,
                match_policy=target.match_policy,
                expected_expression_relation=target.expected_expression_relation,
                derivations=target.derivations,
                abstention=target.abstention,
                verification_rejection=target.verification_rejection,
                review_refs=(bad_ref,),
            )

    manifest = _manifest()
    with pytest.raises(ValueError, match="reviewer"):
        R4ReviewManifest.create(
            review_policy_ref=manifest.review_policy_ref,
            reviewer_refs=("runtime_observation:human-1",),
            reviewed_base_revision=manifest.reviewed_base_revision,
            authority_generation=manifest.authority_generation,
            source_bundle_ref=manifest.source_bundle_ref,
            scenario_source_sha256=manifest.scenario_source_sha256,
            sources=manifest.sources,
            approval_state=manifest.approval_state,
            supersedes_refs=manifest.supersedes_refs,
            runtime_observations_are_source_authority=False,
            bootstrap_outputs_are_source_authority=False,
        )


def test_blueprint_action_abi_enforces_ordered_shapes_and_local_graph_integrity() -> None:
    blueprint = _blueprint()
    wrong_context = supervision_module.StructuralSelectorBinding.create(
        selector_handle=0,
        selector_kind="mode_slot",
        value_ref="mode_slot:observe",
    )
    with pytest.raises(ValueError, match="action shape"):
        DerivationBlueprint.create(
            selector_bindings=(wrong_context, *blueprint.selector_bindings[1:]),
            actions=blueprint.actions,
            root_local_refs=blueprint.root_local_refs,
            expected_expression_ref=blueprint.expected_expression_ref,
            source_assignment_blueprint=blueprint.source_assignment_blueprint,
        )

    duplicate_local = (
        *blueprint.actions[:-1],
        BlueprintAction.create(
            action_index=3,
            action_type="instantiate_operator",
            selector_handles=(2, 3),
        ),
        BlueprintAction.create(action_index=4, action_type="complete_program", selector_handles=()),
    )
    with pytest.raises(ValueError, match="duplicate local"):
        DerivationBlueprint.create(
            selector_bindings=blueprint.selector_bindings,
            actions=duplicate_local,
            root_local_refs=blueprint.root_local_refs,
            expected_expression_ref=blueprint.expected_expression_ref,
            source_assignment_blueprint=blueprint.source_assignment_blueprint,
        )
    assert blueprint.action_abi_ref.startswith("action_abi:")


def test_parent_factories_reject_forged_nested_supervision_values() -> None:
    blueprint = _blueprint()
    valid = blueprint.selector_bindings[0]
    forged = object.__new__(type(valid))
    for name, value in valid.__dict__.items():
        object.__setattr__(forged, name, value)
    object.__setattr__(forged, "binding_ref", "structural_selector_binding_v1:" + "f" * 24)
    with pytest.raises(ValueError, match="canonical"):
        DerivationBlueprint.create(
            selector_bindings=(forged, *blueprint.selector_bindings[1:]),
            actions=blueprint.actions,
            root_local_refs=blueprint.root_local_refs,
            expected_expression_ref=blueprint.expected_expression_ref,
            source_assignment_blueprint=blueprint.source_assignment_blueprint,
        )

    row = _realization()
    forged_binding = object.__new__(RealizationBinding)
    for name, value in row.bindings[0].__dict__.items():
        object.__setattr__(forged_binding, name, value)
    object.__setattr__(forged_binding, "binding_ref", "realization_binding_v1:" + "f" * 24)
    with pytest.raises(ValueError, match="canonical"):
        _recreate_realization(row, bindings=(forged_binding,))


def test_realization_alignment_union_has_independent_authority_and_exact_slot_ownership() -> None:
    row = _realization()
    slot = RealizationSlot.create(
        slot_ref="response_slot:addressee",
        semantic_ref="participant:user",
        required=True,
        qualifier_refs=(),
    )
    reference = ReferenceAlignment.create(
        slot_ref=slot.slot_ref,
        participant_ref="participant:user",
        reference_authority_ref=REVIEW_REF,
        surface_start=0,
        surface_end=3,
    )
    reference_row = _recreate_realization(
        row,
        authorized_surface="You see the lamp.",
        semantic_slots=(slot,),
        alignments=(reference,),
    )
    assert reference_row.alignments == (reference,)

    with pytest.raises(ValueError, match="participant"):
        _recreate_realization(
            row,
            authorized_surface="I see the lamp.",
            semantic_slots=(slot,),
            alignments=(
                ReferenceAlignment.create(
                    slot_ref=slot.slot_ref,
                    participant_ref="participant:system",
                    reference_authority_ref=REVIEW_REF,
                    surface_start=0,
                    surface_end=1,
                ),
            ),
        )
    with pytest.raises(ValueError, match="review_refs"):
        _recreate_realization(
            row,
            alignments=(
                MorphologyAlignment.create(
                    slot_ref="response_slot:subject",
                    morphology_authority_ref="source_review:ffffffffffffffffffffffff",
                    surface_start=4,
                    surface_end=8,
                ),
            ),
        )
    omission = OmissionAlignment.create(
        slot_ref="response_slot:subject",
        omission_authority_ref=REVIEW_REF,
    )
    assert _recreate_realization(row, alignments=(omission,)).alignments == (omission,)

    literal = LiteralAlignment.create(
        slot_ref="response_slot:subject",
        literal_source_ref="effect_literal:0123456789abcdef01234567",
        surface_start=8,
        surface_end=10,
    )
    with pytest.raises(ValueError, match="required semantic slot"):
        _recreate_realization(row, alignments=(row.alignments[0], literal))

    optional_slot = RealizationSlot.create(
        slot_ref="response_slot:optional",
        semantic_ref="entity:lamp",
        required=False,
        qualifier_refs=(),
    )
    optional_designation = DesignationAlignment.create(
        slot_ref=optional_slot.slot_ref,
        designation_fact_ref="designation:1123456789abcdef01234567",
        surface_start=4,
        surface_end=8,
    )
    optional_literal = LiteralAlignment.create(
        slot_ref=optional_slot.slot_ref,
        literal_source_ref="effect_literal:1123456789abcdef01234567",
        surface_start=8,
        surface_end=10,
    )
    with pytest.raises(ValueError, match="optional semantic slot"):
        _recreate_realization(
            row,
            semantic_slots=(optional_slot,),
            alignments=(optional_designation, optional_literal),
        )

    unknown_tag = deepcopy(row.as_dict())
    unknown_tag["alignments"][0]["alignment_kind"] = "surface_copy"
    with pytest.raises(ValueError, match="closed union"):
        RealizationRow.from_dict(unknown_tag)
    self_authored = deepcopy(row.as_dict())
    self_authored["alignments"][0]["source_literal"] = "lamp"
    with pytest.raises(ValueError, match="fields mismatch"):
        RealizationRow.from_dict(self_authored)


def test_realization_signature_is_reconstructed_from_complete_explicit_semantics() -> None:
    row = _realization()
    assert row.response_signature_ref.startswith("response_signature:")
    assert row.bindings[0].binding_key_ref == "binding_key:subject"
    assert row.response_subject.subject_kind == "expression_set"
    assert row.semantic_slots[0].qualifier_refs == ("qualifier:definite",)

    tampered = row.as_dict()
    tampered["bindings"][0]["semantic_ref"] = "entity:other"
    with pytest.raises(ValueError, match="signature|canonical"):
        RealizationRow.from_dict(tampered)

    with pytest.raises(ValueError, match="duplicate"):
        _recreate_realization(row, bindings=(row.bindings[0], row.bindings[0]))
    with pytest.raises(ValueError, match="required semantic slot"):
        _recreate_realization(row, alignments=())


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
        if filename == "r4_proposal_supervision.schema.json":
            for array_schema in (
                schema["properties"]["derivations"],
                schema["$defs"]["blueprint"]["properties"]["selector_bindings"],
                schema["$defs"]["blueprint"]["properties"]["actions"],
                schema["$defs"]["groundedSelectorBinding"]["properties"]["spans"],
                schema["$defs"]["sourceAssignmentBlueprint"]["properties"]["assignments"],
            ):
                assert "uniqueItems" not in array_schema
        if filename == "r4_realization_supervision.schema.json":
            for array_schema in (
                schema["properties"]["bindings"],
                schema["properties"]["semantic_slots"],
                schema["properties"]["alignments"],
            ):
                assert "uniqueItems" not in array_schema
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

    adversarial = []
    manifest = _manifest().as_dict()
    manifest["reviewer_refs"] = ["runtime_observation:human"]
    adversarial.append(("r4_review_manifest.schema.json", manifest, R4ReviewManifest))
    manifest = _manifest().as_dict()
    manifest["sources"][1]["path"] = manifest["sources"][0]["path"]
    adversarial.append(("r4_review_manifest.schema.json", manifest, R4ReviewManifest))
    proposal = _derive_target().as_dict()
    proposal["derivations"][0]["selector_bindings"][0]["selector_kind"] = "raw_phrase"
    proposal["derivations"][0]["selector_bindings"][0]["value_ref"] = "literal:lamp"
    adversarial.append(("r4_proposal_supervision.schema.json", proposal, ProposalTarget))
    proposal = _derive_target().as_dict()
    proposal["derivations"][0]["selector_bindings"][0]["value_ref"] = (
        "proposal_context:resource:semantic_store"
    )
    adversarial.append(("r4_proposal_supervision.schema.json", proposal, ProposalTarget))
    proposal = _derive_target().as_dict()
    proposal["derivations"][0]["selector_bindings"][3]["graph_component_ref"] = (
        "application_frame_slot:.*"
    )
    adversarial.append(("r4_proposal_supervision.schema.json", proposal, ProposalTarget))
    literal_row = _recreate_realization(
        _realization(),
        alignments=(
            LiteralAlignment.create(
                slot_ref="response_slot:subject",
                literal_source_ref="effect_literal:0123456789abcdef01234567",
                surface_start=4,
                surface_end=8,
            ),
        ),
    )
    realization = literal_row.as_dict()
    realization["alignments"][0]["literal_source_ref"] = "effect_literal:lamp"
    adversarial.append(("r4_realization_supervision.schema.json", realization, RealizationRow))
    mutation = _mutation().as_dict()
    mutation["source_case_ref"] = "expanded_case_v2:not-content-addressed"
    adversarial.append(("r4_mutation_contract.schema.json", mutation, MutationContract))
    for filename, corrupt, decoder in adversarial:
        schema = json.loads((SCHEMAS / filename).read_text(encoding="utf-8"))
        assert not Draft202012Validator(schema).is_valid(corrupt), filename
        with pytest.raises((TypeError, ValueError)):
            decoder.from_dict(corrupt)

    proposal = _abstain_target().as_dict()
    proposal["abstention"]["gap_kind_ref"] = "gap_kind:" + "x" * 600
    schema = json.loads((SCHEMAS / "r4_proposal_supervision.schema.json").read_text(encoding="utf-8"))
    assert not Draft202012Validator(schema).is_valid(proposal)
    with pytest.raises(ValueError, match="512 characters"):
        ProposalTarget.from_dict(proposal)

    realization = _realization().as_dict()
    realization["language"] = "en-" + "-".join(("abcdefgh",) * 8)
    schema = json.loads((SCHEMAS / "r4_realization_supervision.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["language"]["maxLength"] == 64
    assert not Draft202012Validator(schema).is_valid(realization)
    with pytest.raises(ValueError, match="64 characters"):
        RealizationRow.from_dict(realization)

    # Cross-action graph integrity and content-address reconstruction are
    # semantic decoder postconditions, not falsely represented as JSON Schema.
    proposal = _derive_target().as_dict()
    proposal["proposal_target_ref"] = "proposal_supervision_v1:" + "f" * 24
    schema = json.loads((SCHEMAS / "r4_proposal_supervision.schema.json").read_text(encoding="utf-8"))
    assert Draft202012Validator(schema).is_valid(proposal)
    assert "semantic postconditions" in schema["$comment"]
    with pytest.raises(ValueError, match="canonical"):
        ProposalTarget.from_dict(proposal)


_REVIEW_MANIFEST_PATH = "data/review/r4_1/REVIEW_MANIFEST.json"
_SCENARIO_SOURCE_PATH = "data/scenarios/use_cases.jsonl"
_REVIEW_CHILD_PATHS = (
    "data/review/r4_1/mutation_contracts.jsonl",
    "data/review/r4_1/proposal_supervision.jsonl",
    "data/review/r4_1/purpose_contract.json",
    "data/review/r4_1/realization_supervision.jsonl",
)


def _purpose_source() -> bytes:
    purposes = ("train", "selection", "calibration", "frozen_test")
    memberships = tuple(
        PurposeMembership.create(
            source_case_ref=f"expanded_case_v2:{index:024x}",
            classification="semantic_supervision",
            purpose=purpose,
            duplicate_risk_group_refs=(),
            diagnostic_reason_ref=None,
            review_refs=(REVIEW_REF,),
        )
        for index, purpose in enumerate(purposes, 1)
    )
    minima = tuple(
        DenominatorMinimum.create(
            denominator_ref=f"denominator:semantic-expression-{purpose}",
            denominator_family="semantic_expression",
            purpose=purpose,
            minimum=1,
            review_refs=(REVIEW_REF,),
        )
        for purpose in purposes
    )
    return PurposeContract.create(
        source_set_ref="r4_source_set_v1:0123456789abcdef01234567",
        memberships=memberships,
        duplicate_risk_groups=(),
        challenge_holdouts=(),
        denominator_minima=minima,
        review_refs=(REVIEW_REF,),
        solver_output_is_authority=False,
    ).to_json_bytes()


def _record_count(path: str, raw: bytes) -> int:
    return 1 if path.endswith(".json") else len(raw.splitlines())


def _bundle_ref(child_bytes: dict[str, bytes], scenario_bytes: bytes) -> str:
    return stable_ref(
        "r4_review_bundle_v1",
        {
            "scenario_source": {
                "path": _SCENARIO_SOURCE_PATH,
                "sha256": hashlib.sha256(scenario_bytes).hexdigest(),
                "record_count": _record_count(_SCENARIO_SOURCE_PATH, scenario_bytes),
            },
            "sources": [
                {
                    "path": path,
                    "sha256": hashlib.sha256(child_bytes[path]).hexdigest(),
                    "record_count": _record_count(path, child_bytes[path]),
                }
                for path in _REVIEW_CHILD_PATHS
            ],
        },
    )


def _write_review_tree(
    tmp_path: Path,
    *,
    count_override: tuple[str, int] | None = None,
    sha_override: tuple[str, str] | None = None,
    bundle_ref: str | None = None,
) -> tuple[Path, R4ReviewManifest, dict[str, bytes]]:
    root = tmp_path / "candidate"
    child_bytes = {
        _REVIEW_CHILD_PATHS[0]: _mutation().to_json_bytes(),
        _REVIEW_CHILD_PATHS[1]: _derive_target().to_json_bytes(),
        _REVIEW_CHILD_PATHS[2]: _purpose_source(),
        _REVIEW_CHILD_PATHS[3]: _realization().to_json_bytes(),
    }
    scenario_bytes = (ROOT / _SCENARIO_SOURCE_PATH).read_bytes()
    all_bytes = {_SCENARIO_SOURCE_PATH: scenario_bytes, **child_bytes}
    for relative, raw in all_bytes.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    sources = []
    for index, path in enumerate(_REVIEW_CHILD_PATHS, 1):
        raw = child_bytes[path]
        count = _record_count(path, raw)
        sha = hashlib.sha256(raw).hexdigest()
        if count_override is not None and count_override[0] == path:
            count = count_override[1]
        if sha_override is not None and sha_override[0] == path:
            sha = sha_override[1]
        sources.append(
            ReviewSourceFile.create(
                source_ref=f"reviewed_source:{index:024x}",
                path=path,
                sha256=sha,
                record_count=count,
                review_refs=(REVIEW_REF,),
            )
        )
    manifest = R4ReviewManifest.create(
        review_policy_ref="review_policy:r4_1",
        reviewer_refs=("reviewer:human-1",),
        reviewed_base_revision="a" * 40,
        authority_generation="authority-v1-2026-07-29",
        source_bundle_ref=bundle_ref or _bundle_ref(child_bytes, scenario_bytes),
        scenario_source_sha256=hashlib.sha256(scenario_bytes).hexdigest(),
        sources=tuple(sources),
        approval_state="approved",
        supersedes_refs=("r4_build_v4:0123456789abcdef01234567",),
        runtime_observations_are_source_authority=False,
        bootstrap_outputs_are_source_authority=False,
    )
    manifest_path = root / _REVIEW_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest.to_json_bytes())
    return root, manifest, all_bytes


def test_review_bundle_reads_exactly_five_reviewed_sources_plus_scenario_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, manifest, all_bytes = _write_review_tree(tmp_path)
    calls: list[str] = []
    real_reader = supervision_module._read_regular_file_once

    def counted_reader(project_root: Path, relative_path: str, *, maximum: int) -> bytes:
        calls.append(relative_path)
        return real_reader(project_root, relative_path, maximum=maximum)

    monkeypatch.setattr(supervision_module, "_read_regular_file_once", counted_reader)
    bundle = supervision_module.load_authenticated_r4_review_bundle(root)

    assert bundle.manifest == manifest
    assert bundle.reviewed_base_revision == manifest.reviewed_base_revision
    assert bundle.authority_generation == manifest.authority_generation
    assert bundle.source_bundle_ref == manifest.source_bundle_ref
    assert bundle.read_count == 6
    assert tuple(calls) == (_REVIEW_MANIFEST_PATH, *_REVIEW_CHILD_PATHS, _SCENARIO_SOURCE_PATH)
    assert len(calls) == len(set(calls))
    assert bundle.source_bytes == MappingProxyType(all_bytes)
    assert bundle.manifest_bytes == manifest.to_json_bytes()
    assert bundle.manifest_sha256 == hashlib.sha256(bundle.manifest_bytes).hexdigest()
    assert bundle.aggregate_bytes == len(bundle.manifest_bytes) + sum(map(len, all_bytes.values()))
    assert supervision_module.MAX_R4_REVIEW_BUNDLE_BYTES == (
        6 * supervision_module.MAX_R4_SOURCE_BYTES
    )
    with pytest.raises(FrozenInstanceError):
        bundle.read_count = 7
    with pytest.raises(TypeError, match="created only by load_authenticated"):
        type(bundle)()


def test_authenticated_review_bundle_has_no_public_mint_api(tmp_path: Path) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    bundle_type = supervision_module.AuthenticatedR4ReviewBundle
    assert "create" not in bundle_type.__dict__
    assert "_mint_authenticated_r4_review_bundle" not in supervision_module.__all__
    bundle = supervision_module.load_authenticated_r4_review_bundle(root)
    with pytest.raises(TypeError, match="created only by load_authenticated"):
        bundle_type()


def test_reader_failure_prevents_authenticated_bundle_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _write_review_tree(tmp_path)

    def disabled_reader(project_root: Path, relative_path: str, *, maximum: int) -> bytes:
        del project_root, relative_path, maximum
        raise ValueError("reader disabled")

    monkeypatch.setattr(supervision_module, "_read_regular_file_once", disabled_reader)
    with pytest.raises(ValueError, match="reader disabled"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_retries_eintr_and_partial_reads_without_reopening(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    real_open = supervision_module.os.open
    real_read = supervision_module.os.read
    open_calls = 0
    read_calls = 0
    interruptions: list[OSError] = [
        InterruptedError(errno.EINTR, "interrupted"),
        OSError(errno.EINTR, "interrupted"),
    ]

    def counted_open(path, flags):
        nonlocal open_calls
        open_calls += 1
        return real_open(path, flags)

    def fragmented_read(descriptor: int, size: int) -> bytes:
        nonlocal read_calls
        read_calls += 1
        if interruptions:
            raise interruptions.pop(0)
        return real_read(descriptor, min(size, 4_096))

    monkeypatch.setattr(supervision_module.os, "open", counted_open)
    monkeypatch.setattr(supervision_module.os, "read", fragmented_read)
    bundle = supervision_module.load_authenticated_r4_review_bundle(root)

    assert bundle.read_count == 6
    assert open_calls == 6
    assert not interruptions
    assert read_calls > open_calls
    assert read_calls <= (
        supervision_module.R4_REVIEW_BUNDLE_READ_COUNT
        * supervision_module.MAX_R4_SOURCE_READ_SYSCALLS
    )


def test_review_bundle_bounds_perpetual_eintr_without_reopening(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    real_open = supervision_module.os.open
    open_calls = 0
    read_calls = 0

    def counted_open(path, flags):
        nonlocal open_calls
        open_calls += 1
        return real_open(path, flags)

    def interrupted_read(descriptor: int, size: int) -> bytes:
        nonlocal read_calls
        del descriptor, size
        read_calls += 1
        raise OSError(errno.EINTR, "interrupted")

    monkeypatch.setattr(supervision_module.os, "open", counted_open)
    monkeypatch.setattr(supervision_module.os, "read", interrupted_read)
    with pytest.raises(ValueError, match="bounded read syscall count"):
        supervision_module.load_authenticated_r4_review_bundle(root)

    assert open_calls == 1
    assert read_calls == supervision_module.MAX_R4_SOURCE_READ_SYSCALLS


def test_review_bundle_validates_each_nonmanifest_source_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    real_validator = supervision_module._record_count_from_authenticated_bytes
    real_manifest_decoder = R4ReviewManifest.from_json_bytes
    validations: list[str] = []
    manifest_decodes = 0

    def counted_validator(path: str, raw: bytes) -> int:
        validations.append(path)
        return real_validator(path, raw)

    def counted_manifest_decoder(cls, raw: bytes) -> R4ReviewManifest:
        nonlocal manifest_decodes
        del cls
        manifest_decodes += 1
        return real_manifest_decoder(raw)

    monkeypatch.setattr(
        supervision_module, "_record_count_from_authenticated_bytes", counted_validator
    )
    monkeypatch.setattr(
        R4ReviewManifest, "from_json_bytes", classmethod(counted_manifest_decoder)
    )
    supervision_module.load_authenticated_r4_review_bundle(root)
    assert manifest_decodes == 1
    assert tuple(validations) == (*_REVIEW_CHILD_PATHS, _SCENARIO_SOURCE_PATH)


def test_review_bundle_rejects_missing_source(tmp_path: Path) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    (root / _REVIEW_CHILD_PATHS[0]).unlink()
    with pytest.raises(ValueError, match="unavailable|missing"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_extra_source_membership(tmp_path: Path) -> None:
    root, manifest, _ = _write_review_tree(tmp_path)
    row = deepcopy(manifest.as_dict())
    extra = deepcopy(row["sources"][-1])
    extra["path"] = "artifacts/r4/observed-extra.jsonl"
    extra["source_ref"] = "reviewed_source:" + "f" * 24
    row["sources"].append(extra)
    (root / _REVIEW_MANIFEST_PATH).write_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="sources exceeds|exact R4.1 reviewed source|source path"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_duplicate_source_membership(tmp_path: Path) -> None:
    root, manifest, _ = _write_review_tree(tmp_path)
    row = deepcopy(manifest.as_dict())
    row["sources"][1]["path"] = row["sources"][0]["path"]
    (root / _REVIEW_MANIFEST_PATH).write_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="duplicate identities|every exact R4.1"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_lexical_path_escape(tmp_path: Path) -> None:
    root, manifest, _ = _write_review_tree(tmp_path)
    row = deepcopy(manifest.as_dict())
    row["sources"][0]["path"] = "data/review/r4_1/../../../artifacts/r4/episodes.jsonl"
    (root / _REVIEW_MANIFEST_PATH).write_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="source path|approved namespace"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_wrong_record_count(tmp_path: Path) -> None:
    path = _REVIEW_CHILD_PATHS[1]
    root, _, _ = _write_review_tree(tmp_path, count_override=(path, 2))
    with pytest.raises(ValueError, match="record count"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_wrong_source_sha(tmp_path: Path) -> None:
    path = _REVIEW_CHILD_PATHS[3]
    root, _, _ = _write_review_tree(tmp_path, sha_override=(path, "0" * 64))
    with pytest.raises(ValueError, match="SHA-256"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_wrong_source_bundle_ref(tmp_path: Path) -> None:
    root, _, _ = _write_review_tree(
        tmp_path, bundle_ref="r4_review_bundle_v1:" + "f" * 24
    )
    with pytest.raises(ValueError, match="source-bundle"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_symlink_escape_and_hardlink_alias(tmp_path: Path) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    target = root / _REVIEW_CHILD_PATHS[0]
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.fail("test host must support the symlink safety contract")
    with pytest.raises(ValueError, match="link|reparse|regular"):
        supervision_module.load_authenticated_r4_review_bundle(root)

    root, _, _ = _write_review_tree(tmp_path / "hardlink")
    target = root / _REVIEW_CHILD_PATHS[0]
    alias = tmp_path / "source-alias.jsonl"
    try:
        os.link(target, alias)
    except OSError:
        pytest.fail("test host must support the hardlink safety contract")
    with pytest.raises(ValueError, match="hardlink|link count"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_short_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    real_reader = supervision_module._read_descriptor_bytes

    def short_reader(descriptor: int, path: Path, *, maximum: int) -> bytes:
        raw = real_reader(descriptor, path, maximum=maximum)
        return raw[:-1]

    monkeypatch.setattr(supervision_module, "_read_descriptor_bytes", short_reader)
    with pytest.raises(ValueError, match="short read|changed while being read"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_growth_after_stat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    real_reader = supervision_module._read_descriptor_bytes

    def growing_reader(descriptor: int, path: Path, *, maximum: int) -> bytes:
        return real_reader(descriptor, path, maximum=maximum) + b"x"

    monkeypatch.setattr(supervision_module, "_read_descriptor_bytes", growing_reader)
    with pytest.raises(ValueError, match="grew|changed while being read"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_hostile_file_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    target = root / _REVIEW_CHILD_PATHS[1]
    real_probe = supervision_module._path_identity
    probes = 0

    def replacement_probe(path: Path):
        nonlocal probes
        identity = real_probe(path)
        if path == target:
            probes += 1
            if probes == 2:
                return identity._replace(file_index=identity.file_index + 1)
        return identity

    monkeypatch.setattr(supervision_module, "_path_identity", replacement_probe)
    with pytest.raises(ValueError, match="replaced|changed while being read"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_ancestor_directory_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    target = root / _REVIEW_MANIFEST_PATH
    ancestor = target.parent
    real_probe = supervision_module._path_identity
    probes = 0

    def replacement_probe(path: Path):
        nonlocal probes
        identity = real_probe(path)
        if path == ancestor:
            probes += 1
            if probes == 2:
                return identity._replace(file_index=identity.file_index + 1)
        return identity

    monkeypatch.setattr(supervision_module, "_path_identity", replacement_probe)
    with pytest.raises(ValueError, match="ancestor.*replaced|changed while being read"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_crlf_jsonl_normalization(tmp_path: Path) -> None:
    root, _, _ = _write_review_tree(tmp_path)
    proposal_path = root / _REVIEW_CHILD_PATHS[1]
    proposal_path.write_bytes(proposal_path.read_bytes().replace(b"\n", b"\r\n"))
    with pytest.raises(ValueError, match="LF-only|canonical JSONL"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_self_referential_commit_identity(tmp_path: Path) -> None:
    root, manifest, _ = _write_review_tree(tmp_path)
    row = manifest.as_dict()
    row["containing_commit_revision"] = "b" * 40
    (root / _REVIEW_MANIFEST_PATH).write_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="self-referential|unknown fields"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_rejects_unapproved_manifest_state(tmp_path: Path) -> None:
    root, manifest, _ = _write_review_tree(tmp_path)
    row = manifest.as_dict()
    row["approval_state"] = "draft"
    (root / _REVIEW_MANIFEST_PATH).write_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="approval_state must be approved"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_review_bundle_enforces_existing_byte_record_depth_and_ref_bounds(
    tmp_path: Path,
) -> None:
    proposal_path = _REVIEW_CHILD_PATHS[1]

    root, _, _ = _write_review_tree(tmp_path / "bytes")
    (root / proposal_path).write_bytes(
        b"x" * (supervision_module.MAX_R4_SOURCE_BYTES + 1)
    )
    with pytest.raises(ValueError, match="byte bounds"):
        supervision_module.load_authenticated_r4_review_bundle(root)

    root, _, _ = _write_review_tree(tmp_path / "records")
    (root / proposal_path).write_bytes(_derive_target().to_json_bytes() * 4_097)
    with pytest.raises(ValueError, match="record count bounds"):
        supervision_module.load_authenticated_r4_review_bundle(root)

    root, _, _ = _write_review_tree(tmp_path / "depth")
    nested: object = "leaf"
    for _ in range(66):
        nested = [nested]
    (root / proposal_path).write_bytes(
        json.dumps({"nested": nested}, separators=(",", ":")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="nesting exceeds"):
        supervision_module.load_authenticated_r4_review_bundle(root)

    root, _, _ = _write_review_tree(tmp_path / "refs")
    row = _derive_target().as_dict()
    row["review_refs"] = [f"source_review:{index:024x}" for index in range(129)]
    (root / proposal_path).write_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    with pytest.raises(ValueError, match="128 rows"):
        supervision_module.load_authenticated_r4_review_bundle(root)


def test_sr2_selector_binding_union_uses_dense_handles_and_exact_grounding() -> None:
    span = supervision_module.SourceSpan.create(
        surface_ref="reviewed_surface:0123456789abcdef01234567",
        start=0,
        end=4,
    )
    grounded = supervision_module.GroundedSelectorBinding.create(
        selector_handle=0,
        selector_kind="contribution_slot",
        source_case_ref=CASE_REF,
        surface_ref=span.surface_ref,
        graph_component_ref="contribution_slot:predicate-0",
        semantic_kind_ref="semantic_kind:event_type",
        spans=(span,),
        source_selector_kind="contribution",
        source_selector_ref="contribution_slot:predicate-0",
    )
    structural = supervision_module.StructuralSelectorBinding.create(
        selector_handle=1,
        selector_kind="local_node",
        value_ref="application:0",
    )
    assert supervision_module.selector_binding_from_dict(grounded.as_dict()) == grounded
    assert supervision_module.selector_binding_from_dict(structural.as_dict()) == structural
    structural_with_evidence = structural.as_dict()
    structural_with_evidence["spans"] = [span.as_dict()]
    with pytest.raises(ValueError, match="fields mismatch"):
        supervision_module.selector_binding_from_dict(structural_with_evidence)
    with pytest.raises(TypeError, match="source_case_ref"):
        supervision_module.GroundedSelectorBinding.create(
            selector_handle=0,
            selector_kind="contribution_slot",
            surface_ref=span.surface_ref,
            graph_component_ref="contribution_slot:predicate-0",
            semantic_kind_ref="semantic_kind:event_type",
            spans=(span,),
            source_selector_kind="contribution",
            source_selector_ref="contribution_slot:predicate-0",
        )

    with pytest.raises(ValueError, match="surface"):
        supervision_module.GroundedSelectorBinding.create(
            selector_handle=0,
            selector_kind="contribution_slot",
            source_case_ref=CASE_REF,
            surface_ref=span.surface_ref,
            graph_component_ref="contribution_slot:predicate-0",
            semantic_kind_ref="semantic_kind:event_type",
            spans=(
                supervision_module.SourceSpan.create(
                    surface_ref="reviewed_surface:1123456789abcdef01234567",
                    start=0,
                    end=4,
                ),
            ),
            source_selector_kind="contribution",
            source_selector_ref="contribution_slot:predicate-0",
        )
    for changes, error in (
        ({"graph_component_ref": "reference_slot:0"}, "component"),
        ({"graph_component_ref": "contribution_slot:.*"}, "component"),
        ({"semantic_kind_ref": "role:event"}, "semantic kind"),
        ({"semantic_kind_ref": "semantic_kind:resource:event"}, "semantic kind"),
        ({"source_selector_kind": "raw_phrase"}, "source selector"),
        ({"source_selector_ref": "observed_program:forbidden"}, "source selector"),
        ({"source_selector_ref": "contribution_slot:.*"}, "source selector"),
    ):
        values = {
            "selector_handle": 0,
            "selector_kind": "contribution_slot",
            "source_case_ref": CASE_REF,
            "surface_ref": span.surface_ref,
            "graph_component_ref": "contribution_slot:predicate-0",
            "semantic_kind_ref": "semantic_kind:event_type",
            "spans": (span,),
            "source_selector_kind": "contribution",
            "source_selector_ref": "contribution_slot:predicate-0",
            **changes,
        }
        with pytest.raises((TypeError, ValueError), match=error):
            supervision_module.GroundedSelectorBinding.create(**values)
    with pytest.raises((TypeError, ValueError), match="positive|span"):
        supervision_module.SourceSpan.create(
            surface_ref=span.surface_ref,
            start=4,
            end=4,
        )
    for kind, value in (
        ("raw_phrase", "literal:lamp"),
        ("regex", "literal:.*"),
        ("internal_ref_spelling", "literal:op-event"),
        ("local_node", "bootstrap_candidate:forbidden"),
        ("local_node", "application:.*"),
        ("context_slot", "proposal_context:resource:semantic_store"),
    ):
        with pytest.raises(ValueError, match="structural selector|forbidden|regex|internal-ref"):
            supervision_module.StructuralSelectorBinding.create(
                selector_handle=1,
                selector_kind=kind,
                value_ref=value,
            )

    schema = json.loads(
        (SCHEMAS / "r4_proposal_supervision.schema.json").read_text(encoding="utf-8")
    )
    valid_target = _sr2_derive_target(
        ("expression:0123456789abcdef01234567",),
        (_sr2_blueprint("expression:0123456789abcdef01234567"),),
    ).as_dict()
    invalid_structural = deepcopy(valid_target)
    invalid_structural["derivations"][0]["selector_bindings"][0]["spans"] = [
        span.as_dict()
    ]
    assert not Draft202012Validator(schema).is_valid(invalid_structural)
    with pytest.raises(ValueError, match="fields mismatch"):
        supervision_module.ProposalTarget.from_dict(invalid_structural)
    invalid_grounded = deepcopy(valid_target)
    invalid_grounded["derivations"][0]["selector_bindings"][3].pop("surface_ref")
    assert not Draft202012Validator(schema).is_valid(invalid_grounded)
    with pytest.raises(ValueError, match="fields mismatch"):
        supervision_module.ProposalTarget.from_dict(invalid_grounded)


def test_sr2_blueprint_resolves_handle_table_before_program_shape_validation() -> None:
    blueprint = _sr2_blueprint("expression:0123456789abcdef01234567")
    assert tuple(row.selector_handle for row in blueprint.selector_bindings) == tuple(
        range(len(blueprint.selector_bindings))
    )
    assert blueprint.actions[0].selector_handles == (0,)
    with pytest.raises(ValueError, match="duplicate"):
        supervision_module.BlueprintAction.create(
            action_index=0,
            action_type="instantiate_operator",
            selector_handles=(0, 0),
        )
    with pytest.raises(TypeError, match="int|integer"):
        supervision_module.BlueprintAction.create(
            action_index=0,
            action_type="select_context",
            selector_handles=(True,),
        )

    bindings = blueprint.selector_bindings
    duplicate = object.__new__(type(bindings[1]))
    for name, value in bindings[1].__dict__.items():
        object.__setattr__(duplicate, name, value)
    object.__setattr__(duplicate, "selector_handle", 0)
    with pytest.raises((TypeError, ValueError), match="dense|canonical"):
        supervision_module.DerivationBlueprint.create(
            selector_bindings=(bindings[0], duplicate, *bindings[2:]),
            actions=blueprint.actions,
            root_local_refs=blueprint.root_local_refs,
            expected_expression_ref=blueprint.expected_expression_ref,
            source_assignment_blueprint=blueprint.source_assignment_blueprint,
        )
    bad_action = supervision_module.BlueprintAction.create(
        action_index=0,
        action_type="select_context",
        selector_handles=(99,),
    )
    with pytest.raises(ValueError, match="unbound"):
        supervision_module.DerivationBlueprint.create(
            selector_bindings=bindings,
            actions=(bad_action, *blueprint.actions[1:]),
            root_local_refs=blueprint.root_local_refs,
            expected_expression_ref=blueprint.expected_expression_ref,
            source_assignment_blueprint=blueprint.source_assignment_blueprint,
        )
    unused_structural = supervision_module.StructuralSelectorBinding.create(
        selector_handle=len(bindings),
        selector_kind="local_node",
        value_ref="application:unused",
    )
    unused_grounded = supervision_module.GroundedSelectorBinding.create(
        selector_handle=len(bindings),
        selector_kind="contribution_slot",
        source_case_ref=CASE_REF,
        surface_ref="reviewed_surface:0123456789abcdef01234567",
        graph_component_ref="contribution_slot:unused",
        semantic_kind_ref="semantic_kind:event_type",
        spans=(
            supervision_module.SourceSpan.create(
                surface_ref="reviewed_surface:0123456789abcdef01234567",
                start=0,
                end=4,
            ),
        ),
        source_selector_kind="contribution",
        source_selector_ref="contribution_slot:unused",
    )
    for unused in (unused_structural, unused_grounded):
        with pytest.raises(ValueError, match="every selector binding"):
            supervision_module.DerivationBlueprint.create(
                selector_bindings=(*bindings, unused),
                actions=blueprint.actions,
                root_local_refs=blueprint.root_local_refs,
                expected_expression_ref=blueprint.expected_expression_ref,
                source_assignment_blueprint=blueprint.source_assignment_blueprint,
            )


def test_sr2_source_assignments_are_complete_and_critical_residuals_are_not_executable() -> None:
    assert supervision_module._SOURCE_ASSIGNMENT_COMPATIBILITY == frozenset(
        {
            ("predicate", "predicate", "instantiate_operator"),
            ("anchor", "role", "bind_role"),
            ("literal", "role", "bind_role"),
            ("qualifier", "qualifier", "bind_role"),
            ("reference", "reference", "bind_reference"),
            ("scope", "scope", "attach_scope"),
            ("connector", "connector", "bind_nested_application"),
            ("discourse", "discourse", "select_mode"),
            ("discourse", "discourse", "bind_nested_application"),
            ("discourse", "discourse", "propose_transition"),
            ("open_variable", "role", "project_variable"),
            ("binder", "role", "project_variable"),
        }
    )
    entry = supervision_module.SourceAssignmentEntry.create(
        source_unit_ref="unit:0",
        contribution_slot_ref="contribution_slot:predicate-3",
        contribution_kind="predicate",
        assignment_kind="predicate",
        target_action_index=2,
        target_role_ref=None,
        residual_kind=None,
        critical=False,
    )
    assignments = supervision_module.SourceAssignmentBlueprint.create(
        observed_source_unit_refs=("unit:0",),
        assignments=(entry,),
    )
    assert assignments.assignments[0].source_unit_ref == "unit:0"
    with pytest.raises(ValueError, match="residual"):
        supervision_module.SourceAssignmentEntry.create(
            source_unit_ref="unit:0",
            contribution_slot_ref="contribution_slot:residual-0",
            contribution_kind="anchor",
            assignment_kind="residual",
            target_action_index=None,
            target_role_ref=None,
            residual_kind="discourse",
            critical=True,
        )
    with pytest.raises(ValueError, match="cover"):
        supervision_module.SourceAssignmentBlueprint.create(
            observed_source_unit_refs=("unit:0", "unit:1"),
            assignments=(entry,),
        )
    with pytest.raises(ValueError, match="duplicate|cover"):
        supervision_module.SourceAssignmentBlueprint.create(
            observed_source_unit_refs=("unit:0",),
            assignments=(entry, entry),
        )

    wrong_pointer = supervision_module.SourceAssignmentEntry.create(
        source_unit_ref="unit:0",
        contribution_slot_ref="contribution_slot:fake",
        contribution_kind="predicate",
        assignment_kind="predicate",
        target_action_index=2,
        target_role_ref=None,
        residual_kind=None,
        critical=False,
    )
    with pytest.raises(ValueError, match="contribution slot"):
        _sr2_blueprint(
            "expression:0123456789abcdef01234567",
            source_assignment_blueprint=supervision_module.SourceAssignmentBlueprint.create(
                observed_source_unit_refs=("unit:0",),
                assignments=(wrong_pointer,),
            ),
        )
    wrong_action = supervision_module.SourceAssignmentEntry.create(
        source_unit_ref="unit:0",
        contribution_slot_ref="contribution_slot:predicate-3",
        contribution_kind="scope",
        assignment_kind="scope",
        target_action_index=2,
        target_role_ref=None,
        residual_kind=None,
        critical=False,
    )
    with pytest.raises(ValueError, match="incompatible"):
        _sr2_blueprint(
            "expression:0123456789abcdef01234567",
            source_assignment_blueprint=supervision_module.SourceAssignmentBlueprint.create(
                observed_source_unit_refs=("unit:0",),
                assignments=(wrong_action,),
            ),
        )

    base = _sr2_blueprint("expression:0123456789abcdef01234567")
    grounded_mode = supervision_module.GroundedSelectorBinding.create(
        selector_handle=1,
        selector_kind="mode_slot",
        source_case_ref=CASE_REF,
        surface_ref="reviewed_surface:0123456789abcdef01234567",
        graph_component_ref="mode_slot:observe",
        semantic_kind_ref="semantic_kind:discourse",
        spans=(
            supervision_module.SourceSpan.create(
                surface_ref="reviewed_surface:0123456789abcdef01234567",
                start=0,
                end=4,
            ),
        ),
        source_selector_kind="contribution",
        source_selector_ref="contribution_slot:mode-0",
    )
    discourse = supervision_module.SourceAssignmentEntry.create(
        source_unit_ref="unit:0",
        contribution_slot_ref="contribution_slot:mode-0",
        contribution_kind="discourse",
        assignment_kind="discourse",
        target_action_index=1,
        target_role_ref=None,
        residual_kind=None,
        critical=False,
    )
    discourse_blueprint = supervision_module.DerivationBlueprint.create(
        selector_bindings=(base.selector_bindings[0], grounded_mode, *base.selector_bindings[2:]),
        actions=base.actions,
        root_local_refs=base.root_local_refs,
        expected_expression_ref=base.expected_expression_ref,
        source_assignment_blueprint=supervision_module.SourceAssignmentBlueprint.create(
            observed_source_unit_refs=("unit:0",),
            assignments=(discourse,),
        ),
    )
    assert discourse_blueprint.source_assignment_blueprint.assignments == (discourse,)

    critical = supervision_module.SourceAssignmentEntry.create(
        source_unit_ref="unit:0",
        contribution_slot_ref="contribution_slot:residual-0",
        contribution_kind="discourse",
        assignment_kind="residual",
        target_action_index=None,
        target_role_ref=None,
        residual_kind="discourse",
        critical=True,
    )
    critical_blueprint = _sr2_blueprint(
        "expression:0123456789abcdef01234567",
        source_assignment_blueprint=supervision_module.SourceAssignmentBlueprint.create(
            observed_source_unit_refs=("unit:0",),
            assignments=(critical,),
        ),
    )
    with pytest.raises(ValueError, match="critical residual|executable"):
        _sr2_derive_target(("expression:0123456789abcdef01234567",), (critical_blueprint,))


def test_sr2_proposal_relation_and_verification_rejection_are_exact_and_distinct() -> None:
    expression_a = "expression:0123456789abcdef01234567"
    expression_b = "expression:1123456789abcdef01234567"
    single = _sr2_derive_target((expression_a,), (_sr2_blueprint(expression_a),))
    assert single.match_policy == "exact"
    assert single.expected_expression_relation == "single"
    class _StringLike(str):
        pass

    with pytest.raises(TypeError, match="exact str"):
        supervision_module.ProposalTarget.create(
            source_case_ref=single.source_case_ref,
            target_kind=single.target_kind,
            expected_expression_refs=single.expected_expression_refs,
            match_policy=_StringLike("exact"),
            expected_expression_relation=single.expected_expression_relation,
            derivations=single.derivations,
            abstention=None,
            verification_rejection=None,
            review_refs=single.review_refs,
        )

    conflict = _sr2_derive_target(
        (expression_a, expression_b),
        (_sr2_blueprint(expression_a), _sr2_blueprint(expression_b, local_suffix="1")),
    )
    assert conflict.expected_expression_relation == "conflict"
    with pytest.raises(ValueError, match="alternative|mapped|conflict"):
        _sr2_derive_target(
            (expression_a, expression_b),
            (_sr2_blueprint(expression_a, roots=("application:0", "application:1")),),
        )
    with pytest.raises(ValueError, match="case"):
        supervision_module.ProposalTarget.create(
            source_case_ref="expanded_case_v2:3123456789abcdef01234567",
            target_kind="derive",
            expected_expression_refs=(expression_a,),
            match_policy="exact",
            expected_expression_relation="single",
            derivations=(_sr2_blueprint(expression_a),),
            abstention=None,
            verification_rejection=None,
            review_refs=(REVIEW_REF,),
        )

    rejection = supervision_module.VerificationRejection.create(
        input_kind="adversarial_blueprint",
        adversarial_blueprint_ref="adversarial_blueprint:0123456789abcdef01234567",
        mutation_payload_ref=None,
        expected_owner="verify",
        verification_error_code="verification_error:invalid-role",
        rejection_disposition="reject",
        critical=True,
    )
    target = supervision_module.ProposalTarget.create(
        source_case_ref="expanded_case_v2:2123456789abcdef01234567",
        target_kind="verification_rejection",
        expected_expression_refs=(),
        match_policy="exact",
        expected_expression_relation="none",
        derivations=(),
        abstention=None,
        verification_rejection=rejection,
        review_refs=(REVIEW_REF,),
    )
    assert target.verification_rejection == rejection
    assert target.abstention is None
    proposal_schema = json.loads(
        (SCHEMAS / "r4_proposal_supervision.schema.json").read_text(encoding="utf-8")
    )
    assert Draft202012Validator(proposal_schema).is_valid(target.as_dict())
    assert supervision_module.ProposalTarget.from_json_bytes(target.to_json_bytes()) == target
    legacy = target.as_dict()
    legacy["expression_relation"] = "exact"
    with pytest.raises(ValueError, match="fields mismatch"):
        supervision_module.ProposalTarget.from_dict(legacy)
    corrupt = target.as_dict()
    corrupt["verification_rejection"]["observed_verifier_result"] = "reject"
    with pytest.raises(ValueError, match="fields mismatch"):
        supervision_module.ProposalTarget.from_dict(corrupt)
    with pytest.raises(ValueError, match="owner"):
        supervision_module.VerificationRejection.create(
            input_kind="adversarial_blueprint",
            adversarial_blueprint_ref="adversarial_blueprint:0123456789abcdef01234567",
            mutation_payload_ref=None,
            expected_owner="exact-verifier",
            verification_error_code="verification_error:invalid-role",
            rejection_disposition="reject",
            critical=True,
        )
    with pytest.raises(ValueError, match="adversarial blueprint or mutation payload"):
        supervision_module.VerificationRejection.create(
            input_kind="gap",
            adversarial_blueprint_ref=None,
            mutation_payload_ref=None,
            expected_owner="verify",
            verification_error_code="verification_error:invalid-role",
            rejection_disposition="reject",
            critical=True,
        )


def test_sr1_r4_source_abi_registry_states_are_exact_and_nonactivating() -> None:
    registry = (ROOT / "docs/ABI_REGISTRY.md").read_text(encoding="utf-8")
    expected = {
        "Expected Cycle Contract ABI": ("2", "implemented predecessor"),
        "R4 Review Manifest ABI": (
            "1",
            "strict decoder and authenticated loader implemented; checked-in reviewed data, publication and admission pending",
        ),
        "Proposal Supervision ABI": (
            "1",
            "strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending",
        ),
        "Realization Supervision ABI": (
            "1",
            "strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending",
        ),
        "Mutation Contract ABI": (
            "1",
            "strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending",
        ),
        "Purpose Contract ABI": (
            "1",
            "strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending",
        ),
    }
    for name, (version, state) in expected.items():
        rows = [line for line in registry.splitlines() if line.startswith(f"| {name} |")]
        assert len(rows) == 1
        cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
        assert cells[1] == f"**{version}**"
        assert cells[5] == state
        assert "activated" not in cells[5]


__cemm_test_inventory__ = {'tests/test_r4_supervision_contracts.py::test_sr2_selector_binding_union_uses_dense_handles_and_exact_grounding': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-sr2-selector-union-dense-exact-grounding',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4.1-Source-Readiness-SR2',
                                                                                                                    'owner_ref': 'mutation-partition',
                                                                                                                    'source_ast_sha256': 'f61eaaad2f37f61b53458eb5e9411824edecf0e46e0f2e73fb934bbdffef394b'},
 'tests/test_r4_supervision_contracts.py::test_sr2_blueprint_resolves_handle_table_before_program_shape_validation': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:r4-sr2-blueprint-resolves-bounded-handle-table',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R4.1-Source-Readiness-SR2',
                                                                                                                      'owner_ref': 'mutation-partition',
                                                                                                                      'source_ast_sha256': 'a0303c26ff9780c443b579c7ae424304a2873b1fb15af38cee260f1af6335892'},
 'tests/test_r4_supervision_contracts.py::test_sr2_source_assignments_are_complete_and_critical_residuals_are_not_executable': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:r4-sr2-source-assignments-complete-critical-residual-block',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'R4.1-Source-Readiness-SR2',
                                                                                                                                'owner_ref': 'mutation-partition',
                                                                                                                                'source_ast_sha256': '8bfae109d748e158bf38b6f54ebce2c50cc9288eddc46ee7ea1be61f991edc42'},
 'tests/test_r4_supervision_contracts.py::test_sr2_proposal_relation_and_verification_rejection_are_exact_and_distinct': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:r4-sr2-proposal-relation-verification-rejection-distinct',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'R4.1-Source-Readiness-SR2',
                                                                                                                          'owner_ref': 'mutation-partition',
                                                                                                                          'source_ast_sha256': '24e7773b27f90f3f5a18647c9106ce619340da36408f9f77d93fac247ea89a88'},
 'tests/test_r4_supervision_contracts.py::test_supervision_contracts_are_factory_only_frozen_and_canonical[_manifest]': {'activation_phase': 'R4',
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
                                                                                                                                 'source_ast_sha256': '024ad7862b627c1b9f61f0af3ff9dc5326af4f2d285e18d86cc9c5e4ba859011'},
 'tests/test_r4_supervision_contracts.py::test_derivation_blueprints_reject_unsafe_selectors_and_unbounded_lists': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-derivation-blueprints-reject-unsafe-unbounded',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                    'owner_ref': 'mutation-partition',
                                                                                                                    'source_ast_sha256': 'ef3a2a327b625a85e97932f4a2af615e08d7603bcdfa3cd9d7a120e699abcdec'},
 'tests/test_r4_supervision_contracts.py::test_realization_alignment_is_exact_bounded_and_never_input_as_output_gold': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:r4-realization-alignment-exact-bounded-no-input-gold',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                        'owner_ref': 'mutation-partition',
                                                                                                                        'source_ast_sha256': '2ec50935944e98446c51eef528a1ef98ae677444812c05cbee1a552188920f2d'},
 'tests/test_r4_supervision_contracts.py::test_realization_response_subject_is_closed_complete_and_safe_for_r5_boundaries': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:r4-sr3-response-subject-closed-complete-r5-safe',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'R4.1-Source-Readiness-SR3',
                                                                                                                             'owner_ref': 'mutation-partition',
                                                                                                                             'source_ast_sha256': '9203c12f6efbb323b7cb13abd3644dd4f2958d1317032ab888faa5df699c864c'},
 'tests/test_r4_supervision_contracts.py::test_realization_file_decoder_rejects_duplicate_identity_and_fifth_variant': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:r4-sr3-realization-file-identity-four-variant-bound',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R4.1-Source-Readiness-SR3',
                                                                                                                        'owner_ref': 'mutation-partition',
                                                                                                                        'source_ast_sha256': 'd6e2d7201a152732c7290a8e46ca63590834a907bea972c6e7186a83c2e6065c'},
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
                                                                                                                                  'source_ast_sha256': 'de02ae9d238978dd4e0f1440b79deee95f2130f8c87bb748932c56098442dd05'},
 'tests/test_r4_supervision_contracts.py::test_supervision_abi_fields_reject_booleans_at_top_and_nested_boundaries': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:r4-supervision-abi-exact-int-not-bool',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                      'owner_ref': 'mutation-partition',
                                                                                                                      'source_ast_sha256': '06ab98ac26e7c00ea2fbc6c51b25ff70ab49dfea9647e8bcad09a6de47a4ab94'},
 'tests/test_r4_supervision_contracts.py::test_review_provenance_uses_closed_typed_namespaces': {'activation_phase': 'R4',
                                                                                                 'assertion_ref': 'assertion:r4-review-provenance-closed-typed-namespaces',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                 'owner_ref': 'mutation-partition',
                                                                                                 'source_ast_sha256': '757b126a0c26ceea360837d428947bee834bb25eaff2c9cef19a429c0c574247'},
 'tests/test_r4_supervision_contracts.py::test_blueprint_action_abi_enforces_ordered_shapes_and_local_graph_integrity': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-blueprint-action-abi-local-graph-integrity',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                                         'source_ast_sha256': 'd88756d58c47089fbaf51839e91de6deb52323e2bbd659ee2cb897cce2e5b772'},
 'tests/test_r4_supervision_contracts.py::test_parent_factories_reject_forged_nested_supervision_values': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-supervision-parent-rejects-forged-nested-values',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                           'owner_ref': 'mutation-partition',
                                                                                                           'source_ast_sha256': '9ab1d4689989adbe343a10a9193376f918fa109b72ce3d0c32faea8f7f2f0b77'},
 'tests/test_r4_supervision_contracts.py::test_realization_alignment_union_has_independent_authority_and_exact_slot_ownership': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:r4-sr3-alignment-union-authority-slot-ownership',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R4.1-Source-Readiness-SR3',
                                                                                                                                 'owner_ref': 'mutation-partition',
                                                                                                                                 'source_ast_sha256': 'd95bfd6630f5ee8aa82410999508e87f619969304ba6ce70788eda67e482fcf5'},
 'tests/test_r4_supervision_contracts.py::test_realization_signature_is_reconstructed_from_complete_explicit_semantics': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:r4-realization-signature-explicit-reconstructible',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                          'owner_ref': 'mutation-partition',
                                                                                                                          'source_ast_sha256': 'b03e890535cb30537ee365b910a0b74b1f41d3b62a47bebc43da51a2201b2525'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_reads_exactly_five_reviewed_sources_plus_scenario_once': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:r4-review-bundle-read-once-exact-membership',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                                       'owner_ref': 'mutation-partition',
                                                                                                                       'source_ast_sha256': '746ec6715b63ac6b657914f496ca8db132f48499a1e0605616bf21956cb7f1f5'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_missing_source': {'activation_phase': 'R4',
                                                                                       'assertion_ref': 'assertion:r4-review-bundle-rejects-missing-source',
                                                                                       'diagnostic_role': 'owner',
                                                                                       'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                       'owner_ref': 'mutation-partition',
                                                                                       'source_ast_sha256': '9c052aebf0f33885dfab952689d77e311e42070d995aabe574cc273add077097'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_extra_source_membership': {'activation_phase': 'R4',
                                                                                                'assertion_ref': 'assertion:r4-review-bundle-rejects-extra-source',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                'owner_ref': 'mutation-partition',
                                                                                                'source_ast_sha256': '4dab05e49f9dbf6dd2114ebf5a80912a921f1a899d36e4f665ce97e5fb2e2814'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_duplicate_source_membership': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:r4-review-bundle-rejects-duplicate-source',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                    'owner_ref': 'mutation-partition',
                                                                                                    'source_ast_sha256': '5dc4a026e2d56f13eaeb35e2ceba930a4d65ad23f47c180a842a38a7b2e2fed7'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_lexical_path_escape': {'activation_phase': 'R4',
                                                                                            'assertion_ref': 'assertion:r4-review-bundle-rejects-path-escape',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                            'owner_ref': 'mutation-partition',
                                                                                            'source_ast_sha256': 'ef1557050a0af63fc0519e1290c88ace54bc585dc97c6538fcafae43d71c85eb'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_wrong_record_count': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-review-bundle-rejects-record-count',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                           'owner_ref': 'mutation-partition',
                                                                                           'source_ast_sha256': '119fcb605a5b02d441142f75cd282a8f6a30e6473d071b770560ee1057962bcd'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_wrong_source_sha': {'activation_phase': 'R4',
                                                                                         'assertion_ref': 'assertion:r4-review-bundle-rejects-source-sha',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                         'owner_ref': 'mutation-partition',
                                                                                         'source_ast_sha256': 'bc7b2e9da1d0105e06af4bfb2fb167e74bbd0d2efa8dd7f157a8a303313d5fc3'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_wrong_source_bundle_ref': {'activation_phase': 'R4',
                                                                                                'assertion_ref': 'assertion:r4-review-bundle-rejects-bundle-ref',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                'owner_ref': 'mutation-partition',
                                                                                                'source_ast_sha256': '35052e91456d43e9b3f670b93125e9c245c19bccccf84db8ffeef52a1a90eec4'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_symlink_escape_and_hardlink_alias': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-review-bundle-rejects-link-alias',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                          'owner_ref': 'mutation-partition',
                                                                                                          'source_ast_sha256': '0445165457f128eed26a334ef46096b442a635fe6cbee6af0d23b81faa2133b1'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_short_read': {'activation_phase': 'R4',
                                                                                   'assertion_ref': 'assertion:r4-review-bundle-rejects-short-read',
                                                                                   'diagnostic_role': 'owner',
                                                                                   'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                   'owner_ref': 'mutation-partition',
                                                                                   'source_ast_sha256': 'e679cf4c51d7aaf66de7117c65eef6106978d3dacfd7fefd80ee1fa6cb6b4bca'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_growth_after_stat': {'activation_phase': 'R4',
                                                                                          'assertion_ref': 'assertion:r4-review-bundle-rejects-growth-after-stat',
                                                                                          'diagnostic_role': 'owner',
                                                                                          'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                          'owner_ref': 'mutation-partition',
                                                                                          'source_ast_sha256': '71d7b842b2381eda0b809ca06ba37dd03968d82353f01229cbe3d558f7406016'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_hostile_file_replacement': {'activation_phase': 'R4',
                                                                                                 'assertion_ref': 'assertion:r4-review-bundle-rejects-file-replacement',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                 'owner_ref': 'mutation-partition',
                                                                                                 'source_ast_sha256': '7b47a8f2f4cd079e2311c17556344398d6bf031ca08e25edec28d6e6b01ba43d'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_self_referential_commit_identity': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-review-bundle-rejects-self-reference',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                         'source_ast_sha256': '4f7c50e2961954458f2d05f528cce6b053715a464cfebdfb6ccb3401aa04a484'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_unapproved_manifest_state': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:r4-review-bundle-rejects-unapproved-manifest',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                  'source_ast_sha256': 'e57767b0d605de235e87ac48f2444ec86518f2ca27c5cf9f40e297c7163582a2'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_enforces_existing_byte_record_depth_and_ref_bounds': {'activation_phase': 'R4',
                                                                                                                   'assertion_ref': 'assertion:r4-review-bundle-enforces-source-bounds',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                                   'owner_ref': 'mutation-partition',
                                                                                                                   'source_ast_sha256': 'e51e6ed86188c23ee5e3592498285786f2d9c18a9e3084473cd1f6f4606f04ab'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_ancestor_directory_replacement': {'activation_phase': 'R4',
                                                                                                       'assertion_ref': 'assertion:r4-review-bundle-rejects-ancestor-replacement',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                       'owner_ref': 'mutation-partition',
                                                                                                       'source_ast_sha256': '425ad4ae62f6739318e1dfb56f61e9fc9d919884ce90b2fe8f92c6878b6554d0'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_rejects_crlf_jsonl_normalization': {'activation_phase': 'R4',
                                                                                                 'assertion_ref': 'assertion:r4-review-bundle-rejects-jsonl-normalization',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                 'owner_ref': 'mutation-partition',
                                                                                                 'source_ast_sha256': 'fd06350e80e4273c9d438c8fbb9be4972959a2fa26b953eb4969799d8eb4dafa'},
 'tests/test_r4_supervision_contracts.py::test_authenticated_review_bundle_has_no_public_mint_api': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:r4-authenticated-bundle-no-public-mint',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                     'owner_ref': 'mutation-partition',
                                                                                                     'source_ast_sha256': '83c2d8f4e17ad3196176299f7a4ab2361bc58e58cb802dbfc312edf8d3baf6f2'},
 'tests/test_r4_supervision_contracts.py::test_reader_failure_prevents_authenticated_bundle_creation': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:r4-authenticated-bundle-requires-reader',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                        'owner_ref': 'mutation-partition',
                                                                                                        'source_ast_sha256': '89a4ec7af2719fca945fd6437101f1419e54642468b052e9e78ac1bd21401b21'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_retries_eintr_and_partial_reads_without_reopening': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:r4-review-bundle-partial-eintr-same-descriptor',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                                  'source_ast_sha256': '81817db87c80a34a24895e18004072cbcbc58216afd3620d4f4ec21456dc4efd'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_bounds_perpetual_eintr_without_reopening': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-review-bundle-bounded-perpetual-eintr',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                         'source_ast_sha256': 'cf0f7cb273cb13d4ec7f62f0b0a8ecb2f36a90374a7c64b97ca430f4dc6f5d08'},
 'tests/test_r4_supervision_contracts.py::test_review_bundle_validates_each_nonmanifest_source_once': {'activation_phase': 'R4',
                                                                                                       'assertion_ref': 'assertion:r4-review-bundle-single-source-validation',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R4.1-Data-Supervision-Task-3',
                                                                                                       'owner_ref': 'mutation-partition',
                                                                                                       'source_ast_sha256': '859713c8add8377cae91a2fbd8d87d82c15728316b740852958ecc73b848bfff'},
 'tests/test_r4_supervision_contracts.py::test_sr1_r4_source_abi_registry_states_are_exact_and_nonactivating': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:r4-sr1-source-abi-registry-exact-nonactivating',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R4.1-SR1',
                                                                                                                'owner_ref': 'mutation-partition',
                                                                                                                'source_ast_sha256': 'd10f0de42d7bc2e824d92eaf0a1893282410968dfd45900c81f9b46864136086'},
 'tests/test_r4_supervision_contracts.py::test_supervision_schemas_are_strict_draft_2020_12_and_match_decoders': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:r4-supervision-schemas-draft-2020-12-decoder-parity',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R4.1-Data-Supervision-Task-2',
                                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                                  'source_ast_sha256': '03a127599985864349256da0089d8dd6398cba5219d69cf1d776895821558b3a'}}
