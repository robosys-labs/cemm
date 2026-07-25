"""Sparse indexed retrieval for query, workspace and causal reasoning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from cemm.model import Fact, canonical, isvar, stable


@dataclass(frozen=True)
class RetrievalSet:
    retrieval_ref: str
    facts: tuple[Fact, ...]
    rules: tuple[dict[str, Any], ...]
    truncated: bool
    trace: Mapping[str, Any]

    def as_dict(self):
        return {
            "retrieval_ref": self.retrieval_ref,
            "fact_count": len(self.facts),
            "rule_count": len(self.rules),
            "truncated": self.truncated,
            "trace": dict(self.trace),
        }


class SemanticRetriever:
    """Backward relevance expansion from restrictions, not whole-store closure."""

    def __init__(self, store, config, authority_generation):
        self.s = store
        self.config = config
        self.authority_generation = int(authority_generation)

    @staticmethod
    def _constants(applications: Iterable[Mapping[str, Any]]):
        return {
            str(value)
            for application in applications
            for value in application.get("args", {}).values()
            if isinstance(value, str) and not isvar(value)
        }

    def retrieve(self, restrictions=(), *, salient_refs=(), include_causal=False):
        restrictions = tuple(dict(x) for x in restrictions)
        operators = {str(x.get("operator")) for x in restrictions if x.get("operator")}
        refs = set(salient_refs) | self._constants(restrictions)
        facts = {fact.ref: fact for fact in self.s.matching_facts(restrictions, limit=self.config.retrieval_max_seed_facts)}
        rules = {}
        frontier_ops = set(operators)
        frontier_refs = set(refs)
        depth = 0
        truncated = False
        allowed_kinds = ("definition", "entailment", "causal") if include_causal else ("definition", "entailment")
        while depth < self.config.retrieval_max_depth and (frontier_ops or frontier_refs):
            rows = self.s.relevant_rules(
                rule_kinds=allowed_kinds,
                consequent=True,
                operator_refs=frontier_ops,
                semantic_refs=frontier_refs,
                authority_generation=self.authority_generation,
                limit=self.config.retrieval_max_rules - len(rules),
            )
            new_ops = set()
            new_refs = set()
            for row in rows:
                if row["rule_ref"] in rules:
                    continue
                rules[row["rule_ref"]] = dict(row)
                antecedent = self.s.decode_rule_side(row["antecedent"])
                new_ops |= {str(x.get("operator")) for x in antecedent if x.get("operator")}
                new_refs |= self._constants(antecedent)
                for fact in self.s.matching_facts(antecedent, limit=max(1, self.config.retrieval_max_seed_facts - len(facts))):
                    facts.setdefault(fact.ref, fact)
                if len(facts) >= self.config.retrieval_max_seed_facts or len(rules) >= self.config.retrieval_max_rules:
                    truncated = True
                    break
            if truncated or not rows:
                break
            frontier_ops = new_ops - frontier_ops
            frontier_refs = new_refs - frontier_refs
            depth += 1
        if refs and len(facts) < self.config.retrieval_max_seed_facts:
            for fact in self.s.facts_mentioning(refs, limit=self.config.retrieval_max_seed_facts - len(facts)):
                facts.setdefault(fact.ref, fact)
        ordered_facts = tuple(facts[key] for key in sorted(facts))
        ordered_rules = tuple(rules[key] for key in sorted(rules))
        trace = {
            "seed_operators": sorted(operators),
            "seed_refs": sorted(refs),
            "depth": depth,
            "bounded": True,
            "whole_store_scan": False,
        }
        return RetrievalSet(stable("retrieval", restrictions, sorted(refs), [x.ref for x in ordered_facts], [x["rule_ref"] for x in ordered_rules]), ordered_facts, ordered_rules, truncated, trace)
