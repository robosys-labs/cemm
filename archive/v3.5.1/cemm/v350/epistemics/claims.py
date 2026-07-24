"""Compile structurally complete claim semantics into attributed claim records."""
from __future__ import annotations

from ..schema.model import EventSchema, PortFillerClass, StorageKind, UseOperation, semantic_fingerprint
from ..storage import ClaimHistoryAction, ClaimHistoryRecord, ClaimRecord, SemanticStore
from ..uol.model import ClaimForce, ClaimOccurrence, FillerRef, UOLGraph
from .model import CompiledClaim


class ClaimCompilationError(ValueError):
    pass


class ClaimOccurrenceCompiler:
    """Compile claims from UOL structure, never from words or predicate names."""

    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def compile(
        self,
        graph: UOLGraph,
        application_ref: str,
        *,
        claim_force: ClaimForce,
        commitment_strength: float,
        evidence_refs: tuple[str, ...],
        snapshot=None,
    ) -> CompiledClaim:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.compile(
                    graph, application_ref, claim_force=claim_force,
                    commitment_strength=commitment_strength,
                    evidence_refs=evidence_refs, snapshot=pinned,
                )
        self.store.assert_snapshot(snapshot)
        application = graph.applications.get(application_ref)
        if application is None:
            raise ClaimCompilationError("claim application is absent from the selected UOL graph")
        schema = self.store.repositories.schemas.registry(snapshot=snapshot).schema(
            application.schema_ref, application.schema_revision
        )
        if not isinstance(schema, EventSchema):
            raise ClaimCompilationError("claim classification requires an exact EventSchema revision")
        if application.use_operation != UseOperation.COMPOSE or not schema.use_profile.permits(UseOperation.COMPOSE):
            raise ClaimCompilationError("claim classification requires compose-authorized event semantics")
        proposition_ports = tuple(
            port for port in schema.local_ports
            if StorageKind.PROPOSITION in port.accepted_storage_kinds
            and PortFillerClass.REFERENT in port.filler_classes
        )
        source_ports = tuple(
            port for port in schema.local_ports
            if port.identity_contribution
            and PortFillerClass.REFERENT in port.filler_classes
            and port.cardinality.minimum > 0
        )
        if len(proposition_ports) != 1 or len(source_ports) != 1:
            raise ClaimCompilationError("claim schema must expose one proposition port and one required identity-contributing source port")
        proposition_port = proposition_ports[0]
        source_port = source_ports[0]
        audience_ports = tuple(
            port for port in schema.local_ports
            if port.port_ref not in {proposition_port.port_ref, source_port.port_ref}
            and PortFillerClass.REFERENT in port.filler_classes
        )
        bindings = {item.port_ref: item for item in application.bindings}
        proposition_ref = _one_concrete_referent(bindings.get(proposition_port.port_ref))
        claimant_ref = _one_concrete_referent(bindings.get(source_port.port_ref))
        if proposition_ref is None or claimant_ref is None:
            raise ClaimCompilationError("claim proposition/source is still an open semantic frontier")
        proposition = graph.propositions.get(proposition_ref)
        if proposition is None:
            raise ClaimCompilationError("claim content must reference an explicit PropositionReferent")
        audiences = []
        for port in audience_ports:
            binding = bindings.get(port.port_ref)
            if binding is None:
                continue
            for filler in binding.fillers:
                if isinstance(filler, FillerRef) and filler.filler_class == PortFillerClass.REFERENT:
                    audiences.append(filler.ref)
        event = next(
            (
                item for item in graph.events.values()
                if item.participant_application_ref == application.application_ref
                and item.event_schema_ref == application.schema_ref
                and item.event_schema_revision == application.schema_revision
            ),
            None,
        )
        if event is None:
            raise ClaimCompilationError("claim classification requires the corresponding introduced event occurrence")
        if event.context_ref != application.context_ref:
            raise ClaimCompilationError("claim event/application context mismatch")
        source_context_ref = application.context_ref
        reported_context_ref = proposition.context_ref
        if source_context_ref == reported_context_ref:
            raise ClaimCompilationError("claim content must remain in a distinct attributed context")
        claim = ClaimOccurrence(
            referent=event.referent,
            claimant_ref=claimant_ref,
            audience_refs=tuple(sorted(set(audiences))),
            proposition_ref=proposition_ref,
            claim_force=claim_force,
            source_context_ref=source_context_ref,
            reported_context_ref=reported_context_ref,
            time_ref=event.time_ref,
            evidence_refs=tuple(sorted(set(evidence_refs))),
        )
        claim_record_ref = "claim-record:" + semantic_fingerprint(
            "claim-record-ref", (claim.claim_ref, proposition_ref, claimant_ref, reported_context_ref), 32
        )
        record = ClaimRecord(
            claim_record_ref=claim_record_ref,
            claim_occurrence_ref=claim.claim_ref,
            proposition_ref=proposition_ref,
            source_ref=claimant_ref,
            source_context_ref=source_context_ref,
            reported_context_ref=reported_context_ref,
            commitment_strength=commitment_strength,
            permission_ref=claim.referent.permission_ref,
            evidence_refs=tuple(sorted(set(evidence_refs))),
        )
        history = ClaimHistoryRecord(
            history_ref="claim-history:" + semantic_fingerprint("claim-history-ref", (claim_record_ref, "assert"), 32),
            claim_record_ref=claim_record_ref,
            action=ClaimHistoryAction.ASSERT,
            source_ref=claimant_ref,
            context_ref=source_context_ref,
            evidence_refs=tuple(sorted(set(evidence_refs))),
            metadata={"claim_force": claim_force.value},
        )
        return CompiledClaim(claim, record, history, tuple(sorted(set(evidence_refs))))


def _one_concrete_referent(binding):
    if binding is None or len(binding.fillers) != 1 or binding.open_binding_purpose is not None:
        return None
    filler = binding.fillers[0]
    if not isinstance(filler, FillerRef) or filler.filler_class != PortFillerClass.REFERENT:
        return None
    return filler.ref
