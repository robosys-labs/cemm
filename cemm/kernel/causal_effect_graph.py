"""CausalEffectGraph — bounded graph of action schemas, affordances,
learned causal rules, policy rules, and context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict


@dataclass(frozen=True, slots=True)
class CausalRule:
    """A causal rule linking an antecedent to an effect."""
    rule_id: str
    antecedent_key: str
    effect_key: str
    direction: str = "forward"  # forward, inverse
    scope: str = "session"
    confidence: float = 0.5

    # Evidence
    support_count: int = 0
    independent_sources: int = 1
    conflict_ids: tuple[str, ...] = ()

    def is_reliable(self) -> bool:
        return self.support_count >= 3 and self.independent_sources >= 2 and self.confidence >= 0.6


@dataclass(frozen=True, slots=True)
class AffordanceEffect:
    """An affordance: a possible action on an entity."""
    effect_id: str
    action_key: str
    target_kind: str
    effect_type: str
    preconditions: tuple[str, ...] = ()
    confidence: float = 0.5


class CausalEffectGraph:
    """Merged graph of causal rules, affordances, and action schemas."""

    def __init__(self) -> None:
        self._rules: dict[str, CausalRule] = {}
        self._affordances: dict[str, AffordanceEffect] = {}
        self._effects_by_antecedent: dict[str, list[str]] = defaultdict(list)

    def add_rule(self, rule: CausalRule) -> None:
        self._rules[rule.rule_id] = rule
        self._effects_by_antecedent[rule.antecedent_key].append(rule.effect_key)

    def add_affordance(self, affordance: AffordanceEffect) -> None:
        self._affordances[affordance.effect_id] = affordance

    def effects_for(self, antecedent_key: str) -> list[str]:
        return list(self._effects_by_antecedent.get(antecedent_key, []))

    def all_rules(self) -> list[CausalRule]:
        return list(self._rules.values())

    def all_affordances(self) -> list[AffordanceEffect]:
        return list(self._affordances.values())
