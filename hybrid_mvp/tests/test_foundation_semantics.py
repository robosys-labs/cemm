"""Independent foundation containment and semantic diagnostic matrix.

Registry metadata and type membership do not answer requests for descriptive
content. The matrix independently specifies roles, scopes, admission, effects,
query proof, dialogue context and alias reuse without bootstrap-authored gold.
Its passing controls and genuine RED cases are diagnostic evidence, not completed
foundation behavior, learned generalization or phase admission.
"""
from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.contributions import ContributionExpander
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import DecisionAction, DecisionStatus
from cemm_authoritative_hybrid.dialogue import (
    DialogueObligation, DialogueObligationManager, FocusStore, ObligationKind,
    ReferenceConstraints, ReferenceResolver, VerifiedSemanticFocus,
)
from cemm_authoritative_hybrid.expression_projection import project_expression
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
    UnresolvedFiller,
    UnresolvedValue,
    VariableBinder,
    VerifiedMeaning,
)
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.persistence import Fact, RevisionPin, memory_stores, open_stores
from cemm_authoritative_hybrid.proposal_context import (
    ContributionSlot, ProposalContext, ProposalContextBuilder, VariableSlot,
    _variable_slots,
)
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from cemm_authoritative_hybrid.r3_cognition import ObserveDecisionOwner, QueryDecisionOwner, R3EvaluationOwner
from cemm_authoritative_hybrid.r3_effects import (
    AdapterRegistry, AdapterResult, AdapterStatus, EffectReceipt, EffectStatus,
    NoEffectReceipt, ObservedDelta, R3EffectGateway,
)
from cemm_authoritative_hybrid.r3_learning import LearningCoordinator
from cemm_authoritative_hybrid.r3_persistence import begin_turn, obligation_snapshot
from cemm_authoritative_hybrid.r4_contracts import (
    AssertionCompilerError,
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_pipeline import load_reviewed_scenarios
from cemm_authoritative_hybrid.situation import SituationContext
from cemm_authoritative_hybrid.runtime import RuntimeOrientationOwner
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier
from cemm_authoritative_hybrid.verifier_reconstruction import reconstruct_expected_expression

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_semantics.py::test_foundation_membership_bounded_pair_public_preserves_independent_graph[positive-pair]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-bounded-pair-public-preserves-independent-graph-positive-pair",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "30362bb49d57befcdf7fb5f33e933103ad58dc8f968ad23da0f7b44afd544928"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_bounded_pair_public_preserves_independent_graph[mixed-pair]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-bounded-pair-public-preserves-independent-graph-mixed-pair",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "30362bb49d57befcdf7fb5f33e933103ad58dc8f968ad23da0f7b44afd544928"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_bounded_pair_public_preserves_independent_graph[negative-pair]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-bounded-pair-public-preserves-independent-graph-negative-pair",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "30362bb49d57befcdf7fb5f33e933103ad58dc8f968ad23da0f7b44afd544928"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_bounded_pair_public_preserves_independent_graph[coordinated-mixed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-bounded-pair-public-preserves-independent-graph-coordinated-mixed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "30362bb49d57befcdf7fb5f33e933103ad58dc8f968ad23da0f7b44afd544928"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_proposal_prunes_impossible_local_choices[positive-pair]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-proposal-prunes-impossible-local-choices-positive-pair",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "4948516dd6a722aa8504d12e52e9366687e8b48e845dd3ce527ce6d4222d798e"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_proposal_prunes_impossible_local_choices[mixed-pair]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-proposal-prunes-impossible-local-choices-mixed-pair",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "4948516dd6a722aa8504d12e52e9366687e8b48e845dd3ce527ce6d4222d798e"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_proposal_prunes_impossible_local_choices[negative-pair]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-proposal-prunes-impossible-local-choices-negative-pair",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "4948516dd6a722aa8504d12e52e9366687e8b48e845dd3ce527ce6d4222d798e"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_proposal_prunes_impossible_local_choices[coordinated-mixed]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-proposal-prunes-impossible-local-choices-coordinated-mixed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "4948516dd6a722aa8504d12e52e9366687e8b48e845dd3ce527ce6d4222d798e"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_pruning_preserves_unresolved_frame_union": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-pruning-preserves-unresolved-frame-union",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "a3d5cbf410bbe043848ac6711e909d8e48fbb8f75ed0a60cc8d8f71334f8d364"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_pruning_preserves_nonnominal_polysemy_scope": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-pruning-preserves-nonnominal-polysemy-scope",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership-Pruning",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "c212784bb4eb7f3f95e472fd1b1c81fbe6c2fe418cb10da0cc04d225f95742a6"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_composed_malformed_graphs_preserve_all_exact_guards": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-sr4-5-composed-expression-rejects-noncanonical-graphs",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "0d8285dd7199f759b122eb85176fa2b6cae9d311acb1a3db73aabddf6e3ab22d",
        "supersedes_node_id": "tests/test_r4_assertion_compiler.py::test_sr4_5_composed_expression_rejects_noncanonical_graphs"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_public_preserves_exact_roles_scope_and_attribution[bare]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-public-preserves-exact-roles-scope-and-attribution-bare",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "4fda752cd673dabe384cdf2e521e6b81f8c142d74595de1b5f94e12211f8889d"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_public_preserves_exact_roles_scope_and_attribution[determined]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-public-preserves-exact-roles-scope-and-attribution-determined",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "4fda752cd673dabe384cdf2e521e6b81f8c142d74595de1b5f94e12211f8889d"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_public_preserves_exact_roles_scope_and_attribution[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-public-preserves-exact-roles-scope-and-attribution-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "4fda752cd673dabe384cdf2e521e6b81f8c142d74595de1b5f94e12211f8889d"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_public_preserves_exact_roles_scope_and_attribution[multiword]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-public-preserves-exact-roles-scope-and-attribution-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "4fda752cd673dabe384cdf2e521e6b81f8c142d74595de1b5f94e12211f8889d"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_form_geometry_has_typed_nonsemantic_gaps[english]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-form-geometry-has-typed-nonsemantic-gaps-english",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "662ef2598f93483326258da894778ab916179f0583d5a7d93a7d46011d3ceb16"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_form_geometry_has_typed_nonsemantic_gaps[spanish]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-form-geometry-has-typed-nonsemantic-gaps-spanish",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "662ef2598f93483326258da894778ab916179f0583d5a7d93a7d46011d3ceb16"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_reviewed_alias_inherits_type_frame_without_pack_changes[unseen-alias]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-reviewed-alias-inherits-type-frame-without-pack-changes-unseen-alias",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3c94ed6bc6222c64587b1d04272834ded76c8853c519da101357b3aac7548330"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_reviewed_alias_inherits_type_frame_without_pack_changes[unseen-multiword]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-reviewed-alias-inherits-type-frame-without-pack-changes-unseen-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3c94ed6bc6222c64587b1d04272834ded76c8853c519da101357b3aac7548330"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_reviewed_alias_inherits_type_frame_without_pack_changes[spanish]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-reviewed-alias-inherits-type-frame-without-pack-changes-spanish",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3c94ed6bc6222c64587b1d04272834ded76c8853c519da101357b3aac7548330"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_reviewed_alias_inherits_type_frame_without_pack_changes[spanish-unseen-multiword]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-membership-reviewed-alias-inherits-type-frame-without-pack-changes-spanish-unseen-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3c94ed6bc6222c64587b1d04272834ded76c8853c519da101357b3aac7548330"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_composed_gold_uses_world_membership": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-membership-composed-gold-uses-world-membership",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "f8c938567d14d1e9b16873ee3eaf36e97b43055cffb1544f9bef9a2e6fc26a8c"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_composed_multiroot_canonicalization_and_linear_work": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-sr4-5-true-multi-root-and-type-role-remain-one-meaning",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "d6690d7af34837d8ba0cf7ffd35f5f53a712c03888c78588402c0a2af86bb10a",
        "supersedes_node_id": "tests/test_r4_assertion_compiler.py::test_sr4_5_true_multi_root_and_type_role_remain_one_meaning"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_composed_gold_rejects_nonmembership[registry-kind]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-membership-composed-gold-rejects-nonmembership-registry-kind",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "b42e868d386f88ff038d1e630355e43cc1c4cd361222935c1d9794bb8d432c94"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_composed_gold_rejects_nonmembership[wrong-class]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-membership-composed-gold-rejects-nonmembership-wrong-class",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "b42e868d386f88ff038d1e630355e43cc1c4cd361222935c1d9794bb8d432c94"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_composed_gold_rejects_nonmembership[literal-instance]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-membership-composed-gold-rejects-nonmembership-literal-instance",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "b42e868d386f88ff038d1e630355e43cc1c4cd361222935c1d9794bb8d432c94"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_composed_gold_rejects_nonmembership[wrong-instance-kind]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-membership-composed-gold-rejects-nonmembership-wrong-instance-kind",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "b42e868d386f88ff038d1e630355e43cc1c4cd361222935c1d9794bb8d432c94"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_multiclause_reconstruction_keeps_instance_and_scope_owner[scope-transfer]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-multiclause-reconstruction-keeps-instance-and-scope-owner-scope-transfer",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "c268729d98b8803fc9cca02cd6f08600ccc30b8923d0271e75bdba076d96ca10"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_multiclause_reconstruction_keeps_instance_and_scope_owner[widened-instance]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-multiclause-reconstruction-keeps-instance-and-scope-owner-widened-instance",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "c268729d98b8803fc9cca02cd6f08600ccc30b8923d0271e75bdba076d96ca10"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_requires_reviewed_predication_not_juxtaposition[juxtaposition]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-requires-reviewed-predication-not-juxtaposition-juxtaposition",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "25ad5cc953137ce761439d303453627410b0a4d41fa5310c797b674f7e8eddf8"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_requires_reviewed_predication_not_juxtaposition[separate-clause]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-requires-reviewed-predication-not-juxtaposition-separate-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "25ad5cc953137ce761439d303453627410b0a4d41fa5310c797b674f7e8eddf8"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_requires_reviewed_predication_not_juxtaposition[reversed]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-requires-reviewed-predication-not-juxtaposition-reversed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "25ad5cc953137ce761439d303453627410b0a4d41fa5310c797b674f7e8eddf8"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_independent_reconstruction_rejects_source_forgery[missing-gap]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-independent-reconstruction-rejects-source-forgery-missing-gap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "d4cae991cccb8affb09532d6e8d0363549a6184df0600a0970b1b3155b025440"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_independent_reconstruction_rejects_source_forgery[forged-gap]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-independent-reconstruction-rejects-source-forgery-forged-gap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "d4cae991cccb8affb09532d6e8d0363549a6184df0600a0970b1b3155b025440"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_independent_reconstruction_rejects_source_forgery[missing-binder]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-independent-reconstruction-rejects-source-forgery-missing-binder",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "d4cae991cccb8affb09532d6e8d0363549a6184df0600a0970b1b3155b025440"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_independent_reconstruction_rejects_source_forgery[missing-determiner]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-independent-reconstruction-rejects-source-forgery-missing-determiner",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "d4cae991cccb8affb09532d6e8d0363549a6184df0600a0970b1b3155b025440"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_independent_reconstruction_rejects_source_forgery[foreign-instance]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-independent-reconstruction-rejects-source-forgery-foreign-instance",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "d4cae991cccb8affb09532d6e8d0363549a6184df0600a0970b1b3155b025440"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_context_rejects_unowned_predication_geometry[remote-binder]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-context-rejects-unowned-predication-geometry-remote-binder",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "5a66bd9756abeff2d6ea248627aad813261cfecca182738b83520468f5f52c0c"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_context_rejects_unowned_predication_geometry[remote-determiner]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-context-rejects-unowned-predication-geometry-remote-determiner",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "5a66bd9756abeff2d6ea248627aad813261cfecca182738b83520468f5f52c0c"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_context_rejects_unowned_predication_geometry[punctuation-gap]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-context-rejects-unowned-predication-geometry-punctuation-gap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "5a66bd9756abeff2d6ea248627aad813261cfecca182738b83520468f5f52c0c"
    },
    "tests/test_foundation_semantics.py::test_foundation_membership_context_rejects_unowned_predication_geometry[semantic-gap]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-membership-context-rejects-unowned-predication-geometry-semantic-gap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Membership",
        "owner_ref": "form-context",
        "source_ast_sha256": "5a66bd9756abeff2d6ea248627aad813261cfecca182738b83520468f5f52c0c"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[negative-compound]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-negative-compound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[reported-nested]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-reported-nested",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[modal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-modal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[relation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-relation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[unresolved-state]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-unresolved-state",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[bound-state]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-bound-state",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[literal-state]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-literal-state",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_unsupported_admission_retains_exact_occurrence[proposition-state]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-unsupported-admission-retains-exact-occurrence-proposition-state",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c6469632d8fb277baffcc034451455713f9abae887bd487f8abacbae2e1119a7"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_conflicts_require_applicable_signed_same_context_claims[actual-conflict]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-conflicts-require-applicable-signed-same-context-claims-actual-conflict",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "de34ea1181e15838f5cb2e0207f71697fff23b2a1c095efdd6d1bd9450e91432"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_conflicts_require_applicable_signed_same_context_claims[two-denials]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-conflicts-require-applicable-signed-same-context-claims-two-denials",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "de34ea1181e15838f5cb2e0207f71697fff23b2a1c095efdd6d1bd9450e91432"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_conflicts_require_applicable_signed_same_context_claims[different-contexts]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-conflicts-require-applicable-signed-same-context-claims-different-contexts",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "de34ea1181e15838f5cb2e0207f71697fff23b2a1c095efdd6d1bd9450e91432"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_learning_requires_eligible_directive_root[positive]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-learning-requires-eligible-directive-root-positive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "59ad7761db700f5ba62d0f3795adc4c0237fb52109d8d07d8cdca3be38b56efd"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_learning_requires_eligible_directive_root[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-learning-requires-eligible-directive-root-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "59ad7761db700f5ba62d0f3795adc4c0237fb52109d8d07d8cdca3be38b56efd"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_learning_requires_eligible_directive_root[reported]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-learning-requires-eligible-directive-root-reported",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "59ad7761db700f5ba62d0f3795adc4c0237fb52109d8d07d8cdca3be38b56efd"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_learning_requires_eligible_directive_root[conditional]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-learning-requires-eligible-directive-root-conditional",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "59ad7761db700f5ba62d0f3795adc4c0237fb52109d8d07d8cdca3be38b56efd"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_learning_requires_eligible_directive_root[speech]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-learning-requires-eligible-directive-root-speech",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "59ad7761db700f5ba62d0f3795adc4c0237fb52109d8d07d8cdca3be38b56efd"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[positive-request]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-positive-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[positive-simulate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-positive-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[negative-request]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-negative-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[negative-simulate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-negative-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[reported-request]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-reported-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[reported-simulate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-reported-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[conditional-request]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-conditional-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[conditional-simulate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-conditional-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[speech-request]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-speech-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[speech-simulate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-speech-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[multiple-roots-request]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-multiple-roots-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_transition_selects_only_eligible_root[multiple-roots-simulate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-transition-selects-only-eligible-root-multiple-roots-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "650ba856e90b8605ef9fa062623b812ccf8248b0b71a2ff70769f1e2f1b24fd4"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_query_constraints_are_not_flat_fact_patterns[unresolved-role]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-query-constraints-are-not-flat-fact-patterns-unresolved-role",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "9e545a174b8990c280a0bbc38475e90ce15d90f038a29f5ef8c7066062410870"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_query_constraints_are_not_flat_fact_patterns[unresolved-qualifier]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-query-constraints-are-not-flat-fact-patterns-unresolved-qualifier",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "9e545a174b8990c280a0bbc38475e90ce15d90f038a29f5ef8c7066062410870"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_query_constraints_are_not_flat_fact_patterns[proposition-role]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-query-constraints-are-not-flat-fact-patterns-proposition-role",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "9e545a174b8990c280a0bbc38475e90ce15d90f038a29f5ef8c7066062410870"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_query_constraints_are_not_flat_fact_patterns[proposition-qualifier]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-query-constraints-are-not-flat-fact-patterns-proposition-qualifier",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "9e545a174b8990c280a0bbc38475e90ce15d90f038a29f5ef8c7066062410870"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_compound_conflict_keeps_both_actual_sources[link-conjunction]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-compound-conflict-keeps-both-actual-sources-link-conjunction",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c8828a6384f778020c9382004f6e30be4b076d0bfd78907cca5325e2dee1b2be"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_compound_conflict_keeps_both_actual_sources[link-condition]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-compound-conflict-keeps-both-actual-sources-link-condition",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c8828a6384f778020c9382004f6e30be4b076d0bfd78907cca5325e2dee1b2be"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_no_effect_terminal_retry_is_identity_preserving": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-no-effect-terminal-retry-is-identity-preserving",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "9c853b5ef5d526d99ec3dbbdeb63031ce4766fac6b90ef4895737d40642a6817"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_disjoint_joint_query_bindings_are_not_opposing_proof": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-disjoint-joint-query-bindings-are-not-opposing-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e41ffd872f6f03743ec960edfc86f5b966b7d694ac1a7da72533d6a83291a492"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_opposing_query_evidence_keeps_substitutions_distinct[same-binding]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-opposing-query-evidence-keeps-substitutions-distinct-same-binding",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a9ebf21f9df81d62bbb55f8c0211ae1db5d7094f6642dce1e1d5439b91c9b444"
    },
    "tests/test_foundation_semantics.py::test_foundation_safety_opposing_query_evidence_keeps_substitutions_distinct[different-bindings]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-opposing-query-evidence-keeps-substitutions-distinct-different-bindings",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Safety",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a9ebf21f9df81d62bbb55f8c0211ae1db5d7094f6642dce1e1d5439b91c9b444"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_ordered_relation_proof[forward]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-ordered-relation-proof-forward",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "cdf5f76d8d277715971c01e5d5f6a0bc246123008c917a33ba41f7123565ba64"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_ordered_relation_proof[reversed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-ordered-relation-proof-reversed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "cdf5f76d8d277715971c01e5d5f6a0bc246123008c917a33ba41f7123565ba64"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_ordered_relation_proof[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-ordered-relation-proof-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "cdf5f76d8d277715971c01e5d5f6a0bc246123008c917a33ba41f7123565ba64"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_ordered_relation_proof[conflict]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-ordered-relation-proof-conflict",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "cdf5f76d8d277715971c01e5d5f6a0bc246123008c917a33ba41f7123565ba64"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_ordinary_type_surface_matches_independent_membership": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-matrix-ordinary-type-surface-matches-independent-membership",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "form-context",
        "source_ast_sha256": "b912a2babfa9c3c22d43c5ac6e472d92f0aef51e81fcb18aa6a3ce3e83a696a4"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_admission_preserves_polarity_and_enclosing_scope[positive]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-admission-preserves-polarity-and-enclosing-scope-positive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "90bd2c9d5cc16c4fe72c6daff96d05a28a2ecf22aedae5b16d630503d736a24d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_admission_preserves_polarity_and_enclosing_scope[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-admission-preserves-polarity-and-enclosing-scope-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "90bd2c9d5cc16c4fe72c6daff96d05a28a2ecf22aedae5b16d630503d736a24d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_admission_preserves_polarity_and_enclosing_scope[reported]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-admission-preserves-polarity-and-enclosing-scope-reported",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "90bd2c9d5cc16c4fe72c6daff96d05a28a2ecf22aedae5b16d630503d736a24d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_admission_preserves_polarity_and_enclosing_scope[conditional]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-admission-preserves-polarity-and-enclosing-scope-conditional",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "90bd2c9d5cc16c4fe72c6daff96d05a28a2ecf22aedae5b16d630503d736a24d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_admission_preserves_polarity_and_enclosing_scope[speech]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-admission-preserves-polarity-and-enclosing-scope-speech",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "90bd2c9d5cc16c4fe72c6daff96d05a28a2ecf22aedae5b16d630503d736a24d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_admission_preserves_polarity_and_enclosing_scope[opposing-roots]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-admission-preserves-polarity-and-enclosing-scope-opposing-roots",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "90bd2c9d5cc16c4fe72c6daff96d05a28a2ecf22aedae5b16d630503d736a24d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_explicit_operation_permission_and_receipt[permitted]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-explicit-operation-permission-and-receipt-permitted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "f53b50e5db04792dc5dbea56af4f41718032b000583a56b599c00dd401b8a8df"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_explicit_operation_permission_and_receipt[denied]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-explicit-operation-permission-and-receipt-denied",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "f53b50e5db04792dc5dbea56af4f41718032b000583a56b599c00dd401b8a8df"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_scoped_operation_does_not_authorize_effect[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-scoped-operation-does-not-authorize-effect-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "0dc963d928ccd2007734cfe0a8ac95d688192083dc3c59a5eed1623012624554"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_scoped_operation_does_not_authorize_effect[reported]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-scoped-operation-does-not-authorize-effect-reported",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "0dc963d928ccd2007734cfe0a8ac95d688192083dc3c59a5eed1623012624554"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_scoped_operation_does_not_authorize_effect[conditional]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-scoped-operation-does-not-authorize-effect-conditional",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "0dc963d928ccd2007734cfe0a8ac95d688192083dc3c59a5eed1623012624554"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_non_directive_has_no_device_execution[event-claim]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-non-directive-has-no-device-execution-event-claim",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "96020df7ff21adc09afe403e3b94cac9a721a1afd5a8e3237c12ee0d9928e7d9"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_non_directive_has_no_device_execution[capability-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-non-directive-has-no-device-execution-capability-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "96020df7ff21adc09afe403e3b94cac9a721a1afd5a8e3237c12ee0d9928e7d9"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_unknown_role_is_not_dropped_from_query[unresolved-object]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-unknown-role-is-not-dropped-from-query-unresolved-object",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "995b04a6c4620095e0dbd980c6c4aab77963b1d182c9ce8209a50a13160efe22"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_unknown_role_is_not_dropped_from_query[known-root-plus-unresolved]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-unknown-role-is-not-dropped-from-query-known-root-plus-unresolved",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "995b04a6c4620095e0dbd980c6c4aab77963b1d182c9ce8209a50a13160efe22"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_speech_content_focus_keeps_speaker_session_and_recency[current-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-speech-content-focus-keeps-speaker-session-and-recency-current-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "situation-context",
        "source_ast_sha256": "14abeaa25692562d5ba85ce974aea76c9c8856fd7faab9cbd79e06a2d2e6c34d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_speech_content_focus_keeps_speaker_session_and_recency[after-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-speech-content-focus-keeps-speaker-session-and-recency-after-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "situation-context",
        "source_ast_sha256": "14abeaa25692562d5ba85ce974aea76c9c8856fd7faab9cbd79e06a2d2e6c34d"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_fresh_fragment_requires_clarification": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-matrix-fresh-fragment-requires-clarification",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "form-context",
        "source_ast_sha256": "b50c2c45bfce6f4b14a53b27f28a8f9c947e07189dcffc155ac96a3c27983334"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_alias_directive_binds_actual_prior_query": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-alias-directive-binds-actual-prior-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7caacfc26baf1a7b0b6f70927ab2e7f122e47bcf578fd8037d3e106eaf74ef37"
    },
    "tests/test_foundation_semantics.py::test_foundation_matrix_reviewed_alias_survives_restart_and_unseen_reversal": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-matrix-reviewed-alias-survives-restart-and-unseen-reversal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-3",
        "owner_ref": "form-context",
        "source_ast_sha256": "8a907bacf120df2adbd0ba11880deb4630b6500a086dd7777cafe0a38d47ae9e"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[what-cemm]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-what-cemm",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[who-cemm]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-who-cemm",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[where-cemm]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-where-cemm",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[define-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-define-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[what-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-what-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_definition_does_not_substitute_a_known_type_member[define-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-definition-does-not-substitute-a-known-type-member-define-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "0813e012b4caaea8f9a4758a39b20ffdb72464d7e89a8d72ffa112d36347dfd4"
    },
    "tests/test_foundation_semantics.py::test_definition_does_not_substitute_a_known_type_member[what-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-definition-does-not-substitute-a-known-type-member-what-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "0813e012b4caaea8f9a4758a39b20ffdb72464d7e89a8d72ffa112d36347dfd4"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_form_cue_stays_unresolved[bare]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-form-cue-stays-unresolved-bare",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "ea8fa35204d3ab3fd0c50f110c3cedb50ec919030ae8f7a60a5f09fe8b3e9e3a"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_form_cue_stays_unresolved[following-clause]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-form-cue-stays-unresolved-following-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "ea8fa35204d3ab3fd0c50f110c3cedb50ec919030ae8f7a60a5f09fe8b3e9e3a"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_form_cue_stays_unresolved[preceding-clause]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-form-cue-stays-unresolved-preceding-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "ea8fa35204d3ab3fd0c50f110c3cedb50ec919030ae8f7a60a5f09fe8b3e9e3a"
    },
    "tests/test_foundation_semantics.py::test_context_rejects_variable_sources_without_exact_query_ownership[nominal]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-context-rejects-variable-sources-without-exact-query-ownership-nominal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "625d23c57b37ec1fb1db9231945155a745d4363cedd37d91f99901bf142a0348"
    },
    "tests/test_foundation_semantics.py::test_context_rejects_variable_sources_without_exact_query_ownership[binder-only]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-context-rejects-variable-sources-without-exact-query-ownership-binder-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "625d23c57b37ec1fb1db9231945155a745d4363cedd37d91f99901bf142a0348"
    },
    "tests/test_foundation_semantics.py::test_context_rejects_variable_sources_without_exact_query_ownership[query-plus-nominal]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-context-rejects-variable-sources-without-exact-query-ownership-query-plus-nominal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "625d23c57b37ec1fb1db9231945155a745d4363cedd37d91f99901bf142a0348"
    },
    "tests/test_foundation_semantics.py::test_verifier_reconstructs_variable_source_ownership_after_context_forgery": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-verifier-reconstructs-variable-source-ownership-after-context-forgery",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "2c87c95ee8c2e1a6fcd686eba7ca6db996e188d9a6caca5ae409e5a9cd4f37e5"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_cannot_forge_a_variable_from_unresolved_source": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-cannot-forge-a-variable-from-unresolved-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "eb97dc00e6a5fcec60d53a871771a737141c1a38d5fefb3c20e42e867b65488d"
    },
    "tests/test_foundation_semantics.py::test_reviewed_interrogatives_keep_open_variable_sources[english]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-reviewed-interrogatives-keep-open-variable-sources-english",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "9a6e3d177304b3589614e3d5e2a1acfeb545c41471afa0b49df176293fcdc46a"
    },
    "tests/test_foundation_semantics.py::test_reviewed_interrogatives_keep_open_variable_sources[spanish]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-reviewed-interrogatives-keep-open-variable-sources-spanish",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "9a6e3d177304b3589614e3d5e2a1acfeb545c41471afa0b49df176293fcdc46a"
    },
    "tests/test_foundation_semantics.py::test_multiword_nominal_keeps_query_variable_and_roundtrip[determined-multiword]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-multiword-nominal-keeps-query-variable-and-roundtrip-determined-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "e0a0311b0bfb82d99ff77987b9149e4a7664ea175029b354a765cc1dbf48bd85"
    },
    "tests/test_foundation_semantics.py::test_multiword_nominal_keeps_query_variable_and_roundtrip[bare-multiword]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-multiword-nominal-keeps-query-variable-and-roundtrip-bare-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "e0a0311b0bfb82d99ff77987b9149e4a7664ea175029b354a765cc1dbf48bd85"
    },
    "tests/test_foundation_semantics.py::test_designation_surface_variable_preserves_query_and_binder_sources": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-designation-surface-variable-preserves-query-and-binder-sources",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "32da4b32b7d3898281d4e3bf9e80c7286595c8d19b50908a5fa5008597d339ad"
    },
    "tests/test_foundation_semantics.py::test_retiring_definition_cue_preserves_all_other_reviewed_form_fields": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retiring-definition-cue-preserves-all-other-reviewed-form-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "790d41bfd69ad5fbd47403c18d465017888935eebc6a1934f50870870d6f4884"
    },
    "tests/test_foundation_semantics.py::test_atom_registry_does_not_supply_implicit_query_support": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-atom-registry-does-not-supply-implicit-query-support",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "92a3176559cfc1f00a849c02d5d1279641ef46b42954c78b3628c68e728c9e1c"
    },
    "tests/test_foundation_semantics.py::test_explicit_type_fact_preserves_binding_and_attributed_proof": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-explicit-type-fact-preserves-binding-and-attributed-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "f87254046850cea44432442d425e462bd5e6f84181629f187557883e6fb03747"
    },
    "tests/test_foundation_semantics.py::test_metadata_only_definition_is_not_compilable_gold": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-metadata-only-definition-is-not-compilable-gold",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "833a43ed3526888442fdf7292eea55b6c5cc9329cbc72f1a7dc490a425d3d185"
    },
    "tests/test_foundation_semantics.py::test_explicit_ordinary_type_application_remains_compilable": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-explicit-ordinary-type-application-compiles",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "cd61d9f00df28b8f76175421a9419bacbff286e7697c700a7a9d60a281b229b9"
    },
    "tests/test_foundation_semantics.py::test_known_definition_traversal_is_retired_not_completed": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-closure-known-definition-selected-semantic-path",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "source_ast_sha256": "d1f3b4e2d83b2582594b9505553a9fa7b6ec8e843c7596d12d9ad237cf71db42",
        "supersedes_node_id": "tests/test_r3_r4_predecessor_regressions.py::test_closure_known_definition_traverses_selected_semantic_path"
    },
    "tests/test_foundation_semantics.py::test_historical_definition_gold_requires_real_semantic_content[definition-digital-agent]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-reviewed-nominal-state-relation-definition-digital-agent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "3100a25eb2b4e54a7834561ef3c1dc414565236a65a68f8b38e1bb286d4cba36",
        "supersedes_node_id": "tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-digital-agent]"
    },
    "tests/test_foundation_semantics.py::test_historical_definition_gold_requires_real_semantic_content[definition-mother]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-reviewed-nominal-state-relation-definition-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "3100a25eb2b4e54a7834561ef3c1dc414565236a65a68f8b38e1bb286d4cba36",
        "supersedes_node_id": "tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-mother]"
    }
}


