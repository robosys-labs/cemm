from __future__ import annotations

import hashlib
import pytest

from cemm.v350.learning.model import PinnedRecord
from cemm.v350.output.model import (
    ChannelAdapterContractRecord,
    EmissionAnomalyRecord,
    EmissionAuthorizationDecision,
    EmissionAuthorizationRecord,
    EmissionIdempotencyMode,
    EmissionJournalRecord,
    EmissionJournalStatus,
)
from cemm.v350.output.validation import Phase18CommitValidator
from cemm.v350.storage.codec import encode_record, record_fingerprints
from cemm.v350.storage.model import PatchOperation, PatchOperationKind, RecordDependency, RecordKind


def _pin(kind: RecordKind, ref: str) -> PinnedRecord:
    return PinnedRecord(kind, ref, 1, "f" * 64)


def _authorization(**overrides):
    data = dict(
        authorization_ref="emission-auth:test",
        response_uol_pin=_pin(RecordKind.RESPONSE_UOL, "response:test"),
        realization_request_pin=_pin(RecordKind.REALIZATION_REQUEST, "request:test"),
        surface_candidate_pin=_pin(RecordKind.SURFACE_CANDIDATE, "surface:test"),
        semantic_roundtrip_pin=_pin(RecordKind.SEMANTIC_ROUNDTRIP, "roundtrip:test"),
        goal_decision_pin=_pin(RecordKind.GOAL_DECISION, "goal-decision:test"),
        channel_contract_pin=_pin(RecordKind.CHANNEL_ADAPTER_CONTRACT, "channel-contract:test"),
        gate_assessment_pins=(_pin(RecordKind.EMISSION_GATE_ASSESSMENT, "gate:test"),),
        decision=EmissionAuthorizationDecision.ALLOW,
        audience_refs=("ref:user",),
        surface_sha256=hashlib.sha256(b"hello").hexdigest(),
        passed_gates=("roundtrip_passed",),
        failed_gates=(),
        snapshot_revision=3,
        snapshot_fingerprint="snapshot:test",
    )
    data.update(overrides)
    return EmissionAuthorizationRecord(**data)


def test_allow_emission_cannot_hide_failed_gate():
    with pytest.raises(ValueError):
        _authorization(failed_gates=("policy_safety",))


def test_non_allow_emission_requires_explicit_failed_gate():
    with pytest.raises(ValueError):
        _authorization(decision=EmissionAuthorizationDecision.DENY, failed_gates=())


def test_unknown_delivery_retry_requires_idempotency():
    with pytest.raises(ValueError):
        ChannelAdapterContractRecord(
            contract_ref="channel-contract:test",
            channel_ref="channel:test",
            adapter_ref="adapter:test",
            adapter_revision=1,
            max_payload_bytes=1024,
            idempotency_mode=EmissionIdempotencyMode.NONE,
            retry_safe_on_unknown=True,
        )


def test_channel_side_mutation_is_a_non_discourse_anomaly_contract():
    anomaly = EmissionAnomalyRecord(
        anomaly_ref="emission-anomaly:test",
        anomaly_kind_ref="channel_surface_mutation_requires_reverification",
        journal_pin=_pin(RecordKind.EMISSION_JOURNAL, "journal:test"),
        authorization_pin=_pin(RecordKind.EMISSION_AUTHORIZATION, "emission-auth:test"),
        channel_contract_pin=_pin(RecordKind.CHANNEL_ADAPTER_CONTRACT, "channel-contract:test"),
        authorized_surface_sha256=hashlib.sha256(b"hello").hexdigest(),
        observed_surface_sha256=hashlib.sha256(b"mutated").hexdigest(),
        content_left_system=True,
        evidence_refs=("evidence:transport",),
        reason_refs=("surface_mutated",),
        channel_ref="channel:test",
    )
    assert anomaly.no_output_discourse_authority is True


def test_content_left_system_anomaly_requires_evidence_or_proof():
    with pytest.raises(ValueError):
        EmissionAnomalyRecord(
            anomaly_ref="emission-anomaly:bad",
            anomaly_kind_ref="surface_mutation",
            journal_pin=_pin(RecordKind.EMISSION_JOURNAL, "journal:test"),
            authorization_pin=_pin(RecordKind.EMISSION_AUTHORIZATION, "emission-auth:test"),
            channel_contract_pin=_pin(RecordKind.CHANNEL_ADAPTER_CONTRACT, "channel-contract:test"),
            authorized_surface_sha256="a" * 64,
            observed_surface_sha256="b" * 64,
            content_left_system=True,
            evidence_refs=(),
            channel_ref="channel:test",
        )


def test_allowed_emission_requires_explicit_audience():
    with pytest.raises(ValueError):
        _authorization(audience_refs=())


def test_channel_delivery_observation_rejects_contradictory_flags():
    from cemm.v350.output.executor import ChannelObservation
    with pytest.raises(ValueError):
        ChannelObservation(
            accepted=True,
            delivered=True,
            delivery_known=False,
            content_left_system=True,
            evidence_refs=("evidence:transport",),
        )


def test_channel_contract_does_not_assume_delivery_proves_recipient_receipt():
    contract = ChannelAdapterContractRecord(
        contract_ref="channel-contract:receipt-safe",
        channel_ref="channel:test",
        adapter_ref="adapter:test",
        adapter_revision=1,
        max_payload_bytes=1024,
    )
    assert contract.delivery_ack_proves_recipient_receipt is False


def test_journal_transition_requires_exact_authorization_dependency():
    auth_pin = _pin(RecordKind.EMISSION_AUTHORIZATION, "emission-auth:test")
    prior = EmissionJournalRecord(
        journal_ref="emission-journal:test",
        authorization_pin=auth_pin,
        status=EmissionJournalStatus.PREPARED,
        idempotency_key=None,
        adapter_ref="adapter:test",
        adapter_revision=1,
        surface_sha256="a" * 64,
    )
    prior_fp = record_fingerprints(RecordKind.EMISSION_JOURNAL, prior)[1]
    prior_pin = PinnedRecord(RecordKind.EMISSION_JOURNAL, prior.journal_ref, 1, prior_fp)
    transition = EmissionJournalRecord(
        journal_ref=prior.journal_ref,
        authorization_pin=auth_pin,
        status=EmissionJournalStatus.SUBMITTED,
        idempotency_key=None,
        adapter_ref="adapter:test",
        adapter_revision=1,
        surface_sha256="a" * 64,
        prior_journal_pin=prior_pin,
        revision=2,
        supersedes_revision=1,
    )
    op = PatchOperation(
        operation_ref="patch-operation:test",
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=RecordKind.EMISSION_JOURNAL,
        target_ref=transition.journal_ref,
        record_revision=2,
        payload=encode_record(RecordKind.EMISSION_JOURNAL, transition),
        dependencies=(
            RecordDependency(RecordKind.EMISSION_JOURNAL, prior.journal_ref, 1, prior_fp, "emission_journal_prior"),
        ),
    )

    class Resolver:
        def resolve(self, kind, ref, revision=None):
            class Stored:
                payload = prior

            if kind == RecordKind.EMISSION_JOURNAL and ref == prior.journal_ref and revision == 1:
                return Stored()
            return None

    with pytest.raises(ValueError, match="emission_authorization"):
        Phase18CommitValidator(Resolver()).validate_operation(op, transition)
