"""Stable public projection of a canonical CognitiveCycle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PublicCycleResult:
    output_text: str
    cycle_id: str
    context_id: str
    realized_item_refs: tuple[str, ...] = ()
    blocked_item_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    trace_stages: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return bool(self.output_text) and not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_text": self.output_text,
            "cycle_id": self.cycle_id,
            "context_id": self.context_id,
            "realized_item_refs": list(self.realized_item_refs),
            "blocked_item_refs": list(self.blocked_item_refs),
            "errors": list(self.errors),
            "trace_stages": list(self.trace_stages),
        }


def project_cycle(cycle: Any) -> PublicCycleResult:
    payload = getattr(cycle, "surface_payload", None)
    trace = getattr(cycle, "trace", None)
    trigger = getattr(cycle, "trigger", None)
    return PublicCycleResult(
        output_text=getattr(payload, "surface_text", "") if payload else "",
        cycle_id=getattr(cycle, "cycle_id", ""),
        context_id=getattr(trigger, "context_id", "default") if trigger else "default",
        realized_item_refs=tuple(getattr(payload, "realized_item_refs", ()) or ()),
        blocked_item_refs=tuple(getattr(payload, "blocked_item_refs", ()) or ()),
        errors=tuple(getattr(trace, "errors", ()) or ()),
        trace_stages=tuple(getattr(trace, "stages", ()) or ()),
    )
