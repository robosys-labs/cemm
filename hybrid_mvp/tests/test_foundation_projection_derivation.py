"""Exact nonpersistent request derivation from activated source constructions."""
from dataclasses import fields, replace

import pytest

from cemm_authoritative_hybrid.authority import DesignationFact
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.coverage import COVERAGE_ABI_VERSION, CoverageReceipt, CoverageVerifier
from cemm_authoritative_hybrid.expressions import CompilationFailure, QueryProjection, SemanticExpression, SemanticExpressionCompiler
from cemm_authoritative_hybrid.programs import ACTION_ABI_SCHEMAS, PROGRAM_ABI_VERSION, SWITCH_ACTION_TYPES, ProgramAction, SemanticSwitchProgram, SourceAssignment
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.proposal_context import QueryProjectionSlot, licensed_query_projection_slots
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier, LegalActionIndex, _proof_errors
from cemm_authoritative_hybrid.verifier_reconstruction import reconstruct_expected_expression
from tests.test_foundation_projection_construction import _fixture, _with_slots, runtime

__cemm_test_inventory__ = {'tests/test_foundation_projection_derivation.py::test_projection_derivation_program_and_coverage_hard_cut': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-projection-derivation-program-and-coverage-hard-cut',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                              'source_ast_sha256': 'f322d67a422023dba60885d640a8dc3c56e941789af74651d87c10bd9d2a3e7f'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_source_to_verify_preserves_both_readings[en-bare]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-projection-derivation-source-to-verify-preserves-both-readings-en-bare',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '0e85920c03716df0b83b7f8b9f8ec01f4125805407f83a8da69e09a2bb66b348'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_source_to_verify_preserves_both_readings[en-article]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-source-to-verify-preserves-both-readings-en-article',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '0e85920c03716df0b83b7f8b9f8ec01f4125805407f83a8da69e09a2bb66b348'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_source_to_verify_preserves_both_readings[es-bare]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-projection-derivation-source-to-verify-preserves-both-readings-es-bare',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '0e85920c03716df0b83b7f8b9f8ec01f4125805407f83a8da69e09a2bb66b348'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_source_to_verify_preserves_both_readings[es-article]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-source-to-verify-preserves-both-readings-es-article',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '0e85920c03716df0b83b7f8b9f8ec01f4125805407f83a8da69e09a2bb66b348'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_zero_application_context_is_nonempty': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-zero-application-context-is-nonempty',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'ba0fe867c00d04e7e193b432ca2aa7a7b447a73d5443141c3ff25d82b32aa27d'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_alias_cross_product_is_not_content_policy': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-projection-derivation-alias-cross-product-is-not-content-policy',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': '5a21d02bae86923f03e89d96c9a7527edbd4eb4c932f291ef2198080ea11f4f9'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_evidence_fails_every_exact_sink[match]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-evidence-fails-every-exact-sink-match',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': '3333bc249ca97026e1934427c0db2000299ed20a4a615a016a3fdebeae9c0ad4'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_evidence_fails_every_exact_sink[index]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-evidence-fails-every-exact-sink-index',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': '3333bc249ca97026e1934427c0db2000299ed20a4a615a016a3fdebeae9c0ad4'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_evidence_fails_every_exact_sink[schema]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-evidence-fails-every-exact-sink-schema',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                                 'source_ast_sha256': '3333bc249ca97026e1934427c0db2000299ed20a4a615a016a3fdebeae9c0ad4'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_evidence_fails_every_exact_sink[content]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-evidence-fails-every-exact-sink-content',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '3333bc249ca97026e1934427c0db2000299ed20a4a615a016a3fdebeae9c0ad4'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_evidence_fails_every_exact_sink[primitive]': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-evidence-fails-every-exact-sink-primitive',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': '3333bc249ca97026e1934427c0db2000299ed20a4a615a016a3fdebeae9c0ad4'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_evidence_fails_every_exact_sink[activation]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-evidence-fails-every-exact-sink-activation',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '3333bc249ca97026e1934427c0db2000299ed20a4a615a016a3fdebeae9c0ad4'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_predecessor_abi_is_rejected[program]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-predecessor-abi-is-rejected-program',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'facc90cad7c5848590a7378bf32caffa73eccf9095aa552f0e33a9ebc7a66455'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_predecessor_abi_is_rejected[coverage]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-derivation-predecessor-abi-is-rejected-coverage',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'facc90cad7c5848590a7378bf32caffa73eccf9095aa552f0e33a9ebc7a66455'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_predecessor_abi_is_rejected[proposal]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-derivation-predecessor-abi-is-rejected-proposal',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'facc90cad7c5848590a7378bf32caffa73eccf9095aa552f0e33a9ebc7a66455'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_predecessor_abi_is_rejected[context]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-predecessor-abi-is-rejected-context',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'facc90cad7c5848590a7378bf32caffa73eccf9095aa552f0e33a9ebc7a66455'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_unlicensed_sources_have_no_request[unknown]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-projection-derivation-unlicensed-sources-have-no-request-unknown',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'f45478e5c98bd384f42e87afb560e762b2212919a1ee64c2b6c1bcdf3c1af7e1'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_unlicensed_sources_have_no_request[deixis]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-projection-derivation-unlicensed-sources-have-no-request-deixis',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'f45478e5c98bd384f42e87afb560e762b2212919a1ee64c2b6c1bcdf3c1af7e1'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_unlicensed_sources_have_no_request[scope]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-projection-derivation-unlicensed-sources-have-no-request-scope',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'f45478e5c98bd384f42e87afb560e762b2212919a1ee64c2b6c1bcdf3c1af7e1'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_unlicensed_sources_have_no_request[compound]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:foundation-projection-derivation-unlicensed-sources-have-no-request-compound',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                                             'source_ast_sha256': 'f45478e5c98bd384f42e87afb560e762b2212919a1ee64c2b6c1bcdf3c1af7e1'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_unlicensed_sources_have_no_request[quantifier]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-projection-derivation-unlicensed-sources-have-no-request-quantifier',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'f45478e5c98bd384f42e87afb560e762b2212919a1ee64c2b6c1bcdf3c1af7e1'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_assignment_cannot_masquerade_as_a_role': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-projection-derivation-assignment-cannot-masquerade-as-a-role',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': 'a729554bdbaece5e672824d0ec79de2519d1df0a29cc977649a36f7318ca60b2'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_action_mask_accounts_for_leaf_and_root': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-projection-derivation-action-mask-accounts-for-leaf-and-root',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': '78a7165e4beae768627876be72f2307cf9c497c531d6da0b678222fb365290eb'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_supervision_schema_matches_action_abi': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-derivation-supervision-schema-matches-action-abi',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': '4252007fd73b8fd91a0e551bb00f5a33387539e4e95467999daa09a3925b5b9c'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_reviewed_blueprint_is_independent_and_rematched': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-projection-derivation-reviewed-blueprint-is-independent-and-rematched',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': '505162c6c9ff2ea643702fd0f61a111a8d8decaddb18d4f49088c8cf46d21167'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_single_content_diagnostic_uses_real_evaluation_and_response[description]': {'activation_phase': 'R4',
                                                                                                                                                         'assertion_ref': 'assertion:foundation-projection-derivation-single-content-diagnostic-uses-real-evaluation-and-response-description',
                                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                                                         'source_ast_sha256': '63810082a52438d023d617f5227f6be7d41cd135b63f49af2f4609edddb3b433'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_single_content_diagnostic_uses_real_evaluation_and_response[definition]': {'activation_phase': 'R4',
                                                                                                                                                        'assertion_ref': 'assertion:foundation-projection-derivation-single-content-diagnostic-uses-real-evaluation-and-response-definition',
                                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                                                        'source_ast_sha256': '63810082a52438d023d617f5227f6be7d41cd135b63f49af2f4609edddb3b433'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_candidate_source_rows_emit_complete_alternatives[en]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-candidate-source-rows-emit-complete-alternatives-en',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '69b49ba5b286e117dd69c66fe65bb79532422a9fb42a3d77d02f28d0e846f237'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_candidate_source_rows_emit_complete_alternatives[es]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-candidate-source-rows-emit-complete-alternatives-es',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '69b49ba5b286e117dd69c66fe65bb79532422a9fb42a3d77d02f28d0e846f237'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_public_request_keeps_ambiguity_without_world_effect': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:foundation-projection-derivation-public-request-keeps-ambiguity-without-world-effect',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': '023c64dfc3a4f09aa37c05f406ec215654d3f41898b220b0954ab5d90040b536'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_port_ownership_is_exact[drop]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-port-ownership-is-exact-drop',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': 'ce39639e104d8ec6cf96fe38c4e9449f642849eafd547804a82c34445069e32c'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_port_ownership_is_exact[pointer]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-port-ownership-is-exact-pointer',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'ce39639e104d8ec6cf96fe38c4e9449f642849eafd547804a82c34445069e32c'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_port_ownership_is_exact[critical]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-port-ownership-is-exact-critical',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'ce39639e104d8ec6cf96fe38c4e9449f642849eafd547804a82c34445069e32c'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_port_ownership_is_exact[sources]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-port-ownership-is-exact-sources',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'ce39639e104d8ec6cf96fe38c4e9449f642849eafd547804a82c34445069e32c'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_compilation_claim_is_not_authority[target]': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-compilation-claim-is-not-authority-target',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                                    'source_ast_sha256': '4057b57579de2a57f096b88c0c8af64d374dc46b10056c4793fb6569979a7667'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_compilation_claim_is_not_authority[content]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-compilation-claim-is-not-authority-content',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                                     'source_ast_sha256': '4057b57579de2a57f096b88c0c8af64d374dc46b10056c4793fb6569979a7667'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_compilation_claim_is_not_authority[grounding]': {'activation_phase': 'R4',
                                                                                                                                       'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-compilation-claim-is-not-authority-grounding',
                                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                                       'source_ast_sha256': '4057b57579de2a57f096b88c0c8af64d374dc46b10056c4793fb6569979a7667'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_compilation_claim_is_not_authority[assignment]': {'activation_phase': 'R4',
                                                                                                                                        'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-compilation-claim-is-not-authority-assignment',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                                        'source_ast_sha256': '4057b57579de2a57f096b88c0c8af64d374dc46b10056c4793fb6569979a7667'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_compilation_claim_is_not_authority[root]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-compilation-claim-is-not-authority-root',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                                  'source_ast_sha256': '4057b57579de2a57f096b88c0c8af64d374dc46b10056c4793fb6569979a7667'},
 'tests/test_foundation_projection_derivation.py::test_projection_article_metadata_keeps_exact_nominal_signature[honest]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-article-metadata-keeps-exact-nominal-signature-honest', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '9f8c6a84b71a23af0d37e816cd9e1312048063a47411224cf87caca2e6a3a340'},
 'tests/test_foundation_projection_derivation.py::test_projection_article_metadata_keeps_exact_nominal_signature[wrong-role]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-article-metadata-keeps-exact-nominal-signature-wrong-role', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '9f8c6a84b71a23af0d37e816cd9e1312048063a47411224cf87caca2e6a3a340'},
 'tests/test_foundation_projection_derivation.py::test_projection_article_metadata_keeps_exact_nominal_signature[extra-key]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-article-metadata-keeps-exact-nominal-signature-extra-key', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '9f8c6a84b71a23af0d37e816cd9e1312048063a47411224cf87caca2e6a3a340'},
 'tests/test_foundation_projection_derivation.py::test_projection_article_metadata_keeps_exact_nominal_signature[wrong-primary]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-article-metadata-keeps-exact-nominal-signature-wrong-primary', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '9f8c6a84b71a23af0d37e816cd9e1312048063a47411224cf87caca2e6a3a340'},
 'tests/test_foundation_projection_derivation.py::test_projection_article_metadata_keeps_exact_nominal_signature[primitive-ref]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-article-metadata-keeps-exact-nominal-signature-primitive-ref', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '9f8c6a84b71a23af0d37e816cd9e1312048063a47411224cf87caca2e6a3a340'},
 'tests/test_foundation_projection_derivation.py::test_projection_article_metadata_keeps_exact_nominal_signature[provenance]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-article-metadata-keeps-exact-nominal-signature-provenance', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '9f8c6a84b71a23af0d37e816cd9e1312048063a47411224cf87caca2e6a3a340'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_contribution_contract_is_not_authority[binder-ports]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-contribution-contract-is-not-authority-binder-ports', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '3211fa129fb247eeeb2694c351295abf8fc8adaf6902acb6f7a5e573b67be459'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_contribution_contract_is_not_authority[request-ports]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-contribution-contract-is-not-authority-request-ports', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '3211fa129fb247eeeb2694c351295abf8fc8adaf6902acb6f7a5e573b67be459'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_contribution_contract_is_not_authority[anchor-ports]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-contribution-contract-is-not-authority-anchor-ports', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '3211fa129fb247eeeb2694c351295abf8fc8adaf6902acb6f7a5e573b67be459'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_contribution_contract_is_not_authority[anchor-ref]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-contribution-contract-is-not-authority-anchor-ref', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '3211fa129fb247eeeb2694c351295abf8fc8adaf6902acb6f7a5e573b67be459'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_contribution_contract_is_not_authority[anchor-provenance]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-contribution-contract-is-not-authority-anchor-provenance', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '3211fa129fb247eeeb2694c351295abf8fc8adaf6902acb6f7a5e573b67be459'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_rehashed_contribution_contract_is_not_authority[anchor-frame]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-rehashed-contribution-contract-is-not-authority-anchor-frame', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '3211fa129fb247eeeb2694c351295abf8fc8adaf6902acb6f7a5e573b67be459'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_authentic_profile_ports_preserve_alias_targets[entity]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-authentic-profile-ports-preserve-alias-targets-entity', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '154e0c3e1f00d339d1c5b4604d919a24d749f559f6af6dab0731191da475faa3'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_authentic_profile_ports_preserve_alias_targets[concept]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-authentic-profile-ports-preserve-alias-targets-concept', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '154e0c3e1f00d339d1c5b4604d919a24d749f559f6af6dab0731191da475faa3'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_authentic_profile_ports_preserve_alias_targets[participant]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-authentic-profile-ports-preserve-alias-targets-participant', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '154e0c3e1f00d339d1c5b4604d919a24d749f559f6af6dab0731191da475faa3'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_cached_affordance_owner_cannot_be_replaced': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-cached-affordance-owner-cannot-be-replaced', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '393c9ac65423aa37da8ee4004863bd018ca68ad37018e02693c9f9f17439c8e9'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_registry_agrees_with_active_codecs[program]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-registry-agrees-with-active-codecs-program', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': 'cfea5864a88d8f8c207de41bb40e755759ec2676e651909530b7156cc893e439'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_registry_agrees_with_active_codecs[coverage]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-registry-agrees-with-active-codecs-coverage', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': 'cfea5864a88d8f8c207de41bb40e755759ec2676e651909530b7156cc893e439'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_counterfeit_authority_equality_cannot_license_ports': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-counterfeit-authority-equality-cannot-license-ports', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': '238ca4c4bbc3c1a6b82aaebb0dac1c1fb1505d6a9608a0ab8d255d4cbd0b8868'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_activation_requires_actual_exact_owners[factory-authority]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-activation-requires-actual-exact-owners-factory-authority', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': 'ec23766cc8d66c7be2f3ee5e89da07f2d9a2c6aeca157259d7054f48d12759d8'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_activation_requires_actual_exact_owners[factory-config]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-activation-requires-actual-exact-owners-factory-config', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': 'ec23766cc8d66c7be2f3ee5e89da07f2d9a2c6aeca157259d7054f48d12759d8'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_activation_requires_actual_exact_owners[activation]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-activation-requires-actual-exact-owners-activation', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': 'ec23766cc8d66c7be2f3ee5e89da07f2d9a2c6aeca157259d7054f48d12759d8'},
 'tests/test_foundation_projection_derivation.py::test_projection_derivation_activation_requires_actual_exact_owners[exact-sinks]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:foundation-projection-derivation-activation-requires-actual-exact-owners-exact-sinks', 'diagnostic_role': 'owner', 'introduced_by_task': 'Foundation-Task-7', 'owner_ref': 'decision-query-proof', 'source_ast_sha256': 'ec23766cc8d66c7be2f3ee5e89da07f2d9a2c6aeca157259d7054f48d12759d8'},
}


