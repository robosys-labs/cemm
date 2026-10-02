"""Independent declarative relation roles over actual referent kinds."""
from dataclasses import fields
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.authority import DesignationFact
from cemm_authoritative_hybrid.expressions import GroundedReference, ApplicationFiller, RoleBinding, SemanticApplication, SemanticExpression, ScopeOperator
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier
from tests.test_foundation_semantics import _static_composition_context
from tests.test_foundation_relation_queries import _rehash_derivation, _slot_with
from cemm_authoritative_hybrid.coverage import CoverageVerifier
from cemm_authoritative_hybrid.expressions import CompilationFailure, SemanticExpressionCompiler
from cemm_authoritative_hybrid.programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from cemm_authoritative_hybrid.verifier import _replay_program
from cemm_authoritative_hybrid.verifier_reconstruction import reconstruct_expected_expression
from cemm_authoritative_hybrid.role_schemas import ReviewedRoleSchemaIndex
from cemm_authoritative_hybrid.config import RuntimeConfig

ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_mixed_referents.py::test_named_negative_relation_preserves_reviewed_role_projection[negative-forward]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-named-negative-relation-preserves-reviewed-role-projection-negative-forward",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "910d966180b0dcaa36b301f7a5d216870ab7b584ebdc2aaca5d976803443f2d7"
    },
    "tests/test_foundation_mixed_referents.py::test_named_negative_relation_preserves_reviewed_role_projection[negative-reverse]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-named-negative-relation-preserves-reviewed-role-projection-negative-reverse",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "910d966180b0dcaa36b301f7a5d216870ab7b584ebdc2aaca5d976803443f2d7"
    },
    "tests/test_foundation_mixed_referents.py::test_named_embedded_relation_preserves_reviewed_role_projection": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-named-embedded-relation-preserves-reviewed-role-projection",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "522333feb1708a6b3274af36115dfdac1657d9011537b8eb0197c7224f528a33"
    },
    "tests/test_foundation_mixed_referents.py::test_unseen_alias_negative_named_roles_preserve_scope_and_order[en-negative]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unseen-alias-negative-named-roles-preserve-scope-and-order-en-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "81d0361efdbd118a29f0cee6176c7e68f20426a31df64323768ccfa350c35954"
    },
    "tests/test_foundation_mixed_referents.py::test_unseen_alias_negative_named_roles_preserve_scope_and_order[es-negative]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unseen-alias-negative-named-roles-preserve-scope-and-order-es-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "81d0361efdbd118a29f0cee6176c7e68f20426a31df64323768ccfa350c35954"
    },
    "tests/test_foundation_mixed_referents.py::test_capability_relation_is_not_reinterpreted_as_declarative_relation": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-capability-relation-is-not-reinterpreted-as-declarative-relation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "e829c754a270293f7a12b013523e081baf14b67ea15b3386430aeae13fb8bf55"
    },
    "tests/test_foundation_mixed_referents.py::test_activation_rejects_mutable_referent_kind_collection_subclass": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-activation-rejects-mutable-referent-kind-collection-subclass",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "77fcc02a09d5ebc82a3de1451eb40246f3d9c0eb2aa5808c2d25afcda7847ce9"
    },
    "tests/test_foundation_mixed_referents.py::test_public_relation_preserves_actual_referent_roles[named-you]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-public-relation-preserves-actual-referent-roles-named-you",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "cbfa16543de7c5f19e04973432f1eb01e5064ff3495a540837e638e25d577255"
    },
    "tests/test_foundation_mixed_referents.py::test_public_relation_preserves_actual_referent_roles[named-me]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-public-relation-preserves-actual-referent-roles-named-me",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "cbfa16543de7c5f19e04973432f1eb01e5064ff3495a540837e638e25d577255"
    },
    "tests/test_foundation_mixed_referents.py::test_public_relation_preserves_actual_referent_roles[you-named]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-public-relation-preserves-actual-referent-roles-you-named",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "cbfa16543de7c5f19e04973432f1eb01e5064ff3495a540837e638e25d577255"
    },
    "tests/test_foundation_mixed_referents.py::test_public_relation_preserves_actual_referent_roles[speaker-named]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-public-relation-preserves-actual-referent-roles-speaker-named",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "cbfa16543de7c5f19e04973432f1eb01e5064ff3495a540837e638e25d577255"
    },
    "tests/test_foundation_mixed_referents.py::test_public_relation_preserves_actual_referent_roles[you-me]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-public-relation-preserves-actual-referent-roles-you-me",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "cbfa16543de7c5f19e04973432f1eb01e5064ff3495a540837e638e25d577255"
    },
    "tests/test_foundation_mixed_referents.py::test_public_relation_preserves_actual_referent_roles[speaker-you]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-public-relation-preserves-actual-referent-roles-speaker-you",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "cbfa16543de7c5f19e04973432f1eb01e5064ff3495a540837e638e25d577255"
    },
    "tests/test_foundation_mixed_referents.py::test_public_relation_preserves_actual_referent_roles[named-named]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-public-relation-preserves-actual-referent-roles-named-named",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "cbfa16543de7c5f19e04973432f1eb01e5064ff3495a540837e638e25d577255"
    },
    "tests/test_foundation_mixed_referents.py::test_activation_rejects_unreviewed_referent_selectors[concept-not-referent]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-activation-rejects-unreviewed-referent-selectors-concept-not-referent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "8b8f6e08808cb532aa385c5be94f6ce58d6d97d70105bd02432195a303d38871"
    },
    "tests/test_foundation_mixed_referents.py::test_activation_rejects_unreviewed_referent_selectors[unreviewed-kind-widening]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-activation-rejects-unreviewed-referent-selectors-unreviewed-kind-widening",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "8b8f6e08808cb532aa385c5be94f6ce58d6d97d70105bd02432195a303d38871"
    },
    "tests/test_foundation_mixed_referents.py::test_activation_rejects_unreviewed_referent_selectors[changed-kind-order]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-activation-rejects-unreviewed-referent-selectors-changed-kind-order",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "8b8f6e08808cb532aa385c5be94f6ce58d6d97d70105bd02432195a303d38871"
    },
    "tests/test_foundation_mixed_referents.py::test_activation_rejects_unreviewed_referent_selectors[foreign-role]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-activation-rejects-unreviewed-referent-selectors-foreign-role",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "8b8f6e08808cb532aa385c5be94f6ce58d6d97d70105bd02432195a303d38871"
    },
    "tests/test_foundation_mixed_referents.py::test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation[object-other-clause]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unlicensed-mixed-clause-never-settles-reversed-or-unscoped-relation-object-other-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "9fdb4ce244d4189df6a91275d437a61e5df1d22637e97e01d6d6f2ea1e4c0ba2"
    },
    "tests/test_foundation_mixed_referents.py::test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation[subject-other-clause]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unlicensed-mixed-clause-never-settles-reversed-or-unscoped-relation-subject-other-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "9fdb4ce244d4189df6a91275d437a61e5df1d22637e97e01d6d6f2ea1e4c0ba2"
    },
    "tests/test_foundation_mixed_referents.py::test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation[extra-referent]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unlicensed-mixed-clause-never-settles-reversed-or-unscoped-relation-extra-referent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "9fdb4ce244d4189df6a91275d437a61e5df1d22637e97e01d6d6f2ea1e4c0ba2"
    },
    "tests/test_foundation_mixed_referents.py::test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation[unlicensed-punctuation]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unlicensed-mixed-clause-never-settles-reversed-or-unscoped-relation-unlicensed-punctuation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "9fdb4ce244d4189df6a91275d437a61e5df1d22637e97e01d6d6f2ea1e4c0ba2"
    },
    "tests/test_foundation_mixed_referents.py::test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation[unresolved-deixis]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unlicensed-mixed-clause-never-settles-reversed-or-unscoped-relation-unresolved-deixis",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "9fdb4ce244d4189df6a91275d437a61e5df1d22637e97e01d6d6f2ea1e4c0ba2"
    },
    "tests/test_foundation_mixed_referents.py::test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation[unlicensed-embedded]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unlicensed-mixed-clause-never-settles-reversed-or-unscoped-relation-unlicensed-embedded",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "9fdb4ce244d4189df6a91275d437a61e5df1d22637e97e01d6d6f2ea1e4c0ba2"
    },
    "tests/test_foundation_mixed_referents.py::test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation[unlicensed-condition]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-unlicensed-mixed-clause-never-settles-reversed-or-unscoped-relation-unlicensed-condition",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "9fdb4ce244d4189df6a91275d437a61e5df1d22637e97e01d6d6f2ea1e4c0ba2"
    },
    "tests/test_foundation_mixed_referents.py::test_two_sentence_roles_remain_source_local": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-two-sentence-roles-remain-source-local",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "daff8a21fc4aa5eea43f7f9336dac5ce54fe4eb60f6cc719f0efd95acdd57348"
    },
    "tests/test_foundation_mixed_referents.py::test_authenticated_alias_restart_inherits_mixed_referent_roles": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-authenticated-alias-restart-inherits-mixed-referent-roles",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "a4c99c0ebcd30d93c4db1b6ecde9d120156b18916bc4c12144709cbeb16be996"
    },
    "tests/test_foundation_mixed_referents.py::test_rehashed_reversed_roles_fail_independent_exact_sinks[named-you]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-rehashed-reversed-roles-fail-independent-exact-sinks-named-you",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "0eace2b92a2232878d5d05c664f34ccf70ad7aacf9bcfdcc0c787884137810a2"
    },
    "tests/test_foundation_mixed_referents.py::test_rehashed_reversed_roles_fail_independent_exact_sinks[named-me]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-rehashed-reversed-roles-fail-independent-exact-sinks-named-me",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "0eace2b92a2232878d5d05c664f34ccf70ad7aacf9bcfdcc0c787884137810a2"
    },
    "tests/test_foundation_mixed_referents.py::test_rehashed_reversed_roles_fail_independent_exact_sinks[you-named]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-rehashed-reversed-roles-fail-independent-exact-sinks-you-named",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "0eace2b92a2232878d5d05c664f34ccf70ad7aacf9bcfdcc0c787884137810a2"
    },
    "tests/test_foundation_mixed_referents.py::test_rehashed_reversed_roles_fail_independent_exact_sinks[two-participants]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-rehashed-reversed-roles-fail-independent-exact-sinks-two-participants",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "0eace2b92a2232878d5d05c664f34ccf70ad7aacf9bcfdcc0c787884137810a2"
    },
    "tests/test_foundation_mixed_referents.py::test_reviewed_unseen_alias_preserves_mixed_roles_without_pack_regeneration[en-object]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-reviewed-unseen-alias-preserves-mixed-roles-without-pack-regeneration-en-object",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "628abd86f77e3f75e826730c70b15d78a4682244942dfa133e3a500819895d84"
    },
    "tests/test_foundation_mixed_referents.py::test_reviewed_unseen_alias_preserves_mixed_roles_without_pack_regeneration[en-subject]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-reviewed-unseen-alias-preserves-mixed-roles-without-pack-regeneration-en-subject",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "628abd86f77e3f75e826730c70b15d78a4682244942dfa133e3a500819895d84"
    },
    "tests/test_foundation_mixed_referents.py::test_reviewed_unseen_alias_preserves_mixed_roles_without_pack_regeneration[es-object]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-reviewed-unseen-alias-preserves-mixed-roles-without-pack-regeneration-es-object",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "628abd86f77e3f75e826730c70b15d78a4682244942dfa133e3a500819895d84"
    },
    "tests/test_foundation_mixed_referents.py::test_reviewed_unseen_alias_preserves_mixed_roles_without_pack_regeneration[es-subject]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:mixed-referents-reviewed-unseen-alias-preserves-mixed-roles-without-pack-regeneration-es-subject",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "form-context",
        "source_ast_sha256": "628abd86f77e3f75e826730c70b15d78a4682244942dfa133e3a500819895d84"
    }
}


