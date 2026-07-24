from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_v347_package_does_not_reexport_runtime_or_wildcard_semantics():
    v347_init = ROOT / "cemm/v347/__init__.py"
    assert not v347_init.exists(), "cemm/v347 must remain absent after legacy removal"


def test_public_runtime_factory_is_v351_without_executable_legacy_fallback():
    canonical = (ROOT / "cemm/v350/runtime.py").read_text(encoding="utf-8")
    assert "runtime_v351" in canonical
    assert "MeaningComposer" not in canonical
    assert "SelectedUOLCommitPlanner" not in canonical
    assert not (ROOT / "cemm/v350/legacy_runtime_v350.py").exists()


def test_signed_service_loader_rejects_old_uol_runtime_service_module_before_import():
    from cemm.v350.service_loader import RuntimeServiceCompositionError, _resolve_class

    try:
        _resolve_class("cemm.v350.runtime_services:CanonicalSemanticAnalyzer")
    except RuntimeServiceCompositionError as exc:
        assert "legacy/migration service" in str(exc)
    else:
        raise AssertionError("legacy UOL runtime service module was accepted")


def test_active_version_manifest_does_not_declare_uol_as_semantic_model():
    from cemm.v350.version import MANIFEST, VERSION
    assert VERSION == "3.5.1"
    assert MANIFEST.semantic_ir_model == "csir-v2"
    assert not hasattr(MANIFEST, "uol_model")


def test_old_runtime_services_module_is_tombstoned_without_uol_imports():
    text = (ROOT / "cemm/v350/runtime_services.py").read_text(encoding="utf-8")
    assert "from .uol" not in text
    assert "LEGACY_RUNTIME_SERVICES_REMOVED = True" in text


def test_v347_executable_runtime_entrypoint_is_removed():
    assert not (ROOT / "cemm/v347/runtime.py").exists()
