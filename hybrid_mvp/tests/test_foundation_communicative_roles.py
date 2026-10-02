"""Source-local communication construction, without response or force authority."""
from pathlib import Path
from dataclasses import fields
from copy import copy
import json
import inspect

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.expressions import (
    CompilationFailure, SemanticExpressionCompiler, GroundedReference, RoleBinding, SemanticApplication, SemanticExpression,
)
from cemm_authoritative_hybrid.coverage import CoverageVerifier
from cemm_authoritative_hybrid.programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from cemm_authoritative_hybrid.verifier import _replay_program
from cemm_authoritative_hybrid.verifier_reconstruction import reconstruct_expected_expression
from tests.test_foundation_relation_queries import _rehash_derivation, _slot_with
from tests.test_foundation_semantics import _static_composition_context
from cemm_authoritative_hybrid.authority import DesignationFact
from cemm_authoritative_hybrid.role_schemas import CommunicativeRoleMatch, ReviewedRoleSchemaIndex
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.proposal_context import ProposalContext
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

__cemm_test_inventory__ = {'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[bare]': {'activation_phase': 'R2',
                                                                                                         'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-bare',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                         'owner_ref': 'form-context',
                                                                                                         'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[postfix]': {'activation_phase': 'R2',
                                                                                                            'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-postfix',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                            'owner_ref': 'form-context',
                                                                                                            'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[prefix]': {'activation_phase': 'R2',
                                                                                                           'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-prefix',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'form-context',
                                                                                                           'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[both]': {'activation_phase': 'R2',
                                                                                                         'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-both',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                         'owner_ref': 'form-context',
                                                                                                         'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[participant-prefix]': {'activation_phase': 'R2',
                                                                                                                       'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-participant-prefix',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'form-context',
                                                                                                                       'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[participant-postfix]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-participant-postfix',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[terminal]': {'activation_phase': 'R2',
                                                                                                             'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-terminal',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'form-context',
                                                                                                             'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_public_communication_preserves_exact_roles[farewell]': {'activation_phase': 'R2',
                                                                                                             'assertion_ref': 'assertion:communicative-roles-public-communication-preserves-exact-roles-farewell',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'form-context',
                                                                                                             'source_ast_sha256': 'ea8f9e58ffa42b2d83b1cd68ef2d002f9cd01c0af6994798c33f03ae1b205cb5'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_reversed_communication_fails_exact_sinks[entities]': {'activation_phase': 'R2',
                                                                                                                    'assertion_ref': 'assertion:communicative-roles-rehashed-reversed-communication-fails-exact-sinks-entities',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'form-context',
                                                                                                                    'source_ast_sha256': '2b476c0bef1109820c88aa6d5d11e69babf98803db784d5379ed7468e906c238'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_reversed_communication_fails_exact_sinks[participant]': {'activation_phase': 'R2',
                                                                                                                       'assertion_ref': 'assertion:communicative-roles-rehashed-reversed-communication-fails-exact-sinks-participant',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'form-context',
                                                                                                                       'source_ast_sha256': '2b476c0bef1109820c88aa6d5d11e69babf98803db784d5379ed7468e906c238'},
 'tests/test_foundation_communicative_roles.py::test_public_session_reference_collision_preserves_situated_defaults': {'activation_phase': 'R2',
                                                                                                                       'assertion_ref': 'assertion:communicative-roles-public-session-reference-collision-preserves-situated-defaults',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'form-context',
                                                                                                                       'source_ast_sha256': 'bbcce0621bc5d2613e9f63b55a8b8dbf8aa443ef0635decd05c4de8c1fdfc863'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[en-bare]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-en-bare',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[en-prefix]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-en-prefix',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'form-context',
                                                                                                                                   'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[en-postfix]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-en-postfix',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'form-context',
                                                                                                                                    'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[en-both]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-en-both',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[en-participant-prefix]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-en-participant-prefix',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'form-context',
                                                                                                                                               'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[en-participant-postfix]': {'activation_phase': 'R2',
                                                                                                                                                'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-en-participant-postfix',
                                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                                'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[es-bare]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-es-bare',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[es-prefix]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-es-prefix',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'form-context',
                                                                                                                                   'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[es-postfix]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-es-postfix',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'form-context',
                                                                                                                                    'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[es-both]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-es-both',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[es-participant-prefix]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-es-participant-prefix',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'form-context',
                                                                                                                                               'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_static_designation_source_geometry_preserves_multilingual_roles[es-participant-postfix]': {'activation_phase': 'R2',
                                                                                                                                                'assertion_ref': 'assertion:communicative-roles-static-designation-source-geometry-preserves-multilingual-roles-es-participant-postfix',
                                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                                'source_ast_sha256': '44ee4e897e39152b8a94be2b218be2648783578c355d8de66dc4680c06b053c4'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[quotation]': {'activation_phase': 'R2',
                                                                                                                         'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-quotation',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'form-context',
                                                                                                                         'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[reported]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-reported',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[modality]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-modality',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[polarity]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-polarity',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[coordination]': {'activation_phase': 'R2',
                                                                                                                            'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-coordination',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'form-context',
                                                                                                                            'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[extra-referent]': {'activation_phase': 'R2',
                                                                                                                              'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-extra-referent',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'form-context',
                                                                                                                              'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[vocative]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-vocative',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[compound]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-compound',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[question]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-question',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_unsupported_source_never_acquires_direct_construction[causal]': {'activation_phase': 'R2',
                                                                                                                      'assertion_ref': 'assertion:communicative-roles-unsupported-source-never-acquires-direct-construction-causal',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'form-context',
                                                                                                                      'source_ast_sha256': '6cc11a44251dd1fbfcd801e4ce2d3bc1df938613f8864c10e28eff64af36de8f'},
 'tests/test_foundation_communicative_roles.py::test_wrong_activated_index_rejects_direct_construction_at_exact_sinks[missing]': {'activation_phase': 'R2',
                                                                                                                                  'assertion_ref': 'assertion:communicative-roles-wrong-activated-index-rejects-direct-construction-at-exact-sinks-missing',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'form-context',
                                                                                                                                  'source_ast_sha256': '8485f5b08cbf1615cb63bd6429e5dc7deef3a6387a8442a02616ac95c31ff268'},
 'tests/test_foundation_communicative_roles.py::test_wrong_activated_index_rejects_direct_construction_at_exact_sinks[stale]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:communicative-roles-wrong-activated-index-rejects-direct-construction-at-exact-sinks-stale',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': '8485f5b08cbf1615cb63bd6429e5dc7deef3a6387a8442a02616ac95c31ff268'},
 'tests/test_foundation_communicative_roles.py::test_wrong_activated_index_rejects_direct_construction_at_exact_sinks[different-pack]': {'activation_phase': 'R2',
                                                                                                                                         'assertion_ref': 'assertion:communicative-roles-wrong-activated-index-rejects-direct-construction-at-exact-sinks-different-pack',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                         'owner_ref': 'form-context',
                                                                                                                                         'source_ast_sha256': '8485f5b08cbf1615cb63bd6429e5dc7deef3a6387a8442a02616ac95c31ff268'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[assignments]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-assignments',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[reference-provenance]': {'activation_phase': 'R2',
                                                                                                                                         'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-reference-provenance',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                         'owner_ref': 'form-context',
                                                                                                                                         'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[default-provenance]': {'activation_phase': 'R2',
                                                                                                                                       'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-default-provenance',
                                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                       'owner_ref': 'form-context',
                                                                                                                                       'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[default-role]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-default-role',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[predicate-ports]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-predicate-ports',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'form-context',
                                                                                                                                    'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[predicate-frame]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-predicate-frame',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'form-context',
                                                                                                                                    'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[frame-signature]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-frame-signature',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'form-context',
                                                                                                                                    'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_communication_evidence_forgeries_fail_exact_sinks[reference-kind]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:communicative-roles-rehashed-communication-evidence-forgeries-fail-exact-sinks-reference-kind',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'form-context',
                                                                                                                                   'source_ast_sha256': 'bb0a1d0a524e297c55079fcebe7d7fca32917922055729b7158754f5ad172ed7'},
 'tests/test_foundation_communicative_roles.py::test_activation_rejects_malformed_communicative_row[extra-field]': {'activation_phase': 'R2',
                                                                                                                    'assertion_ref': 'assertion:communicative-roles-activation-rejects-malformed-communicative-row-extra-field',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'form-context',
                                                                                                                    'source_ast_sha256': '972691f5be76fdc2f7b8dd35bc772c4c1fd2a4a43baee9ab9180d4fe8d691ede'},
 'tests/test_foundation_communicative_roles.py::test_activation_rejects_malformed_communicative_row[required-actor]': {'activation_phase': 'R2',
                                                                                                                       'assertion_ref': 'assertion:communicative-roles-activation-rejects-malformed-communicative-row-required-actor',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'form-context',
                                                                                                                       'source_ast_sha256': '972691f5be76fdc2f7b8dd35bc772c4c1fd2a4a43baee9ab9180d4fe8d691ede'},
 'tests/test_foundation_communicative_roles.py::test_activation_rejects_malformed_communicative_row[concept-referent]': {'activation_phase': 'R2',
                                                                                                                         'assertion_ref': 'assertion:communicative-roles-activation-rejects-malformed-communicative-row-concept-referent',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'form-context',
                                                                                                                         'source_ast_sha256': '972691f5be76fdc2f7b8dd35bc772c4c1fd2a4a43baee9ab9180d4fe8d691ede'},
 'tests/test_foundation_communicative_roles.py::test_activation_rejects_malformed_communicative_row[wrong-predicate]': {'activation_phase': 'R2',
                                                                                                                        'assertion_ref': 'assertion:communicative-roles-activation-rejects-malformed-communicative-row-wrong-predicate',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'form-context',
                                                                                                                        'source_ast_sha256': '972691f5be76fdc2f7b8dd35bc772c4c1fd2a4a43baee9ab9180d4fe8d691ede'},
 'tests/test_foundation_communicative_roles.py::test_activation_rejects_malformed_communicative_row[reverse-role]': {'activation_phase': 'R2',
                                                                                                                     'assertion_ref': 'assertion:communicative-roles-activation-rejects-malformed-communicative-row-reverse-role',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'form-context',
                                                                                                                     'source_ast_sha256': '972691f5be76fdc2f7b8dd35bc772c4c1fd2a4a43baee9ab9180d4fe8d691ede'},
 'tests/test_foundation_communicative_roles.py::test_activation_rejects_malformed_communicative_row[missing-evidence-order]': {'activation_phase': 'R2',
                                                                                                                               'assertion_ref': 'assertion:communicative-roles-activation-rejects-malformed-communicative-row-missing-evidence-order',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'form-context',
                                                                                                                               'source_ast_sha256': '972691f5be76fdc2f7b8dd35bc772c4c1fd2a4a43baee9ab9180d4fe8d691ede'},
 'tests/test_foundation_communicative_roles.py::test_activation_rejects_malformed_communicative_row[nonlist-evidence-order]': {'activation_phase': 'R2',
                                                                                                                               'assertion_ref': 'assertion:communicative-roles-activation-rejects-malformed-communicative-row-nonlist-evidence-order',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'form-context',
                                                                                                                               'source_ast_sha256': '972691f5be76fdc2f7b8dd35bc772c4c1fd2a4a43baee9ab9180d4fe8d691ede'},
 'tests/test_foundation_communicative_roles.py::test_target_without_reviewed_control_cannot_match': {'activation_phase': 'R2',
                                                                                                     'assertion_ref': 'assertion:communicative-roles-target-without-reviewed-control-cannot-match',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                     'owner_ref': 'form-context',
                                                                                                     'source_ast_sha256': 'd0278a66859233a7959ea3d7363f8e0cb2a13df60d0007f33923ef9783834b9b'},
 'tests/test_foundation_communicative_roles.py::test_unseen_multiword_designation_source_geometry_is_bounded[en]': {'activation_phase': 'R2',
                                                                                                                    'assertion_ref': 'assertion:communicative-roles-unseen-multiword-designation-source-geometry-is-bounded-en',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'form-context',
                                                                                                                    'source_ast_sha256': '9cf93626e29ed95f1727cb7c16a1693c24998b6cb71fadc779ea5d73290c937d'},
 'tests/test_foundation_communicative_roles.py::test_unseen_multiword_designation_source_geometry_is_bounded[es]': {'activation_phase': 'R2',
                                                                                                                    'assertion_ref': 'assertion:communicative-roles-unseen-multiword-designation-source-geometry-is-bounded-es',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'form-context',
                                                                                                                    'source_ast_sha256': '9cf93626e29ed95f1727cb7c16a1693c24998b6cb71fadc779ea5d73290c937d'},
 'tests/test_foundation_communicative_roles.py::test_authenticated_event_alias_restart_inherits_roles_without_pack_write': {'activation_phase': 'R2',
                                                                                                                            'assertion_ref': 'assertion:communicative-roles-authenticated-event-alias-restart-inherits-roles-without-pack-write',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'form-context',
                                                                                                                            'source_ast_sha256': 'ac714c6849532be7a88d4ac480e223650895850d8e23ed0cc897c7f2c5a0fd15'},
 'tests/test_foundation_communicative_roles.py::test_post_activation_communication_does_not_enumerate_atoms': {'activation_phase': 'R2',
                                                                                                               'assertion_ref': 'assertion:communicative-roles-post-activation-communication-does-not-enumerate-atoms',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                               'owner_ref': 'form-context',
                                                                                                               'source_ast_sha256': 'a774df6eaa6f19bdde7a7e96b9e35330624747091e2ded21972552a3648ac7be'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_participant_primitive_requires_authentic_ownership[ports]': {'activation_phase': 'R2',
                                                                                                                           'assertion_ref': 'assertion:communicative-roles-rehashed-participant-primitive-requires-authentic-ownership-ports',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'form-context',
                                                                                                                           'source_ast_sha256': '8e06a0f8b0bf6939986e7a614e0bfda422c3ec56f2ff8c4a033b65694fd36b9f'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_participant_primitive_requires_authentic_ownership[provenance]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:communicative-roles-rehashed-participant-primitive-requires-authentic-ownership-provenance',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': '8e06a0f8b0bf6939986e7a614e0bfda422c3ec56f2ff8c4a033b65694fd36b9f'},
 'tests/test_foundation_communicative_roles.py::test_rehashed_participant_primitive_requires_authentic_ownership[signature]': {'activation_phase': 'R2',
                                                                                                                               'assertion_ref': 'assertion:communicative-roles-rehashed-participant-primitive-requires-authentic-ownership-signature',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'form-context',
                                                                                                                               'source_ast_sha256': '8e06a0f8b0bf6939986e7a614e0bfda422c3ec56f2ff8c4a033b65694fd36b9f'},
 'tests/test_foundation_communicative_roles.py::test_duplicate_communicative_construction_owner_is_rejected': {'activation_phase': 'R2',
                                                                                                               'assertion_ref': 'assertion:communicative-roles-duplicate-communicative-construction-owner-is-rejected',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                               'owner_ref': 'form-context',
                                                                                                               'source_ast_sha256': '3fe562ddcfcd979cf4f3c728cd789711a660e9b26c2715f37192c2200a6f66b3'},
 'tests/test_foundation_communicative_roles.py::test_removed_match_hints_do_not_authorize_false_predicate_evidence': {'activation_phase': 'R2',
                                                                                                                      'assertion_ref': 'assertion:communicative-roles-removed-match-hints-do-not-authorize-false-predicate-evidence',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'form-context',
                                                                                                                      'source_ast_sha256': 'b7feeb6ec70dd2e26b1721995dde9cbd90f2fd75cfd93a5f8324872440d9931f'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_predicate_cannot_borrow_authentic_alternative[input-ports]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:communicative-roles-selected-forged-predicate-cannot-borrow-authentic-alternative-input-ports',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'form-context',
                                                                                                                                   'source_ast_sha256': 'd3510f7d46a261d0e12c0da2f654ea1d766ff1db161c4a5263cb8a9bb8073f1f'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_predicate_cannot_borrow_authentic_alternative[output-ports]': {'activation_phase': 'R2',
                                                                                                                                    'assertion_ref': 'assertion:communicative-roles-selected-forged-predicate-cannot-borrow-authentic-alternative-output-ports',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                    'owner_ref': 'form-context',
                                                                                                                                    'source_ast_sha256': 'd3510f7d46a261d0e12c0da2f654ea1d766ff1db161c4a5263cb8a9bb8073f1f'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_predicate_cannot_borrow_authentic_alternative[provenance]': {'activation_phase': 'R2',
                                                                                                                                  'assertion_ref': 'assertion:communicative-roles-selected-forged-predicate-cannot-borrow-authentic-alternative-provenance',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                  'owner_ref': 'form-context',
                                                                                                                                  'source_ast_sha256': 'd3510f7d46a261d0e12c0da2f654ea1d766ff1db161c4a5263cb8a9bb8073f1f'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_predicate_cannot_borrow_authentic_alternative[frame]': {'activation_phase': 'R2',
                                                                                                                             'assertion_ref': 'assertion:communicative-roles-selected-forged-predicate-cannot-borrow-authentic-alternative-frame',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                                             'owner_ref': 'form-context',
                                                                                                                             'source_ast_sha256': 'd3510f7d46a261d0e12c0da2f654ea1d766ff1db161c4a5263cb8a9bb8073f1f'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_predicate_cannot_borrow_authentic_alternative[constraints]': {'activation_phase': 'R2',
                                                                                                                                   'assertion_ref': 'assertion:communicative-roles-selected-forged-predicate-cannot-borrow-authentic-alternative-constraints',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                   'owner_ref': 'form-context',
                                                                                                                                   'source_ast_sha256': 'd3510f7d46a261d0e12c0da2f654ea1d766ff1db161c4a5263cb8a9bb8073f1f'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_predicate_cannot_borrow_authentic_alternative[contribution-ref]': {'activation_phase': 'R2',
                                                                                                                                        'assertion_ref': 'assertion:communicative-roles-selected-forged-predicate-cannot-borrow-authentic-alternative-contribution-ref',
                                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                        'owner_ref': 'form-context',
                                                                                                                                        'source_ast_sha256': 'd3510f7d46a261d0e12c0da2f654ea1d766ff1db161c4a5263cb8a9bb8073f1f'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_reference_cannot_borrow_authentic_alternative[designation-input-ports]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:communicative-roles-selected-forged-reference-cannot-borrow-authentic-alternative-designation-input-ports',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'form-context',
                                                                                                                                               'source_ast_sha256': '4c3dd7b9727b7eed4e243efd64eecb6db3242ee6a82208f498a10fd7f266199c'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_reference_cannot_borrow_authentic_alternative[designation-output-ports]': {'activation_phase': 'R2',
                                                                                                                                                'assertion_ref': 'assertion:communicative-roles-selected-forged-reference-cannot-borrow-authentic-alternative-designation-output-ports',
                                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                                'source_ast_sha256': '4c3dd7b9727b7eed4e243efd64eecb6db3242ee6a82208f498a10fd7f266199c'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_reference_cannot_borrow_authentic_alternative[designation-constraints]': {'activation_phase': 'R2',
                                                                                                                                               'assertion_ref': 'assertion:communicative-roles-selected-forged-reference-cannot-borrow-authentic-alternative-designation-constraints',
                                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                               'owner_ref': 'form-context',
                                                                                                                                               'source_ast_sha256': '4c3dd7b9727b7eed4e243efd64eecb6db3242ee6a82208f498a10fd7f266199c'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_reference_cannot_borrow_authentic_alternative[designation-provenance]': {'activation_phase': 'R2',
                                                                                                                                              'assertion_ref': 'assertion:communicative-roles-selected-forged-reference-cannot-borrow-authentic-alternative-designation-provenance',
                                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                              'owner_ref': 'form-context',
                                                                                                                                              'source_ast_sha256': '4c3dd7b9727b7eed4e243efd64eecb6db3242ee6a82208f498a10fd7f266199c'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_reference_cannot_borrow_authentic_alternative[designation-contribution-ref]': {'activation_phase': 'R2',
                                                                                                                                                    'assertion_ref': 'assertion:communicative-roles-selected-forged-reference-cannot-borrow-authentic-alternative-designation-contribution-ref',
                                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                                    'owner_ref': 'form-context',
                                                                                                                                                    'source_ast_sha256': '4c3dd7b9727b7eed4e243efd64eecb6db3242ee6a82208f498a10fd7f266199c'},
 'tests/test_foundation_communicative_roles.py::test_selected_forged_reference_cannot_borrow_authentic_alternative[primitive-output-ports]': {'activation_phase': 'R2',
                                                                                                                                              'assertion_ref': 'assertion:communicative-roles-selected-forged-reference-cannot-borrow-authentic-alternative-primitive-output-ports',
                                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                              'owner_ref': 'form-context',
                                                                                                                                              'source_ast_sha256': '4c3dd7b9727b7eed4e243efd64eecb6db3242ee6a82208f498a10fd7f266199c'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[compatible-port]': {'activation_phase': 'R2',
                                                                                                                                'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-compatible-port',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'form-context',
                                                                                                                                'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[input-ports]': {'activation_phase': 'R2',
                                                                                                                            'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-input-ports',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'form-context',
                                                                                                                            'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[constraints]': {'activation_phase': 'R2',
                                                                                                                            'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-constraints',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'form-context',
                                                                                                                            'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[provenance]': {'activation_phase': 'R2',
                                                                                                                           'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-provenance',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'form-context',
                                                                                                                           'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[contribution-ref]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-contribution-ref',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[frame]': {'activation_phase': 'R2',
                                                                                                                      'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-frame',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'form-context',
                                                                                                                      'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[combined]': {'activation_phase': 'R2',
                                                                                                                         'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-combined',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'form-context',
                                                                                                                         'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'},
 'tests/test_foundation_communicative_roles.py::test_selected_role_action_requires_exact_contribution_owner[authentic-anchor]': {'activation_phase': 'R2',
                                                                                                                                 'assertion_ref': 'assertion:communicative-roles-selected-role-action-requires-exact-contribution-owner-authentic-anchor',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                 'owner_ref': 'form-context',
                                                                                                                                 'source_ast_sha256': 'd632baf9dab0bd2b16834f236e060c3cb701c8157ec95aeed90011dd02b9fdbf'}}

ROOT = Path(__file__).resolve().parents[1]


def _expected(actor, addressee, target="event:greeting"):
    app = SemanticApplication("candidate:independent", "op:event", target, (
        RoleBinding("role:actor", GroundedReference(actor)),
        RoleBinding("role:addressee", GroundedReference(addressee)),
    ))
    return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))


@pytest.mark.parametrize("surface,actor,addressee,target", (
    ("hello", "participant:user", "participant:system", "event:greeting"),
    ("hello Bob", "participant:user", "entity:bob", "event:greeting"),
    ("Alice hello", "entity:alice", "participant:system", "event:greeting"),
    ("Alice hello Bob", "entity:alice", "entity:bob", "event:greeting"),
    ("you hello Bob", "participant:system", "entity:bob", "event:greeting"),
    ("Alice hello you", "entity:alice", "participant:system", "event:greeting"),
    ("hello!", "participant:user", "participant:system", "event:greeting"),
    ("goodbye Bob.", "participant:user", "entity:bob", "event:farewell"),
), ids=("bare", "postfix", "prefix", "both", "participant-prefix", "participant-postfix", "terminal", "farewell"))
def test_public_communication_preserves_exact_roles(surface, actor, addressee, target, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "roles.db")
    try:
        result = runtime.process("session:communication", surface)
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == _expected(actor, addressee, target)
        assert not result.proposal.truncated
        assert runtime.stores.world.revision == 0
        assert result.realization_receipt is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation", ("compatible-port", "input-ports", "constraints", "provenance", "contribution-ref", "frame", "combined", "authentic-anchor"),
    ids=("compatible-port", "input-ports", "constraints", "provenance", "contribution-ref", "frame", "combined", "authentic-anchor"))
def test_selected_role_action_requires_exact_contribution_owner(mutation, tmp_path):
    """Changing binding action cannot bypass selected-record authentication."""
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "selected-role.db")
    try:
        index = runtime._owners["verification"].role_schema_index
        if mutation == "authentic-anchor":
            # Source-geometry component fixture, not designation acquisition.
            facts = tuple(DesignationFact.create(surface=s, target_ref=t, language="en") for s, t in (
                ("mira", "participant:user"), ("hello", "event:greeting"), ("Bob", "entity:bob")))
            pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
            builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, "mira hello Bob", facts=facts)
            index = builder.role_schema_index
        else:
            _, context = runtime.orient("session:selected-role", "hello Bob")
        program = runtime.proposal_model.propose(context).candidates[0].program
        good = next(c for c in context.contribution_slots if c.kind == "anchor" and c.target_ref == (
            "participant:user" if mutation == "authentic-anchor" else "entity:bob"))
        changes = {
            "compatible-port": {}, "input-ports": {"input_ports": ("role:actor",)},
            "constraints": {"constraints": (("unreviewed", "forged-anchor"),)},
            "provenance": {"provenance_refs": ("source:forged",)},
            "contribution-ref": {"contribution_ref": "contribution:forged"},
            "frame": {"constraints": (("frame_ref", "frame:event:farewell"),)},
            "combined": {"constraints": (("unreviewed", "forged-anchor"),),
                "provenance_refs": ("source:forged",), "contribution_ref": "contribution:forged"},
            "authentic-anchor": {},
        }[mutation]
        selected = good if mutation == "authentic-anchor" else _slot_with(good, output_ports=("role:addressee",), **changes)
        values = {name: getattr(context, name) for name in inspect.signature(ProposalContext.create).parameters
            if name != "config"}
        forged = ProposalContext.create(**{**values, "contribution_slots": context.contribution_slots
            if mutation == "authentic-anchor" else (*context.contribution_slots, selected)})
        pointers, actions = {}, []
        for original in program.actions:
            is_explicit_binding = original.action_type == "bind_reference" and original.source_unit_refs == good.source_unit_refs
            changed = ProgramAction.create(action_index=original.action_index,
                action_type="bind_role" if is_explicit_binding else original.action_type,
                arguments=(*original.arguments[:2], selected.slot_ref) if is_explicit_binding else tuple(
                    forged.context_ref if value == context.context_ref else value for value in original.arguments),
                source_unit_refs=original.source_unit_refs)
            pointers[original.action_ref] = changed.action_ref
            actions.append(changed)
        assignments = tuple(SourceAssignment.create(**{f.name: selected.slot_ref if f.name == "contribution_slot_ref"
            and a.source_unit_ref in good.source_unit_refs else "role" if f.name == "assignment_kind" and a.source_unit_ref in good.source_unit_refs
            else pointers.get(a.target_action_ref, a.target_action_ref) if f.name == "target_action_ref"
            else getattr(a, f.name) for f in fields(a) if f.name != "assignment_ref"}) for a in program.source_assignments)
        program = SemanticSwitchProgram.create(**{**{f.name: getattr(program, f.name) for f in fields(program)
            if f.name != "program_ref"}, "proposal_context_ref": forged.context_ref,
            "actions": tuple(actions), "source_assignments": assignments})
        assert good in forged.contribution_slots and selected in forged.contribution_slots
        assert any(type(m) is CommunicativeRoleMatch for m in index.matches(
            forged.designation_slots, forged.contribution_slots, forged.source_unit_spans))
        coverage = CoverageVerifier(role_schema_index=index).verify(forged, program)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        reconstructed = reconstruct_expected_expression(program, forged, role_schema_index=index)
        replay = _replay_program(program, forged, role_schema_index=index)
        if mutation == "authentic-anchor":
            assert not coverage.errors and not replay
            assert not isinstance(compiled, CompilationFailure)
            assert reconstructed == _expected("participant:user", "entity:bob")
        else:
            code = "communicative_role_correspondence"
            assert (any(e.code == code for e in coverage.errors),
                isinstance(compiled, CompilationFailure) and compiled.code == code,
                reconstructed is None, any(e.code == code for e in replay)) == (True, True, True, True)
    finally:
        runtime.stores.close()


def _swap_roles(program):
    swap = {"role:actor": "role:addressee", "role:addressee": "role:actor"}
    pointers, actions = {}, []
    for action in program.actions:
        arguments = action.arguments
        if action.action_type in {"bind_reference", "bind_role"}:
            arguments = (arguments[0], swap.get(arguments[1], arguments[1]), *arguments[2:])
        changed = ProgramAction.create(action_index=action.action_index, action_type=action.action_type,
            arguments=arguments, source_unit_refs=action.source_unit_refs)
        pointers[action.action_ref] = changed.action_ref
        actions.append(changed)
    assignments = tuple(SourceAssignment.create(**{f.name: pointers.get(a.target_action_ref, a.target_action_ref)
        if f.name == "target_action_ref" else swap.get(a.target_role_ref, a.target_role_ref)
        if f.name == "target_role_ref" else getattr(a, f.name) for f in fields(a) if f.name != "assignment_ref"})
        for a in program.source_assignments)
    return SemanticSwitchProgram.create(**{**{f.name: getattr(program, f.name) for f in fields(program)
        if f.name != "program_ref"}, "actions": tuple(actions), "source_assignments": assignments})


@pytest.mark.parametrize("surface", ("Alice hello Bob", "you hello Bob"), ids=("entities", "participant"))
def test_rehashed_reversed_communication_fails_exact_sinks(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "tamper.db")
    try:
        _, context = runtime.orient("session:tamper", surface)
        program = runtime.proposal_model.propose(context).candidates[0].program
        replacements = {r.slot_ref: _slot_with(r, compatible_roles=("role:actor", "role:addressee"))
            for r in context.reference_slots if r.source_unit_refs}
        replacements.update({c.slot_ref: _slot_with(c, output_ports=("role:actor", "role:addressee"))
            for c in context.contribution_slots if c.kind == "reference"})
        forged, program = _rehash_derivation(context, program, replacements)
        program = _swap_roles(program)
        index = runtime._owners["verification"].role_schema_index
        coverage = CoverageVerifier(role_schema_index=index).verify(forged, program)
        assert any(e.code == "communicative_role_correspondence" for e in coverage.errors)
        assert isinstance(SemanticExpressionCompiler(role_schema_index=index).compile(program, forged), CompilationFailure)
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert any(e.code == "communicative_role_correspondence" for e in _replay_program(program, forged, role_schema_index=index))
    finally:
        runtime.stores.close()


def test_public_session_reference_collision_preserves_situated_defaults(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "collision.db")
    try:
        for session in ("session:normal", "participant:system"):
            result = runtime.process(session, "hello")
            assert result.verification.selected_meaning.expression == _expected("participant:user", "participant:system")
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,surface,actor,addressee", (
    ("en", "velnora", "participant:user", "participant:system"),
    ("en", "Alice velnora", "entity:alice", "participant:system"),
    ("en", "velnora Bob", "participant:user", "entity:bob"),
    ("en", "Alice velnora Bob", "entity:alice", "entity:bob"),
    ("en", "I velnora Bob!", "participant:user", "entity:bob"),
    ("en", "Alice velnora you", "entity:alice", "participant:system"),
    ("es", "velnora", "participant:user", "participant:system"),
    ("es", "Alice velnora", "entity:alice", "participant:system"),
    ("es", "velnora Bob", "participant:user", "entity:bob"),
    ("es", "Alice velnora Bob", "entity:alice", "entity:bob"),
    ("es", "yo velnora Bob!", "participant:user", "entity:bob"),
    ("es", "Alice velnora t\u00fa", "entity:alice", "participant:system"),
), ids=("en-bare", "en-prefix", "en-postfix", "en-both", "en-participant-prefix", "en-participant-postfix",
        "es-bare", "es-prefix", "es-postfix", "es-both", "es-participant-prefix", "es-participant-postfix"))
def test_static_designation_source_geometry_preserves_multilingual_roles(language, surface, actor, addressee, tmp_path):
    """Static designation fixture, not authenticated alias acquisition."""
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "static.db")
    before = (ROOT / "data/languages" / language / "forms.json").read_bytes()
    facts = tuple(DesignationFact.create(surface=s, target_ref=t, language=language) for s, t in (
        ("Alice", "entity:alice"), ("Bob", "entity:bob"), ("velnora", "event:greeting")))
    try:
        builder, context = _static_composition_context(runtime.authority, runtime.stores, json.loads(before), surface, facts=facts)
        proposal = runtime.proposal_model.propose(context)
        result = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
        assert result.selected_meaning is not None
        assert result.selected_meaning.expression == _expected(actor, addressee)
        matches = tuple(m for m in builder.role_schema_index.matches(context.designation_slots,
            context.contribution_slots, context.source_unit_spans) if type(m) is CommunicativeRoleMatch)
        assert len(matches) == 1
        assert matches[0].source_actor_explicit == any(b.role == "role:actor" for b in matches[0].bindings)
        assert not proposal.truncated and proposal.explored_states <= 16
        assert runtime.stores.world.revision == 0
        assert (ROOT / "data/languages" / language / "forms.json").read_bytes() == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", (
    "\"hello\"", "Mary said hello", "you can hello", "you not hello", "hello and goodbye",
    "hello Bob Alice", "hello, Bob", "hello. goodbye", "hello?", "hello because goodbye",
), ids=("quotation", "reported", "modality", "polarity", "coordination", "extra-referent", "vocative",
        "compound", "question", "causal"))
def test_unsupported_source_never_acquires_direct_construction(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "unsupported.db")
    try:
        _, context = runtime.orient("session:unsupported", surface)
        index = runtime._owners["verification"].role_schema_index
        assert not any(type(m) is CommunicativeRoleMatch for m in index.matches(
            context.designation_slots, context.contribution_slots, context.source_unit_spans))
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case,code", (
    ("missing", "communicative_schema_index_missing"),
    ("stale", "communicative_schema_index_stale"),
    ("different-pack", "communicative_role_correspondence"),
), ids=("missing", "stale", "different-pack"))
def test_wrong_activated_index_rejects_direct_construction_at_exact_sinks(case, code, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "index.db")
    try:
        _, context = runtime.orient("session:index", "hello Bob")
        program = runtime.proposal_model.propose(context).candidates[0].program
        index = runtime._owners["verification"].role_schema_index
        if case == "missing":
            index = None
        elif case == "stale":
            index = copy(index)
            object.__setattr__(index, "authority_content_hash", "authority-content:wrong")
        else:
            pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
            pack["language"] = "different-pack"
            index = ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, RuntimeConfig.release())
        assert any(e.code == code for e in CoverageVerifier(role_schema_index=index).verify(context, program).errors)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, context)
        assert isinstance(compiled, CompilationFailure)
        assert compiled.code == code
        assert reconstruct_expected_expression(program, context, role_schema_index=index) is None
        assert any(e.code == code for e in _replay_program(program, context, role_schema_index=index))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation,code", (
    ("assignments", "communicative_role_correspondence"),
    ("reference-provenance", "communicative_role_correspondence"),
    ("default-provenance", "communicative_role_correspondence"),
    ("default-role", "communicative_role_correspondence"),
    ("predicate-ports", "communicative_schema_match_missing"),
    ("predicate-frame", "communicative_schema_match_missing"),
    ("frame-signature", "communicative_role_correspondence"),
    ("reference-kind", "communicative_role_correspondence"),
), ids=("assignments", "reference-provenance", "default-provenance", "default-role", "predicate-ports",
        "predicate-frame", "frame-signature", "reference-kind"))
