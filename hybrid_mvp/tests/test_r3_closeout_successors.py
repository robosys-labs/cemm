"""R3 behavioral successors for frozen predecessor assertion lineages."""
from dataclasses import FrozenInstanceError

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import OrientationProjector
from cemm_authoritative_hybrid.dialogue import (
    DialogueObligation,
    DialogueObligationManager,
    FocusStore,
    GoalArbiter,
    GoalSelection,
    ObligationKind,
    ReferenceConstraints,
    ReferenceResolver,
    VerifiedSemanticFocus,
)
from cemm_authoritative_hybrid.persistence import RevisionPin, memory_stores
from tests.r3_successor_contracts import assert_successor_contract

__cemm_test_inventory__ = {'tests/test_r3_closeout_successors.py::test_r3_successor_02c8a3b9911859bf0353': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-stale-revision-restart-stale-revision-restart-at-orient',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'f8504d7c1164b6506a71907a862793fad7984e4d2c5f699e8bcd7fd8fdef042a',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_no_stale_revision_reentry_precedes_unadmitted_effect'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_03c11585efe153827572': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-mixed-verified-and-unverified',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '49c454edd4846189946025d8acfb26eb6384547238a1cdc4903f2feb9383c788',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_mixed_verified_and_unverified'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_061076ac8035b501bcbe': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-names-and-aliases-alias-query-preserves-semantic-refs',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '1fb3a676d8c893824bed3ea6658a99262588243119e014b8babee2c49010f72b',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestNamesAndAliases::test_alias_query_preserves_semantic_refs'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_06b6c58163e318ee4963': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'd0ca597e8276839f2ea9988672cd8bd471a63c9fb8cfd460b15d73631518588e',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.UNSUPPORTED]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_07e5438a8190c02f528b': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-acquisition-requires-cap-learn',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '81f8e523974083ee4c221dc82243c60335486a86e40a8ddda88cc73b3ef3ed35',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_acquisition_requires_cap_learn'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_087fa7741523c766b339': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'ea496a4fc9c05386e9debd51dc086dd7b439f81191de7c136314d43705ba66a4',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.UNKNOWN]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_0a59b0d3bb8df37b4930': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-goal-arbiter-prefers-obligation-over-goal',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '0082fb4e3ad369bb5b8ca42e28b7949fa9caa924b8da834f3ac937cc29c162be',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_goal_arbiter_prefers_obligation_over_goal'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_0e8f1a78989177d083df': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-that-resolves-most-recent-proposition',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '8de9ab10a1978c3fa1ccf53dc176f2343b085d7c9e8770f6be71a1479ac5fdd6',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_that_resolves_most_recent_proposition'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_117636df56c528015c99': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-proposal',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'bd46979f4f913c7466bc3d6273b2bf72568e528aec53663a38d6df4a4edebc59',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_retains_canonical_proposal'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_12b14e6f836c432edc1d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-denial-denial-produces-gap-receipt',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '83d9efdb85a907db3570b02c4fb883c2119329ac90904ae5229cd85956ff2c65',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestDenial::test_denial_produces_gap_receipt'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_1312031edfe593132fe2': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-state-intervals-past-state-query',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2947fa506b90779cb26aaa8113abce24f89f56c77dd6f85c977ab2309abec5be',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestStateIntervals::test_past_state_query'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_173c654f2b620a70fc62': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-greeting-and-operational-condition-greeting-produces-resolved-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '25ee257780064b25f3f7d76eb184db115fcd8a093946ce1751dcb8b337209a9d',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestGreetingAndOperationalCondition::test_greeting_produces_resolved_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_1a25374d0e03ea86a7a7': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:query-engine-meaning-description-is-composed-from-grounded-structure',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e8bbc27121e2e858a0503abca242fe01ee10c871c50f318163345922b9e8ab5c',
                                                                                  'supersedes_node_id': 'tests/test_query_engine.py::test_meaning_description_is_composed_from_grounded_structure[what-expected1]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_1e4717dec0e04f377686': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-fulfill-marks-obligation-with-completion-receipt',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'de381b336e9c487013ba11acf1162b7ad3d4933902d91addbe6e700a76bbd626',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_fulfill_marks_obligation_with_completion_receipt'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_1ebc6d8ac2f5ba9c3561': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-that-resolves-prior-verified-proposition',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '5844d159b291239ca477980a6fed986a18d732afc0333a36e0cb930da2f0b094',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_that_resolves_prior_verified_proposition'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_1f9c96bd25efd3eac759': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-incompatible-multi-anchor-incompatible-multi-anchor-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2c502a7b9a10d27d1f4efcedd31d770bbbe1f21c5d3d18ebe65e06f8853df363',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestIncompatibleMultiAnchor::test_incompatible_multi_anchor_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_22e25b96ca44e4637599': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-orientation-projector-uses-focus-store',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '70c8b702b57a301c5e340f0ca50126a1112ccd818197e4fa0d7c26226d22afba',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_orientation_projector_uses_focus_store'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_23ab4f6d79fd50bbf874': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:six-phase-runtime-second-cycle-increments-world-revision',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '30806fa6ea69946391527ee4902e29238ab9be8d799154f4d53fd968a0523e35',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_disabled_effect_owner_does_not_advance_world_revision'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_26c3172feb21ecab47de': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-trace-with-durations',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '50e67e41933009342ca45ea0ffbf9e6ce8a6324dd6b2ae2ae318716edbe68c97',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_trace_is_observational_with_bounded_durations'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_27ba73e12b88ad9fe2eb': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-what-did-you-say-resolves-verified-system-speech',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e9077055d54ac7c040835573e87c680924748daddd7ccf48a3bb5fd0772b4075',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_what_did_you_say_resolves_verified_system_speech'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_2ab331d5cc04d7bcd286': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-atomic-surface-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4ffdf979532121ff7036faebdff24943528838fbf0a970d886e025d435774500',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestAtomicMeaningLookup::test_atomic_surface_produces_cycle[hi]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_2ac780c8d0d83aa505e5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-response-meaning',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'a817b0905a4892f89c7665c22b6f6feb2048b723675aed0223036a2569a21b7e',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_has_no_response_before_evaluation'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_2e2b21568a0be2e3afc5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-no-hidden-fallback-missing-owner-is-not-clarification',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '67073428cd23c5cd0f95a0b0a12c98241b65338e360798e4dc046dd508e29033',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestNoHiddenFallback::test_missing_owner_is_not_clarification'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_2f5fe16467edee9c42fa': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-committed-effect-survives-realization-failure-committed-effect-remains-journaled',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'd9b932a18caddc2acc8ebb0c3bf7b1247d3f499577f05706e86110eae7d2239b',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCommittedEffectSurvivesRealizationFailure::test_committed_effect_remains_journaled'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_2fb6478bb03f0913af9e': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'ee683615591fb11d8f08bb4e0c781a32bba3739153904c7b953faf1959f25795',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.OPERATION_FAILED]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_2fe822715d9bff6bdc8a': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'b6fb9c539d902e8fe012fe1ad37bf38ebb255febfc701f06cc74382533b1b0d3',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[desired]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_30cfc728a8ddc6af448e': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-focus-store-recent-entries',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e95eefeb7b63c817f000d021b005622ef04f21e37e413fda3f2f4dddeccd1521',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_focus_store_recent_entries'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_31ec79e7f8c1d6efaaf8': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-realization-failure-realization-failure-produces-gap-receipt',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '72ab944e06ab75ce2dafd8109044abfa5e51550e9bc24aa4afa84518a836f347',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestRealizationFailure::test_realization_failure_produces_gap_receipt'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_346d127a52d319a4df50': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-state-intervals-current-state-query',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'a7f1d08e88bc2de8d70ba15deb0a2b2e1171a60e741b9918e09f472c63f94738',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestStateIntervals::test_current_state_query'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_37b5fe8ca6b81d8e435d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-evaluation',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'd026ce04d56ef4ac8dda3cbae058e57978d722e7ba2f901827f72c75d644e6a0',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_defers_evaluation_to_exact_later_owner'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_389bab3bb934932a6895': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-atomic-surface-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '1a7c5cb2be3ec295f7a447b07e23c97bb120823bc783d9ce1774413a3b54dfbe',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestAtomicMeaningLookup::test_atomic_surface_produces_cycle[what]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_3b4cfeb86fa0db77def5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-dialogue-obligation-accepts-typed-kinds',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'f7fec01fd0c94d5cb98cdd4e426edc8104425658d2e5e2767a7bcf744d7d4b12',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_dialogue_obligation_accepts_typed_kinds[evidence_request]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_3d4560bbd2cba740ad1d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '3b03d7aa851fdc4df5cf704240a45f5063be98bf564bbf65d477d46dea7592e7',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.PARTIAL]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_3dcf1ce99d768a4a387e': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:response-meaning-test-response-meaning-precedes-language-response-meaning-has-all-fields',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '7f31e845b548c0a0cd4805a516bcb9dc50c95e569f7660d67e1b7776c38063af',
                                                                                  'supersedes_node_id': 'tests/test_response_meaning.py::TestResponseMeaningPrecedesLanguage::test_response_meaning_has_all_fields'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_3e9b731d0d9a6f6936bc': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:r1-episode-strict-codec',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '492c5b37ededf6878dd3cce186b31c5ee0926c8037df5997dd43d75dcc69d353'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_3e9c0f82c70d10847ce9': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-attributed-speech-attributed-speech-does-not-become-world-truth',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '3deda331ed2001d96122296e462876debc94b5bdd7ab9116e63489ee1b743dfb',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestAttributedSpeech::test_attributed_speech_does_not_become_world_truth'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_43ba22a660043d569a04': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9fcee41da7797e2d00b70ba7fe7424445b0b636e9f4e971d8047015e4081bb98',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.DENIED]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_448444eb09d013ea4ad4': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-acquisition-plan-mismatch-rejected',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '6e279c9a527645035c31721ecb3ac0bcb06290e79a5c36f0b1cf2e389d3460c7',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_acquisition_plan_mismatch_rejected'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_4618c9de8b3438873934': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-what-did-you-say-resolves-to-most-recent-system-speech',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'd9f9e7996e4abec651fe6e2c8497a4d5e4f7315d592a21e62f5afeaac421a91c',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_what_did_you_say_resolves_to_most_recent_system_speech'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_496f6e6d7dbfe89cf019': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:six-phase-runtime-injected-program-runs-through-six-phase-owners',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '43802afd2699257c3772885adc448c37432dd37747a2c870769e9a38b074cd50',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_injected_program_reaches_every_admitted_owner_then_stops'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_4ae8e030ad8426ba19b5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-focus-store-starts-empty',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '6d194798ab9ce5e7b5620500e8cff3e42ff7762bceeb85168b2db594db35d2d4',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_focus_store_starts_empty'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_4b9d01eec01554c58a47': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-names-and-aliases-name-query-produces-response-meaning',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '7d06272ae4be3c939270b59242d2f1ccfcfe0e6d2cfb1412206d8f434c4ccd6e',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestNamesAndAliases::test_name_query_produces_response_meaning'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_4d6ad497849e46c6dfea': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:learning-distinctions-one-pending-learning-obligation',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2cb811bd1df7c3bdc5f7fe257c6b826c5ea103e9a05908bfddec3a3d77ba8291',
                                                                                  'supersedes_node_id': 'tests/test_learning_distinctions.py::test_one_pending_learning_obligation'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_4ddeb418d2556ef7d962': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-demonstratives-demonstrative-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'c52c0540fd9be726c97f8c936ee48e27a97f06ad339ff66f01a1e7b60c4b169b',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestDemonstratives::test_demonstrative_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_4e18303fa2e5f85519e1': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-goal-selection-is-frozen',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4d8430aa7618d4120c2b292d06790f831cc62809ff6ed63af374a7c557a5f7b1',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_goal_selection_is_frozen'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_512bcc3c6fba9795ed02': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-acquisition-requires-reviewer-authorization',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '451e10c49c4ccea0a12d19c264e51e991d38bc73bf4a2d4d4defea789dcf2f28',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_acquisition_requires_reviewer_authorization'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_59d62df8f6399e561544': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:learning-distinctions-designation-commit-consumes-plan',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '16e00ca9582ad67bc9b3f57dbd783f17a8b8b4932bf15faf86d8fac86057829e',
                                                                                  'supersedes_node_id': 'tests/test_learning_distinctions.py::test_designation_commit_consumes_plan'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_5b46fb3213f566e27ea3': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:r1-runtime-exceptions-propagate',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '08968c35fb5e03c8a6156b1aba85627410a28db7637a252b509b198f971fd116',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_programming_exceptions_propagate_without_shape_adaptation'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_5c62c09726631356d222': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-orientation',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '57ceddc8b68ac6b489dc7af7738b37c427e3481c4b0da870ad69ff8dcf770ffd',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_retains_canonical_orientation'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_5cd9e27e5bab778ace82': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-acquisition-preserves-compatibility-hash',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '49fa8641c7b1f403e563f9e57608bcb654592f5937feca5a0dd2126c73c1c390',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_acquisition_preserves_compatibility_hash'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_5ce43fa19074d3b15ca4': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:query-engine-meaning-description-is-composed-from-grounded-structure',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2bee27250bc256349d88920bd9fd6679d12a859d6ae4f884d890e4c2d9d12204',
                                                                                  'supersedes_node_id': 'tests/test_query_engine.py::test_meaning_description_is_composed_from_grounded_structure[does-expected2]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_60b5af589ecd1e402709': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:learning-distinctions-lookup-does-not-create-designation',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '0e786643c147f7517f33262ac02b32c776da611cb422d7b6c2a56f7f87b9b349',
                                                                                  'supersedes_node_id': 'tests/test_learning_distinctions.py::test_lookup_does_not_create_designation'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_630ff30ab8ec8b014d0b': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-capability-capability-query-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e4b83718cbb63f7f09cf3e3ee990b1316518e00e4dcf8281ad85b5fab5e5f747',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCapability::test_capability_query_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_647fedb72fbbcfbf2a87': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-reported-speech-does-not-become-world-truth-reported-speech-world-query-unknown',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '8076572210b8c35a8f3915036c1323510d34c51e19c4f3dc6de282a692fbeb6e',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestReportedSpeechDoesNotBecomeWorldTruth::test_reported_speech_world_query_unknown'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_6494fb26adb069b3b7e5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:query-engine-generic-family-rule-lowering-supports-marriage-with-trace',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4b39031c64494573f5a48abe21b38ed7ff8af650d12c01478cf907af822ccb5d',
                                                                                  'supersedes_node_id': 'tests/test_query_engine.py::test_generic_family_rule_lowering_supports_marriage_with_trace'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_6634463067f7cafa0051': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-resolution-bindings-contain-ref-to-resolved',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'b582bbdbc5410606bff18fe1f6f55cdc26c2985d0c4d092e9c779816cdbef5e0',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_resolution_bindings_contain_ref_to_resolved'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_6d677dc551ceca07cc5b': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-person-constraint-filters-by-participant',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'd0f48228843b27f202f04c56888139fbe40c719ee22821135cdada65345646ed',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_person_constraint_filters_by_participant'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_6da536de8c4c1ceb8564': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-multiple-cycles-restart-preserves-revisions-across-multiple-cycles',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'aef1606d53d6c94022c7e84dd2702885b1395f59ef349defb1c0899c76b7c842',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_stable_revisions_across_multiple_cycles'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_6eef143e2a8dbd7da3fb': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '3973e97c34d2bed7762b2982ba24df37d113b7d4115989f96703fbeeddab3e90',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[simulated]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_70660ec884ab5d824ecf': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-world-revision',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4498918d6f79d9d0f113b70193a97ddbb996fe00d40006a151522b88fb493e99',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_world_revision_without_admitted_effect'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_71cd05f2b1cf13d72b58': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-atomic-surface-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '469aaead464687d3fd1202ccab05ecb790ead42537915599d2ac08dfed6b24dd',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestAtomicMeaningLookup::test_atomic_surface_produces_cycle[does]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_74266f64499fe015c1b5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-newly-learned-alias-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9cd023b941f0d3d9728dac1a5f2825291813bba2feb6ffffec5cccae11779351',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestAtomicMeaningLookup::test_newly_learned_alias_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_765ec49d46eaedeb18e0': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-dialogue-obligation-carries-source-query-and-contract',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2b308a0f186bb980602f66cc16bb786164373fb952dccc77f11c191273b5de9f',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_dialogue_obligation_carries_source_query_and_contract'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_792373ec0692ff7b4f7d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-learning-continuation-learning-continuation-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'eb34547ac5b480fda7ce00ff0c18021373ed965be9d7140282c74adcf17d3704',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestLearningContinuation::test_learning_continuation_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_79703ee34fd786bdb486': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-effect-revision',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'c68539b8005406486ad7bbfadb3b9536a553c2692da058fe10f213be9e5ed969',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_effect_revision_without_admitted_effect'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_7c8a7603e86ed244d114': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-successful-operation-successful-operation-increments-world-revision',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'c87aea8ed8e8b71db328b8337a1efa9bd14b3d5d0936885860659ba2790a7ff3',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestSuccessfulOperation::test_successful_operation_increments_world_revision'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_7e270e6990d7880d264d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:learning-distinctions-no-public-install-rules',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '56bca0c84ece03e0026e304f264e14f60f1a5e71c51236bf7981c94c219a3ad6',
                                                                                  'supersedes_node_id': 'tests/test_learning_distinctions.py::test_no_public_install_rules'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_7ef04063a04af8833514': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-greeting-and-operational-condition-operational-condition-has-revision-pin',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4dd0593eb809d5da8a6192aa9c8e910f2ff4818855c215d01060e494b7ba1313',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestGreetingAndOperationalCondition::test_operational_condition_has_revision_pin'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_8240da7c2f121cbcfc14': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-corrections-supersede-without-deleting-provenance-correction-status',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'f1923cde6fefd9742e7d87b32e373be54cea1dc588f6053820f3104fa9877d80',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestCorrectionsSupersedeWithoutDeletingProvenance::test_correction_status'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_829c535a40e12927bf97': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9b463466eead76b896752b5c52cdb33c705279e18466a245ccdd1b5fb8ed9dd6',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.CONFLICT]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_868520aaf5f0d5d8601c': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-adapter-failure-adapter-failure-produces-gap-receipt',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '0236064d63742720afe6a1d339227f6f4de00a4fc4b7ae09b82b7c76f1a1f956',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestAdapterFailure::test_adapter_failure_produces_gap_receipt'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_86faa75790d71aaa138b': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '1e9afeaca74be564295158626d77247df3ce82b14ba8d7b3ae6825348444348c',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[quoted]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_873b881d81e9b56ee8b7': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-revision-pin-fields',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '74033a5c1646299e4e35ef093091c2e496b19e77b5ac8210b5b950080b3b1585',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_every_revision_pin_dimension'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_8bf5349ade7a922ffb28': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:six-phase-runtime-trace-off-still-resolves',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'f3d99cdc4e36bef62a46803f812d39422eac3c07cc390da88eaa459df3c4806d',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_trace_off_preserves_selected_cycle_material'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_8d08917fa702cb9b2fed': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:query-engine-observe-records-facts',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '49e798311544da1aec6b1ffc255288fd2c1c64777f6599d46faf7b6658d4fcc8',
                                                                                  'supersedes_node_id': 'tests/test_query_engine.py::test_observe_records_facts'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_8d46f2d4f8a82b11d71c': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9237a7af49c4f8280086ae9bff44d4f8135c342d38286801f8fa7e206e6f315c',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.REALIZATION_FAILED]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_8de40dd01498141881a5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-unresolved-ref-returns-none',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '07e375615194fef185a8ba1da9ad359f6c637d10a0950ff6b02c74edb87b314e',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_unresolved_ref_returns_none'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_8e5b08c7cdc04e85c277': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:r1-runtime-trace-observational',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'efa9bed9a0af9fcca620722fe710b810140de7a9801497f89f4ecf04a83e294c',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_trace_is_observational_and_cycle_identity_is_stable'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_91f33f163e6a10e410b7': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-dialogue-obligation-accepts-typed-kinds',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'a03cdd172260bfaf346d57f3adbea77b34cbe9c56854b598cb95435f5ee4eb24',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_dialogue_obligation_accepts_typed_kinds[learning_answer]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_9536463b82ad4c736e8a': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-modality-query-mode-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '5ae4e088c356c776af33a822ccf4e62a4ea1203ca737dde362d0e2408bb3cc39',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestModality::test_query_mode_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_9737c160af466856feaf': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-idempotency-restart-does-not-re-invoke-completed-effect',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2882b2abf3c0d9058751b2038203ca2edae010b93a54cbbd320cacabc241facd',
                                                                                  'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartIdempotency::test_restart_does_not_re_invoke_completed_effect'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_977ebbadf7168d551a31': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:response-meaning-test-response-meaning-precedes-language-denied-status-maps-to-deny-action',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'ecd48c47dbbe47db5e2d7c3aade90a917ebc4811bc97719cf333f9f5e364bb32',
                                                                                  'supersedes_node_id': 'tests/test_response_meaning.py::TestResponseMeaningPrecedesLanguage::test_denied_status_maps_to_deny_action'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_9837994441bbb5b0183d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-observed-claims-with-evidence-are-admitted-observed-without-evidence-is-contested',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '625f994ae74aa4246401aee155ee58e998660040a746530c63b3d3f140cbb1b6',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestObservedClaimsWithEvidenceAreAdmitted::test_observed_without_evidence_is_contested'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_989bedf3d53929a6a3e8': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:response-meaning-test-response-meaning-precedes-language-response-builder-cannot-inspect-input-words',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4c307dd70e8e8a531c4d55775590accc8cc3b64792d7597eddd3a7d0f449e895',
                                                                                  'supersedes_node_id': 'tests/test_response_meaning.py::TestResponseMeaningPrecedesLanguage::test_response_builder_cannot_inspect_input_words'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_998c38e96c4506267f43': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-demonstratives-that-demonstrative-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'a89a06b46ffd582adadd57a5b2591fe0eabbf87285b6e26ae4890e4cdd500a41',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestDemonstratives::test_that_demonstrative_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_9eff2e971f959a40f142': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:six-phase-runtime-phase-receipts-have-named-phases-not-stage-numbers',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '33cd10f37ca5a4ee2401fd559188952a23bc52f899c117f23983b18e8493bbcc',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_phase_receipts_use_semantic_names_not_stage_numbers'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_a35b386efc1b5d62d530': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-goal-arbiter-ignores-satisfied-obligations',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '5e01c1325f326cd93c1b3acdc5cb1c7fc1bad7d4545dca1d1cae84798a09319e',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_goal_arbiter_ignores_satisfied_obligations'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_a3c7e653cf515659a7a6': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-committed-effect-committed-effect-remains-journaled-after-restart',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e6feb79d996024e034b8dd93e55294b91940b9a2337bdeb1ec5de2357a585999',
                                                                                  'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartCommittedEffect::test_committed_effect_remains_journaled_after_restart'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_a5dea97d747501c03ddb': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-kind-constraint-filters-by-kind',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'd1d2d4e459251d4219b03870fd05cc9bdc8ee3be1ef530da922fa8df12d29405',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_kind_constraint_filters_by_kind'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_a6877b3557b842cee518': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-what-did-you-say-what-did-you-say-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'f26bf74f555b99b49b8af678e2da4a2adca364d72f436581bd39eaa40dce60d0',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestWhatDidYouSay::test_what_did_you_say_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_a7535250c38166db9516': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:response-meaning-test-response-meaning-precedes-language-response-meaning-precedes-language',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'b2a4108e6de384335c72df73dfb459242c7e52d516fd70fd86aead9af687865e',
                                                                                  'supersedes_node_id': 'tests/test_response_meaning.py::TestResponseMeaningPrecedesLanguage::test_response_meaning_precedes_language'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_a85edba372926159baca': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-fulfilled-learning-allows-new-learning',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'fbd7192675b284f8554336d40fc8c6557b9cc7917053cd8083b5c414acc6854e',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_fulfilled_learning_allows_new_learning'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ac8ed838a7083c66f1e4': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-recency-constraint-limits-candidates',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '3adf9bae650996cc6af61615d33bb69390074763e1beb9ce33bdd5192b553bfe',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_recency_constraint_limits_candidates'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_acb0ed90038c0bce5e74': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-focus-store-accumulates-across-turns',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '52a6f19cc759409f21a9ee7b987b65b9284fc379ca18dc772056fc62af468425',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_focus_store_accumulates_across_turns'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ae3ce54649dca81d1f24': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-one-invalid-definition-rejects-entire-acquisition',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'a64f0751f07b7b4a6dd555c4df3034ed7026bd693fd1e78a3d28bf872131b87a',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_one_invalid_definition_rejects_entire_acquisition'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b0e60c540b0dfdbf9db0': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:six-phase-runtime-gap-receipt-is-none-on-resolved-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4e15185f0165cadbc93db474b61076f19dec41aeb288ff554792871415a422f7',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_selected_cycle_has_exact_later_owner_gap_until_r3'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b248e4945e9a868ee84c': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-verified-user-proposition-enters-focus',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9a95a3f5a7e4ff2fbdea41069ea624a48ff3ec5bd4bf7feeb89fc4dd40da5f91',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_verified_user_proposition_enters_focus'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b3e455c6c3aafd588648': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-non-learning-obligations-coexist',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'adb876e9aebafcc752384c7f07fa6b40d19821e131a8b61628a371eb05cd9e25',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_non_learning_obligations_coexist'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b48619272bc7c008bae8': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-fulfilling-non-learning-does-not-consume-learning',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '5baf03c84ff4b3d5686389bac4f2eb7db26880182d5c76e7ec6ae69e68d8832f',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_fulfilling_non_learning_does_not_consume_learning'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b4d0d67b952a4c0d71fe': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:r1-slice-b-runtime-receipts-bind-orientation-content',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '31cf98cb378d7832c85f5ececdf96ea012b184b92be8421d29774c01abd27a83',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_receipts_bind_exact_orientation_and_context_refs'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b650ca7318ae30576ef7': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '27b99faf56a622554a6f18078ac7e8aa2267472228e5d6bb5bbc74a6017392f1',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.AMBIGUOUS]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b767ac63d32d8299b00e': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-admission-is-policy-derived-admission-carries-policy-ref',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e10eb02dd237c41492a269e33a8c11139eaae5e5cb2a26c48313f6b1097a9a20',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestAdmissionIsPolicyDerived::test_admission_carries_policy_ref'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b7a1255e5e8232dfa402': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:learning-distinctions-untrusted-teaching-is-attributed-only',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'db0d4961552aabec0942d1e698dacd738552542c5bdd4a00066c2c2994bf7207',
                                                                                  'supersedes_node_id': 'tests/test_learning_distinctions.py::test_untrusted_teaching_is_attributed_only'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_b84479b75b9548b571b7': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-ui-intent-label-has-no-control-authority',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '6d77633e7c70b11c12de180d8d7464e9714300c0ac5200557af222ff1512a3b0',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_ui_intent_label_has_no_control_authority'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_be0bc997b98fb4dd9ace': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '066466310dc301d78e78d7e195a65bad8defde06e112a7fc48e25309c820ad56',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[believed]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_be210355a7860538c47c': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-dialogue-obligation-accepts-typed-kinds',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'dbd75d72835850c275e8bd40d414ccf340696a88d838e70df027be4ba1737a92',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_dialogue_obligation_accepts_typed_kinds[operation_resolution]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_be58b79b365d977533c9': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:learning-distinctions-meaning-lookup-does-not-mutate',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '98ba3fa65046dd7588396a90f82d154462fc34019f68d02c8ba6600477b225f3',
                                                                                  'supersedes_node_id': 'tests/test_learning_distinctions.py::test_meaning_lookup_does_not_mutate'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_bef2e803029d9c46f884': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:query-engine-meaning-description-is-composed-from-grounded-structure',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'a87e7f628c4b87156f78b1be284642b5c430be7ec4059751f0023a72a5ab05d8',
                                                                                  'supersedes_node_id': 'tests/test_query_engine.py::test_meaning_description_is_composed_from_grounded_structure[hi-expected0]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_c18205d9c0f40deb8080': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-reordered-questions-reordered-question-same-cycle-structure',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e3e251bfcdea3fa1ef47289638459ab1a06a1c68f64202bd871b47ffebd00882',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestReorderedQuestions::test_reordered_question_same_cycle_structure'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_c40d59f24966f4fa8bd1': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-attributed-speech-attributed-denial-under-contrast',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '28ad4a654040ba8782efdbac31d88ff9e82e92f621923347e13e5997f5885f12',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestAttributedSpeech::test_attributed_denial_under_contrast'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_c7b1f7079a3fe5c96275': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-dialogue-obligation-is-frozen',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2fae250c3d0b6e9889a39aa87bb1a59dba96b88f503332f3027901c717b1421b',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_dialogue_obligation_is_frozen'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_cb8ad9a437e9ab6f1679': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:r1-selected-stops-at-r3',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'ad3391df13a2ca995685ca175f4df9197232afc614b3c3dec73ba3478539bc3d',
                                                                                  'supersedes_node_id': 'tests/test_r1_runtime_path.py::test_r1_selected_meaning_stops_at_exact_later_owner_gap'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ce67b625850e1d0b8f06': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-goal-arbiter-selects-higher-priority-obligation',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'aaf03b86adc83f7a3af187627adf7f18bc04146bd3037e602e095bc71c1539e4',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_goal_arbiter_selects_higher_priority_obligation'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_cf1ea0498148f19cc17c': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:gap-matrix-every-cycle-status-is-reachable',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '8b782fd3f1c38b91c5c7e734bf4ffbba5add38f335c8a51ec676786402473379',
                                                                                  'supersedes_node_id': 'tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.RESOURCE_UNAVAILABLE]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_cf71b98771079a5ffa86': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-polysemy-polysemous-surface-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e35fd835f2a0253700139d931acd85304cb153d00181f40de1a73f50fc44e9ae',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestPolysemy::test_polysemous_surface_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_d1c5dbf99de9415b8519': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-only-one-learning-obligation-may-exist',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'b3446140faf3e353e2e2147ef407dcd33bbd64f341ef55c1b13aa6e8349093f2',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_only_one_learning_obligation_may_exist'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_d3129dc396cacffc2e8d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-reviewed-generic-definitions-publish-one-linked-generation',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e37959fba20e7a890808c6ee512b2a47cf5f315af468b290fcae2205b7118d45',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_reviewed_generic_definitions_publish_one_linked_generation'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_d335a36b78de5c78ae48': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-acquisition-conversational-wording-cannot-select-policy',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '5f1c17e059f1d7e2158e6e6844b4db5026e6bb43cd347d9515d789f7b3c9c28b',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_acquisition_conversational_wording_cannot_select_policy'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_d4770b48f1d95b0a2161': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-memory-consistency-consecutive-cycles-preserve-revision-pins',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'f0ea62c43232191af7237dfef9f42901f8cb62bcc3af01a8dd7d238fe17b32f5',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_consecutive_cycles_preserve_revision_pins_without_effect'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_d73b27aab098023a9867': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'c5f76ecaafe6366c54f770cf60c2525e665de23ca0e3d0568371bab6f6779b88',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[predicted]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_dc84231f7f90a715b69f': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-focus-store-stores-verified-refs',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '92c41e76cc6585d15af5f5191de82f56038d4f04f2eb33881aeb259927870588',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_focus_store_stores_verified_refs'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_dcac0e8e494facbd9d3f': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:synonym-acquisition-acquisition-consumes-plan',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'c8fb93a2d746b8cab995f081dc1916248f58c5a5bb472fce7efce5610ece55cd',
                                                                                  'supersedes_node_id': 'tests/test_synonym_acquisition.py::test_acquisition_consumes_plan'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_de6989568e516bea8aed': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:query-engine-semantic-description-never-reads-internal-ref-name',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4bba880911ef33b8b83c3b61f457db309905a5bfe8bec62a222815bf0a039876',
                                                                                  'supersedes_node_id': 'tests/test_query_engine.py::test_semantic_description_never_reads_internal_ref_name'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_de74cf5c0852c48aa4b5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-observed-claims-with-evidence-are-admitted-observed-with-evidence-is-admitted',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4d483bca211f2604a58865f87660d5105425d3b6758c93f4e01d3d077bc73fdc',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestObservedClaimsWithEvidenceAreAdmitted::test_observed_with_evidence_is_admitted'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_decaeee068cfd77411c0': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-goal-arbiter-idle-when-nothing-pending',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9a57165f0874ec2bc0ef8d15238653a380eaf15fd1820977a711b33df3fdcabf',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_goal_arbiter_idle_when_nothing_pending'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_df4e7f0c6066c9fc02cf': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-admission-is-policy-derived-admission-cannot-be-requested-by-token',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '7008d23a9a6b1516cb6b317b1e4cea6bb43373c0375108da449edce84b0744f7',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestAdmissionIsPolicyDerived::test_admission_cannot_be_requested_by_token'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_e0fc12f50525a8aa7d0f': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-correction-correction-produces-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'c2419a460f0fbb04ee13bb725ca593d2d66bb9305cff2797754626976ca3e87c',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCorrection::test_correction_produces_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_e163cfcc344eddf14b3b': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-dialogue-obligation-accepts-typed-kinds',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '2876cb846bc6b5a62d1668a7b9e891902807915f517fbc91f4442f8efed3ffe9',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_dialogue_obligation_accepts_typed_kinds[clarification]'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_e1d049d841566398e976': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-alternatives-below-margin-are-preserved',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '0264e0a93e2409161e31e094ec9d97cdc9d242778d3e163cbc9165e645a38da1',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_alternatives_below_margin_are_preserved'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_e2effe1dca9264717301': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-verification',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '119375368b80d38f517544cda44fca48b98dbd1c6e298dc6de7ed1c998455635',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_retains_canonical_verification'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_e77fbfa5288e26050075': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:recursive-inference-recursive-inference-with-unseen-synonym',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '78fd787c5d5c3d2a7b6ddd96aa55649f3bbb5c98dff303b275058689e70b0390',
                                                                                  'supersedes_node_id': 'tests/test_recursive_inference.py::test_recursive_inference_with_unseen_synonym'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_e7a30b650ce6517f401a': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-verified-semantic-focus-is-frozen',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'ab56f8c0c8146c882c4cfd6bde936a16eb9946fbe3f33a5b1eb09814abe4a704',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_verified_semantic_focus_is_frozen'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_e8164c03ba5a45f4c73a': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-pending-returns-unfulfilled-obligations',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '4b7928862005e02f982c36d840cd8bcf736e41c951a075bd0c227f629de243f6',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_pending_returns_unfulfilled_obligations'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ea3d1eb00bf28f853d92': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-reported-speech-does-not-become-world-truth-reported-speech-placement-mode',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '33c26e69b477ebe7ed93e916dee6153755839263682c65f96ed91adee5bd68ab',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestReportedSpeechDoesNotBecomeWorldTruth::test_reported_speech_placement_mode'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ec8f7eda4b6dc2aa92fc': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-focus-verified-output-enters-focus',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9021b2940d5e3e56f27dfae992676f595810ef3060ea4621af78ecfacefd8d29',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_focus.py::test_verified_output_enters_focus'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ed763dea9d599d0845d8': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:response-meaning-test-response-meaning-precedes-language-response-meaning-is-frozen',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '9599f27a060e4da3eed4a97b7f55b1cbec9add5208df0da89278077034aa0403',
                                                                                  'supersedes_node_id': 'tests/test_response_meaning.py::TestResponseMeaningPrecedesLanguage::test_response_meaning_is_frozen'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ef3349ae724cbc5de2f5': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-person-first-filters-to-user',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '6c6f31209971ea81e17c76b54acea3603c857b6724d1566a1de506d008ab2465',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_person_first_filters_to_user'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ef9d0b1bf1ba3fe1618e': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:query-engine-existential-witness-is-proof-local',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '747423808464b01e2300a245683fad5695f8157b67e7f6403ec5536aa0a398cb',
                                                                                  'supersedes_node_id': 'tests/test_query_engine.py::test_existential_witness_is_proof_local'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_f30dd96a383dcb1f702d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-family-inference-family-lesson-acquisition-and-marriage-query',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'ab6b93eebdda5c316635e1016ecf77b2b29fdef19fc88f55f423648ed3b68b22',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestFamilyInference::test_family_lesson_acquisition_and_marriage_query'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_f4441486b4cb53c5c9ee': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:restart-e2e-test-restart-cycle-result-structure-cycle-result-after-restart-has-all-artifacts',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'e3f8b9189a4b35d1e8b51a0881da589fbe8f959917c28a405bd1fd3d9f5e4bd1',
                                                                                  'supersedes_node_id': 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_after_reopen_contains_only_admitted_artifacts'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_f82ead85935f7cb8640d': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:epistemic-admission-test-reported-speech-does-not-become-world-truth-reported-speech-admission-is-attributed',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '0f905da2965b81232870b767361bf40cf325ee61eccad985df2f9649eb1a281c',
                                                                                  'supersedes_node_id': 'tests/test_epistemic_admission.py::TestReportedSpeechDoesNotBecomeWorldTruth::test_reported_speech_admission_is_attributed'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_faaf36e1601c7306d355': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:cognitive-loop-e2e-test-modality-simulation-mode-cycle',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'aca1f384a01d1bbc2cfe364ecd51c65ebb8d1945007e1479db8b03ebb023ad29',
                                                                                  'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestModality::test_simulation_mode_cycle'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_fd3d8d92c3cd8dbd7b9b': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:dialogue-obligations-learning-obligation-alongside-non-learning',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '6748d62a3a7a366babb6a7550a1476081227b1e473fe0a4dc732554221be6947',
                                                                                  'supersedes_node_id': 'tests/test_dialogue_obligations.py::test_learning_obligation_alongside_non_learning'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_fdc717e6c26ffcec5598': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:r1-episode-verified-meaning-separation',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': '0d71658ff54e26a0d1989f8193d0cf7bc6d9b4469e131d606459f776099c9146'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_fdf57c758cf49833fadd': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:discourse-reference-what-did-you-say-does-not-resolve-user-speech',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'c96e5cd724b653e28990cafd377ce3e016fa4bc87ee362e16476c8522990e6d2',
                                                                                  'supersedes_node_id': 'tests/test_discourse_reference.py::test_what_did_you_say_does_not_resolve_user_speech'},
 'tests/test_r3_closeout_successors.py::test_r3_successor_ffb56b3b17f5ce2d5a7f': {'activation_phase': 'R3',
                                                                                  'assertion_ref': 'assertion:learning-distinctions-conversational-wording-cannot-select-reviewer-policy',
                                                                                  'diagnostic_role': 'phase',
                                                                                  'introduced_by_task': 'R3-Closeout-Behavioral-Migration',
                                                                                  'source_ast_sha256': 'f85d5dfd6c43e866da1779da8d47da7f3d54061a619ec7e2942fcf0f35410942',
                                                                                  'supersedes_node_id': 'tests/test_learning_distinctions.py::test_conversational_wording_cannot_select_reviewer_policy'}}

