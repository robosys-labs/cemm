"""Mechanical Phase-18 channel execution with crash-safe journal recovery."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Protocol, Any

from ..realization.model import SurfaceCandidateRecord
from ..schema.model import semantic_fingerprint
from ..storage.model import RecordKind
from .coordinator import EmissionJournalCoordinator
from .gate import surface_sha256
from .model import (
    ChannelAdapterContractRecord, EmissionAuthorizationDecision, EmissionAuthorizationRecord,
    EmissionAnomalyRecord, EmissionJournalRecord, EmissionJournalStatus, EmissionRecord, EmissionStatus,
)


@dataclass(frozen=True,slots=True)
class ChannelObservation:
    accepted: bool
    delivered: bool
    delivery_known: bool
    content_left_system: bool
    evidence_refs: tuple[str,...]
    proof_refs: tuple[str,...]=()
    external_correlation_refs: tuple[str,...]=()
    emitted_bytes_ref: str|None=None
    emitted_at: str|None=None
    observed_surface_sha256: str|None=None
    request_evidence_refs: tuple[str,...]=()
    metadata: Mapping[str,Any]|None=None
    def __post_init__(self):
        if self.delivered and (not self.delivery_known or not self.accepted):
            raise ValueError("delivered channel observation requires accepted and delivery_known")
        if self.observed_surface_sha256 is not None and (len(self.observed_surface_sha256)!=64 or any(ch not in "0123456789abcdefABCDEF" for ch in self.observed_surface_sha256)):
            raise ValueError("observed surface sha256 must be 64 hex characters")
        if len(self.evidence_refs)!=len(set(self.evidence_refs)) or len(self.proof_refs)!=len(set(self.proof_refs)):
            raise ValueError("channel observation evidence/proof refs must be unique")


class ChannelEmissionAdapter(Protocol):
    adapter_ref: str
    adapter_revision: int
    def submit(self,*,surface:str,audience_refs:tuple[str,...],idempotency_key:str|None,context:Mapping[str,Any]) -> ChannelObservation: ...
    def recover(self,*,external_correlation_refs:tuple[str,...],idempotency_key:str|None,context:Mapping[str,Any]) -> ChannelObservation: ...


class ChannelExecutionCoordinator:
    def __init__(self,store): self.store=store; self.journals=EmissionJournalCoordinator(store)

    def execute(self,*,journal:EmissionJournalRecord,authorization:EmissionAuthorizationRecord,candidate:SurfaceCandidateRecord,contract:ChannelAdapterContractRecord,adapter:ChannelEmissionAdapter):
        self._preflight(journal,authorization,candidate,contract,adapter)
        submitted=self.journals.advance(journal,EmissionJournalStatus.SUBMITTED,submitted_at=None)
        try:
            observation=adapter.submit(surface=candidate.surface,audience_refs=authorization.audience_refs,idempotency_key=journal.idempotency_key,context={"authorization_ref":authorization.authorization_ref,"channel_ref":contract.channel_ref})
        except Exception as exc:
            # The call may have crossed the process boundary; never infer failure/success.
            unknown=self.journals.advance(submitted,EmissionJournalStatus.DELIVERY_UNKNOWN)
            return unknown,None
        return self._observe(submitted,authorization,candidate,contract,observation)

    def recover(self,*,journal:EmissionJournalRecord,authorization:EmissionAuthorizationRecord,candidate:SurfaceCandidateRecord,contract:ChannelAdapterContractRecord,adapter:ChannelEmissionAdapter):
        if journal.status not in {EmissionJournalStatus.SUBMITTED,EmissionJournalStatus.CHANNEL_ACKNOWLEDGED,EmissionJournalStatus.DELIVERY_UNKNOWN}:
            raise ValueError("recovery is valid only for submitted/acknowledged/unknown journal states")
        if not contract.supports_recovery_query:
            raise ValueError("reviewed channel contract does not authorize a recovery query; preserve uncertainty without resubmitting")
        self._preflight(journal,authorization,candidate,contract,adapter,allow_nonprepared=True)
        observation=adapter.recover(external_correlation_refs=journal.external_correlation_refs,idempotency_key=journal.idempotency_key,context={"authorization_ref":authorization.authorization_ref,"channel_ref":contract.channel_ref})
        return self._observe(journal,authorization,candidate,contract,observation)

    def _observe(self,journal,authorization,candidate,contract,observation):
        if not observation.accepted:
            if observation.content_left_system:
                anomaly=self._anomaly(journal,authorization,contract,observation,"channel_rejected_but_content_left_system",observation.observed_surface_sha256)
                return self.journals.persist_anomaly(journal,anomaly,EmissionJournalStatus.DELIVERY_UNKNOWN),None
            status=EmissionJournalStatus.FAILED_AFTER_SUBMIT if observation.delivery_known else EmissionJournalStatus.DELIVERY_UNKNOWN
            return self.journals.advance(journal,status,response_evidence_refs=observation.evidence_refs,external_correlation_refs=observation.external_correlation_refs,observed_at=observation.emitted_at),None
        observed_hash=observation.observed_surface_sha256 or surface_sha256(candidate.surface)
        if observed_hash!=authorization.surface_sha256:
            # If bytes/content already left the system, preserve an immutable incident instead of pretending nothing was emitted.
            if observation.content_left_system:
                anomaly=self._anomaly(journal,authorization,contract,observation,"channel_surface_mutation_requires_reverification",observed_hash)
                return self.journals.persist_anomaly(journal,anomaly,EmissionJournalStatus.DELIVERY_UNKNOWN),None
            return self.journals.advance(journal,EmissionJournalStatus.DELIVERY_UNKNOWN,response_evidence_refs=(*observation.evidence_refs,"channel_surface_mutation_requires_reverification"),external_correlation_refs=observation.external_correlation_refs,observed_at=observation.emitted_at),None
        if not observation.content_left_system:
            status=EmissionJournalStatus.FAILED_AFTER_SUBMIT if observation.delivery_known else EmissionJournalStatus.DELIVERY_UNKNOWN
            return self.journals.advance(journal,status,response_evidence_refs=observation.evidence_refs,external_correlation_refs=observation.external_correlation_refs,observed_at=observation.emitted_at),None
        if not observation.evidence_refs and not observation.proof_refs:
            raise ValueError("channel observation requires evidence/proof")
        if observation.delivered:
            estatus=EmissionStatus.DELIVERED; jstatus=EmissionJournalStatus.DELIVERY_CONFIRMED
        elif observation.delivery_known:
            estatus=EmissionStatus.CHANNEL_ACCEPTED; jstatus=EmissionJournalStatus.CHANNEL_ACKNOWLEDGED
        else:
            estatus=EmissionStatus.UNKNOWN_DELIVERY; jstatus=EmissionJournalStatus.DELIVERY_UNKNOWN
        from .gate import pin
        emission=EmissionRecord(
            emission_ref="emission:"+semantic_fingerprint("emission-observation",(authorization.authorization_ref,journal.journal_ref,observation.external_correlation_refs,estatus.value),24),
            journal_pin=pin(RecordKind.EMISSION_JOURNAL,journal),authorization_pin=pin(RecordKind.EMISSION_AUTHORIZATION,authorization),
            response_uol_pin=authorization.response_uol_pin,surface_candidate_pin=authorization.surface_candidate_pin,status=estatus,
            surface_sha256=authorization.surface_sha256,audience_refs=authorization.audience_refs,evidence_refs=observation.evidence_refs,proof_refs=observation.proof_refs,
            channel_ref=contract.channel_ref,external_correlation_refs=observation.external_correlation_refs,emitted_bytes_ref=observation.emitted_bytes_ref,
            emitted_at=observation.emitted_at,context_ref=authorization.context_ref,permission_ref=authorization.permission_ref,sensitivity=authorization.sensitivity)
        nxt=self.journals.persist_observation(journal,emission,jstatus)
        return nxt,emission

    def _anomaly(self,journal,authorization,contract,observation,kind_ref,observed_hash):
        from .gate import pin
        evidence=tuple(sorted(set((*observation.evidence_refs,f"phase18_anomaly:{kind_ref}"))))
        return EmissionAnomalyRecord(
            anomaly_ref="emission-anomaly:"+semantic_fingerprint("emission-anomaly",(authorization.authorization_ref,journal.journal_ref,kind_ref,observed_hash,observation.external_correlation_refs),24),
            anomaly_kind_ref=kind_ref,journal_pin=pin(RecordKind.EMISSION_JOURNAL,journal),authorization_pin=pin(RecordKind.EMISSION_AUTHORIZATION,authorization),channel_contract_pin=authorization.channel_contract_pin,
            authorized_surface_sha256=authorization.surface_sha256,observed_surface_sha256=observed_hash,content_left_system=observation.content_left_system,evidence_refs=evidence,proof_refs=observation.proof_refs,
            reason_refs=(kind_ref,),external_correlation_refs=observation.external_correlation_refs,channel_ref=contract.channel_ref,detected_at=observation.emitted_at,context_ref=authorization.context_ref,permission_ref=authorization.permission_ref,sensitivity=authorization.sensitivity)

    def _preflight(self,journal,authorization,candidate,contract,adapter,allow_nonprepared=False):
        if authorization.decision!=EmissionAuthorizationDecision.ALLOW: raise ValueError("channel execution requires ALLOW authorization")
        if not allow_nonprepared and journal.status!=EmissionJournalStatus.PREPARED: raise ValueError("fresh channel execution requires PREPARED journal")
        if journal.authorization_pin.record_ref!=authorization.authorization_ref: raise ValueError("journal authorization mismatch")
        if surface_sha256(candidate.surface)!=authorization.surface_sha256 or journal.surface_sha256!=authorization.surface_sha256: raise ValueError("surface changed after authorization")
        if adapter.adapter_ref!=contract.adapter_ref or adapter.adapter_revision!=contract.adapter_revision: raise ValueError("adapter implementation identity differs from reviewed contract")
        if journal.adapter_ref!=contract.adapter_ref or journal.adapter_revision!=contract.adapter_revision: raise ValueError("journal adapter identity mismatch")
