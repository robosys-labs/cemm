"""Generic signed v3.5.1 runtime-service loader.

Unlike the v3.5 service module, this loader imports no semantic implementation itself.
The signed manifest names exact service classes; this module only validates slot
ownership, rejects legacy namespaces and performs a small deterministic constructor
protocol.
"""
from __future__ import annotations

import importlib
import inspect
from typing import Any, Mapping

from .workspace_store import ReadOnlySemanticStoreView


FORBIDDEN_SERVICE_MODULE_FRAGMENTS = (
    "cemm.v347",
    "cemm.migration",
    "cemm.v350.migration",
    "cemm.v350.runtime_services",
    "cemm.v350.runtime_hardening",
    "cemm.v350.activation_services",
    "cemm.v350.uol",
)

SCALAR_SERVICE_SLOTS = frozenset({
    "clock",
    "csir_compiler",
    "recurrent_semantic_solver",
    "semantic_attractor_stabilizer",
    "discourse_structure_builder",
    "epistemic_coordinator",
    "query_engine",
    "learning_engine",
    "causal_simulator",
    "commit_coordinator",
    "impact_engine",
    "goal_engine",
    "operation_engine",
    "operation_outcome_assimilator",
    "response_csir_builder",
    "realization_engine",
    "emission_engine",
    "independent_semantic_analyzer",
    "output_discourse_engine",
    "consolidation_engine",
    "runtime_signal_provider",
    "learning_maintenance",
})

MAPPING_SERVICE_SLOTS = {
    "observation_analyzer": "observation_analyzers",
    "channel_adapter": "channel_adapters",
    "emission_gate_evaluator": "emission_gate_evaluators",
}


class RuntimeServiceCompositionError(RuntimeError):
    pass


def _resolve_class(class_path: str):
    module_name, sep, symbol = class_path.partition(":")
    if not sep or not module_name or not symbol:
        raise RuntimeServiceCompositionError(f"invalid runtime service class path:{class_path}")
    if any(
        module_name == fragment or module_name.startswith(fragment + ".")
        for fragment in FORBIDDEN_SERVICE_MODULE_FRAGMENTS
    ):
        raise RuntimeServiceCompositionError(
            f"legacy/migration service cannot enter canonical v3.5.1 runtime:{class_path}"
        )
    module = importlib.import_module(module_name)
    cls = getattr(module, symbol, None)
    if cls is None or not callable(cls):
        raise RuntimeServiceCompositionError(f"runtime service class is not callable:{class_path}")
    return cls


def _construct(cls, *, store, authority_manifest, binding: Mapping[str, Any]):
    """Deterministic constructor protocol; no arbitrary kwargs from unsigned callers."""
    signature = inspect.signature(cls)
    kwargs = {}
    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        if name == "store":
            kwargs[name] = store
        elif name == "authority_manifest":
            kwargs[name] = authority_manifest
        elif name == "config":
            kwargs[name] = dict(binding.get("config", {}) or {})
        elif parameter.default is inspect.Parameter.empty and parameter.kind not in {
            inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD,
        }:
            raise RuntimeServiceCompositionError(
                f"unsupported required constructor parameter {name} for {cls.__module__}:{cls.__name__}"
            )
    return cls(**kwargs)


def load_signed_runtime_services(store, authority_manifest, runtime_services_type):
    services = runtime_services_type()
    if authority_manifest is None:
        return services
    seen_scalars = set()
    mappings: dict[str, dict[str, Any]] = {
        attr: {} for attr in MAPPING_SERVICE_SLOTS.values()
    }
    for raw in tuple(getattr(authority_manifest, "runtime_service_bindings", ()) or ()):
        binding = dict(raw)
        kind = str(binding.get("service_kind", ""))
        class_path = str(binding.get("class_path", ""))
        implementation_ref = str(binding.get("implementation_ref", ""))
        if not kind or not class_path or not implementation_ref:
            raise RuntimeServiceCompositionError("signed runtime service binding is incomplete")
        if str(binding.get("runtime_abi", "")) != "v351":
            raise RuntimeServiceCompositionError(
                f"runtime service binding lacks v351 ABI declaration:{kind}:{class_path}"
            )
        cls = _resolve_class(class_path)
        if getattr(cls, "RUNTIME_ABI", None) != "v351":
            raise RuntimeServiceCompositionError(
                f"runtime service implementation lacks RUNTIME_ABI=v351:{class_path}"
            )
        declared_kind = getattr(cls, "SERVICE_KIND", None)
        if declared_kind != kind:
            raise RuntimeServiceCompositionError(
                f"runtime service kind mismatch:{class_path}:{declared_kind!r}!={kind!r}"
            )
        instance = _construct(
            cls, store=ReadOnlySemanticStoreView(store),
            authority_manifest=authority_manifest, binding=binding
        )
        if kind in SCALAR_SERVICE_SLOTS:
            if kind in seen_scalars:
                raise RuntimeServiceCompositionError(f"duplicate scalar runtime service slot:{kind}")
            seen_scalars.add(kind)
            setattr(services, kind, instance)
        elif kind in MAPPING_SERVICE_SLOTS:
            mappings[MAPPING_SERVICE_SLOTS[kind]][implementation_ref] = instance
        else:
            raise RuntimeServiceCompositionError(
                f"unsupported/legacy runtime service kind for v3.5.1:{kind}"
            )
    for attr, values in mappings.items():
        setattr(services, attr, dict(sorted(values.items())))
    return services


__all__ = [
    "FORBIDDEN_SERVICE_MODULE_FRAGMENTS", "RuntimeServiceCompositionError",
    "load_signed_runtime_services",
]
