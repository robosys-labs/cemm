"""Unsupported quotation is source evidence, never a performed greeting."""

from pathlib import Path
import json

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.coverage import CoverageVerifier
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.proposal_context import _residual_evidence


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("source,quote_refs", (
    ('"hello"', ("unit:0", "unit:2")),
    ("'hello'", ("unit:0", "unit:2")),
    ('"hello', ("unit:0",)),
    ('hello"', ("unit:1",)),
    ('Alice said "hello".', ("unit:4", "unit:6")),
    ('"velnora means mother', ("unit:0",)),
    ('learn "velnora means mother', ("unit:2",)),
    ('what does "mother" mean?', ("unit:4", "unit:6")),
), ids=("double-mention", "single-mention", "unclosed-open", "unclosed-close",
        "quoted-report", "quoted-naming", "quoted-directive", "quoted-lookup"))
def test_unsupported_quotation_retains_critical_source_evidence(tmp_path, source, quote_refs):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        _, context = runtime.orient("session:quotation-evidence", source)
        assert tuple(row.source_unit_ref for row in context.residual_evidence
                     if row.critical and row.source_unit_ref in quote_refs) == quote_refs
        for ref in quote_refs:
            residual = context.residual_for_source(ref)
            assert residual.contribution_kind == "discourse"
            slots = context.contributions_for_source(ref)
            assert len(slots) == 1
            assert slots[0].constraints == (("orthography", "quotation_boundary"),)
            assert slots[0].target_ref is None
            assert not slots[0].input_ports and not slots[0].output_ports
        result = runtime.process("session:quotation-runtime", source)
        assert result.verification.selected_meaning is None
        assert result.evaluation is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,source,quote_refs", (
    ("en", '"hello"', ("unit:0", "unit:2")),
    ("en", "'hello'", ("unit:0", "unit:2")),
    ("es", '"hola"', ("unit:0", "unit:2")),
    ("es", "'hola'", ("unit:0", "unit:2")),
), ids=("english-double", "english-single", "spanish-double", "spanish-single"))
def test_reviewed_pack_quotation_boundaries_reconstruct_typed_residuals(language, source, quote_refs):
    pack = json.loads((ROOT / "data" / "languages" / language / "forms.json").read_text(encoding="utf-8"))
    lattice = FormResolver(pack, RuntimeConfig.release()).resolve(source)
    assert "".join(unit.source_text for unit in lattice.units) == source
    units = {unit.unit_ref: unit for unit in lattice.units}
    for ref in quote_refs:
        unit = units[ref]
        assert pack["orthography"].get(unit.source_text, {}).get("kind") == "quotation_boundary"
        assert unit.features == (("orthography", "quotation_boundary"),)
    residuals = _residual_evidence(lattice, set())
    assert tuple(row.source_unit_ref for row in residuals
                 if row.critical and row.contribution_kind == "discourse") == quote_refs


@pytest.mark.parametrize("source,expected_predicate", (
    ("hello", "event:greeting"),
    ("hello!", "event:greeting"),
    ("Alice said hello.", "event:say"),
    ("Alice said: hello.", "event:say"),
    ("velnora means mother", "label:lexical"),
    ("learn velnora means mother", "event:learn_alias"),
    ("what does mother mean?", "label:lexical"),
), ids=("bare-greeting", "ordinary-punctuation", "unquoted-report", "report-colon",
        "naming-literal", "learning-literal", "lexical-lookup"))
