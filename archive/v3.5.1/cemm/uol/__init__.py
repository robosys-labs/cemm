"""Compatibility import surface bound exclusively to the canonical v3.5 UOL.

This package name is retained for callers that imported ``cemm.uol`` historically,
but it no longer exposes or imports any v3.4.7 runtime/model authority.
"""
from ..v350.uol import *  # noqa: F401,F403
from ..v350.uol import __all__ as __all__
