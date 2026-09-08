"""Independent out-of-band review, never dialogue-supplied publication authority."""
import hashlib
import hmac
import json
import secrets
from dataclasses import replace

import pytest

from cemm_authoritative_hybrid import bootstrap, persistence, r3_learning
from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, R3EffectGateway
from tests.test_foundation_learning_proposal import ROOT, _setup

__cemm_test_inventory__ = {
    "tests/test_foundation_alias_publication.py::test_alias_publication_is_default_deny": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-is-default-deny",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1906ebbd8f8ac63dfef6857739a3a1f62abeb0999af446630957bae0901e5867"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[forged-mac]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-forged-mac",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[key]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-key",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[reviewer]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-reviewer",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[policy]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-policy",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[store]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-store",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[proposal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-proposal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[proposal-journal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-proposal-journal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[receipt]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-receipt",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[plan]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-plan",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[pending]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-pending",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[source-journal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-source-journal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[surface]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-surface",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[target]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[language]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-language",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[missing-language]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-missing-language",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rejects_unauthenticated_or_wrong_scope[expiry]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rejects-unauthenticated-or-wrong-scope-expiry",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b66b90f61ca6d5c82db2aeb6f982cb0d49dc293a5e78cc2c89a8a99c78c93ff2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[resolved]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-resolved",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[replaced]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-replaced",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[expired]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-expired",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[rewound]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-rewound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[phase]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-phase",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[capability]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-capability",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[permission]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-permission",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[target]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_rechecks_current_eligibility[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-rechecks-current-eligibility-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f77f53886725b3b85f9f2532c21e53bea5600f7c741b581387f08ddb67a55bbd"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_actual_reopen_retry_and_copied_path_denial": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-actual-reopen-retry-and-copied-path-denial",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d67551bf4c7b3f8e126d1fd65617932efa96621033d38060edba9ea14a51d0e9"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_fault_rolls_back_all_then_restarts_once[after-fact]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-fault-rolls-back-all-then-restarts-once-after-fact",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f8a086cd813d64bcb2582e5fdd066adf854674c2f0093151380dbfa377bd5704"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_fault_rolls_back_all_then_restarts_once[after-completion]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-fault-rolls-back-all-then-restarts-once-after-completion",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f8a086cd813d64bcb2582e5fdd066adf854674c2f0093151380dbfa377bd5704"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_fault_rolls_back_all_then_restarts_once[after-journal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-fault-rolls-back-all-then-restarts-once-after-journal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f8a086cd813d64bcb2582e5fdd066adf854674c2f0093151380dbfa377bd5704"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_separately_signed_conflicting_plans_cannot_both_commit[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-separately-signed-conflicting-plans-cannot-both-commit-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "6f8258210f5b74ef0d82321f005ebbee7a126ddd8119c6266f356097903df69b"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_separately_signed_conflicting_plans_cannot_both_commit[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-separately-signed-conflicting-plans-cannot-both-commit-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "6f8258210f5b74ef0d82321f005ebbee7a126ddd8119c6266f356097903df69b"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_invalid_serialization_precedes_mutation[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-invalid-serialization-precedes-mutation-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "3019d944c89b84778512d95660176d90297c97cf70464597790b36b910759290"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_invalid_serialization_precedes_mutation[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-invalid-serialization-precedes-mutation-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "3019d944c89b84778512d95660176d90297c97cf70464597790b36b910759290"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_peer_revision_race_blocks_commit[world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-peer-revision-race-blocks-commit-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d1622fa646ab8a272f245eb1190279e3da0d407dcc9d1a90171d7899a4bf4fbb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_peer_revision_race_blocks_commit[session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-peer-revision-race-blocks-commit-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d1622fa646ab8a272f245eb1190279e3da0d407dcc9d1a90171d7899a4bf4fbb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_peer_revision_race_blocks_commit[episode]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-peer-revision-race-blocks-commit-episode",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d1622fa646ab8a272f245eb1190279e3da0d407dcc9d1a90171d7899a4bf4fbb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_peer_revision_race_blocks_commit[effect]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-peer-revision-race-blocks-commit-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d1622fa646ab8a272f245eb1190279e3da0d407dcc9d1a90171d7899a4bf4fbb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_sql_peer_revision_race_blocks_commit[obligation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-sql-peer-revision-race-blocks-commit-obligation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d1622fa646ab8a272f245eb1190279e3da0d407dcc9d1a90171d7899a4bf4fbb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_bounded_relevant_reader_uses_index[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-bounded-relevant-reader-uses-index-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5a8a017e583ac0047252a1796ce30013a263bccc2b99451041ce8515b5cef276"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_bounded_relevant_reader_uses_index[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-bounded-relevant-reader-uses-index-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5a8a017e583ac0047252a1796ce30013a263bccc2b99451041ce8515b5cef276"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_memory_requires_explicit_trusted_binding": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-memory-requires-explicit-trusted-binding",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "27f6dbbc6b808e40033181d5d0262a042e70bf5370b8543eaeabf37e149e8b4c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_linked_designation_conflict_is_not_world_admission": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-linked-designation-conflict-is-not-world-admission",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1bcd48c8d6ab2e0e581ace4e5c201413f9f4ca7cc8c9a9c348b3048f72ae1308"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_captures_verified_review_bytes_and_never_secret": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-captures-verified-review-bytes-and-never-secret",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "afa5b5dae8378bda1d4d443b4cc1cf223732e290c86b405f940e43e82f1cc845"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_fresh_grant_cannot_reuse_foreign_model_meaning": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-fresh-grant-cannot-reuse-foreign-model-meaning",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "059aa080724c050ba4c277f970b6c1c1cf15b06f07e8748e67d083383e564cdc"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_locator_does_not_reinterpret_arbitrary_world_roles": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-locator-does-not-reinterpret-arbitrary-world-roles",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "de1890294b40e479b68078b743b7e866d33b382a0db3248e9afa54cbcdddeac0"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_can_publish_later_without_repinning_answer": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-can-publish-later-without-repinning-answer",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "afa36bd38a5e4a2a28d86b7fadf4a1fb3653a2c0e98fd214174e4d8d23c5ffeb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_unfinished_retry_never_repins_changed_snapshot[planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-unfinished-retry-never-repins-changed-snapshot-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "512e699ee09fd9b0b207f5963fec7e207264de337af3570528ca08f3e74c75bb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_unfinished_retry_never_repins_changed_snapshot[observed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-unfinished-retry-never-repins-changed-snapshot-observed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "512e699ee09fd9b0b207f5963fec7e207264de337af3570528ca08f3e74c75bb"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_reserved_snapshot_recovers_after_reopen[planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-reserved-snapshot-recovers-after-reopen-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "c322c4680ab99560b9d3c233d9121b485c677c16ffe49dc88bc2c4c1b2fe1f2f"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_reserved_snapshot_recovers_after_reopen[authorized]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-reserved-snapshot-recovers-after-reopen-authorized",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "c322c4680ab99560b9d3c233d9121b485c677c16ffe49dc88bc2c4c1b2fe1f2f"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-decision]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-decision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-decision]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-decision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-key]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-key",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-origin]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-origin",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-meaning]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-meaning",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-expression]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-expression",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-situation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-situation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-program]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-program",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-event]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-event",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-intent]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-intent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-transition]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-transition",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-adapter]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-adapter",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-adapter-result]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-adapter-result",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[memory-proof]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-memory-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_commit_port_rejects_canonical_foreign_receipt[sqlite-proof]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-commit-port-rejects-canonical-foreign-receipt-sqlite-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7102f553432327ef91480cf1abaf0143b43c8c07250268f02f114ebf1841032c"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_ports_reject_mutually_consistent_unreviewed_delta[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-ports-reject-mutually-consistent-unreviewed-delta-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "29d363c9c7db59ce270ae1d6ed0d4be0bfa99691a3876056f3edb52fe1fab9f6"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_ports_reject_mutually_consistent_unreviewed_delta[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-ports-reject-mutually-consistent-unreviewed-delta-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "29d363c9c7db59ce270ae1d6ed0d4be0bfa99691a3876056f3edb52fe1fab9f6"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_same_plan_two_connections_commit_once": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-same-plan-two-connections-commit-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "860a74518486f13497e7e59509d04e46bae1dbb9a0b75e829fe30155016088de"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_locked_commit_rechecks_rehashed_journals[parent]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-locked-commit-rechecks-rehashed-journals-parent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "deddb11f998112e7ed39ae47ca3e55fa2f414886a86bab3d191c316f030cf8d2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_locked_commit_rechecks_rehashed_journals[proposal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-locked-commit-rechecks-rehashed-journals-proposal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "deddb11f998112e7ed39ae47ca3e55fa2f414886a86bab3d191c316f030cf8d2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_locked_commit_rechecks_rehashed_journals[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-locked-commit-rechecks-rehashed-journals-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "deddb11f998112e7ed39ae47ca3e55fa2f414886a86bab3d191c316f030cf8d2"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_signed_success_preserves_turn_and_lineage[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-signed-success-preserves-turn-and-lineage-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "135faf6ac3162c458a5d686b11d8ecaf209888506750c24674d2a47aff929a36"
    },
    "tests/test_foundation_alias_publication.py::test_alias_publication_signed_success_preserves_turn_and_lineage[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:alias-publication-signed-success-preserves-turn-and-lineage-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "135faf6ac3162c458a5d686b11d8ecaf209888506750c24674d2a47aff929a36"
    }
}


def _publication(tmp_path, monkeypatch, backend="sqlite"):
    runtime, source, _, _, _, _, pending = _setup(tmp_path, monkeypatch, backend)
    proposal = runtime.process(pending.session_ref, "learn velnora means likes")
    stores = runtime.stores
    secret = secrets.token_bytes(32)
    binding = stores.learning_store_binding if backend == "sqlite" else "trusted-process:test-publication"
    journal = stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key)
    plan = proposal.response_meaning.learning_plan
    grant = {"proposal_key": proposal.effect_receipt.idempotency_key,
        "proposal_journal_ref": journal["entry"]["journal_ref"],
        "proposal_receipt_ref": proposal.effect_receipt.receipt_ref,
        "plan_ref": plan.plan_ref, "source_obligation_ref": pending.obligation_ref,
        "source_query_ref": pending.source_query_ref,
        "source_journal_ref": journal["entry"]["request_payload"]["learning_source_journal"]["entry"]["journal_ref"],
        "surface": "velnora", "target_ref": "rel:likes", "language": "en",
        "reviewer_ref": "reviewer:test", "policy_ref": "policy:reviewed_alias",
        "key_ref": "key:test-reviewer", "store_binding": binding,
        "nonce": secrets.token_hex(24), "expires_at_turn": pending.expires_turn_index}
    # The review policy is linked semantic authority; the key is privileged test configuration.
    grant["policy_ref"] = runtime.authority.learning_contract_for_source("op:event", "event:learn_alias").review_policy_ref
    verifier = r3_learning.AliasReviewVerifier(key=secret, key_ref=grant["key_ref"],
        reviewer_ref=grant["reviewer_ref"], policy_ref=grant["policy_ref"], store_binding=binding)
    gateway = R3EffectGateway(stores, AdapterRegistry(), authority=runtime.authority,
        review_verifier=verifier, memory_review_binding=binding if backend == "memory" else None)
    return runtime, source, proposal, pending, gateway, grant, secret


def _signed(grant, secret):
    encoded = json.dumps(grant, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {"grant": grant, "signature": hmac.new(secret, encoded, hashlib.sha256).hexdigest()}


def test_alias_publication_is_default_deny(tmp_path, monkeypatch):
    runtime, _, _, _, _, _, pending = _setup(tmp_path, monkeypatch, "sqlite")
    try:
        proposal = runtime.process(pending.session_ref, "learn velnora means likes")
        gateway = R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority)
        assert hasattr(gateway, "publish_learning"), "missing explicit out-of-band publication owner"
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(PermissionError):
            gateway.publish_learning(proposal.effect_receipt.idempotency_key, {})
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field", ("signature", "key_ref", "reviewer_ref", "policy_ref", "store_binding",
    "proposal_key", "proposal_journal_ref", "proposal_receipt_ref", "plan_ref", "source_obligation_ref",
    "source_query_ref", "source_journal_ref", "surface", "target_ref", "language", "missing-language", "expires_at_turn"),
    ids=("forged-mac", "key", "reviewer", "policy", "store", "proposal", "proposal-journal", "receipt",
        "plan", "pending", "query", "source-journal", "surface", "target", "language", "missing-language", "expiry"))
