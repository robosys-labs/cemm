"""Stage-13 conservative persistence of selected UOL structure.

This module persists semantic *representation* without granting world truth or
state-transition authority. It is deliberately separate from epistemic admission
and transition-effect commits.
"""
from __future__ import annotations

from dataclasses import dataclass

from .epistemic_pipeline import AttributedClaimLineage
from .schema.model import PortFillerClass, semantic_fingerprint
from .storage import (
    EvidenceRecord,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
    SemanticStore,
    StoreSnapshot,
    encode_record,
    record_fingerprints,
    record_ref,
    record_revision,
)
from .uol.model import FillerRef, OccurrenceStatus, UOLGraph


@dataclass(frozen=True, slots=True)
class SemanticCommitPlan:
    patch: GraphPatch | None
    persisted_refs: tuple[str, ...]
    deferred_refs: tuple[str, ...]


class SelectedUOLCommitPlanner:
    """Persist a closed selected-UOL subset without silently upgrading authority.

    Cycle-local variables, coordination groups and scope relations do not yet have
    generic durable record contracts. Any application that depends on those
    structures is therefore deferred, and that deferment propagates to dependent
    applications, propositions, claims and events. This avoids durable half-graphs.
    """

    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def plan(
        self,
        graph: UOLGraph,
        *,
        context_ref: str,
        permission_ref: str,
        source_ref: str,
        evidence_records: tuple[EvidenceRecord, ...] = (),
        claim_lineages: tuple[AttributedClaimLineage, ...] = (),
        snapshot: StoreSnapshot | None = None,
    ) -> SemanticCommitPlan:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.plan(
                    graph,
                    context_ref=context_ref,
                    permission_ref=permission_ref,
                    source_ref=source_ref,
                    evidence_records=evidence_records,
                    claim_lineages=claim_lineages,
                    snapshot=pinned,
                )
        self.store.assert_snapshot(snapshot)
        candidates: list[tuple[RecordKind, object, tuple[RecordDependency, ...]]] = []
        deferred: set[str] = set()

        def durable(kind: RecordKind, ref: str, revision: int | None = None):
            return self.store.get_record(kind, ref, revision, snapshot=snapshot)

        def exact_dependency(
            kind: RecordKind,
            ref: str,
            revision: int | None = None,
            label: str = "semantic",
        ) -> RecordDependency | None:
            stored = durable(kind, ref, revision)
            if stored is None:
                return None
            return RecordDependency(
                kind,
                stored.record_ref,
                stored.revision,
                stored.record_fingerprint,
                label,
            )

        def staged_dependency(kind: RecordKind, payload: object, label: str) -> RecordDependency:
            _content_fp, fp = record_fingerprints(kind, payload)
            return RecordDependency(
                kind,
                record_ref(kind, payload),
                record_revision(kind, payload),
                fp,
                label,
            )

        def append_candidate(
            kind: RecordKind,
            payload: object,
            dependencies: tuple[RecordDependency, ...] = (),
        ) -> bool:
            ref = record_ref(kind, payload)
            revision = record_revision(kind, payload)
            existing = durable(kind, ref, revision)
            if existing is not None:
                _require_same(kind, existing, payload)
                return False
            candidates.append((kind, payload, dependencies))
            return True

        staged_evidence = {item.evidence_ref: item for item in evidence_records}
        for item in sorted(evidence_records, key=lambda value: value.evidence_ref):
            append_candidate(RecordKind.EVIDENCE, item)

        # Specialized proposition/claim/event referents are committed only together
        # with their specialization record. Persisting their bare identity first
        # would create a durable half-graph. Ordinary selected identities are safe.
        specialized_refs = set(graph.propositions) | set(graph.claims) | set(graph.events)
        for referent in sorted(graph.referents.values(), key=lambda item: item.referent_ref):
            if referent.referent_ref not in specialized_refs:
                append_candidate(RecordKind.REFERENT, referent)

        # Applications participating in unresolved scope/coordination cannot be
        # made durable independently without losing graph semantics.
        unsafe_apps: set[str] = set()
        for relation in graph.scope_relations:
            unsafe_apps.add(relation.operator_application_ref)
            if relation.scoped_ref.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                unsafe_apps.add(relation.scoped_ref.ref)
        for group in graph.coordination_groups.values():
            for member in group.members:
                if member.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                    unsafe_apps.add(member.ref)

        for application in graph.applications.values():
            if any(binding.open_binding_purpose is not None for binding in application.bindings):
                unsafe_apps.add(application.application_ref)
                continue
            for binding in application.bindings:
                for filler in binding.fillers:
                    if not isinstance(filler, FillerRef):
                        continue
                    if filler.filler_class in {
                        PortFillerClass.SEMANTIC_VARIABLE,
                        PortFillerClass.COORDINATION_GROUP,
                    }:
                        unsafe_apps.add(application.application_ref)

        # Propagate unresolved semantic-application dependencies to a fixed point.
        changed = True
        while changed:
            changed = False
            for application in graph.applications.values():
                if application.application_ref in unsafe_apps:
                    continue
                for binding in application.bindings:
                    for filler in binding.fillers:
                        if not isinstance(filler, FillerRef):
                            continue
                        if filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                            if (
                                filler.ref in unsafe_apps
                                or (
                                    filler.ref not in graph.applications
                                    and durable(RecordKind.SEMANTIC_APPLICATION, filler.ref) is None
                                )
                            ):
                                unsafe_apps.add(application.application_ref)
                                changed = True
                                break
                        elif filler.filler_class == PortFillerClass.REFERENT:
                            # A selected application may not durably depend on a
                            # specialized referent whose proposition/claim/event
                            # specialization is not already durable. Those apps are
                            # deferred rather than creating bare-reference cycles.
                            if filler.ref in specialized_refs:
                                specialization_exists = any((
                                    durable(RecordKind.PROPOSITION, filler.ref),
                                    durable(RecordKind.CLAIM_OCCURRENCE, filler.ref),
                                    durable(RecordKind.EVENT_OCCURRENCE, filler.ref),
                                ))
                                if not specialization_exists:
                                    unsafe_apps.add(application.application_ref)
                                    changed = True
                                    break
                            elif filler.ref not in graph.referents and durable(RecordKind.REFERENT, filler.ref) is None:
                                unsafe_apps.add(application.application_ref)
                                changed = True
                                break
                    if application.application_ref in unsafe_apps:
                        break

        persistable_apps: set[str] = set()
        for application in sorted(graph.applications.values(), key=lambda item: item.application_ref):
            if application.application_ref in unsafe_apps:
                deferred.add(application.application_ref)
                continue
            schema_dep = exact_dependency(
                RecordKind.SCHEMA,
                application.schema_ref,
                application.schema_revision,
                "application_schema",
            )
            if schema_dep is None:
                deferred.add(application.application_ref)
                continue
            deps: list[RecordDependency] = [schema_dep]
            structurally_closed = True
            for binding in application.bindings:
                for filler in binding.fillers:
                    if not isinstance(filler, FillerRef):
                        continue
                    if filler.filler_class == PortFillerClass.REFERENT:
                        payload = graph.referents.get(filler.ref)
                        dep = (
                            staged_dependency(RecordKind.REFERENT, payload, "application_referent")
                            if payload is not None
                            else exact_dependency(RecordKind.REFERENT, filler.ref, label="application_referent")
                        )
                    elif filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                        payload = graph.applications.get(filler.ref)
                        if filler.ref in unsafe_apps:
                            dep = None
                        else:
                            dep = (
                                staged_dependency(RecordKind.SEMANTIC_APPLICATION, payload, "application_content")
                                if payload is not None
                                else exact_dependency(RecordKind.SEMANTIC_APPLICATION, filler.ref, label="application_content")
                            )
                    elif filler.filler_class == PortFillerClass.QUOTED_LITERAL:
                        dep = True  # literals are embedded values, not durable refs
                    else:
                        dep = None
                    if dep is None:
                        structurally_closed = False
                        break
                    if dep is not True:
                        deps.append(dep)
                if not structurally_closed:
                    break
            if not structurally_closed:
                deferred.add(application.application_ref)
                unsafe_apps.add(application.application_ref)
                continue
            append_candidate(RecordKind.SEMANTIC_APPLICATION, application, tuple(deps))
            persistable_apps.add(application.application_ref)

        persistable_props: set[str] = set()
        for proposition in sorted(graph.propositions.values(), key=lambda item: item.proposition_ref):
            deps: list[RecordDependency] = []
            ok = True
            for content in proposition.content_refs:
                if content.filler_class != PortFillerClass.SEMANTIC_APPLICATION:
                    ok = False
                    break
                payload = graph.applications.get(content.ref)
                if payload is not None:
                    if content.ref not in persistable_apps:
                        ok = False
                        break
                    dep = staged_dependency(
                        RecordKind.SEMANTIC_APPLICATION,
                        payload,
                        "proposition_content",
                    )
                else:
                    dep = exact_dependency(
                        RecordKind.SEMANTIC_APPLICATION,
                        content.ref,
                        label="proposition_content",
                    )
                    if dep is None:
                        ok = False
                        break
                deps.append(dep)
            if not ok:
                deferred.add(proposition.proposition_ref)
                continue
            base = graph.referents.get(proposition.proposition_ref)
            if base is not None:
                append_candidate(RecordKind.REFERENT, base)
            append_candidate(RecordKind.PROPOSITION, proposition, tuple(deps))
            persistable_props.add(proposition.proposition_ref)

        persistable_claims: set[str] = set()
        for claim in sorted(graph.claims.values(), key=lambda item: item.claim_ref):
            prop = graph.propositions.get(claim.proposition_ref)
            if prop is not None:
                if claim.proposition_ref not in persistable_props:
                    deferred.add(claim.claim_ref)
                    continue
                dep = staged_dependency(RecordKind.PROPOSITION, prop, "claim_proposition")
            else:
                dep = exact_dependency(
                    RecordKind.PROPOSITION,
                    claim.proposition_ref,
                    label="claim_proposition",
                )
                if dep is None:
                    deferred.add(claim.claim_ref)
                    continue
            base = graph.referents.get(claim.claim_ref)
            if base is not None:
                append_candidate(RecordKind.REFERENT, base)
            append_candidate(RecordKind.CLAIM_OCCURRENCE, claim, (dep,))
            persistable_claims.add(claim.claim_ref)

        # ClaimRecord/ClaimHistory preserve attribution lineage only. They never
        # imply actual-world admission and require exact durable/staged evidence.
        for lineage in sorted(claim_lineages, key=lambda item: item.claim_record.claim_record_ref):
            claim = lineage.occurrence
            occurrence_payload = graph.claims.get(claim.claim_ref)
            proposition_payload = graph.propositions.get(claim.proposition_ref)
            if (
                occurrence_payload is None
                or proposition_payload is None
                or claim.claim_ref not in persistable_claims
                or claim.proposition_ref not in persistable_props
            ):
                deferred.add(lineage.claim_record.claim_record_ref)
                continue
            occurrence_dep = staged_dependency(
                RecordKind.CLAIM_OCCURRENCE,
                occurrence_payload,
                "claim_lineage_occurrence",
            )
            proposition_dep = staged_dependency(
                RecordKind.PROPOSITION,
                proposition_payload,
                "claim_lineage_proposition",
            )
            evidence_deps: list[RecordDependency] = []
            for evidence_ref in lineage.history_record.evidence_refs:
                payload = staged_evidence.get(evidence_ref)
                dep = (
                    staged_dependency(RecordKind.EVIDENCE, payload, "claim_lineage_evidence")
                    if payload is not None
                    else exact_dependency(
                        RecordKind.EVIDENCE,
                        evidence_ref,
                        label="claim_lineage_evidence",
                    )
                )
                if dep is None:
                    deferred.add(lineage.claim_record.claim_record_ref)
                    evidence_deps = []
                    break
                evidence_deps.append(dep)
            if lineage.history_record.evidence_refs and not evidence_deps:
                continue
            append_candidate(
                RecordKind.CLAIM_RECORD,
                lineage.claim_record,
                (occurrence_dep, proposition_dep, *evidence_deps),
            )
            record_dep = staged_dependency(
                RecordKind.CLAIM_RECORD,
                lineage.claim_record,
                "claim_history_record",
            )
            append_candidate(
                RecordKind.CLAIM_HISTORY,
                lineage.history_record,
                (record_dep, *evidence_deps),
            )

        for event in sorted(graph.events.values(), key=lambda item: item.event_ref):
            if event.occurrence_status != OccurrenceStatus.MENTIONED:
                # Stronger occurrence statuses require observation/admission authority.
                deferred.add(event.event_ref)
                continue
            app = graph.applications.get(event.participant_application_ref)
            if app is not None:
                if app.application_ref not in persistable_apps:
                    deferred.add(event.event_ref)
                    continue
                dep = staged_dependency(
                    RecordKind.SEMANTIC_APPLICATION,
                    app,
                    "event_participants",
                )
            else:
                dep = exact_dependency(
                    RecordKind.SEMANTIC_APPLICATION,
                    event.participant_application_ref,
                    label="event_participants",
                )
                if dep is None:
                    deferred.add(event.event_ref)
                    continue
            base = graph.referents.get(event.event_ref)
            if base is not None:
                append_candidate(RecordKind.REFERENT, base)
            append_candidate(RecordKind.EVENT_OCCURRENCE, event, (dep,))

        operations: list[PatchOperation] = []
        persisted: list[str] = []
        seen: set[tuple[RecordKind, str, int]] = set()
        for index, (kind, payload, dependencies) in enumerate(candidates):
            ref = record_ref(kind, payload)
            revision = record_revision(kind, payload)
            key = (kind, ref, revision)
            if key in seen:
                continue
            seen.add(key)
            operations.append(
                PatchOperation(
                    operation_ref="patch-operation:selected-uol:" + semantic_fingerprint(
                        "selected-uol-operation", (kind.value, ref, revision, index), 20
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=kind,
                    target_ref=ref,
                    record_revision=revision,
                    payload=encode_record(kind, payload),
                    dependencies=tuple(dependencies),
                    reason="persist closed selected semantic representation without granting truth or state authority",
                )
            )
            persisted.append(ref)

        if not operations:
            return SemanticCommitPlan(None, (), tuple(sorted(deferred)))
        patch = GraphPatch(
            patch_ref="graph-patch:selected-uol:" + semantic_fingerprint(
                "selected-uol-patch",
                (graph.graph_ref, snapshot.fingerprint, tuple(item.operation_ref for item in operations)),
                24,
            ),
            context_ref=context_ref,
            scope_ref="v350:selected-meaning",
            source_ref=source_ref,
            permission_ref=permission_ref,
            operations=tuple(operations),
            expected_store_revision=snapshot.store_revision,
            evidence_refs=tuple(sorted(set(graph.evidence_refs))),
            validation_requirements=(
                "selected_uol_is_representation_not_world_truth",
                "selected_uol_durable_dependency_closure",
                "mentioned_events_do_not_trigger_state_effects",
                "no_implicit_epistemic_admission",
            ),
            metadata={
                "stage": 13,
                "actual_world_admission": False,
                "state_transition": False,
                "source_graph_ref": graph.graph_ref,
                "deferred_refs": tuple(sorted(deferred)),
            },
        )
        return SemanticCommitPlan(
            patch,
            tuple(sorted(set(persisted))),
            tuple(sorted(deferred)),
        )


def _require_same(kind: RecordKind, stored, payload: object) -> None:
    _content_fp, expected = record_fingerprints(kind, payload)
    if stored.record_fingerprint != expected:
        raise ValueError(
            f"selected UOL conflicts with existing {kind.value}:"
            f"{stored.record_ref}@{stored.revision}"
        )