def _expected(subject, object_):
    app = SemanticApplication("candidate:independent", "op:relation", "rel:likes", (
        RoleBinding("role:subject", GroundedReference(subject)),
        RoleBinding("role:object", GroundedReference(object_)),
    ))
    return SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))


def test_capability_relation_is_not_reinterpreted_as_declarative_relation(tmp_path):
    from cemm_authoritative_hybrid.r3_cognition import QueryStatus
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "capability.db")
    try:
        result = runtime.process("session:capability", "Can you learn aliases?")
        assert result.verification.selected_meaning is not None
        assert result.evaluation.query_results[0].status is QueryStatus.SUPPORTED
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface,subject,object_", (
    ("Alice not likes Bob", "entity:alice", "entity:bob"),
    ("Bob not likes Alice", "entity:bob", "entity:alice"),
), ids=("negative-forward", "negative-reverse"))
def test_named_negative_relation_preserves_reviewed_role_projection(surface, subject, object_, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "negative.db")
    app = _expected(subject, object_).applications[0]
    scope = ScopeOperator("scope:independent", "scope:polarity", "scope_value:polarity:negative", app.application_ref)
    expected = SemanticExpression.create(applications=(app,), scope_operators=(scope,), root_refs=(scope.scope_ref,))
    try:
        result = runtime.process("session:negative", surface)
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == expected
        assert result.verification.selected_meaning.expression != _expected(subject, object_)
        assert result.verification.selected_meaning.expression != SemanticExpression.create(
            applications=_expected(object_, subject).applications, scope_operators=(scope,), root_refs=(scope.scope_ref,))
        assert not result.proposal.truncated and result.proposal.explored_states <= 7
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_named_embedded_relation_preserves_reviewed_role_projection(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "named-embedded.db")
    child = _expected("entity:bob", "entity:alice").applications[0]
    report = SemanticApplication("candidate:report", "op:event", "event:say", (
        RoleBinding("role:actor", GroundedReference("entity:mary")),
        RoleBinding("role:content", ApplicationFiller(child.application_ref)),
    ))
    expected = SemanticExpression.create(applications=(child, report), root_refs=(report.application_ref,))
    try:
        result = runtime.process("session:embedded", "Mary said Bob likes Alice")
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == expected
        assert not result.proposal.truncated
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface,subject,object_", (
    ("Bob likes you", "entity:bob", "participant:system"),
    ("Alice likes me", "entity:alice", "participant:user"),
    ("you likes Bob", "participant:system", "entity:bob"),
    ("I likes Alice", "participant:user", "entity:alice"),
    ("you likes me", "participant:system", "participant:user"),
    ("I likes you", "participant:user", "participant:system"),
    ("Bob likes Alice", "entity:bob", "entity:alice"),
), ids=("named-you", "named-me", "you-named", "speaker-named", "you-me", "speaker-you", "named-named"))
def test_public_relation_preserves_actual_referent_roles(surface, subject, object_, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "roles.db")
    try:
        result = runtime.process("session:mixed", surface)
        assert result.verification.selected_meaning is not None
        assert result.verification.selected_meaning.expression == _expected(subject, object_)
        assert not result.proposal.truncated and result.proposal.explored_states <= 12
        assert runtime.stores.world.revision == 0
        assert result.realization_receipt is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("kinds,role", (
    (["entity", "concept"], "role:subject"),
    (["entity", "participant", "concept"], "role:object"),
    (["participant", "entity"], "role:subject"),
    (["entity", "participant"], "role:actor"),
), ids=("concept-not-referent", "unreviewed-kind-widening", "changed-kind-order", "foreign-role"))
def test_activation_rejects_unreviewed_referent_selectors(kinds, role, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "activation.db")
    try:
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_bytes())
        selector = pack["application_role_orders"]["relation_subject_predicate_object"]["evidence_order"][0]
        selector.update(target_kinds=kinds, role=role)
        with pytest.raises(ValueError):
            ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, RuntimeConfig.release())
    finally:
        runtime.stores.close()


