"""A learning utterance durably proposes, without publishing or renewing rows."""
from dataclasses import fields, replace

import pytest

from cemm_authoritative_hybrid import bootstrap, persistence
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, NoEffectReason, NoEffectReceipt, R3EffectGateway
from cemm_authoritative_hybrid.r3_learning import LearningCoordinator, LearningPlan
from tests.test_foundation_continuation_binding import ROOT, _answer

__cemm_test_inventory__ = {
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_keeps_full_lineage_and_original_pending_row[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-keeps-full-lineage-and-original-pending-row-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5cd9dc49ac63009e26ffaf6cd57def11d5129e2b65eb3e3622ce4b698dfa3c1c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_keeps_full_lineage_and_original_pending_row[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-effect-cannot-create-a-second-pending-obligation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5cd9dc49ac63009e26ffaf6cd57def11d5129e2b65eb3e3622ce4b698dfa3c1c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_requires_current_linked_authority[missing]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-requires-current-linked-authority-missing",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "95f08c15714d72e698c4e24925dff38c6698859dd0d8f07abed777562b3c762f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_requires_current_linked_authority[foreign]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-requires-current-linked-authority-foreign",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "95f08c15714d72e698c4e24925dff38c6698859dd0d8f07abed777562b3c762f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_requires_current_linked_authority[revoked]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-requires-current-linked-authority-revoked",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "95f08c15714d72e698c4e24925dff38c6698859dd0d8f07abed777562b3c762f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_requires_current_linked_authority[wrong-type]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-requires-current-linked-authority-wrong-type",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "95f08c15714d72e698c4e24925dff38c6698859dd0d8f07abed777562b3c762f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[source-query-fresh]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-source-query-fresh",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[source-query-planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-source-query-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[source-pending-fresh]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-source-pending-fresh",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[source-pending-planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-source-pending-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[world-fresh]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-world-fresh",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[world-planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-world-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[session-fresh]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-session-fresh",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[session-planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-session-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[expiry-fresh]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-expiry-fresh",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_changed_source_or_reservation[expiry-planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-changed-source-or-reservation-expiry-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fd1c042fe64f851e816c3c7e59f1863b0da72fa37af8975dd54527e6efc27d8c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_peer_change_blocks_terminal_write[world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-peer-change-blocks-terminal-write-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d730d72489c0834e7d5dbea4da8a4fea2cf3f8d0a00efe33a6a86317619d71aa"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_peer_change_blocks_terminal_write[session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-peer-change-blocks-terminal-write-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d730d72489c0834e7d5dbea4da8a4fea2cf3f8d0a00efe33a6a86317619d71aa"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_peer_change_blocks_terminal_write[episode]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-peer-change-blocks-terminal-write-episode",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d730d72489c0834e7d5dbea4da8a4fea2cf3f8d0a00efe33a6a86317619d71aa"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_peer_change_blocks_terminal_write[effect]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-peer-change-blocks-terminal-write-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d730d72489c0834e7d5dbea4da8a4fea2cf3f8d0a00efe33a6a86317619d71aa"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_peer_change_blocks_terminal_write[obligation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-peer-change-blocks-terminal-write-obligation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d730d72489c0834e7d5dbea4da8a4fea2cf3f8d0a00efe33a6a86317619d71aa"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_obsolete_second_pending_writer_is_absent": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-obsolete-second-pending-writer-is-absent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "d08169a29dc7dad1db59282db6181591637ca93a91af50ccb1d685de6810ae1c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_source_capture_cannot_replace_validated_query": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-source-capture-cannot-replace-validated-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42c7c6cd436babaf823fba23b944796adb4e7da33cb0685f9cce5b0be009dae5"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_peer_change_blocks_initial_reservation[world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-peer-change-blocks-initial-reservation-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "bf5c1a83414fdc4e542f1762897775c3044e72a81a2535047f00a77ad3626862"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_peer_change_blocks_initial_reservation[obligation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-peer-change-blocks-initial-reservation-obligation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "bf5c1a83414fdc4e542f1762897775c3044e72a81a2535047f00a77ad3626862"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_rehashed_journal_race_is_rejected[parent]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-rehashed-journal-race-is-rejected-parent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "509e9bd3615392fae6bee17e42364b6fdab2a5475c0f9c253651e6e37a57654c"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sqlite_rehashed_journal_race_is_rejected[source-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sqlite-rehashed-journal-race-is-rejected-source-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "509e9bd3615392fae6bee17e42364b6fdab2a5475c0f9c253651e6e37a57654c"
    },
    "tests/test_foundation_learning_proposal.py::test_public_learning_proposal_is_no_effect_not_reviewer_authority[event]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-learning-proposal-is-no-effect-not-reviewer-authority-event",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f8e24c34737dc4517404d1b540ff9af003bcfeb1a1255ee7d7d5dbeea0a2cf08"
    },
    "tests/test_foundation_learning_proposal.py::test_public_learning_proposal_is_no_effect_not_reviewer_authority[embedded-designation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-learning-proposal-is-no-effect-not-reviewer-authority-embedded-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f8e24c34737dc4517404d1b540ff9af003bcfeb1a1255ee7d7d5dbeea0a2cf08"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_terminal_retry_survives_restart_and_source_expiry[terminal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-terminal-retry-survives-restart-and-source-expiry-terminal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7b2cfddee570e25d4d59b7919f31c22b1ed5813b5b43b6aa98920d0dcfb8e3d7"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_terminal_retry_survives_restart_and_source_expiry[expired-source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-terminal-retry-survives-restart-and-source-expiry-expired-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7b2cfddee570e25d4d59b7919f31c22b1ed5813b5b43b6aa98920d0dcfb8e3d7"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_invalid_serialization_preserves_atomic_metadata[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-r3-writer-preserves-atomic-metadata-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1dff861bb18f5784bfabdc726de4be4dec6350ed79eec40a61fd68dc8d9f0904"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_invalid_serialization_preserves_atomic_metadata[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-r3-writer-preserves-atomic-metadata-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1dff861bb18f5784bfabdc726de4be4dec6350ed79eec40a61fd68dc8d9f0904"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_sql_write_failure_rolls_back_then_restarts_once": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-sql-write-failure-rolls-back-then-restarts-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "0c6467d0f6ca821e3579d34a5e869f4e8fc3eab534e8c4aed52f8cbf7a419663"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[fresh-target]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-fresh-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[fresh-goal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-fresh-goal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[fresh-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-fresh-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[fresh-pending]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-fresh-pending",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[fresh-expiry]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-fresh-expiry",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[retry-target]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-retry-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[retry-goal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-retry-goal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[retry-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-retry-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[retry-pending]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-retry-pending",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_changed_plan_rejects_without_new_writes[retry-expiry]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-changed-plan-rejects-without-new-writes-retry-expiry",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "68dc86c0fe05391a205cc33cf767b3129cc6f5381281ffcdd1f575c9647bf14f"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_fabricated_reservation[turn-ref]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-fabricated-reservation-turn-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1d5f7f44bd9476dbcfcf167c9f6a57d32720f993c793e7978ea16a755683c88d"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_fabricated_reservation[foreign-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-fabricated-reservation-foreign-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1d5f7f44bd9476dbcfcf167c9f6a57d32720f993c793e7978ea16a755683c88d"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_fabricated_reservation[turn-rewind]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-fabricated-reservation-turn-rewind",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1d5f7f44bd9476dbcfcf167c9f6a57d32720f993c793e7978ea16a755683c88d"
    },
    "tests/test_foundation_learning_proposal.py::test_learning_proposal_rejects_fabricated_reservation[phase]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:learning-proposal-rejects-fabricated-reservation-phase",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1d5f7f44bd9476dbcfcf167c9f6a57d32720f993c793e7978ea16a755683c88d"
    }
}


def _setup(tmp_path, monkeypatch, backend):
    if backend == "memory":
        monkeypatch.setattr(bootstrap, "open_stores", lambda path, **kw: memory_stores(**kw))
    runtime = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    source = runtime.process("session:continuation", "What does velnora mean?")
    pin = runtime.stores.revision_pin()
    meaning, situation = _answer(runtime, source.evaluation.situation, turn_ref=stable_ref("turn", {
        "session_ref": "session:continuation", "turn_index": 2, "session_store_revision": pin.session_revision}))
    evaluation = R3EvaluationOwner(runtime.authority, runtime.stores, runtime._config).evaluate(meaning, situation)
    plan, row = LearningCoordinator(runtime.authority, runtime.stores).materialize(evaluation, meaning, situation)
    return runtime, source, meaning, situation, evaluation, plan, row


def _execute(runtime, meaning, situation, evaluation, plan, row):
    return R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority).execute(
        evaluation, meaning, situation, learning_plan=plan, obligation=row)


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_learning_proposal_keeps_full_lineage_and_original_pending_row(tmp_path, monkeypatch, backend):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, backend)
    try:
        stores = runtime.stores
        before = stores.revision_pin()
        original = stores.obligations.keyed_row(row.obligation_ref)
        obligation_revision = stores.obligations.revision
        receipt = _execute(runtime, meaning, situation, evaluation, plan, row)
        assert receipt.reason is NoEffectReason.LEARNING_OBLIGATION_ONLY
        assert receipt.learning_plan_ref == plan.plan_ref and receipt.source_obligation_ref == row.obligation_ref
        assert stores.obligations.keyed_row(row.obligation_ref) == original
        assert stores.obligations.revision == obligation_revision
        assert stores.world.revision == before.world_revision and stores.episodes.revision == before.episode_revision
        assert stores.sessions.revision == before.session_revision + 1
        assert stores.effects.revision == before.effect_revision + 2
        assert stores.r3_session_snapshot(row.session_ref)["turn_index"] == 2
        journal = stores.r3_effect_journal_get(receipt.idempotency_key)
        request = journal["entry"]["request_payload"]
        assert request["learning_meaning"] == meaning.as_dict()
        assert request["learning_evaluation"] == evaluation.as_dict()
        assert request["learning_plan"] == plan.as_dict()
        assert request["learning_source_obligation"] == row.as_dict()
        assert request["learning_source_journal"]["receipt"] == source.effect_receipt.as_dict()
        assert receipt.input_revision_pin == situation.revision_pin != row.revision_pin
        final = stores.revision_pin(), stores.obligations.revision, journal
        assert _execute(runtime, meaning, situation, evaluation, plan, row) == receipt
        assert (stores.revision_pin(), stores.obligations.revision,
                stores.r3_effect_journal_get(receipt.idempotency_key)) == final
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("missing", "foreign", "revoked", "wrong-type"),
    ids=("missing", "foreign", "revoked", "wrong-type"))
def test_learning_proposal_requires_current_linked_authority(tmp_path, monkeypatch, case):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "memory")
    try:
        authority = runtime.authority
        if case == "missing":
            authority = None
        elif case == "wrong-type":
            authority = object()
        else:
            from tests.test_foundation_alias_authority import _owners, _manifest
            from cemm_authoritative_hybrid.authority import AuthorityLinker
            owners = _owners()
            if case == "revoked":
                owners["kernel"]["capabilities"]["participant:system"].remove("cap:learn_alias")
            manifest = _manifest(tmp_path / "authority", owners)
            manifest["generation"] = "authority:foreign" if case == "foreign" else authority.generation
            authority = AuthorityLinker().link(manifest)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises((ValueError, TypeError)):
            R3EffectGateway(runtime.stores, AdapterRegistry(), authority=authority).execute(
                evaluation, meaning, situation, learning_plan=plan, obligation=row)
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("planned,case", (
    (False, "source-query"), (True, "source-query"), (False, "source-pending"), (True, "source-pending"),
    (False, "world"), (True, "world"), (False, "session"), (True, "session"), (False, "expiry"), (True, "expiry")),
    ids=("source-query-fresh", "source-query-planned", "source-pending-fresh", "source-pending-planned",
         "world-fresh", "world-planned", "session-fresh", "session-planned", "expiry-fresh", "expiry-planned"))
def test_learning_proposal_rejects_changed_source_or_reservation(tmp_path, monkeypatch, planned, case):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "memory")
    try:
        stores = runtime.stores
        if planned:
            with monkeypatch.context() as patch:
                patch.setattr(persistence.SemanticStores, "r3_effect_journal_transition",
                    lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("planned interruption")))
                with pytest.raises(RuntimeError, match="planned interruption"):
                    _execute(runtime, meaning, situation, evaluation, plan, row)
        if case == "source-query":
            key = source.effect_receipt.idempotency_key
            stores._backend._r3_effect_journals[key]["entry"]["request_payload"]["query_evaluation"]["evaluation_ref"] = "evaluation:changed"
        elif case == "source-pending":
            stores.obligations.commit(row.obligation_ref, row.session_ref, row.as_dict(),
                expected_revision=stores.obligations.revision, resolved=True)
        elif case == "world":
            stores.world.commit((), expected_revision=stores.world.revision)
        else:
            session = stores._backend.sessions._sessions[row.session_ref]
            stores._backend.sessions._sessions[row.session_ref] = replace(session, turn_index=6 if case == "expiry" else 2)
        before = stores.revision_pin(), stores.obligations.revision, stores.r3_session_snapshot(row.session_ref)
        with pytest.raises((ValueError, persistence.StaleRevisionError)):
            _execute(runtime, meaning, situation, evaluation, plan, row)
        assert (stores.revision_pin(), stores.obligations.revision, stores.r3_session_snapshot(row.session_ref)) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field", ("world_revision", "session_revision", "episode_revision", "effect_revision", "obligation_revision"),
    ids=("world", "session", "episode", "effect", "obligation"))
