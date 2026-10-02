"""Subject-person membership queries, distinct from semantic descriptions."""

from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.authority import DesignationFact
from cemm_authoritative_hybrid.expressions import (
    BoundVariable, GroundedReference, RoleBinding, ScopeOperator,
    SemanticApplication, SemanticExpression, VariableBinder,
)
from cemm_authoritative_hybrid.proposal_context import ApplicationFrameSlot, ContributionSlot, ProposalContext
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier
from tests.test_foundation_semantics import _static_composition_context


ROOT = Path(__file__).resolve().parents[1]


__cemm_test_inventory__ = {
    "tests/test_foundation_membership_queries.py::test_public_subject_person_membership_preserves_independent_graph[determined]": {
        "activation_phase": "R2", "assertion_ref": "assertion:subject-person-membership-query-determined",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "bdeeff5d096836a6e9e15afa6b41546f0e3f8b5dbf63e7e4de222470aea14db2",
    },
    "tests/test_foundation_membership_queries.py::test_public_subject_person_membership_preserves_independent_graph[bare]": {
        "activation_phase": "R2", "assertion_ref": "assertion:subject-person-membership-query-bare",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "bdeeff5d096836a6e9e15afa6b41546f0e3f8b5dbf63e7e4de222470aea14db2",
    },
    "tests/test_foundation_membership_queries.py::test_non_subject_person_queries_remain_unsupported[content-determined]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-content-determined-unchanged",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "a9c1a7024c55ad472ef8739f9b44ff09baee16059df78f4a760c77eecfb2b66e",
    },
    "tests/test_foundation_membership_queries.py::test_non_subject_person_queries_remain_unsupported[content-bare]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-content-bare-unchanged",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "a9c1a7024c55ad472ef8739f9b44ff09baee16059df78f4a760c77eecfb2b66e",
    },
    "tests/test_foundation_membership_queries.py::test_non_subject_person_queries_remain_unsupported[boolean-inversion]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-boolean-inversion-unchanged",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "a9c1a7024c55ad472ef8739f9b44ff09baee16059df78f4a760c77eecfb2b66e",
    },
    "tests/test_foundation_membership_queries.py::test_non_subject_person_queries_remain_unsupported[nonadjacent-person]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-nonadjacent-person-denied",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "a9c1a7024c55ad472ef8739f9b44ff09baee16059df78f4a760c77eecfb2b66e",
    },
    "tests/test_foundation_membership_queries.py::test_non_subject_person_queries_remain_unsupported[unknown-class]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-unknown-class-critical",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "a9c1a7024c55ad472ef8739f9b44ff09baee16059df78f4a760c77eecfb2b66e",
    },
    "tests/test_foundation_membership_queries.py::test_person_evidence_cannot_license_another_clause[person-first]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-person-first-clause-local",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "ca1e1f73cfad1c0f10b91f78f0f72fde834ae848853e2d58d8cb563fd7bfec75",
    },
    "tests/test_foundation_membership_queries.py::test_person_evidence_cannot_license_another_clause[content-first]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-content-first-clause-local",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "ca1e1f73cfad1c0f10b91f78f0f72fde834ae848853e2d58d8cb563fd7bfec75",
    },
    "tests/test_foundation_membership_queries.py::test_polarity_is_retained_without_a_positive_query_fallback": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-polarity-fail-closed",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "7be507132d57efd10072f9f24f267dcec0e705efab9fa3728d03e0e836bdac6c",
    },
    "tests/test_foundation_membership_queries.py::test_extended_query_context_rejects_changed_person_evidence": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-person-evidence-integrity",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "3a9687df8bfff092204372d1a7d50e166812bd06f193ba71487a685dec5acb5d",
    },
    "tests/test_foundation_membership_queries.py::test_verifier_rejects_extended_membership_without_form_owner[copula]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-copula-owner-integrity",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "9cf0d23445ba491d69bd2ae8c4dfd7e02485dd598a4fd921df505f2da2d8eae7",
    },
    "tests/test_foundation_membership_queries.py::test_verifier_rejects_extended_membership_without_form_owner[determiner]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-determiner-owner-integrity",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "9cf0d23445ba491d69bd2ae8c4dfd7e02485dd598a4fd921df505f2da2d8eae7",
    },
    "tests/test_foundation_membership_queries.py::test_verifier_rejects_membership_extension_licensed_by_foreign_person": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-foreign-person-owner-integrity",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "af1f8dc10dd64fd5a03d7794b88e3945fc1b2da56505fd97997fab60745fd7d7",
    },
    "tests/test_foundation_membership_queries.py::test_static_synonyms_inherit_membership_affordance_without_pack_changes[unseen-alias]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-unseen-alias-affordance",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "2a7f21d96493d108c4305c6f6445072d504adccb60aeb49989740901ce53ca05",
    },
    "tests/test_foundation_membership_queries.py::test_static_synonyms_inherit_membership_affordance_without_pack_changes[spanish-features]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-spanish-form-equivalence",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "2a7f21d96493d108c4305c6f6445072d504adccb60aeb49989740901ce53ca05",
    },
    "tests/test_foundation_membership_queries.py::test_static_synonyms_inherit_membership_affordance_without_pack_changes[spanish-unseen-multiword]": {
        "activation_phase": "R2", "assertion_ref": "assertion:membership-query-spanish-unseen-multiword-affordance",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "form-context",
        "source_ast_sha256": "2a7f21d96493d108c4305c6f6445072d504adccb60aeb49989740901ce53ca05",
    },
}


