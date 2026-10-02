"""Performed communication selects a reciprocal, non-claim response."""
from pathlib import Path
from dataclasses import fields
import inspect

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.communicative import CommunicativeSource, ResponseSelection, selected_owned_inputs
from cemm_authoritative_hybrid.decision import Decision
from cemm_authoritative_hybrid.situation import SituationContext
from cemm_authoritative_hybrid.r3_response import ResponseMeaning, ResponseBuilder, validate_response_linkage
from cemm_authoritative_hybrid.proposal_context import ProposalContext, ResidualEvidence
from cemm_authoritative_hybrid.persistence import open_stores, StoreActivationError, StaleRevisionError
from cemm_authoritative_hybrid.cycle import Orientation, SemanticMode
from cemm_authoritative_hybrid.expressions import (
    GroundedReference, RoleBinding, SemanticApplication, SemanticExpression,
)

ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_communicative_response.py::test_public_performed_act_selects_reciprocal_nonclaim[greeting]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-public-performed-act-selects-reciprocal-nonclaim-greeting",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "5c8b29869d455001c705eb1923b86aaf71657d3e47a1a7ecc787639981cc737e"
    },
    "tests/test_foundation_communicative_response.py::test_public_performed_act_selects_reciprocal_nonclaim[farewell]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-public-performed-act-selects-reciprocal-nonclaim-farewell",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "5c8b29869d455001c705eb1923b86aaf71657d3e47a1a7ecc787639981cc737e"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[other-recipient]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-other-recipient",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[explicit-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-explicit-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[explicit-deictic-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-explicit-deictic-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[quotation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-quotation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[report]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-report",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[polarity]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-polarity",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[modality]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-modality",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_only_direct_speaker_act_can_select_reply[compound]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-only-direct-speaker-act-can-select-reply-compound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bf47f087d1a8e3ea4f4e424c2ce97f19c9b88d52481463cb98e31b6aef883eb0"
    },
    "tests/test_foundation_communicative_response.py::test_actual_form_primitive_cannot_vanish_or_change_owner[reference-missing]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-form-primitive-cannot-vanish-or-change-owner-reference-missing",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1792d1e510bb8169c9b40a7b573cbf8b465a657e9bb3bb2be1b6ea142c6902c5"
    },
    "tests/test_foundation_communicative_response.py::test_actual_form_primitive_cannot_vanish_or_change_owner[reference-retyped]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-form-primitive-cannot-vanish-or-change-owner-reference-retyped",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1792d1e510bb8169c9b40a7b573cbf8b465a657e9bb3bb2be1b6ea142c6902c5"
    },
    "tests/test_foundation_communicative_response.py::test_actual_form_primitive_cannot_vanish_or_change_owner[reference-foreign-retained-good]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-form-primitive-cannot-vanish-or-change-owner-reference-foreign-retained-good",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1792d1e510bb8169c9b40a7b573cbf8b465a657e9bb3bb2be1b6ea142c6902c5"
    },
    "tests/test_foundation_communicative_response.py::test_actual_form_primitive_cannot_vanish_or_change_owner[quotation-missing]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-form-primitive-cannot-vanish-or-change-owner-quotation-missing",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1792d1e510bb8169c9b40a7b573cbf8b465a657e9bb3bb2be1b6ea142c6902c5"
    },
    "tests/test_foundation_communicative_response.py::test_actual_form_primitive_cannot_vanish_or_change_owner[quotation-retyped]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-form-primitive-cannot-vanish-or-change-owner-quotation-retyped",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1792d1e510bb8169c9b40a7b573cbf8b465a657e9bb3bb2be1b6ea142c6902c5"
    },
    "tests/test_foundation_communicative_response.py::test_actual_form_primitive_cannot_vanish_or_change_owner[quotation-foreign-retained-good]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-form-primitive-cannot-vanish-or-change-owner-quotation-foreign-retained-good",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1792d1e510bb8169c9b40a7b573cbf8b465a657e9bb3bb2be1b6ea142c6902c5"
    },
    "tests/test_foundation_communicative_response.py::test_actual_selected_owner_rejects_source_removal_before_mode_dispatch[source-only]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-selected-owner-rejects-source-removal-before-mode-dispatch-source-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "537ce75e033ce7ec9ad02371a782f9a8b59a62e809215d60945e8ff6949cd0b0"
    },
    "tests/test_foundation_communicative_response.py::test_actual_selected_owner_rejects_source_removal_before_mode_dispatch[source-and-owners]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-selected-owner-rejects-source-removal-before-mode-dispatch-source-and-owners",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "537ce75e033ce7ec9ad02371a782f9a8b59a62e809215d60945e8ff6949cd0b0"
    },
    "tests/test_foundation_communicative_response.py::test_codecs_roundtrip_without_live_authority_and_reject_old_wire[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-codecs-roundtrip-without-live-authority-and-reject-old-wire-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "2239bc6c2aa0c2f485407528392a662ab8768b4707033792b19e1af8711dfbc1"
    },
    "tests/test_foundation_communicative_response.py::test_codecs_roundtrip_without_live_authority_and_reject_old_wire[selection]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-codecs-roundtrip-without-live-authority-and-reject-old-wire-selection",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "2239bc6c2aa0c2f485407528392a662ab8768b4707033792b19e1af8711dfbc1"
    },
    "tests/test_foundation_communicative_response.py::test_codecs_roundtrip_without_live_authority_and_reject_old_wire[situation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-codecs-roundtrip-without-live-authority-and-reject-old-wire-situation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "2239bc6c2aa0c2f485407528392a662ab8768b4707033792b19e1af8711dfbc1"
    },
    "tests/test_foundation_communicative_response.py::test_codecs_roundtrip_without_live_authority_and_reject_old_wire[decision]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-codecs-roundtrip-without-live-authority-and-reject-old-wire-decision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "2239bc6c2aa0c2f485407528392a662ab8768b4707033792b19e1af8711dfbc1"
    },
    "tests/test_foundation_communicative_response.py::test_codecs_roundtrip_without_live_authority_and_reject_old_wire[response]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-codecs-roundtrip-without-live-authority-and-reject-old-wire-response",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "2239bc6c2aa0c2f485407528392a662ab8768b4707033792b19e1af8711dfbc1"
    },
    "tests/test_foundation_communicative_response.py::test_october_one_store_rejected_without_mutation_and_fresh_restart": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-october-one-store-rejected-without-mutation-and-fresh-restart",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "81fc2892a0a7fe02bc5cd3f5c796ad2ace8cdbe67f75c72ff5a797fafe4eace7"
    },
    "tests/test_foundation_communicative_response.py::test_new_wire_rejects_nested_container_alias_before_decode[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-new-wire-rejects-nested-container-alias-before-decode-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "0f1c0db1e2525e3e82afea358ecb1e84af551e1c89536352f89efa2a1b913b99"
    },
    "tests/test_foundation_communicative_response.py::test_new_wire_rejects_nested_container_alias_before_decode[selection]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-new-wire-rejects-nested-container-alias-before-decode-selection",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "0f1c0db1e2525e3e82afea358ecb1e84af551e1c89536352f89efa2a1b913b99"
    },
    "tests/test_foundation_communicative_response.py::test_terminal_request_payload_swap_is_not_journal_authority": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-terminal-request-payload-swap-is-not-journal-authority",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "df12bec707abd6570b73653f0ad07859e50f03c75d48db2f45c8dc8081a48faf"
    },
    "tests/test_foundation_communicative_response.py::test_exact_terminal_retry_retains_original_receipt_after_later_activity": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-exact-terminal-retry-retains-original-receipt-after-later-activity",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "dc4efe7b78864f1164710c7decce6914c0e0d684e4fbc1680bbb12ae66dfe7df"
    },
    "tests/test_foundation_communicative_response.py::test_initial_evaluation_requires_original_situation_inputs[phase]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-initial-evaluation-requires-original-situation-inputs-phase",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "55a43ef428ac21896ccbc89679c497105ebce361afc1892ca1a13bfac62f6313"
    },
    "tests/test_foundation_communicative_response.py::test_initial_evaluation_requires_original_situation_inputs[turn-index]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-initial-evaluation-requires-original-situation-inputs-turn-index",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "55a43ef428ac21896ccbc89679c497105ebce361afc1892ca1a13bfac62f6313"
    },
    "tests/test_foundation_communicative_response.py::test_initial_evaluation_requires_original_situation_inputs[missing-bundle]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-initial-evaluation-requires-original-situation-inputs-missing-bundle",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "55a43ef428ac21896ccbc89679c497105ebce361afc1892ca1a13bfac62f6313"
    },
    "tests/test_foundation_communicative_response.py::test_initial_stale_communicative_request_cannot_reserve_journal": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-initial-stale-communicative-request-cannot-reserve-journal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "9026fe7c130464bf6f6ce09c1a6e200cb09464c0f45678b5a238f52f29d324e4"
    },
    "tests/test_foundation_communicative_response.py::test_live_sinks_require_actual_authenticated_source_inputs[evaluate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-sinks-require-actual-authenticated-source-inputs-evaluate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "62bb9bf747ebd2b19a856eff0acc95ac6f6e10da1328f8597cfc86a4b21784a4"
    },
    "tests/test_foundation_communicative_response.py::test_live_sinks_require_actual_authenticated_source_inputs[finalize]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-sinks-require-actual-authenticated-source-inputs-finalize",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "62bb9bf747ebd2b19a856eff0acc95ac6f6e10da1328f8597cfc86a4b21784a4"
    },
    "tests/test_foundation_communicative_response.py::test_live_sinks_require_actual_authenticated_source_inputs[builder]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-sinks-require-actual-authenticated-source-inputs-builder",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "62bb9bf747ebd2b19a856eff0acc95ac6f6e10da1328f8597cfc86a4b21784a4"
    },
    "tests/test_foundation_communicative_response.py::test_live_sinks_require_actual_authenticated_source_inputs[linkage]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-sinks-require-actual-authenticated-source-inputs-linkage",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "62bb9bf747ebd2b19a856eff0acc95ac6f6e10da1328f8597cfc86a4b21784a4"
    },
    "tests/test_foundation_communicative_response.py::test_live_sinks_require_actual_authenticated_source_inputs[artifacts]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-sinks-require-actual-authenticated-source-inputs-artifacts",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "62bb9bf747ebd2b19a856eff0acc95ac6f6e10da1328f8597cfc86a4b21784a4"
    },
    "tests/test_foundation_communicative_response.py::test_live_sinks_require_actual_authenticated_source_inputs[cycle]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-sinks-require-actual-authenticated-source-inputs-cycle",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "62bb9bf747ebd2b19a856eff0acc95ac6f6e10da1328f8597cfc86a4b21784a4"
    },
    "tests/test_foundation_communicative_response.py::test_live_sinks_require_actual_authenticated_source_inputs[presenter]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-sinks-require-actual-authenticated-source-inputs-presenter",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "62bb9bf747ebd2b19a856eff0acc95ac6f6e10da1328f8597cfc86a4b21784a4"
    },
    "tests/test_foundation_communicative_response.py::test_rehashed_situation_cannot_borrow_original_source[session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-rehashed-situation-cannot-borrow-original-source-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "3e2f178db9455f02d22fe67a517610a3c75d6ccc24bea5cef01b373f105e79a8"
    },
    "tests/test_foundation_communicative_response.py::test_rehashed_situation_cannot_borrow_original_source[turn]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-rehashed-situation-cannot-borrow-original-source-turn",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "3e2f178db9455f02d22fe67a517610a3c75d6ccc24bea5cef01b373f105e79a8"
    },
    "tests/test_foundation_communicative_response.py::test_rehashed_situation_cannot_borrow_original_source[mode]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-rehashed-situation-cannot-borrow-original-source-mode",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "3e2f178db9455f02d22fe67a517610a3c75d6ccc24bea5cef01b373f105e79a8"
    },
    "tests/test_foundation_communicative_response.py::test_rehashed_situation_cannot_borrow_original_source[time]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-rehashed-situation-cannot-borrow-original-source-time",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "3e2f178db9455f02d22fe67a517610a3c75d6ccc24bea5cef01b373f105e79a8"
    },
    "tests/test_foundation_communicative_response.py::test_rehashed_situation_cannot_borrow_original_source[permissions]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-rehashed-situation-cannot-borrow-original-source-permissions",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "3e2f178db9455f02d22fe67a517610a3c75d6ccc24bea5cef01b373f105e79a8"
    },
    "tests/test_foundation_communicative_response.py::test_rehashed_situation_cannot_borrow_original_source[source-refs]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-rehashed-situation-cannot-borrow-original-source-source-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "3e2f178db9455f02d22fe67a517610a3c75d6ccc24bea5cef01b373f105e79a8"
    },
    "tests/test_foundation_communicative_response.py::test_rehashed_compilation_translation_cannot_authorize_source": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-rehashed-compilation-translation-cannot-authorize-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "570848376474c9d2de919ab722a58870fd0bf75b5b48cae0843f5a55033e8c41"
    },
    "tests/test_foundation_communicative_response.py::test_performed_response_rejects_rehashed_unrelated_mode_artifact": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-performed-response-rejects-rehashed-unrelated-mode-artifact",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "d5fdd62b8430a69b677ea84c568963701879425f799f4bffce6406fd7e84cb36"
    },
    "tests/test_foundation_communicative_response.py::test_actual_orientation_without_response_capability_is_nonclaim[without-respond]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-orientation-without-response-capability-is-nonclaim-without-respond",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "41d540a4d96fc4902dc3842b6f91e324918a36eb541a549e7087a4e58ab2f162"
    },
    "tests/test_foundation_communicative_response.py::test_actual_orientation_without_response_capability_is_nonclaim[learn-only]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-actual-orientation-without-response-capability-is-nonclaim-learn-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "41d540a4d96fc4902dc3842b6f91e324918a36eb541a549e7087a4e58ab2f162"
    },
    "tests/test_foundation_communicative_response.py::test_post_activation_response_does_not_enumerate_atoms": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-post-activation-response-does-not-enumerate-atoms",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "52442e02eea3f243792702bbc16c9a7c9cce7e03b5f045ba299e8099564f95d1"
    },
    "tests/test_foundation_communicative_response.py::test_authenticated_unseen_alias_restart_uses_semantic_policy_without_pack_write": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-authenticated-unseen-alias-restart-uses-semantic-policy-without-pack-write",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "bbf057c29cbd71c6470403baab3b82a5289fe9ec25356e79ec4a83609a6f9c2a"
    },
    "tests/test_foundation_communicative_response.py::test_controlled_target_cannot_bypass_missing_activated_owner[kernel]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-controlled-target-cannot-bypass-missing-activated-owner-kernel",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "6f4995a0ecc8ff2e3d8337bced4a23a88fdd65d5356d8eb654bcb6df270d9bd1"
    },
    "tests/test_foundation_communicative_response.py::test_controlled_target_cannot_bypass_missing_activated_owner[evaluator]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-controlled-target-cannot-bypass-missing-activated-owner-evaluator",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "6f4995a0ecc8ff2e3d8337bced4a23a88fdd65d5356d8eb654bcb6df270d9bd1"
    },
    "tests/test_foundation_communicative_response.py::test_controlled_target_cannot_bypass_missing_activated_owner[gateway]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-controlled-target-cannot-bypass-missing-activated-owner-gateway",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "6f4995a0ecc8ff2e3d8337bced4a23a88fdd65d5356d8eb654bcb6df270d9bd1"
    },
    "tests/test_foundation_communicative_response.py::test_recomputed_foreign_program_witnesses_cannot_borrow_actual_program[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-recomputed-foreign-program-witnesses-cannot-borrow-actual-program-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "07bf45344b636d5667bc31476caa97d2a8bacf9a1d11fea4908c11272b438dca"
    },
    "tests/test_foundation_communicative_response.py::test_recomputed_foreign_program_witnesses_cannot_borrow_actual_program[evaluate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-recomputed-foreign-program-witnesses-cannot-borrow-actual-program-evaluate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "07bf45344b636d5667bc31476caa97d2a8bacf9a1d11fea4908c11272b438dca"
    },
    "tests/test_foundation_communicative_response.py::test_new_wire_rejects_actual_shared_containers_and_cycles[source-alias]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-new-wire-rejects-actual-shared-containers-and-cycles-source-alias",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "110e1b3b765c608a5e96b62c9326279bafc1c908d67832d12fe3adf70b1d6347"
    },
    "tests/test_foundation_communicative_response.py::test_new_wire_rejects_actual_shared_containers_and_cycles[selection-alias]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-new-wire-rejects-actual-shared-containers-and-cycles-selection-alias",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "110e1b3b765c608a5e96b62c9326279bafc1c908d67832d12fe3adf70b1d6347"
    },
    "tests/test_foundation_communicative_response.py::test_new_wire_rejects_actual_shared_containers_and_cycles[source-cycle]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-new-wire-rejects-actual-shared-containers-and-cycles-source-cycle",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "110e1b3b765c608a5e96b62c9326279bafc1c908d67832d12fe3adf70b1d6347"
    },
    "tests/test_foundation_communicative_response.py::test_new_wire_rejects_actual_shared_containers_and_cycles[selection-cycle]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-new-wire-rejects-actual-shared-containers-and-cycles-selection-cycle",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "110e1b3b765c608a5e96b62c9326279bafc1c908d67832d12fe3adf70b1d6347"
    },
    "tests/test_foundation_communicative_response.py::test_live_consequence_rejects_absent_authority_but_pure_codecs_decode[finalize]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-consequence-rejects-absent-authority-but-pure-codecs-decode-finalize",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "c7c0252200caa2d19a2231ffc0cf573f83353c9ce60cd34385771b4d941c5e09"
    },
    "tests/test_foundation_communicative_response.py::test_live_consequence_rejects_absent_authority_but_pure_codecs_decode[execute]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-consequence-rejects-absent-authority-but-pure-codecs-decode-execute",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "c7c0252200caa2d19a2231ffc0cf573f83353c9ce60cd34385771b4d941c5e09"
    },
    "tests/test_foundation_communicative_response.py::test_live_authority_generation_cannot_borrow_other_source_pin[finalize]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-authority-generation-cannot-borrow-other-source-pin-finalize",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1685a18a85f89bdec045bc579f27531f1308e8c1797e9e47e47540520fc59824"
    },
    "tests/test_foundation_communicative_response.py::test_live_authority_generation_cannot_borrow_other_source_pin[execute]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-live-authority-generation-cannot-borrow-other-source-pin-execute",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "1685a18a85f89bdec045bc579f27531f1308e8c1797e9e47e47540520fc59824"
    },
    "tests/test_foundation_communicative_response.py::test_wire_decodes_each_authenticated_child_once[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-wire-decodes-each-authenticated-child-once-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "b722ecdf6daafbfcfbd4742b100cc76824e81e2465982a1802cd28dd447b6cbc"
    },
    "tests/test_foundation_communicative_response.py::test_wire_decodes_each_authenticated_child_once[selection]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-wire-decodes-each-authenticated-child-once-selection",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "b722ecdf6daafbfcfbd4742b100cc76824e81e2465982a1802cd28dd447b6cbc"
    },
    "tests/test_foundation_communicative_response.py::test_missing_source_cannot_borrow_or_reclassify_selected_witnesses[foreign-evaluate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-missing-source-cannot-borrow-or-reclassify-selected-witnesses-foreign-evaluate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "ed33c26981bc3a46370c7e036f5daf3e6162f96d4b2035ac5f6200e7ae98216c"
    },
    "tests/test_foundation_communicative_response.py::test_missing_source_cannot_borrow_or_reclassify_selected_witnesses[foreign-finalize]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-missing-source-cannot-borrow-or-reclassify-selected-witnesses-foreign-finalize",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "ed33c26981bc3a46370c7e036f5daf3e6162f96d4b2035ac5f6200e7ae98216c"
    },
    "tests/test_foundation_communicative_response.py::test_missing_source_cannot_borrow_or_reclassify_selected_witnesses[foreign-execute]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-missing-source-cannot-borrow-or-reclassify-selected-witnesses-foreign-execute",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "ed33c26981bc3a46370c7e036f5daf3e6162f96d4b2035ac5f6200e7ae98216c"
    },
    "tests/test_foundation_communicative_response.py::test_missing_source_cannot_borrow_or_reclassify_selected_witnesses[marker-omission-evaluate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-missing-source-cannot-borrow-or-reclassify-selected-witnesses-marker-omission-evaluate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "ed33c26981bc3a46370c7e036f5daf3e6162f96d4b2035ac5f6200e7ae98216c"
    },
    "tests/test_foundation_communicative_response.py::test_missing_source_cannot_borrow_or_reclassify_selected_witnesses[marker-omission-finalize]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-missing-source-cannot-borrow-or-reclassify-selected-witnesses-marker-omission-finalize",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "ed33c26981bc3a46370c7e036f5daf3e6162f96d4b2035ac5f6200e7ae98216c"
    },
    "tests/test_foundation_communicative_response.py::test_missing_source_cannot_borrow_or_reclassify_selected_witnesses[marker-omission-execute]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-missing-source-cannot-borrow-or-reclassify-selected-witnesses-marker-omission-execute",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "ed33c26981bc3a46370c7e036f5daf3e6162f96d4b2035ac5f6200e7ae98216c"
    },
    "tests/test_foundation_communicative_response.py::test_gateway_rejects_foreign_reader_store_before_reservation_and_reopens_same_store[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-gateway-rejects-foreign-reader-store-before-reservation-and-reopens-same-store-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "2b7590bb3c38804dcb0b2d73a4cb05ffc62c592cf4043b8e339ad3d3540d57f5"
    },
    "tests/test_foundation_communicative_response.py::test_gateway_rejects_foreign_reader_store_before_reservation_and_reopens_same_store[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:communicative-response-gateway-rejects-foreign-reader-store-before-reservation-and-reopens-same-store-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C4",
        "owner_ref": "communicative-source",
        "source_ast_sha256": "2b7590bb3c38804dcb0b2d73a4cb05ffc62c592cf4043b8e339ad3d3540d57f5"
    }
}


