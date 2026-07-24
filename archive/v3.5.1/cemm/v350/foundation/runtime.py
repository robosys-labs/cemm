"""Resolution helpers for truthful Phase-6 runtime capability contracts.

A foundation action may name an already implemented runtime component as evidence
for current capability.  Resolution proves only that the named component is
importable from the installed v3.5 package; it does not grant execution authority
or instantiate the component.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any


class RuntimeComponentResolutionError(ImportError):
    """Raised when a declared runtime component cannot be imported exactly."""


def resolve_runtime_component(reference: str) -> Any:
    """Resolve ``package.module.Attribute`` without guessing alternate targets."""
    module_name, separator, attribute_path = str(reference).rpartition(".")
    if not separator or not module_name or not attribute_path:
        raise RuntimeComponentResolutionError(
            f"runtime component must be a dotted module attribute: {reference!r}"
        )
    try:
        value: Any = import_module(module_name)
    except Exception as exc:  # pragma: no cover - exact exception depends on importer
        raise RuntimeComponentResolutionError(
            f"cannot import runtime component module {module_name!r}: {exc}"
        ) from exc
    for attribute in attribute_path.split("."):
        if not hasattr(value, attribute):
            raise RuntimeComponentResolutionError(
                f"runtime component attribute {attribute!r} is missing from {reference!r}"
            )
        value = getattr(value, attribute)
    return value
