"""Discourse obligations, goal arbitration, authorization, and adapter execution."""
from __future__ import annotations

import hashlib
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
    """Build and select exact discourse obligations; blocked goals never execute."""

    @staticmethod
    def _packet_qualifiers(act) -> dict[str, Any]:
        evidence = dict(getattr(act, "evidence", {}) or {})
        return dict(evidence.get("packet_qualifiers", {}) or {})

    def candidates(
        self,
        *,
        act,
        query_result=None,
        frontiers=(),
        transition_previews=(),
        capability_assessments=(),
        required_capability_refs=(),
        learning_probe=(),
    ):
        output: list[GoalCandidate] = []
        if query_result is not None:
            blockers = tuple(
                sorted(
                    set(query_result.unresolved_variables)
                    | set(query_result.blocking_frontiers)
                )
            )
            output.append(
                GoalCandidate(
                    stable("goal", "answer", query_result.query_ref),
                    "answer_query",
                    query_result.query_ref,
                    1.0,
                    {"query_result": query_result.as_dict()},
                    blockers,
                )
            )

        probes = tuple(dict(item) for item in learning_probe or ())
        if probes:
            if query_result is None:
                raise ValueError("learning probe requires the exact QueryResult")
            eligible = (
                query_result.status in {"unknown", "partial"}
                and not query_result.bindings
                and not query_result.blocking_frontiers
            )
            if eligible:
                exact = [
                    item
                    for item in probes
                    if item.get("query_ref") == query_result.query_ref
                    and isinstance(item.get("learning_plan"), Mapping)
                    and str(item.get("surface") or "").strip()
                ]
                if len(exact) != 1:
                    raise ValueError(
                        "unanswered learning query requires exactly one query-bound probe"
                    )
                probe = exact[0]
                output.append(
                    GoalCandidate(
                        stable(
                            "goal",
                            "request-learning-evidence",
                            query_result.query_ref,
                            probe.get("surface"),
                            dict(probe.get("learning_plan", {})).get("plan_ref"),
                        ),
                        "request_learning_evidence",
                        query_result.query_ref,
                        1.15,
                        {**probe, "query_result": query_result.as_dict()},
                        (),
                    )
                )

        for frontier in frontiers:
            blocks_answer = "answer" in set(frontier.blocks) or "interpretation" in set(frontier.blocks)
            output.append(
                GoalCandidate(
                    stable("goal", "clarify", frontier.frontier_ref),
                    "clarify",
                    frontier.frontier_ref,
                    1.1 if blocks_answer else 0.95,
                    {"frontier": frontier.as_dict()},
                    (),
                )
            )

        qualifiers = self._packet_qualifiers(act) if act is not None else {}
        discourse_operation = qualifiers.get("discourse_operation")
        if discourse_operation == "explain_surface_choice":
            decision_ref = qualifiers.get("surface_decision_ref")
            blockers = () if decision_ref else ("missing_surface_decision",)
            output.append(
                GoalCandidate(
                    stable("goal", "explain-surface-choice", getattr(act, "act_ref", None), decision_ref),
                    "explain_surface_choice",
                    getattr(act, "act_ref", "act:none"),
                    1.2,
                    {
                        "surface_decision_ref": decision_ref,
                        "surface_choice_a": qualifiers.get("surface_choice_a"),
                        "surface_choice_b": qualifiers.get("surface_choice_b"),
                    },
                    blockers,
                )
            )

        if getattr(act, "force", None) == "directive":
            required = tuple(sorted(set(str(ref) for ref in required_capability_refs)))
            by_ref = {item.capability_ref: item for item in capability_assessments}
            selected_assessments = tuple(by_ref[ref] for ref in required if ref in by_ref)
            missing = tuple(ref for ref in required if ref not in by_ref)
            unknown = tuple(
                item.capability_ref
                for item in selected_assessments
                if item.status == "unknown"
            )
            unavailable = tuple(
                item.capability_ref
                for item in selected_assessments
                if item.status == "unavailable"
            )
            degraded = tuple(
                item.capability_ref
                for item in selected_assessments
                if item.status == "degraded"
            )
            known_capability_scores = [
                float(item.score)
                for item in selected_assessments
                if item.score is not None
            ]
            capability_score = (
                min(known_capability_scores)
                if len(known_capability_scores) == len(selected_assessments) and not missing
                else None
            )
            blockers = tuple(
                sorted(
                    {blocker for item in selected_assessments for blocker in item.blockers}
                    | {f"missing_capability_assessment:{ref}" for ref in missing}
                    | {f"capability_unknown:{ref}" for ref in unknown}
                    | {f"capability_unavailable:{ref}" for ref in unavailable}
                    | {f"capability_degraded:{ref}" for ref in degraded}
                )
            )
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
                        "capability_score": capability_score,
                    },
                    blockers,
                )
            )

        if getattr(act, "force", None) == "claim":
            if qualifiers.get("claim_kind") == "attributed_open_predication":
                output.append(
                    GoalCandidate(
                        stable("goal", "ack-attributed", act.act_ref),
                        "acknowledge_attributed_claim",
                        act.act_ref,
                        0.8,
                        {
                            "act_ref": act.act_ref,
                            "subject_ref": qualifiers.get("subject_ref"),
                            "predicate_surface": qualifiers.get("predicate_surface"),
                            "epistemic_stance": qualifiers.get("epistemic_stance"),
                        },
                    )
                )
            else:
                output.append(
                    GoalCandidate(
                        stable("goal", "ack", act.act_ref),
                        "acknowledge_claim",
                        act.act_ref,
                        0.3,
                        {"act_ref": act.act_ref},
                    )
                )
        if getattr(act, "force", None) == "acknowledgment":
            output.append(
                GoalCandidate(
                    stable("goal", "acknowledgment", act.act_ref),
                    "acknowledge",
                    act.act_ref,
                    0.4,
                )
            )
        return tuple(output)

    @staticmethod
    def decide(candidates):
        ordered = sorted(candidates, key=lambda x: (-x.priority, x.goal_ref))
        selected = next((item for item in ordered if not item.blockers), None)
        rejected = tuple(item for item in ordered if selected is None or item.goal_ref != selected.goal_ref)
        reason = "highest_satisfied_priority" if selected is not None else "all_goals_blocked" if ordered else "no_goal"
        return GoalDecision(
            stable(
                "goal-decision",
                selected.goal_ref if selected else None,
                [(x.goal_ref, x.blockers) for x in rejected],
            ),
            selected,
            rejected,
            reason,
        )