def test_r3_successor_868520aaf5f0d5d8601c() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-adapter-failure-adapter-failure-produces-gap-receipt')

def test_r3_successor_71cd05f2b1cf13d72b58() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-atomic-surface-produces-cycle')

def test_r3_successor_2ab331d5cc04d7bcd286() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-atomic-surface-produces-cycle')

def test_r3_successor_389bab3bb934932a6895() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-atomic-surface-produces-cycle')

def test_r3_successor_74266f64499fe015c1b5() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-atomic-meaning-lookup-newly-learned-alias-produces-cycle')

def test_r3_successor_c40d59f24966f4fa8bd1() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-attributed-speech-attributed-denial-under-contrast')

def test_r3_successor_3e9c0f82c70d10847ce9() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-attributed-speech-attributed-speech-does-not-become-world-truth')

def test_r3_successor_630ff30ab8ec8b014d0b() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-capability-capability-query-produces-cycle')

def test_r3_successor_2f5fe16467edee9c42fa() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-committed-effect-survives-realization-failure-committed-effect-remains-journaled')

def test_r3_successor_e0fc12f50525a8aa7d0f() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-correction-correction-produces-cycle')

def test_r3_successor_4ddeb418d2556ef7d962() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-demonstratives-demonstrative-produces-cycle')

