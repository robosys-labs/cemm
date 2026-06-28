from __future__ import annotations
from ..store.entity_store import EntityStore
from ..types.context_kernel import ContextKernel
from ..types.entity import Entity, EntityType


class EntityResolver:
    def __init__(self, entity_store: EntityStore) -> None:
        self._store = entity_store

    def resolve_by_name(self, name: str, kernel: ContextKernel) -> list[Entity]:
        return self._store.find_by_name(name)

    def resolve_by_alias(self, alias: str, kernel: ContextKernel) -> list[Entity]:
        return self._store.find_by_alias(alias)

    def resolve_or_create(
        self,
        name: str,
        entity_type: EntityType,
        signal_id: str,
        kernel: ContextKernel,
    ) -> Entity:
        matches = self.resolve_by_name(name, kernel)
        for m in matches:
            if m.type == entity_type:
                return m
        matches_by_alias = self.resolve_by_alias(name, kernel)
        for m in matches_by_alias:
            if m.type == entity_type:
                return m
        import time, uuid
        entity = Entity(
            id=uuid.uuid4().hex[:16],
            type=entity_type,
            name=name,
            aliases=[name.lower()],
            confidence=0.7,
            created_from_signal_id=signal_id,
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._store.put(entity)
        return entity

    def resolve_self(self, kernel: ContextKernel) -> Entity | None:
        if kernel.self_state is None:
            return None
        matches = self._store.find_by_name(kernel.self_state.name)
        for m in matches:
            if m.type == EntityType.SYSTEM:
                return m
        return None
