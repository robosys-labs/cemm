"""Selective, proof-oriented retrieval for query and causal reasoning.

A retrieval request is executable only when its restriction graph has a bound,
indexed seed and every restriction is connected to that seed through shared
variables.  Context salience is recorded but never used to broaden seed facts or
rule expansion.  Every returned seed fact is rechecked against the bound
restriction contract before it enters inference.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from cemm.model import Fact, canonical, isvar, stable


@dataclass(frozen=True)
class QueryPlan:
    plan_ref: str
    restrictions: tuple[Mapping[str, Any], ...]
    indexed_constraints: tuple[Mapping[str, Any], ...]
    seed_operators: tuple[str, ...]
    seed_refs: tuple[str, ...]
    context_refs: tuple[str, ...]
    connected_restriction_indexes: tuple[int, ...]
    selective: bool
    selectivity_class: str
    underconstrained_reason: str | None
    fact_budget: int
    rule_budget: int
    depth_budget: int

    def __post_init__(self) -> None:
        if self.fact_budget < 1 or self.rule_budget < 0 or self.depth_budget < 0:
            raise ValueError("retrieval plan has invalid budgets")
        if self.selective and not self.indexed_constraints:
            raise ValueError("selective retrieval plan lacks indexed constraints")
        if self.selective and self.underconstrained_reason:
            raise ValueError("selective retrieval plan cannot carry underconstrained reason")
        if not self.selective and not self.underconstrained_reason:
            raise ValueError("underconstrained retrieval plan requires an exact reason")

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_ref": self.plan_ref,
            "restrictions": [dict(item) for item in self.restrictions],
            "indexed_constraints": [dict(item) for item in self.indexed_constraints],
            "seed_operators": list(self.seed_operators),
            "seed_refs": list(self.seed_refs),
            "context_refs": list(self.context_refs),
            "connected_restriction_indexes": list(self.connected_restriction_indexes),
            "selective": self.selective,
            "selectivity_class": self.selectivity_class,
            "underconstrained_reason": self.underconstrained_reason,
            "fact_budget": self.fact_budget,
            "rule_budget": self.rule_budget,
            "depth_budget": self.depth_budget,
        }


@dataclass(frozen=True)
class RetrievalSet:
    retrieval_ref: str
    facts: tuple[Fact, ...]
    rules: tuple[dict[str, Any], ...]
    truncated: bool
    trace: Mapping[str, Any]

    def __post_init__(self) -> None:
        fact_refs = [item.ref for item in self.facts]
        rule_refs = [str(item.get("rule_ref")) for item in self.rules]
        if len(fact_refs) != len(set(fact_refs)):
            raise ValueError("retrieval set contains duplicate facts")
        if len(rule_refs) != len(set(rule_refs)):
            raise ValueError("retrieval set contains duplicate rules")

    def as_dict(self):
        return {
            "retrieval_ref": self.retrieval_ref,
            "fact_count": len(self.facts),
            "rule_count": len(self.rules),
            "truncated": self.truncated,
            "trace": dict(self.trace),
        }


class SemanticRetriever:
    """Backward relevance expansion from one selective, inspectable plan."""

    def __init__(self, store, config, authority_generation):
        self.s = store
        self.config = config
        self.authority_generation = int(authority_generation)

    @staticmethod
    def _constants(applications: Iterable[Mapping[str, Any]]) -> set[str]:
        return {
            str(value)
            for application in applications
            for value in application.get("args", {}).values()
            if isinstance(value, str) and not isvar(value)
        }

    @staticmethod
    def _variables(application: Mapping[str, Any]) -> set[str]:
        return {
            str(value)
            for value in application.get("args", {}).values()
            if isinstance(value, str) and isvar(value)
        }

    @staticmethod
    def _bound(value: Any) -> bool:
        if isinstance(value, str):
            return not isvar(value)
        if isinstance(value, Mapping):
            return "literal" in value or "app" in value
        return value is not None

    @staticmethod
    def _fact_matches_restriction(fact: Fact, restriction: Mapping[str, Any]) -> bool:
        if fact.operator != restriction.get("operator"):
            return False
        stance = restriction.get("stance")
        if stance is not None and fact.stance != stance:
            return False
        for role, expected in restriction.get("args", {}).items():
            if isinstance(expected, str) and isvar(expected):
                continue
            if role not in fact.args or canonical(fact.args[role]) != canonical(expected):
                return False
        return True

    @classmethod
    def _fact_matches_any(cls, fact: Fact, restrictions: tuple[Mapping[str, Any], ...]) -> bool:
        return any(cls._fact_matches_restriction(fact, item) for item in restrictions)

    @staticmethod
    def _connected_indexes(
        restrictions: tuple[Mapping[str, Any], ...], seeded: set[int]
    ) -> set[int]:
        variables = [SemanticRetriever._variables(item) for item in restrictions]
        connected = set(seeded)
        changed = True
        while changed:
            changed = False
            connected_variables = set().union(*(variables[index] for index in connected)) if connected else set()
            for index, item_variables in enumerate(variables):
                if index in connected:
                    continue
                if item_variables & connected_variables:
                    connected.add(index)
                    changed = True
        return connected

    def plan(self, restrictions=(), *, salient_refs=()) -> QueryPlan:
        restrictions = tuple(dict(item) for item in restrictions)
        constraints: list[dict[str, Any]] = []
        malformed: list[int] = []
        seeded_indexes: set[int] = set()
        for index, restriction in enumerate(restrictions):
            operator = restriction.get("operator")
            args = restriction.get("args", {})
            if not isinstance(operator, str) or not operator or not isinstance(args, Mapping):
                malformed.append(index)
                continue
            for role, value in sorted(args.items()):
                if not self._bound(value):
                    continue
                seeded_indexes.add(index)
                constraint_kind = (
                    "semantic_ref"
                    if isinstance(value, str)
                    else "literal"
                    if isinstance(value, Mapping) and "literal" in value
                    else "application"
                    if isinstance(value, Mapping) and "app" in value
                    else "structured"
                )
                constraints.append(
                    {
                        "restriction_index": index,
                        "operator": operator,
                        "role": str(role),
                        "constraint_kind": constraint_kind,
                        "value_signature": canonical(value),
                    }
                )
        connected = self._connected_indexes(restrictions, seeded_indexes)
        if not restrictions:
            reason = "no_restrictions"
        elif malformed:
            reason = "malformed_restrictions:" + ",".join(map(str, malformed))
        elif not constraints:
            reason = "no_bound_index_key"
        elif connected != set(range(len(restrictions))):
            disconnected = sorted(set(range(len(restrictions))) - connected)
            reason = "disconnected_unbound_restrictions:" + ",".join(map(str, disconnected))
        else:
            reason = None
        selective = reason is None
        operators = tuple(
            sorted({str(item.get("operator")) for item in restrictions if item.get("operator")})
        )
        refs = tuple(sorted(self._constants(restrictions)))
        context_refs = tuple(sorted(set(str(item) for item in salient_refs if item)))
        selectivity_class = (
            "connected_operator_and_multiple_bound_roles"
            if selective and len(constraints) > 1
            else "connected_operator_and_bound_role"
            if selective
            else "underconstrained"
        )
        payload = (
            restrictions,
            constraints,
            operators,
            refs,
            context_refs,
            sorted(connected),
            reason,
            self.config.retrieval_max_seed_facts,
            self.config.retrieval_max_rules,
            self.config.retrieval_max_depth,
        )
        return QueryPlan(
            stable("query-plan", payload),
            restrictions,
            tuple(constraints),
            operators,
            refs,
            context_refs,
            tuple(sorted(connected)),
            selective,
            selectivity_class,
            reason,
            int(self.config.retrieval_max_seed_facts),
            int(self.config.retrieval_max_rules),
            int(self.config.retrieval_max_depth),
        )

    def _matching_facts(
        self,
        restrictions: tuple[Mapping[str, Any], ...],
        *,
        limit: int,
    ) -> tuple[tuple[Fact, ...], int]:
        if limit <= 0:
            return (), 0
        returned = tuple(self.s.matching_facts(restrictions, limit=limit))
        accepted = tuple(
            fact for fact in returned if self._fact_matches_any(fact, restrictions)
        )
        rejected = len(returned) - len(accepted)
        return accepted[:limit], rejected

    def retrieve(self, restrictions=(), *, salient_refs=(), include_causal=False):
        plan = self.plan(restrictions, salient_refs=salient_refs)
        if not plan.selective:
            trace = {
                "query_plan": plan.as_dict(),
                "underconstrained": True,
                "actual_fact_count": 0,
                "actual_rule_count": 0,
                "rejected_store_rows": 0,
                "depth": 0,
                "bounded": True,
                "whole_store_scan": False,
                "salience_broadening": False,
                "truncation_reason": None,
            }
            return RetrievalSet(
                stable("retrieval", plan.plan_ref, (), ()), (), (), False, trace
            )

        restrictions = tuple(dict(item) for item in restrictions)
        operators = set(plan.seed_operators)
        refs = set(plan.seed_refs)
        seed_facts, rejected_rows = self._matching_facts(
            restrictions, limit=plan.fact_budget
        )
        facts = {fact.ref: fact for fact in seed_facts}
        rules: dict[str, dict[str, Any]] = {}
        frontier_ops = set(operators)
        frontier_refs = set(refs)
        seen_ops = set(frontier_ops)
        seen_refs = set(frontier_refs)
        depth = 0
        truncated = len(seed_facts) >= plan.fact_budget
        truncation_reason = "fact_budget" if truncated else None
        allowed_kinds = (
            ("definition", "entailment", "causal")
            if include_causal
            else ("definition", "entailment")
        )
        while not truncated and depth < plan.depth_budget and (frontier_ops or frontier_refs):
            remaining_rule_budget = plan.rule_budget - len(rules)
            if remaining_rule_budget <= 0:
                if plan.rule_budget:
                    truncated = True
                    truncation_reason = "rule_budget"
                break
            rows = tuple(
                self.s.relevant_rules(
                    rule_kinds=allowed_kinds,
                    consequent=True,
                    operator_refs=frontier_ops,
                    semantic_refs=frontier_refs,
                    authority_generation=self.authority_generation,
                    limit=remaining_rule_budget,
                )
            )
            if not rows:
                break
            new_ops: set[str] = set()
            new_refs: set[str] = set()
            for row in rows:
                rule_ref = str(row["rule_ref"])
                if rule_ref in rules:
                    continue
                rules[rule_ref] = dict(row)
                antecedent = tuple(self.s.decode_rule_side(row["antecedent"]))
                new_ops |= {
                    str(item.get("operator")) for item in antecedent if item.get("operator")
                }
                new_refs |= self._constants(antecedent)
                remaining_fact_budget = plan.fact_budget - len(facts)
                if remaining_fact_budget <= 0:
                    truncated = True
                    truncation_reason = "fact_budget"
                    break
                matched, rejected = self._matching_facts(
                    antecedent, limit=remaining_fact_budget
                )
                rejected_rows += rejected
                for fact in matched:
                    facts.setdefault(fact.ref, fact)
                if len(facts) >= plan.fact_budget:
                    truncated = True
                    truncation_reason = "fact_budget"
                    break
                if len(rules) >= plan.rule_budget:
                    truncated = True
                    truncation_reason = "rule_budget"
                    break
            if truncated:
                break
            frontier_ops = new_ops - seen_ops
            frontier_refs = new_refs - seen_refs
            seen_ops.update(new_ops)
            seen_refs.update(new_refs)
            depth += 1
        if not truncated and depth >= plan.depth_budget and (frontier_ops or frontier_refs):
            truncated = True
            truncation_reason = "depth_budget"

        ordered_facts = tuple(facts[key] for key in sorted(facts))
        ordered_rules = tuple(rules[key] for key in sorted(rules))
        trace = {
            "query_plan": plan.as_dict(),
            "underconstrained": False,
            "actual_fact_count": len(ordered_facts),
            "actual_rule_count": len(ordered_rules),
            "rejected_store_rows": rejected_rows,
            "depth": depth,
            "bounded": True,
            "whole_store_scan": False,
            "salience_broadening": False,
            "truncation_reason": truncation_reason,
        }
        return RetrievalSet(
            stable(
                "retrieval",
                plan.plan_ref,
                [item.ref for item in ordered_facts],
                [item["rule_ref"] for item in ordered_rules],
            ),
            ordered_facts,
            ordered_rules,
            truncated,
            trace,
        )