class AdapterRegistry:
    """Only explicitly registered, semantically licensed adapters can produce effects."""

    def __init__(self):
        self._adapters: dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] = {}

    def register(self, adapter_ref: str, handler: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        if not adapter_ref.startswith("adapter:"):
            raise ValueError(f"adapter ref must be adapter:*: {adapter_ref}")
        if adapter_ref in self._adapters:
            raise ValueError(f"adapter already registered: {adapter_ref}")
        if not callable(handler):
            raise TypeError("adapter handler must be callable")
        self._adapters[adapter_ref] = handler

    def plan(self, goal: GoalCandidate, *, permission_scope=None, candidate_adapter_refs=()):
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
            return OperationResult(
                stable("operation-result", plan.plan_ref, "declined"),
                plan.plan_ref,
                "declined",
                {"reason": plan.reason},
                now(),
            )
        try:
            output = dict(self._adapters[plan.adapter_ref](plan.request))
            status = "succeeded"
        except Exception as exc:  # adapter failures become bounded operation evidence
            digest = hashlib.sha256(str(exc).encode("utf-8", "replace")).hexdigest()[:16]
            output = {"error_type": type(exc).__name__, "error_digest": digest}
            status = "failed"
        return OperationResult(
            stable("operation-result", plan.plan_ref, status, output),
            plan.plan_ref,
            status,
            output,
            now(),
        )
