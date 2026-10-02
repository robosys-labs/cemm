"""Linked alias-learning authority; no publication or reviewer grant is implied."""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cemm_authoritative_hybrid import authority as authority_module
from cemm_authoritative_hybrid.authority import AuthorityLinker, AuthorityLinkError, AuthorityStore, LinkedAuthority
from cemm_authoritative_hybrid.canonical import sha256_governed_text

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_alias_authority.py::test_active_alias_contract_is_typed_frozen_and_exactly_indexed": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-active-alias-contract-is-typed-frozen-and-exactly-indexed", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "0872b25935fc2f6cef15456c881a0b59a943af54cffbf64cda1d1258a8f59ec8"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[unknown_field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-unknown-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[bad_ref_type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-bad-ref-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[empty_ref]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-empty-ref", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[oversize_ref]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-oversize-ref", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_contract]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-contract", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_contract_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-contract-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_goal_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-goal-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_answer_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-answer-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_policy_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-policy-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_event_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-event-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_capability_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-capability-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_permission_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-permission-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_adapter_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-adapter-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_label_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-label-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_goal]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-goal", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_answer]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-answer", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_policy]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-policy", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_capability]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-capability", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_permission]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-permission", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_adapter]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-adapter", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_source_operator]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-source-operator", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_commit_operator]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-commit-operator", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_actor_role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-actor-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_surface_role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-surface-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_target_role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-target-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[bad_effect_owner]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-bad-effect-owner", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[external_adapter]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-external-adapter", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[review_false]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-review-false", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[review_int]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-review-int", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[existing_false]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-existing-false", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[existing_string]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-existing-string", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[empty_kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-empty-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[unknown_kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-unknown-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[kinds_string]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-kinds-string", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[kind_type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-kind-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_source_capability]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-source-capability", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_source_permission]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-source-permission", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_source_adapter]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-source-adapter", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[missing_source_signature]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-missing-source-signature", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_source_signature]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-source-signature", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[extra_source_role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-extra-source-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_source_role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-source-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[optional_actor]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-optional-actor", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[integer_required]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-integer-required", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[proposition_surface]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-proposition-surface", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[integer_proposition]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-integer-proposition", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_actor_kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-actor-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_surface_kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-surface-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[mismatched_target_kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-mismatched-target-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_commit_roles]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-commit-roles", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_source_roles]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-source-roles", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_contract]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-contract", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_source_mapping]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-source-mapping", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[wrong_contract_owner]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-wrong-contract-owner", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_owner_name]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-owner-name", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[owner_name_mismatch]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-owner-name-mismatch", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[collection_object]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-collection-object", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[contract_not_object]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-contract-not-object", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[unreviewed_contract_atom]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-unreviewed-contract-atom", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[truthy_reviewed_contract_atom]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-truthy-reviewed-contract-atom", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[source_caps_type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-source-caps-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[source_roles_object]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-source-roles-object", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[source_role_unknown_field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-source-role-unknown-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_operator_owner]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-operator-owner", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[duplicate_owner_path]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-duplicate-owner-path", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[label_name]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-label-name", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[source_signature_unknown_field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-source-signature-unknown-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_linking_rejects_invalid_authority_atomically[target_kinds_unsorted]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-linking-rejects-invalid-authority-atomically-target-kinds-unsorted", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "386ad0521fcdc938d98786160eb1a4ef5cec8bd5e533b432efe140698547a96b"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_duplicate_json_field_is_rejected": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-duplicate-json-field-is-rejected", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "da204d4f8cad5e2df2b19be39c0afd6a38afb9db2770a2fe9df54e1685c43836"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[extra-state-effect]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-extra-state-effect", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[effect-string]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-effect-string", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[effect-object]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-effect-object", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[effect-bool]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-effect-bool", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[effect-null]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-effect-null", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[phases-string]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-phases-string", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[phases-object]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-phases-object", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[unknown-phase]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-unknown-phase", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[phase-int]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-phase-int", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[phase-bool]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-phase-bool", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[empty-phases]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-empty-phases", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[duplicate-phase]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-duplicate-phase", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[oversize-phases]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-oversize-phases", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_reject_discarded_effects_and_malformed_phases[phases-null]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-reject-discarded-effects-and-malformed-phases-phases-null", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "bb2c6d7bd68b5e89cb72c5b89c24b9cfde013821eb74b61b7f18c32c73af868c"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_preserve_empty_effect_and_established_phase_semantics[established-default]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-preserve-empty-effect-and-established-phase-semantics-established-default", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "16a9ec6d79897c0c4180f3fb9a8c38020353eb7a4d30541cb4f4617535205c32"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_preserve_empty_effect_and_established_phase_semantics[opening]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-preserve-empty-effect-and-established-phase-semantics-opening", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "16a9ec6d79897c0c4180f3fb9a8c38020353eb7a4d30541cb4f4617535205c32"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_preserve_empty_effect_and_established_phase_semantics[active]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-preserve-empty-effect-and-established-phase-semantics-active", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "16a9ec6d79897c0c4180f3fb9a8c38020353eb7a4d30541cb4f4617535205c32"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_preserve_empty_effect_and_established_phase_semantics[suspended]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-preserve-empty-effect-and-established-phase-semantics-suspended", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "16a9ec6d79897c0c4180f3fb9a8c38020353eb7a4d30541cb4f4617535205c32"},
    "tests/test_foundation_alias_authority.py::test_alias_source_constraints_preserve_empty_effect_and_established_phase_semantics[all-established-phases]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-source-constraints-preserve-empty-effect-and-established-phase-semantics-all-established-phases", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "16a9ec6d79897c0c4180f3fb9a8c38020353eb7a4d30541cb4f4617535205c32"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_hash_receives_every_typed_field": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-hash-receives-every-typed-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "fbea9846fa7e635fe20be1bbd4c7b881bc09fc4666f493ebbd1f9cfd5bd91dc7"},
    "tests/test_foundation_alias_authority.py::test_alias_contract_hash_is_canonical_and_covers_every_field": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-contract-hash-is-canonical-and-covers-every-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "79640789d7dcb707ac9e79994e6f072e60079b7b1ba88e74c59861d523644153"},
    "tests/test_foundation_alias_authority.py::test_alias_authority_does_not_add_designations_or_external_adapter_availability": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-alias-authority-does-not-add-designations-or-external-adapter-availability", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "9e39379d6fc2022d1f636a533ea93edb68e465e2913d2b71a8a7e7f132de43d5"},
    "tests/test_foundation_alias_authority.py::test_active_alias_authority_fresh_runtime_reopen_and_prior_generation_rejection": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-active-alias-authority-fresh-runtime-reopen-and-prior-generation-rejection", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "3fb425acbf59a830ec625f3767180670d9c276ce38d64b44aaf1c00127a7947d"},
    "tests/test_foundation_alias_authority.py::test_historical_splitter_rejects_existing_authority_before_any_write": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-alias-historical-splitter-rejects-existing-authority-before-any-write", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "5aa41b6a0eef23f02b7db8be03705d6fa1585cc8c33a27b1a21d0ca1d9dc1d52"},
    "tests/test_foundation_alias_authority.py::test_link_path_returns_current_linked_alias_authority": {"activation_phase": "R1", "assertion_ref": "assertion:authority-linker-link-path-returns-linked-authority", "diagnostic_role": "phase", "introduced_by_task": "Foundation-Task-5", "source_ast_sha256": "cfcc673983dc7ceecf6497647610e9365c90d7e2a9303e3b3a81088e9a46b804", "supersedes_node_id": "tests/test_authority_linker.py::test_link_path_returns_linked_authority"},
    "tests/test_foundation_alias_authority.py::test_all_active_alias_authority_atoms_have_valid_kinds": {"activation_phase": "R1", "assertion_ref": "assertion:authority-linker-all-atoms-have-valid-kinds", "diagnostic_role": "phase", "introduced_by_task": "Foundation-Task-5", "source_ast_sha256": "01a7d3794cde8e71dc321fef9fbbdb33e8ec561bc3b438ee05cfc0b86a5ecc05", "supersedes_node_id": "tests/test_authority_linker.py::test_all_atoms_have_valid_kinds"},
    "tests/test_foundation_alias_authority.py::test_current_alias_authority_link_is_content_addressed_and_fail_closed": {"activation_phase": "R1", "assertion_ref": "assertion:r1-admission-authority-link", "diagnostic_role": "admission_only", "introduced_by_task": "Foundation-Task-5", "source_ast_sha256": "7622ca62ab61ac572694e5c741e3ea47dadb65ec084a9804b285e296aeb7baba", },
}


