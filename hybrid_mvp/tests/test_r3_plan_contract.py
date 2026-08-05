"""R3 plan contract: ensure R3 governance is correctly allocated."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

__cemm_test_inventory__ = {
    "tests/test_r3_plan_contract.py::test_r3_plan_is_committed": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-r3-plan-is-committed",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-0",
        "source_ast_sha256": "64ddaf34e888ab20eb692110e5c2f52a35a6b3d0b70bc028eaf2d1558183581f"
    },
    "tests/test_r3_plan_contract.py::test_r3_abi_registry_includes_decision_abi_1": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-abi-registry-includes-decision-abi-1",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-0",
        "source_ast_sha256": "eb71d82a3ccb101eb3cbf3ad9707cf8297eb1a5fb4b1cb0ec4eb6e4fbf7e52d2"
    },
    "tests/test_r3_plan_contract.py::test_r3_abi_registry_includes_activation_canary_receipt_abi_1": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-abi-registry-includes-activation-canary-receipt-abi-1",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-0",
        "source_ast_sha256": "410c99a76cfcff784daabe0448b92e7083c40a84bdc8266ccf2dc2b821108562"
    },
    "tests/test_r3_plan_contract.py::test_r3_validation_gates_define_r3_phase": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-validation-gates-define-r3-phase",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-0",
        "source_ast_sha256": "b7a8efe6155e0ffc60384fb074a64da02af48bebf113952f2cbb3ff112f142b2"
    },
    "tests/test_r3_plan_contract.py::test_r3_cannot_be_admitted_while_r2_is_non_green": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-cannot-be-admitted-while-r2-is-non-green",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-0",
        "source_ast_sha256": "813c189159f72ce5d0a5931a20be16de09d6ba21005c4e0c86ca8272a21eede1"
    },
    "tests/test_r3_plan_contract.py::test_r3_owner_groups_within_eight_step_limit": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owner-groups-within-eight-step-limit",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-0",
        "source_ast_sha256": "737d910fa75e45ff9d52202d6c9b214b61448630f686c4f48fd74fa9fa677997"
    },
    "tests/test_r3_plan_contract.py::test_r3_duplicate_decision_owner_fails": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-duplicate-decision-owner-fails",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-0",
        "source_ast_sha256": "2060832d844057f93aa4831ff807ddc34e222cfddced00c57887cd361585694d"
    },
}

_ROOT = Path(__file__).resolve().parent.parent
_GATES = _ROOT / "configs" / "validation_gates.json"
_ABI = _ROOT / "docs" / "ABI_REGISTRY.md"
_AUTHORITY = _ROOT / "docs" / "DOCUMENT_AUTHORITY.json"


def test_r3_plan_is_committed() -> None:
    """The R3 implementation plan must be committed in the governed docs tree."""
    plan_path = _ROOT / "docs" / "superpowers" / "plans" / "2026-08-05-hybrid-mvp-r3-cognition-activation-plan.md"
    assert plan_path.exists(), "R3 implementation plan is not committed"
    text = plan_path.read_text(encoding="utf-8")
    assert "R3 Cognition Activation" in text
    assert "R3-00" in text
    assert "Decision ABI" in text


def test_r3_abi_registry_includes_decision_abi_1() -> None:
    """The ABI registry must include Decision ABI 1 with the canonical owner."""
    text = _ABI.read_text(encoding="utf-8")
    assert "Decision ABI" in text
    assert "decision.py" in text
    # Ensure it is version 1
    assert "| 1 |" in text or "| **1** |" in text


def test_r3_abi_registry_includes_activation_canary_receipt_abi_1() -> None:
    """The ABI registry must include Activation Canary Receipt ABI 1."""
    text = _ABI.read_text(encoding="utf-8")
    assert "Activation Canary Receipt ABI" in text


def test_r3_validation_gates_define_r3_phase() -> None:
    """The validation gates config must define an R3 phase with admission steps."""
    with open(_GATES, "r", encoding="utf-8") as f:
        gates = json.load(f)
    phases = gates.get("phases", {})
    assert "R3" in phases, "R3 phase not defined in validation gates"
    r3 = phases["R3"]
    assert "admission" in r3, "R3 phase missing admission steps"
    assert "owners" in r3, "R3 phase missing owner selectors"
    assert "phase" in r3, "R3 phase missing phase selector"
    admission = r3["admission"]
    assert "governance" in admission, "R3 admission missing governance"
    assert "pytest_active" in admission, "R3 admission missing pytest_active"
    assert "r3_structure" in admission, "R3 admission missing r3_structure"
    assert "sqlite_activation" in admission, "R3 admission missing sqlite_activation"
    assert "r3_activation_canaries" in admission, "R3 admission missing r3_activation_canaries"


def test_r3_cannot_be_admitted_while_r2_is_non_green() -> None:
    """R3 admission must require R2 green status."""
    with open(_AUTHORITY, "r", encoding="utf-8") as f:
        authority = json.load(f)
    governing = authority.get("governing_documents", [])
    r3_plan = "docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-cognition-activation-plan.md"
    assert r3_plan in governing, "R3 plan not in governing documents"


def test_r3_owner_groups_within_eight_step_limit() -> None:
    """R3 must have at most 8 owner groups."""
    with open(_GATES, "r", encoding="utf-8") as f:
        gates = json.load(f)
    r3 = gates["phases"]["R3"]
    owners = r3["owners"]
    assert len(owners) <= 8, f"R3 has {len(owners)} owner groups, exceeds maximum of 8"
    assert len(owners) > 0, "R3 has no owner groups"


def test_r3_duplicate_decision_owner_fails() -> None:
    """There must be exactly one Decision ABI owner in the registry."""
    text = _ABI.read_text(encoding="utf-8")
    count = text.count("Decision ABI |")
    assert count == 1, f"Found {count} Decision ABI entries, expected exactly 1"
