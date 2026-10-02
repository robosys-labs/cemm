"""Private description/proof linkage; codecs do not authorize publication."""
from __future__ import annotations

import pytest
from types import SimpleNamespace

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.descriptions import DescriptionCompleteness, DescriptionRequest, DescriptionResult
from cemm_authoritative_hybrid.expressions import ApplicationFiller, GroundedReference, RoleBinding, SemanticApplication, SemanticExpression
from cemm_authoritative_hybrid.persistence import Fact, StaleRevisionError, open_stores
from cemm_authoritative_hybrid.proof_bundle import ClaimEvidence, ProofBundle
from tests.test_foundation_description_request_lineage import _query_expression, _situation
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from tests.test_foundation_description_builder import (
    _description_expression, _physically_replace_fact, _seed_reviewed_generic_claim,
    _seeded_description_case, _stores,
)


__cemm_test_inventory__ = {'tests/test_foundation_description_proof.py::test_description_proof_retains_exact_signed_claim[memory]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-proof-retains-exact-signed-claim-memory',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': '615506a558e9888a495a12c634261c78e506fbb59f23f53f7ff99a33ea593266'},
 'tests/test_foundation_description_proof.py::test_description_proof_retains_exact_signed_claim[sqlite]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-proof-retains-exact-signed-claim-sqlite',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': '615506a558e9888a495a12c634261c78e506fbb59f23f53f7ff99a33ea593266'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_signs_without_graph_truth[denial-memory]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-preserves-signs-without-graph-truth-denial-memory',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '8f607ac5bafedb17c6bf4a1403dcbf691e19772c4247a1ceeb812af7176f70ff'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_signs_without_graph_truth[denial-sqlite]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-preserves-signs-without-graph-truth-denial-sqlite',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '8f607ac5bafedb17c6bf4a1403dcbf691e19772c4247a1ceeb812af7176f70ff'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_signs_without_graph_truth[conflict-memory]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:foundation-proof-preserves-signs-without-graph-truth-conflict-memory',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                             'source_ast_sha256': '8f607ac5bafedb17c6bf4a1403dcbf691e19772c4247a1ceeb812af7176f70ff'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_signs_without_graph_truth[conflict-sqlite]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:foundation-proof-preserves-signs-without-graph-truth-conflict-sqlite',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                             'source_ast_sha256': '8f607ac5bafedb17c6bf4a1403dcbf691e19772c4247a1ceeb812af7176f70ff'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_signs_without_graph_truth[shared-memory]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-preserves-signs-without-graph-truth-shared-memory',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '8f607ac5bafedb17c6bf4a1403dcbf691e19772c4247a1ceeb812af7176f70ff'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_signs_without_graph_truth[shared-sqlite]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-preserves-signs-without-graph-truth-shared-sqlite',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '8f607ac5bafedb17c6bf4a1403dcbf691e19772c4247a1ceeb812af7176f70ff'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[missing-memory]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-missing-memory',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[missing-sqlite]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-missing-sqlite',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[facts-memory]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-facts-memory',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[facts-sqlite]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-facts-sqlite',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[proofs-memory]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-proofs-memory',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[proofs-sqlite]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-proofs-sqlite',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[depth-memory]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-depth-memory',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_terminals_never_truncate_evidence[depth-sqlite]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-proof-terminals-never-truncate-evidence-depth-sqlite',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '77199b56b899347f36ecc6abe1dbda24aa495c33c746c690005f84ecbd2a09a9'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[claim]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-claim',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[application]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-application',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[source]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-source',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[bundle]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-bundle',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[extra]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-extra',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[tuple]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-tuple',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[abi-bool]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-abi-bool',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_codec_rejects_tamper_and_noncanonical_types[claim-bool]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-proof-codec-rejects-tamper-and-noncanonical-types-claim-bool',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': 'ec14d684c1c15966fa5e344358f412a4d15577e994872d9ad3b63300f425935c'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_rehashed_inconsistent_evidence[aggregate]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-proof-rejects-rehashed-inconsistent-evidence-aggregate',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'a461eed43bacea5065dae07d1f496fdaad0d47ef710856b78ad95b7c40ed934c'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_rehashed_inconsistent_evidence[sign]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-proof-rejects-rehashed-inconsistent-evidence-sign',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'a461eed43bacea5065dae07d1f496fdaad0d47ef710856b78ad95b7c40ed934c'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_rehashed_inconsistent_evidence[pin]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-proof-rejects-rehashed-inconsistent-evidence-pin',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': 'a461eed43bacea5065dae07d1f496fdaad0d47ef710856b78ad95b7c40ed934c'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_rehashed_inconsistent_evidence[roots]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-proof-rejects-rehashed-inconsistent-evidence-roots',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'a461eed43bacea5065dae07d1f496fdaad0d47ef710856b78ad95b7c40ed934c'},
 'tests/test_foundation_description_proof.py::test_description_proof_builder_rejects_changed_store_lineage[projection-memory]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:foundation-proof-builder-rejects-changed-store-lineage-projection-memory',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': 'cb25cac059c05cac72640f18c3287ced32a4a8cd2cad2d2a23caad7c6ec72a9b'},
 'tests/test_foundation_description_proof.py::test_description_proof_builder_rejects_changed_store_lineage[projection-sqlite]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:foundation-proof-builder-rejects-changed-store-lineage-projection-sqlite',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': 'cb25cac059c05cac72640f18c3287ced32a4a8cd2cad2d2a23caad7c6ec72a9b'},
 'tests/test_foundation_description_proof.py::test_description_proof_builder_rejects_changed_store_lineage[lineage-memory]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-proof-builder-rejects-changed-store-lineage-lineage-memory',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': 'cb25cac059c05cac72640f18c3287ced32a4a8cd2cad2d2a23caad7c6ec72a9b'},
 'tests/test_foundation_description_proof.py::test_description_proof_builder_rejects_changed_store_lineage[lineage-sqlite]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-proof-builder-rejects-changed-store-lineage-lineage-sqlite',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': 'cb25cac059c05cac72640f18c3287ced32a4a8cd2cad2d2a23caad7c6ec72a9b'},
 'tests/test_foundation_description_proof.py::test_description_proof_builder_rejects_changed_store_lineage[transaction-memory]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-proof-builder-rejects-changed-store-lineage-transaction-memory',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': 'cb25cac059c05cac72640f18c3287ced32a4a8cd2cad2d2a23caad7c6ec72a9b'},
 'tests/test_foundation_description_proof.py::test_description_proof_builder_rejects_changed_store_lineage[transaction-sqlite]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-proof-builder-rejects-changed-store-lineage-transaction-sqlite',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': 'cb25cac059c05cac72640f18c3287ced32a4a8cd2cad2d2a23caad7c6ec72a9b'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_stale_request_and_live_authority[world-memory]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-stale-request-and-live-authority-world-memory',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '959bf0a23085abc19e838cbd7e0ae4a638d0ba1a783e7d3075951f1ec9c4e56a'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_stale_request_and_live_authority[world-sqlite]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-stale-request-and-live-authority-world-sqlite',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '959bf0a23085abc19e838cbd7e0ae4a638d0ba1a783e7d3075951f1ec9c4e56a'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_stale_request_and_live_authority[authority-memory]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-proof-rejects-stale-request-and-live-authority-authority-memory',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '959bf0a23085abc19e838cbd7e0ae4a638d0ba1a783e7d3075951f1ec9c4e56a'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_stale_request_and_live_authority[authority-sqlite]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:foundation-proof-rejects-stale-request-and-live-authority-authority-sqlite',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                                   'source_ast_sha256': '959bf0a23085abc19e838cbd7e0ae4a638d0ba1a783e7d3075951f1ec9c4e56a'},
 'tests/test_foundation_description_proof.py::test_description_proof_rechecks_authority_before_return[memory]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-proof-rechecks-authority-before-return-memory',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '80c6cfec53494de175f9c482c1202276d5fa11c78c523ceb4e72c1730c540afa'},
 'tests/test_foundation_description_proof.py::test_description_proof_rechecks_authority_before_return[sqlite]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-proof-rechecks-authority-before-return-sqlite',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '80c6cfec53494de175f9c482c1202276d5fa11c78c523ceb4e72c1730c540afa'},
 'tests/test_foundation_description_proof.py::test_description_proof_sqlite_restart_retains_exact_bundle': {'activation_phase': 'R4',
                                                                                                            'assertion_ref': 'assertion:foundation-proof-sqlite-restart-retains-exact-bundle',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                            'source_ast_sha256': '2f416681961c4f34f77b0a599257e4b4efd85ae523d03f86fcaa3696e54361d9'},
 'tests/test_foundation_description_proof.py::test_description_proof_memory_sqlite_parity': {'activation_phase': 'R4',
                                                                                             'assertion_ref': 'assertion:foundation-proof-memory-sqlite-parity',
                                                                                             'diagnostic_role': 'owner',
                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                             'owner_ref': 'decision-query-proof',
                                                                                             'source_ast_sha256': '3b23b0d64af8f1f3d875aa7b6f5971768f7c5e72bb6507f2d696bfb8201d1b77'},
 'tests/test_foundation_description_proof.py::test_description_proof_uses_one_snapshot_and_one_target_read[memory]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-proof-uses-one-snapshot-and-one-target-read-memory',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'fd81ea48c0a3672029fb5f34f5d25aec197827ee32fd9bdaaac1544ca476dd5c'},
 'tests/test_foundation_description_proof.py::test_description_proof_uses_one_snapshot_and_one_target_read[sqlite]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-proof-uses-one-snapshot-and-one-target-read-sqlite',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'fd81ea48c0a3672029fb5f34f5d25aec197827ee32fd9bdaaac1544ca476dd5c'},
 'tests/test_foundation_description_proof.py::test_description_proof_indexed_work_is_independent_of_unrelated_claims': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-proof-indexed-work-is-independent-of-unrelated-claims',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '5a9376d6ef67eb6207d4142f8955725f5943acbe88e09701f0237b2761878c29'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_unbounded_or_mispinned_claims[claim-count]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-rejects-unbounded-or-mispinned-claims-claim-count',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '46023f89334b43048b2d49df101aef95e8168ada23503452b2598a18876f3379'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_unbounded_or_mispinned_claims[future-revision]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-unbounded-or-mispinned-claims-future-revision',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '46023f89334b43048b2d49df101aef95e8168ada23503452b2598a18876f3379'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_unbounded_or_mispinned_claims[proof-count]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-rejects-unbounded-or-mispinned-claims-proof-count',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '46023f89334b43048b2d49df101aef95e8168ada23503452b2598a18876f3379'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_unbounded_or_mispinned_claims[wrong-placement]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-unbounded-or-mispinned-claims-wrong-placement',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '46023f89334b43048b2d49df101aef95e8168ada23503452b2598a18876f3379'},
 'tests/test_foundation_description_proof.py::test_description_proof_decoder_rejects_ref_string_subclasses': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-proof-decoder-rejects-ref-string-subclasses',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                              'source_ast_sha256': '4458172ee372c5e3098de9b7dfcb58e273cb92c6d7260839171afbcc6b8ff298'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_bounded_claim_proof_sequence[duplicates-memory]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-proof-preserves-bounded-claim-proof-sequence-duplicates-memory',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '7805724bf4e5c442647f49acf9a597702e2165b9ed547f12d732519f4e847b09'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_bounded_claim_proof_sequence[duplicates-sqlite]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-proof-preserves-bounded-claim-proof-sequence-duplicates-sqlite',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '7805724bf4e5c442647f49acf9a597702e2165b9ed547f12d732519f4e847b09'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_bounded_claim_proof_sequence[overflow-memory]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-proof-preserves-bounded-claim-proof-sequence-overflow-memory',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': '7805724bf4e5c442647f49acf9a597702e2165b9ed547f12d732519f4e847b09'},
 'tests/test_foundation_description_proof.py::test_description_proof_preserves_bounded_claim_proof_sequence[overflow-sqlite]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-proof-preserves-bounded-claim-proof-sequence-overflow-sqlite',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': '7805724bf4e5c442647f49acf9a597702e2165b9ed547f12d732519f4e847b09'},
 'tests/test_foundation_description_proof.py::test_description_proof_retains_nested_persistent_application_correspondence[memory]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-proof-retains-nested-persistent-application-correspondence-memory',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': 'f035514df70d07a28e140f20084316fd254cb3d8a79d34c775a0bc8ee16f731e'},
 'tests/test_foundation_description_proof.py::test_description_proof_retains_nested_persistent_application_correspondence[sqlite]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-proof-retains-nested-persistent-application-correspondence-sqlite',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': 'f035514df70d07a28e140f20084316fd254cb3d8a79d34c775a0bc8ee16f731e'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_normalized_identity_tamper[claim-memory]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-proof-rejects-normalized-identity-tamper-claim-memory',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': 'e421b9c1f8b616d87ecb07ab7e803b176e9a7fdf762cdeff9b512d2877503b20'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_normalized_identity_tamper[claim-sqlite]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-proof-rejects-normalized-identity-tamper-claim-sqlite',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': 'e421b9c1f8b616d87ecb07ab7e803b176e9a7fdf762cdeff9b512d2877503b20'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_normalized_identity_tamper[application-memory]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-normalized-identity-tamper-application-memory',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'e421b9c1f8b616d87ecb07ab7e803b176e9a7fdf762cdeff9b512d2877503b20'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_normalized_identity_tamper[application-sqlite]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-normalized-identity-tamper-application-sqlite',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'e421b9c1f8b616d87ecb07ab7e803b176e9a7fdf762cdeff9b512d2877503b20'},
 'tests/test_foundation_description_proof.py::test_description_proof_structural_codec_does_not_authenticate_publication': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-structural-codec-does-not-authenticate-publication',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': '91dfa7dd8a7a580f0d3ba06e4f4d0d937b504b8be1f0b2a4316a25f3d0847ac9'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_same_generation_authority_drift[before-content]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-proof-rejects-same-generation-authority-drift-before-content',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': '310e68cf4f174d4ea0a2f7e7466df883cdb30675f5d6c04d4f670e816f8cfa01'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_same_generation_authority_drift[before-rules]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-proof-rejects-same-generation-authority-drift-before-rules',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': '310e68cf4f174d4ea0a2f7e7466df883cdb30675f5d6c04d4f670e816f8cfa01'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_same_generation_authority_drift[during-content]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-proof-rejects-same-generation-authority-drift-during-content',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': '310e68cf4f174d4ea0a2f7e7466df883cdb30675f5d6c04d4f670e816f8cfa01'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_same_generation_authority_drift[during-rules]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-proof-rejects-same-generation-authority-drift-during-rules',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': '310e68cf4f174d4ea0a2f7e7466df883cdb30675f5d6c04d4f670e816f8cfa01'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_linked_authority_snapshot_identity_change': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-proof-rejects-linked-authority-snapshot-identity-change',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'e0ba26253b885c23eb083884d62eb2d93bf277bad9e5a3056e18e381422e5df1'},
 'tests/test_foundation_description_proof.py::test_description_proof_accepts_current_linked_generation_and_is_immutable': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-proof-accepts-current-linked-generation-and-is-immutable',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'bdcd7692ccf6f00da541364792a6a0230217b1186eaacc62cb2541822cbbf1b9'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_string_subclasses[source-status]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-string-subclasses-source-status',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                             'source_ast_sha256': '14f12a687acfbf8979df55c2c147f36ffe11794683d0ea57fa625314cdae0342'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_string_subclasses[source-identity]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-string-subclasses-source-identity',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '14f12a687acfbf8979df55c2c147f36ffe11794683d0ea57fa625314cdae0342'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_string_subclasses[description-completeness]': {'activation_phase': 'R4',
                                                                                                                                        'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-string-subclasses-description-completeness',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                                        'source_ast_sha256': '14f12a687acfbf8979df55c2c147f36ffe11794683d0ea57fa625314cdae0342'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_string_subclasses[description-identity]': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-string-subclasses-description-identity',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': '14f12a687acfbf8979df55c2c147f36ffe11794683d0ea57fa625314cdae0342'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_string_subclasses[answer-identity]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-string-subclasses-answer-identity',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '14f12a687acfbf8979df55c2c147f36ffe11794683d0ea57fa625314cdae0342'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_wire_field_name_subclasses': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-proof-rejects-wire-field-name-subclasses',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': '62fa7d11104f4c68baff9ef2f2556e917cc0f658912cb280b5cd66576cc455fe'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_container_subclasses[applications]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-container-subclasses-applications',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': '3be71992f61c5d74cf40fa0ac3f7efce17df215ea5f51981a9d4ab254fcbe6bf'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_container_subclasses[application]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-container-subclasses-application',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': '3be71992f61c5d74cf40fa0ac3f7efce17df215ea5f51981a9d4ab254fcbe6bf'},
 'tests/test_foundation_description_proof.py::test_description_proof_rejects_nested_wire_container_subclasses[filler]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-proof-rejects-nested-wire-container-subclasses-filler',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': '3be71992f61c5d74cf40fa0ac3f7efce17df215ea5f51981a9d4ab254fcbe6bf'},
 'tests/test_foundation_description_proof.py::test_description_proof_accepts_maximum_claim_and_proof_cardinality[memory]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-proof-accepts-maximum-claim-and-proof-cardinality-memory',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'd3a02bb1555272616a93fba414dc938e908b08edb39ea3e3a5d2aa6b72d8efc4'},
 'tests/test_foundation_description_proof.py::test_description_proof_accepts_maximum_claim_and_proof_cardinality[sqlite]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-proof-accepts-maximum-claim-and-proof-cardinality-sqlite',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'd3a02bb1555272616a93fba414dc938e908b08edb39ea3e3a5d2aa6b72d8efc4'},
 'tests/test_foundation_description_proof.py::test_description_proof_claim_codec_requires_exact_wire_field_names': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-proof-claim-codec-requires-exact-wire-field-names',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': '08d10d384ec43ff1d553bfa8c3baf33348d849c3104a749a6a6d866ce459d912'}}


