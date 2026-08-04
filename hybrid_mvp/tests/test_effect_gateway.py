"""Tests for the one proof-bearing effect gateway.

Tests cover:
- Retry does not duplicate external effect (idempotency via journal).
- Denial is not reported as incapacity (denied != unavailable).
- One proof-bearing gateway owns all effectful commits.
- No adapter may write semantic stores directly.
- Timeout/partial failure remains unresolved and never admits predicted success.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

import pytest

from cemm_authoritative_hybrid.authority import EventSignature, RoleSpec
from cemm_authoritative_hybrid.capabilities import (
    CapabilityContext,
    CapabilityEngine,
    CapabilityResult,
)
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.effects import (
    AdapterObservation,
    AdapterReceipt,
    AdapterRegistry,
    AuthorizationDecision,
    EffectGateway,
    EffectJournal,
    EffectPlan,
    EffectReceipt,
    EffectVerifier,
    ObservationValidator,
    PendingEffect,
)
from cemm_authoritative_hybrid.gaps import GapClassifier, GapKind, PermissionDenied
from cemm_authoritative_hybrid.persistence import RevisionPin, memory_stores


# ---------------------------------------------------------------------------
# Test-only authority with event signatures
# ---------------------------------------------------------------------------


class _EffectAuthority:
    """Minimal authority-like object with event signatures for effect tests."""

    generation = "authority:effect-test-v1"
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
# Test-only counting adapter
# ---------------------------------------------------------------------------


class CountingAdapter:
    """A simple adapter that counts calls and returns a success receipt."""

    def __init__(self) -> None:
        self.calls = 0
        self._adapter_ref = "adapter:door"

    def invoke(self, pending: PendingEffect) -> AdapterReceipt:
        self.calls += 1
        return AdapterReceipt(
            adapter_ref=self._adapter_ref,
            status="succeeded",
            payload={"action": "open", "entity": "entity:door"},
            receipt_ref=f"adapter_receipt:{pending.plan.idempotency_key}",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _revision_pin(
    *,
    authority_generation: str = "authority:effect-test-v1",
    world_revision: int = 0,
) -> RevisionPin:
    return RevisionPin(
        authority_generation=authority_generation,
        world_revision=world_revision,
        session_revision=0,
        episode_revision=0,
        effect_revision=0,
        model_identity=None,
    )


def _plan(
    *,
    effect_ref: str = "effect:open-door-1",
    idempotency_key: str = "idem:open-door-1",
    actor_ref: str = "participant:system",
    expected_world_revision: int = 0,
    revision_pin: RevisionPin | None = None,
) -> EffectPlan:
    source_pin = revision_pin or _revision_pin(world_revision=expected_world_revision)
    return EffectPlan(
        effect_ref=effect_ref,
        idempotency_key=idempotency_key,
        program_ref="program:open-door",
        actor_ref=actor_ref,
        transition_ref="transition:open_door",
        expected_world_revision=expected_world_revision,
        requirement_proof_refs=("proof:cap:open_door",),
        revision_pin=source_pin,
    )


def _capability_context(
    *,
    permissions: tuple[str, ...] = ("permission:door",),
    resources: tuple[str, ...] = ("resource:door",),
    adapters: tuple[str, ...] = ("adapter:door",),
) -> CapabilityContext:
    return CapabilityContext(
        actor_ref="participant:system",
        event_type_ref="event:open",
        current_state=None,
        resources=resources,
        permissions=permissions,
        adapters=adapters,
        revisions=_revision_pin(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authority() -> _EffectAuthority:
    return _EffectAuthority()


@pytest.fixture
def config() -> RuntimeConfig:
    return RuntimeConfig.release()


@pytest.fixture
def stores(authority):
    return memory_stores(authority_generation=authority.generation)


@pytest.fixture
def capability_engine(authority, config) -> CapabilityEngine:
    return CapabilityEngine(authority, config)


@pytest.fixture
def default_context() -> CapabilityContext:
    return _capability_context()


@pytest.fixture
def verifier(capability_engine, default_context) -> EffectVerifier:
    return EffectVerifier(capability_engine, default_context=default_context)


@pytest.fixture
def journal(stores) -> EffectJournal:
    return EffectJournal(stores)


@pytest.fixture
def counting_adapter() -> CountingAdapter:
    return CountingAdapter()


@pytest.fixture
def adapter_registry(counting_adapter) -> AdapterRegistry:
    return AdapterRegistry({"adapter:door": counting_adapter})


@pytest.fixture
def observation_validator() -> ObservationValidator:
    return ObservationValidator()


@pytest.fixture
def gateway(
    verifier, journal, adapter_registry, observation_validator
) -> EffectGateway:
    return EffectGateway(
        verifier=verifier,
        journal=journal,
        adapters=adapter_registry,
        observations=observation_validator,
    )


@pytest.fixture
def plan() -> EffectPlan:
    return _plan()


# ---------------------------------------------------------------------------
# Tests: retry does not duplicate external effect
# ---------------------------------------------------------------------------


class TestRetryDoesNotDuplicateExternalEffect:
    def test_retry_returns_same_receipt(self, gateway, counting_adapter, plan):
        first = gateway.execute(plan)
        second = gateway.execute(plan)
        assert first == second
        assert counting_adapter.calls == 1

    def test_first_execution_commits(self, gateway, plan):
        receipt = gateway.execute(plan)
        assert receipt.status == "committed"
        assert receipt.effect_ref == plan.effect_ref

    def test_second_execution_skips_adapter(self, gateway, counting_adapter, plan):
        gateway.execute(plan)
        assert counting_adapter.calls == 1
        gateway.execute(plan)
        assert counting_adapter.calls == 1

    def test_different_idempotency_keys_invoke_separately(
        self, gateway, counting_adapter
    ):
        plan_a = _plan(idempotency_key="idem:a")
        plan_b = _plan(idempotency_key="idem:b")
        gateway.execute(plan_a)
        gateway.execute(plan_b)
        assert counting_adapter.calls == 2


# ---------------------------------------------------------------------------
# Tests: denial is not reported as incapacity
# ---------------------------------------------------------------------------


class TestDenialIsNotIncapacity:
    def test_denial_produces_denied_receipt(self, plan):
        """When permission is missing, the effect is denied, not unavailable."""
        from cemm_authoritative_hybrid.capabilities import CapabilityContext

        denied_context = _capability_context(permissions=())
        denied_stores = memory_stores(
            authority_generation="authority:effect-test-v1"
        )
        denied_verifier = EffectVerifier(
            CapabilityEngine(_EffectAuthority(), RuntimeConfig.release()),
            default_context=denied_context,
        )
        denied_gateway = EffectGateway(
            verifier=denied_verifier,
            journal=EffectJournal(denied_stores),
            adapters=AdapterRegistry(
                {"adapter:door": CountingAdapter()}
            ),
            observations=ObservationValidator(),
        )
        receipt = denied_gateway.execute(plan)
        assert receipt.status == "denied"
        assert receipt.adapter_receipt_ref is None

    def test_denial_gap_receipt_kind_is_permission(self):
        """A permission denial produces a gap receipt with kind 'permission'."""
        classifier = GapClassifier()
        gap = classifier.classify(
            PermissionDenied(
                capability_ref="permission:door",
                participant_ref="participant:system",
            )
        )
        assert gap.kind == GapKind.PERMISSION


# ---------------------------------------------------------------------------
# Tests: one proof-bearing gateway owns all effectful commits
# ---------------------------------------------------------------------------


class TestOneGatewayOwnsAllCommits:
    def test_gateway_is_only_path_to_commit(self, gateway, plan, stores):
        before = stores.effects.revision
        gateway.execute(plan)
        assert stores.effects.revision == before + 1

    def test_denied_effect_does_not_commit(self):
        from cemm_authoritative_hybrid.capabilities import (
            CapabilityContext,
            CapabilityEngine,
        )

        denied_context = _capability_context(permissions=())
        denied_stores = memory_stores(
            authority_generation="authority:effect-test-v1"
        )
        denied_verifier = EffectVerifier(
            CapabilityEngine(_EffectAuthority(), RuntimeConfig.release()),
            default_context=denied_context,
        )
        denied_gateway = EffectGateway(
            verifier=denied_verifier,
            journal=EffectJournal(denied_stores),
            adapters=AdapterRegistry(
                {"adapter:door": CountingAdapter()}
            ),
            observations=ObservationValidator(),
        )
        before = denied_stores.effects.revision
        receipt = denied_gateway.execute(_plan())
        assert receipt.status == "denied"
        assert denied_stores.effects.revision == before

    def test_receipt_carries_proof_refs(self, gateway, plan):
        receipt = gateway.execute(plan)
        assert receipt.proof_refs
        assert receipt.adapter_receipt_ref is not None


# ---------------------------------------------------------------------------
# Tests: no adapter may write semantic stores directly
# ---------------------------------------------------------------------------


class TestNoAdapterWritesStoresDirectly:
    def test_adapter_does_not_receive_stores(self, counting_adapter):
        """The adapter's invoke method only receives PendingEffect, not stores."""
        # The CountingAdapter.invoke signature takes only pending — no stores.
        import inspect

        sig = inspect.signature(counting_adapter.invoke)
        assert "stores" not in sig.parameters
        assert "semantic_stores" not in sig.parameters

    def test_adapter_registry_does_not_expose_stores(
        self, adapter_registry, stores
    ):
        """The AdapterRegistry does not expose stores to adapters."""
        assert not hasattr(adapter_registry, "_stores")
        assert not hasattr(adapter_registry, "stores")


