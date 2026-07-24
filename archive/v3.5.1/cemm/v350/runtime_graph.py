"""Single-source concrete v3.5.1 Stage-0..22 adapter graph."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Sequence

from .orchestration import CoreStage, StageAdapter
from .stage_contracts import StageContract, canonical_stage_contracts


@dataclass(frozen=True, slots=True)
class StageDescriptor:
    contract: StageContract
    adapter_ref: str
    adapter_revision: int
    adapter_class_path: str
    handler_name: str

    @property
    def stage(self): return self.contract.stage



_CLASS_NAMES = (
    "OrientAndPinSemanticBrainAdapter", "ObserveMultimodalEvidenceAdapter",
    "EncodeFormAndSensorEvidenceAdapter", "ActivateAndGroundReferentsAdapter",
    "ProjectEntitledStateSpacesAdapter", "CompileCandidatesToCSIRAdapter",
    "RunRecurrentMeaningDynamicsAdapter", "StabilizeSemanticAttractorsAdapter",
    "BuildDiscourseStructuresAdapter", "PlaceEpistemicContextAdapter",
    "QueryGroundedWorldModelAdapter", "AdvanceLearningAdapter",
    "SimulateCausalTransitionsAdapter", "CommitAuthorizedKnowledgeAdapter",
    "PropagateImpactAdapter", "ArbitrateGoalsAdapter",
    "PlanAuthorizeExecuteObserveAdapter", "AssimilateOperationOutcomesAdapter",
    "ConstructResponseCSIRAdapter", "RealizeTargetLanguageAdapter",
    "VerifySemanticEquivalenceAdapter", "CommitOutputDiscourseAdapter",
    "ConsolidateFinalizeAdapter",
)


def canonical_stage_descriptors() -> tuple[StageDescriptor, ...]:
    contracts = canonical_stage_contracts()
    descriptors = []
    for contract, cls_name in zip(contracts, _CLASS_NAMES, strict=True):
        handler = {
            0:"orient_and_pin_semantic_brain",1:"observe_multimodal_evidence",2:"encode_form_and_sensor_evidence",
            3:"activate_and_ground_referents",4:"project_entitled_state_spaces",5:"compile_candidates_to_csir",
            6:"run_recurrent_meaning_dynamics",7:"stabilize_semantic_attractors",
            8:"build_discourse_proposition_event_and_query_structures",9:"place_epistemic_context_and_assimilate_world_belief",
            10:"query_and_explain_from_grounded_world_model",11:"classify_prediction_error_and_advance_learning",
            12:"simulate_causal_transitions_and_counterfactuals",13:"commit_authorized_knowledge_state_and_learning_artifacts",
            14:"propagate_capability_impact_affect_and_significance",15:"derive_obligations_and_arbitrate_goals",
            16:"plan_authorize_execute_and_observe",17:"assimilate_operation_outcomes_and_recur",18:"construct_response_csir",
            19:"realize_target_language_or_modality",20:"verify_semantic_equivalence_and_authorize_emission",
            21:"commit_output_discourse_and_common_ground",22:"consolidate_invalidate_replay_and_finalize",
        }[int(contract.stage)]
        descriptors.append(StageDescriptor(
            contract=contract,
            adapter_ref=f"v351.stage.{int(contract.stage):02d}.{handler}",
            adapter_revision=1,
            adapter_class_path=f"cemm.v350.stage_adapters:{cls_name}",
            handler_name=f"stage_{int(contract.stage):02d}_{handler}",
        ))
    result = tuple(descriptors)
    validate_stage_descriptors(result)
    return result


def validate_stage_descriptors(descriptors: Sequence[StageDescriptor]) -> None:
    if tuple(x.stage for x in descriptors) != tuple(CoreStage):
        raise ValueError("runtime graph must match exact canonical Stage 0..22")
    if len({x.adapter_ref for x in descriptors}) != len(descriptors):
        raise ValueError("stage adapter refs must be unique")
    if len({x.handler_name for x in descriptors}) != len(descriptors):
        raise ValueError("stage handlers must be unique")
    forbidden = ("uol", "factor_graph", "meaning_bundle", "dummy", "noop", "placeholder")
    for x in descriptors:
        text = f"{x.adapter_ref} {x.adapter_class_path} {x.handler_name}".lower()
        if any(token in text for token in forbidden):
            raise ValueError(f"legacy/non-concrete stage descriptor:{x.stage.name}")


def resolve_adapter_type(descriptor: StageDescriptor):
    module_name, _, symbol = descriptor.adapter_class_path.partition(":")
    return getattr(import_module(module_name), symbol)


def build_stage_adapters(coordinator: object) -> tuple[StageAdapter, ...]:
    result = []
    for descriptor in canonical_stage_descriptors():
        adapter_type = resolve_adapter_type(descriptor)
        if not callable(getattr(coordinator, descriptor.handler_name, None)):
            raise TypeError(f"coordinator missing {descriptor.handler_name}")
        adapter = adapter_type(coordinator)
        if adapter.stage != descriptor.stage or adapter.adapter_ref != descriptor.adapter_ref:
            raise TypeError(f"adapter identity mismatch:{descriptor.stage.name}")
        result.append(adapter)
    return tuple(result)


__all__ = ["StageDescriptor", "build_stage_adapters", "canonical_stage_descriptors", "resolve_adapter_type", "validate_stage_descriptors"]