def test_learning_proposal_sqlite_peer_change_blocks_terminal_write(tmp_path, monkeypatch, field):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "sqlite")
    real_transition = persistence.SemanticStores.r3_effect_journal_transition
    stores = runtime.stores
    before = stores.revision_pin(), stores.obligations.keyed_row(row.obligation_ref)

    def race(self, **kwargs):
        peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation,
            model_identity=stores.revision_pin().model_identity)
        try:
            # A separate connection changes the durable revision after the gateway's read.
            peer._backend._conn.execute("INSERT INTO metadata(key,value) VALUES(?, '1') "
                "ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1", (field,))
            peer._backend._conn.commit()
        finally:
            peer.close()
        return real_transition(self, **kwargs)

    try:
        monkeypatch.setattr(persistence.SemanticStores, "r3_effect_journal_transition", race)
        with pytest.raises(persistence.StaleRevisionError, match="changed concurrently"):
            _execute(runtime, meaning, situation, evaluation, plan, row)
        key = R3EffectGateway._effect_key(evaluation.decision.decision_ref, None, "no_effect:learning_obligation_only")
        assert stores.r3_effect_journal_get(key)["entry"]["state"] == "planned"
        assert stores.r3_session_snapshot(row.session_ref)["turn_index"] == 1
        assert stores.obligations.keyed_row(row.obligation_ref) == before[1]
        assert stores.world.revision == before[0].world_revision
    finally:
        stores.close()


