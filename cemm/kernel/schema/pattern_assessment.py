"""Pattern function + strength — classification and enforcement.

Import boundary: schema.grounding_spec + schema.provenance only.

Architectural guardrails (AGENTS.md §7.6, UNDERSTANDING_PIPELINE.md §8):
- Pattern function and pattern strength are independent.
- function: constitutive, identity, selectional, diagnostic, default,
            typical, incidental, causal, normative
- strength: strict, defeasible, probabilistic
- Typical/default/incidental patterns NEVER satisfy a constitutive
  requirement by themselves.
- At least one permitted constitutive/identity pattern explains
  membership or occurrence.
- Specialization has a differentiator unless explicitly an alias/synonym.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .grounding_spec import SemanticPattern, GroundingSpecification


class PatternFunction(str, Enum):
    """Semantic pattern function — what the pattern does."""
    CONSTITUTIVE = "constitutive"  # defines what something IS
    IDENTITY = "identity"  # identifies an instance
    SELECTIONAL = "selectional"  # selects valid fillers for roles
    DIAGNOSTIC = "diagnostic"  # diagnoses category membership
    DEFAULT = "default"  # default value/behavior
    TYPICAL = "typical"  # typical but not necessary
    INCIDENTAL = "incidental"  # incidental, not relevant
    CAUSAL = "causal"  # causes an effect
    NORMATIVE = "normative"  # prescribes behavior


class PatternStrength(str, Enum):
    """Semantic pattern strength — how strong the pattern is."""
    STRICT = "strict"  # no exceptions
    DEFEASIBLE = "defeasible"  # can be overridden
    PROBABILISTIC = "probabilistic"  # statistical tendency


# Patterns that can satisfy constitutive requirements
CONSTITUTIVE_FUNCTIONS = frozenset({
    PatternFunction.CONSTITUTIVE,
    PatternFunction.IDENTITY,
})

# Patterns that CANNOT satisfy constitutive requirements
NON_CONSTITUTIVE_FUNCTIONS = frozenset({
    PatternFunction.DEFAULT,
    PatternFunction.TYPICAL,
    PatternFunction.INCIDENTAL,
    PatternFunction.SELECTIONAL,
    PatternFunction.DIAGNOSTIC,
    PatternFunction.CAUSAL,
    PatternFunction.NORMATIVE,
})


def is_constitutive(pattern: SemanticPattern) -> bool:
    """Check if a pattern has a constitutive function.

    Only constitutive or identity patterns can satisfy constitutive
    requirements. Typical/default/incidental patterns never do.
    """
    try:
        func = PatternFunction(pattern.function)
        return func in CONSTITUTIVE_FUNCTIONS
    except ValueError:
        return False


def is_non_constitutive(pattern: SemanticPattern) -> bool:
    """Check if a pattern has a non-constitutive function."""
    try:
        func = PatternFunction(pattern.function)
        return func in NON_CONSTITUTIVE_FUNCTIONS
    except ValueError:
        return True  # Unknown functions are treated as non-constitutive


def can_satisfy_constitutive_requirement(pattern: SemanticPattern) -> bool:
    """Check if a pattern can satisfy a constitutive requirement.

    Typical/default/incidental patterns NEVER satisfy a constitutive
    requirement by themselves (UNDERSTANDING_PIPELINE.md §8, point 6).
    """
    return is_constitutive(pattern)


def has_constitutive_pattern(
    patterns: tuple[SemanticPattern, ...],
) -> bool:
    """Check if at least one pattern is constitutive.

    A schema revision is structurally executable only when at least
    one permitted constitutive/identity pattern explains membership
    or occurrence (UNDERSTANDING_PIPELINE.md §8, point 6).
    """
    return any(can_satisfy_constitutive_requirement(p) for p in patterns)


def has_differentiator(
    patterns: tuple[SemanticPattern, ...],
) -> bool:
    """Check if at least one pattern provides a differentiator.

    Specialization has a differentiator unless explicitly an
    alias/synonym (UNDERSTANDING_PIPELINE.md §8, point 7).
    """
    for p in patterns:
        try:
            func = PatternFunction(p.function)
            if func in (PatternFunction.CONSTITUTIVE, PatternFunction.IDENTITY, PatternFunction.DIAGNOSTIC):
                return True
        except ValueError:
            continue
    return False


@dataclass(frozen=True, slots=True)
class PatternAssessment:
    """Assessment of patterns against grounding requirements.

    Derived control record — not a semantic object or activation authority.
    """
    has_constitutive: bool
    has_differentiator: bool
    non_constitutive_count: int
    constitutive_patterns: tuple[SemanticPattern, ...] = ()
    all_patterns: tuple[SemanticPattern, ...] = ()
    blocker_reasons: tuple[str, ...] = ()


def assess_patterns(
    patterns: tuple[SemanticPattern, ...],
    grounding_spec: GroundingSpecification,
    is_alias: bool = False,
) -> PatternAssessment:
    """Assess patterns against grounding specification requirements.

    Checks:
    1. At least one constitutive/identity pattern exists
    2. Specialization has a differentiator (unless alias/synonym)
    3. Typical/default/incidental patterns are not counted as constitutive
    """
    constitutive: list[SemanticPattern] = []
    non_constitutive_count = 0
    blockers: list[str] = []

    for p in patterns:
        if can_satisfy_constitutive_requirement(p):
            constitutive.append(p)
        elif is_non_constitutive(p):
            non_constitutive_count += 1

    has_const = len(constitutive) > 0
    if not has_const:
        blockers.append(
            "No constitutive/identity pattern found — "
            "typical/default/incidental patterns cannot close definitions"
        )

    has_diff = is_alias or has_differentiator(patterns)
    if not has_diff:
        blockers.append(
            "No differentiator pattern found — "
            "specialization requires a differentiator unless explicitly alias/synonym"
        )

    return PatternAssessment(
        has_constitutive=has_const,
        has_differentiator=has_diff,
        non_constitutive_count=non_constitutive_count,
        constitutive_patterns=tuple(constitutive),
        all_patterns=patterns,
        blocker_reasons=tuple(blockers),
    )
