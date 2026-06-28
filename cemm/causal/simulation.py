from __future__ import annotations
from dataclasses import dataclass, field
from .inference import CausalInference
from ..types.signal import Signal, SignalKind, SourceType
from ..store.store import Store
from ..types.context_kernel import ContextKernel
import time, uuid


@dataclass
class SimulationResult:
    signal_id: str
    model_ids: list[str] = field(default_factory=list)
    input_claim_ids: list[str] = field(default_factory=list)
    predicted_claims: list[dict] = field(default_factory=list)
    confidence: float = 0.5
    cost_ms: float = 0.0


class SimulationEngine:
    def __init__(self, store: Store) -> None:
        self._inference = CausalInference(store)
        self._store = store

    def simulate(
        self,
        action_or_event: str,
        kernel: ContextKernel,
    ) -> SimulationResult:
        start = time.time()
        predictions = self._inference.predict(
            action_or_event,
            kernel.world.active_claim_ids,
            kernel,
        )
        signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.SIMULATION_RESULT,
            source_id="simulation_engine",
            source_type=SourceType.SIMULATOR,
            content=f"Simulation result for '{action_or_event}': {len(predictions)} predictions",
            observed_at=time.time(),
            context_id=kernel.id,
            salience=0.5,
            trust=0.6,
            permission=kernel.permission,
        )
        self._store.signals.put(signal)
        model_ids = list({p["model_id"] for p in predictions if "model_id" in p})
        return SimulationResult(
            signal_id=signal.id,
            model_ids=model_ids,
            input_claim_ids=kernel.world.active_claim_ids,
            predicted_claims=predictions,
            confidence=0.5 if not predictions else sum(p["confidence"] for p in predictions) / len(predictions),
            cost_ms=(time.time() - start) * 1000.0,
        )
