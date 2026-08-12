"""Governed R4 successors for the frozen bootstrap-episode assertions.

R4 replaces bootstrap proposal labels with externally reviewed expected
contracts compared against authentic public-runtime cycles.  The committed R4
corpus is therefore the evidence source for these historical assertions.
"""
from __future__ import annotations

from pathlib import Path

from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode

__cemm_test_inventory__ = {'tests/test_r4_authentic_episodes.py::test_every_accepted_episode_binds_coverage_program_and_action_identity': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:r4-authentic-episodes-bind-coverage-program-action',
                                                                                                                 'contributes_to_rewrite_refs': ['rewrite_obligation:e4a2ebdd620978935fe8d884'],
                                                                                                                 'diagnostic_role': 'phase',
                                                                                                                 'introduced_by_task': 'R4-Closeout',
                                                                                                                 'source_ast_sha256': 'a7e93f21189c76573dff2b1b16bbabb10896e796d4f20775cb970e2150676e34'},
 'tests/test_r4_authentic_episodes.py::test_every_emitted_episode_contains_complete_six_phase_artifacts': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-authentic-episodes-contain-six-phase-artifacts',
                                                                                                           'contributes_to_rewrite_refs': ['rewrite_obligation:1d2d0b2ddc0508c0d500ab70'],
                                                                                                           'diagnostic_role': 'phase',
                                                                                                           'introduced_by_task': 'R4-Closeout',
                                                                                                           'source_ast_sha256': 'bcc391784fa61d8b71ad5be4ea41124a868a72a76ed9dfece59ea9864fba01c1'},
 'tests/test_r4_authentic_episodes.py::test_every_episode_binds_exact_authority_and_revision_identity': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-authentic-episodes-bind-authority-revision',
                                                                                                         'contributes_to_rewrite_refs': ['rewrite_obligation:cf2ae32ce7f4e41090dc235e'],
                                                                                                         'diagnostic_role': 'phase',
                                                                                                         'introduced_by_task': 'R4-Closeout',
                                                                                                         'source_ast_sha256': '8ac7df266c0f4c285e404fa86692b65516516c071272cbd04daa682a18efd4b6'}}

ROOT = Path(__file__).parents[1]
EPISODES = ROOT / "artifacts" / "r4" / "episodes.jsonl"


def _episodes() -> tuple[AuthenticEpisode, ...]:
    assert EPISODES.is_file(), "R4 authentic episode corpus has not been built"
    import json

    rows = tuple(
        AuthenticEpisode.from_dict(json.loads(line))
        for line in EPISODES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    assert rows, "R4 authentic episode corpus is empty"
    return rows


def test_every_accepted_episode_binds_coverage_program_and_action_identity() -> None:
    for episode in _episodes():
        assert episode.comparison.passed
        verification = episode.observed_cycle.verification
        if verification.status != "selected":
            assert episode.expected_contract.outcome_kind.value in {
                "gap", "verification_rejection", "restart"
            }
            assert episode.observed_cycle.gap_receipt is not None
            continue
        assert verification.status == "selected"
        meaning = verification.selected_meaning
        assert meaning is not None
        assert meaning.program_ref
        assert meaning.coverage_receipt_ref
        assert meaning.verification_receipt_ref
        evaluation = episode.observed_cycle.evaluation
        assert evaluation is not None
        assert evaluation.decision.decision_ref
        assert evaluation.decision.action.value


def test_every_emitted_episode_contains_complete_six_phase_artifacts() -> None:
    expected = ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE")
    for episode in _episodes():
        cycle = episode.observed_cycle
        assert cycle.orientation is not None
        assert cycle.proposal is not None
        assert cycle.verification is not None
        assert all(row.duration_ns == 0 for row in cycle.trace)
        if cycle.verification.status != "selected":
            assert episode.expected_contract.outcome_kind.value in {
                "gap", "verification_rejection", "restart"
            }
            assert cycle.gap_receipt is not None
            assert tuple(row.phase.value for row in cycle.phase_material) == expected[:3]
            continue
        assert cycle.evaluation is not None
        assert cycle.effect_receipt is not None
        assert cycle.response_meaning is not None
        assert tuple(row.phase.value for row in cycle.phase_material) == expected


def test_every_episode_binds_exact_authority_and_revision_identity() -> None:
    for episode in _episodes():
        contract_pin = episode.expected_contract.revision_pin
        cycle = episode.observed_cycle
        assert cycle.orientation.revision_pin.authority_generation == contract_pin.authority_generation
        assert cycle.final_revision_pin.authority_generation == contract_pin.authority_generation
        meaning = cycle.verification.selected_meaning
        if meaning is not None:
            assert meaning.revision_pin.authority_generation == contract_pin.authority_generation
        else:
            assert episode.expected_contract.outcome_kind.value in {
                "gap", "verification_rejection", "restart"
            }
        assert episode.expanded_case.contract_ref == episode.expected_contract.contract_ref
        assert episode.comparison.expected_contract_ref == episode.expected_contract.contract_ref
        assert episode.comparison.observed_cycle_ref == cycle.cycle_ref
