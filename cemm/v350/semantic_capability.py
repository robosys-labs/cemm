"""Authority-generation compiled semantic eligibility.

Semantic eligibility answers whether exact semantic authority may participate in a
cognitive operation.  It never authorizes durable mutation, execution, disclosure or
emission; those remain EffectAuthorizationBoundary concerns.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Iterable

from .learning.authority import record_supports_use
from .learning.model import PinnedRecord, PromotionDecisionKind, PromotionDecisionRecord
from .schema.model import (
    MeaningSchema, SchemaLifecycleStatus, UseDecision, UseOperation,
    schema_authorizes_use, semantic_fingerprint,
)
from .storage.model import DependencyEdge, RecordKind
from .runtime_generations import AUTHORITY_RECORD_KINDS


@dataclass(frozen=True, slots=True)
class CompiledSemanticCapability:
    capability_ref: str
    record_pin: PinnedRecord
    operation: UseOperation
    eligible: bool
    use_decision: UseDecision
    authority_generation: int
    authority_fingerprint: str
    dependency_pins: tuple[PinnedRecord, ...] = ()
    authorization_pins: tuple[PinnedRecord, ...] = ()
    proof_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise ValueError("compiled semantic capability requires exact authority generation")
        for values, label in (
            (self.dependency_pins, "dependency pins"),
            (self.authorization_pins, "authorization pins"),
            (self.proof_refs, "proof refs"),
            (self.reason_refs, "reason refs"),
        ):
            keys = tuple(getattr(x, "key", x) for x in values)
            if len(keys) != len(set(keys)):
                raise ValueError(f"duplicate compiled capability {label}")


class SemanticCapabilityError(RuntimeError):
    pass


class CompiledSemanticCapabilityRegistry:
    """Compile eligibility once per exact authority generation and cache the result."""

    def __init__(self, store) -> None:
        self.__store = store
        self._lock = RLock()
        self._generation_key: tuple[int, str] | None = None
        self._capabilities: dict[tuple, CompiledSemanticCapability] = {}
        self._records_for_use: dict[tuple[RecordKind, UseOperation], tuple] = {}
        self._promotion_edges: dict[tuple[RecordKind, str, int], tuple[DependencyEdge, ...]] = {}
        self._effective_authority: dict[tuple[RecordKind, str], tuple[int, str] | None] = {}

    def __getattr__(self, name):
        # Capability compilation is not a mutable-store capability.
        if name in {"store", "base_store", "_store"} or name.startswith("_"):
            raise AttributeError(name)
        raise AttributeError(name)

    @staticmethod
    def _pin(stored) -> PinnedRecord:
        return PinnedRecord(
            stored.record_kind, stored.record_ref, stored.revision,
            stored.record_fingerprint,
        )

    def _ensure_generation(self) -> tuple[int, str]:
        authority = self.__store.current_authority_snapshot()
        key = (authority.generation, authority.authority_fingerprint)
        with self._lock:
            if key == self._generation_key:
                return key
            self._generation_key = key
            self._capabilities.clear()
            self._records_for_use.clear()
            self._promotion_edges = self._compile_promotion_index()
            self._effective_authority = self._compile_effective_authority_index()
        return key

    @staticmethod
    def _record_active(record) -> bool:
        lifecycle = getattr(record, "lifecycle_status", None)
        if lifecycle is not None:
            return getattr(lifecycle, "value", lifecycle) == "active"
        if hasattr(record, "active"):
            return bool(getattr(record, "active"))
        if hasattr(record, "executable"):
            return bool(getattr(record, "executable"))
        return True

    def _compile_effective_authority_index(self) -> dict[tuple[RecordKind, str], tuple[int, str] | None]:
        result: dict[tuple[RecordKind, str], tuple[int, str] | None] = {}
        for kind in sorted(AUTHORITY_RECORD_KINDS, key=lambda item: item.value):
            groups: dict[str, list] = {}
            for stored in self.__store.records(kind, all_revisions=True):
                if self.__store.is_invalidated(kind, stored.record_ref, stored.revision):
                    continue
                if self._record_active(stored.payload):
                    groups.setdefault(stored.record_ref, []).append(stored)
            for ref, values in groups.items():
                superseded = {
                    int(value)
                    for item in values
                    for value in (getattr(item.payload, "supersedes_revision", None),)
                    if value is not None
                }
                effective = [item for item in values if item.revision not in superseded]
                if len(effective) == 1:
                    item = effective[0]
                    result[(kind, ref)] = (item.revision, item.record_fingerprint)
                else:
                    # Ambiguous active branches are never silently executable.
                    result[(kind, ref)] = None
        return result

    def _compile_promotion_index(self) -> dict[tuple[RecordKind, str, int], tuple[DependencyEdge, ...]]:
        by_dependent: dict[tuple[RecordKind, str, int], list[DependencyEdge]] = {}
        # This is authority-generation compilation work, never a per-token/per-use scan.
        for stored in self.__store.records(RecordKind.DEPENDENCY, all_revisions=True):
            if self.__store.is_invalidated(RecordKind.DEPENDENCY, stored.record_ref, stored.revision):
                continue
            edge = stored.payload
            if not isinstance(edge, DependencyEdge) or not edge.active:
                continue
            by_dependent.setdefault(
                (edge.dependent_kind, edge.dependent_ref, edge.dependent_revision), []
            ).append(edge)
        return {
            key: tuple(sorted(values, key=lambda e: (
                e.prerequisite_kind.value, e.prerequisite_ref, e.prerequisite_revision
            )))
            for key, values in by_dependent.items()
        }

    def compile(
        self, pin: PinnedRecord, operation: UseOperation, *, allow_provisional: bool = False
    ) -> CompiledSemanticCapability:
        generation, authority_fp = self._ensure_generation()
        cache_key = (*pin.key, pin.record_fingerprint, operation.value, bool(allow_provisional))
        with self._lock:
            cached = self._capabilities.get(cache_key)
        if cached is not None:
            return cached

        stored = self.__store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        if (
            stored is None
            or stored.record_fingerprint != pin.record_fingerprint
            or self.__store.is_invalidated(pin.record_kind, pin.record_ref, pin.revision)
        ):
            result = self._result(pin, operation, False, generation, authority_fp,
                                  reasons=("stale_missing_or_invalidated_exact_record",))
        elif not record_supports_use(pin.record_kind, stored.payload, operation):
            result = self._result(pin, operation, False, generation, authority_fp,
                                  reasons=("record_family_or_declared_use_incompatible",))
        elif pin.record_kind in AUTHORITY_RECORD_KINDS and self._effective_authority.get(
            (pin.record_kind, pin.record_ref)
        ) != (pin.revision, pin.record_fingerprint):
            result = self._result(
                pin, operation, False, generation, authority_fp,
                reasons=("record_not_singular_effective_authority",),
            )
        else:
            result = self._compile_stored(
                stored, operation, generation, authority_fp, allow_provisional=allow_provisional
            )

        with self._lock:
            self._capabilities[cache_key] = result
        return result

    def _compile_stored(
        self, stored, operation, generation, authority_fp, *, allow_provisional: bool
    ):
        record = stored.payload
        pin = self._pin(stored)
        lifecycle = getattr(record, "lifecycle_status", None)
        reasons: list[str] = []
        declared_decision = UseDecision.ALLOW

        if isinstance(record, MeaningSchema):
            declared_decision = record.use_profile.decision_for(operation)
            eligible = schema_authorizes_use(record, operation, provisional=allow_provisional)
            if not eligible:
                reasons.append("schema_use_profile_or_lifecycle_denied")
        else:
            if lifecycle is not None and lifecycle != SchemaLifecycleStatus.ACTIVE:
                eligible = False
                declared_decision = UseDecision.DENY
                reasons.append("record_not_active")
            else:
                declared = getattr(record, "use_decision", None)
                profile = getattr(record, "use_profile", None)
                if declared is not None:
                    declared_decision = declared if isinstance(declared, UseDecision) else UseDecision(str(declared))
                    eligible = declared_decision == UseDecision.ALLOW or (
                        allow_provisional and declared_decision == UseDecision.PROVISIONAL
                    )
                elif profile is not None and hasattr(profile, "decision_for"):
                    declared_decision = profile.decision_for(operation)
                    eligible = declared_decision == UseDecision.ALLOW or (
                        allow_provisional and declared_decision == UseDecision.PROVISIONAL
                    )
                elif profile is not None and hasattr(profile, "permits"):
                    try:
                        eligible = bool(profile.permits(operation, provisional=allow_provisional))
                    except TypeError:
                        eligible = bool(profile.permits(operation))
                    declared_decision = UseDecision.ALLOW if eligible else UseDecision.DENY
                else:
                    eligible = bool(getattr(record, "executable", True))
                    declared_decision = UseDecision.ALLOW if eligible else UseDecision.DENY
                if not eligible:
                    reasons.append("declared_use_not_allowed")

        edges = self._promotion_edges.get((stored.record_kind, stored.record_ref, stored.revision), ())
        dependency_pins: list[PinnedRecord] = []
        authorization_pins: list[PinnedRecord] = []
        proof_refs: list[str] = []
        source_candidate_pins: list[PinnedRecord] = []
        promotion_decisions: list[tuple[PinnedRecord, PromotionDecisionRecord]] = []

        for edge in edges:
            dep = self.__store.get_record(
                edge.prerequisite_kind, edge.prerequisite_ref, edge.prerequisite_revision
            )
            if (
                dep is None
                or dep.record_fingerprint != edge.prerequisite_fingerprint
                or self.__store.is_invalidated(
                    edge.prerequisite_kind, edge.prerequisite_ref, edge.prerequisite_revision
                )
            ):
                eligible = False
                reasons.append("stale_or_invalidated_compiled_dependency")
                continue
            dep_pin = self._pin(dep)
            dependency_pins.append(dep_pin)
            if edge.dependency_kind == "promotion_source_candidate":
                source_candidate_pins.append(dep_pin)
            if edge.prerequisite_kind == RecordKind.PROMOTION_DECISION:
                decision = dep.payload
                if not isinstance(decision, PromotionDecisionRecord) or decision.decision != PromotionDecisionKind.PROMOTE:
                    eligible = False
                    reasons.append("promotion_decision_not_promote")
                    continue
                promotion_decisions.append((dep_pin, decision))

        # Any mutable overlay record that participates in executable semantic authority
        # must be the exact promoted revision produced from a pinned candidate. Merely
        # sharing ref/kind with a promotion decision is insufficient.
        has_promotion_lineage = bool(source_candidate_pins or promotion_decisions)
        if (
            stored.layer != "boot"
            and stored.record_kind in AUTHORITY_RECORD_KINDS
            and has_promotion_lineage
        ):
            if len(source_candidate_pins) != 1:
                eligible = False
                reasons.append("promoted_revision_missing_exact_source_candidate")
            if len(promotion_decisions) != 1:
                eligible = False
                reasons.append("promoted_revision_missing_singular_promotion_decision")
            if len(source_candidate_pins) == 1 and len(promotion_decisions) == 1:
                decision_pin, decision = promotion_decisions[0]
                source_pin = source_candidate_pins[0]
                grant = next((
                    grant for grant in decision.use_grants
                    if grant.operation == operation
                    and grant.candidate_pin == source_pin
                    and grant.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL}
                ), None)
                if grant is None:
                    eligible = False
                    reasons.append("promotion_missing_exact_candidate_use_grant")
                else:
                    authorization_pins.append(decision_pin)
                    proof_refs.extend((decision.decision_ref, *grant.competence_result_refs))
                    if grant.decision == UseDecision.PROVISIONAL:
                        declared_decision = UseDecision.PROVISIONAL
                        if not allow_provisional:
                            eligible = False
                            reasons.append("provisional_promotion_grant_not_executable_in_canonical_runtime")

        return self._result(
            pin, operation, eligible, generation, authority_fp,
            use_decision=declared_decision,
            dependencies=tuple(dependency_pins), authorizations=tuple(authorization_pins),
            proofs=tuple(proof_refs), reasons=tuple(sorted(set(reasons))),
        )

    @staticmethod
    def _result(pin, operation, eligible, generation, authority_fp, *,
                use_decision=None, dependencies=(), authorizations=(), proofs=(), reasons=()):
        return CompiledSemanticCapability(
            capability_ref="semantic-capability:" + semantic_fingerprint(
                "compiled-semantic-capability",
                (pin.key, pin.record_fingerprint, operation.value, generation, authority_fp,
                 tuple(p.key for p in dependencies), tuple(p.key for p in authorizations), eligible),
                24,
            ),
            record_pin=pin, operation=operation, eligible=eligible,
            use_decision=(use_decision if use_decision is not None else (UseDecision.ALLOW if eligible else UseDecision.DENY)),
            authority_generation=generation, authority_fingerprint=authority_fp,
            dependency_pins=tuple(dependencies), authorization_pins=tuple(authorizations),
            proof_refs=tuple(proofs), reason_refs=tuple(reasons),
        )

    def require(
        self, pin: PinnedRecord, operation: UseOperation, *, allow_provisional: bool = False
    ) -> CompiledSemanticCapability:
        capability = self.compile(pin, operation, allow_provisional=allow_provisional)
        if not capability.eligible:
            raise SemanticCapabilityError(
                f"semantic capability denied {pin.key} for {operation.value}: "
                + ",".join(capability.reason_refs)
            )
        return capability

    def records_for_use(self, kind: RecordKind, operation: UseOperation):
        self._ensure_generation()
        key = (kind, operation)
        with self._lock:
            cached = self._records_for_use.get(key)
        if cached is not None:
            return cached
        records = []
        for stored in self.__store.records(kind, all_revisions=True):
            if self.__store.is_invalidated(kind, stored.record_ref, stored.revision):
                continue
            pin = self._pin(stored)
            if self.compile(pin, operation).eligible:
                records.append(stored)
        result = tuple(sorted(records, key=lambda x: (x.record_ref, x.revision)))
        with self._lock:
            self._records_for_use[key] = result
        return result


__all__ = [
    "CompiledSemanticCapability", "CompiledSemanticCapabilityRegistry",
    "SemanticCapabilityError",
]
