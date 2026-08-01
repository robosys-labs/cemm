from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import cemm_authoritative_hybrid.governance as governance
from cemm_authoritative_hybrid.governance import (
    GovernanceError,
    LedgerAnchor,
    effective_replay_status,
    expected_record_ref,
    load_ledger_anchor,
    read_hash_chain,
    verify_file_invalidation,
)


ROOT = Path(__file__).resolve().parents[1]

GOVERNING_DOCUMENTS = (
    "AGENTS.md",
    "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md",
    "docs/ARCHITECTURE.md",
    "docs/ABI_REGISTRY.md",
)

SUPERSEDED_EXECUTION_CLAIMS = (
    "docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md",
    "docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md",
    "docs/superpowers/plans/2026-07-29-m1-six-phase-kernel.md",
    "docs/superpowers/plans/2026-07-29-m2-hybrid-proposal-verifier.md",
    "docs/superpowers/plans/2026-07-29-m3-cognition-learning-realization.md",
    "docs/superpowers/plans/2026-07-29-m4-training-failure-competitive-evaluation.md",
    "docs/superpowers/plans/2026-07-29-m5-surfaces-reliable-cutover.md",
    "docs/superpowers/plans/2026-07-30-corrective-replay-plan.md",
)

HISTORICAL_EVIDENCE = (
    "docs/EVALUATION_REPORT.md",
    "docs/NEURAL_MODEL.md",
    "docs/COMPARISON.md",
    "docs/RUNTIME_TRACES.md",
    "docs/WORKTREE_INTEGRATION.md",
    "artifacts/",
)

ACTIVE_POINTERS = (
    "AGENTS.md",
    "README.md",
    "INTEGRATION.md",
    "docs/IMPLEMENTATION_PLAN.md",
    "docs/ABI_REGISTRY.md",
    "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
)


