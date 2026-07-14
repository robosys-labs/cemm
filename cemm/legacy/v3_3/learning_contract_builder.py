"""LearningContractBuilder — builds LearningContract from episode state.
This is the sole authority for learning operations.
"""

from __future__ import annotations

import uuid
import time
from typing import Any

from ...types.learning_contract import LearningContract
from ...types.learning_episode import LearningEpisode
from ...types.knowledge_strength import PromotionState


class LearningContractBuilder:
    """Builds LearningContract from episode state.

    The LearningContract defines what operations are permitted,
    the scope of activation, promotion ceiling, and evidence requirements.
    """

    def build(
        self,
        episode: LearningEpisode,
        promotion_ceiling: PromotionState = PromotionState.SESSION_PROVISIONAL,
        minimum_confidence: float = 0.3,
    ) -> LearningContract:
        return LearningContract(
            contract_id=uuid.uuid4().hex[:16],
            episode_id=episode.episode_id,
            target_hypothesis_ids=tuple(episode.hypothesis_ids),
            activation_scope=episode.target_scope,
            promotion_ceiling=promotion_ceiling,
            minimum_confidence=minimum_confidence,
            created_at=time.time(),
        )

    def build_for_durable(
        self,
        episode: LearningEpisode,
    ) -> LearningContract:
        """Build a contract that allows durable promotion."""
        return LearningContract(
            contract_id=uuid.uuid4().hex[:16],
            episode_id=episode.episode_id,
            target_hypothesis_ids=tuple(episode.hypothesis_ids),
            activation_scope=episode.target_scope,
            promotion_ceiling=PromotionState.USER_SCOPED_ACTIVE,
            minimum_confidence=0.6,
            required_evidence=("independent_source", "successful_use"),
            created_at=time.time(),
        )
