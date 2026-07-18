"""Review-only identity merge and split proposal generation."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from ..schema.model import semantic_fingerprint
from .model import (
    GroundingCandidate,
    GroundingFactorKind,
    IdentityMergeProposal,
    IdentitySplitProposal,
)


class IdentityProposalEngine:
    def merge_proposals(
        self,
        candidates: Iterable[GroundingCandidate],
        *,
        context_ref: str,
        minimum_confidence: float = 0.7,
    ) -> tuple[IdentityMergeProposal, ...]:
        by_identity: dict[str, list[GroundingCandidate]] = defaultdict(list)
        for candidate in candidates:
            identity_factors = tuple(
                factor for factor in candidate.factors
                if factor.factor_kind == GroundingFactorKind.IDENTITY
            )
            for factor in identity_factors:
                key = str(factor.metadata.get("normalized_value") or factor.reason)
                by_identity[key].append(candidate)
        proposals = []
        for key, values in sorted(by_identity.items()):
            unique = {item.target_ref: item for item in values if not item.provisional}
            refs = sorted(unique)
            for index, left_ref in enumerate(refs):
                for right_ref in refs[index + 1:]:
                    left, right = unique[left_ref], unique[right_ref]
                    common_context = set(left.context_refs).intersection(right.context_refs)
                    common_types = set(left.type_refs).intersection(right.type_refs)
                    conflicting = []
                    if not common_context:
                        conflicting.append("factor:identity-context-conflict")
                    if left.storage_kind != right.storage_kind:
                        conflicting.append("factor:identity-storage-conflict")
                    confidence = min(0.99, 0.65 + 0.05 * len(common_types))
                    if conflicting or confidence < minimum_confidence:
                        continue
                    evidence = tuple(sorted({
                        ref for item in (left, right) for factor in item.factors
                        if factor.factor_kind == GroundingFactorKind.IDENTITY
                        for ref in factor.evidence_refs
                    }))
                    factors = tuple(sorted({
                        factor.factor_ref for item in (left, right) for factor in item.factors
                        if factor.factor_kind in {
                            GroundingFactorKind.IDENTITY, GroundingFactorKind.TYPE,
                            GroundingFactorKind.CONTEXT,
                        }
                    }))
                    proposals.append(IdentityMergeProposal(
                        proposal_ref="identity-merge-proposal:" + semantic_fingerprint(
                            "identity-merge-proposal-ref", (left_ref, right_ref, context_ref, key), 24
                        ),
                        left_ref=left_ref,
                        right_ref=right_ref,
                        context_ref=context_ref,
                        confidence=confidence,
                        evidence_refs=evidence or (f"identity-key:{key}",),
                        supporting_factor_refs=factors or (f"identity-key:{key}",),
                        conflicting_factor_refs=(),
                        requires_review=True,
                    ))
        return tuple(sorted(proposals, key=lambda item: item.proposal_ref))

    def split_proposal(
        self,
        *,
        referent_ref: str,
        partition_keys: tuple[str, ...],
        context_ref: str,
        conflicting_factor_refs: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        confidence: float,
    ) -> IdentitySplitProposal:
        return IdentitySplitProposal(
            proposal_ref="identity-split-proposal:" + semantic_fingerprint(
                "identity-split-proposal-ref",
                (referent_ref, tuple(sorted(partition_keys)), context_ref, conflicting_factor_refs),
                24,
            ),
            referent_ref=referent_ref,
            partition_keys=tuple(sorted(partition_keys)),
            context_ref=context_ref,
            confidence=confidence,
            evidence_refs=tuple(sorted(set(evidence_refs))),
            conflicting_factor_refs=tuple(sorted(set(conflicting_factor_refs))),
            requires_review=True,
        )