def _inputs(stores, expression, *, max_depth=1, max_facts=64, target_ref="entity:alice"):
    pin = stores.revision_pin()
    source = _situation(pin)
    request = DescriptionRequest.create(source_expression=_query_expression(target_ref), situation=source,
        max_depth=max_depth, max_facts=max_facts)
    authority = SimpleNamespace(generation=pin.authority_generation,
        content_hash="authority-content:description-test", atoms={}, capabilities={}, rules={})
    return source, request, authority


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_proof_retains_exact_signed_claim(tmp_path, backend):
    stores, expression, source, request, claim, authority = _seeded_description_case(
        tmp_path, backend
    )
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        before = stores.revisions()
        result, bundle = owner.describe_with_proof(request, _query_expression(request.target_ref), source)
        assert result == owner.describe(request, _query_expression(request.target_ref), source)
        assert bundle.description == result
        assert bundle.source_expression_ref == request.source_expression_ref
        assert bundle.source_expression_ref == _query_expression(request.target_ref).expression_ref
        assert bundle.answer_expression_ref == result.answer_expression.expression_ref
        assert bundle.applications == claim.applications
        assert len(bundle.claims) == 1
        assert bundle.claims[0].as_dict() == {"claim_ref": claim.claim_ref, **dict(claim.claim_payload)}
        assert bundle.revision_pin == request.revision_pin
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend,stances", (
    ("memory", ("deny",)), ("sqlite", ("deny",)),
    ("memory", ("support", "deny")), ("sqlite", ("support", "deny")),
    ("memory", ("support", "support")), ("sqlite", ("support", "support")),
), ids=("denial-memory", "denial-sqlite", "conflict-memory", "conflict-sqlite", "shared-memory", "shared-sqlite"))
def test_description_proof_preserves_signs_without_graph_truth(tmp_path, backend, stances):
    stores = _stores(backend, tmp_path)
    try:
        expression = _description_expression()
        seeds = tuple(_seed_reviewed_generic_claim(stores, expression, stance=stance,
            fact_ref=f"fact:sign-{index}", source_ref=f"source:sign-{index}",
            decision_ref=f"decision:sign-{index}", occurrence_ref=f"occurrence:sign-{index}",
            proof_refs=(f"proof:sign-{index}",)) for index, stance in enumerate(stances))
        source, request, authority = _inputs(stores, expression)
        before = stores.revisions()
        result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        assert result.completeness is (DescriptionCompleteness.CONFLICT if len(set(stances)) > 1 else DescriptionCompleteness.SUFFICIENT)
        assert len(result.answer_expression.applications) == len(bundle.applications) == 1
        assert tuple(sorted(row.stance for row in bundle.claims)) == tuple(sorted(stances))
        assert {row.claim_ref for row in bundle.claims} == {row.claim_ref for row in seeds}
        assert {row.application_ref for row in bundle.claims} == {seeds[0].root_application_ref}
        assert tuple(row.stance for row in (stores.world.get(seed.claim_payload["fact_ref"]) for seed in seeds)) == stances
        assert ProofBundle.from_dict(bundle.as_dict()) == bundle
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend,terminal", (
    ("memory", "missing"), ("sqlite", "missing"),
    ("memory", "facts"), ("sqlite", "facts"),
    ("memory", "proofs"), ("sqlite", "proofs"),
    ("memory", "depth"), ("sqlite", "depth"),
), ids=("missing-memory", "missing-sqlite", "facts-memory", "facts-sqlite", "proofs-memory", "proofs-sqlite", "depth-memory", "depth-sqlite"))
def test_description_proof_terminals_never_truncate_evidence(tmp_path, backend, terminal):
    stores = _stores(backend, tmp_path)
    try:
        expression = _description_expression()
        if terminal == "depth":
            child = expression.applications[0]
            parent = SemanticApplication("application:parent", "op:event", "event:assert", (
                RoleBinding("role:actor", GroundedReference("participant:reviewer")),
                RoleBinding("role:content", ApplicationFiller(child.application_ref)),
            ))
            expression = SemanticExpression.create(applications=(child, parent), root_refs=(parent.application_ref,))
        if terminal != "missing":
            _seed_reviewed_generic_claim(stores, expression, proof_refs=(
                tuple(f"proof:limit-{i}" for i in range(65)) if terminal == "proofs" else ("proof:normal",)))
        if terminal == "facts":
            _seed_reviewed_generic_claim(stores, expression, fact_ref="fact:second",
                decision_ref="decision:second", occurrence_ref="occurrence:second")
        source, request, authority = _inputs(stores, expression, max_facts=1)
        before = stores.revisions()
        result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        assert result.completeness is (DescriptionCompleteness.MISSING if terminal == "missing" else DescriptionCompleteness.BUDGET_EXHAUSTED)
        assert result.answer_expression is None
        assert bundle.answer_expression_ref is None
        assert bundle.claims == bundle.applications == bundle.application_refs == ()
        assert result.fact_refs == result.claim_refs == result.source_refs == result.proof_refs == result.definition_refs == ()
        assert bundle.source_expression_ref == request.source_expression_ref
        assert ProofBundle.from_dict(bundle.as_dict()) == bundle
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("corruption", ("claim", "application", "source", "bundle", "extra", "tuple", "abi-bool", "claim-bool"),
    ids=("claim", "application", "source", "bundle", "extra", "tuple", "abi-bool", "claim-bool"))
