"""Canonical Stage-0..22 runtime graph for CEMM v3.5.

This module is the single source of truth for the concrete runtime topology.  It
contains no semantic routing: each descriptor binds one core-loop stage to one
stable adapter class and one distinct coordinator handler.  Release authority
manifests are generated from this graph rather than accepting hand-authored
``STAGE=adapter`` entries.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Iterable, Sequence, Type

from .orchestration import CoreStage, StageAdapter


@dataclass(frozen=True, slots=True)
class StageDescriptor:
    stage: CoreStage
    adapter_ref: str
    adapter_revision: int
    adapter_class_path: str
    handler_name: str
    mutates_semantic_store: bool = False
    permits_external_side_effect: bool = False

    def __post_init__(self) -> None:
        if not self.adapter_ref.strip():
            raise ValueError("stage descriptor requires adapter_ref")
        if self.adapter_revision < 1:
            raise ValueError("stage descriptor revision must be positive")
        module, sep, symbol = self.adapter_class_path.partition(":")
        if not sep or not module or not symbol:
            raise ValueError("adapter_class_path must be module:symbol")
        if not self.handler_name.startswith("stage_"):
            raise ValueError("stage handler must use an explicit stage_* method")


# Store mutation is intentionally constrained to the commit/journal/discourse/final
# boundaries.  Stage 16 may journal before an external operation; Stage 20 may
# journal before emission.  External side effects are permitted only at 16 and 20.
_DESCRIPTORS: tuple[StageDescriptor, ...] = (
    StageDescriptor(CoreStage.ORIENT_AND_PIN, "v350.stage.00.orient_and_pin", 1, "cemm.v350.stage_adapters:OrientAndPinAdapter", "stage_00_orient_and_pin"),
    StageDescriptor(CoreStage.OBSERVE, "v350.stage.01.observe", 1, "cemm.v350.stage_adapters:ObserveAdapter", "stage_01_observe"),
    StageDescriptor(CoreStage.ANALYZE_AND_FUSE_FORM, "v350.stage.02.analyze_and_fuse_form", 1, "cemm.v350.stage_adapters:AnalyzeAndFuseFormAdapter", "stage_02_analyze_and_fuse_form"),
    StageDescriptor(CoreStage.GENERATE_REFERENT_AND_SCHEMA_CANDIDATES, "v350.stage.03.generate_candidates", 1, "cemm.v350.stage_adapters:GenerateCandidatesAdapter", "stage_03_generate_candidates"),
    StageDescriptor(CoreStage.PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS, "v350.stage.04.project_knowledge", 1, "cemm.v350.stage_adapters:ProjectKnowledgeAdapter", "stage_04_project_knowledge"),
    StageDescriptor(CoreStage.BUILD_UOL_FACTOR_GRAPH, "v350.stage.05.build_factor_graph", 1, "cemm.v350.stage_adapters:BuildFactorGraphAdapter", "stage_05_build_factor_graph"),
    StageDescriptor(CoreStage.SOLVE_MEANING_HYPOTHESES, "v350.stage.06.solve_meaning", 1, "cemm.v350.stage_adapters:SolveMeaningAdapter", "stage_06_solve_meaning"),
    StageDescriptor(CoreStage.SELECT_MEANING_BUNDLE, "v350.stage.07.select_meaning", 1, "cemm.v350.stage_adapters:SelectMeaningAdapter", "stage_07_select_meaning"),
    StageDescriptor(CoreStage.CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS, "v350.stage.08.classify_discourse", 1, "cemm.v350.stage_adapters:ClassifyDiscourseAdapter", "stage_08_classify_discourse"),
    StageDescriptor(CoreStage.EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT, "v350.stage.09.epistemic_assessment", 1, "cemm.v350.stage_adapters:EpistemicAssessmentAdapter", "stage_09_epistemically_assess"),
    StageDescriptor(CoreStage.RETRIEVE_AND_ANSWER_BIND, "v350.stage.10.retrieve_and_bind", 1, "cemm.v350.stage_adapters:RetrieveAndBindAdapter", "stage_10_retrieve_and_bind"),
    StageDescriptor(CoreStage.BUILD_OR_ADVANCE_LEARNING_FRONTIERS, "v350.stage.11.learning_frontiers", 1, "cemm.v350.stage_adapters:LearningFrontiersAdapter", "stage_11_learning_frontiers"),
    StageDescriptor(CoreStage.INFER_AND_PREVIEW_TRANSITIONS, "v350.stage.12.preview_transitions", 1, "cemm.v350.stage_adapters:PreviewTransitionsAdapter", "stage_12_preview_transitions"),
    StageDescriptor(CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE, "v350.stage.13.commit_knowledge_state", 1, "cemm.v350.stage_adapters:CommitKnowledgeStateAdapter", "stage_13_commit_knowledge_state", mutates_semantic_store=True),
    StageDescriptor(CoreStage.ASSESS_IMPACT_AND_IMPORTANCE, "v350.stage.14.assess_significance", 1, "cemm.v350.stage_adapters:AssessSignificanceAdapter", "stage_14_assess_significance", mutates_semantic_store=True),
    StageDescriptor(CoreStage.DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS, "v350.stage.15.arbitrate_goals", 1, "cemm.v350.stage_adapters:ArbitrateGoalsAdapter", "stage_15_arbitrate_goals", mutates_semantic_store=True),
    StageDescriptor(CoreStage.PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE, "v350.stage.16.execute_operations", 1, "cemm.v350.stage_adapters:ExecuteOperationsAdapter", "stage_16_plan_execute_operations", mutates_semantic_store=True, permits_external_side_effect=True),
    StageDescriptor(CoreStage.RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS, "v350.stage.17.reconcile_operations", 1, "cemm.v350.stage_adapters:ReconcileOperationsAdapter", "stage_17_reconcile_operations", mutates_semantic_store=True),
    StageDescriptor(CoreStage.BUILD_RESPONSE_UOL, "v350.stage.18.build_response_uol", 1, "cemm.v350.stage_adapters:BuildResponseUOLAdapter", "stage_18_build_response_uol", mutates_semantic_store=True),
    StageDescriptor(CoreStage.REALIZE_TARGET_LANGUAGE, "v350.stage.19.realize", 1, "cemm.v350.stage_adapters:RealizeTargetLanguageAdapter", "stage_19_realize_target_language", mutates_semantic_store=True),
    StageDescriptor(CoreStage.VERIFY_AND_AUTHORIZE_EMISSION, "v350.stage.20.authorize_emission", 1, "cemm.v350.stage_adapters:AuthorizeEmissionAdapter", "stage_20_verify_authorize_emission", mutates_semantic_store=True, permits_external_side_effect=True),
    StageDescriptor(CoreStage.COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND, "v350.stage.21.commit_output_discourse", 1, "cemm.v350.stage_adapters:CommitOutputDiscourseAdapter", "stage_21_commit_output_discourse", mutates_semantic_store=True),
    StageDescriptor(CoreStage.INVALIDATE_RECOMPUTE_AND_FINALIZE, "v350.stage.22.finalize", 1, "cemm.v350.stage_adapters:FinalizeAdapter", "stage_22_finalize"),
)


def canonical_stage_descriptors() -> tuple[StageDescriptor, ...]:
    validate_stage_descriptors(_DESCRIPTORS)
    return _DESCRIPTORS


def validate_stage_descriptors(descriptors: Sequence[StageDescriptor]) -> None:
    stages = tuple(item.stage for item in descriptors)
    if stages != tuple(CoreStage):
        raise ValueError(
            "canonical stage graph must contain exactly CoreStage 0..22 in order"
        )
    if len({item.adapter_ref for item in descriptors}) != len(descriptors):
        raise ValueError("canonical stage adapter refs must be unique")
    if len({item.handler_name for item in descriptors}) != len(descriptors):
        raise ValueError("canonical stage handlers must be unique")
    forbidden_tokens = ("dummy", "noop", "no_op", "passthrough", "placeholder")
    for item in descriptors:
        lowered = f"{item.adapter_ref} {item.adapter_class_path} {item.handler_name}".lower()
        if any(token in lowered for token in forbidden_tokens):
            raise ValueError(f"non-concrete stage descriptor: {item.stage.name}")


def resolve_adapter_type(descriptor: StageDescriptor) -> Type[StageAdapter]:
    module_name, _, symbol = descriptor.adapter_class_path.partition(":")
    module = import_module(module_name)
    adapter_type = getattr(module, symbol, None)
    if adapter_type is None or not isinstance(adapter_type, type):
        raise TypeError(f"stage adapter class is unavailable: {descriptor.adapter_class_path}")
    return adapter_type


def build_stage_adapters(coordinator: object) -> tuple[StageAdapter, ...]:
    result = []
    for descriptor in canonical_stage_descriptors():
        handler = getattr(coordinator, descriptor.handler_name, None)
        if handler is None or not callable(handler):
            raise TypeError(
                f"canonical runtime coordinator lacks {descriptor.handler_name} "
                f"for {descriptor.stage.name}"
            )
        adapter_type = resolve_adapter_type(descriptor)
        adapter = adapter_type(coordinator)
        if adapter.stage != descriptor.stage:
            raise TypeError(f"adapter stage mismatch: {descriptor.stage.name}")
        if (adapter.adapter_ref, int(adapter.adapter_revision)) != (
            descriptor.adapter_ref,
            descriptor.adapter_revision,
        ):
            raise TypeError(f"adapter identity mismatch: {descriptor.stage.name}")
        result.append(adapter)
    return tuple(result)
