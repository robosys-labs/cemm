"""R3 exact effect/no-effect and atomic persistence tests."""
from __future__ import annotations

from cemm_authoritative_hybrid.persistence import Fact, RevisionPin, memory_stores
from cemm_authoritative_hybrid.r3_effects import (
    EffectReceipt,
    EffectStatus,
    NoEffectReason,
    NoEffectReceipt,
)
from cemm_authoritative_hybrid.r3_persistence import (
    commit_effect_transaction,
    predicted_effect_pin,
)

__cemm_test_inventory__ = {
    "tests/test_r3_effect_receipts.py::test_atomic_effect_transaction_advances_world_and_effect_together": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-atomic-effect-transaction-advances-world-and-effect-together",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "a6d3364bc9af25c96cef9cef1f9c8a9bf465e6a4c9579459aae7fd7bf10acefd"
    },
    "tests/test_r3_effect_receipts.py::test_committed_receipt_requires_advanced_effect_revision": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-committed-receipt-requires-advanced-effect-revision",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "dd234a00c572dbfc4b12add4ce3491a272b106376870e6cbb10aad48edb1621a"
    },
    "tests/test_r3_effect_receipts.py::test_no_effect_round_trip_preserves_reason": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-no-effect-round-trip-preserves-reason",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "d07767618aaa49abfd13111da93adc9daaecfb2239532c1fe36c25bad3b35373"
    }
}



def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


def test_no_effect_round_trip_preserves_reason() -> None:
    pin = _pin()
    value = NoEffectReceipt.create(
        reason=NoEffectReason.READ_ONLY,
        idempotency_key="effect-key:test",
        journal_origin_ref="journal:origin:test",
        journal_preterminal_ref="journal:preterminal:test",
        decision_ref="decision:test",
        verified_meaning_ref="meaning:test",
        expression_ref="expression:test",
        situation_ref="situation:test",
        program_ref="program:test",
        learning_plan_ref=None,
        obligation_ref=None,
        proof_refs=("proof:test",),
        blocker_refs=(),
        input_revision_pin=pin,
        output_revision_pin=predicted_effect_pin(pin, has_world_delta=False),
    )
    assert NoEffectReceipt.from_dict(value.as_dict()) == value


def test_atomic_effect_transaction_advances_world_and_effect_together() -> None:
    stores = memory_stores(
        authority_generation="authority:test", model_identity="model:test"
    )
    pin = stores.revision_pin()
    fact = Fact(
        fact_ref="fact:test",
        operator="op:state",
        args={"role:subject": "entity:lamp"},
        proof={"source": "decision:test"},
    )
    output = commit_effect_transaction(
        stores,
        expected_pin=pin,
        facts=(fact,),
        effect_key="effect-key:test",
        effect_payload={"r3_receipt": {"receipt_ref": "receipt:test"}},
    )
    assert output == predicted_effect_pin(pin, has_world_delta=True)
    assert stores.world.get("fact:test") == fact
    assert stores.effects.get("effect-key:test") is not None


def test_committed_receipt_requires_advanced_effect_revision() -> None:
    pin = _pin()
    output = predicted_effect_pin(pin, has_world_delta=True)
    value = EffectReceipt.create(
        status=EffectStatus.COMMITTED,
        idempotency_key="effect-key:test",
        journal_origin_ref="journal:origin:test",
        journal_preterminal_ref="journal:preterminal:test",
        reconciliation_required=False,
        decision_ref="decision:test",
        verified_meaning_ref="meaning:test",
        expression_ref="expression:test",
        situation_ref="situation:test",
        program_ref="program:test",
        effect_intent_ref=None,
        actor_ref="participant:system",
        event_type_ref="event:test",
        transition_ref=None,
        adapter_ref="adapter:test",
        adapter_result_ref="adapter_result:test",
        operation_receipt_ref="operation:test",
        observed_delta_refs=("observed_delta:test",),
        committed_fact_refs=("fact:test",),
        proof_refs=(),
        blocker_refs=(),
        input_revision_pin=pin,
        output_revision_pin=output,
    )
    assert EffectReceipt.from_dict(value.as_dict()) == value