def test_learning_proposal_obsolete_second_pending_writer_is_absent():
    from cemm_authoritative_hybrid import r3_persistence
    assert not hasattr(persistence.SemanticStores, "r3_commit_learning_outcome")
    assert not hasattr(r3_persistence, "commit_learning_outcome")
    assert "r3_commit_learning_outcome" not in r3_persistence._REQUIRED_PORT_METHODS


def test_learning_proposal_source_capture_cannot_replace_validated_query(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid import r3_learning
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry, EffectJournalState
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "memory")
    real_capture = r3_learning.learning_proposal_request
    stores = runtime.stores

    def replace_before_capture(*args, **kwargs):
        journal = stores._backend._r3_effect_journals[source.effect_receipt.idempotency_key]
        values = {name: value for name, value in journal["entry"].items() if name not in {"abi_version", "journal_ref"}}
        values["state"] = EffectJournalState(values["state"])
        values["blocker_refs"] = tuple(values["blocker_refs"])
        values["request_payload"] = {**values["request_payload"], "turn_ref": "turn:forged"}
        journal["entry"] = EffectJournalEntry.create(**values).as_dict()
        return real_capture(*args, **kwargs)

    try:
        before = stores.revision_pin(), stores.obligations.revision
        monkeypatch.setattr(r3_learning, "learning_proposal_request", replace_before_capture)
        with pytest.raises(ValueError, match="source query journal changed"):
            _execute(runtime, meaning, situation, evaluation, plan, row)
        assert (stores.revision_pin(), stores.obligations.revision) == before
    finally:
        stores.close()


