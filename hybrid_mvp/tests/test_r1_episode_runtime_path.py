"""R1 episode caller contracts for the one canonical runtime path."""

from __future__ import annotations

import importlib.util
import inspect
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType, MethodType, SimpleNamespace

import pytest

from cemm_authoritative_hybrid.episodes import (
    EPISODE_ABI_VERSION,
    EpisodeBuilder,
    ScenarioCase,
    SemanticEpisode,
    validate_episode,
)
from cemm_authoritative_hybrid.coverage import CoverageReceipt
from cemm_authoritative_hybrid.programs import ACTION_ABI_HASH
from cemm_authoritative_hybrid.runtime import HybridRuntime


def _runtime_fixture():
    helper_path = Path(__file__).with_name("test_r1_runtime_path.py")
    spec = importlib.util.spec_from_file_location("_r1_episode_helpers", helper_path)
    assert spec is not None and spec.loader is not None
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    return helpers._runtime()[0]


def test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning():
    runtime = _runtime_fixture()
    calls: list[tuple[str, str, bool]] = []
    original_process = runtime.process

    def recording_process(self, session_ref, text, *, trace=True):
        calls.append((session_ref, text, trace))
        return original_process(session_ref, text, trace=trace)

    runtime.process = MethodType(recording_process, runtime)
    builder = EpisodeBuilder(
        authority=SimpleNamespace(generation="authority:r1-runtime"),
        runtime=runtime,
        seed=1701,
    )
    case = ScenarioCase(
        scenario_ref="scenario:r1-episode",
        review_status="reviewed",
        competency_category="relation",
        semantic_assertions=({"operator": "op:relation"},),
        surface_examples=("alice likes bob",),
    )

    episode = builder.build_episode(case)

    assert EPISODE_ABI_VERSION == 2
    assert episode.abi_version == 2
    assert episode.action_abi_hash == ACTION_ABI_HASH
    assert calls == [("session:scenario:r1-episode", "alice likes bob", False)]
    assert episode.selected_program["artifact_role"] == "derivation_lineage"
    assert episode.verified_meaning["verified_meaning_ref"].startswith(
        "verified_meaning:"
    )
    assert episode.verified_meaning["program_ref"] == episode.selected_program[
        "program"
    ]["program_ref"]
    assert episode.evaluation == {}
    assert episode.effect_or_no_effect == {"status": "not_admitted"}
    assert episode.response_meaning == {}
    assert episode.realization_receipt == {}
    assert episode.gap_receipt["status"] == "later_owner_not_admitted"
    assert episode.gap_receipt["source_refs"] == (
        episode.verified_meaning["verified_meaning_ref"],
    )
    assert episode.training_source["independently_reverified"] is False
    coverage_wire = episode.as_dict()["coverage"]
    assert CoverageReceipt.from_dict(coverage_wire).as_dict() == coverage_wire
    assert SemanticEpisode.from_dict(episode.as_dict()) == episode
    validate_episode(episode.as_dict())
    legacy = episode.as_dict()
    legacy["abi_version"] = 1
    with pytest.raises(ValueError, match="ABI version"):
        validate_episode(legacy)

    assert isinstance(episode.review_provenance, MappingProxyType)
    with pytest.raises(TypeError):
        episode.review_provenance["review_status"] = "changed"
    with pytest.raises(ValueError, match="episode_ref mismatch"):
        replace(episode, episode_ref="episode:forged")
    with pytest.raises(ValueError, match="not admitted"):
        replace(episode, evaluation={"status": "fabricated"})


def test_r1_episode_codec_is_strict_bounded_and_authority_bound(monkeypatch):
    runtime = _runtime_fixture()
    with pytest.raises(ValueError, match="authority"):
        EpisodeBuilder(
            authority=SimpleNamespace(generation="authority:other"),
            runtime=runtime,
        )

    builder = EpisodeBuilder(
        authority=SimpleNamespace(generation="authority:r1-runtime"),
        runtime=runtime,
    )
    case = ScenarioCase(
        scenario_ref="scenario:r1-episode-codec",
        review_status="reviewed",
        competency_category="relation",
        semantic_assertions=({"operator": "op:relation"},),
        surface_examples=("alice likes bob",),
    )
    episode = builder.build_episode(case)
    wire = episode.as_dict()

    missing = dict(wire)
    missing.pop("training_source")
    with pytest.raises(ValueError, match="fields"):
        SemanticEpisode.from_dict(missing)
    extra = {**wire, "legacy_meaning": wire["selected_program"]}
    with pytest.raises(ValueError, match="fields"):
        SemanticEpisode.from_dict(extra)

    mutated = episode.as_dict()
    mutated["review_provenance"]["review_status"] = "reviewed-revised"
    with pytest.raises(ValueError, match="episode_ref mismatch"):
        SemanticEpisode.from_dict(mutated)

    import cemm_authoritative_hybrid.episodes as episodes_module

    hostile = dict(wire)
    hostile["legal_proposals"] = [wire["selected_program"]] * 65

    def forbidden_hash(*_args, **_kwargs):
        raise AssertionError("hostile episode reached stable_ref")

    monkeypatch.setattr(episodes_module, "stable_ref", forbidden_hash)
    with pytest.raises(ValueError, match="bound"):
        SemanticEpisode.from_dict(hostile)


def test_r1_episode_source_has_no_fixture_proposal_or_duplicate_result_path():
    source = Path(inspect.getsourcefile(EpisodeBuilder)).read_text(encoding="utf-8")
    assert "FixtureProposalOwner" not in source
    assert "KernelCycleResult" not in source
    assert "ProcessResult" not in source
    assert "runtime.process(" in source
    assert inspect.signature(HybridRuntime.process).parameters["trace"].default is True


__cemm_test_inventory__ = {
    "tests/test_r1_episode_runtime_path.py::test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-episode-verified-meaning-separation",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "bef1ef1759e6fc171fc9f827cfe4d59722a13bb063f7d6d0980cdbcaef22eb2b",
    },
    "tests/test_r1_episode_runtime_path.py::test_r1_episode_codec_is_strict_bounded_and_authority_bound": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-episode-strict-codec",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "108f707b43bfefe7d405e77a9fd9adcadc1ee488805e0a134982269b6bd7c9f5",
    },
    "tests/test_r1_episode_runtime_path.py::test_r1_episode_source_has_no_fixture_proposal_or_duplicate_result_path": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-episode-one-runtime-path",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "f28c3c663e299ecbe7de7d2f8f1ee53629d3b7c44cf5a6f4c1fe0f1a650dc3ae",
    },
}