"""Reviewed event lowering preserves source meaning and never publishes aliases."""
from dataclasses import fields, replace
import inspect
import json
import shutil

import pytest

from cemm_authoritative_hybrid import r3_learning
from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import DecisionAction, DecisionStatus
from cemm_authoritative_hybrid.expressions import (
    GroundedReference, LiteralValue, RoleBinding, SemanticApplication,
    SemanticExpression, ScopeOperator, UnresolvedValue, UnresolvedFiller,
)
from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
from cemm_authoritative_hybrid.r3_artifacts import LearningDraft
from cemm_authoritative_hybrid.r3_effects import R3EffectGateway
from cemm_authoritative_hybrid.r3_learning import LearningCoordinator, LearningPlan
from cemm_authoritative_hybrid.situation import SituationContext
from tests.test_foundation_continuation_binding import ROOT, _setup, _answer
from tests.test_foundation_semantics import _matrix_meaning, _matrix_expression
from tests.test_foundation_alias_authority import _owners, _manifest


def _situation(source, **changes):
    values = {field.name: getattr(source, field.name) for field in fields(source)
              if field.name not in {"abi_version", "situation_ref"}}
    return SituationContext.create(**{**values, **changes})


def _event_answer(runtime, source, *, surface="velnora", target="rel:likes", **changes):
    _, situation = _answer(runtime, source, surface=surface)
    situation = _situation(situation, actor_ref=situation.addressee_ref, **changes)
    app = SemanticApplication("app:learning", "op:event", "event:learn_alias", (
        RoleBinding("role:actor", GroundedReference(situation.addressee_ref)),
        RoleBinding("role:surface", LiteralValue("string", surface)),
        RoleBinding("role:target", GroundedReference(target)),
    ))
    expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
    return _matrix_meaning(expression, runtime.stores.revision_pin()), situation


def _lower(authority, expression, situation):
    assert hasattr(r3_learning, "lower_designation_learning"), "reviewed pure learning lowerer is missing"
    return r3_learning.lower_designation_learning(authority, expression, situation)


@pytest.mark.parametrize("surface", ["learn velnora means likes", "learn that velnora means likes"], ids=["event", "embedded-designation"])
def test_public_learning_event_materializes_linked_plan_before_disabled_effect(tmp_path, monkeypatch, surface):
    runtime, query_cycle, pending = _setup(tmp_path)
    captured = {}

    class ReachedEffect(Exception):
        pass

    def inspect_effect(self, evaluation, meaning, situation, **kwargs):
        captured.update(evaluation=evaluation, meaning=meaning, situation=situation, **kwargs)
        raise ReachedEffect

    monkeypatch.setattr(R3EffectGateway, "execute", inspect_effect)
    before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
    try:
        with pytest.raises(ReachedEffect):
            runtime.process("session:continuation", surface)
        evaluation, meaning, situation = (captured[key] for key in ("evaluation", "meaning", "situation"))
        assert evaluation.decision.action is DecisionAction.CREATE_LEARNING_OBLIGATION
        expected, _ = _event_answer(runtime, query_cycle.evaluation.situation)
        assert meaning.expression == expected.expression == evaluation.expression
        assert evaluation.decision.expression_ref == meaning.expression.expression_ref
        plan = captured["learning_plan"]
        contract = runtime.authority.learning_contract_for_source("op:event", "event:learn_alias")
        assert plan is not None
        for name in ("contract_ref", "capability_ref", "permission_ref", "commit_operator_ref", "goal_ref", "answer_contract_ref"):
            assert getattr(plan, name) == getattr(contract, name)
        assert plan.source_query_ref == pending.source_query_ref
        assert plan.expires_at_turn == pending.expires_turn_index
        assert plan.surface_literal == "velnora" and plan.target_ref == "rel:likes"
        assert situation.adapter_refs == ()  # Internal lowering grants no external adapter availability.
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