def test_activation_rejects_mutable_referent_kind_collection_subclass(tmp_path):
    class ForeignKinds(list):
        pass
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "foreign-kinds.db")
    try:
        pack = json.loads((ROOT / "data/languages/en/forms.json").read_bytes())
        pack["application_role_orders"]["relation_subject_predicate_object"]["evidence_order"][0]["target_kinds"] = ForeignKinds(("entity", "participant"))
        with pytest.raises(ValueError):
            ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, RuntimeConfig.release())
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", (
    "Bob likes. you", "Bob. likes you", "Bob likes you Alice", "Bob likes you, Alice", "Bob likes that",
    "Mary said Bob likes you", "if Bob likes you then proceed",
), ids=("object-other-clause", "subject-other-clause", "extra-referent", "unlicensed-punctuation", "unresolved-deixis", "unlicensed-embedded", "unlicensed-condition"))
def test_unlicensed_mixed_clause_never_settles_reversed_or_unscoped_relation(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "boundary.db")
    try:
        result = runtime.process("session:boundary", surface)
        assert result.verification.selected_meaning is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_two_sentence_roles_remain_source_local(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "two.db")
    try:
        result = runtime.process("session:two", "Bob likes you. I likes Alice.")
        assert result.verification.selected_meaning is not None
        expression = result.verification.selected_meaning.expression
        assert len(expression.root_refs) == len(expression.applications) == 2
        assert {tuple((r.role_ref, r.filler.target_ref) for r in a.roles) for a in expression.applications} == {
            tuple((r.role_ref, r.filler.target_ref) for r in _expected("entity:bob", "participant:system").applications[0].roles),
            tuple((r.role_ref, r.filler.target_ref) for r in _expected("participant:user", "entity:alice").applications[0].roles),
        }
        assert not result.proposal.truncated
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_authenticated_alias_restart_inherits_mixed_referent_roles(tmp_path, monkeypatch):
    from tests.test_foundation_alias_publication import _publication, _signed
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    before = (ROOT / "data/languages/en/forms.json").read_bytes()
    try:
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        assert len(receipt.committed_fact_refs) == 1
        revision = runtime.stores.world.revision
    finally:
        runtime.stores.close()
    reopened = load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        for surface, subject, object_ in (("Bob velnora you", "entity:bob", "participant:system"),
            ("you velnora Bob", "participant:system", "entity:bob"), ("I velnora you", "participant:user", "participant:system")):
            result = reopened.process("session:alias-restart", surface)
            assert result.verification.selected_meaning.expression == _expected(subject, object_)
            assert not result.proposal.truncated
        assert reopened.stores.world.revision == revision
        assert (ROOT / "data/languages/en/forms.json").read_bytes() == before
    finally:
        reopened.stores.close()