def test_description_proof_codec_rejects_tamper_and_noncanonical_types(tmp_path, corruption):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        _, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        row = bundle.as_dict()
        if corruption == "claim":
            row["claims"][0]["source_ref"] = "source:forged"
        elif corruption == "application":
            row["application_refs"][0] = "semantic_application:forged"
        elif corruption == "source":
            row["source_expression_ref"] = "expression:forged"
        elif corruption == "bundle":
            row["proof_bundle_ref"] = "proof_bundle:forged"
        elif corruption == "extra":
            row["authorized"] = True
        elif corruption == "tuple":
            row["claims"] = tuple(row["claims"])
        elif corruption == "abi-bool":
            row["abi_version"] = True
        else:
            row["claims"][0]["confidence_micros"] = True
        with pytest.raises((TypeError, ValueError)):
            ProofBundle.from_dict(row)
    finally:
        stores.close()


@pytest.mark.parametrize("corruption", ("aggregate", "sign", "pin", "roots"), ids=("aggregate", "sign", "pin", "roots"))
def test_description_proof_rejects_rehashed_inconsistent_evidence(tmp_path, corruption):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        kwargs = {name: getattr(result, name) for name in result._FIELDS - {"abi_version", "description_result_ref"}}
        claims = bundle.claims
        if corruption == "aggregate":
            kwargs["source_refs"] = ("source:invented",)
        elif corruption == "sign":
            kwargs["completeness"] = DescriptionCompleteness.CONFLICT
        elif corruption == "roots":
            kwargs["definition_refs"] = ("semantic_application:invented",)
        else:
            row = claims[0].as_dict()
            row["authority_generation"] = "authority:forged"
            row["claim_ref"] = stable_ref("semantic_claim", {name: value for name, value in row.items() if name != "claim_ref"})
            claims = (ClaimEvidence.from_dict(row),)
            kwargs["claim_refs"] = (claims[0].claim_ref,)
        changed = DescriptionResult.create(**kwargs)
        with pytest.raises(ValueError, match="(aggregate|completeness|pin|correspondence)"):
            ProofBundle.create(description=changed, application_refs=bundle.application_refs,
                claims=claims, revision_pin=request.revision_pin)
    finally:
        stores.close()