def _candidate(runtime, surface="what is Bob?", language="en", *, facts=None):
    pack, index, context = _fixture(runtime, surface, language, facts=facts)
    context = _with_slots(context, licensed_query_projection_slots(index, context))
    return index, context, BootstrapProposer(RuntimeConfig.release()).propose(context)


def test_projection_derivation_program_and_coverage_hard_cut():
    assert PROGRAM_ABI_VERSION == COVERAGE_ABI_VERSION == 3
    assert len(SWITCH_ACTION_TYPES) == 12
    assert ACTION_ABI_SCHEMAS["project_variable"] == (
        ("binder_local_ref", "variable_slot_ref", "body_node_ref"),
        ("projection_local_ref", "query_projection_slot_ref"),
    )
    action = ProgramAction.create(action_index=2, action_type="project_variable", arguments=("request:local", "slot:projection"))
    assert ProgramAction.from_dict(action.as_dict()) == action
    with pytest.raises(ValueError):
        ProgramAction.create(action_index=2, action_type="project_variable", arguments=("request:local",))


@pytest.mark.parametrize("language,surface", (("en", "what is Bob?"), ("en", "what is the Bob?"), ("es", "qué es Bob?"), ("es", "qué es el Bob?")), ids=("en-bare", "en-article", "es-bare", "es-article"))
def test_projection_derivation_source_to_verify_preserves_both_readings(runtime, language, surface):
    index, context, proposal = _candidate(runtime, surface, language)
    assert len(proposal.candidates) == 2 and not proposal.truncated
    batch = ExactProgramVerifier(authority=runtime.authority, role_schema_index=index).verify_candidates(proposal, context)
    assert batch.selected_meaning is None and len(batch.ambiguity_expression_refs) == 2
    contents = set()
    for candidate, receipt in zip(proposal.candidates, batch.candidate_receipts, strict=True):
        program = candidate.program
        assert program.as_dict()["abi_version"] == 3 and receipt.accepted
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, context)
        assert not isinstance(compiled, CompilationFailure)
        assert reconstruct_expected_expression(program, context, authority=runtime.authority, role_schema_index=index) == compiled.expression
        assert compiled.expression.applications == ()
        assert compiled.expression.scope_operators == compiled.expression.binders == compiled.expression.expression_links == ()
        assert len(compiled.expression.query_projections) == len(compiled.expression.root_refs) == 1
        request = compiled.expression.query_projections[0]
        assert request.target_ref == "entity:bob"
        contents.add(request.requested_content)
        projection_action = next(a for a in program.actions if a.action_type == "project_variable")
        slot = context.query_projection(projection_action.arguments[1])
        semantic_refs = {ref for b in slot.bindings for ref in b.source_unit_refs if ref not in slot.orthographic_source_unit_refs}
        assert set(projection_action.source_unit_refs) == semantic_refs
        assignments = {a.source_unit_ref: a for a in program.source_assignments}
        for binding in slot.bindings:
            for ref in binding.source_unit_refs:
                if ref in semantic_refs:
                    assignment = assignments[ref]
                    assert assignment.assignment_kind == "projection" and assignment.target_role_ref is None
                    assert assignment.target_action_ref == projection_action.action_ref
                    assert assignment.contribution_slot_ref == binding.contribution_slot_ref
        assert _proof_errors(program, context, compiled.expression, compiled.proof, authority=runtime.authority, role_schema_index=index) == ()
        assert all(ref in compiled.proof.grounding_refs for ref in slot.provenance_refs)
        assert len(compiled.proof.action_translations) == len(program.actions)
        assert len(compiled.proof.assignment_translations) == len(program.source_assignments)
        assert len(compiled.proof.root_translations) == 1
    assert contents == {"description", "definition"}


