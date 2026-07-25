"""Bounded exact inference and proof-bearing query execution for CEMM v1."""
from __future__ import annotations

import json
import threading
from typing import Any

from cemm.cognition import QueryBinding, QueryResult, QueryStructure
from cemm.config import Config
from cemm.model import Fact, canonical, isexist, isvar, stable


class InferenceTimeoutError(TimeoutError):
    pass


class Inference:
    def __init__(self, store, config=None, authority_generation=None, max_rounds=None, max_facts=None):
        self.store = store
        self.config = config or Config()
        self.authority_generation = authority_generation
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
        store = self.store
        facts = list(store.base_facts()) + list(extra)
        by_signature = {fact.signature(): fact for fact in facts}
        by_ref = {fact.ref: fact for fact in facts}
        cutoff = self.authority_generation if self.authority_generation is not None else store.generation
        rules = [
            dict(row)
            for row in store.db.execute(
                "SELECT * FROM rules WHERE rule_kind IN('definition','entailment') "
                "AND authority_status IN('reviewed','promoted') AND generation<=? ORDER BY rule_ref",
                (cutoff,),
            )
        ]
        for _ in range(max_rounds):
            if self._timed_out:
                raise InferenceTimeoutError(f"inference exceeded {self.config.inference_timeout_seconds}s")
            added = 0
            for rule in rules:
                antecedent = json.loads(rule["antecedent"])
                consequent = json.loads(rule["consequent"])
                for environment, parents in self._matches(antecedent, list(by_signature.values())):
                    existentials: dict[str, str] = {}
                    parent_refs = tuple(sorted(item.ref for item in parents))
                    for clause in consequent:
                        args = {
                            role: self._inst(value, environment, existentials, rule["rule_ref"], parent_refs)
                            for role, value in clause.get("args", {}).items()
                        }
                        stance = clause.get("stance", "support")
                        ref = stable("derived", rule["rule_ref"], parent_refs, clause.get("operator"), args, stance)
                        fact = Fact(
                            ref,
                            clause["operator"],
                            args,
                            stance,
                            min([item.confidence for item in parents] + [1.0]) * float(rule["confidence"]),
                            True,
                            {"rule_ref": rule["rule_ref"], "parents": parent_refs},
                        )
                        if fact.signature() not in by_signature:
                            by_signature[fact.signature()] = fact
                            by_ref[fact.ref] = fact
                            added += 1
                        if len(by_signature) >= max_facts:
                            self.incomplete = True
                            self.incomplete_reason = "max_facts"
                            return list(by_signature.values()), by_ref
            if not added:
                break
        else:
            self.incomplete = True
            self.incomplete_reason = "max_rounds"
        return list(by_signature.values()), by_ref

    def _matches(self, clauses, facts, initial=None):
        states = [(dict(initial or {}), [])]
        for clause in clauses:
            next_states = []
            for environment, parents in states:
                for fact in facts:
                    candidate = dict(environment)
                    if self._unify_clause(clause, fact, candidate):
                        next_states.append((candidate, parents + [fact]))
            states = next_states
            if not states:
                break
        return states

    def _unify_clause(self, clause, fact, environment):
        if clause.get("stance", "support") != fact.stance or not self._unify(
            clause["operator"], fact.operator, environment
        ):
            return False
        return all(
            role in fact.args and self._unify(pattern, fact.args[role], environment)
            for role, pattern in clause.get("args", {}).items()
        )

    @staticmethod
    def _unify(pattern, value, environment):
        if isvar(pattern):
            if pattern in environment:
                return canonical(environment[pattern]) == canonical(value)
            environment[pattern] = value
            return True
        return canonical(pattern) == canonical(value)

    @staticmethod
    def _inst(value, environment, existentials, rule, parents):
        if isvar(value):
            return environment[value]
        if isexist(value):
            if value not in existentials:
                existentials[value] = stable("existential", rule, parents, value)
            return existentials[value]
        return value

    def match(self, pattern, facts):
        return [
            fact
            for fact in facts
            if self._unify_clause(
                {
                    "operator": pattern["operator"],
                    "args": pattern.get("args", {}),
                    "stance": pattern.get("stance", "support"),
                },
                fact,
                {},
            )
        ]

    def match_with_bindings(self, pattern, facts):
        output = []
        clause = {
            "operator": pattern["operator"],
            "args": pattern.get("args", {}),
            "stance": pattern.get("stance", "support"),
        }
        for fact in facts:
            environment: dict[str, Any] = {}
            if self._unify_clause(clause, fact, environment):
                output.append((environment, fact))
        return output

    def execute_query(self, raw_query, facts, by_ref=None):
        query = raw_query if isinstance(raw_query, QueryStructure) else QueryStructure.from_dict(raw_query)
        support_matches = self._matches(list(query.restrictions), facts)
        opposition_matches = []
        if len(query.restrictions) == 1:
            denied = dict(query.restrictions[0])
            denied["stance"] = "deny"
            opposition_matches = self._matches([denied], facts)

        bindings: list[QueryBinding] = []
        proofs: list[dict[str, Any]] = []
        seen = set()
        for environment, parents in support_matches:
            projected = {name: environment[name] for name in query.projection if name in environment}
            signature = canonical(projected)
            if signature in seen:
                continue
            seen.add(signature)
            proof_refs = tuple(sorted(item.ref for item in parents))
            bindings.append(QueryBinding(projected, proof_refs))
            if by_ref is not None:
                proofs.extend(self.explain(item, by_ref) for item in parents)

        projected_variables = set(query.projection)
        bound_variables = {name for binding in bindings for name in binding.values}
        unresolved = tuple(sorted(projected_variables - bound_variables))
        if query.projection:
            coverage = len(bound_variables) / max(1, len(projected_variables))
            if support_matches and opposition_matches:
                status = "conflict"
            elif support_matches and not unresolved:
                status = "answered"
            elif support_matches:
                status = "partial"
            elif opposition_matches:
                status = "contradicted"
            else:
                status = "unknown"
        else:
            coverage = 1.0 if support_matches or opposition_matches else 0.0
            status = (
                "conflict"
                if support_matches and opposition_matches
                else "supported"
                if support_matches
                else "contradicted"
                if opposition_matches
                else "unknown"
            )
        return QueryResult(
            query_ref=query.query_ref,
            status=status,
            bindings=tuple(bindings),
            coverage=coverage,
            support_count=len(support_matches),
            opposition_count=len(opposition_matches),
            unresolved_variables=unresolved,
            proofs=tuple(proofs),
        )

    def explain(self, fact, by_ref):
        if not fact.derived:
            return {
                "fact_ref": fact.ref,
                "source": "observed",
                "operator": fact.operator,
                "args": fact.args,
            }
        return {
            "fact_ref": fact.ref,
            "source": "derived",
            "operator": fact.operator,
            "args": fact.args,
            "rule_ref": fact.proof["rule_ref"],
            "parents": [
                self.explain(by_ref[parent], by_ref)
                for parent in fact.proof["parents"]
                if parent in by_ref
            ],
        }
