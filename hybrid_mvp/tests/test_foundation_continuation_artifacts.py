"""Hard-cut artifacts carry the original generic query continuation."""
from dataclasses import fields

import pytest

from cemm_authoritative_hybrid.dialogue import DialogueObligation, ObligationKind
from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
from cemm_authoritative_hybrid.r3_learning import LearningCoordinator, LearningPlan
from cemm_authoritative_hybrid.r3_response import ResponseBuilder, ResponseMeaning
from cemm_authoritative_hybrid.r3_kernel import R3Artifacts
from cemm_authoritative_hybrid.r3_effects import NoEffectReceipt, NoEffectReason
from cemm_authoritative_hybrid.persistence import RevisionPin
from tests.test_foundation_continuation_binding import _setup, _answer

__cemm_test_inventory__ = {
    "tests/test_foundation_continuation_artifacts.py::test_response_and_artifacts_bind_effect_program_and_input_pin[program-response]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-effect-lineage-program-response",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "c7af8e7399e76b7932009cd6bc23d8bf0cccabfe6adbebbd9c9170e4b679b399"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_and_artifacts_bind_effect_program_and_input_pin[program-artifacts]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-effect-lineage-program-artifacts",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "c7af8e7399e76b7932009cd6bc23d8bf0cccabfe6adbebbd9c9170e4b679b399"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_and_artifacts_bind_effect_program_and_input_pin[input-pin-response]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-effect-lineage-input-pin-response",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "c7af8e7399e76b7932009cd6bc23d8bf0cccabfe6adbebbd9c9170e4b679b399"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_and_artifacts_bind_effect_program_and_input_pin[input-pin-artifacts]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-effect-lineage-input-pin-artifacts",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "c7af8e7399e76b7932009cd6bc23d8bf0cccabfe6adbebbd9c9170e4b679b399"
    },
    "tests/test_foundation_continuation_artifacts.py::test_learning_receipt_cannot_omit_its_plan_and_source": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-learning-receipt-cannot-omit-its-plan-and-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "d9a12f6d54f02ffb0b5e4b3c29b2d4e8f73fdd688beffbe9e1a54ef89dae28a7"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_registry_hard_cut": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-registry-hard-cut",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "a7f8350d6a120e7734f804c93c7ddada0a8f22b535f1eb633a5892dd9ebf5800"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[answer]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-answer",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[expiry]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-expiry",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[kind]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-kind",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[completed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-completed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[created-turn]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-created-turn",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[expired-turn]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-expired-turn",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[pending]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-pending",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[decision]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-decision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[meaning]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-meaning",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[expression]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-expression",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[situation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-situation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_artifact_and_effect_reject_foreign_continuation[effect]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-artifact-and-effect-reject-foreign-continuation-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "4feb62d378c69c7588ad21e789d52ad34d07d2a5b743a1ede56e02af827b520b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_source_obligation_is_required_and_hash_bound": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-source-obligation-is-required-and-hash-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "73e705fb5a86e9de58216b0d1c5430445c2cf8f4f7c0bf5f13b1b9dae143ff19"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[abi_version-2]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-abi-version-2",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[abi_version-3.0]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-abi-version-3-0",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[abi_version-True]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-abi-version-true",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[expected_target_kinds-value3]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-expected-target-kinds-value3",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[provenance_refs-proof-test]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-provenance-refs-proof-test",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[source_obligation_ref-None]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-source-obligation-ref-none",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[source_obligation_ref-]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-source-obligation-ref-",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[source_obligation_ref-value7]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-source-obligation-ref-value7",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[plan_ref-learning_plan-tampered]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-plan-ref-learning-plan-tampered",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_plan_strict_wire_rejects_old_or_malformed[extra-None]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-plan-strict-wire-rejects-old-or-malformed-extra-none",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "364624532223ff22da59962a75d55f630cb18af4262ee8d48d5c25ee8bfe3664"
    },
    "tests/test_foundation_continuation_artifacts.py::test_materialize_returns_exact_persisted_generic_record": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-materialize-returns-exact-persisted-generic-record",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "7c80c8ed05165882aac4e8e26eab104b823c32b7252ab57b712ce49e148a321b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_legacy_receipt_reopen_rejects_without_reset": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-legacy-receipt-reopen-rejects-without-reset",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "8749123533a759349f9f36f67b6dd16ff2d82fb9c6ca4d32ef8140964ade217b"
    },
    "tests/test_foundation_continuation_artifacts.py::test_nonlearning_response_semantic_fields_are_preserved": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-nonlearning-response-semantic-fields-are-preserved",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "ebc4cca66b754476b6f880304bc1c8631ffd71549e158df879664b925dbb90b1"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_nested_plan[abi_version-2]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-nested-plan-abi-version-2",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "3988d914a3e59b30d2862a51284ca424ae1025636854ea4a2030d82ed73e8058"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_nested_plan[source_query_ref-query-foreign]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-nested-plan-source-query-ref-query-foreign",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "3988d914a3e59b30d2862a51284ca424ae1025636854ea4a2030d82ed73e8058"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_nested_plan[source_obligation_ref-obligation-foreign]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-nested-plan-source-obligation-ref-obligation-foreign",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "3988d914a3e59b30d2862a51284ca424ae1025636854ea4a2030d82ed73e8058"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_nested_plan[provenance_refs-value3]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-nested-plan-provenance-refs-value3",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "3988d914a3e59b30d2862a51284ca424ae1025636854ea4a2030d82ed73e8058"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_generic_obligation[abi_version-1.0]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-generic-obligation-abi-version-1-0",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "eb67bcf44da914f9ca9621eb9492c488a8836917525dba161e6a7a49538e8f8e"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_generic_obligation[kind-evidence_request]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-generic-obligation-kind-evidence-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "eb67bcf44da914f9ca9621eb9492c488a8836917525dba161e6a7a49538e8f8e"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_generic_obligation[source_query_ref-query-foreign]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-generic-obligation-source-query-ref-query-foreign",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "eb67bcf44da914f9ca9621eb9492c488a8836917525dba161e6a7a49538e8f8e"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_generic_obligation[session_ref-session-foreign]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-generic-obligation-session-ref-session-foreign",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "eb67bcf44da914f9ca9621eb9492c488a8836917525dba161e6a7a49538e8f8e"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_generic_obligation[completion_receipt_ref-receipt-completed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-generic-obligation-completion-receipt-ref-receipt-completed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "eb67bcf44da914f9ca9621eb9492c488a8836917525dba161e6a7a49538e8f8e"
    },
    "tests/test_foundation_continuation_artifacts.py::test_response_strictly_decodes_generic_obligation[plan_ref-plan-retired]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-artifact-response-strictly-decodes-generic-obligation-plan-ref-plan-retired",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "eb67bcf44da914f9ca9621eb9492c488a8836917525dba161e6a7a49538e8f8e"
    }
}


