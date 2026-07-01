from __future__ import annotations

from ..types.context_kernel import ContextKernel
from ..types.packets import GroundedGraph
from ..types.semantic_event_graph import SemanticEventGraph
from .entity_resolver import EntityResolver
from .frame_engine import FrameEngine


class GroundingPipeline:
    def __init__(self, resolver: EntityResolver, frames: FrameEngine) -> None:
        self._resolver = resolver
        self._frames = frames

    def run(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        content: str | None = None,
    ) -> GroundedGraph:
        self._resolver.resolve_self(kernel)
        resolved_ids: list[str] = []
        for ref in graph.entity_refs:
            name = ref.get("name", "")
            if name and not ref.get("entity_id"):
                resolved = self._resolver.resolve_by_name(name, kernel)
                if resolved:
                    ref["entity_id"] = resolved[0].id
                    ref["entity_type"] = resolved[0].type.value
                    resolved_ids.append(resolved[0].id)
        invalidated_ids = self._frames.apply_frame_rules(kernel)
        graph.permission_scope = kernel.permission.scope.value
        location_ids = []
        for ref in graph.entity_refs:
            ref["frame_valid"] = ref.get("entity_id", "") not in invalidated_ids
            if ref.get("role") == "location" and ref.get("entity_id"):
                location_ids.append(ref["entity_id"])

        return GroundedGraph(
            semantic_event_graph_id=graph.id,
            entity_ids=resolved_ids,
            resolved_time_refs=self._resolve_time_refs(content, kernel),
            resolved_location_ids=location_ids,
            active_frame_ids=list(kernel.memory.active_frame_ids) if kernel.memory else [],
            permission=kernel.permission.scope.value if kernel.permission else "public",
            missing_slots=list(kernel.goal.missing_slots) if kernel.goal else [],
            confidence=graph.confidence,
        )

    def _resolve_time_refs(self, content: str | None, kernel: ContextKernel) -> list[str]:
        refs: list[str] = []
        if not content:
            return refs
        now = kernel.time.now
        content_lower = content.lower()
        if any(w in content_lower for w in ("now", "today", "currently")):
            refs.append(f"now:{now}")
        if "yesterday" in content_lower:
            refs.append(f"yesterday:{now - 86400}")
        if "tomorrow" in content_lower:
            refs.append(f"tomorrow:{now + 86400}")
        return refs