def test_quotation_containment_preserves_reviewed_unquoted_controls(tmp_path, source, expected_predicate):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        result = runtime.process("session:quotation-controls", source)
        meaning = result.verification.selected_meaning
        assert meaning is not None
        assert expected_predicate in {row.predicate_ref for row in meaning.expression.applications}
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("corruption", ("drop", "demote"), ids=("drop", "demote"))
def test_independent_coverage_rejects_quotation_residual_tampering(tmp_path, corruption):
    from cemm_authoritative_hybrid.programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
    from cemm_authoritative_hybrid.proposal import ProposalResult, RankedProgramCandidate
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        _, context = runtime.orient("session:quotation-tamper", '"hello"')
        # An adversarial proposer attempts the unsupported performed greeting.
        # Select source-local reviewed slots, but never borrow a runtime result
        # as the expected meaning or rely on the bootstrap abstention as proof.
        frame = next(row for row in context.application_frames if row.predicate_target_ref == "event:greeting")
        designation = next(row for row in context.designation_slots if row.target_ref == "event:greeting")
        predicate = next(row for row in context.contribution_slots
            if row.kind == "predicate" and row.target_ref == "event:greeting"
            and row.source_unit_refs == ("unit:1",))
        actor = next(row for row in context.reference_slots if row.target_ref == "participant:user")
        addressee = next(row for row in context.reference_slots if row.target_ref == "participant:system")
        actions = tuple(ProgramAction.create(action_index=index, action_type=kind, arguments=args,
            source_unit_refs=sources) for index, (kind, args, sources) in enumerate((
                ("select_context", (context.context_ref,), ()),
                ("select_mode", (context.mode_slots[0].slot_ref,), ()),
                ("select_designation", (designation.slot_ref,), ()),
                ("instantiate_operator", ("application:0", frame.slot_ref), ("unit:1",)),
                ("bind_reference", ("application:0", "role:actor", actor.slot_ref), ()),
                ("bind_reference", ("application:0", "role:addressee", addressee.slot_ref), ()),
                ("complete_program", (), ()),
            )))
        assignments = tuple(SourceAssignment.create(source_unit_ref=row.source_unit_ref,
            contribution_slot_ref=row.residual_ref, assignment_kind="residual",
            target_action_ref=None, target_role_ref=None,
            residual_kind=row.contribution_kind, critical=row.critical) for row in context.residual_evidence)
        assignments = (*assignments, SourceAssignment.create(source_unit_ref="unit:1",
            contribution_slot_ref=predicate.slot_ref, assignment_kind="predicate",
            target_action_ref=actions[3].action_ref, target_role_ref=None,
            residual_kind=None, critical=True))
        by_source = {row.source_unit_ref: row for row in assignments}
        assignments = tuple(by_source[ref] for ref in context.source_unit_refs)
        program = SemanticSwitchProgram.create(orientation_ref=context.orientation_ref,
            proposal_context_ref=context.context_ref, actions=actions, root_refs=("application:0",),
            mode_slot_ref=context.mode_slots[0].slot_ref, goal_refs=(),
            source_unit_refs=context.source_unit_refs, source_assignments=assignments,
            revision_pin=context.revision_pin)
        coverage = CoverageVerifier().verify(context, program)
        assert tuple(row.source_unit_ref for row in coverage.critical_residuals) == ("unit:0", "unit:2")
        assert not coverage.executable
        assignments = tuple(
            SourceAssignment.create(source_unit_ref=row.source_unit_ref,
                contribution_slot_ref=row.contribution_slot_ref,
                assignment_kind=row.assignment_kind,
                target_action_ref=row.target_action_ref, target_role_ref=row.target_role_ref,
                residual_kind=row.residual_kind, critical=False)
            if corruption == "demote" and row.source_unit_ref in {"unit:0", "unit:2"} else row
            for row in program.source_assignments
            if corruption != "drop" or row.source_unit_ref not in {"unit:0", "unit:2"})
        forged = SemanticSwitchProgram.create(orientation_ref=program.orientation_ref,
            proposal_context_ref=program.proposal_context_ref, actions=program.actions,
            root_refs=program.root_refs, mode_slot_ref=program.mode_slot_ref,
            goal_refs=program.goal_refs, source_unit_refs=tuple(row.source_unit_ref for row in assignments),
            source_assignments=assignments, revision_pin=program.revision_pin)
        rejected = CoverageVerifier().verify(context, forged)
        assert not rejected.executable
        assert ("missing_source_unit" if corruption == "drop" else "false_residual_criticality") in {
            row.code for row in rejected.errors}
        candidate = RankedProgramCandidate.create(rank=0, score_q=1_000_000,
            program=forged, provenance_refs=("fixture:unsupported-quotation",))
        proposal = ProposalResult.create(orientation_ref=context.orientation_ref,
            proposal_context_ref=context.context_ref, candidates=(candidate,), status="candidates",
            abstention_code=None, explored_states=1, truncated=False,
            model_identity=context.revision_pin.model_identity, revision_pin=context.revision_pin)
        verification = runtime._owners["verification"].verify_candidates(proposal, context)
        assert verification.selected_meaning is None
        assert {error.code for receipt in verification.candidate_receipts
                for error in receipt.verification_errors} == (
            {"missing_source_unit", "missing_source_assignment"} if corruption == "drop"
            else {"false_residual_criticality", "critical_residual"})
    finally:
        runtime.stores.close()