@pytest.mark.parametrize("backend,corruption", (
    ("memory", "projection"), ("sqlite", "projection"),
    ("memory", "lineage"), ("sqlite", "lineage"),
    ("memory", "transaction"), ("sqlite", "transaction"),
), ids=("projection-memory", "projection-sqlite", "lineage-memory", "lineage-sqlite", "transaction-memory", "transaction-sqlite"))
def test_description_proof_builder_rejects_changed_store_lineage(tmp_path, backend, corruption):
    stores, expression, source, request, claim, authority = _seeded_description_case(tmp_path, backend)
    try:
        if corruption == "transaction":
            if backend == "memory":
                stores._backend.world._revision_transactions[request.revision_pin.world_revision] = "transaction:forged"
            else:
                stores._backend._conn.execute("UPDATE revisions SET transaction_ref=? WHERE store='world' AND revision=?", ("transaction:forged", request.revision_pin.world_revision))
                stores._backend._conn.commit()
        else:
            fact = stores.world.get(claim.claim_payload["fact_ref"])
            changed = Fact(fact_ref=fact.fact_ref, operator=fact.operator,
                args={**fact.args, "role:instance": "entity:mallory"} if corruption == "projection" else fact.args,
                stance=fact.stance, confidence=fact.confidence, derived=fact.derived,
                proof={**fact.proof, "source": "source:forged"} if corruption == "lineage" else fact.proof)
            _physically_replace_fact(stores, backend, changed)
        with pytest.raises(ValueError, match="description claim.*(projection|lineage)"):
            QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
    finally:
        stores.close()


