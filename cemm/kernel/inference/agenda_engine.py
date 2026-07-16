"""Incremental agenda-driven bounded semantic inference."""
from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic
from uuid import uuid4

from .engine import BoundedInferenceEngine
from .rule_model import InferenceOutcome, InferenceProofStep


class AgendaInferenceEngine(BoundedInferenceEngine):
    """Triggers only rules reachable from newly committed facts.

    The public signature remains compatible with BoundedInferenceEngine.  When
    ``delta_facts`` is omitted, every seed fact is treated as agenda input, which
    is appropriate for boot closure and standalone calls.
    """

    engine_version = "agenda-seminaive-v3.4.6"

    def infer(
        self,
        *,
        seed_facts,
        rules,
        budget,
        dependency_fingerprint,
        delta_facts=(),
    ):
        started = monotonic()
        seed_facts = tuple(self._ensure_inference_fact(f) for f in seed_facts)
        delta_facts = tuple(self._ensure_inference_fact(f) for f in delta_facts)
        fact_by_identity = {fact.identity: fact for fact in seed_facts}
        facts_by_predicate = defaultdict(list)
        for fact in seed_facts:
            facts_by_predicate[fact.predicate_key].append(fact)

        supported_rules = tuple(sorted(
            (
                rule for rule in rules
                if rule.cycle_class.value != "unsupported_non_monotone"
            ),
            key=lambda item: (item.stratum, -item.priority, item.rule_id),
        ))
        unresolved = tuple(
            rule.rule_id for rule in rules
            if rule.cycle_class.value == "unsupported_non_monotone"
        )
        rules_by_trigger = defaultdict(list)
        for rule in supported_rules:
            for predicate in {
                atom.predicate_key for atom in rule.premises
            }:
                rules_by_trigger[predicate].append(rule)

        agenda_seed = delta_facts or seed_facts
        agenda = deque(agenda_seed)
        queued_ids = {fact.fact_id for fact in agenda_seed}
        derived = []
        constraints = []
        proofs = []
        blockers = []
        visits = {}
        firings_by_rule = {}
        total_firings = 0
        steps = 0
        status = "fixed_point"

        while agenda:
            if self._budget_hit(
                started, steps, total_firings, derived, constraints, budget
            ):
                status = self._budget_status(
                    started, steps, total_firings, derived, constraints, budget
                )
                break
            trigger = agenda.popleft()
            queued_ids.discard(trigger.fact_id)
            for rule in rules_by_trigger.get(trigger.predicate_key, ()):
                if not rule.enabled_by_default:
                    continue
                if rule.sensitivity == "sensitive" and not budget.allow_sensitive:
                    continue
                if firings_by_rule.get(rule.rule_id, 0) >= min(
                    budget.max_firings_per_rule,
                    rule.max_firings_per_cycle,
                ):
                    continue

                for bindings, supporting in self._match_rule_indexed(
                    rule, facts_by_predicate
                ):
                    if trigger.fact_id not in {
                        fact.fact_id for fact in supporting
                    }:
                        continue
                    signature = (
                        rule.rule_id,
                        tuple(sorted(bindings.items())),
                        tuple(fact.fact_id for fact in supporting),
                    )
                    if visits.get(signature, 0) >= budget.max_signature_visits:
                        continue
                    visits[signature] = visits.get(signature, 0) + 1
                    steps += 1

                    all_facts = tuple(
                        fact
                        for bucket in facts_by_predicate.values()
                        for fact in bucket
                    )
                    exception_refs = self._matching_exception_refs(
                        rule, all_facts, bindings
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

                    proof_id = f"inference_proof:{uuid4().hex[:12]}"
                    conclusion_refs = []
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
                            continue
                        if instantiated is None:
                            blockers.append(
                                f"unbound_conclusion:{rule.rule_id}:{atom.predicate_key}"
                            )
                            continue
                        existing = fact_by_identity.get(instantiated.identity)
                        if existing is None:
                            fact_by_identity[instantiated.identity] = instantiated
                            facts_by_predicate[instantiated.predicate_key].append(
                                instantiated
                            )
                            derived.append(instantiated)
                            conclusion_refs.append(instantiated.fact_id)
                            if instantiated.fact_id not in queued_ids:
                                agenda.append(instantiated)
                                queued_ids.add(instantiated.fact_id)
                        else:
                            conclusion_refs.append(existing.fact_id)

                    if conclusion_refs:
                        proofs.append(InferenceProofStep(
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
                        ))
                        firings_by_rule[rule.rule_id] = (
                            firings_by_rule.get(rule.rule_id, 0) + 1
                        )
                        total_firings += 1

                    if self._budget_hit(
                        started, steps, total_firings, derived, constraints, budget
                    ):
                        status = self._budget_status(
                            started, steps, total_firings, derived, constraints, budget
                        )
                        agenda.clear()
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

    def _match_rule_indexed(self, rule, facts_by_predicate):
        partial = [({}, ())]
        for atom in rule.premises:
            next_partial = []
            for bindings, supporting in partial:
                for fact in facts_by_predicate.get(atom.predicate_key, ()):
                    unified = self._unify(atom, fact, bindings)
                    if unified is not None:
                        next_partial.append((unified, (*supporting, fact)))
            partial = next_partial
            if not partial:
                break
        return tuple(partial)