def _assert_no_atom_kind_answer(result) -> None:
    assert result.verification is not None
    meaning = result.verification.selected_meaning
    if meaning is not None:
        assert not any(
            app.operator == "op:type"
            and binding.role_ref == "role:type"
            and binding.filler == LiteralValue("string", "concept")
            for app in meaning.expression.applications
            for binding in app.roles
        ), meaning.expression.as_dict()
    assert result.effect_receipt is None or isinstance(
        result.effect_receipt, NoEffectReceipt
    )


@pytest.mark.parametrize(
    "surface",
    ("What is CEMM?", "Who is CEMM?", "Where is CEMM?", "Define mother.", "What is a mother?"),
    ids=("what-cemm", "who-cemm", "where-cemm", "define-mother", "what-mother"),
)
def test_public_question_never_substitutes_registry_kind(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-question", surface)
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        _assert_no_atom_kind_answer(result)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "surface", ("Define mother.", "What is a mother?"), ids=("define-mother", "what-mother")
)
def test_definition_does_not_substitute_a_known_type_member(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        # Both existing role spellings describe Alice's membership, not mother.
        runtime.stores.world.commit(
            (
                Fact(
                    fact_ref="fact:foundation-alice-mother",
                    operator="op:type",
                    args={"predicate_ref": "concept:mother", "role:subject": "entity:alice", "role:type": "concept:mother"},
                    proof={"source": "source:reviewed-membership"},
                ),
                Fact(
                    fact_ref="fact:foundation-alice-mother-nominal",
                    operator="op:type",
                    args={"predicate_ref": "concept:mother", "role:instance": "entity:alice", "role:class": "concept:mother"},
                    proof={"source": "source:reviewed-membership"},
                ),
            ),
            expected_revision=0,
        )
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-description", surface)
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        _assert_no_atom_kind_answer(result)
        meaning = result.verification.selected_meaning
        assert meaning is None or not any(
            app.operator == "op:type" for app in meaning.expression.applications
        ), "A type member is not the requested descriptive content"
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "surface",
    ("Define mother.", "Define mother. Alice is a person.", "Alice is a person. Define mother."),
    ids=("bare", "following-clause", "preceding-clause"),
)
def test_retired_definition_form_cue_stays_unresolved(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-definition-form", surface)
        assert any(frame.operator_ref == "op:type" for frame in context.application_frames)
        assert not any(row.kind == "open_variable" for row in context.contribution_slots)
        assert context.variable_slots == ()
        assert any(row.critical for row in context.residual_evidence)
        assert ProposalContext.from_dict(context.as_dict()) == context
    finally:
        runtime.stores.close()


def _forged_variable_payload(context, source_refs):
    frame = next(frame for frame in context.application_frames if frame.operator_ref == "op:type")
    variable = VariableSlot.create(
        application_frame_ref=frame.slot_ref,
        role_ref="role:instance",
        required_kinds=("entity", "participant", "concept"),
        source_unit_refs=source_refs,
        construction_ref=None,
    )
    payload = {
        row.name: getattr(context, row.name) for row in fields(context)
        if row.init and row.name not in {"context_ref", "abi_version"}
    }
    payload["variable_slots"] = (variable,)
    return payload


@pytest.mark.parametrize(
    "source_kind", ("nominal", "binder", "mixed"), ids=("nominal", "binder-only", "query-plus-nominal"),
)
def test_context_rejects_variable_sources_without_exact_query_ownership(source_kind: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-forged-variable", "Who is a mother?")
        nominal = next(row for row in context.application_frames if row.operator_ref == "op:type")
        query = next(row for row in context.contribution_slots if row.kind == "open_variable")
        binder = next(row for row in context.contribution_slots if row.kind == "binder")
        source_refs = {
            "nominal": nominal.source_unit_refs,
            "binder": binder.source_unit_refs,
            "mixed": (*query.source_unit_refs, *nominal.source_unit_refs),
        }[source_kind]
        with pytest.raises(ValueError, match="variable.*source evidence"):
            ProposalContext.create(**_forged_variable_payload(context, source_refs))
    finally:
        runtime.stores.close()


def test_verifier_reconstructs_variable_source_ownership_after_context_forgery(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-forged-candidate", "Who mother")
        nominal = next(row for row in context.application_frames if row.operator_ref == "op:type")
        payload = _forged_variable_payload(context, nominal.source_unit_refs)
        payload["variable_slots"] = (*context.variable_slots, *payload["variable_slots"])
        # Bypass constructors to model an adversarial object. VERIFY must
        # independently reconstruct the canonical envelope, not trust its hash.
        forged = object.__new__(ProposalContext)
        for name, value in payload.items():
            object.__setattr__(forged, name, value)
        object.__setattr__(forged, "abi_version", context.abi_version)
        wire = context.as_dict()
        wire["variable_slots"] = [row.as_dict() for row in payload["variable_slots"]]
        del wire["context_ref"]
        object.__setattr__(forged, "context_ref", stable_ref("proposal_context", wire))
        forged._build_indexes()
        proposal = runtime.proposal_model.propose(forged)
        assert proposal.status == "candidates", "The forged proposal must exercise VERIFY"
        with pytest.raises(ValueError, match="variable.*source evidence"):
            ExactProgramVerifier().verify_candidates(proposal, forged)
    finally:
        runtime.stores.close()


def test_retired_definition_cannot_forge_a_variable_from_unresolved_source(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-forged-definition", "Define mother.")
        source = next(ref for ref, start, _ in context.source_unit_spans if start == 0)
        with pytest.raises(ValueError, match="variable.*source evidence"):
            ProposalContext.create(**_forged_variable_payload(context, (source,)))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    ("language", "surface"),
    (("en", "Who is a mother?"), ("es", "Quién es una madre?")),
    ids=("english", "spanish"),
)
def test_reviewed_interrogatives_keep_open_variable_sources(language: str, surface: str, tmp_path: Path) -> None:
    """Form-owner control only; this does not claim Spanish designation lookup."""
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        orientation, context = runtime.orient("session:foundation-form-control", "Who is a mother?")
        pack = json.loads((ROOT / "data" / "languages" / language / "forms.json").read_text(encoding="utf-8"))
        config = RuntimeConfig.release()
        lattice = FormResolver(pack, config).resolve(surface)
        builder = ProposalContextBuilder(runtime.authority, SemanticAffordanceIndex(runtime.authority, config), config, form_pack=pack)
        contributions, _ = builder._form_evidence_slots(orientation, lattice, {})
        query_sources = {ref for row in contributions if row.kind == "open_variable" for ref in row.source_unit_refs}
        assert query_sources
        variables = _variable_slots(lattice, contributions, context.application_frames, config)
        assert len(variables) == 1
        assert variables[0].role_ref == "role:instance"
        assert set(variables[0].source_unit_refs) <= query_sources
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "surface", ("Who is a job role?", "Who is job role?"),
    ids=("determined-multiword", "bare-multiword"),
)
def test_multiword_nominal_keeps_query_variable_and_roundtrip(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-multiword-variable", surface)
        frame = next(
            row for row in context.application_frames
            if row.predicate_target_ref == "concept:job_role"
            and row.operator_ref == "op:type" and len(row.source_unit_refs) >= 2
        )
        assert any(row.application_frame_ref == frame.slot_ref for row in context.variable_slots)
        assert ProposalContext.from_dict(context.as_dict()) == context
    finally:
        runtime.stores.close()


def test_designation_surface_variable_preserves_query_and_binder_sources(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-designation-variable", "What is your name?")
        variable = next(
            row for row in context.variable_slots
            if row.role_ref == "role:surface"
            and context.frame(row.application_frame_ref).predicate_kind == "label_type"
        )
        query_sources = {ref for row in context.contribution_slots if row.kind == "open_variable" for ref in row.source_unit_refs}
        binder_sources = {ref for row in context.contribution_slots if row.kind == "binder" for ref in row.source_unit_refs}
        assert set(variable.source_unit_refs) & query_sources
        assert set(variable.source_unit_refs) & binder_sources
        assert set(variable.source_unit_refs) <= query_sources | binder_sources
        assert ProposalContext.from_dict(context.as_dict()) == context
    finally:
        runtime.stores.close()


def test_retiring_definition_cue_preserves_all_other_reviewed_form_fields() -> None:
    pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
    assert "define" not in pack["query_projection"]
    # The exact predecessor pack, reconstructed by only restoring the retired
    # cue, must retain its known canonical hash. No other input/output field is
    # implicitly removed or regenerated.
    pack["query_projection"]["define"] = {"kind": "query"}
    assert FormResolver(pack, RuntimeConfig.release()).form_pack_hash == (
        "sha256:32f5133c901afc05cc5345bc5766d00c97518b54025cad4ca0fb3707ad40b5ad"
    )


def _situation(pin: RevisionPin) -> SituationContext:
    return SituationContext.create(
        orientation_ref="orientation:foundation",
        proposal_context_ref="proposal_context:foundation",
        mode=SemanticMode.QUERY,
        session_ref="session:foundation",
        turn_ref="turn:foundation",
        turn_index=1,
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref=None,
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref="snapshot:focus:foundation",
        focus_refs=(),
        obligation_snapshot_ref="snapshot:obligation:foundation",
        obligation_refs=(),
        capability_refs=(),
        permission_snapshot_ref="snapshot:permission:foundation",
        permission_refs=(),
        resource_snapshot_ref="snapshot:resource:foundation",
        resource_refs=(),
        adapter_snapshot_ref="snapshot:adapter:foundation",
        adapter_refs=(),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:foundation",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=("source:foundation",),
        epistemic_scope_ref="epistemic_scope:query",
        session_phase_ref="session_phase:active",
        revision_pin=pin,
    )


def test_atom_registry_does_not_supply_implicit_query_support(linked_authority) -> None:
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        app = SemanticApplication(
            "application:metadata-question", "op:type", "concept:mother",
            (RoleBinding("role:subject", GroundedReference("concept:mother")),
             RoleBinding("role:type", LiteralValue("string", "concept"))),
        )
        expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        pin = RevisionPin(linked_authority.generation, 0, 0, 0, 0, "model:foundation")
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _situation(pin)
        )
        query = result.query_results[0]
        assert query.status is QueryStatus.UNKNOWN
        assert query.proof is None
        assert query.bindings == ()
        assert set(query.retrieval_refs) <= set(linked_authority.rules)
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


def test_explicit_type_fact_preserves_binding_and_attributed_proof(linked_authority) -> None:
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        fact = Fact(
            fact_ref="fact:foundation-type",
            operator="op:type",
            args={"predicate_ref": "concept:mother", "role:subject": "entity:alice", "role:type": "concept:mother"},
            proof={"source": "source:reviewed-membership"},
        )
        stores.world.commit((fact,), expected_revision=0)
        app = SemanticApplication(
            "application:type-membership", "op:type", "concept:mother",
            (RoleBinding("role:subject", BoundVariable("?member")),
             RoleBinding("role:type", GroundedReference("concept:mother"))),
        )
        binder = VariableBinder("binder:member", "?member", app.application_ref)
        expression = SemanticExpression.create(
            applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,)
        )
        pin = RevisionPin(linked_authority.generation, 1, 0, 0, 0, "model:foundation")
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _situation(pin)
        )
        query = result.query_results[0]
        variable_ref = expression.binders[0].variable_ref
        assert query.status is QueryStatus.SUPPORTED
        assert query.bindings == ((variable_ref, "entity:alice"),)
        assert query.proof is not None
        assert query.proof.source_refs == ("source:reviewed-membership",)
        assert query.proof.rule_refs == ()
        assert len(query.proof.nodes) == 1
        assert query.proof.nodes[0].source_fact_refs == (fact.fact_ref,)
        assert query.proof.nodes[0].substitutions == query.bindings
        assert query.proof.revision_pin == pin
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


def _compile_scenario(authority, scenario):
    return ExpectedCycleContractCompiler(authority, abi_registry_ref="abi:foundation").compile(
        scenario_ref=scenario.scenario_ref,
        case_ref="case:foundation",
        surface_ref="surface:foundation",
        context_ref="context:foundation",
        assertions=scenario.assertions,
        situation_constraints={},
        revision_pin=RevisionPin(authority.generation, 0, 0, 0, 0, "model:foundation"),
    )


def test_metadata_only_definition_is_not_compilable_gold(linked_authority) -> None:
    scenario = ReviewedScenario.from_dict({
        "scenario_ref": "scenario:foundation-independent-definition",
        "review_status": "reviewed",
        "competency_category": "definition",
        "semantic_assertions": [{"kind": "defines", "target": "concept:mother", "semantic_kind": "concept"}],
        "surface_examples": ["Define mother."],
        "metadata": {},
    })
    with pytest.raises(AssertionCompilerError) as error:
        _compile_scenario(linked_authority, scenario)
    assert error.value.code == "definition_requires_semantic_content"
    assert error.value.assertion_ref == scenario.assertions[0].assertion_ref


def test_explicit_ordinary_type_application_remains_compilable(linked_authority) -> None:
    scenario = ReviewedScenario.from_dict({
        "scenario_ref": "scenario:foundation-independent-type-claim",
        "review_status": "reviewed",
        "competency_category": "type",
        "semantic_assertions": [{
            "kind": "application", "operator": "op:type", "predicate": "concept:mother",
            "roles": {"role:subject": "entity:alice", "role:type": "concept:mother"},
        }],
        "surface_examples": ["Alice is a mother."],
        "metadata": {},
    })
    contract = _compile_scenario(linked_authority, scenario)
    assert len(contract.expected_expressions) == 1
    app = contract.expected_expressions[0].applications[0]
    assert app.operator == "op:type"
    assert app.predicate_ref == "concept:mother"
    assert {role.role_ref: role.filler for role in app.roles} == {
        "role:subject": GroundedReference("entity:alice"),
        "role:type": GroundedReference("concept:mother"),
    }


def test_known_definition_traversal_is_retired_not_completed(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-retired-traversal", "What is CEMM?")
        assert result.orientation.mode is SemanticMode.QUERY
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        _assert_no_atom_kind_answer(result)
        # There is no descriptive content in this fresh context. Traversal alone
        # must not claim a supported definition; usable projection stays open.
        assert result.evaluation is None or all(
            query.status is not QueryStatus.SUPPORTED
            for query in result.evaluation.query_results
        )
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "scenario_ref",
    ("scenario:designation_definition-0006", "scenario:designation_definition-0010"),
    ids=("definition-digital-agent", "definition-mother"),
)
def test_historical_definition_gold_requires_real_semantic_content(scenario_ref: str, linked_authority) -> None:
    scenario = next(
        row for row in load_reviewed_scenarios(ROOT / "data" / "scenarios" / "use_cases.jsonl")
        if row.scenario_ref == scenario_ref
    )
    definition = next(row for row in scenario.assertions if row.kind == "defines")
    assert set(definition.fields) == {"target", "semantic_kind"}
    with pytest.raises(AssertionCompilerError) as error:
        _compile_scenario(linked_authority, scenario)
    assert error.value.code == "definition_requires_semantic_content"
    assert error.value.assertion_ref == definition.assertion_ref


# Task 3: independently authored diagnostic contrasts. Direct R3 seams below
# assume canonical predecessor expressions; they are not public VERIFY proofs.
def _matrix_situation(stores, mode=SemanticMode.QUERY, **changes):
    base = _situation(stores.revision_pin())
    values = {
        row.name: getattr(base, row.name) for row in fields(base)
        if row.name not in {"abi_version", "situation_ref"}
    }
    values.update(mode=mode, **changes)
    return SituationContext.create(**values)


def _matrix_meaning(expression, pin):
    return VerifiedMeaning.create(
        program_ref="program:foundation-independent-predecessor", expression=expression,
        grounding_refs=("grounding:foundation-independent-predecessor",),
        coverage_receipt_ref="coverage:foundation-independent-predecessor",
        compilation_proof_ref="compilation:foundation-independent-predecessor",
        verification_receipt_ref="verification:foundation-independent-predecessor",
        revision_pin=pin,
    )


def _matrix_relation(subject="entity:alice", object_ref="entity:bob"):
    return SemanticApplication(
        "application:likes", "op:relation", "rel:likes",
        (RoleBinding("role:subject", GroundedReference(subject)),
         RoleBinding("role:object", GroundedReference(object_ref))),
    )


def _matrix_state(value="value:on", app_ref="application:power"):
    return SemanticApplication(
        app_ref, "op:state", "dim:power",
        (RoleBinding("role:subject", GroundedReference("entity:lamp")),
         RoleBinding("role:dimension", GroundedReference("dim:power")),
         RoleBinding("role:value", GroundedReference(value))),
    )


def _matrix_event():
    return SemanticApplication(
        "application:set-power", "op:event", "event:set_state",
        (RoleBinding("role:actor", GroundedReference("participant:system")),
         RoleBinding("role:target", GroundedReference("entity:lamp")),
         RoleBinding("role:dimension", GroundedReference("dim:power")),
         RoleBinding("role:value", GroundedReference("value:on"))),
    )


def _matrix_expression(app, wrapper="positive"):
    if wrapper == "positive":
        return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
    if wrapper in {"negative", "reported"}:
        scope = ScopeOperator(
            "scope:outer", "scope:polarity" if wrapper == "negative" else "scope:attribution",
            "polarity:negative" if wrapper == "negative" else "scope_value:attribution:reported", app.application_ref,
        )
        return SemanticExpression.create(applications=(app,), scope_operators=(scope,), root_refs=(scope.scope_ref,))
    if wrapper == "conditional":
        premise = _matrix_relation()
        link = ExpressionLink("link:if", "link:condition", (premise.application_ref, app.application_ref))
        return SemanticExpression.create(applications=(premise, app), expression_links=(link,), root_refs=(link.link_ref,))
    if wrapper == "speech":
        speech = SemanticApplication(
            "application:said", "op:event", "event:say",
            (RoleBinding("role:actor", GroundedReference("entity:alice")),
             RoleBinding("role:content", ApplicationFiller(app.application_ref))),
        )
        return SemanticExpression.create(applications=(app, speech), root_refs=(speech.application_ref,))
    raise AssertionError(f"unreviewed matrix wrapper: {wrapper}")


def _matrix_seed_likes(stores, *, conflict=False):
    facts = tuple(
        Fact(
            fact_ref=f"fact:foundation-likes-{stance}", operator="op:relation",
            args={"predicate_ref": "rel:likes", "role:subject": "entity:alice", "role:object": "entity:bob"},
            stance=stance, proof={"source": f"source:foundation-likes-{stance}"},
        )
        for stance in (("support", "deny") if conflict else ("support",))
    )
    stores.world.commit(facts, expected_revision=0)
    return facts


@pytest.mark.parametrize(
    ("subject", "object_ref", "wrapper", "conflict", "expected_status"),
    (("entity:alice", "entity:bob", "positive", False, QueryStatus.SUPPORTED),
     ("entity:bob", "entity:alice", "positive", False, QueryStatus.UNKNOWN),
     ("entity:alice", "entity:bob", "negative", False, QueryStatus.CONTRADICTED),
     ("entity:alice", "entity:bob", "positive", True, QueryStatus.CONFLICT)),
    ids=("forward", "reversed", "negative", "conflict"),
)
def test_foundation_matrix_ordered_relation_proof(subject, object_ref, wrapper, conflict, expected_status, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        facts = _matrix_seed_likes(stores, conflict=conflict)
        expression = _matrix_expression(_matrix_relation(subject, object_ref), wrapper)
        before = stores.revisions(), stores.r3_world_facts()
        situation = _matrix_situation(stores)
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), situation,
        )
        query = result.query_results[0]
        assert query.status is expected_status
        assert query.bindings == ()
        assert (stores.revisions(), stores.r3_world_facts()) == before
        if expected_status is QueryStatus.UNKNOWN:
            assert query.proof is None
        else:
            assert query.proof is not None
            assert set(query.proof.source_refs) == {fact.proof["source"] for fact in facts}
            assert {ref for node in query.proof.nodes for ref in node.source_fact_refs} == {fact.fact_ref for fact in facts}
            assert query.proof.rule_refs == ()
            assert query.proof.revision_pin == situation.revision_pin
    finally:
        stores.close()


