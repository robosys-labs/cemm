"""LearningUseObserver — observes use of learned bindings and emits evidence.

Later turns that select a session-provisional binding produce
LearningUseOutcome evidence events that strengthen or weaken the binding's
knowledge strength. This observer operates across turns, recording
successful use, repair events, user confirmations, and corrections.
"""

from __future__ import annotations

import uuid
import time
from typing import Any

from ..types.learning_evidence import (
    LearningUseOutcome, UseOutcomeKind, LearningEvidenceEvent,
)


class LearningUseObserver:
    """Observes use of learned material and emits evidence events.

    Called after:
    - A session-provisional binding is selected during interpretation
    - A query or write succeeds using a learned binding
    - A response is formed using learned material
    - A user corrects or confirms learned material
    """

    def observe_binding_selected(
        self,
        hypothesis_id: str,
        surface_form: str,
        resolved_target: str = "",
        confidence: float = 0.5,
    ) -> list[LearningUseOutcome]:
        outcome = LearningUseOutcome(
            outcome_id=uuid.uuid4().hex[:16],
            hypothesis_id=hypothesis_id,
            outcome_kind=UseOutcomeKind.BINDING_SELECTED,
            confidence=confidence,
            details={
                "surface_form": surface_form,
                "resolved_target": resolved_target,
            },
        )
        return [outcome]

    def observe_use_success(
        self,
        hypothesis_id: str,
        use_type: str = "query",
        surface_form: str = "",
        confidence: float = 0.6,
    ) -> list[LearningUseOutcome]:
        kind_map = {
            "query": UseOutcomeKind.QUERY_SUCCESS,
            "write": UseOutcomeKind.WRITE_SUCCESS,
            "response": UseOutcomeKind.RESPONSE_SUCCESS,
            "reference": UseOutcomeKind.SUBSEQUENT_REFERENCE_RESOLVED,
        }
        kind = kind_map.get(use_type, UseOutcomeKind.QUERY_SUCCESS)
        outcome = LearningUseOutcome(
            outcome_id=uuid.uuid4().hex[:16],
            hypothesis_id=hypothesis_id,
            outcome_kind=kind,
            confidence=confidence,
            details={"surface_form": surface_form},
        )
        return [outcome]

    def observe_repair(
        self,
        hypothesis_id: str,
        repair_type: str = "correction",
        surface_form: str = "",
    ) -> list[LearningUseOutcome]:
        kind_map = {
            "correction": UseOutcomeKind.USER_CORRECTION,
            "confirmation": UseOutcomeKind.USER_CONFIRMATION,
            "reference_failed": UseOutcomeKind.SUBSEQUENT_REFERENCE_FAILED,
            "response_repair": UseOutcomeKind.RESPONSE_REPAIR,
        }
        kind = kind_map.get(repair_type, UseOutcomeKind.USER_CORRECTION)
        outcome = LearningUseOutcome(
            outcome_id=uuid.uuid4().hex[:16],
            hypothesis_id=hypothesis_id,
            outcome_kind=kind,
            details={"surface_form": surface_form},
        )
        return [outcome]

    def use_outcomes_to_evidence(
        self,
        outcomes: list[LearningUseOutcome],
    ) -> list[LearningEvidenceEvent]:
        return [outcome.to_evidence_event() for outcome in outcomes]