__cemm_test_inventory__ = {
    "tests/test_replay_governance.py::test_admission_binding_stores_gate_and_exact_run_refs": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:admission-binding-stores-gate-and-exact-run-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "cd85c5d6af670fd72f5260bd3ba077845c405a918d77c928535edfbc2411e541"
    },
    "tests/test_replay_governance.py::test_admission_refs_require_exact_gate_and_run_namespaces": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:admission-refs-require-exact-gate-and-run-namespaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "f14b0c9a3323d6d990bdcece576c0b738ffec5df5911bdc2f57b8e929a01e66d"
    },
    "tests/test_replay_governance.py::test_admission_requires_passed_technical_steps_and_passes_passed_to_task4[externally-blocked]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:admission-requires-passed-technical-steps-and-passes-passed-to-task4",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "cabe0c6ce12e0dc44ebac1c5b68e83a4ad50610959317e643dfa89d536391974"
    },
    "tests/test_replay_governance.py::test_admission_requires_passed_technical_steps_and_passes_passed_to_task4[green]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:admission-requires-passed-technical-steps-and-passes-passed-to-task4",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "cabe0c6ce12e0dc44ebac1c5b68e83a4ad50610959317e643dfa89d536391974"
    },
    "tests/test_replay_governance.py::test_anchor_byte_tamper_is_rejected_by_document_authority": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:anchor-byte-tamper-is-rejected-by-document-authority",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "064100d12c37aa392a01a4259520d580f176afa929f89b082b7b956e12cfb3f1"
    },
    "tests/test_replay_governance.py::test_append_lock_is_exclusive": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:append-lock-is-exclusive",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "c86f343750cd04f28449456f111b2d49a8789f4465ffef5d2f30c10c1853d1ad"
    },
    "tests/test_replay_governance.py::test_append_requires_reviewed_candidate_ref": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:append-requires-reviewed-candidate-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "dd41dbc8a881af061a228523e9a20b961466c855e3c8867a9ed34b3f6565614c"
    },
    "tests/test_replay_governance.py::test_blob_size_is_checked_before_git_load": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:blob-size-is-checked-before-git-load",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "00abfbdeee92030f4d72b62dd462f6b27fc5b1d7576285b9f277a5ad0073e961"
    },
    "tests/test_replay_governance.py::test_bounded_git_io_cannot_deadlock_on_alternating_large_input_output": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:bounded-git-io-cannot-deadlock-on-alternating-large-input-output",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "4802fb7d254334591a13c640e68ac8cc89e953231508db5ec8e56065409b1004"
    },
    "tests/test_replay_governance.py::test_bounded_git_io_rejects_oversized_input_before_process_start": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:bounded-git-io-rejects-oversized-input-before-process-start",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "57e41e8fdebcb93f45cc5e0df3e921cf63ecc8a6c1849339c036ca545e10f72b"
    },
    "tests/test_replay_governance.py::test_candidate_preflight_allows_exact_run_phase_and_fixed_evidence": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:candidate-preflight-allows-exact-run-phase-and-fixed-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "36b140517beb09b1ddb99d63e167afe912652bf93f606711d4e35abb78019ecf"
    },
    "tests/test_replay_governance.py::test_candidate_reconstructs_prior_admissions_before_any_transition[green]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:candidate-reconstructs-prior-admissions-before-any-transition",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "cd7c145d7eac22419e44ffbc71542f6abdcf6eb0516dd2a97a991a2c2001b14d"
    },
    "tests/test_replay_governance.py::test_candidate_reconstructs_prior_admissions_before_any_transition[red]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:candidate-reconstructs-prior-admissions-before-any-transition",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "cd7c145d7eac22419e44ffbc71542f6abdcf6eb0516dd2a97a991a2c2001b14d"
    },
    "tests/test_replay_governance.py::test_cli_requires_exact_run_ref_and_exposes_no_latest_selector": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:cli-requires-exact-run-ref-and-exposes-no-latest-selector",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "0eeef2fa42d9f710939ed9047e1f9af9011275054015ff73a44499cbfcfe698e"
    },
    "tests/test_replay_governance.py::test_commit_graph_enforces_record_bound_and_follows_merge_parents": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:commit-graph-enforces-record-bound-and-follows-merge-parents",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "d57b5c3354e2bf905ee8e966bb02ccb4ab40da685dd703e6d222e892024d0a49"
    },
    "tests/test_replay_governance.py::test_commit_graph_load_is_single_and_bounded": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:commit-graph-load-is-single-and-bounded",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "6c5964d290a8a667eb0bdbaac7506d5f032ddea0d2d08ee34d0bd3bf3fa0baa4"
    },
    "tests/test_replay_governance.py::test_dirty_governed_inputs_allow_only_validated_evidence_paths": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:dirty-governed-inputs-allow-only-validated-evidence-paths",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "b06c03b9d68dc8349868551c5fbc583730167715d6e701659a8180fc94b8166f"
    },
    "tests/test_replay_governance.py::test_document_authority_cryptographically_pins_ledger_anchors": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:document-authority-cryptographically-pins-governance-inputs",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "8c85531117e8d0d3d3c624b5b0f9c91ea13679e9ecf22be51c3e06a79714cd83"
    },
    "tests/test_replay_governance.py::test_document_authority_is_lf_normalized": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:document-authority-is-lf-normalized",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "da426f07ee077c9d8ca79e40877449419dc9ab7230cedac10697a1e9ac5d71ee"
    },
    "tests/test_replay_governance.py::test_document_authority_is_scoped_and_classifications_are_exact": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:document-authority-is-scoped-and-classifications-are-exact",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-1",
        "owner_ref": "governance",
        "source_ast_sha256": "3e7eae63222daa6bf989f558d4fa98ae0ed3059f4e530788e24cc728caa6db21"
    },
    "tests/test_replay_governance.py::test_every_suffix_record_binds_commit_ancestor_monotonic_exact_prefix": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:every-suffix-record-binds-commit-ancestor-monotonic-exact-prefix",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "c111dfd33b301af9a9badd35c3380ce4c8641e770df9abc901aaf341273f70c4"
    },
    "tests/test_replay_governance.py::test_external_status_requires_green_predecessors_and_unique_dual_refs": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:external-status-requires-green-predecessors-and-unique-dual-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "f0f792279b35250664d46f52763566bcd9b82a172b60ea768adda811b7768cec"
    },
    "tests/test_replay_governance.py::test_git_witness_process_count_is_constant_for_multiple_suffixes": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:git-witness-process-count-is-constant-for-multiple-suffixes",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "8cca689635ba8e49abf72e3addc781a46d7a773d733e46c3217c397b0f7654bf"
    },
    "tests/test_replay_governance.py::test_governance_import_does_not_load_torch": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:governance-import-does-not-load-torch",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "4e19b9b7d2fcc894b6f8c5f9c42594b7c38d58e65627fb16b64f09c85163fcb9"
    },
    "tests/test_replay_governance.py::test_governance_ledgers_are_lf_normalized_without_live_git_dependency": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:governance-ledgers-are-lf-normalized-without-live-git-dependency",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "282162884a2f97c9ab08908da9942bf3de5d8131638cfcb71b39f91101a68cce"
    },
    "tests/test_replay_governance.py::test_governing_pointers_make_no_old_admission_claim": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:governing-pointers-make-no-old-admission-claim",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-1",
        "owner_ref": "governance",
        "source_ast_sha256": "623bcd127d0331bb99237f2860e9f81d1c3505b0f08fb8ec13644a62616d30bf"
    },
    "tests/test_replay_governance.py::test_hash_chain_has_small_external_bounds": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:hash-chain-has-small-external-bounds",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "5c231d897e6d33f0745efc7380fce046fb505864c86f96a46242fc261d26bb65"
    },
    "tests/test_replay_governance.py::test_hash_chain_rejects_broken_predecessor_and_truncation": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:hash-chain-rejects-broken-predecessor-and-truncation",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "772bd01c1e18f2d05bd0697efaddcfdcc7add8505dcb6954accda0c97f2c9b96"
    },
    "tests/test_replay_governance.py::test_hash_chain_rejects_duplicate_blank_noncanonical_and_nonfinite_rows": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:hash-chain-rejects-duplicate-blank-noncanonical-and-nonfinite-rows",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "93a67abc15dd8c0eb8c604b997de3bc9acffcacf30d8e281e0b51590e8425e57"
    },
    "tests/test_replay_governance.py::test_initial_replay_status_is_truthful_and_receipt_free": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:initial-replay-status-is-truthful-and-receipt-free",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "9e66aaba5b510b74fd7b8c9d00a31a78bae30453bb4fe4b34a0f3e6279e3d890"
    },
    "tests/test_replay_governance.py::test_invalidation_rejects_traversal_even_with_rehashed_record": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:invalidation-rejects-traversal-even-with-rehashed-record",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "3a2c79df61c07bf130fa17ae6ef7ee4fd500931089942c1e7c90f96b1023142e"
    },
    "tests/test_replay_governance.py::test_invalidations_bind_six_unchanged_historical_files": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:invalidations-bind-six-unchanged-historical-files",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "445b4c8f10a5dea1dc8458b3f0d8718224594f79f5422fe6b972108b9f46641e"
    },
    "tests/test_replay_governance.py::test_ledger_anchor_record_schema_must_be_a_strict_string": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:ledger-anchor-record-schema-must-be-a-strict-string",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "6adea71f802838734843b69d81ccb4ab51586ee9d83d5edc221fa984f9d3a6ce"
    },
    "tests/test_replay_governance.py::test_multi_admission_verify_aggregates_exact_paths_before_dirty_narrowing": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:multi-admission-verify-aggregates-exact-paths-before-dirty-narrowing",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "0b8d07913a9f47204b1ecbe80f6ab9b5c5cd4d87f0b7a303823ef89999d5fa49"
    },
    "tests/test_replay_governance.py::test_only_typed_admission_errors_are_wrapped": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:only-typed-admission-errors-are-wrapped",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "c6a7fcb14cd6440c70fe66a671403f17575c56fa60f20d96ee8a88e7d8c88ef7"
    },
    "tests/test_replay_governance.py::test_owner_import_preflight_rejects_dirty_code_before_loading": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:owner-import-preflight-rejects-dirty-code-before-loading",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "3992215d672410b07ebb5dfc4a08b8856a8ca8094e1f2231df730c8c53c8d3b1"
    },
    "tests/test_replay_governance.py::test_owner_loads_exact_reviewed_file_and_rejects_broad_error_alias": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:owner-loads-exact-reviewed-file-and-rejects-broad-error-alias",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "09a63d7b66581f6bb52fb5b6ce58a6975ba915f99800a915743e6fef7407e290"
    },
    "tests/test_replay_governance.py::test_post_write_callback_cannot_mutate_ledger_before_structural_verification": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:post-write-callback-cannot-mutate-ledger-before-structural-verification",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "c3516cef45c5b8ea8706c68fcd0afeacc90473aaf9360e9d1b9d3c357db962c3"
    },
    "tests/test_replay_governance.py::test_post_write_failure_rolls_back_exact_prior_bytes": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:post-write-failure-rolls-back-exact-prior-bytes",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "387ef02fa4253c1212917fa37b98228e528d6c9fb70c31d92d838df0909e5a90"
    },
    "tests/test_replay_governance.py::test_post_write_reconstructs_all_admitted_rows_and_preserves_path_union": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:post-write-reconstructs-all-admitted-rows-and-preserves-path-union",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "a13b37bd08d812350de85278d7dbbaae9a5608e11bfca2bcac123a98ffc90c89"
    },
    "tests/test_replay_governance.py::test_receipt_mutation_between_candidate_and_write_rolls_back_exact_bytes": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:receipt-mutation-between-candidate-and-write-rolls-back-exact-bytes",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "56157ba0a6172229f6854e68f39ccb6534d672d0840f2e7352546d7e635620b1"
    },
    "tests/test_replay_governance.py::test_red_candidate_without_prior_admissions_scans_dirty_status_once": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:red-candidate-without-prior-admissions-scans-dirty-status-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "e2bfa1b07db6ba3824de7d89907a0bb4a70b324fb8a967dac6bf05593ede0414"
    },
    "tests/test_replay_governance.py::test_red_suffix_resets_green_descendants": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:red-suffix-resets-green-descendants",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "420b2879fa979bf69e7da69ac63aa047e61d8d764894ea48dec819b57d3d1c92"
    },
    "tests/test_replay_governance.py::test_status_cli_derives_current_effective_status": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-cli-derives-current-effective-status",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "70d00e5ae3f84e421aa3b7c2a2db59c6b292fe2357faca3cb4d29c4ca65b892c"
    },
    "tests/test_replay_governance.py::test_status_enum_and_ref_types_fail_closed[gate-ref-type]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-enum-and-ref-types-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "b370750a915be882c4404627a1629ab876afd64247105fdd6e8d35b8840f23b2"
    },
    "tests/test_replay_governance.py::test_status_enum_and_ref_types_fail_closed[phase-type]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-enum-and-ref-types-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "b370750a915be882c4404627a1629ab876afd64247105fdd6e8d35b8840f23b2"
    },
    "tests/test_replay_governance.py::test_status_enum_and_ref_types_fail_closed[run-ref-type]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-enum-and-ref-types-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "b370750a915be882c4404627a1629ab876afd64247105fdd6e8d35b8840f23b2"
    },
    "tests/test_replay_governance.py::test_status_enum_and_ref_types_fail_closed[status-type]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-enum-and-ref-types-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "b370750a915be882c4404627a1629ab876afd64247105fdd6e8d35b8840f23b2"
    },
    "tests/test_replay_governance.py::test_status_records_require_exact_typed_content_addressed_fields[content]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-records-require-exact-typed-content-addressed-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "763f3aa622180cf906c10d8e1baa3ffa4cab53e3056c3e5336350a3d4645d427"
    },
    "tests/test_replay_governance.py::test_status_records_require_exact_typed_content_addressed_fields[extra]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-records-require-exact-typed-content-addressed-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "763f3aa622180cf906c10d8e1baa3ffa4cab53e3056c3e5336350a3d4645d427"
    },
    "tests/test_replay_governance.py::test_status_records_require_exact_typed_content_addressed_fields[missing]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-records-require-exact-typed-content-addressed-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "763f3aa622180cf906c10d8e1baa3ffa4cab53e3056c3e5336350a3d4645d427"
    },
    "tests/test_replay_governance.py::test_status_records_require_exact_typed_content_addressed_fields[wrong-type]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:status-records-require-exact-typed-content-addressed-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "763f3aa622180cf906c10d8e1baa3ffa4cab53e3056c3e5336350a3d4645d427"
    },
    "tests/test_replay_governance.py::test_suffix_git_witness_defects_fail_closed[non-commit]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:suffix-git-witness-defects-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "d459759007d3393d8fe04c8c090a4dbcd8b56bda908ed40f99d91bf82c4736d6"
    },
    "tests/test_replay_governance.py::test_suffix_git_witness_defects_fail_closed[non-monotonic]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:suffix-git-witness-defects-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "d459759007d3393d8fe04c8c090a4dbcd8b56bda908ed40f99d91bf82c4736d6"
    },
    "tests/test_replay_governance.py::test_suffix_git_witness_defects_fail_closed[not-ancestor]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:suffix-git-witness-defects-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "d459759007d3393d8fe04c8c090a4dbcd8b56bda908ed40f99d91bf82c4736d6"
    },
    "tests/test_replay_governance.py::test_suffix_git_witness_defects_fail_closed[wrong-prefix]": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:suffix-git-witness-defects-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "d459759007d3393d8fe04c8c090a4dbcd8b56bda908ed40f99d91bf82c4736d6"
    },
    "tests/test_replay_governance.py::test_suffix_transitions_reset_descendants_before_applying": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:suffix-transitions-reset-descendants-before-applying",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "39df192f049680a88a065f77a573e3df3a0acc0cd4e3be3ef72db286148cfea0"
    },
    "tests/test_replay_governance.py::test_tensor_type_hints_resolve_without_loading_torch": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:tensor-type-hints-resolve-without-loading-torch",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "13b4bd380bea496dc2505ca3bc02320a2b513bc5d617cdce48878b9f3d8a064b"
    },
    "tests/test_replay_governance.py::test_unavailable_admission_owner_is_injected_not_filesystem_dependent": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:unavailable-admission-owner-is-injected-not-filesystem-dependent",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "1651cac117d0b5f7e1ea36a572f8be0076cb0270df5302a8e2945d958054023f"
    },
    "tests/test_replay_governance.py::test_updater_rejects_swapped_gate_and_run_ref_namespaces": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:updater-rejects-swapped-gate-and-run-ref-namespaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "8632b86b48b44aef2856e59b3220418ad689a06981fdad3a521373d485acdf2a"
    },
    "tests/test_replay_governance.py::test_verify_chain_reconstructs_each_admitted_run": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:verify-chain-reconstructs-each-admitted-run",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "29bd42a9baf306e6fea32ad4ae8b63a4eabf88197af78ab304893aca69c00937"
    }
}


