"""Output-only query grammar: real public graphs and finite negative contrasts."""
from dataclasses import replace
from pathlib import Path
import os
import subprocess
import sys

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.development_reference import _CannotPresent, _EnglishGraph
from cemm_authoritative_hybrid.expressions import (
    BoundVariable, GroundedReference, LiteralValue, RoleBinding,
    ScopeOperator, SemanticApplication, SemanticExpression, VariableBinder,
)

ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[respond]': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-respond',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                     'owner_ref': 'runtime-path',
                                                                                                     'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[learn-aliases]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-learn-aliases',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'runtime-path',
                                                                                                           'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[speaker]': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-speaker',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                     'owner_ref': 'runtime-path',
                                                                                                     'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[named]': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-named',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                   'owner_ref': 'runtime-path',
                                                                                                   'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[negative-cap]': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-negative-cap',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                          'owner_ref': 'runtime-path',
                                                                                                          'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[subject]': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-subject',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                     'owner_ref': 'runtime-path',
                                                                                                     'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[object]': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-object',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                    'owner_ref': 'runtime-path',
                                                                                                    'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_public_query_diagnostic_covers_exact_graph[type]': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:foundation-query-output-public-query-diagnostic-covers-exact-graph-type',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                  'owner_ref': 'runtime-path',
                                                                                                  'source_ast_sha256': 'bfbac84a8ecd4c86191443167ea37040c0f8b8892a7844d7dfb5dc3014491c27'},
 'tests/test_foundation_query_output.py::test_same_status_query_graphs_keep_distinct_surfaces[capability-identities]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-query-output-same-status-query-graphs-keep-distinct-surfaces-capability-identities',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'runtime-path',
                                                                                                                        'source_ast_sha256': '88f46d0c477ee13de8d38b44c1f0424ce1eea1a68c3de037f62df7ff82c9577a'},
 'tests/test_foundation_query_output.py::test_same_status_query_graphs_keep_distinct_surfaces[queried-roles]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-query-output-same-status-query-graphs-keep-distinct-surfaces-queried-roles',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'runtime-path',
                                                                                                                'source_ast_sha256': '88f46d0c477ee13de8d38b44c1f0424ce1eea1a68c3de037f62df7ff82c9577a'},
 'tests/test_foundation_query_output.py::test_supported_variable_query_renders_actual_instantiation[subject-answer]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-query-output-supported-variable-query-renders-actual-instantiation-subject-answer',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'runtime-path',
                                                                                                                       'source_ast_sha256': '80a9d15cc97aa8f75d2c86e6040b4839b3066a2ebae38270f75ba982d7cecc92'},
 'tests/test_foundation_query_output.py::test_supported_variable_query_renders_actual_instantiation[object-answer]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-query-output-supported-variable-query-renders-actual-instantiation-object-answer',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'runtime-path',
                                                                                                                      'source_ast_sha256': '80a9d15cc97aa8f75d2c86e6040b4839b3066a2ebae38270f75ba982d7cecc92'},
 'tests/test_foundation_query_output.py::test_supported_variable_query_renders_actual_instantiation[type-answer]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-query-output-supported-variable-query-renders-actual-instantiation-type-answer',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'runtime-path',
                                                                                                                    'source_ast_sha256': '80a9d15cc97aa8f75d2c86e6040b4839b3066a2ebae38270f75ba982d7cecc92'},
 'tests/test_foundation_query_output.py::test_supported_variable_query_renders_actual_instantiation[subject-denied]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-query-output-supported-variable-query-renders-actual-instantiation-subject-denied',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'runtime-path',
                                                                                                                       'source_ast_sha256': '80a9d15cc97aa8f75d2c86e6040b4839b3066a2ebae38270f75ba982d7cecc92'},
 'tests/test_foundation_query_output.py::test_supported_variable_query_renders_actual_instantiation[object-denied]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-query-output-supported-variable-query-renders-actual-instantiation-object-denied',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'runtime-path',
                                                                                                                      'source_ast_sha256': '80a9d15cc97aa8f75d2c86e6040b4839b3066a2ebae38270f75ba982d7cecc92'},
 'tests/test_foundation_query_output.py::test_supported_variable_query_renders_actual_instantiation[type-denied]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-query-output-supported-variable-query-renders-actual-instantiation-type-denied',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'runtime-path',
                                                                                                                    'source_ast_sha256': '80a9d15cc97aa8f75d2c86e6040b4839b3066a2ebae38270f75ba982d7cecc92'},
 'tests/test_foundation_query_output.py::test_query_component_preserves_participant_perspective[object-system]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-query-output-query-component-preserves-participant-perspective-object-system',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'runtime-path',
                                                                                                                  'source_ast_sha256': '279310ca28f1a8f1537c16ef667e4e460b6ba27e33ccaa1a67c93ec83c772527'},
 'tests/test_foundation_query_output.py::test_query_component_preserves_participant_perspective[object-user]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-query-output-query-component-preserves-participant-perspective-object-user',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'runtime-path',
                                                                                                                'source_ast_sha256': '279310ca28f1a8f1537c16ef667e4e460b6ba27e33ccaa1a67c93ec83c772527'},
 'tests/test_foundation_query_output.py::test_query_component_preserves_participant_perspective[subject-system]': {'activation_phase': 'R4',
                                                                                                                   'assertion_ref': 'assertion:foundation-query-output-query-component-preserves-participant-perspective-subject-system',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                   'owner_ref': 'runtime-path',
                                                                                                                   'source_ast_sha256': '279310ca28f1a8f1537c16ef667e4e460b6ba27e33ccaa1a67c93ec83c772527'},
 'tests/test_foundation_query_output.py::test_query_component_preserves_participant_perspective[subject-user]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-query-output-query-component-preserves-participant-perspective-subject-user',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'runtime-path',
                                                                                                                 'source_ast_sha256': '279310ca28f1a8f1537c16ef667e4e460b6ba27e33ccaa1a67c93ec83c772527'},
 'tests/test_foundation_query_output.py::test_actual_interactive_cli_query_diagnostics[concise]': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:foundation-query-output-actual-interactive-cli-query-diagnostics-concise',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                   'owner_ref': 'runtime-path',
                                                                                                   'source_ast_sha256': '50d9b521528716a13192a622ebf3367a5a74d8ee5b40bf9ef0030365703266d7'},
 'tests/test_foundation_query_output.py::test_actual_interactive_cli_query_diagnostics[trace]': {'activation_phase': 'R4',
                                                                                                 'assertion_ref': 'assertion:foundation-query-output-actual-interactive-cli-query-diagnostics-trace',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                 'owner_ref': 'runtime-path',
                                                                                                 'source_ast_sha256': '50d9b521528716a13192a622ebf3367a5a74d8ee5b40bf9ef0030365703266d7'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[cap-role]': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-cap-role',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'runtime-path',
                                                                                                             'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[cap-qualifier]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-cap-qualifier',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'runtime-path',
                                                                                                                  'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[cap-label]': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-cap-label',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                              'owner_ref': 'runtime-path',
                                                                                                              'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[cap-scope]': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-cap-scope',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                              'owner_ref': 'runtime-path',
                                                                                                              'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-role]': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-role',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'runtime-path',
                                                                                                             'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-qualifier]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-qualifier',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'runtime-path',
                                                                                                                  'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-label]': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-label',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                              'owner_ref': 'runtime-path',
                                                                                                              'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-foreign]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-foreign',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'runtime-path',
                                                                                                                'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-unused]': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-unused',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                               'owner_ref': 'runtime-path',
                                                                                                               'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-repeated]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-repeated',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'runtime-path',
                                                                                                                 'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-scope]': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-scope',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                              'owner_ref': 'runtime-path',
                                                                                                              'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_unlicensed_structure_fails_closed[var-bodies]': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:foundation-query-output-query-component-unlicensed-structure-fails-closed-var-bodies',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                               'owner_ref': 'runtime-path',
                                                                                                               'source_ast_sha256': '4d8fab1ee794f0e88a44689ac4ad1b03ea5c5a3c808c46300b4476042e988995'},
 'tests/test_foundation_query_output.py::test_query_component_scope_preserved_or_closed[cap-negative]': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:foundation-query-output-query-component-scope-preserved-or-closed-cap-negative',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                         'owner_ref': 'runtime-path',
                                                                                                         'source_ast_sha256': '3cd934c112f4e29e994d1af8c6bd3bd74d9bdc3e4c272b91fc4a7eb6da36b4eb'},
 'tests/test_foundation_query_output.py::test_query_component_scope_preserved_or_closed[cap-past]': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:foundation-query-output-query-component-scope-preserved-or-closed-cap-past',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                     'owner_ref': 'runtime-path',
                                                                                                     'source_ast_sha256': '3cd934c112f4e29e994d1af8c6bd3bd74d9bdc3e4c272b91fc4a7eb6da36b4eb'},
 'tests/test_foundation_query_output.py::test_query_component_scope_preserved_or_closed[var-negative]': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:foundation-query-output-query-component-scope-preserved-or-closed-var-negative',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                         'owner_ref': 'runtime-path',
                                                                                                         'source_ast_sha256': '3cd934c112f4e29e994d1af8c6bd3bd74d9bdc3e4c272b91fc4a7eb6da36b4eb'},
 'tests/test_foundation_query_output.py::test_query_component_scope_preserved_or_closed[var-past]': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:foundation-query-output-query-component-scope-preserved-or-closed-var-past',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                     'owner_ref': 'runtime-path',
                                                                                                     'source_ast_sha256': '3cd934c112f4e29e994d1af8c6bd3bd74d9bdc3e4c272b91fc4a7eb6da36b4eb'}}


