from __future__ import annotations
from ..types.signal import Signal, SignalKind, SourceType, ObservationSemantics
from ..types.context_kernel import ContextKernel, UserAffectState, ConversationDynamics
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
        return ObservationSemantics(speech_act="unknown", stance="unknown", confidence=0.0)
    cluster_def = reg.clusters.get(cluster_key, {})
    affect_baseline = cluster_def.get("affect_baseline", {})
    target = cluster_def.get("target", "")
    target_entity_id = ""
    if target == "assistant":
        target_entity_id = kernel.self_view.self_id
    active_groups = kernel.conversation.active_repetition_group_ids
    is_repeat = cluster_key in active_groups
    repetition_count = 1
    if is_repeat:
        last = getattr(kernel.conversation.dynamics, 'repetition_pressure', 0)
        repetition_count = max(1, int(last / 0.15) + 1) if last > 0 else 2
    cause_ids: list[str] = []
    if speech_act in ("insult", "complaint") and repetition_count > 1 and store is not None:
        cause_ids = _trace_causes(store, kernel)
    valence = affect_baseline.get("valence", 0)
    stance = "negative" if valence < 0 else "positive" if valence > 0 else "neutral"
    return ObservationSemantics(
        speech_act=speech_act, target_entity_id=target_entity_id,
        semantic_cluster_key=cluster_key, stance=stance,
        affect=dict(affect_baseline), repetition_group_id=cluster_key,
        repetition_count=repetition_count,
        cause_hypothesis_claim_ids=cause_ids, confidence=confidence,
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
    "frustration": 900000.0, "hostility": 1800000.0,
    "playfulness": 600000.0, "repetition_pressure": 300000.0,
}


def update_user_affect(
    current: UserAffectState, semantics: ObservationSemantics,
    kernel: ContextKernel, signal_id: str | None = None,
) -> UserAffectState:
    elapsed_ms = (kernel.time.now - current.last_updated_at) * 1000.0 if current.last_updated_at > 0 else 0.0
    affect = UserAffectState(
        current_stance=current.current_stance,
        frustration=_decay(current.frustration, elapsed_ms, _HALF_LIVES["frustration"]),
        hostility=_decay(current.hostility, elapsed_ms, _HALF_LIVES["hostility"]),
        playfulness=_decay(current.playfulness, elapsed_ms, _HALF_LIVES["playfulness"]),
        active_quality_atom_keys=list(current.active_quality_atom_keys),
        last_updated_signal_id=signal_id or current.last_updated_signal_id,
        last_updated_at=kernel.time.now,
        decay_half_life_ms=current.decay_half_life_ms,
    )
    sem_affect = semantics.affect
    affect.frustration = max(0.0, min(1.0, affect.frustration + sem_affect.get("frustration", 0.0)))
    affect.hostility = max(0.0, min(1.0, affect.hostility + sem_affect.get("hostility", 0.0)))
    affect.playfulness = max(0.0, min(1.0, affect.playfulness + sem_affect.get("playfulness", 0.0)))
    f, h, p = affect.frustration, affect.hostility, affect.playfulness
    if h > 0.5: affect.current_stance = "hostile"
    elif f > 0.5: affect.current_stance = "frustrated"
    elif p > 0.5: affect.current_stance = "playful"
    else: affect.current_stance = "cooperative"
    return affect


def update_conversation_dynamics(
    current: ConversationDynamics, semantics: ObservationSemantics,
    kernel: ContextKernel, signal_id: str | None = None,
) -> ConversationDynamics:
    elapsed_ms = (kernel.time.now - current.last_updated_at) * 1000.0 if current.last_updated_at > 0 else 0.0
    dynamics = ConversationDynamics(
        repetition_pressure=_decay(current.repetition_pressure, elapsed_ms, _HALF_LIVES["repetition_pressure"]),
        active_repetition_group_ids=list(current.active_repetition_group_ids),
        active_process_atom_keys=list(current.active_process_atom_keys),
        likely_cause_claim_ids=list(current.likely_cause_claim_ids),
        last_updated_signal_id=signal_id or current.last_updated_signal_id,
        last_updated_at=kernel.time.now,
        decay_half_life_ms=current.decay_half_life_ms,
    )
    if semantics.repetition_group_id:
        dynamics.repetition_pressure = max(0.0, min(1.0, dynamics.repetition_pressure + 0.15))
    if semantics.repetition_group_id:
        if semantics.repetition_group_id not in dynamics.active_repetition_group_ids:
            dynamics.active_repetition_group_ids.append(semantics.repetition_group_id)
    if semantics.cause_hypothesis_claim_ids:
        merged = set(dynamics.likely_cause_claim_ids) | set(semantics.cause_hypothesis_claim_ids)
        dynamics.likely_cause_claim_ids = sorted(merged)
    return dynamics