def _values(value, *excluded):
    return {f.name: getattr(value, f.name) for f in fields(value) if f.name not in excluded}


@pytest.fixture
def continuation(tmp_path):
    runtime, source, pending = _setup(tmp_path)
    try:
        meaning, situation = _answer(runtime, source.evaluation.situation)
        evaluation = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        plan, row = LearningCoordinator(runtime._authority, runtime.stores).materialize(evaluation, meaning, situation)
        yield runtime, source, meaning, situation, evaluation, plan, row
    finally:
        runtime.stores.close()


def _receipt(meaning, situation, evaluation, plan, row):
    pin = situation.revision_pin
    return NoEffectReceipt.create(reason=NoEffectReason.LEARNING_OBLIGATION_ONLY,
        idempotency_key="effect:diagnostic", journal_origin_ref="origin:diagnostic",
        journal_preterminal_ref="planned:diagnostic", decision_ref=evaluation.decision.decision_ref,
        verified_meaning_ref=meaning.verified_meaning_ref, expression_ref=meaning.expression.expression_ref,
        situation_ref=situation.situation_ref, program_ref=meaning.program_ref,
        learning_plan_ref=plan.plan_ref, source_obligation_ref=row.obligation_ref,
        proof_refs=evaluation.decision.proof_refs, blocker_refs=evaluation.decision.blocker_refs,
        input_revision_pin=pin, output_revision_pin=RevisionPin(pin.authority_generation, pin.world_revision,
            pin.session_revision + 1, pin.episode_revision, pin.effect_revision + 1, pin.model_identity))


def _response(meaning, situation, evaluation, plan, row, effect):
    return ResponseBuilder().build(evaluation=evaluation, meaning=meaning, situation=situation,
        learning_plan=plan, obligation=row, effect=effect)


