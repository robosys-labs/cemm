"""Lazy capability derivation under exact revisions.

Capability status is derived from actor kind, event/transition signature, current
state, resources, permission, policy, and adapter availability under exact
revisions.  The cache key contains all revisions and the requested signature.
Statuses distinguish ``available``, ``unknown``, ``resource_unavailable``,
``denied``, and ``adapter_missing``.

Denial is NOT reported as incapacity: ``denied`` (permission/capability not
granted) is distinct from ``resource_unavailable`` (a resource is missing).
Capability proofs are lazy — derived under revision, not precomputed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from .authority import LinkedAuthority
from .canonical import stable_ref
from .config import RuntimeConfig
from .persistence import RevisionPin

__all__ = [
    "CapabilityStatus",
    "CapabilityResult",
    "CapabilityContext",
    "CapabilityEngine",
]


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


CapabilityStatus = Literal[
    "available",
    "unknown",
    "resource_unavailable",
    "denied",
    "adapter_missing",
]


@dataclass(frozen=True)
class CapabilityResult:
    """The result of a capability check.

    Attributes:
        status: one of ``available``, ``unknown``, ``resource_unavailable``,
            ``denied``, ``adapter_missing``.
        proof_refs: tuple of proof refs supporting the derivation.  For
            ``available``, this includes the permission, adapter, and resource
            refs that were checked.
        cache_key: a stable ref containing all revisions and the requested
            signature.
    """

    status: CapabilityStatus
    proof_refs: tuple[str, ...]
    cache_key: str


@dataclass(frozen=True)
class CapabilityContext:
    """The environmental context for a capability check.

    Attributes:
        actor_ref: the participant requesting the capability.
        event_type_ref: the event type being checked.
        current_state: the current temporal state of the target entity, or
            ``None`` if no state precondition is needed.
        resources: tuple of available resource refs.
        permissions: tuple of granted permission refs.
        adapters: tuple of available adapter refs.
        revisions: the exact revision pin under which the check is derived.
    """

    actor_ref: str
    event_type_ref: str
    current_state: Any
    resources: tuple[str, ...]
    permissions: tuple[str, ...]
    adapters: tuple[str, ...]
    revisions: RevisionPin


# ---------------------------------------------------------------------------
# Capability engine
# ---------------------------------------------------------------------------


class CapabilityEngine:
    """Derives capability status from prerequisites under exact revisions.

    The engine checks, in order:
    1. Event signature exists (else ``unknown``).
    2. Actor holds required capabilities (else ``denied``).
    3. Required permissions are granted (else ``denied``).
    4. Required resources are available (else ``resource_unavailable``).
    5. Required adapter is available (else ``adapter_missing``).
    6. All pass → ``available``.

    The cache key contains all revisions and the requested signature so that
    results are never stale across a revision change.
    """

    def __init__(self, authority: LinkedAuthority, config: RuntimeConfig) -> None:
        self._authority = authority
        self._config = config

    def check(
        self,
        actor_ref: str,
        event_type_ref: str,
        context: CapabilityContext,
    ) -> CapabilityResult:
        """Derive the capability status for ``actor_ref`` and ``event_type_ref``."""
        cache_key = self._cache_key(actor_ref, event_type_ref, context)

        # 1. Event signature must exist.
        sig = self._authority.by_event_signature(event_type_ref)
        if sig is None:
            return CapabilityResult(
                status="unknown",
                proof_refs=(),
                cache_key=cache_key,
            )

        proof_refs: list[str] = []

        # 2. Actor must hold required capabilities.
        actor_caps = set(self._authority.capabilities.get(actor_ref, []))
        for cap in sig.required_capabilities:
            if cap not in actor_caps:
                return CapabilityResult(
                    status="denied",
                    proof_refs=(cap,),
                    cache_key=cache_key,
                )

        # 3. Required permissions must be granted.
        granted_perms = set(context.permissions)
        for perm in sig.required_permissions:
            if perm not in granted_perms:
                return CapabilityResult(
                    status="denied",
                    proof_refs=(perm,),
                    cache_key=cache_key,
                )
            proof_refs.append(perm)

        # 4. Required resources must be available.
        available_resources = set(context.resources)
        required_resources = self._required_resources(sig)
        for res in required_resources:
            if res not in available_resources:
                return CapabilityResult(
                    status="resource_unavailable",
                    proof_refs=(res,),
                    cache_key=cache_key,
                )
            proof_refs.append(res)

        # 5. Required adapter must be available.
        if sig.adapter_ref is not None:
            available_adapters = set(context.adapters)
            if sig.adapter_ref not in available_adapters:
                return CapabilityResult(
                    status="adapter_missing",
                    proof_refs=(sig.adapter_ref,),
                    cache_key=cache_key,
                )
            proof_refs.append(sig.adapter_ref)

        # 6. All prerequisites met.
        return CapabilityResult(
            status="available",
            proof_refs=tuple(proof_refs),
            cache_key=cache_key,
        )

    # -- internal ----------------------------------------------------------

    @staticmethod
    def _required_resources(sig: Any) -> tuple[str, ...]:
        """Extract required resource refs from an event signature's effect schema."""
        resources: list[str] = []
        for entry in getattr(sig, "effect_schema", ()):
            if isinstance(entry, Mapping):
                kind = entry.get("kind")
                resource = entry.get("resource")
                if kind == "resource" and resource is not None:
                    resources.append(str(resource))
        return tuple(resources)

    @staticmethod
    def _cache_key(
        actor_ref: str,
        event_type_ref: str,
        context: CapabilityContext,
    ) -> str:
        """Build a cache key containing all revisions and the requested signature."""
        revs = context.revisions
        return stable_ref(
            "capability",
            {
                "actor": actor_ref,
                "event": event_type_ref,
                "authority_generation": revs.authority_generation,
                "world_revision": revs.world_revision,
                "session_revision": revs.session_revision,
                "episode_revision": revs.episode_revision,
                "effect_revision": revs.effect_revision,
                "model_identity": revs.model_identity,
            },
        )
