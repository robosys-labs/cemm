"""R2 transition preview structures.

Transition previews are extracted from ``propose_transition`` actions
during verification.  They record the transition metadata that would be
executed if the verified meaning were admitted to EVALUATE, but they
do NOT trigger any effect execution.  This maintains the R2/R3 boundary:
R2 previews transitions, R3 executes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


TRANSITION_PREVIEW_ABI_VERSION = 1


@dataclass(frozen=True)
class TransitionPreview:
    """A validated transition preview extracted from a program action."""

    preview_ref: str
    transition_slot_ref: str
    source_application_ref: str
    event_type_ref: str
    compatible_modes: tuple[str, ...]
    required_roles: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    required_permissions: tuple[str, ...]
    adapter_ref: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": TRANSITION_PREVIEW_ABI_VERSION,
            "preview_ref": self.preview_ref,
            "transition_slot_ref": self.transition_slot_ref,
            "source_application_ref": self.source_application_ref,
            "event_type_ref": self.event_type_ref,
            "compatible_modes": list(self.compatible_modes),
            "required_roles": list(self.required_roles),
            "required_capabilities": list(self.required_capabilities),
            "required_permissions": list(self.required_permissions),
            "adapter_ref": self.adapter_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TransitionPreview":
        return cls(
            preview_ref=data["preview_ref"],
            transition_slot_ref=data["transition_slot_ref"],
            source_application_ref=data["source_application_ref"],
            event_type_ref=data["event_type_ref"],
            compatible_modes=tuple(data["compatible_modes"]),
            required_roles=tuple(data["required_roles"]),
            required_capabilities=tuple(data["required_capabilities"]),
            required_permissions=tuple(data["required_permissions"]),
            adapter_ref=data["adapter_ref"],
        )


def extract_transition_previews(
    program: Any, context: Any
) -> tuple[TransitionPreview, ...]:
    """Extract transition previews from a program's propose_transition actions.

    Returns a tuple of TransitionPreview objects for each valid
    propose_transition action in the program.  Invalid transitions
    (unknown slot, unknown application, frame mismatch) are silently
    skipped — the verifier's replay logic handles error reporting.
    """
    previews: list[TransitionPreview] = []
    for action in program.actions:
        if action.action_type != "propose_transition":
            continue
        slot_ref, source_ref = action.arguments
        slot = context.transition(slot_ref)
        if slot is None:
            continue
        # Find the application frame for the source application
        frame = None
        for a in program.actions:
            if (
                a.action_type == "instantiate_operator"
                and a.arguments[0] == source_ref
            ):
                frame = context.frame(a.arguments[1])
                break
        if frame is None or slot.application_frame_ref != frame.slot_ref:
            continue
        previews.append(
            TransitionPreview(
                preview_ref=action.action_ref,
                transition_slot_ref=slot.slot_ref,
                source_application_ref=source_ref,
                event_type_ref=slot.event_type_ref,
                compatible_modes=slot.compatible_modes,
                required_roles=slot.required_roles,
                required_capabilities=slot.required_capabilities,
                required_permissions=slot.required_permissions,
                adapter_ref=slot.adapter_ref,
            )
        )
    return tuple(previews)