def _artifacts(situation, evaluation, plan, row, effect, response):
    return R3Artifacts.create(situation=situation, evaluation=evaluation, learning_plan=plan,
        obligation=row, effect=effect, response_meaning=response,
        input_revision_pin=situation.revision_pin, output_revision_pin=effect.output_revision_pin)


def test_response_artifact_and_registry_hard_cut(continuation):
    from cemm_authoritative_hybrid.r3_effects import EFFECT_RECEIPT_ABI_VERSION
    from cemm_authoritative_hybrid.config import ABIRegistry
    assert EFFECT_RECEIPT_ABI_VERSION == 2
    runtime, source, meaning, situation, evaluation, plan, row = continuation
    effect = _receipt(meaning, situation, evaluation, plan, row)
    response = _response(meaning, situation, evaluation, plan, row, effect)
    artifacts = _artifacts(situation, evaluation, plan, row, effect, response)
    assert response.abi_version == ABIRegistry().response_meaning == 3
    assert plan.abi_version == ABIRegistry().learning_plan == 3
    assert artifacts.abi_version == 2
    assert artifacts.obligation is response.obligation is row
    assert row.as_dict()["abi_version"] == 1
    assert ResponseMeaning.from_dict(response.as_dict()) == response
    assert NoEffectReceipt.from_dict(effect.as_dict()) == effect
    for cls, obj, old in ((ResponseMeaning, response, 2), (NoEffectReceipt, effect, 1)):
        for invalid in (old, float(obj.abi_version), True):
            with pytest.raises((TypeError, ValueError)):
                cls.from_dict({**obj.as_dict(), "abi_version": invalid})
    # Diagnostic artifacts alone cannot enable publication or mutate any store.
    from cemm_authoritative_hybrid.r3_effects import R3EffectGateway, AdapterRegistry
    before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
    with pytest.raises(ValueError, match="publication is unavailable"):
        R3EffectGateway(runtime.stores, AdapterRegistry()).execute(evaluation, meaning, situation,
            learning_plan=plan, obligation=row)
    assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before


@pytest.mark.parametrize("field", ("source", "query", "answer", "expiry", "session", "kind", "completed",
    "created-turn", "expired-turn", "pending", "decision", "meaning", "expression", "situation", "effect"),
    ids=("source", "query", "answer", "expiry", "session", "kind", "completed", "created-turn", "expired-turn",
        "pending", "decision", "meaning", "expression", "situation", "effect"))
def test_response_artifact_and_effect_reject_foreign_continuation(continuation, field):
    from cemm_authoritative_hybrid.r3_effects import EFFECT_RECEIPT_ABI_VERSION, R3EffectGateway, AdapterRegistry
    assert EFFECT_RECEIPT_ABI_VERSION == 2
    runtime, source, meaning, situation, evaluation, plan, row = continuation
    effect = _receipt(meaning, situation, evaluation, plan, row)
    response = _response(meaning, situation, evaluation, plan, row, effect)
    if field in {"source", "query", "answer", "expiry", "decision", "meaning", "expression", "situation"}:
        key, value = {"source": ("source_obligation_ref", "obligation:foreign"),
            "query": ("source_query_ref", "query:foreign"), "answer": ("answer_contract_ref", "contract:foreign"),
            "expiry": ("expires_at_turn", 7), "decision": ("decision_ref", "decision:foreign"),
            "meaning": ("verified_meaning_ref", "meaning:foreign"), "expression": ("expression_ref", "expression:foreign"),
            "situation": ("situation_ref", "situation:foreign")}[field]
        values = _values(plan, "abi_version", "plan_ref")
        values[key] = value
        if field == "source": values["provenance_refs"] = (*plan.provenance_refs, value)
        plan = LearningPlan.create(**values)
    elif field == "pending":
        situation = type(situation).create(**{**_values(situation, "abi_version", "situation_ref"), "obligation_refs": ()})
    elif field == "effect":
        effect = NoEffectReceipt.create(**{**_values(effect, "abi_version", "receipt_ref"), "source_obligation_ref": "obligation:foreign"})
    else:
        key, value = {"session": ("session_ref", "session:foreign"), "kind": ("kind", ObligationKind.CLARIFICATION),
            "completed": ("completion_receipt_ref", "receipt:completed"),
            "created-turn": ("created_turn_index", situation.turn_index),
            "expired-turn": ("expires_turn_index", situation.turn_index)}[field]
        row = DialogueObligation.create(**{**_values(row, "obligation_ref"), key: value})
        # Rebind the plan and receipt to isolate lifecycle/session validation.
        plan = LearningPlan.create(**{**_values(plan, "abi_version", "plan_ref"),
            "source_obligation_ref": row.obligation_ref, "expires_at_turn": row.expires_turn_index,
            "provenance_refs": (*plan.provenance_refs, row.obligation_ref)})
        effect = _receipt(meaning, situation, evaluation, plan, row)
    with pytest.raises((ValueError, TypeError)):
        _response(meaning, situation, evaluation, plan, row, effect)
    with pytest.raises((ValueError, TypeError)):
        _artifacts(situation, evaluation, plan, row, effect, response)
    before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
    with pytest.raises((ValueError, TypeError)) as exc:
        R3EffectGateway(runtime.stores, AdapterRegistry()).execute(evaluation, meaning, situation,
            learning_plan=plan, obligation=row)
    if field != "effect":
        assert "publication is unavailable" not in str(exc.value)
    assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before


