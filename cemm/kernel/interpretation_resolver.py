"""InterpretationResolver — selects interpretation branches and grounds meaning.
Single authority for interpretation branch selection.
"""

from __future__ import annotations

from typing import Any

from .interpretation_lattice import InterpretationLattice, InterpretationBranch
from .branch_arbitrator import BranchArbitrator


class InterpretationResolver:
    """Resolves interpretation branches into selected meanings.
    
    Authority for:
    - Interpretation branch selection
    - Branch score computation
    - Gap-to-branch assignment
    """
    
    def __init__(self) -> None:
        self._arbitrator = BranchArbitrator()
    
    def resolve(
        self,
        lattice: InterpretationLattice,
    ) -> dict[str, Any]:
        """Resolve the interpretation lattice into selected branches.
        
        Returns dict with:
        - selected_branches: list of selected branch IDs
        - primary_branch_id: the highest-scoring branch
        - all_branches: all viable branches
        """
        selected = self._arbitrator.arbitrate(lattice)
        primary = self._arbitrator.select_primary(lattice)
        
        return {
            "selected_branches": [b.branch_id for b in selected],
            "primary_branch_id": primary.branch_id if primary else None,
            "all_branches": [b.branch_id for b in lattice.viable_branches()],
            "branch_count": len(selected),
            "primary_score": primary.total_score if primary else 0.0,
        }
