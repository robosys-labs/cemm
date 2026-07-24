"""Stage-9 attributed-claim preservation and epistemic placement helpers.

This module deliberately does not infer actual-world truth from grammar. It turns
explicit ClaimOccurrence UOL into durable-attribution lineage candidates and leaves
actual-world admission to EpistemicAdmissionEngine plus explicit policy/source/
authorization inputs.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema.model import semantic_fingerprint
from .storage import ClaimHistoryAction, ClaimHistoryRecord, ClaimRecord
from .uol.model import ClaimForce, ClaimOccurrence, UOLGraph


@dataclass(frozen=True, slots=True)
class AttributedClaimLineage:
    occurrence: ClaimOccurrence
    claim_record: ClaimRecord
    history_record: ClaimHistoryRecord


@dataclass(frozen=True, slots=True)
class EpistemicPlacementResult:
    attributed_claims: tuple[AttributedClaimLineage, ...]
    actual_world_admission: bool
    unresolved_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


class AttributedClaimCompiler:
    """Compile exact claim occurrences into append-only attributed lineage."""

    def compile_graph(self, graph: UOLGraph, *, durable_evidence_ref: str) -> EpistemicPlacementResult:
        compiled: list[AttributedClaimLineage] = []
        unresolved: list[str] = []
        evidence = set(graph.evidence_refs)
        evidence.add(durable_evidence_ref)
        for claim in sorted(graph.claims.values(), key=lambda item: item.claim_ref):
            if claim.claim_force in {ClaimForce.CORRECTED, ClaimForce.RETRACTED}:
                # Correction/retraction requires an explicit target claim lineage.
                # Never guess the target from recency or surface similarity.
                unresolved.append(f"claim-history-target:{claim.claim_ref}")
                continue
            try:
                commitment_strength = _commitment_strength(claim)
            except ValueError:
                unresolved.append(f"claim-commitment-evidence:{claim.claim_ref}")
                continue
            record_ref = "claim-record:" + semantic_fingerprint(
                "claim-record-ref",
                (claim.claim_ref, claim.proposition_ref, claim.claimant_ref, claim.reported_context_ref),
                32,
            )
            record = ClaimRecord(
                claim_record_ref=record_ref,
                claim_occurrence_ref=claim.claim_ref,
                proposition_ref=claim.proposition_ref,
                source_ref=claim.claimant_ref,
                source_context_ref=claim.source_context_ref,
                reported_context_ref=claim.reported_context_ref,
                commitment_strength=commitment_strength,
                permission_ref=claim.referent.permission_ref,
                evidence_refs=(durable_evidence_ref,),
            )
            history = ClaimHistoryRecord(
                history_ref="claim-history:" + semantic_fingerprint(
                    "claim-history-ref", (record_ref, ClaimHistoryAction.ASSERT.value), 32
                ),
                claim_record_ref=record_ref,
                action=ClaimHistoryAction.ASSERT,
                source_ref=claim.claimant_ref,
                context_ref=claim.source_context_ref,
                evidence_refs=(durable_evidence_ref,),
                metadata={"claim_force": claim.claim_force.value},
            )
            compiled.append(AttributedClaimLineage(claim, record, history))
        return EpistemicPlacementResult(
            attributed_claims=tuple(compiled),
            actual_world_admission=False,
            unresolved_refs=tuple(sorted(set(unresolved))),
            evidence_refs=tuple(sorted(evidence)),
        )


def _commitment_strength(claim: ClaimOccurrence) -> float:
    """Use evidence-backed discourse confidence, never hard-coded force semantics."""
    value = claim.referent.metadata.get("commitment_strength")
    if value is None:
        raise ValueError(
            f"claim {claim.claim_ref} lacks explicit commitment-strength evidence"
        )
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid commitment strength for {claim.claim_ref}") from exc
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"commitment strength outside [0,1] for {claim.claim_ref}")
    return numeric
