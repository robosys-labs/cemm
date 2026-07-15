"""Typed relational, default, probabilistic, and causal rule records."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RuleStrength(str, Enum):
    STRICT = "strict"
    DEFEASIBLE = "defeasible"
    PROBABILISTIC = "probabilistic"


class CausalWarrant(str, Enum):
    NONE = "none"
    REPORTED_CLAIM = "reported_claim"
    CONTEXTUAL_RULE = "contextual_rule"
    PREDICTIVE_ASSOCIATION = "predictive_association"
    MECHANISM_SUPPORTED = "mechanism_supported"
    INTERVENTION_SUPPORTED = "intervention_supported"


class CycleClass(str, Enum):
    ACYCLIC = "acyclic"
    INVERSE = "inverse"
    POSITIVE_MONOTONE = "positive_monotone"
    STRATIFIED_DEFEASIBLE = "stratified_defeasible"
    UNSUPPORTED_NON_MONOTONE = "unsupported_non_monotone"


@dataclass(frozen=True, slots=True)
class RuleAtom:
    predicate_key: str
    roles: dict[str, str]
    polarity: str = "positive"
    context_term: str = "$context"
    valid_time_term: str = "$valid_time"


@dataclass(frozen=True, slots=True)
class ExistentialDeclaration:
    variable: str
    entity_kind_ref: str = ""
    identity_scope: str = "rule_application"
    maximum_instances: int = 1


@dataclass(frozen=True, slots=True)
class SemanticRule:
    rule_id: str
    premises: tuple[RuleAtom, ...]
    conclusions: tuple[RuleAtom, ...]
    strength: RuleStrength
    cycle_class: CycleClass
    confidence: float = 1.0
    causal_warrant: CausalWarrant = CausalWarrant.NONE
    exception_atoms: tuple[RuleAtom, ...] = ()
    existential_declarations: tuple[ExistentialDeclaration, ...] = ()
    context_refs: tuple[str, ...] = ()
    valid_time_policy: str = "intersection"
    sensitivity: str = "ordinary"
    enabled_by_default: bool = True
    priority: int = 0
    stratum: int = 0
    max_firings_per_cycle: int = 32
    provenance_refs: tuple[str, ...] = ()

    def declared_existential(self, variable: str) -> ExistentialDeclaration | None:
        return next(
            (
                declaration
                for declaration in self.existential_declarations
                if declaration.variable == variable
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class SemanticFact:
    fact_id: str
    predicate_key: str
    roles: dict[str, str]
    context_ref: str
    valid_time_ref: str = ""
    polarity: str = "positive"
    confidence: float = 1.0
    strength: RuleStrength = RuleStrength.STRICT
    causal_warrant: CausalWarrant = CausalWarrant.NONE
    sensitivity: str = "ordinary"
    evidence_refs: tuple[str, ...] = ()
    derivation_ref: str = ""
    derivation_depth: int = 0

    @property
    def identity(self) -> tuple:
        return (
            self.predicate_key,
            tuple(sorted(self.roles.items())),
            self.context_ref,
            self.valid_time_ref,
            self.polarity,
        )


@dataclass(frozen=True, slots=True)
class ExistentialConstraint:
    constraint_id: str
    rule_ref: str
    variable: str
    entity_kind_ref: str
    bound_roles: dict[str, str]
    context_ref: str
    valid_time_ref: str
    evidence_refs: tuple[str, ...]
    sensitivity: str = "ordinary"


@dataclass(frozen=True, slots=True)
class InferenceProofStep:
    proof_id: str
    rule_ref: str
    premise_fact_refs: tuple[str, ...]
    variable_bindings: dict[str, str]
    conclusion_refs: tuple[str, ...]
    exception_checks: tuple[str, ...]
    strength: RuleStrength
    causal_warrant: CausalWarrant
    context_ref: str
    valid_time_ref: str
    derivation_depth: int
    dependency_fingerprint: str


@dataclass(frozen=True, slots=True)
class InferenceBudget:
    max_steps: int = 128
    max_depth: int = 8
    max_new_facts: int = 256
    max_rule_firings: int = 256
    max_firings_per_rule: int = 32
    max_signature_visits: int = 1
    max_existential_constraints: int = 32
    wall_clock_ms: int = 50
    allow_sensitive: bool = False


@dataclass(frozen=True, slots=True)
class InferenceOutcome:
    status: str
    derived_facts: tuple[SemanticFact, ...] = ()
    existential_constraints: tuple[ExistentialConstraint, ...] = ()
    proofs: tuple[InferenceProofStep, ...] = ()
    unresolved_rule_refs: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()
    steps: int = 0
    elapsed_ms: float = 0.0
