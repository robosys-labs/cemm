"""Narrow fail-closed authorization boundary for actual runtime effects.

Semantic eligibility licenses cognition only.  This module owns the separate boundary
for durable persistence, execution, disclosure and emission.  Receipts are tied to one
exact authority generation and stage capability; an allowed receipt from another pass
or authority generation is not reusable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..stage_contracts import CoreStage, EffectKind, stage_contract


class EffectDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class EffectAuthorizationRequest:
    effect_ref: str
    cycle_ref: str
    pass_ref: str
    capability_nonce: str
    effect_kind: EffectKind
    stage: CoreStage
    permission_ref: str
    authority_generation: int
    authority_fingerprint: str
    target_refs: tuple[str, ...] = ()
    audience_refs: tuple[str, ...] = ()
    authorization_pins: tuple[PinnedRecord, ...] = ()
    proof_refs: tuple[str, ...] = ()
    patch_ref: str = ""
    patch_fingerprint: str = ""
    expected_store_revision: int | None = None
    patch_generation_domains: tuple[str, ...] = ()
    patch_record_kinds: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.effect_ref or not self.cycle_ref or not self.pass_ref or not self.capability_nonce:
            raise ValueError("effect request requires exact cycle/pass/capability identity")
        if not self.permission_ref:
            raise ValueError("effect request requires permission scope")
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise ValueError("effect request requires exact semantic authority generation")
        for values, label in (
            (self.target_refs, "target refs"),
            (self.audience_refs, "audience refs"),
            (self.proof_refs, "proof refs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate effect {label}")
        if len(self.patch_generation_domains) != len(set(self.patch_generation_domains)):
            raise ValueError("duplicate patch generation domains")
        if len(self.patch_record_kinds) != len(set(self.patch_record_kinds)):
            raise ValueError("duplicate patch record kinds")
        pin_keys = tuple((pin.key, pin.record_fingerprint) for pin in self.authorization_pins)
        if len(pin_keys) != len(set(pin_keys)):
            raise ValueError("duplicate effect authorization pins")


@dataclass(frozen=True, slots=True)
class EffectAuthorizationReceipt:
    receipt_ref: str
    request_ref: str
    cycle_ref: str
    pass_ref: str
    capability_nonce: str
    effect_kind: EffectKind
    stage: CoreStage
    decision: EffectDecision
    authority_generation: int
    authority_fingerprint: str
    permission_ref: str
    target_refs: tuple[str, ...]
    audience_refs: tuple[str, ...]
    checked_pins: tuple[PinnedRecord, ...]
    proof_refs: tuple[str, ...]
    patch_ref: str
    patch_fingerprint: str
    store_revision_before: int | None
    patch_generation_domains: tuple[str, ...]
    patch_record_kinds: tuple[str, ...]
    reason_refs: tuple[str, ...]

    @property
    def allowed(self) -> bool:
        return self.decision == EffectDecision.ALLOW


class EffectAuthorizationBoundary:
    def __init__(self, store) -> None:
        self.__store = store

    def __getattr__(self, name):
        # The authorization object is not a store capability. Services may never
        # recover a mutable-store handle through this boundary.
        if name in {"store", "base_store", "_store"} or name.startswith("_"):
            raise AttributeError(name)
        raise AttributeError(name)

    def authorize(self, request: EffectAuthorizationRequest) -> EffectAuthorizationReceipt:
        reasons: list[str] = []
        contract = stage_contract(request.stage)
        current = self.__store.current_authority_snapshot()
        if (
            request.authority_generation != current.generation
            or request.authority_fingerprint != current.authority_fingerprint
        ):
            reasons.append("effect_request_authority_generation_stale")
        if request.effect_kind not in contract.allowed_effects:
            reasons.append("effect_not_allowed_at_stage")

        checked: list[PinnedRecord] = []
        for pin in request.authorization_pins:
            stored = self.__store.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if (
                stored is None
                or stored.record_fingerprint != pin.record_fingerprint
                or self.__store.is_invalidated(pin.record_kind, pin.record_ref, pin.revision)
            ):
                reasons.append("stale_missing_or_invalidated_effect_authorization_pin")
            else:
                checked.append(pin)

        metadata = dict(request.metadata)
        if request.effect_kind == EffectKind.DURABLE_PERSISTENCE:
            if not request.target_refs:
                reasons.append("durable_persistence_requires_explicit_targets")
            if not request.patch_ref or not request.patch_fingerprint:
                reasons.append("durable_persistence_requires_exact_patch_identity")
            if request.expected_store_revision is None:
                reasons.append("durable_persistence_requires_exact_cas_revision")
            elif int(request.expected_store_revision) != int(self.__store.revision):
                reasons.append("durable_persistence_cas_revision_stale")
            if not metadata.get("persistence_reason"):
                reasons.append("durable_persistence_reason_required")
            allowed_domains = {domain.value for domain in contract.allowed_generation_changes}
            requested_domains = set(request.patch_generation_domains)
            forbidden_domains = requested_domains.difference(allowed_domains)
            if forbidden_domains:
                reasons.append(
                    "durable_persistence_forbidden_generation_domains:"
                    + ",".join(sorted(forbidden_domains))
                )
            if "authority" in requested_domains:
                reasons.append("authority_publication_requires_post_pass_maintenance_boundary")
            patch_permission = str(metadata.get("patch_permission_ref", ""))
            if patch_permission and patch_permission not in {"public", request.permission_ref}:
                reasons.append("durable_persistence_permission_scope_widened")
            patch_context = str(metadata.get("patch_context_ref", ""))
            cycle_context = str(metadata.get("cycle_context_ref", ""))
            if patch_context and cycle_context and patch_context not in {"global", cycle_context}:
                reasons.append("durable_persistence_context_scope_widened")
            # Authority publication is deliberately outside an active semantic pass.
            # Stage 22 may schedule it for post-pass maintenance but cannot publish it.
            if metadata.get("publishes_authority"):
                reasons.append("authority_publication_requires_post_pass_maintenance_boundary")

        elif request.effect_kind == EffectKind.EXTERNAL_OPERATION:
            if request.stage != CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE:
                reasons.append("external_operation_outside_stage16")
            if metadata.get("operation_authorization_decision") != "allow":
                reasons.append("operation_authorization_not_allow")
            if not metadata.get("prepared_journal_ref"):
                reasons.append("prepared_effect_journal_required")
            if not metadata.get("idempotency_identity"):
                reasons.append("external_operation_idempotency_identity_required")
            if not request.authorization_pins:
                reasons.append("external_operation_requires_exact_authorization_pins")

        elif request.effect_kind == EffectKind.PROTECTED_DISCLOSURE:
            if request.stage != CoreStage.VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION:
                reasons.append("protected_disclosure_outside_stage20")
            if not request.audience_refs:
                reasons.append("explicit_audience_required")
            if not metadata.get("disclosure_gate_passed", False):
                reasons.append("disclosure_gate_not_passed")
            if not str(metadata.get("disclosure_authorization_ref", "")).strip():
                reasons.append("exact_disclosure_authorization_ref_required")
            if not str(metadata.get("disclosure_authorization_content_hash", "")).strip():
                reasons.append("exact_disclosure_authorization_content_hash_required")
            if not request.authorization_pins:
                reasons.append("protected_disclosure_requires_exact_authorization_pins")
            if not request.proof_refs:
                reasons.append("protected_disclosure_requires_semantic_proof")

        elif request.effect_kind == EffectKind.EXTERNAL_EMISSION:
            if request.stage != CoreStage.VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION:
                reasons.append("external_emission_outside_stage20")
            if not request.audience_refs:
                reasons.append("explicit_audience_required")
            if not metadata.get("semantic_preservation_passed", False):
                reasons.append("semantic_preservation_not_proven")
            if metadata.get("emission_gate_decision") != "allow":
                reasons.append("emission_gate_not_allow")
            channel_contract_ref = str(metadata.get("channel_contract_ref", ""))
            if not channel_contract_ref:
                reasons.append("exact_channel_contract_required")
            elif not any(pin.record_ref == channel_contract_ref for pin in checked):
                reasons.append("exact_channel_contract_pin_required")
            if not request.authorization_pins:
                reasons.append("external_emission_requires_exact_authorization_pins")
            if not metadata.get("idempotency_identity"):
                reasons.append("external_emission_idempotency_identity_required")
            if not request.proof_refs:
                reasons.append("external_emission_requires_semantic_proof")

        decision = EffectDecision.DENY if reasons else EffectDecision.ALLOW
        receipt_ref = "effect-auth:" + semantic_fingerprint(
            "effect-authorization-v351",
            (
                request.effect_ref,
                request.cycle_ref,
                request.pass_ref,
                request.capability_nonce,
                request.effect_kind.value,
                int(request.stage),
                request.authority_generation,
                request.authority_fingerprint,
                request.permission_ref,
                request.target_refs,
                request.audience_refs,
                decision.value,
                tuple((pin.key, pin.record_fingerprint) for pin in checked),
                request.proof_refs,
                request.patch_ref, request.patch_fingerprint, request.expected_store_revision,
                request.patch_generation_domains, request.patch_record_kinds,
                tuple(sorted(set(reasons))),
            ),
            24,
        )
        return EffectAuthorizationReceipt(
            receipt_ref=receipt_ref,
            request_ref=request.effect_ref,
            cycle_ref=request.cycle_ref,
            pass_ref=request.pass_ref,
            capability_nonce=request.capability_nonce,
            effect_kind=request.effect_kind,
            stage=request.stage,
            decision=decision,
            authority_generation=request.authority_generation,
            authority_fingerprint=request.authority_fingerprint,
            permission_ref=request.permission_ref,
            target_refs=tuple(request.target_refs),
            audience_refs=tuple(request.audience_refs),
            checked_pins=tuple(checked),
            proof_refs=tuple(request.proof_refs),
            patch_ref=request.patch_ref,
            patch_fingerprint=request.patch_fingerprint,
            store_revision_before=request.expected_store_revision,
            patch_generation_domains=tuple(request.patch_generation_domains),
            patch_record_kinds=tuple(request.patch_record_kinds),
            reason_refs=tuple(sorted(set(reasons))),
        )

    def require(self, request: EffectAuthorizationRequest) -> EffectAuthorizationReceipt:
        receipt = self.authorize(request)
        if not receipt.allowed:
            raise PermissionError(
                f"effect denied {request.effect_kind.value}: "
                + ",".join(receipt.reason_refs)
            )
        return receipt


__all__ = [
    "EffectAuthorizationBoundary",
    "EffectAuthorizationReceipt",
    "EffectAuthorizationRequest",
    "EffectDecision",
]
