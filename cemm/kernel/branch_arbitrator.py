"""BranchArbitrator — selects and scores interpretation branches.
Uses multi-factor scoring: coherence, type/port compatibility,
context/provenance, and complexity penalty.

Does not discard compatible meanings — multiple branches may coexist.
"""

from __future__ import annotations

from typing import Any

from .interpretation_lattice import InterpretationBranch, InterpretationLattice


class BranchArbitrator:
    """Arbitrates between interpretation branches.
    
    Preserves compatible branches. Only truly contradictory branches
    are resolved by preference.
    """
    
    def arbitrate(
        self,
        lattice: InterpretationLattice,
    ) -> list[InterpretationBranch]:
        """Score all branches and return selected order.
        
        Compatible branches are all returned, ordered by score.
        """
        viable = lattice.viable_branches()
        return sorted(viable, key=lambda b: b.total_score, reverse=True)
    
    def select_primary(
        self,
        lattice: InterpretationLattice,
    ) -> InterpretationBranch | None:
        viable = lattice.viable_branches()
        if not viable:
            return None
        return max(viable, key=lambda b: b.total_score)
