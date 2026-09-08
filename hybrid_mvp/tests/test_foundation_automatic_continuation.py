"""Automatic generic query continuity, independent of alias publication."""
from pathlib import Path
from dataclasses import fields
import sqlite3

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.dialogue import DialogueObligation, ObligationKind
from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, NoEffectReason, R3EffectGateway
from cemm_authoritative_hybrid.r3_persistence import effect_journal_get
from cemm_authoritative_hybrid.r3_codec import thaw_json
from cemm_authoritative_hybrid.persistence import StaleRevisionError, memory_stores

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_automatic_continuation.py::test_automatic_continuation_exact_answer_window[source-turn]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-automatic-continuation-exact-answer-window-source-turn",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "62fe1b3c1842ecab32af8e72bd67141b7d1382720e04ef8c82c924ebb768ae31"
    },
    "tests/test_foundation_automatic_continuation.py::test_automatic_continuation_exact_answer_window[next-one]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-automatic-continuation-exact-answer-window-next-one",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "62fe1b3c1842ecab32af8e72bd67141b7d1382720e04ef8c82c924ebb768ae31"
    },
    "tests/test_foundation_automatic_continuation.py::test_automatic_continuation_exact_answer_window[next-two]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-automatic-continuation-exact-answer-window-next-two",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "62fe1b3c1842ecab32af8e72bd67141b7d1382720e04ef8c82c924ebb768ae31"
    },
    "tests/test_foundation_automatic_continuation.py::test_automatic_continuation_exact_answer_window[next-three]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-automatic-continuation-exact-answer-window-next-three",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "62fe1b3c1842ecab32af8e72bd67141b7d1382720e04ef8c82c924ebb768ae31"
    },
    "tests/test_foundation_automatic_continuation.py::test_automatic_continuation_exact_answer_window[next-four]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-automatic-continuation-exact-answer-window-next-four",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "62fe1b3c1842ecab32af8e72bd67141b7d1382720e04ef8c82c924ebb768ae31"
    },
    "tests/test_foundation_automatic_continuation.py::test_automatic_continuation_exact_answer_window[exclusive-expiry]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-automatic-continuation-exact-answer-window-exclusive-expiry",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "62fe1b3c1842ecab32af8e72bd67141b7d1382720e04ef8c82c924ebb768ae31"
    },
    "tests/test_foundation_automatic_continuation.py::test_rehashed_extended_deadline_cannot_bind_original_query": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-rehashed-extended-deadline-cannot-bind-original-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "0cf50647942524956baf94f38c4e83521596a9e9d2c3b643d1aff0a24691c526"
    },
    "tests/test_foundation_automatic_continuation.py::test_replacement_failure_preserves_expired_row_and_planned_journal[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-replacement-failure-preserves-expired-row-and-planned-journal-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2b872eb6e12d07489feb9cfed0d08476c5707b3edf684f3ad06d86af80ba7f3c"
    },
    "tests/test_foundation_automatic_continuation.py::test_replacement_failure_preserves_expired_row_and_planned_journal[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-replacement-failure-preserves-expired-row-and-planned-journal-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2b872eb6e12d07489feb9cfed0d08476c5707b3edf684f3ad06d86af80ba7f3c"
    },
    "tests/test_foundation_automatic_continuation.py::test_sqlite_transition_rechecks_database_under_transaction[other-connection-obligation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-sqlite-transition-rechecks-database-under-transaction-other-connection-obligation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5c1a378b04c75b7c8ddd37a23e23c0099a860d1056bfb38ef748ff7e69fc7695"
    },
    "tests/test_foundation_automatic_continuation.py::test_sqlite_transition_rechecks_database_under_transaction[other-connection-effect]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-sqlite-transition-rechecks-database-under-transaction-other-connection-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5c1a378b04c75b7c8ddd37a23e23c0099a860d1056bfb38ef748ff7e69fc7695"
    },
    "tests/test_foundation_automatic_continuation.py::test_sqlite_transition_rechecks_database_under_transaction[journal-parent]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-sqlite-transition-rechecks-database-under-transaction-journal-parent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5c1a378b04c75b7c8ddd37a23e23c0099a860d1056bfb38ef748ff7e69fc7695"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_transaction_rejects_increased_journal_bound[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-transaction-rejects-increased-journal-bound-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "ccd0d858b1f2d47a36fb7d2b1a10e0f4717efaf0c1079900b201f05d64108e45"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_transaction_rejects_increased_journal_bound[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-transaction-rejects-increased-journal-bound-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "ccd0d858b1f2d47a36fb7d2b1a10e0f4717efaf0c1079900b201f05d64108e45"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_journal_cannot_drop_required_continuation_before_terminal[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-journal-cannot-drop-required-continuation-before-terminal-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "a16a42d200861782fd353e802a99b50d260fbffa113eaa27ccc8e9b609d60009"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_journal_cannot_drop_required_continuation_before_terminal[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-journal-cannot-drop-required-continuation-before-terminal-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "a16a42d200861782fd353e802a99b50d260fbffa113eaa27ccc8e9b609d60009"
    },
    "tests/test_foundation_automatic_continuation.py::test_oriented_obligation_snapshot_cannot_be_replaced_before_planning[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-oriented-obligation-snapshot-cannot-be-replaced-before-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "78dbfbacb2211e4297d165cb0083888b9e1fba5ec72d2bebb55a583e767bd4cb"
    },
    "tests/test_foundation_automatic_continuation.py::test_oriented_obligation_snapshot_cannot_be_replaced_before_planning[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-oriented-obligation-snapshot-cannot-be-replaced-before-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "78dbfbacb2211e4297d165cb0083888b9e1fba5ec72d2bebb55a583e767bd4cb"
    },
    "tests/test_foundation_automatic_continuation.py::test_changed_world_cannot_create_an_unbindable_query_continuation[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-changed-world-cannot-create-an-unbindable-query-continuation-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "c1b306449f28d73f2750d2bbae5fdaa156c97723481eb05d8bd12804c1daa8ea"
    },
    "tests/test_foundation_automatic_continuation.py::test_changed_world_cannot_create_an_unbindable_query_continuation[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-changed-world-cannot-create-an-unbindable-query-continuation-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "c1b306449f28d73f2750d2bbae5fdaa156c97723481eb05d8bd12804c1daa8ea"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_eligibility_is_exact_expression_structure[target-slot]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-eligibility-is-exact-expression-structure-target-slot",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fe8f0bd4311f0d4ee1342a310d232c819c407bfb3de95bb69b079ff06e0e7e5c"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_eligibility_is_exact_expression_structure[surface-slot]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-eligibility-is-exact-expression-structure-surface-slot",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fe8f0bd4311f0d4ee1342a310d232c819c407bfb3de95bb69b079ff06e0e7e5c"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_eligibility_is_exact_expression_structure[nonlexical-label]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-eligibility-is-exact-expression-structure-nonlexical-label",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fe8f0bd4311f0d4ee1342a310d232c819c407bfb3de95bb69b079ff06e0e7e5c"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_eligibility_is_exact_expression_structure[scoped-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-eligibility-is-exact-expression-structure-scoped-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fe8f0bd4311f0d4ee1342a310d232c819c407bfb3de95bb69b079ff06e0e7e5c"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_eligibility_is_exact_expression_structure[linked-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-eligibility-is-exact-expression-structure-linked-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fe8f0bd4311f0d4ee1342a310d232c819c407bfb3de95bb69b079ff06e0e7e5c"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_eligibility_is_exact_expression_structure[critical-residual]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-eligibility-is-exact-expression-structure-critical-residual",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fe8f0bd4311f0d4ee1342a310d232c819c407bfb3de95bb69b079ff06e0e7e5c"
    },
    "tests/test_foundation_automatic_continuation.py::test_other_session_queries_do_not_age_or_replace_continuation": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-other-session-queries-do-not-age-or-replace-continuation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "cce64c82b5ed6082ebdd1cdc6462e79d6c6abd141cbca8e5da0f98a1a982345d"
    },
    "tests/test_foundation_automatic_continuation.py::test_corrupt_pending_row_blocks_creation_without_partial_terminal[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-corrupt-pending-row-blocks-creation-without-partial-terminal-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1e4d4f0100b6f04bd13ca7188f8a8d34ddc20b57fa876a497c5b6d31475ddb26"
    },
    "tests/test_foundation_automatic_continuation.py::test_corrupt_pending_row_blocks_creation_without_partial_terminal[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-corrupt-pending-row-blocks-creation-without-partial-terminal-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1e4d4f0100b6f04bd13ca7188f8a8d34ddc20b57fa876a497c5b6d31475ddb26"
    },
    "tests/test_foundation_automatic_continuation.py::test_planned_query_survives_rollback_restart_and_exact_retry": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-planned-query-survives-rollback-restart-and-exact-retry",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fcb5336efd92c2674d0816d3ab0a285cc2fcf44a35e02b8ab203d16fdc57121e"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_creation_respects_full_pending_snapshot[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-creation-respects-full-pending-snapshot-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2ebaf5dea71c08f25f28f607def763d8f34954a6aaa2fc46a456bb2eb455da3b"
    },
    "tests/test_foundation_automatic_continuation.py::test_continuation_creation_respects_full_pending_snapshot[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-continuation-creation-respects-full-pending-snapshot-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2ebaf5dea71c08f25f28f607def763d8f34954a6aaa2fc46a456bb2eb455da3b"
    },
    "tests/test_foundation_automatic_continuation.py::test_live_continuation_is_preserved_and_expired_history_replaced[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-live-continuation-is-preserved-and-expired-history-replaced-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "cf53d406649df682a2395605569e4e2ab8e2ca78e6c95d87d39de8b5aea1c082"
    },
    "tests/test_foundation_automatic_continuation.py::test_live_continuation_is_preserved_and_expired_history_replaced[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-live-continuation-is-preserved-and-expired-history-replaced-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "cf53d406649df682a2395605569e4e2ab8e2ca78e6c95d87d39de8b5aea1c082"
    },
    "tests/test_foundation_automatic_continuation.py::test_pending_snapshot_race_blocks_terminal_continuation_write[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-snapshot-race-blocks-terminal-continuation-write-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b9d658081676e03de59127ccfa3991fe627451193da89616b68a536f83d0547f"
    },
    "tests/test_foundation_automatic_continuation.py::test_pending_snapshot_race_blocks_terminal_continuation_write[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-snapshot-race-blocks-terminal-continuation-write-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b9d658081676e03de59127ccfa3991fe627451193da89616b68a536f83d0547f"
    },
    "tests/test_foundation_automatic_continuation.py::test_public_unknown_creates_exact_generic_continuation_and_retry[same-process]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-public-unknown-creates-exact-generic-continuation-and-retry-same-process",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8eb1800083d2b5f63ec4c94a1c8a2116d43746838adf3d4563a1cfa49774b33f"
    },
    "tests/test_foundation_automatic_continuation.py::test_public_unknown_creates_exact_generic_continuation_and_retry[restart]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-public-unknown-creates-exact-generic-continuation-and-retry-restart",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8eb1800083d2b5f63ec4c94a1c8a2116d43746838adf3d4563a1cfa49774b33f"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-same-session-before-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-same-session-before-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-same-session-before-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-same-session-before-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-same-session-after-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-same-session-after-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-same-session-after-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-same-session-after-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-foreign-session-before-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-foreign-session-before-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-foreign-session-before-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-foreign-session-before-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-foreign-session-after-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-foreign-session-after-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[same-turn-duplicate-foreign-session-after-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-same-turn-duplicate-foreign-session-after-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-same-session-before-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-same-session-before-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-same-session-before-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-same-session-before-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-same-session-after-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-same-session-after-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-same-session-after-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-same-session-after-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-foreign-session-before-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-foreign-session-before-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-foreign-session-before-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-foreign-session-before-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-foreign-session-after-planning-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-foreign-session-after-planning-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_query_continuation_rechecks_source_session_reservation[four-turn-rewind-foreign-session-after-planning-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-continuation-rechecks-source-session-reservation-four-turn-rewind-foreign-session-after-planning-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8aebc4c7e784ea3b33008eda7f78162732baae08add55626597f2a74b2c53490"
    },
    "tests/test_foundation_automatic_continuation.py::test_sqlite_pending_snapshot_work_ignores_irrelevant_history[foreign-pending]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-sqlite-pending-snapshot-work-ignores-irrelevant-history-foreign-pending",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "07d4497e7266da3ba0d8ea6a8a08b5b225b350acd0bfaeb0b47b550ae802b3c3"
    },
    "tests/test_foundation_automatic_continuation.py::test_sqlite_pending_snapshot_work_ignores_irrelevant_history[same-session-resolved]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-sqlite-pending-snapshot-work-ignores-irrelevant-history-same-session-resolved",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "07d4497e7266da3ba0d8ea6a8a08b5b225b350acd0bfaeb0b47b550ae802b3c3"
    },
    "tests/test_foundation_automatic_continuation.py::test_reopen_adds_pending_session_index_without_changing_records": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-reopen-adds-pending-session-index-without-changing-records",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d29877719406bae3ab21ca82dd8d45649216d479562cad2f229cca2418e41f86"
    }
}


