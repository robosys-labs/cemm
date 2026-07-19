"""Stage-8 discourse/claim/event/gap classification and attribution transform.

The implementation is language-neutral. It consumes selected UOL plus exact
schema metadata; it never inspects surface words. Claim-bearing discourse acts
move their content into a distinct attributed context and create explicit
PropositionReferent + ClaimOccurrence structure. This prevents ordinary user
assertions from remaining as unwrapped actual-context applications while still
avoiding any actual-world admission.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .schema.model import OpenBindingPurpose, PortFillerClass, SchemaClass, StorageKind, semantic_fingerprint
from .storage import SemanticStore, StoreSnapshot
from .uol.model import (
    ApplicationBinding,
    ClaimForce,
    ClaimOccurrence,
    FillerRef,
    IdentityStatus,
    PropositionReferent,
    Referent,
    SemanticApplication,
    UOLGraph,
)


@dataclass(frozen=True, slots=True)
class DiscourseActEvidence:
    application_ref: str
    schema_ref: str
    schema_revision: int
    claim_force: ClaimForce | None
    content_port_ref: str | None
    content_refs: tuple[str, ...]
    speaker_refs: tuple[str, ...]
    addressee_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DiscourseClassification:
    discourse_acts: tuple[DiscourseActEvidence, ...]
    query_application_refs: tuple[str, ...]
    event_refs: tuple[str, ...]
    claim_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    requires_attribution_compilation: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    @property
    def has_explicit_force(self) -> bool:
        return bool(self.discourse_acts)


@dataclass(frozen=True, slots=True)
class AttributionResult:
    graph: UOLGraph
    compiled_claim_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


class DiscourseClassifier:
    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def classify(self, graph: UOLGraph, *, snapshot: StoreSnapshot | None = None) -> DiscourseClassification:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.classify(graph, snapshot=pinned)
        self.store.assert_snapshot(snapshot)
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)

        acts: list[DiscourseActEvidence] = []
        queries: set[str] = set()
        needs_attribution: set[str] = set()
        evidence: set[str] = set(graph.evidence_refs)

        for application in graph.applications.values():
            evidence.update(application.evidence_refs)
            if any(binding.open_binding_purpose == OpenBindingPurpose.QUERY for binding in application.bindings):
                queries.add(application.application_ref)
            try:
                schema = registry.schema(application.schema_ref, application.schema_revision)
            except KeyError:
                continue
            if schema.schema_class != SchemaClass.DISCOURSE_ACT:
                continue
            claim_force = _claim_force(schema.metadata.get("claim_force"))
            speaker_port = getattr(schema, "speaker_port_ref", None)
            addressee_port = getattr(schema, "addressee_port_ref", None)
            content_port = getattr(schema, "content_port_ref", None)
            speakers = _binding_refs(application, speaker_port)
            addressees = _binding_refs(application, addressee_port)
            content = _binding_refs(application, content_port)
            acts.append(DiscourseActEvidence(
                application.application_ref,
                schema.schema_ref,
                schema.revision,
                claim_force,
                content_port,
                content,
                speakers,
                addressees,
                tuple(sorted(set(application.evidence_refs))),
            ))
            if claim_force is not None and not _act_has_explicit_claim(graph, application.application_ref):
                needs_attribution.add(application.application_ref)

        unresolved = set(graph.unresolved_refs)
        if graph.root_refs and not acts and not queries:
            unresolved.add("discourse-force:unresolved")

        return DiscourseClassification(
            tuple(sorted(acts, key=lambda item: item.application_ref)),
            tuple(sorted(queries)),
            tuple(sorted(graph.events)),
            tuple(sorted(graph.claims)),
            tuple(sorted(unresolved)),
            tuple(sorted(needs_attribution)),
            tuple(sorted(evidence)),
        )

    def attribute_claims(
        self,
        graph: UOLGraph,
        classification: DiscourseClassification,
        *,
        context_ref: str,
        permission_ref: str,
        snapshot: StoreSnapshot | None = None,
    ) -> AttributionResult:
        """Compile claim-bearing discourse acts into attributed UOL.

        The transform is intentionally conservative: exactly one speaker and one
        or more semantic-application content fillers are required. Unsupported or
        multiply-referenced content remains a frontier instead of being guessed.
        """
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.attribute_claims(
                    graph, classification, context_ref=context_ref,
                    permission_ref=permission_ref, snapshot=pinned,
                )
        self.store.assert_snapshot(snapshot)

        applications = dict(graph.applications)
        referents = dict(graph.referents)
        propositions = dict(graph.propositions)
        claims = dict(graph.claims)
        events = dict(graph.events)
        roots = list(graph.root_refs)
        unresolved = set(graph.unresolved_refs)
        evidence = set(graph.evidence_refs)
        compiled: list[str] = []

        inbound = _application_inbound_refs(graph)
        for act in classification.discourse_acts:
            if act.claim_force is None or act.application_ref not in classification.requires_attribution_compilation:
                continue
            if len(act.speaker_refs) != 1 or not act.content_port_ref or not act.content_refs:
                unresolved.add(f"claim-attribution:{act.application_ref}:incomplete-discourse-roles")
                continue
            act_app = applications.get(act.application_ref)
            if act_app is None:
                unresolved.add(f"claim-attribution:{act.application_ref}:missing-act-application")
                continue

            # Attribution is transactional per discourse act. Validate the entire
            # content set first so a later ambiguity cannot leave a partially moved
            # proposition graph. Complex/shared structures remain an explicit frontier.
            invalid_content = False
            for content_ref in act.content_refs:
                if applications.get(content_ref) is None:
                    unresolved.add(f"claim-attribution:{act.application_ref}:{content_ref}:unsupported-content")
                    invalid_content = True
                    continue
                consumers = tuple(ref for ref in inbound.get(content_ref, ()) if ref != act.application_ref)
                if consumers:
                    unresolved.add(f"claim-attribution:{content_ref}:shared-content")
                    invalid_content = True
            if invalid_content:
                continue

            rewritten_content: list[FillerRef] = []
            act_compiled: list[str] = []
            for content_ref in act.content_refs:
                content = applications[content_ref]
                seed = (act.application_ref, content_ref, act.claim_force.value, act.speaker_refs[0])
                attributed_context = "context:attributed:" + semantic_fingerprint("attributed-context", seed, 24)
                attributed_app_ref = "application:attributed:" + semantic_fingerprint("attributed-application", seed, 24)
                attributed_app = replace(
                    content,
                    application_ref=attributed_app_ref,
                    context_ref=attributed_context,
                    metadata={**dict(content.metadata), "attributed_from": content.application_ref, "discourse_act_ref": act.application_ref},
                )
                proposition_ref = "referent:proposition:" + semantic_fingerprint("attributed-proposition", seed, 24)
                proposition_referent = Referent(
                    referent_ref=proposition_ref,
                    storage_kind=StorageKind.PROPOSITION,
                    identity_status=IdentityStatus.CANDIDATE,
                    scope_ref="local",
                    context_refs=(attributed_context,),
                    provenance_refs=tuple(sorted(set((*content.evidence_refs, *act.evidence_refs)))),
                    permission_ref=permission_ref,
                    metadata={"discourse_act_ref": act.application_ref},
                )
                proposition = PropositionReferent(
                    referent=proposition_referent,
                    content_refs=(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, attributed_app_ref),),
                    context_ref=attributed_context,
                    attribution_refs=(act.application_ref,),
                    evidence_refs=tuple(sorted(set((*content.evidence_refs, *act.evidence_refs)))),
                )
                claim_ref = "referent:claim:" + semantic_fingerprint("discourse-claim", seed, 24)
                claim_referent = Referent(
                    referent_ref=claim_ref,
                    storage_kind=StorageKind.EVENT_OCCURRENCE,
                    identity_status=IdentityStatus.CANDIDATE,
                    scope_ref="local",
                    context_refs=(context_ref,),
                    provenance_refs=tuple(sorted(set((*content.evidence_refs, *act.evidence_refs)))),
                    permission_ref=permission_ref,
                    metadata={
                        "discourse_act_ref": act.application_ref,
                        "commitment_strength": float(act_app.confidence),
                    },
                )
                claim = ClaimOccurrence(
                    referent=claim_referent,
                    claimant_ref=act.speaker_refs[0],
                    audience_refs=act.addressee_refs,
                    proposition_ref=proposition_ref,
                    claim_force=act.claim_force,
                    source_context_ref=context_ref,
                    reported_context_ref=attributed_context,
                    evidence_refs=tuple(sorted(set((*content.evidence_refs, *act.evidence_refs)))),
                )

                applications.pop(content_ref, None)
                applications[attributed_app_ref] = attributed_app
                # Event content must move with its participant application; otherwise
                # the pre-discourse actual-context EventOccurrence would survive as a
                # misleading world-looking record. The clone remains MENTIONED only.
                for event_ref, event in tuple(events.items()):
                    if event.participant_application_ref != content_ref:
                        continue
                    attributed_event_ref = "referent:attributed-event:" + semantic_fingerprint("attributed-event", (event_ref, seed), 24)
                    attributed_event_referent = replace(
                        event.referent, referent_ref=attributed_event_ref, context_refs=(attributed_context,),
                        metadata={**dict(event.referent.metadata), "attributed_from": event_ref, "discourse_act_ref": act.application_ref},
                    )
                    attributed_event = replace(
                        event, referent=attributed_event_referent, participant_application_ref=attributed_app_ref,
                        context_ref=attributed_context, admission_refs=(),
                    )
                    events.pop(event_ref, None)
                    referents.pop(event_ref, None)
                    events[attributed_event_ref] = attributed_event
                    referents[attributed_event_ref] = attributed_event_referent
                referents[proposition_ref] = proposition_referent
                referents[claim_ref] = claim_referent
                propositions[proposition_ref] = proposition
                claims[claim_ref] = claim
                rewritten_content.append(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, attributed_app_ref))
                roots = [root for root in roots if not (root.filler_class == PortFillerClass.SEMANTIC_APPLICATION and root.ref == content_ref)]
                compiled.append(claim_ref)
                act_compiled.append(claim_ref)
                evidence.update(proposition.evidence_refs)
                evidence.update(claim.evidence_refs)

            old_binding = act_app.binding(act.content_port_ref)
            if old_binding is None:
                unresolved.add(f"claim-attribution:{act.application_ref}:missing-content-binding")
                continue
            replacement_binding = replace(old_binding, fillers=tuple(rewritten_content), open_binding_purpose=None)
            applications[act.application_ref] = replace(
                act_app,
                bindings=tuple(replacement_binding if item.port_ref == act.content_port_ref else item for item in act_app.bindings),
                metadata={**dict(act_app.metadata), "claim_occurrence_refs": tuple(sorted(act_compiled))},
            )

        transformed = UOLGraph(
            graph_ref="uol:attributed:" + semantic_fingerprint("attributed-uol", (graph.graph_ref, tuple(sorted(compiled))), 24),
            referents=referents,
            applications=applications,
            variables=graph.variables,
            coordination_groups=graph.coordination_groups,
            propositions=propositions,
            claims=claims,
            events=events,
            scope_relations=graph.scope_relations,
            state_deltas=graph.state_deltas,
            capability_deltas=graph.capability_deltas,
            impact_assessments=graph.impact_assessments,
            importance_assessments=graph.importance_assessments,
            root_refs=tuple(roots),
            unresolved_refs=tuple(sorted(unresolved)),
            assumptions=graph.assumptions,
            evidence_refs=tuple(sorted(evidence)),
        )
        return AttributionResult(transformed, tuple(sorted(compiled)), tuple(sorted(unresolved)), tuple(sorted(evidence)))


def _act_has_explicit_claim(graph: UOLGraph, act_ref: str) -> bool:
    for item in graph.claims.values():
        marker = item.referent.metadata.get("discourse_act_ref")
        if marker == act_ref:
            return True
        if isinstance(marker, (tuple, list, set, frozenset)) and act_ref in marker:
            return True
    return False


def _claim_force(value: object) -> ClaimForce | None:
    if value is None:
        return None
    try:
        return ClaimForce(str(value))
    except ValueError:
        return None


def _binding_refs(application: SemanticApplication, port_ref: str | None) -> tuple[str, ...]:
    if not port_ref:
        return ()
    binding = application.binding(port_ref)
    if binding is None:
        return ()
    return tuple(sorted({getattr(item, "ref", "") for item in binding.fillers if getattr(item, "ref", "")}))


def _application_inbound_refs(graph: UOLGraph) -> dict[str, tuple[str, ...]]:
    """Return semantic consumers that make in-place attribution unsafe.

    EventOccurrence participant links are intentionally omitted because the
    attribution transform rewrites those together with the content application.
    Scope/coordination/proposition links are not guessed or partially cloned; such
    content remains a frontier until a complete subgraph attribution contract exists.
    """
    inbound: dict[str, list[str]] = {}
    for app in graph.applications.values():
        for binding in app.bindings:
            for filler in binding.fillers:
                if isinstance(filler, FillerRef) and filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                    inbound.setdefault(filler.ref, []).append(app.application_ref)
    for relation in graph.scope_relations:
        inbound.setdefault(relation.operator_application_ref, []).append(relation.scope_relation_ref)
        if relation.scoped_ref.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
            inbound.setdefault(relation.scoped_ref.ref, []).append(relation.scope_relation_ref)
    for group in graph.coordination_groups.values():
        for member in group.members:
            if member.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                inbound.setdefault(member.ref, []).append(group.group_ref)
    for proposition in graph.propositions.values():
        for content in proposition.content_refs:
            if content.filler_class == PortFillerClass.SEMANTIC_APPLICATION:
                inbound.setdefault(content.ref, []).append(proposition.proposition_ref)
    return {key: tuple(sorted(set(value))) for key, value in inbound.items()}
