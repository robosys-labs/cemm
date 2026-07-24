"""Build reviewable GraphPatch proposals for provisional grounded referents."""
from __future__ import annotations

from ..schema.model import semantic_fingerprint
from ..storage import (
    EvidenceRecord,
    GraphPatch,
    IdentityFacetRecord,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SemanticStore,
    encode_record,
)
from ..uol.model import IdentityStatus, Referent
from .model import MentionHypothesis, ProvisionalReferentProposal


class ProvisionalReferentPlanner:
    def propose(
        self,
        mention: MentionHypothesis,
        *,
        referent_ref: str,
        type_refs: tuple[str, ...],
        storage_kind,
        confidence: float = 0.5,
    ) -> ProvisionalReferentProposal:
        evidence = mention.evidence_refs or (
            f"source-span:{mention.source_ref}:{mention.span.start}:{mention.span.end}",
        )
        return ProvisionalReferentProposal(
            proposal_ref="provisional-proposal:" + semantic_fingerprint(
                "provisional-proposal-ref",
                (mention.mention_ref, referent_ref, type_refs, storage_kind.value),
                24,
            ),
            mention_ref=mention.mention_ref,
            referent_ref=referent_ref,
            storage_kind=storage_kind,
            type_refs=type_refs,
            identity_value=mention.normalized_surface,
            context_ref=mention.context_ref,
            evidence_refs=evidence,
            confidence=confidence,
            reasons=(
                "no sufficiently decisive existing identity",
                "surface evidence is retained as a provisional identity facet",
            ),
        )

    def graph_patch(
        self,
        proposal: ProvisionalReferentProposal,
        *,
        source_ref: str,
        permission_ref: str = "conversation",
        expected_store_revision: int | None = None,
        store: SemanticStore,
        snapshot=None,
    ) -> GraphPatch:
        evidence_ref = "evidence:grounding:" + semantic_fingerprint(
            "grounding-evidence-ref", (proposal.proposal_ref, proposal.evidence_refs), 24
        )
        identity_ref = "identity-facet:grounding:" + semantic_fingerprint(
            "grounding-identity-ref", (proposal.referent_ref, proposal.identity_value), 24
        )
        evidence = EvidenceRecord(
            evidence_ref=evidence_ref,
            source_ref=source_ref,
            confidence=proposal.confidence,
            lineage_ref=proposal.proposal_ref,
            context_ref=proposal.context_ref,
            permission_ref=permission_ref,
            metadata={
                "phase": 8,
                "proposal_only": True,
                "source_evidence_refs": proposal.evidence_refs,
            },
        )
        referent = Referent(
            referent_ref=proposal.referent_ref,
            storage_kind=proposal.storage_kind,
            identity_status=IdentityStatus.PROVISIONAL,
            type_refs=proposal.type_refs,
            identity_facet_refs=(identity_ref,),
            context_refs=(proposal.context_ref,),
            provenance_refs=(evidence_ref,),
            permission_ref=permission_ref,
            metadata={"grounding_proposal_ref": proposal.proposal_ref},
        )
        registry = store.repositories.schemas.registry(snapshot=snapshot)
        identity_facets = tuple(
            schema for schema in registry.active_schemas()
            if getattr(schema, "facet_family", None) == "identity"
        )
        if len(identity_facets) != 1:
            raise ValueError("provisional identity requires exactly one active identity facet authority")
        identity = IdentityFacetRecord(
            identity_facet_ref=identity_ref,
            referent_ref=proposal.referent_ref,
            facet_schema_ref=identity_facets[0].schema_ref,
            normalized_value=proposal.identity_value,
            confidence=proposal.confidence,
            evidence_refs=(evidence_ref,),
            context_ref=proposal.context_ref,
        )
        operations = (
            PatchOperation(
                operation_ref=f"{proposal.proposal_ref}:evidence",
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.EVIDENCE,
                target_ref=evidence.evidence_ref,
                payload=encode_record(RecordKind.EVIDENCE, evidence),
                reason="retain grounding evidence",
            ),
            PatchOperation(
                operation_ref=f"{proposal.proposal_ref}:referent",
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.REFERENT,
                target_ref=referent.referent_ref,
                payload=encode_record(RecordKind.REFERENT, referent),
                reason="create provisional identity only after review",
            ),
            PatchOperation(
                operation_ref=f"{proposal.proposal_ref}:identity",
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.IDENTITY_FACET,
                target_ref=identity.identity_facet_ref,
                payload=encode_record(RecordKind.IDENTITY_FACET, identity),
                reason="attach reversible normalized identity evidence",
            ),
        )
        return GraphPatch(
            patch_ref="patch:" + proposal.proposal_ref,
            context_ref=proposal.context_ref,
            scope_ref="grounding",
            source_ref=source_ref,
            permission_ref=permission_ref,
            operations=operations,
            expected_store_revision=expected_store_revision,
            evidence_refs=(evidence_ref,),
            validation_requirements=(
                "review_provisional_identity",
                "no_claim_admission",
                "no_automatic_merge",
            ),
            rollback_hint="tombstone provisional referent and identity facet",
            metadata={"phase": 8, "proposal_ref": proposal.proposal_ref},
        )