def test_alias_publication_rejects_unauthenticated_or_wrong_scope(tmp_path, monkeypatch, field):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    try:
        changed = dict(grant)
        if field == "missing-language":
            del changed["language"]
        elif field != "signature":
            changed[field] = 999 if field == "expires_at_turn" else "fr" if field == "language" else "ref:wrong"
        signed = _signed(changed, secret)
        if field == "language":
            signed["signature"] = _signed(grant, secret)["signature"]
        if field == "signature":
            signed["signature"] = "0" * 64
        stores = runtime.stores
        before = stores.revision_pin(), stores.obligations.revision, stores.r3_session_snapshot(pending.session_ref)
        monkeypatch.setattr(AdapterRegistry, "get", lambda *a: pytest.fail("publication consulted adapter"))
        with pytest.raises((PermissionError, ValueError, TypeError)):
            gateway.publish_learning(proposal.effect_receipt.idempotency_key, signed)
        assert (stores.revision_pin(), stores.obligations.revision, stores.r3_session_snapshot(pending.session_ref)) == before
        assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("resolved", "replaced", "expired", "rewound", "phase", "capability", "permission", "target", "source"),
    ids=("resolved", "replaced", "expired", "rewound", "phase", "capability", "permission", "target", "source"))
def test_alias_publication_rechecks_current_eligibility(tmp_path, monkeypatch, case):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    stores = runtime.stores
    try:
        if case == "resolved":
            stores.obligations.commit(pending.obligation_ref, pending.session_ref, pending.as_dict(),
                expected_revision=stores.obligations.revision, resolved=True)
        elif case == "replaced":
            stores.obligations.commit("obligation:foreign", pending.session_ref, {}, expected_revision=stores.obligations.revision)
        elif case in {"expired", "rewound", "phase"}:
            session = stores._backend.sessions._sessions[pending.session_ref]
            stores._backend.sessions._sessions[pending.session_ref] = replace(session,
                **({"phase": "closed"} if case == "phase" else {"turn_index": 6 if case == "expired" else 1}))
        elif case == "source":
            key = stores.r3_effect_journal_get(grant["proposal_key"])["entry"]["request_payload"]["learning_source_key"]
            del stores._backend._r3_effect_journals[key]
        else:
            from tests.test_foundation_alias_authority import _owners, _manifest
            from cemm_authoritative_hybrid.authority import AuthorityLinker
            owners = _owners()
            if case == "capability":
                owners["kernel"]["capabilities"]["participant:system"].remove("cap:learn_alias")
            elif case == "permission":
                for owner in owners.values():
                    if "permissions" in owner:
                        owner["permissions"] = [row for row in owner["permissions"]
                            if row != ["participant:system", "permission:write_alias", "event:learn_alias"]]
            else:
                owners["kernel"]["atoms"] = [row for row in owners["kernel"]["atoms"] if row["ref"] != "rel:likes"]
            if case == "target":
                # Directly replacing the exact linked target map is an adversarial owner diagnostic.
                monkeypatch.delitem(runtime.authority.atoms, "rel:likes")
            else:
                manifest = _manifest(tmp_path / "changed-authority", owners)
                manifest["generation"] = runtime.authority.generation
                gateway._authority = AuthorityLinker().link(manifest)
        before = stores.revision_pin(), stores.obligations.revision, stores.r3_session_snapshot(pending.session_ref)
        with pytest.raises((PermissionError, ValueError, persistence.StaleRevisionError),
                match=case if case in {"capability", "permission"} else None):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert (stores.revision_pin(), stores.obligations.revision, stores.r3_session_snapshot(pending.session_ref)) == before
        assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
    finally:
        stores.close()


