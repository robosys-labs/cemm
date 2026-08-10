from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "hybrid_mvp" / "configs" / "validation_gates.json"
data = json.loads(path.read_text(encoding="utf-8"))
steps = data["steps"]
r3 = data["phases"]["R3"]

r3["owners"] = {
    "capability-effect": ["r3_capability_effect_owner_tests"],
    "decision-query-proof": ["r3_decision_query_proof_owner_tests"],
    "effect-learning-response": ["r3_effect_learning_owner_tests"],
    "learning-response": ["r3_learning_response_owner_tests"],
    "situation-context": ["r3_situation_context_owner_tests"],
}
r3["phase"] = ["r3_phase_tests"]

steps.pop("r3_governance_owner_tests", None)
steps.pop("r3_situation_decision_owner_tests", None)

steps["r3_capability_effect_owner_tests"] = {
    "depends_on": ["source_compile"],
    "exact_nodes": [
        "tests/test_r3_effect_receipts.py::test_atomic_effect_transaction_advances_world_and_effect_together",
        "tests/test_r3_effect_receipts.py::test_committed_receipt_requires_advanced_effect_revision",
        "tests/test_r3_effect_receipts.py::test_no_effect_round_trip_preserves_reason",
    ],
    "inputs": [
        "src/cemm_authoritative_hybrid/r3_effects.py",
        "src/cemm_authoritative_hybrid/r3_persistence.py",
        "tests/test_r3_effect_receipts.py",
    ],
    "kind": "pytest",
}

steps["r3_decision_query_proof_owner_tests"] = {
    "depends_on": ["source_compile"],
    "exact_nodes": [
        "tests/test_r3_decision_abi.py::test_decision_identity_covers_proof_refs",
        "tests/test_r3_decision_abi.py::test_evaluate_rejects_raw_program_like_object",
        "tests/test_r3_decision_abi.py::test_evaluator_requires_all_four_closed_modes",
        "tests/test_r3_decision_abi.py::test_exact_evaluator_consumes_verified_meaning_and_situation",
        "tests/test_r3_expression_projection.py::test_projection_indexes_roles_without_ref_spelling_dispatch",
        "tests/test_r3_expression_projection.py::test_projection_validates_recursive_expression",
        "tests/test_r3_recursive_query.py::test_query_owner_applies_reviewed_rules_with_proof_lineage",
    ],
    "inputs": [
        "src/cemm_authoritative_hybrid/decision.py",
        "src/cemm_authoritative_hybrid/expression_projection.py",
        "src/cemm_authoritative_hybrid/r3_cognition.py",
        "tests/test_r3_decision_abi.py",
        "tests/test_r3_expression_projection.py",
        "tests/test_r3_recursive_query.py",
    ],
    "kind": "pytest",
}

steps["r3_effect_learning_owner_tests"] = {
    "depends_on": ["source_compile"],
    "exact_nodes": [
        "tests/test_r3_learning_transaction.py::test_incomplete_designation_requests_clarification_without_learning_draft",
        "tests/test_r3_learning_transaction.py::test_learning_decision_materializes_exact_evaluated_draft",
        "tests/test_r3_learning_transaction.py::test_learning_finalization_rejects_unbound_draft_ref",
    ],
    "inputs": [
        "src/cemm_authoritative_hybrid/decision.py",
        "src/cemm_authoritative_hybrid/r3_cognition.py",
        "src/cemm_authoritative_hybrid/r3_learning.py",
        "src/cemm_authoritative_hybrid/situation.py",
        "tests/test_r3_learning_transaction.py",
    ],
    "kind": "pytest",
}

steps["r3_learning_response_owner_tests"] = {
    "depends_on": ["source_compile"],
    "exact_nodes": [
        "tests/test_r3_learning_response.py::test_learning_plan_abi2_round_trip_binds_semantic_lineage",
        "tests/test_r3_learning_response.py::test_response_meaning_round_trip_has_no_surface_text",
    ],
    "inputs": [
        "src/cemm_authoritative_hybrid/r3_learning.py",
        "src/cemm_authoritative_hybrid/r3_response.py",
        "tests/test_r3_learning_response.py",
    ],
    "kind": "pytest",
}