def test_rehashed_communication_evidence_forgeries_fail_exact_sinks(mutation, code, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "forgery.db")
    try:
        _, context = runtime.orient("session:forgery", "hello Bob")
        program = runtime.proposal_model.propose(context).candidates[0].program
        replacements = {}
        if mutation == "reference-provenance":
            row = next(r for r in context.reference_slots if r.source_unit_refs)
            replacements[row.slot_ref] = _slot_with(row, provenance_refs=("source:forged",))
        elif mutation.startswith("default-"):
            row = next(r for r in context.reference_slots if r.resolution_kind == "situated_participant")
            replacements[row.slot_ref] = _slot_with(row, **({"provenance_refs": ("orientation:forged", *row.provenance_refs[1:])}
                if mutation == "default-provenance" else {"compatible_roles": ("role:addressee",)}))
        elif mutation.startswith("predicate-"):
            row = next(c for c in context.contribution_slots if c.kind == "predicate")
            replacements[row.slot_ref] = _slot_with(row, **({"input_ports": tuple(reversed(row.input_ports))} if mutation == "predicate-ports"
                else {"constraints": (("frame_ref", "frame:event:farewell"),)}))
        elif mutation == "frame-signature":
            row = context.application_frames[0]
            replacements[row.slot_ref] = _slot_with(row, required_roles=row.optional_roles, optional_roles=row.required_roles)
        elif mutation == "reference-kind":
            row = next(r for r in context.reference_slots if r.source_unit_refs)
            replacements[row.slot_ref] = _slot_with(row, target_kind="participant")
        forged, program = _rehash_derivation(context, program, replacements)
        if mutation == "assignments":
            selected = next(a for a in program.actions if a.action_type == "bind_reference" and not a.source_unit_refs)
            assignments = tuple(SourceAssignment.create(**{f.name: selected.action_ref if f.name == "target_action_ref"
                and a.assignment_kind == "reference" else getattr(a, f.name) for f in fields(a) if f.name != "assignment_ref"})
                for a in program.source_assignments)
            program = SemanticSwitchProgram.create(**{**{f.name: getattr(program, f.name) for f in fields(program)
                if f.name != "program_ref"}, "source_assignments": assignments})
        index = runtime._owners["verification"].role_schema_index
        assert any(e.code == code for e in CoverageVerifier(role_schema_index=index).verify(forged, program).errors)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        assert isinstance(compiled, CompilationFailure) and compiled.code == code
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert any(e.code == code for e in _replay_program(program, forged, role_schema_index=index))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation", ("extra-field", "required-actor", "concept-referent", "wrong-predicate", "reverse-role", "missing-evidence-order", "nonlist-evidence-order"),
    ids=("extra-field", "required-actor", "concept-referent", "wrong-predicate", "reverse-role", "missing-evidence-order", "nonlist-evidence-order"))
