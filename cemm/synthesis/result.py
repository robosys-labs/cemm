from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SynthesisResult:
    success: bool
    output: str
    strategy: str = "template"
    cost_ms: float = 0.0
    verified: bool = False
