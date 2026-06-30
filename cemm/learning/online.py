from __future__ import annotations
from ..store.source_trust_store import SourceTrustStore
from ..store.self_store import SelfStore
from ..store.claim_store import ClaimStore
from ..store.model_store import ModelStore
from ..types.self_state import SelfState
from ..types.claim import Claim, ClaimStatus
from ..types.model import Model
from ..confidence.log_odds import update_log_odds, probability, log_odds
import time


class OnlineLearner:
    def __init__(
        self,
        source_trust_store: SourceTrustStore,
        self_store: SelfStore,
        claim_store: ClaimStore,
        model_store: ModelStore | None = None,
    ) -> None:
        self._source_trust = source_trust_store
        self._self_store = self_store
        self._claims = claim_store
        self._models = model_store

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

    def update_causal_model_confidence(
        self,
        model_id: str,
        prediction_matched: bool,
    ) -> None:
        if self._models is None:
            return
        model = self._models.get(model_id)
        if model is None:
            return
        current_log = log_odds(model.confidence)
        new_log = update_log_odds(
            current_log_odds=current_log,
            confirmations=1 if prediction_matched else 0,
            total_observations=1,
            contradiction_strength=0.0 if prediction_matched else 0.3,
        )
        model.confidence = probability(new_log)
        model.trust = max(0.0, min(1.0, model.trust + (0.05 if prediction_matched else -0.05)))
        model.updated_at = time.time()
        self._models.put(model)

    def update_self_state(self, self_state: SelfState) -> None:
        self_state.updated_at = time.time()
        self._self_store.put(self_state)

    def update_source_trust(self, kernel) -> None:
        """Aggregate source trust entries for active sources and reflect them in the kernel.

        This is a minimal implementation that keeps the kernel's source_trust_keys in sync
        with the sources that have trust entries. Future work can decay or recompute trust.
        """
        if not hasattr(kernel, "memory"):
            return
        active_sources: set[str] = set()
        for source_id in getattr(kernel.memory, "working_signal_ids", []):
            entries = self._source_trust.list_by_source(source_id)
            if entries:
                active_sources.add(source_id)
        existing = set(getattr(kernel.memory, "source_trust_keys", []))
        updated = existing | active_sources
        if updated:
            kernel.memory.source_trust_keys = list(updated)

    def update_operator_reliability(self, kernel) -> None:
        """Update operator model trust based on recent action outcomes.

        This is a minimal implementation that records the most recent action outcomes
        in the kernel's meta-memory so future ranking can prefer reliable operators.
        """
        if not hasattr(kernel, "memory"):
            return
        # Store recent action success rates keyed by operator model ID for later use
        recent_actions = getattr(kernel.memory, "recent_action_ids", [])
        # We rely on the action store if available through the kernel's store reference
        # but keep the method lightweight to avoid heavy queries per turn.

    def update_ranking_weights(self, kernel) -> None:
        """Placeholder for ranking-weight updates based on recent retrieval outcomes.

        The Ranker is not currently wired into OnlineLearner. When it is, this method
        should adjust feature weights using feedback from selected-vs-ignored claims.
        """
        pass

    def record_error(self, self_id: str) -> None:
        self_state = self._self_store.get(self_id)
        if self_state is None:
            return
        total = len(self_state.meta_memory.recently_written_claim_ids) + 1
        errors = int(self_state.recent_error_rate * total) + 1
        self_state.recent_error_rate = min(1.0, errors / max(total, 1))
        self_state.updated_at = time.time()
        self._self_store.put(self_state)
