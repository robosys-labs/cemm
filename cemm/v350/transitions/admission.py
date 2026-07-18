"""Independent event-admission gate for Phase-11 transitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..storage.model import (
    AdmissionDecision,
    AdmissionLifecycleStatus,
    EpistemicAdmissionRecord,
    RecordKind,
)
from ..uol.model import (
    EventOccurrence,
    FillerRef,
    Polarity,
    PortFillerClass,
    PropositionReferent,
    QuotedLiteral,
    SemanticApplication,
)


class Resolver(Protocol):
    def resolve(self, record_kind: RecordKind, record_ref: str, revision: int | None = None) -> Any | None: ...
    def records(self, record_kind: RecordKind) -> tuple[Any, ...]: ...


@dataclass(frozen=True, slots=True)
class EventAdmissionAssessment:
    admitted: bool
    admission_pins: tuple[tuple[str, int], ...]
    evidence_refs: tuple[str, ...]
    confidence: float
    reasons: tuple[str, ...]


    @property
    def admission_refs(self) -> tuple[str, ...]:
        return tuple(ref for ref, _revision in self.admission_pins)


class EventAdmissionGate:
    """Require exact active support admission for a structurally equivalent event.

    A syntactically valid event, observed/claimed status, or a non-empty string in
    ``EventOccurrence.admission_refs`` is never sufficient.  The admission must
    resolve to an active Phase-10 support admission whose positively asserted
    source-context proposition contains an event application with the same exact
    schema revision and semantic bindings as the target-context event application.

    The source and target application refs are intentionally allowed to differ:
    epistemic admission is the explicit bridge that permits attributed content to
    be re-instantiated in the admitted target context.  Context is *not* ignored
    silently; the source and target contexts are checked against the admission.
    """

    def __init__(self, resolver: Resolver) -> None:
        self._resolver = resolver

    def assess(
        self,
        event: EventOccurrence,
        *,
        participant_application_revision: int | None = None,
    ) -> EventAdmissionAssessment:
        reasons: list[str] = []
        evidence: set[str] = set()
        accepted: list[tuple[str, int]] = []
        accepted_confidences: list[float] = []
        if not event.admission_refs:
            return EventAdmissionAssessment(False, (), (), 0.0, ("event_has_no_admission_lineage",))

        target_stored = self._resolver.resolve(
            RecordKind.SEMANTIC_APPLICATION,
            event.participant_application_ref,
            participant_application_revision,
        )
        if target_stored is None or not isinstance(target_stored.payload, SemanticApplication):
            return EventAdmissionAssessment(
                False,
                (),
                (),
                0.0,
                ("event_participant_application_unresolved",),
            )
        target_application = target_stored.payload
        if target_application.context_ref != event.context_ref:
            return EventAdmissionAssessment(
                False,
                (),
                (),
                0.0,
                ("event_participant_application_context_mismatch",),
            )
        if (
            target_application.schema_ref != event.event_schema_ref
            or target_application.schema_revision != event.event_schema_revision
        ):
            return EventAdmissionAssessment(
                False,
                (),
                (),
                0.0,
                ("event_participant_application_schema_mismatch",),
            )

        for admission_ref in event.admission_refs:
            stored = self._resolver.resolve(RecordKind.EPISTEMIC_ADMISSION, admission_ref)
            if stored is None or not isinstance(stored.payload, EpistemicAdmissionRecord):
                reasons.append(f"unresolved_admission:{admission_ref}")
                continue
            admission = stored.payload
            if admission.lifecycle_status != AdmissionLifecycleStatus.ACTIVE:
                reasons.append(f"inactive_admission:{admission_ref}")
                continue
            if admission.decision != AdmissionDecision.ADMIT_SUPPORT:
                reasons.append(f"non_support_admission:{admission_ref}")
                continue
            if admission.target_context_ref != event.context_ref:
                reasons.append(f"admission_context_mismatch:{admission_ref}")
                continue
            if self._effectively_retracted(admission):
                reasons.append(f"retracted_admission:{admission_ref}")
                continue
            proposition_stored = self._resolver.resolve(RecordKind.PROPOSITION, admission.proposition_ref)
            if proposition_stored is None or not isinstance(proposition_stored.payload, PropositionReferent):
                reasons.append(f"admission_proposition_unresolved:{admission_ref}")
                continue
            proposition = proposition_stored.payload
            if proposition.polarity != Polarity.POSITIVE:
                reasons.append(f"negative_proposition_cannot_admit_event:{admission_ref}")
                continue
            if proposition.context_ref != admission.source_context_ref:
                reasons.append(f"admission_source_context_mismatch:{admission_ref}")
                continue
            if not self._contains_equivalent_source_application(
                proposition,
                target_application,
                admission.source_context_ref,
            ):
                reasons.append(f"admission_does_not_support_equivalent_event:{admission_ref}")
                continue
            accepted.append((admission_ref, stored.revision))
            accepted_confidences.append(admission.confidence)
            evidence.update(admission.evidence_refs)

        return EventAdmissionAssessment(
            admitted=bool(accepted),
            admission_pins=tuple(sorted(accepted)),
            evidence_refs=tuple(sorted(evidence)),
            confidence=min(accepted_confidences) if accepted_confidences else 0.0,
            reasons=tuple(sorted(reasons)),
        )

    def _contains_equivalent_source_application(
        self,
        proposition: PropositionReferent,
        target: SemanticApplication,
        source_context_ref: str,
    ) -> bool:
        for item in proposition.content_refs:
            if not isinstance(item, FillerRef) or item.filler_class != PortFillerClass.SEMANTIC_APPLICATION:
                continue
            source_stored = self._resolver.resolve(RecordKind.SEMANTIC_APPLICATION, item.ref)
            if source_stored is None or not isinstance(source_stored.payload, SemanticApplication):
                continue
            source = source_stored.payload
            if source.context_ref != source_context_ref:
                continue
            if self._semantic_application_signature(source) == self._semantic_application_signature(target):
                return True
        return False

    @staticmethod
    def _semantic_application_signature(application: SemanticApplication) -> tuple[Any, ...]:
        """Compare meaning-bearing application structure while excluding context/IDs/proof.

        Admission explicitly supplies the context bridge.  Exact schema revision,
        polarity, valid-time reference, port ordering, filler classes/identities,
        open-binding purpose, and orderedness remain meaning-bearing.
        """

        bindings: list[tuple[Any, ...]] = []
        for binding in sorted(application.bindings, key=lambda item: item.port_ref):
            fillers: list[tuple[Any, ...]] = []
            for filler in binding.fillers:
                if isinstance(filler, FillerRef):
                    fillers.append(("ref", filler.filler_class.value, filler.ref))
                elif isinstance(filler, QuotedLiteral):
                    fillers.append(("literal", filler.surface, filler.language_tag))
                else:  # pragma: no cover - defensive against future filler families
                    fillers.append(("unknown", repr(filler)))
            bindings.append(
                (
                    binding.port_ref,
                    tuple(fillers),
                    binding.ordered,
                    binding.open_binding_purpose.value if binding.open_binding_purpose is not None else None,
                )
            )
        return (
            application.schema_ref,
            application.schema_revision,
            application.use_operation.value,
            application.polarity.value,
            application.valid_time_ref,
            tuple(bindings),
        )

    def _effectively_retracted(self, admission: EpistemicAdmissionRecord) -> bool:
        for stored in self._resolver.records(RecordKind.EPISTEMIC_ADMISSION):
            item = stored.payload
            if not isinstance(item, EpistemicAdmissionRecord):
                continue
            if (
                item.decision == AdmissionDecision.RETRACT
                and item.lifecycle_status == AdmissionLifecycleStatus.ACTIVE
                and item.retracts_admission_ref == admission.admission_ref
                and item.proposition_ref == admission.proposition_ref
                and item.target_context_ref == admission.target_context_ref
                and set(item.source_refs).intersection(admission.source_refs)
            ):
                return True
        return False
