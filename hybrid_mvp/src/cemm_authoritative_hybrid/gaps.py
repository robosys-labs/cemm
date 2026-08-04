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

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .canonical import stable_ref

__all__ = [
    "GapKind",
    "RepairOwner",
    "GapReceipt",
    "GapClassifier",
    "GapException",
    "LaterOwnerNotAdmitted",
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


GAP_RECEIPT_ABI_VERSION = 1
_MAX_TEXT_CHARS = 256
_MAX_RECEIPT_ROWS = 64


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


@dataclass
class LaterOwnerNotAdmitted(GapException):
    """A verified meaning reached a later semantic owner not admitted in this release."""

    verified_meaning_ref: str
    contract_ref: str

    def __post_init__(self) -> None:
        _exact_text(self.verified_meaning_ref, "verified_meaning_ref")
        _exact_text(self.contract_ref, "contract_ref")

    def __str__(self) -> str:
        return "LaterOwnerNotAdmitted"

@dataclass
class MissingOwner(GapException):
    """A required owner was missing for a phase or operation."""

    owner_name: str

    def __str__(self) -> str:
        return f"MissingOwner({self.owner_name})"


@dataclass
class VerificationFailure(GapException):
    """A candidate failed structural, reference, scope, capability or transition legality."""

    code: str
    cycle_ref: str

    def __str__(self) -> str:
        return f"VerificationFailure({self.code})"


@dataclass
class CoverageGap(GapException):
    """A surface span produced no designation or affordance candidate."""

    span_ref: str
    reason: str

    def __str__(self) -> str:
        return f"CoverageGap({self.span_ref})"


@dataclass
class EffectDenied(GapException):
    """An effect was denied because it lacked a verified decision or permission."""

    effect_ref: str
    reason: str

    def __str__(self) -> str:
        return f"EffectDenied({self.effect_ref})"


@dataclass
class RealizationFailure(GapException):
    """A response surface could not be realized or verified."""

    response_ref: str
    reason: str

    def __str__(self) -> str:
        return f"RealizationFailure({self.response_ref})"


@dataclass
class BudgetExhausted(GapException):
    """A configured budget was exhausted."""

    budget_name: str
    limit: int

    def __str__(self) -> str:
        return f"BudgetExhausted({self.budget_name})"


@dataclass
class ResourceUnavailable(GapException):
    """A required resource (model, store, adapter) was unavailable."""

    resource_ref: str
    reason: str

    def __str__(self) -> str:
        return f"ResourceUnavailable({self.resource_ref})"


@dataclass
class PermissionDenied(GapException):
    """A capability or permission was denied for a participant."""

    capability_ref: str
    participant_ref: str

    def __str__(self) -> str:
        return f"PermissionDenied({self.capability_ref})"


@dataclass
class SemanticConflict(GapException):
    """Two or more candidates conflicted and could not be settled."""

    graph_ref: str
    reason: str

    def __str__(self) -> str:
        return f"SemanticConflict({self.graph_ref})"


# -- New typed exceptions for the expanded 18-kind matrix --------------------


@dataclass
class EvidenceGap(GapException):
    """Evidence was missing or insufficient for a claim."""

    claim_ref: str
    reason: str

    def __str__(self) -> str:
        return f"EvidenceGap({self.claim_ref})"


@dataclass
class ReferenceAmbiguity(GapException):
    """A reference was ambiguous with an existing candidate."""

    ref_ref: str
    candidate_refs: tuple[str, ...]

    def __str__(self) -> str:
        return f"ReferenceAmbiguity({self.ref_ref})"


@dataclass
class AbsentIdentity(GapException):
    """An identity or frame was absent and could not be resolved."""

    identity_ref: str
    frame_ref: str

    def __str__(self) -> str:
        return f"AbsentIdentity({self.identity_ref})"


@dataclass
class ProposalGap(GapException):
    """No valid proposal could be generated from orientation."""

    cycle_ref: str
    reason: str

    def __str__(self) -> str:
        return f"ProposalGap({self.cycle_ref})"


@dataclass
class InferenceBound(GapException):
    """An inference bound was reached before a conclusion could be drawn."""

    query_ref: str
    bound_name: str

    def __str__(self) -> str:
        return f"InferenceBound({self.query_ref})"


@dataclass
class StateGap(GapException):
    """A state dimension or value was missing."""

    entity_ref: str
    dimension_ref: str

    def __str__(self) -> str:
        return f"StateGap({self.entity_ref})"


@dataclass
class MissingTransition(GapException):
    """A transition definition was missing for a requested state change."""

    from_state: str
    to_state: str

    def __str__(self) -> str:
        return f"MissingTransition({self.from_state}->{self.to_state})"


@dataclass
class TransitionBoundExhausted(GapException):
    """A transition proof bound was exhausted."""

    transition_ref: str
    bound: int

    def __str__(self) -> str:
        return f"TransitionBoundExhausted({self.transition_ref})"


@dataclass
class LearningGap(GapException):
    """A learning obligation could not be fulfilled."""

    obligation_ref: str
    reason: str

    def __str__(self) -> str:
        return f"LearningGap({self.obligation_ref})"


@dataclass
class AdapterFailure(GapException):
    """An adapter failed to invoke or return a valid receipt."""

    adapter_ref: str
    reason: str

    def __str__(self) -> str:
        return f"AdapterFailure({self.adapter_ref})"


@dataclass
class StorageFailure(GapException):
    """A storage operation failed."""

    store_ref: str
    reason: str

    def __str__(self) -> str:
        return f"StorageFailure({self.store_ref})"


# ---------------------------------------------------------------------------
# Gap receipt
# ---------------------------------------------------------------------------


def _exact_text(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise TypeError(f"{name} must be an exact non-empty str")
    if len(value) > _MAX_TEXT_CHARS:
        raise ValueError(f"{name} exceeds {_MAX_TEXT_CHARS} characters")
    return value


def _exact_rows(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if len(value) > _MAX_RECEIPT_ROWS:
        raise ValueError(f"{name} exceeds {_MAX_RECEIPT_ROWS} rows")
    rows = value
    for row in rows:
        _exact_text(row, f"{name} item")
    if len(rows) != len(set(rows)):
        raise ValueError(f"{name} must not contain duplicates")
    return rows


def _wire_rows(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} must be an exact list")
    if len(value) > _MAX_RECEIPT_ROWS:
        raise ValueError(f"{name} exceeds {_MAX_RECEIPT_ROWS} rows")
    rows = tuple(value)
    return _exact_rows(rows, name)


def _gap_material(
    *,
    kind: GapKind,
    status: str,
    source_refs: tuple[str, ...],
    blockers: tuple[str, ...],
    missing_contract_refs: tuple[str, ...],
    rejected_candidate_refs: tuple[str, ...],
    recommended_owner: RepairOwner,
    safe_response_action: str,
) -> dict[str, Any]:
    return {
        "abi_version": GAP_RECEIPT_ABI_VERSION,
        "kind": kind.value,
        "status": status,
        "source_refs": list(source_refs),
        "blockers": list(blockers),
        "missing_contract_refs": list(missing_contract_refs),
        "rejected_candidate_refs": list(rejected_candidate_refs),
        "recommended_owner": recommended_owner.value,
        "safe_response_action": safe_response_action,
    }


def _validate_gap_fields(
    *,
    kind: object,
    status: object,
    source_refs: object,
    blockers: object,
    missing_contract_refs: object,
    rejected_candidate_refs: object,
    recommended_owner: object,
    safe_response_action: object,
) -> tuple[
    GapKind,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    RepairOwner,
    str,
]:
    if type(kind) is not GapKind:
        raise TypeError("kind must be an exact GapKind")
    if type(recommended_owner) is not RepairOwner:
        raise TypeError("recommended_owner must be an exact RepairOwner")
    return (
        kind,
        _exact_text(status, "status"),
        _exact_rows(source_refs, "source_refs"),
        _exact_rows(blockers, "blockers"),
        _exact_rows(missing_contract_refs, "missing_contract_refs"),
        _exact_rows(rejected_candidate_refs, "rejected_candidate_refs"),
        recommended_owner,
        _exact_text(safe_response_action, "safe_response_action"),
    )


@dataclass(frozen=True)
class GapReceipt:
    """Strict content-addressed receipt for one failed or unresolved cycle."""

    abi_version: int
    gap_ref: str
    kind: GapKind
    status: str
    source_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    missing_contract_refs: tuple[str, ...]
    rejected_candidate_refs: tuple[str, ...]
    recommended_owner: RepairOwner
    safe_response_action: str

    def __post_init__(self) -> None:
        if type(self.abi_version) is not int or self.abi_version != GAP_RECEIPT_ABI_VERSION:
            raise ValueError(f"abi_version must be exactly {GAP_RECEIPT_ABI_VERSION}")
        _exact_text(self.gap_ref, "gap_ref")
        fields = _validate_gap_fields(
            kind=self.kind,
            status=self.status,
            source_refs=self.source_refs,
            blockers=self.blockers,
            missing_contract_refs=self.missing_contract_refs,
            rejected_candidate_refs=self.rejected_candidate_refs,
            recommended_owner=self.recommended_owner,
            safe_response_action=self.safe_response_action,
        )
        expected = stable_ref("gap", _gap_material_from_fields(fields))
        if self.gap_ref != expected:
            raise ValueError("gap_ref mismatch")

    @staticmethod
    def _from_checked(
        gap_ref: str,
        fields: tuple[
            GapKind,
            str,
            tuple[str, ...],
            tuple[str, ...],
            tuple[str, ...],
            tuple[str, ...],
            RepairOwner,
            str,
        ],
    ) -> "GapReceipt":
        value = object.__new__(GapReceipt)
        for name, item in zip(
            (
                "kind", "status", "source_refs", "blockers",
                "missing_contract_refs", "rejected_candidate_refs",
                "recommended_owner", "safe_response_action",
            ),
            fields,
            strict=True,
        ):
            object.__setattr__(value, name, item)
        object.__setattr__(value, "abi_version", GAP_RECEIPT_ABI_VERSION)
        object.__setattr__(value, "gap_ref", gap_ref)
        return value

    @classmethod
    def create(
        cls,
        *,
        kind: GapKind,
        status: str,
        source_refs: tuple[str, ...],
        blockers: tuple[str, ...],
        missing_contract_refs: tuple[str, ...] = (),
        rejected_candidate_refs: tuple[str, ...] = (),
        recommended_owner: RepairOwner,
        safe_response_action: str,
    ) -> "GapReceipt":
        if cls is not GapReceipt:
            raise TypeError("GapReceipt factories reject subclasses")
        fields = _validate_gap_fields(
            kind=kind,
            status=status,
            source_refs=source_refs,
            blockers=blockers,
            missing_contract_refs=missing_contract_refs,
            rejected_candidate_refs=rejected_candidate_refs,
            recommended_owner=recommended_owner,
            safe_response_action=safe_response_action,
        )
        gap_ref = stable_ref("gap", _gap_material_from_fields(fields))
        return GapReceipt._from_checked(gap_ref, fields)

    def as_dict(self) -> dict[str, Any]:
        return {
            "gap_ref": self.gap_ref,
            **_gap_material(
                kind=self.kind,
                status=self.status,
                source_refs=self.source_refs,
                blockers=self.blockers,
                missing_contract_refs=self.missing_contract_refs,
                rejected_candidate_refs=self.rejected_candidate_refs,
                recommended_owner=self.recommended_owner,
                safe_response_action=self.safe_response_action,
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GapReceipt":
        if cls is not GapReceipt:
            raise TypeError("GapReceipt factories reject subclasses")
        if type(data) is not dict:
            raise TypeError("GapReceipt payload must be an exact dict")
        expected_fields = frozenset(
            {
                "abi_version", "gap_ref", "kind", "status", "source_refs",
                "blockers", "missing_contract_refs", "rejected_candidate_refs",
                "recommended_owner", "safe_response_action",
            }
        )
        if len(data) != len(expected_fields):
            raise ValueError("GapReceipt payload has wrong field count")
        if any(type(key) is not str for key in data):
            raise TypeError("GapReceipt field names must be exact strings")
        actual_fields = frozenset(data)
        if actual_fields != expected_fields:
            raise ValueError("GapReceipt fields mismatch")
        if type(data["abi_version"]) is not int or data["abi_version"] != GAP_RECEIPT_ABI_VERSION:
            raise ValueError(f"abi_version must be exactly {GAP_RECEIPT_ABI_VERSION}")
        gap_ref = _exact_text(data["gap_ref"], "gap_ref")
        kind_name = _exact_text(data["kind"], "kind")
        owner_name = _exact_text(data["recommended_owner"], "recommended_owner")
        try:
            kind = GapKind(kind_name)
            recommended_owner = RepairOwner(owner_name)
        except ValueError as exc:
            raise ValueError("GapReceipt contains an unknown closed enum value") from exc
        receipt = cls.create(
            kind=kind,
            status=_exact_text(data["status"], "status"),
            source_refs=_wire_rows(data["source_refs"], "source_refs"),
            blockers=_wire_rows(data["blockers"], "blockers"),
            missing_contract_refs=_wire_rows(
                data["missing_contract_refs"], "missing_contract_refs"
            ),
            rejected_candidate_refs=_wire_rows(
                data["rejected_candidate_refs"], "rejected_candidate_refs"
            ),
            recommended_owner=recommended_owner,
            safe_response_action=_exact_text(
                data["safe_response_action"], "safe_response_action"
            ),
        )
        if receipt.gap_ref != gap_ref:
            raise ValueError("gap_ref mismatch")
        if receipt.as_dict() != data:
            raise ValueError("non-canonical GapReceipt encoding")
        return receipt


def _gap_material_from_fields(
    fields: tuple[
        GapKind,
        str,
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        RepairOwner,
        str,
    ],
) -> dict[str, Any]:
    return _gap_material(
        kind=fields[0],
        status=fields[1],
        source_refs=fields[2],
        blockers=fields[3],
        missing_contract_refs=fields[4],
        rejected_candidate_refs=fields[5],
        recommended_owner=fields[6],
        safe_response_action=fields[7],
    )

# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


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
        )

    def _classify_exception(self, exc: BaseException) -> GapReceipt:
        if isinstance(exc, LaterOwnerNotAdmitted):
            return self._make_gap(
                GapKind.IMPLEMENTATION,
                status="later_owner_not_admitted",
                source_refs=(exc.verified_meaning_ref,),
                blockers=("later_owner_not_admitted",),
                missing_contract_refs=(exc.contract_ref,),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="stop_without_surface",
            )
        if isinstance(exc, MissingOwner):
            return self._make_gap(
                GapKind.IMPLEMENTATION,
                status="activation_failure",
                source_refs=(),
                blockers=(f"missing owner: {exc.owner_name}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="activation_failure",
            )
        if isinstance(exc, VerificationFailure):
            return self._make_gap(
                GapKind.VERIFICATION,
                status="verification_failed",
                source_refs=(exc.cycle_ref,),
                blockers=(f"rejection: {exc.code}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="reject_candidate",
            )
        if isinstance(exc, CoverageGap):
            return self._make_gap(
                GapKind.DESIGNATION,
                status="coverage_gap",
                source_refs=(exc.span_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.DATA,
                safe_response_action="request_designation",
            )
        if isinstance(exc, EffectDenied):
            return self._make_gap(
                GapKind.OPERATION,
                status="effect_denied",
                source_refs=(exc.effect_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.ADAPTER,
                safe_response_action="hold_effect",
            )
        if isinstance(exc, RealizationFailure):
            return self._make_gap(
                GapKind.REALIZATION,
                status="realization_failed",
                source_refs=(exc.response_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.TRAINING,
                safe_response_action="hold_response",
            )
        if isinstance(exc, BudgetExhausted):
            return self._make_gap(
                GapKind.PERFORMANCE,
                status="budget_exhausted",
                source_refs=(),
                blockers=(f"budget exhausted: {exc.budget_name}={exc.limit}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="bound_cycle",
            )
        if isinstance(exc, ResourceUnavailable):
            return self._make_gap(
                GapKind.RESOURCE,
                status="resource_unavailable",
                source_refs=(exc.resource_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.DATA,
                safe_response_action="retry_or_degrade",
            )
        if isinstance(exc, PermissionDenied):
            return self._make_gap(
                GapKind.PERMISSION,
                status="permission_denied",
                source_refs=(exc.capability_ref,),
                blockers=(f"denied for {exc.participant_ref}",),
                recommended_owner=RepairOwner.POLICY,
                safe_response_action="deny_operation",
            )
        if isinstance(exc, SemanticConflict):
            return self._make_gap(
                GapKind.AUTHORITY,
                status="semantic_conflict",
                source_refs=(exc.graph_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.AUTHORITY,
                safe_response_action="request_authority_review",
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
            )
        if isinstance(exc, ReferenceAmbiguity):
            return self._make_gap(
                GapKind.REFERENCE,
                status="reference_ambiguous",
                source_refs=(exc.ref_ref,),
                blockers=("reference_ambiguous",),
                rejected_candidate_refs=exc.candidate_refs,
                recommended_owner=RepairOwner.TRAINING,
                safe_response_action="request_reference_resolution",
            )
        if isinstance(exc, AbsentIdentity):
            return self._make_gap(
                GapKind.REFERENCE,
                status="identity_absent",
                source_refs=(exc.identity_ref,),
                blockers=(f"frame absent: {exc.frame_ref}",),
                recommended_owner=RepairOwner.AUTHORITY,
                safe_response_action="request_identity",
            )
        if isinstance(exc, ProposalGap):
            return self._make_gap(
                GapKind.PROPOSAL,
                status="proposal_gap",
                source_refs=(exc.cycle_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.TRAINING,
                safe_response_action="request_proposal_review",
            )
        if isinstance(exc, InferenceBound):
            return self._make_gap(
                GapKind.INFERENCE,
                status="inference_bound",
                source_refs=(exc.query_ref,),
                blockers=(f"bound: {exc.bound_name}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="bound_inference",
            )
        if isinstance(exc, StateGap):
            return self._make_gap(
                GapKind.STATE,
                status="state_gap",
                source_refs=(exc.entity_ref,),
                blockers=(f"dimension missing: {exc.dimension_ref}",),
                recommended_owner=RepairOwner.DATA,
                safe_response_action="request_state_evidence",
            )
        if isinstance(exc, MissingTransition):
            return self._make_gap(
                GapKind.TRANSITION,
                status="transition_missing",
                source_refs=(exc.from_state,),
                blockers=(f"no transition to {exc.to_state}",),
                recommended_owner=RepairOwner.AUTHORITY,
                safe_response_action="request_transition_definition",
            )
        if isinstance(exc, TransitionBoundExhausted):
            return self._make_gap(
                GapKind.TRANSITION,
                status="transition_bound_exhausted",
                source_refs=(exc.transition_ref,),
                blockers=(f"proof bound exhausted: {exc.bound}",),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="bound_transition",
            )
        if isinstance(exc, LearningGap):
            return self._make_gap(
                GapKind.LEARNING,
                status="learning_gap",
                source_refs=(exc.obligation_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.POLICY,
                safe_response_action="request_learning_review",
            )
        if isinstance(exc, AdapterFailure):
            return self._make_gap(
                GapKind.ADAPTER,
                status="adapter_failure",
                source_refs=(exc.adapter_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.ADAPTER,
                safe_response_action="retry_adapter",
            )
        if isinstance(exc, StorageFailure):
            return self._make_gap(
                GapKind.STORAGE,
                status="storage_failure",
                source_refs=(exc.store_ref,),
                blockers=(exc.reason,),
                recommended_owner=RepairOwner.RUNTIME,
                safe_response_action="retry_storage",
            )
        # Unknown exception — implementation gap, never generic clarification.
        return self._make_gap(
            GapKind.IMPLEMENTATION,
            status="activation_failure",
            source_refs=(),
            blockers=(f"unhandled exception: {type(exc).__name__}",),
            recommended_owner=RepairOwner.RUNTIME,
            safe_response_action="activation_failure",
        )

    @staticmethod
    def _make_gap(
        kind: GapKind,
        *,
        status: str,
        source_refs: tuple[str, ...],
        blockers: tuple[str, ...],
        missing_contract_refs: tuple[str, ...] = (),
        rejected_candidate_refs: tuple[str, ...] = (),
        recommended_owner: RepairOwner,
        safe_response_action: str,
    ) -> GapReceipt:
        return GapReceipt.create(
            kind=kind,
            status=status,
            source_refs=source_refs,
            blockers=blockers,
            missing_contract_refs=missing_contract_refs,
            rejected_candidate_refs=rejected_candidate_refs,
            recommended_owner=recommended_owner,
            safe_response_action=safe_response_action,
        )