@pytest.mark.parametrize("backend,stale", (
    ("memory", "world"), ("sqlite", "world"),
    ("memory", "authority"), ("sqlite", "authority"),
), ids=("world-memory", "world-sqlite", "authority-memory", "authority-sqlite"))
def test_description_proof_rejects_stale_request_and_live_authority(tmp_path, backend, stale):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, backend)
    try:
        if stale == "world":
            _seed_reviewed_generic_claim(stores, _description_expression("entity:bob"),
                fact_ref="fact:bob", decision_ref="decision:bob", occurrence_ref="occurrence:bob")
        else:
            authority.generation = "authority:replacement"
        before = stores.revisions()
        with pytest.raises(StaleRevisionError):
            QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_proof_rechecks_authority_before_return(tmp_path, backend, monkeypatch):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, backend)
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        original = owner._description_at_pin
        def read_then_change_authority(request):
            answer = original(request)
            authority.generation = "authority:changed-during-read"
            return answer
        monkeypatch.setattr(owner, "_description_at_pin", read_then_change_authority)
        with pytest.raises(StaleRevisionError, match="authority changed"):
            owner.describe_with_proof(request, _query_expression(request.target_ref), source)
    finally:
        stores.close()


def test_description_proof_sqlite_restart_retains_exact_bundle(tmp_path):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "sqlite")
    try:
        first = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
    finally:
        stores.close()
    reopened = open_stores(tmp_path / "description-store", authority_generation=request.revision_pin.authority_generation)
    try:
        before = reopened.revisions()
        assert QueryDecisionOwner(reopened, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source) == first
        assert reopened.revisions() == before
    finally:
        reopened.close()