def test_consumed_source_claim_cannot_erase_uninterpreted_quotation():
    pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
    lattice = FormResolver(pack, RuntimeConfig.release()).resolve('"hello"')
    residuals = _residual_evidence(lattice, {"unit:0", "unit:1", "unit:2"})
    assert tuple((row.source_unit_ref, row.contribution_kind, row.critical) for row in residuals) == (
        ("unit:0", "discourse", True), ("unit:2", "discourse", True))


def test_designation_span_cannot_swallow_quotation_but_unquoted_alias_survives(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
    from cemm_authoritative_hybrid.r3_learning import AdmittedDesignationReader
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        # An explicit static authority fixture, not a fabricated publication or
        # a pack entry. Identity grounding does not license quote interpretation.
        original = tuple(runtime.authority.designations._facts_by_ref.values())
        quoted = DesignationFact.create(surface='"hello"', target_ref="event:greeting", language="en")
        alias = DesignationFact.create(surface="luz nuvemora", target_ref="event:greeting", language="en")
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex((*original, quoted, alias)))
        monkeypatch.setattr(runtime._owners["orientation"], "_designation_reader",
            AdmittedDesignationReader(runtime.authority, runtime.stores))
        _, context = runtime.orient("session:quoted-alias", '"hello"')
        assert context.critical_residual_unit_refs == ("unit:0", "unit:2")
        assert all(not {"unit:0", "unit:2"} & set(row.source_unit_refs)
                   for row in context.contribution_slots if row.target_ref is not None)
        assert runtime.process("session:quoted-alias-result", '"hello"').verification.selected_meaning is None
        result = runtime.process("session:plain-alias", "luz nuvemora")
        assert result.verification.selected_meaning is not None
        assert "event:greeting" in {row.predicate_ref for row in result.verification.selected_meaning.expression.applications}
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("source", ('"velnora means mother', 'learn "velnora means mother',
    '"learn velnora means mother', '"learn that velnora means mother'),
    ids=("quoted-label", "quoted-directive-label", "quoted-predicate", "quoted-embedded-predicate"))
def test_unsupported_quotation_never_creates_a_stripped_naming_fragment(tmp_path, source):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        _, context = runtime.orient("session:quoted-naming-fragment", source)
        assert not any(row.kind == "literal" and row.literal_value == "velnora"
                       for row in context.contribution_slots)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("corruption", ("demote", "retype"), ids=("demote", "retype"))
def test_context_reconstruction_rejects_quotation_residual_metadata_tampering(tmp_path, corruption):
    from dataclasses import fields
    from cemm_authoritative_hybrid.proposal_context import ProposalContext, ResidualEvidence
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        _, context = runtime.orient("session:quotation-context-tamper", '"hello"')
        values = {field.name: getattr(context, field.name) for field in fields(context)
                  if field.init and field.name not in {"context_ref", "abi_version"}}
        values["residual_evidence"] = tuple(ResidualEvidence.create(
            source_unit_ref=row.source_unit_ref,
            contribution_kind="anchor" if corruption == "retype" else row.contribution_kind,
            critical=False if corruption == "demote" else row.critical,
            reason=row.reason) for row in context.residual_evidence)
        with pytest.raises(ValueError, match="quotation boundary requires critical discourse residual"):
            ProposalContext.create(**values)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("language,source", (
    ("en", "“hello”"), ("en", "‘hello’"), ("en", "«hello»"), ("en", "‹hello›"),
    ("es", "“hola”"), ("es", "‘hola’"), ("es", "«hola»"), ("es", "‹hola›"),
), ids=("english-curly-double", "english-curly-single", "english-guillemets", "english-single-guillemets",
        "spanish-curly-double", "spanish-curly-single", "spanish-guillemets", "spanish-single-guillemets"))
