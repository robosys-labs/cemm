"""Import-boundary tests for the package-level public API."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

PUBLIC_EXPORTS = (
    "ABIRegistry",
    "CycleFinalizer",
    "CycleResult",
    "CycleStatus",
    "GapClassifier",
    "GapReceipt",
    "HybridRuntime",
    "MissingOwner",
    "Orientation",
    "PhaseDisposition",
    "PhaseReceipt",
    "ProposalOwner",
    "ProposalResult",
    "RevisionPin",
    "RuntimeConfig",
    "RuntimeOrientationOwner",
    "SemanticExpression",
    "SemanticMode",
    "SemanticPhase",
    "SemanticStores",
    "SemanticSwitchProgram",
    "VerificationBatch",
    "VerifiedMeaning",
    "load_runtime",
    "open_stores",
)

HEAVY_MODULES = (
    "cemm_authoritative_hybrid.model",
    "cemm_authoritative_hybrid.runtime",
    "cemm_authoritative_hybrid.training",
    "torch",
)


def _run_probe(source: str) -> dict[str, Any]:
    script = "\n".join(
        (
            "import json",
            "import sys",
            "sys.path.insert(0, sys.argv[1])",
            source,
        )
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script, str(SRC)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_bare_package_import_and_dir_remain_lightweight() -> None:
    payload = _run_probe(
        f"""
import cemm_authoritative_hybrid as package
before_dir = sorted(set({HEAVY_MODULES!r}) & set(sys.modules))
listed = dir(package)
after_dir = sorted(set({HEAVY_MODULES!r}) & set(sys.modules))
print(json.dumps({{
    "after_dir": after_dir,
    "before_dir": before_dir,
    "dir_is_sorted": listed == sorted(listed),
    "missing_exports": sorted(set(package.__all__) - set(listed)),
}}))
"""
    )

    assert payload == {
        "after_dir": [],
        "before_dir": [],
        "dir_is_sorted": True,
        "missing_exports": [],
    }


def test_package_preserves_exact_public_exports_and_resolves_each_one() -> None:
    payload = _run_probe(
        """
import importlib
import cemm_authoritative_hybrid as package
unresolved = []
wrong_owner = []
for name in package.__all__:
    try:
        value = getattr(package, name)
        module_name, attribute_name = package._EXPORTS[name]
        owner = importlib.import_module(module_name, package.__name__)
        if value is not getattr(owner, attribute_name):
            wrong_owner.append(name)
    except (AttributeError, ImportError) as exc:
        unresolved.append([name, type(exc).__name__])
print(json.dumps({
    "exports": package.__all__,
    "unresolved": unresolved,
    "wrong_owner": wrong_owner,
}))
"""
    )

    assert tuple(payload["exports"]) == PUBLIC_EXPORTS
    assert payload["unresolved"] == []
    assert payload["wrong_owner"] == []


def test_lazy_export_resolution_loads_only_its_owner_and_caches_value() -> None:
    payload = _run_probe(
        """
import cemm_authoritative_hybrid as package
owner_module = "cemm_authoritative_hybrid.config"
owner_loaded_before = owner_module in sys.modules
first = package.ABIRegistry
owner_loaded_after = owner_module in sys.modules
second = package.ABIRegistry
print(json.dumps({
    "cached": first is second and package.__dict__["ABIRegistry"] is first,
    "owner_loaded_after": owner_loaded_after,
    "owner_loaded_before": owner_loaded_before,
    "runtime_loaded": "cemm_authoritative_hybrid.runtime" in sys.modules,
}))
"""
    )

    assert payload == {
        "cached": True,
        "owner_loaded_after": True,
        "owner_loaded_before": False,
        "runtime_loaded": False,
    }


def test_unknown_package_attribute_fails_without_loading_exports() -> None:
    payload = _run_probe(
        """
import cemm_authoritative_hybrid as package
try:
    package.not_a_public_export
except AttributeError as exc:
    error = str(exc)
else:
    error = None
print(json.dumps({
    "error": error,
    "runtime_loaded": "cemm_authoritative_hybrid.runtime" in sys.modules,
}))
"""
    )

    assert payload == {
        "error": (
            "module 'cemm_authoritative_hybrid' has no attribute "
            "'not_a_public_export'"
        ),
        "runtime_loaded": False,
    }


__cemm_test_inventory__ = {
    "tests/test_lazy_package_imports.py::test_bare_package_import_and_dir_remain_lightweight": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:lazy-package-import-and-dir-remain-lightweight",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "9e1b5fe2931e702bdc909239bd2da2308f0d11562c066a746cdb1c7286bf31b1",
    },
    "tests/test_lazy_package_imports.py::test_lazy_export_resolution_loads_only_its_owner_and_caches_value": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:lazy-package-export-owner-and-cache",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "1d47141b1462de31bdff0c3fce2301c40b84ae1a857496ddc44bdf951200cd2b",
    },
    "tests/test_lazy_package_imports.py::test_package_preserves_exact_public_exports_and_resolves_each_one": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:lazy-package-preserves-public-exports",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "92e0c332fb15f9959731d963c003c6497274bdedaa14b207d29ad45268e275d0",
    },
    "tests/test_lazy_package_imports.py::test_unknown_package_attribute_fails_without_loading_exports": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:lazy-package-unknown-attribute-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "G0-Task-4",
        "owner_ref": "validation-runner",
        "source_ast_sha256": "75d18c0c1fcee8648117a7f865e6e3f2ce40f44c7f44d3348ebd35de038a0c61",
    },
}