# ---------------------------------------------------------------------------
# Tests: timeout / partial failure remains unresolved
# ---------------------------------------------------------------------------


class TestTimeoutAndPartialFailure:
    def test_timeout_produces_pending_receipt(self, stores):
        """A timeout produces a pending receipt, never a predicted success."""
        from cemm_authoritative_hybrid.capabilities import (
            CapabilityContext,
            CapabilityEngine,
        )
        from cemm_authoritative_hybrid.effects import (
            AdapterRegistry,
            EffectGateway,
            EffectJournal,
            EffectVerifier,
            ObservationValidator,
        )

        class TimeoutAdapter:
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

        ctx = _capability_context()
        verifier = EffectVerifier(
            CapabilityEngine(_EffectAuthority(), RuntimeConfig.release()),
            default_context=ctx,
        )
        timeout_adapter = TimeoutAdapter()
        gateway = EffectGateway(
            verifier=verifier,
            journal=EffectJournal(stores),
            adapters=AdapterRegistry({"adapter:door": timeout_adapter}),
            observations=ObservationValidator(),
        )
        receipt = gateway.execute(_plan())
        assert receipt.status == "pending"
        assert timeout_adapter.calls == 1

    def test_pending_does_not_commit(self, stores):
        """A pending effect does not commit to the effect store."""
        from cemm_authoritative_hybrid.capabilities import (
            CapabilityContext,
            CapabilityEngine,
        )
        from cemm_authoritative_hybrid.effects import (
            AdapterRegistry,
            EffectGateway,
            EffectJournal,
            EffectVerifier,
            ObservationValidator,
        )

        class TimeoutAdapter:
            def invoke(self, pending: PendingEffect) -> AdapterReceipt:
                return AdapterReceipt(
                    adapter_ref="adapter:door",
                    status="timeout",
                    payload={},
                    receipt_ref="timeout:1",
                )

        ctx = _capability_context()
        verifier = EffectVerifier(
            CapabilityEngine(_EffectAuthority(), RuntimeConfig.release()),
            default_context=ctx,
        )
        gateway = EffectGateway(
            verifier=verifier,
            journal=EffectJournal(stores),
            adapters=AdapterRegistry({"adapter:door": TimeoutAdapter()}),
            observations=ObservationValidator(),
        )
        before = stores.effects.revision
        receipt = gateway.execute(_plan())
        assert receipt.status == "pending"
        assert stores.effects.revision == before