def _event(target, actor, addressee):
    app = SemanticApplication("candidate:independent", "op:event", target, (
        RoleBinding("role:actor", GroundedReference(actor)),
        RoleBinding("role:addressee", GroundedReference(addressee)),
    ))
    return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))


@pytest.mark.parametrize("surface,target", (("hello", "event:greeting"), ("goodbye", "event:farewell")),
    ids=("greeting", "farewell"))
def test_public_performed_act_selects_reciprocal_nonclaim(surface, target, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "communication.db")
    try:
        before = runtime.stores.world.revision
        cycle = runtime.process("session:communication", surface)
        assert cycle.verification.selected_meaning.expression == _event(
            target, "participant:user", "participant:system")
        assert cycle.evaluation.decision.action.value == "respond"
        assert cycle.response_meaning.response_expression == _event(
            target, "participant:system", "participant:user")
        assert not cycle.evaluation.claim_occurrences
        assert not cycle.evaluation.admission_decisions
        assert not cycle.evaluation.query_results
        assert runtime.stores.world.revision == before
        assert cycle.realization_receipt is None
        assert runtime.development_reference(cycle).surface.startswith("Response: ")
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface,performed", (
    ("hello Bob", True), ("Alice hello", False), ("you hello Bob", False),
    ('"hello"', False), ("Alice says hello", False), ("not hello", False),
    ("can hello", False), ("hello and goodbye", False),
), ids=("other-recipient", "explicit-actor", "explicit-deictic-actor", "quotation", "report", "polarity", "modality", "compound"))
def test_only_direct_speaker_act_can_select_reply(surface, performed, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "negative.db")
    try:
        cycle = runtime.process("session:negative", surface)
        assert cycle.response_meaning is None or cycle.response_meaning.response_selection is None
        if performed:
            assert cycle.evaluation.decision.action.value == "no_op"
            assert cycle.evaluation.decision.blocker_refs == ("communicative:other_recipient",)
            assert not cycle.evaluation.claim_occurrences
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def _replace_record(record, **changes):
    values = {f.name: getattr(record, f.name) for f in fields(record)
        if f.name not in {"abi_version", record._ref}}
    return type(record).create(**{**values, **changes})