def _contract():
    return {
        "contract_ref": "contract:designation_learning:v2",
        "goal_ref": "goal:resolve_designation",
        "answer_contract_ref": "contract:designation_answer:v2",
        "review_policy_ref": "policy:learning_directive_requires_review:v2",
        "source_operator_ref": "op:event",
        "source_event_ref": "event:learn_alias",
        "actor_role_ref": "role:actor",
        "surface_role_ref": "role:surface",
        "target_role_ref": "role:target",
        "capability_ref": "cap:learn_alias",
        "permission_ref": "permission:write_alias",
        "commit_operator_ref": "op:designation",
        "designation_label_ref": "label:lexical",
        "allowed_target_kinds": [
            "concept", "entity", "event_type", "participant", "relation_type",
            "state_dimension", "state_value",
        ],
        "internal_effect_owner": "EFFECT",
        "internal_adapter_ref": "adapter:memory",
        "requires_explicit_review": True,
        "existing_targets_only": True,
    }


def _owners():
    owners = {
        name: json.loads((ROOT / "data" / "authority" / f"{name}.json").read_text("utf-8"))
        for name in ("kernel", "conversation", "state_operations")
    }
    owners["alias_learning"] = {
        "owner": "alias_learning",
        "atoms": [
            {"ref": "contract:designation_learning:v2", "kind": "learning_contract", "reviewed": True},
            {"ref": "goal:resolve_designation", "kind": "goal", "reviewed": True},
            {"ref": "contract:designation_answer:v2", "kind": "answer_contract", "reviewed": True},
            {"ref": "policy:learning_directive_requires_review:v2", "kind": "policy", "reviewed": True},
        ],
        "learning_contracts": [_contract()],
        "designations": [],
    }
    return owners