def _plan_values():
    return dict(contract_ref="contract:designation-learning", verified_meaning_ref="meaning:test",
        expression_ref="expression:test", situation_ref="situation:test", decision_ref="decision:test",
        source_query_ref="query:test", source_obligation_ref="obligation:source", goal_ref="goal:learn",
        capability_ref="cap:learn", permission_ref="permission:learn", commit_operator_ref="op:designation",
        surface_literal="velnora", target_ref="rel:likes", expected_target_kinds=("relation_type",),
        answer_contract_ref="contract:designation_answer:v2", provenance_refs=("proof:test", "obligation:source"),
        revision_pin=RevisionPin("authority:test", 0, 0, 0, 0, "model:test"), expires_at_turn=6)


def test_plan_source_obligation_is_required_and_hash_bound():
    import cemm_authoritative_hybrid.r3_learning as owner
    assert owner.LEARNING_PLAN_ABI_VERSION == 3
    assert "DialogueObligation" not in owner.__all__
    assert not hasattr(owner, "DIALOGUE_OBLIGATION_ABI_VERSION")
    values = _plan_values()
    values["provenance_refs"] = (*values["provenance_refs"], "obligation:other")
    plan = LearningPlan.create(**values)
    assert LearningPlan.from_dict(plan.as_dict()) == plan
    other = LearningPlan.create(**{**values, "source_obligation_ref": "obligation:other"})
    assert other.plan_ref != plan.plan_ref
    with pytest.raises((ValueError, TypeError)):
        LearningPlan.from_dict({**plan.as_dict(), "source_obligation_ref": "obligation:other"})
    del values["source_obligation_ref"]
    with pytest.raises(TypeError):
        LearningPlan.create(**values)


@pytest.mark.parametrize("field,value", [("abi_version", 2), ("abi_version", 3.0), ("abi_version", True),
    ("expected_target_kinds", ("relation_type",)), ("provenance_refs", "proof:test"),
    ("source_obligation_ref", None), ("source_obligation_ref", ""), ("source_obligation_ref", []),
    ("plan_ref", "learning_plan:tampered"), ("extra", None)],
    ids=("abi_version-2", "abi_version-3.0", "abi_version-True", "expected_target_kinds-value3",
        "provenance_refs-proof-test", "source_obligation_ref-None", "source_obligation_ref-",
        "source_obligation_ref-value7", "plan_ref-learning_plan-tampered", "extra-None"))
def test_plan_strict_wire_rejects_old_or_malformed(field, value):
    assert __import__(LearningPlan.__module__, fromlist=["LEARNING_PLAN_ABI_VERSION"]).LEARNING_PLAN_ABI_VERSION == 3
    plan = LearningPlan.create(**_plan_values())
    with pytest.raises((ValueError, TypeError)):
        LearningPlan.from_dict({**plan.as_dict(), field: value})


