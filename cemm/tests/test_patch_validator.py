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
from cemm.types.claim import Claim, ClaimStatus
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
    assert patch.operations[0].operation == "upsert_relation_candidate"
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
    # Claim is NOT written directly to store — must go through GraphPatch validation
    stored = store.claims.get(cid)
    assert stored is None


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


# ── Phase 8: MMU upgrade tests ───────────────────────────────────────────────


def test_validation_result_has_check_results() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t")],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert len(result.check_results) > 0
    assert all(hasattr(c, "check_name") for c in result.check_results)
    assert all(hasattr(c, "passed") for c in result.check_results)


def test_validation_result_has_accepted_operations() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "t1" in result.accepted_operations


def test_validation_result_has_rejected_operations() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[
            PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7),
            PatchOperation(operation="custom:upsert_claim", target_id="", confidence=0.7),
        ],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "t1" in result.accepted_operations
    assert len(result.rejected_operations) == 1
    assert "missing target_id" in result.rejected_operations[0]


def test_validator_detects_contradiction() -> None:
    store = Store(":memory:")
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
        registry=Registry(),
        params={
            "subject_entity_id": "entity_x",
            "predicate": "color",
            "object_value": "red",
        },
    )
    # Execute RememberOperator (no longer directly writes to store)
    RememberOperator().execute(ctx)

    # Directly insert a claim into the store to simulate an already-committed claim
    # (in production this happens through the GraphPatch pipeline → LegacyClaimAdapter)
    claim = Claim(
        id=uuid.uuid4().hex[:16],
        subject_entity_id="entity_x",
        predicate="color",
        object_value="red",
        status=ClaimStatus.ACTIVE,
        confidence=0.8,
        trust=0.7,
        observed_at=time.time(),
        updated_at=time.time(),
    )
    store.claims.put(claim)

    # Now try to store a contradictory claim
    compiler = MemoryPatchCompiler()
    validator = PatchValidator(store=store, contradiction_threshold=0.5)
    patch = compiler.compile(
        subject_entity_id="entity_x",
        predicate="color",
        object_value="blue",
        evidence_signal_ids=[signal.id],
        source_id="user",
        confidence=0.8,
    )
    result = validator.validate(patch, kernel)
    assert "contradiction_absent_or_resolved" in result.failed_checks
    assert "contradicts active claim" in result.reasons[0]


def test_validator_quarantines_low_score_patch() -> None:
    patch = GraphPatch(
        source_refs=[],
        evidence_refs=[],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="")],
        confidence=0.05,
    )
    result = PatchValidator(min_confidence=0.3).validate(patch, _kernel())
    assert result.status in ("quarantined", "rejected", "needs_confirmation")
    assert result.quarantine_reason or result.reasons


def test_validator_schema_compatibility_pass() -> None:
    from cemm.memory.predicate_schema_store import PredicateSchemaStore
    store = PredicateSchemaStore()
    validator = PatchValidator(schema_store=store)
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(
            operation="observe_predicate_schema",
            target_id="schema:is_a",
            fields={"predicate_key": "is_a", "argument_roles": ["child", "parent"]},
            confidence=0.7,
        )],
        confidence=0.7,
    )
    result = validator.validate(patch, _kernel())
    assert "schema_compatible" not in result.failed_checks


def test_validator_schema_compatibility_fails() -> None:
    from cemm.memory.predicate_schema_store import PredicateSchemaStore
    store = PredicateSchemaStore()
    validator = PatchValidator(schema_store=store)
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(
            operation="observe_predicate_schema",
            target_id="schema:is_a",
            fields={"predicate_key": "is_a", "argument_roles": ["child"]},
            confidence=0.7,
        )],
        confidence=0.7,
    )
    result = validator.validate(patch, _kernel())
    assert "schema_compatible" in result.failed_checks
    assert "missing required role" in result.reasons[0]


def test_validator_reversibility_check() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(
            operation="merge_concepts",
            target_id="concept_a:concept_b",
            confidence=0.7,
        )],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "reversibility_ok" in result.failed_checks


def test_validator_reversibility_passes_with_inverse() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(
            operation="merge_concepts",
            target_id="concept_a:concept_b",
            confidence=0.7,
        )],
        inverse_operations=[PatchOperation(
            operation="custom:upsert_claim",
            target_id="concept_a:concept_b",
            confidence=0.7,
        )],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "reversibility_ok" not in result.failed_checks


def test_validator_custom_upsert_claim_needs_confirmation() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "t1" in result.required_user_confirmation


def test_validator_freshness_rejects_stale_evidence() -> None:
    store = Store(":memory:")
    kernel = _kernel()
    old_time = time.time() - 7200
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="old evidence",
        observed_at=old_time,
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )
    store.signals.put(signal)
    kernel.time.now = time.time()
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=[signal.id],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator(store=store).validate(patch, kernel)
    assert "freshness_valid" in result.failed_checks