def test_alias_publication_actual_reopen_retry_and_copied_path_denial(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    durable = (runtime.stores.revision_pin(), runtime.stores.obligations.revision,
        runtime.stores.world.get(receipt.committed_fact_refs[0]),
        runtime.stores.r3_effect_journal_get(receipt.idempotency_key))
    verifier = gateway._review_verifier
    runtime.stores.close()
    runtime = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision,
            runtime.stores.world.get(receipt.committed_fact_refs[0]),
            runtime.stores.r3_effect_journal_get(receipt.idempotency_key)) == durable
        gateway = R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority, review_verifier=verifier)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        assert runtime.stores.learning_store_binding == str((tmp_path / "proposal.db" / "semantic.db").resolve())
        assert gateway.publish_learning(grant["proposal_key"], _signed(grant, secret)) == receipt
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()
    import shutil
    shutil.copytree(tmp_path / "proposal.db", tmp_path / "copied.db")
    copied = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "copied.db")
    try:
        with pytest.raises(PermissionError):
            R3EffectGateway(copied.stores, AdapterRegistry(), authority=copied.authority,
                review_verifier=verifier).publish_learning(grant["proposal_key"], _signed(grant, secret))
    finally:
        copied.stores.close()


@pytest.mark.parametrize("stage", ("world", "obligations", "effects"), ids=("after-fact", "after-completion", "after-journal"))
def test_alias_publication_sql_fault_rolls_back_all_then_restarts_once(tmp_path, monkeypatch, stage):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    stores = runtime.stores
    before = stores.revision_pin(), stores.obligations.revision, stores.obligations.get(pending.obligation_ref)
    real = persistence._r3_insert_revision
    writes = []
    def fault(conn, **kwargs):
        real(conn, **kwargs)
        if kwargs["store"] == stage and (stage != "effects" or kwargs["new_revision"] == before[0].effect_revision + 4):
            assert conn.execute("SELECT count(*) FROM world_facts").fetchone()[0] == 1
            writes.append(stage)
            raise RuntimeError("after real publication SQL write")
    with monkeypatch.context() as patch:
        patch.setattr(persistence, "_r3_insert_revision", fault)
        with pytest.raises(RuntimeError, match="after real publication SQL write"):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    assert writes == [stage]
    assert stores.world.revision == before[0].world_revision
    assert stores.obligations.revision == before[1]
    assert stores.obligations.get(pending.obligation_ref) == before[2]
    assert stores.sessions.revision == before[0].session_revision
    assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
    verifier = gateway._review_verifier
    stores.close()
    runtime = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        gateway = R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority, review_verifier=verifier)
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert receipt.input_revision_pin == before[0]
        assert runtime.stores.effects.revision == before[0].effect_revision + 4
        assert runtime.stores.world.revision == before[0].world_revision + 1
        assert gateway.publish_learning(grant["proposal_key"], _signed(grant, secret)) == receipt
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_alias_publication_separately_signed_conflicting_plans_cannot_both_commit(tmp_path, monkeypatch, backend):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    try:
        runtime.process("session:second", "What does velnora mean?")
        proposal2 = runtime.process("session:second", "learn velnora means likes")
        row2 = proposal2.response_meaning.obligation
        journal2 = runtime.stores.r3_effect_journal_get(proposal2.effect_receipt.idempotency_key)
        changed = {**grant, "proposal_key": proposal2.effect_receipt.idempotency_key,
            "proposal_journal_ref": journal2["entry"]["journal_ref"],
            "proposal_receipt_ref": proposal2.effect_receipt.receipt_ref,
            "plan_ref": proposal2.response_meaning.learning_plan.plan_ref,
            "source_obligation_ref": row2.obligation_ref, "source_query_ref": row2.source_query_ref,
            "source_journal_ref": journal2["entry"]["request_payload"]["learning_source_journal"]["entry"]["journal_ref"]}
        gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises((ValueError, PermissionError), match="conflicts"):
            gateway.publish_learning(changed["proposal_key"], _signed(changed, secret))
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_alias_publication_invalid_serialization_precedes_mutation(tmp_path, monkeypatch, backend):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    from cemm_authoritative_hybrid.r3_effects import EffectReceipt
    original = EffectReceipt.as_dict
    try:
        before = stores.revision_pin(), stores.obligations.revision, stores.obligations.get(pending.obligation_ref)
        with monkeypatch.context() as patch:
            patch.setattr(EffectReceipt, "as_dict", lambda self: {**original(self), "invalid": {1}})
            with pytest.raises((TypeError, ValueError)):
                gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert stores.world.revision == before[0].world_revision
        assert stores.sessions.revision == before[0].session_revision
        assert stores.obligations.revision == before[1]
        assert stores.obligations.get(pending.obligation_ref) == before[2]
        assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert receipt.input_revision_pin == before[0]
    finally:
        stores.close()