@pytest.mark.parametrize("source,expected,status,predicate,variable_role", (
    ("Can you respond?", "Supported: I can respond.", "supported", "cap:respond", None),
    ("Can you learn aliases?", "Supported: I can learn aliases.", "supported", "cap:learn_alias", None),
    ("Can I respond?", "Unknown: you can respond.", "unknown", "cap:respond", None),
    ("Can Bob respond?", "Unknown: Bob can respond.", "unknown", "cap:respond", None),
    ("Can you not respond?", "Contradicted: not (not (I can respond)).", "contradicted", "cap:respond", None),
    ("Who likes Bob?", "Unknown: who or what likes Bob?", "unknown", "rel:likes", "role:subject"),
    ("Bob likes who?", "Unknown: Bob likes who or what?", "unknown", "rel:likes", "role:object"),
    ("Who is a mother?", "Unknown: who or what is a mother?", "unknown", "concept:mother", "role:instance"),
), ids=("respond", "learn-aliases", "speaker", "named", "negative-cap", "subject", "object", "type"))
def test_public_query_diagnostic_covers_exact_graph(tmp_path, source, expected, status, predicate, variable_role):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "public.db")
    try:
        cycle = runtime.process("session:query-output", source)
        assert cycle.evaluation.decision.status.value == status
        expression = cycle.response_meaning.response_expression
        assert len(expression.applications) == 1
        app = expression.applications[0]
        assert app.predicate_ref == predicate
        if variable_role:
            assert len(expression.binders) == 1
            binder = expression.binders[0]
            assert binder.body_ref == app.application_ref
            assert dict((r.role_ref, r.filler) for r in app.roles)[variable_role] == BoundVariable(binder.variable_ref)
        else:
            assert not expression.binders
            assert {r.role_ref for r in app.roles} == {"role:subject"}
        before, focus = runtime.stores.revision_pin(), runtime.stores.focus.revision
        original = cycle.as_dict()
        output = runtime.development_reference(cycle)
        assert output.surface == expected
        assert not output.limitations
        assert (app.application_ref, "node") in output.slot_coverage
        assert (app.application_ref, "predicate") in output.slot_coverage
        assert all((app.application_ref, r.role_ref) in output.slot_coverage for r in app.roles)
        for scope in expression.scope_operators:
            assert (scope.scope_ref, "operand") in output.slot_coverage
            assert (scope.scope_ref, "value") in output.slot_coverage
        if variable_role:
            assert (binder.binder_ref, "variable") in output.slot_coverage
            assert (binder.binder_ref, "body") in output.slot_coverage
            assert (app.application_ref, variable_role) in output.slot_coverage
        assert any(t == predicate and p for t, _, p in output.designation_provenance)
        assert runtime.stores.revision_pin() == before
        assert runtime.stores.focus.revision == focus
        assert cycle.as_dict() == original
        assert cycle.realization_receipt is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("sources,status", (
    (("Can you respond?", "Can you learn aliases?"), "supported"),
    (("Who likes Bob?", "Bob likes who?"), "unknown"),
), ids=("capability-identities", "queried-roles"))
def test_same_status_query_graphs_keep_distinct_surfaces(tmp_path, sources, status):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "contrasts.db")
    try:
        cycles, outputs = [], []
        for source in sources:
            cycle = runtime.process("session:contrasts", source)
            cycles.append(cycle)
            # Consume each exact captured pin before the next journal advance.
            outputs.append(runtime.development_reference(cycle))
        assert all(c.evaluation.decision.status.value == status for c in cycles)
        expressions = tuple(c.response_meaning.response_expression for c in cycles)
        assert len(expressions[0].applications) == len(expressions[1].applications) == 1
        assert len(expressions[0].binders) == len(expressions[1].binders)
        assert expressions[0].expression_ref != expressions[1].expression_ref
        assert all(o.surface and not o.limitations for o in outputs)
        assert outputs[0].surface != outputs[1].surface
        assert all(c.realization_receipt is None for c in cycles)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("source,operator,predicate,subject,object_ref,stance,expected", (
    ("Who likes Bob?", "op:relation", "rel:likes", "entity:alice", "entity:bob", "support", "Supported: Alice likes Bob."),
    ("Bob likes who?", "op:relation", "rel:likes", "entity:bob", "entity:alice", "support", "Supported: Bob likes Alice."),
    ("Who is a mother?", "op:type", "concept:mother", "entity:alice", None, "support", "Supported: Alice is a mother."),
    ("Who likes Bob?", "op:relation", "rel:likes", "entity:alice", "entity:bob", "deny", "Contradicted: not (Alice likes Bob)."),
    ("Bob likes who?", "op:relation", "rel:likes", "entity:bob", "entity:alice", "deny", "Contradicted: not (Bob likes Alice)."),
    ("Who is a mother?", "op:type", "concept:mother", "entity:alice", None, "deny", "Contradicted: not (Alice is a mother)."),
), ids=("subject-answer", "object-answer", "type-answer", "subject-denied", "object-denied", "type-denied"))
def test_supported_variable_query_renders_actual_instantiation(tmp_path, source, operator, predicate, subject, object_ref, stance, expected):
    # Isolated indexed world fixture; no authority publication or invented answer.
    from tests.test_foundation_description_builder import _seed_reviewed_generic_claim
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "answer.db")
    try:
        roles = ((RoleBinding("role:instance", GroundedReference(subject)),
                  RoleBinding("role:class", GroundedReference(predicate))) if object_ref is None else
                 (RoleBinding("role:subject", GroundedReference(subject)),
                  RoleBinding("role:object", GroundedReference(object_ref))))
        app = SemanticApplication("app:answer", operator, predicate, roles)
        fact = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        _seed_reviewed_generic_claim(runtime.stores, fact, stance=stance)
        cycle = runtime.process("session:actual-answer", source)
        assert cycle.evaluation.decision.status.value == ("supported" if stance == "support" else "contradicted")
        assert cycle.evaluation.expression.binders
        assert not cycle.response_meaning.response_expression.binders
        before, focus = runtime.stores.revision_pin(), runtime.stores.focus.revision
        output = runtime.development_reference(cycle)
        assert output.surface == expected
        assert not output.limitations
        assert runtime.stores.revision_pin() == before
        assert runtime.stores.focus.revision == focus
        assert cycle.realization_receipt is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("source,role,target,expected", (
    ("Who likes Bob?", "role:object", "participant:system", "who or what likes me"),
    ("Who likes Bob?", "role:object", "participant:user", "who or what likes you"),
    ("Bob likes who?", "role:subject", "participant:system", "I like who or what"),
    ("Bob likes who?", "role:subject", "participant:user", "you like who or what"),
), ids=("object-system", "object-user", "subject-system", "subject-user"))
def test_query_component_preserves_participant_perspective(tmp_path, source, role, target, expected):
    # Independent output graph contrast, not public input-grammar support.
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "perspective.db")
    try:
        cycle = runtime.process("session:query-perspective", source)
        expression = cycle.response_meaning.response_expression
        app = expression.applications[0]
        app = replace(app, roles=tuple(RoleBinding(r.role_ref, GroundedReference(target) if r.role_ref == role else r.filler) for r in app.roles))
        expression = SemanticExpression.create(applications=(app,), binders=expression.binders, root_refs=expression.root_refs)
        provenance, rules, coverage = [], [], []
        with runtime._owners["orientation"]._designation_reader.batch(cycle.final_revision_pin) as batch:
            renderer = _EnglishGraph(batch, cycle.evaluation.situation, provenance, rules, coverage)
            assert renderer.graph(expression) == expected
        assert "output:participant-perspective" in rules
        assert any(t == "rel:likes" and p for t, _, p in provenance)
        assert (app.application_ref, role) in coverage
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("trace", (False, True), ids=("concise", "trace"))
def test_actual_interactive_cli_query_diagnostics(tmp_path, trace):
    command = [sys.executable, "-m", "cemm_authoritative_hybrid.cli", "--root", str(ROOT),
               "--interactive", "--store", str(tmp_path / "cli.db"), "--development-reference"]
    if trace:
        command.append("--trace")
    child_environment = os.environ.copy()
    inherited_pythonpath = child_environment.get("PYTHONPATH", "")
    child_environment["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + inherited_pythonpath if inherited_pythonpath else "")
    result = subprocess.run(command, input="Can you respond?\nCan you learn aliases?\nWho likes Bob?\nBob likes who?\nWho is a mother?\n/quit\n",
                            text=True, capture_output=True, cwd=ROOT, env=child_environment, timeout=60)
    assert result.returncode == 0, result.stderr
    for surface in ("Supported: I can respond.", "Supported: I can learn aliases.",
                    "Unknown: who or what likes Bob?", "Unknown: Bob likes who or what?",
                    "Unknown: who or what is a mother?"):
        assert "CEMM (development reference): " + surface in result.stdout
    assert "No complete output rule" not in result.stdout
    assert ('"realization_receipt": null' in result.stdout) is trace
    assert ('"development_only": true' in result.stdout) is trace


@pytest.mark.parametrize("family,mutation", (
    ("capability", "extra-role"), ("capability", "qualifier"),
    ("capability", "missing-label"), ("capability", "scope"),
    ("variable", "extra-role"), ("variable", "qualifier"),
    ("variable", "missing-label"), ("variable", "foreign-variable"),
    ("variable", "unused-variable"), ("variable", "two-occurrences"),
    ("variable", "scope"), ("variable", "multiple-bodies"),
), ids=("cap-role", "cap-qualifier", "cap-label", "cap-scope", "var-role", "var-qualifier",
        "var-label", "var-foreign", "var-unused", "var-repeated", "var-scope", "var-bodies"))
def test_query_component_unlicensed_structure_fails_closed(tmp_path, family, mutation):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "negative.db")
    try:
        cycle = runtime.process("session:negative-output", "Can you respond?" if family == "capability" else "Who likes Bob?")
        expression = cycle.response_meaning.response_expression
        app = expression.applications[0]
        kwargs = dict(applications=expression.applications, root_refs=expression.root_refs, binders=expression.binders)
        if mutation == "extra-role":
            app = replace(app, roles=(*app.roles, RoleBinding("role:owner", GroundedReference("entity:alice"))))
        elif mutation == "qualifier":
            app = replace(app, qualifiers=(RoleBinding("role:owner", LiteralValue("string", "must retain")),))
        elif mutation == "missing-label":
            app = replace(app, predicate_ref="cap:unknown" if family == "capability" else "rel:unknown")
        elif mutation in {"foreign-variable", "unused-variable", "two-occurrences"}:
            roles = {r.role_ref: r.filler for r in app.roles}
            if mutation == "foreign-variable":
                roles["role:object"] = BoundVariable("?foreign")
            elif mutation == "unused-variable":
                kwargs["binders"] = (replace(expression.binders[0], variable_ref="?unused"),)
            else:
                roles["role:object"] = roles["role:subject"]
            app = replace(app, roles=tuple(RoleBinding(k, v) for k, v in roles.items()))
        elif mutation == "scope":
            scope = ScopeOperator("scope:unlicensed", "scope:aspect", "scope_value:aspect:ongoing", expression.root_refs[0])
            kwargs.update(scope_operators=(scope,), root_refs=(scope.scope_ref,))
        else:
            second = replace(app, application_ref="app:extra", roles=(RoleBinding("role:subject", GroundedReference("entity:alice")), RoleBinding("role:object", GroundedReference("entity:bob"))))
            kwargs["root_refs"] = (*expression.root_refs, second.application_ref)
            kwargs["applications"] = (app, second)
        if mutation != "multiple-bodies":
            kwargs["applications"] = (app,)
        with runtime._owners["orientation"]._designation_reader.batch(cycle.final_revision_pin) as batch:
            renderer = _EnglishGraph(batch, cycle.evaluation.situation, [], [], [])
            # Canonical construction itself rejects escaped/unused variables;
            # otherwise the finite output owner must refuse the whole graph.
            with pytest.raises((ValueError, _CannotPresent)):
                renderer.graph(SemanticExpression.create(**kwargs))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("family,scope,expected", (
    ("capability", "negative", "not (I can respond)"),
    ("capability", "past", "in the past (I can respond)"),
    ("variable", "negative", None),
    ("variable", "past", None),
), ids=("cap-negative", "cap-past", "var-negative", "var-past"))
def test_query_component_scope_preserved_or_closed(tmp_path, family, scope, expected):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "scope.db")
    try:
        cycle = runtime.process("session:scope-output", "Can you respond?" if family == "capability" else "Who likes Bob?")
        expression = cycle.response_meaning.response_expression
        operator, value = (("scope:polarity", "scope_value:polarity:negative") if scope == "negative" else ("scope:tense", "scope_value:tense:past"))
        node = ScopeOperator("scope:test", operator, value, expression.root_refs[0])
        expression = SemanticExpression.create(applications=expression.applications, binders=expression.binders,
                                              scope_operators=(node,), root_refs=(node.scope_ref,))
        with runtime._owners["orientation"]._designation_reader.batch(cycle.final_revision_pin) as batch:
            renderer = _EnglishGraph(batch, cycle.evaluation.situation, [], [], [])
            if expected is None:
                with pytest.raises(_CannotPresent):
                    renderer.graph(expression)
            else:
                assert renderer.graph(expression) == expected
    finally:
        runtime.stores.close()
