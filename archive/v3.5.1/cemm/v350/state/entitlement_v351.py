"""Entitled state-space compilation and durable-value decoding."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import StateDimensionSchema, StateValueSchema, semantic_fingerprint
from ..storage.model import AssignmentStatus, RecordKind, StateAssignment
from .algebra_v351 import StateAlgebraV351, StateDomainCompilerV351, _pin_from_doc
from .model_v351 import (
    EntitledStateVariableV351, ProbabilityPointV351, ProcessStatus, RelationStateRoleBindingV351,
    StateDomainKind, StateModelError, StateValueV351,
)


class EntitledStateSpaceCompilerV351:
    """Build finite typed state variables only from exact entitled dimensions.

    `dimension_records` must already be filtered by the Phase-4 entitlement/applicability
    closure. This compiler never scans all schemas per referent and never invents facets.
    """

    def __init__(self, store) -> None:
        self.store = store
        self.algebra = StateAlgebraV351()

    def compile(
        self,
        *,
        holder_ref: str,
        dimension_records: Iterable[StateDimensionSchema],
        context_ref: str,
        at_time: str | None,
        entitlement_proof_refs: tuple[str, ...] = (),
    ) -> tuple[EntitledStateVariableV351, ...]:
        result = []
        for dimension in sorted(dimension_records, key=lambda item: (item.schema_ref, item.revision)):
            domain = StateDomainCompilerV351.compile(dimension)
            dimension_pin = ExactAuthorityPin(
                "state_dimension", "cemm:schema", dimension.schema_ref, dimension.revision,
                dimension.content_fingerprint, dimension.scope_ref,
            )
            assignments = self._active_assignments(
                holder_ref, dimension.schema_ref, dimension.revision, context_ref, at_time,
            )
            values = [self.assignment_value(item.payload, dimension, store=self.store) for item in assignments]
            if len(values) > 1:
                raise StateModelError(
                    f"state dimension has multiple active current assignments:{holder_ref}:{dimension.schema_ref}"
                )
            value = values[0] if values else None
            if value is not None:
                self.algebra.validate_value(domain, value)
            result.append(EntitledStateVariableV351(
                state_variable_ref="state-variable:" + semantic_fingerprint(
                    "entitled-state-variable-v351",
                    (holder_ref, dimension_pin.key, context_ref, at_time), 32,
                ),
                holder_ref=holder_ref,
                dimension_pin=dimension_pin,
                domain=domain,
                value=value,
                context_ref=context_ref,
                valid_time_ref=at_time,
                entitlement_proof_refs=entitlement_proof_refs,
                evidence_refs=tuple(sorted({ref for item in assignments for ref in item.payload.evidence_refs})),
            ))
        return tuple(result)

    def _active_assignments(self, holder_ref, dimension_ref, dimension_revision, context_ref, at_time):
        latest = {}
        for stored in self.store.records(RecordKind.STATE_ASSIGNMENT):
            item = stored.payload
            if not isinstance(item, StateAssignment):
                continue
            if (
                item.holder_ref != holder_ref
                or item.dimension_ref != dimension_ref
                or item.dimension_revision != dimension_revision
                or item.context_ref not in {"global", context_ref}
            ):
                continue
            prior = latest.get(item.assignment_ref)
            if prior is None or stored.revision > prior.revision:
                latest[item.assignment_ref] = stored
        result = []
        for stored in latest.values():
            item = stored.payload
            if item.status != AssignmentStatus.ACTIVE:
                continue
            # Existing store helper handles precise interval queries elsewhere.  Here the
            # caller may omit time; when time is supplied, compare only ISO-like lexical
            # timestamps after validating basic ordering. This keeps the algebra independent
            # of wall-clock reads.
            if at_time is not None:
                if item.valid_from and at_time < item.valid_from:
                    continue
                if item.valid_to and at_time >= item.valid_to:
                    continue
            result.append(stored)
        ordered = tuple(sorted(result, key=lambda item: (item.record_ref, item.revision)))
        exact = tuple(item for item in ordered if item.payload.context_ref == context_ref)
        fallback = tuple(item for item in ordered if item.payload.context_ref == "global")
        return exact if exact else fallback

    @staticmethod
    def assignment_value(
        assignment: StateAssignment,
        dimension: StateDimensionSchema,
        *,
        store=None,
    ) -> StateValueV351:
        document = dict(getattr(assignment, "value_document", {}) or {})
        if document:
            value = state_value_from_document(document)
            if value.categorical_pin is not None:
                if (
                    assignment.value_ref != value.categorical_pin.ref
                    or assignment.value_revision != value.categorical_pin.revision
                ):
                    raise StateModelError(
                        "rich categorical assignment ref/revision differs from exact value document"
                    )
            elif assignment.value_ref != value.value_ref or assignment.value_revision != 1:
                raise StateModelError(
                    "rich state assignment content identity differs from value_document"
                )
            return value
        # Backwards-compatible categorical/ordered assignment. Resolve the real exact
        # StateValueSchema authority when a store is available; never fabricate a content hash.
        value_schema = None
        if store is not None:
            stored = store.get_record(RecordKind.SCHEMA, assignment.value_ref, assignment.value_revision)
            if stored is not None and isinstance(stored.payload, StateValueSchema):
                value_schema = stored.payload
        if value_schema is None:
            raise StateModelError(
                "legacy categorical assignment requires resolvable exact StateValueSchema authority"
            )
        if value_schema.dimension_ref != dimension.schema_ref:
            raise StateModelError(
                "legacy categorical assignment value belongs to a different state dimension"
            )
        value_pin = ExactAuthorityPin(
            "state_value", "cemm:schema", value_schema.schema_ref, value_schema.revision,
            value_schema.content_fingerprint, value_schema.scope_ref,
        )
        domain = StateDomainCompilerV351.compile(dimension)
        if domain.kind not in {StateDomainKind.CATEGORICAL, StateDomainKind.ORDERED}:
            raise StateModelError(
                "non-categorical state assignment requires value_document; schema ref alone is insufficient"
            )
        return StateValueV351(domain.kind, categorical_pin=value_pin, evidence_refs=assignment.evidence_refs)


def state_value_from_document(document: Mapping[str, Any]) -> StateValueV351:
    if str(document.get("model", "")) != "state-value-v351":
        raise StateModelError("unknown state value document model")
    return StateValueV351(
        domain_kind=StateDomainKind(str(document["domain_kind"])),
        categorical_pin=_pin_from_doc(document.get("categorical_pin")),
        scalar_value=None if document.get("scalar_value") is None else float(document["scalar_value"]),
        vector_value=tuple(float(item) for item in document.get("vector_value", ())),
        relation_pin=_pin_from_doc(document.get("relation_pin")),
        relation_bindings=tuple(
            RelationStateRoleBindingV351(
                _pin_from_doc(item.get("role_pin") if isinstance(item, Mapping) else item[0]),
                str(item.get("participant_ref") if isinstance(item, Mapping) else item[1]),
            )
            for item in document.get("relation_bindings", ())
        ),
        set_members=tuple(map(str, document.get("set_members", ()))),
        process_pin=_pin_from_doc(document.get("process_pin")),
        process_status=(None if document.get("process_status") is None else ProcessStatus(str(document["process_status"]))),
        process_progress=None if document.get("process_progress") is None else float(document["process_progress"]),
        probability_mass=tuple(
            ProbabilityPointV351(state_value_from_document(dict(a)), float(b))
            for a, b in document.get("probability_mass", ())
        ),
        unit_pin=_pin_from_doc(document.get("unit_pin")),
        coordinate_frame_pin=_pin_from_doc(document.get("coordinate_frame_pin")),
        evidence_refs=tuple(map(str, document.get("evidence_refs", ()))),
    )


__all__ = ["EntitledStateSpaceCompilerV351", "state_value_from_document"]
