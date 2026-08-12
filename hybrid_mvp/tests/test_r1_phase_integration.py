"""R1 composition-root integration contracts."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.gaps import MissingOwner


def test_r1_bootstrap_requires_profile_and_fails_later_profiles_closed():
    signature = inspect.signature(load_runtime)
    assert "proposal_fixture" not in signature.parameters
    assert signature.parameters["profile"].default is inspect.Parameter.empty
    with pytest.raises(MissingOwner, match="program_abi_2_proposal_owner"):
        load_runtime(Path("does-not-exist"), profile="neural")
    with pytest.raises(MissingOwner, match="program_abi_2_proposal_owner"):
        load_runtime(Path("does-not-exist"), profile="release")


__cemm_test_inventory__ = {
    "tests/test_r1_phase_integration.py::test_r1_bootstrap_requires_profile_and_fails_later_profiles_closed": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-fails-later-profiles-closed",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "1808f0fa44cc4a95f54f6b8ef899c591bb9928d710df4e1e2f0441a849f07047",
    },
}
