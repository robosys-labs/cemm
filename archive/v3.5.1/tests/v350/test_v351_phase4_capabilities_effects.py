from __future__ import annotations

from dataclasses import dataclass, field

from cemm.v350.effects.authorization import (
    EffectAuthorizationBoundary, EffectAuthorizationRequest, EffectDecision,
)
from cemm.v350.stage_contracts import CoreStage, EffectKind
from cemm.v350.storage.model import RecordKind


@dataclass(frozen=True)
class _Authority:
    generation: int = 7
    authority_fingerprint: str = "authority:test"


class _Store:
    revision = 3

    def current_authority_snapshot(self):
        return _Authority()

    def get_record(self, *_args, **_kwargs):
        return None

    def is_invalidated(self, *_args, **_kwargs):
        return False


def _request(**kwargs):
    return EffectAuthorizationRequest(
        cycle_ref="cycle:test",
        pass_ref="pass:test",
        capability_nonce="nonce:test",
        authority_generation=7,
        authority_fingerprint="authority:test",
        **kwargs,
    )


def test_semantic_eligibility_cannot_authorize_external_emission_by_itself():
    boundary = EffectAuthorizationBoundary(_Store())
    request = _request(
        effect_ref="effect:test",
        effect_kind=EffectKind.EXTERNAL_EMISSION,
        stage=CoreStage.VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION,
        permission_ref="conversation",
        audience_refs=("referent:user",),
        proof_refs=("proof:semantic-preservation",),
        metadata={
            "semantic_eligible": True,
            "semantic_preservation_passed": True,
            "emission_gate_decision": "deny",
            "channel_contract_ref": "channel:text@1",
            "idempotency_identity": "idempotency:1",
        },
    )
    receipt = boundary.authorize(request)
    assert receipt.decision is EffectDecision.DENY
    assert "emission_gate_not_allow" in receipt.reason_refs


def test_external_operation_requires_stage16_authorization_journal_and_idempotency():
    boundary = EffectAuthorizationBoundary(_Store())
    denied = boundary.authorize(_request(
        effect_ref="effect:op",
        effect_kind=EffectKind.EXTERNAL_OPERATION,
        stage=CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE,
        permission_ref="internal",
        metadata={"operation_authorization_decision": "allow"},
    ))
    assert not denied.allowed
    assert "prepared_effect_journal_required" in denied.reason_refs
    assert "external_operation_idempotency_identity_required" in denied.reason_refs
    assert "external_operation_requires_exact_authorization_pins" in denied.reason_refs


def test_authority_publication_requires_post_pass_maintenance_even_from_stage22():
    boundary = EffectAuthorizationBoundary(_Store())
    receipt = boundary.authorize(_request(
        effect_ref="effect:publish",
        effect_kind=EffectKind.DURABLE_PERSISTENCE,
        stage=CoreStage.CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE,
        permission_ref="internal",
        target_refs=("schema:learned",),
        patch_ref="patch:promote",
        patch_fingerprint="patch-fingerprint:promote",
        expected_store_revision=3,
        metadata={
            "publishes_authority": True,
            "persistence_reason": "promote reviewed candidate",
        },
    ))
    assert not receipt.allowed
    assert "authority_publication_requires_post_pass_maintenance_boundary" in receipt.reason_refs


def test_durable_persistence_requires_explicit_targets_reason_and_cas():
    boundary = EffectAuthorizationBoundary(_Store())
    receipt = boundary.authorize(_request(
        effect_ref="effect:commit",
        effect_kind=EffectKind.DURABLE_PERSISTENCE,
        stage=CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS,
        permission_ref="conversation",
        patch_ref="patch:commit",
        patch_fingerprint="patch-fingerprint:commit",
        expected_store_revision=3,
        metadata={},
    ))
    assert not receipt.allowed
    assert "durable_persistence_requires_explicit_targets" in receipt.reason_refs
    assert "durable_persistence_reason_required" in receipt.reason_refs