def test_foundation_matrix_ordinary_type_surface_matches_independent_membership(tmp_path, linked_authority):
    # Reviewed nominal affordances license instance/class. Both independent
    # compilation and the public path must yield this one forest, without an
    # unreviewed subject/type alias or a parser-authored expectation.
    scenario = ReviewedScenario.from_dict({
        "scenario_ref": "scenario:foundation-type-alignment", "review_status": "reviewed",
        "competency_category": "type", "semantic_assertions": [{
            "kind": "application", "operator": "op:type", "predicate": "concept:mother",
            "roles": {"role:instance": "entity:alice", "role:class": "concept:mother"},
        }], "surface_examples": ["Alice is a mother."], "metadata": {},
    })
    expected = _matrix_expression(SemanticApplication(
        "application:membership", "op:type", "concept:mother",
        (RoleBinding("role:instance", GroundedReference("entity:alice")),
         RoleBinding("role:class", GroundedReference("concept:mother"))),
    ))
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-type-alignment", "Alice is a mother.")
        # Execute the public path first so a compiler-owner rejection cannot
        # prevent the corresponding runtime outcome from being reproduced.
        compiled = _compile_scenario(linked_authority, scenario).expected_expressions[0]
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        assert compiled == expected
        assert result.verification.selected_meaning is not None, "ordinary membership must survive exact verification"
        assert result.verification.selected_meaning.expression == expected
        assert result.evaluation is not None
        assert result.evaluation.decision.action is DecisionAction.RETAIN_ATTRIBUTION
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "case", ("positive", "negative", "reported", "conditional", "speech", "opposing-roots"),
    ids=("positive", "negative", "reported", "conditional", "speech", "opposing-roots"),
)
def test_foundation_matrix_admission_preserves_polarity_and_enclosing_scope(case, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        if case == "opposing-roots":
            positive = _matrix_state()
            negative = _matrix_state(app_ref="application:negative-power")
            scope = ScopeOperator("scope:negative", "scope:polarity", "polarity:negative", negative.application_ref)
            expression = SemanticExpression.create(
                applications=(positive, negative), scope_operators=(scope,),
                root_refs=(positive.application_ref, scope.scope_ref),
            )
        else:
            expression = _matrix_expression(_matrix_state(), case)
        situation = _matrix_situation(
            stores, SemanticMode.OBSERVE, evidence_kinds=("operation",),
            adapter_receipt_refs=("operation_receipt:foundation-observation",), trusted_observation=True,
            epistemic_scope_ref="epistemic_scope:observed",
        )
        before = stores.revisions(), stores.r3_world_facts()
        result = ObserveDecisionOwner().evaluate_full(expression, project_expression(expression), situation)
        assert (stores.revisions(), stores.r3_world_facts()) == before, "EVALUATE proposes, it does not commit"
        if case in {"positive", "negative"}:
            assert len(result.state_deltas) == 1
            delta = result.state_deltas[0]
            assert delta.operator_ref == "op:state" and delta.predicate_ref == "dim:power"
            assert dict(delta.role_values) == {
                "role:subject": "entity:lamp", "role:dimension": "dim:power", "role:value": "value:on",
            }
            assert delta.stance == ("support" if case == "positive" else "deny")
            assert result.contribution.status is DecisionStatus.ADMITTED
            assert delta.occurrence_ref == result.claim_occurrences[0].occurrence_ref
            assert result.claim_occurrences[0].source_ref == "source:foundation"
        else:
            assert result.state_deltas == (), "embedded or conflicting content cannot become unconditional world deltas"
            if case == "opposing-roots":
                assert result.contribution.status is DecisionStatus.CONFLICT
            else:
                assert result.contribution.action is DecisionAction.RETAIN_ATTRIBUTION
    finally:
        stores.close()


class _FoundationLampAdapter:
    """An independent deterministic device observation, never predicted-as-observed."""
    def __init__(self):
        self.requests = []
        self.observation = ObservedDelta.create(
            operator_ref="op:state", predicate_ref="dim:power",
            role_values=(("role:subject", "entity:lamp"), ("role:dimension", "dim:power"), ("role:value", "value:on")),
            stance="support", evidence_refs=("sensor:foundation-lamp-on",),
        )

    def invoke(self, request):
        self.requests.append(request)
        assert request.actor_ref == "participant:system"
        assert request.event_type_ref == "event:set_state"
        assert request.target_ref == "entity:lamp"
        assert request.transition_ref == "transition:set_power_on"
        assert request.adapter_ref == "adapter:state"
        assert len(request.expected_deltas) == 1
        assert dict(request.expected_deltas[0].role_values) == {
            "role:subject": "entity:lamp", "role:dimension": "dim:power", "role:value": "value:on",
        }
        return AdapterResult.create(
            adapter_ref="adapter:state", status=AdapterStatus.SUCCEEDED,
            idempotency_key=request.idempotency_key, request_ref=request.request_ref,
            event_type_ref="event:set_state", target_ref="entity:lamp", transition_ref="transition:set_power_on",
            observed_deltas=(self.observation,), blocker_refs=(),
            operation_receipt_ref="operation_receipt:foundation-lamp-on",
        )

    def reconcile(self, request):
        raise AssertionError("a completed synchronous request must not invoke reconciliation")


def _matrix_operation_situation(stores, *, permitted=True, mode=SemanticMode.REQUEST):
    stores.world.commit((Fact(
        fact_ref="fact:foundation-lamp-off", operator="op:state",
        args={"predicate_ref": "dim:power", "role:subject": "entity:lamp", "role:dimension": "dim:power", "role:value": "value:off"},
        proof={"source": "sensor:foundation-lamp-off"},
    ),), expected_revision=0)
    turn = begin_turn(stores, "session:foundation")
    return _matrix_situation(
        stores, mode, turn_ref=turn["turn_ref"], turn_index=turn["turn_index"],
        actor_ref="participant:system", capability_refs=("cap:set_state",),
        permission_refs=("permission:set_state",) if permitted else (), adapter_refs=("adapter:state",),
        epistemic_scope_ref={
            SemanticMode.REQUEST: "epistemic_scope:requested", SemanticMode.OBSERVE: "epistemic_scope:observed",
            SemanticMode.QUERY: "epistemic_scope:query",
        }[mode],
    )


@pytest.mark.parametrize("permitted", (True, False), ids=("permitted", "denied"))
def test_foundation_matrix_explicit_operation_permission_and_receipt(permitted, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        situation = _matrix_operation_situation(stores, permitted=permitted)
        expression = _matrix_expression(_matrix_event())
        meaning = _matrix_meaning(expression, situation.revision_pin)
        adapter = _FoundationLampAdapter()
        gateway = R3EffectGateway(stores, AdapterRegistry({"adapter:state": adapter}))
        before = stores.world.revision, stores.r3_world_facts()
        evaluation = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release()).evaluate(meaning, situation)
        assert (stores.world.revision, stores.r3_world_facts()) == before
        assert evaluation.decision.status is (DecisionStatus.PENDING if permitted else DecisionStatus.DENIED)
        receipt = gateway.execute(evaluation, meaning, situation)
        if permitted:
            assert type(receipt) is EffectReceipt and receipt.status is EffectStatus.COMMITTED
            assert len(adapter.requests) == 1
            assert receipt.input_revision_pin.world_revision == before[0]
            assert receipt.output_revision_pin.world_revision == before[0] + 1
            assert receipt.observed_delta_refs == (adapter.observation.observed_delta_ref,)
            assert receipt.operation_receipt_ref == "operation_receipt:foundation-lamp-on"
            facts = [row for row in stores.r3_world_facts() if row.fact_ref in receipt.committed_fact_refs]
            assert len(facts) == 1
            assert facts[0].args == {
                "predicate_ref": "dim:power", "role:subject": "entity:lamp", "role:dimension": "dim:power", "role:value": "value:on",
            }
            assert facts[0].proof["source"] == "operation_receipt:foundation-lamp-on"
            assert facts[0].proof["evidence_refs"] == ["sensor:foundation-lamp-on"]
            revisions = stores.revisions()
            assert gateway.execute(evaluation, meaning, situation) == receipt
            assert stores.revisions() == revisions and len(adapter.requests) == 1
        else:
            assert type(receipt) is NoEffectReceipt
            assert evaluation.effect_intents == () and adapter.requests == []
            assert evaluation.decision.blocker_refs == ("permission:set_state",)
            assert (stores.world.revision, stores.r3_world_facts()) == before
            assert receipt.input_revision_pin.world_revision == receipt.output_revision_pin.world_revision
    finally:
        stores.close()


@pytest.mark.parametrize("wrapper", ("negative", "reported", "conditional"), ids=("negative", "reported", "conditional"))
def test_foundation_matrix_scoped_operation_does_not_authorize_effect(wrapper, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        situation = _matrix_operation_situation(stores)
        expression = _matrix_expression(_matrix_event(), wrapper)
        meaning = _matrix_meaning(expression, situation.revision_pin)
        before = stores.revisions(), stores.r3_world_facts()
        evaluation = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release()).evaluate(meaning, situation)
        assert (stores.revisions(), stores.r3_world_facts()) == before
        assert evaluation.effect_intents == (), "an embedded event is not an unconditional directive"
        assert evaluation.decision.action is not DecisionAction.REQUEST_EFFECT
    finally:
        stores.close()


@pytest.mark.parametrize("mode", (SemanticMode.OBSERVE, SemanticMode.QUERY), ids=("event-claim", "capability-query"))
def test_foundation_matrix_non_directive_has_no_device_execution(mode, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        situation = _matrix_operation_situation(stores, mode=mode)
        app = _matrix_event() if mode is SemanticMode.OBSERVE else SemanticApplication(
            "application:capability", "op:relation", "cap:set_state",
            (RoleBinding("role:subject", GroundedReference("participant:system")),),
        )
        meaning = _matrix_meaning(_matrix_expression(app), situation.revision_pin)
        adapter = _FoundationLampAdapter()
        before = stores.world.revision, stores.r3_world_facts()
        evaluation = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release()).evaluate(meaning, situation)
        assert evaluation.effect_intents == ()
        receipt = R3EffectGateway(stores, AdapterRegistry({"adapter:state": adapter})).execute(evaluation, meaning, situation)
        assert type(receipt) is NoEffectReceipt and adapter.requests == []
        assert (stores.world.revision, stores.r3_world_facts()) == before
        if mode is SemanticMode.OBSERVE:
            assert evaluation.decision.action is DecisionAction.RETAIN_ATTRIBUTION
            assert evaluation.claim_occurrences[0].source_ref == "source:foundation"
        else:
            assert evaluation.query_results[0].status is QueryStatus.SUPPORTED
            assert evaluation.query_results[0].proof is not None
    finally:
        stores.close()


@pytest.mark.parametrize("independent_root", (False, True), ids=("unresolved-object", "known-root-plus-unresolved"))
def test_foundation_matrix_unknown_role_is_not_dropped_from_query(independent_root, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        _matrix_seed_likes(stores)
        unresolved = SemanticApplication(
            "application:unresolved-likes", "op:relation", "rel:likes",
            (RoleBinding("role:subject", GroundedReference("entity:alice")),
             RoleBinding("role:object", UnresolvedValue("unresolved:object"))),
        )
        known = _matrix_relation()
        expression = SemanticExpression.create(
            applications=(unresolved, known) if independent_root else (unresolved,),
            root_refs=(unresolved.application_ref, known.application_ref) if independent_root else (unresolved.application_ref,),
            unresolved_fillers=(UnresolvedFiller(
                "unresolved:object", unresolved.application_ref, "role:object", "reference", ("entity",), True,
            ),),
        )
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _matrix_situation(stores),
        )
        assert (stores.revisions(), stores.r3_world_facts()) == before
        assert len(expression.unresolved_fillers) == 1 and expression.unresolved_fillers[0].critical
        assert result.query_results[0].status in {QueryStatus.UNKNOWN, QueryStatus.PARTIAL}, (
            "support for Alice liking Bob does not fill an unidentified critical object"
        )
        assert result.contribution.blocker_refs, "useful partial support retains the unresolved owning role"
    finally:
        stores.close()


@pytest.mark.parametrize("restart", (False, True), ids=("current-session", "after-reopen"))
def test_foundation_matrix_speech_content_focus_keeps_speaker_session_and_recency(restart, tmp_path, linked_authority):
    path = tmp_path / "focus.db"
    stores = open_stores(path, authority_generation=linked_authority.generation)
    try:
        focus = FocusStore(stores)
        old = _matrix_expression(_matrix_relation())
        latest = _matrix_expression(_matrix_state())
        rows = []
        for turn, participant, session, expression in (
            ("turn:old", "participant:system", "session:speech", old),
            ("turn:latest", "participant:system", "session:speech", latest),
            ("turn:user", "participant:user", "session:speech", old),
            ("turn:other", "participant:system", "session:other", old),
        ):
            row = VerifiedSemanticFocus.create(
                expression_refs=(expression.expression_ref,), entity_refs=(), event_refs=(),
                salience_proof_refs=(f"equivalence:{turn}",), participant_ref=participant,
                session_ref=session, turn_ref=turn, revision_pin=stores.revision_pin(),
            )
            focus.add(row)
            rows.append(row)
        if restart:
            stores.close()
            stores = open_stores(path, authority_generation=linked_authority.generation)
            focus = FocusStore(stores)
        before = stores.revisions(), stores.r3_world_facts()
        result = ReferenceResolver(focus, linked_authority).resolve(
            "reference:what-you-said", ReferenceConstraints("second", None, "content", 8, "session:speech"), "turn:now",
        )
        assert (stores.revisions(), stores.r3_world_facts()) == before
        assert result.selected_ref == latest.expression_ref
        assert result.alternative_refs == (old.expression_ref,)
        assert result.proof_refs == (rows[1].focus_ref,)
    finally:
        stores.close()


def _membership_expected(class_ref="concept:mother", *, negative=False):
    app = SemanticApplication(
        "application:independent-membership", "op:type", class_ref,
        (RoleBinding("role:instance", GroundedReference("entity:alice")),
         RoleBinding("role:class", GroundedReference(class_ref))),
    )
    if not negative:
        return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
    scope = ScopeOperator("scope:independent-negative", "scope:polarity", "scope_value:polarity:negative", app.application_ref)
    return SemanticExpression.create(applications=(app,), scope_operators=(scope,), root_refs=(scope.scope_ref,))


@pytest.mark.parametrize(
    ("surface", "class_ref", "negative"),
    (("Alice is mother.", "concept:mother", False),
     ("Alice is a mother.", "concept:mother", False),
     ("Alice is not a mother.", "concept:mother", True),
     ("Alice is a job role.", "concept:job_role", False)),
    ids=("bare", "determined", "negative", "multiword"),
)
def test_foundation_membership_public_preserves_exact_roles_scope_and_attribution(surface, class_ref, negative, tmp_path):
    expected = _membership_expected(class_ref, negative=negative)
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "membership.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:membership-owner", surface)
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == expected
        assert result.evaluation.decision.action is DecisionAction.RETAIN_ATTRIBUTION
        assert result.evaluation.effect_intents == ()
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        assert isinstance(result.effect_receipt, NoEffectReceipt)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language", ("en", "es"), ids=("english", "spanish"))
def test_foundation_membership_form_geometry_has_typed_nonsemantic_gaps(language):
    pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
    surface = "Alice is a mother." if language == "en" else "Alice es una madre."
    lattice = FormResolver(pack, RuntimeConfig.release()).resolve(surface)
    for unit in lattice.units:
        if unit.source_text.isspace():
            assert ("orthography", "whitespace") in unit.features
        elif unit.source_text == ".":
            assert ("orthography", "punctuation") in unit.features
        else:
            assert not any(key == "orthography" for key, _ in unit.features)
    assert not any(row.construction == "orthography" for row in lattice.hypotheses)