def test_projection_derivation_zero_application_context_is_nonempty(runtime):
    index, context, proposal = _candidate(runtime)
    values = {f.name: getattr(context, f.name) for f in fields(context) if f.init and f.name not in {"context_ref", "abi_version"}}
    values["application_frames"] = ()
    from cemm_authoritative_hybrid.proposal_context import ProposalContext
    context = ProposalContext.create(**values)
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)
    assert len(proposal.candidates) == 2
    for candidate in proposal.candidates:
        assert candidate.program.root_refs
        assert not any(a.action_type == "instantiate_operator" for a in candidate.program.actions)
        assert CoverageVerifier(role_schema_index=index).verify(context, candidate.program).executable


def test_projection_derivation_alias_cross_product_is_not_content_policy(runtime):
    facts = tuple(DesignationFact.create(surface="vel nora", target_ref=ref, language="en") for ref in ("entity:bob", "entity:alice"))
    index, context, proposal = _candidate(runtime, "what is vel nora?", facts=facts)
    assert len(proposal.candidates) == 4 and not proposal.truncated
    expressions = [SemanticExpressionCompiler(role_schema_index=index).compile(c.program, context).expression for c in proposal.candidates]
    assert {(e.query_projections[0].target_ref, e.query_projections[0].requested_content) for e in expressions} == {(target, content) for target in ("entity:bob", "entity:alice") for content in ("description", "definition")}
    assert len({c.score_q for c in proposal.candidates}) == 1