def _expected_person_membership():
    app = SemanticApplication("application:expected-membership", "op:type", "concept:mother", (
        RoleBinding("role:instance", BoundVariable("?person")),
        RoleBinding("role:class", GroundedReference("concept:mother")),
    ))
    binder = VariableBinder("binder:expected-person", "?person", app.application_ref)
    return SemanticExpression.create(applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,))


def _context(runtime, surface):
    evidence = runtime.create_evidence("session:membership-query", surface)
    turn = runtime._orient_turn("session:membership-query", evidence,
        revision_pin=runtime.stores.revision_pin())
    return turn.context


def _assert_membership_receipt(result):
    assert result.verification.selected_meaning is not None, result.proposal.abstention_code
    assert result.verification.selected_meaning.expression == _expected_person_membership()
    assert len(result.proposal.candidates) == 1 and not result.proposal.truncated
    assert result.proposal.explored_states == 4
    selected = next(receipt for receipt in result.verification.candidate_receipts
        if receipt.candidate_ref == result.verification.selected_candidate_ref)
    assert selected.verification_errors == ()
    assert selected.coverage_receipt.executable
    assert selected.coverage_receipt.missing_unit_refs == ()
    assert selected.coverage_receipt.duplicate_unit_refs == ()
    assert selected.coverage_receipt.critical_residuals == ()
    assignments = {row.source_unit_ref: row for row in selected.coverage_receipt.assignments}
    assert assignments["unit:0"].assignment_kind == "role"
    assert assignments["unit:0"].target_role_ref == "role:instance"
    assert assignments["unit:2"].assignment_kind == "predicate"
    assert assignments["unit:4"].assignment_kind == "predicate"


@pytest.mark.parametrize("surface", ("who is a mother?", "who is mother?"),
    ids=("determined", "bare"))
