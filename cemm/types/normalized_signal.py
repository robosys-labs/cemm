from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedSignal:
    raw_text: str
    normalized_forms: list[str] = field(default_factory=list)
    canonical_form: str = ""
    cased_form: str = ""
    detected_scripts: list[str] = field(default_factory=list)
    noise_features: dict[str, int | float | bool] = field(default_factory=dict)
    transform_trace: list[dict[str, str]] = field(default_factory=list)
    surface_features: dict[str, Any] = field(default_factory=dict)
    unknown_tokens: list[str] = field(default_factory=list)
    repair_candidates: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.5
    version: str = "cemm.normalized_signal.v1"