@pytest.mark.parametrize("mutation", ("match", "index", "schema", "content", "primitive", "activation"), ids=("match", "index", "schema", "content", "primitive", "activation"))
def test_projection_derivation_rehashed_evidence_fails_every_exact_sink(runtime, mutation):
    index, context, proposal = _candidate(runtime)
    original = proposal.candidates[0].program
    honest = SemanticExpressionCompiler(role_schema_index=index).compile(original, context)
    slot = context.query_projection(next(a.arguments[1] for a in original.actions if a.action_type == "project_variable"))
    values = {f.name: getattr(slot, f.name) for f in fields(slot) if f.name != "slot_ref"}
    if mutation in {"match", "index", "schema"}:
        key = mutation + "_ref"
        values[key] = "reviewed_query_projection_" + mutation + ":forged"
        values["provenance_refs"] = tuple(values[key] if ref == getattr(slot, key) else ref for ref in slot.provenance_refs)
    elif mutation == "content":
        values["requested_content"] = "definition" if slot.requested_content == "description" else "description"
    forged = QueryProjectionSlot.create(**values)
    context = _with_slots(context, (forged,))
    if mutation == "primitive":
        binder = next(c for c in context.contribution_slots if c.kind == "binder")
        from cemm_authoritative_hybrid.proposal_context import ContributionSlot, ProposalContext
        contribution = ContributionSlot.create(**{f.name: ("form_contribution:forged" if f.name == "contribution_ref" else getattr(binder, f.name)) for f in fields(binder) if f.name != "slot_ref"})
        # The slot's selected binder has gone stale, so structural construction
        # itself rejects this pointer. Rehash both before testing actual sinks.
        bindings = tuple(replace(b, contribution_slot_ref=contribution.slot_ref) if b.contribution_slot_ref == binder.slot_ref else b for b in forged.bindings)
        values = {f.name: getattr(forged, f.name) for f in fields(forged) if f.name != "slot_ref"}
        values["bindings"] = bindings
        values["provenance_refs"] = tuple(contribution.slot_ref if ref == binder.slot_ref else ref for ref in forged.provenance_refs)
        forged = QueryProjectionSlot.create(**values)
        context_values = {f.name: getattr(context, f.name) for f in fields(context) if f.init and f.name not in {"context_ref", "abi_version"}}
        context_values["contribution_slots"] = tuple(contribution if c is binder else c for c in context.contribution_slots)
        context_values["query_projection_slots"] = (forged,)
        context = ProposalContext.create(**context_values)
    if mutation == "activation":
        object.__setattr__(index, "index_ref", "reviewed_role_schema_index:forged")
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)
    assert len(proposal.candidates) == 1
    program = proposal.candidates[0].program
    assert not CoverageVerifier(role_schema_index=index).verify(context, program).executable
    assert isinstance(SemanticExpressionCompiler(role_schema_index=index).compile(program, context), CompilationFailure)
    assert reconstruct_expected_expression(program, context, authority=runtime.authority, role_schema_index=index) is None
    assert _proof_errors(program, context, honest.expression, honest.proof, authority=runtime.authority, role_schema_index=index)
    batch = ExactProgramVerifier(authority=runtime.authority, role_schema_index=index).verify_candidates(proposal, context)
    assert batch.selected_meaning is None and not batch.candidate_receipts[0].accepted


@pytest.mark.parametrize("artifact", ("program", "coverage", "proposal", "context"), ids=("program", "coverage", "proposal", "context"))
def test_projection_derivation_predecessor_abi_is_rejected(runtime, artifact):
    from cemm_authoritative_hybrid.proposal import ProposalResult
    from cemm_authoritative_hybrid.proposal_context import ProposalContext
    index, context, proposal = _candidate(runtime)
    program = proposal.candidates[0].program
    coverage = CoverageVerifier(role_schema_index=index).verify(context, program)
    value, decoder = {"program": (program, SemanticSwitchProgram.from_dict),
        "coverage": (coverage, CoverageReceipt.from_dict),
        "proposal": (proposal, ProposalResult.from_dict),
        "context": (context, ProposalContext.from_dict)}[artifact]
    wire = value.as_dict()
    if artifact == "proposal":
        wire["candidates"][0]["program"]["abi_version"] = 2
    else:
        wire["abi_version"] = 2
    with pytest.raises(ValueError):
        decoder(wire)


@pytest.mark.parametrize("surface", ("what is velnora?", "what is you?", "what is not Bob?", "what is Bob and Alice?", "what is every mother?"), ids=("unknown", "deixis", "scope", "compound", "quantifier"))
def test_projection_derivation_unlicensed_sources_have_no_request(runtime, surface):
    _, context, proposal = _candidate(runtime, surface)
    assert context.query_projection_slots == ()
    assert not any(a.action_type == "project_variable" and len(a.arguments) == 2 for c in proposal.candidates for a in c.program.actions)


def test_projection_derivation_assignment_cannot_masquerade_as_a_role(runtime):
    index, context, proposal = _candidate(runtime)
    assignment = next(a for a in proposal.candidates[0].program.source_assignments if a.assignment_kind == "projection")
    values = {f.name: getattr(assignment, f.name) for f in fields(assignment) if f.name != "assignment_ref"}
    values["target_role_ref"] = "role:subject"
    with pytest.raises(ValueError, match="projection"):
        SourceAssignment.create(**values)


def test_projection_derivation_action_mask_accounts_for_leaf_and_root(runtime):
    _, context, proposal = _candidate(runtime)
    program = proposal.candidates[0].program
    mask = LegalActionIndex(context, max_depth=1)
    for i, action in enumerate(program.actions):
        assert mask.is_legal(action, program.actions[:i])
    projection = next(a for a in program.actions if a.action_type == "project_variable")
    prefix = program.actions[:projection.action_index]
    assert not mask.is_legal(ProgramAction.create(action_index=len(prefix), action_type="project_variable", arguments=projection.arguments), prefix)


def test_projection_derivation_supervision_schema_matches_action_abi():
    import json
    from pathlib import Path
    from cemm_authoritative_hybrid.programs import ACTION_ABI_HASH
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/r4_proposal_supervision.schema.json").read_text(encoding="utf-8"))
    assert schema["$defs"]["blueprint"]["properties"]["program_abi_version"]["const"] == 3
    assert schema["$defs"]["blueprint"]["properties"]["action_abi_ref"]["const"] == ACTION_ABI_HASH
    from cemm_authoritative_hybrid.r4_supervision import BlueprintAction, SourceAssignmentEntry
    assert BlueprintAction.create(action_index=3, action_type="project_variable", selector_handles=(0, 1)).selector_handles == (0, 1)
    assignment = SourceAssignmentEntry.create(source_unit_ref="unit:request", contribution_slot_ref="contribution_slot:request", contribution_kind="open_variable", assignment_kind="projection", target_action_index=3, target_role_ref=None, residual_kind=None, critical=True)
    assert assignment.assignment_kind == "projection" and assignment.target_role_ref is None


