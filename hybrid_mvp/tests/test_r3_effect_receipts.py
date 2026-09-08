"""R3 exact effect/no-effect and atomic persistence tests."""
from __future__ import annotations

import sqlite3

import pytest

from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r3_effects import (
    EffectReceipt,
    EffectStatus,
    NoEffectReason,
    NoEffectReceipt,
)
from cemm_authoritative_hybrid.r3_persistence import predicted_effect_pin

__cemm_test_inventory__ = {
    "tests/test_r3_effect_receipts.py::test_atomic_effect_transaction_advances_world_and_effect_together": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-atomic-effect-transaction-advances-world-and-effect-together",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "8a11fa057579688ee60acff6870d4cf3767e5e3b5860c04c7c4b4d5a5983c913"
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


def test_atomic_effect_transaction_advances_world_and_effect_together(
    tmp_path, linked_authority, monkeypatch
) -> None:
    from cemm_authoritative_hybrid import persistence, r3_persistence
    from cemm_authoritative_hybrid.r3_codec import thaw_json
    from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, R3EffectGateway
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalState, effect_journal_get
    from tests.test_foundation_effect_currentness import (
        _LampAdapter, _effect_case, _seed_lamp_off, _stores,
    )

    stores = _stores("atomic-rollback", tmp_path, linked_authority.generation)
    adapter = _LampAdapter()
    try:
        _seed_lamp_off(stores)
        situation, meaning, evaluation = _effect_case(
            stores, linked_authority, turn_ref="turn:atomic-rollback"
        )
        before = stores.revision_pin()
        before_facts = stores.r3_world_facts()
        before_session = stores.r3_session_snapshot(situation.session_ref)
        original_write = persistence._r3_write_session_sqlite

        def fail_after_session_write(*args, **kwargs):
            # Real world and session SQL writes occur before this injected I/O
            # failure. The transaction must roll them back, retaining OBSERVED.
            original_write(*args, **kwargs)
            raise sqlite3.OperationalError("injected terminal transaction failure")

        with monkeypatch.context() as fault:
            fault.setattr(persistence, "_r3_write_session_sqlite", fail_after_session_write)
            with pytest.raises(sqlite3.OperationalError, match="injected terminal transaction failure"):
                R3EffectGateway(stores, AdapterRegistry({"adapter:state": adapter})).execute(
                    evaluation, meaning, situation
                )
        assert len(adapter.requests) == 1
        key = adapter.requests[0].idempotency_key
        observed = effect_journal_get(stores, key)
        assert observed is not None and observed.entry.state is EffectJournalState.OBSERVED
        assert observed.receipt_payload is None and observed.entry.outcome_ref is None
        assert stores.r3_world_facts() == before_facts
        assert stores.r3_session_snapshot(situation.session_ref) == before_session
        after_failure = stores.revision_pin()
        assert after_failure.world_revision == before.world_revision
        assert after_failure.session_revision == before.session_revision
        assert after_failure.effect_revision == observed.entry.effect_revision
    finally:
        stores.close()

    reopened = _stores("atomic-rollback", tmp_path, linked_authority.generation)
    try:
        assert reopened.revision_pin() == after_failure
        assert reopened.r3_world_facts() == before_facts
        assert reopened.r3_session_snapshot(situation.session_ref) == before_session
        assert effect_journal_get(reopened, key) == observed
        gateway = R3EffectGateway(reopened, AdapterRegistry({"adapter:state": adapter}))
        receipt = gateway.execute(evaluation, meaning, situation)
        assert receipt.status is EffectStatus.COMMITTED
        assert len(adapter.requests) == 1  # reuse the durable observation, not the device
        assert receipt.output_revision_pin == reopened.revision_pin()
        assert receipt.output_revision_pin.world_revision == before.world_revision + 1
        assert receipt.output_revision_pin.session_revision == before.session_revision + 1
        assert receipt.output_revision_pin.effect_revision == after_failure.effect_revision + 1
        assert len(receipt.committed_fact_refs) == 1
        assert reopened.world.get(receipt.committed_fact_refs[0]) is not None
        terminal = effect_journal_get(reopened, key)
        assert terminal.entry.state is EffectJournalState.COMMITTED
        assert terminal.entry.outcome_ref == receipt.receipt_ref
        assert terminal.entry.parent_journal_ref == observed.entry.journal_ref
        assert EffectReceipt.from_dict(thaw_json(terminal.receipt_payload)) == receipt
        assert gateway.execute(evaluation, meaning, situation) == receipt
        assert reopened.revision_pin() == receipt.output_revision_pin
        assert len(adapter.requests) == 1
    finally:
        reopened.close()
    assert not hasattr(r3_persistence, "commit_effect_transaction")
    assert "commit_effect_transaction" not in r3_persistence.__all__


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
