from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SemanticFocus:
    atom_id: str
    reason: str
    priority: int
    confidence: float
