"""Language-neutral dialogue policy rules loaded from data."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ResponsePolicyRule:
    rule_id: str
    trigger_predicate: str
    trigger_force: str
    output_predicate: str
    output_force: str
    role_map: dict[str, dict[str, str]]
    priority: int = 0

    @classmethod
    def from_dict(cls, raw):
        return cls(
            rule_id=raw["rule_id"],
            trigger_predicate=raw["trigger"][
                "predicate_key"
            ],
            trigger_force=raw["trigger"].get(
                "communicative_force", "ask"
            ),
            output_predicate=raw["output"][
                "predicate_key"
            ],
            output_force=raw["output"].get(
                "communicative_force", "assert"
            ),
            role_map=dict(
                raw["output"].get("role_map", {})
            ),
            priority=int(raw.get("priority", 0)),
        )

class ResponsePolicyRegistry:
    def __init__(self, raw_rules=()):
        self._rules = tuple(sorted(
            (
                ResponsePolicyRule.from_dict(raw)
                for raw in raw_rules
            ),
            key=lambda rule: rule.priority,
            reverse=True,
        ))

    def match(self, predicate_key, force):
        return next(
            (
                rule for rule in self._rules
                if rule.trigger_predicate
                == predicate_key
                and rule.trigger_force == force
            ),
            None,
        )
