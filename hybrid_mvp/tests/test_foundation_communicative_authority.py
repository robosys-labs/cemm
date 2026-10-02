"""Activation-only reviewed communication policy; no lexical or effect grant."""
from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid import authority as owner
from cemm_authoritative_hybrid.canonical import sha256_governed_text

ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_communicative_authority.py::test_communicative_record_is_frozen_and_strict": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-communicative-record-is-frozen-and-strict", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "34e051a81904141dd7053cc814693dcd64c202631b3fc926696fc70806719937"},
    "tests/test_foundation_communicative_authority.py::test_registered_owner_requires_control_collection": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-registered-owner-requires-control-collection", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "da77396900dfee5426f1adb410072973fef91dc9a5b6339d56fbf1874dfabf5a"},
    "tests/test_foundation_communicative_authority.py::test_control_lookup_is_generation_pinned_immutable_and_indexed": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-control-lookup-is-generation-pinned-immutable-and-indexed", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "f84a4aedfd2ffe1879da720079a64320f813b0df32d24e4593f0304384669cb1"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[collection-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-collection-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[row-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-row-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[unknown-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-unknown-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[missing-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-missing-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[ref-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-ref-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[bad-ref]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-bad-ref", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[overlong-ref]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-overlong-ref", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[ref-namespace]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-ref-namespace", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[frame-namespace]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-frame-namespace", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[target-namespace]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-target-namespace", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[role-namespace]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-role-namespace", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[cap-namespace]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-cap-namespace", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[construction]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-construction", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[response]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-response", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[missing-target]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-missing-target", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[missing-frame]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-missing-frame", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[wrong-frame]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-wrong-frame", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[same-roles]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-same-roles", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[wrong-role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-wrong-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[missing-cap]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-missing-cap", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[wrong-cap-kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-wrong-cap-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[duplicate]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-duplicate", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[target-conflict]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-target-conflict", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[atom-collision]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-atom-collision", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[frame-collision]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-frame-collision", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[source-collision]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-source-collision", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[inheritance-collision]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-inheritance-collision", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[no-predicate]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-no-predicate", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[stale-generation]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-stale-generation", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[owner-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-owner-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[missing-actor]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-missing-actor", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[third-role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-third-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[proposition-role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-proposition-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[concept-filler]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-concept-filler", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[actor-optional]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-actor-optional", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[effects]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-effects", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[effect-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-effect-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[adapter]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-adapter", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[cap-requirement]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-cap-requirement", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[permission]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-permission", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_malformed_control_fails_before_activation[signature-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-malformed-control-fails-before-activation-signature-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "28a451fcbb580e5f6104ca87f10ed408a5e5cbe4badcc5fe1ded946dc3cf93eb"},
    "tests/test_foundation_communicative_authority.py::test_empty_or_unregistered_controls_grant_nothing": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-empty-or-unregistered-controls-grant-nothing", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "0d02c9bea8cf9db6708f17bebff0367d5719eb3a3eb851ce393aaa0e86b82ad2"},
    "tests/test_foundation_communicative_authority.py::test_reciprocal_control_cannot_substitute_alias_learning_capability": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-reciprocal-control-cannot-substitute-alias-learning-capability", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "583058e84119a1e04a09b6227c824b9c3eaa87771717dc0252106b2a3964a717"},
    "tests/test_foundation_communicative_authority.py::test_policy_content_changes_both_hashes_and_not_designations": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-policy-content-changes-both-hashes-and-not-designations", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "4e327c1e090400cd613ef3ac5325eaff8acbf408710b6929d511a2ddbea6445e"},
    "tests/test_foundation_communicative_authority.py::test_registered_policy_file_failure_is_atomic[missing]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-registered-policy-file-failure-is-atomic-missing", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "0d50c5b2d87c4fceb6967b2d94eddd4996f604531cbd97e26d620977251cb21c"},
    "tests/test_foundation_communicative_authority.py::test_registered_policy_file_failure_is_atomic[hash]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-registered-policy-file-failure-is-atomic-hash", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "0d50c5b2d87c4fceb6967b2d94eddd4996f604531cbd97e26d620977251cb21c"},
    "tests/test_foundation_communicative_authority.py::test_registered_policy_file_failure_is_atomic[json]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-registered-policy-file-failure-is-atomic-json", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "0d50c5b2d87c4fceb6967b2d94eddd4996f604531cbd97e26d620977251cb21c"},
    "tests/test_foundation_communicative_authority.py::test_active_policy_and_store_restart_reject_old_generation_without_writes": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-active-policy-and-store-restart-reject-old-generation-without-writes", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "4b4b3b144f07d45e418294a4e49225299dd056064a0d4eac664c683c40cdf8e6"},
    "tests/test_foundation_communicative_authority.py::test_reciprocal_roles_must_accept_actual_participants[actor-entity-only]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-reciprocal-roles-must-accept-actual-participants-actor-entity-only", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "c191ac72d04f61e1c2feae62f1ac707ff264712ce3385a89e2335867f7976f41"},
    "tests/test_foundation_communicative_authority.py::test_reciprocal_roles_must_accept_actual_participants[addressee-entity-only]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-communicative-reciprocal-roles-must-accept-actual-participants-addressee-entity-only", "diagnostic_role": "owner", "introduced_by_task": "Foundation-C2", "owner_ref": "semantic-affordances", "source_ast_sha256": "c191ac72d04f61e1c2feae62f1ac707ff264712ce3385a89e2335867f7976f41"},
}
SOURCE = ROOT / "data/authority/frames/semantic_affordances.json"
GENERATION = "authority-v1-2026-10-01-communicative-controls"