def _authority() -> dict[str, object]:
    return json.loads(
        (ROOT / "docs/DOCUMENT_AUTHORITY.json").read_text(encoding="utf-8")
    )


def test_document_authority_is_scoped_and_classifications_are_exact() -> None:
    authority = _authority()

    assert authority["schema"] == "cemm-hybrid-document-authority-v1"
    assert authority["scope"] == "hybrid_mvp/"
    assert authority["path_base"] == "hybrid_mvp/"
    assert authority["root_runtime_authority"] == "../AGENTS.md"
    assert authority["governing_documents"] == list(GOVERNING_DOCUMENTS)
    assert authority["superseded_execution_claims"] == list(
        SUPERSEDED_EXECUTION_CLAIMS
    )
    assert authority["historical_evidence"] == list(HISTORICAL_EVIDENCE)
    assert authority["generated_artifacts_are_authority"] is False
    assert authority["root_adoption_requires_separate_review"] is True

    classifications = (
        set(GOVERNING_DOCUMENTS),
        set(SUPERSEDED_EXECUTION_CLAIMS),
        set(HISTORICAL_EVIDENCE),
    )
    for index, current in enumerate(classifications):
        for other in classifications[index + 1 :]:
            assert current.isdisjoint(other)

    for relative in (
        *GOVERNING_DOCUMENTS,
        *SUPERSEDED_EXECUTION_CLAIMS,
        *HISTORICAL_EVIDENCE,
    ):
        assert (ROOT / relative.rstrip("/")).exists(), relative

    root_authority = (ROOT / str(authority["root_runtime_authority"])).resolve()
    assert root_authority == (ROOT.parent / "AGENTS.md").resolve()
    assert root_authority.is_file()


def test_governing_pointers_make_no_old_admission_claim() -> None:
    obsolete_claims = (
        re.compile(r"\bM1\s*[-–]\s*M3\s+are\s+complete\b", re.IGNORECASE),
        re.compile(
            r"\bM4\s+Tasks?\s+(?:1\s*[-–]\s*)?4\s+"
            r"(?:is|are)\s+(?:complete|implemented)\b",
            re.IGNORECASE,
        ),
    )

    for relative in ACTIVE_POINTERS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "proposed for user review" not in text.casefold()
        for pattern in obsolete_claims:
            assert pattern.search(text) is None, relative


STATUS_FIELDS = {
    "schema",
    "sequence",
    "predecessor_ref",
    "source_base",
    "phase",
    "status",
    "admission_gate_result_ref",
    "admission_run_ref",
    "rationale",
    "record_ref",
}

INVALIDATION_FIELDS = {
    "schema",
    "sequence",
    "predecessor_ref",
    "source_base",
    "subject",
    "subject_sha256",
    "disposition",
    "rationale",
    "record_ref",
}

INITIAL_STATUS = {
    "G0": "pending",
    "R1": "red",
    "R2": "red",
    "R3": "red",
    "R4": "red",
    "R5": "red",
    "R6": "red",
    "R7": "red",
    "R8": "red",
}

INVALIDATED_RECEIPTS = {
    "artifacts/validation/MILESTONE_RECEIPT.json":
        "f6df34c05b9cbbdd5b5864ad5fb11bfc7c530105753117e05e80a2da642b6aa7",
    "artifacts/validation/M2_PROPOSAL_RECEIPT.json":
        "c01945cfb2d482f9a43cbf4837284d65a6659914718b2d3c4e5629db4160f5ae",
    "artifacts/validation/M3_MILESTONE_RECEIPT.json":
        "6ab45fa606f7ce9ff99e7d779aacc84a7734abde858e2cff1a96225f91005c5e",
    "artifacts/validation/REPRODUCIBILITY.json":
        "330e214f5fa2cf301dd5d0831645eed0e7c61e4e9eadb1917a16c760b84f9768",
    "artifacts/training_receipt.json":
        "7d03f5151f1750b077f44c975095e9db99510d9b4220e1ae00e010e074066517",
    "artifacts/evaluation/CEMM_EVALUATION.json":
        "4caf7f65fd9d30ddeedf455e81b10194132808d75a274dea49229878ca09dc61",
}


def _ledger(name: str) -> Path:
    return ROOT / "governance" / name


def _canonical_jsonl(records: list[dict[str, object]]) -> bytes:
    return b"".join(
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        for record in records
    )