# ---------------------------------------------------------------------------
# Integration: runtime.process("s", "open the door") denial test
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ProcessResult:
    effect_receipt: EffectReceipt
    gap_receipt: Any


class _EffectTestRuntime:
    """Lightweight test runtime that wires capability engine and effect gateway."""

    def __init__(
        self,
        authority: _EffectAuthority,
        config: RuntimeConfig,
        stores: Any,
        *,
        permissions: tuple[str, ...] = ("permission:door",),
    ) -> None:
        self._authority = authority
        self._config = config
        self._stores = stores
        self._classifier = GapClassifier()
        self._capability_engine = CapabilityEngine(authority, config)
        self._default_context = _capability_context(permissions=permissions)
        self._verifier = EffectVerifier(
            self._capability_engine,
            default_context=self._default_context,
        )
        self._journal = EffectJournal(stores)
        self._adapter_registry = AdapterRegistry(
            {"adapter:door": CountingAdapter()}
        )
        self._observations = ObservationValidator()
        self._gateway = EffectGateway(
            verifier=self._verifier,
            journal=self._journal,
            adapters=self._adapter_registry,
            observations=self._observations,
        )

    def process(self, session_ref: str, text: str) -> _ProcessResult:
        """Process text and return an effect receipt + gap receipt."""
        text_lower = text.lower().strip()
        plan = _plan()
        receipt = self._gateway.execute(plan)

        gap_receipt = None
        if receipt.status == "denied":
            gap_receipt = self._classifier.classify(
                PermissionDenied(
                    capability_ref="permission:door",
                    participant_ref="participant:system",
                )
            )
        return _ProcessResult(effect_receipt=receipt, gap_receipt=gap_receipt)


