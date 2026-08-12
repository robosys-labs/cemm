"""Behavioral R4 closeout regressions over the reviewed corpus.

These tests keep the independent expected-contract compiler total over the
reviewed scenario source without allowing runtime/proposer outputs to influence
expectations.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy

import pytest

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.expressions import GroundedReference, LiteralValue
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContract,
    ExpectedCycleContractCompiler,
    ExpectedOutcomeKind,
    ExpressionRelation,
)
from cemm_authoritative_hybrid.r4_episodes import (
    AuthenticEpisodeBuilder,
    PublicRuntimeEpisodeOwner,
)
from cemm_authoritative_hybrid.r4_environment import build_environment
from cemm_authoritative_hybrid.r4_expansion import CaseExpander, ExpandedCase
from cemm_authoritative_hybrid.r4_pipeline import load_reviewed_scenarios

__cemm_test_inventory__ = {'tests/test_r4_closeout_regressions.py::test_every_reviewed_surface_compiles_and_round_trips_canonically': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:r4-reviewed-corpus-compiles-canonically',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R4-Closeout',
                                                                                                             'owner_ref': 'expected-contract',
                                                                                                             'source_ast_sha256': '41711e3c829cc11ddcbdab0180bf583217b1e75c75f023e9a569e40c3ddef351'},
 'tests/test_r4_closeout_regressions.py::test_external_sensor_provenance_is_not_mistaken_for_active_adapter_authority': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-sensor-provenance-distinct-from-active-adapter-authority',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4-Closeout',
                                                                                                                         'owner_ref': 'expected-contract',
                                                                                                                         'source_ast_sha256': 'fe5da5366cc3278841cc16761106111d40bb670bc3a056e1637b1c895ae5d38b'},
 'tests/test_r4_closeout_regressions.py::test_learning_reported_speech_and_effect_contracts_have_connected_compatible_topology': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:r4-reviewed-contract-topology-is-connected-and-compatible',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'R4-Closeout',
                                                                                                                                  'owner_ref': 'expected-contract',
                                                                                                                                  'source_ast_sha256': '898793eb96c28d0012ba8494bf1d590b4a71e38c071ba006f6d5b6841b972936'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_designation_aliases_match_authentic_r3_cycles': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:r4-designation-aliases-match-authentic-r3-cycles',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R4-Authentic-Designation-Tranche',
                                                                                                        'owner_ref': 'expected-contract',
                                                                                                        'source_ast_sha256': '5c3bd3eeceb770d31465b913495276d876c5c1df4ff69e84f4679d69b88d1394'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_greeting_and_farewell_surfaces_match_authentic_r3_cycles': {'activation_phase': 'R4',
                                                                                                                   'assertion_ref': 'assertion:r4-designation-events-match-authentic-r3-cycles',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R4-Designation-Event-Tranche',
                                                                                                                   'owner_ref': 'expected-contract',
                                                                                                                   'source_ast_sha256': 'b57ad5da997eea7893fbf073e2a792009287c65c944b2dca09482da882264d8f'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_scenario_source_matches_deterministic_generator': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-reviewed-scenario-source-matches-generator',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4-Designation-Event-Tranche',
                                                                                                          'owner_ref': 'expected-contract',
                                                                                                          'source_ast_sha256': 'ae45385ae4668fca755ff60a9ab2d4cc915eb8c5b87b84b21c525cab2bac7e54'},
 'tests/test_r4_closeout_regressions.py::test_singleton_polysemy_is_not_fabricated_as_ambiguity': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:r4-singleton-polysemy-is-not-fabricated-ambiguity',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R4-Closeout',
                                                                                                   'owner_ref': 'expected-contract',
                                                                                                   'source_ast_sha256': 'e3537192e23a8bac5019da33aff92a490169470396b3cfa0b53a96dee40f7f88'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-book]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-book',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                   'owner_ref': 'expected-contract',
                                                                                                                                   'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-server]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-server',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                     'owner_ref': 'expected-contract',
                                                                                                                                     'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-digital-agent]': {'activation_phase': 'R4',
                                                                                                                                           'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-definition-digital-agent',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                           'owner_ref': 'expected-contract',
                                                                                                                                           'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-mother]': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-definition-mother',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                    'owner_ref': 'expected-contract',
                                                                                                                                    'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-partner]': {'activation_phase': 'R4',
                                                                                                                                      'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-partner',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                      'owner_ref': 'expected-contract',
                                                                                                                                      'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-progenitor]': {'activation_phase': 'R4',
                                                                                                                                         'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-progenitor',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                         'owner_ref': 'expected-contract',
                                                                                                                                         'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-lamp]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-lamp',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                   'owner_ref': 'expected-contract',
                                                                                                                                   'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[relation-likes]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-likes',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                 'owner_ref': 'expected-contract',
                                                                                                                                 'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[relation-owns]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-owns',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                'owner_ref': 'expected-contract',
                                                                                                                                'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[state-availability]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-state-availability',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                     'owner_ref': 'expected-contract',
                                                                                                                                     'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[state-power]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-state-power',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                              'owner_ref': 'expected-contract',
                                                                                                                              'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[negation]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-reviewed-recursive-scope-negation',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                    'owner_ref': 'expected-contract',
                                                                                                                    'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[modality]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-reviewed-recursive-scope-modality',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                    'owner_ref': 'expected-contract',
                                                                                                                    'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[reported-speech]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:r4-reviewed-recursive-scope-reported-speech',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                           'owner_ref': 'expected-contract',
                                                                                                                           'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[learning-security]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:r4-reviewed-recursive-scope-learning-security',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                             'owner_ref': 'expected-contract',
                                                                                                                             'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[recursive-family-proof]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:r4-reviewed-recursive-scope-recursive-family-proof',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                  'owner_ref': 'expected-contract',
                                                                                                                                  'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[participant-reference]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:r4-reviewed-recursive-scope-participant-reference',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                 'owner_ref': 'expected-contract',
                                                                                                                                 'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[contradiction]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-reviewed-recursive-scope-contradiction',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                         'owner_ref': 'expected-contract',
                                                                                                                         'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_every_reviewed_scenario_matches_authentic_cycles': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:r4-every-reviewed-scenario-matches-authentic-cycles',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                  'owner_ref': 'expected-contract',
                                                                                                  'source_ast_sha256': '5b7f197deb6f81e6721ef3b68327997f6a1a23b4c65721001994dfd915da1810'},
 'tests/test_r4_closeout_regressions.py::test_bare_effect_designation_does_not_authorize_request': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-bare-effect-is-not-request', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '5684216533506d4a9348181611b8264bb9181a275b0ecb76dbd10b4c265ca8c2'},
 'tests/test_r4_closeout_regressions.py::test_prospective_alias_teaching_uses_definition_evidence_without_prelinking': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-prospective-alias-is-not-prelinked', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '47042d260ee6dcd69b91539e18e0d0b8078e13ff37001a43103351d1f5c70804'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_sensor_and_operation_evidence_uses_authentic_extra_items': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-authentic-extra-evidence-items', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '99eadf970ca3ed935cbcfd4750925cce6afed8d471e0f5aed3a8805e9440b40c'},
 'tests/test_r4_closeout_regressions.py::test_reported_speech_relational_content_composes_recursively': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-reported-relation-composes', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': 'eea64d05bb84565a6a4a90bd5d4626355f87af58812dd48d68e688214806634f'},
 'tests/test_r4_closeout_regressions.py::test_reported_speech_event_content_reuses_speaker_by_reviewed_coreference': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-reported-event-coreference', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': 'f1723ebed92d745bc581ebcced0413d8e2992741d75fd4528bced7709802af8b'},
 'tests/test_r4_closeout_regressions.py::test_singleton_polysemy_is_observed_designation_evidence': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-singleton-polysemy-is-observed', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '883c11e05eede9b8ee1d714de58d1acb8fe985cf0304a00514a95f070855f115'},
 'tests/test_r4_closeout_regressions.py::test_question_mark_projects_state_interrogative_to_query_mode': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-question-marker-projects-query', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '2e6e556e03984adbe84a9df71ddf2f29af3beb8451b49202eb0d5617af29ecd3'},
 'tests/test_r4_closeout_regressions.py::test_realization_equivalence_uses_exact_semantic_contracts[state-0202]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-realization-exact-0202', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '4dd7d577bcf55a94920893bcf9c818261fca71084dc89d94aa6e78265d2617d5'},
 'tests/test_r4_closeout_regressions.py::test_realization_equivalence_uses_exact_semantic_contracts[state-0203]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-realization-exact-0203', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '4dd7d577bcf55a94920893bcf9c818261fca71084dc89d94aa6e78265d2617d5'},
 'tests/test_r4_closeout_regressions.py::test_realization_equivalence_uses_exact_semantic_contracts[state-0207]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-realization-exact-0207', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '4dd7d577bcf55a94920893bcf9c818261fca71084dc89d94aa6e78265d2617d5'},
 'tests/test_r4_closeout_regressions.py::test_realization_equivalence_uses_exact_semantic_contracts[state-0209]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-realization-exact-0209', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '4dd7d577bcf55a94920893bcf9c818261fca71084dc89d94aa6e78265d2617d5'},
 'tests/test_r4_closeout_regressions.py::test_realization_equivalence_uses_exact_semantic_contracts[state-0210]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-realization-exact-0210', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '4dd7d577bcf55a94920893bcf9c818261fca71084dc89d94aa6e78265d2617d5'},
 'tests/test_r4_closeout_regressions.py::test_capability_questions_consume_all_reviewed_mode_evidence[query]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-mode-query', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '283ced6d64840cfe912be74425c8760ca058399b0932aacf55ca4ecae288551e'},
 'tests/test_r4_closeout_regressions.py::test_capability_questions_consume_all_reviewed_mode_evidence[respond]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-mode-respond', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '283ced6d64840cfe912be74425c8760ca058399b0932aacf55ca4ecae288551e'},
 'tests/test_r4_closeout_regressions.py::test_capability_questions_consume_all_reviewed_mode_evidence[learn-alias]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-mode-learn-alias', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '283ced6d64840cfe912be74425c8760ca058399b0932aacf55ca4ecae288551e'},
 'tests/test_r4_closeout_regressions.py::test_capability_questions_consume_all_reviewed_mode_evidence[set-state]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-mode-set-state', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '283ced6d64840cfe912be74425c8760ca058399b0932aacf55ca4ecae288551e'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_capability_queries_use_explicit_designations[query]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-designation-query', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '80e9f68aa6efa4708b7bc198d86f8df19a28212a875a4bb2b9e384008c364c8d'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_capability_queries_use_explicit_designations[respond]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-designation-respond', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '80e9f68aa6efa4708b7bc198d86f8df19a28212a875a4bb2b9e384008c364c8d'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_capability_queries_use_explicit_designations[learn-alias]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-designation-learn-alias', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '80e9f68aa6efa4708b7bc198d86f8df19a28212a875a4bb2b9e384008c364c8d'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_capability_queries_use_explicit_designations[set-state]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-capability-designation-set-state', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': '80e9f68aa6efa4708b7bc198d86f8df19a28212a875a4bb2b9e384008c364c8d'},
 'tests/test_r4_closeout_regressions.py::test_fail_closed_boundary_families_match_authentic_cycles[adversarial]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-boundary-adversarial', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': 'ac5e32cc4b9c31d33617c8c61892166e6a2af02085e0170a51218922023ae59c'},
 'tests/test_r4_closeout_regressions.py::test_fail_closed_boundary_families_match_authentic_cycles[gaps]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-boundary-gaps', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': 'ac5e32cc4b9c31d33617c8c61892166e6a2af02085e0170a51218922023ae59c'},
 'tests/test_r4_closeout_regressions.py::test_fail_closed_boundary_families_match_authentic_cycles[restart]': {'activation_phase': 'R4', 'assertion_ref': 'assertion:r4-boundary-restart', 'diagnostic_role': 'admission_only', 'introduced_by_task': 'R4-Final-Admission-Closeout', 'source_ast_sha256': 'ac5e32cc4b9c31d33617c8c61892166e6a2af02085e0170a51218922023ae59c'}}

ROOT = Path(__file__).parents[1]
SCENARIOS = ROOT / "data" / "scenarios" / "use_cases.jsonl"


def test_reviewed_scenario_source_matches_deterministic_generator() -> None:
    generate_all = runpy.run_path(
        str(ROOT / "scripts" / "generate_scenarios.py")
    )["generate_all"]
    generated = generate_all()
    expected = (
        "\n".join(
            json.dumps(
                row,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            for row in generated
        )
        + "\n"
    ).encode("utf-8")
    assert SCENARIOS.read_bytes() == expected


def _expanded_cases() -> tuple[ExpandedCase, ...]:
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    compiler = ExpectedCycleContractCompiler(authority, abi_registry_ref="abi:r4-closeout")
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, "model:r4-closeout")
    expander = CaseExpander(compiler)
    rows: list[ExpandedCase] = []
    for scenario in load_reviewed_scenarios(SCENARIOS):
        environments = scenario.metadata.get("environments", ({},))
        rows.extend(expander.expand(scenario, revision_pin=pin, environments=environments))
    return tuple(rows)


def _authentic_episodes_for_scenario(
    scenario_ref: str,
    store_root: Path,
):
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, model_identity)
    compiler = ExpectedCycleContractCompiler(
        authority,
        abi_registry_ref="abi:r4-nominal-state-relation-canary",
    )
    scenario = next(
        row
        for row in load_reviewed_scenarios(SCENARIOS)
        if row.scenario_ref == scenario_ref
    )
    cases = CaseExpander(compiler).expand(
        scenario,
        revision_pin=pin,
        environments=scenario.metadata.get("environments", ({},)),
    )
    runtimes = []

    def runtime_factory(_case: ExpandedCase):
        runtime = load_runtime(
            ROOT,
            profile="development",
            store_path=store_root / f"runtime-{len(runtimes):02d}",
        )
        runtimes.append(runtime)
        return runtime

    try:
        return AuthenticEpisodeBuilder(
            PublicRuntimeEpisodeOwner(runtime_factory)
        ).build_many(cases)
    finally:
        for runtime in reversed(runtimes):
            runtime.stores.close()


def test_every_reviewed_scenario_matches_authentic_cycles(tmp_path: Path) -> None:
    cases = _expanded_cases()
    environment = build_environment(ROOT, tmp_path)
    builder = AuthenticEpisodeBuilder(
        PublicRuntimeEpisodeOwner(
            environment["runtime_factory"],
            restart_executor=environment["restart_executor"],
        )
    )
    try:
        episodes = builder.build_many(cases)
    finally:
        environment["close"]()

    assert [
        (
            row.expanded_case.scenario_ref,
            row.expanded_case.surface,
            row.comparison.mismatch_codes,
        )
        for row in episodes
        if not row.comparison.passed
    ] == []


@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:designation_definition-0003",
        "scenario:designation_definition-0004",
        "scenario:designation_definition-0006",
        "scenario:designation_definition-0010",
        "scenario:designation_definition-0012",
        "scenario:designation_definition-0013",
        "scenario:designation_definition-0014",
        "scenario:reordered_constructions-0021",
        "scenario:reordered_constructions-0022",
        "scenario:temporal_state-0089",
        "scenario:temporal_state-0091",
    ),
    ids=(
        "designation-book",
        "designation-server",
        "definition-digital-agent",
        "definition-mother",
        "designation-partner",
        "designation-progenitor",
        "designation-lamp",
        "relation-likes",
        "relation-owns",
        "state-availability",
        "state-power",
    ),
)
def test_reviewed_nominal_state_relation_families_match_authentic_cycles(
    scenario_ref: str,
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(scenario_ref, tmp_path)

    assert episodes
    assert all(row.comparison.passed for row in episodes)


@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:realization_equivalence-0202",
        "scenario:realization_equivalence-0203",
        "scenario:realization_equivalence-0207",
        "scenario:realization_equivalence-0209",
        "scenario:realization_equivalence-0210",
    ),
    ids=("state-0202", "state-0203", "state-0207", "state-0209", "state-0210"),
)
def test_realization_equivalence_uses_exact_semantic_contracts(
    scenario_ref: str,
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(scenario_ref, tmp_path)

    assert len(episodes) == 2
    assert all(row.expected_contract.expected_expressions for row in episodes)
    assert all(row.expected_contract.expected_mode.value == "QUERY" for row in episodes)
    assert all(row.comparison.passed for row in episodes)
    assert (
        episodes[0].observed_cycle.evaluation.expression.as_dict()
        == episodes[1].observed_cycle.evaluation.expression.as_dict()
    )


@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:capability_policy_adapter_effect-0131",
        "scenario:capability_policy_adapter_effect-0132",
        "scenario:capability_policy_adapter_effect-0133",
        "scenario:capability_policy_adapter_effect-0134",
    ),
    ids=("query", "respond", "learn-alias", "set-state"),
)
def test_capability_questions_consume_all_reviewed_mode_evidence(
    scenario_ref: str,
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(scenario_ref, tmp_path)

    assert episodes
    assert all(row.comparison.passed for row in episodes)


def test_bare_effect_designation_does_not_authorize_request(tmp_path: Path) -> None:
    episodes = _authentic_episodes_for_scenario(
        "scenario:polysemy-0033", tmp_path
    )

    assert len(episodes) == 2
    assert all(row.observed_cycle.orientation.mode.value == "OBSERVE" for row in episodes)
    assert all(row.comparison.passed for row in episodes)


@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:negation_scope-0047",
        "scenario:modality-0037",
        "scenario:reported_speech-0085",
        "scenario:learning_security-0119",
        "scenario:recursive_family_proof-0059",
        "scenario:participant_reference-0078",
        "scenario:contradiction-0143",
    ),
    ids=(
        "negation",
        "modality",
        "reported-speech",
        "learning-security",
        "recursive-family-proof",
        "participant-reference",
        "contradiction",
    ),
)
def test_reviewed_recursive_scope_families_match_authentic_cycles(
    scenario_ref: str,
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(scenario_ref, tmp_path)

    assert episodes
    assert all(row.comparison.passed for row in episodes)
    if scenario_ref == "scenario:recursive_family_proof-0059":
        assert all(
            row.observed_cycle.evaluation is not None
            and row.observed_cycle.evaluation.query_results
            and "rule:mother-in-law-implies-partner-exists"
            in row.observed_cycle.evaluation.query_results[0].retrieval_refs
            for row in episodes
        )


def test_every_reviewed_surface_compiles_and_round_trips_canonically() -> None:
    scenarios = load_reviewed_scenarios(SCENARIOS)
    cases = _expanded_cases()
    assert len(scenarios) == 210
    assert len(cases) == sum(len(row.surface_examples) for row in scenarios)
    assert len(cases) == 400
    assert all(ExpandedCase.from_dict(row.as_dict()) == row for row in cases)
    assert all(
        ExpectedCycleContract.from_dict(row.contract.as_dict()) == row.contract
        for row in cases
    )


def test_reviewed_greeting_and_farewell_surfaces_match_authentic_r3_cycles(
    tmp_path: Path,
) -> None:
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, model_identity)
    compiler = ExpectedCycleContractCompiler(
        authority, abi_registry_ref="abi:r4-designation-event"
    )
    expander = CaseExpander(compiler)
    selected = {
        row.scenario_ref: row
        for row in load_reviewed_scenarios(SCENARIOS)
        if row.scenario_ref
        in {
            "scenario:designation_definition-0001",
            "scenario:designation_definition-0002",
        }
    }
    assert set(selected) == {
        "scenario:designation_definition-0001",
        "scenario:designation_definition-0002",
    }
    expected_targets = {
        "scenario:designation_definition-0001": "event:greeting",
        "scenario:designation_definition-0002": "event:farewell",
    }
    for scenario_ref, scenario in selected.items():
        assert tuple(row.kind for row in scenario.assertions) == (
            "event",
            "mode",
            "decision",
            "no_effect",
            "response",
        )
        assert scenario.assertions[0].fields["event_type"] == expected_targets[scenario_ref]

    def runtime_factory(case: ExpandedCase):
        store_name = stable_ref("r4_designation_event_store", case.case_ref).split(
            ":", 1
        )[1]
        return load_runtime(
            ROOT,
            profile="development",
            store_path=tmp_path / f"{store_name}.db",
        )

    builder = AuthenticEpisodeBuilder(PublicRuntimeEpisodeOwner(runtime_factory))
    episodes = tuple(
        builder.build(case)
        for scenario in selected.values()
        for case in expander.expand(scenario, revision_pin=pin)
    )
    assert len(episodes) == 5
    assert all(row.comparison.passed for row in episodes)
    for episode in episodes:
        expected = episode.expected_contract.expected_expressions
        meaning = episode.observed_cycle.verification.selected_meaning
        candidate_ref = episode.observed_cycle.verification.selected_candidate_ref
        assert len(expected) == 1
        assert meaning is not None
        assert candidate_ref is not None
        candidate = episode.observed_cycle.proposal.candidate_by_ref(candidate_ref)
        assert tuple(
            action.action_type
            for action in candidate.program.actions
            if action.action_type == "select_designation"
        ) == ("select_designation",)
        expected_target = expected_targets[episode.expanded_case.scenario_ref]
        assert expected_target in candidate.provenance_refs
        assert expected[0].applications[0].operator == "op:event"
        assert meaning.expression.applications[0].operator == "op:event"
        assert (
            expected[0].applications[0].predicate_ref
            == meaning.expression.applications[0].predicate_ref
            == expected_target
        )


def test_reviewed_designation_aliases_match_authentic_r3_cycles(
    tmp_path: Path,
) -> None:
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, model_identity)
    compiler = ExpectedCycleContractCompiler(
        authority, abi_registry_ref="abi:r4-authentic-designations"
    )
    expander = CaseExpander(compiler)
    scenarios = {
        row.scenario_ref: row
        for row in load_reviewed_scenarios(SCENARIOS)
        if len(row.assertions) == 1 and row.assertions[0].kind == "designates"
    }
    cases = tuple(
        case
        for scenario in scenarios.values()
        for case in expander.expand(scenario, revision_pin=pin)
    )
    linked: list[tuple[ExpandedCase, str, str]] = []
    unlinked: set[tuple[str, str]] = set()
    for case in cases:
        target = scenarios[case.scenario_ref].assertions[0].fields["target"]
        canonical_surface = authority.designations.canonical_surface_for_target(
            case.surface,
            target,
            case.language,
        )
        if canonical_surface is None:
            unlinked.add((case.surface, target))
        else:
            linked.append((case, target, canonical_surface))

    assert len(scenarios) == 15
    assert len(cases) == 32
    assert len(linked) == 29
    assert unlinked == {
        ("the book", "entity:book"),
        ("the server", "entity:server"),
        ("the lamp", "entity:lamp"),
    }
    assert authority.designations.for_surface("entity:book", "en") == ()
    assert authority.designations.for_surface(
        "CEMM", "en"
    ) == authority.designations.for_surface("cemm", "en")
    assert (
        authority.designations.canonical_surface_for_target(
            "cemm", "participant:system", "en"
        )
        == "CEMM"
    )

    episodes = []
    for index, (case, target, canonical_surface) in enumerate(linked):
        runtime = load_runtime(
            ROOT,
            profile="development",
            store_path=tmp_path / f"designation-{index:02d}.db",
        )
        try:
            episode = AuthenticEpisodeBuilder(
                PublicRuntimeEpisodeOwner(lambda _case, runtime=runtime: runtime)
            ).build(case)
        finally:
            runtime.stores.close()
        episodes.append((episode, target, canonical_surface))

    assert all(episode.comparison.passed for episode, _, _ in episodes)
    for episode, target, canonical_surface in episodes:
        expected = episode.expected_contract.expected_expressions
        meaning = episode.observed_cycle.verification.selected_meaning
        candidate_ref = episode.observed_cycle.verification.selected_candidate_ref
        assert len(expected) == 1
        assert meaning is not None
        assert candidate_ref is not None
        candidate = episode.observed_cycle.proposal.candidate_by_ref(candidate_ref)
        assert tuple(
            action.action_type
            for action in candidate.program.actions
            if action.action_type == "select_designation"
        ) == ("select_designation",)
        expected_application = expected[0].applications[0]
        observed_application = meaning.expression.applications[0]
        assert (
            expected_application.operator
            == observed_application.operator
            == "op:designation"
        )
        assert (
            expected_application.predicate_ref
            == observed_application.predicate_ref
            == target
        )
        expected_roles = {
            binding.role_ref: binding.filler
            for binding in expected_application.roles
        }
        observed_roles = {
            binding.role_ref: binding.filler
            for binding in observed_application.roles
        }
        assert expected_roles == observed_roles == {
            "role:surface": LiteralValue("string", canonical_surface),
            "role:target": GroundedReference(target),
        }


def test_prospective_alias_teaching_uses_definition_evidence_without_prelinking(
    tmp_path: Path,
) -> None:
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    assert authority.designations.for_surface("hola", "es") == ()

    episodes = _authentic_episodes_for_scenario(
        "scenario:multilingual_aliases-0169",
        tmp_path,
    )

    assert episodes
    assert all(row.comparison.passed for row in episodes)
    assert authority.designations.for_surface("hola", "es") == ()


@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:capability_policy_adapter_effect-0131",
        "scenario:capability_policy_adapter_effect-0132",
        "scenario:capability_policy_adapter_effect-0133",
        "scenario:capability_policy_adapter_effect-0134",
    ),
    ids=("query", "respond", "learn-alias", "set-state"),
)
def test_reviewed_capability_queries_use_explicit_designations(
    scenario_ref: str,
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(scenario_ref, tmp_path)

    assert episodes
    assert all(row.comparison.passed for row in episodes)


def test_reviewed_sensor_and_operation_evidence_uses_authentic_extra_items(
    tmp_path: Path,
) -> None:
    scenarios = tuple(
        row
        for row in load_reviewed_scenarios(SCENARIOS)
        if row.competency_category == "reviewed_sensor_operation_evidence"
    )
    assert len(scenarios) == 10
    episodes = tuple(
        episode
        for scenario in scenarios
        for episode in _authentic_episodes_for_scenario(
            scenario.scenario_ref,
            tmp_path / scenario.scenario_ref.rsplit("-", 1)[-1],
        )
    )

    assert episodes
    assert all(row.comparison.passed for row in episodes)
    assert all(row.comparison.environment_match for row in episodes)


@pytest.mark.parametrize(
    "category",
    ("adversarial_programs", "gap_kinds", "restart"),
    ids=("adversarial", "gaps", "restart"),
)
def test_fail_closed_boundary_families_match_authentic_cycles(
    category: str,
    tmp_path: Path,
) -> None:
    scenarios = tuple(
        row
        for row in load_reviewed_scenarios(SCENARIOS)
        if row.competency_category == category
    )
    assert len(scenarios) == (18 if category == "gap_kinds" else 10)
    scenario_refs = {row.scenario_ref for row in scenarios}
    cases = tuple(
        case for case in _expanded_cases() if case.scenario_ref in scenario_refs
    )
    environment = build_environment(ROOT, tmp_path)
    builder = AuthenticEpisodeBuilder(
        PublicRuntimeEpisodeOwner(
            environment["runtime_factory"],
            restart_executor=environment["restart_executor"],
        )
    )
    try:
        episodes = builder.build_many(cases)
    finally:
        environment["close"]()

    assert episodes
    assert all(row.comparison.passed for row in episodes)


def test_reported_speech_relational_content_composes_recursively(
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(
        "scenario:reported_speech-0087", tmp_path
    )

    assert episodes
    assert all(row.comparison.passed for row in episodes)


def test_reported_speech_event_content_reuses_speaker_by_reviewed_coreference(
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(
        "scenario:reported_speech-0079", tmp_path
    )

    assert episodes
    assert all(row.comparison.passed for row in episodes)


def test_singleton_polysemy_is_not_fabricated_as_ambiguity() -> None:
    scenarios = {row.scenario_ref: row for row in load_reviewed_scenarios(SCENARIOS)}
    polysemy = tuple(
        row
        for row in _expanded_cases()
        if any(assertion.kind == "polysemy" for assertion in scenarios[row.scenario_ref].assertions)
    )
    assert polysemy
    for row in polysemy:
        if len(row.contract.expected_expressions) == 1:
            assert row.contract.outcome_kind is not ExpectedOutcomeKind.AMBIGUITY
            assert row.contract.expression_relation is not ExpressionRelation.ANY


def test_singleton_polysemy_is_observed_designation_evidence() -> None:
    cases = tuple(
        row
        for row in _expanded_cases()
        if row.scenario_ref == "scenario:polysemy-0027"
    )

    assert cases
    assert all(row.contract.expected_mode.value == "OBSERVE" for row in cases)
    assert all(
        row.contract.expected_expression.applications[0].operator == "op:designation"
        for row in cases
    )


def test_question_mark_projects_state_interrogative_to_query_mode(
    tmp_path: Path,
) -> None:
    runtime = load_runtime(
        ROOT,
        profile="development",
        store_path=tmp_path / "question-mode",
    )
    try:
        orientation, _ = runtime.orient("question-mode", "is the server online?")
    finally:
        runtime.stores.close()

    assert orientation.mode.value == "QUERY"


def test_external_sensor_provenance_is_not_mistaken_for_active_adapter_authority() -> None:
    cases = _expanded_cases()
    sensor_cases = tuple(
        row for row in cases
        if row.scenario_ref in {
            "scenario:reviewed_sensor_operation_evidence-0099",
            "scenario:reviewed_sensor_operation_evidence-0100",
            "scenario:reviewed_sensor_operation_evidence-0105",
        }
    )
    assert sensor_cases
    assert all(row.contract.outcome_kind is not ExpectedOutcomeKind.GAP for row in sensor_cases)

    explicit_adapter = tuple(row for row in cases if row.scenario_ref == "scenario:capability_policy_adapter_effect-0139")
    assert explicit_adapter
    for row in explicit_adapter:
        assert row.contract.outcome_kind is ExpectedOutcomeKind.GAP
        assert row.contract.expected_gap is not None
        assert row.contract.expected_gap.error_code is None
        assert row.contract.expected_gap.recommended_owner == "training"


def test_learning_reported_speech_and_effect_contracts_have_connected_compatible_topology() -> None:
    cases = _expanded_cases()
    reviewed = {
        row.scenario_ref: row
        for row in cases
        if row.scenario_ref in {
            "scenario:reported_speech-0081",
            "scenario:learning_security-0119",
            "scenario:learning_security-0120",
            "scenario:learning_security-0121",
            "scenario:learning_security-0122",
            "scenario:learning_security-0125",
            "scenario:learning_security-0126",
            "scenario:learning_security-0129",
            "scenario:capability_policy_adapter_effect-0140",
            "scenario:capability_policy_adapter_effect-0142",
        }
    }
    assert len(reviewed) == 10
    for case in reviewed.values():
        for expression in case.contract.expected_expressions:
            application_refs = {app.application_ref for app in expression.applications}
            node_refs = {
                *application_refs,
                *(row.scope_ref for row in expression.scope_operators),
                *(row.link_ref for row in expression.expression_links),
                *(row.binder_ref for row in expression.binders),
            }
            assert set(expression.root_refs) <= node_refs
            child_refs = {
                binding.filler.application_ref
                for app in expression.applications
                for binding in (*app.roles, *app.qualifiers)
                if hasattr(binding.filler, "application_ref")
            }
            assert child_refs <= application_refs
            assert len(expression.root_refs) == 1
