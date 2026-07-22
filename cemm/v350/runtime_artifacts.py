"""Typed cycle artifacts shared by the canonical Stage-0..22 runtime."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class StageReceipt:
    stage: int
    status: str
    reason_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {
            "performed",
            "deferred",
            "blocked",
            "no_authorized_work",
        }:
            raise ValueError(
                f"invalid stage receipt status: {self.status}"
            )


@dataclass(frozen=True, slots=True)
class RuntimeInput:
    content: str
    language_hints: tuple[str, ...] = ()
    emission_idempotency_key: str | None = None
    discourse_anchors: tuple[Any, ...] = ()
    multimodal_tracks: tuple[Any, ...] = ()
    system_output_anchors: tuple[Any, ...] = ()
    grounding_constraints: tuple[Any, ...] = ()
    speaker_ref: str | None = None
    participant_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError(
                "runtime input content must be text"
            )
        if len(self.language_hints) != len(
            set(self.language_hints)
        ):
            raise ValueError(
                "language hints must be unique"
            )
        if (
            self.emission_idempotency_key is not None
            and not self.emission_idempotency_key.strip()
        ):
            raise ValueError(
                "emission idempotency key must be non-empty"
            )
        if (
            self.speaker_ref is not None
            and not self.speaker_ref.strip()
        ):
            raise ValueError(
                "speaker_ref must be non-empty"
            )
        if len(self.participant_evidence_refs) != len(
            set(self.participant_evidence_refs)
        ):
            raise ValueError(
                "participant evidence refs must be unique"
            )
        if (
            self.speaker_ref is not None
            and not self.participant_evidence_refs
        ):
            raise ValueError(
                "speaker_ref requires explicit "
                "participant identity evidence"
            )
        for values, attribute, label in (
            (
                self.discourse_anchors,
                "anchor_ref",
                "discourse anchors",
            ),
            (
                self.multimodal_tracks,
                "track_ref",
                "multimodal tracks",
            ),
            (
                self.system_output_anchors,
                "output_ref",
                "system-output anchors",
            ),
            (
                self.grounding_constraints,
                "constraint_ref",
                "grounding constraints",
            ),
        ):
            refs = tuple(
                getattr(item, attribute, None)
                for item in values
            )
            if (
                any(not ref for ref in refs)
                or len(refs) != len(set(refs))
            ):
                raise ValueError(
                    f"{label} require unique stable refs"
                )


@dataclass(frozen=True, slots=True)
class TextObservation:
    source_ref: str
    content: str
    channel_ref: str
    context_ref: str
    permission_ref: str
    audience_refs: tuple[str, ...]
    language_hints: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AuthorityPin:
    kind: str
    ref: str
    revision: int
    fingerprint: str


@dataclass(frozen=True, slots=True)
class CyclePins:
    snapshot_fingerprint: str
    store_revision: int
    boot_fingerprint: str
    overlay_fingerprint: str
    cycle_time: str
    context_ref: str
    permission_ref: str
    channel_ref: str
    target_language: str | None
    runtime_version: str
    authority_generation: int = 1
    authority_fingerprint: str = ""
    cognitive_generation_fingerprint: str = ""
    world_revision: int = 0
    discourse_revision: int = 0
    runtime_observation_revision: int = 0
    audit_revision: int = 0
    effect_journal_revision: int = 0
    language_pack_pins: tuple[AuthorityPin, ...] = ()
    operation_adapter_pins: tuple[AuthorityPin, ...] = ()
    semantic_analyzer_pins: tuple[AuthorityPin, ...] = ()
    channel_adapter_pins: tuple[AuthorityPin, ...] = ()


@dataclass(frozen=True, slots=True)
class FinalizationSummary:
    initial_snapshot_fingerprint: str
    final_snapshot_fingerprint: str
    initial_store_revision: int
    final_store_revision: int
    substrate_changed: bool
    recomputation_required: bool
    replay_required_refs: tuple[str, ...] = ()
    unresolved_frontier_refs: tuple[str, ...] = ()
    incomplete_budget_refs: tuple[str, ...] = ()
    invalidation_authority: str = (
        "semantic_store_dependency_graph"
    )

    def __post_init__(self) -> None:
        if (
            self.initial_store_revision < 0
            or self.final_store_revision
            < self.initial_store_revision
        ):
            raise ValueError(
                "finalization store revision must be monotonic"
            )
        if (
            not self.initial_snapshot_fingerprint
            or not self.final_snapshot_fingerprint
        ):
            raise ValueError(
                "finalization requires exact "
                "initial/final snapshot fingerprints"
            )
        if len(self.replay_required_refs) != len(
            set(self.replay_required_refs)
        ):
            raise ValueError(
                "replay requirements must be unique"
            )
        if len(self.unresolved_frontier_refs) != len(
            set(self.unresolved_frontier_refs)
        ):
            raise ValueError(
                "finalization frontiers must be unique"
            )


@dataclass(frozen=True, slots=True)
class RuntimeTrace:
    stages: tuple[str, ...]
    details: tuple[Mapping[str, Any], ...]
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    cycle_ref: str
    context_ref: str
    output_text: str | None
    target_language: str | None
    stage_trace: tuple[Mapping[str, Any], ...]
    frontier_refs: tuple[str, ...]
    errors: tuple[str, ...]
    artifacts: Mapping[str, Any]
    committed_patch_refs: tuple[str, ...] = ()

    @property
    def emitted(self) -> bool:
        return bool(self.output_text)

    @property
    def cycle_id(self) -> str:
        return self.cycle_ref

    @property
    def context_id(self) -> str:
        return self.context_ref

    @property
    def completion_status(self) -> str:
        return str(
            self.artifacts.get(
                "cycle_completion_status",
                "PARTIAL",
            )
        )

    @property
    def trace(self) -> RuntimeTrace:
        return RuntimeTrace(
            stages=tuple(
                str(item.get("stage_name", ""))
                for item in self.stage_trace
            ),
            details=self.stage_trace,
            errors=self.errors,
        )
