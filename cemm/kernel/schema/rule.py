"""Language-neutral relation, default and causal rule schemas."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class RuleKind(str, Enum):
    RELATIONAL = "relational"
    DEFINITIONAL = "definitional"
    DEFAULT = "default"
    CAUSAL = "causal"

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
    roles: dict[str, str] = field(default_factory=dict)
    polarity: str = "positive"
    context_ref: str = ""
    modality: str = "actual"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RuleAtom":
        return cls(
            predicate_key=str(raw["predicate_key"]),
            roles={str(k): str(v) for k, v in raw.get("roles", {}).items()},
            polarity=str(raw.get("polarity", "positive")),
            context_ref=str(raw.get("context_ref", "")),
            modality=str(raw.get("modality", "actual")),
        )

@dataclass(frozen=True, slots=True)
class RuleSchema:
    semantic_key: str
    premises: tuple[RuleAtom, ...]
    conclusions: tuple[RuleAtom, ...]
    rule_kind: RuleKind = RuleKind.RELATIONAL
    strength: RuleStrength = RuleStrength.STRICT
    confidence: float = 1.0
    causal_warrant: CausalWarrant = CausalWarrant.NONE
    cycle_class: CycleClass = CycleClass.ACYCLIC
    stratum: int = 0
    exception_atoms: tuple[RuleAtom, ...] = ()
    context_refs: tuple[str, ...] = ()
    valid_time_policy: str = "inherit"
    sensitivity: str = "ordinary"
    enabled_by_default: bool = True
    max_firings_per_cycle: int = 32
    provenance_refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RuleSchema":
        return cls(
            semantic_key=str(raw["semantic_key"]),
            premises=tuple(RuleAtom.from_dict(v) for v in raw.get("premises", ())),
            conclusions=tuple(RuleAtom.from_dict(v) for v in raw.get("conclusions", ())),
            rule_kind=RuleKind(raw.get("rule_kind", "relational")),
            strength=RuleStrength(raw.get("strength", "strict")),
            confidence=float(raw.get("confidence", 1.0)),
            causal_warrant=CausalWarrant(raw.get("causal_warrant", "none")),
            cycle_class=CycleClass(raw.get("cycle_class", "acyclic")),
            stratum=int(raw.get("stratum", 0)),
            exception_atoms=tuple(
                RuleAtom.from_dict(v) for v in raw.get("exception_atoms", ())
            ),
            context_refs=tuple(str(v) for v in raw.get("context_refs", ())),
            valid_time_policy=str(raw.get("valid_time_policy", "inherit")),
            sensitivity=str(raw.get("sensitivity", "ordinary")),
            enabled_by_default=bool(raw.get("enabled_by_default", True)),
            max_firings_per_cycle=int(raw.get("max_firings_per_cycle", 32)),
            provenance_refs=tuple(str(v) for v in raw.get("provenance_refs", ())),
        )

@dataclass(frozen=True, slots=True)
class RelationAlgebraSchema:
    predicate_key: str
    inverse_predicate_key: str = ""
    symmetric: bool = False
    transitive: bool = False
    reflexive: bool = False
    irreflexive: bool = False
    antisymmetric: bool = False
    composition_rules: tuple[str, ...] = ()