def test_materialize_returns_exact_persisted_generic_record(tmp_path):
    runtime, source, pending = _setup(tmp_path)
    try:
        meaning, situation = _answer(runtime, source.evaluation.situation)
        evaluation = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        plan, obligation = LearningCoordinator(runtime._authority, runtime.stores).materialize(evaluation, meaning, situation)
        assert type(obligation) is DialogueObligation
        assert obligation == pending
        assert plan.source_obligation_ref == pending.obligation_ref
        assert pending.obligation_ref in plan.provenance_refs
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
        assert runtime.stores.obligations.get(pending.obligation_ref) == {**obligation.as_dict(), "resolved": False}
    finally:
        runtime.stores.close()


def test_legacy_receipt_reopen_rejects_without_reset(tmp_path, linked_authority):
    """Author ABI1 independently; a valid hash must not stand in for ABI support."""
    import json
    import sqlite3
    from cemm_authoritative_hybrid.canonical import stable_ref
    from cemm_authoritative_hybrid.persistence import StoreActivationError, _payload_hash, open_stores
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry, EffectJournalState
    from tests.test_foundation_effect_currentness import _seed_lamp_off
    path = tmp_path / "legacy-receipt.db"
    stores = open_stores(path, authority_generation=linked_authority.generation)
    _seed_lamp_off(stores)
    pin = stores.revision_pin().as_dict()
    old = dict(abi_version=1, reason="read_only", idempotency_key="key:legacy",
        journal_origin_ref="origin:legacy", journal_preterminal_ref="planned:legacy",
        decision_ref="decision:legacy", verified_meaning_ref="meaning:legacy", expression_ref="expression:legacy",
        situation_ref="situation:legacy", program_ref="program:legacy", learning_plan_ref=None, obligation_ref=None,
        proof_refs=[], blocker_refs=[], input_revision_pin=pin,
        output_revision_pin={**pin, "session_revision": 1, "effect_revision": 2})
    old["receipt_ref"] = stable_ref("no_effect_receipt", old)
    entry = EffectJournalEntry.create(idempotency_key="key:legacy", state=EffectJournalState.NO_EFFECT,
        attempt_index=0, intent_ref="origin:legacy", decision_ref="decision:legacy",
        request_payload={"kind": "no_effect", "session_ref": "session:legacy", "turn_index": 1},
        observation_payload=None, outcome_ref=old["receipt_ref"], blocker_refs=(),
        parent_journal_ref="planned:legacy", effect_revision=2).as_dict()
    stores.close()
    with sqlite3.connect(path / "semantic.db") as conn:
        conn.execute("INSERT INTO r3_effect_journal VALUES (?, ?, ?, ?, ?, ?)",
            ("key:legacy", json.dumps(entry), _payload_hash(entry), json.dumps(old), _payload_hash(old), 2))
        before = {table: conn.execute(f"SELECT * FROM {table}").fetchall()
            for table in ("metadata", "world_facts", "r3_effect_journal")}
    with pytest.raises(StoreActivationError):
        reopened = open_stores(path, authority_generation=linked_authority.generation)
        reopened.close()
    with sqlite3.connect(path / "semantic.db") as conn:
        assert {table: conn.execute(f"SELECT * FROM {table}").fetchall() for table in before} == before
    assert before["world_facts"]


def test_nonlearning_response_semantic_fields_are_preserved(tmp_path):
    runtime, source, pending = _setup(tmp_path)
    try:
        response = source.response_meaning
        assert response.abi_version == 3
        assert response.learning_plan is response.obligation is None
        assert response.learning_plan_ref is response.obligation_ref is None
        assert response.response_expression == source.evaluation.expression
        assert response.source_expression_ref == source.evaluation.expression.expression_ref
        assert response.decision_ref == source.evaluation.decision.decision_ref
        assert response.bindings == source.evaluation.decision.bindings == ()
        assert response.proof_refs == source.evaluation.decision.proof_refs
        assert response.blocker_refs == source.evaluation.decision.blocker_refs
        assert response.policy_refs == source.evaluation.decision.policy_refs
        assert response.discourse_action == "unknown"
        assert response.epistemic_status_ref == "epistemic_status:unknown"
        assert response.polarity_ref == "polarity:positive"
        assert response.modality_ref == "modality:actual"
        assert ResponseMeaning.from_dict(response.as_dict()) == response
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field,value", [("abi_version", 2), ("source_query_ref", "query:foreign"),
    ("source_obligation_ref", "obligation:foreign"), ("provenance_refs", ())],
    ids=("abi_version-2", "source_query_ref-query-foreign", "source_obligation_ref-obligation-foreign", "provenance_refs-value3"))
