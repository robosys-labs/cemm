"""PredicateSchema — executable definition of a semantic predicate.

Import boundary: standard library only → model.refs, model.predication.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.predication import AspectProfile
from .grounding_spec import SemanticPattern
from .role import RoleSchema


@dataclass(frozen=True, slots=True)
class ContextBehavior:
    """How a predicate behaves across contexts."""
    supports_reported: bool = True
    supports_hypothetical: bool = True
    supports_counterfactual: bool = False
    supports_quoted: bool = True


@dataclass(frozen=True, slots=True)
class PolarityBehavior:
    """How a predicate handles negation."""
    supports_negation: bool = True
    negation_kind: str = "contradictory"  # contradictory, contrary, subcontrary


@dataclass(frozen=True, slots=True)
class ModalityBehavior:
    """How a predicate interacts with modal qualifiers."""
    supports_modality: bool = True
    default_modal_kind: str = "possible"


@dataclass(frozen=True, slots=True)
class IdentityPolicy:
    """Policy for proposition identity under this predicate."""
    includes_valid_time: bool = False
    includes_modal_qualifiers: bool = True
    includes_attribution: bool = False
    custom_qualifier_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CardinalityPolicy:
    """Policy for how propositions under this predicate coexist."""
    cardinality: str = "many"  # one, many, exclusive
    reinforcement_policy: str = "independent"  # independent, reinforce, supersede


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    """Policy for evidence handling under this predicate."""
    minimum_evidence_count: int = 1
    requires_independent_sources: bool = False
    allows_self_attribution: bool = True


@dataclass(frozen=True, slots=True)
class PersistencePolicy:
    """Policy for how long propositions under this predicate persist."""
    retention: str = "long_term"  # ephemeral, session, long_term
    decay_rate: float = 0.0


@dataclass(frozen=True, slots=True)
class MutationTemplate:
    """A template for a predicted effect of a predicate."""
    target_kind: str = ""
    operation: str = ""  # create, update, supersede, append
    pattern_ref: str = ""
    conditions: tuple[SemanticPattern, ...] = ()


@dataclass(frozen=True, slots=True)
class QueryProjection:
    """A projection for querying under this predicate."""
    projection_kind: str = ""
    role_refs: tuple[str, ...] = ()
    pattern_ref: str = ""


@dataclass(frozen=True, slots=True)
class PredicateSchema:
    """Executable definition of a semantic predicate.

    Actions and processes are event-oriented predicate schemas;
    executable operations use OperationSchema and reference semantic
    predicates for preconditions and effects.
    """
    semantic_key: str
    predication_kind: str = "relation"  # relation, state, event
    agentive: bool = False
    aspect_profile: AspectProfile = field(default_factory=AspectProfile)
    role_refs: tuple[str, ...] = ()  # Ref[RoleSchema]
    context_behavior: ContextBehavior = field(default_factory=ContextBehavior)
    polarity_behavior: PolarityBehavior = field(default_factory=PolarityBehavior)
    modality_behavior: ModalityBehavior = field(default_factory=ModalityBehavior)
    preconditions: tuple[SemanticPattern, ...] = ()
    predicted_effects: tuple[MutationTemplate, ...] = ()
    query_projections: tuple[QueryProjection, ...] = ()
    identity_policy: IdentityPolicy = field(default_factory=IdentityPolicy)
    cardinality_policy: CardinalityPolicy = field(default_factory=CardinalityPolicy)
    evidence_policy: EvidencePolicy = field(default_factory=EvidencePolicy)
    persistence_policy: PersistencePolicy = field(default_factory=PersistencePolicy)
    lexicalization_refs: tuple[str, ...] = ()  # Ref[LexemeSenseSchema]
    realization_refs: tuple[str, ...] = ()  # Ref[RealizationSchema]
    sensitivity: str = "ordinary"
