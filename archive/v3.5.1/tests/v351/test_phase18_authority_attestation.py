from __future__ import annotations

from pathlib import Path

from cemm.v350.finalization.service_authority_v351 import SERVICE_SPECS
from cemm.v350.finalization.source_attestation_v351 import runtime_source_root_v351


def test_service_inventory_separates_runtime_slot_and_implementation_identity():
    specs = {slot: (path, methods) for slot, path, methods in SERVICE_SPECS}
    assert specs["operation_engine"][1] == ("prepare", "execute")
    assert specs["emission_engine"][1] == ("authorize", "emit")
    assert specs["consolidation_engine"][1] == ("finalize",)
    assert specs["clock"][1] == ("now_iso",)


def test_runtime_source_root_changes_with_source(tmp_path: Path):
    (tmp_path / "cemm/v350").mkdir(parents=True)
    source = tmp_path / "cemm/v350/a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    first, inventory = runtime_source_root_v351(tmp_path)
    assert inventory
    source.write_text("x = 2\n", encoding="utf-8")
    second, _ = runtime_source_root_v351(tmp_path)
    assert first != second
