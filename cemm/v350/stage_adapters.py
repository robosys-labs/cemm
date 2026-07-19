"""Concrete capability adapters for the canonical CEMM v3.5 core loop.

Adapters validate capability ownership and call one explicit coordinator handler.
They contain no domain semantics or phrase routing. Every canonical stage has a
real, separately inspectable class; there is no generated/dummy/no-op adapter path.
"""
from __future__ import annotations

from typing import ClassVar

from .orchestration import CoreStage, CycleState, StageCapability, StageOutcome


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
            raise TypeError(f"coordinator lacks concrete handler {self.HANDLER}")

    @property
    def stage(self) -> CoreStage: return self.STAGE
    @property
    def adapter_ref(self) -> str: return self.ADAPTER_REF
    @property
    def adapter_revision(self) -> int: return self.ADAPTER_REVISION

    def execute(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        if capability.cycle_ref != cycle.cycle_ref:
            raise StageAdapterExecutionError("stage capability belongs to another cycle")
        if capability.stage != self.STAGE:
            raise StageAdapterExecutionError(f"stage capability mismatch: {capability.stage.name} != {self.STAGE.name}")
        if capability.predecessor_stage != cycle.current_stage:
            raise StageAdapterExecutionError("stage capability predecessor mismatch")
        outcome = getattr(self._coordinator, self.HANDLER)(cycle, capability)
        if not isinstance(outcome, StageOutcome):
            raise StageAdapterExecutionError(f"{self.HANDLER} returned {type(outcome).__name__}, expected StageOutcome")
        if not outcome.artifacts and not outcome.frontier_refs and not outcome.errors:
            raise StageAdapterExecutionError(f"{self.HANDLER} produced an unobservable empty stage outcome")
        return outcome


class OrientAndPinAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.ORIENT_AND_PIN; ADAPTER_REF="v350.stage.00.orient_and_pin"; HANDLER="stage_00_orient_and_pin"
class ObserveAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.OBSERVE; ADAPTER_REF="v350.stage.01.observe"; HANDLER="stage_01_observe"
class AnalyzeAndFuseFormAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.ANALYZE_AND_FUSE_FORM; ADAPTER_REF="v350.stage.02.analyze_and_fuse_form"; HANDLER="stage_02_analyze_and_fuse_form"
class GenerateCandidatesAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.GENERATE_REFERENT_AND_SCHEMA_CANDIDATES; ADAPTER_REF="v350.stage.03.generate_candidates"; HANDLER="stage_03_generate_candidates"
class ProjectKnowledgeAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS; ADAPTER_REF="v350.stage.04.project_knowledge"; HANDLER="stage_04_project_knowledge"
class BuildFactorGraphAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.BUILD_UOL_FACTOR_GRAPH; ADAPTER_REF="v350.stage.05.build_factor_graph"; HANDLER="stage_05_build_factor_graph"
class SolveMeaningAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.SOLVE_MEANING_HYPOTHESES; ADAPTER_REF="v350.stage.06.solve_meaning"; HANDLER="stage_06_solve_meaning"
class SelectMeaningAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.SELECT_MEANING_BUNDLE; ADAPTER_REF="v350.stage.07.select_meaning"; HANDLER="stage_07_select_meaning"
class ClassifyDiscourseAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS; ADAPTER_REF="v350.stage.08.classify_discourse"; HANDLER="stage_08_classify_discourse"
class EpistemicAssessmentAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT; ADAPTER_REF="v350.stage.09.epistemic_assessment"; HANDLER="stage_09_epistemically_assess"
class RetrieveAndBindAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.RETRIEVE_AND_ANSWER_BIND; ADAPTER_REF="v350.stage.10.retrieve_and_bind"; HANDLER="stage_10_retrieve_and_bind"
class LearningFrontiersAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.BUILD_OR_ADVANCE_LEARNING_FRONTIERS; ADAPTER_REF="v350.stage.11.learning_frontiers"; HANDLER="stage_11_learning_frontiers"
class PreviewTransitionsAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.INFER_AND_PREVIEW_TRANSITIONS; ADAPTER_REF="v350.stage.12.preview_transitions"; HANDLER="stage_12_preview_transitions"
class CommitKnowledgeStateAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE; ADAPTER_REF="v350.stage.13.commit_knowledge_state"; HANDLER="stage_13_commit_knowledge_state"
class AssessSignificanceAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.ASSESS_IMPACT_AND_IMPORTANCE; ADAPTER_REF="v350.stage.14.assess_significance"; HANDLER="stage_14_assess_significance"
class ArbitrateGoalsAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS; ADAPTER_REF="v350.stage.15.arbitrate_goals"; HANDLER="stage_15_arbitrate_goals"
class ExecuteOperationsAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE; ADAPTER_REF="v350.stage.16.execute_operations"; HANDLER="stage_16_plan_execute_operations"
class ReconcileOperationsAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS; ADAPTER_REF="v350.stage.17.reconcile_operations"; HANDLER="stage_17_reconcile_operations"
class BuildResponseUOLAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.BUILD_RESPONSE_UOL; ADAPTER_REF="v350.stage.18.build_response_uol"; HANDLER="stage_18_build_response_uol"
class RealizeTargetLanguageAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.REALIZE_TARGET_LANGUAGE; ADAPTER_REF="v350.stage.19.realize"; HANDLER="stage_19_realize_target_language"
class AuthorizeEmissionAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.VERIFY_AND_AUTHORIZE_EMISSION; ADAPTER_REF="v350.stage.20.authorize_emission"; HANDLER="stage_20_verify_authorize_emission"
class CommitOutputDiscourseAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND; ADAPTER_REF="v350.stage.21.commit_output_discourse"; HANDLER="stage_21_commit_output_discourse"
class FinalizeAdapter(_ConcreteStageAdapter):
    STAGE=CoreStage.INVALIDATE_RECOMPUTE_AND_FINALIZE; ADAPTER_REF="v350.stage.22.finalize"; HANDLER="stage_22_finalize"


__all__ = [name for name in globals() if name.endswith("Adapter") or name == "StageAdapterExecutionError"]