def test_r3_successor_998c38e96c4506267f43() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-demonstratives-that-demonstrative-produces-cycle')

def test_r3_successor_12b14e6f836c432edc1d() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-denial-denial-produces-gap-receipt')

def test_r3_successor_f30dd96a383dcb1f702d() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-family-inference-family-lesson-acquisition-and-marriage-query')

def test_r3_successor_173c654f2b620a70fc62() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-greeting-and-operational-condition-greeting-produces-resolved-cycle')

def test_r3_successor_7ef04063a04af8833514() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-greeting-and-operational-condition-operational-condition-has-revision-pin')

def test_r3_successor_1f9c96bd25efd3eac759() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-incompatible-multi-anchor-incompatible-multi-anchor-produces-cycle')

def test_r3_successor_792373ec0692ff7b4f7d() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-learning-continuation-learning-continuation-produces-cycle')

def test_r3_successor_9536463b82ad4c736e8a() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-modality-query-mode-cycle')

def test_r3_successor_faaf36e1601c7306d355() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-modality-simulation-mode-cycle')

def test_r3_successor_061076ac8035b501bcbe() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-names-and-aliases-alias-query-preserves-semantic-refs')

def test_r3_successor_4b9d01eec01554c58a47() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-names-and-aliases-name-query-produces-response-meaning')

