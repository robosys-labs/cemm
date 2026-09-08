"""Explicit current semantic assertions replacing stale test fixtures only."""
from __future__ import annotations

from pathlib import Path

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.expressions import (
    BoundVariable, GroundedReference, LiteralValue, RoleBinding,
    SemanticApplication, SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.programs import PERSISTENT_OPERATORS


ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_test_successors.py::test_linked_five_persistent_operators_compose_and_exactly_verify": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:adversarial-programs-only-five-persistent-operators-accepted",
        "diagnostic_role": "owner",
        "owner_ref": "exact-verifier",
        "supersedes_node_id": "tests/test_adversarial_programs.py::test_canonical_designation_successor_accepts_all_five_persistent_operators",
        "introduced_by_task": "Foundation-Proof-Test-Fixture-Repair",
        "source_ast_sha256": "776cbf94551182ddd2ca5d3f5a69418775085ab2c2cba6c62c4cdca0f26753f5"
    },
    "tests/test_foundation_test_successors.py::test_explicit_unresolved_lexical_query_preserves_label_bound_target_and_roundtrip": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-unresolved-designation-unresolved-designation-query-uses-the-same-label-application-with-bound-target",
        "diagnostic_role": "owner",
        "owner_ref": "expression-compiler",
        "supersedes_node_id": "tests/test_semantic_expressions.py::test_unresolved_designation_query_uses_the_same_label_application_with_bound_target",
        "introduced_by_task": "Foundation-Proof-Test-Fixture-Repair",
        "source_ast_sha256": "cb3291a5a8f7696169268a5a5c847db0b20e7d3fcbcccbc9c376c9a1a7cff9f6"
    },
    "tests/test_foundation_test_successors.py::test_unreviewed_seeded_alias_cannot_enter_grounding_or_query_proof_after_restart": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-unreviewed-seeded-alias-excluded-after-restart",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Test-Fixture-Repair",
        "source_ast_sha256": "6c5b9c2b99663edb29c005590eb22097952cb3e2439799a0d14f2e2ae369d3e5"
    }
}



def _verify(runtime, session, surface):
    _, context = runtime.orient(session, surface)
    proposal = runtime.proposal_model.propose(context)
    batch = runtime._owners["verification"].verify_candidates(proposal, context)
    return context, proposal, batch


def test_linked_five_persistent_operators_compose_and_exactly_verify(tmp_path):
    operators = {"op:designation", "op:type", "op:relation", "op:state", "op:event"}
    assert PERSISTENT_OPERATORS == frozenset(operators)
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "five.db")
    try:
        assert set(runtime.authority.operator_roles) == operators
        used_schema_roles = {
            "op:designation": {"role:target", "role:label_type", "role:surface"},
            "op:type": {"role:instance", "role:class"},
            "op:relation": {"role:subject", "role:relation", "role:object"},
            "op:state": {"role:subject", "role:dimension", "role:value"},
            "op:event": {"role:event", "role:type"},
        }
        for operator, required_roles in used_schema_roles.items():
            assert required_roles <= set(runtime.authority.operator_roles[operator])
        assert "role:actor" in runtime.authority.by_event_signature("event:leave").required_roles
        # Independently authored semantic forests. Relation/event structural
        # identities are predicate/application refs, not duplicate role fillers.
        cases = (
            ("CEMM", "op:designation", "label:lexical", (
                RoleBinding("role:label_type", GroundedReference("label:lexical")),
                RoleBinding("role:target", GroundedReference("participant:system")),
                RoleBinding("role:surface", LiteralValue("string", "CEMM")),
            )),
            ("Alice is a mother.", "op:type", "concept:mother", (
                RoleBinding("role:instance", GroundedReference("entity:alice")),
                RoleBinding("role:class", GroundedReference("concept:mother")),
            )),
            ("Alice likes Bob.", "op:relation", "rel:likes", (
                RoleBinding("role:subject", GroundedReference("entity:alice")),
                RoleBinding("role:object", GroundedReference("entity:bob")),
            )),
            ("The lamp is on.", "op:state", "dim:power", (
                RoleBinding("role:subject", GroundedReference("entity:lamp")),
                RoleBinding("role:dimension", GroundedReference("dim:power")),
                RoleBinding("role:value", GroundedReference("value:on")),
            )),
            ("Alice left.", "op:event", "event:leave", (
                RoleBinding("role:actor", GroundedReference("entity:alice")),
            )),
        )
        accepted = set()
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        for index, (surface, operator, predicate, roles) in enumerate(cases):
            app = SemanticApplication("application:expected", operator, predicate, roles)
            expected = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
            context, proposal, batch = _verify(runtime, f"session:five:{index}", surface)
            assert proposal.candidates, operator
            assert batch.status == "selected", operator
            assert batch.selected_meaning is not None, operator
            program = next(candidate.program for candidate in proposal.candidates if candidate.candidate_ref == batch.selected_candidate_ref)
            assert tuple(row.source_unit_ref for row in program.source_assignments) == context.source_unit_refs
            actual = batch.selected_meaning.expression
            assert actual == expected, operator
            assert any(frame.operator_ref == operator for frame in context.application_frames)
            assert len(actual.applications) == 1
            accepted.add(actual.applications[0].operator)
        assert accepted == operators
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
    finally:
        runtime.stores.close()


