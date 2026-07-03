"""RetrievalExecutor - execute explicit RetrievalPlan objects.

RetrievalPlanner decides *what kind* of retrieval is needed. This executor makes
that plan operational. It prevents the old failure mode where every plan falls
back to broad kernel/graph retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..store.store import Store
from ..types.claim import Claim, ClaimStatus
from ..types.context_kernel import ContextKernel
from ..types.meaning_percept import RetrievalPlan
from ..types.model import ModelKind, ModelStatus
from ..types.semantic_event_graph import SemanticEventGraph
from .structural import RetrievalQuery, RetrievalResult, StructuralRetriever


@dataclass
class RetrievalExecutionTrace:
    """Trace for plan execution and training export."""

    mode: str
    queries: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    model_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class RetrievalExecutionResult:
    """Result plus trace."""

    result: RetrievalResult
    trace: RetrievalExecutionTrace


class RetrievalExecutor:
    """Execute RetrievalPlan against CEMM stores."""

    def __init__(self, store: Store) -> None:
        self._store = store
        self._structural = StructuralRetriever(store)

    def execute(
        self,
        plan: RetrievalPlan,
        kernel: ContextKernel,
        graph: SemanticEventGraph | None = None,
        lexeme_memory: Any | None = None,
    ) -> RetrievalExecutionResult:
        trace = RetrievalExecutionTrace(mode=plan.mode)
        result = RetrievalResult()

        if plan.mode in ("", "none"):
            trace.skipped.append("mode=none")
            return RetrievalExecutionResult(result=result, trace=trace)

        if plan.mode == "profile":
            self._retrieve_profile(plan, kernel, result, trace)
        elif plan.mode == "self_knowledge":
            self._retrieve_self_knowledge(plan, kernel, result, trace)
        elif plan.mode == "entity_memory":
            self._retrieve_entity_memory(plan, kernel, result, trace)
        elif plan.mode == "world_memory":
            self._retrieve_world_memory(plan, kernel, graph, result, trace)
        elif plan.mode == "lexeme_memory":
            self._retrieve_lexeme_memory(plan, lexeme_memory, result, trace)
        elif plan.mode == "procedure_model":
            self._retrieve_models(plan, [ModelKind.PROCEDURE.value], result, trace)
        elif plan.mode == "live_tool_required":
            self._retrieve_models(plan, [ModelKind.TOOL.value], result, trace)
        else:
            trace.skipped.append(f"unknown_mode:{plan.mode}")

        result.claims = self._dedupe_claims(self._filter_claims(result.claims, kernel))
        result.models = self._dedupe_models(result.models)
        result.total_count = len(result.claims) + len(result.models) + len(result.entities)
        trace.claim_ids = [c.id for c in result.claims]
        trace.model_ids = [m.id for m in result.models]
        trace.confidence = min(0.95, 0.5 + result.total_count * 0.05)
        return RetrievalExecutionResult(result=result, trace=trace)

    def _retrieve_profile(
        self,
        plan: RetrievalPlan,
        kernel: ContextKernel,
        result: RetrievalResult,
        trace: RetrievalExecutionTrace,
    ) -> None:
        predicates = plan.target_predicates or ["user.name", "user.alias", "name", "preferred_name"]
        for predicate in predicates:
            query = RetrievalQuery(subject_entity_id="user", predicate=predicate, limit=16)
            trace.queries.append(query.__dict__)
            result.claims.extend(self._structural.retrieve(query, kernel).claims)

    def _retrieve_self_knowledge(
        self,
        plan: RetrievalPlan,
        kernel: ContextKernel,
        result: RetrievalResult,
        trace: RetrievalExecutionTrace,
    ) -> None:
        self_id = getattr(kernel.self_view, "self_id", "") or "self_main"
        predicates = plan.target_predicates or [
            "answers_identity_as",
            "name",
            "is_a",
            "does",
            "capability",
            "knows_about",
            "limitation",
            "architecture",
            "purpose",
        ]
        for predicate in predicates:
            query = RetrievalQuery(subject_entity_id=self_id, predicate=predicate, limit=16)
            trace.queries.append(query.__dict__)
            result.claims.extend(self._structural.retrieve(query, kernel).claims)

    def _retrieve_entity_memory(
        self,
        plan: RetrievalPlan,
        kernel: ContextKernel,
        result: RetrievalResult,
        trace: RetrievalExecutionTrace,
    ) -> None:
        for entity_id in self._target_entities(plan, kernel):
            self._retrieve_entity_claims(entity_id, plan, kernel, result, trace)

    def _retrieve_world_memory(
        self,
        plan: RetrievalPlan,
        kernel: ContextKernel,
        graph: SemanticEventGraph | None,
        result: RetrievalResult,
        trace: RetrievalExecutionTrace,
    ) -> None:
        entity_ids = list(plan.target_entity_ids)
        if graph:
            for ref in graph.entity_refs:
                entity_id = ref.get("entity_id", "")
                if entity_id and entity_id not in entity_ids:
                    entity_ids.append(entity_id)
        if not entity_ids:
            trace.skipped.append("world_memory_without_target_entity")
            return
        for entity_id in entity_ids:
            self._retrieve_entity_claims(entity_id, plan, kernel, result, trace)

    def _retrieve_entity_claims(
        self,
        entity_id: str,
        plan: RetrievalPlan,
        kernel: ContextKernel,
        result: RetrievalResult,
        trace: RetrievalExecutionTrace,
    ) -> None:
        predicates = plan.target_predicates or [None]
        for predicate in predicates:
            query = RetrievalQuery(subject_entity_id=entity_id, predicate=predicate, limit=kernel.budget.max_claims)
            trace.queries.append(query.__dict__)
            result.claims.extend(self._structural.retrieve(query, kernel).claims)

    def _retrieve_lexeme_memory(
        self,
        plan: RetrievalPlan,
        lexeme_memory: Any | None,
        result: RetrievalResult,
        trace: RetrievalExecutionTrace,
    ) -> None:
        self._retrieve_models(
            plan,
            [ModelKind.UOL_SEMANTIC.value, ModelKind.PREDICATE.value, ModelKind.PROCESS.value],
            result,
            trace,
        )
        if lexeme_memory is None:
            trace.skipped.append("no_lexeme_memory_adapter")
            return
        trace.skipped.append("lexeme_memory_cache_not_queryable")

    def _retrieve_models(
        self,
        plan: RetrievalPlan,
        default_kinds: list[str],
        result: RetrievalResult,
        trace: RetrievalExecutionTrace,
    ) -> None:
        kinds = plan.target_model_kinds or default_kinds
        for kind in kinds:
            query = RetrievalQuery(model_kind=kind, model_status=ModelStatus.ACTIVE.value, limit=32)
            trace.queries.append(query.__dict__)
            result.models.extend(self._structural.retrieve(query).models)

    def _target_entities(self, plan: RetrievalPlan, kernel: ContextKernel) -> list[str]:
        ids = list(plan.target_entity_ids)
        for source in (
            getattr(kernel.world, "active_entity_ids", []),
            getattr(kernel.conversation, "active_entity_ids", []),
            getattr(kernel.memory, "working_entity_ids", []),
        ):
            for entity_id in source:
                if entity_id and entity_id not in ids:
                    ids.append(entity_id)
        return ids

    def _filter_claims(self, claims: Iterable[Claim], kernel: ContextKernel) -> list[Claim]:
        now = kernel.time.now
        filtered: list[Claim] = []
        for claim in claims:
            if claim.status != ClaimStatus.ACTIVE:
                continue
            if claim.valid_from is not None and claim.valid_from > now:
                continue
            if claim.valid_until is not None and claim.valid_until < now:
                continue
            filtered.append(claim)
        return filtered

    def _dedupe_claims(self, claims: Iterable[Claim]) -> list[Claim]:
        out: list[Claim] = []
        seen: set[str] = set()
        for claim in claims:
            if claim.id in seen:
                continue
            seen.add(claim.id)
            out.append(claim)
        return out

    def _dedupe_models(self, models: Iterable[Any]) -> list[Any]:
        out: list[Any] = []
        seen: set[str] = set()
        for model in models:
            model_id = getattr(model, "id", "")
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            out.append(model)
        return out