@pytest.mark.parametrize("surface", ("Bob likes you", "Alice likes me", "you likes Bob", "I likes you"),
    ids=("named-you", "named-me", "you-named", "two-participants"))
def test_rehashed_reversed_roles_fail_independent_exact_sinks(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "tamper.db")
    try:
        _, context = runtime.orient("session:tamper", surface)
        proposal = runtime.proposal_model.propose(context)
        assert proposal.candidates
        program = proposal.candidates[0].program
        replacements = {r.slot_ref: _slot_with(r, compatible_roles=("role:subject", "role:object"))
            for r in context.reference_slots if r.source_unit_refs}
        replacements.update({c.slot_ref: _slot_with(c, output_ports=("role:subject", "role:object"))
            for c in context.contribution_slots if c.kind == "reference"})
        forged, program = _rehash_derivation(context, program, replacements)
        swap = {"role:subject": "role:object", "role:object": "role:subject"}
        pointers = {}
        actions = []
        for action in program.actions:
            arguments = action.arguments
            if action.action_type in {"bind_reference", "bind_role"}:
                arguments = (arguments[0], swap.get(arguments[1], arguments[1]), *arguments[2:])
            changed = ProgramAction.create(action_index=action.action_index, action_type=action.action_type,
                arguments=arguments, source_unit_refs=action.source_unit_refs)
            pointers[action.action_ref] = changed.action_ref
            actions.append(changed)
        assignments = tuple(SourceAssignment.create(**{f.name: (pointers.get(getattr(a, f.name), getattr(a, f.name))
            if f.name == "target_action_ref" else swap.get(a.target_role_ref, a.target_role_ref)
            if f.name == "target_role_ref" else getattr(a, f.name)) for f in fields(a) if f.name != "assignment_ref"})
            for a in program.source_assignments)
        values = {f.name: getattr(program, f.name) for f in fields(program) if f.name != "program_ref"}
        program = SemanticSwitchProgram.create(**{**values, "actions": tuple(actions), "source_assignments": assignments})
        index = runtime._owners["verification"].role_schema_index
        coverage = CoverageVerifier(role_schema_index=index).verify(forged, program)
        assert not coverage.executable
        assert any(e.code == "relation_declarative_role_correspondence" for e in coverage.errors)
        compiled = SemanticExpressionCompiler(role_schema_index=index).compile(program, forged)
        assert isinstance(compiled, CompilationFailure)
        assert reconstruct_expected_expression(program, forged, role_schema_index=index) is None
        assert any(e.code == "relation_declarative_role_correspondence" for e in _replay_program(program, forged, role_schema_index=index))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,surface,subject,object_", (
    ("en", "Bob velnora you", "entity:bob", "participant:system"),
    ("en", "I velnora Alice", "participant:user", "entity:alice"),
    ("es", "Bob velnora t\u00fa", "entity:bob", "participant:system"),
    ("es", "yo velnora Alice", "participant:user", "entity:alice"),
), ids=("en-object", "en-subject", "es-object", "es-subject"))
def test_reviewed_unseen_alias_preserves_mixed_roles_without_pack_regeneration(language, surface, subject, object_, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "static.db")
    pack_path = ROOT / "data/languages" / language / "forms.json"
    before = pack_path.read_bytes()
    facts = tuple(DesignationFact.create(surface=s, target_ref=t, language=language) for s, t in (
        ("Bob", "entity:bob"), ("Alice", "entity:alice"), ("velnora", "rel:likes")))
    try:
        builder, context = _static_composition_context(runtime.authority, runtime.stores, json.loads(before), surface, facts=facts)
        proposal = runtime.proposal_model.propose(context)
        result = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
        assert result.selected_meaning is not None
        assert result.selected_meaning.expression == _expected(subject, object_)
        assert not proposal.truncated and proposal.explored_states <= 12
        assert pack_path.read_bytes() == before
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,surface", (
    ("en", "Alice not velnora Bob"), ("es", "Alice no velnora Bob"),
), ids=("en-negative", "es-negative"))
def test_unseen_alias_negative_named_roles_preserve_scope_and_order(language, surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "negative-alias.db")
    pack_path = ROOT / "data/languages" / language / "forms.json"
    before = pack_path.read_bytes()
    facts = tuple(DesignationFact.create(surface=s, target_ref=t, language=language) for s, t in (
        ("Bob", "entity:bob"), ("Alice", "entity:alice"), ("velnora", "rel:likes")))
    app = _expected("entity:alice", "entity:bob").applications[0]
    scope = ScopeOperator("scope:independent", "scope:polarity", "scope_value:polarity:negative", app.application_ref)
    expected = SemanticExpression.create(applications=(app,), scope_operators=(scope,), root_refs=(scope.scope_ref,))
    try:
        builder, context = _static_composition_context(runtime.authority, runtime.stores, json.loads(before), surface, facts=facts)
        proposal = runtime.proposal_model.propose(context)
        result = ExactProgramVerifier(role_schema_index=builder.role_schema_index).verify_candidates(proposal, context)
        assert result.selected_meaning is not None
        assert result.selected_meaning.expression == expected
        assert not proposal.truncated and proposal.explored_states <= 7
        assert pack_path.read_bytes() == before
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()
