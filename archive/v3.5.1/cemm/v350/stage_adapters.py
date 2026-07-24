"""Explicit concrete v3.5.1 Stage-0..22 adapters.

Every adapter is separately inspectable and has one fixed stage/ref/handler identity.
There is no generated, dummy, no-op, placeholder, or legacy-alias adapter path.
"""
from __future__ import annotations

from typing import ClassVar

from .orchestration import (
    CognitiveCycleState,
    CoreStage,
    StageCapability,
    StageExecutionStatus,
    StageOutcome,
)


class StageAdapterExecutionError(RuntimeError):
    pass


class _ConcreteStageAdapter:
    STAGE: ClassVar[CoreStage]
    ADAPTER_REF: ClassVar[str]
    HANDLER: ClassVar[str]
    ADAPTER_REVISION: ClassVar[int] = 1

    def __init__(self, coordinator: object) -> None:
        self._coordinator = coordinator
        handler = getattr(coordinator, self.HANDLER, None)
        if handler is None or not callable(handler):
            raise TypeError(f"coordinator lacks concrete handler:{self.HANDLER}")

    @property
    def stage(self) -> CoreStage:
        return self.STAGE

    @property
    def adapter_ref(self) -> str:
        return self.ADAPTER_REF

    @property
    def adapter_revision(self) -> int:
        return self.ADAPTER_REVISION

    def execute(
        self,
        cycle: CognitiveCycleState,
        capability: StageCapability,
    ) -> StageOutcome:
        if capability.cycle_ref != cycle.cycle_ref or capability.pass_ref != cycle.pass_ref:
            raise StageAdapterExecutionError("stage capability belongs to another cycle/pass")
        if capability.stage != self.STAGE:
            raise StageAdapterExecutionError("stage capability stage mismatch")
        if capability.predecessor_stage != cycle.current_stage:
            raise StageAdapterExecutionError("stage capability predecessor mismatch")
        result = getattr(self._coordinator, self.HANDLER)(cycle, capability)
        if not isinstance(result, StageOutcome):
            raise StageAdapterExecutionError(
                f"{self.HANDLER} returned {type(result).__name__}, expected StageOutcome"
            )
        if result.status is StageExecutionStatus.PERFORMED and not result.artifacts:
            raise StageAdapterExecutionError(
                f"{self.HANDLER} claimed performed with no inspectable artifacts"
            )
        return result


class OrientAndPinSemanticBrainAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.ORIENT_AND_PIN_SEMANTIC_BRAIN
    ADAPTER_REF = "v351.stage.00.orient_and_pin_semantic_brain"
    HANDLER = "stage_00_orient_and_pin_semantic_brain"


class ObserveMultimodalEvidenceAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.OBSERVE_MULTIMODAL_EVIDENCE
    ADAPTER_REF = "v351.stage.01.observe_multimodal_evidence"
    HANDLER = "stage_01_observe_multimodal_evidence"


class EncodeFormAndSensorEvidenceAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.ENCODE_FORM_AND_SENSOR_EVIDENCE
    ADAPTER_REF = "v351.stage.02.encode_form_and_sensor_evidence"
    HANDLER = "stage_02_encode_form_and_sensor_evidence"


class ActivateAndGroundReferentsAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.ACTIVATE_AND_GROUND_REFERENTS
    ADAPTER_REF = "v351.stage.03.activate_and_ground_referents"
    HANDLER = "stage_03_activate_and_ground_referents"


class ProjectEntitledStateSpacesAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.PROJECT_ENTITLED_STATE_SPACES
    ADAPTER_REF = "v351.stage.04.project_entitled_state_spaces"
    HANDLER = "stage_04_project_entitled_state_spaces"


class CompileCandidatesToCSIRAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.COMPILE_CANDIDATES_TO_CSIR
    ADAPTER_REF = "v351.stage.05.compile_candidates_to_csir"
    HANDLER = "stage_05_compile_candidates_to_csir"


class RunRecurrentMeaningDynamicsAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.RUN_RECURRENT_MEANING_DYNAMICS
    ADAPTER_REF = "v351.stage.06.run_recurrent_meaning_dynamics"
    HANDLER = "stage_06_run_recurrent_meaning_dynamics"


class StabilizeSemanticAttractorsAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.STABILIZE_SEMANTIC_ATTRACTORS
    ADAPTER_REF = "v351.stage.07.stabilize_semantic_attractors"
    HANDLER = "stage_07_stabilize_semantic_attractors"


class BuildDiscourseStructuresAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.BUILD_DISCOURSE_PROPOSITION_EVENT_AND_QUERY_STRUCTURES
    ADAPTER_REF = "v351.stage.08.build_discourse_proposition_event_and_query_structures"
    HANDLER = "stage_08_build_discourse_proposition_event_and_query_structures"


class PlaceEpistemicContextAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORLD_BELIEF
    ADAPTER_REF = "v351.stage.09.place_epistemic_context_and_assimilate_world_belief"
    HANDLER = "stage_09_place_epistemic_context_and_assimilate_world_belief"


class QueryGroundedWorldModelAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.QUERY_AND_EXPLAIN_FROM_GROUNDED_WORLD_MODEL
    ADAPTER_REF = "v351.stage.10.query_and_explain_from_grounded_world_model"
    HANDLER = "stage_10_query_and_explain_from_grounded_world_model"


class AdvanceLearningAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING
    ADAPTER_REF = "v351.stage.11.classify_prediction_error_and_advance_learning"
    HANDLER = "stage_11_classify_prediction_error_and_advance_learning"


class SimulateCausalTransitionsAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS
    ADAPTER_REF = "v351.stage.12.simulate_causal_transitions_and_counterfactuals"
    HANDLER = "stage_12_simulate_causal_transitions_and_counterfactuals"


class CommitAuthorizedKnowledgeAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS
    ADAPTER_REF = "v351.stage.13.commit_authorized_knowledge_state_and_learning_artifacts"
    HANDLER = "stage_13_commit_authorized_knowledge_state_and_learning_artifacts"


class PropagateImpactAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE
    ADAPTER_REF = "v351.stage.14.propagate_capability_impact_affect_and_significance"
    HANDLER = "stage_14_propagate_capability_impact_affect_and_significance"


class ArbitrateGoalsAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS
    ADAPTER_REF = "v351.stage.15.derive_obligations_and_arbitrate_goals"
    HANDLER = "stage_15_derive_obligations_and_arbitrate_goals"


class PlanAuthorizeExecuteObserveAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE
    ADAPTER_REF = "v351.stage.16.plan_authorize_execute_and_observe"
    HANDLER = "stage_16_plan_authorize_execute_and_observe"


class AssimilateOperationOutcomesAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR
    ADAPTER_REF = "v351.stage.17.assimilate_operation_outcomes_and_recur"
    HANDLER = "stage_17_assimilate_operation_outcomes_and_recur"


class ConstructResponseCSIRAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.CONSTRUCT_RESPONSE_CSIR
    ADAPTER_REF = "v351.stage.18.construct_response_csir"
    HANDLER = "stage_18_construct_response_csir"


class RealizeTargetLanguageAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.REALIZE_TARGET_LANGUAGE_OR_MODALITY
    ADAPTER_REF = "v351.stage.19.realize_target_language_or_modality"
    HANDLER = "stage_19_realize_target_language_or_modality"


class VerifySemanticEquivalenceAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION
    ADAPTER_REF = "v351.stage.20.verify_semantic_equivalence_and_authorize_emission"
    HANDLER = "stage_20_verify_semantic_equivalence_and_authorize_emission"


class CommitOutputDiscourseAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND
    ADAPTER_REF = "v351.stage.21.commit_output_discourse_and_common_ground"
    HANDLER = "stage_21_commit_output_discourse_and_common_ground"


class ConsolidateFinalizeAdapter(_ConcreteStageAdapter):
    STAGE = CoreStage.CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE
    ADAPTER_REF = "v351.stage.22.consolidate_invalidate_replay_and_finalize"
    HANDLER = "stage_22_consolidate_invalidate_replay_and_finalize"


__all__ = [
    "ActivateAndGroundReferentsAdapter",
    "AdvanceLearningAdapter",
    "ArbitrateGoalsAdapter",
    "AssimilateOperationOutcomesAdapter",
    "BuildDiscourseStructuresAdapter",
    "CommitAuthorizedKnowledgeAdapter",
    "CommitOutputDiscourseAdapter",
    "CompileCandidatesToCSIRAdapter",
    "ConsolidateFinalizeAdapter",
    "ConstructResponseCSIRAdapter",
    "EncodeFormAndSensorEvidenceAdapter",
    "ObserveMultimodalEvidenceAdapter",
    "OrientAndPinSemanticBrainAdapter",
    "PlaceEpistemicContextAdapter",
    "PlanAuthorizeExecuteObserveAdapter",
    "ProjectEntitledStateSpacesAdapter",
    "PropagateImpactAdapter",
    "QueryGroundedWorldModelAdapter",
    "RealizeTargetLanguageAdapter",
    "RunRecurrentMeaningDynamicsAdapter",
    "SimulateCausalTransitionsAdapter",
    "StabilizeSemanticAttractorsAdapter",
    "StageAdapterExecutionError",
    "VerifySemanticEquivalenceAdapter",
]