def _runtime(tmp_path, monkeypatch, backend):
    if backend == "memory":
        monkeypatch.setattr("cemm_authoritative_hybrid.bootstrap.open_stores", lambda _path, **kwargs: memory_stores(**kwargs))
    return load_runtime(ROOT, profile="development", store_path=tmp_path / "automatic.db")


@pytest.mark.parametrize("turn,eligible", ((1, False), (2, True), (3, True), (4, True), (5, True), (6, False)),
                         ids=("source-turn", "next-one", "next-two", "next-three", "next-four", "exclusive-expiry"))
def test_automatic_continuation_exact_answer_window(tmp_path, turn, eligible):
    from tests.test_foundation_continuation_binding import _setup, _answer
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    runtime, source, pending = _setup(tmp_path)
    try:
        meaning, situation = _answer(runtime, source.evaluation.situation, turn_index=turn)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        result = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert bool(result.learning_drafts) is eligible
        if eligible:
            assert result.learning_drafts[0].source_query_ref == pending.source_query_ref
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


def test_rehashed_extended_deadline_cannot_bind_original_query(tmp_path):
    from tests.test_foundation_continuation_binding import _setup, _answer
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    runtime, source, pending = _setup(tmp_path)
    try:
        values = {field.name: getattr(pending, field.name) for field in fields(pending) if field.name != "obligation_ref"}
        extended = DialogueObligation.create(**{**values, "expires_turn_index": 100})
        runtime.stores.obligations.commit(pending.obligation_ref, pending.session_ref, pending.as_dict(),
            expected_revision=runtime.stores.obligations.revision, resolved=True)
        runtime.stores.obligations.commit(extended.obligation_ref, extended.session_ref, extended.as_dict(),
            expected_revision=runtime.stores.obligations.revision)
        meaning, situation = _answer(runtime, source.evaluation.situation)
        result = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert result.learning_drafts == ()
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_replacement_failure_preserves_expired_row_and_planned_journal(tmp_path, monkeypatch, backend):
    import cemm_authoritative_hybrid.persistence as persistence
    runtime = _runtime(tmp_path, monkeypatch, backend)
    try:
        runtime.process("session:rollback", "What does velnora mean?")
        first_ref = runtime.stores.r3_obligation_snapshot("session:rollback", maximum=1)["obligation_refs"][0]
        for _ in range(4):
            runtime.process("session:rollback", "What does mother mean?")
        first = runtime.stores.obligations.keyed_row(first_ref)
        import cemm_authoritative_hybrid.r3_effects as effects
        transition = effects.effect_journal_transition
        captured = {}
        def capture(stores, **kwargs):
            captured["before"] = stores.revision_pin(), stores.obligations.revision
            captured["key"] = kwargs["idempotency_key"]
            return transition(stores, **kwargs)
        monkeypatch.setattr(effects, "effect_journal_transition", capture)
        if backend == "memory":
            prepare = persistence._MemoryObligationStore._prepare_row
            def fail_new(ref, session, payload, revision, resolved):
                if not resolved:
                    raise ValueError("injected preparation failure")
                return prepare(ref, session, payload, revision, resolved)
            monkeypatch.setattr(persistence._MemoryObligationStore, "_prepare_row", staticmethod(fail_new))
        else:
            conn = runtime.stores._backend._conn
            conn.execute("CREATE TEMP TRIGGER fail_new_continuation BEFORE INSERT ON obligations BEGIN SELECT RAISE(ABORT, 'injected obligation failure'); END")
        with pytest.raises((ValueError, sqlite3.IntegrityError), match="injected"):
            runtime.process("session:rollback", "What does zorbulate mean?")
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == captured["before"]
        assert runtime.stores.obligations.keyed_row(first_ref) == first
        assert runtime.stores.r3_obligation_snapshot("session:rollback", maximum=1)["obligation_refs"] == [first_ref]
        journal = effect_journal_get(runtime.stores, captured["key"])
        assert journal.entry.state.value == "planned" and journal.receipt_payload is None
        assert runtime.stores.world.revision == runtime.stores.episodes.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("race", ("obligation", "effect", "journal"), ids=("other-connection-obligation", "other-connection-effect", "journal-parent"))