def _anchor_for(raw: bytes, records: list[dict[str, object]]) -> LedgerAnchor:
    return LedgerAnchor(
        ledger_path="governance/test.jsonl",
        record_schema=str(records[0]["schema"]),
        initial_count=len(records),
        genesis_ref=str(records[0]["record_ref"]),
        initial_head_ref=str(records[-1]["record_ref"]),
        initial_bytes_size=len(raw),
        initial_bytes_sha256=hashlib.sha256(raw).hexdigest(),
        source_base=str(records[0]["source_base"]),
    )


def _append_status(
    records: list[dict[str, object]],
    *,
    phase: str,
    status: object,
    gate_ref: object = None,
    run_ref: object = None,
    source_base: str = "a" * 40,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": "cemm-replay-status-record-v1",
        "sequence": len(records),
        "predecessor_ref": records[-1]["record_ref"],
        "source_base": source_base,
        "phase": phase,
        "status": status,
        "admission_gate_result_ref": gate_ref,
        "admission_run_ref": run_ref,
        "rationale": "test transition",
    }
    record["record_ref"] = expected_record_ref(record)
    records.append(record)
    return record


def _initial_status_records() -> list[dict[str, object]]:
    path = _ledger("replay_status.jsonl")
    records = read_hash_chain(path)
    return [dict(record) for record in records[: load_ledger_anchor(path).initial_count]]


def _order_ancestor(order: dict[str, int]):
    return lambda ancestor, descendant: order[ancestor] <= order[descendant]


def _pure_read(
    path: Path,
    anchor: LedgerAnchor,
    *,
    blobs: dict[str, bytes] | None = None,
    kinds: dict[str, str] | None = None,
    head_ref: str | None = None,
    order: dict[str, int] | None = None,
) -> tuple[dict[str, object], ...]:
    return governance._read_hash_chain_for_test(
        path,
        anchor,
        committed_blobs=blobs or {},
        commit_kinds=kinds or {},
        head_ref=head_ref,
        is_ancestor=_order_ancestor(order) if order is not None else None,
    )


def _load_update_script():
    path = ROOT / "scripts" / "update_replay_status.py"
    spec = importlib.util.spec_from_file_location("task2_update_replay_status", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _receipt(
    *,
    phase: str,
    gate_ref: str,
    run_ref: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        gate_result_ref=gate_ref,
        run_ref=run_ref,
        phase=phase,
        tier="admission",
        fresh=True,
        step_results=(SimpleNamespace(disposition="passed"),),
    )


def test_initial_replay_status_is_truthful_and_receipt_free() -> None:
    records = _initial_status_records()
    assert effective_replay_status(records) == INITIAL_STATUS
    assert len(records) == len(INITIAL_STATUS)
    assert [record["phase"] for record in records] == list(INITIAL_STATUS)
    assert all(set(record) == STATUS_FIELDS for record in records)
    assert all(record["admission_gate_result_ref"] is None for record in records)
    assert all(record["admission_run_ref"] is None for record in records)


def test_invalidations_bind_six_unchanged_historical_files() -> None:
    path = _ledger("receipt_invalidations.jsonl")
    all_records = read_hash_chain(path)
    records = all_records[: load_ledger_anchor(path).initial_count]
    assert len(records) == 6
    assert all(set(record) == INVALIDATION_FIELDS for record in records)
    assert {record["subject"]: record["subject_sha256"] for record in records} == (
        INVALIDATED_RECEIPTS
    )
    for record in records:
        verify_file_invalidation(ROOT, record)


def test_document_authority_cryptographically_pins_ledger_anchors() -> None:
    pin = _authority()["governance_ledger_anchors"]
    assert pin["path"] == "governance/ledger_anchors.json"
    anchor_path = ROOT / pin["path"]
    assert hashlib.sha256(anchor_path.read_bytes()).hexdigest() == pin["sha256"]

    inventory_pin = _authority()["test_inventory"]
    assert inventory_pin["path"] == "governance/test_inventory.json"
    inventory_path = ROOT / inventory_pin["path"]
    assert (
        hashlib.sha256(inventory_path.read_bytes()).hexdigest()
        == inventory_pin["sha256"]
    )



def test_document_authority_is_lf_normalized() -> None:
    assert b"\r\n" not in (ROOT / "docs" / "DOCUMENT_AUTHORITY.json").read_bytes()


def test_ledger_anchor_record_schema_must_be_a_strict_string() -> None:
    anchor = load_ledger_anchor(_ledger("replay_status.jsonl"))
    values = dict(vars(anchor))
    values["record_schema"] = []
    with pytest.raises(GovernanceError, match="record_schema"):
        LedgerAnchor(**values)


@pytest.mark.parametrize(
    "mutation",
    ["missing", "extra", "wrong_type", "content"],
    ids=["missing", "extra", "wrong-type", "content"],
)
def test_status_records_require_exact_typed_content_addressed_fields(
    tmp_path: Path, mutation: str
) -> None:
    source = _ledger("replay_status.jsonl")
    records = _initial_status_records()
    anchor = load_ledger_anchor(source)
    if mutation == "missing":
        records[0].pop("rationale")
    elif mutation == "extra":
        records[0]["unexpected"] = "not allowed"
    elif mutation == "wrong_type":
        records[0]["sequence"] = False
    else:
        records[0]["rationale"] = "rewritten without updating its content ref"
    tampered = tmp_path / "replay_status.jsonl"
    tampered.write_bytes(_canonical_jsonl(records))
    with pytest.raises(GovernanceError):
        _pure_read(tampered, anchor)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phase", []),
        ("status", []),
        ("admission_gate_result_ref", True),
        ("admission_run_ref", 7),
    ],
    ids=["phase-type", "status-type", "gate-ref-type", "run-ref-type"],
)
def test_status_enum_and_ref_types_fail_closed(
    tmp_path: Path, field: str, value: object
) -> None:
    source = _ledger("replay_status.jsonl")
    records = _initial_status_records()
    records[0][field] = value
    records[0]["record_ref"] = expected_record_ref(records[0])
    path = tmp_path / "bad-type.jsonl"
    path.write_bytes(_canonical_jsonl(records))
    with pytest.raises(GovernanceError):
        _pure_read(path, load_ledger_anchor(source))


def test_admission_refs_require_exact_gate_and_run_namespaces() -> None:
    records = _initial_status_records()
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref="run:" + "1" * 24,
        run_ref="gate_result:" + "2" * 24,
    )
    with pytest.raises(GovernanceError, match="admission_gate_result_ref"):
        effective_replay_status(records)


def test_hash_chain_rejects_duplicate_blank_noncanonical_and_nonfinite_rows(
    tmp_path: Path,
) -> None:
    source = _ledger("replay_status.jsonl")
    raw = source.read_bytes()
    anchor = load_ledger_anchor(source)
    corruptions = (
        raw.replace(b'"phase":"G0"', b'"phase":"G0","phase":"G0"', 1),
        raw.replace(b"\n", b"\n\n", 1),
        raw.replace(b'{"admission_gate_result_ref"', b'{ "admission_gate_result_ref"', 1),
        raw.replace(b'"sequence":0', b'"sequence":NaN', 1),
    )
    for index, corrupted in enumerate(corruptions):
        path = tmp_path / f"corrupted-{index}.jsonl"
        path.write_bytes(corrupted)
        with pytest.raises(GovernanceError):
            _pure_read(path, anchor)


def test_hash_chain_rejects_broken_predecessor_and_truncation(tmp_path: Path) -> None:
    source = _ledger("replay_status.jsonl")
    anchor = load_ledger_anchor(source)
    records = _initial_status_records()
    records[2]["predecessor_ref"] = records[0]["record_ref"]
    records[2]["record_ref"] = expected_record_ref(records[2])
    broken = tmp_path / "broken.jsonl"
    broken.write_bytes(_canonical_jsonl(records))
    with pytest.raises(GovernanceError, match="predecessor"):
        _pure_read(broken, anchor)
    truncated = tmp_path / "truncated.jsonl"
    truncated.write_bytes(_canonical_jsonl(_initial_status_records()[:-1]))
    with pytest.raises(GovernanceError, match="truncated"):
        _pure_read(truncated, anchor)