def test_response_strictly_decodes_nested_plan(continuation, field, value):
    _, _, meaning, situation, evaluation, plan, row = continuation
    response = _response(meaning, situation, evaluation, plan, row, _receipt(meaning, situation, evaluation, plan, row))
    wire = response.as_dict()
    wire["learning_plan"][field] = value
    with pytest.raises((ValueError, TypeError)):
        ResponseMeaning.from_dict(wire)


@pytest.mark.parametrize("field,value", [("abi_version", 1.0), ("kind", "evidence_request"),
    ("source_query_ref", "query:foreign"), ("session_ref", "session:foreign"),
    ("completion_receipt_ref", "receipt:completed"), ("plan_ref", "plan:retired")],
    ids=("abi_version-1.0", "kind-evidence_request", "source_query_ref-query-foreign", "session_ref-session-foreign",
        "completion_receipt_ref-receipt-completed", "plan_ref-plan-retired"))
def test_response_strictly_decodes_generic_obligation(continuation, field, value):
    _, _, meaning, situation, evaluation, plan, row = continuation
    response = _response(meaning, situation, evaluation, plan, row, _receipt(meaning, situation, evaluation, plan, row))
    wire = response.as_dict()
    wire["obligation"][field] = value
    with pytest.raises((ValueError, TypeError)):
        ResponseMeaning.from_dict(wire)


def test_learning_receipt_cannot_omit_its_plan_and_source(continuation):
    _, _, meaning, situation, evaluation, plan, row = continuation
    effect = _receipt(meaning, situation, evaluation, plan, row)
    response = _response(meaning, situation, evaluation, plan, row, effect)
    without = ResponseMeaning.create(**{**_values(response, "abi_version", "response_meaning_ref"),
        "learning_plan": None, "obligation": None, "learning_plan_ref": None, "obligation_ref": None})
    with pytest.raises(ValueError, match="learning"):
        _response(meaning, situation, evaluation, None, None, effect)
    with pytest.raises(ValueError, match="learning"):
        _artifacts(situation, evaluation, None, None, effect, without)


@pytest.mark.parametrize("field,boundary", (("program", "response"), ("program", "artifacts"),
    ("input-pin", "response"), ("input-pin", "artifacts")),
    ids=("program-response", "program-artifacts", "input-pin-response", "input-pin-artifacts"))
def test_response_and_artifacts_bind_effect_program_and_input_pin(continuation, field, boundary):
    _, _, meaning, situation, evaluation, plan, row = continuation
    effect = _receipt(meaning, situation, evaluation, plan, row)
    response = _response(meaning, situation, evaluation, plan, row, effect)
    valid = _artifacts(situation, evaluation, plan, row, effect, response)
    assert valid.effect.program_ref == meaning.program_ref == evaluation.decision.program_ref
    assert valid.effect.input_revision_pin == situation.revision_pin == evaluation.revision_pin
    assert valid.output_revision_pin.effect_revision > valid.input_revision_pin.effect_revision
    assert valid.output_revision_pin.session_revision > valid.input_revision_pin.session_revision
    assert response.revision_pin == valid.output_revision_pin
    changes = {"program_ref": "program:foreign"}
    if field == "input-pin":
        pin = effect.input_revision_pin
        changes = {"input_revision_pin": RevisionPin(pin.authority_generation, pin.world_revision,
            pin.session_revision, pin.episode_revision + 1, pin.effect_revision, pin.model_identity)}
    foreign = NoEffectReceipt.create(**{**_values(effect, "abi_version", "receipt_ref"), **changes})
    assert foreign.receipt_ref != effect.receipt_ref
    assert NoEffectReceipt.from_dict(foreign.as_dict()) == foreign
    # Rebind the response's effect ref to isolate artifact lineage validation.
    rebound = ResponseMeaning.create(**{**_values(response, "abi_version", "response_meaning_ref"),
        "effect_outcome_ref": foreign.receipt_ref})
    with pytest.raises(ValueError, match="lineage"):
        if boundary == "response":
            _response(meaning, situation, evaluation, plan, row, foreign)
        else:
            _artifacts(situation, evaluation, plan, row, foreign, rebound)