def test_sqlite_transition_rechecks_database_under_transaction(tmp_path, monkeypatch, race):
    import json
    import cemm_authoritative_hybrid.r3_effects as effects
    from cemm_authoritative_hybrid.persistence import open_stores, _payload_hash
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry
    runtime = _runtime(tmp_path, monkeypatch, "sqlite")
    transition = effects.effect_journal_transition
    captured = {}
    def interleave(stores, **kwargs):
        key = kwargs["idempotency_key"]
        captured["before"] = stores.revision_pin(), stores.obligations.revision
        captured["key"] = key
        pin = stores.revision_pin()
        other = open_stores(tmp_path / "automatic.db", authority_generation=pin.authority_generation, model_identity=pin.model_identity)
        try:
            if race == "obligation":
                other.obligations.commit("obligation:other", "session:foreign", {}, expected_revision=other.obligations.revision)
            elif race == "effect":
                other.r3_effect_journal_begin(idempotency_key="key:other", intent_ref="intent:other", decision_ref="decision:other",
                    request_payload={"session_ref": "session:foreign"}, expected_effect_revision=other.effects.revision)
            else:
                original_get = stores.r3_effect_journal_get
                def swapped(request_key):
                    row = original_get(request_key)
                    entry = EffectJournalEntry.from_dict(row["entry"])
                    values = {field.name: getattr(entry, field.name) for field in fields(entry) if field.name not in {"abi_version", "journal_ref"}}
                    changed = EffectJournalEntry.create(**{**values, "intent_ref": "intent:forged"}).as_dict()
                    other._backend._conn.execute("UPDATE r3_effect_journal SET entry_json=?, entry_hash=? WHERE idempotency_key=?",
                        (json.dumps(changed), _payload_hash(changed), request_key))
                    other._backend._conn.commit()
                    monkeypatch.setattr(stores, "r3_effect_journal_get", original_get)
                    return row
                monkeypatch.setattr(stores, "r3_effect_journal_get", swapped)
            return transition(stores, **kwargs)
        finally:
            other.close()
    monkeypatch.setattr(effects, "effect_journal_transition", interleave)
    try:
        with pytest.raises(StaleRevisionError, match="concurrently"):
            runtime.process("session:race", "What does velnora mean?")
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == captured["before"]
        journal = effect_journal_get(runtime.stores, captured["key"])
        assert journal.entry.state.value == "planned" and journal.receipt_payload is None
        assert runtime.stores.r3_obligation_snapshot("session:race", maximum=1)["obligation_refs"] == []
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_continuation_transaction_rejects_increased_journal_bound(tmp_path, monkeypatch, backend):
    runtime = _runtime(tmp_path, monkeypatch, backend)
    begin = R3EffectGateway._begin
    def forged(gateway, **kwargs):
        kwargs["request_payload"] = {**kwargs["request_payload"], "query_obligation_maximum": 17}
        return begin(gateway, **kwargs)
    monkeypatch.setattr(R3EffectGateway, "_begin", forged)
    try:
        assert runtime._owners["r3"]._effects._config is runtime._config
        with pytest.raises(ValueError, match="maximum|bound"):
            runtime.process("session:bound", "What does velnora mean?")
        assert runtime.stores.obligations.revision == 0
        assert runtime.stores.world.revision == runtime.stores.episodes.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_query_journal_cannot_drop_required_continuation_before_terminal(tmp_path, monkeypatch, backend):
    runtime = _runtime(tmp_path, monkeypatch, backend)
    begin = R3EffectGateway._begin
    def forged(gateway, **kwargs):
        kwargs["request_payload"] = {name: value for name, value in kwargs["request_payload"].items()
                                     if name != "query_continuation"}
        return begin(gateway, **kwargs)
    monkeypatch.setattr(R3EffectGateway, "_begin", forged)
    try:
        with pytest.raises(ValueError, match="continuation"):
            runtime.process("session:removed", "What does velnora mean?")
        assert runtime.stores.obligations.revision == 0
        assert runtime.stores.effects.revision == 1
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_oriented_obligation_snapshot_cannot_be_replaced_before_planning(tmp_path, monkeypatch, backend):
    runtime = _runtime(tmp_path, monkeypatch, backend)
    original = R3EffectGateway._persist_no_effect
    captured = {}
    def interleave(gateway, evaluation, meaning, situation, reason):
        row = DialogueObligation.create(kind=ObligationKind.CLARIFICATION, session_ref=situation.session_ref,
            source_query_ref="query:interleaved", expected_answer_contract_ref="contract:clarification",
            created_turn_index=0, expires_turn_index=50, source_decision_ref="decision:interleaved",
            completion_receipt_ref=None, revision_pin=gateway._stores.revision_pin())
        gateway._stores.obligations.commit(row.obligation_ref, row.session_ref, row.as_dict(),
            expected_revision=gateway._stores.obligations.revision)
        captured["before"] = gateway._stores.revision_pin(), gateway._stores.obligations.revision
        return original(gateway, evaluation, meaning, situation, reason)
    monkeypatch.setattr(R3EffectGateway, "_persist_no_effect", interleave)
    try:
        with pytest.raises(ValueError, match="snapshot"):
            runtime.process("session:oriented", "What does velnora mean?")
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == captured["before"]
        assert runtime.stores.effects.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_changed_world_cannot_create_an_unbindable_query_continuation(tmp_path, monkeypatch, backend):
    from cemm_authoritative_hybrid.persistence import Fact
    runtime = _runtime(tmp_path, monkeypatch, backend)
    original = R3EffectGateway._persist_no_effect
    def interleave(gateway, evaluation, meaning, situation, reason):
        gateway._stores.world.commit((Fact("fact:other", "op:type", {"role:subject": "entity:alice", "role:type": "concept:person"}),),
            expected_revision=gateway._stores.world.revision)
        return original(gateway, evaluation, meaning, situation, reason)
    monkeypatch.setattr(R3EffectGateway, "_persist_no_effect", interleave)
    try:
        with pytest.raises(ValueError, match="revision"):
            runtime.process("session:changed-world", "What does velnora mean?")
        assert runtime.stores.obligations.revision == runtime.stores.effects.revision == 0
        assert runtime.stores.world.revision == 1
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("target", "surface", "nonlexical", "scope", "link", "critical"),
                         ids=("target-slot", "surface-slot", "nonlexical-label", "scoped-query", "linked-query", "critical-residual"))