def test_activation_rejects_malformed_communicative_row(mutation, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "row.db")
    try:
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
        row = pack["application_role_orders"]["communicative_actor_event_addressee"]
        if mutation == "extra-field":
            row["unreviewed"] = True
        elif mutation == "required-actor":
            row["evidence_order"][0]["cardinality"] = "required"
        elif mutation == "concept-referent":
            row["evidence_order"][0]["target_kinds"] = ["concept", "participant"]
        elif mutation == "wrong-predicate":
            row["evidence_order"][1]["target_kind"] = "relation_type"
        elif mutation == "reverse-role":
            row["evidence_order"][0]["role"] = "role:addressee"
        elif mutation == "missing-evidence-order":
            del row["evidence_order"]
        else:
            row["evidence_order"] = "unreviewed"
        with pytest.raises(ValueError, match="communicative"):
            ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, RuntimeConfig.release())
    finally:
        runtime.stores.close()


def test_target_without_reviewed_control_cannot_match(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "control.db")
    facts = (DesignationFact.create(surface="velnora", target_ref="event:learn_alias", language="en"),)
    try:
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, "velnora", facts=facts)
        assert runtime.authority.communicative_control_for_target("event:learn_alias") is None
        assert not any(type(m) is CommunicativeRoleMatch for m in builder.role_schema_index.matches(
            context.designation_slots, context.contribution_slots, context.source_unit_spans))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,surface", (
    ("en", "Alice frelora senora Bob"), ("es", "Alice frelora senora Bob"),
), ids=("en", "es"))
def test_unseen_multiword_designation_source_geometry_is_bounded(language, surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "multiword.db")
    try:
        pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
        facts = tuple(DesignationFact.create(surface=s, target_ref=t, language=language) for s, t in (
            ("Alice", "entity:alice"), ("Bob", "entity:bob"), ("frelora senora", "event:greeting")))
        builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, surface, facts=facts)
        proposal = runtime.proposal_model.propose(context)
        result = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
        assert result.selected_meaning is not None
        assert result.selected_meaning.expression == _expected("entity:alice", "entity:bob")
        assert not proposal.truncated
    finally:
        runtime.stores.close()