def test_description_proof_memory_sqlite_parity(tmp_path):
    bundles = []
    for backend in ("memory", "sqlite"):
        stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, backend)
        try:
            bundles.append(QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source))
        finally:
            stores.close()
    assert bundles[0] == bundles[1]


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_proof_uses_one_snapshot_and_one_target_read(tmp_path, backend, monkeypatch):
    from contextlib import contextmanager
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, backend)
    try:
        snapshot = stores.r3_read_snapshot
        target_read = stores.r3_active_application_claims_for_target
        active = 0
        snapshots = 0
        target_reads = 0
        @contextmanager
        def counted_snapshot(pin):
            nonlocal active, snapshots
            snapshots += 1
            with snapshot(pin):
                active += 1
                try:
                    yield
                finally:
                    active -= 1
        def counted_target_read(*args, **kwargs):
            nonlocal target_reads
            assert active == 1
            target_reads += 1
            return target_read(*args, **kwargs)
        def forbid_write(*args, **kwargs):
            pytest.fail("description proof attempted world mutation")
        monkeypatch.setattr(stores, "r3_read_snapshot", counted_snapshot)
        monkeypatch.setattr(stores, "r3_active_application_claims_for_target", counted_target_read)
        monkeypatch.setattr(stores.world, "commit", forbid_write)
        monkeypatch.setattr(stores, "_r3_write_normalized_batch", forbid_write)
        result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        assert snapshots == target_reads == 1
        assert bundle.description == result
    finally:
        stores.close()


def test_description_proof_indexed_work_is_independent_of_unrelated_claims(tmp_path):
    measured = []
    for unrelated in (0, 200):
        path = tmp_path / f"work-{unrelated}"
        stores = _stores("sqlite", path)
        try:
            expression = _description_expression()
            _seed_reviewed_generic_claim(stores, expression)
            for index in range(unrelated):
                _seed_reviewed_generic_claim(stores, _description_expression(f"entity:unrelated-{index}"),
                    fact_ref=f"fact:unrelated-{index}", source_ref=f"source:unrelated-{index}",
                    decision_ref=f"decision:unrelated-{index}", occurrence_ref=f"occurrence:unrelated-{index}")
            source, request, authority = _inputs(stores, expression)
            queries = []
            stores._backend._conn.set_trace_callback(queries.append)
            result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
            stores._backend._conn.set_trace_callback(None)
            assert len(bundle.claims) == len(bundle.applications) == 1
            assert result.completeness is DescriptionCompleteness.SUFFICIENT
            assert all(query.split()[0] in {"SELECT", "BEGIN", "ROLLBACK"} for query in queries)
            selects = tuple(query for query in queries if query.startswith("SELECT"))
            measured.append(len(selects))
            target_queries = tuple(query for query in selects if "semantic_claim_target_postings" in query)
            assert len(target_queries) == 1
            assert "LIMIT 65" in target_queries[0]
            plan = stores._backend._conn.execute("EXPLAIN QUERY PLAN " + target_queries[0]).fetchall()
            assert any("SEARCH" in row[3] and "target_ref" in row[3] for row in plan)
            assert not any("SCAN" in row[3] for row in plan)
        finally:
            stores.close()
    assert measured[0] == measured[1]
    assert measured[0] <= 24


@pytest.mark.parametrize("invalid", ("claim-count", "future-revision", "proof-count", "wrong-placement"),
    ids=("claim-count", "future-revision", "proof-count", "wrong-placement"))
def test_description_proof_rejects_unbounded_or_mispinned_claims(tmp_path, invalid):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        if invalid == "claim-count":
            claims = bundle.claims * 65
        else:
            row = bundle.claims[0].as_dict()
            if invalid == "future-revision":
                row["asserted_world_revision"] = request.revision_pin.world_revision + 1
            elif invalid == "proof-count":
                row["proof_refs"] = [f"proof:overflow-{index}" for index in range(65)]
            else:
                row["placement"] = "attributed"
            row["claim_ref"] = stable_ref("semantic_claim", {name: value for name, value in row.items() if name != "claim_ref"})
            if invalid in {"proof-count", "wrong-placement"}:
                with pytest.raises(ValueError):
                    ClaimEvidence.from_dict(row)
                return
            claims = (ClaimEvidence.from_dict(row),)
        with pytest.raises((TypeError, ValueError)):
            ProofBundle.create(description=result, application_refs=bundle.application_refs,
                claims=claims, revision_pin=request.revision_pin)
    finally:
        stores.close()


def test_description_proof_decoder_rejects_ref_string_subclasses(tmp_path):
    class Ref(str):
        pass
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        _, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        row = bundle.as_dict()
        row["proof_bundle_ref"] = Ref(row["proof_bundle_ref"])
        with pytest.raises(TypeError, match="exact str"):
            ProofBundle.from_dict(row)
    finally:
        stores.close()