def _manifest(tmp_path, owners):
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest = {"abi_version": 1, "generation": "authority:test-alias", "owners": []}
    for name, owner in owners.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(owner, sort_keys=True, indent=2), encoding="utf-8")
        manifest["owners"].append({
            "name": name, "path": str(path), "sha256": sha256_governed_text(path),
        })
    return manifest


def _source_signature(owners):
    return next(row for row in owners["conversation"]["event_signatures"] if row["event_type"] == "event:learn_alias")


def test_active_alias_contract_is_typed_frozen_and_exactly_indexed():
    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    assert hasattr(linked, "learning_contract_for_source"), "active linked learning authority is missing"
    contract = linked.learning_contract_for_source("op:event", "event:learn_alias")
    assert contract is not None
    assert type(contract) is authority_module.DesignationLearningContract
    assert contract.to_dict() == _contract()
    assert linked.learning_contract(contract.contract_ref) is contract
    assert linked.learning_contract_for_source("op:event", "event:teach") is None
    assert linked.learning_contract_for_source("op:designation", "event:learn_alias") is None
    assert linked.learning_contract("contract:missing") is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        contract.permission_ref = "permission:set_state"
    assert type(contract.allowed_target_kinds) is tuple


@pytest.mark.parametrize("mutation", [
    "unknown_field", "missing_field", "bad_ref_type", "empty_ref", "oversize_ref",
    "missing_contract", "wrong_contract_kind", "wrong_goal_kind", "wrong_answer_kind",
    "wrong_policy_kind", "wrong_event_kind", "wrong_capability_kind", "wrong_permission_kind",
    "wrong_adapter_kind", "wrong_label_kind", "missing_goal", "missing_answer",
    "missing_policy", "missing_capability", "missing_permission", "missing_adapter",
    "wrong_source_operator", "wrong_commit_operator", "wrong_actor_role", "wrong_surface_role",
    "wrong_target_role", "bad_effect_owner", "external_adapter", "review_false", "review_int",
    "existing_false", "existing_string", "empty_kinds", "duplicate_kinds", "unknown_kind",
    "kinds_string", "kind_type", "wrong_source_capability", "wrong_source_permission",
    "wrong_source_adapter", "missing_source_signature", "duplicate_source_signature",
    "extra_source_role", "duplicate_source_role", "optional_actor", "integer_required",
    "proposition_surface", "integer_proposition", "wrong_actor_kinds", "wrong_surface_kinds",
    "mismatched_target_kinds", "wrong_commit_roles", "wrong_source_roles",
    "duplicate_contract", "duplicate_source_mapping", "wrong_contract_owner",
    "duplicate_owner_name", "owner_name_mismatch", "collection_object", "contract_not_object",
    "unreviewed_contract_atom", "truthy_reviewed_contract_atom",
    "source_caps_type", "source_roles_object", "source_role_unknown_field",
    "duplicate_operator_owner", "duplicate_owner_path", "label_name",
    "source_signature_unknown_field", "target_kinds_unsorted",
],
    ids=('unknown_field', 'missing_field', 'bad_ref_type', 'empty_ref', 'oversize_ref', 'missing_contract', 'wrong_contract_kind', 'wrong_goal_kind', 'wrong_answer_kind', 'wrong_policy_kind', 'wrong_event_kind', 'wrong_capability_kind', 'wrong_permission_kind', 'wrong_adapter_kind', 'wrong_label_kind', 'missing_goal', 'missing_answer', 'missing_policy', 'missing_capability', 'missing_permission', 'missing_adapter', 'wrong_source_operator', 'wrong_commit_operator', 'wrong_actor_role', 'wrong_surface_role', 'wrong_target_role', 'bad_effect_owner', 'external_adapter', 'review_false', 'review_int', 'existing_false', 'existing_string', 'empty_kinds', 'duplicate_kinds', 'unknown_kind', 'kinds_string', 'kind_type', 'wrong_source_capability', 'wrong_source_permission', 'wrong_source_adapter', 'missing_source_signature', 'duplicate_source_signature', 'extra_source_role', 'duplicate_source_role', 'optional_actor', 'integer_required', 'proposition_surface', 'integer_proposition', 'wrong_actor_kinds', 'wrong_surface_kinds', 'mismatched_target_kinds', 'wrong_commit_roles', 'wrong_source_roles', 'duplicate_contract', 'duplicate_source_mapping', 'wrong_contract_owner', 'duplicate_owner_name', 'owner_name_mismatch', 'collection_object', 'contract_not_object', 'unreviewed_contract_atom', 'truthy_reviewed_contract_atom', 'source_caps_type', 'source_roles_object', 'source_role_unknown_field', 'duplicate_operator_owner', 'duplicate_owner_path', 'label_name', 'source_signature_unknown_field', 'target_kinds_unsorted'),
)
def test_alias_contract_linking_rejects_invalid_authority_atomically(tmp_path, mutation):
    owners = _owners()
    row = owners["alias_learning"]["learning_contracts"][0]
    sig = _source_signature(owners)
    if mutation == "unknown_field":
        row["learning_operation"] = "resolve_designation"
    elif mutation == "missing_field":
        del row["goal_ref"]
    elif mutation in {"bad_ref_type", "empty_ref", "oversize_ref"}:
        row["goal_ref"] = {"bad_ref_type": 1, "empty_ref": "", "oversize_ref": "goal:" + "a" * 512}[mutation]
    elif mutation.startswith("wrong_") and mutation.endswith("_kind"):
        field = {
            "contract": "contract_ref", "goal": "goal_ref", "answer": "answer_contract_ref",
            "policy": "review_policy_ref", "event": "source_event_ref", "capability": "capability_ref",
            "permission": "permission_ref", "adapter": "internal_adapter_ref", "label": "designation_label_ref",
        }[mutation[len("wrong_"):-len("_kind")]]
        for owner in owners.values():
            for atom in owner["atoms"]:
                if atom["ref"] == row[field]:
                    atom["kind"] = "entity"
    elif mutation.startswith("missing_") and mutation != "missing_source_signature":
        field = {"contract": "contract_ref", "goal": "goal_ref", "answer": "answer_contract_ref", "policy": "review_policy_ref", "capability": "capability_ref", "permission": "permission_ref", "adapter": "internal_adapter_ref"}[mutation[len("missing_"):]]
        row[field] = "missing:authority"
    elif mutation in {"wrong_source_operator", "wrong_commit_operator"}:
        row["source_operator_ref" if mutation == "wrong_source_operator" else "commit_operator_ref"] = "op:relation"
    elif mutation in {"wrong_actor_role", "wrong_surface_role", "wrong_target_role"}:
        row[mutation[len("wrong_"):] + "_ref"] = "role:content"
    elif mutation == "bad_effect_owner":
        row["internal_effect_owner"] = "EVALUATE"
    elif mutation == "external_adapter":
        row["internal_adapter_ref"] = "adapter:state"
    elif mutation in {"review_false", "review_int", "existing_false", "existing_string"}:
        row["requires_explicit_review" if mutation.startswith("review") else "existing_targets_only"] = {"review_false": False, "review_int": 1, "existing_false": False, "existing_string": "true"}[mutation]
    elif mutation in {"empty_kinds", "duplicate_kinds", "unknown_kind", "kinds_string", "kind_type"}:
        row["allowed_target_kinds"] = {"empty_kinds": [], "duplicate_kinds": ["concept", "concept"], "unknown_kind": ["permission"], "kinds_string": "concept", "kind_type": [1]}[mutation]
    elif mutation in {"wrong_source_capability", "wrong_source_permission", "wrong_source_adapter"}:
        key, value = {"wrong_source_capability": ("required_capabilities", ["cap:query"]), "wrong_source_permission": ("required_permissions", ["permission:set_state"]), "wrong_source_adapter": ("adapter_ref", "adapter:state")}[mutation]
        sig[key] = value
    elif mutation == "missing_source_signature":
        owners["conversation"]["event_signatures"].remove(sig)
    elif mutation == "duplicate_source_signature":
        owners["conversation"]["event_signatures"].append(copy.deepcopy(sig))
    elif mutation in {"extra_source_role", "duplicate_source_role"}:
        extra = copy.deepcopy(sig["roles"][0])
        if mutation == "extra_source_role":
            extra["role"] = "role:content"
        sig["roles"].append(extra)
    elif mutation in {"optional_actor", "integer_required", "proposition_surface", "integer_proposition"}:
        index, key, value = {"optional_actor": (0, "required", False), "integer_required": (0, "required", 1), "proposition_surface": (2, "proposition_valued", True), "integer_proposition": (2, "proposition_valued", 0)}[mutation]
        sig["roles"][index][key] = value
    elif mutation in {"wrong_actor_kinds", "wrong_surface_kinds", "mismatched_target_kinds"}:
        index = {"wrong_actor_kinds": 0, "wrong_surface_kinds": 2, "mismatched_target_kinds": 1}[mutation]
        sig["roles"][index]["filler_kinds"] = ["concept"]
    elif mutation in {"wrong_commit_roles", "wrong_source_roles"}:
        owners["kernel"]["operator_roles"]["op:designation" if mutation == "wrong_commit_roles" else "op:event"] = ["role:subject", "role:object"]
    elif mutation == "duplicate_contract":
        owners["alias_learning"]["learning_contracts"].append(copy.deepcopy(row))
    elif mutation == "duplicate_source_mapping":
        duplicate = copy.deepcopy(row)
        duplicate["contract_ref"] = "contract:second"
        owners["alias_learning"]["atoms"].append({"ref": "contract:second", "kind": "learning_contract", "reviewed": True})
        owners["alias_learning"]["learning_contracts"].append(duplicate)
    elif mutation == "wrong_contract_owner":
        owners["conversation"]["learning_contracts"] = owners["alias_learning"].pop("learning_contracts")
    elif mutation == "duplicate_owner_name":
        owners["duplicate"] = {"owner": "duplicate", "atoms": []}
    elif mutation == "owner_name_mismatch":
        owners["alias_learning"]["owner"] = "other"
    elif mutation == "collection_object":
        owners["alias_learning"]["learning_contracts"] = {"first": row}
    elif mutation == "contract_not_object":
        owners["alias_learning"]["learning_contracts"] = [True]
    elif mutation in {"unreviewed_contract_atom", "truthy_reviewed_contract_atom"}:
        owners["alias_learning"]["atoms"][0]["reviewed"] = False if mutation == "unreviewed_contract_atom" else 1
    elif mutation == "source_caps_type":
        sig["required_capabilities"] = True
    elif mutation == "source_roles_object":
        sig["roles"] = {"actor": sig["roles"][0]}
    elif mutation == "source_role_unknown_field":
        sig["roles"][0]["optional"] = True
    elif mutation == "duplicate_operator_owner":
        owners["alias_learning"]["operator_roles"] = {"op:designation": owners["kernel"]["operator_roles"]["op:designation"]}
    elif mutation == "duplicate_owner_path":
        pass  # Applied after manifest construction.
    elif mutation == "label_name":
        row["designation_label_ref"] = "label:name"
    elif mutation == "source_signature_unknown_field":
        sig["unreviewed_lowering"] = True
    elif mutation == "target_kinds_unsorted":
        row["allowed_target_kinds"].reverse()
    else:
        raise AssertionError(mutation)
    manifest = _manifest(tmp_path, owners)
    if mutation == "duplicate_owner_name":
        manifest["owners"][-1]["name"] = "alias_learning"
    if mutation == "duplicate_owner_path":
        manifest["owners"][-1]["path"] = manifest["owners"][0]["path"]
    store = AuthorityStore()
    with pytest.raises(AuthorityLinkError):
        AuthorityLinker().link({**manifest, "_store": store})
    assert store.active_generation is None