def test_anchor_byte_tamper_is_rejected_by_document_authority(tmp_path: Path) -> None:
    root = tmp_path / "hybrid_mvp"
    (root / "docs").mkdir(parents=True)
    (root / "governance").mkdir()
    authority = copy.deepcopy(_authority())
    (root / "docs" / "DOCUMENT_AUTHORITY.json").write_text(
        json.dumps(authority), encoding="utf-8"
    )
    anchor_bytes = _ledger("ledger_anchors.json").read_bytes() + b" "
    (root / "governance" / "ledger_anchors.json").write_bytes(anchor_bytes)
    (root / "governance" / "replay_status.jsonl").write_bytes(
        _ledger("replay_status.jsonl").read_bytes()
    )
    with pytest.raises(GovernanceError, match="document authority"):
        load_ledger_anchor(root / "governance" / "replay_status.jsonl")


def test_invalidation_rejects_traversal_even_with_rehashed_record() -> None:
    record = dict(read_hash_chain(_ledger("receipt_invalidations.jsonl"))[0])
    record["subject"] = "artifacts/../docs/DOCUMENT_AUTHORITY.json"
    record["record_ref"] = expected_record_ref(record)
    with pytest.raises(GovernanceError, match="safe relative path"):
        verify_file_invalidation(ROOT, record)


def test_every_suffix_record_binds_commit_ancestor_monotonic_exact_prefix(
    tmp_path: Path,
) -> None:
    initial = _initial_status_records()
    initial_raw = _canonical_jsonl(initial)
    anchor = _anchor_for(initial_raw, initial)
    first_base, second_base, head = "a" * 40, "b" * 40, "c" * 40
    records = [dict(record) for record in initial]
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref="gate_result:" + "1" * 24,
        run_ref="run:" + "1" * 24,
        source_base=first_base,
    )
    first_prefix = _canonical_jsonl(records)
    _append_status(
        records,
        phase="R1",
        status="externally_blocked",
        gate_ref="gate_result:" + "2" * 24,
        run_ref="run:" + "2" * 24,
        source_base=second_base,
    )
    complete = _canonical_jsonl(records)
    path = tmp_path / "replay_status.jsonl"
    path.write_bytes(complete)
    order = {str(anchor.source_base): 0, first_base: 1, second_base: 2, head: 3}
    assert _pure_read(
        path,
        anchor,
        blobs={first_base: initial_raw, second_base: first_prefix},
        kinds={str(anchor.source_base): "commit", first_base: "commit", second_base: "commit", head: "commit"},
        head_ref=head,
        order=order,
    ) == tuple(records)


@pytest.mark.parametrize(
    "defect",
    ["non_commit", "not_ancestor", "non_monotonic", "wrong_prefix"],
    ids=["non-commit", "not-ancestor", "non-monotonic", "wrong-prefix"],
)
def test_suffix_git_witness_defects_fail_closed(tmp_path: Path, defect: str) -> None:
    initial = _initial_status_records()
    initial_raw = _canonical_jsonl(initial)
    anchor = _anchor_for(initial_raw, initial)
    base, head = "a" * 40, "c" * 40
    records = [dict(record) for record in initial]
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref="gate_result:" + "3" * 24,
        run_ref="run:" + "3" * 24,
        source_base=base,
    )
    path = tmp_path / "replay_status.jsonl"
    path.write_bytes(_canonical_jsonl(records))
    kinds = {str(anchor.source_base): "commit", base: "commit", head: "commit"}
    order = {str(anchor.source_base): 0, base: 1, head: 2}
    blobs = {base: initial_raw}
    if defect == "non_commit":
        kinds[base] = "tree"
    elif defect == "not_ancestor":
        order[base] = 3
    elif defect == "non_monotonic":
        order[str(anchor.source_base)] = 2
        order[base] = 1
    else:
        blobs[base] = initial_raw + b" "
    with pytest.raises(GovernanceError):
        _pure_read(path, anchor, blobs=blobs, kinds=kinds, head_ref=head, order=order)


def test_hash_chain_has_small_external_bounds(tmp_path: Path) -> None:
    too_many = tmp_path / "too-many.jsonl"
    too_many.write_bytes(b"{}\n" * (governance.MAX_LEDGER_RECORDS + 1))
    with pytest.raises(GovernanceError, match="too many records"):
        governance.parse_and_validate_records(too_many.read_bytes())
    line_too_long = tmp_path / "line-too-long.jsonl"
    line_too_long.write_bytes(b"{" + b" " * governance.MAX_LEDGER_LINE_BYTES + b"}\n")
    with pytest.raises(GovernanceError, match="row exceeds"):
        governance.parse_and_validate_records(line_too_long.read_bytes())


def test_suffix_transitions_reset_descendants_before_applying() -> None:
    records = _initial_status_records()
    _append_status(records, phase="G0", status="green", gate_ref="gate_result:" + "4" * 24, run_ref="run:" + "4" * 24)
    _append_status(records, phase="R1", status="green", gate_ref="gate_result:" + "5" * 24, run_ref="run:" + "5" * 24, source_base="b" * 40)
    assert effective_replay_status(records)["R1"] == "green"
    _append_status(records, phase="G0", status="green", gate_ref="gate_result:" + "6" * 24, run_ref="run:" + "6" * 24, source_base="c" * 40)
    assert effective_replay_status(records) == {"G0": "green", **{f"R{i}": "red" for i in range(1, 9)}}


def test_external_status_requires_green_predecessors_and_unique_dual_refs() -> None:
    records = _initial_status_records()
    _append_status(records, phase="R1", status="externally_blocked", gate_ref="gate_result:" + "7" * 24, run_ref="run:" + "7" * 24)
    with pytest.raises(GovernanceError, match="dependency"):
        effective_replay_status(records)

    records = _initial_status_records()
    gate_ref, run_ref = "gate_result:" + "8" * 24, "run:" + "8" * 24
    _append_status(records, phase="G0", status="externally_blocked", gate_ref=gate_ref, run_ref=run_ref)
    _append_status(records, phase="G0", status="green", gate_ref=gate_ref, run_ref="run:" + "9" * 24, source_base="b" * 40)
    with pytest.raises(GovernanceError, match="gate result.*already consumed"):
        effective_replay_status(records)


def test_red_suffix_resets_green_descendants() -> None:
    records = _initial_status_records()
    _append_status(records, phase="G0", status="green", gate_ref="gate_result:" + "a" * 24, run_ref="run:" + "a" * 24)
    _append_status(records, phase="R1", status="green", gate_ref="gate_result:" + "b" * 24, run_ref="run:" + "b" * 24, source_base="b" * 40)
    _append_status(records, phase="G0", status="red", source_base="c" * 40)
    assert effective_replay_status(records) == INITIAL_STATUS | {"G0": "red"}


def test_governance_ledgers_are_lf_normalized_without_live_git_dependency() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "governance/*.json text eol=lf" in attributes
    assert "governance/*.jsonl text eol=lf" in attributes
    for name in ("replay_status.jsonl", "receipt_invalidations.jsonl", "ledger_anchors.json"):
        assert b"\r\n" not in _ledger(name).read_bytes()


