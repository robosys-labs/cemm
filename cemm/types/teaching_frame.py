"""TeachingFrame — persistent concept-building state across turns.

A TeachingFrame tracks an active teaching session: the target concept being
taught, accumulated graph/patch references, open slots yet to be filled,
and the signals that started and continued the frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TeachingFrame:
    frame_id: str
    context_id: str
    target_concept_key: str
    target_concept_id: str = ""
    active: bool = True
    started_signal_id: str = ""
    last_signal_id: str = ""
    open_slots: list[str] = field(default_factory=list)
    accumulated_graph_ids: list[str] = field(default_factory=list)
    accumulated_patch_ids: list[str] = field(default_factory=list)
    current_definition_graph_id: str = ""
    confidence: float = 0.5
