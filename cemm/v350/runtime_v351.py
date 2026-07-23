"""Canonical CEMM v3.5.1 runtime composition root.

This module intentionally imports neither v347 nor the legacy UOL/composition brain.
Stages 5-7 are real CSIR/recurrent/attractor service boundaries.  Until Phase 6+ installs
those exact services, the canonical runtime emits typed capability frontiers and does
not fall back to the quarantined v3.5 pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from pathlib import Path
from typing import Any, Mapping

from .csir.authority import CURRENT_KERNEL_ABI
from .csir.authority_v351 import AuthoritySnapshotV351
from .csir.compiler import ExactCSIRCompiler
from .csir.model import CSIRCandidate, CSIRCandidateFragment, CSIRGraph
from .observation import CanonicalOperationOutcomeAssimilatorV351, canonical_observation_adapters_v351
from .observation.runtime_bridge_v351 import (
    stage_01_observe_multimodal_evidence_v351,
    stage_02_encode_form_and_sensor_evidence_v351,
    stage_03_activate_and_ground_referents_v351,
)
from .finalization.runtime_v351 import CanonicalCycleFinalizerV351
from .runtime_support_v351 import SystemUTCClockV351
from .composition import ProjectionAwareDeterministicCSIRComposer
from .dynamics import (
    RecurrentAttractorStabilizerV351, RecurrentSemanticDynamicsV351,
    compile_reviewed_phase13_parameter_artifacts,
)
from .conversation import SessionDiscourseMemory, SessionMemoryCommitCoordinatorV351, participant_frame_session_anchors
from .discourse import DiscourseAuthorityMap, DiscourseStructureBuilderV351
from .epistemic import EpistemicAdmissionPolicy, EpistemicCoordinatorV351
from .query import GroundedQueryEngineV351
from .causal.commit_v351 import CompositeStage13CommitterV351
from .causal.authority_projection_v351 import project_state_causal_authority
from .causal.query_v351 import Phase16QueryEngineV351
from .causal.response_v351 import Phase16ResponseCSIRBuilderV351
from .causal.runtime_v351 import (
    CausalPlanningOperationEngineV351, CompositeGoalArbitratorV351,
    Phase15CausalSimulatorV351, Phase16ImpactRuntimeV351,
)
from .response import (
    ConversationalGoalBridgeV351, ResponseAuthorityMapV351, ResponseCSIRBuilderV351,
    ResponseFamily, compile_minimum_response_authority,
)
from .realization.english_v351 import (
    EnglishCSIRRealizerV351, EnglishRealizationPackageV351,
    compile_minimum_english_realization_package,
)
from .output.runtime_v351 import InProcessTextEmissionEngineV351, OutputDiscourseCommitterV351
from .output.authorization_v351 import DisclosureAuthorizationGrantV351
from .effects.authorization import (
    EffectAuthorizationBoundary, EffectAuthorizationReceipt, EffectAuthorizationRequest,
)
from .effects.store import AuthorizedEffectStore
from .facets.applicability_index_v351 import SchemaApplicabilityIndex
from .facets.closure import ReferentKnowledgeClosureCompiler
from .facets.projector import ReferentKnowledgeProjector
from .grounding.coordinator import JointGrounder
from .grounding.participants import participant_frame_anchors
from .language.analyzer import FormLatticeAnalyzer
from .learning.model import PinnedRecord
from .learning.engine_v351 import Phase14LearningEngineV351
from .learning.commit_v351 import Stage13LearningCommitterV351
from .learning.maintenance_v351 import Phase14LearningMaintenanceV351
from .maintenance import MaintenanceEvent, MaintenanceScheduler, MaintenanceTrigger
from .orchestration import (
    CanonicalOrchestrator, CognitiveCycleState, CoreStage, StageCapability,
    StageExecutionStatus, StageOutcome,
)
from .realization.policy import SelectiveRoundTripPolicy, VerificationMode
from .realization.proof_v351 import ExactRealizationProof, ExactRealizationProofVerifier
from .runtime_abi import (
    ActivationGraph, ActivationTrace, CSIRCandidateSet, CognitiveCyclePins,
    EmissionObservationArtifact, EvidenceEnvelope, EvidenceLattice, GroundingCandidateSet,
    RealizationPlanArtifact, RuntimeInput, RuntimeResult, SemanticAttractorSet,
    SurfaceCandidateArtifact, artifact_ref,
)
from .runtime_graph import build_stage_adapters
from .runtime_kernel import ParticipantFrame, RuntimeBudgetSet
from .schema.model import semantic_fingerprint
from .semantic_capability import CompiledSemanticCapabilityRegistry
from .service_loader import load_signed_runtime_services
from .stage_contracts import EffectKind
from .storage import SemanticStore
from .version import VERSION
from .workspace_store import CycleArtifactStoreView


@dataclass(slots=True)
class RuntimeServices:
    """Signed/injected v3.5.1 service slots.

    Empty semantic-brain slots are reported honestly as runtime capability frontiers;
    an empty slot never triggers a legacy fallback.
    """
    semantic_authority_snapshot: AuthoritySnapshotV351 | None = None
    syntax_adapters: Any | None = None
    clock: Any | None = None
    observation_analyzers: Mapping[str, Any] = field(default_factory=dict)
    composition_constraint_evaluator: Any | None = None
    discourse_authority_map: DiscourseAuthorityMap | None = None
    epistemic_admission_policy: EpistemicAdmissionPolicy | None = None
    response_authority_map: ResponseAuthorityMapV351 | None = None
    english_realization_package: EnglishRealizationPackageV351 | None = None
    text_channel_contract_pin: PinnedRecord | None = None
    disclosure_authorization_grants: tuple[DisclosureAuthorizationGrantV351, ...] = ()
    csir_compiler: Any | None = None
    recurrent_semantic_solver: Any | None = None
    semantic_attractor_stabilizer: Any | None = None
    discourse_structure_builder: Any | None = None
    epistemic_coordinator: Any | None = None
    query_engine: Any | None = None
    learning_engine: Any | None = None
    causal_simulator: Any | None = None
    commit_coordinator: Any | None = None
    impact_engine: Any | None = None
    goal_engine: Any | None = None
    operation_engine: Any | None = None
    operation_outcome_assimilator: Any | None = None
    response_csir_builder: Any | None = None
    realization_engine: Any | None = None
    emission_engine: Any | None = None
    independent_semantic_analyzer: Any | None = None
    channel_adapters: Mapping[str, Any] = field(default_factory=dict)
    emission_gate_evaluators: Mapping[str, Any] = field(default_factory=dict)
    output_discourse_engine: Any | None = None
    consolidation_engine: Any | None = None
    runtime_signal_provider: Any | None = None
    learning_maintenance: Any | None = None
    learning_competence_executors: Mapping[str, Any] = field(default_factory=dict)
    causal_query_contracts: tuple[Any, ...] = ()
    causal_impact_rules: tuple[Any, ...] = ()
    causal_goal_policy: Any | None = None
    causal_utility_evaluator: Any | None = None
    causal_utility_policy_pin: Any | None = None
    causal_parameter_lookup: Any | None = None
    state_manifold_transform_resolver: Any | None = None
    state_set_member_type_resolver: Any | None = None
    causal_capability_leaf_resolver: Any | None = None
    causal_aggregation_selection_evaluators: Mapping[str, Any] = field(default_factory=dict)
    causal_simulation_budget: Any | None = None
    system_ref: str = "referent:self"
    runtime_epoch_ref: str | None = None
    runtime_attestation_ref: str | None = None
    runtime_authority_generation: int | None = None
    retain_transient_audit: bool = False


class StoreSnapshotProvider:
    def __init__(self, store: SemanticStore) -> None:
        self.store = store
    def generation(self): return self.store.current_read_generation()
    def semantic_pass(self): return self.store.semantic_pass()


class _SessionRegistry:
    """In-memory transport/session grounding. No pre-Stage-0 durable writes."""
    def __init__(self) -> None:
        self._items = {}
        self._lock = RLock()

    def resolve(
        self, context_ref: str, permission_ref: str, requested_ref: str | None, store, *, system_ref: str
    ) -> tuple[str, str]:
        key = (context_ref, permission_ref, requested_ref)
        with self._lock:
            if key in self._items:
                return self._items[key]
        if requested_ref == system_ref:
            raise ValueError("public/session speaker identity cannot impersonate the CEMM self referent")
        participant_ref = None
        if requested_ref:
            from .storage.model import RecordKind
            durable = store.get_record(RecordKind.REFERENT, requested_ref)
            if durable is not None:
                contexts = set(getattr(durable.payload, "context_refs", ()) or ())
                visible = not contexts or "global" in contexts or context_ref in contexts
                permission = durable.permission_ref or getattr(durable.payload, "permission_ref", None)
                if not visible or permission not in {None, "public", permission_ref}:
                    raise ValueError("explicit speaker referent is not visible/authorized in this session")
                participant_ref = requested_ref
        if participant_ref is None:
            # An untrusted transport principal is mapped to a session-scoped semantic
            # referent instead of being allowed to inject an arbitrary semantic ref.
            participant_ref = "referent:session-participant:" + semantic_fingerprint(
                "session-participant", (context_ref, permission_ref, requested_ref or "anonymous"), 24
            )
        evidence_ref = "evidence:session-participant:" + semantic_fingerprint(
            "session-participant-evidence", (context_ref, participant_ref, permission_ref), 24
        )
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                return existing
            self._items[key] = (participant_ref, evidence_ref)
            return self._items[key]


class V351RuntimeCoordinator:
    def __init__(self, store: SemanticStore, services: RuntimeServices | None = None) -> None:
        self.store = store
        self.services = services or RuntimeServices()
        self.semantic_capabilities = CompiledSemanticCapabilityRegistry(store)
        self.exact_csir_compiler = ExactCSIRCompiler()
        self._authority_index_lock = RLock()
        self._schema_applicability_indexes = {}
        self.effect_boundary = EffectAuthorizationBoundary(store)
        self.realization_proof_verifier = ExactRealizationProofVerifier()
        self.roundtrip_policy = SelectiveRoundTripPolicy()
        self.session_memory = SessionDiscourseMemory()
        self._minimum_response_authority = compile_minimum_response_authority()
        self._minimum_english_realization = compile_minimum_english_realization_package()
        self._reviewed_phase13_dynamics = compile_reviewed_phase13_parameter_artifacts()
        if self.services.clock is None:
            self.services.clock = SystemUTCClockV351()
        self._canonical_observation_adapters = canonical_observation_adapters_v351()
        if self.services.learning_maintenance is None:
            self.services.learning_maintenance = Phase14LearningMaintenanceV351(
                store,
                competence_executors=self.services.learning_competence_executors,
            )
        response_authority_map = (
            self.services.response_authority_map or self._minimum_response_authority.authority_map
        )
        english_realization_package = (
            self.services.english_realization_package or self._minimum_english_realization
        )
        # Canonical pre-learned baseline services. Injected signed services replace
        # these by slot; this is not legacy fallback and never introduces another
        # semantic representation. All paths consume/produce exact CSIR.
        self._canonical_services = {
            "csir_compiler": ProjectionAwareDeterministicCSIRComposer(
                store, constraint_evaluator=self.services.composition_constraint_evaluator
            ),
            "recurrent_semantic_solver": RecurrentSemanticDynamicsV351(),
            "semantic_attractor_stabilizer": RecurrentAttractorStabilizerV351(),
            "discourse_structure_builder": DiscourseStructureBuilderV351(
                self.session_memory, authority_map=self.services.discourse_authority_map
            ),
            "epistemic_coordinator": EpistemicCoordinatorV351(
                self.session_memory, policy=self.services.epistemic_admission_policy
            ),
            "query_engine": Phase16QueryEngineV351(
                self.session_memory, causal_query_contracts=self.services.causal_query_contracts,
            ),
            "learning_engine": Phase14LearningEngineV351(),
            "causal_simulator": Phase15CausalSimulatorV351(
                parameter_lookup=self.services.causal_parameter_lookup,
                manifold_transform_resolver=self.services.state_manifold_transform_resolver,
                set_member_type_resolver=self.services.state_set_member_type_resolver,
                simulation_budget=self.services.causal_simulation_budget,
                aggregation_selection_evaluators=self.services.causal_aggregation_selection_evaluators,
            ),
            "commit_coordinator": CompositeStage13CommitterV351(self.session_memory),
            "impact_engine": Phase16ImpactRuntimeV351(
                self.services.causal_impact_rules,
                capability_leaf_resolver=self.services.causal_capability_leaf_resolver,
                manifold_transform_resolver=self.services.state_manifold_transform_resolver,
                set_member_type_resolver=self.services.state_set_member_type_resolver,
            ),
            "goal_engine": CompositeGoalArbitratorV351(policy=self.services.causal_goal_policy),
            "operation_engine": CausalPlanningOperationEngineV351(
                utility_evaluator=self.services.causal_utility_evaluator,
                utility_policy_pin=self.services.causal_utility_policy_pin,
                parameter_lookup=self.services.causal_parameter_lookup,
                manifold_transform_resolver=self.services.state_manifold_transform_resolver,
                set_member_type_resolver=self.services.state_set_member_type_resolver,
                simulation_budget=self.services.causal_simulation_budget,
                aggregation_selection_evaluators=self.services.causal_aggregation_selection_evaluators,
            ),
            "operation_outcome_assimilator": CanonicalOperationOutcomeAssimilatorV351(),
            "response_csir_builder": Phase16ResponseCSIRBuilderV351(
                authority_map=response_authority_map, session_memory=self.session_memory,
            ),
            "realization_engine": EnglishCSIRRealizerV351(
                package=english_realization_package,
                response_authority_map=response_authority_map,
                session_memory=self.session_memory,
            ),
            "emission_engine": InProcessTextEmissionEngineV351(
                channel_contract_pin=self.services.text_channel_contract_pin,
                disclosure_authorization_grants=self.services.disclosure_authorization_grants,
            ),
            "output_discourse_engine": OutputDiscourseCommitterV351(self.session_memory),
            "consolidation_engine": CanonicalCycleFinalizerV351(),
        }

    def _schema_applicability_index(self, registry, capability: StageCapability):
        key = (capability.authority_generation, capability.authority_fingerprint)
        with self._authority_index_lock:
            cached = self._schema_applicability_indexes.get(key)
        if cached is not None:
            return cached

        # Build outside the lock: authority is immutable and duplicate concurrent builds
        # are harmless, while holding a runtime-global lock across schema computation is
        # forbidden by ISSUES_TO_AVOID. Only the tiny ownership swap is synchronized.
        built = SchemaApplicabilityIndex.build(
            registry,
            authority_generation=capability.authority_generation,
            authority_fingerprint=capability.authority_fingerprint,
        )
        with self._authority_index_lock:
            cached = self._schema_applicability_indexes.get(key)
            if cached is None:
                # Retain only the active generation so vocabulary growth cannot create an
                # unbounded process-global cache.
                self._schema_applicability_indexes = {key: built}
                cached = built
            return cached

    def _read(self, capability: StageCapability):
        cm = self.store.snapshot()
        snapshot = cm.__enter__()
        generation = snapshot.read_generation
        if (
            generation.authority_generation != capability.authority_generation
            or generation.authority_fingerprint != capability.authority_fingerprint
        ):
            cm.__exit__(None, None, None)
            from .runtime_generations import ReadGenerationChanged
            raise ReadGenerationChanged("semantic authority changed before stage read")
        # Every stage reads the exact cognitive generation encoded in its capability.
        # The orchestrator advances that generation only after an allowed stage-owned
        # commit; concurrent post-commit drift therefore fails closed into replay.
        if generation.cognitive_fingerprint != capability.read_generation.cognitive_fingerprint:
            cm.__exit__(None, None, None)
            from .runtime_generations import ReadGenerationChanged
            raise ReadGenerationChanged("cognitive read generation changed before stage read")
        return cm, snapshot

    @staticmethod
    def _performed(**artifacts):
        return StageOutcome(StageExecutionStatus.PERFORMED, artifacts)

    def _gap(self, stage: CoreStage, capability_name: str, *, extra=()):
        ref = f"frontier:runtime-capability:{int(stage)}:{capability_name}"
        return StageOutcome(
            StageExecutionStatus.DEFERRED,
            artifacts={"_runtime_frontiers": ()},
            frontier_refs=tuple((ref, *extra)),
        )

    def _stage_stores(self, cycle, capability):
        read_store = CycleArtifactStoreView(self.store, cycle.workspace)
        effect_store = AuthorizedEffectStore(
            base_store=self.store, read_store=read_store, boundary=self.effect_boundary,
            capability=capability, permission_ref=cycle.permission_ref, context_ref=cycle.context_ref,
        )
        return read_store, effect_store

    @staticmethod
    def _attach_effect_receipts(outcome: StageOutcome, receipts):
        receipts = tuple(receipts)
        if not receipts:
            return outcome
        artifacts = dict(outcome.artifacts)
        existing = tuple(artifacts.get("_effect_authorization_receipts", ()) or ())
        deduped = {}
        for receipt in (*existing, *receipts):
            ref = str(getattr(receipt, "receipt_ref", "") or "")
            if not ref:
                raise ValueError("effect authorization receipt requires stable receipt_ref")
            prior = deduped.get(ref)
            if prior is not None and prior != receipt:
                raise ValueError("effect authorization receipt identity collision")
            deduped[ref] = receipt
        artifacts["_effect_authorization_receipts"] = tuple(deduped[key] for key in sorted(deduped))
        return StageOutcome(
            outcome.status, artifacts=artifacts, frontier_refs=outcome.frontier_refs,
            errors=outcome.errors, reentry_request=outcome.reentry_request, terminal=outcome.terminal,
        )

    def _resolved_service(self, service_name: str):
        injected = getattr(self.services, service_name, None)
        return injected if injected is not None else self._canonical_services.get(service_name)

    def _service(self, cycle, capability, service_name: str, method: str = "run"):
        service = self._resolved_service(service_name)
        if service is None:
            return self._gap(capability.stage, service_name)
        fn = getattr(service, method, None)
        if not callable(fn):
            raise TypeError(f"v3.5.1 service {service_name} lacks callable {method}()")
        read_store, effect_store = self._stage_stores(cycle, capability)
        result = fn(
            cycle=cycle,
            capability=capability,
            store=read_store,
            effect_store=effect_store,
            semantic_capabilities=self.semantic_capabilities,
        )
        if isinstance(result, StageOutcome):
            return self._attach_effect_receipts(result, effect_store.receipts)
        if not isinstance(result, Mapping):
            raise TypeError(f"{service_name}.{method} must return Mapping or StageOutcome")
        outcome = StageOutcome(StageExecutionStatus.PERFORMED, dict(result))
        return self._attach_effect_receipts(outcome, effect_store.receipts)

    def stage_00_orient_and_pin_semantic_brain(self, cycle: CognitiveCycleState, capability: StageCapability):
        if self.services.clock is None or not callable(getattr(self.services.clock, "now_iso", None)):
            return self._gap(capability.stage, "clock")
        envelope = cycle.input_payload if isinstance(cycle.input_payload, RuntimeInput) else RuntimeInput(str(cycle.input_payload))
        speaker = envelope.speaker_ref or "referent:anonymous-session-participant"
        evidence = envelope.participant_evidence_refs or (cycle.cycle_ref,)
        frame = ParticipantFrame(
            frame_ref=artifact_ref("participant-frame", cycle.context_ref, speaker, self.services.system_ref, cycle.audience_refs),
            system_ref=self.services.system_ref,
            input_speaker_ref=speaker,
            input_addressee_refs=(self.services.system_ref,),
            response_audience_refs=cycle.audience_refs or (speaker,),
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            identity_evidence_refs=tuple(evidence),
        )
        authority = self.store.current_authority_snapshot(
            runtime_attestation_ref=str(self.services.runtime_attestation_ref or "")
        )
        semantic_authority = self.services.semantic_authority_snapshot or AuthoritySnapshotV351(
            generation=authority.generation,
            authority_fingerprint=authority.authority_fingerprint,
        )
        # Phase 13 requires an explicit immutable Θ inventory.  The reviewed canonical
        # baseline is pinned only when the supplied semantic snapshot has no dynamics
        # artifacts at all; a partial/custom inventory is never silently completed.
        if not semantic_authority.dynamics_parameters:
            semantic_authority = replace(
                semantic_authority,
                dynamics_parameters=tuple(self._reviewed_phase13_dynamics),
            )
        # Deterministically project only already-promoted Phase-15/16 operational authority
        # from this exact store AuthorityGeneration into the cycle-local split snapshot.
        semantic_authority = project_state_causal_authority(self.store, semantic_authority)
        if (semantic_authority.generation, semantic_authority.authority_fingerprint) != (
            authority.generation, authority.authority_fingerprint
        ):
            raise ValueError("semantic authority snapshot differs from Stage-0 AuthorityGeneration")
        pins = CognitiveCyclePins(
            authority_snapshot=authority,
            read_generation=capability.read_generation,
            kernel_abi_fingerprint=CURRENT_KERNEL_ABI.fingerprint,
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            channel_ref=cycle.channel_ref,
            target_language=cycle.target_language,
            cycle_time=str(self.services.clock.now_iso()),
            semantic_authority_snapshot_fingerprint=semantic_authority.snapshot_fingerprint,
            dynamics_parameter_pins=tuple(
                item.parameter_pin
                for item in sorted(semantic_authority.dynamics_parameters, key=lambda item: item.parameter_family)
            ),
            runtime_attestation_ref=str(self.services.runtime_attestation_ref or ""),
        )
        context_stack = (cycle.context_ref,)
        return self._performed(
            authority_snapshot=authority,
            semantic_authority_snapshot_v351=semantic_authority,
            read_generation=capability.read_generation,
            kernel_semantic_abi=CURRENT_KERNEL_ABI,
            participant_frame=frame,
            context_stack=context_stack,
            runtime_budgets=RuntimeBudgetSet(),
            _cycle_pins=pins,
        )

    def _inactive_pre_phase17_stage_01_observe_multimodal_evidence(self, cycle, capability):
        envelope = cycle.input_payload if isinstance(cycle.input_payload, RuntimeInput) else RuntimeInput(str(cycle.input_payload))
        items = []
        participant_frame = cycle.artifacts.get("participant_frame")
        for evidence_ref in tuple(envelope.participant_evidence_refs):
            participant_ref = getattr(participant_frame, "input_speaker_ref", envelope.speaker_ref)
            source_ref = artifact_ref("source-transport-participant", cycle.context_ref, participant_ref, evidence_ref)
            items.append(EvidenceEnvelope(
                evidence_ref=evidence_ref,
                source_ref=source_ref,
                kind="transport_participant_identity",
                payload={"participant_ref": participant_ref, "transport_grounded": True},
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                confidence=1.0,
                lineage_refs=(source_ref,),
            ))
        if envelope.content:
            source_ref = artifact_ref("source-cycle-input", cycle.cycle_ref, envelope.content)
            items.append(EvidenceEnvelope(
                evidence_ref=artifact_ref("evidence-cycle-input", cycle.cycle_ref, source_ref),
                source_ref=source_ref,
                kind="text",
                payload=envelope.content,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                evidence_refs=tuple(envelope.participant_evidence_refs),
                lineage_refs=(source_ref,),
            ))
        for track in envelope.multimodal_tracks:
            items.append(EvidenceEnvelope(
                evidence_ref=artifact_ref("evidence-multimodal", cycle.cycle_ref, getattr(track, "track_ref", repr(track))),
                source_ref=str(getattr(track, "track_ref", cycle.cycle_ref)),
                kind=str(getattr(track, "kind", "sensor")), payload=track,
                context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            ))
        if not items:
            return StageOutcome(StageExecutionStatus.DEFERRED, frontier_refs=("frontier:observation:no-evidence",))
        return self._performed(evidence_envelopes=tuple(items))

    def _inactive_pre_phase17_stage_02_encode_form_and_sensor_evidence(self, cycle, capability):
        envelopes = tuple(cycle.artifacts["evidence_envelopes"])
        text_items = [item for item in envelopes if item.kind == "text"]
        form_lattice = None
        unresolved = []
        language_evidence = ()
        if text_items:
            cm, snapshot = self._read(capability)
            try:
                registry = self.store.repositories.language.registry(snapshot=snapshot)
                analyzer = FormLatticeAnalyzer(registry, syntax_adapters=self.services.syntax_adapters)
                content = "\n".join(str(item.payload) for item in text_items)
                hints = tuple(getattr(cycle.input_payload, "language_hints", ()) or ())
                form_lattice = analyzer.analyze(content, source_ref=text_items[0].source_ref, language_hints=hints)
                unresolved.extend(f"form-span:{x.start}:{x.end}" for x in form_lattice.unresolved_spans)
                language_evidence = tuple(getattr(form_lattice, "language_evidence", ()) or ())
            finally:
                cm.__exit__(None, None, None)
        sensor = tuple(item for item in envelopes if item.kind != "text")
        lattice = EvidenceLattice(
            lattice_ref=artifact_ref("evidence-lattice", cycle.cycle_ref, tuple(x.evidence_ref for x in envelopes)),
            form_lattice=form_lattice,
            structured_observations=sensor,
            evidence_refs=tuple(x.evidence_ref for x in envelopes),
            unresolved_refs=tuple(unresolved),
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "evidence_lattice": lattice,
                "language_decision_evidence": language_evidence,
                "sensor_feature_candidates": sensor,
            },
            frontier_refs=tuple(f"frontier:{x}" for x in unresolved),
        )

    def _inactive_pre_phase17_stage_03_activate_and_ground_referents(self, cycle, capability):
        lattice: EvidenceLattice = cycle.artifacts["evidence_lattice"]
        if lattice.form_lattice is None:
            return self._gap(capability.stage, "multimodal_grounder")
        cm, snapshot = self._read(capability)
        try:
            analyzer = FormLatticeAnalyzer(self.store.repositories.language.registry(snapshot=snapshot), syntax_adapters=self.services.syntax_adapters)
            grounder = JointGrounder(self.store, analyzer)
            envelope = cycle.input_payload
            frame = cycle.artifacts["participant_frame"]
            participant_anchors = participant_frame_anchors(frame, store=self.store, snapshot=snapshot)
            session_snapshot = self.session_memory.snapshot(cycle.context_ref, cycle.permission_ref)
            cycle_participant_anchors = participant_frame_session_anchors(
                frame, turn_index=session_snapshot.revision + 1
            )
            anchors = {
                item.anchor_ref: item
                for item in (
                    *tuple(getattr(envelope, "discourse_anchors", ()) or ()),
                    *self.session_memory.grounding_anchors(cycle.context_ref, cycle.permission_ref),
                    *participant_anchors,
                    *cycle_participant_anchors,
                )
            }
            prepared = grounder.prepare_lattice(
                lattice.form_lattice,
                context_ref=cycle.context_ref,
                discourse_anchors=tuple(anchors[key] for key in sorted(anchors)),
                multimodal_tracks=tuple(getattr(envelope, "multimodal_tracks", ()) or ()),
                system_outputs=(
                    *tuple(getattr(envelope, "system_output_anchors", ()) or ()),
                    *self.session_memory.system_output_anchors(cycle.context_ref, cycle.permission_ref),
                ),
                constraints=tuple(getattr(envelope, "grounding_constraints", ()) or ()),
                snapshot=snapshot,
            )
            result = grounder.solve_prepared(prepared)
        finally:
            cm.__exit__(None, None, None)
        artifact = GroundingCandidateSet(
            candidate_set_ref=artifact_ref("grounding-candidates", cycle.cycle_ref, tuple(x.candidate_ref for x in prepared.candidates)),
            preparation=prepared,
            result=result,
            evidence_refs=tuple(result.evidence_refs),
            unresolved_refs=tuple(result.frontier_refs),
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={"grounding_candidates": artifact, "identity_coreference_trace": tuple(result.evidence_refs)},
            frontier_refs=tuple(result.frontier_refs),
        )

    def stage_01_observe_multimodal_evidence(self, cycle, capability):
        return stage_01_observe_multimodal_evidence_v351(self, cycle, capability)

    def stage_02_encode_form_and_sensor_evidence(self, cycle, capability):
        return stage_02_encode_form_and_sensor_evidence_v351(self, cycle, capability)

    def stage_03_activate_and_ground_referents(self, cycle, capability):
        return stage_03_activate_and_ground_referents_v351(self, cycle, capability)

    def stage_04_project_entitled_state_spaces(self, cycle, capability):
        grounding: GroundingCandidateSet = cycle.artifacts["grounding_candidates"]
        cm, snapshot = self._read(capability)
        projections = {}
        state_spaces = {}
        frontiers = []
        try:
            projector = ReferentKnowledgeProjector(self.store)
            by_target = {}
            for candidate in grounding.preparation.candidates:
                by_target.setdefault(candidate.target_ref, []).append(candidate)
            for target_ref, candidates in sorted(by_target.items()):
                # Project durable referents exactly; non-durable candidates stay cycle-local.
                from .storage.model import RecordKind
                durable = self.store.get_record(RecordKind.REFERENT, target_ref, snapshot=snapshot)
                if durable is not None:
                    projection = projector.project(target_ref, context_ref=cycle.context_ref, at_time=None, snapshot=snapshot)
                else:
                    envelopes = {(tuple(sorted(x.type_refs)), x.storage_kind.value, tuple(sorted(x.context_refs))) for x in candidates}
                    if len(envelopes) != 1:
                        frontiers.append(f"frontier:referent-knowledge:{target_ref}:candidate-envelope-ambiguous")
                        continue
                    projection = projector.project_candidate(candidates[0], context_ref=cycle.context_ref, at_time=None, snapshot=snapshot)
                projections[target_ref] = projection
                state_spaces[target_ref] = tuple(getattr(projection, "state_spaces", ()) or ())
            schema_registry = self.store.repositories.schemas.registry(snapshot=snapshot)
            applicability_index = self._schema_applicability_index(schema_registry, capability)
            closure = ReferentKnowledgeClosureCompiler(self.store).compile(
                projections, snapshot=snapshot, applicability_index=applicability_index
            )
        finally:
            cm.__exit__(None, None, None)
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "referent_projections": projections,
                "state_space_projections": state_spaces,
                "semantic_closure_candidates": tuple(closure),
            },
            frontier_refs=tuple(frontiers),
        )

    def stage_05_compile_candidates_to_csir(self, cycle, capability):
        if cycle.artifacts["kernel_semantic_abi"].fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("Stage 5 kernel ABI differs from Stage-0 pinned semantic brain")
        proposed = []
        proposal_frontiers = []
        service = self._resolved_service("csir_compiler")
        if service is not None:
            result = service.compile(
                evidence_lattice=cycle.artifacts["evidence_lattice"],
                grounding_candidates=cycle.artifacts["grounding_candidates"],
                referent_projections=cycle.artifacts["referent_projections"],
                state_space_projections=cycle.artifacts["state_space_projections"],
                closure_candidates=cycle.artifacts["semantic_closure_candidates"],
                authority_snapshot=cycle.artifacts["authority_snapshot"],
                semantic_authority_snapshot_v351=cycle.artifacts["semantic_authority_snapshot_v351"],
                read_generation=cycle.artifacts["read_generation"],
                kernel_semantic_abi=CURRENT_KERNEL_ABI,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
            )
            # Phase-7 Stage-5 service boundary accepts proposed fragments with typed
            # ClosureProof payloads. Pre-final candidates carrying only proof refs cannot
            # re-authorize themselves at the kernel barrier.
            if isinstance(result, Mapping):
                proposed.extend(tuple(result.get("candidate_fragments", ()) or ()))
                proposal_frontiers.extend(tuple(result.get("composition_frontiers", ()) or ()))
            else:
                try:
                    proposed.extend(tuple(result))
                except TypeError as exc:
                    raise TypeError("csir_compiler must return exact CSIR candidate fragments") from exc
            if any(isinstance(item, (CSIRCandidate, CSIRCandidateSet)) for item in proposed):
                raise TypeError(
                    "Stage-5 proposal service must return CSIRCandidateFragment with typed closure proofs"
                )
        else:
            # Phase-6 kernel may consume explicit CSIR fragments produced by already
            # migrated authorities. Opaque v3.5 closure objects are rejected and become
            # frontiers; they never enter the solver.
            proposed.extend(tuple(cycle.artifacts["semantic_closure_candidates"]))

        compiled = self.exact_csir_compiler.compile_fragments(
            proposed,
            authority_generation=capability.authority_generation,
            authority_fingerprint=capability.authority_fingerprint,
            semantic_authority_snapshot=cycle.artifacts["semantic_authority_snapshot_v351"],
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            # Stage 5 compiles meaning from language/multimodal evidence. Projection
            # authority is a boundary invariant, never a proposal-service-controlled flag.
            require_projection_authority=True,
        )
        # Exact observation-model projections may contribute already-typed CSIR fragments.
        # They join the same Stage-5 compiler barrier; they never bypass closure/authority validation.
        for analysis in tuple(cycle.artifacts.get("_structured_observation_analyses", ()) or ()):
            fragments = tuple(getattr(analysis, "semantic_fragments", ()) or ())
            if fragments and not tuple(getattr(analysis, "semantic_projection_pins", ()) or ()):
                raise ValueError("semantic observation fragments require exact ObservationModel projection pins")
            proposed.extend(fragments)
        if proposed and tuple(cycle.artifacts.get("_structured_observation_analyses", ()) or ()):
            compiled = self.exact_csir_compiler.compile_fragments(
                proposed, authority_generation=capability.authority_generation,
                authority_fingerprint=capability.authority_fingerprint,
                semantic_authority_snapshot=cycle.artifacts["semantic_authority_snapshot_v351"],
                context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                require_projection_authority=True,
            )
        combined_frontiers = tuple((*proposal_frontiers, *compiled.frontiers))
        combined_frontier_refs = tuple(sorted(set((
            *(str(getattr(item, "frontier_ref", "")) for item in proposal_frontiers if getattr(item, "frontier_ref", "")),
            *compiled.unresolved_refs,
        ))))
        if not compiled.candidates:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                artifacts={"_runtime_frontiers": combined_frontiers},
                frontier_refs=combined_frontier_refs,
            )
        candidate_set = CSIRCandidateSet(
            candidate_set_ref=artifact_ref(
                "csir-candidate-set", cycle.cycle_ref, tuple(x.semantic_fingerprint for x in compiled.candidates)
            ),
            candidates=compiled.candidates,
            authority_generation=capability.authority_generation,
            authority_fingerprint=capability.authority_fingerprint,
            kernel_abi_fingerprint=CURRENT_KERNEL_ABI.fingerprint,
            closure_proof_refs=compiled.closure_proof_refs,
            hard_constraint_trace_refs=compiled.hard_constraint_trace_refs,
            unresolved_refs=compiled.unresolved_refs,
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "csir_candidates": candidate_set,
                "closure_proofs": candidate_set.closure_proof_refs,
                "hard_constraint_trace": candidate_set.hard_constraint_trace_refs,
                "_runtime_frontiers": combined_frontiers,
            },
            frontier_refs=combined_frontier_refs,
        )

    def stage_06_run_recurrent_meaning_dynamics(self, cycle, capability):
        candidates = cycle.artifacts["csir_candidates"]
        if not isinstance(candidates, CSIRCandidateSet):
            raise TypeError("Stage 6 requires exact CSIRCandidateSet")
        if (candidates.authority_generation, candidates.authority_fingerprint) != (capability.authority_generation, capability.authority_fingerprint):
            raise ValueError("Stage 6 candidates were compiled under another AuthorityGeneration")
        if candidates.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("Stage 6 candidate kernel ABI mismatch")
        semantic_authority = cycle.artifacts["semantic_authority_snapshot_v351"]
        expected_dynamics = tuple(
            item.parameter_pin.key
            for item in sorted(semantic_authority.dynamics_parameters, key=lambda item: item.parameter_family)
        )
        for candidate in candidates.candidates:
            if candidate.graph.applications:
                if not candidate.execution_authority_ref:
                    raise ValueError("Stage 6 candidate lacks exact execution authority envelope")
                if candidate.semantic_authority_snapshot_fingerprint != semantic_authority.snapshot_fingerprint:
                    raise ValueError("Stage 6 candidate semantic authority snapshot mismatch")
                if tuple(pin.key for pin in candidate.dynamics_parameter_pins) != expected_dynamics:
                    raise ValueError("Stage 6 candidate dynamics parameter pins mismatch")
                rebound_graph, rebound_authority = semantic_authority.bind_execution_authority(
                    candidate.graph,
                    operation="compose",
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                    projection_authority_pins=candidate.projection_authority_pins,
                    causal_mechanism_pins=candidate.causal_mechanism_pins,
                    policy_adapter_pins=candidate.policy_adapter_pins,
                    require_projection_authority=candidate.projection_authority_required,
                )
                if rebound_graph != candidate.graph or rebound_authority.envelope_ref != candidate.execution_authority_ref:
                    raise ValueError("Stage 6 candidate execution authority envelope cannot be replayed exactly")
                if rebound_authority.use_authorization_pins != candidate.use_authorization_pins:
                    raise ValueError("Stage 6 candidate use authorization pins mismatch")
        service = self._resolved_service("recurrent_semantic_solver")
        if service is None:
            return self._gap(capability.stage, "recurrent_semantic_solver")
        graph, trace = service.run(
            csir_candidates=cycle.artifacts["csir_candidates"],
            authority_snapshot=cycle.artifacts["authority_snapshot"],
            semantic_authority_snapshot_v351=cycle.artifacts["semantic_authority_snapshot_v351"],
            dynamics_parameters=cycle.artifacts["semantic_authority_snapshot_v351"].dynamics_parameters,
            read_generation=cycle.artifacts["read_generation"],
            budgets=cycle.artifacts["runtime_budgets"],
            evidence_lattice=cycle.artifacts.get("evidence_lattice"),
            evidence_envelopes=cycle.artifacts.get("evidence_envelopes", ()),
            grounding_candidates=cycle.artifacts.get("grounding_candidates"),
            referent_projections=cycle.artifacts.get("referent_projections"),
            state_space_projections=cycle.artifacts.get("state_space_projections"),
        )
        if not isinstance(graph, ActivationGraph) or not isinstance(trace, ActivationTrace):
            raise TypeError("recurrent_semantic_solver must return ActivationGraph, ActivationTrace")
        if (graph.authority_generation, graph.authority_fingerprint) != (capability.authority_generation, capability.authority_fingerprint):
            raise ValueError("activation graph belongs to another AuthorityGeneration")
        if graph.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("activation graph kernel ABI mismatch")
        semantic_authority = cycle.artifacts["semantic_authority_snapshot_v351"]
        expected_dynamics = tuple(
            item.parameter_pin.key
            for item in sorted(semantic_authority.dynamics_parameters, key=lambda item: item.parameter_family)
        )
        if graph.semantic_authority_snapshot_fingerprint != semantic_authority.snapshot_fingerprint:
            raise ValueError("activation graph semantic authority snapshot mismatch")
        if tuple(pin.key for pin in graph.dynamics_parameter_pins) != expected_dynamics:
            raise ValueError("activation graph dynamics parameter pins mismatch")
        return self._performed(activation_graph=graph, activation_trace=trace)

    def stage_07_stabilize_semantic_attractors(self, cycle, capability):
        service = self._resolved_service("semantic_attractor_stabilizer")
        if service is None:
            return self._gap(capability.stage, "semantic_attractor_stabilizer")
        result = service.stabilize(
            activation_graph=cycle.artifacts["activation_graph"],
            activation_trace=cycle.artifacts["activation_trace"],
            authority_snapshot=cycle.artifacts["authority_snapshot"],
            semantic_authority_snapshot_v351=cycle.artifacts["semantic_authority_snapshot_v351"],
            budgets=cycle.artifacts["runtime_budgets"],
        )
        if not isinstance(result, SemanticAttractorSet):
            raise TypeError("semantic_attractor_stabilizer must return SemanticAttractorSet")
        if (result.authority_generation, result.authority_fingerprint) != (capability.authority_generation, capability.authority_fingerprint):
            raise ValueError("semantic attractors belong to another AuthorityGeneration")
        if result.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("semantic attractor kernel ABI mismatch")
        semantic_authority = cycle.artifacts["semantic_authority_snapshot_v351"]
        expected_dynamics = tuple(
            item.parameter_pin.key
            for item in sorted(semantic_authority.dynamics_parameters, key=lambda item: item.parameter_family)
        )
        if result.semantic_authority_snapshot_fingerprint != semantic_authority.snapshot_fingerprint:
            raise ValueError("semantic attractor semantic authority snapshot mismatch")
        if tuple(pin.key for pin in result.dynamics_parameter_pins) != expected_dynamics:
            raise ValueError("semantic attractor dynamics parameter pins mismatch")
        return self._performed(
            semantic_attractors=result,
            partial_meaning=result.partial_meaning,
            open_variables=result.open_variables,
            convergence_assessment=result.convergence,
        )

    # Stages 8-10 now have canonical Phase-11 CSIR/discourse/epistemic/query services.
    # Later services remain exact replaceable boundaries and never invoke legacy UOL.
    def stage_08_build_discourse_proposition_event_and_query_structures(self, c, cap): return self._service(c, cap, "discourse_structure_builder", "build")
    def stage_09_place_epistemic_context_and_assimilate_world_belief(self, c, cap): return self._service(c, cap, "epistemic_coordinator", "place")
    def stage_10_query_and_explain_from_grounded_world_model(self, c, cap): return self._service(c, cap, "query_engine", "query")
    def stage_11_classify_prediction_error_and_advance_learning(self, c, cap): return self._service(c, cap, "learning_engine", "advance")
    def stage_12_simulate_causal_transitions_and_counterfactuals(self, c, cap): return self._service(c, cap, "causal_simulator", "simulate")

    def stage_13_commit_authorized_knowledge_state_and_learning_artifacts(self, c, cap):
        return self._service(c, cap, "commit_coordinator", "commit")
    def stage_14_propagate_capability_impact_affect_and_significance(self, c, cap): return self._service(c, cap, "impact_engine", "propagate")
    def stage_15_derive_obligations_and_arbitrate_goals(self, c, cap): return self._service(c, cap, "goal_engine", "arbitrate")

    @staticmethod
    def _operation_value(value, name, default=None):
        if isinstance(value, Mapping):
            return value.get(name, default)
        return getattr(value, name, default)

    def stage_16_plan_authorize_execute_and_observe(self, c, cap):
        service = self._resolved_service("operation_engine")
        if service is None:
            return self._gap(cap.stage, "operation_engine")
        prepare = getattr(service, "prepare", None)
        execute = getattr(service, "execute", None)
        if not callable(prepare) or not callable(execute):
            raise TypeError("v3.5.1 operation_engine requires separate prepare() and execute() methods")

        read_store, effect_store = self._stage_stores(c, cap)
        prepared = prepare(
            cycle=c, capability=cap, store=read_store, effect_store=effect_store,
            semantic_capabilities=self.semantic_capabilities,
        )
        if not isinstance(prepared, Mapping):
            raise TypeError("operation_engine.prepare must return a Mapping")
        plans = tuple(prepared.get("plans", ()) or ())
        effect_authorizations = tuple(prepared.get("effect_authorizations", ()) or ())
        operation_journals = tuple(prepared.get("operation_journals", ()) or ())
        attempts = tuple(prepared.get("authorized_operations", ()) or ())

        operation_receipts: list[EffectAuthorizationReceipt] = []
        authorized_refs: set[str] = set()
        for attempt in attempts:
            operation_ref = str(self._operation_value(attempt, "operation_ref", "") or "")
            if not operation_ref or operation_ref in authorized_refs:
                raise ValueError("authorized operation attempts require unique stable operation_ref")
            decision = str(self._operation_value(attempt, "operation_authorization_decision", "") or "")
            if decision != "allow":
                continue
            pins = tuple(self._operation_value(attempt, "authorization_pins", ()) or ())
            if any(not isinstance(pin, PinnedRecord) for pin in pins):
                raise TypeError("operation authorization_pins must be exact PinnedRecord values")
            receipt = self.effect_boundary.authorize(
                EffectAuthorizationRequest(
                    effect_ref=f"operation:{c.cycle_ref}:{operation_ref}",
                    cycle_ref=cap.cycle_ref,
                    pass_ref=cap.pass_ref,
                    capability_nonce=cap.nonce,
                    effect_kind=EffectKind.EXTERNAL_OPERATION,
                    stage=cap.stage,
                    permission_ref=c.permission_ref,
                    authority_generation=cap.authority_generation,
                    authority_fingerprint=cap.authority_fingerprint,
                    target_refs=tuple(self._operation_value(attempt, "target_refs", ()) or ()),
                    authorization_pins=pins,
                    proof_refs=tuple(self._operation_value(attempt, "proof_refs", ()) or ()),
                    metadata={
                        "operation_authorization_decision": decision,
                        "prepared_journal_ref": str(self._operation_value(attempt, "prepared_journal_ref", "") or ""),
                        "idempotency_identity": str(self._operation_value(attempt, "idempotency_identity", "") or ""),
                    },
                )
            )
            operation_receipts.append(receipt)
            if receipt.allowed:
                authorized_refs.add(operation_ref)

        denied = tuple(receipt for receipt in operation_receipts if not receipt.allowed)
        if denied:
            return StageOutcome(
                StageExecutionStatus.BLOCKED,
                artifacts={
                    "plans": plans, "effect_authorizations": effect_authorizations,
                    "operation_journals": operation_journals, "operation_observations": (),
                    "_effect_authorization_receipts": (*effect_store.receipts, *operation_receipts),
                },
                frontier_refs=tuple(sorted({
                    f"frontier:effect-authorization:{reason}"
                    for receipt in denied for reason in receipt.reason_refs
                })),
            )

        executed = execute(
            cycle=c, capability=cap, store=read_store, effect_store=effect_store,
            prepared=dict(prepared), operation_effect_receipts=tuple(operation_receipts),
        )
        if not isinstance(executed, Mapping):
            raise TypeError("operation_engine.execute must return a Mapping")
        observations = tuple(executed.get("operation_observations", ()) or ())
        for observation in observations:
            observed_ref = str(self._operation_value(observation, "operation_ref", "") or "")
            if observed_ref not in authorized_refs:
                raise ValueError("operation observation has no exact pre-effect authorization receipt")
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "plans": plans,
                "effect_authorizations": effect_authorizations,
                "operation_journals": tuple(executed.get("operation_journals", operation_journals) or ()),
                "operation_observations": observations,
                "_effect_authorization_receipts": (*effect_store.receipts, *operation_receipts),
            },
            frontier_refs=tuple(executed.get("frontier_refs", ()) or ()),
        )

    def stage_17_assimilate_operation_outcomes_and_recur(self, c, cap): return self._service(c, cap, "operation_outcome_assimilator", "assimilate")
    def stage_18_construct_response_csir(self, c, cap):
        return self._service(c, cap, "response_csir_builder", "build")

    @staticmethod
    def _candidate_ref(candidate):
        return str(getattr(candidate, "candidate_ref", None) or (candidate.get("candidate_ref") if isinstance(candidate, Mapping) else ""))

    @staticmethod
    def _candidate_surface(candidate):
        return str(getattr(candidate, "surface", None) or (candidate.get("surface") if isinstance(candidate, Mapping) else ""))

    @staticmethod
    def _candidate_language(candidate):
        return str(getattr(candidate, "language_tag", None) or (candidate.get("language_tag") if isinstance(candidate, Mapping) else ""))

    @staticmethod
    def _plan_value(plan, name, default=None):
        if isinstance(plan, Mapping):
            return plan.get(name, default)
        return getattr(plan, name, default)

    def stage_19_realize_target_language_or_modality(self, c, cap):
        service = self._resolved_service("realization_engine")
        if service is None:
            return self._gap(cap.stage, "realization_engine")
        read_store, _effect_store = self._stage_stores(c, cap)
        result = service.realize(
            cycle=c,
            capability=cap,
            store=read_store,
            effect_store=_effect_store,
            semantic_capabilities=self.semantic_capabilities,
        )
        # Stage 19 is a kernel-validated proof boundary.  A service may not bypass it
        # by returning a prebuilt StageOutcome.
        if not isinstance(result, Mapping):
            raise TypeError("realization_engine.realize must return a proof-carrying Mapping")
        plan = result.get("realization_plan")
        candidates = tuple(result.get("surface_candidates", ()) or ())
        proofs = tuple(result.get("realization_proofs", ()) or ())
        if bool(result.get("no_response_required", False)):
            if plan is None:
                raise ValueError("NO_RESPONSE_REQUIRED realization requires explicit plan artifact")
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={
                    "realization_plan": plan,
                    "surface_candidates": (),
                    "realization_proofs": (),
                    "_no_response_required": True,
                    "_effect_authorization_receipts": _effect_store.receipts,
                },
            )
        if plan is None or not candidates or not proofs:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=tuple(result.get("frontier_refs", ()) or ("frontier:realization:incomplete-proof-carrying-result",)),
            )

        refs = [self._candidate_ref(item) for item in candidates]
        if any(not ref for ref in refs) or len(refs) != len(set(refs)):
            raise ValueError("realization candidates require unique stable candidate refs")
        by_candidate: dict[str, ExactRealizationProof] = {}
        for proof in proofs:
            if not isinstance(proof, ExactRealizationProof):
                raise TypeError("Stage 19 realization_proofs must be ExactRealizationProof records")
            if proof.surface_candidate_ref in by_candidate:
                raise ValueError("one surface candidate cannot carry multiple competing realization proofs")
            if (
                proof.authority_generation != cap.authority_generation
                or proof.authority_fingerprint != cap.authority_fingerprint
            ):
                raise ValueError("realization proof was built under another authority generation")
            if proof.permission_ref not in {"public", c.permission_ref}:
                raise ValueError("realization proof widens permission scope")
            if not set(c.audience_refs).issubset(set(proof.audience_refs)):
                raise ValueError("realization proof does not cover the requested audience")
            by_candidate[proof.surface_candidate_ref] = proof

        missing = sorted(set(refs).difference(by_candidate))
        extra = sorted(set(by_candidate).difference(refs))
        if missing or extra:
            raise ValueError(
                f"realization candidate/proof identity mismatch:missing={missing}:extra={extra}"
            )
        for candidate in candidates:
            ref = self._candidate_ref(candidate)
            proof_ref = str(
                getattr(candidate, "proof_ref", None)
                or (candidate.get("proof_ref") if isinstance(candidate, Mapping) else "")
                or ""
            )
            if proof_ref and proof_ref != by_candidate[ref].proof_ref:
                raise ValueError("surface candidate proof_ref does not identify its exact realization proof")
            language = self._candidate_language(candidate)
            if c.target_language and language and language != c.target_language:
                raise ValueError("surface candidate language differs from exact target language")

        selected = str(self._plan_value(plan, "selected_candidate_ref", "") or "")
        if not selected and len(refs) == 1:
            selected = refs[0]
        if selected not in set(refs):
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:realization:selected-candidate-unresolved",),
            )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "realization_plan": plan,
                "surface_candidates": candidates,
                "realization_proofs": proofs,
                "_selected_surface_candidate_ref": selected,
                "_effect_authorization_receipts": _effect_store.receipts,
            },
        )

    @staticmethod
    def _authorization_value(value, name, default=None):
        if isinstance(value, Mapping):
            return value.get(name, default)
        return getattr(value, name, default)

    def stage_20_verify_semantic_equivalence_and_authorize_emission(self, c, cap):
        if bool(c.artifacts.get("_no_response_required", False)):
            decision = c.artifacts.get("response_decision")
            if decision is None or getattr(decision, "family", None) is not ResponseFamily.NO_RESPONSE_REQUIRED:
                raise ValueError("semantic silence marker requires NO_RESPONSE_REQUIRED ResponseDecision")
            silence = EmissionObservationArtifact(
                emission_ref=artifact_ref("observed-non-emission", c.cycle_ref, decision.decision_ref),
                surface_candidate_ref="no-response:" + decision.selected_candidate_ref,
                output_text="",
                evidence_refs=tuple(filter(None, (decision.no_response_reason_ref, *decision.proof_refs))),
                channel_ref=c.channel_ref,
            )
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={
                    "semantic_preservation_assessments": (),
                    "emission_authorization": {"decision": "no_response_required", "reason_ref": decision.no_response_reason_ref},
                    "emission_observation": silence,
                    "_no_effectful_work": True,
                },
            )
        plan = c.artifacts["realization_plan"]
        candidates = tuple(c.artifacts["surface_candidates"])
        proofs = tuple(c.artifacts["realization_proofs"])
        selected_ref = str(
            c.artifacts.get("_selected_surface_candidate_ref")
            or self._plan_value(plan, "selected_candidate_ref", "")
        )
        selected = next((item for item in candidates if self._candidate_ref(item) == selected_ref), None)
        proof = next((item for item in proofs if item.surface_candidate_ref == selected_ref), None)
        if selected is None or proof is None:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:emission:selected-candidate-proof-missing",),
            )
        surface = self._candidate_surface(selected)
        if not surface:
            raise ValueError("selected surface candidate is empty")

        preservation = self.realization_proof_verifier.verify(
            semantic_input=c.artifacts["response_decision"],
            surface=surface,
            proof=proof,
            authority_snapshot=c.artifacts["semantic_authority_snapshot_v351"],
        )
        service = self._resolved_service("emission_engine")
        verification_channel = self._plan_value(plan, "channel_metadata", None)
        if service is not None:
            channel_metadata = getattr(service, "verification_channel_metadata", None)
            if callable(channel_metadata):
                read_view = CycleArtifactStoreView(self.store, c.workspace)
                before_channel_read = self.store.current_read_generation()
                verification_channel = channel_metadata(cycle=c, store=read_view)
                after_channel_read = self.store.current_read_generation()
                if before_channel_read.fingerprint != after_channel_read.fingerprint:
                    raise ValueError("emission channel metadata lookup must be read-only")
        decision = self.roundtrip_policy.decide(
            preservation=preservation,
            novelty=bool(self._plan_value(plan, "novelty", False)),
            risk_refs=tuple(self._plan_value(plan, "risk_refs", ()) or ()),
            audit_required=bool(self._plan_value(plan, "audit_required", False)),
            release_competence=bool(self._plan_value(plan, "release_competence", False)),
            unreviewed_transform=bool(self._plan_value(plan, "unreviewed_transform", False)),
            channel=verification_channel,
        )
        if decision.mode is VerificationMode.BLOCK:
            return StageOutcome(
                StageExecutionStatus.BLOCKED,
                artifacts={"semantic_preservation_assessments": (preservation,)},
                frontier_refs=("frontier:emission:semantic-preservation-proof-failed",),
            )

        roundtrip = None
        independent_proof_refs: tuple[str, ...] = ()
        if decision.mode is VerificationMode.PROOF_PLUS_INDEPENDENT_ROUNDTRIP:
            analyzer = self.services.independent_semantic_analyzer
            if analyzer is None:
                return StageOutcome(
                    StageExecutionStatus.DEFERRED,
                    artifacts={"semantic_preservation_assessments": (preservation,)},
                    frontier_refs=("frontier:emission:independent-semantic-analyzer-required",),
                )
            verify = getattr(analyzer, "verify_equivalence", None)
            if not callable(verify):
                raise TypeError("independent_semantic_analyzer lacks verify_equivalence()")
            roundtrip = verify(
                semantic_input=c.artifacts["response_decision"],
                surface_candidate=selected,
                surface=surface,
                proof=proof,
                cycle=c,
                capability=cap,
                store=CycleArtifactStoreView(self.store, c.workspace),
            )
            if not bool(getattr(roundtrip, "passed", False)):
                return StageOutcome(
                    StageExecutionStatus.BLOCKED,
                    artifacts={"semantic_preservation_assessments": (preservation,)},
                    frontier_refs=("frontier:emission:independent-roundtrip-failed",),
                )
            independent_proof_refs = tuple(getattr(roundtrip, "proof_refs", ()) or ())
            if not independent_proof_refs:
                raise ValueError("independent semantic round-trip pass requires proof lineage")

        # emission service was resolved before preservation policy so exact channel transforms could influence round-trip.
        if service is None:
            return self._gap(cap.stage, "emission_engine")
        authorize = getattr(service, "authorize", None)
        emit = getattr(service, "emit", None)
        if not callable(authorize) or not callable(emit):
            raise TypeError("v3.5.1 emission_engine requires separate authorize() and emit() methods")

        read_store, effect_store = self._stage_stores(c, cap)
        before_authorize = self.store.current_read_generation()
        authorization = authorize(
            cycle=c,
            capability=cap,
            store=read_store,
            semantic_capabilities=self.semantic_capabilities,
            selected_candidate=selected,
            realization_proof=proof,
            semantic_preservation=preservation,
            verification_policy=decision,
            independent_roundtrip=roundtrip,
        )
        after_authorize = self.store.current_read_generation()
        if before_authorize.fingerprint != after_authorize.fingerprint:
            raise ValueError("emission_engine.authorize() must be read-only")
        if not isinstance(authorization, Mapping):
            raise TypeError("emission_engine.authorize must return a Mapping")
        gate_decision = str(authorization.get("emission_gate_decision", ""))
        if gate_decision != "allow":
            return StageOutcome(
                StageExecutionStatus.BLOCKED,
                artifacts={
                    "semantic_preservation_assessments": (preservation,),
                    "emission_authorization": dict(authorization),
                },
                frontier_refs=tuple(authorization.get("frontier_refs", ()) or ("frontier:emission:gate-denied",)),
            )

        disclosure_grant = authorization.get("disclosure_authorization_grant")
        if not isinstance(disclosure_grant, DisclosureAuthorizationGrantV351):
            return StageOutcome(
                StageExecutionStatus.BLOCKED,
                artifacts={
                    "semantic_preservation_assessments": (preservation,),
                    "emission_authorization": dict(authorization),
                },
                frontier_refs=("frontier:emission:typed-disclosure-authorization-required",),
            )
        try:
            disclosure_grant.validate_exact_authority(c.artifacts["semantic_authority_snapshot_v351"])
            grant_allowed, grant_reasons = disclosure_grant.matches(
                cycle=c, selected_candidate=selected
            )
        except Exception:
            grant_allowed, grant_reasons = False, ("disclosure_grant_invalid",)
        if not grant_allowed:
            return StageOutcome(
                StageExecutionStatus.BLOCKED,
                artifacts={
                    "semantic_preservation_assessments": (preservation,),
                    "emission_authorization": dict(authorization),
                },
                frontier_refs=tuple(
                    "frontier:emission:" + reason for reason in grant_reasons
                ) or ("frontier:emission:disclosure-grant-rejected",),
            )
        auth_pins = tuple(authorization.get("authorization_pins", ()) or ())
        supplied = {(pin.key, pin.record_fingerprint) for pin in auth_pins if isinstance(pin, PinnedRecord)}
        required = {(pin.key, pin.record_fingerprint) for pin in disclosure_grant.substrate_pins}
        if not required.issubset(supplied):
            raise ValueError("emission authorization omitted exact disclosure substrate pins")
        if any(not isinstance(pin, PinnedRecord) for pin in auth_pins):
            raise TypeError("emission authorization_pins must be exact PinnedRecord values")
        proof_refs = tuple(sorted(set((
            proof.proof_ref,
            preservation.assessment_ref,
            *proof.proof_refs,
            *independent_proof_refs,
            *tuple(authorization.get("proof_refs", ()) or ()),
        ))))
        common = dict(
            stage=cap.stage,
            permission_ref=c.permission_ref,
            authority_generation=cap.authority_generation,
            authority_fingerprint=cap.authority_fingerprint,
            audience_refs=tuple(c.audience_refs),
            authorization_pins=auth_pins,
            proof_refs=proof_refs,
        )
        disclosure_receipt = self.effect_boundary.authorize(
            EffectAuthorizationRequest(
                effect_ref=f"disclosure:{c.cycle_ref}:{selected_ref}",
                cycle_ref=cap.cycle_ref,
                pass_ref=cap.pass_ref,
                capability_nonce=cap.nonce,
                effect_kind=EffectKind.PROTECTED_DISCLOSURE,
                target_refs=(selected_ref,),
                metadata={
                    "disclosure_gate_passed": bool(authorization.get("disclosure_gate_passed", False)),
                    "disclosure_authorization_ref": str(authorization.get("disclosure_authorization_ref", "")),
                    "disclosure_authorization_content_hash": str(
                        authorization.get("disclosure_authorization_content_hash", "")
                    ),
                },
                **common,
            )
        )
        emission_receipt = self.effect_boundary.authorize(
            EffectAuthorizationRequest(
                effect_ref=f"emission:{c.cycle_ref}:{selected_ref}",
                cycle_ref=cap.cycle_ref,
                pass_ref=cap.pass_ref,
                capability_nonce=cap.nonce,
                effect_kind=EffectKind.EXTERNAL_EMISSION,
                target_refs=(selected_ref,),
                metadata={
                    "semantic_preservation_passed": preservation.passed,
                    "emission_gate_decision": gate_decision,
                    "channel_contract_ref": str(authorization.get("channel_contract_ref", "")),
                    "idempotency_identity": str(authorization.get("idempotency_identity", "")),
                },
                **common,
            )
        )
        receipts: list[EffectAuthorizationReceipt] = [disclosure_receipt, emission_receipt]
        denied_effects = tuple(receipt for receipt in receipts if not receipt.allowed)
        if denied_effects:
            return StageOutcome(
                StageExecutionStatus.BLOCKED,
                artifacts={
                    "semantic_preservation_assessments": (preservation,),
                    "emission_authorization": dict(authorization),
                    "_effect_authorization_receipts": tuple(receipts),
                },
                frontier_refs=tuple(
                    sorted({
                        f"frontier:effect-authorization:{reason}"
                        for receipt in denied_effects
                        for reason in receipt.reason_refs
                    })
                ),
            )
        # Durable emission/audit journal patches must be applied through effect_store,
        # which issues exact pre-effect patch receipts. The kernel never pre-authorizes
        # anonymous target refs without an exact GraphPatch fingerprint/CAS revision.

        result = emit(
            cycle=c,
            capability=cap,
            store=read_store,
            effect_store=effect_store,
            selected_candidate=selected,
            realization_proof=proof,
            semantic_preservation=preservation,
            authorization=dict(authorization),
            effect_authorization_receipts=tuple(receipts),
        )
        if not isinstance(result, Mapping):
            raise TypeError("emission_engine.emit must return a Mapping")
        receipts.extend(effect_store.receipts)
        observation = result.get("emission_observation")
        if observation is None:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                artifacts={
                    "semantic_preservation_assessments": (preservation,),
                    "emission_authorization": dict(authorization),
                    "_effect_authorization_receipts": tuple(receipts),
                },
                frontier_refs=tuple(result.get("frontier_refs", ()) or ("frontier:emission:outcome-unknown",)),
            )
        emitted_ref = str(
            getattr(observation, "surface_candidate_ref", None)
            or (observation.get("surface_candidate_ref") if isinstance(observation, Mapping) else "")
        )
        if emitted_ref != selected_ref:
            raise ValueError("emission observation does not identify the proof-verified selected candidate")
        artifacts = {
            "semantic_preservation_assessments": (preservation,),
            "emission_authorization": dict(authorization),
            "emission_observation": observation,
            "_effect_authorization_receipts": tuple(receipts),
        }
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts=artifacts,
            frontier_refs=tuple(result.get("frontier_refs", ()) or ()),
        )

    def stage_21_commit_output_discourse_and_common_ground(self, c, cap):
        return self._service(c, cap, "output_discourse_engine", "commit")

    def stage_22_consolidate_invalidate_replay_and_finalize(self, c, cap):
        service = self._resolved_service("consolidation_engine")
        if service is None:
            return self._gap(cap.stage, "consolidation_engine")
        return self._service(c, cap, "consolidation_engine", "finalize")


class Runtime:
    VERSION = VERSION
    def __init__(self, *, store: SemanticStore, orchestrator: CanonicalOrchestrator,
                 services: RuntimeServices, maintenance_scheduler: MaintenanceScheduler | None = None) -> None:
        self.store = store
        self.orchestrator = orchestrator
        self.services = services
        self.maintenance_scheduler = maintenance_scheduler or MaintenanceScheduler()
        self.sessions = _SessionRegistry()

    def run_text(self, text: str, *, context_id: str = "conversation", language_hint: str | None = None,
                 target_language: str | None = None, audience_refs: tuple[str, ...] = (), speaker_ref: str | None = None,
                 permission_ref: str = "conversation", channel_ref: str = "text", emission_idempotency_key: str | None = None,
                 discourse_anchors: tuple[Any, ...] = (), multimodal_tracks: tuple[Any, ...] = (),
                 system_output_anchors: tuple[Any, ...] = (), grounding_constraints: tuple[Any, ...] = (),
                 response_requested: bool = True, observations: tuple[Any, ...] = ()) -> RuntimeResult:
        participant_ref, evidence_ref = self.sessions.resolve(
            context_id, permission_ref, speaker_ref, self.store, system_ref=self.services.system_ref
        )
        audiences = tuple(audience_refs) or (participant_ref,)
        envelope = RuntimeInput(
            content=text, language_hints=() if language_hint is None else (language_hint,),
            emission_idempotency_key=emission_idempotency_key,
            discourse_anchors=discourse_anchors, multimodal_tracks=multimodal_tracks,
            system_output_anchors=system_output_anchors, grounding_constraints=grounding_constraints,
            speaker_ref=participant_ref, participant_evidence_refs=(evidence_ref,),
            response_requested=bool(response_requested), observations=tuple(observations),
        )
        cycle = self.orchestrator.run(
            envelope, context_ref=context_id, permission_ref=permission_ref,
            audience_refs=audiences, target_language=target_language, channel_ref=channel_ref,
        )
        # Event-driven means work runs because an event exists, not because a request
        # happened.  Targeted post-cycle events are drained only after the semantic
        # pass lease is released, so promotion cannot mutate authority mid-pass.
        for event in tuple(cycle.artifacts.get("_maintenance_events", ())):
            self.maintenance_scheduler.notify(
                event.trigger, refs=event.ref_set, context_ref=event.context_ref,
                permission_ref=event.permission_ref,
            )
        maintenance_results = ()
        if cycle.artifacts.get("_maintenance_events"):
            maintenance_results = self.maintenance_scheduler.drain()
        emission = cycle.artifacts.get("emission_observation")
        output = None
        if emission is not None:
            output = getattr(emission, "surface", None) or getattr(emission, "output_text", None)
        if output == "":
            output = None
        return RuntimeResult(
            cycle_ref=cycle.cycle_ref, context_ref=cycle.context_ref, output_text=output,
            target_language=cycle.target_language, stage_trace=tuple(cycle.trace),
            frontier_refs=tuple(sorted(set(cycle.frontiers))), errors=tuple(cycle.errors),
            artifacts={
                **dict(cycle.artifacts),
                "_post_cycle_maintenance_results": tuple(maintenance_results),
                "_runtime_restart_required": any(
                    bool(getattr(getattr(item, "details", {}).get("result"), "restart_required", False))
                    for item in maintenance_results
                ),
            },
        )

    def run_maintenance(self, trigger=MaintenanceTrigger.MANUAL):
        resolved = trigger if isinstance(trigger, MaintenanceTrigger) else MaintenanceTrigger(str(trigger))
        return self.maintenance_scheduler.run_event(MaintenanceEvent(resolved))
    def drain_maintenance(self): return self.maintenance_scheduler.drain()
    def close(self): self.store.close()


def _build_scheduler(services: RuntimeServices) -> MaintenanceScheduler:
    scheduler = MaintenanceScheduler()
    if services.learning_maintenance is not None:
        scheduler.register(
            "maintenance:v351-learning",
            triggers={
                MaintenanceTrigger.LEARNING_EVIDENCE_CHANGED,
                MaintenanceTrigger.COMPETENCE_COMPLETED,
                MaintenanceTrigger.REVIEW_DECISION,
                MaintenanceTrigger.EXPLICIT_CONSOLIDATION,
            },
            callback=lambda event: services.learning_maintenance.handle(event),
        )
    if services.runtime_signal_provider is not None:
        scheduler.register(
            "maintenance:v351-runtime-signals",
            triggers={MaintenanceTrigger.STARTUP, MaintenanceTrigger.RELOAD, MaintenanceTrigger.RUNTIME_SIGNAL_CHANGED},
            callback=lambda event: services.runtime_signal_provider.refresh(event),
        )
    return scheduler


def build_runtime(*, database_path: str = ":memory:", boot_database_path: str | Path | None = None,
                  authority_guard, services: RuntimeServices | None = None) -> Runtime:
    if authority_guard is None:
        raise TypeError("canonical v3.5.1 runtime requires attested authority")
    authority_guard.require_service_authority()
    store = SemanticStore(database_path, boot_path=boot_database_path)
    manifest = getattr(authority_guard, "manifest", None)
    if services is None:
        services = load_signed_runtime_services(store, manifest, RuntimeServices)
    signed_system_ref = getattr(manifest, "output_speaker_ref", None) if manifest is not None else None
    if signed_system_ref:
        services.system_ref = str(signed_system_ref)
    epoch = getattr(authority_guard, "runtime_epoch", None)
    attestation = getattr(authority_guard, "attestation", None)
    if epoch is not None:
        services.runtime_epoch_ref = epoch.epoch_ref
        services.runtime_authority_generation = epoch.generation
    if attestation is not None:
        services.runtime_attestation_ref = attestation.attestation_ref
    coordinator = V351RuntimeCoordinator(store, services)
    orchestrator = CanonicalOrchestrator(
        build_stage_adapters(coordinator), snapshot_provider=StoreSnapshotProvider(store), authority_guard=authority_guard
    )
    scheduler = _build_scheduler(services)
    runtime = Runtime(store=store, orchestrator=orchestrator, services=services, maintenance_scheduler=scheduler)
    scheduler.run_event(MaintenanceEvent(MaintenanceTrigger.STARTUP))
    return runtime


__all__ = ["Runtime", "RuntimeServices", "StoreSnapshotProvider", "V351RuntimeCoordinator", "build_runtime"]