@pytest.mark.parametrize(
    ("language", "alias", "surface"),
    (("en", "velnora", "Alice is a velnora."),
     ("en", "care giver", "Alice is a care giver."),
     ("es", "madre", "Alice es una madre."),
     ("es", "luz velnora", "Alice es una luz velnora.")),
    ids=("unseen-alias", "unseen-multiword", "spanish", "spanish-unseen-multiword"),
)
def test_foundation_membership_reviewed_alias_inherits_type_frame_without_pack_changes(language, alias, surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "reviewed-alias.db")
    pack_path = ROOT / "data/languages" / language / "forms.json"
    before_pack = pack_path.read_bytes()
    pack = json.loads(before_pack)
    config = RuntimeConfig.release()
    facts = (
        DesignationFact.create(surface="Alice", target_ref="entity:alice", language=language),
        DesignationFact.create(surface=alias, target_ref="concept:mother", language=language),
    )
    class ReviewedIndex:
        def build_index(self):
            return DesignationIndex(facts)
    try:
        resolver = FormResolver(pack, config)
        affordances = SemanticAffordanceIndex(runtime.authority, config)
        runtime._owners["orientation"] = RuntimeOrientationOwner(
            authority=runtime.authority, stores=runtime.stores, config=config,
            form_resolver=resolver,
            grounder=Grounder(runtime.authority, config, form_pack=pack, form_pack_hash=resolver.form_pack_hash, designation_store=ReviewedIndex()),
            contribution_expander=ContributionExpander(affordances, config),
            context_builder=ProposalContextBuilder(runtime.authority, affordances, config, form_pack=pack),
        )
        atoms = dict(runtime.authority.atoms)
        _, context = runtime.orient("session:reviewed-nominal", surface)
        predicate = next(row for row in context.application_frames if row.operator_ref == "op:type")
        assert context.designation(predicate.designation_slot_ref).designation_fact_ref == facts[1].designation_fact_ref
        result = runtime.process("session:reviewed-nominal", surface)
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == _membership_expected()
        assert result.evaluation.decision.action is DecisionAction.RETAIN_ATTRIBUTION
        assert runtime.stores.world.revision == 0 and runtime.stores.r3_world_facts() == ()
        assert dict(runtime.authority.atoms) == atoms and pack_path.read_bytes() == before_pack
        assert result.proposal.explored_states == 4 and not result.proposal.truncated
    finally:
        runtime.stores.close()