def _reviewed_blueprint(context):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.canonical import stable_ref
    from cemm_authoritative_hybrid.r4_expansion import ExpandedCase
    from cemm_authoritative_hybrid.r4_supervision import BlueprintAction, DerivationBlueprint, GroundedSelectorBinding, StructuralSelectorBinding, SourceAssignmentBlueprint, SourceAssignmentEntry, SourceSpan
    surface = "what is Bob?"
    expected = SemanticExpression.create(applications=(), root_refs=("projection:main",), query_projections=(QueryProjection("projection:main", "description", "entity:bob"),))
    case = object.__new__(ExpandedCase)
    for name, value in {"case_ref": stable_ref("expanded_case_v2", {"fixture": "projection"}),
        "surface_ref": stable_ref("reviewed_surface", {"surface": surface}), "surface": surface,
        "language": "en", "contract": SimpleNamespace(revision_pin=context.revision_pin, expected_expressions=(expected,))}.items():
        object.__setattr__(case, name, value)
    slot = next(s for s in context.query_projection_slots if s.requested_content == "description")
    designation = context.designation(slot.target_designation_slot_ref)
    mode = context.mode_slots[0]
    question = next(c for c in context.contribution_slots if c.kind == "discourse" and ("discourse", "question") in c.constraints)
    spans = {ref: (start, end) for ref, start, end in context.source_unit_spans}
    def grounded(handle, kind, component, semantic_kind, refs):
        return GroundedSelectorBinding.create(selector_handle=handle, selector_kind=kind,
            source_case_ref=case.case_ref, surface_ref=case.surface_ref, graph_component_ref=component.slot_ref,
            semantic_kind_ref=semantic_kind,
            spans=tuple(SourceSpan.create(surface_ref=case.surface_ref, start=spans[ref][0], end=spans[ref][1]) for ref in refs),
            source_selector_kind="source_unit", source_selector_ref=refs[0])
    selectors = (StructuralSelectorBinding.create(selector_handle=0, selector_kind="context_slot", value_ref=context.context_ref),
        grounded(1, "mode_slot", mode, "semantic_kind:discourse", question.source_unit_refs),
        grounded(2, "designation_slot", designation, "semantic_kind:entity", designation.source_unit_refs),
        StructuralSelectorBinding.create(selector_handle=3, selector_kind="local_node", value_ref="projection:main"),
        grounded(4, "query_projection_slot", slot, "semantic_kind:query_projection", slot.source_unit_refs))
    actions = tuple(BlueprintAction.create(action_index=i, action_type=kind, selector_handles=handles)
        for i, (kind, handles) in enumerate((("select_context", (0,)), ("select_mode", (1,)),
            ("select_designation", (2,)), ("project_variable", (3, 4)), ("complete_program", ()))))
    ownership = {ref: b.contribution_slot_ref for b in slot.bindings for ref in b.source_unit_refs if ref not in slot.orthographic_source_unit_refs}
    rows = []
    for ref in context.source_unit_refs:
        if ref in ownership:
            c = context.contribution(ownership[ref])
            rows.append(SourceAssignmentEntry.create(source_unit_ref=ref, contribution_slot_ref=c.slot_ref,
                contribution_kind=c.kind, assignment_kind="projection", target_action_index=3, target_role_ref=None,
                residual_kind=None, critical=c.kind != "qualifier"))
        elif ref in question.source_unit_refs:
            rows.append(SourceAssignmentEntry.create(source_unit_ref=ref, contribution_slot_ref=question.slot_ref,
                contribution_kind=question.kind, assignment_kind="discourse", target_action_index=1,
                target_role_ref=None, residual_kind=None, critical=False))
        else:
            r = context.residual_for_source(ref)
            rows.append(SourceAssignmentEntry.create(source_unit_ref=ref, contribution_slot_ref=r.residual_ref,
                contribution_kind=r.contribution_kind, assignment_kind="residual", target_action_index=None,
                target_role_ref=None, residual_kind=r.contribution_kind, critical=r.critical))
    blueprint = DerivationBlueprint.create(selector_bindings=selectors, actions=actions, root_local_refs=("projection:main",),
        expected_expression_ref=expected.expression_ref, source_assignment_blueprint=SourceAssignmentBlueprint.create(
            observed_source_unit_refs=context.source_unit_refs, assignments=tuple(rows)))
    return case, blueprint, expected


def test_projection_derivation_reviewed_blueprint_is_independent_and_rematched(runtime):
    from cemm_authoritative_hybrid.r4_derivation_compiler import ReviewedDerivationCompiler, DerivationCompilationError
    from cemm_authoritative_hybrid.r4_supervision import DerivationBlueprint
    index, context, _ = _candidate(runtime)
    case, blueprint, expected = _reviewed_blueprint(context)
    assert DerivationBlueprint.from_dict(blueprint.as_dict()) == blueprint
    result = ReviewedDerivationCompiler(runtime.authority, role_schema_index=index).compile(case=case, context=context, blueprint=blueprint)
    assert result.expression == expected
    assert CoverageVerifier(role_schema_index=index).verify(context, result.program).executable
    with pytest.raises(DerivationCompilationError):
        ReviewedDerivationCompiler(runtime.authority).compile(case=case, context=context, blueprint=blueprint)
    wire = blueprint.as_dict()
    wire["program_abi_version"] = 2
    with pytest.raises(ValueError):
        DerivationBlueprint.from_dict(wire)


