"""Phase-11 generic event transition engine.

The package keeps eager imports storage-independent so the storage codec can load
transition record codecs without creating a storage↔transition import cycle.
Runtime engines are exposed lazily through ``__getattr__``.
"""
from __future__ import annotations

from .model import (
    AssignmentMutation,
    CapabilityDependencyRecord,
    CapabilityProjection,
    CompiledTransitionContract,
    ConditionOperator,
    StateConditionSpec,
    StateEffectSpec,
    StateTimelineProjection,
    TransitionContractRecord,
    TransitionFrontier,
    TransitionPreview,
    TransitionProofRecord,
    UnknownConditionPolicy,
)

_LAZY = {
    "EventAdmissionAssessment": (".admission", "EventAdmissionAssessment"),
    "EventAdmissionGate": (".admission", "EventAdmissionGate"),
    "CapabilityDependencyEngine": (".capabilities", "CapabilityDependencyEngine"),
    "EffectCommitCoordinator": (".commit", "EffectCommitCoordinator"),
    "EffectCommitError": (".commit", "EffectCommitError"),
    "TransitionContractCompiler": (".compiler", "TransitionContractCompiler"),
    "TransitionContractError": (".compiler", "TransitionContractError"),
    "TransitionCoordinator": (".coordinator", "TransitionCoordinator"),
    "TransitionExecutionPlan": (".coordinator", "TransitionExecutionPlan"),
    "TransitionPreviewEngine": (".preview", "TransitionPreviewEngine"),
    "StateConditionEvaluator": (".state", "StateConditionEvaluator"),
    "StateDeltaValidator": (".state", "StateDeltaValidator"),
    "StateTimelineProjector": (".state", "StateTimelineProjector"),
    "StateTransitionError": (".state", "StateTransitionError"),
}


def __getattr__(name: str):
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(name)
    from importlib import import_module

    module = import_module(target[0], __name__)
    value = getattr(module, target[1])
    globals()[name] = value
    return value


__all__ = [
    "AssignmentMutation", "CapabilityDependencyRecord", "CapabilityProjection",
    "CompiledTransitionContract", "ConditionOperator", "StateConditionSpec",
    "StateEffectSpec", "StateTimelineProjection", "TransitionContractRecord",
    "TransitionFrontier", "TransitionPreview", "TransitionProofRecord",
    "UnknownConditionPolicy", *_LAZY.keys(),
]
