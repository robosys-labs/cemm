from __future__ import annotations
from ..types.claim import Claim, ClaimStatus
from ..types.model import Model
from ..types.context_kernel import ContextKernel
from ..confidence.scoring import (
    score_claim, score_model, compute_relevance,
)
from ..confidence.log_odds import contradiction_weight
from ..types.permission import PermissionScope
from ..types.semantic_event_graph import SemanticEventGraph


class Ranker:
    def rank_claims(
        self,
        claims: list[Claim],
        kernel: ContextKernel,
        goal_keywords: list[str] | None = None,
        graph: SemanticEventGraph | None = None,
    ) -> list[tuple[Claim, float]]:
        scored: list[tuple[Claim, float]] = []
        now = kernel.time.now
        goal_terms = goal_keywords or []

        for claim in claims:
            permission_valid = self._claim_permitted(claim, kernel)
            if not permission_valid:
                continue
            recency = 1.0
            if claim.observed_at > 0:
                age_hours = (now - claim.observed_at) / 3600.0
                recency = max(0.01, 1.0 - (age_hours / 720.0))
            relevance = compute_relevance(
                claim_predicate=claim.predicate,
                goal_keywords=goal_terms,
            )
            frame_validity = 1.0
            if graph:
                for proc in graph.processes:
                    if proc.get("frame_key") == claim.predicate:
                        frame_validity = max(0.5, proc.get("confidence", 0.5))
                        break
                if claim.id in graph.claim_refs:
                    relevance = max(relevance, relevance * graph.confidence)
            contradiction_penalty = 0.0
            if claim.status == ClaimStatus.DISPUTED:
                contradiction_penalty = abs(contradiction_weight(0.5))
            s = score_claim(
                relevance=relevance,
                trust=claim.trust,
                confidence=claim.confidence,
                salience=claim.salience,
                recency=recency,
                permission_valid=permission_valid,
                frame_validity=frame_validity,
                contradiction_penalty=contradiction_penalty,
            )
            scored.append((claim, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: kernel.budget.max_ranked]

    def rank_models(
        self,
        models: list[Model],
        kernel: ContextKernel,
    ) -> list[tuple[Model, float]]:
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
            scored.append((model, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: kernel.budget.max_ranked]

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
