"""CEMM v3.5.1 implementation namespace.

The physical ``v350`` package path is retained for repository/module stability; active
runtime/version authority is v3.5.1 and is declared only by ``version.py`` and the
signed runtime manifest. No legacy Runtime or UOL API is re-exported here.
"""
from .version import VERSION

__all__ = ["VERSION"]