def _control(target="greeting"):
    return {
        "control_ref": f"control:communicative:event_{target}",
        "source_frame_ref": f"frame:event:{target}",
        "target_ref": f"event:{target}",
        "actor_role_ref": "role:actor",
        "addressee_role_ref": "role:addressee",
        "construction_kind": "direct_performed",
        "response_kind": "reciprocal_event",
        "required_capability_ref": "cap:respond",
    }


def _source():
    source = json.loads(SOURCE.read_text("utf-8"))
    source["generation"] = GENERATION
    if not any(row["target_ref"] == "event:farewell" for row in source["frames"]):
        source["frames"].append({**source["frames"][0], "frame_ref": "frame:event:farewell", "target_ref": "event:farewell"})
    source["communicative_controls"] = [_control(), _control("farewell")]
    return source


def _bundle(tmp_path, source=None, conversation=None):
    manifest = json.loads((ROOT / "data/authority/manifest.json").read_text("utf-8"))
    manifest["generation"] = GENERATION
    for row in manifest["owners"]:
        row["path"] = str(ROOT / "data/authority" / row["path"])
    for name, data in (("semantic_affordances", source), ("conversation", conversation)):
        if data is None:
            continue
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        next(row for row in manifest["owners"] if row["name"] == name).update(path=str(path), sha256=sha256_governed_text(path))
    store = owner.AuthorityStore()
    manifest["_store"] = store
    return manifest, store


def test_communicative_record_is_frozen_and_strict():
    assert hasattr(owner, "CommunicativeControl"), "typed activation policy is missing"
    record = owner.CommunicativeControl.from_dict(_control())
    assert record.to_dict() == _control()
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.target_ref = "event:farewell"


def test_registered_owner_requires_control_collection(tmp_path):
    source = _source()
    del source["communicative_controls"]
    manifest, store = _bundle(tmp_path, source)
    with pytest.raises(owner.AuthorityLinkError):
        owner.AuthorityLinker().link(manifest)
    assert store.active_generation is None