def test_r3_successor_2e2b21568a0be2e3afc5() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-no-hidden-fallback-missing-owner-is-not-clarification')

def test_r3_successor_cf71b98771079a5ffa86() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-polysemy-polysemous-surface-produces-cycle')

def test_r3_successor_31ec79e7f8c1d6efaaf8() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-realization-failure-realization-failure-produces-gap-receipt')

def test_r3_successor_c18205d9c0f40deb8080() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-reordered-questions-reordered-question-same-cycle-structure')

def test_r3_successor_346d127a52d319a4df50() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-state-intervals-current-state-query')

def test_r3_successor_1312031edfe593132fe2() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-state-intervals-past-state-query')

def test_r3_successor_7c8a7603e86ed244d114() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-successful-operation-successful-operation-increments-world-revision')

def test_r3_successor_a6877b3557b842cee518() -> None:
    assert_successor_contract('cycle', 'assertion:cognitive-loop-e2e-test-what-did-you-say-what-did-you-say-produces-cycle')

def _verified_focus(
    suffix: str,
    *,
    session_ref: str = "session:focus",
    participant_ref: str = "participant:system",
    expression_refs: tuple[str, ...] | None = None,
    entity_refs: tuple[str, ...] = (),
    event_refs: tuple[str, ...] = (),
) -> VerifiedSemanticFocus:
    return VerifiedSemanticFocus.create(
        expression_refs=(f"expression:{suffix}",) if expression_refs is None else expression_refs,
        entity_refs=entity_refs,
        event_refs=event_refs,
        salience_proof_refs=(f"proof:trusted-fixture:{suffix}",),
        participant_ref=participant_ref,
        session_ref=session_ref,
        turn_ref=f"turn:{suffix}",
        revision_pin=RevisionPin(
            "authority:test", 1, 2, 3, 4, "model:test"
        ),
    )


