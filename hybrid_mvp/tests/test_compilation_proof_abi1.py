"""Compilation Proof ABI 1 retained exact translation evidence."""

from __future__ import annotations

from dataclasses import fields

import pytest

from cemm_authoritative_hybrid.expressions import CompilationProof, TranslationRow
from cemm_authoritative_hybrid.persistence import RevisionPin


def _pin(**changes: object) -> RevisionPin:
    values = {
        "authority_generation": "authority:g1",
        "world_revision": 1,
        "session_revision": 2,
        "episode_revision": 3,
        "effect_revision": 4,
        "model_identity": "model:m1",
    }
    values.update(changes)
    return RevisionPin(**values)  # type: ignore[arg-type]


def _proof(
    *,
    expression_ref: str = "expression:one",
    revision_pin: RevisionPin | None = None,
) -> CompilationProof:
    return CompilationProof.create(
        program_ref="program:one",
        proposal_context_ref="proposal_context:one",
        expression_ref=expression_ref,
        action_translations=(
            TranslationRow("program_action:0", "validated", ("proposal_context:one",)),
            TranslationRow("program_action:1", "translated", ("application:0",)),
        ),
        assignment_translations=(
            TranslationRow("source_assignment:0", "translated", ("application:0", "role:actor")),
        ),
        root_translations=(
            TranslationRow("application:main", "translated", ("application:0",)),
        ),
        grounding_refs=("entity:alice", "event:teach"),
        revision_pin=revision_pin or _pin(),
    )


def test_compilation_proof_retains_rows_and_excludes_hidden_program_or_context() -> None:
    proof = _proof()
    names = {field.name for field in fields(CompilationProof)}
    assert "program" not in names
    assert "proposal_context" not in names
    assert proof.action_translations[0].source_ref == "program_action:0"
    assert proof.assignment_translations[0].target_refs[-1] == "role:actor"


def test_compilation_proof_ref_covers_expression_rows_grounding_and_revision() -> None:
    base = _proof()
    changed_expression = _proof(expression_ref="expression:two")
    changed_pin = _proof(revision_pin=_pin(world_revision=9))
    assert changed_expression.proof_ref != base.proof_ref
    assert changed_pin.proof_ref != base.proof_ref

    changed_rows = CompilationProof.create(
        program_ref=base.program_ref,
        proposal_context_ref=base.proposal_context_ref,
        expression_ref=base.expression_ref,
        action_translations=tuple(reversed(base.action_translations)),
        assignment_translations=base.assignment_translations,
        root_translations=base.root_translations,
        grounding_refs=base.grounding_refs,
        revision_pin=base.revision_pin,
    )
    assert changed_rows.proof_ref != base.proof_ref


@pytest.mark.parametrize(
    "domain",
    ("action_translations", "assignment_translations", "root_translations"),
    ids=("actions", "assignments", "roots"),
)
def test_compilation_proof_rejects_duplicate_domain_sources(domain: str) -> None:
    proof = _proof()
    values = {
        "program_ref": proof.program_ref,
        "proposal_context_ref": proof.proposal_context_ref,
        "expression_ref": proof.expression_ref,
        "action_translations": proof.action_translations,
        "assignment_translations": proof.assignment_translations,
        "root_translations": proof.root_translations,
        "grounding_refs": proof.grounding_refs,
        "revision_pin": proof.revision_pin,
    }
    values[domain] = (getattr(proof, domain)[0], getattr(proof, domain)[0])
    with pytest.raises(ValueError, match="duplicate"):
        CompilationProof.create(**values)  # type: ignore[arg-type]


def test_compilation_proof_round_trip_rejects_forged_refs_and_nested_pin_tamper() -> None:
    with pytest.raises(TypeError):
        CompilationProof()  # type: ignore[call-arg]
    proof = _proof()
    assert CompilationProof.from_dict(proof.as_dict()) == proof
    with pytest.raises(TypeError):
        CompilationProof(  # type: ignore[call-arg]
            "proof:forged", proof.program_ref, proof.proposal_context_ref,
            proof.expression_ref, proof.action_translations,
            proof.assignment_translations, proof.root_translations,
            proof.grounding_refs, proof.revision_pin,
        )

    payload = proof.as_dict()
    payload["action_translations"][0]["target_refs"][0] = "proposal_context:other"
    with pytest.raises(ValueError, match="proof_ref mismatch"):
        CompilationProof.from_dict(payload)

    payload = proof.as_dict()
    payload["revision_pin"]["episode_revision"] = True
    with pytest.raises((TypeError, ValueError), match="episode_revision"):
        CompilationProof.from_dict(payload)

__cemm_test_inventory__ = {'tests/test_compilation_proof_abi1.py::test_compilation_proof_ref_covers_expression_rows_grounding_and_revision': {'activation_phase': 'R1',
                                                                                                                    'assertion_ref': 'assertion:r1-compilation-proof-abi1-test-compilation-proof-ref-covers-expression-rows-grounding-and-revision',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                                    'owner_ref': 'program-verifier',
                                                                                                                    'source_ast_sha256': '58a94c9913f582728e59ba6bb4535d73bdcf795e7b94d44de34807a954758032'},
 'tests/test_compilation_proof_abi1.py::test_compilation_proof_rejects_duplicate_domain_sources[actions]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-compilation-proof-abi1-test-compilation-proof-rejects-duplicate-domain-sources-actions',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': '8937db381d1d79d4ca3dd53dcb59266c8553e598cac5bdf1d84be7f9ea063c63'},
 'tests/test_compilation_proof_abi1.py::test_compilation_proof_rejects_duplicate_domain_sources[assignments]': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:r1-compilation-proof-abi1-test-compilation-proof-rejects-duplicate-domain-sources-assignments',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                'source_ast_sha256': '8937db381d1d79d4ca3dd53dcb59266c8553e598cac5bdf1d84be7f9ea063c63'},
 'tests/test_compilation_proof_abi1.py::test_compilation_proof_rejects_duplicate_domain_sources[roots]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-compilation-proof-abi1-test-compilation-proof-rejects-duplicate-domain-sources-roots',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': '8937db381d1d79d4ca3dd53dcb59266c8553e598cac5bdf1d84be7f9ea063c63'},
 'tests/test_compilation_proof_abi1.py::test_compilation_proof_retains_rows_and_excludes_hidden_program_or_context': {'activation_phase': 'R1',
                                                                                                                      'assertion_ref': 'assertion:r1-compilation-proof-abi1-test-compilation-proof-retains-rows-and-excludes-hidden-program-or-context',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                                      'owner_ref': 'program-verifier',
                                                                                                                      'source_ast_sha256': 'fd3a139f5e4c890ea556fd44ba059e799020bb89982fcf8d22081f24da645001'},
 'tests/test_compilation_proof_abi1.py::test_compilation_proof_round_trip_rejects_forged_refs_and_nested_pin_tamper': {'activation_phase': 'R1',
                                                                                                                       'assertion_ref': 'assertion:r1-compilation-proof-abi1-test-compilation-proof-round-trip-rejects-forged-refs-and-nested-pin-tamper',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                                       'owner_ref': 'program-verifier',
                                                                                                                       'source_ast_sha256': 'ec15acb67fd197adfb9da243b15f5b441754d4d3047950b13024f64ca0c1e04c'}}