@pytest.mark.parametrize("field", ("world_revision", "session_revision", "episode_revision", "effect_revision", "obligation_revision"),
    ids=("world", "session", "episode", "effect", "obligation"))
def test_alias_publication_sql_peer_revision_race_blocks_commit(tmp_path, monkeypatch, field):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    stores = runtime.stores
    real = persistence.SemanticStores.r3_effect_journal_commit
    def race(self, **kwargs):
        peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation,
            model_identity=stores.revision_pin().model_identity)
        try:
            peer._backend._conn.execute("INSERT INTO metadata(key,value) VALUES(?, '1') "
                "ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1", (field,))
            peer._backend._conn.commit()
        finally:
            peer.close()
        return real(self, **kwargs)
    try:
        before = stores.revision_pin(), stores.obligations.get(pending.obligation_ref)
        monkeypatch.setattr(persistence.SemanticStores, "r3_effect_journal_commit", race)
        with pytest.raises(persistence.StaleRevisionError):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert stores.obligations.get(pending.obligation_ref) == before[1]
        assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
        assert stores.r3_session_snapshot(pending.session_ref)["turn_index"] == 2
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_alias_publication_bounded_relevant_reader_uses_index(tmp_path, monkeypatch, backend):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        irrelevant = tuple(persistence.Fact(fact_ref=f"fact:irrelevant:{i}", operator="op:designation",
            args={"role:surface": f"unrelated-{i}", "role:target": "rel:likes"},
            stance="support", confidence=1.0, derived=False, proof={"alias_language": "en"}) for i in range(3000))
        stores.world.commit(irrelevant, expected_revision=stores.world.revision)
        if backend == "sqlite":
            plan = stores._backend._conn.execute("EXPLAIN QUERY PLAN SELECT fact_ref FROM world_facts "
                "WHERE operator='op:designation' AND json_extract(args_json, '$.\"role:surface\"')=? "
                "AND json_extract(proof_json, '$.alias_language')=? ORDER BY fact_ref LIMIT ?", ("velnora", "en", 9)).fetchall()
            assert any("SEARCH" in str(row[3]) and "world_designation_surface_language" in str(row[3]) for row in plan)
        monkeypatch.setattr(persistence.SemanticStores, "r3_world_facts", lambda *a: pytest.fail("whole world scan"))
        gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert len(stores.r3_alias_facts("velnora", "en", maximum=8)) == 1
        extras = tuple(replace(irrelevant[0], fact_ref=f"fact:collision:{i}",
            args={**irrelevant[0].args, "role:surface": "velnora"}) for i in range(9))
        stores.world.commit(extras, expected_revision=stores.world.revision)
        with pytest.raises(ValueError, match="exceeds bound"):
            stores.r3_alias_facts("velnora", "en", maximum=8)
    finally:
        stores.close()


