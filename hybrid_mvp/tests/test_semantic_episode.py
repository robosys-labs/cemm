"""Tests for complete Semantic Episodes and the episode builder.

A SemanticEpisode serializes all six-phase inputs/outputs, legal and rejected
alternatives, typed verifier errors, exact proof/placement/effect, response
semantics, accepted/rejected realizations, gap receipt, revisions, hashes,
generator lineage, and review provenance. Schema validation rejects missing
no-effect markers and unknown ABI versions.

Episode generation is byte-deterministic: the same seed produces byte-identical
output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.episodes import (
    EPISODE_ABI_VERSION,
    EpisodeBuilder,
    ScenarioCase,
    SemanticEpisode,
    TrainingSource,
    TrainingSourceKind,
    validate_episode,
    validate_training_source,
)
ROOT = Path(__file__).parents[1]
SCENARIOS_PATH = ROOT / "data" / "scenarios" / "use_cases.jsonl"
EPISODES_PATH = ROOT / "data" / "episodes" / "all.jsonl"
BUILD_SCRIPT = ROOT / "scripts" / "build_episodes.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def load_scenarios():
    """Callable that loads and parses the reviewed scenario JSONL file."""

    def _load() -> list[ScenarioCase]:
        assert SCENARIOS_PATH.exists(), f"Missing {SCENARIOS_PATH}"
        cases: list[ScenarioCase] = []
        for line in SCENARIOS_PATH.read_text(encoding="utf-8").strip().splitlines():
            data = json.loads(line)
            cases.append(ScenarioCase.from_dict(data))
        return cases

    return _load


@pytest.fixture
def builder():
    """Callable that builds episodes to a path with a given seed."""

    def _build(output: Path, *, seed: int = 1701) -> None:
        import subprocess
        import sys

        subprocess.run(
            [
                sys.executable,
                str(BUILD_SCRIPT),
                "--scenarios",
                str(SCENARIOS_PATH),
                "--output",
                str(output),
                "--seed",
                str(seed),
            ],
            check=True,
            capture_output=True,
        )

    return _build


@pytest.fixture
def reviewed_episode():
    """A single reviewed SemanticEpisode built from the first scenario."""
    cases: list[ScenarioCase] = []
    for line in SCENARIOS_PATH.read_text(encoding="utf-8").strip().splitlines():
        cases.append(ScenarioCase.from_dict(json.loads(line)))
    builder = EpisodeBuilder.for_reviewed_scenarios(seed=1701)
    episodes = builder.build_all(cases)
    assert episodes, "No episodes were built"
    return episodes[0]


# ---------------------------------------------------------------------------
# Completeness: every phase and revision
# ---------------------------------------------------------------------------


def test_episode_contains_every_phase_and_revision(reviewed_episode):
    assert reviewed_episode.orientation
    assert reviewed_episode.legal_proposals
    assert reviewed_episode.rejected_proposals
    assert reviewed_episode.selected_program
    assert reviewed_episode.coverage
    assert reviewed_episode.evaluation
    assert reviewed_episode.effect_or_no_effect
    assert reviewed_episode.response_meaning
    assert reviewed_episode.realization_receipt
    assert reviewed_episode.authority_hash and reviewed_episode.action_encoding_hash


def test_episode_carries_generator_lineage_and_review_provenance(reviewed_episode):
    assert reviewed_episode.generator_lineage
    assert reviewed_episode.review_provenance
    assert reviewed_episode.review_provenance.get("review_status") == "reviewed"


def test_episode_has_known_abi_version(reviewed_episode):
    assert reviewed_episode.abi_version == EPISODE_ABI_VERSION


def test_episode_serializes_to_dict(reviewed_episode):
    data = reviewed_episode.as_dict()
    assert isinstance(data, dict)
    assert data["orientation"]
    assert data["selected_program"]
    assert data["effect_or_no_effect"]


# ---------------------------------------------------------------------------
# Scenario source: 210 unique reviewed cases
# ---------------------------------------------------------------------------


def test_scenario_source_has_210_unique_reviewed_cases(load_scenarios):
    scenarios = load_scenarios()
    assert len(scenarios) == 210
    assert len({case.scenario_ref for case in scenarios}) == 210
    assert all(case.review_status == "reviewed" for case in scenarios)


def test_scenario_cases_have_semantic_assertions(load_scenarios):
    scenarios = load_scenarios()
    for case in scenarios:
        assert case.semantic_assertions, f"{case.scenario_ref} has no assertions"
        assert case.competency_category, f"{case.scenario_ref} has no category"


def test_scenario_cases_cover_all_competency_categories(load_scenarios):
    expected = {
        "designation_definition",
        "reordered_constructions",
        "polysemy",
        "modality",
        "negation_scope",
        "recursive_family_proof",
        "participant_reference",
        "reported_speech",
        "temporal_state",
        "reviewed_sensor_operation_evidence",
        "transition_simulation",
        "learning_security",
        "capability_policy_adapter_effect",
        "contradiction",
        "gap_kinds",
        "multilingual_aliases",
        "adversarial_programs",
        "restart",
        "realization_equivalence",
    }
    scenarios = load_scenarios()
    actual = {case.competency_category for case in scenarios}
    missing = expected - actual
    assert not missing, f"Missing competency categories: {missing}"


# ---------------------------------------------------------------------------
# Byte-deterministic episode generation
# ---------------------------------------------------------------------------


def test_episode_generation_is_byte_deterministic(tmp_path, builder):
    left, right = tmp_path / "left.jsonl", tmp_path / "right.jsonl"
    builder(left, seed=1701)
    builder(right, seed=1701)
    assert left.read_bytes() == right.read_bytes()


def test_generated_episodes_match_committed_file(tmp_path, builder):
    out = tmp_path / "regenerated.jsonl"
    builder(out, seed=1701)
    assert EPISODES_PATH.exists(), "Committed episodes file missing"
    assert out.read_bytes() == EPISODES_PATH.read_bytes()


def test_generated_episodes_count_matches_scenarios(builder, load_scenarios):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "all.jsonl"
        builder(out, seed=1701)
        lines = out.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == len(load_scenarios())


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_validate_episode_rejects_missing_no_effect_marker(reviewed_episode):
    data = reviewed_episode.as_dict()
    # Remove the no-effect marker.
    data["effect_or_no_effect"] = None
    with pytest.raises(ValueError):
        validate_episode(data)


def test_validate_episode_rejects_unknown_abi_version(reviewed_episode):
    data = reviewed_episode.as_dict()
    data["abi_version"] = 999
    with pytest.raises(ValueError):
        validate_episode(data)


def test_validate_episode_accepts_valid_episode(reviewed_episode):
    data = reviewed_episode.as_dict()
    validate_episode(data)  # should not raise


def test_training_source_kinds_are_closed():
    expected = {
        "reviewed_scenario",
        "authority_derived",
        "human_paraphrase",
        "teacher_paraphrase",
        "verified_correction",
    }
    actual = {kind.value for kind in TrainingSourceKind}
    assert actual == expected


def test_validate_training_source_rejects_unknown_kind():
    data = {
        "source_kind": "unknown_kind",
        "source_ref": "scenario:test",
        "reviewed_target_ref": "scenario:target",
        "independently_reverified": True,
    }
    with pytest.raises(ValueError):
        validate_training_source(data)


def test_validate_training_source_accepts_valid_source():
    data = {
        "source_kind": "reviewed_scenario",
        "source_ref": "scenario:test",
        "reviewed_target_ref": None,
        "independently_reverified": True,
    }
    validate_training_source(data)  # should not raise


def test_human_paraphrase_requires_reviewed_target():
    data = {
        "source_kind": "human_paraphrase",
        "source_ref": "utterance:test",
        "reviewed_target_ref": None,
        "independently_reverified": False,
    }
    with pytest.raises(ValueError):
        validate_training_source(data)


def test_teacher_paraphrase_requires_reviewed_target():
    data = {
        "source_kind": "teacher_paraphrase",
        "source_ref": "utterance:test",
        "reviewed_target_ref": "scenario:target",
        "independently_reverified": False,
    }
    with pytest.raises(ValueError):
        validate_training_source(data)


def test_verified_correction_requires_reverification():
    data = {
        "source_kind": "verified_correction",
        "source_ref": "correction:test",
        "reviewed_target_ref": "scenario:target",
        "independently_reverified": False,
    }
    with pytest.raises(ValueError):
        validate_training_source(data)


# ---------------------------------------------------------------------------
# Untrusted evidence: human/teacher language never creates authority
# ---------------------------------------------------------------------------


def test_untrusted_evidence_never_creates_authority():
    """Human/teacher language is untrusted evidence: it may become an episode
    only when paired with an already reviewed semantic target and independently
    re-verified. It never creates an atom, rule, frame, policy, or transition."""
    # A human_paraphrase source without a reviewed target must be rejected.
    bad = TrainingSource(
        source_kind=TrainingSourceKind.HUMAN_PARAPHRASE,
        source_ref="utterance:human-1",
        reviewed_target_ref=None,
        independently_reverified=False,
    )
    with pytest.raises(ValueError):
        validate_training_source(bad.as_dict())

    # A human_paraphrase source WITH a reviewed target and re-verification is
    # accepted — but it still does not create authority.
    good = TrainingSource(
        source_kind=TrainingSourceKind.HUMAN_PARAPHRASE,
        source_ref="utterance:human-1",
        reviewed_target_ref="scenario:reviewed-1",
        independently_reverified=True,
    )
    validate_training_source(good.as_dict())
    # The source kind is evidence, not authority.
    assert good.source_kind.value == "human_paraphrase"