@pytest.mark.parametrize("surface,mutation", (("hello you", "missing"), ("hello you", "retyped"),
    ("hello you", "fake-ref"), ('"hello"', "missing"), ('"hello"', "retyped"), ('"hello"', "fake-ref")),
    ids=("reference-missing", "reference-retyped", "reference-foreign-retained-good",
        "quotation-missing", "quotation-retyped", "quotation-foreign-retained-good"))
def test_actual_form_primitive_cannot_vanish_or_change_owner(surface, mutation, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "primitive.db")
    try:
        turn = runtime._orient_turn("session:primitive", runtime.create_evidence("session:primitive", surface),
            revision_pin=runtime.stores.revision_pin())
        context = turn.context
        owner = runtime._owners["r3"]._communicative_owner
        original = next(c for c in context.contribution_slots if (
            c.kind == "reference" if surface == "hello you" else
            c.constraints == (("orthography", "quotation_boundary"),))
            and c.contribution_ref.startswith("form_contribution:"))
        slots = tuple(c for c in context.contribution_slots if c is not original)
        if mutation != "missing":
            values = {f.name: getattr(original, f.name) for f in fields(original) if f.name != "slot_ref"}
            values.update(contribution_ref="contribution:forged", kind="qualifier" if mutation == "retyped" else original.kind)
            if mutation == "fake-ref" and surface != "hello you":
                from cemm_authoritative_hybrid.proposal_context import _primitive_form_ref
                values.update(constraints=(("orthography", "whitespace"),),
                    contribution_ref=_primitive_form_ref(original.source_unit_refs[0], "orthography", "whitespace"))
            slots = (*slots, type(original).create(**values))
            if mutation == "fake-ref":
                slots = (*slots, original)
        values = {name: getattr(context, name) for name in inspect.signature(ProposalContext.create).parameters if name != "config"}
        if mutation == "missing" and surface == "hello you":
            values["residual_evidence"] = (*context.residual_evidence, ResidualEvidence.create(
                source_unit_ref=original.source_unit_refs[0], contribution_kind="discourse", critical=False, reason="forged"))
        if mutation == "retyped" and surface != "hello you":
            values["residual_evidence"] = tuple(r for r in context.residual_evidence
                if r.source_unit_ref != original.source_unit_refs[0])
        changed = ProposalContext.create(**{**values, "contribution_slots": slots})
        with pytest.raises(ValueError, match="primitive"):
            owner._authenticate_form_evidence(turn.situation_inputs.evidence, changed, turn.orientation)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("omit_owners", (False, True), ids=("source-only", "source-and-owners"))
