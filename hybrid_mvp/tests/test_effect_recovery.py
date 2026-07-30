"""Tests for effect recovery and restart semantics.

Tests cover:
- Restart reads the journal before retry (completed effects are not re-invoked).
- Timeout/partial failure remains unresolved and never admits predicted success.
- Idempotency survives journal reconstruction (new journal reads existing store).
- Pending effects do not commit to the effect store.
"""

from __future__ import annotations

from typing import Any

import pytest

from cemm_authoritative_hybrid.authority import EventSignature, RoleSpec
from cemm_authoritative_hybrid.capabilities import (
    CapabilityContext,
    CapabilityEngine,
)
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.effects import (
    AdapterReceipt,
    AdapterRegistry,
    EffectGateway,
    EffectJournal,
    EffectPlan,
    EffectReceipt,
    EffectVerifier,
    ObservationValidator,
    PendingEffect,
)
from cemm_authoritative_hybrid.persistence import RevisionPin, memory_stores


# ---------------------------------------------------------------------------
# Test-only authority
# ---------------------------------------------------------------------------


class _RecoveryAuthority:
    """Minimal authority-like object for recovery tests."""

    generation = "authority:recovery-test-v1"
    content_hash = "test-content"
    model_compatibility_hash = "test-compat"
    capabilities = {"participant:system": ["cap:open_door"]}
    permissions = ()
    adapters = ()
    operator_roles = {}
    value_dimensions = {}

    _event_sigs = {
        "event:open": EventSignature(
            event_type="event:open",
            roles=(RoleSpec(role="role:actor", filler_kinds=("participant",)),),
            required_capabilities=("cap:open_door",),
            required_permissions=("permission:door",),
            adapter_ref="adapter:door",
            effect_schema=(
                {"kind": "resource", "resource": "resource:door"},
            ),
        ),
    }

    def by_kind(self, kind: str) -> frozenset[str]:
        return frozenset()

    def by_transition(self, key: str) -> dict[str, Any] | None:
        return None

    def by_event_signature(self, event_type: str) -> EventSignature | None:
        return self._event_sigs.get(event_type)

    def by_state_dimension(self, dim: str) -> frozenset[str]:
        return frozenset()


# ---------------------------------------------------------------------------
# Test adapters
# ---------------------------------------------------------------------------


class CountingAdapter:
    """A simple adapter that counts calls."""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, pending: PendingEffect) -> AdapterReceipt:
        self.calls += 1
        return AdapterReceipt(
            adapter_ref="adapter:door",
            status="succeeded",
            payload={"action": "open"},
            receipt_ref=f"adapter_receipt:{pending.plan.idempotency_key}",
        )


