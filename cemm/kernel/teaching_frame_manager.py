"""TeachingFrameManager — open/continue/close teaching frames across turns.

Detects teaching intent from SemanticProgram instructions and manages a
TeachingFrame state machine: open on teaching offer, continue on related
input, close on topic shift or explicit completion.

All memory writes are produced as graph patch candidates — never direct
store mutations.
"""

from __future__ import annotations

import uuid
from typing import Any

from ..types.teaching_frame import TeachingFrame


class TeachingFrameManager:
    def __init__(self) -> None:
        self._active_frames: dict[str, TeachingFrame] = {}

    @property
    def active_frame(self) -> TeachingFrame | None:
        for frame in self._active_frames.values():
            if frame.active:
                return frame
        return None

    def process_turn(
        self,
        program: Any | None = None,
        graph: Any | None = None,
        kernel: Any | None = None,
        signal_id: str = "",
    ) -> TeachingFrame | None:
        if program is None:
            return self.active_frame

        entry = program.entry_instruction
        if entry is None:
            return self.active_frame

        if entry.instruction_kind == "teaching":
            return self._open_or_continue(entry, graph, kernel, signal_id)

        if self._is_continuation(entry, program, kernel):
            frame = self.active_frame
            if frame is not None:
                frame.last_signal_id = signal_id
                if graph is not None:
                    frame.accumulated_graph_ids.append(graph.id)
                return frame

        self._close_or_suspend(kernel)
        return self.active_frame

    def _open_or_continue(
        self,
        entry: Any,
        graph: Any | None = None,
        kernel: Any | None = None,
        signal_id: str = "",
    ) -> TeachingFrame:
        target_concept = self._extract_target_concept(entry, graph)

        existing = self.active_frame
        if existing is not None and existing.target_concept_key == target_concept:
            existing.last_signal_id = signal_id
            if graph is not None:
                existing.accumulated_graph_ids.append(graph.id)
            return existing

        if existing is not None:
            existing.active = False

        context_id = ""
        if kernel is not None:
            context_id = getattr(kernel, "id", "")

        frame = TeachingFrame(
            frame_id=uuid.uuid4().hex[:16],
            context_id=context_id,
            target_concept_key=target_concept,
            started_signal_id=signal_id,
            last_signal_id=signal_id,
            open_slots=self._extract_open_slots(entry),
            accumulated_graph_ids=[graph.id] if graph is not None else [],
            confidence=entry.confidence,
        )
        self._active_frames[frame.frame_id] = frame

        if kernel is not None:
            conv = getattr(kernel, "conversation", None)
            if conv is not None and hasattr(conv, "active_teaching_target"):
                conv.active_teaching_target = target_concept

        return frame

    def _is_continuation(
        self,
        entry: Any,
        program: Any,
        kernel: Any | None = None,
    ) -> bool:
        frame = self.active_frame
        if frame is None:
            return False

        if entry.discourse_relation in ("elaboration", "sequence"):
            return True

        if kernel is not None:
            topic = getattr(kernel, "topic", None)
            if topic is not None:
                active_topic = getattr(topic, "active_topic_surface", "")
                if active_topic and active_topic.lower() == frame.target_concept_key.lower():
                    return True

        return False

    def _close_or_suspend(self, kernel: Any | None = None) -> None:
        frame = self.active_frame
        if frame is None:
            return

        if kernel is not None:
            conv = getattr(kernel, "conversation", None)
            if conv is not None and hasattr(conv, "active_teaching_target"):
                if conv.active_teaching_target == frame.target_concept_key:
                    conv.active_teaching_target = ""

        frame.active = False

    def _extract_target_concept(self, entry: Any, graph: Any | None = None) -> str:
        if graph is not None:
            for aid in entry.atom_ids:
                atom = graph.atoms.get(aid)
                if atom is None:
                    continue
                if atom.kind in ("entity", "concept"):
                    return atom.key.replace("entity:", "").replace("concept:", "")
                if atom.kind == "intent" and "teach" in atom.key:
                    for edge in graph.edges:
                        if edge.source_id == atom.id and edge.edge_type == "teaches":
                            target = graph.atoms.get(edge.target_id)
                            if target is not None:
                                return target.key.replace("entity:", "").replace("concept:", "")
            for aid in entry.atom_ids:
                atom = graph.atoms.get(aid)
                if atom is None:
                    continue
                if atom.kind in ("relation", "state", "process"):
                    return atom.key.replace("relation:", "").replace("state:", "").replace("process:", "")
            for aid in entry.atom_ids:
                atom = graph.atoms.get(aid)
                if atom is None:
                    continue
                if atom.kind == "entity" and atom.key.startswith("entity:"):
                    return atom.key.replace("entity:", "")
        if entry.surface:
            words = entry.surface.strip().split()
            for w in reversed(words):
                if w[0].isupper() or (len(w) > 3 and not w[0].islower()):
                    return w.lower()
            if len(words) > 1:
                return words[-1]
            return words[0]
        return "unknown"

    def _extract_open_slots(self, entry: Any) -> list[str]:
        return [k for k, v in entry.output_slots.items() if not v]
