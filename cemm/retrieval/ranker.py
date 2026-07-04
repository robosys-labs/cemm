from __future__ import annotations
import math
from typing import Any

from ..types.action import Action, ActionStatus
from ..types.claim import Claim, ClaimStatus
from ..types.model import Model
from ..types.context_kernel import ContextKernel
from ..confidence.scoring import (
    score_claim, score_model, compute_relevance,
)
from ..confidence.log_odds import contradiction_weight
from ..types.permission import PermissionScope
from ..store.store import Store


class Ranker:
    def rank_claims(
        self,
        claims: list[Claim],
        kernel: ContextKernel,
        goal_keywords: list[str] | None = None,
        graph: Any | None = None,
    ) -> list[tuple[Claim, float]]:
        scored: list[tuple[Claim, float]] = []
        now = kernel.time.now
        goal_terms = list(goal_keywords or [])
        if graph:
            for proc in graph.processes:
                fk = proc.get("frame_key", "")
                if fk and fk not in goal_terms:
                    goal_terms.append(fk)
            for ref in graph.entity_refs:
                name = ref.get("name", "")
                if name and name not in goal_terms:
                    goal_terms.append(name)
        # Keep short goal terms from swamping relevance
        goal_terms = [g for g in goal_terms if len(g) > 1 or g.isalnum()]

        for claim in claims:
            permission_valid = self._claim_permitted(claim, kernel)
            if not permission_valid:
                continue
            recency = 1.0
            if claim.observed_at > 0:
                age_hours = (now - claim.observed_at) / 3600.0
                recency = max(0.01, 1.0 - (age_hours / 720.0))
            entity_overlap = 0
            if graph:
                claim_entities = {claim.subject_entity_id, claim.object_entity_id}
                graph_entities = {ref.get("entity_id", "") for ref in graph.entity_refs}
                entity_overlap = len(claim_entities & graph_entities)
            relevance = compute_relevance(
                claim_predicate=claim.predicate,
                goal_keywords=goal_terms,
                entity_overlap=entity_overlap,
                total_goal_entities=max(1, len(graph.entity_refs)) if graph else 1,
            )
            frame_validity = 1.0
            if graph:
                for proc in graph.processes:
                    if proc.get("frame_key") == claim.predicate:
                        frame_validity = max(0.5, proc.get("confidence", 0.5))
                        break
                if claim.id in graph.claim_refs:
                    relevance = max(relevance, min(1.0, 0.7 + 0.3 * graph.confidence))
            contradiction_penalty = 0.0
            if claim.status == ClaimStatus.DISPUTED:
                contradiction_penalty = abs(contradiction_weight(0.5))
            semantic_compatibility_penalty = 0.0
            if graph:
                process_keys = {p.get("frame_key", "") for p in graph.processes}
                query_predicates = {p.get("frame_key", "") for p in graph.processes if p.get("frame_key", "").startswith("claim_")}
                query_predicates = {k.replace("claim_", "") for k in query_predicates}
                if process_keys & {"self_identity_query", "user_identity_query", "user_name_query"}:
                    if claim.predicate not in {"name", "preferred_name", "called", "known_as", "identity_name"}:
                        semantic_compatibility_penalty += 0.4
                elif process_keys & {"self_capability_query", "self_knowledge_query"}:
                    if claim.predicate not in {"capability", "can", "does", "function", "role"}:
                        semantic_compatibility_penalty += 0.4
                elif query_predicates and claim.predicate not in query_predicates:
                    semantic_compatibility_penalty += 0.2
                # Unknown lexeme / teaching frames should not retrieve claims at all.
                if process_keys & {"command_alias_teaching", "definition_teaching", "correction", "unknown_intent"}:
                    semantic_compatibility_penalty += 0.5
            s = score_claim(
                relevance=relevance,
                trust=claim.trust,
                confidence=claim.confidence,
                salience=claim.salience,
                recency=recency,
                permission_valid=permission_valid,
                frame_validity=frame_validity,
                contradiction_penalty=contradiction_penalty,
                semantic_compatibility_penalty=semantic_compatibility_penalty,
            )
            scored.append((claim, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: kernel.budget.max_ranked]

    def rank_models(
        self,
        models: list[Model],
        kernel: ContextKernel,
        store: Store | None = None,
    ) -> list[tuple[Model, float]]:
        latent_bonus = self._compute_latent_model_bonus(models, kernel, store)
        scored: list[tuple[Model, float]] = []
        for model in models:
            permission_valid = self._model_permitted(model, kernel)
            if not permission_valid:
                continue
            s = score_model(
                applicability=0.7 if model.registry_key else 0.4,
                trust=model.trust,
                confidence=model.confidence,
                utility=model.utility,
                permission_valid=permission_valid,
                cost_penalty=model.cost_estimate_ms / 1000.0,
                risk_penalty=model.risk * 2.0,
            )
            s += latent_bonus.get(model.id, 0.0)
            scored.append((model, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: kernel.budget.max_ranked]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _compute_latent_model_bonus(
        self,
        models: list[Model],
        kernel: ContextKernel,
        store: Store | None,
    ) -> dict[str, float]:
        """Return a small score bonus for models used in similar successful contexts.

        Looks at recent actions with stored typed latent snapshots and boosts a model
        if the historical context is similar to the current kernel.
        """
        bonuses: dict[str, float] = {}
        if store is None:
            return bonuses
        current_latents = self._kernel_latent_snapshot(kernel)
        if not current_latents:
            return bonuses
        recent_actions = store.actions.recent(50)
        model_ids = {m.id for m in models}
        for action in recent_actions:
            if action.status != ActionStatus.EXECUTED:
                continue
            if not action.trace or not action.trace.typed_latents:
                continue
            hist = self._flatten_latents(action.trace.typed_latents)
            if not hist:
                continue
            sim = self._cosine_similarity(current_latents, hist)
            if sim < 0.5:
                continue
            for mid in action.trace.selected_model_ids:
                if mid in model_ids:
                    bonuses[mid] = max(bonuses.get(mid, 0.0), sim * 0.1)
        return bonuses

    @staticmethod
    def _flatten_latents(typed_latents) -> list[float]:
        """Concatenate all typed latent vectors into a single vector."""
        vec: list[float] = []
        for field in ["entity", "process", "state", "claim", "model", "context", "self", "memory", "action", "answer"]:
            part = getattr(typed_latents, field, None)
            if part:
                vec.extend(part)
        return vec

    @staticmethod
    def _kernel_latent_snapshot(kernel: ContextKernel) -> list[float]:
        """Build a latent snapshot from the current kernel for similarity comparison."""
        from ..latent.encoder import LatentEncoder
        encoder = LatentEncoder(dim=64)
        parts: list[float] = []
        parts.extend(encoder.encode("entity", kernel.memory.working_entity_ids + kernel.world.active_entity_ids))
        parts.extend(encoder.encode("context", [kernel.id]))
        parts.extend(encoder.encode("self", [kernel.self_view.mode, str(round(kernel.self_view.uncertainty, 2))]))
        parts.extend(encoder.encode("memory", kernel.memory.working_claim_ids))
        return parts

    @staticmethod
    def _scope_permits(claim_scope: PermissionScope | None, kernel_scope: PermissionScope) -> bool:
        hierarchy = {
            PermissionScope.PUBLIC: 0,
            PermissionScope.USER_PRIVATE: 1,
            PermissionScope.SESSION_PRIVATE: 2,
            PermissionScope.SYSTEM_PRIVATE: 3,
        }
        claim_level = hierarchy.get(claim_scope, 0)
        kernel_level = hierarchy.get(kernel_scope, 0)
        return kernel_level >= claim_level

    @staticmethod
    def _claim_permitted(claim: Claim, kernel: ContextKernel) -> bool:
        if claim.permission is None:
            return True
        if not Ranker._scope_permits(claim.permission.scope, kernel.permission.scope):
            return False
        if claim.permission.scope == PermissionScope.USER_PRIVATE:
            return kernel.user.known
        if claim.permission.scope == PermissionScope.SESSION_PRIVATE:
            return bool(kernel.conversation.session_id)
        return True

    @staticmethod
    def _model_permitted(model: Model, kernel: ContextKernel) -> bool:
        if model.permission is None:
            return True
        if not Ranker._scope_permits(model.permission.scope, kernel.permission.scope):
            return False
        if model.permission.scope == PermissionScope.USER_PRIVATE:
            return kernel.user.known
        return True
