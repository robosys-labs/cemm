"""Exact-clamped bounded semantic settling with explicit candidate receipts."""
from __future__ import annotations

import math
from typing import Any

from cemm.config import Config
from cemm.compiler import ExactStructuredCompiler
from cemm.model import canonical, stable
from cemm.semantic_coverage import CoverageIntegrityError, coverage_from_dict


class SemanticSettler:
    def __init__(
        self,
        store,
        compiler: ExactStructuredCompiler,
        config: Config | None = None,
    ):
        self.s = store
        self.compiler = compiler
        self.config = config or Config()

    _PROVENANCE_ONLY_PACKET_QUALIFIERS = frozenset({
        "construction_schema_ref",
        "coverage_ref",
        "construction_evidence_ref",
        "hypothesis_ref",
        "match_seed_ref",
    })

    @staticmethod
    def _candidate_ref(candidate: Any, index: int) -> str:
        trace = dict(getattr(candidate, "trace", {}) or {})
        return str(
            trace.get("construction_evidence_ref")
            or trace.get("candidate_ref")
            or stable("semantic-candidate", index, getattr(candidate, "packet", None), trace)
        )

    @classmethod
    def _semantic_signature(cls, packet: Any) -> str:
        """Return the executable meaning signature, excluding match provenance.

        Atomic construction provenance is required for audit and coverage checks,
        but it is not a semantic alternative. Multiple normalization or grounding
        hypotheses that compile to the same force/apps/query/directive must not
        divide posterior mass merely because their coverage receipts differ.
        Meaning-bearing qualifiers (query kind, learning operation, discourse
        operation, modality, etc.) remain part of the signature.
        """
        if not isinstance(packet, dict):
            return canonical(packet)
        material = dict(packet)
        qualifiers = dict(material.get("qualifiers", {}) or {})
        for key in cls._PROVENANCE_ONLY_PACKET_QUALIFIERS:
            qualifiers.pop(key, None)
        material["qualifiers"] = qualifiers
        return canonical(material)

    def settle(self, candidates, prefix="C0", *, require_coverage: bool = False):
        valid = []
        rejected = []
        for index, candidate in enumerate(candidates):
            candidate_ref = self._candidate_ref(candidate, index)
            source_trace = dict(getattr(candidate, "trace", {}) or {})
            if require_coverage:
                try:
                    coverage = coverage_from_dict(source_trace.get("coverage"))
                except CoverageIntegrityError as exc:
                    rejected.append(
                        {
                            "candidate_ref": candidate_ref,
                            "reason": "invalid_coverage_receipt",
                            "details": str(exc),
                        }
                    )
                    continue
                if not coverage.executable:
                    rejected.append(
                        {
                            "candidate_ref": candidate_ref,
                            "reason": "incomplete_semantic_coverage",
                            "coverage_ref": coverage.coverage_ref,
                            "critical_residual_refs": list(coverage.critical_residual_refs),
                            "missing_semantic_roles": list(coverage.missing_semantic_roles),
                        }
                    )
                    continue
            try:
                packet, news = self.compiler.compile(candidate.packet, prefix)
            except ValueError as exc:
                rejected.append(
                    {
                        "candidate_ref": candidate_ref,
                        "reason": "exact_compiler_rejection",
                        "details": str(exc),
                    }
                )
                continue
            signature = self._semantic_signature(packet)
            valid.append(
                {
                    "candidate_ref": candidate_ref,
                    "packet": packet,
                    "news": news,
                    "base": float(candidate.score),
                    "source_trace": source_trace,
                    "signature": signature,
                    "equivalent_candidate_refs": [candidate_ref],
                }
            )

        by_signature = {}
        for item in valid:
            prior = by_signature.get(item["signature"])
            if prior is None:
                by_signature[item["signature"]] = item
                continue
            equivalent_refs = sorted(
                set(prior.get("equivalent_candidate_refs", ()))
                | set(item.get("equivalent_candidate_refs", ()))
            )
            winner = max(
                (prior, item),
                key=lambda value: (value["base"], value["candidate_ref"]),
            )
            winner = dict(winner)
            winner["equivalent_candidate_refs"] = equivalent_refs
            by_signature[item["signature"]] = winner
        values = list(by_signature.values())
        if not values:
            return None, {
                "status": "no_exact_candidate",
                "selected_candidate_ref": None,
                "selected_source_trace": None,
                "candidates": [],
                "rejected_candidates": rejected,
            }

        maximum = max(item["base"] for item in values)
        temperature = float(self.config.settler_score_temperature)
        for item in values:
            item["energy"] = (item["base"] - maximum) / temperature + 0.35
        for _ in range(self.config.settler_rounds):
            normalizer = sum(math.exp(item["energy"]) for item in values)
            probabilities = [math.exp(item["energy"]) / normalizer for item in values]
            for index, item in enumerate(values):
                item["energy"] = (
                    (item["base"] - maximum) / temperature + 0.35
                ) - 0.28 * (1 - probabilities[index])
        normalizer = sum(math.exp(item["energy"]) for item in values)
        for item in values:
            item["posterior"] = math.exp(item["energy"]) / normalizer
        values.sort(
            key=lambda item: (-item["posterior"], -item["base"], item["candidate_ref"])
        )
        top = values[0]
        margin = top["posterior"] - (
            values[1]["posterior"] if len(values) > 1 else 0.0
        )
        score_margin = top["base"] - (
            values[1]["base"] if len(values) > 1 else 0.0
        )
        settled = len(values) == 1 or (
            top["posterior"] >= self.config.settler_posterior_threshold
            and margin >= self.config.settler_margin_threshold
            and score_margin >= self.config.settler_score_margin_threshold
        )
        trace = {
            "status": "settled" if settled else "ambiguous",
            "posterior": top["posterior"],
            "margin": margin,
            "score_margin": score_margin,
            "selected_candidate_ref": top["candidate_ref"] if settled else None,
            "selected_source_trace": dict(top["source_trace"]) if settled else None,
            "candidates": [
                {
                    "candidate_ref": item["candidate_ref"],
                    "posterior": round(item["posterior"], 6),
                    "base_score": item["base"],
                    "packet": item["packet"],
                    "source_trace": dict(item["source_trace"]),
                    "equivalent_candidate_refs": list(
                        item.get("equivalent_candidate_refs", (item["candidate_ref"],))
                    ),
                }
                for item in values[: self.config.settler_top_k]
            ],
            "rejected_candidates": rejected,
        }
        return (
            (top["packet"], top["news"])
            if settled
            else None
        ), trace
