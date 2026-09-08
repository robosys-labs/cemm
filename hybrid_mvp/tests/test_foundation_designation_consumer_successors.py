"""Authentic publication successors for retired mutable-index test doubles."""
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.authority import AuthorityLinker
from tests.test_foundation_designation_consumers import _publish_alias
from tests.test_foundation_learning_proposal import ROOT

__cemm_test_inventory__ = {
    "tests/test_foundation_designation_consumer_successors.py::test_admitted_designation_inherits_target_without_pack_regeneration": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:grounding-new-designation-uses-target-affordance-without-pack-regeneration",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-5",
        "source_ast_sha256": "da3c9222b65019644e02835d833be0fd59bdff5c1d8ae0caaec05c31a5e6aeba",
        "supersedes_node_id": "tests/test_grounding.py::test_new_designation_uses_target_affordance_without_pack_regeneration"
    },
    "tests/test_foundation_designation_consumer_successors.py::test_admitted_designation_preserves_form_pack_hash": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:grounding-adding-designation-does-not-change-form-pack-hash",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-5",
        "source_ast_sha256": "d57a45e89748db5cd0d68aca8e1a04c47ad83222469563e020436180636aefdb",
        "supersedes_node_id": "tests/test_grounding.py::test_adding_designation_does_not_change_form_pack_hash"
    },
    "tests/test_foundation_designation_consumer_successors.py::test_admitted_designation_preserves_relinked_authority": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:grounding-adding-designation-changes-authority-generation",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-5",
        "source_ast_sha256": "043114566510b740706b19674e78dbd83ca4896d0e0e378ae9b525bec78d9466",
        "supersedes_node_id": "tests/test_grounding.py::test_designation_store_addition_does_not_alter_authority_files"
    }
}


def test_admitted_designation_inherits_target_without_pack_regeneration(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "affordance.db")
    try:
        grounder = runtime._owners["orientation"]._grounder
        before_hash = grounder.form_pack_hash
        before_pack = (ROOT / "data/languages/en/forms.json").read_bytes()
        receipt = _publish_alias(runtime, "nuvemora", "mother", "concept:mother")
        _, context = runtime.orient("session:unseen", "Alice is a nuvemora.")
        predicate = next(row for row in context.application_frames if row.operator_ref == "op:type")
        designation = context.designation(predicate.designation_slot_ref)
        assert designation.target_ref == "concept:mother"
        assert receipt.committed_fact_refs[0] in designation.provenance_refs
        assert grounder.form_pack_hash == before_hash
        assert (ROOT / "data/languages/en/forms.json").read_bytes() == before_pack
    finally:
        runtime.stores.close()


def test_admitted_designation_preserves_form_pack_hash(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "form.db")
    try:
        grounder = runtime._owners["orientation"]._grounder
        before = grounder.form_pack_hash
        _publish_alias(runtime, "nuvemora", "mother", "concept:mother")
        assert grounder.form_pack_hash == before
        assert runtime.stores.world.revision == 1
    finally:
        runtime.stores.close()


def test_admitted_designation_preserves_relinked_authority(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "authority.db")
    try:
        original_generation = runtime.authority.generation
        original_hash = runtime.authority.content_hash
        form_hash = runtime._owners["orientation"]._grounder.form_pack_hash
        _publish_alias(runtime, "nuvemora", "mother", "concept:mother")
        assert form_hash != original_hash
        relinked = AuthorityLinker().link_path(ROOT / "data/authority/manifest.json")
        assert relinked.content_hash == original_hash
        assert relinked.generation == original_generation
        _, context = runtime.orient("session:relinked", "nuvemora")
        assert context.designation_slots[0].target_ref == "concept:mother"
        assert runtime.stores.world.revision == 1
    finally:
        runtime.stores.close()
