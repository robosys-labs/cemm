"""Typed gap receipts and classification.

This module owns the Gap Receipt ABI. ``GapClassifier`` maps typed exceptions
and results to exact :class:`GapReceipt` rows. It never examines surface text:
classification is by Python type only. Unknown exceptions become
``implementation`` gaps with ``recommended_owner=runtime`` and
``safe_response_action=activation_failure`` so that no failure reaches users as
generic clarification when a more exact status exists.

Every failed or unresolved cycle emits a typed ``GapReceipt``.

The 18 canonical gap kinds and their six repair owners form a closed matrix:

    evidence       -> data
    designation    -> data
    reference      -> training   (ambiguity with candidate)
                    -> authority  (absent identity/frame)
    authority      -> authority
    proposal       -> training
    verification   -> runtime
    inference      -> runtime
    state          -> data
    transition     -> authority  (missing transition)
                    -> runtime    (exhausted proof bound)
    learning       -> policy
    resource       -> data
    permission     -> policy
    adapter        -> adapter
    operation      -> adapter
    storage        -> runtime
    realization    -> training
    performance    -> runtime
    implementation -> runtime
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .canonical import stable_ref

__all__ = [
    "GapKind",
    "RepairOwner",
    "GapReceipt",
    "GapClassifier",
    "GapException",
    "MissingOwner",
    "VerificationFailure",
    "CoverageGap",
    "EffectDenied",
    "RealizationFailure",
    "BudgetExhausted",
    "ResourceUnavailable",
    "PermissionDenied",
    "SemanticConflict",
    "EvidenceGap",
    "ReferenceAmbiguity",
    "AbsentIdentity",
    "ProposalGap",
    "InferenceBound",
    "StateGap",
    "MissingTransition",
    "TransitionBoundExhausted",
    "LearningGap",
    "AdapterFailure",
    "StorageFailure",
]


# ---------------------------------------------------------------------------
# Closed enums
# ---------------------------------------------------------------------------


class GapKind(Enum):
    """Closed set of 18 gap kinds."""

    EVIDENCE = "evidence"
    DESIGNATION = "designation"
    REFERENCE = "reference"
    AUTHORITY = "authority"
    PROPOSAL = "proposal"
    VERIFICATION = "verification"
    INFERENCE = "inference"
    STATE = "state"
    TRANSITION = "transition"
    LEARNING = "learning"
    RESOURCE = "resource"
    PERMISSION = "permission"
    ADAPTER = "adapter"
    OPERATION = "operation"
    STORAGE = "storage"
    REALIZATION = "realization"
    PERFORMANCE = "performance"
    IMPLEMENTATION = "implementation"


class RepairOwner(Enum):
    """Closed set of 6 recommended repair owners."""

    DATA = "data"
    TRAINING = "training"
    AUTHORITY = "authority"
    RUNTIME = "runtime"
    POLICY = "policy"
    ADAPTER = "adapter"


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class GapException(Exception):
    """Base class for typed gap exceptions.

    Subclasses carry structured fields (not surface text) so that
    :class:`GapClassifier` can map by type without examining messages.
    """


@dataclass(frozen=True)
class MissingOwner(GapException):
    """A required owner was missing for a phase or operation."""

    owner_name: str

    def __str__(self) -> str:
        return f"MissingOwner({self.owner_name})"


@dataclass(frozen=True)
class VerificationFailure(GapException):
    """A candidate failed structural, reference, scope, capability or transition legality."""

    code: str
    cycle_ref: str

    def __str__(self) -> str:
        return f"VerificationFailure({self.code})"


@dataclass(frozen=True)
class CoverageGap(GapException):
    """A surface span produced no designation or affordance candidate."""

    span_ref: str
    reason: str

    def __str__(self) -> str:
        return f"CoverageGap({self.span_ref})"


@dataclass(frozen=True)
class EffectDenied(GapException):
    """An effect was denied because it lacked a verified decision or permission."""

    effect_ref: str
    reason: str

    def __str__(self) -> str:
        return f"EffectDenied({self.effect_ref})"


@dataclass(frozen=True)
class RealizationFailure(GapException):
    """A response surface could not be realized or verified."""

    response_ref: str
    reason: str

    def __str__(self) -> str:
        return f"RealizationFailure({self.response_ref})"


@dataclass(frozen=True)
class BudgetExhausted(GapException):
    """A configured budget was exhausted."""

    budget_name: str
    limit: int

    def __str__(self) -> str:
        return f"BudgetExhausted({self.budget_name})"


@dataclass(frozen=True)
class ResourceUnavailable(GapException):
    """A required resource (model, store, adapter) was unavailable."""

    resource_ref: str
    reason: str

    def __str__(self) -> str:
        return f"ResourceUnavailable({self.resource_ref})"


@dataclass(frozen=True)
class PermissionDenied(GapException):
    """A capability or permission was denied for a participant."""

    capability_ref: str
    participant_ref: str

    def __str__(self) -> str:
        return f"PermissionDenied({self.capability_ref})"


@dataclass(frozen=True)
class SemanticConflict(GapException):
    """Two or more candidates conflicted and could not be settled."""

    graph_ref: str
    reason: str

    def __str__(self) -> str:
        return f"SemanticConflict({self.graph_ref})"


# -- New typed exceptions for the expanded 18-kind matrix --------------------


@dataclass(frozen=True)
class EvidenceGap(GapException):
    """Evidence was missing or insufficient for a claim."""

    claim_ref: str
    reason: str

    def __str__(self) -> str:
        return f"EvidenceGap({self.claim_ref})"


@dataclass(frozen=True)
class ReferenceAmbiguity(GapException):
    """A reference was ambiguous with an existing candidate."""

    ref_ref: str
    candidate_refs: tuple[str, ...]

    def __str__(self) -> str:
        return f"ReferenceAmbiguity({self.ref_ref})"


@dataclass(frozen=True)
class AbsentIdentity(GapException):
    """An identity or frame was absent and could not be resolved."""

    identity_ref: str
    frame_ref: str

    def __str__(self) -> str:
        return f"AbsentIdentity({self.identity_ref})"


@dataclass(frozen=True)
class ProposalGap(GapException):
    """No valid proposal could be generated from orientation."""

    cycle_ref: str
    reason: str

    def __str__(self) -> str:
        return f"ProposalGap({self.cycle_ref})"


@dataclass(frozen=True)
class InferenceBound(GapException):
    """An inference bound was reached before a conclusion could be drawn."""

    query_ref: str
    bound_name: str

    def __str__(self) -> str:
        return f"InferenceBound({self.query_ref})"


@dataclass(frozen=True)
class StateGap(GapException):
    """A state dimension or value was missing."""

    entity_ref: str
    dimension_ref: str

    def __str__(self) -> str:
        return f"StateGap({self.entity_ref})"


@dataclass(frozen=True)
class MissingTransition(GapException):
    """A transition definition was missing for a requested state change."""

    from_state: str
    to_state: str

    def __str__(self) -> str:
        return f"MissingTransition({self.from_state}->{self.to_state})"


@dataclass(frozen=True)
class TransitionBoundExhausted(GapException):
    """A transition proof bound was exhausted."""

    transition_ref: str
    bound: int

    def __str__(self) -> str:
        return f"TransitionBoundExhausted({self.transition_ref})"


@dataclass(frozen=True)
class LearningGap(GapException):
    """A learning obligation could not be fulfilled."""

    obligation_ref: str
    reason: str

    def __str__(self) -> str:
        return f"LearningGap({self.obligation_ref})"


@dataclass(frozen=True)
class AdapterFailure(GapException):
    """An adapter failed to invoke or return a valid receipt."""

    adapter_ref: str
    reason: str

    def __str__(self) -> str:
        return f"AdapterFailure({self.adapter_ref})"


@dataclass(frozen=True)
class StorageFailure(GapException):
    """A storage operation failed."""

    store_ref: str
    reason: str

    def __str__(self) -> str:
        return f"StorageFailure({self.store_ref})"


# ---------------------------------------------------------------------------
# Gap receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GapReceipt:
    """A typed receipt for a failed or unresolved cycle.

    Every failed or unresolved cycle emits exactly one ``GapReceipt``. The
    receipt identifies the gap kind, status, source refs, blockers, missing
    contracts, rejected candidates, the recommended repair owner and the safe
    response action. No failure becomes generic clarification when a more
    exact status exists.
    """

    gap_ref: str
    kind: GapKind
    status: str
    source_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    missing_contract_refs: tuple[str, ...]
    rejected_candidate_refs: tuple[str, ...]
    recommended_owner: RepairOwner
    safe_response_action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "gap_ref": self.gap_ref,
            "kind": self.kind.value,
            "status": self.status,
            "source_refs": list(self.source_refs),
            "blockers": list(self.blockers),
            "missing_contract_refs": list(self.missing_contract_refs),
            "rejected_candidate_refs": list(self.rejected_candidate_refs),
            "recommended_owner": self.recommended_owner.value,
            "safe_response_action": self.safe_response_action,
        }


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def _gap_ref(exc: GapException, kind: GapKind) -> str:
    """Deterministic gap ref from the exception's structured fields."""
    payload: dict[str, Any] = {
        "type": type(exc).__name__,
        "kind": kind.value,
        "fields": _exc_fields(exc),
    }
    return stable_ref("gap", payload)