def test_actual_selected_owner_rejects_source_removal_before_mode_dispatch(omit_owners, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "removed.db")
    try:
        cycle = runtime.process("session:removed", "hello")
        situation = cycle.evaluation.situation
        values = {name: getattr(situation, name) for name in inspect.signature(SituationContext.create).parameters}
        stripped = SituationContext.create(**{**values, "communicative_source": None})
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        with pytest.raises(ValueError, match="source"):
            runtime._owners["r3"]._evaluator.evaluate(meaning, stripped,
                **({} if omit_owners else dict(orientation=cycle.orientation, program=program, receipt=receipt)))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("owner", ("source", "selection", "situation", "decision", "response"),
    ids=("source", "selection", "situation", "decision", "response"))
def test_codecs_roundtrip_without_live_authority_and_reject_old_wire(owner, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "codec.db")
    try:
        cycle = runtime.process("session:codec", "hello")
        value = {"source": cycle.evaluation.situation.communicative_source,
            "selection": cycle.evaluation.response_selection, "situation": cycle.evaluation.situation,
            "decision": cycle.evaluation.decision, "response": cycle.response_meaning}[owner]
        wire = value.as_dict()
        assert type(value).from_dict(wire) == value
        wire["abi_version"] -= 1
        with pytest.raises(ValueError):
            type(value).from_dict(wire)
    finally:
        runtime.stores.close()


def test_october_one_store_rejected_without_mutation_and_fresh_restart(tmp_path):
    old = tmp_path / "old.db"
    stores = open_stores(old, authority_generation="authority-v1-2026-10-01-communicative-controls")
    stores.close()
    before = (old / "semantic.db").read_bytes()
    with pytest.raises(StoreActivationError, match="authority generation mismatch"):
        load_runtime(ROOT, profile="development", store_path=old)
    assert (old / "semantic.db").read_bytes() == before
    for _ in range(2):
        runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "fresh.db")
        try:
            assert runtime.authority.generation == "authority-v1-2026-10-02-communicative-source"
        finally:
            runtime.stores.close()


@pytest.mark.parametrize("kind", ("source", "selection"), ids=("source", "selection"))
def test_new_wire_rejects_nested_container_alias_before_decode(kind, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "wire.db")
    class DictAlias(dict):
        pass
    try:
        cycle = runtime.process("session:wire", "hello")
        value = (cycle.evaluation.situation.communicative_source if kind == "source"
            else cycle.evaluation.response_selection)
        wire = value.as_dict()
        wire["original_revision_pin"] = DictAlias(wire["original_revision_pin"])
        with pytest.raises(TypeError):
            type(value).from_dict(wire)
    finally:
        runtime.stores.close()


def test_terminal_request_payload_swap_is_not_journal_authority(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.r3_persistence import StoredEffectJournal, effect_journal_get, thaw_json
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "payload.db")
    try:
        cycle = runtime.process("session:payload", "hello")
        stored = effect_journal_get(runtime.stores, cycle.effect_receipt.idempotency_key)
        values = {name: getattr(stored.entry, name) for name in inspect.signature(type(stored.entry).create).parameters}
        payload = thaw_json(stored.entry.request_payload)
        payload["turn_ref"] = "turn:foreign"
        entry = type(stored.entry).create(**{**values, "request_payload": payload})
        forged = StoredEffectJournal(entry, stored.receipt_payload)
        monkeypatch.setattr("cemm_authoritative_hybrid.r3_persistence.effect_journal_get", lambda *args: forged)
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        with pytest.raises(ValueError, match="persisted"):
            runtime._owners["r3"]._communicative_owner.authenticate(situation=cycle.evaluation.situation,
                meaning=meaning, orientation=cycle.orientation, program=program, receipt=receipt,
                selection=cycle.evaluation.response_selection, evaluation=cycle.evaluation, effect=cycle.effect_receipt)
    finally:
        runtime.stores.close()