def test_pure_lowering_preserves_actor_source_and_canonical_designation(tmp_path):
    runtime, source, pending = _setup(tmp_path)
    try:
        meaning, situation = _event_answer(runtime, source.evaluation.situation)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        lowered = _lower(runtime.authority, meaning.expression, situation)
        assert lowered.actor_ref == "participant:system"
        assert lowered.source_application_ref == meaning.expression.applications[0].application_ref
        assert lowered.contract is runtime.authority.learning_contract("contract:designation_learning:v2")
        expected = SemanticApplication("app:designation", "op:designation", "label:lexical", (
            RoleBinding("role:target", GroundedReference("rel:likes")),
            RoleBinding("role:surface", LiteralValue("string", "velnora")),
            RoleBinding("role:label_type", GroundedReference("label:lexical")),
        ))
        expected_expression = SemanticExpression.create(applications=(expected,), root_refs=(expected.application_ref,))
        assert lowered.designation == expected_expression.applications[0]
        assert meaning.expression.applications[0].operator == "op:event"
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", [
    "direct-designation", "missing-actor", "wrong-actor", "literal-actor", "missing-situation-actor",
    "different-situation-actor", "not-addressed", "unknown-actor", "missing-capability",
    "missing-permission", "wrong-phase", "observe", "query", "simulate", "negative", "reported",
    "conditional", "speech", "extra-role", "qualifier", "unresolved-target", "unsupported-kind",
    "foreign-generation", "missing-contract", "authority-capability", "authority-permission",
    "permission-other-event", "permission-other-actor",
], ids=[
    "direct-designation", "missing-actor", "wrong-actor", "literal-actor", "missing-situation-actor",
    "different-situation-actor", "not-addressed", "unknown-actor", "missing-capability",
    "missing-permission", "wrong-phase", "observe", "query", "simulate", "negative", "reported",
    "conditional", "speech", "extra-role", "qualifier", "unresolved-target", "unsupported-kind",
    "foreign-generation", "missing-contract", "authority-capability", "authority-permission",
    "permission-other-event", "permission-other-actor",
])
def test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority(tmp_path, case):
    runtime, source, pending = _setup(tmp_path)
    try:
        meaning, situation = _event_answer(runtime, source.evaluation.situation)
        expression = meaning.expression
        app = expression.applications[0]
        authority = runtime.authority
        if case == "direct-designation":
            designation = SemanticApplication("app:direct", "op:designation", "label:lexical", (
                RoleBinding("role:label_type", GroundedReference("label:lexical")),
                RoleBinding("role:surface", LiteralValue("string", "velnora")),
                RoleBinding("role:target", GroundedReference("rel:likes")),
            ))
            expression = _matrix_expression(designation)
        elif case in {"missing-actor", "wrong-actor", "literal-actor", "unknown-actor"}:
            roles = tuple(binding for binding in app.roles if binding.role_ref != "role:actor")
            if case != "missing-actor":
                filler = LiteralValue("string", "participant:system") if case == "literal-actor" else GroundedReference("participant:user" if case == "wrong-actor" else "participant:unknown")
                roles += (RoleBinding("role:actor", filler),)
            expression = _matrix_expression(replace(app, roles=roles))
        elif case in {"missing-situation-actor", "different-situation-actor", "not-addressed"}:
            situation = _situation(situation, **{
                "missing-situation-actor": {"actor_ref": None},
                "different-situation-actor": {"actor_ref": "participant:user"},
                "not-addressed": {"addressee_ref": "participant:user", "speaker_ref": "participant:system"},
            }[case])
        elif case in {"missing-capability", "missing-permission", "wrong-phase", "observe", "query", "simulate"}:
            changes = {
                "missing-capability": {"capability_refs": ()}, "missing-permission": {"permission_refs": ()},
                "wrong-phase": {"session_phase_ref": "suspended"},
                "observe": {"mode": SemanticMode.OBSERVE, "epistemic_scope_ref": "epistemic_scope:observed"},
                "query": {"mode": SemanticMode.QUERY, "epistemic_scope_ref": "epistemic_scope:query"},
                "simulate": {"mode": SemanticMode.SIMULATE, "epistemic_scope_ref": "epistemic_scope:simulated"},
            }[case]
            situation = _situation(situation, **changes)
        elif case in {"negative", "reported", "conditional", "speech"}:
            expression = _matrix_expression(app, case)
        elif case in {"extra-role", "qualifier"}:
            extra = RoleBinding("role:content", GroundedReference("entity:book"))
            expression = _matrix_expression(replace(app, **({"roles": (*app.roles, extra)} if case == "extra-role" else {"qualifiers": (extra,)})))
        elif case == "unresolved-target":
            roles = tuple(RoleBinding(binding.role_ref, UnresolvedValue("unresolved:target")) if binding.role_ref == "role:target" else binding for binding in app.roles)
            expression = SemanticExpression.create(applications=(replace(app, roles=roles),), root_refs=(app.application_ref,), unresolved_fillers=(UnresolvedFiller("unresolved:target", app.application_ref, "role:target", "anchor", ("relation_type",), True),))
        elif case == "unsupported-kind":
            expression = _matrix_expression(replace(app, roles=tuple(RoleBinding(binding.role_ref, GroundedReference("cap:learn_alias")) if binding.role_ref == "role:target" else binding for binding in app.roles)))
        elif case == "foreign-generation":
            situation = _situation(situation, revision_pin=replace(situation.revision_pin, authority_generation="authority:foreign"))
        else:
            owners = _owners()
            if case == "missing-contract":
                owners["alias_learning"]["learning_contracts"] = []
            elif case == "authority-capability":
                owners["kernel"]["capabilities"]["participant:system"].remove("cap:learn_alias")
            else:
                for owner in owners.values():
                    owner["permissions"] = [row for row in owner.get("permissions", []) if row[1] != "permission:write_alias"]
                if case in {"permission-other-event", "permission-other-actor"}:
                    owners["kernel"]["permissions"].append([
                        "participant:user" if case == "permission-other-actor" else "participant:system",
                        "permission:write_alias", "event:greeting" if case == "permission-other-event" else "event:learn_alias",
                    ])
            manifest = _manifest(tmp_path / "authority", owners)
            manifest["generation"] = authority.generation
            authority = AuthorityLinker().link(manifest)
        expected_error = PermissionError if case in {"missing-permission", "authority-permission", "permission-other-event", "permission-other-actor"} else ValueError
        with pytest.raises(expected_error):
            _lower(authority, expression, situation)
    finally:
        runtime.stores.close()


