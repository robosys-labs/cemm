from __future__ import annotations
from ..types.context_kernel import ContextKernel
from ..types.claim import Claim
from ..registry import Registry


class Normalizer:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def normalize_claim(self, claim: Claim, kernel: ContextKernel) -> Claim:
        canonical_predicate = self.registry.canonicalize_predicate(claim.predicate)
        if canonical_predicate != claim.predicate:
            claim.predicate = canonical_predicate
        if claim.valid_from is None:
            claim.valid_from = kernel.time.now
        return claim

    def normalize_predicate(self, raw: str) -> str:
        return self.registry.canonicalize_predicate(raw.lower().strip())

    def normalize_entity_type(self, raw: str) -> str:
        return self.registry.canonicalize_entity_type(raw.lower().strip())