@pytest.mark.parametrize("field", ("world_revision", "obligation_revision"), ids=("world", "obligation"))
def test_learning_proposal_sqlite_peer_change_blocks_initial_reservation(tmp_path, monkeypatch, field):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "sqlite")
    real_begin = persistence.SemanticStores.r3_effect_journal_begin
    stores = runtime.stores
    before = stores.revision_pin()

    def race(self, **kwargs):
        peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation,
            model_identity=before.model_identity)
        try:
            if field == "world_revision":
                peer.world.commit((), expected_revision=peer.world.revision)
            else:
                peer.obligations.commit("obligation:peer", "session:peer", {}, expected_revision=peer.obligations.revision)
        finally:
            peer.close()
        return real_begin(self, **kwargs)

    try:
        monkeypatch.setattr(persistence.SemanticStores, "r3_effect_journal_begin", race)
        with pytest.raises(persistence.StaleRevisionError, match="changed concurrently"):
            _execute(runtime, meaning, situation, evaluation, plan, row)
        key = R3EffectGateway._effect_key(evaluation.decision.decision_ref, None, "no_effect:learning_obligation_only")
        assert stores.r3_effect_journal_get(key) is None
        assert stores.effects.revision == before.effect_revision
        assert stores.r3_session_snapshot(row.session_ref)["turn_index"] == 1
    finally:
        stores.close()


