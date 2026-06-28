from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrainingLabel:
    id: str
    job_id: str
    arbiter_label: dict[str, Any] | None = None
    final_confidence: float | None = None
    source: str = "auto"
    created_at: float = 0.0


@dataclass
class EvalSet:
    id: str
    name: str
    description: str | None = None
    created_at: float = 0.0


@dataclass
class EvalResult:
    id: str
    eval_set_id: str
    job_id: str
    score: float | None = None
    metrics: dict[str, Any] | None = None
    created_at: float = 0.0


@dataclass
class PromotionCandidate:
    id: str
    model_id: str
    reason: str
    score: float = 0.0
    status: str = "pending"
    created_at: float = 0.0
    reviewed_at: float | None = None
