from pathlib import Path

from cemm.v350.maintenance import MaintenanceEvent, MaintenanceTrigger
from cemm.v350.learning.maintenance_v351 import Phase14LearningMaintenanceV351
from cemm.v350.storage import SemanticStore


def test_event_driven_maintenance_never_global_scans_on_empty_ref_set():
    store = SemanticStore()
    try:
        result = Phase14LearningMaintenanceV351(store).handle(
            MaintenanceEvent(MaintenanceTrigger.LEARNING_EVIDENCE_CHANGED, (), "ctx", "conversation")
        )
        assert not result.promoted_package_refs
        assert "maintenance:explicit-package-refs-required" in result.blocked_refs
        assert not result.restart_required
    finally:
        store.close()


def test_legacy_advancer_patch_forbids_implicit_global_frontier_scan_and_revision_severing():
    # Source-level regression: these are safety properties of the baseline patch itself.
    root = Path(__file__).resolve().parents[2]
    apply_script = (root / "apply_phases13_14.py").read_text(encoding="utf-8")
    assert "requires explicit event-targeted frontier_refs" in apply_script
    assert "frontiers = ()" in apply_script
    assert "Never sever exact competence/evidence lineage with a synthetic PROMOTABLE" in apply_script
