"""CompetencyCase — competence test cases with provenance rules.

Import boundary: standard library only → model.refs, model.identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model.identity import TimeExtent


@dataclass(frozen=True, slots=True)
class CompetencyCase:
    """A competency test case for schema validation.

    competency_kind: compose, query, discriminate, infer, realize, etc.
    oracle_kind: invariant, audited_expected, independent_observation,
                 sibling_contrast, teaching_derived

    A teaching-derived case may count for structure but not independent
    discrimination or epistemic support.
    """
    id: str
    competency_kind: str = "compose"
    input_ref: str = ""
    expected_pattern_ref: str = ""
    oracle_kind: str = "invariant"
    generation_lineage_refs: tuple[str, ...] = ()
    oracle_lineage_refs: tuple[str, ...] = ()
    independence_cluster: str = ""
    counts_for_structure: bool = True
    counts_for_discrimination: bool = False
    counts_for_epistemic_support: bool = False
    context_refs: tuple[str, ...] = ()
    budget_cost: int = 1