def test_exact_terminal_retry_retains_original_receipt_after_later_activity(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "retry.db")
    try:
        evidence = runtime.create_evidence("session:retry", "hello")
        original = runtime._orient_turn("session:retry", evidence, revision_pin=runtime.stores.revision_pin())
        cycle = runtime.process_evidence("session:retry", evidence)
        before = cycle.effect_receipt
        runtime.process("session:later", "goodbye")
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        retry = runtime._owners["r3"]._effects.execute(cycle.evaluation, meaning, cycle.evaluation.situation,
            communicative_owner=runtime._owners["r3"]._communicative_owner,
            orientation=cycle.orientation, program=program, receipt=receipt, situation_inputs=original.situation_inputs)
        assert retry == before
        assert retry.output_revision_pin == cycle.final_revision_pin
        assert runtime.development_reference(cycle).surface.startswith("Response: ")
        artifacts = runtime._owners["r3"].run(meaning=meaning, orientation=cycle.orientation,
            context=original.context, situation_inputs=original.situation_inputs, program=program, receipt=receipt)
        assert artifacts.effect == before
        assert artifacts.output_revision_pin == before.output_revision_pin
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation", ("phase", "turn-index", "missing-bundle"), ids=("phase", "turn-index", "missing-bundle"))
def test_initial_evaluation_requires_original_situation_inputs(mutation, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "initial-input.db")
    try:
        evidence = runtime.create_evidence("session:initial-input", "hello")
        oriented = runtime._orient_turn("session:initial-input", evidence, revision_pin=runtime.stores.revision_pin())
        cycle = runtime.process_evidence("session:initial-input", evidence)
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        situation = cycle.evaluation.situation
        values = {name: getattr(situation, name) for name in inspect.signature(SituationContext.create).parameters}
        changes = {"phase": {"session_phase_ref": "session_phase:closed"},
            "turn-index": {"turn_index": situation.turn_index + 1}, "missing-bundle": {}}[mutation]
        forged = SituationContext.create(**{**values, **changes})
        inputs = dict(orientation=cycle.orientation, program=program, receipt=receipt)
        assert runtime._owners["r3"]._evaluator.evaluate(meaning, situation,
            situation_inputs=oriented.situation_inputs, **inputs).decision.action.value == "respond"
        if mutation != "missing-bundle":
            inputs["situation_inputs"] = oriented.situation_inputs
        with pytest.raises((ValueError, TypeError), match="[Ss]ituation"):
            runtime._owners["r3"]._evaluator.evaluate(meaning, forged, **inputs)
    finally:
        runtime.stores.close()


def test_initial_stale_communicative_request_cannot_reserve_journal(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stale.db")
    try:
        evidence = runtime.create_evidence("session:stale", "hello")
        original = runtime._orient_turn("session:stale", evidence, revision_pin=runtime.stores.revision_pin())
        proposal = runtime.proposal_model.propose(original.context)
        verification = runtime._owners["verification"].verify_candidates(proposal, original.context)
        meaning = verification.selected_meaning
        program, receipt = selected_owned_inputs(proposal, verification, meaning)
        runtime.process("session:later", "goodbye")
        before = runtime.stores.revision_pin()
        with pytest.raises(StaleRevisionError, match="effect request revision pin"):
            runtime._owners["r3"].run(meaning=meaning, orientation=original.orientation,
                context=original.context, situation_inputs=original.situation_inputs, program=program, receipt=receipt)
        assert runtime.stores.revision_pin() == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("sink", ("evaluate", "finalize", "builder", "linkage", "artifacts", "cycle", "presenter"),
    ids=("evaluate", "finalize", "builder", "linkage", "artifacts", "cycle", "presenter"))
def test_live_sinks_require_actual_authenticated_source_inputs(sink, tmp_path):
    from cemm_authoritative_hybrid.r3_kernel import R3Artifacts
    from cemm_authoritative_hybrid.r3_cycle import CycleFinalizer
    from cemm_authoritative_hybrid.development_reference import DevelopmentPresentationOwner
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "sink.db")
    try:
        cycle = runtime.process("session:sink", "hello")
        meaning, evaluation = cycle.verification.selected_meaning, cycle.evaluation
        situation, effect = evaluation.situation, cycle.effect_receipt
        values = dict(evaluation=evaluation, meaning=meaning, situation=situation, effect=effect,
            learning_plan=None, obligation=None)
        with pytest.raises((ValueError, TypeError)):
            if sink == "evaluate":
                runtime._owners["r3"]._evaluator.evaluate(meaning, situation)
            elif sink == "finalize":
                from cemm_authoritative_hybrid.r3_artifacts import ModeEvaluation
                mode = ModeEvaluation(contribution=evaluation.decision._contribution(), response_selection=evaluation.response_selection)
                runtime._owners["r3"]._evaluator.finalize(meaning, situation, mode)
            elif sink == "builder":
                ResponseBuilder().build(**values)
            elif sink == "linkage":
                validate_response_linkage(response=cycle.response_meaning, evaluation=evaluation, situation=situation, effect=effect)
            elif sink == "artifacts":
                R3Artifacts.create(**{k: v for k, v in values.items() if k != "meaning"},
                    response_meaning=cycle.response_meaning, input_revision_pin=situation.revision_pin,
                    output_revision_pin=cycle.final_revision_pin)
            elif sink == "cycle":
                CycleFinalizer.finalize(**{name: getattr(cycle, name) for name in (
                    "input_ref", "status", "orientation", "proposal", "verification", "evaluation",
                    "effect_receipt", "response_meaning", "realization_receipt", "gap_receipt",
                    "phase_material", "final_revision_pin")}, capture_trace=False, durations_ns=(0,) * 6)
            else:
                DevelopmentPresentationOwner(runtime.authority, runtime.config,
                    runtime._owners["orientation"]._designation_reader).present(cycle)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field", ("session", "turn", "mode", "time", "permissions", "source-refs"),
    ids=("session", "turn", "mode", "time", "permissions", "source-refs"))
def test_rehashed_situation_cannot_borrow_original_source(field, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "situation.db")
    try:
        cycle = runtime.process("session:situation", "hello")
        situation = cycle.evaluation.situation
        changes = {"session": {"session_ref": "session:foreign"}, "turn": {"turn_ref": "turn:foreign"},
            "mode": {"mode": SemanticMode.QUERY, "epistemic_scope_ref": "epistemic_scope:query"},
            "time": {"temporal_frame_ref": "time:foreign"}, "permissions": {"permission_refs": ()},
            "source-refs": {"source_refs": ("evidence_packet:foreign",)}}[field]
        values = {name: getattr(situation, name) for name in inspect.signature(SituationContext.create).parameters}
        forged = SituationContext.create(**{**values, **changes})
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        with pytest.raises(ValueError, match="situation"):
            runtime._owners["r3"]._evaluator.evaluate(meaning, forged,
                orientation=cycle.orientation, program=program, receipt=receipt)
    finally:
        runtime.stores.close()


