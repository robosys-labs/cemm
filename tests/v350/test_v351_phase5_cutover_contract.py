from __future__ import annotations

from pathlib import Path

from cemm.v350.stage_contracts import canonical_stage_contracts
from cemm.v350.version import MANIFEST, VERSION

ROOT = Path(__file__).resolve().parents[2]


def test_active_version_authority_is_v351_csir_not_uol():
    assert VERSION == "3.5.1"
    assert MANIFEST.core_loop_revision == "stage0-22-v351-csir-recurrent"
    assert MANIFEST.semantic_ir_model == "csir-v2"
    assert not hasattr(MANIFEST, "uol_model")


def test_cutover_requires_manifest_v3_before_service_import_resolution():
    source = (ROOT / "cemm/v350/cutover.py").read_text(encoding="utf-8")
    version_guard = source.index("if m.manifest_version < 5")
    service_loop = source.index("for item in m.runtime_service_bindings")
    assert version_guard < service_loop
    assert 'm.release_version != "3.5.1"' in source
    assert "runtime authority manifest v5 is required for final v3.5.1 cutover" in source


def test_cutover_uses_stage_contract_fingerprint_not_legacy_mutation_booleans():
    source = (ROOT / "cemm/v350/cutover.py").read_text(encoding="utf-8")
    assert "authority.contract_fingerprint" in source
    assert "descriptor.contract.fingerprint" in source
    graph = (ROOT / "cemm/v350/runtime_graph.py").read_text(encoding="utf-8")
    assert "def mutates_semantic_store" not in graph
    assert "def permits_external_side_effect" not in graph


def test_no_stale_en_fr_sw_activation_requirement():
    source = (ROOT / "cemm/v350/cutover.py").read_text(encoding="utf-8")
    assert 'not {"en", "fr", "sw"}.issubset' not in source
    assert "english_conversational_kernel" in source
    assert "realization_languages" in source


def test_all_stage_contracts_have_manifest_fingerprints():
    contracts = canonical_stage_contracts()
    assert len(contracts) == 23
    assert all(item.fingerprint.startswith("stage-contract-v351:") for item in contracts)


def test_signed_runtime_services_require_explicit_v351_abi_declaration():
    source = (ROOT / "cemm/v350/service_loader.py").read_text(encoding="utf-8")
    assert 'binding.get("runtime_abi", "")' in source
    assert 'getattr(cls, "RUNTIME_ABI", None) != "v351"' in source
    assert 'getattr(cls, "SERVICE_KIND", None)' in source


def test_activation_ready_requires_real_csir_and_recurrent_semantic_capabilities():
    source = (ROOT / "cemm/v350/cutover.py").read_text(encoding="utf-8")
    assert '("csir_compilation", "recurrent_semantics")' in source
    assert "activation-ready v3.5.1 release lacks required capability" in source
