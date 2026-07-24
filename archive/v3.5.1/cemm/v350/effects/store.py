"""Pre-effect guarded durable persistence for canonical v3.5.1 services.

Runtime services never receive the mutable semantic store as their ordinary ``store``
argument.  They receive a read-only CycleArtifactStoreView plus this narrow writer.
Every GraphPatch must be authorized *before* application by an exact receipt tied to
one patch fingerprint, store revision, stage, permission scope and authority generation.
"""
from __future__ import annotations

from typing import Iterable

from .authorization import (
    EffectAuthorizationBoundary,
    EffectAuthorizationReceipt,
    EffectAuthorizationRequest,
)
from ..learning.model import PinnedRecord
from ..runtime_generations import infer_patch_domains
from ..stage_contracts import EffectKind


class EffectStoreAuthorizationError(PermissionError):
    pass


class AuthorizedEffectStore:
    def __init__(
        self,
        *,
        base_store,
        read_store,
        boundary: EffectAuthorizationBoundary,
        capability,
        permission_ref: str,
        context_ref: str,
    ) -> None:
        self.__base = base_store
        self.__read = read_store
        self.__boundary = boundary
        self.__capability = capability
        self.__permission_ref = permission_ref
        self.__context_ref = context_ref
        self._receipts: list[EffectAuthorizationReceipt] = []

    @property
    def receipts(self) -> tuple[EffectAuthorizationReceipt, ...]:
        return tuple(self._receipts)

    @property
    def read_store(self):
        return self.__read

    def __getattr__(self, name):
        # Read APIs are delegated through the cycle-local durable+workspace view.
        if name in {"apply_patch", "close"}:
            raise AttributeError(name)
        if name.startswith("_") or name in {"base_store", "read_store", "boundary", "capability"}:
            raise AttributeError(name)
        return getattr(self.__read, name)

    @staticmethod
    def _patch_targets(patch) -> tuple[str, ...]:
        return tuple(sorted({str(operation.target_ref) for operation in patch.operations}))

    def authorize_patch(
        self,
        patch,
        *,
        authorization_pins: Iterable[PinnedRecord] = (),
        proof_refs: Iterable[str] = (),
        publishes_authority: bool = False,
    ) -> EffectAuthorizationReceipt:
        expected_revision = getattr(patch, "expected_store_revision", None)
        domains = tuple(sorted(domain.value for domain in infer_patch_domains(patch)))
        record_kinds = tuple(sorted({operation.record_kind.value for operation in patch.operations}))
        request = EffectAuthorizationRequest(
            effect_ref=f"persistence:{patch.patch_ref}",
            cycle_ref=self.__capability.cycle_ref,
            pass_ref=self.__capability.pass_ref,
            capability_nonce=self.__capability.nonce,
            effect_kind=EffectKind.DURABLE_PERSISTENCE,
            stage=self.__capability.stage,
            permission_ref=self.__permission_ref,
            authority_generation=self.__capability.authority_generation,
            authority_fingerprint=self.__capability.authority_fingerprint,
            target_refs=self._patch_targets(patch),
            authorization_pins=tuple(authorization_pins),
            proof_refs=tuple(sorted(set(map(str, proof_refs)))),
            patch_ref=str(patch.patch_ref),
            patch_fingerprint=str(patch.fingerprint),
            expected_store_revision=expected_revision,
            patch_generation_domains=domains,
            patch_record_kinds=record_kinds,
            metadata={
                "persistence_reason": ";".join(
                    sorted({str(operation.reason) for operation in patch.operations if operation.reason})
                ),
                "publishes_authority": bool(publishes_authority),
                "patch_permission_ref": str(getattr(patch, "permission_ref", "")),
                "patch_context_ref": str(getattr(patch, "context_ref", "")),
                "cycle_context_ref": self.__context_ref,
            },
        )
        return self.__boundary.authorize(request)

    def apply_patch(self, patch, *, receipt: EffectAuthorizationReceipt):
        if not isinstance(receipt, EffectAuthorizationReceipt) or not receipt.allowed:
            raise EffectStoreAuthorizationError("durable patch requires allowed effect authorization receipt")
        if receipt.effect_kind is not EffectKind.DURABLE_PERSISTENCE:
            raise EffectStoreAuthorizationError("receipt does not authorize durable persistence")
        if (
            receipt.cycle_ref != self.__capability.cycle_ref
            or receipt.pass_ref != self.__capability.pass_ref
            or receipt.capability_nonce != self.__capability.nonce
        ):
            raise EffectStoreAuthorizationError("persistence receipt belongs to another cycle/pass/capability")
        if receipt.stage != self.__capability.stage:
            raise EffectStoreAuthorizationError("persistence receipt belongs to another stage")
        if (
            receipt.authority_generation != self.__capability.authority_generation
            or receipt.authority_fingerprint != self.__capability.authority_fingerprint
        ):
            raise EffectStoreAuthorizationError("persistence receipt belongs to another authority generation")
        if receipt.permission_ref not in {"public", self.__permission_ref}:
            raise EffectStoreAuthorizationError("persistence receipt widens permission scope")
        if receipt.patch_ref != str(patch.patch_ref) or receipt.patch_fingerprint != str(patch.fingerprint):
            raise EffectStoreAuthorizationError("persistence receipt does not bind the exact GraphPatch")
        if receipt.store_revision_before != self.__base.revision:
            raise EffectStoreAuthorizationError("persistence receipt CAS revision is stale")
        if set(receipt.target_refs) != set(self._patch_targets(patch)):
            raise EffectStoreAuthorizationError("persistence receipt target set differs from GraphPatch")
        if getattr(patch, "expected_store_revision", None) != receipt.store_revision_before:
            raise EffectStoreAuthorizationError("GraphPatch expected revision differs from authorized CAS revision")
        current_domains = tuple(sorted(domain.value for domain in infer_patch_domains(patch)))
        current_kinds = tuple(sorted({operation.record_kind.value for operation in patch.operations}))
        if current_domains != tuple(receipt.patch_generation_domains):
            raise EffectStoreAuthorizationError("GraphPatch generation domains differ from pre-effect authorization")
        if current_kinds != tuple(receipt.patch_record_kinds):
            raise EffectStoreAuthorizationError("GraphPatch record kinds differ from pre-effect authorization")
        result = self.__base.apply_patch(patch)
        if getattr(result, "committed", False):
            self._receipts.append(receipt)
        return result

    def authorize_and_apply_patch(
        self,
        patch,
        *,
        authorization_pins: Iterable[PinnedRecord] = (),
        proof_refs: Iterable[str] = (),
        publishes_authority: bool = False,
    ):
        receipt = self.authorize_patch(
            patch,
            authorization_pins=authorization_pins,
            proof_refs=proof_refs,
            publishes_authority=publishes_authority,
        )
        if not receipt.allowed:
            raise EffectStoreAuthorizationError(
                "durable persistence denied:" + ",".join(receipt.reason_refs)
            )
        result = self.apply_patch(patch, receipt=receipt)
        return result, receipt


__all__ = ["AuthorizedEffectStore", "EffectStoreAuthorizationError"]
