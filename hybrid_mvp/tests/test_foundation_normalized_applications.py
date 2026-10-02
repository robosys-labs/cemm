"""Normalized semantic application persistence, independent of descriptions."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace

import pytest

__cemm_test_inventory__ = {'tests/test_foundation_normalized_applications.py::test_typed_fillers_and_qualifier_ownership_are_identity_bearing[memory]': {'activation_phase': 'R3',
                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-typed-fillers-and-qualifier-ownership-are-identity-bearing-memory',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '974e298dce0006027e74f7d75e6ec9e048cb9f58126691591afa2f4620269a95'},
 'tests/test_foundation_normalized_applications.py::test_typed_fillers_and_qualifier_ownership_are_identity_bearing[sqlite]': {'activation_phase': 'R3',
                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-typed-fillers-and-qualifier-ownership-are-identity-bearing-sqlite',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '974e298dce0006027e74f7d75e6ec9e048cb9f58126691591afa2f4620269a95'},
 'tests/test_foundation_normalized_applications.py::test_nested_applications_are_content_addressed_child_first_and_hydrated[memory]': {'activation_phase': 'R3',
                                                                                                                                       'assertion_ref': 'assertion:foundation-normalized-nested-applications-are-content-addressed-child-first-and-hydrated-memory',
                                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                                       'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                                       'source_ast_sha256': 'cc43757435f33d6fe521d3d35be7f9f7e961899125f5b079b5262119b1693590'},
 'tests/test_foundation_normalized_applications.py::test_nested_applications_are_content_addressed_child_first_and_hydrated[sqlite]': {'activation_phase': 'R3',
                                                                                                                                       'assertion_ref': 'assertion:foundation-normalized-nested-applications-are-content-addressed-child-first-and-hydrated-sqlite',
                                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                                       'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                                       'source_ast_sha256': 'cc43757435f33d6fe521d3d35be7f9f7e961899125f5b079b5262119b1693590'},
 'tests/test_foundation_normalized_applications.py::test_claims_are_independent_and_one_retraction_preserves_its_sibling[memory]': {'activation_phase': 'R3',
                                                                                                                                    'assertion_ref': 'assertion:foundation-normalized-claims-are-independent-and-one-retraction-preserves-its-sibling-memory',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': 'f2b6959eb5a48a007ef8bfd4a3f44ae4885e91e8fa8330ca44f22b88d29dd5c4'},
 'tests/test_foundation_normalized_applications.py::test_claims_are_independent_and_one_retraction_preserves_its_sibling[sqlite]': {'activation_phase': 'R3',
                                                                                                                                    'assertion_ref': 'assertion:foundation-normalized-claims-are-independent-and-one-retraction-preserves-its-sibling-sqlite',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': 'f2b6959eb5a48a007ef8bfd4a3f44ae4885e91e8fa8330ca44f22b88d29dd5c4'},
 'tests/test_foundation_normalized_applications.py::test_reads_use_bounded_postings_and_raise_on_max_plus_one': {'activation_phase': 'R3',
                                                                                                                 'assertion_ref': 'assertion:foundation-normalized-reads-use-bounded-postings-and-raise-on-max-plus-one',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '984af3e1ee433a66a45f91c80326bc3a629915714793d81c1d6ec876c2b78d39'},
 'tests/test_foundation_normalized_applications.py::test_r3_port_reads_require_current_pin_and_do_not_scan_legacy_world': {'activation_phase': 'R3',
                                                                                                                           'assertion_ref': 'assertion:foundation-normalized-r3-port-reads-require-current-pin-and-do-not-scan-legacy-world',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-6',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '2bd302141fc5b377a7b9b08f37889a85fd4eeeafd0aa97973c2193b9db85df95'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[variable]': {'activation_phase': 'R3',
                                                                                                                                      'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-variable',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                                      'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[unresolved]': {'activation_phase': 'R3',
                                                                                                                                        'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-unresolved',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                                        'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[dangling]': {'activation_phase': 'R3',
                                                                                                                                      'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-dangling',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                                      'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[cycle]': {'activation_phase': 'R3',
                                                                                                                                   'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-cycle',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[scope]': {'activation_phase': 'R3',
                                                                                                                                   'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-scope',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[link]': {'activation_phase': 'R3',
                                                                                                                                  'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-link',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[binder]': {'activation_phase': 'R3',
                                                                                                                                    'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-binder',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_first_slice_rejects_unpersisted_or_invalid_expression_structure[non-app-root]': {'activation_phase': 'R3',
                                                                                                                                          'assertion_ref': 'assertion:foundation-normalized-first-slice-rejects-unpersisted-or-invalid-expression-structure-non-app-root',
                                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                                          'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                                          'source_ast_sha256': '009fe6c6c3697aaeaf3ce473f3ddb3c9c6e9488181e7d7b49a866498bfed5e16'},
 'tests/test_foundation_normalized_applications.py::test_sqlite_reopen_parity_and_payload_tamper_rejection': {'activation_phase': 'R3',
                                                                                                              'assertion_ref': 'assertion:foundation-normalized-sqlite-reopen-parity-and-payload-tamper-rejection',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-6',
                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                              'source_ast_sha256': 'f1c1778f2e314be22921a80282d0bb0bc66b0218c2397315ef7ac4d11178fdcf'},
 'tests/test_foundation_normalized_applications.py::test_authenticated_alias_publication_atomically_dual_writes_once[memory]': {'activation_phase': 'R3',
                                                                                                                                'assertion_ref': 'assertion:foundation-normalized-authenticated-alias-publication-atomically-dual-writes-once-memory',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': 'a304d39b95ff44f99363e98781bc776189ff3f92feb3a88d8d449a213e749f1a'},
 'tests/test_foundation_normalized_applications.py::test_authenticated_alias_publication_atomically_dual_writes_once[sqlite]': {'activation_phase': 'R3',
                                                                                                                                'assertion_ref': 'assertion:foundation-normalized-authenticated-alias-publication-atomically-dual-writes-once-sqlite',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': 'a304d39b95ff44f99363e98781bc776189ff3f92feb3a88d8d449a213e749f1a'},
 'tests/test_foundation_normalized_applications.py::test_normalized_claim_rejects_unrelated_legacy_fact[memory]': {'activation_phase': 'R3',
                                                                                                                   'assertion_ref': 'assertion:foundation-normalized-normalized-claim-rejects-unrelated-legacy-fact-memory',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                   'source_ast_sha256': '7c640d4c2b5a3e34e0b658fb57d5c4dda63424f3a671329475b72d3194b9de10'},
 'tests/test_foundation_normalized_applications.py::test_normalized_claim_rejects_unrelated_legacy_fact[sqlite]': {'activation_phase': 'R3',
                                                                                                                   'assertion_ref': 'assertion:foundation-normalized-normalized-claim-rejects-unrelated-legacy-fact-sqlite',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-6',
                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                   'source_ast_sha256': '7c640d4c2b5a3e34e0b658fb57d5c4dda63424f3a671329475b72d3194b9de10'},
 'tests/test_foundation_normalized_applications.py::test_alias_claim_uses_observed_delta_as_occurrence_not_review_source[memory]': {'activation_phase': 'R3',
                                                                                                                                    'assertion_ref': 'assertion:foundation-normalized-alias-claim-uses-observed-delta-as-occurrence-not-review-source-memory',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': 'a8ad88558c92dadb342d88797e98362c53a20232ccc67c81beb3ed2b33b73100'},
 'tests/test_foundation_normalized_applications.py::test_alias_claim_uses_observed_delta_as_occurrence_not_review_source[sqlite]': {'activation_phase': 'R3',
                                                                                                                                    'assertion_ref': 'assertion:foundation-normalized-alias-claim-uses-observed-delta-as-occurrence-not-review-source-sqlite',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': 'a8ad88558c92dadb342d88797e98362c53a20232ccc67c81beb3ed2b33b73100'},
 'tests/test_foundation_normalized_applications.py::test_target_lookup_indexes_predicate_only_semantic_identity[memory]': {'activation_phase': 'R3',
                                                                                                                           'assertion_ref': 'assertion:foundation-normalized-target-lookup-indexes-predicate-only-semantic-identity-memory',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-6',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '63c4619176c2faaa32c543383db6e13e97b9f4b06401f5783a215a9cec7028e2'},
 'tests/test_foundation_normalized_applications.py::test_target_lookup_indexes_predicate_only_semantic_identity[sqlite]': {'activation_phase': 'R3',
                                                                                                                           'assertion_ref': 'assertion:foundation-normalized-target-lookup-indexes-predicate-only-semantic-identity-sqlite',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-6',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '63c4619176c2faaa32c543383db6e13e97b9f4b06401f5783a215a9cec7028e2'},
 'tests/test_foundation_normalized_applications.py::test_normalized_retraction_rejects_unrelated_world_commit_and_forged_lineage[memory]': {'activation_phase': 'R3',
                                                                                                                                            'assertion_ref': 'assertion:foundation-normalized-normalized-retraction-rejects-unrelated-world-commit-and-forged-lineage-memory',
                                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                                            'source_ast_sha256': 'a02d0b371037621336ade29b11b6f4c2026ec0c25d7f1c8e1a3dc91dcfd4e96d'},
 'tests/test_foundation_normalized_applications.py::test_normalized_retraction_rejects_unrelated_world_commit_and_forged_lineage[sqlite]': {'activation_phase': 'R3',
                                                                                                                                            'assertion_ref': 'assertion:foundation-normalized-normalized-retraction-rejects-unrelated-world-commit-and-forged-lineage-sqlite',
                                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                                            'source_ast_sha256': 'a02d0b371037621336ade29b11b6f4c2026ec0c25d7f1c8e1a3dc91dcfd4e96d'},
 'tests/test_foundation_normalized_applications.py::test_activation_rejects_hash_consistent_non_kernel_normalized_application': {'activation_phase': 'R3',
                                                                                                                                 'assertion_ref': 'assertion:foundation-normalized-activation-rejects-hash-consistent-non-kernel-normalized-application',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': '140f6144c90fdb98151ccc0574706cc272b5c9bc517385bd743442855cef46bf'},
 'tests/test_foundation_normalized_applications.py::test_alias_normalized_write_failure_rolls_back_entire_commit[memory]': {'activation_phase': 'R3',
                                                                                                                            'assertion_ref': 'assertion:foundation-normalized-alias-normalized-write-failure-rolls-back-entire-commit-memory',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': '9a4003692073906700922e9054b88d6dca2eb7c64214c79a4beb1f45eb7bcef7'},
 'tests/test_foundation_normalized_applications.py::test_alias_normalized_write_failure_rolls_back_entire_commit[sqlite]': {'activation_phase': 'R3',
                                                                                                                            'assertion_ref': 'assertion:foundation-normalized-alias-normalized-write-failure-rolls-back-entire-commit-sqlite',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': '9a4003692073906700922e9054b88d6dca2eb7c64214c79a4beb1f45eb7bcef7'},
 'tests/test_foundation_normalized_applications.py::test_normalized_prepare_requires_the_one_exact_expression_root[multiple-roots]': {'activation_phase': 'R3',
                                                                                                                                      'assertion_ref': 'assertion:foundation-normalized-normalized-prepare-requires-the-one-exact-expression-root-multiple-roots',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                                      'source_ast_sha256': '4a583897301a4be82dd3f632df16efd13d04edb09c4af3761b8617c5266721db'},
 'tests/test_foundation_normalized_applications.py::test_normalized_prepare_requires_the_one_exact_expression_root[child-as-root]': {'activation_phase': 'R3',
                                                                                                                                     'assertion_ref': 'assertion:foundation-normalized-normalized-prepare-requires-the-one-exact-expression-root-child-as-root',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '4a583897301a4be82dd3f632df16efd13d04edb09c4af3761b8617c5266721db'},
 'tests/test_foundation_normalized_applications.py::test_memory_and_sqlite_return_identical_canonical_claim_order': {'activation_phase': 'R3',
                                                                                                                     'assertion_ref': 'assertion:foundation-normalized-memory-and-sqlite-return-identical-canonical-claim-order',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-6',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'c7f7bff061cbb5a85273ba7f81d8d3c3885d91345e8d2cfbb6fdbc9711d08be8'},
 'tests/test_foundation_normalized_applications.py::test_sqlite_target_read_batches_thirty_claims_and_six_application_closure': {'activation_phase': 'R3',
                                                                                                                                 'assertion_ref': 'assertion:foundation-normalized-sqlite-target-read-batches-thirty-claims-and-six-application-closure',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': 'ead7eba7b4794c84bb4fb014a79a203943b84992460ac8825574442de22efd60'},
 'tests/test_foundation_normalized_applications.py::test_malformed_unversioned_normalized_schema_is_rejected_without_mutation': {'activation_phase': 'R3',
                                                                                                                                 'assertion_ref': 'assertion:foundation-normalized-malformed-unversioned-normalized-schema-is-rejected-without-mutation',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': '1c5b517bb744fbaf5444345ae9d39d043c2d38174fe326c3805b83b8f50f87a3'},
 'tests/test_foundation_normalized_applications.py::test_canonical_normalized_schema_has_only_header_and_binding_storage': {'activation_phase': 'R3',
                                                                                                                            'assertion_ref': 'assertion:foundation-normalized-canonical-normalized-schema-has-only-header-and-binding-storage',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-6',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': '13afabee87c6e21590797919f9c65aee34bef60dbf74da0bdda5cca46138d4fb'},
 'tests/test_foundation_normalized_applications.py::test_authenticated_alias_without_normalized_mirror_cannot_silently_reopen': {'activation_phase': 'R3',
                                                                                                                                 'assertion_ref': 'assertion:foundation-normalized-authenticated-alias-without-normalized-mirror-cannot-silently-reopen',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': '6d7d8419a9187fcd8d6a24bea34c3ea81c8fe50a19f149511a531a427819a58a'},
 'tests/test_foundation_normalized_applications.py::test_activation_rejects_self_consistent_alias_claim_lineage_tamper': {'activation_phase': 'R3',
                                                                                                                          'assertion_ref': 'assertion:foundation-normalized-activation-rejects-self-consistent-alias-claim-lineage-tamper',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-6',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': '7c9a60fbe74c82afb097b8ed67806912c844285aec27326649cbbdb1884a407f'},
 'tests/test_foundation_normalized_applications.py::test_world_commit_cannot_replace_fact_owned_by_normalized_claim[memory]': {'activation_phase': 'R3',
                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-world-commit-cannot-replace-fact-owned-by-normalized-claim-memory',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'e1594b2f86ca41a9b216db0d07af7fca903dd5fb6daf7893c9b3e9c4f9a8a489'},
 'tests/test_foundation_normalized_applications.py::test_world_commit_cannot_replace_fact_owned_by_normalized_claim[sqlite]': {'activation_phase': 'R3',
                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-world-commit-cannot-replace-fact-owned-by-normalized-claim-sqlite',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'e1594b2f86ca41a9b216db0d07af7fca903dd5fb6daf7893c9b3e9c4f9a8a489'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[source-memory]': {'activation_phase': 'R3',
                                                                                                                                           'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-source-memory',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                                           'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[source-sqlite]': {'activation_phase': 'R3',
                                                                                                                                           'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-source-sqlite',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                                           'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[decision-memory]': {'activation_phase': 'R3',
                                                                                                                                             'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-decision-memory',
                                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                                             'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                                             'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[decision-sqlite]': {'activation_phase': 'R3',
                                                                                                                                             'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-decision-sqlite',
                                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                                             'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                                             'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[occurrence-memory]': {'activation_phase': 'R3',
                                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-occurrence-memory',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                                               'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[occurrence-sqlite]': {'activation_phase': 'R3',
                                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-occurrence-sqlite',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                                               'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[placement-memory]': {'activation_phase': 'R3',
                                                                                                                                              'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-placement-memory',
                                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                                              'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                                              'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[placement-sqlite]': {'activation_phase': 'R3',
                                                                                                                                              'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-placement-sqlite',
                                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                                              'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                                              'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[placement-ref-memory]': {'activation_phase': 'R3',
                                                                                                                                                  'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-placement-ref-memory',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                                  'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[placement-ref-sqlite]': {'activation_phase': 'R3',
                                                                                                                                                  'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-placement-ref-sqlite',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                                  'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[proof-refs-memory]': {'activation_phase': 'R3',
                                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-proof-refs-memory',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                                               'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_semantically_matching_fact_with_forged_lineage_cannot_own_claim[proof-refs-sqlite]': {'activation_phase': 'R3',
                                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-semantically-matching-fact-with-forged-lineage-cannot-own-claim-proof-refs-sqlite',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                                               'source_ast_sha256': '788bd5f220fcb81977f636cefa19cf243cb518de656757c7df0fd3f7cad87a7c'},
 'tests/test_foundation_normalized_applications.py::test_activation_rejects_same_name_nonunique_fact_ownership_index': {'activation_phase': 'R3',
                                                                                                                        'assertion_ref': 'assertion:foundation-normalized-activation-rejects-same-name-nonunique-fact-ownership-index',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-6',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '3ebadf596bf8b03bdada603f5af0515dda4c31a1ece423ca5431c6169d118f42'},
 'tests/test_foundation_normalized_applications.py::test_pre_feature_authenticated_alias_store_is_rejected_without_mutation': {'activation_phase': 'R3',
                                                                                                                               'assertion_ref': 'assertion:foundation-normalized-pre-feature-authenticated-alias-store-is-rejected-without-mutation',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-6',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '7682f50d01b97427844e658a810413b05636ee3d428e101376d5bfef2de3d303'}}

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    UnresolvedValue,
    VariableBinder,
)
from cemm_authoritative_hybrid.gaps import BudgetExhausted
from cemm_authoritative_hybrid.persistence import (
    Fact,
    StaleRevisionError,
    StoreActivationError,
    _normalized_application_payload,
    _normalized_legacy_projection,
    _payload_hash,
    _prepare_normalized_application_claim,
    memory_stores,
    open_stores,
)
from cemm_authoritative_hybrid.r3_persistence import (
    active_application_claims_for_target,
    application_claims,
)


def _stores(kind: str, tmp_path):
    if kind == "memory":
        return memory_stores(authority_generation="authority:test")
    return open_stores(tmp_path / "store", authority_generation="authority:test")


def _expression(*, literal_surface: bool = False, qualifier: bool = False):
    surface = LiteralValue("string", "entity:alice") if literal_surface else GroundedReference("entity:alice")
    app = SemanticApplication(
        "local:root",
        "op:relation",
        "rel:likes",
        (
            RoleBinding("role:subject", surface),
            RoleBinding("role:object", GroundedReference("entity:bob")),
        ),
        (RoleBinding("role:tense", GroundedReference("tense:present")),) if qualifier else (),
    )
    return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))


def _prepare(expression, *, fact_ref="fact:one", stance="support", source_ref="receipt:one",
             decision_ref="decision:one", occurrence_ref="occurrence:one",
             placement="reviewed", placement_ref="policy:reviewed", proof_refs=("proof:one",),
             authority_generation="authority:test", confidence_micros=1_000_000,
             commit_transaction_ref="txn:one", revision=1):
    return _prepare_normalized_application_claim(
        expression,
        root_ref=expression.root_refs[0],
        stance=stance,
        fact_ref=fact_ref,
        source_ref=source_ref,
        decision_ref=decision_ref,
        occurrence_ref=occurrence_ref,
        placement=placement,
        placement_ref=placement_ref,
        proof_refs=proof_refs,
        authority_generation=authority_generation,
        confidence_micros=confidence_micros,
        commit_transaction_ref=commit_transaction_ref,
        asserted_world_revision=revision,
    )


def _commit_claim(stores, expression, *, fact_ref="fact:one", stance="support", source_ref="receipt:one"):
    occurrence_ref = f"occurrence:{fact_ref}"
    decision_ref = "decision:one"
    placement = "reviewed"
    placement_ref = "policy:reviewed"
    proof_refs = (f"proof:{fact_ref}",)
    provisional = _prepare(
        expression,
        fact_ref=fact_ref,
        stance=stance,
        source_ref=source_ref,
        decision_ref=decision_ref,
        occurrence_ref=occurrence_ref,
        placement=placement,
        placement_ref=placement_ref,
        proof_refs=proof_refs,
        revision=0,
        commit_transaction_ref="transaction:pending",
    )
    persistent_root = next(
        row
        for row in provisional.applications
        if row.application_ref == provisional.root_application_ref
    )
    operator, args, projected_stance = _normalized_legacy_projection(
        _normalized_application_payload(persistent_root), stance
    )
    fact = Fact(
        fact_ref=fact_ref,
        operator=operator,
        args=args,
        stance=projected_stance,
        proof={
            "source": source_ref,
            "decision_ref": decision_ref,
            "occurrence_ref": occurrence_ref,
            "placement": placement,
            "placement_ref": placement_ref,
            "proof_refs": list(proof_refs),
        },
    )
    receipt = stores.world.commit((fact,), expected_revision=stores.world.revision)
    batch = _prepare(
        expression,
        fact_ref=fact_ref,
        stance=stance,
        source_ref=source_ref,
        decision_ref=decision_ref,
        occurrence_ref=occurrence_ref,
        placement=placement,
        placement_ref=placement_ref,
        proof_refs=proof_refs,
        revision=receipt.new_revision,
        commit_transaction_ref=receipt.transaction_ref,
    )
    stores._r3_write_normalized_batch(batch)
    return batch


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_typed_fillers_and_qualifier_ownership_are_identity_bearing(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        grounded = _commit_claim(stores, _expression(qualifier=True), fact_ref="fact:grounded")
        literal = _commit_claim(stores, _expression(literal_surface=True, qualifier=True), fact_ref="fact:literal")

        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            claims = stores.r3_active_application_claims_for_target("entity:bob", maximum=8, expected_pin=pin)
            alice_claims = stores.r3_active_application_claims_for_target("entity:alice", maximum=8, expected_pin=pin)
        assert len(claims) == 2
        assert claims[0].application_ref != claims[1].application_ref
        for claim in claims:
            root = claim.applications[-1]
            assert [row.role_ref for row in root.qualifiers] == ["role:tense"]
            assert all(row.role_ref != "role:tense" for row in root.roles)
        assert len(alice_claims) == 1
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_nested_applications_are_content_addressed_child_first_and_hydrated(tmp_path, backend):
    child = SemanticApplication(
        "local:child", "op:event", "event:learn",
        (RoleBinding("role:actor", GroundedReference("entity:student")),),
    )
    parent = SemanticApplication(
        "local:parent", "op:event", "event:say",
        (
            RoleBinding("role:speaker", GroundedReference("participant:user")),
            RoleBinding("role:content", ApplicationFiller(child.application_ref)),
        ),
    )
    expression = SemanticExpression.create(
        applications=(parent, child), root_refs=(parent.application_ref,)
    )
    stores = _stores(backend, tmp_path)
    try:
        batch = _commit_claim(stores, expression)
        assert [row.operator for row in batch.applications] == ["op:event", "op:event"]
        assert batch.applications[0].predicate_ref == "event:learn"
        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            claim = stores.r3_application_claims((batch.root_application_ref,), maximum=8, expected_pin=pin)[0]
            by_nested_target = stores.r3_active_application_claims_for_target(
                "entity:student", maximum=8, expected_pin=pin
            )
        assert tuple(row.application_ref for row in claim.applications) == tuple(
            row.application_ref for row in batch.applications
        )
        content = next(row.filler for row in claim.applications[-1].roles if row.role_ref == "role:content")
        assert isinstance(content, ApplicationFiller)
        assert content.node_ref == claim.applications[0].application_ref
        assert [row.claim_ref for row in by_nested_target] == [claim.claim_ref]
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_claims_are_independent_and_one_retraction_preserves_its_sibling(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        expression = _expression()
        support = _commit_claim(stores, expression, fact_ref="fact:support", stance="support")
        support_two = _commit_claim(stores, expression, fact_ref="fact:support-two", stance="support", source_ref="receipt:two")
        denial = _commit_claim(stores, expression, fact_ref="fact:deny", stance="deny", source_ref="receipt:three")
        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            assert [row.stance for row in stores.r3_application_claims(
                (support.root_application_ref,), maximum=8, expected_pin=pin
            )].count("support") == 2

        retraction_occurrence = "occurrence:retract"
        retraction_fact = Fact("fact:retract", "op:event", {"predicate_ref": "event:retract",
            "role:object": support.claim_ref}, proof={"source": "receipt:retract",
            "occurrence_ref": retraction_occurrence})
        retraction_receipt = stores.world.commit((retraction_fact,), expected_revision=stores.world.revision)
        stores._r3_write_normalized_retraction(support.claim_ref, source_ref="fact:retract",
            occurrence_ref=retraction_occurrence, proof_refs=(retraction_occurrence, "proof:retract"),
            asserted_world_revision=retraction_receipt.new_revision,
            commit_transaction_ref=retraction_receipt.transaction_ref)
        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            active = stores.r3_active_application_claims_for_target("entity:bob", maximum=8, expected_pin=pin)
            all_claims = stores.r3_application_claims((support.root_application_ref,), maximum=8, expected_pin=pin)
        assert {row.claim_ref for row in active} == {support_two.claim_ref, denial.claim_ref}
        assert {row.claim_ref: row.active for row in all_claims} == {
            support.claim_ref: False,
            support_two.claim_ref: True,
            denial.claim_ref: True,
        }
    finally:
        stores.close()


def test_reads_use_bounded_postings_and_raise_on_max_plus_one(tmp_path):
    stores = memory_stores(authority_generation="authority:test")
    try:
        for index in range(3):
            expression = _expression()
            batch = _commit_claim(stores, expression, fact_ref=f"fact:{index}", source_ref=f"receipt:{index}")
        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            with pytest.raises(BudgetExhausted):
                stores.r3_active_application_claims_for_target("entity:bob", maximum=2, expected_pin=pin)
            with pytest.raises(BudgetExhausted):
                stores.r3_application_claims((batch.root_application_ref,), maximum=2, expected_pin=pin)
    finally:
        stores.close()


def test_r3_port_reads_require_current_pin_and_do_not_scan_legacy_world():
    stores = memory_stores(authority_generation="authority:test")
    try:
        batch = _commit_claim(stores, _expression())
        pin = stores.revision_pin()

        class NoIteration(dict):
            def __iter__(self):
                raise AssertionError("normalized read scanned legacy world facts")

            def keys(self):
                raise AssertionError("normalized read scanned legacy world facts")

        stores._backend.world._facts = NoIteration(stores._backend.world._facts)
        with stores.r3_read_snapshot(pin):
            assert active_application_claims_for_target(
                stores, "entity:bob", maximum=8, expected_pin=pin
            )[0].claim_ref == batch.claim_ref
            assert application_claims(
                stores, (batch.root_application_ref,), maximum=8, expected_pin=pin
            )[0].claim_ref == batch.claim_ref

        stores.world.revision += 1
        with pytest.raises(StaleRevisionError, match="captured store pin|stale"):
            active_application_claims_for_target(
                stores, "entity:bob", maximum=8, expected_pin=pin
            )
    finally:
        stores.close()


@pytest.mark.parametrize(
    "defect",
    ("variable", "unresolved", "dangling", "cycle", "scope", "link", "binder", "non-app-root"),
    ids=("variable", "unresolved", "dangling", "cycle", "scope", "link", "binder", "non-app-root"),
)
def test_first_slice_rejects_unpersisted_or_invalid_expression_structure(defect):
    filler = GroundedReference("entity:alice")
    if defect == "variable":
        filler = BoundVariable("?x")
    elif defect == "unresolved":
        filler = UnresolvedValue("unresolved:x")
    elif defect == "dangling":
        filler = ApplicationFiller("local:missing")
    app = SemanticApplication(
        "local:root", "op:relation", "rel:likes",
        (RoleBinding("role:subject", filler), RoleBinding("role:object", GroundedReference("entity:bob"))),
    )
    kwargs = {"applications": (app,), "root_refs": (app.application_ref,)}
    if defect == "scope":
        scope = ScopeOperator("scope:one", "scope:polarity", "polarity:positive", app.application_ref)
        kwargs.update(scope_operators=(scope,))
    elif defect == "link":
        link = ExpressionLink("link:one", "link:sequence", (app.application_ref, app.application_ref))
        kwargs.update(expression_links=(link,))
    elif defect == "binder":
        binder = VariableBinder("binder:one", "?x", app.application_ref)
        kwargs.update(binders=(binder,))
    elif defect == "non-app-root":
        scope = ScopeOperator("scope:one", "scope:polarity", "polarity:positive", app.application_ref)
        kwargs.update(scope_operators=(scope,), root_refs=(scope.scope_ref,))
    if defect == "cycle":
        # SemanticExpression correctly rejects cycles; forge only the otherwise
        # exact immutable object to prove persistence also defends its boundary.
        app = replace(app, roles=(RoleBinding("role:subject", ApplicationFiller("local:root")),
                                  RoleBinding("role:object", GroundedReference("entity:bob"))))
        value = object.__new__(SemanticExpression)
        object.__setattr__(value, "expression_ref", "expression:forged")
        object.__setattr__(value, "applications", (app,))
        object.__setattr__(value, "root_refs", (app.application_ref,))
        object.__setattr__(value, "scope_operators", ())
        object.__setattr__(value, "expression_links", ())
        object.__setattr__(value, "binders", ())
        object.__setattr__(value, "unresolved_fillers", ())
        expression = value
    else:
        try:
            expression = SemanticExpression.create(**kwargs)
        except ValueError:
            # The expression ABI may reject the defect earlier, which is also a
            # valid closed boundary. Persistence is exercised where constructible.
            return
    with pytest.raises(ValueError):
        _prepare(expression)


def test_sqlite_reopen_parity_and_payload_tamper_rejection(tmp_path):
    path = tmp_path / "store"
    stores = open_stores(path, authority_generation="authority:test")
    batch = _commit_claim(stores, _expression(qualifier=True))
    pin = stores.revision_pin()
    with stores.r3_read_snapshot(pin):
        before = stores.r3_active_application_claims_for_target("entity:bob", maximum=8, expected_pin=pin)
    stores.close()

    reopened = open_stores(path, authority_generation="authority:test")
    pin = reopened.revision_pin()
    with reopened.r3_read_snapshot(pin):
        assert reopened.r3_active_application_claims_for_target("entity:bob", maximum=8, expected_pin=pin) == before
    reopened.close()

    conn = sqlite3.connect(path / "semantic.db")
    conn.execute("UPDATE semantic_applications SET predicate_ref='rel:tampered'")
    conn.commit()
    conn.close()
    with pytest.raises(StoreActivationError):
        open_stores(path, authority_generation="authority:test")


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_authenticated_alias_publication_atomically_dual_writes_once(tmp_path, monkeypatch, backend):
    from cemm_authoritative_hybrid import bootstrap
    from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, R3EffectGateway
    from tests.test_foundation_alias_publication import ROOT, _publication, _signed

    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    verifier = gateway._review_verifier
    try:
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        legacy = runtime.stores.world.get(receipt.committed_fact_refs[0])
        assert legacy is not None and legacy.args["role:surface"] == "velnora"
        pin = runtime.stores.revision_pin()
        with runtime.stores.r3_read_snapshot(pin):
            claims = active_application_claims_for_target(
                runtime.stores, "rel:likes", maximum=8, expected_pin=pin
            )
        assert len(claims) == 1
        claim = claims[0]
        assert claim.fact_ref == legacy.fact_ref
        assert claim.application_ref == claim.applications[-1].application_ref
        assert claim.applications[-1].operator == "op:designation"
        assert claim.placement == "reviewed"
        assert claim.authority_generation == pin.authority_generation
        before = runtime.stores.revision_pin(), claim
        assert gateway.publish_learning(grant["proposal_key"], _signed(grant, secret)) == receipt
        pin = runtime.stores.revision_pin()
        with runtime.stores.r3_read_snapshot(pin):
            retry = active_application_claims_for_target(
                runtime.stores, "rel:likes", maximum=8, expected_pin=pin
            )
        assert (runtime.stores.revision_pin(), retry[0]) == before
    finally:
        runtime.stores.close()

    if backend == "sqlite":
        runtime = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
        try:
            pin = runtime.stores.revision_pin()
            with runtime.stores.r3_read_snapshot(pin):
                reopened = active_application_claims_for_target(
                    runtime.stores, "rel:likes", maximum=8, expected_pin=pin
                )
            assert len(reopened) == 1 and reopened[0] == before[1]
            gateway = R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority,
                                      review_verifier=verifier)
            assert gateway.publish_learning(grant["proposal_key"], _signed(grant, secret)) == receipt
        finally:
            runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_normalized_claim_rejects_unrelated_legacy_fact(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        expression = _expression()
        unrelated = Fact(
            fact_ref="fact:unrelated",
            operator="op:relation",
            args={
                "predicate_ref": "rel:source",
                "role:subject": "entity:unrelated",
                "role:object": "entity:elsewhere",
            },
            proof={"source": "receipt:unrelated"},
        )
        receipt = stores.world.commit(
            (unrelated,), expected_revision=stores.world.revision
        )
        batch = _prepare(
            expression,
            fact_ref=unrelated.fact_ref,
            source_ref="receipt:unrelated",
            occurrence_ref="occurrence:unrelated",
            proof_refs=("proof:unrelated",),
            revision=receipt.new_revision,
            commit_transaction_ref=receipt.transaction_ref,
        )

        with pytest.raises(ValueError, match="correspond|semantic|unrelated"):
            stores._r3_write_normalized_batch(batch)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_alias_claim_uses_observed_delta_as_occurrence_not_review_source(
    tmp_path, monkeypatch, backend
):
    from tests.test_foundation_alias_publication import _publication, _signed

    runtime, _, _, _, gateway, grant, secret = _publication(
        tmp_path, monkeypatch, backend
    )
    try:
        receipt = gateway.publish_learning(
            grant["proposal_key"], _signed(grant, secret)
        )
        pin = runtime.stores.revision_pin()
        with runtime.stores.r3_read_snapshot(pin):
            claim = active_application_claims_for_target(
                runtime.stores, "rel:likes", maximum=8, expected_pin=pin
            )[0]

        assert claim.occurrence_ref == receipt.observed_delta_refs[0]
        assert claim.source_ref == receipt.operation_receipt_ref
        assert claim.occurrence_ref != claim.source_ref
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_target_lookup_indexes_predicate_only_semantic_identity(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        batch = _commit_claim(stores, _expression())
        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            claims = stores.r3_active_application_claims_for_target(
                "rel:likes", maximum=8, expected_pin=pin
            )

        assert [row.claim_ref for row in claims] == [batch.claim_ref]
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_normalized_retraction_rejects_unrelated_world_commit_and_forged_lineage(
    tmp_path, backend
):
    stores = _stores(backend, tmp_path)
    try:
        claim = _commit_claim(stores, _expression())
        unrelated = Fact(
            fact_ref="fact:unrelated-retraction",
            operator="op:event",
            args={
                "predicate_ref": "event:unrelated",
                "role:actor": "participant:user",
            },
            proof={"source": "receipt:unrelated-retraction"},
        )
        receipt = stores.world.commit(
            (unrelated,), expected_revision=stores.world.revision
        )

        with pytest.raises(ValueError, match="retraction|lineage|source|occurrence"):
            stores._r3_write_normalized_retraction(
                claim.claim_ref,
                source_ref=unrelated.fact_ref,
                occurrence_ref="forged:occurrence",
                proof_refs=("forged:proof",),
                asserted_world_revision=receipt.new_revision,
                commit_transaction_ref=receipt.transaction_ref,
            )

        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            stored = stores.r3_application_claims(
                (claim.root_application_ref,), maximum=8, expected_pin=pin
            )[0]
        assert stored.active is True
    finally:
        stores.close()


def test_activation_rejects_hash_consistent_non_kernel_normalized_application(
    tmp_path,
):
    path = tmp_path / "store"
    stores = open_stores(path, authority_generation="authority:test")
    stores.close()

    payload = {
        "operator": "op:learn",
        "predicate_ref": "event:learn",
        "roles": [
            {
                "binding_kind": "role",
                "ordinal": 0,
                "role_ref": "role:actor",
                "filler": {"kind": "grounded", "target_ref": "entity:student"},
            }
        ],
        "qualifiers": [],
    }
    application_ref = stable_ref("semantic_application", payload)
    binding_material = {
        "application_ref": application_ref,
        "binding_kind": "role",
        "ordinal": 0,
        "role_ref": "role:actor",
        "filler_kind": "grounded",
        "filler_value": "entity:student",
    }
    binding_ref = stable_ref("semantic_binding", binding_material)
    connection = sqlite3.connect(path / "semantic.db")
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            "INSERT INTO semantic_applications VALUES(?,?,?,?)",
            (
                application_ref,
                payload["operator"],
                payload["predicate_ref"],
                _payload_hash(payload),
            ),
        )
        connection.execute(
            "INSERT INTO semantic_application_bindings VALUES(?,?,?,?,?,?,?,?)",
            (
                binding_ref,
                application_ref,
                "role",
                0,
                "role:actor",
                "grounded",
                "entity:student",
                _payload_hash(binding_material),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    reopened = None
    try:
        with pytest.raises(StoreActivationError):
            reopened = open_stores(path, authority_generation="authority:test")
    finally:
        if reopened is not None:
            reopened.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_alias_normalized_write_failure_rolls_back_entire_commit(
    tmp_path, monkeypatch, backend
):
    import cemm_authoritative_hybrid.r3_effects as effects_module
    from tests.test_foundation_alias_publication import _publication, _signed

    runtime, _, _, _, gateway, grant, secret = _publication(
        tmp_path, monkeypatch, backend
    )
    captured = {}
    real_commit = effects_module.effect_journal_commit

    def capture_commit(stores, **kwargs):
        captured["pin"] = kwargs["expected_revision_pin"]
        captured["obligation_revision"] = stores.r3_obligation_revision()
        captured["facts"] = kwargs["facts"]
        return real_commit(stores, **kwargs)

    def fail_normalized_write(_batch):
        raise RuntimeError("injected normalized persistence failure")

    monkeypatch.setattr(effects_module, "effect_journal_commit", capture_commit)
    monkeypatch.setattr(
        runtime.stores, "_r3_write_normalized_batch", fail_normalized_write
    )
    try:
        with pytest.raises(RuntimeError, match="injected normalized persistence failure"):
            gateway.publish_learning(
                grant["proposal_key"], _signed(grant, secret)
            )

        assert runtime.stores.revision_pin() == captured["pin"]
        assert (
            runtime.stores.r3_obligation_revision()
            == captured["obligation_revision"]
        )
        assert all(
            runtime.stores.world.get(fact.fact_ref) is None
            for fact in captured["facts"]
        )
        pin = runtime.stores.revision_pin()
        with runtime.stores.r3_read_snapshot(pin):
            assert active_application_claims_for_target(
                runtime.stores, "rel:likes", maximum=8, expected_pin=pin
            ) == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "case", ("multiple-roots", "child-as-root"), ids=("multiple-roots", "child-as-root")
)
def test_normalized_prepare_requires_the_one_exact_expression_root(case):
    child = SemanticApplication(
        "local:child",
        "op:event",
        "event:learn",
        (RoleBinding("role:actor", GroundedReference("entity:student")),),
    )
    parent = SemanticApplication(
        "local:parent",
        "op:event",
        "event:say",
        (
            RoleBinding("role:speaker", GroundedReference("participant:user")),
            RoleBinding("role:content", ApplicationFiller(child.application_ref)),
        ),
    )
    if case == "multiple-roots":
        sibling = SemanticApplication(
            "local:sibling",
            "op:state",
            "state:availability",
            (RoleBinding("role:entity", GroundedReference("entity:server")),),
        )
        expression = SemanticExpression.create(
            applications=(parent, child, sibling),
            root_refs=(parent.application_ref, sibling.application_ref),
        )
        attempted_root = parent.application_ref
    else:
        expression = SemanticExpression.create(
            applications=(parent, child), root_refs=(parent.application_ref,)
        )
        attempted_root = child.application_ref

    with pytest.raises(ValueError, match="one exact application root|expression root"):
        _prepare_normalized_application_claim(
            expression,
            root_ref=attempted_root,
            stance="support",
            fact_ref="fact:root-boundary",
            source_ref="receipt:root-boundary",
            decision_ref="decision:root-boundary",
            occurrence_ref="occurrence:root-boundary",
            placement="reviewed",
            placement_ref="policy:reviewed",
            proof_refs=("proof:root-boundary",),
            authority_generation="authority:test",
            confidence_micros=1_000_000,
            asserted_world_revision=1,
            commit_transaction_ref="transaction:root-boundary",
        )


def test_memory_and_sqlite_return_identical_canonical_claim_order(tmp_path):
    memory = _stores("memory", tmp_path / "memory-order")
    sqlite = _stores("sqlite", tmp_path / "sqlite-order")
    try:
        roots = []
        for stores in (memory, sqlite):
            root = None
            for fact_ref in ("fact:zeta", "fact:alpha", "fact:middle"):
                batch = _commit_claim(
                    stores,
                    _expression(),
                    fact_ref=fact_ref,
                    source_ref=f"receipt:{fact_ref}",
                )
                root = batch.root_application_ref
            roots.append(root)

        assert roots[0] == roots[1]
        observations = []
        for stores, root in zip((memory, sqlite), roots):
            pin = stores.revision_pin()
            with stores.r3_read_snapshot(pin):
                by_target = stores.r3_active_application_claims_for_target(
                    "entity:bob", maximum=8, expected_pin=pin
                )
                by_application = stores.r3_application_claims(
                    (root,), maximum=8, expected_pin=pin
                )
            observations.append(
                (
                    tuple(row.claim_ref for row in by_target),
                    tuple(row.claim_ref for row in by_application),
                )
            )

        assert observations[0] == observations[1]
        assert observations[0][0] == tuple(sorted(observations[0][0]))
        assert observations[0][1] == tuple(sorted(observations[0][1]))
    finally:
        memory.close()
        sqlite.close()


def test_sqlite_target_read_batches_thirty_claims_and_six_application_closure(
    tmp_path,
):
    applications = []
    child_ref = None
    for depth in range(6):
        roles = [
            RoleBinding("role:actor", GroundedReference("entity:student"))
        ]
        if child_ref is not None:
            roles.append(RoleBinding("role:content", ApplicationFiller(child_ref)))
        application = SemanticApplication(
            f"local:depth-{depth}",
            "op:event",
            "event:learn" if depth == 0 else "event:say",
            tuple(roles),
        )
        applications.append(application)
        child_ref = application.application_ref
    expression = SemanticExpression.create(
        applications=tuple(reversed(applications)), root_refs=(child_ref,)
    )
    stores = _stores("sqlite", tmp_path / "bounded-read")
    try:
        for index in range(30):
            _commit_claim(
                stores,
                expression,
                fact_ref=f"fact:shared-closure-{index:02d}",
                source_ref=f"receipt:shared-closure-{index:02d}",
            )

        pin = stores.revision_pin()
        statements = []
        connection = stores._backend._conn
        with stores.r3_read_snapshot(pin):
            connection.set_trace_callback(
                lambda sql: statements.append(sql)
                if sql.lstrip().upper().startswith("SELECT")
                else None
            )
            try:
                claims = stores.r3_active_application_claims_for_target(
                    "entity:student", maximum=64, expected_pin=pin
                )
            finally:
                connection.set_trace_callback(None)

        assert len(claims) == 30
        assert len(statements) <= 20, "\n".join(statements)
    finally:
        stores.close()


def test_malformed_unversioned_normalized_schema_is_rejected_without_mutation(
    tmp_path,
):
    path = tmp_path / "malformed-unversioned"
    path.mkdir()
    database = path / "semantic.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE semantic_applications "
            "(application_ref TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
        )
        connection.commit()
        before_schema = tuple(
            connection.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        )
        before_metadata = tuple(
            connection.execute("SELECT key,value FROM metadata ORDER BY key")
        )
    finally:
        connection.close()

    with pytest.raises(StoreActivationError):
        open_stores(path, authority_generation="authority:test")

    connection = sqlite3.connect(database)
    try:
        after_schema = tuple(
            connection.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            )
        )
        after_metadata = tuple(
            connection.execute("SELECT key,value FROM metadata ORDER BY key")
        )
    finally:
        connection.close()
    assert after_schema == before_schema
    assert after_metadata == before_metadata


def test_canonical_normalized_schema_has_only_header_and_binding_storage(tmp_path):
    path = tmp_path / "canonical-schema"
    stores = open_stores(path, authority_generation="authority:test")
    stores.close()

    connection = sqlite3.connect(path / "semantic.db")
    try:
        application_columns = tuple(
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(semantic_applications)"
            )
        )
        normalized_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'semantic_%'"
            )
        }
    finally:
        connection.close()

    assert application_columns == (
        "application_ref",
        "operator",
        "predicate_ref",
        "payload_hash",
    )
    assert "semantic_application_bindings" in normalized_tables
    assert "semantic_claim_target_postings" in normalized_tables
    assert "semantic_target_postings" not in normalized_tables
    assert "payload_json" not in application_columns


def test_authenticated_alias_without_normalized_mirror_cannot_silently_reopen(
    tmp_path, monkeypatch
):
    from cemm_authoritative_hybrid import bootstrap
    from tests.test_foundation_alias_publication import ROOT, _publication, _signed

    runtime, _, _, _, gateway, grant, secret = _publication(
        tmp_path, monkeypatch, "sqlite"
    )
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    connection = runtime.stores._backend._conn
    connection.execute("DELETE FROM semantic_claim_target_postings")
    connection.execute("DELETE FROM semantic_claim_retractions")
    connection.execute("DELETE FROM semantic_application_claims")
    connection.execute("DELETE FROM semantic_application_bindings")
    connection.execute("DELETE FROM semantic_applications")
    connection.commit()
    runtime.stores.close()

    reopened = None
    try:
        try:
            reopened = bootstrap.load_runtime(
                ROOT,
                profile="development",
                store_path=tmp_path / "proposal.db",
            )
        except StoreActivationError:
            return
        pin = reopened.stores.revision_pin()
        with reopened.stores.r3_read_snapshot(pin):
            claims = reopened.stores.r3_active_application_claims_for_target(
                "rel:likes", maximum=8, expected_pin=pin
            )
        assert len(claims) == 1
        assert claims[0].fact_ref == receipt.committed_fact_refs[0]
    finally:
        if reopened is not None:
            reopened.stores.close()


def test_activation_rejects_self_consistent_alias_claim_lineage_tamper(
    tmp_path, monkeypatch
):
    from cemm_authoritative_hybrid import bootstrap
    from tests.test_foundation_alias_publication import ROOT, _publication, _signed

    runtime, _, _, _, gateway, grant, secret = _publication(
        tmp_path, monkeypatch, "sqlite"
    )
    gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    connection = runtime.stores._backend._conn
    row = connection.execute(
        "SELECT * FROM semantic_application_claims"
    ).fetchone()
    old_claim_ref = row["claim_ref"]
    postings = tuple(
        posting[0]
        for posting in connection.execute(
            "SELECT target_ref FROM semantic_claim_target_postings "
            "WHERE claim_ref=? ORDER BY target_ref",
            (old_claim_ref,),
        )
    )
    payload = {
        "application_ref": row["application_ref"],
        "stance": row["stance"],
        "fact_ref": row["fact_ref"],
        "source_ref": "forged:source",
        "decision_ref": row["decision_ref"],
        "occurrence_ref": "forged:occurrence",
        "placement": row["placement"],
        "placement_ref": row["placement_ref"],
        "proof_refs": json.loads(row["proof_json"]),
        "authority_generation": row["authority_generation"],
        "confidence_micros": row["confidence_micros"],
        "asserted_world_revision": row["asserted_world_revision"],
        "commit_transaction_ref": row["commit_transaction_ref"],
    }
    forged_claim_ref = stable_ref("semantic_claim", payload)
    connection.execute("DELETE FROM semantic_claim_target_postings WHERE claim_ref=?", (old_claim_ref,))
    connection.execute("DELETE FROM semantic_application_claims WHERE claim_ref=?", (old_claim_ref,))
    connection.execute(
        "INSERT INTO semantic_application_claims "
        "(claim_ref,application_ref,stance,fact_ref,source_ref,decision_ref,"
        "occurrence_ref,placement,placement_ref,proof_json,authority_generation,"
        "confidence_micros,asserted_world_revision,commit_transaction_ref,payload_hash) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            forged_claim_ref,
            payload["application_ref"],
            payload["stance"],
            payload["fact_ref"],
            payload["source_ref"],
            payload["decision_ref"],
            payload["occurrence_ref"],
            payload["placement"],
            payload["placement_ref"],
            row["proof_json"],
            payload["authority_generation"],
            payload["confidence_micros"],
            payload["asserted_world_revision"],
            payload["commit_transaction_ref"],
            _payload_hash(payload),
        ),
    )
    connection.executemany(
        "INSERT INTO semantic_claim_target_postings(target_ref,claim_ref) VALUES(?,?)",
        ((target_ref, forged_claim_ref) for target_ref in postings),
    )
    connection.commit()
    runtime.stores.close()

    reopened = None
    try:
        with pytest.raises(StoreActivationError):
            reopened = bootstrap.load_runtime(
                ROOT,
                profile="development",
                store_path=tmp_path / "proposal.db",
            )
    finally:
        if reopened is not None:
            reopened.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_world_commit_cannot_replace_fact_owned_by_normalized_claim(
    tmp_path, backend
):
    stores = _stores(backend, tmp_path / f"protected-fact-{backend}")
    try:
        fact_ref = f"fact:protected-{backend}"
        batch = _commit_claim(stores, _expression(), fact_ref=fact_ref)
        before_pin = stores.revision_pin()
        before_fact = stores.world.get(fact_ref)
        with stores.r3_read_snapshot(before_pin):
            before_claim = stores.r3_application_claims(
                (batch.root_application_ref,), maximum=8, expected_pin=before_pin
            )[0]
        replacement = Fact(
            fact_ref=fact_ref,
            operator="op:relation",
            args={
                "predicate_ref": "rel:likes",
                "role:subject": "entity:alice",
                "role:object": "entity:charlie",
            },
            proof={
                "source": "receipt:replacement",
                "occurrence_ref": "occurrence:replacement",
            },
        )

        with pytest.raises(ValueError, match="normalized|claim|replace|protected"):
            stores.world.commit(
                (replacement,), expected_revision=stores.world.revision
            )

        after_pin = stores.revision_pin()
        assert after_pin == before_pin
        assert stores.world.get(fact_ref) == before_fact
        with stores.r3_read_snapshot(after_pin):
            after_claim = stores.r3_application_claims(
                (batch.root_application_ref,), maximum=8, expected_pin=after_pin
            )[0]
        assert after_claim == before_claim
    finally:
        stores.close()


@pytest.mark.parametrize(
    "lineage_field,backend",
    (
        ("source", "memory"),
        ("source", "sqlite"),
        ("decision_ref", "memory"),
        ("decision_ref", "sqlite"),
        ("occurrence_ref", "memory"),
        ("occurrence_ref", "sqlite"),
        ("placement", "memory"),
        ("placement", "sqlite"),
        ("placement_ref", "memory"),
        ("placement_ref", "sqlite"),
        ("proof_refs", "memory"),
        ("proof_refs", "sqlite"),
    ),
    ids=(
        "source-memory",
        "source-sqlite",
        "decision-memory",
        "decision-sqlite",
        "occurrence-memory",
        "occurrence-sqlite",
        "placement-memory",
        "placement-sqlite",
        "placement-ref-memory",
        "placement-ref-sqlite",
        "proof-refs-memory",
        "proof-refs-sqlite",
    ),
)
def test_semantically_matching_fact_with_forged_lineage_cannot_own_claim(
    tmp_path, backend, lineage_field
):
    stores = _stores(
        backend, tmp_path / f"forged-lineage-{backend}-{lineage_field}"
    )
    try:
        expression = _expression()
        fact_ref = f"fact:forged-lineage:{lineage_field}"
        source_ref = "receipt:lineage"
        decision_ref = "decision:lineage"
        occurrence_ref = "occurrence:lineage"
        placement = "reviewed"
        placement_ref = "policy:reviewed"
        proof_refs = ("proof:lineage",)
        provisional = _prepare(
            expression,
            fact_ref=fact_ref,
            source_ref=source_ref,
            decision_ref=decision_ref,
            occurrence_ref=occurrence_ref,
            placement=placement,
            placement_ref=placement_ref,
            proof_refs=proof_refs,
            revision=0,
            commit_transaction_ref="transaction:pending",
        )
        persistent_root = next(
            row
            for row in provisional.applications
            if row.application_ref == provisional.root_application_ref
        )
        operator, args, stance = _normalized_legacy_projection(
            _normalized_application_payload(persistent_root), "support"
        )
        proof = {
            "source": source_ref,
            "decision_ref": decision_ref,
            "occurrence_ref": occurrence_ref,
            "placement": placement,
            "placement_ref": placement_ref,
            "proof_refs": list(proof_refs),
        }
        proof[lineage_field] = (
            ["forged:proof"]
            if lineage_field == "proof_refs"
            else f"forged:{lineage_field}"
        )
        receipt = stores.world.commit(
            (
                Fact(
                    fact_ref=fact_ref,
                    operator=operator,
                    args=args,
                    stance=stance,
                    proof=proof,
                ),
            ),
            expected_revision=stores.world.revision,
        )
        batch = _prepare(
            expression,
            fact_ref=fact_ref,
            source_ref=source_ref,
            decision_ref=decision_ref,
            occurrence_ref=occurrence_ref,
            placement=placement,
            placement_ref=placement_ref,
            proof_refs=proof_refs,
            revision=receipt.new_revision,
            commit_transaction_ref=receipt.transaction_ref,
        )

        with pytest.raises(ValueError, match="lineage|correspond|proof"):
            stores._r3_write_normalized_batch(batch)

        pin = stores.revision_pin()
        with stores.r3_read_snapshot(pin):
            assert stores.r3_application_claims(
                (batch.root_application_ref,), maximum=8, expected_pin=pin
            ) == ()
            assert stores.r3_active_application_claims_for_target(
                "entity:bob", maximum=8, expected_pin=pin
            ) == ()
    finally:
        stores.close()


def test_activation_rejects_same_name_nonunique_fact_ownership_index(tmp_path):
    path = tmp_path / "weakened-fact-index"
    stores = open_stores(path, authority_generation="authority:test")
    stores.close()

    connection = sqlite3.connect(path / "semantic.db")
    try:
        connection.execute("DROP INDEX semantic_application_claims_fact")
        connection.execute(
            "CREATE INDEX semantic_application_claims_fact "
            "ON semantic_application_claims(fact_ref)"
        )
        connection.commit()
    finally:
        connection.close()

    reopened = None
    try:
        with pytest.raises(StoreActivationError):
            reopened = open_stores(path, authority_generation="authority:test")
    finally:
        if reopened is not None:
            reopened.close()


def test_pre_feature_authenticated_alias_store_is_rejected_without_mutation(
    tmp_path, monkeypatch
):
    from cemm_authoritative_hybrid import bootstrap
    from tests.test_foundation_alias_publication import ROOT, _publication, _signed

    runtime, _, _, _, gateway, grant, secret = _publication(
        tmp_path, monkeypatch, "sqlite"
    )
    gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    connection = runtime.stores._backend._conn
    for table in (
        "semantic_claim_target_postings",
        "semantic_claim_retractions",
        "semantic_application_claims",
        "semantic_application_bindings",
        "semantic_applications",
    ):
        connection.execute(f"DROP TABLE {table}")
    connection.execute(
        "DELETE FROM metadata WHERE key='normalized_store_schema_version'"
    )
    connection.commit()
    runtime.stores.close()

    database = tmp_path / "proposal.db" / "semantic.db"

    def snapshot():
        snapshot_connection = sqlite3.connect(database)
        try:
            return (
                tuple(
                    snapshot_connection.execute(
                        "SELECT type,name,tbl_name,sql FROM sqlite_master "
                        "ORDER BY type,name"
                    )
                ),
                tuple(
                    snapshot_connection.execute(
                        "SELECT key,value FROM metadata ORDER BY key"
                    )
                ),
            )
        finally:
            snapshot_connection.close()

    before = snapshot()
    reopened = None
    try:
        with pytest.raises(StoreActivationError):
            reopened = bootstrap.load_runtime(
                ROOT,
                profile="development",
                store_path=tmp_path / "proposal.db",
            )
    finally:
        if reopened is not None:
            reopened.stores.close()

    assert snapshot() == before
