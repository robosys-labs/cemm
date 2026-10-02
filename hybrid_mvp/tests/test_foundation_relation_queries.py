"""Independent reviewed relation-role correspondence; isolated static fixtures."""
from dataclasses import FrozenInstanceError, fields
import inspect
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.authority import DesignationFact
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.expressions import (
    BoundVariable, GroundedReference, RoleBinding, SemanticApplication,
    SemanticExpression, VariableBinder,
)
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_cognition import QueryStatus
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier
from cemm_authoritative_hybrid.coverage import CoverageVerifier
from cemm_authoritative_hybrid.expressions import CompilationFailure, SemanticExpressionCompiler
from cemm_authoritative_hybrid.programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from cemm_authoritative_hybrid.proposal_context import ProposalContext
from cemm_authoritative_hybrid.role_schemas import ReviewedRoleSchemaIndex
from cemm_authoritative_hybrid.verifier import _replay_program
from cemm_authoritative_hybrid.verifier_reconstruction import reconstruct_expected_expression
from tests.test_foundation_semantics import _static_composition_context

ROOT = Path(__file__).resolve().parents[1]


__cemm_test_inventory__ = {'tests/test_foundation_relation_queries.py::test_public_relation_query_preserves_independent_role[leading-subject]': {'activation_phase': 'R2',
                                                                                                                       'assertion_ref': 'assertion:relation-query-public-relation-query-preserves-independent-role-leading-subject',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'form-context',
                                                                                                                       'source_ast_sha256': '1cc4a62dbf8f543c5e8e62e783657ff13157d5b609947368e14c9d65aa326a76'},
 'tests/test_foundation_relation_queries.py::test_public_relation_query_preserves_independent_role[trailing-object]': {'activation_phase': 'R2',
                                                                                                                       'assertion_ref': 'assertion:relation-query-public-relation-query-preserves-independent-role-trailing-object',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'form-context',
                                                                                                                       'source_ast_sha256': '1cc4a62dbf8f543c5e8e62e783657ff13157d5b609947368e14c9d65aa326a76'},
 'tests/test_foundation_relation_queries.py::test_public_relation_query_preserves_independent_role[no-terminal]': {'activation_phase': 'R2',
                                                                                                                   'assertion_ref': 'assertion:relation-query-public-relation-query-preserves-independent-role-no-terminal',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                   'owner_ref': 'form-context',
                                                                                                                   'source_ast_sha256': '1cc4a62dbf8f543c5e8e62e783657ff13157d5b609947368e14c9d65aa326a76'},
 'tests/test_foundation_relation_queries.py::test_asymmetric_evidence_answers_only_requested_relation_role[subject-answer]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:relation-query-asymmetric-evidence-answers-only-requested-relation-role-subject-answer',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'form-context',
                                                                                                                              'source_ast_sha256': 'aeeb21cb56da6ec44c209661a1530306fc8e013df0e9f8ae86a055e9742a6555'},
 'tests/test_foundation_relation_queries.py::test_asymmetric_evidence_answers_only_requested_relation_role[object-answer]': {'activation_phase': 'R2',
                                                                                                                             'assertion_ref': 'assertion:relation-query-asymmetric-evidence-answers-only-requested-relation-role-object-answer',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'form-context',
                                                                                                                             'source_ast_sha256': 'aeeb21cb56da6ec44c209661a1530306fc8e013df0e9f8ae86a055e9742a6555'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[en-leading]': {'activation_phase': 'R2',
                                                                                                                                     'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-en-leading',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'form-context',
                                                                                                                                     'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[en-trailing]': {'activation_phase': 'R2',
                                                                                                                                      'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-en-trailing',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                      'owner_ref': 'form-context',
                                                                                                                                      'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[en-multi-leading]': {'activation_phase': 'R2',
                                                                                                                                           'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-en-multi-leading',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                           'owner_ref': 'form-context',
                                                                                                                                           'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[en-multi-trailing]': {'activation_phase': 'R2',
                                                                                                                                            'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-en-multi-trailing',
                                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                            'owner_ref': 'form-context',
                                                                                                                                            'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[es-leading]': {'activation_phase': 'R2',
                                                                                                                                     'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-es-leading',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'form-context',
                                                                                                                                     'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[es-trailing]': {'activation_phase': 'R2',
                                                                                                                                      'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-es-trailing',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                      'owner_ref': 'form-context',
                                                                                                                                      'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[es-multi-leading]': {'activation_phase': 'R2',
                                                                                                                                           'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-es-multi-leading',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                           'owner_ref': 'form-context',
                                                                                                                                           'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_static_unseen_alias_inherits_exact_query_order_without_pack_changes[es-multi-trailing]': {'activation_phase': 'R2',
                                                                                                                                            'assertion_ref': 'assertion:relation-query-static-unseen-alias-inherits-exact-query-order-without-pack-changes-es-multi-trailing',
                                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                            'owner_ref': 'form-context',
                                                                                                                                            'source_ast_sha256': '610ad40d95ab2fd7e34b55b30042eb91c5b5c385027e6493e6df2ed122e88dbe'},
 'tests/test_foundation_relation_queries.py::test_unlicensed_relation_query_evidence_remains_blocked[fronted-auxiliary]': {'activation_phase': 'R2',
                                                                                                                           'assertion_ref': 'assertion:relation-query-unlicensed-relation-query-evidence-remains-blocked-fronted-auxiliary',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'form-context',
                                                                                                                           'source_ast_sha256': '942e6e99539cf0ccb0f50451f66f62b5999ce1ed77745ee04dc835ec100393d4'},
 'tests/test_foundation_relation_queries.py::test_unlicensed_relation_query_evidence_remains_blocked[unlicensed-polarity]': {'activation_phase': 'R2',
                                                                                                                             'assertion_ref': 'assertion:relation-query-unlicensed-relation-query-evidence-remains-blocked-unlicensed-polarity',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'form-context',
                                                                                                                             'source_ast_sha256': '942e6e99539cf0ccb0f50451f66f62b5999ce1ed77745ee04dc835ec100393d4'},
 'tests/test_foundation_relation_queries.py::test_unlicensed_relation_query_evidence_remains_blocked[connector]': {'activation_phase': 'R2',
                                                                                                                   'assertion_ref': 'assertion:relation-query-unlicensed-relation-query-evidence-remains-blocked-connector',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                   'owner_ref': 'form-context',
                                                                                                                   'source_ast_sha256': '942e6e99539cf0ccb0f50451f66f62b5999ce1ed77745ee04dc835ec100393d4'},
 'tests/test_foundation_relation_queries.py::test_unlicensed_relation_query_evidence_remains_blocked[extra-referent]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:relation-query-unlicensed-relation-query-evidence-remains-blocked-extra-referent',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '942e6e99539cf0ccb0f50451f66f62b5999ce1ed77745ee04dc835ec100393d4'},
 'tests/test_foundation_relation_queries.py::test_unlicensed_relation_query_evidence_remains_blocked[internal-punctuation]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:relation-query-unlicensed-relation-query-evidence-remains-blocked-internal-punctuation',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'form-context',
                                                                                                                              'source_ast_sha256': '942e6e99539cf0ccb0f50451f66f62b5999ce1ed77745ee04dc835ec100393d4'},
 'tests/test_foundation_relation_queries.py::test_relation_query_variable_does_not_leak_to_adjacent_predicate': {'activation_phase': 'R2',
                                                                                                                 'assertion_ref': 'assertion:relation-query-relation-query-variable-does-not-leak-to-adjacent-predicate',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'form-context',
                                                                                                                 'source_ast_sha256': '521d9dff02556ac3074d0b9e6905dd4a6e1625ef10402b20019a248272800348'},
 'tests/test_foundation_relation_queries.py::test_activation_shares_immutable_reviewed_role_schema_identity': {'activation_phase': 'R2',
                                                                                                               'assertion_ref': 'assertion:relation-query-activation-shares-immutable-reviewed-role-schema-identity',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                               'owner_ref': 'form-context',
                                                                                                               'source_ast_sha256': 'a0c02e9b972b35d525c3e6dedeed1aeb7181d950e25a0aeb2d36e520494737c3'},
 'tests/test_foundation_relation_queries.py::test_context_activation_rejects_role_index_from_different_form_pack': {'activation_phase': 'R2',
                                                                                                                    'assertion_ref': 'assertion:relation-query-context-activation-rejects-role-index-from-different-form-pack',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'form-context',
                                                                                                                    'source_ast_sha256': '29624247a74460b12bcb1c0f417d0dc442d6bbcc0cc92470285ce9638a096e6d'},
 'tests/test_foundation_relation_queries.py::test_all_exact_sinks_reconstruct_independent_relation_roles[leading]': {'activation_phase': 'R2',
                                                                                                                     'assertion_ref': 'assertion:relation-query-all-exact-sinks-reconstruct-independent-relation-roles-leading',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'exact-verifier',
                                                                                                                     'source_ast_sha256': 'cd5b62ed8485845f7d7d3cdba74390e75383115883dd5eb1d86fd00ac3b212a0'},
 'tests/test_foundation_relation_queries.py::test_all_exact_sinks_reconstruct_independent_relation_roles[trailing]': {'activation_phase': 'R2',
                                                                                                                      'assertion_ref': 'assertion:relation-query-all-exact-sinks-reconstruct-independent-relation-roles-trailing',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'exact-verifier',
                                                                                                                      'source_ast_sha256': 'cd5b62ed8485845f7d7d3cdba74390e75383115883dd5eb1d86fd00ac3b212a0'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[variable-role]': {'activation_phase': 'R2',
                                                                                                                           'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-variable-role',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'exact-verifier',
                                                                                                                           'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[referent-target]': {'activation_phase': 'R2',
                                                                                                                             'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-referent-target',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'exact-verifier',
                                                                                                                             'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[predicate-source]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-predicate-source',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'exact-verifier',
                                                                                                                              'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[witness]': {'activation_phase': 'R2',
                                                                                                                     'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-witness',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'exact-verifier',
                                                                                                                     'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[person-feature]': {'activation_phase': 'R2',
                                                                                                                            'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-person-feature',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'exact-verifier',
                                                                                                                            'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[foreign-primitive]': {'activation_phase': 'R2',
                                                                                                                               'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-foreign-primitive',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'exact-verifier',
                                                                                                                               'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[noncanonical-primitive]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-noncanonical-primitive',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'exact-verifier',
                                                                                                                                    'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[all-witnesses-missing]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-all-witnesses-missing',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'exact-verifier',
                                                                                                                                   'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[predicate-assignment]': {'activation_phase': 'R2',
                                                                                                                                  'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-predicate-assignment',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'exact-verifier',
                                                                                                                                  'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_rehashed_relation_query_forgeries_fail_all_exact_sinks[referent-assignment]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:relation-query-rehashed-relation-query-forgeries-fail-all-exact-sinks-referent-assignment',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'exact-verifier',
                                                                                                                                 'source_ast_sha256': 'dac770b36150c915ba3ca26a44b1dd4d204540f1f7f467239e7ccdc151b4d80f'},
 'tests/test_foundation_relation_queries.py::test_asymmetric_fact_does_not_support_reverse_relation_answers[reverse-subject]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:relation-query-asymmetric-fact-does-not-support-reverse-relation-answers-reverse-subject',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': '9aae512f0d1a2854c3b9f6964a4d66f74d117e4630e9e363db38d3d46f88efd9'},
 'tests/test_foundation_relation_queries.py::test_asymmetric_fact_does_not_support_reverse_relation_answers[reverse-object]': {'activation_phase': 'R2',
                                                                                                                               'assertion_ref': 'assertion:relation-query-asymmetric-fact-does-not-support-reverse-relation-answers-reverse-object',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'form-context',
                                                                                                                               'source_ast_sha256': '9aae512f0d1a2854c3b9f6964a4d66f74d117e4630e9e363db38d3d46f88efd9'},
 'tests/test_foundation_relation_queries.py::test_authenticated_relation_alias_inherits_roles_after_restart_without_pack_write': {'activation_phase': 'R2',
                                                                                                                                  'assertion_ref': 'assertion:relation-query-authenticated-relation-alias-inherits-roles-after-restart-without-pack-write',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'form-context',
                                                                                                                                  'source_ast_sha256': '9c84eea1c3a4a1cb1dac310bee1096b30b9dd719af976e93f29abdde74e307a4'},
 'tests/test_foundation_relation_queries.py::test_reviewed_role_index_is_generic_and_attempt_bounded': {'activation_phase': 'R2',
                                                                                                        'assertion_ref': 'assertion:relation-query-reviewed-role-index-is-generic-and-attempt-bounded',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                        'owner_ref': 'form-context',
                                                                                                        'source_ast_sha256': '8b7d16f1be05026af45c9c57186f643828099ae5b06d4ae0b820349858a2dc50'},
 'tests/test_foundation_relation_queries.py::test_malformed_role_geometry_fails_closed_at_exact_sinks': {'activation_phase': 'R2',
                                                                                                         'assertion_ref': 'assertion:relation-query-malformed-role-geometry-fails-closed-at-exact-sinks',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                         'owner_ref': 'exact-verifier',
                                                                                                         'source_ast_sha256': '99b841617e907b4959da97916c27b2a7d5a046f211fc0cf3cf0f39ee778452ab'},
 'tests/test_foundation_relation_queries.py::test_public_role_match_overflow_is_typed_budget_without_pin_change': {'activation_phase': 'R2',
                                                                                                                   'assertion_ref': 'assertion:relation-query-public-role-match-overflow-is-typed-budget-without-pin-change',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                   'owner_ref': 'form-context',
                                                                                                                   'source_ast_sha256': '9bd58c3e199d3dfa1c5f1cfaade8a632686afe1b218c473eaf504ee25d9a0149'},
 'tests/test_foundation_relation_queries.py::test_absent_typed_query_feature_does_not_spend_role_match_budget': {'activation_phase': 'R2',
                                                                                                                 'assertion_ref': 'assertion:relation-query-absent-typed-query-feature-does-not-spend-role-match-budget',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'form-context',
                                                                                                                 'source_ast_sha256': 'a0189a481966ae9628f15bcc530165dac7a74045d8b021ab4ca3275d5b27be52'},
 'tests/test_foundation_relation_queries.py::test_relation_query_pack_preserves_all_predecessor_fields': {'activation_phase': 'R2',
                                                                                                          'assertion_ref': 'assertion:foundation-retiring-definition-cue-preserves-all-other-reviewed-form-fields',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                          'owner_ref': 'form-context',
                                                                                                          'source_ast_sha256': '7e718553d7f25521cd984576a010f0de8680028fda3fdeef55c7b29808a523df',
                                                                                                          'supersedes_node_id': 'tests/test_foundation_semantics.py::test_foundation_lexical_pack_preserves_all_predecessor_fields'},
 'tests/test_foundation_relation_queries.py::test_spanish_relation_pack_preserves_all_undeclared_predecessor_fields': {'activation_phase': 'R2',
                                                                                                                       'assertion_ref': 'assertion:relation-query-spanish-relation-pack-preserves-all-undeclared-predecessor-fields',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'form-context',
                                                                                                                       'source_ast_sha256': 'feedde1e7543a720a7900e07713afa70c2e69565ea4bb04f617f50db150d256b'},
 'tests/test_foundation_relation_queries.py::test_relation_query_requires_current_pinned_index_at_every_exact_sink[missing]': {'activation_phase': 'R2',
                                                                                                                               'assertion_ref': 'assertion:relation-query-relation-query-requires-current-pinned-index-at-every-exact-sink-missing',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'exact-verifier',
                                                                                                                               'source_ast_sha256': '67817018f08102af6a3bbbfe4d793c201371b72cc5a635dd7838da43cb26132c'},
 'tests/test_foundation_relation_queries.py::test_relation_query_requires_current_pinned_index_at_every_exact_sink[stale-generation]': {'activation_phase': 'R2',
                                                                                                                                        'assertion_ref': 'assertion:relation-query-relation-query-requires-current-pinned-index-at-every-exact-sink-stale-generation',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'exact-verifier',
                                                                                                                                        'source_ast_sha256': '67817018f08102af6a3bbbfe4d793c201371b72cc5a635dd7838da43cb26132c'},
 'tests/test_foundation_relation_queries.py::test_relation_query_requires_current_pinned_index_at_every_exact_sink[different-pack]': {'activation_phase': 'R2',
                                                                                                                                      'assertion_ref': 'assertion:relation-query-relation-query-requires-current-pinned-index-at-every-exact-sink-different-pack',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                      'owner_ref': 'exact-verifier',
                                                                                                                                      'source_ast_sha256': '67817018f08102af6a3bbbfe4d793c201371b72cc5a635dd7838da43cb26132c'},
 'tests/test_foundation_relation_queries.py::test_relation_query_requires_current_pinned_index_at_every_exact_sink[different-content]': {'activation_phase': 'R2',
                                                                                                                                         'assertion_ref': 'assertion:relation-query-relation-query-requires-current-pinned-index-at-every-exact-sink-different-content',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                         'owner_ref': 'exact-verifier',
                                                                                                                                         'source_ast_sha256': '67817018f08102af6a3bbbfe4d793c201371b72cc5a635dd7838da43cb26132c'},
 'tests/test_foundation_relation_queries.py::test_relation_query_requires_current_pinned_index_at_every_exact_sink[changed-attempt-bound]': {'activation_phase': 'R2',
                                                                                                                                             'assertion_ref': 'assertion:relation-query-relation-query-requires-current-pinned-index-at-every-exact-sink-changed-attempt-bound',
                                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                             'owner_ref': 'exact-verifier',
                                                                                                                                             'source_ast_sha256': '67817018f08102af6a3bbbfe4d793c201371b72cc5a635dd7838da43cb26132c'},
 'tests/test_foundation_relation_queries.py::test_polysemous_referent_preserves_both_role_graphs_until_exact_settling[en-leading]': {'activation_phase': 'R2',
                                                                                                                                     'assertion_ref': 'assertion:relation-query-polysemous-referent-preserves-both-role-graphs-until-exact-settling-en-leading',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'form-context',
                                                                                                                                     'source_ast_sha256': '547d72785e9bc609a60ffa3a5fb65c571f0145f5ee923337139733997de7957e'},
 'tests/test_foundation_relation_queries.py::test_polysemous_referent_preserves_both_role_graphs_until_exact_settling[en-trailing]': {'activation_phase': 'R2',
                                                                                                                                      'assertion_ref': 'assertion:relation-query-polysemous-referent-preserves-both-role-graphs-until-exact-settling-en-trailing',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                      'owner_ref': 'form-context',
                                                                                                                                      'source_ast_sha256': '547d72785e9bc609a60ffa3a5fb65c571f0145f5ee923337139733997de7957e'},
 'tests/test_foundation_relation_queries.py::test_polysemous_referent_preserves_both_role_graphs_until_exact_settling[es-leading]': {'activation_phase': 'R2',
                                                                                                                                     'assertion_ref': 'assertion:relation-query-polysemous-referent-preserves-both-role-graphs-until-exact-settling-es-leading',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'form-context',
                                                                                                                                     'source_ast_sha256': '547d72785e9bc609a60ffa3a5fb65c571f0145f5ee923337139733997de7957e'},
 'tests/test_foundation_relation_queries.py::test_polysemous_referent_preserves_both_role_graphs_until_exact_settling[es-trailing]': {'activation_phase': 'R2',
                                                                                                                                      'assertion_ref': 'assertion:relation-query-polysemous-referent-preserves-both-role-graphs-until-exact-settling-es-trailing',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                      'owner_ref': 'form-context',
                                                                                                                                      'source_ast_sha256': '547d72785e9bc609a60ffa3a5fb65c571f0145f5ee923337139733997de7957e'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[en-modal]': {'activation_phase': 'R2',
                                                                                                                             'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-en-modal',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'form-context',
                                                                                                                             'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[en-negative]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-en-negative',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[en-connector]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-en-connector',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[en-punctuation]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-en-punctuation',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'form-context',
                                                                                                                                   'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[en-linker]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-en-linker',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'form-context',
                                                                                                                              'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[en-referent-negative]': {'activation_phase': 'R2',
                                                                                                                                         'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-en-referent-negative',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                         'owner_ref': 'form-context',
                                                                                                                                         'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[es-modal]': {'activation_phase': 'R2',
                                                                                                                             'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-es-modal',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'form-context',
                                                                                                                             'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[es-negative]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-es-negative',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[es-connector]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-es-connector',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[es-punctuation]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-es-punctuation',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'form-context',
                                                                                                                                   'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[es-linker]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-es-linker',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'form-context',
                                                                                                                              'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_closed_primitive_evidence[es-referent-negative]': {'activation_phase': 'R2',
                                                                                                                                         'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-closed-primitive-evidence-es-referent-negative',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                         'owner_ref': 'form-context',
                                                                                                                                         'source_ast_sha256': '9b82779400c0bda6bcb2f8872c0d891c55d6bf424c4d972f29f1c9eb9eb5a39f'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[modal]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-modal',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'exact-verifier',
                                                                                                                                 'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[negative]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-negative',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'exact-verifier',
                                                                                                                                    'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[connector]': {'activation_phase': 'R2',
                                                                                                                                     'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-connector',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'exact-verifier',
                                                                                                                                     'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[punctuation]': {'activation_phase': 'R2',
                                                                                                                                       'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-punctuation',
                                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                       'owner_ref': 'exact-verifier',
                                                                                                                                       'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[linker]': {'activation_phase': 'R2',
                                                                                                                                  'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-linker',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'exact-verifier',
                                                                                                                                  'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[en-addressee]': {'activation_phase': 'R2',
                                                                                                                                        'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-en-addressee',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'exact-verifier',
                                                                                                                                        'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[en-speaker]': {'activation_phase': 'R2',
                                                                                                                                      'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-en-speaker',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                      'owner_ref': 'exact-verifier',
                                                                                                                                      'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[en-possessive]': {'activation_phase': 'R2',
                                                                                                                                         'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-en-possessive',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                         'owner_ref': 'exact-verifier',
                                                                                                                                         'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[en-trailing-deixis]': {'activation_phase': 'R2',
                                                                                                                                              'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-en-trailing-deixis',
                                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                              'owner_ref': 'exact-verifier',
                                                                                                                                              'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[es-speaker]': {'activation_phase': 'R2',
                                                                                                                                      'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-es-speaker',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                      'owner_ref': 'exact-verifier',
                                                                                                                                      'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[es-trailing-deixis]': {'activation_phase': 'R2',
                                                                                                                                              'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-es-trailing-deixis',
                                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                              'owner_ref': 'exact-verifier',
                                                                                                                                              'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[es-possessive]': {'activation_phase': 'R2',
                                                                                                                                         'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-es-possessive',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                         'owner_ref': 'exact-verifier',
                                                                                                                                         'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[es-addressee]': {'activation_phase': 'R2',
                                                                                                                                        'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-es-addressee',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'exact-verifier',
                                                                                                                                        'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[en-other-unresolved]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-en-other-unresolved',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'exact-verifier',
                                                                                                                                               'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[en-proximal-unresolved]': {'activation_phase': 'R2',
                                                                                                                                                  'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-en-proximal-unresolved',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                  'owner_ref': 'exact-verifier',
                                                                                                                                                  'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[en-group-unresolved]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-en-group-unresolved',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'exact-verifier',
                                                                                                                                               'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[es-other-unresolved]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-es-other-unresolved',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'exact-verifier',
                                                                                                                                               'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[es-proximal-unresolved]': {'activation_phase': 'R2',
                                                                                                                                                  'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-es-proximal-unresolved',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                  'owner_ref': 'exact-verifier',
                                                                                                                                                  'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks[es-group-unresolved]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:relation-query-self-rehashed-overlap-witness-cannot-erase-primitives-at-exact-sinks-es-group-unresolved',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'exact-verifier',
                                                                                                                                               'source_ast_sha256': '715016d0ffe165e41de42a9ec9de85b629960f6ae6e688fcdfea179d3cdfbd1c'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[en-addressee]': {'activation_phase': 'R2',
                                                                                                                                          'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-en-addressee',
                                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                          'owner_ref': 'form-context',
                                                                                                                                          'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[en-speaker]': {'activation_phase': 'R2',
                                                                                                                                        'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-en-speaker',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'form-context',
                                                                                                                                        'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[en-possessive]': {'activation_phase': 'R2',
                                                                                                                                           'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-en-possessive',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                           'owner_ref': 'form-context',
                                                                                                                                           'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[en-trailing-deixis]': {'activation_phase': 'R2',
                                                                                                                                                'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-en-trailing-deixis',
                                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                                'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[es-speaker]': {'activation_phase': 'R2',
                                                                                                                                        'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-es-speaker',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'form-context',
                                                                                                                                        'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[es-trailing-deixis]': {'activation_phase': 'R2',
                                                                                                                                                'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-es-trailing-deixis',
                                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                                'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[es-possessive]': {'activation_phase': 'R2',
                                                                                                                                           'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-es-possessive',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                           'owner_ref': 'form-context',
                                                                                                                                           'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[es-addressee]': {'activation_phase': 'R2',
                                                                                                                                          'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-es-addressee',
                                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                          'owner_ref': 'form-context',
                                                                                                                                          'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[en-referent-deixis]': {'activation_phase': 'R2',
                                                                                                                                                'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-en-referent-deixis',
                                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                                'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_relation_designation_cannot_swallow_target_bearing_primitive_reference[es-referent-deixis]': {'activation_phase': 'R2',
                                                                                                                                                'assertion_ref': 'assertion:relation-query-relation-designation-cannot-swallow-target-bearing-primitive-reference-es-referent-deixis',
                                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                                'source_ast_sha256': 'c36867e3ae65f6c7fe86558effd99424fed578c6201823f102c254ae3aa5a614'},
 'tests/test_foundation_relation_queries.py::test_unresolved_primitive_reference_retains_owned_requirement_and_blocks_relation_alias[en-other]': {'activation_phase': 'R2',
                                                                                                                                                  'assertion_ref': 'assertion:relation-query-unresolved-primitive-reference-retains-owned-requirement-and-blocks-relation-alias-en-other',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                  'owner_ref': 'form-context',
                                                                                                                                                  'source_ast_sha256': '525a895e482d55ccd3c9f3ad2643cf317339c41834538ff6cc5de609481dbf6d'},
 'tests/test_foundation_relation_queries.py::test_unresolved_primitive_reference_retains_owned_requirement_and_blocks_relation_alias[en-proximal]': {'activation_phase': 'R2',
                                                                                                                                                     'assertion_ref': 'assertion:relation-query-unresolved-primitive-reference-retains-owned-requirement-and-blocks-relation-alias-en-proximal',
                                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                     'owner_ref': 'form-context',
                                                                                                                                                     'source_ast_sha256': '525a895e482d55ccd3c9f3ad2643cf317339c41834538ff6cc5de609481dbf6d'},
 'tests/test_foundation_relation_queries.py::test_unresolved_primitive_reference_retains_owned_requirement_and_blocks_relation_alias[en-group]': {'activation_phase': 'R2',
                                                                                                                                                  'assertion_ref': 'assertion:relation-query-unresolved-primitive-reference-retains-owned-requirement-and-blocks-relation-alias-en-group',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                  'owner_ref': 'form-context',
                                                                                                                                                  'source_ast_sha256': '525a895e482d55ccd3c9f3ad2643cf317339c41834538ff6cc5de609481dbf6d'},
 'tests/test_foundation_relation_queries.py::test_unresolved_primitive_reference_retains_owned_requirement_and_blocks_relation_alias[es-other]': {'activation_phase': 'R2',
                                                                                                                                                  'assertion_ref': 'assertion:relation-query-unresolved-primitive-reference-retains-owned-requirement-and-blocks-relation-alias-es-other',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                  'owner_ref': 'form-context',
                                                                                                                                                  'source_ast_sha256': '525a895e482d55ccd3c9f3ad2643cf317339c41834538ff6cc5de609481dbf6d'},
 'tests/test_foundation_relation_queries.py::test_unresolved_primitive_reference_retains_owned_requirement_and_blocks_relation_alias[es-proximal]': {'activation_phase': 'R2',
                                                                                                                                                     'assertion_ref': 'assertion:relation-query-unresolved-primitive-reference-retains-owned-requirement-and-blocks-relation-alias-es-proximal',
                                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                     'owner_ref': 'form-context',
                                                                                                                                                     'source_ast_sha256': '525a895e482d55ccd3c9f3ad2643cf317339c41834538ff6cc5de609481dbf6d'},
 'tests/test_foundation_relation_queries.py::test_unresolved_primitive_reference_retains_owned_requirement_and_blocks_relation_alias[es-group]': {'activation_phase': 'R2',
                                                                                                                                                  'assertion_ref': 'assertion:relation-query-unresolved-primitive-reference-retains-owned-requirement-and-blocks-relation-alias-es-group',
                                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                  'owner_ref': 'form-context',
                                                                                                                                                  'source_ast_sha256': '525a895e482d55ccd3c9f3ad2643cf317339c41834538ff6cc5de609481dbf6d'},
 'tests/test_foundation_relation_queries.py::test_ordinary_separate_participant_reference_keeps_its_exact_role[en-speaker]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:relation-query-ordinary-separate-participant-reference-keeps-its-exact-role-en-speaker',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'form-context',
                                                                                                                              'source_ast_sha256': '59b2acb4e8c84e2bf85e530cb08cb4555e735f8683e2a446be7079c5630709fe'},
 'tests/test_foundation_relation_queries.py::test_ordinary_separate_participant_reference_keeps_its_exact_role[en-addressee]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:relation-query-ordinary-separate-participant-reference-keeps-its-exact-role-en-addressee',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': '59b2acb4e8c84e2bf85e530cb08cb4555e735f8683e2a446be7079c5630709fe'},
 'tests/test_foundation_relation_queries.py::test_ordinary_separate_participant_reference_keeps_its_exact_role[es-speaker]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:relation-query-ordinary-separate-participant-reference-keeps-its-exact-role-es-speaker',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'form-context',
                                                                                                                              'source_ast_sha256': '59b2acb4e8c84e2bf85e530cb08cb4555e735f8683e2a446be7079c5630709fe'},
 'tests/test_foundation_relation_queries.py::test_ordinary_separate_participant_reference_keeps_its_exact_role[es-addressee]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:relation-query-ordinary-separate-participant-reference-keeps-its-exact-role-es-addressee',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': '59b2acb4e8c84e2bf85e530cb08cb4555e735f8683e2a446be7079c5630709fe'}}


def _expected(variable_role, target):
    other_role = "role:object" if variable_role == "role:subject" else "role:subject"
    app = SemanticApplication("application:independent-relation", "op:relation", "rel:likes", (
        RoleBinding(variable_role, BoundVariable("?person")),
        RoleBinding(other_role, GroundedReference(target)),
    ))
    binder = VariableBinder("binder:independent-person", "?person", app.application_ref)
    return SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))


@pytest.mark.parametrize("surface,role,target", (
    ("Who likes Bob?", "role:subject", "entity:bob"),
    ("Alice likes who?", "role:object", "entity:alice"),
    ("Who likes Bob", "role:subject", "entity:bob"),
), ids=("leading-subject", "trailing-object", "no-terminal"))
def test_public_relation_query_preserves_independent_role(surface, role, target, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "public.db")
    try:
        result = runtime.process("session:relation-role", surface)
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == _expected(role, target)
        assert not result.proposal.truncated and result.proposal.explored_states <= 7
        assert result.evaluation.query_results[0].status is QueryStatus.UNKNOWN
        assert result.evaluation.query_results[0].bindings == ()
        assert runtime.stores.world.revision == 0 and runtime.stores.r3_world_facts() == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface,answer", (
    ("Who likes Bob?", "entity:alice"), ("Alice likes who?", "entity:bob"),
), ids=("subject-answer", "object-answer"))
def test_asymmetric_evidence_answers_only_requested_relation_role(surface, answer, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "asymmetric.db")
    try:
        runtime.stores.world.commit((Fact("fact:independent-asymmetric", "op:relation", {
            "predicate_ref": "rel:likes", "role:subject": "entity:alice", "role:object": "entity:bob",
        }, proof={"source": "source:independent-asymmetric"}),), expected_revision=0)
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:relation-answer", surface)
        query = result.evaluation.query_results[0]
        assert query.status is QueryStatus.SUPPORTED
        assert len(query.bindings) == 1
        assert tuple(value for _, value in query.bindings) == (answer,)
        assert query.proof is not None and "source:independent-asymmetric" in query.proof.source_refs
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,alias,leading", (
    ("en", "velnora", True), ("en", "velnora", False),
    ("en", "velnora luz", True), ("en", "velnora luz", False),
    ("es", "velnora", True), ("es", "velnora", False),
    ("es", "luz velnora", True), ("es", "luz velnora", False),
), ids=("en-leading", "en-trailing", "en-multi-leading", "en-multi-trailing",
         "es-leading", "es-trailing", "es-multi-leading", "es-multi-trailing"))
def test_static_unseen_alias_inherits_exact_query_order_without_pack_changes(language, alias, leading, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "static.db")
    pack_path = ROOT / "data/languages" / language / "forms.json"
    before = pack_path.read_bytes()
    pack = json.loads(before)
    question = "who" if language == "en" else "qui\u00e9n"
    surface = f"{question} {alias} Bob?" if leading else f"Alice {alias} {question}?"
    facts = tuple(DesignationFact.create(surface=label, target_ref=target, language=language)
                  for label, target in (("Alice", "entity:alice"), ("Bob", "entity:bob"), (alias, "rel:likes")))
    try:
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, surface, facts=facts)
        proposal = runtime.proposal_model.propose(context)
        result = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
        assert result.selected_meaning is not None
        assert result.selected_meaning.expression == _expected(
            "role:subject" if leading else "role:object", "entity:bob" if leading else "entity:alice")
        assert not proposal.truncated and proposal.explored_states <= 7
        assert pack_path.read_bytes() == before
        assert runtime.stores.world.revision == 0 and runtime.stores.r3_world_facts() == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", (
    "Who does Alice likes?", "Who never likes Bob?", "Who likes Bob and Alice likes Bob?",
    "Who likes Bob Carol?", "Who likes Bob, Alice?",
), ids=("fronted-auxiliary", "unlicensed-polarity", "connector", "extra-referent", "internal-punctuation"))
def test_unlicensed_relation_query_evidence_remains_blocked(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "blocked.db")
    try:
        _, context = runtime.orient("session:relation-blocked", surface)
        assert not any(context.frame(row.application_frame_ref).operator_ref == "op:relation" for row in context.variable_slots)
        if "does" in surface:
            assert any(row.kind == "binder" and ("query", "query_auxiliary") in row.constraints for row in context.contribution_slots)
        result = runtime.process("session:relation-blocked", surface)
        assert result.verification.selected_meaning is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_relation_query_variable_does_not_leak_to_adjacent_predicate(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "local.db")
    try:
        _, context = runtime.orient("session:relation-local", "Who likes Bob? Alice likes Bob.")
        variables = tuple(row for row in context.variable_slots if context.frame(row.application_frame_ref).operator_ref == "op:relation")
        assert len(variables) == 1 and variables[0].role_ref == "role:subject"
        assert context.source_span(context.frame(variables[0].application_frame_ref).source_unit_refs)[0] < 14
    finally:
        runtime.stores.close()


def test_activation_shares_immutable_reviewed_role_schema_identity(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "activation.db")
    try:
        builder = runtime._owners["orientation"]._context_builder
        verifier = runtime._owners["verification"]
        index = builder.role_schema_index
        assert type(index) is ReviewedRoleSchemaIndex
        assert verifier.role_schema_index is index
        assert verifier._coverage.role_schema_index is index
        assert verifier._compiler.role_schema_index is index
        assert index.authority_generation == runtime.authority.generation
        assert index.authority_content_hash == runtime.authority.content_hash
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            index.authority_generation = "authority:forged"
        assert type(index.schemas) is tuple
        assert all(type(row.selectors) is tuple for row in index.schemas)
    finally:
        runtime.stores.close()


def test_context_activation_rejects_role_index_from_different_form_pack(tmp_path):
    from cemm_authoritative_hybrid.proposal_context import ProposalContextBuilder
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "foreign-pack.db")
    try:
        builder = runtime._owners["orientation"]._context_builder
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
        foreign_pack = {**pack, "language": "foreign-reviewed-pack"}
        foreign = ReviewedRoleSchemaIndex.from_pack(foreign_pack, runtime.authority, runtime._config)
        with pytest.raises(ValueError, match="form pack"):
            ProposalContextBuilder(runtime.authority, builder._affordance_index, runtime._config,
                form_pack=pack, role_schema_index=foreign)
    finally:
        runtime.stores.close()


def _slot_with(slot, **changes):
    return type(slot).create(**{**{f.name: getattr(slot, f.name) for f in fields(slot)
                                  if f.name != "slot_ref"}, **changes})


def _rehash_derivation(context, program, replacements):
    """Forge canonical identities too; rejection cannot depend on stale hashes."""
    pointers = {}
    def rewrite(value):
        if isinstance(value, str):
            return pointers.get(value, value)
        if isinstance(value, tuple):
            return tuple(rewrite(part) for part in value)
        return value
    values = {name: getattr(context, name) for name in inspect.signature(ProposalContext.create).parameters
              if name != "config"}
    for name in ("designation_slots", "contribution_slots", "application_frames", "reference_slots", "variable_slots"):
        rows = []
        for old in values[name]:
            row = replacements.get(old.slot_ref, old)
            row = type(row).create(**{f.name: rewrite(getattr(row, f.name)) for f in fields(row) if f.name != "slot_ref"})
            pointers[old.slot_ref] = row.slot_ref
            rows.append(row)
        values[name] = tuple(rows)
    forged = ProposalContext.create(**values)
    pointers[context.context_ref] = forged.context_ref
    actions = []
    for old in program.actions:
        action = ProgramAction.create(action_index=old.action_index, action_type=old.action_type,
            arguments=rewrite(old.arguments), source_unit_refs=old.source_unit_refs)
        pointers[old.action_ref] = action.action_ref
        actions.append(action)
    assignments = tuple(SourceAssignment.create(**{f.name: rewrite(getattr(old, f.name))
        for f in fields(old) if f.name != "assignment_ref"}) for old in program.source_assignments)
    program_values = {f.name: getattr(program, f.name) for f in fields(program) if f.name != "program_ref"}
    program_values.update(proposal_context_ref=forged.context_ref, actions=tuple(actions), source_assignments=assignments)
    return forged, SemanticSwitchProgram.create(**program_values)


@pytest.mark.parametrize("surface,role,target", (
    ("Who likes Bob?", "role:subject", "entity:bob"),
    ("Alice likes who?", "role:object", "entity:alice"),
), ids=("leading", "trailing"))
def test_all_exact_sinks_reconstruct_independent_relation_roles(surface, role, target, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "sinks.db")
    try:
        _, context = runtime.orient("session:exact-sinks", surface)
        proposal = runtime.proposal_model.propose(context)
        program = proposal.candidates[0].program
        index = runtime._owners["verification"].role_schema_index
        assert CoverageVerifier(role_schema_index=index).verify(context, program).executable
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, context)
        assert not isinstance(compiled, CompilationFailure)
        assert compiled.expression == _expected(role, target)
        assert reconstruct_expected_expression(program, context, role_schema_index=index) == _expected(role, target)
        assert _replay_program(program, context, role_schema_index=index) == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation", ("variable-role", "referent-target", "predicate-source", "witness", "person-feature", "foreign-primitive", "noncanonical-primitive", "all-witnesses-missing", "predicate-assignment", "referent-assignment"),
    ids=("variable-role", "referent-target", "predicate-source", "witness", "person-feature", "foreign-primitive", "noncanonical-primitive", "all-witnesses-missing", "predicate-assignment", "referent-assignment"))
def test_rehashed_relation_query_forgeries_fail_all_exact_sinks(mutation, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "forgery.db")
    try:
        _, context = runtime.orient("session:forgery", "Who likes Bob?")
        program = runtime.proposal_model.propose(context).candidates[0].program
        replacements = {}
        if mutation == "variable-role":
            row = context.variable_slots[0]
            replacements[row.slot_ref] = _slot_with(row, role_ref="role:object")
        elif mutation == "referent-target":
            row = next(r for r in context.reference_slots if r.target_ref == "entity:bob")
            replacements[row.slot_ref] = _slot_with(row, target_ref="entity:alice")
        elif mutation == "predicate-source":
            row = next(f for f in context.application_frames if f.operator_ref == "op:relation")
            replacements[row.slot_ref] = _slot_with(row, source_unit_refs=("unit:4",))
            for contribution in context.contribution_slots:
                if contribution.kind == "predicate" and contribution.target_ref == "rel:likes":
                    replacements[contribution.slot_ref] = _slot_with(contribution, source_unit_refs=("unit:4",))
        elif mutation == "witness":
            row = next(c for c in context.contribution_slots if c.kind == "predicate")
            replacements[row.slot_ref] = _slot_with(row, constraints=tuple(
                (key, "reviewed_role_match:forged" if key == "role_schema_match" else value)
                for key, value in row.constraints))
        elif mutation == "person-feature":
            row = next(c for c in context.contribution_slots if c.kind == "open_variable")
            replacements[row.slot_ref] = _slot_with(row, constraints=(("query", "query"), ("interrogative", "content")))
        elif mutation in {"foreign-primitive", "noncanonical-primitive"}:
            row = next(c for c in context.contribution_slots if c.kind == "open_variable")
            replacements[row.slot_ref] = _slot_with(row, **(
                {"provenance_refs": ("unit:4",)} if mutation == "foreign-primitive"
                else {"contribution_ref": "form_contribution:forged"}))
        elif mutation == "all-witnesses-missing":
            witness_refs = set(context.variable_slots[0].construction_ref for _ in (0,))
            for row in context.contribution_slots:
                if row.kind == "predicate":
                    witness_refs.update(value for key, value in row.constraints if key in {"role_schema_index", "role_schema", "role_schema_match"})
            for row in context.contribution_slots:
                if row.kind in {"predicate", "open_variable"}:
                    replacements[row.slot_ref] = _slot_with(row, constraints=(),
                        provenance_refs=tuple(ref for ref in row.provenance_refs if ref not in witness_refs))
            for row in context.application_frames:
                if row.operator_ref == "op:relation":
                    replacements[row.slot_ref] = _slot_with(row, provenance_refs=tuple(ref for ref in row.provenance_refs if ref not in witness_refs))
            row = context.variable_slots[0]
            replacements[row.slot_ref] = _slot_with(row, construction_ref=None)
        forged, forgery = _rehash_derivation(context, program, replacements)
        if mutation in {"predicate-assignment", "referent-assignment"}:
            assignment_kind = "predicate" if mutation == "predicate-assignment" else "reference"
            assignments = []
            for assignment in forgery.source_assignments:
                values = {f.name: getattr(assignment, f.name) for f in fields(assignment) if f.name != "assignment_ref"}
                if assignment.assignment_kind == assignment_kind:
                    if assignment_kind == "predicate":
                        values["contribution_slot_ref"] = next(c.slot_ref for c in context.contribution_slots if c.kind == "open_variable")
                    else:
                        values["target_role_ref"] = "role:subject"
                assignments.append(SourceAssignment.create(**values))
            values = {f.name: getattr(forgery, f.name) for f in fields(forgery) if f.name != "program_ref"}
            forgery = SemanticSwitchProgram.create(**{**values, "source_assignments": tuple(assignments)})
        else:
            assert forged.context_ref != context.context_ref
        assert forgery.program_ref != program.program_ref
        index = runtime._owners["verification"].role_schema_index
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(forgery, forged)
        assert isinstance(compiled, CompilationFailure) and compiled.code.startswith("relation_query_")
        coverage = CoverageVerifier(role_schema_index=index).verify(forged, forgery)
        assert not coverage.executable
        assert any(e.code.startswith("relation_query_") for e in coverage.errors)
        assert reconstruct_expected_expression(forgery, forged, role_schema_index=index) is None
        assert any(e.code.startswith("relation_query_") for e in _replay_program(forgery, forged, role_schema_index=index))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", ("Who likes Alice?", "Bob likes who?"), ids=("reverse-subject", "reverse-object"))
def test_asymmetric_fact_does_not_support_reverse_relation_answers(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "reverse.db")
    try:
        runtime.stores.world.commit((Fact("fact:asymmetric-negative", "op:relation", {
            "predicate_ref": "rel:likes", "role:subject": "entity:alice", "role:object": "entity:bob",
        }, proof={"source": "source:asymmetric-negative"}),), expected_revision=0)
        result = runtime.process("session:reverse", surface)
        assert result.verification.selected_meaning is not None
        assert result.evaluation.query_results[0].status is QueryStatus.UNKNOWN
        assert result.evaluation.query_results[0].bindings == ()
        assert runtime.stores.world.revision == 1
    finally:
        runtime.stores.close()


def test_authenticated_relation_alias_inherits_roles_after_restart_without_pack_write(tmp_path, monkeypatch):
    from tests.test_foundation_alias_publication import _publication, _signed
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    pack_path = ROOT / "data/languages/en/forms.json"
    before = pack_path.read_bytes()
    store_path = tmp_path / "proposal.db"
    try:
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert receipt.committed_fact_refs
        assert pack_path.read_bytes() == before
        revision = runtime.stores.world.revision
        for surface, role, target in (("Who velnora Bob?", "role:subject", "entity:bob"),
                                      ("Alice velnora who?", "role:object", "entity:alice")):
            result = runtime.process("session:authenticated-alias", surface)
            assert result.verification.selected_meaning.expression == _expected(role, target)
            assert not result.proposal.truncated and result.proposal.explored_states <= 7
        assert runtime.stores.world.revision == revision
    finally:
        runtime.stores.close()
    reopened = load_runtime(ROOT, profile="development", store_path=store_path)
    try:
        result = reopened.process("session:reopened-alias", "Who velnora Bob?")
        assert result.verification.selected_meaning.expression == _expected("role:subject", "entity:bob")
        assert reopened.stores.world.revision == revision
        assert pack_path.read_bytes() == before
    finally:
        reopened.stores.close()


def test_reviewed_role_index_is_generic_and_attempt_bounded(tmp_path):
    from cemm_authoritative_hybrid.config import RuntimeConfig
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "generic.db")
    try:
        _, context = runtime.orient("session:generic", "Who likes Bob?")
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
        pack["application_role_orders"] = {"typed-membership-evidence": {
            "target_kinds": ["concept"], "roles": ["role:class"],
            "evidence_order": [
                {"kind": "feature", "features": [["query", "query"], ["interrogative", "person"]], "role": "role:instance"},
                {"kind": "designation", "target_kind": "concept", "role": "role:class"},
            ],
        }}
        generic = ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, RuntimeConfig.release())
        assert len(generic.schemas[0].selectors) == 2
        builder, unrelated = _static_composition_context(runtime.authority, runtime.stores, pack,
            "who mother?", facts=(DesignationFact.create(surface="mother", target_ref="concept:mother", language="en"),))
        unrelated_matches = generic.matches(unrelated.designation_slots, unrelated.contribution_slots, unrelated.source_unit_spans)
        assert len(unrelated_matches) == 1
        assert tuple(binding.role for binding in unrelated_matches[0].bindings) == ("role:instance", "role:class")
        assert not any(frame.operator_ref == "op:relation" for frame in unrelated.application_frames)
        # Extra semantic evidence prevents completion while ambiguous prefixes
        # still exercise the attempted-transition bound, not a success counter.
        _, context = runtime.orient("session:attempt-bound", "Alice likes Bob who?")
        bounded = runtime._owners["verification"].role_schema_index
        designations = tuple(_slot_with(row, designation_fact_ref=f"designation:alternative-{i}")
                             for row in context.designation_slots if row.target_ref in {"entity:alice", "rel:likes"}
                             for i in range(8))
        from cemm_authoritative_hybrid.gaps import BudgetExhausted
        with pytest.raises(BudgetExhausted) as exhausted:
            bounded.matches(designations, context.contribution_slots, context.source_unit_spans)
        assert exhausted.value.budget_name == "reviewed_role_match_attempts"
    finally:
        runtime.stores.close()


def test_malformed_role_geometry_fails_closed_at_exact_sinks(tmp_path):
    import copy
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "geometry.db")
    try:
        _, context = runtime.orient("session:geometry", "Who likes Bob?")
        program = runtime.proposal_model.propose(context).candidates[0].program
        forged = copy.copy(context)
        object.__setattr__(forged, "source_unit_spans", (("unit:0", 4, 2), *context.source_unit_spans[1:]))
        index = runtime._owners["verification"].role_schema_index
        assert not CoverageVerifier(role_schema_index=index).verify(forged, program).executable
        assert isinstance(SemanticExpressionCompiler(role_schema_index=index).compile(program, forged), CompilationFailure)
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert _replay_program(program, forged, role_schema_index=index)
    finally:
        runtime.stores.close()


def test_public_role_match_overflow_is_typed_budget_without_pin_change(tmp_path):
    from dataclasses import replace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.cycle import CycleStatus
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "overflow.db")
    try:
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
        isolated = ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority,
            replace(RuntimeConfig.release(), max_beam_states=1))
        runtime._owners["orientation"]._context_builder.role_schema_index = isolated
        before = runtime.stores.revision_pin()
        result = runtime.process("session:role-budget", "Who likes Bob?")
        assert result.status is CycleStatus.BUDGET_EXHAUSTED
        assert result.gap_receipt.status == "budget_exhausted"
        assert result.proposal is None and result.verification is None and result.evaluation is None
        assert result.final_revision_pin == before == runtime.stores.revision_pin()
        assert RuntimeConfig.release().max_beam_states == 32
    finally:
        runtime.stores.close()


def test_absent_typed_query_feature_does_not_spend_role_match_budget(tmp_path):
    from dataclasses import replace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "declarative.db")
    try:
        _, context = runtime.orient("session:no-question", "Alice likes Bob.")
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
        # Isolate the preserved query-selector assertion from the newly
        # reviewed declarative construction, which correctly needs no query.
        pack["application_role_orders"]["relation_subject_predicate_object"].pop("evidence_order")
        isolated = ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority,
            replace(RuntimeConfig.release(), max_beam_states=1))
        designations = tuple(_slot_with(row, designation_fact_ref=f"designation:declarative-{i}")
                             for row in context.designation_slots for i in range(8))
        assert isolated.matches(designations, context.contribution_slots, context.source_unit_spans) == ()
        runtime._owners["orientation"]._context_builder.role_schema_index = isolated
        result = runtime.process("session:no-question-public", "Alice likes Bob.")
        assert result.verification.selected_meaning is not None
        app = SemanticApplication("application:independent-declarative", "op:relation", "rel:likes", (
            RoleBinding("role:subject", GroundedReference("entity:alice")),
            RoleBinding("role:object", GroundedReference("entity:bob")),
        ))
        assert result.verification.selected_meaning.expression == SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
    finally:
        runtime.stores.close()


def test_relation_query_pack_preserves_all_predecessor_fields():
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.forms import FormResolver
    pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
    orders = pack["application_role_orders"]
    assert len(orders) == 16
    assert orders.pop("communicative_actor_event_addressee") == {
        "construction": "communicative_event",
        "evidence_order": [
            {"kind": "referent", "role": "role:actor", "target_kinds": ["entity", "participant"], "cardinality": "optional"},
            {"kind": "designation", "role": "role:event", "target_kind": "event_type"},
            {"kind": "referent", "role": "role:addressee", "target_kinds": ["entity", "participant"], "cardinality": "optional"},
        ],
    }
    assert orders["relation_subject_predicate_object"].pop("evidence_order") == [
        {"kind": "referent", "target_kinds": ["entity", "participant"], "role": "role:subject"},
        {"kind": "designation", "target_kind": "relation_type", "role": "role:relation"},
        {"kind": "referent", "target_kinds": ["entity", "participant"], "role": "role:object"},
    ]
    from tests.test_foundation_projection_construction import _pack
    assert orders.pop("content_target_projection") == _pack()["application_role_orders"]["content_target_projection"]
    for word in ("a", "an", "the"):
        assert pack["determiners"][word].pop("construction_role") == "query_target_article"
    assert orders["relation_subject_predicate_query_object"].pop("evidence_order") == [
        {"kind": "designation", "target_kind": "entity", "role": "role:subject"},
        {"kind": "designation", "target_kind": "relation_type", "role": "role:relation"},
        {"kind": "feature", "features": [["query", "query"], ["interrogative", "person"]], "role": "role:object"},
    ]
    assert orders["relation_predicate_subject_query_object"].pop("evidence_order") == [
        {"kind": "feature", "features": [["query", "query"], ["interrogative", "person"]], "role": "role:subject"},
        {"kind": "designation", "target_kind": "relation_type", "role": "role:relation"},
        {"kind": "designation", "target_kind": "entity", "role": "role:object"},
    ]
    assert orders["relation_predicate_subject_query_object"]["roles"] == ["role:relation", "role:object"]
    orders["relation_predicate_subject_query_object"]["roles"] = ["role:relation", "role:subject"]
    # Retain the frozen predecessor assertion, reversing only declared earlier
    # metadata/define changes plus the two reviewed mixed role rows above.
    assert "define" not in pack["query_projection"] and pack["abi_version"] == 7
    assert pack.pop("orthography") == {
        "'": {"kind": "quotation_boundary"}, "\"": {"kind": "quotation_boundary"},
        "\u201c": {"kind": "quotation_boundary"}, "\u201d": {"kind": "quotation_boundary"},
        "\u2018": {"kind": "quotation_boundary"}, "\u2019": {"kind": "quotation_boundary"},
        "\u00ab": {"kind": "quotation_boundary"}, "\u00bb": {"kind": "quotation_boundary"},
        "\u2039": {"kind": "quotation_boundary"}, "\u203a": {"kind": "quotation_boundary"},
        ".": {"kind": "sentence_boundary"}, "!": {"kind": "sentence_boundary"},
        "?": {"kind": "sentence_boundary"}, ";": {"kind": "sentence_boundary"},
    }
    for delimiter in ("\u201c", "\u201d", "\u2018", "\u2019", "\u00ab", "\u00bb", "\u2039", "\u203a"):
        assert pack["tokenization"]["punctuation"].count(delimiter) == 1
        pack["tokenization"]["punctuation"].remove(delimiter)
    for word, kind in (("what", "content"), ("who", "person"), ("where", "location"), ("when", "time"), ("why", "reason"), ("which", "selection"), ("how", "manner")):
        assert pack["query_projection"][word].pop("interrogative") == kind
        assert pack["query_projection"][word] == {"kind": "query"}
    assert pack["query_projection"]["does"].pop("construction_role") == "lexical_query_auxiliary"
    assert pack["discourse"]["mean"].pop("construction_role") == "lexical_query_terminal"
    assert pack["linkers"].pop("in") == {"kind": "restriction_linker"}
    pack["query_projection"]["define"] = {"kind": "query"}
    assert FormResolver(pack, RuntimeConfig.release()).form_pack_hash == "sha256:32f5133c901afc05cc5345bc5766d00c97518b54025cad4ca0fb3707ad40b5ad"


def test_spanish_relation_pack_preserves_all_undeclared_predecessor_fields():
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.forms import FormResolver
    pack = json.loads((ROOT / "data/languages/es/forms.json").read_text(encoding="utf-8"))
    assert len(pack["application_role_orders"]) == 16
    assert pack["application_role_orders"].pop("communicative_actor_event_addressee") == {
        "construction": "communicative_event",
        "evidence_order": [
            {"kind": "referent", "role": "role:actor", "target_kinds": ["entity", "participant"], "cardinality": "optional"},
            {"kind": "designation", "role": "role:event", "target_kind": "event_type"},
            {"kind": "referent", "role": "role:addressee", "target_kinds": ["entity", "participant"], "cardinality": "optional"},
        ],
    }
    assert pack.pop("orthography") == {
        "'": {"kind": "quotation_boundary"}, "\"": {"kind": "quotation_boundary"},
        "\u201c": {"kind": "quotation_boundary"}, "\u201d": {"kind": "quotation_boundary"},
        "\u2018": {"kind": "quotation_boundary"}, "\u2019": {"kind": "quotation_boundary"},
        "\u00ab": {"kind": "quotation_boundary"}, "\u00bb": {"kind": "quotation_boundary"},
        "\u2039": {"kind": "quotation_boundary"}, "\u203a": {"kind": "quotation_boundary"},
        ".": {"kind": "sentence_boundary"}, "!": {"kind": "sentence_boundary"},
        "?": {"kind": "sentence_boundary"}, ";": {"kind": "sentence_boundary"},
    }
    for delimiter in ("\u201c", "\u201d", "\u2018", "\u2019", "\u00ab", "\u00bb", "\u2039", "\u203a"):
        assert pack["tokenization"]["punctuation"].count(delimiter) == 1
        pack["tokenization"]["punctuation"].remove(delimiter)
    from tests.test_foundation_projection_construction import _pack
    assert pack["application_role_orders"].pop("content_target_projection") == _pack("es")["application_role_orders"]["content_target_projection"]
    for word in ("el", "la", "un", "una"):
        assert pack["determiners"][word].pop("construction_role") == "query_target_article"
    assert pack["query_projection"]["qué"].pop("interrogative") == "content"
    assert pack["query_projection"]["qui\u00e9n"].pop("interrogative") == "person"
    orders = pack["application_role_orders"]
    assert orders["relation_subject_predicate_object"].pop("evidence_order") == [
        {"kind": "referent", "target_kinds": ["entity", "participant"], "role": "role:subject"},
        {"kind": "designation", "target_kind": "relation_type", "role": "role:relation"},
        {"kind": "referent", "target_kinds": ["entity", "participant"], "role": "role:object"},
    ]
    assert orders["relation_subject_predicate_query_object"].pop("evidence_order") == [
        {"kind": "designation", "target_kind": "entity", "role": "role:subject"},
        {"kind": "designation", "target_kind": "relation_type", "role": "role:relation"},
        {"kind": "feature", "features": [["query", "query"], ["interrogative", "person"]], "role": "role:object"},
    ]
    assert orders["relation_predicate_subject_query_object"].pop("evidence_order") == [
        {"kind": "feature", "features": [["query", "query"], ["interrogative", "person"]], "role": "role:subject"},
        {"kind": "designation", "target_kind": "relation_type", "role": "role:relation"},
        {"kind": "designation", "target_kind": "entity", "role": "role:object"},
    ]
    assert orders["relation_predicate_subject_query_object"]["roles"] == ["role:relation", "role:object"]
    orders["relation_predicate_subject_query_object"]["roles"] = ["role:relation", "role:subject"]
    assert FormResolver(pack, RuntimeConfig.release()).form_pack_hash == "sha256:198102ddd7e69eb33a24b4e7a8e103c5627eefd405f6a64b61e8db38583bcd61"


@pytest.mark.parametrize("language,leading", (("en", True), ("en", False), ("es", True), ("es", False)),
    ids=("en-leading", "en-trailing", "es-leading", "es-trailing"))
def test_polysemous_referent_preserves_both_role_graphs_until_exact_settling(language, leading, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "alternatives.db")
    try:
        pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
        question = "who" if language == "en" else "qui\u00e9n"
        source = f"{question} velnora Bob?" if leading else f"Bob velnora {question}?"
        facts = tuple(DesignationFact.create(surface=surface, target_ref=target, language=language)
            for surface, target in (("velnora", "rel:likes"), ("Bob", "entity:bob"), ("Bob", "entity:alice")))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, source, facts=facts)
        matches = builder.role_schema_index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
        assert len(matches) == 2
        variables = tuple(v for v in context.variable_slots if context.frame(v.application_frame_ref).operator_ref == "op:relation")
        assert {v.construction_ref for v in variables} == {m.match_ref for m in matches}
        assert {v.role_ref for v in variables} == {"role:subject" if leading else "role:object"}
        proposal = runtime.proposal_model.propose(context)
        assert proposal.candidates and not proposal.truncated
        assert len(proposal.candidates) <= runtime._config.max_complete_candidates
        verified = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
        expected = {_expected("role:subject" if leading else "role:object", target) for target in ("entity:alice", "entity:bob")}
        accepted = tuple(receipt for receipt in verified.candidate_receipts if receipt.accepted)
        assert {receipt.expression for receipt in accepted} == expected
        assert verified.status == "ambiguous" and verified.selected_meaning is None
        assert set(verified.ambiguity_expression_refs) == {e.expression_ref for e in expected}
        for receipt in accepted:
            program = next(c.program for c in proposal.candidates if c.program.program_ref == receipt.program_ref)
            projection = next(a for a in program.actions if a.action_type == "project_variable")
            match = next(m for m in matches if m.match_ref == context.variable(projection.arguments[1]).construction_ref)
            referent = context.designation(match.referent_slot_ref)
            binding = next(a for a in program.actions if a.action_type == "bind_reference")
            assert binding.arguments[1] == match.referent_role
            assert context.reference(binding.arguments[2]).target_ref == referent.target_ref
            assert not _replay_program(program, context, role_schema_index=builder.role_schema_index)
            variable = context.variable(projection.arguments[1])
            other = next(m for m in matches if m.match_ref != match.match_ref)
            other_variable = next(v for v in variables if v.construction_ref == other.match_ref)
            predicate = next(c for c in context.contribution_slots if c.kind == "predicate"
                             and c.source_unit_refs == context.frame(variable.application_frame_ref).source_unit_refs)
            for replacements in (
                {variable.slot_ref: _slot_with(variable, construction_ref=other.match_ref),
                 other_variable.slot_ref: _slot_with(other_variable, construction_ref=match.match_ref)},
                {predicate.slot_ref: _slot_with(predicate, constraints=tuple(
                    (key, "match-set:forged") if key == "role_schema_match_set" else (key, value)
                    for key, value in predicate.constraints))},
            ):
                forged_context, forged_program = _rehash_derivation(context, program, replacements)
                assert isinstance(SemanticExpressionCompiler(role_schema_index=builder.role_schema_index).compile(
                    forged_program, forged_context), CompilationFailure)
                assert not CoverageVerifier(role_schema_index=builder.role_schema_index).verify(forged_context, forged_program).executable
                assert reconstruct_expected_expression(forged_program, forged_context, role_schema_index=builder.role_schema_index) is None
                assert _replay_program(forged_program, forged_context, role_schema_index=builder.role_schema_index)
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,predicate_alias,referent_alias", (
    ("en", "can likes", "Bob"), ("en", "not likes", "Bob"),
    ("en", "likes and", "Bob"), ("en", "likes,", "Bob"),
    ("en", "care about", "Bob"), ("en", "velnora", "not Bob"),
    ("es", "puede likes", "Bob"), ("es", "no likes", "Bob"),
    ("es", "likes y", "Bob"), ("es", "likes,", "Bob"),
    ("es", "velnora sobre", "Bob"), ("es", "velnora", "no Bob"),
), ids=("en-modal", "en-negative", "en-connector", "en-punctuation", "en-linker", "en-referent-negative",
         "es-modal", "es-negative", "es-connector", "es-punctuation", "es-linker", "es-referent-negative"))
def test_relation_designation_cannot_swallow_closed_primitive_evidence(language, predicate_alias, referent_alias, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "overlap.db")
    try:
        pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
        question = "who" if language == "en" else "qui\u00e9n"
        facts = tuple(DesignationFact.create(surface=surface, target_ref=target, language=language)
            for surface, target in ((predicate_alias, "rel:likes"), (referent_alias, "entity:bob")))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack,
            f"{question} {predicate_alias} {referent_alias}?", facts=facts)
        assert any(c.target_ref is None and c.constraints and c.constraints[0][0] != "orthography"
                   and c.kind != "open_variable" for c in context.contribution_slots)
        assert not builder.role_schema_index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
        assert not any(context.frame(v.application_frame_ref).operator_ref == "op:relation" for v in context.variable_slots)
        verified = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(
            runtime.proposal_model.propose(context), context)
        assert verified.selected_meaning is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,alias", (
    ("en", "can likes"), ("en", "not likes"), ("en", "likes and"), ("en", "likes,"), ("en", "care about"),
    ("en", "you likes"), ("en", "I likes"), ("en", "my likes"), ("en", "likes you"),
    ("es", "yo velnora"), ("es", "velnora yo"), ("es", "mi velnora"), ("es", "t\u00fa velnora"),
    ("en", "they likes"), ("en", "this likes"), ("en", "we likes"),
    ("es", "ellos velnora"), ("es", "esto velnora"), ("es", "nosotros velnora"),
), ids=("modal", "negative", "connector", "punctuation", "linker", "en-addressee", "en-speaker", "en-possessive", "en-trailing-deixis",
         "es-speaker", "es-trailing-deixis", "es-possessive", "es-addressee",
         "en-other-unresolved", "en-proximal-unresolved", "en-group-unresolved", "es-other-unresolved", "es-proximal-unresolved", "es-group-unresolved"))
def test_self_rehashed_overlap_witness_cannot_erase_primitives_at_exact_sinks(language, alias, tmp_path):
    from cemm_authoritative_hybrid.canonical import stable_ref
    from cemm_authoritative_hybrid.proposal_context import VariableSlot
    from cemm_authoritative_hybrid.role_schemas import RoleSchemaMatch, SelectedRoleEvidence
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "overlap-forgery.db")
    try:
        pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
        question = "who" if language == "en" else "qui\u00e9n"
        facts = (DesignationFact.create(surface=alias, target_ref="rel:likes", language=language),
                 DesignationFact.create(surface="Bob", target_ref="entity:bob", language=language))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack,
            f"{question} {alias} Bob?", facts=facts)
        index = builder.role_schema_index
        predicate = next(d for d in context.designation_slots if d.target_kind == "relation_type")
        referent = next(d for d in context.designation_slots if d.target_kind == "entity")
        query = next(c for c in context.contribution_slots if c.kind == "open_variable")
        schema = next(s for s in index.schemas if s.selectors[0].kind == "feature")
        bindings = (SelectedRoleEvidence("role:subject", None, None, query.source_unit_refs),
            SelectedRoleEvidence("role:relation", predicate.target_kind, predicate.slot_ref, predicate.source_unit_refs),
            SelectedRoleEvidence("role:object", referent.target_kind, referent.slot_ref, referent.source_unit_refs))
        match = RoleSchemaMatch(index.index_ref, schema.schema_ref, stable_ref("reviewed_role_match", {
            "index": index.index_ref, "schema": schema.schema_ref,
            "bindings": [(b.role, b.target_kind, b.designation_slot_ref, b.source_unit_refs) for b in bindings],
        }), bindings)
        old_frame = next(f for f in context.application_frames if f.operator_ref == "op:relation")
        old_predicate = next(c for c in context.contribution_slots if c.kind == "predicate" and c.target_ref == "rel:likes")
        witness_keys = {key for key, _ in match.witness}
        old_witness_refs = {value for key, value in old_predicate.constraints if key in {"role_schema_index", "role_schema", "role_schema_match"}}
        frame = _slot_with(old_frame, provenance_refs=tuple(ref for ref in old_frame.provenance_refs if ref not in old_witness_refs) + match.provenance)
        contribution = _slot_with(old_predicate, constraints=tuple(pair for pair in old_predicate.constraints if pair[0] not in witness_keys) + match.witness,
            provenance_refs=tuple(ref for ref in old_predicate.provenance_refs if ref not in old_witness_refs) + match.provenance)
        values = {name: getattr(context, name) for name in inspect.signature(ProposalContext.create).parameters if name != "config"}
        values["application_frames"] = tuple(frame if f == old_frame else f for f in context.application_frames)
        values["contribution_slots"] = tuple(contribution if c == old_predicate else c for c in context.contribution_slots)
        values["reference_slots"] = tuple(_slot_with(r, provenance_refs=tuple(frame.slot_ref if ref == old_frame.slot_ref else ref for ref in r.provenance_refs)) for r in context.reference_slots)
        values["variable_slots"] = (VariableSlot.create(application_frame_ref=frame.slot_ref, role_ref="role:subject",
            required_kinds=("entity", "participant", "concept"), source_unit_refs=query.source_unit_refs, construction_ref=match.match_ref),)
        forged = ProposalContext.create(**values)
        proposal = runtime.proposal_model.propose(forged)
        assert proposal.candidates and not proposal.truncated
        program = next(c.program for c in proposal.candidates if not any(a.action_type == "attach_scope" for a in c.program.actions))
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        assert isinstance(compiled, CompilationFailure) and compiled.code.startswith("relation_query_")
        assert not CoverageVerifier(role_schema_index=index).verify(forged, program).executable
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert _replay_program(program, forged, role_schema_index=index)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,predicate_alias,referent_alias", (
    ("en", "you likes", "Bob"), ("en", "I likes", "Bob"), ("en", "my likes", "Bob"), ("en", "likes you", "Bob"),
    ("es", "yo velnora", "Bob"), ("es", "velnora yo", "Bob"), ("es", "mi velnora", "Bob"), ("es", "t\u00fa velnora", "Bob"),
    ("en", "velnora", "you Bob"), ("es", "velnora", "mi Bob"),
), ids=("en-addressee", "en-speaker", "en-possessive", "en-trailing-deixis", "es-speaker", "es-trailing-deixis", "es-possessive", "es-addressee",
         "en-referent-deixis", "es-referent-deixis"))
def test_relation_designation_cannot_swallow_target_bearing_primitive_reference(language, predicate_alias, referent_alias, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "deixis-overlap.db")
    try:
        pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
        question = "who" if language == "en" else "qui\u00e9n"
        facts = tuple(DesignationFact.create(surface=surface, target_ref=target, language=language)
            for surface, target in ((predicate_alias, "rel:likes"), (referent_alias, "entity:bob")))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack,
            f"{question} {predicate_alias} {referent_alias}?", facts=facts)
        references = tuple(c for c in context.contribution_slots if c.kind == "reference" and c.constraints
                           and c.constraints[0][0] == "participant")
        assert references and all(c.target_ref in {"participant:user", "participant:system"} for c in references)
        assert all(c.provenance_refs == c.source_unit_refs for c in references)
        assert not builder.role_schema_index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
        assert not any(context.frame(v.application_frame_ref).operator_ref == "op:relation" for v in context.variable_slots)
        verified = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(
            runtime.proposal_model.propose(context), context)
        assert verified.selected_meaning is None and runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,alias,feature", (
    ("en", "they likes", "reference_other"), ("en", "this likes", "proximal"), ("en", "we likes", "reference_group"),
    ("es", "ellos velnora", "reference_other"), ("es", "esto velnora", "proximal"), ("es", "nosotros velnora", "reference_group"),
), ids=("en-other", "en-proximal", "en-group", "es-other", "es-proximal", "es-group"))
def test_unresolved_primitive_reference_retains_owned_requirement_and_blocks_relation_alias(language, alias, feature, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "unresolved-deixis.db")
    try:
        pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
        question = "who" if language == "en" else "qui\u00e9n"
        facts = (DesignationFact.create(surface=alias, target_ref="rel:likes", language=language),
                 DesignationFact.create(surface="Bob", target_ref="entity:bob", language=language))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack,
            f"{question} {alias} Bob?", facts=facts)
        unresolved = tuple(c for c in context.contribution_slots if c.kind == "reference"
                           and c.constraints == (("participant", feature),))
        assert len(unresolved) == 1 and unresolved[0].target_ref is None and unresolved[0].target_kind is None
        assert unresolved[0].provenance_refs == unresolved[0].source_unit_refs
        assert not builder.role_schema_index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
        verified = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(
            runtime.proposal_model.propose(context), context)
        assert verified.selected_meaning is None and runtime.stores.world.revision == 0
        # Unresolved reference criticality is retained outside a designation too.
        _, ordinary = _static_composition_context(runtime.authority, runtime.stores, pack, alias.split()[0], facts=())
        reference_residual = ordinary.residual_for_source("unit:0")
        assert reference_residual is not None and reference_residual.critical
        assert reference_residual.contribution_kind == "reference"
        assert not ordinary.contributions_for_source("unit:0")
        actions = (
            ProgramAction.create(action_index=0, action_type="select_context", arguments=(ordinary.context_ref,), source_unit_refs=()),
            ProgramAction.create(action_index=1, action_type="select_mode", arguments=(ordinary.mode_slots[0].slot_ref,), source_unit_refs=()),
            ProgramAction.create(action_index=2, action_type="abstain", arguments=(), source_unit_refs=()),
        )
        assignment = SourceAssignment.create(source_unit_ref="unit:0", contribution_slot_ref=reference_residual.residual_ref,
            assignment_kind="residual", target_action_ref=None, target_role_ref=None, residual_kind="reference", critical=False)
        program = SemanticSwitchProgram.create(orientation_ref=ordinary.orientation_ref, proposal_context_ref=ordinary.context_ref,
            actions=actions, root_refs=(), mode_slot_ref=ordinary.mode_slots[0].slot_ref, goal_refs=(), source_unit_refs=ordinary.source_unit_refs,
            source_assignments=(assignment,), revision_pin=ordinary.revision_pin)
        coverage = CoverageVerifier(role_schema_index=builder.role_schema_index).verify(ordinary, program)
        assert not coverage.executable and any(e.code == "false_residual_criticality" for e in coverage.errors)
        assert [(r.source_unit_ref, r.contribution_kind) for r in coverage.critical_residuals] == [("unit:0", "reference")]
        if language == "en":
            before = runtime.stores.revision_pin()
            result = runtime.process("session:unresolved-reference", f"{alias} Bob.")
            assert result.verification.selected_meaning is None and runtime.stores.world.revision == 0
            assert result.final_revision_pin == before == runtime.stores.revision_pin()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,pronoun,target", (
    ("en", "I", "participant:user"), ("en", "you", "participant:system"),
    ("es", "yo", "participant:user"), ("es", "t\u00fa", "participant:system"),
), ids=("en-speaker", "en-addressee", "es-speaker", "es-addressee"))
def test_ordinary_separate_participant_reference_keeps_its_exact_role(language, pronoun, target, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "ordinary-participant.db")
    try:
        pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
        facts = (DesignationFact.create(surface="velnora", target_ref="rel:likes", language=language),
                 DesignationFact.create(surface="Bob", target_ref="entity:bob", language=language))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, f"{pronoun} velnora Bob.", facts=facts)
        verified = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(
            runtime.proposal_model.propose(context), context)
        app = SemanticApplication("application:independent-participant", "op:relation", "rel:likes", (
            RoleBinding("role:subject", GroundedReference(target)), RoleBinding("role:object", GroundedReference("entity:bob")),
        ))
        assert verified.selected_meaning is not None
        assert verified.selected_meaning.expression == SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("identity", ("missing", "stale-generation", "different-pack", "different-content", "changed-attempt-bound"),
    ids=("missing", "stale-generation", "different-pack", "different-content", "changed-attempt-bound"))
def test_relation_query_requires_current_pinned_index_at_every_exact_sink(identity, tmp_path):
    from dataclasses import replace
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "pinned.db")
    try:
        _, context = runtime.orient("session:pinned", "Who likes Bob?")
        program = runtime.proposal_model.propose(context).candidates[0].program
        index = runtime._owners["verification"].role_schema_index
        if identity == "missing":
            index = None
        elif identity == "stale-generation":
            index = replace(index, authority_generation="authority:stale")
        elif identity == "different-content":
            index = replace(index, authority_content_hash="authority-content:stale")
        elif identity == "changed-attempt-bound":
            index = replace(index, attempt_limit=1000000)
        else:
            pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
            pack["language"] = "different-pack"
            index = ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, runtime._owners["orientation"]._config)
        assert not CoverageVerifier(role_schema_index=index).verify(context, program).executable
        assert isinstance(SemanticExpressionCompiler(role_schema_index=index).compile(program, context), CompilationFailure)
        assert reconstruct_expected_expression(program, context, role_schema_index=index) is None
        assert _replay_program(program, context, role_schema_index=index)
    finally:
        runtime.stores.close()