def _membership_composed_scenario(roles):
    roles = {role: ({"kind": "grounded", "target": value["target_ref"]}
                    if value["kind"] == "grounded" else value) for role, value in roles.items()}
    return ReviewedScenario.from_dict({
        "scenario_ref": "scenario:foundation-composed-membership", "review_status": "reviewed",
        "competency_category": "type", "semantic_assertions": [{
            "kind": "composed_expression", "shape": "multi_root",
            "applications": [
                {"local_ref": "membership", "operator": "op:type", "predicate": "concept:mother", "roles": roles},
                {"local_ref": "relation", "operator": "op:relation", "predicate": "rel:likes", "roles": {
                    "role:subject": {"kind": "grounded", "target": "entity:alice"},
                    "role:object": {"kind": "grounded", "target": "entity:bob"},
                }},
            ], "expression_links": [], "root_local_refs": ["membership", "relation"],
        }], "surface_examples": ["Alice is a mother. Alice likes Bob."], "metadata": {},
    })


def test_foundation_membership_composed_gold_uses_world_membership(linked_authority):
    scenario = _membership_composed_scenario({
        "role:instance": {"kind": "grounded", "target_ref": "entity:alice"},
        "role:class": {"kind": "grounded", "target_ref": "concept:mother"},
    })
    membership = _membership_expected().applications[0]
    relation = _matrix_relation()
    expected = SemanticExpression.create(applications=(membership, relation), root_refs=(membership.application_ref, relation.application_ref))
    assert _compile_scenario(linked_authority, scenario).expected_expressions == (expected,)