def test_status_cli_derives_current_effective_status() -> None:
    expected = effective_replay_status(read_hash_chain(_ledger("replay_status.jsonl")))
    completed = subprocess.run(
        [sys.executable, "scripts/update_replay_status.py", "--verify-chain"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    for phase, status in expected.items():
        assert f"{phase}={status}" in completed.stdout


def test_unavailable_admission_owner_is_injected_not_filesystem_dependent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    monkeypatch.setattr(
        script,
        "_load_admission_owner",
        lambda **_kwargs: (_ for _ in ()).throw(GovernanceError("validated admission receipt owner is unavailable")),
    )
    with pytest.raises(GovernanceError, match="owner is unavailable"):
        script._validated_admission("G0", "green", run_ref="run:" + "0" * 24)


def test_owner_import_preflight_rejects_dirty_code_before_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    monkeypatch.setattr(
        script, "_dirty_hybrid_paths", lambda: frozenset({"src/runtime.py"})
    )
    with pytest.raises(GovernanceError, match="dirty governed input"):
        script._load_admission_owner(
            phase="G0", run_ref="run:" + "1" * 24
        )


def test_candidate_preflight_allows_exact_run_phase_and_fixed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    run_ref = "run:" + "1" * 24
    dirty = frozenset(
        {
            "artifacts/validation/runs/" + "1" * 24 + ".json",
            "artifacts/validation/G0_ADMISSION_RECEIPT.json",
            "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
            "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
        }
    )
    monkeypatch.setattr(script, "_dirty_hybrid_paths", lambda: dirty)
    script._preflight_owner_import("G0", run_ref)


def test_owner_loads_exact_reviewed_file_and_rejects_broad_error_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    gate_path = scripts / "validation_gate.py"
    gate_path.write_text(
        "class AdmissionValidationError(Exception):\n"
        "    pass\n"
        "def load_verified_admission_receipt(**kwargs):\n"
        "    return kwargs\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(script, "ROOT", tmp_path)
    monkeypatch.setattr(script, "_dirty_hybrid_paths", lambda: frozenset())
    monkeypatch.setitem(sys.modules, "validation_gate", SimpleNamespace(
        AdmissionValidationError=Exception,
        load_verified_admission_receipt=lambda **_kwargs: None,
    ))
    owner = script._load_admission_owner(
        phase="G0", run_ref="run:" + "1" * 24
    )
    assert Path(owner.loader.__code__.co_filename).resolve() == gate_path.resolve()

    gate_path.write_text(
        "AdmissionValidationError = ValueError\n"
        "def load_verified_admission_receipt(**kwargs):\n"
        "    return kwargs\n",
        encoding="utf-8",
    )
    with pytest.raises(TypeError, match="AdmissionValidationError"):
        script._load_admission_owner(
            phase="G0", run_ref="run:" + "1" * 24
        )


def test_only_typed_admission_errors_are_wrapped() -> None:
    script = _load_update_script()
    run_ref = "run:" + "0" * 24

    class AdmissionValidationError(Exception):
        pass

    def typed_failure(**_kwargs):
        raise AdmissionValidationError("bad receipt")

    owner = script.AdmissionOwner(AdmissionValidationError, typed_failure)
    with pytest.raises(GovernanceError, match="admission receipt was rejected"):
        script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)

    def programming_failure(**_kwargs):
        raise RuntimeError("implementation defect")

    owner = script.AdmissionOwner(AdmissionValidationError, programming_failure)
    with pytest.raises(RuntimeError, match="implementation defect"):
        script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)


@pytest.mark.parametrize(
    "ledger_status",
    ["green", "externally_blocked"],
    ids=["green", "externally-blocked"],
)
def test_admission_requires_passed_technical_steps_and_passes_passed_to_task4(
    ledger_status: str,
) -> None:
    script = _load_update_script()
    gate_ref, run_ref = "gate_result:" + "b" * 24, "run:" + "b" * 24
    receipt = _receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref)
    receipt.step_results = (SimpleNamespace(disposition="failed"),)
    expected_statuses: list[str] = []

    def loader(**kwargs):
        expected_statuses.append(kwargs["expected_status"])
        return receipt, ()

    owner = script.AdmissionOwner(ValueError, loader)
    with pytest.raises(GovernanceError, match="non-passed"):
        script._validated_admission(
            "G0", ledger_status, run_ref=run_ref, owner=owner
        )
    assert expected_statuses == ["passed"]


def test_updater_rejects_swapped_gate_and_run_ref_namespaces() -> None:
    script = _load_update_script()
    receipt = _receipt(
        phase="G0",
        gate_ref="run:" + "b" * 24,
        run_ref="gate_result:" + "b" * 24,
    )
    owner = script.AdmissionOwner(ValueError, lambda **_kwargs: (receipt, ()))
    with pytest.raises(TypeError, match="gate_result_ref"):
        script._validated_admission(
            "G0", "green", run_ref="run:" + "b" * 24, owner=owner
        )


def test_admission_binding_stores_gate_and_exact_run_refs() -> None:
    script = _load_update_script()
    gate_ref, run_ref = "gate_result:" + "c" * 24, "run:" + "c" * 24
    receipt = _receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref)
    owner = script.AdmissionOwner(
        ValueError,
        lambda **_kwargs: (receipt, ("artifacts/validation/runs/current.json",)),
    )
    validated, paths = script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)
    assert validated is receipt
    assert paths == ("artifacts/validation/runs/current.json",)
    record = governance.make_status_record(
        _initial_status_records(),
        source_base="a" * 40,
        phase="G0",
        status="green",
        admission_gate_result_ref=receipt.gate_result_ref,
        admission_run_ref=receipt.run_ref,
        rationale="test",
    )
    assert record["admission_gate_result_ref"] == gate_ref
    assert record["admission_run_ref"] == run_ref


def test_verify_chain_reconstructs_each_admitted_run() -> None:
    script = _load_update_script()
    records = _initial_status_records()
    gate_ref, run_ref = "gate_result:" + "d" * 24, "run:" + "d" * 24
    _append_status(records, phase="G0", status="green", gate_ref=gate_ref, run_ref=run_ref)
    calls: list[str | None] = []

    def loader(**kwargs):
        calls.append(kwargs["run_ref"])
        return (_receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref), ())

    owner = script.AdmissionOwner(ValueError, loader)
    script._verify_admitted_runs(records, owner=owner)
    assert calls == [run_ref]




def test_multi_admission_verify_aggregates_exact_paths_before_dirty_narrowing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    records = _initial_status_records()
    g_gate, g_run = "gate_result:" + "2" * 24, "run:" + "2" * 24
    r_gate, r_run = "gate_result:" + "3" * 24, "run:" + "3" * 24
    _append_status(
        records, phase="G0", status="green", gate_ref=g_gate, run_ref=g_run
    )
    _append_status(
        records,
        phase="R1",
        status="green",
        gate_ref=r_gate,
        run_ref=r_run,
        source_base="b" * 40,
    )
    paths_by_phase = {
        "G0": (
            "artifacts/validation/runs/" + "2" * 24 + ".json",
            "artifacts/validation/G0_ADMISSION_RECEIPT.json",
        ),
        "R1": (
            "artifacts/validation/runs/" + "3" * 24 + ".json",
            "artifacts/validation/R1_ADMISSION_RECEIPT.json",
        ),
    }

    def loader(**kwargs):
        phase = kwargs["phase"]
        gate_ref, run_ref = (
            (g_gate, g_run) if phase == "G0" else (r_gate, r_run)
        )
        return _receipt(phase=phase, gate_ref=gate_ref, run_ref=run_ref), paths_by_phase[phase]

    owner = script.AdmissionOwner(ValueError, loader)
    dirty = frozenset(
        {
            *paths_by_phase["G0"],
            *paths_by_phase["R1"],
            "governance/replay_status.jsonl",
        }
    )
    monkeypatch.setattr(script, "_dirty_hybrid_paths", lambda: dirty)
    script._preflight_owner_import("G0", g_run, authenticated_ledger=True)
    allowed = script._verify_admitted_runs(
        records,
        owner=owner,
        dirty_paths=dirty,
        require_evidence_files=False,
    )
    assert allowed == frozenset((*paths_by_phase["G0"], *paths_by_phase["R1"]))




