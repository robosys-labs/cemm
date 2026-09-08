"""Current EFFECT-owner successors for retired direct transition commits."""

from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.expressions import (
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
    VerifiedMeaning,
)
from cemm_authoritative_hybrid.persistence import (
    Fact,
    StaleRevisionError,
    memory_stores,
    open_stores,
)
from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
from cemm_authoritative_hybrid.r3_codec import thaw_json
from cemm_authoritative_hybrid.r3_effects import (
    AdapterRegistry,
    AdapterResult,
    AdapterStatus,
    EffectReceipt,
    EffectStatus,
    ObservedDelta,
    R3EffectGateway,
)
from cemm_authoritative_hybrid.r3_persistence import (
    EffectJournalState,
    effect_journal_get,
    install_reviewed_world_facts,
)
from cemm_authoritative_hybrid.situation import SituationContext
from cemm_authoritative_hybrid.state import TransitionEngine


MODEL_IDENTITY = "model:foundation-effect-currentness"


__cemm_test_inventory__ = {
    "tests/test_foundation_effect_currentness.py::test_r3_effect_gateway_atomically_advances_current_world_and_effect": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:transition-simulation-test-commit-appends-history-commit-increments-revision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Effect-Currentness-Repair",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "7568be891c505b97c51bf0080a5a5dcc9d588f63e849d625aedd97734a2f7322",
        "supersedes_node_id": "tests/test_transition_simulation.py::TestCommitAppendsHistory::test_commit_increments_revision",
    },
    "tests/test_foundation_effect_currentness.py::test_r3_effect_gateway_rejects_stale_new_request_but_replays_exact_receipt": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:transition-simulation-test-commit-appends-history-commit-stale-revision-raises",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Effect-Currentness-Repair",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "34072134b5eb58d9258c64146e50588aedf3999b89c60b1ae31333ed0d8a899b",
        "supersedes_node_id": "tests/test_transition_simulation.py::TestCommitAppendsHistory::test_commit_stale_revision_raises",
    },
    "tests/test_foundation_effect_currentness.py::test_r3_effect_gateway_persists_exact_proof_and_journal_history": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:transition-simulation-test-commit-appends-history-commit-records-transition-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Effect-Currentness-Repair",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "58af4921a48bc2afafbfdd81b59082a091c080b6a93496207967428ffcca1056",
        "supersedes_node_id": "tests/test_transition_simulation.py::TestCommitAppendsHistory::test_commit_records_transition_proof",
    },
    "tests/test_foundation_effect_currentness.py::test_r3_effect_gateway_recovers_exact_pending_request_after_restart": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-effect-pending-restart-exact-recovery",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Effect-Currentness-Repair",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "9e1642a91187219f06ba0a3f03b6c1d1090e566409c93b48f930043dd0091811",
    },
    "tests/test_foundation_effect_currentness.py::test_r3_effect_gateway_rejects_stale_new_trusted_admission": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-effect-stale-new-trusted-admission",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Effect-Currentness-Repair",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "3c9a4c56c47bd74b3cfd9e5574d2b5a974ff361ea934eccee98e63a9cf2413dc",
    },
    "tests/test_foundation_effect_currentness.py::test_transition_preview_owner_exposes_no_direct_world_commit": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-transition-preview-owner-exposes-no-direct-world-commit",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Effect-Currentness-Repair",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "be5a4dc41630e8c119a3937d881dd706cd449411b935053a17a81c56cc138775",
    },
}


def _stores(backend: str, root: Path, authority_generation: str):
    if backend == "memory":
        return memory_stores(
            authority_generation=authority_generation,
            model_identity=MODEL_IDENTITY,
        )
    return open_stores(
        root / backend,
        authority_generation=authority_generation,
        model_identity=MODEL_IDENTITY,
    )


def _seed_lamp_off(stores) -> None:
    install_reviewed_world_facts(
        stores,
        facts=(
            Fact(
                fact_ref="fact:foundation-currentness-lamp-off",
                operator="op:state",
                args={
                    "predicate_ref": "dim:power",
                    "role:subject": "entity:lamp",
                    "role:dimension": "dim:power",
                    "role:value": "value:off",
                },
                proof={"source": "sensor:foundation-currentness-lamp-off"},
            ),
        ),
    )