def test_authenticated_event_alias_restart_inherits_roles_without_pack_write(tmp_path):
    import secrets
    from cemm_authoritative_hybrid.r3_learning import AliasReviewVerifier
    from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, R3EffectGateway
    from tests.test_foundation_alias_publication import _signed
    from tests.test_foundation_continuation_binding import _setup
    runtime, _, pending = _setup(tmp_path)
    before = (ROOT / "data/languages/en/forms.json").read_bytes()
    try:
        proposal = runtime.process(pending.session_ref, "learn velnora means hello")
        plan = proposal.response_meaning.learning_plan
        assert plan.target_ref == "event:greeting"
        assert plan.expected_target_kinds == ("event_type",)
        stores = runtime.stores
        secret = secrets.token_bytes(32)
        binding = stores.learning_store_binding
        journal = stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key)
        grant = {"proposal_key": proposal.effect_receipt.idempotency_key,
            "proposal_journal_ref": journal["entry"]["journal_ref"],
            "proposal_receipt_ref": proposal.effect_receipt.receipt_ref,
            "plan_ref": plan.plan_ref, "source_obligation_ref": pending.obligation_ref,
            "source_query_ref": pending.source_query_ref,
            "source_journal_ref": journal["entry"]["request_payload"]["learning_source_journal"]["entry"]["journal_ref"],
            "surface": "velnora", "target_ref": "event:greeting", "language": "en",
            "reviewer_ref": "reviewer:test", "policy_ref": runtime.authority.learning_contract_for_source(
                "op:event", "event:learn_alias").review_policy_ref,
            "key_ref": "key:test-reviewer", "store_binding": binding,
            "nonce": secrets.token_hex(24), "expires_at_turn": pending.expires_turn_index}
        verifier = AliasReviewVerifier(key=secret, key_ref=grant["key_ref"], reviewer_ref=grant["reviewer_ref"],
            policy_ref=grant["policy_ref"], store_binding=binding)
        gateway = R3EffectGateway(stores, AdapterRegistry(), authority=runtime.authority, review_verifier=verifier)
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert len(receipt.committed_fact_refs) == 1
        revision = stores.world.revision
    finally:
        runtime.stores.close()
    reopened = load_runtime(ROOT, profile="development", store_path=tmp_path / "continuation.db")
    try:
        for surface, actor, addressee in (("velnora Bob", "participant:user", "entity:bob"),
            ("Alice velnora", "entity:alice", "participant:system"), ("you velnora Bob", "participant:system", "entity:bob")):
            result = reopened.process("session:alias-restart", surface)
            assert result.verification.selected_meaning.expression == _expected(actor, addressee)
            assert not result.proposal.truncated
        assert reopened.stores.world.revision == revision
        assert (ROOT / "data/languages/en/forms.json").read_bytes() == before
    finally:
        reopened.stores.close()


