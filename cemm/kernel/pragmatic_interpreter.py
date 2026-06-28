from __future__ import annotations
from ..types.signal import Signal, SignalKind, SourceType, ObservationSemantics
from ..types.context_kernel import ContextKernel
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