def test_continuation_eligibility_is_exact_expression_structure(tmp_path, case):
    from cemm_authoritative_hybrid.dialogue import query_continuation
    from cemm_authoritative_hybrid.expressions import (BoundVariable, GroundedReference, LiteralValue,
        RoleBinding, SemanticApplication, SemanticExpression, VariableBinder, ScopeOperator, ExpressionLink,
        UnresolvedFiller, UnresolvedValue)
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    from tests.test_foundation_semantics import _matrix_meaning, _matrix_situation
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "structure.db")
    try:
        label = "label:personal_name" if case == "nonlexical" else "label:lexical"
        app = SemanticApplication("app:query", "op:designation", label, (
            RoleBinding("role:label_type", GroundedReference(label)),
            RoleBinding("role:surface", BoundVariable("?slot") if case == "surface" else LiteralValue("string", "velnora")),
            RoleBinding("role:target", GroundedReference("rel:likes") if case == "surface" else BoundVariable("?slot"))))
        apps, scopes, links, unresolved = (app,), (), (), ()
        body = app.application_ref
        if case == "scope":
            scopes = (ScopeOperator("scope:query", "scope:polarity", "polarity:negative", body),)
            body = scopes[0].scope_ref
        if case in {"link", "critical"}:
            other = SemanticApplication("app:other", "op:relation", "rel:likes", (
                RoleBinding("role:subject", GroundedReference("entity:alice")),
                RoleBinding("role:object", UnresolvedValue("unresolved:other") if case == "critical" else GroundedReference("entity:bob"))))
            apps += (other,)
            if case == "critical":
                unresolved = (UnresolvedFiller("unresolved:other", other.application_ref, "role:object", "anchor", ("entity",), True),)
            links = (ExpressionLink("link:query", "link:coordination", (body, other.application_ref)),)
            body = links[0].link_ref
        binder = VariableBinder("binder:query", "?slot", body)
        expression = SemanticExpression.create(applications=apps, root_refs=(binder.binder_ref,),
            binders=(binder,), scope_operators=scopes, expression_links=links, unresolved_fillers=unresolved)
        situation = _matrix_situation(runtime.stores)
        meaning = _matrix_meaning(expression, situation.revision_pin)
        evaluation = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        row = query_continuation(evaluation)
        assert (row is not None) is (case == "target")
        if row is not None:
            assert row.source_query_ref == evaluation.query_results[0].query_result_ref
        assert runtime.stores.obligations.revision == runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_other_session_queries_do_not_age_or_replace_continuation(tmp_path):
    from tests.test_foundation_continuation_binding import _setup, _answer
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    runtime, source, pending = _setup(tmp_path)
    try:
        original = runtime.stores.obligations.keyed_row(pending.obligation_ref)
        for _ in range(6):
            runtime.process("session:other", "What does zorbulate mean?")
        assert runtime.stores.obligations.keyed_row(pending.obligation_ref) == original
        assert runtime.stores.r3_obligation_snapshot(pending.session_ref, maximum=1)["obligation_refs"] == [pending.obligation_ref]
        meaning, situation = _answer(runtime, source.evaluation.situation)
        evaluation = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert evaluation.learning_drafts[0].source_query_ref == pending.source_query_ref
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_corrupt_pending_row_blocks_creation_without_partial_terminal(tmp_path, monkeypatch, backend):
    import json
    runtime = _runtime(tmp_path, monkeypatch, backend)
    try:
        runtime.process("session:corrupt", "What does velnora mean?")
        ref = runtime.stores.r3_obligation_snapshot("session:corrupt", maximum=1)["obligation_refs"][0]
        if backend == "memory":
            runtime.stores.obligations._obligations[ref]["expires_turn_index"] = 99
        else:
            payload = runtime.stores.obligations.get(ref)
            payload["expires_turn_index"] = 99
            runtime.stores._backend._conn.execute("UPDATE obligations SET payload_json=? WHERE obligation_ref=?", (json.dumps(payload), ref))
            runtime.stores._backend._conn.commit()
        effects, obligations = runtime.stores.effects.revision, runtime.stores.obligations.revision
        with pytest.raises(ValueError, match="hash"):
            runtime.process("session:corrupt", "What does zorbulate mean?")
        assert (runtime.stores.effects.revision, runtime.stores.obligations.revision) == (effects, obligations)
        assert runtime.stores.world.revision == runtime.stores.episodes.revision == 0
    finally:
        runtime.stores.close()