def test_foundation_membership_composed_multiroot_canonicalization_and_linear_work(linked_authority, monkeypatch):
    # Same-assertion successor: true multi-root canonicalization and bounded
    # compiler work survive retirement of registry-kind-shaped type gold.
    scenario = _membership_composed_scenario({
        "role:instance": {"kind": "grounded", "target_ref": "entity:alice"},
        "role:class": {"kind": "grounded", "target_ref": "concept:mother"},
    })
    first = _compile_scenario(linked_authority, scenario)
    raw = scenario.as_dict()
    assertion = raw["semantic_assertions"][0]
    assertion["applications"].reverse()
    for app in assertion["applications"]:
        app["local_ref"] = {"membership": "renamed_type", "relation": "renamed_relation"}[app["local_ref"]]
        app["roles"] = dict(reversed(tuple(app["roles"].items())))
    assertion["root_local_refs"] = ["renamed_relation", "renamed_type"]
    # Scenario and assertion IDs are reviewed lineage, not expression identity.
    raw.pop("source_digest", None)
    raw.pop("source_hash", None)
    second = _compile_scenario(linked_authority, ReviewedScenario.from_dict(raw))
    assert first.expression_relation.value == "single"
    assert len(first.expected_expressions) == 1 and len(first.expected_expressions[0].root_refs) == 2
    assert first.expected_expressions == second.expected_expressions
    assert not first.expected_expressions[0].expression_links
    work = []
    monkeypatch.setattr(ExpectedCycleContractCompiler, "_record_composed_work", lambda _owner, operation: work.append(operation))
    for count in (2, 8):
        applications = [{"local_ref": f"membership_{index}", "operator": "op:type", "predicate": "concept:mother", "roles": {
            "role:instance": {"kind": "grounded", "target": "entity:alice"},
            "role:class": {"kind": "grounded", "target": "concept:mother"},
        }} for index in range(count)]
        current = ReviewedScenario.from_dict({
            "scenario_ref": "scenario:membership-linear-work", "review_status": "reviewed", "competency_category": "type",
            "semantic_assertions": [{"kind": "composed_expression", "shape": "multi_root", "applications": applications,
                "expression_links": [], "root_local_refs": [row["local_ref"] for row in applications]}],
            "surface_examples": ["Alice is a mother."], "metadata": {},
        })
        work.clear()
        _compile_scenario(linked_authority, current)
        assert work.count("local_ref_duplicate_probe") == count
        assert work.count("local_ref_insert") == count
        assert work.count("root_resolution") == count
        assert work.count("proposition_resolution") == 0 and work.count("link_operand_resolution") == 0
        assert len(work) == 3 * count
    linked = ReviewedScenario.from_dict({
        "scenario_ref": "scenario:membership-link-work", "review_status": "reviewed", "competency_category": "type",
        "semantic_assertions": [{"kind": "composed_expression", "shape": "linked", "mode": "SIMULATE", "applications": [
            {"local_ref": "power", "operator": "op:state", "predicate": "dim:power", "roles": {
                "role:subject": {"kind": "grounded", "target": "entity:lamp"},
                "role:dimension": {"kind": "grounded", "target": "dim:power"},
                "role:value": {"kind": "grounded", "target": "value:on"}}},
            {"local_ref": "greeting", "operator": "op:event", "predicate": "event:greeting", "roles": {
                "role:actor": {"kind": "grounded", "target": "participant:user"},
                "role:addressee": {"kind": "grounded", "target": "participant:system"}}}],
            "expression_links": [{"local_ref": "joined", "link_type": "link:condition", "operand_local_refs": ["power", "greeting"]}],
            "root_local_refs": ["joined"]}], "surface_examples": ["A conditional greeting."], "metadata": {},
    })
    work.clear()
    _compile_scenario(linked_authority, linked)
    assert work == ["local_ref_duplicate_probe", "local_ref_insert", "local_ref_duplicate_probe", "local_ref_insert",
                    "local_ref_duplicate_probe", "local_ref_insert", "root_resolution", "link_operand_resolution", "link_operand_resolution"]


def test_foundation_membership_composed_malformed_graphs_preserve_all_exact_guards(linked_authority):
    from tests.test_r4_assertion_compiler import _assert_composed_expression_rejects_noncanonical_graph

    # Preserve the 26 unaffected malformed assertions verbatim through their
    # frozen helper; replace only the five registry-kind-shaped fixtures below.
    for mutation, error in (
        ("duplicate_local", "duplicate"), ("duplicate_root", "duplicate"),
        ("unknown_root", "unknown|dangling"), ("unknown_shape", "shape"),
        ("bad_link_arity", "arity"), ("unknown_link", "unsupported expression link"),
        ("dangling_operand", "unknown expression link operand"),
        ("multi_root_with_link", "multi_root"), ("linked_without_link", "linked"),
        ("unknown_operator", "operator"), ("unknown_predicate", "authority ref"),
        ("wrong_predicate_kind", "incompatible kind"), ("unknown_role", "role"),
        ("unknown_filler", "filler kind"), ("literal_event_actor", "literal filler"),
        ("designation_non_string", "designation surface"), ("designation_empty", "designation surface"),
        ("dangling_proposition", "unknown proposition"), ("orphan", "non-root"),
        ("cycle", "cycle|parent"), ("extra_application_field", "fields must match"),
        ("missing_link_field", "fields must match"), ("extra_filler_field", "fields must match"),
        ("over_role_bound", "role bound"), ("over_application_bound", "application"), ("over_link_bound", "link"),
    ):
        _assert_composed_expression_rejects_noncanonical_graph(mutation, error)

    def compile_fields(fields):
        return _compile_scenario(linked_authority, ReviewedScenario.from_dict({
            "scenario_ref": "scenario:membership-malformed-guard", "review_status": "reviewed", "competency_category": "type",
            "semantic_assertions": [{"kind": "composed_expression", **fields}],
            "surface_examples": ["Alice is a mother."], "metadata": {},
        }))

    def membership(index):
        return {"local_ref": f"member_{index}", "operator": "op:type", "predicate": "concept:mother", "roles": {
            "role:instance": {"kind": "grounded", "target": "entity:alice"},
            "role:class": {"kind": "grounded", "target": "concept:mother"}}}

    valid = {"shape": "multi_root", "applications": [membership(0), membership(1)],
             "expression_links": [], "root_local_refs": ["member_0", "member_1"]}
    assert len(compile_fields(valid).expected_expressions[0].root_refs) == 2
    for value, value_type, error in ((True, "integer", "integer"), (1, "boolean", "boolean"), ("adapter", "string", "type class")):
        malformed = json.loads(json.dumps(valid))
        malformed["applications"][0]["roles"]["role:class"] = {"kind": "literal", "value_type": value_type, "value": value}
        # The third guard now rejects a nongrounded class, not registry metadata.
        with pytest.raises((AssertionCompilerError, TypeError, ValueError), match=error):
            compile_fields(malformed)
    for count in (6, 8):
        deep = {"shape": "linked", "applications": [membership(index) for index in range(count)],
            "expression_links": [{"local_ref": f"link_{index}", "link_type": "link:condition",
                "operand_local_refs": ["member_0" if index == 0 else f"link_{index - 1}", f"member_{index + 1}"]}
                for index in range(count - 1)], "root_local_refs": [f"link_{count - 2}"]}
        if count == 6:
            assert len(compile_fields(deep).expected_expressions) == 1
        else:
            with pytest.raises((AssertionCompilerError, TypeError, ValueError), match="depth"):
                compile_fields(deep)
    too_many_roots = {"shape": "multi_root", "applications": [membership(index) for index in range(9)],
        "expression_links": [], "root_local_refs": [f"member_{index}" for index in range(9)]}
    with pytest.raises((AssertionCompilerError, TypeError, ValueError), match="root"):
        compile_fields(too_many_roots)


@pytest.mark.parametrize(
    "case", ("registry-kind", "wrong-class", "literal-instance", "wrong-instance-kind"),
    ids=("registry-kind", "wrong-class", "literal-instance", "wrong-instance-kind"),
)
def test_foundation_membership_composed_gold_rejects_nonmembership(case, linked_authority):
    roles = {
        "role:instance": {"kind": "grounded", "target_ref": "entity:alice"},
        "role:class": {"kind": "grounded", "target_ref": "concept:mother"},
    }
    if case == "registry-kind":
        roles = {"role:subject": {"kind": "grounded", "target_ref": "concept:mother"},
                 "role:type": {"kind": "literal", "value_type": "string", "value": "concept"}}
    elif case == "wrong-class":
        roles["role:class"]["target_ref"] = "concept:person"
    elif case == "literal-instance":
        roles["role:instance"] = {"kind": "literal", "value_type": "string", "value": "Alice"}
    else:
        roles["role:instance"]["target_ref"] = "rel:likes"
    with pytest.raises(ValueError):
        _compile_scenario(linked_authority, _membership_composed_scenario(roles))


def _membership_slot_with(slot, **changes):
    values = {row.name: getattr(slot, row.name) for row in fields(slot) if row.init and row.name != "slot_ref"}
    values.update(changes)
    return type(slot).create(**values)


def _membership_unchecked(value, **changes):
    forged = object.__new__(type(value))
    for row in fields(value):
        object.__setattr__(forged, row.name, changes.get(row.name, getattr(value, row.name)))
    if isinstance(forged, ProposalContext):
        forged._build_indexes()
    return forged


@pytest.mark.parametrize("attack", ("scope-transfer", "widened-instance"), ids=("scope-transfer", "widened-instance"))
def test_foundation_membership_multiclause_reconstruction_keeps_instance_and_scope_owner(attack, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "clauses.db")
    try:
        _, context = runtime.orient("session:nominal-clauses", "Alice is not a mother. Bob is a mother.")
        proposal = runtime.proposal_model.propose(context)
        assert proposal.candidates and not proposal.truncated
        alice = _membership_expected(negative=True)
        bob = SemanticApplication("application:bob", "op:type", "concept:mother", (
            RoleBinding("role:instance", GroundedReference("entity:bob")),
            RoleBinding("role:class", GroundedReference("concept:mother")),
        ))
        expected = SemanticExpression.create(applications=(*alice.applications, bob),
            scope_operators=alice.scope_operators, root_refs=(*alice.root_refs, bob.application_ref))
        reconstructed = tuple((candidate.program, reconstruct_expected_expression(candidate.program, context)) for candidate in proposal.candidates)
        correct = next(program for program, expression in reconstructed if expression == expected)
        if attack == "scope-transfer":
            assert all(expression is None or expression == expected for _, expression in reconstructed)
        else:
            instance = next(row for row in context.reference_slots if row.target_ref == "entity:bob")
            forged = _membership_unchecked(context, reference_slots=tuple(
                _membership_unchecked(row, source_unit_refs=("unit:0", "unit:11")) if row == instance else row
                for row in context.reference_slots))
            assert reconstruct_expected_expression(correct, forged) is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", ("Alice mother", "Alice. mother", "mother is Alice"), ids=("juxtaposition", "separate-clause", "reversed"))
def test_foundation_membership_requires_reviewed_predication_not_juxtaposition(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "unlicensed.db")
    try:
        _, context = runtime.orient("session:unlicensed-membership", surface)
        proposal = runtime.proposal_model.propose(context)
        for candidate in proposal.candidates:
            assert reconstruct_expected_expression(candidate.program, context) is None
        result = runtime.process("session:unlicensed-membership", surface)
        assert result.verification.selected_meaning is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "corruption", ("missing-gap", "forged-gap", "missing-binder", "missing-determiner", "foreign-instance"),
    ids=("missing-gap", "forged-gap", "missing-binder", "missing-determiner", "foreign-instance"),
)
def test_foundation_membership_independent_reconstruction_rejects_source_forgery(corruption, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "reconstruction.db")
    try:
        _, context = runtime.orient("session:independent-membership", "Alice is a mother.")
        proposal = runtime.proposal_model.propose(context)
        assert proposal.candidates
        program = proposal.candidates[0].program
        contributions = context.contribution_slots
        references = context.reference_slots
        if corruption in {"missing-gap", "missing-binder", "missing-determiner"}:
            source = {"missing-gap": "unit:3", "missing-binder": "unit:2", "missing-determiner": "unit:4"}[corruption]
            contributions = tuple(row for row in contributions if row.source_unit_refs != (source,))
        elif corruption == "forged-gap":
            gap = next(row for row in contributions if row.source_unit_refs == ("unit:3",))
            invalid_gap = _membership_slot_with(gap, provenance_refs=("unit:7",))
            contributions = tuple(invalid_gap if row.slot_ref == gap.slot_ref else row for row in contributions)
        else:
            instance = next(row for row in references if row.target_ref == "entity:alice")
            references = tuple(_membership_unchecked(row, source_unit_refs=("unit:7",)) if row == instance else row for row in references)
        forged = _membership_unchecked(context, contribution_slots=contributions, reference_slots=references)
        assert reconstruct_expected_expression(program, forged) is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "extension", ("remote-binder", "remote-determiner", "punctuation-gap", "semantic-gap"),
    ids=("remote-binder", "remote-determiner", "punctuation-gap", "semantic-gap"),
)
def test_foundation_membership_context_rejects_unowned_predication_geometry(extension, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "forged.db")
    try:
        _, context = runtime.orient("session:forged-membership", "Alice is a mother. Bob is a person.")
        frame = next(row for row in context.application_frames if row.predicate_target_ref == "concept:mother")
        designation = context.designation(frame.designation_slot_ref)
        # Independently named source positions; no parser-authored semantic gold.
        injected = {"remote-binder": "unit:11", "remote-determiner": "unit:13",
                    "punctuation-gap": "unit:7", "semantic-gap": "unit:9"}[extension]
        refs = tuple(dict.fromkeys((*designation.source_unit_refs, injected)))
        forged_frame = _membership_slot_with(frame, source_unit_refs=refs)
        predicate = next(row for row in context.contribution_slots if row.kind == "predicate" and row.target_ref == "concept:mother")
        forged_predicate = _membership_slot_with(predicate, source_unit_refs=refs)
        values = {row.name: getattr(context, row.name) for row in fields(context)
                  if row.init and row.name not in {"context_ref", "abi_version"}}
        values["application_frames"] = tuple(forged_frame if row.slot_ref == frame.slot_ref else row for row in context.application_frames)
        values["contribution_slots"] = tuple(forged_predicate if row.slot_ref == predicate.slot_ref else row for row in context.contribution_slots)
        values["residual_evidence"] = tuple(row for row in context.residual_evidence if row.source_unit_ref not in refs)
        with pytest.raises(ValueError, match="nominal predication.*source"):
            ProposalContext.create(**values)
    finally:
        runtime.stores.close()


def _membership_pair_expected(case):
    alice = SemanticApplication("application:pair-alice", "op:type", "concept:mother", (
        RoleBinding("role:instance", GroundedReference("entity:alice")),
        RoleBinding("role:class", GroundedReference("concept:mother")),
    ))
    bob = SemanticApplication("application:pair-bob", "op:type", "concept:mother", (
        RoleBinding("role:instance", GroundedReference("entity:bob")),
        RoleBinding("role:class", GroundedReference("concept:mother")),
    ))
    scopes = []
    roots = [alice.application_ref, bob.application_ref]
    if case != "positive-pair":
        scopes.append(ScopeOperator("scope:pair-alice-negative", "scope:polarity", "scope_value:polarity:negative", alice.application_ref))
        roots[0] = scopes[-1].scope_ref
    if case == "negative-pair":
        scopes.append(ScopeOperator("scope:pair-bob-negative", "scope:polarity", "scope_value:polarity:negative", bob.application_ref))
        roots[1] = scopes[-1].scope_ref
    links = []
    if case == "coordinated-mixed":
        links.append(ExpressionLink("link:pair-conjunction", "link:conjunction", tuple(roots)))
        roots = [links[0].link_ref]
    return SemanticExpression.create(applications=(alice, bob), scope_operators=tuple(scopes),
        expression_links=tuple(links), root_refs=tuple(roots))


