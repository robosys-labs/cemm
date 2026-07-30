"""One proof-bearing gateway for all semantic effects.

The :class:`EffectGateway` is the only owner of world mutation and external
operation invocation.  It accepts verified decisions and returns idempotent
receipts.  No adapter may write semantic stores directly.

Flow::

    decision = verifier.authorize(plan)
    pending  = journal.begin_once(plan, decision)
    if pending.completed_receipt is not None:
        return pending.completed_receipt
    adapter_receipt = adapters.invoke(pending)
    observation     = observations.validate(adapter_receipt)
    return journal.finish_and_commit(pending, observation)

Timeout/partial failure remains unresolved and never admits predicted success.
Restart reads the journal before retry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .capabilities import CapabilityContext, CapabilityEngine, CapabilityResult
from .persistence import CommitReceipt, SemanticStores

__all__ = [
    "EffectPlan",
    "EffectReceipt",
    "AuthorizationDecision",
    "PendingEffect",
    "AdapterReceipt",
    "AdapterObservation",
    "EffectVerifier",
    "EffectJournal",
    "AdapterRegistry",
    "ObservationValidator",
    "EffectGateway",
    "Adapter",
]


# ---------------------------------------------------------------------------
# Effect plan and receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectPlan:
    """A plan for one effectful operation.

    Attributes:
        effect_ref: unique ref for this effect.
        idempotency_key: key used for idempotent journal lookup.
        program_ref: the verified program that produced this plan.
        actor_ref: the participant requesting the effect.
        transition_ref: the transition to apply (if any).
        expected_world_revision: the world revision expected at commit time.
        requirement_proof_refs: proof refs from capability/verification.
    """

    effect_ref: str
    idempotency_key: str
    program_ref: str
    actor_ref: str
    transition_ref: str
    expected_world_revision: int
    requirement_proof_refs: tuple[str, ...]


@dataclass(frozen=True)
class EffectReceipt:
    """The receipt for one effect execution.

    Attributes:
        effect_ref: the effect ref from the plan.
        status: one of ``committed``, ``denied``, ``failed``, ``pending``.
        world_revision: the world revision at the time of the receipt.
        proof_refs: proof refs supporting the effect.
        adapter_receipt_ref: the adapter receipt ref, or ``None`` if no adapter
            was invoked (e.g. denied).
    """

    effect_ref: str
    status: Literal["committed", "denied", "failed", "pending"]
    world_revision: int
    proof_refs: tuple[str, ...]
    adapter_receipt_ref: str | None


# ---------------------------------------------------------------------------
# Authorization decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorizationDecision:
    """The result of authorizing an effect plan.

    Attributes:
        authorized: whether the plan is authorized to proceed.
        status: one of ``authorized``, ``denied``, ``resource_unavailable``,
            ``adapter_missing``, ``unknown``.
        proof_refs: proof refs supporting the decision.
        reason: a short reason string (not user-visible).
    """

    authorized: bool
    status: Literal[
        "authorized",
        "denied",
        "resource_unavailable",
        "adapter_missing",
        "unknown",
    ]
    proof_refs: tuple[str, ...]
    reason: str


# ---------------------------------------------------------------------------
# Pending effect
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PendingEffect:
    """A pending effect awaiting adapter invocation and commit.

    Attributes:
        plan: the original :class:`EffectPlan`.
        decision: the :class:`AuthorizationDecision` from the verifier.
        completed_receipt: if non-``None``, the effect is already complete
            (either committed or denied) and the gateway returns this receipt
            immediately without invoking the adapter.
    """

    plan: EffectPlan
    decision: AuthorizationDecision
    completed_receipt: EffectReceipt | None = None


# ---------------------------------------------------------------------------
# Adapter receipt and observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterReceipt:
    """The receipt returned by an external adapter.

    Attributes:
        adapter_ref: the adapter that produced this receipt.
        status: one of ``succeeded``, ``failed``, ``timeout``.
        payload: the adapter's response payload.
        receipt_ref: a stable ref for this receipt.
    """

    adapter_ref: str
    status: Literal["succeeded", "failed", "timeout"]
    payload: Mapping[str, Any]
    receipt_ref: str


@dataclass(frozen=True)
class AdapterObservation:
    """A validated observation derived from an adapter receipt.

    Attributes:
        valid: whether the adapter receipt represents a valid observation.
        adapter_receipt: the original adapter receipt.
        proof_refs: proof refs supporting the validation.
    """

    valid: bool
    adapter_receipt: AdapterReceipt
    proof_refs: tuple[str, ...]


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Adapter(Protocol):
    """Protocol for external adapters.

    No adapter may write semantic stores directly.  The adapter receives only
    a :class:`PendingEffect` and returns an :class:`AdapterReceipt`.
    """

    def invoke(self, pending: PendingEffect) -> AdapterReceipt: ...


# ---------------------------------------------------------------------------
# Effect verifier
# ---------------------------------------------------------------------------


class EffectVerifier:
    """Checks capability, permissions, and preconditions for an effect plan.

    The verifier uses a :class:`CapabilityEngine` to derive the capability
    status and produces an :class:`AuthorizationDecision`.  If no default
    context is provided, the verifier builds one from the plan's fields.
    """

    def __init__(
        self,
        capability_engine: CapabilityEngine,
        *,
        default_context: CapabilityContext | None = None,
    ) -> None:
        self._capability_engine = capability_engine
        self._default_context = default_context

    def authorize(self, plan: EffectPlan) -> AuthorizationDecision:
        """Authorize an effect plan.

        Returns an :class:`AuthorizationDecision` with ``authorized=True`` if
        the capability is available, or ``authorized=False`` with the
        appropriate status otherwise.
        """
        context = self._default_context
        if context is None:
            context = self._context_from_plan(plan)

        # Derive the event type from the transition ref or program ref.
        event_type_ref = context.event_type_ref
        result: CapabilityResult = self._capability_engine.check(
            plan.actor_ref, event_type_ref, context
        )

        if result.status == "available":
            return AuthorizationDecision(
                authorized=True,
                status="authorized",
                proof_refs=result.proof_refs + plan.requirement_proof_refs,
                reason="all prerequisites met",
            )

        status_map: dict[str, Literal[
            "denied",
            "resource_unavailable",
            "adapter_missing",
            "unknown",
        ]] = {
            "denied": "denied",
            "resource_unavailable": "resource_unavailable",
            "adapter_missing": "adapter_missing",
            "unknown": "unknown",
        }
        mapped = status_map.get(result.status, "unknown")
        return AuthorizationDecision(
            authorized=False,
            status=mapped,
            proof_refs=result.proof_refs,
            reason=f"capability status: {result.status}",
        )

    @staticmethod
    def _context_from_plan(plan: EffectPlan) -> CapabilityContext:
        """Build a minimal capability context from a plan (no prerequisites)."""
        from .persistence import RevisionPin

        return CapabilityContext(
            actor_ref=plan.actor_ref,
            event_type_ref="",
            current_state=None,
            resources=(),
            permissions=(),
            adapters=(),
            revisions=RevisionPin(
                authority_generation="",
                world_revision=plan.expected_world_revision,
                session_revision=0,
                episode_revision=0,
                effect_revision=0,
                model_identity=None,
            ),
        )


# ---------------------------------------------------------------------------
# Effect journal
# ---------------------------------------------------------------------------


class EffectJournal:
    """Idempotent journal for effect execution.

    ``begin_once`` checks whether an effect with the same idempotency key is
    already completed.  If so, it returns a :class:`PendingEffect` with the
    completed receipt set.  ``finish_and_commit`` commits the effect to the
    effect store and returns the final receipt.

    On restart, a new journal constructed over the same store finds completed
    effects via :meth:`lookup`.
    """

    def __init__(self, stores: SemanticStores) -> None:
        self._stores = stores

    def begin_once(
        self, plan: EffectPlan, decision: AuthorizationDecision
    ) -> PendingEffect:
        """Begin an effect, returning a pending or already-completed result.

        If the effect is already completed (found in the store), the returned
        :class:`PendingEffect` has ``completed_receipt`` set.  If the decision
        is not authorized, a denied receipt is returned as completed.
        """
        # Check for an already-completed effect.
        existing = self.lookup(plan.idempotency_key)
        if existing is not None:
            return PendingEffect(
                plan=plan,
                decision=decision,
                completed_receipt=existing,
            )

        # If not authorized, return a denied receipt immediately.
        if not decision.authorized:
            denied_receipt = EffectReceipt(
                effect_ref=plan.effect_ref,
                status="denied",
                world_revision=plan.expected_world_revision,
                proof_refs=decision.proof_refs,
                adapter_receipt_ref=None,
            )
            return PendingEffect(
                plan=plan,
                decision=decision,
                completed_receipt=denied_receipt,
            )

        return PendingEffect(
            plan=plan,
            decision=decision,
            completed_receipt=None,
        )

    def finish_and_commit(
        self, pending: PendingEffect, observation: AdapterObservation
    ) -> EffectReceipt:
        """Commit a completed effect to the store and return the receipt.

        Timeout/partial failure remains unresolved (status ``pending``) and
        never commits to the effect store.
        """
        adapter_receipt = observation.adapter_receipt

        # Timeout or partial failure: remain pending, do not commit.
        if adapter_receipt.status == "timeout" or not observation.valid:
            return EffectReceipt(
                effect_ref=pending.plan.effect_ref,
                status="pending",
                world_revision=self._stores.world.revision,
                proof_refs=pending.decision.proof_refs,
                adapter_receipt_ref=adapter_receipt.receipt_ref,
            )

        if adapter_receipt.status == "failed":
            return EffectReceipt(
                effect_ref=pending.plan.effect_ref,
                status="failed",
                world_revision=self._stores.world.revision,
                proof_refs=pending.decision.proof_refs,
                adapter_receipt_ref=adapter_receipt.receipt_ref,
            )

        # Succeeded: commit to the effect store.
        proof_refs = (
            pending.decision.proof_refs
            + observation.proof_refs
            + (adapter_receipt.receipt_ref,)
        )
        receipt = EffectReceipt(
            effect_ref=pending.plan.effect_ref,
            status="committed",
            world_revision=self._stores.world.revision,
            proof_refs=proof_refs,
            adapter_receipt_ref=adapter_receipt.receipt_ref,
        )
        payload = {
            "effect_ref": receipt.effect_ref,
            "status": receipt.status,
            "world_revision": receipt.world_revision,
            "proof_refs": list(receipt.proof_refs),
            "adapter_receipt_ref": receipt.adapter_receipt_ref,
            "idempotency_key": pending.plan.idempotency_key,
            "program_ref": pending.plan.program_ref,
            "actor_ref": pending.plan.actor_ref,
            "transition_ref": pending.plan.transition_ref,
        }
        self._stores.effects.commit(
            {
                "effect_key": pending.plan.idempotency_key,
                "payload": payload,
            }
        )

        return receipt

    def lookup(self, idempotency_key: str) -> EffectReceipt | None:
        """Look up a completed effect by idempotency key.

        Returns ``None`` if no completed effect exists for the key.  On
        restart, a new journal constructed over the same store finds
        completed effects via this method.
        """
        payload = self._stores.effects.get(idempotency_key)
        if payload is None:
            return None
        return EffectReceipt(
            effect_ref=payload.get("effect_ref", ""),
            status=payload.get("status", "committed"),  # type: ignore[arg-type]
            world_revision=payload.get("world_revision", 0),
            proof_refs=tuple(payload.get("proof_refs", ())),
            adapter_receipt_ref=payload.get("adapter_receipt_ref"),
        )


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------


class AdapterRegistry:
    """Registry of external adapters keyed by adapter ref.

    No adapter may write semantic stores directly.  The registry does not
    expose stores to adapters.
    """

    def __init__(self, adapters: Mapping[str, Adapter]) -> None:
        self._adapters = dict(adapters)

    def invoke(self, pending: PendingEffect) -> AdapterReceipt:
        """Invoke the adapter for the pending effect's transition.

        Looks up the adapter by the decision's proof refs or the plan's
        transition ref.  If no adapter is found, returns a failed receipt.
        """
        # Determine which adapter to use from the capability proof refs.
        adapter_ref = self._find_adapter_ref(pending)
        if adapter_ref is None or adapter_ref not in self._adapters:
            return AdapterReceipt(
                adapter_ref=adapter_ref or "adapter:unknown",
                status="failed",
                payload={"reason": "adapter not found"},
                receipt_ref=stable_ref(
                    "adapter_receipt",
                    {"key": pending.plan.idempotency_key, "reason": "not_found"},
                ),
            )

        adapter = self._adapters[adapter_ref]
        return adapter.invoke(pending)

    @staticmethod
    def _find_adapter_ref(pending: PendingEffect) -> str | None:
        """Find the adapter ref from the decision's proof refs."""
        for ref in pending.decision.proof_refs:
            if ref.startswith("adapter:"):
                return ref
        return None


