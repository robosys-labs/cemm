from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ..types.signal import Signal, SignalKind, SourceType, ObservationSemantics
from ..types.context_kernel import ContextKernel, UserAffectState, ConversationDynamics
from ..store.store import Store
from ..registry.registry import Registry
from .semantic_clusters import SemanticClusterRegistry

_UOL_SEMANTICS_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load_failure_markers() -> set[str]:
    """Load failure marker cues from UOL semantic metadata."""
    if not _UOL_SEMANTICS_PATH.exists():
        return set()
    data = json.loads(_UOL_SEMANTICS_PATH.read_text(encoding="utf-8"))
    for entry in data.get("uol_semantics", []):
        if entry.get("cue_type") == "failure_marker":
            return set(entry.get("aliases", []))
    return set()


_FAILURE_MARKERS = _load_failure_markers()

_DEFAULT_REGISTRY = SemanticClusterRegistry()
_SPEECH_ACT_TO_FRAME_KEY = {
    "greeting": "greeting",
    "acknowledgment": "acknowledgment",
    "clarification": "request_clarification",
    "exit": "session_exit",
    "command": "command_remember",
    "playful_acknowledgment": "playful_acknowledgment",
    "confusion": "request_clarification",
    "self_correction": "self_correction",
    "simplification_request": "simplification_request",
    "reassurance": "reassurance",
}


def interpret_signal(
    signal: Signal,
    kernel: ContextKernel,
    store: Store | None = None,
    registry: SemanticClusterRegistry | None = None,
    main_registry: Registry | None = None,
) -> ObservationSemantics | None:
    if signal.source_type != SourceType.USER or signal.kind != SignalKind.INPUT:
        return None
    if registry is not None:
        reg = registry
    elif main_registry is not None:
        reg = SemanticClusterRegistry(registry=main_registry)
    else:
        reg = _DEFAULT_REGISTRY
    extra_forms = signal.normalized.normalized_forms if signal.normalized else []
    ranked = reg.match_ranked(signal.content, extra_forms=extra_forms)
    if not ranked:
        return ObservationSemantics(speech_act="unknown", stance="unknown", confidence=0.0)
    best = ranked[0]
    cluster_key = best.cluster_key
    speech_act = best.speech_act
    confidence = best.confidence
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
    frame_key = _SPEECH_ACT_TO_FRAME_KEY.get(speech_act, "")
    return ObservationSemantics(
        speech_act=speech_act, target_entity_id=target_entity_id,
        semantic_cluster_key=cluster_key, stance=stance,
        affect=dict(affect_baseline), repetition_group_id=cluster_key,
        repetition_count=repetition_count,
        cause_hypothesis_claim_ids=cause_ids, confidence=confidence,
        frame_key=frame_key,
    )


def _trace_causes(store: Store, kernel: ContextKernel) -> list[str]:
    def _looks_like_failure_cause(claim) -> bool:
        if claim is None or claim.domain != "causal":
            return False
        text_parts = [
            str(claim.subject_entity_id or ""),
            str(claim.predicate or ""),
            str(claim.object_value or ""),
        ]
        text = " ".join(text_parts).lower()
        return any(marker in text for marker in _FAILURE_MARKERS)

    candidate_ids: list[str] = []
    candidate_ids.extend(kernel.memory.working_claim_ids[-5:])

    self_state = store.self_store.latest()
    if self_state is not None:
        candidate_ids.extend(self_state.meta_memory.recently_written_claim_ids[-10:])

    seen: set[str] = set()
    result: list[str] = []
    for cid in reversed(candidate_ids):
        if cid in seen:
            continue
        seen.add(cid)
        claim = store.claims.get(cid)
        if _looks_like_failure_cause(claim):
            result.append(cid)
    return result[:3]


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

    # Conflicting affect should not accumulate without resistance:
    # sharp negative turns cool lingering playfulness, while playful turns
    # can soften mild negativity without erasing it.
    negative_push = sem_affect.get("frustration", 0.0) + (sem_affect.get("hostility", 0.0) * 0.75)
    if negative_push > 0.0:
        cool_factor = max(0.15, 1.0 - min(0.85, negative_push * 0.9))
        affect.playfulness = max(0.0, min(1.0, affect.playfulness * cool_factor))

    playful_push = sem_affect.get("playfulness", 0.0)
    if playful_push > 0.0:
        soften_factor = max(0.65, 1.0 - min(0.35, playful_push * 0.25))
        affect.frustration = max(0.0, min(1.0, affect.frustration * soften_factor))
        affect.hostility = max(0.0, min(1.0, affect.hostility * soften_factor))

    f, h, p = affect.frustration, affect.hostility, affect.playfulness
    if h >= 0.45 and h >= f and h >= p:
        affect.current_stance = "hostile"
    elif f >= 0.4 and f >= p:
        affect.current_stance = "frustrated"
    elif p >= 0.55 and p > max(f, h) + 0.1:
        affect.current_stance = "playful"
    else:
        affect.current_stance = "cooperative"
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


def affect_markers_to_semantics(
    affect_markers: list[dict[str, Any]],
    signal_id: str = "",
) -> ObservationSemantics:
    """Convert MeaningPerceptPacket.affect_markers into ObservationSemantics.

    This bridges the gap between the language adapter's affect detection
    and the pragmatic interpreter's update_user_affect function.
    """
    affect: dict[str, float] = {
        "valence": 0.0,
        "arousal": 0.0,
        "frustration": 0.0,
        "hostility": 0.0,
        "playfulness": 0.0,
    }
    for marker in affect_markers:
        marker_type = marker.get("type", "")
        valence = float(marker.get("valence", 0.0))
        if marker_type in ("frustration", "hostility", "playfulness"):
            affect[marker_type] = max(affect[marker_type], abs(valence))
        if valence > 0:
            affect["valence"] = max(affect["valence"], valence)
            affect["arousal"] = max(affect["arousal"], abs(valence))
        elif valence < 0:
            affect["valence"] = min(affect["valence"], valence)
            affect["arousal"] = max(affect["arousal"], abs(valence))
    return ObservationSemantics(
        speech_act="statement",
        affect=affect,
        confidence=0.6,
    )