@pytest.mark.parametrize(
    ("case", "surface"),
    (("positive-pair", "Alice is a mother. Bob is a mother."),
     ("mixed-pair", "Alice is not a mother. Bob is a mother."),
     ("negative-pair", "Alice is not a mother. Bob is not a mother."),
     ("coordinated-mixed", "Alice is not a mother and Bob is a mother.")),
    ids=("positive-pair", "mixed-pair", "negative-pair", "coordinated-mixed"),
)
def test_foundation_membership_bounded_pair_public_preserves_independent_graph(case, surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "bounded-pair.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:bounded-membership-pair", surface)
        assert not result.proposal.truncated
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == _membership_pair_expected(case)
        assert result.evaluation.decision.action is DecisionAction.RETAIN_ATTRIBUTION
        assert result.evaluation.effect_intents == ()
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        assert isinstance(result.effect_receipt, NoEffectReceipt)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    ("case", "surface"),
    (("positive-pair", "Alice is a mother. Bob is a mother."),
     ("mixed-pair", "Alice is not a mother. Bob is a mother."),
     ("negative-pair", "Alice is not a mother. Bob is not a mother."),
     ("coordinated-mixed", "Alice is not a mother and Bob is a mother.")),
    ids=("positive-pair", "mixed-pair", "negative-pair", "coordinated-mixed"),
)
def test_foundation_membership_proposal_prunes_impossible_local_choices(case, surface, tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.recursive_composer._search import RecursiveComposer
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "local-choices.db")
    seen = []
    original = RecursiveComposer._apply
    try:
        _, context = runtime.orient("session:local-membership-choices", surface)
        boundary = surface.index("Bob")

        def observed_apply(owner, state, choice):
            action = choice.action
            applications = dict(state.application_frames)
            if action.action_type in {"bind_reference", "bind_role"}:
                app_ref, role, slot_ref = action.arguments
                frame = context.frame(applications[app_ref])
                if frame.operator_ref == "op:type":
                    predicate_start = context.source_span(context.designation(frame.designation_slot_ref).source_unit_refs)[0]
                    expected_instance = "entity:alice" if predicate_start < boundary else "entity:bob"
                    slot = context.reference(slot_ref) if action.action_type == "bind_reference" else context.contribution(slot_ref)
                    assert role == "role:instance" and slot.target_ref == expected_instance
                    seen.append("instance")
            elif action.action_type == "attach_scope":
                _, slot_ref, operand = action.arguments
                scope = context.scope(slot_ref)
                assert operand in applications, "local polarity cannot wrap the compound root"
                frame = context.frame(applications[operand])
                predicate_start = context.source_span(context.designation(frame.designation_slot_ref).source_unit_refs)[0]
                polarity_start = context.source_span(scope.source_unit_refs)[0]
                assert (predicate_start < boundary) == (polarity_start < boundary)
                seen.append("polarity")
            return original(owner, state, choice)

        monkeypatch.setattr(RecursiveComposer, "_apply", observed_apply)
        proposal = runtime.proposal_model.propose(context)
        assert proposal.candidates and not proposal.truncated
        assert "instance" in seen and (case == "positive-pair" or "polarity" in seen)
        assert all(reconstruct_expected_expression(row.program, context) == _membership_pair_expected(case) for row in proposal.candidates)
        assert len(proposal.candidates) <= 20
    finally:
        runtime.stores.close()


def test_foundation_membership_pruning_preserves_unresolved_frame_union():
    from tests.test_proposal_context_abi1 import _context_with_unresolved_designation
    from cemm_authoritative_hybrid.proposal_context import nominal_predication_choice_index
    from cemm_authoritative_hybrid.recursive_composer._search import RecursiveComposer

    context, unresolved = _context_with_unresolved_designation()
    restored = ProposalContext.from_dict(context.as_dict())
    assert restored.unresolved_designation_frame(unresolved.slot_ref) == unresolved
    bindings, scopes = nominal_predication_choice_index(restored)
    assert dict(bindings) == {} and dict(scopes) == {}
    owner = RecursiveComposer(restored)
    assert owner.explored == 0 and not owner.truncated


def test_foundation_membership_pruning_preserves_nonnominal_polysemy_scope(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "polysemy.db")
    pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
    config = RuntimeConfig.release()
    facts = (
        DesignationFact.create(surface="Alice", target_ref="entity:alice", language="en"),
        DesignationFact.create(surface="velnora", target_ref="concept:mother", language="en"),
        DesignationFact.create(surface="velnora", target_ref="value:on", language="en"),
    )
    class ReviewedIndex:
        def build_index(self):
            return DesignationIndex(facts)
    try:
        resolver = FormResolver(pack, config)
        affordances = SemanticAffordanceIndex(runtime.authority, config)
        runtime._owners["orientation"] = RuntimeOrientationOwner(
            authority=runtime.authority, stores=runtime.stores, config=config,
            form_resolver=resolver,
            grounder=Grounder(runtime.authority, config, form_pack=pack, form_pack_hash=resolver.form_pack_hash, designation_store=ReviewedIndex()),
            contribution_expander=ContributionExpander(affordances, config),
            context_builder=ProposalContextBuilder(runtime.authority, affordances, config, form_pack=pack),
        )
        _, context = runtime.orient("session:polysemy", "Alice is not velnora.")
        assert {frame.operator_ref for frame in context.application_frames} == {"op:type", "op:state"}
        proposal = runtime.proposal_model.propose(context)
        app = SemanticApplication("application:independent-state", "op:state", "dim:power", (
            RoleBinding("role:subject", GroundedReference("entity:alice")),
            RoleBinding("role:dimension", GroundedReference("dim:power")),
            RoleBinding("role:value", GroundedReference("value:on")),
        ))
        scope = ScopeOperator("scope:independent-state-negative", "scope:polarity", "scope_value:polarity:negative", app.application_ref)
        state_expected = SemanticExpression.create(applications=(app,), scope_operators=(scope,), root_refs=(scope.scope_ref,))
        expressions = {reconstruct_expected_expression(row.program, context) for row in proposal.candidates}
        assert not proposal.truncated
        assert state_expected in expressions, "an unselected nominal alternative cannot suppress state polarity"
        assert runtime.stores.world.revision == 0 and runtime.stores.r3_world_facts() == ()
    finally:
        runtime.stores.close()


def _matrix_designation_query(surface):
    app = SemanticApplication(
        "application:lexical-lookup", "op:designation", "label:lexical",
        (RoleBinding("role:label_type", GroundedReference("label:lexical")),
         RoleBinding("role:surface", LiteralValue("string", surface)),
         RoleBinding("role:target", BoundVariable("?meaning"))),
    )
    binder = VariableBinder("binder:meaning", "?meaning", app.application_ref)
    return SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))


def test_foundation_matrix_fresh_fragment_requires_clarification(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-fragment", "that you learn")
        assert result.orientation.obligation_refs == () and result.orientation.focus_refs == ()
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        assert result.evaluation is not None, "a fresh incomplete content fragment requires an exact clarification obligation"
        assert result.evaluation.decision.action is DecisionAction.REQUEST_CLARIFICATION
        assert result.evaluation.effect_intents == ()
    finally:
        runtime.stores.close()


def test_foundation_matrix_alias_directive_binds_actual_prior_query(linked_authority):
    # Continuity only, NOT authorization: the materializer currently defaults
    # to unlinked cap:learn, permission:learn_designation and
    # contract:designation_answer:v2. No reviewed answer-contract ref is linked;
    # the obligation below preserves that existing ABI default, not new authority.
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        turn = begin_turn(stores, "session:foundation")
        query_expression = _matrix_designation_query("velnora")
        situation = _matrix_situation(stores, turn_ref=turn["turn_ref"], turn_index=turn["turn_index"])
        query_meaning = _matrix_meaning(query_expression, situation.revision_pin)
        evaluator = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release())
        query_evaluation = evaluator.evaluate(query_meaning, situation)
        query = query_evaluation.query_results[0]
        assert query.status is QueryStatus.UNKNOWN and query.bindings == () and query.proof is None
        pending = DialogueObligation.create(
            kind=ObligationKind.LEARNING_ANSWER, session_ref="session:foundation",
            source_query_ref=query.query_result_ref, expected_answer_contract_ref="contract:designation_answer:v2",
            created_turn_index=turn["turn_index"], expires_turn_index=turn["turn_index"] + 4,
            source_decision_ref=query_evaluation.decision.decision_ref,
            completion_receipt_ref=None, revision_pin=stores.revision_pin(),
        )
        DialogueObligationManager(stores).add(pending)
        snapshot = obligation_snapshot(stores, "session:foundation", maximum=8)
        assert pending.obligation_ref in snapshot["obligation_refs"]
        turn = begin_turn(stores, "session:foundation")
        assert "cap:learn_alias" in linked_authority.capabilities["participant:system"]
        assert ("participant:system", "permission:write_alias", "event:learn_alias") in linked_authority.permissions
        request = _matrix_situation(
            stores, SemanticMode.REQUEST, turn_ref=turn["turn_ref"], turn_index=turn["turn_index"],
            obligation_refs=(pending.obligation_ref,), obligation_snapshot_ref=snapshot["snapshot_ref"],
            capability_refs=("cap:learn_alias",), permission_refs=("permission:write_alias",),
            epistemic_scope_ref="epistemic_scope:requested",
        )
        alias = _matrix_expression(SemanticApplication(
            "application:alias", "op:designation", "label:lexical",
            (RoleBinding("role:label_type", GroundedReference("label:lexical")),
             RoleBinding("role:surface", LiteralValue("string", "velnora")),
             RoleBinding("role:target", GroundedReference("rel:likes"))),
        ))
        meaning = _matrix_meaning(alias, request.revision_pin)
        before = stores.world.revision, stores.r3_world_facts()
        evaluation = evaluator.evaluate(meaning, request)
        assert len(evaluation.learning_drafts) == 1
        plan, obligation = LearningCoordinator(linked_authority, stores).materialize(evaluation, meaning, request)
        assert (stores.world.revision, stores.r3_world_facts()) == before
        after_snapshot = obligation_snapshot(stores, "session:foundation", maximum=8)
        assert pending.obligation_ref in after_snapshot["obligation_refs"]
        persisted_pending = stores.obligations.get(pending.obligation_ref)
        assert persisted_pending is not None
        assert persisted_pending["completion_receipt_ref"] is None
        assert evaluation.learning_drafts[0].source_query_ref == query.query_result_ref
        assert plan.source_query_ref == query.query_result_ref and obligation.source_query_ref == query.query_result_ref
        assert plan.surface_literal == "velnora" and plan.target_ref == "rel:likes"
        assert plan.expected_target_kinds == ("relation_type",)
    finally:
        stores.close()


def test_foundation_matrix_reviewed_alias_survives_restart_and_unseen_reversal(tmp_path):
    # This is reviewed durable designation/index evidence, not a fabricated
    # learning commit. The active ABI 2 has no authorized alias-commit owner.
    path = tmp_path / "alias.db"
    pack_path = ROOT / "data/languages/en/forms.json"
    pack_before = pack_path.read_bytes()
    runtime = load_runtime(ROOT, profile="development", store_path=path)
    atoms_before = dict(runtime.authority.atoms)
    try:
        runtime.stores.world.commit((Fact(
            fact_ref="fact:reviewed-velnora", operator="op:designation",
            args={"predicate_ref": "label:lexical", "role:label_type": "label:lexical", "role:surface": "velnora", "role:target": "rel:likes"},
            proof={"source": "review:foundation-existing-target-alias"},
        ),), expected_revision=0)
    finally:
        runtime.stores.close()


    runtime = load_runtime(ROOT, profile="development", store_path=path)
    try:
        assert dict(runtime.authority.atoms) == atoms_before
        assert pack_path.read_bytes() == pack_before
        assert any(fact.fact_ref == "fact:reviewed-velnora" for fact in runtime.stores.r3_world_facts())
        _, context = runtime.orient("session:foundation-alias", "Bob velnora Alice.")
        assert any(frame.predicate_target_ref == "rel:likes" for frame in context.application_frames), (
            "a durable reviewed alias must inherit its target frame without regenerating the pack"
        )
        result = runtime.process("session:foundation-alias", "Bob velnora Alice.")
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == _matrix_expression(_matrix_relation("entity:bob", "entity:alice"))
        assert dict(runtime.authority.atoms) == atoms_before and pack_path.read_bytes() == pack_before
        assert runtime.stores.world.revision == 1, "unseen reuse is attributed, not new authority"
    finally:
        runtime.stores.close()


def _safety_observation(stores, *, trusted=True):
    return _matrix_situation(
        stores, SemanticMode.OBSERVE, trusted_observation=trusted,
        evidence_kinds=("operation",) if trusted else ("text",),
        adapter_receipt_refs=("operation_receipt:safety",) if trusted else (),
        epistemic_scope_ref="epistemic_scope:observed",
    )


