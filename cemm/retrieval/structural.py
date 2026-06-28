from __future__ import annotations
from dataclasses import dataclass, field
from ..store.store import Store
from ..types.claim import Claim, ClaimStatus
from ..types.model import Model, ModelKind, ModelStatus
from ..types.entity import Entity
from ..types.context_kernel import ContextKernel


@dataclass
class RetrievalQuery:
    subject_entity_id: str | None = None
    predicate: str | None = None
    object_entity_id: str | None = None
    domain: str | None = None
    source_id: str | None = None
    frame_id: str | None = None
    model_kind: str | None = None
    model_status: str | None = None
    registry_key: str | None = None
    limit: int = 64


@dataclass
class RetrievalResult:
    claims: list[Claim] = field(default_factory=list)
    models: list[Model] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    total_count: int = 0


class StructuralRetriever:
    def __init__(self, store: Store) -> None:
        self._store = store

    def retrieve(self, query: RetrievalQuery, kernel: ContextKernel | None = None) -> RetrievalResult:
        result = RetrievalResult()

        if query.subject_entity_id and query.predicate:
            result.claims = self._store.claims.find_by_subject(
                query.subject_entity_id, query.predicate, query.limit,
            )
        elif query.subject_entity_id:
            result.claims = self._store.claims.find_by_subject(
                query.subject_entity_id, limit=query.limit,
            )
        elif query.object_entity_id:
            result.claims = self._store.claims.find_by_object(
                query.object_entity_id, query.limit,
            )
        elif query.domain:
            result.claims = self._store.claims.find_by_domain(
                query.domain, query.source_id, query.limit,
            )
        elif query.frame_id:
            result.claims = self._store.claims.find_by_frame(
                query.frame_id, status="active", limit=query.limit,
            )
        else:
            result.claims = self._store.claims.find_active(query.limit)

        if query.model_kind:
            result.models = self._store.models.find_by_kind(
                query.model_kind, query.model_status, query.limit,
            )
        elif query.registry_key:
            m = self._store.models.find_by_registry_key(query.registry_key)
            if m:
                result.models = [m]

        if kernel:
            result.claims = [
                c for c in result.claims
                if c.status == ClaimStatus.ACTIVE
            ]

        result.total_count = len(result.claims) + len(result.models)
        return result

    def retrieve_for_kernel(self, kernel: ContextKernel) -> RetrievalResult:
        result = RetrievalResult()
        entity_ids = (
            kernel.world.active_entity_ids
            + kernel.conversation.active_entity_ids
            + kernel.memory.working_entity_ids
        )
        seen = set()
        for eid in entity_ids:
            if eid in seen:
                continue
            seen.add(eid)
            claims = self._store.claims.find_by_subject(eid, limit=kernel.budget.max_claims)
            result.claims.extend(c for c in claims if c.status == ClaimStatus.ACTIVE)

        model_ids = kernel.world.active_model_ids + kernel.memory.registry_model_ids
        for mid in set(model_ids):
            m = self._store.models.get(mid)
            if m:
                result.models.append(m)

        result.total_count = len(result.claims) + len(result.models)
        return result
