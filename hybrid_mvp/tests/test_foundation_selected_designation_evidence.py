"""Authenticate selected evidence at its original pin through a current snapshot."""
from dataclasses import replace

import pytest

from cemm_authoritative_hybrid import persistence
from cemm_authoritative_hybrid.authority import DesignationIndex
from cemm_authoritative_hybrid.r3_codec import MAX_REF_CHARS, MAX_ROWS
from cemm_authoritative_hybrid.r3_designations import AdmittedDesignationReader
from tests.test_foundation_alias_publication import _publication, _signed


__cemm_test_inventory__ = {
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_preserves_original_pin_after_readonly_turns[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-preserves-original-pin-after-readonly-turns-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7e7f2da260d1f953d9b1066cc864d417daf36e36612cb1ec934143d53da9c88a"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_preserves_original_pin_after_readonly_turns[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-preserves-original-pin-after-readonly-turns-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7e7f2da260d1f953d9b1066cc864d417daf36e36612cb1ec934143d53da9c88a"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_restarts_without_reviewer_key_under_new_proposer": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-restarts-without-reviewer-key-under-new-proposer",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "234b402f507a021d7100fa7644c88273ed455b3f7f8ead332a7ddc76cabc1a8d"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_learned_owner_survives_static_identity_collision[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-learned-owner-survives-static-identity-collision-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "e505cd9dc6f50ae0414221a3c9ea09bc8867a49d4eee3ea096df20e640765a0c"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_learned_owner_survives_static_identity_collision[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-learned-owner-survives-static-identity-collision-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "e505cd9dc6f50ae0414221a3c9ea09bc8867a49d4eee3ea096df20e640765a0c"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_foreign_or_future_source_pin[generation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-foreign-or-future-source-pin-generation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2b24d1c1f4c627f63d332dff50652590604835ef2f16f79c60500d48eae5b587"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_foreign_or_future_source_pin[world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-foreign-or-future-source-pin-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2b24d1c1f4c627f63d332dff50652590604835ef2f16f79c60500d48eae5b587"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_foreign_or_future_source_pin[session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-foreign-or-future-source-pin-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2b24d1c1f4c627f63d332dff50652590604835ef2f16f79c60500d48eae5b587"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_foreign_or_future_source_pin[episode]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-foreign-or-future-source-pin-episode",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2b24d1c1f4c627f63d332dff50652590604835ef2f16f79c60500d48eae5b587"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_foreign_or_future_source_pin[effect]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-foreign-or-future-source-pin-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "2b24d1c1f4c627f63d332dff50652590604835ef2f16f79c60500d48eae5b587"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_caps_publication_and_cache_by_original_pin[memory-world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-caps-publication-and-cache-by-original-pin-memory-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "24595c8b2f7bdf98d87699997ccba98966fa3e8a0a5e7141735b15fe32923327"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_caps_publication_and_cache_by_original_pin[sqlite-world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-caps-publication-and-cache-by-original-pin-sqlite-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "24595c8b2f7bdf98d87699997ccba98966fa3e8a0a5e7141735b15fe32923327"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_caps_publication_and_cache_by_original_pin[memory-effect]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-caps-publication-and-cache-by-original-pin-memory-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "24595c8b2f7bdf98d87699997ccba98966fa3e8a0a5e7141735b15fe32923327"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_caps_publication_and_cache_by_original_pin[sqlite-effect]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-caps-publication-and-cache-by-original-pin-sqlite-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "24595c8b2f7bdf98d87699997ccba98966fa3e8a0a5e7141735b15fe32923327"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-identity]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-identity",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[learned-identity]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-learned-identity",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-truncated]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-truncated",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[learned-truncated]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-learned-truncated",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-reordered]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-reordered",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[learned-reordered]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-learned-reordered",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-substituted]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-substituted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[learned-substituted]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-learned-substituted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-duplicate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-duplicate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-empty]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-empty",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-list]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-list",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-ref-type]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-ref-type",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-ref-empty]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-ref-empty",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-ref-bound]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-ref-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-rows-bound]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-rows-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[static-contribution]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-static-contribution",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_changed_or_nonexact_selection[learned-contribution]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-changed-or-nonexact-selection-learned-contribution",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "42379febf193431495eba24c5cf9e4a415168dd19de4654d71f4e3d2cf1a7cec"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[id-type]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-id-type",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[id-empty]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-id-empty",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[id-bound]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-id-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[pin-dict]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-pin-dict",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[pin-subclass]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-pin-subclass",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[id-subclass]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-id-subclass",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[tuple-subclass]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-tuple-subclass",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_requires_exact_identity_and_pin[ref-subclass]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-requires-exact-identity-and-pin-ref-subclass",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "fdb370aba725f401556ac70f0527cdcf3d19ebf01321c720bbeb2d6c2faf44cc"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_missing_and_nonpublication_locator[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-missing-and-nonpublication-locator-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "55e7cd2ed325d76ee5b468d35bf0978e4821ebea406b18ddb8ed2c8f4f208dd3"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_rejects_missing_and_nonpublication_locator[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-rejects-missing-and-nonpublication-locator-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "55e7cd2ed325d76ee5b468d35bf0978e4821ebea406b18ddb8ed2c8f4f208dd3"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_cache_rejects_closed_and_locally_mutated_batch[memory-world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-cache-rejects-closed-and-locally-mutated-batch-memory-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "dd64d982a3b8b556d7ca471618c3b0e84c19dc8290a7a2c34afcaefa02423e2b"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_cache_rejects_closed_and_locally_mutated_batch[sqlite-world]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-cache-rejects-closed-and-locally-mutated-batch-sqlite-world",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "dd64d982a3b8b556d7ca471618c3b0e84c19dc8290a7a2c34afcaefa02423e2b"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_cache_rejects_closed_and_locally_mutated_batch[memory-model]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-cache-rejects-closed-and-locally-mutated-batch-memory-model",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "dd64d982a3b8b556d7ca471618c3b0e84c19dc8290a7a2c34afcaefa02423e2b"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_cache_rejects_closed_and_locally_mutated_batch[sqlite-model]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-cache-rejects-closed-and-locally-mutated-batch-sqlite-model",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "dd64d982a3b8b556d7ca471618c3b0e84c19dc8290a7a2c34afcaefa02423e2b"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_cache_rejects_closed_and_locally_mutated_batch[memory-obligation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-cache-rejects-closed-and-locally-mutated-batch-memory-obligation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "dd64d982a3b8b556d7ca471618c3b0e84c19dc8290a7a2c34afcaefa02423e2b"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_cache_rejects_closed_and_locally_mutated_batch[sqlite-obligation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-cache-rejects-closed-and-locally-mutated-batch-sqlite-obligation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "dd64d982a3b8b556d7ca471618c3b0e84c19dc8290a7a2c34afcaefa02423e2b"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_cached_sqlite_batch_preserves_peer_snapshot_and_rejects_stale_reopen": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-cached-sqlite-batch-preserves-peer-snapshot-and-rejects-stale-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "a77e288773d57a97ed54a907bcb7c7b337f8951948af2f74e3ee0585d790ed9b"
    },
    "tests/test_foundation_selected_designation_evidence.py::test_selected_evidence_uses_existing_bounded_cache": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:selected-evidence-uses-existing-bounded-cache",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7.4",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "238ce9f29c7ede826e77238b05802158d7d75abbc3c3a7e5ffa102311e571ab2"
    }
}


def _published(tmp_path, monkeypatch, backend):
    runtime, _, _, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    reader = AdmittedDesignationReader(runtime.authority, runtime.stores,
        memory_review_binding=grant["store_binding"] if backend == "memory" else None)
    pin = runtime.stores.revision_pin()
    with reader.batch(pin) as batch:
        learned = batch.resolve_world_fact(receipt.committed_fact_refs[0])
        static, = batch.for_surface("likes", "en")
    return runtime, pending, reader, pin, learned, static


def _authenticate(batch, evidence, pin):
    assert hasattr(batch, "authenticate_selected"), "missing selected designation evidence authentication"
    return batch.authenticate_selected(evidence.designation.designation_fact_ref, evidence.provenance_refs, pin)


def _forbid_enumeration(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("selected evidence must use keyed reads, not enumeration")
    monkeypatch.setattr(DesignationIndex, "bounded_facts", forbidden)
    monkeypatch.setattr(DesignationIndex, "facts_for_surface", forbidden)
    monkeypatch.setattr(DesignationIndex, "facts_for_target", forbidden)
    monkeypatch.setattr(persistence.SemanticStores, "r3_designation_facts", forbidden)


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_selected_evidence_preserves_original_pin_after_readonly_turns(tmp_path, monkeypatch, backend):
    runtime, pending, reader, original, learned, static = _published(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        world = stores.world.revision
        for _ in range(2):
            runtime.process(pending.session_ref, "What does hello mean?")
        current = stores.revision_pin()
        assert current != original and current.world_revision == world
        assert current.effect_revision > original.effect_revision
        assert current.session_revision > original.session_revision
        with pytest.raises(persistence.StaleRevisionError), reader.batch(original):
            pytest.fail("historical pin cannot open a current batch")
        _forbid_enumeration(monkeypatch)
        before = current, stores.r3_obligation_revision(), stores.world.get(learned.world_fact_ref)
        with reader.batch(current) as batch:
            assert _authenticate(batch, learned, original) == learned
            assert _authenticate(batch, static, original) == static
            assert _authenticate(batch, learned, original) == learned
        assert (stores.revision_pin(), stores.r3_obligation_revision(),
            stores.world.get(learned.world_fact_ref)) == before
        assert runtime.authority.designations.resolve_fact(learned.designation.designation_fact_ref) is None
    finally:
        stores.close()


def test_selected_evidence_restarts_without_reviewer_key_under_new_proposer(tmp_path, monkeypatch):
    runtime, pending, reader, original, learned, static = _published(tmp_path, monkeypatch, "sqlite")
    authority = runtime.authority
    runtime.process(pending.session_ref, "What does velnora mean?")
    runtime.stores.close()
    del runtime, reader
    stores = persistence.open_stores(tmp_path / "proposal.db", authority_generation=authority.generation,
        model_identity="model:new-reader")
    try:
        _forbid_enumeration(monkeypatch)
        before = stores.revision_pin(), stores.r3_obligation_revision()
        assert before[0].model_identity != original.model_identity
        with AdmittedDesignationReader(authority, stores).batch(before[0]) as batch:
            assert _authenticate(batch, learned, original) == learned
            assert _authenticate(batch, static, original) == static
        assert (stores.revision_pin(), stores.r3_obligation_revision()) == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_selected_learned_owner_survives_static_identity_collision(tmp_path, monkeypatch, backend):
    runtime, _, reader, pin, learned, static = _published(tmp_path, monkeypatch, backend)
    try:
        # Synthetic evidence-owner component fixture, not reviewed acquisition:
        # the replacement index deliberately retains the original authority hash.
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex((learned.designation, static.designation)))
        _forbid_enumeration(monkeypatch)
        with reader.batch(pin) as batch:
            assert _authenticate(batch, learned, pin) == learned
            assert _authenticate(batch, static, pin) == static
            static_proofs = (learned.designation.designation_fact_ref, runtime.authority.generation,
                runtime.authority.content_hash)
            resolved = batch.authenticate_selected(learned.designation.designation_fact_ref, static_proofs, pin)
            assert resolved.designation == learned.designation
            assert resolved.world_fact_ref is None
            assert resolved.authority_designation_ref == learned.designation.designation_fact_ref
            assert resolved.provenance_refs == static_proofs
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("generation", "world", "session", "episode", "effect"),
    ids=("generation", "world", "session", "episode", "effect"))
def test_selected_evidence_rejects_foreign_or_future_source_pin(tmp_path, monkeypatch, case):
    runtime, _, reader, pin, learned, _ = _published(tmp_path, monkeypatch, "memory")
    try:
        bad = (replace(pin, authority_generation="authority:foreign") if case == "generation" else
            replace(pin, **{case + "_revision": getattr(pin, case + "_revision") + 1}))
        with reader.batch(pin) as batch, pytest.raises(ValueError, match="future or foreign"):
            _authenticate(batch, learned, bad)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend,cap", (("memory", "world"), ("sqlite", "world"),
    ("memory", "effect"), ("sqlite", "effect")),
    ids=("memory-world", "sqlite-world", "memory-effect", "sqlite-effect"))
def test_selected_evidence_caps_publication_and_cache_by_original_pin(tmp_path, monkeypatch, backend, cap):
    runtime, _, reader, original, learned, _ = _published(tmp_path, monkeypatch, backend)
    try:
        earlier = replace(original, **{cap + "_revision": getattr(original, cap + "_revision") - 1})
        with reader.batch(original) as batch:
            assert _authenticate(batch, learned, original) == learned
            with pytest.raises(ValueError):
                _authenticate(batch, learned, earlier)
            assert _authenticate(batch, learned, original) == learned
        # Rejected historical evidence cannot become an authorized cache entry.
        assert len(reader._cache) < 256
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("kind,case", (("static", "identity"), ("learned", "identity"),
    ("static", "truncated"), ("learned", "truncated"), ("static", "reordered"), ("learned", "reordered"),
    ("static", "substituted"), ("learned", "substituted"), ("static", "duplicate"),
    ("static", "empty"), ("static", "list"), ("static", "ref-type"), ("static", "ref-empty"),
    ("static", "ref-bound"), ("static", "rows-bound"),
    ("static", "contribution"), ("learned", "contribution")),
    ids=("static-identity", "learned-identity", "static-truncated", "learned-truncated", "static-reordered",
        "learned-reordered", "static-substituted", "learned-substituted", "static-duplicate", "static-empty", "static-list",
        "static-ref-type", "static-ref-empty", "static-ref-bound", "static-rows-bound", "static-contribution",
        "learned-contribution"))
def test_selected_evidence_rejects_changed_or_nonexact_selection(tmp_path, monkeypatch, kind, case):
    runtime, _, reader, pin, learned, static = _published(tmp_path, monkeypatch, "memory")
    try:
        evidence = static if kind == "static" else learned
        identity, refs = evidence.designation.designation_fact_ref, evidence.provenance_refs
        if case == "identity":
            identity = (learned if kind == "static" else static).designation.designation_fact_ref
        elif case == "truncated":
            refs = refs[:-1]
        elif case == "reordered":
            refs = tuple(reversed(refs))
        elif case == "substituted":
            refs = refs[:-1] + ("proof:unrelated",)
        elif case == "duplicate":
            refs = refs + (refs[0],)
        elif case == "empty":
            refs = ()
        elif case == "list":
            refs = list(refs)
        elif case == "ref-type":
            refs = (1,) + refs[1:]
        elif case == "ref-empty":
            refs = ("",) + refs[1:]
        elif case == "ref-bound":
            refs = ("x" * (MAX_REF_CHARS + 1),) + refs[1:]
        elif case == "rows-bound":
            refs = tuple("proof:" + str(i) for i in range(MAX_ROWS + 1))
        elif case == "contribution":
            refs = ("frame:unrelated",) + refs
        with reader.batch(pin) as batch:
            assert _authenticate(batch, evidence, pin) == evidence
            with pytest.raises((TypeError, ValueError)):
                batch.authenticate_selected(identity, refs, pin)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("id-type", "id-empty", "id-bound", "pin-dict", "pin-subclass", "id-subclass",
    "tuple-subclass", "ref-subclass"), ids=("id-type", "id-empty", "id-bound", "pin-dict", "pin-subclass",
        "id-subclass", "tuple-subclass", "ref-subclass"))
def test_selected_evidence_requires_exact_identity_and_pin(tmp_path, monkeypatch, case):
    runtime, _, reader, pin, learned, _ = _published(tmp_path, monkeypatch, "memory")
    class Text(str):
        pass
    class Refs(tuple):
        pass
    class Pin(persistence.RevisionPin):
        pass
    try:
        identity, refs, source = learned.designation.designation_fact_ref, learned.provenance_refs, pin
        if case == "id-type":
            identity = 1
        elif case == "id-empty":
            identity = ""
        elif case == "id-bound":
            identity = "x" * (MAX_REF_CHARS + 1)
        elif case == "pin-dict":
            source = pin.as_dict()
        elif case == "pin-subclass":
            source = Pin(**{k: v for k, v in pin.as_dict().items() if k != "abi_version"})
        elif case == "id-subclass":
            identity = Text(identity)
        elif case == "tuple-subclass":
            refs = Refs(refs)
        elif case == "ref-subclass":
            refs = (Text(refs[0]),) + refs[1:]
        with reader.batch(pin) as batch, pytest.raises((TypeError, ValueError)):
            assert hasattr(batch, "authenticate_selected"), "missing selected designation evidence authentication"
            batch.authenticate_selected(identity, refs, source)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_selected_evidence_rejects_missing_and_nonpublication_locator(tmp_path, monkeypatch, backend):
    runtime, _, reader, pin, learned, _ = _published(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        naked = persistence.Fact("fact:unreviewed", "op:designation", {"role:surface": "naked", "role:target": "rel:likes"},
            proof={"source": "reviewer:test", "alias_language": "en"})
        stores.world.commit((naked,), expected_revision=pin.world_revision)
        current = stores.revision_pin()
        with reader.batch(current) as batch:
            assert hasattr(batch, "authenticate_selected"), "missing selected designation evidence authentication"
            for locator in ("fact:missing", naked.fact_ref):
                with pytest.raises(ValueError):
                    batch.authenticate_selected(learned.designation.designation_fact_ref, (locator,), current)
    finally:
        stores.close()


@pytest.mark.parametrize("backend,mutation", (("memory", "world"), ("sqlite", "world"),
    ("memory", "model"), ("sqlite", "model"), ("memory", "obligation"), ("sqlite", "obligation")),
    ids=("memory-world", "sqlite-world", "memory-model", "sqlite-model", "memory-obligation", "sqlite-obligation"))
def test_selected_evidence_cache_rejects_closed_and_locally_mutated_batch(tmp_path, monkeypatch, backend, mutation):
    runtime, _, reader, pin, learned, _ = _published(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        with reader.batch(pin) as batch:
            assert _authenticate(batch, learned, pin) == learned
        with pytest.raises(ValueError, match="closed"):
            _authenticate(batch, learned, pin)
        with pytest.raises(persistence.StaleRevisionError):
            with reader.batch(pin) as batch:
                assert _authenticate(batch, learned, pin) == learned
                # Temporary-store integrity corruption, not supported public writes.
                if mutation == "world":
                    if backend == "memory":
                        stores.world.commit((), expected_revision=stores.world.revision)
                    else:
                        # The open read transaction forbids the public SQLite writer.
                        stores._backend._conn.execute("UPDATE metadata SET value=value+1 WHERE key='world_revision'")
                elif mutation == "model":
                    stores._backend._model_identity = "model:changed"
                elif backend == "memory":
                    stores.obligations.revision += 1
                else:
                    stores._backend._conn.execute("UPDATE metadata SET value=value+1 WHERE key='obligation_revision'")
                _authenticate(batch, learned, pin)
    finally:
        stores.close()


def test_selected_evidence_cached_sqlite_batch_preserves_peer_snapshot_and_rejects_stale_reopen(tmp_path, monkeypatch):
    runtime, _, reader, pin, learned, static = _published(tmp_path, monkeypatch, "sqlite")
    stores = runtime.stores
    peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation)
    try:
        with reader.batch(pin) as batch:
            assert _authenticate(batch, learned, pin) == learned
            peer.world.commit((persistence.Fact("fact:peer", "op:type", {}),), expected_revision=peer.world.revision)
            assert _authenticate(batch, learned, pin) == learned
            assert _authenticate(batch, static, pin) == static
        assert stores.revision_pin() == pin
        with pytest.raises(persistence.StaleRevisionError), reader.batch(pin):
            pytest.fail("new batch must reject stale peer metadata before cache reuse")
    finally:
        peer.close()
        stores.close()


def test_selected_evidence_uses_existing_bounded_cache(tmp_path, monkeypatch):
    runtime, _, reader, pin, _, static = _published(tmp_path, monkeypatch, "memory")
    try:
        _forbid_enumeration(monkeypatch)
        with reader.batch(pin) as batch:
            for i in range(257):
                assert _authenticate(batch, static, replace(pin, model_identity="model:source-" + str(i))) == static
                assert len(reader._cache) <= 256
        assert len(reader._cache) == 256
    finally:
        runtime.stores.close()