# ── Temporal scope tests ──────────────────────────────────────────────────


def test_temporal_stale_evidence() -> None:
    store = Store(":memory:")
    kernel = _kernel()
    old_time = time.time() - 90000
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="old temporal evidence",
        observed_at=old_time,
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )
    store.signals.put(signal)
    kernel.time.now = time.time()
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=[signal.id],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator(store=store, temporal_threshold=86400).validate(patch, kernel)
    assert "temporal_scope_valid" in result.failed_checks
    assert any("outside temporal scope" in r for r in result.reasons)


def test_temporal_fresh_evidence() -> None:
    store = Store(":memory:")
    kernel = _kernel()
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="fresh temporal evidence",
        observed_at=time.time(),
        context_id=kernel.id,
        salience=0.5,
        trust=0.8,
        permission=kernel.permission,
    )
    store.signals.put(signal)
    kernel.time.now = time.time()
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=[signal.id],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator(store=store, temporal_threshold=86400).validate(patch, kernel)
    assert "temporal_scope_valid" not in result.failed_checks


def test_temporal_no_evidence() -> None:
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=[],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, _kernel())
    assert "temporal_scope_valid" not in result.failed_checks


# ── Source trust tests ────────────────────────────────────────────────────


def test_source_trust_trusted_keys() -> None:
    kernel = _kernel()
    kernel.memory.source_trust_keys = ["trusted_source"]
    patch = GraphPatch(
        source_refs=["trusted_source"],
        evidence_refs=["ev1"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator().validate(patch, kernel)
    assert "source_trust_sufficient" not in result.failed_checks


def test_source_trust_untrusted_keys() -> None:
    kernel = _kernel()
    kernel.memory.source_trust_keys = ["trusted_source"]
    patch = GraphPatch(
        source_refs=["untrusted_source"],
        evidence_refs=["ev1"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.7,
    )
    result = PatchValidator(min_source_trust=0.6).validate(patch, kernel)
    assert "source_trust_sufficient" in result.failed_checks


def test_source_trust_fallback_confidence() -> None:
    kernel = _kernel()
    kernel.memory.source_trust_keys = []
    patch = GraphPatch(
        source_refs=["src1"],
        evidence_refs=["ev1"],
        operations=[PatchOperation(operation="custom:upsert_claim", target_id="t1", confidence=0.7)],
        confidence=0.05,
    )
    result = PatchValidator(min_source_trust=0.3).validate(patch, kernel)
    assert "source_trust_sufficient" in result.failed_checks


# ── Compression gain tests ────────────────────────────────────────────────


def test_compression_gain_novel() -> None:
    store = Store(":memory:")
    store.conn.execute("PRAGMA foreign_keys=OFF")
    from cemm.types.claim import Claim, ClaimStatus
    store.claims.put(Claim(
        id=uuid.uuid4().hex[:16],
        subject_entity_id="entity_x",
        predicate="color",
        object_value="blue",
        confidence=0.8,
        status=ClaimStatus.ACTIVE,
    ))
    store.conn.execute("PRAGMA foreign_keys=ON")
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev1"],
        operations=[PatchOperation(
            operation="upsert_relation_candidate",
            target_id="t1",
            fields={"subject_entity_id": "entity_x", "predicate": "color", "object_value": "green"},
            confidence=0.7,
        )],
        confidence=0.7,
    )
    result = PatchValidator(store=store).validate(patch, _kernel())
    assert "compression_gain" not in result.failed_checks


def test_compression_gain_duplicate() -> None:
    store = Store(":memory:")
    store.conn.execute("PRAGMA foreign_keys=OFF")
    from cemm.types.claim import Claim, ClaimStatus
    claim_id = uuid.uuid4().hex[:16]
    store.claims.put(Claim(
        id=claim_id,
        subject_entity_id="entity_x",
        predicate="color",
        object_value="blue",
        confidence=0.8,
        status=ClaimStatus.ACTIVE,
    ))
    store.conn.execute("PRAGMA foreign_keys=ON")
    patch = GraphPatch(
        source_refs=["src"],
        evidence_refs=["ev1"],
        operations=[PatchOperation(
            operation="upsert_relation_candidate",
            target_id="t1",
            fields={"subject_entity_id": "entity_x", "predicate": "color", "object_value": "blue"},
            confidence=0.7,
        )],
        confidence=0.7,
    )
    result = PatchValidator(store=store).validate(patch, _kernel())
    assert "compression_gain" in result.failed_checks
    assert "duplicates existing claim" in result.reasons[-1]
