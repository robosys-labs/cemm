"""GroundingSpecification and SemanticPattern — schema grounding requirements.

Import boundary: standard library only → model.refs, model.identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.refs import FrozenMap
from ..model.identity import TimeExtent


@dataclass(frozen=True, slots=True)
class SemanticPattern:
    """A semantic pattern with function and strength.

    function: constitutive, identity, selectional, diagnostic, default,
              typical, incidental, causal, normative
    strength: strict, defeasible, probabilistic

    Pattern function and pattern strength are independent.
    A typical feature never satisfies a constitutive requirement by itself.
    """
    pattern_kind: str = ""
    function: str = "typical"
    strength: str = "defeasible"
    expression: Any = None  # typed pattern AST; never copied executable code
    context_refs: tuple[str, ...] = ()
    valid_time: TimeExtent | None = None
    exception_refs: tuple[str, ...] = ()
    priority: int = 0
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GroundingSpecification:
    """Requirements for a schema to be considered grounded.

    Only patterns with an allowed function/strength combination satisfy
    a required definition field.
    """
    semantic_family: str = ""
    required_definition_fields: tuple[str, ...] = ()
    constitutive_pattern_refs: tuple[str, ...] = ()
    differentiating_pattern_refs: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()  # Ref[SchemaDependency]
    competency_case_refs: tuple[str, ...] = ()  # Ref[CompetencyCase]
    allowed_cycle_classes: frozenset[str] = field(default_factory=frozenset)
    minimum_independent_oracle_classes: frozenset[str] = field(default_factory=frozenset)