def test_r3_successor_acb0ed90038c0bce5e74() -> None:
    store = FocusStore()
    first = _verified_focus("accumulated-first")
    second = _verified_focus("accumulated-second")
    store.add(first)
    store.add(second)
    assert store.entries == (first, second)
    assert tuple(row.focus_ref for row in store.entries) == (
        first.focus_ref,
        second.focus_ref,
    )
    assert store.refs == frozenset(
        {first.expression_refs[0], second.expression_refs[0]}
    )

def test_r3_successor_30cfc728a8ddc6af448e() -> None:
    store = FocusStore()
    first = _verified_focus("recent-first", session_ref="session:primary")
    other = _verified_focus("recent-other", session_ref="session:other")
    latest = _verified_focus("recent-latest", session_ref="session:primary")
    for focus in (first, other, latest):
        store.add(focus)
    assert store.recent_entries(2) == (other, latest)
    assert store.recent_entries(2, session_ref="session:primary") == (
        first,
        latest,
    )

def test_r3_successor_4ae8e030ad8426ba19b5() -> None:
    store = FocusStore()
    assert store.entries == ()
    assert store.refs == frozenset()
    assert "expression:absent" not in store.refs

def test_r3_successor_dc84231f7f90a715b69f() -> None:
    store = FocusStore()
    focus = _verified_focus(
        "typed-refs",
        expression_refs=("expression:one", "expression:two"),
        entity_refs=("entity:door",),
        event_refs=("event:greeting",),
    )
    store.add(focus)
    assert store.refs == frozenset(
        {
            "expression:one",
            "expression:two",
            "entity:door",
            "event:greeting",
        }
    )
    assert "entity:absent" not in store.refs

def test_r3_successor_03c11585efe153827572() -> None:
    assert_successor_contract('focus', 'assertion:dialogue-focus-mixed-verified-and-unverified')

def test_r3_successor_ec8f7eda4b6dc2aa92fc() -> None:
    assert_successor_contract('focus', 'assertion:dialogue-focus-verified-output-enters-focus')

def test_r3_successor_e7a30b650ce6517f401a() -> None:
    focus = _verified_focus("frozen")
    with pytest.raises(FrozenInstanceError):
        focus.expression_refs = ("expression:changed",)

def test_r3_successor_b248e4945e9a868ee84c() -> None:
    assert_successor_contract('focus', 'assertion:dialogue-focus-verified-user-proposition-enters-focus')


