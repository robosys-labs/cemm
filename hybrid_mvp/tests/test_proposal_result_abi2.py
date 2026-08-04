"""Proposal Result ABI 2 exact identity and canonical wire tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)
from cemm_authoritative_hybrid.proposal import (
    PROPOSAL_RESULT_ABI_VERSION,
    ProposalResult,
    RankedProgramCandidate,
)


def _pin(**changes: object) -> RevisionPin:
    values = {
        "authority_generation": "authority:generation-1",
        "world_revision": 1,
        "session_revision": 2,
        "episode_revision": 3,
        "effect_revision": 4,
        "model_identity": "model:one",
    }
    values.update(changes)
    return RevisionPin(**values)  # type: ignore[arg-type]


def _action(
    action_index: int,
    action_type: str,
    arguments: tuple[str, ...],
    source_unit_refs: tuple[str, ...] = (),
) -> ProgramAction:
    return ProgramAction.create(
        action_index=action_index,
        action_type=action_type,
        arguments=arguments,
        source_unit_refs=source_unit_refs,
    )


def _program(
    *,
    orientation_ref: str = "orientation:one",
    proposal_context_ref: str = "proposal_context:one",
    revision_pin: RevisionPin | None = None,
    designation_slot_ref: str = "designation_slot:alice",
) -> SemanticSwitchProgram:
    pin = revision_pin or _pin()
    mode_slot_ref = "mode_slot:observe"
    actions = (
        _action(0, "select_context", (proposal_context_ref,)),
        _action(1, "select_mode", (mode_slot_ref,)),
        _action(
            2,
            "select_designation",
            (designation_slot_ref,),
            ("unit:alice",),
        ),
        _action(
            3,
            "instantiate_operator",
            ("application:main", "application_frame_slot:main"),
            ("unit:teaches",),
        ),
        _action(
            4,
            "bind_role",
            ("application:main", "role:actor", "contribution_slot:alice"),
            ("unit:alice",),
        ),
        _action(5, "complete_program", ()),
    )
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:alice",
            contribution_slot_ref="contribution_slot:alice",
            assignment_kind="role",
            target_action_ref=actions[4].action_ref,
            target_role_ref="role:actor",
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:teaches",
            contribution_slot_ref="contribution_slot:teaches",
            assignment_kind="predicate",
            target_action_ref=actions[3].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=True,
        ),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=orientation_ref,
        proposal_context_ref=proposal_context_ref,
        actions=actions,
        root_refs=("application:main",),
        mode_slot_ref=mode_slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=("unit:alice", "unit:teaches"),
        source_assignments=assignments,
        revision_pin=pin,
    )


def _abstain_program() -> SemanticSwitchProgram:
    context_ref = "proposal_context:one"
    mode_slot_ref = "mode_slot:observe"
    return SemanticSwitchProgram.create(
        orientation_ref="orientation:one",
        proposal_context_ref=context_ref,
        actions=(
            _action(0, "select_context", (context_ref,)),
            _action(1, "select_mode", (mode_slot_ref,)),
            _action(2, "abstain", ()),
        ),
        root_refs=(),
        mode_slot_ref=mode_slot_ref,
        goal_refs=(),
        source_unit_refs=(),
        source_assignments=(),
        revision_pin=_pin(),
    )


def _candidate(
    *,
    rank: int = 0,
    score_q: int = 100,
    program: SemanticSwitchProgram | None = None,
    provenance_refs: tuple[str, ...] = ("evidence:one",),
) -> RankedProgramCandidate:
    return RankedProgramCandidate.create(
        rank=rank,
        score_q=score_q,
        program=program or _program(),
        provenance_refs=provenance_refs,
    )


def _candidate_result(
    *,
    orientation_ref: str = "orientation:one",
    proposal_context_ref: str = "proposal_context:one",
    score_q: int = 100,
    provenance_refs: tuple[str, ...] = ("evidence:one",),
    explored_states: int = 7,
    truncated: bool = False,
    model_identity: str = "model:one",
    revision_pin: RevisionPin | None = None,
    designation_slot_ref: str = "designation_slot:alice",
) -> ProposalResult:
    pin = revision_pin or _pin(model_identity=model_identity)
    program = _program(
        orientation_ref=orientation_ref,
        proposal_context_ref=proposal_context_ref,
        revision_pin=pin,
        designation_slot_ref=designation_slot_ref,
    )
    candidate = _candidate(
        score_q=score_q,
        program=program,
        provenance_refs=provenance_refs,
    )
    return ProposalResult.create(
        orientation_ref=orientation_ref,
        proposal_context_ref=proposal_context_ref,
        candidates=(candidate,),
        status="candidates",
        abstention_code=None,
        explored_states=explored_states,
        truncated=truncated,
        model_identity=model_identity,
        revision_pin=pin,
    )


def _abstained_result(code: str = "frontier_exhausted") -> ProposalResult:
    pin = _pin()
    return ProposalResult.create(
        orientation_ref="orientation:one",
        proposal_context_ref="proposal_context:one",
        candidates=(),
        status="abstained",
        abstention_code=code,
        explored_states=7,
        truncated=False,
        model_identity="model:one",
        revision_pin=pin,
    )


def test_proposal_result_abi2_owns_only_strict_canonical_fields() -> None:
    assert PROPOSAL_RESULT_ABI_VERSION == 2
    assert tuple(field.name for field in fields(RankedProgramCandidate)) == (
        "candidate_ref",
        "rank",
        "score_q",
        "program",
        "provenance_refs",
    )
    assert tuple(field.name for field in fields(ProposalResult)) == (
        "proposal_ref",
        "orientation_ref",
        "proposal_context_ref",
        "candidates",
        "status",
        "abstention_code",
        "explored_states",
        "truncated",
        "model_identity",
        "revision_pin",
    )
    with pytest.raises(TypeError):
        RankedProgramCandidate()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ProposalResult()  # type: ignore[call-arg]


def test_proposal_result_round_trip_preserves_complete_nested_batch() -> None:
    result = _candidate_result()
    restored = ProposalResult.from_dict(result.as_dict())

    assert restored == result
    assert restored.output_refs == (restored.proposal_ref,)
    assert not hasattr(restored, "program")
    assert restored.candidate_by_ref(restored.candidates[0].candidate_ref) is restored.candidates[0]
    with pytest.raises(KeyError):
        restored.candidate_by_ref("proposal_candidate:missing")
    assert restored.as_dict()["revision_pin"] == result.revision_pin.as_dict()


def test_ranked_candidate_rejects_abstention_program() -> None:
    with pytest.raises(ValueError, match="completed program"):
        _candidate(program=_abstain_program())


def test_ranked_candidate_identity_covers_every_semantic_field() -> None:
    program = _program()
    base = _candidate(program=program)
    variants = (
        _candidate(rank=1, program=program),
        _candidate(score_q=101, program=program),
        _candidate(
            program=_program(designation_slot_ref="designation_slot:bob"),
        ),
        _candidate(program=program, provenance_refs=("evidence:two",)),
    )
    assert len({base.candidate_ref, *(item.candidate_ref for item in variants)}) == 5


def test_proposal_identity_covers_every_semantic_field() -> None:
    base = _candidate_result()
    revised_pin = _pin(world_revision=9)
    variants = (
        _candidate_result(orientation_ref="orientation:two"),
        _candidate_result(proposal_context_ref="proposal_context:two"),
        _candidate_result(score_q=101),
        _candidate_result(provenance_refs=("evidence:two",)),
        _candidate_result(explored_states=8),
        _candidate_result(truncated=True),
        _candidate_result(model_identity="model:two"),
        _candidate_result(revision_pin=revised_pin),
        _abstained_result("frontier_exhausted"),
        _abstained_result("budget_exhausted"),
    )
    assert len({base.proposal_ref, *(item.proposal_ref for item in variants)}) == 11


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("rank", True),
        ("rank", 1.0),
        ("rank", -1),
        ("rank", RuntimeConfig.release().max_complete_candidates),
        ("score_q", True),
        ("score_q", 1.0),
        ("score_q", 2**63),
    ),
    ids=(
        "rank-bool",
        "rank-float",
        "rank-negative",
        "rank-over-bound",
        "score-bool",
        "score-float",
        "score-over-bound",
    ),
)
def test_ranked_candidate_rejects_noncanonical_scalars(field: str, value: object) -> None:
    values = {
        "rank": 0,
        "score_q": 100,
        "program": _program(),
        "provenance_refs": ("evidence:one",),
    }
    values[field] = value
    with pytest.raises(ValueError):
        RankedProgramCandidate.create(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "provenance_refs",
    (
        ("",),
        ("evidence:one", "evidence:one"),
        tuple(f"evidence:{index}" for index in range(65)),
    ),
    ids=("empty-ref", "duplicate-ref", "over-bound"),
)
def test_ranked_candidate_rejects_noncanonical_provenance(
    provenance_refs: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError):
        _candidate(provenance_refs=provenance_refs)


def test_proposal_preserves_rank_order_without_program_ref_sorting() -> None:
    programs = tuple(
        sorted(
            (
                _program(designation_slot_ref="designation_slot:alice"),
                _program(designation_slot_ref="designation_slot:bob"),
            ),
            key=lambda program: program.program_ref,
            reverse=True,
        )
    )
    candidates = tuple(
        _candidate(rank=rank, score_q=100 - rank, program=program)
        for rank, program in enumerate(programs)
    )
    result = ProposalResult.create(
        orientation_ref="orientation:one",
        proposal_context_ref="proposal_context:one",
        candidates=candidates,
        status="candidates",
        abstention_code=None,
        explored_states=7,
        truncated=False,
        model_identity="model:one",
        revision_pin=_pin(),
    )

    assert tuple(item.program.program_ref for item in result.candidates) == tuple(
        item.program_ref for item in programs
    )
    with pytest.raises(ValueError, match="contiguous"):
        ProposalResult.create(
            orientation_ref="orientation:one",
            proposal_context_ref="proposal_context:one",
            candidates=tuple(reversed(candidates)),
            status="candidates",
            abstention_code=None,
            explored_states=7,
            truncated=False,
            model_identity="model:one",
            revision_pin=_pin(),
        )


@pytest.mark.parametrize(
    ("status", "candidates", "abstention_code"),
    (
        ("candidates", (), None),
        ("candidates", None, "not_allowed"),
        ("abstained", None, "frontier_exhausted"),
        ("abstained", (), None),
        ("abstained", (), ""),
        ("unknown", (), None),
    ),
    ids=(
        "candidates-empty",
        "candidates-with-code",
        "abstained-with-candidate",
        "abstained-without-code",
        "abstained-empty-code",
        "unknown-status",
    ),
)
def test_proposal_rejects_incoherent_status_contract(
    status: str,
    candidates: tuple[RankedProgramCandidate, ...] | None,
    abstention_code: str | None,
) -> None:
    candidate_tuple = (_candidate(),) if candidates is None else candidates
    with pytest.raises(ValueError):
        ProposalResult.create(
            orientation_ref="orientation:one",
            proposal_context_ref="proposal_context:one",
            candidates=candidate_tuple,
            status=status,  # type: ignore[arg-type]
            abstention_code=abstention_code,
            explored_states=7,
            truncated=False,
            model_identity="model:one",
            revision_pin=_pin(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("explored_states", True),
        ("explored_states", 1.0),
        ("explored_states", -1),
        (
            "explored_states",
            RuntimeConfig.release().max_beam_states
            * RuntimeConfig.release().max_applications
            + 1,
        ),
        ("truncated", 0),
        ("truncated", 1),
    ),
    ids=(
        "explored-bool",
        "explored-float",
        "explored-negative",
        "explored-over-bound",
        "truncated-zero",
        "truncated-one",
    ),
)
def test_proposal_rejects_noncanonical_search_scalars(field: str, value: object) -> None:
    values = {
        "orientation_ref": "orientation:one",
        "proposal_context_ref": "proposal_context:one",
        "candidates": (_candidate(),),
        "status": "candidates",
        "abstention_code": None,
        "explored_states": 7,
        "truncated": False,
        "model_identity": "model:one",
        "revision_pin": _pin(),
    }
    values[field] = value
    with pytest.raises(ValueError):
        ProposalResult.create(**values)  # type: ignore[arg-type]


def test_proposal_rejects_orientation_context_model_and_revision_mismatch() -> None:
    candidate = _candidate()
    common = {
        "candidates": (candidate,),
        "status": "candidates",
        "abstention_code": None,
        "explored_states": 7,
        "truncated": False,
        "model_identity": "model:one",
        "revision_pin": _pin(),
    }
    with pytest.raises(ValueError, match="orientation"):
        ProposalResult.create(
            orientation_ref="orientation:other",
            proposal_context_ref="proposal_context:one",
            **common,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="context"):
        ProposalResult.create(
            orientation_ref="orientation:one",
            proposal_context_ref="proposal_context:other",
            **common,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="model"):
        ProposalResult.create(
            orientation_ref="orientation:one",
            proposal_context_ref="proposal_context:one",
            **{**common, "model_identity": "model:other"},  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="revision"):
        ProposalResult.create(
            orientation_ref="orientation:one",
            proposal_context_ref="proposal_context:one",
            **{**common, "revision_pin": _pin(world_revision=9)},  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "mutator",
    (
        lambda data: {key: value for key, value in data.items() if key != "candidate_ref"},
        lambda data: {**data, "unknown": "value"},
        lambda data: {**data, "candidate_ref": "proposal_candidate:forged"},
        lambda data: {**data, "score_q": True},
        lambda data: {**data, "provenance_refs": tuple(data["provenance_refs"])},
        lambda data: {
            **data,
            "program": {**data["program"], "program_ref": "program:forged"},
        },
    ),
    ids=(
        "missing-field",
        "unknown-field",
        "candidate-ref",
        "score-bool",
        "tuple-provenance",
        "nested-program-ref",
    ),
)
def test_ranked_candidate_deserializer_rejects_noncanonical_or_tampered_wire(
    mutator,
) -> None:
    wire = _candidate().as_dict()
    with pytest.raises((TypeError, ValueError)):
        RankedProgramCandidate.from_dict(mutator(deepcopy(wire)))


@pytest.mark.parametrize(
    "mutator",
    (
        lambda data: {key: value for key, value in data.items() if key != "proposal_ref"},
        lambda data: {**data, "unknown": "value"},
        lambda data: {**data, "proposal_ref": "proposal:forged"},
        lambda data: {**data, "candidates": tuple(data["candidates"])},
        lambda data: {
            **data,
            "candidates": [
                {
                    **data["candidates"][0],
                    "candidate_ref": "proposal_candidate:forged",
                }
            ],
        },
        lambda data: {
            **data,
            "candidates": [
                {
                    **data["candidates"][0],
                    "program": {
                        **data["candidates"][0]["program"],
                        "program_ref": "program:forged",
                    },
                }
            ],
        },
        lambda data: {
            **data,
            "revision_pin": {**data["revision_pin"], "world_revision": 99},
        },
        lambda data: {**data, "orientation_ref": "orientation:forged"},
    ),
    ids=(
        "missing-field",
        "unknown-field",
        "proposal-ref",
        "tuple-candidates",
        "nested-candidate-ref",
        "nested-program-ref",
        "nested-revision-pin",
        "orientation-binding",
    ),
)
def test_proposal_deserializer_rejects_noncanonical_or_tampered_wire(mutator) -> None:
    wire = _candidate_result().as_dict()
    with pytest.raises((TypeError, ValueError)):
        ProposalResult.from_dict(mutator(deepcopy(wire)))


def test_abstained_proposal_has_canonical_round_trip() -> None:
    result = _abstained_result()
    assert ProposalResult.from_dict(result.as_dict()) == result
    assert result.candidates == ()
    assert result.status == "abstained"
    assert result.abstention_code == "frontier_exhausted"

__cemm_test_inventory__ = {'tests/test_proposal_result_abi2.py::test_abstained_proposal_has_canonical_round_trip': {'activation_phase': 'R1',
                                                                                          'assertion_ref': 'assertion:r1-proposal-result-abi2-test-abstained-proposal-has-canonical-round-trip',
                                                                                          'diagnostic_role': 'owner',
                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                          'owner_ref': 'program-verifier',
                                                                                          'source_ast_sha256': '01f9bdf2feae56b830602ec8c517ffc8d8e45d32bd3a7d4f37df52ebc4963d50'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[missing-field]': {'activation_phase': 'R1',
                                                                                                                         'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-missing-field',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                                         'owner_ref': 'program-verifier',
                                                                                                                         'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[nested-candidate-ref]': {'activation_phase': 'R1',
                                                                                                                                'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-nested-candidate-ref',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                                'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[nested-program-ref]': {'activation_phase': 'R1',
                                                                                                                              'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-nested-program-ref',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                                                              'owner_ref': 'program-verifier',
                                                                                                                              'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[nested-revision-pin]': {'activation_phase': 'R1',
                                                                                                                               'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-nested-revision-pin',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                                                               'owner_ref': 'program-verifier',
                                                                                                                               'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[orientation-binding]': {'activation_phase': 'R1',
                                                                                                                               'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-orientation-binding',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                                                               'owner_ref': 'program-verifier',
                                                                                                                               'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[proposal-ref]': {'activation_phase': 'R1',
                                                                                                                        'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-proposal-ref',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                                        'owner_ref': 'program-verifier',
                                                                                                                        'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[tuple-candidates]': {'activation_phase': 'R1',
                                                                                                                            'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-tuple-candidates',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                                            'owner_ref': 'program-verifier',
                                                                                                                            'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_deserializer_rejects_noncanonical_or_tampered_wire[unknown-field]': {'activation_phase': 'R1',
                                                                                                                         'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-deserializer-rejects-noncanonical-or-tampered-wire-unknown-field',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                                         'owner_ref': 'program-verifier',
                                                                                                                         'source_ast_sha256': '95dc3a29ab90628c192d5577323478bd9adc07aa1a880544842f959e75aefb0c'},
 'tests/test_proposal_result_abi2.py::test_proposal_identity_covers_every_semantic_field': {'activation_phase': 'R1',
                                                                                            'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-identity-covers-every-semantic-field',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                            'owner_ref': 'program-verifier',
                                                                                            'source_ast_sha256': '5f7e0cfd8684698283b3d6ee20aeb36677f25804984d7b4e7f96e156da5b522e'},
 'tests/test_proposal_result_abi2.py::test_proposal_preserves_rank_order_without_program_ref_sorting': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-preserves-rank-order-without-program-ref-sorting',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': '1044ca67c693401c8dc36619737ebd52df3e0fcd7111e6118179376765bd498e'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_incoherent_status_contract[abstained-empty-code]': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-incoherent-status-contract-abstained-empty-code',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                'source_ast_sha256': 'd7511f4556f0062cd7119d8bcf46dc8e85096f9d2a575902a278c950eee6be5e'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_incoherent_status_contract[abstained-with-candidate]': {'activation_phase': 'R1',
                                                                                                                    'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-incoherent-status-contract-abstained-with-candidate',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                                    'owner_ref': 'program-verifier',
                                                                                                                    'source_ast_sha256': 'd7511f4556f0062cd7119d8bcf46dc8e85096f9d2a575902a278c950eee6be5e'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_incoherent_status_contract[abstained-without-code]': {'activation_phase': 'R1',
                                                                                                                  'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-incoherent-status-contract-abstained-without-code',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R1-Task-7',
                                                                                                                  'owner_ref': 'program-verifier',
                                                                                                                  'source_ast_sha256': 'd7511f4556f0062cd7119d8bcf46dc8e85096f9d2a575902a278c950eee6be5e'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_incoherent_status_contract[candidates-empty]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-incoherent-status-contract-candidates-empty',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Task-7',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': 'd7511f4556f0062cd7119d8bcf46dc8e85096f9d2a575902a278c950eee6be5e'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_incoherent_status_contract[candidates-with-code]': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-incoherent-status-contract-candidates-with-code',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                'source_ast_sha256': 'd7511f4556f0062cd7119d8bcf46dc8e85096f9d2a575902a278c950eee6be5e'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_incoherent_status_contract[unknown-status]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-incoherent-status-contract-unknown-status',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'd7511f4556f0062cd7119d8bcf46dc8e85096f9d2a575902a278c950eee6be5e'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_noncanonical_search_scalars[explored-bool]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-noncanonical-search-scalars-explored-bool',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'e385ab7d3ef6687de93f49fb929dd47f416cbd4e4ea84d47aaa828d923bc6df8'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_noncanonical_search_scalars[explored-float]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-noncanonical-search-scalars-explored-float',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'e385ab7d3ef6687de93f49fb929dd47f416cbd4e4ea84d47aaa828d923bc6df8'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_noncanonical_search_scalars[explored-negative]': {'activation_phase': 'R1',
                                                                                                              'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-noncanonical-search-scalars-explored-negative',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                                              'owner_ref': 'program-verifier',
                                                                                                              'source_ast_sha256': 'e385ab7d3ef6687de93f49fb929dd47f416cbd4e4ea84d47aaa828d923bc6df8'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_noncanonical_search_scalars[explored-over-bound]': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-noncanonical-search-scalars-explored-over-bound',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                'source_ast_sha256': 'e385ab7d3ef6687de93f49fb929dd47f416cbd4e4ea84d47aaa828d923bc6df8'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_noncanonical_search_scalars[truncated-one]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-noncanonical-search-scalars-truncated-one',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'e385ab7d3ef6687de93f49fb929dd47f416cbd4e4ea84d47aaa828d923bc6df8'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_noncanonical_search_scalars[truncated-zero]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-noncanonical-search-scalars-truncated-zero',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'e385ab7d3ef6687de93f49fb929dd47f416cbd4e4ea84d47aaa828d923bc6df8'},
 'tests/test_proposal_result_abi2.py::test_proposal_rejects_orientation_context_model_and_revision_mismatch': {'activation_phase': 'R1',
                                                                                                               'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-rejects-orientation-context-model-and-revision-mismatch',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                                               'owner_ref': 'program-verifier',
                                                                                                               'source_ast_sha256': '50b1699f567625f9eca3c850544caf964ba90ee095e4d20ed3feb2b134bf47cd'},
 'tests/test_proposal_result_abi2.py::test_proposal_result_abi2_owns_only_strict_canonical_fields': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-result-abi2-owns-only-strict-canonical-fields',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '37f71744f81075aee271ec3f044587303a46eff51b793fd23dc9f827698a4c91'},
 'tests/test_proposal_result_abi2.py::test_proposal_result_round_trip_preserves_complete_nested_batch': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-proposal-result-abi2-test-proposal-result-round-trip-preserves-complete-nested-batch',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '35b2d6304c7741633e4b6a4f68b408d3c5706f5fb02bde665ed417e62bffb1db'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_deserializer_rejects_noncanonical_or_tampered_wire[candidate-ref]': {'activation_phase': 'R1',
                                                                                                                                 'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-deserializer-rejects-noncanonical-or-tampered-wire-candidate-ref',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                                 'source_ast_sha256': '67e249d9356f69065892b04289c923807eb53a3929088dcbb3d848899046b854'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_deserializer_rejects_noncanonical_or_tampered_wire[missing-field]': {'activation_phase': 'R1',
                                                                                                                                 'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-deserializer-rejects-noncanonical-or-tampered-wire-missing-field',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                                 'source_ast_sha256': '67e249d9356f69065892b04289c923807eb53a3929088dcbb3d848899046b854'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_deserializer_rejects_noncanonical_or_tampered_wire[nested-program-ref]': {'activation_phase': 'R1',
                                                                                                                                      'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-deserializer-rejects-noncanonical-or-tampered-wire-nested-program-ref',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                                                      'owner_ref': 'program-verifier',
                                                                                                                                      'source_ast_sha256': '67e249d9356f69065892b04289c923807eb53a3929088dcbb3d848899046b854'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_deserializer_rejects_noncanonical_or_tampered_wire[score-bool]': {'activation_phase': 'R1',
                                                                                                                              'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-deserializer-rejects-noncanonical-or-tampered-wire-score-bool',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                                                              'owner_ref': 'program-verifier',
                                                                                                                              'source_ast_sha256': '67e249d9356f69065892b04289c923807eb53a3929088dcbb3d848899046b854'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_deserializer_rejects_noncanonical_or_tampered_wire[tuple-provenance]': {'activation_phase': 'R1',
                                                                                                                                    'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-deserializer-rejects-noncanonical-or-tampered-wire-tuple-provenance',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                                                    'owner_ref': 'program-verifier',
                                                                                                                                    'source_ast_sha256': '67e249d9356f69065892b04289c923807eb53a3929088dcbb3d848899046b854'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_deserializer_rejects_noncanonical_or_tampered_wire[unknown-field]': {'activation_phase': 'R1',
                                                                                                                                 'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-deserializer-rejects-noncanonical-or-tampered-wire-unknown-field',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                                 'source_ast_sha256': '67e249d9356f69065892b04289c923807eb53a3929088dcbb3d848899046b854'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_identity_covers_every_semantic_field': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-identity-covers-every-semantic-field',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': 'eaaf4e9b2f865ec1ae22b33df12281250b51a8224dc46253d4327d327ab66d0d'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_abstention_program': {'activation_phase': 'R1',
                                                                                          'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-abstention-program',
                                                                                          'diagnostic_role': 'owner',
                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                          'owner_ref': 'program-verifier',
                                                                                          'source_ast_sha256': 'a1ad8cd0b4c8c204ec845177d657ed5755f3fb247de0f529a11a41c3a55f9a07'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_provenance[duplicate-ref]': {'activation_phase': 'R1',
                                                                                                              'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-provenance-duplicate-ref',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                                              'owner_ref': 'program-verifier',
                                                                                                              'source_ast_sha256': 'e8984acd09c12c2112819c69f0690d63c4a6b540593ac1a75fd53ecbc6fcaa0c'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_provenance[empty-ref]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-provenance-empty-ref',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'e8984acd09c12c2112819c69f0690d63c4a6b540593ac1a75fd53ecbc6fcaa0c'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_provenance[over-bound]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-provenance-over-bound',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'e8984acd09c12c2112819c69f0690d63c4a6b540593ac1a75fd53ecbc6fcaa0c'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_scalars[rank-bool]': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-scalars-rank-bool',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                       'owner_ref': 'program-verifier',
                                                                                                       'source_ast_sha256': 'ab92d8bbb74b44b2bf232fa43ec091a6271a15e52e970495db44a5595289d54e'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_scalars[rank-float]': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-scalars-rank-float',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': 'ab92d8bbb74b44b2bf232fa43ec091a6271a15e52e970495db44a5595289d54e'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_scalars[rank-negative]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-scalars-rank-negative',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'ab92d8bbb74b44b2bf232fa43ec091a6271a15e52e970495db44a5595289d54e'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_scalars[rank-over-bound]': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-scalars-rank-over-bound',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                             'owner_ref': 'program-verifier',
                                                                                                             'source_ast_sha256': 'ab92d8bbb74b44b2bf232fa43ec091a6271a15e52e970495db44a5595289d54e'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_scalars[score-bool]': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-scalars-score-bool',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': 'ab92d8bbb74b44b2bf232fa43ec091a6271a15e52e970495db44a5595289d54e'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_scalars[score-float]': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-scalars-score-float',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': 'ab92d8bbb74b44b2bf232fa43ec091a6271a15e52e970495db44a5595289d54e'},
 'tests/test_proposal_result_abi2.py::test_ranked_candidate_rejects_noncanonical_scalars[score-over-bound]': {'activation_phase': 'R1',
                                                                                                              'assertion_ref': 'assertion:r1-proposal-result-abi2-test-ranked-candidate-rejects-noncanonical-scalars-score-over-bound',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                                              'owner_ref': 'program-verifier',
                                                                                                              'source_ast_sha256': 'ab92d8bbb74b44b2bf232fa43ec091a6271a15e52e970495db44a5595289d54e'}}