def test_rehashed_compilation_translation_cannot_authorize_source(tmp_path):
    from cemm_authoritative_hybrid.expressions import CompilationProof, TranslationRow, VerifiedMeaning
    from cemm_authoritative_hybrid.verifier import CandidateVerificationReceipt
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "proof.db")
    try:
        cycle = runtime.process("session:proof", "hello")
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        original = receipt.compilation_proof
        values = {f.name: getattr(original, f.name) for f in fields(original) if f.name != "proof_ref"}
        changed = CompilationProof.create(**{**values, "action_translations": (
            TranslationRow(original.action_translations[0].source_ref, "validated", ("context:foreign",)),
            *original.action_translations[1:])})
        values = {f.name: getattr(receipt, f.name) for f in fields(receipt) if f.name != "receipt_ref"}
        receipt = CandidateVerificationReceipt.create(**{**values, "compilation_proof": changed})
        values = {f.name: getattr(meaning, f.name) for f in fields(meaning) if f.name != "verified_meaning_ref"}
        meaning = VerifiedMeaning.create(**{**values, "compilation_proof_ref": changed.proof_ref,
            "verification_receipt_ref": receipt.receipt_ref})
        source = _replace_record(cycle.evaluation.situation.communicative_source,
            verified_meaning_ref=meaning.verified_meaning_ref, compilation_proof_ref=changed.proof_ref,
            verification_receipt_ref=receipt.receipt_ref)
        with pytest.raises(ValueError, match="translation"):
            runtime._owners["r3"]._communicative_owner.authenticate_source(source,
                meaning=meaning, orientation=cycle.orientation, program=program, receipt=receipt)
    finally:
        runtime.stores.close()


def test_performed_response_rejects_rehashed_unrelated_mode_artifact(tmp_path):
    from cemm_authoritative_hybrid.r3_artifacts import EvaluationBundle, ModeEvaluation, StateQueryResult, QueryStatus
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "extra-mode.db")
    try:
        evidence = runtime.create_evidence("session:extra-mode", "hello")
        oriented = runtime._orient_turn("session:extra-mode", evidence, revision_pin=runtime.stores.revision_pin())
        cycle = runtime.process_evidence("session:extra-mode", evidence)
        original = cycle.evaluation
        extra = StateQueryResult.create(status=QueryStatus.UNKNOWN, entity_ref="entity:Alice",
            dimension_ref="dimension:foreign", value_refs=(), source_refs=(), proof_refs=(),
            revision_pin=original.revision_pin)
        forged = EvaluationBundle.create(decision=original.decision, expression=original.expression,
            situation=original.situation, revision_pin=original.revision_pin,
            mode_evaluation=ModeEvaluation(contribution=original.decision._contribution(),
                response_selection=original.response_selection, state_query_results=(extra,)))
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        with pytest.raises(ValueError, match="nonclaim"):
            runtime._owners["r3"]._communicative_owner.authenticate(situation=original.situation,
                meaning=meaning, orientation=cycle.orientation, program=program, receipt=receipt,
                situation_inputs=oriented.situation_inputs, selection=forged.response_selection, evaluation=forged)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("capabilities", ("without-respond", "learn-only"), ids=("without-respond", "learn-only"))
def test_actual_orientation_without_response_capability_is_nonclaim(capabilities, tmp_path, monkeypatch):
    original = Orientation.create
    def create(cls, **values):
        summary = tuple(c for c in values["capability_summary"] if c != "cap:respond")
        if capabilities == "learn-only":
            summary = tuple(c for c in summary if c == "cap:learn_alias")
        return original(**{**values, "capability_summary": summary})
    monkeypatch.setattr(Orientation, "create", classmethod(create))
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "capability.db")
    try:
        cycle = runtime.process("session:capability", "hello")
        assert cycle.evaluation.decision.action.value == "no_op"
        assert cycle.evaluation.decision.blocker_refs == ("communicative:capability_missing",)
        assert not cycle.evaluation.claim_occurrences
        assert cycle.response_meaning.response_selection is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_post_activation_response_does_not_enumerate_atoms(tmp_path, monkeypatch):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "bounded.db")
    class NoEnumeration(dict):
        def __iter__(self):
            pytest.fail("response source enumerated authority atoms")
        def values(self):
            pytest.fail("response source enumerated authority atom values")
        def items(self):
            pytest.fail("response source enumerated authority atom items")
    try:
        monkeypatch.setattr(runtime.authority, "atoms", NoEnumeration(runtime.authority.atoms))
        cycle = runtime.process("session:bounded", "hello")
        assert cycle.evaluation.decision.action.value == "respond"
        assert runtime.development_reference(cycle).surface.startswith("Response: ")
    finally:
        runtime.stores.close()


def test_authenticated_unseen_alias_restart_uses_semantic_policy_without_pack_write(tmp_path):
    import secrets
    from cemm_authoritative_hybrid.r3_learning import AliasReviewVerifier
    from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, R3EffectGateway
    from tests.test_foundation_alias_publication import _signed
    from tests.test_foundation_continuation_binding import _setup
    runtime, _, pending = _setup(tmp_path)
    before = (ROOT / "data/languages/en/forms.json").read_bytes()
    try:
        proposal = runtime.process(pending.session_ref, "learn velnora means hello")
        plan, stores = proposal.response_meaning.learning_plan, runtime.stores
        journal = stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key)
        secret, binding = secrets.token_bytes(32), stores.learning_store_binding
        grant = {"proposal_key": proposal.effect_receipt.idempotency_key,
            "proposal_journal_ref": journal["entry"]["journal_ref"],
            "proposal_receipt_ref": proposal.effect_receipt.receipt_ref, "plan_ref": plan.plan_ref,
            "source_obligation_ref": pending.obligation_ref, "source_query_ref": pending.source_query_ref,
            "source_journal_ref": journal["entry"]["request_payload"]["learning_source_journal"]["entry"]["journal_ref"],
            "surface": "velnora", "target_ref": "event:greeting", "language": "en",
            "reviewer_ref": "reviewer:test", "policy_ref": runtime.authority.learning_contract_for_source(
                "op:event", "event:learn_alias").review_policy_ref, "key_ref": "key:test-reviewer",
            "store_binding": binding, "nonce": secrets.token_hex(24), "expires_at_turn": pending.expires_turn_index}
        verifier = AliasReviewVerifier(key=secret, key_ref=grant["key_ref"], reviewer_ref=grant["reviewer_ref"],
            policy_ref=grant["policy_ref"], store_binding=binding)
        receipt = R3EffectGateway(stores, AdapterRegistry(), authority=runtime.authority,
            review_verifier=verifier).publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert len(receipt.committed_fact_refs) == 1
        revision = stores.world.revision
    finally:
        runtime.stores.close()
    reopened = load_runtime(ROOT, profile="development", store_path=tmp_path / "continuation.db")
    try:
        cycle = reopened.process("session:alias-response", "velnora")
        assert cycle.response_meaning.response_expression == _event(
            "event:greeting", "participant:system", "participant:user")
        assert cycle.response_meaning.response_selection.control_ref == "control:communicative:event_greeting"
        assert reopened.stores.world.revision == revision
        assert (ROOT / "data/languages/en/forms.json").read_bytes() == before
        assert reopened.development_reference(cycle).surface.startswith("Response: ")
    finally:
        reopened.stores.close()