def _dialogue_obligation(
    kind: ObligationKind,
    *,
    suffix: str,
    created_turn_index: int = 1,
    expires_turn_index: int = 10,
    completion_receipt_ref: str | None = None,
) -> DialogueObligation:
    return DialogueObligation.create(
        kind=kind,
        session_ref=f"session:{suffix}",
        source_query_ref=f"query:{suffix}",
        expected_answer_contract_ref=f"contract:answer:{suffix}",
        created_turn_index=created_turn_index,
        expires_turn_index=expires_turn_index,
        source_decision_ref=f"decision:{suffix}",
        completion_receipt_ref=completion_receipt_ref,
        revision_pin=RevisionPin(
            "authority:test", 1, 2, 3, 4, "model:test"
        ),
    )


def test_r3_successor_e163cfcc344eddf14b3b() -> None:
    obligation = _dialogue_obligation(
        ObligationKind.CLARIFICATION, suffix="clarification"
    )
    round_tripped = DialogueObligation.from_dict(obligation.as_dict())
    assert round_tripped.kind is ObligationKind.CLARIFICATION

def test_r3_successor_3b4cfeb86fa0db77def5() -> None:
    obligation = _dialogue_obligation(
        ObligationKind.EVIDENCE_REQUEST, suffix="evidence"
    )
    round_tripped = DialogueObligation.from_dict(obligation.as_dict())
    assert round_tripped.kind is ObligationKind.EVIDENCE_REQUEST

def test_r3_successor_91f33f163e6a10e410b7() -> None:
    obligation = _dialogue_obligation(
        ObligationKind.LEARNING_ANSWER, suffix="learning"
    )
    round_tripped = DialogueObligation.from_dict(obligation.as_dict())
    assert round_tripped.kind is ObligationKind.LEARNING_ANSWER

def test_r3_successor_be210355a7860538c47c() -> None:
    obligation = _dialogue_obligation(
        ObligationKind.OPERATION_RESOLUTION, suffix="operation"
    )
    round_tripped = DialogueObligation.from_dict(obligation.as_dict())
    assert round_tripped.kind is ObligationKind.OPERATION_RESOLUTION

def test_r3_successor_765ec49d46eaedeb18e0() -> None:
    obligation = _dialogue_obligation(
        ObligationKind.CLARIFICATION,
        suffix="roundtrip",
        expires_turn_index=7,
    )
    encoded = obligation.as_dict()
    rebuilt = DialogueObligation.from_dict(encoded)
    assert rebuilt == obligation
    assert rebuilt.as_dict() == encoded
    assert rebuilt.source_query_ref == "query:roundtrip"
    assert rebuilt.expected_answer_contract_ref == "contract:answer:roundtrip"
    assert rebuilt.expires_turn_index == 7
    assert rebuilt.completion_receipt_ref is None

def test_r3_successor_c7b1f7079a3fe5c96275() -> None:
    obligation = _dialogue_obligation(
        ObligationKind.CLARIFICATION, suffix="frozen"
    )
    with pytest.raises(FrozenInstanceError):
        obligation.kind = ObligationKind.EVIDENCE_REQUEST

def test_r3_successor_1e4717dec0e04f377686() -> None:
    manager = DialogueObligationManager()
    original = _dialogue_obligation(
        ObligationKind.CLARIFICATION, suffix="fulfill"
    )
    manager.add(original)
    completed = manager.fulfill(original.obligation_ref, "receipt:done")
    assert manager.pending() == ()
    assert manager.get(original.obligation_ref) == completed
    assert completed.obligation_ref != original.obligation_ref
    assert completed.completion_receipt_ref == "receipt:done"
    with pytest.raises(FrozenInstanceError):
        completed.completion_receipt_ref = "receipt:changed"

def test_r3_successor_a85edba372926159baca() -> None:
    manager = DialogueObligationManager()
    first = _dialogue_obligation(
        ObligationKind.LEARNING_ANSWER, suffix="learn-first"
    )
    second = _dialogue_obligation(
        ObligationKind.LEARNING_ANSWER, suffix="learn-second"
    )
    manager.add(first)
    manager.fulfill(first.obligation_ref, "receipt:learned")
    manager.add(second)
    assert manager.has_learning_obligation()
    assert manager.pending() == (second,)

def test_r3_successor_b48619272bc7c008bae8() -> None:
    manager = DialogueObligationManager()
    learning = _dialogue_obligation(
        ObligationKind.LEARNING_ANSWER, suffix="learning-pending"
    )
    clarification = _dialogue_obligation(
        ObligationKind.CLARIFICATION, suffix="clarification-completed"
    )
    manager.add(learning)
    manager.add(clarification)
    manager.fulfill(clarification.obligation_ref, "receipt:clarified")
    assert manager.has_learning_obligation()
    assert manager.pending() == (learning,)
    assert manager.get(learning.obligation_ref) == learning
    assert learning.completion_receipt_ref is None

def test_r3_successor_decaeee068cfd77411c0() -> None:
    selection = GoalArbiter().select(goals=(), obligations=())
    assert selection.selected_goal_ref is None
    assert selection.selected_obligation_ref is None
    assert selection.ui_intent_label == "idle"

def test_r3_successor_a35b386efc1b5d62d530() -> None:
    completed = _dialogue_obligation(
        ObligationKind.CLARIFICATION,
        suffix="completed",
        completion_receipt_ref="receipt:completed",
    )
    selection = GoalArbiter().select(
        goals=("goal:explore",), obligations=(completed,)
    )
    assert selection.selected_goal_ref == "goal:explore"
    assert selection.selected_obligation_ref is None
    assert selection.ui_intent_label == "goal:pursue"

def test_r3_successor_0a59b0d3bb8df37b4930() -> None:
    pending = _dialogue_obligation(
        ObligationKind.EVIDENCE_REQUEST, suffix="pending"
    )
    selection = GoalArbiter().select(
        goals=("goal:explore",), obligations=(pending,)
    )
    assert selection.selected_goal_ref is None
    assert selection.selected_obligation_ref == pending.obligation_ref
    assert selection.ui_intent_label == "obligation:fulfill"

def test_r3_successor_ce67b625850e1d0b8f06() -> None:
    assert_successor_contract('obligation', 'assertion:dialogue-obligations-goal-arbiter-selects-higher-priority-obligation')

def test_r3_successor_4e18303fa2e5f85519e1() -> None:
    selection = GoalSelection(
        selected_goal_ref="goal:one",
        selected_obligation_ref=None,
        policy_ref=GoalArbiter.POLICY_REF,
    )
    assert selection.ui_intent_label == "goal:pursue"
    with pytest.raises(FrozenInstanceError):
        selection.ui_intent_label = "idle"

def test_r3_successor_fd3d8d92c3cd8dbd7b9b() -> None:
    manager = DialogueObligationManager()
    learning = _dialogue_obligation(
        ObligationKind.LEARNING_ANSWER, suffix="learning-coexists"
    )
    clarification = _dialogue_obligation(
        ObligationKind.CLARIFICATION, suffix="clarification-coexists"
    )
    manager.add(learning)
    manager.add(clarification)
    assert manager.has_learning_obligation()
    pending = manager.pending()
    assert len(pending) == 2
    assert set(pending) == {learning, clarification}

def test_r3_successor_b3e455c6c3aafd588648() -> None:
    manager = DialogueObligationManager()
    obligations = (
        _dialogue_obligation(
            ObligationKind.CLARIFICATION, suffix="coexist-clarification"
        ),
        _dialogue_obligation(
            ObligationKind.EVIDENCE_REQUEST, suffix="coexist-evidence"
        ),
        _dialogue_obligation(
            ObligationKind.OPERATION_RESOLUTION, suffix="coexist-operation"
        ),
    )
    for obligation in obligations:
        manager.add(obligation)
    pending = manager.pending()
    assert len(pending) == 3
    assert set(pending) == set(obligations)

def test_r3_successor_d1c5dbf99de9415b8519() -> None:
    manager = DialogueObligationManager()
    first = _dialogue_obligation(
        ObligationKind.LEARNING_ANSWER, suffix="only-learning-first"
    )
    second = _dialogue_obligation(
        ObligationKind.LEARNING_ANSWER, suffix="only-learning-second"
    )
    manager.add(first)
    with pytest.raises(ValueError, match="only one learning obligation"):
        manager.add(second)
    assert manager.pending() == (first,)

def test_r3_successor_e8164c03ba5a45f4c73a() -> None:
    manager = DialogueObligationManager()
    first = _dialogue_obligation(
        ObligationKind.CLARIFICATION,
        suffix="pending-first",
        expires_turn_index=8,
    )
    second = _dialogue_obligation(
        ObligationKind.EVIDENCE_REQUEST,
        suffix="pending-second",
        expires_turn_index=9,
    )
    manager.add(second)
    manager.add(first)
    assert manager.pending() == (first, second)
    assert all(
        obligation.completion_receipt_ref is None
        for obligation in manager.pending()
    )

def test_r3_successor_b84479b75b9548b571b7() -> None:
    selection = GoalArbiter().select(goals=("goal:one",), obligations=())
    assert selection.ui_intent_label == "goal:pursue"
    assert selection.ui_intent_label != selection.selected_goal_ref

def test_r3_successor_e1d049d841566398e976() -> None:
    store = FocusStore()
    older = _verified_focus("alternative-older")
    latest = _verified_focus("alternative-latest")
    store.add(older)
    store.add(latest)
    result = ReferenceResolver(store, object()).resolve(
        "reference:content",
        ReferenceConstraints("second", None, "content", 8, "session:focus"),
        "turn:current",
    )
    assert result.selected_ref == latest.expression_refs[0]
    assert result.alternative_refs == older.expression_refs
    assert result.selected_ref not in result.alternative_refs
    assert result.proof_refs == (latest.focus_ref,)