def test_alias_contract_duplicate_json_field_is_rejected(tmp_path):
    manifest = _manifest(tmp_path, _owners())
    owner = manifest["owners"][-1]
    path = Path(owner["path"])
    text = path.read_text("utf-8").replace('"requires_explicit_review": true', '"requires_explicit_review": false, "requires_explicit_review": true')
    path.write_text(text, encoding="utf-8")
    owner["sha256"] = sha256_governed_text(path)
    with pytest.raises(AuthorityLinkError, match="duplicate"):
        AuthorityLinker().link(manifest)


@pytest.mark.parametrize("field,value", [
    ("effect_schema", [{"operator": "op:state", "args": {"role:subject": "entity:server", "role:dimension": "dim:availability", "role:value": "value:online"}}]),
    ("effect_schema", "bad"),
    ("effect_schema", {}),
    ("effect_schema", False),
    ("effect_schema", None),
    ("valid_session_phases", "active"),
    ("valid_session_phases", {"active": True}),
    ("valid_session_phases", ["invalid-phase"]),
    ("valid_session_phases", [1]),
    ("valid_session_phases", [True]),
    ("valid_session_phases", []),
    ("valid_session_phases", ["active", "active"]),
    ("valid_session_phases", ["opening", "active", "suspended", "active"]),
    ("valid_session_phases", None),
], ids=[
    "extra-state-effect", "effect-string", "effect-object", "effect-bool", "effect-null",
    "phases-string", "phases-object", "unknown-phase", "phase-int", "phase-bool",
    "empty-phases", "duplicate-phase", "oversize-phases", "phases-null",
])
def test_alias_source_constraints_reject_discarded_effects_and_malformed_phases(tmp_path, field, value):
    owners = _owners()
    _source_signature(owners)[field] = value
    store = AuthorityStore()
    manifest = _manifest(tmp_path, owners)
    with pytest.raises(AuthorityLinkError):
        AuthorityLinker().link({**manifest, "_store": store})
    assert store.active_generation is None


