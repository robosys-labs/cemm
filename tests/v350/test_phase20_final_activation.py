from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

from cemm.v350.operations.executor import ReconciliationCoordinator
from cemm.v350.orchestration import CoreStage
from cemm.v350.runtime import CanonicalRuntimeCoordinator
from cemm.v350.runtime_artifacts import RuntimeInput
from cemm.v350.runtime_graph import canonical_stage_descriptors, resolve_adapter_type
from cemm.v350.transitions.coordinator import TransitionCoordinator

ROOT=Path(__file__).resolve().parents[2]


def test_canonical_runtime_has_exact_concrete_stage_0_through_22_graph():
    descriptors=canonical_stage_descriptors()
    assert tuple(item.stage for item in descriptors)==tuple(CoreStage)
    assert len(descriptors)==23
    assert len({item.adapter_ref for item in descriptors})==23
    assert len({item.adapter_class_path for item in descriptors})==23
    assert len({item.handler_name for item in descriptors})==23
    for item in descriptors:
        cls=resolve_adapter_type(item)
        assert getattr(cls,"HANDLER")==item.handler_name
        assert callable(getattr(CanonicalRuntimeCoordinator,item.handler_name))


def test_external_side_effect_and_store_mutation_ownership_is_explicit():
    descriptors=canonical_stage_descriptors()
    assert {int(x.stage) for x in descriptors if x.permits_external_side_effect}=={16,20}
    assert {int(x.stage) for x in descriptors if x.mutates_semantic_store}==set(range(13,22))


def test_source_manifest_is_fail_closed_but_topologically_real():
    path=ROOT/"cemm/data/v350/runtime_authority_manifest.json"
    doc=json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(doc["activation_ready"], bool)
    assert doc["metadata"]["generated_from_canonical_stage_graph"] is True
    source=json.loads((ROOT/"cemm/data/v350/manifest.json").read_text(encoding="utf-8"))
    if doc["activation_ready"]:
        assert source["metadata"].get("runtime_cutover") is True
        if doc.get("release_capabilities", {}).get("external_operations"):
            assert doc["operation_adapter_contracts"]
        else:
            assert doc["operation_adapter_contracts"] == []
        assert doc["semantic_analyzer_contracts"]
        assert doc["channel_adapter_contracts"]
    if not doc["activation_ready"]:
        assert doc["metadata"].get("preactivation") is True
    assert [item["stage"] for item in doc["stage_adapters"]]==list(range(23))
    by_stage={item["stage"]:item for item in doc["stage_adapters"]}
    for descriptor in canonical_stage_descriptors():
        item=by_stage[int(descriptor.stage)]
        assert item["adapter_ref"]==descriptor.adapter_ref
        assert item["factory_path"]==descriptor.adapter_class_path
        assert item["handler_name"]==descriptor.handler_name
        assert item["mutates_semantic_store"]==descriptor.mutates_semantic_store
        assert item["permits_external_side_effect"]==descriptor.permits_external_side_effect


def test_public_runtime_surfaces_have_no_legacy_v347_import_authority():
    files=("cemm/__init__.py","cemm/app/runtime.py","cemm/__main__.py","cemm/uol/__init__.py","cemm/web_demo.py")
    forbidden=("cemm.v347","cemm.migration","cemm.v350.migration")
    for rel in files:
        source=(ROOT/rel).read_text(encoding="utf-8")
        assert "v347" not in source
        tree=ast.parse(source)
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): imports.extend(alias.name for alias in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module: imports.append(node.module)
        assert not [name for name in imports if any(name==p or name.startswith(p+".") for p in forbidden)]


def test_runtime_input_carries_grounding_evidence_without_semantic_routing():
    class Anchor:
        anchor_ref="anchor:test"
    class Track:
        track_ref="track:test"
    class Output:
        output_ref="output:test"
    class Constraint:
        constraint_ref="constraint:test"
    item=RuntimeInput("x",discourse_anchors=(Anchor(),),multimodal_tracks=(Track(),),system_output_anchors=(Output(),),grounding_constraints=(Constraint(),))
    assert item.discourse_anchors[0].anchor_ref=="anchor:test"


def test_transition_preview_has_non_durable_staged_entrypoint():
    assert "plans_for_staged_event" in TransitionCoordinator.__dict__
    source=inspect.getsource(TransitionCoordinator.plans_for_staged_event)
    assert "StagedResolver" in source
    assert "apply_patch" not in source


def test_operation_reconciliation_requires_exact_observed_journal_pin():
    signature=inspect.signature(ReconciliationCoordinator.build)
    assert "observed_journal_pin" in signature.parameters
    assert signature.parameters["observed_journal_pin"].default is inspect.Signature.empty


def test_final_activation_verifier_rejects_current_manifest_without_live_runtime_authority(monkeypatch):
    import tools.verify_v350_phase20 as verifier

    monkeypatch.setattr("sys.argv", ["verify_v350_phase20.py"])
    rc=verifier.main()

    assert rc == 1
