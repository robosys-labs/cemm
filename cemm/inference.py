"""Forward-chaining inference engine for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 457-503) with weakness #6 fix:
an inference timeout via threading.Timer so runaway rule chains cannot
hang the system indefinitely.
"""
from __future__ import annotations

import json
import threading

from cemm.config import Config
from cemm.store import Store
from cemm.model import Fact, isvar, isexist, stable, canonical


class InferenceTimeoutError(TimeoutError):
    """Raised when inference closure exceeds the configured timeout."""


class Inference:
    def __init__(self, store, config=None, authority_generation=None,
                 max_rounds=None, max_facts=None):
        self.store = store
        self.config = config or Config()
        self.authority_generation = authority_generation
        # Optional per-instance overrides (backward-compatible with v4 API).
        self._max_rounds = max_rounds
        self._max_facts = max_facts
        self.incomplete = False
        self.incomplete_reason = None
        self._timed_out = False

    def closure(self, extra=(), max_rounds=None, max_facts=None):
        max_rounds = max_rounds or self._max_rounds or self.config.inference_max_rounds
        max_facts = max_facts or self._max_facts or self.config.inference_max_facts
        self._timed_out = False
        self.incomplete = False
        self.incomplete_reason = None
        timer = threading.Timer(self.config.inference_timeout_seconds, self._timeout)
        timer.start()
        try:
            return self._closure_impl(extra, max_rounds, max_facts)
        finally:
            timer.cancel()

    def _timeout(self):
        self._timed_out = True

    def _closure_impl(self, extra, max_rounds, max_facts):
        s = self.store
        facts = list(s.base_facts()) + list(extra)
        bysig = {f.signature(): f for f in facts}
        byref = {f.ref: f for f in facts}
        cut = (
            self.authority_generation
            if self.authority_generation is not None
            else s.generation
        )
        rules = [
            dict(r)
            for r in s.db.execute(
                "SELECT * FROM rules WHERE rule_kind IN('definition','entailment') "
                "AND authority_status IN('reviewed','promoted') AND generation<=? "
                "ORDER BY rule_ref",
                (cut,),
            )
        ]
        for _ in range(max_rounds):
            if self._timed_out:
                raise InferenceTimeoutError(
                    f"inference exceeded {self.config.inference_timeout_seconds}s"
                )
            added = 0
            for r in rules:
                ants = json.loads(r["antecedent"])
                cons = json.loads(r["consequent"])
                for env, parents in self._matches(ants, list(bysig.values())):
                    ex = {}
                    parent_refs = tuple(sorted(x.ref for x in parents))
                    for c in cons:
                        args = {
                            k: self._inst(v, env, ex, r["rule_ref"], parent_refs)
                            for k, v in c.get("args", {}).items()
                        }
                        st = c.get("stance", "support")
                        ref = stable(
                            "derived", r["rule_ref"], parent_refs, c.get("operator"), args, st
                        )
                        f = Fact(
                            ref,
                            c["operator"],
                            args,
                            st,
                            min([x.confidence for x in parents] + [1.0])
                            * float(r["confidence"]),
                            True,
                            {"rule_ref": r["rule_ref"], "parents": parent_refs},
                        )
                        if f.signature() not in bysig:
                            bysig[f.signature()] = f
                            byref[f.ref] = f
                            added += 1
                        if len(bysig) >= max_facts:
                            self.incomplete = True
                            self.incomplete_reason = "max_facts"
                            return list(bysig.values()), byref
            if not added:
                break
        else:
            self.incomplete = True
            self.incomplete_reason = "max_rounds"
        return list(bysig.values()), byref

    def _matches(self, clauses, facts):
        states = [({}, [])]
        for c in clauses:
            nxt = []
            for env, pars in states:
                for f in facts:
                    e = dict(env)
                    if self._unify_clause(c, f, e):
                        nxt.append((e, pars + [f]))
            states = nxt
            if not states:
                break
        return states

    def _unify_clause(self, c, f, env):
        if c.get("stance", "support") != f.stance or not self._unify(
            c["operator"], f.operator, env
        ):
            return False
        return all(
            role in f.args and self._unify(pv, f.args[role], env)
            for role, pv in c.get("args", {}).items()
        )

    def _unify(self, p, v, env):
        if isvar(p):
            if p in env:
                return canonical(env[p]) == canonical(v)
            env[p] = v
            return True
        return canonical(p) == canonical(v)

    def _inst(self, v, env, ex, rule, parents):
        if isvar(v):
            return env[v]
        if isexist(v):
            if v not in ex:
                ex[v] = stable("existential", rule, parents, v)
            return ex[v]
        return v

    def match(self, pattern, facts):
        return [
            f
            for f in facts
            if self._unify_clause(
                {
                    "operator": pattern["operator"],
                    "args": pattern.get("args", {}),
                    "stance": pattern.get("stance", "support"),
                },
                f,
                {},
            )
        ]

    def explain(self, f, byref):
        if not f.derived:
            return {
                "fact_ref": f.ref,
                "source": "observed",
                "operator": f.operator,
                "args": f.args,
            }
        return {
            "fact_ref": f.ref,
            "source": "derived",
            "operator": f.operator,
            "args": f.args,
            "rule_ref": f.proof["rule_ref"],
            "parents": [
                self.explain(byref[x], byref)
                for x in f.proof["parents"]
                if x in byref
            ],
        }