def test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries(language, source):
    pack = json.loads((ROOT / "data" / "languages" / language / "forms.json").read_text(encoding="utf-8"))
    lattice = FormResolver(pack, RuntimeConfig.release()).resolve(source)
    assert tuple(unit.source_text for unit in lattice.units) == (source[0], source[1:-1], source[-1])
    assert "".join(unit.source_text for unit in lattice.units) == source
    for unit in (lattice.units[0], lattice.units[-1]):
        assert unit.source_text in pack["tokenization"]["punctuation"]
        assert pack["orthography"][unit.source_text]["kind"] == "quotation_boundary"
        assert unit.features == (("orthography", "quotation_boundary"),)
    residuals = _residual_evidence(lattice, {"unit:0", "unit:1", "unit:2"})
    assert tuple((row.source_unit_ref, row.contribution_kind, row.critical) for row in residuals) == (
        ("unit:0", "discourse", True), ("unit:2", "discourse", True))


@pytest.mark.parametrize("source", ("“hello”", "‘hello’", "«hello»", "‹hello›"),
    ids=("curly-double", "curly-single", "guillemets", "single-guillemets"))
def test_unicode_quoted_designations_cannot_be_performed_greetings(tmp_path, monkeypatch, source):
    from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
    from cemm_authoritative_hybrid.r3_learning import AdmittedDesignationReader
    from cemm_authoritative_hybrid.expressions import (
        GroundedReference, RoleBinding, SemanticApplication, SemanticExpression,
    )
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        # Explicit static designation fixtures are not authenticated alias
        # publication and do not provide an owner for quotation interpretation.
        original = tuple(runtime.authority.designations._facts_by_ref.values())
        quoted = DesignationFact.create(surface=source, target_ref="event:greeting", language="en")
        alias = DesignationFact.create(surface="luz nuvemora", target_ref="event:greeting", language="en")
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex((*original, quoted, alias)))
        monkeypatch.setattr(runtime._owners["orientation"], "_designation_reader",
            AdmittedDesignationReader(runtime.authority, runtime.stores))
        _, context = runtime.orient("session:unicode-quoted-designation", source)
        assert context.critical_residual_unit_refs == ("unit:0", "unit:2")
        assert all(not {"unit:0", "unit:2"} & set(row.source_unit_refs)
                   for row in context.contribution_slots if row.target_ref is not None)
        result = runtime.process("session:unicode-quoted-result", source)
        assert result.verification.selected_meaning is None
        assert result.evaluation is None
        expected = SemanticApplication("application:expected", "op:event", "event:greeting", (
            RoleBinding("role:actor", GroundedReference("participant:user")),
            RoleBinding("role:addressee", GroundedReference("participant:system")),
        ))
        expected_expression = SemanticExpression.create(applications=(expected,), root_refs=(expected.application_ref,))
        for control in ("hello", "luz nuvemora"):
            result = runtime.process("session:unicode-quote-control", control)
            assert result.verification.selected_meaning.expression == expected_expression
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