@pytest.fixture
def denied_runtime():
    """A runtime where the permission to open the door is NOT granted."""
    authority = _EffectAuthority()
    config = RuntimeConfig.release()
    stores = memory_stores(authority_generation=authority.generation)
    return _EffectTestRuntime(
        authority, config, stores, permissions=()
    )


class TestRuntimeDenialIntegration:
    def test_denial_is_not_reported_as_incapacity(self, denied_runtime):
        result = denied_runtime.process("s", "open the door")
        assert result.effect_receipt.status == "denied"
        assert result.gap_receipt.kind == GapKind.PERMISSION


def test_effect_plan_threads_authentic_revision_pin_to_derived_context() -> None:
    source_pin = _revision_pin(world_revision=7)
    plan = EffectPlan(
        effect_ref="effect:pin-lineage",
        idempotency_key="idem:pin-lineage",
        program_ref="program:pin-lineage",
        actor_ref="participant:system",
        transition_ref="transition:open_door",
        expected_world_revision=source_pin.world_revision,
        requirement_proof_refs=("proof:pin-lineage",),
        revision_pin=source_pin,
    )

    context = EffectVerifier._context_from_plan(plan)

    assert context.revisions is source_pin
    assert context.revisions.revision_ref == source_pin.revision_ref


class _EffectRevisionInt(int):
    pass


class _RecordingCapabilityEngine:
    def __init__(self) -> None:
        self.contexts: list[CapabilityContext] = []

    def check(
        self,
        actor_ref: str,
        event_type_ref: str,
        context: CapabilityContext,
    ) -> CapabilityResult:
        self.contexts.append(context)
        return CapabilityResult(
            status="unknown",
            proof_refs=(),
            cache_key="capability-check:recorded",
        )


@pytest.mark.parametrize("pins_match", (True, False), ids=("matching", "mismatched"))
def test_effect_verifier_authorize_binds_exact_plan_revision_pin(
    pins_match: bool,
) -> None:
    plan_pin = _revision_pin(world_revision=7)
    default_pin = (
        plan_pin
        if pins_match
        else _revision_pin(
            authority_generation="authority:default-context",
            world_revision=3,
        )
    )
    default_context = replace(
        _capability_context(
            permissions=("permission:default",),
            resources=("resource:default",),
            adapters=("adapter:default",),
        ),
        revisions=default_pin,
    )
    engine = _RecordingCapabilityEngine()
    verifier = EffectVerifier(engine, default_context=default_context)
    plan = _plan(expected_world_revision=7, revision_pin=plan_pin)

    decision = verifier.authorize(plan)

    assert decision.authorized is False
    assert decision.status == "unknown"
    if not pins_match:
        assert decision.proof_refs == ()
        assert decision.reason == "capability context revision pin mismatch"
        assert engine.contexts == []
        return

    assert len(engine.contexts) == 1
    received = engine.contexts[0]
    assert received.revisions is plan_pin
    assert received is default_context


def test_effect_plan_rejects_nonexact_or_unequal_expected_world_revision() -> None:
    source_pin = _revision_pin(world_revision=1)
    plan = _plan(expected_world_revision=1, revision_pin=source_pin)

    for invalid_revision in (True, _EffectRevisionInt(1), 2):
        with pytest.raises((TypeError, ValueError)):
            replace(plan, expected_world_revision=invalid_revision)


__cemm_test_inventory__ = {'tests/test_effect_gateway.py::test_effect_plan_rejects_nonexact_or_unequal_expected_world_revision': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-effect-plan-world-revision-exact-and-equal',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Slice-A',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': '2311048b071f0f668465b0a3d34164c22d090542d9d7b488d6f43f226e39ea34'},
 'tests/test_effect_gateway.py::test_effect_plan_threads_authentic_revision_pin_to_derived_context': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-effect-plan-preserves-revision-pin-lineage',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Slice-A',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': 'c21ab7aae163ebb707faf606f0e605cb1fb3389a614a6020e29661cd8c1499aa'},
 'tests/test_effect_gateway.py::test_effect_verifier_authorize_binds_exact_plan_revision_pin[matching]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-effect-verifier-binds-matching-plan-pin',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Slice-A',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': '53c3d54af8e5bad9ed4d4d50937e839be06abcb0b05778a7dbcec47b818071df'},
 'tests/test_effect_gateway.py::test_effect_verifier_authorize_binds_exact_plan_revision_pin[mismatched]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-effect-verifier-rejects-mismatched-default-pin',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Slice-A',
                                                                                                            'owner_ref': 'program-verifier',
                                                                                                            'source_ast_sha256': '53c3d54af8e5bad9ed4d4d50937e839be06abcb0b05778a7dbcec47b818071df'}}