@pytest.mark.parametrize("content", ("description", "definition"), ids=("description", "definition"))
def test_projection_derivation_single_content_diagnostic_uses_real_evaluation_and_response(runtime, content):
    from tests.test_foundation_projection_construction import _pack
    from tests.test_foundation_semantics import _static_composition_context
    from tests.test_foundation_description_builder import _description_expression, _seed_reviewed_generic_claim
    from tests.test_foundation_description_request_lineage import _situation
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    from cemm_authoritative_hybrid.r3_effects import NoEffectReceipt, NoEffectReason
    from cemm_authoritative_hybrid.r3_response import ResponseBuilder, ResponseMeaning
    from cemm_authoritative_hybrid.r3_artifacts import EvaluationBundle
    _seed_reviewed_generic_claim(runtime.stores, _description_expression("entity:bob"))
    # Only this reviewed diagnostic source has one content reading. Generic
    # public construction remains two readings regardless of stored facts.
    pack = _pack()
    pack["application_role_orders"]["content_target_projection"]["result"]["requested_contents"] = [content]
    builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, "what is Bob?")
    context = _with_slots(context, licensed_query_projection_slots(builder.role_schema_index, context))
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)
    batch = ExactProgramVerifier(authority=runtime.authority, role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
    meaning = batch.selected_meaning
    assert meaning is not None and meaning.expression.query_projections[0].requested_content == content
    situation = _situation(meaning.revision_pin)
    before = runtime.stores.revision_pin()
    evaluation = R3EvaluationOwner(runtime.authority, runtime.stores, RuntimeConfig.release()).evaluate(meaning, situation)
    assert EvaluationBundle.from_dict(evaluation.as_dict()) == evaluation
    query = evaluation.query_results[0]
    assert query.result_kind == "projection" and query.proof is None and query.bindings == ()
    signed = query.description_proof
    assert signed.description.request.source_expression_ref == meaning.expression.expression_ref
    assert signed.description.request.source_situation_ref == situation.situation_ref
    assert query.status.value == ("supported" if content == "description" else "unknown")
    assert signed.description.completeness.value == ("sufficient" if content == "description" else "missing")
    effect = NoEffectReceipt.create(reason=NoEffectReason.READ_ONLY, idempotency_key="effect:projection-diagnostic",
        journal_origin_ref="origin:projection-diagnostic", journal_preterminal_ref="planned:projection-diagnostic",
        decision_ref=evaluation.decision.decision_ref, verified_meaning_ref=meaning.verified_meaning_ref,
        expression_ref=meaning.expression.expression_ref, situation_ref=situation.situation_ref,
        program_ref=meaning.program_ref, learning_plan_ref=None, source_obligation_ref=None,
        proof_refs=evaluation.decision.proof_refs, blocker_refs=evaluation.decision.blocker_refs,
        input_revision_pin=before, output_revision_pin=replace(before, effect_revision=before.effect_revision + 1))
    response = ResponseBuilder().build(evaluation=evaluation, meaning=meaning, situation=situation,
        effect=effect, learning_plan=None, obligation=None)
    assert response.description_proof == signed and ResponseMeaning.from_dict(response.as_dict()) == response
    assert response.response_expression == (signed.description.answer_expression if content == "description" else meaning.expression)
    assert response.epistemic_status_ref == ("epistemic_status:attributed" if content == "description" else "epistemic_status:unknown")
    assert runtime.stores.revision_pin() == before


@pytest.mark.parametrize("language", ("en", "es"), ids=("en", "es"))
def test_projection_derivation_candidate_source_rows_emit_complete_alternatives(runtime, language):
    import json
    from pathlib import Path
    from tests.test_foundation_semantics import _static_composition_context
    pack = json.loads((Path(__file__).resolve().parents[1] / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
    assert "content_target_projection" in pack["application_role_orders"]
    row = pack["application_role_orders"]["content_target_projection"]
    assert row["result"]["requested_contents"] == ["description", "definition"]
    surfaces = (("a", "an", "the") if language == "en" else ("el", "la", "un", "una"))
    for article in ("", *surfaces):
        source = ("what is " if language == "en" else "qué es ") + (article + " " if article else "") + "Bob?"
        facts = (DesignationFact.create(surface="Bob", target_ref="entity:bob", language=language),)
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, source, facts=facts)
        assert len(context.query_projection_slots) == 2
        proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)
        batch = ExactProgramVerifier(authority=runtime.authority, role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
        assert batch.selected_meaning is None and len(batch.ambiguity_expression_refs) == 2
        assert all(r.accepted for r in batch.candidate_receipts) and not proposal.truncated


def test_projection_derivation_public_request_keeps_ambiguity_without_world_effect(runtime):
    before = runtime.stores.world.revision
    orientation, context = runtime.orient("session:projection-request", "What is Bob?")
    assert len(context.query_projection_slots) == 2
    proposal = runtime.proposal_model.propose(context)
    batch = runtime._owners["verification"].verify_candidates(proposal, context)
    assert batch.selected_meaning is None and len(batch.ambiguity_expression_refs) == 2
    assert all(r.accepted for r in batch.candidate_receipts)
    assert runtime.stores.world.revision == before


@pytest.mark.parametrize("mutation", ("drop", "pointer", "critical", "sources"), ids=("drop", "pointer", "critical", "sources"))
def test_projection_derivation_rehashed_port_ownership_is_exact(runtime, mutation):
    index, context, proposal = _candidate(runtime)
    original = proposal.candidates[0].program
    projection = next(a for a in original.actions if a.action_type == "project_variable")
    rows = list(original.source_assignments)
    pos = next(i for i, a in enumerate(rows) if a.assignment_kind == "projection")
    actions = original.actions
    if mutation == "drop":
        rows.pop(pos)
        values = {f.name: (tuple(rows) if f.name == "source_assignments" else getattr(original, f.name))
            for f in fields(original) if f.name not in {"program_ref", "abi_version"}}
        with pytest.raises(ValueError, match="cover source units exactly once"):
            SemanticSwitchProgram.create(**values)
        return
    elif mutation in {"pointer", "critical"}:
        values = {f.name: getattr(rows[pos], f.name) for f in fields(rows[pos]) if f.name != "assignment_ref"}
        if mutation == "pointer":
            values["contribution_slot_ref"] = next(a.contribution_slot_ref for a in rows if a.assignment_kind == "projection" and a.contribution_slot_ref != rows[pos].contribution_slot_ref)
        else:
            values["critical"] = not rows[pos].critical
        rows[pos] = SourceAssignment.create(**values)
    else:
        forged_action = ProgramAction.create(action_index=projection.action_index, action_type=projection.action_type,
            arguments=projection.arguments, source_unit_refs=projection.source_unit_refs[:-1])
        actions = tuple(forged_action if a is projection else a for a in actions)
        rows = [SourceAssignment.create(**{f.name: (forged_action.action_ref if f.name == "target_action_ref" else getattr(a, f.name))
            for f in fields(a) if f.name != "assignment_ref"}) if a.target_action_ref == projection.action_ref else a for a in rows]
    program = SemanticSwitchProgram.create(**{f.name: (tuple(rows) if f.name == "source_assignments" else actions if f.name == "actions" else getattr(original, f.name))
        for f in fields(original) if f.name not in {"program_ref", "abi_version"}})
    assert SemanticSwitchProgram.from_dict(program.as_dict()) == program
    assert not CoverageVerifier(role_schema_index=index).verify(context, program).executable
    assert isinstance(SemanticExpressionCompiler(role_schema_index=index).compile(program, context), CompilationFailure)
    assert reconstruct_expected_expression(program, context, authority=runtime.authority, role_schema_index=index) is None


@pytest.mark.parametrize("mutation", ("target", "content", "grounding", "assignment", "root"), ids=("target", "content", "grounding", "assignment", "root"))
def test_projection_derivation_rehashed_compilation_claim_is_not_authority(runtime, mutation):
    from cemm_authoritative_hybrid.expressions import CompilationProof, TranslationRow
    index, context, proposal = _candidate(runtime)
    program = proposal.candidates[0].program
    compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, context)
    expression = compiled.expression
    proof_values = {f.name: getattr(compiled.proof, f.name) for f in fields(compiled.proof) if f.name != "proof_ref"}
    if mutation in {"target", "content"}:
        request = expression.query_projections[0]
        expression = SemanticExpression.create(applications=(), root_refs=expression.root_refs,
            query_projections=(QueryProjection(request.projection_ref,
                ("definition" if request.requested_content == "description" else "description") if mutation == "content" else request.requested_content,
                "entity:alice" if mutation == "target" else request.target_ref),))
        proof_values["expression_ref"] = expression.expression_ref
    elif mutation == "grounding":
        proof_values["grounding_refs"] = compiled.proof.grounding_refs[:-1]
    elif mutation == "assignment":
        proof_values["assignment_translations"] = compiled.proof.assignment_translations[:-1]
    else:
        row = compiled.proof.root_translations[0]
        proof_values["root_translations"] = (TranslationRow(row.source_ref, row.disposition, ("projection:forged",)),)
    proof = CompilationProof.create(**proof_values)
    assert CompilationProof.from_dict(proof.as_dict()) == proof
    assert _proof_errors(program, context, expression, proof, authority=runtime.authority, role_schema_index=index)


@pytest.mark.parametrize("mutation", ("honest", "wrong-role", "extra-key", "wrong-primary", "primitive-ref", "provenance"), ids=("honest", "wrong-role", "extra-key", "wrong-primary", "primitive-ref", "provenance"))
def test_projection_article_metadata_keeps_exact_nominal_signature(runtime, mutation):
    from tests.test_foundation_projection_construction import _pack
    from tests.test_foundation_semantics import _static_composition_context
    from cemm_authoritative_hybrid.proposal_context import ContributionSlot, ProposalContext
    from cemm_authoritative_hybrid.verifier_reconstruction import _nominal_form_feature
    _, context = _static_composition_context(runtime.authority, runtime.stores, _pack(), "Alice is a mother.")
    row = next(c for c in context.contribution_slots if c.kind == "qualifier" and ("determiner", "determiner") in c.constraints)
    values = {f.name: getattr(row, f.name) for f in fields(row) if f.name != "slot_ref"}
    if mutation == "wrong-role":
        values["constraints"] = (("determiner", "determiner"), ("construction_role", "forged_article"))
    elif mutation == "extra-key":
        values["constraints"] = (*row.constraints, ("opaque", "forged"))
    elif mutation == "wrong-primary":
        values["constraints"] = (("determiner", "unlicensed"), ("construction_role", "query_target_article"))
    elif mutation == "primitive-ref":
        values["contribution_ref"] = "form_contribution:forged"
    elif mutation == "provenance":
        values["provenance_refs"] = ("unit:forged",)
    forged = ContributionSlot.create(**values)
    context_values = {f.name: getattr(context, f.name) for f in fields(context) if f.init and f.name not in {"context_ref", "abi_version"}}
    context_values["contribution_slots"] = tuple(forged if c is row else c for c in context.contribution_slots)
    context = ProposalContext.create(**context_values)
    assert ProposalContext.from_dict(context.as_dict()) == context
    assert _nominal_form_feature(context, row.source_unit_refs[0], "qualifier", "determiner") is (mutation == "honest")


@pytest.mark.parametrize("mutation", ("binder-ports", "request-ports", "anchor-ports", "anchor-ref", "anchor-provenance", "anchor-frame"), ids=("binder-ports", "request-ports", "anchor-ports", "anchor-ref", "anchor-provenance", "anchor-frame"))
def test_projection_derivation_rehashed_contribution_contract_is_not_authority(runtime, mutation):
    from cemm_authoritative_hybrid.canonical import stable_ref
    from cemm_authoritative_hybrid.proposal_context import ContributionSlot, ProposalContext
    index, context, _ = _candidate(runtime)
    kind = "binder" if mutation == "binder-ports" else "open_variable" if mutation == "request-ports" else "anchor"
    row = next(c for c in context.contribution_slots if c.kind == kind)
    values = {f.name: getattr(row, f.name) for f in fields(row) if f.name != "slot_ref"}
    if mutation.endswith("ports"):
        values.update(input_ports=("role:forged_input",), output_ports=("role:forged_output",))
    elif mutation == "anchor-ref":
        values["contribution_ref"] = "contribution:forged"
    elif mutation == "anchor-provenance":
        values["provenance_refs"] = ("unit:forged",)
    else:
        values["constraints"] = (("frame_ref", "frame:event:greeting"),)
    forged = ContributionSlot.create(**values)
    slots = []
    for slot in context.query_projection_slots:
        bindings = tuple(replace(b, contribution_slot_ref=forged.slot_ref) if b.contribution_slot_ref == row.slot_ref else b for b in slot.bindings)
        match_ref = stable_ref("reviewed_query_projection_match", {
            "index": slot.index_ref, "schema": slot.schema_ref, "requested_content": slot.requested_content,
            "target_designation_slot_ref": slot.target_designation_slot_ref,
            "bindings": [(b.port, b.contribution_slot_ref, b.source_unit_refs) for b in bindings],
            "source_unit_spans": slot.source_unit_spans, "orthographic_source_unit_refs": slot.orthographic_source_unit_refs})
        slot_values = {f.name: getattr(slot, f.name) for f in fields(slot) if f.name != "slot_ref"}
        slot_values.update(bindings=bindings, match_ref=match_ref, provenance_refs=tuple(dict.fromkeys(
            (slot.index_ref, slot.schema_ref, match_ref, slot.target_designation_slot_ref, *(b.contribution_slot_ref for b in bindings)))))
        slots.append(QueryProjectionSlot.create(**slot_values))
    context_values = {f.name: getattr(context, f.name) for f in fields(context) if f.init and f.name not in {"context_ref", "abi_version"}}
    context_values.update(contribution_slots=tuple(forged if c is row else c for c in context.contribution_slots), query_projection_slots=tuple(slots))
    context = ProposalContext.create(**context_values)
    assert ProposalContext.from_dict(context.as_dict()) == context
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)
    assert len(proposal.candidates) == 2
    for candidate in proposal.candidates:
        program = candidate.program
        assert not CoverageVerifier(role_schema_index=index).verify(context, program).executable
        assert isinstance(SemanticExpressionCompiler(role_schema_index=index).compile(program, context), CompilationFailure)
        assert reconstruct_expected_expression(program, context, authority=runtime.authority, role_schema_index=index) is None
    batch = ExactProgramVerifier(authority=runtime.authority, role_schema_index=index).verify_candidates(proposal, context)
    assert not any(r.accepted for r in batch.candidate_receipts)
    assert batch.selected_meaning is None