def test_post_activation_communication_does_not_enumerate_atoms(tmp_path, monkeypatch):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "bounded.db")
    class NoEnumeration(dict):
        def __iter__(self):
            pytest.fail("normal construction enumerated authority atoms")
        def values(self):
            pytest.fail("normal construction enumerated authority atom values")
        def items(self):
            pytest.fail("normal construction enumerated authority atom items")
    try:
        monkeypatch.setattr(runtime.authority, "atoms", NoEnumeration(runtime.authority.atoms))
        _, context = runtime.orient("session:bounded", "Alice hello Bob")
        index = runtime._owners["verification"].role_schema_index
        matches = tuple(m for m in index.matches(context.designation_slots, context.contribution_slots,
            context.source_unit_spans) if type(m) is CommunicativeRoleMatch)
        assert len(matches) == 1
        proposal = runtime.proposal_model.propose(context)
        verified = ExactProgramVerifier(role_schema_index=index).verify_candidates(proposal, context)
        assert verified.selected_meaning.expression == _expected("entity:alice", "entity:bob")
        assert not proposal.truncated and proposal.explored_states <= 16
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation,code", (
    ("ports", "communicative_evidence_invalid"), ("provenance", "communicative_evidence_invalid"),
    ("signature", "communicative_schema_match_missing"),
), ids=("ports", "provenance", "signature"))
def test_rehashed_participant_primitive_requires_authentic_ownership(mutation, code, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "primitive.db")
    try:
        _, context = runtime.orient("session:primitive", "you hello Bob")
        program = runtime.proposal_model.propose(context).candidates[0].program
        row = next(c for c in context.contribution_slots if c.kind == "reference" and c.constraints[0][0] == "participant")
        changed = _slot_with(row, **({"input_ports": ("role:actor",)} if mutation == "ports"
            else {"provenance_refs": ("source:forged",)} if mutation == "provenance"
            else {"constraints": (("participant", "unreviewed"),)}))
        forged, program = _rehash_derivation(context, program, {row.slot_ref: changed})
        index = runtime._owners["verification"].role_schema_index
        assert any(e.code == code for e in CoverageVerifier(role_schema_index=index).verify(forged, program).errors)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        assert isinstance(compiled, CompilationFailure) and compiled.code == code
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert any(e.code == code for e in _replay_program(program, forged, role_schema_index=index))
    finally:
        runtime.stores.close()