@pytest.mark.parametrize("phases", [
    None, ["opening"], ["active"], ["suspended"], ["opening", "active", "suspended"],
], ids=["established-default", "opening", "active", "suspended", "all-established-phases"])
def test_alias_source_constraints_preserve_empty_effect_and_established_phase_semantics(tmp_path, phases):
    owners = _owners()
    signature = _source_signature(owners)
    signature["effect_schema"] = []
    if phases is not None:
        signature["valid_session_phases"] = phases
    linked = AuthorityLinker().link(_manifest(tmp_path, owners))
    source = linked.by_event_signature("event:learn_alias")
    assert source.effect_schema == ()
    assert source.valid_session_phases == (("opening", "active") if phases is None else tuple(phases))
    assert linked.learning_contract_for_source("op:event", "event:learn_alias") is not None


def test_alias_contract_hash_receives_every_typed_field(tmp_path, monkeypatch):
    real_hash = authority_module.stable_ref
    hashed_contracts = []

    def recording_hash(namespace, payload):
        if namespace == "authority-content":
            hashed_contracts.extend(payload["learning_contracts"])
        return real_hash(namespace, payload)

    monkeypatch.setattr(authority_module, "stable_ref", recording_hash)
    linked = AuthorityLinker().link(_manifest(tmp_path, _owners()))
    assert linked.content_hash.startswith("authority-content:")
    assert hashed_contracts == [_contract()]


