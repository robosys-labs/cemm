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
                                                                                                                 'source_ast_sha256': '4ec6dd58d16552a7ca7ffa8681b932b046c9c90769248abff7dc4b30505fa863'},
 'tests/test_r4_authentic_episodes.py::test_every_emitted_episode_contains_complete_six_phase_artifacts': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-authentic-episodes-contain-six-phase-artifacts',
                                                                                                           'contributes_to_rewrite_refs': ['rewrite_obligation:1d2d0b2ddc0508c0d500ab70'],
                                                                                                           'diagnostic_role': 'phase',
                                                                                                           'introduced_by_task': 'R4-Closeout',
                                                                                                           'source_ast_sha256': '260a5c7f41706b20313a852483962f0a462bde23a47eec74ce14595c0aef8d78'},
 'tests/test_r4_authentic_episodes.py::test_every_episode_binds_exact_authority_and_revision_identity': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-authentic-episodes-bind-authority-revision',
                                                                                                         'contributes_to_rewrite_refs': ['rewrite_obligation:cf2ae32ce7f4e41090dc235e'],
                                                                                                         'diagnostic_role': 'phase',
                                                                                                         'introduced_by_task': 'R4-Closeout',
                                                                                                         'source_ast_sha256': '2819eaa256e153f9990f7d08ae4e63557c3ee7dd13709f8cd196e38c9ce991e6'}}

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
    expected = ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "RESPOND")
    for episode in _episodes():
        cycle = episode.observed_cycle
        assert cycle.orientation is not None
        assert cycle.proposal is not None
        assert cycle.verification is not None
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
        assert meaning is not None
        assert meaning.revision_pin.authority_generation == contract_pin.authority_generation
        assert episode.expanded_case.contract_ref == episode.expected_contract.contract_ref
        assert episode.comparison.expected_contract_ref == episode.expected_contract.contract_ref
        assert episode.comparison.observed_cycle_ref == cycle.cycle_ref