@pytest.mark.parametrize(
    "case",
    ("negative-compound", "reported-nested", "modal", "relation", "unresolved-state", "bound-state", "literal-state", "proposition-state"),
    ids=("negative-compound", "reported-nested", "modal", "relation", "unresolved-state", "bound-state", "literal-state", "proposition-state"),
)
def test_foundation_safety_unsupported_admission_retains_exact_occurrence(case, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        first = _matrix_state()
        second = _matrix_state("value:off", "application:off")
        if case in {"negative-compound", "reported-nested"}:
            if case == "reported-nested":
                scope = ScopeOperator("scope:reported", "scope:attribution", "scope_value:attribution:reported", second.application_ref)
                link = ExpressionLink("link:and", "link:conjunction", (first.application_ref, scope.scope_ref))
                root = link.link_ref
            else:
                link = ExpressionLink("link:and", "link:conjunction", (first.application_ref, second.application_ref))
                scope = ScopeOperator("scope:not", "scope:polarity", "polarity:negative", link.link_ref)
                root = scope.scope_ref
            expression = SemanticExpression.create(applications=(first, second), scope_operators=(scope,), expression_links=(link,), root_refs=(root,))
        elif case == "modal":
            scope = ScopeOperator("scope:modal", "scope:modality", "modality:possible", first.application_ref)
            expression = SemanticExpression.create(applications=(first,), scope_operators=(scope,), root_refs=(scope.scope_ref,))
        elif case == "relation":
            expression = _matrix_expression(_matrix_relation())
        else:
            filler = {"unresolved-state": UnresolvedValue("unresolved:value"), "bound-state": BoundVariable("?value"), "literal-state": LiteralValue("string", "value:on"), "proposition-state": ApplicationFiller(second.application_ref)}[case]
            app = SemanticApplication(first.application_ref, first.operator, first.predicate_ref, (*first.roles[:2], RoleBinding("role:value", filler)))
            if case == "unresolved-state":
                expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,), unresolved_fillers=(UnresolvedFiller("unresolved:value", app.application_ref, "role:value", "reference", ("value",), True),))
            elif case == "bound-state":
                binder = VariableBinder("binder:value", "?value", app.application_ref)
                expression = SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))
            else:
                expression = SemanticExpression.create(applications=(app, second) if case == "proposition-state" else (app,), root_refs=(app.application_ref,))
        before = stores.revisions(), stores.r3_world_facts()
        situation = _safety_observation(stores)
        result = ObserveDecisionOwner().evaluate_full(expression, project_expression(expression), situation)
        assert result.state_deltas == ()
        assert result.contribution.action is DecisionAction.RETAIN_ATTRIBUTION
        assert result.contribution.status is not DecisionStatus.CONFLICT
        assert result.contribution.blocker_refs
        assert len(result.claim_occurrences) == 1
        occurrence = result.claim_occurrences[0]
        assert occurrence.expression_ref == expression.expression_ref and occurrence.root_ref == expression.root_refs[0]
        assert occurrence.source_ref == "source:foundation" and occurrence.evidence_refs == situation.source_refs
        assert all(row.proposed_fact_refs == () for row in result.admission_decisions)
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


@pytest.mark.parametrize(
    "case", ("actual-conflict", "two-denials", "different-contexts"),
    ids=("actual-conflict", "two-denials", "different-contexts"),
)
def test_foundation_safety_conflicts_require_applicable_signed_same_context_claims(case, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        first, second = _matrix_state(), _matrix_state("value:off", "application:off")
        scopes = ()
        if case == "two-denials":
            scopes = tuple(ScopeOperator(f"scope:not-{index}", "scope:polarity", "polarity:negative", app.application_ref) for index, app in enumerate((first, second)))
            operands = tuple(scope.scope_ref for scope in scopes)
        elif case == "different-contexts":
            # A literal and a reference with identical spelling are not the same context.
            first = SemanticApplication(first.application_ref, first.operator, first.predicate_ref, first.roles, (RoleBinding("role:time", GroundedReference("time:earlier")),))
            second = SemanticApplication(second.application_ref, second.operator, second.predicate_ref, second.roles, (RoleBinding("role:time", LiteralValue("string", "time:earlier")),))
            operands = (first.application_ref, second.application_ref)
        else:
            operands = (first.application_ref, second.application_ref)
        link = ExpressionLink("link:and", "link:conjunction", operands)
        expression = SemanticExpression.create(applications=(first, second), scope_operators=scopes, expression_links=(link,), root_refs=(link.link_ref,))
        result = ObserveDecisionOwner().evaluate_full(expression, project_expression(expression), _safety_observation(stores, trusted=False))
        assert result.state_deltas == ()
        assert (result.contribution.status is DecisionStatus.CONFLICT) is (case == "actual-conflict")
        if case != "actual-conflict":
            assert result.contribution.action is DecisionAction.RETAIN_ATTRIBUTION
            assert result.claim_occurrences[0].expression_ref == expression.expression_ref
    finally:
        stores.close()


@pytest.mark.parametrize(
    "wrapper", ("positive", "negative", "reported", "conditional", "speech"),
    ids=("positive", "negative", "reported", "conditional", "speech"),
)
def test_foundation_safety_learning_requires_eligible_directive_root(wrapper, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        app = SemanticApplication("application:alias", "op:designation", "label:lexical", (RoleBinding("role:label_type", GroundedReference("label:lexical")), RoleBinding("role:surface", LiteralValue("string", "velnora")), RoleBinding("role:target", GroundedReference("rel:likes"))))
        expression = _matrix_expression(app, wrapper)
        situation = _matrix_situation(stores, SemanticMode.REQUEST, epistemic_scope_ref="epistemic_scope:requested")
        meaning = _matrix_meaning(expression, situation.revision_pin)
        before = stores.revisions(), stores.r3_world_facts()
        result = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release()).evaluate(meaning, situation)
        assert result.effect_intents == ()
        if wrapper == "positive":
            assert len(result.learning_drafts) == 1
            assert result.learning_drafts[0].surface_literal == "velnora"
            assert result.learning_drafts[0].target_ref == "rel:likes"
        else:
            assert result.learning_drafts == ()
            assert result.decision.action is not DecisionAction.CREATE_LEARNING_OBLIGATION
            assert result.decision.blocker_refs
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


@pytest.mark.parametrize(
    ("mode", "wrapper"),
    (
        (SemanticMode.REQUEST, "positive"), (SemanticMode.SIMULATE, "positive"),
        (SemanticMode.REQUEST, "negative"), (SemanticMode.SIMULATE, "negative"),
        (SemanticMode.REQUEST, "reported"), (SemanticMode.SIMULATE, "reported"),
        (SemanticMode.REQUEST, "conditional"), (SemanticMode.SIMULATE, "conditional"),
        (SemanticMode.REQUEST, "speech"), (SemanticMode.SIMULATE, "speech"),
        (SemanticMode.REQUEST, "multiple-roots"), (SemanticMode.SIMULATE, "multiple-roots"),
    ),
    ids=(
        "positive-request", "positive-simulate", "negative-request", "negative-simulate",
        "reported-request", "reported-simulate", "conditional-request", "conditional-simulate",
        "speech-request", "speech-simulate", "multiple-roots-request", "multiple-roots-simulate",
    ),
)
def test_foundation_safety_transition_selects_only_eligible_root(mode, wrapper, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        seeded = _matrix_operation_situation(stores)
        situation = _matrix_situation(stores, mode, actor_ref=seeded.actor_ref, capability_refs=seeded.capability_refs, permission_refs=seeded.permission_refs, adapter_refs=seeded.adapter_refs, epistemic_scope_ref="epistemic_scope:requested" if mode is SemanticMode.REQUEST else "epistemic_scope:simulated")
        app = _matrix_event()
        if wrapper == "multiple-roots":
            other = SemanticApplication("application:other", app.operator, app.predicate_ref, app.roles)
            expression = SemanticExpression.create(applications=(app, other), root_refs=(app.application_ref, other.application_ref))
        else:
            expression = _matrix_expression(app, wrapper)
        meaning = _matrix_meaning(expression, situation.revision_pin)
        result = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release()).evaluate(meaning, situation)
        if wrapper == "positive":
            assert result.decision.action is (DecisionAction.REQUEST_EFFECT if mode is SemanticMode.REQUEST else DecisionAction.PREVIEW_TRANSITION)
        else:
            assert result.effect_intents == () and result.learning_drafts == ()
            assert result.transition_evaluations == ()
            assert result.decision.blocker_refs
        assert stores.world.revision == 1
    finally:
        stores.close()


@pytest.mark.parametrize(
    ("position", "kind"),
    (("role", "unresolved"), ("qualifier", "unresolved"), ("role", "proposition"), ("qualifier", "proposition")),
    ids=("unresolved-role", "unresolved-qualifier", "proposition-role", "proposition-qualifier"),
)
def test_foundation_safety_query_constraints_are_not_flat_fact_patterns(position, kind, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        child = _matrix_state()
        filler = UnresolvedValue("unresolved:constraint") if kind == "unresolved" else ApplicationFiller(child.application_ref)
        constraint = RoleBinding("role:object" if position == "role" else "role:content", filler)
        roles = (RoleBinding("role:subject", GroundedReference("entity:alice")),)
        app = SemanticApplication("application:constraint", "op:relation", "rel:likes", (*roles, constraint) if position == "role" else roles, (constraint,) if position == "qualifier" else ())
        known = _matrix_relation()
        expression = SemanticExpression.create(
            applications=(app, known, child) if kind == "proposition" else (app, known),
            root_refs=(app.application_ref, known.application_ref),
            unresolved_fillers=(UnresolvedFiller("unresolved:constraint", app.application_ref, constraint.role_ref, "reference", ("entity",), True),) if kind == "unresolved" else (),
        )
        canonical_app = next(row for row in expression.applications if any(isinstance(binding.filler, (UnresolvedValue, ApplicationFiller)) for binding in (*row.roles, *row.qualifiers)))
        canonical_constraint = next(binding for binding in (*canonical_app.roles, *canonical_app.qualifiers) if isinstance(binding.filler, (UnresolvedValue, ApplicationFiller)))
        # Deliberately hostile flat evidence matching a candidate-local ID must
        # never count as evidence for the proposition denoted by that ID.
        value = canonical_constraint.filler.node_ref if kind == "proposition" else "entity:bob"
        stores.world.commit((
            Fact("fact:safety-constraint", "op:relation", {"predicate_ref": "rel:likes", "role:subject": "entity:alice", canonical_constraint.role_ref: value}, proof={"source": "source:safety-constraint"}),
            Fact("fact:safety-known", "op:relation", {"predicate_ref": "rel:likes", "role:subject": "entity:alice", "role:object": "entity:bob"}, proof={"source": "source:safety-known"}),
        ), expected_revision=0)
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
        assert result.query_results[0].status is QueryStatus.PARTIAL
        assert result.query_results[0].proof is None and result.query_results[0].bindings == ()
        assert canonical_constraint.role_ref in result.contribution.blocker_refs
        assert result.contribution.action is DecisionAction.REQUEST_CLARIFICATION
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


@pytest.mark.parametrize(
    "link_type", ("link:conjunction", "link:condition"),
    ids=("link-conjunction", "link-condition"),
)
def test_foundation_safety_compound_conflict_keeps_both_actual_sources(link_type, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        facts = _matrix_seed_likes(stores, conflict=True)
        first, second = _matrix_relation(), _matrix_state()
        link = ExpressionLink("link:conflict", link_type, (first.application_ref, second.application_ref))
        expression = SemanticExpression.create(applications=(first, second), expression_links=(link,), root_refs=(link.link_ref,))
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
        query = result.query_results[0]
        assert query.status is QueryStatus.CONFLICT and query.proof is not None
        assert set(query.proof.source_refs) == {fact.proof["source"] for fact in facts}
        assert {ref for node in query.proof.nodes for ref in node.source_fact_refs} == {fact.fact_ref for fact in facts}
        assert result.contribution.action is DecisionAction.REQUEST_CLARIFICATION
    finally:
        stores.close()


def test_foundation_safety_no_effect_terminal_retry_is_identity_preserving(linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        situation = _matrix_operation_situation(stores, permitted=False)
        meaning = _matrix_meaning(_matrix_expression(_matrix_event()), situation.revision_pin)
        result = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release()).evaluate(meaning, situation)
        adapter = _FoundationLampAdapter()
        gateway = R3EffectGateway(stores, AdapterRegistry({"adapter:state": adapter}))
        receipt = gateway.execute(result, meaning, situation)
        assert type(receipt) is NoEffectReceipt
        before = stores.revisions(), stores.r3_world_facts()
        assert gateway.execute(result, meaning, situation) == receipt
        assert (stores.revisions(), stores.r3_world_facts()) == before
        assert adapter.requests == []
    finally:
        stores.close()


def test_foundation_safety_disjoint_joint_query_bindings_are_not_opposing_proof(linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        apps = tuple(SemanticApplication(f"application:{index}", "op:relation", predicate, (RoleBinding("role:subject", BoundVariable("?person")), RoleBinding("role:object", GroundedReference("entity:bob")))) for index, predicate in enumerate(("rel:likes", "rel:knows")))
        link = ExpressionLink("link:joint", "link:conjunction", tuple(app.application_ref for app in apps))
        binder = VariableBinder("binder:person", "?person", link.link_ref)
        expression = SemanticExpression.create(applications=apps, expression_links=(link,), binders=(binder,), root_refs=(binder.binder_ref,))
        stores.world.commit(tuple(Fact(f"fact:joint-{index}", "op:relation", {"predicate_ref": predicate, "role:subject": subject, "role:object": "entity:bob"}, proof={"source": f"source:joint-{index}"}) for index, (predicate, subject) in enumerate((("rel:likes", "entity:alice"), ("rel:knows", "entity:carol")))), expected_revision=0)
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
        assert result.query_results[0].status is QueryStatus.UNKNOWN
        assert result.query_results[0].proof is None and result.query_results[0].bindings == ()
        assert result.contribution.blocker_refs
    finally:
        stores.close()


@pytest.mark.parametrize("same_binding", (True, False), ids=("same-binding", "different-bindings"))
def test_foundation_safety_opposing_query_evidence_keeps_substitutions_distinct(same_binding, linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        app = SemanticApplication("application:likes", "op:relation", "rel:likes", (RoleBinding("role:subject", BoundVariable("?person")), RoleBinding("role:object", GroundedReference("entity:bob"))))
        binder = VariableBinder("binder:person", "?person", app.application_ref)
        expression = SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))
        facts = tuple(Fact(f"fact:substitution-{stance}", "op:relation", {"predicate_ref": "rel:likes", "role:subject": "entity:alice" if stance == "support" or same_binding else "entity:carol", "role:object": "entity:bob"}, stance=stance, proof={"source": f"source:substitution-{stance}"}) for stance in ("support", "deny"))
        stores.world.commit(facts, expected_revision=0)
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
        query = result.query_results[0]
        if same_binding:
            assert query.status is QueryStatus.CONFLICT and query.proof is not None
            assert query.bindings == ((expression.binders[0].variable_ref, "entity:alice"),)
            assert set(query.proof.source_refs) == {fact.proof["source"] for fact in facts}
        else:
            assert query.status is QueryStatus.PARTIAL
            assert "query:multi_binding_projection_unsupported" in result.contribution.blocker_refs
            assert query.bindings == () and query.proof is None
        assert stores.world.revision == 1 and result.contribution.action is DecisionAction.REQUEST_CLARIFICATION
    finally:
        stores.close()
