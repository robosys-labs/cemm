"""Tests for Phase 4: PatchValidator, MemoryPatchCompiler, RememberOperator validation gate."""

from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.learning.patch_validator import PatchValidator, PatchValidationResult
from cemm.learning.memory_patch_compiler import MemoryPatchCompiler
from cemm.types.graph_patch import GraphPatch, PatchOperation
from cemm.types.context_kernel import ContextKernel, Budget, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState
from cemm.types.permission import Permission, PermissionScope
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.operators.remember import RememberOperator
from cemm.operators.base import OperatorContext
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.self_view import SelfView


def _kernel(permission=Permission.public()) -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(),
        user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id=uuid.uuid4().hex[:16], turn_index=1),
        goal=GoalState(),
        memory=MemoryState(),
        permission=permission,
        budget=Budget(),
        self_view=SelfView(self_id="test"),
    )


# ── PatchValidationResult ──────────────────────────────────────────────────


def test_validation_result_defaults() -> None:
    result = PatchValidationResult(patch_id="p1")
    assert result.patch_id == "p1"
    assert result.status == "rejected"
    assert result.reasons == []
    assert result.scores == {}
    assert result.failed_checks == []
    assert result.accepted is False
    assert result.mean_score == 0.0


def test_validation_result_accepted() -> None:
    result = PatchValidationResult(patch_id="p1", status="accepted", scores={"a": 1.0})
    assert result.accepted is True
    assert result.mean_score == 1.0


# ── PatchValidator ─────────────────────────────────────────────────────────


def test_validator_accepts_valid_patch() -> None:
    patch = GraphPatch(
        source_refs=["src1"],
        evidence_refs=["ev1"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="test:test")],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert result.accepted is True
    assert result.failed_checks == []


def test_validator_rejects_no_permission() -> None:
    patch = GraphPatch(
        source_refs=["src1"],
        evidence_refs=["ev1"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="test:test")],
        confidence=0.7,
    )
    restricted = Permission(scope=PermissionScope.PUBLIC, may_store=False)
    result = PatchValidator().validate(patch, _kernel(permission=restricted))
    assert result.accepted is False
    assert "permission_valid" in result.failed_checks


def test_validator_rejects_no_source() -> None:
    patch = GraphPatch(
        source_refs=[],
        evidence_refs=[],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t")],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "source_present" in result.failed_checks
    assert "evidence_present" in result.failed_checks


def test_validator_rejects_low_confidence() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t")],
        confidence=0.05,
    )
    result = PatchValidator(min_confidence=0.3).validate(patch, _kernel())
    assert "confidence_sufficient" in result.failed_checks


def test_validator_needs_confirmation() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=[],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t")],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert result.accepted is False
    assert result.status == "needs_confirmation"


def test_validator_rejects_empty_target_id() -> None:
    patch = GraphPatch(
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="")],
        source_refs=["src"],
        evidence_refs=["ev"],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "required_ports_bound" in result.failed_checks


# ── MemoryPatchCompiler ────────────────────────────────────────────────────


def test_compiler_produces_graph_patch() -> None:
    compiler = MemoryPatchCompiler()
    patch = compiler.compile(
        subject_entity_id="user",
        predicate="name",
        object_value="Alice",
        source_id="sig1",
    )
    assert isinstance(patch, GraphPatch)
    assert patch.target == "episodic_trace"
    assert len(patch.operations) == 1
    assert patch.operations[0].operation == "custom:upsert_claim"
    assert patch.source_refs == ["sig1"]


def test_compiler_attaches_evidence() -> None:
    compiler = MemoryPatchCompiler()
    patch = compiler.compile(
        subject_entity_id="entity_x",
        predicate="likes",
        object_value="pizza",
        evidence_signal_ids=["sig1", "sig2"],
        source_id="src1",
    )
    assert patch.evidence_refs == ["sig1", "sig2"]


def test_compiler_with_kernel() -> None:
    kernel = _kernel()
    compiler = MemoryPatchCompiler()
    patch = compiler.compile(
        subject_entity_id="user",
        predicate="name",
        object_value="Alice",
        kernel=kernel,
    )
    assert f"kernel:{kernel.id}" in patch.source_refs


# ── RememberOperator validation gate ───────────────────────────────────────


def test_remember_accepts_valid_claim() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel()
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="remember this",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )
    store.signals.put(signal)

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        params={
            "subject_entity_id": "entity_user",
            "predicate": "likes",
            "object_value": "Postgres",
        },
    )
    op = RememberOperator()
    result = op.execute(ctx)

    assert result.success is True
    assert len(result.new_claim_ids) == 1
    cid = result.new_claim_ids[0]
    stored = store.claims.get(cid)
    assert stored is not None


def test_remember_rejects_no_permission() -> None:
    store = Store(":memory:")
    registry = Registry()
    kernel = _kernel(permission=Permission(scope=PermissionScope.PUBLIC, may_store=False, may_execute=True))
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="remember this",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )
    store.signals.put(signal)

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=signal,
        store=store,
        registry=registry,
        params={
            "subject_entity_id": "entity_user",
            "predicate": "likes",
            "object_value": "Postgres",
        },
    )
    op = RememberOperator()
    result = op.execute(ctx)

    assert result.success is False
    assert "storage not allowed" in result.output_text
