"""Promotion loop for CEMM v3.3 Learning Nervous System.

Implements the promotion rule:
    candidate labels → validation (held-out eval set) → promoted registry update
    → deterministic fallback preserved

Generated labels must never become active truth without validation.
The deterministic code path remains as fallback. Promoted models augment, not replace.

Key design:
- PromotionGate evaluates candidate labels against a held-out validation set
- Only labels that pass validation threshold are promoted
- Promoted labels update the SemanticModelStore or registry seed files
- The deterministic fallback (seed aliases, semantic matcher) is always preserved
- Negative supervision from correction labels is tracked separately
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .training_tasks import TrainingLabel, CorrectionLabel, TrainingTaskSpec, TaskType, MetricType
from ...registry.semantic_model_store import SemanticModelStore, SurfaceBinding, BindingStatus


@dataclass
class PromotionCandidate:
    """A candidate label awaiting promotion validation."""
    label: TrainingLabel
    created_at: float = field(default_factory=time.time)
    validated: bool = False
    validation_score: float = 0.0
    promoted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label.to_dict(),
            "created_at": self.created_at,
            "validated": self.validated,
            "validation_score": self.validation_score,
            "promoted": self.promoted,
        }


@dataclass
class PromotionResult:
    """Result of a promotion cycle."""
    promoted_count: int = 0
    rejected_count: int = 0
    promoted_labels: list[dict[str, Any]] = field(default_factory=list)
    rejected_labels: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "promoted_count": self.promoted_count,
            "rejected_count": self.rejected_count,
            "promoted_labels": list(self.promoted_labels),
            "rejected_labels": list(self.rejected_labels),
        }


class PromotionGate:
    """Validates candidate labels before promotion.

    The gate uses a held-out validation set to evaluate candidate labels.
    Labels that pass the validation threshold are promoted; others are rejected.

    For surface_binding_learning, promotion means:
    - Creating/reinforcing a SurfaceBinding in SemanticModelStore
    - The binding starts as candidate and must accumulate evidence before becoming active

    For conversation_act_classification, promotion means:
    - Adding the label to a validation queue for future model training
    - The deterministic classifier remains as fallback
    """

    def __init__(
        self,
        semantic_model_store: SemanticModelStore | None = None,
        validation_threshold: float = 0.7,
        min_evidence_for_promotion: int = 2,
    ) -> None:
        self._store = semantic_model_store
        self._threshold = validation_threshold
        self._min_evidence = min_evidence_for_promotion
        self._candidates: list[PromotionCandidate] = []
        self._validation_set: list[TrainingLabel] = []
        self._promotion_history: list[PromotionResult] = []

    @property
    def candidates(self) -> list[PromotionCandidate]:
        return list(self._candidates)

    @property
    def promotion_history(self) -> list[PromotionResult]:
        return list(self._promotion_history)

    def add_candidate(self, label: TrainingLabel) -> PromotionCandidate:
        """Add a candidate label for promotion validation."""
        candidate = PromotionCandidate(label=label)
        self._candidates.append(candidate)
        return candidate

    def add_correction(self, correction: CorrectionLabel) -> list[PromotionCandidate]:
        """Add a correction label as both positive and negative candidates.

        Returns the created PromotionCandidate objects.
        """
        candidates = []
        # Positive supervision: correct mapping
        pos_label = correction.to_positive_label()
        candidates.append(self.add_candidate(pos_label))
        # Negative supervision: wrong mapping to avoid
        neg_label = correction.to_negative_label()
        candidates.append(self.add_candidate(neg_label))
        return candidates

    def add_validation_sample(self, label: TrainingLabel) -> None:
        """Add a sample to the held-out validation set."""
        self._validation_set.append(label)

    def validate(self) -> PromotionResult:
        """Validate all pending candidates and promote those that pass.

        For surface_binding_learning:
        - Positive labels create/reinforce bindings in SemanticModelStore
        - Bindings go through the normal lifecycle (observed → candidate → active)
        - The SemanticModelStore.promote_ready() handles the final promotion

        For other tasks:
        - Labels are scored against the validation set
        - Only labels above threshold are marked as promoted

        Returns:
            PromotionResult with counts of promoted and rejected labels.
        """
        result = PromotionResult()

        for candidate in self._candidates:
            if candidate.validated:
                continue

            candidate.validated = True
            label = candidate.label

            if label.task_name == "surface_binding_learning" and self._store:
                # Promote via SemanticModelStore lifecycle
                score = self._validate_surface_binding(label)
                candidate.validation_score = score
                if score >= self._threshold:
                    self._promote_surface_binding(label)
                    candidate.promoted = True
                    result.promoted_count += 1
                    result.promoted_labels.append(candidate.to_dict())
                else:
                    result.rejected_count += 1
                    result.rejected_labels.append(candidate.to_dict())
            else:
                # Generic validation: score against validation set
                score = self._score_against_validation(label)
                candidate.validation_score = score
                if score >= self._threshold:
                    candidate.promoted = True
                    result.promoted_count += 1
                    result.promoted_labels.append(candidate.to_dict())
                else:
                    result.rejected_count += 1
                    result.rejected_labels.append(candidate.to_dict())

        # Clear validated candidates
        self._candidates = [c for c in self._candidates if not c.validated]

        self._promotion_history.append(result)
        return result

    def _validate_surface_binding(self, label: TrainingLabel) -> float:
        """Validate a surface binding label.

        Score is based on:
        - Whether the label has a source with high confidence (correction > deterministic)
        - Whether there's validation set agreement
        """
        base_score = label.confidence
        if label.source == "correction":
            base_score = min(1.0, base_score + 0.1)
        if label.source == "user_teaching":
            base_score = min(1.0, base_score + 0.15)

        # Check validation set for agreement
        if self._validation_set:
            agreeing = sum(
                1 for v in self._validation_set
                if v.task_name == "surface_binding_learning"
                and v.input_data.get("surface") == label.input_data.get("surface")
                and v.label.get("maps_to_act_type") == label.label.get("maps_to_act_type")
            )
            if agreeing > 0:
                base_score = min(1.0, base_score + 0.1 * agreeing)

        return base_score

    def _promote_surface_binding(self, label: TrainingLabel) -> None:
        """Promote a surface binding label to the SemanticModelStore."""
        if not self._store:
            return

        surface = label.input_data.get("surface", "")
        if not surface:
            return

        act_type = label.label.get("maps_to_act_type", "")
        frame_key = label.label.get("maps_to_frame_key", "")
        language = label.input_data.get("language", "en")

        binding = SurfaceBinding(
            id="",
            surface=surface,
            language=language,
            normalized_surface=surface.lower().strip(),
            maps_to_act_type=act_type,
            maps_to_frame_key=frame_key,
            source=label.source,
        )
        self._store.observe_candidate(binding, signal_id=label.turn_id)

    def _score_against_validation(self, label: TrainingLabel) -> float:
        """Score a label against the validation set.

        For negative labels, score is based on whether the validation set
        confirms the error type.
        For positive labels, score is based on agreement with validation set.
        """
        if not self._validation_set:
            return label.confidence

        if label.is_negative:
            # Negative labels: check if validation set has similar errors
            agreeing = sum(
                1 for v in self._validation_set
                if v.task_name == label.task_name
                and v.label.get("error_type") == label.label.get("error_type")
            )
            return min(1.0, label.confidence + 0.05 * agreeing)
        else:
            # Positive labels: check agreement
            agreeing = sum(
                1 for v in self._validation_set
                if v.task_name == label.task_name
                and v.label == label.label
            )
            return min(1.0, label.confidence + 0.1 * agreeing)

    def export_promotion_report(self) -> dict[str, Any]:
        """Export a summary of all promotion cycles."""
        total_promoted = sum(r.promoted_count for r in self._promotion_history)
        total_rejected = sum(r.rejected_count for r in self._promotion_history)
        return {
            "total_cycles": len(self._promotion_history),
            "total_promoted": total_promoted,
            "total_rejected": total_rejected,
            "promotion_rate": total_promoted / max(total_promoted + total_rejected, 1),
            "validation_threshold": self._threshold,
            "min_evidence": self._min_evidence,
            "pending_candidates": len(self._candidates),
            "validation_set_size": len(self._validation_set),
        }