@pytest.mark.parametrize("target", ("entity:bob", "concept:mother", "participant:user"), ids=("entity", "concept", "participant"))
def test_projection_derivation_authentic_profile_ports_preserve_alias_targets(runtime, target):
    from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
    from cemm_authoritative_hybrid.contributions import ContributionExpander
    facts = (DesignationFact.create(surface="vel nora", target_ref=target, language="en"),)
    index, context, proposal = _candidate(runtime, "what is vel nora?", facts=facts)
    assert len(proposal.candidates) == 2 and not proposal.truncated
    profiles = SemanticAffordanceIndex(runtime.authority, RuntimeConfig.release()).for_target(target)
    source_refs = context.designation(context.query_projection_slots[0].target_designation_slot_ref).source_unit_refs
    expected = tuple(ContributionExpander._make_contribution(kind="anchor", source_unit_refs=source_refs,
        target_ref=target, input_ports=p.input_ports, output_ports=p.output_ports, frame_ref=p.frame_ref)
        for p in profiles if "anchor" in p.contribution_kinds)
    for slot in context.query_projection_slots:
        anchor = context.contribution(next(b.contribution_slot_ref for b in slot.bindings if b.port == "target"))
        assert any((anchor.contribution_ref, anchor.input_ports, anchor.output_ports, anchor.constraints) ==
            (c.contribution_ref, c.input_ports, c.output_ports, c.constraints) for c in expected)
    batch = ExactProgramVerifier(authority=runtime.authority, role_schema_index=index).verify_candidates(proposal, context)
    assert all(r.accepted for r in batch.candidate_receipts)
    assert batch.selected_meaning is None and len(batch.ambiguity_expression_refs) == 2


