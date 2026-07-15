"""Bounded proof-carrying semantic inference.

The engine distinguishes strict entailment, defeasible defaults, probabilistic
associations, and causal warrant.  Unbound entities are represented as
ExistentialConstraint records; concrete people or events are never invented.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
from time import monotonic
from uuid import uuid4

from .rule_model import (
    CausalWarrant,
    ExistentialConstraint,
    InferenceBudget,
    InferenceOutcome,
    InferenceProofStep,
    RuleAtom,
    RuleStrength,
    SemanticFact,
    SemanticRule,
)


class BoundedInferenceEngine:
    def infer(
        self,
        *,
        seed_facts: tuple[SemanticFact, ...],
        rules: tuple[SemanticRule, ...],
        budget: InferenceBudget,
        dependency_fingerprint: str,
    ) -> InferenceOutcome:
        started = monotonic()
        fact_by_identity = {fact.identity: fact for fact in seed_facts}
        all_facts = list(seed_facts)
        derived: list[SemanticFact] = []
        constraints: list[ExistentialConstraint] = []
        proofs: list[InferenceProofStep] = []
        visits: dict[tuple, int] = {}
        firings_by_rule: dict[str, int] = {}
        total_firings = 0
        steps = 0
        blockers: list[str] = []
        unresolved: list[str] = []

        supported_rules = tuple(
            sorted(
                (
                    rule
                    for rule in rules
                    if rule.cycle_class.value
                    not in {"unsupported_non_monotone"}
                ),
                key=lambda item: (item.stratum, -item.priority, item.rule_id),
            )
        )
        unresolved.extend(
            rule.rule_id
            for rule in rules
            if rule.cycle_class.value == "unsupported_non_monotone"
        )

        status = "fixed_point"
        changed = True
        while changed:
            changed = False
            if steps >= budget.max_steps:
                status = "max_steps"
                break
            if total_firings >= budget.max_rule_firings:
                status = "max_rule_firings"
                break
            if len(derived) >= budget.max_new_facts:
                status = "max_new_facts"
                break
            if len(constraints) >= budget.max_existential_constraints:
                status = "max_existential_constraints"
                break
            if (monotonic() - started) * 1000 >= budget.wall_clock_ms:
                status = "timed_out"
                break

            snapshot = tuple(all_facts)
            for rule in supported_rules:
                if not rule.enabled_by_default:
                    continue
                if rule.sensitivity == "sensitive" and not budget.allow_sensitive:
                    continue
                if firings_by_rule.get(rule.rule_id, 0) >= min(
                    budget.max_firings_per_rule,
                    rule.max_firings_per_cycle,
                ):
                    continue

                for bindings, supporting in self._match_rule(rule, snapshot):
                    signature = (
                        rule.rule_id,
                        tuple(sorted(bindings.items())),
                        tuple(fact.fact_id for fact in supporting),
                    )
                    if visits.get(signature, 0) >= budget.max_signature_visits:
                        continue
                    visits[signature] = visits.get(signature, 0) + 1
                    steps += 1

                    exception_refs = self._matching_exception_refs(
                        rule, snapshot, bindings
                    )
                    if exception_refs:
                        continue

                    depth = max(
                        (fact.derivation_depth for fact in supporting),
                        default=0,
                    ) + 1
                    if depth > budget.max_depth:
                        blockers.append(f"depth_limit:{rule.rule_id}")
                        continue

                    conclusion_refs: list[str] = []
                    proof_id = f"inference_proof:{uuid4().hex[:12]}"
                    for atom in rule.conclusions:
                        instantiated, existential = self._instantiate(
                            rule=rule,
                            atom=atom,
                            bindings=bindings,
                            supporting=supporting,
                            proof_id=proof_id,
                            depth=depth,
                        )
                        if existential is not None:
                            if existential.constraint_id not in {
                                item.constraint_id for item in constraints
                            }:
                                constraints.append(existential)
                                conclusion_refs.append(existential.constraint_id)
                                changed = True
                            continue
                        if instantiated is None:
                            blockers.append(
                                f"unbound_conclusion:{rule.rule_id}:{atom.predicate_key}"
                            )
                            continue
                        existing = fact_by_identity.get(instantiated.identity)
                        if existing is None:
                            fact_by_identity[instantiated.identity] = instantiated
                            all_facts.append(instantiated)
                            derived.append(instantiated)
                            conclusion_refs.append(instantiated.fact_id)
                            changed = True
                        else:
                            conclusion_refs.append(existing.fact_id)

                    if conclusion_refs:
                        proofs.append(
                            InferenceProofStep(
                                proof_id=proof_id,
                                rule_ref=rule.rule_id,
                                premise_fact_refs=tuple(
                                    fact.fact_id for fact in supporting
                                ),
                                variable_bindings=dict(bindings),
                                conclusion_refs=tuple(conclusion_refs),
                                exception_checks=tuple(exception_refs),
                                strength=rule.strength,
                                causal_warrant=rule.causal_warrant,
                                context_ref=self._context(supporting),
                                valid_time_ref=self._valid_time(supporting),
                                derivation_depth=depth,
                                dependency_fingerprint=dependency_fingerprint,
                            )
                        )
                        firings_by_rule[rule.rule_id] = (
                            firings_by_rule.get(rule.rule_id, 0) + 1
                        )
                        total_firings += 1

                    if self._budget_hit(
                        started, steps, total_firings, derived, constraints, budget
                    ):
                        status = self._budget_status(
                            started,
                            steps,
                            total_firings,
                            derived,
                            constraints,
                            budget,
                        )
                        changed = False
                        break
                if status != "fixed_point":
                    break
            if status != "fixed_point":
                break

        return InferenceOutcome(
            status=status,
            derived_facts=tuple(derived),
            existential_constraints=tuple(constraints),
            proofs=tuple(proofs),
            unresolved_rule_refs=tuple(dict.fromkeys(unresolved)),
            blocker_refs=tuple(dict.fromkeys(blockers)),
            steps=steps,
            elapsed_ms=(monotonic() - started) * 1000,
        )

    def _match_rule(self, rule, facts):
        partial: list[tuple[dict[str, str], tuple[SemanticFact, ...]]] = [
            ({}, ())
        ]
        for atom in rule.premises:
            next_partial = []
            for bindings, supporting in partial:
                for fact in facts:
                    unified = self._unify(atom, fact, bindings)
                    if unified is not None:
                        next_partial.append((unified, (*supporting, fact)))
            partial = next_partial
            if not partial:
                break
        return tuple(partial)

    @staticmethod
    def _unify(atom: RuleAtom, fact: SemanticFact, bindings):
        if atom.predicate_key != fact.predicate_key:
            return None
        if atom.polarity != fact.polarity:
            return None
        result = dict(bindings)
        for role_key, term in atom.roles.items():
            actual = fact.roles.get(role_key)
            if actual is None:
                return None
            if term.startswith("$"):
                existing = result.get(term)
                if existing is not None and existing != actual:
                    return None
                result[term] = actual
            elif term.startswith("?"):
                # Existential terms are never bound from premises implicitly.
                return None
            elif term != actual:
                return None
        context = result.get(atom.context_term)
        if context is not None and context != fact.context_ref:
            return None
        result[atom.context_term] = fact.context_ref
        if atom.valid_time_term:
            valid_time = result.get(atom.valid_time_term)
            if valid_time is not None and valid_time != fact.valid_time_ref:
                return None
            result[atom.valid_time_term] = fact.valid_time_ref
        return result

    def _matching_exception_refs(self, rule, facts, bindings):
        refs = []
        for exception in rule.exception_atoms:
            for fact in facts:
                if self._unify(exception, fact, bindings) is not None:
                    refs.append(fact.fact_id)
        return tuple(refs)

    def _instantiate(
        self,
        *,
        rule,
        atom,
        bindings,
        supporting,
        proof_id,
        depth,
    ):
        roles = {}
        existential_variables = []
        for role_key, term in atom.roles.items():
            if term.startswith("$"):
                value = bindings.get(term)
                if value is None:
                    return None, None
                roles[role_key] = value
            elif term.startswith("?"):
                declaration = rule.declared_existential(term)
                if declaration is None:
                    return None, None
                existential_variables.append((term, declaration))
                roles[role_key] = term
            else:
                roles[role_key] = term

        context_ref = bindings.get(
            atom.context_term, self._context(supporting)
        )
        valid_time_ref = bindings.get(
            atom.valid_time_term, self._valid_time(supporting)
        )
        evidence_refs = tuple(
            dict.fromkeys(
                ref
                for fact in supporting
                for ref in (*fact.evidence_refs, fact.fact_id)
            )
        )

        if existential_variables:
            variable, declaration = existential_variables[0]
            normalized_bindings = {
                key: value for key, value in roles.items() if value != variable
            }
            digest = hashlib.sha256(
                (
                    f"{rule.rule_id}|{variable}|{sorted(normalized_bindings.items())}|"
                    f"{context_ref}|{valid_time_ref}"
                ).encode("utf-8")
            ).hexdigest()[:16]
            return None, ExistentialConstraint(
                constraint_id=f"existential:{digest}",
                rule_ref=rule.rule_id,
                variable=variable,
                entity_kind_ref=declaration.entity_kind_ref,
                bound_roles=normalized_bindings,
                context_ref=context_ref,
                valid_time_ref=valid_time_ref,
                evidence_refs=evidence_refs,
                sensitivity=rule.sensitivity,
            )

        confidence = min(
            [rule.confidence, *(fact.confidence for fact in supporting)]
        )
        if rule.strength is RuleStrength.DEFEASIBLE:
            confidence *= 0.75
        elif rule.strength is RuleStrength.PROBABILISTIC:
            confidence *= 0.5

        return SemanticFact(
            fact_id=f"derived:{uuid4().hex[:16]}",
            predicate_key=atom.predicate_key,
            roles=roles,
            context_ref=context_ref,
            valid_time_ref=valid_time_ref,
            polarity=atom.polarity,
            confidence=confidence,
            strength=rule.strength,
            causal_warrant=rule.causal_warrant,
            sensitivity=rule.sensitivity,
            evidence_refs=evidence_refs,
            derivation_ref=proof_id,
            derivation_depth=depth,
        ), None

    @staticmethod
    def _context(facts):
        values = {fact.context_ref for fact in facts if fact.context_ref}
        return next(iter(values)) if len(values) == 1 else ""

    @staticmethod
    def _valid_time(facts):
        values = {fact.valid_time_ref for fact in facts if fact.valid_time_ref}
        return next(iter(values)) if len(values) == 1 else ""

    @staticmethod
    def _budget_hit(started, steps, firings, derived, constraints, budget):
        return any(
            (
                steps >= budget.max_steps,
                firings >= budget.max_rule_firings,
                len(derived) >= budget.max_new_facts,
                len(constraints) >= budget.max_existential_constraints,
                (monotonic() - started) * 1000 >= budget.wall_clock_ms,
            )
        )

    @staticmethod
    def _budget_status(started, steps, firings, derived, constraints, budget):
        if (monotonic() - started) * 1000 >= budget.wall_clock_ms:
            return "timed_out"
        if steps >= budget.max_steps:
            return "max_steps"
        if firings >= budget.max_rule_firings:
            return "max_rule_firings"
        if len(derived) >= budget.max_new_facts:
            return "max_new_facts"
        if len(constraints) >= budget.max_existential_constraints:
            return "max_existential_constraints"
        return "bounded_stop"
