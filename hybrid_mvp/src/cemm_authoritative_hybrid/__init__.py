"""CEMM Authoritative Hybrid MVP lazy public API."""

from importlib import import_module


_EXPORTS = {
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