def test_public_subject_person_membership_preserves_independent_graph(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "membership")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:membership-query", surface, trace=True)
        _assert_membership_receipt(result)
        assert result.orientation.mode.value == "QUERY"
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", (
    "what is a mother?", "what is mother?", "is Alice a mother?",
    "who Alice is a mother?", "who is a person?",
), ids=("content-determined", "content-bare", "boolean-inversion", "nonadjacent-person", "unknown-class"))
def test_non_subject_person_queries_remain_unsupported(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "unsupported")
    try:
        context = _context(runtime, surface)
        for frame in context.application_frames:
            designation = context.designation(frame.designation_slot_ref)
            assert frame.source_unit_refs == designation.source_unit_refs
        result = runtime.process("session:membership-query", surface)
        assert result.verification.selected_meaning is None
        if surface in ("what is a mother?", "what is mother?"):
            assert len(context.query_projection_slots) == 2
            assert len(result.proposal.candidates) == len(result.verification.candidate_receipts) == 2
            assert all(receipt.accepted for receipt in result.verification.candidate_receipts)
            expressions = tuple(receipt.expression for receipt in result.verification.candidate_receipts)
            assert {(query.target_ref, query.requested_content) for expression in expressions
                for query in expression.query_projections} == {
                    ("concept:mother", "description"), ("concept:mother", "definition")}
            assert all(expression.applications == () and expression.binders == ()
                and expression.scope_operators == () and expression.expression_links == ()
                and len(expression.root_refs) == len(expression.query_projections) == 1
                for expression in expressions)
            assert len(result.verification.ambiguity_expression_refs) == 2
        else:
            assert result.proposal.candidates == ()
        if surface == "who is a person?":
            assert context.critical_residual_unit_refs
            assert result.proposal.abstention_code == "proposal:critical_residual"
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", (
    "who is a mother? what is a mother?", "what is a mother? who is a mother?",
), ids=("person-first", "content-first"))
def test_person_evidence_cannot_license_another_clause(surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "locality")
    try:
        context = _context(runtime, surface)
        assert len(context.application_frames) == 2
        extended = [frame for frame in context.application_frames
            if frame.source_unit_refs != context.designation(frame.designation_slot_ref).source_unit_refs]
        assert len(extended) == 1
        span = context.source_span(extended[0].source_unit_refs)
        assert surface[span[0]:span[1]] == "is a mother"
        person_start = surface.index("who")
        assert span[0] == person_start + len("who ")
        result = runtime.process("session:membership-query", surface)
        assert result.verification.selected_meaning is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_polarity_is_retained_without_a_positive_query_fallback(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "polarity")
    try:
        context = _context(runtime, "who is not a mother?")
        assert len(context.scope_slots) == 1
        assert context.scope_slots[0].operator_type == "scope:polarity"
        assert context.scope_slots[0].value_ref == "scope_value:polarity:negative"
        assert context.scope_slots[0].source_unit_refs == ("unit:4",)
        assert context.application_frames[0].source_unit_refs == ("unit:2", "unit:6", "unit:8")
        result = runtime.process("session:membership-query", "who is not a mother?")
        assert result.verification.selected_meaning is None
        assert result.proposal.candidates == ()
        # Existing declarative scope must still describe only the type claim.
        result = runtime.process("session:negative-claim", "Alice is not a mother.")
        app = SemanticApplication("application:negative-expected", "op:type", "concept:mother", (
            RoleBinding("role:instance", GroundedReference("entity:alice")),
            RoleBinding("role:class", GroundedReference("concept:mother")),
        ))
        scope = ScopeOperator("scope:negative-expected", "scope:polarity",
            "scope_value:polarity:negative", app.application_ref)
        expected = SemanticExpression.create(applications=(app,), scope_operators=(scope,),
            root_refs=(scope.scope_ref,))
        assert result.verification.selected_meaning.expression == expected
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_extended_query_context_rejects_changed_person_evidence(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "tamper")
    try:
        context = _context(runtime, "who is a mother?")
        assert context.application_frames[0].source_unit_refs == ("unit:2", "unit:4", "unit:6")
        assert ProposalContext.from_dict(context.as_dict()) == context
        contributions = []
        for row in context.contribution_slots:
            if row.kind == "open_variable":
                row = ContributionSlot.create(contribution_ref=stable_ref("form_contribution", ("unit:0", "query", "query")),
                    kind=row.kind, source_unit_refs=row.source_unit_refs, target_ref=row.target_ref,
                    target_kind=row.target_kind, input_ports=row.input_ports, output_ports=row.output_ports,
                    constraints=(("query", "query"), ("interrogative", "content")),
                    provenance_refs=row.provenance_refs, literal_value=row.literal_value)
            contributions.append(row)
        values = {name: getattr(context, name) for name in inspect.signature(ProposalContext.create).parameters
            if name != "config"}
        with pytest.raises(ValueError, match="nominal predication"):
            ProposalContext.create(**{**values, "contribution_slots": tuple(contributions)})
        forged = copy.copy(context)
        object.__setattr__(forged, "contribution_slots", tuple(contributions))
        proposal = runtime.proposal_model.propose(context)
        with pytest.raises(ValueError, match="nominal predication"):
            ExactProgramVerifier(authority=runtime.authority).verify_candidates(proposal, forged)
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("missing_source", ("unit:2", "unit:4"), ids=("copula", "determiner"))
def test_verifier_rejects_extended_membership_without_form_owner(missing_source, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "missing-owner")
    try:
        context = _context(runtime, "who is a mother?")
        assert context.application_frames[0].source_unit_refs == ("unit:2", "unit:4", "unit:6")
        proposal = runtime.proposal_model.propose(context)
        forged = copy.copy(context)
        object.__setattr__(forged, "contribution_slots", tuple(row for row in context.contribution_slots
            if row.source_unit_refs != (missing_source,)))
        with pytest.raises(ValueError, match="nominal predication"):
            ExactProgramVerifier(authority=runtime.authority).verify_candidates(proposal, forged)
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_verifier_rejects_membership_extension_licensed_by_foreign_person(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "foreign-person")
    try:
        context = _context(runtime, "who is a mother? what is a mother?")
        proposal = runtime.proposal_model.propose(context)
        frame = next(row for row in context.application_frames if row.source_unit_refs == ("unit:15",))
        values = {name: getattr(frame, name) for name in inspect.signature(ApplicationFrameSlot.create).parameters}
        foreign_licensed = ApplicationFrameSlot.create(**{**values,
            "source_unit_refs": ("unit:11", "unit:13", "unit:15")})
        forged = copy.copy(context)
        object.__setattr__(forged, "application_frames", tuple(foreign_licensed if row == frame else row
            for row in context.application_frames))
        with pytest.raises(ValueError, match="nominal predication"):
            ExactProgramVerifier(authority=runtime.authority).verify_candidates(proposal, forged)
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,alias,surface", (
    ("en", "velnora", "who is a velnora?"),
    ("es", "madre", "quién es una madre?"),
    ("es", "luz velnora", "quién es una luz velnora?"),
), ids=("unseen-alias", "spanish-features", "spanish-unseen-multiword"))
def test_static_synonyms_inherit_membership_affordance_without_pack_changes(language, alias, surface, tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "static")
    try:
        pack_path = ROOT / "data/languages" / language / "forms.json"
        before_pack = pack_path.read_bytes()
        pack = json.loads(before_pack)
        if language == "es":
            # Feature-equivalent component fixture, not Spanish pack publication.
            pack["query_projection"]["quién"]["interrogative"] = "person"
        facts = (DesignationFact.create(surface=alias, target_ref="concept:mother", language=language),)
        _, context = _static_composition_context(runtime.authority, runtime.stores, pack, surface, facts=facts)
        proposal = runtime.proposal_model.propose(context)
        verification = ExactProgramVerifier(authority=runtime.authority).verify_candidates(proposal, context)
        assert verification.selected_meaning is not None, proposal.abstention_code
        assert verification.selected_meaning.expression == _expected_person_membership()
        assert verification.candidate_receipts[0].coverage_receipt.executable
        assert not proposal.truncated
        assert pack_path.read_bytes() == before_pack
        assert runtime.stores.world.revision == 0 and runtime.stores.r3_world_facts() == ()
    finally:
        runtime.stores.close()