def test_r3_successor_a5dea97d747501c03ddb() -> None:
    store = FocusStore()
    row = _verified_focus(
        "mixed-kind",
        expression_refs=("expression:mixed",),
        entity_refs=("entity:mixed",),
    )
    store.add(row)
    result = ReferenceResolver(store, object()).resolve(
        "reference:entity",
        ReferenceConstraints(None, None, "entity", 8, "session:focus"),
        "turn:current",
    )
    assert result.selected_ref == "entity:mixed"
    assert result.alternative_refs == ()
    assert "expression:mixed" not in (result.selected_ref, *result.alternative_refs)
    assert result.proof_refs == (row.focus_ref,)

def test_r3_successor_22e25b96ca44e4637599(linked_authority) -> None:
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        focus = FocusStore()
        focus.add(
            _verified_focus(
                "orientation",
                expression_refs=("expression:orientation",),
                entity_refs=("entity:orientation",),
            )
        )
        orientation = OrientationProjector(
            linked_authority,
            stores,
            RuntimeConfig.release(),
            focus_store=focus,
        ).project("session:orientation", "ignored surface")
        assert orientation.focus_refs == (
            "entity:orientation",
            "expression:orientation",
        )
        assert "focus_store:refs" in orientation.index_probes
        assert orientation.scanned_atom_count == 0
    finally:
        stores.close()

def test_r3_successor_6d677dc551ceca07cc5b() -> None:
    store = FocusStore()
    system = _verified_focus("second-system")
    user = _verified_focus(
        "second-user", participant_ref="participant:user"
    )
    store.add(system)
    store.add(user)
    result = ReferenceResolver(store, object()).resolve(
        "reference:second-person",
        ReferenceConstraints("second", None, "content", 8, "session:focus"),
        "turn:current",
    )
    assert result.selected_ref == system.expression_refs[0]
    assert result.alternative_refs == ()
    assert user.expression_refs[0] not in (
        result.selected_ref,
        *result.alternative_refs,
    )
    assert result.proof_refs == (system.focus_ref,)

def test_r3_successor_ef3349ae724cbc5de2f5() -> None:
    store = FocusStore()
    user = _verified_focus(
        "first-user", participant_ref="participant:user"
    )
    system = _verified_focus("first-system")
    store.add(user)
    store.add(system)
    result = ReferenceResolver(store, object()).resolve(
        "reference:first-person",
        ReferenceConstraints("first", None, "content", 8, "session:focus"),
        "turn:current",
    )
    assert result.selected_ref == user.expression_refs[0]
    assert result.alternative_refs == ()
    assert system.expression_refs[0] not in (
        result.selected_ref,
        *result.alternative_refs,
    )
    assert result.proof_refs == (user.focus_ref,)

def test_r3_successor_ac8ed838a7083c66f1e4() -> None:
    store = FocusStore()
    older = _verified_focus("recency-older")
    newest = _verified_focus("recency-newest")
    store.add(older)
    store.add(newest)
    result = ReferenceResolver(store, object()).resolve(
        "reference:recent",
        ReferenceConstraints(None, None, "content", 1, "session:focus"),
        "turn:current",
    )
    assert result.selected_ref == newest.expression_refs[0]
    assert result.alternative_refs == ()
    assert older.expression_refs[0] not in (
        result.selected_ref,
        *result.alternative_refs,
    )
    assert result.proof_refs == (newest.focus_ref,)

def test_r3_successor_6634463067f7cafa0051() -> None:
    store = FocusStore()
    prior = _verified_focus("typed-binding")
    store.add(prior)
    result = ReferenceResolver(store, object()).resolve(
        "reference:demonstrative:1",
        ReferenceConstraints("third", None, "proposition", 8, "session:focus"),
        "turn:current",
    )
    assert (result.reference_ref, result.selected_ref) == (
        "reference:demonstrative:1",
        prior.expression_refs[0],
    )
    assert result.alternative_refs == ()
    assert result.proof_refs == (prior.focus_ref,)

def test_r3_successor_0e8f1a78989177d083df() -> None:
    store = FocusStore()
    older = _verified_focus("prior-proposition-older")
    latest = _verified_focus("prior-proposition-latest")
    current = _verified_focus("prior-proposition-current")
    for row in (older, latest, current):
        store.add(row)
    result = ReferenceResolver(store, object()).resolve(
        "reference:proposition",
        ReferenceConstraints("third", None, "proposition", 8, "session:focus"),
        current.turn_ref,
    )
    assert result.selected_ref == latest.expression_refs[0]
    assert result.alternative_refs == older.expression_refs
    assert current.expression_refs[0] not in (
        result.selected_ref,
        *result.alternative_refs,
    )
    assert result.proof_refs == (latest.focus_ref,)

def test_r3_successor_1ebc6d8ac2f5ba9c3561() -> None:
    store = FocusStore()
    prior = _verified_focus("verified-proposition")
    store.add(prior)
    result = ReferenceResolver(store, object()).resolve(
        "reference:verified-proposition",
        ReferenceConstraints("third", None, "proposition", 8, "session:focus"),
        "turn:current",
    )
    assert (result.reference_ref, result.selected_ref) == (
        "reference:verified-proposition",
        prior.expression_refs[0],
    )
    assert result.proof_refs == (prior.focus_ref,)

def test_r3_successor_8de40dd01498141881a5() -> None:
    result = ReferenceResolver(FocusStore(), object()).resolve(
        "reference:unresolved",
        ReferenceConstraints(None, None, "proposition", 8, "session:focus"),
        "turn:current",
    )
    assert result.reference_ref == "reference:unresolved"
    assert result.selected_ref is None
    assert result.alternative_refs == ()
    assert result.proof_refs == ()

def test_r3_successor_fdf57c758cf49833fadd() -> None:
    store = FocusStore()
    user = _verified_focus(
        "negative-user", participant_ref="participant:user"
    )
    current = _verified_focus("negative-current")
    store.add(user)
    store.add(current)
    result = ReferenceResolver(store, object()).resolve(
        "reference:second-person-content",
        ReferenceConstraints("second", None, "content", 2, "session:focus"),
        current.turn_ref,
    )
    assert result.selected_ref is None
    assert result.alternative_refs == ()
    assert result.proof_refs == ()
    assert user.expression_refs[0] not in (
        result.selected_ref,
        *result.alternative_refs,
    )

def test_r3_successor_4618c9de8b3438873934() -> None:
    store = FocusStore()
    older = _verified_focus("system-content-older")
    latest = _verified_focus("system-content-latest")
    user = _verified_focus(
        "system-content-user", participant_ref="participant:user"
    )
    store.add(older)
    store.add(latest)
    store.add(user)
    result = ReferenceResolver(store, object()).resolve(
        "reference:second-person-content",
        ReferenceConstraints("second", None, "content", 8, "session:focus"),
        "turn:current",
    )
    assert result.selected_ref == latest.expression_refs[0]
    assert result.alternative_refs == older.expression_refs
    assert user.expression_refs[0] not in (
        result.selected_ref,
        *result.alternative_refs,
    )
    assert result.proof_refs == (latest.focus_ref,)

def test_r3_successor_27ba73e12b88ad9fe2eb() -> None:
    assert_successor_contract('reference', 'assertion:discourse-reference-what-did-you-say-resolves-verified-system-speech')

def test_r3_successor_df4e7f0c6066c9fc02cf() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-admission-is-policy-derived-admission-cannot-be-requested-by-token')

def test_r3_successor_b767ac63d32d8299b00e() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-admission-is-policy-derived-admission-carries-policy-ref')

def test_r3_successor_8240da7c2f121cbcfc14() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-corrections-supersede-without-deleting-provenance-correction-status')

def test_r3_successor_be0bc997b98fb4dd9ace() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed')

def test_r3_successor_2fe822715d9bff6bdc8a() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed')

def test_r3_successor_d73b27aab098023a9867() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed')

def test_r3_successor_86faa75790d71aaa138b() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed')

def test_r3_successor_6eef143e2a8dbd7da3fb() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-nested-placements-remain-attributed-nested-mode-is-attributed')

def test_r3_successor_de74cf5c0852c48aa4b5() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-observed-claims-with-evidence-are-admitted-observed-with-evidence-is-admitted')

def test_r3_successor_9837994441bbb5b0183d() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-observed-claims-with-evidence-are-admitted-observed-without-evidence-is-contested')

def test_r3_successor_f82ead85935f7cb8640d() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-reported-speech-does-not-become-world-truth-reported-speech-admission-is-attributed')

def test_r3_successor_ea3d1eb00bf28f853d92() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-reported-speech-does-not-become-world-truth-reported-speech-placement-mode')

def test_r3_successor_647fedb72fbbcfbf2a87() -> None:
    assert_successor_contract('epistemic', 'assertion:epistemic-admission-test-reported-speech-does-not-become-world-truth-reported-speech-world-query-unknown')

def test_r3_successor_b650ca7318ae30576ef7() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_829c535a40e12927bf97() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_43ba22a660043d569a04() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_2fb6478bb03f0913af9e() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_3d4560bbd2cba740ad1d() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_8d46f2d4f8a82b11d71c() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_cf1ea0498148f19cc17c() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_087fa7741523c766b339() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_06b6c58163e318ee4963() -> None:
    assert_successor_contract('gap', 'assertion:gap-matrix-every-cycle-status-is-reachable')

