"""Discourse obligations, goal arbitration, authorization and adapter execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from cemm.model import now, stable


@dataclass(frozen=True)
class GoalCandidate:
    goal_ref: str
    kind: str
    source_ref: str
    priority: float
    payload: Mapping[str, Any] = field(default_factory=dict)
    blockers: tuple[str, ...] = ()

    def as_dict(self):
        return {
            "goal_ref": self.goal_ref,
            "kind": self.kind,
            "source_ref": self.source_ref,
            "priority": self.priority,
            "payload": dict(self.payload),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class GoalDecision:
    decision_ref: str
    selected: GoalCandidate | None
    rejected: tuple[GoalCandidate, ...]
    reason: str

    def as_dict(self):
        return {
            "decision_ref": self.decision_ref,
            "selected": self.selected.as_dict() if self.selected else None,
            "rejected": [x.as_dict() for x in self.rejected],
            "reason": self.reason,
        }


@dataclass(frozen=True)
class OperationPlan:
    plan_ref: str
    goal_ref: str
    adapter_ref: str | None
    request: Mapping[str, Any]
    authorized: bool
    reason: str
    idempotency_key: str

    def as_dict(self):
        return {
            "plan_ref": self.plan_ref,
            "goal_ref": self.goal_ref,
            "adapter_ref": self.adapter_ref,
            "request": dict(self.request),
            "authorized": self.authorized,
            "reason": self.reason,
            "idempotency_key": self.idempotency_key,
        }


@dataclass(frozen=True)
class OperationResult:
    result_ref: str
    plan_ref: str
    status: str
    output: Mapping[str, Any]
    observed_at: str

    def as_dict(self):
        return {
            "result_ref": self.result_ref,
            "plan_ref": self.plan_ref,
            "status": self.status,
            "output": dict(self.output),
            "observed_at": self.observed_at,
        }


class GoalArbiter:
    def candidates(
        self,
        *,
        act,
        query_result=None,
        frontiers=(),
        transition_previews=(),
        capability_assessments=(),
        required_capability_refs=(),
    ):
        output = []
        if query_result is not None:
            blockers = tuple(query_result.unresolved_variables)
            output.append(GoalCandidate(stable("goal", "answer", query_result.query_ref), "answer_query", query_result.query_ref, 1.0, {"query_result": query_result.as_dict()}, blockers))
        for frontier in frontiers:
            output.append(GoalCandidate(stable("goal", "clarify", frontier.frontier_ref), "clarify", frontier.frontier_ref, 0.95, {"frontier": frontier.as_dict()}, frontier.blocks))
        if getattr(act, "force", None) == "directive":
            required = tuple(sorted(set(str(ref) for ref in required_capability_refs)))
            by_ref = {item.capability_ref: item for item in capability_assessments}
            selected_assessments = tuple(by_ref[ref] for ref in required if ref in by_ref)
            missing = tuple(ref for ref in required if ref not in by_ref)
            capability = min((item.score for item in selected_assessments), default=1.0 if not required else 0.0)
            blockers = tuple(sorted(
                {blocker for item in selected_assessments for blocker in item.blockers}
                | {f"missing_capability_assessment:{ref}" for ref in missing}
                | {f"capability_unavailable:{item.capability_ref}" for item in selected_assessments if item.score < 0.5}
            ))
            output.append(
                GoalCandidate(
                    stable("goal", "directive", act.act_ref),
                    "handle_directive",
                    act.act_ref,
                    0.9,
                    {
                        "act": act.as_dict(),
                        "transition_previews": [x.as_dict() for x in transition_previews],
                        "required_capability_refs": list(required),
                        "capability_score": capability,
                    },
                    blockers,
                )
            )
        if getattr(act, "force", None) == "claim":
            output.append(GoalCandidate(stable("goal", "ack", act.act_ref), "acknowledge_claim", act.act_ref, 0.3, {"act_ref": act.act_ref}))
        if getattr(act, "force", None) == "acknowledgment":
            output.append(GoalCandidate(stable("goal", "acknowledgment", act.act_ref), "acknowledge", act.act_ref, 0.4))
        return tuple(output)

    @staticmethod
    def decide(candidates):
        ordered = sorted(candidates, key=lambda x: (-x.priority, x.goal_ref))
        satisfied = next((item for item in ordered if not item.blockers or item.kind == "clarify"), None)
        selected = satisfied or (ordered[0] if ordered else None)
        rejected = tuple(item for item in ordered if selected is None or item.goal_ref != selected.goal_ref)
        reason = (
            "highest_satisfied_priority"
            if satisfied is not None
            else "highest_priority_blocked"
            if selected is not None
            else "no_goal"
        )
        return GoalDecision(stable("goal-decision", selected.goal_ref if selected else None, [x.goal_ref for x in rejected]), selected, rejected, reason)


class AdapterRegistry:
    """Only explicitly registered adapters can produce effects."""

    def __init__(self):
        self._adapters: dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] = {}

    def register(self, adapter_ref: str, handler: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        if adapter_ref in self._adapters:
            raise ValueError(f"adapter already registered: {adapter_ref}")
        self._adapters[adapter_ref] = handler

    def plan(self, goal: GoalCandidate, *, permission_scope=None, candidate_adapter_refs=()):
        """Plan only through adapters licensed by semantic authority and registered at runtime."""
        candidates = tuple(sorted(set(str(x) for x in candidate_adapter_refs if x)))
        adapter_ref = next((ref for ref in candidates if ref in self._adapters), None)
        goal_blockers = tuple(goal.blockers if goal else ())
        authorized = bool(adapter_ref and permission_scope and not goal_blockers)
        if authorized:
            reason = "authorized"
        elif goal_blockers:
            reason = "goal_blocked:" + ",".join(goal_blockers)
        elif not candidates:
            reason = "no_semantically_authorized_adapter"
        elif adapter_ref is None:
            reason = "authorized_adapter_not_registered"
        else:
            reason = "permission_missing"
        request = dict(goal.payload if goal else {})
        request["candidate_adapter_refs"] = list(candidates)
        key = stable("effect-key", goal.goal_ref if goal else None, adapter_ref, request)
        return OperationPlan(
            stable("operation-plan", goal.goal_ref if goal else None, adapter_ref, request),
            goal.goal_ref if goal else "goal:none",
            adapter_ref,
            request,
            authorized,
            reason,
            key,
        )

    @staticmethod
    def not_executed(plan: OperationPlan, *, reason: str):
        return OperationResult(
            stable("operation-result", plan.plan_ref, "not_executed", reason),
            plan.plan_ref,
            "not_executed",
            {"reason": reason, "authorized_plan": plan.authorized},
            now(),
        )

    def execute(self, plan: OperationPlan):
        if not plan.authorized or not plan.adapter_ref:
            return OperationResult(stable("operation-result", plan.plan_ref, "declined"), plan.plan_ref, "declined", {"reason": plan.reason}, now())
        try:
            output = dict(self._adapters[plan.adapter_ref](plan.request))
            status = "succeeded"
        except Exception as exc:  # adapter boundary; captured as operation evidence
            output = {"error": str(exc)}
            status = "failed"
        return OperationResult(stable("operation-result", plan.plan_ref, status, output), plan.plan_ref, status, output, now())
