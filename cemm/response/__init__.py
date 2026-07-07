"""Response formation package."""

__all__ = ["ResponseFormationEngine"]


def __getattr__(name: str):
    if name == "ResponseFormationEngine":
        from .response_formation_engine import ResponseFormationEngine
        return ResponseFormationEngine
    raise AttributeError(name)