# ---------------------------------------------------------------------------
# Observation validator
# ---------------------------------------------------------------------------


class ObservationValidator:
    """Validates adapter receipts into observations.

    A succeeded adapter receipt is valid.  A timeout or failed receipt is
    not valid (but is still returned as an observation for the journal to
    handle).
    """

    def validate(self, adapter_receipt: AdapterReceipt) -> AdapterObservation:
        """Validate an adapter receipt into an observation."""
        if adapter_receipt.status == "succeeded":
            return AdapterObservation(
                valid=True,
                adapter_receipt=adapter_receipt,
                proof_refs=(adapter_receipt.receipt_ref,),
            )
        return AdapterObservation(
            valid=False,
            adapter_receipt=adapter_receipt,
            proof_refs=(adapter_receipt.receipt_ref,),
        )


# ---------------------------------------------------------------------------
# Effect gateway
# ---------------------------------------------------------------------------


class EffectGateway:
    """The one proof-bearing gateway that owns all effectful commits.

    The gateway routes every effect through a single path:
    authorize → begin → invoke → validate → commit.  No adapter may write
    semantic stores directly.  Timeout/partial failure remains unresolved
    and never admits predicted success.
    """

    def __init__(
        self,
        verifier: EffectVerifier,
        journal: EffectJournal,
        adapters: AdapterRegistry,
        observations: ObservationValidator,
    ) -> None:
        self._verifier = verifier
        self._journal = journal
        self._adapters = adapters
        self._observations = observations

    def execute(self, plan: EffectPlan) -> EffectReceipt:
        """Execute an effect plan through the gateway.

        Steps:
        1. ``decision = self.verifier.authorize(plan)``
        2. ``pending = self.journal.begin_once(plan, decision)``
        3. If ``pending.completed_receipt`` is not ``None``, return it.
        4. ``adapter_receipt = self.adapters.invoke(pending)``
        5. ``observation = self.observations.validate(adapter_receipt)``
        6. ``return self.journal.finish_and_commit(pending, observation)``
        """
        decision = self._verifier.authorize(plan)
        pending = self._journal.begin_once(plan, decision)
        if pending.completed_receipt is not None:
            return pending.completed_receipt
        adapter_receipt = self._adapters.invoke(pending)
        observation = self._observations.validate(adapter_receipt)
        return self._journal.finish_and_commit(pending, observation)