def test_learning_plan_factory_requires_all_linked_authority_fields():
    signature = inspect.signature(LearningPlan.create)
    for name in ("contract_ref", "goal_ref", "capability_ref", "permission_ref", "commit_operator_ref", "answer_contract_ref", "source_obligation_ref"):
        assert signature.parameters[name].default is inspect.Parameter.empty


def test_incomplete_reviewed_learning_event_requests_clarification_without_draft(tmp_path):
    runtime, source, _ = _setup(tmp_path)
    try:
        meaning, situation = _event_answer(runtime, source.evaluation.situation)
        app = meaning.expression.applications[0]
        app = replace(app, roles=tuple(
            RoleBinding(binding.role_ref, UnresolvedValue("unresolved:learning-target"))
            if binding.role_ref == "role:target" else binding for binding in app.roles
        ))
        expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,),
            unresolved_fillers=(UnresolvedFiller("unresolved:learning-target", app.application_ref,
                "role:target", "reference", ("relation_type",), True),))
        meaning = _matrix_meaning(expression, situation.revision_pin)
        evaluation = R3EvaluationOwner(runtime.authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert evaluation.decision.status is DecisionStatus.UNKNOWN
        assert evaluation.decision.action is DecisionAction.REQUEST_CLARIFICATION
        assert evaluation.decision.blocker_refs == ("learning:target_missing",)
        assert evaluation.learning_drafts == ()
        assert evaluation.effect_intents == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field,status", [
    ("capability_refs", DecisionStatus.UNKNOWN), ("permission_refs", DecisionStatus.DENIED),
], ids=["unknown-capability", "denied-permission"])
def test_learning_grant_decisions_preserve_unknown_and_denied_distinction(tmp_path, field, status):
    runtime, source, _ = _setup(tmp_path)
    try:
        meaning, situation = _event_answer(runtime, source.evaluation.situation, **{field: ()})
        result = R3EvaluationOwner(runtime.authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert result.decision.status is status
        assert result.learning_drafts == () and result.effect_intents == ()
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ["actor-proof", "policy", "direct-designation"], ids=["actor-proof", "policy", "direct-designation"])
def test_materializer_rederives_source_authority_instead_of_trusting_draft(tmp_path, case):
    runtime, source, _ = _setup(tmp_path)
    try:
        meaning, situation = _event_answer(runtime, source.evaluation.situation)
        evaluator = R3EvaluationOwner(runtime.authority, runtime.stores, runtime._config)
        mode = evaluator.evaluate_mode(meaning, situation)
        if case == "actor-proof":
            draft = mode.learning_drafts[0]
            values = {field.name: getattr(draft, field.name) for field in fields(draft)
                      if field.name not in {"abi_version", "learning_draft_ref"}}
            values["proof_refs"] = tuple("participant:user" if ref == "participant:system" else ref for ref in draft.proof_refs)
            forged = LearningDraft.create(**values)
            mode = replace(mode, learning_drafts=(forged,), contribution=replace(mode.contribution,
                learning_draft_refs=(forged.learning_draft_ref,),
                proof_refs=tuple("participant:user" if ref == "participant:system" else ref for ref in mode.contribution.proof_refs)))
        elif case == "policy":
            mode = replace(mode, contribution=replace(mode.contribution, policy_refs=("policy:forged-review",)))
        else:
            app = _lower(runtime.authority, meaning.expression, situation).designation
            meaning = _matrix_meaning(_matrix_expression(app), situation.revision_pin)
        evaluation = evaluator.finalize(meaning, situation, mode, authority=runtime.authority)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(ValueError):
            LearningCoordinator(runtime.authority, runtime.stores).materialize(evaluation, meaning, situation)
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


