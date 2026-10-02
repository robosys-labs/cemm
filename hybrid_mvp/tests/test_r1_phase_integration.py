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
    with pytest.raises(MissingOwner, match="program_abi_3_proposal_owner"):
        load_runtime(Path("does-not-exist"), profile="neural")
    with pytest.raises(MissingOwner, match="program_abi_3_proposal_owner"):
        load_runtime(Path("does-not-exist"), profile="release")


__cemm_test_inventory__ = {
    "tests/test_r1_phase_integration.py::test_r1_bootstrap_requires_profile_and_fails_later_profiles_closed": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-fails-later-profiles-closed",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "5895273b94cc41e8381c1012795fbcbd4e6af8324d9a81877e5d17697ff8aedc",
    },
}
