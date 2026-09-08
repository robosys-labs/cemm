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
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_r3_writer_preserves_atomic_metadata[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-r3-writer-preserves-atomic-metadata-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "0a7ba39a2c789874dc4ddcf27119160a05214ef804b886e81a6af7a75a6b15f8"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_r3_writer_preserves_atomic_metadata[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-r3-writer-preserves-atomic-metadata-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "0a7ba39a2c789874dc4ddcf27119160a05214ef804b886e81a6af7a75a6b15f8"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_failed_completion_is_atomic[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-failed-completion-is-atomic-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "8520ec577d5b16ba95c657e21ece4eb25afd73906d6a364a63d0acbd275ad6c2"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_failed_completion_is_atomic[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-failed-completion-is-atomic-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "8520ec577d5b16ba95c657e21ece4eb25afd73906d6a364a63d0acbd275ad6c2"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_codec_is_exact": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-codec-is-exact",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "0b5257f9a732a2adbd25e493a5b453956215bbe1f4b8c235300a45accc463abc"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_reads_exact_keys_and_rejects_invalid_lifecycle[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-reads-exact-keys-and-rejects-invalid-lifecycle-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "e472db9e0386b249b61d1a206d2f6d4792131286d2a5bdc48049a8be5c49fc7d"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_reads_exact_keys_and_rejects_invalid_lifecycle[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-reads-exact-keys-and-rejects-invalid-lifecycle-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "e472db9e0386b249b61d1a206d2f6d4792131286d2a5bdc48049a8be5c49fc7d"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_reads_exact_keys_and_rejects_invalid_lifecycle[sqlite-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-reads-exact-keys-and-rejects-invalid-lifecycle-sqlite-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "e472db9e0386b249b61d1a206d2f6d4792131286d2a5bdc48049a8be5c49fc7d"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_authenticates_payload_and_detaches_writes[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-authenticates-payload-and-detaches-writes-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "1822a2237c04902ff5622b0d24bc6b3d71bdb9d76a846a297d0032a796d224f3"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_authenticates_payload_and_detaches_writes[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-authenticates-payload-and-detaches-writes-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "1822a2237c04902ff5622b0d24bc6b3d71bdb9d76a846a297d0032a796d224f3"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_rejects_forged_envelopes_and_future_pins[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-rejects-forged-envelopes-and-future-pins-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c06e7d3dc8fcfcfedebfb1de2600ae8ad815c02ea077f151dd37aee2de19b9e2"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_rejects_forged_envelopes_and_future_pins[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-rejects-forged-envelopes-and-future-pins-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c06e7d3dc8fcfcfedebfb1de2600ae8ad815c02ea077f151dd37aee2de19b9e2"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_work_is_key_bounded[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-work-is-key-bounded-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "62e4ee5cd35c7bd9d8121f073076fe45071b20b391118f4b49fcd3a4d93d9d94"
    },
    "tests/test_foundation_semantics.py::test_foundation_pending_dialogue_work_is_key_bounded[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pending-dialogue-work-is-key-bounded-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "situation-context",
        "source_ast_sha256": "62e4ee5cd35c7bd9d8121f073076fe45071b20b391118f4b49fcd3a4d93d9d94"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_typed_query_pattern_preserves_repeated_role_constraint": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-typed-query-pattern-preserves-repeated-role-constraint",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "584c1bb7aa2d27040e1da0f343f2ff7bee27a7872e1a3b460cb176958c937173"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_exact_target_lookup[known]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-exact-target-lookup-known",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "eb7b7237c721aa3c2a46922e491df7bd04ddddf44b1a91ba9bac78a0b7331e2d"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_exact_target_lookup[unknown]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-exact-target-lookup-unknown",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "eb7b7237c721aa3c2a46922e491df7bd04ddddf44b1a91ba9bac78a0b7331e2d"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_exact_target_lookup[multiword]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-exact-target-lookup-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "eb7b7237c721aa3c2a46922e491df7bd04ddddf44b1a91ba9bac78a0b7331e2d"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_exact_target_lookup[exact-case]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-exact-target-lookup-exact-case",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "eb7b7237c721aa3c2a46922e491df7bd04ddddf44b1a91ba9bac78a0b7331e2d"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_exact_index_retrieves_admitted_target": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-exact-index-retrieves-admitted-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "0d6728211a4e8b5a703c0e8441698684801428be221453f8a7d0a6244a721c33"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[other-language]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-other-language",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[nonconcept]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-nonconcept",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[same-target-languages]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-same-target-languages",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[competing-targets]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-competing-targets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[overflow]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-overflow",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[literal-question-prefix]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-literal-question-prefix",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[teaching-only]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-teaching-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[inverse]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-inverse",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[mixed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-mixed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[reported]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-reported",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_authority_ambiguity_and_typed_constraints[conditional]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-authority-ambiguity-and-typed-constraints-conditional",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "32d21e259f1455248022818b4ea12c367dcc06fea9f1e107385d194bc55be2e6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[generic-what]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-generic-what",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[generic-who]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-generic-who",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[generic-where]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-generic-where",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[reason]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-reason",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[past]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-past",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[language-trailing]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-language-trailing",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[language-internal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-language-internal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[punctuated-clause]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-punctuated-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[extra-clause]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-extra-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[teaching]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-teaching",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_does_not_launder_unsupported_evidence[unknown-event-argument]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-does-not-launder-unsupported-evidence-unknown-event-argument",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "62e4668a099dba4e847ee05ea23e521e1f74843a460d3c73fd237a836e76a648"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_independent_reconstruction_checks_exact_owners[borrowed-literal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-independent-reconstruction-checks-exact-owners-borrowed-literal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "326cb5518d576d5e90da9f6365f96534b21096b41049b86b16a4863d6fadf82b"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_independent_reconstruction_checks_exact_owners[binder-only]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-independent-reconstruction-checks-exact-owners-binder-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "326cb5518d576d5e90da9f6365f96534b21096b41049b86b16a4863d6fadf82b"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_independent_reconstruction_checks_exact_owners[foreign-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-independent-reconstruction-checks-exact-owners-foreign-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "326cb5518d576d5e90da9f6365f96534b21096b41049b86b16a4863d6fadf82b"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_independent_reconstruction_checks_exact_owners[foreign-binder]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-independent-reconstruction-checks-exact-owners-foreign-binder",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "326cb5518d576d5e90da9f6365f96534b21096b41049b86b16a4863d6fadf82b"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_independent_reconstruction_checks_exact_owners[label]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-independent-reconstruction-checks-exact-owners-label",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "326cb5518d576d5e90da9f6365f96534b21096b41049b86b16a4863d6fadf82b"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_language_unspecified_and_response[nonconcept]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-language-unspecified-and-response-nonconcept",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "fe07acaa1c72dad61339af31af8a42f50fa3c4babb44fa732026b85a2c8902d0"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_language_unspecified_and_response[other-language]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-language-unspecified-and-response-other-language",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "fe07acaa1c72dad61339af31af8a42f50fa3c4babb44fa732026b85a2c8902d0"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_language_unspecified_and_response[ambiguous]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-language-unspecified-and-response-ambiguous",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "fe07acaa1c72dad61339af31af8a42f50fa3c4babb44fa732026b85a2c8902d0"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_public_language_unspecified_and_response[synthetic-feature-transport]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-public-language-unspecified-and-response-synthetic-feature-transport",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "fe07acaa1c72dad61339af31af8a42f50fa3c4babb44fa732026b85a2c8902d0"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_index_work_is_bounded_and_never_scans_world[small]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-index-work-is-bounded-and-never-scans-world-small",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3282d4f86fa8a05c3c54b6e0030d1d27b5d1f309ff98b7f7be3e2001a69407c8"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_index_work_is_bounded_and_never_scans_world[grown]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-index-work-is-bounded-and-never-scans-world-grown",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3282d4f86fa8a05c3c54b6e0030d1d27b5d1f309ff98b7f7be3e2001a69407c8"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_unknown_identity_binds_source_content": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-unknown-identity-binds-source-content",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "6920feb41e07888de3b9f5af739911cd851862b3472e9e743ca00d90f0a2d974"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_mentioned_multiword_does_not_expand_constituent_predicates": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-mentioned-multiword-does-not-expand-constituent-predicates",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e854e58d708e1746cfd13afce706798ed4d8af50c421ec1a01a76268726d2f10"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_projection_consumes_exact_owned_binder": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-projection-consumes-exact-owned-binder",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "769fa3e7cb785cb61ed381d18c8e7dcc8c0ae8973b39017baaf0d98ca619e531"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_original_feature_and_assignment_authority_is_independent[literal-provenance]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-original-feature-and-assignment-authority-is-independent-literal-provenance",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "07bacaa1693995e50f393aee59a84eb345a4360f41c74705d1900a0b5e6753d6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_original_feature_and_assignment_authority_is_independent[binder-provenance]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-original-feature-and-assignment-authority-is-independent-binder-provenance",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "07bacaa1693995e50f393aee59a84eb345a4360f41c74705d1900a0b5e6753d6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_original_feature_and_assignment_authority_is_independent[interrogative-feature]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-original-feature-and-assignment-authority-is-independent-interrogative-feature",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "07bacaa1693995e50f393aee59a84eb345a4360f41c74705d1900a0b5e6753d6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_original_feature_and_assignment_authority_is_independent[auxiliary-feature]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-original-feature-and-assignment-authority-is-independent-auxiliary-feature",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "07bacaa1693995e50f393aee59a84eb345a4360f41c74705d1900a0b5e6753d6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_original_feature_and_assignment_authority_is_independent[binder-assignment]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-lexical-original-feature-and-assignment-authority-is-independent-binder-assignment",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "07bacaa1693995e50f393aee59a84eb345a4360f41c74705d1900a0b5e6753d6"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_pack_preserves_all_predecessor_fields": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retiring-definition-cue-preserves-all-other-reviewed-form-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "form-context",
        "source_ast_sha256": "12715ca076dffabd7bf77c9639dd4f976f533dc589bc4d5d64aacd59e5911d6b",
        "supersedes_node_id": "tests/test_foundation_semantics.py::test_retiring_definition_cue_preserves_all_other_reviewed_form_fields"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_explicit_unknown_frame_preserves_literal_query_and_binder": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-closure-unknown-designation-current-context-blocker",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "proposal-context",
        "source_ast_sha256": "99ec5c79f05e814f47baa5092208bbfb86f2e7951240e3392c067ebee95537ed",
        "supersedes_node_id": "tests/test_proposal_context_builder.py::test_unknown_designation_query_builds_one_exact_unresolved_designation_frame"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_explicit_unknown_uses_unchanged_program_actions": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-unresolved-designation-unresolved-designation-derivation-uses-program-abi-2-without-new-actions",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "cce1414858f352aca00906b0c3d80c2812646d7330cb0d3c6121b6e17dd50fea",
        "supersedes_node_id": "tests/test_proposal_context_program_verifier_canary.py::test_unresolved_designation_derivation_uses_program_abi_2_without_new_actions"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_explicit_unknown_preserves_response_lineage": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-closure-unknown-designation-preserves-literal",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "source_ast_sha256": "699450c4eec78e5ef441fe39c469514fe076a5b2d745b47f9fbdd8cce7da55fc",
        "supersedes_node_id": "tests/test_r3_r4_predecessor_regressions.py::test_closure_unknown_designation_preserves_literal_and_unknown_action"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[unhashable-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-unhashable-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[unhashable-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-unhashable-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[numeric-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-numeric-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[numeric-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-numeric-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[empty-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-empty-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[empty-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-empty-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[boolean-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-boolean-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic[boolean-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-fresh-identity-is-failure-atomic-boolean-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "fefbb08c67b05eddfd284db7b85ed7aac5486437f9a6cdd753fd6d9e01bb6c86"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[unhashable-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-unhashable-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[unhashable-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-unhashable-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[numeric-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-numeric-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[numeric-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-numeric-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[empty-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-empty-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[empty-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-empty-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[boolean-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-boolean-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic[boolean-focus]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-invalid-recommit-identity-is-failure-atomic-boolean-focus",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c48e7376c74b48ad063da5d997799c6ec86045f933f669ad2b822d7b27aa891b"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_generic_identity_checks_add_no_length_cap": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-generic-identity-checks-add-no-length-cap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "db3e72860569c179d4cca70ae799c39293276864229c5577a4584aef98a33f96"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_commit_hashes_exact_stored_json[tuple]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-commit-hashes-exact-stored-json-tuple",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "03e6a7edb61ca96fb385b695a991d3bacff3f91952632398ba0d4e95af008aad"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_commit_hashes_exact_stored_json[list]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-commit-hashes-exact-stored-json-list",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "03e6a7edb61ca96fb385b695a991d3bacff3f91952632398ba0d4e95af008aad"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_commit_hashes_exact_stored_json[nested-tuples-and-lists]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-commit-hashes-exact-stored-json-nested-tuples-and-lists",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "03e6a7edb61ca96fb385b695a991d3bacff3f91952632398ba0d4e95af008aad"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_json_normalization_preserves_canonical_record[canonical-lists]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-json-normalization-preserves-canonical-record-canonical-lists",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "cc4c796ffe5b36a00869ed3bc33bf1581011e2a1589e3a19bb5f58d551ad6a79"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_json_normalization_preserves_canonical_record[normalized-tuples]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-json-normalization-preserves-canonical-record-normalized-tuples",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "cc4c796ffe5b36a00869ed3bc33bf1581011e2a1589e3a19bb5f58d551ad6a79"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_session_window_precedes_person_and_turn_filter[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-session-window-precedes-person-and-turn-filter-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "82d69234997c24967c893fb3ec45a11627794a3586fb4c4fb7166dc3c4ec4101"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_session_window_precedes_person_and_turn_filter[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-session-window-precedes-person-and-turn-filter-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "82d69234997c24967c893fb3ec45a11627794a3586fb4c4fb7166dc3c4ec4101"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_session_window_precedes_person_and_turn_filter[sqlite-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-session-window-precedes-person-and-turn-filter-sqlite-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "82d69234997c24967c893fb3ec45a11627794a3586fb4c4fb7166dc3c4ec4101"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_commit_order_and_record_snapshot_identity[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-commit-order-and-record-snapshot-identity-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "e46b84986e8d3e44fc20a1042d3640fa6ea856f248d7cf661f24016b302996f8"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_commit_order_and_record_snapshot_identity[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-commit-order-and-record-snapshot-identity-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "e46b84986e8d3e44fc20a1042d3640fa6ea856f248d7cf661f24016b302996f8"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_commit_order_and_record_snapshot_identity[sqlite-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-commit-order-and-record-snapshot-identity-sqlite-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "e46b84986e8d3e44fc20a1042d3640fa6ea856f248d7cf661f24016b302996f8"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_codec_requires_exact_abi[boolean]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-codec-requires-exact-abi-boolean",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "82f7fdb79bac233c527454df0ec3613b5ed8d62c4a720fc7f6a2ba57c6b5870a"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_codec_requires_exact_abi[float]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-codec-requires-exact-abi-float",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "82f7fdb79bac233c527454df0ec3613b5ed8d62c4a720fc7f6a2ba57c6b5870a"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[raw-target-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-raw-target-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[raw-target-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-raw-target-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[raw-semantic-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-raw-semantic-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[raw-semantic-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-raw-semantic-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[unknown-field-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-unknown-field-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[unknown-field-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-unknown-field-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[empty-expression-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-empty-expression-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[empty-expression-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-empty-expression-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[abi-bool-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-abi-bool-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[abi-bool-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-abi-bool-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[abi-float-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-abi-float-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[abi-float-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-abi-float-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[key-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-key-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[key-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-key-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[session-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-session-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[session-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-session-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[generation-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-generation-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[generation-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-generation-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[world-future-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-world-future-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[world-future-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-world-future-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[session-future-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-session-future-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[session-future-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-session-future-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[episode-future-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-episode-future-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[episode-future-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-episode-future-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[effect-future-memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-effect-future-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_rejects_unauthenticated_record[effect-future-sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-rejects-unauthenticated-record-effect-future-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "973b1e430cd39f7a807fdd7063c40296a8e401eeb6a8f892f1d8f64f53f35498"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_checks_payload_hash_at_read_boundary[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-checks-payload-hash-at-read-boundary-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "225b42dc854d3b6cd918dc384df535342335d75eff856398726971f828f4aeed"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_checks_payload_hash_at_read_boundary[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-checks-payload-hash-at-read-boundary-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "225b42dc854d3b6cd918dc384df535342335d75eff856398726971f828f4aeed"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_checks_sqlite_row_envelope[stored-key]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-checks-sqlite-row-envelope-stored-key",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "8239bb4b8941dda16f163cd057b301603bc0e11872ada9101ca30824f35cf875"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_checks_sqlite_row_envelope[stored-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-checks-sqlite-row-envelope-stored-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "8239bb4b8941dda16f163cd057b301603bc0e11872ada9101ca30824f35cf875"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_checks_sqlite_row_envelope[stored-future-revision]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-checks-sqlite-row-envelope-stored-future-revision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "8239bb4b8941dda16f163cd057b301603bc0e11872ada9101ca30824f35cf875"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_only_authenticates_requested_window[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-only-authenticates-requested-window-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "5dae337360681112f02390352c88fdd407c9ed4d0152044d8fb0a9d33ca3e620"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_only_authenticates_requested_window[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-only-authenticates-requested-window-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "5dae337360681112f02390352c88fdd407c9ed4d0152044d8fb0a9d33ca3e620"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_preserves_active_window_overflow[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-preserves-active-window-overflow-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "665f2f0e93470c08f653705d6615af4ccd724a932ddd3a6c4c87edc9327c77cf"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_preserves_active_window_overflow[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-preserves-active-window-overflow-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "665f2f0e93470c08f653705d6615af4ccd724a932ddd3a6c4c87edc9327c77cf"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_preserves_active_window_overflow[sqlite-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-preserves-active-window-overflow-sqlite-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "665f2f0e93470c08f653705d6615af4ccd724a932ddd3a6c4c87edc9327c77cf"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_sqlite_index_and_irrelevant_session_work": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-sqlite-index-and-irrelevant-session-work",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "5c942184b45c3f9d7c0b4eadffdd003a655c22f81d54a95dc2f293238a00aecd"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_memory_does_not_enumerate_global_history": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-memory-does-not-enumerate-global-history",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "86e183a649afb0436ab53bfeffc2b96d33da8aa568c3186670d2ac4125b18a3c"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_cross_session_recommit_stays_untrusted[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-cross-session-recommit-stays-untrusted-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "620f029a5bc993375c4d1d71379e6485d365c28fa028833626d126b75a3d1bd5"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_cross_session_recommit_stays_untrusted[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-cross-session-recommit-stays-untrusted-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "620f029a5bc993375c4d1d71379e6485d365c28fa028833626d126b75a3d1bd5"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_cross_session_recommit_stays_untrusted[sqlite-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-cross-session-recommit-stays-untrusted-sqlite-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "620f029a5bc993375c4d1d71379e6485d365c28fa028833626d126b75a3d1bd5"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_preserves_input_and_codec_limits[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-preserves-input-and-codec-limits-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7000320fd106f22d8aa873677e6e88a8061f925f8cf755050896c8d4f334ceee"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_preserves_input_and_codec_limits[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-preserves-input-and-codec-limits-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7000320fd106f22d8aa873677e6e88a8061f925f8cf755050896c8d4f334ceee"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_r3_maximum_retains_sentinel_and_nested_codec_bound": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-r3-maximum-retains-sentinel-and-nested-codec-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "5e91274fec110a399e573cda15267764d4c474941592953335bc01398266e629"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_index_activation_preserves_rows_and_revisions": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-index-activation-preserves-rows-and-revisions",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "928b5214bbe98c22ac7de7e8817b1e79cf4c55aef83e71c3b0b8bf406f5877a3"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_standalone_diagnostic_api_remains_transient": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-standalone-diagnostic-api-remains-transient",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "1d1409b2ddbfbe4fa4d80853309c2ec30f6e3330e422c38705850a877a61d0c2"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_active_orient_preserves_record_identity_without_writing[current-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-active-orient-preserves-record-identity-without-writing-current-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "337be4a4b413b76ab4a1838dc3f126bf65a163fdaecdd073e23cbc4ee81443d5"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_active_orient_preserves_record_identity_without_writing[after-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-active-orient-preserves-record-identity-without-writing-after-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "337be4a4b413b76ab4a1838dc3f126bf65a163fdaecdd073e23cbc4ee81443d5"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_historical_pin_remains_valid_after_store_advances[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-historical-pin-remains-valid-after-store-advances-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "af56dc00a50a609364d3df327a1637bab707ce14ee9c6773d90acb7737aa7b4c"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_historical_pin_remains_valid_after_store_advances[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-historical-pin-remains-valid-after-store-advances-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "af56dc00a50a609364d3df327a1637bab707ce14ee9c6773d90acb7737aa7b4c"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_historical_pin_remains_valid_after_store_advances[sqlite-reopen]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-historical-pin-remains-valid-after-store-advances-sqlite-reopen",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "af56dc00a50a609364d3df327a1637bab707ce14ee9c6773d90acb7737aa7b4c"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_sqlite_unscoped_window_uses_recency_index": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-sqlite-unscoped-window-uses-recency-index",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "b4a9a0aca9e7b89244503752c4377210fdf71deafc374799ed74eda2565f32f8"
    },
    "tests/test_foundation_semantics.py::test_foundation_focus_restart_memory_window_visits_only_limit_and_sentinel": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-focus-restart-memory-window-visits-only-limit-and-sentinel",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4",
        "owner_ref": "situation-context",
        "source_ast_sha256": "2a71b2df31d3af77fa9af62f714744ba7e6f98483729bcf4f8a480c6be1d6ef0"
    },
    "tests/test_foundation_semantics.py::test_foundation_nonstate_transition_guard_preserves_complete_source_partition": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-abi1-test-context-rejects-transition-on-non-state-frame",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Fixture-Repair",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "3cfdb1558ccd22713b6f297ce989dc94e4a1963efd42ed5d3d845516789a98d3",
        "supersedes_node_id": "tests/test_proposal_context_abi1.py::test_context_rejects_transition_on_non_state_frame"
    },
    "tests/test_foundation_semantics.py::test_foundation_context_fixture_has_independent_exact_query_evidence": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-context-fixture-independent-exact-query-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Fixture-Repair",
        "owner_ref": "form-context",
        "source_ast_sha256": "17f6529a4b382fca5fa771757b4dbc35aba998a0529dde976860807ae5ccb1a2"
    },
    "tests/test_foundation_semantics.py::test_foundation_context_duplicate_source_and_span_guards_have_valid_query_setup": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-abi1-test-context-rejects-duplicate-slots-unknown-sources-and-invalid-spans",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Fixture-Repair",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "4896508b28d99ae36736434f288f64ec242824bb7deb68c6dc62e6c06d920384",
        "supersedes_node_id": "tests/test_proposal_context_abi1.py::test_context_rejects_duplicate_slots_unknown_sources_and_invalid_spans"
    },
    "tests/test_foundation_semantics.py::test_foundation_context_exact_geometry_guards_have_complete_query_sources[zero-width]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-abi1-test-direct-context-rejects-zero-width-and-noncontiguous-spans-zero-width",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Fixture-Repair",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "fa0858d369939e09da8739eedf96e3e8350cc708a248f81b07d37c4b44201408",
        "supersedes_node_id": "tests/test_proposal_context_abi1.py::test_direct_context_rejects_zero_width_and_noncontiguous_spans[zero-width]"
    },
    "tests/test_foundation_semantics.py::test_foundation_context_exact_geometry_guards_have_complete_query_sources[gap]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-abi1-test-direct-context-rejects-zero-width-and-noncontiguous-spans-gap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Fixture-Repair",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "fa0858d369939e09da8739eedf96e3e8350cc708a248f81b07d37c4b44201408",
        "supersedes_node_id": "tests/test_proposal_context_abi1.py::test_direct_context_rejects_zero_width_and_noncontiguous_spans[gap]"
    },
    "tests/test_foundation_semantics.py::test_foundation_context_exact_geometry_guards_have_complete_query_sources[overlap]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-abi1-test-direct-context-rejects-zero-width-and-noncontiguous-spans-overlap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Fixture-Repair",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "fa0858d369939e09da8739eedf96e3e8350cc708a248f81b07d37c4b44201408",
        "supersedes_node_id": "tests/test_proposal_context_abi1.py::test_direct_context_rejects_zero_width_and_noncontiguous_spans[overlap]"
    },
    "tests/test_foundation_semantics.py::test_foundation_variable_role_guard_has_exact_query_evidence_and_body_coverage": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-coverage-abi2-test-variable-slot-role-must-belong-to-its-exact-body-frame",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Fixture-Repair",
        "owner_ref": "program-verifier",
        "source_ast_sha256": "1ab248554e3c65d4fb9d6b4706405336c25418ff5ee5b72cfb2105083c4ed917",
        "supersedes_node_id": "tests/test_coverage_abi2.py::test_variable_slot_role_must_belong_to_its_exact_body_frame"
    },
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
    "tests/test_foundation_semantics.py::test_foundation_scoped_event_query_contract_requests_clarification": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-scoped-event-query-contract-requests-clarification",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "f25b01f8524e08ef9ca92034c814b8dbb72a721453f6d8ea2d55b7de6807d14f"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_context_kind_domain_is_not_an_orientation_alternative_cap": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-lexical-context-kind-domain-is-not-orientation-alternative-cap",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "form-context",
        "source_ast_sha256": "6508217ead27b59f6f6cf6fdb3f9e93c609e55dbc5acf0a59c43d11a557920e5"
    },
    "tests/test_foundation_semantics.py::test_foundation_lexical_content_interrogative_assignment_uses_exact_evidence": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-lexical-content-interrogative-assignment-uses-exact-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-4-Lexical-Lookup",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "06a65053ffb1cf0cfe1af0697ad851eefd723ff57443941a731d8625f37e1876"
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


def test_foundation_scoped_event_query_contract_requests_clarification(linked_authority) -> None:
    scenario = ReviewedScenario.from_dict({
        "scenario_ref": "scenario:foundation-independent-scoped-event-query",
        "review_status": "reviewed",
        "competency_category": "modality",
        "semantic_assertions": [{
            "actor": "participant:user",
            "event_target": "participant:system",
            "kind": "modality",
            "modality_kind": "capability",
            "surface": "CEMM",
            "target": "event:learn_alias",
        }],
        "surface_examples": ["independent form evidence"],
        "metadata": {},
    })

    contract = _compile_scenario(linked_authority, scenario)

    assert contract.expected_mode is SemanticMode.QUERY
    assert contract.expected_decision.status is DecisionStatus.PARTIAL
    assert contract.expected_decision.action is DecisionAction.REQUEST_CLARIFICATION
    assert contract.expected_decision.blocker_refs == ("query:partial_conjunct",)
    assert contract.expected_response.cycle_status.value == "partial"
    assert contract.expected_response.discourse_action == "clarify"
    assert contract.expected_response.epistemic_status_ref == "epistemic_status:partial"


def test_foundation_lexical_context_kind_domain_is_not_an_orientation_alternative_cap(
    tmp_path: Path,
) -> None:
    from cemm_authoritative_hybrid.authority import AtomRecord

    runtime = load_runtime(
        ROOT,
        profile="development",
        store_path=tmp_path / "reviewed-kind-domain.db",
    )
    try:
        config = RuntimeConfig.release()
        base_authority = runtime.authority

        class ReviewedAuthorityView:
            def __init__(self) -> None:
                self.atoms = dict(base_authority.atoms)
                self.atoms.update({
                    f"synthetic:test-kind-{index}": AtomRecord(
                        ref=f"synthetic:test-kind-{index}",
                        kind=f"reviewed_test_kind_{index}",
                    )
                    for index in range(config.max_orientation_alternatives + 1)
                })

            def __getattr__(self, name):
                return getattr(base_authority, name)

        authority = ReviewedAuthorityView()
        pack = json.loads(
            (ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8")
        )
        resolver = FormResolver(pack, config)
        affordances = SemanticAffordanceIndex(authority, config)

        class ReviewedIndex:
            def build_index(self):
                return authority.designations

        builder = ProposalContextBuilder(
            authority,
            affordances,
            config,
            form_pack=pack,
        )
        runtime._owners["orientation"] = RuntimeOrientationOwner(
            authority=authority,
            stores=runtime.stores,
            config=config,
            form_resolver=resolver,
            grounder=Grounder(
                authority,
                config,
                form_pack=pack,
                form_pack_hash=resolver.form_pack_hash,
                designation_store=ReviewedIndex(),
            ),
            contribution_expander=ContributionExpander(affordances, config),
            context_builder=builder,
        )

        _, context = runtime.orient(
            "session:reviewed-kind-domain",
            "What does mother mean?",
        )

        assert len(builder._designation_target_kinds) > config.max_orientation_alternatives
        frame = context.unresolved_designation_frames[0]
        variable = next(
            row
            for row in context.variable_slots
            if row.application_frame_ref == frame.slot_ref
        )
        assert variable.required_kinds == builder._designation_target_kinds
        assert ProposalContext.from_dict(context.as_dict()) == context
    finally:
        runtime.stores.close()


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


def _restart_focus(stores, suffix, *, session="session:focus", participant="participant:system", pin=None):
    """Trusted direct-owner fixture; no assertion of a real equivalence receipt."""
    return VerifiedSemanticFocus.create(
        expression_refs=(f"expression:{suffix}",), entity_refs=(), event_refs=(),
        salience_proof_refs=(f"proof:trusted-fixture:{suffix}",),
        participant_ref=participant, session_ref=session, turn_ref=f"turn:{suffix}",
        revision_pin=pin or stores.revision_pin(),
    )


def _restart_stores(backend, tmp_path):
    return memory_stores() if backend == "memory" else open_stores(
        tmp_path / "focus.db", authority_generation="authority:generation-test",
    )


def _restart_reopen(stores, backend, tmp_path):
    if backend == "sqlite-reopen":
        stores.close()
        return _restart_stores(backend, tmp_path)
    return stores


@pytest.mark.parametrize("backend", ("memory", "sqlite", "sqlite-reopen"), ids=("memory", "sqlite", "sqlite-reopen"))
def test_foundation_focus_restart_session_window_precedes_person_and_turn_filter(backend, tmp_path, linked_authority):
    stores = _restart_stores(backend, tmp_path)
    try:
        writer = FocusStore(stores)
        old = _restart_focus(stores, "old")
        latest = _restart_focus(stores, "latest")
        user = _restart_focus(stores, "user", participant="participant:user")
        current = _restart_focus(stores, "current")
        for row in (old, latest, user, current):
            writer.add(row)
        for index in range(40):
            writer.add(_restart_focus(stores, f"other-{index}", session="session:other"))
        stores = _restart_reopen(stores, backend, tmp_path)
        reader = FocusStore(stores)
        before = (stores.revision_pin(), stores.focus.revision, stores.obligations.revision, stores.r3_world_facts())
        resolver = ReferenceResolver(reader, linked_authority)
        result = resolver.resolve("reference:content", ReferenceConstraints("second", None, "content", 4, "session:focus"), "turn:current")
        assert result.selected_ref == latest.expression_refs[0]
        assert result.alternative_refs == old.expression_refs
        assert result.proof_refs == (latest.focus_ref,)
        # Person/current-turn filtering cannot silently search beyond this window.
        narrow = resolver.resolve("reference:content", ReferenceConstraints("second", None, "content", 2, "session:focus"), "turn:current")
        assert narrow.selected_ref is None and narrow.alternative_refs == () and narrow.proof_refs == ()
        assert reader.entries == () and reader.refs == frozenset()
        assert (stores.revision_pin(), stores.focus.revision, stores.obligations.revision, stores.r3_world_facts()) == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite", "sqlite-reopen"), ids=("memory", "sqlite", "sqlite-reopen"))
def test_foundation_focus_restart_commit_order_and_record_snapshot_identity(backend, tmp_path):
    from cemm_authoritative_hybrid.r3_persistence import focus_snapshot
    stores = _restart_stores(backend, tmp_path)
    try:
        first = _restart_focus(stores, "first")
        second = _restart_focus(stores, "second")
        third = _restart_focus(stores, "third", session="session:other")
        writer = FocusStore(stores)
        for row in (first, second, third, first):
            writer.add(row)
        stores = _restart_reopen(stores, backend, tmp_path)
        reader = FocusStore(stores)
        assert reader.recent_entries(3) == (second, third, first)
        assert reader.recent_entries(2, session_ref="session:focus") == (second, first)
        material = {"session_ref": "session:focus", "focus_refs": [first.focus_ref, second.focus_ref], "focus_store_revision": 4}
        assert stores.r3_focus_snapshot("session:focus", maximum=2) == {"snapshot_ref": stable_ref("r3_focus_snapshot", material), **material}
        snapshot = focus_snapshot(stores, "session:focus", maximum=2)
        assert tuple(snapshot["focus_refs"]) == (first.focus_ref, second.focus_ref)
        assert not set(snapshot["focus_refs"]) & set(first.expression_refs + second.expression_refs)
    finally:
        stores.close()


@pytest.mark.parametrize("abi", (True, 1.0), ids=("boolean", "float"))
def test_foundation_focus_restart_codec_requires_exact_abi(abi):
    stores = memory_stores()
    row = _restart_focus(stores, "codec")
    wire = row.as_dict()
    assert VerifiedSemanticFocus.from_dict(wire) == row
    wire["abi_version"] = abi
    with pytest.raises(TypeError, match="abi_version must be exact int"):
        VerifiedSemanticFocus.from_dict(wire)


@pytest.mark.parametrize(
    "backend,attack", (
        ("memory", "raw-target"),
        ("sqlite", "raw-target"),
        ("memory", "raw-semantic"),
        ("sqlite", "raw-semantic"),
        ("memory", "unknown-field"),
        ("sqlite", "unknown-field"),
        ("memory", "empty-expression"),
        ("sqlite", "empty-expression"),
        ("memory", "abi-bool"),
        ("sqlite", "abi-bool"),
        ("memory", "abi-float"),
        ("sqlite", "abi-float"),
        ("memory", "key"),
        ("sqlite", "key"),
        ("memory", "session"),
        ("sqlite", "session"),
        ("memory", "generation"),
        ("sqlite", "generation"),
        ("memory", "world-future"),
        ("sqlite", "world-future"),
        ("memory", "session-future"),
        ("sqlite", "session-future"),
        ("memory", "episode-future"),
        ("sqlite", "episode-future"),
        ("memory", "effect-future"),
        ("sqlite", "effect-future"),
    ), ids=(
        "raw-target-memory",
        "raw-target-sqlite",
        "raw-semantic-memory",
        "raw-semantic-sqlite",
        "unknown-field-memory",
        "unknown-field-sqlite",
        "empty-expression-memory",
        "empty-expression-sqlite",
        "abi-bool-memory",
        "abi-bool-sqlite",
        "abi-float-memory",
        "abi-float-sqlite",
        "key-memory",
        "key-sqlite",
        "session-memory",
        "session-sqlite",
        "generation-memory",
        "generation-sqlite",
        "world-future-memory",
        "world-future-sqlite",
        "session-future-memory",
        "session-future-sqlite",
        "episode-future-memory",
        "episode-future-sqlite",
        "effect-future-memory",
        "effect-future-sqlite",
    ),
)
def test_foundation_focus_restart_rejects_unauthenticated_record(backend, attack, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _restart_focus(stores, "auth")
        payload = row.as_dict()
        key = row.focus_ref
        session = row.session_ref
        error = ValueError
        match = "VerifiedSemanticFocus fields mismatch"
        if attack.startswith("raw-"):
            payload = {"target_ref" if attack == "raw-target" else "semantic_ref": "entity:arbitrary"}
        elif attack == "unknown-field":
            payload["extra"] = "unreviewed"
        elif attack == "empty-expression":
            payload["expression_refs"] = []
            match = "expression_refs must be nonempty"
        elif attack in {"abi-bool", "abi-float"}:
            payload["abi_version"] = True if attack == "abi-bool" else 1.0
            error, match = TypeError, "abi_version must be exact int"
        elif attack == "key":
            key, match = "focus:wrong-key", "non-canonical focus encoding"
        elif attack == "session":
            session, match = "session:wrong", "non-canonical focus encoding"
        else:
            pin = stores.revision_pin().as_dict()
            if attack == "generation":
                pin["authority_generation"] = "authority:stale"
                match = "focus authority generation differs"
            else:
                pin[attack.removesuffix("-future") + "_revision"] += 1
                match = "focus revision pin exceeds"
            row = _restart_focus(stores, "auth", pin=RevisionPin.from_dict(pin))
            payload, key = row.as_dict(), row.focus_ref
        stores.focus.commit(key, session, payload, expected_revision=0)
        before = stores.revision_pin(), stores.focus.revision
        with pytest.raises(error, match=match):
            stores.r3_focus_snapshot(session, maximum=16)
        with pytest.raises(error, match=match):
            FocusStore(stores).recent_entries(1)
        assert (stores.revision_pin(), stores.focus.revision) == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_focus_restart_checks_payload_hash_at_read_boundary(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _restart_focus(stores, "original")
        FocusStore(stores).add(row)
        if backend == "sqlite":
            stores._backend._conn.execute("UPDATE focus SET payload_hash=? WHERE focus_ref=?", ("tampered", row.focus_ref))
            stores._backend._conn.commit()
        else:
            stores.focus._focus[row.focus_ref]["turn_ref"] = "turn:tampered"
        with pytest.raises(ValueError, match="focus payload hash mismatch"):
            stores.r3_focus_snapshot(row.session_ref, maximum=16)
        with pytest.raises(ValueError, match="focus payload hash mismatch"):
            FocusStore(stores).recent_entries(1)
    finally:
        stores.close()


@pytest.mark.parametrize("column", ("focus_ref", "session_ref", "revision"), ids=("stored-key", "stored-session", "stored-future-revision"))
def test_foundation_focus_restart_checks_sqlite_row_envelope(column, tmp_path):
    stores = _restart_stores("sqlite", tmp_path)
    try:
        row = _restart_focus(stores, "envelope")
        FocusStore(stores).add(row)
        value = 2 if column == "revision" else "ref:tampered"
        stores._backend._conn.execute(f"UPDATE focus SET {column}=?", (value,))
        stores._backend._conn.commit()
        match = "focus commit revision exceeds" if column == "revision" else "focus stored key/session mismatch"
        with pytest.raises(ValueError, match=match):
            FocusStore(stores).recent_entries(1)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_focus_restart_only_authenticates_requested_window(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        stores.focus.commit("focus:malformed-old", "session:focus", {"target_ref": "entity:untrusted"}, expected_revision=0)
        row = _restart_focus(stores, "valid")
        FocusStore(stores).add(row)
        stores.focus.commit("focus:malformed-other", "session:other", {}, expected_revision=2)
        reader = FocusStore(stores)
        assert reader.recent_entries(1, session_ref=row.session_ref) == (row,)
        with pytest.raises(ValueError, match="VerifiedSemanticFocus fields mismatch"):
            reader.recent_entries(2, session_ref=row.session_ref)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite", "sqlite-reopen"), ids=("memory", "sqlite", "sqlite-reopen"))
def test_foundation_focus_restart_preserves_active_window_overflow(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        writer = FocusStore(stores)
        for index in range(16):
            writer.add(_restart_focus(stores, f"bounded-{index}"))
        assert len(stores.r3_focus_snapshot("session:focus", maximum=16)["focus_refs"]) == 16
        writer.add(_restart_focus(stores, "overflow"))
        stores = _restart_reopen(stores, backend, tmp_path)
        with pytest.raises(ValueError, match="focus snapshot exceeds its configured bound"):
            stores.r3_focus_snapshot("session:focus", maximum=16)
        assert len(FocusStore(stores).recent_entries(16)) == 16
    finally:
        stores.close()


def test_foundation_focus_restart_sqlite_index_and_irrelevant_session_work(tmp_path):
    stores = _restart_stores("sqlite", tmp_path)
    try:
        for index in range(4):
            FocusStore(stores).add(_restart_focus(stores, f"wanted-{index}"))
        conn = stores._backend._conn
        work = []
        for count in (0, 128, 4096):
            for index in range(count):
                # Unrelated records need not be decoded during the requested read.
                stores.focus.commit(f"focus:other-{count}-{index}", "session:other", {}, expected_revision=stores.focus.revision)
            steps = []
            statements = []
            conn.set_progress_handler(lambda: steps.append(1) or 0, 1)
            conn.set_trace_callback(statements.append)
            try:
                assert len(stores.r3_focus_snapshot("session:focus", maximum=16)["focus_refs"]) == 4
            finally:
                conn.set_progress_handler(None, 0)
                conn.set_trace_callback(None)
            work.append(len(steps))
            queries = [sql for sql in statements if "FROM focus" in sql]
            assert len(queries) == 1
            plan = tuple(row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + queries[0]))
            assert any("USING INDEX" in detail for detail in plan), plan
            assert all("SCAN focus" not in detail and "TEMP B-TREE" not in detail for detail in plan), plan
        assert max(work) <= min(work) + 16, work
        print("focus SQLite VM steps at 0/128/4224 irrelevant rows:", work)
    finally:
        stores.close()


def test_foundation_focus_restart_memory_does_not_enumerate_global_history():
    class NoEnumeration(dict):
        def __iter__(self):
            raise AssertionError("global focus iteration is unbounded")
        def items(self):
            raise AssertionError("global focus items are unbounded")
        def values(self):
            raise AssertionError("global focus values are unbounded")
    stores = memory_stores()
    row = _restart_focus(stores, "wanted")
    FocusStore(stores).add(row)
    for index in range(4096):
        stores.focus.commit(f"focus:other-{index}", "session:other", {}, expected_revision=stores.focus.revision)
    stores.focus._focus = NoEnumeration(stores.focus._focus)
    assert stores.r3_focus_snapshot(row.session_ref, maximum=16)["focus_refs"] == [row.focus_ref]
    assert FocusStore(stores).recent_entries(1, session_ref=row.session_ref) == (row,)


@pytest.mark.parametrize("backend", ("memory", "sqlite", "sqlite-reopen"), ids=("memory", "sqlite", "sqlite-reopen"))
def test_foundation_focus_restart_cross_session_recommit_stays_untrusted(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _restart_focus(stores, "moved")
        FocusStore(stores).add(row)
        # Reusing a content-addressed key for different content is not verified
        # focus. The generic persistence owner still indexes the committed session.
        stores.focus.commit(row.focus_ref, "session:moved", row.as_dict(), expected_revision=1)
        stores = _restart_reopen(stores, backend, tmp_path)
        assert stores.r3_focus_snapshot(row.session_ref, maximum=16)["focus_refs"] == []
        with pytest.raises(ValueError, match="non-canonical focus encoding"):
            stores.r3_focus_snapshot("session:moved", maximum=16)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_focus_restart_preserves_input_and_codec_limits(backend, tmp_path):
    from cemm_authoritative_hybrid.r3_persistence import focus_snapshot
    stores = _restart_stores(backend, tmp_path)
    try:
        reader = FocusStore(stores)
        assert reader.recent_entries(0) == () and reader.recent_entries(512) == ()
        assert focus_snapshot(stores, "session:focus", maximum=10_000)["focus_refs"] == ()
        for invalid in (True, 1.0, -1, 513):
            with pytest.raises((TypeError, ValueError)):
                reader.recent_entries(invalid)
        for invalid in (True, 1.0, 0, -1, 10_001):
            with pytest.raises((TypeError, ValueError)):
                focus_snapshot(stores, "session:focus", maximum=invalid)
        for invalid in (True, "", "s" * 513):
            with pytest.raises((TypeError, ValueError)):
                reader.recent_entries(1, session_ref=invalid)
        row = _restart_focus(stores, "codec-limits")
        wire = row.as_dict()
        wire["expression_refs"] = [f"expression:{index}" for index in range(513)]
        with pytest.raises(ValueError, match="expression_refs exceeds 512 rows"):
            VerifiedSemanticFocus.from_dict(wire)
        at_bound = VerifiedSemanticFocus.create(
            expression_refs=tuple(wire["expression_refs"][:512]), entity_refs=(), event_refs=(),
            salience_proof_refs=(), participant_ref=row.participant_ref,
            session_ref=row.session_ref, turn_ref=row.turn_ref, revision_pin=row.revision_pin,
        )
        assert VerifiedSemanticFocus.from_dict(at_bound.as_dict()) == at_bound
    finally:
        stores.close()


def test_foundation_focus_restart_r3_maximum_retains_sentinel_and_nested_codec_bound():
    from cemm_authoritative_hybrid.r3_persistence import focus_snapshot
    stores = memory_stores()
    for index in range(513):
        row = _restart_focus(stores, f"many-{index}")
        stores.focus.commit(row.focus_ref, row.session_ref, row.as_dict(), expected_revision=stores.focus.revision)
    assert len(stores.r3_focus_snapshot("session:focus", maximum=10_000)["focus_refs"]) == 513
    assert len(FocusStore(stores).recent_entries(512)) == 512
    with pytest.raises(ValueError, match="JSON sequence exceeds bound"):
        focus_snapshot(stores, "session:focus", maximum=10_000)
    for index in range(513, 10_001):
        row = _restart_focus(stores, f"many-{index}")
        stores.focus.commit(row.focus_ref, row.session_ref, row.as_dict(), expected_revision=stores.focus.revision)
    with pytest.raises(ValueError, match="focus snapshot exceeds its configured bound"):
        focus_snapshot(stores, "session:focus", maximum=10_000)


def test_foundation_focus_restart_index_activation_preserves_rows_and_revisions(tmp_path):
    stores = _restart_stores("sqlite", tmp_path)
    row = _restart_focus(stores, "activation")
    FocusStore(stores).add(row)
    before = stores.revision_pin(), stores.focus.revision, stores.focus.get(row.focus_ref)
    conn = stores._backend._conn
    conn.execute("DROP INDEX focus_session_recent")
    conn.execute("DROP INDEX focus_recent")
    conn.commit()
    stores.close()
    stores = _restart_stores("sqlite", tmp_path)
    try:
        assert (stores.revision_pin(), stores.focus.revision, stores.focus.get(row.focus_ref)) == before
        assert FocusStore(stores).recent_entries(1) == (row,)
        indexes = {item[1] for item in stores._backend._conn.execute("PRAGMA index_list(focus)")}
        assert {"focus_session_recent", "focus_recent"} <= indexes
        assert stores._backend._conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert stores._backend._conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "1"
    finally:
        stores.close()


def test_foundation_focus_restart_standalone_diagnostic_api_remains_transient():
    source = memory_stores()
    reader = FocusStore()
    first = _restart_focus(source, "first")
    other = _restart_focus(source, "other", session="session:other")
    for row in (first, other, first):
        reader.add(row)
    assert reader.entries == (first, other, first)
    assert reader.refs == frozenset(first.expression_refs + other.expression_refs)
    assert reader.recent_entries(2) == (other, first)
    assert reader.recent_entries(2, session_ref=first.session_ref) == (first, first)
    assert source.focus.revision == 0


@pytest.mark.parametrize("restart", (False, True), ids=("current-session", "after-reopen"))
def test_foundation_focus_restart_active_orient_preserves_record_identity_without_writing(restart, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "runtime-focus.db")
    try:
        row = _restart_focus(runtime.stores, "active")
        FocusStore(runtime.stores).add(row)
        if restart:
            runtime.stores.close()
            runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "runtime-focus.db")
        before = runtime.stores.revision_pin(), runtime.stores.focus.revision, runtime.stores.obligations.revision
        orientation, _ = runtime.orient(row.session_ref, "Alice is a mother.")
        assert orientation.focus_refs == (row.focus_ref,)
        assert row.expression_refs[0] not in orientation.focus_refs
        assert (runtime.stores.revision_pin(), runtime.stores.focus.revision, runtime.stores.obligations.revision) == before
        # No claim that a record identity answers a speech-history content query.
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite", "sqlite-reopen"), ids=("memory", "sqlite", "sqlite-reopen"))
def test_foundation_focus_restart_historical_pin_remains_valid_after_store_advances(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _restart_focus(stores, "historical")
        FocusStore(stores).add(row)
        stores.world.commit((Fact("fact:later", "op:relation", {"subject": "entity:alice"}),), expected_revision=0)
        stores.sessions.create()
        stores.episodes.append({"event": "later"})
        stores.effects.commit({"effect_key": "effect:later", "payload": {"action": "noop"}})
        stores = _restart_reopen(stores, backend, tmp_path)
        assert stores.revision_pin() != row.revision_pin
        assert FocusStore(stores).recent_entries(1) == (row,)
        assert stores.r3_focus_snapshot(row.session_ref, maximum=16)["focus_refs"] == [row.focus_ref]
    finally:
        stores.close()


def test_foundation_focus_restart_sqlite_unscoped_window_uses_recency_index(tmp_path):
    stores = _restart_stores("sqlite", tmp_path)
    try:
        for index in range(4096):
            stores.focus.commit(f"focus:old-{index}", "session:other", {}, expected_revision=stores.focus.revision)
        row = _restart_focus(stores, "latest-global")
        FocusStore(stores).add(row)
        conn = stores._backend._conn
        statements, steps = [], []
        conn.set_trace_callback(statements.append)
        conn.set_progress_handler(lambda: steps.append(1) or 0, 1)
        try:
            assert FocusStore(stores).recent_entries(1) == (row,)
        finally:
            conn.set_trace_callback(None)
            conn.set_progress_handler(None, 0)
        queries = [sql for sql in statements if "FROM focus" in sql]
        assert len(queries) == 1
        plan = tuple(item[3] for item in conn.execute("EXPLAIN QUERY PLAN " + queries[0]))
        assert any("USING INDEX focus_recent" in detail for detail in plan), plan
        assert all("TEMP B-TREE" not in detail for detail in plan), plan
        assert len(steps) < 64, len(steps)
        print("focus unscoped SQLite VM steps at 4096 irrelevant rows:", len(steps))
    finally:
        stores.close()


def test_foundation_focus_restart_memory_window_visits_only_limit_and_sentinel():
    from collections import OrderedDict
    class CountedRecency(OrderedDict):
        def __reversed__(self):
            for key in super().__reversed__():
                visits.append(key)
                yield key
    stores = memory_stores()
    for index in range(512):
        row = _restart_focus(stores, f"same-session-{index}")
        FocusStore(stores).add(row)
    visits = []
    stores.focus._session_recent[row.session_ref] = CountedRecency(stores.focus._session_recent[row.session_ref])
    assert len(FocusStore(stores).recent_entries(16, session_ref=row.session_ref)) == 16
    assert len(visits) == 16
    visits.clear()
    with pytest.raises(ValueError, match="focus snapshot exceeds its configured bound"):
        stores.r3_focus_snapshot(row.session_ref, maximum=16)
    assert len(visits) == 17


@pytest.mark.parametrize(
    "supplied,stored", (
        ({"values": ("a", "b")}, {"values": ["a", "b"]}),
        ({"values": ["a", "b"]}, {"values": ["a", "b"]}),
        ({"values": ({"inner": ("a", ["b", ("c",)])},)}, {"values": [{"inner": ["a", ["b", ["c"]]]}]}),
    ), ids=("tuple", "list", "nested-tuples-and-lists"),
)
def test_foundation_focus_restart_commit_hashes_exact_stored_json(supplied, stored, tmp_path):
    from hashlib import sha256
    from cemm_authoritative_hybrid.canonical import canonical_bytes
    memory = _restart_stores("memory", tmp_path)
    sqlite = _restart_stores("sqlite", tmp_path)
    try:
        expected = {**stored, "focus_ref": "focus:normalization", "session_ref": "session:normalization"}
        expected_hash = sha256(canonical_bytes(expected)).hexdigest()
        receipts = []
        for stores in (memory, sqlite):
            receipt = stores.focus.commit("focus:normalization", "session:normalization", supplied, expected_revision=0)
            assert stores.focus.get("focus:normalization") == expected
            assert receipt.delta_hash == expected_hash
            receipts.append(receipt)
        assert receipts[0] == receipts[1]
        assert sqlite.focus.verify() == ()
        sqlite.close()
        sqlite = _restart_stores("sqlite", tmp_path)
        assert sqlite.focus.verify() == ()
        assert sqlite.focus.get("focus:normalization") == expected
        assert sqlite.focus.revision == 1
        # Generic JSON normalization is not admission as verified semantic focus.
        with pytest.raises(ValueError, match="VerifiedSemanticFocus fields mismatch"):
            sqlite.r3_focus_snapshot("session:normalization", maximum=16)
    finally:
        memory.close()
        sqlite.close()


@pytest.mark.parametrize("sequence_kind", ("list", "tuple"), ids=("canonical-lists", "normalized-tuples"))
def test_foundation_focus_restart_json_normalization_preserves_canonical_record(sequence_kind, tmp_path):
    memory = _restart_stores("memory", tmp_path)
    sqlite = _restart_stores("sqlite", tmp_path)
    try:
        row = _restart_focus(memory, "normalized-record")
        payload = row.as_dict()
        if sequence_kind == "tuple":
            for field in ("expression_refs", "entity_refs", "event_refs", "salience_proof_refs"):
                payload[field] = tuple(payload[field])
            # The exact codec still requires wire lists. Only the generic JSON
            # persistence boundary normalizes its accepted Python sequences.
            with pytest.raises(TypeError, match="expression_refs wire value must be an exact list"):
                VerifiedSemanticFocus.from_dict(payload)
        receipts = []
        for stores in (memory, sqlite):
            receipts.append(stores.focus.commit(row.focus_ref, row.session_ref, payload, expected_revision=0))
            assert stores.focus.get(row.focus_ref) == row.as_dict()
            assert FocusStore(stores).recent_entries(1) == (row,)
            assert stores.r3_focus_snapshot(row.session_ref, maximum=16)["focus_refs"] == [row.focus_ref]
        assert receipts[0] == receipts[1]
        assert sqlite.focus.verify() == ()
        sqlite.close()
        sqlite = _restart_stores("sqlite", tmp_path)
        assert FocusStore(sqlite).recent_entries(1) == (row,)
        assert sqlite.focus.verify() == ()
    finally:
        memory.close()
        sqlite.close()


def _assert_focus_identity_failure_atomic(backend, field, invalid, *, recommit, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _restart_focus(stores, "failure-atomic")
        if recommit:
            stores.focus.commit(row.focus_ref, row.session_ref, row.as_dict(), expected_revision=0)
        revision = int(recommit)
        expected_payload = row.as_dict() if recommit else None
        expected_entries = (row,) if recommit else ()
        before_pin = stores.revision_pin()
        before_session = dict(stores.r3_focus_snapshot(row.session_ref, maximum=16))
        assert stores.focus.get(row.focus_ref) == expected_payload
        assert FocusStore(stores).recent_entries(16) == expected_entries
        key = invalid if field == "focus_ref" else row.focus_ref
        session = invalid if field == "session_ref" else row.session_ref
        statements = []
        if backend == "sqlite":
            stores._backend._conn.set_trace_callback(statements.append)
        try:
            with pytest.raises(TypeError):
                stores.focus.commit(key, session, row.as_dict(), expected_revision=revision)
        finally:
            if backend == "sqlite":
                stores._backend._conn.set_trace_callback(None)
        assert statements == [], "invalid identities must be rejected before a SQLite transaction"
        assert stores.focus.revision == revision
        assert stores.revision_pin() == before_pin
        assert stores.focus.get(row.focus_ref) == expected_payload
        assert FocusStore(stores).recent_entries(16) == expected_entries
        assert dict(stores.r3_focus_snapshot(row.session_ref, maximum=16)) == before_session
        # A failed generic commit cannot remove recency entries, publish a bad
        # payload, advance revisions, or poison the next legitimate retry.
        receipt = stores.focus.commit(row.focus_ref, row.session_ref, row.as_dict(), expected_revision=revision)
        assert receipt.parent_revision == revision and receipt.new_revision == revision + 1
        assert stores.focus.get(row.focus_ref) == row.as_dict()
        assert FocusStore(stores).recent_entries(16) == (row,)
        assert stores.r3_focus_snapshot(row.session_ref, maximum=16)["focus_refs"] == [row.focus_ref]
    finally:
        stores.close()


@pytest.mark.parametrize(
    "field,invalid", (
        ("session_ref", []), ("focus_ref", []),
        ("session_ref", 7), ("focus_ref", 7),
        ("session_ref", ""), ("focus_ref", ""),
        ("session_ref", True), ("focus_ref", True),
    ), ids=("unhashable-session", "unhashable-focus", "numeric-session", "numeric-focus", "empty-session", "empty-focus", "boolean-session", "boolean-focus"),
)
def test_foundation_focus_restart_invalid_fresh_identity_is_failure_atomic(field, invalid, tmp_path):
    for backend in ("memory", "sqlite"):
        _assert_focus_identity_failure_atomic(backend, field, invalid, recommit=False, tmp_path=tmp_path)


@pytest.mark.parametrize(
    "field,invalid", (
        ("session_ref", []), ("focus_ref", []),
        ("session_ref", 7), ("focus_ref", 7),
        ("session_ref", ""), ("focus_ref", ""),
        ("session_ref", True), ("focus_ref", True),
    ), ids=("unhashable-session", "unhashable-focus", "numeric-session", "numeric-focus", "empty-session", "empty-focus", "boolean-session", "boolean-focus"),
)
def test_foundation_focus_restart_invalid_recommit_identity_is_failure_atomic(field, invalid, tmp_path):
    for backend in ("memory", "sqlite"):
        _assert_focus_identity_failure_atomic(backend, field, invalid, recommit=True, tmp_path=tmp_path)


def test_foundation_focus_restart_generic_identity_checks_add_no_length_cap(tmp_path):
    receipts = []
    focus_ref, session_ref = "f" * 513, "s" * 513
    for backend in ("memory", "sqlite"):
        stores = _restart_stores(backend, tmp_path)
        try:
            receipt = stores.focus.commit(focus_ref, session_ref, {"value": "generic-json"}, expected_revision=0)
            assert stores.focus.get(focus_ref) == {"focus_ref": focus_ref, "session_ref": session_ref, "value": "generic-json"}
            assert stores.focus.revision == 1
            receipts.append(receipt)
        finally:
            stores.close()
    assert receipts[0] == receipts[1]


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


def test_foundation_context_fixture_has_independent_exact_query_evidence():
    from tests.test_proposal_context_abi1 import _context, _context_with_unresolved_designation

    context = _context()
    query = context.contribution_slots[2]
    variable = context.variable_slots[0]
    assert query.kind == "open_variable"
    assert query.target_ref is None and query.target_kind is None
    assert query.source_unit_refs == variable.source_unit_refs == ("unit:grounded-query",)
    assert query.output_ports == (variable.role_ref,) == ("role:object",)
    assert context.source_unit_spans == (
        ("unit:alice", 0, 5), ("unit:loves", 5, 10),
        ("unit:period", 10, 11), ("unit:grounded-query", 11, 15),
    )
    assert context.contributions_for_source("unit:grounded-query") == (query,)
    assert context.contribution_slots[0].source_unit_refs == ("unit:alice",)
    assert context.contribution_slots[1].source_unit_refs == ("unit:loves",)
    assert context.residual_for_source("unit:period") is context.residual_evidence[0]
    assert context.variables_for_frame_role(variable.application_frame_ref, "role:object") == (variable,)
    unresolved, _ = _context_with_unresolved_designation()
    assert set(context.source_unit_refs).isdisjoint(unresolved.source_unit_refs)
    assert ProposalContext.from_dict(context.as_dict()) == context


def test_foundation_context_duplicate_source_and_span_guards_have_valid_query_setup():
    from tests.test_proposal_context_abi1 import _context, _creation_fields
    from cemm_authoritative_hybrid.proposal_context import ResidualEvidence

    context = _context()
    base = _creation_fields(context)
    assert ProposalContext.create(**base) == context
    with pytest.raises(ValueError, match="^duplicate designation slot$"):
        ProposalContext.create(**(base | {"designation_slots": context.designation_slots * 2}))

    # Remove only the predicate source; the query's evidence remains exact.
    missing_source = base | {
        "source_unit_refs": ("unit:alice", "unit:period", "unit:grounded-query"),
        "source_unit_spans": (
            ("unit:alice", 0, 5), ("unit:period", 5, 6),
            ("unit:grounded-query", 6, 10),
        ),
    }
    with pytest.raises(ValueError, match="unknown source unit"):
        ProposalContext.create(**missing_source)

    invalid_spans = (("unit:alice", 5, 0), *context.source_unit_spans[1:])
    assert tuple(row[0] for row in invalid_spans) == context.source_unit_refs
    with pytest.raises(ValueError, match="^source span must have positive width$"):
        ProposalContext.create(**(base | {"source_unit_spans": invalid_spans}))

    duplicate_residual = ResidualEvidence.create(
        source_unit_ref="unit:period", contribution_kind="discourse",
        critical=False, reason="terminal punctuation",
    )
    with pytest.raises(ValueError, match="^duplicate residual source unit$"):
        ProposalContext.create(**(base | {
            "residual_evidence": (*context.residual_evidence, duplicate_residual),
        }))


@pytest.mark.parametrize(
    ("span_index", "changed_span", "message"),
    (
        (3, ("unit:grounded-query", 11, 11), "source span must have positive width"),
        (0, ("unit:alice", 0, 4), "source spans must be contiguous and monotonic"),
        (0, ("unit:alice", 0, 6), "source spans must be contiguous and monotonic"),
    ),
    ids=("zero-width", "gap", "overlap"),
)
def test_foundation_context_exact_geometry_guards_have_complete_query_sources(span_index, changed_span, message):
    from tests.test_proposal_context_abi1 import _context, _creation_fields

    context = _context()
    base = _creation_fields(context)
    assert ProposalContext.create(**base) == context
    spans = (
        *context.source_unit_spans[:span_index], changed_span,
        *context.source_unit_spans[span_index + 1:],
    )
    assert len(spans) == len(context.source_unit_refs)
    assert tuple(row[0] for row in spans) == context.source_unit_refs
    with pytest.raises(ValueError, match=f"^{message}$"):
        ProposalContext.create(**(base | {"source_unit_spans": spans}))


def test_foundation_nonstate_transition_guard_preserves_complete_source_partition():
    from tests.test_proposal_context_abi1 import _context, _creation_fields
    from cemm_authoritative_hybrid.proposal_context import TransitionSlot

    context = _context()
    designation = _membership_slot_with(
        context.designation_slots[0], target_ref="relation:love",
        target_kind="relation_type", designation_fact_ref="designation:love",
    )
    frame = _membership_slot_with(
        context.application_frames[0], designation_slot_ref=designation.slot_ref,
        predicate_target_ref=designation.target_ref, predicate_kind=designation.target_kind,
        operator_ref="op:relation", structural_role_ref="role:relation",
        required_roles=("role:subject", "role:object"), derived_role_targets=(),
        affordance_frame_ref="frame:love", provenance_refs=(designation.slot_ref, "frame:love"),
    )
    predicate = _membership_slot_with(
        context.contribution_slots[1], contribution_ref="contribution:love-predicate",
        target_ref=designation.target_ref, target_kind=designation.target_kind,
        input_ports=("role:subject", "role:object"), output_ports=("role:relation",),
        constraints=(), provenance_refs=("frame:love",),
    )
    creation = _creation_fields(context) | {
        "designation_slots": (designation,), "application_frames": (frame,),
        "contribution_slots": (context.contribution_slots[0], predicate, context.contribution_slots[2]),
        "variable_slots": (), "transition_slots": (),
    }
    valid = ProposalContext.create(**creation)
    assert ProposalContext.from_dict(valid.as_dict()) == valid
    assert valid.source_unit_refs == context.source_unit_refs
    transition = TransitionSlot.create(
        application_frame_ref=frame.slot_ref, event_type_ref="event:set_state",
        compatible_modes=("REQUEST",), required_roles=("role:actor",),
        required_capabilities=("cap:set_state",), required_permissions=("permission:set_state",),
        adapter_ref="adapter:state", source_unit_refs=frame.source_unit_refs,
    )
    with pytest.raises(ValueError, match="^transition requires an op:state application frame$"):
        ProposalContext.create(**(creation | {"transition_slots": (transition,)}))


def _foundation_query_variable_coverage_case(role_ref):
    from tests.test_coverage_abi2 import _context, _rebuild_context
    from cemm_authoritative_hybrid.proposal_context import ModeSlot
    from cemm_authoritative_hybrid.programs import ProgramAction, SemanticSwitchProgram, SourceAssignment

    context = _context()
    query = ContributionSlot.create(
        contribution_ref="contribution:independent-query", kind="open_variable",
        source_unit_refs=("unit:query",), target_ref=None, target_kind=None,
        input_ports=(), output_ports=("role:subject", "role:object"), constraints=(),
    )
    variable = VariableSlot.create(
        application_frame_ref=context.application_frames[0].slot_ref,
        role_ref=role_ref, required_kinds=("entity",),
        source_unit_refs=query.source_unit_refs, construction_ref="construction:query",
    )
    mode = ModeSlot.create(
        mode="QUERY", source_unit_refs=(), construction_ref="construction:query",
        requested_effect="query",
    )
    context = _rebuild_context(
        context, contribution_slots=(context.contribution_slots[0], query),
        mode_slots=(mode,), variable_slots=(variable,),
        source_unit_refs=("unit:predicate", "unit:query"),
        source_unit_spans=(("unit:predicate", 0, 5), ("unit:query", 5, 9)),
    )
    actions = (
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=(mode.slot_ref,)),
        ProgramAction.create(action_index=2, action_type="select_designation", arguments=(context.designation_slots[0].slot_ref,)),
        ProgramAction.create(action_index=3, action_type="instantiate_operator", arguments=("application:0", context.application_frames[0].slot_ref), source_unit_refs=("unit:predicate",)),
        ProgramAction.create(action_index=4, action_type="project_variable", arguments=("binder:0", variable.slot_ref, "application:0"), source_unit_refs=query.source_unit_refs),
        ProgramAction.create(action_index=5, action_type="complete_program", arguments=()),
    )
    assignments = (
        SourceAssignment.create(source_unit_ref="unit:predicate", contribution_slot_ref=context.contribution_slots[0].slot_ref, assignment_kind="predicate", target_action_ref=actions[3].action_ref, target_role_ref=None, residual_kind=None, critical=False),
        SourceAssignment.create(source_unit_ref="unit:query", contribution_slot_ref=query.slot_ref, assignment_kind="role", target_action_ref=actions[4].action_ref, target_role_ref=role_ref, residual_kind=None, critical=False),
    )
    candidate = SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref, proposal_context_ref=context.context_ref,
        actions=actions, root_refs=("binder:0",), mode_slot_ref=mode.slot_ref,
        goal_refs=(), source_unit_refs=context.source_unit_refs,
        source_assignments=assignments, revision_pin=context.revision_pin,
    )
    return context, candidate


def test_foundation_variable_role_guard_has_exact_query_evidence_and_body_coverage():
    from cemm_authoritative_hybrid.coverage import CoverageReceipt, CoverageVerifier

    context, candidate = _foundation_query_variable_coverage_case("role:subject")
    assert ProposalContext.from_dict(context.as_dict()) == context
    positive = CoverageVerifier().verify(context, candidate)
    assert positive.executable and positive.errors == ()
    assert positive.assignments == candidate.source_assignments
    assert CoverageReceipt.from_dict(positive.as_dict()) == positive

    wrong_context, wrong_candidate = _foundation_query_variable_coverage_case("role:object")
    assert wrong_context.application_frames == context.application_frames
    assert wrong_context.contribution_slots == context.contribution_slots
    assert wrong_context.source_unit_spans == context.source_unit_spans
    negative = CoverageVerifier().verify(wrong_context, wrong_candidate)
    assert not negative.executable
    assert tuple(error.code for error in negative.errors) == ("variable_role_incompatible",)
    assert negative.errors[0].target_role_ref == "role:object"


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
    # AUDIT: this direct seed is not authenticated review or acquisition; its
    # reviewer-looking source string cannot authorize index admission. Preserve
    # this diagnostic's positive restart/unseen-composition obligation through
    # a successor using the real publication transaction once implemented.
    # Do not make arbitrary stored designation facts trusted to pass this test.
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


@pytest.mark.parametrize(
    ("literal", "status", "target"),
    (("mother", QueryStatus.SUPPORTED, "concept:mother"),
     ("zorbulate", QueryStatus.UNKNOWN, None),
     ("job role", QueryStatus.SUPPORTED, "concept:job_role"),
     ("Mother", QueryStatus.UNKNOWN, None)),
    ids=("known", "unknown", "multiword", "exact-case"),
)
def test_foundation_lexical_public_exact_target_lookup(literal, status, target, tmp_path):
    expected = _matrix_designation_query(literal)
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "lexical.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:lexical", f"What does {literal} mean?")
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == expected
        query = result.evaluation.query_results[0]
        assert query.status is status
        assert query.bindings == (((expected.binders[0].variable_ref, target),) if target else ())
        assert (query.proof is not None) is (target is not None)
        assert result.response_meaning.discourse_action == ("answer" if target else "unknown")
        assert isinstance(result.effect_receipt, NoEffectReceipt)
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
    finally:
        runtime.stores.close()


def test_foundation_lexical_exact_index_retrieves_admitted_target(linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        expression = _matrix_designation_query("mother")
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _matrix_situation(stores))
        query = result.query_results[0]
        assert query.status is QueryStatus.SUPPORTED
        assert query.bindings == ((expression.binders[0].variable_ref, "concept:mother"),)
        expected = linked_authority.designations.facts_for_surface("mother", "en")[0]
        assert query.retrieval_refs == (expected.designation_fact_ref, linked_authority.content_hash)
        assert expected.designation_fact_ref in query.proof.source_refs
        assert linked_authority.generation in query.proof.source_refs
    finally:
        stores.close()


@pytest.mark.parametrize("case", ("other-language", "nonconcept", "same-target-languages", "competing-targets", "overflow", "literal-question-prefix", "teaching-only", "inverse", "mixed", "negative", "reported", "conditional"),
    ids=("other-language", "nonconcept", "same-target-languages", "competing-targets", "overflow", "literal-question-prefix", "teaching-only", "inverse", "mixed", "negative", "reported", "conditional"))
def test_foundation_lexical_authority_ambiguity_and_typed_constraints(case, linked_authority):
    from types import SimpleNamespace
    literal = "?verbatim" if case == "literal-question-prefix" else "velnora"
    target = "event:learn_alias" if case == "nonconcept" else "concept:mother"
    facts = (DesignationFact.create(surface=literal, target_ref=target, language="es"),)
    if case == "same-target-languages":
        facts += (DesignationFact.create(surface=literal, target_ref=target, language="en"),)
    if case == "competing-targets":
        facts += (DesignationFact.create(surface=literal, target_ref="concept:person", language="es"),)
    if case == "overflow":
        facts = tuple(DesignationFact.create(surface=literal, target_ref=target, language=f"language-{index}") for index in range(40))
    if case == "teaching-only":
        facts = ()
    authority = SimpleNamespace(designations=DesignationIndex(facts), generation=linked_authority.generation,
        content_hash=stable_ref("authority-content", [fact.designation_fact_ref for fact in facts]), atoms=linked_authority.atoms,
        capabilities=linked_authority.capabilities, rules={})
    stores = memory_stores(authority_generation=authority.generation)
    try:
        stores.world.commit((Fact("fact:untrusted-teaching", "op:designation", {"predicate_ref": "label:lexical", "role:label_type": "label:lexical", "role:surface": literal, "role:target": target}),), expected_revision=0)
        expression = _matrix_designation_query(literal)
        if case == "inverse":
            app = SemanticApplication("app:inverse", "op:designation", "label:lexical", (RoleBinding("role:label_type", GroundedReference("label:lexical")), RoleBinding("role:surface", BoundVariable("?surface")), RoleBinding("role:target", GroundedReference(target))))
            binder = VariableBinder("binder:surface", "?surface", app.application_ref)
            expression = SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))
        elif case == "mixed":
            expression = SemanticExpression.create(applications=(*expression.applications, _matrix_state()), binders=expression.binders, root_refs=(*expression.root_refs, _matrix_state().application_ref))
        elif case in {"negative", "reported"}:
            scope = ScopeOperator("scope:query", "scope:polarity" if case == "negative" else "scope:attribution", "polarity:negative" if case == "negative" else "scope_value:attribution:reported", expression.root_refs[0])
            expression = SemanticExpression.create(applications=expression.applications, binders=expression.binders, scope_operators=(scope,), root_refs=(scope.scope_ref,))
        elif case == "conditional":
            link = ExpressionLink("link:query", "link:condition", (_matrix_state().application_ref, expression.root_refs[0]))
            expression = SemanticExpression.create(applications=(*expression.applications, _matrix_state()), binders=expression.binders, expression_links=(link,), root_refs=(link.link_ref,))
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
        query = result.query_results[0]
        if case in {"other-language", "nonconcept", "literal-question-prefix"}:
            assert query.status is QueryStatus.SUPPORTED
            assert query.bindings == ((expression.binders[0].variable_ref, target),)
            assert query.proof and set(query.proof.source_refs) == {facts[0].designation_fact_ref, authority.generation, authority.content_hash}
        else:
            assert query.status is (QueryStatus.UNKNOWN if case == "teaching-only" else QueryStatus.PARTIAL)
            assert query.proof is None and query.bindings == ()
            assert result.contribution.answer_expression_ref is None
        assert stores.world.revision == 1
        if case not in {"mixed", "conditional", "inverse"}:
            assert "fact:untrusted-teaching" not in query.retrieval_refs
            assert authority.content_hash in query.retrieval_refs
        if case in {"same-target-languages", "competing-targets", "overflow"}:
            assert set(query.retrieval_refs) - {authority.content_hash} == {fact.designation_fact_ref for fact in sorted(facts, key=lambda row: (row.language, row.target_ref, row.designation_fact_ref))[:16]}
    finally:
        stores.close()


@pytest.mark.parametrize("surface", ("What is zorbulate?", "Who is mother?", "Where is mother?", "Why does mother mean?", "What did mother mean?", "What does mother mean in Spanish?", "What does mother in Spanish mean?", "What does mother not mean?", "What does mother; Alice likes Bob mean?", "What does mother mean and Bob likes Alice?", "zorbulate means mother.", "Alice learns zorbulate."),
    ids=("generic-what", "generic-who", "generic-where", "reason", "past", "language-trailing", "language-internal", "negative", "punctuated-clause", "extra-clause", "teaching", "unknown-event-argument"))
def test_foundation_lexical_public_does_not_launder_unsupported_evidence(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "blocked-lexical.db")
    try:
        _, context = runtime.orient("session:blocked", surface)
        assert context.unresolved_designation_frames == ()
        before = runtime.stores.world.revision
        result = runtime.process("session:blocked", surface)
        assert result.evaluation is None or all(row.status is not QueryStatus.SUPPORTED for row in result.evaluation.query_results)
        assert runtime.stores.world.revision == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("corruption", ("borrowed-literal", "binder-only", "foreign-query", "foreign-binder", "label"), ids=("borrowed-literal", "binder-only", "foreign-query", "foreign-binder", "label"))
def test_foundation_lexical_independent_reconstruction_checks_exact_owners(corruption, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "forged-lexical.db")
    try:
        _, context = runtime.orient("session:forged", "What does mother mean?")
        proposal = runtime.proposal_model.propose(context)
        program = next(row.program for row in proposal.candidates if any(action.action_type == "instantiate_operator" and context.unresolved_designation_frame(action.arguments[1]) for action in row.program.actions))
        frame = context.unresolved_designation_frames[0]
        if corruption == "borrowed-literal":
            forged_frame = _membership_unchecked(frame, literal_contribution_slot_ref="contribution:foreign")
            forged = _membership_unchecked(context, application_frames=tuple(forged_frame if row == frame else row for row in context.application_frames))
        elif corruption == "label":
            forged_frame = _membership_unchecked(frame, label_type_ref="concept:mother")
            forged = _membership_unchecked(context, application_frames=tuple(forged_frame if row == frame else row for row in context.application_frames))
        else:
            variable = next(row for row in context.variable_slots if row.application_frame_ref == frame.slot_ref)
            source = {"binder-only": ("unit:2", "unit:6"), "foreign-query": ("unit:7", "unit:2", "unit:6"), "foreign-binder": ("unit:0", "unit:2")}[corruption]
            forged_variable = _membership_unchecked(variable, source_unit_refs=source)
            forged = _membership_unchecked(context, variable_slots=tuple(forged_variable if row == variable else row for row in context.variable_slots))
        assert reconstruct_expected_expression(program, forged) is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("nonconcept", "other-language", "ambiguous", "synthetic-feature-transport"), ids=("nonconcept", "other-language", "ambiguous", "synthetic-feature-transport"))
def test_foundation_lexical_public_language_unspecified_and_response(case, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "languages.db")
    try:
        if case == "nonconcept":
            surface, literal, target = "What does learn mean?", "learn", "event:learn_alias"
        else:
            literal, target = "luz velnora", "concept:mother"
            facts = (DesignationFact.create(surface=literal, target_ref=target, language="es"),)
            if case == "ambiguous":
                facts += (DesignationFact.create(surface=literal, target_ref=target, language="fr"),)
            runtime.authority.designations = DesignationIndex(facts)
            runtime.authority.content_hash = stable_ref("authority-content", [row.designation_fact_ref for row in facts])
            surface = "What does luz velnora mean?"
        if case == "synthetic-feature-transport":
            # Synthetic reviewed-feature transport, not natural Spanish grammar.
            pack = json.loads((ROOT / "data/languages/en/forms.json").read_text())
            pack["language"] = "es"
            pack["query_projection"]["qué"] = pack["query_projection"].pop("what")
            pack["query_projection"]["auxiliar"] = pack["query_projection"].pop("does")
            pack["discourse"]["significa"] = pack["discourse"].pop("mean")
            resolver = FormResolver(pack, RuntimeConfig.release())
            affordances = SemanticAffordanceIndex(runtime.authority, RuntimeConfig.release())
            class ReviewedIndex:
                def build_index(self):
                    return runtime.authority.designations
            runtime._owners["orientation"] = RuntimeOrientationOwner(
                authority=runtime.authority, stores=runtime.stores, config=RuntimeConfig.release(),
                form_resolver=resolver, grounder=Grounder(runtime.authority, RuntimeConfig.release(), form_pack=pack, form_pack_hash=resolver.form_pack_hash, designation_store=ReviewedIndex()),
                contribution_expander=ContributionExpander(affordances, RuntimeConfig.release()),
                context_builder=ProposalContextBuilder(runtime.authority, affordances, RuntimeConfig.release(), form_pack=pack))
            surface = "Qué auxiliar luz velnora significa?"
        result = runtime.process("session:languages", surface)
        assert result.verification.selected_meaning.expression == _matrix_designation_query(literal)
        query = result.evaluation.query_results[0]
        if case == "ambiguous":
            assert query.status is QueryStatus.PARTIAL and query.bindings == () and query.proof is None
            assert result.response_meaning.discourse_action == "clarify"
            assert result.response_meaning.bindings == ()
        else:
            assert query.status is QueryStatus.SUPPORTED
            assert query.bindings == ((_matrix_designation_query(literal).binders[0].variable_ref, target),)
            assert result.response_meaning.discourse_action == "answer"
        assert isinstance(result.effect_receipt, NoEffectReceipt)
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("growth", (0, 10000), ids=("small", "grown"))
def test_foundation_lexical_index_work_is_bounded_and_never_scans_world(growth, linked_authority, monkeypatch):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.persistence import SemanticStores
    facts = tuple(DesignationFact.create(surface=f"unrelated-{index}", target_ref="concept:mother", language="en") for index in range(growth))
    matches = tuple(DesignationFact.create(surface="velnora", target_ref="concept:mother", language=f"l-{index:02}") for index in range(40))
    index = DesignationIndex((*facts, *matches))
    visits = []
    class CountedRows:
        def __len__(self):
            return len(matches)
        def __getitem__(self, selection):
            assert selection == slice(None, 16)
            visits.extend(range(16))
            return matches[selection]
    index._exact_surface_all_languages["velnora"] = CountedRows()
    authority = SimpleNamespace(designations=index, generation=linked_authority.generation, content_hash=stable_ref("authority-content", growth))
    stores = memory_stores(authority_generation=authority.generation)
    try:
        def forbidden(*args, **kwargs):
            raise AssertionError("pure lexical target lookup scanned the world")
        monkeypatch.setattr(SemanticStores, "r3_world_facts", forbidden)
        expression = _matrix_designation_query("velnora")
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
        assert visits == list(range(16))
        assert result.query_results[0].status is QueryStatus.PARTIAL
        assert len(result.query_results[0].retrieval_refs) == 17  # 16 rows plus exact snapshot content ref.
    finally:
        stores.close()


def test_foundation_lexical_unknown_identity_binds_source_content(linked_authority):
    from types import SimpleNamespace
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        results = []
        expression = _matrix_designation_query("zorbulate")
        for content in ("authority-content:first", "authority-content:second"):
            authority = SimpleNamespace(designations=DesignationIndex(()), generation=linked_authority.generation, content_hash=content)
            result = QueryDecisionOwner(stores, RuntimeConfig.release(), authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores)).query_results[0]
            assert result.status is QueryStatus.UNKNOWN and result.proof is None and result.bindings == ()
            assert result.retrieval_refs == (content,)
            results.append(result.query_result_ref)
        assert len(set(results)) == 2
    finally:
        stores.close()


def test_foundation_lexical_mentioned_multiword_does_not_expand_constituent_predicates(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "mentioned.db")
    try:
        literal = "job role job role"
        result = runtime.process("session:mentioned", f"What does {literal} mean?")
        assert result.verification.selected_meaning.expression == _matrix_designation_query(literal)
        assert result.evaluation.query_results[0].status is QueryStatus.UNKNOWN
        assert result.proposal.explored_states <= 8 and not result.proposal.truncated
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_foundation_lexical_projection_consumes_exact_owned_binder(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "binder.db")
    try:
        _, context = runtime.orient("session:binder", "What does mother mean?")
        frame = context.unresolved_designation_frames[0]
        binder = context.contribution(frame.query_binder_slot_ref)
        literal = context.contribution(frame.literal_contribution_slot_ref)
        assert not any(row.kind == "open_variable" and "unit:2" in row.source_unit_refs for row in context.contribution_slots)
        assert set(next(row for row in context.variable_slots if row.application_frame_ref == frame.slot_ref).required_kinds) == {row.kind for row in runtime.authority.atoms.values() if row.reviewed}
        proposal = runtime.proposal_model.propose(context)
        assert proposal.candidates
        for candidate in proposal.candidates:
            program = candidate.program
            assert next(row for row in program.actions if row.action_type == "instantiate_operator").source_unit_refs == ()
            surface_action = next(row for row in program.actions if row.action_type == "bind_role")
            assert surface_action.source_unit_refs == literal.source_unit_refs
            assignments = {row.source_unit_ref: row for row in program.source_assignments}
            assert all(assignments[ref].contribution_slot_ref == binder.slot_ref and assignments[ref].critical for ref in binder.source_unit_refs)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("corruption", ("literal-provenance", "binder-provenance", "interrogative-feature", "auxiliary-feature", "binder-assignment"), ids=("literal-provenance", "binder-provenance", "interrogative-feature", "auxiliary-feature", "binder-assignment"))
def test_foundation_lexical_original_feature_and_assignment_authority_is_independent(corruption, tmp_path):
    from cemm_authoritative_hybrid.recursive_compiler import compile_recursive
    from cemm_authoritative_hybrid.expressions import CompilationFailure
    from cemm_authoritative_hybrid.coverage import CoverageVerifier
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "original-owners.db")
    try:
        _, context = runtime.orient("session:original", "What does mother mean?")
        program = runtime.proposal_model.propose(context).candidates[0].program
        frame = context.unresolved_designation_frames[0]
        slots = context.contribution_slots
        if corruption in {"literal-provenance", "binder-provenance"}:
            ref = frame.literal_contribution_slot_ref if corruption == "literal-provenance" else frame.query_binder_slot_ref
            slots = tuple(_membership_unchecked(row, provenance_refs=("form_lattice:foreign",)) if row.slot_ref == ref else row for row in slots)
        elif corruption in {"interrogative-feature", "auxiliary-feature"}:
            source = "unit:0" if corruption == "interrogative-feature" else "unit:2"
            slots = tuple(_membership_unchecked(row, constraints=(("query", "query"), ("interrogative", "person"))) if row.source_unit_refs == (source,) else row for row in slots)
        else:
            other = next(row for row in slots if row.source_unit_refs == ("unit:2",) and row.kind == "binder")
            assignments = tuple(type(row).create(**{field.name: other.slot_ref if field.name == "contribution_slot_ref" else getattr(row, field.name) for field in fields(row) if field.name != "assignment_ref"}) if row.source_unit_ref == "unit:2" else row for row in program.source_assignments)
            program = _membership_unchecked(program, source_assignments=assignments)
            assert not CoverageVerifier(RuntimeConfig.release()).verify(context, program).executable
        forged = _membership_unchecked(context, contribution_slots=slots)
        assert isinstance(compile_recursive(program, forged), CompilationFailure)
        assert reconstruct_expected_expression(program, forged) is None
    finally:
        runtime.stores.close()


def test_foundation_lexical_content_interrogative_assignment_uses_exact_evidence(
    tmp_path,
):
    from cemm_authoritative_hybrid.coverage import CoverageVerifier
    from cemm_authoritative_hybrid.expressions import CompilationFailure
    from cemm_authoritative_hybrid.programs import (
        ProgramAction,
        SemanticSwitchProgram,
        SourceAssignment,
    )
    from cemm_authoritative_hybrid.recursive_compiler import compile_recursive

    runtime = load_runtime(
        ROOT,
        profile="development",
        store_path=tmp_path / "interrogative-assignment.db",
    )
    try:
        _, context = runtime.orient(
            "session:interrogative-assignment",
            "What does mother mean?",
        )
        program = runtime.proposal_model.propose(context).candidates[0].program
        query = next(
            row
            for row in context.contribution_slots
            if row.kind == "open_variable"
            and ("interrogative", "content") in row.constraints
        )
        competing_binder = ContributionSlot.create(
            contribution_ref="contribution:competing-content-interrogative",
            kind="binder",
            source_unit_refs=query.source_unit_refs,
            target_ref=query.target_ref,
            target_kind=query.target_kind,
            input_ports=query.input_ports,
            output_ports=query.output_ports,
            constraints=query.constraints,
            provenance_refs=query.provenance_refs,
        )
        forged_context = ProposalContext.create(
            orientation_ref=context.orientation_ref,
            evidence_packet_ref=context.evidence_packet_ref,
            form_lattice_ref=context.form_lattice_ref,
            grounding_ref=context.grounding_ref,
            designation_slots=context.designation_slots,
            contribution_slots=(*context.contribution_slots, competing_binder),
            mode_slots=context.mode_slots,
            application_frames=context.application_frames,
            reference_slots=context.reference_slots,
            scope_slots=context.scope_slots,
            expression_link_slots=context.expression_link_slots,
            variable_slots=context.variable_slots,
            transition_slots=context.transition_slots,
            residual_evidence=context.residual_evidence,
            context_refs=context.context_refs,
            source_unit_refs=context.source_unit_refs,
            source_unit_spans=context.source_unit_spans,
            revision_pin=context.revision_pin,
        )
        actions = tuple(
            ProgramAction.create(
                action_index=action.action_index,
                action_type=action.action_type,
                arguments=(forged_context.context_ref,),
                source_unit_refs=action.source_unit_refs,
            )
            if action.action_type == "select_context"
            else action
            for action in program.actions
        )
        assignments = tuple(
            SourceAssignment.create(
                source_unit_ref=row.source_unit_ref,
                contribution_slot_ref=(
                    competing_binder.slot_ref
                    if row.source_unit_ref == query.source_unit_refs[0]
                    else row.contribution_slot_ref
                ),
                assignment_kind=row.assignment_kind,
                target_action_ref=row.target_action_ref,
                target_role_ref=row.target_role_ref,
                residual_kind=row.residual_kind,
                critical=row.critical,
            )
            for row in program.source_assignments
        )
        forged_program = SemanticSwitchProgram.create(
            orientation_ref=program.orientation_ref,
            proposal_context_ref=forged_context.context_ref,
            actions=actions,
            root_refs=program.root_refs,
            mode_slot_ref=program.mode_slot_ref,
            goal_refs=program.goal_refs,
            source_unit_refs=program.source_unit_refs,
            source_assignments=assignments,
            revision_pin=program.revision_pin,
        )

        assert ProposalContext.from_dict(forged_context.as_dict()) == forged_context
        assert SemanticSwitchProgram.from_dict(forged_program.as_dict()) == forged_program
        coverage = CoverageVerifier(RuntimeConfig.release()).verify(
            forged_context,
            forged_program,
        )
        compiled = compile_recursive(forged_program, forged_context)
        reconstructed = reconstruct_expected_expression(
            forged_program,
            forged_context,
        )
        assert (
            coverage.executable,
            not isinstance(compiled, CompilationFailure),
            reconstructed is not None,
        ) == (False, False, False)
        assert tuple(error.code for error in coverage.errors) == (
            "unresolved_designation_interrogative_pointer",
        )
    finally:
        runtime.stores.close()


def test_foundation_lexical_pack_preserves_all_predecessor_fields():
    # Same assertion as the frozen Task-2 whole-pack hash test. Reconstruct
    # only the explicitly reviewed metadata additions and retired define cue.
    pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
    assert "define" not in pack["query_projection"] and pack["abi_version"] == 7
    for word, kind in (("what", "content"), ("who", "person"), ("where", "location"), ("when", "time"), ("why", "reason"), ("which", "selection"), ("how", "manner")):
        assert pack["query_projection"][word].pop("interrogative") == kind
        assert pack["query_projection"][word] == {"kind": "query"}
    assert pack["query_projection"]["does"].pop("construction_role") == "lexical_query_auxiliary"
    assert pack["discourse"]["mean"].pop("construction_role") == "lexical_query_terminal"
    assert pack["linkers"].pop("in") == {"kind": "restriction_linker"}
    pack["query_projection"]["define"] = {"kind": "query"}
    assert FormResolver(pack, RuntimeConfig.release()).form_pack_hash == "sha256:32f5133c901afc05cc5345bc5766d00c97518b54025cad4ca0fb3707ad40b5ad"


def test_foundation_lexical_explicit_unknown_frame_preserves_literal_query_and_binder(tmp_path):
    # Same-assertion successor to the generic What-is fixture: explicit lexical
    # construction now provides the missing positive license, not copula alone.
    from cemm_authoritative_hybrid.proposal_context import UnresolvedDesignationFrame
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "exact-frame.db")
    try:
        source = "What does zorbulate mean?"
        _, context = runtime.orient("session:exact-frame", source)
        assert len(context.unresolved_designation_frames) == 1
        frame = context.unresolved_designation_frames[0]
        assert type(frame) is UnresolvedDesignationFrame and frame.label_type_ref == "label:lexical"
        literal = context.contribution(frame.literal_contribution_slot_ref)
        assert literal.kind == "literal" and literal.literal_value == "zorbulate"
        assert literal.source_unit_refs == frame.source_unit_refs == ("unit:4",)
        assert context.source_span(frame.source_unit_refs) == (source.index("zorbulate"), source.index("zorbulate") + len("zorbulate"))
        variables = context.variables_for_frame_role(frame.slot_ref, "role:target")
        assert len(variables) == 1 and variables[0].application_frame_ref == frame.slot_ref
        assert any(row.kind == "open_variable" and row.source_unit_refs == ("unit:0",) for row in context.contribution_slots)
        assert any(row.kind == "discourse" and row.source_unit_refs == ("unit:7",) for row in context.contribution_slots)
        binder = context.contribution(frame.query_binder_slot_ref)
        assert binder.kind == "binder" and binder.source_unit_refs == ("unit:2", "unit:6")
        assert variables[0].source_unit_refs == ("unit:0", *binder.source_unit_refs)
        assert all(context.residual_for_source(ref) is None for ref in ("unit:0", "unit:4", "unit:7"))
        assert runtime.orient("session:generic-frame", "What is zorbulate?")[1].unresolved_designation_frames == ()
    finally:
        runtime.stores.close()


def test_foundation_lexical_explicit_unknown_uses_unchanged_program_actions(tmp_path):
    # Same-assertion successor to the generic question derivation canary.
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "actions.db")
    try:
        _, context = runtime.orient("session:actions", "What does zorbulate mean?")
        proposal = runtime.proposal_model.propose(context)
        assert proposal.status == "candidates" and not proposal.truncated
        assert proposal.candidates
        verified = ExactProgramVerifier().verify_candidates(proposal, context)
        assert verified.selected_meaning.expression == _matrix_designation_query("zorbulate")
        for candidate in proposal.candidates:
            program = candidate.program
            assert program.as_dict()["abi_version"] == 2
            actions = {row.action_type for row in program.actions}
            assert actions == {"select_context", "select_mode", "instantiate_operator", "bind_role", "project_variable", "complete_program"}
            assert "select_designation" not in actions
        assert all(receipt.accepted for receipt in verified.candidate_receipts)
    finally:
        runtime.stores.close()


def test_foundation_lexical_explicit_unknown_preserves_response_lineage(tmp_path):
    # Same-assertion successor to the closure unknown-action canary. A missing
    # designation is unknown lookup evidence, never proof of meaninglessness.
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "response-lineage.db")
    try:
        result = runtime.process("session:response-lineage", "What does zorbulate mean?")
        assert result.orientation.mode is SemanticMode.QUERY
        meaning, response = result.verification.selected_meaning, result.response_meaning
        assert meaning.expression == _matrix_designation_query("zorbulate")
        assert tuple(binding.filler for app in response.response_expression.applications for binding in app.roles if binding.role_ref == "role:surface") == (LiteralValue("string", "zorbulate"),)
        assert response.verified_meaning_ref == meaning.verified_meaning_ref
        assert response.source_expression_ref == meaning.expression.expression_ref
        assert response.decision_ref == result.evaluation.decision.decision_ref
        assert result.evaluation.decision.source_refs
        assert set(result.evaluation.decision.source_refs) <= set(response.source_refs)
        assert response.discourse_action == "unknown" and response.bindings == ()
        assert result.evaluation.query_results[0].proof is None
        assert isinstance(result.effect_receipt, NoEffectReceipt) and runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_foundation_lexical_typed_query_pattern_preserves_repeated_role_constraint(linked_authority):
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        app = SemanticApplication("application:typed", "op:relation", "rel:likes",
            (RoleBinding("role:subject", BoundVariable("?person")), RoleBinding("role:object", GroundedReference("entity:alice"))),
            (RoleBinding("role:subject", GroundedReference("entity:bob")),))
        binder = VariableBinder("binder:person", "?person", app.application_ref)
        expression = SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(expression, project_expression(expression), _matrix_situation(stores))
        assert result.query_results[0].status is QueryStatus.UNKNOWN
        assert result.query_results[0].proof is None and result.query_results[0].bindings == ()
    finally:
        stores.close()


def _pending_dialogue(stores, suffix="one", **changes):
    values = dict(kind=ObligationKind.LEARNING_ANSWER, session_ref="session:pending",
        source_query_ref=f"query:{suffix}", expected_answer_contract_ref="contract:designation_answer:v2",
        created_turn_index=1, expires_turn_index=5, source_decision_ref=f"decision:{suffix}",
        completion_receipt_ref=None, revision_pin=stores.revision_pin())
    values.update(changes)
    return DialogueObligation.create(**values)


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_pending_dialogue_r3_writer_preserves_atomic_metadata(backend, tmp_path):
    # Persistence seam only: this does not authorize or prove alias acquisition.
    stores = _restart_stores(backend, tmp_path)
    try:
        stores.r3_effect_journal_begin(idempotency_key="key:learning", intent_ref="intent:learning",
            decision_ref="decision:learning", request_payload={"session_ref": "session:pending", "turn_index": 1},
            expected_effect_revision=0)
        row = _pending_dialogue(stores)
        before = (stores.revision_pin(), stores.obligations.revision, stores.r3_effect_journal_get("key:learning"))
        commit = lambda payload: stores.r3_commit_learning_outcome(session_ref=row.session_ref,
            obligation_ref=row.obligation_ref, obligation_payload=payload, idempotency_key="key:learning",
            intent_ref="intent:learning", decision_ref="decision:learning", receipt_payload={"receipt_ref": "receipt:learning"},
            expected_revision_pin=before[0])
        with pytest.raises(TypeError):
            commit({**row.as_dict(), "not_json": {1}})
        assert (stores.revision_pin(), stores.obligations.revision, stores.r3_effect_journal_get("key:learning")) == before
        assert stores.sessions.get(row.session_ref) is None
        assert stores.obligations.keyed_row(row.obligation_ref) is None
        commit(row.as_dict())
        assert stores.obligations.revision == 1
        assert stores.pending_dialogue_obligations(row.session_ref, (row.obligation_ref,), maximum=1, turn_index=2) == (row,)
        assert stores.r3_obligation_snapshot(row.session_ref, maximum=1)["obligation_refs"] == [row.obligation_ref]
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_pending_dialogue_failed_completion_is_atomic(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _pending_dialogue(stores)
        stores.obligations.commit(row.obligation_ref, row.session_ref, row.as_dict(), expected_revision=0)
        before = stores.obligations.keyed_row(row.obligation_ref)
        with pytest.raises(TypeError):
            stores.obligations.complete(row.obligation_ref, "completed:invalid", row.session_ref,
                {"completion_receipt_ref": "receipt:done", "not_json": {1}}, expected_revision=1)
        assert stores.obligations.revision == 1
        assert stores.obligations.keyed_row(row.obligation_ref) == before
        assert stores.obligations.get("completed:invalid") is None
    finally:
        stores.close()


def test_foundation_pending_dialogue_codec_is_exact():
    stores = memory_stores()
    try:
        for kind in ObligationKind:
            row = _pending_dialogue(stores, kind=kind)
            assert DialogueObligation.from_dict(row.as_dict()) == row
        original = _pending_dialogue(stores).as_dict()
        class RefSubclass(str):
            pass
        for patch in ({"abi_version": True}, {"abi_version": 1.0}, {"abi_version": 2},
                      {"kind": "unknown"}, {"created_turn_index": True},
                      {"expires_turn_index": 1}, {"obligation_ref": "forged"},
                      {"resolved": False}, {"revision_pin": {}}, {"obligation_ref": RefSubclass(original["obligation_ref"])}):
            with pytest.raises((TypeError, ValueError)):
                DialogueObligation.from_dict({**original, **patch})
        missing = dict(original)
        del missing["source_query_ref"]
        with pytest.raises(ValueError):
            DialogueObligation.from_dict(missing)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite", "sqlite-reopen"), ids=("memory", "sqlite", "sqlite-reopen"))
def test_foundation_pending_dialogue_reads_exact_keys_and_rejects_invalid_lifecycle(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        first = _pending_dialogue(stores)
        second = _pending_dialogue(stores, "two", kind=ObligationKind.CLARIFICATION)
        foreign = _pending_dialogue(stores, "foreign", session_ref="session:foreign")
        for row in (first, second, foreign):
            stores.obligations.commit(row.obligation_ref, row.session_ref, row.as_dict(), expected_revision=stores.obligations.revision)
        stores = _restart_reopen(stores, backend, tmp_path)
        before = (stores.revision_pin(), stores.obligations.revision)
        read = lambda refs, turn=2: stores.pending_dialogue_obligations("session:pending", refs, maximum=2, turn_index=turn)
        assert read((second.obligation_ref, first.obligation_ref)) == (second, first)
        assert read(()) == ()
        for refs in ((first.obligation_ref, "missing"), (foreign.obligation_ref,), (first.obligation_ref,) * 2,
                     (first.obligation_ref, second.obligation_ref, foreign.obligation_ref), [first.obligation_ref]):
            with pytest.raises((TypeError, ValueError)):
                read(refs)
        for turn in (0, 5):
            with pytest.raises(ValueError):
                read((first.obligation_ref,), turn)
        assert (stores.revision_pin(), stores.obligations.revision) == before
        completed = _pending_dialogue(stores, completion_receipt_ref="receipt:done", revision_pin=first.revision_pin)
        stores.obligations.complete(first.obligation_ref, completed.obligation_ref, first.session_ref, completed.as_dict(), expected_revision=stores.obligations.revision)
        for ref in (first.obligation_ref, completed.obligation_ref):
            with pytest.raises(ValueError):
                read((ref,))
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_pending_dialogue_authenticates_payload_and_detaches_writes(backend, tmp_path):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _pending_dialogue(stores)
        payload = row.as_dict()
        stores.obligations.commit(row.obligation_ref, row.session_ref, payload, expected_revision=0)
        payload["revision_pin"]["world_revision"] = 999
        read = lambda: stores.pending_dialogue_obligations(row.session_ref, (row.obligation_ref,), maximum=1, turn_index=2)
        assert read() == (row,)
        if backend == "memory":
            stores.obligations._obligations[row.obligation_ref]["source_query_ref"] = "query:tampered"
        else:
            stores._backend._conn.execute("UPDATE obligations SET payload_hash='tampered' WHERE obligation_ref=?", (row.obligation_ref,))
            stores._backend._conn.commit()
        before = (stores.revision_pin(), stores.obligations.revision)
        with pytest.raises(ValueError, match="hash"):
            read()
        assert (stores.revision_pin(), stores.obligations.revision) == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_pending_dialogue_rejects_forged_envelopes_and_future_pins(backend, tmp_path):
    from cemm_authoritative_hybrid.persistence import _payload_hash
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _pending_dialogue(stores)
        stores.obligations.commit(row.obligation_ref, row.session_ref, row.as_dict(), expected_revision=0)
        original = stores.obligations.keyed_row(row.obligation_ref)
        key, session, payload, digest, revision, resolved = original
        variants = [
            (key, "session:forged", payload, digest, revision, resolved),
            (key, session, payload, digest, 0, resolved),
            (key, session, payload, digest, 2, resolved),
            (key, session, payload, digest, revision, 1),
        ]
        for change in ({"resolved": 0}, {"extra": "field"}, {"obligation_ref": "forged"}):
            altered = {**payload, **change}
            variants.append((key, session, altered, _payload_hash(altered), revision, resolved))
        for field in ("authority_generation", "world_revision", "session_revision", "episode_revision", "effect_revision"):
            pin = row.revision_pin.as_dict()
            pin[field] = "authority:foreign" if field == "authority_generation" else 99
            other = _pending_dialogue(stores, revision_pin=RevisionPin.from_dict(pin))
            data = {**other.as_dict(), "resolved": False}
            stores.obligations.commit(other.obligation_ref, session, data, expected_revision=stores.obligations.revision)
            with pytest.raises(ValueError, match="generation|revision pin"):
                stores.pending_dialogue_obligations(session, (other.obligation_ref,), maximum=1, turn_index=2)
        # Use a definitely future commit revision after the additional writes.
        variants[2] = (key, session, payload, digest, stores.obligations.revision + 1, resolved)
        for _, db_session, data, data_hash, commit_revision, status in variants:
            if backend == "memory":
                stores.obligations._obligations[key] = data
                stores.obligations._row_metadata[key] = (db_session, data_hash, commit_revision, status)
            else:
                stores._backend._conn.execute(
                    "UPDATE obligations SET session_ref=?, payload_json=?, payload_hash=?, revision=?, resolved=? WHERE obligation_ref=?",
                    (db_session, json.dumps(data), data_hash, commit_revision, status, key))
                stores._backend._conn.commit()
            before = (stores.revision_pin(), stores.obligations.revision)
            with pytest.raises((TypeError, ValueError)):
                stores.pending_dialogue_obligations(session, (key,), maximum=1, turn_index=2)
            assert (stores.revision_pin(), stores.obligations.revision) == before
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_foundation_pending_dialogue_work_is_key_bounded(backend, tmp_path, monkeypatch):
    stores = _restart_stores(backend, tmp_path)
    try:
        row = _pending_dialogue(stores)
        stores.obligations.commit(row.obligation_ref, row.session_ref, row.as_dict(), expected_revision=0)
        for index in range(128):
            stores.obligations.commit(f"unrelated:{index}", "session:elsewhere", {"not": "a dialogue payload"}, expected_revision=stores.obligations.revision)
        keyed = stores.obligations.keyed_row
        visited = []
        def counted(ref):
            visited.append(ref)
            return keyed(ref)
        monkeypatch.setattr(stores.obligations, "keyed_row", counted)
        if backend == "memory":
            class NoEnumeration(dict):
                def __iter__(self): raise AssertionError("whole-store enumeration")
                def items(self): raise AssertionError("whole-store enumeration")
                def values(self): raise AssertionError("whole-store enumeration")
            stores.obligations._obligations = NoEnumeration(stores.obligations._obligations)
        else:
            plan = stores._backend._conn.execute("EXPLAIN QUERY PLAN SELECT obligation_ref, session_ref, payload_json, payload_hash, revision, resolved FROM obligations WHERE obligation_ref=?", (row.obligation_ref,)).fetchall()
            assert all("SCAN" not in str(part).upper() for part in plan)
        assert stores.pending_dialogue_obligations(row.session_ref, (row.obligation_ref,), maximum=1, turn_index=2) == (row,)
        assert visited == [row.obligation_ref]
        for refs, maximum, turn in (((row.obligation_ref,) * 2, 1, 2), ((row.obligation_ref,), True, 2), ((row.obligation_ref,), 1, True)):
            with pytest.raises((TypeError, ValueError)):
                stores.pending_dialogue_obligations(row.session_ref, refs, maximum=maximum, turn_index=turn)
        assert visited == [row.obligation_ref]
    finally:
        stores.close()
