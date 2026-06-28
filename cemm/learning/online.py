from __future__ import annotations
from ..store.source_trust_store import SourceTrustStore
from ..store.self_store import SelfStore
from ..store.claim_store import ClaimStore
from ..types.self_state import SelfState
from ..types.claim import Claim, ClaimStatus
from ..confidence.log_odds import update_log_odds, probability
import time


class OnlineLearner:
    def __init__(
        self,
        source_trust_store: SourceTrustStore,
        self_store: SelfStore,
        claim_store: ClaimStore,
    ) -> None:
        self._source_trust = source_trust_store
        self._self_store = self_store
        self._claims = claim_store

    def record_outcome(
        self,
        source_id: str,
        domain: str,
        success: bool,
    ) -> None:
        self._source_trust.record_outcome(source_id, domain, success)

    def update_claim_confidence(
        self,
        claim_id: str,
        feedback_correct: bool,
    ) -> None:
        claim = self._claims.get(claim_id)
        if claim is None:
            return
        new_log_odds = update_log_odds(
            current_log_odds=claim.confidence_log_odds,
            evidence_count=1,
            confirmations=1 if feedback_correct else 0,
            total_observations=1,
            contradiction_strength=0.0 if feedback_correct else 0.5,
        )
        claim.confidence_log_odds = new_log_odds
        claim.confidence = probability(new_log_odds)
        claim.updated_at = time.time()
        self._claims.put(claim)

    def update_self_state(self, self_state: SelfState) -> None:
        self_state.updated_at = time.time()
        self._self_store.put(self_state)

    def record_error(self, self_id: str) -> None:
        self_state = self._self_store.get(self_id)
        if self_state is None:
            return
        total = len(self_state.meta_memory.recently_written_claim_ids) + 1
        errors = int(self_state.recent_error_rate * total) + 1
        self_state.recent_error_rate = min(1.0, errors / max(total, 1))
        self_state.updated_at = time.time()
        self._self_store.put(self_state)