def test_duplicate_communicative_construction_owner_is_rejected(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "duplicate.db")
    try:
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
        orders = pack["application_role_orders"]
        del orders["label_designation_query"]
        orders["unreviewed_second_owner"] = orders["communicative_actor_event_addressee"]
        with pytest.raises(ValueError, match="communicative.*one owner"):
            ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, RuntimeConfig.release())
    finally:
        runtime.stores.close()


def test_removed_match_hints_do_not_authorize_false_predicate_evidence(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "hints.db")
    try:
        _, context = runtime.orient("session:hints", "hello Bob")
        program = runtime.proposal_model.propose(context).candidates[0].program
        predicate = next(c for c in context.contribution_slots if c.kind == "predicate")
        frame = context.application_frames[0]
        replacements = {predicate.slot_ref: _slot_with(predicate, constraints=(("frame_ref", "frame:event:farewell"),)),
            frame.slot_ref: _slot_with(frame, provenance_refs=tuple(r for r in frame.provenance_refs
                if not r.startswith(("reviewed_communicative", "control:"))))}
        forged, program = _rehash_derivation(context, program, replacements)
        index = runtime._owners["verification"].role_schema_index
        code = "communicative_schema_match_missing"
        assert any(e.code == code for e in CoverageVerifier(role_schema_index=index).verify(forged, program).errors)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        assert isinstance(compiled, CompilationFailure) and compiled.code == code
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert any(e.code == code for e in _replay_program(program, forged, role_schema_index=index))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation", ("input-ports", "output-ports", "provenance", "frame", "constraints", "contribution-ref"),
    ids=("input-ports", "output-ports", "provenance", "frame", "constraints", "contribution-ref"))