def test_planned_query_survives_rollback_restart_and_exact_retry(tmp_path, monkeypatch):
    runtime = _runtime(tmp_path, monkeypatch, "sqlite")
    original = R3EffectGateway._persist_no_effect
    captured = {}
    def capture(gateway, evaluation, meaning, situation, reason):
        captured.update(evaluation=evaluation, meaning=meaning, situation=situation)
        return original(gateway, evaluation, meaning, situation, reason)
    monkeypatch.setattr(R3EffectGateway, "_persist_no_effect", capture)
    try:
        runtime.stores._backend._conn.execute("CREATE TEMP TRIGGER fail_continuation BEFORE INSERT ON obligations BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with pytest.raises(sqlite3.IntegrityError, match="injected"):
            runtime.process("session:restart", "What does velnora mean?")
        assert runtime.stores.obligations.revision == 0
        assert runtime.stores.effects.revision == 1
        runtime.stores.close()
        runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "automatic.db")
        receipt = R3EffectGateway(runtime.stores, AdapterRegistry()).execute(**captured)
        refs = runtime.stores.r3_obligation_snapshot("session:restart", maximum=1)["obligation_refs"]
        assert len(refs) == 1
        row = runtime.stores.obligations.get(refs[0])
        assert row["created_turn_index"] == 1 and row["expires_turn_index"] == 6
        assert row["source_query_ref"] == captured["evaluation"].query_results[0].query_result_ref
        assert runtime.stores.effects.revision == 2
        assert runtime.stores.obligations.revision == 1
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        assert R3EffectGateway(runtime.stores, AdapterRegistry()).execute(**captured) == receipt
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
        assert runtime.stores.world.revision == runtime.stores.episodes.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_continuation_creation_respects_full_pending_snapshot(tmp_path, monkeypatch, backend):
    runtime = _runtime(tmp_path, monkeypatch, backend)
    try:
        for index in range(16):
            row = DialogueObligation.create(kind=ObligationKind.CLARIFICATION, session_ref="session:full",
                source_query_ref=f"query:{index}", expected_answer_contract_ref="contract:clarification",
                created_turn_index=0, expires_turn_index=50, source_decision_ref=f"decision:{index}",
                completion_receipt_ref=None, revision_pin=runtime.stores.revision_pin())
            runtime.stores.obligations.commit(row.obligation_ref, row.session_ref, row.as_dict(),
                expected_revision=runtime.stores.obligations.revision)
        before = runtime.stores.r3_obligation_snapshot("session:full", maximum=16)
        with pytest.raises(ValueError, match="bound"):
            runtime.process("session:full", "What does velnora mean?")
        assert runtime.stores.r3_obligation_snapshot("session:full", maximum=16) == before
        assert runtime.stores.world.revision == runtime.stores.episodes.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_live_continuation_is_preserved_and_expired_history_replaced(tmp_path, monkeypatch, backend):
    runtime = _runtime(tmp_path, monkeypatch, backend)
    try:
        source = runtime.process("session:lifecycle", "What does velnora mean?")
        first_ref = runtime.stores.r3_obligation_snapshot("session:lifecycle", maximum=1)["obligation_refs"][0]
        first = runtime.stores.obligations.keyed_row(first_ref)
        for turn in range(2, 6):
            result = runtime.process("session:lifecycle", "What does zorbulate mean?")
            assert result.evaluation.situation.turn_index == turn
            assert runtime.stores.obligations.keyed_row(first_ref) == first
            assert runtime.stores.obligations.revision == 1
            journal = effect_journal_get(runtime.stores, result.effect_receipt.idempotency_key)
            assert journal.entry.request_payload["query_continuation"] is None
        result = runtime.process("session:lifecycle", "What does zorbulate mean?")
        assert result.evaluation.situation.turn_index == 6
        refs = runtime.stores.r3_obligation_snapshot("session:lifecycle", maximum=1)["obligation_refs"]
        assert len(refs) == 1 and refs[0] != first_ref
        assert runtime.stores.obligations.get(first_ref) == {**first[2], "resolved": True}
        assert runtime.stores.obligations.get(first_ref)["completion_receipt_ref"] is None
        assert runtime.stores.obligations.get(refs[0])["expires_turn_index"] == 11
        assert runtime.stores.obligations.revision == 2
        assert runtime.stores.world.revision == runtime.stores.episodes.revision == 0
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        assert R3EffectGateway(runtime.stores, AdapterRegistry()).execute(source.evaluation,
            source.verification.selected_meaning, source.evaluation.situation) == source.effect_receipt
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
        assert runtime.stores.r3_obligation_snapshot("session:lifecycle", maximum=1)["obligation_refs"] == refs
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_pending_snapshot_race_blocks_terminal_continuation_write(tmp_path, monkeypatch, backend):
    import cemm_authoritative_hybrid.r3_effects as effects
    runtime = _runtime(tmp_path, monkeypatch, backend)
    original = effects.effect_journal_transition
    captured = {}
    def interleaved(stores, **kwargs):
        captured["key"] = kwargs["idempotency_key"]
        stores.obligations.commit("obligation:race", "session:race", {}, expected_revision=stores.obligations.revision)
        captured["before"] = stores.revision_pin(), stores.obligations.revision
        return original(stores, **kwargs)
    monkeypatch.setattr(effects, "effect_journal_transition", interleaved)
    try:
        with pytest.raises(StaleRevisionError, match="snapshot|obligation"):
            runtime.process("session:race", "What does velnora mean?")
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == captured["before"]
        journal = effect_journal_get(runtime.stores, captured["key"])
        assert journal.entry.state.value == "planned" and journal.receipt_payload is None
        assert runtime.stores.r3_obligation_snapshot("session:race", maximum=1)["obligation_refs"] == ["obligation:race"]
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("restart", (False, True), ids=("same-process", "restart"))
def test_public_unknown_creates_exact_generic_continuation_and_retry(tmp_path, restart):
    path = tmp_path / "automatic.db"
    runtime = load_runtime(ROOT, profile="development", store_path=path)
    try:
        before = runtime.stores.revision_pin()
        source = runtime.process("session:automatic", "What does velnora mean?")
        query = source.evaluation.query_results[0]
        expected = DialogueObligation.create(kind=ObligationKind.LEARNING_ANSWER,
            session_ref="session:automatic", source_query_ref=query.query_result_ref,
            expected_answer_contract_ref="contract:designation_answer:v2", created_turn_index=1,
            expires_turn_index=6, source_decision_ref=source.evaluation.decision.decision_ref,
            completion_receipt_ref=None, revision_pin=query.revision_pin)
        snapshot = runtime.stores.r3_obligation_snapshot("session:automatic", maximum=1)
        assert snapshot["obligation_refs"] == [expected.obligation_ref]
        assert runtime.stores.obligations.get(expected.obligation_ref) == {**expected.as_dict(), "resolved": False}
        receipt = source.effect_receipt
        assert receipt.reason is NoEffectReason.UNKNOWN
        assert receipt.learning_plan_ref is receipt.obligation_ref is None
        journal = effect_journal_get(runtime.stores, receipt.idempotency_key)
        assert thaw_json(journal.entry.request_payload)["query_continuation"] == expected.as_dict()
        assert runtime.stores.world.revision == before.world_revision
        assert runtime.stores.episodes.revision == before.episode_revision
        if restart:
            runtime.stores.close()
            runtime = load_runtime(ROOT, profile="development", store_path=path)
        before_retry = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        replay = R3EffectGateway(runtime.stores, AdapterRegistry()).execute(
            source.evaluation, source.verification.selected_meaning, source.evaluation.situation)
        assert replay == receipt
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before_retry
        assert runtime.stores.r3_obligation_snapshot("session:automatic", maximum=1) == snapshot
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend,stage,other_session,advance", (
    ("memory", "before", False, 1),
    ("sqlite", "before", False, 1),
    ("memory", "planned", False, 1),
    ("sqlite", "planned", False, 1),
    ("memory", "before", True, 1),
    ("sqlite", "before", True, 1),
    ("memory", "planned", True, 1),
    ("sqlite", "planned", True, 1),
    ("memory", "before", False, 4),
    ("sqlite", "before", False, 4),
    ("memory", "planned", False, 4),
    ("sqlite", "planned", False, 4),
    ("memory", "before", True, 4),
    ("sqlite", "before", True, 4),
    ("memory", "planned", True, 4),
    ("sqlite", "planned", True, 4),
), ids=(
    "same-turn-duplicate-same-session-before-planning-memory",
    "same-turn-duplicate-same-session-before-planning-sqlite",
    "same-turn-duplicate-same-session-after-planning-memory",
    "same-turn-duplicate-same-session-after-planning-sqlite",
    "same-turn-duplicate-foreign-session-before-planning-memory",
    "same-turn-duplicate-foreign-session-before-planning-sqlite",
    "same-turn-duplicate-foreign-session-after-planning-memory",
    "same-turn-duplicate-foreign-session-after-planning-sqlite",
    "four-turn-rewind-same-session-before-planning-memory",
    "four-turn-rewind-same-session-before-planning-sqlite",
    "four-turn-rewind-same-session-after-planning-memory",
    "four-turn-rewind-same-session-after-planning-sqlite",
    "four-turn-rewind-foreign-session-before-planning-memory",
    "four-turn-rewind-foreign-session-before-planning-sqlite",
    "four-turn-rewind-foreign-session-after-planning-memory",
    "four-turn-rewind-foreign-session-after-planning-sqlite",
))
def test_query_continuation_rechecks_source_session_reservation(tmp_path, monkeypatch, backend, stage, other_session, advance):
    runtime = _runtime(tmp_path, monkeypatch, backend)
    captured = {}
    def interleave():
        captured["entered"] = True
        session = "session:other" if other_session else "session:reservation"
        for _ in range(advance):
            runtime.process(session, "What does mother mean?")
        captured["pin"] = runtime.stores.revision_pin()
        captured["session"] = runtime.stores.r3_session_snapshot("session:reservation")
    if stage == "before":
        original = R3EffectGateway._persist_no_effect
        def before(gateway, evaluation, meaning, situation, reason):
            if not captured:
                interleave()
            return original(gateway, evaluation, meaning, situation, reason)
        monkeypatch.setattr(R3EffectGateway, "_persist_no_effect", before)
    else:
        original = R3EffectGateway._begin
        persist = R3EffectGateway._persist_no_effect
        def capture_source(gateway, evaluation, meaning, situation, reason):
            if "entered" not in captured:
                captured["source"] = (evaluation, meaning, situation)
            return persist(gateway, evaluation, meaning, situation, reason)
        monkeypatch.setattr(R3EffectGateway, "_persist_no_effect", capture_source)
        def planned(gateway, **kwargs):
            stored = original(gateway, **kwargs)
            if "entered" not in captured:
                interleave()
            return stored
        monkeypatch.setattr(R3EffectGateway, "_begin", planned)
    try:
        if other_session:
            source = runtime.process("session:reservation", "What does velnora mean?")
            assert source.evaluation.situation.turn_index == 1
            assert runtime.stores.r3_session_snapshot("session:reservation")["turn_index"] == 1
            assert len(runtime.stores.r3_obligation_snapshot("session:reservation", maximum=1)["obligation_refs"]) == 1
        else:
            with pytest.raises(ValueError, match="session|reservation"):
                runtime.process("session:reservation", "What does velnora mean?")
            assert runtime.stores.revision_pin() == captured["pin"]
            assert runtime.stores.r3_session_snapshot("session:reservation") == captured["session"]
            assert captured["session"]["turn_index"] == advance
            assert runtime.stores.obligations.revision == 0
            assert runtime.stores.r3_obligation_snapshot("session:reservation", maximum=1)["obligation_refs"] == []
            if stage == "planned":
                with pytest.raises(ValueError, match="session|reservation"):
                    R3EffectGateway(runtime.stores, AdapterRegistry()).execute(*captured["source"])
                assert runtime.stores.revision_pin() == captured["pin"]
                assert runtime.stores.r3_session_snapshot("session:reservation") == captured["session"]
                key = R3EffectGateway._effect_key(captured["source"][0].decision.decision_ref, None, "no_effect:unknown")
                journal = effect_journal_get(runtime.stores, key)
                assert journal.entry.state.value == "planned" and journal.receipt_payload is None
        assert runtime.stores.world.revision == runtime.stores.episodes.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("irrelevant", ("foreign-pending", "same-session-resolved"),
                         ids=("foreign-pending", "same-session-resolved"))