@pytest.mark.parametrize("target", ("parent", "source-query"), ids=("parent", "source-query"))
def test_learning_proposal_sqlite_rehashed_journal_race_is_rejected(tmp_path, monkeypatch, target):
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "sqlite")
    stores = runtime.stores
    real_transition = persistence.SemanticStores.r3_effect_journal_transition
    real_verify = persistence._r3_verify_journal_row
    key = R3EffectGateway._effect_key(evaluation.decision.decision_ref, None, "no_effect:learning_obligation_only")
    changed = []

    def after_initial_read(*args):
        result = real_verify(*args)
        if not changed and result["entry"]["idempotency_key"] == key:
            changed.append(True)
            peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation,
                model_identity=stores.revision_pin().model_identity)
            try:
                target_key = key if target == "parent" else source.effect_receipt.idempotency_key
                journal = peer.r3_effect_journal_get(target_key)
                values = {name: value for name, value in journal["entry"].items()
                          if name not in {"abi_version", "journal_ref"}}
                from cemm_authoritative_hybrid.r3_persistence import EffectJournalState
                values["state"] = EffectJournalState(values["state"])
                values["blocker_refs"] = tuple(values["blocker_refs"])
                values["request_payload"] = {**values["request_payload"], "changed_evidence": "proof:peer"}
                entry = EffectJournalEntry.create(**values).as_dict()
                peer._backend._conn.execute("UPDATE r3_effect_journal SET entry_json=?,entry_hash=? WHERE idempotency_key=?",
                    (persistence._r3_canonical_json(entry), persistence._payload_hash(entry), target_key))
                peer._backend._conn.commit()
            finally:
                peer.close()
        return result

    def race(self, **kwargs):
        with monkeypatch.context() as patch:
            patch.setattr(persistence, "_r3_verify_journal_row", after_initial_read)
            return real_transition(self, **kwargs)

    try:
        monkeypatch.setattr(persistence.SemanticStores, "r3_effect_journal_transition", race)
        with pytest.raises((ValueError, persistence.StaleRevisionError), match="parent changed|source query journal changed"):
            _execute(runtime, meaning, situation, evaluation, plan, row)
        assert changed == [True]
        assert stores.r3_session_snapshot(row.session_ref)["turn_index"] == 1
        assert stores.obligations.get(row.obligation_ref) == {**row.as_dict(), "resolved": False}
        assert stores.world.revision == 0
    finally:
        stores.close()


