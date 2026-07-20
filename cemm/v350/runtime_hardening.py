"""Hardened cross-stage coordinator for the canonical CEMM v3.5 runtime.

The existing phase components remain independently testable.  This coordinator
closes the architectural gaps between them: immutable semantic-pass re-entry,
typed non-text observations, Stage-4 -> Stage-5 applicability factors, typed
learning frontiers, response pre-commit authorization, and operation-result
re-entry without direct world-state mutation.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from .knowledge_factors import ReferentKnowledgeFactorBinder
from .epistemic_runtime import AdmittedEventProjector, RuntimeEpistemicCoordinator
from .learning.frontier import FrontierCollector, FrontierObservation
from .runtime import CanonicalRuntimeCoordinator
from .runtime_kernel import (
    FrontierClass,
    ObservationBatch,
    ObservationEnvelope,
    ObservationKind,
    ParticipantFrame,
    RuntimeBudgetSet,
    RuntimeFrontier,
    SemanticReentryRequest,
    StructuredObservationAnalysis,
)
from .schema.model import SchemaClass, semantic_fingerprint
from .storage.model import RecordKind
from .orchestration import CoreStage, CycleState, StageCapability, StageOutcome


class HardenedRuntimeCoordinator(CanonicalRuntimeCoordinator):
    """Canonical coordinator with cross-phase invariants enforced explicitly."""

    def stage_00_orient_and_pin(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        outcome = super().stage_00_orient_and_pin(cycle, capability)
        budgets = cycle.artifacts.get("runtime_budgets")
        if not isinstance(budgets, RuntimeBudgetSet):
            budgets = RuntimeBudgetSet()
        runtime_frontiers: list[RuntimeFrontier] = []
        frame = cycle.artifacts.get("participant_frame")
        if frame is None:
            envelope = cycle.input_payload
            speaker_ref = getattr(envelope, "speaker_ref", None)
            evidence_refs = tuple(
                getattr(envelope, "participant_evidence_refs", ())
            )
            system_ref = getattr(self.services, "speaker_ref", None)
            if speaker_ref and system_ref and cycle.audience_refs and evidence_refs:
                frame = ParticipantFrame(
                    frame_ref="participant-frame:"
                    + semantic_fingerprint(
                        "participant-frame",
                        (
                            cycle.context_ref,
                            speaker_ref,
                            system_ref,
                            cycle.audience_refs,
                            evidence_refs,
                        ),
                        24,
                    ),
                    system_ref=system_ref,
                    input_speaker_ref=speaker_ref,
                    input_addressee_refs=(system_ref,),
                    response_audience_refs=tuple(cycle.audience_refs),
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                    identity_evidence_refs=evidence_refs,
                )
            else:
                runtime_frontiers.append(
                    RuntimeFrontier(
                        frontier_ref="runtime-frontier:participant-frame:"
                        + semantic_fingerprint(
                            "participant-frame-gap",
                            (
                                cycle.cycle_ref,
                                cycle.context_ref,
                                speaker_ref,
                                system_ref,
                                cycle.audience_refs,
                            ),
                            20,
                        ),
                        frontier_class=FrontierClass.REFERENCE_AMBIGUITY,
                        missing_contract="participant_frame",
                        target_refs=tuple(
                            ref for ref in (speaker_ref, system_ref) if ref
                        ),
                        evidence_refs=evidence_refs or (cycle.cycle_ref,),
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                    )
                )
        return StageOutcome(
            {
                **dict(outcome.artifacts),
                "participant_frame": frame,
                "runtime_budgets": budgets,
                "runtime_frontiers": tuple(runtime_frontiers),
            },
            frontier_refs=outcome.frontier_refs,
            errors=outcome.errors,
        )

    def stage_01_observe(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        if not isinstance(cycle.input_payload, ObservationBatch):
            return super().stage_01_observe(cycle, capability)

        batch = cycle.input_payload
        if batch.context_ref != cycle.context_ref or batch.permission_ref != cycle.permission_ref:
            return StageOutcome(
                {
                    "observation_batch": batch,
                    "stage01_receipt": self._receipt(
                        CoreStage.OBSERVE,
                        "blocked",
                        "reentry_observation_scope_mismatch",
                    ),
                },
                frontier_refs=(f"runtime-frontier:observation-scope:{batch.batch_ref}",),
            )
        from .storage import EvidenceRecord

        lineage_refs = tuple(
            sorted(
                {
                    ref
                    for item in batch.observations
                    for ref in (*item.evidence_refs, *item.lineage_refs)
                }
            )
        )
        evidence_ref = "evidence:observation-batch:" + semantic_fingerprint(
            "observation-batch-evidence",
            (
                batch.batch_ref,
                tuple(item.observation_ref for item in batch.observations),
                lineage_refs,
            ),
            24,
        )
        batch_evidence = EvidenceRecord(
            evidence_ref=evidence_ref,
            source_ref=batch.batch_ref,
            confidence=min(item.confidence for item in batch.observations),
            lineage_ref=batch.batch_ref,
            context_ref=batch.context_ref,
            permission_ref=batch.permission_ref,
            metadata={
                "observation_kind_refs": tuple(
                    sorted({item.kind.value for item in batch.observations})
                ),
                "source_lineage_refs": lineage_refs,
                "semantic_authority": False,
            },
        )
        return StageOutcome(
            {
                "observation_batch": batch,
                "structured_observations": batch.observations,
                "input_evidence_record": batch_evidence,
                "stage01_receipt": self._receipt(
                    CoreStage.OBSERVE,
                    "performed",
                    "typed_observation_batch_preserved",
                    evidence=(batch_evidence.evidence_ref, *lineage_refs),
                ),
            }
        )

    def stage_02_analyze_and_fuse_form(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        if not isinstance(cycle.input_payload, ObservationBatch):
            return super().stage_02_analyze_and_fuse_form(cycle, capability)

        batch = cycle.input_payload
        analyzers = getattr(self.services, "observation_analyzers", {}) or {}
        analyses: list[StructuredObservationAnalysis] = []
        frontiers: list[str] = []
        for observation in batch.observations:
            if observation.kind == ObservationKind.TEXT:
                frontiers.append(
                    "runtime-frontier:typed-text-observation:"
                    + semantic_fingerprint(
                        "typed-text-observation-gap",
                        (observation.observation_ref, observation.payload_ref),
                        20,
                    )
                )
                continue
            analyzer = analyzers.get(observation.kind.value)
            if analyzer is None:
                frontiers.append(
                    "runtime-frontier:observation-analyzer:"
                    + semantic_fingerprint(
                        "observation-analyzer-gap",
                        (
                            observation.kind.value,
                            observation.payload_ref,
                            observation.context_ref,
                        ),
                        20,
                    )
                )
                continue
            analysis = analyzer.analyze(
                observation=observation,
                store=self.store,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                participant_frame=cycle.artifacts.get("participant_frame"),
            )
            if not isinstance(analysis, StructuredObservationAnalysis):
                raise TypeError(
                    "reviewed observation analyzer must return StructuredObservationAnalysis"
                )
            if observation.observation_ref not in analysis.observation_refs:
                raise ValueError(
                    "structured observation analysis omitted its source observation"
                )
            analyses.append(analysis)

        graph = self._merge_structured_observation_graphs(tuple(analyses))
        status = "performed" if graph is not None else ("deferred" if frontiers else "no_authorized_work")
        return StageOutcome(
            {
                "structured_observation_analyses": tuple(analyses),
                "structured_observation_graph": graph,
                "form_lattice": None,
                "stage02_receipt": self._receipt(
                    CoreStage.ANALYZE_AND_FUSE_FORM,
                    status,
                    "reviewed_structured_observation_analysis",
                    evidence=tuple(
                        sorted(
                            {
                                ref
                                for item in analyses
                                for ref in (*item.proof_refs, *item.evidence_refs)
                            }
                        )
                    ),
                ),
            },
            frontier_refs=tuple(sorted(set(frontiers))),
        )

    def stage_03_generate_candidates(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        graph = cycle.artifacts.get("structured_observation_graph")
        if graph is None:
            return super().stage_03_generate_candidates(cycle, capability)
        return StageOutcome(
            {
                "stage03_receipt": self._receipt(
                    CoreStage.GENERATE_REFERENT_AND_SCHEMA_CANDIDATES,
                    "performed",
                    "structured_analyzer_supplied_candidate_uol",
                    evidence=graph.evidence_refs,
                )
            },
            frontier_refs=tuple(graph.unresolved_refs),
        )

    def stage_04_project_knowledge(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        graph = cycle.artifacts.get("structured_observation_graph")
        if graph is None:
            return super().stage_04_project_knowledge(cycle, capability)
        from .facets.projector import ReferentKnowledgeProjector

        projections = {}
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            projector = ReferentKnowledgeProjector(self.store)
            for ref in sorted(graph.referents):
                if self.store.get_record(RecordKind.REFERENT, ref, snapshot=snapshot) is None:
                    continue
                projections[ref] = projector.project(
                    ref,
                    context_ref=cycle.context_ref,
                    at_time=None,
                    snapshot=snapshot,
                )
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome(
            {
                "referent_projections": projections,
                "stage04_receipt": self._receipt(
                    CoreStage.PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS,
                    "performed",
                    "structured_observation_referent_knowledge_projected",
                    evidence=tuple(sorted(projections)),
                ),
            }
        )

    def stage_05_build_factor_graph(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        structured = cycle.artifacts.get("structured_observation_graph")
        if structured is not None:
            return StageOutcome(
                {
                    "stage05_receipt": self._receipt(
                        CoreStage.BUILD_UOL_FACTOR_GRAPH,
                        "performed",
                        "structured_observation_uol_already_proof_constrained",
                        evidence=structured.evidence_refs,
                    )
                },
                frontier_refs=tuple(structured.unresolved_refs),
            )
        outcome = super().stage_05_build_factor_graph(cycle, capability)
        graph = outcome.artifacts.get("meaning_factor_graph")
        lattice = cycle.artifacts.get("form_lattice")
        grounding = outcome.artifacts.get("grounding_result")
        projections = cycle.artifacts.get("referent_projections", {})
        if graph is None or lattice is None or grounding is None:
            return outcome
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            bound = ReferentKnowledgeFactorBinder(self.store).bind(
                graph,
                lattice=lattice,
                projections=projections,
                snapshot=snapshot,
            )
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome(
            {
                **dict(outcome.artifacts),
                "meaning_factor_graph": bound,
                "stage05_receipt": self._receipt(
                    CoreStage.BUILD_UOL_FACTOR_GRAPH,
                    "performed",
                    "unified_factor_graph_includes_stage4_projection_constraints",
                    evidence=bound.evidence_refs,
                ),
            },
            frontier_refs=tuple(sorted(set((*outcome.frontier_refs, *bound.unresolved_refs)))),
            errors=outcome.errors,
        )

    def stage_06_solve_meaning(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        graph = cycle.artifacts.get("structured_observation_graph")
        if graph is None:
            return super().stage_06_solve_meaning(cycle, capability)
        return StageOutcome(
            {
                "stage06_receipt": self._receipt(
                    CoreStage.SOLVE_MEANING_HYPOTHESES,
                    "performed",
                    "structured_analyzer_proof_is_single_bounded_hypothesis",
                    evidence=graph.evidence_refs,
                )
            },
            frontier_refs=tuple(graph.unresolved_refs),
        )

    def stage_07_select_meaning(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        graph = cycle.artifacts.get("structured_observation_graph")
        if graph is None:
            return super().stage_07_select_meaning(cycle, capability)
        return StageOutcome(
            {
                "selected_structured_uol_graph": graph,
                "stage07_receipt": self._receipt(
                    CoreStage.SELECT_MEANING_BUNDLE,
                    "performed",
                    "reviewed_structured_observation_uol_selected",
                    evidence=graph.evidence_refs,
                ),
            },
            frontier_refs=tuple(graph.unresolved_refs),
        )

    def stage_08_classify_discourse(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        graph = cycle.artifacts.get("selected_structured_uol_graph")
        if graph is None:
            return super().stage_08_classify_discourse(cycle, capability)
        from .discourse import DiscourseClassifier
        from .uol.validator import UOLValidator

        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            classifier = DiscourseClassifier(self.store)
            classification = classifier.classify(graph, snapshot=snapshot)
            attribution = classifier.attribute_claims(
                graph,
                classification,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                snapshot=snapshot,
            )
            validation = UOLValidator(
                self.store.repositories.schemas.registry(snapshot=snapshot)
            ).validate(attribution.graph, provisional=True)
            validation.require_valid()
        finally:
            cm.__exit__(None, None, None)
        validation_frontiers = tuple(
            f"uol-validation:{item.code}:{item.target_ref}"
            for item in validation.unresolved
        )
        frontiers = tuple(
            sorted(
                set(
                    (
                        *classification.unresolved_refs,
                        *attribution.unresolved_refs,
                        *validation_frontiers,
                    )
                )
            )
        )
        return StageOutcome(
            {
                "discourse_classification": classification,
                "attribution_result": attribution,
                "epistemic_uol_graph": attribution.graph,
                "stage08_receipt": self._receipt(
                    CoreStage.CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS,
                    "performed",
                    "structured_observation_classified_and_attributed",
                    evidence=attribution.evidence_refs,
                ),
            },
            frontier_refs=frontiers,
        )

    @staticmethod
    def _merge_structured_observation_graphs(
        analyses: tuple[StructuredObservationAnalysis, ...],
    ):
        if not analyses:
            return None
        from .uol.model import UOLGraph

        def merge_mapping(name: str):
            merged = {}
            for analysis in analyses:
                for ref, value in getattr(analysis.graph, name).items():
                    existing = merged.get(ref)
                    if existing is not None and existing != value:
                        raise ValueError(
                            f"structured observation graph identity collision: {name}:{ref}"
                        )
                    merged[ref] = value
            return merged

        def merge_tuple(name: str, ref_attr: str):
            merged = {}
            for analysis in analyses:
                for value in getattr(analysis.graph, name):
                    ref = getattr(value, ref_attr)
                    existing = merged.get(ref)
                    if existing is not None and existing != value:
                        raise ValueError(
                            f"structured observation graph identity collision: {name}:{ref}"
                        )
                    merged[ref] = value
            return tuple(merged[key] for key in sorted(merged))

        return UOLGraph(
            graph_ref="structured-observation-graph:"
            + semantic_fingerprint(
                "structured-observation-graph",
                tuple(
                    (
                        item.analyzer_ref,
                        item.analyzer_revision,
                        item.observation_refs,
                        item.graph.record_fingerprint,
                    )
                    for item in analyses
                ),
                24,
            ),
            referents=merge_mapping("referents"),
            applications=merge_mapping("applications"),
            variables=merge_mapping("variables"),
            coordination_groups=merge_mapping("coordination_groups"),
            propositions=merge_mapping("propositions"),
            claims=merge_mapping("claims"),
            events=merge_mapping("events"),
            scope_relations=merge_tuple("scope_relations", "scope_relation_ref"),
            state_deltas=merge_tuple("state_deltas", "delta_ref"),
            capability_deltas=merge_tuple("capability_deltas", "delta_ref"),
            impact_assessments=merge_tuple(
                "impact_assessments", "assessment_ref"
            ),
            importance_assessments=merge_tuple(
                "importance_assessments", "assessment_ref"
            ),
            root_refs=tuple(
                sorted(
                    {
                        root
                        for item in analyses
                        for root in item.graph.root_refs
                    },
                    key=lambda item: (item.filler_class.value, item.ref),
                )
            ),
            unresolved_refs=tuple(
                sorted(
                    {
                        ref
                        for item in analyses
                        for ref in item.graph.unresolved_refs
                    }
                )
            ),
            assumptions=tuple(
                sorted(
                    {
                        ref
                        for item in analyses
                        for ref in item.graph.assumptions
                    }
                )
            ),
            evidence_refs=tuple(
                sorted(
                    {
                        ref
                        for item in analyses
                        for ref in (
                            *item.graph.evidence_refs,
                            *item.evidence_refs,
                            *item.proof_refs,
                        )
                    }
                )
            ),
        )

    def stage_09_epistemically_assess(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        base = super().stage_09_epistemically_assess(cycle, capability)
        lineages = tuple(base.artifacts.get("compiled_claim_lineages", ()))
        provider = getattr(self.services, "epistemic_policy_provider", None)
        if not lineages or provider is None:
            runtime_frontiers = list(cycle.artifacts.get("runtime_frontiers", ()))
            if lineages and provider is None:
                runtime_frontiers.append(
                    RuntimeFrontier(
                        frontier_ref="runtime-frontier:epistemic-policy:"
                        + semantic_fingerprint(
                            "epistemic-policy-gap",
                            (
                                cycle.pass_ref,
                                tuple(
                                    sorted(
                                        item.claim_record.proposition_ref
                                        for item in lineages
                                    )
                                ),
                            ),
                            20,
                        ),
                        frontier_class=FrontierClass.POLICY_BLOCK,
                        missing_contract="epistemic_policy_provider",
                        target_refs=tuple(
                            sorted(
                                {
                                    item.claim_record.proposition_ref
                                    for item in lineages
                                }
                            )
                        ),
                        evidence_refs=tuple(
                            sorted(
                                {
                                    ref
                                    for item in lineages
                                    for ref in item.claim_record.evidence_refs
                                }
                            )
                        )
                        or (cycle.cycle_ref,),
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                    )
                )
            return StageOutcome(
                {
                    **dict(base.artifacts),
                    "prepared_epistemic_admissions": (),
                    "runtime_frontiers": tuple(runtime_frontiers),
                },
                frontier_refs=base.frontier_refs,
                errors=base.errors,
            )

        allowed = {
            item.claim_record.proposition_ref
            for item in lineages
        }
        proposals = tuple(
            provider.proposals(
                attributed_claims=lineages,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                store=self.store,
            )
        )
        prepared = RuntimeEpistemicCoordinator(self.store).prepare(
            proposals,
            allowed_proposition_refs=allowed,
        )
        return StageOutcome(
            {
                **dict(base.artifacts),
                "prepared_epistemic_admissions": prepared,
                "epistemic_policy_provider_ref": getattr(
                    provider, "provider_ref", ""
                ),
                "epistemic_policy_provider_revision": getattr(
                    provider, "provider_revision", ""
                ),
                "stage09_receipt": self._receipt(
                    CoreStage.EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT,
                    "performed",
                    "claims_attributed_and_epistemic_policy_assessed",
                    evidence=tuple(
                        sorted(
                            {
                                ref
                                for item in prepared
                                for ref in item.assessment.evidence_refs
                            }
                        )
                    ),
                ),
            },
            frontier_refs=base.frontier_refs,
            errors=base.errors,
        )

    def stage_12_preview_transitions(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        base = super().stage_12_preview_transitions(cycle, capability)
        engine = getattr(self.services, "inference_engine", None)
        runtime_frontiers = list(cycle.artifacts.get("runtime_frontiers", ()))
        if engine is None:
            frontier = RuntimeFrontier(
                frontier_ref="runtime-frontier:generic-inference:"
                + semantic_fingerprint(
                    "generic-inference-authority-gap",
                    (cycle.pass_ref, cycle.context_ref),
                    20,
                ),
                frontier_class=FrontierClass.RUNTIME_CAPABILITY,
                missing_contract="generic_proof_bearing_inference_engine",
                target_refs=(),
                evidence_refs=(cycle.cycle_ref,),
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
            )
            runtime_frontiers.append(frontier)
            return StageOutcome(
                {
                    **dict(base.artifacts),
                    "inference_preview": None,
                    "runtime_frontiers": tuple(runtime_frontiers),
                    "stage12_receipt": self._receipt(
                        CoreStage.INFER_AND_PREVIEW_TRANSITIONS,
                        "deferred",
                        "transition_preview_completed_but_generic_inference_authority_missing",
                    ),
                },
                frontier_refs=tuple(
                    sorted(set((*base.frontier_refs, frontier.frontier_ref)))
                ),
                errors=base.errors,
            )

        with self.store.snapshot() as snapshot:
            preview = engine.preview(
                graph=cycle.artifacts.get("epistemic_uol_graph"),
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                snapshot=snapshot,
                budget=cycle.artifacts.get("runtime_budgets"),
            )
        if not getattr(preview, "proof_refs", ()):
            raise ValueError("generic inference preview requires proof lineage")
        if not getattr(preview, "rule_pins", ()):
            raise ValueError("generic inference preview requires exact rule pins")
        return StageOutcome(
            {
                **dict(base.artifacts),
                "inference_preview": preview,
                "runtime_frontiers": tuple(runtime_frontiers),
                "stage12_receipt": self._receipt(
                    CoreStage.INFER_AND_PREVIEW_TRANSITIONS,
                    "performed",
                    "proof_bearing_inference_and_transition_preview_completed",
                    evidence=tuple(getattr(preview, "proof_refs", ())),
                ),
            },
            frontier_refs=tuple(
                sorted(
                    set(
                        (
                            *base.frontier_refs,
                            *tuple(getattr(preview, "frontier_refs", ())),
                        )
                    )
                )
            ),
            errors=base.errors,
        )

    def stage_13_commit_knowledge_state(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        base = super().stage_13_commit_knowledge_state(cycle, capability)
        prepared = tuple(cycle.artifacts.get("prepared_epistemic_admissions", ()))
        if not prepared:
            return base

        from .epistemics.patches import EpistemicPatchPlanner
        from .transitions.coordinator import TransitionCoordinator

        committed = list(base.artifacts.get("committed_patch_refs", ()))
        persisted = set(base.artifacts.get("persisted_semantic_refs", ()))
        transition_plans = list(
            base.artifacts.get("canonical_transition_plans", ())
        )
        admissions = []
        admitted_events = []
        deferred = list(base.frontier_refs)
        planner = EpistemicPatchPlanner()

        for item in prepared:
            with self.store.snapshot() as snapshot:
                patch = planner.admission_patch(
                    item.admission,
                    item.knowledge,
                    item.source_assessments,
                    expected_store_revision=snapshot.store_revision,
                )
            result = self.store.apply_patch(patch)
            if not result.committed:
                raise RuntimeError(
                    "epistemic admission commit failed: "
                    + "; ".join(result.errors)
                )
            committed.append(patch.patch_ref)
            admissions.append(item.admission)
            persisted.add(item.admission.admission_ref)
            persisted.update(
                assessment.assessment_ref
                for assessment in item.source_assessments
            )
            if item.knowledge is not None:
                persisted.add(item.knowledge.knowledge_ref)

            if getattr(item.admission.decision, "value", item.admission.decision) != "admit_support":
                continue

            projected = AdmittedEventProjector(self.store).patches_for_admission(
                item.admission
            )
            for event_patch, event in projected:
                event_result = self.store.apply_patch(event_patch)
                if not event_result.committed:
                    raise RuntimeError(
                        "admitted event projection failed: "
                        + "; ".join(event_result.errors)
                    )
                committed.append(event_patch.patch_ref)
                admitted_events.append(event)
                persisted.update(
                    operation.target_ref
                    for operation in event_patch.operations
                )

                coordinator = TransitionCoordinator(self.store)
                event_plans = tuple(
                    coordinator.plans_for_event(
                        event,
                        effective_time_ref=(
                            event.time_ref
                            or cycle.artifacts["cycle_pins"].cycle_time
                        ),
                    )
                )
                for plan in event_plans:
                    if not plan.preview.authorized or plan.preview.proof is None:
                        deferred.extend(
                            frontier.frontier_ref
                            for frontier in plan.preview.frontiers
                        )
                        continue
                    effect_patch = coordinator.build_patch(
                        event,
                        plan,
                        source_ref="source:stage13:admitted-transition",
                        permission_ref=cycle.permission_ref,
                    )
                    effect_result = self.store.apply_patch(effect_patch)
                    if not effect_result.committed:
                        raise RuntimeError(
                            "admitted transition commit failed: "
                            + "; ".join(effect_result.errors)
                        )
                    committed.append(effect_patch.patch_ref)
                    persisted.update(
                        operation.target_ref
                        for operation in effect_patch.operations
                    )
                transition_plans.append((event.event_ref, event_plans))

        return StageOutcome(
            {
                **dict(base.artifacts),
                "committed_patch_refs": tuple(committed),
                "persisted_semantic_refs": tuple(sorted(persisted)),
                "canonical_transition_plans": tuple(transition_plans),
                "epistemic_admission_records": tuple(admissions),
                "admitted_event_records": tuple(admitted_events),
                "stage13_receipt": self._receipt(
                    CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE,
                    "performed",
                    "selected_meaning_epistemics_and_authorized_transitions_committed",
                    evidence=tuple(
                        sorted(
                            {
                                *(item.admission_ref for item in admissions),
                                *(item.event_ref for item in admitted_events),
                            }
                        )
                    ),
                ),
            },
            frontier_refs=tuple(sorted(set(deferred))),
            errors=base.errors,
        )

    def stage_11_learning_frontiers(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        observations: list[FrontierObservation] = []

        lattice = cycle.artifacts.get("form_lattice")
        if lattice is not None:
            for span in lattice.unresolved_spans:
                observations.append(
                    FrontierObservation(
                        missing_contract="language_form_or_sense",
                        expected_record_kinds=(
                            RecordKind.LANGUAGE_FORM,
                            RecordKind.LEXICAL_SENSE,
                        ),
                        expected_schema_classes=(),
                        accepted_anchor_types=(),
                        evidence_refs=(lattice.lattice_ref,),
                        target_ref=f"span:{span.start}:{span.end}",
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                    )
                )

        grounding = cycle.artifacts.get("grounding_result")
        if grounding is not None:
            for ref in tuple(
                sorted(
                    set(
                        (*grounding.frontier_refs, *grounding.unresolved_mention_refs)
                    )
                )
            ):
                observations.append(
                    FrontierObservation(
                        missing_contract="referent_or_schema_grounding",
                        expected_record_kinds=(RecordKind.REFERENT, RecordKind.SCHEMA),
                        expected_schema_classes=(SchemaClass.REFERENT_TYPE,),
                        accepted_anchor_types=(),
                        evidence_refs=tuple(grounding.evidence_refs) or (cycle.cycle_ref,),
                        target_ref=ref,
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                    )
                )

        bundle = cycle.artifacts.get("meaning_bundle")
        if bundle is not None:
            for ref in bundle.partial_understanding.unresolved_refs:
                observations.append(
                    FrontierObservation(
                        missing_contract="semantic_composition_dependency",
                        expected_record_kinds=(
                            RecordKind.SCHEMA,
                            RecordKind.SEMANTIC_APPLICATION,
                        ),
                        expected_schema_classes=(),
                        accepted_anchor_types=(),
                        evidence_refs=tuple(bundle.evidence_refs) or (cycle.cycle_ref,),
                        target_ref=ref,
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                    )
                )

        retrieval = cycle.artifacts.get("retrieval_result")
        if retrieval is not None:
            for ref in retrieval.unresolved_query_refs:
                observations.append(
                    FrontierObservation(
                        missing_contract="query_binding_or_knowledge",
                        expected_record_kinds=(
                            RecordKind.KNOWLEDGE,
                            RecordKind.SEMANTIC_APPLICATION,
                        ),
                        expected_schema_classes=(),
                        accepted_anchor_types=(),
                        evidence_refs=tuple(retrieval.evidence_refs) or (cycle.cycle_ref,),
                        target_ref=ref,
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                    )
                )

        # Deliberately do not reinterpret arbitrary runtime frontier strings as
        # semantic learning requests. Missing adapters, permissions, budgets and
        # emission authority remain runtime frontiers.
        budget = cycle.artifacts.get("runtime_budgets")
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
        collector = FrontierCollector()
        if isinstance(budget, RuntimeBudgetSet):
            collector.budget = replace(
                collector.budget,
                maximum_frontiers=min(
                    collector.budget.maximum_frontiers,
                    budget.learning_frontiers,
                ),
            )
        frontiers = collector.collect(tuple(observations), existing)
        return StageOutcome(
            {
                "learning_observations": tuple(observations),
                "learning_frontier_records": frontiers,
                "stage11_receipt": self._receipt(
                    CoreStage.BUILD_OR_ADVANCE_LEARNING_FRONTIERS,
                    "performed" if observations else "no_authorized_work",
                    "typed_learning_frontiers_preserved",
                ),
            },
            frontier_refs=tuple(item.frontier_ref for item in frontiers),
        )

    def stage_17_reconcile_operations(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        outcome = super().stage_17_reconcile_operations(cycle, capability)
        new_reconciliations = tuple(
            item
            for item in outcome.artifacts.get("operation_reconciliations", ())
            if item not in tuple(cycle.artifacts.get("operation_reconciliations", ()))
        )
        pending = tuple(cycle.artifacts.get("stage16_pending_outcomes", ()))
        observations: list[ObservationEnvelope] = []
        for _plan, _auth, _assessments, journal, result in pending:
            if journal is None or result is None:
                continue
            observations.append(
                ObservationEnvelope(
                    observation_ref="observation:operation-result:"
                    + semantic_fingerprint(
                        "operation-result-observation",
                        (
                            result.result_ref,
                            result.revision,
                            journal.journal_ref,
                            journal.revision,
                        ),
                        24,
                    ),
                    kind=ObservationKind.OPERATION_RESULT,
                    source_ref=journal.adapter_ref,
                    payload_ref=result.result_ref,
                    context_ref=result.context_ref,
                    permission_ref=result.permission_ref,
                    observed_at=journal.observed_at,
                    confidence=1.0,
                    evidence_refs=tuple(result.evidence_refs),
                    lineage_refs=tuple(
                        sorted(
                            {
                                result.result_ref,
                                journal.journal_ref,
                                *result.proof_refs,
                            }
                        )
                    ),
                    metadata={
                        "operation_result_status": result.status.value,
                        "transport_acknowledged": result.transport_acknowledged,
                        "domain_result_refs": result.domain_result_refs,
                        # These are observation claims only. They are never consumed
                        # as direct state mutation authority.
                        "reported_effect_refs": result.observed_effect_refs,
                        "uncertainty_refs": result.uncertainty_refs,
                    },
                )
            )

        if not observations:
            return StageOutcome(
                dict(outcome.artifacts),
                frontier_refs=outcome.frontier_refs,
                errors=outcome.errors,
                request_goal_refresh=False,
            )

        batch = ObservationBatch(
            batch_ref="observation-batch:operation-reentry:"
            + semantic_fingerprint(
                "operation-reentry-batch",
                tuple(item.observation_ref for item in observations),
                24,
            ),
            observations=tuple(observations),
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            parent_pass_ref=getattr(cycle, "pass_ref", None),
            reason_refs=tuple(
                sorted(
                    {
                        "operation_outcome_requires_semantic_reentry",
                        *(item.reconciliation_ref for item in new_reconciliations),
                    }
                )
            ),
        )
        budgets = cycle.artifacts.get("runtime_budgets")
        max_reentries = (
            budgets.semantic_reentries
            if isinstance(budgets, RuntimeBudgetSet)
            else 2
        )
        request = SemanticReentryRequest(
            request_ref="semantic-reentry:"
            + semantic_fingerprint(
                "semantic-reentry-request",
                (cycle.cycle_ref, getattr(cycle, "pass_ref", ""), batch.batch_ref),
                24,
            ),
            observation_batch=batch,
            reason_refs=batch.reason_refs,
            carry_artifact_keys=(
                "operation_outcomes",
                "operation_reconciliations",
                "operation_attempted_goal_refs",
                "emission_idempotency_key",
                "runtime_budgets",
                "runtime_frontiers",
                "participant_frame",
            ),
            max_reentries=max_reentries,
        )
        return StageOutcome(
            {
                **dict(outcome.artifacts),
                "operation_reentry_batch": batch,
            },
            frontier_refs=outcome.frontier_refs,
            errors=outcome.errors,
            request_goal_refresh=False,
            reentry_request=request,
        )

    def stage_18_build_response_uol(
        self, cycle: CycleState, capability: StageCapability
    ) -> StageOutcome:
        decision = cycle.artifacts.get("goal_decision")
        if decision is None or not decision.selected_goal_refs:
            return StageOutcome(
                {
                    "response_uol": None,
                    "stage18_receipt": self._receipt(
                        CoreStage.BUILD_RESPONSE_UOL,
                        "no_authorized_work",
                        "no_selected_response_goal",
                    ),
                }
            )

        from .response.coordinator import ResponseUOLCommitCoordinator
        from .response.planner import ResponseMeaningPlanner

        decision_stored = self.store.get_record(
            RecordKind.GOAL_DECISION, decision.decision_ref
        )
        if decision_stored is None:
            return self._missing(CoreStage.BUILD_RESPONSE_UOL, "goal_decision")
        rules = tuple(
            item.payload
            for item in self.store.repositories.response_transform_rules.all(
                all_revisions=True
            )
        )
        try:
            response, proofs, frontiers = ResponseMeaningPlanner(
                self.store, rules
            ).plan(
                self._pin(decision_stored),
                audience_refs=cycle.audience_refs,
                perspective_ref="perspective:self",
            )
            ResponseUOLCommitCoordinator(
                self.store,
                permission_evaluator=getattr(
                    self.services, "permission_evaluator", None
                ),
            ).commit(response, proofs, frontiers)
        except ValueError as exc:
            return StageOutcome(
                {
                    "response_uol": None,
                    "stage18_receipt": self._receipt(
                        CoreStage.BUILD_RESPONSE_UOL,
                        "deferred",
                        "response_uol_not_authorized",
                    ),
                },
                frontier_refs=(
                    "runtime-frontier:response:"
                    + semantic_fingerprint("response-frontier", str(exc), 20),
                ),
            )
        return StageOutcome(
            {
                "response_uol": response,
                "response_frontiers": frontiers,
                "stage18_receipt": self._receipt(
                    CoreStage.BUILD_RESPONSE_UOL,
                    "performed",
                    "response_uol_authorized_and_committed",
                    evidence=(response.response_ref,),
                ),
            },
            frontier_refs=tuple(item.frontier_ref for item in frontiers),
        )
