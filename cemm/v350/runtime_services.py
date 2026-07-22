"""Removed v3.5 runtime-service composition module.

The old implementation reconstructed UOL through MeaningComposer and therefore cannot
participate in the v3.5.1 canonical runtime. Mechanical services live in
``runtime_mechanics``; semantic/runtime services are loaded only through signed v351
bindings in ``service_loader``.
"""
from __future__ import annotations

LEGACY_RUNTIME_SERVICES_REMOVED = True


def __getattr__(name: str):
    raise RuntimeError(
        f"cemm.v350.runtime_services.{name} is legacy v3.5 runtime authority; "
        "use signed v351 service bindings via cemm.v350.service_loader"
    )


__all__ = ["LEGACY_RUNTIME_SERVICES_REMOVED"]
