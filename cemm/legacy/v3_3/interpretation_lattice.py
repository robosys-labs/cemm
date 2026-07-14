"""InterpretationLattice — manages multiple interpretation branches for one turn.
Each branch contains lexical senses, grammar, construction, grounding, scope,
operator activation, consequences, and gaps.

Branches are scored by coherence, type/port compatibility, context,
provenance strength, and complexity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class InterpretationBranch:
    """One interpretation hypothesis for a meaning group.
    
    Branches are hypotheses, not facts. They compete and coexist
    until resolved by the interpretation resolver.
    """
    branch_id: str
    group_id: str
    language_tag: str = "und"
    
    # Content
    lexical_sense_ids: tuple[str, ...] = ()
    grammar_binding_ids: tuple[str, ...] = ()
    construction_ids: tuple[str, ...] = ()
    entity_resolutions: dict[str, str] = field(default_factory=dict)
    predicate_activation_id: str = ""
    scope: str = "asserted"
    
    # Consequences
    state_delta_ids: tuple[str, ...] = ()
    operational_frame_id: str = ""
    frame_type: str = ""
    gap_ids: tuple[str, ...] = ()
    
    # Scoring
    coherence_score: float = 0.5
    type_compatibility: float = 0.5
    context_support: float = 0.5
    provenance_strength: float = 0.5
    complexity_penalty: float = 0.0
    
    @property
    def total_score(self) -> float:
        return (
            self.coherence_score * 0.3
            + self.type_compatibility * 0.25
            + self.context_support * 0.2
            + self.provenance_strength * 0.15
            - self.complexity_penalty * 0.1
        )
    
    @property
    def has_gaps(self) -> bool:
        return len(self.gap_ids) > 0
    
    @property
    def is_viable(self) -> bool:
        return self.total_score >= 0.3 or self.has_gaps

    @property
    def is_activatable_scope(self) -> bool:
        """Scopes that permit predicate activation and operational effects."""
        return self.scope not in ("quoted", "negated", "hypothesized")


class InterpretationLattice:
    """Collection of interpretation branches for one turn.
    
    Branches may be compatible (both can be true) or mutually exclusive.
    The resolver selects branches, preserving compatible alternatives.
    """
    
    def __init__(self) -> None:
        self._branches: dict[str, InterpretationBranch] = {}
    
    def add_branch(self, branch: InterpretationBranch) -> None:
        self._branches[branch.branch_id] = branch
    
    def get_branch(self, branch_id: str) -> InterpretationBranch | None:
        return self._branches.get(branch_id)
    
    def all_branches(self) -> list[InterpretationBranch]:
        return list(self._branches.values())
    
    def viable_branches(self) -> list[InterpretationBranch]:
        return [b for b in self._branches.values() if b.is_viable]
    
    def branches_by_group(self, group_id: str) -> list[InterpretationBranch]:
        return [b for b in self._branches.values() if b.group_id == group_id]
    
    def branches_with_gaps(self) -> list[InterpretationBranch]:
        return [b for b in self._branches.values() if b.has_gaps]
    
    def top_branch(self) -> InterpretationBranch | None:
        viable = self.viable_branches()
        if not viable:
            return None
        return max(viable, key=lambda b: b.total_score)
    
    def clear(self) -> None:
        self._branches.clear()
