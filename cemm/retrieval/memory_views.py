from __future__ import annotations
from ..store.store import Store
from ..types.claim import Claim
from ..types.model import Model, ModelKind
from ..types.signal import Signal, SignalKind
from ..types.context_kernel import ContextKernel


class MemoryViews:
    def __init__(self, store: Store) -> None:
        self._store = store

    def working_memory(self, kernel: ContextKernel) -> dict:
        return {
            "signals": [self._store.signals.get(sid) for sid in kernel.memory.working_signal_ids if sid],
            "entities": [self._store.entities.get(eid) for eid in kernel.memory.working_entity_ids if eid],
            "claims": [self._store.claims.get(cid) for cid in kernel.memory.working_claim_ids if cid],
        }

    def semantic_memory(self, subject_id: str, predicate: str | None = None, limit: int = 50) -> list[Claim]:
        return self._store.claims.find_by_subject(subject_id, predicate, limit)

    def episodic_memory(self, source_id: str, limit: int = 50) -> list[Signal]:
        return self._store.signals.list_by_source(source_id, limit)

    def causal_memory(self, kind: str = "causal_rule", status: str = "active") -> list[Model]:
        return self._store.models.find_by_kind(kind, status)

    def procedural_memory(self, operator_model_id: str | None = None, limit: int = 50) -> list:
        if operator_model_id:
            return self._store.actions.list_by_operator(operator_model_id, limit=limit)
        return self._store.actions.recent(limit)

    def registry_memory(self, kind: str | None = None, status: str | None = None) -> list[Model]:
        if kind:
            return self._store.models.find_by_kind(kind, status)
        return self._store.models.find_by_kind("predicate", "active")

    def uol_memory(self, atom_key: str | None = None, limit: int = 50) -> list[Model]:
        models = self._store.models.find_by_kind("uol_semantic", "active")
        if atom_key:
            models = [m for m in models if atom_key in m.name]
        return models[:limit]

    def frame_memory(self, frame_id: str, status: str | None = "active") -> list[Claim]:
        return self._store.claims.find_by_frame(frame_id, status)

    def self_memory(self, self_id: str) -> dict | None:
        state = self._store.self_store.get(self_id)
        if state is None:
            return None
        return {
            "state": state,
            "claims": [self._store.claims.get(cid) for cid in state.identity_claim_ids if cid],
        }

    def trust_memory(self, source_id: str | None = None, domain: str | None = None) -> list:
        if source_id and domain:
            entry = self._store.source_trust.get(source_id, domain)
            return [entry] if entry else []
        if source_id:
            return self._store.source_trust.list_by_source(source_id)
        if domain:
            return self._store.source_trust.list_by_domain(domain)
        return []

    def context_memory(self, context_id: str, kind: str | None = None, limit: int = 50) -> list[Signal]:
        return self._store.signals.list_by_context(context_id, kind, limit)

    def permission_memory(self, kernel: ContextKernel) -> dict:
        perm = kernel.permission
        return {
            "scope": perm.scope.value if perm.scope else "unknown",
            "retention": perm.retention.value if perm.retention else "unknown",
            "may_store": perm.may_store,
            "may_retrieve": perm.may_retrieve,
            "may_use": perm.may_use,
            "may_share": perm.may_share,
            "may_execute": perm.may_execute,
        }
