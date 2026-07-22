"""Canonical CEMM v3.5.1 runtime composition root.

This module intentionally imports neither v347 nor the legacy UOL/composition brain.
Stages 5-7 are real CSIR/recurrent/attractor service boundaries.  Until Phase 6+ installs
those exact services, the canonical runtime emits typed capability frontiers and does
not fall back to the quarantined v3.5 pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from pathlib import Path
from typing import Any, Mapping

from .csir.authority import CURRENT_KERNEL_ABI
from .csir.compiler import ExactCSIRCompiler, ExactCompilationResult
from .csir.model import CSIRCandidate, CSIRCandidateFragment, CSIRGraph
from .effects.authorization import (
    EffectAuthorizationBoundary, EffectAuthorizationReceipt, EffectAuthorizationRequest,
)
from .effects.store import AuthorizedEffectStore
from .facets.closure import ReferentKnowledgeClosureCompiler
from .facets.projector import ReferentKnowledgeProjector
from .grounding.coordinator import JointGrounder
from .grounding.participants import participant_frame_anchors
from .language.analyzer import FormLatticeAnalyzer
from .learning.model import PinnedRecord
from .maintenance import MaintenanceEvent, MaintenanceScheduler, MaintenanceTrigger
from .orchestration import (
    CanonicalOrchestrator, CognitiveCycleState, CoreStage, StageCapability,
    StageExecutionStatus, StageOutcome,
)
from .realization.policy import SelectiveRoundTripPolicy, VerificationMode
from .realization.proof import RealizationProof, RealizationProofVerifier
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
    syntax_adapters: Any | None = None
    clock: Any | None = None
    observation_analyzers: Mapping[str, Any] = field(default_factory=dict)
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
        self.effect_boundary = EffectAuthorizationBoundary(store)
        self.realization_proof_verifier = RealizationProofVerifier(store, self.semantic_capabilities)
        self.roundtrip_policy = SelectiveRoundTripPolicy()

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

    def _service(self, cycle, capability, service_name: str, method: str = "run"):
        service = getattr(self.services, service_name, None)
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
        pins = CognitiveCyclePins(
            authority_snapshot=authority,
            read_generation=capability.read_generation,
            kernel_abi_fingerprint=CURRENT_KERNEL_ABI.fingerprint,
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            channel_ref=cycle.channel_ref,
            target_language=cycle.target_language,
            cycle_time=str(self.services.clock.now_iso()),
            runtime_attestation_ref=str(self.services.runtime_attestation_ref or ""),
        )
        context_stack = (cycle.context_ref,)
        return self._performed(
            authority_snapshot=authority,
            read_generation=capability.read_generation,
            kernel_semantic_abi=CURRENT_KERNEL_ABI,
            participant_frame=frame,
            context_stack=context_stack,
            runtime_budgets=RuntimeBudgetSet(),
            _cycle_pins=pins,
        )

    def stage_01_observe_multimodal_evidence(self, cycle, capability):
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

    def stage_02_encode_form_and_sensor_evidence(self, cycle, capability):
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

    def stage_03_activate_and_ground_referents(self, cycle, capability):
        lattice: EvidenceLattice = cycle.artifacts["evidence_lattice"]
        if lattice.form_lattice is None:
            return self._gap(capability.stage, "multimodal_grounder")
        cm, snapshot = self._read(capability)
        try:
            analyzer = FormLatticeAnalyzer(self.store.repositories.language.registry(snapshot=snapshot), syntax_adapters=self.services.syntax_adapters)
            grounder = JointGrounder(self.store, analyzer)
            envelope = cycle.input_payload
            participant_anchors = participant_frame_anchors(cycle.artifacts["participant_frame"], store=self.store, snapshot=snapshot)
            anchors = {x.anchor_ref: x for x in (*tuple(getattr(envelope, "discourse_anchors", ()) or ()), *participant_anchors)}
            prepared = grounder.prepare_lattice(
                lattice.form_lattice,
                context_ref=cycle.context_ref,
                discourse_anchors=tuple(anchors[key] for key in sorted(anchors)),
                multimodal_tracks=tuple(getattr(envelope, "multimodal_tracks", ()) or ()),
                system_outputs=tuple(getattr(envelope, "system_output_anchors", ()) or ()),
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
            closure = ReferentKnowledgeClosureCompiler(self.store).compile(projections, snapshot=snapshot)
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
        service = self.services.csir_compiler
        if service is not None:
            result = service.compile(
                evidence_lattice=cycle.artifacts["evidence_lattice"],
                grounding_candidates=cycle.artifacts["grounding_candidates"],
                referent_projections=cycle.artifacts["referent_projections"],
                state_space_projections=cycle.artifacts["state_space_projections"],
                closure_candidates=cycle.artifacts["semantic_closure_candidates"],
                authority_snapshot=cycle.artifacts["authority_snapshot"],
                read_generation=cycle.artifacts["read_generation"],
                kernel_semantic_abi=CURRENT_KERNEL_ABI,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
            )
            if isinstance(result, CSIRCandidateSet):
                proposed.extend(
                    CSIRCandidateFragment(
                        fragment_ref=item.candidate_ref, graph=item.graph,
                        evidence_refs=item.evidence_refs,
                        closure_proof_refs=item.closure_proof_refs,
                        hard_constraint_trace_refs=item.hard_constraint_trace_refs,
                        prior_score=item.prior_score,
                    )
                    for item in result.candidates
                )
            elif isinstance(result, ExactCompilationResult):
                proposed.extend(
                    CSIRCandidateFragment(
                        fragment_ref=item.candidate_ref, graph=item.graph,
                        evidence_refs=item.evidence_refs, closure_proof_refs=item.closure_proof_refs,
                        hard_constraint_trace_refs=item.hard_constraint_trace_refs, prior_score=item.prior_score,
                    ) for item in result.candidates
                )
            elif isinstance(result, Mapping):
                proposed.extend(tuple(result.get("candidate_fragments", ()) or ()))
            else:
                try:
                    proposed.extend(tuple(result))
                except TypeError as exc:
                    raise TypeError("csir_compiler must return exact CSIR fragments/candidates") from exc
        else:
            # Phase-6 kernel may consume explicit CSIR fragments produced by already
            # migrated authorities. Opaque v3.5 closure objects are rejected and become
            # frontiers; they never enter the solver.
            proposed.extend(tuple(cycle.artifacts["semantic_closure_candidates"]))

        compiled = self.exact_csir_compiler.compile_fragments(
            proposed,
            authority_generation=capability.authority_generation,
            authority_fingerprint=capability.authority_fingerprint,
        )
        if not compiled.candidates:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                artifacts={"_runtime_frontiers": compiled.frontiers},
                frontier_refs=tuple(compiled.unresolved_refs),
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
                "_runtime_frontiers": compiled.frontiers,
            },
            frontier_refs=tuple(compiled.unresolved_refs),
        )

    def stage_06_run_recurrent_meaning_dynamics(self, cycle, capability):
        candidates = cycle.artifacts["csir_candidates"]
        if not isinstance(candidates, CSIRCandidateSet):
            raise TypeError("Stage 6 requires exact CSIRCandidateSet")
        if (candidates.authority_generation, candidates.authority_fingerprint) != (capability.authority_generation, capability.authority_fingerprint):
            raise ValueError("Stage 6 candidates were compiled under another AuthorityGeneration")
        if candidates.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("Stage 6 candidate kernel ABI mismatch")
        service = self.services.recurrent_semantic_solver
        if service is None:
            return self._gap(capability.stage, "recurrent_semantic_solver")
        graph, trace = service.run(
            csir_candidates=cycle.artifacts["csir_candidates"],
            authority_snapshot=cycle.artifacts["authority_snapshot"],
            read_generation=cycle.artifacts["read_generation"],
            budgets=cycle.artifacts["runtime_budgets"],
        )
        if not isinstance(graph, ActivationGraph) or not isinstance(trace, ActivationTrace):
            raise TypeError("recurrent_semantic_solver must return ActivationGraph, ActivationTrace")
        if (graph.authority_generation, graph.authority_fingerprint) != (capability.authority_generation, capability.authority_fingerprint):
            raise ValueError("activation graph belongs to another AuthorityGeneration")
        if graph.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("activation graph kernel ABI mismatch")
        return self._performed(activation_graph=graph, activation_trace=trace)

    def stage_07_stabilize_semantic_attractors(self, cycle, capability):
        service = self.services.semantic_attractor_stabilizer
        if service is None:
            return self._gap(capability.stage, "semantic_attractor_stabilizer")
        result = service.stabilize(
            activation_graph=cycle.artifacts["activation_graph"],
            activation_trace=cycle.artifacts["activation_trace"],
            authority_snapshot=cycle.artifacts["authority_snapshot"],
            budgets=cycle.artifacts["runtime_budgets"],
        )
        if not isinstance(result, SemanticAttractorSet):
            raise TypeError("semantic_attractor_stabilizer must return SemanticAttractorSet")
        if (result.authority_generation, result.authority_fingerprint) != (capability.authority_generation, capability.authority_fingerprint):
            raise ValueError("semantic attractors belong to another AuthorityGeneration")
        if result.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("semantic attractor kernel ABI mismatch")
        return self._performed(
            semantic_attractors=result,
            partial_meaning=result.partial_meaning,
            open_variables=result.open_variables,
            convergence_assessment=result.convergence,
        )

    # Stages 8-22 are exact service boundaries.  Their semantic implementations land
    # in later roadmap phases; missing services defer honestly instead of invoking UOL.
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
        service = self.services.operation_engine
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
        service = self.services.realization_engine
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
        if plan is None or not candidates or not proofs:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:realization:incomplete-proof-carrying-result",),
            )

        refs = [self._candidate_ref(item) for item in candidates]
        if any(not ref for ref in refs) or len(refs) != len(set(refs)):
            raise ValueError("realization candidates require unique stable candidate refs")
        by_candidate: dict[str, RealizationProof] = {}
        for proof in proofs:
            if not isinstance(proof, RealizationProof):
                raise TypeError("Stage 19 realization_proofs must be RealizationProof records")
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
        )
        decision = self.roundtrip_policy.decide(
            preservation=preservation,
            novelty=bool(self._plan_value(plan, "novelty", False)),
            risk_refs=tuple(self._plan_value(plan, "risk_refs", ()) or ()),
            audit_required=bool(self._plan_value(plan, "audit_required", False)),
            release_competence=bool(self._plan_value(plan, "release_competence", False)),
            unreviewed_transform=bool(self._plan_value(plan, "unreviewed_transform", False)),
            channel=self._plan_value(plan, "channel_metadata", None),
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

        service = self.services.emission_engine
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

        auth_pins = tuple(authorization.get("authorization_pins", ()) or ())
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
                metadata={"disclosure_gate_passed": bool(authorization.get("disclosure_gate_passed", False))},
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
        service = self.services.consolidation_engine
        if service is not None:
            return self._service(c, cap, "consolidation_engine", "finalize")
        from .cycle_control import CompletionEvaluator
        status = CompletionEvaluator().evaluate(c).value
        return self._performed(
            cycle_completion_status=status,
            invalidation_set=(), replay_requirements=(), consolidation_results=(),
            final_cycle_summary={
                "cycle_ref": c.cycle_ref,
                "frontier_refs": tuple(sorted(set(c.frontiers))),
                "errors": tuple(c.errors),
                "authority_generation": cap.authority_generation,
            },
        )


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
                 response_requested: bool = True) -> RuntimeResult:
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
            response_requested=bool(response_requested),
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
        if cycle.artifacts.get("_maintenance_events"):
            self.maintenance_scheduler.drain()
        emission = cycle.artifacts.get("emission_observation")
        output = None
        if emission is not None:
            output = getattr(emission, "surface", None) or getattr(emission, "output_text", None)
        return RuntimeResult(
            cycle_ref=cycle.cycle_ref, context_ref=cycle.context_ref, output_text=output,
            target_language=cycle.target_language, stage_trace=tuple(cycle.trace),
            frontier_refs=tuple(sorted(set(cycle.frontiers))), errors=tuple(cycle.errors),
            artifacts=dict(cycle.artifacts),
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
