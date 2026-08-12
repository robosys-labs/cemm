"""R1 episode caller contracts for the one canonical runtime path."""

from __future__ import annotations

import inspect
from pathlib import Path

from cemm_authoritative_hybrid.episodes import EpisodeBuilder
from cemm_authoritative_hybrid.runtime import HybridRuntime


def test_r1_episode_source_has_no_fixture_proposal_or_duplicate_result_path():
    source = Path(inspect.getsourcefile(EpisodeBuilder)).read_text(encoding="utf-8")
    assert "FixtureProposalOwner" not in source
    assert "KernelCycleResult" not in source
    assert "ProcessResult" not in source
    assert "runtime.process(" in source
    assert inspect.signature(HybridRuntime.process).parameters["trace"].default is True


__cemm_test_inventory__ = {
    "tests/test_r1_episode_runtime_path.py::test_r1_episode_source_has_no_fixture_proposal_or_duplicate_result_path": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-episode-one-runtime-path",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "f28c3c663e299ecbe7de7d2f8f1ee53629d3b7c44cf5a6f4c1fe0f1a650dc3ae",
    },
}