def test_alias_contract_hash_is_canonical_and_covers_every_field(tmp_path):
    owners = _owners()
    # Keep the complete atom graph fixed so only contract metadata changes.
    for atom in list(owners["alias_learning"]["atoms"]):
        owners["alias_learning"]["atoms"].append({**atom, "ref": atom["ref"] + ":other"})
    linked = AuthorityLinker().link(_manifest(tmp_path / "first", owners))
    assert hasattr(linked, "learning_contract"), "learning contract hashing is missing"
    contract = linked.learning_contract(_contract()["contract_ref"])
    assert set(contract.to_dict()) == set(_contract())
    reversed_owners = dict(reversed(list(owners.items())))
    repeated = AuthorityLinker().link(_manifest(tmp_path / "second", reversed_owners))
    assert repeated.content_hash == linked.content_hash
    assert repeated.learning_contract(contract.contract_ref) == contract
    for index, field in enumerate(("goal_ref", "answer_contract_ref", "review_policy_ref", "contract_ref")):
        changed = copy.deepcopy(owners)
        original = changed["alias_learning"]["learning_contracts"][0][field]
        replacement = original + ":other"
        changed["alias_learning"]["learning_contracts"][0][field] = replacement
        assert AuthorityLinker().link(_manifest(tmp_path / str(index), changed)).content_hash != linked.content_hash


