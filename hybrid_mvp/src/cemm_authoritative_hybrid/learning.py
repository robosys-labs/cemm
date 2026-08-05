"""Canonical Learning Plan ABI 2 and dialogue-obligation owner."""
from .r3_learning import *
from .r3_learning import __all__ as _R3_ALL

_INTERNAL_REF_PREFIXES = (
    "op:", "role:", "dim:", "state:", "state_value:", "value:",
    "entity:", "concept:", "relation:", "event:", "participant:",
    "cap:", "rel:", "label:", "adapter:", "policy:", "permission:",
)

def _is_internal_ref_spelling(surface: str) -> bool:
    if type(surface) is not str:
        raise TypeError("surface must be exact str")
    return any(surface.startswith(prefix) for prefix in _INTERNAL_REF_PREFIXES)

__all__ = [*_R3_ALL, "_is_internal_ref_spelling"]