def test_pure_learning_lowering_uses_activation_grant_indexes_and_preserves_unicode(tmp_path):
    runtime, source, _ = _setup(tmp_path)

    class NoGrantScan:
        def __iter__(self):
            raise AssertionError("normal lowering scanned authority grants")
        def get(self, *_args):
            raise AssertionError("normal lowering scanned authority grants")

    try:
        meaning, situation = _event_answer(runtime, source.evaluation.situation, surface="뜻 αλφα", target="entity:alice")
        app = meaning.expression.applications[0]
        positive = ScopeOperator("scope:positive", "scope:polarity", "polarity:positive", app.application_ref)
        expression = SemanticExpression.create(applications=(app,), scope_operators=(positive,), root_refs=(positive.scope_ref,))
        runtime.authority.capabilities = NoGrantScan()
        runtime.authority.permissions = NoGrantScan()
        lowered = _lower(runtime.authority, expression, situation)
        roles = {binding.role_ref: binding.filler for binding in lowered.designation.roles}
        assert roles["role:surface"] == LiteralValue("string", "뜻 αλφα")
        assert roles["role:target"] == GroundedReference("entity:alice")
    finally:
        runtime.stores.close()


def test_unseen_reviewed_learning_synonym_uses_public_path_without_pack_regeneration(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.bootstrap import load_runtime

    owners = _owners()
    owners["conversation"]["designations"].append({"language": "en", "surface": "mavren", "target": "event:learn_alias"})
    authority_dir = tmp_path / "data" / "authority"
    manifest = _manifest(authority_dir, owners)
    (authority_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    form_path = tmp_path / "data" / "languages" / "en" / "forms.json"
    form_path.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "data" / "languages" / "en" / "forms.json", form_path)
    pack_before = form_path.read_bytes()
    runtime = load_runtime(tmp_path, profile="development", store_path=tmp_path / "synonym.db")
    captured = {}

    class ReachedEffect(Exception):
        pass

    def inspect_effect(self, evaluation, meaning, situation, **kwargs):
        captured.update(evaluation=evaluation, meaning=meaning, **kwargs)
        raise ReachedEffect

    try:
        source = runtime.process("session:synonym", "What does velnora mean?")
        monkeypatch.setattr(R3EffectGateway, "execute", inspect_effect)
        with pytest.raises(ReachedEffect):
            runtime.process("session:synonym", "mavren velnora means likes")
        assert captured["evaluation"].decision.action is DecisionAction.CREATE_LEARNING_OBLIGATION
        assert captured["meaning"].expression.applications[0].predicate_ref == "event:learn_alias"
        assert captured["learning_plan"].source_query_ref == source.evaluation.query_results[0].query_result_ref
        assert form_path.read_bytes() == pack_before
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


__cemm_test_inventory__ = {
    "tests/test_foundation_learning_lowering.py::test_public_learning_event_materializes_linked_plan_before_disabled_effect[event]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-public-learning-event-materializes-linked-plan-before-disabled-effect-event",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7fc15bd5af9e906d70157b09b70cc4d61d5923cc43703631a14adfaf4edfed51"
    },
    "tests/test_foundation_learning_lowering.py::test_public_learning_event_materializes_linked_plan_before_disabled_effect[embedded-designation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-public-learning-event-materializes-linked-plan-before-disabled-effect-embedded-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7fc15bd5af9e906d70157b09b70cc4d61d5923cc43703631a14adfaf4edfed51"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_lowering_preserves_actor_source_and_canonical_designation": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-lowering-preserves-actor-source-and-canonical-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "cfe7b7f24b7a626d3df53c6f60b5c5f61bc2a135143d6a3327e0f83144bf15d2"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[direct-designation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-direct-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[missing-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-missing-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[wrong-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-wrong-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[literal-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-literal-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[missing-situation-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-missing-situation-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[different-situation-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-different-situation-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[not-addressed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-not-addressed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[unknown-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-unknown-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[missing-capability]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-missing-capability",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[missing-permission]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-missing-permission",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[wrong-phase]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-wrong-phase",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[observe]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-observe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[simulate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[negative]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-negative",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[reported]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-reported",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[conditional]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-conditional",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[speech]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-speech",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[extra-role]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-extra-role",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[qualifier]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-qualifier",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[unresolved-target]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-unresolved-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[unsupported-kind]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-unsupported-kind",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[foreign-generation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-foreign-generation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[missing-contract]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-missing-contract",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[authority-capability]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-authority-capability",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[authority-permission]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-authority-permission",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[permission-other-event]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-permission-other-event",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_rejects_nonlicensed_structure_or_authority[permission-other-actor]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-rejects-nonlicensed-structure-or-authority-permission-other-actor",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "253ead018c00261b87748958ff4bc3fd71bbba1746811c11f54d4aaf8a8e2182"
    },
    "tests/test_foundation_learning_lowering.py::test_learning_plan_factory_requires_all_linked_authority_fields": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-learning-plan-factory-requires-all-linked-authority-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "9b722dd2e9394a06c0524c43bc5b7c284bd02979e3dab33fceb8841e98c44003"
    },
    "tests/test_foundation_learning_lowering.py::test_incomplete_reviewed_learning_event_requests_clarification_without_draft": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-incomplete-designation-clarifies-without-learning-draft",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "c4d9d8a9a418aa5316777cafa8b04322c824880b741a996d82b92a94487085dd",
    },
    "tests/test_foundation_learning_lowering.py::test_learning_grant_decisions_preserve_unknown_and_denied_distinction[unknown-capability]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-learning-grant-decisions-preserve-unknown-and-denied-distinction-unknown-capability",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7090ddd90525bdc9adfa64167de532a144915fb3413c3e90ac19cbc9c3cfd09a"
    },
    "tests/test_foundation_learning_lowering.py::test_learning_grant_decisions_preserve_unknown_and_denied_distinction[denied-permission]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-learning-grant-decisions-preserve-unknown-and-denied-distinction-denied-permission",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "7090ddd90525bdc9adfa64167de532a144915fb3413c3e90ac19cbc9c3cfd09a"
    },
    "tests/test_foundation_learning_lowering.py::test_materializer_rederives_source_authority_instead_of_trusting_draft[actor-proof]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-materializer-rederives-source-authority-instead-of-trusting-draft-actor-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "3bcf298d19787514d04eb4013d4e6b9abea49cbe76be985e943abd861f319dec"
    },
    "tests/test_foundation_learning_lowering.py::test_materializer_rederives_source_authority_instead_of_trusting_draft[policy]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-materializer-rederives-source-authority-instead-of-trusting-draft-policy",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "3bcf298d19787514d04eb4013d4e6b9abea49cbe76be985e943abd861f319dec"
    },
    "tests/test_foundation_learning_lowering.py::test_materializer_rederives_source_authority_instead_of_trusting_draft[direct-designation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-materializer-rederives-source-authority-instead-of-trusting-draft-direct-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "3bcf298d19787514d04eb4013d4e6b9abea49cbe76be985e943abd861f319dec"
    },
    "tests/test_foundation_learning_lowering.py::test_pure_learning_lowering_uses_activation_grant_indexes_and_preserves_unicode": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-pure-learning-lowering-uses-activation-grant-indexes-and-preserves-unicode",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "317e614301a63ba7176d8ee445eaeb87b958c2565492c38246581df58abb0c64"
    },
    "tests/test_foundation_learning_lowering.py::test_unseen_reviewed_learning_synonym_uses_public_path_without_pack_regeneration": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-unseen-reviewed-learning-synonym-uses-public-path-without-pack-regeneration",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1914688b4b33ffbbfde43825440493eb7e738025fa7498001ba06f3752e16759"
    }
}
