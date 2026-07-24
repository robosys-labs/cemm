"""Generation-separated runtime authority and mutable-state contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Any, Generic, Iterable, MutableMapping, TypeVar

from .csir.authority import CURRENT_KERNEL_ABI
from .schema.model import semantic_fingerprint
from .storage.model import GraphPatch, RecordKind


class GenerationDomain(str, Enum):
    AUTHORITY = "authority"
    WORLD = "world"
    DISCOURSE = "discourse"
    RUNTIME_OBSERVATION = "runtime_observation"
    AUDIT = "audit"
    EFFECT_JOURNAL = "effect_journal"


class ReadGenerationChanged(RuntimeError):
    """Mutable cognition changed during a pre-commit semantic pass."""


@dataclass(frozen=True, slots=True)
class AuthoritySnapshot:
    generation: int
    authority_fingerprint: str
    boot_fingerprint: str
    runtime_attestation_ref: str = ""
    kernel_abi_fingerprint: str = CURRENT_KERNEL_ABI.fingerprint

    def __post_init__(self) -> None:
        if self.generation < 1:
            raise ValueError("authority generation must be positive")
        if not self.authority_fingerprint or not self.boot_fingerprint:
            raise ValueError("authority snapshot requires exact fingerprints")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("authority snapshot Kernel Semantic ABI mismatch")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            "authority-snapshot",
            (
                self.generation,
                self.authority_fingerprint,
                self.boot_fingerprint,
                self.runtime_attestation_ref,
                self.kernel_abi_fingerprint,
            ),
            64,
        )


@dataclass(frozen=True, slots=True)
class ReadGeneration:
    store_revision: int
    authority_generation: int
    authority_fingerprint: str
    world_revision: int
    discourse_revision: int
    runtime_observation_revision: int
    audit_revision: int
    effect_journal_revision: int
    overlay_fingerprint: str
    boot_fingerprint: str

    def __post_init__(self) -> None:
        numeric = (
            self.store_revision,
            self.world_revision,
            self.discourse_revision,
            self.runtime_observation_revision,
            self.audit_revision,
            self.effect_journal_revision,
        )
        if any(value < 0 for value in numeric) or self.authority_generation < 1:
            raise ValueError("runtime generation revisions must be non-negative")
        if not self.authority_fingerprint:
            raise ValueError("read generation requires authority fingerprint")

    @property
    def cognitive_fingerprint(self) -> str:
        return semantic_fingerprint(
            "cognitive-read-generation",
            (
                self.world_revision,
                self.discourse_revision,
                self.runtime_observation_revision,
            ),
            64,
        )

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            "read-generation",
            (
                self.store_revision,
                self.authority_generation,
                self.authority_fingerprint,
                self.world_revision,
                self.discourse_revision,
                self.runtime_observation_revision,
                self.audit_revision,
                self.effect_journal_revision,
                self.overlay_fingerprint,
                self.boot_fingerprint,
            ),
            64,
        )

    def token_for(self, domains: Iterable[GenerationDomain]) -> tuple[Any, ...]:
        values = []
        for domain in sorted(set(domains), key=lambda item: item.value):
            if domain is GenerationDomain.AUTHORITY:
                values.append(
                    (
                        domain.value,
                        self.authority_generation,
                        self.authority_fingerprint,
                    )
                )
            elif domain is GenerationDomain.WORLD:
                values.append((domain.value, self.world_revision))
            elif domain is GenerationDomain.DISCOURSE:
                values.append((domain.value, self.discourse_revision))
            elif domain is GenerationDomain.RUNTIME_OBSERVATION:
                values.append((domain.value, self.runtime_observation_revision))
            elif domain is GenerationDomain.AUDIT:
                values.append((domain.value, self.audit_revision))
            elif domain is GenerationDomain.EFFECT_JOURNAL:
                values.append((domain.value, self.effect_journal_revision))
        return tuple(values)


AUTHORITY_RECORD_KINDS = frozenset({
    RecordKind.SCHEMA,
    RecordKind.FACET_ENTITLEMENT,
    RecordKind.TRANSITION_CONTRACT,
    RecordKind.CAPABILITY_DEPENDENCY,
    RecordKind.DEFAULT_RULE,
    RecordKind.IMPACT_RULE,
    RecordKind.IMPORTANCE_POLICY,
    RecordKind.RESPONSE_POLICY_RULE,
    RecordKind.RESPONSE_TRANSFORM_RULE,
    RecordKind.OPERATION_ADAPTER_CONTRACT,
    RecordKind.ARGUMENT_FRAME,
    RecordKind.MORPHOLOGY_RULE,
    RecordKind.LINEARIZATION_RULE,
    RecordKind.SEMANTIC_ANALYZER_CONTRACT,
    RecordKind.CHANNEL_ADAPTER_CONTRACT,
    RecordKind.LITERAL_EMISSION_POLICY,
    RecordKind.LANGUAGE_PACK,
    RecordKind.LANGUAGE_FORM,
    RecordKind.LEXEME,
    RecordKind.FORM_LEXEME_LINK,
    RecordKind.LEXICAL_SENSE,
    RecordKind.LEXEME_SENSE_LINK,
    RecordKind.FORM_SENSE_LINK,
    RecordKind.SEMANTIC_CONTRIBUTION_SPEC,
    RecordKind.MORPHOLOGY_ANALYSIS_RULE,
    RecordKind.CONSTRUCTION,
    RecordKind.CONSTRUCTION_PROGRAM,
})

DISCOURSE_RECORD_KINDS = frozenset({
    RecordKind.CLAIM_OCCURRENCE,
    RecordKind.CLAIM_RECORD,
    RecordKind.CLAIM_HISTORY,
    RecordKind.OUTPUT_DISCOURSE_ACT,
    RecordKind.OUTPUT_COMMITMENT,
    RecordKind.COMMON_GROUND,
    RecordKind.OUTPUT_REFERENCE_ANCHOR,
    RecordKind.OUTPUT_CORRECTION,
    RecordKind.SILENCE_OUTCOME,
})

EFFECT_RECORD_KINDS = frozenset({
    RecordKind.OPERATION_GATE_ASSESSMENT,
    RecordKind.OPERATION_PLAN,
    RecordKind.OPERATION_AUTHORIZATION,
    RecordKind.OPERATION_JOURNAL,
    RecordKind.OPERATION_RESULT,
    RecordKind.OPERATION_RECONCILIATION,
    RecordKind.EMISSION_GATE_ASSESSMENT,
    RecordKind.EMISSION_AUTHORIZATION,
    RecordKind.EMISSION_JOURNAL,
    RecordKind.EMISSION,
    RecordKind.EMISSION_ANOMALY,
})

WORLD_RECORD_KINDS = frozenset({
    RecordKind.REFERENT,
    RecordKind.TYPE_ASSERTION,
    RecordKind.IDENTITY_FACET,
    RecordKind.SEMANTIC_APPLICATION,
    RecordKind.PROPOSITION,
    RecordKind.EPISTEMIC_ADMISSION,
    RecordKind.KNOWLEDGE,
    RecordKind.EVENT_OCCURRENCE,
    RecordKind.STATE_ASSIGNMENT,
    RecordKind.STATE_DELTA,
    RecordKind.CAPABILITY_INSTANCE,
    RecordKind.CAPABILITY_DELTA,
    RecordKind.EVIDENCE,
    RecordKind.SOURCE_ASSESSMENT,
})


def domains_for_record_kind(kind: RecordKind) -> frozenset[GenerationDomain]:
    if kind in AUTHORITY_RECORD_KINDS:
        return frozenset({GenerationDomain.AUTHORITY})
    if kind in DISCOURSE_RECORD_KINDS:
        return frozenset({GenerationDomain.DISCOURSE})
    if kind in EFFECT_RECORD_KINDS:
        return frozenset({GenerationDomain.EFFECT_JOURNAL})
    if kind in WORLD_RECORD_KINDS:
        return frozenset({GenerationDomain.WORLD})
    return frozenset({GenerationDomain.AUDIT})


def _operation_domains(operation) -> frozenset[GenerationDomain]:
    kind = operation.record_kind
    base = domains_for_record_kind(kind)

    # Candidate/provisional definitions share storage kinds with active authority.
    # They are durable learning/audit state, not executable authority until an
    # ACTIVE revision is published.
    if GenerationDomain.AUTHORITY in base:
        op_value = str(
            getattr(
                operation.operation_kind,
                "value",
                operation.operation_kind,
            )
        )
        if op_value in {"tombstone", "invalidate"}:
            return base
        lifecycle = operation.payload.get("lifecycle_status")
        active = operation.payload.get("active")
        if lifecycle is not None and str(lifecycle) != "active":
            return frozenset({GenerationDomain.AUDIT})
        if active is not None and not bool(active):
            return frozenset({GenerationDomain.AUDIT})
    return base


def infer_patch_domains(patch: GraphPatch) -> frozenset[GenerationDomain]:
    domains: set[GenerationDomain] = {GenerationDomain.AUDIT}
    for operation in patch.operations:
        domains.update(_operation_domains(operation))
        if operation.record_kind == RecordKind.DEPENDENCY:
            dependent_kind = operation.payload.get("dependent_kind")
            if dependent_kind:
                try:
                    domains.update(
                        domains_for_record_kind(RecordKind(str(dependent_kind)))
                    )
                except ValueError:
                    # Commit validation owns malformed payload rejection.
                    pass
    if patch.scope_ref.startswith(
        ("runtime:self-observation", "runtime:observation")
    ):
        domains.add(GenerationDomain.RUNTIME_OBSERVATION)
    for raw in patch.metadata.get("generation_domains", ()):
        domains.add(GenerationDomain(str(raw)))
    return frozenset(domains)


T = TypeVar("T")


class GenerationAwareCache(Generic[T]):
    """Cache entries are keyed by only the generations they depend upon."""

    def __init__(self, *, maximum_entries: int = 256) -> None:
        if maximum_entries < 1:
            raise ValueError("maximum_entries must be positive")
        self.maximum_entries = maximum_entries
        self._lock = RLock()
        self._items: MutableMapping[tuple[Any, ...], T] = {}

    @staticmethod
    def key(
        logical_key: Any,
        generation: ReadGeneration,
        domains: Iterable[GenerationDomain],
    ) -> tuple[Any, ...]:
        return (logical_key, generation.token_for(domains))

    def get(
        self,
        logical_key: Any,
        generation: ReadGeneration,
        domains: Iterable[GenerationDomain],
    ) -> T | None:
        with self._lock:
            return self._items.get(self.key(logical_key, generation, domains))

    def put(
        self,
        logical_key: Any,
        generation: ReadGeneration,
        domains: Iterable[GenerationDomain],
        value: T,
    ) -> None:
        key = self.key(logical_key, generation, domains)
        with self._lock:
            self._items[key] = value
            while len(self._items) > self.maximum_entries:
                self._items.pop(next(iter(self._items)))

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


__all__ = [
    "AUTHORITY_RECORD_KINDS",
    "AuthoritySnapshot",
    "GenerationAwareCache",
    "GenerationDomain",
    "ReadGeneration",
    "ReadGenerationChanged",
    "domains_for_record_kind",
    "infer_patch_domains",
]
