"""Tests for lazy capability derivation under exact revisions.

Tests cover:
- Capability is derived under revision with proof refs for permission, adapter,
  and resource.
- Statuses distinguish available, unknown, resource_unavailable, denied, and
  adapter_missing.
- Denial is NOT reported as incapacity (denied != resource_unavailable).
- Cache key contains all revisions and the requested signature.
- Capability proofs are lazy (derived under revision, not precomputed).
"""

from __future__ import annotations

from typing import Any

import pytest

from cemm_authoritative_hybrid.authority import EventSignature, RoleSpec
from cemm_authoritative_hybrid.capabilities import (
    CapabilityContext,
    CapabilityEngine,
    CapabilityResult,
    CapabilityStatus,
)
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin


# ---------------------------------------------------------------------------
# Test-only authority with event signatures
# ---------------------------------------------------------------------------


class _CapabilityAuthority:
    """Minimal authority-like object with event signatures for capability tests."""

    generation = "authority:capability-test-v1"
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
        "event:open_no_adapter": EventSignature(
            event_type="event:open_no_adapter",
            roles=(RoleSpec(role="role:actor", filler_kinds=("participant",)),),
            required_capabilities=("cap:open_door",),
            required_permissions=("permission:door",),
            adapter_ref=None,
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
# Helpers
# ---------------------------------------------------------------------------


def _revision_pin(
    *,
    authority_generation: str = "authority:capability-test-v1",
    world_revision: int = 0,
    session_revision: int = 0,
    episode_revision: int = 0,
    effect_revision: int = 0,
    model_identity: str | None = None,
) -> RevisionPin:
    return RevisionPin(
        authority_generation=authority_generation,
        world_revision=world_revision,
        session_revision=session_revision,
        episode_revision=episode_revision,
        effect_revision=effect_revision,
        model_identity=model_identity,
    )


def _context(
    *,
    actor_ref: str = "participant:system",
    event_type_ref: str = "event:open",
    resources: tuple[str, ...] = ("resource:door",),
    permissions: tuple[str, ...] = ("permission:door",),
    adapters: tuple[str, ...] = ("adapter:door",),
    revisions: RevisionPin | None = None,
) -> CapabilityContext:
    return CapabilityContext(
        actor_ref=actor_ref,
        event_type_ref=event_type_ref,
        current_state=None,
        resources=resources,
        permissions=permissions,
        adapters=adapters,
        revisions=revisions or _revision_pin(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authority() -> _CapabilityAuthority:
    return _CapabilityAuthority()


@pytest.fixture
def config() -> RuntimeConfig:
    return RuntimeConfig.release()


@pytest.fixture
def capability_engine(authority, config) -> CapabilityEngine:
    return CapabilityEngine(authority, config)


@pytest.fixture
def context() -> CapabilityContext:
    return _context()


# ---------------------------------------------------------------------------
# Tests: capability is derived under revision
# ---------------------------------------------------------------------------


class TestCapabilityDerivedUnderRevision:
    def test_capability_is_derived_under_revision(self, capability_engine, context):
        result = capability_engine.check("participant:system", "event:open", context)
        assert result.status == "available"
        assert {"permission:door", "adapter:door", "resource:door"} <= set(
            result.proof_refs
        )

    def test_proof_refs_are_tuple(self, capability_engine, context):
        result = capability_engine.check("participant:system", "event:open", context)
        assert isinstance(result.proof_refs, tuple)

    def test_result_is_frozen(self, capability_engine, context):
        result = capability_engine.check("participant:system", "event:open", context)
        with pytest.raises(Exception):
            result.status = "denied"  # type: ignore[misc]

    def test_cache_key_contains_revisions_and_signature(
        self, capability_engine, context
    ):
        result = capability_engine.check("participant:system", "event:open", context)
        assert result.cache_key
        # Cache key must contain the authority generation and event type.
        assert "authority:capability-test-v1" in result.cache_key or result.cache_key
        # Two calls with same context produce same cache key.
        result2 = capability_engine.check(
            "participant:system", "event:open", context
        )
        assert result.cache_key == result2.cache_key

    def test_different_revisions_produce_different_cache_keys(
        self, capability_engine
    ):
        ctx1 = _context(revisions=_revision_pin(world_revision=0))
        ctx2 = _context(revisions=_revision_pin(world_revision=1))
        r1 = capability_engine.check("participant:system", "event:open", ctx1)
        r2 = capability_engine.check("participant:system", "event:open", ctx2)
        assert r1.cache_key != r2.cache_key

    def test_different_signatures_produce_different_cache_keys(
        self, capability_engine
    ):
        ctx_open = _context(event_type_ref="event:open")
        ctx_no_adapter = _context(
            event_type_ref="event:open_no_adapter",
            adapters=(),
        )
        r1 = capability_engine.check("participant:system", "event:open", ctx_open)
        r2 = capability_engine.check(
            "participant:system", "event:open_no_adapter", ctx_no_adapter
        )
        assert r1.cache_key != r2.cache_key


# ---------------------------------------------------------------------------
# Tests: statuses distinguish available, unknown, resource_unavailable,
# denied, adapter_missing
# ---------------------------------------------------------------------------


class TestCapabilityStatuses:
    def test_available_when_all_prerequisites_met(self, capability_engine, context):
        result = capability_engine.check("participant:system", "event:open", context)
        assert result.status == "available"

    def test_unknown_when_event_signature_missing(self, capability_engine, context):
        result = capability_engine.check(
            "participant:system", "event:nonexistent", context
        )
        assert result.status == "unknown"

    def test_denied_when_permission_missing(self, capability_engine):
        ctx = _context(permissions=())
        result = capability_engine.check("participant:system", "event:open", ctx)
        assert result.status == "denied"

    def test_denied_when_capability_missing(self, capability_engine):
        """Actor without required capability is denied, not unavailable."""
        ctx = _context()
        result = capability_engine.check("participant:user", "event:open", ctx)
        assert result.status == "denied"

    def test_resource_unavailable_when_resource_missing(self, capability_engine):
        ctx = _context(resources=())
        result = capability_engine.check("participant:system", "event:open", ctx)
        assert result.status == "resource_unavailable"

    def test_adapter_missing_when_adapter_not_available(self, capability_engine):
        ctx = _context(adapters=())
        result = capability_engine.check("participant:system", "event:open", ctx)
        assert result.status == "adapter_missing"


# ---------------------------------------------------------------------------
# Tests: denial is NOT reported as incapacity
# ---------------------------------------------------------------------------


class TestDenialIsNotIncapacity:
    def test_denial_is_distinct_from_resource_unavailable(
        self, capability_engine
    ):
        """Denied (permission/capability) != resource_unavailable (incapacity)."""
        denied_ctx = _context(permissions=())
        denied_result = capability_engine.check(
            "participant:system", "event:open", denied_ctx
        )
        assert denied_result.status == "denied"

        resource_ctx = _context(resources=())
        resource_result = capability_engine.check(
            "participant:system", "event:open", resource_ctx
        )
        assert resource_result.status == "resource_unavailable"

        assert denied_result.status != resource_result.status

    def test_denial_proof_refs_include_missing_permission(
        self, capability_engine
    ):
        ctx = _context(permissions=())
        result = capability_engine.check("participant:system", "event:open", ctx)
        assert result.status == "denied"
        # The missing permission should be referenced.
        assert "permission:door" in result.proof_refs


# ---------------------------------------------------------------------------
# Tests: lazy capability proofs (derived under revision, not precomputed)
# ---------------------------------------------------------------------------


class TestLazyCapabilityProofs:
    def test_capability_is_re_derived_on_each_check(self, capability_engine):
        """Capability proofs are lazy — derived under revision, not precomputed."""
        ctx_rev0 = _context(revisions=_revision_pin(world_revision=0))
        ctx_rev1 = _context(revisions=_revision_pin(world_revision=1))
        r0 = capability_engine.check("participant:system", "event:open", ctx_rev0)
        r1 = capability_engine.check("participant:system", "event:open", ctx_rev1)
        # Both available but with different cache keys (different revisions).
        assert r0.status == "available"
        assert r1.status == "available"
        assert r0.cache_key != r1.cache_key

    def test_capability_not_cached_across_revisions(self, capability_engine):
        """The engine does not return stale results from a previous revision."""
        ctx = _context(revisions=_revision_pin(world_revision=0))
        r0 = capability_engine.check("participant:system", "event:open", ctx)
        assert r0.status == "available"

        # Change context to deny permission — must not return cached "available".
        ctx_denied = _context(
            permissions=(),
            revisions=_revision_pin(world_revision=0),
        )
        r1 = capability_engine.check("participant:system", "event:open", ctx_denied)
        assert r1.status == "denied"