def _situation(stores, *, turn_ref: str) -> SituationContext:
    return SituationContext.create(
        orientation_ref=f"orientation:{turn_ref}",
        proposal_context_ref=f"proposal_context:{turn_ref}",
        mode=SemanticMode.REQUEST,
        session_ref="session:foundation-effect-currentness",
        turn_ref=turn_ref,
        turn_index=1,
        session_phase_ref="active",
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref="participant:system",
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref=f"focus_snapshot:{turn_ref}",
        focus_refs=(),
        obligation_snapshot_ref=f"obligation_snapshot:{turn_ref}",
        obligation_refs=(),
        capability_refs=("cap:set_state",),
        permission_snapshot_ref=f"permission_snapshot:{turn_ref}",
        permission_refs=("permission:set_state",),
        resource_snapshot_ref=f"resource_snapshot:{turn_ref}",
        resource_refs=(),
        adapter_snapshot_ref=f"adapter_snapshot:{turn_ref}",
        adapter_refs=("adapter:state",),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:foundation-currentness",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=(f"evidence:{turn_ref}",),
        epistemic_scope_ref="epistemic_scope:requested",
        revision_pin=stores.revision_pin(),
    )


def _meaning(pin) -> VerifiedMeaning:
    application = SemanticApplication(
        "application:foundation-currentness-set-power",
        "op:event",
        "event:set_state",
        (
            RoleBinding("role:actor", GroundedReference("participant:system")),
            RoleBinding("role:target", GroundedReference("entity:lamp")),
            RoleBinding("role:dimension", GroundedReference("dim:power")),
            RoleBinding("role:value", GroundedReference("value:on")),
        ),
    )
    expression = SemanticExpression.create(
        applications=(application,),
        root_refs=(application.application_ref,),
    )
    return VerifiedMeaning.create(
        program_ref="program:foundation-effect-currentness",
        expression=expression,
        grounding_refs=("grounding:foundation-effect-currentness",),
        coverage_receipt_ref="coverage:foundation-effect-currentness",
        compilation_proof_ref="compilation:foundation-effect-currentness",
        verification_receipt_ref="verification:foundation-effect-currentness",
        revision_pin=pin,
    )


def _trusted_claim_case(stores, linked_authority, *, turn_ref: str, app_ref: str):
    situation = SituationContext.create(
        orientation_ref=f"orientation:{turn_ref}",
        proposal_context_ref=f"proposal_context:{turn_ref}",
        mode=SemanticMode.OBSERVE,
        session_ref="session:foundation-effect-currentness-admission",
        turn_ref=turn_ref,
        turn_index=1,
        session_phase_ref="active",
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref="participant:user",
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref=f"focus_snapshot:{turn_ref}",
        focus_refs=(),
        obligation_snapshot_ref=f"obligation_snapshot:{turn_ref}",
        obligation_refs=(),
        capability_refs=(),
        permission_snapshot_ref=f"permission_snapshot:{turn_ref}",
        permission_refs=(),
        resource_snapshot_ref=f"resource_snapshot:{turn_ref}",
        resource_refs=(),
        adapter_snapshot_ref=f"adapter_snapshot:{turn_ref}",
        adapter_refs=(),
        evidence_kinds=("operation",),
        evidence_policy_refs=("policy:evidence:foundation-currentness",),
        adapter_receipt_refs=("operation_receipt:foundation-currentness-observation",),
        trusted_observation=True,
        source_refs=(f"evidence:{turn_ref}",),
        epistemic_scope_ref="epistemic_scope:observed",
        revision_pin=stores.revision_pin(),
    )
    application = SemanticApplication(
        app_ref,
        "op:state",
        "dim:power",
        (
            RoleBinding("role:subject", GroundedReference("entity:lamp")),
            RoleBinding("role:dimension", GroundedReference("dim:power")),
            RoleBinding("role:value", GroundedReference("value:on")),
        ),
    )
    expression = SemanticExpression.create(
        applications=(application,), root_refs=(application.application_ref,)
    )
    meaning = VerifiedMeaning.create(
        program_ref=f"program:{app_ref}",
        expression=expression,
        grounding_refs=(f"grounding:{app_ref}",),
        coverage_receipt_ref=f"coverage:{app_ref}",
        compilation_proof_ref=f"compilation:{app_ref}",
        verification_receipt_ref=f"verification:{app_ref}",
        revision_pin=situation.revision_pin,
    )
    evaluation = R3EvaluationOwner(
        linked_authority, stores, RuntimeConfig.release()
    ).evaluate(meaning, situation)
    return situation, meaning, evaluation