def test_effect_receipt_is_bound_to_exact_authority_generation():
    boundary = EffectAuthorizationBoundary(_Store())
    receipt = EffectAuthorizationRequest(
        effect_ref="effect:stale",
        cycle_ref="cycle:test",
        pass_ref="pass:test",
        capability_nonce="nonce:test",
        effect_kind=EffectKind.DURABLE_PERSISTENCE,
        stage=CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS,
        permission_ref="conversation",
        authority_generation=6,
        authority_fingerprint="authority:old",
        target_refs=("knowledge:1",),
        patch_ref="patch:stale",
        patch_fingerprint="patch-fingerprint:stale",
        expected_store_revision=3,
        metadata={
            "persistence_reason": "commit authorized knowledge",
        },
    )
    denied = boundary.authorize(receipt)
    assert not denied.allowed
    assert "effect_request_authority_generation_stale" in denied.reason_refs


def test_durable_persistence_requires_exact_patch_and_cas_revision():
    boundary = EffectAuthorizationBoundary(_Store())
    receipt = boundary.authorize(_request(
        effect_ref="effect:missing-patch",
        effect_kind=EffectKind.DURABLE_PERSISTENCE,
        stage=CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS,
        permission_ref="conversation",
        target_refs=("knowledge:1",),
        metadata={"persistence_reason": "commit"},
    ))
    assert not receipt.allowed
    assert "durable_persistence_requires_exact_patch_identity" in receipt.reason_refs
    assert "durable_persistence_requires_exact_cas_revision" in receipt.reason_refs


def test_durable_persistence_rejects_stale_cas_revision():
    boundary = EffectAuthorizationBoundary(_Store())
    receipt = boundary.authorize(_request(
        effect_ref="effect:stale-cas",
        effect_kind=EffectKind.DURABLE_PERSISTENCE,
        stage=CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS,
        permission_ref="conversation",
        target_refs=("knowledge:1",),
        patch_ref="patch:1",
        patch_fingerprint="patch-fingerprint:1",
        expected_store_revision=2,
        metadata={"persistence_reason": "commit"},
    ))
    assert not receipt.allowed
    assert "durable_persistence_cas_revision_stale" in receipt.reason_refs


def test_guarded_effect_store_binds_receipt_to_exact_patch_and_pre_effect_revision():
    from dataclasses import dataclass
    from cemm.v350.effects.store import AuthorizedEffectStore, EffectStoreAuthorizationError

    @dataclass(frozen=True)
    class Op:
        target_ref: str = "knowledge:1"
        reason: str = "commit authorized knowledge"
        record_kind: RecordKind = RecordKind.CLAIM_RECORD
        operation_kind: str = "upsert"
        payload: dict = None

    @dataclass(frozen=True)
    class Patch:
        patch_ref: str = "patch:guarded"
        fingerprint: str = "patch-fingerprint:guarded"
        expected_store_revision: int = 3
        operations: tuple = (Op(),)
        scope_ref: str = "commit"
        metadata: dict = field(default_factory=dict)

    @dataclass(frozen=True)
    class Capability:
        stage: CoreStage = CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS
        authority_generation: int = 7
        authority_fingerprint: str = "authority:test"
        cycle_ref: str = "cycle:test"
        pass_ref: str = "pass:test"
        nonce: str = "nonce:test"

    @dataclass(frozen=True)
    class Result:
        committed: bool = True

    class Base(_Store):
        def apply_patch(self, patch):
            assert patch.patch_ref == "patch:guarded"
            self.revision += 1
            return Result()

    base = Base()
    guarded = AuthorizedEffectStore(
        base_store=base, read_store=object(),
        boundary=EffectAuthorizationBoundary(base), capability=Capability(),
        permission_ref="conversation", context_ref="conversation",
    )
    patch = Patch()
    receipt = guarded.authorize_patch(patch)
    assert receipt.allowed
    assert receipt.patch_ref == patch.patch_ref
    assert receipt.patch_fingerprint == patch.fingerprint
    assert receipt.store_revision_before == 3
    result = guarded.apply_patch(patch, receipt=receipt)
    assert result.committed
    assert guarded.receipts == (receipt,)

    # The same pre-effect receipt is single-generation/CAS scoped and cannot be reused.
    try:
        guarded.apply_patch(patch, receipt=receipt)
    except EffectStoreAuthorizationError as exc:
        assert "CAS revision is stale" in str(exc)
    else:
        raise AssertionError("stale persistence receipt was reused")