def test_control_lookup_is_generation_pinned_immutable_and_indexed(tmp_path):
    manifest, _ = _bundle(tmp_path, _source())
    linked = owner.AuthorityLinker().link(manifest)
    class NoEnumeration(dict):
        def __iter__(self):
            raise AssertionError("normal lookup scanned atoms")
        def values(self):
            raise AssertionError("normal lookup scanned atoms")
        def items(self):
            raise AssertionError("normal lookup scanned atoms")
    linked.atoms = NoEnumeration(linked.atoms)
    record = linked.communicative_control_for_target("event:greeting")
    assert record.to_dict() == _control()
    assert linked.communicative_control_for_target("event:missing") is None
    with pytest.raises(TypeError):
        linked.communicative_controls["event:greeting"] = record
    with pytest.raises(AttributeError):
        linked.communicative_controls = {}
    generation, content, rules = linked.rule_generation_snapshot()
    linked._rule_generation_state = (generation + "-stale", content, rules)
    with pytest.raises(owner.AuthorityLinkError):
        linked.communicative_control_for_target("event:greeting")
    linked._rule_generation_state = (generation, content + "-corrupt", rules)
    with pytest.raises(owner.AuthorityLinkError):
        linked.communicative_control_for_target("event:missing")


@pytest.mark.parametrize("damage", [
    "collection-type", "row-type", "unknown-field", "missing-field", "ref-type", "bad-ref", "overlong-ref", "ref-namespace", "frame-namespace", "target-namespace", "role-namespace", "cap-namespace", "construction", "response", "missing-target", "missing-frame", "wrong-frame", "same-roles", "wrong-role", "missing-cap", "wrong-cap-kind", "duplicate", "target-conflict", "atom-collision", "frame-collision", "source-collision", "inheritance-collision", "no-predicate", "stale-generation", "owner-field", "missing-actor", "third-role", "proposition-role", "concept-filler", "actor-optional", "effects", "effect-type", "adapter", "cap-requirement", "permission", "signature-field",
], ids=[
    "collection-type", "row-type", "unknown-field", "missing-field", "ref-type", "bad-ref", "overlong-ref", "ref-namespace", "frame-namespace", "target-namespace", "role-namespace", "cap-namespace", "construction", "response", "missing-target", "missing-frame", "wrong-frame", "same-roles", "wrong-role", "missing-cap", "wrong-cap-kind", "duplicate", "target-conflict", "atom-collision", "frame-collision", "source-collision", "inheritance-collision", "no-predicate", "stale-generation", "owner-field", "missing-actor", "third-role", "proposition-role", "concept-filler", "actor-optional", "effects", "effect-type", "adapter", "cap-requirement", "permission", "signature-field",
])
def test_malformed_control_fails_before_activation(tmp_path, damage):
    source = _source()
    row = source["communicative_controls"][0]
    conversation = json.loads((ROOT / "data/authority/conversation.json").read_text("utf-8"))
    signature = next(row for row in conversation["event_signatures"] if row["event_type"] == "event:greeting")
    mutations = {
        "ref-type": ("control_ref", True), "bad-ref": ("control_ref", "control:bad ref"), "overlong-ref": ("control_ref", "control:" + "x" * 512),
        "ref-namespace": ("control_ref", "event:control"), "frame-namespace": ("source_frame_ref", "event:greeting"), "target-namespace": ("target_ref", "concept:mother"), "role-namespace": ("actor_role_ref", "event:actor"), "cap-namespace": ("required_capability_ref", "event:greeting"),
        "construction": ("construction_kind", "reported"), "response": ("response_kind", "reply"), "missing-target": ("target_ref", "event:absent"), "missing-frame": ("source_frame_ref", "frame:absent"), "wrong-frame": ("source_frame_ref", "frame:event:say"),
        "same-roles": ("addressee_role_ref", "role:actor"), "wrong-role": ("actor_role_ref", "role:subject"), "missing-cap": ("required_capability_ref", "cap:absent"), "wrong-cap-kind": ("required_capability_ref", "cap:learn_alias"),
        "atom-collision": ("control_ref", "cap:respond"), "frame-collision": ("control_ref", "frame:event:greeting"), "source-collision": ("control_ref", source["source_attribution_controls"][0]["control_ref"]), "inheritance-collision": ("control_ref", source["reported_role_inheritance_controls"][0]["control_ref"]),
    }
    if damage in mutations:
        key, value = mutations[damage]
        row[key] = value
        if damage == "wrong-cap-kind":
            next(atom for atom in conversation["atoms"] if atom["ref"] == "cap:learn_alias")["kind"] = "concept"
    elif damage == "collection-type": source["communicative_controls"] = {}
    elif damage == "row-type": source["communicative_controls"][0] = []
    elif damage == "unknown-field": row["permission_ref"] = "permission:write_alias"
    elif damage == "missing-field": del row["response_kind"]
    elif damage == "duplicate": source["communicative_controls"].append(copy.deepcopy(row))
    elif damage == "target-conflict": source["communicative_controls"].append({**row, "control_ref": "control:conflict"})
    elif damage == "no-predicate": source["frames"][0]["contribution_kinds"] = ["anchor"]
    elif damage == "stale-generation": source["generation"] = "authority:old"
    elif damage == "owner-field": source["lexemes"] = {}
    elif damage == "missing-actor": signature["roles"].pop(0)
    elif damage == "third-role": signature["roles"].append({**signature["roles"][0], "role": "role:other"})
    elif damage == "proposition-role": signature["roles"][1].update(filler_kinds=["application"], proposition_valued=True)
    elif damage == "concept-filler": signature["roles"][1]["filler_kinds"] = ["concept"]
    elif damage == "actor-optional": signature["roles"][0]["required"] = False
    elif damage == "effects": signature["effect_schema"] = [{"operator": "op:event"}]
    elif damage == "effect-type": signature["effect_schema"] = {}
    elif damage == "adapter": signature["adapter_ref"] = "adapter:memory"
    elif damage == "cap-requirement": signature["required_capabilities"] = "cap:respond"
    elif damage == "permission": signature["required_permissions"] = ["permission:write_alias"]
    elif damage == "signature-field": signature["extra"] = True
    manifest, store = _bundle(tmp_path, source, conversation)
    with pytest.raises(owner.AuthorityLinkError):
        owner.AuthorityLinker().link(manifest)
    assert store.active_generation is None


