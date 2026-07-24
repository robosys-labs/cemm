from __future__ import annotations

from types import SimpleNamespace

import pytest

from cemm.v350.cycle_control import CompletionEvaluator, CycleCompletionStatus, CycleWorkspace
from cemm.v350.effects.authorization import EffectAuthorizationBoundary
from cemm.v350.effects.store import AuthorizedEffectStore
from cemm.v350.orchestration import CoreStage, StageCapability
from cemm.v350.runtime_generations import ReadGeneration
from cemm.v350.schema.model import SchemaLifecycleStatus, UseDecision, UseOperation
from cemm.v350.semantic_capability import CompiledSemanticCapabilityRegistry
from cemm.v350.storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordKind
from cemm.v350.workspace_store import CycleArtifactStoreView
from cemm.v350.learning.model import PinnedRecord


class FakeStore:
    revision = 0
    def current_authority_snapshot(self):
        return SimpleNamespace(generation=1, authority_fingerprint="auth")
    def get_record(self, *_args, **_kwargs): return None
    def is_invalidated(self, *_args, **_kwargs): return False
    def apply_patch(self, _patch): raise AssertionError("forbidden patch reached mutable store")


class ReadView:
    pass


def read_generation():
    return ReadGeneration(
        store_revision=0, authority_generation=1, authority_fingerprint="auth",
        world_revision=0, discourse_revision=0, runtime_observation_revision=0,
        audit_revision=0, effect_journal_revision=0, overlay_fingerprint="overlay", boot_fingerprint="boot",
    )


def test_forbidden_generation_write_is_denied_before_apply_patch():
    store = FakeStore()
    cap = StageCapability(
        cycle_ref="c", pass_ref="p", stage=CoreStage.PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE,
        nonce="n", predecessor_stage=None, authority_generation=1, authority_fingerprint="auth",
        read_generation=read_generation(),
    )
    writer = AuthorizedEffectStore(
        base_store=store, read_store=ReadView(), boundary=EffectAuthorizationBoundary(store),
        capability=cap, permission_ref="conversation", context_ref="conversation",
    )
    patch = GraphPatch(
        patch_ref="patch:world", context_ref="conversation", scope_ref="test", source_ref="source:test",
        permission_ref="conversation", expected_store_revision=0,
        operations=(PatchOperation(
            operation_ref="op:world", operation_kind=PatchOperationKind.UPSERT,
            record_kind=RecordKind.EVIDENCE, target_ref="evidence:x", record_revision=1,
            payload={"x": "y"}, reason="attempt forbidden world write from Stage 14",
        ),),
    )
    receipt = writer.authorize_patch(patch)
    assert not receipt.allowed
    assert any("forbidden_generation_domains" in reason for reason in receipt.reason_refs)
    with pytest.raises(PermissionError):
        writer.authorize_and_apply_patch(patch)


def test_cycle_store_exposes_no_obvious_mutable_base_handle():
    view = object.__new__(CycleArtifactStoreView)
    with pytest.raises(AttributeError):
        _ = view.base_store
    with pytest.raises(AttributeError):
        _ = view.workspace
    with pytest.raises(AttributeError):
        _ = view.apply_patch


def test_completion_evaluator_uses_v351_artifacts_not_uol_aliases():
    cycle = SimpleNamespace(
        errors=[], input_payload=SimpleNamespace(response_requested=True),
        artifacts={"response_decision": object(), "surface_candidates": ()},
        workspace=CycleWorkspace(),
    )
    assert CompletionEvaluator().evaluate(cycle) is CycleCompletionStatus.RESPONSE_DEFERRED
    cycle.artifacts["emission_observation"] = object()
    assert CompletionEvaluator().evaluate(cycle) is CycleCompletionStatus.SUCCESS