class TimeoutAdapter:
    """An adapter that always times out."""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, pending: PendingEffect) -> AdapterReceipt:
        self.calls += 1
        return AdapterReceipt(
            adapter_ref="adapter:door",
            status="timeout",
            payload={},
            receipt_ref=f"timeout:{pending.plan.idempotency_key}",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _revision_pin() -> RevisionPin:
    return RevisionPin(
        authority_generation="authority:recovery-test-v1",
        world_revision=0,
        session_revision=0,
        episode_revision=0,
        effect_revision=0,
        model_identity=None,
    )


def _capability_context() -> CapabilityContext:
    return CapabilityContext(
        actor_ref="participant:system",
        event_type_ref="event:open",
        current_state=None,
        resources=("resource:door",),
        permissions=("permission:door",),
        adapters=("adapter:door",),
        revisions=_revision_pin(),
    )


def _plan(
    *,
    idempotency_key: str = "idem:open-door-1",
    expected_world_revision: int = 0,
) -> EffectPlan:
    return EffectPlan(
        effect_ref="effect:open-door-1",
        idempotency_key=idempotency_key,
        program_ref="program:open-door",
        actor_ref="participant:system",
        transition_ref="transition:open_door",
        expected_world_revision=expected_world_revision,
        requirement_proof_refs=("proof:cap:open_door",),
    )


def _make_gateway(
    stores,
    adapter,
    *,
    authority=None,
    config=None,
):
    """Build a gateway with the given stores and adapter."""
    authority = authority or _RecoveryAuthority()
    config = config or RuntimeConfig.release()
    cap_engine = CapabilityEngine(authority, config)
    verifier = EffectVerifier(cap_engine, default_context=_capability_context())
    journal = EffectJournal(stores)
    adapter_registry = AdapterRegistry({"adapter:door": adapter})
    observations = ObservationValidator()
    return EffectGateway(
        verifier=verifier,
        journal=journal,
        adapters=adapter_registry,
        observations=observations,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authority() -> _RecoveryAuthority:
    return _RecoveryAuthority()


@pytest.fixture
def config() -> RuntimeConfig:
    return RuntimeConfig.release()


@pytest.fixture
def stores(authority):
    return memory_stores(authority_generation=authority.generation)


@pytest.fixture
def counting_adapter() -> CountingAdapter:
    return CountingAdapter()


@pytest.fixture
def gateway(stores, counting_adapter) -> EffectGateway:
    return _make_gateway(stores, counting_adapter)


@pytest.fixture
def plan() -> EffectPlan:
    return _plan()


# ---------------------------------------------------------------------------
# Tests: restart reads journal before retry
# ---------------------------------------------------------------------------


class TestRestartReadsJournalBeforeRetry:
    def test_new_journal_finds_completed_effect(self, stores, counting_adapter):
        """A new journal constructed over the same store finds the completed effect."""
        gateway1 = _make_gateway(stores, counting_adapter)
        plan = _plan()
        first = gateway1.execute(plan)
        assert first.status == "committed"
        assert counting_adapter.calls == 1

        # Simulate restart: new journal over the same store, new adapter.
        new_adapter = CountingAdapter()
        gateway2 = _make_gateway(stores, new_adapter)
        second = gateway2.execute(plan)
        assert second.status == "committed"
        assert second == first
        # The new adapter was NOT called — the journal found the completed effect.
        assert new_adapter.calls == 0

    def test_retry_after_restart_does_not_duplicate(self, stores, counting_adapter):
        """Retry after restart does not duplicate the external effect."""
        gateway1 = _make_gateway(stores, counting_adapter)
        plan = _plan()
        gateway1.execute(plan)
        assert counting_adapter.calls == 1

        # Restart with a fresh gateway over the same stores.
        new_adapter = CountingAdapter()
        gateway2 = _make_gateway(stores, new_adapter)
        gateway2.execute(plan)
        assert new_adapter.calls == 0

    def test_journal_lookup_by_idempotency_key(self, stores):
        """The journal looks up completed effects by idempotency key."""
        adapter = CountingAdapter()
        gateway = _make_gateway(stores, adapter)
        plan = _plan(idempotency_key="idem:unique-key")
        receipt = gateway.execute(plan)
        assert receipt.status == "committed"

        # A new journal over the same store should find it.
        new_journal = EffectJournal(stores)
        found = new_journal.lookup("idem:unique-key")
        assert found is not None
        assert found.status == "committed"


# ---------------------------------------------------------------------------
# Tests: timeout / partial failure remains unresolved
# ---------------------------------------------------------------------------


class TestTimeoutRemainsUnresolved:
    def test_timeout_produces_pending_receipt(self, stores):
        """A timeout produces a pending receipt, never a predicted success."""
        adapter = TimeoutAdapter()
        gateway = _make_gateway(stores, adapter)
        receipt = gateway.execute(_plan())
        assert receipt.status == "pending"
        assert adapter.calls == 1

    def test_pending_never_admits_predicted_success(self, stores):
        """A pending effect never admits predicted success."""
        adapter = TimeoutAdapter()
        gateway = _make_gateway(stores, adapter)
        receipt = gateway.execute(_plan())
        assert receipt.status != "committed"
        assert receipt.status == "pending"

    def test_pending_does_not_commit_to_store(self, stores):
        """A pending effect does not increment the effect store revision."""
        adapter = TimeoutAdapter()
        gateway = _make_gateway(stores, adapter)
        before = stores.effects.revision
        gateway.execute(_plan())
        assert stores.effects.revision == before

    def test_retry_after_timeout_re_invokes_adapter(self, stores):
        """Retry after a timeout re-invokes the adapter (not yet completed)."""
        adapter = TimeoutAdapter()
        gateway = _make_gateway(stores, adapter)
        plan = _plan()
        first = gateway.execute(plan)
        assert first.status == "pending"
        assert adapter.calls == 1

        # Retry — the effect was not completed, so the adapter is called again.
        second = gateway.execute(plan)
        assert second.status == "pending"
        assert adapter.calls == 2


# ---------------------------------------------------------------------------
# Tests: idempotency integrity
# ---------------------------------------------------------------------------


class TestIdempotencyIntegrity:
    def test_completed_effect_is_deterministic(self, stores, counting_adapter):
        """Executing the same plan twice returns identical receipts."""
        gateway = _make_gateway(stores, counting_adapter)
        plan = _plan()
        first = gateway.execute(plan)
        second = gateway.execute(plan)
        assert first == second
        assert first.effect_ref == plan.effect_ref
        assert first.status == "committed"

    def test_effect_store_has_unique_key(self, stores, counting_adapter):
        """The effect store enforces unique effect keys (no duplicate commits)."""
        gateway = _make_gateway(stores, counting_adapter)
        plan = _plan()
        gateway.execute(plan)
        before = stores.effects.revision
        # Second execute should not create a new effect store entry.
        gateway.execute(plan)
        assert stores.effects.revision == before