def test_alias_publication_memory_requires_explicit_trusted_binding(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    try:
        unbound = R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority,
            review_verifier=gateway._review_verifier)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(PermissionError, match="trusted binding"):
            unbound.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


def test_alias_publication_linked_designation_conflict_is_not_world_admission(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    try:
        from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
        # A controlled linked-index conflict after the proposal was recorded.
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex((
            DesignationFact.create(surface="velnora", target_ref="rel:likes", language="en"),)))
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(ValueError, match="linked designation"):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
        assert runtime.stores.r3_alias_facts("velnora", "en", maximum=8) == ()
    finally:
        runtime.stores.close()


def test_alias_publication_captures_verified_review_bytes_and_never_secret(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    signed = _signed(grant, secret)
    original = r3_learning.publication_lineage
    def mutate_caller(*args):
        signed["grant"]["language"] = "fr"
        signed["grant"]["target_ref"] = "rel:forged"
        return original(*args)
    try:
        monkeypatch.setattr(r3_learning, "publication_lineage", mutate_caller)
        receipt = gateway.publish_learning(proposal.effect_receipt.idempotency_key, signed)
        journal = runtime.stores.r3_effect_journal_get(receipt.idempotency_key)
        retained = journal["entry"]["request_payload"]["review"]["grant"]
        assert retained["language"] == "en" and retained["target_ref"] == "rel:likes"
        assert secret.hex() not in json.dumps(journal)
        fact = runtime.stores.world.get(receipt.committed_fact_refs[0])
        assert fact.args["role:target"] == "rel:likes" and fact.proof["alias_language"] == "en"
    finally:
        runtime.stores.close()


def test_alias_publication_fresh_grant_cannot_reuse_foreign_model_meaning(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    try:
        runtime.stores._backend._model_identity = "model:changed"
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(ValueError, match="model"):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


def test_alias_publication_locator_does_not_reinterpret_arbitrary_world_roles(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    try:
        raw = persistence.Fact(fact_ref="fact:structured-evidence", operator="op:designation",
            args={"role:surface": {"literal": "unrelated"}}, stance="support", confidence=1.0,
            derived=False, proof={})
        runtime.stores.world.commit((raw,), expected_revision=runtime.stores.world.revision)
        assert runtime.stores.world.get(raw.fact_ref) == raw
        assert runtime.stores.r3_alias_facts("velnora", "en", maximum=8) == ()
    finally:
        runtime.stores.close()


def test_alias_publication_can_publish_later_without_repinning_answer(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    try:
        original = runtime.stores.r3_effect_journal_get(grant["proposal_key"])
        runtime.process(pending.session_ref, "What does velnora mean?")
        before = runtime.stores.revision_pin()
        assert runtime.stores.r3_session_snapshot(pending.session_ref)["turn_index"] == 3
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert receipt.input_revision_pin == before
        assert receipt.situation_ref == proposal.effect_receipt.situation_ref
        assert runtime.stores.r3_effect_journal_get(grant["proposal_key"]) == original
        assert runtime.stores.r3_session_snapshot(pending.session_ref)["turn_index"] == 3
        assert runtime.stores.sessions.revision == before.session_revision
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("state", ("planned", "observed"), ids=("planned", "observed"))
def test_alias_publication_unfinished_retry_never_repins_changed_snapshot(tmp_path, monkeypatch, state):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    try:
        with monkeypatch.context() as patch:
            owner = "r3_effect_journal_transition" if state == "planned" else "r3_effect_journal_commit"
            patch.setattr(persistence.SemanticStores, owner,
                lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("paused publication")))
            with pytest.raises(RuntimeError, match="paused publication"):
                gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        runtime.stores.world.commit((), expected_revision=runtime.stores.world.revision)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(persistence.StaleRevisionError, match="snapshot revision"):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
        assert runtime.stores.r3_alias_facts("velnora", "en", maximum=8) == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("state", ("planned", "authorized"), ids=("planned", "authorized"))
def test_alias_publication_reserved_snapshot_recovers_after_reopen(tmp_path, monkeypatch, state):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
    verifier = gateway._review_verifier
    real = persistence.SemanticStores.r3_effect_journal_transition
    def pause(self, **kwargs):
        if kwargs["expected_state"] == state:
            raise RuntimeError("paused reserved publication")
        return real(self, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(persistence.SemanticStores, "r3_effect_journal_transition", pause)
        with pytest.raises(RuntimeError, match="paused reserved publication"):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    paused = runtime.stores.revision_pin()
    runtime.stores.close()
    runtime = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        assert runtime.stores.revision_pin() == paused
        gateway = R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority, review_verifier=verifier)
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert receipt.input_revision_pin == before[0]
        assert receipt.situation_ref == proposal.effect_receipt.situation_ref
        assert runtime.stores.effects.revision == before[0].effect_revision + 4
        assert runtime.stores.world.revision == before[0].world_revision + 1
        assert runtime.stores.obligations.revision == before[1] + 1
        assert runtime.stores.sessions.revision == before[0].session_revision
        assert runtime.stores.r3_session_snapshot(pending.session_ref)["turn_index"] == 2
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend,field", (
    ("memory", "decision_ref"), ("sqlite", "decision_ref"),
    ("memory", "idempotency_key"), ("sqlite", "journal_origin_ref"),
    ("memory", "verified_meaning_ref"), ("sqlite", "expression_ref"),
    ("memory", "situation_ref"), ("sqlite", "program_ref"),
    ("memory", "actor_ref"), ("sqlite", "event_type_ref"),
    ("memory", "effect_intent_ref"), ("sqlite", "transition_ref"),
    ("memory", "adapter_ref"), ("sqlite", "adapter_result_ref"),
    ("memory", "proof_refs"), ("sqlite", "proof_refs")),
    ids=("memory-decision", "sqlite-decision", "memory-key", "sqlite-origin", "memory-meaning", "sqlite-expression",
        "memory-situation", "sqlite-program", "memory-actor", "sqlite-event", "memory-intent", "sqlite-transition",
        "memory-adapter", "sqlite-adapter-result", "memory-proof", "sqlite-proof"))
def test_alias_publication_commit_port_rejects_canonical_foreign_receipt(tmp_path, monkeypatch, backend, field):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    from cemm_authoritative_hybrid.r3_effects import EffectReceipt
    real = persistence.SemanticStores.r3_effect_journal_commit
    intercepted = []
    def forge(self, **kwargs):
        receipt = EffectReceipt.from_dict(kwargs["receipt_payload"])
        values = {name: getattr(receipt, name) for name in receipt._FIELDS - {"abi_version", "receipt_ref"}}
        values[field] = (*receipt.proof_refs, "proof:unrelated") if field == "proof_refs" else "ref:unrelated"
        forged = EffectReceipt.create(**values)
        intercepted.append(forged)
        return real(self, **{**kwargs, "receipt_payload": forged.as_dict(), "outcome_ref": forged.receipt_ref})
    try:
        before = stores.revision_pin(), stores.obligations.revision, stores.obligations.get(pending.obligation_ref)
        with monkeypatch.context() as patch:
            patch.setattr(persistence.SemanticStores, "r3_effect_journal_commit", forge)
            with pytest.raises(ValueError, match="publication.*lineage"):
                gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert len(intercepted) == 1
        assert stores.world.revision == before[0].world_revision
        assert stores.obligations.revision == before[1]
        assert stores.obligations.get(pending.obligation_ref) == before[2]
        assert stores.sessions.revision == before[0].session_revision
        assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert receipt.decision_ref == proposal.effect_receipt.decision_ref
        assert receipt != intercepted[0]
        assert gateway.publish_learning(grant["proposal_key"], _signed(grant, secret)) == receipt
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_alias_publication_ports_reject_mutually_consistent_unreviewed_delta(tmp_path, monkeypatch, backend):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    from cemm_authoritative_hybrid.r3_effects import ObservedDelta, EffectReceipt, EffectStatus, _predicted_pin
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalState
    stores = runtime.stores
    real = persistence.SemanticStores.r3_effect_journal_transition
    captured = []
    def pause(self, **kwargs):
        if kwargs["next_state"] == "observed":
            captured.append(kwargs)
            raise RuntimeError("pause before observed")
        return real(self, **kwargs)
    try:
        before = stores.revision_pin(), stores.obligations.revision
        with monkeypatch.context() as patch:
            patch.setattr(persistence.SemanticStores, "r3_effect_journal_transition", pause)
            with pytest.raises(RuntimeError, match="pause before observed"):
                gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        values = captured[0]
        original = ObservedDelta.from_dict(values["observation_payload"]["observed_deltas"][0])
        delta = ObservedDelta.create(operator_ref=original.operator_ref, predicate_ref=original.predicate_ref,
            role_values=tuple((role, "rel:unreviewed" if role == "role:target" else value)
                for role, value in original.role_values), stance=original.stance, evidence_refs=original.evidence_refs)
        observation = {**values["observation_payload"], "observed_deltas": [delta.as_dict()]}
        with pytest.raises(ValueError, match="publication.*(lineage|observation)"):
            observed = real(stores, **{**values, "observation_payload": observation})
            request = observed["entry"]["request_payload"]
            fact = gateway._publication_fact(delta, decision_ref=proposal.effect_receipt.decision_ref,
                review=request["review"], publication_key=values["idempotency_key"])
            plan = proposal.response_meaning.learning_plan
            receipt = EffectReceipt.create(status=EffectStatus.COMMITTED,
                idempotency_key=values["idempotency_key"], journal_origin_ref=request["journal_origin_ref"],
                journal_preterminal_ref=observed["entry"]["journal_ref"], reconciliation_required=False,
                decision_ref=plan.decision_ref, verified_meaning_ref=plan.verified_meaning_ref,
                expression_ref=plan.expression_ref, situation_ref=plan.situation_ref,
                program_ref=proposal.effect_receipt.program_ref, effect_intent_ref=None,
                actor_ref="participant:system", event_type_ref="event:learn_alias", transition_ref=None,
                adapter_ref=None, adapter_result_ref=None, operation_receipt_ref=observation["operation_receipt_ref"],
                observed_delta_refs=(delta.observed_delta_ref,), committed_fact_refs=(fact.fact_ref,),
                proof_refs=proposal.effect_receipt.proof_refs + (pending.obligation_ref,), blocker_refs=(),
                input_revision_pin=before[0], output_revision_pin=_predicted_pin(stores.revision_pin(), world=1, effects=1))
            stores.r3_effect_journal_commit(idempotency_key=values["idempotency_key"],
                expected_state=EffectJournalState.OBSERVED.value, observation_payload=observation,
                outcome_ref=receipt.receipt_ref, receipt_payload=receipt.as_dict(), facts=(fact,),
                expected_revision_pin=stores.revision_pin())
        assert stores.world.revision == before[0].world_revision
        assert stores.obligations.revision == before[1]
        assert stores.obligations.get(pending.obligation_ref)["resolved"] is False
        assert stores.sessions.revision == before[0].session_revision
        assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
    finally:
        stores.close()


def test_alias_publication_same_plan_two_connections_commit_once(tmp_path, monkeypatch):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    stores = runtime.stores
    original_commit = persistence.SemanticStores.r3_effect_journal_commit
    peer_receipts = []
    def race(self, **kwargs):
        peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation,
            model_identity=stores.revision_pin().model_identity)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(persistence.SemanticStores, "r3_effect_journal_commit", original_commit)
                peer_receipts.append(R3EffectGateway(peer, AdapterRegistry(), authority=runtime.authority,
                    review_verifier=gateway._review_verifier).publish_learning(grant["proposal_key"], _signed(grant, secret)))
        finally:
            peer.close()
        return original_commit(self, **kwargs)
    try:
        monkeypatch.setattr(persistence.SemanticStores, "r3_effect_journal_commit", race)
        with pytest.raises((ValueError, persistence.StaleRevisionError)):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert len(peer_receipts) == 1
        assert len(stores.r3_alias_facts("velnora", "en", maximum=8)) == 1
        assert gateway.publish_learning(grant["proposal_key"], _signed(grant, secret)) == peer_receipts[0]
        assert stores.r3_session_snapshot(pending.session_ref)["turn_index"] == 2
    finally:
        stores.close()


