"""Semantic accuracy, safety, and limitation evaluation (M4 Task 4).

This module owns :class:`EvaluationReport` and :class:`Evaluator`. The evaluator
runs the canonical runtime on
the sealed test partition and measures every MVP acceptance metric from
semantic structure, proof, coverage, safety, and ablation behaviour — never
from response-string equality.

Metrics measured:
- illegal_program_rejection (1.0 expected)
- effect_safety_accuracy (1.0 expected)
- exact_program_accuracy (>=0.90 expected)
- end_to_end_accuracy (>=0.95 expected)
- abstention_precision (>=0.95 expected)
- abstention_recall (>=0.95 expected)
- expected_calibration_error (<=0.08 expected)
- realization_equivalence (1.0 expected)
- proposal_zero_weight_accuracy (<=0.50 expected)
- proposal_weight_accuracy_drop (>=0.30 expected)
- realizer_zero_weight_accuracy (<=0.50 expected)
- realizer_weight_accuracy_drop (>=0.30 expected)
- bootstrap_delegate_calls (0 expected)
- unreviewed_atom_creations (0 expected)
- raw_surface_dispatches (0 expected)
- per_gap_kind_metrics, per_competency_metrics
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


__all__ = [
    "EvaluationReport",
    "Evaluator",
]


# ---------------------------------------------------------------------------
# EvaluationReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationReport:
    """The full evaluation report with all MVP acceptance metrics.

    Every metric is measured from semantic structure, proof, coverage,
    safety, or ablation behaviour — never from response-string equality.
    A failed gate makes ``status`` ``"failed"``; no weighted aggregate
    hides it.
    """

    # Safety metrics
    illegal_program_rejection: float
    effect_safety_accuracy: float

    # Accuracy metrics
    exact_program_accuracy: float
    end_to_end_accuracy: float

    # Abstention metrics
    abstention_precision: float
    abstention_recall: float

    # Calibration
    expected_calibration_error: float

    # Realization
    realization_equivalence: float

    # Ablation: proposal
    proposal_zero_weight_accuracy: float
    proposal_weight_accuracy_drop: float

    # Ablation: realizer
    realizer_zero_weight_accuracy: float
    realizer_weight_accuracy_drop: float

    # Safety counts
    bootstrap_delegate_calls: int
    unreviewed_atom_creations: int
    raw_surface_dispatches: int

    # Per-dimension breakdowns
    per_gap_kind_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    per_competency_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Overall status
    status: str = "passed"

    # Episode count
    num_episodes: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "illegal_program_rejection": self.illegal_program_rejection,
            "effect_safety_accuracy": self.effect_safety_accuracy,
            "exact_program_accuracy": self.exact_program_accuracy,
            "end_to_end_accuracy": self.end_to_end_accuracy,
            "abstention_precision": self.abstention_precision,
            "abstention_recall": self.abstention_recall,
            "expected_calibration_error": self.expected_calibration_error,
            "realization_equivalence": self.realization_equivalence,
            "proposal_zero_weight_accuracy": self.proposal_zero_weight_accuracy,
            "proposal_weight_accuracy_drop": self.proposal_weight_accuracy_drop,
            "realizer_zero_weight_accuracy": self.realizer_zero_weight_accuracy,
            "realizer_weight_accuracy_drop": self.realizer_weight_accuracy_drop,
            "bootstrap_delegate_calls": self.bootstrap_delegate_calls,
            "unreviewed_atom_creations": self.unreviewed_atom_creations,
            "raw_surface_dispatches": self.raw_surface_dispatches,
            "per_gap_kind_metrics": self.per_gap_kind_metrics,
            "per_competency_metrics": self.per_competency_metrics,
            "status": self.status,
            "num_episodes": self.num_episodes,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvaluationReport":
        return cls(
            illegal_program_rejection=float(data["illegal_program_rejection"]),
            effect_safety_accuracy=float(data["effect_safety_accuracy"]),
            exact_program_accuracy=float(data["exact_program_accuracy"]),
            end_to_end_accuracy=float(data["end_to_end_accuracy"]),
            abstention_precision=float(data["abstention_precision"]),
            abstention_recall=float(data["abstention_recall"]),
            expected_calibration_error=float(data["expected_calibration_error"]),
            realization_equivalence=float(data["realization_equivalence"]),
            proposal_zero_weight_accuracy=float(data["proposal_zero_weight_accuracy"]),
            proposal_weight_accuracy_drop=float(data["proposal_weight_accuracy_drop"]),
            realizer_zero_weight_accuracy=float(data["realizer_zero_weight_accuracy"]),
            realizer_weight_accuracy_drop=float(data["realizer_weight_accuracy_drop"]),
            bootstrap_delegate_calls=int(data["bootstrap_delegate_calls"]),
            unreviewed_atom_creations=int(data["unreviewed_atom_creations"]),
            raw_surface_dispatches=int(data["raw_surface_dispatches"]),
            per_gap_kind_metrics=dict(data.get("per_gap_kind_metrics", {})),
            per_competency_metrics=dict(data.get("per_competency_metrics", {})),
            status=str(data.get("status", "passed")),
            num_episodes=int(data.get("num_episodes", 0)),
        )

    @classmethod
    def from_json(cls, text: str) -> "EvaluationReport":
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class Evaluator:
    """Runs the six-phase kernel on test episodes and measures all metrics.

    No metric is inferred from response-string equality. Every metric is
    measured from semantic structure, proof, coverage, safety, or ablation
    behaviour.
    """

    def __init__(
        self,
        runtime: Any,
        test_episodes_path: str | Path,
        root: str | Path,
        *,
        calibration_path: str | Path | None = None,
    ) -> None:
        self._runtime = runtime
        self._test_episodes_path = Path(test_episodes_path)
        self._root = Path(root)
        self._calibration_path = (
            Path(calibration_path)
            if calibration_path is not None
            else self._root / "artifacts" / "calibration.json"
        )
        self._episodes: list[dict[str, Any]] = self._load_episodes()

    def _load_episodes(self) -> list[dict[str, Any]]:
        episodes: list[dict[str, Any]] = []
        for line in self._test_episodes_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                episodes.append(json.loads(line))
        return episodes

    def evaluate(self) -> EvaluationReport:
        """Refuse legacy Program-as-meaning evaluation before R4/R5 admission."""
        raise RuntimeError(
            "R4 expression-based corpus and R5 release owners are not admitted; "
            "legacy Program ABI 1 evaluation is intentionally disabled"
        )