class _LampAdapter:
    def __init__(self) -> None:
        self.requests = []
        self.observation = ObservedDelta.create(
            operator_ref="op:state",
            predicate_ref="dim:power",
            role_values=(
                ("role:subject", "entity:lamp"),
                ("role:dimension", "dim:power"),
                ("role:value", "value:on"),
            ),
            stance="support",
            evidence_refs=("sensor:foundation-currentness-lamp-on",),
        )

    def invoke(self, request):
        self.requests.append(request)
        return AdapterResult.create(
            adapter_ref=request.adapter_ref,
            status=AdapterStatus.SUCCEEDED,
            idempotency_key=request.idempotency_key,
            request_ref=request.request_ref,
            event_type_ref=request.event_type_ref,
            target_ref=request.target_ref,
            transition_ref=request.transition_ref,
            observed_deltas=(self.observation,),
            blocker_refs=(),
            operation_receipt_ref="operation_receipt:foundation-currentness-lamp-on",
        )

    def reconcile(self, request):
        raise AssertionError(f"terminal request must not reconcile: {request.request_ref}")


class _PendingLampAdapter(_LampAdapter):
    def invoke(self, request):
        self.requests.append(request)
        return AdapterResult.create(
            adapter_ref=request.adapter_ref,
            status=AdapterStatus.PENDING,
            idempotency_key=request.idempotency_key,
            request_ref=request.request_ref,
            event_type_ref=request.event_type_ref,
            target_ref=request.target_ref,
            transition_ref=request.transition_ref,
            observed_deltas=(),
            blocker_refs=("adapter_pending",),
            operation_receipt_ref=None,
        )