def test_r3_successor_ffb56b3b17f5ce2d5a7f() -> None:
    assert_successor_contract('learning', 'assertion:learning-distinctions-conversational-wording-cannot-select-reviewer-policy')

def test_r3_successor_59d62df8f6399e561544() -> None:
    assert_successor_contract('learning', 'assertion:learning-distinctions-designation-commit-consumes-plan')

def test_r3_successor_60b5af589ecd1e402709() -> None:
    assert_successor_contract('learning', 'assertion:learning-distinctions-lookup-does-not-create-designation')

def test_r3_successor_be58b79b365d977533c9() -> None:
    assert_successor_contract('learning', 'assertion:learning-distinctions-meaning-lookup-does-not-mutate')

def test_r3_successor_7e270e6990d7880d264d() -> None:
    assert_successor_contract('learning', 'assertion:learning-distinctions-no-public-install-rules')

def test_r3_successor_4d6ad497849e46c6dfea() -> None:
    assert_successor_contract('learning', 'assertion:learning-distinctions-one-pending-learning-obligation')

def test_r3_successor_b7a1255e5e8232dfa402() -> None:
    assert_successor_contract('learning', 'assertion:learning-distinctions-untrusted-teaching-is-attributed-only')

def test_r3_successor_ef9d0b1bf1ba3fe1618e() -> None:
    assert_successor_contract('query', 'assertion:query-engine-existential-witness-is-proof-local')

def test_r3_successor_6494fb26adb069b3b7e5() -> None:
    assert_successor_contract('query', 'assertion:query-engine-generic-family-rule-lowering-supports-marriage-with-trace')

def test_r3_successor_5ce43fa19074d3b15ca4() -> None:
    assert_successor_contract('query', 'assertion:query-engine-meaning-description-is-composed-from-grounded-structure')

def test_r3_successor_bef2e803029d9c46f884() -> None:
    assert_successor_contract('query', 'assertion:query-engine-meaning-description-is-composed-from-grounded-structure')

def test_r3_successor_1a25374d0e03ea86a7a7() -> None:
    assert_successor_contract('query', 'assertion:query-engine-meaning-description-is-composed-from-grounded-structure')

def test_r3_successor_8d08917fa702cb9b2fed() -> None:
    assert_successor_contract('query', 'assertion:query-engine-observe-records-facts')

def test_r3_successor_de6989568e516bea8aed() -> None:
    assert_successor_contract('query', 'assertion:query-engine-semantic-description-never-reads-internal-ref-name')

def test_r3_successor_d4770b48f1d95b0a2161() -> None:
    assert_successor_contract('r3_runtime', 'assertion:restart-e2e-test-restart-memory-consistency-consecutive-cycles-preserve-revision-pins')

def test_r3_successor_f4441486b4cb53c5c9ee() -> None:
    assert_successor_contract('r3_runtime', 'assertion:restart-e2e-test-restart-cycle-result-structure-cycle-result-after-restart-has-all-artifacts')

def test_r3_successor_37b5fe8ca6b81d8e435d() -> None:
    assert_successor_contract('r3_runtime', 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-evaluation')

def test_r3_successor_2ac780c8d0d83aa505e5() -> None:
    assert_successor_contract('r3_runtime', 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-response-meaning')

def test_r3_successor_5c62c09726631356d222() -> None:
    assert_successor_contract('r3_runtime', 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-orientation')

def test_r3_successor_117636df56c528015c99() -> None:
    assert_successor_contract('r3_runtime', 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-proposal')

def test_r3_successor_e2effe1dca9264717301() -> None:
    assert_successor_contract('r3_runtime', 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-verification')

def test_r3_successor_26c3172feb21ecab47de() -> None:
    assert_successor_contract('r3_runtime', 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-trace-with-durations')

def test_r3_successor_02c8a3b9911859bf0353() -> None:
    assert_successor_contract('r3_runtime', 'assertion:restart-e2e-test-stale-revision-restart-stale-revision-restart-at-orient')

def test_r3_successor_79703ee34fd786bdb486() -> None:
    assert_successor_contract('r3_runtime', 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-effect-revision')

def test_r3_successor_873b881d81e9b56ee8b7() -> None:
    assert_successor_contract('r3_runtime', 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-revision-pin-fields')

def test_r3_successor_6da536de8c4c1ceb8564() -> None:
    assert_successor_contract('r3_runtime', 'assertion:restart-e2e-test-restart-multiple-cycles-restart-preserves-revisions-across-multiple-cycles')

def test_r3_successor_70660ec884ab5d824ecf() -> None:
    assert_successor_contract('r3_runtime', 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-world-revision')

def test_r3_successor_fdc717e6c26ffcec5598() -> None:
    assert_successor_contract('episode', 'assertion:r1-episode-verified-meaning-separation')

def test_r3_successor_3e9b731d0d9a6f6936bc() -> None:
    assert_successor_contract('episode', 'assertion:r1-episode-strict-codec')

def test_r3_successor_23ab4f6d79fd50bbf874() -> None:
    assert_successor_contract('r3_runtime', 'assertion:six-phase-runtime-second-cycle-increments-world-revision')

def test_r3_successor_496f6e6d7dbfe89cf019() -> None:
    assert_successor_contract('r3_runtime', 'assertion:six-phase-runtime-injected-program-runs-through-six-phase-owners')

def test_r3_successor_9eff2e971f959a40f142() -> None:
    assert_successor_contract('r3_runtime', 'assertion:six-phase-runtime-phase-receipts-have-named-phases-not-stage-numbers')

def test_r3_successor_5b46fb3213f566e27ea3() -> None:
    assert_successor_contract('r3_runtime', 'assertion:r1-runtime-exceptions-propagate')

def test_r3_successor_b4d0d67b952a4c0d71fe() -> None:
    assert_successor_contract('r3_runtime', 'assertion:r1-slice-b-runtime-receipts-bind-orientation-content')

def test_r3_successor_b0e60c540b0dfdbf9db0() -> None:
    assert_successor_contract('r3_runtime', 'assertion:six-phase-runtime-gap-receipt-is-none-on-resolved-cycle')

def test_r3_successor_cb8ad9a437e9ab6f1679() -> None:
    assert_successor_contract('r3_runtime', 'assertion:r1-selected-stops-at-r3')

def test_r3_successor_8e5b08c7cdc04e85c277() -> None:
    assert_successor_contract('r3_runtime', 'assertion:r1-runtime-trace-observational')

def test_r3_successor_8bf5349ade7a922ffb28() -> None:
    assert_successor_contract('r3_runtime', 'assertion:six-phase-runtime-trace-off-still-resolves')

def test_r3_successor_e77fbfa5288e26050075() -> None:
    assert_successor_contract('query', 'assertion:recursive-inference-recursive-inference-with-unseen-synonym')

def test_r3_successor_977ebbadf7168d551a31() -> None:
    assert_successor_contract('response', 'assertion:response-meaning-test-response-meaning-precedes-language-denied-status-maps-to-deny-action')

def test_r3_successor_989bedf3d53929a6a3e8() -> None:
    assert_successor_contract('response', 'assertion:response-meaning-test-response-meaning-precedes-language-response-builder-cannot-inspect-input-words')

def test_r3_successor_3dcf1ce99d768a4a387e() -> None:
    assert_successor_contract('response', 'assertion:response-meaning-test-response-meaning-precedes-language-response-meaning-has-all-fields')

def test_r3_successor_ed763dea9d599d0845d8() -> None:
    assert_successor_contract('response', 'assertion:response-meaning-test-response-meaning-precedes-language-response-meaning-is-frozen')

def test_r3_successor_a7535250c38166db9516() -> None:
    assert_successor_contract('response', 'assertion:response-meaning-test-response-meaning-precedes-language-response-meaning-precedes-language')

def test_r3_successor_a3c7e653cf515659a7a6() -> None:
    assert_successor_contract('restart', 'assertion:restart-e2e-test-restart-committed-effect-committed-effect-remains-journaled-after-restart')

def test_r3_successor_9737c160af466856feaf() -> None:
    assert_successor_contract('restart', 'assertion:restart-e2e-test-restart-idempotency-restart-does-not-re-invoke-completed-effect')




def test_r3_successor_dcac0e8e494facbd9d3f() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-acquisition-consumes-plan')

def test_r3_successor_d335a36b78de5c78ae48() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-acquisition-conversational-wording-cannot-select-policy')

def test_r3_successor_448444eb09d013ea4ad4() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-acquisition-plan-mismatch-rejected')

def test_r3_successor_5cd9e27e5bab778ace82() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-acquisition-preserves-compatibility-hash')

def test_r3_successor_07e5438a8190c02f528b() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-acquisition-requires-cap-learn')

def test_r3_successor_512bcc3c6fba9795ed02() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-acquisition-requires-reviewer-authorization')

def test_r3_successor_ae3ce54649dca81d1f24() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-one-invalid-definition-rejects-entire-acquisition')

def test_r3_successor_d3129dc396cacffc2e8d() -> None:
    assert_successor_contract('learning', 'assertion:synonym-acquisition-reviewed-generic-definitions-publish-one-linked-generation')