def test_alias_authority_does_not_add_designations_or_external_adapter_availability(tmp_path):
    linked = AuthorityLinker().link(_manifest(tmp_path, _owners()))
    assert hasattr(linked, "learning_contract_for_source"), "learning contract authority is missing"
    for ref in ("contract:designation_learning:v2", "goal:resolve_designation", "contract:designation_answer:v2", "policy:learning_directive_requires_review:v2"):
        assert linked.designations.for_target(ref, "en") == ()
        assert linked.designations.for_surface(ref.split(":", 1)[1].replace("_", " "), "en") == ()
    assert linked.designations.for_surface("velnora", "en") == ()
    assert "concept:zorbulate" not in linked.atoms
    from cemm_authoritative_hybrid.r3_effects import AdapterRegistry
    assert AdapterRegistry().refs == ()


def test_active_alias_authority_fresh_runtime_reopen_and_prior_generation_rejection(tmp_path):
    from cemm_authoritative_hybrid.bootstrap import load_runtime
    from cemm_authoritative_hybrid.persistence import open_stores, StoreActivationError

    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "fresh.db")
    try:
        generation = runtime.authority.generation
        assert generation != "authority-v1-2026-07-29"
        assert runtime.authority.learning_contract_for_source("op:event", "event:learn_alias") is not None
        assert runtime.stores.revision_pin().authority_generation == generation
    finally:
        runtime.stores.close()
    reopened = load_runtime(ROOT, profile="development", store_path=tmp_path / "fresh.db")
    try:
        assert reopened.authority.generation == generation
        assert reopened.authority.learning_contract_for_source("op:event", "event:learn_alias") is not None
    finally:
        reopened.stores.close()
    prior = open_stores(tmp_path / "prior.db", authority_generation="authority-v1-2026-07-29")
    prior.close()
    with pytest.raises(StoreActivationError, match="authority generation mismatch"):
        load_runtime(ROOT, profile="development", store_path=tmp_path / "prior.db")