def test_sqlite_pending_snapshot_work_ignores_irrelevant_history(tmp_path, irrelevant):
    from cemm_authoritative_hybrid.persistence import open_stores
    stores = open_stores(tmp_path / "bounded-index.db", authority_generation="authority:test")
    try:
        for ref in ("obligation:z", "obligation:a"):
            stores.obligations.commit(ref, "session:chosen", {}, expected_revision=stores.obligations.revision)
        conn = stores._backend._conn
        counts, imported = [], 0
        for target_count in (0, 128, 4096):
            for index in range(imported, target_count):
                stores.obligations.commit(f"obligation:irrelevant:{index}",
                    "session:foreign" if irrelevant == "foreign-pending" else "session:chosen", {},
                    expected_revision=stores.obligations.revision, resolved=irrelevant == "same-session-resolved")
            imported = target_count
            # Warm the identical statement so compilation is not charged only
            # to the zero-history baseline in the VM-work comparison.
            stores.r3_obligation_snapshot("session:chosen", maximum=2)
            instructions = 0
            def count_instruction():
                nonlocal instructions
                instructions += 1
                return 0
            conn.set_progress_handler(count_instruction, 1)
            try:
                snapshot = stores.r3_obligation_snapshot("session:chosen", maximum=2)
            finally:
                conn.set_progress_handler(None, 0)
            assert snapshot["obligation_refs"] == ["obligation:z", "obligation:a"]
            counts.append(instructions)
        # An adjacent excluded key adds one end-of-range instruction. Growing
        # that excluded range from 128 to 4096 rows must add no work at all.
        assert max(counts) - min(counts) <= 1
        assert counts[1] == counts[2]
        details = [row[3].upper() for row in conn.execute(
            "EXPLAIN QUERY PLAN SELECT obligation_ref FROM obligations WHERE session_ref=? "
            "AND resolved=0 ORDER BY revision, obligation_ref LIMIT ?", ("session:chosen", 3))]
        assert any("SEARCH" in detail and "COVERING INDEX" in detail for detail in details)
        assert all("SCAN" not in detail and "TEMP" not in detail for detail in details)
    finally:
        stores.close()