class _RecoveringLampAdapter(_LampAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.reconciliations = []

    def invoke(self, request):
        raise AssertionError(f"pending request must not be invoked twice: {request.request_ref}")

    def reconcile(self, request):
        self.reconciliations.append(request)
        return AdapterResult.create(
            adapter_ref=request.adapter_ref,
            status=AdapterStatus.SUCCEEDED,
            idempotency_key=request.idempotency_key,
            request_ref=request.request_ref,
            event_type_ref=request.event_type_ref,
            target_ref=request.target_ref,
            transition_ref=request.transition_ref,
            observed_deltas=(self.observation,),
            blocker_refs=(),
            operation_receipt_ref="operation_receipt:foundation-currentness-recovered",
        )


def _effect_case(stores, linked_authority, *, turn_ref: str):
    situation = _situation(stores, turn_ref=turn_ref)
    meaning = _meaning(situation.revision_pin)
    evaluation = R3EvaluationOwner(
        linked_authority, stores, RuntimeConfig.release()
    ).evaluate(meaning, situation)
    return situation, meaning, evaluation


def test_r3_effect_gateway_atomically_advances_current_world_and_effect(
    tmp_path, linked_authority
):
    for backend in ("memory", "sqlite"):
        stores = _stores(backend, tmp_path, linked_authority.generation)
        try:
            _seed_lamp_off(stores)
            situation, meaning, evaluation = _effect_case(
                stores, linked_authority, turn_ref=f"turn:atomic:{backend}"
            )
            adapter = _LampAdapter()
            receipt = R3EffectGateway(
                stores, AdapterRegistry({"adapter:state": adapter})
            ).execute(evaluation, meaning, situation)

            assert type(receipt) is EffectReceipt
            assert receipt.status is EffectStatus.COMMITTED
            assert stores.revision_pin() == receipt.output_revision_pin
            assert receipt.output_revision_pin.world_revision == situation.revision_pin.world_revision + 1
            assert receipt.output_revision_pin.session_revision == situation.revision_pin.session_revision + 1
            assert receipt.output_revision_pin.effect_revision > situation.revision_pin.effect_revision
            journal = effect_journal_get(stores, receipt.idempotency_key)
            assert journal is not None and journal.entry.state is EffectJournalState.COMMITTED
            assert journal.entry.effect_revision == receipt.output_revision_pin.effect_revision
            assert journal.entry.outcome_ref == receipt.receipt_ref
            assert stores.r3_session_snapshot(situation.session_ref) == {
                "snapshot_ref": stores.r3_session_snapshot(situation.session_ref)["snapshot_ref"],
                "session_ref": situation.session_ref,
                "session_phase_ref": "active",
                "turn_index": situation.turn_index,
                "session_record_revision": receipt.output_revision_pin.session_revision,
                "store_revision": receipt.output_revision_pin.session_revision,
            }
            assert tuple(
                stores.world.get(fact_ref) for fact_ref in receipt.committed_fact_refs
            ) == tuple(
                fact
                for fact in stores.r3_world_facts()
                if fact.fact_ref in receipt.committed_fact_refs
            )
            assert len(receipt.committed_fact_refs) == 1
            assert len(adapter.requests) == 1
        finally:
            stores.close()


def test_r3_effect_gateway_rejects_stale_new_request_but_replays_exact_receipt(
    tmp_path, linked_authority
):
    for backend in ("memory", "sqlite"):
        stores = _stores(backend, tmp_path, linked_authority.generation)
        try:
            _seed_lamp_off(stores)
            first = _effect_case(
                stores, linked_authority, turn_ref=f"turn:current:first:{backend}"
            )
            stale = _effect_case(
                stores, linked_authority, turn_ref=f"turn:current:stale:{backend}"
            )
            adapter = _LampAdapter()
            gateway = R3EffectGateway(
                stores, AdapterRegistry({"adapter:state": adapter})
            )

            receipt = gateway.execute(first[2], first[1], first[0])
            after_commit = stores.revision_pin()
            assert gateway.execute(first[2], first[1], first[0]) == receipt
            assert stores.revision_pin() == after_commit
            assert len(adapter.requests) == 1

            terminal = effect_journal_get(stores, receipt.idempotency_key)
            assert terminal is not None
            changed_payload = thaw_json(terminal.entry.request_payload)
            changed_payload["turn_ref"] = f"turn:changed-retry:{backend}"
            with pytest.raises(
                ValueError,
                match="idempotency key is already bound to another request",
            ):
                gateway._begin(
                    key=receipt.idempotency_key,
                    intent_ref=terminal.entry.intent_ref,
                    decision_ref=terminal.entry.decision_ref,
                    request_payload=changed_payload,
                    input_revision_pin=first[0].revision_pin,
                )
            assert stores.revision_pin() == after_commit
            assert len(adapter.requests) == 1

            with pytest.raises(StaleRevisionError, match="effect.*revision pin is stale"):
                gateway.execute(stale[2], stale[1], stale[0])
            assert stores.revision_pin() == after_commit
            assert len(adapter.requests) == 1
            stale_intent = stale[2].effect_intents[0]
            stale_key = R3EffectGateway._effect_key(
                stale[2].decision.decision_ref,
                stale_intent.effect_intent_ref,
                "external",
            )
            assert effect_journal_get(stores, stale_key) is None

            if backend == "sqlite":
                concurrent_pin = stores.revision_pin()
                concurrent_key = "key:foundation-currentness-concurrent-sqlite"
                peer = open_stores(
                    tmp_path / backend,
                    authority_generation=linked_authority.generation,
                    model_identity=MODEL_IDENTITY,
                )
                try:
                    install_reviewed_world_facts(
                        peer,
                        facts=(
                            Fact(
                                fact_ref="fact:foundation-currentness-peer-progress",
                                operator="op:relation",
                                args={
                                    "predicate_ref": "rel:likes",
                                    "role:subject": "entity:alice",
                                    "role:object": "entity:bob",
                                },
                                proof={"source": "review:peer-progress"},
                            ),
                        ),
                    )
                finally:
                    peer.close()
                with pytest.raises(
                    StaleRevisionError,
                    match="effect request (revision pin is stale|world_revision changed concurrently)",
                ):
                    gateway._begin(
                        key=concurrent_key,
                        intent_ref="intent:foundation-currentness-concurrent-sqlite",
                        decision_ref="decision:foundation-currentness-concurrent-sqlite",
                        request_payload={"kind": "external"},
                        input_revision_pin=concurrent_pin,
                    )
                assert len(adapter.requests) == 1
                assert effect_journal_get(stores, concurrent_key) is None
        finally:
            stores.close()


def test_r3_effect_gateway_persists_exact_proof_and_journal_history(
    tmp_path, linked_authority
):
    path = tmp_path / "proof-restart"
    stores = _stores("proof-restart", tmp_path, linked_authority.generation)
    try:
        _seed_lamp_off(stores)
        situation, meaning, evaluation = _effect_case(
            stores, linked_authority, turn_ref="turn:proof-restart"
        )
        adapter = _LampAdapter()
        receipt = R3EffectGateway(
            stores, AdapterRegistry({"adapter:state": adapter})
        ).execute(evaluation, meaning, situation)
        fact = stores.world.get(receipt.committed_fact_refs[0])
        journal = effect_journal_get(stores, receipt.idempotency_key)
        pin = stores.revision_pin()

        assert fact is not None
        assert dict(fact.proof) == {
            "source": receipt.operation_receipt_ref,
            "decision_ref": receipt.decision_ref,
            "evidence_refs": ["sensor:foundation-currentness-lamp-on"],
        }
        assert receipt.proof_refs == evaluation.decision.proof_refs
        assert receipt.transition_ref == "transition:set_power_on"
        assert journal is not None
        assert journal.entry.state is EffectJournalState.COMMITTED
        assert journal.entry.outcome_ref == receipt.receipt_ref
        assert journal.entry.parent_journal_ref == receipt.journal_preterminal_ref
        assert journal.entry.decision_ref == receipt.decision_ref
        assert thaw_json(journal.receipt_payload) == receipt.as_dict()
    finally:
        stores.close()

    reopened = open_stores(
        path,
        authority_generation=linked_authority.generation,
        model_identity=MODEL_IDENTITY,
    )
    try:
        assert reopened.revision_pin() == pin
        assert reopened.world.get(fact.fact_ref) == fact
        assert effect_journal_get(reopened, receipt.idempotency_key) == journal
    finally:
        reopened.close()


def test_r3_effect_gateway_rejects_stale_new_trusted_admission(
    tmp_path, linked_authority
):
    for backend in ("memory", "sqlite-admission"):
        stores = _stores(backend, tmp_path, linked_authority.generation)
        try:
            first = _trusted_claim_case(
                stores,
                linked_authority,
                turn_ref=f"turn:admission:first:{backend}",
                app_ref=f"application:admission:first:{backend}",
            )
            stale = _trusted_claim_case(
                stores,
                linked_authority,
                turn_ref=f"turn:admission:stale:{backend}",
                app_ref=f"application:admission:stale:{backend}",
            )
            gateway = R3EffectGateway(stores, AdapterRegistry())
            committed = gateway.execute(first[2], first[1], first[0])
            pin = stores.revision_pin()
            facts = stores.r3_world_facts()
            assert committed.status is EffectStatus.COMMITTED

            with pytest.raises(StaleRevisionError, match="effect.*revision pin is stale"):
                gateway.execute(stale[2], stale[1], stale[0])
            assert stores.revision_pin() == pin
            assert stores.r3_world_facts() == facts
            stale_key = R3EffectGateway._effect_key(
                stale[2].decision.decision_ref,
                None,
                "trusted_semantic_admission",
            )
            assert effect_journal_get(stores, stale_key) is None
        finally:
            stores.close()


def test_r3_effect_gateway_recovers_exact_pending_request_after_restart(
    tmp_path, linked_authority
):
    path = tmp_path / "pending-restart"
    stores = _stores("pending-restart", tmp_path, linked_authority.generation)
    pending_adapter = _PendingLampAdapter()
    try:
        _seed_lamp_off(stores)
        situation, meaning, evaluation = _effect_case(
            stores, linked_authority, turn_ref="turn:pending-restart"
        )
        pending = R3EffectGateway(
            stores, AdapterRegistry({"adapter:state": pending_adapter})
        ).execute(evaluation, meaning, situation)
        journal = effect_journal_get(stores, pending.idempotency_key)
        assert pending.status is EffectStatus.PENDING
        assert journal is not None
        assert journal.entry.state is EffectJournalState.PENDING_RECONCILIATION
        assert len(pending_adapter.requests) == 1
        assert stores.world.get("fact:foundation-currentness-lamp-off") is not None
    finally:
        stores.close()

    reopened = open_stores(
        path,
        authority_generation=linked_authority.generation,
        model_identity=MODEL_IDENTITY,
    )
    recovering_adapter = _RecoveringLampAdapter()
    try:
        gateway = R3EffectGateway(
            reopened, AdapterRegistry({"adapter:state": recovering_adapter})
        )
        committed = gateway.execute(evaluation, meaning, situation)
        assert committed.status is EffectStatus.COMMITTED
        assert len(recovering_adapter.requests) == 0
        assert len(recovering_adapter.reconciliations) == 1
        assert len(committed.committed_fact_refs) == 1
        assert reopened.world.get(committed.committed_fact_refs[0]) is not None
        journal = effect_journal_get(reopened, committed.idempotency_key)
        assert journal is not None and journal.entry.state is EffectJournalState.COMMITTED
        pin = reopened.revision_pin()
        assert gateway.execute(evaluation, meaning, situation) == committed
        assert reopened.revision_pin() == pin
        assert len(recovering_adapter.reconciliations) == 1
    finally:
        reopened.close()


def test_transition_preview_owner_exposes_no_direct_world_commit():
    assert "commit" not in TransitionEngine.__dict__
