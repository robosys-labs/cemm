"""Structured rule learner with explicit participant-frame grounding."""
from __future__ import annotations

import hashlib

from cemm.config import Config


class RuleLearner:
    def __init__(self, store, interpreter, min_evidence=None, config=None):
        self.s = store
        self.i = interpreter
        self.config = config or Config()
        self.min_evidence = (
            min_evidence
            if min_evidence is not None
            else self.config.rule_evidence_threshold
        )

    def teach(self, text, participant_frame, *, cycle_ref, expected_world_revision):
        local, anchors, _uses = self.i.delex_for_rule(text, participant_frame)
        candidates = self.i.codec.predict_rules(local, anchors, self.s, top_k=5)
        valid = []
        for candidate in candidates:
            rule = {key: candidate[key] for key in ("rule_kind", "if", "then")}
            try:
                self.s.validate_rule(rule)
                valid.append((rule, float(candidate["score"])))
            except Exception:
                continue
        if not valid:
            return {
                "status": "frontier",
                "reason": "rule_induction_unsettled",
                "input": local,
            }
        valid.sort(key=lambda item: item[1], reverse=True)
        rule, score = valid[0]
        margin = score - (valid[1][1] if len(valid) > 1 else score - 1)
        if len(valid) > 1 and margin < 0.05:
            return {
                "status": "frontier",
                "reason": "rule_induction_ambiguous",
                "candidates": [item[0] for item in valid[:3]],
            }
        with self.s.db:
            generation = self.s.begin(
                "rule_learning:" + hashlib.sha256(text.encode()).hexdigest()[:12],
                expected_world_revision=expected_world_revision,
            )
            observation = self.s.add_observation(
                text,
                {"rule": rule},
                self.i.lang,
                "teaching",
                generation,
                occurrence_ref=f"rule:{generation}",
            )
            ref, promoted = self.s.upsert_rule_candidate(
                rule,
                generation,
                confidence=min(1, 0.75 + max(0, margin)),
                min_evidence=self.min_evidence,
            )
            receipt = self.s.finish(
                generation,
                cycle_ref=cycle_ref,
                stage=13,
                expected_world_revision=expected_world_revision,
                world_delta=bool(promoted),
                observation_delta=True,
                payload={"candidate_ref": ref, "promoted": promoted, "rule": rule},
            )
        return {
            "status": "promoted_rule" if promoted else "provisional_rule",
            "candidate_ref": ref,
            "rule": rule,
            "generation": generation,
            "margin": margin,
            "observation_ref": observation,
            "commit_receipt": receipt,
        }