def _exc_fields(exc: GapException) -> dict[str, Any]:
    """Extract structured fields from a typed exception (not its message)."""
    if isinstance(exc, MissingOwner):
        return {"owner_name": exc.owner_name}
    if isinstance(exc, VerificationFailure):
        return {"code": exc.code, "cycle_ref": exc.cycle_ref}
    if isinstance(exc, CoverageGap):
        return {"span_ref": exc.span_ref, "reason": exc.reason}
    if isinstance(exc, EffectDenied):
        return {"effect_ref": exc.effect_ref, "reason": exc.reason}
    if isinstance(exc, RealizationFailure):
        return {"response_ref": exc.response_ref, "reason": exc.reason}
    if isinstance(exc, BudgetExhausted):
        return {"budget_name": exc.budget_name, "limit": exc.limit}
    if isinstance(exc, ResourceUnavailable):
        return {"resource_ref": exc.resource_ref, "reason": exc.reason}
    if isinstance(exc, PermissionDenied):
        return {"capability_ref": exc.capability_ref, "participant_ref": exc.participant_ref}
    if isinstance(exc, SemanticConflict):
        return {"graph_ref": exc.graph_ref, "reason": exc.reason}
    if isinstance(exc, EvidenceGap):
        return {"claim_ref": exc.claim_ref, "reason": exc.reason}
    if isinstance(exc, ReferenceAmbiguity):
        return {"ref_ref": exc.ref_ref, "candidate_refs": list(exc.candidate_refs)}
    if isinstance(exc, AbsentIdentity):
        return {"identity_ref": exc.identity_ref, "frame_ref": exc.frame_ref}
    if isinstance(exc, ProposalGap):
        return {"cycle_ref": exc.cycle_ref, "reason": exc.reason}
    if isinstance(exc, InferenceBound):
        return {"query_ref": exc.query_ref, "bound_name": exc.bound_name}
    if isinstance(exc, StateGap):
        return {"entity_ref": exc.entity_ref, "dimension_ref": exc.dimension_ref}
    if isinstance(exc, MissingTransition):
        return {"from_state": exc.from_state, "to_state": exc.to_state}
    if isinstance(exc, TransitionBoundExhausted):
        return {"transition_ref": exc.transition_ref, "bound": exc.bound}
    if isinstance(exc, LearningGap):
        return {"obligation_ref": exc.obligation_ref, "reason": exc.reason}
    if isinstance(exc, AdapterFailure):
        return {"adapter_ref": exc.adapter_ref, "reason": exc.reason}
    if isinstance(exc, StorageFailure):
        return {"store_ref": exc.store_ref, "reason": exc.reason}
    # Unknown typed exception — fall back to type name only.
    return {"type": type(exc).__name__}


