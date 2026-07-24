"""Stable public projection of a canonical v3.4.7 CycleResult."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PublicCycleResult:
    output_text: str
    cycle_id: str
    context_id: str
    target_language: str = "und"
    realized_item_refs: tuple[str, ...] = ()
    blocked_item_refs: tuple[str, ...] = ()
    committed_patch_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    trace_stages: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return bool(self.output_text) and not self.blocked_item_refs

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_text": self.output_text,
            "cycle_id": self.cycle_id,
            "context_id": self.context_id,
            "target_language": self.target_language,
            "realized_item_refs": list(self.realized_item_refs),
            "blocked_item_refs": list(self.blocked_item_refs),
            "committed_patch_refs": list(self.committed_patch_refs),
            "errors": list(self.errors),
            "trace_stages": list(self.trace_stages),
        }


def project_cycle(cycle: Any) -> PublicCycleResult:
    proof = getattr(cycle, "emission_proof", None)
    trace = getattr(cycle, "trace", None)
    return PublicCycleResult(
        output_text=getattr(cycle, "output_text", ""),
        cycle_id=getattr(cycle, "cycle_id", ""),
        context_id=getattr(cycle, "context_id", "default"),
        target_language=getattr(cycle, "target_language", "und"),
        realized_item_refs=tuple(getattr(proof, "realized_clause_refs", ()) or ()),
        blocked_item_refs=tuple(getattr(proof, "blocked_semantic_refs", ()) or ()),
        committed_patch_refs=tuple(getattr(cycle, "committed_patch_refs", ()) or ()),
        errors=tuple(getattr(trace, "errors", ()) or ()),
        trace_stages=tuple(getattr(trace, "stages", ()) or ()),
    )