def test_post_write_reconstructs_all_admitted_rows_and_preserves_path_union() -> None:
    script = _load_update_script()
    records = _initial_status_records()
    g_gate, g_run = "gate_result:" + "6" * 24, "run:" + "6" * 24
    r_gate, r_run = "gate_result:" + "7" * 24, "run:" + "7" * 24
    _append_status(records, phase="G0", status="green", gate_ref=g_gate, run_ref=g_run)
    _append_status(
        records,
        phase="R1",
        status="green",
        gate_ref=r_gate,
        run_ref=r_run,
        source_base="b" * 40,
    )
    paths_by_run = {
        g_run: ("artifacts/validation/runs/" + "6" * 24 + ".json",),
        r_run: ("artifacts/validation/runs/" + "7" * 24 + ".json",),
    }
    calls: list[str] = []

    def loader(**kwargs):
        run_ref = kwargs["run_ref"]
        calls.append(run_ref)
        phase, gate_ref = ("G0", g_gate) if run_ref == g_run else ("R1", r_gate)
        return _receipt(phase=phase, gate_ref=gate_ref, run_ref=run_ref), paths_by_run[run_ref]

    owner = script.AdmissionOwner(ValueError, loader)
    allowed = tuple(sorted((*paths_by_run[g_run], *paths_by_run[r_run])))
    callback = script._make_post_write_validator(
        records=records,
        evidence_paths=allowed,
        source_base="a" * 40,
        prior_bytes=b"prior\n",
        owner=owner,
        dirty_loader=lambda: frozenset({*allowed, "governance/replay_status.jsonl"}),
        head_loader=lambda: "a" * 40,
        committed_loader=lambda _source_base: b"prior\n",
        require_evidence_files=False,
    )

    callback()
    assert calls == [g_run, r_run]


@pytest.mark.parametrize(
    "candidate_status",
    ["red", "green"],
    ids=["red", "green"],
)
def test_candidate_reconstructs_prior_admissions_before_any_transition(
    monkeypatch: pytest.MonkeyPatch,
    candidate_status: str,
) -> None:
    script = _load_update_script()
    records = _initial_status_records()
    prior_gate = "gate_result:" + "4" * 24
    prior_run = "run:" + "4" * 24
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref=prior_gate,
        run_ref=prior_run,
    )
    new_run = "run:" + "5" * 24 if candidate_status == "green" else None
    owner_loads = 0

    def load_owner(**_kwargs):
        nonlocal owner_loads
        owner_loads += 1

        def reject_prior(**kwargs):
            if kwargs["run_ref"] == prior_run:
                raise ValueError("prior receipt is no longer valid")
            raise AssertionError("new receipt must not be read after prior rejection")

        return script.AdmissionOwner(ValueError, reject_prior)

    monkeypatch.setattr(script, "read_hash_chain", lambda _path: records)
    monkeypatch.setattr(script, "_dirty_hybrid_paths", frozenset)
    monkeypatch.setattr(script, "_load_admission_owner", load_owner)
    args = SimpleNamespace(phase="R1", status=candidate_status, run_ref=new_run)

    with pytest.raises(GovernanceError, match="receipt was rejected"):
        script._candidate(args)
    assert owner_loads == 1




def test_red_candidate_without_prior_admissions_scans_dirty_status_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    records = _initial_status_records()
    dirty_scans = 0

    def dirty_paths() -> frozenset[str]:
        nonlocal dirty_scans
        dirty_scans += 1
        return frozenset()

    monkeypatch.setattr(script, "read_hash_chain", lambda _path: records)
    monkeypatch.setattr(script, "_dirty_hybrid_paths", dirty_paths)
    monkeypatch.setattr(
        script,
        "_require_committed_current_prefix",
        lambda: ("9" * 40, b"prior\n"),
    )

    script._candidate(SimpleNamespace(phase="G0", status="red", run_ref=None))
    assert dirty_scans == 1
def test_cli_requires_exact_run_ref_and_exposes_no_latest_selector() -> None:
    script = _load_update_script()
    with pytest.raises(SystemExit):
        script._parser().parse_args(["--admit-latest"])
    with pytest.raises(GovernanceError, match="exact --run-ref"):
        script._validate_transition_args(
            SimpleNamespace(phase="G0", status="green", run_ref=None)
        )
    script._validate_transition_args(
        SimpleNamespace(
            phase="G0",
            status="green",
            run_ref="run:" + "1" * 24,
        )
    )
    with pytest.raises(GovernanceError, match="only valid for admission"):
        script._validate_transition_args(
            SimpleNamespace(
                phase="G0",
                status="red",
                run_ref="run:" + "1" * 24,
            )
        )

def test_append_requires_reviewed_candidate_ref() -> None:
    script = _load_update_script()
    record = {"record_ref": "governance_record:" + "e" * 24}
    with pytest.raises(GovernanceError, match="--expect-record-ref is required"):
        script._require_expected_record_ref(record, None)
    with pytest.raises(GovernanceError, match="reviewed candidate changed"):
        script._require_expected_record_ref(record, "governance_record:" + "f" * 24)
    script._require_expected_record_ref(record, str(record["record_ref"]))


def test_dirty_governed_inputs_allow_only_validated_evidence_paths(tmp_path: Path) -> None:
    script = _load_update_script()
    allowed = script._normalize_allowed_evidence_paths(
        ("artifacts/validation/runs/current.json",),
        root=tmp_path,
        require_files=False,
    )
    script._reject_dirty_governed_inputs(
        {"artifacts/validation/runs/current.json"}, allowed
    )
    with pytest.raises(GovernanceError, match="dirty governed input"):
        script._reject_dirty_governed_inputs({"src/runtime.py"}, allowed)
    with pytest.raises(GovernanceError, match="unsafe validated evidence path"):
        script._normalize_allowed_evidence_paths(("../runtime.py",), root=tmp_path, require_files=False)


def test_append_lock_is_exclusive(tmp_path: Path) -> None:
    script = _load_update_script()
    lock = tmp_path / "status.lock"
    lock.write_text("held", encoding="utf-8")
    with pytest.raises(GovernanceError, match="another status update"):
        with script._exclusive_append_lock(lock):
            pass


def test_post_write_failure_rolls_back_exact_prior_bytes(tmp_path: Path) -> None:
    script = _load_update_script()
    ledger = tmp_path / "status.jsonl"
    prior = b'{"prior":true}\n'
    ledger.write_bytes(prior)

    def fail_verification(_path: Path):
        raise RuntimeError("post-write verifier failed")

    with pytest.raises(RuntimeError, match="post-write verifier failed"):
        script._append_exact(
            {"record_ref": "governance_record:" + "1" * 24},
            prior,
            ledger_path=ledger,
            verifier=fail_verification,
            post_write_validate=lambda: None,
        )
    assert ledger.read_bytes() == prior



def test_post_write_callback_cannot_mutate_ledger_before_structural_verification(
    tmp_path: Path,
) -> None:
    script = _load_update_script()
    ledger = tmp_path / "status.jsonl"
    prior = b'{"prior":true}\n'
    ledger.write_bytes(prior)
    verifier_called = False

    def mutate_ledger() -> None:
        with ledger.open("ab") as handle:
            handle.write(b'{"unauthorized":true}\n')

    def verifier(_path: Path) -> None:
        nonlocal verifier_called
        verifier_called = True

    with pytest.raises(GovernanceError, match="exact candidate bytes"):
        script._append_exact(
            {"record_ref": "governance_record:" + "1" * 24},
            prior,
            ledger_path=ledger,
            verifier=verifier,
            post_write_validate=mutate_ledger,
        )
    assert verifier_called is False
    assert ledger.read_bytes() == prior