def test_reopen_adds_pending_session_index_without_changing_records(tmp_path):
    from cemm_authoritative_hybrid.persistence import open_stores
    path = tmp_path / "index-migration.db"
    stores = open_stores(path, authority_generation="authority:test")
    try:
        stores.obligations.commit("obligation:existing", "session:chosen", {}, expected_revision=0)
        stores._backend._conn.execute("DROP INDEX IF EXISTS obligations_session_pending")
        stores._backend._conn.commit()
        before_row = stores.obligations.keyed_row("obligation:existing")
        before_revisions = stores.revisions()
        before_schema_version = stores._backend._conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0]
        stores.close()
        schemas = []
        for _ in range(2):
            stores = open_stores(path, authority_generation="authority:test")
            index = stores._backend._conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='obligations_session_pending'").fetchone()
            assert index is not None
            schemas.append(index[0])
            columns = [row[2] for row in stores._backend._conn.execute("PRAGMA index_info(obligations_session_pending)")]
            assert columns == ["session_ref", "resolved", "revision", "obligation_ref"]
            assert stores.obligations.keyed_row("obligation:existing") == before_row
            assert stores.revisions() == before_revisions
            assert stores._backend._conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == before_schema_version
            assert stores.r3_obligation_snapshot("session:chosen", maximum=1)["obligation_refs"] == ["obligation:existing"]
            stores.close()
        assert schemas[0] == schemas[1]
    finally:
        stores.close()