def test_explicit_unresolved_lexical_query_preserves_label_bound_target_and_roundtrip(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "lexical.db")
    try:
        result = runtime.process("session:unresolved-designation-expression", "What does zorbulate mean?")
    finally:
        runtime.stores.close()
    assert result.verification.selected_meaning is not None
    expression = result.verification.selected_meaning.expression
    applications = tuple(app for app in expression.applications if app.operator == "op:designation")
    assert len(applications) == 1
    designation = applications[0]
    assert designation.predicate_ref == "label:lexical"
    assert designation.qualifiers == ()
    roles = {binding.role_ref: binding.filler for binding in designation.roles}
    assert set(roles) == {"role:label_type", "role:surface", "role:target"}
    assert roles["role:label_type"] == GroundedReference("label:lexical")
    assert roles["role:surface"] == LiteralValue("string", "zorbulate")
    assert isinstance(roles["role:target"], BoundVariable)
    matching_binders = tuple(binder for binder in expression.binders if binder.variable_ref == roles["role:target"].variable_ref)
    assert len(matching_binders) == 1
    assert matching_binders[0].body_ref == designation.application_ref
    assert all(app.predicate_ref != "concept:zorbulate" for app in expression.applications)
    assert all(
        not (isinstance(binding.filler, GroundedReference) and binding.filler.target_ref == "concept:zorbulate")
        for app in expression.applications for binding in app.roles
    )
    assert SemanticExpression.from_dict(expression.as_dict()) == expression


def test_unreviewed_seeded_alias_cannot_enter_grounding_or_query_proof_after_restart(tmp_path):
    # This negative does not replace the still-open authenticated publication,
    # restart, and unseen-composition positive obligation.
    path = tmp_path / "alias.db"
    authority_before = {source.relative_to(ROOT): source.read_bytes() for source in (ROOT / "data/authority").rglob("*.json")}
    pack = ROOT / "data/languages/en/forms.json"
    pack_before = pack.read_bytes()
    runtime = load_runtime(ROOT, profile="development", store_path=path)
    atoms_before = dict(runtime.authority.atoms)
    content_before = runtime.authority.content_hash
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
        assert any(fact.fact_ref == "fact:reviewed-velnora" for fact in runtime.stores.r3_world_facts())
        assert runtime.authority.designations.for_surface("velnora", "en") == ()
        _, context = runtime.orient("session:unreviewed-alias", "Bob velnora Alice.")
        assert not any(slot.target_ref == "rel:likes" for slot in context.designation_slots)
        assert not any(frame.predicate_target_ref == "rel:likes" for frame in context.application_frames)
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:unreviewed-lexical-query", "What does velnora mean?")
        assert result.verification.selected_meaning is not None
        assert len(result.evaluation.query_results) == 1
        query = result.evaluation.query_results[0]
        assert query.status.value == "unknown"
        assert query.proof is None
        assert query.bindings == ()
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        assert runtime.authority.content_hash == content_before
        assert dict(runtime.authority.atoms) == atoms_before
        assert {source.relative_to(ROOT): source.read_bytes() for source in (ROOT / "data/authority").rglob("*.json")} == authority_before
        assert pack.read_bytes() == pack_before
    finally:
        runtime.stores.close()
