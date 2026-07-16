"""Compile active schema-store rules and relation algebra into runtime rules.

The schema store remains the sole lifecycle authority.  This catalog is a
read-only projection of active schema revisions into the bounded inference
engine's immutable rule model.  It does not activate, mutate, or silently
promote learned rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .rule_model import (
    CausalWarrant,
    CycleClass,
    ExistentialDeclaration,
    RuleAtom,
    RuleStrength,
    SemanticRule,
)


@dataclass(frozen=True, slots=True)
class RuleCatalogSnapshot:
    store_revision: int
    rules: tuple[SemanticRule, ...]


class SemanticRuleCatalog:
    """Revision-pinned runtime view of active RuleSchema/algebra records."""

    def __init__(self, schema_store) -> None:
        self._store = schema_store
        self._cached = RuleCatalogSnapshot(-1, ())

    def active_rules(self) -> tuple[SemanticRule, ...]:
        revision = int(getattr(self._store, "store_revision", 0))
        if self._cached.store_revision == revision:
            return self._cached.rules

        compiled: list[SemanticRule] = []
        for envelope in self._store.records(
            schema_kind="rule",
            statuses=("active",),
        ):
            rule = self._compile_rule_envelope(envelope)
            if rule is not None:
                compiled.append(rule)

        for envelope in self._store.records(
            schema_kind="relation_algebra",
            statuses=("active",),
        ):
            compiled.extend(self._compile_algebra_envelope(envelope))

        rules = self._dedupe(compiled)
        self._cached = RuleCatalogSnapshot(revision, rules)
        return rules

    def _compile_rule_envelope(self, envelope) -> SemanticRule | None:
        payload = getattr(envelope, "payload", None)
        if payload is None or not getattr(payload, "premises", ()):
            return None
        if not getattr(payload, "conclusions", ()):
            return None
        try:
            strength = RuleStrength(
                getattr(getattr(payload, "strength", "strict"), "value", payload.strength)
            )
            cycle_class = CycleClass(
                getattr(
                    getattr(payload, "cycle_class", "acyclic"),
                    "value",
                    payload.cycle_class,
                )
            )
            causal_warrant = CausalWarrant(
                getattr(
                    getattr(payload, "causal_warrant", "none"),
                    "value",
                    payload.causal_warrant,
                )
            )
        except (TypeError, ValueError, AttributeError):
            return None

        return SemanticRule(
            rule_id=str(getattr(payload, "semantic_key", "") or envelope.record_id),
            premises=tuple(self._compile_atom(atom) for atom in payload.premises),
            conclusions=tuple(self._compile_atom(atom) for atom in payload.conclusions),
            strength=strength,
            cycle_class=cycle_class,
            confidence=float(getattr(payload, "confidence", envelope.confidence)),
            causal_warrant=causal_warrant,
            exception_atoms=tuple(
                self._compile_atom(atom)
                for atom in getattr(payload, "exception_atoms", ())
            ),
            existential_declarations=tuple(
                ExistentialDeclaration(
                    variable=str(item.variable),
                    entity_kind_ref=str(item.entity_kind_ref),
                    identity_scope=str(item.identity_scope),
                    maximum_instances=int(item.maximum_instances),
                )
                for item in getattr(payload, "existential_declarations", ())
            ),
            context_refs=tuple(getattr(payload, "context_refs", ()) or ()),
            valid_time_policy=str(
                getattr(payload, "valid_time_policy", "intersection")
            ),
            sensitivity=str(getattr(payload, "sensitivity", "ordinary")),
            enabled_by_default=bool(
                getattr(payload, "enabled_by_default", True)
            ),
            priority=int(getattr(payload, "priority", 0)),
            stratum=int(getattr(payload, "stratum", 0)),
            max_firings_per_cycle=int(
                getattr(payload, "max_firings_per_cycle", 32)
            ),
            provenance_refs=tuple(dict.fromkeys((
                envelope.record_id,
                *tuple(getattr(payload, "provenance_refs", ()) or ()),
                *tuple(getattr(envelope, "support_refs", ()) or ()),
            ))),
        )

    @staticmethod
    def _compile_atom(atom) -> RuleAtom:
        context_ref = str(getattr(atom, "context_ref", ""))
        return RuleAtom(
            predicate_key=str(atom.predicate_key),
            roles={str(key): str(value) for key, value in atom.roles.items()},
            polarity=str(getattr(atom, "polarity", "positive")),
            context_term=context_ref if context_ref.startswith("$") else "$context",
            valid_time_term="$valid_time",
        )

    def _compile_algebra_envelope(self, envelope) -> tuple[SemanticRule, ...]:
        algebra = getattr(envelope, "payload", None)
        predicate_key = str(getattr(algebra, "predicate_key", ""))
        role_keys = self._predicate_roles(predicate_key)
        if not predicate_key or len(role_keys) != 2:
            return ()

        left, right = role_keys
        result: list[SemanticRule] = []
        common = {
            "strength": RuleStrength.STRICT,
            "confidence": 1.0,
            "causal_warrant": CausalWarrant.NONE,
            "enabled_by_default": True,
            "provenance_refs": (envelope.record_id,),
        }

        if bool(getattr(algebra, "symmetric", False)):
            result.append(SemanticRule(
                rule_id=f"algebra:{predicate_key}:symmetric",
                premises=(RuleAtom(predicate_key, {left: "$a", right: "$b"}),),
                conclusions=(RuleAtom(predicate_key, {left: "$b", right: "$a"}),),
                cycle_class=CycleClass.INVERSE,
                max_firings_per_cycle=16,
                **common,
            ))

        inverse_key = str(getattr(algebra, "inverse_predicate_key", ""))
        inverse_roles = self._predicate_roles(inverse_key) if inverse_key else ()
        if inverse_key and len(inverse_roles) == 2:
            inverse_left, inverse_right = inverse_roles
            result.append(SemanticRule(
                rule_id=f"algebra:{predicate_key}:inverse:{inverse_key}",
                premises=(RuleAtom(predicate_key, {left: "$a", right: "$b"}),),
                conclusions=(RuleAtom(
                    inverse_key,
                    {inverse_left: "$b", inverse_right: "$a"},
                ),),
                cycle_class=CycleClass.INVERSE,
                max_firings_per_cycle=16,
                **common,
            ))

        if bool(getattr(algebra, "transitive", False)):
            result.append(SemanticRule(
                rule_id=f"algebra:{predicate_key}:transitive",
                premises=(
                    RuleAtom(predicate_key, {left: "$a", right: "$b"}),
                    RuleAtom(predicate_key, {left: "$b", right: "$c"}),
                ),
                conclusions=(RuleAtom(
                    predicate_key,
                    {left: "$a", right: "$c"},
                ),),
                cycle_class=CycleClass.POSITIVE_MONOTONE,
                max_firings_per_cycle=32,
                **common,
            ))

        return tuple(result)

    def _predicate_roles(self, predicate_key: str) -> tuple[str, ...]:
        if not predicate_key:
            return ()
        envelope = self._store.find_active(predicate_key)
        payload = getattr(envelope, "payload", None) if envelope else None
        return tuple(
            str(role).removeprefix("role:")
            for role in tuple(getattr(payload, "role_refs", ()) or ())
        )

    @staticmethod
    def _dedupe(rules: Iterable[SemanticRule]) -> tuple[SemanticRule, ...]:
        by_id: dict[str, SemanticRule] = {}
        for rule in rules:
            by_id[rule.rule_id] = rule
        return tuple(by_id[key] for key in sorted(by_id))