@pytest.mark.parametrize("sink", ("kernel", "evaluator", "gateway"), ids=("kernel", "evaluator", "gateway"))
def test_controlled_target_cannot_bypass_missing_activated_owner(sink, tmp_path):
    from cemm_authoritative_hybrid.r3_kernel import R3Kernel
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner, ObserveDecisionOwner
    from cemm_authoritative_hybrid.r3_artifacts import EvaluationBundle
    from cemm_authoritative_hybrid.expression_projection import project_expression
    from cemm_authoritative_hybrid.r3_effects import R3EffectGateway, AdapterRegistry
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "owner-missing.db")
    try:
        evidence = runtime.create_evidence("session:owner-missing", "hello")
        oriented = runtime._orient_turn("session:owner-missing", evidence, revision_pin=runtime.stores.revision_pin())
        proposal = runtime.proposal_model.propose(oriented.context)
        verification = runtime._owners["verification"].verify_candidates(proposal, oriented.context)
        meaning = verification.selected_meaning
        situation = runtime._owners["r3"]._situation_builder.build(oriented.orientation, oriented.context,
            **oriented.situation_inputs.as_kwargs())
        mode = ObserveDecisionOwner(runtime.authority).evaluate_full(meaning.expression,
            project_expression(meaning.expression), situation)
        decision = Decision.create(meaning=meaning, situation=situation, contribution=mode.contribution)
        evaluation = EvaluationBundle.create(decision=decision, expression=meaning.expression,
            situation=situation, mode_evaluation=mode, revision_pin=meaning.revision_pin)
        before = runtime.stores.revision_pin()
        with pytest.raises(ValueError, match="communicative.*owner"):
            if sink == "kernel":
                R3Kernel(authority=runtime.authority, stores=runtime.stores, config=runtime.config).run(
                    meaning=meaning, orientation=oriented.orientation, context=oriented.context,
                    situation_inputs=oriented.situation_inputs)
            elif sink == "evaluator":
                R3EvaluationOwner(runtime.authority, runtime.stores, runtime.config).evaluate(meaning, situation)
            else:
                R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority).execute(
                    evaluation, meaning, situation)
        assert runtime.stores.revision_pin() == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("sink", ("source", "evaluate"), ids=("source", "evaluate"))
def test_recomputed_foreign_program_witnesses_cannot_borrow_actual_program(sink, tmp_path):
    from cemm_authoritative_hybrid.verifier import _proposal_candidate_ref
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "foreign-program.db")
    try:
        evidence = runtime.create_evidence("session:foreign-program", "hello")
        oriented = runtime._orient_turn("session:foreign-program", evidence, revision_pin=runtime.stores.revision_pin())
        cycle = runtime.process_evidence("session:foreign-program", evidence)
        meaning = cycle.verification.selected_meaning
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        def rebuild(record, ref, **changes):
            values = {f.name: getattr(record, f.name) for f in fields(record) if f.name not in {ref, "abi_version"}}
            return type(record).create(**{**values, **changes})
        coverage = rebuild(receipt.coverage_receipt, "coverage_receipt_ref", program_ref="program:foreign")
        proof = rebuild(receipt.compilation_proof, "proof_ref", program_ref="program:foreign")
        receipt = rebuild(receipt, "receipt_ref", program_ref="program:foreign", coverage_receipt=coverage,
            compilation_proof=proof, candidate_ref=_proposal_candidate_ref(candidate_rank=receipt.candidate_rank,
                score_q=receipt.score_q, program_ref="program:foreign", candidate_provenance_refs=receipt.candidate_provenance_refs))
        meaning = rebuild(meaning, "verified_meaning_ref", coverage_receipt_ref=coverage.coverage_receipt_ref,
            compilation_proof_ref=proof.proof_ref, verification_receipt_ref=receipt.receipt_ref)
        source = _replace_record(cycle.evaluation.situation.communicative_source,
            verified_meaning_ref=meaning.verified_meaning_ref, coverage_receipt_ref=coverage.coverage_receipt_ref,
            compilation_proof_ref=proof.proof_ref, verification_receipt_ref=receipt.receipt_ref)
        owner = runtime._owners["r3"]._communicative_owner
        with pytest.raises(ValueError, match="lineage"):
            if sink == "source":
                owner.authenticate_source(source, meaning=meaning, orientation=cycle.orientation,
                    program=program, receipt=receipt)
            else:
                values = {name: getattr(cycle.evaluation.situation, name)
                    for name in inspect.signature(SituationContext.create).parameters}
                situation = SituationContext.create(**{**values, "communicative_source": source})
                runtime._owners["r3"]._evaluator.evaluate(meaning, situation, orientation=cycle.orientation,
                    program=program, receipt=receipt, situation_inputs=oriented.situation_inputs)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation", ("source-alias", "selection-alias", "source-cycle", "selection-cycle"),
    ids=("source-alias", "selection-alias", "source-cycle", "selection-cycle"))
def test_new_wire_rejects_actual_shared_containers_and_cycles(mutation, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "wire-identity.db")
    try:
        cycle = runtime.process("session:wire-identity", "hello")
        value = (cycle.evaluation.situation.communicative_source if mutation.startswith("source")
            else cycle.evaluation.response_selection)
        wire = value.as_dict()
        if mutation == "source-alias":
            wire["original_revision_pin"] = wire["context"]["revision_pin"]
        elif mutation == "selection-alias":
            wire["outgoing_expression"]["binders"] = wire["outgoing_expression"]["scope_operators"]
        else:
            wire["original_revision_pin"] = wire
        with pytest.raises(ValueError):
            type(value).from_dict(wire)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("sink", ("finalize", "execute"), ids=("finalize", "execute"))
def test_live_consequence_rejects_absent_authority_but_pure_codecs_decode(sink, tmp_path):
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner, ObserveDecisionOwner
    from cemm_authoritative_hybrid.r3_artifacts import EvaluationBundle
    from cemm_authoritative_hybrid.expression_projection import project_expression
    from cemm_authoritative_hybrid.r3_effects import R3EffectGateway, AdapterRegistry
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "authority-missing.db")
    try:
        evidence = runtime.create_evidence("session:authority-missing", "hello")
        oriented = runtime._orient_turn("session:authority-missing", evidence, revision_pin=runtime.stores.revision_pin())
        proposal = runtime.proposal_model.propose(oriented.context)
        verification = runtime._owners["verification"].verify_candidates(proposal, oriented.context)
        meaning = verification.selected_meaning
        situation = runtime._owners["r3"]._situation_builder.build(oriented.orientation, oriented.context,
            **oriented.situation_inputs.as_kwargs())
        mode = ObserveDecisionOwner(runtime.authority).evaluate_full(meaning.expression,
            project_expression(meaning.expression), situation)
        decision = Decision.create(meaning=meaning, situation=situation, contribution=mode.contribution)
        evaluation = EvaluationBundle.create(decision=decision, expression=meaning.expression,
            situation=situation, mode_evaluation=mode, revision_pin=meaning.revision_pin)
        assert Decision.from_dict(decision.as_dict()) == decision
        assert EvaluationBundle.from_dict(evaluation.as_dict()) == evaluation
        before = runtime.stores.revision_pin()
        with pytest.raises(ValueError, match="activated authority"):
            if sink == "finalize":
                R3EvaluationOwner.finalize(meaning, situation, mode)
            else:
                R3EffectGateway(runtime.stores, AdapterRegistry()).execute(evaluation, meaning, situation)
        assert runtime.stores.revision_pin() == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("sink", ("finalize", "execute"), ids=("finalize", "execute"))
def test_live_authority_generation_cannot_borrow_other_source_pin(sink, tmp_path):
    from cemm_authoritative_hybrid.authority import AuthorityLinker
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    from cemm_authoritative_hybrid.r3_artifacts import ModeEvaluation
    from cemm_authoritative_hybrid.r3_effects import R3EffectGateway, AdapterRegistry
    from tests.test_foundation_communicative_authority import _bundle, _source
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "authority-generation.db")
    try:
        cycle = runtime.process("session:authority-generation", "What does velnora mean?")
        manifest, _ = _bundle(tmp_path, _source())
        foreign = AuthorityLinker().link(manifest)
        assert foreign.generation != cycle.evaluation.revision_pin.authority_generation
        meaning, evaluation = cycle.verification.selected_meaning, cycle.evaluation
        mode = ModeEvaluation(contribution=evaluation.decision._contribution(), query_results=evaluation.query_results)
        before = runtime.stores.revision_pin()
        with pytest.raises(ValueError, match="authority.*generation"):
            if sink == "finalize":
                R3EvaluationOwner.finalize(meaning, evaluation.situation, mode, authority=foreign)
            else:
                R3EffectGateway(runtime.stores, AdapterRegistry(), authority=foreign).execute(
                    evaluation, meaning, evaluation.situation)
        assert runtime.stores.revision_pin() == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("kind", ("source", "selection"), ids=("source", "selection"))