def test_projection_derivation_cached_affordance_owner_cannot_be_replaced(runtime):
    from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
    index, context, proposal = _candidate(runtime)
    replacement = SemanticAffordanceIndex(index._activation_authority, index._activation_config)
    forged_index = replace(index, _activation_affordances=replacement)
    assert not forged_index.identity_is_current
    program = proposal.candidates[0].program
    assert not CoverageVerifier(role_schema_index=forged_index).verify(context, program).executable
    assert isinstance(SemanticExpressionCompiler(role_schema_index=forged_index).compile(program, context), CompilationFailure)
    assert reconstruct_expected_expression(program, context, role_schema_index=forged_index) is None


@pytest.mark.parametrize("field,expected", (("switch_program", PROGRAM_ABI_VERSION), ("coverage", COVERAGE_ABI_VERSION)), ids=("program", "coverage"))
def test_projection_derivation_registry_agrees_with_active_codecs(field, expected):
    assert getattr(RuntimeConfig.release().abis, field) == expected


def test_projection_derivation_counterfeit_authority_equality_cannot_license_ports(runtime):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.canonical import stable_ref
    from cemm_authoritative_hybrid.contributions import ContributionExpander
    from cemm_authoritative_hybrid.proposal_context import ContributionSlot, ProposalContext
    index, context, _ = _candidate(runtime)
    class CounterfeitAuthority:
        def __eq__(self, other):
            return True
        def __getattr__(self, name):
            return getattr(runtime.authority, name)
        def reviewed_frames_for_target(self, target):
            if target == "entity:bob":
                return (SimpleNamespace(frame_ref="frame:event:greeting", target_ref=target,
                    contribution_kinds=("anchor",), input_ports=("role:forged_input",),
                    output_ports=("role:forged_output",), role_candidates=("role:forged_input",)),)
            return runtime.authority.reviewed_frames_for_target(target)
    counterfeit = CounterfeitAuthority()
    forged_index = replace(index, _activation_authority=counterfeit)
    forged_index._activation_affordances._authority = counterfeit
    row = next(c for c in context.contribution_slots if c.kind == "anchor")
    profile = forged_index._activation_affordances.for_target(row.target_ref)[0]
    generated = ContributionExpander._make_contribution(kind="anchor", source_unit_refs=row.source_unit_refs,
        target_ref=row.target_ref, input_ports=profile.input_ports, output_ports=profile.output_ports, frame_ref=profile.frame_ref)
    forged = ContributionSlot.create(**{f.name: (getattr(generated, f.name) if hasattr(generated, f.name) else getattr(row, f.name))
        for f in fields(row) if f.name != "slot_ref"})
    slots = []
    for slot in context.query_projection_slots:
        bindings = tuple(replace(b, contribution_slot_ref=forged.slot_ref) if b.contribution_slot_ref == row.slot_ref else b for b in slot.bindings)
        match_ref = stable_ref("reviewed_query_projection_match", {
            "index": slot.index_ref, "schema": slot.schema_ref, "requested_content": slot.requested_content,
            "target_designation_slot_ref": slot.target_designation_slot_ref,
            "bindings": [(b.port, b.contribution_slot_ref, b.source_unit_refs) for b in bindings],
            "source_unit_spans": slot.source_unit_spans, "orthographic_source_unit_refs": slot.orthographic_source_unit_refs})
        values = {f.name: getattr(slot, f.name) for f in fields(slot) if f.name != "slot_ref"}
        values.update(bindings=bindings, match_ref=match_ref, provenance_refs=tuple(dict.fromkeys(
            (slot.index_ref, slot.schema_ref, match_ref, slot.target_designation_slot_ref, *(b.contribution_slot_ref for b in bindings)))))
        slots.append(QueryProjectionSlot.create(**values))
    values = {f.name: getattr(context, f.name) for f in fields(context) if f.init and f.name not in {"context_ref", "abi_version"}}
    values.update(contribution_slots=tuple(forged if c is row else c for c in context.contribution_slots), query_projection_slots=tuple(slots))
    context = ProposalContext.create(**values)
    assert ProposalContext.from_dict(context.as_dict()) == context
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(context)
    assert len(proposal.candidates) == 2
    for candidate in proposal.candidates:
        assert not CoverageVerifier(role_schema_index=forged_index).verify(context, candidate.program).executable
        assert isinstance(SemanticExpressionCompiler(role_schema_index=forged_index).compile(candidate.program, context), CompilationFailure)
        assert reconstruct_expected_expression(candidate.program, context, role_schema_index=forged_index) is None
    assert not forged_index.identity_is_current
    batch = ExactProgramVerifier(authority=runtime.authority, role_schema_index=forged_index).verify_candidates(proposal, context)
    assert not any(r.accepted for r in batch.candidate_receipts)


@pytest.mark.parametrize("boundary", ("factory-authority", "factory-config", "activation", "exact-sinks"), ids=("factory-authority", "factory-config", "activation", "exact-sinks"))
def test_projection_derivation_activation_requires_actual_exact_owners(runtime, boundary):
    from copy import copy
    from types import SimpleNamespace
    from tests.test_foundation_projection_construction import _pack
    from cemm_authoritative_hybrid.role_schemas import ReviewedRoleSchemaIndex
    class CounterfeitOwner:
        def __init__(self, actual):
            self.actual = actual
        def __getattr__(self, name):
            return getattr(self.actual, name)
        def reviewed_frames_for_target(self, target):
            return (SimpleNamespace(frame_ref="frame:event:greeting", target_ref=target,
                contribution_kinds=("anchor",), input_ports=("role:forged_input",),
                output_ports=("role:forged_output",), role_candidates=("role:forged_input",)),)
    config = RuntimeConfig.release()
    if boundary.startswith("factory"):
        authority = CounterfeitOwner(runtime.authority) if boundary == "factory-authority" else runtime.authority
        config = CounterfeitOwner(config) if boundary == "factory-config" else config
        with pytest.raises(TypeError):
            ReviewedRoleSchemaIndex.from_pack(_pack(), authority, config)
        return
    index, context, proposal = _candidate(runtime)
    other_authority = copy(runtime.authority)
    assert other_authority is not runtime.authority
    assert (other_authority.generation, other_authority.content_hash) == (runtime.authority.generation, runtime.authority.content_hash)
    if boundary == "activation":
        with pytest.raises(ValueError, match="authority or activation"):
            index.validate_activation(other_authority, _pack())
    else:
        program = proposal.candidates[0].program
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, context)
        assert reconstruct_expected_expression(program, context, authority=other_authority, role_schema_index=index) is None
        assert _proof_errors(program, context, compiled.expression, compiled.proof, authority=other_authority, role_schema_index=index)
        batch = ExactProgramVerifier(authority=other_authority, role_schema_index=index).verify_candidates(proposal, context)
        assert not any(r.accepted for r in batch.candidate_receipts)