class GapClassifier:
    """Maps typed exceptions and results to :class:`GapReceipt` rows.

    Classification is by Python type only; the classifier never examines
    surface text. Unknown exceptions become ``implementation`` gaps with
    ``recommended_owner=runtime`` and ``safe_response_action=activation_failure``
    so that no failure reaches users as generic clarification.

    Branch cases:
    - Reference ambiguity with an existing candidate routes to **training**;
      an absent identity/frame routes to **authority**.
    - Missing transition routes to **authority**; an exhausted proof bound
      routes to **runtime**.
    - Resource absence, permission denial, and adapter failure remain distinct.
    """

    def classify(self, exception_or_result: Any) -> GapReceipt:
        exc = exception_or_result
        if isinstance(exc, BaseException):
            return self._classify_exception(exc)
        # Non-exception results are treated as implementation gaps by default.
        return self._make_gap(
            GapKind.IMPLEMENTATION,
            status="activation_failure",
            source_refs=(),
            blockers=(f"unexpected result: {type(exc).__name__}",),
            recommended_owner=RepairOwner.RUNTIME,
            safe_response_action="activation_failure",
            ref_payload={"type": type(exc).__name__},
        )

    def _classify_exception(self, exc: BaseException) -> GapReceipt:
        if isinstance(exc, MissingOwner):
            return self._make_gap(
                GapKind.IMPLEMENTATION,
                status="activation_failure",
                source_refs=(),
                blockers=(f"missing owner: {exc.owner_name}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="activation_failure",
                ref_payload={"type": "MissingOwner", "owner_name": exc.owner_name},
            )
        if isinstance(exc, VerificationFailure):
            return self._make_gap(
                GapKind.VERIFICATION,
                status="verification_failed",
                source_refs=(exc.cycle_ref,),
                blockers=(f"rejection: {exc.code}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="reject_candidate",
                ref_payload={"type": "VerificationFailure", "code": exc.code, "cycle_ref": exc.cycle_ref},
            )
        if isinstance(exc, CoverageGap):
            return self._make_gap(
                GapKind.DESIGNATION,
                status="coverage_gap",
                source_refs=(exc.span_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.DATA,
                safe_response_action="request_designation",
                ref_payload={"type": "CoverageGap", "span_ref": exc.span_ref},
            )
        if isinstance(exc, EffectDenied):
            return self._make_gap(
                GapKind.OPERATION,
                status="effect_denied",
                source_refs=(exc.effect_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.ADAPTER,
                safe_response_action="hold_effect",
                ref_payload={"type": "EffectDenied", "effect_ref": exc.effect_ref},
            )
        if isinstance(exc, RealizationFailure):
            return self._make_gap(
                GapKind.REALIZATION,
                status="realization_failed",
                source_refs=(exc.response_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.TRAINING,
                safe_response_action="hold_response",
                ref_payload={"type": "RealizationFailure", "response_ref": exc.response_ref},
            )
        if isinstance(exc, BudgetExhausted):
            return self._make_gap(
                GapKind.PERFORMANCE,
                status="budget_exhausted",
                source_refs=(),
                blockers=(f"budget exhausted: {exc.budget_name}={exc.limit}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="bound_cycle",
                ref_payload={"type": "BudgetExhausted", "budget_name": exc.budget_name, "limit": exc.limit},
            )
        if isinstance(exc, ResourceUnavailable):
            return self._make_gap(
                GapKind.RESOURCE,
                status="resource_unavailable",
                source_refs=(exc.resource_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.DATA,
                safe_response_action="retry_or_degrade",
                ref_payload={"type": "ResourceUnavailable", "resource_ref": exc.resource_ref},
            )
        if isinstance(exc, PermissionDenied):
            return self._make_gap(
                GapKind.PERMISSION,
                status="permission_denied",
                source_refs=(exc.capability_ref,),
                blockers=(f"denied for {exc.participant_ref}",),
                recommended_owner=RepairOwner.POLICY,
                safe_response_action="deny_operation",
                ref_payload={"type": "PermissionDenied", "capability_ref": exc.capability_ref},
            )
        if isinstance(exc, SemanticConflict):
            return self._make_gap(
                GapKind.AUTHORITY,
                status="semantic_conflict",
                source_refs=(exc.graph_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.AUTHORITY,
                safe_response_action="request_authority_review",
                ref_payload={"type": "SemanticConflict", "graph_ref": exc.graph_ref},
            )
        # -- New gap kinds --------------------------------------------------
        if isinstance(exc, EvidenceGap):
            return self._make_gap(
                GapKind.EVIDENCE,
                status="evidence_missing",
                source_refs=(exc.claim_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.DATA,
                safe_response_action="request_evidence",
                ref_payload={"type": "EvidenceGap", "claim_ref": exc.claim_ref},
            )
        if isinstance(exc, ReferenceAmbiguity):
            return self._make_gap(
                GapKind.REFERENCE,
                status="reference_ambiguous",
                source_refs=(exc.ref_ref,),
                blockers=(f"candidates: {', '.join(exc.candidate_refs)}",),
                recommended_owner=RepairOwner.TRAINING,
                safe_response_action="request_reference_resolution",
                ref_payload={"type": "ReferenceAmbiguity", "ref_ref": exc.ref_ref},
            )
        if isinstance(exc, AbsentIdentity):
            return self._make_gap(
                GapKind.REFERENCE,
                status="identity_absent",
                source_refs=(exc.identity_ref,),
                blockers=(f"frame absent: {exc.frame_ref}",),
                recommended_owner=RepairOwner.AUTHORITY,
                safe_response_action="request_identity",
                ref_payload={"type": "AbsentIdentity", "identity_ref": exc.identity_ref},
            )
        if isinstance(exc, ProposalGap):
            return self._make_gap(
                GapKind.PROPOSAL,
                status="proposal_gap",
                source_refs=(exc.cycle_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.TRAINING,
                safe_response_action="request_proposal_review",
                ref_payload={"type": "ProposalGap", "cycle_ref": exc.cycle_ref},
            )
        if isinstance(exc, InferenceBound):
            return self._make_gap(
                GapKind.INFERENCE,
                status="inference_bound",
                source_refs=(exc.query_ref,),
                blockers=(f"bound: {exc.bound_name}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="bound_inference",
                ref_payload={"type": "InferenceBound", "query_ref": exc.query_ref},
            )
        if isinstance(exc, StateGap):
            return self._make_gap(
                GapKind.STATE,
                status="state_gap",
                source_refs=(exc.entity_ref,),
                blockers=(f"dimension missing: {exc.dimension_ref}",),
                recommended_owner=RepairOwner.DATA,
                safe_response_action="request_state_evidence",
                ref_payload={"type": "StateGap", "entity_ref": exc.entity_ref},
            )
        if isinstance(exc, MissingTransition):
            return self._make_gap(
                GapKind.TRANSITION,
                status="transition_missing",
                source_refs=(exc.from_state,),
                blockers=(f"no transition to {exc.to_state}",),
                recommended_owner=RepairOwner.AUTHORITY,
                safe_response_action="request_transition_definition",
                ref_payload={"type": "MissingTransition", "from_state": exc.from_state, "to_state": exc.to_state},
            )
        if isinstance(exc, TransitionBoundExhausted):
            return self._make_gap(
                GapKind.TRANSITION,
                status="transition_bound_exhausted",
                source_refs=(exc.transition_ref,),
                blockers=(f"proof bound exhausted: {exc.bound}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="bound_transition",
                ref_payload={"type": "TransitionBoundExhausted", "transition_ref": exc.transition_ref},
            )
        if isinstance(exc, LearningGap):
            return self._make_gap(
                GapKind.LEARNING,
                status="learning_gap",
                source_refs=(exc.obligation_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.POLICY,
                safe_response_action="request_learning_review",
                ref_payload={"type": "LearningGap", "obligation_ref": exc.obligation_ref},
            )
        if isinstance(exc, AdapterFailure):
            return self._make_gap(
                GapKind.ADAPTER,
                status="adapter_failure",
                source_refs=(exc.adapter_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.ADAPTER,
                safe_response_action="retry_adapter",
                ref_payload={"type": "AdapterFailure", "adapter_ref": exc.adapter_ref},
            )
        if isinstance(exc, StorageFailure):
            return self._make_gap(
                GapKind.STORAGE,
                status="storage_failure",
                source_refs=(exc.store_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="retry_storage",
                ref_payload={"type": "StorageFailure", "store_ref": exc.store_ref},
            )
        # Unknown exception — implementation gap, never generic clarification.
        return self._make_gap(
            GapKind.IMPLEMENTATION,
            status="activation_failure",
            source_refs=(),
            blockers=(f"unhandled exception: {type(exc).__name__}",),
            recommended_owner=RepairOwner.RUNTIME,
            safe_response_action="activation_failure",
            ref_payload={"type": type(exc).__name__},
        )

    @staticmethod
    def _make_gap(
        kind: GapKind,
        *,
        status: str,
        source_refs: tuple[str, ...],
        blockers: tuple[str, ...],
        recommended_owner: RepairOwner,
        safe_response_action: str,
        ref_payload: Mapping[str, Any],
    ) -> GapReceipt:
        gap_ref = stable_ref("gap", {"kind": kind.value, **dict(ref_payload)})
        return GapReceipt(
            gap_ref=gap_ref,
            kind=kind,
            status=status,
            source_refs=source_refs,
            blockers=blockers,
            missing_contract_refs=(),
            rejected_candidate_refs=(),
            recommended_owner=recommended_owner,
            safe_response_action=safe_response_action,
        )
