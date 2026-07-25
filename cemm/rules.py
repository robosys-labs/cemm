"""Rule learner for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 442-455). Hardcoded evidence
threshold replaced with Config value (weakness #4 fix).
"""
from __future__ import annotations

import hashlib

from cemm.config import Config
from cemm.store import Store
from cemm.interpreter import Interpreter


class RuleLearner:
    def __init__(self, s, interpreter, min_evidence=None, config=None):
        self.s = s
        self.i = interpreter
        self.config = config or Config()
        self.min_evidence = (
            min_evidence if min_evidence is not None else self.config.rule_evidence_threshold
        )

    def teach(self, text, participant_frame=None):
        local, anchors, uses = self.i.delex_for_rule(text, participant_frame)
        cands = self.i.codec.predict_rules(local, anchors, self.s, top_k=5)
        valid = []
        for r in cands:
            rule = {k: r[k] for k in ("rule_kind", "if", "then")}
            try:
                self.s.validate_rule(rule)
                valid.append((rule, float(r["score"])))
            except Exception:
                continue
        if not valid:
            return {"status": "frontier", "reason": "rule_induction_unsettled", "input": local}
        valid.sort(key=lambda x: x[1], reverse=True)
        rule, score = valid[0]
        margin = score - (valid[1][1] if len(valid) > 1 else score - 1)
        if len(valid) > 1 and margin < 0.05:
            return {
                "status": "frontier",
                "reason": "rule_induction_ambiguous",
                "candidates": [x[0] for x in valid[:3]],
            }
        with self.s.db:
            g = self.s.begin(
                "rule_learning:" + hashlib.sha256(text.encode()).hexdigest()[:12]
            )
            obs = self.s.add_observation(
                text, {"rule": rule}, self.i.lang, "teaching", g,
                occurrence_ref=f"rule:{g}",
            )
            ref, promoted = self.s.upsert_rule_candidate(
                rule, g, confidence=min(1, 0.75 + max(0, margin)), min_evidence=self.min_evidence
            )
            self.s.finish(g)
        return {
            "status": "promoted_rule" if promoted else "provisional_rule",
            "candidate_ref": ref,
            "rule": rule,
            "generation": g,
            "margin": margin,
            "observation_ref": obs,
        }
