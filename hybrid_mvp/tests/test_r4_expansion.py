"""R4 all-surface expansion tests."""
from __future__ import annotations

from cemm_authoritative_hybrid.authority import AtomRecord, DesignationIndex
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_expansion import CaseExpander, ExpandedCase

__cemm_test_inventory__ = {
    "tests/test_r4_expansion.py::test_expander_uses_every_reviewed_surface_and_environment": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-expander-uses-every-reviewed-surface-and-environment",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Complete",
        "owner_ref": "surface-expansion",
        "source_ast_sha256": "680dd423e3d81a0a44a01d675c3721a6bb9e36b7f3106333502c3b1734308387"
    },
    "tests/test_r4_expansion.py::test_paraphrase_surfaces_are_isolated_trajectories_by_default": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-paraphrase-trajectories-are-isolated",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Final-Admission-Closeout",
        "owner_ref": "surface-expansion",
        "source_ast_sha256": "af4157ebce344c48c8967f8d5d6a8d9f6a1dbb18bdec960cac160850c7fccec0"
    }
}



class _Authority:
    generation = "authority:test"
    atoms = {
        ref: AtomRecord(ref=ref, kind=kind)
        for ref, kind in {
            "rel:mother_in_law": "relation_type",
        }.items()
    }
    event_signatures = {}
    value_dimensions = {}
    designations = DesignationIndex(
        by_surface={("mother-in-law", "en"): ("rel:mother_in_law",)},
        by_target={("rel:mother_in_law", "en"): ("mother-in-law",)},
    )
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}
    rules = {}


def _scenario():
    return ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:multi",
            "review_status": "reviewed",
            "competency_category": "designation_definition",
            "semantic_assertions": [
                {
                    "kind": "designates",
                    "surface": "mother-in-law",
                    "target": "rel:mother_in_law",
                }
            ],
            "surface_examples": [
                "mother-in-law",
                "mother in law",
                "spouse's mother",
            ],
            "expected_gap_kind": None,
            "metadata": {},
        }
    )


def _compiler():
    return ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test")


def _pin():
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


def test_expander_uses_every_reviewed_surface_and_environment() -> None:
    expanded = CaseExpander(_compiler()).expand(
        _scenario(), revision_pin=_pin(), environments=({}, {"permission_refs": []})
    )
    assert len(expanded) == 6
    assert {row.surface for row in expanded} == set(_scenario().surface_examples)
    assert all(ExpandedCase.from_dict(row.as_dict()) == row for row in expanded)


def test_paraphrase_surfaces_are_isolated_trajectories_by_default() -> None:
    expanded = CaseExpander(_compiler()).expand(
        _scenario(), revision_pin=_pin(), environments=({},)
    )
    assert len({row.trajectory_ref for row in expanded}) == len(expanded)
    assert {row.turn_index for row in expanded} == {0}
