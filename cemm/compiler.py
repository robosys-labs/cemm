"""Exact structured compiler for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 346-384).

The compiler validates neural-proposed semantic packets against the exact
operator/role schema stored in the Store, renames existential placeholders,
and returns a normalized packet plus the list of new entities to mint.
"""
from __future__ import annotations

import json

from cemm.model import canonical
from cemm.store import Store


class ExactStructuredCompiler:
    def __init__(self, s: Store):
        self.s = s

    def _kind_ok(self, spec, v):
        exp = spec["filler_kind"]
        if exp == "state_value":
            if isinstance(v, dict) and "new" in v:
                return True
            if isinstance(v, dict) and ("literal" in v or "app" in v):
                return True
            return bool(isinstance(v, str) and self.s.atom(v))
        if isinstance(v, dict) and "new" in v:
            return exp in {None, "atom", v.get("kind")}
        if isinstance(v, dict) and "literal" in v:
            return bool(
                exp
                and exp.startswith("literal:")
                and v["literal"].get("type") == exp.split(":", 1)[1]
            )
        a = self.s.atom(v) if isinstance(v, str) else None
        return bool(a and (not exp or exp == "atom" or a["kind"] == exp))

    def _rename(self, v, prefix, map_):
        if isinstance(v, dict) and "new" in v:
            old = v["new"]
            if old not in map_:
                map_[old] = f"@X_{prefix}_{old.replace('@X_', '')}"
            return {"new": map_[old], "kind": v.get("kind", "entity")}
        return v

    def compile(self, packet, prefix="C0"):
        p = json.loads(canonical(packet))
        news = []
        ren = {}

        def one(a):
            op = a["operator"]
            specs = self.s.roles(op)
            if not specs:
                raise ValueError(f"unknown/non-executable operator:{op}")
            args = {
                r: self._rename(v, prefix, ren)
                for r, v in a.get("args", {}).items()
                if r in specs
            }
            if (
                op == "op:state"
                and "role:dimension" not in args
                and "role:value" in args
                and isinstance(args["role:value"], str)
            ):
                dim = self.s.infer_state_dimension(args["role:value"])
                if dim:
                    args["role:dimension"] = dim
            for r, sp in specs.items():
                if sp["required"] and r not in args:
                    raise ValueError(f"missing {op}:{r}")
            for r, v in args.items():
                if not self._kind_ok(specs[r], v):
                    raise ValueError(f"invalid filler {op}:{r}:{v}")
            if op == "op:state" and "role:dimension" in args and "role:value" in args:
                state_value = args["role:value"]
                if not (isinstance(state_value, dict) and "new" in state_value):
                    self.s.validate_state_value(
                        str(args["role:dimension"]), state_value
                    )
            return {"operator": op, "args": args, "stance": a.get("stance", "support")}

        apps = [one(x) for x in p.get("apps", [])]
        query = one(p["query"]) if p.get("query") else None
        describe = p.get("describe")
        if describe is not None:
            if not isinstance(describe, str) or not self.s.atom(describe):
                raise ValueError("invalid describe referent")
        for old, newtok in ren.items():
            # recover kind from all occurrences
            kind = None
            for a0 in list(p.get("apps", [])) + (
                [p["query"]] if p.get("query") else []
            ):
                for v in a0.get("args", {}).values():
                    if isinstance(v, dict) and v.get("new") == old:
                        kind = v.get("kind")
            news.append({"token": newtok, "kind": kind or "entity"})
        return {"apps": apps, "query": query, "describe": describe}, news