def test_empty_or_unregistered_controls_grant_nothing(tmp_path):
    source = _source()
    source["communicative_controls"] = []
    manifest, _ = _bundle(tmp_path, source)
    assert owner.AuthorityLinker().link(manifest).communicative_control_for_target("event:greeting") is None
    manifest["owners"] = [row for row in manifest["owners"] if row["name"] != "semantic_affordances"]
    linked = owner.AuthorityLinker().link(manifest)
    assert linked.communicative_control_for_target("event:greeting") is None
    assert linked.reviewed_frames_for_target("event:greeting") == ()


def test_reciprocal_control_cannot_substitute_alias_learning_capability(tmp_path):
    source = _source()
    source["communicative_controls"][0]["required_capability_ref"] = "cap:learn_alias"
    manifest, store = _bundle(tmp_path, source)
    with pytest.raises(owner.AuthorityLinkError, match="cap:respond"):
        owner.AuthorityLinker().link(manifest)
    assert store.active_generation is None


@pytest.mark.parametrize("role_index", [0, 1], ids=["actor-entity-only", "addressee-entity-only"])
def test_reciprocal_roles_must_accept_actual_participants(tmp_path, role_index):
    conversation = json.loads((ROOT / "data/authority/conversation.json").read_text("utf-8"))
    signature = next(row for row in conversation["event_signatures"] if row["event_type"] == "event:greeting")
    signature["roles"][role_index]["filler_kinds"] = ["entity"]
    source = _source()
    # Remove independent report inheritance so this negative isolates C2.
    source["reported_role_inheritance_controls"] = []
    manifest, store = _bundle(tmp_path, source, conversation)
    with pytest.raises(owner.AuthorityLinkError, match="participant"):
        owner.AuthorityLinker().link(manifest)
    assert store.active_generation is None


