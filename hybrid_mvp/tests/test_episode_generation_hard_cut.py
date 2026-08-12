"""Episode ABI 2 caller hard-cut and ABI 1 lineage supersessions."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.episodes import (
    EPISODE_ABI_VERSION,
    EpisodeBuilder,
    ScenarioCase,
    SemanticEpisode,
    validate_episode,
)
from cemm_authoritative_hybrid.gaps import MissingOwner
from cemm_authoritative_hybrid.programs import ACTION_ABI_HASH


ROOT = Path(__file__).parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_episodes.py"
QUARANTINED_CORPUS = ROOT / "data" / "episodes" / "all.jsonl"
R4_OWNER = "r4_authentic_episode_generation_owner"


def _load_builder_script():
    spec = importlib.util.spec_from_file_location(
        "_episode_generation_hard_cut", BUILD_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def canonical_runtime():
    with tempfile.TemporaryDirectory(prefix="cemm-episode-hard-cut-") as root:
        runtime = load_runtime(
            ROOT,
            profile="development",
            store_path=Path(root) / "stores",
        )
        try:
            yield runtime
        finally:
            runtime.stores.close()


@pytest.fixture(scope="module")
def diagnostic_episode(canonical_runtime):
    builder = EpisodeBuilder.for_reviewed_scenarios(
        runtime=canonical_runtime,
        seed=1701,
    )
    return builder.build_episode(
        ScenarioCase(
            scenario_ref="scenario:episode-hard-cut",
            review_status="reviewed",
            competency_category="relation",
            semantic_assertions=({"operator": "op:relation"},),
            surface_examples=("alice likes bob",),
        )
    )


def test_episode_generator_requires_injected_runtime_and_missing_r4_owner(
    canonical_runtime,
):
    module = _load_builder_script()
    signature = inspect.signature(module.build_all_episodes)
    assert signature.parameters["runtime"].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="HybridRuntime"):
        module.build_all_episodes(Path("not-read.jsonl"), runtime=object())
    with pytest.raises(MissingOwner, match=R4_OWNER):
        module.build_all_episodes(
            Path("not-read.jsonl"),
            runtime=canonical_runtime,
            seed=1701,
        )


def test_episode_abi2_r1_shape_preserves_derivation_lineage_without_later_truth(
    diagnostic_episode,
):
    assert diagnostic_episode.orientation
    assert diagnostic_episode.legal_proposals
    assert all(
        row["artifact_role"] == "derivation_lineage"
        for row in diagnostic_episode.legal_proposals
    )
    assert diagnostic_episode.selected_program == {}
    assert diagnostic_episode.verified_meaning == {}
    assert diagnostic_episode.coverage == {}
    assert diagnostic_episode.evaluation == {}
    assert diagnostic_episode.effect_or_no_effect == {"status": "not_admitted"}
    assert diagnostic_episode.response_meaning == {}
    assert diagnostic_episode.realization_receipt == {}
    assert diagnostic_episode.training_source["independently_reverified"] is False


def test_episode_abi2_preserves_diagnostic_lineage_without_gold_claim(
    diagnostic_episode,
):
    assert diagnostic_episode.generator_lineage["authority_generation"]
    assert diagnostic_episode.review_provenance == {
        "review_status": "reviewed",
        "scenario_ref": "scenario:episode-hard-cut",
        "competency_category": "relation",
    }
    assert diagnostic_episode.training_source["independently_reverified"] is False


def test_episode_abi2_is_exact_active_diagnostic_version(diagnostic_episode):
    assert EPISODE_ABI_VERSION == 2
    assert diagnostic_episode.abi_version == 2
    assert diagnostic_episode.action_abi_hash == ACTION_ABI_HASH


def test_episode_abi2_serializes_authenticated_diagnostic_wire(diagnostic_episode):
    wire = diagnostic_episode.as_dict()
    assert SemanticEpisode.from_dict(wire) == diagnostic_episode
    validate_episode(wire)


def test_r4_episode_generation_determinism_remains_unadmitted(canonical_runtime):
    module = _load_builder_script()
    errors = []
    for _ in range(2):
        with pytest.raises(MissingOwner) as caught:
            module.build_all_episodes(
                Path("not-read.jsonl"),
                runtime=canonical_runtime,
                seed=1701,
            )
        errors.append(str(caught.value))
    assert errors == [f"MissingOwner({R4_OWNER})"] * 2


def test_r4_committed_program_abi1_corpus_remains_quarantined(tmp_path):
    before = hashlib.sha256(QUARANTINED_CORPUS.read_bytes()).hexdigest()
    output = tmp_path / "candidate.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--profile",
            "development",
            "--store-path",
            str(tmp_path / "stores.db"),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    after = hashlib.sha256(QUARANTINED_CORPUS.read_bytes()).hexdigest()
    assert result.returncode != 0
    assert f"MissingOwner({R4_OWNER})" in result.stderr
    assert not output.exists()
    assert before == after


def test_episode_abi2_rejects_missing_r1_no_later_artifact_marker(
    diagnostic_episode,
):
    wire = diagnostic_episode.as_dict()
    wire.pop("effect_or_no_effect")
    with pytest.raises(ValueError, match="fields"):
        validate_episode(wire)


def test_episode_abi2_rejects_unknown_version(diagnostic_episode):
    wire = diagnostic_episode.as_dict()
    wire["abi_version"] = 999
    with pytest.raises(ValueError, match="ABI version"):
        validate_episode(wire)


def test_episode_abi2_accepts_exact_authenticated_wire(diagnostic_episode):
    validate_episode(diagnostic_episode.as_dict())


__cemm_test_inventory__ = {
    "tests/test_episode_generation_hard_cut.py::test_episode_generator_requires_injected_runtime_and_missing_r4_owner": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-episode-generator-requires-canonical-runtime",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "2daa3699fba931ec0b14c34194ac71903c240ffaba29ff919e7e9fbd0670226c",
    },
    "tests/test_episode_generation_hard_cut.py::test_episode_abi2_r1_shape_preserves_derivation_lineage_without_later_truth": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-episode-contains-every-phase-and-revision",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "d53de647de351aabfe329ed608ba1fa0d113d5091d1a55c36658b94d76586b6b",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_episode_contains_every_phase_and_revision",
    },
    "tests/test_episode_generation_hard_cut.py::test_episode_abi2_preserves_diagnostic_lineage_without_gold_claim": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-episode-carries-generator-lineage-and-review-provenance",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "69f3acf3b9dc614e60912f7e3080d184f1cce1a37cc7cf665fdb2333450036fa",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_episode_carries_generator_lineage_and_review_provenance",
    },
    "tests/test_episode_generation_hard_cut.py::test_episode_abi2_is_exact_active_diagnostic_version": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-episode-has-known-abi-version",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "e6ca1a9545969046e91bc3a83948e04c8c54c982bd2fc4936834d99347d1a9dc",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_episode_has_known_abi_version",
    },
    "tests/test_episode_generation_hard_cut.py::test_episode_abi2_serializes_authenticated_diagnostic_wire": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-episode-serializes-to-dict",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "0600f57ed455c56017efe333ab42ff7b072d0dffc366460e1b7a7843db1395d2",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_episode_serializes_to_dict",
    },
    "tests/test_episode_generation_hard_cut.py::test_r4_episode_generation_determinism_remains_unadmitted": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-episode-generation-is-byte-deterministic",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "5d4cd17bc7686810bb30198d383b7c00b6d7d7be1ba12b73b0ab51400b652f47",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_episode_generation_is_byte_deterministic",
    },
    "tests/test_episode_generation_hard_cut.py::test_r4_committed_program_abi1_corpus_remains_quarantined": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-generated-episodes-match-committed-file",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "4bd5f58e9278c9cbe3b31f1c2dbc2422a221a76115d95fba43595e2e1a54d80b",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_generated_episodes_match_committed_file",
    },
    "tests/test_episode_generation_hard_cut.py::test_episode_abi2_rejects_missing_r1_no_later_artifact_marker": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-validate-episode-rejects-missing-no-effect-marker",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "95f64cf3f0152628ead325b46e019b49726e0c68e67018c6177941cc6ec972f8",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_validate_episode_rejects_missing_no_effect_marker",
    },
    "tests/test_episode_generation_hard_cut.py::test_episode_abi2_rejects_unknown_version": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-validate-episode-rejects-unknown-abi-version",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "107e1c936519623c7f5fbb3bdfb9414254666426e8b5f249437a6ff1aeaa8f52",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_validate_episode_rejects_unknown_abi_version",
    },
    "tests/test_episode_generation_hard_cut.py::test_episode_abi2_accepts_exact_authenticated_wire": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:semantic-episode-validate-episode-accepts-valid-episode",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9-Episode-Hard-Cut",
        "source_ast_sha256": "4a3fcb384cefd6a56b3be45b2043bb225d17834ef6c8e2bb6a8b1e99b4f75c9c",
        "supersedes_node_id": "tests/test_semantic_episode.py::test_validate_episode_accepts_valid_episode",
    },
}
