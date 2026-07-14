"""SituationFrameBuilder — builds SituationFrame from MeaningPerceptPacket.

Implements §8.3 from cemm_foundational_fixes.md and §9 from architecture.md.

The builder generates EventSchemas from the Semantic Schema Kernel's
ActionOperatorRegistry. Role binding is delegated to FrameBinder, which
replaces first-match slot filling with traceable candidate scoring.
"""

from __future__ import annotations

import uuid

from ...types.meaning_percept import (
    MeaningPerceptPacket,
    SituationFrame,
    OutcomeAtom,
    EventSchema,
)
from ...types.context_kernel import ContextKernel
from .frame_binder import FrameBinder
from .semantic_schema_kernel import SemanticSchemaKernel, get_kernel


def _event_schema_from_kernel(action_key: str, kernel: SemanticSchemaKernel) -> EventSchema:
    """Build an EventSchema from an ActionOperatorSchema in the kernel."""
    schema = kernel.action_operators.get(action_key)
    if schema is None:
        return EventSchema(action_key=action_key, confidence=0.5)

    outcomes: list[OutcomeAtom] = []
    for delta in schema.state_deltas:
        target = delta.get("target", "actor")
        dimension = delta.get("dimension", "")
        direction = delta.get("direction", "unknown")
        confidence = float(delta.get("confidence", 0.7))
        outcomes.append(OutcomeAtom(
            affected_entity_role=target,
            changed_dimension=dimension,
            direction=direction,
            confidence=confidence,
            event_key=action_key,
            state_changes=[{"dimension": dimension, "direction": direction}],
        ))

    slots = schema.slots
    actor_role = None
    target_role = None
    object_role = None
    destination_role = None
    recipient_role = None
    if "actor" in slots:
        kinds = slots["actor"].get("allowed_entity_kinds", [])
        if "self" in kinds or "autonomous_agent" in kinds:
            actor_role = "self"
        elif "person" in kinds:
            actor_role = "actor"
    if "target" in slots:
        target_role = "target"
    if "object" in slots:
        object_role = "object"
    if "destination" in slots:
        destination_role = "destination"
    if "recipient" in slots:
        recipient_role = "recipient"

    aliases = schema.aliases.get("en", [])

    return EventSchema(
        schema_key=schema.action_key,
        actor_role=actor_role,
        action_key=action_key,
        object_role=object_role,
        target_role=target_role,
        destination_role=destination_role,
        recipient_role=recipient_role,
        expected_outcomes=outcomes,
        examples=aliases,
        source="schema_kernel",
        confidence=0.8,
    )


def _build_seed_schemas(kernel: SemanticSchemaKernel) -> dict[str, EventSchema]:
    """Build all seed EventSchemas from the kernel's ActionOperatorRegistry."""
    schemas: dict[str, EventSchema] = {}
    for action_key in kernel.action_operators.all_action_keys():
        schemas[action_key] = _event_schema_from_kernel(action_key, kernel)
    return schemas


class SituationFrameBuilder:
    """Builds SituationFrame from MeaningPerceptPacket + ContextKernel."""

    def __init__(self, schema_kernel: SemanticSchemaKernel | None = None) -> None:
        self._kernel = schema_kernel or get_kernel()
        self._schemas = _build_seed_schemas(self._kernel)
        self._frame_binder = FrameBinder(
            schemas=self._schemas,
            schema_kernel=self._kernel,
        )

    def build(
        self,
        percept: MeaningPerceptPacket,
        kernel: ContextKernel,
    ) -> SituationFrame:
        """Build a SituationFrame from the meaning percept and kernel context.

        Delegates to FrameBinder for atom-based role binding with traceable
        candidate scoring. The old first-match slot filling is replaced by
        scored role assignment, but the public API remains stable.
        """
        frame = SituationFrame(
            id=uuid.uuid4().hex[:16],
            signal_id=percept.signal_id,
            context_id=percept.context_id,
        )
        return self._frame_binder.bind(percept, kernel, base_frame=frame).frame

    def get_schema(self, action_key: str) -> EventSchema | None:
        """Retrieve a seed event schema by action key."""
        return self._schemas.get(action_key)