@pytest.mark.parametrize("surface", ("learn velnora means likes", "learn that velnora means likes"),
    ids=("event", "embedded-designation"))
def test_public_learning_proposal_is_no_effect_not_reviewer_authority(tmp_path, monkeypatch, surface):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "sqlite")
    try:
        original = runtime.stores.obligations.keyed_row(row.obligation_ref)
        monkeypatch.setattr(AdapterRegistry, "get", lambda *a: pytest.fail("proposal consulted an adapter"))
        result = runtime.process(row.session_ref, surface)
        assert result.effect_receipt.reason is NoEffectReason.LEARNING_OBLIGATION_ONLY
        assert result.evaluation.expression == meaning.expression
        assert result.response_meaning.learning_plan.target_ref == "rel:likes"
        assert runtime.stores.world.revision == 0
        assert runtime.stores.obligations.keyed_row(row.obligation_ref) == original
        assert result.response_meaning.obligation == row
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("expired", (False, True), ids=("terminal", "expired-source"))
def test_learning_proposal_terminal_retry_survives_restart_and_source_expiry(tmp_path, monkeypatch, expired):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "sqlite")
    receipt = _execute(runtime, meaning, situation, evaluation, plan, row)
    if expired:
        for _ in range(4):
            runtime.process(row.session_ref, "What does velnora mean?")
        assert runtime.stores.r3_session_snapshot(row.session_ref)["turn_index"] == 6
    runtime.stores.close()
    runtime = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        assert _execute(runtime, meaning, situation, evaluation, plan, row).as_dict() == receipt.as_dict()
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_learning_proposal_invalid_serialization_preserves_atomic_metadata(tmp_path, monkeypatch, backend):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, backend)
    try:
        stores = runtime.stores
        before = stores.revision_pin(), stores.obligations.revision, stores.obligations.keyed_row(row.obligation_ref)
        original = type(meaning).as_dict
        with monkeypatch.context() as patch:
            patch.setattr(type(meaning), "as_dict", lambda self: {**original(self), "invalid": {1}})
            with pytest.raises((ValueError, TypeError)):
                _execute(runtime, meaning, situation, evaluation, plan, row)
        assert (stores.revision_pin(), stores.obligations.revision, stores.obligations.keyed_row(row.obligation_ref)) == before
        encode_receipt = NoEffectReceipt.as_dict
        with monkeypatch.context() as patch:
            patch.setattr(NoEffectReceipt, "as_dict", lambda self: (
                {**encode_receipt(self), "invalid": {1}} if self.reason is NoEffectReason.LEARNING_OBLIGATION_ONLY
                else encode_receipt(self)))
            with pytest.raises((ValueError, TypeError)):
                _execute(runtime, meaning, situation, evaluation, plan, row)
        key = R3EffectGateway._effect_key(evaluation.decision.decision_ref, None, "no_effect:learning_obligation_only")
        assert stores.r3_effect_journal_get(key)["entry"]["state"] == "planned"
        assert stores.sessions.revision == before[0].session_revision
        assert stores.effects.revision == before[0].effect_revision + 1
        assert stores.obligations.revision == before[1]
        assert stores.obligations.keyed_row(row.obligation_ref) == before[2]
        receipt = _execute(runtime, meaning, situation, evaluation, plan, row)
        assert receipt.reason is NoEffectReason.LEARNING_OBLIGATION_ONLY
        assert stores.obligations.keyed_row(row.obligation_ref) == before[2]
        assert stores.pending_dialogue_obligations(row.session_ref, (row.obligation_ref,), maximum=1, turn_index=2) == (row,)
        assert stores.r3_obligation_snapshot(row.session_ref, maximum=1)["obligation_refs"] == [row.obligation_ref]
    finally:
        runtime.stores.close()