__cemm_test_inventory__ = {
    "tests/test_foundation_quotation_evidence.py::test_consumed_source_claim_cannot_erase_uninterpreted_quotation": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:consumed-source-claim-cannot-erase-uninterpreted-quotation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "9222f366b579139fa4bf7b8f010ba12be5ff7e1bc02f65ecd306f5d491a809f6"
    },
    "tests/test_foundation_quotation_evidence.py::test_context_reconstruction_rejects_quotation_residual_metadata_tampering[demote]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:context-reconstruction-rejects-quotation-residual-metadata-tampering-demote",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "7acd78167d89ffb239bbbb49ace20da2561003e023d0e0d1a24a667dbd57cabf"
    },
    "tests/test_foundation_quotation_evidence.py::test_context_reconstruction_rejects_quotation_residual_metadata_tampering[retype]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:context-reconstruction-rejects-quotation-residual-metadata-tampering-retype",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "7acd78167d89ffb239bbbb49ace20da2561003e023d0e0d1a24a667dbd57cabf"
    },
    "tests/test_foundation_quotation_evidence.py::test_designation_span_cannot_swallow_quotation_but_unquoted_alias_survives": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:designation-span-cannot-swallow-quotation-but-unquoted-alias-survives",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "886bfcd3d8e78e2eb7cac11b41ae94a228398877c457b9655e8e3d50020caa4a"
    },
    "tests/test_foundation_quotation_evidence.py::test_independent_coverage_rejects_quotation_residual_tampering[demote]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:independent-coverage-rejects-quotation-residual-tampering-demote",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "53484519b7f8ef28d9e9f87c2a7558d183626518e613ebc172fb8004971e9cd0"
    },
    "tests/test_foundation_quotation_evidence.py::test_independent_coverage_rejects_quotation_residual_tampering[drop]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:independent-coverage-rejects-quotation-residual-tampering-drop",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "53484519b7f8ef28d9e9f87c2a7558d183626518e613ebc172fb8004971e9cd0"
    },
    "tests/test_foundation_quotation_evidence.py::test_quotation_containment_preserves_reviewed_unquoted_controls[bare-greeting]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-containment-preserves-reviewed-unquoted-controls-bare-greeting",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "516b573881bd684f99d853a39a80a80e9adbbf6fe9119c9f5d48886312e056e7"
    },
    "tests/test_foundation_quotation_evidence.py::test_quotation_containment_preserves_reviewed_unquoted_controls[learning-literal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-containment-preserves-reviewed-unquoted-controls-learning-literal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "516b573881bd684f99d853a39a80a80e9adbbf6fe9119c9f5d48886312e056e7"
    },
    "tests/test_foundation_quotation_evidence.py::test_quotation_containment_preserves_reviewed_unquoted_controls[lexical-lookup]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-containment-preserves-reviewed-unquoted-controls-lexical-lookup",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "516b573881bd684f99d853a39a80a80e9adbbf6fe9119c9f5d48886312e056e7"
    },
    "tests/test_foundation_quotation_evidence.py::test_quotation_containment_preserves_reviewed_unquoted_controls[naming-literal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-containment-preserves-reviewed-unquoted-controls-naming-literal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "516b573881bd684f99d853a39a80a80e9adbbf6fe9119c9f5d48886312e056e7"
    },
    "tests/test_foundation_quotation_evidence.py::test_quotation_containment_preserves_reviewed_unquoted_controls[ordinary-punctuation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-containment-preserves-reviewed-unquoted-controls-ordinary-punctuation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "516b573881bd684f99d853a39a80a80e9adbbf6fe9119c9f5d48886312e056e7"
    },
    "tests/test_foundation_quotation_evidence.py::test_quotation_containment_preserves_reviewed_unquoted_controls[report-colon]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-containment-preserves-reviewed-unquoted-controls-report-colon",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "516b573881bd684f99d853a39a80a80e9adbbf6fe9119c9f5d48886312e056e7"
    },
    "tests/test_foundation_quotation_evidence.py::test_quotation_containment_preserves_reviewed_unquoted_controls[unquoted-report]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-containment-preserves-reviewed-unquoted-controls-unquoted-report",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "516b573881bd684f99d853a39a80a80e9adbbf6fe9119c9f5d48886312e056e7"
    },
    "tests/test_foundation_quotation_evidence.py::test_reviewed_pack_quotation_boundaries_reconstruct_typed_residuals[english-double]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:reviewed-pack-quotation-boundaries-reconstruct-typed-residuals-english-double",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d67f03dbfe2abc7e691668f7d60845a1343eb9df57099794282fb105c0ba17dc"
    },
    "tests/test_foundation_quotation_evidence.py::test_reviewed_pack_quotation_boundaries_reconstruct_typed_residuals[english-single]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:reviewed-pack-quotation-boundaries-reconstruct-typed-residuals-english-single",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d67f03dbfe2abc7e691668f7d60845a1343eb9df57099794282fb105c0ba17dc"
    },
    "tests/test_foundation_quotation_evidence.py::test_reviewed_pack_quotation_boundaries_reconstruct_typed_residuals[spanish-double]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:reviewed-pack-quotation-boundaries-reconstruct-typed-residuals-spanish-double",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d67f03dbfe2abc7e691668f7d60845a1343eb9df57099794282fb105c0ba17dc"
    },
    "tests/test_foundation_quotation_evidence.py::test_reviewed_pack_quotation_boundaries_reconstruct_typed_residuals[spanish-single]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:reviewed-pack-quotation-boundaries-reconstruct-typed-residuals-spanish-single",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d67f03dbfe2abc7e691668f7d60845a1343eb9df57099794282fb105c0ba17dc"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[english-curly-double]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-english-curly-double",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[english-curly-single]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-english-curly-single",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[english-guillemets]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-english-guillemets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[english-single-guillemets]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-english-single-guillemets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[spanish-curly-double]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-spanish-curly-double",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[spanish-curly-single]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-spanish-curly-single",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[spanish-guillemets]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-spanish-guillemets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quotation_delimiters_are_reviewed_reversible_form_boundaries[spanish-single-guillemets]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quotation-delimiters-are-reviewed-reversible-form-boundaries-spanish-single-guillemets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "94565e26562ca1b7f0b45b4856b9ea54273c547b70d71192f6e827abb7adecb0"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quoted_designations_cannot_be_performed_greetings[curly-double]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quoted-designations-cannot-be-performed-greetings-curly-double",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "215c2586e72a249698ca2615ad42268aea62933af1855bc1b4d6ea9a90b173ff"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quoted_designations_cannot_be_performed_greetings[curly-single]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quoted-designations-cannot-be-performed-greetings-curly-single",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "215c2586e72a249698ca2615ad42268aea62933af1855bc1b4d6ea9a90b173ff"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quoted_designations_cannot_be_performed_greetings[guillemets]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quoted-designations-cannot-be-performed-greetings-guillemets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "215c2586e72a249698ca2615ad42268aea62933af1855bc1b4d6ea9a90b173ff"
    },
    "tests/test_foundation_quotation_evidence.py::test_unicode_quoted_designations_cannot_be_performed_greetings[single-guillemets]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unicode-quoted-designations-cannot-be-performed-greetings-single-guillemets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "215c2586e72a249698ca2615ad42268aea62933af1855bc1b4d6ea9a90b173ff"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_never_creates_a_stripped_naming_fragment[quoted-directive-label]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-never-creates-a-stripped-naming-fragment-quoted-directive-label",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f6bb39bd98a300bfe29b1e78f4f5ce30562486b91de96a4f3802a3d5b6cc9a68"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_never_creates_a_stripped_naming_fragment[quoted-embedded-predicate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-never-creates-a-stripped-naming-fragment-quoted-embedded-predicate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f6bb39bd98a300bfe29b1e78f4f5ce30562486b91de96a4f3802a3d5b6cc9a68"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_never_creates_a_stripped_naming_fragment[quoted-label]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-never-creates-a-stripped-naming-fragment-quoted-label",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f6bb39bd98a300bfe29b1e78f4f5ce30562486b91de96a4f3802a3d5b6cc9a68"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_never_creates_a_stripped_naming_fragment[quoted-predicate]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-never-creates-a-stripped-naming-fragment-quoted-predicate",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f6bb39bd98a300bfe29b1e78f4f5ce30562486b91de96a4f3802a3d5b6cc9a68"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[double-mention]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-double-mention",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[quoted-directive]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-quoted-directive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[quoted-lookup]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-quoted-lookup",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[quoted-naming]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-quoted-naming",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[quoted-report]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-quoted-report",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[single-mention]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-single-mention",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[unclosed-close]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-unclosed-close",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    },
    "tests/test_foundation_quotation_evidence.py::test_unsupported_quotation_retains_critical_source_evidence[unclosed-open]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unsupported-quotation-retains-critical-source-evidence-unclosed-open",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-C1",
        "owner_ref": "situation-context",
        "source_ast_sha256": "d007ea9c4bb39bdb385c7a54f30d31e21f087250ac00c706dccf5ea57ded8d6e"
    }
}