def test_historical_splitter_rejects_existing_authority_before_any_write(tmp_path):
    source_dir = tmp_path / "scripts"
    source_dir.mkdir()
    script = source_dir / "gen_authority_split.py"
    shutil.copyfile(ROOT / "scripts" / script.name, script)
    authority_dir = tmp_path / "data" / "authority"
    authority_dir.mkdir(parents=True)
    for name in ("manifest", "kernel", "conversation", "state_operations", "alias_learning"):
        shutil.copyfile(ROOT / "data" / "authority" / f"{name}.json", authority_dir / f"{name}.json")
    legacy = {name: [] for name in ("atoms", "designations", "event_signatures", "rules", "permissions", "adapters")}
    legacy.update({name: {} for name in ("capabilities", "operator_roles", "value_dimensions")})
    for owner in list(_owners().values())[:3]:
        for name in legacy:
            if isinstance(legacy[name], list):
                legacy[name].extend(owner[name])
            else:
                legacy[name].update(owner[name])
    (tmp_path / "data" / "authority.json").write_text(json.dumps(legacy), encoding="utf-8")
    before = {path.name: path.read_bytes() for path in authority_dir.iterdir()}
    result = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    assert result.returncode != 0, "historical splitter overwrote reviewed active authority"
    assert "existing authority" in result.stdout + result.stderr
    assert {path.name: path.read_bytes() for path in authority_dir.iterdir()} == before


def test_link_path_returns_current_linked_alias_authority():
    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    assert isinstance(linked, LinkedAuthority)
    assert linked.content_hash.startswith("authority-content:")
    assert linked.model_compatibility_hash.startswith("authority-compat:")
    assert linked.generation == "authority-v1-2026-10-01-communicative-controls"


def test_all_active_alias_authority_atoms_have_valid_kinds(linked_authority):
    valid_kinds = {
        "participant", "entity", "concept", "label_type", "relation_type",
        "state_dimension", "state_value", "event_type", "capability",
        "permission", "adapter", "learning_contract", "goal", "answer_contract", "policy",
    }
    for atom in linked_authority.atoms.values():
        assert atom.kind in valid_kinds


def test_current_alias_authority_link_is_content_addressed_and_fail_closed(tmp_path):
    from tests.test_r1_validation_gate import _context, gate

    context = _context(tmp_path)
    result = context.run_authority_link()
    assert result.disposition == "passed"
    assert result.report is not None
    assert result.report["schema"] == "cemm-authority-link-step-report-v1"
    assert result.report["generation"] == "authority-v1-2026-10-01-communicative-controls"
    assert result.report["authority_ref"].startswith("linked_authority:")

    manifest = ROOT / "data" / "authority" / "manifest.json"
    original = context._read_bytes
    context._read_bytes = lambda path: b"{}" if path == manifest else original(path)
    with pytest.raises(gate.GateConfigError, match="authority link failed"):
        context.run_authority_link()
