"""R3 structural mode projection tests."""
from __future__ import annotations

from types import SimpleNamespace
import pytest

from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.mode import (
    ModeProjection,
    ModeProjectionError,
    StructuralModeProjector,
)

__cemm_test_inventory__ = {
    "tests/test_r3_mode_projection.py::test_closed_modes_are_projected_from_structural_hypotheses": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-closed-modes-are-projected-from-structural-hypotheses",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "situation-context",
        "source_ast_sha256": "91b58783bef7073d55f783ed4e05297243fa8ffbf220c2f940129e512cb39e76"
    },
    "tests/test_r3_mode_projection.py::test_competing_nonobserve_modes_fail_closed": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-competing-nonobserve-modes-fail-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "situation-context",
        "source_ast_sha256": "c36b7dd56111e28fc9412128b2db5d2344fdbf2ad1ad2cc7bf592b9f07e5713a"
    }
}



def _lattice(*hypotheses):
    return SimpleNamespace(lattice_ref="lattice:test", hypotheses=tuple(hypotheses), units=())


def _hyp(ref: str, construction: str, features=()):
    return SimpleNamespace(
        hypothesis_ref=ref,
        construction=construction,
        unit_refs=(f"unit:{ref}",),
        features=tuple(features),
    )


def test_closed_modes_are_projected_from_structural_hypotheses() -> None:
    projector = StructuralModeProjector()
    cases = {
        "declarative": SemanticMode.OBSERVE,
        "query": SemanticMode.QUERY,
        "imperative": SemanticMode.REQUEST,
        "hypothetical": SemanticMode.SIMULATE,
    }
    for construction, expected in cases.items():
        value = projector.project(_lattice(_hyp(construction, construction)))
        assert value.mode is expected
        assert ModeProjection.from_dict(value.as_dict()) == value


def test_competing_nonobserve_modes_fail_closed() -> None:
    with pytest.raises(ModeProjectionError, match="mode_ambiguous"):
        StructuralModeProjector().project(
            _lattice(_hyp("q", "query"), _hyp("r", "imperative"))
        )