def test_selected_forged_predicate_cannot_borrow_authentic_alternative(mutation, tmp_path):
    """Retain the good predicate; fully rehash the actually selected bad slot."""
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "selected-predicate.db")
    try:
        _, context = runtime.orient("session:selected-predicate", "hello Bob")
        program = runtime.proposal_model.propose(context).candidates[0].program
        good = next(c for c in context.contribution_slots if c.kind == "predicate")
        changes = {
            "input-ports": {"input_ports": tuple(reversed(good.input_ports))},
            "output-ports": {"output_ports": (*good.output_ports, "role:predicate")},
            "provenance": {"provenance_refs": ("source:forged",)},
            "frame": {"constraints": (("frame_ref", "frame:event:farewell"),)},
            "constraints": {"constraints": (*good.constraints, ("unreviewed", "predicate"))},
            "contribution-ref": {"contribution_ref": "contribution:forged"},
        }[mutation]
        bad = _slot_with(good, **changes)
        values = {name: getattr(context, name) for name in inspect.signature(ProposalContext.create).parameters
            if name != "config"}
        forged = ProposalContext.create(**{**values, "contribution_slots": (*context.contribution_slots, bad)})
        pointers, actions = {}, []
        for original in program.actions:
            changed = ProgramAction.create(action_index=original.action_index, action_type=original.action_type,
                arguments=tuple(forged.context_ref if value == context.context_ref else value for value in original.arguments),
                source_unit_refs=original.source_unit_refs)
            pointers[original.action_ref] = changed.action_ref
            actions.append(changed)
        assignments = tuple(SourceAssignment.create(**{f.name: bad.slot_ref if f.name == "contribution_slot_ref"
            and a.assignment_kind == "predicate" else pointers.get(a.target_action_ref, a.target_action_ref)
            if f.name == "target_action_ref" else getattr(a, f.name) for f in fields(a) if f.name != "assignment_ref"})
            for a in program.source_assignments)
        program = SemanticSwitchProgram.create(**{**{f.name: getattr(program, f.name) for f in fields(program)
            if f.name != "program_ref"}, "proposal_context_ref": forged.context_ref,
            "actions": tuple(actions), "source_assignments": assignments})
        index = runtime._owners["verification"].role_schema_index
        assert good in forged.contribution_slots and bad in forged.contribution_slots
        assert any(type(m) is CommunicativeRoleMatch for m in index.matches(
            forged.designation_slots, forged.contribution_slots, forged.source_unit_spans))
        code = "communicative_role_correspondence"
        coverage = CoverageVerifier(role_schema_index=index).verify(forged, program)
        assert any(e.code == code for e in coverage.errors)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        assert isinstance(compiled, CompilationFailure) and compiled.code == code
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert any(e.code == code for e in _replay_program(program, forged, role_schema_index=index))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface,mutation,code", (
    ("hello Bob", "input-ports", "communicative_role_correspondence"),
    ("hello Bob", "output-ports", "communicative_role_correspondence"),
    ("hello Bob", "constraints", "communicative_role_correspondence"),
    ("hello Bob", "provenance", "communicative_role_correspondence"),
    ("hello Bob", "contribution-ref", "communicative_role_correspondence"),
    ("hello you", "output-ports", "communicative_role_correspondence"),
), ids=("designation-input-ports", "designation-output-ports", "designation-constraints", "designation-provenance",
        "designation-contribution-ref", "primitive-output-ports"))
