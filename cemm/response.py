"""Response planning and pointerization for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 558-595).

The ResponsePlanner maps a dialogue outcome (e.g. "answered", "clarify") to a
structured response goal by walking policy relations in the Store. Facts and
plans are then pointerized into a delexicalized semantic string with @A
placeholders so the PointerRealizer can render them in natural language.
"""
from __future__ import annotations

from cemm.store import Store
from cemm.model import Fact, stable, isvar, isexist


class ResponsePlanner:
    def __init__(self, s: Store):
        self.s = s

    def plan(self, outcome):
        result = self.s.symbol(f"result.{outcome}")
        goalrel = self.s.symbol("policy.response_goal_relation")
        goal = self.s.find_relation_object(result, goalrel)
        if not goal:
            raise ValueError(f"no response goal for {outcome}")
        valrel = self.s.symbol("policy.response_value_relation")
        value = self.s.find_relation_object(goal, valrel)
        if value:
            return {"goal": goal, "value": value, "facts": []}
        srel = self.s.symbol("policy.response_state_subject_relation")
        prel = self.s.symbol("policy.response_state_spec_relation")
        subject = self.s.find_relation_object(goal, srel)
        spec = self.s.find_relation_object(goal, prel)
        if not subject or not spec:
            raise ValueError(f"incomplete response plan for {goal}")
        dim = self.s.find_relation_object(spec, self.s.symbol("policy.state_dimension_relation"))
        val = self.s.find_relation_object(spec, self.s.symbol("policy.state_value_relation"))
        if not dim or not val:
            raise ValueError(f"incomplete state spec {spec}")
        return {
            "goal": goal,
            "facts": [
                Fact(
                    stable("planfact", goal, subject, dim, val),
                    "op:state",
                    {"role:subject": subject, "role:dimension": dim, "role:value": val},
                )
            ],
        }


def pointerize_fact(f: Fact):
    refs = []
    contexts = {}
    for role, v in f.args.items():
        if isinstance(v, str) and v not in refs:
            refs.append(v)
            contexts[v] = role
    refs.sort()
    mp = {r: f"@A{i}" for i, r in enumerate(refs)}
    parts = ["FACT", f.stance, f.operator]
    for r, v in sorted(f.args.items()):
        parts += [r, mp.get(v, str(v))]
    return " ".join(parts), {mp[r]: (r, contexts.get(r)) for r in refs}


def pointerize_plan(plan):
    refs = []

    def add(v):
        if isinstance(v, str) and v not in refs:
            refs.append(v)

    if plan.get("value"):
        add(plan["value"])
    for f in plan.get("facts", []):
        for v in f.args.values():
            add(v)
    refs.sort()
    mp = {r: f"@A{i}" for i, r in enumerate(refs)}
    contexts = {}
    if plan.get("value"):
        contexts[plan["value"]] = "response:value"
    for f in plan.get("facts", []):
        for role, v in f.args.items():
            contexts.setdefault(v, role)
    parts = ["PLAN", plan["goal"]]
    if plan.get("value"):
        parts += ["VALUE", mp[plan["value"]]]
    for f in plan.get("facts", []):
        parts += ["|", "FACT", f.stance, f.operator]
        for r, v in sorted(f.args.items()):
            parts += [r, mp.get(v, str(v))]
    return " ".join(parts), {mp[r]: (r, contexts.get(r)) for r in refs}
