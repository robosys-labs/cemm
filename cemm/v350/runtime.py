"""Canonical CEMM v3.5 Stage-0..22 runtime composition root.

The orchestrator owns stage order; this coordinator owns concrete capability
composition.  Domain meaning remains in schemas/UOL/data records.  Missing
runtime authority is represented as a typed frontier/deferment, never repaired by
surface-text routing or placeholder adapters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .composition.coordinator import MeaningComposer
from .cutover import RuntimeAuthorityGuard
from .discourse import DiscourseClassifier
from .epistemic_pipeline import AttributedClaimCompiler
from .identity import IdempotencyOutcome, classify_persisted_identity
from .facets.projector import ReferentKnowledgeProjector
from .grounding.coordinator import JointGrounder
from .grounding.participants import participant_frame_anchors
from .language.analyzer import FormLatticeAnalyzer
from .learning.frontier import FrontierCollector, FrontierObservation
from .learning.model import PinnedRecord
from .orchestration import CanonicalOrchestrator, CoreStage, CycleState, StageCapability, StageOutcome
from .retrieval import SemanticRetriever
from .runtime_artifacts import AuthorityPin, CyclePins, FinalizationSummary, RuntimeInput, RuntimeResult, StageReceipt, TextObservation
from .runtime_graph import build_stage_adapters
from .schema.model import SchemaClass, StorageKind, UseOperation, semantic_fingerprint
from .semantic_commit import SelectedUOLCommitPlanner
from .storage import (
    EvidenceRecord,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
    AssertionStatus,
    ReferentTypeAssertion,
    SemanticStore,
    encode_record,
    record_fingerprints,
)
from .transitions.coordinator import TransitionCoordinator
from .uol.model import IdentityStatus, Referent
from .version import VERSION


@dataclass(slots=True)
class RuntimeServices:
    """Reviewed/injected capability implementations at non-kernel boundaries."""

    syntax_adapters: Any | None = None
    observation_analyzers: Mapping[str, Any] = field(default_factory=dict)
    epistemic_policy_provider: Any | None = None
    inference_engine: Any | None = None
    operation_gate_evaluators: Mapping[str, Any] = field(default_factory=dict)
    operation_adapters: Mapping[str, Any] = field(default_factory=dict)
    semantic_analyzer: Any | None = None
    emission_gate_evaluators: Mapping[str, Any] = field(default_factory=dict)
    channel_adapters: Mapping[str, Any] = field(default_factory=dict)
    speaker_ref: str | None = None
    output_commitment_kind_ref: str | None = None
    permission_evaluator: Any | None = None
    clock: Any | None = None
    runtime_signal_provider: Any | None = None
    learning_inducers: tuple[Any, ...] = ()
    learning_competence_executors: Mapping[str, Any] = field(default_factory=dict)
    # Process/reload identity is injected from AttestedRuntimeAuthority by the
    # composition root.  It is observational metadata, never semantic authority.
    runtime_epoch_ref: str | None = None
    runtime_attestation_ref: str | None = None
    runtime_authority_generation: int | None = None


class StoreSnapshotProvider:
    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def fingerprint(self) -> str:
        with self.store.snapshot() as snapshot:
            return snapshot.fingerprint


class CanonicalRuntimeCoordinator:
    """Concrete handler set for every canonical core-loop stage."""

    def __init__(self, store: SemanticStore, services: RuntimeServices | None = None) -> None:
        self.store = store
        self.services = services or RuntimeServices()

    @staticmethod
    def _receipt(stage: CoreStage, status: str, *reasons: str, evidence=(), **metadata) -> StageReceipt:
        return StageReceipt(int(stage), status, tuple(reasons), tuple(evidence), metadata)

    def _snapshot(self, capability: StageCapability, cycle: CycleState | None = None, *, require_cycle_pin: bool = False):
        cm = self.store.snapshot()
        snapshot = cm.__enter__()
        if snapshot.fingerprint != capability.snapshot_fingerprint:
            cm.__exit__(None, None, None)
            raise RuntimeError("stage capability snapshot differs from current store snapshot")
        if require_cycle_pin and cycle is not None:
            pins = cycle.artifacts.get("cycle_pins")
            if pins is None or snapshot.fingerprint != pins.snapshot_fingerprint:
                cm.__exit__(None, None, None)
                raise RuntimeError("Stage-0 semantic substrate changed before the Stage-13 commit boundary; restart cycle")
        return cm, snapshot

    @staticmethod
    def _authority_pin(stored) -> AuthorityPin:
        return AuthorityPin(stored.record_kind.value, stored.record_ref, stored.revision, stored.record_fingerprint)

    @staticmethod
    def _pin(stored) -> PinnedRecord:
        if stored is None:
            raise ValueError("cannot pin missing durable record")
        return PinnedRecord(stored.record_kind, stored.record_ref, stored.revision, stored.record_fingerprint)

    def _resolve_any(self, record_ref: str) -> tuple[Any, ...]:
        if not record_ref:
            return ()
        found = []
        for kind in RecordKind:
            try:
                stored = self.store.get_record(kind, record_ref)
            except (KeyError, ValueError, TypeError):
                continue
            if stored is not None:
                found.append(stored)
        return tuple(sorted(found, key=lambda item: (item.record_kind.value, item.revision)))

    def _cycle_source_records(self, cycle: CycleState) -> tuple[Any, ...]:
        refs = set(cycle.artifacts.get("persisted_semantic_refs", ()))
        for pair in cycle.artifacts.get("significance_records", ()):
            if isinstance(pair, tuple) and len(pair) == 2:
                refs.add(getattr(pair[1], "assessment_ref", ""))
        refs.update(getattr(item, "frontier_ref", "") for item in cycle.artifacts.get("learning_frontier_records", ()))
        refs.update(getattr(item, "reconciliation_ref", "") for item in cycle.artifacts.get("operation_reconciliations", ()))
        retrieval = cycle.artifacts.get("retrieval_result")
        for binding in getattr(retrieval, "bindings", ()):
            refs.add(getattr(getattr(binding, "matched_application_pin", None), "record_ref", ""))
        for outcome in cycle.artifacts.get("operation_outcomes", ()):
            if isinstance(outcome, tuple) and len(outcome) == 5 and outcome[4] is not None:
                refs.add(getattr(outcome[4], "result_ref", ""))
        records = {}
        for ref in sorted(ref for ref in refs if ref):
            for stored in self._resolve_any(ref):
                records[(stored.record_kind, stored.record_ref, stored.revision)] = stored
        return tuple(records[key] for key in sorted(records, key=lambda item: (item[0].value, item[1], item[2])))

    def stage_00_orient_and_pin(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        cm, snapshot = self._snapshot(capability)
        try:
            def pins_for(kind: RecordKind):
                return tuple(self._authority_pin(item) for item in self.store.records(kind, snapshot=snapshot))

            pins = CyclePins(
                snapshot_fingerprint=snapshot.fingerprint,
                store_revision=snapshot.store_revision,
                boot_fingerprint=snapshot.boot_fingerprint,
                overlay_fingerprint=snapshot.overlay_fingerprint,
                cycle_time=datetime.now(timezone.utc).isoformat(),
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                channel_ref=cycle.channel_ref,
                target_language=cycle.target_language,
                runtime_version=VERSION,
                language_pack_pins=pins_for(RecordKind.LANGUAGE_PACK),
                operation_adapter_pins=pins_for(RecordKind.OPERATION_ADAPTER_CONTRACT),
                semantic_analyzer_pins=pins_for(RecordKind.SEMANTIC_ANALYZER_CONTRACT),
                channel_adapter_pins=pins_for(RecordKind.CHANNEL_ADAPTER_CONTRACT),
            )
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome({"cycle_pins": pins, "stage00_receipt": self._receipt(CoreStage.ORIENT_AND_PIN, "performed", "semantic_substrate_pinned", evidence=(pins.snapshot_fingerprint, pins.cycle_time))})

    def stage_01_observe(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        envelope = cycle.input_payload
        if isinstance(envelope, str):
            envelope = RuntimeInput(envelope)
        if not isinstance(envelope, RuntimeInput):
            return StageOutcome(
                {"stage01_receipt": self._receipt(CoreStage.OBSERVE, "blocked", "unsupported_input_payload")},
                frontier_refs=("frontier:observation:unsupported-input-payload",),
            )
        source_ref = "source:cycle-input:" + semantic_fingerprint("cycle-input", (cycle.cycle_ref, envelope.content), 24)
        observation = TextObservation(source_ref, envelope.content, cycle.channel_ref, cycle.context_ref, cycle.permission_ref, cycle.audience_refs, envelope.language_hints)
        input_evidence = EvidenceRecord(
            evidence_ref="evidence:cycle-input:" + semantic_fingerprint("cycle-input-evidence", (cycle.cycle_ref, source_ref), 24),
            source_ref=source_ref, confidence=1.0, lineage_ref=source_ref,
            context_ref=cycle.context_ref, observed_at=cycle.artifacts["cycle_pins"].cycle_time,
            permission_ref=cycle.permission_ref, metadata={"channel_ref": cycle.channel_ref},
        )
        return StageOutcome({
            "observation": observation,
            "input_evidence_record": input_evidence,
            "emission_idempotency_key": envelope.emission_idempotency_key,
            "stage01_receipt": self._receipt(CoreStage.OBSERVE, "performed", "text_observed", evidence=(source_ref, input_evidence.evidence_ref)),
        })

    def stage_02_analyze_and_fuse_form(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        observation = cycle.artifacts.get("observation")
        if not isinstance(observation, TextObservation):
            return self._missing(CoreStage.ANALYZE_AND_FUSE_FORM, "observation")
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            registry = self.store.repositories.language.registry(snapshot=snapshot)
            analyzer = FormLatticeAnalyzer(registry, syntax_adapters=self.services.syntax_adapters)
            lattice = analyzer.analyze(observation.content, source_ref=observation.source_ref, language_hints=observation.language_hints)
        finally:
            cm.__exit__(None, None, None)
        frontier_refs = tuple(f"frontier:form-span:{span.start}:{span.end}" for span in lattice.unresolved_spans)
        return StageOutcome({"form_lattice": lattice, "stage02_receipt": self._receipt(CoreStage.ANALYZE_AND_FUSE_FORM, "performed", "form_lattice_built", evidence=(lattice.lattice_ref,))}, frontier_refs=frontier_refs)

    def stage_03_generate_candidates(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        lattice = cycle.artifacts.get("form_lattice")
        observation = cycle.artifacts.get("observation")
        if lattice is None or observation is None:
            return self._missing(CoreStage.GENERATE_REFERENT_AND_SCHEMA_CANDIDATES, "form_lattice")
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            analyzer = FormLatticeAnalyzer(self.store.repositories.language.registry(snapshot=snapshot), syntax_adapters=self.services.syntax_adapters)
            grounder = JointGrounder(self.store, analyzer)
            envelope = cycle.input_payload if isinstance(cycle.input_payload, RuntimeInput) else RuntimeInput(str(cycle.input_payload))
            participant_anchors = participant_frame_anchors(
                cycle.artifacts.get("participant_frame"),
                store=self.store,
                snapshot=snapshot,
            )
            anchors_by_ref = {
                item.anchor_ref: item
                for item in (*tuple(envelope.discourse_anchors), *participant_anchors)
            }
            prepared = grounder.prepare_lattice(
                lattice,
                context_ref=cycle.context_ref,
                discourse_anchors=tuple(
                    anchors_by_ref[key] for key in sorted(anchors_by_ref)
                ),
                multimodal_tracks=envelope.multimodal_tracks,
                system_outputs=envelope.system_output_anchors,
                constraints=envelope.grounding_constraints,
                snapshot=snapshot,
            )
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome({"grounder": grounder, "grounding_preparation": prepared, "stage03_receipt": self._receipt(CoreStage.GENERATE_REFERENT_AND_SCHEMA_CANDIDATES, "performed", "grounding_candidates_generated", evidence=prepared.evidence_refs)}, frontier_refs=tuple(m.mention_ref for m in prepared.mentions if not any(c.mention_ref == m.mention_ref for c in prepared.candidates)))

    def stage_04_project_knowledge(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        prepared = cycle.artifacts.get("grounding_preparation")
        if prepared is None:
            return self._missing(CoreStage.PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS, "grounding_preparation")
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        projections = {}
        projection_frontiers = []
        try:
            projector = ReferentKnowledgeProjector(self.store)
            by_target = {}
            for item in prepared.candidates:
                by_target.setdefault(item.target_ref, []).append(item)
            for target_ref in sorted(by_target):
                candidates = tuple(by_target[target_ref])
                durable = self.store.get_record(
                    RecordKind.REFERENT, target_ref, snapshot=snapshot
                )
                if durable is not None:
                    projections[target_ref] = projector.project(
                        target_ref,
                        context_ref=cycle.context_ref,
                        at_time=None,
                        snapshot=snapshot,
                    )
                    continue
                envelopes = {
                    (
                        tuple(sorted(item.type_refs)),
                        item.storage_kind.value,
                        tuple(sorted(item.context_refs)),
                    )
                    for item in candidates
                }
                if len(envelopes) != 1:
                    projection_frontiers.append(
                        f"frontier:referent-knowledge:{target_ref}:candidate-envelope-ambiguous"
                    )
                    continue
                projections[target_ref] = projector.project_candidate(
                    candidates[0],
                    context_ref=cycle.context_ref,
                    at_time=None,
                    snapshot=snapshot,
                )
            from .facets.closure import ReferentKnowledgeClosureCompiler
            closure_candidates = ReferentKnowledgeClosureCompiler(self.store).compile(projections, snapshot=snapshot)
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome(
            {"referent_projections": projections, "semantic_closure_candidates": closure_candidates, "stage04_receipt": self._receipt(CoreStage.PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS, "performed", "referent_knowledge_and_semantic_closure_projected", evidence=tuple(sorted({*projections, *(item.candidate_ref for item in closure_candidates)})))},
            frontier_refs=tuple(projection_frontiers),
        )

    def stage_05_build_factor_graph(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        grounder = cycle.artifacts.get("grounder")
        prepared = cycle.artifacts.get("grounding_preparation")
        lattice = cycle.artifacts.get("form_lattice")
        if grounder is None or prepared is None or lattice is None:
            return self._missing(CoreStage.BUILD_UOL_FACTOR_GRAPH, "grounding_preparation")
        grounding = grounder.solve_prepared(prepared)
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            composer = MeaningComposer(self.store)
            factor_graph = composer.build_factor_graph(
                lattice, grounding,
                context_ref=cycle.context_ref,
                referent_projections=cycle.artifacts.get("referent_projections", {}),
                closure_candidates=cycle.artifacts.get("semantic_closure_candidates", ()),
                snapshot=snapshot,
            )
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome({"grounding_result": grounding, "meaning_composer": composer, "meaning_factor_graph": factor_graph, "stage05_receipt": self._receipt(CoreStage.BUILD_UOL_FACTOR_GRAPH, "performed", "unified_factor_graph_built", evidence=factor_graph.evidence_refs)}, frontier_refs=tuple(grounding.frontier_refs))

    def stage_06_solve_meaning(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        composer = cycle.artifacts.get("meaning_composer")
        graph = cycle.artifacts.get("meaning_factor_graph")
        if composer is None or graph is None:
            return self._missing(CoreStage.SOLVE_MEANING_HYPOTHESES, "meaning_factor_graph")
        solved = composer.solve_factor_graph(graph)
        status = "performed" if solved.hypotheses else "deferred"
        frontiers = () if solved.hypotheses else ("frontier:meaning:no-compatible-hypothesis",)
        return StageOutcome({"meaning_solve": solved, "stage06_receipt": self._receipt(CoreStage.SOLVE_MEANING_HYPOTHESES, status, "bounded_meaning_solve", evidence=solved.evidence_refs)}, frontier_refs=frontiers)

    def stage_07_select_meaning(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        composer = cycle.artifacts.get("meaning_composer"); graph = cycle.artifacts.get("meaning_factor_graph"); solved = cycle.artifacts.get("meaning_solve"); lattice = cycle.artifacts.get("form_lattice"); grounding = cycle.artifacts.get("grounding_result")
        if any(item is None for item in (composer, graph, solved, lattice, grounding)):
            return self._missing(CoreStage.SELECT_MEANING_BUNDLE, "meaning_solve")
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            result = composer.select_bundle(graph, solved, lattice, grounding, context_ref=cycle.context_ref, snapshot=snapshot)
        finally:
            cm.__exit__(None, None, None)
        intentional_query_refs = {
            ref
            for ref, variable in (
                result.bundle.uol_graph.variables.items()
                if result.bundle.uol_graph is not None else ()
            )
            if getattr(
                variable.open_binding_purpose, "value", None
            ) == "query"
        }
        frontiers = tuple(sorted(
            set((
                *result.bundle.partial_understanding.frontier_refs,
                *(
                    ref
                    for ref
                    in result.bundle.partial_understanding.unresolved_refs
                    if ref not in intentional_query_refs
                ),
            ))
        ))
        status = "performed" if result.bundle.uol_graph is not None else "deferred"
        return StageOutcome({"meaning_composition": result, "meaning_bundle": result.bundle, "stage07_receipt": self._receipt(CoreStage.SELECT_MEANING_BUNDLE, status, "meaning_bundle_selected", evidence=result.bundle.evidence_refs)}, frontier_refs=frontiers)

    def stage_08_classify_discourse(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        bundle = cycle.artifacts.get("meaning_bundle")
        if bundle is None or bundle.uol_graph is None:
            return self._missing(CoreStage.CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS, "selected_uol")
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            classifier = DiscourseClassifier(self.store)
            classification = classifier.classify(bundle.uol_graph, snapshot=snapshot)
            attribution = classifier.attribute_claims(
                bundle.uol_graph, classification, context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref, snapshot=snapshot,
            )
            from .uol.validator import UOLValidator
            validation = UOLValidator(self.store.repositories.schemas.registry(snapshot=snapshot)).validate(
                attribution.graph, provisional=True
            )
            validation.require_valid()
        finally:
            cm.__exit__(None, None, None)
        validation_frontiers = tuple(
            f"uol-validation:{item.code}:{item.target_ref}" for item in validation.unresolved
        )
        frontiers = tuple(sorted(set((*classification.unresolved_refs, *attribution.unresolved_refs, *validation_frontiers))))
        return StageOutcome({"discourse_classification": classification, "attribution_result": attribution, "epistemic_uol_graph": attribution.graph, "stage08_receipt": self._receipt(CoreStage.CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS, "performed", "discourse_structures_classified_and_attributed", evidence=attribution.evidence_refs)}, frontier_refs=frontiers)

    def stage_09_epistemically_assess(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        classification = cycle.artifacts.get("discourse_classification")
        graph = cycle.artifacts.get("epistemic_uol_graph")
        evidence_record = cycle.artifacts.get("input_evidence_record")
        if classification is None or graph is None or evidence_record is None:
            return self._missing(CoreStage.EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT, "attributed_uol")
        placement = AttributedClaimCompiler().compile_graph(graph, durable_evidence_ref=evidence_record.evidence_ref)
        # Actual-world admission remains false unless a separate explicit admission
        # request, source assessments, policy and authorization are supplied. Grammar
        # and claim force alone never cross that boundary.
        unresolved = tuple(sorted(set((*classification.unresolved_refs, *placement.unresolved_refs))))
        return StageOutcome({
            "epistemic_placement": placement,
            "compiled_claim_lineages": placement.attributed_claims,
            "stage09_receipt": self._receipt(CoreStage.EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT, "performed", "attributed_claims_preserved_without_implicit_world_admission", evidence=placement.evidence_refs),
        }, frontier_refs=unresolved)

    def stage_10_retrieve_and_bind(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        graph = cycle.artifacts.get("epistemic_uol_graph")
        if graph is None:
            return self._missing(CoreStage.RETRIEVE_AND_ANSWER_BIND, "epistemic_uol_graph")
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            from .querying import UniversalSemanticBinder
            retrieval = UniversalSemanticBinder(self.store).bind(
                graph, classification=cycle.artifacts.get("discourse_classification"),
                context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                referent_projections=cycle.artifacts.get("referent_projections", {}), snapshot=snapshot,
            )
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome({"retrieval_result": retrieval, "stage10_receipt": self._receipt(CoreStage.RETRIEVE_AND_ANSWER_BIND, "performed", "universal_semantic_query_binding_completed", evidence=retrieval.evidence_refs)}, frontier_refs=tuple(retrieval.unresolved_query_refs))

    def stage_11_learning_frontiers(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        from .learning.runtime import TypedRuntimeFrontierCompiler
        observations = TypedRuntimeFrontierCompiler().compile(cycle)
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            existing = tuple(
                item.payload
                for item in self.store.repositories.learning_frontiers.all(
                    all_revisions=True, snapshot=snapshot
                )
            )
        finally:
            cm.__exit__(None, None, None)
        frontiers = FrontierCollector().collect(observations, existing)
        return StageOutcome({"learning_observations": observations, "learning_frontier_records": frontiers, "stage11_receipt": self._receipt(CoreStage.BUILD_OR_ADVANCE_LEARNING_FRONTIERS, "performed" if observations else "no_authorized_work", "learning_frontiers_built")}, frontier_refs=tuple(item.frontier_ref for item in frontiers))

    def stage_12_preview_transitions(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        graph = cycle.artifacts.get("epistemic_uol_graph")
        if graph is None or not graph.events:
            return StageOutcome({"transition_previews": (), "stage12_receipt": self._receipt(CoreStage.INFER_AND_PREVIEW_TRANSITIONS, "no_authorized_work", "no_selected_events")})
        staged = []
        staged.extend((RecordKind.REFERENT, item) for item in graph.referents.values())
        staged.extend((RecordKind.SEMANTIC_APPLICATION, item) for item in graph.applications.values())
        staged.extend((RecordKind.PROPOSITION, item) for item in graph.propositions.values())
        staged.extend((RecordKind.CLAIM_OCCURRENCE, item) for item in graph.claims.values())
        staged.extend((RecordKind.EVENT_OCCURRENCE, item) for item in graph.events.values())
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            coordinator = TransitionCoordinator(self.store)
            cycle_time = cycle.artifacts["cycle_pins"].cycle_time
            plans = tuple(
                (
                    event.event_ref,
                    coordinator.plans_for_staged_event(
                        event,
                        staged_records=tuple(staged),
                        effective_time_ref=event.time_ref or cycle_time,
                        snapshot=snapshot,
                    ),
                )
                for event in graph.events.values()
            )
        finally:
            cm.__exit__(None, None, None)
        frontier_refs = tuple(sorted({f.frontier_ref for _event_ref, event_plans in plans for plan in event_plans for f in plan.preview.frontiers}))
        return StageOutcome({"transition_previews": plans, "stage12_receipt": self._receipt(CoreStage.INFER_AND_PREVIEW_TRANSITIONS, "performed", "transitions_previewed_non_durably")}, frontier_refs=frontier_refs)

    def stage_13_commit_knowledge_state(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        graph = cycle.artifacts.get("epistemic_uol_graph")
        committed = []
        persisted_semantic_refs = []
        deferred = []
        if graph is not None:
            cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
            try:
                evidence_record = cycle.artifacts.get("input_evidence_record")
                plan = SelectedUOLCommitPlanner(self.store).plan(
                    graph, context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                    source_ref=cycle.artifacts.get("observation").source_ref if cycle.artifacts.get("observation") else cycle.cycle_ref,
                    evidence_records=() if evidence_record is None else (evidence_record,),
                    claim_lineages=tuple(cycle.artifacts.get("compiled_claim_lineages", ())),
                    snapshot=snapshot,
                )
            finally:
                cm.__exit__(None, None, None)
            deferred.extend(plan.deferred_refs)
            persisted_semantic_refs.extend(plan.persisted_refs)
            if plan.patch is not None:
                result = self.store.apply_patch(plan.patch)
                if not result.committed:
                    raise RuntimeError("selected UOL commit failed: " + "; ".join(result.errors))
                committed.append(plan.patch.patch_ref)
        observations = cycle.artifacts.get("learning_observations", ())
        learning_commit_trace = None
        if observations:
            from .learning.coordinator import LearningCoordinator
            learning_commit_trace = LearningCoordinator(self.store).collect_frontiers(
                observations,
                persist=True,
                source_ref="source:stage13:learning-frontier",
            )
        learning_advance_trace = None
        if observations:
            from .learning.runtime_advance import RuntimeLearningAdvancer
            learning_advance_trace = RuntimeLearningAdvancer(
                self.store,
                inducers=tuple(self.services.learning_inducers),
                competence_executors=dict(
                    self.services.learning_competence_executors
                ),
            ).advance(
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
            )
        # Recompute transition plans only after the semantic records are durable.
        canonical_transition_plans = []
        if graph is not None:
            coordinator = TransitionCoordinator(self.store)
            for event in graph.events.values():
                stored = self.store.get_record(RecordKind.EVENT_OCCURRENCE, event.event_ref)
                if stored is None:
                    continue
                effective_time_ref = stored.payload.time_ref or cycle.artifacts["cycle_pins"].cycle_time
                event_plans = tuple(
                    coordinator.plans_for_event(stored.payload, effective_time_ref=effective_time_ref)
                )
                for plan in event_plans:
                    if plan.preview.authorized and plan.preview.proof is not None:
                        patch = coordinator.build_patch(stored.payload, plan, source_ref="source:stage13:transition", permission_ref=cycle.permission_ref)
                        result = self.store.apply_patch(patch)
                        if not result.committed:
                            raise RuntimeError("transition commit failed: " + "; ".join(result.errors))
                        committed.append(patch.patch_ref)
                canonical_transition_plans.append((event.event_ref, event_plans))
        status = "performed" if committed else "no_authorized_work"
        return StageOutcome(
            {
                "committed_patch_refs": tuple(committed),
                "persisted_semantic_refs": tuple(sorted(set(persisted_semantic_refs))),
                "canonical_transition_plans": tuple(canonical_transition_plans),
                "learning_commit_trace": learning_commit_trace,
                "learning_advance_trace": learning_advance_trace,
                "stage13_receipt": self._receipt(
                    CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE,
                    status,
                    "cas_commit_boundary",
                ),
            },
            frontier_refs=tuple(sorted(set(deferred))),
        )

    def stage_14_assess_significance(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        # Impact/importance are derived only from exact durable source pins and active rules.
        from .significance.engine import ImpactRuleRegistry, SignificanceEngine
        from .significance.coordinator import SignificanceCommitCoordinator
        rules_stored = self.store.repositories.impact_rules.all(all_revisions=True)
        registry = ImpactRuleRegistry(item.payload for item in rules_stored)
        engine = SignificanceEngine(self.store)
        records = []
        frontiers = []
        source_refs = set(cycle.artifacts.get("persisted_semantic_refs", ()))
        for ref in sorted(source_refs):
            matches = self._resolve_any(ref)
            for stored in matches:
                if stored.record_kind not in {RecordKind.EVENT_OCCURRENCE, RecordKind.SEMANTIC_APPLICATION}:
                    continue
                source = engine.resolve_source(self._pin(stored))
                for rule in registry.candidates(source):
                    rule_stored = self.store.get_record(RecordKind.IMPACT_RULE, rule.rule_ref, rule.revision)
                    if rule_stored is None:
                        continue
                    app_pin = None
                    if stored.record_kind == RecordKind.EVENT_OCCURRENCE:
                        app = self.store.get_record(RecordKind.SEMANTIC_APPLICATION, stored.payload.participant_application_ref)
                        app_pin = None if app is None else self._pin(app)
                    assessed, gaps = engine.assess(self._pin(stored), rule, self._pin(rule_stored), participant_application_pin=app_pin)
                    records.extend(assessed); frontiers.extend(gaps)
        # Commit independently per source scope to respect coordinator isolation.
        committed_refs = []
        coordinator = SignificanceCommitCoordinator(self.store)
        for pair in records:
            result = coordinator.commit((pair,))
            if result.committed:
                committed_refs.append(pair[1].assessment_ref)
        for frontier in frontiers:
            source = self._resolve_any(frontier.target_ref or "")
            pins = tuple(self._pin(item) for item in source[:1])
            if pins:
                result = coordinator.commit((), (frontier,), pins)
                if result.committed:
                    committed_refs.append(frontier.frontier_ref)
        return StageOutcome({"significance_records": tuple(records), "stage14_receipt": self._receipt(CoreStage.ASSESS_IMPACT_AND_IMPORTANCE, "performed" if records or frontiers else "no_authorized_work", "significance_assessed_from_exact_rules")}, frontier_refs=tuple(item.frontier_ref for item in frontiers))

    def stage_15_arbitrate_goals(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        from .goals.coordinator import GoalDecisionCoordinator
        from .goals.policy import ResponsePolicyRegistry, ObligationDeriver, GoalAuthorizationGate, GoalConflictDetector, GoalArbitrator, build_candidate
        rules_stored = self.store.repositories.response_policy_rules.all(all_revisions=True)
        registry = ResponsePolicyRegistry(item.payload for item in rules_stored)
        allowed_source_kinds = {
            RecordKind.SIGNIFICANCE_ASSESSMENT, RecordKind.LEARNING_FRONTIER,
            RecordKind.CLAIM_RECORD, RecordKind.EVENT_OCCURRENCE,
            RecordKind.SEMANTIC_APPLICATION, RecordKind.KNOWLEDGE,
            RecordKind.OPERATION_RECONCILIATION, RecordKind.OPERATION_RESULT,
        }
        source_records = [
            item for item in self._cycle_source_records(cycle)
            if item.record_kind in allowed_source_kinds
            and (item.context_ref or getattr(item.payload, "context_ref", cycle.context_ref)) in {"global", cycle.context_ref}
            and (item.permission_ref or getattr(item.payload, "permission_ref", cycle.permission_ref)) in {"public", cycle.permission_ref}
        ]
        obligations=[]; candidates=[]
        deriver=ObligationDeriver(self.store); auth=GoalAuthorizationGate(self.store)
        for source in source_records:
            rule_candidates = registry.candidates(source.record_kind, source.payload)
            for rule in rule_candidates:
                rule_stored=self.store.get_record(RecordKind.RESPONSE_POLICY_RULE,rule.rule_ref,rule.revision)
                if rule_stored is None: continue
                obligation=deriver.derive(self._pin(source),rule,self._pin(rule_stored))
                if obligation is None: continue
                obligations.append(obligation); candidates.append(auth.authorize(build_candidate(obligation),rule))
        retrieval = cycle.artifacts.get("retrieval_result")
        if retrieval is not None and getattr(getattr(retrieval, "request", None), "response_requested", False):
            from .goals.query_policy import QueryResponseGoalDeriver
            frontier_pins=[]
            for item in cycle.artifacts.get("learning_frontier_records", ()):
                stored=self.store.get_record(RecordKind.LEARNING_FRONTIER,item.frontier_ref,item.revision)
                if stored is not None: frontier_pins.append(self._pin(stored))
            q_obligations,q_candidates=QueryResponseGoalDeriver(self.store,registry).derive(retrieval,frontier_pins=tuple(frontier_pins))
            obligations.extend(q_obligations); candidates.extend(q_candidates)
        if not candidates:
            return StageOutcome({"goal_decision": None, "stage15_receipt": self._receipt(CoreStage.DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS, "no_authorized_work", "no_policy_licensed_goal")})
        conflicts=GoalConflictDetector().detect(candidates)
        selected,rejected,deferred=GoalArbitrator().select(candidates,conflicts)
        result,decision=GoalDecisionCoordinator(self.store).commit(obligations=tuple(obligations),candidates=tuple(candidates),conflicts=conflicts,selected_goal_refs=selected,rejected_goal_refs=rejected,deferred_goal_refs=deferred,arbitration_policy_ref="kernel:authorization-first-priority-utility:v1",context_ref=cycle.context_ref,permission_ref=cycle.permission_ref)
        return StageOutcome({"goal_decision": decision, "stage15_receipt": self._receipt(CoreStage.DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS, "performed", "generic_goals_arbitrated", evidence=(decision.decision_ref,))}, frontier_refs=tuple(deferred))

    def stage_16_plan_execute_operations(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        decision = cycle.artifacts.get("goal_decision")
        existing_outcomes = tuple(cycle.artifacts.get("operation_outcomes", ()))
        attempted = set(cycle.artifacts.get("operation_attempted_goal_refs", ()))
        if decision is None:
            return StageOutcome({
                "operation_outcomes": existing_outcomes,
                "stage16_pending_outcomes": (),
                "operation_attempted_goal_refs": tuple(sorted(attempted)),
                "stage16_receipt": self._receipt(CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE, "no_authorized_work", "no_goal_decision"),
            })
        execute_refs=[]
        for pin in decision.candidate_pins:
            stored=self.store.get_record(pin.record_kind,pin.record_ref,pin.revision)
            if (
                stored is not None
                and stored.record_fingerprint==pin.record_fingerprint
                and stored.payload.operation==UseOperation.EXECUTE
                and stored.payload.goal_ref in decision.selected_goal_refs
                and stored.payload.goal_ref not in attempted
            ):
                execute_refs.append(stored.payload.goal_ref)
        if not execute_refs:
            return StageOutcome({
                "operation_outcomes": existing_outcomes,
                "stage16_pending_outcomes": (),
                "operation_attempted_goal_refs": tuple(sorted(attempted)),
                "stage16_receipt": self._receipt(CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE, "no_authorized_work", "no_new_selected_execute_goal"),
            })
        if not self.services.operation_adapters or not self.services.operation_gate_evaluators:
            return StageOutcome({
                "operation_outcomes": existing_outcomes,
                "stage16_pending_outcomes": (),
                "operation_attempted_goal_refs": tuple(sorted(attempted)),
                "stage16_receipt": self._receipt(CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE, "blocked", "operation_runtime_authority_unavailable"),
            }, frontier_refs=tuple(f"frontier:operation-runtime:{ref}" for ref in execute_refs))
        from .operations.planner import OperationPlanner, OperationAuthorizationGate
        from .operations.coordinator import OperationJournalCoordinator
        from .operations.executor import OperationExecutionCoordinator
        decision_stored=self.store.get_record(RecordKind.GOAL_DECISION,decision.decision_ref)
        decision_pin=self._pin(decision_stored)
        new_outcomes=[]
        frontiers=[]
        for goal_ref in execute_refs:
            goal_stored=next(
                (
                    self.store.get_record(p.record_kind,p.record_ref,p.revision)
                    for p in decision.candidate_pins
                    if p.record_ref==goal_ref
                ),
                None,
            )
            matching_pins=tuple(p for p in decision.candidate_pins if p.record_ref==goal_ref)
            if (
                goal_stored is None
                or not matching_pins
                or goal_stored.record_fingerprint not in {p.record_fingerprint for p in matching_pins}
            ):
                frontiers.append(f"frontier:operation-goal:{goal_ref}:stale")
                continue
            goal=goal_stored.payload
            action_targets = tuple(
                item.target_ref for item in getattr(goal, "target_bindings", ())
                if item.role_ref in {"action_application", "execute_target", "application_port"}
            )
            if not action_targets and len(goal.target_refs) == 1:
                action_targets = tuple(goal.target_refs)
            app=self.store.get_record(RecordKind.SEMANTIC_APPLICATION,next(iter(action_targets))) if len(action_targets)==1 else None
            contracts=[]
            if app is not None:
                with self.store.snapshot() as snapshot:
                    contracts=[
                        item
                        for item in self.store.repositories.operation_adapter_contracts.all(snapshot=snapshot)
                        if item.payload.active
                        and (app.payload.schema_ref,app.payload.schema_revision) in item.payload.action_schema_pins
                    ]
            if len(contracts)!=1:
                frontiers.append(f"frontier:operation-adapter-contract:{goal_ref}")
                continue
            plan=OperationPlanner(self.store).plan(decision_pin,goal_ref,self._pin(contracts[0]))
            authorization,assessments=OperationAuthorizationGate(self.store).authorize(
                plan,gate_evaluators=self.services.operation_gate_evaluators
            )
            if getattr(authorization.decision,"value",authorization.decision)!="allow":
                new_outcomes.append((plan, authorization, assessments, None, None))
                continue
            adapter = self.services.operation_adapters.get(contracts[0].payload.adapter_ref)
            if adapter is None:
                frontiers.append(f"frontier:operation-adapter:{contracts[0].payload.adapter_ref}")
                new_outcomes.append((plan, authorization, assessments, None, None))
                continue
            # From PREPARED onward this goal has an external-side-effect attempt identity.
            # Preserve it across the bounded Stage-17 -> Stage-15 refresh so it cannot
            # be submitted twice in the same cycle even if policy selects it again.
            journal=OperationJournalCoordinator(self.store).prepare(plan,authorization,assessments)
            attempted.add(goal_ref)
            final_journal, result_record = OperationExecutionCoordinator(self.store).execute_prepared(
                journal, plan, adapter
            )
            new_outcomes.append((plan, authorization, assessments, final_journal, result_record))
        cumulative=(*existing_outcomes,*tuple(new_outcomes))
        return StageOutcome(
            {
                "operation_outcomes": cumulative,
                "stage16_pending_outcomes": tuple(new_outcomes),
                "operation_attempted_goal_refs": tuple(sorted(attempted)),
                "stage16_receipt": self._receipt(
                    CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE,
                    "performed" if new_outcomes else "deferred",
                    "operation_gate_pipeline_executed",
                ),
            },
            frontier_refs=tuple(sorted(set(frontiers))),
        )

    def stage_17_reconcile_operations(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        outcomes=tuple(cycle.artifacts.get("stage16_pending_outcomes",()))
        existing_reconciliations=tuple(cycle.artifacts.get("operation_reconciliations",()))
        if not outcomes:
            return StageOutcome({
                "operation_reconciliations": existing_reconciliations,
                "stage17_receipt": self._receipt(CoreStage.RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS, "no_authorized_work", "no_new_operation_outcome"),
            })
        from .operations.executor import ReconciliationCoordinator
        from .operations.coordinator import OperationJournalCoordinator
        new_reconciliations=[]
        frontiers=[]
        for plan,_auth,_assessments,journal,result in outcomes:
            if journal is None or result is None:
                if journal is not None:
                    frontiers.append(f"frontier:operation-outcome:{journal.journal_ref}")
                continue
            journal_stored=self.store.get_record(RecordKind.OPERATION_JOURNAL,journal.journal_ref,journal.revision)
            result_stored=self.store.get_record(RecordKind.OPERATION_RESULT,result.result_ref,result.revision)
            if journal_stored is None or result_stored is None:
                frontiers.append(f"frontier:operation-reconciliation:{plan.plan_ref}:missing-observation")
                continue
            observed_effect_frontiers=tuple(
                f"frontier:operation-observed-effect:{ref}" for ref in result.observed_effect_refs
            )
            reconciliation=ReconciliationCoordinator(self.store).build(
                self._pin(self.store.get_record(RecordKind.OPERATION_PLAN,plan.plan_ref,plan.revision)),
                self._pin(result_stored),
                observed_journal_pin=self._pin(journal_stored),
                observed_pins=(),
                generated_evidence_refs=result.evidence_refs,
                replay_required_refs=result.uncertainty_refs,
                contradiction_refs=(),
                frontier_refs=observed_effect_frontiers,
            )
            OperationJournalCoordinator(self.store).persist_reconciliation(reconciliation)
            new_reconciliations.append(reconciliation)
            frontiers.extend(reconciliation.frontier_refs)
        cumulative=(*existing_reconciliations,*tuple(new_reconciliations))
        refresh=bool(new_reconciliations)
        status="performed" if new_reconciliations else ("deferred" if frontiers else "no_authorized_work")
        return StageOutcome(
            {
                "operation_reconciliations": cumulative,
                "stage17_receipt": self._receipt(
                    CoreStage.RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS,
                    status,
                    "operation_outcomes_reconciled",
                ),
            },
            frontier_refs=tuple(sorted(set(frontiers))),
            request_goal_refresh=refresh,
        )

    def stage_18_build_response_uol(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        decision=cycle.artifacts.get("goal_decision")
        if decision is None or not decision.selected_goal_refs:
            return StageOutcome({"response_uol": None, "stage18_receipt": self._receipt(CoreStage.BUILD_RESPONSE_UOL, "no_authorized_work", "no_selected_response_goal")})
        from .response.planner import ResponseMeaningPlanner
        from .response.coordinator import ResponseUOLCommitCoordinator
        decision_stored=self.store.get_record(RecordKind.GOAL_DECISION,decision.decision_ref)
        rules=tuple(item.payload for item in self.store.repositories.response_transform_rules.all(all_revisions=True))
        retrieval=cycle.artifacts.get("retrieval_result")
        try:
            selected_query_goal=any(
                self.store.get_record(pin.record_kind,pin.record_ref,pin.revision) is not None
                and self.store.get_record(pin.record_kind,pin.record_ref,pin.revision).payload.metadata.get("query_result_ref")==getattr(retrieval,"result_ref",None)
                and pin.record_ref in decision.selected_goal_refs
                for pin in decision.candidate_pins
            ) if retrieval is not None else False
            if selected_query_goal:
                from .response.query_response import BoundQueryResponsePlanner
                response,proofs,frontiers=BoundQueryResponsePlanner(self.store,rules).plan(self._pin(decision_stored),retrieval,audience_refs=cycle.audience_refs,perspective_ref="perspective:self")
            else:
                response,proofs,frontiers=ResponseMeaningPlanner(self.store,rules).plan(self._pin(decision_stored),audience_refs=cycle.audience_refs,perspective_ref="perspective:self")
        except ValueError as exc:
            return StageOutcome({"response_uol": None, "stage18_receipt": self._receipt(CoreStage.BUILD_RESPONSE_UOL, "deferred", "response_uol_not_authorized")},frontier_refs=("frontier:response:"+semantic_fingerprint("response-frontier",str(exc),20),))
        ResponseUOLCommitCoordinator(self.store).commit(response,proofs,frontiers)
        return StageOutcome({"response_uol": response, "response_frontiers": frontiers, "stage18_receipt": self._receipt(CoreStage.BUILD_RESPONSE_UOL, "performed", "response_uol_committed", evidence=(response.response_ref,))},frontier_refs=tuple(item.frontier_ref for item in frontiers))

    def stage_19_realize_target_language(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        response=cycle.artifacts.get("response_uol")
        if response is None:
            return StageOutcome({"surface_candidate": None, "stage19_receipt": self._receipt(CoreStage.REALIZE_TARGET_LANGUAGE, "no_authorized_work", "no_response_uol")})
        from .realization.engine import PrivacyAwareReferenceResolver, RealizationCompiler, RealizationFrontier
        from .realization.coordinator import RealizationCommitCoordinator
        from .realization.model import RealizationRequestRecord
        response_stored=self.store.get_record(RecordKind.RESPONSE_UOL,response.response_ref)
        language_tag=cycle.target_language
        if not language_tag:
            lattice=cycle.artifacts.get("form_lattice"); tags=tuple(getattr(lattice,"metadata",{}).get("language_tags",())) if lattice is not None else ()
            language_tag=tags[0] if len(tags)==1 else None
        if not language_tag:
            return StageOutcome({"surface_candidate": None, "stage19_receipt": self._receipt(CoreStage.REALIZE_TARGET_LANGUAGE, "deferred", "target_language_unresolved")},frontier_refs=("frontier:realization:target-language",))
        pack_stored=[]
        for item in self.store.repositories.language.packs.all(all_revisions=True):
            if item.payload.language_tag==language_tag and item.payload in self.store.repositories.language.registry().active_packs(): pack_stored.append(item)
        if not pack_stored:
            return StageOutcome({"surface_candidate": None, "stage19_receipt": self._receipt(CoreStage.REALIZE_TARGET_LANGUAGE, "deferred", "active_language_pack_missing")},frontier_refs=(f"frontier:realization:language-pack:{language_tag}",))
        request=RealizationRequestRecord(request_ref="realization-request:"+semantic_fingerprint("realization-request",(response.response_ref,language_tag,cycle.audience_refs),24),response_uol_pin=self._pin(response_stored),language_tag=language_tag,script=None,locale_ref=None,audience_refs=cycle.audience_refs,register_refs=(),language_pack_pins=tuple(self._pin(item) for item in pack_stored),budget_ref="budget:runtime-default",permission_ref=cycle.permission_ref,sensitivity=response.sensitivity,metadata={"speaker_ref":self.services.speaker_ref,"addressee_refs":cycle.audience_refs})
        frames=tuple((self._pin(item),item.payload) for item in self.store.repositories.argument_frames.all(all_revisions=True))
        morph=tuple((self._pin(item),item.payload) for item in self.store.repositories.morphology_rules.all(all_revisions=True))
        linear=tuple((self._pin(item),item.payload) for item in self.store.repositories.linearization_rules.all(all_revisions=True))
        try:
            clauses,refs,candidate=RealizationCompiler(self.store,PrivacyAwareReferenceResolver(self.store)).compile(request,frames=frames,morphology_rules=morph,linearization_rules=linear)
        except RealizationFrontier as exc:
            return StageOutcome({"surface_candidate": None, "stage19_receipt": self._receipt(CoreStage.REALIZE_TARGET_LANGUAGE, "deferred", exc.missing_contract)},frontier_refs=("frontier:realization:"+semantic_fingerprint("realization-frontier",(exc.missing_contract,exc.refs),20),))
        RealizationCommitCoordinator(self.store).commit_candidate(request,clauses,refs,candidate)
        return StageOutcome({"realization_request": request, "surface_candidate": candidate, "stage19_receipt": self._receipt(CoreStage.REALIZE_TARGET_LANGUAGE, "performed", "surface_candidate_compiled_not_yet_authorized", evidence=(candidate.candidate_ref,))})

    def stage_20_verify_authorize_emission(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        request=cycle.artifacts.get("realization_request"); candidate=cycle.artifacts.get("surface_candidate"); response=cycle.artifacts.get("response_uol")
        if request is None or candidate is None or response is None:
            return StageOutcome({"emission": None, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "no_authorized_work", "no_surface_candidate")})
        if not cycle.audience_refs:
            return StageOutcome(
                {
                    "emission": None,
                    "stage20_receipt": self._receipt(
                        CoreStage.VERIFY_AND_AUTHORIZE_EMISSION,
                        "deferred",
                        "explicit_audience_required",
                    ),
                },
                frontier_refs=("frontier:emission:audience",),
            )
        analyzer=self.services.semantic_analyzer
        if analyzer is None:
            return StageOutcome({"emission": None, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "blocked", "semantic_roundtrip_analyzer_unavailable")},frontier_refs=("frontier:emission:semantic-analyzer",))
        from .realization.engine import RoundTripVerifier
        from .realization.coordinator import RealizationCommitCoordinator
        from .output.gate import EmissionGate
        from .output.coordinator import EmissionJournalCoordinator
        from .output.executor import ChannelExecutionCoordinator
        request_stored=self.store.get_record(RecordKind.REALIZATION_REQUEST,request.request_ref); candidate_stored=self.store.get_record(RecordKind.SURFACE_CANDIDATE,candidate.candidate_ref)
        contracts=[item for item in self.store.repositories.semantic_analyzer_contracts.all() if item.payload.active and item.payload.analyzer_ref==analyzer.analyzer_ref and item.payload.analyzer_revision==analyzer.analyzer_revision and (not item.payload.supported_language_tags or request.language_tag in item.payload.supported_language_tags)]
        if len(contracts)!=1:
            return StageOutcome({"emission": None, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "blocked", "semantic_analyzer_contract_not_singular")},frontier_refs=("frontier:emission:semantic-analyzer-contract",))
        roundtrip=RoundTripVerifier(self.store).verify(
            self._pin(request_stored),
            self._pin(candidate_stored),
            response.graph,
            candidate.surface,
            request.language_tag,
            analyzer,
            self._pin(contracts[0]),
            context_ref=cycle.context_ref,
            speaker_ref=self.services.speaker_ref or "referent:self",
            addressee_refs=tuple(cycle.audience_refs),
            permission_ref=cycle.permission_ref,
        )
        RealizationCommitCoordinator(self.store).commit_roundtrip(roundtrip)
        if getattr(roundtrip.decision,"value",roundtrip.decision)!="pass":
            return StageOutcome({"semantic_roundtrip": roundtrip, "emission": None, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "blocked", "semantic_roundtrip_failed")},frontier_refs=("frontier:emission:roundtrip-drift",))
        channels=[item for item in self.store.repositories.channel_adapter_contracts.all() if item.payload.active and item.payload.channel_ref==cycle.channel_ref]
        if len(channels)!=1:
            return StageOutcome({"semantic_roundtrip": roundtrip, "emission": None, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "blocked", "channel_contract_not_singular")},frontier_refs=(f"frontier:emission:channel:{cycle.channel_ref}",))
        channel=channels[0].payload; adapter=self.services.channel_adapters.get(channel.adapter_ref)
        if adapter is None:
            return StageOutcome(
                {
                    "semantic_roundtrip": roundtrip,
                    "emission": None,
                    "stage20_receipt": self._receipt(
                        CoreStage.VERIFY_AND_AUTHORIZE_EMISSION,
                        "blocked",
                        "channel_adapter_unavailable",
                    ),
                },
                frontier_refs=(f"frontier:emission-adapter:{channel.adapter_ref}",),
            )
        operation_results=tuple(
            result
            for _plan,_authorization,_assessments,_journal,result
            in cycle.artifacts.get("operation_outcomes",())
            if result is not None
        )
        operation_reconciliations=tuple(cycle.artifacts.get("operation_reconciliations",()))
        gate=EmissionGate(self.store,self.services.emission_gate_evaluators)
        authorization,assessments=gate.authorize(
            response=response,
            request=request,
            candidate=candidate,
            roundtrip=roundtrip,
            channel=channel,
            audience_refs=cycle.audience_refs,
            operation_results=operation_results,
            operation_reconciliations=operation_reconciliations,
        )
        if getattr(authorization.decision,"value",authorization.decision)!="allow":
            return StageOutcome({"semantic_roundtrip": roundtrip, "emission_authorization": authorization, "emission": None, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "blocked", "emission_gate_denied")},frontier_refs=tuple(f"frontier:emission-gate:{ref}" for ref in authorization.failed_gates))
        from .output.model import EmissionIdempotencyMode
        idempotency_key = cycle.artifacts.get("emission_idempotency_key")
        if channel.idempotency_mode == EmissionIdempotencyMode.CLIENT_KEY and not idempotency_key:
            return StageOutcome(
                {"semantic_roundtrip": roundtrip, "emission_authorization": authorization, "emission": None, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "blocked", "client_idempotency_key_required")},
                frontier_refs=(f"frontier:emission-idempotency:{channel.contract_ref}",),
            )
        if channel.idempotency_mode != EmissionIdempotencyMode.CLIENT_KEY:
            idempotency_key = None
        journal=EmissionJournalCoordinator(self.store).prepare(authorization,assessments,channel,idempotency_key=idempotency_key)
        journal,emission=ChannelExecutionCoordinator(self.store).execute(journal=journal,authorization=authorization,candidate=candidate,contract=channel,adapter=adapter)
        return StageOutcome({"semantic_roundtrip": roundtrip, "emission_authorization": authorization, "emission_journal": journal, "emission": emission, "stage20_receipt": self._receipt(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "performed" if emission is not None else "deferred", "emission_authorized_and_observed" if emission is not None else "emission_outcome_uncertain")})

    def stage_21_commit_output_discourse(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        emission=cycle.artifacts.get("emission")
        if emission is None:
            return StageOutcome({"stage21_receipt": self._receipt(CoreStage.COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND, "no_authorized_work", "no_observed_emission")})
        if not self.services.speaker_ref or not self.services.output_commitment_kind_ref:
            return StageOutcome({"stage21_receipt": self._receipt(CoreStage.COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND, "deferred", "output_discourse_authority_missing")},frontier_refs=("frontier:output-discourse:authority",))
        from .output.coordinator import OutputDiscourseCoordinator
        result=OutputDiscourseCoordinator(self.store).commit_emitted(emission,speaker_ref=self.services.speaker_ref,commitment_kind_ref=self.services.output_commitment_kind_ref)
        return StageOutcome({"output_discourse_commit": result, "stage21_receipt": self._receipt(CoreStage.COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND, "performed", "observed_output_committed")})

    def stage_22_finalize(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        pins = cycle.artifacts.get("cycle_pins")
        if pins is None:
            return self._missing(CoreStage.INVALIDATE_RECOMPUTE_AND_FINALIZE, "cycle_pins")
        replay_required=set()
        for reconciliation in cycle.artifacts.get("operation_reconciliations", ()):
            replay_required.update(getattr(reconciliation, "replay_required_refs", ()))
            replay_required.update(getattr(reconciliation, "frontier_refs", ()))
        for _event_ref, plans in cycle.artifacts.get("canonical_transition_plans", ()):
            for plan in plans:
                preview=getattr(plan, "preview", None)
                for frontier in getattr(preview, "frontiers", ()):
                    replay_required.add(getattr(frontier, "frontier_ref", ""))
        replay_required.discard("")
        with self.store.snapshot() as snapshot:
            final_fp=snapshot.fingerprint
            final_revision=snapshot.store_revision
        substrate_changed=(
            final_revision != pins.store_revision
            or final_fp != pins.snapshot_fingerprint
        )
        unresolved=tuple(sorted(set(cycle.frontiers)))
        summary=FinalizationSummary(
            initial_snapshot_fingerprint=pins.snapshot_fingerprint,
            final_snapshot_fingerprint=final_fp,
            initial_store_revision=pins.store_revision,
            final_store_revision=final_revision,
            substrate_changed=substrate_changed,
            recomputation_required=bool(replay_required or unresolved),
            replay_required_refs=tuple(sorted(replay_required)),
            unresolved_frontier_refs=unresolved,
            incomplete_budget_refs=tuple(
                sorted(ref for ref in unresolved if "budget" in ref or "timeout" in ref)
            ),
        )
        status="deferred" if summary.recomputation_required else "performed"
        return StageOutcome({
            "finalization_summary": summary,
            "final_snapshot_fingerprint": final_fp,
            "stage22_receipt": self._receipt(
                CoreStage.INVALIDATE_RECOMPUTE_AND_FINALIZE,
                status,
                "dependency_invalidations_applied_and_cycle_finalized",
                evidence=(final_fp,),
            ),
        }, frontier_refs=summary.replay_required_refs)

    @staticmethod
    def _missing(stage: CoreStage, artifact: str) -> StageOutcome:
        ref=f"frontier:stage:{int(stage)}:missing:{artifact}"
        return StageOutcome({f"stage{int(stage):02d}_receipt": StageReceipt(int(stage),"deferred",(f"missing_artifact:{artifact}",))},frontier_refs=(ref,))


class Runtime:
    VERSION = VERSION

    def __init__(self, *, store: SemanticStore, orchestrator: CanonicalOrchestrator, services: RuntimeServices | None = None) -> None:
        self.store=store; self.orchestrator=orchestrator; self.services=services or RuntimeServices()

    def _ensure_session_participant(
        self,
        context_ref: str,
        permission_ref: str,
        requested_ref: str | None = None,
    ) -> tuple[str, str]:
        participant_ref = requested_ref or (
            "referent:session-participant:"
            + semantic_fingerprint(
                "session-participant", (context_ref, permission_ref), 24
            )
        )
        existing = self.store.get_record(RecordKind.REFERENT, participant_ref)
        if requested_ref is not None and existing is None:
            raise ValueError(
                "explicit speaker_ref must resolve to an existing durable referent"
            )
        if existing is not None:
            visible_contexts = set(getattr(existing.payload, "context_refs", ()))
            if "global" not in visible_contexts and context_ref not in visible_contexts:
                raise ValueError("speaker referent is not visible in this context")

        source_ref = "source:session-participant:" + semantic_fingerprint(
            "session-participant-source",
            (context_ref, participant_ref, permission_ref),
            24,
        )
        evidence_ref = "evidence:session-participant:" + semantic_fingerprint(
            "session-participant-evidence",
            (context_ref, participant_ref, permission_ref),
            24,
        )
        evidence = EvidenceRecord(
            evidence_ref=evidence_ref,
            source_ref=source_ref,
            confidence=1.0,
            lineage_ref=source_ref,
            context_ref=context_ref,
            permission_ref=permission_ref,
            metadata={
                "identity_criterion": "runtime_session_transport_participant",
                "global_person_identity_claimed": False,
            },
        )
        existing_evidence = self.store.get_record(RecordKind.EVIDENCE, evidence_ref)
        evidence_idempotency = classify_persisted_identity(
            existing_evidence, RecordKind.EVIDENCE, evidence, revision=1
        )
        if evidence_idempotency.outcome is IdempotencyOutcome.CONFLICT:
            raise RuntimeError(
                "deterministic session participant evidence identity collision:"
                + evidence_ref
            )
        if existing_evidence is not None and existing is not None:
            return participant_ref, evidence_ref

        operations = []
        if existing_evidence is None:
            operations.append(PatchOperation(
                operation_ref="patch-operation:session-participant:evidence:"
                + semantic_fingerprint("session-participant-evidence-op", evidence_ref, 20),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.EVIDENCE,
                target_ref=evidence_ref,
                record_revision=1,
                payload=encode_record(RecordKind.EVIDENCE, evidence),
                reason="persist session transport participant evidence before Stage 0",
            ))
        evidence_fp = evidence_idempotency.expected.record_fingerprint
        if existing is None:
            try:
                agent_schema = self.store.repositories.schemas.authoritative("type:agent")
            except KeyError:
                agent_schema = None
            referent = Referent(
                referent_ref=participant_ref,
                storage_kind=StorageKind.ORDINARY,
                identity_status=IdentityStatus.RESOLVED,
                scope_ref=context_ref,
                context_refs=(context_ref,),
                provenance_refs=(source_ref, evidence_ref),
                permission_ref=permission_ref,
                metadata={
                    "identity_criterion": "session_scoped_transport_participant",
                    "global_person_identity_claimed": False,
                },
            )
            referent_fp = record_fingerprints(RecordKind.REFERENT, referent)[1]
            operations.append(
                PatchOperation(
                    operation_ref="patch-operation:session-participant:referent:"
                    + semantic_fingerprint("session-participant-referent-op", participant_ref, 20),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.REFERENT,
                    target_ref=participant_ref,
                    record_revision=1,
                    payload=encode_record(RecordKind.REFERENT, referent),
                    dependencies=(
                        RecordDependency(
                            RecordKind.EVIDENCE, evidence_ref, 1, evidence_fp,
                            "session_participant_identity_evidence",
                        ),
                    ),
                    reason="persist session-scoped discourse participant identity",
                )
            )
            if agent_schema is not None:
                assertion = ReferentTypeAssertion(
                    assertion_ref="type-assertion:session-agent:"
                    + semantic_fingerprint("session-agent-assertion", participant_ref, 20),
                    referent_ref=participant_ref,
                    type_schema_ref="type:agent",
                    type_revision=agent_schema.revision,
                    status=AssertionStatus.SUPPORTED,
                    confidence=1.0,
                    context_ref=context_ref,
                    evidence_refs=(evidence_ref,),
                    source_refs=(source_ref,),
                    permission_ref=permission_ref,
                )
                operations.append(
                    PatchOperation(
                        operation_ref="patch-operation:session-participant:type:"
                        + semantic_fingerprint("session-participant-type-op", participant_ref, 20),
                        operation_kind=PatchOperationKind.UPSERT,
                        record_kind=RecordKind.TYPE_ASSERTION,
                        target_ref=assertion.assertion_ref,
                        record_revision=1,
                        payload=encode_record(RecordKind.TYPE_ASSERTION, assertion),
                        dependencies=(
                            RecordDependency(
                                RecordKind.REFERENT, participant_ref, 1, referent_fp,
                                "session_participant_referent",
                            ),
                            RecordDependency(
                                RecordKind.EVIDENCE, evidence_ref, 1, evidence_fp,
                                "session_participant_type_evidence",
                            ),
                        ),
                        reason="assert only the transport-grounded agent role of the session participant",
                    )
                )

        with self.store.snapshot() as snapshot:
            patch = GraphPatch(
                patch_ref="graph-patch:session-participant:"
                + semantic_fingerprint(
                    "session-participant-patch",
                    (participant_ref, evidence_ref, snapshot.fingerprint),
                    24,
                ),
                context_ref=context_ref,
                scope_ref="runtime:session-participant",
                source_ref=source_ref,
                permission_ref=permission_ref,
                operations=tuple(operations),
                expected_store_revision=snapshot.store_revision,
                evidence_refs=(evidence_ref,),
                validation_requirements=(
                    "session_participant_is_scope_local",
                    "no_global_person_identity_invention",
                ),
            )
        result = self.store.apply_patch(patch)
        if not result.committed:
            # A concurrent creator is safe only if the same deterministic identity/evidence now exists.
            if (
                self.store.get_record(RecordKind.REFERENT, participant_ref) is None
                or self.store.get_record(RecordKind.EVIDENCE, evidence_ref) is None
            ):
                raise RuntimeError(
                    "session participant initialization failed: "
                    + "; ".join(result.errors)
                )
        return participant_ref, evidence_ref

    def run_text(
        self,
        text: str,
        *,
        context_id: str = "conversation",
        language_hint: str | None = None,
        target_language: str | None = None,
        audience_refs: tuple[str, ...] = (),
        speaker_ref: str | None = None,
        permission_ref: str = "conversation",
        channel_ref: str = "text",
        emission_idempotency_key: str | None = None,
        discourse_anchors: tuple[Any, ...] = (),
        multimodal_tracks: tuple[Any, ...] = (),
        system_output_anchors: tuple[Any, ...] = (),
        grounding_constraints: tuple[Any, ...] = (),
    ) -> RuntimeResult:
        # Hints/anchors/tracks are evidence inputs only. Stage 2/3 validate and
        # combine them with reviewed language/schema authority; none route domain
        # semantics directly.
        from .learning.runtime import LearningRuntimeActivator
        from .runtime_state import RuntimeSelfObserver
        _learning_activation = LearningRuntimeActivator(self.store).activate_ready()
        RuntimeSelfObserver(self.store, self.services).observe(context_ref=context_id, permission_ref=permission_ref)
        resolved_speaker_ref, participant_evidence_ref = self._ensure_session_participant(
            context_id, permission_ref, speaker_ref
        )
        resolved_audience_refs = tuple(audience_refs) or (resolved_speaker_ref,)
        envelope = RuntimeInput(
            content=text,
            language_hints=() if language_hint is None else (language_hint,),
            emission_idempotency_key=emission_idempotency_key,
            discourse_anchors=discourse_anchors,
            multimodal_tracks=multimodal_tracks,
            system_output_anchors=system_output_anchors,
            grounding_constraints=grounding_constraints,
            speaker_ref=resolved_speaker_ref,
            participant_evidence_refs=(participant_evidence_ref,),
        )
        cycle=self.orchestrator.run(
            envelope,
            context_ref=context_id,
            permission_ref=permission_ref,
            audience_refs=resolved_audience_refs,
            target_language=target_language,
            channel_ref=channel_ref,
        )
        candidate=cycle.artifacts.get("surface_candidate"); emission=cycle.artifacts.get("emission")
        output_text=candidate.surface if emission is not None and candidate is not None else None
        committed=tuple(cycle.artifacts.get("committed_patch_refs",()))
        return RuntimeResult(cycle.cycle_ref,cycle.context_ref,output_text,cycle.target_language,tuple(cycle.trace),tuple(sorted(set(cycle.frontiers))),tuple(cycle.errors),dict(cycle.artifacts),committed)

    def close(self) -> None:
        self.store.close()


def build_runtime(*, database_path:str=":memory:",boot_database_path:str|Path|None=None,authority_guard:RuntimeAuthorityGuard,services:RuntimeServices|None=None) -> Runtime:
    if authority_guard is None:
        raise TypeError("canonical v3.5 runtime requires RuntimeAuthorityGuard")
    authority_guard.require_service_authority()
    store=SemanticStore(database_path,boot_path=boot_database_path)
    if services is None:
        from .runtime_services import build_canonical_runtime_services
        services=build_canonical_runtime_services(
            store, authority_manifest=getattr(authority_guard, "manifest", None)
        )
    epoch=getattr(authority_guard,"runtime_epoch",None)
    attestation=getattr(authority_guard,"attestation",None)
    if epoch is not None:
        services.runtime_epoch_ref=epoch.epoch_ref
        services.runtime_authority_generation=epoch.generation
    if attestation is not None:
        services.runtime_attestation_ref=attestation.attestation_ref
    from .runtime_hardening import HardenedRuntimeCoordinator
    coordinator=HardenedRuntimeCoordinator(store,services)
    adapters=build_stage_adapters(coordinator)
    orchestrator=CanonicalOrchestrator(adapters,snapshot_provider=StoreSnapshotProvider(store),authority_guard=authority_guard)
    return Runtime(store=store,orchestrator=orchestrator,services=services)


__all__=["Runtime","RuntimeServices","CanonicalRuntimeCoordinator","StoreSnapshotProvider","build_runtime"]