def test_selected_forged_reference_cannot_borrow_authentic_alternative(surface, mutation, code, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "selected-reference.db")
    try:
        _, context = runtime.orient("session:selected-reference", surface)
        program = runtime.proposal_model.propose(context).candidates[0].program
        good = next(c for c in context.contribution_slots if c.kind == "reference")
        reference = next(r for r in context.reference_slots if r.source_unit_refs)
        changes = {
            "input-ports": {"input_ports": ("role:actor",)},
            "output-ports": {"output_ports": ("role:actor",)},
            "constraints": {"constraints": (("resolution_kind", "participant_deixis"),)},
            "provenance": {"provenance_refs": ("source:forged",)},
            "contribution-ref": {"contribution_ref": "contribution:forged"},
        }[mutation]
        bad = _slot_with(good, **changes)
        row = _slot_with(reference, provenance_refs=tuple(bad.slot_ref if r == good.slot_ref else r
            for r in reference.provenance_refs))
        first, program = _rehash_derivation(context, program, {reference.slot_ref: row})
        values = {name: getattr(first, name) for name in inspect.signature(ProposalContext.create).parameters
            if name != "config"}
        forged = ProposalContext.create(**{**values, "contribution_slots": (*first.contribution_slots, bad)})
        pointers, actions = {}, []
        for original in program.actions:
            changed = ProgramAction.create(action_index=original.action_index, action_type=original.action_type,
                arguments=tuple(forged.context_ref if value == first.context_ref else value for value in original.arguments),
                source_unit_refs=original.source_unit_refs)
            pointers[original.action_ref] = changed.action_ref
            actions.append(changed)
        assignments = tuple(SourceAssignment.create(**{f.name: bad.slot_ref if f.name == "contribution_slot_ref"
            and a.assignment_kind == "reference" else pointers.get(a.target_action_ref, a.target_action_ref)
            if f.name == "target_action_ref" else getattr(a, f.name) for f in fields(a) if f.name != "assignment_ref"})
            for a in program.source_assignments)
        program = SemanticSwitchProgram.create(**{**{f.name: getattr(program, f.name) for f in fields(program)
            if f.name != "program_ref"}, "proposal_context_ref": forged.context_ref,
            "actions": tuple(actions), "source_assignments": assignments})
        index = runtime._owners["verification"].role_schema_index
        assert good in forged.contribution_slots and bad in forged.contribution_slots
        assert any(type(m) is CommunicativeRoleMatch for m in index.matches(
            forged.designation_slots, forged.contribution_slots, forged.source_unit_spans))
        assert any(e.code == code for e in CoverageVerifier(role_schema_index=index).verify(forged, program).errors)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        assert isinstance(compiled, CompilationFailure) and compiled.code == code
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert any(e.code == code for e in _replay_program(program, forged, role_schema_index=index))
    finally:
        runtime.stores.close()