steps["r3_situation_context_owner_tests"] = {
    "depends_on": ["source_compile"],
    "exact_nodes": [
        "tests/test_r3_form_mode_integration.py::test_reviewed_conditional_and_hypothetical_forms_project_simulation",
        "tests/test_r3_mode_projection.py::test_closed_modes_are_projected_from_structural_hypotheses",
        "tests/test_r3_mode_projection.py::test_competing_nonobserve_modes_fail_closed",
        "tests/test_r3_situation_context.py::test_situation_context_identity_covers_source_lineage",
        "tests/test_r3_situation_context.py::test_situation_context_round_trip_is_exact",
        "tests/test_r3_situation_context.py::test_situation_rejects_mode_scope_disagreement",
        "tests/test_r3_situation_context.py::test_situation_requires_distinct_reviewed_participants",
    ],
    "inputs": [
        "data/languages/en/forms.json",
        "src/cemm_authoritative_hybrid/forms.py",
        "src/cemm_authoritative_hybrid/mode.py",
        "src/cemm_authoritative_hybrid/situation.py",
        "tests/test_r3_form_mode_integration.py",
        "tests/test_r3_mode_projection.py",
        "tests/test_r3_situation_context.py",
    ],
    "kind": "pytest",
}

steps["r3_phase_tests"] = {
    "depends_on": ["source_compile"],
    "exact_nodes": [
        "tests/test_r3_no_program_as_meaning.py::test_program_to_evaluate_raises_type_error",
        "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_access_program_actions",
        "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_access_program_graph",
        "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_branch_on_raw_words",
        "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_import_semantic_switch_program",
        "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_read_orientation_source_text",
        "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_use_form_resolver_or_grounder",
        "tests/test_r3_no_program_as_meaning.py::test_r3_transition_preview_not_effect_authorization",
        "tests/test_r3_owner_structure.py::test_r3_owners_are_post_verify",
        "tests/test_r3_owner_structure.py::test_r3_owners_do_not_import_legacy_proposition_fixtures",
        "tests/test_r3_owner_structure.py::test_r3_owners_do_not_import_r4_plus_modules",
        "tests/test_r3_owner_structure.py::test_r3_runtime_owns_evaluate_and_exposes_only_r5_boundary",
        "tests/test_r3_plan_contract.py::test_r3_abi_registry_includes_activation_canary_receipt_abi_1",
        "tests/test_r3_plan_contract.py::test_r3_abi_registry_includes_decision_abi_1",
        "tests/test_r3_plan_contract.py::test_r3_cannot_be_admitted_while_r2_is_non_green",
        "tests/test_r3_plan_contract.py::test_r3_duplicate_decision_owner_fails",
        "tests/test_r3_plan_contract.py::test_r3_owner_groups_within_eight_step_limit",
        "tests/test_r3_plan_contract.py::test_r3_plan_is_committed",
        "tests/test_r3_plan_contract.py::test_r3_validation_gates_define_r3_phase",
        "tests/test_r3_public_cycle.py::test_simulate_cycle_emits_no_effect_and_preserves_world_revision",
        "tests/test_r3_public_cycle.py::test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation",
        "tests/test_r3_structure.py::test_cycle_extension_preserves_canonical_cycle_class_owner",
        "tests/test_r3_structure.py::test_only_atomic_effect_persistence_commits_world_state",
        "tests/test_r3_structure.py::test_post_verify_owners_do_not_consume_program_graph_or_raw_text",
        "tests/test_r3_structure.py::test_r3_runtime_has_exact_r5_boundary",
    ],
    "inputs": [
        "configs/validation_gates.json",
        "data/authority/",
        "data/languages/",
        "docs/ABI_REGISTRY.md",
        "docs/DOCUMENT_AUTHORITY.json",
        "docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-cognition-activation-plan.md",
        "scripts/run_r3_canaries.py",
        "src/cemm_authoritative_hybrid/",
        "tests/conftest.py",
        "tests/test_r3_no_program_as_meaning.py",
        "tests/test_r3_owner_structure.py",
        "tests/test_r3_plan_contract.py",
        "tests/test_r3_public_cycle.py",
        "tests/test_r3_structure.py",
    ],
    "kind": "pytest",
}

path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
