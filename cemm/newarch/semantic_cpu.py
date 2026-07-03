"""Compatibility import path for the canonical seed semantic CPU.

The active runtime implementation lives under ``cemm.kernel``.  The ``newarch``
tree remains a staging/reference area for architecture notes and seed modules,
so this file intentionally delegates instead of carrying a divergent copy.
"""

from __future__ import annotations

from ..kernel.semantic_cpu import SemanticCPU, SemanticCycleResult

__all__ = ["SemanticCPU", "SemanticCycleResult"]