@pytest.mark.parametrize("target", ("parent", "proposal", "source"), ids=("parent", "proposal", "source"))
def test_alias_publication_locked_commit_rechecks_rehashed_journals(tmp_path, monkeypatch, target):
    runtime, _, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    stores = runtime.stores
    real_commit = persistence.SemanticStores.r3_effect_journal_commit
    real_verify = persistence._r3_verify_journal_row
    changed = []
    def race(self, **kwargs):
        publication_key = kwargs["idempotency_key"]
        def after_read(*args):
            result = real_verify(*args)
            if not changed and result["entry"]["idempotency_key"] == publication_key:
                changed.append(True)
                peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation,
                    model_identity=stores.revision_pin().model_identity)
                try:
                    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry, EffectJournalState
                    key = publication_key if target == "parent" else grant["proposal_key"] if target == "proposal" else (
                        stores.r3_effect_journal_get(grant["proposal_key"])["entry"]["request_payload"]["learning_source_key"])
                    journal = peer.r3_effect_journal_get(key)
                    values = {k: v for k, v in journal["entry"].items() if k not in {"abi_version", "journal_ref"}}
                    values["state"] = EffectJournalState(values["state"])
                    values["blocker_refs"] = tuple(values["blocker_refs"])
                    values["request_payload"] = {**values["request_payload"], "tampered": "proof:changed"}
                    entry = EffectJournalEntry.create(**values).as_dict()
                    peer._backend._conn.execute("UPDATE r3_effect_journal SET entry_json=?,entry_hash=? WHERE idempotency_key=?",
                        (persistence._r3_canonical_json(entry), persistence._payload_hash(entry), key))
                    peer._backend._conn.commit()
                finally:
                    peer.close()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(persistence, "_r3_verify_journal_row", after_read)
            return real_commit(self, **kwargs)
    try:
        monkeypatch.setattr(persistence.SemanticStores, "r3_effect_journal_commit", race)
        with pytest.raises((ValueError, persistence.StaleRevisionError), match="changed"):
            gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert changed == [True]
        assert stores.r3_alias_facts("velnora", "en", maximum=8) == ()
        assert stores.obligations.get(pending.obligation_ref)["resolved"] is False
        assert stores.r3_session_snapshot(pending.session_ref)["turn_index"] == 2
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_alias_publication_signed_success_preserves_turn_and_lineage(tmp_path, monkeypatch, backend):
    assert hasattr(r3_learning, "AliasReviewVerifier"), "missing independently configured verifier"
    runtime, source, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    try:
        stores = runtime.stores
        before = stores.revision_pin(), stores.obligations.revision, stores.r3_session_snapshot(pending.session_ref)
        original = stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key)
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert receipt.status.value == "committed"
        assert stores.world.revision == before[0].world_revision + 1
        assert stores.obligations.revision == before[1] + 1
        assert stores.sessions.revision == before[0].session_revision
        assert stores.episodes.revision == before[0].episode_revision
        assert stores.r3_session_snapshot(pending.session_ref) == before[2]
        assert stores.r3_effect_journal_get(grant["proposal_key"]) == original
        assert receipt.verified_meaning_ref == proposal.effect_receipt.verified_meaning_ref
        assert receipt.program_ref == proposal.effect_receipt.program_ref
        assert receipt.situation_ref == proposal.effect_receipt.situation_ref
        assert receipt.input_revision_pin == before[0]
        assert len(receipt.committed_fact_refs) == 1
        fact = stores.world.get(receipt.committed_fact_refs[0])
        assert fact.operator == "op:designation"
        assert fact.args["role:surface"] == "velnora" and fact.args["role:target"] == "rel:likes"
        assert "role:language" not in fact.args
        assert fact.proof["alias_language"] == "en"
        assert fact.proof["source"] == receipt.operation_receipt_ref
        assert pending.obligation_ref in receipt.proof_refs
        assert stores.obligations.get(pending.obligation_ref)["resolved"] is True
        from cemm_authoritative_hybrid.dialogue import DialogueObligation
        completed = DialogueObligation.create(**{**{k: v for k, v in pending.as_dict().items()
            if k not in {"abi_version", "obligation_ref", "revision_pin", "kind"}},
            "kind": pending.kind, "revision_pin": pending.revision_pin,
            "completion_receipt_ref": receipt.receipt_ref})
        assert stores.obligations.get(completed.obligation_ref) == {**completed.as_dict(), "resolved": True}
        final = stores.revision_pin(), stores.obligations.revision
        assert gateway.publish_learning(grant["proposal_key"], _signed(grant, secret)) == receipt
        changed = {**grant, "nonce": secrets.token_hex(24)}
        with pytest.raises(ValueError):
            gateway.publish_learning(grant["proposal_key"], _signed(changed, secret))
        assert (stores.revision_pin(), stores.obligations.revision) == final
    finally:
        runtime.stores.close()
