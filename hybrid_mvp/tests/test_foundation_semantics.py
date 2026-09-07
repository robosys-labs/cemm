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
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
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
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
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