@pytest.mark.parametrize("backend,count", (
    ("memory", 3), ("sqlite", 3), ("memory", 65), ("sqlite", 65),
), ids=("duplicates-memory", "duplicates-sqlite", "overflow-memory", "overflow-sqlite"))
def test_description_proof_preserves_bounded_claim_proof_sequence(tmp_path, backend, count):
    stores = _stores(backend, tmp_path)
    try:
        expression = _description_expression()
        proof_refs = ("proof:z", "proof:a", "proof:z") if count == 3 else ("proof:repeated",) * count
        seed = _seed_reviewed_generic_claim(stores, expression, proof_refs=proof_refs)
        source, request, authority = _inputs(stores, expression)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        assert owner.describe(request, _query_expression(request.target_ref), source).completeness is DescriptionCompleteness.SUFFICIENT
        result, bundle = owner.describe_with_proof(request, _query_expression(request.target_ref), source)
        if count <= 64:
            assert bundle.claims[0].proof_refs == tuple(seed.claim_payload["proof_refs"])
            assert bundle.description.proof_refs == ("proof:a", "proof:z")
            assert ProofBundle.from_dict(bundle.as_dict()) == bundle
        else:
            assert result.completeness is DescriptionCompleteness.BUDGET_EXHAUSTED
            assert result.answer_expression is None
            assert bundle.claims == bundle.application_refs == ()
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_proof_retains_nested_persistent_application_correspondence(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        child = _description_expression().applications[0]
        parent = SemanticApplication("application:parent", "op:event", "event:assert", (
            RoleBinding("role:actor", GroundedReference("participant:reviewer")),
            RoleBinding("role:content", ApplicationFiller(child.application_ref)),
        ))
        expression = SemanticExpression.create(applications=(child, parent), root_refs=(parent.application_ref,))
        seeds = tuple(_seed_reviewed_generic_claim(stores, expression, stance=stance,
            fact_ref=f"fact:nested-{index}", decision_ref=f"decision:nested-{index}",
            occurrence_ref=f"occurrence:nested-{index}") for index, stance in enumerate(("support", "deny")))
        source, request, authority = _inputs(stores, expression, max_depth=2)
        result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        assert result.completeness is DescriptionCompleteness.CONFLICT
        assert len(bundle.application_refs) == len(bundle.applications) == 2
        assert set(bundle.applications) == set(seeds[0].applications)
        assert {claim.application_ref for claim in bundle.claims} == {seeds[0].root_application_ref}
        assert ProofBundle.from_dict(bundle.as_dict()) == bundle
        row = bundle.as_dict()
        row["application_refs"].reverse()
        with pytest.raises(ValueError, match="correspondence|identity"):
            ProofBundle.from_dict(row)
    finally:
        stores.close()


@pytest.mark.parametrize("backend,corruption", (
    ("memory", "claim"), ("sqlite", "claim"),
    ("memory", "application"), ("sqlite", "application"),
), ids=("claim-memory", "claim-sqlite", "application-memory", "application-sqlite"))
def test_description_proof_rejects_normalized_identity_tamper(tmp_path, backend, corruption):
    stores, expression, source, request, seed, authority = _seeded_description_case(tmp_path, backend)
    try:
        if backend == "memory":
            if corruption == "claim":
                stores._backend._normalized_claims[seed.claim_ref]["stance"] = "deny"
            else:
                stores._backend._normalized_applications[seed.root_application_ref]["predicate_ref"] = "concept:forged"
        else:
            if corruption == "claim":
                stores._backend._conn.execute("UPDATE semantic_application_claims SET stance='deny' WHERE claim_ref=?", (seed.claim_ref,))
            else:
                stores._backend._conn.execute("UPDATE semantic_applications SET predicate_ref='concept:forged' WHERE application_ref=?", (seed.root_application_ref,))
            stores._backend._conn.commit()
        with pytest.raises(ValueError, match="(identity|hash)"):
            QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
    finally:
        stores.close()


def test_description_proof_structural_codec_does_not_authenticate_publication(tmp_path):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        result, bundle = owner.describe_with_proof(request, _query_expression(request.target_ref), source)
        row = bundle.claims[0].as_dict()
        row["source_ref"] = "source:unpublished"
        row["claim_ref"] = stable_ref("semantic_claim", {name: value for name, value in row.items() if name != "claim_ref"})
        evidence = ClaimEvidence.from_dict(row)
        kwargs = {name: getattr(result, name) for name in result._FIELDS - {"abi_version", "description_result_ref"}}
        kwargs["claim_refs"] = (evidence.claim_ref,)
        kwargs["source_refs"] = (evidence.source_ref,)
        before = stores.revisions()
        structural = ProofBundle.create(description=DescriptionResult.create(**kwargs), application_refs=bundle.application_refs,
            claims=(evidence,), revision_pin=request.revision_pin)
        assert ProofBundle.from_dict(structural.as_dict()) == structural
        assert owner.describe_with_proof(request, _query_expression(request.target_ref), source) == (result, bundle)
        assert stores.revisions() == before
        assert "authorized" not in structural.as_dict()
    finally:
        stores.close()


@pytest.mark.parametrize("timing,field", (
    ("before", "content_hash"), ("before", "rules"),
    ("during", "content_hash"), ("during", "rules"),
), ids=("before-content", "before-rules", "during-content", "during-rules"))
def test_description_proof_rejects_same_generation_authority_drift(tmp_path, timing, field, monkeypatch):
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        activated_key = owner._rule_index_key
        def change_authority():
            setattr(authority, field, "authority-content:forged" if field == "content_hash" else {})
        if timing == "before":
            change_authority()
        else:
            original = owner._description_at_pin
            def read_then_change_authority(request):
                answer = original(request)
                change_authority()
                return answer
            monkeypatch.setattr(owner, "_description_at_pin", read_then_change_authority)
        with pytest.raises(StaleRevisionError, match="authority"):
            owner.describe_with_proof(request, _query_expression(request.target_ref), source)
        assert owner._rule_index_key == activated_key
    finally:
        stores.close()


def test_description_proof_rejects_linked_authority_snapshot_identity_change(linked_authority, monkeypatch):
    from cemm_authoritative_hybrid.persistence import memory_stores
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        expression = _description_expression()
        _seed_reviewed_generic_claim(stores, expression)
        source, request, _ = _inputs(stores, expression)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        original = owner._description_at_pin
        def read_then_replace_snapshot(request):
            answer = original(request)
            generation, content_hash, rules = linked_authority.rule_generation_snapshot()
            object.__setattr__(linked_authority, "_rule_generation_state", (generation, content_hash, rules))
            return answer
        monkeypatch.setattr(owner, "_description_at_pin", read_then_replace_snapshot)
        with pytest.raises(StaleRevisionError, match="authority"):
            owner.describe_with_proof(request, _query_expression(request.target_ref), source)
    finally:
        stores.close()


def test_description_proof_accepts_current_linked_generation_and_is_immutable(linked_authority):
    from dataclasses import FrozenInstanceError
    from cemm_authoritative_hybrid.persistence import memory_stores
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        expression = _description_expression()
        _seed_reviewed_generic_claim(stores, expression)
        source, request, _ = _inputs(stores, expression)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        result, bundle = owner.describe_with_proof(request, _query_expression(request.target_ref), source)
        assert owner.describe_with_proof(request, _query_expression(request.target_ref), source) == (result, bundle)
        assert ProofBundle.from_dict(bundle.as_dict()) == bundle
        assert bundle.claims[0].authority_generation == linked_authority.generation
        with pytest.raises(FrozenInstanceError):
            bundle.claims[0].stance = "deny"
        with pytest.raises(FrozenInstanceError):
            bundle.claims = ()
        with pytest.raises(TypeError, match="create"):
            ClaimEvidence()
        with pytest.raises(TypeError, match="create"):
            ProofBundle()
    finally:
        stores.close()


@pytest.mark.parametrize("path", (
    ("description", "request", "requested_content"), ("description", "request", "source_expression_ref"),
    ("description", "completeness"), ("description", "description_result_ref"),
    ("description", "answer_expression", "expression_ref"),
), ids=("source-status", "source-identity", "description-completeness", "description-identity", "answer-identity"))
def test_description_proof_rejects_nested_wire_string_subclasses(tmp_path, path):
    class WireString(str):
        pass
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        _, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        wire = bundle.as_dict()
        target = wire
        for field in path[:-1]:
            target = target[field]
        target[path[-1]] = WireString(target[path[-1]])
        with pytest.raises(TypeError):
            ProofBundle.from_dict(wire)
    finally:
        stores.close()


def test_description_proof_rejects_wire_field_name_subclasses(tmp_path):
    class WireString(str):
        pass
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        _, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        wire = bundle.as_dict()
        wire[WireString("description")] = wire.pop("description")
        with pytest.raises(TypeError):
            ProofBundle.from_dict(wire)
    finally:
        stores.close()


@pytest.mark.parametrize("container", ("applications", "application", "filler"),
    ids=("applications", "application", "filler"))
def test_description_proof_rejects_nested_wire_container_subclasses(tmp_path, container):
    class WireList(list):
        pass
    class WireDict(dict):
        pass
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        _, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        wire = bundle.as_dict()
        answer = wire["description"]["answer_expression"]
        if container == "applications":
            answer["applications"] = WireList(answer["applications"])
        elif container == "application":
            answer["applications"][0] = WireDict(answer["applications"][0])
        else:
            binding = answer["applications"][0]["roles"][0]
            binding["filler"] = WireDict(binding["filler"])
        with pytest.raises(TypeError):
            ProofBundle.from_dict(wire)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_proof_accepts_maximum_claim_and_proof_cardinality(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        expression = _description_expression()
        proof_refs = ("proof:z", "proof:a") * 32
        seeds = tuple(_seed_reviewed_generic_claim(stores, expression,
            fact_ref=f"fact:maximum-{index}", source_ref=f"source:maximum-{index}",
            decision_ref=f"decision:maximum-{index}", occurrence_ref=f"occurrence:maximum-{index}",
            proof_refs=proof_refs) for index in range(64))
        source, request, authority = _inputs(stores, expression, max_facts=64)
        result, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        assert result.completeness is DescriptionCompleteness.SUFFICIENT
        assert len(bundle.claims) == len(result.fact_refs) == len(result.claim_refs) == len(result.source_refs) == 64
        assert len(bundle.applications) == 1
        assert {claim.claim_ref for claim in bundle.claims} == {seed.claim_ref for seed in seeds}
        assert all(claim.proof_refs == proof_refs for claim in bundle.claims)
        assert sum(len(claim.proof_refs) for claim in bundle.claims) == 4096
        assert ProofBundle.from_dict(bundle.as_dict()) == bundle
    finally:
        stores.close()


def test_description_proof_claim_codec_requires_exact_wire_field_names(tmp_path):
    class WireString(str):
        pass
    stores, expression, source, request, _, authority = _seeded_description_case(tmp_path, "memory")
    try:
        _, bundle = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).describe_with_proof(request, _query_expression(request.target_ref), source)
        wire = bundle.claims[0].as_dict()
        wire[WireString("stance")] = wire.pop("stance")
        with pytest.raises(TypeError):
            ClaimEvidence.from_dict(wire)
    finally:
        stores.close()
