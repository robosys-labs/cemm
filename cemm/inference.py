"""Bounded exact inference and proof-bearing query execution over sparse retrieval."""
from __future__ import annotations

import json
import time
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

    def closure(self, *, seed_facts, rules, extra=(), max_rounds=None, max_facts=None):
        """Derive a bounded closure from an explicit sparse seed set."""
        max_rounds = max_rounds or self._max_rounds or self.config.inference_max_rounds
        max_facts = max_facts or self._max_facts or self.config.inference_max_facts
        self.incomplete = False
        self.incomplete_reason = None
        deadline = time.monotonic() + float(self.config.inference_timeout_seconds)
        facts = list(seed_facts) + list(extra)
        by_signature = {fact.signature(): fact for fact in facts}
        by_ref = {fact.ref: fact for fact in facts}
        decoded_rules = [dict(row) for row in rules]
        for _round in range(int(max_rounds)):
            if time.monotonic() >= deadline:
                raise InferenceTimeoutError(f"inference exceeded {self.config.inference_timeout_seconds}s")
            added = 0
            snapshot = list(by_signature.values())
            for rule in decoded_rules:
                antecedent = json.loads(rule["antecedent"]) if isinstance(rule["antecedent"], str) else list(rule["antecedent"])
                consequent = json.loads(rule["consequent"]) if isinstance(rule["consequent"], str) else list(rule["consequent"])
                for environment, parents in self._matches(antecedent, snapshot):
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
                            if len(by_signature) >= int(max_facts):
                                self.incomplete = True
                                self.incomplete_reason = "max_facts"
                                return list(by_signature.values()), by_ref
            if not added:
                break
        else:
            self.incomplete = True
            self.incomplete_reason = "max_rounds"
        return list(by_signature.values()), by_ref

    def match_clauses(self, clauses, facts, initial=None):
        return self._matches(clauses, facts, initial)

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
        if clause.get("stance", "support") != fact.stance:
            return False
        if not self._unify(clause["operator"], fact.operator, environment):
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
            if value not in environment:
                raise ValueError(f"unbound rule variable: {value}")
            return environment[value]
        if isexist(value):
            if value not in existentials:
                existentials[value] = stable("existential", rule, parents, value)
            return existentials[value]
        return value

    def match(self, pattern, facts):
        return [fact for environment, parents in self._matches([pattern], facts) for fact in parents[-1:]]

    def execute_query(self, raw_query, facts, by_ref=None, *, blocking_frontiers=()):
        query = raw_query if isinstance(raw_query, QueryStructure) else QueryStructure.from_dict(raw_query)
        support_matches = self._matches(list(query.restrictions), facts)
        opposition_matches = []
        if len(query.restrictions) == 1:
            denied = dict(query.restrictions[0])
            denied["stance"] = "deny"
            opposition_matches = self._matches([denied], facts)

        bindings = []
        proofs = []
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
            status = (
                "conflict" if support_matches and opposition_matches
                else "answered" if support_matches and not unresolved
                else "partial" if support_matches
                else "contradicted" if opposition_matches
                else "unknown"
            )
        else:
            coverage = 1.0 if support_matches or opposition_matches else 0.0
            status = (
                "conflict" if support_matches and opposition_matches
                else "supported" if support_matches
                else "contradicted" if opposition_matches
                else "unknown"
            )
        return QueryResult(
            query.query_ref,
            status,
            tuple(bindings),
            coverage,
            len(support_matches),
            len(opposition_matches),
            unresolved,
            tuple(proofs),
            tuple(blocking_frontiers),
        )

    def explain(self, fact, by_ref):
        if not fact.derived:
            return {
                "fact_ref": fact.ref,
                "source": "observed",
                "operator": fact.operator,
                "args": fact.args,
                "stance": fact.stance,
                "confidence": fact.confidence,
            }
        if not fact.proof or "rule_ref" not in fact.proof:
            return {
                "fact_ref": fact.ref,
                "source": "runtime_provider" if fact.proof and fact.proof.get("runtime_provider") else "ephemeral",
                "operator": fact.operator,
                "args": fact.args,
                "stance": fact.stance,
                "confidence": fact.confidence,
                "proof": dict(fact.proof or {}),
            }
        return {
            "fact_ref": fact.ref,
            "source": "derived",
            "operator": fact.operator,
            "args": fact.args,
            "stance": fact.stance,
            "confidence": fact.confidence,
            "rule_ref": fact.proof["rule_ref"],
            "parents": [
                self.explain(by_ref[parent], by_ref)
                for parent in fact.proof["parents"]
                if parent in by_ref
            ],
        }