def test_learning_proposal_sql_write_failure_rolls_back_then_restarts_once(tmp_path, monkeypatch):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "sqlite")
    stores = runtime.stores
    before = stores.revision_pin(), stores.obligations.revision, stores.obligations.keyed_row(row.obligation_ref)
    real_write = persistence._r3_write_session_sqlite
    writes = []

    def fail_after_write(*args, **kwargs):
        real_write(*args, **kwargs)
        writes.append(kwargs["turn_index"])
        raise RuntimeError("after real session write")

    with monkeypatch.context() as patch:
        patch.setattr(persistence, "_r3_write_session_sqlite", fail_after_write)
        with pytest.raises(RuntimeError, match="after real session write"):
            _execute(runtime, meaning, situation, evaluation, plan, row)
    assert writes == [2]
    assert stores.sessions.revision == before[0].session_revision
    assert stores.effects.revision == before[0].effect_revision + 1
    assert stores.obligations.keyed_row(row.obligation_ref) == before[2]
    assert stores.r3_session_snapshot(row.session_ref)["turn_index"] == 1
    key = R3EffectGateway._effect_key(evaluation.decision.decision_ref, None, "no_effect:learning_obligation_only")
    assert stores.r3_effect_journal_get(key)["entry"]["state"] == "planned"
    stores.close()
    runtime = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        receipt = _execute(runtime, meaning, situation, evaluation, plan, row)
        assert receipt.reason is NoEffectReason.LEARNING_OBLIGATION_ONLY
        assert runtime.stores.effects.revision == before[0].effect_revision + 2
        assert runtime.stores.sessions.revision == before[0].session_revision + 1
        assert runtime.stores.obligations.keyed_row(row.obligation_ref) == before[2]
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("terminal,field", (
    (False, "target_ref"), (False, "goal_ref"), (False, "source_query_ref"), (False, "source_obligation_ref"), (False, "expires_at_turn"),
    (True, "target_ref"), (True, "goal_ref"), (True, "source_query_ref"), (True, "source_obligation_ref"), (True, "expires_at_turn")),
    ids=("fresh-target", "fresh-goal", "fresh-query", "fresh-pending", "fresh-expiry",
         "retry-target", "retry-goal", "retry-query", "retry-pending", "retry-expiry"))
def test_learning_proposal_changed_plan_rejects_without_new_writes(tmp_path, monkeypatch, field, terminal):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "memory")
    try:
        if terminal:
            _execute(runtime, meaning, situation, evaluation, plan, row)
        values = {f.name: getattr(plan, f.name) for f in fields(plan) if f.name not in {"abi_version", "plan_ref"}}
        values[field] = 7 if field == "expires_at_turn" else "rel:loves" if field == "target_ref" else "ref:changed"
        if field == "source_obligation_ref":
            values["provenance_refs"] = (*plan.provenance_refs, "ref:changed")
        changed = LearningPlan.create(**values)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(ValueError):
            _execute(runtime, meaning, situation, evaluation, changed, row)
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("turn-ref", "foreign-session", "turn-rewind", "phase"),
    ids=("turn-ref", "foreign-session", "turn-rewind", "phase"))
def test_learning_proposal_rejects_fabricated_reservation(tmp_path, monkeypatch, case):
    runtime, source, meaning, situation, evaluation, plan, row = _setup(tmp_path, monkeypatch, "memory")
    try:
        if case == "turn-ref":
            # Independently authored semantic artifacts, but no real ORIENT reservation.
            meaning, situation = _answer(runtime, source.evaluation.situation)
            evaluation = R3EvaluationOwner(runtime.authority, runtime.stores, runtime._config).evaluate(meaning, situation)
            plan, row = LearningCoordinator(runtime.authority, runtime.stores).materialize(evaluation, meaning, situation)
        else:
            session = runtime.stores._backend.sessions._sessions[row.session_ref]
            runtime.stores._backend.sessions._sessions[row.session_ref] = replace(session,
                **({"session_ref": "session:foreign"} if case == "foreign-session" else
                   {"turn_index": 0} if case == "turn-rewind" else {"phase": "active"}))
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(ValueError):
            _execute(runtime, meaning, situation, evaluation, plan, row)
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()
