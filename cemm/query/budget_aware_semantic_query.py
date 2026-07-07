"""Budget-aware wrapper for SemanticQueryEngine.

This module keeps the boundary clean: it changes query *effort* and evidence
binding limits, never final wording, framing, or response style.
"""

from __future__ import annotations

import copy
from typing import Any

from cemm.response.types import BudgetDecision, BudgetFrame
from .binding_limiter import AnswerBindingLimiter
from .frame_selector import QueryFrameSelector
from .query_budget_policy import QueryBudgetPolicyBuilder
from .types import QueryBudgetPolicy, QueryBudgetTrace


class BudgetAwareSemanticQueryEngine:
    def __init__(self, base_engine: Any) -> None:
        self._base = base_engine
        self._policy_builder = QueryBudgetPolicyBuilder()
        self._frame_selector = QueryFrameSelector()
        self._binding_limiter = AnswerBindingLimiter()

    def build_query(
        self,
        obligation: Any,
        relation_frames: list[Any],
        program: Any | None = None,
        uol_graph: Any | None = None,
        *,
        budget_decision: BudgetDecision | None = None,
        budget_frame: BudgetFrame | None = None,
    ) -> Any:
        query = self._base.build_query(obligation, relation_frames, program, uol_graph)
        policy = self._policy(obligation, budget_decision, budget_frame)
        return self._apply_policy_to_query(query, policy)

    def execute(
        self,
        query: Any,
        relation_frames: list[Any],
        *,
        budget_decision: BudgetDecision | None = None,
        budget_frame: BudgetFrame | None = None,
        evidence_policy: str = "",
    ) -> tuple[Any, QueryBudgetTrace]:
        policy = self._policy(None, budget_decision, budget_frame, evidence_policy=evidence_policy)
        query = self._apply_policy_to_query(query, policy)
        selected_frames = self._frame_selector.select(query=query, relation_frames=relation_frames, policy=policy)
        binding = self._base.execute(query, selected_frames)
        input_fill_count = len(getattr(binding, "slot_fills", []) or [])
        limited = self._binding_limiter.limit(binding, policy)
        trace = QueryBudgetTrace(
            policy=policy,
            input_frame_count=len(relation_frames or []),
            selected_frame_count=len(selected_frames),
            input_fill_count=input_fill_count,
            selected_fill_count=len(getattr(limited, "slot_fills", []) or []),
            reasons=self._trace_reasons(policy),
        )
        return limited, trace

    def run(
        self,
        obligation: Any,
        relation_frames: list[Any],
        program: Any | None = None,
        uol_graph: Any | None = None,
        *,
        budget_decision: BudgetDecision | None = None,
        budget_frame: BudgetFrame | None = None,
    ) -> tuple[Any, Any, Any, QueryBudgetTrace]:
        query = self.build_query(
            obligation,
            relation_frames,
            program,
            uol_graph,
            budget_decision=budget_decision,
            budget_frame=budget_frame,
        )
        binding, trace = self.execute(
            query,
            relation_frames,
            budget_decision=budget_decision,
            budget_frame=budget_frame,
            evidence_policy=getattr(obligation, "evidence_policy", ""),
        )
        return query, binding, None, trace

    def _policy(
        self,
        obligation: Any | None,
        budget_decision: BudgetDecision | None,
        budget_frame: BudgetFrame | None,
        *,
        evidence_policy: str = "",
    ) -> QueryBudgetPolicy:
        return self._policy_builder.build(
            budget_decision=budget_decision,
            budget_frame=budget_frame,
            evidence_policy=evidence_policy or getattr(obligation, "evidence_policy", ""),
        )

    @staticmethod
    def _apply_policy_to_query(query: Any, policy: QueryBudgetPolicy) -> Any:
        q = copy.copy(query)
        for key, value in {
            "allow_inverse": bool(getattr(query, "allow_inverse", True) and policy.allow_inverse),
            "allow_inheritance": bool(getattr(query, "allow_inheritance", True) and policy.allow_inheritance),
            "allow_composition": bool(getattr(query, "allow_composition", False) and policy.allow_composition),
            "max_results": policy.max_results,
            "max_inference_depth": policy.max_inference_depth,
            "stop_on_first_sufficient": policy.stop_on_first_sufficient,
            "min_confidence": policy.min_confidence,
        }.items():
            try:
                setattr(q, key, value)
            except Exception:
                pass
        return q

    @staticmethod
    def _trace_reasons(policy: QueryBudgetPolicy) -> list[str]:
        reasons: list[str] = []
        if policy.stop_on_first_sufficient:
            reasons.append("stop_on_first_sufficient")
        if not policy.allow_inverse:
            reasons.append("inverse_disabled")
        if not policy.allow_inheritance:
            reasons.append("inheritance_disabled")
        if policy.require_evidence_refs:
            reasons.append("evidence_required")
        return reasons
