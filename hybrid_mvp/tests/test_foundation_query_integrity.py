"""Independent QUERY evidence completeness and provenance regressions."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

__cemm_test_inventory__ = {
    "tests/test_foundation_query_integrity.py::test_pinned_atom_registry_does_not_supply_implicit_query_support": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-atom-registry-does-not-supply-implicit-query-support",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "322e03560712b452d6b05f0cb73c58fc0447e5ef8099b51635034d6bf6d8bf78",
        "supersedes_node_id": "tests/test_foundation_semantics.py::test_atom_registry_does_not_supply_implicit_query_support"
    },
    "tests/test_foundation_query_integrity.py::test_pinned_explicit_type_fact_preserves_binding_and_attributed_proof": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-explicit-type-fact-preserves-binding-and-attributed-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "ea9b8821361661b3881fbc416dfa57275224e33c676d758fddf6f60aca8c8abf",
        "supersedes_node_id": "tests/test_foundation_semantics.py::test_explicit_type_fact_preserves_binding_and_attributed_proof"
    },
    "tests/test_foundation_query_integrity.py::test_relevant_fact_after_irrelevant_prefix_is_not_unknown[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-relevant-fact-after-irrelevant-prefix-is-not-unknown-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "94f0971044ee4bc96664444f216282434cd47fc8a34007bcf2cbc16d959102be"
    },
    "tests/test_foundation_query_integrity.py::test_relevant_fact_after_irrelevant_prefix_is_not_unknown[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-relevant-fact-after-irrelevant-prefix-is-not-unknown-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "94f0971044ee4bc96664444f216282434cd47fc8a34007bcf2cbc16d959102be"
    },
    "tests/test_foundation_query_integrity.py::test_opposition_after_irrelevant_prefix_survives[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-opposition-after-irrelevant-prefix-survives-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "98cf634331a1c7cb4dcfbbc5e1333f83318ad57967f91ae9ec1463c27783854f"
    },
    "tests/test_foundation_query_integrity.py::test_opposition_after_irrelevant_prefix_survives[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-opposition-after-irrelevant-prefix-survives-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "98cf634331a1c7cb4dcfbbc5e1333f83318ad57967f91ae9ec1463c27783854f"
    },
    "tests/test_foundation_query_integrity.py::test_relevant_overflow_never_answers_from_partial_support[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-relevant-overflow-never-answers-from-partial-support-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c8608af5144777887fe9b9933a99d6a1d7a3d8cb2adbd2f39890f91a48d5e571"
    },
    "tests/test_foundation_query_integrity.py::test_relevant_overflow_never_answers_from_partial_support[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-relevant-overflow-never-answers-from-partial-support-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c8608af5144777887fe9b9933a99d6a1d7a3d8cb2adbd2f39890f91a48d5e571"
    },
    "tests/test_foundation_query_integrity.py::test_reported_evidence_is_not_unqualified_truth[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-reported-evidence-is-not-unqualified-truth-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "461e1f997e0e62d40e3ce8652b1d3a3f5a34ef7ad4280b46574cc26f9114e804"
    },
    "tests/test_foundation_query_integrity.py::test_reported_evidence_is_not_unqualified_truth[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-reported-evidence-is-not-unqualified-truth-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "461e1f997e0e62d40e3ce8652b1d3a3f5a34ef7ad4280b46574cc26f9114e804"
    },
    "tests/test_foundation_query_integrity.py::test_rule_does_not_launder_reported_premise[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-does-not-launder-reported-premise-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "0394c41c84bfb6c52d3732d252daf5819d82e7b90062276b44d4f4b27a6cab7d"
    },
    "tests/test_foundation_query_integrity.py::test_rule_does_not_launder_reported_premise[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-does-not-launder-reported-premise-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "0394c41c84bfb6c52d3732d252daf5819d82e7b90062276b44d4f4b27a6cab7d"
    },
    "tests/test_foundation_query_integrity.py::test_rule_source_provenance_survives[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-source-provenance-survives-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "67d32323adaa7a706d732fb89d9ef54a6e64c2341b95c9b279864865f435f404"
    },
    "tests/test_foundation_query_integrity.py::test_rule_source_provenance_survives[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-source-provenance-survives-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "67d32323adaa7a706d732fb89d9ef54a6e64c2341b95c9b279864865f435f404"
    },
    "tests/test_foundation_query_integrity.py::test_nonconverged_seven_hop_rule_chain_is_budget_not_unknown[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-nonconverged-seven-hop-rule-chain-is-budget-not-unknown-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "0f310f49c7c190fcb18353b02e358e47fc1f3a6fe7a6a5217b678014bedadd49"
    },
    "tests/test_foundation_query_integrity.py::test_nonconverged_seven_hop_rule_chain_is_budget_not_unknown[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-nonconverged-seven-hop-rule-chain-is-budget-not-unknown-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "0f310f49c7c190fcb18353b02e358e47fc1f3a6fe7a6a5217b678014bedadd49"
    },
    "tests/test_foundation_query_integrity.py::test_direct_owner_rejects_stale_situation_pin[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-direct-owner-rejects-stale-situation-pin-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "211c0ea855aecfeacd4538ee08a1900ab854616c4392d7542615507ce2f7ee01"
    },
    "tests/test_foundation_query_integrity.py::test_direct_owner_rejects_stale_situation_pin[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-direct-owner-rejects-stale-situation-pin-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "211c0ea855aecfeacd4538ee08a1900ab854616c4392d7542615507ce2f7ee01"
    },
    "tests/test_foundation_query_integrity.py::test_backward_demands_include_every_conjunct_and_intermediate_entity[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-backward-demands-include-every-conjunct-and-intermediate-entity-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "ff9786619120f2520fdad0f533ff7dafbac4c5607a29d33deed9c4f31b444e16"
    },
    "tests/test_foundation_query_integrity.py::test_backward_demands_include_every_conjunct_and_intermediate_entity[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-backward-demands-include-every-conjunct-and-intermediate-entity-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "ff9786619120f2520fdad0f533ff7dafbac4c5607a29d33deed9c4f31b444e16"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-missing]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-missing",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-cycle]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-cycle",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-unproven]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-unproven",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-premises-only]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-premises-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-invalid-rule]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-invalid-rule",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-empty-premises]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-empty-premises",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-invalid-parent]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-invalid-parent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-invalid-substitution]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-invalid-substitution",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[memory-wrong-conclusion]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-memory-wrong-conclusion",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-missing]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-missing",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-cycle]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-cycle",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-unproven]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-unproven",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-premises-only]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-premises-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-invalid-rule]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-invalid-rule",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-empty-premises]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-empty-premises",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-invalid-parent]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-invalid-parent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-invalid-substitution]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-invalid-substitution",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_invalid_derived_proof_fails_closed[sqlite-wrong-conclusion]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-invalid-derived-proof-fails-closed-sqlite-wrong-conclusion",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "710eddaaac12535bf93e709d3f21e5c7a4e8d1f5fdd4fcfa70a870dc773139fc"
    },
    "tests/test_foundation_query_integrity.py::test_relevant_rule_limit_overrides_initial_support[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-relevant-rule-limit-overrides-initial-support-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "b57cf123ceadf9e0d3559c481c73a684b70104dcf8f39a8f2f6f272bc4464cf7"
    },
    "tests/test_foundation_query_integrity.py::test_relevant_rule_limit_overrides_initial_support[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-relevant-rule-limit-overrides-initial-support-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "b57cf123ceadf9e0d3559c481c73a684b70104dcf8f39a8f2f6f272bc4464cf7"
    },
    "tests/test_foundation_query_integrity.py::test_irrelevant_rules_do_not_consume_relevant_scan_limit[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-irrelevant-rules-do-not-consume-relevant-scan-limit-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "8dccdb5a7d44d80e1c7c8be07fe7238f6467c90bf6bc4726f8502dc08cbb4fb7"
    },
    "tests/test_foundation_query_integrity.py::test_irrelevant_rules_do_not_consume_relevant_scan_limit[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-irrelevant-rules-do-not-consume-relevant-scan-limit-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "8dccdb5a7d44d80e1c7c8be07fe7238f6467c90bf6bc4726f8502dc08cbb4fb7"
    },
    "tests/test_foundation_query_integrity.py::test_all_saturated_postings_conservatively_exhaust_small_intersection[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-all-saturated-postings-conservatively-exhaust-small-intersection-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "9ced0dad8ef441875a0e81924f7356facba8e2439ab94e5e0fee33ef9e47d305"
    },
    "tests/test_foundation_query_integrity.py::test_all_saturated_postings_conservatively_exhaust_small_intersection[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-all-saturated-postings-conservatively-exhaust-small-intersection-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "9ced0dad8ef441875a0e81924f7356facba8e2439ab94e5e0fee33ef9e47d305"
    },
    "tests/test_foundation_query_integrity.py::test_rule_alternative_derivations_preserve_both_sources[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-alternative-derivations-preserve-both-sources-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "19c0ea0fe72b573f84ff677507fd207b62595ae636969c46b9688375ca89daa9"
    },
    "tests/test_foundation_query_integrity.py::test_rule_alternative_derivations_preserve_both_sources[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-alternative-derivations-preserve-both-sources-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "19c0ea0fe72b573f84ff677507fd207b62595ae636969c46b9688375ca89daa9"
    },
    "tests/test_foundation_query_integrity.py::test_rule_join_overflow_does_not_return_partial_answer[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-join-overflow-does-not-return-partial-answer-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2dcc2926a86a74a3b48d2dbc4b5a83de7e198369a4a9d93446f6da0961890893"
    },
    "tests/test_foundation_query_integrity.py::test_rule_join_overflow_does_not_return_partial_answer[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-join-overflow-does-not-return-partial-answer-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "2dcc2926a86a74a3b48d2dbc4b5a83de7e198369a4a9d93446f6da0961890893"
    },
    "tests/test_foundation_query_integrity.py::test_unflagged_empty_derived_witness_cannot_become_direct_fact[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-unflagged-empty-derived-witness-cannot-become-direct-fact-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "01a7ab2f5f23ee0da0a20d0fb8128f74b9d9bd4008768d3f5de628966dcbc5c4"
    },
    "tests/test_foundation_query_integrity.py::test_unflagged_empty_derived_witness_cannot_become_direct_fact[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-unflagged-empty-derived-witness-cannot-become-direct-fact-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "01a7ab2f5f23ee0da0a20d0fb8128f74b9d9bd4008768d3f5de628966dcbc5c4"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_proof_premises_are_verified_inside_query_snapshot[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-proof-premises-are-verified-inside-query-snapshot-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "af535cd0c2ed3720557a04606672f58d96afc593977993c479238e818dcbb61a"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_proof_premises_are_verified_inside_query_snapshot[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-proof-premises-are-verified-inside-query-snapshot-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "af535cd0c2ed3720557a04606672f58d96afc593977993c479238e818dcbb61a"
    },
    "tests/test_foundation_query_integrity.py::test_rule_dependency_index_is_built_at_construction_and_not_scanned_by_first_query[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-index-built-at-construction-no-first-query-scan-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c31f3f8399df75a181b0b7040d4da0bc6fab6b21ffc476356bc0b5e26c13156c"
    },
    "tests/test_foundation_query_integrity.py::test_rule_dependency_index_is_built_at_construction_and_not_scanned_by_first_query[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-rule-index-built-at-construction-no-first-query-scan-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c31f3f8399df75a181b0b7040d4da0bc6fab6b21ffc476356bc0b5e26c13156c"
    },
    "tests/test_foundation_query_integrity.py::test_malformed_fact_stance_fails_closed[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-malformed-fact-stance-fails-closed-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "7bb4cf8bd48d42a80aabef6dd48fbf65d67bad84c8524d8ef0b7a4dbf67dc5b0"
    },
    "tests/test_foundation_query_integrity.py::test_malformed_fact_stance_fails_closed[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-malformed-fact-stance-fails-closed-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "7bb4cf8bd48d42a80aabef6dd48fbf65d67bad84c8524d8ef0b7a4dbf67dc5b0"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_derived_proof_reconstructs_exact_sources[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-derived-proof-reconstructs-exact-sources-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3601be07dda2246d4e2c8eb6186ec4576ae4b8973e42e03f770f54c8678807d5"
    },
    "tests/test_foundation_query_integrity.py::test_persisted_derived_proof_reconstructs_exact_sources[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-persisted-derived-proof-reconstructs-exact-sources-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3601be07dda2246d4e2c8eb6186ec4576ae4b8973e42e03f770f54c8678807d5"
    },
    "tests/test_foundation_query_integrity.py::test_same_generation_rule_mapping_replacement_fails_closed[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-same-generation-rule-mapping-replacement-fails-closed-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "086ccda647208e0bfce6d64d07e2a1e6ef73b64138f341d5e2b890daafa2f283"
    },
    "tests/test_foundation_query_integrity.py::test_same_generation_rule_mapping_replacement_fails_closed[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-same-generation-rule-mapping-replacement-fails-closed-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "086ccda647208e0bfce6d64d07e2a1e6ef73b64138f341d5e2b890daafa2f283"
    },
    "tests/test_foundation_query_integrity.py::test_malformed_rule_clause_stance_fails_closed[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-malformed-rule-clause-stance-fails-closed-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e7160cd13e07f2e57ebe64875e4f8acbb34f38354c2e9bc4273b519fc24dfbf6"
    },
    "tests/test_foundation_query_integrity.py::test_malformed_rule_clause_stance_fails_closed[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-query-malformed-rule-clause-stance-fails-closed-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e7160cd13e07f2e57ebe64875e4f8acbb34f38354c2e9bc4273b519fc24dfbf6"
    }
}

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.decision import DecisionAction
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.persistence import Fact, StaleRevisionError, memory_stores, open_stores
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from tests.test_foundation_semantics import _matrix_expression, _matrix_relation, _matrix_situation


@pytest.fixture
def stores(request, tmp_path):
    if request.param == "memory":
        store = memory_stores(authority_generation="authority:test", model_identity="model:test")
    else:
        store = open_stores(tmp_path / "query.sqlite", authority_generation="authority:test", model_identity="model:test")
    try:
        yield store
    finally:
        store.close()


def fact(ref, predicate="rel:likes", subject="entity:alice", object_ref="entity:bob", **kw):
    return Fact(ref, "op:relation", {"predicate_ref": predicate,
        "role:subject": subject, "role:object": object_ref}, **kw)


def clause(predicate, subject="?x", object_ref="?y"):
    return {"operator": "op:relation", "args": {"predicate_ref": predicate,
        "role:subject": subject, "role:object": object_ref}}


def rule(ref, antecedent, consequent):
    return SimpleNamespace(rule_ref=ref, reviewed=True, source_ref="review:" + ref,
        antecedent=tuple(antecedent), consequent=tuple(consequent))


def query(stores, predicate="rel:likes", rules=(), wrapper="positive", situation=None):
    app = replace(_matrix_relation(), predicate_ref=predicate)
    expression = _matrix_expression(app, wrapper)
    return QueryDecisionOwner(stores, RuntimeConfig.release(),
        SimpleNamespace(generation=stores.revision_pin().authority_generation,
            atoms={}, capabilities={},
            rules={r.rule_ref: r for r in rules})).evaluate_full(
            expression, project_expression(expression), situation or _matrix_situation(stores))


def assert_exhausted(result):
    q = result.query_results[0]
    assert q.status is QueryStatus.BUDGET_EXHAUSTED
    assert q.bindings == () and q.proof is None
    assert result.contribution.action is DecisionAction.NO_OP
    assert result.contribution.answer_expression_ref is None
    assert result.contribution.proof_refs == ()


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_relevant_fact_after_irrelevant_prefix_is_not_unknown(stores):
    stores.world.commit(tuple(fact(f"fact:a{i:04}", subject=f"entity:other{i}") for i in range(300))
        + (fact("fact:z"),), expected_revision=0)
    assert query(stores).query_results[0].status is QueryStatus.SUPPORTED


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_opposition_after_irrelevant_prefix_survives(stores):
    stores.world.commit((fact("fact:a"),)
        + tuple(fact(f"fact:m{i:04}", object_ref=f"entity:other{i}") for i in range(300))
        + (fact("fact:z", stance="deny"),), expected_revision=0)
    assert query(stores).query_results[0].status is QueryStatus.CONFLICT


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_relevant_overflow_never_answers_from_partial_support(stores):
    stores.world.commit(tuple(fact(f"fact:{i:04}") for i in range(257)), expected_revision=0)
    assert_exhausted(query(stores))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_reported_evidence_is_not_unqualified_truth(stores):
    stores.world.commit((fact("fact:reported", proof={"placement": "reported"}),), expected_revision=0)
    assert query(stores).query_results[0].status is QueryStatus.UNKNOWN
    assert query(stores, wrapper="reported").query_results[0].status is QueryStatus.SUPPORTED


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_rule_does_not_launder_reported_premise(stores):
    stores.world.commit((fact("fact:reported", proof={"placement": "reported"}),), expected_revision=0)
    r = rule("rule:knows", (clause("rel:likes"),), (clause("rel:knows"),))
    assert query(stores, "rel:knows", (r,)).query_results[0].status is QueryStatus.UNKNOWN


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_rule_source_provenance_survives(stores):
    stores.world.commit((fact("fact:likes", proof={"source": "source:observation"}),), expected_revision=0)
    r = rule("rule:knows", (clause("rel:likes"),), (clause("rel:knows"),))
    proof = query(stores, "rel:knows", (r,)).query_results[0].proof
    assert proof is not None
    assert r.source_ref in proof.source_refs


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_nonconverged_seven_hop_rule_chain_is_budget_not_unknown(stores):
    stores.world.commit((fact("fact:base", predicate="rel:0"),), expected_revision=0)
    rules = tuple(rule(f"rule:{i}", (clause(f"rel:{i}"),), (clause(f"rel:{i+1}"),)) for i in range(7))
    assert_exhausted(query(stores, "rel:7", rules))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_direct_owner_rejects_stale_situation_pin(stores):
    situation = _matrix_situation(stores)
    stores.world.commit((fact("fact:late"),), expected_revision=0)
    with pytest.raises(StaleRevisionError):
        query(stores, situation=situation)


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_backward_demands_include_every_conjunct_and_intermediate_entity(stores):
    stores.world.commit((fact("fact:ab", "rel:left", object_ref="entity:middle"),
        fact("fact:bc", "rel:right", subject="entity:middle")), expected_revision=0)
    r = rule("rule:joined", (clause("rel:left", "?x", "?mid"),
        clause("rel:right", "?mid", "?y")), (clause("rel:joined"),))
    assert query(stores, "rel:joined", (r,)).query_results[0].status is QueryStatus.SUPPORTED


@pytest.mark.parametrize(("stores", "damage"), (
    ("memory", "missing"), ("memory", "cycle"), ("memory", "unproven"),
    ("memory", "premises_only"), ("memory", "invalid_rule"), ("memory", "empty_premises"),
    ("memory", "invalid_parent"), ("memory", "invalid_substitution"), ("memory", "wrong_conclusion"),
    ("sqlite", "missing"), ("sqlite", "cycle"), ("sqlite", "unproven"),
    ("sqlite", "premises_only"), ("sqlite", "invalid_rule"), ("sqlite", "empty_premises"),
    ("sqlite", "invalid_parent"), ("sqlite", "invalid_substitution"), ("sqlite", "wrong_conclusion")),
    indirect=("stores",), ids=("memory-missing", "memory-cycle", "memory-unproven",
        "memory-premises-only", "memory-invalid-rule", "memory-empty-premises",
        "memory-invalid-parent", "memory-invalid-substitution", "memory-wrong-conclusion",
        "sqlite-missing", "sqlite-cycle", "sqlite-unproven", "sqlite-premises-only",
        "sqlite-invalid-rule", "sqlite-empty-premises", "sqlite-invalid-parent",
        "sqlite-invalid-substitution", "sqlite-wrong-conclusion"))
def test_persisted_invalid_derived_proof_fails_closed(stores, damage):
    proof = {"rule_ref": "rule:knows", "premise_fact_refs": ("fact:absent",)}
    if damage == "cycle":
        proof["premise_fact_refs"] = ("fact:derived",)
    if damage == "unproven":
        proof = {}
    if damage == "premises_only":
        proof.pop("rule_ref")
    if damage == "invalid_rule":
        proof["rule_ref"] = 42
    if damage == "empty_premises":
        proof["premise_fact_refs"] = ()
    if damage == "invalid_parent":
        proof["premise_fact_refs"] = (42,)
    if damage == "invalid_substitution":
        proof["substitutions"] = (("?x", 42),)
    if damage == "wrong_conclusion":
        proof["premise_fact_refs"] = ("fact:base",)
        stores.world.commit((fact("fact:base", "rel:base", subject="entity:other"),), expected_revision=0)
    stores.world.commit((fact("fact:derived", derived=True, proof=proof),), expected_revision=stores.world.revision)
    r = rule("rule:knows", (clause("rel:base"),), (clause("rel:likes"),))
    if damage == "cycle":
        r = rule("rule:knows", (clause("rel:likes"),), (clause("rel:likes"),))
    assert_exhausted(query(stores, rules=(r,)))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_relevant_rule_limit_overrides_initial_support(stores):
    stores.world.commit((fact("fact:supported"),), expected_revision=0)
    rules = tuple(rule(f"rule:{i}", (clause(f"rel:base{i}"),), (clause("rel:likes"),)) for i in range(65))
    assert_exhausted(query(stores, rules=rules))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_irrelevant_rules_do_not_consume_relevant_scan_limit(stores):
    stores.world.commit((fact("fact:supported"),), expected_revision=0)
    rules = tuple(rule(f"rule:{i}", (clause(f"rel:base{i}"),), (clause(f"rel:other{i}"),)) for i in range(100))
    assert query(stores, rules=rules).query_results[0].status is QueryStatus.SUPPORTED


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_all_saturated_postings_conservatively_exhaust_small_intersection(stores):
    rows = tuple(fact(f"fact:left{i}", object_ref=f"entity:o{i}") for i in range(257))
    rows += tuple(fact(f"fact:right{i}", subject=f"entity:s{i}") for i in range(257))
    stores.world.commit((*rows, fact("fact:joint")), expected_revision=0)
    assert_exhausted(query(stores))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_rule_alternative_derivations_preserve_both_sources(stores):
    stores.world.commit((fact("fact:base", "rel:base", proof={"source": "source:base"}),), expected_revision=0)
    rules = tuple(rule(f"rule:{i}", (clause("rel:base"),), (clause("rel:likes"),)) for i in range(2))
    result = query(stores, rules=rules).query_results[0]
    assert result.status is QueryStatus.SUPPORTED
    assert len([ref for ref in result.retrieval_refs if ref.startswith("r3_derived_fact:")]) == 2
    assert result.proof.rule_refs in (("rule:0",), ("rule:1",))
    assert "review:" + result.proof.rule_refs[0] in result.proof.source_refs


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_rule_join_overflow_does_not_return_partial_answer(stores):
    stores.world.commit(tuple(fact(f"fact:l{i}", "rel:left", object_ref=f"entity:l{i}") for i in range(17))
        + tuple(fact(f"fact:r{i}", "rel:right", subject=f"entity:r{i}") for i in range(17)), expected_revision=0)
    r = rule("rule:cross", (clause("rel:left", "?x", "?a"), clause("rel:right", "?b", "?y")),
        (clause("rel:likes"),))
    assert_exhausted(query(stores, rules=(r,)))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_unflagged_empty_derived_witness_cannot_become_direct_fact(stores):
    stores.world.commit((fact("fact:unproven", proof={"premise_fact_refs": ()}),), expected_revision=0)
    assert_exhausted(query(stores))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_persisted_proof_premises_are_verified_inside_query_snapshot(stores, monkeypatch):
    stores.world.commit((fact("fact:base", "rel:base", proof={"source": "source:base"}),
        fact("fact:derived", derived=True, proof={"placement": "derived", "rule_ref": "rule:derive",
            "premise_fact_refs": ("fact:base",), "substitutions": (("?x", "entity:alice"), ("?y", "entity:bob"))})),
        expected_revision=0)
    r = rule("rule:derive", (clause("rel:base"),), (clause("rel:likes"),))
    real_get = stores.world.get
    checked = []
    def get(ref):
        conn = getattr(stores._backend, "_conn", None)
        if conn is not None:
            assert conn.in_transaction
        checked.append(ref)
        return real_get(ref)
    monkeypatch.setattr(stores.world, "get", get)
    proof = query(stores, rules=(r,)).query_results[0].proof
    assert proof is not None
    assert "fact:base" in checked
    assert {"source:base", "review:rule:derive"} <= set(proof.source_refs)
    assert any("fact:base" in node.source_fact_refs for node in proof.nodes)


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_rule_dependency_index_is_built_at_construction_and_not_scanned_by_first_query(stores):
    class Rules(dict):
        scans = 0
        def items(self):
            self.scans += 1
            return super().items()
    rules = Rules()
    owner = QueryDecisionOwner(stores, RuntimeConfig.release(), SimpleNamespace(
        generation=stores.revision_pin().authority_generation,
        atoms={}, capabilities={}, rules=rules))
    assert rules.scans == 1
    expression = _matrix_expression(_matrix_relation())
    owner.evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
    assert rules.scans == 1


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_malformed_fact_stance_fails_closed(stores):
    stores.world.commit((fact("fact:invalid-stance", stance="banana"),), expected_revision=0)

    assert_exhausted(query(stores))


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_persisted_derived_proof_reconstructs_exact_sources(stores):
    stores.world.commit((
        fact("fact:base", "rel:base", proof={"source": "source:base"}),
        fact("fact:derived", derived=True, proof={
            "placement": "derived",
            "rule_ref": "rule:derive",
            "premise_fact_refs": ("fact:base",),
            "substitutions": (("?x", "entity:alice"), ("?y", "entity:bob")),
            "source": "source:forged-single",
            "source_refs": ("source:forged-list",),
        }),
    ), expected_revision=0)
    r = rule("rule:derive", (clause("rel:base"),), (clause("rel:likes"),))

    result = query(stores, rules=(r,)).query_results[0]

    assert result.status is QueryStatus.SUPPORTED
    assert result.proof is not None
    assert result.proof.source_refs == ("review:rule:derive", "source:base")


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_same_generation_rule_mapping_replacement_fails_closed(stores):
    stores.world.commit((fact("fact:base", "rel:base"),), expected_revision=0)
    authority = SimpleNamespace(
        generation=stores.revision_pin().authority_generation,
        atoms={}, capabilities={}, rules={},
    )
    owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
    injected = rule("rule:injected", (clause("rel:base"),), (clause("rel:likes"),))
    authority.rules = {injected.rule_ref: injected}
    expression = _matrix_expression(_matrix_relation())

    result = owner.evaluate_full(
        expression, project_expression(expression), _matrix_situation(stores)
    )

    assert_exhausted(result)


@pytest.mark.parametrize("stores", ("memory", "sqlite"), indirect=True, ids=("memory", "sqlite"))
def test_malformed_rule_clause_stance_fails_closed(stores):
    stores.world.commit((fact("fact:base", "rel:base"),), expected_revision=0)
    bad_consequent = clause("rel:likes")
    bad_consequent["stance"] = "banana"
    malformed = rule("rule:malformed", (clause("rel:base"),), (bad_consequent,))

    assert_exhausted(query(stores, rules=(malformed,)))


def test_pinned_atom_registry_does_not_supply_implicit_query_support(linked_authority):
    from cemm_authoritative_hybrid.expressions import GroundedReference, LiteralValue, RoleBinding, SemanticApplication, SemanticExpression
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        app = SemanticApplication("application:metadata-question", "op:type", "concept:mother",
            (RoleBinding("role:subject", GroundedReference("concept:mother")),
             RoleBinding("role:type", LiteralValue("string", "concept"))))
        expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _matrix_situation(stores))
        query = result.query_results[0]
        assert query.status is QueryStatus.UNKNOWN
        assert query.proof is None
        assert query.bindings == ()
        assert set(query.retrieval_refs) <= set(linked_authority.rules)
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


def test_pinned_explicit_type_fact_preserves_binding_and_attributed_proof(linked_authority):
    from cemm_authoritative_hybrid.expressions import BoundVariable, GroundedReference, RoleBinding, SemanticApplication, SemanticExpression, VariableBinder
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        row = Fact("fact:foundation-type", "op:type", {"predicate_ref": "concept:mother",
            "role:subject": "entity:alice", "role:type": "concept:mother"}, proof={"source": "source:reviewed-membership"})
        stores.world.commit((row,), expected_revision=0)
        app = SemanticApplication("application:type-membership", "op:type", "concept:mother",
            (RoleBinding("role:subject", BoundVariable("?member")),
             RoleBinding("role:type", GroundedReference("concept:mother"))))
        binder = VariableBinder("binder:member", "?member", app.application_ref)
        expression = SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))
        pin = stores.revision_pin()
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _matrix_situation(stores))
        query = result.query_results[0]
        variable_ref = expression.binders[0].variable_ref
        assert query.status is QueryStatus.SUPPORTED
        assert query.bindings == ((variable_ref, "entity:alice"),)
        assert query.proof is not None
        assert query.proof.source_refs == ("source:reviewed-membership",)
        assert query.proof.rule_refs == ()
        assert len(query.proof.nodes) == 1
        assert query.proof.nodes[0].source_fact_refs == (row.fact_ref,)
        assert query.proof.nodes[0].substitutions == query.bindings
        assert query.proof.revision_pin == pin
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()
