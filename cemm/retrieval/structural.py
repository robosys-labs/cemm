from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
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

    @staticmethod
    def filter_frame_valid(claims: list[Claim], now: float) -> list[Claim]:
        filtered: list[Claim] = []
        for c in claims:
            if c.valid_from is not None and c.valid_from > now:
                continue
            if c.valid_until is not None and c.valid_until < now:
                continue
            filtered.append(c)
        return filtered

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
            result.claims = self.filter_frame_valid(result.claims, kernel.time.now)

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

        result.claims = self.filter_frame_valid(result.claims, kernel.time.now)
        result.total_count = len(result.claims) + len(result.models)
        return result

    def retrieve_for_graph(self, graph: Any, kernel: ContextKernel) -> RetrievalResult:
        result = RetrievalResult()
        seen = set()

        # Detect query-specific predicate constraints
        frame_keys = {p.get("frame_key", "") for p in graph.processes}
        _identity_predicates = {"name", "preferred_name", "called", "known_as", "identity_name"}
        _capability_predicates = {"capability", "can", "does", "function", "role"}
        constrain_predicates: set[str] | None = None
        if frame_keys & {"user_name_query", "user_identity_query", "self_identity_query"}:
            constrain_predicates = _identity_predicates
        elif frame_keys & {"self_capability_query", "self_knowledge_query"}:
            constrain_predicates = _capability_predicates
        # Teaching/alias frames are stored as lexeme models, not claims; skip claim retrieval.
        if frame_keys & {"command_alias_teaching", "definition_teaching", "correction"}:
            return result

        # Extract entity names/IDs from graph's entity_refs as retrieval queries
        for ref in graph.entity_refs:
            eid = ref.get("entity_id", "")
            if eid and eid not in seen:
                seen.add(eid)
                if constrain_predicates:
                    # Predicate-constrained retrieval: only get name-related claims
                    for pred in constrain_predicates:
                        claims = self._store.claims.find_by_subject(eid, pred, kernel.budget.max_claims)
                        result.claims.extend(c for c in claims if c.status == ClaimStatus.ACTIVE)
                else:
                    claims = self._store.claims.find_by_subject(eid, limit=kernel.budget.max_claims)
                    result.claims.extend(c for c in claims if c.status == ClaimStatus.ACTIVE)

        # Extract process frame_key values and use as frame_id queries
        for proc in graph.processes:
            frame_key = proc.get("frame_key", "")
            if frame_key:
                frame_query = RetrievalQuery(frame_id=frame_key)
                frame_result = self.retrieve(frame_query, kernel)
                for c in frame_result.claims:
                    if c.id not in seen:
                        result.claims.append(c)
                        seen.add(c.id)

        # Extract state_key values and use as domain queries
        for state in graph.states:
            state_key = state.get("state_key", "")
            if state_key:
                domain_query = RetrievalQuery(domain=state_key)
                domain_result = self.retrieve(domain_query, kernel)
                for c in domain_result.claims:
                    if c.id not in seen:
                        result.claims.append(c)
                        seen.add(c.id)

        result.claims = self.filter_frame_valid(result.claims, kernel.time.now)
        result.total_count = len(result.claims) + len(result.models)
        return result
