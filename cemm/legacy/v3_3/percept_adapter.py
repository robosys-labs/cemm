"""Legacy v3.3 percept adapter — explicit boundary to legacy perception.

This is the SOLE entry point through which legacy v3.3 perception
components feed the canonical v3.4 cycle. It wraps:

- MeaningPerceptor (legacy perception)
- PerceptToSurfaceEvidence (legacy → v3.4 bridge)

The adapter may supply surface candidates only. It CANNOT supply:
- final predications
- goals
- contracts
- writes
- response content

Per completion-plan.md Stage 1:
"Initially the adapter may supply surface candidates, but it cannot
supply final predications, goals, contracts, writes, or response
content."

Once a native v3.4 language adapter exists, this boundary will be
retired (Stage 9 — legacy isolation and retirement).
"""
from __future__ import annotations

from typing import Any

from ...language.interfaces import SurfaceEvidence


class LegacyV33PerceptAdapter:
    """Explicit legacy boundary for v3.3 perception.

    Wraps MeaningPerceptor + PerceptToSurfaceEvidence to produce
    v3.4 SurfaceEvidence. This is the only permitted path from
    legacy perception into the canonical cycle.
    """

    def __init__(
        self,
        perceptor: Any | None = None,
        percept_bridge: Any | None = None,
    ) -> None:
        self._perceptor = perceptor
        self._percept_bridge = percept_bridge

    def perceive(
        self,
        signal_ids: tuple[str, ...] = (),
        raw_text: str = "",
        signal: Any | None = None,
        kernel: Any | None = None,
    ) -> tuple[SurfaceEvidence, ...]:
        """Produce SurfaceEvidence from legacy perception.

        Returns a tuple of SurfaceEvidence — one per signal.
        The adapter supplies surface candidates only.
        """
        if self._perceptor is None or self._percept_bridge is None:
            return ()

        results: list[SurfaceEvidence] = []

        if signal is not None and kernel is not None:
            percept = self._perceptor.perceive(signal, kernel)
            evidence = self._percept_bridge.convert(percept)
            results.append(evidence)
        elif raw_text:
            # Minimal path: create a dummy signal for the perceptor
            # This path is used when only raw text is available
            try:
                from ...types.normalized_signal import NormalizedSignal
                sig = NormalizedSignal(
                    text=raw_text,
                    context_id="default",
                    turn_index=1,
                )
                from ..context_kernel_builder import ContextKernelBuilder
                builder = ContextKernelBuilder()
                kernel_obj = builder.build(context_id="default")
                percept = self._perceptor.perceive(sig, kernel_obj)
                evidence = self._percept_bridge.convert(percept)
                results.append(evidence)
            except Exception:
                pass

        return tuple(results)
