from __future__ import annotations
from ..types.signal import Signal, SignalKind, SourceType, ObservationSemantics
from ..types.context_kernel import ContextKernel, PragmaticState
from ..store.store import Store
from .semantic_clusters import SemanticClusterRegistry


_DEFAULT_REGISTRY = SemanticClusterRegistry()


def interpret_signal(
    signal: Signal,
    kernel: ContextKernel,
    store: Store | None = None,
    registry: SemanticClusterRegistry | None = None,
) -> ObservationSemantics | None:
    if signal.source_type != SourceType.USER or signal.kind != SignalKind.INPUT:
        return None

    reg = registry if registry is not None else _DEFAULT_REGISTRY
    speech_act, cluster_key, confidence = reg.match(signal.content)

    if not cluster_key:
        return ObservationSemantics(
            speech_act="unknown",
            stance="unknown",
            confidence=0.0,
        )

    cluster_def = reg.clusters.get(cluster_key, {})
    affect_baseline = cluster_def.get("affect_baseline", {})
    target = cluster_def.get("target", "")

    target_entity_id = ""
    if target == "assistant" and kernel.self_state is not None:
        target_entity_id = kernel.self_state.id

    active_groups = kernel.conversation.active_repetition_group_ids
    if cluster_key in active_groups:
        prev_count = kernel.conversation.repetition_counts.get(cluster_key, 0)
        repetition_count = prev_count + 1
    else:
        repetition_count = 1

    cause_ids: list[str] = []
    if speech_act in ("insult", "complaint") and repetition_count > 1 and store is not None:
        cause_ids = _trace_causes(store, kernel)

    valence = affect_baseline.get("valence", 0)
    stance = "negative" if valence < 0 else "positive" if valence > 0 else "neutral"

    return ObservationSemantics(
        speech_act=speech_act,
        target_entity_id=target_entity_id,
        semantic_cluster_key=cluster_key,
        stance=stance,
        affect=dict(affect_baseline),
        repetition_group_id=cluster_key,
        repetition_count=repetition_count,
        cause_hypothesis_claim_ids=cause_ids,
        confidence=confidence,
    )


def _trace_causes(store: Store, kernel: ContextKernel) -> list[str]:
    recent_ids = kernel.memory.working_claim_ids[-5:]
    result: list[str] = []
    for cid in recent_ids:
        claim = store.claims.get(cid)
        if claim is not None and claim.domain == "causal" and claim.object_value == "failure":
            result.append(cid)
    return result


def _decay(value: float, elapsed_ms: float, half_life_ms: float) -> float:
    if half_life_ms <= 0 or elapsed_ms <= 0:
        return value
    return value * (0.5 ** (elapsed_ms / half_life_ms))


_HALF_LIVES = {
    "frustration": 900000.0,
    "hostility": 1800000.0,
    "playfulness": 600000.0,
    "repetition_pressure": 300000.0,
}


def update_pragmatic_state(
    current: PragmaticState,
    semantics: ObservationSemantics,
    kernel: ContextKernel,
) -> PragmaticState:
    elapsed_ms = (kernel.time.now - current.last_updated_at) * 1000.0 if current.last_updated_at > 0 else 0.0

    pragmatic = PragmaticState(
        current_stance=current.current_stance,
        target_entity_id=current.target_entity_id,
        frustration=_decay(current.frustration, elapsed_ms, _HALF_LIVES["frustration"]),
        hostility=_decay(current.hostility, elapsed_ms, _HALF_LIVES["hostility"]),
        playfulness=_decay(current.playfulness, elapsed_ms, _HALF_LIVES["playfulness"]),
        repetition_pressure=_decay(current.repetition_pressure, elapsed_ms, _HALF_LIVES["repetition_pressure"]),
        likely_cause_claim_ids=list(current.likely_cause_claim_ids),
        last_updated_signal_id=semantics.repetition_group_id,
        last_updated_at=kernel.time.now,
        decay_half_life_ms=current.decay_half_life_ms,
    )

    affect = semantics.affect
    pragmatic.frustration = max(0.0, min(1.0, pragmatic.frustration + affect.get("frustration", 0.0)))
    pragmatic.hostility = max(0.0, min(1.0, pragmatic.hostility + affect.get("hostility", 0.0)))
    pragmatic.playfulness = max(0.0, min(1.0, pragmatic.playfulness + affect.get("playfulness", 0.0)))

    pressure_inc = 0.15 * semantics.repetition_count
    pragmatic.repetition_pressure = max(0.0, min(1.0, pragmatic.repetition_pressure + pressure_inc))

    f, h, p = pragmatic.frustration, pragmatic.hostility, pragmatic.playfulness
    if h > 0.5:
        pragmatic.current_stance = "hostile"
    elif f > 0.5:
        pragmatic.current_stance = "frustrated"
    elif p > 0.5:
        pragmatic.current_stance = "playful"
    else:
        pragmatic.current_stance = "cooperative"

    if semantics.cause_hypothesis_claim_ids:
        merged = set(pragmatic.likely_cause_claim_ids) | set(semantics.cause_hypothesis_claim_ids)
        pragmatic.likely_cause_claim_ids = sorted(merged)

    return pragmatic
