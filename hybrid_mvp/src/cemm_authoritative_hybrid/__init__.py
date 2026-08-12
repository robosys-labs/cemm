"""CEMM Authoritative Hybrid MVP lazy public API."""

from importlib import import_module


_EXPORTS = {
    "AuthenticEpisode": (".r4_episodes", "AuthenticEpisode"),
    "Decision": (".decision", "Decision"),
    "DecisionAction": (".decision", "DecisionAction"),
    "DecisionStatus": (".decision", "DecisionStatus"),
    "EffectReceipt": (".r3_effects", "EffectReceipt"),
    "EvaluationBundle": (".r3_artifacts", "EvaluationBundle"),
    "ExpectedCycleContract": (".r4_contracts", "ExpectedCycleContract"),
    "ExpectedDerivationContract": (".r4_contracts", "ExpectedDerivationContract"),
    "LearningPlan": (".r3_learning", "LearningPlan"),
    "NoEffectReceipt": (".r3_effects", "NoEffectReceipt"),
    "PartitionAxisManifest": (".r4_partitions", "PartitionAxisManifest"),
    "ResponseMeaning": (".r3_response", "ResponseMeaning"),
    "SituationContext": (".situation", "SituationContext"),
    "ABIRegistry": (".config", "ABIRegistry"),
    "CycleFinalizer": (".cycle", "CycleFinalizer"),
    "CycleResult": (".cycle", "CycleResult"),
    "CycleStatus": (".cycle", "CycleStatus"),
    "GapClassifier": (".gaps", "GapClassifier"),
    "GapReceipt": (".gaps", "GapReceipt"),
    "HybridRuntime": (".runtime", "HybridRuntime"),
    "MissingOwner": (".gaps", "MissingOwner"),
    "Orientation": (".cycle", "Orientation"),
    "PhaseDisposition": (".cycle", "PhaseDisposition"),
    "PhaseReceipt": (".cycle", "PhaseReceipt"),
    "ProposalOwner": (".proposal", "ProposalOwner"),
    "ProposalResult": (".proposal", "ProposalResult"),
    "RevisionPin": (".persistence", "RevisionPin"),
    "RuntimeConfig": (".config", "RuntimeConfig"),
    "RuntimeOrientationOwner": (".runtime", "RuntimeOrientationOwner"),
    "SemanticExpression": (".expressions", "SemanticExpression"),
    "SemanticMode": (".cycle", "SemanticMode"),
    "SemanticPhase": (".cycle", "SemanticPhase"),
    "SemanticStores": (".persistence", "SemanticStores"),
    "SemanticSwitchProgram": (".programs", "SemanticSwitchProgram"),
    "VerificationBatch": (".verifier", "VerificationBatch"),
    "VerifiedMeaning": (".expressions", "VerifiedMeaning"),
    "load_runtime": (".bootstrap", "load_runtime"),
    "open_stores": (".persistence", "open_stores"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