def test_policy_content_changes_both_hashes_and_not_designations(tmp_path, monkeypatch):
    hash_payloads = {}
    stable_ref = owner.stable_ref
    def capture(kind, payload):
        if kind in {"authority-content", "authority-compat"}:
            hash_payloads[kind] = payload
        return stable_ref(kind, payload)
    monkeypatch.setattr(owner, "stable_ref", capture)
    source = _source()
    manifest, _ = _bundle(tmp_path, source)
    first = owner.AuthorityLinker().link(manifest)
    expected_controls = sorted(source["communicative_controls"], key=lambda row: row["control_ref"])
    assert hash_payloads["authority-content"]["communicative_controls"] == expected_controls
    assert hash_payloads["authority-compat"]["communicative_controls"] == expected_controls
    source["communicative_controls"].reverse()
    manifest, _ = _bundle(tmp_path, source)
    reordered = owner.AuthorityLinker().link(manifest)
    assert (first.content_hash, first.model_compatibility_hash) == (reordered.content_hash, reordered.model_compatibility_hash)
    for field in ("control_ref",):
        changed = _source()
        changed["communicative_controls"][0][field] = "control:alternate"
        manifest, _ = _bundle(tmp_path, changed)
        later = owner.AuthorityLinker().link(manifest)
        assert later.content_hash != first.content_hash
        assert later.model_compatibility_hash != first.model_compatibility_hash
    for record in first.communicative_controls.values():
        assert first.designations.for_surface(record.control_ref, "en") == ()
        assert first.designations.for_surface(record.source_frame_ref, "en") == ()


@pytest.mark.parametrize("damage", ["missing", "hash", "json"], ids=["missing", "hash", "json"])
def test_registered_policy_file_failure_is_atomic(tmp_path, damage):
    manifest, store = _bundle(tmp_path, _source())
    row = next(row for row in manifest["owners"] if row["name"] == "semantic_affordances")
    path = Path(row["path"])
    if damage == "missing": path.unlink()
    elif damage == "hash": path.write_text("{}", encoding="utf-8")
    else:
        path.write_text("{bad", encoding="utf-8")
        row["sha256"] = sha256_governed_text(path)
    with pytest.raises(owner.AuthorityLinkError):
        owner.AuthorityLinker().link(manifest)
    assert store.active_generation is None


def test_active_policy_and_store_restart_reject_old_generation_without_writes(tmp_path):
    from cemm_authoritative_hybrid.bootstrap import load_runtime
    from cemm_authoritative_hybrid.persistence import open_stores, StoreActivationError
    old_path = tmp_path / "old"
    stores = open_stores(old_path, authority_generation="authority-v1-2026-09-09-reported-role-inheritance")
    stores.close()
    before = (old_path / "semantic.db").read_bytes()
    with pytest.raises(StoreActivationError, match="authority generation mismatch"):
        load_runtime(ROOT, profile="development", store_path=old_path)
    assert (old_path / "semantic.db").read_bytes() == before
    wal = old_path / "semantic.db-wal"
    assert not wal.exists() or wal.read_bytes() == b""
    for _ in range(2):
        runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "fresh")
        try:
            assert runtime.authority.generation == "authority-v1-2026-10-02-communicative-source"
            assert runtime.stores.revision_pin().authority_generation == runtime.authority.generation
            assert tuple(runtime.authority.communicative_controls) == ("event:farewell", "event:greeting")
            for target in ("greeting", "farewell"):
                assert runtime.authority.communicative_control_for_target(f"event:{target}").to_dict() == _control(target)
        finally:
            runtime.stores.close()
