#!/usr/bin/env python3
"""Apply CEMM v3.5.1 Phase 2-3 transformations to the 2cad08f baseline.

Copy the bundle's replacement/new files into the repo first, then run this script
from repository root. Every transformation is fail-fast and must match exactly once.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path.cwd()


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: expected exactly one anchor, found {count}: {old[:120]!r}"
        )
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def regex_once(path: str, pattern: str, replacement: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S | re.M)
    if count != 1:
        raise SystemExit(
            f"{path}: expected exactly one regex match, found {count}: {pattern[:120]!r}"
        )
    target.write_text(updated, encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 2 storage substrate
# ---------------------------------------------------------------------------

# Allow the canonical generation store to use a named shared-memory URI.
replace_once(
    "cemm/v350/storage/store.py",
    '''        self._overlay = sqlite3.connect(
            self.overlay_path,
            check_same_thread=False,
            isolation_level=None,
        )''',
    '''        self._overlay = sqlite3.connect(
            self.overlay_path,
            uri=self.overlay_path.startswith("file:"),
            check_same_thread=False,
            isolation_level=None,
        )''',
)

# Eliminate the remaining all-RecordKind staged lookup path.
replace_once(
    "cemm/v350/storage/store.py",
    '''    def resolve_any(self, record_ref: str) -> tuple[StoredRecord[Any], ...]:
        result = []
        for kind in RecordKind:
            value = self.resolve(kind, record_ref)
            if value is not None:
                result.append(value)
        return tuple(result)''',
    '''    def resolve_any(self, record_ref: str) -> tuple[StoredRecord[Any], ...]:
        kinds = {
            kind
            for (kind, ref, _revision) in self._staged
            if ref == record_ref
        }
        kinds.update(
            item.record_kind
            for item in self._store.resolve_any(record_ref)
        )
        result = []
        for kind in sorted(kinds, key=lambda item: item.value):
            value = self.resolve(kind, record_ref)
            if value is not None:
                result.append(value)
        return tuple(result)''',
)

# Canonical runtime import resolves to GenerationSemanticStore. The legacy class is
# retained as its implementation base for compatibility/migration tests.
replace_once(
    "cemm/v350/storage/__init__.py",
    '    "SemanticStore": ".store",',
    '    "SemanticStore": ".generation_store",',
)

# Generation metadata is additive; do not bump the signed v3.5 storage schema yet.
replace_once(
    "cemm/v350/storage/sqlite_schema.py",
    '''    "record_set_fingerprint": "",
}''',
    '''    "record_set_fingerprint": "",
    "authority_generation": "1",
    "authority_fingerprint": "",
    "world_revision": "0",
    "discourse_revision": "0",
    "runtime_observation_revision": "0",
    "audit_revision": "0",
    "effect_journal_revision": "0",
    "overlay_root": "",
}''',
)

# Split exact authority identity from mutable read generations while preserving the
# compatibility snapshot API until Phase 5 changes the Stage ABI.
regex_once(
    "cemm/v350/storage/model.py",
    r'''@dataclass\(frozen=True, slots=True\)\nclass StoreSnapshot:\n.*?\n\n\ndef _confidence''',
    '''@dataclass(frozen=True, slots=True)
class StoreSnapshot:
    store_revision: int
    boot_fingerprint: str
    overlay_fingerprint: str
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    snapshot_ref: str = ""
    authority_generation: int = 1
    authority_fingerprint: str = ""
    world_revision: int = 0
    discourse_revision: int = 0
    runtime_observation_revision: int = 0
    audit_revision: int = 0
    effect_journal_revision: int = 0

    @property
    def read_generation(self):
        from ..runtime_generations import ReadGeneration
        authority_fingerprint = self.authority_fingerprint or semantic_fingerprint(
            "legacy-authority-root",
            (self.boot_fingerprint, self.overlay_fingerprint),
            64,
        )
        return ReadGeneration(
            store_revision=self.store_revision,
            authority_generation=self.authority_generation,
            authority_fingerprint=authority_fingerprint,
            world_revision=self.world_revision,
            discourse_revision=self.discourse_revision,
            runtime_observation_revision=self.runtime_observation_revision,
            audit_revision=self.audit_revision,
            effect_journal_revision=self.effect_journal_revision,
            overlay_fingerprint=self.overlay_fingerprint,
            boot_fingerprint=self.boot_fingerprint,
        )

    @property
    def cognitive_fingerprint(self) -> str:
        return self.read_generation.cognitive_fingerprint

    @property
    def fingerprint(self) -> str:
        return self.read_generation.fingerprint


def _confidence''',
)

# Schema and language registries depend on semantic authority, not unrelated mutable
# world/discourse/audit revisions.
replace_once(
    "cemm/v350/storage/repositories.py",
    '''        if snapshot is None:
            key = (
                self._store.revision,
                self._store.boot_fingerprint,
                self._store.overlay_fingerprint,
            )
        else:
            self._store.assert_snapshot(snapshot)
            key = (
                snapshot.store_revision,
                snapshot.boot_fingerprint,
                snapshot.overlay_fingerprint,
            )''',
    '''        if snapshot is None:
            authority = self._store.current_authority_snapshot()
            key = (authority.generation, authority.authority_fingerprint)
        else:
            self._store.assert_snapshot(snapshot)
            key = (snapshot.authority_generation, snapshot.authority_fingerprint)''',
)
replace_once(
    "cemm/v350/storage/repositories.py",
    '        self._registry_cache: dict[tuple[int, str, str], LanguageRegistry] = {}',
    '        self._registry_cache: dict[tuple[int, str], LanguageRegistry] = {}',
)
replace_once(
    "cemm/v350/storage/repositories.py",
    '''        if snapshot is None:
            key = (self._store.revision, self._store.boot_fingerprint, self._store.overlay_fingerprint)
        else:
            self._store.assert_snapshot(snapshot)
            key = (snapshot.store_revision, snapshot.boot_fingerprint, snapshot.overlay_fingerprint)''',
    '''        if snapshot is None:
            authority = self._store.current_authority_snapshot()
            key = (authority.generation, authority.authority_fingerprint)
        else:
            self._store.assert_snapshot(snapshot)
            key = (snapshot.authority_generation, snapshot.authority_fingerprint)''',
)

# ---------------------------------------------------------------------------
# Phase 1 residual hardening
# ---------------------------------------------------------------------------

# Seal nested manifest mappings after full attestation. Runtime consumers no longer
# observe a mutable nested configuration object after verification.
replace_once(
    "cemm/v350/runtime_authority.py",
    "from dataclasses import dataclass",
    "from dataclasses import dataclass, replace",
)
replace_once(
    "cemm/v350/runtime_authority.py",
    '''import importlib
from threading import RLock''',
    '''import importlib
from types import MappingProxyType
from threading import RLock''',
)
replace_once(
    "cemm/v350/runtime_authority.py",
    "class AttestedRuntimeAuthority:",
    '''def _deep_freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_deep_freeze(item) for item in value)
    return value


def _sealed_manifest_copy(manifest):
    fields = {}
    for name in ("metadata", "release_capabilities"):
        value = getattr(manifest, name, None)
        if value is not None:
            fields[name] = _deep_freeze(dict(value))
    bindings = getattr(manifest, "runtime_service_bindings", None)
    if bindings is not None:
        fields["runtime_service_bindings"] = tuple(
            _deep_freeze(dict(item)) for item in bindings
        )
    return replace(manifest, **fields) if fields else manifest


class AttestedRuntimeAuthority:''',
)
replace_once(
    "cemm/v350/runtime_authority.py",
    '''        self._guard = guard
        self.attestation = attestation''',
    '''        self._guard = guard
        self._sealed_manifest = _sealed_manifest_copy(guard.manifest)
        self.attestation = attestation''',
)
replace_once(
    "cemm/v350/runtime_authority.py",
    '''    def manifest(self) -> Any:
        return self._guard.manifest''',
    '''    def manifest(self) -> Any:
        return self._sealed_manifest''',
)

# ---------------------------------------------------------------------------
# Runtime generation pinning / targeted learning / lifecycle
# ---------------------------------------------------------------------------

replace_once(
    "cemm/v350/runtime.py",
    '''    runtime_authority_generation: int | None = None''',
    '''    runtime_authority_generation: int | None = None
    runtime_observation_snapshot: Any | None = None
    retain_transient_audit: bool = True''',
)

replace_once(
    "cemm/v350/runtime.py",
    '''    def fingerprint(self) -> str:
        with self.store.snapshot() as snapshot:
            return snapshot.fingerprint''',
    '''    def fingerprint(self) -> str:
        return self.store.current_read_generation().fingerprint

    def generation(self):
        return self.store.current_read_generation()

    def authority_snapshot(self, *, runtime_attestation_ref: str = ""):
        return self.store.current_authority_snapshot(
            runtime_attestation_ref=runtime_attestation_ref
        )

    def semantic_pass(self):
        return self.store.semantic_pass()''',
)

regex_once(
    "cemm/v350/runtime.py",
    r'''    def _snapshot\(self, capability: StageCapability, cycle: CycleState \| None = None, \*, require_cycle_pin: bool = False\):\n.*?        return cm, snapshot\n''',
    '''    def _snapshot(self, capability: StageCapability, cycle: CycleState | None = None, *, require_cycle_pin: bool = False):
        from .runtime_generations import ReadGenerationChanged
        cm = self.store.snapshot()
        snapshot = cm.__enter__()
        if capability.authority_generation and snapshot.authority_generation != capability.authority_generation:
            cm.__exit__(None, None, None)
            raise ReadGenerationChanged("authority generation changed before stage execution")
        if capability.authority_fingerprint and snapshot.authority_fingerprint != capability.authority_fingerprint:
            cm.__exit__(None, None, None)
            raise ReadGenerationChanged("authority fingerprint changed before stage execution")
        # Audit/effect-only revision movement must not restart unrelated cognition.
        # Pre-commit semantic stability is enforced by the cognitive generation below,
        # while exact semantic authority is checked independently above.
        if require_cycle_pin and cycle is not None:
            pins = cycle.artifacts.get("cycle_pins")
            if pins is None:
                cm.__exit__(None, None, None)
                raise RuntimeError("cycle pins missing")
            if snapshot.authority_fingerprint != pins.authority_fingerprint:
                cm.__exit__(None, None, None)
                raise ReadGenerationChanged("semantic authority changed during one pass")
            if int(capability.stage) <= int(CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE):
                if snapshot.cognitive_fingerprint != pins.cognitive_generation_fingerprint:
                    cm.__exit__(None, None, None)
                    raise ReadGenerationChanged("mutable cognitive read generation changed before commit")
        return cm, snapshot
''',
)

regex_once(
    "cemm/v350/runtime.py",
    r'''    def _resolve_any\(self, record_ref: str\) -> tuple\[Any, \.\.\.\]:\n.*?        return tuple\(sorted\(found, key=lambda item: \(item\.record_kind\.value, item\.revision\)\)\)\n''',
    '''    def _resolve_any(self, record_ref: str) -> tuple[Any, ...]:
        if not record_ref:
            return ()
        return tuple(
            sorted(
                self.store.resolve_any(record_ref),
                key=lambda item: (item.record_kind.value, item.revision),
            )
        )
''',
)

replace_once(
    "cemm/v350/runtime.py",
    '''                runtime_version=VERSION,
                language_pack_pins=pins_for(RecordKind.LANGUAGE_PACK),''',
    '''                runtime_version=VERSION,
                authority_generation=snapshot.authority_generation,
                authority_fingerprint=snapshot.authority_fingerprint,
                cognitive_generation_fingerprint=snapshot.cognitive_fingerprint,
                world_revision=snapshot.world_revision,
                discourse_revision=snapshot.discourse_revision,
                runtime_observation_revision=snapshot.runtime_observation_revision,
                audit_revision=snapshot.audit_revision,
                effect_journal_revision=snapshot.effect_journal_revision,
                language_pack_pins=pins_for(RecordKind.LANGUAGE_PACK),''',
)

# Stage 11 retrieves only structural frontier refs produced by this observation.
regex_once(
    "cemm/v350/runtime.py",
    r'''    def stage_11_learning_frontiers\(self, cycle: CycleState, capability: StageCapability\) -> StageOutcome:\n.*?        return StageOutcome\(\{"learning_observations": observations, "learning_frontier_records": frontiers, "stage11_receipt": self\._receipt\(CoreStage\.BUILD_OR_ADVANCE_LEARNING_FRONTIERS, "performed" if observations else "no_authorized_work", "learning_frontiers_built"\)\}, frontier_refs=tuple\(item\.frontier_ref for item in frontiers\)\)\n''',
    '''    def stage_11_learning_frontiers(self, cycle: CycleState, capability: StageCapability) -> StageOutcome:
        from .learning.runtime import TypedRuntimeFrontierCompiler
        observations = TypedRuntimeFrontierCompiler().compile(cycle)
        collector = FrontierCollector()
        cm, snapshot = self._snapshot(capability, cycle, require_cycle_pin=True)
        try:
            existing = []
            for frontier_ref in sorted({
                collector.frontier_ref_for_observation(item)
                for item in observations
            }):
                stored = self.store.get_record(
                    RecordKind.LEARNING_FRONTIER,
                    frontier_ref,
                    snapshot=snapshot,
                )
                if stored is not None:
                    existing.append(stored.payload)
        finally:
            cm.__exit__(None, None, None)
        frontiers = collector.collect(observations, tuple(existing))
        return StageOutcome(
            {
                "learning_observations": observations,
                "learning_frontier_records": frontiers,
                "stage11_receipt": self._receipt(
                    CoreStage.BUILD_OR_ADVANCE_LEARNING_FRONTIERS,
                    "performed" if observations else "no_authorized_work",
                    "learning_frontiers_built",
                ),
            },
            frontier_refs=tuple(item.frontier_ref for item in frontiers),
        )
''',
)

# Remove request-frequency candidate/competence advancement. Stage 13 only records
# evidence/frontiers and emits an event for explicit maintenance.
regex_once(
    "cemm/v350/runtime.py",
    r'''        learning_advance_trace = None\n        if observations:\n            from \.learning\.runtime_advance import RuntimeLearningAdvancer\n            learning_advance_trace = RuntimeLearningAdvancer\(\n                self\.store,\n                inducers=tuple\(self\.services\.learning_inducers\),\n                competence_executors=dict\(\n                    self\.services\.learning_competence_executors\n                \),\n            \)\.advance\(\n                context_ref=cycle\.context_ref,\n                permission_ref=cycle\.permission_ref,\n            \)\n''',
    '''        learning_advance_trace = None
        maintenance_event = (
            ("learning_evidence_changed", tuple(learning_commit_trace.frontier_refs))
            if learning_commit_trace is not None and learning_commit_trace.frontier_refs
            else None
        )
''',
)
replace_once(
    "cemm/v350/runtime.py",
    '''                "learning_advance_trace": learning_advance_trace,
                "stage13_receipt":''',
    '''                "learning_advance_trace": learning_advance_trace,
                "maintenance_event": maintenance_event,
                "stage13_receipt":''',
)

# Stage22 should report executable-authority drift separately from the cycle's own
# expected world/discourse/audit commits.
replace_once(
    "cemm/v350/runtime.py",
    '''        substrate_changed=(
            final_revision != pins.store_revision
            or final_fp != pins.snapshot_fingerprint
        )''',
    '''        substrate_changed=(
            snapshot.authority_generation != pins.authority_generation
            or snapshot.authority_fingerprint != pins.authority_fingerprint
        )''',
)

# Session lifecycle and explicit maintenance objects.
replace_once(
    "cemm/v350/runtime.py",
    '''    def __init__(self, *, store: SemanticStore, orchestrator: CanonicalOrchestrator, services: RuntimeServices | None = None) -> None:
        self.store=store; self.orchestrator=orchestrator; self.services=services or RuntimeServices()''',
    '''    def __init__(
        self,
        *,
        store: SemanticStore,
        orchestrator: CanonicalOrchestrator,
        services: RuntimeServices | None = None,
        maintenance_scheduler=None,
        session_lifecycle=None,
    ) -> None:
        from .maintenance import SessionParticipantLifecycle
        self.store = store
        self.orchestrator = orchestrator
        self.services = services or RuntimeServices()
        self.maintenance_scheduler = maintenance_scheduler
        self.session_lifecycle = session_lifecycle or SessionParticipantLifecycle()''',
)

# Phase-1 race hardening: a concurrent creator is accepted only if exact deterministic
# identities match, not merely because the refs now exist.
# Track the deterministic type assertion as part of the session identity CAS set.
replace_once(
    "cemm/v350/runtime.py",
    '''        evidence_fp = record_fingerprints(RecordKind.EVIDENCE, evidence)[1]
        if existing is None:''',
    '''        evidence_fp = record_fingerprints(RecordKind.EVIDENCE, evidence)[1]
        expected_type_assertion = None
        if existing is None:''',
)
regex_once(
    "cemm/v350/runtime.py",
    r'''(                assertion = ReferentTypeAssertion\(.*?\n                \))\n                operations\.append\(''',
    r'''\1\n                expected_type_assertion = assertion\n                operations.append(''',
)

replace_once(
    "cemm/v350/runtime.py",
    '''        result = self.store.apply_patch(patch)
        if not result.committed:
            # A concurrent creator is safe only if the same deterministic identity/evidence now exists.
            if (
                self.store.get_record(RecordKind.REFERENT, participant_ref) is None
                or self.store.get_record(RecordKind.EVIDENCE, evidence_ref) is None
            ):
                raise RuntimeError(
                    "session participant initialization failed: "
                    + "; ".join(result.errors)
                )
        return participant_ref, evidence_ref''',
    '''        result = self.store.apply_patch(patch)
        if not result.committed:
            concurrent_referent = self.store.get_record(RecordKind.REFERENT, participant_ref)
            concurrent_evidence = self.store.get_record(RecordKind.EVIDENCE, evidence_ref)
            concurrent_assertion = (
                None
                if expected_type_assertion is None
                else self.store.get_record(
                    RecordKind.TYPE_ASSERTION,
                    expected_type_assertion.assertion_ref,
                )
            )
            expected_referent_fp = (
                None
                if existing is not None
                else record_fingerprints(RecordKind.REFERENT, referent)[1]
            )
            expected_assertion_fp = (
                None
                if expected_type_assertion is None
                else record_fingerprints(
                    RecordKind.TYPE_ASSERTION, expected_type_assertion
                )[1]
            )
            if (
                concurrent_referent is None
                or concurrent_evidence is None
                or concurrent_evidence.record_fingerprint != evidence_fp
                or (
                    expected_referent_fp is not None
                    and concurrent_referent.record_fingerprint != expected_referent_fp
                )
                or (
                    expected_assertion_fp is not None
                    and (
                        concurrent_assertion is None
                        or concurrent_assertion.record_fingerprint != expected_assertion_fp
                    )
                )
            ):
                raise RuntimeError(
                    "session participant initialization failed or collided: "
                    + "; ".join(result.errors)
                )
        return participant_ref, evidence_ref''',
)

# Remove request-frequency learning activation and runtime-self persistence.
replace_once(
    "cemm/v350/runtime.py",
    '''        from .learning.runtime import LearningRuntimeActivator
        from .runtime_state import RuntimeSelfObserver
        _learning_activation = LearningRuntimeActivator(self.store).activate_ready()
        RuntimeSelfObserver(self.store, self.services).observe(context_ref=context_id, permission_ref=permission_ref)
        resolved_speaker_ref, participant_evidence_ref = self._ensure_session_participant(
            context_id, permission_ref, speaker_ref
        )''',
    '''        resolved_speaker_ref, participant_evidence_ref = self.session_lifecycle.resolve(
            context_id,
            permission_ref,
            speaker_ref,
            initializer=self._ensure_session_participant,
        )''',
)

# Meaningful learning events enqueue maintenance but do not run it implicitly inside
# every ordinary request.
replace_once(
    "cemm/v350/runtime.py",
    '''        candidate=cycle.artifacts.get("surface_candidate"); emission=cycle.artifacts.get("emission")
        output_text=candidate.surface if emission is not None and candidate is not None else None''',
    '''        maintenance_event = cycle.artifacts.get("maintenance_event")
        if maintenance_event and self.maintenance_scheduler is not None:
            from .maintenance import MaintenanceTrigger
            trigger_name, refs = maintenance_event
            if trigger_name == "learning_evidence_changed":
                self.maintenance_scheduler.notify(
                    MaintenanceTrigger.LEARNING_EVIDENCE_CHANGED,
                    refs=refs,
                    context_ref=context_id,
                    permission_ref=permission_ref,
                )
        candidate=cycle.artifacts.get("surface_candidate"); emission=cycle.artifacts.get("emission")
        output_text=candidate.surface if emission is not None and candidate is not None else None''',
)

replace_once(
    "cemm/v350/runtime.py",
    '''    def close(self) -> None:
        self.store.close()''',
    '''    def prepare_session(
        self,
        *,
        context_id: str = "conversation",
        permission_ref: str = "conversation",
        speaker_ref: str | None = None,
    ) -> tuple[str, str]:
        return self.session_lifecycle.resolve(
            context_id,
            permission_ref,
            speaker_ref,
            initializer=self._ensure_session_participant,
        )

    def run_maintenance(self, trigger=None):
        if self.maintenance_scheduler is None:
            return ()
        from .maintenance import MaintenanceEvent, MaintenanceTrigger
        resolved = (
            MaintenanceTrigger.STARTUP
            if trigger is None
            else trigger if isinstance(trigger, MaintenanceTrigger) else MaintenanceTrigger(str(trigger))
        )
        return self.maintenance_scheduler.run_event(MaintenanceEvent(resolved))

    def drain_maintenance(self):
        if self.maintenance_scheduler is None:
            return ()
        return self.maintenance_scheduler.drain()

    def refresh_runtime_observation(self):
        if self.maintenance_scheduler is None:
            return ()
        from .maintenance import MaintenanceEvent, MaintenanceTrigger
        return self.maintenance_scheduler.run_event(
            MaintenanceEvent(MaintenanceTrigger.RUNTIME_SIGNAL_CHANGED)
        )

    def close(self) -> None:
        self.store.close()''',
)

replace_once(
    "cemm/v350/runtime.py",
    '''    orchestrator=CanonicalOrchestrator(adapters,snapshot_provider=StoreSnapshotProvider(store),authority_guard=authority_guard)
    return Runtime(store=store,orchestrator=orchestrator,services=services)''',
    '''    orchestrator=CanonicalOrchestrator(
        adapters,
        snapshot_provider=StoreSnapshotProvider(store),
        authority_guard=authority_guard,
    )
    from .maintenance import (
        MaintenanceEvent,
        MaintenanceTrigger,
        SessionParticipantLifecycle,
        build_default_maintenance_scheduler,
    )
    scheduler = build_default_maintenance_scheduler(store, services)
    runtime = Runtime(
        store=store,
        orchestrator=orchestrator,
        services=services,
        maintenance_scheduler=scheduler,
        session_lifecycle=SessionParticipantLifecycle(),
    )
    scheduler.run_event(MaintenanceEvent(MaintenanceTrigger.STARTUP))
    return runtime''',
)

# ---------------------------------------------------------------------------
# Phase 3 learning maintenance
# ---------------------------------------------------------------------------

# Late-stage frontier collection stays at Stage22, but candidate/competence advancement
# moves to explicit event-driven maintenance.
regex_once(
    "cemm/v350/runtime_hardening.py",
    r'''        from \.learning\.runtime_advance import RuntimeLearningAdvancer\n        advance = RuntimeLearningAdvancer\(.*?\n        base = super\(\)\.stage_22_finalize\(cycle, capability\)''',
    '''        advance = None
        base = super().stage_22_finalize(cycle, capability)''',
)
replace_once(
    "cemm/v350/runtime_hardening.py",
    '''                "late_learning_advance_trace": advance,
            },''',
    '''                "late_learning_advance_trace": advance,
                "maintenance_event": (
                    "learning_evidence_changed",
                    tuple(trace.frontier_refs),
                ) if trace.frontier_refs else cycle.artifacts.get("maintenance_event"),
            },''',
)

# RuntimeLearningAdvancer can consume targeted event refs and must preserve candidate
# dependency pins. This also fixes the Phase-1-live undefined dependency_pins bug.
replace_once(
    "cemm/v350/learning/runtime_advance.py",
    '''        permission_ref: str,
    ) -> RuntimeLearningAdvanceTrace:
        frontiers = tuple(
            item.payload
            for item in self.store.repositories.learning_frontiers.all()
            if item.payload.context_ref in {context_ref, "global"}
            and item.payload.permission_ref in {permission_ref, "public"}
            and item.payload.resolution_status.value in {"open", "partial"}
        )''',
    '''        permission_ref: str,
        frontier_refs: tuple[str, ...] | None = None,
    ) -> RuntimeLearningAdvanceTrace:
        if frontier_refs:
            frontiers = tuple(
                stored.payload
                for ref in sorted(set(frontier_refs))
                for stored in (self.store.get_record(RecordKind.LEARNING_FRONTIER, ref),)
                if stored is not None
                and stored.payload.context_ref in {context_ref, "global"}
                and stored.payload.permission_ref in {permission_ref, "public"}
                and stored.payload.resolution_status.value in {"open", "partial"}
            )
        else:
            frontiers = tuple(
                item.payload
                for item in self.store.repositories.learning_frontiers.all()
                if item.payload.context_ref in {context_ref, "global"}
                and item.payload.permission_ref in {permission_ref, "public"}
                and item.payload.resolution_status.value in {"open", "partial"}
            )''',
)
replace_once(
    "cemm/v350/learning/runtime_advance.py",
    '''            pins = self._persist_proposals(frontier, tuple(proposals))
            candidate_refs.extend(pin.record_ref for pin in pins)
            if not pins:''',
    '''            pins, dependency_pins = self._persist_proposals(frontier, tuple(proposals))
            candidate_refs.extend(pin.record_ref for pin in pins)
            if not pins:''',
)
replace_once(
    "cemm/v350/learning/runtime_advance.py",
    '''        operations = []
        pins = []
        with self.store.snapshot() as snapshot:''',
    '''        operations = []
        pins = []
        dependency_pins = {
            pin.key: pin
            for proposal in proposals
            for pin in proposal.dependency_pins
        }
        with self.store.snapshot() as snapshot:''',
)
replace_once(
    "cemm/v350/learning/runtime_advance.py",
    '''                return ()
        return tuple(pins)

    def _package(self, frontier, pins):''',
    '''                return (), ()
        return (
            tuple(pins),
            tuple(dependency_pins[key] for key in sorted(dependency_pins)),
        )

    def _package(self, frontier, pins, dependency_pins):''',
)
replace_once(
    "cemm/v350/learning/runtime_advance.py",
    '''            dependency_pins=tuple(
                pin
                for proposal in ()
                for pin in proposal.dependency_pins
            ),''',
    '''            dependency_pins=tuple(dependency_pins),''',
)

print("CEMM v3.5.1 Phase 2-3 transformations applied.")
