"""Semantic settler for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 386-414).

Neural likelihood proposes structure. Exact compilation clamps impossible
graphs. Recurrent inhibition sharpens competing exact candidates; it never
overrides exact semantic constraints. Hardcoded thresholds are replaced
with Config values (weakness #4 fix).
"""
from __future__ import annotations

import math

from cemm.config import Config
from cemm.compiler import ExactStructuredCompiler
from cemm.model import canonical


class SemanticSettler:
    def __init__(self, store, compiler: ExactStructuredCompiler, config: Config | None = None):
        self.s = store
        self.compiler = compiler
        self.config = config or Config()

    def settle(self, candidates, prefix="C0"):
        valid = []
        for c in candidates:
            try:
                p, news = self.compiler.compile(c.packet, prefix)
            except Exception:
                continue
            sig = canonical(p)
            valid.append(
                {
                    "packet": p,
                    "news": news,
                    "base": float(c.score),
                    "trace": c.trace,
                    "sig": sig,
                }
            )
        by = {}
        for x in valid:
            if x["sig"] not in by or x["base"] > by[x["sig"]]["base"]:
                by[x["sig"]] = x
        xs = list(by.values())
        if not xs:
            return None, {"status": "no_exact_candidate", "candidates": []}
        m = max(x["base"] for x in xs)
        for x in xs:
            x["energy"] = x["base"] - m + 0.35
        for _ in range(self.config.settler_rounds):
            z = sum(math.exp(x["energy"]) for x in xs)
            probs = [math.exp(x["energy"]) / z for x in xs]
            for i, x in enumerate(xs):
                x["energy"] = (x["base"] - m + 0.35) - 0.28 * (1 - probs[i])
        z = sum(math.exp(x["energy"]) for x in xs)
        for x in xs:
            x["posterior"] = math.exp(x["energy"]) / z
        xs.sort(key=lambda x: x["posterior"], reverse=True)
        top = xs[0]
        margin = top["posterior"] - (xs[1]["posterior"] if len(xs) > 1 else 0)
        settled = len(xs) == 1 or (
            top["posterior"] >= self.config.settler_posterior_threshold
            and margin >= self.config.settler_margin_threshold
        )
        trace = {
            "status": "settled" if settled else "ambiguous",
            "posterior": top["posterior"],
            "margin": margin,
            "candidates": [
                {
                    "posterior": round(x["posterior"], 4),
                    "packet": x["packet"],
                    "neural": x["trace"],
                }
                for x in xs[:5]
            ],
        }
        return (top["packet"], top["news"]) if trace["status"] == "settled" else None, trace