def test_wire_decodes_each_authenticated_child_once(kind, tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.forms import EvidencePacket
    from cemm_authoritative_hybrid.persistence import RevisionPin
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "decode-once.db")
    try:
        cycle = runtime.process("session:decode-once", "hello")
        value = (cycle.evaluation.situation.communicative_source if kind == "source"
            else cycle.evaluation.response_selection)
        children = (EvidencePacket, ProposalContext) if kind == "source" else (SemanticExpression, RevisionPin)
        counts = {child.__name__: 0 for child in children}
        for child in children:
            decoder = child.from_dict
            def decode(cls, row, *, _child=child, _decoder=decoder):
                counts[_child.__name__] += 1
                return _decoder(row)
            monkeypatch.setattr(child, "from_dict", classmethod(decode))
        assert type(value).from_dict(value.as_dict()) == value
        assert counts == {child.__name__: 1 for child in children}
    finally:
        runtime.stores.close()


def _selected_before_effect(runtime, session, surface):
    evidence = runtime.create_evidence(session, surface)
    oriented = runtime._orient_turn(session, evidence, revision_pin=runtime.stores.revision_pin())
    proposal = runtime.proposal_model.propose(oriented.context)
    verification = runtime._owners["verification"].verify_candidates(proposal, oriented.context)
    meaning = verification.selected_meaning
    program, receipt = selected_owned_inputs(proposal, verification, meaning)
    return oriented, meaning, program, receipt


@pytest.mark.parametrize("mutation,sink", (("foreign", "evaluate"), ("foreign", "finalize"),
    ("foreign", "execute"), ("marker-omission", "evaluate"), ("marker-omission", "finalize"),
    ("marker-omission", "execute")), ids=("foreign-evaluate", "foreign-finalize", "foreign-execute",
    "marker-omission-evaluate", "marker-omission-finalize", "marker-omission-execute"))
def test_missing_source_cannot_borrow_or_reclassify_selected_witnesses(mutation, sink, tmp_path):
    from cemm_authoritative_hybrid.verifier import _proposal_candidate_ref
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner, ObserveDecisionOwner
    from cemm_authoritative_hybrid.r3_artifacts import EvaluationBundle
    from cemm_authoritative_hybrid.expression_projection import project_expression
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "witness-omission.db")
    try:
        oriented, meaning, program, receipt = _selected_before_effect(runtime, "session:omission", "hello")
        situation = runtime._owners["r3"]._situation_builder.build(oriented.orientation, oriented.context,
            **oriented.situation_inputs.as_kwargs())
        assert situation.communicative_source is None
        if mutation == "foreign":
            _, _, _, receipt = _selected_before_effect(runtime, "session:ordinary", "What does velnora mean?")
        else:
            provenance = tuple(p for p in receipt.candidate_provenance_refs
                if not p.startswith("reviewed_communicative_match:"))
            assert provenance != receipt.candidate_provenance_refs
            values = {f.name: getattr(receipt, f.name) for f in fields(receipt)
                if f.name not in {"abi_version", "receipt_ref"}}
            receipt = type(receipt).create(**{**values, "candidate_provenance_refs": provenance,
                "candidate_ref": _proposal_candidate_ref(candidate_rank=receipt.candidate_rank,
                    score_q=receipt.score_q, program_ref=program.program_ref, candidate_provenance_refs=provenance)})
            values = {f.name: getattr(meaning, f.name) for f in fields(meaning) if f.name != "verified_meaning_ref"}
            meaning = type(meaning).create(**{**values, "verification_receipt_ref": receipt.receipt_ref})
        owner = runtime._owners["r3"]._communicative_owner
        inputs = dict(orientation=oriented.orientation, program=program, receipt=receipt,
            situation_inputs=oriented.situation_inputs)
        mode = ObserveDecisionOwner(runtime.authority).evaluate_full(meaning.expression,
            project_expression(meaning.expression), situation)
        decision = Decision.create(meaning=meaning, situation=situation, contribution=mode.contribution)
        evaluation = EvaluationBundle.create(decision=decision, expression=meaning.expression,
            situation=situation, mode_evaluation=mode, revision_pin=meaning.revision_pin)
        before = runtime.stores.revision_pin()
        with pytest.raises(ValueError, match="lineage|retained source"):
            if sink == "evaluate":
                runtime._owners["r3"]._evaluator.evaluate(meaning, situation, **inputs)
            elif sink == "finalize":
                R3EvaluationOwner.finalize(meaning, situation, mode, communicative_owner=owner, **inputs)
            else:
                runtime._owners["r3"]._effects.execute(evaluation, meaning, situation,
                    communicative_owner=owner, **inputs)
        assert runtime.stores.revision_pin() == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_gateway_rejects_foreign_reader_store_before_reservation_and_reopens_same_store(backend, tmp_path):
    from cemm_authoritative_hybrid.communicative import CommunicativeOwner
    from cemm_authoritative_hybrid.r3_designations import AdmittedDesignationReader
    from cemm_authoritative_hybrid.r3_effects import R3EffectGateway, AdapterRegistry
    from cemm_authoritative_hybrid.persistence import memory_stores
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store-a.db")
    stores_b = None
    try:
        oriented, meaning, program, receipt = _selected_before_effect(runtime, "session:foreign-store", "hello")
        owner_a = runtime._owners["r3"]._communicative_owner
        source = owner_a.source(evidence=oriented.situation_inputs.evidence, context=oriented.context,
            meaning=meaning, orientation=oriented.orientation, program=program, receipt=receipt)
        situation = runtime._owners["r3"]._situation_builder.build(oriented.orientation, oriented.context,
            communicative_source=source, **oriented.situation_inputs.as_kwargs())
        inputs = dict(orientation=oriented.orientation, program=program, receipt=receipt,
            situation_inputs=oriented.situation_inputs)
        evaluation = runtime._owners["r3"]._evaluator.evaluate(meaning, situation, **inputs)
        options = dict(authority_generation=runtime.authority.generation,
            model_identity=runtime.stores.revision_pin().model_identity)
        path_b = tmp_path / "store-b.db"
        stores_b = memory_stores(**options) if backend == "memory" else open_stores(path_b, **options)
        before_a, before_b = runtime.stores.revision_pin(), stores_b.revision_pin()
        assert before_a == before_b
        gateway = R3EffectGateway(stores_b, AdapterRegistry(), authority=runtime.authority)
        with pytest.raises(ValueError):
            gateway.execute(evaluation, meaning, situation, communicative_owner=owner_a, **inputs)
        assert runtime.stores.revision_pin() == before_a
        assert stores_b.revision_pin() == before_b
        def owner_for(stores):
            return CommunicativeOwner(runtime.authority, owner_a.resolver, owner_a.index,
                AdmittedDesignationReader(runtime.authority, stores))
        effect = gateway.execute(evaluation, meaning, situation, communicative_owner=owner_for(stores_b), **inputs)
        if backend == "sqlite":
            stores_b.close()
            stores_b = open_stores(path_b, **options)
        retry_gateway = R3EffectGateway(stores_b, AdapterRegistry(), authority=runtime.authority)
        before_retry = stores_b.revision_pin()
        assert retry_gateway.execute(evaluation, meaning, situation,
            communicative_owner=owner_for(stores_b), **inputs) == effect
        assert stores_b.revision_pin() == before_retry
        assert runtime.stores.revision_pin() == before_a
    finally:
        runtime.stores.close()
        if stores_b is not None:
            stores_b.close()
