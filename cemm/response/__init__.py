"""Response formation package.

This package owns the Decide -> Realize boundary for CEMM response output.
It composes response goals from semantic runtime state, then realizes those
goals through language-specific surface rules.
"""

from .response_formation_engine import ResponseFormationEngine

__all__ = ["ResponseFormationEngine"]