def test_receipt_mutation_between_candidate_and_write_rolls_back_exact_bytes(
    tmp_path: Path,
) -> None:
    script = _load_update_script()
    ledger = tmp_path / "status.jsonl"
    prior = b'{"prior":true}\n'
    ledger.write_bytes(prior)
    gate_ref, run_ref = "gate_result:" + "f" * 24, "run:" + "f" * 24
    receipt = _receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref)
    evidence_paths = ("artifacts/validation/runs/" + "f" * 24 + ".json",)
    owner = script.AdmissionOwner(ValueError, lambda **_kwargs: (receipt, evidence_paths))
    records = _initial_status_records()
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref=gate_ref,
        run_ref=run_ref,
    )
    script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)
    callback = script._make_post_write_validator(
        records=records,
        evidence_paths=evidence_paths,
        source_base="a" * 40,
        prior_bytes=prior,
        owner=owner,
        dirty_loader=lambda: frozenset({"governance/replay_status.jsonl"}),
        head_loader=lambda: "a" * 40,
        committed_loader=lambda _source_base: prior,
        require_evidence_files=False,
    )
    receipt.step_results = (SimpleNamespace(disposition="failed"),)

    with pytest.raises(GovernanceError, match="non-passed"):
        script._append_exact(
            {"record_ref": "governance_record:" + "1" * 24},
            prior,
            ledger_path=ledger,
            verifier=lambda _path: None,
            post_write_validate=callback,
        )
    assert ledger.read_bytes() == prior




def test_bounded_git_io_cannot_deadlock_on_alternating_large_input_output() -> None:
    chunk_size = 4096
    chunk_count = 256
    payload = bytes(range(256)) * (chunk_size * chunk_count // 256)
    code = (
        "import sys\n"
        f"for _ in range({chunk_count}):\n"
        f"    chunk = sys.stdin.buffer.read({chunk_size})\n"
        "    if not chunk:\n"
        "        break\n"
        "    sys.stdout.buffer.write(chunk)\n"
        "    sys.stdout.buffer.flush()\n"
    )

    output = governance._run_bounded_git_stdout(
        (sys.executable, "-c", code),
        max_bytes=len(payload),
        input_bytes=payload,
    )
    assert output == payload


def test_bounded_git_io_rejects_oversized_input_before_process_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = False

    def popen(*_args, **_kwargs):
        nonlocal started
        started = True
        raise AssertionError("oversized input must be rejected before process start")

    monkeypatch.setattr(governance.subprocess, "Popen", popen)
    with pytest.raises(GovernanceError, match="input exceeds its byte bound"):
        governance._run_bounded_git_stdout(
            ("git", "cat-file", "--batch-check"),
            max_bytes=1,
            input_bytes=b"x" * (governance.MAX_GIT_INPUT_BYTES + 1),
        )
    assert started is False
def test_blob_size_is_checked_before_git_load(monkeypatch: pytest.MonkeyPatch) -> None:
    anchor, revision, head, blob = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    calls: list[tuple[str, ...]] = []

    def bounded(command, *, max_bytes, input_bytes=None):
        calls.append(tuple(command))
        assert "--batch-check=%(objectname) %(objecttype) %(objectsize)" in command
        return (
            f"{head} commit 1\n"
            f"{anchor} commit 1\n"
            f"{revision} commit 1\n"
            f"{blob} blob 11\n"
        ).encode("ascii")

    monkeypatch.setattr(governance, "_run_bounded_git_stdout", bounded)
    with pytest.raises(GovernanceError, match="exact committed prefix size"):
        governance._load_git_witnesses(
            ROOT.parent,
            _ledger("replay_status.jsonl"),
            anchor,
            (governance._PrefixWitness(revision, 10),),
        )
    assert len(calls) == 1


def test_commit_graph_load_is_single_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    head, parent, root = "c" * 40, "b" * 40, "a" * 40
    calls: list[tuple[tuple[str, ...], int]] = []

    def bounded(command, *, max_bytes):
        calls.append((tuple(command), max_bytes))
        return f"{head} {parent}\n{parent} {root}\n{root}\n".encode("ascii")

    monkeypatch.setattr(governance, "_run_bounded_git_stdout", bounded)
    graph = governance._git_load_commit_graph(ROOT.parent, head)
    assert len(calls) == 1
    assert "rev-list" in calls[0][0]
    assert calls[0][1] == governance.MAX_COMMIT_GRAPH_BYTES
    assert governance._graph_is_ancestor(graph, root, head)

    oversized = b"a" * (governance.MAX_COMMIT_GRAPH_BYTES + 1)
    with pytest.raises(GovernanceError, match="byte bound"):
        governance._parse_commit_graph(oversized, head)


def test_commit_graph_enforces_record_bound_and_follows_merge_parents() -> None:
    anchor, left, right, merge, head = (
        "a" * 40,
        "b" * 40,
        "c" * 40,
        "d" * 40,
        "e" * 40,
    )
    graph = governance._CommitGraph(
        anchor,
        head,
        {
            head: (merge,),
            merge: (left, right),
            left: (anchor,),
            right: (anchor,),
        },
    )
    assert governance._graph_is_ancestor(graph, right, head)
    governance._verify_graph_history(
        anchor,
        (
            governance._PrefixWitness(right, 1),
            governance._PrefixWitness(merge, 2),
        ),
        graph,
    )

    too_many = (f"{anchor}\n".encode("ascii")) * (
        governance.MAX_COMMIT_GRAPH_RECORDS + 1
    )
    with pytest.raises(GovernanceError, match="record bound"):
        governance._parse_commit_graph(too_many, head, anchor)


def test_git_witness_process_count_is_constant_for_multiple_suffixes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anchor, first, second, head = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    first_blob, second_blob = "e" * 40, "f" * 40
    calls: list[tuple[str, ...]] = []

    def bounded(command, *, max_bytes, input_bytes=None):
        calls.append(tuple(command))
        if any("batch-check=" in part for part in command):
            return (
                f"{head} commit 1\n"
                f"{anchor} commit 1\n"
                f"{first} commit 1\n"
                f"{second} commit 1\n"
                f"{first_blob} blob 3\n"
                f"{second_blob} blob 5\n"
            ).encode("ascii")
        if "rev-list" in command:
            return (
                f"{head} {second}\n"
                f"{second} {first}\n"
                f"{first} {anchor}\n"
            ).encode("ascii")
        assert "--batch" in command
        return (
            f"{first_blob} blob 3\nabc\n"
            f"{second_blob} blob 5\nabcde\n"
        ).encode("ascii")

    monkeypatch.setattr(governance, "_run_bounded_git_stdout", bounded)
    resolved_head, blobs = governance._load_git_witnesses(
        ROOT.parent,
        _ledger("replay_status.jsonl"),
        anchor,
        (
            governance._PrefixWitness(first, 3),
            governance._PrefixWitness(second, 5),
        ),
    )
    assert resolved_head == head
    assert blobs == {first: b"abc", second: b"abcde"}
    assert len(calls) == 3
    assert sum("rev-list" in call for call in calls) == 1
    assert all("merge-base" not in call for call in calls)


def test_governance_import_does_not_load_torch() -> None:
    code = (
        "import sys; import cemm_authoritative_hybrid.governance; "
        "raise SystemExit(1 if 'torch' in sys.modules else 0)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**dict(os.environ), "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stderr

def test_tensor_type_hints_resolve_without_loading_torch() -> None:
    code = (
        "import sys, typing; "
        "from cemm_authoritative_hybrid.canonical import tensor_identity; "
        "typing.get_type_hints(tensor_identity); "
        "raise SystemExit(1 if 'torch' in sys.modules else 0)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**dict(os.environ), "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stderr
